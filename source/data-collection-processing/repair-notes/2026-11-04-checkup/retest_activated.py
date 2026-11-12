import json,datetime
from pathlib import Path
from additional_source_apis import get_json
from copernicus_capture import call,API
from constellation.control import Control
p=Path(__file__).parent
class Capture:
 def save(self,*args): pass
client=Capture();out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
try:
 d,_=get_json(client,'https://api.census.gov/data/timeseries/intltrade/exports/hs',{'get':'CTY_CODE,CTY_NAME,E_COMMODITY,ALL_VAL_MO','E_COMMODITY':'282520','CTY_CODE':'*','YEAR':'2016','MONTH':'02'},'US-census','key')
 out['census']={'status':'passed','rows':len(d)-1,'columns':d[0]}
except Exception as e:out['census']={'status':'failed','reason':getattr(e,'code',type(e).__name__)}
for dataset in ['reanalysis-era5-single-levels','reanalysis-era5-land']:
 receipt=p/(dataset+'-activation-probe.json')
 try:
  if receipt.exists():d=json.loads(receipt.read_text())
  else:
   active=call(client,'GET',API+'/jobs?limit=100')['jobs']
   if sum(r.get('status') in ('accepted','running') for r in active)>=2:
    out[dataset]={'status':'deferred','reason':'two_provider_jobs_active'};continue
   req={'variable':['2m_temperature'],'year':['2016'],'month':['01'],'day':['01'],'time':['00:00'],'area':[51.5,0,51.25,0.25],'data_format':'netcdf','download_format':'unarchived'}
   if dataset=='reanalysis-era5-single-levels':req['product_type']=['reanalysis']
   d=call(client,'POST',API+'/processes/'+dataset+'/execution',{'inputs':req})
   receipt.write_text(json.dumps(d,indent=2))
  out[dataset]={'status':'submission_accepted','job_id':d.get('jobID'),'provider_status':d.get('status')}
 except Exception as e:out[dataset]={'status':'failed','reason':getattr(e,'code',type(e).__name__)}
(p/'activated-access-retest.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
c=Control()
with c.db() as cur:
 cur.execute("SELECT source_key,status,COUNT(*) AS jobs FROM backfill_jobs WHERE source_key IN ('us_census_international_trade_api','copernicus_era5_era5_land') GROUP BY source_key,status")
 rows=cur.fetchall();print(json.dumps(rows))
 (p/'activated-queue-status.json').write_text(json.dumps(rows,indent=2))
