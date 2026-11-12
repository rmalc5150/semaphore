import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from openpyxl import Workbook

import eia_enrichment as module
from collection_storage import LocalStore
from regulatory_collection import SourceIssue

URL='https://www.eia.gov/electricity/data/eia860m/archive/xls/january_generator2018.xlsx'
META={'id':'retail-sales','data':{'price':{'units':'cents per kilowatt-hour'},'sales':{'units':'million kilowatt hours'},'revenue':{'units':'million dollars'},'customers':{'units':'number of customers'}}}

def workbook():
    w=Workbook();s=w.active;s.title='Operating';s.append(['January 2018 inventory'])
    s.append(['Plant ID','Generator ID','Plant State','Status','Prime Mover Code','Nameplate Capacity (MW)','Energy Capacity (MWh)'])
    s.append([1,'01','CA','OP','BAT',10,40]);s.append([2,'02','TX','OP','CT',20,None])
    s=w.create_sheet('Planned');s.append(['Plant ID','Generator ID','Plant State','Status','Prime Mover Code','Nameplate Capacity (MW)']);s.append([3,'A','CA','U','BAT',5])
    raw=io.BytesIO();w.save(raw);w.close();return raw.getvalue()


def row(period,price='10',sales='100',revenue='10',customers='1000'):
    return {'stateid':'US','sectorid':'ALL','period':period,'price':price,'sales':sales,'revenue':revenue,'customers':customers}

