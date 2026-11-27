import unittest,json
from monitoring_overview import overview,sms_delivery_confirmed
from collection_alerts import stamp
class OverviewTests(unittest.TestCase):
 def test_grouping_and_recent_retry(self):
  now=1800000000
  def item(unit,code,age):return {'unit':unit,'code':code,'severity':'low','first_seen':stamp(now-age),'detail':code}
  active={'a':item('market','unresolved_market_coverage',100),'b':item('market','market_empty_price_window_unverified',100),'c':item('api','source_http_429',60)}
  subject,body=overview(active,now,stamp(now))
  self.assertIn('2 data gap groups need attention',subject)
  self.assertIn('OTHER COVERAGE GAPS',body)
  self.assertNotIn('[source_http_429]',body)
  active['c']['first_seen']=stamp(now-7*3600)
  self.assertIn('1 service and 2 data gap groups need attention',overview(active,now,stamp(now))[0])
 def test_critical_is_never_delayed(self):
  now=1800000000
  subject,body=overview({'x':{'unit':'publication','code':'oom_kill','severity':'high','first_seen':stamp(now)}},now,stamp(now))
  self.assertIn('URGENT publication [oom_kill]',body)
 def test_idle_sms_alarm_not_delivery_success(self):
  self.assertFalse(sms_delivery_confirmed({'StateValue':'OK','StateReasonData':'{"evaluatedDatapoints":[]}'}))
  self.assertTrue(sms_delivery_confirmed({'StateValue':'OK','StateReasonData':json.dumps({'evaluatedDatapoints':[{'value':1,'sampleCount':1}]})}))
 def test_only_open_issues_and_short_fixes(self):
  now=1800000000
  active={'x':{'unit':'optima-specialist-daily.service','code':'eia_html_instead_of_xlsx','severity':'low','first_seen':stamp(now)}}
  snapshot={'checked_at':stamp(now),'jobs':{'publisher':{'activity':'queued','publication_backlog':{'market':304}}},'daily_audit':{'checked_at':stamp(now-27*3600),'observations':12664762,'partitions':68,'shared_readbacks_passed':68},'pipeline_stages':{'tft':{'label':'TFT training','status':'awaiting_setup','jobs':{},'receipts':[]}}}
  body=overview(active,now,stamp(now),snapshot)[1]
  self.assertIn('Update the EIA workbook URL or adapter',body)
  for noise in ('1. Find the EIA', 'journalctl', '68/68 passed', 'market: 304', 'TFT training'):
   self.assertNotIn(noise,body)

 def test_blockers_and_daily_gaps_with_pauses(self):
  now=1800000000
  blocker={'source':'openalex_scholarly_graph','label':'OpenAlex','issue':'Provider access is pending.',
           'fix':'Configure an API key and validate a historical collector.'}
  snapshot={'historical_capture_blockers':[blocker,dict(blocker,source='paused',label='Paused source')],
            'paused_sources':['paused'],
            'jobs':{'core':{'daily_reconciliation_gaps':[{'source':'documents','dates':['2026-10-14'],
                                                       'reason':'prerequisite_incomplete'}]}}}
  subject,body=overview({},now,stamp(now),snapshot)
  self.assertIn('2 data gap groups need attention',subject)
  self.assertIn('OpenAlex — Provider access is pending.',body)
  self.assertIn('Configure an API key',body)
  self.assertIn('Complete the upstream inventory or document window',body)
  self.assertNotIn('Paused source',body)

class ScheduledBatchOverviewTests(unittest.TestCase):
 def test_sleep_is_explicit_and_not_live_health(self):
  now=1800000000
  snapshot={'checked_at':stamp(now),'jobs':{'worker':{'activity':'scheduled_wait','scheduled_batch_wait':{'queued_requests':27,'earliest_wake_at_epoch':now+3600,'wake_deadline_epoch':now+7200},'progress':{'pending':True}}}}
  _,body=overview({},now,stamp(now),snapshot)
  self.assertIn('No unresolved action items',body)
  self.assertNotIn('27 durable requests',body)
