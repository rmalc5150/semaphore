import os,sys,json
from pathlib import Path
root='/opt/constellation/auxiliary-publication/source';os.chdir(root);sys.path.insert(0,root);os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings
from specialist_inputs import SpecialistClient,item,fetch_page
from additional_source_apis import get_json
from regulatory_collection import SourceIssue
from edinet_pipeline import API
s=StorageSettings.load(Path('config/collection-storage.s3.json'));store=s.store()
client=SpecialistClient(store,'us_census_international_trade_api')
try:
 d,_=get_json(client,'https://api.census.gov/data/timeseries/intltrade/imports/hs',{'get':'CTY_CODE,CTY_NAME,I_COMMODITY,GEN_VAL_MO','I_COMMODITY':'260400','CTY_CODE':'*','YEAR':'2019','MONTH':'03'},'US-census',key_parameter='key',allow_empty=True);print(json.dumps({'census_rows':len(d)if d else None,'evidence':client.evidence}))
except Exception as e:print(json.dumps({'census_error':type(e).__name__,'reason':getattr(e,'code',None),'diagnostics':getattr(e,'diagnostics',None)}))
# A first-day archive listing establishes the provider's explicit status, without downloading documents.
from specialist_authenticated import credentials
import requests
key,=credentials('edinet')
for date in ['2016-01-04','2026-11-13']:
 try:
  from constellation.shared_limits import admit
  admit(API)
  r=requests.get(API+'/documents.json',params={'date':date,'type':2,'Subscription-Key':key},timeout=45)
  raw=r.content.replace(key.encode(),b'[REDACTED]');client.source='edinet_filings';client.save(raw,API+'/documents.json?date='+date+'&type=2','application/json');d=r.json();print(json.dumps({'edinet_date':date,'http_status':r.status_code,'metadata':d.get('metadata'),'count':len(d.get('results',[])),'evidence':client.evidence[-1:]}))
 except Exception as e:print(json.dumps({'edinet_date':date,'error':type(e).__name__}))
