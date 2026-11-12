import copy,json,unittest
from datetime import date
from unittest.mock import Mock
from specialist_plan import jobs
from specialist_public_apis import fetch
from specialist_inputs import item
from metadata_engine.openfda import validate,ProviderError
class DrugsFDA(unittest.TestCase):
 def test_complete_application_validation(self):
  app={'application_number':'NDA017398','products':[{'product_number':'001','brand_name':'Example'}],'submissions':[]};r={'source':'drugsfda_applications','source_record_id':'NDA017398','source_url':'https://api.fda.gov/drug/drugsfda.json','payload':{'data':copy.deepcopy(app)}};u=r['source_url'];self.assertEqual(validate(json.dumps({'results':[app]}).encode(),r,u)['product_count'],1)
  r['payload']['data']['products'][0]['brand_name']='Wrong'
  with self.assertRaises(ProviderError):validate(json.dumps({'results':[app]}).encode(),r,u)
 def test_all_application_inventory_not_company_scoped(self):
  plan={'historical_start':'2016-01-01','backfill_end_exclusive':'2026-10-26','sources':[{'source_id':'S20','source':'drugsfda_applications','adapter':'drugsfda','api':'https://api.fda.gov/drug/drugsfda.json','enabled':True,'historical':True,'full_inventory':True}]};universe={'companies':[]};out=list(jobs(plan,universe,'daily',date(2026,11,10)));snap=[j for j in out if j['parameters'].get('inventory_scope')];self.assertEqual(len(snap),31);self.assertEqual(len(out),32)
  self.assertEqual({j['start']for j in snap},{'2026-11-09'});self.assertTrue(all('submission_status_date'not in j['parameters']['query']['search']for j in snap));self.assertIn('other_application_ids',{j['parameters']['partition']for j in snap})
  again=[j for j in jobs(plan,universe,'daily',date(2026,11,11))if j['parameters'].get('inventory_scope')];self.assertEqual(snap,again)
 def test_inventory_revisions_cannot_mix(self):
  job={'adapter':'drugsfda','parameters':{'url':'https://api.fda.gov/drug/drugsfda.json','query':{},'inventory_scope':'all_provider_applications'}};row={'application_number':'NDA017398'};client=Mock();client.json.return_value={'meta':{'last_updated':'2026-11-01','results':{'total':2}},'results':[row]};_,cursor=fetch(client,job,None,item)
  client.json.return_value={'meta':{'last_updated':'2026-11-02','results':{'total':2}},'results':[row]}
  with self.assertRaisesRegex(Exception,'source_changed_refresh_required'):fetch(client,job,cursor,item)
 def test_private_queue_bridge_is_idempotent_and_isolates_bad_entries(self):
  import tempfile
  from collection_storage import LocalStore,StorageSettings,write_json
  from specialist_publication import bridge_drugsfda_inventory
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);cfg=StorageSettings(local_root=tmp)
   write_json(store,'constellation-backfill/specialist-publication-queue/drugsfda-inventory/one.json',{'window_id':'one','manifests':['original']})
   write_json(store,'constellation-backfill/specialist-publication-queue/drugsfda-inventory/bad.json',{'missing':'window'})
   self.assertEqual(bridge_drugsfda_inventory(store,cfg),1);self.assertEqual(bridge_drugsfda_inventory(store,cfg),0)
   self.assertIsNotNone(store.get('operations/specialists/publication-queue/one.json'))

if __name__=='__main__':unittest.main()
