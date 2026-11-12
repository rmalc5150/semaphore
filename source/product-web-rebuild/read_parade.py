from html.parser import HTMLParser
from pathlib import Path
import re,json,urllib.request,concurrent.futures
out=Path(__file__).resolve().parent
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.a=None;self.h1=False;self.head=[];self.text=[];self.skip=0
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in ['script','style']:self.skip+=1
  if t=='a':self.a=[a.get('href',''),'']
  if t=='h1':self.h1=True
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip=max(0,self.skip-1)
  if t=='a' and self.a:self.links.append(self.a);self.a=None
  if t=='h1':self.h1=False
 def handle_data(self,d):
  if not self.skip:
   if self.a:self.a[1]+=d
   if self.h1:self.head.append(d)
   if d.strip():self.text.append(d.strip())
p=Parse();p.feed((out/'parade-products.html').read_text());links={u:' '.join(n.split()) for u,n in p.links if re.match(r'^(PS|FL|DP|GC)\d',n.strip()) and '/products/' in u};print('catalogue_pages',len(links),flush=True)
(out/'parade-catalogue-links.json').write_text(json.dumps(links,indent=2))
def get(x):
 u,n=x
 try:
  data=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (product catalogue research)'}),timeout=20).read().decode()
  q=Parse();q.feed(data);slug=u.rstrip('/').split('/')[-1];(out/f'parade-{slug}.html').write_text(data)
  text=' '.join(q.text);title=' '.join(q.head).strip();i=text.find(title);return {'url':u,'catalogue_title':n,'title':title,'excerpt':text[i:i+5000] if i>=0 else text[:5000]}
 except Exception as e:return {'url':u,'catalogue_title':n,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:r=list(pool.map(get,links.items()))
(out/'parade-reviewed-pages.json').write_text(json.dumps(r,indent=2));print('retrieved',sum('error' not in x for x in r),'failed',sum('error' in x for x in r))
for x in r:print(x.get('title') or x.get('error'),x['url'])