class EiaTests(unittest.TestCase):
    def test_plan_uses_visible_archive_links_and_daily_cache(self):
        plan={'sources':[{'enabled':True,'adapter':'eia_xlsx','api':'https://www.eia.gov/electricity/data/eia860m/',
                         'archives':[{'period':'2026-12','url':'stale-template'}]}]}
        raw=b'<a href="xls/august_generator2026.xlsx">X</a><!--<a href="xls/december_generator2026.xlsx">X</a>-->'
        with tempfile.TemporaryDirectory() as d, patch('regulatory_collection.EvidenceClient') as cls:
            cls.return_value.get.return_value=raw;cls.return_value.evidence=[]
            store=LocalStore(d)
            self.assertEqual(module.refresh_generator_archives(plan,store),{'2026-08'})
            self.assertEqual(module.refresh_generator_archives(plan,store),{'2026-08'})
            self.assertEqual(cls.return_value.get.call_count,1)
            self.assertEqual(plan['sources'][0]['archives'][0]['period'],'2026-08')

    def test_archive_schema_and_units_no_battery_row_duplication(self):
        r=module.workbook_summary(workbook(),URL)
        self.assertEqual(r['report_period'],'2018-01')
        self.assertEqual(r['distinct_generators_across_sheets'],3)
        self.assertEqual(r['sheets'][0]['reported_capacity_sums_mw'],{'nameplate capacity (mw)':'30'})
        self.assertEqual(r['sheets'][0]['prime_mover_code_counts'],{'BAT':1,'CT':1})
        self.assertEqual(r['battery_dataset_link']['source'],'eia_battery_generators')
        self.assertNotIn('generator_rows',r)
    def test_workbook_cache_retains_evidence_and_avoids_repeated_download(self):
        with tempfile.TemporaryDirectory() as d:
            c=Mock(store=LocalStore(d),evidence=[])
            def get(url):c.evidence.append({'source_url':url,'key':'original','sha256':'a'*64});return workbook()
            c.get.side_effect=get
            first=module.enrich_archive(URL,c);second=module.enrich_archive(URL,c)
        self.assertEqual(c.get.call_count,1);self.assertEqual(first,second)
    def test_bad_hosts_periods_and_html_rejected(self):
        for url in [URL.replace('www.eia.gov','example.com'),URL.replace('january','nonsense'),URL+'?api_key=bad']:
            with self.assertRaises(SourceIssue):module.archive_period(url)
        with self.assertRaises(SourceIssue):module.workbook_summary(b'<html/>',URL)
    def test_retail_units_conversions_and_distinct_comparisons(self):
        r=module.retail_row(row('2021-01','12'),[row('2020-12','10'),row('2020-01','8')],META)['enrichment']
        self.assertEqual(r['fields']['sales']['units'],'million kilowatt hours')
        self.assertEqual(r['price_usd_per_kwh']['value'],'0.12')
        prices=[c for c in r['comparisons'] if c['metric']=='price']
        self.assertEqual(prices[0]['absolute_change'],'2');self.assertEqual(prices[0]['relative_change_percent'],'20.00')
        self.assertEqual(prices[1]['relative_change_percent'],'50.00')
        self.assertEqual(r['status'],'enriched')
    def test_missing_or_different_baselines_are_not_invented(self):
        r=module.retail_row(row('2021-01','NA'),[],META)['enrichment']
        self.assertIsNone(r['fields']['price']['value']);self.assertEqual(r['status'],'review_required')
        self.assertTrue(all(c['status']!='computed' for c in r['comparisons']))
    def test_history_checks_pagination_scope_and_duplicate_periods(self):
        response={'response':{'total':'2','data':[row('2021-01'),row('2021-01')]}}
        with patch('specialist_authenticated.request',return_value=response):
            with self.assertRaisesRegex(SourceIssue,'duplicate_period'):module.retail_history(Mock(),'2020-01','2021-01')
        response['response']['data']=[{**row('2021-01'),'stateid':'CA'}];response['response']['total']='1'
        with patch('specialist_authenticated.request',return_value=response):
            with self.assertRaisesRegex(SourceIssue,'scope'):module.retail_history(Mock(),'2020-01','2021-01')
    def test_index_cursor_pins_discovered_links(self):
        from specialist_inputs import item
        urls=[URL.replace('january',name) for name in ['january','february','march','april','may','june']]
        c=Mock(evidence=[]);c.get.return_value=(''.join('<a href="'+u+'">X</a>' for u in urls)).encode()
        with patch.object(module,'enrich_archive',return_value={'status':'enriched'}):
            first,cursor=module.index_page(c,{'parameters':{'url':'https://www.eia.gov/electricity/data/eia860m/'}},None,item)
            second,end=module.index_page(c,{'parameters':{'url':'https://www.eia.gov/electricity/data/eia860m/'}},cursor,item)
        self.assertEqual(len(first),5);self.assertEqual(len(second),1);self.assertIsNone(end);self.assertEqual(c.get.call_count,1)
    def test_commented_templates_are_not_published_links(self):
        raw=b'<a href="xls/august_generator2026.xlsx">XLS</a><!--<a href="xls/december_generator2026.xlsx">XLS</a>-->'
        links=module.published_links(raw,'https://www.eia.gov/electricity/data/eia860m/')
        self.assertEqual(len(links),1);self.assertIn('august',links[0])
    def test_future_archive_link_is_not_downloaded_or_a_release(self):
        c=Mock()
        r=module.enrich_archive(URL.replace('2018','2099'),c)
        c.get.assert_not_called();self.assertFalse(r['workbook_validated']);self.assertIsNone(r['event_candidate'])
    def test_observed_retail_revision_ignores_formatting_changes(self):
        with tempfile.TemporaryDirectory() as d:
            c=Mock(store=LocalStore(d),evidence=[])
            self.assertEqual(module.retail_revision(row('2021-01','10.0'),c)['status'],'baseline')
            self.assertEqual(module.retail_revision(row('2021-01','10.00'),c)['status'],'unchanged')
            self.assertEqual(module.retail_revision(row('2021-01','11'),c)['status'],'observed_revision')

    def test_daily_retail_routes_only_targeted_source(self):
        from specialist_authenticated import fetch
        from specialist_inputs import item
        job={'source':'eia_retail_prices','adapter':'eia_api','parameters':{'url':module.RETAIL_URL}}
        with patch.object(module,'retail_page',return_value=([],None)) as page:
            fetch(Mock(),job,None,item)
        page.assert_called_once()
