"""Boundary, dependency, evidence and resume tests for disclosure migration."""
from datetime import date
import copy
import json
import tempfile
import unittest
from unittest.mock import Mock

from collection_storage import LocalStore, StorageSettings
from research_contract import ROOT, load_json, validate_record
from regulatory_collection import EvidenceClient, SourceIssue
import disclosure_collection as d


def row(n=1, company="Example Robotics", day="02/06/2024", title="Exclusive licensing agreement"):
    return {"NEWS_ID": str(n), "DATE_TIME": day+" 17:30", "STOCK_NAME": company, "STOCK_CODE": "12345",
            "TITLE": title, "FILE_LINK": f"/listedco/listconews/sehk/2024/0602/{n}.htm", "FILE_TYPE": "HTM"}


def page(rows, total=None):
    total = len(rows) if total is None else total
    return {"result": json.dumps(rows), "recordCnt": total, "loadedRecord": len(rows), "hasNextRow": len(rows) < total}


class Client(EvidenceClient):
    def __init__(self, store, responses=(), documents=None):
        super().__init__(store, "hkex_news", sleeper=lambda _: None)
        self.responses = iter(responses)
        self.documents = documents or {}
        self.calls = []
    def json(self, url, params=None):
        value = next(self.responses)
        self.calls.append((url, params))
        self.save(json.dumps(value).encode(), url)
        return value
    def get(self, url):
        self.calls.append(url)
        value = self.documents[url]
        if isinstance(value, Exception):
            raise value
        return self.save(value, url, "text/html")


class DisclosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.settings = StorageSettings()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.start, self.end = date(2024,6,2), date(2024,6,3)

    def collect(self, responses, **kwargs):
        kwargs.setdefault("capture_documents", False)
        return d.collect_hkex(self.store, self.settings, self.universe, self.taxonomy, self.start, self.end,
            "historical", client=Client(self.store, responses), **kwargs)

    def read(self, result):
        return d.read_inputs(self.store, [result["manifest"]], self.universe, self.taxonomy)[0]

    def derive(self, stage, keys, client=None, **kwargs):
        return d.collect_derived(self.store, self.settings, self.universe, self.taxonomy, self.start, self.end,
            "historical", stage, keys, ["hkex_news"] if stage == "documents" else ["disclosure_documents"], client=client, **kwargs)

    def test_hkex_cumulative_resume_does_not_duplicate_prefix(self):
        first = self.collect([page([row(1)], 2)], page_size=1, max_pages=1)
        self.assertEqual(first["status"], "partial")
        second = self.collect([page([row(1), row(2)])], page_size=1)
        records = self.read(second)
        self.assertEqual(len(records), 2)
        self.assertEqual(len({e['record']['run_id'] for e in records}), 2)
        for entry in records:
            self.assertEqual(validate_record(entry['record'], self.universe), [])
        self.assertTrue(self.collect([], page_size=1)["already_complete"])

    def test_prefix_change_and_source_total_change_fail(self):
        for response, reason in [(page([row(1, title="Changed"),row(2)]), "hkex_prefix_changed"),
                                 (page([row(1),row(2)],3), "source_changed_during_pagination")]:
            with self.subTest(reason=reason):
                self.collect([page([row(1)],2)], max_pages=1, refresh=True)
                result = self.collect([response])
                self.assertEqual(result["reason"], reason)

    def test_stalled_cumulative_page_is_partial(self):
        self.collect([page([row(1)],2)], max_pages=1)
        self.assertEqual(self.collect([page([row(1)],2)])["status"], "partial")

    def test_wrong_date_duplicate_identity_and_untrusted_link_rejected(self):
        for rows in ([row(day="03/06/2024")], [row(1),row(1)], [{**row(),"FILE_LINK":"https://example.test/doc.pdf"}]):
            self.assertEqual(self.collect([page(rows)], refresh=True)["status"], "failed")

    def test_zero_requires_explicit_provider_completion(self):
        self.assertEqual(self.collect([page([])])["records"],0)
        value=page([]);value.pop('hasNextRow')
        self.assertEqual(self.collect([value],refresh=True)["status"],"failed")

    def test_all_sector_members_and_unknown_discovery_retained(self):
        rows=[row(i+1,c['canonical_name']) for i,c in enumerate(self.universe['companies'])]+[row(9,'Unknown institution')]
        result=self.collect([page(rows)])
        entries=self.read(result)
        self.assertEqual(len(entries),5)
        self.assertEqual({s for e in entries for s in e['record']['payload']['candidate_sector_ids']},set(d.SECTORS))
        result=self.collect([page(rows)],selection='universe',sectors=['robotics'])
        self.assertEqual(result['records'],1)

    def test_partial_or_uncommitted_prerequisite_rejected(self):
        partial=self.collect([page([row()],2)],max_pages=1)
        with self.assertRaisesRegex(SourceIssue,'not_complete'):
            self.derive('documents',[partial['manifest']])
        complete=self.collect([page([row(),row(2)])])
        final=json.loads(self.store.get(complete['manifest']).body)
        path=self.store.root/'checkpoints'/final['task_id']/'head.json'
        head=json.loads(path.read_text());head['terminal_history']=[];path.write_text(json.dumps(head))
        with self.assertRaisesRegex(SourceIssue,'not_committed'):
            self.read(complete)

    def test_missing_source_or_window_gap_rejected(self):
        result=self.collect([page([row()])])
        _,_,manifests=d.read_inputs(self.store,[result['manifest']],self.universe,self.taxonomy)
        with self.assertRaisesRegex(SourceIssue,'source_set'):
            d.check_coverage(manifests,self.start,self.end,['sec_edgar','hkex_news'])
        with self.assertRaisesRegex(SourceIssue,'window_gap'):
            d.check_coverage(manifests,self.start,date(2024,6,4),['hkex_news'])

    def test_document_resume_then_candidates_preserve_lineage(self):
        filings=self.collect([page([row(1),row(2)])])
        urls=[entry['record']['source_url'] for entry in self.read(filings)]
        documents={url:b'<html><body>Example Robotics signs an exclusive license agreement for robot control technology.</body></html>' for url in urls}
        first=self.derive('documents',[filings['manifest']],Client(self.store,documents=documents),max_records=1)
        self.assertEqual(first['status'],'partial')
        second_client=Client(self.store,documents=documents)
        second=self.derive('documents',[filings['manifest']],second_client)
        self.assertEqual(len(second_client.calls),1)
        self.assertEqual(second['records'],2)
        candidates=self.derive('licensing-agreements',[second['manifest']])
        records=self.read(candidates)
        self.assertEqual(len(records),2)
        self.assertTrue(all(e['record']['payload']['data']['review_status']=='unreviewed' for e in records))
        self.assertTrue(all(e['record']['payload']['prerequisite']['manifest']==second['manifest'] for e in records))
        self.assertTrue(all(e['record']['available_at'] is None for e in records))

    def test_failed_document_is_not_an_empty_success(self):
        filings=self.collect([page([row()])]);url=self.read(filings)[0]['record']['source_url']
        result=self.derive('documents',[filings['manifest']],Client(self.store,documents={url:b'<title>Access denied</title>'}))
        self.assertEqual(result['status'],'failed')
        with self.assertRaisesRegex(SourceIssue,'not_complete'):
            self.derive('ma-announcements',[result['manifest']])

    def test_hkex_captures_original_and_processing_reuses_it(self):
        source = row()
        url = d.urljoin(d.HKEX_API, source['FILE_LINK'])
        raw = b'<html><body>Example Robotics signs an exclusive license agreement for robot technology.</body></html>'
        client = Client(self.store, [page([source])], {url: raw})
        result = d.collect_hkex(self.store, self.settings, self.universe, self.taxonomy,
            self.start, self.end, 'historical', client=client)
        self.assertEqual(result['status'], 'complete')
        payload = self.read(result)[0]['record']['payload']
        captured = payload['document_capture']
        self.assertEqual(captured['bytes'], len(raw))
        self.assertEqual(self.store.get(captured['source_evidence'][0]['key']).body, raw)
        self.assertEqual(len(payload['source_evidence']), 2)
        offline = Client(self.store)
        derived = self.derive('documents', [result['manifest']], offline)
        self.assertEqual(derived['status'], 'complete')
        self.assertEqual(offline.calls, [])
        self.assertIn('exclusive license', self.read(derived)[0]['record']['payload']['data']['text'])

    def test_hkex_download_failure_resumes_without_metadata_only_success(self):
        source = {**row(), 'FILE_TYPE': 'PDF'}
        url = d.urljoin(d.HKEX_API, source['FILE_LINK'])
        for value in (SourceIssue('source_http_503'), b'<html>Access denied</html>'):
            client = Client(self.store, [page([source])], {url: value})
            result = d.collect_hkex(self.store, self.settings, self.universe, self.taxonomy,
                self.start, self.end, 'historical', client=client)
            self.assertEqual(result['status'], 'failed')
        raw = b'%PDF-1.7\noriginal report bytes'
        result = d.collect_hkex(self.store, self.settings, self.universe, self.taxonomy,
            self.start, self.end, 'historical', client=Client(self.store, [page([source])], {url: raw}))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.read(result)), 1)

    def test_source_evidence_corruption_rejected(self):
        result=self.collect([page([row()])]);record=self.read(result)[0]['record']
        path=self.store.root/record['payload']['source_evidence'][0]['key'];path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(SourceIssue,'checksum'):
            self.read(result)

    def test_sec_submission_identity_exhibits_and_hidden_text(self):
        parent={'source':'sec_edgar','source_record_id':'0000000001-24-000001','payload':{'form':'8-K'}}
        body=b'ACCESSION NUMBER: 0000000001-24-000001\n<DOCUMENT><TYPE>8-K\n<TEXT><html><script>bad merger</script>Example company issues a detailed operating update to its investors.</html></TEXT></DOCUMENT><DOCUMENT><TYPE>EX-99.1\n<TEXT>Exclusive license agreement signed for a battery storage technology.</TEXT></DOCUMENT>'
        text,info=d.document_text(body,parent)
        self.assertNotIn('bad merger',text)
        self.assertIn('battery storage',text)
        self.assertEqual(info['text_documents'],2)
        with self.assertRaisesRegex(SourceIssue,'identity'):
            d.document_text(body.replace(b'24-000001',b'24-000002'),parent)

    def test_strategic_candidate_has_no_biotech_gate_or_claimed_economics(self):
        for sector in ['semiconductor','robotics','thermal storage','hydrogen storage','biotech']:
            parent={'payload':{'data':{'text':f'Alpha acquires a {sector} company under a proposed agreement.'}}}
            self.assertTrue(d.candidate('strategic-transactions',parent))


if __name__=='__main__':unittest.main()
