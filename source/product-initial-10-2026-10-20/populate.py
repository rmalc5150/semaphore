raise SystemExit('Retired sample importer: initial ten products were deleted by user request. Use product_catalogue_pipeline.py.')
import json,sys,os,subprocess,uuid,inspect,hashlib,urllib.request,boto3
from pathlib import Path
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
import rds_company_directory as directory
OUT=Path(__file__).resolve().parent
ACTOR='codex-product-initial-10/2026-10-20'
# Reuse the existing audited TLS connection setup without invoking directory queries.
src=inspect.getsource(directory.read_directory)
prefix=src[src.index('    session ='):src.index('    queries =')]
ns=directory.__dict__.copy();exec('def connect():\n'+prefix+'    return command,env,session\n',ns)
command,env,session=ns['connect']()
def run(sql):
 p=subprocess.run(command,input=sql,text=True,capture_output=True,env=env,timeout=60)
 if p.returncode:raise RuntimeError(p.stderr.replace(env['MYSQL_PWD'],'[REDACTED]'))
 return p.stdout.strip()
def v(x):return 'NULL' if x is None else 'CONVERT(0x'+str(x).encode().hex()+' USING utf8mb4) COLLATE utf8mb4_0900_as_cs'
def j(x):return v(json.dumps(x))
assert run('SELECT COUNT(*) FROM tracking.products')=='0','Nonempty registry: stop to reconcile'
I='cmp_4dc3ed4d-ddf8-4853-ab61-fec13686a6fb';F='cmp_72f60a85-0e1d-4bdd-95f2-1fdcc9c53b5f'
for cid,sym in [(I,'ISRG.US'),(F,'FLNC.US')]:
 assert run('SELECT COUNT(*) FROM tracking.companies c JOIN tracking.company_identifiers i USING(company_id) WHERE c.company_id='+v(cid)+" AND c.archived_at IS NULL AND c.review_status<>'rejected' AND i.namespace='eodhd_symbol' AND i.identifier_value="+v(sym))=='1'
D='https://www.intuitive.com/en-us/products-and-services/da-vinci'
data=[
('da Vinci 5',I,'robotics','medical_robotics','commercial','Multiport robotic surgical system.','Integrated robotic instrument control and surgical computing.',D,'minimally_invasive_surgery','Minimally invasive surgery','US'),
('da Vinci Xi',I,'robotics','medical_robotics','commercial','Multiport robotic surgical system.','Articulated instruments, fluorescence imaging and integrated table motion.',D,'minimally_invasive_surgery','Minimally invasive surgery','US'),
('da Vinci X',I,'robotics','medical_robotics','commercial','Entry-level multiport robotic surgical system.','Shares arm architecture and core instrument and vision technology with Xi.',D,'minimally_invasive_surgery','Minimally invasive surgery','US'),
('da Vinci SP',I,'robotics','medical_robotics','commercial','Single-port robotic surgical system.','One arm carries three articulated instruments and a 3D endoscope.',D,'single_port_surgery','Single-port surgery','US'),
('Ion endoluminal system',I,'robotics','medical_robotics','commercial','Robotic bronchoscopy system for lung biopsy.','Shape-sensing catheter navigation and imaging integration.','https://www.intuitive.com/en-us/products-and-services/ion','robotic_bronchoscopy','Robotic bronchoscopy','US'),
('Gridstack',F,'energy_storage','batteries','commercial','Configurable utility-scale battery storage.','Modular storage with embedded controls.','https://fluenceenergy.com/gridstack-grid-energy-storage/','grid_energy_storage','Grid energy storage','unknown'),
('Gridstack Pro',F,'energy_storage','batteries','commercial','Grid-scale battery storage product line.','Integrated modules, battery management and monitoring.','https://fluenceenergy.com/gridstack-pro-energy-storage/','grid_energy_storage','Grid energy storage','unknown'),
('Smartstack',F,'energy_storage','batteries','commercial','Modular industrial battery storage platform.','Control skid and battery pods integrated with Fluence OS.','https://fluenceenergy.com/smartstack-energy-storage/','grid_energy_storage','Grid energy storage','unknown'),
('Ultrastack',F,'energy_storage','batteries','unknown','Battery storage for transmission and distribution networks.','Grid stabilization and network utilization controls.','https://ir.fluenceenergy.com/news-releases/news-release-details/fluence-launches-ultrastack-its-highest-performance-energy','transmission_storage','Storage as a transmission asset','unknown'),
('Sunstack',F,'energy_storage','batteries','unknown','Battery storage for solar-coupled projects.','DC-coupled storage architecture.','https://info.fluenceenergy.com/fluence-on-the-future-of-solar-plus-energy-storage','solar_plus_storage','Solar plus storage','unknown')]
from datetime import datetime,timezone
stamp=datetime.now(timezone.utc).isoformat();sources={}
for url in {r[7] for r in data}:
 e={'source':'official_company_website','reference':url,'retrieved_at':stamp}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=15) as res:raw=res.read()
  sha=hashlib.sha256(raw).hexdigest();key='research-data/source_documents/product_registry/'+sha+'.html'
  session.client('s3').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=raw,ServerSideEncryption='AES256',ContentType='text/html')
  e.update(snapshot='s3://data-collection-059416028963-us-east-1-an/'+key,sha256=sha)
 except Exception as err:e['snapshot_status']='Raw snapshot unavailable: '+type(err).__name__+'; official page reviewed via web tool'
 sources[url]=e
