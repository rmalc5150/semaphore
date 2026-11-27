import os,sys,json
from pathlib import Path
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
p=Path('config/metadata-engine.json');config=json.loads(p.read_text());source='indonesia_esdm_and_geological_agency_mineral_statistics';config.setdefault('verified_source_failure_handling',{})[source]='queue_by_source_date';temp=p.with_suffix('.streaming.tmp');temp.write_text(json.dumps(config,indent=2)+'\n');temp.replace(p);db=Database(config)
with db.tx()as c:
 c.execute("UPDATE engine_jobs SET state='retry',reason='streaming_lane_required',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='raw_failed' AND reason='streaming_archive_no_dataset_or_document'",('e131223a53b8e81558b565058b17123595e8d37a6a3a1dd4356a5f79fd57354d',));print('CORDIS corrected job requeued:',c.rowcount)
 c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason='Verified 37-page original PDF; discovery-page failures remain queued separately',updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,));print('Indonesian source resumed:',c.rowcount)
import subprocess
print(subprocess.run(['systemctl','start','--no-block','optima-metadata-streaming.service'],capture_output=True,text=True).stdout)
