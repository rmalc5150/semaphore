"""Bounded PubMed current-record verification through the native capture path."""
import json
from datetime import datetime,timedelta,timezone
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import collect

def main():
 day=datetime.now(timezone.utc).date();job={'source':'pubmed_abstracts','source_id':'S27','adapter':'pubmed','mode':'daily','start':day.isoformat(),'end':(day+timedelta(days=1)).isoformat(),'parameters':{'url':'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi','query':{'term':'35129803[uid]'}},'coverage_note':'Current original PubMed citation/abstract for one explicitly selected PMID; not complete recent-topic, date-window or archive coverage.'}
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');result=collect(job,store,settings,universe,load_json(ROOT/'config/sectors.v1.json'),1)
 report={'source':'pubmed_abstracts','at':now(),**result}
 if result.get('manifest'):
  manifest=json.loads(store.get(result['manifest']).body);report['records']=manifest['record_count'];report['window_id']=digest({'job':job,'universe':digest(universe)})
 write_json(store,'constellation-backfill/legacy-operation-receipts/pubmed-verified-capture/'+day.isoformat()+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
 if result['status']!='complete' or report.get('records')!=1:raise SystemExit(2)
if __name__=='__main__':main()
