"""One paid rendered-body probe, accounted against the production RSS Decodo cap."""
import json,hashlib
from pathlib import Path
from collection_storage import StorageSettings,now,write_json
from collection_operations import load_stored
from regulatory_collection import EvidenceClient
from people_rss_content import public_url,extract_html
from decodo_scraping_api import scrape_url,ScrapeError
p=Path(__file__).parent;store=StorageSettings.load('config/collection-storage.s3.json').store();entry=json.loads((p/'live-captures.json').read_text())[1];url=entry['url'];public_url(url);key='operations/news/fulltext/people_rss/decodo-budgets/'+now()[:10]+'.json';state,token=load_stored(store,key);count=(state or{}).get('requests',0);assert count<40;write_json(store,key,{'requests':count+1,'updated_at':now()},token)
out={'url':url,'diagnostic':'explicit rendered-transport probe; no claim of direct HTTP denial'}
try:
 html=scrape_url(url,headless='html');raw=html.encode();assert len(raw)<=8*1024*1024;client=EvidenceClient(store,'people_rss_article_content');client.save(raw,url,'text/html');text=extract_html(raw,url,'');out.update(status='passed',text_characters=len(text),text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_evidence=client.evidence,retrieval_method='decodo_rendered_html')
except Exception as error:out.update(status='failed',reason=getattr(error,'code',str(error)if isinstance(error,ScrapeError)else type(error).__name__))
(p/'decodo-live-probe.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
if out['status']!='passed':raise SystemExit(2)
