"""Validate EPO OAuth and legal-event access without saving authentication material."""
from datetime import datetime,timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import boto3,requests
SECRET='arn:aws:secretsmanager:us-east-1:059416028963:secret:dataSourceAPIkeys-PSTzff'
def main():
 result={'checked_at':datetime.now(timezone.utc).isoformat(),'credential_fields':['EPO-consumer','EPO-consumer-secret'],'values_logged':False,'collection_enabled':False}
 try:
  values=json.loads(boto3.client('secretsmanager',region_name='us-east-1').get_secret_value(SecretId=SECRET)['SecretString'])
  pair=tuple(values.get(k,'').strip() for k in result['credential_fields']);result['fields_present']=all(pair)
  if not all(pair):raise ValueError('missing_fields')
  r=requests.post('https://ops.epo.org/3.2/auth/accesstoken',auth=pair,data={'grant_type':'client_credentials'},timeout=(10,45),allow_redirects=False)
  result['oauth_http_status']=r.status_code
  if r.status_code==200:
   token=r.json().get('access_token');result['oauth_token_issued']=bool(token)
   if token:
    url='https://ops.epo.org/3.2/rest-services/legal/publication/epodoc/EP1000000'
    r=requests.get(url,headers={'Authorization':'Bearer '+token,'Accept':'application/xml'},timeout=(10,45),allow_redirects=False)
    result['legal_probe_http_status']=r.status_code;result['legal_probe_reference']='EP1000000';result['legal_probe_bytes']=len(r.content)
    if r.status_code==200:
     doc=ET.fromstring(r.content);result['legal_probe_xml_root']=doc.tag
     result['legal_event_nodes']=sum(x.tag.rsplit('}',1)[-1]=='legal-event' for x in doc.iter())
    else:
     try:result['provider_error_code']=ET.fromstring(r.content).findtext('.//code')
     except ET.ParseError:pass
  else:
   try:
    d=r.json();result['provider_error_code']=d.get('error') if isinstance(d.get('error'),str) else None
   except ValueError:pass
 except Exception as error:result['error_type']=type(error).__name__
 path=Path(__file__).with_name('access-validation.json');path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
