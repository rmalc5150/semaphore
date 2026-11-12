"""Publication inventory scans remain bounded even for already-published sources."""
import unittest
from contextlib import contextmanager
from unittest.mock import Mock
from metadata_engine.controller import publish

class BoundedPublicationScan(unittest.TestCase):
    def test_already_published_rows_advance_bounded_scan(self):
        cursor=Mock();cursor.fetchall.return_value=[{'job_id':'a'*64,'finished_at':'2026-11-11 20:00:00'}]
        cursor.fetchone.return_value=None
        class DB:
            session=Mock();config={}
            def __init__(self):self.saved=[]
            def cursor(self,key):return {'finished_at':'2026-11-10 20:00:00','job_id':'0'*64}
            def save_cursor(self,key,state):self.saved.append(state)
            @contextmanager
            def tx(self):yield cursor
        db=DB();self.assertEqual(publish(db,'fixture'),0)
        sql,args=cursor.execute.call_args_list[0].args
        self.assertIn('LIMIT 32',sql);self.assertIn('job_id>%s',sql)
        self.assertEqual(args[0],'fixture');self.assertEqual(db.saved[-1]['job_id'],'a'*64)

if __name__=='__main__':unittest.main()
