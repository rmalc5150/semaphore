"""Local sandbox registry: immutable snapshots and explicit review decisions."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import uuid

from semiotic_sandbox import encoded, identity, normalize, sha

TYPES = {'CIK': 'organization', 'NCT': 'trial', 'DOI': 'publication'}


def empty():
    return seal({'environment': 'sandbox', 'schema_version': 1, 'parent_snapshot_id': None,
                 'entities': [], 'identifiers': [], 'assertions': [], 'decisions': []})


def seal(registry):
    registry.pop('snapshot_id', None)
    registry['snapshot_id'] = identity('registry', registry)
    return registry


def validate(registry):
    content = {k: v for k, v in registry.items() if k != 'snapshot_id'}
    if registry.get('environment') != 'sandbox' or identity('registry', content) != registry['snapshot_id']:
        raise ValueError('registry snapshot checksum mismatch')
    entities = {r['entity_id']: r for r in registry['entities']}
    if len(entities) != len(registry['entities']):
        raise ValueError('duplicate entity ID')
    for item in registry['identifiers']:
        if item['entity_id'] not in entities or TYPES[item['namespace']] != entities[item['entity_id']]['entity_type']:
            raise ValueError('identifier endpoint/type mismatch')


def context(actor, reason, at):
    if not actor.strip() or not reason.strip() or datetime.fromisoformat(at.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('actor, reason and timestamp with timezone required')


def advance(registry):
    validate(registry)
    result = deepcopy(registry)
    result['parent_snapshot_id'] = registry['snapshot_id']
    return result


def discover(registry, release, *, actor, reason, at):
    """Create provisional identities only from extracted ID mentions, never names."""
    context(actor, reason, at)
    expected = identity('release', {k: v for k, v in release.items() if k != 'release_id'})
    if release.get('environment') != 'sandbox' or expected != release['release_id']:
        raise ValueError('graph release checksum mismatch')
    result = advance(registry)
    observations = {r['id']: r for r in release['tables']['observations']}
    for mention in release['tables']['mentions']:
        obs = observations[mention['observation_id']]
        namespace, value = mention['namespace'], normalize(mention['namespace'], mention['value'])
        matches = {r['entity_id'] for r in result['identifiers']
                   if (r['namespace'], normalize(r['namespace'], r['value'])) == (namespace, value)}
        # Conflicting mappings need adjudication; discovery never creates a third.
        if len(matches) > 1:
            continue
        if matches:
            entity_id = next(iter(matches))
        else:
            entity_id = 'ent_' + str(uuid.uuid4())
            result['entities'].append({'entity_id': entity_id, 'entity_type': TYPES[namespace],
                'lifecycle_status': 'provisional', 'canonical_name': None, 'created_at': at})
            result['identifiers'].append({'entity_id': entity_id, 'namespace': namespace,
                'value': value, 'review_status': 'candidate'})
            result['decisions'].append({'decision_id': identity('decision', ['create', entity_id]),
                'entity_id': entity_id, 'action': 'create_provisional', 'actor': actor,
                'reason': reason, 'at': at, 'evidence_ids': [mention['id']]})
        assertion = {'entity_id': entity_id, 'namespace': namespace, 'value': value,
            'mention_id': mention['id'], 'observation_id': mention['observation_id'],
            'raw_s3_uri': obs['raw_s3_uri'], 'raw_sha256': obs['raw_sha256'],
            'page': mention['page'], 'start': mention['start'], 'end': mention['end'], 'quote': mention['quote']}
        assertion['assertion_id'] = identity('assertion', assertion)
        if not any(a['assertion_id'] == assertion['assertion_id'] for a in result['assertions']):
            result['assertions'].append(assertion)
    if all(result[k] == registry[k] for k in ('entities', 'identifiers', 'assertions', 'decisions')):
        return deepcopy(registry)
    return seal(result)


def review(registry, entity_id, *, action, evidence_ids, actor, reason, at, canonical_name=None):
    """Promote/reject only with evidence already registered for this entity.

    A review is an explicit human/policy decision, not inferred verification
    from the syntax of a mention. Timestamp is when the decision became known.
    """
    context(actor, reason, at)
    if action not in ('promote', 'reject'):
        raise ValueError('action must be promote or reject')
    result = advance(registry)
    entity = next((e for e in result['entities'] if e['entity_id'] == entity_id), None)
    if entity is None or entity['lifecycle_status'] != 'provisional':
        raise ValueError('review requires a provisional entity')
    if datetime.fromisoformat(at.replace('Z', '+00:00')) < datetime.fromisoformat(entity['created_at'].replace('Z', '+00:00')):
        raise ValueError('review predates entity creation')
    evidence = {a['assertion_id']: a for a in result['assertions'] if a['entity_id'] == entity_id}
    if not evidence_ids or not set(evidence_ids).issubset(evidence):
        raise ValueError('review evidence must belong to this entity')
    identifiers = [i for i in result['identifiers'] if i['entity_id'] == entity_id]
    if action == 'promote':
        for item in identifiers:
            key = (item['namespace'], normalize(item['namespace'], item['value']))
            if not any((evidence[e]['namespace'], evidence[e]['value']) == key for e in evidence_ids):
                raise ValueError('each promoted identifier needs selected evidence')
            if any(i['entity_id'] != entity_id and
                   (i['namespace'], normalize(i['namespace'], i['value'])) == key for i in result['identifiers']):
                raise ValueError('identifier collision requires adjudication')
    entity['lifecycle_status'] = 'active' if action == 'promote' else 'rejected'
    entity['reviewed_at'] = at
    if canonical_name is not None:
        if not canonical_name.strip():
            raise ValueError('empty canonical name')
        entity['canonical_name'] = canonical_name
    for item in identifiers:
        item['review_status'] = 'verified' if action == 'promote' else 'rejected'
    decision = {'entity_id': entity_id, 'action': action, 'actor': actor, 'reason': reason,
                'at': at, 'evidence_ids': sorted(set(evidence_ids)), 'canonical_name': canonical_name}
    decision['decision_id'] = identity('decision', decision)
    result['decisions'].append(decision)
    return seal(result)


def save(registry, directory):
    validate(registry)
    path = Path(directory) / (registry['snapshot_id'] + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2).encode() + b'\n'
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError('immutable registry snapshot conflict')
    else:
        with path.open('xb') as stream:
            stream.write(body)
    return path


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init', 'discover', 'promote', 'reject'])
    p.add_argument('--registry')
    p.add_argument('--graph')
    p.add_argument('--entity')
    p.add_argument('--evidence', action='append', default=[])
    p.add_argument('--actor')
    p.add_argument('--reason')
    p.add_argument('--at')
    p.add_argument('--name')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if args.action == 'init':
        registry = empty()
    else:
        registry = json.loads(Path(args.registry).read_text())
        kwargs = dict(actor=args.actor or '', reason=args.reason or '', at=args.at or '')
        if args.action == 'discover':
            registry = discover(registry, json.loads(Path(args.graph).read_text()), **kwargs)
        else:
            registry = review(registry, args.entity, action=args.action, evidence_ids=args.evidence,
                              canonical_name=args.name, **kwargs)
    print(save(registry, args.output))


if __name__ == '__main__':
    main()
