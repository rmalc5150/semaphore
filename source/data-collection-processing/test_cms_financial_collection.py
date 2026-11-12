import csv
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from botocore.exceptions import ClientError
import cms_financial_collection as cms


class Body(io.BytesIO):
    def iter_chunks(self,size):
        while True:
            b=self.read(size)
            if not b:break
            yield b


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.db=cms.registry(Path(self.temp.name)/'state.db');self.addCleanup(self.db.close)
        self.meta={'source':'cms_open_payments','dataset_id':'dataset','edition_id':'edition',
                   'program_year':2025,'category':'general','url':'https://download.cms.gov/test.csv'}
        self.db.execute('INSERT INTO editions VALUES (?,?,1,?,\'pending\',NULL)',('edition',json.dumps(self.meta),'{}'));self.db.commit()

    def test_selection_excludes_summary_and_unrelated_datasets(self):
        def op(title):return {'title':title,'identifier':title,'distribution':[{'format':'csv','downloadURL':'https://download.cms.gov/file.csv'}]}
        result=cms.select_editions({'payments':[op('2025 General Payment Data'),op('2025 Research Payment Data'),op('2025 Ownership Payment Data'),op('2025 state payment totals'),op('2020 General Payment Data')], 'spending':{'dataset':[]}})
        self.assertEqual({r['category'] for r in result},{'general','research','ownership'})

    def test_unexpected_download_host_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'host'):
            cms.select_editions({'payments':[{'title':'2025 General Payment Data','identifier':'id','distribution':[{'format':'csv','downloadURL':'https://example.com/file.csv'}]}],'spending':{'dataset':[]}})

    def test_csv_resume_handles_unicode_quoted_newlines_and_exact_money_strings(self):
        raw='Record_ID,Program_Year,Amount,Name\r\n1,2025,100.01,"García\nResearch"\r\n2,2025,*,Second\r\n'.encode()
        lines=cms.PhysicalLines(Body(raw));header=next(csv.reader(lines))
        reader=csv.DictReader(lines,fieldnames=header,strict=True)
        rows,done=cms.rows_from_reader(self.meta,reader,1,0);offset=lines.offset
        self.assertFalse(done);self.assertEqual(json.loads(rows[0]['row_json'])['Amount'],'100.01')
        resumed=cms.PhysicalLines(Body(raw[offset:]),offset)
        rows,done=cms.rows_from_reader(self.meta,csv.DictReader(resumed,fieldnames=header),10,1)
        self.assertTrue(done);self.assertEqual(json.loads(rows[0]['row_json'])['Amount'],'*')
        self.assertEqual(rows[0]['row_number'],2);self.assertEqual(resumed.offset,len(raw))

    def test_year_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'year mismatch'):
            cms.rows_from_reader(self.meta,csv.DictReader(io.StringIO('Record_ID,Program_Year\n1,2024\n')),1,0)

    def test_malformed_rows_and_non_payment_header_rejected(self):
        with self.assertRaisesRegex(ValueError,'malformed'):
            cms.rows_from_reader(self.meta,csv.DictReader(io.StringIO('Record_ID,Program_Year\n1,2025,extra\n')),1,0)
        with self.assertRaisesRegex(ValueError,'detailed'):
            cms.validate_header(self.meta,['Summary','Amount'])

    def test_processing_archives_every_row_in_bounded_parquet_chunks(self):
        raw=b'Record_ID,Program_Year,Amount\n1,2025,0.10\n2,2025,0.20\n'
        s3=Mock();s3.get_object.side_effect=lambda **kw:{'Body':Body(raw[int(kw.get('Range','bytes=0-').split('=')[1].split('-')[0]):])}
        state={'raw_key':'raw','total_bytes':len(raw)}
        self.assertTrue(cms.process_csv(self.db,self.meta,state,s3,'bucket','prefix/',time.monotonic()+10,1))
        self.assertEqual(state['row_count'],2);self.assertEqual(state['chunks'],2)
        self.assertEqual(state['csv_offset'],len(raw));self.assertEqual(s3.put_object.call_count,2)
        self.assertTrue(state['sha256'])
        before=s3.put_object.call_count
        cms.process_csv(self.db,self.meta,state,s3,'bucket','prefix/',time.monotonic()+10,1)
        self.assertEqual(before,s3.put_object.call_count)

    def test_changed_range_never_uploads_mixed_source_bytes(self):
        s3=Mock();s3.exceptions.ClientError=ClientError
        s3.head_object.side_effect=ClientError({'Error':{'Code':'404'}},'HeadObject')
        state={'upload_id':'upload','total_bytes':3,'offset_download':0,'parts':[],'validator':'old'}
        response=Mock(status_code=206,headers={'Content-Range':'bytes 0-2/3','ETag':'new'},content=b'abc')
        with patch.object(cms,'safe_get',return_value=response),self.assertRaisesRegex(ValueError,'mix source'):
            cms.raw_download(self.db,self.meta,state,s3,'bucket','prefix/',time.monotonic()+10)
        s3.upload_part.assert_not_called()

    def test_stream_fallback_resumes_after_committed_bytes(self):
        state={'upload_id':'upload','offset_download':4,'parts':[{'PartNumber':1,'ETag':'old-part'}],'validator':'same'}
        response=Mock(headers={'ETag':'same'})
        response.iter_content.return_value=[b'ab',b'cdef',b'gh']
        s3=Mock();s3.upload_part.return_value={'ETag':'new-part'}
        with patch.object(cms,'safe_get',return_value=response):
            self.assertTrue(cms.stream_download(self.db,self.meta,state,s3,'bucket','key',time.monotonic()+10))
        self.assertEqual(s3.upload_part.call_args.kwargs['Body'],b'efgh')
        self.assertEqual(state['total_bytes'],8)
        self.assertTrue(state['raw_complete'])

    def test_no_completion_email_until_all_initial_editions_done(self):
        with patch('cms_financial_collection.boto3.client') as client:
            self.assertIsNone(cms.verify_and_email(self.db,{},Mock(),'bucket','prefix/'))
        client.assert_not_called()

    def test_athena_count_mismatch_blocks_completion_email(self):
        self.db.execute("UPDATE editions SET status='done',state=?",(json.dumps({'row_count':2}),));self.db.commit()
        # Include both sources so empty source lists aren't part of this test.
        drug={**self.meta,'source':'cms_drug_spending','edition_id':'drug'}
        self.db.execute("INSERT INTO editions VALUES (?,?,1,?,'done',NULL)",('drug',json.dumps(drug),json.dumps({'row_count':1})));self.db.commit()
        with patch('cms_financial_collection.boto3.client') as clients,patch('committed_data_athena.query',return_value={'rows':[['edition','1','1']]}),self.assertRaisesRegex(ValueError,'counts'):
            cms.verify_and_email(self.db,{'region':'us-east-1','athena_database':'test'},Mock(),'bucket','prefix/')
        self.assertEqual(clients.call_count,1)

    def test_completion_requires_both_sources_then_sends_once(self):
        state={'row_count':2,'raw_key':'raw','total_bytes':10}
        self.db.execute("UPDATE editions SET status='done',state=?",(json.dumps(state),))
        drug={**self.meta,'source':'cms_drug_spending','edition_id':'drug'}
        self.db.execute("INSERT INTO editions VALUES (?,?,1,?,'done',NULL)",('drug',json.dumps(drug),json.dumps({**state,'row_count':1})));self.db.commit()
        sns=Mock();sns.get_paginator.return_value.paginate.return_value=[{'Subscriptions':[{'Protocol':'email','Endpoint':'owner@example.com','SubscriptionArn':'arn:confirmed'}]}]
        sns.publish.return_value={'MessageId':'accepted'}
        s3=Mock();s3.head_object.return_value={'ContentLength':10}
        config={'region':'us-east-1','athena_database':'test','email_topic_arn':'arn:topic','email_recipient':'owner@example.com','job_id':'test','scope_note':'test scope'}
        with patch('cms_financial_collection.boto3.client',side_effect=[Mock(),sns]),patch('committed_data_athena.query',side_effect=[{'rows':[['edition','2','2']]},{'rows':[['drug','1','1']]}]):
            self.assertEqual(cms.verify_and_email(self.db,config,s3,'bucket','prefix/'),'accepted')
            self.assertEqual(cms.verify_and_email(self.db,config,s3,'bucket','prefix/'),'accepted')
        sns.publish.assert_called_once()

if __name__=='__main__':unittest.main()
