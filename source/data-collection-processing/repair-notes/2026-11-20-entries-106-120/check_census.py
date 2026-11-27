from concurrent.futures import ThreadPoolExecutor
import json
from ops import B, BASE, P, session
from metadata_engine.worker import load_input
from metadata_engine.census_trade import evidence

source='us_census_international_trade_api'
audit=json.loads((P/'before.json').read_text())[source]
lanes=json.loads((P/'source-lanes.json').read_text())[source]['schedulers']
s3=session.client('s3')
keys={j['input_key'] for j in audit['failed_jobs']}
for state in lanes.values():
    values=sorted(state.get('jobs',{}).values(), key=lambda j:j.get('last_attempt',''),reverse=True)
    good=[j for j in values if j.get('status')=='complete' and j.get('manifest') and j.get('records',0)>0][:5]
    for j in good:
        try:
            manifest=json.loads(s3.get_object(Bucket=B,Key='research-data/'+j['manifest'])['Body'].read())
            keys.update('research-data/'+b['key'] for p in manifest['pages'][:1] for b in p['batches'][:1])
        except Exception as error:
            print('manifest lookup',type(error).__name__)
def verify(key):
    try:
        rows,_,manifest=load_input(s3,B,{'input_format':'legacy_batch','input_key':key})
        checked=[evidence(row,s3,B)[0] for row in rows]
        return dict(key=key, mode=manifest['task']['mode'], rows=len(rows), artifact=checked[0], status='verified')
    except Exception as error:
        return dict(key=key,status='failed',reason=type(error).__name__+':'+str(error)[:240])
with ThreadPoolExecutor(max_workers=5) as pool:
    out=list(pool.map(verify,sorted(keys)))
(P/'census-proof.json').write_text(json.dumps(out,indent=2)+'\n')
for r in out:print(r.get('mode'),r.get('rows'),r['status'],r.get('reason'))
