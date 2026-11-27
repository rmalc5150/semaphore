"""Synthetic judgments exercise grouping mechanics and tradeoffs."""
from unittest import TestCase

from semiotic_batch import run_batches
from semiotic_grouping import evaluate
from semiotic_sandbox import encoded, sha
from test_semiotic_sandbox import REGISTRY, fixture


class GroupingTests(TestCase):
    def test_grouping_evaluation_and_time_bounded_cross_sector_similarity(self):
        base = fixture()['observations'][0]
        observations = [
            {**base, 'observation_id': key, 'payload': {
                'pages': [{'page': 1, 'text': passage}],
                'sector_classifications': [{'isic_code': code, 'isic_revision': 5}] if code else [],
            }}
            for key, code, passage in (
                ('factory', '27', 'The battery factory expands production.'),
                ('translated', 'C', 'Die Batteriefabrik erweitert ihre Produktion.'),
                ('paraphrase', '27', 'Battery production capacity increases at the plant.'),
                ('repost', '27', 'The battery factory expands production.'),
                ('insurer', '65', 'The insurer covers the same battery factory.'),
                ('furniture', '31', 'The furniture plant expands production.'),
                ('unknown', None, 'No activity specified.'),
                ('future', '27', 'The battery plant opens another production line.'),
            )
        ]
        snapshot = {'environment': 'sandbox', 'observations': observations,
                    'observations_sha256': sha(encoded(observations))}
        first, _ = run_batches([snapshot], REGISTRY, workers=1)
        tables = first['tables']
        evidence = {row['observation_id']: row['id'] for row in tables['evidence_units']}
        embedding_spec = {
            'model_revision': 'synthetic-test-vectors-v1', 'as_of': '2026-11-18T00:00:00Z', 'min_cosine': 0.8,
            'embeddings': [
                {'point_type': 'observation', 'point_id': key, 'model_revision': 'synthetic-test-vectors-v1',
                 'evidence_id': evidence[key], 'eligible_at': eligible_at, 'vector': vector}
                for key, eligible_at, vector in (
                    ('factory', '2026-11-17T00:00:00Z', [1, 0]),
                    ('insurer', '2026-11-17T00:00:00Z', [1, 0.1]),
                    ('furniture', '2026-11-17T00:00:00Z', [0, 1]),
                    ('unknown', None, [1, 0]),
                    ('future', '2026-11-19T00:00:00Z', [1, 0]),
                )
            ],
        }
        release, _ = run_batches([snapshot], REGISTRY, workers=1, similarity_input=embedding_spec)
        tables = release['tables']
        self.assertEqual(first['tables']['industry_groups'], tables['industry_groups'])
        translation = next(row for row in tables['industry_groups'] if row['point_id'] == 'translated')
        self.assertEqual((translation['section_id'], translation['division_ids']), ('isic_C', []))
        group = next(row for row in tables['similarity_groups'] if row['anchor_id'] == 'factory')
        self.assertEqual([row['point_id'] for row in group['members']], ['insurer'])
        self.assertEqual(group['status'], 'similarity_hypothesis')

        pairs = [{'left': 'factory', 'right': right, 'criterion': criterion, 'scenario': scenario, 'level': level}
                 for right, criterion, scenario, level in (
                     ('translated', 'stability', 'translation', 'section'),
                     ('paraphrase', 'stability', 'paraphrase', 'section'),
                     ('repost', 'stability', 'repeat_coverage', 'section'),
                     ('insurer', 'separation', 'distinct_activities', 'section'),
                     ('furniture', 'separation', 'distinct_activities', 'division'),
                     ('translated', 'stability', 'translation', 'division'),
                     ('unknown', 'separation', 'missing_label', 'section'),
                 )]
        jobs = [
            {'anchor': 'factory', 'baseline_ranking': ['insurer', 'translated'], 'relevant': ['translated']},
            {'anchor': 'factory', 'baseline_ranking': ['furniture', 'insurer'], 'relevant': ['insurer']},
        ]
        report = evaluate(tables, {'pairs': pairs, 'retrieval': jobs}, k=1)
        self.assertEqual(sum(row['passed'] for row in report['pairs']), 5)
        self.assertEqual(sum(row['abstained'] for row in report['pairs']), 2)
        first_query, second_query = report['retrieval']['queries']
        self.assertEqual(first_query['baseline']['recall_at_k'], 0)
        self.assertEqual(first_query['isic_reranked']['recall_at_k'], 1)
        self.assertEqual(second_query['isic_reranked']['recall_at_k'], 0)
        self.assertEqual(second_query['similarity_reranked']['recall_at_k'], 1)
