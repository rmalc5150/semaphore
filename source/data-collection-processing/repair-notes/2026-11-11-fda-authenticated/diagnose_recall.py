from specialist_authenticated import credentials
import requests,json,time
from pathlib import Path
p=Path(__file__).parent;user,key=credentials('fda-enforcement');url='https://www.accessdata.fda.gov/rest/iresapi/recalls/';body={'displaycolumns':'','filter':json.dumps([{'eventlmdfrom':'10/28/2026'},{'eventlmdto':'10/28/2026'}]),'start':1,'rows':1,'sort':'productid','sortorder':'asc'}
try:
 r=requests.post(url,params={'signature':str(time.time_ns())},headers={'Authorization-User':user,'Authorization-Key':key},data={'payload':json.dumps(body)},timeout=25,allow_redirects=False);out={'http_status':r.status_code,'content_type':r.headers.get('Content-Type'),'bytes':len(r.content)}
 if r.is_redirect:
  from urllib.parse import urlsplit
  target=urlsplit(r.headers.get('Location',''));out['redirect_host']=target.hostname;out['redirect_path']=target.path
 if r.status_code==200:
  data=r.json();out['api_code']=data.get('STATUSCODE');out['message']=data.get('MESSAGE');out['result_type']=type(data.get('RESULT')).__name__
  if data.get('STATUSCODE')==400:
   from specialist_authenticated import table_rows
   rows=table_rows(data);out['fields']=list(rows[0])if rows else[]
 print(out)
except Exception as e:out={'exception_type':type(e).__name__};print(out)
(p/'recall-diagnostic.json').write_text(json.dumps(out,indent=2))
