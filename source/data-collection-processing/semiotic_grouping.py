"""ISIC membership, embedding neighborhoods, and sandbox grouping evaluation."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from semiotic_sandbox import encoded, identity, sha


def industry_groups(attributions):
    """Roll up all supported ISIC attributions to their section, even without a division."""
    groups = defaultdict(lambda: {'divisions': set(), 'attributions': set(), 'statuses': set()})
    for item in attributions:
        if item['taxonomy_namespace'] != 'isic_rev5' or item.get('selection_status') == 'context_only':
            continue
        key = (item['point_type'], item['point_id'], item['taxonomy_version'], item['sector_id'])
        group = groups[key]
        group['attributions'].add(item['id'])
        group['statuses'].add(item['status'])
        if item.get('subsector_id'):
            group['divisions'].add(item['subsector_id'])
    return [{
        'id': identity('isic_membership', [key, sorted(group['attributions'])]),
        'point_type': key[0], 'point_id': key[1], 'taxonomy_version': key[2],
        'section_id': key[3], 'division_ids': sorted(group['divisions']),
        'attribution_ids': sorted(group['attributions']), 'attribution_statuses': sorted(group['statuses']),
        'historically_eligible': False,
    } for key, group in sorted(groups.items())]


def instant(text):
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise ValueError('grouping timestamps require a timezone')
    return value.astimezone(timezone.utc)


def similarity_groups(tables, spec):
    """Build bounded, overlapping neighborhoods from one supplied embedding revision."""
    vectors = spec['embeddings']
    if len(vectors) > 512:
        raise ValueError('sandbox similarity input is limited to 512 embeddings')
    cutoff = instant(spec['as_of'])
    model, threshold = spec['model_revision'], spec.get('min_cosine', 0.8)
    if not isinstance(model, str) or not model.strip() or not 0 < threshold <= 1:
        raise ValueError('similarity requires a model revision and min_cosine in (0, 1]')
    points = {(row['point_type'], row['point_id']): row['observation_id'] for row in tables['sector_coverage']}
    evidence = {row['id']: row['observation_id'] for row in tables['evidence_units']}
    neighborhoods = {}
    dimension = None
    for row in vectors:
        key = row['point_type'], row['point_id']
        if key not in points or evidence.get(row['evidence_id']) != points[key] or row['model_revision'] != model:
            raise ValueError('embedding requires a known point, matching evidence, and the pinned model revision')
        if row.get('eligible_at') is None or instant(row['eligible_at']) > cutoff:
            continue
        vector = row['vector']
        if (not 0 < len(vector) <= 4096 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)):
            raise ValueError('embedding vector is empty, oversized, or non-finite')
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or not norm or key in neighborhoods or dimension not in (None, len(vector)):
            raise ValueError('invalid norm, duplicate point, or inconsistent embedding dimension')
        dimension = len(vector)
        neighborhoods[key] = (row, [v / norm for v in vector])
    neighbors = defaultdict(list)
    keys = sorted(neighborhoods)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            if left[0] != right[0]:
                continue
            a, b = neighborhoods[left][1], neighborhoods[right][1]
            score = max(-1.0, min(1.0, math.fsum(x * y for x, y in zip(a, b))))
            if score >= threshold:
                neighbors[left].append((right, score))
                neighbors[right].append((left, score))
    result = []
    for anchor in keys:
        if not neighbors[anchor]:
            continue
        nearest = sorted(neighbors[anchor], key=lambda item: (-item[1], item[0]))[:10]
        group = {'point_type': anchor[0], 'anchor_id': anchor[1],
                 'anchor_evidence_id': neighborhoods[anchor][0]['evidence_id'],
                 'members': [{'point_id': key[1], 'cosine': score,
                              'evidence_id': neighborhoods[key][0]['evidence_id'],
                              'embedding_sha256': sha(encoded(neighborhoods[key][0]))}
                             for key, score in nearest],
                 'anchor_embedding_sha256': sha(encoded(neighborhoods[anchor][0])),
                 'as_of': cutoff.isoformat(), 'min_cosine': threshold, 'model_revision': model,
                 'status': 'similarity_hypothesis', 'historically_eligible': False}
        result.append(dict(group, id=identity('similarity_group', group)))
    return result


def evaluate(tables, judgments, *, k=5):
    if k < 1:
        raise ValueError('retrieval cutoff must be positive')
    membership = defaultdict(set)
    known = {(row['point_type'], row['point_id']) for row in tables['sector_coverage']}
    for item in tables['industry_groups']:
        key = item['point_type'], item['point_id']
        membership[key, 'section'].add(item['section_id'])
        membership[key, 'division'].update(item['division_ids'])

    def labels(point_type, point_id, level):
        key = point_type, point_id
        if key not in known:
            raise ValueError(f'unknown evaluation point: {key}')
        return membership[key, level]

    pairs = defaultdict(list)
    for item in judgments.get('pairs', []):
        criterion, level = item['criterion'], item.get('level', 'section')
        if criterion not in ('stability', 'separation') or level not in ('section', 'division'):
            raise ValueError('invalid pair criterion or grouping level')
        if item['left'] == item['right']:
            raise ValueError('pair must contain distinct points')
        point_type = item.get('point_type', 'observation')
        left, right = (labels(point_type, item[key], level) for key in ('left', 'right'))
        result = (bool(left & right) == (criterion == 'stability')) if left and right else None
        pairs[criterion, level, item.get('scenario', 'unspecified')].append(result)
    pair_report = []
    for (criterion, level, scenario), results in sorted(pairs.items()):
        evaluated = sum(value is not None for value in results)
        passed = sum(value is True for value in results)
        pair_report.append({'criterion': criterion, 'level': level, 'scenario': scenario,
                            'total': len(results), 'evaluated': evaluated, 'passed': passed,
                            'abstained': len(results) - evaluated,
                            'pass_rate': passed / evaluated if evaluated else None})

    def scores(ranked, relevant):
        return {'recall_at_k': len(set(ranked[:k]) & relevant) / len(relevant),
                'reciprocal_rank_at_k': next((1 / i for i, point in enumerate(ranked[:k], 1)
                                              if point in relevant), 0)}

    retrieval = []
    semantic_neighbors = {(row['point_type'], row['anchor_id']): {item['point_id'] for item in row['members']}
                          for row in tables.get('similarity_groups', [])}
    for query in judgments.get('retrieval', []):
        point_type = query.get('point_type', 'observation')
        anchor = query['anchor']
        base, relevant = query['baseline_ranking'], set(query['relevant'])
        if not relevant or len(base) != len(set(base)) or anchor in base or anchor in relevant:
            raise ValueError('retrieval needs unique non-anchor candidates and relevance judgments')
        query_labels = labels(point_type, anchor, 'section')
        for point in relevant:
            labels(point_type, point, 'section')
        ranked = sorted(base, key=lambda point: not bool(query_labels & labels(point_type, point, 'section')))
        nearby = semantic_neighbors.get((point_type, anchor), set())
        semantic_ranked = sorted(base, key=lambda point: point not in nearby)
        retrieval.append({'anchor': anchor, 'baseline': scores(base, relevant),
                          'isic_reranked': scores(ranked, relevant),
                          'similarity_reranked': scores(semantic_ranked, relevant),
                          'similarity_available': bool(nearby)})
    metrics = {}
    for metric in ('recall_at_k', 'reciprocal_rank_at_k'):
        base, grouped, semantic = (
            sum(row[method][metric] for row in retrieval) / len(retrieval) if retrieval else None
            for method in ('baseline', 'isic_reranked', 'similarity_reranked'))
        metrics[metric] = {'baseline': base, 'isic_reranked': grouped,
                           'isic_delta': grouped - base if retrieval else None,
                           'similarity_reranked': semantic,
                           'similarity_delta': semantic - base if retrieval else None}
    return {'pairs': pair_report, 'retrieval': {'k': k, 'queries': retrieval, 'mean_metrics': metrics}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True, help='sandbox graph.json')
    parser.add_argument('--judgments', type=Path, required=True,
                        help='JSON with pairs and retrieval relevance judgments')
    parser.add_argument('--k', type=int, default=5)
    args = parser.parse_args()
    release = json.loads(args.release.read_text())
    judgments = json.loads(args.judgments.read_text())
    content = {key: value for key, value in release.items() if key != 'release_id'}
    if identity('release', content) != release['release_id']:
        raise ValueError('release checksum mismatch')
    report = evaluate(release['tables'], judgments, k=args.k)
    print(json.dumps({'release_id': release['release_id'], 'judgments_sha256': sha(encoded(judgments)),
                      **report}, indent=2))


if __name__ == '__main__':
    main()
