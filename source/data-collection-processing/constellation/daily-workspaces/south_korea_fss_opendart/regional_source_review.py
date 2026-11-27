"""Scoped original releases for catalogue entries 91–105; no inferred measurements."""
import re,json
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,parse_qs,urldefrag

PROFILES={
'japan_mhlw_ndb_open_data':{'entry':91,'hosts':['www.mhlw.go.jp','mhlw.go.jp'],'kind':'file'},
'cninfo_mainland_china_company_disclosures':{'entry':92,'hosts':['www.cninfo.com.cn','cninfo.com.cn','static.cninfo.com.cn'],'kind':'filing'},
'china_nbs_industrial_production':{'entry':93,'hosts':['www.stats.gov.cn','stats.gov.cn','data.stats.gov.cn'],'kind':'release','topic':r'industrial production|工业生产|工业增加值'},
'china_miit_electronics_and_battery_statistics':{'entry':94,'hosts':['www.miit.gov.cn','wap.miit.gov.cn'],'kind':'release','topic':r'电子信息制造业|锂离子电池|锂电池|光伏制造'},
'china_nea_power_statistics':{'entry':95,'hosts':['www.nea.gov.cn','nea.gov.cn'],'kind':'release','topic':r'全国电力统计|全国电力工业|电力统计数据|全社会用电量'},
'china_nhsa_reimbursement_and_procurement':{'entry':96,'hosts':['www.nhsa.gov.cn','nhsa.gov.cn'],'kind':'release','topic':r'药品目录|药品.*采购|药品.*集采|医药.*集采|医疗保障事业发展统计'},
'china_mofcom_export_controls':{'entry':97,'hosts':['www.mofcom.gov.cn','exportcontrol.mofcom.gov.cn','picpolicy.mofcom.gov.cn','interview.mofcom.gov.cn'],'kind':'release','topic':r'出口管制|两用物项|管控名单'},
'south_korea_fss_opendart':{'entry':98,'hosts':['opendart.fss.or.kr','dart.fss.or.kr'],'kind':'filing'},
'taiwan_twse_mops_issuer_and_revenue_archives':{'entry':100,'hosts':['openapi.twse.com.tw','mops.twse.com.tw'],'kind':'twse'},
'taiwan_customs_trade_statistics':{'entry':101,'hosts':['opendata.customs.gov.tw','data.gov.tw'],'kind':'file'},
'india_ibm_mineral_production':{'entry':102,'hosts':['ibm.gov.in','www.ibm.gov.in'],'kind':'file'},
'indonesia_esdm_and_geological_agency_mineral_statistics':{'entry':103,'hosts':['www.esdm.go.id','geologi.esdm.go.id','jdih.esdm.go.id'],'kind':'file'},
'brazil_anm_mineral_yearbook':{'entry':104,'hosts':['www.gov.br','dadosabertos.anm.gov.br'],'kind':'file'},
'brazil_anm_cfem_mining_royalties':{'entry':105,'hosts':['www.gov.br','dadosabertos.anm.gov.br'],'kind':'file'},
}
PUBLIC_KEYS=set(PROFILES)-{'south_korea_fss_opendart'}

class Page(HTMLParser):
 """Read article regions and labelled anchors without evaluating page scripts."""
 VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
 IGNORE={'script','style','noscript','nav','footer','form'}
 REGION_IDS={'zoom','zoomcon','ucap-content','article-content','content','contenttext'}
 REGION_CLASSES={'trs_editor','article-content','easysite-article-content'}
 def __init__(self,body):
  super().__init__(convert_charrefs=True);self.stack=[];self.text=[];self.title=[];self.headings=[];self.meta={};self.anchors=[];self.regions=[];self.images=[];self.heading_nodes=[];self.feed(decode_html(body));self.close()
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=='meta':self.meta[(attrs.get('name')or attrs.get('property')or'').lower()]=attrs.get('content','')
  if tag=='img':self.images.append((attrs.get('src',''),attrs.get('alt','')))
  if tag in self.VOID:return
  node={'tag':tag,'attrs':attrs,'parts':[],'depth':len(self.stack)}
  self.stack.append(node)
  if tag in ('h1','h2','h3')or re.search(r'(?:art.?title|art.?tit|main.?title|article_title|biaoti)',attrs.get('class','')+' '+attrs.get('id',''),re.I):self.heading_nodes.append(node)
  if tag=='a'and attrs.get('href'):self.anchors.append(node)
  if tag=='article'or attrs.get('id','').lower()in self.REGION_IDS or set(attrs.get('class','').lower().split())&self.REGION_CLASSES:self.regions.append(node)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]['tag']==tag:del self.stack[i:];break
 def handle_data(self,text):
  if any(n['tag']in self.IGNORE for n in self.stack):return
  if not text.strip():return
  self.text.append(text.strip())
  for node in self.stack:
   if node in self.regions or node in self.heading_nodes or node['tag']=='a':node['parts'].append(text.strip())
  if any(n['tag']=='title'for n in self.stack):self.title.append(text.strip())
  if any(n['tag']=='h1'for n in self.stack):self.headings.append(text.strip())
 @property
 def headline(self):return ' '.join(self.headings)or self.meta.get('articletitle')or self.meta.get('og:title')or' '.join(self.title)
 @property
 def content(self):
  regions=[' '.join(n['parts'])for n in self.regions if len(' '.join(n['parts']))>=100]
  return max(regions,key=len)if regions else' '.join(self.text)
 def links(self,url):return [(urljoin(url,n['attrs']['href']), ' '.join(n['parts']))for n in self.anchors]

