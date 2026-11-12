"""Register explicit initial scopes for new APIs; no implied complete-provider coverage."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
 registry=json.loads((ROOT/'config/constellation-source-registry.json').read_text())['sources']
 path=ROOT/'config/constellation-specialist-historical.json';plan=json.loads(path.read_text());routes_path=ROOT/'config/constellation-legacy-routes.json';routes=json.loads(routes_path.read_text());added=[]
 definitions=[
 (66,'fred','https://api.stlouisfed.org/fred/series/observations','Selected macroeconomic series with all available ALFRED realtime intervals since 2016, fixed realtime cutoff; observation periods and vintage intervals are distinct. Initial scope is the configured series list, not the full FRED catalog.'),
 (76,'nasa','https://power.larc.nasa.gov/api/temporal/daily/point','Daily temperature, corrected precipitation and solar radiation for eight named regional reference locations. Current reanalysis retrieval, not original forecast vintages or plant-specific exposure.'),
 (98,'dart','https://opendart.fss.or.kr/api/list.json','All-company monthly filing index including corrections, date and receipt identifiers since 2016; original report downloads and financial-statement extraction are separate.'),
 (143,'datacite','https://api.datacite.org/dois','DOI metadata for dataset, software and dissertation resource-type filters, partitioned by DOI creation month; publication dates, usage and revisions remain distinct; no linked content downloaded.'),
 (145,'biorxiv','https://api.biorxiv.org/details','bioRxiv and medRxiv preprint metadata by posting month and version; initial dates before service operation can have empty queries, not proof of historical public availability. No article bodies are downloaded.'),
 (147,'zenodo','https://zenodo.org/api/records','Public research artifact metadata by publication month, preserving source precision and identifiers. Ten-thousand-result scopes remain blocked for splitting; files and usage vintages are separate.'),
 (156,'huggingface','https://huggingface.co/api','Public model and dataset repository metadata sorted by creation, with dated and undated source fields retained. Current metadata only; no gated content, model weights or private repositories are downloaded.')]
 for n,kind,url,note in definitions:
  entry=registry[n-1];key=entry['source_key'];source={'source_id':f'C{n:03d}','source':key,'adapter':'additional_'+kind,'api':url,'enabled':True,'historical':True,'coverage_note':note}
  if kind=='fred':source['scopes']=[{'series_id':s} for s in ['GDP','GDPC1','INDPRO','UNRATE','CPIAUCSL','CPILFESL','PCEPI','PCEPILFE','FEDFUNDS','DGS10','DGS2','T10Y2Y','PAYEMS','ICSA','HOUST','PERMIT','RSAFS','DTWEXBGS','M2SL','BAA','DCOILWTICO','VIXCLS']]
  if kind=='nasa':source['scopes']=[{'location':name,'latitude':lat,'longitude':lon} for name,lat,lon in [('Phoenix',33.4484,-112.074),('Berlin',52.52,13.405),('Delhi',28.6139,77.209),('Shanghai',31.2304,121.4737),('SaoPaulo',-23.5505,-46.6333),('Johannesburg',-26.2041,28.0473),('Sydney',-33.8688,151.2093),('Tokyo',35.6762,139.6503)]]
  plan['sources']=[s for s in plan['sources'] if s['source']!=key]+[source]
  unit='constellation-specialist-'+key+'.service';template=next(r for r in routes['routes'] if r.get('specialist_source')=='cpsc_recalls');row={**template,'unit':unit,'specialist_source':key,'argv':[*template['argv']],'catalog_entry':n,'validation_basis':'New endpoint-specific adapter with fixed provider host, redacted credentials, source-date checks, explicit pagination, provider total reconciliation where available, and native immutable evidence.'}
  row['argv'][row['argv'].index('--source')+1]=key
  if kind=='huggingface':row['argv'][row['argv'].index('--pages')+1]='50'
  routes['routes']=[r for r in routes['routes'] if r['unit']!=unit]+[row];added.append({'entry':n,'source':key,'adapter':kind,'scope_note':note})
 path.write_text(json.dumps(plan,indent=2)+'\n');routes_path.write_text(json.dumps(routes,indent=2)+'\n');(ROOT/'constellation/expansion/new-adapters.json').write_text(json.dumps(added,indent=2)+'\n');print(json.dumps({'new_provider_integrations':len(added),'entries':[r['entry'] for r in added]}))

if __name__=='__main__':main()
