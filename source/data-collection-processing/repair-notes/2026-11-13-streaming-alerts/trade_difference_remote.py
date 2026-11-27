import os,sys,json
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming import session,download,JSONStream
config=json.load(open('config/metadata-engine.json'));d=Database(config);s=d.session.client('s3');key='research-data/raw/source=trade_screening/dataset=specialist_inputs/ingestion_date=2026-11-12/run_id=run_35482ebc-41ef-4587-8131-6f5c8e4d207d/page-00000000-part-00001-5f6a2c516df6f9b4f55826606fdd931fe73d49bf17d3b205a097cffe74777dd8.jsonl';body=s.get_object(Bucket=config['bucket'],Key=key)['Body'].read(8*1024**2+1);record=json.loads(body.splitlines()[0]);data=record['payload']['data'];refs=record['payload']['source_evidence'];print(json.dumps({'source_record_id':record['source_record_id'],'payload_keys':list(record['payload']),'data_keys':list(data),'references':refs}),flush=True)
with session():
 ref=refs[0];key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;e=download(s,config['bucket'],key,ref['sha256']);found=False
 with e['path'].open(encoding='utf-8-sig')as f:
  for row in JSONStream(f).results():
   if str(row.get('id'))==str(data.get('id')):
    found=True;print(json.dumps({'original_keys':list(row),'differences':{k:{'collected':str(data.get(k))[:150],'original':str(row.get(k))[:150]}for k in set(data)|set(row)if data.get(k)!=row.get(k)}},default=str),flush=True);break
 print('matched id',found,flush=True)
