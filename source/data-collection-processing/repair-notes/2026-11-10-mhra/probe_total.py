import json
from pathlib import Path
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
from mhra_product_enrichment import INDEX,public_search_key
c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'uk_mhra');d=c.json(INDEX,params={'api-version':'2017-11-11','search':'*','$top':1,'$count':'true'},api_key=public_search_key(c),api_key_parameter='api-key');print(d.get('@odata.count'));Path('repair-notes/2026-11-10-mhra/all-documents-count.json').write_text(json.dumps({'count':d.get('@odata.count'),'evidence':c.evidence},indent=2))
