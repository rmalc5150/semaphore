import json,unittest
from unittest.mock import patch
from constellation.autostop.check import evaluate,quiet_ready,QUIET_SECONDS
from constellation.control import job_id
from constellation.sources import PROVIDERS,VERSION
from monitoring_overview import overview

class AutoStopTests(unittest.TestCase):
 def raw(self,status='succeeded',reason=None):
  spec={'source_key':'arxiv','dataset':PROVIDERS['arxiv']['dataset'],'geography':'global','start':'2016-01-01','end':'2016-01-02','edition':'current_retrieval','extractor_version':VERSION,'parameters':{}}
  result={'coverage_status':'verified_complete','manifest_uri':'s3://bucket/manifest'} if status=='succeeded' else {'reason':reason or 'source_http_503','gap_evidence_uri':'s3://bucket/failure'}
  return {'job_id':job_id(spec),'source_key':'arxiv','spec_json':json.dumps(spec),'result_json':json.dumps(result),'status':status,'updated_at':1}
 def contract(self):return {'raw_sources':['arxiv'],'raw_start':'2016-01-01','raw_end_exclusive':'2016-01-02'}
 def test_registered_failure_does_not_block_shutdown(self):
  r=evaluate([self.raw('blocked')],[],self.contract());self.assertTrue(r['eligible']);self.assertEqual(r['failure_count'],1)
 def test_retryable_failure_is_retained_and_does_not_block_shutdown(self):
  r=evaluate([self.raw('retryable_failed')],[],self.contract());self.assertTrue(r['eligible']);self.assertEqual(r['failure_count'],1)
 def test_missing_partition_is_not_completion(self):
  r=evaluate([],[],self.contract());self.assertFalse(r['eligible']);self.assertEqual(r['missing_raw_partitions'],1)
 def test_quota_deferred_raw_work_blocks_shutdown(self):
  r=evaluate([self.raw('retryable_failed','historical_daily_budget_exhausted')],[],self.contract());self.assertFalse(r['eligible'])
 def test_running_fresh_work_blocks_shutdown(self):
  self.assertFalse(evaluate([self.raw('running')],[],self.contract())['eligible'])
 def test_legacy_succeeded_invocation_without_scope_proof_is_not_complete(self):
  self.assertFalse(evaluate([self.raw()],[{'unit':'unit'}],self.contract())['eligible'])
 def test_legacy_failed_only_scope_allows_shutdown(self):
  proof={'unit':{'state':'failed_only','failures':[{'reason':'source_http_403'}]}}
  r=evaluate([self.raw()],[{'unit':'unit'}],self.contract(),proof);self.assertTrue(r['eligible']);self.assertEqual(r['failure_count'],1)
 def test_legacy_healthy_partial_scope_still_blocks(self):
  proof={'unit':{'state':'unfinished','reason':'page_budget','failures':[]}}
  self.assertFalse(evaluate([self.raw()],[{'unit':'unit'}],self.contract(),proof)['eligible'])
 def test_quiet_time_requires_same_scope_and_work_state(self):
  ready,state=quiet_ready({},'scope','queue',100);self.assertFalse(ready)
  self.assertTrue(quiet_ready(state,'scope','queue',100+QUIET_SECONDS)[0]);self.assertFalse(quiet_ready(state,'new-scope','queue',100+QUIET_SECONDS)[0])
 def test_daily_update_includes_failures_even_without_long_calendar_gap(self):
  _,body=overview({},1793001600,'2026-10-25',{'historical_autostop':{'status':'worker_stopped','failure_count':1,'failures':[{'source':'arxiv','reason':'source_http_503','job_id':'failed-job'}]}})
  self.assertIn('HISTORICAL WORKER AND REPAIR LIST',body);self.assertIn('arxiv',body);self.assertIn('source_http_503',body);self.assertIn('do not keep',body)
if __name__=='__main__':unittest.main()

