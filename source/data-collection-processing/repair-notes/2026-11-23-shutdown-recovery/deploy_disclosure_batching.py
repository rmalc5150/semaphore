from pathlib import Path
import os,json
p=Path('/opt/constellation/auxiliary-publication/source/disclosure_collection.py');old=p.read_text();a=old.index('def collect_derived(');b=old.index('\ndef main(',a);s=old[a:b]
changes=[('        require(0 <= offset <= len(entries), "invalid_derived_cursor")','        require(0 <= offset <= len(entries), "invalid_derived_cursor")\n        checkpoint_offset = offset'),
('            if max_records is not None and processed >= max_records:\n                return', '            if max_records is not None and processed >= max_records:\n                if offset > checkpoint_offset:\n                    run.commit_page([], next_cursor=str(offset), exhausted=False)\n                return'),
('            run.commit_page(records, next_cursor=str(offset) if offset < len(entries) else None, exhausted=offset == len(entries))', '            if records or offset == len(entries) or offset - checkpoint_offset >= 64:\n                run.commit_page(records, next_cursor=str(offset) if offset < len(entries) else None, exhausted=offset == len(entries))\n                checkpoint_offset = offset')]
if 'checkpoint_offset'not in s:
 for before,after in changes:
  assert s.count(before)==1,'Deployment anchor drift';s=s.replace(before,after,1)
 new=old[:a]+s+old[b:];compile(new,str(p),'exec');backup=p.with_suffix('.pre1123batch.py')
 if not backup.exists():backup.write_text(old)
 temp=p.with_suffix('.1123batch.tmp');temp.write_text(new);st=p.stat();os.chmod(temp,st.st_mode & 0o777);os.chown(temp,st.st_uid,st.st_gid);temp.replace(p)
print('disclosure_skip_batching_installed')
