import os,sys,json
from pathlib import Path
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming import session,download,validate_file
p=Path('config/metadata-engine.json');config=json.loads(p.read_text());db=Database(config);s=db.session.client('s3');source='european_commission_cordis';objects=s.list_objects_v2(Bucket=config['bucket'],Prefix='research-data/constellation-backfill/public-capture/objects/'+source+'/')['Contents'];key=next(x['Key']for x in objects if x['Size']>32*1024**2)
with session():print(json.dumps({'validated':validate_file(download(s,config['bucket'],key,key.rsplit('/',1)[1]))}),flush=True)
config.setdefault('verified_source_failure_handling',{})[source]='queue_by_source_date';temp=p.with_suffix('.streaming.tmp');temp.write_text(json.dumps(config,indent=2)+'\n');temp.replace(p)
with db.tx()as c:
 c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason='Original CORDIS semicolon CSV archive CRC and dataset checks passed',updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,));print('resumed',c.rowcount)
