from datetime import datetime,timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch
from research_contract import ROOT,digest
import eodhd_daily_cohort as daily

class CohortTests(unittest.TestCase):
    def test_resumed_prefixes_removed_but_independent_refreshes_retained(self):
        u={'version':'test'}; t={'version':'taxonomy'}
        task={'source':'eodhd','dataset':'company_profiles',
              'universe_hash':digest(u),'taxonomy_hash':digest(t)}
        manifests={}
        relative='manifests/collection_runs/source=eodhd/dataset=company_profiles/'
        for run,pages in [('old',[{'run_id':'old','sequence':0}]),
                          ('resumed',[{'run_id':'old','sequence':0},{'run_id':'new','sequence':1}]),
                          ('refresh',[{'run_id':'refresh','sequence':0}])]:
            manifests[relative+run+'/final.json']={'status':'partial','task':task,'pages':pages}
        store=Mock();store.get.side_effect=lambda key:SimpleNamespace(body=json.dumps(manifests[key]).encode())
        store.client.get_paginator.return_value.paginate.return_value=[{'Contents':[
            {'Key':'data/'+key} for key in manifests]}]
        result=daily.manifest_keys(store,SimpleNamespace(s3_prefix='data',s3_bucket='bucket'),u,t)
        self.assertEqual(result,[relative+'refresh/final.json',relative+'resumed/final.json'])
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.day=datetime.now(timezone.utc).date().isoformat()
        self.args=SimpleNamespace(storage_config=ROOT/'config/collection-storage.s3.json',config=ROOT/'config/eodhd-universe.json',
          universe=ROOT/'examples/sec-filings/universe.json',taxonomy=ROOT/'config/sectors.v1.json',report_dir=self.root,
          inventory_manifest='inventory',max_profiles=8800,workers=4,top_up=True)
        self.client=Mock();self.client.quota.status.return_value={'groups':{'profiles':87000}}
    def run_patched(self):
        with patch.object(daily.StorageSettings,'load',return_value=Mock()),patch.object(daily.EODHDClient,'configured',return_value=self.client),\
             patch.object(daily,'quota_batch_size',return_value=(8800,{})),patch.object(daily,'manifest_keys',return_value=[]),\
             patch.object(daily,'make_plan',return_value={'plan_id':'new'}) as plan,\
             patch.object(daily,'collect',return_value={'status':'complete','records':100}) as collect:
            result=daily.run(self.args)
        return result,plan,collect
    def test_completed_today_gets_separate_bounded_top_up(self):
        (self.root/f'eodhd-auto-plan-{self.day}.json').write_text('{"plan_id":"old"}')
        (self.root/f'eodhd-auto-result-{self.day}.json').write_text('{"status":"complete"}')
        result,plan,_=self.run_patched()
        self.assertEqual(plan.call_args.args[3],100)
        self.assertTrue(result['plan_file'].endswith('-0002.json'))
    def test_previous_day_partial_resumes_exact_plan_before_new_cohort(self):
        path=self.root/'eodhd-auto-plan-2020-01-01.json';path.write_text('{"plan_id":"unfinished"}')
        result,plan,collect=self.run_patched()
        plan.assert_not_called();self.assertEqual(collect.call_args.args[3]['plan_id'],'unfinished')
        self.assertEqual(result['plan_file'],str(path))
        self.assertEqual(collect.call_args.kwargs['max_pages'],8)

if __name__=='__main__':unittest.main()
