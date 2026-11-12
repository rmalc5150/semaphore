import copy
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

from pubmed_enrichment import enrich, date_fact
from research_contract import ROOT
from specialist_inputs import item
from specialist_public_apis import fetch

FIXTURES=ROOT/'tests/fixtures/pubmed'


class PubMedTests(unittest.TestCase):
    def article(self,pmid):
        return (FIXTURES/(pmid+'.xml')).read_text()

    def test_all_twenty_samples_have_traceable_publication_context(self):
        paths=list(FIXTURES.glob('*.xml'));self.assertEqual(len(paths),20)
        for path in paths:
            result=enrich(path.read_text(),path.stem)
            self.assertIsNone(result['publication_event']['underlying_clinical_event_date'])
            self.assertFalse(result['company_product_person_ids_assigned'])
            self.assertTrue(result['journal_country_is_not_trial_country'])
            if result['key_takeaway']:
                self.assertFalse(result['key_takeaway']['independent_assessment'])
                self.assertEqual(result['key_takeaway']['text'],result['key_takeaway']['source']['text'])

    def test_recruitment_failure_is_not_efficacy_success(self):
        result=enrich(self.article('35129803'))
        self.assertEqual(result['study_design'],'trial_report_with_recruitment_failure')
        self.assertEqual(result['publication_event']['type'],'recruitment_failure_report_published')
        self.assertTrue(any(t['trial_id']=='NCT03835728' and any(e['role']=='declared_registration' for e in t['evidence']) for t in result['trial_links']))

    def test_reference_trial_ids_do_not_become_the_review_registration(self):
        result=enrich(self.article('33598857'))
        self.assertEqual(result['study_design'],'evidence_synthesis')
        for trial in result['trial_links']:
            self.assertTrue(all(e['role']=='reference_only' for e in trial['evidence']))
        self.assertIn('NCT03548207',[t['trial_id'] for t in result['trial_links']])

    def test_mendelian_randomization_overrides_conflicting_trial_tag(self):
        result=enrich(self.article('34749668'))
        self.assertEqual(result['study_design'],'genetic_causal_inference')
        self.assertIn('indexing_design_conflict',[f['code'] for f in result['quality_flags']])

    def test_missing_abstract_is_not_a_positive_outcome(self):
        result=enrich(self.article('34655480'))
        self.assertIsNone(result['key_takeaway'])
        self.assertEqual(result['interpretation_status'],'abstract_missing')
        self.assertEqual(result['identifiers']['pmc'],'PMC9297938')
        self.assertEqual(result['full_text_candidate']['status'],'not_retrieved')

    def test_inline_sections_and_immunogenicity_evidence_remain_verbatim(self):
        result=enrich(self.article('34954967'))
        self.assertEqual([s['label'] for s in result['abstract_sections']],['OBJECTIVE','METHODS','RESULTS','CONCLUSIONS'])
        self.assertTrue(result['key_takeaway'])
        self.assertIn('GMT',result['key_takeaway']['text'])

    def test_partial_dates_never_invent_a_day_and_indexing_is_not_publication(self):
        fact=date_fact(ET.fromstring('<PubDate><Year>2021</Year><Month>Mar</Month></PubDate>'),'issue')
        self.assertEqual((fact['value'],fact['precision']),('2021-03','month'))
        result=enrich(self.article('34655480'))
        self.assertEqual(result['publication_event']['date']['value'],'2021-10-28')
        self.assertEqual(result['publication_event']['date']['basis'],'electronic_publication')

    def test_wrong_primary_pmid_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'primary_pmid_mismatch'):
            enrich(self.article('35129803'),'34655480')

    def test_book_records_are_retained_without_fabricated_trial_findings(self):
        result=enrich('<PubmedBookArticle><BookDocument><PMID>123</PMID><ArticleTitle>Clinical background</ArticleTitle></BookDocument></PubmedBookArticle>','123')
        self.assertEqual(result['interpretation_status'],'record_type_needs_review')
        self.assertIsNone(result['key_takeaway'])
        self.assertIsNone(result['publication_event']['date'])

    def test_collector_keeps_original_xml_and_adds_enrichment_with_publication_date(self):
        client=Mock()
        client.json.return_value={'esearchresult':{'count':'1','idlist':['35129803']}}
        client.get.return_value=('<PubmedArticleSet>'+self.article('35129803')+'</PubmedArticleSet>').encode()
        rows,cursor=fetch(client,{'adapter':'pubmed','parameters':{'url':'https://example.org','query':{}}},None,item)
        self.assertIsNone(cursor)
        self.assertEqual(rows[0]['date'],'2022-02-07')
        self.assertIn('article_xml',rows[0]['data'])
        self.assertEqual(rows[0]['data']['enrichment']['pmid'],'35129803')


if __name__=='__main__':
    unittest.main()
