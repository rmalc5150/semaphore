import io
import json
import unittest
from datetime import date
from unittest.mock import Mock, patch
from specialist_authenticated import fetch, request, scopes
from specialist_inputs import item
from regulatory_collection import SourceIssue

class SamTests(unittest.TestCase):
    def job(self):
        return {'adapter':'sam_gov','parameters':{'url':'https://api.sam.gov/opportunities/v2/search','start':'2026-10-01','end':'2026-10-13'}}

    @patch('specialist_authenticated.sam_request_budget')
    @patch('specialist_authenticated.request')
    def test_page_index_resume_and_terminal(self, req, budget):
        req.return_value={'offset':0,'limit':1000,'totalRecords':1001,'opportunitiesData':[
            {'noticeId':str(i),'postedDate':'2026-10-09'} for i in range(1000)]}
        rows,cursor=fetch(Mock(),self.job(),None,item)
        self.assertEqual(cursor,'1')
        req.return_value={'offset':1,'limit':1000,'totalRecords':1001,'opportunitiesData':[{'noticeId':'last','postedDate':'2026-10-10'}]}
        rows,cursor=fetch(Mock(),self.job(),cursor,item)
        self.assertEqual(req.call_args.args[3]['offset'],1)
        self.assertIsNone(cursor)
        self.assertEqual(rows[0]['id'],'last')

    @patch('specialist_authenticated.sam_request_budget')
    @patch('specialist_authenticated.request')
    def test_empty_scope_and_invalid_pages(self, req, budget):
        req.return_value={'offset':0,'limit':1000,'totalRecords':0,'opportunitiesData':[]}
        self.assertEqual(fetch(Mock(),self.job(),None,item),([],None))
        req.return_value['totalRecords']=10
        with self.assertRaisesRegex(SourceIssue,'missing_page'):fetch(Mock(),self.job(),None,item)
        req.return_value['opportunitiesData']=[{'noticeId':'a','postedDate':'2021-01-01'}]
        with self.assertRaisesRegex(SourceIssue,'record_scope'):fetch(Mock(),self.job(),None,item)

    def test_key_removed_from_evidence_and_records(self):
        response=io.BytesIO(json.dumps({'links':[{'href':'https://example.org/?api_key=test-secret'}]}).encode())
        client=Mock()
        with patch('specialist_authenticated.credentials',return_value=('test-secret',)), patch('specialist_authenticated.build_opener') as opener:
            opener.return_value.open.return_value=response
            data=request(client,'sam-gov','https://api.sam.gov/opportunities/v2/search')
        self.assertNotIn('test-secret',json.dumps(data))
        self.assertNotIn(b'test-secret',client.save.call_args.args[0])

    def test_monthly_windows(self):
        result=list(scopes({'adapter':'sam_gov','api':'example','coverage_note':'API scope only'},date(2021,1,1),date(2021,3,1),'historical'))
        self.assertEqual(len(result),2)
        self.assertEqual(result[0][2]['end'],'2021-02-01')

    def test_daily_budget_enforced_and_persisted(self):
        import tempfile
        from pathlib import Path
        from specialist_authenticated import sam_request_budget
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'reports').mkdir()
            with patch('research_contract.ROOT',root), patch('specialist_authenticated.load_json',return_value={'daily_request_budget':2,'hourly_request_budget':2}):
                sam_request_budget();sam_request_budget()
                with self.assertRaisesRegex(SourceIssue,'sam_daily_request_budget'):sam_request_budget()
            self.assertEqual(len(json.loads((root/'reports/sam-gov-quota.json').read_text())['calls']),2)

    def test_scheduled_both_modes(self):
        from specialist_plan import jobs
        from research_contract import ROOT,load_json
        plan=load_json(ROOT/'config/specialist-inputs.json')
        plan['sources']=[s for s in plan['sources'] if s['source_id']=='S41']
        universe={'companies':[]}
        for mode in ('daily','historical'):
            rows=list(jobs(plan,universe,mode,date(2026,10,13)))
            self.assertTrue(rows)
            self.assertTrue(all(r['source']=='sam_gov_opportunities' for r in rows))
        self.assertEqual(rows[0]['parameters']['start'],'2021-01-01')
