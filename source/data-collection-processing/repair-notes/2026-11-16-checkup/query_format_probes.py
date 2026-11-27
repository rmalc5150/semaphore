import json,collections
from pathlib import Path
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from additional_source_apis import get_json
P=Path(__file__).parent;store=StorageSettings.load(Path('config/collection-storage.s3.json')).store();out={}
j=json.load(open(P/'biorxiv-job.json'));c=EvidenceClient(store,j['source']);url='https://api.biorxiv.org/details/'+j['parameters']['repository']+'/'+j['start']+'/2026-06-30/0'
try:
 d,_=get_json(c,url);rows=d.get('collection',[]);g=collections.defaultdict(list)
 for r in rows:g[(r.get('doi'),str(r.get('version')))].append(r)
 dup=[{'doi':k[0],'version':k[1],'copies':len(v),'identical':all(x==v[0]for x in v),'differing_keys':[f for f in set().union(*(set(x)for x in v))if any(x.get(f)!=v[0].get(f)for x in v)]}for k,v in g.items()if len(v)>1];out['biorxiv']={'messages':d.get('messages'),'rows':len(rows),'duplicates':dup,'evidence':c.evidence};print('BIO',json.dumps(out['biorxiv']),flush=True)
except Exception as e:print('BIO',getattr(e,'code',str(e)),flush=True)
j=json.load(open(P/'portwatch-job.json'));c=EvidenceClient(store,j['source']);url=j['parameters']['url'];where="date >= DATE '"+j['start']+"' AND date < DATE '"+j['end']+"'"
for size in (1000,100):
 try:
  d,_=get_json(c,url,{'where':where,'outFields':'*','returnGeometry':'false','orderByFields':'ObjectId ASC','resultRecordCount':size,'resultOffset':0,'f':'json'});out['portwatch-'+str(size)]={'count':len(d.get('features',[])),'error':d.get('error'),'transfer_limit':d.get('exceededTransferLimit'),'evidence':c.evidence[-1:]};print('PORTWATCH',size,json.dumps(out['portwatch-'+str(size)]),flush=True)
 except Exception as e:print('PORTWATCH',size,getattr(e,'code',str(e)),flush=True)
(P/'query-format-probes.json').write_text(json.dumps(out,indent=2))
