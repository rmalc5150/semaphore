"""Read-only comparison of sampled committed rows and their official originals."""
import io,json,hashlib,zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import boto3,botocore.session

aws=botocore.session.get_session();aws.get_component('credential_provider').remove('login')
s3=boto3.Session(botocore_session=aws,region_name='us-east-1').client('s3')
BUCKET='data-collection-059416028963-us-east-1-an'
BASE='research-data/constellation-backfill/repairs/six-source-review-20261114/'
before=json.loads(s3.get_object(Bucket=BUCKET,Key=BASE+'before.json')['Body'].read())
cache={}
class Reader:
 def get_object(self,**kw):
  key=kw['Key']
  if key not in cache:
   r=s3.get_object(**kw)
   try:body=r['Body'].read(32*1024*1024+1)
   finally:r['Body'].close()
   assert len(body)<=32*1024*1024,'verification artifact exceeds bound'
   if sum(map(len,cache.values()))+len(body)>64*1024*1024:cache.clear()
   cache[key]=body
  return {'Body':io.BytesIO(cache[key]),'ContentLength':len(cache[key])}
reader=Reader()
from metadata_engine.worker import load_input
from research_contract import digest

def original(ref):
 key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
 assert key.startswith('research-data/source_documents/')
 body=reader.get_object(Bucket=BUCKET,Key=key)['Body'].read()
 assert hashlib.sha256(body).hexdigest()==ref['sha256'],'original SHA-256 mismatch'
 return body,key

