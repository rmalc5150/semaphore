import copy,json,unittest
from unittest.mock import patch
from datetime import date
from public_statistics_apis import fetch,PORTWATCH,UNIDO
from specialist_inputs import item
from regulatory_collection import SourceIssue
from additional_source_plan import scopes
from metadata_engine.public_statistics import evidence
from metadata_engine.evidence import RawFailure
from research_contract import digest
import hashlib,io

class PublicStatistics(unittest.TestCase):
 def portjob(self):return {'adapter':'additional_portwatch','start':'2026-11-06','end':'2026-11-07','parameters':{'url':PORTWATCH}}
 def portrow(self):return {'ObjectId':3,'date':'2026-11-06','portid':'port1','portcalls':0,'import':0,'export':0}
 def test_portwatch_zero_values_are_data(self):
  row=self.portrow()
  with patch('additional_source_apis.get_json',side_effect=[({'count':1},''),({'features':[{'attributes':row}]},'')]):
   rows,cursor=fetch(type('C',(),{})(),self.portjob(),None,item)
  self.assertEqual(rows[0]['data'],row);self.assertIsNone(cursor)
 def test_portwatch_missing_page_does_not_finish(self):
  with patch('additional_source_apis.get_json',side_effect=[({'count':2},''),({'features':[{'attributes':self.portrow()}]},'')]):
   with self.assertRaisesRegex(SourceIssue,'partial'):fetch(type('C',(),{})(),self.portjob(),None,item)
 def test_portwatch_duplicate_object_rejected(self):
  with patch('additional_source_apis.get_json',side_effect=[({'count':2},''),({'features':[{'attributes':self.portrow()}]*2},'')]):
   with self.assertRaises(SourceIssue):fetch(type('C',(),{})(),self.portjob(),None,item)
 def test_portwatch_count_change_restarts(self):
  with patch('additional_source_apis.get_json',return_value=({'count':2},'')):
   with self.assertRaisesRegex(SourceIssue,'changed'):fetch(type('C',(),{})(),self.portjob(),json.dumps({'total':1}),item)
 def metadata(self):return {'id':879,'countries':[{'c':'840'}],'variables':[{'c':'53'},{'c':'54'}],'activities':[{'c':'C'}],'periods':['2023','2023 M01','2024']}
 def test_unido_dynamic_id_and_empty_page_continues(self):
  job={'adapter':'additional_unido','start':'2023-01-01','end':'2024-01-01','parameters':{'dataset':'IIP'}}
  with patch('additional_source_apis.get_json',return_value=(self.metadata(),'')),patch('public_statistics_apis.post_unido',return_value={'data':[],'ym':[],'am':[]})as post:
   rows,cursor=fetch(None,job,None,item)
  self.assertFalse(rows);self.assertEqual(json.loads(cursor)['variable_position'],1);self.assertEqual(post.call_args.args[1]['datasetId'],879);self.assertEqual(post.call_args.args[1]['periods'],['2023','2023 M01'])
 def test_unido_native_dimensions_and_value_preserved(self):
  job={'adapter':'additional_unido','start':'2023-01-01','end':'2024-01-01','parameters':{'dataset':'IIP','variable_code':'53'}}
  native={'p':'2023 M01','a':'C','v':0}
  with patch('additional_source_apis.get_json',return_value=(self.metadata(),'')),patch('public_statistics_apis.post_unido',return_value={'data':[native],'ym':[],'am':[]}):
   rows,cursor=fetch(None,job,None,item)
  self.assertIsNone(cursor);self.assertEqual(rows[0]['data']['native_observation'],native);self.assertIsNone(rows[0]['date'])
 def test_unido_suppressed_cell_retains_footnote_without_zero(self):
  job={'adapter':'additional_unido','start':'2023-01-01','end':'2024-01-01','parameters':{'dataset':'INDSTAT/4','variable_code':'53'}}
  native={'p':'2023','a':'C','c':'C-A','cn':'Included in another category'}
  with patch('additional_source_apis.get_json',return_value=(self.metadata(),'')),patch('public_statistics_apis.post_unido',return_value={'data':[native],'ym':[],'am':[]}):
   rows,cursor=fetch(None,job,None,item)
  self.assertEqual(rows[0]['data']['native_observation'],native);self.assertNotIn('v',rows[0]['data']['native_observation'])
 def test_native_raw_match_and_forgery_rejection(self):
  data=self.portrow();body=json.dumps({'features':[{'attributes':data}]}).encode();sha=hashlib.sha256(body).hexdigest();key='research-data/source_documents/imf_portwatch_shipping_activity/'+sha
  class S3:
   def get_object(self,**kwargs):return {'Body':io.BytesIO(body),'ContentLength':len(body)}
  row={'source':'imf_portwatch_shipping_activity','source_record_id':'port1:2026-11-06','event_at':{'value':'2026-11-06'},'payload':{'data':copy.deepcopy(data),'source_evidence':[{'key':key,'sha256':sha,'source_url':PORTWATCH+'?outFields=*'}],'scope':{'data_start':'2026-11-06','data_end':'2026-11-07'}}}
  self.assertEqual(evidence(row,S3(),'b')[0]['validation']['record_type'],'port_activity_observation')
  row['payload']['data']['import']=99
  with self.assertRaises(RawFailure):evidence(row,S3(),'b')
 def test_history_floor_and_daily_lag(self):
  source={'adapter':'additional_portwatch','api':PORTWATCH,'coverage_note':'native'}
  history=next(scopes(source,date(2016,1,1),date(2026,11,14),'historical'));self.assertEqual(history[0],date(2019,1,1))
  daily=list(scopes(source,date(2016,1,1),date(2026,11,14),'daily'));self.assertEqual(daily[-1][1],date(2026,11,7))
 def test_unido_measurement_requires_both_native_response_and_catalogue(self):
  meta=self.metadata();request={'datasetId':879,'countryCode':'840','variableCode':'53','activityCodes':['C'],'periods':['2023'],'fullPrecision':True};native={'p':'2023','a':'C','v':0}
  data={'dataset':'IIP','country':meta['countries'][0],'variable':meta['variables'][0],'native_observation':native,'request':request,'response_context':{'ym':[],'am':[]}}
  objects={};refs=[]
  for body,url in [(meta,UNIDO+'getDataset/IIP'),({'data':[native],'ym':[],'am':[]},UNIDO+'getData?request_sha256='+digest(request))]:
   raw=json.dumps(body).encode();sha=hashlib.sha256(raw).hexdigest();key='source_documents/unido_iip_and_indstat/'+sha;objects['research-data/'+key]=raw;refs.append({'key':key,'sha256':sha,'source_url':url})
  class S3:
   def get_object(self,**kwargs):
    raw=objects[kwargs['Key']];return {'Body':io.BytesIO(raw),'ContentLength':len(raw)}
  row={'source':'unido_iip_and_indstat','source_record_id':digest(['IIP','840','53','2023','C']),'payload':{'data':copy.deepcopy(data),'source_evidence':refs}}
  self.assertEqual(evidence(row,S3(),'b')[0]['validation']['record_type'],'industrial_statistics_observation')
  row['payload']['data']['request']['datasetId']=123
  with self.assertRaises(RawFailure):evidence(row,S3(),'b')
if __name__=='__main__':unittest.main()
