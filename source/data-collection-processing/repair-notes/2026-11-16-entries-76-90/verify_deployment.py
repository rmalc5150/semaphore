from ops import *
import hashlib
files={name:hashlib.sha256(Path(name).read_bytes()).hexdigest()for name in ['public_source_capture.py','public_source_scope.py','nhsbsa_capture.py','specialist_inputs.py','metadata_engine/raw_catalog_review.py','metadata_engine/nhsbsa.py','metadata_engine/public_documents.py','constellation/autostop/proofs.py','reviewed_metadata_publication.py']}
results={}
for host,instance in [('t3',T3),('m7',M7)]:
 code=r'''import json,hashlib,os
from pathlib import Path
roots=[Path.cwd()]if INSTANCE==T3 else[Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source')];out={}
for root in roots:
 checked=[]
 for name,sha in FILES.items():
  p=root/name
  if not p.exists():continue
  assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,str(p);checked.append(name)
 p=root/'config/metadata-engine.json';cfg=json.loads(p.read_text());sha=hashlib.sha256(b''.join(v.read_bytes()for v in sorted((root/'metadata_engine').glob('*.py')))).hexdigest()
 if cfg.get('build_sha256')!=sha:
  cfg['build_sha256']=sha;tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
 public=json.loads((root/'config/constellation-public-sources.json').read_text());assert next(v for v in public['sources']if v['source']=='nice_technology_appraisals')['enabled']is False
 out[str(root)]={'checked_files':checked,'metadata_build_sha256':sha,'nice_still_disabled':True}
print(json.dumps(out))
'''.replace('INSTANCE',repr(instance)).replace('T3',repr(T3)).replace('FILES',repr(files));results[host]=json.loads(remote(instance,code)['out']);print(host,results[host])
(P/'deployment-verified.json').write_text(json.dumps(results,indent=2)+'\n')
