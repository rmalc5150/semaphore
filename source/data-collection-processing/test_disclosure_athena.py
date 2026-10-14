from pathlib import Path
import json
import unittest
import pyarrow.parquet as pq

from collection_storage import StorageSettings
import test_disclosure_collection as fixtures
import disclosure_athena as a


class DisclosureAthenaTests(unittest.TestCase):
    setUp = fixtures.DisclosureTests.setUp
    collect = fixtures.DisclosureTests.collect
    read = fixtures.DisclosureTests.read
    derive = fixtures.DisclosureTests.derive

    def test_release_parquet_counts_and_candidates(self):
        filings=self.collect([fixtures.page([fixtures.row()])]);url=self.read(filings)[0]['record']['source_url']
        docs=self.derive('documents',[filings['manifest']],fixtures.Client(self.store,documents={url:b'<html>Example Robotics signs an exclusive license agreement covering its robot designs.</html>'}))
        events=self.derive('licensing-agreements',[docs['manifest']])
        config={'database':'optima_disclosures_pilot','workgroup':'optima-disclosures-pilot','region':'us-east-1',
            'curated_prefix':'curated/disclosures_pilot/releases','query_results_prefix':'athena-results/disclosures-pilot',
            'source_manifests':[filings['manifest'],docs['manifest'],events['manifest']]}
        root=a.prepare(self.store,StorageSettings(backend='s3',s3_bucket='test-bucket'),config,Path(self.temp.name)/'build')
        report=json.loads((root/'release.json').read_text())
        self.assertEqual(report['catalog_owner'],'disclosures')
        self.assertEqual(report['expected_results']['candidate_counts'],[['licensing_agreements','1']])
        table=pq.ParquetFile(root/'tables/event_candidates/part-00000.parquet').read().to_pylist()
        self.assertEqual(json.loads(table[0]['data_json'])['review_status'],'unreviewed')
        self.assertIsNone(table[0]['available_at'])


if __name__=='__main__':unittest.main()
