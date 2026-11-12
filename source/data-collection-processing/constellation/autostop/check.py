"""Stop the pinned historical worker only after capture completion with a durable unresolved-failure handoff.

Runs on t3. No idle-CPU, billing-deadline or temporary-empty-queue heuristics.
"""
import argparse,base64,hashlib,json,os,shlex,time
from collections import Counter
from datetime import date,datetime,timezone
from pathlib import Path
from botocore.exceptions import ClientError
from constellation.control import Control,canonical,job_id
from constellation.historical_guard import dispatch_guard
from constellation.legacy_routes import route_hash
from constellation.plan import partitions
from constellation.sources import PROVIDERS
from source_pauses import unit_pause

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
TARGET='i-06241bd1c4e91c2fc'
ARM=HERE/'armed-scope.json'
STATE=HERE/'state.json'
LATEST=HERE/'latest-check.json'
QUIET_SECONDS=600


def write(path,value):
    temporary=path.with_suffix('.updated');temporary.write_bytes(canonical(value)+b'\n');temporary.replace(path)


def scope(config):
    rows=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())['routes']
    active=[r for r in rows if r['execution_enabled'] and r['route_kind']!='migration_probe' and not unit_pause(r.get('original_unit',r['unit']))]
    if not active:raise ValueError('No active historical routes; refuse empty-scope completion')
    end=max(r['end_exclusive'] for r in active)
    files={}
    for name in ('constellation-legacy-routes.json','constellation-specialist-historical.json','constellation-public-sources.json','constellation-core-public.json','source-pauses.json'):
        p=ROOT/'config'/name
        if p.exists():files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    contract={'worker_instance_id':config['worker_instance_id'],'worker_instance_type':config['worker_instance_type'],'legacy_seed_key':config['legacy_seed_key'],
        'raw_sources':sorted(PROVIDERS),'raw_start':'2016-01-01','raw_end_exclusive':end,'config_sha256':files,
        'active_routes':[r['unit'] for r in active],
        'excluded_routes':[{'unit':r['unit'],'reason':r.get('remaining_requirements') or ('migration_probe' if r['route_kind']=='migration_probe' else 'operator_paused')} for r in rows if r not in active]}
    return active,contract,hashlib.sha256(canonical(contract)).hexdigest()


def load_jobs(control):
    with control.db() as cursor:
        cursor.execute("SELECT job_id,source_key,spec_json,status,result_json,updated_at,attempts FROM backfill_jobs WHERE source_key<>'__lease_check__'")
        return cursor.fetchall()


def accepted_raw(row):
    result=json.loads(row.get('result_json') or '{}');spec=json.loads(row['spec_json'])
    if row['status']=='succeeded':
        return result.get('coverage_status')=='verified_complete' and bool(result.get('manifest_uri'))
    if row['status']=='permanently_unavailable':
        return all(result.get(k) for k in ('reason','evidence_uri','reviewed_at')) and result.get('source_key')==spec['source_key'] and result.get('period_start')==spec['start'] and result.get('period_end')==spec['end']
    return False


