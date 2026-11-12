import unittest
from bls_enrichment import enrich,period,number
class BLS(unittest.TestCase):
 def test_changes_and_footnotes(self):
  row={'year':'2023','period':'M12','value':'33.23','footnotes':[{}, {'code':'P','text':'preliminary'}]}
  hist={'CES3000000003':{'2023-11':{'value':'33.00'},'2022-12':{'value':'30.00'}}}
  x=enrich(row,'CES3000000003',hist)
  self.assertEqual(x['changes']['month_over_month']['absolute_change'],'0.23')
  self.assertTrue(x['quality']['preliminary']);self.assertEqual(len(x['quality']['footnotes']),1)
  self.assertIsNone(x['timing']['official_published_at']);self.assertFalse(x['timing']['point_in_time_eligible'])
 def test_annual_no_monthly_math(self):
  x=enrich({'year':'2023','period':'M13','value':'33','footnotes':[{}]},'CES3000000003',{})
  self.assertEqual(x['reference_period'],'2023-annual');self.assertEqual(x['changes'],{})
 def test_missing_baseline(self):
  x=enrich({'year':'2023','period':'M01','value':'33'},'CES3000000003',{})
  self.assertIsNone(x['changes']['year_over_year']['percent_change'])
 def test_invalid(self):
  self.assertIsNone(number('NaN'))
  with self.assertRaises(Exception):period({'year':'2023','period':'M00'})
 def test_observed_revisions_and_repeated_fetch(self):
  import tempfile
  from types import SimpleNamespace
  from collection_storage import LocalStore
  from bls_enrichment import track_observation
  with tempfile.TemporaryDirectory() as d:
   client=SimpleNamespace(store=LocalStore(d),evidence=[{'key':'original'}])
   row={'year':'2023','period':'M12','value':'33.23'}
   first=enrich(row,'CES3000000003',{});track_observation(client,'CES3000000003',row,first)
   self.assertEqual(first['observed_change']['kind'],'first_observed')
   again=enrich(row,'CES3000000003',{});track_observation(client,'CES3000000003',row,again)
   self.assertEqual(again['observed_change']['kind'],'unchanged')
   changed={**row,'value':'33.24'};e=enrich(changed,'CES3000000003',{})
   track_observation(client,'CES3000000003',changed,e)
   self.assertEqual(e['observed_change']['kind'],'value_revision')
   self.assertEqual(e['observed_change']['previous_observation']['row']['value'],'33.23')
 def test_email_waits_for_publication(self):
  from unittest.mock import Mock,patch
  from bls_enrichment_backfill import notify_when_verified
  sns=Mock();state={'remaining_batches':0,'pending_versions':0}
  with patch('bls_enrichment_backfill.publication_ready',return_value=False):
   result=notify_when_verified(Mock(),Mock(),{},sns,state,'unused',Mock())
  self.assertEqual(result['status'],'awaiting_athena_publication');sns.publish.assert_not_called()
if __name__=='__main__':unittest.main()
