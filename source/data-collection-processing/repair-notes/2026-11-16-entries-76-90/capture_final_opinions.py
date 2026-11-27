import json
import boto3
import public_source_capture as pc
from research_contract import ROOT,load_json
from metadata_engine.evidence import evidence_for
from metadata_engine.streaming import session as streaming
from metadata_engine.runtime_db import Database
b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';s=boto3.client('s3',region_name='us-east-1');cfg=load_json(ROOT/'config/metadata-engine.json');db=Database(cfg);sources={v['source']:v for v in load_json(ROOT/'config/constellation-public-sources.json')['sources']};out=[]
for source,url in [('canada_cda_amc_cadth_reimbursement_reviews','https://www.cda-amc.ca/sites/default/files/DRR/2024/SR0793_Uplizna-Final_Rec.pdf'),('france_has_medicine_assessment_opinions','https://www.has-sante.fr/upload/docs/evamed/CT-21717_KISQALI_PIC_INS_AvisDef_CT21717.pdf')]:
 try:
  row,_=pc.capture(s,sources[source],{'url':url,'depth':1},'historical')
  record={'source':source,'dataset':'public_documents','source_record_id':row['sha256'],'payload':{'source_evidence':[{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'source_url':row['source_url'],'retrieved_at':row['retrieved_at']}]}}
  with streaming():artifacts=evidence_for(record,cfg['contracts'][source],s,b)
  key=pc.PREFIX+'/athena/review-final-opinion-'+row['sha256']+'.jsonl';pc.put(s,key,pc.encode(row),'application/x-ndjson');db.enqueue(source,key,s.head_object(Bucket=b,Key=key)['ETag'],'public_receipt',550);out.append({'source':source,'status':'verified','receipt_key':key,'record':row,'artifacts':artifacts,'document_role':'final_reimbursement_recommendation'if source.startswith('canada')else'final_transparency_committee_opinion'})
 except Exception as e:out.append({'source':source,'status':'failed','reason':type(e).__name__+':'+str(e)})
 s.put_object(Bucket=b,Key=base+'final-opinions.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(out[-1],default=str),flush=True)
