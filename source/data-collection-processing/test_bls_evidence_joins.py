import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from collection_storage import LocalStore
from bls_evidence_joins import COMP,archive_index,compensation_join,assess_exposure,publication_join,cached

class Joins(unittest.TestCase):
 def client(self,path):
  client=SimpleNamespace(store=LocalStore(path),evidence=[])
  client.save=lambda raw,url,media:client.evidence.append({'source_url':url,'body_sha256':__import__('hashlib').sha256(raw).hexdigest()})
  return client
 def test_archive_labels_and_date(self):
  raw=b'<a href="/news.release/archives/empsit_01052024.htm">December 2023 Employment Situation</a>'
  result=archive_index(raw)
  self.assertEqual(result['2023-12']['first_release_date'],'2024-01-05')
 def test_original_release_kept_separate_from_api_value(self):
  with tempfile.TemporaryDirectory() as path:
   client=self.client(path)
   entry={'url':'https://www.bls.gov/news.release/archives/empsit_01052024.htm','first_release_date':'2024-01-05'}
   vintage={'status':'recovered','value':'33.25','official_published_at':'2024-01-05T13:30:00Z'}
   with patch('bls_evidence_joins.release_index',return_value={'periods':{'2023-12':entry}}),patch('bls_evidence_joins.archived_values',return_value=vintage):
    out=publication_join(client,{'year':'2023','period':'M12','value':'33.23'})
   self.assertEqual(out['status'],'joined');self.assertFalse(out['saved_value_matches_original'])
   self.assertIsNone(out['current_saved_value_published_at']);self.assertFalse(out['point_in_time_eligible'])
 def test_documented_cancelled_release_is_not_an_invented_date(self):
  with patch('bls_evidence_joins.release_index',return_value={'periods':{},'not_published':{'2025-10':'official archive note'}}):
   result=publication_join(None,{'year':'2025','period':'M10','value':'35'})
  self.assertEqual(result['status'],'documented_no_separate_release')
 def test_quarterly_costs_are_not_monthly_wage_multiplier(self):
  values=['170','175','48.62','32.50','16.12']
  data={'status':'checked','retrieved_at':'2026-10-18T00:00:00Z','series':{s:[{'year':'2026','period':'Q02','value':v}] for s,v in zip(COMP,values)}}
  with patch('bls_evidence_joins.compensation_history',return_value=data):
   out=compensation_join(None,{'year':'2026','period':'M06'})
   future=compensation_join(None,{'year':'2026','period':'M09'})
  self.assertEqual(out['status'],'joined');self.assertEqual(out['reference_quarter'],'Q02')
  self.assertTrue(out['reconciliation']['reconciled']);self.assertIsNone(out['company_fully_loaded_cost'])
  self.assertFalse(out['point_in_time_eligible']);self.assertEqual(future['status'],'quarter_not_yet_available')
 def test_headquarters_and_relationship_territory_are_not_factory_evidence(self):
  directory={'companies':[{'company_id':'c','review_status':'verified','domicile_country':'US'}],
    'products':[{'product_id':'p','review_status':'verified','sector_id':'semiconductors','attributes':{}}],
    'relationships':[{'company_id':'c','product_id':'p','relationship_id':1,'review_status':'verified','role':'manufacturer','territory':'US','evidence':[{'url':'https://example.com'}]}]}
  out=assess_exposure(directory);self.assertEqual(out['company_links'],[]);self.assertEqual(len(out['review_candidates']),1)
  directory['products'][0]['attributes']['manufacturing_locations']=[{'country_code':'US','operator_company_id':'c','review_status':'verified','evidence':[{'url':'https://example.com/factory'}]}]
  out=assess_exposure(directory);self.assertEqual(len(out['company_links']),1)
  self.assertFalse(out['company_links'][0]['historical_exposure_eligible'])
 def test_empty_rds_is_explicit(self):
  out=assess_exposure({});self.assertEqual(out['company_count'],0);self.assertEqual(out['company_links'],[])
 def test_cache_replays_evidence_without_refetching(self):
  with tempfile.TemporaryDirectory() as d:
   c=self.client(d);calls=[]
   def build():calls.append(1);c.evidence.append({'key':'source'});return {'status':'checked'}
   cached(c,'test',build);c.evidence.clear();cached(c,'test',build)
   self.assertEqual(c.evidence,[{'key':'source'}]);self.assertEqual(len(calls),1)
 def test_all_bootstrap_vintages_have_supported_dates_and_tables(self):
  root=Path(__file__).parent
  data=json.loads((root/'config/bls-release-vintages.json').read_text())['periods']
  self.assertEqual(len(data),68)
  for p,r in data.items():
   self.assertEqual(r['official_published_at'][:10],r['first_release_date'])
   self.assertIn('Manufacturing',r['source_excerpt']);self.assertEqual(r['table'],'B-3')
  self.assertEqual(data['2023-12']['value'],'33.25')
  self.assertEqual(data['2023-12']['official_published_at'],'2024-01-05T13:30:00Z')
if __name__=='__main__':unittest.main()

class BackfillEvidence(unittest.TestCase):
 def test_original_value_and_all_evidence_are_retained(self):
  import bls_enrichment_backfill as b
  row={'series':'CES3000000003','year':'2023','period':'M12','value':'33.23','footnotes':[{}]}
  parent={'payload':{'data':copy.deepcopy(row),'source_evidence':[{'key':'original','sha256':'a'}]},'ingested_at':'2026-10-09T00:00:00Z'}
  with tempfile.TemporaryDirectory() as d,b.registry(Path(d)/'test.sqlite') as db:
   client=SimpleNamespace(evidence=[])
   def join(c,r,e):
    c.evidence.append({'key':'join','sha256':'b'});e['join_status']='assessed';e['evidence_joins']={'publication':{'status':'joined'}}
   with patch('bls_enrichment.history',return_value={'CES3000000003':{'2023-12':{'value':'33.25'}}}),patch('bls_evidence_joins.add_joins',side_effect=join):
    payload,status=b.source_enrichment(parent,client,db)
   self.assertEqual(payload['data']['value'],'33.23');self.assertEqual(status,'enriched')
   self.assertEqual({e['key'] for e in payload['source_evidence']},{'original','join'})
   self.assertEqual(parent['payload']['data'],row)
 def test_pending_join_cannot_complete_backfill(self):
  import bls_enrichment_backfill as b
  parent={'payload':{'data':{'series':'CES3000000003','year':'2023','period':'M12','value':'33.23'}},'ingested_at':'2026-10-09T00:00:00Z'}
  with tempfile.TemporaryDirectory() as d,b.registry(Path(d)/'test.sqlite') as db:
   with patch('bls_enrichment.history',return_value={'CES3000000003':{}}),patch('bls_evidence_joins.add_joins',side_effect=lambda c,r,e:e.update(join_status='retry_pending')):
    with self.assertRaisesRegex(Exception,'bls_evidence_joins_retry_pending'):
     b.source_enrichment(parent,SimpleNamespace(evidence=[]),db)
