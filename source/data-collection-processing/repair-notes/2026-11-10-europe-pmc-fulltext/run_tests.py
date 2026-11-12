import unittest
from unittest.mock import patch
from pathlib import Path
import test_specialist_inputs as specialist
from research_contract import load_json
original=specialist.load_json
def local_fixture(path):
 if str(path).endswith('/config/company-universe.v0.5.json'):return load_json(Path('examples/research-contract/universe.json'))
 return original(path)
names=['test_metadata_epmc_fulltext','test_epmc_fulltext_capture','test_metadata_pubmed','test_metadata_engine','test_metadata_runtime','test_specialist_inputs','test_drugsfda_inventory']
with patch.object(specialist,'load_json',side_effect=local_fixture):
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
raise SystemExit(not result.wasSuccessful())
