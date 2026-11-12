import copy
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from usgs_minerals_enrichment import parse_report,compare_editions,within_report_changes,value_cell,entity_mentions,document_identity,capture

URL='https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-cobalt.pdf'
RAW=(Path(__file__).parent/'tests/fixtures/usgs/mcs2026-cobalt.pdf').read_bytes()

class MineralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=parse_report(RAW,URL)
    def test_full_document_reserves_footnotes_and_publication(self):
        r=self.report
        self.assertEqual(r['page_count'],2)
        self.assertEqual(r['publication']['value'],'2026-02')
        self.assertTrue(r['footnotes'])
        aus=next(c for c in r['statistics'] if c['metric']=='reserves' and c['geography']=='Australia')
        self.assertEqual(aus['value'],'1700000')
        self.assertIn('10',aus['footnote_refs'])
        self.assertIsNone(aus['reference_year'])
    def test_units_flags_and_group_boundaries(self):
        cells=[c for c in self.report['statistics'] if c['table']=='salient_us_statistics' and c['reference_year']==2025]
        mine=next(c for c in cells if c['metric']=='Production: Mine')
        self.assertEqual(mine['value'],'300');self.assertTrue(mine['estimated'])
        imports=next(c for c in cells if c['metric']=='Imports for consumption')
        self.assertEqual(imports['value'],'14000');self.assertEqual(imports['unit'],'metric_ton')
        price=next(c for c in cells if 'spot' in c['metric'])
        self.assertEqual(price['unit'],'USD/lb')
        reliance=next(c for c in cells if c['metric'].startswith('Net import reliance'))
        self.assertEqual(reliance['value'],'79');self.assertEqual(reliance['unit'],'percent')
    def test_share_period_and_named_asset_not_table_heading(self):
        shares=self.report['supply_chain']['import_source_shares']
        self.assertEqual(shares[0]['reference_period'],{'start_year':2021,'end_year':2024})
        names=[a['name'] for a in self.report['entity_candidates']]
        self.assertIn('Eagle Mine',names);self.assertNotIn('World Mine',names)
        self.assertTrue(any('banned' in d['claim'] for d in self.report['development_candidates']))
        self.assertTrue(all(d['event_date'] is None for d in self.report['development_candidates']))
    def test_stockpile_values_are_plans_and_fiscal_periods_not_actual_purchases(self):
        values=self.report['supply_chain']['stockpile_values']
        first=next(v for v in values if v['fiscal_year']==2025 and v['action']=='potential_acquisitions')
        self.assertEqual(first['value'],'60')
        self.assertEqual(first['weight_basis'],'gross_weight')
        next_year=[v for v in values if v['fiscal_year']==2026]
        self.assertTrue(next_year);self.assertTrue(all(v['status']=='not_available' for v in next_year))

    def test_percent_point_and_relative_changes_are_separate(self):
        c=next(c for c in self.report['within_report_changes'] if c['metric'].startswith('Net import reliance'))
        self.assertEqual(c['absolute_change'],'5');self.assertEqual(c['absolute_change_unit'],'percentage_points')
        self.assertEqual(c['relative_change_percent'],'6.76')
    def test_revision_is_same_reference_year_not_reserve_snapshot(self):
        previous=copy.deepcopy(self.report);previous['edition']=2025;previous['report_version_id']='prior'
        current=copy.deepcopy(self.report)
        target=next(c for c in previous['statistics'] if c['metric']=='Imports for consumption' and c['reference_year']==2024)
        target['value']='10000'
        reserve=next(c for c in previous['statistics'] if c['metric']=='reserves');reserve['value']='1'
        comparison=compare_editions(current,previous)
        self.assertEqual(len(comparison['revisions']),1)
        self.assertEqual(comparison['revisions'][0]['reference_year'],2024)
    def test_special_values_and_dash_only_zero_when_defined(self):
        word=lambda s:[{'text':s,'size':10}]
        self.assertEqual(value_cell(word('NA'),10,None)['status'],'not_available')
        self.assertIsNone(value_cell(word('—'),10,None)['value'])
        self.assertEqual(value_cell(word('—'),10,'zero')['value'],'0')
        self.assertIsNone(value_cell(word('W'),10,None)['value'])
    def test_verified_rds_mentions_have_no_ownership_inference(self):
        report={'pages':[{'page':1,'text':'Acme Mining operates here. Acme Mining Tools are unrelated.'}]}
        directory={'companies':{'companies':[{'company_id':'c1','canonical_name':'Acme Mining','review_status':'verified'}]},'products':{'products':[]}}
        result=entity_mentions(report,directory)
        self.assertEqual(result['company_count'],1)
        self.assertTrue(result['matches']);self.assertIn('ownership',result['matches'][0]['role'])
        self.assertFalse(result['historical_association'])
    def test_all_four_current_report_layouts_and_special_cells(self):
        for mineral,production in [('lithium','290000'),('nickel','3900000'),('graphite','1800000')]:
            raw=(Path(__file__).parent/('tests/fixtures/usgs/mcs2026-'+mineral+'.pdf')).read_bytes()
            r=parse_report(raw,'https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-'+mineral+'.pdf')
            self.assertEqual(r['gaps'],[],mineral)
            total=next(c for c in r['statistics'] if c['table']=='world_production_reserves' and c['geography']=='World total (rounded)' and c.get('reference_year')==2025)
            self.assertEqual(total['value'],production,mineral)
            if mineral=='lithium':
                prices=[c for c in r['statistics'] if 'Price' in c['metric']]
                self.assertTrue(all(c['unit']=='USD/metric_ton' for c in prices))

    def test_source_url_and_html_are_rejected(self):
        with self.assertRaises(Exception):document_identity('https://example.com/mcs2026-cobalt.pdf')
        with self.assertRaises(Exception):parse_report(b'<html/>',URL)
    def test_daily_adapter_commits_one_full_report_not_page_events(self):
        from specialist_inputs import fetch_page
        client=Mock();client.get.return_value=RAW
        report={'report_id':'r1','pages':[{},{}]}
        job={'source':'usgs_minerals','adapter':'pdf','mode':'daily','parameters':{'url':URL,'period':'2026'}}
        with patch('usgs_minerals_enrichment.capture',return_value=report):rows,cursor=fetch_page(client,job,None)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['id'],'report:r1');self.assertIsNone(cursor)
