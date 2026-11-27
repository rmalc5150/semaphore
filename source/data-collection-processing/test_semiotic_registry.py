import copy
import tempfile
import unittest

from semiotic_registry import empty, discover, review, save
from semiotic_sandbox import build, encoded
from test_semiotic_sandbox import fixture


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.original = empty()
        self.graph = build(fixture(), self.original)
        self.kw = dict(actor='fixture-reviewer', reason='Synthetic lifecycle test', at='2026-11-18T10:00:00Z')
        self.registry = discover(self.original, self.graph, **self.kw)

    def test_discovery_reuses_ids_and_preserves_input(self):
        self.assertEqual(len(self.registry['entities']), 2)
        self.assertEqual(self.registry, discover(self.registry, self.graph, **self.kw))
        self.assertEqual(self.original, empty())
        graph = build(fixture(), self.registry)
        self.assertEqual({b['status'] for b in graph['tables']['bindings']}, {'provisional'})
        self.assertEqual(graph['tables']['edges'], [])

    def test_promotion_rebinds_and_retains_id(self):
        entity = next(e for e in self.registry['entities'] if e['entity_type'] == 'trial')
        evidence = [a['assertion_id'] for a in self.registry['assertions'] if a['entity_id'] == entity['entity_id']]
        promoted = review(self.registry, entity['entity_id'], action='promote', evidence_ids=evidence, **self.kw)
        graph = build(fixture(), promoted)
        self.assertEqual(graph['tables']['edges'][0]['object_id'], entity['entity_id'])
        self.assertFalse(graph['tables']['edges'][0]['historically_eligible'])
        self.assertEqual(self.registry['entities'][1]['lifecycle_status'], 'provisional')
        self.assertEqual(promoted['parent_snapshot_id'], self.registry['snapshot_id'])
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(save(promoted, directory), save(promoted, directory))

    def test_review_requires_entity_evidence(self):
        entity = self.registry['entities'][0]
        with self.assertRaisesRegex(ValueError, 'evidence'):
            review(self.registry, entity['entity_id'], action='promote', evidence_ids=['invented'], **self.kw)

    def test_rejection_prevents_promotion_and_rediscovery(self):
        entity = self.registry['entities'][0]
        evidence = [a['assertion_id'] for a in self.registry['assertions'] if a['entity_id'] == entity['entity_id']]
        rejected = review(self.registry, entity['entity_id'], action='reject', evidence_ids=evidence, **self.kw)
        self.assertEqual(discover(rejected, self.graph, **self.kw), rejected)
        with self.assertRaisesRegex(ValueError, 'provisional'):
            review(rejected, entity['entity_id'], action='promote', evidence_ids=evidence, **self.kw)

    def test_tampered_registry_and_graph_fail(self):
        broken = copy.deepcopy(self.registry)
        broken['entities'][0]['lifecycle_status'] = 'active'
        with self.assertRaises(ValueError):
            build(fixture(), broken)
        broken = copy.deepcopy(self.graph)
        broken['tables']['mentions'][0]['value'] = 'forged'
        with self.assertRaises(ValueError):
            discover(self.registry, broken, **self.kw)


if __name__ == '__main__':
    unittest.main()
