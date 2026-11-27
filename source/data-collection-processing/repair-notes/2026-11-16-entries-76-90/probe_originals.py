import json
from ops import remote,M7,session,B,BASE,P
code=r'''import json,os,sys,boto3
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
s=boto3.client('s3',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());out={}
for source in before:
 if source in ('decodo_shared_web_retrieval_access_layer','nice_technology_appraisals'):continue
 jobs=before[source]['native_jobs'][:1]or before[source]['failed_jobs'][:1]
 if not jobs:continue
 j=jobs[0];raw=s.get_object(Bucket=b,Key=j['input_key'])['Body'].read(4*1024*1024);row=json.loads(raw.splitlines()[0])
 if 'pages'in row:
  m=row;page=m['pages'][0];record=json.loads(s.get_object(Bucket=b,Key=page['records']['uri'].split(b+'/',1)[1])['Body'].read(2*1024*1024).splitlines()[0]);out[source]={'manifest':j['input_key'],'record':record}
 else:out[source]={'record':row}
 if row.get('artifact_uri'):
  key=row['artifact_uri'].split(b+'/',1)[1];r=s.get_object(Bucket=b,Key=key);body=r['Body'].read(4*1024*1024);r['Body'].close();out[source]['prefix_hex']=body[:16].hex()
  if body.startswith(b'%PDF-'):
   import io
   from pypdf import PdfReader
   pdf=PdfReader(io.BytesIO(body));out[source]['pages']=len(pdf.pages);out[source]['text']='\n'.join(p.extract_text()or''for p in pdf.pages[:2])[:5000]
s.put_object(Bucket=b,Key=base+'original-probes.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':base+'original-probes.json'}))
'''
r=remote(M7,code);raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'original-probes.json').write_bytes(raw)
for k,v in json.loads(raw).items():print(k,json.dumps(v)[:1200])
