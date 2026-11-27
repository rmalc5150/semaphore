from ops import *
urls={
'mhlw':'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00016.html',
'cninfo':'https://www.cninfo.com.cn/new/hisAnnouncement/query?pageNum=1&pageSize=5&column=sse&tabName=fulltext&seDate=2026-11-17~2026-11-17',
'nbs':'https://www.stats.gov.cn/english/PressRelease/202611/t20261117_1965883.html',
'miit':'https://www.miit.gov.cn/gxsj/tjfx/dzxx/art/2026/art_bcb9e6c06d814f9183b9f5a795d0610e.html',
'nea':'https://www.nea.gov.cn/20260825/1430d07985474c5b8110552785f1c74b/c.html',
'nhsa':'https://www.nhsa.gov.cn/art/2026/11/14/art_53_23387.html',
'mofcom':'https://exportcontrol.mofcom.gov.cn/article/zcfg/gnzcfg/zcfggzqd/202610/1322.html',
'kosis':'https://kosis.kr/openapi/index/index.jsp',
'twse':'https://openapi.twse.com.tw/v1/opendata/t187ap05_L',
'customs':'https://data.gov.tw/en/datasets/6053',
'india':'https://ibm.gov.in/IBMPortal/pages/monthly-statistics-of-mineral-production---2026',
'anm_amb':'https://dadosabertos.anm.gov.br/AMB/',
'anm_cfem':'https://dadosabertos.anm.gov.br/CFEM/'}
r=remote(T3,r'''import json,requests,re,sys
sys.path.insert(0,'/opt/constellation/auxiliary-publication/source')
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from html.parser import HTMLParser
import boto3
from public_source_capture import admit
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   href=dict(attrs).get('href')
   if href:self.links.append(href)
s=boto3.client('s3',region_name='us-east-1')
def get(item):
 name,url=item
 try:
  admit(url)
  with requests.request('POST'if name=='cninfo'else'GET',url.split('?')[0]if name=='cninfo'else url,data={'pageNum':1,'pageSize':5,'column':'sse','tabName':'fulltext','seDate':'2026-11-17~2026-11-17'}if name=='cninfo'else None,headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)','Referer':'https://www.cninfo.com.cn/','X-Requested-With':'XMLHttpRequest'},timeout=(8,25),stream=True)as response:
   body=response.raw.read(2*1024*1024,decode_content=True);parser=Links();text=body.decode(response.encoding or'utf-8',errors='replace');parser.feed(text);key=BASE+'probe-bodies/'+name+'.bin';s.put_object(Bucket=BUCKET,Key=key,Body=body,ServerSideEncryption='AES256')
   return name,{'url':url,'final_url':response.url,'status':response.status_code,'bytes_sampled':len(body),'media_type':response.headers.get('Content-Type'),'body_key':key,'title':re.findall(r'<title[^>]*>(.*?)</title>',text,re.I|re.S)[:1],'links':[urljoin(response.url,u)for u in parser.links if re.search(r'xlsx?|\.csv|\.pdf|download|\.zip|ndb|nb_20|Produ|Arrec|stat|statistics',u,re.I)][:120],'head':text[:300]if'json'in response.headers.get('Content-Type','')else None}
 except Exception as e:return name,{'url':url,'error':type(e).__name__}
with ThreadPoolExecutor(max_workers=5)as pool:out=dict(pool.map(get,URLS.items()))
key=BASE+'provider-probes.json';s.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(out,ensure_ascii=False).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key}))
'''.replace('BASE',repr(BASE)).replace('BUCKET',repr(B)).replace('URLS',repr(urls)))
raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'provider-probes.json').write_bytes(raw)
for name,v in json.loads(raw).items():print(name,v.get('status'),v.get('error'),v.get('title'),v.get('links'))
