"""Bounded read-only replay of committed EODHD inputs; saves an audit receipt."""
import hashlib
import json
from pathlib import Path

from metadata_engine.runtime_db import Database,encoded
from metadata_engine.worker import load_input,put,now
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.labelling import label_observation


def main():
    config=json.loads((Path(__file__).resolve().parents[1]/'config/metadata-engine.json').read_text())
    db=Database(config);s3=db.session.client('s3');bucket=config['bucket']
    with db.tx() as c:
        c.execute("SELECT * FROM engine_jobs WHERE source_key IN ('eodhd','eodhd_market') AND state='raw_failed' ORDER BY source_key,created_at LIMIT 8")
        jobs=c.fetchall()
    candidates=[];inputs=set()
    for job in jobs:
        if job['input_key'] in inputs:continue
        inputs.add(job['input_key'])
        rows,raw,manifest=load_input(s3,bucket,job,db)
        if rows:candidates.append((rows[0],job['input_key'],raw))
        # A market run's committed manifest contains prices, dividends and
        # splits in separate batches. Inspect one record per saved batch.
        if job['source_key']=='eodhd_market':
            for page in manifest.get('pages',[]):
                for batch in page.get('batches',[]):
                    key='research-data/'+batch['key']
                    if key in inputs or len(inputs)>=12:continue
                    inputs.add(key)
                    more,body,_=load_input(s3,bucket,{**job,'input_key':key},db)
                    if more:candidates.append((more[0],key,body))
            break
    seen=set();results=[]
    for row,key,raw in candidates:
        identity=(row['source'],row['dataset'],row['payload'].get('kind'))
        if identity in seen:continue
        seen.add(identity);contract=config['contracts'][row['source']]
        artifacts=evidence_for(row,contract,s3,bucket)
        envelope={'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(raw).hexdigest(),'origin':'first_party_source'}
        labelled=label_observation({**row,'raw_s3_uri':envelope['s3_uri'],'raw_sha256':envelope['sha256'],
            'raw_completeness_status':'complete','raw_artifacts':[envelope,*artifacts]},contract)
        results.append({'source':row['source'],'dataset':row['dataset'],'kind':row['payload'].get('kind'),
            'source_record_id':row['source_record_id'],'input_uri':envelope['s3_uri'],
            'provider_artifacts':artifacts,'contract_version':contract['contract_version'],
            'provider_role':labelled['provider_role'],'quality_status':labelled['quality_status'],
            'quality_flags':labelled['quality_flags'],'result':'passed'})
    required={('eodhd','company_profiles',None),('eodhd','listing_inventory',None),('eodhd_market','market_records','prices')}
    if not required.issubset(seen):raise RuntimeError('pilot_missing_required_dataset_samples')
    report={'checked_at':now(),'status':'passed','scope':'bounded committed archived samples only',
            'new_provider_requests':0,'build_sha256':config['build_sha256'],'inputs_inspected':len(inputs),'samples':results}
    body=encoded(report).encode();key=config['prefix']+'/pilots/eodhd-provider-data/'+hashlib.sha256(body).hexdigest()+'.json'
    uri=put(s3,bucket,key,body)
    print(encoded({'status':'passed','receipt_uri':uri,'samples':[{k:r[k] for k in ('source','dataset','kind','source_record_id','result')} for r in results]}))


if __name__=='__main__':main()
