import json
from pathlib import Path
from datetime import date
from urllib.parse import urljoin
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from disclosure_collection import HKEX_API
p=Path(__file__).parent;settings=StorageSettings.load(Path('config/collection-storage.s3.json'));store=settings.store();client=EvidenceClient(store,'hkex_news')
status=json.load(open('repair-notes/2026-11-09-hkex-query/metadata-status.json'));raw=store.client.get_object(Bucket=store.bucket,Key=status['latest_failure']['input_key'])['Body'].read();record=next(json.loads(x)for x in raw.splitlines()if json.loads(x)['source_record_id']=='12343955');(p/'blocked-record.json').write_text(json.dumps(record,indent=2));target=record['payload']['data']
params={'sortDir':'0','sortByOptions':'DateTime','category':'0','market':'SEHK','stockId':'','documentType':'','fromDate':'20260923','toDate':'20260923','title':'','searchType':'0','t1code':'-2','t2Gcode':'-2','t2code':'-2','rowRange':100000,'lang':'ZH'}
d=client.json(HKEX_API,params=params);rows=json.loads(d['result'])if isinstance(d['result'],str)else d['result'];matches=[r for r in rows if str(r.get('NEWS_ID'))==str(target['NEWS_ID'])];candidates=[r for r in rows if r.get('STOCK_CODE')==target['STOCK_CODE'] and r.get('DATE_TIME')==target['DATE_TIME']]
out={'target':target,'total':d['recordCnt'],'returned':len(rows),'has_next':d['hasNextRow'],'exact_news_id_matches':matches,'diagnostic_issuer_time_candidates':candidates,'evidence':client.evidence};(p/'bilingual-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out)[:10000])