def decode_html(body):
 for encoding in ('utf-8-sig','gb18030'):
  try:return body.decode(encoding)
  except UnicodeDecodeError:pass
 raise ValueError('unsupported_release_encoding')

def in_scope(url,source,discovery=False):
 profile=PROFILES[source];u=urlsplit(url);p=u.path.lower();q=parse_qs(u.query)
 if u.scheme!='https'or u.hostname not in profile['hosts']or u.username or u.password or u.port not in (None,443):return False
 n=profile['entry']
 if n==91:return bool(re.fullmatch(r'/content/\d+/[^/]+\.(?:xlsx?|csv|zip)',p)or discovery and p.startswith('/stf/seisakunitsuite/bunya/'))
 if n==92:return bool(u.hostname=='static.cninfo.com.cn'and re.fullmatch(r'/finalpage/\d{4}-\d{2}-\d{2}/\d+\.pdf',p)or discovery and p=='/new/hisannouncement/query')
 if n==93:return bool(re.fullmatch(r'/english/pressrelease/\d{6}/t\d+_\d+\.html',p)or discovery and p.startswith('/english/pressrelease/'))
 if n==94:return bool(re.fullmatch(r'/gxsj/tjfx/(?:dzxx|[a-z]+)/art/\d{4}/art_[a-f0-9]+\.html',p)or discovery and p.startswith('/gxsj/tjfx/'))
 if n==95:return bool(re.fullmatch(r'/\d{8}/[a-f0-9]+/c\.html',p)or re.fullmatch(r'/\d{4}-\d{2}/\d{2}/c_\d+\.htm',p)or discovery and p in ('/nyyw/','/nyyw.htm','/'))
 if n==96:return bool(re.fullmatch(r'/art/\d{4}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html',p)or p=='/module/download/downfile.jsp'and any(v.lower().endswith('.pdf')for v in q.get('filename',[]))or discovery and p.startswith('/col/'))
 if n==97:return bool(u.hostname=='exportcontrol.mofcom.gov.cn'and re.fullmatch(r'/article/zcfg/gnzcfg/[^/]+/\d{6}/\d+\.html',p)or re.fullmatch(r'/zcfb/(?:zc|blgg)/art/\d{4}/art_[a-f0-9]+\.html',p)or u.hostname=='picpolicy.mofcom.gov.cn'and p.endswith('.pdf')or discovery and(p.startswith('/article/zcfg/gnzcfg/')or p.startswith('/zcfb/')))
 if n==100:return bool(u.hostname=='openapi.twse.com.tw'and p in ('/v1/opendata/t187ap03_l','/v1/opendata/t187ap05_l'))
 if n==101:return bool(u.hostname=='opendata.customs.gov.tw'and re.fullmatch(r'/data/6053/[^/]+\.csv',p)or discovery and u.hostname=='data.gov.tw'and re.fullmatch(r'/(?:en/datasets|dataset)/6053',p))
 if n==102:return bool(p.startswith('/writereaddata/files/')and p.endswith(('.pdf','.xlsx','.xls'))and 'msmp'in p or discovery and p.startswith('/ibmportal/pages/')and any(k in p for k in ('monthly-statistics-of-mineral-production','monthly_statistics_of_mineral_production','mineral_production')))
 if n==103:return bool(u.hostname=='geologi.esdm.go.id'and p.startswith('/storage/publikasi/')and p.endswith('.pdf')or u.hostname=='jdih.esdm.go.id'and p=='/dokumen/download'and any('kmesdm'in v and v.lower().endswith('.pdf')for v in q.get('id',[]))or discovery and u.hostname=='geologi.esdm.go.id'and(p.startswith('/publikasi/laporan-dan-buku')or p.startswith('/index.php/publikasi/laporan-dan-buku')))
 if n==104:return bool(u.hostname=='dadosabertos.anm.gov.br'and p.startswith('/amb/')and p.endswith(('.csv','.zip'))or u.hostname=='www.gov.br'and '/anm/'in p and 'anuario-mineral'in p and(p.endswith('.pdf')or p.endswith('/@@download/file')or '/anuario-mineral-brasileiro/'in p and bool(re.search(r'20\d{2}',p.rsplit('/',1)[-1])))or discovery and u.hostname=='www.gov.br'and '/anuario-mineral'in p)
 if n==105:return bool(u.hostname=='dadosabertos.anm.gov.br'and p.startswith('/cfem/')and p.endswith(('.csv','.zip'))or u.hostname=='www.gov.br'and '/anm/'in p and ('arrecadacao'in p or 'cfem'in p)and p.endswith(('.pdf','.xls','.xlsx'))or discovery and u.hostname=='www.gov.br'and '/anm/'in p and ('arrecadacao'in p or 'cfem'in p))
 return False

