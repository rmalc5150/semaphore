import json
from pathlib import Path
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from additional_source_apis import get_json
P=Path(__file__).parent;settings=StorageSettings.load(Path('config/collection-storage.s3.json'));store=settings.store();out={}
c=EvidenceClient(store,'fred_alfred_series_and_vintages')
try:
 d,_=get_json(c,'https://api.stlouisfed.org/fred/series/vintagedates',{'series_id':'DTWEXBGS','file_type':'json','sort_order':'asc','limit':5},'FRED');out['fred']={'vintage_dates':d.get('vintage_dates'),'evidence':c.evidence};print('FRED',out['fred'],flush=True)
except Exception as e:out['fred']={'error':type(e).__name__+':'+str(e)};print('FRED',out['fred'],flush=True)
c=EvidenceClient(store,'usgs_minerals')
for slug in ('cobal','cobalt'):
 url='https://pubs.usgs.gov/periodicals/mcs2019/mcs2019-'+slug+'.pdf'
 try:
  body=c.get(url);out[slug]={'bytes':len(body),'pdf':body.startswith(b'%PDF'),'evidence':c.evidence[-1:]};print('USGS',slug,out[slug],flush=True)
 except Exception as e:out[slug]={'error':getattr(e,'code',type(e).__name__)};print('USGS',slug,out[slug],flush=True)
c=EvidenceClient(store,'us_census_international_trade_api')
for period,commodity in [('2019-01','260400'),('2019-01','-'),('2026-10','-'),('2026-09','-')]:
 try:
  d,_=get_json(c,'https://api.census.gov/data/timeseries/intltrade/imports/hs',{'get':'CTY_CODE,CTY_NAME,I_COMMODITY,GEN_VAL_MO','I_COMMODITY':commodity,'CTY_CODE':'*','YEAR':period[:4],'MONTH':period[5:]},'US-census','key',allow_empty=True);out['census-'+period+'-'+commodity]={'rows':len(d)-1 if d else None,'no_content':d is None,'evidence':c.evidence[-1:]};print('CENSUS',period,commodity,out['census-'+period+'-'+commodity],flush=True)
 except Exception as e:print('CENSUS',period,getattr(e,'code',type(e).__name__),flush=True)
(P/'provider-probes.json').write_text(json.dumps(out,indent=2))
