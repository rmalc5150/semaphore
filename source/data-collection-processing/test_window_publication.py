import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from botocore.exceptions import ClientError
from collection_storage import StorageSettings,write_json
from research_contract import canonical_json
from window_publication import deploy_window,publish_pending

class WindowTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.settings=StorageSettings(local_root=str(self.root/'store'),s3_bucket='test')
        self.store=self.settings.store(); self.wid='a'*64
        self.report={'bucket':'test','s3_prefix':self.settings.s3_prefix,'release_id':'release','release_prefix':'curated/r',
          'config':{'database':'db','workgroup':'wg','region':'us-east-1'},'files':{'articles':{'columns':[['id','string']],'location':'s3://test/new/','rows':2}}}
        (self.root/'release.json').write_bytes(canonical_json(self.report)+b'\n')
        self.store.put('curated/r/release.json',(self.root/'release.json').read_bytes())
        self.glue=Mock();self.athena=Mock()
        self.glue.get_table.return_value={'Table':{'Parameters':{'optima_owner':'news'},'PartitionKeys':[{'Name':'window_id','Type':'string'}],'StorageDescriptor':{'Columns':[{'Name':'id','Type':'string'}]}}}
        self.previous={'Values':[self.wid],'StorageDescriptor':{'Location':'s3://test/old/'},'Parameters':{'optima_owner':'news','release_id':'old'}}
        self.glue.get_partition.return_value={'Partition':self.previous}

    def test_failed_query_restores_previous_partition(self):
        with patch('window_publication.ensure_catalog'),patch('window_publication.release.run_query',return_value={'rows':[['articles','1']]}):
            with self.assertRaises(ValueError): deploy_window(self.store,self.settings,self.root,self.wid,'news',self.glue,self.athena)
        self.assertEqual(self.glue.update_partition.call_args.kwargs['PartitionInput'],self.previous)
        self.assertFalse((self.root/'window-verification.json').exists())

    def test_success_has_durable_verification(self):
        with patch('window_publication.ensure_catalog'),patch('window_publication.release.run_query',return_value={'rows':[['articles','2']]}):
            receipt=deploy_window(self.store,self.settings,self.root,self.wid,'news',self.glue,self.athena)
        self.assertEqual(json.loads(self.store.get(receipt['verification_key']).body)['status'],'verified')

    def test_failed_publication_is_not_marked_done_and_retries(self):
        item={'window_id':self.wid,'manifests':['m']}
        write_json(self.store,'operations/news/publication-queue/'+self.wid+'.json',item)
        prepare=Mock(side_effect=ValueError('uncommitted manifest'))
        result=publish_pending(self.store,self.settings,'news',{},prepare,self.root)
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(self.store.get('operations/news/publication-receipts/'+self.wid+'.json'))

    def test_uncommitted_specialist_does_not_starve_valid_window(self):
        bad,good='a'*64,'b'*64
        for wid in (bad,good):
            write_json(self.store,'operations/specialists/publication-queue/'+wid+'.json',
                       {'window_id':wid,'manifests':[wid]})
        prepare=Mock(side_effect=[ValueError('Uncommitted manifest'),self.root])
        receipt={'status':'verified','release_id':'valid'}
        with patch('window_publication.release.publish'),patch('window_publication.deploy_window',return_value=receipt):
            result=publish_pending(self.store,self.settings,'specialists',{},prepare,self.root,max_windows=1)
        self.assertEqual([r['status'] for r in result['results']],['failed','verified'])
        self.assertEqual(result['status'],'failed')
        self.assertIsNone(self.store.get('operations/specialists/publication-receipts/'+bad+'.json'))
        self.assertIsNotNone(self.store.get('operations/specialists/publication-receipts/'+good+'.json'))
        self.assertEqual(result['results'][0]['reason_code'],'uncommitted_publication_input')

    def test_repaired_alias_is_not_published_twice(self):
        for wid,extra in [('a'*64,{'repair_evidence':'saved-repair'}),('b'*64,{})]:
            write_json(self.store,'operations/specialists/publication-queue/'+wid+'.json',
                       {'window_id':wid,'manifests':['same-manifest'],**extra})
        prepare=Mock(return_value=self.root)
        with patch('window_publication.release.publish'),patch('window_publication.deploy_window',return_value={'release_id':'valid'}):
            result=publish_pending(self.store,self.settings,'specialists',{},prepare,self.root,1,{'b'*64})
        self.assertEqual(prepare.call_count,1)
        self.assertEqual(result['results'][0]['reason'],'duplicate_queue_alias_requires_review')
        self.assertIsNone(self.store.get('operations/specialists/publication-receipts/'+'a'*64+'.json'))

if __name__=='__main__':unittest.main()
