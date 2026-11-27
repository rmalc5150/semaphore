import boto3,json,io
from pathlib import Path
from pypdf import PdfReader
p=Path(__file__).parent;ref=json.loads((p/'pilot-result.json').read_text())['source_evidence'][-1];s=boto3.client('s3',region_name='us-east-1');o=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/'+ref['key'])['Body'].read());content=o['results'][0]['content'];rows=[]
for encoding in ('utf-8','cp1252','latin1'):
 r={'encoding':encoding}
 try:
  raw=content.encode(encoding);r['bytes']=len(raw);doc=PdfReader(io.BytesIO(raw),strict=True);text=''.join(page.extract_text()or''for page in doc.pages);r.update(strict_parse=True,pages=len(doc.pages),text_characters=len(text),doi_present='10.64898/2026.05.07.26352693'in text)
 except Exception as e:r.update(strict_parse=False,error_type=type(e).__name__,detail=str(e)[:120])
 rows.append(r)
(p/'raw-pdf-validation.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