def evaluate(rows,routes,contract,proofs=None):
    proofs=proofs or {};reasons=[];raw_missing=0;healthy=Counter();index={r['job_id']:r for r in rows};expected=set();failures=[];raw_done=0
    from constellation.autostop.proofs import QUOTA_REASONS
    def failure(row):
        result=json.loads(row.get('result_json') or '{}')
        return row['status'] in ('blocked','retryable_failed','permanently_unavailable') and result.get('reason') not in QUOTA_REASONS
    for source in contract['raw_sources']:
        for spec in partitions(source,date.fromisoformat(contract['raw_start']),date.fromisoformat(contract['raw_end_exclusive'])):
            identity=job_id(spec);expected.add(identity);row=index.get(identity)
            if row is None:raw_missing+=1
            elif accepted_raw(row):raw_done+=1
            elif failure(row):
                result=json.loads(row.get('result_json') or '{}');failures.append({'source':source,'job_id':identity,'start':spec['start'],'end':spec['end'],'reason':result.get('reason') or row['status'],'evidence_uri':result.get('gap_evidence_uri') or result.get('evidence_uri')})
            else:healthy[source+':'+row['status']]+=1
    if raw_missing:reasons.append('raw_partitions_not_registered')
    if healthy:reasons.append('healthy_raw_work_or_quota_wait_remains')
    active={'legacy:'+r['unit']:r for r in routes};undrained=[];ignored=Counter();unknown=[]
    for source,route in active.items():
        proof=proofs.get(route['unit']) or {'state':'unfinished','reason':'route_proof_unavailable'}
        if proof['state'] not in ('complete','failed_only'):undrained.append({'unit':route['unit'],**{k:v for k,v in proof.items() if k!='failures'}})
        failures.extend({'unit':route['unit'],**f} for f in proof.get('failures',[]))
    for row in rows:
        source=row['source_key']
        if source in active:continue  # Proofs distinguish queued failed-only retries from healthy work.
        if source.startswith('legacy:'):
            ignored[row['status']]+=1
            if row['status']=='running':unknown.append(row['job_id'])
        elif row['job_id'] not in expected and not accepted_raw(row):
            if failure(row):failures.append({'source':source,'job_id':row['job_id'],'reason':json.loads(row.get('result_json') or '{}').get('reason') or row['status']})
            else:unknown.append(row['job_id'])
    if undrained:reasons.append('healthy_or_unattempted_legacy_work_remains')
    if unknown:reasons.append('other_healthy_work_remains')
    return {'eligible':not reasons,'reasons':reasons,'expected_raw_partitions':len(expected),'missing_raw_partitions':raw_missing,
        'healthy_raw':dict(healthy),'accounted_raw_partitions':raw_done,'active_routes':len(routes),'undrained_routes':undrained,
        'failures':failures,'failure_count':len(failures),'route_proofs':{k:{a:b for a,b in v.items() if a!='failures'} for k,v in proofs.items()},
        'unknown_healthy_jobs':unknown,'excluded_route_job_counts':dict(ignored),
        'queue_fingerprint':hashlib.sha256(canonical({'scope':contract,'healthy':dict(healthy),'missing':raw_missing,'unfinished':[r['unit'] for r in undrained]})).hexdigest()}


def quiet_ready(previous,scope_sha,queue_sha,now):
    same=previous.get('scope_sha256')==scope_sha and previous.get('queue_fingerprint')==queue_sha
    since=previous.get('eligible_since',now) if same else now
    return now-since>=QUIET_SECONDS,{'scope_sha256':scope_sha,'queue_fingerprint':queue_sha,'eligible_since':since,'phase':'observing_completion'}


DRAIN_SCRIPT=r'''import json,subprocess,time,os
from pathlib import Path
patterns=['constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service']
r=subprocess.run(['systemctl','list-units','--all','--plain','--no-legend',*patterns],capture_output=True,text=True,check=True)
units=[line.split()[0] for line in r.stdout.splitlines() if line.strip()]
if not units:raise RuntimeError('No worker units found; refuse unverifiable drain')
subprocess.run(['systemctl','stop','--no-block',*units],check=True)
deadline=time.monotonic()+210
while True:
 active=[]
 for unit in units:
  state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip()
  if state not in ('inactive','failed'):active.append(unit)
 if not active:break
 if time.monotonic()>deadline:raise RuntimeError('Worker services did not drain: '+str(active))
 time.sleep(2)
pending=[];workspace=[]
for base in (Path('/dev/shm/constellation-legacy'),Path('/dev/shm/optima-s3')):
 if not base.exists():continue
 pending += [str(p) for p in base.rglob('pending.json')]
 for work in base.rglob('work'):
  workspace += [str(p) for p in work.rglob('*') if p.is_file() and not p.is_symlink()]
collectors=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:args=(p/'cmdline').read_bytes().decode().split(chr(0))
 except (OSError,UnicodeDecodeError):continue
 if any(a.startswith('/opt/constellation/legacy/') for a in args) or 'constellation.worker' in args or 'constellation.legacy_worker' in args:collectors.append(int(p.name))
proof={'safe_to_stop':not pending and not workspace and not collectors,'stopped_units':units,'pending_checkpoints':pending,'uncommitted_workspace_files':workspace,'collector_processes':collectors}
print(json.dumps(proof))
if not proof['safe_to_stop']:raise SystemExit(2)
'''


