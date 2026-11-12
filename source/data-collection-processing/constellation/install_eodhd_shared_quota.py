"""Quiesce EODHD callers and install one account-wide conditional S3 budget."""
import base64,json
from constellation.finish_aux_migration import remote,M7,T3,ROOT

def main():
 remote(T3,"import subprocess;subprocess.run(['systemctl','stop','optima-market-collection.service','optima-eodhd-profiles.service'],check=True);print('Controller EODHD callers quiesced')")
 remote(M7,"import subprocess;subprocess.run(['systemctl','kill','--kill-whom=main','--signal=SIGINT','optima-m7-eodhd-inventory.service'],capture_output=True);subprocess.run(['systemctl','stop','optima-m7-eodhd-inventory.service'],check=True);print('Worker EODHD inventory quiesced')")
 config=json.loads((ROOT/'config/eodhd-quota.json').read_text())
 config['shared_s3']={'region':'us-east-1','bucket':'data-collection-059416028963-us-east-1-an','key':'research-data/operations/eodhd/shared-quota.json'}
 config['scope']='All configured controller and m7 clients; one weighted daily budget and rolling request rate, reserved using conditional S3 writes before each HTTP attempt.'
 payload=base64.b64encode((ROOT/'eodhd_quota.py').read_bytes()).decode()
 # Seed conservatively from the freshest provider usage, retaining any stronger existing reservation.
 remote(M7,'''import os,sys,json,base64,boto3,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root))
from eodhd_universe import EODHDClient
from research_contract import load_json
client=EODHDClient.configured(load_json(root/'config/eodhd-universe.json'));account=client.account();old=client.quota.status()
p=root/'eodhd_quota.py';tmp=p.with_suffix('.quota-deploy');tmp.write_bytes(base64.b64decode(__PAYLOAD__));os.chown(tmp,1000,1000);tmp.replace(p)
import importlib,eodhd_quota;importlib.reload(eodhd_quota)
cfg=__CONFIG__;quota=eodhd_quota.S3Quota(cfg);quota.sync(account)
def seed(doc):
 row=doc['days'][quota.day()]
 row['used']=max(row['used'],old.get('reserved_calls',0))
 return None,True
quota.change(seed)
target=root/'config/eodhd-quota.json';target.write_text(json.dumps(cfg,indent=2));os.chown(target,1000,1000)
print(json.dumps({'shared_quota_seeded':True,'usage':quota.status(),'credentials_exported':False}))
'''.replace('__PAYLOAD__',repr(payload)).replace('__CONFIG__',repr(config)))
 remote(T3,'''import json,subprocess,os
from pathlib import Path
p=Path('/home/ec2-user/data-collection-processing/config/eodhd-quota.json');p.write_text(json.dumps(__CONFIG__,indent=2));os.chown(p,1000,1000)
subprocess.run(['systemctl','start','--no-block','optima-market-collection.service','optima-eodhd-profiles.service'],check=True)
print('Controller clients now share the m7 weighted quota')
'''.replace('__CONFIG__',repr(config)))
 remote(M7,"import subprocess;subprocess.run(['systemctl','start','--no-block','optima-m7-eodhd-inventory.service'],check=True);print('Worker inventory restarted with shared quota')")

if __name__=='__main__':main()
