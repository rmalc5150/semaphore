"""Tests for the parser package boundary, bundle and legacy callers."""
from importlib import import_module
from io import BytesIO
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from raw_parsers import __version__
from raw_parsers.release import build, source_paths

ROOT = Path(__file__).resolve().parent
PUBLIC = {
    'canada_noc': ('product_id', 'validate'),
    'chictr_tables': ('parse_detail_page', 'has_trial_detail'),
    'epmc_fulltext': ('parse_original', 'enrichment', 'ProviderError'),
    'nmpa_tables': ('parse_detail_page', 'structured_detail'),
    'pmda_tables': ('japanese_date', 'parse_pdf'),
    'pubmed_enrichment': ('enrich',),
}


class RawParserTests(unittest.TestCase):
    def test_legacy_imports_refer_to_the_same_functions(self):
        for name, exports in PUBLIC.items():
            with self.subTest(parser=name):
                shared = import_module('raw_parsers.' + name)
                previous = import_module('metadata_engine.' + name)
                for key in exports:
                    self.assertIs(getattr(shared, key), getattr(previous, key))

    def test_bundle_reproduces_and_imports_without_metadata(self):
        release = build(ROOT)
        self.assertEqual(release, build(ROOT))
        with ZipFile(BytesIO(release)) as z:
            manifest = json.loads(z.read('raw_parsers/manifest.json'))
            self.assertEqual(manifest['version'], __version__)
            self.assertEqual(set(manifest['files']), set(source_paths()))
            self.assertEqual(set(z.namelist()), set(source_paths()) | {'raw_parsers/manifest.json'})
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), digest)
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'pinned-parsers.zip'
            path.write_bytes(release)
            probe = """
import sys
sys.path.insert(0, sys.argv[1])
from raw_parsers import __version__
from raw_parsers.canada_noc import product_id
from raw_parsers.chictr_tables import parse_detail_page
from raw_parsers.epmc_fulltext import request_pmcid
from raw_parsers.pmda_tables import japanese_date
from raw_parsers.pubmed_enrichment import date_fact
assert product_id({'name': 'example'}).startswith('product:')
assert japanese_date('R1.5.1').isoformat() == '2019-05-01'
assert request_pmcid('https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML') == 'PMC1'
assert not any(key == 'metadata_engine' or key.startswith('metadata_engine.') for key in sys.modules)
"""
            subprocess.run([sys.executable, '-IB', '-c', probe, str(path)], cwd=directory,
                           check=True, capture_output=True, text=True)

    def test_capture_deployment_includes_the_shared_package(self):
        from constellation.deploy_legacy import dependencies

        bundled = dependencies(['specialist_inputs.py'])
        self.assertTrue(set(source_paths()).issubset(bundled))
        self.assertFalse(any(path.startswith('metadata_engine/') for path in bundled))

    def test_install_checks_the_zip_before_selecting_a_release(self):
        from install_raw_parser_release import activate

        body = build(ROOT)
        digest = hashlib.sha256(body).hexdigest()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'raw-parsers.zip'
            archive.write_bytes(body)
            releases = root / 'releases'
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                activate(archive, '0' * 64, releases)
            self.assertFalse(releases.exists())
            release = activate(archive, digest, releases)
            self.assertEqual((releases / 'current').resolve(), release)
            self.assertEqual(activate(archive, digest, releases), release)
            self.assertTrue((release / 'raw_parsers/canada_noc.py').is_file())


if __name__ == '__main__':
    unittest.main()
