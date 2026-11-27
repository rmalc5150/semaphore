"""Cost-bounded last-resort native PDF downloads; credentials never enter logs."""
import hashlib,io,ipaddress,json,re,socket
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,quote,urljoin
import requests
from collection_storage import write_json,now,Conflict
from regulatory_collection import SourceIssue,require

PREFIX='constellation-backfill/source-metadata/operations/pdf-proxy'
CONTROL=None
ELIGIBLE={'source_http_403','source_http_408','source_http_500','source_http_502','source_http_503','source_http_504','source_retries_exhausted','source_pdf_html_response','document_http_403','document_network_error'}

def settings():
 p=Path(__file__).resolve().parent/'config/pdf-proxy-fallback.json'
 if not p.exists():return {'enabled':False}
 c=json.loads(p.read_text())
 require(type(c.get('max_requests_per_day'))is int and 1<=c['max_requests_per_day']<=24,'pdf_proxy_invalid_budget')
 require(type(c.get('max_pdf_bytes'))is int and 0<c['max_pdf_bytes']<=16*1024**2,'pdf_proxy_invalid_byte_limit')
 require(c.get('max_requests_per_client')==1,'pdf_proxy_invalid_client_budget')
 return c

def safe_url(url):
 try:
  p=urlsplit(url)
  if not (p.scheme=='https'and p.hostname and not p.username and not p.password and p.port in (None,443)and not p.fragment):return False
  if p.hostname.endswith(('.localhost','.local','.internal'))or p.hostname=='localhost':return False
  if any(re.search(r'key|token|auth|signature|credential|password',k,re.I) for k,v in parse_qsl(p.query)):return False
  addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
  return bool(addresses)and all(ipaddress.ip_address(row[4][0]).is_global for row in addresses)
 except Exception:return False

def eligible(url,reason):
 return reason in ELIGIBLE and urlsplit(url).path.lower().endswith('.pdf') and safe_url(url)

def validate(raw,url):
 require(raw.startswith(b'%PDF-')and b'%%EOF'in raw[-4096:],'pdf_proxy_invalid_pdf')
 try:
  from pypdf import PdfReader
  reader=PdfReader(io.BytesIO(raw),strict=True)
  require(not reader.is_encrypted and 0<len(reader.pages)<=1000,'pdf_proxy_invalid_pdf')
  doi=re.search(r'/content/(10\.[0-9]+/.+?)v[0-9]+\.full\.pdf$',urlsplit(url).path)
  if doi:
   text=''.join(reader.pages[i].extract_text()or''for i in range(min(2,len(reader.pages))))
   require(doi[1].lower()in re.sub(r'\s+','',text).lower(),'pdf_proxy_doi_mismatch')
  return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'pages':len(reader.pages),'strict_pdf':True}
 except SourceIssue:raise
 except Exception:raise SourceIssue('pdf_proxy_invalid_pdf')from None

def proxy_url(config):
 import boto3
 try:
  d=json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=config['secret_id'])['SecretString'])
  p=urlsplit(d['decodo-proxy-endpoint']);host=p.hostname;port=p.port
  require(p.scheme=='https'and host and host.endswith('.decodo.com')and not p.username and not p.password and not p.query and not p.fragment and p.path in ('','/') and port,'pdf_proxy_invalid_endpoint')
  u=d['decodo-proxy-username'];password=d['decodo-proxy-password'];require(isinstance(u,str)and u and isinstance(password,str)and password,'pdf_proxy_missing_credentials')
  return f'https://{quote(u,safe="")}:{quote(password,safe="")}@{host}:{port}'
 except SourceIssue:raise
 except Exception:raise SourceIssue('pdf_proxy_credentials_unavailable',True)from None

def reserve(url,config):
 global CONTROL
 if CONTROL is None:
  from constellation.control import Control
  CONTROL=Control()
 day=datetime.now(timezone.utc).date();identity=hashlib.sha256(url.encode()).hexdigest()
 names=['decodo_proxy_pdf_requests','decodo_proxy_pdf_reserved_bytes','decodo_proxy_pdf_url_'+identity]
 limits=[config['max_requests_per_day'],config['max_requests_per_day']*config['max_pdf_bytes'],1]
 amounts=[1,config['max_pdf_bytes'],1]
 with CONTROL.db()as q:
  counts=[]
  for name in names:
   q.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)',(name,day))
   q.execute('SELECT used_requests FROM backfill_quotas WHERE source_key=%s AND quota_day=%s FOR UPDATE',(name,day));counts.append(int(q.fetchone()['used_requests']))
  if not (counts[0]<limits[0]and counts[1]+amounts[1]<=limits[1]):raise SourceIssue('pdf_proxy_daily_budget',True)
  if counts[2]!=0:raise SourceIssue('pdf_proxy_url_cooldown',True)
  for name,amount in zip(names,amounts):q.execute('UPDATE backfill_quotas SET used_requests=used_requests+%s WHERE source_key=%s AND quota_day=%s',(amount,name,day))

