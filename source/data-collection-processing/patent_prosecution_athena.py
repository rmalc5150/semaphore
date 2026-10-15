"""Typed prosecution observations; immutable source and document evidence is verified."""
import json
from source_observation_athena import prepare as prepare_observations

COLUMNS = [(n, 'string') for n in ('application_number', 'official_document_id', 'document_type',
    'action_date', 'provider_updated_at', 'first_observed_at', 'document_retrieval_status',
    'documents_json', 'structured_source_fields_json', 'reported_parties_json', 'source_text')]


def fields(record):
    data = record['payload']['data']
    return {**{name: data.get(name) for name in ('application_number', 'official_document_id', 'document_type',
        'action_date', 'provider_updated_at', 'first_observed_at', 'document_retrieval_status', 'source_text')},
        **{name + '_json': json.dumps(data[name], ensure_ascii=False, sort_keys=True) for name in
            ('documents', 'structured_source_fields', 'reported_parties')}}


def prepare(store, settings, config, output_root):
    return prepare_observations(store, settings, config, output_root, extra_columns=COLUMNS, enrich_row=fields)
