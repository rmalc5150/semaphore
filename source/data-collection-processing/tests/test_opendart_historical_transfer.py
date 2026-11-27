"""Checks for OpenDART's historical host and scheduling guards."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from constellation import legacy_dispatch as dispatch
from constellation import trial_historical_access as access
from constellation import trial_specialist_backfill as runner


class OpenDartAssignmentTests(unittest.TestCase):
    def test_date_exception_requires_exact_owner_and_preserves_emergency_pause(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            host, policy, owner = (root / name for name in ('host', 'policy.json', 'owner.json'))
            host.write_text(access.INSTANCE)
            policy.write_text(json.dumps({'instance_id': access.INSTANCE, 'mode': 'no_date_cutoff',
                                          'sources': sorted(access.SOURCES)}))
            control = Mock()
            control.allowed.return_value = False
            control.get.return_value = {'enabled': True, 'stop_after_epoch': 1}
            assignment = {'instance_id': access.INSTANCE, 'source': access.OPENDART, 'mode': 'historical_only'}
            with patch.multiple(access, ROOT=root, POLICY=policy, OPENDART_OWNER=owner, HOST_ID=host):
                self.assertFalse(access.allowed(control, access.OPENDART))
                self.assertTrue(all(access.allowed(control, key) for key in access.SOURCES))
                owner.write_text(json.dumps({**assignment, 'mode': 'daily'}))
                self.assertFalse(access.allowed(control, access.OPENDART))
                owner.write_text(json.dumps(assignment))
                self.assertTrue(access.allowed(control, access.OPENDART))
                self.assertFalse(access.allowed(control, 'unassigned_provider'))
                host.write_text('i-06241bd1c4e91c2fc')
                self.assertFalse(access.allowed(control, access.OPENDART))
                host.write_text(access.INSTANCE)
                control.get.return_value = {'enabled': False, 'stop_after_epoch': 1}
                self.assertFalse(access.allowed(control, access.OPENDART))
                control.get.return_value = {'enabled': True, 'stop_after_epoch': 1}
                (root / 'batch-paused').touch()
                self.assertFalse(access.allowed(control, access.OPENDART))

    def test_controller_delegates_even_if_shared_date_expired(self):
        with TemporaryDirectory() as tmp:
            owner = Path(tmp) / 'owner.json'
            owner.write_text(json.dumps({'instance_id': access.INSTANCE, 'source': access.OPENDART,
                                         'mode': 'historical_only'}))
            row = {'unit': 'example.service', 'specialist_source': access.OPENDART}
            control = Mock()
            control.allowed.return_value = False
            with patch.object(dispatch, 'OPENDART_OWNER', owner):
                result = dispatch.dispatch(control, row)
                self.assertEqual(result['status'], 'delegated_to_trial')
                self.assertEqual(result['instance_id'], access.INSTANCE)
                control.allowed.assert_not_called()

    def test_existing_collectors_keep_priority(self):
        now = 10_000
        portwatch, copernicus = runner.SOURCES
        state = {portwatch: now-1000, copernicus: now-300}
        self.assertEqual(runner.select_source(state, runner.SOURCES, now, True), (portwatch, None))
        state = {portwatch: now-20, copernicus: now-20}
        self.assertEqual(runner.select_source(state, runner.SOURCES, now, True), (access.OPENDART, now+130))
        self.assertEqual(runner.select_source(state, runner.SOURCES, now, False), (None, None))
        state[portwatch] = now-148
        self.assertEqual(runner.select_source(state, runner.SOURCES, now, True), (None, None))


if __name__ == '__main__':
    unittest.main()
