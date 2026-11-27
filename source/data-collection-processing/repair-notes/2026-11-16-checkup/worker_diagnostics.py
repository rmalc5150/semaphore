import subprocess,json,hashlib,os,sys
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root))
for unit in ['optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-aux-cms-coverage-publication.service','optima-m7-capture-authenticated-processing.service']:
 print(unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','ExecMainStartTimestamp','-p','ExecMainExitTimestamp'],capture_output=True,text=True).stdout)
 print(subprocess.run(['journalctl','-u',unit,'-n','3','--no-pager'],capture_output=True,text=True).stdout[-1800:])
files=['regulatory_sources.py','regulatory_collection.py','additional_source_apis.py','copernicus_capture.py','public_statistics_apis.py','specialist_inputs.py','reviewed_source_gaps.py']
paths=[root,Path('/opt/constellation/capture-workers/source'),*Path('/opt/constellation/legacy').glob('constellation-core-*-historical.service'),*Path('/opt/constellation/legacy').glob('constellation-specialist-*')]
for p in paths:
 if 'specialist-'in str(p)and not any(x in str(p)for x in ('copernicus','zenodo','datacite','biorxiv','portwatch','us_census','fred_','wto_','ted_notices','edinet','usa_spending','usgs_')):continue
 print(json.dumps({'root':str(p),'files':{f:hashlib.sha256((p/f).read_bytes()).hexdigest()for f in files if(p/f).is_file()}}))
from constellation.control import Control
c=Control()
try:
 with c.db()as q:
  q.execute('SET SESSION max_execution_time=3000');q.execute("SHOW STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Max_used_connections','Aborted_connects')");print('DB',q.fetchall())
except Exception as e:print('DB_ERROR',type(e).__name__,str(e)[:200])
