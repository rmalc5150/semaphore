"""Run a bounded, reproducible sample from published metadata jobs."""
import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path

from semiotic_batch import read_parquet, run_batches
from semiotic_raw_text import ArchivedEvidenceReader
from semiotic_registry import empty
from semiotic_sandbox import encoded, sha, write_release


def sample_batches(snapshots, count):
    """Take a deterministic round robin sample with no repeated observation IDs."""
    if count < 1:
        raise ValueError('sample count must be positive')
    if any(len(snapshot['jobs']) != 1 for snapshot in snapshots):
        raise ValueError('sample each published job individually')
    ordered = sorted(snapshots, key=lambda snapshot: snapshot['jobs'][0])
    candidates = [
        sorted(snapshot['observations'], key=lambda row: row['observation_id'])
        for snapshot in ordered
    ]
    selected = [[] for _ in ordered]
    seen = set()
    for wave in zip_longest(*candidates):
        for index, row in enumerate(wave):
            if row is None or row['observation_id'] in seen:
                continue
            selected[index].append(row)
            seen.add(row['observation_id'])
            if len(seen) == count:
                return [
                    {'environment': 'sandbox', 'jobs': snapshot['jobs'], 'observations': rows,
                     'observations_sha256': sha(encoded(rows))}
                    for snapshot, rows in zip(ordered, selected, strict=True) if rows
                ]
    raise ValueError(f'only {len(seen)} distinct published observations available for requested {count}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--job', action='append')
    source.add_argument('--frozen-input', type=Path, help='reprocess the exact observations from a prior sample')
    parser.add_argument('--metadata-only', action='store_true', help='skip fetching and extracting archived artifacts')
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path(__file__).parent / 'config/metadata-engine.json')
    parser.add_argument('--registry', type=Path, help='optional reviewed registry snapshot')
    parser.add_argument('--llm-model', help='optional model alias served on the same host')
    parser.add_argument('--llm-port', type=int, default=8080)
    parser.add_argument('--llm-parallel', type=int, choices=range(1, 5), default=1,
                        help='concurrent model requests per extraction worker')
    parser.add_argument('--llm-timeout', type=int, choices=(90, 180, 240, 300), default=90,
                        help='model request timeout in seconds')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--record-model-abstentions', action='store_true')
    args = parser.parse_args()
    if args.job or not args.metadata_only:
        import boto3

        config = json.loads(args.config.read_text())
        session = boto3.Session(region_name=config['region'])
        s3 = session.client('s3')
    if args.frozen_input:
        saved = json.loads(args.frozen_input.read_text())
        batches, files = saved['batches'], saved['files']
        if sum(len(batch['observations']) for batch in batches) != args.count:
            raise ValueError('frozen sample observation count disagrees with requested count')
        registry = saved['registry']
    else:
        glue = session.client('glue')
        snapshots, files = [], []
        for job in sorted(set(args.job)):
            snapshot, refs = read_parquet(glue, s3, [job], config['bucket'], config['prefix'])
            snapshots.append(snapshot)
            files.extend(refs)
        batches = sample_batches(snapshots, args.count)
        registry = empty()
    if args.registry:
        registry = json.loads(args.registry.read_text())
    if not args.metadata_only:
        archived = ArchivedEvidenceReader(s3, config['bucket'])
        batches = [archived.hydrate(batch) for batch in batches]
    source_regions = Path(__file__).parent / 'config/semiotic-source-regions.json'
    release, _ = run_batches(batches, registry, workers=args.workers, language_options={
        'source_regions': json.loads(source_regions.read_text()),
        'model': args.llm_model, 'port': args.llm_port,
        'record_invalid': args.record_model_abstentions, 'parallel': args.llm_parallel,
        'timeout': args.llm_timeout,
    })
    tables = release['tables']
    if len(tables['observations']) != args.count:
        raise RuntimeError('output observation count disagrees with selected sample')
    root = write_release(release, args.output / 'releases')
    inputs = {'files': files, 'batches': batches, 'registry': registry}
    receipt = {
        'release_id': release['release_id'], 'graph': str(root / 'graph.json'),
        'source_counts': dict(Counter(row['source_key'] for row in tables['observations'])),
        'table_counts': {name: len(rows) for name, rows in tables.items()},
        'industry_grouped_observations': len({row['point_id'] for row in tables['industry_groups']
                                              if row['point_type'] == 'observation'}),
        'archive_extraction_status': dict(Counter(row['status'] for row in tables['raw_extraction'])),
        'sample_sha256': sha(encoded(inputs)),
    }
    for name, value in (('sample-input', inputs), ('sample-outcome', receipt)):
        path = args.output / f'{release["release_id"]}-{name}.json'
        body = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
        if path.exists():
            if path.read_text() != body:
                raise ValueError(f'existing sample artifact differs: {path}')
        else:
            with path.open('x') as stream:
                stream.write(body)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
