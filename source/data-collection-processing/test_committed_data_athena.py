import unittest
from committed_data_athena import batches
from research_contract import digest

class CommittedTests(unittest.TestCase):
 def doc(self):
  task={'source':'example','dataset':'records'}
  batch={'key':'raw/source=example/dataset=records/ingestion_date=2026-10-11/run_id=run_a/page-00000000-part-00000-'+'a'*64+'.jsonl','sha256':'a'*64,'records':2,'bytes':100}
  return {'task':task,'task_id':'task_'+digest(task),'status':'partial','record_count':2,'pages':[{'record_count':2,'batches':[batch]}]}
 def test_partial_committed_rows_are_accessible(self):self.assertEqual(batches(self.doc())[0][3],2)
 def test_wrong_scope_rejected(self):
  d=self.doc();d['pages'][0]['batches'][0]['key']=d['pages'][0]['batches'][0]['key'].replace('source=example','source=other')
  with self.assertRaises(ValueError):batches(d)
 def test_incorrect_counts_rejected(self):
  d=self.doc();d['record_count']=3
  with self.assertRaises(ValueError):batches(d)
 def test_duplicate_batch_rejected(self):
  d=self.doc();d['pages'][0]['batches']*=2
  with self.assertRaises(ValueError):batches(d)
 def test_wrong_task_identity_rejected(self):
  d=self.doc();d['task_id']='task_other'
  with self.assertRaises(ValueError):batches(d)

class IncrementalVerificationTests(unittest.TestCase):
 def setUp(self):
  import sqlite3
  self.db=sqlite3.connect(':memory:')
  self.db.executescript('CREATE TABLE batches (key TEXT PRIMARY KEY,source TEXT,dataset TEXT,records INTEGER,bytes INTEGER,sha256 TEXT); CREATE TABLE verified_batches (key TEXT PRIMARY KEY,query_id TEXT); CREATE TABLE verified_partitions (source TEXT,dataset TEXT,manifest_sha256 TEXT,query_id TEXT);')
  self.db.execute("INSERT INTO batches VALUES ('raw/a','example','records',2,100,'a')")
 def tearDown(self):self.db.close()
 def test_full_verified_manifest_seeds_incremental_ledger(self):
  import hashlib
  from committed_data_athena import manifest_body,bootstrap_verified
  checksum=hashlib.sha256(manifest_body(self.db,'example','records')).hexdigest()
  self.db.execute('INSERT INTO verified_partitions VALUES (?,?,?,?)',('example','records',checksum,'q1'))
  bootstrap_verified(self.db)
  self.assertEqual(b'',manifest_body(self.db,'example','records',pending=True))
 def test_changed_manifest_cannot_be_assumed_verified(self):
  from committed_data_athena import bootstrap_verified
  self.db.execute("INSERT INTO verified_partitions VALUES ('example','records','old_hash','q1')")
  bootstrap_verified(self.db)
  self.assertEqual(0,self.db.execute('SELECT count(*) FROM verified_batches').fetchone()[0])
 def test_only_new_batches_enter_delta_manifest(self):
  from committed_data_athena import manifest_body
  self.db.execute("INSERT INTO verified_batches VALUES ('raw/a','q1')")
  self.db.execute("INSERT INTO batches VALUES ('raw/b','example','records',1,50,'b')")
  body=manifest_body(self.db,'example','records',pending=True)
  self.assertIn(b'raw/b\n',body);self.assertNotIn(b'raw/a\n',body)

 def verifier(self):
  from unittest.mock import Mock
  class Missing(Exception):pass
  glue=Mock();glue.exceptions.EntityNotFoundException=Missing
  glue.get_table.side_effect=Missing;glue.get_partition.side_effect=Missing
  return Mock(),glue,Mock()
 def test_verified_receipt_precedes_ledger_commit(self):
  from unittest.mock import patch
  from committed_data_athena import verify_batches
  s3,glue,athena=self.verifier()
  s3.put_object.side_effect=[{},RuntimeError('evidence write failed')]
  with patch('committed_data_athena.query',return_value={'query_id':'q1','rows':[['2','0']],'bytes_scanned':100}):
   with self.assertRaisesRegex(RuntimeError,'evidence write failed'):
    verify_batches(self.db,s3,glue,athena,{},[{'source':'example','dataset':'records','manifest_sha256':'hash'}])
  self.assertEqual(0,self.db.execute('SELECT count(*) FROM verified_batches').fetchone()[0])
 def test_wrong_query_count_cannot_verify_batches(self):
  from unittest.mock import patch
  from committed_data_athena import verify_batches
  s3,glue,athena=self.verifier()
  with patch('committed_data_athena.query',return_value={'query_id':'q1','rows':[['1','0']],'bytes_scanned':100}):
   with self.assertRaisesRegex(ValueError,'count/schema mismatch'):
    verify_batches(self.db,s3,glue,athena,{},[{'source':'example','dataset':'records','manifest_sha256':'hash'}])
  self.assertEqual(0,self.db.execute('SELECT count(*) FROM verified_batches').fetchone()[0])
 def test_large_file_inventory_is_split_into_bounded_queries(self):
  import re
  from unittest.mock import patch
  from committed_data_athena import verify_batches
  self.db.execute('UPDATE batches SET records=1')
  self.db.executemany('INSERT INTO batches VALUES (?,?,?,?,?,?)',[(f'raw/b{i}', 'example','records',1,100,'b') for i in range(1000)])
  s3,glue,athena=self.verifier();objects={}
  s3.put_object.side_effect=lambda **kw:objects.update({kw['Key']:kw['Body']}) or {}
  def checked_query(client,sql):
   group=re.search("batch_group='([a-f0-9]+)'",sql).group(1)
   body=next(v for k,v in objects.items() if k.endswith('/'+group+'/files.txt'))
   count=len(body.splitlines());self.assertLessEqual(count,1000)
   return {'query_id':group,'rows':[[str(count),'0']],'bytes_scanned':count*100}
  with patch('committed_data_athena.query',side_effect=checked_query):
   result=verify_batches(self.db,s3,glue,athena,{},[{'source':'example','dataset':'records','manifest_sha256':'hash'}])
  self.assertEqual(2,len(result['queries']))
  self.assertEqual(1001,self.db.execute('SELECT count(*) FROM verified_batches').fetchone()[0])

if __name__=='__main__':unittest.main()
