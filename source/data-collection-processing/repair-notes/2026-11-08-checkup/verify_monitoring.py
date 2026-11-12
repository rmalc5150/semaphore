import json,time,boto3
from pathlib import Path
from collection_health_exporter import Evidence,inspect_job
from collection_alerts import evaluate
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');c=json.load(open('config/collection-monitoring.json'))
h=json.load(open(p/'health.json'));prior=json.load(open(p/'state.json'));now=time.time();h['checked_at']=now
for unit in ['optima-conference-publication.service','optima-daily-health-audit.service']:
 h['jobs'][unit]=inspect_job(unit,c['jobs'][unit],Evidence(s,c['bucket'],c['data_prefix']),now-3600,now)
h['daily_audit']=json.loads(s.get_object(Bucket=c['bucket'],Key=c['prefix']+'/daily-health/latest.json')['Body'].read())
active,_=evaluate(h,prior,c,now)
report={'checked_at':now,'selected_jobs':{k:h['jobs'][k] for k in ['optima-conference-publication.service','optima-daily-health-audit.service']},'audit':h['daily_audit'],'selected_remaining':{k:v for k,v in active.items() if v['unit'] in ['optima-conference-publication.service','optima-daily-health-audit.service']}}
(p/'monitoring-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({'selected_remaining':report['selected_remaining'],'audit_queries':report['audit'].get('queries'),'audit_failures':report['audit'].get('query_failures')}))
