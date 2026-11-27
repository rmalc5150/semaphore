import json,boto3
from pathlib import Path
from decodo_web_data import decode_pdf
from regulatory_collection import SourceIssue
p=Path(__file__).parent;pilot=json.loads((p/'pilot-result.json').read_text());ref=pilot['source_evidence'][-1];s=boto3.client('s3',region_name='us-east-1');o=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/'+ref['key'])['Body'].read());r=o['results'][0]
try:decode_pdf(o,'10.64898/2026.05.07.26352693');raise AssertionError('Unexpected validated PDF')
except SourceIssue as e:reason=e.code
result={'credential_verified':True,'secret_arn':'arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV','token_field':'decodo-web','endpoint':'https://data.decodo.com/v1/scrape','method':'POST','request_body':{'url':'https://www.medrxiv.org/content/10.64898/2026.05.07.26352693v2.full.pdf'},'target_status':r['status_code'],'task_id':r.get('task_id'),'created_at':r.get('created_at'),'updated_at':r.get('updated_at'),'content_location':'results[0].content','content_type':r.get('type'),'base64_validated':False,'reason':reason,'envelope_evidence':ref,'not_promoted_to_pdf_evidence':True,'production_fallback_deployed':False}
(p/'live-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
