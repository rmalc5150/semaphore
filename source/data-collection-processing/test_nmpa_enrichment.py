import copy
import hashlib
import sqlite3
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from collection_storage import LocalStore, StorageSettings, write_checked
from research_contract import ROOT, load_json, validate_record
import nmpa_enrichment as facts
import nmpa_enrichment_worker as worker

FIXTURE = ROOT / 'tests/fixtures/nmpa/CTR20231998.html'


class FactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = FIXTURE.read_text()
        cls.facts = facts.structured_detail(cls.document,'CTR20231998')

    def test_live_source_sponsor_status_and_explicit_dates(self):
        self.assertEqual(self.facts['sponsors'],['成都优洛生物科技有限公司'])
        self.assertEqual(self.facts['drug_name'],'EP-9001A注射液')
        self.assertEqual(self.facts['recruitment_status'],'招募中')
        self.assertIn('2023-11-24',[m['date'] for m in self.facts['milestones'] if m['kind']=='FIRST_PARTICIPANT_ENROLLED'])
        self.assertFalse(any(m['kind']=='TRIAL_COMPLETED' for m in self.facts['milestones']))
        self.assertTrue(self.facts['sites'])
        self.assertTrue(self.facts['investigators'])

    def test_applicant_row_numbers_are_not_companies(self):
        self.assertNotIn('1', self.facts['sponsors'])
        old=facts.structured_detail((ROOT/'tests/fixtures/nmpa/saved-detail.html').read_text(),'CTR20221481')
        self.assertEqual(len(old['sponsors']),1)
        self.assertEqual(next(m['date'] for m in old['milestones'] if m['kind']=='TRIAL_TERMINATED'),'2026-02-25')

    def test_formatting_listing_movement_and_table_order_do_not_make_events(self):
        previous={'status':'进行中 招募中','drug_name':'EP-9001A注射液','sites':self.facts['sites']}
        current=copy.deepcopy(self.facts)
        current['sites'].reverse()
        current['listing_page']=999
        current['advertised_total_records']=40000
        self.assertEqual(facts.changes(previous,current),{})

    def test_only_shared_substantive_changes_have_observation_intervals(self):
        previous={'status':'进行中 招募中'}
        current=copy.deepcopy(self.facts); current['status']='已完成'
        events=facts.event_facts('CTR20231998',previous,current,'2026-10-01T12:00:00.000000Z','2026-10-16T12:00:00.000000Z')
        change=next(e for e in events if e['action']=='TRIAL_CHANGE_OBSERVED')
        self.assertEqual(set(change['changes']),{'status'})
        self.assertEqual(change['date_basis'],'observed_change_not_actual_change_date')
        self.assertEqual(change['observation_interval']['after'],'2026-10-01T12:00:00.000000Z')

    def test_202_acceptance_requires_correct_complete_unblocked_trial(self):
        self.assertTrue(facts.valid_detail(self.document,'CTR20231998'))
        self.assertFalse(facts.valid_detail(self.document,'CTR20242640'))
        self.assertFalse(facts.valid_detail('<table class="searchDetailTable"></table>','CTR20231998'))
        self.assertFalse(facts.valid_detail('验证码'+self.document,'CTR20231998'))

    def test_private_sponsor_is_missing_data_not_a_guessed_company(self):
        document=self.document.replace('成都优洛生物科技有限公司','企业选择不公示')
        result=facts.structured_detail(document,'CTR20231998')
        self.assertEqual(result['sponsors'],[])
        self.assertIn('sponsors',result['missing_core_fields'])
        self.assertTrue(facts.valid_detail(document,'CTR20231998'))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.db=worker.registry(self.root/'registry.sqlite3');self.addCleanup(self.db.close)
        self.store=LocalStore(self.root/'store');self.settings=StorageSettings()
        self.config={'job_id':'nmpa-test','window_start':'2021-01-01T00:00:00Z','scope_end':'2026-10-16T12:00:00Z',
            'max_provider_requests_per_day':8,'email_topic_arn':'arn:topic','email_recipient':'owner@example.com'}
        self.parent={'record_id':'rec_'+'1'*64,'observation_id':'obs_'+'2'*64,'payload':{'source_evidence':[]}}

    def test_capture_commits_schema_valid_details_and_distinct_event_types(self):
        at='2026-10-15T12:00:00.000000Z'
        trial=('CTR20231998',json.dumps(self.parent),at,json.dumps({'status':'进行中 招募中'}),at,0)
        client=Mock(evidence=[])
        client.rendered.return_value=FIXTURE.read_text()
        universe=load_json(ROOT/'examples/research-contract/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
        records,refs,manifest=worker.capture(self.store,self.settings,universe,taxonomy,self.config,self.db,client,trial,'baseline')
        self.assertTrue(refs)
        self.assertTrue(all(not validate_record(r,universe) for r in records))
        self.assertEqual(records[0]['payload']['record_type'],'clinical_trial')
        actions=[r['payload']['data']['action'] for r in records[1:]]
        self.assertIn('FIRST_OBSERVED',actions)
        self.assertIn('FIRST_PARTICIPANT_ENROLLED',actions)
        self.assertNotIn('TRIAL_CHANGE_OBSERVED',actions)
        self.assertEqual(records[0]['company_ids'],[])
        again=worker.capture(self.store,self.settings,universe,taxonomy,self.config,self.db,client,trial,'baseline')
        self.assertEqual([r['observation_id'] for r in again[0]],[r['observation_id'] for r in records])
        self.assertEqual(client.rendered.call_count,1)

    def test_budget_accounts_for_all_four_provider_retry_slots(self):
        self.assertTrue(worker.reserve(self.db,self.config))
        self.assertTrue(worker.reserve(self.db,self.config))
        self.assertFalse(worker.reserve(self.db,self.config))

    def test_saved_cumulative_evidence_cannot_seed_the_wrong_trial(self):
        ref1={'key':'evidence/wrong','sha256':hashlib.sha256((ROOT/'tests/fixtures/nmpa/saved-detail.html').read_bytes()).hexdigest(),
              'source_url':'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no=CTR20221481'}
        ref2={'key':'evidence/right','sha256':hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
              'source_url':'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no=CTR20231998'}
        write_checked(self.store,ref1['key'],(ROOT/'tests/fixtures/nmpa/saved-detail.html').read_bytes())
        write_checked(self.store,ref2['key'],FIXTURE.read_bytes())
        parent={**self.parent,'source':'nmpa_trials','dataset':'research_records','source_record_id':'CTR20231998',
                'ingested_at':'2026-10-15T12:00:00.000000Z','payload':{'data':{},'source_evidence':[ref2,ref1]}}
        raw=(json.dumps(parent)+'\n').encode();sha=hashlib.sha256(raw).hexdigest();write_checked(self.store,'batch',raw)
        path=self.root/'index.sqlite3'
        with sqlite3.connect(path) as index:
            index.execute('CREATE TABLE batches(key TEXT,sha256 TEXT,dataset TEXT,records INTEGER,source TEXT)')
            index.execute('INSERT INTO batches VALUES (?,?,?,?,?)',('batch',sha,'research_records',1,'nmpa_trials'))
        worker.discover(self.store,self.db,path,10)
        baseline=json.loads(self.db.execute('SELECT baseline FROM trials').fetchone()[0])
        self.assertEqual(baseline['drug_name'],'EP-9001A注射液')

    def test_completion_email_waits_for_inventory_and_pending_trials(self):
        sns=Mock()
        for complete,pending in ((False,0),(True,1)):
            state={'inventory_complete':complete,'remaining_input_batches':0,'pending_trials':pending}
            worker.notify(self.store,self.db,self.config,state,sns,Mock())
        sns.publish.assert_not_called()

    def test_completion_requires_verified_athena_rows_and_sends_once(self):
        self.db.execute("INSERT INTO trials(registration,parent,first_seen,baseline,baseline_at,status,output_batches) VALUES (?,?,?,?,?,'done',?)",
            ('CTR20231998',json.dumps(self.parent),'2026-10-15', '{}','2026-10-15',json.dumps([{'key':'output','records':3}])))
        self.db.commit()
        index=MagicMock();index.__enter__.return_value=index
        index.execute.return_value.fetchone.return_value=(1,)
        sns=Mock();sns.get_paginator.return_value.paginate.return_value=[{'Subscriptions':[{
            'Protocol':'email','Endpoint':'owner@example.com','SubscriptionArn':'arn:confirmed'}]}]
        sns.publish.return_value={'MessageId':'sent'}
        state={'inventory_complete':True,'remaining_input_batches':0,'pending_trials':0}
        with patch.object(worker.sqlite3,'connect',return_value=index),patch('committed_data_athena.query',return_value={'rows':[['2']]}):
            with self.assertRaisesRegex(ValueError,'count_mismatch'):
                worker.notify(self.store,self.db,self.config,state,sns,Mock())
        sns.publish.assert_not_called()
        with patch.object(worker.sqlite3,'connect',return_value=index),patch('committed_data_athena.query',return_value={'rows':[['3']]}):
            result=worker.notify(self.store,self.db,self.config,state,sns,Mock())
            worker.notify(self.store,self.db,self.config,result,sns,Mock())
        self.assertEqual(sns.publish.call_count,1)
        self.assertEqual(result['notification_message_id'],'sent')


if __name__=='__main__':
    unittest.main()
