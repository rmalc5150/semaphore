from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_storage import CollectionRun, StorageSettings, task_spec
from personnel_archive import collect, match_terms, retrieval_context
from people_social_collection import record, event_timestamp
from regulatory_collection import EvidenceClient
from research_contract import ROOT, load_json
from source_observation_athena import prepare


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); self.settings = StorageSettings(local_root=str(self.root / 'store'), s3_bucket='test')
        self.store = self.settings.store()
        self.u = load_json(ROOT / 'examples/sec-filings/universe.json'); self.t = load_json(ROOT / 'config/sectors.v1.json')

    def parent(self, titles=None):
        spec = task_spec('marketaux', 'news_articles', 'historical', '2021-01-01T00:00:00Z', '2021-01-02T00:00:00Z', {}, 'test', self.u, self.t)
        run = CollectionRun.start(self.store, spec, self.u, self.t, self.settings)
        client = EvidenceClient(self.store, 'marketaux'); client.save(b'original provider response', 'https://example.com/archive')
        rows = [record(run, str(i), 'https://example.com/' + str(i), {'title': title},
                       event_timestamp('2021-01-01T01:00:00Z'), client.evidence, 'test') for i, title in enumerate(titles or [
                           'Robotics company appoints chief technology officer', 'Trial recruits 20 participants'])]
        run.commit_page(rows, next_cursor=None, exhausted=True)
        return run.finish('complete', expected_records=len(rows)), client.evidence[0]['key']

    def test_retrieval_preserves_parent_and_curates(self):
        key, _ = self.parent(); result = collect(self.store, self.settings, key)
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual((result['input_records'], result['records']), (2, 1))
        cfg = load_json(ROOT / 'config/people-observations-athena.json')
        root = prepare(self.store, self.settings, {**cfg, 'source_manifests': [result['manifest']]}, self.root / 'build')
        self.assertEqual(load_json(root / 'release.json')['files']['source_observations']['rows'], 1)
        self.assertTrue(collect(self.store, self.settings, key)['already_complete'])

    def test_corrupt_source_rejected(self):
        key, evidence_key = self.parent()
        obj = self.store.get(evidence_key)
        self.store.put(evidence_key, b'corrupt', expected=obj.token)
        with self.assertRaises(Exception):
            collect(self.store, self.settings, key)

    def test_retrieval_not_clinical_recruitment(self):
        self.assertFalse(match_terms({'payload': {'data': {'text': 'The clinical trial recruits patients.'}}}))
        self.assertTrue(match_terms({'payload': {'data': {'text': 'Item 5.02 Departure of directors'}}}))
        self.assertTrue(match_terms({'payload': {'title': '董事辭任'}}))
        self.assertFalse(match_terms({'payload': {'data': {'text': 'The trial joins a network.' + 'x' * 500 + 'chief investigator'}}}))

    def test_reviewed_workforce_misses_and_context(self):
        for text in [
            'OpenAI has expanded its robotics hiring, listing 27 roles, up from 11 in May',
            'Amazon Turns To Former Employees, Including Those Laid-Off, For AI, Cloud Jobs',
            'Company names Jane Smith chief technology officer',
        ]:
            self.assertTrue(match_terms({'payload': {'data': {'text': text}}}), text)
        row={'payload':{'data':{'text':'Redeploy affected workers without layoffs'},'candidate_sector_ids':['energy_storage']}}
        self.assertIn('negated_or_avoided_layoffs',retrieval_context(row))
        self.assertIn('search_sector_is_not_verified_company_sector',retrieval_context(row))
        self.assertFalse(match_terms({'payload': {'title':'Chief scientist discusses trial recruitment'}}))

    def test_interrupted_candidate_batches_resume_without_duplicates(self):
        key, _ = self.parent(['Company appoints chief engineer'] * 70)
        original = CollectionRun.commit_page
        calls = 0
        def interrupted(run, records, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return original(run, records, **kwargs)
        with patch.object(CollectionRun, 'commit_page', interrupted):
            result = collect(self.store, self.settings, key)
        self.assertEqual(result['status'], 'partial', result)
        result = collect(self.store, self.settings, key)
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(result['records'], 70)
        cfg = load_json(ROOT / 'config/people-observations-athena.json')
        root = prepare(self.store, self.settings, {**cfg, 'source_manifests': [result['manifest']]}, self.root / 'build')
        self.assertEqual(load_json(root / 'release.json')['files']['source_observations']['rows'], 70)


if __name__ == '__main__':
    unittest.main()
