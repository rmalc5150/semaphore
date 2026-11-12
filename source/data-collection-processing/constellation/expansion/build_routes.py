"""Expand working historical adapters into independent source-owned workspaces."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    plan=json.loads((ROOT/'config/specialist-inputs.json').read_text());plan['backfill_end_exclusive']='2026-10-26'
    (ROOT/'config/constellation-specialist-historical.json').write_text(json.dumps(plan,indent=2)+'\n')
    path=ROOT/'config/constellation-legacy-routes.json';data=json.loads(path.read_text());added=[];blocked=[]
    for source in plan['sources']:
        key=source['source']
        if not source.get('enabled') or not source.get('historical'):continue
        # Their existing per-host budgets must be migrated before cross-host use.
        if key in ('mlperf_results','sam_gov_opportunities','uspto_assignment_histories'):
            blocked.append({'source':key,'reason':{'mlperf_results':'shared_GitHub_rolling_quota','sam_gov_opportunities':'shared_SAM_hourly_daily_quota','uspto_assignment_histories':'USPTO_account_shared_quota'}[key]});continue
        unit='constellation-specialist-'+key+'.service'
        row={'unit':unit,'route_kind':'independent_specialist_historical','specialist_source':key,
            'argv':['specialist_inputs.py','--mode','historical','--lane',source.get('execution_lane','default'),'--source',key,'--max-jobs','8','--pages','6','--publish','0'],
            'start_target':'2016-01-01','end_exclusive':'2026-10-26','cadence_seconds':60,'timeout_seconds':1800,
            'execution_enabled':True,'remaining_requirements':[],
            'validation_basis':'Existing native adapter; isolated per-source historical scheduler; fixed mode/source; shared HTTP pacing; original task identities retained; private publication queue.'}
        if not any(r['unit']==unit for r in data['routes']):data['routes'].append(row)
        added.append(row)
    # Public core routes whose daily payloads already run on t3.
    for source in ('uk','japan'):
        unit='constellation-core-'+source+'-historical.service'
        template=next(r for r in data['routes'] if r['unit']=='constellation-core-clinicaltrials-historical.service')
        row={**template,'unit':unit,'argv':[*template['argv']]};row['argv'][row['argv'].index('--only')+1]=source
        if not any(r['unit']==unit for r in data['routes']):data['routes'].append(row)
        added.append(row)
    path.write_text(json.dumps(data,indent=2)+'\n')
    (ROOT/'constellation/expansion/route-plan.json').write_text(json.dumps({'added_routes':[r['unit'] for r in added],'temporary_gates':blocked},indent=2)+'\n')
    print(json.dumps({'independent_routes_added':len(added),'temporary_gates':blocked}))

if __name__=='__main__':main()
