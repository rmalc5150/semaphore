import json,unittest
from types import SimpleNamespace
from unittest.mock import Mock
from specialist_inputs import nih_refresh_required
class TedRecovery(unittest.TestCase):
 def check(self,reason='ted_count_mismatch',seen=100,token='old',status='failed'):
  store=Mock();store.get.side_effect=[SimpleNamespace(body=json.dumps({'terminal_manifest':'old.json','cursor':json.dumps({'seen':seen,'token':token})}).encode()),SimpleNamespace(body=json.dumps({'status':status,'reason_code':reason}).encode())]
  return nih_refresh_required(store,{}, {'adapter':'ted'})
 def test_failed_resumed_count_restarts_generation(self):self.assertTrue(self.check())
 def test_missing_page_restarts_generation(self):self.assertTrue(self.check('ted_missing_iteration_page'))
 def test_no_reset_for_first_page_partial_or_other_errors(self):
  self.assertFalse(self.check(seen=0));self.assertFalse(self.check(token=None));self.assertFalse(self.check(status='partial'));self.assertFalse(self.check(reason='source_http_403'))
