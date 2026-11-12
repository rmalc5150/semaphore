"""S59 versioned CES labor context. No inferred release dates or company costs."""
import copy
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from collection_storage import now
from research_contract import digest
from regulatory_collection import require

VERSION='bls-labor-context-v2'
API='https://api.bls.gov/publicAPI/v2/timeseries/data/'
DEFINITIONS={
 'CES3000000003':('Average hourly earnings of all employees, manufacturing','USD/hour','all employees'),
 'CES3000000001':('All employees, manufacturing','thousand employees','all employees'),
 'CES3000000002':('Average weekly hours of all employees, manufacturing','hours/week','all employees'),
 'CES3000000004':('Average weekly overtime hours of all employees, manufacturing','hours/week','all employees'),
}

def number(value):
    try:
        value=Decimal(str(value).replace(',',''))
        return value if value.is_finite() else None
    except (InvalidOperation,ValueError):return None

def period(row):
    p=row['period'];y=int(row['year'])
    require(re.fullmatch(r'M(0[1-9]|1[0-3])',p) is not None,'bls_invalid_period')
    return f'{y:04d}-{int(p[1:]):02d}' if p!='M13' else f'{y:04d}-annual'

def shift(p,delta):
    y,m=map(int,p.split('-'));n=y*12+m-1+delta
    return f'{n//12:04d}-{n%12+1:02d}'

def history(client,year):
    cache=getattr(client,'bls_history',{})
    if year not in cache:
        response=client.json(API,body={'seriesid':list(DEFINITIONS),'startyear':str(year-1),'endyear':str(year)})
        require(response.get('status')=='REQUEST_SUCCEEDED','bls_provider_error')
        rows=response.get('Results',{}).get('series',[])
        require({s['seriesID'] for s in rows}==set(DEFINITIONS),'bls_companion_series_missing')
        cache[year]={s['seriesID']:{period(r):r for r in s['data']} for s in rows}
        client.bls_history=cache
    return cache[year]

def enrich(row,series,hist,observed_at=None):
    observed_at=observed_at or now();p=period(row);value=number(row['value'])
    require(series in DEFINITIONS,'bls_unknown_series')
    title,unit,population=DEFINITIONS[series]
    footnotes=[f for f in row.get('footnotes',[]) if f.get('code') or f.get('text')]
    changes={}
    if not p.endswith('annual') and value is not None:
        for label,delta in [('month_over_month',-1),('year_over_year',-12)]:
            base=hist.get(series,{}).get(shift(p,delta));b=number(base['value']) if base else None
            changes[label]={'baseline_period':shift(p,delta),'baseline_value':str(b) if b is not None else None,
                'absolute_change':str(value-b) if b is not None else None,
                'percent_change':str((value/b-1)*100) if b not in (None,0) else None,
                'baseline_observation':base,'vintage_basis':'current retrieval; not original historical release'}
    companion={s:{'definition':DEFINITIONS[s][0],'unit':DEFINITIONS[s][1],'observation':rows.get(p)}
        for s,rows in hist.items() if s!=series}
    return {'version':VERSION,'status':'enriched','metadata':{'series_id':series,'title':title,'unit':unit,
        'geography':'United States','industry':'manufacturing','naics':'31-33','employee_population':population,
        'frequency':'monthly','seasonally_adjusted':True,'nominal':True,
        'definition_source':'https://www.bls.gov/web/empsit/cesfaq.htm',
        'metadata_basis':'explicit reviewed CES series mapping; public API catalog unavailable'},
        'reference_period':p,'numeric_value':str(value) if value is not None else None,
        'quality':{'footnotes':footnotes,'preliminary':any(f.get('code')=='P' for f in footnotes),
                  'final_status':'not established','numeric_valid':value is not None},
        'timing':{'retrieved_at':observed_at,'official_published_at':None,'publication_evidence_status':'not recovered',
                  'point_in_time_eligible':False},'changes':changes,'companion_series':companion,
        'compensation_context':{'eci_url':'https://www.bls.gov/eci/','ecec_url':'https://www.bls.gov/ecec/',
            'status':'separate source joins required; no benefit multiplier or fully loaded cost inferred'},
        'sector_exposure':{'candidate_sectors':['robotics','semiconductors','energy_storage','biotech'],
            'basis':'broad manufacturing context only','company_links':[],
            'review_status':'requires evidenced US manufacturing activity and labor exposure; no automatic RDS match'},
        'observation_fingerprint':digest([series,p,row['value'],footnotes]),
        'event_policy':{'release':'requires official publication evidence; first collection is not proof of a new release',
            'revision':'compare same series and reference period with previous observed value; preserve both versions',
            'repeated_collection':'no new event','company_action_inferred':False}}

def daily_page(client,p,item):
    hist=history(client,int(p['year']));series=p['series']
    result=[]
    for key,r in sorted(hist[series].items()):
        if r['year']!=str(p['year']):continue
        enrichment=enrich(r,series,hist)
        from bls_evidence_joins import add_joins
        add_joins(client,r,enrichment)
        track_observation(client,series,r,enrichment)
        result.append(item(series+':'+r['year']+':'+r['period'],
            {'series':series,'unit':p['unit'],**r,'enrichment':enrichment},p['url'],None))
    return result,None



def track_observation(client,series,row,enrichment):
    """Observed changes only; retain prior snapshots and evidence, never assert release time."""
    from collection_storage import write_json
    key='operations/bls-labor/observed/'+series+'/'+period(row)+'.json'
    old=client.store.get(key)
    prior=__import__('json').loads(old.body) if old else None
    snapshot={'row':row,'observed_at':now(),'evidence':copy.deepcopy(client.evidence),
              'fingerprint':enrichment['observation_fingerprint']}
    if prior and prior['fingerprint']==snapshot['fingerprint']:
        enrichment['observed_change']={'kind':'unchanged','first_observed_at':prior['observed_at']}
        return
    if prior:
        archive='operations/bls-labor/versions/'+series+'/'+period(row)+'/'+prior['fingerprint']+'.json'
        write_json(client.store,archive,prior)
        changed=number(prior['row']['value'])!=number(row['value'])
        enrichment['observed_change']={'kind':'value_revision' if changed else 'quality_revision',
            'previous_observation':prior,'detected_at':snapshot['observed_at'],'official_published_at':None}
    else:
        enrichment['observed_change']={'kind':'first_observed','release_event_established':False}
    write_json(client.store,key,snapshot,old.token if old else None)
