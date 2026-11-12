import json,io,zipfile,hashlib,base64
from pathlib import Path
from urllib.request import urlopen
import boto3
p=Path(__file__).parent;l=boto3.client('lambda',region_name='us-east-1');f=l.get_function(FunctionName='optima-collection-watchdog');raw=urlopen(f['Code']['Location'],timeout=30).read();(p/'watchdog-before.zip').write_bytes(raw);out=io.BytesIO();names={'collection-monitoring.json'}
with zipfile.ZipFile(io.BytesIO(raw)) as old,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as new:
 assert names<=set(old.namelist())
 for info in old.infolist():
  data=old.read(info.filename)
  if info.filename=='collection-monitoring.json':
   config=json.loads(data)
   local=json.loads(Path('config/collection-monitoring.json').read_text())
   for unit,fields in {'optima-search-capture.service':['timer','max_start_gap_seconds','stale_progress_seconds'], 'optima-conference-collection.service':['progress_keys']}.items():
    for field in fields:config['jobs'][unit][field]=local['jobs'][unit][field]
   data=json.dumps(config).encode()
  new.writestr(info,data)
l.update_function_code(FunctionName='optima-collection-watchdog',ZipFile=out.getvalue(),RevisionId=f['Configuration']['RevisionId']);l.get_waiter('function_updated_v2').wait(FunctionName='optima-collection-watchdog');r=l.get_function_configuration(FunctionName='optima-collection-watchdog');assert r['CodeSha256']==base64.b64encode(hashlib.sha256(out.getvalue()).digest()).decode()
(p/'monitoring-deployment.json').write_text(json.dumps({'status':r['LastUpdateStatus'],'sha256':r['CodeSha256'],'changed_modules':sorted(names),'notifications_sent':False},indent=2));print(r['LastUpdateStatus'])
