import json
from datetime import date
from pathlib import Path
import patent_prosecution as p
from collection_storage import StorageSettings
folder=Path(__file__).parent;c=p.Client(StorageSettings.load(Path('config/collection-storage.s3.json')).store(),max_requests=15,max_download_bytes=1024*1024);out=[]
try:
 field,q=p.query(p.DATASETS[0],date(2026,10,14),date(2026,10,15),'daily');total,rows=c.search(p.DATASETS[0],q,0,5)
 for row in rows:
  data=p.normalize(p.DATASETS[0],row);docs=c.documents(data['application_number'])
  result={'source_record_id':data['source_document_id'],'application':data['application_number'],'requested_document':data['official_document_id'],'returned_document_count':len(docs),'matching_document_count':sum(d.get('documentIdentifier')==data['official_document_id']for d in docs),'returned_document_ids':[d.get('documentIdentifier')for d in docs],'evidence':list(c.evidence)}
  out.append(result)
  if not result['matching_document_count']:break
except Exception as e:out.append({'error_type':type(e).__name__,'reason':getattr(e,'code',str(e)),'evidence':c.evidence})
(folder/'patent-document-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out)[:7500])
