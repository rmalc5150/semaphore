import unittest
from reconcile_coverage import missing_intervals
class CoverageGapsTest(unittest.TestCase):
 def test_overlap_clipping_and_holes(self):
  self.assertEqual(missing_intervals('2021-01-01T00:00:00Z','2021-01-10T00:00:00Z',[
   ('2020-01-01T00:00:00Z','2021-01-03T00:00:00Z'),('2021-01-02T00:00:00Z','2021-01-05T00:00:00Z'),
   ('2021-01-07T00:00:00Z','2022-01-01T00:00:00Z')]),[['2021-01-05T00:00:00Z','2021-01-07T00:00:00Z']])
 def test_empty_and_timezone(self):
  self.assertEqual(missing_intervals('2021-01-01T00:00:00Z','2021-01-02T00:00:00Z',[]),[['2021-01-01T00:00:00Z','2021-01-02T00:00:00Z']])
  self.assertEqual(missing_intervals('2021-01-01T00:00:00Z','2021-01-02T00:00:00Z',[('2021-01-01T08:00:00+08:00','2021-01-02T08:00:00+08:00')]),[])
if __name__=='__main__':unittest.main()
