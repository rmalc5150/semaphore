import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from metadata_engine.runtime_db import Database
cfg=json.loads((root/'config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute("SELECT s3_uri,verified_at,status FROM publication_releases WHERE release_id=UNHEX(SUBSTRING(%s,1,32)) AND release_kind='labelled'",('4eefcf23f2121210b10c924f27bfedae8f6630f1f073a9662344ac907325307c',));print('RECEIPT',json.dumps(c.fetchone(),default=str))
 c.execute("SELECT job_id,source_key,finished_at,output_rows,output_uri FROM engine_jobs FORCE INDEX (publication_ready_order) WHERE state='accepted' ORDER BY finished_at DESC,job_id DESC LIMIT 1");print('LATEST_ACCEPTED',json.dumps(c.fetchone(),default=str))
