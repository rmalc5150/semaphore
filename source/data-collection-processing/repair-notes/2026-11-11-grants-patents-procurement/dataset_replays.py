import json,base64,hashlib,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);sources=['nist_robotics_methods','ted_notices','uspto_odp'];template=Path('repair-notes/2026-11-09-hkex-repair/replay_verified.py').read_text();files={};c=json.load(open('config/constellation-infrastructure.json'));s=boto3.client('s3',region_name=c['region']);selected={}
for source in sources:
 with db.tx()as x:
  if source=='uspto_odp':
   selected_jobs=[]
   for dataset in ('patent_records','patent_assignment_records','patent_petition_decisions'):
    x.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND contract_version='2.0.3' AND state IN ('queued','retry') AND input_key LIKE %s ORDER BY created_at DESC LIMIT 1",(source,'%dataset='+dataset+'/%'));selected_jobs.extend(x.fetchall())
  else:
   x.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND contract_version='2.0.3' AND state IN ('queued','retry') AND input_key LIKE '%%ingestion_date=2026-11-11/%%' ORDER BY created_at DESC LIMIT 3",(source,));selected_jobs=x.fetchall()
  ids=tuple(r['job_id']for r in selected_jobs)
 if not ids:continue
 selected[source]=list(ids);runner=template;start=runner.index('IDS=');end=runner.index('\nconfig=',start);runner=runner[:start]+'IDS='+repr(ids)+runner[end:];runner=runner.replace('hkex_news',source).replace('range(4)','range(len(IDS))').replace(' AND available_after<=UTC_TIMESTAMP(6)','');raw=runner.encode();sha=hashlib.sha256(raw).hexdigest();key=c['prefix']+'/deployments/grants-patents-validation-20261111/'+sha+'/'+source+'_replay.py';s.put_object(Bucket=c['bucket'],Key=key,Body=raw,ServerSideEncryption='AES256');files[source]={'key':key,'sha256':sha}
(p/'dataset-replay-jobs.json').write_text(json.dumps(selected,indent=2));script=(p/'run_replays_remote.py').read_text();a=script.index('for source,ref in ');b=script.index('.items():',a);script=script[:a]+'files='+repr(files)+'\nfor source,ref in files'+script[b:];# replace remaining literal dict references via regenerate template from prior boundaries
start=script.index('with concurrent.futures.ThreadPoolExecutor');script=script[:start]+"with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(run,files))\n";script=script.replace('review-replay-v2','dataset-replay-v2');(p/'run_datasets_remote.py').write_text(script);print(selected)
