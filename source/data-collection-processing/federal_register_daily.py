"""Resume parent-discovered S51 full-notice evidence outside the shared heavy queue."""
import fcntl
import json
from datetime import datetime,timedelta,timezone
from collection_storage import StorageSettings,now,write_json
from research_contract import ROOT,digest,load_json
from specialist_inputs import discover_children,collect
from window_publication import list_keys


def main():
    with (ROOT/'.federal-register-daily.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
        key='operations/federal-register/daily-enrichment-state.json';stored=store.get(key)
        state=json.loads(stored.body) if stored else {'seeded':[],'jobs':{}}
        scheduler=json.loads(store.get('operations/specialists/scheduler/daily.json').body)
        today=datetime.now(timezone.utc).date().isoformat()
        for row in scheduler['jobs'].values():
            if row['source']!='federal_register' or row.get('status') not in {'complete','partial'} or not row.get('manifest') or row['last_attempt'][:10]!=today:continue
            manifest=row['manifest']
            if manifest not in state['seeded']:
                discover_children(store,manifest,row['job']);state['seeded'].append(manifest)
        universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
        jobs=[]
        for path in list_keys(store,settings,'operations/federal-register/discovered-jobs/'):
            # Names are digests: inspect only this small metadata queue; no document bodies read.
            job=json.loads(store.get(path).body)
            if job.get('source')!='federal_register_documents' or job.get('execution_lane')!='fr_enrichment':continue
            identity=digest(job);prior=state['jobs'].get(identity,{})
            if prior.get('status')=='complete' or prior.get('retry_after','')>now():continue
            jobs.append((prior.get('last_attempt',''),identity,job))
        results=[]
        for _,identity,job in sorted(jobs,key=lambda r:(r[0],r[1]))[:8]:
            prior=state['jobs'].get(identity,{})
            execution_job=json.loads(json.dumps(job))
            # Keep retrying missing originals. A body-only capture is retained
            # as evidence by the collector, but cannot finish the document job.
            execution_job['parameters'].pop('allow_partial',None)
            result=collect(execution_job,store,settings,universe,taxonomy,1)
            entry={**result,'last_attempt':now(),'attempts':prior.get('attempts',0)+1}
            if result['status']!='complete':entry['retry_after']=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat().replace('+00:00','Z')
            state['jobs'][identity]=entry;results.append({'document_number':job['parameters']['listing']['document_number'],**entry})
            if result['status']=='complete':
                queue='operations/specialists/publication-queue/fr-'+identity+'.json'
                if store.get(queue) is None:write_json(store,queue,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
            current=store.get(key);write_json(store,key,state,current.token if current else None)
        current=store.get(key);write_json(store,key,state,current.token if current else None)
        report={'at':now(),'pending_at_start':len(jobs),'outcomes':results,'completed':sum(r.get('status')=='complete' for r in state['jobs'].values())}
        (ROOT/'reports/federal-register-daily-enrichment-latest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)

if __name__=='__main__':main()
