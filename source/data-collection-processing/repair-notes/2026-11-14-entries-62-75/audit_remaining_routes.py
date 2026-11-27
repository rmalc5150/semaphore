import json
from ops import remote,T3,M7,session,B,BASE,P
code='''import json,subprocess,boto3
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');out={'public':{},'units':{},'runtime_paths':{}}
for source in ['bis_sdmx_api','ilostat_labor_statistics','unido_iip_and_indstat','imf_portwatch_shipping_activity']:
 row=next(r for r in json.load(open('config/constellation-public-sources.json'))['sources']if r['source']==source)
 rev=row.get('raw_content_revision')
 for mode in ['daily','historical']:
  key='research-data/constellation-backfill/public-capture/states/'+mode+'/'+source+('/'+rev if rev else'')+'.json'
  try:out['public'][source+':'+mode]=json.loads(s.get_object(Bucket=BUCKET,Key=key)['Body'].read(2*1024*1024))
  except s.exceptions.NoSuchKey:out['public'][source+':'+mode]={'missing':True,'key':key}
for u in ['optima-authenticated-daily.service','optima-authenticated-daily.timer','optima-authenticated-historical.timer','optima-patents-prosecution.service','optima-patents-prosecution.timer','optima-metadata-controller.service','optima-specialist-daily.service','optima-specialist-daily.timer','constellation-historical-dispatch.service','constellation-historical-dispatch.timer']:
 out['units'][u]=subprocess.run(['systemctl','show',u,'-p','LoadState','-p','ActiveState','-p','Result','-p','ExecMainExitTimestamp','-p','ExecMainStatus','-p','UnitFileState'],capture_output=True,text=True).stdout
current=json.loads(s.get_object(Bucket=BUCKET,Key='research-data/operations/s3-runtime/current.json')['Body'].read())
for name,ref in current['paths'].items():
 if any(word in name for word in ['authenticated','sam-','patent-prosecution'])and name.endswith('.json'):
  out['runtime_paths'][name]={'ref':ref}
  if 'scheduler'in name or'prosecution'in name:
   try:
    r=s.get_object(Bucket=BUCKET,Key=ref['key']);body=r['Body'].read(16*1024*1024);r['Body'].close();out['runtime_paths'][name]['state']=json.loads(body)
   except Exception as error:out['runtime_paths'][name]['error']=str(error)[:100]
key=BASE+'remaining-route-audit.json';s.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key}))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE))
r=remote(T3,code);raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'remaining-route-audit.json').write_bytes(raw);d=json.loads(raw)
print('PUBLIC',[(k,len(v.get('done',{})),len(v.get('failures',{})),v.get('updated_at'),v.get('missing'))for k,v in d['public'].items()]);print('UNITS',d['units']);print('RUNTIME_PATHS',list(d['runtime_paths']))
r=remote(M7,'''import json,subprocess
from pathlib import Path
out={'unit':subprocess.run(['systemctl','show','optima-m7-capture-patents-prosecution.service','optima-m7-specialist-daily.service','-p','Id','-p','Result','-p','ActiveState','-p','ExecMainStatus','-p','ExecMainExitTimestamp','-p','WorkingDirectory'],capture_output=True,text=True).stdout}
p=Path('/opt/constellation/capture-workers/source/config/patent-prosecution-operations.m7-bounded.json')
if p.exists():out['prosecution_config']=json.loads(p.read_text())
print(json.dumps(out))
''');(P/'m7-capture-routes.json').write_text(r['out']);print('M7',r['out'])
