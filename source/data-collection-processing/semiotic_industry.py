"""Evidence precedence for observation industry and exact entity lookups."""
from datetime import datetime, timezone
from uuid import UUID

from metadata_engine.graph import links, stable_id
from semiotic_sectors import native_industry_pair
from semiotic_structured import json_field


def entity_references(observation):
    references = {}
    for container, prefix in ((observation, ''), (observation['payload'], '/payload')):
        for field in ('company_ids', 'entity_ids', 'product_ids', 'person_ids'):
            for index, value in enumerate(container.get(field) or []):
                if not isinstance(value, str):
                    continue
                try:
                    identifier = str(UUID(value.split('_', 1)[-1]))
                except ValueError:
                    continue
                references.setdefault(identifier, {'entity_id': value, 'uuid': identifier, 'role': 'linked_entity',
                                                    'path': f'{prefix}/{field}/{index}'})
    for kind, namespace, value, name, role in links(observation):
        identifier = str(stable_id([kind, namespace, value]))
        references.setdefault(identifier, {'entity_id': identifier, 'uuid': identifier, 'name': name, 'role': role,
                                            'namespace': namespace, 'identifier': value})
    return list(references.values())


def timestamp(value):
    if isinstance(value, dict):
        value = value.get('value')
    if not isinstance(value, str) or len(value) <= 10:
        return None
    try:
        instant = datetime.fromisoformat(value)
    except ValueError:
        return None
    return instant if instant.tzinfo else None


def entity_industry_context(observation, assertions):
    """Keep linked, self-reported classifications as actor context only."""
    at = timestamp(observation.get('available_at')) or timestamp(observation.get('source_published_at'))
    matches = []
    if at:
        for ref in entity_references(observation):
            for row in assertions.get(ref['uuid'], ()):
                known, start, end = (timestamp(row.get(key)) for key in ('known_at', 'valid_from', 'valid_to'))
                if (row['basis'] == 'self_reported' and row['review_status'] == 'verified' and row['is_primary']
                        and row['isic_revision'] == 5 and known and known <= at
                        and (start is None or start <= at) and (end is None or at < end)):
                    matches.append((ref, row))
    if matches:
        pairs = {native_industry_pair(row['isic_code']) for _, row in matches}
        sections = {section for section, _ in pairs}
        if len(sections) != 1:
            return []
        sector = next(iter(sections))
        division = next(iter(pairs))[1] if len(pairs) == 1 else None
        evidence = [{'entity_id': ref['entity_id'], 'assertion_id': row['assertion_id'],
                     'evidence_uri': row['evidence_uri'], 'source_observation_id': row['source_observation_id'],
                     'reported_code': row['isic_code']} for ref, row in matches]
        return [{**item, 'field': 'entity_reported_' + item['field']} for item in industry_values(
            sector, division, 'entity_self_reported_context',
            {'coordinate_system': 'entity_industry_assertion', 'assertions': evidence})]
    return []


def source_fallback(observation, declaration, reason):
    """Assign the source routing code after the content classification path is exhausted."""
    profile = observation.get('semiotic_source_profile', {})
    mapping = profile.get('isic_fallback') or declaration.get('isic_fallback')
    method = 'source_profile_fallback' if mapping else 'source_information_service_default'
    sector, division = native_industry_pair(mapping['code'] if mapping else 'K')
    locator = {'coordinate_system': 'source_profile' if mapping else 'source_routing_policy',
               'source_key': observation['source_key'],
               'profile_version': profile.get('version') or declaration.get('industry_profile_version'),
               'reference': (mapping['reference'] if mapping else
                             'https://unstats.un.org/unsd/classifications/Econ/Structure/Detail/EN/2095/63')}
    return [{**item, 'classification_scope': 'source', 'fallback_reason': reason,
             'source_topic': (mapping.get('topic') if mapping else None) or declaration.get('industry_context'),
             'source_code_basis': 'configured_mapping' if mapping else 'provisional_information_service_routing'}
            for item in industry_values(sector, division, method, locator)]


def industry_values(sector, division, method, locator):
    fields = [('isic_section', sector)]
    if division:
        fields.append(('isic_division', division))
    return [{'field': field, 'value': code.removeprefix('isic_'), 'method': method,
             'status': 'candidate', 'locator': locator} for field, code in fields]


def read_assertions(db, observations):
    """Snapshot verified, primary Rev. 5 assertions for exact IDs only."""
    from pymysql import MySQLError

    ids = sorted({UUID(ref['uuid']).bytes for row in observations for ref in entity_references(row)})
    if not ids:
        return {}, 'no_linked_entity_ids'
    results = {}
    try:
        with db.tx() as cur:
            for offset in range(0, len(ids), 200):
                batch = ids[offset:offset + 200]
                marks = ','.join(['%s'] * len(batch))
                cur.execute(f"""SELECT assertion_id, entity_id, isic_code, isic_revision, basis, review_status,
                                    is_primary, evidence_uri, source_observation_id, known_at, valid_from, valid_to
                     FROM entity_industry_assertions WHERE entity_id IN ({marks}) AND review_status='verified'
                       AND basis='self_reported' AND is_primary=1 AND isic_revision=5 ORDER BY assertion_id""", batch)
                for row in cur.fetchall():
                    key = str(UUID(bytes=row.pop('entity_id')))
                    for field in ('known_at', 'valid_from', 'valid_to'):
                        if row[field] is not None:
                            row[field] = row[field].replace(tzinfo=timezone.utc).isoformat()
                    results.setdefault(key, []).append(row)
    except MySQLError as error:
        if error.args[0] not in (1142, 1146):
            raise
        return {}, 'entity_industry_lookup_unavailable'
    return results, 'available'
