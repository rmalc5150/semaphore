import urllib.request,re,json,concurrent.futures
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parent
class P(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None;self.links=[];self.href=None;self.text=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='tr':self.row=[]
  if t in ['td','th']and self.row is not None:self.cell=[]
  if t=='a':self.href=a.get('href');self.text=[]
 def handle_data(self,d):
  if self.cell is not None:self.cell.append(d)
  if self.href:self.text.append(d)
 def handle_endtag(self,t):
  if t in ['td','th']and self.cell is not None:
   if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
   self.cell=None
  if t=='tr'and self.row is not None:self.rows.append(self.row);self.row=None
  if t=='a'and self.href:self.links.append((self.href,' '.join(self.text)));self.href=None
p=P();p.feed((root/'elmos-products.html').read_text());urls=sorted({urllib.parse.urljoin('https://www.elmos.com',u)for u,n in p.links if '/english/products/'in u and '/contacts/'not in u})
def fetch(u):
 try:
  s=urllib.request.urlopen(u,timeout=25).read().decode();p=P();p.feed(s);rows=[r for r in p.rows if r and re.search(r'\bE\d{3}\.\d{2}\b',r[0])];return {'url':u,'rows':rows,'links':[(urllib.parse.urljoin(u,h),n)for h,n in p.links if re.search(r'\bE\d{3}\.\d{2}\b',n)]}
 except Exception as e:return {'url':u,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as ex:results=list(ex.map(fetch,urls))
(root/'elmos-reviewed-tables.json').write_text(json.dumps(results,indent=2))
for d in results:
 print(d['url'],d.get('error',''),len(d.get('rows',[])))
 for r in d.get('rows',[]):print(json.dumps(r))
