import json,time
from pathlib import Path
from specialist_authenticated import request,table_rows
from specialist_inputs import SpecialistClient
from collection_storage import StorageSettings
p=Path(__file__).parent;store=StorageSettings.load('config/collection-storage.s3.json').store();client=SpecialistClient(store,'fda_ires_recalls')
body={'displaycolumns':'','filter':json.dumps([{'eventlmdfrom':'10/28/2026'},{'eventlmdto':'10/28/2026'}]),'start':1,'rows':1,'sort':'productid','sortorder':'asc'}
try:
 data=request(client,'fda-enforcement','https://www.accessdata.fda.gov/rest/iresapi/recalls/',{'signature':str(time.time_ns())},body=body,form=True);rows=table_rows(data);out={'status':'success','fields':list(rows[0])if rows else[],'returned_rows':len(rows),'evidence':client.evidence};print(out)
except Exception as error:out={'status':'failed','reason':str(error)};print(out)
(p/'full-recall-probe.json').write_text(json.dumps(out,indent=2))
