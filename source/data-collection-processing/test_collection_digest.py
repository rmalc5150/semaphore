import unittest,copy
from test_collection_alerts import FakeS3,FakeSNS,CONFIG,NOW,UNIT,health
from collection_alerts import Watchdog,stamp,evaluate

class DigestTests(unittest.TestCase):
    def setUp(self):
        self.sns=FakeSNS();cfg=copy.deepcopy(CONFIG);cfg['email_digest_seconds']=86400
        self.w=Watchdog(FakeS3(),self.sns,cfg)
    def check(self,at,**changes):
        h=health(**changes);h['checked_at']=stamp(at);h['jobs'][UNIT]['progress']['last_verified_at']=stamp(at)
        self.w.put('health/latest.json',h);return self.w.run(at)
    def test_many_errors_one_email_at_24_hours(self):
        self.check(NOW,timer_state='inactive',result='failed')
        self.check(NOW+1800,timer_state='inactive',result='failed')
        self.assertEqual(self.sns.messages,[])
        self.check(NOW+43200,timer_state='inactive',result='failed')
        self.assertEqual(self.sns.messages,[])
        self.check(NOW+86400,timer_state='inactive',result='failed')
        self.assertEqual(len(self.sns.messages),1)
        self.assertIn('24-hour',self.sns.messages[0]['Subject'])
        self.assertIn('timer_disabled',self.sns.messages[0]['Message']);self.assertIn('service_failed',self.sns.messages[0]['Message'])
        self.check(NOW+88200,timer_state='inactive');self.assertEqual(len(self.sns.messages),1)
    def test_recovered_within_period_is_included(self):
        self.check(NOW,timer_state='inactive');self.check(NOW+1800);self.check(NOW+86400)
        self.assertEqual(len(self.sns.messages),1);self.assertNotIn('RECOVERED',self.sns.messages[0]['Message']);self.assertIn('no action items',self.sns.messages[0]['Subject'])
    def test_failed_digest_retained_for_retry(self):
        self.check(NOW,timer_state='inactive');self.sns.fail='email-topic';self.check(NOW+86400)
        self.assertTrue(self.w.get('state/latest.json')['email_digest']['incidents'])
        self.sns.fail=None;self.check(NOW+88200)
        self.assertEqual(len(self.sns.messages),1);self.assertFalse(self.w.get('state/latest.json')['email_digest']['incidents'])
    def test_critical_sms_immediate_email_waits(self):
        self.w.run(NOW)
        self.assertEqual([m['TopicArn'] for m in self.sns.messages],['sms-topic'])
    def test_healthy_period_still_sends_daily_report(self):
        self.check(NOW);self.check(NOW+86400)
        self.assertEqual(len(self.sns.messages),1)
        self.assertIn('COLLECTION STATUS',self.sns.messages[0]['Message'])
        self.check(NOW+88200);self.assertEqual(len(self.sns.messages),1)
    def test_healthy_email_failure_retries(self):
        self.check(NOW);self.sns.fail='email-topic';self.check(NOW+86400)
        self.assertEqual(self.sns.messages,[])
        self.sns.fail=None;self.check(NOW+88200)
        self.assertEqual(len(self.sns.messages),1)
    def test_daily_audit_missing_alert_clears_on_verified_report(self):
        cfg=copy.deepcopy(CONFIG);cfg['daily_health_required']=True
        unit='optima-daily-health-audit.service';cfg['jobs'][unit]=copy.deepcopy(cfg['jobs'][UNIT])
        h=health();h['jobs'][unit]=copy.deepcopy(h['jobs'][UNIT])
        incidents,_=evaluate(h,{},cfg,NOW)
        self.assertIn(unit+':daily_audit_missing_or_stale',incidents)
        h['daily_audit']={'checked_at':stamp(NOW),'query_failures':[],'s3_failures':[],'receipt_query_failures':[]}
        recovered,_=evaluate(h,{'active':incidents},cfg,NOW+60)
        self.assertNotIn(unit+':daily_audit_missing_or_stale',recovered)
    def test_planned_model_stage_does_not_create_false_failure(self):
        h=health();h['pipeline_stages']={'tft':{'status':'awaiting_setup'}}
        self.assertEqual(evaluate(h,{},CONFIG,NOW)[0],{})
        h['pipeline_stages']['tft']['status']='verification_failed'
        self.assertIn('pipeline:tft:pipeline_output_verification_failed',evaluate(h,{},CONFIG,NOW)[0])
if __name__=='__main__':unittest.main()
