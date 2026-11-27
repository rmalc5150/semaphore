from pathlib import Path
import json,os
changed=[]
for root in [Path('/opt/constellation/auxiliary-publication/source'),Path('/opt/constellation/capture-workers/source'),Path('/opt/constellation/legacy/constellation-specialist-sam_gov_opportunities.service')]:
 p=root/'specialist_inputs.py'
 if p.exists():
  old=p.read_text();a=old.index("    if job['adapter'] == 'sam_gov':",old.index('def nih_refresh_required'));b=old.index('    reasons=',a);part=old[a:b];new=old[:a]+part.replace("result.get('status') == 'failed'","result.get('status') in {'failed', 'partial'}")+old[b:];compile(new,str(p),'exec')
  if new!=old:
   backup=p.with_suffix('.pre1123.py')
   if not backup.exists():backup.write_text(old)
   tmp=p.with_suffix('.1123.tmp');tmp.write_text(new);st=p.stat();os.chown(tmp,st.st_uid,st.st_gid);os.chmod(tmp,st.st_mode & 0o777);tmp.replace(p);changed.append(str(p))
 cfg=root/'config/sam-gov-access.json'
 if cfg.exists():
  d=json.loads(cfg.read_text());d['daily_request_budget']=10;d['allowance_status']='unconfirmed; conservative cap pending owner/SAM confirmation';cfg.write_text(json.dumps(d,indent=2)+'\n');changed.append(str(cfg))
print(json.dumps(changed))
