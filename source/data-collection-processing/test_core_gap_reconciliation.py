import copy
import unittest
from constellation.gaps import current_core_window
from constellation.gaps import capacity_wait
from research_contract import digest

class CoreGapReconciliationTests(unittest.TestCase):
    def test_bundled_crl_pdf_keeps_distinct_letters_across_pages(self):
        from datetime import date
        from regulatory_sources import FDA
        from test_regulatory_collection import FakeClient
        first={'letter_type':'COMPLETE RESPONSE','letter_date':'12/03/2019',
               'file_name':'bundled.pdf','application_number':['NDA 123']}
        second={**first,'letter_date':'12/20/2019'}
        def page(row):return {'meta':{'results':{'total':2}},'results':[row]}
        client=FakeClient([page(first),page(second)])
        one,state,_=FDA().page(client,date(2019,12,1),date(2020,1,1),'historical',{'stage':'crls'},1)
        two,_,done=FDA().page(client,date(2019,12,1),date(2020,1,1),'historical',state,1)
        self.assertTrue(done);self.assertNotEqual(one[0]['id'],two[0]['id'])
        self.assertEqual(one[0]['data']['file_name'],two[0]['data']['file_name'])
    def test_capacity_wait_is_backlog_but_provider_denial_remains_actionable(self):
        window={'scope':'copernicus_era5_era5_land|C075|specialist_historical|location','status':'failed','reason':'copernicus_queue_wait'}
        self.assertTrue(capacity_wait(window))
        self.assertFalse(capacity_wait({**window,'reason':'source_http_403'}))
        self.assertFalse(capacity_wait({**window,'scope':'fda|stream|configured_legacy_scope'}))
    def setUp(self):
        self.window={'scope':'fda|'+'a'*64+'|configured_legacy_scope','start':'2016-02-01T00:00:00','end':'2016-03-01T00:00:00','status':'failed','reason':'invalid_fda_action_date'}
        self.task={'source':'fda_openfda','dataset':'research_records','mode':'historical','window':{'start':'2016-02-01T00:00:00Z','end':'2016-03-01T00:00:00Z'}}
        self.outcome={'source':'fda','mode':'historical','start':'2016-02-01','end':'2016-03-01','status':'complete','manifest':'manifests/collection_runs/test/final.json'}
        self.manifest={'task':self.task,'task_id':'task_'+digest(self.task),'status':'complete','exhausted':True}
        self.head={'task':self.task,'terminal_history':[self.outcome['manifest']]}
    def test_reconciliation_needs_no_collector_module(self):
        import sys
        from unittest.mock import patch
        from constellation.gaps import digest as standalone_digest
        self.assertEqual(standalone_digest({'text': '公告', 'nested': [None, True, 3]}),
                         digest({'nested': [None, True, 3], 'text': '公告'}))
        with patch.dict(sys.modules, {'research_contract': None}):
            self.assertEqual(current_core_window(self.window,self.outcome,self.manifest,self.head)['status'], 'complete')

    def test_exact_committed_repair_supersedes_retained_error(self):
        result=current_core_window(self.window,self.outcome,self.manifest,self.head)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(self.window['status'],'failed')
    def test_another_month_source_or_uncommitted_run_cannot_clear_gap(self):
        cases=[]
        out=copy.deepcopy(self.outcome);out['start']='2016-03-01';cases.append((out,self.manifest,self.head))
        m=copy.deepcopy(self.manifest);m['task']['source']='clinicaltrials_gov';cases.append((self.outcome,m,self.head))
        h=copy.deepcopy(self.head);h['terminal_history']=[];cases.append((self.outcome,self.manifest,h))
        m=copy.deepcopy(self.manifest);m['exhausted']=False;cases.append((self.outcome,m,self.head))
        for args in cases:self.assertIs(current_core_window(self.window,*args),self.window)

if __name__=='__main__':unittest.main()
