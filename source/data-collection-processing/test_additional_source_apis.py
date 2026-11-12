import json,unittest
from datetime import date
from unittest.mock import Mock,patch
from additional_source_apis import fetch,get_json,validated_url
from additional_source_plan import scopes
from regulatory_collection import SourceIssue
from specialist_inputs import item

class AdditionalTests(unittest.TestCase):
    def job(self,kind,start='2016-01-01',end='2016-02-01',**parameters):return {'adapter':'additional_'+kind,'start':start,'end':end,'parameters':parameters}
    def test_secrets_are_removed_from_payload_and_evidence_url(self):
        secret='test-secret-marker-never-persist'
        response=Mock(status_code=200,headers={'Content-Type':'application/json'},links={})
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.iter_content.return_value=[json.dumps({'echo':secret,'records':[]}).encode()]
        client=Mock()
        with patch('additional_source_apis.requests.get',return_value=response),patch('additional_source_apis.credentials',return_value={'FRED':secret}),patch('constellation.shared_limits.admit'):
            data,_=get_json(client,'https://api.stlouisfed.org/fred/series',{'series_id':'GDP'},'FRED')
        self.assertNotIn(secret,client.save.call_args.args[0].decode());self.assertNotIn(secret,client.save.call_args.args[1]);self.assertEqual(data['echo'],'[REDACTED]')
    def test_provider_error_is_not_an_empty_page(self):
        response=Mock(status_code=403,headers={},links={});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=[b'{"error":"denied"}']
        client=Mock()
        with patch('additional_source_apis.requests.get',return_value=response),patch('constellation.shared_limits.admit'),self.assertRaises(SourceIssue):get_json(client,'https://zenodo.org/api/records')
        client.save.assert_called_once()
    def test_pagination_cannot_leave_provider_or_downgrade_https(self):
        for url in ('http://api.datacite.org/dois','https://evil.example/x','https://u:p@api.datacite.org/dois','https://api.datacite.org:444/x'):
            with self.assertRaises((SourceIssue,ValueError)):validated_url(url,'api.datacite.org')
    def test_biorxiv_cursor_uses_actual_page_length_not_assumed_hundred(self):
        records=[{'doi':'10.1101/'+str(i),'version':'1','date':'2016-01-02'} for i in range(30)]
        with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':'35'}],'collection':records},None)):
            client=Mock();client.get.return_value=b'%PDF-1.4\nfixture\n%%EOF';client.evidence=[{'key':'fixture.pdf'}]
            rows,cursor=fetch(client,self.job('biorxiv',repository='biorxiv'),None,item)
        self.assertEqual(len(rows),20);self.assertEqual(json.loads(cursor)['offset'],20)
        self.assertEqual(client.get.call_count,20)
    def test_changed_total_cannot_complete_old_offset(self):
        with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':36}],'collection':[]},None)),self.assertRaises(SourceIssue):
            fetch(Mock(),self.job('biorxiv',repository='biorxiv'),json.dumps({'offset':30,'total':35}),item)
    def test_nasa_missing_value_is_null_not_zero(self):
        payload={'properties':{'parameter':{'T2M':{'20160101':-999},'PRECTOTCORR':{'20160101':0},'ALLSKY_SFC_SW_DWN':{'20160101':5}}},'header':{'fill_value':-999}}
        with patch('additional_source_apis.get_json',return_value=(payload,None)):
            rows,cursor=fetch(Mock(),self.job('nasa',end='2016-01-02',location='reference',latitude=0,longitude=0),None,item)
        self.assertIsNone(rows[0]['data']['values']['T2M']);self.assertEqual(rows[0]['data']['values']['PRECTOTCORR'],0);self.assertIsNone(cursor)
    def test_datacite_requires_next_page_if_total_not_reconciled(self):
        payload={'data':[{'id':'10.123/a','attributes':{'created':'2016-01-02T00:00:00Z'}}],'meta':{'total':2},'links':{}}
        with patch('additional_source_apis.get_json',return_value=(payload,None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('datacite',resource='dataset'),None,item)
    def test_daily_plan_uses_recent_window_and_history_keeps_2016(self):
        s={'adapter':'additional_fred','coverage_note':'fixture','api':'https://api.stlouisfed.org','scopes':[{'series_id':'GDP'}]}
        daily=list(scopes(s,date(2016,1,1),date(2017,1,1),'daily'));self.assertEqual(daily[0][0],date(2016,12,25))
        jobs=list(scopes(s,date(2016,1,1),date(2017,1,1),'historical'));self.assertEqual(len(jobs),1);self.assertEqual(jobs[0][0],date(2016,1,1))

    def test_daily_observation_window_keeps_provider_query_dates(self):
        from specialist_plan import jobs
        source={'source_id':'C076','source':'nasa','enabled':True,'historical':True,'adapter':'additional_nasa','coverage_note':'fixture','api':'https://power.larc.nasa.gov','scopes':[{'location':'reference','latitude':0,'longitude':0}]}
        planned=list(jobs({'historical_start':'2016-01-01','sources':[source]}, {'companies':[]},'daily',date(2026,10,26)))
        self.assertEqual(planned[0]['start'],'2026-10-26');self.assertEqual(planned[0]['parameters']['data_start'],'2026-10-16');self.assertEqual(planned[0]['parameters']['data_end'],'2026-10-23')

    def test_huggingface_millisecond_timestamps_satisfy_temporal_contract(self):
        from research_contract import temporal_errors
        with patch('additional_source_apis.get_json',return_value=([{'id':'fixture/model','createdAt':'2016-01-02T12:00:00.123Z'}],None)):
            rows,cursor=fetch(Mock(),self.job('huggingface',category='models'),None,item)
        self.assertEqual(temporal_errors({'value':rows[0]['date'],'precision':rows[0]['date_precision'],'source_timezone':'UTC'}),[])

    def test_zenodo_anonymous_request_uses_provider_limit(self):
        payload={'hits':{'hits':[],'total':0}}
        with patch('additional_source_apis.get_json',return_value=(payload,None)) as get:
            fetch(Mock(),self.job('zenodo'),None,item)
        self.assertLessEqual(get.call_args.args[2]['size'],25)

if __name__=='__main__':unittest.main()
