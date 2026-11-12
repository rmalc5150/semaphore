import json,re,urllib.request,concurrent.futures
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parent
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,t,a):
  if t in ['script','style','noscript']:self.skip+=1
 def handle_endtag(self,t):
  if t in ['script','style','noscript']:self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip():self.parts.append(d.strip())
def read(r):
 try:
  s=urllib.request.urlopen(urllib.request.Request(r['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read().decode()
  (root/('jersey-product-'+r['code']+'.html')).write_text(s)
  h=re.search(r'<h1[^>]*>.*?</h1>',s,re.S);part=s[h.start():] if h else s
  p=Text();p.feed(part);r['detail_text']=' '.join(p.parts)
 except Exception as e:r['error']=str(e)
 return r
rows=[r for r in json.loads((root/'jersey-reviewed-index.json').read_text()) if r['code']!='502728']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(read,rows))
(root/'jersey-product-details.json').write_text(json.dumps(result,indent=2))
for i,r in enumerate(result):print(i,r['code'],r['name'],'\n',r.get('error',r.get('detail_text','')[:2600]))
