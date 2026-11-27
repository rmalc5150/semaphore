from ops import *
from regional_source_review import Page
updates=json.loads((P/'public-source-updates.json').read_text());entries=json.loads((P/'entries.json').read_text());by_entry={v['entry']:v['source']for v in entries};selected={91:[updates[by_entry[91]]['seeds'][0]],93:[updates[by_entry[93]]['seeds'][0]],94:[updates[by_entry[94]]['seeds'][0]],95:[updates[by_entry[95]]['seeds'][0]],96:[updates[by_entry[96]]['seeds'][0]],97:[updates[by_entry[97]]['seeds'][0]],100:updates[by_entry[100]]['seeds'],101:updates[by_entry[101]]['seeds'],102:['https://ibm.gov.in/writereaddata/files/17931042466ae09976cf2dfMSMP_JUNE_2026F_11zon.pdf'],104:updates[by_entry[104]]['seeds'][:3]}
code=r'''import json,requests
import public_source_capture as pc
updates=UPDATES;selected=SELECTED;by_entry=BY_ENTRY;out={};s=pc.boto3.client('s3',region_name='us-east-1')
for n,urls in selected.items():
 source=by_entry[n];out[source]=[]
 for url in urls:
  try:
   row,links=pc.capture(s,updates[source],{'url':url,'depth':1},'daily',publish_receipt=False)
   status='staged_original'if row['artifact_kind']=='public_document'else'discovery_only'
   key=BASE+'staged-receipts/'+source+'/'+row['sha256']+'.jsonl';pc.put(s,key,pc.encode(row),'application/x-ndjson');out[source].append({'status':status,'receipt_key':key,'record':row,'linked_documents':links[:8],'metadata_status':'awaiting_worker_validation_and_publication'})
  except Exception as e:out[source].append({'status':'failed','url':url,'reason':type(e).__name__+':'+str(e)[:180]})
  s.put_object(Bucket=pc.BUCKET,Key=BASE+'staged-originals.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
 print(source,[(v['status'],v.get('reason'))for v in out[source]],flush=True)
print(json.dumps({'key':BASE+'staged-originals.json'}))
'''.replace('UPDATES',repr(updates)).replace('SELECTED',repr(selected)).replace('BY_ENTRY',repr(by_entry)).replace('BASE',repr(BASE))
r=remote(T3,code);(P/'staging-response.json').write_text(json.dumps(r));raw=session.client('s3').get_object(Bucket=B,Key=BASE+'staged-originals.json')['Body'].read();(P/'staged-originals.json').write_bytes(raw);print(r['out'])
