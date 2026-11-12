from html.parser import HTMLParser
from pathlib import Path
import json
from urllib.parse import urljoin
class P(HTMLParser):
 def __init__(self):super().__init__();self.a=None;self.rows=[]
 def handle_starttag(self,t,attrs):
  if t=='a':self.a=[dict(attrs).get('href',''),[]]
 def handle_data(self,d):
  if self.a is not None:self.a[1].append(d)
 def handle_endtag(self,t):
  if t=='a'and self.a is not None:
   u,n=self.a;self.rows.append({'name':' '.join(''.join(n).split()),'url':urljoin('https://www.kla.com',u)});self.a=None
root=Path(__file__).parent;s=(root/'kla-products-az.html').read_text();s=s[s.index('<h3 id="numbers">'):s.index('Need refurbished, certified')];p=P();p.feed(s);rows=[x for x in p.rows if x['name']]
(root/'kla-reviewed-index.json').write_text(json.dumps(rows,indent=2));print('TOTAL',len(rows))
for x in rows:
 if any(t in x['url'] for t in ['/chip-manufacturing/','/wafer-manufacturing/','/reticle-qualification','/packaging-manufacturing/','/software-solutions/semiconductor','/certified-remanufactured/','/instruments/']):print(x['name'],x['url'].split('/products/')[-1])
