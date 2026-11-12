from contextlib import contextmanager,nullcontext
from datetime import datetime,timedelta,timezone
import io,json,unittest
from unittest.mock import Mock,patch
from constellation.gaps import build
from constellation.coverage_scope import specialist_scope
from constellation.daily_raw import page
from constellation.sources import VERSION
import time

class FakeControl:
    config={'bucket':'fixture','prefix':'research-data/constellation-backfill'}
    def __init__(self,reports,final=None):
        self.jobs=[];objects={};prefix='s3://fixture/research-data/constellation-backfill/legacy-operation-receipts/'
        for i,report in enumerate(reports):
            uri=prefix+str(i)+'.json';objects[uri.removeprefix('s3://fixture/')]=report
            self.jobs.append({'job_id':str(i),'source_key':'legacy:fixture','status':'succeeded','spec_json':'{}','updated_at':i,
                'result_json':json.dumps({'coverage_windows':[{'scope':'fixture|S|specialist_historical','evidence_uri':uri}]})})
        if final:objects['research-data/manifests/collection_runs/final.json']=final
        self.s3=Mock();self.s3.get_object.side_effect=lambda Bucket,Key:{'Body':io.BytesIO(json.dumps(objects[Key]).encode())}
    @contextmanager
    def db(self):
        cursor=Mock();cursor.fetchall.return_value=self.jobs;yield cursor

def outcome(company,status):
    return {'source':'fixture','source_id':'S','job_id':company,'start':'2016-01-01','end_exclusive':'2016-01-08','status':status,'job':{'parameters':{'cik':company,'start':'2016-01-01','end':'2016-01-08'}}}

class PublicOperationsTests(unittest.TestCase):
    def test_epo_patent_lookup_failure_is_not_a_calendar_gap(self):
        row=outcome('patent','failed');row['source']='epo_ops_patent_legal_events'
        row['job']['adapter']='additional_epo'
        control=FakeControl([{'outcomes':[row]}])
        self.assertEqual(build(control)['flagged_gaps'],0)
    def test_paused_public_source_does_not_read_or_fetch(self):
        from public_source_capture import run
        with patch('public_source_capture.boto3.client') as client:
            with self.assertRaisesRegex(ValueError, 'public_source_paused'):
                run({'source':'nice_technology_appraisals','enabled':False}, 'daily')
        client.assert_not_called()

    def test_memory_pressure_defers_claim_without_taking_a_lease(self):
        from constellation.control import Control
        control=Control.__new__(Control);control.config={'worker_pool':{'admission_memory_high_gib':4.5}};control.get=Mock()
        with patch.dict('os.environ',{'CONSTELLATION_ROLE':'worker'}),patch('pathlib.Path.exists',return_value=True),patch('pathlib.Path.read_text',return_value=str(5*1024**3)):
            self.assertIsNone(control.claim_next('fixture',kind='public'))
        control.get.assert_not_called()
    def test_lightweight_workers_can_only_claim_public_artifact_routes(self):
        from constellation.control import Control
        control=Control.__new__(Control);control.get=Mock(return_value={'enabled':True,'stop_after_epoch':time.time()+3600})
        cursor=Mock();cursor.fetchone.return_value=None
        @contextmanager
        def database():yield cursor
        control.db=database
        self.assertIsNone(control.claim_next('fixture',kind='public'))
        sql,values=cursor.execute.call_args.args
        self.assertIn('legacy:constellation-public-%',values);self.assertIn('source_key LIKE %s',sql);self.assertNotIn('source_key NOT LIKE %s',sql)
    def test_another_company_cannot_clear_a_gap(self):
        result=build(FakeControl([{'outcomes':[outcome('company_a','failed')]},{'outcomes':[outcome('company_b','complete')]}]))
        self.assertEqual(result['flagged_gaps'],1)
    def test_old_page_budget_receipt_is_progress_not_a_gap(self):
        item={**outcome('company_a','partial'),'manifest':'manifests/collection_runs/final.json'}
        result=build(FakeControl([{'outcomes':[item]}],{'reason_code':'page_budget'}))
        self.assertEqual(result['gaps'],[])
    def test_same_company_has_stable_scope_across_date_windows(self):
        first=outcome('company_a','failed');second=outcome('company_a','failed');second['job']['parameters']['start']='2017-01-01'
        self.assertEqual(specialist_scope(first),specialist_scope(second))
    def test_daily_quota_wait_preserves_cursor_and_makes_no_request(self):
        end=datetime.now(timezone.utc).date();start=end-timedelta(days=1)
        spec={'source_key':'usgs_earthquakes','dataset':'earthquake_events','geography':'global','start':start.isoformat(),'end':end.isoformat(),'edition':'current_retrieval','extractor_version':VERSION,'parameters':{}}
        state={'cursor':42,'seen':['saved'],'record_count':1}
        with patch('constellation.daily_raw.connection',return_value=nullcontext()),patch('constellation.daily_raw.reserve',return_value=False),patch('constellation.daily_raw.requests.get') as fetch:
            result=page(Mock(),'usgs_earthquakes',spec,state)
        self.assertEqual(result['status'],'deferred_not_a_gap');self.assertEqual(result['cursor'],42);fetch.assert_not_called()

if __name__=='__main__':unittest.main()
