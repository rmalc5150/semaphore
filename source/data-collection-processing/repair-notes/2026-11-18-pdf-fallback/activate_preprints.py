import json,os,hashlib
from pathlib import Path
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/legacy/constellation-specialist-biorxiv_medrxiv_preprints.service')]
for root in roots:
 p=root/'config/pdf-proxy-fallback.json';c=json.loads(p.read_text());assert c['allowed_sources']==['biorxiv_medrxiv_preprints']and c['max_requests_per_day']==4 and c['max_pdf_bytes']==8388608 and c['max_requests_per_client']==1
 assert 'def _get_direct('in(root/'regulatory_collection.py').read_text()
 c['enabled']=True;tmp=p.with_suffix('.activation.tmp');tmp.write_text(json.dumps(c,indent=2)+'\n');os.chmod(tmp,0o644);tmp.replace(p)
print(json.dumps({'enabled_roots':len(roots),'allowed_sources':['biorxiv_medrxiv_preprints'],'shared_daily_requests':4,'max_pdf_bytes':8388608}))
