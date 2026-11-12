import json
from pathlib import Path
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
from mhra_product_enrichment import INDEX,public_search_key
c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'uk_mhra');key=public_search_key(c)
for params in [ {'search':'*','$top':1,'$count':'true','$orderby':'metadata_storage_name asc'}, {'search':'*','$top':1,'$count':'true','$orderby':'metadata_storage_name asc','$filter':"metadata_storage_name gt '0'"}]:
 try:
  d=c.json(INDEX,params={'api-version':'2017-11-11',**params},api_key=key,api_key_parameter='api-key');print(json.dumps({'params':params,'count':d.get('@odata.count'),'sample':d.get('value',[])[:1]})[:1700])
 except Exception as e:print(type(e).__name__,str(e)[:200])
