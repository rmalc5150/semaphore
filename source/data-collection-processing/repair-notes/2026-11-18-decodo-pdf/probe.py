"""Two authorised diagnostic API requests; no collector/config activation."""
import hashlib,io,json,time,os
from pathlib import Path
import boto3,requests
from pypdf import PdfReader
from decodo_web_data import reserve
from constellation.shared_limits import admit
P=Path(__file__).parent;P.mkdir(exist_ok=True);session=requests.Session()
secrets=json.loads(boto3.client('secretsmanager').get_secret_value(SecretId='arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV')['SecretString'])
token=secrets['decodo-web'].strip().removeprefix('Bearer ')
API='https://data.decodo.com/v1/scrape';MAX=20*1024**2
CASES=[('control','https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',None),('medrxiv','https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf','10.64898/2026.05.07.26352693')]
def fetch(method,url,**kwargs):
 with session.request(method,url,stream=True,timeout=(10,55),allow_redirects=False,**kwargs) as response:
  chunks=[];size=0
  for chunk in response.iter_content(65536):
   size+=len(chunk)
   if size>MAX:raise ValueError('response_size_limit')
   chunks.append(chunk)
  return response.status_code,response.headers.get('Content-Type',''),b''.join(chunks)
def validate(raw,doi=None):
 result={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 try:
  assert raw.startswith(b'%PDF-') and b'%%EOF' in raw[-4096:],'not_complete_pdf'
  reader=PdfReader(io.BytesIO(raw),strict=True);assert not reader.is_encrypted and 0<len(reader.pages)<=1000
  text=''.join(reader.pages[i].extract_text() or '' for i in range(min(2,len(reader.pages))))
  result.update(strict_pdf=True,pages=len(reader.pages),text_characters=len(text))
  if doi:result['doi_match']=doi.lower() in ''.join(text.split()).lower()
 except Exception as exc:result.update(strict_pdf=False,error_type=type(exc).__name__,detail=str(exc)[:120])
 return result
report={'started_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'max_api_requests':2,'cases':[],'production_changed':False,'proxy_route':'not_tested_no_separate_proxy_credentials'}
for label,url,doi in CASES:
 row={'label':label,'url':url}
 try:
  status,media,raw=fetch('GET',url,headers={'User-Agent':'Optima Holdings support@optima-holdings.com','Accept':'application/pdf'})
  direct={'http_status':status,'content_type':media,'bytes':len(raw)};expected=None
  if status==200 and raw.startswith(b'%PDF-'):
   direct['validation']=validate(raw,doi);expected=hashlib.sha256(raw).hexdigest();(P/(label+'-direct.pdf')).write_bytes(raw)
  row['direct']=direct
  reserve();admit(API);started=time.monotonic()
  status,media,body=fetch('POST',API,headers={'Authorization':'Bearer '+token,'Accept':'application/pdf','Content-Type':'application/json'},json={'url':url})
  result={'http_status':status,'content_type':media,'bytes':len(body),'elapsed_seconds':round(time.monotonic()-started,2),'accept':'application/pdf'}
  if body.startswith(b'%PDF-'):
   result['wire_pdf']=validate(body,doi)
   if result['wire_pdf'].get('strict_pdf') and (not doi or result['wire_pdf'].get('doi_match')):(P/(label+'-gateway.pdf')).write_bytes(body)
  else:
   try:document=json.loads(body)
   except Exception:document=None
   if isinstance(document,dict):
    rows=document.get('results');r=rows[0]if isinstance(rows,list)and len(rows)==1 else document
    content=r.get('content');result.update(json_envelope=True,task_id=r.get('task_id') or document.get('task_id'),target_status=r.get('status_code'),content_kind=r.get('type'),content_is_pdf_string=isinstance(content,str) and content.startswith('%PDF-'))
    if isinstance(content,str) and content.startswith('%PDF-'):
     candidates=[]
     for encoding in ['utf-8','latin1','cp1252']:
      candidate={'encoding':encoding}
      try:
       raw=content.encode(encoding);candidate.update(validate(raw,doi));candidate['matches_direct_original']=expected is not None and candidate['sha256']==expected
      except UnicodeError:candidate.update(strict_pdf=False,error_type='UnicodeEncodeError')
      candidates.append(candidate)
     result['reconstruction_candidates']=candidates
   else:result['json_envelope']=False
  row['decodo']=result
 except Exception as exc:row['error_type']=type(exc).__name__
 report['cases'].append(row);(P/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(row),flush=True)
report['finished_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());(P/'results.json').write_text(json.dumps(report,indent=2))
