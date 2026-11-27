"""Regression checks for reviewed archive parsing and paid-source exclusions."""
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from market_archive_import import indexed_filing, prepared_rows, profiles
from market_source_register import PAID_EXCLUSIONS


class MarketArchiveImportTests(unittest.TestCase):
    def test_no_paid_import_profile(self):
        self.assertFalse({profile['id'] for profile in profiles()} & PAID_EXCLUSIONS.keys())

    def test_scoped_edition_parses_only_matching_native_rows(self):
        profile={'format':'csv','fields':['year','firms'],'row_filter':['year','^2016$']}
        with tempfile.TemporaryDirectory() as directory:
            original=Path(directory)/'archive.csv'
            original.write_text('year,firms\n2015,1\n2016,2\n')
            records,limited=prepared_rows(original,profile)
        self.assertFalse(limited)
        self.assertEqual(records,[('file',2,{'year':'2016','firms':'2'})])

    def test_blank_table_viewer_has_no_provider_rows(self):
        profile={'format':'html','text_pattern':'production','table_xpath':'//main//table//tr'}
        with tempfile.TemporaryDirectory() as directory:
            original=Path(directory)/'viewer.html'
            description='Production statistics. '*40
            original.write_text('<html><head><title>Production</title></head><body><main>'+description+
                                '<table><tr><th>Year</th><th>Indicator</th><th>Measure</th></tr></table>'
                                '</main></body></html>')
            with self.assertRaisesRegex(ValueError,'no_parsed_provider_records'):
                prepared_rows(original,profile)

    def test_trends_timeline_retains_censored_scores_and_excludes_prior_year_week(self):
        spec = {'format': 'google_trends_csv', 'term': 'semiconductors', 'year': 2016}
        header = 'Category: All categories\n\nWeek,semiconductors: (Worldwide)\n'
        weeks = [f'{date(2016, 1, 3) + timedelta(weeks=i)},{"<1" if i == 0 else "50"}\n'
                 for i in range(52)]
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'multiTimeline.csv'
            original.write_text(header + '2015-12-27,3\n' + ''.join(weeks))
            parsed, limited = prepared_rows(original, spec)
            self.assertEqual(len(parsed), 52)
            self.assertFalse(limited)
            self.assertEqual(parsed[0][1], 5)
            self.assertEqual(parsed[0][2]['week_start'], '2016-01-03')
            self.assertEqual(parsed[0][2]['reported_interest'], '<1')
            self.assertIsNone(parsed[0][2]['interest_score'])
            original.write_text(header + ''.join(weeks[:-1]))
            with self.assertRaisesRegex(ValueError, 'incomplete_trends_window'):
                prepared_rows(original, spec)

    def test_trends_timeline_accepts_contiguous_weekly_rows_across_calendar_years(self):
        spec = {'format': 'google_trends_csv', 'term': 'semiconductors', 'year': 2017, 'end_year': 2020}
        header = 'Category: All categories\n\nWeek,semiconductors: (Worldwide)\n'
        weeks = [f'{date(2017, 1, 1) + timedelta(weeks=i)},50\n' for i in range(209)]
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'multiTimeline.csv'
            original.write_text(header + ''.join(weeks))
            parsed, limited = prepared_rows(original, spec)
            self.assertEqual(len(parsed), 209)
            self.assertFalse(limited)
            self.assertEqual(parsed[0][2]['week_start'], '2017-01-01')
            self.assertEqual(parsed[-1][2]['week_start'], '2020-12-27')

    def test_entsoe_variable_blocks_end_at_period_boundary(self):
        profile = {'format': 'entsoe_load_xml', 'bidding_zone': '10YFR-RTE------C',
                   'window_start': '2016-01-01T00:00:00Z',
                   'window_end_exclusive': '2016-01-01T05:00:00Z'}
        document = '''<GL_MarketDocument xmlns="urn:entsoe:fixture">
          <mRID>document</mRID><revisionNumber>1</revisionNumber><type>A65</type>
          <process.processType>A16</process.processType><createdDateTime>2026-11-23T00:00Z</createdDateTime>
          <TimeSeries><mRID>1</mRID><outBiddingZone_Domain.mRID>10YFR-RTE------C</outBiddingZone_Domain.mRID>
          <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name><curveType>A03</curveType>
          <Period><timeInterval><start>2016-01-01T00:00Z</start><end>2016-01-01T03:00Z</end></timeInterval>
          <resolution>PT60M</resolution><Point><position>1</position><quantity>20</quantity></Point>
          <Point><position>3</position><quantity>30</quantity></Point></Period>
          <Period><timeInterval><start>2016-01-01T04:00Z</start><end>2016-01-01T05:00Z</end></timeInterval>
          <resolution>PT60M</resolution><Point><position>1</position><quantity>40</quantity></Point></Period>
          </TimeSeries></GL_MarketDocument>'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'actual-load.xml'
            path.write_text(document)
            rows, limited = prepared_rows(path, profile)
        self.assertFalse(limited)
        blocks = [(row['interval_start'][11:13], row['interval_end_exclusive'][11:13], row['megawatts'])
                  for _, _, row in rows]
        self.assertEqual(blocks, [('00', '02', 20.0), ('02', '03', 30.0), ('04', '05', 40.0)])

    def test_cmf_headerless_archive_preserves_the_first_row_and_checks_all_quarters(self):
        profile = {'format': 'cmf_ifrs', 'year': 2016}
        rows = [f'2016{month};60503000;Empresa;I;CLP;Cash;100;TAX CI;ESF C/NC\n'
                for month in ('03', '06', '09', '12')]
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory)/'issuer-ifrs.txt'
            original.write_text(''.join(rows))
            parsed, limited = prepared_rows(original, profile)
            self.assertEqual([row['reference_period'] for _, _, row in parsed], ['201603','201606','201609','201612'])
            self.assertFalse(limited)
            original.write_text(''.join(rows[:-1]))
            with self.assertRaisesRegex(ValueError,'cmf_ifrs_statement_periods_missing'):
                prepared_rows(original, profile)

    def test_scanned_filing_uses_the_matching_register_row(self):
        from pypdf import PdfWriter

        base = 'https://register.example/company/01234567/filing-history'
        spec = {'url':base+'/first/document?format=pdf', 'filing_index_url':base,
                'year':2016, 'filing_form':'TM01', 'company_number':'01234567'}
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory)/'filing.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            writer.write(pdf)
            index = Path(directory)/'index.html'
            index.write_text(f'<table><tr><td>06 Jan 2016</td><td>TM01</td><td>Filed notice</td>'
                             f'<td><a href="{spec["url"]}">PDF</a></td></tr></table>')
            _, _, filing = indexed_filing(pdf, index, spec)[0]
            self.assertEqual((filing['filing_date'], filing['document_page_count']), ('2016-01-06', 1))
            with self.assertRaisesRegex(ValueError, 'filing_scope_mismatch'):
                indexed_filing(pdf, index, {**spec, 'year':2017})


if __name__=='__main__':
    unittest.main()
