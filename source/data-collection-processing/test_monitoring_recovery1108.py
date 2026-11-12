import copy
import unittest
from collection_alerts import evaluate, stamp
from test_collection_alerts import CONFIG, UNIT, NOW, health

class Recovery(unittest.TestCase):
 def prior(self,unit,code):
  return {'active':{unit+':'+code:{'unit':unit,'code':code,'severity':'low','detail':'old','evidence_at':stamp(NOW-3600)}}}
 def test_empty_queue_requires_verified_receipt_and_no_pending(self):
  c=copy.deepcopy(CONFIG);c['jobs'][UNIT]['publication_owners']=['conferences']
  h=health(progress={'token':'old','pending':False,'last_verified_at':stamp(NOW-7200)})
  p=self.prior(UNIT,'progress_stalled')
  self.assertTrue(evaluate(h,p,c,NOW)[0])
  h['jobs'][UNIT]['publication_queue_drained']={'owners':['conferences'],'verified_receipts':['receipt'],'checked_at':stamp(NOW)}
  self.assertFalse(evaluate(h,p,c,NOW)[0])
  h['jobs'][UNIT]['progress']['pending']=True
  self.assertTrue(evaluate(h,p,c,NOW)[0])
 def test_audit_success_requires_fresh_clean_query_evidence(self):
  unit='optima-daily-health-audit.service';c=copy.deepcopy(CONFIG);c['jobs'][unit]=c['jobs'].pop(UNIT)
  h=health(progress={'pending':False});h['jobs'][unit]=h['jobs'].pop(UNIT)
  p=self.prior(unit,'service_failed')
  for audit in ({},{'checked_at':stamp(NOW),'queries':0},{'checked_at':stamp(NOW),'queries':3,'query_failures':[{}]}, {'checked_at':stamp(NOW-7200),'queries':3}):
   h['daily_audit']=audit;self.assertTrue(evaluate(h,p,c,NOW)[0])
  h['daily_audit']={'checked_at':stamp(NOW-60),'queries':3,'query_failures':[],'s3_failures':[],'receipt_query_failures':[]}
  self.assertFalse(evaluate(h,p,c,NOW)[0])

class ExporterRecovery(unittest.TestCase):
 def test_drained_marker_requires_receipt_verification(self):
  from unittest.mock import Mock,patch
  from collection_health_exporter import inspect_job
  e=Mock();e.inventory.side_effect=lambda key: {'operations/conferences/publication-receipts/a.json':{'LastModified':10,'ETag':'a'}} if 'receipts' in key else {}
  e.read.return_value=({'verification_key':'v'},None,10)
  for verified in ([],[('v',stamp(NOW-7200))]):
   e.confirmed.side_effect=lambda doc: verified if doc else []
   with patch('collection_health_exporter.properties',return_value={}),patch('collection_health_exporter.activity',return_value=('idle',0)),patch('collection_health_exporter.json_reports',return_value=([],[],None)):
    result=inspect_job('example.service',{'publication_owners':['conferences']},e,NOW-3600,NOW)
   self.assertEqual('publication_queue_drained' in result,bool(verified))
