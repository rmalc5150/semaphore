"""Register bounded initial capture scopes for owner-supplied API credentials."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 registry=json.loads((ROOT/'config/constellation-source-registry.json').read_text())['sources'];p=ROOT/'config/constellation-specialist-historical.json';plan=json.loads(p.read_text());rp=ROOT/'config/constellation-legacy-routes.json';routes=json.loads(rp.read_text());dp=ROOT/'constellation/expansion/new-adapters.json';definitions=json.loads(dp.read_text());selected=[]
 indicators=json.loads((ROOT/'constellation/credential-rollout/wto-probe.json').read_text());usda_spec=json.loads((ROOT/'constellation/credential-rollout/usda-public-spec.txt').read_text())
 # Provider PSD commodity list is currently failing; use documented major crops,
 # with provider errors retained until access recovers. No invented observations.
 specs=[
 (51,'comtrade','https://comtradeapi.un.org/data/v1/get/C/A/HS','Keyed annual imports and exports for the existing five reporters and four battery/mineral HS6 commodities; world partner totals. Initial scope, not all trade flows.'),
 (70,'ember','https://api.ember-energy.org/v1','All available geography rows for monthly electricity generation and demand, since 2016; current released data, Ember CC-BY-4.0. Missing months are not inferred as zeros.'),
 (71,'wto_timeseries','https://api.wto.org/timeseries/v1/data','All currently catalogued indicators, all reporting economies, provider default partner/product scopes, by year since 2016; current vintages and explicit pagination. Not all bilateral/product combinations.'),
 (72,'wto_qr','https://api.wto.org/qrs','Notifications submitted since 2016 and restriction records entering into force since 2016. Current records, not historical database snapshots or a complete inventory of older restrictions still in force.'),
 (73,'wto_eping','https://api.wto.org/eping/notifications/search','English SPS/TBT notification metadata, all notifying members, distribution-date partitions since 2016; includes addenda and revisions, no attached document downloads.'),
 (75,'copernicus','https://cds.climate.copernicus.eu/api/retrieve/v1','ERA5 and ERA5-Land hourly 2m temperature and precipitation, eight named regional reference cells since 2016. Raw NetCDF archives with checksums; structured weather extraction pending. Current reanalysis, not original forecast vintages. Dataset licence acceptance required.'),
 (118,'census','https://api.census.gov/data/timeseries/intltrade','Monthly US imports and exports for TOTAL and four battery/mineral HS6 commodities across all partner codes since 2016; current releases, not original vintages. Country totals and commodity totals remain distinct.'),
 (125,'usda','https://apps.fas.usda.gov/OpenData/api/psd/commodity/{commodity}/country/all/year/{year}','Current PSD forecasts/estimates for corn, wheat, rice, soybeans and cotton, all countries, market years since 2016. Market year differs from release date; historical forecast vintages not supplied by this route.')]
 old_comtrade=next(s for s in plan['sources'] if s['source']=='un_comtrade')
 nasa=next(s for s in plan['sources'] if s['adapter']=='additional_nasa')
 template=next(r for r in routes['routes'] if r.get('specialist_source')=='cpsc_recalls')
 for entry,kind,url,note in specs:
  name=next(r['source_key'] for r in registry if r['catalog_entry']==entry) if any(r.get('catalog_entry')==entry for r in registry) else registry[entry-1]['source_key']
  source={'source_id':f'C{entry:03d}','source':name,'adapter':'additional_'+kind,'api':url,'enabled':True,'historical':True,'coverage_note':note}
  if kind=='comtrade':source['scopes']=[{'query':{'reporterCode':r,'cmdCode':cmd,'flowCode':flow,'partnerCode':0,'partner2Code':0,'customsCode':'C00','motCode':0},'reporter':r,'commodity':cmd,'flow':flow} for r in old_comtrade.get('reporters',[842,156,276,392,410]) for cmd in old_comtrade.get('commodities',['850760','260400','282520','250410']) for flow in ('M','X')]
  elif kind=='ember':source['scopes']=[{'dataset':x} for x in ('electricity-generation','electricity-demand')]
  elif kind=='wto_timeseries':source['scopes']=[{'indicator':r['code'],**({'no_time_dimension':True} if r.get('startYear')==0 and r.get('endYear')==0 else {})} for r in indicators]
  elif kind=='wto_qr':source['scopes']=[{'url':url+'/notifications','resource':'notifications','year_parameter':'notification_year'},{'url':url+'/qrs','resource':'qrs','year_parameter':'year_of_entry_into_force'}]
  elif kind=='copernicus':source['scopes']=[{'dataset':dataset,'location':r['location'],'area':[r['latitude']+.25,r['longitude']-.25,r['latitude']-.25,r['longitude']+.25]} for dataset in ('reanalysis-era5-single-levels','reanalysis-era5-land') for r in nasa['scopes']]
  elif kind=='census':source['scopes']=[{'direction':direction,'commodity':code} for direction in ('imports','exports') for code in ('TOTAL','850760','260400','282520','250410')]
  elif kind=='usda':source['scopes']=[{'commodity':code} for code in ('0440000','0410000','0422110','2222000','2631000')]
  else:source['scopes']=[{}]
  plan['sources']=[s for s in plan['sources'] if s['source']!=name]+[source]
  unit='constellation-specialist-'+name+'.service';row={**template,'unit':unit,'specialist_source':name,'argv':list(template['argv']),'catalog_entry':entry,'execution_enabled':True,'activation_staged':False,'remaining_requirements':[],'validation_basis':note};row['argv'][row['argv'].index('--source')+1]=name
  if kind in ('census','usda','copernicus'):row['argv'][row['argv'].index('--max-jobs')+1]='1';row['argv'][row['argv'].index('--pages')+1]='1'
  routes['routes']=[r for r in routes['routes'] if r['unit']!=unit]+[row]
  definitions=[r for r in definitions if r['source']!=name]+[{'entry':entry,'source':name,'adapter':kind,'daily_enabled':True,'scope_note':note}];selected.append(name)
 selected+=['fred_alfred_series_and_vintages','south_korea_fss_opendart']
 p.write_text(json.dumps(plan,indent=2)+'\n');rp.write_text(json.dumps(routes,indent=2)+'\n');dp.write_text(json.dumps(definitions,indent=2)+'\n')
 p=ROOT/'config/specialist-inputs.json';daily=json.loads(p.read_text());daily['sources']=[s for s in daily['sources'] if s['source'] not in selected]+[{**s,'execution_lane':'independent_public_daily'} for s in plan['sources'] if s['source'] in selected];p.write_text(json.dumps(daily,indent=2)+'\n')
 (ROOT/'constellation/credential-rollout/selected-sources.json').write_text(json.dumps(selected,indent=2)+'\n');print(json.dumps({'registered':selected,'wto_indicators':len(indicators)}))
if __name__=='__main__':main()
