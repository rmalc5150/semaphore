from ops import *
print(remote(T3,r'''import json,io,zipfile
from pathlib import Path
from additional_source_apis import credentials
from filing_originals_capture import original
from specialist_inputs import SpecialistClient
from collection_storage import StorageSettings
from research_contract import ROOT
before=json.loads(Path(LOCAL_BEFORE).read_text());r=before['south_korea_fss_opendart']['samples'][0]['record'];filing=r['payload']['data'];store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store();client=SpecialistClient(store,'south_korea_fss_opendart');ref,error=original(client,'south_korea_fss_opendart',filing,credentials()['dart']);out={'filing':filing,'artifact':ref,'error':error}
if ref:
 raw=store.get(ref['key']).body;out['bytes']=len(raw)
 with zipfile.ZipFile(io.BytesIO(raw))as z:out['members']=[{'name':m.filename,'bytes':m.file_size}for m in z.infolist()][:10]
import boto3;s=boto3.client('s3',region_name='us-east-1');s.put_object(Bucket=BUCKET,Key=BASE+'dart-original-probe.json',Body=json.dumps(out,ensure_ascii=False).encode(),ServerSideEncryption='AES256');print(json.dumps(out,ensure_ascii=False))
'''.replace('LOCAL_BEFORE',repr(str((P/'before.json').resolve()))).replace('BUCKET',repr(B)).replace('BASE',repr(BASE)))['out'])
