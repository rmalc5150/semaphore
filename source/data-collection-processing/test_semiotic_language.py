from unittest import TestCase
from unittest.mock import patch

from semiotic_batch import extract
from semiotic_coverage import numerical_tables
from semiotic_language import analyze_chunk, analyze_passages, subject_frequency, token_frequency
from semiotic_sandbox import encoded, sha
from test_semiotic_sandbox import REGISTRY, fixture


class LanguageTests(TestCase):
    def test_missing_table_structure_is_distinct_from_checked_empty(self):
        observation = fixture()['observations'][0]
        self.assertEqual(numerical_tables(observation), ([], 'table_structure_not_supplied'))
        observation['payload']['tables'] = []
        self.assertEqual(numerical_tables(observation), ([], 'no_numeric_tables_in_supplied_structure'))

    def test_source_location_is_distinct_from_addressed_region(self):
        snapshot = fixture()
        row = snapshot['observations'][0]
        row['source_key'] = 'sec_edgar'
        text = 'Acme prevé mayor demanda en Alemania.'
        row['payload']['pages'] = [{'page': 1, 'text': text}]
        row['raw_artifacts'] = [{'artifact_kind': 'primary_document'}]
        row['quality_flags'] = ['historical_vintages_unknown']
        row['payload']['tables'] = [{
            'locator': {'page': 2, 'table': 1}, 'reporting_methodology': 'Survey of adult residents',
            'methodology_evidence': {'page': 2, 'section': 'Methods'},
            'columns': [{'label': 'Demand', 'unit': '%'}, {'label': 'Sample size'}],
            'rows': [['12%', 200], ['15%', 220]],
        }]
        snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
        candidate = {'triples': [{'subject': 'Acme', 'verb': 'prevé', 'object': 'mayor demanda', 'quote': text,
                                 'subject_en': 'Acme', 'verb_en': 'expects', 'object_en': 'demand to rise'}],
                     'tone': 'uncertain', 'tone_quote': text,
                     'original_language': 'es', 'english_text': 'Acme expects demand to rise in Germany.',
                     'extraction_confidence': 'medium',
                     'geographic_coverage': [{'label': 'Alemania', 'quote': text}], 'population_coverage': [],
                     'sector_classifications': [{'sector_id': 'robotics', 'subsector_id': None, 'quote': text}]}
        options = {'model': 'test-model', 'port': 8080,
                   'source_regions': {'sec_edgar': {'region': 'US', 'reference': 'fixture:source-registry'}}}
        with patch('semiotic_language.infer', return_value=candidate):
            graph, events, _ = extract(snapshot, REGISTRY, 100000, options)
        language = graph['tables']['language_candidates'][0]
        geography = graph['tables']['observation_geography'][0]
        self.assertEqual(language['tone'], 'uncertain')
        self.assertEqual(language['word_count'], 6)
        self.assertEqual(geography['source_region'], 'US')
        self.assertEqual(geography['geographic_coverage'], ['Alemania'])
        evidence = language['triples'][0]['evidence']
        self.assertEqual(text[evidence['start']:evidence['end']], evidence['quote'])
        summary = subject_frequency([language])[0]
        self.assertEqual(summary['verb_objects'], [{'verb': 'expects', 'object': 'demand to rise', 'mentions': 1}])
        tokens = {item['token'] for item in token_frequency([language])}
        self.assertIn('germany', tokens)
        self.assertNotIn('alemania', tokens)
        profile = graph['tables']['observation_profiles'][0]
        self.assertEqual(profile['original_language'], 'es')
        self.assertEqual(profile['evidence_types'], ['primary_document'])
        self.assertEqual(profile['coverage_flags'], ['historical_vintages_unknown'])
        self.assertEqual(profile['extraction_confidence'], 'medium')
        self.assertIn('population_coverage', profile['missingness_flags'])
        table = graph['tables']['numerical_tables'][0]
        self.assertEqual(table['numeric_columns'][0]['unit'], '%')
        self.assertEqual(table['missingness_flags'], ['unit_not_supplied:1'])
        self.assertEqual(table['reporting_methodology'], 'Survey of adult residents')
        self.assertEqual({row['point_type'] for row in graph['tables']['sector_attributions']},
                         {'observation', 'chunk', 'claim'})
        self.assertTrue(all(row['status'] == 'candidate' and row['eligible_at'] is None
                            for row in graph['tables']['sector_attributions']))
        self.assertEqual(events, [])

    def test_rejects_model_quote_missing_from_chunk(self):
        chunk = {'text': 'Acme grew.', 'id': 'chunk', 'start': 0, 'page': 1, 'observation_id': 'obs'}
        with patch('semiotic_language.infer', return_value={
                'triples': [], 'tone': 'neutral', 'tone_quote': 'invented',
                'original_language': 'en', 'english_text': 'Acme grew.', 'extraction_confidence': 'low',
                'geographic_coverage': [], 'population_coverage': []}):
            with self.assertRaisesRegex(ValueError, 'exactly once'):
                analyze_chunk(chunk, 'test-model', 8080)

    def test_parallel_inference_preserves_passage_order_and_records_abstentions(self):
        chunks = [{'text': value, 'id': str(index), 'observation_id': 'obs', 'start': 0, 'page': 1}
                  for index, value in enumerate(('Acme grew.', 'Atlas shrank.', '123'))]

        def infer(text, _model, _port, *, timeout):
            self.assertEqual(timeout, 240)
            if text == 'Atlas shrank.':
                raise TimeoutError()
            return {'triples': [], 'tone': 'neutral', 'tone_quote': 'unsupported',
                    'original_language': 'en', 'english_text': '', 'extraction_confidence': 'low',
                    'geographic_coverage': [], 'population_coverage': []}

        with patch('semiotic_language.infer', side_effect=infer):
            outcomes = list(analyze_passages(chunks, {'model': 'test-model', 'port': 8080,
                                                     'record_invalid': True, 'parallel': 2, 'timeout': 240}))
        self.assertEqual([row['chunk_id'] if row else failure['chunk_id'] for row, failure in outcomes],
                         ['0', '1', '2'])
        self.assertEqual(outcomes[0][0]['validation_issues'][0]['field'], 'tone')
        self.assertEqual(outcomes[0][0]['english_text'], 'Acme grew.')
        self.assertEqual(outcomes[1][1]['error_type'], 'TimeoutError')
