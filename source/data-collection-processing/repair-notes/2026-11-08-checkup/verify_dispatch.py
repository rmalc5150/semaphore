import json,time
from pathlib import Path
from constellation.control import Control
from constellation.legacy_dispatch import dispatch
from constellation.legacy_routes import route
p=Path(__file__).parent;c=Control();out=[]
for source in ['usda_fas_production_supply_and_distribution','us_census_international_trade_api']:
 started=time.monotonic()
 try:result=dispatch(c,route('constellation-specialist-'+source+'.service'))
 except Exception as e:result={'source':source,'status':'error','error_type':type(e).__name__,'error':str(e)[:250]}
 result['elapsed_seconds']=round(time.monotonic()-started,3);out.append(result)
 (p/'source-dispatch.json').write_text(json.dumps(out,indent=2));print(json.dumps(result),flush=True)
