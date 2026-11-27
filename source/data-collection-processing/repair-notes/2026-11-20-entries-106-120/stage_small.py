"""Archive complete light examples without entering production metadata intake."""
import json
import os
from datetime import date
from ops import B, BASE, P, session
import public_source_capture as capture
from metadata_engine.evidence import evidence_for
from metadata_engine.streaming import session as streaming
from metadata_engine.worker import load_input
from trade_mining_sources import MDIC, COMEXT, TRACE, GEOCAT, SIACAM, MINEM, SIGMINE, request_seeds

os.environ['CONSTELLATION_SHARED_HTTP_LIMITS'] = '1'
from constellation import shared_limits
from constellation.control import Control
shared_limits._CONTROL = Control(session=session)
capture.MAX_BYTES = 2 * 1024**2
today = date.today().isoformat()
s3 = session.client('s3')
updates=json.loads((P/'capture-updates.json').read_text())
policies=json.loads((P/'policies.json').read_text())
out={}
for source in (MDIC, COMEXT, TRACE, GEOCAT, SIACAM, MINEM, SIGMINE):
    spec=updates[source]
    examples={}
    for mode in ('daily','historical'):
        seeds=request_seeds(source,mode,today) or spec.get('historical_seeds' if mode=='historical' else 'seeds') or spec['seeds']
        if source==MINEM and mode=='historical':
            seeds=spec['seeds'][:1]
        for url in seeds[:2] if source in (MDIC,SIACAM,SIGMINE) else seeds[:1]:
            try:
                entry,_=capture.capture(s3,spec,{'url':url,'depth':0},mode,publish_receipt=False)
                key=BASE+'staged-receipts/'+mode+'/'+source+'/'+entry['sha256']+'.jsonl'
                capture.put(s3,key,capture.encode(entry),'application/x-ndjson')
                rows,_,_=load_input(s3,B,{'input_format':'public_receipt','input_key':key,'contract_version':'2.0.3'})
                with streaming():
                    artifacts=[evidence_for(row,policies[source],s3,B)[0] for row in rows]
                result={'state':'validated_raw','rows':len(rows),'artifact':artifacts[0],'receipt_key':key}
            except Exception as error:
                result={'state':'failed','reason':type(error).__name__+':'+str(error)[:240],'url':url}
            examples.setdefault(mode,[]).append(result)
            print(source,mode,result['state'],result.get('rows'),result.get('reason'),flush=True)
    out[source]=examples
    (P/'staged-raw-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
s3.put_object(Bucket=B,Key=BASE+'staged-raw-proof.json',Body=(P/'staged-raw-proof.json').read_bytes(),ServerSideEncryption='AES256')
