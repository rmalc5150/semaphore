import unittest,json
from monitoring_overview import overview,sms_delivery_confirmed
from collection_alerts import stamp
class OverviewTests(unittest.TestCase):
 def test_grouping_and_recent_retry(self):
  now=1800000000
  def item(unit,code,age):return {'unit':unit,'code':code,'severity':'low','first_seen':stamp(now-age),'detail':code}
  active={'a':item('market','unresolved_market_coverage',100),'b':item('market','market_empty_price_window_unverified',100),'c':item('api','source_http_429',60)}
  subject,body=overview(active,now,stamp(now))
  self.assertIn('1 services need attention',subject)
  self.assertEqual(body.count('market —'),1)
  self.assertIn('1 services have recent retryable issues',body)
  active['c']['first_seen']=stamp(now-7*3600)
  self.assertIn('2 services need attention',overview(active,now,stamp(now))[0])
 def test_critical_is_never_delayed(self):
  now=1800000000
  subject,body=overview({'x':{'unit':'publication','code':'oom_kill','severity':'high','first_seen':stamp(now)}},now,stamp(now))
  self.assertIn('URGENT REPAIR',body)
 def test_idle_sms_alarm_not_delivery_success(self):
  self.assertFalse(sms_delivery_confirmed({'StateValue':'OK','StateReasonData':'{"evaluatedDatapoints":[]}'}))
  self.assertTrue(sms_delivery_confirmed({'StateValue':'OK','StateReasonData':json.dumps({'evaluatedDatapoints':[{'value':1,'sampleCount':1}]})}))
 def test_live_report_steps_backlog_and_stale_audit(self):
  now=1800000000
  active={'x':{'unit':'optima-specialist-daily.service','code':'eia_html_instead_of_xlsx','severity':'low','first_seen':stamp(now)}}
  snapshot={'checked_at':stamp(now),'jobs':{'publisher':{'activity':'queued','publication_backlog':{'market':304}}},'daily_audit':{'checked_at':stamp(now-27*3600),'observations':12664762,'partitions':68,'shared_readbacks_passed':68},'pipeline_stages':{'tft':{'label':'TFT training','status':'awaiting_setup','jobs':{},'receipts':[]}}}
  body=overview(active,now,stamp(now),snapshot)[1]
  self.assertIn('1. Find the EIA',body)
  self.assertIn('68/68 passed',body)
  self.assertIn('STALE',body)
  self.assertIn('market: 304',body)
  self.assertIn('TFT training: awaiting_setup',body)
