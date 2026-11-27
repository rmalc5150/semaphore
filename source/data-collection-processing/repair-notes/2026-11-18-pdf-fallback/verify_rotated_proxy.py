"""Two budgeted diagnostic calls simulate unavailable free routes; no production data writes."""
import json,hashlib
from pathlib import Path
from unittest.mock import patch
from collection_storage import LocalStore
from regulatory_collection import EvidenceClient,SourceIssue
import pdf_proxy_fallback as f
p=Path(__file__).parent;cfg={**f.settings(),'enabled':True};real=f.fetch;rows=[]
def blocked_free(url,limit,proxy=None):
 if proxy is None:raise SourceIssue('pdf_proxy_http_403')
 return real(url,limit,proxy)
for name,url,expected in [('control','https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf','3df79d34abbca99308e79cb94461c1893582604d68329a41fd4bec1885e6adb4'),('medrxiv','https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf','2711c86f4189824a8324c0ecafdc2a807485054560bb7d50cef2eee9b7f821ef')]:
 client=EvidenceClient(LocalStore(p/'diagnostic-storage'),'biorxiv_medrxiv_preprints')
 try:
  with patch.object(f,'settings',return_value=cfg),patch.object(f,'fetch',side_effect=blocked_free):raw=f.capture(client,url,'source_http_403')
  passed=hashlib.sha256(raw).hexdigest()==expected;rows.append({'test':name,'passed':passed,'bytes':len(raw),'validation':f.validate(raw,url),'paid_requests':client._pdf_proxy_requests})
 except Exception as e:rows.append({'test':name,'passed':False,'error_type':type(e).__name__,'reason':getattr(e,'code',None)})
 (p/'rotated-proxy-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows[-1]),flush=True)
 if not rows[-1]['passed']:break
assert len(rows)==2 and all(r['passed']for r in rows),'proxy_validation_failed'
