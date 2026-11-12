from datetime import date
import json
from test_market_collection import MarketTests
from research_contract import canonical_json,validate_record
from market_collection import collect_eodhd
from market_symbol_mappings import segments,validate

class MappingTests(MarketTests):
 def mapping(self):
  return {'symbol':'OLD.US','target_symbol':'NEW.US','start':'2021-01-15','end_exclusive':None,'listing_ids':[],
          'reviewer':'test','explanation':'Same security symbol change','evidence':[{'key':'proof','sha256':'0'*64,'source_url':'https://issuer.test/notice'}]}
 def run_mapping(self,empty=False):
  def get(path,params):
   self.calls.append((path,params))
   if path.startswith('eod/'):
    day='2021-01-04' if path.endswith('OLD.US') else '2021-01-19'
    rows=[] if empty and path.endswith('NEW.US') else [{'date':day,'open':10,'high':12,'low':9,'close':11,'adjusted_close':11,'volume':100}]
   else:rows=[]
   return rows,canonical_json(rows),'https://example.org/'+path
  self.client.get.side_effect=get
  return collect_eodhd(self.store,self.settings,self.u,self.t,'OLD.US',date(2021,1,1),date(2021,2,1),'historical',self.client,symbol_mapping=self.mapping())
 def test_mapping_splits_dates_and_preserves_provider_evidence(self):
  result=self.run_mapping();self.assertEqual(result['status'],'complete',result)
  self.assertEqual(self.calls[0],('eod/OLD.US',{'from':'2021-01-01','to':'2021-01-14','order':'a'}))
  self.assertEqual(self.calls[1],('eod/NEW.US',{'from':'2021-01-15','to':'2021-01-31','order':'a'}))
  m=json.loads(self.store.get(result['manifest']).body)
  records=[json.loads(line) for page in m['pages'] for b in page['batches'] for line in self.store.get(b['key']).body.splitlines()]
  self.assertEqual([r['payload']['provider_symbol']for r in records],['OLD.US','NEW.US'])
  self.assertTrue(all(r['payload']['symbol']=='OLD.US'for r in records))
  self.assertTrue(records[1]['source_url'].endswith('NEW.US'))
  for r in records:self.assertEqual(validate_record(r,self.u),[])
 def test_empty_new_segment_cannot_mark_year_complete(self):
  self.assertEqual(self.run_mapping(empty=True)['reason'],'market_empty_price_window_unverified')
 def test_cross_exchange_mapping_rejected(self):
  d=self.mapping();d['target_symbol']='NEW.TO'
  with self.assertRaises(ValueError):validate(d,'OLD.US',[])
 def test_prechange_window_uses_original_symbol(self):
  self.assertEqual(segments('OLD.US',date(2021,1,1),date(2021,1,10),self.mapping()),[('OLD.US',date(2021,1,1),date(2021,1,10))])
 def test_mapping_expiry_restores_original_route(self):
  d=self.mapping();d['end_exclusive']='2021-01-20'
  self.assertEqual([s for s,_,_ in segments('OLD.US',date(2021,1,1),date(2021,2,1),d)],['OLD.US','NEW.US','OLD.US'])
