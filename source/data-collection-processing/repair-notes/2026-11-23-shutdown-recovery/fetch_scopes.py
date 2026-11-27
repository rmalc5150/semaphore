import boto3,json
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
def read(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
base='operations/market/automation/73d86afe67f4dc0c545538c8917092c07b4bedb8f92bc1cdb4334e66c029f886/'
for lane in ['daily','historical']:
 d=read(base+lane+'.json');(p/('market-'+lane+'.json')).write_text(json.dumps(d,indent=2))
 for symbol,row in d.get('symbols',{}).items():
  r=row.get('last_result',{})
  if r.get('reason')=='market_ohlc_inconsistent':print('BAD_MARKET',lane,symbol,json.dumps(row));m=read(r['manifest']);(p/('market-bad-'+symbol.replace('/','_')+'.json')).write_text(json.dumps(m,indent=2))
core='operations/streams/656fe06ba4c7d922ad513e4d7f0c104eff4ddcf51cc5ec9f22bfa1afc46c2406/daily/'
for source in ['sec','hkex-filings','documents']:
 d=read(core+source+'/progress-2026-09-21.json');print('CORE',source,{k:d.get(k)for k in ['next_date','last_result','pending_dates']});(p/('core-'+source+'.json')).write_text(json.dumps(d,indent=2))
 if d.get('last_result',{}).get('manifest'):(p/('core-'+source+'-manifest.json')).write_text(json.dumps(read(d['last_result']['manifest']),indent=2))
for lane in ['daily','historical']:
 key='operations/specialists/scheduler/'+lane+'.json'
 d=read(key);found=[(i,r) for i,r in d.get('jobs',{}).items()if r.get('job',{}).get('adapter')=='sam_gov' and r.get('reason')=='sam_source_changed_refresh_required'];print('SAM',lane,[(i,r.get('job',{}).get('start'),r.get('status'))for i,r in found]);(p/('sam-'+lane+'.json')).write_text(json.dumps(found,indent=2))
