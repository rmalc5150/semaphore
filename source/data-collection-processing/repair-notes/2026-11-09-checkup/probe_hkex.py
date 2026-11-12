import json
from datetime import date
from pathlib import Path
from disclosure_collection import hkex_page
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
p=Path(__file__).parent;settings=StorageSettings.load(Path('config/collection-storage.s3.json'));c=EvidenceClient(settings.store(),'hkex_news')
try:
 rows,state,done=hkex_page(c,date(2026,9,23),{},100000)
 out={'rows':len(rows),'exhausted':done,'state':state,'evidence':c.evidence}
except Exception as e:out={'error_type':type(e).__name__,'reason':str(e),'evidence':c.evidence}
(p/'hkex-index-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
