import boto3,json,subprocess
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
d=json.loads(s.get_object(Bucket=b,Key='research-data/monitoring/health/latest.json')['Body'].read());(p/'health-after.json').write_text(json.dumps(d,indent=2));print('health',d['checked_at'],'errors',d.get('errors'),'cache_checks',d.get('s3_batch_checks'));print(subprocess.run(['systemctl','show','optima-collection-health.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
c=Path('state/collection-health/health-verified-batches.json');print('cache_exists',c.exists(),'bytes',c.stat().st_size if c.exists()else None)
