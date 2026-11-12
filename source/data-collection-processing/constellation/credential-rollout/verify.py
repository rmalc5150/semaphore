"""Read native scheduler evidence for the requested credential-backed sources."""
import json
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]
def main():
 c=Control();names=json.loads((ROOT/'constellation/credential-rollout/selected-sources.json').read_text())+['epo_ops_patent_legal_events']
 def go(name):
  result={'source':name}
  for mode,key in [('historical',c.config['prefix']+'/specialist-schedulers/constellation-specialist-'+name+'.service/historical.json'),('daily',c.config['prefix']+'/daily-api-schedulers/'+name+'/daily.json')]:
   try:
    r=c.s3.get_object(Bucket=c.config['bucket'],Key=key)
    try:d=json.loads(r['Body'].read())
    finally:r['Body'].close()
    rows=list(d.get('jobs',{}).values());recent=sorted(rows,key=lambda r:r.get('last_attempt',''),reverse=True);result[mode]={'tasks':len(rows),'records':sum(r.get('records',0) or 0 for r in rows),'statuses':{s:sum(r.get('status')==s for r in rows) for s in ('complete','partial','failed')},'last_attempt':recent[0].get('last_attempt') if recent else None,'recent_reasons':list(dict.fromkeys(r.get('reason') for r in recent[:4] if r.get('reason'))),'sample_manifests':[r['manifest'] for r in recent[:2] if r.get('manifest')]}
   except c.s3.exceptions.NoSuchKey:result[mode]=None
  return result
 with ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(go,names))
 result={'checked_at':datetime.now(timezone.utc).isoformat(),'sources':rows};(ROOT/'constellation/credential-rollout/current-status.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
