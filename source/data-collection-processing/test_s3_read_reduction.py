from datetime import date,timedelta
from hashlib import sha256
from io import BytesIO
import json
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from constellation.s3_integrity import put_immutable_checked
from metadata_engine.evidence import job_evidence_cache, object_bytes, OversizedArtifact, RawFailure
from daily_athena_routes import inspect_changes, plan_routes, verified_publisher, OWNER


class EvidenceCacheTests(TestCase):
    def test_dedup_by_key_and_expected_checksum_only_within_job(self):
        s3=Mock()
        body=b'original'
        digest=sha256(body).hexdigest()
        s3.get_object.side_effect=lambda **_: {'Body':BytesIO(body),'ContentLength':len(body)}
        with job_evidence_cache() as stats:
            self.assertEqual(object_bytes(s3,'b','key',expected=digest),body)
            self.assertEqual(object_bytes(s3,'b','key',expected='sha256:'+digest),body)
            self.assertEqual(stats['hits'],1)
            with self.assertRaises(OversizedArtifact):
                object_bytes(s3,'b','key',limit=1,expected=digest)
            self.assertEqual(s3.get_object.call_count,1)
            with self.assertRaises(RawFailure):
                object_bytes(s3,'b','key',expected='a'*64)
            object_bytes(s3,'b','key')
        object_bytes(s3,'b','key',expected=digest)
        self.assertEqual(s3.get_object.call_count,4)

    def test_reused_large_objects_are_cached_on_disk_and_cleaned(self):
        s3=Mock()
        body=b'compressed-original'*20
        digest=sha256(body).hexdigest()
        rows=[{'payload':{'source_evidence':[{'sha256':digest}]}}]*3
        s3.get_object.side_effect=lambda **_: {'Body':BytesIO(body),'ContentLength':len(body)}
        with TemporaryDirectory() as disk:
            with job_evidence_cache(rows,memory_limit=1,disk_limit=1024,disk_dir=disk) as stats:
                for _ in rows:self.assertEqual(object_bytes(s3,'b','key',expected=digest),body)
                self.assertEqual(stats['disk_hits'],2)
                self.assertEqual(stats['disk_bytes'],len(body))
                self.assertEqual(stats['memory_bytes'],0)
        self.assertEqual(s3.get_object.call_count,1)


class ChecksumWriteTests(TestCase):
    def test_verified_put_skips_readback_and_only_conflicts_read(self):
        s3=Mock()
        body=b'one full object'
        digest=sha256(body).hexdigest()
        s3.put_object.side_effect=lambda **kw: {'ChecksumSHA256':kw['ChecksumSHA256']}
        self.assertEqual(put_immutable_checked(s3,'b','k',body,'text/plain',digest),'put_checksum')
        s3.get_object.assert_not_called()
        self.assertEqual(s3.put_object.call_args.kwargs['IfNoneMatch'],'*')
        s3.put_object.side_effect=ClientError({'Error':{'Code':'PreconditionFailed'}},'PutObject')
        s3.get_object.return_value={'Body':StreamingBody(BytesIO(body),len(body))}
        self.assertEqual(put_immutable_checked(s3,'b','k',body,'text/plain',digest),'readback')

    def test_bad_digest_and_different_checksum_fail_closed(self):
        s3=Mock()
        body=b'x';digest=sha256(body).hexdigest()
        s3.put_object.return_value={'ChecksumSHA256':'other'}
        with self.assertRaises(ValueError):
            put_immutable_checked(s3,'b','k',body,'text/plain',digest)
        s3.put_object.side_effect=ClientError({'Error':{'Code':'BadDigest'}},'PutObject')
        with self.assertRaises(ClientError):
            put_immutable_checked(s3,'b','k',body,'text/plain',digest)
        s3.get_object.assert_not_called()


class DailyAthenaRoutesTests(TestCase):
    qid='aaaaaaaa-0000-0000-0000-000000000000'
    digest='a'*64
    today='2026-11-24'

    def report(self,n=20):
        sources=[{'source':f's{i:02}', 'dataset':'d','manifest_sha256':self.digest,'records':i+1} for i in range(n)]
        return {'status':'verified','sources':sources,
                'partition_verifications':[{**r,'query_id':self.qid} for r in sources]}

    def test_manifest_checksum_and_pointer_both_have_to_match(self):
        s3=Mock();published=self.report()
        raw=json.dumps(published).encode();digest=sha256(raw).hexdigest()
        pointer={**published,'verification_key':f'athena-committed/verifications/{digest}.json',
                 'verification_sha256':digest,'checked_at':'when'}
        s3.get_object.return_value={'Body':BytesIO(raw)}
        self.assertEqual(verified_publisher(s3,'b',pointer),published)
        s3.get_object.return_value={'Body':BytesIO(raw)}
        with self.assertRaises(ValueError):verified_publisher(s3,'b',{**pointer,'status':'bad'})

    def test_reuses_unchanged_manifest_and_rotates_live_checks(self):
        publisher=self.report()
        initial,changed,live,_,failed=plan_routes(publisher,{},self.today)
        self.assertEqual(len(changed),20)
        self.assertEqual(len(live),8)
        self.assertFalse(failed)
        future=(date.fromisoformat(self.today)+timedelta(days=1)).isoformat()
        pending={'name':live[0],'state':'FAILED'}
        rows,changed,new,queue,failed=plan_routes(publisher,{'published_route_proofs':initial,'route_live_failures':[pending]},future)
        self.assertFalse(changed)
        self.assertEqual({v['basis'] for v in rows.values()},{'receipt_reused'})
        self.assertEqual(len(new),8)
        self.assertNotEqual(live,new)
        self.assertEqual(new[0],pending['name'])
        self.assertIn(pending['name'],queue)

    def test_changed_batches_use_status_not_new_selects_and_report_bad_receipts(self):
        publisher=self.report(1)
        part=publisher['sources'][0]; name='s00--d'
        loc=f"s3://b/research-data/athena-committed/manifests/s00/d/{self.digest}/"
        glue=Mock();paginator=glue.get_paginator.return_value
        paginator.paginate.return_value=[{'Partitions':[{'Values':['s00','d'],'Parameters':{'optima_owner':OWNER},
                                                           'StorageDescriptor':{'Location':loc}}]}]
        athena=Mock()
        athena.batch_get_query_execution.return_value={'QueryExecutions':[
            {'QueryExecutionId':self.qid,'Status':{'State':'SUCCEEDED'}}]}
        publisher['verification']={'queries':[{**part,'batch_group':self.digest,'query_id':self.qid,
                                                'status':'verified','rows':[['1','0']]}]}
        rows,changed,_,_,_=plan_routes(publisher,{},self.today)
        statuses,fail=inspect_changes(glue,athena,'b',publisher,rows,changed)
        self.assertEqual(statuses[0]['state'],'SUCCEEDED')
        self.assertFalse(fail)
        athena.start_query_execution.assert_not_called()
        publisher['verification']['queries'][0]['rows']=[['2','0']]
        self.assertTrue(inspect_changes(glue,athena,'b',publisher,rows,changed)[1])
        self.assertEqual(rows[name]['status'],'invalid')
