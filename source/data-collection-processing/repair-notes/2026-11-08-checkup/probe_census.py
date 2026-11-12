import json,requests
from pathlib import Path
from additional_source_apis import credentials
key=credentials()['US-census'];base='https://api.census.gov/data/timeseries/intltrade/exports/hs';out=[]
for label,extra in [('old',{'YEAR':'2017','MONTH':'05','E_COMMODITY':'TOTAL'}),('time_total',{'time':'2017-05','E_COMMODITY':'TOTAL'}),('time_default',{'time':'2017-05'})]:
 p={'get':'CTY_CODE,CTY_NAME,E_COMMODITY,ALL_VAL_MO','CTY_CODE':'*','key':key,**extra};r=requests.get(base,params=p,timeout=30);d=r.json() if r.status_code==200 else None
 out.append({'probe':label,'status':r.status_code,'rows':len(d)-1 if isinstance(d,list) else None,'sample':d[:2] if isinstance(d,list) else None});print(json.dumps(out[-1]),flush=True)
Path(__file__).with_name('census-probe.json').write_text(json.dumps(out,indent=2))
