"""Install and verify the configured resize plan while historical execution is paused."""
import base64,hashlib,json,shlex,tarfile
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]

def main():
    c=Control();assert not c.allowed();plan=c.config['worker_resize_plan'];target=plan['worker_instance_type']
    assert plan.get('allow_shared_memory_oversubscription') or plan['raw_workers']*384+plan['legacy_workers']*1536+plan['public_workers']*512<=plan['memory_max_gib']*1024
    i=c.session.client('ec2').describe_instances(InstanceIds=[c.config['worker_instance_id']])['Reservations'][0]['Instances'][0]
    assert i['InstanceType']==target and i['State']['Name']=='running'
    bundle=ROOT/'constellation/expansion/resized-worker.tar.gz'
    with tarfile.open(bundle,'w:gz') as a:
        for n in ('control.py','constellation-workers.slice','constellation-backfill@.service','constellation-legacy-worker@.service','constellation-public-worker@.service'):a.add(ROOT/'constellation'/n,arcname=n,recursive=False)
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest();key=c.config['prefix']+'/deployments/resized-worker-'+digest+'.tar.gz';c.s3.upload_file(str(bundle),c.config['bucket'],key,ExtraArgs={'ServerSideEncryption':'AES256'})
    code=r'''import boto3,hashlib,json,os,subprocess,tarfile
from pathlib import Path
plan=PLAN
base=Path('/opt/constellation')
def run(*args):return subprocess.check_output(args,text=True).strip()
def property(unit,name):return run('systemctl','show',unit,'-p',name,'--value')
assert subprocess.call(['mountpoint','-q',str(base)])==0
assert (base/'.venv/bin/python').exists()
assert os.cpu_count()==plan['cpu_capacity']
s3=boto3.client('s3',region_name='us-east-1');bundle=base/'tmp/resized-worker.tar.gz';s3.download_file(BUCKET,KEY,str(bundle));assert hashlib.sha256(bundle.read_bytes()).hexdigest()==DIGEST
dest=base/'tmp/resized-worker';dest.mkdir(exist_ok=True)
with tarfile.open(bundle) as archive:
 for member in archive.getmembers():assert '/' not in member.name and member.isfile()
 archive.extractall(dest)
for path in dest.iterdir():
 run('install','-m','0644',str(path),str(base/'constellation'/path.name) if path.suffix=='.py' else '/etc/systemd/system/'+path.name)
groups={'raw':('constellation-backfill',5,384,320),'legacy':('constellation-legacy-worker',8,1536,1250),'public':('constellation-public-worker',4,512,448)}
all_units=[name+'@'+str(i)+'.service' for name,count,_,_ in groups.values() for i in range(1,count+1)]
run('systemctl','disable','--now',*all_units)
run('systemctl','daemon-reload')
run('systemctl','set-property','constellation-workers.slice','CPUQuota='+str(plan['cpu_capacity']*100)+'%','MemoryHigh='+str(plan['memory_high_gib'])+'G','MemoryMax='+str(plan['memory_max_gib'])+'G','MemorySwapMax=0')
selected=[]
for kind,(prefix,_,maximum,high) in groups.items():
 for i in range(1,plan[kind+'_workers']+1):
  unit=prefix+'@'+str(i)+'.service';selected.append((unit,maximum))
  run('systemctl','set-property',unit,'CPUQuota='+str(plan['cpu_capacity']*100)+'%','MemoryHigh='+str(high)+'M','MemoryMax='+str(maximum)+'M')
path=base/'config/constellation-infrastructure.json';cfg=json.loads(path.read_text());assert 'controller_secret_arn' not in cfg
cfg.update(worker_instance_type=plan['worker_instance_type'],concurrency=len(selected),collection_enabled=True)
cfg.setdefault('worker_pool',{}).update({k:v for k,v in plan.items() if k not in ('worker_instance_type','limits_installation_pending')})
cfg['worker_resize_plan']={**plan,'limits_installation_pending':False}
temporary=path.with_suffix('.new');temporary.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(temporary,1000,1000);temporary.replace(path)
run('systemctl','enable','--now',*[n for n,_ in selected])
assert property('constellation-workers.slice','CPUQuotaPerSecUSec')==str(plan['cpu_capacity'])+'s'
assert int(property('constellation-workers.slice','MemoryMax'))==plan['memory_max_gib']*1024**3
assert int(property('constellation-workers.slice','MemoryHigh'))==plan['memory_high_gib']*1024**3
for unit,mib in selected:
 assert run('systemctl','is-active',unit)=='active'
 assert run('systemctl','is-enabled',unit)=='enabled'
 assert int(property(unit,'MemoryMax'))==mib*1024**2
for unit in set(all_units)-{n for n,_ in selected}:
 assert subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()=='inactive'
 assert subprocess.run(['systemctl','is-enabled',unit],capture_output=True,text=True).stdout.strip()=='disabled'
assert not list(Path('/dev/shm/constellation-legacy').rglob('pending.json'))
print(json.dumps({'verified':True,'active_enabled_workers':len(selected),'cpu_capacity':plan['cpu_capacity'],'memory_max_gib':plan['memory_max_gib'],'sum_individual_memory_max_mib':sum(m for _,m in selected),'instance_type':plan['worker_instance_type']}))
'''.replace('PLAN',repr(plan)).replace('BUCKET',repr(c.config['bucket'])).replace('KEY',repr(key)).replace('DIGEST',repr(digest))
    command='/opt/constellation/.venv/bin/python -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(base64.b64encode(code.encode()).decode())+'))')
    r=c.session.client('ssm').send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=300)
    receipt={'command_id':r['Command']['CommandId'],'bundle_sha256':digest,'plan':plan,'historical_queue_still_paused':True};(ROOT/'constellation/expansion/resized-worker-installation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
