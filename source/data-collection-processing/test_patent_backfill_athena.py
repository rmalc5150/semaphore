from contextlib import redirect_stdout
from datetime import date
import io
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
import pyarrow.parquet as pq
from collection_storage import StorageSettings
from patent_bigquery_collection import collect
from patent_query_plan import build
from patent_collection import RULES_PATH
from research_contract import ROOT, load_json
from test_patent_bigquery_collection import Client
import patent_backfill_athena as curated


class CurationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.settings = StorageSettings(local_root=str(self.root / "store"), s3_bucket="fixture")
        self.store = self.settings.store()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.config = load_json(ROOT / "config/patent-backfill-athena.json")
        plan = build(self.universe, load_json(RULES_PATH), date(2025,1,1), date(2025,2,1), 50000000000)
        with redirect_stdout(io.StringIO()):
            self.result = collect(self.store, self.settings, self.universe, self.taxonomy, plan, 50000000000, Client())

    def prepare(self):
        with redirect_stdout(io.StringIO()):
            return curated.prepare(self.store, self.settings, self.config, self.result["manifest"], self.root / "build")

    def test_reproducible_complete_month_with_explicit_unresolved_review(self):
        root = self.prepare()
        self.assertEqual(root, self.prepare())
        report = load_json(root / "release.json")
        rows = pq.read_table(root / report["files"][curated.TABLE]["path"]).to_pylist()
        self.assertEqual(len(rows), 3)
        pubs = [r for r in rows if r["row_type"] == "publication"]
        self.assertTrue(all(not r["point_in_time_eligible"] and r["available_at"] is None for r in pubs))
        self.assertTrue(all(r["current_ownership_status"] == "not_established" for r in pubs))
        self.assertEqual(report["counts"]["unresolved_party_publications"], 2)
        self.assertEqual(report["counts"]["supported_technology_publications"], 0)
        self.assertTrue(all(json.loads(r["pending_technology_json"]) for r in pubs))

    def test_partial_and_tampered_evidence_rejected(self):
        manifest = json.loads(self.store.get(self.result["manifest"]).body)
        batch = manifest["pages"][1]["batches"][0]
        obj = self.store.get(batch["key"])
        self.store.put(batch["key"], b"bad", expected=obj.token)
        with self.assertRaises(ValueError):
            self.prepare()

    def test_streamed_month_roundtrips_multiple_row_groups(self):
        class LargerClient(Client):
            def page(self, identity, token, size):
                result = super().page(identity, token, size)
                result.pop('pageToken', None)
                result['totalRows'] = '150'
                result['rows'] = [{'f': [{'v': f'CN-{n}-A'}, {'v': '2025-01-06'}, {'v': 'Battery'}]} for n in range(150)]
                return result
        plan = build(self.universe, load_json(RULES_PATH), date(2025,1,1), date(2025,2,1), 50000000000)
        with redirect_stdout(io.StringIO()):
            self.result = collect(self.store, self.settings, self.universe, self.taxonomy,
                plan, 50000000000, LargerClient(), refresh=True)
        root = self.prepare()
        report = load_json(root / 'release.json')
        parquet = pq.ParquetFile(root / report['files'][curated.TABLE]['path'])
        self.assertEqual(parquet.metadata.num_rows, 151)
        self.assertGreater(parquet.num_row_groups, 1)
        self.assertEqual(report['counts']['publications'], 150)
        self.assertTrue(report['streaming_upload'])

    def clients(self):
        glue, athena = Mock(), Mock()
        glue.get_database.return_value = {"Database": {"Parameters": {"optima_pilot": "patents"}}}
        athena.get_work_group.return_value = {"WorkGroup": {"State": "ENABLED", "Configuration": {"EnforceWorkGroupConfiguration": True, "BytesScannedCutoffPerQuery": 104857600}}}
        def table(**kwargs):
            name = kwargs["Name"]
            if name == curated.TABLE:
                return {"Table": {"Parameters": {"optima_owner": curated.OWNER}, "StorageDescriptor": curated.descriptor("fixture"), "PartitionKeys": [{"Name": "publication_month", "Type": "string"}]}}
            return {"Table": {"TableType": "VIRTUAL_VIEW", "Parameters": {"optima_view_hash": curated.digest(curated.views(self.config["database"])[name])}}}
        glue.get_table.side_effect = table
        glue.get_partition.side_effect = ClientError({"Error": {"Code": "EntityNotFoundException"}}, "GetPartition")
        return glue, athena

    def test_failed_athena_checks_remove_only_new_month_partition(self):
        root = self.prepare()
        with redirect_stdout(io.StringIO()):
            curated.publish(self.store, self.settings, root)
        glue, athena = self.clients()
        with patch.object(curated.release, "run_query", return_value={"rows": [["wrong"]]}), self.assertRaises(ValueError):
            curated.deploy(self.store, self.settings, root, clients=(glue, athena))
        glue.delete_partition.assert_called_once_with(DatabaseName=self.config["database"], TableName=curated.TABLE, PartitionValues=["2025-01"])
        glue.delete_table.assert_not_called()

    def test_other_month_partition_untouched_and_matching_release_is_retryable(self):
        root = self.prepare()
        with redirect_stdout(io.StringIO()):
            curated.publish(self.store, self.settings, root)
        glue, athena = self.clients()
        outputs = [ [["2","2","0","0","0","0","0"]], [["2","0","0","2"]], [], [["party","0"],["sector","2"]] ]
        with redirect_stdout(io.StringIO()), patch.object(curated.release, "run_query", side_effect=[{"rows": r} for r in outputs]):
            curated.deploy(self.store, self.settings, root, clients=(glue, athena))
        self.assertEqual(glue.create_partition.call_args.kwargs["PartitionInput"]["Values"], ["2025-01"])
        self.assertEqual(load_json(root / "athena-verification.json")["status"], "verified")
        glue.delete_partition.assert_not_called()

    def test_overlapping_replacement_requires_explicit_flag(self):
        root = self.prepare()
        with redirect_stdout(io.StringIO()):
            curated.publish(self.store, self.settings, root)
        glue, athena = self.clients()
        glue.get_partition.side_effect = None
        glue.get_partition.return_value = {"Partition": {"Parameters": {"optima_owner": curated.OWNER, "release_id": "old"}}}
        with self.assertRaises(ValueError):
            curated.deploy(self.store, self.settings, root, clients=(glue, athena))
        glue.update_partition.assert_not_called()

    def test_replacement_failure_restores_previous_partition(self):
        root = self.prepare()
        with redirect_stdout(io.StringIO()):
            curated.publish(self.store, self.settings, root)
        glue, athena = self.clients()
        previous = {"Values": ["2025-01"], "StorageDescriptor": curated.descriptor("s3://fixture/old/"),
            "Parameters": {"optima_owner": curated.OWNER, "release_id": "old"}}
        glue.get_partition.side_effect = None
        glue.get_partition.return_value = {"Partition": previous}
        with patch.object(curated.release, "run_query", side_effect=RuntimeError("query failed")), self.assertRaises(RuntimeError):
            curated.deploy(self.store, self.settings, root, replace_window=True, clients=(glue, athena))
        self.assertEqual(glue.update_partition.call_args.kwargs["PartitionInput"], previous)
        glue.delete_partition.assert_not_called()

    def test_recover_view_created_before_tagging_only_for_exact_definition(self):
        sql = "SELECT 1"
        view = {"Name": "view", "TableType": "VIRTUAL_VIEW", "ViewOriginalText": "/* Presto View: " + base64.b64encode(json.dumps({"originalSql": sql}).encode()).decode() + " */"}
        self.assertEqual(curated.view_input(view, sql)["Parameters"]["optima_view_hash"], curated.digest(sql))
        with self.assertRaises(ValueError):
            curated.view_input(view, "SELECT 2")

    def test_athena_formatting_equivalent_but_semantic_changes_rejected(self):
        self.assertTrue(curated.same_sql("SELECT a,b FROM t WHERE row_type='publication'", "SELECT\n a\n, b\nFROM\n t\nWHERE (row_type = 'publication')"))
        self.assertFalse(curated.same_sql("SELECT a FROM t WHERE row_type='publication'", "SELECT a FROM t WHERE row_type='coverage'"))
        self.assertFalse(curated.same_sql("SELECT (a+b)*c FROM t", "SELECT a+b*c FROM t"))
        self.assertTrue(curated.same_sql("SELECT p FROM (db.tbl CROSS JOIN UNNEST(x) t(p)) WHERE (x=1)", "SELECT p FROM db.tbl CROSS JOIN UNNEST(x) AS t(p) WHERE x=1"))
        self.assertFalse(curated.same_sql("SELECT p FROM (db.tbl CROSS JOIN UNNEST(y) t(p))", "SELECT p FROM db.tbl CROSS JOIN UNNEST(x) AS t(p)"))


if __name__ == "__main__":
    unittest.main()
