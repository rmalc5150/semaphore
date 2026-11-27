"""Join a published metadata snapshot and its semiotic annotations at observation granularity."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
import re
from uuid import UUID

from metadata_engine.graph import links, stable_id
from semiotic_language import WORDS
from semiotic_sandbox import encoded, evidence_pages, identity, sha, write_release

VERSION = 'unified-metadata-v1'
UUID_LITERAL = re.compile(r'(?<![\w-])(?:[a-z][a-z0-9]{1,24}_)?'
                          r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?![\w-])', re.I)
REGIONAL = {'publisher_country', 'geographic_coverage', 'geographic_mention', 'population_coverage'}
STRUCTURED = {'source_type', 'evidence_type', 'identifier', 'date', 'reported_amount', 'reported_measurement',
              'reporting_methodology', 'numerical_table', 'provider_classification', 'native_file_structure'}
INDUSTRY = {'isic_section', 'isic_division', 'isic_shortlist', 'industry_context', 'industry_actor',
            'source_industry_context', 'source_reported_isic_section', 'source_reported_isic_division',
            'entity_reported_isic_section', 'entity_reported_isic_division'}


def pointer(path, key):
    return path + '/' + str(key).replace('~', '~0').replace('/', '~1')


def uuid_values(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from uuid_values(child, pointer(path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from uuid_values(child, pointer(path, index))
    elif isinstance(value, str):
        for match in UUID_LITERAL.finditer(value):
            yield str(UUID(match[1])), match[0], path, match.start(), match.end()


def group(rows, key):
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return result


def frequencies(fields):
    english = Counter(token.casefold() for row in fields.get('english_text', ())
                      for token in WORDS.findall(row['value']))
    svo = Counter()
    for row in fields.get('svo', ()):
        value = row['value']
        verb = ('not ' if value['negated'] else '') + value['verb_lemma'].casefold()
        svo[value['subject'].casefold(), verb, value['object'].casefold()] += 1
    return {'english_tokens': dict(english),
            'subject_verb_object': [{'subject': s, 'verb': v, 'object': o, 'count': count}
                                    for (s, v, o), count in sorted(svo.items())]}


def attach(release, observations):
    """Add the consumer view and UUID index without changing existing observation or entity IDs."""
    tables = release['tables']
    if set(observations) != {row['id'] for row in tables['observations']}:
        raise ValueError('metadata and semiotic observation IDs differ')
    by_observation = {name: group(tables.get(name, ()), 'observation_id') for name in (
        'observation_profiles', 'hybrid_field_values', 'hybrid_field_coverage', 'sector_attributions',
        'sector_coverage', 'sector_source_codes', 'measurements', 'numerical_tables', 'claims', 'mentions',
        'publication_inputs', 'raw_extraction', 'evidence_units', 'language_candidates', 'language_failures')}
    bindings = group(tables.get('bindings', ()), 'mention_id')
    edges = group(tables.get('edges', ()), 'subject_id')
    entities = {row['id']: row for row in tables.get('entities', ())}
    by_event = defaultdict(list)
    for event in tables.get('event_versions', ()):
        for evidence in event.get('evidence', ()):
            by_event[evidence['observation_id']].append(event)
    bundled, index = [], {}
    for obs_id, source in sorted(observations.items()):
        related = {name: groups.get(obs_id, []) for name, groups in by_observation.items()}
        fields = group(related['hybrid_field_values'], 'field')
        source_metadata = {key: value for key, value in source.items() if key not in ('extracted_pages', 'raw_extraction')}
        event = stable_id(['source_record_event', source['source_key'], source['dataset'], source['source_record_id']])
        version = stable_id(['version', obs_id])
        native_links = [{'namespace': namespace, 'value': value, 'name': name, 'role': role, 'entity_type': kind,
                         'entity_uuid': str(stable_id([kind, namespace, value])), 'status': 'candidate',
                         'basis': 'metadata_engine_direct_identifier_rule'}
                        for kind, namespace, value, name, role in links(source)]
        mention_bindings = [link for mention in related['mentions'] for link in bindings.get(mention['id'], ())]
        entity_ids = {candidate for binding in mention_bindings for candidate in binding.get('candidates', ())}
        registry_entities = [entities[key] for key in sorted(entity_ids) if key in entities]
        identity_data = {'record_id': source['record_id'], 'observation_id': obs_id,
                         'source_observation_id': source.get('source_observation_id'),
                         'provider_record_id': source['source_record_id'],
                         'metadata_graph': {'source_record_event_uuid': str(event), 'event_version_uuid': str(version),
                                            'status': 'derived_using_metadata_engine_key_rule'},
                         'source_identifier_links': native_links, 'identifier_fields': fields.get('identifier', []),
                         'mentions': related['mentions'], 'bindings': mention_bindings, 'entities': registry_entities}
        refs = {}

        def collect(value, origin, locator):
            for uuid, literal, path, start, end in uuid_values(value):
                ref = {'uuid': uuid, 'literal': literal, 'observation_id': obs_id, 'origin': origin,
                       'locator': {**locator, 'path': path, 'start': start, 'end': end}}
                ref['id'] = identity('uuid_occurrence', ref)
                refs[ref['id']] = ref

        collect(source_metadata, 'source_observation', {'coordinate_system': 'published_observation_json_pointer'})
        collect(identity_data['metadata_graph'], 'metadata_graph_reference', {'coordinate_system': 'json_pointer', 'section': 'identity/metadata_graph'})
        collect(native_links, 'metadata_graph_candidate', {'coordinate_system': 'json_pointer', 'section': 'identity/source_identifier_links'})
        collect(identity_data['identifier_fields'], 'semiotic_identifier_evidence', {'coordinate_system': 'json_pointer', 'section': 'identity/identifier_fields'})
        collect(registry_entities, 'semiotic_registry', {'coordinate_system': 'json_pointer', 'section': 'identity/entities'})
        for page in evidence_pages(source):
            collect(page['text'], 'evidence_text', {'coordinate_system': 'unicode_codepoints_in_extracted_page',
                                                  'page': page['page'], 'artifact_sha256': page.get('artifact_sha256')})
        index.update(refs)
        identity_data['uuids'] = sorted({row['uuid'] for row in refs.values()})
        events = {row['id']: row for row in by_event[obs_id]}
        sectors = related['sector_attributions']
        bundled.append({'id': obs_id, 'observation_id': obs_id, 'version': VERSION,
                        'source_metadata': source_metadata, 'identity': identity_data,
                        'regional': {field: fields[field] for field in sorted(REGIONAL & fields.keys())},
                        'structured': {field: fields[field] for field in sorted(STRUCTURED & fields.keys())},
                        'semantic': {field: values for field, values in sorted(fields.items())
                                     if field not in REGIONAL | STRUCTURED | INDUSTRY},
                        'frequencies': frequencies(fields),
                        'profile': related['observation_profiles'][0] if related['observation_profiles'] else None,
                        'coverage': {row['field']: row['status'] for row in related['hybrid_field_coverage']},
                        'isic': {'taxonomy_version': release.get('sector_taxonomy_version'),
                                 'attributions': [row for row in sectors if row['taxonomy_namespace'] == 'isic_rev5'
                                                  and row.get('selection_status') != 'context_only'],
                                 'source_reported_context': [row for row in sectors if row.get('selection_status') == 'context_only'],
                                 'object_and_actors': fields.get('industry_context', []),
                                 'actors': fields.get('industry_actor', []),
                                 'source_context': fields.get('source_industry_context', []),
                                 'entity_context': fields.get('entity_reported_isic_section', []) + fields.get('entity_reported_isic_division', []),
                                 'coverage': related['sector_coverage'],
                                 'source_codes': related['sector_source_codes'], 'shortlists': fields.get('isic_shortlist', [])},
                        'other_sector_attributions': [row for row in sectors if row['taxonomy_namespace'] != 'isic_rev5'],
                        'claims': related['claims'], 'measurements': related['measurements'],
                        'numerical_tables': related['numerical_tables'], 'language_candidates': related['language_candidates'],
                        'language_failures': related['language_failures'], 'events': [events[key] for key in sorted(events)],
                        'edges': edges.get(obs_id, []), 'publication_inputs': related['publication_inputs'],
                        'raw_extraction': related['raw_extraction'], 'evidence_ids': [row['id'] for row in related['evidence_units']]})
    tables['unified_observations'] = bundled
    tables['uuid_index'] = sorted(index.values(), key=lambda row: (row['uuid'], row['observation_id'], row['id']))


def replay(frozen, release):
    if release.get('environment') != 'sandbox' or release['release_id'] != identity(
            'release', {key: value for key, value in release.items() if key != 'release_id'}):
        raise ValueError('semiotic release checksum mismatch')
    if sha(encoded(frozen)) != release.get('frozen_sample_sha256'):
        raise ValueError('frozen metadata input does not match the semiotic release')
    observations = {}
    for batch in frozen['batches']:
        if sha(encoded(batch['observations'])) != batch['observations_sha256']:
            raise ValueError('metadata batch checksum mismatch')
        for observation in batch['observations']:
            if observations.setdefault(observation['observation_id'], observation) != observation:
                raise ValueError('conflicting observation versions')
    result = deepcopy(release)
    attach(result, observations)
    if result != release:
        result['parent_release_id'] = result.pop('release_id')
        result['release_id'] = identity('release', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('frozen', 'graph', 'output'):
        parser.add_argument('--' + option, required=True, type=Path)
    args = parser.parse_args()
    result = replay(json.loads(args.frozen.read_bytes()), json.loads(args.graph.read_bytes()))
    root = write_release(result, args.output / 'releases')
    rows = result['tables']['uuid_index']
    with (args.output / 'uuid-index.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['uuid', 'literal', 'observation_id', 'origin', 'locator_json'])
        for row in rows:
            writer.writerow([row['uuid'], row['literal'], row['observation_id'], row['origin'], encoded(row['locator']).decode()])
    print(json.dumps({'graph': str(root / 'graph.json'), 'release_id': result['release_id'],
                      'observations': len(result['tables']['unified_observations']),
                      'unique_uuids': len({row['uuid'] for row in rows}), 'uuid_occurrences': len(rows)}))


if __name__ == '__main__':
    main()
