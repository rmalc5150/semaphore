import json,hashlib
from pathlib import Path
from types import SimpleNamespace
from collection_storage import StorageSettings,write_checked
import patent_prosecution as p
folder=Path(__file__).parent;store=StorageSettings.load(Path('config/collection-storage.s3.json')).store()
source_key='source_documents/uspto_odp/dbcba68b966da19d9af432b2824a26cda991b0e36da8bbe57476ab7b530d1680'
doc=json.loads(store.get(source_key).body);rows=doc['response']['docs'];row=next(r for r in rows if p.scalar(r.get('obsoleteDocumentIdentifier'))=='MMOWZII4X158X88');data=p.normalize(p.DATASETS[0],row)
assert data['application_number']=='35526479'
cache='checkpoints/uspto-prosecution-documents/'+p.digest([p.VERSION,p.DATASETS[0],row])+'.json';old=store.get(cache);archive=None
if old:
 archive='source_documents/uspto_document_exceptions/prior-failure-'+hashlib.sha256(old.body).hexdigest();write_checked(store,archive,old.body)
def forbidden(*a,**kw):raise AssertionError('An excluded document must not call a provider endpoint')
c=SimpleNamespace(store=store,evidence=[],documents=forbidden,request=forbidden)
r=p.enrich(c,p.DATASETS[0],row,data);assert r['status']=='excluded_by_owner';assert r['documents']==[];assert r['document_exception']['official_document_id']=='MMOWZII4X158X88'
out={'status':r['status'],'application_number':data['application_number'],'official_document_id':data['official_document_id'],'cache_key':cache,'prior_failure_archive':archive,'source_evidence':r['source_evidence'],'provider_calls':0,'pdf_captured':False}
(folder/'live-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='source_evidence'}))
