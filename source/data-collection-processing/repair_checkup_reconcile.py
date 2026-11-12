"""Reconcile only exact repaired outcomes; never advance coverage watermarks."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from collection_operations import Operations
from research_contract import ROOT,load_json
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store();results=[]
for step in ('hkex-docx','hkex-removed','hkex-history','clinicaltrials','hkex-sep28'):
 report=json.loads((ROOT/f'repair-notes/2026-10-23-checkup/{step}.json').read_text())
 result=next(e for e in report['events'] if e.get('manifest'))
 m=json.loads(store.get(result['manifest']).body);t=m['task']
 head=json.loads(store.get('checkpoints/'+m['task_id']+'/head.json').body)
 if result['manifest'] not in head['terminal_history']:raise ValueError('Uncommitted repair')
 u=json.loads(store.get('manifests/configurations/universe/'+t['universe_hash']+'.json').body);tax=json.loads(store.get('manifests/configurations/taxonomy/'+t['taxonomy_hash']+'.json').body)
 config=load_json(ROOT/('config/core-historical-schedule.json' if t['mode']=='historical' else 'config/collection-operations.json'))
 op=Operations(store,s,config,u,tax)
 zone=ZoneInfo('Asia/Hong_Kong') if t['source']=='hkex_news' else ZoneInfo('UTC')
 a,b=[datetime.fromisoformat(t['window'][x].replace('Z','+00:00')).astimezone(zone).date() for x in ('start','end')]
 source='hkex-filings' if t['source']=='hkex_news' else 'clinicaltrials'
 key=op.outcome_key(source,a,b,t['mode']);obj=store.get(key)
 if not obj:results.append({'step':step,'status':'outcome_not_found','key':key});continue
 prior=json.loads(obj.body)
 if not prior.get('manifest'):results.append({'step':step,'status':'no_prior_manifest','key':key});continue
 old=json.loads(store.get(prior['manifest']).body)
 if old['task']!=t:raise ValueError('Scope mismatch')
 if prior['manifest']==result['manifest']:continue
 if prior['status']=='complete':raise ValueError('Do not downgrade completed outcome')
 backup='operations/repairs/2026-10-23-checkup/outcomes/'+step+'.json'
 write_json(store,backup,{'before':prior,'replacement_manifest':result['manifest'],'at':now()})
 updated={**prior,'status':m['status'],'reason':m.get('reason_code') or 'page_limit','manifest':result['manifest'],'finished_at':m['finished_at'],'repair_receipt':backup}
 write_json(store,key,updated,obj.token)
 results.append({'step':step,'status':'reconciled_partial','records':m['record_count'],'key':key,'manifest':result['manifest']})
(ROOT/'repair-notes/2026-10-23-checkup/outcome-reconciliation.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
