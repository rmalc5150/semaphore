"""Offline prosecution paging, document evidence and scheduler recovery tests."""
from copy import deepcopy
from datetime import date
import hashlib
import io
from urllib.error import HTTPError
import json
import tempfile
import unittest
from pathlib import Path

from collection_storage import StorageSettings, write_checked
from research_contract import ROOT, load_json, seal_record, validate_record
import patent_prosecution as p
from patent_prosecution_operations import Operations


def action(index=0, **extra):
    return {'id': f'provider-{index}', 'patentApplicationNumber': ['15123456'],
        'obsoleteDocumentIdentifier': [f'doc-{index}'], 'submissionDate': '2021-01-04T00:00:00',
        'legacyDocumentCodeIdentifier': ['CTNF'], 'bodyText': ['robot claim rejection'],
        'lastModifiedTimestamp': '2026-10-13T12:00:00', **extra}


def petition(index=0, **extra):
    return {'petitionDecisionRecordIdentifier': f'petition-{index}', 'applicationNumberText': '15123456',
        'decisionDate': '2021-01-04', 'finalPetitionDecisionIndicator': True,
        'documentBag': [document(f'doc-{index}')], **extra}


def document(identity):
    return {'documentIdentifier': identity, 'documentCode': 'PETDEC', 'downloadOptionBag': [
        {'mimeTypeIdentifier': 'PDF', 'downloadUrl': f'{p.BASE}/api/v1/download/applications/15123456/{identity}.pdf'}]}


class FakeClient:
    def __init__(self, store, rows):
        self.store, self.rows = store, rows
        self.evidence, self.calls, self.downloads = [], [], []
        self.failure = None
        self.total = None

    def save(self, raw, url):
        checksum = hashlib.sha256(raw).hexdigest()
        key = f'source_documents/uspto_odp/{checksum}'
        write_checked(self.store, key, raw)
        self.evidence.append({'key': key, 'sha256': checksum, 'bytes': len(raw), 'url': url})

    def search(self, dataset, criteria, offset, size):
        self.calls.append(offset)
        rows = deepcopy(self.rows[offset:offset+size])
        self.save(json.dumps(rows).encode(), p.BASE+'/search')
        return len(self.rows) if self.total is None else self.total, rows

    def documents(self, application):
        docs = [document(f'doc-{i}') for i in range(10)]
        self.save(json.dumps(docs).encode(), p.BASE+'/documents')
        return docs

    def request(self, url, pdf=False):
        self.downloads.append(url)
        if self.failure and self.failure in url:
            raise p.SourceIssue('source_http_503', True)
        raw = b'%PDF-1.0 '+url.encode()
        self.save(raw, url)
        return raw


class Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.settings = StorageSettings(local_root=tmp.name)
        self.store = self.settings.store()
        self.universe = load_json(ROOT/'examples/sec-filings/universe.json')
        self.taxonomy = load_json(ROOT/'config/sectors.v1.json')
        self.start, self.end = date(2021,1,4), date(2021,1,5)

    def collect(self, client, dataset=p.DATASETS[0], **kw):
        return p.collect(self.store, self.settings, self.universe, self.taxonomy, dataset,
            self.start, self.end, client=client, page_size=kw.pop('page_size',1), **kw)

    def records(self, result):
        manifest = json.loads(self.store.get(result['manifest']).body)
        return [json.loads(line) for page in manifest['pages'] for batch in page['batches']
                for line in self.store.get(batch['key']).body.splitlines()]

    def test_older_application_original_pdf_and_unknown_availability(self):
        c=FakeClient(self.store,[action()]); r=self.collect(c)
        self.assertEqual(r['status'],'complete')
        row=self.records(r)[0]; d=row['payload']['data']
        self.assertEqual(d['application_number'],'15123456')
        self.assertIsNone(row['available_at'])
        self.assertEqual(d['document_retrieval_status'],'downloaded')
        self.assertTrue(self.store.get(d['documents'][0]['key']).body.startswith(b'%PDF'))
        self.assertEqual(validate_record(row,self.universe),[])

    def test_partial_resume_and_completed_skip(self):
        c=FakeClient(self.store,[action(0),action(1),action(2)])
        first=self.collect(c,max_pages=1); self.assertEqual(first['status'],'partial')
        c.calls=[]; done=self.collect(c,max_pages=5)
        self.assertEqual(done['records'],3)
        self.assertEqual(c.calls[:2],[0,0])
        self.assertEqual(len(c.downloads),3)
        c.calls=[]; skip=self.collect(c)
        self.assertTrue(skip['already_complete']); self.assertEqual(c.calls,[])

    def test_failed_second_download_reuses_first_pdf(self):
        c=FakeClient(self.store,[action(0),action(1)]); c.failure='doc-1.pdf'
        fail=self.collect(c,page_size=2)
        self.assertEqual(fail['status'],'partial'); self.assertEqual(fail['records'],0)
        self.assertEqual(fail['reason'],'source_http_503')
        c.failure=None; done=self.collect(c,page_size=2)
        self.assertEqual(done['records'],2)
        self.assertEqual(sum('doc-0.pdf' in u for u in c.downloads),1)

    def test_changed_count_requires_refresh(self):
        c=FakeClient(self.store,[action(0),action(1)]); self.collect(c,max_pages=1)
        c.total=3
        fail=self.collect(c)
        self.assertEqual(fail['reason'],'source_changed_refresh_required')
        self.assertEqual(fail['records'],1)

    def test_same_count_changed_boundary_rejected(self):
        c=FakeClient(self.store,[action(0),action(1)]); self.collect(c,max_pages=1)
        c.rows[0]['bodyText']=['corrected']
        fail=self.collect(c)
        self.assertEqual(fail['reason'],'source_changed_refresh_required')

    def test_duplicate_document_and_ignored_date_filter_rejected(self):
        c=FakeClient(self.store,[action(0),action(0)])
        self.assertEqual(self.collect(c,page_size=2)['reason'],'duplicate_provider_document')
        c=FakeClient(self.store,[action(0,submissionDate='2020-12-31T00:00:00')])
        self.assertEqual(self.collect(c,page_size=2,refresh=True)['reason'],'source_ignored_date_filter')

    def test_final_petition_scope_and_multiple_documents(self):
        c=FakeClient(self.store,[petition(documentBag=[document('doc-0'),document('doc-1')])])
        r=self.collect(c,dataset=p.DATASETS[1])
        self.assertEqual(r['status'],'complete')
        self.assertEqual(len(self.records(r)[0]['payload']['data']['documents']),2)
        _, q=p.query(p.DATASETS[1],self.start,self.end,'historical')
        self.assertIn('finalPetitionDecisionIndicator:true',q)
        c.rows=[petition(finalPetitionDecisionIndicator=False)]
        self.assertEqual(self.collect(c,dataset=p.DATASETS[1],refresh=True)['reason'],'source_ignored_final_filter')

    def test_refresh_retains_old_evidence_and_refetches_correction(self):
        c=FakeClient(self.store,[action()]); old=self.collect(c)
        c.rows[0]['bodyText']=['corrected robot text']
        fresh=self.collect(c,refresh=True)
        self.assertEqual(len(c.downloads),2)
        self.assertEqual(self.records(old)[0]['record_id'],self.records(fresh)[0]['record_id'])
        self.assertNotEqual(self.records(old)[0]['payload_hash'],self.records(fresh)[0]['payload_hash'])
        self.assertEqual(self.records(old)[0]['payload']['data']['first_observed_at'],
            self.records(fresh)[0]['payload']['data']['first_observed_at'])

    def test_corrupt_cached_pdf_cannot_complete(self):
        c=FakeClient(self.store,[action()]); done=self.collect(c)
        key=self.records(done)[0]['payload']['data']['documents'][0]['key']
        (self.store.root/key).write_bytes(b'bad')
        fail=self.collect(c,refresh=True)
        self.assertEqual(fail['reason'],'corrupt_cached_document')

    def test_schema_prevents_missing_document_evidence(self):
        c=FakeClient(self.store,[action()]); row=self.records(self.collect(c))[0]
        row['payload']['data']['documents']=[]; row=seal_record(row)
        self.assertTrue(validate_record(row,self.universe))

    def test_safe_url_and_request_budget_without_credentials(self):
        c=p.Client(self.store,key_loader=lambda:self.fail('credential should not load'))
        with self.assertRaises(p.SourceIssue):c.request('https://other.example/x',pdf=True)
        c=p.Client(self.store,key_loader=lambda:'fixture',max_requests=0,gate=lambda:None)
        with self.assertRaises(p.SourceIssue):c.request(p.OA_PATH+'/fields')

    def test_empty_search_404_is_distinct_from_unknown_route(self):
        raw=b'{"detailedMessage":"No matching records found, refine your search criteria and try again"}'
        def empty(req,timeout):raise HTTPError(req.full_url,404,'missing',{},io.BytesIO(raw))
        c=p.Client(self.store,key_loader=lambda:'fixture',opener=empty,gate=lambda:None)
        total, rows=c.search(p.DATASETS[1],'query',0,1)
        self.assertEqual((total,rows),(0,[]))
        self.assertTrue(c.evidence)
        def missing(req,timeout):raise HTTPError(req.full_url,404,'missing',{},io.BytesIO(b'{}'))
        c.opener=missing
        with self.assertRaises(p.SourceIssue):c.search(p.DATASETS[1],'query',0,1)

    def test_pdf_redirect_strips_credentials_and_does_not_save_signed_url(self):
        calls=[]
        class Response(io.BytesIO):headers={}
        def opener(req,timeout):
            calls.append(req)
            if len(calls)==1:
                raise HTTPError(req.full_url,302,'redirect',{'Location':'https://data-documents.uspto.gov/file.pdf?signature=private'},io.BytesIO())
            return Response(b'%PDF-1.0 example')
        c=p.Client(self.store,key_loader=lambda:'fixture-secret',opener=opener,gate=lambda:None)
        c.request(p.BASE+'/api/v1/download/applications/15123456/doc.pdf',pdf=True)
        self.assertEqual(calls[0].get_header('X-api-key'),'fixture-secret')
        self.assertIsNone(calls[1].get_header('X-api-key'))
        self.assertNotIn('private',str(c.evidence))
        self.assertNotIn('fixture-secret',str(c.evidence))
        def unsafe(req,timeout):raise HTTPError(req.full_url,302,'redirect',{'Location':'https://other.example/file.pdf'},io.BytesIO())
        c.opener=unsafe
        with self.assertRaises(p.SourceIssue):c.request(p.BASE+'/api/v1/download/applications/15123456/doc.pdf',pdf=True)

    def test_typed_publication_preserves_document_joins_and_verifies_pdf(self):
        import pyarrow.parquet as pq
        from patent_prosecution_athena import prepare
        from research_publication import discover
        c=FakeClient(self.store,[action()]); done=self.collect(c)
        config=load_json(ROOT/'config/patent-office-actions-athena.json')
        config['source_manifests']=[done['manifest']]
        root=prepare(self.store,self.settings,config,self.store.root/'release')
        rows=pq.read_table(root/'tables/source_observations/part-00000.parquet').to_pylist()
        self.assertEqual(rows[0]['application_number'],'15123456')
        self.assertEqual(rows[0]['official_document_id'],'doc-0')
        self.assertFalse(rows[0]['point_in_time_eligible'])
        write_checked(self.store,'checkpoints/task_'+'a'*64+'/head.json',b'unrelated legacy checkpoint')
        self.assertEqual(discover(self.store,self.settings,owners=list(p.DATASETS))['patent_office_actions'],1)
        self.assertEqual(discover(self.store,self.settings,owners=list(p.DATASETS))['patent_office_actions'],0)
        key=self.records(done)[0]['payload']['data']['documents'][0]['key']
        (self.store.root/key).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'Source evidence checksum mismatch'):
            prepare(self.store,self.settings,config,self.store.root/'release2')

    def test_empty_window_completes_and_scheduler_keeps_datasets_separate(self):
        c=FakeClient(self.store,[])
        cfg={'start_date':'2021-01-01','historical_end_exclusive':'2021-01-03','page_size':1,
            'max_windows':1,'max_pages':1,'max_requests':20,'max_download_bytes':10000,'restart_cooldown_hours':6}
        ops=Operations(self.store,self.settings,cfg,self.universe,self.taxonomy,c)
        a=ops.run(p.DATASETS[0],'historical',date(2021,1,4))
        self.assertEqual(a['next_date'],'2021-01-02')
        self.assertIsNone(ops.status()['datasets'][p.DATASETS[1]]['historical'])
        ops.run(p.DATASETS[1],'historical',date(2021,1,4))
        self.assertEqual(ops.status()['datasets'][p.DATASETS[1]]['historical']['next_date'],'2021-01-02')


if __name__=='__main__':unittest.main()
