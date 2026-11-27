"""Graph-ready evidence units for published metadata observations."""
from datetime import date
from urllib.parse import urlsplit

from semiotic_sandbox import evidence_pages, identity

NASA_POWER = 'nasa_power_weather_and_solar_resource'
VERSION = 'graph-evidence-v1'
LINEAGE_FIELDS = (
    'source_observation_id', 'source_key', 'dataset', 'record_kind', 'source_record_id',
    'source_record_id_basis', 'source_document_id', 'original_url', 'payload_hash', 'contract_version',
    'adapter', 'adapter_version', 'parser_version', 'license_policy_id', 'raw_requirements_version',
    'raw_completeness_status', 'quality_status', 'quality_flags', 'completeness_scope',
    'source_published_at', 'event_at', 'labelled_at', 'availability_basis', 'availability_evidence',
)


def graph_observation(observation, row):
    return {**row, **{field: observation.get(field) for field in LINEAGE_FIELDS}}


def artifact_fields(artifact):
    return {key: artifact.get(key) for key in ('s3_uri', 'sha256', 'artifact_kind', 'source_url', 'origin', 'retrieved_at')}


def unit(observation, kind, locator, *, artifact=None, value=None, provenance_group_id=None):
    artifact = artifact or {}
    artifact_ref = artifact_fields(artifact) if artifact else None
    group = provenance_group_id or observation.get('provenance_group_id')
    row = {
        'observation_id': observation['observation_id'],
        'kind': kind,
        'locator': locator,
        'artifact': artifact_ref,
        'value': value,
        'provenance_group_id': group,
        'provenance_status': 'supplied' if group else 'unresolved',
        'source_published_at': observation.get('source_published_at'),
        'available_at': observation.get('available_at'),
        'availability_basis': observation.get('availability_basis', 'unknown'),
        'availability_evidence': observation.get('availability_evidence'),
        'observed_at': observation.get('ingested_at'),
        'labelled_at': observation.get('labelled_at'),
        'eligible_at': None,
        'version': VERSION,
    }
    key = [row['observation_id'], kind, locator, artifact_ref and artifact_ref['sha256'], VERSION]
    return dict(row, id=identity('evidence', key))


def nasa_measurements(observation, artifact):
    data = observation['payload']['data']
    period = date.fromisoformat(data['date']).isoformat()
    day = period.replace('-', '')
    geography = {key: data[key] for key in ('reference_location', 'latitude', 'longitude')}
    evidence, measurements = [], []
    for parameter, original in sorted(data['provider_values'].items()):
        definition = data['parameters'].get(parameter) or {}
        encoded_parameter = parameter.replace('~', '~0').replace('/', '~1')
        locator = {'coordinate_system': 'json_pointer', 'path': f'/properties/parameter/{encoded_parameter}/{day}'}
        item = unit(observation, 'provider_field', locator, artifact=artifact, value=original,
                    provenance_group_id=identity('artifact_group', artifact['sha256']))
        evidence.append(item)
        series = {'source_key': NASA_POWER, 'parameter': parameter, 'geography': geography,
                  'frequency': 'daily', 'time_standard': data['header'].get('time_standard')}
        missing = parameter in data['missing_parameters']
        row = {
            'observation_id': observation['observation_id'], 'evidence_id': item['id'],
            'series_id': identity('graph_series', series), **series,
            'reference_period': period, 'original_value': original,
            'value': None if missing else data['values'][parameter],
            'unit': definition.get('units'), 'unit_locator': f'/parameters/{encoded_parameter}/units'
            if definition.get('units') else None,
            'population_scope': 'not_applicable',
            'reporting_methodology': None,
            'missingness_flags': (['provider_fill_value'] if missing else [])
            + (['unit_not_supplied'] if not definition.get('units') else [])
            + ['methodology_not_supplied'],
            'eligible_at': None,
        }
        measurements.append(dict(row, id=identity('measurement', [item['id'], row['series_id']])))
    return evidence, measurements


def build_evidence(observations, chunks):
    evidence, measurements = [], []
    artifacts = {}
    for observation in observations.values():
        obs_id = observation['observation_id']
        artifacts[obs_id] = {a['sha256']: a for a in observation.get('raw_artifacts', [])
                             if a.get('sha256') and a.get('s3_uri') and not a.get('representation')}
        for artifact in artifacts[obs_id].values():
            evidence.append(unit(observation, 'artifact', {'coordinate_system': 'whole_artifact'}, artifact=artifact))
        if observation.get('source_key') == NASA_POWER:
            native_refs = {ref.get('sha256') for ref in observation['payload'].get('source_evidence', [])}
            originals = []
            for artifact in artifacts[obs_id].values():
                validation = artifact.get('validation')
                provider_checked = isinstance(validation, dict) and validation.get('provider') == 'NASA POWER'
                source = urlsplit(artifact.get('source_url') or '')
                native_match = (artifact['sha256'] in native_refs and source.scheme == 'https'
                                and source.hostname == 'power.larc.nasa.gov'
                                and artifact.get('origin') == 'first_party_source')
                if provider_checked or native_match:
                    originals.append(artifact)
            if len(originals) != 1:
                raise ValueError('NASA POWER measurement lacks its verified original artifact')
            inputs, values = nasa_measurements(observation, originals[0])
            evidence.extend(inputs)
            measurements.extend(values)
    for chunk in chunks:
        obs_id = chunk['observation_id']
        row = observations[obs_id]
        locator = {key: chunk[key] for key in ('coordinate_system', 'page', 'start', 'end')}
        locator['chunk_id'] = chunk['id']
        page = next((p for p in evidence_pages(row) if p['page'] == chunk['page']), {})
        if 'source_locator' in page:
            locator['source_locator'] = page['source_locator']
        artifact = artifacts[obs_id].get(page.get('artifact_sha256'))
        evidence.append(unit(row, 'extracted_passage', locator, artifact=artifact, value=chunk['text']))
    return evidence, measurements
