import json
from pathlib import Path
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
p=Path(__file__).parent;c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'drugsfda_applications');d=c.json('https://api.fda.gov/drug/drugsfda.json',params={'limit':1});out={'provider_total':d['meta']['results']['total'],'sample_application':d['results'][0]['application_number'],'evidence':c.evidence};(p/'inventory-probe.json').write_text(json.dumps(out,indent=2));print(out)
