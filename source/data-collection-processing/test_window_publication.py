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

    def test_repeated_failure_increases_cooldown_without_success_receipt(self):
        from datetime import datetime
        item={'window_id':self.wid,'manifests':['m']}
        write_json(self.store,'operations/news/publication-queue/'+self.wid+'.json',item)
        prepare=Mock(side_effect=ValueError('provider unavailable'))
        publish_pending(self.store,self.settings,'news',{},prepare,self.root)
        key='operations/news/publication-retries/'+self.wid+'.json'
        first=self.store.get(key);one=json.loads(first.body)
        self.assertEqual(one['attempts'],1)
        write_json(self.store,key,{**one,'retry_after':'2000-01-01T00:00:00Z'},first.token)
        publish_pending(self.store,self.settings,'news',{},prepare,self.root)
        two=json.loads(self.store.get(key).body)
        self.assertEqual(two['attempts'],2)
        self.assertGreater((datetime.fromisoformat(two['retry_after'].replace('Z','+00:00'))-
                            datetime.fromisoformat(one['retry_after'].replace('Z','+00:00'))).total_seconds(),1700)
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
            result=publish_pending(self.store,self.settings,'specialists',{},prepare,self.root,1)
        self.assertEqual(prepare.call_count,1)
        self.assertEqual(result['results'][0]['reason'],'duplicate_queue_alias_requires_review')
        self.assertIsNone(self.store.get('operations/specialists/publication-receipts/'+'a'*64+'.json'))

    def test_targeted_canonical_window_does_not_scan_queue(self):
        write_json(self.store,'operations/specialists/publication-queue/'+self.wid+'.json',
                   {'window_id':self.wid,'manifests':['m']})
        prepare=Mock(return_value=self.root)
        with patch('window_publication.list_keys',side_effect=AssertionError('Full queue scan')), \
             patch('window_publication.release.publish'), \
             patch('window_publication.deploy_window',return_value={'release_id':'valid'}):
            result=publish_pending(self.store,self.settings,'specialists',{},prepare,self.root,1,{self.wid})
        self.assertEqual(result['results'][0]['status'],'verified')

    def test_targeted_alias_still_checks_canonical_manifest(self):
        for wid,extra in [('a'*64,{'repair_evidence':'saved'}),('b'*64,{})]:
            write_json(self.store,'operations/specialists/publication-queue/'+wid+'.json',
                       {'window_id':wid,'manifests':['same'],**extra})
        prepare=Mock()
        result=publish_pending(self.store,self.settings,'specialists',{},prepare,self.root,1,{'a'*64})
        prepare.assert_not_called()
        self.assertEqual(result['results'][0]['reason'],'duplicate_queue_alias_requires_review')

if __name__=='__main__':unittest.main()

class RegulatoryScanTests(unittest.TestCase):
    def test_archive_scan_is_bounded_rotates_and_wraps(self):
        from research_contract import digest
        from collection_storage import LocalStore,write_checked
        import hashlib
        with tempfile.TemporaryDirectory() as root:
            settings=StorageSettings(local_root=root);store=settings.store();config={}
            verification=b'verified';write_checked(store,'verified.json',verification)
            for n in range(130):
                wid=f'{n:064x}';manifests=['m'+str(n)]
                write_json(store,'operations/regulatory/publication-queue/'+wid+'.json',{'window_id':wid,'manifests':manifests})
                write_json(store,'operations/regulatory/publication-receipts/'+wid+'.json',{'source_hash':digest({'manifests':manifests,'config':config,'curation_version':'window-publication-1.0'}),'verification_key':'verified.json','verification_sha256':hashlib.sha256(verification).hexdigest()})
            with patch('window_publication.load_stored',wraps=__import__('window_publication').load_stored)as reads:
                publish_pending(store,settings,'regulatory',config,Mock(),root,2)
                queues=[c.args[1]for c in reads.call_args_list if '/publication-queue/'in c.args[1]]
                self.assertEqual(len(queues),128)
                self.assertEqual(json.loads(store.get('operations/regulatory/publication-retries/_scan-cursor.json').body)['last_key'],queues[-1])
                reads.reset_mock();publish_pending(store,settings,'regulatory',config,Mock(),root,2)
                queues=[c.args[1]for c in reads.call_args_list if '/publication-queue/'in c.args[1]]
                self.assertEqual(queues[:2],['operations/regulatory/publication-queue/'+f'{n:064x}'+'.json'for n in (128,129)])
                self.assertEqual(len(queues),128)
    def test_next_unpublished_window_is_not_skipped_at_batch_limit(self):
        from collection_storage import write_checked
        with tempfile.TemporaryDirectory()as root:
            settings=StorageSettings(local_root=root);store=settings.store()
            for n in range(3):
                wid=f'{n:064x}';write_json(store,'operations/regulatory/publication-queue/'+wid+'.json',{'window_id':wid,'manifests':['m'+str(n)]})
            with patch('window_publication.release.publish'),patch('window_publication.deploy_window',return_value={'release_id':'r'}):
                publish_pending(store,settings,'regulatory',{},Mock(return_value=root),root,1)
            state=json.loads(store.get('operations/regulatory/publication-retries/_scan-cursor.json').body)
            self.assertEqual(state['last_key'],'operations/regulatory/publication-queue/'+'0'*64+'.json')
