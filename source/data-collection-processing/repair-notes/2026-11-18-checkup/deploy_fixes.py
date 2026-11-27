import os,hashlib,json
from pathlib import Path
roots=[Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/summary-worker'),*Path('/opt/constellation/legacy').glob('*')]
changed=[]
for root in roots:
 for name in ('constellation/gaps.py','hkex_originals.py'):
  p=root/name
  if not p.is_file():continue
  old=p.read_text();s=old
  if name=='hkex_originals.py':s=s.replace('MAX_ORIGINAL_BYTES = 64 * 1024 * 1024','MAX_ORIGINAL_BYTES = 128 * 1024 * 1024')
  elif 'from research_contract import digest' in s:
   s='\n'.join(line for line in s.split('\n') if line.strip()!='from research_contract import digest')
   pos=s.index('def current_core_window')
   s=s[:pos]+'''def digest(value):
    import hashlib
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()

'''+s[pos:]
  if s==old:continue
  compile(s,str(p),'exec');backup=Path('/opt/constellation/tmp/checkup1118-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():backup.write_text(old)
  temp=p.with_suffix('.1118.tmp');temp.write_text(s);os.chmod(temp,0o644);temp.replace(p);changed.append(str(p))
print(json.dumps({'changed':changed}))
