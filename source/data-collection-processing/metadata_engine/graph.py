"""Evidence-linked deterministic identities and source-defined roles.

No fuzzy matches or parent-stock attribution. Source record events remain
distinct unless an explicit durable provider identity establishes sameness.
"""
import time
import uuid

from metadata_engine.labelling import canonical_json, digest as fingerprint


def encoded(value):return canonical_json(value).decode('utf-8')


def stable_id(parts):return uuid.uuid5(uuid.NAMESPACE_URL,'metadata-engine:'+encoded(parts))


def links(record):
    payload=record['payload'];data=payload.get('data',payload)
    output=[]
    if record['source_key']=='sec_edgar':
        for row in payload.get('issuer_rows',[]):
            output.append(('organization','CIK',str(row['cik']).zfill(10),row.get('company_name'),'filer'))
    if isinstance(data,dict):
        for field,kind,namespace,role in [('doi','publication','DOI','publication'),('pmid','publication','PMID','publication'),
            ('nctId','trial','ClinicalTrials.gov','trial'),('imo','vessel','IMO','vessel'),('lei','organization','LEI','reported_organization'),
            ('ror','organization','ROR','reported_organization')]:
            value=data.get(field)
            if isinstance(value,(str,int)) and str(value).strip():output.append((kind,namespace,str(value).strip(),None,role))
    return output


def register(db,records,*,write_stats=None):
    if not records:
        return 0
    # The insertion order keeps referenced rows ahead of their dependents.
    inserts = {
        'canonical_events': 'INSERT IGNORE INTO canonical_events(event_id,event_type,created_at) VALUES(%s,%s,%s)',
        'event_versions': 'INSERT IGNORE INTO event_versions(event_version_id,event_id,source_observation_id,revision_kind,asserted_values,evidence_uri) VALUES(%s,%s,%s,%s,%s,%s)',
        'entities': 'INSERT IGNORE INTO entities(entity_id,entity_type,lifecycle_status,created_at) VALUES(%s,%s,%s,%s)',
        'entity_identifiers': 'INSERT IGNORE INTO entity_identifiers(identifier_id,entity_id,namespace,identifier_value,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,%s,%s,%s)',
        'entity_names': 'INSERT IGNORE INTO entity_names(name_id,entity_id,name_original,name_normalized,name_kind,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
        'event_participants': 'INSERT IGNORE INTO event_participants(participant_id,event_id,entity_id,role,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,%s,%s,%s)',
        'engine_assertions': 'INSERT IGNORE INTO engine_assertions(assertion_id,entity_id,kind,subject_key,source_observation_id,asserted_value,valid_from,available_at,recorded_at,evidence_uri) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        'engine_artifacts': 'INSERT IGNORE INTO engine_artifacts(sha256,s3_uri,bytes,provenance,registered_at) VALUES(%s,%s,%s,%s,%s)',
        'raw_objects': 'INSERT IGNORE INTO raw_objects(raw_object_id,s3_uri,sha256,media_type,artifact_kind,origin,bytes,source_url,retrieved_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        'engine_document_links': 'INSERT IGNORE INTO engine_document_links VALUES(%s,%s,%s,%s,%s)',
        'engine_series': 'INSERT IGNORE INTO engine_series VALUES(%s,%s)',
        'engine_series_vintages': 'INSERT IGNORE INTO engine_series_vintages VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
    }
    pending = {table: [] for table in inserts}
    with db.tx() as c:
        c.execute('SELECT UTC_TIMESTAMP(6) AS recorded_at')
        recorded_at = c.fetchone()['recorded_at']
        for record in records:
            evidence = record['raw_s3_uri']
            observation = record['observation_id']
            event_id = stable_id(['source_record_event', record['source_key'], record['dataset'], record['source_record_id']])
            event_at = record.get('event_at')
            event_time = event_at.get('value') if isinstance(event_at, dict) else None
            available_at = encoded(record.get('available_at'))
            # Preserve date precision in assertions; the graph date is optional.
            pending['canonical_events'].append((event_id.bytes, 'source_record_observed', recorded_at))
            version = stable_id(['version', observation])
            assertions = {
                'source_key': record['source_key'], 'record_id': record['record_id'],
                'event_at': event_at, 'available_at': record.get('available_at'),
                'payload_hash': record['payload_hash'],
            }
            pending['event_versions'].append((version.bytes, event_id.bytes, observation, 'original', encoded(assertions), evidence))
            for kind, namespace, value, name, role in links(record):
                entity = stable_id([kind, namespace, value])
                pending['entities'].append((entity.bytes, kind, 'provisional', recorded_at))
                identifier = stable_id(['identifier', namespace, value, observation])
                pending['entity_identifiers'].append(
                    (identifier.bytes, entity.bytes, namespace, value, observation, evidence, 'candidate'))
                if name:
                    name_id = stable_id(['name', entity.hex, name, observation])
                    pending['entity_names'].append((name_id.bytes, entity.bytes, name, ' '.join(name.casefold().split()),
                                                     'source_label', observation, evidence, 'candidate'))
                participant = stable_id(['role', event_id.hex, entity.hex, role, observation])
                pending['event_participants'].append(
                    (participant.bytes, event_id.bytes, entity.bytes, role, observation, evidence, 'candidate'))
                assertion = {'namespace': namespace, 'identifier': value, 'role': role, 'name': name, 'event_id': str(event_id)}
                pending['engine_assertions'].append(
                    (fingerprint([observation, assertion]), entity.bytes, 'source_role', str(entity), observation,
                     encoded(assertion), event_time, available_at, recorded_at, evidence))
            for artifact in record['raw_artifacts']:
                if artifact.get('representation'):
                    continue
                sha, uri, size = artifact['sha256'], artifact['s3_uri'], artifact.get('bytes',0)
                pending['engine_artifacts'].append((sha, uri, size, encoded(artifact), recorded_at))
                pending['raw_objects'].append((stable_id(['raw', sha, uri]).bytes, uri, sha, None, artifact['artifact_kind'],
                                               artifact['origin'], size, artifact.get('source_url'), recorded_at))
                pending['engine_document_links'].append((sha, observation, record['source_key'], record['source_record_id'], uri))
            if record['adapter'] == 'time_series':
                data = record['payload'].get('data', record['payload'])
                dimensions = {key: data[key] for key in ('series_id','series','metric','unit','units','geography','country','currency','frequency')
                              if isinstance(data, dict) and key in data}
                if dimensions:
                    definition = {'source': record['source_key'], 'dataset': record['dataset'], 'dimensions': dimensions}
                    series = fingerprint(definition)
                    period = str(data.get('period') or data.get('date') or event_time or 'unknown')
                    pending['engine_series'].append((series, encoded(definition)))
                    pending['engine_series_vintages'].append(
                        (fingerprint([series, period, observation]), series, period, record['payload_hash'], observation,
                         evidence, encoded(data), available_at, record['ingested_at']))
        batches = 0
        for table, statement in inserts.items():
            rows = pending[table]
            if rows:
                if table in ('engine_artifacts', 'raw_objects'):
                    # Several observations can share the same original object.
                    rows = list(dict.fromkeys(rows))
                # The raw-object URL prefix is also unique. Keep its original
                # input order so duplicate handling preserves the first URI.
                if table != 'raw_objects':
                    rows = sorted(rows, key=lambda row: row[0])
                # PyMySQL packs these parameter-only INSERTs into bounded statements.
                began = time.monotonic()
                c.executemany(statement, rows)
                if write_stats is not None:
                    write_stats[table] = {'rows': len(rows), 'seconds': round(time.monotonic() - began, 4)}
                batches += 1
    return batches
