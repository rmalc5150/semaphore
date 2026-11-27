"""Controller and worker entry points for versioned, committed metadata pilots."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from semiotic_batch import read_parquet
from semiotic_raw_text import ArchivedEvidenceReader
from semiotic_sandbox import encoded, sha


def save(path, data):
    body = encoded(data)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f'conflicting pilot handoff: {path}')
    else:
        with path.open('xb') as stream:
            stream.write(body)


def published_jobs(db, source):
    with db.tx() as cur:
        cur.execute("""SELECT j.job_id,j.output_rows,r.s3_uri AS receipt_uri,r.manifest_sha256
            FROM (SELECT job_id,output_rows FROM engine_jobs FORCE INDEX(source_publication_order)
              WHERE source_key=%s AND state='accepted' AND output_rows>0
              ORDER BY finished_at DESC,job_id DESC LIMIT 120) j
            JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32))
            WHERE r.status='published' AND r.release_kind='labelled'
            ORDER BY j.output_rows,j.job_id LIMIT 5""", (source,))
        return cur.fetchall()


def verified_receipt(s3, config, job):
    uri = urlsplit(job['receipt_uri'])
    prefix = f"/{config['prefix'].rstrip('/')}/publication/{job['job_id']}/"
    if uri.scheme != 's3' or uri.netloc != config['bucket'] or not uri.path.startswith(prefix):
        raise ValueError('publication receipt outside the metadata job namespace')
    response = s3.get_object(Bucket=uri.netloc, Key=uri.path[1:])
    with response['Body'] as body:
        raw = body.read(65537)
    if len(raw) > 65536 or sha(raw) != job['manifest_sha256']:
        raise ValueError('publication receipt checksum mismatch')
    receipt = json.loads(raw)
    if (receipt['job_id'], receipt['status'], receipt['rows']) != (job['job_id'], 'verified', job['output_rows']):
        raise ValueError('publication receipt does not match committed job')
    return receipt


def probe_example(s3, config, profile):
    example = profile['raw_examples'][0]
    parsed = urlsplit(example)
    bucket = parsed.path.rsplit('/', 1)[-1]
    key, = parse_qs(parsed.query)['prefix']
    if parsed.netloc != 's3.console.aws.amazon.com' or bucket != config['bucket'] or not key.startswith('research-data/'):
        raise ValueError('raw example outside the configured archive')
    response = s3.head_object(Bucket=bucket, Key=key)
    return {'url': example, 'bytes': response['ContentLength'], 'content_type': response.get('ContentType')}


def prepare(config, registry, output):
    from botocore.exceptions import ClientError
    from metadata_engine.runtime_db import Database
    from semiotic_industry import read_assertions
    from semiotic_registry import empty

    db = Database(config)
    glue, s3 = db.session.client('glue'), db.session.client('s3')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'archive'
    archive.mkdir(exist_ok=True)
    reader = ArchivedEvidenceReader(s3, config['bucket'],
                                    max_artifact_bytes=registry.get('max_original_bytes', 8 * 1024 * 1024))
    batches, files, results = [], [], {}
    for profile in registry['sources']:
        key = profile['source_key']
        status = {'profile_version': profile['profile_version'], 'status': 'no_published_job_found'}
        results[key] = status
        try:
            status['example'] = probe_example(s3, config, profile)
        except (ClientError, ValueError, KeyError) as error:
            status['example_error'] = type(error).__name__
        if profile['input_kind'] == 'catalogue':
            status['status'] = 'catalogue_evidence_requires_underlying_original'
            print(key, status['status'], flush=True)
            continue
        for job in published_jobs(db, key):
            try:
                receipt = verified_receipt(s3, config, job)
                snapshot, refs = read_parquet(glue, s3, [job['job_id']], config['bucket'], config['prefix'])
                if (len(snapshot['observations']) != receipt['rows'] or
                        receipt['output_uri'] != f"s3://{config['bucket']}/{refs[0]['key']}" or
                        any(row['source_key'] != key for row in snapshot['observations'])):
                    raise ValueError('verified job does not match its published observations')
            except (ClientError, ValueError, KeyError) as error:
                status.update(status='published_input_unavailable', reason=type(error).__name__)
                continue
            observations = [row for row in snapshot['observations'] if row.get('quality_status') == 'accepted'][:1]
            if not observations:
                status.update(status='no_accepted_observation', job_id=job['job_id'])
                continue
            row, = observations
            verified = []
            for artifact in row['raw_artifacts']:
                if artifact.get('representation') or artifact.get('origin') != 'first_party_source':
                    continue
                digest = artifact['sha256'].removeprefix('sha256:')
                try:
                    the_bytes = reader.fetch(artifact)
                except (ValueError, ClientError, RuntimeError) as error:
                    status.setdefault('artifact_errors', []).append(type(error).__name__)
                    continue
                if the_bytes is None:
                    status.setdefault('artifact_errors', []).append('artifact_size_limit')
                    continue
                path = archive / digest
                if not path.exists():
                    with path.open('xb') as stream:
                        stream.write(the_bytes)
                verified.append(digest)
                if (the_bytes.startswith(b'%PDF-') or b'<html' in the_bytes[:4096].lower()) and (
                        profile['input_kind'] != 'article' or artifact['artifact_kind'] in ('primary_document', 'full_text')):
                    status.setdefault('document_digests', []).append(digest)
            if not verified:
                status.update(status='original_not_staged', job_id=job['job_id'])
                continue
            if profile['input_kind'] in ('document', 'article') and not set(verified) & set(status.get('document_digests', ())):
                status.update(status='full_document_not_found_in_candidate_jobs', job_id=job['job_id'])
                continue
            batches.append({**snapshot, 'observations': observations, 'observations_sha256': sha(encoded(observations)),
                            'published_observations_sha256': snapshot['observations_sha256']})
            files.append({**refs[0], 'publication_receipt_uri': job['receipt_uri'], 'receipt_sha256': job['manifest_sha256']})
            status.update(status='staged', job_id=job['job_id'], verified_artifacts=sorted(set(verified)))
            break
        print(key, status['status'], flush=True)
    assertions, lookup_status = read_assertions(db, (row for batch in batches for row in batch['observations']))
    handoff = {'version': registry['version'], 'profiles': registry['sources'], 'results': results,
               'entity_industry_lookup_status': lookup_status,
               'frozen': {'batches': batches, 'files': files, 'registry': empty(),
                          'entity_industry_assertions': assertions}}
    save(output / 'handoff.json', handoff)


class StagedReader(ArchivedEvidenceReader):
    def __init__(self, directory):
        self.directory = directory

    def fetch(self, artifact):
        digest = artifact['sha256'].removeprefix('sha256:')
        if len(digest) != 64 or any(letter not in '0123456789abcdef' for letter in digest):
            raise ValueError('invalid archived-artifact digest')
        file = self.directory / digest
        if not file.is_file():
            return None
        raw = file.read_bytes()
        if sha(raw) != digest:
            raise ValueError('staged archived artifact checksum mismatch')
        return raw


def qualify(snapshot, profile, reader):
    hydrated = reader.hydrate(snapshot)
    observation, = hydrated['observations']
    kind = profile['input_kind']
    if kind == 'catalogue':
        return None, 'catalogue_evidence_requires_underlying_original'
    if kind in ('document', 'article'):
        artifacts = {item['sha256']: item for item in observation['raw_artifacts']}
        allowed = []
        for receipt in observation['raw_extraction']['artifacts']:
            artifact = artifacts[receipt['artifact_sha256']]
            if receipt['status'] != 'extracted' or (kind == 'article' and artifact['artifact_kind'] not in ('primary_document', 'full_text')):
                continue
            raw = reader.fetch(artifact)
            # Recognize only complete provider document representations in this profile version.
            if raw and (raw.startswith(b'%PDF-') or b'<html' in raw[:4096].lower()):
                allowed.append(receipt['artifact_sha256'])
        observation['extracted_pages'] = [page for page in observation['extracted_pages'] if page['artifact_sha256'] in allowed]
        if not observation['extracted_pages']:
            return None, 'complete_document_not_supported_or_not_collected'
        if kind == 'article' and any(r.get('limitation') for r in observation['raw_extraction']['artifacts']
                                     if r['artifact_sha256'] in allowed):
            return None, 'article_text_extraction_incomplete'
    else:
        originals = [item for item in observation['raw_artifacts']
                     if item.get('origin') == 'first_party_source' and not item.get('representation')]
        if not originals or not all(reader.fetch(item) is not None for item in originals):
            return None, 'complete_native_evidence_not_staged'
        observation['extracted_pages'] = []
    observation['semiotic_source_profile'] = {'version': profile['profile_version'], 'input_kind': kind,
                                             'source_key': profile['source_key'], 'field_paths': profile.get('field_paths', [])}
    for field in ('subject_status', 'isic_fallback'):
        if field in profile:
            observation['semiotic_source_profile'][field] = profile[field]
    hydrated['observations_sha256'] = sha(encoded(hydrated['observations']))
    return hydrated, None


def work(handoff, archive, assets, output, model, port, *, thesis_model=None, thesis_port=None):
    from semiotic_hybrid import run

    reader = StagedReader(archive)
    frozen = deepcopy(handoff['frozen'])
    profiles = {row['source_key']: row for row in handoff['profiles']}
    results = deepcopy(handoff['results'])
    batches = []
    for batch in frozen['batches']:
        source = batch['observations'][0]['source_key']
        qualified, reason = qualify(batch, profiles[source], reader)
        if qualified:
            batches.append(qualified)
            results[source].update(status='qualified', text_pages=len(qualified['observations'][0]['extracted_pages']))
        else:
            results[source].update(status=reason)
    frozen['batches'] = batches
    output.mkdir(parents=True, exist_ok=True)
    release = None
    if batches:
        release = run(frozen, archives=archive, assets=assets, output=output, model_alias=model, port=port,
                      thesis_model=thesis_model, thesis_port=thesis_port)
        for value in results.values():
            if value['status'] == 'qualified':
                value['status'] = 'processed'
    save(output / 'pilot-results.json', {'version': handoff['version'], 'handoff_sha256': sha(encoded(handoff)),
                                        'release_id': release['release_id'] if release else None, 'sources': results})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    controller = commands.add_parser('prepare')
    worker = commands.add_parser('work')
    for command, flags in ((controller, ('config', 'profiles', 'output')), (worker, ('handoff', 'archive', 'assets', 'output'))):
        for flag in flags:
            command.add_argument('--' + flag, type=Path, required=True)
    worker.add_argument('--model', required=True)
    worker.add_argument('--port', type=int, default=18080)
    worker.add_argument('--thesis-model')
    worker.add_argument('--thesis-port', type=int)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(json.loads(args.config.read_bytes()), json.loads(args.profiles.read_bytes()), args.output)
    else:
        work(json.loads(args.handoff.read_bytes()), args.archive, args.assets, args.output, args.model, args.port,
             thesis_model=args.thesis_model, thesis_port=args.thesis_port)


if __name__ == '__main__':
    main()
