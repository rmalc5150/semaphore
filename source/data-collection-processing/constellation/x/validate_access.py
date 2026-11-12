"""Bounded, read-only X authentication and Ads Repository entitlement probes."""
import json,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import quote
import requests
from additional_source_apis import credentials

def main():
 values=credentials();access=values.get('X-access','').strip();secret=values.get('X-secret','').strip();app_key=values.get('X-api-key','').strip();app_secret=values.get('X-api-secret','').strip();bearer=(values.get('X-bearer-token') or values.get('X-bearer') or '').strip()
 result={'checked_at':datetime.now(timezone.utc).isoformat(),'fields':{k:bool(values.get(k)) for k in ('X-access','X-secret','X-api-key','X-api-secret','X-bearer-token','X-bearer')},'values_logged':False,'collection_enabled':False,'probes':[]};sensitive=[access,secret,app_key,app_secret,bearer];token=None
 def status(name,r):
  item={'probe':name,'http_status':r.status_code}
  try:
   d=r.json()
   for field in ('title','detail','type','error','errors'):
    if field in d:item[field]=d[field]
   if isinstance(d.get('data'),dict):item['data_returned']=bool(d['data'])
  except ValueError:item['json_response']=False
  result['probes'].append(item);return d if 'd' in locals() else {}
 try:
  result['access_looks_like_oauth1_user_token']=bool(re.match(r'^\d+-',access))
  result['access_looks_like_bearer']=access.startswith('AAAA')
  if bearer:token=bearer
  elif result['access_looks_like_bearer']:token=access
  elif result['access_looks_like_oauth1_user_token'] and not (app_key and app_secret):
   result['blocked_reason']='OAuth 1.0a access token and token secret need the app API key and API key secret to sign a read request.'
  elif (app_key and app_secret) or (access and secret):
   r=requests.post('https://api.x.com/oauth2/token',auth=(quote(app_key or access,safe=''),quote(app_secret or secret,safe='')),data={'grant_type':'client_credentials'},timeout=(10,30),allow_redirects=False)
   d=status('app_only_token_exchange',r);token=d.get('access_token');result['token_issued']=bool(token)
   if token:sensitive.append(token)
  else:result['blocked_reason']='Missing X credential fields'
  if token:
   headers={'Authorization':'Bearer '+token}
   r=requests.get('https://api.x.com/2/users/by/username/XDevelopers',headers=headers,timeout=(10,30),allow_redirects=False);status('public_user_lookup',r)
   # Official Ads Repository endpoint: request a small read-only export job.
   today=datetime.now(timezone.utc).date();body={'variables':{'user':'2244994945','geoLocation':'FR','deliveryRange':{'start_date':(today-timedelta(days=7)).isoformat(),'end_date':(today-timedelta(days=1)).isoformat()}}}
   r=requests.post('https://api.twitter.com/graphql/e9OJa7fJKHtHftkNzcRkzw/CreateExportReportMutation',headers=headers,json=body,timeout=(10,30),allow_redirects=False);d=status('ads_repository_export_query',r)
   result['ads_repository_response_has_data']=bool(d.get('data'))
 except Exception as e:result['error_type']=type(e).__name__
 encoded=json.dumps(result,indent=2)
 for value in sensitive:
  if value:
   for variant in (value,quote(value,safe=''),json.dumps(value)[1:-1]):encoded=encoded.replace(variant,'[REDACTED]')
 Path(__file__).with_name('access-validation.json').write_text(encoded+'\n');print(encoded)
if __name__=='__main__':main()
