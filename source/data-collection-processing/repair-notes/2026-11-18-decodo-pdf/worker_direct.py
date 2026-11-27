import os,sys,json,hashlib,io
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
import requests
from pypdf import PdfReader
from collection_storage import LocalStore
from regulatory_collection import EvidenceClient
url='https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf';doi='10.64898/2026.05.07.26352693';p=Path('/opt/constellation/tmp/decodo-pdf-20261118');p.mkdir(exist_ok=True);rows=[]
for method in ['production_urllib','requests']:
 row={'method':method,'url':url}
 try:
  if method=='production_urllib':
   client=EvidenceClient(LocalStore(p/'evidence'),'biorxiv_medrxiv_preprints');raw=client.get(url);row['evidence']=client.evidence
  else:
   with requests.get(url,headers={'User-Agent':'Optima Holdings support@optima-holdings.com','Accept':'application/pdf'},stream=True,timeout=(10,40),allow_redirects=False)as r:
    row['http_status']=r.status_code
    chunks=[];size=0
    for chunk in r.iter_content(65536):
     size+=len(chunk);assert size<=16*1024**2;chunks.append(chunk)
    raw=b''.join(chunks)
  row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());assert raw.startswith(b'%PDF-') and b'%%EOF' in raw[-4096:];doc=PdfReader(io.BytesIO(raw),strict=True);text=''.join(doc.pages[i].extract_text()or''for i in range(min(2,len(doc.pages))));row.update(strict_pdf=True,pages=len(doc.pages),doi_match=doi in ''.join(text.split()))
 except Exception as e:row.update(strict_pdf=False,error_type=type(e).__name__,reason=getattr(e,'code',None))
 rows.append(row)
(p/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
