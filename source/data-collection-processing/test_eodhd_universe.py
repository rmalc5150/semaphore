import io
import json
import tempfile
import unittest
from unittest.mock import Mock,patch
from datetime import timedelta
from urllib.error import HTTPError

from collection_storage import LocalStore,StorageSettings
from regulatory_collection import SourceIssue
from research_contract import ROOT,load_json,validate_record
import eodhd_universe as e
import eodhd_coverage as coverage
import eodhd_batch as broad
import eodhd_athena as athena
import eodhd_review as review
import eodhd_sector_review as sector_review
import company_universe_pipeline as universe_pipeline
import company_registry_verify as registry_verify
from pathlib import Path


class Response(io.BytesIO):
    pass


class EODHDTests(unittest.TestCase):
    def setUp(self):
        self.config=load_json(ROOT/'config/eodhd-universe.json')

    def test_secret_formats_and_ambiguity(self):
        self.assertEqual(e.parse_token('{"EODHD":" key "}'),'key')
        self.assertEqual(e.parse_token('key'),'key')
        with self.assertRaises(SourceIssue):e.parse_token('{"api_key":"one","token":"two"}')

    def test_access_denied_is_explicit_and_does_not_leak_key(self):
        opener=Mock(side_effect=HTTPError('https://example.test/?api_token=private',403,'forbidden',{},None))
        client=e.EODHDClient('private',opener,sleeper=lambda _:None)
        with self.assertRaises(SourceIssue) as raised:client.get('fundamentals/TEST.US',{'filter':'General'})
        self.assertEqual(str(raised.exception),'eodhd_endpoint_access_denied')
        self.assertNotIn('private',str(raised.exception))
        self.assertEqual(opener.call_count,1)

    def test_public_url_and_evidence_do_not_contain_token(self):
        raw=b'{"Code":"TEST","Name":"Test Semiconductor"}'
        opener=Mock(return_value=Response(raw))
        client=e.EODHDClient('never-expose-token',opener,sleeper=lambda _:None)
        data,body,url=client.get('fundamentals/TEST.US',{'filter':'General'})
        self.assertNotIn('api_token',url)
        self.assertNotIn(b'never-expose-token',body)
        self.assertIn('api_token=',opener.call_args.args[0].full_url)

    def test_echoed_credential_is_never_saved(self):
        client=e.EODHDClient('never-expose-token',Mock(return_value=Response(b'{"error":"never-expose-token"}')),sleeper=lambda _:None)
        with self.assertRaisesRegex(SourceIssue,'contains_credential'):client.get('screener')

    def test_account_details_are_whitelisted(self):
        raw=json.dumps({'subscriptionType':'free','dailyRateLimit':20,'apiKey':'private','email':'private@example.test'}).encode()
        client=e.EODHDClient('private',Mock(return_value=Response(raw)),sleeper=lambda _:None)
        self.assertNotIn('apiKey',client.account())

    def test_multi_sector_and_all_storage_families(self):
        candidates=e.sector_candidates({'Description':'Robotics company develops semiconductor chips and battery energy storage.'},self.config)
        self.assertEqual({c['sector_id'] for c in candidates},{'robotics','semiconductors','energy_storage'})
        for description in ['Thermal storage','Flywheel energy storage','Hydrogen storage tanks','Supercapacitors','Batteries']:
            self.assertIn('energy_storage',{r['sector_id'] for r in e.sector_candidates({'Description':description},self.config)})
        for description in ['Cloud data storage','Hydrogen production','Renewable power generation']:
            self.assertEqual(e.sector_candidates({'Description':description},self.config),[])

    def test_profiles_resume_and_never_backdate_classification(self):
        with tempfile.TemporaryDirectory() as root:
            store=LocalStore(root);settings=StorageSettings()
            universe=load_json(ROOT/'examples/sec-filings/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
            class Client:
                def get(self,path,params):
                    general={'Code':path.split('/')[-1].split('.')[0],'Name':'Synthetic biotech company','Industry':'Biotechnology'}
                    return general,json.dumps(general).encode(),'https://eodhd.com/api/'+path+'?filter=General'
            args=(store,settings,universe,taxonomy,self.config,['AAA.US','BBB.US'],Client())
            self.assertEqual(e.collect_profiles(*args,max_records=1)['status'],'partial')
            result=e.collect_profiles(*args)
            self.assertEqual(result['records'],2)
            manifest=json.loads(store.get(result['manifest']).body)
            for page in manifest['pages']:
                for batch in page['batches']:
                    record=json.loads(store.get(batch['key']).body.splitlines()[0])
                    self.assertEqual(validate_record(record,universe),[])
                    self.assertIsNone(record['event_at'])
                    self.assertIsNone(record['available_at'])
                    self.assertEqual(record['payload']['sector_candidates'][0]['review_status'],'pending')

    def test_inventory_is_complete_input_and_profiles_resume_from_it(self):
        with tempfile.TemporaryDirectory() as root:
            store=LocalStore(root);settings=StorageSettings()
            universe=load_json(ROOT/'examples/sec-filings/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
            exchange={'Name':'Test Exchange','Code':'ZZ','OperatingMIC':'XZZA','Country':'Testland',
                'Currency':'ZZD','CountryISO2':'ZZ','CountryISO3':'ZZZ'}
            class Client:
                def get(self,path,params=None):
                    if path.startswith('exchange-symbol-list/'):
                        rows=[{'Code':'BIO','Name':'Synthetic Biotech','Country':'Testland','Exchange':'ZZ',
                            'Currency':'ZZD','Type':'Common Stock','Isin':'ZZ0000000001'},
                           {'Code':'BOT','Name':'Synthetic Robotics','Country':'Testland','Exchange':'ZZ',
                            'Currency':'ZZD','Type':'Common Stock','Isin':'ZZ0000000002'}]
                        return rows,json.dumps(rows).encode(),'https://eodhd.com/api/'+path+'?fmt=json&type=common_stock'
                    symbol=path.rsplit('/',1)[-1]
                    general={'Code':symbol.split('.')[0],'Name':'Synthetic Biotech','Industry':'Biotechnology'}
                    return general,json.dumps(general).encode(),'https://eodhd.com/api/'+path+'?fmt=json&filter=General'
            inv=e.collect_inventory(store,settings,universe,taxonomy,self.config,[exchange],b'[{"Code":"ZZ"}]',
                'https://eodhd.com/api/exchanges-list?fmt=json',('active',),Client())
            self.assertEqual(inv['records'],2)
            store.get=Mock(wraps=store.get)
            symbols,input_ref=e.read_inventory(store,inv['manifest'],universe,taxonomy)
            evidence_reads=[call.args[0] for call in store.get.call_args_list
                if call.args[0].startswith('source_documents/')]
            self.assertEqual(len(evidence_reads),1)
            self.assertEqual(symbols,['BIO.ZZ','BOT.ZZ'])
            self.assertEqual(input_ref['records'],2)
            first=e.collect_inventory_profiles(store,settings,universe,taxonomy,self.config,inv['manifest'],Client(),max_records=1)
            self.assertEqual(first['status'],'partial')
            partial_report=coverage.report(store,inv['manifest'],[first['manifest']])
            self.assertEqual(partial_report['inventory_symbols_not_yet_attempted'],1)
            self.assertEqual(partial_report['profile_inputs'][0]['status'],'partial')
            self.assertFalse(partial_report['ready_for_universe_promotion'])
            bounded_plan=broad.make_plan(store,inv['manifest'],[],10,self.config)
            with patch.object(broad,'quota_batch_size',return_value=(4,{})):
                bounded_first=broad.collect(store,settings,self.config,bounded_plan,Client(),max_pages=1)
                self.assertEqual((bounded_first['status'],bounded_first['reason'],bounded_first['records']),
                                 ('partial','page_limit',1))
                bounded_second=broad.collect(store,settings,self.config,bounded_plan,Client(),max_pages=1)
                self.assertEqual((bounded_second['status'],bounded_second['records']),('complete',2))
            before=json.loads(store.get(bounded_first['manifest']).body)
            after=json.loads(store.get(bounded_second['manifest']).body)
            self.assertEqual(before['task_id'],after['task_id'])
            self.assertEqual(after['resumed_from_run_id'],before['run_id'])
            plan=broad.make_plan(store,inv['manifest'],[first['manifest']],10,self.config)
            self.assertEqual(plan['symbols'],['BOT.ZZ'])
            self.assertEqual(plan['reused_inventory_symbols'],1)
            client=Client();client.account=lambda:{'dailyRateLimit':100000,'apiRequests':0}
            batch=broad.collect(store,settings,self.config,plan,client)
            self.assertEqual(batch['status'],'complete')
            self.assertEqual(batch['records'],1)
            self.assertTrue(broad.collect(store,settings,self.config,plan,client)['already_complete'])
            release_config={'database':'optima_eodhd_research','workgroup':'optima-eodhd-research','region':'us-east-1',
                'curated_prefix':'curated/eodhd/releases','query_results_prefix':'athena-results/eodhd',
                'inventory_manifest':inv['manifest'],'profile_manifests':[first['manifest']]}
            tables,_,_=athena.curate(store,release_config)
            self.assertEqual(tables['listing_inventory'][0]['exchange_mic'],'XZZA')
            self.assertEqual(tables['exchange_coverage'][0]['profiles_not_collected'],1)
            self.assertEqual(tables['collection_runs'][0]['run_status'],'partial')
            self.assertEqual(tables['company_identity_review'][0]['identity_status'],'pending')
            built=athena.prepare(store,StorageSettings(backend='s3',s3_bucket='test-bucket'),release_config,Path(root)/'build')
            self.assertTrue((built/'sector_candidates.csv').exists())
            decisions_path=Path(root)/'decisions.json'
            decisions_path.write_text('[]')
            with self.assertRaisesRegex(ValueError,'explicit decision'):
                review.prepare(built,decisions_path,Path(root)/'review-build')
            candidate=tables['sector_candidates'][0]
            decision={'provider_symbol':candidate['provider_symbol'],'sector_id':'biotech',
                'profile_observation_id':candidate['profile_observation_id'],'review_status':'supported',
                'reason':'Provider industry explicitly identifies biotechnology.','review_basis':'provider_profile'}
            decisions_path.write_text(json.dumps([decision]))
            reviewed=review.prepare(built,decisions_path,Path(root)/'review-build')
            report=json.loads((reviewed/'release.json').read_text())
            self.assertEqual(report['expected_results']['sector_review_counts'],[['biotech','supported','1']])
            decision['profile_observation_id']='stale'
            decisions_path.write_text(json.dumps([decision]))
            with self.assertRaisesRegex(ValueError,'Stale review'):
                review.prepare(built,decisions_path,Path(root)/'review-build')
            future=e.datetime.now(e.timezone.utc)+timedelta(days=4)
            with patch.object(e,'datetime',wraps=e.datetime) as clock:
                clock.now.return_value=future
                result=e.collect_inventory_profiles(store,settings,universe,taxonomy,self.config,inv['manifest'],Client(),
                    resume_manifest=first['manifest'])
            self.assertEqual(result['records'],2)
            first_run=json.loads(store.get(first['manifest']).body)
            resumed=json.loads(store.get(result['manifest']).body)
            self.assertEqual(first_run['task_id'],resumed['task_id'])
            self.assertEqual(resumed['resumed_from_run_id'],first_run['run_id'])
            full_report=coverage.report(store,inv['manifest'],[first['manifest'],result['manifest']])
            self.assertEqual(full_report['distinct_profiles_attempted'],2)
            self.assertEqual(full_report['inventory_symbols_not_yet_attempted'],0)
            self.assertEqual(full_report['sector_candidate_counts'],{'biotech':2})
            with self.assertRaisesRegex(SourceIssue,'resume_checkpoint_changed'):
                e.collect_inventory_profiles(store,settings,universe,taxonomy,self.config,inv['manifest'],Client(),
                    resume_manifest=first['manifest'])
            evidence_key=evidence_reads[0]
            store.put(evidence_key,b'corrupted',expected=store.get(evidence_key).token)
            with self.assertRaisesRegex(SourceIssue,'inventory_evidence_missing'):
                e.read_inventory(store,inv['manifest'],universe,taxonomy)
            with self.assertRaisesRegex(SourceIssue,'coverage_evidence_checksum_mismatch'):
                coverage.report(store,inv['manifest'])

    def test_directory_excludes_virtual_markets_and_keeps_validated_supplement(self):
        rows=[{'Name':'Stocks','Code':'ZZ','OperatingMIC':'XZZA','CountryISO2':'ZZ'},
              {'Name':'Virtual','Code':'VV','OperatingMIC':None,'CountryISO2':''}]
        class Client:
            def get(self,path,params=None):return rows,json.dumps(rows).encode(),'https://eodhd.com/api/exchanges-list?fmt=json'
        selected,_,_=e.exchange_directory(Client(),self.config)
        self.assertEqual({row['Code'] for row in selected},{'ZZ','HK'})

    def test_quota_batch_reserves_capacity(self):
        class Client:
            def account(self):return {'dailyRateLimit':100000,'apiRequests':97990}
        size,_=e.quota_batch_size(Client(),self.config,100)
        self.assertEqual(size,1)

    def test_profile_404_is_audited_as_terminal_coverage_result(self):
        error=HTTPError('https://example.test',404,'missing',{},io.BytesIO(b'{"error":"not found"}'))
        client=e.EODHDClient('private',Mock(side_effect=error),sleeper=lambda _:None)
        with self.assertRaises(SourceIssue) as raised:client.get('fundamentals/MISSING.ZZ',{'filter':'General'})
        self.assertEqual(raised.exception.code,'eodhd_http_404')
        self.assertEqual(raised.exception.raw,b'{"error":"not found"}')
        self.assertNotIn('api_token',raised.exception.public_url)

    def test_identity_screen_blocks_wrong_instrument_and_empty_content(self):
        base={'name':'Example company','review_flags_json':'["no_legal_identifier"]'}
        self.assertEqual(review.assess_identity({**base,'name':'Example C/W 30'})[0],'instrument_type_review')
        self.assertEqual(review.assess_identity({**base,'name':'Example Inc. CDR'})[0],'security_wrapper_review')
        self.assertEqual(review.assess_identity(base,{'description':'There is no Profile data available for ABC.TW.'})[0],
                         'profile_content_missing')
        self.assertEqual(review.assess_identity({**base,'review_flags_json':'["inventory_isin_mismatch"]'})[0],
                         'identifier_conflict')

    def test_conservative_sector_review_and_alias_extraction(self):
        supported=sector_review.classify('energy_storage',{'description':'We develop and manufacture battery energy storage systems.'})
        rejected=sector_review.classify('energy_storage',{'description':'We explore lithium mineral deposits for battery customers.'})
        pending=sector_review.classify('semiconductors',{'description':'A commercial bank.','gics_industry':'Semiconductors'})
        self.assertEqual(supported[0],'supported')
        self.assertEqual(rejected[0],'rejected')
        self.assertEqual(pending[0],'needs_more_evidence')
        self.assertEqual(universe_pipeline.former_names('The company was formerly known as Example Therapeutics Inc. and changed its name in 2020.'),
                         ['Example Therapeutics Inc'])
        self.assertEqual(universe_pipeline.subsectors('energy_storage','battery and hydrogen storage systems'),
                         ['batteries','hydrogen_storage'])
        self.assertEqual(universe_pipeline.listing_mic({'exchange_mic':'XNAS, XNYS'}, {'provider_exchange':'NASDAQ'}),'XNAS')
        self.assertGreater(registry_verify.similarity('Moderna, Inc.','MODERNA INC'),.99)


if __name__=='__main__':unittest.main()
