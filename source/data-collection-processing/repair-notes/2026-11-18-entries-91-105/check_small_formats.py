"""Bounded format checks on existing samples; no queue claims or publication."""
from ops import *
import hashlib
from metadata_engine.streaming import session as validation_session,download,validate_file
from metadata_engine.regional_public import validate_ndb_workbook,validate_figure
from metadata_engine.regional_filings import evidence as filing_evidence
s3=session.client('s3');out={}
staged=json.loads((P/'staged-originals.json').read_text());before=json.loads((P/'before.json').read_text())
with validation_session():
 for source,rows in staged.items():
  if source not in ('japan_mhlw_ndb_open_data','china_nea_power_statistics'):continue
  r=rows[0]['record']
  if source=='japan_mhlw_ndb_open_data':
   key=r['artifact_uri'].split(B+'/',1)[1];entry=download(s3,B,key,r['sha256']);validate_ndb_workbook(entry);out[source]=entry['validation']
  else:
   ref=r['embedded_artifacts'][0];key=ref['s3_uri'].split(B+'/',1)[1];obj=s3.get_object(Bucket=B,Key=key);assert obj['ContentLength']<2*1024**2;raw=obj['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];out[source]={'format':validate_figure(raw),'bytes':len(raw)}
 for source,filename in [('cninfo_mainland_china_company_disclosures','cninfo-original-probe.json'),('south_korea_fss_opendart','dart-original-probe.json')]:
  probe=json.loads((P/filename).read_text());index=probe.get('index_evidence')or before[source]['samples'][0]['record']['payload']['source_evidence'][0];rid=str(probe['filing']['rcept_no'if source=='south_korea_fss_opendart'else'announcementId'])
  record={'source':source,'source_record_id':rid,'payload':{'data':{'filing':probe['filing'],'index_evidence':index,'primary_document':probe['artifact']}}}
  try:out[source]={'artifacts':filing_evidence(record,s3,B),'status':'sample_format_validated'}
  except Exception as e:out[source]={'status':'sample_format_failed','error':str(e)}
(P/'small-format-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
s3.put_object(Bucket=B,Key=BASE+'small-format-checks.json',Body=(P/'small-format-checks.json').read_bytes(),ServerSideEncryption='AES256')
for k,v in out.items():print(k,v.get('status',v.get('format')),v.get('error',''))
