"""Versioned sector attribution for graph data points."""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from semiotic_sandbox import identity

CONFIG = Path(__file__).parent / 'config'
RESEARCH = json.loads((CONFIG / 'sectors.v1.json').read_text())
ISIC_SOURCE = {
    'standard': 'ISIC', 'edition': 'Rev. 5',
    'source_url': 'https://unstats.un.org/unsd/classifications/Econ/Download/In%20Text/ISIC_Rev_5_english_structure.csv',
    'source_sha256': 'fc408f57bd3a4f33c35a4f384ec0010283dd72774892c8d48ae1330a8caeb57f',
}


def load_isic(path):
    nodes = {}
    current_section = None
    levels = {2: 'division', 3: 'group', 4: 'class'}
    with path.open(encoding='utf-8', newline='') as stream:
        records = csv.DictReader(stream)
        for record in records:
            code = record['ISIC Rev 5 Code'].strip()
            title = record['ISIC Rev 5 Title'].strip()
            if not title or code in nodes or not re.fullmatch(r'[A-V]|[0-9]{2,4}', code):
                raise ValueError(f'invalid ISIC entry: {code!r}')
            if len(code) == 1:
                current_section = code
                level, parent = 'section', None
            else:
                level = levels[len(code)]
                parent = current_section if len(code) == 2 else code[:-1]
                if parent not in nodes or nodes[parent]['section'] != current_section:
                    raise ValueError(f'invalid ISIC parent for {code!r}')
            nodes[code] = {'name': title, 'level': level, 'parent': parent, 'section': current_section}
    return nodes


ISIC = load_isic(CONFIG / 'semiotic-isic-rev5.csv')
TAXONOMY = {
    'taxonomy_version': '3.0.0',
    'research_taxonomy_version': RESEARCH['taxonomy_version'],
    'industry_standard': ISIC_SOURCE,
    'industry_activity_nodes': ISIC,
    'sectors': [
        {**entry, 'taxonomy_namespace': 'research'} for entry in RESEARCH['sectors']
    ] + [
        {'sector_id': f'isic_{code}', 'name': entry['name'], 'taxonomy_namespace': 'isic_rev5',
         'subsectors': [{'subsector_id': f'isic_{sub}', 'name': node['name']}
                        for sub, node in ISIC.items() if node['parent'] == code]}
        for code, entry in ISIC.items() if entry['level'] == 'section'
    ],
}
SECTORS = {entry['sector_id']: {sub['subsector_id'] for sub in entry['subsectors']}
           for entry in TAXONOMY['sectors']}
NAMESPACES = {entry['sector_id']: entry['taxonomy_namespace'] for entry in TAXONOMY['sectors']}
VERSION = TAXONOMY['taxonomy_version']


def validate_pair(sector, subsector):
    if sector not in SECTORS or (subsector is not None and subsector not in SECTORS[sector]):
        raise ValueError(f'invalid sector/subsector pair: {sector!r}, {subsector!r}')


def native_industry_pair(code):
    """Map a native ISIC Rev. 5 code, preserving leading zeros in the caller."""
    if not isinstance(code, str) or code not in ISIC:
        raise ValueError(f'unsupported ISIC Rev. 5 activity code: {code!r}')
    node = ISIC[code]
    division = f'isic_{code[:2]}' if node['level'] != 'section' else None
    return f'isic_{node["section"]}', division


def row_id(kind, row):
    return {**row, 'id': identity(kind, row)}


