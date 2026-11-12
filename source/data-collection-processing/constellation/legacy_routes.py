"""Reviewed historical command routes. Queue parameters never supply commands."""
from datetime import date
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'legacy-migration-v1'


def manifest():
    return json.loads((ROOT / 'config/constellation-legacy-routes.json').read_text())


def route(unit):
    matches = [r for r in manifest()['routes'] if r['unit'] == unit]
    if len(matches) != 1:
        raise ValueError('Unknown historical route')
    return matches[0]


def route_hash(row):
    return hashlib.sha256(json.dumps(row['argv'],sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_spec(spec):
    if spec['source_key'] != 'legacy:' + spec['parameters'].get('unit',''):
        raise ValueError('Historical source/route mismatch')
    row = route(spec['parameters']['unit'])
    if not row['execution_enabled']:
        raise ValueError('Historical route is staged but not validated: ' + row['unit'])
    if set(spec['parameters']) != {'unit','route_sha256','dispatch_slot'} or spec['parameters']['route_sha256'] != route_hash(row):
        raise ValueError('Historical command version mismatch')
    if spec['extractor_version'] != VERSION or spec['dataset'] != 'legacy_historical_invocation' or spec['edition'] != 'pinned_legacy_checkpoint':
        raise ValueError('Invalid historical invocation contract')
    if spec['start'] != row['start_target'] or spec['end'] != row['end_exclusive'] or spec['geography'] != 'configured_legacy_scope':
        raise ValueError('Historical scope mismatch')
    if date.fromisoformat(spec['start']) >= date.fromisoformat(spec['end']):
        raise ValueError('Empty historical scope')


def specification(row, slot):
    return {'source_key':'legacy:'+row['unit'],'dataset':'legacy_historical_invocation',
        'geography':'configured_legacy_scope','start':row['start_target'],'end':row['end_exclusive'],
        'edition':'pinned_legacy_checkpoint','extractor_version':VERSION,
        'parameters':{'unit':row['unit'],'route_sha256':route_hash(row),'dispatch_slot':str(slot)}}
