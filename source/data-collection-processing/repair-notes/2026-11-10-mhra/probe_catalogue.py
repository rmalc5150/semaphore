import json
from pathlib import Path
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from mhra_product_enrichment import public_search_key,INDEX
p=Path(__file__).parent;c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'uk_mhra');key=public_search_key(c);d=c.json(INDEX,params={'api-version':'2017-11-11','search':'*','$top':1,'$count':'true','$filter':"doc_type eq 'Spc'"},api_key=key,api_key_parameter='api-key');(p/'catalogue-probe.json').write_text(json.dumps({'count':d.get('@odata.count'),'keys':list(d),'sample':d.get('value',[])[:1],'evidence':c.evidence},indent=2));print(json.dumps({'count':d.get('@odata.count'),'keys':list(d),'sample':d.get('value',[])[:1]})[:3000])
