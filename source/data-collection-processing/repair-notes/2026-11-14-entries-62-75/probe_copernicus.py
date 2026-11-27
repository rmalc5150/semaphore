import json
from ops import remote,M7,session,B,BASE,P
lanes=json.loads((P/'source-lanes.json').read_text());states=lanes['copernicus_era5_era5_land']['schedulers'];bad=[j for key,v in states.items()if '/daily-api-'in key for j in v['jobs'].values()if j.get('reason')=='source_http_404'];job=max(bad,key=lambda j:j['last_attempt'])['job']
code='''import sys,os,json,requests
os.chdir('/opt/constellation/auxiliary-publication/source');sys.path.insert(0,os.getcwd())
from collection_storage import StorageSettings
from research_contract import ROOT,digest
from additional_source_apis import credentials
from datetime import date,timedelta
job=JOB;p=job['parameters'];start=p['data_start'];end=p['data_end'];day=date.fromisoformat(start);days=[]
while day<date.fromisoformat(end):days.append(day.strftime('%d'));day+=timedelta(days=1)
request={'variable':['2m_temperature','total_precipitation'],'year':[start[:4]],'month':[start[5:7]],'day':days,'time':[f'{h:02d}:00'for h in range(24)],'area':p['area'],'data_format':'netcdf','download_format':'unarchived'}
if p['dataset']=='reanalysis-era5-single-levels':request['product_type']=['reanalysis']
key='constellation-backfill/copernicus/submissions/'+digest({'dataset':p['dataset'],'request':request})+'.json';store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store();saved=store.get(key);state=json.loads(saved.body);r=requests.get('https://cds.climate.copernicus.eu/api/retrieve/v1/jobs/'+state['job_id'],headers={'PRIVATE-TOKEN':credentials()['copernicus'].strip()},timeout=30)
print(json.dumps({'submission_key':key,'saved_state':state,'http_status':r.status_code,'body':r.text[:1600],'requested_start':start,'requested_end':end}))
'''.replace('JOB',repr(job));r=remote(M7,code);(P/'copernicus-expiry-probe.json').write_text(r['out']);print(r['out'])
