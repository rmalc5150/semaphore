import copy,json,unittest
from metadata_engine.sam_opportunities import validate
from metadata_engine.evidence import RawFailure
class SAM(unittest.TestCase):
 def fixture(self):
  data={'noticeId':'n1','postedDate':'2026-11-01','title':'Supply notice','description':'https://api.sam.gov/description/n1'}
  return json.dumps({'opportunitiesData':[copy.deepcopy(data)],'totalRecords':1}).encode(),{'source_record_id':'n1','event_at':{'value':'2026-11-01'},'payload':{'data':data}},'https://api.sam.gov/opportunities/v2/search?postedFrom=11%2F01%2F2026&postedTo=11%2F02%2F2026'
 def test_non_award_notice_is_valid_notice_metadata(self):self.assertEqual(validate(*self.fixture())['record_type'],'opportunity_notice_metadata')
 def test_changed_notice_rejected(self):
  body,row,url=self.fixture();row['payload']['data']['title']='Changed'
  with self.assertRaises(RawFailure):validate(body,row,url)
 def test_wrong_posted_window_rejected(self):
  body,row,url=self.fixture()
  with self.assertRaises(RawFailure):validate(body,row,url.replace('11%2F01','11%2F02'))
if __name__=='__main__':unittest.main()
