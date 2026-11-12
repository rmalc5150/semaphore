import json
from pathlib import Path
from additional_source_apis import fetch
from specialist_inputs import item
class Capture:
 def save(self,body,url,kind):pass
p=Path(__file__).parent;reports=json.loads((p/'receipts.json').read_text());out=[]
for name in ('fred_alfred','datacite'):
 row=next(x for x in reports[name]['outcomes']if (x.get('job',{}).get('parameters',{}).get('series_id')=='T10Y2Y' if name=='fred_alfred' else x.get('reason')=='additional_response_too_large_split_scope'))
 try:
  rows,cursor=fetch(Capture(),row['job'],None,item);r={'source':name,'rows':len(rows),'has_next_page':cursor is not None,'cursor':json.loads(cursor)if cursor else None}
 except Exception as e:r={'source':name,'error':type(e).__name__,'reason':getattr(e,'code','')}
 out.append(r);print(json.dumps(r),flush=True)
(p/'live-probes.json').write_text(json.dumps(out,indent=2))
