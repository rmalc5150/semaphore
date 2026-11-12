import io
import json
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from regulatory_collection import SourceIssue
from ted_packages import index_archive, issue_number, package_xml
from ted_enrichment import enrich_notice
from test_ted_enrichment import TedTests


def archive(entries):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as out:
        for name,raw in entries:
            member=tarfile.TarInfo(name);member.size=len(raw)
            out.addfile(member,io.BytesIO(raw))
    return stream.getvalue()


class PackageTests(unittest.TestCase):
    def test_issue_numbers(self):
        self.assertEqual(issue_number('126/2021'),'202100126')
        self.assertEqual(issue_number(['202100126']),'202100126')
        for bad in ['../bad','https://example.com',[],None]:
            with self.assertRaises(Exception): issue_number(bad)

    def test_package_cached_and_provenance_retained(self):
        raw=archive([('nested/331738_2021.xml',TedTests.raw)])
        response=Mock(status=200,headers={'Content-Length':str(len(raw))})
        response.read=io.BytesIO(raw).read
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        client=Mock(evidence=[])
        def save(raw,url,media):
            client.evidence.append({'source_url':url,'sha256':'xml-sha'})
        client.save.side_effect=save
        with tempfile.TemporaryDirectory() as d, patch('ted_packages.request',return_value=response) as request:
            first,_=package_xml({'ojs-number':'126/2021'},'331738-2021',client,cache=d)
            second,_=package_xml({'ojs-number':'126/2021'},'331738-2021',client,cache=d)
            self.assertEqual(first,second)
            self.assertEqual(first,TedTests.raw)
            self.assertEqual(request.call_count,1)
            self.assertEqual(client.evidence[-1]['package_member'],'nested/331738_2021.xml')
            self.assertIn('archive_sha256',client.evidence[-1]['package_receipt'])
            with self.assertRaisesRegex(Exception,'missing_from_daily_package'):
                package_xml({'ojs-number':'126/2021'},'99-2021',client,cache=d)

    def test_bad_archive_not_cached_as_complete_and_retried_later(self):
        response=Mock(status=202)
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with tempfile.TemporaryDirectory() as d, patch('ted_packages.request',return_value=response) as request:
            for expected in ['http_202','retry_deferred']:
                with self.assertRaisesRegex(Exception,expected):
                    package_xml({'ojs-number':'126/2021'},'331738-2021',Mock(evidence=[]),cache=d)
            self.assertEqual(request.call_count,1)
            with sqlite3.connect(Path(d)/'202100126.sqlite3') as db:
                self.assertEqual(db.execute('SELECT count(*) FROM receipt').fetchone()[0],0)

    def test_daily_bypasses_individual_endpoint(self):
        client=Mock(evidence=[],last_request=0)
        with patch('ted_enrichment.build_opener') as direct, patch('ted_packages.package_xml',return_value=(TedTests.raw,[])):
            data,_=enrich_notice({'ojs-number':'126/2021'},'331738-2021',client,prefer_package=True)
        direct.assert_not_called()
        self.assertEqual(data['enrichment']['retrieval_method'],'daily_xml_package')

    def test_daily_collection_keeps_unavailable_xml_page_pending(self):
        from specialist_inputs import fetch_page
        client=Mock()
        client.json.return_value={'notices':[{'publication-number':'331738-2021','ojs-number':'126/2021'}], 'totalNoticeCount':1}
        job={'adapter':'ted','mode':'daily','parameters':{'url':'https://api.ted.europa.eu/v3/notices/search','query':'x','fields':['publication-number']}}
        with patch('ted_enrichment.enrich_notice',side_effect=SourceIssue('ted_package_http_404')):
            with self.assertRaisesRegex(SourceIssue,'daily_xml_pending'): fetch_page(client,job,None)
        self.assertIn('ojs-number',client.json.call_args.kwargs['body']['fields'])
