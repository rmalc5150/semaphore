import json
from pathlib import Path
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from metadata_engine.openfda import validate
p=Path(__file__).parent;c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'fda_openfda');out=[]
for route,params in [('/drug/drugsfda.json',{'limit':'1'}),('/transparency/crl.json',{'limit':'1','search':'letter_type:"COMPLETE RESPONSE"'})]:
 try:
  response=c.json('https://api.fda.gov'+route,params=params);r=response['results'][0];ref=c.evidence[-1]
  if route.startswith('/transparency'):
   record={'source_record_id':'crl:'+r['file_name'],'source_url':'https://api.fda.gov'+route,'payload':{'data':r}};info=validate(json.dumps(response).encode(),record,ref['source_url'])
  else:
   sub=next(s for s in r.get('submissions',[])if s.get('submission_status')=='AP');data={'action':'APPROVAL','application':r,'submission':sub};record={'source_record_id':'approval:'+':'.join(str(x)for x in (r['application_number'],sub['submission_type'],sub['submission_number'])),'source_url':'https://api.fda.gov'+route,'payload':{'data':data}};info=validate(json.dumps(response).encode(),record,ref['source_url'])
  out.append({'endpoint':route,'state':'passed','validation':info,'original_response':ref})
 except Exception as error:out.append({'endpoint':route,'state':'failed','reason':type(error).__name__+': '+str(error)[:200]})
(p/'api-probes.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
if any(r['state']!='passed'for r in out):raise SystemExit(1)
