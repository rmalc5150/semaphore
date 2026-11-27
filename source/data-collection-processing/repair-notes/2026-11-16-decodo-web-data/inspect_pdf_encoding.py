import json,boto3,base64
from pathlib import Path
p=Path(__file__).parent;d=json.loads((p/'pilot-result.json').read_text());key=d['source_evidence'][-1]['key'];s=boto3.client('s3',region_name='us-east-1');o=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/'+key)['Body'].read());r=o['results'][0];v=r['content'];out={'target_status':r.get('status_code'),'response_type':r.get('type'),'native_content_type':r.get('headers',{}).get('content-type'),'native_content_length':r.get('headers',{}).get('content-length'),'characters':len(v),'starts_pdf':v.startswith('%PDF-'),'starts_base64_pdf':v.startswith('JVBER'),'replacement_characters':v.count('\ufffd'),'non_latin1_characters':sum(ord(c)>255 for c in v),'all_ascii':v.isascii()}
try:body=base64.b64decode(v,validate=True);out.update(base64_valid=True,decoded_bytes=len(body),decoded_starts_pdf=body.startswith(b'%PDF-'))
except (ValueError,Exception)as e:out.update(base64_valid=False,base64_error=type(e).__name__)
(p/'encoding-inspection.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
