import json,hashlib,os
from pathlib import Path
import boto3
body=boto3.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/constellation-backfill/deployments/pdf-fallback-20261118/85d7d92825b667cba2fe83ebffd05968b0ff45c801450a65c0d65def325784d6.json')['Body'].read();assert hashlib.sha256(body).hexdigest()=='85d7d92825b667cba2fe83ebffd05968b0ff45c801450a65c0d65def325784d6';data=json.loads(body)
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/summary-worker'),*Path('/opt/constellation/legacy').glob('*')];planned=[];skipped=[]
for root in roots:
 if (root/'regulatory_collection.py').exists():
  planned.extend([(root,'pdf_proxy_fallback.py',data['helper']),(root,'config/pdf-proxy-fallback.json',json.dumps(data['config'],indent=2)+'\n')])
 for name in ['regulatory_collection.py','additional_source_apis.py','public_source_capture.py','specialist_inputs.py','collection_alerts.py','constellation/gaps.py']:
  path=root/name
  if not path.is_file():continue
  old=path.read_text();new=old
  if name=='regulatory_collection.py' and 'def _get_direct('not in old:
   needle='    def get(self, url, params=None, body=None, api_key=None, no_matches=False, api_key_parameter="api_key", persist=True):\n'
   if old.count(needle)!=1:skipped.append(str(path));continue
   new=old.replace(needle,data['wrapper'],1)
  elif name=='additional_source_apis.py':
   a=old.index("    if kind=='additional_biorxiv':");z=old.index("    if kind=='additional_datacite':",a);new=old[:a]+data['biorxiv']+old[z:]
  elif name=='public_source_capture.py' and 'from pdf_proxy_fallback import settings as pdf_settings'not in old:
   needle="        if response.status_code in (403, 429, 503) and source.get('decodo'):"
   if old.count(needle)!=1:skipped.append(str(path));continue
   new=old.replace(needle,data['public'],1)
  elif name=='specialist_inputs.py' and 'pdf_proxy_daily_budget'not in old:
   needle="        code = exc.code if isinstance(exc, SourceIssue) else 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'collection_error'"
   if old.count(needle)!=1:skipped.append(str(path));continue
   new=old.replace(needle,needle+"\n        if isinstance(exc,SourceIssue) and code in {'pdf_proxy_daily_budget','pdf_proxy_url_cooldown','pdf_proxy_client_budget'}:status='partial'",1)
  elif name=='collection_alerts.py' and 'pdf_proxy_daily_budget'not in old:
   new=old.replace('EXPECTED = {',"EXPECTED = {\n    'pdf_proxy_daily_budget', 'pdf_proxy_url_cooldown', 'pdf_proxy_client_budget',",1)
  elif name=='constellation/gaps.py' and 'pdf_proxy_daily_budget'not in old:
   new=old.replace("'decodo_web_data_daily_budget'}", "'decodo_web_data_daily_budget','pdf_proxy_daily_budget','pdf_proxy_url_cooldown','pdf_proxy_client_budget'}")
  if new!=old:planned.append((root,name,new))
for root,name,value in planned:
 if name.endswith('.py'):compile(value,name,'exec')
 else:json.loads(value)
for root,name,value in planned:
 target=root/name
 if target.exists() and target.read_text()==value:continue
 if target.exists():
  backup=Path('/opt/constellation/tmp/pdf-fallback-20261118-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_bytes(target.read_bytes())
 target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.proxy-tmp');temp.write_text(value);os.chmod(temp,0o644);temp.replace(target)
print(json.dumps({'planned_files':len(planned),'skipped':skipped,'config_enabled':data['config']['enabled']}))
