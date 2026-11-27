"""Describe source evidence, missing fields, and explicitly parsed numerical tables."""
import math
import re

from semiotic_sandbox import identity

NUMERIC = re.compile(r'[+−-]?(?:\d+(?:[.,]\d+)*|\.\d+)(?:[eE][+-]?\d+)?\s*%?')


def is_number(value):
    if type(value) is int:
        return True
    if type(value) is float:
        return math.isfinite(value)
    return isinstance(value, str) and NUMERIC.fullmatch(value.strip()) is not None


def numerical_tables(observation):
    """Consume adapter-provided tables. Units and methods stay as reported."""
    payload = observation['payload']
    tables = payload.get('tables')
    if tables is None:
        return [], 'table_structure_not_supplied'
    if not isinstance(tables, list):
        raise ValueError('payload.tables must be a list of parsed tables')
    output = []
    for table in tables:
        columns = table['columns']
        rows = table['rows']
        if not isinstance(columns, list) or not isinstance(rows, list) or any(
                not isinstance(row, list) or len(row) != len(columns) for row in rows):
            raise ValueError('table rows must align with declared columns')
        counts = [sum(is_number(row[index]) for row in rows) for index in range(len(columns))]
        if not any(counts):
            continue
        if not table.get('locator'):
            raise ValueError('numerical table requires an original evidence locator')
        measurements = [{'index': index, 'label': column['label'], 'numeric_cells': count,
                         'unit': column.get('unit') or None,
                         'unit_evidence': column.get('unit_evidence')}
                        for index, (column, count) in enumerate(zip(columns, counts)) if count]
        method = table.get('reporting_methodology') or None
        missing = [f'unit_not_supplied:{column["index"]}' for column in measurements if not column['unit']]
        if not method:
            missing.append('reporting_methodology_not_supplied')
        row = {'observation_id': observation['observation_id'], 'locator': table['locator'],
               'raw_s3_uri': observation.get('raw_s3_uri'), 'raw_sha256': observation.get('raw_sha256'),
               'title': table.get('title'), 'numeric_columns': measurements,
               'reporting_methodology': method, 'methodology_evidence': table.get('methodology_evidence'),
               'missingness_flags': missing}
        output.append(dict(row, id=identity('numeric_table', row)))
    return output, 'numeric_tables_found' if output else 'no_numeric_tables_in_supplied_structure'


def describe_observations(observations, geography, language, source_registry):
    geography_by_id = {row['observation_id']: row for row in geography}
    model_chunks = {}
    for chunk in language:
        model_chunks.setdefault(chunk['observation_id'], []).append(chunk)
    profiles, tables = [], []
    for observation in observations:
        scope = geography_by_id[observation['observation_id']]
        declaration = source_registry.get(scope['source_key'], {})
        source_type = observation.get('source_type') or declaration.get('source_type')
        evidence_types = {a['artifact_kind'] for a in observation.get('raw_artifacts', []) if a.get('artifact_kind')}
        if observation.get('evidence_type'):
            evidence_types.add(observation['evidence_type'])
        extracted_tables, table_status = numerical_tables(observation)
        tables.extend(extracted_tables)
        declared = observation.get('original_language') or observation.get('language')
        chunks = model_chunks.get(observation['observation_id'], [])
        detected = {chunk['original_language'] for chunk in chunks} - {'und'}
        language_code = declared or ('mul' if len(detected) > 1 else next(iter(detected), None))
        confidence = observation.get('extraction_confidence')
        basis = 'upstream_metadata' if confidence is not None else 'unknown'
        if confidence is None and chunks:
            confidence = min((chunk['extraction_confidence'] for chunk in chunks),
                             key=('low', 'medium', 'high').index)
            basis = 'lowest_chunk_model_self_report_uncalibrated'
        missing = [key for key, value in (
            ('source_type', source_type), ('evidence_types', evidence_types),
            ('geographic_coverage', scope['geographic_coverage']),
            ('population_coverage', scope['population_coverage']), ('original_language', language_code),
            ('extraction_confidence', confidence is not None),
        ) if not value]
        row = {**{k: v for k, v in scope.items() if k != 'id'},
               'source_type': source_type, 'evidence_types': sorted(evidence_types),
               'source_type_basis': ('upstream_metadata' if observation.get('source_type') else
                                     'source_registry' if source_type else 'unknown'),
               'original_language': language_code,
               'language_basis': 'provider_metadata' if declared else 'model_candidate' if detected else 'unknown',
               'extraction_confidence': confidence,
               'confidence_basis': basis,
               'completeness_scope': observation.get('completeness_scope'),
               'raw_completeness_status': observation.get('raw_completeness_status'),
               'coverage_flags': observation.get('quality_flags') or [],
               'missingness_flags': missing, 'numerical_table_status': table_status}
        profiles.append(dict(row, id=identity('observation_profile', row)))
    return profiles, tables
