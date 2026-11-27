import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
import boto3
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
def load(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
proof=load('constellation-backfill/repairs/2026-11-16-afternoon/monitoring-reconciliation.json');print('PROOF_KEYS',list(proof))
counts={};examples=[]
for row in proof['fda_windows']:
 wid=row['task_id'].removeprefix('task_');prefix='research-data/operations/regulatory/'
 for kind in ['publication-queue','publication-receipts']:
  try:r=load('operations/regulatory/'+kind+'/'+wid+'.json');status=r.get('status','present')
  except s.exceptions.NoSuchKey:status='missing'
  counts[kind+':'+status]=counts.get(kind+':'+status,0)+1
 if len(examples)<1:examples.append(wid)
print('FDA',counts,'EXAMPLE',examples)
for line in subprocess.run(['systemctl','list-unit-files','--no-pager'],capture_output=True,text=True).stdout.splitlines():
 if 'news-collection' in line and line.split()[0].endswith('.service') and 'historical' not in line:print('NEWS_UNIT',line)
