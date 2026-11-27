import json,unittest
from unittest.mock import Mock,patch
from copernicus_capture import fetch,call
from regulatory_collection import SourceIssue
from specialist_inputs import item
class Expiry(unittest.TestCase):
 def setup(self):
  client=Mock();client.store.get.return_value=Mock(body=b'{"job_id":"abc-123"}',token='old-etag')
  job={'adapter':'additional_copernicus','start':'2026-10-01','end':'2026-10-02','parameters':{'dataset':'reanalysis-era5-single-levels','location':'Berlin','area':[53,13,52,14]}}
  return client,job
 def test_successful_job_with_expired_asset_is_requeued_without_data(self):
  client,job=self.setup();response=Mock(status_code=404);response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch('copernicus_capture.call',side_effect=[{'status':'successful'},{'asset':{'value':{'href':'https://download.ecmwf.int/gone.nc','file:size':100}}}]),patch('copernicus_capture.requests.get',return_value=response),patch('collection_storage.write_json')as write:
   rows,cursor=fetch(client,job,None,item)
  self.assertFalse(rows);self.assertEqual(json.loads(cursor)['expired_job_id'],'abc-123');self.assertEqual(write.call_args.args[-1],'old-etag');self.assertEqual(write.call_args.args[2]['reason'],'copernicus_successful_job_asset_expired');self.assertEqual(len(write.call_args_list),2)
 def test_403_does_not_clear_saved_job(self):
  client,job=self.setup();response=Mock(status_code=403);response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
  with patch('copernicus_capture.call',side_effect=[{'status':'successful'},{'asset':{'value':{'href':'https://download.ecmwf.int/no.nc','file:size':100}}}]),patch('copernicus_capture.requests.get',return_value=response),patch('collection_storage.write_json')as write:
   with self.assertRaisesRegex(SourceIssue,'403'):fetch(client,job,None,item)
  write.assert_not_called()
 def test_provider_job_404_preserves_receipt_before_retry(self):
  client,job=self.setup()
  with patch('copernicus_capture.call',side_effect=SourceIssue('copernicus_expired_job',True)),patch('collection_storage.write_json')as write:
   rows,cursor=fetch(client,job,json.dumps({'job_id':'abc-123','poll':5}),item)
  self.assertEqual(json.loads(cursor)['poll'],6);self.assertFalse(rows);self.assertIn('/expired/',write.call_args_list[0].args[1])
 def test_renewal_replaces_only_expired_submission_revision(self):
  client,job=self.setup();client.store.get.return_value=Mock(body=b'{"expired_job_id":"old"}',token='expired-etag')
  from unittest.mock import MagicMock
  control=MagicMock();control.db.return_value.__enter__.return_value.fetchone.return_value={'acquired':1}
  with patch('constellation.control.Control',return_value=control),patch('copernicus_capture.call',side_effect=[{'jobs':[]},{'jobID':'fresh-123'},{'status':'running'}]),patch('collection_storage.write_json')as write:
   rows,state=fetch(client,job,None,item)
  self.assertFalse(rows);self.assertEqual(write.call_args.args[-1],'expired-etag');self.assertEqual(json.loads(state)['job_id'],'fresh-123')
if __name__=='__main__':unittest.main()
