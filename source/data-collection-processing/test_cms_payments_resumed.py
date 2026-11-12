import io,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import cms_payments_resumed as worker
from cms_financial_collection import registry
class Resumed(unittest.TestCase):
 def test_mutable_state_uses_existing_token(self):
  store=Mock();store.get.return_value=Mock(token='etag')
  with patch.object(worker,'write_json')as put:worker.save(store,'key',{'status':'complete'})
  self.assertEqual(put.call_args.args[3],'etag')
 def test_native_row_counts_must_equal_committed_csv_count(self):
  with tempfile.TemporaryDirectory()as tmp,registry(Path(tmp)/'registry.db')as db:
   db.execute("INSERT INTO editions VALUES('edition',?,1,?,'done',NULL)",(json.dumps({'source':'cms_open_payments','edition_id':'edition'}),json.dumps({'row_count':12})));db.commit()
   with patch('committed_data_athena.query',return_value={'rows':[['edition','11']]}),patch('boto3.client'):
    with self.assertRaisesRegex(ValueError,'count_mismatch'):worker.verify_done(db,{'region':'us-east-1','athena_database':'db'},Mock())
 def test_backup_is_consistent_sqlite_and_never_replaces_old_snapshot(self):
  with tempfile.TemporaryDirectory()as tmp:
   state=Path(tmp)/'registry.db'
   with registry(state)as db:db.execute("INSERT INTO control VALUES('test','value')");db.commit()
   store=Mock();store.get.return_value=None
   with patch.object(worker,'save')as save:worker.backup({'state_file':str(state)},store)
   raw=store.put.call_args.args[1];self.assertTrue(raw.startswith(b'SQLite format 3'))
   self.assertEqual(save.call_args.args[2]['bytes'],len(raw));self.assertTrue(store.put.call_args.args[0].endswith('.sqlite3'))
 def test_catalog_failure_does_not_run_metadata_or_queue_fake_window(self):
  store=Mock();store.get.return_value=None;job={'source':'cms_payments_catalog'}
  with patch.object(worker,'load_json',return_value={'sources':[job]}),patch.object(worker,'jobs',return_value=[job]),patch.object(worker,'deadline'),patch.object(worker,'collect',return_value={'status':'failed','reason':'http_503'}),patch.object(worker,'queue_metadata')as queue,patch.object(worker,'save')as save,patch.object(worker,'write_json'):
   worker.catalog(store,Mock());queue.assert_not_called();self.assertEqual(save.call_args.args[2]['status'],'failed')
