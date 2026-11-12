import json
from pathlib import Path
from collection_storage import StorageSettings
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);store=StorageSettings.load('config/collection-storage.s3.json').store();fresh=json.load(open(p/'fresh-row-identities.json'));capture=json.load(open(p/'fresh-capture.json'));release=json.load(open(p/'fresh-publication.json'));assert release['status']=='complete'and release['results'][0]['status']=='verified';fresh_ids=tuple(json.load(open(p/'fresh-replay.json'))['repair_job_ids'])
with db.tx()as c:
 c.execute('SELECT state,output_rows FROM engine_jobs WHERE job_id IN %s',(fresh_ids,));assert all(r['state']=='accepted'and r['output_rows']==fresh['rows']for r in c.fetchall())
bad={r['job_id']for r in json.load(open(p/'failed-batch-validation.json'))if r['row_errors']};keys=[]
for j in json.load(open(p/'failed-jobs-before.json')):
 if j['job_id']not in bad:continue
 rows=[json.loads(l)for l in store.get(j['input_key'].removeprefix('research-data/')).body.splitlines()]
 for r in rows:
  assert r['source_record_id']in fresh['identities']
  refs=[e for e in r['payload']['source_evidence']if e['source_url']==r['source_url']];assert refs and all(e['sha256']==fresh['provider_pdf_sha256']for e in refs)
 keys.append(j['input_key'])
assert keys
with db.tx()as c:
 c.execute("SELECT job_id,state,reason FROM engine_jobs WHERE source_key='japan_pmda' AND input_key IN %s",(tuple(keys),));old=c.fetchall();ids=tuple(r['job_id']for r in old)
 c.execute('SELECT * FROM source_date_failures WHERE source_key=%s AND latest_job_id IN %s',('japan_pmda',ids));failures=c.fetchall();(p/'legacy-replacement-before.json').write_text(json.dumps({'jobs':old,'date_failures':failures},indent=2,default=str))
 c.execute("UPDATE engine_jobs SET state='superseded',reason=%s WHERE source_key='japan_pmda' AND input_key IN %s AND state IN ('queued','retry','raw_failed','uncommitted')",('legacy_flattened_extraction_replaced_by_verified_pdf_table:'+capture['manifest'],tuple(keys)));changed=c.rowcount
 c.execute("UPDATE source_date_failures SET status='resolved',reason_code='verified_original_pdf_table_reparse',report_uri=%s WHERE source_key='japan_pmda' AND latest_job_id IN %s AND status='open'",('s3://'+cfg['bucket']+'/research-data/operations/regulatory/publication-receipts/'+capture['window_id']+'.json',ids));resolved=c.rowcount
out={'superseded_jobs':changed,'resolved_date_failures':resolved,'replacement_manifest':capture['manifest'],'same_original_pdf_sha256':fresh['provider_pdf_sha256'],'all_source_record_ids_covered':True};(p/'legacy-replacement.json').write_text(json.dumps(out,indent=2));print(out)
