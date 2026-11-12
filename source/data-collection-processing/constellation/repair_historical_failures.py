"""Verify stable NSF pagination and retry repaired historical failures once."""
import base64
from pathlib import Path
from constellation.finish_aux_migration import remote,T3,M7

def main():
 remote(T3,'''from constellation.control import Control
from constellation.sources import request,parse
import requests,json,time
from datetime import datetime,timezone
c=Control();spec={'source_key':'nsf_awards','dataset':'research_awards','extractor_version':'constellation-raw-v1','parameters':{},'geography':'global','edition':'current_retrieval','start':'2020-04-27','end':'2020-04-28'}
seen=set();cursor=None;total=None;pages=[]
for n in range(8):
 with c.db()as q:
  q.execute("INSERT INTO backfill_quotas(source_key,quota_day,used_requests,next_request_at) VALUES('nsf_awards',UTC_DATE(),0,0) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)")
  q.execute("SELECT used_requests,next_request_at FROM backfill_quotas WHERE source_key='nsf_awards' AND quota_day=UTC_DATE() FOR UPDATE");budget=q.fetchone()
  if budget['used_requests']>=1000:raise RuntimeError('NSF daily budget exhausted')
  wait=max(0,float(budget['next_request_at'])-time.time());time.sleep(wait)
  q.execute("UPDATE backfill_quotas SET used_requests=used_requests+1,next_request_at=UNIX_TIMESTAMP()+3 WHERE source_key='nsf_awards' AND quota_day=UTC_DATE()")
 url,params=request(spec,cursor);r=requests.get(url,params=params,timeout=(10,30),headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'});r.raise_for_status()
 rows,next_cursor=parse(spec,r.content,cursor);ids=[x['id']for x in rows]
 if len(set(ids))!=len(ids)or seen.intersection(ids):raise RuntimeError('NSF stable sort still duplicated records')
 metadata=r.json()['response']['metadata'];total=int(metadata['totalCount'])
 seen.update(ids);pages.append({'offset':params['offset'],'ids':ids,'total':total});print(json.dumps({'page':n,'offset':params['offset'],'rows':len(rows),'total':total}),flush=True)
 if next_cursor is None:break
 cursor=next_cursor
else:raise RuntimeError('NSF pilot did not exhaust pagination')
if len(seen)!=total:raise RuntimeError('NSF total mismatch')
proof={'verified_at':datetime.now(timezone.utc).isoformat(),'spec':spec,'sortKey':'awardNumber','pages':pages,'unique_records':len(seen),'status':'verified'}
key=c.config['prefix']+'/repairs/nsf-stable-sort-pilot.json';c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=json.dumps(proof).encode(),ServerSideEncryption='AES256');print(json.dumps(proof))
''')
 body=base64.b64encode((Path(__file__).parent/'sources.py').read_bytes()).decode()
 remote(M7,'''from pathlib import Path
import base64,subprocess
root=Path('/opt/constellation/constellation');p=root/'sources.py'
assert p.exists()
data=base64.b64decode(BODY);compile(data,str(p),'exec');tmp=p.with_suffix('.repair');tmp.write_bytes(data);tmp.replace(p)
print('Installed stable NSF sort; restarting raw workers gracefully')
subprocess.run(['systemctl','restart','--no-block','constellation-backfill@1.service','constellation-backfill@2.service','constellation-backfill@3.service','constellation-backfill@4.service','constellation-backfill@5.service'],check=True)
'''.replace('BODY',repr(body)))
 remote(T3,'''from constellation.control import Control
from source_pauses import unit_pause
import json,uuid,time
c=Control();routes=json.load(open('config/constellation-legacy-routes.json'))['routes'];enabled={'legacy:'+r['unit'] for r in routes if r.get('execution_enabled') and r.get('route_kind')!='migration_probe' and not unit_pause(r.get('original_unit',r['unit']))}
selected=[]
with c.db()as q:
 q.execute("SELECT * FROM backfill_jobs WHERE status IN ('blocked','retryable_failed') AND lease_until<UNIX_TIMESTAMP() FOR UPDATE")
 for row in q.fetchall():
  result=json.loads(row.get('result_json')or '{}');source=row['source_key'];reason=result.get('reason','')
  nsf=source=='nsf_awards' and ('Duplicate provider identities' in reason or reason in ('attempt_budget_exhausted',"(1040, 'Too many connections')","(1213, 'Deadlock found when trying to get lock; try restarting transaction')"))
  bio=source=='legacy:constellation-specialist-biorxiv_medrxiv_preprints.service' and source in enabled and result.get('exit_code')==1 and result.get('checkpoint_verified')
  transient=source in enabled and result.get('exit_code') in (130,137) and result.get('checkpoint_verified')
  if nsf or bio or transient:selected.append(row)
 key=c.config['prefix']+'/repairs/requeue-'+uuid.uuid4().hex+'.json';c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=json.dumps(selected,default=str).encode(),ServerSideEncryption='AES256')
 for row in selected:
  q.execute("UPDATE backfill_jobs SET status='pending',attempts=0,lease_until=0,next_attempt_at=UNIX_TIMESTAMP()+%s,updated_at=UNIX_TIMESTAMP() WHERE job_id=%s AND status=%s",(len(selected)%120,row['job_id'],row['status']))
 print(json.dumps({'requeued':len(selected),'previous_failure_archive':key,'by_source':{s:sum(r['source_key']==s for r in selected)for s in sorted({r['source_key']for r in selected})}}))
''')
if __name__=='__main__':main()
