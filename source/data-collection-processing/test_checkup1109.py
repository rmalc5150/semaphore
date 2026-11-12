import json
import unittest
from additional_source_apis import zenodo_event_date
import test_disclosure_collection as fixtures
from test_disclosure_collection import Client,row,page
import disclosure_collection as d

class Dates(unittest.TestCase):
 def test_scalar_dates_canonical_and_intervals_remain_unknown(self):
  for raw,expected in [('2017-02-08 ',('2017-02-08','day')),(' 2016-05 ',('2016-05','month')),('2016',('2016','year')),('2020-04-27/2020-04-30',(None,'unknown')),('2020-02-31',(None,'unknown'))]:
   self.assertEqual(zenodo_event_date(raw),expected)

class Snapshot(unittest.TestCase):
 setUp = fixtures.DisclosureTests.setUp
 read = fixtures.DisclosureTests.read
 def test_frozen_index_resumes_without_requery_after_provider_changes(self):
  rows=[row(1),row(2)];docs={d.urljoin(d.HKEX_API,r['FILE_LINK']):b'<html>Full original filing content for Example Robotics and its operations.</html>' for r in rows}
  c=Client(self.store,[page(rows)],docs)
  first=d.collect_hkex(self.store,self.settings,self.universe,self.taxonomy,self.start,self.end,'historical',client=c,page_size=1,max_pages=1)
  self.assertEqual(first['status'],'partial')
  offline=Client(self.store,[],docs)
  second=d.collect_hkex(self.store,self.settings,self.universe,self.taxonomy,self.start,self.end,'historical',client=offline,page_size=1)
  self.assertEqual(second['status'],'complete');self.assertEqual(len(self.read(second)),2)
  self.assertFalse(any(isinstance(x,tuple) for x in offline.calls))
 def test_partial_daily_listing_cannot_be_snapshot_completion(self):
  c=Client(self.store,[page([row(1)],2)])
  result=d.collect_hkex(self.store,self.settings,self.universe,self.taxonomy,self.start,self.end,'historical',client=c)
  self.assertEqual(result['reason'],'hkex_daily_index_snapshot_incomplete')

class ZenodoPayload(unittest.TestCase):
 def test_interval_keeps_original_value_and_explicit_unknown_date(self):
  from unittest.mock import Mock,patch
  from additional_source_apis import fetch
  from specialist_inputs import item
  raw={'id':1,'metadata':{'publication_date':'2020-04-27/2020-04-30'}}
  job={'adapter':'additional_zenodo','start':'2020-04-01','end':'2020-05-01','parameters':{}}
  with patch('additional_source_apis.get_json',return_value=({'hits':{'hits':[raw],'total':1}},None)):
   rows,cursor=fetch(Mock(),job,None,item)
  self.assertEqual(rows[0]['data'],raw)
  self.assertIsNone(rows[0]['date'])
  self.assertEqual(rows[0]['date_status'],'interval_retained_in_raw')
  self.assertIsNone(cursor)

class SnapshotMigration(unittest.TestCase):
 def test_old_failed_index_migrates_without_repeating_old_cooldown(self):
  import test_collection_operations as fixtures
  from collection_storage import write_json,now
  owner=fixtures.OperationsTests();owner.setUp()
  self.addCleanup(owner.doCleanups)
  original=owner.invoke('hkex-filings',owner.start,owner.end,'daily',[],False)
  key=owner.runner.outcome_key('hkex-filings',owner.start,owner.end,'daily')
  write_json(owner.store,key,{**original,'status':'failed','reason':'hkex_prefix_changed','finished_at':now()})
  owner.calls.clear()
  result=owner.runner.window('hkex-filings',owner.start,owner.end,'daily')
  self.assertEqual(result['status'],'complete')
  self.assertTrue(owner.calls[-1][3])
