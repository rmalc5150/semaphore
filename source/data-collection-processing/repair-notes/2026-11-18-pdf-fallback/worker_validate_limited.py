import os,sys,json,hashlib,tempfile
from pathlib import Path
from unittest.mock import patch
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from collection_storage import LocalStore,write_json
from regulatory_collection import EvidenceClient,SourceIssue
import pdf_proxy_fallback as f
url='https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf';expected='2711c86f4189824a8324c0ecafdc2a807485054560bb7d50cef2eee9b7f821ef';cfg={**f.settings(),'enabled':True};out={'scope':'worker local diagnostic only','production_cache_seeded':False}
connection=f.proxy_url(cfg);out['credentials_readable']=connection.startswith('https://');del connection
with tempfile.TemporaryDirectory(prefix='pdf-fallback-test-')as temp:
 client=EvidenceClient(LocalStore(Path(temp)/'cached'),'biorxiv_medrxiv_preprints');raw=client.get(url);proof=client.evidence[-1];validation=f.validate(raw,url);assert validation['sha256']==expected
 key=f.PREFIX+'/cache/'+hashlib.sha256(url.encode()).hexdigest()+'.json';write_json(client.store,key,{'url':url,'evidence':proof,'validation':validation,'checked_at':f.now(),'transport':'direct_requests'})
 with patch.object(f,'settings',return_value=cfg),patch.object(client,'_get_direct',side_effect=SourceIssue('source_http_403')),patch.object(f,'fetch',side_effect=AssertionError('cache must prevent network'))as fetch:
  recovered=client.get(url);assert hashlib.sha256(recovered).hexdigest()==expected;fetch.assert_not_called()
 out['cached_recovery_passed']=True
 other=EvidenceClient(LocalStore(Path(temp)/'quota'),'biorxiv_medrxiv_preprints')
 with patch.object(f,'settings',return_value=cfg),patch.object(f,'fetch',side_effect=SourceIssue('pdf_proxy_http_403'))as fetch:
  try:f.capture(other,url,'source_http_403');raise AssertionError('URL cooldown should prevent paid request')
  except SourceIssue as e:assert e.code in {'pdf_proxy_url_cooldown','pdf_proxy_daily_budget'};out['shared_budget_guard']=e.code
  assert fetch.call_count==1
 out['paid_proxy_requests']=0
print(json.dumps(out))
