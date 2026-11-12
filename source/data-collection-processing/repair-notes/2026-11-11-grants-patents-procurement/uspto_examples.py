import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent/'uspto_odp';cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3')
for dataset in ('patent_records','patent_assignment_records','patent_petition_decisions'):
 with db.tx()as c:c.execute("SELECT * FROM engine_jobs WHERE source_key='uspto_odp' AND input_key LIKE %s AND input_format LIKE 'legacy_batch%%' LIMIT 1",('%/dataset='+dataset+'/%',));j=c.fetchone()
 if not j:continue
 raw=s.get_object(Bucket=cfg['bucket'],Key=j['input_key'])['Body'].read();r=json.loads(raw.splitlines()[0]);(p/('sample-'+dataset+'.json')).write_text(json.dumps(r,indent=2));d=r['payload'].get('data',{});print(dataset,'id',r['source_record_id'],'PAYLOAD',list(r['payload']),'DATA',list(d)[:45]);print('REFS',[(ref.get('source_url')or ref.get('url'),ref.get('key'))for ref in r['payload'].get('source_evidence',[])][:4])
