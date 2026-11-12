"""Reconcile the supplied catalog without claiming access or historical coverage."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    text = (ROOT.parent / 'October 24 2026 update.txt').read_text()
    entries = re.findall(r'^(\d{3})\. (.+)$', text, re.M)
    if [int(n) for n, _ in entries] != list(range(1, 159)):
        raise ValueError('Expected the supplied 158-entry ordered catalog')
    existing = {}
    for block in re.split(r'\n(?=\d+\. )', (ROOT / 'data_soucres.md').read_text()):
        number = re.match(r'(\d+)\.', block)
        key = re.search(r'\*\*Source:\*\* `([^`]+)`', block)
        datasets = re.search(r'\*\*Saved dataset\(s\):\*\*(.*)', block)
        if number and int(number[1]) <= 64:
            existing[int(number[1])] = (key[1] if key else 'reddit',
                re.findall(r'`([^`]+)`', datasets[1]) if datasets else [])
    rows = []
    for number, name in entries:
        n = int(number)
        old = existing.get(n)
        source = old[0] if old else re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        # These durable keys belong to distinct publishers, not catalog row numbers.
        source = {77: 'usgs_earthquakes', 79: 'arxiv', 151: 'nsf_awards'}.get(n, source)
        paused = n in {12, 44, 59, 61}
        route = n in {9, 10, 60, 81}
        rows.append({'catalog_entry': n, 'catalog_name': name, 'source_key': source,
            'datasets': old[1] if old else [],
            'lineage': 'existing' if old else 'additional',
            'evidence_role': 'access_or_processing_route' if route else 'publisher',
            'readiness': 'paused' if paused else 'conditional',
            'collector_status': 'existing_route_requires_migration_audit' if old else 'not_implemented',
            'historical_start_target': '2016-01-01',
            'execution_targets': {'historical':'i-06241bd1c4e91c2fc', 'daily':'i-070bab0b09f794629', 'control':'i-070bab0b09f794629'},
            'execution_target_note':'Placement target; implementation and route readiness are separately gated.',
            'verified_earliest_observation': None, 'verified_earliest_publication': None,
            'historical_vintage_support': 'not_audited', 'historical_evidence_tier': 'E' if paused else None,
            'license': None, 'commercial_ml_rights': 'not_audited',
            'last_audited_at': None, 'historical_complete': False,
            'missing_reason': 'operator_paused' if paused else 'not_yet_audited'})
    return {'schema_version': 1, 'catalog_entries': 158,
        'scope_note': 'Catalog rows are not a count of independent publishers or working integrations.',
        'sources': rows}


def coverage(registry):
    for source in registry['sources']:
        for year in range(2016, 2027):
            yield {'catalog_entry': source['catalog_entry'], 'source_key': source['source_key'],
                'year': year, 'country': 'not_audited', 'field': 'not_audited',
                'population': 'not_audited', 'status': 'not_yet_audited',
                'missing_reason': source['missing_reason'], 'verified_complete': False}


if __name__ == '__main__':
    registry = build()
    destination = ROOT / 'config/constellation-source-registry.json'
    if destination.exists():
        raise SystemExit('Refusing to overwrite an existing source audit')
    destination.write_text(json.dumps(registry, indent=2) + '\n')
    with (ROOT / 'config/constellation-coverage-baseline.jsonl').open('w') as handle:
        for row in coverage(registry):
            handle.write(json.dumps(row, sort_keys=True) + '\n')
