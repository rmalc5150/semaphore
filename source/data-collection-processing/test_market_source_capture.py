"""Regression checks for the workbook gate, exact evidence and resumable windows."""
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest

import market_source_capture as capture
from market_source_register import MANIFEST
from metadata_engine.market_sources import evidence, from_receipt
from metadata_engine.evidence import RawFailure


class OriginalBody(io.BytesIO):
    def iter_chunks(self, chunk_size):
        return iter(lambda: self.read(chunk_size), b'')


class ObjectStore:
    def __init__(self, original):
        self.original=original

    def get_object(self, **request):
        return {'Body':OriginalBody(self.original)}


class MarketSourcesTests(unittest.TestCase):
    def test_register_covers_every_active_workbook_id_once(self):
        entries=json.loads(MANIFEST.read_text())['sources']
        self.assertEqual([row['catalog_entry'] for row in entries],
                         [entry for entry in range(159,273) if entry != 191])
        self.assertEqual(sum(row['registration']=='conditional' for row in entries),11)
        known={(r['source_key'],d) for r in entries for d in r['datasets']}
        for r in capture.configuration()['routes']:
            self.assertIn((r['source'],r['dataset']),known)

    def test_month_backfill_retains_2016_and_leap_day(self):
        config=capture.configuration()
        profile=next(r for r in config['routes'] if r['catalog_entry']==162)
        parts=list(capture.plan(profile,'historical',date(2016,3,1),date(2017,1,1)))
        self.assertEqual([p[0] for p in parts],['2016-01-01T0000','2016-02-01T0000'])
        self.assertTrue(all(url.endswith('2016022900') for url in parts[-1][1]))

    def test_native_response_requires_matching_rows(self):
        config=capture.configuration()
        profile=next(r for r in config['routes'] if r['catalog_entry']==162)
        original=b'{"items":[{"article":"Semiconductor","timestamp":"2016010100","views":8}]}'
        source=profile['source']
        sha=capture.hashlib.sha256(original).hexdigest()
        url='https://wikimedia.org/api/rest_v1/metrics/pageviews'
        with tempfile.NamedTemporaryFile() as raw:
            raw.write(original)
            raw.flush()
            proof=capture.validated(Path(raw.name),profile,url)
        self.assertEqual(proof['observed_from'],'2016-01-01')
        receipt={'source':source,'dataset':profile['dataset'],'sha256':sha,
                 'resource_url':url,'source_url':url,'retrieved_at':'2026-11-21T14:00:00Z',
                 'artifact_uri':f's3://test/{capture.MARKET}/objects/{source}/{sha}',
                 'bytes':len(original),'validation':proof,'partition':'2016-01','scope_note':'fixture'}
        record=from_receipt(receipt)
        contract={'market_routes':{profile['dataset']:profile}}
        self.assertEqual(evidence(record,contract,ObjectStore(original),'test')[0]['sha256'],sha)
        with self.assertRaisesRegex(RawFailure,'checksum'):
            evidence(record,contract,ObjectStore(b'{"items":[]}'),'test')
        with tempfile.NamedTemporaryFile() as raw:
            raw.write(b'<!doctype html><html><title>Sign in</title></html>')
            raw.flush()
            with self.assertRaises(ValueError):
                capture.validated(Path(raw.name),profile,url)


if __name__=='__main__':
    unittest.main()
