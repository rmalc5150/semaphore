#!/usr/bin/env python3
"""Evidence-backed, reversible exclusions for exact market listing/date scopes."""
import argparse
from copy import deepcopy
from datetime import date, datetime
import fcntl
import hashlib
import json
import re
from pathlib import Path
from uuid import uuid4

from collection_storage import StorageSettings, now, write_json
from research_contract import ROOT, digest, load_json

REASONS = {'pre_ipo', 'post_delisting', 'documented_unavailable'}
SUCCESS = {'complete', 'excluded'}


def validate(decision, stream_id):
    required = {'stream_id', 'source', 'symbol', 'listing_ids', 'start', 'end_exclusive',
                'reason', 'explanation', 'evidence', 'reviewer', 'reviewed_at'}
    if required - decision.keys() or decision.keys() - required - {'boundary_date'}:
        raise ValueError('Coverage exclusion is missing required review fields')
    if decision['stream_id'] != stream_id or decision['source'] != 'eodhd_market':
        raise ValueError('Coverage exclusion scope does not match this market stream')
    if decision['reason'] not in REASONS or not all(isinstance(decision[k], str) and decision[k].strip()
            for k in ('symbol', 'explanation', 'reviewer')):
        raise ValueError('Invalid coverage exclusion reason or explanation')
    start, end = date.fromisoformat(decision['start']), date.fromisoformat(decision['end_exclusive'])
    if (not start < end or str(start) != decision['start'] or str(end) != decision['end_exclusive'] or
            not isinstance(decision['listing_ids'], list) or not decision['listing_ids'] or
            not all(isinstance(v, str) and v for v in decision['listing_ids']) or
            len(set(decision['listing_ids'])) != len(decision['listing_ids']) or
            not isinstance(decision['evidence'], list) or not decision['evidence']):
        raise ValueError('Coverage exclusions require a finite interval, listing IDs and evidence')
    if datetime.fromisoformat(decision['reviewed_at'].replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Coverage exclusion review time needs a timezone')
    if decision['reason'] in {'pre_ipo', 'post_delisting'}:
        boundary = date.fromisoformat(decision['boundary_date'])
        if (decision['reason'] == 'pre_ipo' and end > boundary or
                decision['reason'] == 'post_delisting' and start < boundary):
            raise ValueError('Coverage exclusion crosses its documented trading boundary')
    for item in decision['evidence']:
        if not all(isinstance(item.get(k), str) and item[k] for k in ('key', 'sha256', 'source_url')):
            raise ValueError('Each evidence item needs a saved key, SHA-256 and source URL')
        if not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid evidence SHA-256')


class Exclusions:
    def __init__(self, store, prefix, listings=None, document=None):
        self.store, self.prefix, self.listings = store, prefix, listings
        self.stream_id = prefix.rsplit('/', 1)[-1]
        self.key = prefix + '/coverage-exclusions.json'
        saved = store.get(self.key) if store is not None and document is None else None
        self.token = saved.token if saved else None
        self.document = document if document is not None else (json.loads(saved.body) if saved else {
            'schema_version': 1, 'stream_id': self.stream_id, 'decisions': {}})
        if self.document.get('stream_id') != self.stream_id or self.document.get('schema_version') != 1:
            raise ValueError('Invalid market coverage exclusion registry')
        for identity, entry in self.document['decisions'].items():
            validate(entry['decision'], self.stream_id)
            if identity != 'exclusion_' + digest(entry['decision']) or entry['status'] not in {'active', 'revoked'}:
                raise ValueError('Coverage exclusion integrity mismatch')

    def match(self, symbol, start, end):
        if not start or not end or start >= end:
            return None
        for identity, entry in sorted(self.document['decisions'].items()):
            d = entry['decision']
            if (entry['status'] == 'active' and d['symbol'] == symbol and
                    d['start'] <= start and end <= d['end_exclusive'] and
                    (self.listings is None or sorted(d['listing_ids']) == self.listings.get(symbol))):
                return {**d, 'id': identity}
        return None

    def _save(self, event):
        event = {**event, 'at': now(), 'stream_id': self.stream_id}
        receipt = self.prefix + '/coverage-exclusion-events/' + str(uuid4()) + '.json'
        write_json(self.store, receipt, event)
        self.document.update(updated_at=event['at'], latest_event=receipt)
        self.token = write_json(self.store, self.key, self.document, self.token)
        return receipt

    def add(self, decision):
        validate(decision, self.stream_id)
        if self.listings is None or sorted(decision['listing_ids']) != self.listings.get(decision['symbol']):
            raise ValueError('Coverage exclusion does not match the current provider listing IDs')
        for item in decision['evidence']:
            obj = self.store.get(item['key'])
            if obj is None or hashlib.sha256(obj.body).hexdigest() != item['sha256']:
                raise ValueError('Coverage exclusion evidence hash mismatch or missing evidence')
        identity = 'exclusion_' + digest(decision)
        if identity in self.document['decisions']:
            if self.document['decisions'][identity]['status'] == 'revoked':
                raise ValueError('A revoked exclusion needs a new review before reactivation')
            return identity
        self.document['decisions'][identity] = {'status': 'active', 'decision': deepcopy(decision)}
        self._save({'action': 'exclude', 'id': identity, 'decision': decision})
        return identity

    def revoke(self, identity, reviewer, explanation):
        if not reviewer.strip() or not explanation.strip():
            raise ValueError('Revocation needs a reviewer and explanation')
        entry = self.document['decisions'][identity]
        if entry['status'] == 'revoked':
            return
        entry.update(status='revoked', revoked_at=now(), revoked_by=reviewer, revocation_reason=explanation)
        self._save({'action': 'revoke', 'id': identity, 'reviewer': reviewer, 'explanation': explanation})


def excluded_window(registry, decision, start, end, prior=None):
    prior = prior or {}
    return {'status': 'excluded', 'reason': decision['reason'], 'window_start': start,
            'end_exclusive': end, 'exclusion_id': decision['id'], 'registry_key': registry.key,
            'explanation': decision['explanation'], 'evidence': decision['evidence'],
            'prior_manifest': prior.get('manifest') or prior.get('prior_manifest'),
            'prior_reason': prior.get('prior_reason') if 'prior_reason' in prior else prior.get('reason'),
            'coverage': 'Explained exclusion; no claim of collected prices or corporate actions.'}


def reconcile_state(state, lane, registry):
    """Move explained gaps to a separate ledger; revocation restores pending work."""
    result = deepcopy(state)
    for symbol, item in result.get('symbols', {}).items():
        excluded = item.get('excluded_windows', {})
        for start, old in list(excluded.items()):
            decision = registry.match(symbol, start, old['end_exclusive'])
            if decision:
                excluded[start] = excluded_window(registry, decision, start, old['end_exclusive'], old)
                continue
            del excluded[start]
            gap = {'end_exclusive': old['end_exclusive'], 'manifest': old.get('prior_manifest'),
                   'reason': 'coverage_exclusion_revoked'}
            if lane == 'historical' or item.get('scan_next_date'):
                item.setdefault('gaps', {})[start] = gap
            item['next_date'] = min(start, item.get('next_date', start))
            item.update(last_result={'status': 'partial', **gap}, window_start=start,
                        window_end_exclusive=old['end_exclusive'])
            item.pop('retry_after', None)
        for start, gap in list(item.get('gaps', {}).items()):
            decision = registry.match(symbol, start, gap.get('end_exclusive'))
            if decision:
                excluded[start] = excluded_window(registry, decision, start, gap['end_exclusive'], gap)
                del item['gaps'][start]
        start, end = item.get('window_start'), item.get('window_end_exclusive')
        decision = registry.match(symbol, start, end)
        if decision and item.get('last_result', {}).get('status') != 'complete':
            excluded[start] = excluded_window(registry, decision, start, end, item.get('last_result'))
            item['last_result'] = excluded[start]
            if lane == 'daily':
                item['next_date'] = max(end, item.get('next_date', end))
                if item.get('scan_next_date'):
                    item['scan_next_date'] = max(end, item['scan_next_date'])
            item.pop('retry_after', None)
        if excluded or 'excluded_windows' in item:
            item['excluded_windows'] = excluded
        if item.get('scan_next_date'):
            item['next_date'] = min(item['gaps']) if item.get('gaps') else item['scan_next_date']
    return result


def unresolved(item):
    return bool(item.get('gaps')) or item.get('last_result', {}).get('status') not in SUCCESS


def report(states, registry):
    lanes = {}
    for lane, state in states.items():
        symbols = (state or {}).get('symbols', {})
        lanes[lane] = {'unresolved_symbols': sum(unresolved(v) for v in symbols.values()),
                       'unresolved_gap_windows': sum(len(v.get('gaps', {})) for v in symbols.values()),
                       'excluded_windows': [{'symbol': s, **w} for s, v in symbols.items()
                                            for w in v.get('excluded_windows', {}).values()]}
    return {'registry_key': registry.key, 'stream_id': registry.stream_id,
            'decisions': registry.document['decisions'], 'lanes': lanes,
            'coverage': 'Excluded windows are explained missing coverage, never collected data.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    apply = sub.add_parser('apply'); apply.add_argument('file', type=Path)
    revoke = sub.add_parser('revoke'); revoke.add_argument('id'); revoke.add_argument('--reviewer', required=True); revoke.add_argument('--explanation', required=True)
    review = sub.add_parser('report'); review.add_argument('--output', type=Path)
    sub.add_parser('reconcile')
    args = parser.parse_args()
    from market_operations import MarketOperations
    config = load_json(ROOT/'config/market-operations.json')
    settings = StorageSettings.load(ROOT/config['storage_config'])
    with (ROOT/'.market-collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = MarketOperations(settings.store(), settings, config, load_json(ROOT/config['universe']), load_json(ROOT/config['taxonomy']))
        registry = Exclusions(runner.store, runner.prefix, runner.symbols)
        if args.command == 'apply':
            decisions = load_json(args.file)
            # Validate every proof before writing any registry changes.
            for decision in decisions:
                validate(decision, registry.stream_id)
                if sorted(decision['listing_ids']) != runner.symbols.get(decision['symbol']):
                    raise ValueError('Listing scope mismatch')
                for proof in decision['evidence']:
                    saved = runner.store.get(proof['key'])
                    if saved is None or hashlib.sha256(saved.body).hexdigest() != proof['sha256']:
                        raise ValueError('Coverage exclusion evidence hash mismatch')
            for decision in decisions:
                registry.add(decision)
        elif args.command == 'revoke':
            registry.revoke(args.id, args.reviewer, args.explanation)
        states = runner.reconcile_exclusions(registry, persist=args.command != 'report')
        result = report(states, registry)
        output = json.dumps(result, indent=2) + '\n'
        if args.command == 'report' and args.output:
            args.output.write_text(output)
        print(output)


if __name__ == '__main__':
    main()
