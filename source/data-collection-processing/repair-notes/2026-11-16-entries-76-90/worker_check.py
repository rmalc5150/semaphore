"""Read-only capture, historical-executor and metadata service inventory."""
import contextlib, io, json
from pathlib import Path
from constellation.finish_aux_migration import remote, T3, M7, session

CODE = '''import json,subprocess,time,boto3
from pathlib import Path
def run(args):return subprocess.run(args,capture_output=True,text=True).stdout.strip()
files=json.loads(run(['systemctl','list-unit-files','optima-*','constellation-*','--output=json']))
loaded=json.loads(run(['systemctl','list-units','--all','optima-*','constellation-*','--output=json']))
units=sorted({r['unit_file']for r in files if r['unit_file'].endswith('.timer')}|{r['unit']for r in loaded})
raw=run(['systemctl','show',*units,'-p','Id','-p','LoadState','-p','ActiveState','-p','SubState','-p','UnitFileState','-p','Result','-p','ExecMainStatus','-p','ExecMainStartTimestamp','-p','ExecMainExitTimestamp','-p','CPUQuotaPerSecUSec','-p','MemoryMax','-p','ExecStart','-p','WorkingDirectory'])
props={}
for block in raw.split('\\n\\n'):
 d=dict(line.split('=',1)for line in block.splitlines()if'='in line)
 if d.get('Id'):props[d['Id']]=d
out={'checked_at_epoch':time.time(),'host':HOST,'units':props,
 'failed':run(['systemctl','list-units','--failed','optima-*','constellation-*','--no-pager','--no-legend']),
 'memory':run(['free','-m']),'cpu':run(['vmstat','1','3']),
 'pool':run(['systemctl','show','optima-data.slice','constellation-workers.slice','-p','Id','-p','CPUQuotaPerSecUSec','-p','MemoryMax','-p','MemoryCurrent']),
 'recent_kernel_oom':run(['journalctl','-k','--since','30 minutes ago','--grep','oom-kill|Out of memory','-n','8','--no-pager'])}
if HOST=='t3':
 from metadata_engine.runtime_db import Database
 cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg)
 with db.tx()as c:
  c.execute('SELECT source_key,state,last_reason FROM engine_sources ORDER BY source_key');out['source_controls']=c.fetchall()
 out['intentional_pauses']=json.load(open('config/source-pauses.json'))
 out['retirement']=json.load(open('constellation/migration/tracking-retirement.json'))['retired_units']
key='research-data/constellation-backfill/repairs/entries-76-90-20261116/worker-check-'+HOST+'.json'
boto3.client('s3',region_name='us-east-1').put_object(Bucket=BUCKET,Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
print(json.dumps({'key':key}))
'''

P = Path(__file__).parent
B = 'data-collection-059416028963-us-east-1-an'
for host, instance in (('t3', T3), ('m7', M7)):
    cap = io.StringIO()
    with contextlib.redirect_stdout(cap):
        remote(instance, CODE.replace('HOST', repr(host)).replace('BUCKET', repr(B)))
    response = json.loads(cap.getvalue());assert response['status'] == 'Success', response
    key = json.loads(response['out'])['key']
    body = session.client('s3').get_object(Bucket=B, Key=key)['Body'].read()
    (P / ('worker-check-' + host + '.json')).write_bytes(body)
    data = json.loads(body)
    inactive = [u for u, v in data['units'].items() if u.endswith('.timer') and v.get('UnitFileState') == 'enabled' and v['ActiveState'] != 'active']
    executors = [u for u, v in data['units'].items() if u.startswith(('constellation-backfill@', 'constellation-legacy-worker@', 'constellation-public-worker@')) and v['ActiveState'] == 'active']
    print(host, 'inactive_enabled_timers', inactive, 'active_historical_executors', len(executors), 'failed', data['failed'])
