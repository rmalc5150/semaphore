import urllib.request,re,html,json,concurrent.futures
from pathlib import Path
root=Path(__file__).resolve().parent
urls={'powerbanks':'https://www.powerhouse.je/smart-tech-phones-c952/phones-c151/powerbanks-c1024','portable':'https://www.powerhouse.je/smart-tech-phones-c952/powerstations-solar-c1334/portable-powerstations-and-solar-c1335','robots':'https://www.powerhouse.je/small-appliances-c958/floor-care-c501/robot-vacuums-c758'}
def read(kv):
 key,u=kv;s=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=45).read().decode();(root/('jersey-'+key+'.html')).write_text(s);rows=[]
 for part in s.split('<div class="product product--')[1:]:
  code=re.search(r'data-productreference="([^"]*)"',part);a=re.search(r'<div class="product__details__title[^>]*>\s*<a\s+href="([^"]+)"\s+title="([^"]+)"',part,re.S)
  if not code or not a:continue
  rows.append({'category':key,'code':html.unescape(code[1]),'url':'https://www.powerhouse.je'+html.unescape(a[1]),'name':' '.join(html.unescape(a[2]).split())})
 return key,rows
allrows={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for key,rows in pool.map(read,urls.items()):
  print(key,len(rows))
  for r in rows:allrows[r['url']]=r
(root/'jersey-reviewed-index.json').write_text(json.dumps(list(allrows.values()),indent=2))
for i,r in enumerate(allrows.values()):print(i,r['category'],r['code'],r['name'])
