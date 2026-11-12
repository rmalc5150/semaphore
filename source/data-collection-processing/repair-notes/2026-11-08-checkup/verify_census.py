import json
from pathlib import Path
from unittest.mock import Mock
from credential_source_apis import fetch
from specialist_inputs import item
p=Path(__file__).parent;job=json.loads((p/'replay-status.json').read_text())[1]['scheduler']['latest'][0]['job'];client=Mock();out={'job':job}
try:
 rows,cursor=fetch(client,job,None,item)
 out.update(status='passed',records=len(rows),unique_ids=len({r['id'] for r in rows}),cursor=cursor,sample=rows[:1]);print(json.dumps({k:v for k,v in out.items() if k not in ('job','sample')}))
except Exception as e:
 out.update(status='failed',error_type=type(e).__name__,reason=getattr(e,'code',type(e).__name__));print(json.dumps(out))
(p/'census-adapter-live.json').write_text(json.dumps(out,indent=2))
