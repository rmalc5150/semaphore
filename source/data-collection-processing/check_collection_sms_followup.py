"""One-time SMS registration follow-up; --preview reads without sending email."""
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
import boto3
ROOT=Path(__file__).resolve().parent

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');args=parser.parse_args()
 cfg=json.loads((ROOT/'config/collection-monitoring.json').read_text());saved=json.loads((ROOT/'reports/collection-monitoring-sms-registration-live.json').read_text())
 now=datetime.now(timezone.utc);region=cfg['region'];sms=boto3.client('pinpoint-sms-voice-v2',region_name=region);sns=boto3.client('sns',region_name=region);cw=boto3.client('cloudwatch',region_name=region)
 report={'checked_at':now.isoformat(),'errors':[]}
 def read(label,fn):
  try:report[label]=fn()
  except Exception as exc:report['errors'].append(label+': '+str(exc))
 rid=saved['registration']['RegistrationId'];pid=saved['phone']['PhoneNumberId']
 read('registration',lambda:sms.describe_registrations(RegistrationIds=[rid])['Registrations'][0])
 read('versions',lambda:sms.describe_registration_versions(RegistrationId=rid)['RegistrationVersions'])
 read('phone',lambda:sms.describe_phone_numbers(PhoneNumberIds=[pid])['PhoneNumbers'][0])
 read('sms_recipients',lambda:[s['Endpoint'] for p in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=cfg['sms_topic_arn']) for s in p['Subscriptions'] if s['Protocol']=='sms'])
 read('us_delivery_last_7_days',lambda:cw.get_metric_statistics(Namespace='AWS/SNS',MetricName='SMSSuccessRate',Dimensions=[{'Name':'Country','Value':'US'},{'Name':'SMSType','Value':'Transactional'}],StartTime=now-timedelta(days=7),EndTime=now,Period=86400,Statistics=['Average','SampleCount'])['Datapoints'])
 status=report.get('registration',{}).get('RegistrationStatus','UNKNOWN');phone_status=report.get('phone',{}).get('Status','UNKNOWN')
 lines=['Optima SMS follow-up — 15 business days',f'Checked: {now.isoformat()}',f'Registration: {status}',f'US sending number: {saved["phone"]["PhoneNumber"]} ({phone_status})',f'Recipients: {", ".join(report.get("sms_recipients",[]))}', '']
 if status=='COMPLETE' and phone_status=='ACTIVE':lines.append('Sender approval is complete. A recipient-confirmed delivery test is still required before calling SMS operational.')
 else:lines.append('SMS is not confirmed operational. Review registration status and any carrier feedback below.')
 if '+34617895324' in report.get('sms_recipients',[]):lines.append('Action still required: remove the Spanish SNS subscription; the requested US-only removal has not completed.')
 if not report.get('us_delivery_last_7_days'):lines.append('No US delivery metric samples in the last 7 days. Absence of samples does not prove successful delivery.')
 lines.extend(['','AWS status and delivery details:',json.dumps(report,indent=2,default=str)])
 body='\n'.join(lines)
 if args.preview:print(body);return
 s3=boto3.client('s3',region_name=region);key=cfg['prefix'].rstrip('/')+'/checks/'+now.strftime('%Y-%m-%d')+'/sms-registration-followup-'+now.strftime('%H%M%S')+'.json'
 s3.put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(report,default=str).encode(),ContentType='application/json')
 result=sns.publish(TopicArn=cfg['email_topic_arn'],Subject='Optima SMS registration follow-up: '+status,Message=body)
 print(json.dumps({'email_message_id':result['MessageId'],'report_key':key,'registration_status':status}))

if __name__=='__main__':main()
