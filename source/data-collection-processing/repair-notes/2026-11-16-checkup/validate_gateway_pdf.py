import io,json,os,sys,boto3,hashlib
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';key='research-data/source_documents/biorxiv_medrxiv_preprints/2d8c27926b3b6579b93f36daee2ebd65c44f84847b14af69abd391c48f8c407b';raw=s.get_object(Bucket=b,Key=key)['Body'].read();result={'probe_only':True,'not_linked_to_collection_manifest':True,'source_key':key,'sha256':hashlib.sha256(raw).hexdigest(),'utf8_replacement_sequences':raw.count(b'\xef\xbf\xbd')}
try:
 from pypdf import PdfReader
 doc=PdfReader(io.BytesIO(raw),strict=True);texts=[p.extract_text()or''for p in doc.pages];result.update(strict_parse=True,pages=len(texts),text_characters=sum(map(len,texts)))
except Exception as e:result.update(strict_parse=False,validation_error=type(e).__name__)
result['promote_to_collector']=False
s.put_object(Bucket=b,Key='research-data/constellation-backfill/repairs/2026-11-16/gateway-pdf-validation.json',Body=json.dumps(result).encode(),ServerSideEncryption='AES256');print(json.dumps(result))
