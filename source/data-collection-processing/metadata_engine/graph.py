"""Evidence-linked deterministic identities and source-defined roles.

No fuzzy matches or parent-stock attribution. Source record events remain
distinct unless an explicit durable provider identity establishes sameness.
"""
import json
import uuid
from datetime import datetime

from metadata_engine.runtime_db import fingerprint,encoded


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


def register(db,records):
    with db.tx() as c:
        for r in records:
            evidence=r['raw_s3_uri'];obs=r['observation_id']
            event_id=stable_id(['source_record_event',r['source_key'],r['dataset'],r['source_record_id']])
            event_time=(r.get('event_at') or {}).get('value') if isinstance(r.get('event_at'),dict) else None
            # Preserve date precision in assertions; the graph date is optional.
            c.execute('INSERT IGNORE INTO canonical_events(event_id,event_type,created_at) VALUES(%s,%s,UTC_TIMESTAMP(6))',
                      (event_id.bytes,'source_record_observed'))
            version=stable_id(['version',obs])
            c.execute("INSERT IGNORE INTO event_versions(event_version_id,event_id,source_observation_id,revision_kind,asserted_values,evidence_uri) VALUES(%s,%s,%s,'original',%s,%s)",
                      (version.bytes,event_id.bytes,obs,encoded({'source_key':r['source_key'],'record_id':r['record_id'],'event_at':r.get('event_at'),'available_at':r.get('available_at'),'payload_hash':r['payload_hash']}),evidence))
            for kind,namespace,value,name,role in links(r):
                entity=stable_id([kind,namespace,value])
                c.execute("INSERT IGNORE INTO entities(entity_id,entity_type,lifecycle_status,created_at) VALUES(%s,%s,'provisional',UTC_TIMESTAMP(6))",(entity.bytes,kind))
                c.execute("INSERT IGNORE INTO entity_identifiers(identifier_id,entity_id,namespace,identifier_value,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,%s,%s,'candidate')",(stable_id(['identifier',namespace,value,obs]).bytes,entity.bytes,namespace,value,obs,evidence))
                if name:
                    c.execute("INSERT IGNORE INTO entity_names(name_id,entity_id,name_original,name_normalized,name_kind,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,'source_label',%s,%s,'candidate')",(stable_id(['name',entity.hex,name,obs]).bytes,entity.bytes,name,' '.join(name.casefold().split()),obs,evidence))
                c.execute("INSERT IGNORE INTO event_participants(participant_id,event_id,entity_id,role,source_observation_id,evidence_uri,review_status) VALUES(%s,%s,%s,%s,%s,%s,'candidate')",(stable_id(['role',event_id.hex,entity.hex,role,obs]).bytes,event_id.bytes,entity.bytes,role,obs,evidence))
                assertion={'namespace':namespace,'identifier':value,'role':role,'name':name,'event_id':str(event_id)}
                c.execute('INSERT IGNORE INTO engine_assertions(assertion_id,entity_id,kind,subject_key,source_observation_id,asserted_value,valid_from,available_at,recorded_at,evidence_uri) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6),%s)',
                    (fingerprint([obs,assertion]),entity.bytes,'source_role',str(entity),obs,encoded(assertion),event_time,encoded(r.get('available_at')),evidence))
            for artifact in r['raw_artifacts']:
                if artifact.get('representation'):continue
                sha=artifact['sha256'];uri=artifact['s3_uri'];size=artifact.get('bytes',0)
                c.execute('INSERT IGNORE INTO engine_artifacts(sha256,s3_uri,bytes,provenance,registered_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP(6))',(sha,uri,size,encoded(artifact)))
                c.execute('INSERT IGNORE INTO raw_objects(raw_object_id,s3_uri,sha256,media_type,artifact_kind,origin,bytes,source_url,retrieved_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6))',
                          (stable_id(['raw',sha,uri]).bytes,uri,sha,None,artifact['artifact_kind'],artifact['origin'],size,artifact.get('source_url')))
                c.execute('INSERT IGNORE INTO engine_document_links VALUES(%s,%s,%s,%s,%s)',(sha,obs,r['source_key'],r['source_record_id'],uri))
            if r['adapter']=='time_series':
                data=r['payload'].get('data',r['payload']);dimensions={k:data.get(k) for k in ('series_id','series','metric','unit','units','geography','country','currency','frequency') if isinstance(data,dict) and k in data}
                if dimensions:
                    definition={'source':r['source_key'],'dataset':r['dataset'],'dimensions':dimensions};series=fingerprint(definition)
                    period=str(data.get('period') or data.get('date') or event_time or 'unknown')
                    c.execute('INSERT IGNORE INTO engine_series VALUES(%s,%s)',(series,encoded(definition)))
                    c.execute('INSERT IGNORE INTO engine_series_vintages VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(fingerprint([series,period,obs]),series,period,r['payload_hash'],obs,evidence,encoded(data),encoded(r.get('available_at')),r['ingested_at']))
