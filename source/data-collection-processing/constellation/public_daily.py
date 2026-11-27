"""Small sequential public-file batches on the controller, with source fairness."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import uuid

from constellation.control import Control
from public_source_capture import PREFIX,read_json,run,save_checkpoint

ROOT=Path(__file__).resolve().parents[1]

def main(*, batch_receipts=False):
    parser=argparse.ArgumentParser();parser.add_argument('--sources',type=int,default=6);parser.add_argument('--limit',type=int,default=2);args=parser.parse_args()
    c=Control()
    if not c.daily_allowed():
        print(json.dumps({'status':'paused'}));return
    sources=json.loads((ROOT/'config/constellation-public-sources.json').read_text())['sources']
    sources=[source for source in sources if source.get('enabled',True) and source.get('daily_execution','controller')!='worker']
    key=PREFIX+'/daily-fairness.json';state,token=read_json(c.s3,key);state=state or {'sources':{}}
    sources.sort(key=lambda s:(state['sources'].get(s['source'],''),s['catalog_entry'] not in (65,68,82,129,152),s['catalog_entry']))
    results=[]
    for source in sources[:args.sources]:
        try:
            report=run(source,'daily',args.limit,s3=c.s3,batch_receipts=batch_receipts)
            result={k:report[k] for k in ('source','captured_urls','remaining_urls','failed_urls')}
            results.append({**result, 'attempts':len(report['outcomes'])})
        except Exception as e:
            results.append({'source':source['source'],'error':type(e).__name__})
        state['sources'][source['source']]=datetime.now(timezone.utc).isoformat()
        if not batch_receipts:
            token = save_checkpoint(c.s3,key,state,token)
    if batch_receipts and results:
        save_checkpoint(c.s3,key,state,token)
    print(json.dumps({'daily_public_sources':results}),flush=True)
    return results

if __name__=='__main__':main()
