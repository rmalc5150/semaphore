import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
import boto3
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
def load(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
r=load('operations/streams/'+stream+'/historical/uk/2016-01-01_2016-02-01.json');m=load(r['manifest']);print('UK_MANIFEST',json.dumps(m)[-4000:])
for r in subprocess.run(['systemctl','list-unit-files','--no-pager'],capture_output=True,text=True).stdout.splitlines():
 if ('news' in r and 'service' in r and 'historical' not in r) or 'summary' in r:print('UNIT',r)
print('LOCKS',subprocess.run(['lslocks','--output','PID,COMMAND,PATH'],capture_output=True,text=True).stdout[-1600:])
