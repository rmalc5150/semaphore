from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
import constellation.clean_publication_staging as staging

class StagingTests(unittest.TestCase):
    def test_only_the_selected_units_staging_is_cleared(self):
        with tempfile.TemporaryDirectory()as tmp,patch.object(staging,'BASE',Path(tmp)):
            one=Path(tmp)/'optima-m7-one.service';two=Path(tmp)/'optima-m7-two.service';one.mkdir();two.mkdir()
            (one/'derived.parquet').write_text('temporary');(two/'keep').write_text('keep')
            staging.clean(one.name);self.assertEqual(list(one.iterdir()),[]);self.assertTrue((two/'keep').exists())
    def test_symlinked_staging_root_is_rejected(self):
        with tempfile.TemporaryDirectory()as tmp,patch.object(staging,'BASE',Path(tmp)):
            other=Path(tmp)/'other';other.mkdir();(other/'keep').write_text('keep');(Path(tmp)/'optima-m7-one.service').symlink_to(other)
            with self.assertRaises(ValueError):staging.clean('optima-m7-one.service')
            self.assertTrue((other/'keep').exists())
    def test_child_symlink_is_removed_without_following_it(self):
        with tempfile.TemporaryDirectory()as tmp,patch.object(staging,'BASE',Path(tmp)):
            external=Path(tmp)/'external';external.write_text('keep');root=Path(tmp)/'optima-m7-one.service';root.mkdir();(root/'link').symlink_to(external)
            staging.clean(root.name);self.assertEqual(external.read_text(),'keep')
            with self.assertRaises(ValueError):staging.clean('../../outside')

if __name__=='__main__':unittest.main()
