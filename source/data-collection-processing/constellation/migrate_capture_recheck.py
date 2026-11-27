"""Move approved heavy capture to bounded, memory-admitted m7 passes."""
import base64
import json
from constellation.finish_aux_migration import remote,M7,T3,ROOT
from constellation.m7_capture_plan import JOBS,UNITS,SOURCE_SCOPES

TARGET='/opt/constellation/capture-workers/source'

def deploy():
 remote(M7,"import shutil,subprocess; subprocess.run(['dnf','install','-y','poppler-utils'],check=True,timeout=240) if not shutil.which('pdftotext') else print('Poppler dependency present')")
 remote(T3,"""import json,time
from pathlib import Path
p=Path('constellation/autostop/m7-deployment-hold.json');p.write_text(json.dumps({'expires_at':time.time()+7200,'reason':'Installing shared guarded capture workers'}))
print('Shared lifecycle deployment hold installed')
""")
 remote(M7,"""from pathlib import Path
import shutil,os
src=Path('/opt/constellation/auxiliary-publication/source');dst=Path(TARGET);dst.mkdir(parents=True,exist_ok=True)
for p in src.glob('*.py'):shutil.copy2(p,dst/p.name)
for folder in ('config','schemas'):
 (dst/folder).mkdir(exist_ok=True)
 for p in (src/folder).iterdir():
  if p.is_file():shutil.copy2(p,dst/folder/p.name)
for folder in ('metadata_engine','constellation'):
 (dst/folder).mkdir(exist_ok=True)
 for p in (src/folder).glob('*.py'):shutil.copy2(p,dst/folder/p.name)
for p in [dst,*dst.glob('*'),*(dst/'config').glob('*'),*(dst/'constellation').glob('*'),*(dst/'metadata_engine').glob('*'),*(dst/'schemas').glob('*')]:
 if p.exists():os.chown(p,1000,1000)
print('Prepared independent capture source; active publication source remains available')
""".replace('TARGET',repr(TARGET)))
 names=['m7_capture_worker.py','specialist_inputs.py','specialist_discovery_queue.py','edinet_pipeline.py','uspto_rate_limit.py','patent_collection.py','patent_operations.py','patent_prosecution_operations.py','grants_review_capture.py','eodhd_daily_cohort.py','eodhd_batch.py','eodhd_quota.py','constellation/m7_capture_plan.py','constellation/shared_limits.py','constellation/control.py','config/source-pauses.json','config/specialist-inputs.json','config/patent-operations.json','config/patent-prosecution-operations.json','config/crossref-resumed-universe.json']
 for name in names:
  data=(ROOT/name).read_bytes()
  if len(data)>52000:
   import boto3,hashlib
   checksum=hashlib.sha256(data).hexdigest();key='research-data/constellation-backfill/deployments/capture-config-'+checksum+'.json'
   boto3.client('s3',region_name='us-east-1').put_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key,Body=data,ServerSideEncryption='AES256')
   remote(M7,"""from pathlib import Path
import boto3,hashlib,os
raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=KEY)['Body'].read();assert hashlib.sha256(raw).hexdigest()==SHA
p=Path(TARGET)/NAME;p.write_bytes(raw);os.chown(p,1000,1000);print('Installed verified config',NAME)
""".replace('TARGET',repr(TARGET)).replace('NAME',repr(name)).replace('KEY',repr(key)).replace('SHA',repr(checksum)))
   continue
  payload=base64.b64encode(data).decode()
  remote(M7,"""from pathlib import Path
import base64,os
p=Path(TARGET)/NAME;p.parent.mkdir(exist_ok=True);tmp=p.with_suffix('.capture-deploy');tmp.write_bytes(base64.b64decode(PAYLOAD));os.chown(tmp,1000,1000);tmp.replace(p);print('Installed',NAME)
""".replace('TARGET',repr(TARGET)).replace('NAME',repr(name)).replace('PAYLOAD',repr(payload)))
 # The reviewed assignment universe is regular source configuration, already
 # present in the worker package; verify its digest before using it.
 import hashlib
 expected=hashlib.sha256((ROOT/'config/crossref-resumed-universe.json').read_bytes()).hexdigest()
 remote(M7,"""import hashlib,json,subprocess,os
from pathlib import Path
root=Path(TARGET);assert hashlib.sha256((root/'config/crossref-resumed-universe.json').read_bytes()).hexdigest()==EXPECTED,'Reviewed universe differs; preserve scope before cutover'
for src,dest,updates in [('patent-operations.json','patent-operations.m7-bounded.json',{'daily_partition_eager_split':True}),('patent-prosecution-operations.json','patent-prosecution-operations.m7-bounded.json',{'max_windows':1,'max_pages':3,'max_requests':40})]:
 d=json.loads((root/'config'/src).read_text());d.update(updates);p=root/'config'/dest;p.write_text(json.dumps(d,indent=2));os.chown(p,1000,1000)
base=Path('/opt/constellation/capture-workers');(base/'eodhd-reports').mkdir(exist_ok=True)
for p in [base,base/'eodhd-reports']:os.chown(p,1000,1000)
slice_name='constellation-workers-capture.slice'
Path('/etc/systemd/system/'+slice_name).write_text('[Slice]\\nCPUAccounting=true\\nMemoryAccounting=true\\nCPUQuota=100%\\nCPUWeight=300\\nMemoryHigh=3G\\nMemoryMax=3328M\\nMemorySwapMax=0\\n')
for name in JOBS:
 unit='optima-m7-capture-'+name+'.service';tmp=Path('/opt/constellation/tmp/publication-staging')/unit;tmp.mkdir(parents=True,exist_ok=True);os.chown(tmp,1000,1000)
 text='[Unit]\\nDescription=Bounded m7 capture '+name+'\\nAfter=network-online.target\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory='+str(root)+'\\nExecStart=/opt/constellation/legacy-venv/bin/python -B m7_capture_worker.py --job '+name+'\\nSlice='+slice_name+'\\nCPUQuota=100%\\nCPUWeight=150\\nMemoryHigh=1536M\\nMemoryMax=2G\\nMemorySwapMax=0\\nTimeoutStartSec=3h\\nTimeoutStopSec=150\\nKillSignal=SIGINT\\nSuccessExitStatus=2 75\\nEnvironment=AWS_DEFAULT_REGION=us-east-1\\nEnvironment=CONSTELLATION_ROLE=worker\\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\\nEnvironment=METADATA_ENGINE_NOTIFY=1\\nEnvironment=ARROW_NUM_THREADS=1\\nEnvironment=MALLOC_ARENA_MAX=2\\nEnvironment=TMPDIR='+str(tmp)+'\\n'
 if name=='edinet-documents-daily':text=text.replace('MemoryHigh=1536M','MemoryHigh=2560M').replace('MemoryMax=2G','MemoryMax=2560M')
 if name in SCOPES:text+='Environment=CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX=operations/specialists/m7-schedulers/'+SCOPES[name]+'\\nEnvironment=CONSTELLATION_SPECIALIST_MODE=daily\\n'
 clean='/opt/constellation/legacy-venv/bin/python /opt/constellation/auxiliary-publication/source/constellation/clean_publication_staging.py '+unit
 text+='ExecStartPre='+clean+'\\nExecStopPost='+clean+'\\n'
 Path('/etc/systemd/system/'+unit).write_text(text)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify',*['optima-m7-capture-'+n+'.service'for n in JOBS]],check=True)
print('Installed eight guarded capture units and a bounded child resource slice')
""".replace('TARGET',repr(TARGET)).replace('EXPECTED',repr(expected)).replace('JOBS',repr(JOBS)).replace('SCOPES',repr(SOURCE_SCOPES)))

