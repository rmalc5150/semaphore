import json,unittest
from datetime import date
from unittest.mock import Mock,patch
import fda_review_capture as worker
class Capture(unittest.TestCase):
 def test_probe_dates_are_real_single_day_windows(self):
  plan={'sources':[{'source':'fda_dd_compliance_actions','source_id':'S35','adapter':'fda_dashboard','api':'https://api-datadashboard.fda.gov/v1/compliance_actions','date_field':'ActionTakenDate','coverage_note':'scope'},{'source':'fda_product_codes','source_id':'S35','adapter':'fda_productcodes','api':'https://www.accessdata.fda.gov/rest/pcbapi/v1/industry/','coverage_note':'industry only'}]}
  jobs=worker.plan_jobs(plan,{},date(2026,11,11),True);self.assertEqual(jobs[0]['start'],'2026-07-27');self.assertEqual(jobs[0]['end'],'2026-07-28');self.assertEqual(jobs[1]['mode'],'daily')
 def test_default_capture_leaves_historical_routes_independent(self):
  with patch.object(worker,'jobs',return_value=[])as jobs:worker.plan_jobs({}, {},date(2026,11,11))
  self.assertEqual(jobs.call_args.args[2],'daily');self.assertEqual(jobs.call_count,1)
 def test_failure_is_logged_with_bounded_cooldown(self):
  with patch.object(worker,'deadline'),patch.object(worker,'collect',side_effect=RuntimeError('unavailable')),patch.object(worker,'write_json'),patch.object(worker,'queue_metadata')as queue:
   result=worker.capture_one(Mock(),Mock(),{}, {},{'source':'fda_dd_import_refusals'})
  self.assertEqual(result['status'],'failed');queue.assert_not_called();self.assertGreater(result['retry_after'],0)
 def test_partial_committed_data_can_enter_metadata_without_complete_window_claim(self):
  store=Mock();store.get.return_value=Mock(body=json.dumps({'task':{'source':'fda_dd_import_refusals'},'status':'partial','exhausted':False}))
  with patch.object(worker,'deadline'),patch.object(worker,'collect',return_value={'status':'partial','manifest':'m'}),patch.object(worker,'write_json')as put,patch.object(worker,'queue_metadata')as queue:
   result=worker.capture_one(store,Mock(),{}, {},{'source':'fda_dd_import_refusals'})
  self.assertEqual(result['status'],'partial');self.assertNotIn('window_id',result);queue.assert_called_once();self.assertEqual(put.call_count,1)
