import json,tempfile,unittest
from collection_storage import LocalStore
from research_contract import digest
from repair_scope import save_report

class RepairReportTests(unittest.TestCase):
 def test_repeat_repair_updates_latest_and_retains_both_attempts(self):
  with tempfile.TemporaryDirectory() as directory:
   store=LocalStore(directory)
   first={'capture':{'status':'failed'}};second={'capture':{'status':'complete'}}
   save_report(store,'scope',first);save_report(store,'scope',second);save_report(store,'scope',second)
   self.assertEqual(json.loads(store.get('operations/repairs/2026-10-21/scope.json').body),second)
   for report in [first,second]:
    self.assertEqual(json.loads(store.get('operations/repairs/2026-10-21/attempts/scope/'+digest(report)+'.json').body),report)
if __name__=='__main__':unittest.main()
