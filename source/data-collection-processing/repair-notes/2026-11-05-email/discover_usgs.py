import requests,re,json
from pathlib import Path
out={};proof={}
for mineral in ('lithium','cobalt','nickel','graphite'):
 index='https://www.usgs.gov/centers/national-minerals-information-center/'+mineral+'-statistics-and-information'
 r=requests.get(index,timeout=25);r.raise_for_status()
 for link in re.findall(r'href=[\"\x27]([^\"\x27]+)',r.text):
  m=re.search(r'/mcs-(201[5-9])-[a-z]+\.pdf$',link)
  if m and link.startswith(('https://d9-wret.s3.us-west-2.amazonaws.com/','https://d9-wret.s3-us-west-2.amazonaws.com/')):
   canonical=f'https://pubs.usgs.gov/periodicals/mcs{m[1]}/mcs{m[1]}-{mineral}.pdf';out[canonical]=link;proof[canonical]={'official_index':index,'download_url':link}
Path('usgs_archive_urls.py').write_text('"""Exact archive links discovered on official USGS mineral pages, November 5, 2026."""\nARCHIVES = '+repr(out)+'\n\ndef resolve(url):\n    return ARCHIVES.get(url, url)\n')
Path('repair-notes/2026-11-05-email/usgs-link-provenance.json').write_text(json.dumps(proof,indent=2));print('reviewed links',len(out))
