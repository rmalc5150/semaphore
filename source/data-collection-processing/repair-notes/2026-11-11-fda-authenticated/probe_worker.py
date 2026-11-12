import boto3,json,base64,time
from pathlib import Path
p=Path(__file__).parent
code='''import json,time
from specialist_authenticated import request,table_rows
from specialist_inputs import SpecialistClient
from collection_storage import StorageSettings
settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store()
for source,kind,url,body in [
 ('fda_dd_compliance_actions','fda-dashboard','https://api-datadashboard.fda.gov/v1/compliance_actions',{'start':1,'rows':1,'sort':'','sortorder':'ASC','returntotalcount':True,'columns':[],'filters':{'ActionTakenDateFrom':['2026-10-01'],'ActionTakenDateTo':['2026-11-10']}}),
 ('fda_dd_import_refusals','fda-dashboard','https://api-datadashboard.fda.gov/v1/import_refusals',{'start':1,'rows':1,'sort':'','sortorder':'ASC','returntotalcount':True,'columns':[],'filters':{'RefusalDateFrom':['2026-10-01'],'RefusalDateTo':['2026-11-10']}}),
 ('fda_dd_inspections_citations','fda-dashboard','https://api-datadashboard.fda.gov/v1/inspections_citations',{'start':1,'rows':1,'sort':'','sortorder':'ASC','returntotalcount':True,'columns':[],'filters':{'InspectionEndDateFrom':['2026-10-01'],'InspectionEndDateTo':['2026-11-10']}}),
 ('fda_ires_recalls','fda-enforcement','https://www.accessdata.fda.gov/rest/iresapi/recalls/',{'displaycolumns':'','filter':json.dumps([{'eventlmdfrom':'10/28/2026'},{'eventlmdto':'10/28/2026'}]),'start':1,'rows':1,'sort':'productid','sortorder':'asc'}),
 ('fda_product_codes','fda-productcodes','https://www.accessdata.fda.gov/rest/pcbapi/v1/industry/',None)]:
 client=SpecialistClient(store,source)
 try:
  result=request(client,kind,url,{'signature':str(time.time_ns())}if kind!='fda-dashboard'else None,body=body,form=kind=='fda-enforcement');rows=result.get('result',[])if kind=='fda-dashboard'else table_rows(result);out={'source':source,'status':'success','row_count':len(rows),'fields':list(rows[0])if rows else[],'evidence':client.evidence}
 except Exception as error:out={'source':source,'status':'failed','reason':str(error)}
 print(json.dumps(out),flush=True)
'''
enc=base64.b64encode(code.encode()).decode();cmd="systemd-run --unit=optima-fda-authenticated-probe-1111 --wait --property=User=ec2-user --property=WorkingDirectory=/opt/constellation/source --property=Slice=constellation-workers.slice --property=MemoryMax=402653184 --property=CPUQuota=20% --property=RuntimeMaxSec=300 --setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1 /opt/constellation/legacy-venv/bin/python -B -c \"import base64;exec(base64.b64decode('"+enc+"'))\"";s=boto3.client('ssm',region_name='us-east-1');r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=330);ref={'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'};(p/'probe-command.json').write_text(json.dumps(ref))
for _ in range(160):
 try:o=s.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'probe-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardOutputContent'],o['StandardErrorContent'])
