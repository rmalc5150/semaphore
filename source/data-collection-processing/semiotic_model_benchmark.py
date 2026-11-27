"""Compare local language models on shared probes and archived passages."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import statistics
from time import monotonic

from jsonschema.exceptions import ValidationError

from semiotic_language import PROMPT_VERSION, analyze_chunk

PROBES = (
    ('factory', 'Acme manufactures batteries in Germany.', 'Germany', 'isic_C'),
    ('insurance', 'Atlas insures a German battery factory against fire.', 'German', 'isic_L'),
    ('spanish', 'Acme fabrica baterías en España.', 'España', 'isic_C'),
    ('no_geography', 'Atlas provides insurance services.', None, 'isic_L'),
)


def cases(graph_path, *, probes_only=False):
    for key, sentence, region, sector in PROBES:
        yield {'id': key, 'observation_id': key, 'page': 1, 'start': 0, 'text': sentence}, {
            'region': region, 'sector': sector}
    if probes_only:
        return
    graph = json.loads(graph_path.read_text())['tables']
    sources = {row['id']: row['source_key'] for row in graph['observations']}
    chosen = defaultdict(int)
    for chunk in sorted(graph['chunks'], key=lambda row: (-len(row['text']), row['id'])):
        source = sources[chunk['observation_id']]
        if chosen[source] < 1 and chunk['text'].strip():
            yield chunk, None
            chosen[source] += 1


def benchmark(graph_path, alias, port, *, probes_only=False, timeout=90):
    rows = []
    for chunk, expected in cases(graph_path, probes_only=probes_only):
        start = monotonic()
        record = {'chunk_id': chunk['id'], 'expected': expected}
        try:
            result = analyze_chunk(chunk, alias, port, record_invalid=True, timeout=timeout)
        except (ValueError, ValidationError, KeyError, TypeError, IndexError, TimeoutError) as error:
            record['error'] = type(error).__name__
        else:
            record['result'] = result
            if expected:
                regions = {item['label'].casefold() for item in result['geographic_coverage']}
                sectors = {item['sector_id'] for item in result['sector_classifications']}
                expected_region = expected['region']
                record['region_match'] = expected_region.casefold() in regions if expected_region else not regions
                record['sector_match'] = expected['sector'] in sectors
        record['seconds'] = round(monotonic() - start, 3)
        rows.append(record)
        print(f'{alias} case {len(rows)} {record.get("error", "returned")} {record["seconds"]:.1f}s', flush=True)
    accepted = [row for row in rows if 'result' in row]
    return {
        'model': alias, 'prompt_version': PROMPT_VERSION, 'input_graph_sha256': sha256(graph_path.read_bytes()).hexdigest(),
        'finished_at': datetime.now(timezone.utc).isoformat(), 'request_timeout_seconds': timeout, 'cases': rows,
        'summary': {
            'attempted': len(rows), 'returned': len(accepted),
            'with_evidence_linked_triples': sum(bool(row['result']['triples']) for row in accepted),
            'with_evidence_linked_tone': sum(row['result']['tone'] is not None for row in accepted),
            'rejected_annotations': sum(len(row['result'].get('validation_issues', [])) for row in accepted),
            'gold_region_matches': sum(row.get('region_match', False) for row in rows),
            'gold_sector_matches': sum(row.get('sector_match', False) for row in rows),
            'gold_cases': len(PROBES), 'median_seconds': round(statistics.median(row['seconds'] for row in rows), 3),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--graph', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probes-only', action='store_true')
    parser.add_argument('--timeout', type=int, choices=(90, 180, 240, 300), default=90)
    args = parser.parse_args()
    report = benchmark(args.graph, args.model, args.port, probes_only=args.probes_only, timeout=args.timeout)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
