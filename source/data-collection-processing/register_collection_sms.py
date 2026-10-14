"""Resume the authorized toll-free sender registration without duplicate purchases."""
import json,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import boto3
ROOT=Path(__file__).resolve().parent
P=ROOT/'reports/collection-monitoring-sms-registration-live.json'
c=boto3.client('pinpoint-sms-voice-v2',region_name='us-east-1')
d=json.loads((ROOT/'reports/collection-monitoring-sms-registration-draft.json').read_text())
s=json.loads(P.read_text()) if P.exists() else {}
tags=[{'Key':'Project','Value':'OptimaCollectionMonitoring'},{'Key':'Name','Value':'Optima collection critical alerts'}]
def save():
 s['updated_at']=datetime.now(timezone.utc).isoformat();P.write_text(json.dumps(s,indent=2,default=str)+'\n')
def once(key,fn,**kw):
 if key not in s:
  result=fn(**kw);result.pop('ResponseMetadata',None);s[key]=result;save()
 return s[key]
base='https://optima-collection-sms-public-059416028963-us-east-1.s3.us-east-1.amazonaws.com'
for key in ['sms-terms.html','sms-privacy.html']:
 with urllib.request.urlopen(base+'/'+key) as response:
  body=response.read().decode();assert response.status==200 and 'Optima Holdings INC' in body
s['public_terms_url']=base+'/sms-terms.html';s['public_privacy_url']=base+'/sms-privacy.html';save()
r=once('registration',c.create_registration,RegistrationType='US_TOLL_FREE_REGISTRATION',Tags=tags,ClientToken='optima-collection-tfn-registration-20260926')
rid=r['RegistrationId']
a=once('attachment',c.create_registration_attachment,AttachmentBody=(ROOT/'reports/optima-sms-opt-in-workflow.png').read_bytes(),Tags=tags,ClientToken='optima-collection-tfn-optin-20260926')
texts={
'companyInfo.companyName':d['company_legal_name'],'companyInfo.website':d['company_website'],
'companyInfo.address1':'1309 Coffeen Avenue','companyInfo.address2':'STE 1200','companyInfo.city':'Sheridan','companyInfo.state':'WY','companyInfo.zipCode':'82801','companyInfo.isoCountryCode':'US',
'companyInfo.taxId':d['company_identification_number'],'companyInfo.taxIdCountry':'US',
'contactInfo.firstName':'Randall','contactInfo.lastName':'Malcolm','contactInfo.supportEmail':d['contact_email'],'contactInfo.supportPhoneNumber':d['contact_phone'],
'messagingUseCase.useCaseDetails':d['use_case'],
'messagingUseCase.privacyPolicyUrl':s['public_privacy_url'],'messagingUseCase.termsAndConditionsUrl':s['public_terms_url'],
'messagingUseCase.optInDescription':"Private administrative chat enrollment for authorized internal operators; no public signup or marketing. The operator requests operational SMS and supplies their number. The administrator provides the SMS Terms and Privacy Notice, including variable frequency, message/data rates, STOP/HELP and voluntary consent, and requires affirmative authorization for each enrolled number. The account owner requested alerts in the setup conversation and subsequently reviewed the drafted terms. The attached image illustrates this workflow; it is not a screenshot or a signed consent record. Consent requests are retained privately. Numbers are subscribed to the critical-alert SNS topic; email remains separate. Recipients can reply STOP or email randall@optima-holdings.com for removal.",
'messageSamples.messageSample1':'Optima Holdings INC: Critical data collection failure in patents publication. Check your alert email for details. Reply STOP to opt out or HELP for help.'}
selects={'companyInfo.businessType':'PRIVATE_PROFIT','companyInfo.taxIdAuthority':'EIN','messagingUseCase.monthlyMessageVolume':'100','messagingUseCase.useCaseCategory':'EVENT_NOTIFICATIONS','messagingUseCase.optInType':'TEXT'}
if 'submission' not in s:
 for path,value in texts.items():c.put_registration_field_value(RegistrationId=rid,FieldPath=path,TextValue=value)
 for path,value in selects.items():c.put_registration_field_value(RegistrationId=rid,FieldPath=path,SelectChoices=[value])
 c.put_registration_field_value(RegistrationId=rid,FieldPath='messagingUseCase.optInImage',RegistrationAttachmentId=a['RegistrationAttachmentId'])
 s['fields_populated']=True;s['estimated_monthly_volume']=100;save()

if '--prepare-only' not in sys.argv:
 # International routing remains a separate investigation; request the verified US path.
 p=once('phone',c.request_phone_number,IsoCountryCode='US',MessageType='TRANSACTIONAL',NumberCapabilities=['SMS'],NumberType='TOLL_FREE',Tags=tags,ClientToken='optima-collection-tfn-phone-20260926')
 once('association',c.create_registration_association,RegistrationId=rid,ResourceId=p['PhoneNumberId'])
 policy={'Version':'2012-10-17','Statement':[{'Sid':'AllowAccountSNS','Effect':'Allow','Principal':{'Service':'sns.amazonaws.com'},'Action':'sms-voice:SendTextMessage','Resource':p['PhoneNumberArn'],'Condition':{'StringEquals':{'aws:SourceAccount':'059416028963'}}}]}
 once('sns_resource_policy',c.put_resource_policy,ResourceArn=p['PhoneNumberArn'],Policy=json.dumps(policy))
 if '--submit' in sys.argv:
  once('submission',c.submit_registration_version,RegistrationId=rid)
s['current_registration']=c.describe_registrations(RegistrationIds=[rid])['Registrations'][0]
s['status']=s['current_registration']['RegistrationStatus'].lower()
if 'submission' in s:s.pop('blocker',None)
if 'phone' in s:s['current_phone']=c.describe_phone_numbers(PhoneNumberIds=[s['phone']['PhoneNumberId']])['PhoneNumbers'][0]
save()
print(json.dumps({'registration_id':rid,'status':s['current_registration']['RegistrationStatus'],'phone':s.get('phone',{}).get('PhoneNumber'),'monthly_lease':s.get('phone',{}).get('MonthlyLeasingPrice'),'submitted':'submission' in s},indent=2))