def verify(row):
 source=row['source'];p=row['payload'];data=p['data'];refs=p.get('source_evidence',[])
 assert refs and all(r.get('sha256')for r in refs)
 if source=='usgs_minerals':
  from usgs_minerals_enrichment import parse_report
  ref=next(r for r in refs if r['source_url']==row['source_url']);body,key=original(ref)
  assert urlsplit(ref['source_url']).hostname=='pubs.usgs.gov'
  assert body.startswith(b'%PDF-')and b'%%EOF'in body[-4096:]
  report=parse_report(body,row['source_url']);saved=data['enrichment']
  for field in ('report_id','pdf_sha256','edition','mineral','page_count','pages','statistics','footnotes','sections','default_unit_caption','supply_chain'):
   assert saved[field]==report[field],'USGS original reparse differs: '+field
  return ref,key,body,{'kind':'mineral_report','edition':report['edition'],'mineral':report['mineral'],'pages':report['page_count'],'extraction_gaps':report['gaps']}
 if source=='eia_battery_generators':
  import openpyxl
  from eia_enrichment import archive_period
  ref=next(r for r in refs if r['source_url']==row['source_url']);body,key=original(ref)
  assert urlsplit(ref['source_url']).hostname=='www.eia.gov'
  assert body.startswith(b'PK') and archive_period(ref['source_url'])==data['report_period']
  with zipfile.ZipFile(io.BytesIO(body))as z:assert sum(i.file_size for i in z.infolist())<=256*1024*1024
  book=openpyxl.load_workbook(io.BytesIO(body),read_only=True,data_only=True)
  try:
   sheet=book[data['sheet']];headers=None;found=None
   for values in sheet.iter_rows(values_only=True):
    cells=[str(v).strip()if v is not None else''for v in values]
    if 'Plant ID'in cells and 'Generator ID'in cells:headers=cells;continue
    if headers is None:continue
    candidate={str(i)+':'+h:c for i,(h,c)in enumerate(zip(headers,cells))if h}
    if candidate==data['values']:found={h:c for h,c in zip(headers,cells)if h in ('Plant ID','Generator ID')};break
   assert found,'battery generator differs from workbook'
   assert row['source_record_id']==digest({'sheet':data['sheet'],'identity':found})
  finally:book.close()
  return ref,key,body,{'kind':'battery_generator_row','sheet':data['sheet'],'report_period':data['report_period'],'identity':found}
 if source=='caiso_prices':
  from caiso_enrichment import parse_archive
  ref=next(r for r in refs if urlsplit(r['source_url']).hostname=='oasis.caiso.com');body,key=original(ref)
  archive=parse_archive(body,p['scope']['query'],ref,nodes={data['NODE']})
  provider={k:v for k,v in data.items()if k not in ('enrichment','unit')}
  matches=[r for r in archive['rows']if r['raw']==provider];assert matches,'CAISO row differs from original ZIP'
  for field in ('price','timing','provenance'):assert data['enrichment'][field]==matches[0][field],'CAISO mismatch: '+field
  assert row['event_at']['value']==matches[0]['timing']['start_utc']
  return ref,key,body,{'kind':'caiso_price_component','node':data['NODE'],'market':data['MARKET_RUN_ID'],'component':data['LMP_TYPE'],'interval_start':matches[0]['timing']['start_utc'],'price':matches[0]['price']}
 if source=='bls_wages':
  ref=next(r for r in refs if urlsplit(r['source_url']).hostname=='api.bls.gov');body,key=original(ref);d=json.loads(body)
  assert d['status']=='REQUEST_SUCCEEDED'
  series=next(s for s in d['Results']['series']if s['seriesID']==data['series'])
  provider={k:v for k,v in data.items()if k not in ('enrichment','series','unit')}
  assert provider in series['data'],'BLS observation differs from original'
  assert row['source_record_id']==':'.join((data['series'],data['year'],data['period']))
  assert data['enrichment']['metadata']['series_id']==data['series']
  return ref,key,body,{'kind':'manufacturing_wage_observation','series':data['series'],'year':data['year'],'period':data['period'],'value':data['value'],'unit':data['unit']}
 if source=='ror_institutions':
  ref=next(r for r in refs if urlsplit(r['source_url']).hostname=='api.ror.org');body,key=original(ref);d=json.loads(body)
  assert data in d['items'],'ROR organization differs from original'
  assert row['source_record_id']==row['source_url']==data['id']
  return ref,key,body,{'kind':'current_institution_identity','ror_id':data['id'],'status':data['status']}
 if source=='eia_retail_prices':
  provider={k:v for k,v in data.items()if k!='enrichment'}
  for ref in refs:
   u=urlsplit(ref['source_url'])
   if u.hostname!='api.eia.gov'or not u.path.endswith('/retail-sales/data/'):continue
   body,key=original(ref);d=json.loads(body)
   if provider in d.get('response',{}).get('data',[]):break
  else:raise AssertionError('EIA retail row differs from original')
  assert row['source_record_id']==':'.join((data['stateid'],data['sectorid'],data['period']))
  assert all(data.get(k+'-units')for k in ('price','sales','revenue','customers'))
  return ref,key,body,{'kind':'monthly_retail_sales_observation','period':data['period'],'state':data['stateid'],'sector':data['sectorid'],'price_units':data['price-units']}
 raise AssertionError('unknown source')

results=[];seen=set()
for source,entry in before.items():
 for job in entry['native_jobs']:
  offset=int(job['input_format'].split('@')[1])if'@'in job['input_format']else 0
  marker=(job['input_key'],offset)
  if marker in seen:continue
  seen.add(marker)
  if sum(r['source']==source for r in results)>=2:break
  try:
   rows,raw,manifest=load_input(reader,BUCKET,job)
   row=rows[offset];ref,key,body,details=verify(row)
   result={'source':source,'job_id':job['job_id'],'input_key':job['input_key'],'input_format':job['input_format'],'record_id':row['record_id'],'source_record_id':row['source_record_id'],
    'status':'verified','collection_commit_verified':True,'original_uri':'s3://'+BUCKET+'/'+key,'original_sha256':hashlib.sha256(body).hexdigest(),'original_bytes':len(body),'source_url':ref['source_url'],'details':details}
  except Exception as error:result={'source':source,'job_id':job['job_id'],'input_key':job['input_key'],'status':'failed','reason':type(error).__name__+': '+str(error)}
  results.append(result);print(json.dumps(result),flush=True)
s3.put_object(Bucket=BUCKET,Key=BASE+'raw-validation.json',Body=json.dumps(results).encode(),ServerSideEncryption='AES256')
assert len(results)==12 and all(r['status']=='verified'for r in results),results
