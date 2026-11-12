import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mlperf_enrichment as module
from regulatory_collection import SourceIssue

class Client:
    def __init__(self,responses): self.responses=responses;self.evidence=[];self.calls=[]
    def get(self,url):
        self.calls.append(url)
        if url not in self.responses: raise SourceIssue('source_http_404')
        raw=self.responses[url]
        self.evidence.append({'source_url':url,'sha256':hashlib.sha256(raw).hexdigest(),'key':'source_documents/test/'+hashlib.sha256(raw).hexdigest()})
        return raw

class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cache=patch.object(module,'CACHE',Path(self.temp.name));self.cache.start();self.addCleanup(self.cache.stop)
        self.data={'repository':'mlcommons/inference_results_v5.0','commit':'a'*40,
            'result':{'ID':'5.0-1','Location':'open/Vendor/results/system/model/singlestream',
                'Submitter':'Vendor','UsedModel':'model','Scenario':'SingleStream','Suite':'edge','has_power':False}}
        self.location=self.data['result']['Location']
        self.blobs={
          'open/Vendor/systems/system.json':b'{"system_name":"Example","host_processor_model_name":"CPU"}',
          'open/Vendor/measurements/system/model/singlestream/user.conf':b'*.SingleStream.min_query_count = 1024',
          self.location+'/accuracy/accuracy.txt':b'accuracy=65.750%',
          self.location+'/performance/run_1/mlperf_log_summary.txt':b'Result is : VALID\n90th percentile latency (ns) : 2147502'}
        self.responses={'https://raw.githubusercontent.com/'+self.data['repository']+'/'+self.data['commit']+'/'+p:r for p,r in self.blobs.items()}
    def entries(self,tree,base):
        return [{'path':p,'type':'blob','size':len(r),'sha':hashlib.sha1(b'blob '+str(len(r)).encode()+b'\0'+r).hexdigest()} for p,r in self.blobs.items() if p.startswith(base+'/')]
    def test_linked_evidence_keeps_roles_and_replays_without_download(self):
        c=Client(self.responses)
        with patch.object(module.Tree,'files',autospec=True,side_effect=self.entries):
            result=module.enrich(self.data,c)
            replay=module.enrich(self.data,c)
        e=result['enrichment']
        self.assertEqual(e['status'],'enriched');self.assertTrue(e['specialist_ready'])
        self.assertEqual(len(c.calls),4)
        self.assertEqual(e['event_candidate'],replay['enrichment']['event_candidate'])
        self.assertEqual(e['comparison_context']['has_power'],False)
        self.assertEqual(e['entity_candidates'][0],{'role':'submitter','name':'Vendor'})
        self.assertNotIn('enrichment',self.data)
        changed=copy.deepcopy(self.data);changed['result']['Performance_Result']=1
        with patch.object(module.Tree,'files',autospec=True,side_effect=self.entries): new=module.enrich(changed,c)['enrichment']['event_candidate']
        self.assertEqual(new['key'],e['event_candidate']['key'])
        self.assertNotEqual(new['content_version'],e['event_candidate']['content_version'])
    def test_blob_mismatch_rejected(self):
        c=Client({u:b'tampered' for u in self.responses})
        with patch.object(module.Tree,'files',autospec=True,side_effect=self.entries):
            with self.assertRaisesRegex(SourceIssue,'blob_mismatch'):module.enrich(self.data,c)
    def test_rate_limited_api_uses_standard_raw_paths_with_explicit_inventory_gap(self):
        c=Client(self.responses)
        with patch.object(module.Tree,'files',side_effect=SourceIssue('github_public_hour_budget')):
            r=module.enrich(self.data,c)['enrichment']
        self.assertEqual(r['artifact_inventory'],'standard_paths_api_deferred')
        self.assertEqual(r['status'],'review_required');self.assertTrue(r['specialist_ready'])
        self.assertEqual(len(r['artifacts']),4)
    def test_missing_and_supporting_artifacts_are_not_full_results(self):
        with patch.object(module.Tree,'files',return_value=[]):
            r=module.enrich(self.data,Client({}))['enrichment']
        self.assertFalse(r['specialist_ready']);self.assertTrue(r['gaps'])
        data={k:v for k,v in self.data.items() if k!='result'}
        self.assertFalse(module.enrich(data,Client({}))['enrichment']['event_candidate'])
    def test_truncated_tree_is_walked_in_complete_subtrees(self):
        tree=module.Tree(Client({}),self.data['repository'],self.data['commit'])
        def read(sha,recursive=False):
            if sha=='parent' and recursive: return {'truncated':True,'tree':[]}
            if sha=='parent': return {'truncated':False,'tree':[{'path':'child','type':'tree','sha':'child-sha'}]}
            return {'truncated':False,'tree':[{'path':'user.conf','type':'blob','sha':'b'*40,'size':4}]}
        with patch.object(tree,'directory',return_value='parent'),patch.object(tree,'read',side_effect=read):
            files=tree.files('open/Vendor/measurements/system')
        self.assertEqual(files[0]['path'],'open/Vendor/measurements/system/child/user.conf')

    def test_untrusted_repository_path_and_unpinned_commit(self):
        for field,value in [('repository','someone/other'),('commit','main')]:
            d=copy.deepcopy(self.data);d[field]=value
            with self.assertRaises(SourceIssue):module.enrich(d,Client({}))
        d=copy.deepcopy(self.data);d['result']['Location']='open/Vendor/../secret'
        with self.assertRaises(SourceIssue):module.enrich(d,Client({}))
    def test_cursor_remains_commit_pinned_and_pages_are_bounded(self):
        row=self.data['result'];raw=json.dumps([row]*105).encode();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        snap={'repository':self.data['repository'],'commit':self.data['commit'],'summary_file':'summary_results.json','summary_blob_sha':blob}
        url='https://raw.githubusercontent.com/'+snap['repository']+'/'+snap['commit']+'/summary_results.json'
        from specialist_inputs import item
        c=Client({url:raw})
        with patch.object(module,'enrich',side_effect=lambda d,c:d):
            rows,cursor=module.summary_page(c,snap,item)
            next_rows,next_cursor=module.summary_page(c,json.loads(cursor),item)
        self.assertEqual(len(rows),50);self.assertEqual(len(next_rows),50)
        self.assertEqual(json.loads(next_cursor)['commit'],'a'*40)
        self.assertEqual(json.loads(next_cursor)['offset'],100)