def release_info(source,url,body):
 if source not in PUBLIC_KEYS or PROFILES[source]['kind']!='release'or not in_scope(url,source):return None
 if len(body)>4*1024*1024:raise ValueError('release_html_too_large')
 page=Page(body);text=page.content;topic=PROFILES[source]['topic'];title=page.meta.get('articletitle')or page.headline
 if title in ('中国出口管制信息网','中华人民共和国商务部'):return None
 if not title or not re.search(topic,title,re.I)or len(text)<100 or len(re.findall(r'\d+(?:[.,]\d+)?',text))<4:return None
 if any(k in text[:1000].lower()for k in ('access denied','verify you are human','captcha challenge')):return None
 return {'format':'html','kind':'official_release','title':title,'text_characters':len(text),'table_elements':decode_html(body).lower().count('<table'),'scope':'Complete original official HTML release; linked attachments/figures and numerical extraction are separate.'}

def discover(body,url,source,depth):
 key=source['source'];profile=PROFILES[key];page=Page(body);found=[]
 if profile['entry']==92:
  data=json.loads(body)
  for row in data.get('announcements')or[]:
   target=urljoin('https://static.cninfo.com.cn/',row.get('adjunctUrl',''))
   if in_scope(target,key):found.append({'url':target,'depth':depth+1})
  return found
 for target,label in page.links(url):
  target=urldefrag(target)[0]
  if target==urldefrag(url)[0]:continue
  if target.startswith('http://')and urlsplit(target).hostname in profile['hosts']:target='https://'+target[7:]
  if not in_scope(target,key,True):continue
  n=profile['entry']
  if n==103 and target.lower().endswith('.pdf')and not re.search(r'neraca|cadangan|mineral|resources',url+label,re.I):continue
  if n==103 and not target.lower().endswith('.pdf')and '/laporan-dan-buku/'in target and not re.search(r'neraca|cadangan|mineral|resources',target+label,re.I):continue
  if n==91 and '/stf/'in target and not re.search(r'第.{1,4}回.*NDB|NDB.*オープンデータ',label):continue
  if profile['kind']=='release'and not re.search(r'\.pdf(?:\?|$)|downfile.jsp',target,re.I):
   if in_scope(target,key)and not re.search(profile['topic'],label,re.I):continue
  found.append({'url':target,'depth':depth+1})
 # Prefer source files; preserve original response order within each group.
 found=list({r['url']:r for r in found}.values())
 return sorted(found,key=lambda r:not bool(re.search(r'\.pdf(?:\?|$)|\.(?:csv|xlsx?|zip)$|downfile.jsp',r['url'],re.I)))

def figure_urls(url,body):
 path=urlsplit(url).path.rsplit('/',1)[0]+'/'
 return list(dict.fromkeys(urljoin(url,src)for src,alt in Page(body).images if src and urlsplit(urljoin(url,src)).hostname==urlsplit(url).hostname and urlsplit(urljoin(url,src)).path.startswith(path)and re.search(r'\.(?:png|jpe?g)$',urlsplit(urljoin(url,src)).path,re.I)))

def capture_figures(s3,row,body,prefix,bucket):
 import hashlib,requests
 from constellation.shared_limits import admit
 from datetime import datetime,timezone
 urls=figure_urls(row['source_url'],body)
 if len(urls)>12:raise ValueError('release_figure_count_limit')
 refs=[]
 for url in urls:
  if urlsplit(url).hostname not in PROFILES[row['source']]['hosts']:raise ValueError('release_figure_origin_unapproved')
  admit(url)
  with requests.get(url,timeout=(10,30),stream=True,allow_redirects=False)as response:
   if response.status_code!=200:raise ValueError('release_figure_http_'+str(response.status_code))
   chunks=[];size=0
   for block in response.iter_content(65536):
    size+=len(block)
    if size>8*1024**2:raise ValueError('release_figure_size_limit')
    chunks.append(block)
   raw=b''.join(chunks);sha=hashlib.sha256(raw).hexdigest();key=prefix+'/objects/'+row['source']+'/'+sha;s3.put_object(Bucket=bucket,Key=key,Body=raw,ContentType=response.headers.get('Content-Type','application/octet-stream'),ServerSideEncryption='AES256');saved=s3.get_object(Bucket=bucket,Key=key)['Body'].read()
   if hashlib.sha256(saved).hexdigest()!=sha:raise ValueError('release_figure_readback_mismatch')
  refs.append({'s3_uri':'s3://'+bucket+'/'+key,'sha256':sha,'source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat()})
 return refs