def drain(control):
    compile(DRAIN_SCRIPT,'worker_drain','exec');code='import base64;exec(base64.b64decode('+repr(base64.b64encode(DRAIN_SCRIPT.encode()).decode())+'))'
    session=control.session.client('ssm');identity=session.send_command(InstanceIds=[TARGET],DocumentName='AWS-RunShellScript',Parameters={'commands':['/opt/constellation/.venv/bin/python -c '+shlex.quote(code)],'executionTimeout':['260']},TimeoutSeconds=270)['Command']['CommandId']
    deadline=time.monotonic()+280
    while time.monotonic()<deadline:
        try:r=session.get_command_invocation(CommandId=identity,InstanceId=TARGET)
        except session.exceptions.InvocationDoesNotExist:time.sleep(2);continue
        if r['Status'] in ('Success','Failed','Cancelled','TimedOut'):
            if r['Status']!='Success':raise RuntimeError('Worker drain failed; historical control remains paused. SSM '+identity)
            proof=json.loads(r['StandardOutputContent']);assert proof['safe_to_stop'];return {'command_id':identity,'proof':proof}
        time.sleep(2)
    raise RuntimeError('Worker drain timed out; historical control remains paused. SSM '+identity)


def verify_target(control):
    if control.config['worker_instance_id']!=TARGET or control.config['controller_instance_id']==TARGET:raise ValueError('Pinned historical target mismatch')
    instance=control.session.client('ec2').describe_instances(InstanceIds=[TARGET])['Reservations'][0]['Instances'][0]
    if instance['InstanceType']!=control.config['worker_instance_type']:raise ValueError('Worker type changed; rearm required')
    return instance


def report(control,value):
    timestamp=datetime.now(timezone.utc).isoformat()
    if 'failures' not in value and LATEST.exists():
        prior=json.loads(LATEST.read_text())
        value={**{k:prior[k] for k in ('failures','failure_count','failures_checked_at') if k in prior},**value}
    elif 'failures' in value:value={**value,'failures_checked_at':timestamp}
    value={'checked_at':timestamp,'worker_instance_id':TARGET,'repair_list_uri':'s3://'+control.config['bucket']+'/'+control.config['prefix']+'/monitoring/historical-autostop/latest.json',**value};write(LATEST,value)
    for key in (control.config['prefix']+'/monitoring/historical-autostop/latest.json','research-data/monitoring/health/historical-autostop.json'):
        control.s3.put_object(Bucket=control.config['bucket'],Key=key,Body=canonical(value),ContentType='application/json',ServerSideEncryption='AES256')
    print(json.dumps({'status':value['status'],'reasons':value.get('reasons',[]),'expected_raw_partitions':value.get('expected_raw_partitions'),'missing_raw_partitions':value.get('missing_raw_partitions'),'undrained_routes':len(value.get('undrained_routes',[]))}));return value


