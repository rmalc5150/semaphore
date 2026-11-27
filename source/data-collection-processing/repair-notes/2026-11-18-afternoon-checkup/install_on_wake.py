"""Apply a narrow tested patch when M7 next runs; never start or stop EC2."""
import json,time,subprocess
from pathlib import Path
import boto3
P=Path(__file__).resolve().parent
STATE=P/'publication-deployment-state.json'
TIMER='optima-publication-repair-install-20261118.timer'
def save(doc):
 temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(doc,indent=2));temp.replace(STATE)
def finished(doc,status):
 doc.update(status=status,finished_at_epoch=time.time());save(doc)
 subprocess.run(['systemctl','stop',TIMER],check=True)
def main():
 doc=json.loads(STATE.read_text())if STATE.exists()else{'created_at_epoch':time.time(),'status':'waiting_for_scheduled_boot'}
 if doc['status']in ('installed','failed','expired'):
  subprocess.run(['systemctl','stop',TIMER],check=True);return
 if time.time()-doc['created_at_epoch']>25*3600:
  finished(doc,'expired');return
 instance='i-06241bd1c4e91c2fc';ssm=boto3.client('ssm',region_name='us-east-1')
 if not doc.get('command_id'):
  state=boto3.client('ec2',region_name='us-east-1').describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]['State']['Name']
  doc.update(last_checked_at_epoch=time.time(),instance_state=state);save(doc)
  if state!='running':return
  online=ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[instance]}])['InstanceInformationList']
  if not online or online[0]['PingStatus']!='Online':return
  r=ssm.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':[(P/'publication-command.txt').read_text()],'executionTimeout':['120']},TimeoutSeconds=180)
  doc.update(command_id=r['Command']['CommandId'],status='installing');save(doc);return
 try:r=ssm.get_command_invocation(CommandId=doc['command_id'],InstanceId=instance)
 except ssm.exceptions.InvocationDoesNotExist:return
 doc['command_status']=r['Status'];save(doc)
 if r['Status']in ('Success','Failed','TimedOut','Cancelled'):
  (P/'publication-deployment-result.json').write_text(json.dumps(r,indent=2,default=str))
  finished(doc,'installed'if r['Status']=='Success'else'failed')
if __name__=='__main__':main()
