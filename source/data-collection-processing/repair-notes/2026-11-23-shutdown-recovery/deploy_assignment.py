from pathlib import Path
import os,base64,subprocess
p=Path('/opt/constellation/capture-workers/source/grants_review_capture.py');old=p.read_text();s=old
if 'def completed_summary('not in s:
 pos=s.index('def save(');s=s[:pos]+base64.b64decode('ZGVmIGNvbXBsZXRlZF9zdW1tYXJ5KHBsYW5uZWQsIHN0YXRlKToKIGlmIG5vdCBwbGFubmVkOnJldHVybiBOb25lCiByZXN1bHRzPVtdCiBmb3Igam9iIGluIHBsYW5uZWQ6CiAgcHJpb3I9c3RhdGUuZ2V0KCd3aW5kb3dzJyx7fSkuZ2V0KGRpZ2VzdChqb2IpLHt9KQogIGlmIChwcmlvci5nZXQoJ2pvYicpIT1qb2Igb3IgcHJpb3IuZ2V0KCdzdGF0dXMnKSE9J2NvbXBsZXRlJwogICAgICBvciBub3Qgc3RyKHByaW9yLmdldCgnbWFuaWZlc3QnLCcnKSkuc3RhcnRzd2l0aCgnbWFuaWZlc3RzL2NvbGxlY3Rpb25fcnVucy8nKSk6CiAgIHJldHVybiBOb25lCiAgcmVzdWx0cy5hcHBlbmQoeydzdGF0dXMnOidjb21wbGV0ZScsJ21hbmlmZXN0JzpwcmlvclsnbWFuaWZlc3QnXX0pCiByZXR1cm4geydzdGF0dXMnOidjb21wbGV0ZScsJ3Jldmlld2VkX3Njb3BlX29ubHknOlRydWUsJ2NvbXBsZXRlZF9zY29wZXMnOmxlbihyZXN1bHRzKSwncmVzdWx0cyc6cmVzdWx0c30K').decode()+'\n'+s[pos:]
 anchor="   if attempted>=2:break\nif __name__=='__main__':main()"
 assert anchor in s,'Unexpected assignment runner layout'
 s=s.replace(anchor,"   if attempted>=2:break\n  if attempted==0:\n   summary=completed_summary(planned,state)\n   if summary:print(json.dumps(summary),flush=True)\nif __name__=='__main__':main()",1)
 compile(s,str(p),'exec');backup=p.with_suffix('.pre1123summary.py')
 if not backup.exists():backup.write_text(old)
 temp=p.with_suffix('.1123summary.tmp');temp.write_text(s);st=p.stat();os.chmod(temp,st.st_mode & 0o777);os.chown(temp,st.st_uid,st.st_gid);temp.replace(p)
print('assignment_scope_summary_installed')
r=subprocess.run(['systemctl','start','--no-block','optima-m7-capture-assignments-reviewed-historical.service'],capture_output=True,text=True);print('assignment_replay',r.returncode,r.stderr)
