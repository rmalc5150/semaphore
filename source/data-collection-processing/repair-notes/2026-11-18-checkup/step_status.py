import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from collection_storage import StorageSettings
store=StorageSettings.load(root/'config/collection-storage.s3.json').store()
stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
for lane,source,start,end in [('daily','hkex-filings','2026-10-07','2026-10-08'),('historical','clinicaltrials','2022-08-01','2022-09-01')]:
 r=json.loads(store.get('operations/streams/'+stream+'/'+lane+'/'+source+'/'+start+'_'+end+'.json').body);print(source,r.get('status'),r.get('reason'))
 if r.get('manifest'):
  m=json.loads(store.get(r['manifest']).body);print('MANIFEST',m.get('record_count'),m.get('expected_records'),m.get('reason_code'),len(m.get('pages',[])))
p=Path('/opt/constellation/tmp/checkup1118/fda-publication.log');print('FDA_LOG',p.read_text()[-2500:] if p.exists()else'missing')
print('FDA_UNIT',subprocess.run(['systemctl','show','optima-fda-repair-publication-20261118.service','-p','ActiveState','-p','Result'],capture_output=True,text=True).stdout)
