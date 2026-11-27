"""Run independent enrichment passes over a verified frozen sandbox sample."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import json
from pathlib import Path
from time import monotonic

from semiotic_batch import run_batches
from semiotic_evidence import unit
from semiotic_grouping import industry_groups
from semiotic_industry import entity_industry_context, entity_references, source_fallback
from semiotic_language import WORDS, token_frequency
from semiotic_sandbox import encoded, evidence_pages, identity, sha, write_release
from semiotic_sectors import VERSION as SECTOR_VERSION
from semiotic_specialists import Geography, Language, SectorRanker, ask, candidate
from semiotic_structured import extract, json_field, profile_fields
from unified_metadata import attach as attach_unified_metadata

VERSION = 'semiotic-hybrid-v5'
FIELDS = ('publisher_country', 'source_type', 'evidence_type', 'identifier', 'date', 'geographic_coverage',
          'population_coverage', 'reported_amount', 'reported_measurement', 'reporting_methodology', 'numerical_table', 'native_file_structure',
          'passage_language', 'english_text', 'svo', 'isic_section', 'isic_division', 'provider_classification',
          'tone', 'thesis', 'technical_claim', 'event_role', 'industry_context', 'industry_actor', 'source_industry_context',
          'source_reported_isic_section', 'source_reported_isic_division', 'entity_reported_isic_section',
          'entity_reported_isic_division')


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_bytes(encoded(value) + b'\n')
    temp.replace(path)


def checkpoint(path, operation):
    started = monotonic()
    if path.exists():
        result = json.loads(path.read_bytes())
    else:
        result = operation()
        write_json(path, result)
    print(json.dumps({'pass': path.stem, 'observations': len(result), 'seconds': round(monotonic() - started, 2)}), flush=True)
    return result


def structured(observations, source_registry, archives):
    output = {}
    for obs_id, row in observations.items():
        result = extract(row, archives)
        result['values'].extend(profile_fields(row))
        source = source_registry.get(row['source_key'], {})
        publisher = source.get('industry_publisher') or row['source_key']
        result['values'].append(candidate('industry_actor', {'name': publisher, 'role': 'publisher'},
                                          'source_identity', {'coordinate_system': 'source_profile',
                                          'source_key': row['source_key'], 'reference': source.get('reference')}))
        if topic := source.get('industry_context'):
            result['values'].append(candidate('source_industry_context', topic, 'source_profile',
                                              {'coordinate_system': 'source_profile', 'source_key': row['source_key'],
                                               'reference': source['reference']}))
        for ref in entity_references(row):
            result['values'].append(candidate('industry_actor', ref, 'metadata_entity_reference',
                                              {'coordinate_system': 'published_observation', 'path': ref.get('path')}))
        for field, key in [('publisher_country', 'region'), ('source_type', 'source_type')]:
            if key in source:
                result['values'].append({'field': field, 'value': source[key], 'method': 'verified-publisher-registry',
                                         'status': 'verified_registry', 'locator': {'source_key': row['source_key'],
                                                                                  'reference': source['reference']}})
        for index, artifact in enumerate(row.get('raw_artifacts', [])):
            if artifact.get('artifact_kind') and not artifact.get('representation'):
                result['values'].append(json_field('evidence_type', artifact['artifact_kind'],
                                                   f'/raw_artifacts/{index}/artifact_kind'))
        native = row['payload'].get('sector_classifications', [])
        for index, label in enumerate(native):
            if label.get('isic_code') and label.get('isic_revision') in (5, '5'):
                from semiotic_sectors import native_industry_pair

                section, division = native_industry_pair(label['isic_code'])
                path = f'/payload/sector_classifications/{index}/isic_code'
                result['values'].append(json_field('isic_section', section.removeprefix('isic_'), path))
                if division:
                    result['values'].append(json_field('isic_division', division.removeprefix('isic_'), path))
        output[obs_id] = result
    return output


def language_pass(observations, structure, assets):
    engine = Language(assets)
    output = {}
    for obs_id, row in observations.items():
        declaration = next((item['value'] for item in structure[obs_id]['values']
                            if item['field'] == 'original_language'), None)
        output[obs_id] = engine.analyze(evidence_pages(row), declaration)
    return output


def english_passages(language, obs_id):
    passages = (item for item in language[obs_id]['values'] if item['field'] == 'english_text')
    return sorted(passages, key=lambda item: (item['locator']['page'], item['locator']['start']))


def scope_pass(observations, language, assets, *, model, port, assertions):
    geography = Geography(assets)
    sectors = SectorRanker(assets)
    result = {}
    def inspect(obs_id):
        row = observations[obs_id]
        page_map = {page['page']: page for page in evidence_pages(row)}
        passages = english_passages(language, obs_id)
        if not passages:
            status = row.get('semiotic_source_profile', {}).get('subject_status', 'unclear') if not page_map else 'unclear'
            return None, None, status, None
        passage = max(passages[:4], key=lambda item: min(len(item['value']), 260))
        loc = passage['locator']
        try:
            context = ask(page_map[loc['page']], loc['start'], loc['end'], 'industry_context', model, port, english=passage)
        except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
            return None, None, 'unclear', type(error).__name__
        return context, passage, context['value']['subject_status'], None

    with ThreadPoolExecutor(max_workers=3) as pool:
        decisions = dict(zip(observations, pool.map(inspect, observations), strict=True))
    for obs_id, row in observations.items():
        pages = evidence_pages(row)
        values = list(geography.extract(pages))
        values.extend(entity_industry_context(row, assertions))
        context, passage, decision, error = decisions[obs_id]
        if context:
            values.append(context)
            for actor in context['value']['actors']:
                values.append(candidate('industry_actor', {k: v for k, v in actor.items() if k != 'locator'},
                                        context['method'], actor['locator']))
        if decision == 'explicit':
            subject = context['value']['object']
            try:
                ranked = sectors.shortlist([passage], subject=subject)
            except (ValueError, RuntimeError) as exc:
                result[obs_id] = {'values': values, 'errors': [{'field': 'isic_section', 'reason': type(exc).__name__}]}
                continue
            values.extend({**item, 'classification_object': subject} for item in ranked)
        result[obs_id] = {'values': values, 'errors': [{'field': 'industry_context', 'reason': error}] if error else []}
    return result


def targeted(observations, structure, language, scopes, model, port, assets, *, thesis_model=None, thesis_port=None):
    jobs = []
    pages = {key: {item['page']: item for item in evidence_pages(row)} for key, row in observations.items()}
    result = {key: {'values': [], 'errors': [], 'attempts': {}} for key in observations}
    for obs_id, row in observations.items():
        known = {item['field'] for item in structure[obs_id]['values']}
        passages = english_passages(language, obs_id)
        excerpts = [item for item in passages if len(WORDS.findall(item['value'])) >= 18]
        has_thesis = row.get('semiotic_source_profile', {}).get('input_kind') in ('document', 'article')
        if excerpts:
            longest = max(excerpts, key=lambda item: len(item['value']))
            jobs.append((obs_id, longest, 'tone', []))
            if has_thesis:
                jobs.append((obs_id, excerpts[0], 'thesis', []))
            if row['source_key'] in ('arxiv', 'nist_robotics_methods'):
                jobs.append((obs_id, longest, 'technical_claim', []))
            if row['source_key'] == 'ted_notices' and 'event_role' not in known:
                jobs.append((obs_id, longest, 'event_role', []))
        elif has_thesis and pages[obs_id] and not passages:
            result[obs_id]['errors'].append({'field': 'thesis', 'reason': 'no_routed_english_evidence'})
            result[obs_id]['attempts']['thesis'] = 'blocked'
        if 'geographic_coverage' not in known:
            mention = next((item for item in scopes[obs_id]['values'] if item['field'] == 'geographic_mention'), None)
            if mention:
                loc = mention['locator']
                covering = next((item for item in passages if item['locator']['page'] == loc['page']
                                 and item['locator']['start'] <= loc['start']
                                 and item['locator']['end'] >= loc['end']), None)
                if covering:
                    jobs.append((obs_id, covering, 'coverage_role', [mention['value']]))
        shortlists = [value for value in scopes[obs_id]['values'] if value['field'] == 'isic_shortlist']
        if shortlists:
            selected = max(shortlists, key=lambda row: row['value'][0]['similarity'])
            passage = next(item for item in passages if item['locator'] == selected['locator'])
            jobs.append((obs_id, passage, 'isic_section', selected['value'], selected['classification_object']))

    def request(job):
        obs_id, passage, task, choices, *subject = job
        locator = passage['locator']
        alias = thesis_model if task == 'thesis' and thesis_model else model
        endpoint = thesis_port if task == 'thesis' and thesis_model else port
        try:
            return obs_id, task, ask(pages[obs_id][locator['page']], locator['start'], locator['end'],
                                     task, alias, endpoint, choices, english=passage,
                                     subject=subject[0] if subject else None), None
        except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
            return obs_id, task, None, type(error).__name__

    validator = None
    with ThreadPoolExecutor(max_workers=3) as pool:
        for obs_id, task, value, error in pool.map(request, sorted(jobs, key=lambda job: job[2] != 'thesis')):
            output = result[obs_id]
            if task == 'thesis' and value:
                try:
                    if validator is None:
                        validator = Language(assets)
                    if validator.detect(value['value']) != 'en' or len(WORDS.findall(value['value'])) > 19:
                        raise ValueError('thesis failed the English or word-count check')
                except (LookupError, OSError, RuntimeError, ValueError) as exc:
                    value, error = None, type(exc).__name__
            output['attempts'][task] = 'failed' if error else 'candidate' if value else 'no_evidence_found'
            if value:
                output['values'].append(value)
            if error:
                output['errors'].append({'field': 'geographic_coverage' if task == 'coverage_role' else task, 'reason': error})
    return result


def annotate_release(release, observations, stages, fingerprint, *, source_registry=None):
    tables = release['tables']
    source_registry = source_registry or {}
    profiles = {row['observation_id']: row for row in tables['observation_profiles']}
    geography = {row['observation_id']: row for row in tables['observation_geography']}
    measurement_obs = {row['observation_id'] for row in tables['measurements']}
    attributes, coverage, triples, translated = [], [], Counter(), []
    for obs_id, row in observations.items():
        page_count = len(evidence_pages(row))
        values = defaultdict(list)
        annotations = [item for stage in stages for item in stage[obs_id]['values']]
        issues = [issue for stage in stages for issue in stage[obs_id]['errors']]
        if not any(item['field'] == 'isic_section' and item.get('classification_object') for item in annotations):
            reason = ('content_classification_failed' if any(item.get('field') in {'industry_context', 'isic_section'}
                      for item in issues) else 'no_supported_content_code')
            annotations.extend(source_fallback(row, source_registry.get(row['source_key'], {}), reason))
        fallback_divisions = {item['method']: item['value'] for item in annotations if item['field'] == 'isic_division'}
        for annotation in annotations:
            if annotation['field'] in {'isic_section', 'isic_division'} and annotation['status'] == 'source_reported':
                annotation = {**annotation, 'field': 'source_reported_' + annotation['field']}
            values[annotation['field']].append(annotation)
            locator = annotation['locator']
            artifact = next((a for a in row.get('raw_artifacts', [])
                             if locator.get('artifact_sha256') and a['sha256'] == locator['artifact_sha256']), None)
            evidence = unit(row, 'hybrid_field_evidence', locator, artifact=artifact)
            item = {**annotation, 'observation_id': obs_id, 'evidence_id': evidence['id'], 'eligible_at': None}
            attributes.append(dict(item, id=identity('hybrid_field', item)))
            tables['evidence_units'].append(evidence)
            if annotation['field'] == 'isic_section' and annotation['status'] == 'candidate':
                sector = {'point_type': 'observation', 'point_id': obs_id, 'observation_id': obs_id,
                          'taxonomy_version': SECTOR_VERSION, 'sector_id': 'isic_' + annotation['value'],
                          'subsector_id': ('isic_' + fallback_divisions[annotation['method']]
                                           if annotation['method'] in fallback_divisions else None),
                          'taxonomy_namespace': 'isic_rev5', 'basis': (annotation['method'] if annotation.get('classification_scope') == 'source'
                                                                      else 'explicit_object_activity'),
                          'status': 'candidate', 'eligible_at': None, 'evidence_id': evidence['id'],
                          'model': annotation['method'], 'actor': annotation.get('actor'),
                          'activity': annotation.get('activity'), 'classification_object': annotation.get('classification_object')}
                sector.update({key: annotation[key] for key in ('source_language', 'translation_method',
                              'english_evidence_quote', 'evidence_alignment', 'classification_scope', 'fallback_reason',
                              'source_code_basis', 'source_topic') if key in annotation})
                tables['sector_attributions'].append(dict(sector, id=identity('sector_attribution', sector)))
            if annotation['field'] == 'english_text':
                translated.append({'english_text': annotation['value']})
            if annotation['field'] in ('svo', 'technical_claim'):
                statement = {'observation_id': obs_id, 'status': 'model_candidate', 'evidence_id': evidence['id'],
                             'extractor': annotation['method'], 'evidence': locator, 'eligible_at': None}
                statement.update({key: annotation[key] for key in ('source_language', 'translation_method',
                                 'english_evidence_quote', 'evidence_alignment') if key in annotation})
                if annotation['field'] == 'svo':
                    triplet = annotation['value']
                    statement.update(triplet)
                    verb = triplet['verb_lemma'].casefold()
                    if triplet['negated']:
                        verb = 'not ' + verb
                    triples[triplet['subject'].casefold(), verb, triplet['object'].casefold()] += 1
                else:
                    statement['statement'] = annotation['value']
                tables['claims'].append(dict(statement, id=identity('claim', statement)))
        for field in FIELDS:
            group = values[field]
            existing_measurement = field == 'reported_measurement' and obs_id in measurement_obs
            selected_industry = field in {'isic_section', 'isic_division'} and bool(group)
            has_issues = not selected_industry and any(
                issue.get('field') == field or 'field' not in issue and field in
                {'numerical_table', 'reported_amount', 'geographic_coverage'} for issue in issues)
            text_only = field in {'population_coverage', 'passage_language', 'english_text', 'svo', 'tone', 'thesis', 'technical_claim', 'event_role'}
            if group:
                status = 'partial' if has_issues else 'reported' if any(item['status'] != 'candidate' for item in group) else 'candidate'
            elif existing_measurement:
                status = 'reported'
            elif has_issues:
                status = 'processing_failed'
            elif text_only and not page_count:
                status = 'not_applicable'
            else:
                status = 'no_evidence_found'
            summary = {'observation_id': obs_id, 'source_key': row['source_key'], 'field': field,
                       'status': status, 'values': len(group) or int(existing_measurement)}
            coverage.append(dict(summary, id=identity('hybrid_coverage', summary)))
        profile = profiles[obs_id]
        language = sorted({item['value'] for item in values['passage_language']})
        if language:
            profile['original_language'] = language[0] if len(language) == 1 else 'mul'
            profile['language_basis'] = ('source_declaration' if all(item['method'] == 'source_declaration'
                                         for item in values['passage_language']) else 'passage_language_detection')
        for field in ('geographic_coverage', 'population_coverage'):
            labels = sorted({item['value'].get('name') or item['value'].get('reference_location') or
                             item['value'].get('label') or f"{item['value'].get('latitude')},{item['value'].get('longitude')}"
                             for item in values[field]})
            if labels:
                for target in (profile, geography[obs_id]):
                    target[field] = labels
                    target['coverage_status'][field] = 'reported' if any(item['status'] == 'source_reported'
                                                                       for item in values[field]) else 'candidate'
        profile['missingness_flags'] = [field for field in profile['missingness_flags']
                                        if not profile.get(field)]
        if values['numerical_table']:
            profile['numerical_table_status'] = 'numeric_table_candidates_found'
        for target, kind in ((profile, 'observation_profile'), (geography[obs_id], 'geography')):
            target['id'] = identity(kind, {k: v for k, v in target.items() if k != 'id'})
    tables['hybrid_field_values'] = attributes
    tables['hybrid_field_coverage'] = coverage
    attribution_ids = defaultdict(set)
    for row in tables['sector_attributions']:
        if row['taxonomy_namespace'] == 'isic_rev5' and row['basis'] == 'source_declared':
            row['selection_status'] = 'context_only'
            row['id'] = identity('sector_attribution', {key: value for key, value in row.items() if key != 'id'})
            continue
        attribution_ids[row['point_type'], row['point_id']].add(row['id'])
    existing = {row['point_id'] for row in tables['sector_coverage'] if row['point_type'] == 'claim'}
    for claim in tables['claims']:
        if claim['id'] not in existing:
            tables['sector_coverage'].append({'point_type': 'claim', 'point_id': claim['id'],
                                              'observation_id': claim['observation_id'], 'taxonomy_version': SECTOR_VERSION})
    for row in tables['sector_coverage']:
        row['attribution_ids'] = sorted(attribution_ids[row['point_type'], row['point_id']])
        row['status'] = 'attributions_present' if row['attribution_ids'] else 'unclassified'
        row['id'] = identity('sector_coverage', {k: v for k, v in row.items() if k != 'id'})
    tables['industry_groups'] = industry_groups(tables['sector_attributions'])
    tables['token_frequency'] = token_frequency(translated)
    subject_pairs = defaultdict(list)
    for (subject, verb, obj), mentions in sorted(triples.items(), key=lambda item: (-item[1], item[0])):
        subject_pairs[subject].append({'verb': verb, 'object': obj, 'mentions': mentions})
    tables['subject_frequency'] = []
    for subject, pairs in subject_pairs.items():
        item = {'subject': subject, 'mentions': sum(pair['mentions'] for pair in pairs), 'verb_objects': pairs,
                'normalization': 'original_language_casefold_and_verb_lemma'}
        tables['subject_frequency'].append(dict(item, id=identity('subject_frequency', item)))
    for name, rows in tables.items():
        by_id = {}
        for item in rows:
            if by_id.setdefault(item['id'], item) != item:
                raise ValueError(f'conflicting {name} value for {item["id"]}')
        tables[name] = sorted(by_id.values(), key=lambda item: item['id'])
    release['version'] = VERSION
    release['frozen_sample_sha256'] = fingerprint
    attach_unified_metadata(release, observations)
    release.pop('release_id')
    release['release_id'] = identity('release', release)


def report(output, release, observations, stages, baseline, wall_seconds):
    tables = release['tables']
    old = defaultdict(list, baseline['tables'] if baseline else {})
    previous = {
        'publisher_country': sum(bool(row['source_region']) for row in old['observation_profiles']),
        'source_type': sum(bool(row['source_type']) for row in old['observation_profiles']),
        'evidence_type': sum(bool(row['evidence_types']) for row in old['observation_profiles']),
        'identifier': sum(bool(row.get('source_record_id')) for row in old['observations']),
        'date': sum(any(row.get(key) for key in ('source_published_at', 'event_at', 'available_at'))
                    for row in old['observations']),
        'passage_language': sum(bool(row['original_language']) for row in old['observation_profiles']),
        'geographic_coverage': sum(bool(row['geographic_coverage']) for row in old['observation_profiles']),
        'population_coverage': sum(bool(row['population_coverage']) for row in old['observation_profiles']),
        'english_text': len({row['observation_id'] for row in old['language_candidates'] if row['english_text']}),
        'svo': len({row['observation_id'] for row in old['language_candidates'] if row['triples']}),
        'tone': len({row['observation_id'] for row in old['language_candidates'] if row['tone']}),
        'isic_section': len({row['observation_id'] for row in old['sector_attributions'] if row['taxonomy_namespace'] == 'isic_rev5'}),
        'isic_division': len({row['observation_id'] for row in old['sector_attributions']
                              if row['taxonomy_namespace'] == 'isic_rev5' and row['subsector_id']}),
        'numerical_table': len({row['observation_id'] for row in old['numerical_tables']}),
        'reported_measurement': len({row['observation_id'] for row in old['measurements']}),
    }
    current = Counter(row['field'] for row in tables['hybrid_field_coverage'] if row['values'])
    current['reported_measurement'] = len({row['observation_id'] for row in tables['measurements']} |
                                         {row['observation_id'] for row in tables['hybrid_field_coverage']
                                          if row['field'] == 'reported_measurement' and row['values']})
    status = defaultdict(Counter)
    source = defaultdict(Counter)
    for row in tables['hybrid_field_coverage']:
        status[row['field']][row['status']] += 1
        if row['values']:
            source[row['source_key']][row['field']] += 1
    metrics = {'release_id': release['release_id'], 'sample_sha256': release['frozen_sample_sha256'],
               'observations': len(observations), 'seconds': round(wall_seconds, 2),
               'comparison_observations': {field: {'previous': previous.get(field) if baseline else None, 'hybrid': current[field]}
                                           for field in FIELDS},
               'status_by_field': status, 'filled_by_source': source,
               'translated_segments': sum(value['translated_segments'] for value in stages[1].values()),
               'targeted_requests': dict(Counter(status for row in stages[3].values() for status in row['attempts'].values())),
               'table_counts': {key: len(rows) for key, rows in tables.items()}}
    comparison = output / 'comparison.json'
    if comparison.exists():
        prior = json.loads(comparison.read_bytes())
        if prior['sample_sha256'] == metrics['sample_sha256']:
            metrics['release_rebuild_seconds'] = metrics['seconds']
            metrics['seconds'] = prior['seconds']
    write_json(comparison, metrics)
    by_obs = defaultdict(dict)
    for row in tables['hybrid_field_coverage']:
        by_obs[row['observation_id']][row['field']] = row['status']
    with (output / 'observation-coverage.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['observation_id', 'source', *FIELDS])
        for obs_id, values in sorted(by_obs.items()):
            writer.writerow([obs_id, observations[obs_id]['source_key'], *(values[value] for value in FIELDS)])
    with (output / 'field-values.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['observation_id', 'source', 'field', 'status', 'method', 'value_json', 'evidence_locator_json'])
        for row in sorted(tables['hybrid_field_values'], key=lambda item: (item['observation_id'], item['field'], item['id'])):
            writer.writerow([row['observation_id'], observations[row['observation_id']]['source_key'], row['field'],
                             row['status'], row['method'], encoded(row['value']).decode(), encoded(row['locator']).decode()])
    print(json.dumps(metrics, indent=2), flush=True)


def run(frozen, *, archives, assets, output, model_alias, port=18080, baseline=None, thesis_model=None, thesis_port=None):
    started = monotonic()
    fingerprint = sha(encoded(frozen))
    observations = {row['observation_id']: row for batch in frozen['batches'] for row in batch['observations']}
    if baseline and set(observations) != {row['id'] for row in baseline['tables']['observations']}:
        raise ValueError('baseline observations differ from frozen sample')
    source_registry = json.loads((Path(__file__).parent / 'config/semiotic-source-regions.json').read_text())
    signature = sha(encoded([VERSION, fingerprint, model_alias, thesis_model, source_registry]))
    checkpoints = output / 'checkpoints' / signature
    checkpoints.mkdir(parents=True, exist_ok=True)

    import torch

    torch.set_num_threads(4)
    structure = checkpoint(checkpoints / '01-structured-v3.json', lambda: structured(observations, source_registry, archives))
    language = checkpoint(checkpoints / '02-language.json', lambda: language_pass(observations, structure, assets))
    scopes = checkpoint(checkpoints / '03-scope.json', lambda: scope_pass(observations, language, assets,
                        model=model_alias, port=port, assertions=frozen.get('entity_industry_assertions', {})))
    model = checkpoint(checkpoints / '04-targeted.json', lambda: targeted(observations, structure, language,
                       scopes, model_alias, port, assets, thesis_model=thesis_model, thesis_port=thesis_port or port))
    release, _ = run_batches(frozen['batches'], frozen['registry'], workers=1,
                             language_options={'source_regions': source_registry})
    stages = structure, language, scopes, model
    annotate_release(release, observations, stages, fingerprint, source_registry=source_registry)
    write_release(release, output / 'releases')
    report(output, release, observations, stages, baseline, monotonic() - started)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('frozen', 'archives', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, default=18080)
    parser.add_argument('--thesis-model')
    parser.add_argument('--thesis-port', type=int)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_bytes()) if args.baseline else None
    run(json.loads(args.frozen.read_bytes()), archives=args.archives, assets=args.assets, output=args.output,
        model_alias=args.model, port=args.port, baseline=baseline, thesis_model=args.thesis_model, thesis_port=args.thesis_port)


if __name__ == '__main__':
    main()
