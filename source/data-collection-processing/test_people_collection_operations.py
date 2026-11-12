import unittest
from unittest.mock import Mock,patch
import people_collection_operations as operations

class PlacementTests(unittest.TestCase):
    def test_normal_daily_capture_does_not_launch_the_heavy_publisher(self):
        with patch.object(operations.subprocess,'run',return_value=Mock(returncode=0))as run:
            self.assertEqual(operations.main(['--lane','daily']),0)
        commands=[call.args[0]for call in run.call_args_list]
        self.assertEqual(len(commands),2)
        self.assertFalse(any('research_publication.py'in command for command in commands))
        self.assertIn('people_social_collection.py',commands[0])
        self.assertIn('personnel_archive.py',commands[1])
    def test_worker_can_explicitly_request_inline_publication(self):
        with patch.object(operations.subprocess,'run',return_value=Mock(returncode=0))as run:
            self.assertEqual(operations.main(['--lane','daily','--publish']),0)
        self.assertIn('research_publication.py',run.call_args_list[-1].args[0])

if __name__=='__main__':unittest.main()
