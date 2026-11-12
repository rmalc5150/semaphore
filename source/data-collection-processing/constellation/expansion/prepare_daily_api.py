"""Give new t3 daily APIs source-owned runtimes instead of the legacy global queue."""
import json,os,uuid
from pathlib import Path
from constellation.control import Control
from constellation.deploy_legacy import dependencies
ROOT=Path(__file__).resolve().parents[2]

def main():
    c=Control();modules=dependencies(['specialist_inputs.py','s3_runtime.py'])
    sources=[r['source'] for r in json.loads((ROOT/'constellation/expansion/new-adapters.json').read_text()) if r.get('daily_enabled',True)]
    response=c.s3.get_object(Bucket=c.config['bucket'],Key=c.config['legacy_seed_key']);seed=json.loads(response['Body'].read());response['Body'].close()
    frozen={k:v for k,v in seed['paths'].items() if k in ('config/company-universe.v0.2.json','config/company-universe.v0.3.json','config/company-universe.v0.5.json')}
    for source in sources:
        root=ROOT/'constellation/daily-workspaces'/source;root.mkdir(parents=True,exist_ok=True)
        for name,body in modules.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body.replace(str(ROOT),str(root)))
        for name in ('control.py','shared_limits.py','sources.py'):
            target=root/'constellation'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text((ROOT/'constellation'/name).read_text().replace(str(ROOT),str(root)))
        for path in (ROOT/'schemas').glob('*.json'):
            target=root/'schemas'/path.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        for name in ('collection-storage.s3.json','sectors.v1.json','constellation-specialist-historical.json','constellation-infrastructure.json','rds-us-east-1-ca-bundle.pem','source-pauses.json'):
            (root/'config').mkdir(exist_ok=True);(root/'config'/name).write_text((ROOT/'config'/name).read_text().replace(str(ROOT),str(root)))
        prefix=c.config['prefix']+'/daily-api-runtime/'+source
        try:c.s3.head_object(Bucket=c.config['bucket'],Key=prefix+'/current.json')
        except c.s3.exceptions.ClientError as e:
            if e.response['Error']['Code'] not in ('404','NoSuchKey'):raise
            state={**seed,'paths':frozen,'run_id':'daily-api-seed-'+uuid.uuid4().hex,'unit':'constellation-public-api-'+source+'.service'}
            body=json.dumps(state,sort_keys=True).encode()
            for key in (prefix+'/manifests/'+state['run_id']+'.json',prefix+'/current.json'):c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256',IfNoneMatch='*')
    # Definitions remain available for publication; the ordinary default daily lane
    # must not run these same tasks concurrently with their private daily owners.
    path=ROOT/'config/specialist-inputs.json';plan=json.loads(path.read_text())
    for row in plan['sources']:
        if row['source'] in sources:row['execution_lane']='independent_public_daily'
    path.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'prepared_independent_daily_apis':sources,'source_modules':len(modules)}))

if __name__=='__main__':main()
