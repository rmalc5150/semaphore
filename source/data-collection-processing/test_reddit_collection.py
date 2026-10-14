import unittest
from unittest.mock import Mock,patch
from reddit_collection import normalize,revalidate,trim,capture,APIError
NOW=1791750000

def post(name='one',body='example',author='sample',kind='t3'):
 return {'kind':kind,'data':{'id':name,'name':kind+'_'+name,'author':author,'created_utc':NOW-3600,'selftext':body,'body':body,'subreddit':'biotech','title':'Title','score':2,'num_comments':0,'permalink':'/r/biotech/comments/'+name}}

class RedditTests(unittest.TestCase):
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
