import unittest
from constellation.gaps import merged_gaps
from monitoring_overview import overview

class GapTests(unittest.TestCase):
    def window(self,start,end,scope='provider|dataset|global',status='partial',at=1):
        return {'scope':scope,'start':start,'end':end,'status':status,'reason':'missing','updated_at':at,'evidence_uri':'s3://evidence'}
    def test_threshold_and_adjacent_intervals(self):
        w=[self.window('2016-01-01','2016-01-04'),self.window('2016-01-04','2016-01-06')]
        gap=merged_gaps(w)[0];self.assertEqual(gap['duration_days'],5);self.assertFalse(gap['flag_for_checkup'])
        w.append(self.window('2016-01-06','2016-01-07'))
        self.assertTrue(merged_gaps(w)[0]['flag_for_checkup'])
    def test_different_scope_and_successful_repair(self):
        w=[self.window('2016-01-01','2016-01-05'),self.window('2016-01-05','2016-01-09',scope='other')]
        self.assertEqual(len(merged_gaps(w)),2)
        w.append(self.window('2016-01-01','2016-01-05',status='succeeded',at=2))
        self.assertEqual(len(merged_gaps(w)),1)
    def test_email_flags_only_long_gaps(self):
        gaps=merged_gaps([self.window('2016-01-01','2016-01-06'),self.window('2016-02-01','2016-02-07',scope='other')])
        snap={'historical_gaps':{'checked_at':'2026-10-26T08:00:00Z','gaps':gaps,'flagged_gaps':1,'record_only_gaps':1}}
        subject,body=overview({},1793001600,'2026-10-25',snap)
        self.assertIn('0 services need attention',subject)
        self.assertIn('1 historical scopes need review',subject)
        self.assertNotIn('journalctl -u constellation-history/',body)
        self.assertIn('constellation-history/other',body)
        self.assertNotIn('constellation-history/provider',body)
        self.assertIn('five days or less are recorded without flags',body)
    def test_active_bounded_window_is_backlog_not_gap(self):
        self.assertEqual(merged_gaps([self.window('2016-01-01','2016-02-01',status='in_progress')]),[])

    def test_empty_day_is_not_missing(self):
        self.assertEqual(merged_gaps([self.window('2016-01-01','2016-01-02',status='succeeded')]),[])

if __name__=='__main__':unittest.main()
