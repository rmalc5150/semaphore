import json
import io,hashlib
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock,patch
from zipfile import ZipFile

from public_source_capture import allowed,discover,capture,run
from public_source_scope import in_scope, verify_expected_asset

SOURCE={'source':'fixture','catalog_entry':999,'seeds':['https://official.example/archive/'],'hosts':['official.example'],'scope_note':'fixture'}


def checksum_put(saved):
    def put(**kwargs):
        body=kwargs['Body']
        saved[kwargs['Key']]=body.read() if hasattr(body,'read') else body
        return {'ChecksumSHA256':kwargs.get('ChecksumSHA256')}
    return put


class PublicCaptureTests(unittest.TestCase):
    def test_hkex_links_only_substantive_quote_reports_and_checks_editions(self):
        source = {**SOURCE, 'source':'hkex_prices', 'reviewed_document_discovery':True}
        base = 'https://official.example/eng/stat/smstat/dayquot/'
        links = b'<a href="d261116e.htm">Nov 16</a><a href="d261119e.htm">Nov 19</a><a href="/risk.zip">Risk</a>'
        self.assertEqual([row['url'] for row in discover(links, base+'qtn.asp', source, 0)],
                         [base+'d261119e.htm', base+'d261116e.htm'])
        with TemporaryDirectory() as directory:
            path = Path(directory)/'raw'
            path.write_bytes(b'DATE: 16 NOV 2026 (MONDAY) MAIN BOARD DAILY QUOTATIONS NAME OF STOCK SHARES TRADED')
            self.assertEqual(verify_expected_asset('hkex_prices', base+'d261116e.htm', path, b'')['report_date'],
                             '2026-11-16')
            with self.assertRaisesRegex(ValueError, 'quotation_date_mismatch'):
                verify_expected_asset('hkex_prices', base+'d261119e.htm', path, b'')

    def test_eia_860_requires_year_specific_generator_file(self):
        url = 'https://official.example/electricity/data/eia860/archive/xls/eia8602016.zip'
        with TemporaryDirectory() as directory:
            path = Path(directory)/'raw.zip'
            with ZipFile(path, 'w') as package:
                package.writestr('epa_07_17.xlsx', b'')
            with self.assertRaisesRegex(ValueError, 'missing_annual_generator_workbook'):
                verify_expected_asset('eia_generator_index', url, path, b'')
            with ZipFile(path, 'w') as package:
                package.writestr('3_1_Generator_Y2016.xlsx', b'')
            verify_expected_asset('eia_generator_index', url, path, b'')

    def test_capes_rejects_unrelated_catalogues_and_wrong_csv_schema(self):
        source = 'brazil_capes_theses_and_dissertations'
        base = 'https://official.example/dataset/4b0780eb-5ba4-48d4-8d6a-0b77c56f2fd7/resource/7403d9ac-0e71-4539-bc44-8d7aa7b8f452/download/'
        raw = base+'br-capes-btd-2013a2016-2017-12-01_2016.csv'
        self.assertTrue(in_scope(raw, source))
        self.assertFalse(in_scope(raw.replace('_2016.csv','_2015.csv'), source))
        self.assertFalse(in_scope(base+'br-capes-portal-periodicos-2025.csv', source))
        with self.assertRaisesRegex(ValueError, 'theses_csv_schema_mismatch'):
            verify_expected_asset(source, raw, None, b'AN_REFERENCIA;NR_TC\n2025;8\n')
        verify_expected_asset(source, raw, None, b'AN_BASE;DT_TITULACAO;NM_PRODUCAO\n2016;01/02/2016;X\n')

    def test_pdf_failure_uses_native_last_resort_not_html_scraper(self):
        from test_decodo_web_data import pdf
        from botocore.response import StreamingBody
        from pathlib import Path
        body=pdf();saved={};s3=Mock()
        s3.put_object.side_effect=checksum_put(saved)
        s3.get_object.side_effect=lambda Bucket,Key:{'Body':StreamingBody(io.BytesIO(saved[Key]),len(saved[Key]))}
        response=Mock(status_code=403,headers={});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),patch('pdf_proxy_fallback.settings',return_value={'enabled':True}),patch('pdf_proxy_fallback.eligible',return_value=True),patch('pdf_proxy_fallback.capture',return_value=body)as fallback,patch('collection_storage.StorageSettings.load'),patch('public_source_capture.rendered')as rendered:
            record,_=capture(s3,{**SOURCE,'decodo':True},{'url':'https://official.example/report.pdf','depth':0},'historical')
        self.assertEqual(record['sha256'],hashlib.sha256(body).hexdigest());fallback.assert_called_once();rendered.assert_not_called()
    def test_doe_follows_storage_main_content_not_site_navigation(self):
        source = {**SOURCE, 'source': 'doe_storage_program', 'hosts': ['www.energy.gov']}
        body = b'<html><nav><a href="/history/archive">History</a></nav><main><h1>Energy Storage</h1><a href="/sites/default/files/report.pdf">Storage report</a><a href="/management/history">Department history</a></main></html>'
        found = discover(body, 'https://www.energy.gov/oe/energy-storage', source, 0)
        self.assertEqual([r['url'] for r in found], ['https://www.energy.gov/sites/default/files/report.pdf'])
    def test_single_part_upload_verifies_checksum_without_readback(self):
        body=b'column,value\n2016,42\n';s3=Mock();saved={}
        s3.put_object.side_effect=checksum_put(saved)
        response=Mock(status_code=200,headers={'Content-Type':'text/csv'});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=iter([body])
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'):
            record,_=capture(s3,SOURCE,{'url':SOURCE['seeds'][0],'depth':0},'historical')
        self.assertIn(body,saved.values())
        self.assertEqual(record['sha256'],hashlib.sha256(body).hexdigest())
        s3.get_object.assert_not_called()
        s3.upload_file.assert_not_called()

    def test_multipart_path_keeps_full_readback(self):
        body=b'column,value\n2016,42\n';s3=Mock();saved={}
        def upload(path,bucket,key,ExtraArgs):
            from pathlib import Path
            saved[key]=Path(path).read_bytes()
        from botocore.response import StreamingBody
        s3.upload_file.side_effect=upload;s3.get_object.side_effect=lambda Bucket,Key:{'Body':StreamingBody(io.BytesIO(saved[Key]),len(saved[Key]))}
        response=Mock(status_code=200,headers={'Content-Type':'text/csv'});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=iter([body])
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),patch('public_source_capture.SINGLE_PART_LIMIT',1):
            record,links=capture(s3,SOURCE,{'url':SOURCE['seeds'][0],'depth':0},'historical')
        self.assertEqual(record['sha256'],hashlib.sha256(body).hexdigest());self.assertEqual(record['artifact_kind'],'public_document');self.assertEqual(links,[])
    def test_only_reviewed_https_hosts_and_no_credentials(self):
        for url in ('http://official.example/data.csv','https://official.example.evil/data.csv','https://u:p@official.example/data.csv','https://official.example:444/data.csv'):
            self.assertFalse(allowed(url,SOURCE))
        self.assertTrue(allowed('https://official.example/data.csv',SOURCE))

    def test_archive_links_are_scoped_and_downloads_first(self):
        body=b'<a href="/archive/2020">2020</a><a href="/data.csv">data</a><a href="https://evil.example/a.pdf">bad</a><a href="/login">login</a>'
        found=discover(body,SOURCE['seeds'][0],SOURCE,0)
        self.assertEqual([r['url'] for r in found],['https://official.example/data.csv','https://official.example/archive/2020'])
        self.assertEqual(discover(body,SOURCE['seeds'][0],SOURCE,3),[])

    def test_html_is_not_a_successful_bulk_download(self):
        response=Mock(status_code=200,headers={'Content-Type':'text/html'})
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=iter([b'<html>login</html>'])
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),self.assertRaisesRegex(ValueError,'returned_html'):
            capture(Mock(),{**SOURCE,'asset_only':True},{'url':SOURCE['seeds'][0],'depth':0},'historical')

    def test_failed_request_is_retained_and_not_drained(self):
        writes=[]
        def save(s3,key,body,*a,**kw):
            writes.append(json.loads(body))
            return {'ETag':'"saved"'}
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'worker'}),patch('public_source_capture.read_json',return_value=(None,None)) as read,patch('public_source_capture.put',side_effect=save),patch('public_source_capture.capture',side_effect=ValueError('public_http_503')):
            report=run(SOURCE,'historical',1,s3=Mock())
        read.assert_called_once()
        self.assertFalse(report['route_drained']);self.assertFalse(report['historical_complete']);self.assertEqual(report['failed_urls'],1)
        self.assertTrue(writes[0]['frontier'][0]['retry_after'])

    def test_batches_metadata_receipts_before_one_checkpoint(self):
        source = {**SOURCE, 'seeds': ['https://official.example/one.csv', 'https://official.example/two.csv']}
        def captured(s3, source, entry, mode, *, publish_receipt):
            self.assertFalse(publish_receipt)
            return {'source':'fixture', 'artifact_kind':'public_document', 'source_url':entry['url'],
                    'retrieved_at':'2026-11-20T12:00:00Z','sha256':'abc'}, []
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'controller'}), \
                patch('public_source_capture.read_json',return_value=(None,None)) as read, \
                patch('public_source_capture.put',return_value={'ETag':'"saved"'}) as put, \
                patch('public_source_capture.capture',side_effect=captured):
            report = run(source,'daily',2,Mock(),batch_receipts=True)
        self.assertEqual(report['captured_urls'], 2)
        read.assert_called_once()
        receipts, checkpoint, report = put.call_args_list
        self.assertIn('/athena/', receipts.args[1])
        self.assertEqual(len(receipts.args[2].splitlines()), 2)
        self.assertIn('/states/', checkpoint.args[1])
        self.assertEqual(checkpoint.kwargs, {'IfNoneMatch':'*'})

    def test_failed_receipt_write_does_not_advance_checkpoint(self):
        doc = {'source':'fixture','artifact_kind':'public_document',
               'retrieved_at':'2026-11-20T12:00:00Z','sha256':'abc'}
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'controller'}), \
                patch('public_source_capture.read_json',return_value=(None,None)), \
                patch('public_source_capture.put',side_effect=OSError('receipt write failed')) as put, \
                patch('public_source_capture.capture',return_value=(doc,[])):
            with self.assertRaisesRegex(OSError,'receipt write failed'):
                run(SOURCE,'daily',1,Mock(),batch_receipts=True)
        put.assert_called_once()
        self.assertIn('/athena/', put.call_args.args[1])

    def test_idle_backoff_is_bounded_and_work_resets_it(self):
        from constellation import public_daily_s3_canary as runner
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp, patch.object(runner,'IDLE_STATE',Path(tmp)/'idle.json'), \
                patch.object(runner.time,'time',return_value=1000):
            runner.save_idle_state(2,[{'attempts':0}])
            self.assertEqual(runner.idle_state(),(3,1060))
            runner.save_idle_state(6,[{'attempts':0}])
            self.assertEqual(runner.idle_state(),(6,1300))
            runner.save_idle_state(6,[{'attempts':1}])
            self.assertEqual(runner.idle_state(),(0,1000))

    def test_historical_payload_refuses_controller(self):
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'controller'}),self.assertRaisesRegex(ValueError,'requires_c7i'):
            run(SOURCE,'historical',s3=Mock())

    def test_redirect_to_unreviewed_host_is_rejected(self):
        response=Mock(status_code=302,headers={'Location':'https://evil.example/archive/'})
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),self.assertRaisesRegex(ValueError,'unreviewed_public_redirect'):
            capture(Mock(),SOURCE,{'url':SOURCE['seeds'][0],'depth':0},'historical')

if __name__=='__main__':unittest.main()
