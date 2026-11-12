from html.parser import HTMLParser
from pathlib import Path
import urllib.request,json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pypdf import PdfReader
p=Path(__file__).resolve().parent
class P(HTMLParser):
 def __init__(self):super().__init__();self.urls={}
 def handle_starttag(self,t,a):
  d=dict(a);u=d.get('href','')
  if t=='a' and '.pdf' in u.lower() and 'pi.amgen.com' in u and ('_pi' in u.lower() or '_fpi' in u.lower()):
   name=u.split('/united_states/')[1].split('/')[0];self.urls.setdefault(name.upper(),u.replace('http://','https://'))
x=P();x.feed((p/'amgen-products.html').read_text());(p/'amgen-label-urls.json').write_text(json.dumps(x.urls,indent=2))
def read(z):
 name,u=z;f=p/f'amgen-label-{name}.pdf';f.write_bytes(urllib.request.urlopen(u,timeout=40).read());s=PdfReader(f).pages[0].extract_text();(p/f'amgen-label-{name}-firstpage.txt').write_text(s);return name,s
with ThreadPoolExecutor(max_workers=4) as ex:
 for f in as_completed([ex.submit(read,z) for z in x.urls.items()]):
  try:
   name,s=f.result();print(name,repr(s[:450]),flush=True)
  except Exception as e:print('ERROR',str(e),flush=True)