def cutover():
 existing=[u for u in UNITS if u not in ('optima-authenticated-processing.service','optima-eia-daily-processing.service')]+['optima-authenticated-daily.service']
 remote(T3,"""import subprocess,json,os,signal,time
from pathlib import Path
from collection_health_exporter import properties,activity
units=UNITS;before={u:properties(u)for u in units};Path('constellation/migration/capture-recheck-t3-before.json').write_text(json.dumps(before,indent=2))
for u in units:subprocess.run(['systemctl','stop',u.replace('.service','.timer')],check=True)
running=[]
for u in units:
 props=properties(u);state,_=activity(props,True)
 if state=='running':running.append(u)
 else:subprocess.run(['systemctl','stop',u],check=True)
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=(p/'cmdline').read_bytes().split(bytes([0]))
  if any(x.endswith(b'/s3_runtime.py')for x in args)and b'--unit'in args:
   unit=args[args.index(b'--unit')+1].decode()
   if unit in running:os.kill(int(p.name),signal.SIGINT);print('Requested durable checkpoint before moving',unit,flush=True)
 except (OSError,ValueError):pass
end=time.monotonic()+210
while any(properties(u).get('ActiveState')in ('active','activating','deactivating')for u in running):
 if time.monotonic()>end:raise RuntimeError('Capture still checkpointing; cutover remains held')
 time.sleep(2)
for u in units:subprocess.run(['systemctl','stop',u],check=True)
print('Migrating t3 payloads stopped with their durable state retained')
""".replace('UNITS',repr(existing)))
 # Copy only the selected pinned cohort state through a worker-readable
 # migration prefix. The worker does not receive access to t3's full cache.
 import boto3
 s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
 current=json.loads(s.get_object(Bucket=bucket,Key='research-data/operations/s3-runtime/current.json')['Body'].read());paths={}
 for name,entry in current['paths'].items():
  if name.startswith('reports/eodhd-auto-')and name.endswith('.json'):
   key='research-data/constellation-backfill/migration/capture-recheck/eodhd-'+entry['sha256']+'.json'
   s.copy_object(Bucket=bucket,Key=key,CopySource={'Bucket':bucket,'Key':entry['key']},ServerSideEncryption='AES256')
   paths[name]={**entry,'key':key}
 selected='research-data/constellation-backfill/migration/capture-recheck/eodhd-state.json'
 s.put_object(Bucket=bucket,Key=selected,Body=json.dumps({'paths':paths}).encode(),ServerSideEncryption='AES256')
 remote(M7,"""import boto3,json,hashlib,os
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');B='data-collection-059416028963-us-east-1-an';d=json.loads(s.get_object(Bucket=B,Key='research-data/constellation-backfill/migration/capture-recheck/eodhd-state.json')['Body'].read());out=Path('/opt/constellation/capture-workers/eodhd-reports');count=0
for name,entry in d['paths'].items():
 if name.startswith('reports/eodhd-auto-')and name.endswith('.json'):
  raw=s.get_object(Bucket=B,Key=entry['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==entry['sha256'];p=out/Path(name).name;p.write_bytes(raw);os.chown(p,1000,1000);count+=1
print('Restored',count,'checksum-verified EODHD plans/results')
""")
 remote(T3,"""from pathlib import Path
import subprocess,json
from monitoring_extra_jobs import extend
units=UNITS
for logical,target in units.items():
 if logical in ('optima-authenticated-processing.service','optima-eia-daily-processing.service'):
  Path('/etc/systemd/system/'+logical).write_text('[Unit]\\nDescription=Dispatch bounded authenticated processing to m7\\n[Service]\\nType=oneshot\\nUser=ec2-user\\nWorkingDirectory=/home/ec2-user/data-collection-processing\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit '+target+'\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\n')
  timer=logical.replace('.service','.timer');Path('/etc/systemd/system/'+timer).write_text('[Unit]\\nDescription=Resume bounded authenticated worker processing\\n[Timer]\\nOnBootSec=2min\\nOnUnitInactiveSec=2min\\nRandomizedDelaySec=15\\n[Install]\\nWantedBy=timers.target\\n')
 else:
  folder=Path('/etc/systemd/system/'+logical+'.d');folder.mkdir(exist_ok=True)
  (folder/'zzzzzzzz-m7-capture.conf').write_text('[Service]\\nExecStart=\\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m constellation.m7_lifecycle dispatch --unit '+target+'\\nSlice=system.slice\\nMemoryHigh=128M\\nMemoryMax=256M\\nCPUQuota=50%\\nTimeoutStartSec=10min\\nReadWritePaths=/home/ec2-user/data-collection-processing/constellation/autostop\\n')
folder=Path('/etc/systemd/system/optima-authenticated-daily.service.d');folder.mkdir(exist_ok=True)
cmd='/usr/bin/flock --exclusive --timeout 43200 --conflict-exit-code 75 /dev/shm/optima-s3/supervisor.lock /home/ec2-user/data-collection-processing/.venv-athena/bin/python -B /home/ec2-user/data-collection-processing/s3_runtime.py --unit optima-authenticated-daily.service -- /usr/bin/timeout --signal=INT --kill-after=120s 5m /home/ec2-user/data-collection-processing/.venv-athena/bin/python -B /home/ec2-user/data-collection-processing/specialist_inputs.py --lane authenticated --mode daily --source sam_gov_opportunities --max-jobs 1 --pages 1 --publish 0'
(folder/'zzzzzzzz-light-sam-capture.conf').write_text('[Service]\\nExecStart=\\nExecStart='+cmd+'\\nMemoryHigh=512M\\nMemoryMax=768M\\nCPUQuota=50%\\n')
cfg=Path('config/collection-monitoring.json');d=json.loads(cfg.read_text());extend(d);cfg.write_text(json.dumps(d,indent=2)+'\\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemd-analyze','verify',*units],check=True)
for u in [*units,'optima-authenticated-daily.service']:
 subprocess.run(['systemctl','enable','--now',u.replace('.service','.timer')],check=True)
 subprocess.run(['systemctl','reset-failed',u],check=False,capture_output=True)
 subprocess.run(['systemctl','start','--no-block',u],check=True)
print('Controller dispatchers activated; SAM remains bounded light capture on t3')
""".replace('UNITS',repr(UNITS)))
 remote(M7,"""import subprocess
for u in UNITS.values():
 state=subprocess.check_output(['systemctl','show',u,'-p','ActiveState','--value'],text=True).strip();print(u,state)
 assert state in ('active','activating','inactive'),u
""".replace('UNITS',repr(UNITS)))
 remote(T3,"""from pathlib import Path
Path('constellation/autostop/m7-deployment-hold.json').unlink(missing_ok=True)
print('Deployment hold removed after worker activation; shared autostop activity checks protect capture')
""")

if __name__=='__main__':deploy();cutover()
