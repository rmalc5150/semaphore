import json
from pathlib import Path
from constellation.control import Control
p=Path(__file__).parent;c=Control();sources=['legacy:constellation-specialist-'+x+'.service'for x in ('copernicus_era5_era5_land','zenodo_research_artifacts_and_usage','datacite_dissertations_datasets_software_and_usage','biorxiv_medrxiv_preprints','us_census_international_trade_api','wto_timeseries_api','imf_portwatch_shipping_activity','fred_alfred_series_and_vintages','edinet_filings','ted_notices','usgs_minerals','usa_spending')]+['legacy:constellation-core-'+x+'-historical.service'for x in ('fda','ema','uk','clinicaltrials')];out=[]
for source in sources:
 try:
  with c.db()as q:
   q.execute('SET SESSION max_execution_time=4000');q.execute('SELECT job_id,status,spec_json,result_json,updated_at,lease_until FROM backfill_jobs WHERE source_key=%s ORDER BY updated_at DESC LIMIT 1',(source,));r=q.fetchone()
  if r:
   r['source']=source;out.append(r);result=json.loads(r.get('result_json')or'{}');print(source,r['status'],r['updated_at'],result.get('reason'),len(result.get('coverage_windows',[])),flush=True)
 except Exception as e:out.append({'source':source,'error':str(e)[:250]});print(source,type(e).__name__,str(e)[:80],flush=True)
(p/'latest-source-jobs.json').write_text(json.dumps(out,indent=2,default=str))
