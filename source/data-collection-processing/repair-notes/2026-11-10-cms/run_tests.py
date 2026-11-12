"""Use the checked-in test universe without changing runtime-managed symlinks."""
import unittest
from pathlib import Path
from unittest.mock import patch
import test_specialist_inputs
from research_contract import load_json

def fixture(path):
 if str(path).endswith('/config/company-universe.v0.5.json'):
  return load_json(Path('examples/research-contract/universe.json'))
 return load_json(path)

suite=unittest.defaultTestLoader.loadTestsFromNames(['test_metadata_cms_coverage','test_cms_coverage_capture','test_metadata_runtime','test_metadata_engine','test_specialist_inputs','test_window_publication'])
with patch.object(test_specialist_inputs,'load_json',side_effect=fixture):result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
