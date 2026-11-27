import gzip
import hashlib
import io
import json
from pathlib import Path
import unittest

from metadata_engine.evidence import RawFailure, Uncommitted
from metadata_engine.labelling import label_observation
from metadata_engine.research_feeds import DATASETS, FORM, KAKEN, OPENALEX, PREFIX, SNAPSHOT_DATE, evidence, load_batch
from metadata_engine.s3_metrics import MeteredS3


BUCKET = 'test-research'
STAMP = '2026-11-21T17:30:00Z'
WORK = {'id': 'https://openalex.org/W123', 'publication_date': '2026-11-19',
        'ids': {'openalex': 'https://openalex.org/W123'}, 'authorships': [], 'type': 'article'}


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def get_object(self, Bucket, Key):
        assert Bucket == BUCKET
        body = self.objects[Key]
        return {'Body': io.BytesIO(body), 'ContentLength': len(body)}


def sha(body):
    return hashlib.sha256(body).hexdigest()


class ResearchMetadataTests(unittest.TestCase):
    def fixture(self, source, mode, window, identifier, source_url, data, native, *, event_date=None):
        s3 = MemoryS3()
        raw = f'{PREFIX}/raw/{source}/{sha(native)}.gz'
        s3.objects[raw] = gzip.compress(native)
        row = {'source_record_id': identifier, 'collection_mode': mode, 'source_url': source_url,
               'payload_json': json.dumps(data), 'collected_at': STAMP, 'window_id': window,
               'raw_uri': f's3://{BUCKET}/{raw}', 'event_date': event_date}
        body = gzip.compress((json.dumps(row) + '\n').encode())
        namespace = window + '-000000'
        batch = f'{PREFIX}/records/{source}/{mode}/{namespace}/{sha(body)}.jsonl.gz'
        manifest = f'{PREFIX}/published/{source}/{mode}/{namespace}.manifest'
        s3.objects[batch] = body
        s3.objects[manifest] = (f's3://{BUCKET}/{batch}\n').encode()
        return s3, {'source_key': source, 'input_format': FORM, 'input_key': batch}, raw, manifest

    def test_openalex_api_record_matches_full_provider_row_and_contract(self):
        s3, job, _, _ = self.fixture(OPENALEX, 'daily', WORK['publication_date'], WORK['id'],
                                      WORK['id'], WORK, json.dumps({'results': [WORK]}).encode(),
                                      event_date=WORK['publication_date'])
        rows, raw, manifest = load_batch(s3, BUCKET, job)
        artifact, = evidence(rows[0], s3, BUCKET)
        config = json.loads((Path(__file__).parent / 'config/metadata-engine.json').read_text())
        envelope = {'artifact_kind': 'provider_record', 's3_uri': f"s3://{BUCKET}/{job['input_key']}",
                    'sha256': sha(raw), 'origin': 'first_party_source'}
        label = label_observation({
            **rows[0], 'raw_s3_uri': envelope['s3_uri'], 'raw_sha256': envelope['sha256'],
            'raw_completeness_status': 'complete', 'raw_artifacts': [envelope, artifact],
        }, config['contracts'][OPENALEX])
        self.assertEqual(label['record_kind'], 'openalex_work_metadata')
        self.assertEqual(label['dataset'], DATASETS[OPENALEX])
        self.assertEqual(manifest['task']['mode'], 'daily')
        self.assertEqual(label['event_at']['value'], WORK['publication_date'])

    def test_kaken_checks_original_xml_id_and_exact_fiscal_projection(self):
        identifier = 'KAKENHI-PROJECT-19K20626'
        xml = f'''<grantAwards><totalResults>1</totalResults>
          <grantAward id="{identifier}" awardNumber="19K20626" projectType="project">
            <modified>{STAMP}</modified>
            <summary xml:lang="en"><title>Grant</title>
              <periodOfAward searchStartFiscalYear="2019" searchEndFiscalYear="2022"/>
            </summary>
          </grantAward></grantAwards>'''.encode()
        data = {'award_number': '19K20626', 'project_type': 'project', 'fiscal_start': 2019,
                'fiscal_end': 2022, 'created': None, 'modified': STAMP, 'titles': {'en': 'Grant'}}
        s3, job, _, _ = self.fixture(KAKEN, 'historical', 'fy-2019', identifier,
                                      f'https://kaken.nii.ac.jp/grant/{identifier}/', data, xml)
        rows, _, _ = load_batch(s3, BUCKET, job)
        self.assertEqual(evidence(rows[0], s3, BUCKET)[0]['artifact_kind'], 'kaken_project_xml')
        rows[0]['payload']['data']['fiscal_end'] = 2029
        with self.assertRaisesRegex(RawFailure, 'provider_record_mismatch'):
            evidence(rows[0], s3, BUCKET)

        open_ended_xml = xml.replace(b' searchEndFiscalYear="2022"', b'')
        open_ended = {**data, 'fiscal_end': None}
        s3, job, _, _ = self.fixture(KAKEN, 'historical', 'fy-2019', identifier,
                                      f'https://kaken.nii.ac.jp/grant/{identifier}/', open_ended, open_ended_xml)
        rows, _, _ = load_batch(s3, BUCKET, job)
        self.assertEqual(evidence(rows[0], s3, BUCKET)[0]['artifact_kind'], 'kaken_project_xml')
        rows[0]['payload']['data']['fiscal_end'] = 2019
        with self.assertRaisesRegex(RawFailure, 'provider_record_mismatch'):
            evidence(rows[0], s3, BUCKET)

    def test_only_committed_files_are_loaded(self):
        s3, job, _, manifest = self.fixture(OPENALEX, 'daily', WORK['publication_date'], WORK['id'],
                                             WORK['id'], WORK, json.dumps({'results': [WORK]}).encode(),
                                             event_date=WORK['publication_date'])
        original = s3.objects[manifest]
        s3.objects[manifest] = original.replace(b'.jsonl.gz', b'-unexpected.jsonl.gz')
        with self.assertRaisesRegex(RawFailure, 'batch_location'):
            load_batch(s3, BUCKET, job)
        filename = job['input_key'].rsplit('/', 1)[1]
        s3.objects[manifest] = original.replace(filename.encode(), ('a' * 64 + '.jsonl.gz').encode())
        with self.assertRaisesRegex(Uncommitted, 'not_published'):
            load_batch(s3, BUCKET, job)

    def test_rejects_corrupt_original_payload(self):
        s3, job, raw, _ = self.fixture(OPENALEX, 'daily', WORK['publication_date'], WORK['id'],
                                       WORK['id'], WORK, json.dumps({'results': [WORK]}).encode(),
                                       event_date=WORK['publication_date'])
        s3.objects[raw] = gzip.compress(b'{"results":[]}')
        rows, _, _ = load_batch(s3, BUCKET, job)
        with self.assertRaisesRegex(RawFailure, 'provider_page_checksum'):
            evidence(rows[0], s3, BUCKET)

    def test_snapshot_reuses_proofs_but_checks_each_batch_and_receipt_membership(self):
        storage = MemoryS3()
        s3 = MeteredS3(storage)
        mode = 'historical'
        namespace = 'snapshot-000123'
        part = 's3://openalex/data/jsonl/works/updated_date=2026-10-13/part_001.gz'
        manifest = f'{PREFIX}/published/{OPENALEX}/{mode}/{namespace}.manifest'
        receipt = f'{PREFIX}/snapshots/{SNAPSHOT_DATE}/parts/000123.json'
        jobs = []
        for index in range(4):
            work = {**WORK, 'id': f'https://openalex.org/W{123 + index}', 'publication_date': '2019-06-30'}
            saved = {'collection_mode': mode, 'window_id': SNAPSHOT_DATE, 'raw_uri': part,
                     'source_record_id': work['id'], 'source_url': work['id'], 'collected_at': STAMP,
                     'event_date': work['publication_date'], 'payload_json': json.dumps(work)}
            body = gzip.compress((json.dumps(saved) + '\n').encode())
            batch = f'{PREFIX}/records/{OPENALEX}/{mode}/{namespace}/{sha(body)}.jsonl.gz'
            storage.objects[batch] = body
            jobs.append({'source_key': OPENALEX, 'input_format': FORM, 'input_key': batch})

        uris = [f"s3://{BUCKET}/{job['input_key']}" for job in jobs]
        storage.objects[manifest] = ('\n'.join(uris[:3]) + '\n').encode()
        storage.objects[receipt] = json.dumps({
            'part': part, 'snapshot': f's3://{BUCKET}/{PREFIX}/snapshots/{SNAPSHOT_DATE}/{"b" * 64}.json',
            'records': uris[:2], 'retrieved_at': STAMP,
        }).encode()

        first, _, _ = load_batch(s3, BUCKET, jobs[0])
        self.assertEqual(s3.counts(), {'get_object': 3})
        first[0]['_research_evidence']['snapshot']['records'].clear()
        second, _, _ = load_batch(s3, BUCKET, jobs[1])
        self.assertEqual(s3.counts(), {'get_object': 4})
        self.assertEqual(evidence(second[0], s3, BUCKET)[0]['upstream_uri'], part)
        with self.assertRaisesRegex(RawFailure, 'openalex_snapshot_receipt_mismatch'):
            load_batch(s3, BUCKET, jobs[2])
        with self.assertRaisesRegex(Uncommitted, 'not_published'):
            load_batch(s3, BUCKET, jobs[3])
        storage.objects[jobs[1]['input_key']] = b'corrupt previously verified raw file'
        with self.assertRaisesRegex(RawFailure, 'raw_artifact_checksum_mismatch'):
            load_batch(s3, BUCKET, jobs[1])


if __name__ == '__main__':
    unittest.main()
