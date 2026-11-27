from ops import *
print(remote(T3,r'''import json,hashlib
from pathlib import Path
import boto3
from filing_originals_capture import original
from specialist_inputs import SpecialistClient
from collection_storage import StorageSettings
from research_contract import ROOT
s=boto3.client('s3',region_name='us-east-1');raw=s.get_object(Bucket=BUCKET,Key=BASE+'probe-bodies/cninfo.bin')['Body'].read();data=json.loads(raw);filing=data['announcements'][0];client=SpecialistClient(StorageSettings.load(ROOT/'config/collection-storage.s3.json').store(),'cninfo_mainland_china_company_disclosures');public='https://www.cninfo.com.cn/new/hisAnnouncement/query?pageNum=1&pageSize=5&column=sse&tabName=fulltext&seDate=2026-11-17~2026-11-17';client.save(raw,public,'application/json');index_ref=dict(client.evidence[-1]);ref,error=original(client,'cninfo_mainland_china_company_disclosures',filing);out={'filing':filing,'artifact':ref,'index_evidence':index_ref,'error':error};s.put_object(Bucket=BUCKET,Key=BASE+'cninfo-original-probe.json',Body=json.dumps(out,ensure_ascii=False).encode(),ServerSideEncryption='AES256');print(json.dumps({'receipt_id':filing['announcementId'],'artifact':ref,'error':error},ensure_ascii=False))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)))['out'])
