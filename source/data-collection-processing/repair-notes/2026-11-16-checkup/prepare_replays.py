import json
from pathlib import Path
p=Path(__file__).parent
from reviewed_source_gaps import reviewed_gap
from research_contract import digest
rows=[]
for source in ['fred_alfred_series_and_vintages','biorxiv_medrxiv_preprints','us_census_international_trade_api','usgs_minerals','imf_portwatch_shipping_activity','usa_spending','wto_timeseries_api']:
 d=json.loads((p/(source+'-scheduler.json')).read_text());selected=[]
 for identity,r in d['jobs'].items():
  if r.get('status')not in('failed','partial'):continue
  job=r['job'];decision=reviewed_gap(job)
  if decision or source in ['us_census_international_trade_api','usgs_minerals'] or (source in ['imf_portwatch_shipping_activity','usa_spending','wto_timeseries_api'] and r['status']=='failed' and len(selected)<1):
   selected.append({'identity':identity,'job':job,'pages':3 if source=='imf_portwatch_shipping_activity' else 1})
 rows.extend(selected)
(p/'replay-jobs.json').write_text(json.dumps(rows,indent=2))
print('selected',len(rows),'bounded tasks')