sql=["SET SESSION time_zone='+00:00'",'SET @app_actor='+v(ACTOR)+', @app_change_reason='+v('User-authorized initial research: exactly 10 products, then stop for review'),'START TRANSACTION'];products=[]
for name,cid,sector,sub,life,desc,tech,url,app,appname,geo in data:
 pid='prd_'+str(uuid.uuid4());e=[dict(sources[url])]
 if life=='unknown':e[0]['note']='Historical product evidence; current commercial/discontinued status not established.'
 attrs={'research_batch':ACTOR,'portfolio_coverage':'partial; initial checkpoint','company_identity_basis':'Primary US listing; company pending state preserved'}
 if cid==I:attrs['company_sector_note']='Company sector_ids empty; product independently classified as medical robotics'
 vals=[pid,name,'product',sector,sub,desc,tech,life,'candidate',json.dumps(attrs),'verified',json.dumps(e)]
 sql.append('INSERT INTO tracking.products(product_id,canonical_name,product_type,sector_id,subsector_id,description,technology_summary,lifecycle_status,tracking_status,attributes,review_status,evidence,observed_at,last_reviewed_at) VALUES('+','.join(v(a) for a in vals)+',CURRENT_TIMESTAMP(6),CURRENT_TIMESTAMP(6))')
 # Portfolio association only: no assumption about legal owner or manufacturing subsidiary.
 sql.append('INSERT INTO tracking.product_companies(product_id,company_id,role,territory,review_status,evidence,observed_at) VALUES('+','.join(v(a) for a in [pid,cid,'commercial_partner','unknown','verified',json.dumps(e)])+',CURRENT_TIMESTAMP(6))')
 sql.append('INSERT INTO tracking.product_contexts(product_id,application_key,application_name,geography_key,review_status,evidence,observed_at) VALUES('+','.join(v(a) for a in [pid,app,appname,geo,'verified',json.dumps(e)])+',CURRENT_TIMESTAMP(6))')
 if name=='Ion endoluminal system':sql.append('INSERT INTO tracking.product_aliases(product_id,alias,alias_type,language_code,review_status,evidence,observed_at) VALUES('+','.join(v(a) for a in [pid,'Ion','brand','en','verified',json.dumps(e)])+',CURRENT_TIMESTAMP(6))')
 products.append(dict(product_id=pid,canonical_name=name,company_id=cid,sector_id=sector,lifecycle_status=life,evidence=e))
assert len(products)==10
sql+=['COMMIT','SET @app_actor=NULL,@app_change_reason=NULL']
(OUT/'batch.json').write_text(json.dumps({'batch':ACTOR,'products':products,'limitations':['Company review states unchanged.','Company relationships denote commercial portfolio association, not legal ownership or manufacture.','Regulatory approvals and development stages not inferred.','Current lifecycle unknown for Ultrastack and Sunstack.','Family/predecessor hierarchy requires further reconciliation.']},indent=2))
(OUT/'insert.sql').write_text(';\n'.join(sql)+';\n')
run(';\n'.join(sql)+';')
result=run("SELECT JSON_OBJECT('products',(SELECT COUNT(*) FROM tracking.products),'relationships',(SELECT COUNT(*) FROM tracking.product_companies),'contexts',(SELECT COUNT(*) FROM tracking.product_contexts),'aliases',(SELECT COUNT(*) FROM tracking.product_aliases),'audit_rows',(SELECT COUNT(*) FROM tracking.entity_changes WHERE changed_by="+v(ACTOR)+'))')
(OUT/'verification.json').write_text(result+'\n');print(result)
assert json.loads(result)==dict(products=10,relationships=10,contexts=10,aliases=1,audit_rows=31)
print(run('SELECT product_id,canonical_name,sector_id,lifecycle_status,review_status FROM tracking.products ORDER BY canonical_name'))
