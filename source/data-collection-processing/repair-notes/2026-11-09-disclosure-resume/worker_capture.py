"""Isolated bounded disclosure capture using the existing immutable universe and cursors."""
import argparse,json,hashlib
from pathlib import Path
import boto3
from collection_storage import StorageSettings
from disclosure_content_backfill import run,prefix_for,read,run_stage
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['daily','historical'],required=True);args=p.parse_args()
root=Path(__file__).resolve().parent;config=json.loads((root/'config/s11-content-backfill.json').read_text());settings=StorageSettings.load(root/config['storage_config']);s=boto3.client('s3',region_name=settings.region)
# This frozen reviewed snapshot is the existing v0.5 universe; no fixture substitution.
key='research-data/operations/s3-runtime/snapshots/migration-seed/'+config['universe'];body=s.get_object(Bucket=settings.s3_bucket,Key=key)['Body'].read();assert hashlib.sha256(body).hexdigest()=='fc53f3cdc196e0fb55df2ad5c8f0d6386ad64ea6556b84cfaf9d6e3b742296cf';universe=json.loads(body);taxonomy=json.loads((root/config['taxonomy']).read_text());store=settings.store();prefix=prefix_for(config,universe,taxonomy,args.mode)
print(json.dumps({'stage':'capture_start','mode':args.mode,'state_key':prefix+'/state.json','before':read(store,prefix+'/state.json')}),flush=True)
def bounded_stage(stage,day,mode,stages,store,settings,config,universe,taxonomy,cache):
    # Increase work per resume without changing task/checkpoint identity.
    budget={**config,'hkex_pages_per_invocation':10} if stage=='hkex' else config
    return run_stage(stage,day,mode,stages,store,settings,budget,universe,taxonomy,cache)
result=run(store,settings,config,universe,taxonomy,boto3.client('sns',region_name=settings.region),args.mode,max_days=1,stage_runner=bounded_stage)
print(json.dumps({'stage':'capture_result','mode':args.mode,'result':result}),flush=True)
