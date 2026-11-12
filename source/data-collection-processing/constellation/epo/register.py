"""Register EPO OPS for the current Constellation universe; credentials stay in SM."""
import json,hashlib
from pathlib import Path
from constellation.control import Control
ROOT=Path(__file__).resolve().parents[2]
SOURCE='epo_ops_patent_legal_events'
NOTE='Applicant-name and existing-alias candidate discovery for the enabled company universe, including pre-2016 patents; current INPADOC legal histories retain gazette dates since 2016 and undated events. Gazette, effective, created and exchanged dates remain distinct. Applicant links are unreviewed; aliases/subsidiaries and provider omissions can leave gaps. This is not original historical vintages or a calendar-completeness certification. Daily discovery overlaps seven days; known patents rotate through bounded refresh shards.'
def main():
 c=Control();response=c.s3.get_object(Bucket=c.config['bucket'],Key=c.config['legacy_seed_key']);seed=json.loads(response['Body'].read());response['Body'].close();entry=seed['paths']['config/company-universe.v0.5.json'];r=c.s3.get_object(Bucket=c.config['bucket'],Key=entry['key']);body=r['Body'].read();r['Body'].close();assert hashlib.sha256(body).hexdigest()==entry['sha256'];universe=json.loads(body)
 scopes=[]
 aliases={}
 for alias in universe.get('company_aliases',[]):
  if alias.get('review_status')!='rejected':aliases.setdefault(alias['company_id'],set()).add(alias['alias'])
 for company in universe['companies']:
  if not company['collection_enabled']:continue
  name=company['canonical_name'].replace('"',' ').replace('\\',' ').strip()
  if name:
   names=sorted({a.replace('"',' ').replace('\\',' ').strip() for a in aliases.get(company['company_id'],set())|{name} if a.strip()})
   for i in range(0,len(names),8):scopes.append({'applicant':name,'applicant_aliases':names[i:i+8],'company_id':company['company_id']})
 source={'source_id':'C074','source':SOURCE,'adapter':'additional_epo','api':'https://ops.epo.org/3.2/','enabled':True,'historical':True,'coverage_note':NOTE,'scopes':scopes}
 for filename in ('constellation-specialist-historical.json','specialist-inputs.json'):
  p=ROOT/'config'/filename;d=json.loads(p.read_text());d['sources']=[r for r in d['sources'] if r['source']!=SOURCE]+[{**source,**({'execution_lane':'independent_public_daily'} if filename=='specialist-inputs.json' else {})}];p.write_text(json.dumps(d,indent=2)+'\n')
 p=ROOT/'config/constellation-legacy-routes.json';d=json.loads(p.read_text());template=next(r for r in d['routes'] if r.get('specialist_source')=='cpsc_recalls');row={**template,'unit':'constellation-specialist-'+SOURCE+'.service','specialist_source':SOURCE,'argv':list(template['argv']),'catalog_entry':74,'execution_enabled':False,'activation_staged':True,'remaining_requirements':['worker_deployment_verification'],'validation_basis':NOTE}
 row['argv'][row['argv'].index('--source')+1]=SOURCE;row['argv'][row['argv'].index('--max-jobs')+1]='4';row['argv'][row['argv'].index('--pages')+1]='5';d['routes']=[r for r in d['routes'] if r['unit']!=row['unit']]+[row];p.write_text(json.dumps(d,indent=2)+'\n')
 p=ROOT/'constellation/expansion/new-adapters.json';d=json.loads(p.read_text());d=[r for r in d if r['entry']!=74]+[{'entry':74,'source':SOURCE,'adapter':'epo','daily_enabled':False,'scope_note':NOTE}];p.write_text(json.dumps(d,indent=2)+'\n')
 # Publication allowlists retain the new normalized native source.
 p=ROOT/'config/specialist-observations-athena.json'
 if p.exists():
  d=json.loads(p.read_text());d['allowed_sources']=list(dict.fromkeys(d['allowed_sources']+[SOURCE]));p.write_text(json.dumps(d,indent=2)+'\n')
 (ROOT/'constellation/epo/registration.json').write_text(json.dumps({'source':SOURCE,'applicant_query_groups':len(scopes),'companies':len({s['company_id'] for s in scopes}),'universe_sha256':entry['sha256'],'scope_note':NOTE,'historical_unit':row['unit']},indent=2)+'\n');print(json.dumps({'applicant_query_groups':len(scopes),'companies':len({s['company_id'] for s in scopes}),'historical_unit':row['unit']}))
if __name__=='__main__':main()
