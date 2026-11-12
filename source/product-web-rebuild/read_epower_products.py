import urllib.request,json,re,html,concurrent.futures
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parent
class Text(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ['script','style','noscript']:self.skip+=1
 def handle_endtag(self,tag):
  if tag in ['script','style','noscript']:self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip and data.strip():self.parts.append(data.strip())
def read(r):
 s=urllib.request.urlopen(urllib.request.Request(r['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode();slug=r['url'].rstrip('/').split('/')[-1];(root/('epower-'+slug+'.html')).write_text(s)
 h=re.search(r'<h1[^>]*>.*?</h1>',s,re.S);part=s[h.end():] if h else s
 part=re.split(r'Related Products|Related products',part)[0];p=Text();p.feed(part);r['detail_text']=' '.join(p.parts);r['tables']=[]
 for t in re.findall(r'<table.*?</table>',part,re.S):
  q=Text();q.feed(t);r['tables'].append(' | '.join(q.parts))
 return r
rows=json.loads((root/'epower-reviewed-index.json').read_text());result=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for r in pool.map(read,rows):result.append(r)
(root/'epower-product-details.json').write_text(json.dumps(result,indent=2));print('staged',len(result))
for i,r in enumerate(result):
 print(i,r['title']);print(('TABLES '+'\n'.join(r['tables']))[:2300] if r['tables'] else r['detail_text'][:1500])
