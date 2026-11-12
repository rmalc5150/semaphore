import json,hashlib
from pathlib import Path
import patent_prosecution as p
from collection_storage import StorageSettings
folder=Path(__file__).parent;old=json.loads((folder/'patent-document-probe.json').read_text())[-1]
url=p.BASE+'/api/v1/download/applications/'+old['application']+'/'+old['requested_document']+'.pdf';c=p.Client(StorageSettings.load(Path('config/collection-storage.s3.json')).store(),max_requests=4,max_download_bytes=4*1024*1024)
try:
 raw=c.request(url,pdf=True);out={'status':'downloaded','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'evidence':c.evidence}
except Exception as e:out={'status':'failed','reason':getattr(e,'code',type(e).__name__),'diagnostics':getattr(e,'diagnostics',None),'evidence':c.evidence}
(folder/'patent-direct-download.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
