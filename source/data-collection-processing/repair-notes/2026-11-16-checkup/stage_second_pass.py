import json,boto3
from pathlib import Path
from research_contract import digest
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/2026-11-16';rows=[]
first=json.load(open(p/'replay-results.json'))
for r in first['outcomes']:
 if r['source']=='us_census_international_trade_api'and r['status']=='failed':rows.append({'identity':r['job_id'],'job':r['job'],'pages':1})
for source,limit in [('edinet_filings',300),('wto_timeseries_api',2),('copernicus_era5_era5_land',2),('biorxiv_medrxiv_preprints',1)]:
 d=json.load(open(p/(source+'-scheduler.json')));candidates=[]
 for identity,r in d['jobs'].items():
  if source=='edinet_filings':ok=r.get('reason')=='edinet_api_status'and r['job']['end']<'2016-11-01'and not r.get('records')
  elif source=='wto_timeseries_api':ok=r.get('reason')=='source_http_400'
  elif source=='copernicus_era5_era5_land':ok=r.get('reason')=='page_budget'
  else:ok=r.get('reason')=='additional_duplicate_provider_ids'
  if ok:candidates.append((r.get('last_attempt',''),{'identity':identity,'job':r['job'],'pages':1}))
 candidates.sort(reverse=True,key=lambda v:v[0]);rows.extend(x[1]for x in candidates[:limit])
# Place evidence-only outcomes after bounded live provider verification.
rows.sort(key=lambda x:x['job']['source']=='edinet_filings')
s.put_object(Bucket=b,Key=base+'/second-jobs.json',Body=json.dumps(rows).encode(),ServerSideEncryption='AES256')
script=s.get_object(Bucket=b,Key=base+'/replay.py')['Body'].read().decode().replace("base+'/jobs.json'","base+'/second-jobs.json'").replace("base+'/steps/'","base+'/second-steps/'").replace("base+'/replay-results.json'","base+'/second-results.json'")
s.put_object(Bucket=b,Key=base+'/second.py',Body=script.encode(),ServerSideEncryption='AES256')
launch=(p/'launch_replays.py').read_text().replace("f=p/'replay.py'","f=p/'second.py'").replace("2026-11-16/replay.py","2026-11-16/second.py").replace('optima-checkup-1116-replays','optima-checkup-1116-second').replace("p/'replay.log'","p/'second.log'")
(p/'launch_second.py').write_text(launch);print('second-pass scopes',len(rows))
