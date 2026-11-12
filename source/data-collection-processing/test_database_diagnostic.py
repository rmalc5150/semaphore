import copy
from contextlib import contextmanager
import time
import unittest
from unittest.mock import Mock,MagicMock,patch
import pymysql
from constellation.database_diagnostic import run
from constellation.control import Control

class Cursor:
    def __init__(self,lane,fail_once=False):self.lane=lane;self.fail_once=fail_once;self.count_timeout=False;self.statements=[]
    def execute(self,sql,params=()):
        self.statements.append((sql,params))
        if 'information_schema.TABLES'in sql:self.rows=[{'table_name':'engine_jobs'if self.lane=='metadata'else'backfill_jobs','estimated_rows':99}]
        elif 'FROM engine_sources'in sql:self.rows=[{'source_key':'meta','state':'enabled','last_reason':None},{'source_key':'paused','state':'owner_paused','last_reason':None}]
        elif 'DISTINCT source_key'in sql:self.rows=[{'source_key':'raw'},{'source_key':'__lease_check__'}]
        elif 'COUNT(*)'in sql:
            if self.count_timeout:self.count_timeout=False;raise pymysql.OperationalError(3024,'count timed out')
            states=({'accepted':2,'raw_failed':2,'retry':1}if params[0]=='meta'else{'queued':2})if self.lane=='metadata'else{'succeeded':4,'blocked':2}
            self.rows=[{'job_state':k,'jobs':v}for k,v in states.items()]
        elif self.lane=='metadata'and 'job_id FROM'in sql:
            ids={'accepted':['a1','a2'],'raw_failed':['m1','m2'],'retry':['m3']}if params[0]=='meta'else{'queued':['p1','p2']}
            self.rows=[{'job_id':value}for value in ids.get(params[1],[])if value>params[2]][:params[-1]]
        elif self.lane=='metadata':
            if self.fail_once:self.fail_once=False;raise pymysql.OperationalError(3024,'bounded read timed out')
            rows=[{'job_id':'m1','reason':'truncated_document'},{'job_id':'m2','reason':'truncated_document'}]if params[1]=='raw_failed'else[{'job_id':'m3','reason':'retry_connection'}]
            self.rows=[r for r in rows if r['job_id']>params[2]][:params[-1]]
        else:
            rows=[{'job_id':'h1','updated_at':10,'result_json':'{"reason":"source_http_403"}'},{'job_id':'h2','updated_at':10,'result_json':'{"reason":"source_http_403"}'}]
            self.rows=[r for r in rows if (r['updated_at'],r['job_id'])>(params[2],params[4])][:params[-1]]
    def fetchall(self):return self.rows

class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.meta_cursor=Cursor('metadata');self.history_cursor=Cursor('historical');self.saved={}
        @contextmanager
        def meta():yield self.meta_cursor
        @contextmanager
        def historical():yield self.history_cursor
        self.control=Mock();self.control.db=historical;self.metadata=Mock();self.metadata.tx=meta
    def save(self,c,identity,**values):self.saved.update(copy.deepcopy(values))
    def test_complete_counts_and_failure_causes_preserve_owner_pauses(self):
        report=run(self.control,{'id':'job'},self.save,lambda:'now',metadata=self.metadata)
        self.assertEqual(report['job_rows_counted'],13)
        self.assertEqual(report['sources_audited'],{'metadata':2,'historical':1})
        self.assertEqual(report['failure_counts']['historical|raw|blocked|source_http_403'],2)
        self.assertEqual(report['failure_counts']['metadata|meta|raw_failed|truncated_document'],2)
        self.assertEqual(report['source_controls'][1]['state'],'owner_paused')
        count_queries=[sql for cur in (self.meta_cursor,self.history_cursor)for sql,_ in cur.statements if 'COUNT(*)'in sql]
        self.assertTrue(all('FORCE INDEX('in sql and 'WHERE source_key=%s'in sql for sql in count_queries))
    def test_deadline_yields_a_resumable_checkpoint_then_finishes(self):
        self.assertIsNone(run(self.control,{'id':'job'},self.save,lambda:'now',deadline_seconds=0,metadata=self.metadata))
        self.assertEqual(self.saved['state'],'pending')
        report=run(self.control,{'id':'job','checkpoint':self.saved['checkpoint']},self.save,lambda:'now',metadata=self.metadata)
        self.assertEqual(report['job_rows_counted'],13)
    def test_timeout_reduces_batch_without_losing_or_double_counting_failures(self):
        self.meta_cursor.fail_once=True
        with patch('constellation.database_diagnostic.time.sleep'):
            report=run(self.control,{'id':'job'},self.save,lambda:'now',metadata=self.metadata)
        self.assertEqual(report['query_metrics']['retries'],1)
        self.assertEqual(sum(report['failure_counts'].values()),5)
        self.assertEqual(self.saved['checkpoint']['batch_size'],12)
    def test_large_count_timeout_switches_to_bounded_index_pages(self):
        self.meta_cursor.count_timeout=True
        report=run(self.control,{'id':'job'},self.save,lambda:'now',metadata=self.metadata)
        self.assertEqual(report['job_rows_counted'],13)
        self.assertEqual(report['counts']['metadata|meta|accepted'],2)
        self.assertEqual(report['query_metrics']['retries'],1)
    def test_failed_rollback_preserves_the_original_exception(self):
        c=Control(config={'region':'us-east-1','controller_secret_arn':'fixture','db_host':'fixture','database':'fixture'},session=Mock())
        c._credentials={'username':'fixture','password':'fixture'};c._credentials_at=time.time()
        connection=MagicMock();connection.rollback.side_effect=pymysql.InterfaceError(0,'broken connection')
        with patch('constellation.control.pymysql.connect',return_value=connection):
            with self.assertRaisesRegex(RuntimeError,'original timeout'):
                with c.db():raise RuntimeError('original timeout')

if __name__=='__main__':unittest.main()
