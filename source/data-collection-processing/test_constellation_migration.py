"""Check credential coverage, fixed routes, and separation of daily workloads."""
from contextlib import redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from contextlib import contextmanager
import pymysql

from constellation.build_access_inventory import build,GROUPS
from constellation.legacy_routes import manifest,route,specification,validate_spec
from constellation.shared_limits import provider


class MigrationTests(unittest.TestCase):
    def test_pretty_json_output_cannot_fake_or_break_checkpoint_verification(self):
        from constellation.legacy_worker import checkpoint_events
        body=b'"ordinary string"\n123\nnull\n[]\n{"stage":"s3_checkpoint_verified","unit":"other","run_id":"wrong"}\n{"stage":"s3_checkpoint_verified","unit":"test","run_id":"right"}\n'
        self.assertEqual(checkpoint_events(body,'test'),[{'stage':'s3_checkpoint_verified','unit':'test','run_id':'right'}])

    def test_worker_kind_like_pattern_is_safely_parameterized(self):
        from constellation.control import Control
        connection=pymysql.connect(defer_connect=True);connection.server_status=0
        driver=connection.cursor()
        cursor=Mock()
        cursor.execute.side_effect=lambda sql,args=None:driver.mogrify(sql,args)
        cursor.fetchone.return_value={'job_id':'a'*64,'attempts':0}
        @contextmanager
        def db():yield cursor
        control=Control.__new__(Control);control.db=db
        for enabled in (False,True):
            control.get=Mock(return_value={'enabled':enabled,'pilot_job_ids':['a'*64],'stop_after_epoch':9999999999})
            for kind in ('raw','legacy'):
                self.assertIsNotNone(control.claim_next('test-worker',kind=kind))

    def test_all_catalog_rows_have_access_actions_and_shared_credentials(self):
        rows=build();self.assertEqual([r['catalog_entry'] for r in rows],list(range(1,159)))
        self.assertTrue(all(r['action'] and r['reference'] for r in rows))
        by={r['catalog_entry']:r for r in rows}
        self.assertEqual(by[2]['credential_group'],by[3]['credential_group'])
        self.assertEqual(by[40]['credential_group'],by[64]['credential_group'])
        self.assertEqual(sum(g[2]=='obtain' for g in GROUPS),19)
        self.assertEqual(by[121]['credential_group'],'opensupplyhub')
        self.assertEqual(by[12]['access_status'],'paused_stored')

    def test_no_daily_commands_in_historical_route_catalog(self):
        rows=manifest()['routes']
        self.assertEqual(sum(r['route_kind']=='historical_only' for r in rows),24)
        self.assertEqual(sum(r['route_kind']=='split_historical' for r in rows),5)
        for row in rows:
            args=row['argv']
            for flag in ('--mode','--lane'):
                if flag in args:self.assertNotEqual(args[args.index(flag)+1],'daily')
            self.assertNotIn('collect_daily.py',args)
            if not row['execution_enabled']:self.assertTrue(row['remaining_requirements'])

    def test_queue_cannot_supply_a_shell_command_or_alter_scope(self):
        row=route('constellation-core-migration-probe.service')
        spec=specification(row,1);validate_spec(spec)
        for change in ({'command':'rm -rf /'}, {'unit':'unknown.service'}, {'route_sha256':'0'*64}):
            altered={**spec,'parameters':{**spec['parameters'],**change}}
            with self.subTest(change=change),self.assertRaises(ValueError):validate_spec(altered)
        with self.assertRaises(ValueError):validate_spec({**spec,'start':'2015-01-01'})

    def test_sec_subdomains_share_one_pacing_group(self):
        self.assertEqual(provider('https://www.sec.gov/Archives/'),provider('https://data.sec.gov/submissions/'))
        self.assertEqual(provider('https://api.fda.gov/'),provider('https://datadashboard.fda.gov/'))

    def test_conference_daily_cli_never_calls_history(self):
        import conference_collection as module
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'ROOT',Path(folder)),patch.object(module,'load_json',return_value={}),patch.object(module.StorageSettings,'load',return_value=Mock()),patch.object(module,'advance',return_value={'status':'complete'}) as advance,redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--mode','daily']),0)
        self.assertEqual([c.args[4] for c in advance.call_args_list],['daily'])

    def test_people_daily_preserves_daily_archive_but_not_history(self):
        import people_collection_operations as module
        with patch.object(module.subprocess,'run',return_value=Mock(returncode=0)) as run,redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--lane','daily']),0)
        calls=[c.args[0] for c in run.call_args_list]
        self.assertEqual(len(calls),3)
        archives=next(c for c in calls if 'personnel_archive.py' in c)
        self.assertEqual(archives[archives.index('--mode')+1],'daily')
        with patch.object(module.subprocess,'run',return_value=Mock(returncode=0)) as run,redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--lane','historical']),0)
        self.assertEqual(len(run.call_args_list),1)
        self.assertIn('historical',run.call_args.args[0])

    def test_patent_daily_only_keeps_overlap_and_excludes_history(self):
        import patent_prosecution_operations as module
        today=module.datetime.now(module.timezone.utc).date().isoformat()
        instance=Mock(identity='test')
        instance.run.return_value={'status':'complete'}
        config={'storage_config':'storage.json','universe':'universe.json','taxonomy':'taxonomy.json'}
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'ROOT',Path(folder)),patch.object(module,'load_json',return_value=config),patch.object(module.StorageSettings,'load',return_value=Mock()),patch.object(module,'Operations',return_value=instance),patch.object(module,'load_stored',return_value=({'through':today,'complete':True},None)),redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['daily-only']),0)
        self.assertEqual({call.args[1] for call in instance.run.call_args_list},{'daily'})

    def test_patent_historical_only_retains_older_reconciliation(self):
        import patent_prosecution_operations as module
        instance=Mock(identity='test');instance.run.return_value={'status':'complete'}
        config={'storage_config':'storage.json','universe':'universe.json','taxonomy':'taxonomy.json'}
        with tempfile.TemporaryDirectory() as folder,patch.object(module,'ROOT',Path(folder)),patch.object(module,'load_json',return_value=config),patch.object(module.StorageSettings,'load',return_value=Mock()),patch.object(module,'Operations',return_value=instance),patch.object(module,'load_stored',return_value=(None,None)),patch.object(module,'write_json'),redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['historical-only']),0)
        self.assertEqual({call.args[1] for call in instance.run.call_args_list},{'historical','reconcile'})


if __name__=='__main__':unittest.main()
