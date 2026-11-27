import copy
import hashlib
import io
import json
import unittest

from metadata_engine.benchmark_recalls import ProviderError, cpsc, mlperf, evidence
from metadata_engine.evidence import RawFailure
from mlperf_enrichment import IDENTITY_FIELDS
from research_contract import digest


class OriginalValidationTests(unittest.TestCase):
    def setUp(self):
        self.repo='mlcommons/inference_results_v5.1';self.commit='a'*40
        self.url='https://raw.githubusercontent.com/'+self.repo+'/'+self.commit+'/summary_results.json'
        self.result={'ID':'5.1-1','Model':'resnet50','Scenario':'Offline','Performance_Result':12,
                     'Performance_Units':'Samples/s','Accuracy':'99%','has_power':False}
        self.record={'source':'mlperf_results','source_url':self.url,'source_record_id':self.repo+':'+digest({k:self.result.get(k)for k in IDENTITY_FIELDS}),
                     'payload':{'data':{'repository':self.repo,'commit':self.commit,'result':self.result}}}
        self.original=json.dumps([self.result]).encode()

    def test_mlperf_exact_summary_row_and_tampering(self):
        self.assertEqual(mlperf(self.original,self.record,self.url)['record_type'],'benchmark_result')
        for field,value in [('Performance_Result',99),('Accuracy','invented'),('has_power',True)]:
            bad=copy.deepcopy(self.record);bad['payload']['data']['result'][field]=value
            with self.assertRaisesRegex(ProviderError,'original_result_mismatch'):mlperf(self.original,bad,self.url)

    def test_mlperf_rejects_wrong_identity_branch_and_repository(self):
        bad=copy.deepcopy(self.record);bad['source_record_id']='wrong'
        with self.assertRaisesRegex(ProviderError,'identity_mismatch'):mlperf(self.original,bad,self.url)
        for field,value in [('commit','main'),('repository','other/inference_results_v5.1')]:
            bad=copy.deepcopy(self.record);bad['payload']['data'][field]=value
            with self.assertRaises(ProviderError):mlperf(self.original,bad,self.url)
        with self.assertRaisesRegex(ProviderError,'not_commit_pinned'):mlperf(self.original,self.record,self.url.replace('/'+self.commit+'/','/main/'))

    def test_mlperf_csv_and_complete_row_comparison(self):
        result={'Model':'resnet','Scenario':'Offline','Result':'12','Units':'Samples/s','Location':'./closed/Vendor/results/sys/model/Offline'}
        record=copy.deepcopy(self.record);record['payload']['data']['result']=result
        record['source_url']=self.url.replace('summary_results.json','summary.csv')
        record['source_record_id']=self.repo+':'+digest({k:result.get(k)for k in IDENTITY_FIELDS})
        import csv
        out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(result));w.writeheader();w.writerow(result)
        self.assertEqual(mlperf(out.getvalue().encode(),record,record['source_url'])['record_type'],'benchmark_result')

    def test_legacy_csv_identity_is_preserved_with_exact_original_row(self):
        from metadata_engine.benchmark_recalls import LEGACY_IDENTITY_FIELDS
        record=copy.deepcopy(self.record)
        record['source_record_id']=self.repo+':'+digest({k:self.result.get(k)for k in LEGACY_IDENTITY_FIELDS})
        self.assertEqual(mlperf(self.original,record,self.url)['record_type'],'benchmark_result')
        record['payload']['data']['result']['Performance_Result']=99
        with self.assertRaisesRegex(ProviderError,'original_result_mismatch'):mlperf(self.original,record,self.url)

    def test_mlperf_supporting_file_is_not_a_result(self):
        path='open/Vendor/results/system/model/Offline/performance/run_1/mlperf_log_summary.txt'
        raw=b'MLPerf Results Summary\nSamples per second: 12\nResult is : VALID\n'
        record={'source_record_id':self.repo+':'+path,'source_url':'https://raw.githubusercontent.com/'+self.repo+'/'+self.commit+'/'+path,
                'payload':{'data':{'repository':self.repo,'commit':self.commit,'path':path,'content':raw.decode()},
                'scope':{'blob_sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}}}
        self.assertEqual(mlperf(raw,record,record['source_url'])['record_type'],'benchmark_supporting_artifact')
        record['payload']['data']['content']+=' invented'
        with self.assertRaisesRegex(ProviderError,'content_mismatch'):mlperf(raw,record,record['source_url'])

    def test_git_inventory_requires_exact_entry_and_cannot_be_result(self):
        path='closed';sha='b'*40
        tree={'sha':'c'*40,'truncated':False,'tree':[{'path':path,'type':'tree','sha':sha}]}
        url='https://api.github.com/repos/'+self.repo+'/git/trees/'+tree['sha']
        record={'source_record_id':self.repo+':'+path,'source_url':'https://github.com/'+self.repo+'/tree/'+self.commit+'/'+path,
                'payload':{'data':{'repository':self.repo,'commit':self.commit,'artifact_kind':'tree','path':path,'tree_sha':sha}}}
        self.assertEqual(mlperf(json.dumps(tree).encode(),record,url)['record_type'],'benchmark_artifact_inventory')
        tree['truncated']=True
        with self.assertRaisesRegex(ProviderError,'incomplete_tree'):mlperf(json.dumps(tree).encode(),record,url)

    def cpsc_record(self):
        row={'RecallID':123,'RecallNumber':'26123','RecallDate':'2026-01-15T00:00:00','Title':'Recall',
             'Description':'Hazard description','Products':[{'Name':'Product','NumberOfUnits':'100'}],
             'Hazards':[{'Name':'Fire'}],'URL':'https://cpsc.gov/Recalls/2026/Example'}
        url='https://www.saferproducts.gov/RestWebServices/Recall?format=json&RecallDateStart=2026-01-01&RecallDateEnd=2026-01-31'
        record={'source':'cpsc_recalls','source_record_id':'123','source_url':row['URL'],'event_at':{'value':'2026-01-15'},
                'payload':{'data':row,'scope':{'start':'2026-01-01','end':'2026-02-01'}}}
        return json.dumps([row]).encode(),record,url

    def test_cpsc_exact_recall_and_full_nested_content(self):
        raw,r,u=self.cpsc_record();self.assertEqual(cpsc(raw,r,u)['record_type'],'product_recall')
        r['payload']['data']['Hazards'][0]['Name']='tampered'
        with self.assertRaisesRegex(ProviderError,'original_row_mismatch'):cpsc(raw,r,u)

    def test_cpsc_requires_official_origin_identity_window_and_date(self):
        raw,r,u=self.cpsc_record()
        with self.assertRaisesRegex(ProviderError,'untrusted_api_url'):cpsc(raw,r,u.replace('www.saferproducts.gov','other.example'))
        with self.assertRaisesRegex(ProviderError,'projected_query'):cpsc(raw,r,u+'&fields=RecallID')
        for field,value,reason in [('source_record_id','9','identity'),('event_at',{'value':'2026-02-01'},'date')]:
            bad=copy.deepcopy(r);bad[field]=value
            with self.assertRaisesRegex(ProviderError,reason):cpsc(raw,bad,u)
        r['payload']['scope']['end']='2026-01-31'
        with self.assertRaisesRegex(ProviderError,'window_mismatch'):cpsc(raw,r,u)

    def test_evidence_rejects_checksum_tampering(self):
        raw,r,url=self.cpsc_record();r['payload']['source_evidence']=[{'key':'source_documents/cpsc_recalls/original','source_url':url,'sha256':hashlib.sha256(raw).hexdigest()}]
        class S3:
            def __init__(self,body):self.body=body
            def get_object(self,**kw):return {'Body':io.BytesIO(self.body),'ContentLength':len(self.body)}
        self.assertEqual(evidence(r,S3(raw),'bucket')[0]['validation']['recall_id'],'123')
        with self.assertRaisesRegex(RawFailure,'checksum_mismatch'):evidence(r,S3(raw+b' '),'bucket')

    def test_labelling_uses_original_validation_after_collection_envelope(self):
        from metadata_engine.labelling import label_observation
        raw,r,url=self.cpsc_record()
        envelope={'artifact_kind':'provider_record','s3_uri':'s3://bucket/batch','sha256':'a'*64,'origin':'first_party_source'}
        original={**envelope,'s3_uri':'s3://bucket/original','validation':cpsc(raw,r,url)}
        r.update(dataset='specialist_inputs',ingested_at='2026-11-13T10:00:00Z',raw_s3_uri=envelope['s3_uri'],raw_sha256=envelope['sha256'],raw_completeness_status='complete',raw_artifacts=[envelope,original])
        contract={'source_key':'cpsc_recalls','record_kind':'source_record','contract_version':'2.0.3','adapter':'api_records','adapter_version':'2.0.3','license_policy_id':'review','raw_requirements':{'required_artifact_kinds':['provider_record']}}
        labelled=label_observation(r,contract)
        self.assertEqual(labelled['record_kind'],'product_recall')
        self.assertEqual(labelled['payload']['data']['Hazards'],r['payload']['data']['Hazards'])
