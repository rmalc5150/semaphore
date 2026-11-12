import unittest
from unittest.mock import Mock,patch
from reddit_collection import normalize,revalidate,trim,capture,APIError
NOW=1791750000

def post(name='one',body='example',author='sample',kind='t3'):
 return {'kind':kind,'data':{'id':name,'name':kind+'_'+name,'author':author,'created_utc':NOW-3600,'selftext':body,'body':body,'subreddit':'biotech','title':'Title','score':2,'num_comments':0,'permalink':'/r/biotech/comments/'+name}}

class RedditTests(unittest.TestCase):
 def test_one_broken_info_record_does_not_block_other_revalidation(self):
  records={}
  for name in ('bad','good'):
   row=normalize(post(name),'biotech','daily',NOW);row['verified_utc']=NOW-50000;records[row['record_id']]=row
  api=Mock();api.get.side_effect=[APIError('reddit_http_500'),APIError('reddit_http_500'),{'data':{'children':[post('good')]}}]
  gaps=revalidate(api,records,NOW)
  self.assertEqual(gaps,[{'record_id':'t3_bad','reason':'reddit_http_500'}])
  self.assertEqual(records['t3_bad']['verified_utc'],NOW-50000)
  self.assertEqual(records['t3_good']['verified_utc'],NOW)

 def test_transient_retries_consume_budget_and_preserve_access_errors(self):
  import io
  from urllib.error import HTTPError
  from reddit_collection import Reddit
  api=Reddit.__new__(Reddit);api.calls=0;api.remaining=None;api.config={'max_requests_per_run':3};api.opener=Mock()
  response=Mock();response.headers={};response.read.return_value=b'{"ok":true}'
  context=Mock();context.__enter__=Mock(return_value=response);context.__exit__=Mock(return_value=False)
  api.opener.open.side_effect=[HTTPError('https://example.com',500,'error',{},io.BytesIO()),context]
  with patch('reddit_collection.time.sleep'):
   self.assertEqual(api._request(Mock(full_url='https://example.com')), {'ok':True})
  self.assertEqual(api.calls,2)
  api.opener.open.side_effect=HTTPError('https://example.com',403,'denied',{},io.BytesIO())
  with patch('reddit_collection.time.sleep'), self.assertRaisesRegex(APIError,'reddit_http_403'): api._request(Mock(full_url='https://example.com'))
  self.assertEqual(api.calls,3)
  with self.assertRaisesRegex(APIError,'request_budget'): api._request(Mock(full_url='https://example.com'))

 def test_server_failure_retry_is_bounded(self):
  import io
  from urllib.error import HTTPError
  from reddit_collection import Reddit
  api=Reddit.__new__(Reddit);api.calls=0;api.remaining=None;api.config={'max_requests_per_run':10};api.opener=Mock()
  api.opener.open.side_effect=[HTTPError('https://example.com',500,'error',{},io.BytesIO()) for _ in range(3)]
  with patch('reddit_collection.time.sleep'),self.assertRaisesRegex(APIError,'reddit_http_500'):api._request(Mock(full_url='https://example.com'))
  self.assertEqual(api.calls,3)

 def test_deleted_content_not_retained(self):
  for child in (post(body='[deleted]'),post(author='[deleted]'),post(body='[removed]')):
   self.assertIsNone(normalize(child,'biotech','daily',NOW))
 def test_no_author_identity_saved(self):
  row=normalize(post(),'biotech','daily',NOW)
  self.assertNotIn('author',row);self.assertEqual('t3_one',row['record_id'])
 def test_revalidation_removes_missing_and_updates_body(self):
  records={}
  for name in ('gone','edited'):
   row=normalize(post(name),'biotech','daily',NOW);row['verified_utc']=NOW-50000;records[row['record_id']]=row
  api=Mock();api.get.return_value={'data':{'children':[post('edited','new text')]}}
  revalidate(api,records,NOW)
  self.assertNotIn('t3_gone',records);self.assertEqual('new text',records['t3_edited']['body'])
 def test_expiry_and_cap(self):
  a=normalize(post('a'),'biotech','daily',NOW);b=normalize(post('b'),'biotech','daily',NOW);b['verified_utc']=NOW-86401
  kept,raw=trim({'a':a,'b':b},NOW,10,10000)
  self.assertEqual(['t3_a'],list(kept));self.assertNotIn(b't3_b',raw)
  self.assertEqual({},trim({'a':a},NOW,10,1)[0])
 def test_historical_cursor_commits_and_no_complete_archive_claim(self):
  api=Mock();api.get.side_effect=[{'data':{'children':[post()],'after':None}}, {'data':{'children':[post('old')],'after':'t3_next'}}]
  state={};records={};report={'scopes':[]}
  with patch('reddit_collection.time.time',return_value=NOW):capture(api,records,state,{'queries':{'biotech':'biotech'}},report)
  self.assertEqual('t3_next',state['biotech:historical_sample']['after']);self.assertFalse(state['biotech:historical_sample']['exhausted'])
 def test_cursor_stall_fails_without_advancing(self):
  api=Mock();api.get.side_effect=[{'data':{'children':[],'after':None}},{'data':{'children':[],'after':'t3_same'}}]
  state={'biotech:historical_sample':{'after':'t3_same'}}
  with patch('reddit_collection.time.time',return_value=NOW),self.assertRaisesRegex(APIError,'cursor_stalled'):
   capture(api,{},state,{'queries':{'biotech':'biotech'}},{'scopes':[]})
  self.assertEqual('t3_same',state['biotech:historical_sample']['after'])

if __name__=='__main__':unittest.main()
