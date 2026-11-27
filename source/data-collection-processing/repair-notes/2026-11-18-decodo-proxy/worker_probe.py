import os,sys
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
"""Bounded proxy tests. Never log credential-bearing URLs or exception text."""
import io,json,hashlib,re,time
from pathlib import Path
from urllib.parse import quote,urlsplit
import boto3,requests
from pypdf import PdfReader
P=Path('/opt/constellation/tmp/decodo-proxy-test-20261118');P.mkdir(exist_ok=True)
SECRET='arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV'
def credentials():
 v=json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
 username=v.get('decodo-proxy-username');password=v.get('decodo-proxy-password');endpoint=v.get('decodo-proxy-endpoint')
 if not all(isinstance(s,str)and s.strip()for s in [username,password,endpoint]):raise RuntimeError('proxy_fields_missing')
 # Accept the provider's host:port:user:pass export, but never log it.
 endpoint=endpoint.strip();scheme='https'
 if '://'in endpoint:scheme,endpoint=endpoint.split('://',1)
 if '@'in endpoint:
  parsed=urlsplit(scheme+'://'+endpoint);host=parsed.hostname;port=parsed.port
 else:
  match=re.fullmatch(r'([a-zA-Z0-9.-]+):(\d{1,5})(?::(.*))?/?',endpoint)
  if not match:raise RuntimeError('proxy_endpoint_format_invalid')
  host=match[1].lower();port=int(match[2])
 if not (scheme=='https' and host and (host=='decodo.com'or host.endswith('.decodo.com'))and port and 0<port<65536):raise RuntimeError('proxy_endpoint_not_approved_https')
 return scheme,host,port,username.strip(),password

def validate(raw,doi=None):
 out={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 try:
  assert raw.startswith(b'%PDF-')and b'%%EOF'in raw[-4096:]
  pdf=PdfReader(io.BytesIO(raw),strict=True);assert not pdf.is_encrypted and 0<len(pdf.pages)<=1000
  text=''.join(pdf.pages[i].extract_text()or''for i in range(min(2,len(pdf.pages))))
  out.update(strict_pdf=True,pages=len(pdf.pages))
  if doi:out['doi_match']=doi in ''.join(text.split())
 except Exception as e:out.update(strict_pdf=False,error_type=type(e).__name__)
 return out

def main():
 try:scheme,host,port,username,password=credentials()
 except Exception as e:
  P.joinpath('results.json').write_text(json.dumps({'status':'configuration_unreadable','error_type':type(e).__name__}));print('Proxy configuration could not be safely parsed.');return
 proxy=f'{scheme}://{quote(username,safe="")}:{quote(password,safe="")}@{host}:{port}'
 session=requests.Session();session.trust_env=False
 session.proxies={'http':proxy,'https':proxy}
 tests=[('control','https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',None),('medrxiv','https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf','10.64898/2026.05.07.26352693')]
 report={'proxy_host':host,'proxy_port':port,'proxy_scheme':scheme,'tls_verification':True,'production_enabled':False,'cases':[],'max_requests':2}
 for label,url,doi in tests:
  row={'label':label,'url':url};started=time.monotonic()
  try:
   with session.get(url,headers={'Accept':'application/pdf','User-Agent':'Optima Holdings support@optima-holdings.com'},stream=True,timeout=(12,50),allow_redirects=False)as r:
    row.update(http_status=r.status_code,content_type=r.headers.get('Content-Type',''));parts=[];size=0
    for chunk in r.iter_content(65536):
     size+=len(chunk)
     if size>2*1024**2:raise RuntimeError('response_size_limit')
     parts.append(chunk)
    raw=b''.join(parts)
   row['validation']=validate(raw,doi)
   original=Path('repair-notes/2026-11-18-decodo-pdf')/(label+'-direct.pdf')
   row['matches_direct_original']=row['validation']['sha256']=={'control':'3df79d34abbca99308e79cb94461c1893582604d68329a41fd4bec1885e6adb4','medrxiv':'2711c86f4189824a8324c0ecafdc2a807485054560bb7d50cef2eee9b7f821ef'}[label]
   passed=row.get('http_status')==200 and row['validation'].get('strict_pdf') and row['matches_direct_original'] and (not doi or row['validation'].get('doi_match'))
   if passed:P.joinpath(label+'-proxy.pdf').write_bytes(raw)
   row['passed']=bool(passed)
  except Exception as e:
   row.update(passed=False,error_type=type(e).__name__)
   # Exception text may contain proxy credentials. Persist only recognised codes.
   status=re.search(r'\b(407|403|429|502|503|504)\b',str(e))
   if status:row['proxy_error_status']=int(status[1])
  row['elapsed_seconds']=round(time.monotonic()-started,2);report['cases'].append(row)
  P.joinpath('results.json').write_text(json.dumps(report,indent=2));print(json.dumps(row),flush=True)
  if not row['passed']:break
 report['status']='passed'if len(report['cases'])==2 and all(r['passed']for r in report['cases'])else'failed'
 P.joinpath('results.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
