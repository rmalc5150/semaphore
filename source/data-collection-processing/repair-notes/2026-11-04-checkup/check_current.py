import json
from pathlib import Path
import boto3
from additional_source_apis import get_json
from collection_health_exporter import Evidence
p=Path(__file__).parent;out={}
class Capture:
 def save(self,*args):pass
try:
 d,_=get_json(Capture(),'https://api.census.gov/data/timeseries/intltrade/exports/hs',{'get':'CTY_CODE,CTY_NAME,E_COMMODITY,ALL_VAL_MO','E_COMMODITY':'282520','CTY_CODE':'*','YEAR':'2016','MONTH':'02'},'US-census','key');out['census']={'status':'response_received','rows':len(d)-1 if isinstance(d,list)else None}
except Exception as e:out['census']={'status':'failed','reason':getattr(e,'code',type(e).__name__)}
s=boto3.client('s3',region_name='us-east-1');ev=Evidence(s,'data-collection-059416028963-us-east-1-an','research-data');value,sha,at=ev.read('operations/s3-runtime/current.json');out['runtime_index']={'status':'read_verified','paths':len(value.get('paths',{})),'sha256':sha,'modified_at':at}
(p/'live-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
