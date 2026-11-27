import os,sys,time,json
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from constellation.shared_limits import admit
start=time.time()
try:admit('https://api.fda.gov/drug/drugsfda.json');print('admit_ok',time.time()-start)
except Exception as e:print('admit_failed',type(e).__name__,str(e)[:400],time.time()-start)
from constellation.control import Control
try:
 with Control().db() as c:
  c.execute('SHOW FULL PROCESSLIST');rows=c.fetchall();print('DB',json.dumps([{k:r.get(k)for k in ['Id','User','Command','Time','State']}for r in rows if (r.get('Time')or 0)>8])[:2500])
except Exception as e:print('DB_FAILED',type(e).__name__,str(e)[:400])
