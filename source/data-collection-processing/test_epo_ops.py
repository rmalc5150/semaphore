import json,unittest
from datetime import date
from unittest.mock import Mock,patch
import xml.etree.ElementTree as ET
from epo_ops import legal_rows,fetch,OPS,EX
from specialist_inputs import item
from additional_source_plan import scopes
from regulatory_collection import SourceIssue

def document(events):
 return ET.fromstring(f'<ops:world-patent-data xmlns:ops="http://ops.epo.org" xmlns="http://www.epo.org/exchange"><ops:patent-family><ops:family-member family-id="1"><publication-reference><document-id document-id-type="docdb"><country>EP</country><doc-number>1</doc-number><kind>A1</kind></document-id></publication-reference>{events}</ops:family-member></ops:patent-family></ops:world-patent-data>')
def event(day,eff='19990101'):
 return f'<ops:legal code="X" desc="test"><ops:L007EP>{day}</ops:L007EP><ops:L525EP>{eff}</ops:L525EP></ops:legal>'
class EPOTests(unittest.TestCase):
 def test_empty_later_search_page_requires_refresh(self):
  cursor=json.dumps({'ranges':[['2016-01-01','2017-01-01']],'offset':26,'total':50,'pending':[]})
  job={'parameters':{'applicant':'ASML','snapshot_end':'2026-10-26'}}
  with patch('epo_ops.xml',return_value=None):
   with self.assertRaisesRegex(SourceIssue,'source_changed_refresh_required'):fetch(Mock(),job,cursor,item)
 def test_oversize_failed_response_still_counts_bytes(self):
  from contextlib import contextmanager
  from epo_ops import response
  q=Mock();r=Mock();r.iter_content.return_value=[b'oversize'];request=Mock();request.__enter__=Mock(return_value=r);request.__exit__=Mock(return_value=False)
  @contextmanager
  def slot():yield q,date(2026,10,26)
  with patch('epo_ops.request_slot',slot),patch('epo_ops.requests.request',return_value=request),patch('epo_ops.MAX_BYTES',2):
   with self.assertRaisesRegex(SourceIssue,'epo_response_too_large'):response('GET','https://ops.epo.org/3.2/rest-services/published-data/search')
  self.assertEqual(q.execute.call_args.args[1][-1],8);q.connection.commit.assert_called_once()
 def test_provider_no_results_is_empty_but_generic_404_is_failure(self):
  from epo_ops import xml
  for message,empty in [('No results found',True),('Invalid endpoint',False)]:
   body=f'<fault xmlns="http://ops.epo.org"><code>SERVER.EntityNotFound</code><message>{message}</message></fault>'.encode()
   with patch('epo_ops.token',return_value='token'),patch('epo_ops.response',return_value=(404,body,{})),patch('additional_source_apis.credentials',return_value={}):
    if empty:self.assertIsNone(xml(Mock(),'rest-services/published-data/search'))
    else:
     with self.assertRaises(SourceIssue):xml(Mock(),'rest-services/published-data/search')
 def test_gazette_dates_and_pre2016_patents(self):
  rows=legal_rows(document(event('2015-12-31')+event('2016-01-01')+event('2026-10-27')), 'EP.1.A1',{'snapshot_end':'2026-10-27'},item)
  self.assertEqual([r['date'] for r in rows],['2016-01-01']);self.assertEqual(rows[0]['data']['effective_date_raw'],'19990101')
 def test_unknown_dates_retained_without_inventing_dates(self):
  rows=legal_rows(document(event('0000-00-00')),'EP.1.A1',{'snapshot_end':'2026-10-27'},item)
  self.assertIsNone(rows[0]['date']);self.assertEqual(rows[0]['data']['date_basis'],'unknown')
 def test_duplicate_xml_events_collapse_but_amendments_remain(self):
  self.assertEqual(len(legal_rows(document(event('2020-01-01')*2+event('2020-01-01','20200102')),'EP.1.A1',{'snapshot_end':'2026-10-27'},item)),2)
 def test_plan_covers_older_patents_and_refreshes_known_patents(self):
  source={'adapter':'additional_epo','api':'https://ops.epo.org/3.2/','coverage_note':'test','scopes':[{'applicant':'ASML'}]}
  history=list(scopes(source,date(2016,1,1),date(2026,10,26),'historical'))
  self.assertEqual(history[0][2]['discovery_start'],'1900-01-01');self.assertEqual(history[0][2]['discovery_end'],'2016-01-01')
  daily=list(scopes(source,date(2016,1,1),date(2026,10,26),'daily'));self.assertEqual(len(daily),17)
  self.assertEqual(daily[0][2]['discovery_start'],'2026-10-19');self.assertEqual(sum(r[2].get('purpose')=='refresh' for r in daily),16)
 def test_search_over_2000_is_split_before_any_patent_is_skipped(self):
  root=ET.fromstring(f'<ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="2001"/></ops:world-patent-data>')
  job={'parameters':{'applicant':'ASML','discovery_start':'2016-01-01','discovery_end':'2017-01-01','snapshot_end':'2026-10-26'}}
  with patch('epo_ops.xml',return_value=root),patch('epo_ops.registry') as register:
   rows,cursor=fetch(Mock(),job,None,item)
  self.assertEqual(rows,[]);state=json.loads(cursor);self.assertEqual(len(state['ranges']),2);self.assertEqual(state['ranges'][0][1],state['ranges'][1][0]);register.assert_not_called()
 def test_failed_patent_does_not_advance_saved_cursor(self):
  cursor=json.dumps({'ranges':[['2016-01-01','2017-01-01']],'offset':2,'total':1,'pending':['EP.1.A1']})
  with patch('epo_ops.xml',side_effect=SourceIssue('source_http_503')),patch('epo_ops.registry') as register:
   with self.assertRaises(SourceIssue):fetch(Mock(),{'parameters':{'snapshot_end':'2026-10-26'}},cursor,item)
  register.assert_not_called();self.assertEqual(json.loads(cursor)['pending'],['EP.1.A1'])
 def test_xml_evidence_redacts_authentication_values(self):
  from epo_ops import xml
  client=Mock();body=f'<ops:world-patent-data xmlns:ops="http://ops.epo.org"><x>SECRET_TOKEN SECRET_KEY SECRET_PASSWORD</x></ops:world-patent-data>'.encode()
  with patch('epo_ops.token',return_value='SECRET_TOKEN'),patch('epo_ops.response',return_value=(200,body,{})),patch('additional_source_apis.credentials',return_value={'EPO-consumer':'SECRET_KEY','EPO-consumer-secret':'SECRET_PASSWORD'}):xml(client,'rest-services/legal/publication/docdb/EP.1.A1')
  saved=client.save.call_args.args[0];self.assertNotIn(b'SECRET_',saved);self.assertIn(b'[REDACTED]',saved)
if __name__=='__main__':unittest.main()
