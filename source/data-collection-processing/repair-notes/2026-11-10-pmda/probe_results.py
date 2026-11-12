from pathlib import Path
import json,re
from bs4 import BeautifulSoup
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
p=Path(__file__).parent;html=(p/'search-page.html').read_text();soup=BeautifulSoup(html,'html.parser');form=soup.find('form');params=[]
for tag in form.find_all(['input','select']):
 name=tag.get('name')
 if not name:continue
 if tag.name=='input':
  kind=tag.get('type','text')
  if kind in ['button','submit','image']or(kind in ['radio','checkbox']and not tag.has_attr('checked')):continue
  value=tag.get('value','')
 else:
  option=tag.find('option',selected=True)or tag.find('option');value=option.get('value','')if option else ''
 if name=='ListRows':value='100'
 params.append((name,value))
params.extend([('btnA.x','1'),('btnA.y','1')]);url='https://www.pmda.go.jp/PmdaSearch/iyakuSearch';request=Request(url,data=urlencode(params).encode(),headers={'User-Agent':'Optima Holdings support@optima-holdings.com','Content-Type':'application/x-www-form-urlencoded'})
with urlopen(request,timeout=60)as response:raw=response.read();print('url',response.url,'bytes',len(raw))
p.joinpath('results.html').write_bytes(raw);c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'japan_pmda');c.save(raw,url,'text/html');p.joinpath('results-evidence.json').write_text(json.dumps(c.evidence,indent=2));doc=BeautifulSoup(raw,'html.parser');print(doc.get_text(' ',strip=True)[-2600:]);print('links',[(a.get_text(' ',strip=True),a.get('href'))for a in doc.find_all('a',href=True)][:12]);p.joinpath('search-params.json').write_text(json.dumps(params,indent=2))
