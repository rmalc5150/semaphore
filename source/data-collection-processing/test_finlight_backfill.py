from copy import deepcopy
from datetime import date
import hashlib
import tempfile
import unittest
from unittest.mock import Mock, patch

from collection_storage import StorageSettings, write_json
from collection_operations import load_stored
from news_operations import NewsOperations
from news_collection import targets
from research_contract import ROOT, load_json, digest, canonical_json
import finlight_backfill as archive


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.settings = StorageSettings(local_root=tmp.name)
        self.store = self.settings.store()
        self.runner = NewsOperations(self.store, self.settings, load_json(ROOT/'config/news-operations.json'))
        control, self.config, self.prefix = archive.setup()
        self.control = {**control, 'start': '2021-01-01', 'end_exclusive': '2021-01-02'}
        self.patch = patch.object(archive, 'setup', return_value=(self.control, self.config, self.prefix))
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.sns = Mock(); self.sns.publish.return_value = {'MessageId': 'sent'}

    def ready(self):
        write_json(self.store, self.prefix+'/collection.json', {'next_date':'2021-01-02'})
        write_json(self.store, self.runner.prefix+'/finlight/daily.json', {'next_date':'2026-10-11'})
        scope = targets(self.config, self.runner.universe, [], [])
        self.wid = digest({'provider':'finlight','date':'2021-01-01','mode':'historical',
                           'universe':digest(self.runner.universe),'targets':scope})
        manifests = []
        for target in scope:
            for lang in ('en','zh'):
                key = 'test/'+target['name']+'/'+lang+'.json'; manifests.append(key)
                write_json(self.store,key,{'status':'complete','exhausted':True,'task':{
                    'source':'finlight','mode':'historical',
                    'window':{'start':'2021-01-01T00:00:00Z','end':'2021-01-02T00:00:00Z'},
                    'scope':{'configuration_hash':digest(self.config),'target':target,'language':lang}}})
        self.queue = {'manifests':manifests}
        self.qkey = 'operations/news/publication-queue/'+self.wid+'.json'
        write_json(self.store,self.qkey,self.queue)
        body = canonical_json({'status':'verified','window_id':self.wid,'release_id':'release'})
        self.store.put('verification',body)
        receipt = {'status':'verified','release_id':'release','verification_key':'verification',
            'verification_sha256':hashlib.sha256(body).hexdigest(),
            'source_hash':digest({'manifests':manifests,'config':load_json(ROOT/'config/news-athena.json'),
                                  'curation_version':'window-publication-1.0'})}
        self.rkey = 'operations/news/publication-receipts/'+self.wid+'.json'
        write_json(self.store,self.rkey,receipt)

    def check(self):
        return archive.check_completion(self.runner,self.sns,'topic',date(2026,10,11))

    def test_no_notification_before_collection(self):
        self.assertEqual(self.check()['status'],'incomplete'); self.sns.publish.assert_not_called()

    def test_verified_completion_notifies_once(self):
        self.ready()
        self.assertEqual(self.check()['status'],'ready_to_downgrade')
        self.check(); self.sns.publish.assert_called_once()

    def test_stale_receipt_never_advances(self):
        self.ready()
        receipt, token = load_stored(self.store,self.rkey)
        receipt['source_hash']='stale'; write_json(self.store,self.rkey,receipt,token)
        self.assertEqual(self.check()['next_date'],'2021-01-01'); self.sns.publish.assert_not_called()

    def test_corrupt_verification_never_notifies(self):
        self.ready(); old=self.store.get('verification'); self.store.put('verification',b'bad',old.token)
        self.assertEqual(self.check()['status'],'invalid_verification'); self.sns.publish.assert_not_called()

    def test_missing_language_never_notifies(self):
        self.ready()
        key = self.queue['manifests'][-1]; value,token=load_stored(self.store,key)
        value['task']['scope']['language']='en'; write_json(self.store,key,value,token)
        self.assertEqual(self.check()['status'],'scope_incomplete'); self.sns.publish.assert_not_called()

    def test_daily_lag_blocks_notification(self):
        self.ready(); key=self.runner.prefix+'/finlight/daily.json'; _,token=load_stored(self.store,key)
        write_json(self.store,key,{'next_date':'2026-10-10'},token)
        self.assertEqual(self.check()['status'],'incomplete'); self.sns.publish.assert_not_called()

    def test_partial_archive_preserves_cursor(self):
        with patch.object(self.runner,'window',return_value={'status':'partial','reason':'page_limit'}):
            result=archive.collect_archive(self.runner,'fake')
        self.assertEqual(result['next_date'],'2021-01-01')

    def test_send_failure_can_retry(self):
        self.ready(); self.sns.publish.side_effect=RuntimeError('unavailable')
        with self.assertRaises(RuntimeError): self.check()
        self.sns.publish.side_effect=None
        self.assertEqual(self.check()['notification_message_id'],'sent')


if __name__ == '__main__': unittest.main()
