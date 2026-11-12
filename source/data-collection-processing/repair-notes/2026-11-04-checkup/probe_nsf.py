import json,requests,hashlib,time
from pathlib import Path
from constellation.sources import request,parse,identity
spec={'source_key':'nsf_awards','dataset':'research_awards','extractor_version':'constellation-raw-v1','parameters':{},'geography':'global','edition':'current_retrieval','start':'2016-02-29','end':'2016-03-01'};out=[];cursor=None;seen={}
for n in range(3):
 time.sleep(3)
 url,params=request(spec,cursor);r=requests.get(url,params=params,timeout=(10,30));r.raise_for_status();rows,next_cursor=parse(spec,r.content,cursor)
 duplicates=[]
 for row in rows:
  key=identity(spec,row);sha=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
  if key in seen:duplicates.append({'id':key,'identical':seen[key]==sha})
  seen[key]=sha
 out.append({'page':n,'rows':len(rows),'duplicates':duplicates,'next_cursor':next_cursor});print(out[-1],flush=True)
 if next_cursor is None:break
 cursor=next_cursor
Path('repair-notes/2026-11-04-checkup/nsf-probe.json').write_text(json.dumps(out,indent=2))
