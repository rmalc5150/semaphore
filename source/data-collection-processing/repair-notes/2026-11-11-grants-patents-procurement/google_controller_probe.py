import json
from pathlib import Path
from patent_bigquery_access import session,API
p=Path(__file__).parent;out={}
try:
 h=session(Path('config/google-patents-aws.json'));r=h.get(API+'/projects/patents-public-data/datasets/patents/tables/publications',timeout=40);d=r.json();out={'http_status':r.status_code,'table_id':d.get('id'),'error_status':d.get('error',{}).get('status')}
except Exception as e:out={'error_type':type(e).__name__,'error':str(e)[:300]}
(p/'google-controller-access.json').write_text(json.dumps(out,indent=2));print(out)
