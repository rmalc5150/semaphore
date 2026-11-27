"""Regression checks for stale grants, worker paths and incompatible cursors."""
import copy
from datetime import date
import json
import os
import unittest
from unittest.mock import patch

from test_news_operations import OperationsTests
from test_regulatory_collection import CollectionTests, FakeClient
import regulatory_collection as core
import regulatory_sources as sources
from eia_enrichment import historical_metadata_key

class NewsGrantTests(OperationsTests):
    def test_archive_grant_recovers_old_daily_without_resetting_stream(self):
        identity = self.runner.identity
        seen=[]
        def capture(*args):
            seen.append(args[4]);return {'status':'partial','reason':'page_limit'}
        with patch('news_operations.collect', side_effect=capture):
            self.runner.window('finlight', date(2026,10,10), 'daily', None, self.runner.daily)
        self.assertEqual(seen[0]['providers']['finlight']['historical_access'],'observed_archive')
        self.assertEqual(self.runner.daily['providers']['finlight']['historical_access'],'recent_only')
        self.assertEqual(self.runner.identity,identity)
        self.assertEqual(seen[0]['providers']['finlight']['max_requests_per_day'],40)

    def test_disabled_or_wrong_account_grant_does_not_expand_access(self):
        from finlight_backfill import setup
        control, archive, prefix = setup()
        for enabled, wrong_account in [(False,False),(True,True)]:
            grant=copy.deepcopy(archive)
            if wrong_account:grant['secret_id']='different-account'
            with patch('finlight_backfill.setup', return_value=({**control,'enabled':enabled},grant,prefix)), patch('news_operations.collect', return_value={'status':'partial'}) as capture:
                self.runner.window('finlight',date(2026,10,10),'daily',None,self.runner.daily)
                self.assertEqual(capture.call_args.args[4]['providers']['finlight']['historical_access'],'recent_only')

class StoragePathTests(unittest.TestCase):
    def test_daily_worker_uses_approved_metadata_namespace(self):
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'worker'},clear=True):
            self.assertEqual(historical_metadata_key('operations/eia-enrichment/archive-heads/x.json'),'constellation-backfill/source-metadata/operations/eia-enrichment/archive-heads/x.json')
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(historical_metadata_key('operations/eia-enrichment/archive-heads/x.json'),'operations/eia-enrichment/archive-heads/x.json')

class FDACursorTests(CollectionTests):
    def test_repaired_contract_does_not_resume_old_fda_cursor(self):
        args=(self.store,self.settings,self.universe,self.taxonomy,'fda',self.start,self.end,'historical',sources.FDA())
        empty={'meta':{'results':{'total':0}},'results':[]}
        with patch.object(sources.FDA,'version',None):
            old=core.collect(*args,client=FakeClient([empty]),max_pages=1)
        client=FakeClient([empty,empty])
        new=core.collect(*args,client=client,max_pages=2)
        self.assertEqual(new['status'],'complete')
        self.assertNotEqual(new['manifest'],old['manifest'])
        self.assertIn('drugsfda.json',client.calls[0][0][0])
        self.assertIsNotNone(self.store.get(old['manifest']))

if __name__=='__main__':unittest.main()
