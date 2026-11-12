import json
import io,hashlib
import os
import unittest
from unittest.mock import Mock,patch

from public_source_capture import allowed,discover,capture,run

SOURCE={'source':'fixture','catalog_entry':999,'seeds':['https://official.example/archive/'],'hosts':['official.example'],'scope_note':'fixture'}

class PublicCaptureTests(unittest.TestCase):
    def test_download_passes_checksum_readback_and_keeps_scratch_open(self):
        body=b'column,value\n2016,42\n';s3=Mock();saved={}
        def upload(path,bucket,key,ExtraArgs):
            from pathlib import Path
            saved[key]=Path(path).read_bytes()
        from botocore.response import StreamingBody
        s3.upload_file.side_effect=upload;s3.get_object.side_effect=lambda Bucket,Key:{'Body':StreamingBody(io.BytesIO(saved[Key]),len(saved[Key]))}
        response=Mock(status_code=200,headers={'Content-Type':'text/csv'});response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.iter_content.return_value=iter([body])
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'):
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
        def save(s3,key,body,*a,**kw):writes.append(json.loads(body))
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'worker'}),patch('public_source_capture.read_json',side_effect=[(None,None),({},'etag')]),patch('public_source_capture.put',side_effect=save),patch('public_source_capture.capture',side_effect=ValueError('public_http_503')):
            report=run(SOURCE,'historical',1,s3=Mock())
        self.assertFalse(report['route_drained']);self.assertFalse(report['historical_complete']);self.assertEqual(report['failed_urls'],1)
        self.assertTrue(writes[0]['frontier'][0]['retry_after'])

    def test_historical_payload_refuses_controller(self):
        with patch.dict(os.environ,{'CONSTELLATION_ROLE':'controller'}),self.assertRaisesRegex(ValueError,'requires_c7i'):
            run(SOURCE,'historical',s3=Mock())

    def test_redirect_to_unreviewed_host_is_rejected(self):
        response=Mock(status_code=302,headers={'Location':'https://evil.example/archive/'})
        with patch('public_source_capture.requests.get',return_value=response),patch('public_source_capture.admit'),self.assertRaisesRegex(ValueError,'unreviewed_public_redirect'):
            capture(Mock(),SOURCE,{'url':SOURCE['seeds'][0],'depth':0},'historical')

if __name__=='__main__':unittest.main()
