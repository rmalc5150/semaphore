import io,json,unittest
from types import SimpleNamespace
from botocore.exceptions import ClientError
from constellation.m7_summary_queue import enqueue,read,pending,change

class Store:
    def __init__(self):self.body=None;self.version=0;self.conflict=False
    def get_object(self,**kw):
        if self.body is None:raise ClientError({'Error':{'Code':'NoSuchKey'}},'GetObject')
        return {'Body':io.BytesIO(self.body),'ETag':str(self.version)}
    def put_object(self,**kw):
        if self.conflict:
            self.conflict=False
            raise ClientError({'Error':{'Code':'PreconditionFailed'}},'PutObject')
        if 'IfMatch'in kw:assert kw['IfMatch']==str(self.version)
        if 'IfNoneMatch'in kw:assert self.body is None
        self.body=kw['Body'];self.version+=1

class QueueTests(unittest.TestCase):
    def setUp(self):self.c=SimpleNamespace(s3=Store(),config={'bucket':'fixture'})
    def test_duplicate_requests_coalesce_and_other_kind_remains(self):
        enqueue(self.c,'gaps');enqueue(self.c,'gaps');enqueue(self.c,'database')
        self.assertEqual(len(read(self.c)[0]['jobs']),2);self.assertTrue(pending(self.c))
    def test_complete_and_failed_jobs_do_not_hold_instance(self):
        enqueue(self.c,'gaps');job=read(self.c)[0]['jobs'][0]
        change(self.c,job['id'],state='failed');self.assertFalse(pending(self.c))
        enqueue(self.c,'gaps');self.assertTrue(pending(self.c))
    def test_conditional_write_conflict_retries(self):
        enqueue(self.c,'database');self.c.s3.conflict=True;enqueue(self.c,'gaps')
        self.assertEqual(len(read(self.c)[0]['jobs']),2)

if __name__=='__main__':unittest.main()