def build_sector_tables(observations, tables, reviewed=()):
    attributions, by_point, source_codes = {}, {}, []

    def add(point_type, point_id, observation_id, item, basis, status, **evidence):
        sector, subsector = item['sector_id'], item.get('subsector_id')
        validate_pair(sector, subsector)
        row = row_id('sector_attribution', {
            'point_type': point_type, 'point_id': point_id, 'observation_id': observation_id,
            'taxonomy_version': VERSION, 'sector_id': sector, 'subsector_id': subsector,
            'taxonomy_namespace': NAMESPACES[sector],
            'basis': basis, 'status': status, 'eligible_at': None, **evidence,
        })
        attributions[row['id']] = row
        by_point.setdefault((point_type, point_id), set()).add(row['id'])

    for obs_id, observation in observations.items():
        payload = observation['payload']
        for index, item in enumerate(payload.get('sector_classifications', [])):
            locator = f'/payload/sector_classifications/{index}'
            legacy_sector = (item.get('sector_id') or '').startswith('naics_')
            if 'naics_code' in item or legacy_sector:
                legacy_code = item.get('naics_code')
                if legacy_code is None and legacy_sector:
                    legacy_code = (item.get('subsector_id') or item['sector_id']).removeprefix('naics_')
                if legacy_code is None or not str(legacy_code).strip():
                    raise ValueError('source NAICS code must not be empty')
                source_codes.append(row_id('sector_source_code', {
                    'observation_id': obs_id, 'standard': 'NAICS',
                    'edition': item.get('naics_edition') or ('2022' if legacy_sector else None),
                    'code': str(legacy_code),
                    'evidence_locator': locator, 'evidence_reference': item.get('evidence_reference'),
                    'mapping_status': 'unmapped_to_isic',
                }))
                if 'isic_code' not in item:
                    continue
            if 'isic_code' in item:
                if (('sector_id' in item or 'subsector_id' in item) and not legacy_sector
                        or item.get('isic_revision') not in (5, '5')):
                    raise ValueError('native ISIC classification requires revision 5 and no separate active label pair')
                sector, subsector = native_industry_pair(item['isic_code'])
                item = {**item, 'sector_id': sector, 'subsector_id': subsector}
            add('observation', obs_id, obs_id, item, 'source_declared', 'reported',
                evidence_locator=locator, evidence_reference=item.get('evidence_reference'),
                native_isic_code=item.get('isic_code'))
        for index, item in enumerate(payload.get('technology_classifications', [])):
            # Existing patent labels are collector classifications. Their
            # category names are not canonical subsector identifiers.
            if item.get('sector_id') in SECTORS:
                add('observation', obs_id, obs_id, {'sector_id': item['sector_id']},
                    'upstream_technology_classification', 'candidate',
                    evidence_locator=f'/payload/technology_classifications/{index}')

    claims_by_result = defaultdict(list)
    for claim in tables['claims']:
        if candidate_id := claim.get('language_candidate_id'):
            claims_by_result[candidate_id].append(claim)
    for result in tables['language_candidates']:
        for item in result.get('sector_classifications', []):
            for point_type, point_id, basis in (
                ('chunk', result['chunk_id'], 'model_passage'),
                ('observation', result['observation_id'], 'model_passage_rollup'),
            ):
                add(point_type, point_id, result['observation_id'], item, basis, 'candidate',
                    evidence=item['evidence'], language_candidate_id=result['id'],
                    model=result['model'], extractor_version=result['prompt_version'])
            for claim in claims_by_result[result['id']]:
                if claim['evidence'] == item['evidence']:
                    add('claim', claim['id'], claim['observation_id'], item, 'model_claim_passage', 'candidate',
                        evidence=item['evidence'], language_candidate_id=result['id'],
                        model=result['model'], extractor_version=result['prompt_version'])

    points = {}
    for table, point_type in (
        ('observations', 'observation'), ('chunks', 'chunk'), ('claims', 'claim'),
        ('measurements', 'measurement'), ('numerical_tables', 'numerical_table'),
    ):
        for point in tables[table]:
            points[point_type, point['id']] = (point['id'] if point_type == 'observation'
                                              else point['observation_id'])

    evidence_observations = {row['id']: row['observation_id'] for row in tables['evidence_units']}
    for item in reviewed:
        point_type, point_id = item['point_type'], item['point_id']
        obs_id = points.get((point_type, point_id))
        if (obs_id is None or evidence_observations.get(item['evidence_id']) != obs_id
                or not item['reviewer'].strip() or not item['reason'].strip()):
            raise ValueError('reviewed sector attribution requires a local point, its evidence, and reviewer rationale')
        add(point_type, point_id, obs_id, item, 'reviewed_evidence', 'reviewed',
            evidence_id=item['evidence_id'], reviewer=item['reviewer'], reason=item['reason'])

    coverage = []
    for (point_type, point_id), obs_id in points.items():
        ids = sorted(by_point.get((point_type, point_id), ()))
        coverage.append(row_id('sector_coverage', {
            'point_type': point_type, 'point_id': point_id, 'observation_id': obs_id,
            'taxonomy_version': VERSION, 'attribution_ids': ids,
            'status': 'attributions_present' if ids else 'unclassified',
        }))
    return list(attributions.values()), coverage, source_codes
