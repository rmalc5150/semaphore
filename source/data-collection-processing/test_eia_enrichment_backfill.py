import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import eia_enrichment_backfill as backfill
from collection_storage import LocalStore, StorageSettings, write_checked
from research_contract import ROOT, load_json, seal_record


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = LocalStore(self.root / "store")
        self.db = backfill.registry(self.root / "registry.sqlite3")
        self.addCleanup(self.db.close)
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.config = {"job_id": "test-s56", "window_start": "2021-01-01T00:00:00Z",
            "snapshot_cutoff": "2026-10-16T00:00:00Z", "inventory_sha256": "a" * 64,
            "max_batches_per_invocation": 10, "max_attempts": 3,
            "email_topic_arn": "arn:topic", "email_recipient": "owner@example.com"}
        self.parent = seal_record({'document_type':'collected_record','schema_version':'1.0',
            'source':'eia_retail_prices','dataset':'specialist_inputs','source_record_id':'35129803',
            'source_record_id_basis':'provider','source_url':'https://pubmed.ncbi.nlm.nih.gov/35129803/',
            'universe_version':self.universe['universe_version'],'company_ids':[],'listing_ids':[],
            'product_ids':[],'person_ids':[],'entity_match_status':'unresolved','event_at':None,
            'available_at':None,'source_updated_at':None,'ingested_at':'2026-10-01T12:00:00Z',
            'availability_basis':'unknown','availability_evidence':[],'run_id':'run_example',
            'payload':{'source_evidence':[], 'data':{'period':'2021-01','stateid':'US','sectorid':'ALL','price':'10.0','price-units':'cents per kilowatt-hour'}}})

    def discover(self, parents):
        raw = b"".join((json.dumps(p) + "\n").encode() for p in parents)
        sha = hashlib.sha256(raw).hexdigest()
        write_checked(self.store, "input/records.jsonl", raw)
        inventory = {"batches": [{"key": "input/records.jsonl", "sha256": sha, "records": len(parents), "source": "eia_retail_prices"}]}
        return backfill.discover(self.store, self.db, self.config, inventory)

    def test_repeated_observations_are_grouped_without_losing_source_revisions(self):
        second = seal_record({**self.parent, "ingested_at": "2026-10-02T12:00:00Z"})
        changed = copy.deepcopy(second)
        changed['payload']['data']['price']='10.1'
        changed = seal_record(changed)
        self.assertEqual(self.discover([self.parent, second, changed]), 0)
        self.assertEqual(self.db.execute("SELECT count(*),sum(observations) FROM versions").fetchone(), (2, 3))
        self.discover([self.parent, second, changed])
        self.assertEqual(self.db.execute("SELECT sum(observations) FROM versions").fetchone()[0], 3)

    def test_retail_original_identity_value_date_and_current_vintage_are_separate(self):
        from test_eia_enrichment import META,row as retail
        self.discover([self.parent])
        row=self.db.execute("SELECT id,source,parent,lineage,observations,attempts FROM versions").fetchone()
        with patch('eia_enrichment.retail_metadata',return_value=META),patch('eia_enrichment.retail_history',return_value=[retail('2021-01','12'),retail('2020-12'),retail('2020-01')]):
            _,_,record=backfill.enrich_one(self.store,StorageSettings(),self.config,self.universe,self.taxonomy,self.db,Mock(evidence=[]),row)
            _,_,replay=backfill.enrich_one(self.store,StorageSettings(),self.config,self.universe,self.taxonomy,self.db,Mock(evidence=[]),row)
        self.assertEqual(record['record_id'],self.parent['record_id'])
        self.assertEqual(record['event_at'],self.parent['event_at'])
        self.assertEqual(record['payload']['data']['price'],'10.0')
        self.assertEqual(record['payload']['data']['enrichment']['fields']['price']['value'],'12')
        self.assertEqual(record['observation_id'],replay['observation_id'])
        self.assertNotIn('enrichment',self.parent['payload']['data'])

    def test_transient_api_failure_never_consumes_final_attempt_as_gap(self):
        self.discover([self.parent])
        row=self.db.execute("SELECT id,source,parent,lineage,observations,attempts FROM versions").fetchone()
        with patch('eia_enrichment.retail_metadata',side_effect=backfill.SourceIssue('source_http_504')):
            with self.assertRaises(backfill.SourceIssue):
                backfill.enrich_one(self.store,StorageSettings(),self.config,self.universe,self.taxonomy,self.db,Mock(evidence=[]),(*row[:-1],10))

    def test_email_waits_for_publication_and_athena_counts(self):
        state = {"remaining_batches": 0, "pending_versions": 0}
        sns = Mock()
        with patch.object(backfill, "publication_ready", return_value=False):
            result = backfill.notify_when_verified(self.store, self.db, self.config, sns, state, self.root / "index", Mock())
        self.assertEqual(result["status"], "awaiting_athena_publication")
        sns.publish.assert_not_called()
        with patch.object(backfill, "publication_ready", return_value=True), patch("committed_data_athena.query", return_value={"rows": [["eia_retail_prices", "1"]]}):
            with self.assertRaisesRegex(Exception, "athena_count_mismatch"):
                backfill.notify_when_verified(self.store, self.db, self.config, sns, state, self.root / "index", Mock())
        sns.publish.assert_not_called()

    def test_completion_email_includes_explicit_gaps_and_is_not_repeated(self):
        self.discover([self.parent])
        self.db.execute("UPDATE versions SET status='done',outcome='gap',batch_key='batch'")
        self.db.commit()
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{"Subscriptions": [
            {"Protocol": "email", "Endpoint": "owner@example.com", "SubscriptionArn": "arn:confirmed"}]}]
        sns.publish.return_value = {"MessageId": "accepted"}
        state = {"remaining_batches": 0, "pending_versions": 0}
        with patch.object(backfill, "publication_ready", return_value=True), patch("committed_data_athena.query", return_value={"rows": [["eia_retail_prices", "1"]]}):
            result = backfill.notify_when_verified(self.store, self.db, self.config, sns, state, self.root / "index", Mock())
            backfill.notify_when_verified(self.store, self.db, self.config, sns, result, self.root / "index", Mock())
        self.assertEqual(result["status"], "finished_with_gaps")
        self.assertEqual(result["notification_message_id"], "accepted")
        self.assertIn("gaps recorded", sns.publish.call_args.kwargs["Subject"])
        self.assertEqual(sns.publish.call_count, 1)


if __name__ == "__main__":
    unittest.main()
