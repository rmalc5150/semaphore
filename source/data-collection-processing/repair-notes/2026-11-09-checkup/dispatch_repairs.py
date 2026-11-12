import json,time
from pathlib import Path
from constellation.control import Control
from constellation.legacy_dispatch import dispatch
from constellation.legacy_routes import route,manifest
p=Path(__file__).parent;c=Control();out=[]
for source in ['zenodo_research_artifacts_and_usage','bls_wages']:
 unit='constellation-specialist-'+source+'.service';start=time.monotonic()
 try:result=dispatch(c,route(unit))
 except Exception as e:result={'unit':unit,'status':'error','error_type':type(e).__name__,'reason':str(e)[:250]}
 result['elapsed_seconds']=round(time.monotonic()-start,3);out.append(result);print(json.dumps(result),flush=True)
(p/'source-dispatch.json').write_text(json.dumps(out,indent=2))
