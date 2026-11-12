import json,hashlib
from pathlib import Path
from urllib.request import Request,urlopen
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
P=Path('repair-notes/2026-10-21-market-coverage')
store=StorageSettings.load(Path('config/collection-storage.s3.json')).store()
urls={'1COV.XETRA':'https://annualreport.covestro.com/annual-financial-report-2025/en/report/capital-market/covestro-shares/','1CO.XETRA':'https://www.cashmarket.deutsche-boerse.com/cash-en/Stay-Informed/newsroom/Xetra-Frankfurt-Newsboard/XETR-Deletion-of-Instruments-from-XETRA-05.12.2025-4841756'}
out=json.loads((P/'primary-evidence.json').read_text())
for symbol,url in urls.items():
 try:
  with urlopen(Request(url,headers={'User-Agent':'Optima Holdings support@optima-holdings.com'}),timeout=40) as response:raw=response.read(4000000)
  e=EvidenceClient(store,'market_coverage_review');e.save(raw,url);out[symbol]=e.evidence
  (P/('evidence-'+symbol.replace('/','_')+'.bin')).write_bytes(raw)
  print(symbol,len(raw))
 except Exception as exc:print(symbol,type(exc).__name__,getattr(exc,'code',''))
(P/'primary-evidence.json').write_text(json.dumps(out,indent=2))
