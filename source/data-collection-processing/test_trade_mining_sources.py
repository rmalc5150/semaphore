"""Regressions for the source-specific evidence boundaries."""
from datetime import date
import json
import unittest

from metadata_engine.census_trade import native_table
from metadata_engine.evidence import RawFailure
from metadata_engine.trade_mining import native_rows
from trade_mining_sources import MDIC, COMEXT, SNIFA, in_scope, request_seeds


class TradeAndMiningEvidence(unittest.TestCase):
    def test_census_repeated_predicates_must_agree(self):
        header = ['CTY_CODE','CTY_NAME','E_COMMODITY','ALL_VAL_MO','E_COMMODITY','CTY_CODE','YEAR','MONTH']
        row = ['5330','INDIA','260400','0','260400','5330','2024','11']
        def parse():
            return native_table(json.dumps([header,row]).encode(),'E_COMMODITY','ALL_VAL_MO','2024','11','260400')
        self.assertEqual(parse()['5330']['ALL_VAL_MO'],'0')
        row[5] = '5700'
        with self.assertRaisesRegex(RawFailure,'repeated_predicate_mismatch'):
            parse()

    def test_mdic_original_metric_must_come_from_requested_month(self):
        url = request_seeds(MDIC,'daily','2026-11-20')[0]
        row = {'coNcm':'85076000','year':'2026','monthNumber':'10','metricFOB':'42','metricKG':'2'}
        body = lambda: json.dumps({'success':True,'data':{'list':[row]}}).encode()
        self.assertEqual(native_rows(MDIC,url,body())['import:2026-10:85076000'],row)
        row['monthNumber'] = '01'
        with self.assertRaisesRegex(RawFailure,'outside_query'):
            native_rows(MDIC,url,body())

    def test_comext_csv_preserves_flags_and_rejects_wrong_reporter(self):
        url = request_seeds(COMEXT,'historical','2026-11-20')[0]
        header = 'DATAFLOW,freq,reporter,partner,product,flow,indicators,TIME_PERIOD,OBS_VALUE,OBS_FLAG\n'
        row = 'ESTAT:DS-045409(1.0),A,DE,US,850760,1,VALUE_IN_EUROS,2023,123,p\n'
        result = native_rows(COMEXT,url,(header+row).encode())
        self.assertEqual(result['A:DE:US:850760:1:VALUE_IN_EUROS:2023']['OBS_FLAG'],'p')
        with self.assertRaisesRegex(RawFailure,'outside_query'):
            native_rows(COMEXT,url,(header+row.replace(',DE,',',FR,')).encode())

    def test_snifa_does_not_trust_unrelated_drive_documents(self):
        self.assertTrue(in_scope('https://drive.usercontent.google.com/download?id=1hPEwmUFZpmD7xFbJy-kjhhzjplnUB1mH&export=download',SNIFA))
        self.assertFalse(in_scope('https://drive.usercontent.google.com/download?id=some_other_file&export=download',SNIFA))