def fetch(url,limit,proxy=None):
 # Sessions are short-lived; redirects cannot silently spend a second paid request.
 session=requests.Session();session.trust_env=False
 if proxy:session.proxies={'http':proxy,'https':proxy}
 try:
  current=url
  for hop in range(4):
   with session.get(current,headers={'Accept':'application/pdf','Accept-Encoding':'identity','User-Agent':'Optima Holdings support@optima-holdings.com'},stream=True,timeout=(8,35),allow_redirects=False)as r:
    if r.status_code in {301,302,303,307,308}:
     require(not proxy and hop<3,'pdf_proxy_redirect_not_retried')
     following=urljoin(current,r.headers.get('Location',''))
     require(safe_url(following),'pdf_proxy_unsafe_redirect');current=following;continue
    if r.status_code!=200:
     raise SourceIssue('pdf_proxy_http_'+str(r.status_code),diagnostics={'resolved_url':current})
    if r.headers.get('Content-Length'):require(int(r.headers['Content-Length'])<=limit,'pdf_proxy_size_limit')
    parts=[];size=0
    for chunk in r.iter_content(65536):
     size+=len(chunk);require(size<=limit,'pdf_proxy_size_limit');parts.append(chunk)
   return b''.join(parts)
  raise SourceIssue('pdf_proxy_redirect_not_retried')
 except SourceIssue:raise
 except Exception:raise SourceIssue('pdf_proxy_transport_failed',True)from None
 finally:session.close()

def capture(client,url,reason):
 config=settings()
 require(config.get('enabled')and eligible(url,reason),reason)
 require(client.source in config.get('allowed_sources',[]),reason)
 identity=hashlib.sha256(url.encode()).hexdigest();key=PREFIX+'/cache/'+identity+'.json'
 obj=client.store.get(key)
 if obj:
  cache=json.loads(obj.body);proof=cache['evidence'];saved=client.store.get(proof['key'])
  require(cache['url']==url and saved is not None,'pdf_proxy_cache_invalid')
  checked=validate(saved.body,url);require(checked['sha256']==proof['sha256'],'pdf_proxy_cache_invalid')
  age=(datetime.now(timezone.utc)-datetime.fromisoformat(cache['checked_at'].replace('Z','+00:00'))).total_seconds()
  if 0<=age<24*3600:
   client.evidence.append(proof);return saved.body
 transport='direct_requests';charged=False
 try:
  try:
   raw=fetch(url,config['max_pdf_bytes']);validation=validate(raw,url)
  except SourceIssue as exc:
   # Missing files, authentication failures, rate limits and oversized files
   # cannot be cured by spending residential bandwidth.
   if exc.code in {'pdf_proxy_http_401','pdf_proxy_http_404','pdf_proxy_http_410','pdf_proxy_http_429','pdf_proxy_size_limit','pdf_proxy_unsafe_redirect','pdf_proxy_redirect_not_retried'}:raise
   target=(exc.diagnostics or {}).get('resolved_url',url)
   require(safe_url(target),'pdf_proxy_unsafe_redirect')
   if getattr(client,'_pdf_proxy_requests',0)>=config['max_requests_per_client']:raise SourceIssue('pdf_proxy_client_budget',True)
   connection=proxy_url(config);reserve(url,config);charged=True
   client._pdf_proxy_requests=getattr(client,'_pdf_proxy_requests',0)+1
   transport='decodo_residential_proxy';raw=fetch(target,config['max_pdf_bytes'],connection);validation=validate(raw,url)
  client.save(raw,url,'application/pdf');proof=dict(client.evidence[-1])
  value={'url':url,'evidence':proof,'validation':validation,'transport':transport,'checked_at':now()}
  try:write_json(client.store,key,value,obj.token if obj else None)
  except Conflict:pass
  audit={**value,'paid_request_reserved':charged,'status':'verified'}
 except SourceIssue as exc:
  audit={'url':url,'reason':exc.code,'transport':transport,'paid_request_reserved':charged,'status':'failed','checked_at':now()}
  raise
 finally:
  if 'audit'in locals():
   from uuid import uuid4
   try:write_json(client.store,PREFIX+'/attempts/'+uuid4().hex+'.json',audit)
   except Exception:pass # Do not discard validated source data if audit write retries.
 return raw
