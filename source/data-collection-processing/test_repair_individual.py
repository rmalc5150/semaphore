import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import repair_individual as runner

class RepairRunnerTests(unittest.TestCase):
    def test_failure_retains_log_and_checkpoint_status(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner,'OUT',Path(directory)):
            def run(command,**kwargs):
                self.assertNotIn('--pipe',command)
                self.assertEqual(kwargs['stderr'],runner.subprocess.STDOUT)
                kwargs['stdout'].write(b'{"stage":"s3_checkpoint_verified","unit":"repair-test"}\n')
                return SimpleNamespace(returncode=1)
            with patch.object(runner.subprocess,'run',side_effect=run):
                result=runner.execute('test',['example.py'],10)
            self.assertEqual(result['status'],'needs_attention')
            self.assertTrue(result['checkpoint_verified'])
            self.assertTrue((Path(directory)/'test.log').is_file())
    def test_zero_exit_does_not_imply_verified_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(runner,'OUT',Path(directory)):
            with patch.object(runner.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
                result=runner.execute('test',['example.py'],10)
            self.assertFalse(result['checkpoint_verified'])
            self.assertEqual(result['status'],'execution_completed')

if __name__=='__main__':unittest.main()
