import json,io,zipfile,hashlib,base64
from pathlib import Path
from urllib.request import urlopen
import boto3
p=Path(__file__).parent;l=boto3.client('lambda',region_name='us-east-1');f=l.get_function(FunctionName='optima-collection-watchdog');raw=urlopen(f['Code']['Location'],timeout=30).read();(p/'watchdog-before.zip').write_bytes(raw);out=io.BytesIO();names={'collection_alerts.py'}
with zipfile.ZipFile(io.BytesIO(raw)) as old,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as new:
 assert names<=set(old.namelist())
 for info in old.infolist():new.writestr(info,Path(info.filename).read_bytes()if info.filename in names else old.read(info.filename))
l.update_function_code(FunctionName='optima-collection-watchdog',ZipFile=out.getvalue(),RevisionId=f['Configuration']['RevisionId']);l.get_waiter('function_updated_v2').wait(FunctionName='optima-collection-watchdog');r=l.get_function_configuration(FunctionName='optima-collection-watchdog');assert r['CodeSha256']==base64.b64encode(hashlib.sha256(out.getvalue()).digest()).decode()
(p/'monitoring-deployment.json').write_text(json.dumps({'status':r['LastUpdateStatus'],'sha256':r['CodeSha256'],'changed_modules':sorted(names),'notifications_sent':False},indent=2));print(r['LastUpdateStatus'])