def run(control,execute=False,arm=False):
    if os.environ.get('CONSTELLATION_ROLE','controller')!='controller':raise ValueError('Auto-stop must run on t3')
    instance=verify_target(control);routes,contract,scope_sha=scope(control.config)
    if arm:
        # DryRun verifies authorization without changing instance state.
        try:control.session.client('ec2').stop_instances(InstanceIds=[TARGET],DryRun=True)
        except ClientError as e:
            if e.response['Error']['Code']!='DryRunOperation':raise
        write(ARM,{'armed_at':datetime.now(timezone.utc).isoformat(),'scope_sha256':scope_sha,'scope':contract,'target':TARGET});write(STATE,{})
        return report(control,{'status':'armed','scope_sha256':scope_sha,'active_routes':len(routes),'excluded_routes':contract['excluded_routes']})
    if not ARM.exists():return report(control,{'status':'not_armed','reasons':['completion_scope_not_armed']})
    armed=json.loads(ARM.read_text())
    if armed['scope_sha256']!=scope_sha:return report(control,{'status':'scope_changed','reasons':['collection_scope_changed_rearm_required']})
    if instance['State']['Name'] in ('stopping','stopped'):
        saved=json.loads((HERE/'stop-receipt.json').read_text()) if (HERE/'stop-receipt.json').exists() else {}
        return report(control,{**saved,'status':'worker_'+instance['State']['Name']})
    if instance['State']['Name']!='running':return report(control,{'status':'not_running','reasons':['worker_not_running']})
    with dispatch_guard(control) as acquired:
        if not acquired:return report(control,{'status':'guard_busy'})
        state=control.get('control') or {};previous=json.loads(STATE.read_text()) if STATE.exists() else {}
        recovery=previous.get('phase')=='draining' and previous.get('scope_sha256')==scope_sha
        if state.get('pilot_job_ids'):return report(control,{'status':'waiting','reasons':['pilot_jobs_present']})
        if not state.get('enabled') and not recovery:return report(control,{'status':'paused','reasons':['historical_capture_paused_not_complete']})
        rows=load_jobs(control)
        from constellation.autostop.proofs import inspect_routes
        plan=json.loads((ROOT/'config/constellation-specialist-historical.json').read_text())
        proofs=inspect_routes(control,rows,routes,plan)
        evaluation=evaluate(rows,routes,contract,proofs)
        if not evaluation['eligible']:
            if not recovery:write(STATE,{})
            return report(control,{'status':'work_remains',**evaluation})
        ready,candidate=quiet_ready(previous,scope_sha,evaluation['queue_fingerprint'],time.time())
        if not recovery:write(STATE,candidate)
        if not ready and not recovery:return report(control,{'status':'settling','quiet_seconds_required':QUIET_SECONDS,**evaluation})
        if not execute:return report(control,{'status':'ready_dry_run',**evaluation})
        write(STATE,{**candidate,'phase':'draining'})
        control.set_enabled(False)
        report(control,{'status':'draining_for_shutdown',**evaluation})
        proof=drain(control)
        final_rows=load_jobs(control)
        final_proofs=inspect_routes(control,final_rows,routes,plan)
        final=evaluate(final_rows,routes,contract,final_proofs)
        if not final['eligible']:raise RuntimeError('Work changed during drain; remain paused for review')
        _,_,final_sha=scope(control.config)
        if final_sha!=scope_sha:raise RuntimeError('Scope changed during drain; remain paused for review')
        verify_target(control)
        receipt={'failure_count':final['failure_count'],'failures':final['failures'],'status':'capture_finished_stopping','scope_sha256':scope_sha,'completion_scope':contract,'queue':final,'drain':proof,'daily_capture_unchanged':True,'meaning':'Healthy configured work finished; unresolved failures handed to the daily repair list, not marked successful. Not certification of all sources or complete history.'}
        write(HERE/'stop-receipt.json',receipt);report(control,receipt)
        response=control.session.client('ec2').stop_instances(InstanceIds=[TARGET])
        receipt['ec2_states']=response['StoppingInstances'];receipt['status']='stop_requested';write(HERE/'stop-receipt.json',receipt);write(STATE,{**candidate,'phase':'stop_requested'})
        return report(control,receipt)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');parser.add_argument('--arm',action='store_true');args=parser.parse_args()
    control=Control()
    try:run(control,execute=args.execute,arm=args.arm)
    except Exception as error:
        report(control,{'status':'shutdown_check_error','reasons':[type(error).__name__+': '+str(error)[:300]]})
        raise

if __name__=='__main__':main()
