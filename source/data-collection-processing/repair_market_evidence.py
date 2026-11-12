import json,hashlib
from pathlib import Path
from urllib.request import Request,urlopen
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
P=Path('repair-notes/2026-10-21-market-coverage')
store=StorageSettings.load(Path('config/collection-storage.s3.json')).store()
urls={
'AADI.US':'https://infomemo.theocc.com/infomemos?number=56219',
'ATLN.SW':'https://www.globenewswire.com/news-release/2017/10/31/1160492/0/en/cancellation-of-publicly-held-actelion-shares-and-delisting-from-six-swiss-exchange-as-of-november-7-2017.html',
'MMED.NEO':'https://www.sec.gov/Archives/edgar/data/1813814/000095017024039484/mnmd-ex99_1.htm',
'AELIS.PA':'https://www.euronext.com/en/about/media/euronext-press-releases/aelis-farma-lists-euronext-paris',
'1SXP.XETRA':'https://ir.schott-pharma.com/investor-relations/share/basic-information'}
out={}
for symbol,url in urls.items():
 try:
  with urlopen(Request(url,headers={'User-Agent':'Optima Holdings support@optima-holdings.com'}),timeout=40) as response:raw=response.read(4000000)
  e=EvidenceClient(store,'market_coverage_review');e.save(raw,url);out[symbol]=e.evidence
  (P/('evidence-'+symbol.replace('/','_')+'.bin')).write_bytes(raw)
  print(symbol,len(raw))
 except Exception as exc:print(symbol,type(exc).__name__,getattr(exc,'code',''))
(P/'primary-evidence.json').write_text(json.dumps(out,indent=2))
