import json,unittest
from pathlib import Path
from unittest.mock import patch
from collection_storage import StorageSettings
from research_contract import ROOT,digest
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store()
h='f4c7ae2b11bea39032454f05461576fddd1fd3364cd88a3d91f5ff55ba4d1ee4'
raw=s.get('manifests/configurations/universe/'+h+'.json').body.decode();assert digest(json.loads(raw))==h
original=Path.read_text
def read(path,*a,**kw):
 if path==ROOT/'config/company-universe.v0.5.json':return raw
 return original(path,*a,**kw)
names=['test_checkup_repairs','test_specialist_inputs','test_caiso_enrichment','test_nih_pagination','test_disclosure_content','test_collection_health_repairs','test_collection_alerts','test_monitoring_overview','test_regulatory_collection']
with patch.object(Path,'read_text',read):
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(names))
raise SystemExit(not result.wasSuccessful())
