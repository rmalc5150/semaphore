from contextlib import redirect_stdout
import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock

class ExpansionTests(unittest.TestCase):
    def test_worker_scheduler_seeds_only_its_historical_source_and_keeps_legacy_state(self):
        import specialist_inputs as module
        from collection_storage import LocalStore,write_json
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);store=LocalStore(str(root/'store'))
            job={'source':'cpsc_recalls','source_id':'S50','adapter':'cpsc','mode':'historical','start':'2016-01-01','end':'2017-01-01','parameters':{'url':'https://www.saferproducts.gov/'},'coverage_note':'fixture'}
            old={'jobs':{'historical':{'job':job,'status':'failed'},'daily':{'job':{**job,'mode':'daily'},'status':'failed'},'other':{'job':{**job,'source':'other'},'status':'failed'}}}
            key='operations/specialists/scheduler/historical.json';write_json(store,key,old)
            before=store.get(key).body
            env={'CONSTELLATION_ROLE':'worker','CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX':'constellation-backfill/test-scheduler','CONSTELLATION_SPECIALIST_PUBLICATION_PREFIX':'constellation-backfill/test-publication/','CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX':'constellation-backfill/test-discovery/','CONSTELLATION_OPERATION_RECEIPT_PREFIX':'constellation-backfill/legacy-operation-receipts/test'}
            settings=Mock(store=Mock(return_value=store))
            plan={'sources':[{'source':'cpsc_recalls','enabled':True,'historical':True,'adapter':'cpsc'}]}
            def load(path):return plan if 'specialist-inputs' in str(path) else {'companies':[]} if 'universe' in str(path) else {}
            with patch.dict(os.environ,env),patch.object(module,'ROOT',root),patch.object(module,'OUT',root/'reports'),patch.object(module,'load_json',side_effect=load),patch.object(module.StorageSettings,'load',return_value=settings),patch('specialist_plan.jobs',return_value=[job]),patch.object(module,'collect',return_value={'status':'complete','records':0,'manifest':'manifests/fixture'}),patch.object(module,'discover_children'),patch('sys.argv',['specialist_inputs.py','--mode','historical','--source','cpsc_recalls','--publish','0']),redirect_stdout(io.StringIO()):
                module.main()
            self.assertEqual(store.get(key).body,before)
            state=json.loads(store.get('constellation-backfill/test-scheduler/historical.json').body)
            self.assertFalse(any(v.get('job',{}).get('mode')=='daily' for v in state['jobs'].values()))
            self.assertFalse(any(v.get('job',{}).get('source')=='other' for v in state['jobs'].values()))
            self.assertTrue(list((root/'store/constellation-backfill/test-publication').glob('*.json')))
    def test_worker_refuses_daily_or_inline_publication(self):
        import specialist_inputs as module
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'worker','CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX':'private'}),patch('sys.argv',['specialist_inputs.py','--mode','daily','--source','cpsc_recalls','--publish','0']),patch.object(module.StorageSettings,'load'),patch.object(module,'load_json',return_value={}),tempfile.TemporaryDirectory() as folder,patch.object(module,'ROOT',Path(folder)),redirect_stdout(io.StringIO()),patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit):module.main()

if __name__=='__main__':unittest.main()
