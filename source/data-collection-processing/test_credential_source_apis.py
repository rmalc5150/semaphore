import json,unittest
from datetime import date
from unittest.mock import Mock,patch
from credential_source_apis import fetch
from additional_source_plan import scopes
from regulatory_collection import SourceIssue
from specialist_inputs import item

class CredentialSources(unittest.TestCase):
    def job(self,kind,**parameters):return {'adapter':'additional_'+kind,'source':kind,'mode':'historical','start':'2016-01-01','end':'2016-02-01','parameters':{'url':'https://api.wto.org/example',**parameters}}
    def test_wto_total_requires_all_pages(self):
        payload={'Dataset':[{'Year':2016,'IndicatorCode':'i','ReportingEconomyCode':'USA'}],'Summary':[{'DataSet':[{'Name':'Data','TotalCount':2}]}]}
        client=Mock()
        with patch('credential_source_apis.get_json',return_value=(payload,None)):
            rows,cursor=fetch(client,self.job('wto_timeseries',indicator='i',year=2016),None,item)
        self.assertEqual(len(rows),1);self.assertEqual(json.loads(cursor)['offset'],1);self.assertEqual(client.expected_records,2)
    def test_wto_repeated_page_is_not_silently_duplicated(self):
        from research_contract import digest
        records=[{'Year':2016,'IndicatorCode':'i'}];payload={'Dataset':records,'Summary':[{'DataSet':[{'Name':'Data','TotalCount':2}]}]}
        with patch('credential_source_apis.get_json',return_value=(payload,None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('wto_timeseries',indicator='i',year=2016),json.dumps({'offset':1,'page_hash':digest(records),'total':2}),item)
    def test_ember_count_mismatch_fails(self):
        with patch('credential_source_apis.get_json',return_value=({'data':[],'stats':{'number_of_records':1}},None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('ember',dataset='electricity-demand'),None,item)
    def test_ember_month_precision_and_attribution(self):
        payload={'data':[{'date':'2016-01-01','entity':'USA','demand_twh':1}],'stats':{'number_of_records':1}}
        with patch('credential_source_apis.get_json',return_value=(payload,None)):rows,cursor=fetch(Mock(),self.job('ember',dataset='electricity-demand'),None,item)
        self.assertEqual(rows[0]['date'],'2016-01');self.assertEqual(rows[0]['date_precision'],'month');self.assertIn('CC-BY',rows[0]['data']['attribution'])
    def test_qr_refuses_stale_total(self):
        with patch('credential_source_apis.get_json',return_value=({'data':[],'meta':{'total':4}},None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('wto_qr',year=2016,resource='notifications',year_parameter='notification_year'),json.dumps({'page':2,'total':3}),item)
    def test_eping_outside_scope_fails(self):
        payload={'items':[{'id':1,'distributionDate':'2015-01-01'}],'totalCount':1,'currentPage':1}
        with patch('credential_source_apis.get_json',return_value=(payload,None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('wto_eping'),None,item)
    def test_census_duplicate_partner_identity_fails(self):
        payload=[['CTY_CODE','I_COMMODITY'],['0000','TOTAL'],['0000','TOTAL']]
        with patch('credential_source_apis.get_json',return_value=(payload,None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('census',direction='imports',commodity='TOTAL'),None,item)
    def test_comtrade_sends_actual_year(self):
        with patch('credential_source_apis.reserve_comtrade'),patch('credential_source_apis.get_json',return_value=({'data':[]},None)) as get:fetch(Mock(),self.job('comtrade',query={},year=2016),None,item)
        self.assertEqual(get.call_args.args[2]['period'],'2016')
    def test_census_total_uses_provider_dash_and_preserves_scope(self):
        job=self.job('census',direction='exports',commodity='TOTAL')
        payload=[['CTY_CODE','CTY_NAME','E_COMMODITY','ALL_VAL_MO','YEAR','MONTH'],['1220','CANADA','-','100','2016','01']]
        with patch('credential_source_apis.get_json',return_value=(payload,None)) as get:
            rows,cursor=fetch(Mock(),job,None,item)
        self.assertEqual(get.call_args.args[2]['E_COMMODITY'],'-')
        self.assertEqual(job['parameters']['commodity'],'TOTAL')
        self.assertEqual(rows[0]['data']['E_COMMODITY'],'-')
        self.assertIsNone(cursor)
    def test_census_specific_commodity_is_not_mapped_to_total(self):
        with patch('credential_source_apis.get_json',return_value=([['CTY_CODE']],None)) as get:
            fetch(Mock(),self.job('census',direction='imports',commodity='850760'),None,item)
        self.assertEqual(get.call_args.args[2]['I_COMMODITY'],'850760')
    def test_usda_migrates_saved_scope_to_current_gateway(self):
        job=self.job('usda',year=2016,commodity='0440000',url='https://apps.fas.usda.gov/OpenData/api/psd/commodity/{commodity}/country/all/year/{year}')
        with patch('credential_source_apis.get_json',return_value=([],None)) as get:
            fetch(Mock(),job,None,item)
        self.assertEqual(get.call_args.args[1],'https://api.fas.usda.gov/api/psd/commodity/0440000/country/all/year/2016')
        self.assertEqual(get.call_args.kwargs,{'key_parameter':'api_key'})
        self.assertIn('OpenData',job['parameters']['url'])
    def test_usda_provider_error_cannot_be_empty_success(self):
        with patch('credential_source_apis.get_json',return_value=({'message':'error'},None)),self.assertRaises(SourceIssue):fetch(Mock(),self.job('usda',year=2016,commodity='0440000'),None,item)
    def test_daily_ember_revisits_released_months(self):
        source={'adapter':'additional_ember','api':'https://api.ember-energy.org/v1','coverage_note':'fixture','scopes':[{'dataset':'electricity-demand'}]}
        jobs=list(scopes(source,date(2016,1,1),date(2026,10,27),'daily'));self.assertEqual(jobs[0][0],date(2024,1,1));self.assertEqual(jobs[-1][1],date(2026,10,27))
    def test_historical_starts_2016(self):
        source={'adapter':'additional_wto_timeseries','api':'https://api.wto.org','coverage_note':'fixture','scopes':[{'indicator':'i'}]}
        jobs=list(scopes(source,date(2016,1,1),date(2026,10,26),'historical'));self.assertEqual(len(jobs),11);self.assertEqual(jobs[0][2]['year'],2016)
    def test_header_credentials_never_enter_url_or_saved_body(self):
        from additional_source_apis import get_json
        response=Mock(status_code=200,headers={},links={});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=[b'{"echo":"private-test-key"}'];client=Mock()
        with patch('additional_source_apis.credentials',return_value={'WTO-primary':'private-test-key'}),patch('additional_source_apis.requests.get',return_value=response) as get,patch('constellation.shared_limits.admit'):
            get_json(client,'https://api.wto.org/qrs',{'page':1},'WTO-primary',key_header='Ocp-Apim-Subscription-Key')
        self.assertNotIn('private-test-key',str(get.call_args.kwargs['params']));self.assertNotIn(b'private-test-key',client.save.call_args.args[0]);self.assertEqual(get.call_args.kwargs['headers']['Ocp-Apim-Subscription-Key'],'private-test-key')
    def test_fred_vintage_partitions_stay_below_provider_cap(self):
        source={'adapter':'additional_fred','api':'https://api.stlouisfed.org','coverage_note':'fixture','scopes':[{'series_id':'DGS10'}]}
        planned=list(scopes(source,date(2016,1,1),date(2026,10,26),'historical'))
        self.assertTrue(all((date.fromisoformat(p['realtime_end'])-date.fromisoformat(p['realtime_start'])).days<2000 for _,_,p,_ in planned))
        self.assertEqual(min(p['realtime_start'] for _,_,p,_ in planned),'2016-01-01')
        self.assertEqual(max(p['realtime_end'] for _,_,p,_ in planned),'2026-10-26')
    def test_periodless_wto_indicators_have_no_invented_event_year(self):
        payload={'Dataset':[{'Year':0,'IndicatorCode':'BOUND','ReportingEconomyCode':'USA'}],'Summary':[{'DataSet':[{'Name':'Data','TotalCount':1}]}]}
        with patch('credential_source_apis.get_json',return_value=(payload,None)) as get:
            rows,cursor=fetch(Mock(),self.job('wto_timeseries',indicator='BOUND',no_time_dimension=True),None,item)
        self.assertIsNone(rows[0]['date']);self.assertIsNone(cursor);self.assertEqual(get.call_args.args[2]['ps'],'default')
    def test_comtrade_budget_blocks_http_when_exhausted(self):
        with patch('credential_source_apis.reserve_comtrade',side_effect=SourceIssue('comtrade_daily_request_budget')),patch('credential_source_apis.get_json') as get,self.assertRaises(SourceIssue):fetch(Mock(),self.job('comtrade',query={},year=2016),None,item)
        get.assert_not_called()
    def test_copernicus_signed_asset_url_not_persisted(self):
        from copernicus_capture import call
        payload={'asset':{'value':{'href':'https://download.ecmwf.int/test.nc?signature=private-signature'}}};response=Mock(status_code=200,content=json.dumps(payload).encode());response.json.return_value=payload;client=Mock()
        with patch('copernicus_capture.credentials',return_value={'copernicus':'private-test-token'}),patch('copernicus_capture.requests.request',return_value=response),patch('constellation.shared_limits.admit'):
            result=call(client,'GET','https://cds.climate.copernicus.eu/api/retrieve/v1/jobs/test/results')
        self.assertIn('private-signature',result['asset']['value']['href']);self.assertNotIn(b'private-signature',client.save.call_args.args[0])
    def test_copernicus_pending_is_not_completed_data(self):
        from copernicus_capture import fetch as capture
        client=Mock();client.store.get.return_value=Mock(body=b'{"job_id":"abc-123"}')
        job=self.job('copernicus',dataset='reanalysis-era5-single-levels',location='Berlin',area=[53,13,52,14])
        with patch('copernicus_capture.call',return_value={'status':'running'}):rows,cursor=capture(client,job,None,item)
        self.assertEqual(rows,[]);self.assertEqual(json.loads(cursor)['job_id'],'abc-123')
    def test_copernicus_rejects_foreign_download_host(self):
        from copernicus_capture import fetch as capture
        client=Mock();client.store.get.return_value=Mock(body=b'{"job_id":"abc-123"}')
        job=self.job('copernicus',dataset='reanalysis-era5-single-levels',location='Berlin',area=[53,13,52,14])
        with patch('copernicus_capture.call',side_effect=[{'status':'successful'},{'asset':{'value':{'href':'https://evil.example/test','file:size':1}}}]),self.assertRaises(SourceIssue):capture(client,job,None,item)

if __name__=='__main__':unittest.main()
