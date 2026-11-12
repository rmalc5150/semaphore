"""Add four public-only executors while keeping maximum worker RAM below 16 GiB."""
import hashlib,json,shlex,tarfile
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]

def main():
    assert 5*384+8*1536+4*512<=16*1024
    c=Control();bundle=ROOT/'constellation/expansion/public-pool.tar.gz'
    with tarfile.open(bundle,'w:gz') as archive:
        for name in ('control.py','legacy_worker.py','coverage_scope.py','constellation-public-worker@.service','constellation-backfill@.service'):
            archive.add(ROOT/'constellation'/name,arcname='constellation/'+name,recursive=False)
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest();key=c.config['prefix']+'/deployments/public-pool-'+digest+'.tar.gz';c.s3.upload_file(str(bundle),c.config['bucket'],key,ExtraArgs={'ServerSideEncryption':'AES256'})
    script=r'''set -eu
cd /opt/constellation
aws s3 cp URL tmp/public-pool.tar.gz --only-show-errors --region us-east-1
echo 'HASH  tmp/public-pool.tar.gz' | sha256sum --check --status
/opt/constellation/.venv/bin/python - <<'CHECK'
import subprocess
for i in range(1,6):
 current=int(subprocess.check_output(['systemctl','show','constellation-backfill@'+str(i)+'.service','-p','MemoryCurrent','--value']))
 if current>300*1024**2:raise RuntimeError('Retain the existing raw-worker limit: current memory exceeds the reduction guard')
CHECK
tar -xzf tmp/public-pool.tar.gz --no-same-owner
install -m 0644 constellation/constellation-public-worker@.service constellation/constellation-backfill@.service /etc/systemd/system/
systemctl daemon-reload
for i in {1..5}; do systemctl set-property --runtime constellation-backfill@$i.service MemoryHigh=320M MemoryMax=384M; done
systemctl enable --now constellation-public-worker@{1..4}.service
systemctl is-active constellation-public-worker@{1..4}.service constellation-legacy-worker@{1..8}.service constellation-backfill@{1..5}.service
systemctl show constellation-workers.slice -p CPUQuotaPerSecUSec -p MemoryMax -p MemoryCurrent
'''.replace('URL',shlex.quote('s3://'+c.config['bucket']+'/'+key)).replace('HASH',digest)
    command=c.session.client('ssm').send_command(InstanceIds=[c.config['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':['bash -c '+shlex.quote(script)]},TimeoutSeconds=180)['Command']['CommandId']
    result={'command_id':command,'sha256':digest,'raw_workers':5,'raw_memory_max_mib':384,'legacy_workers':8,'legacy_memory_max_mib':1536,'public_workers':4,'public_memory_max_mib':512,'total_workers':17,'sum_individual_memory_max_mib':16256,'aggregate_memory_max_mib':16384,'aggregate_cpu_limit':16}
    (ROOT/'constellation/expansion/public-pool-deployment.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
