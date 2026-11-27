import boto3,json,collections
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';sources=['copernicus_era5_era5_land','zenodo_research_artifacts_and_usage','datacite_dissertations_datasets_software_and_usage','biorxiv_medrxiv_preprints','us_census_international_trade_api','wto_timeseries_api','imf_portwatch_shipping_activity','fred_alfred_series_and_vintages','edinet_filings','ted_notices','usgs_minerals','usa_spending'];out={}
for source in sources:
 key='research-data/constellation-backfill/specialist-schedulers/constellation-specialist-'+source+'.service/historical.json'
 try:
  r=s.get_object(Bucket=b,Key=key);d=json.loads(r['Body'].read());(p/(source+'-scheduler.json')).write_text(json.dumps(d,indent=2));jobs=d.get('jobs',{});counts=collections.Counter(v.get('status')for v in jobs.values());reasons=collections.Counter(v.get('reason')for v in jobs.values()if v.get('status')in('failed','partial'));out[source]={'key':key,'counts':dict(counts),'reasons':dict(reasons),'updated_at':d.get('updated_at')};print(source,out[source],flush=True)
 except Exception as e:out[source]={'key':key,'error':str(e)[:200]};print(source,type(e).__name__,flush=True)
(p/'scheduler-summary.json').write_text(json.dumps(out,indent=2))
