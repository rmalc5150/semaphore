import sys,os
sys.path.insert(0,'/opt/constellation/source');os.chdir('/opt/constellation/source')
import json
from pathlib import Path
from patent_bigquery_access import session,API,PROJECT
from uspto_patents import load_api_key
from urllib.request import Request,urlopen
root=Path('/opt/constellation/source');p=json.loads((root/'config/google-patents-aws.json').read_text());http=session(root/'config/google-patents-aws.json');r=http.get(API+'/projects/patents-public-data/datasets/patents/tables/publications',params={},timeout=40);print(json.dumps({'source':'google_patents_bigquery','operation':'read_public_patent_table_metadata_no_new_query','http_status':r.status_code,'error_reason':r.json().get('error',{}).get('status')}),flush=True)
key=load_api_key();req=Request('https://api.uspto.gov/api/v1/patent/applications/18680477',headers={'X-API-KEY':key,'Accept':'application/json'})
try:
 with urlopen(req,timeout=40)as response:d=json.load(response);print(json.dumps({'source':'uspto_odp','operation':'existing_application','http_status':response.status,'count':d.get('count'),'application':d.get('patentFileWrapperDataBag',[{}])[0].get('applicationNumberText')}),flush=True)
except Exception as e:print(json.dumps({'source':'uspto_odp','error':type(e).__name__,'http_status':getattr(e,'code',None)}),flush=True)
