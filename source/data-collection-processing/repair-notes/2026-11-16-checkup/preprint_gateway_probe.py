import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings
from specialist_inputs import SpecialistClient
from additional_source_apis import get_json
from decodo_scraping_api import scrape,cached_token,DEFAULT_SECRET_ID
from public_source_scope import decoded_response
s=StorageSettings.load(root/'config/collection-storage.s3.json');c=SpecialistClient(s.store(),'biorxiv_medrxiv_preprints')
d,_=get_json(c,'https://api.biorxiv.org/details/medrxiv/2026-08-01/2026-08-31/0');r=d['collection'][0];url='https://www.medrxiv.org/content/'+r['doi']+'v'+str(r['version'])+'.full.pdf'
print(json.dumps({'pdf_url':url,'title':r.get('title')}),flush=True)
try:
 result=scrape(url,cached_token(DEFAULT_SECRET_ID,'us-east-1'),timeout=60)
 for row in result.get('results',[])[:1]:
  content=row.get('content','');raw,media,wrapper=decoded_response(content.encode(),url,'text/html')
  print(json.dumps({'target_status':row.get('status_code'),'bytes':len(raw),'is_pdf':raw.startswith(b'%PDF-'),'media':media}),flush=True)
  if row.get('status_code')==200 and raw.startswith(b'%PDF-'):
   c.save(raw,url,'application/pdf');print(json.dumps({'evidence':c.evidence[-1:]}),flush=True)
except Exception as e:print(json.dumps({'gateway_error':type(e).__name__,'reason':str(e)[:150]}),flush=True)
