"""Remove duplicate inline credentials; preserve all other secret fields."""
import boto3,json,re,uuid
from pathlib import Path
s=boto3.client('secretsmanager');arn='arn:aws:secretsmanager:us-east-1:059416028963:secret:proxies-fkWzVV';r=s.get_secret_value(SecretId=arn);v=json.loads(r['SecretString']);endpoint=v['decodo-proxy-endpoint'];scheme='https'
if '://'in endpoint:scheme,endpoint=endpoint.split('://',1)
m=re.fullmatch(r'([a-zA-Z0-9.-]+):(\d{1,5})(?::.*)?',endpoint)
assert m and scheme=='https' and m[1].endswith('.decodo.com') and 0<int(m[2])<65536,'invalid_endpoint'
clean=scheme+'://'+m[1]+':'+m[2];report={'endpoint_normalized':False,'endpoint':clean,'other_secret_fields_preserved':True}
if v['decodo-proxy-endpoint']!=clean:
 assert s.get_secret_value(SecretId=arn)['VersionId']==r['VersionId'],'concurrent_secret_change'
 v['decodo-proxy-endpoint']=clean
 out=s.put_secret_value(SecretId=arn,ClientRequestToken=str(uuid.uuid4()),SecretString=json.dumps(v));report.update(endpoint_normalized=True,new_secret_version=out['VersionId'])
Path(__file__).with_name('endpoint-normalization.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
