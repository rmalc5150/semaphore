from unittest import TestCase
from unittest.mock import Mock, patch

from semiotic_hybrid import annotate_release, scope_pass, targeted
from semiotic_industry import entity_industry_context, source_fallback
from semiotic_specialists import Language, ask, segments, span
from semiotic_structured import html_tables, ted_xml


class HybridTests(TestCase):
    def test_ted_geography_preserves_place_of_performance_role(self):
        document = b'''<ContractAwardNotice><NoticeLanguageCode>RON</NoticeLanguageCode>
            <Buyer><Address><Country><IdentificationCode>LUX</IdentificationCode></Country></Address></Buyer>
            <ProcurementProjectLot><ID>LOT-0001</ID><RealizedLocation><Address><Country>
                <IdentificationCode>ROU</IdentificationCode></Country></Address></RealizedLocation>
            </ProcurementProjectLot><TotalAmount currencyID="RON">123.00</TotalAmount></ContractAwardNotice>'''
        items = list(ted_xml(document, {'sha256': 'fixture'}))
        locations = [item['value'] for item in items if item['field'] == 'geographic_coverage']
        self.assertEqual(locations, [{'role': 'place_of_performance', 'name': 'ROU',
                                      'code_system': 'ISO 3166-1 alpha-3'}])
        self.assertTrue(all(item['locator']['artifact_sha256'] == 'fixture' for item in items))
        self.assertEqual(next(item['value']['unit'] for item in items if item['field'] == 'reported_amount'), 'RON')

    def test_segmentation_preserves_source_offsets(self):
        text = 'One sentence. Another sentence. And a final clause.'
        excerpts = list(segments(text, 17))
        self.assertEqual(''.join(text[start:end] for start, end in excerpts), text)
        self.assertTrue(all(end - start <= 17 for start, end in excerpts))

    def test_native_html_numeric_cells_keep_header_units_and_locator(self):
        document = b'<html><table><tr><th>Depth (km)</th></tr><tr><td>12.5</td></tr></table></html>'
        row, = html_tables(document, {'sha256': 'fixture'})
        self.assertEqual(row['locator']['path'], '/html/body/table')
        self.assertEqual(row['value']['cells'], [{'row': 2, 'column': 1, 'value': '12.5',
                                                  'column_label': 'Depth (km)', 'unit': 'km'}])

    def test_chinese_passage_routes_translation_without_whitespace_tokens(self):
        text = '我国电子信息制造业生产快速增长出口持续上行。'
        page = {'page': 1, 'text': text, 'artifact_sha256': 'original'}
        language = Language.__new__(Language)
        language.detector = Mock()
        language.detector.predict.side_effect = lambda texts, k: (
            ([['__label__zh']], [[0.99]]) if texts == [text] else ([['__label__en']], [[0.99]]))
        language.translate = Mock(return_value=['Electronics manufacturing production rose.'])
        language.translation_version = 'translation-fixture'
        result = language.analyze([page], 'zh-Hans')
        language.translate.assert_called_once_with([text], 'zh')
        translation, = [row for row in result['values'] if row['field'] == 'english_text']
        self.assertEqual(translation['locator'], span(page, 0, len(text)))
        self.assertEqual(translation['source_language'], 'zh')

    def test_translated_thesis_keeps_original_passage_and_model_quote(self):
        page = {'page': 1, 'text': '制造业增加值增长。', 'artifact_sha256': 'original'}
        translation = {'value': 'Manufacturing value added increased.', 'method': 'translation-fixture',
                       'source_language': 'zh', 'locator': span(page, 0, len(page['text']))}
        model_message = b'{"choices":[{"finish_reason":"stop","message":{"content":"{\\"value\\":\\"Manufacturing value added rose.\\",\\"quote\\":\\"value added increased\\"}"}}]}'
        with patch('semiotic_specialists.HTTPConnection') as connector:
            response = connector.return_value.getresponse.return_value
            response.status = 200
            response.read.return_value = model_message
            result = ask(page, 0, len(page['text']), 'thesis', 'fixture-thesis', 18082, english=translation)
        self.assertEqual(result['locator'], translation['locator'])
        self.assertEqual(result['english_evidence_quote'], 'value added increased')
        self.assertEqual(result['evidence_alignment'], 'passage')

    def test_targeted_thesis_routes_to_separate_model_and_blocks_missing_translation(self):
        page = {'page': 1, 'text': 'Texto del documento original.'}
        observation = {'source_key': 'example', 'payload': {}, 'extracted_pages': [page],
                       'semiotic_source_profile': {'input_kind': 'document'}}
        empty = {'a': {'values': []}}
        blocked = targeted({'a': observation}, empty, empty, empty, 'general', 18081, None)
        self.assertEqual(blocked['a']['attempts']['thesis'], 'blocked')
        translation = {'field': 'english_text', 'value': 'The agency publishes this report to describe the quantity of goods delivered to the market during the current year.',
                       'method': 'translation-fixture', 'source_language': 'es', 'locator': span(page, 0, len(page['text']))}
        with patch('semiotic_hybrid.ask', return_value=None) as invoke:
            targeted({'a': observation}, empty, {'a': {'values': [translation]}}, empty,
                     'general', 18081, None, thesis_model='summary', thesis_port=18082)
        endpoints = {call.args[3]: (call.args[4], call.args[5]) for call in invoke.call_args_list}
        self.assertEqual(endpoints, {'tone': ('general', 18081), 'thesis': ('summary', 18082)})

    def test_explicit_object_drives_shortlist_even_with_reported_actor_code(self):
        page = {'page': 1, 'text': 'An insurer reported on battery cell manufacturing.'}
        locator = span(page, 0, len(page['text']))
        obs = {'source_key': 'publisher', 'payload': {}, 'extracted_pages': [page]}
        passage = {'field': 'english_text', 'value': page['text'], 'locator': locator, 'method': 'original_english'}
        context = {'field': 'industry_context', 'method': 'fixture', 'locator': locator, 'value': {
            'object': 'battery cell manufacturing', 'subject_status': 'explicit', 'actors': []}}
        with (patch('semiotic_hybrid.Geography') as geography, patch('semiotic_hybrid.SectorRanker') as sectors,
              patch('semiotic_hybrid.ask', return_value=context)):
            geography.return_value.extract.return_value = []
            sectors.return_value.shortlist.return_value = []
            scope_pass({'a': obs}, {'a': {'values': [passage]}}, None, model='fixture', port=18081, assertions={})
        sectors.return_value.shortlist.assert_called_once_with([passage], subject='battery cell manufacturing')

    def test_company_industry_context_requires_timely_evidence(self):
        uid = 'acbc7867-c86f-4d87-9604-7cdcfdeaef30'
        observation = {'source_key': 'publisher', 'company_ids': ['cmp_' + uid], 'payload': {},
                       'available_at': {'value': '2026-01-01T00:00:00Z'},
                       'semiotic_source_profile': {'version': '1', 'isic_fallback': {'code': 'D', 'reference': 'source'}}}
        company = {'isic_revision': 5, 'isic_code': '6512', 'basis': 'self_reported', 'review_status': 'verified',
                   'is_primary': True, 'known_at': '2025-01-01T00:00:00Z', 'assertion_id': 'assertion',
                   'evidence_uri': 'source', 'source_observation_id': 'obs_source'}
        self.assertEqual([(r['field'], r['value']) for r in entity_industry_context(observation, {uid: [company]})],
                         [('entity_reported_isic_section', 'L'), ('entity_reported_isic_division', '65')])
        company['known_at'] = '2027-01-01T00:00:00Z'
        self.assertEqual(entity_industry_context(observation, {uid: [company]}), [])

    def test_source_fallback_has_explicit_scope_and_broad_default(self):
        declaration = {'isic_fallback': {'code': '84', 'topic': 'financial disclosures', 'reference': 'fixture'}}
        rows = source_fallback({'source_key': 'regulator'}, declaration, 'content_classification_failed')
        self.assertEqual([x['value'] for x in rows], ['P', '84'])
        self.assertEqual(rows[0]['source_topic'], 'financial disclosures')
        self.assertEqual(rows[0]['classification_scope'], 'source')
        default, = source_fallback({'source_key': 'new_source'}, {}, 'no_supported_content_code')
        self.assertEqual(default['value'], 'K')
        self.assertEqual(default['source_code_basis'], 'provisional_information_service_routing')

    def test_release_falls_back_after_explicit_object_is_not_classifiable(self):
        obs_id = 'obs_1'
        observation = {'observation_id': obs_id, 'record_id': 'rec_1', 'source_record_id': 'filing',
                       'source_key': 'regulator', 'dataset': 'disclosures', 'payload': {}}
        profile = {'observation_id': obs_id, 'missingness_flags': [], 'coverage_status': {}}
        tables = {name: [] for name in ('measurements', 'evidence_units', 'claims', 'sector_attributions', 'sector_coverage')}
        tables.update(observations=[{'id': obs_id}], observation_profiles=[profile],
                      observation_geography=[{'observation_id': obs_id, 'coverage_status': {}}])
        release = {'release_id': 'fixture', 'tables': tables}
        stage = {obs_id: {'values': [{'field': 'industry_context', 'value': {'subject_status': 'explicit', 'object': 'battery'},
                                     'method': 'fixture', 'locator': {}, 'status': 'candidate'}], 'errors': []}}
        annotate_release(release, {obs_id: observation}, [stage], 'frozen', source_registry={
            'regulator': {'isic_fallback': {'code': '84', 'reference': 'fixture'}}})
        selected, = tables['unified_observations'][0]['isic']['attributions']
        self.assertEqual(selected['sector_id'], 'isic_P')
        self.assertEqual(selected['classification_scope'], 'source')
