import unittest
from pipeline_health import inspect_stages

class PipelineHealthTests(unittest.TestCase):
    def registry(self,keys=None):
        return {'stages':{'tft':{'label':'TFT testing','unit_patterns':['optima-tft-test*.service'],'receipt_keys':keys or []}}}
    def test_planned_stage_not_healthy(self):
        self.assertEqual(inspect_stages(self.registry(),[],lambda u:{},lambda k:None,lambda a:None)['tft']['status'],'awaiting_setup')
    def test_discovered_worker_requires_artifacts(self):
        stage=inspect_stages(self.registry(),['optima-tft-test.service','optima-other.service'],lambda u:{'activity':'idle'},lambda k:None,lambda a:None)['tft']
        self.assertEqual(stage['status'],'awaiting_artifact_registration')
        self.assertEqual(list(stage['jobs']),['optima-tft-test.service'])
    def test_missing_receipt_and_corrupt_artifact_fail(self):
        self.assertEqual(inspect_stages(self.registry(['models/receipt.json']),[],lambda u:{},lambda k:None,lambda a:None)['tft']['status'],'verification_failed')
        def bad(a):raise ValueError('checksum mismatch')
        receipt={'status':'verified','artifacts':[{'key':'models/test.json'}]}
        self.assertEqual(inspect_stages(self.registry(['models/receipt.json']),[],lambda u:{},lambda k:receipt,bad)['tft']['status'],'verification_failed')
    def test_metrics_retained_from_validated_receipt(self):
        receipt={'status':'verified','artifacts':[{'key':'models/test.json'}],'metrics':{'loss':0.2},'validation':{'split':'held_out'}}
        stage=inspect_stages(self.registry(['models/receipt.json']),[],lambda u:{},lambda k:receipt,lambda a:None)['tft']
        self.assertEqual(stage['status'],'outputs_verified')
        self.assertEqual(stage['receipts'][0]['metrics'],{'loss':0.2})
