import unittest,json
from pathlib import Path
from research_contract import ROOT,load_json as original
import test_market_operations,test_market_coverage_exclusions
def load(path):
 return json.loads((ROOT/'repair-notes/2026-10-21-market-coverage/universe.json').read_text()) if path==ROOT/'config/company-universe.v0.3.json' else original(path)
test_market_operations.load_json=load
test_market_coverage_exclusions.load_json=load
s=unittest.defaultTestLoader.loadTestsFromNames(['test_market_collection','test_market_operations','test_market_coverage_exclusions','test_market_symbol_mappings'])
raise SystemExit(0 if unittest.TextTestRunner().run(s).wasSuccessful() else 1)
