import json
from pathlib import Path
from datetime import date,timedelta
from additional_source_apis import get_json
class Capture:
 def save(self,body,url,kind):
  print(json.dumps({'body':body.decode()[:1600]},ensure_ascii=False))
p=Path(__file__).parent;r=json.loads((p/'receipts.json').read_text())['fred_alfred']
for x in r['outcomes'][:2]:
 j=x['job'];a=j['parameters'];query={'series_id':a['series_id'],'file_type':'json','observation_start':j['start'],'observation_end':(date.fromisoformat(j['end'])-timedelta(days=1)).isoformat(),'realtime_start':a.get('realtime_start','2016-01-01'),'realtime_end':a['realtime_end'],'output_type':1,'limit':1000,'offset':0,'sort_order':'asc'}
 print(a['series_id'])
 try:get_json(Capture(),'https://api.stlouisfed.org/fred/series/observations',query,'FRED')
 except Exception as e:print(type(e).__name__,getattr(e,'code',''))
