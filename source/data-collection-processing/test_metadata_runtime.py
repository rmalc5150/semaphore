import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from contextlib import nullcontext

from metadata_engine.runtime_db import Database,source_failure_state,fingerprint,source_failure_mode,failure_date
from metadata_engine.evidence import substantive,RawFailure,object_bytes
from metadata_engine.source_policies import build
from metadata_engine.graph import stable_id
from metadata_engine_sec_document_pilot import committed_input,HEAD,MANIFEST,KEY


class RuntimeTests(unittest.TestCase):
    def test_a_handed_off_source_is_excluded_only_on_that_worker(self):
        database = Database.__new__(Database)
        database.config = {}
        cursor = Mock()
        cursor.fetchall.return_value = []
        database.tx = Mock(return_value=nullcontext(cursor))
        with patch('metadata_engine.runtime_db.host_excluded_sources',
                   return_value=('openalex_scholarly_graph',)):
            self.assertIsNone(database.claim(source_key='openalex_scholarly_graph'))
            database.tx.assert_not_called()
            self.assertIsNone(database.claim())
            sql, parameters = cursor.execute.call_args.args
            self.assertIn('s.source_key NOT IN (%s)', sql)
            self.assertEqual(parameters[-1], 'openalex_scholarly_graph')

    def test_repeated_edinet_missing_manifest_waits_longer(self):
        database=Database.__new__(Database)
        database.config={}
        cursor=Mock()
        database.tx=lambda: nullcontext(cursor)
        for source, attempts, minutes in (('edinet_filings', 2, 15), ('edinet_filings', 3, 360), ('other', 32, 15)):
            with self.subTest(source=source, attempts=attempts):
                cursor.reset_mock()
                cursor.fetchone.side_effect=[{'state': 'enabled'}, {'state': 'running', 'lease_token': 'lease', 'attempts': attempts}]
                database.finish({'source_key': source, 'job_id': 'job', 'lease_token': 'lease'},
                                'uncommitted', 'collection_manifest_not_yet_present')
                self.assertEqual(cursor.execute.call_args.args[1][-2], minutes)

    def test_native_evidence_uses_actual_request_host(self):
        from metadata_engine.worker import load_input
        import hashlib
        key='research-data/constellation-backfill/jobs/test/attempts/test/manifest.json';bucket='bucket'
        row={'source_key':'nsf_awards','source_record_id':'123','record_kind':'research_records','retrieved_at':'2026-10-30T10:00:00Z','original_url':'https://www.nsf.gov/awardsearch/showAward?AWD_ID=123','payload':{'id':'123'}}
        record_bytes=json.dumps(row).encode()
        manifest={'job_id':'test','pagination_exhausted':True,'pages':[{'request_page':0,'records':{'uri':'s3://bucket/research-data/records/0','sha256':hashlib.sha256(record_bytes).hexdigest()},'raw':{'uri':'s3://bucket/research-data/raw/sha','sha256':'a'*64}}]}
        manifest_bytes=json.dumps(manifest).encode()
        request={'request_url':'https://api.nsf.gov/services/v1/awards.json','raw':manifest['pages'][0]['raw']}
        bodies={key:manifest_bytes,'research-data/records/0':record_bytes,key.rsplit('/manifest.json',1)[0]+'/requests/0.json':json.dumps(request).encode()}
        cursor=Mock();cursor.fetchone.return_value={'status':'succeeded','result_json':json.dumps({'manifest_uri':'s3://bucket/'+key,'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest()})}
        db=Mock();db.config={}
        with patch('metadata_engine.worker.collection_tx',return_value=nullcontext(cursor)),patch('metadata_engine.worker.object_bytes',side_effect=lambda s,b,k,**kw:bodies[k]):
            rows,_,_=load_input(Mock(),bucket,{'input_key':key,'input_format':'native_manifest'},db)
        self.assertEqual(rows[0]['payload']['source_evidence'][0]['source_url'],request['request_url'])
        request['request_parameters']={'printFields':'id,title,abstractText'}
        bodies[key.rsplit('/manifest.json',1)[0]+'/requests/0.json']=json.dumps(request).encode()
        with patch('metadata_engine.worker.collection_tx',return_value=nullcontext(cursor)),patch('metadata_engine.worker.object_bytes',side_effect=lambda s,b,k,**kw:bodies[k]),self.assertRaisesRegex(RawFailure,'projects_subset'):
            load_input(Mock(),bucket,{'input_key':key,'input_format':'native_manifest'},db)

    def test_daily_commit_wakes_metadata_only_after_checkpoint_commit(self):
        import collection_storage as storage
        run=object.__new__(storage.CollectionRun)
        run.closed=False;run.pending_final={'status':'complete','reason_code':None,'expected_records':1}
        run.spec={'source':'sec_edgar','mode':'daily'}
        run.state={'exhausted':True,'record_count':1,'revision':1,'terminal_history':[],'manifest_prefix':'manifests/run-test',
            'pages':[{'batches':[{'key':'raw/source=sec_edgar/batch.jsonl','etag':'"original-write"'},
                                 {'key':'raw/source=sec_edgar/older.jsonl'}]}]}
        run.token='old';run.checkpoint_key='checkpoints/test/head.json'
        run.store=object.__new__(storage.S3Store);run.store.bucket='test';run.store.prefix='research-data';run.store.owner=None;run.store.client=Mock()
        with patch.dict('os.environ',{'METADATA_ENGINE_NOTIFY':'1'}),patch.object(storage,'write_json',return_value='new') as committed:
            run.finish('complete',expected_records=1)
        self.assertEqual(committed.call_count,2)
        notice=run.store.client.put_object.call_args.kwargs
        self.assertIn('/intake/',notice['Key'])
        body=json.loads(notice['Body'])
        self.assertEqual(body['batches'],['research-data/raw/source=sec_edgar/batch.jsonl',
                                          'research-data/raw/source=sec_edgar/older.jsonl'])
        self.assertEqual(body['batch_etags'],{'research-data/raw/source=sec_edgar/batch.jsonl':'"original-write"'})

    def test_intake_prefers_write_etag_with_per_batch_head_fallback(self):
        from metadata_engine.controller import committed_daily_intake
        first='research-data/raw/source=sec_edgar/first.jsonl'
        second='research-data/raw/source=sec_edgar/second.jsonl'
        for etags, expected_heads in (({first:'"original"',second:'"other"'},0),
                                     ({first:'"original"',second:'bad'},1), (None,2)):
            with self.subTest(etags=etags):
                db=Mock(config={'bucket':'bucket','prefix':'meta','contracts':{'sec_edgar':{}}})
                db.cursor.return_value={}
                db.enqueue.return_value=True
                s3=Mock()
                s3.list_objects_v2.side_effect=[{'Contents':[{'Key':'meta/notice.json'}]},{}]
                s3.head_object.return_value={'ETag':'"fallback"'}
                notice={'batches':[first,second]}
                if etags is not None:
                    notice['batch_etags']=etags
                with patch('metadata_engine.controller.object_bytes',return_value=json.dumps(notice).encode()):
                    self.assertEqual(committed_daily_intake(db,s3),2)
                self.assertEqual(s3.head_object.call_count,expected_heads)
                tokens=[call.args[2] for call in db.enqueue.call_args_list]
                self.assertEqual(tokens, ['"original"' if etags else '"fallback"',
                                          '"other"' if expected_heads==0 else '"fallback"'])

    def test_failed_checkpoint_does_not_wake_metadata(self):
        import collection_storage as storage
        run=object.__new__(storage.CollectionRun)
        run.closed=False;run.pending_final={'status':'complete','reason_code':None,'expected_records':1}
        run.spec={'source':'sec_edgar','mode':'daily'};run.token='old';run.checkpoint_key='checkpoints/test/head.json'
        run.state={'exhausted':True,'record_count':1,'revision':1,'terminal_history':[],'manifest_prefix':'manifests/run-test','pages':[]}
        run.store=object.__new__(storage.S3Store);run.store.client=Mock()
        with patch.dict('os.environ',{'METADATA_ENGINE_NOTIFY':'1'}),patch.object(storage,'write_json',side_effect=[None,storage.Conflict('lost lease')]):
            with self.assertRaises(storage.Conflict):run.finish('complete',expected_records=1)
        run.store.client.put_object.assert_not_called()

    def test_four_separate_failures_open_circuit(self):
        count=0
        for i in range(1,5):
            count,state=source_failure_state(count,True)
            self.assertEqual(count,i);self.assertEqual(state,'enabled' if i<4 else 'raw_stopped')

    def test_success_breaks_consecutive_failures(self):
        count,state=source_failure_state(3,False)
        self.assertEqual((count,state),(0,'enabled'))

    def test_reviewed_source_uses_date_queue_without_disabling_collection(self):
        config={'verified_source_failure_handling':{'gleif_legal_entities':'queue_by_source_date'}}
        self.assertEqual(source_failure_mode(config,'gleif_legal_entities'),'queue_by_source_date')
        self.assertIsNone(source_failure_mode(config,'unreviewed'))
        self.assertEqual(failure_date({'input_key':'research-data/raw/source=gleif_legal_entities/dataset=specialist_inputs/ingestion_date=2026-11-09/run_id=x/batch.jsonl'}),'2026-11-09')

    def test_metadata_with_numeric_dates_and_citations_fails(self):
        with self.assertRaises(RawFailure):substantive(json.dumps({'id':123,'year':2020,'citationCount':100,'abstract':'text','title':'title'}).encode())

    def test_native_measurements_are_raw_data(self):
        self.assertEqual(substantive(b'{"data":[{"period":"2024-01","value":3.2,"units":"USD"}]}'),'native_record')

    def test_html_indexes_and_block_pages_rejected(self):
        for body in (b'<html><title>Catalogue</title></html>',b'<html><title>Access denied</title></html>'):
            with self.assertRaises(RawFailure):substantive(body)

    def test_scientific_abstract_xml_is_not_full_text(self):
        with self.assertRaises(RawFailure):substantive(b'<article><abstract>abstract only</abstract></article>')
        self.assertEqual(substantive(b'<article><body>original full article text</body></article>'),'full_text')

    def test_raw_checksum_mismatch_fails(self):
        s3=Mock();s3.get_object.return_value={'Body':io.BytesIO(b'raw')}
        with self.assertRaisesRegex(RawFailure,'checksum'):object_bytes(s3,'bucket','key',expected='a'*64)

    def test_stable_ids_keep_entities_separate(self):
        a=stable_id(['organization','CIK','0001674416'])
        self.assertEqual(a,stable_id(['organization','CIK','0001674416']))
        self.assertNotEqual(a,stable_id(['organization','CIK','0001674417']))

    def test_all_catalog_entries_have_policies_and_owner_pauses(self):
        policies=build(Path(__file__).parent)
        catalogued={n for p in policies.values() for n in p['catalog_entries']}
        from market_source_register import OWNER_REMOVED
        from metadata_engine.market_archive import contracts as archive_contracts
        self.assertEqual({n for n in catalogued if n<=158},set(range(1,159))-OWNER_REMOVED)
        from market_source_capture import active_routes
        enabled={int(source.rsplit('_',1)[-1]) for source,datasets in active_routes().items()
                 if any(policy['metadata'] for policy in datasets.values())}
        self.assertEqual({n for n in catalogued if n>158},enabled|{166,248,253})
        for source, policy in archive_contracts().items():
            self.assertEqual(policies[source],policy)
        self.assertNotIn('marketaux',policies)
        for key in ('github_sdk','reddit','bluesky_search','nice_technology_appraisals'):
            self.assertEqual(policies[key]['state'],'owner_paused')
        self.assertIn('full_text',policies['europe_pmc']['raw_requirements']['required_artifact_kinds'])

    def test_eodhd_contract_is_vendor_data_scoped_to_general_and_market(self):
        policies=build(Path(__file__).parent)
        for key in ('eodhd','eodhd_market'):
            self.assertEqual(policies[key]['provider_role'],'third_party_data_vendor')
            self.assertEqual(policies[key]['raw_requirements']['required_artifact_kinds'],['provider_record','provider_data'])
            self.assertIn('eodhd.com',policies[key]['allowed_hosts'])
        self.assertFalse(policies['eodhd']['dataset_contracts']['company_profiles']['full_fundamentals_required'])

    def test_eodhd_profile_response_is_not_required_to_be_a_primary_document(self):
        from metadata_engine.evidence import evidence_for
        from metadata_engine.labelling import label_observation
        import hashlib
        general={'Code':'ABC','Name':'ABC plc','Exchange':'US','Description':'Provider company description'}
        body=json.dumps(general).encode();sha=hashlib.sha256(body).hexdigest()
        row={'source':'eodhd','dataset':'company_profiles','source_record_id':'ABC.US','ingested_at':'2026-10-30T10:00:00Z',
             'payload':{'provider_symbol':'ABC.US','profile_status':'available','general':general,
                        'source_evidence':[{'key':'source_documents/eodhd/'+sha,'sha256':sha,'source_url':'https://eodhd.com/api/fundamentals/ABC.US?filter=General&fmt=json'}]}}
        policy=build(Path(__file__).parent)['eodhd'];s3=Mock();s3.get_object.return_value={'Body':io.BytesIO(body)}
        evidence=evidence_for(row,policy,s3,'bucket')
        self.assertEqual(evidence[0]['artifact_kind'],'provider_data')
        self.assertEqual(evidence[0]['provider_role'],'third_party_data_vendor')
        envelope={**evidence[0],'artifact_kind':'provider_record'}
        labelled=label_observation({**row,'raw_s3_uri':'s3://bucket/envelope','raw_sha256':'a'*64,'raw_completeness_status':'complete','raw_artifacts':[envelope,*evidence]},policy)
        self.assertEqual(labelled['completeness_scope'],'declared_provider_dataset')
        self.assertIn('vendor_data_not_primary_document',labelled['quality_flags'])

    def test_eodhd_profile_identity_mismatch_and_error_response_fail(self):
        from metadata_engine.eodhd import validate,ProviderDataError
        row={'source':'eodhd','dataset':'company_profiles','payload':{'provider_symbol':'ABC.US','profile_status':'available','general':{'Code':'ABC','Name':'ABC'}}}
        url='https://eodhd.com/api/fundamentals/ABC.US?filter=General'
        for data in ({'Code':'XYZ','Name':'Wrong company'},{'error':'quota exceeded'},{'Code':'ABC','Name':'Changed'}):
            with self.assertRaises(ProviderDataError):validate(json.dumps(data).encode(),row,url)

    def test_eodhd_not_found_is_explicit_unavailable_outcome(self):
        from metadata_engine.eodhd import validate,ProviderDataError
        row={'source':'eodhd','dataset':'company_profiles','payload':{'provider_symbol':'ABC.US','profile_status':'not_found','general':None}}
        url='https://eodhd.com/api/fundamentals/ABC.US?filter=General'
        self.assertFalse(validate(b'404 Not Found',row,url)['profile_content_complete'])
        for body in (b'{"error":"quota exceeded"}',b'404 Access denied',b'{}'):
            with self.assertRaises(ProviderDataError):validate(body,row,url)

    def test_eodhd_price_fields_dates_and_adjustments_are_verified(self):
        from metadata_engine.eodhd import validate,ProviderDataError
        native={'date':'2026-10-29','open':10,'high':12,'low':9,'close':11,'adjusted_close':5.5,'volume':100}
        row={'source':'eodhd_market','dataset':'market_records','payload':{'symbol':'ABC.US','kind':'prices','data':{k:str(v) for k,v in native.items()}}}
        url='https://eodhd.com/api/eod/ABC.US?fmt=json'
        result=validate(json.dumps([native]).encode(),row,url)
        self.assertEqual(result['provider_symbol'],'ABC.US')
        for changed in ({**native,'close':6},{k:v for k,v in native.items() if k!='adjusted_close'}, {**native,'date':'2026-10-28'}):
            with self.assertRaises(ProviderDataError):validate(json.dumps([changed]).encode(),row,url)

    def test_eodhd_listing_status_dividends_and_split_scope(self):
        from metadata_engine.eodhd import validate,ProviderDataError
        native={'Code':'ABC','Name':'ABC','Type':'Common Stock','Currency':'USD'}
        row={'source':'eodhd','dataset':'listing_inventory','payload':{'provider_symbol':'ABC.US','requested_exchange':'US','name':'ABC','listing_status':'active','instrument_type':'Common Stock','currency':'USD'}}
        self.assertTrue(validate(json.dumps([native]).encode(),row,'https://eodhd.com/api/exchange-symbol-list/US')['row_identity_verified'])
        with self.assertRaises(ProviderDataError):validate(json.dumps([native]).encode(),row,'https://eodhd.com/api/exchange-symbol-list/US?delisted=1')
        for kind,endpoint,data in [('dividends','div',{'date':'2026-10-29','value':'0.3'}),('splits','splits',{'date':'2026-10-29','split':'2/1'})]:
            row={'source':'eodhd_market','dataset':'market_records','payload':{'symbol':'ABC.US','kind':kind,'data':data}}
            self.assertTrue(validate(json.dumps([data]).encode(),row,'https://eodhd.com/api/'+endpoint+'/ABC.US')['row_identity_verified'])

    def test_new_etag_or_contract_is_new_work(self):
        self.assertNotEqual(fingerprint(['s','key','etag1','v2']),fingerprint(['s','key','etag2','v2']))
        self.assertNotEqual(fingerprint(['s','key','etag1','v2']),fingerprint(['s','key','etag1','v3']))


if __name__=='__main__':unittest.main()
