import json
import tempfile
import unittest
from collection_storage import LocalStore,StorageSettings,write_json
from research_contract import digest
from patent_review_continuation import queue_metadata_notice

class MetadataHandoffTests(unittest.TestCase):
 def test_only_new_committed_batches_are_queued_without_downloading_raw_data(self):
  with tempfile.TemporaryDirectory()as directory:
   store=LocalStore(directory);task={'source':'uspto_odp','mode':'historical'};identity='task_'+digest(task);key='manifests/current/final.json'
   manifest={'task':task,'task_id':identity,'run_id':'current','pages':[
    {'run_id':'old','batches':[{'key':'raw/old.jsonl'}]},
    {'run_id':'current','batches':[{'key':'raw/new.jsonl'}]}]}
   write_json(store,'checkpoints/'+identity+'/head.json',{'task':task,'terminal_history':[key]})
   target=queue_metadata_notice(store,StorageSettings(),key,manifest)
   notice=json.loads(store.get(target).body)
   self.assertEqual(notice['batches'],['research-data/raw/new.jsonl'])
   self.assertEqual(notice['mode'],'historical')
   self.assertEqual(target,queue_metadata_notice(store,StorageSettings(),key,manifest))
   previous=store.get('checkpoints/'+identity+'/head.json')
   write_json(store,'checkpoints/'+identity+'/head.json',{'task':task,'terminal_history':[]},previous.token)
   with self.assertRaisesRegex(ValueError,'not_committed'):queue_metadata_notice(store,StorageSettings(),key,manifest)

 def test_empty_attempt_does_not_repeat_old_intake(self):
  with tempfile.TemporaryDirectory()as directory:
   store=LocalStore(directory);task={'source':'uspto_odp','mode':'daily'};identity='task_'+digest(task);key='manifests/empty/final.json'
   manifest={'task':task,'task_id':identity,'run_id':'empty','pages':[{'run_id':'old','batches':[{'key':'raw/old.jsonl'}]}]}
   write_json(store,'checkpoints/'+identity+'/head.json',{'task':task,'terminal_history':[key]})
   self.assertIsNone(queue_metadata_notice(store,StorageSettings(),key,manifest))
