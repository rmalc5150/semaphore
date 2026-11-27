from ops import *
updates=json.loads((P/'public-source-updates.json').read_text())
for instance in (M7,T3):
 code=r'''import json,os
from pathlib import Path
updates=UPDATES
roots=[Path.cwd()]if INSTANCE==T3 else [Path('/opt/constellation/metadata-engine-runtime'),Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/source'),*[p for p in Path('/opt/constellation/legacy').glob('constellation-public-*')if any(source in p.name for source in updates)]]
for root in roots:
 p=root/'config/constellation-public-sources.json'
 if not p.exists():continue
 cfg=json.loads(p.read_text())
 for i,row in enumerate(cfg['sources']):
  if row['source']in updates:cfg['sources'][i]={**row,**updates[row['source']]}
  elif row['source']=='england_nhsbsa_prescribing_data':row['enabled']=False;row['scope_note']='Catalogue-only public route replaced by native NHSBSA datastore daily and historical collectors; original receipts retained.'
 tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.chown(tmp,1000,1000);tmp.replace(p)
print('Scoped source plans updated; NICE pause preserved')
'''.replace('UPDATES',repr(updates)).replace('INSTANCE',repr(instance)).replace('T3',repr(T3));print(remote(instance,code)['out'])
