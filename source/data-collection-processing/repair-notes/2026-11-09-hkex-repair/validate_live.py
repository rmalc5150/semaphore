import json,hashlib,io
from pathlib import Path
import boto3
from metadata_engine.hkex_documents import Client,expand
from metadata_engine.evidence import evidence_for
from metadata_engine.labelling import label_observation
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';cfg=json.load(open('config/metadata-engine.json'));contract=cfg['contracts']['hkex_news'];record=json.load(open(p/'blocked-record.json'));c=Client(s,bucket)
expanded,gap=expand(record,c,s,bucket);out={'notice':gap,'records':[]}
for r,envelope in expanded:
 artifacts=evidence_for(r,contract,s,bucket);candidate={**r,'raw_s3_uri':envelope['s3_uri'],'raw_sha256':envelope['sha256'],'raw_completeness_status':'complete','raw_artifacts':[envelope,*artifacts]};labelled=label_observation(candidate,contract)
 out['records'].append({'source_record_id':labelled['source_record_id'],'record_id':labelled['record_id'],'raw_s3_uri':labelled['raw_s3_uri'],'artifacts':artifacts,'language':r['payload']['document_language']})
(p/'live-original-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