class RouteProofTests(unittest.TestCase):
 def public(self,state,seeds=None):
  from constellation.autostop.proofs import inspect_routes
  from unittest.mock import Mock
  control=Mock();control.config={'prefix':'research-data/constellation-backfill','bucket':'bucket'}
  route={'unit':'fixture','public_capture_source':'fixture','start_target':'2016-01-01','end_exclusive':'2026-10-26','argv':['fixture.py']}
  with patch('pathlib.Path.read_text',return_value=json.dumps({'sources':[{'source':'fixture','seeds':seeds or ['https://example.org/']}]})),patch('constellation.autostop.proofs.get_json',return_value=state):return inspect_routes(control,[],[route],{'sources':[]})['fixture']
 def test_failed_download_retries_do_not_hold_worker_open(self):
  url='https://example.org/';proof=self.public({'done':{},'frontier':[{'url':url,'retry_after':'2099-01-01'}],'failures':{url:{'reason':'public_http_403'}}});self.assertEqual(proof['state'],'failed_only')
 def test_unattempted_public_url_still_blocks_shutdown(self):
  proof=self.public({'done':{},'frontier':[{'url':'https://example.org/'}],'failures':{}});self.assertEqual(proof['state'],'unfinished')
 def test_new_unattempted_seed_is_not_an_empty_completed_frontier(self):
  proof=self.public({'done':{},'frontier':[],'failures':{}});self.assertEqual(proof['state'],'unfinished')

class StopActionTests(unittest.TestCase):
 def execute(self,drain_error=False):
  import tempfile,time
  from pathlib import Path
  from contextlib import contextmanager
  from unittest.mock import Mock
  import constellation.autostop.check as module
  @contextmanager
  def guard(control):yield True
  with tempfile.TemporaryDirectory() as tmp:
   directory=Path(tmp);(directory/'armed-scope.json').write_text(json.dumps({'scope_sha256':'scope'}));(directory/'state.json').write_text(json.dumps({'scope_sha256':'scope','queue_fingerprint':'queue','eligible_since':time.time()-601}))
   control=Mock();control.get.return_value={'enabled':True,'pilot_job_ids':[]};ec2=control.session.client.return_value;ec2.stop_instances.return_value={'StoppingInstances':[{'InstanceId':module.TARGET}]}
   evaluation={'eligible':True,'queue_fingerprint':'queue','failure_count':1,'failures':[{'source':'arxiv','reason':'source_http_503'}]}
   patches=[patch.object(module,'ARM',directory/'armed-scope.json'),patch.object(module,'STATE',directory/'state.json'),patch.object(module,'HERE',directory),patch.object(module,'verify_target',return_value={'State':{'Name':'running'}}),patch.object(module,'scope',return_value=([],{},'scope')),patch.object(module,'dispatch_guard',guard),patch.object(module,'load_jobs',return_value=[]),patch.object(module,'evaluate',return_value=evaluation),patch.object(module,'report'),patch.object(module,'ROOT',directory),patch('constellation.autostop.proofs.inspect_routes',return_value={})]
   (directory/'config').mkdir();(directory/'config/constellation-specialist-historical.json').write_text('{"sources":[]}')
   from contextlib import ExitStack
   with ExitStack() as stack:
    for p in patches:stack.enter_context(p)
    drain=stack.enter_context(patch.object(module,'drain',side_effect=RuntimeError('uncommitted state') if drain_error else None,return_value={'proof':{'safe_to_stop':True}}))
    if drain_error:
     with self.assertRaises(RuntimeError):module.run(control,execute=True)
     ec2.stop_instances.assert_not_called()
    else:
     module.run(control,execute=True);ec2.stop_instances.assert_called_once_with(InstanceIds=[module.TARGET])
    control.set_enabled.assert_called_once_with(False)
 def test_failures_allow_stop_of_only_the_pinned_worker_after_drain(self):self.execute()
 def test_failed_checkpoint_drain_prevents_ec2_stop(self):self.execute(drain_error=True)
 def test_controller_instance_cannot_be_used_as_stop_target(self):
  from unittest.mock import Mock
  from constellation.autostop.check import verify_target,TARGET
  control=Mock();control.config={'worker_instance_id':TARGET,'controller_instance_id':TARGET}
  with self.assertRaises(ValueError):verify_target(control)
  control.session.client.assert_not_called()
