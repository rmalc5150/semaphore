"""Rollback-only live test of source stopping and durable email intent.

All synthetic rows share one transaction that is deliberately rolled back.
The notifier cannot see them and no email is sent by this test.
"""
import json
from contextlib import nullcontext
from pathlib import Path
import uuid

from metadata_engine.runtime_db import Database,fingerprint,encoded


class RollbackTest(Exception):pass


def main():
    config=json.loads((Path(__file__).parent/'config/metadata-engine.json').read_text());db=Database(config)
    source='metadata_selftest_'+uuid.uuid4().hex;original_tx=db.tx
    try:
        with original_tx() as c:
            db.tx=lambda:nullcontext(c)
            c.execute("INSERT INTO engine_sources(source_key,catalog_entries,contract_version,state,updated_at) VALUES(%s,'[]','test','enabled',UTC_TIMESTAMP(6))",(source,))
            for index in range(1,5):
                identity=fingerprint([source,index]);token=str(uuid.uuid4())
                c.execute("INSERT INTO engine_jobs(job_id,source_key,input_key,input_etag,input_format,contract_version,state,lease_token,lease_until,available_after,created_at) VALUES(%s,%s,%s,'test','test','test','running',%s,DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",(identity,source,'test/'+str(index),token))
                db.finish({'job_id':identity,'source_key':source,'lease_token':token},'raw_failed','synthetic_missing_primary_document',report='s3://test/rollback-only')
                c.execute('SELECT state,consecutive_raw_failures FROM engine_sources WHERE source_key=%s',(source,));state=c.fetchone()
                assert state['consecutive_raw_failures']==index
                assert state['state']==('enabled' if index<4 else 'raw_stopped')
            c.execute('SELECT COUNT(*) n FROM engine_notifications WHERE source_key=%s',(source,));assert c.fetchone()['n']==1
            c.execute("SELECT COUNT(*) n FROM engine_sources WHERE source_key=%s AND state='enabled'",(source,));assert c.fetchone()['n']==0
            raise RollbackTest()
    except RollbackTest:pass
    finally:db.tx=original_tx
    with db.tx() as c:
        c.execute('SELECT COUNT(*) n FROM engine_sources WHERE source_key=%s',(source,));assert c.fetchone()['n']==0
    print(encoded({'four_failure_stop':'passed','single_durable_notification':'passed','source_excluded_from_claim':'passed','synthetic_rows_rolled_back':True,'emails_sent':0}))


if __name__=='__main__':main()
