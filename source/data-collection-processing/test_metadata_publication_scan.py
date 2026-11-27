"""Publication inventory scans remain bounded even for already-published sources."""
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
from metadata_engine.controller import (COLUMNS, catalog, daily_publication_input, publish, publish_source, register_partitions,
                                         verify_publication_batch, verify_publication_jobs)

class BoundedPublicationScan(unittest.TestCase):
    def test_catalog_validates_existing_tables_only_once_per_session(self):
        session=Mock()
        glue=session.client.return_value
        glue.get_table.return_value={'Table':{
            'StorageDescriptor':{'Columns':[{'Name':name,'Type':kind} for name,kind in COLUMNS]},
            'PartitionKeys':[{'Name':'job_id','Type':'string'}],
        }}
        config={'athena_database':'metadata','bucket':'bucket','prefix':'prefix'}
        self.assertEqual(catalog(config,session),catalog(dict(config),session))
        self.assertEqual(glue.get_table.call_count,2)
        glue.create_database.assert_not_called()
        glue.create_table.assert_not_called()

    def test_batch_verification_uses_one_grouped_query_and_checks_each_job(self):
        jobs = [{'job_id': letter * 64, 'output_rows': count}
                for count, letter in enumerate('abcdef', 1)]
        athena=Mock()
        athena.start_query_execution.return_value={'QueryExecutionId':'batch-query'}
        athena.get_query_execution.return_value={'QueryExecution':{'Status':{'State':'SUCCEEDED'}}}
        athena.get_query_results.return_value={'ResultSet':{'Rows':[
            {'Data':[{'VarCharValue':'job_id'},{'VarCharValue':'rows'}]},
            *[{'Data':[{'VarCharValue': job['job_id']}, {'VarCharValue': str(job['output_rows'])}]}
              for job in jobs],
        ]}}
        config={'athena_database':'metadata','athena_workgroup':'workgroup','bucket':'bucket','prefix':'prefix'}
        self.assertEqual(verify_publication_batch(athena, config, jobs), 'batch-query')
        self.assertEqual(athena.start_query_execution.call_count, 1)
        query=athena.start_query_execution.call_args.kwargs['QueryString']
        branches = query.split(' UNION ALL ')
        self.assertEqual([branch.count("'") // 2 for branch in branches], [5, 1])
        for job in jobs:
            self.assertEqual(query.count(job['job_id']), 1)

    def test_batch_verification_rejects_missing_partition_count(self):
        athena=Mock();athena.start_query_execution.return_value={'QueryExecutionId':'batch-query'}
        athena.get_query_execution.return_value={'QueryExecution':{'Status':{'State':'SUCCEEDED'}}}
        athena.get_query_results.return_value={'ResultSet':{'Rows':[{'Data':[]}]}}
        config={'athena_database':'metadata','athena_workgroup':'workgroup','bucket':'bucket','prefix':'prefix'}
        with self.assertRaisesRegex(ValueError,'count_mismatch'):
            verify_publication_batch(athena,config,[{'job_id':'a'*64,'output_rows':3}])

    def test_repair_publication_requires_exact_bounded_source_jobs(self):
        for source,ids in [(None,['a'*64]),('s',[]),('s',['a'*64]*6),('s',['invalid'])]:
            with self.assertRaises(ValueError):publish(None,source,job_ids=ids)

    def test_daily_lane_uses_original_manifest_mode_for_legacy_batches(self):
        db=Mock()
        db.config={'bucket':'test'}
        job={'input_format':'legacy_batch@32','priority':20,
             'input_key':'research-data/raw/source=abc/dataset=test/ingestion_date=2026-11-22/run_id=1/a.jsonl'}
        with patch('metadata_engine.controller.object_bytes',return_value=b'{"task":{"mode":"historical"}}') as get:
            cache={}
            self.assertFalse(daily_publication_input(db,job,cache))
            self.assertFalse(daily_publication_input(db,job,cache))
            get.assert_called_once()
        with patch('metadata_engine.controller.object_bytes',return_value=b'{"task":{"mode":"daily"}}'):
            self.assertTrue(daily_publication_input(db,job,{}))
        self.assertTrue(daily_publication_input(db,{'input_format':'research_feed@128','input_key':'source/daily/a'},{}))
        self.assertFalse(daily_publication_input(db,{'input_format':'research_feed@128','input_key':'source/historical/a'},{}))

    def test_global_limit_blocks_a_third_publisher_before_its_source_lock(self):
        db=Mock()
        db.config={'publication_parallel_sources':2}
        cursor=Mock()
        cursor.fetchone.return_value={'acquired':0}
        db.tx.return_value.__enter__=Mock(return_value=cursor)
        db.tx.return_value.__exit__=Mock(return_value=False)
        self.assertEqual(publish(db,'source'),0)
        self.assertEqual([call.args[1][0] for call in cursor.execute.call_args_list],
                         ['metadata-publish-slot:0','metadata-publish-slot:1'])
    def test_exact_repair_does_not_advance_normal_publication_cursor(self):
        cursor=Mock();cursor.fetchall.return_value=[]
        cursor.fetchone.return_value={'acquired':1}
        db=Mock();db.tx.return_value.__enter__=Mock(return_value=cursor);db.tx.return_value.__exit__=Mock(return_value=False)
        self.assertEqual(publish(db,'fixture',job_ids=['a'*64]),0)
        sql,args=cursor.execute.call_args_list[1].args
        self.assertIn('job_id IN (%s)',sql);self.assertEqual(args,('fixture','a'*64));db.save_cursor.assert_not_called()
    def test_already_published_rows_advance_bounded_scan(self):
        cursor=Mock();cursor.fetchall.side_effect=[[{'job_id':'a'*64,'finished_at':'2026-11-11 20:00:00'}],[]]
        cursor.fetchone.return_value={'acquired':1}
        class DB:
            session=Mock();config={}
            def __init__(self):self.saved=[]
            def cursor(self,key):return {'finished_at':'2026-11-10 20:00:00','job_id':'0'*64}
            def save_cursor(self,key,state):self.saved.append(state)
            @contextmanager
            def tx(self):yield cursor
        db=DB();self.assertEqual(publish(db,'fixture'),0)
        sql,args=cursor.execute.call_args_list[1].args
        self.assertIn('LIMIT 32',sql);self.assertIn('job_id>%s',sql)
        self.assertEqual(args[0],'fixture');self.assertEqual(db.saved[-1]['job_id'],'a'*64)

    def test_bounded_batches_preserve_exact_receipts_and_cursor(self):
        jobs=[{'job_id':f'{n:064x}','output_rows':3,'output_uri':f's3://bucket/{n}/part.parquet',
               'finished_at':'2026-11-11 20:00:00'} for n in range(55)]
        for size in (25,50):
            cursor=Mock();cursor.fetchall.side_effect=[jobs,jobs]
            db=Mock();db.config={'publication_batch_size':size,'athena_database':'metadata','bucket':'bucket','prefix':'prefix'}
            db.cursor.return_value={}
            db.tx.return_value.__enter__=Mock(return_value=cursor)
            db.tx.return_value.__exit__=Mock(return_value=False)
            with patch('metadata_engine.controller.catalog',return_value={}), \
                    patch('metadata_engine.controller.register_partitions') as register, \
                    patch('metadata_engine.controller.verify_publication_batch',return_value='verified') as verify, \
                    patch('metadata_engine.controller.put',return_value='s3://bucket/receipt') as put_receipt:
                self.assertEqual(publish_source(db,'fixture',None),size)
            self.assertEqual([len(call.args[3]) for call in register.call_args_list],[size,size])
            self.assertEqual(verify.call_args.args[2],jobs[:size])
            self.assertEqual(put_receipt.call_count,size)
            self.assertEqual(db.save_cursor.call_args.args[1]['job_id'],jobs[size-1]['job_id'])

    def test_batch_denial_uses_existing_partition_permission(self):
        glue=Mock()
        glue.batch_create_partition.side_effect=ClientError({'Error':{'Code':'AccessDeniedException'}},'BatchCreatePartition')
        config={'athena_database':'metadata','publication_glue_batch':True}
        inputs=[{'Values':[str(i)],'StorageDescriptor':{'Location':f's3://bucket/{i}/'}} for i in range(5)]
        register_partitions(glue,config,'source_observations',inputs)
        self.assertEqual(glue.create_partition.call_count,5)
        self.assertFalse(config['publication_glue_batch'])

    def test_failed_parallel_receipt_keeps_release_and_cursor_pending(self):
        jobs = [{'job_id': letter * 64, 'output_rows': 3, 'output_uri': f's3://bucket/{letter}/part.parquet',
                 'finished_at': '2026-11-11 20:00:00'} for letter in 'ab']
        cursor = Mock()
        cursor.fetchall.side_effect = [jobs, jobs]
        db = Mock()
        db.config = {'athena_database': 'metadata', 'bucket': 'bucket', 'prefix': 'prefix'}
        db.cursor.return_value = {}
        db.tx.return_value.__enter__ = Mock(return_value=cursor)
        db.tx.return_value.__exit__ = Mock(return_value=False)
        with (
            patch('metadata_engine.controller.catalog', return_value={}),
            patch('metadata_engine.controller.register_partitions'),
            patch('metadata_engine.controller.verify_publication_batch', return_value='verified'),
            patch('metadata_engine.controller.put', side_effect=RuntimeError('receipt unavailable')),
        ):
            with self.assertRaisesRegex(RuntimeError, 'receipt unavailable'):
                publish_source(db, 'fixture', None)
        self.assertFalse(any('INSERT INTO publication_releases' in call.args[0]
                             for call in cursor.execute.call_args_list))
        db.save_cursor.assert_not_called()

    def test_permission_limited_verification_assigns_correct_group_receipts(self):
        jobs=[{'job_id':str(n)} for n in range(25)]
        def query(_athena,_config,chunk):
            self.assertEqual(len(chunk),5)
            return 'query-'+chunk[0]['job_id']
        with patch('metadata_engine.controller.verify_publication_batch',side_effect=query) as verify:
            receipts=verify_publication_jobs(None,{'publication_verify_chunk_size':5},jobs)
        self.assertEqual(verify.call_count,5)
        self.assertEqual(receipts, {str(n):'query-'+str(n//5*5) for n in range(25)})

    def test_batch_existing_partition_must_match_original_location(self):
        glue=Mock()
        glue.batch_create_partition.return_value={'Errors':[{'PartitionValues':['job'],
            'ErrorDetail':{'ErrorCode':'AlreadyExistsException'}}]}
        glue.get_partition.return_value={'Partition':{'StorageDescriptor':{'Location':'s3://bucket/conflict/'}}}
        with self.assertRaisesRegex(ValueError,'partition_conflict'):
            register_partitions(glue,{'athena_database':'metadata','publication_glue_batch':True},
                'source_observations',[{'Values':['job'],'StorageDescriptor':{'Location':'s3://bucket/correct/'}}])

if __name__=='__main__':unittest.main()
