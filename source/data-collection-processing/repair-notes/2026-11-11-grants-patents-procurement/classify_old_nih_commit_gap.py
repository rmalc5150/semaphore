import json,hashlib
from pathlib import Path
from metadata_engine.runtime_db import Database
from botocore.exceptions import ClientError
p=Path(__file__).parent;e=json.loads((p/'nih-missing-object.json').read_text());config=json.load(open('config/metadata-engine.json'));db=Database(config);s=db.session.client('s3')
try:s.head_object(Bucket=config['bucket'],Key=e['missing_key']);raise RuntimeError('checkpoint_now_exists_do_not_reclassify')
except ClientError as error:
 if error.response['Error']['Code']not in ('404','NoSuchKey','NotFound'):raise
proof={'classification':'uncommitted_legacy_batch','reason':'collection_checkpoint_head_missing','input_key':e['job']['input_key'],'missing_key':e['missing_key'],'job_id':e['job']['job_id'],'raw_files_retained':True,'raw_complete':False,'owner_action_required':False,'historical_repair_pending':True};body=json.dumps(proof,sort_keys=True).encode();key=config['prefix']+'/repair-evidence/20261111/'+hashlib.sha256(body).hexdigest()+'.json';s.put_object(Bucket=config['bucket'],Key=key,Body=body,ServerSideEncryption='AES256')
with db.tx()as c:
 c.execute("UPDATE engine_jobs SET state='uncommitted',reason='collection_checkpoint_head_missing',report_uri=%s,finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='retry' AND reason LIKE 'NoSuchKey:%%'",('s3://'+config['bucket']+'/'+key,e['job']['job_id']));proof['reclassified_jobs']=c.rowcount
 c.execute("UPDATE pipeline_failures SET status='resolved',report_uri=%s WHERE job_id=%s AND status='open' AND error_reason LIKE 'NoSuchKey:%%'",('s3://'+config['bucket']+'/'+key,e['job']['job_id']))
(p/'nih-commit-gap-classification.json').write_text(json.dumps(proof,indent=2));print(proof)
