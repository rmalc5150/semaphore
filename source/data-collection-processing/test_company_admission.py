import unittest
from company_admission import evaluate
class AdmissionTests(unittest.TestCase):
 def setUp(self):
  self.company={'review_status':'verified','entity_type':'legal_entity','evidence':[{'source':'registry'}],'sectors':[{'sector_id':'robotics','review_status':'verified','evidence':[{'source':'official'}]}]}
  self.ids=[{'system':'lei','value':'test','review_status':'verified'}]
 def test_verified_eligibility_does_not_backdate_activation(self):
  r=evaluate(self.company,self.ids);self.assertEqual(r['eligibility'],'eligible_for_activation');self.assertIsNone(r['activation_at'])
 def test_listing_identity_and_conflict_do_not_admit(self):
  self.assertEqual(evaluate(self.company,[{'system':'isin','review_status':'verified'}])['eligibility'],'review_required')
  self.assertIn('identifier_conflict',evaluate(self.company,self.ids,['collision'])['reasons'])
 def test_sector_labels_and_rejected_identities_do_not_admit(self):
  self.company['sectors'][0]['review_status']='pending';self.assertIn('sector_not_verified',evaluate(self.company,self.ids)['reasons'])
  self.company['review_status']='rejected';self.assertIn('rejected_identity',evaluate(self.company,self.ids)['reasons'])
if __name__=='__main__':unittest.main()
