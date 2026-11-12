import json
import time
import unittest
from unittest.mock import patch
from constellation.recover_disk_full_jobs import eligible

class RecoveryTests(unittest.TestCase):
    def test_only_unchanged_proven_failures_on_enabled_unpaused_routes_qualify(self):
        job={'status':'blocked','lease_until':0,'updated_at':time.time(),
             'result_json':json.dumps({'reason':'executor_verification_error','error':'OSError'}),
             'spec_json':json.dumps({'parameters':{'unit':'example.service'}})}
        proof={'errno':28,'at':job['updated_at']}
        with patch('constellation.recover_disk_full_jobs.validate_spec'),patch('constellation.recover_disk_full_jobs.route',return_value={'unit':'example.service','execution_enabled':True,'specialist_source':'example'}),patch('constellation.recover_disk_full_jobs.unit_pause',return_value=None),patch('constellation.recover_disk_full_jobs.is_paused',return_value=False)as paused:
            self.assertTrue(eligible(job,proof))
            self.assertFalse(eligible({**job,'status':'running'},proof))
            self.assertFalse(eligible(job,{**proof,'errno':13}))
            self.assertFalse(eligible(job,{**proof,'at':proof['at']-60}))
            paused.return_value=True
            self.assertFalse(eligible(job,proof))

    def test_changed_route_is_not_requeued(self):
        job={'status':'blocked','lease_until':0,'updated_at':100,
             'result_json':json.dumps({'reason':'executor_verification_error','error':'OSError'}),
             'spec_json':json.dumps({'parameters':{'unit':'retired.service'}})}
        with patch('constellation.recover_disk_full_jobs.validate_spec',side_effect=ValueError('retired')):
            self.assertFalse(eligible(job,{'at':100,'errno':28}))
