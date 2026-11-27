import json,boto3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
p=Path(__file__).parent;s=boto3.client('s3');bucket='data-collection-059416028963-us-east-1-an';proof=json.loads(Path('repair-notes/2026-11-18-checkup/monitoring-reconciliation.json').read_text())
def read(key):
 try:return json.loads(s.get_object(Bucket=bucket,Key='research-data/'+key)['Body'].read())
 except s.exceptions.NoSuchKey:return None
ids=[('fda',r['task_id'][5:])for r in proof['fda_windows']]+[('clinicaltrials','eaf37cc5744309b9d623215023d62bd756b27d6be2fe229e3f3ebace5aa98fa9')]
def one(entry):
 source,wid=entry;receipt=read('operations/regulatory/publication-receipts/'+wid+'.json');return {'source':source,'window_id':wid,'receipt':receipt}
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,ids))
(p/'publication-status.json').write_text(json.dumps(rows,indent=2));print('FDA verified',sum(r['source']=='fda' and (r['receipt']or{}).get('status')=='verified'for r in rows),'of 54');print('ClinicalTrials',rows[-1]['receipt'])
d=json.loads((p/'worker-health-before.json').read_text())
reports=d['jobs']['optima-research-publication.service']['reports'];last=reports[-1]['value'];(p/'research-publication-last-result.json').write_text(json.dumps(last,indent=2))
for owner,result in last.items():
 print('OWNER',owner,'SUMMARY',str(result)[:900])
