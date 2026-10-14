#!/usr/bin/env python3
"""Prepare and publish an explicit, immutable disclosure research pilot."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings
from disclosure_collection import read_inputs
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

COMMON = [("record_id","string"),("observation_id","string"),("source","string"),("origin_source","string"),
    ("dataset","string"),("provider_id","string"),("title","string"),("event_date","date"),("date_basis","string"),
    ("source_url","string"),("company_ids","array<string>"),("candidate_company_ids","array<string>"),
    ("available_at","string"),("ingested_at","string"),("coverage_note","string"),("data_json","string"),
    ("prerequisite_json","string"),("raw_manifest","string"),("raw_batch","string"),("source_evidence_json","string")]
SCHEMAS = {name:COMMON for name in ("disclosures","documents","event_candidates")}
SCHEMAS.update({name:release.SCHEMAS[name] for name in ("companies","company_sectors")})


def prepare(store, settings, config, output_root):
    release.validate_config(config)
    first = json.loads(release.get_bytes(store,config['source_manifests'][0]))
    universe = json.loads(release.get_bytes(store,f"manifests/configurations/universe/{first['task']['universe_hash']}.json"))
    taxonomy = json.loads(release.get_bytes(store,f"manifests/configurations/taxonomy/{first['task']['taxonomy_hash']}.json"))
    entries, inputs, _ = read_inputs(store,config['source_manifests'],universe,taxonomy)
    tables={name:[] for name in SCHEMAS}
    dimensions=release.curate({},universe)
    for name in ('companies','company_sectors'):tables[name]=dimensions[name]
    for entry in entries:
        record=entry['record'];payload=record['payload']
        table={'hkex_news':'disclosures','disclosure_documents':'documents','disclosure_candidates':'event_candidates'}.get(record['source'])
        release.require(table is not None,'Use the SEC pilot for SEC index metadata')
        tables[table].append({'record_id':record['record_id'],'observation_id':record['observation_id'],
            'source':record['source'],'origin_source':payload.get('origin_source',record['source']),'dataset':record['dataset'],
            'provider_id':record['source_record_id'],'title':payload.get('title'),
            'event_date':date.fromisoformat(record['event_at']['value']), 'date_basis':payload['date_basis'],
            'source_url':record['source_url'],'company_ids':record['company_ids'],
            'candidate_company_ids':payload['candidate_company_ids'],'available_at':None,'ingested_at':record['ingested_at'],
            'coverage_note':payload['coverage_note'],'data_json':release.json_text(payload['data']),
            'prerequisite_json':release.json_text(payload.get('prerequisite')),'raw_manifest':entry['manifest'],
            'raw_batch':entry['batch'],'source_evidence_json':release.json_text(payload['source_evidence'])})
    release_id=digest({'version':'disclosure-curation-1.0','arrow':pa.__version__,'config':config,'inputs':inputs,
                       'schemas':SCHEMAS,'bucket':settings.s3_bucket,'prefix':settings.s3_prefix})
    root=Path(output_root)/release_id;root.mkdir(parents=True,exist_ok=True)
    prefix=config['curated_prefix']+'/'+release_id
    files,ddl={},[]
    for name,rows in tables.items():
        table=pa.Table.from_pylist(rows,schema=pa.schema([(field,release.ARROW_TYPES[kind]) for field,kind in SCHEMAS[name]]))
        relative=f'tables/{name}/part-00000.parquet';path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(table,path,compression='snappy',version='1.0')
        release.require(pq.ParquetFile(path).read().equals(table),'Parquet round-trip mismatch')
        body=path.read_bytes();location=f's3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/'
        files[name]={'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows':len(rows),
                     'location':location,'columns':SCHEMAS[name]}
        columns=', '.join(f'{field} {kind}' for field,kind in SCHEMAS[name])
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({columns}) STORED AS PARQUET LOCATION '{location}';")
    db=config['database']
    queries={'table_counts':' UNION ALL '.join(f"SELECT '{name}' AS table_name, count(*) AS records FROM {db}.{name}" for name in SCHEMAS)+' ORDER BY table_name',
        'candidate_counts':f'SELECT dataset, count(*) FROM {db}.event_candidates GROUP BY dataset ORDER BY dataset',
        'quality':f'SELECT count(*), count(DISTINCT record_id), count(available_at) FROM {db}.event_candidates',
        'preview':f'SELECT origin_source, dataset, event_date, title FROM {db}.event_candidates ORDER BY dataset, provider_id LIMIT 20'}
    counts=Counter(row['dataset'] for row in tables['event_candidates'])
    expected={'table_counts':[[name,str(len(rows))] for name,rows in sorted(tables.items())],
        'candidate_counts':[[name,str(count)] for name,count in sorted(counts.items())],
        'quality':[[str(len(tables['event_candidates'])),str(len(tables['event_candidates'])),'0']]}
    report={'curator_version':'disclosure-curation-1.0','catalog_owner':'disclosures','workgroup_description':'Optima disclosure pilot',
        'release_id':release_id,'release_prefix':prefix,'bucket':settings.s3_bucket,'s3_prefix':settings.s3_prefix,'config':config,
        'inputs':inputs,'universe_hash':digest(universe),'files':files,'expected_results':expected,'queries':queries,
        'status':'locally_validated','schema_version':'1.0'}
    (root/'release.json').write_bytes(canonical_json(report)+b'\n')
    (root/'tables.sql').write_text('\n\n'.join(ddl)+'\n')
    (root/'queries.sql').write_text('\n\n'.join(f'-- {name}\n{sql};' for name,sql in queries.items())+'\n')
    print(json.dumps({'stage':'prepared','directory':str(root),'expected_results':expected}),flush=True)
    return root


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','publish','deploy'))
    parser.add_argument('--config',type=Path,default=ROOT/'config/disclosure-athena-pilot.json')
    parser.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    parser.add_argument('--output-root',type=Path,default=ROOT/'disclosure-athena-build')
    parser.add_argument('--release-dir',type=Path)
    args=parser.parse_args();settings=StorageSettings.load(args.storage_config);store=settings.store()
    if args.stage=='prepare':prepare(store,settings,load_json(args.config),args.output_root)
    else:
        release.require(args.release_dir is not None,'--release-dir required')
        (release.publish if args.stage=='publish' else release.deploy)(store,settings,args.release_dir)


if __name__=='__main__':main()
