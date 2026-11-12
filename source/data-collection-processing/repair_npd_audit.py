import subprocess,json,sys
for name,args in [('news',['news_operations.py','--status']),('patents',['patent_operations.py','daily','--status']),('prosecution',['patent_prosecution_operations.py','status']),('disclosures',['collect_daily.py','--only','documents','--status'])]:
 r=subprocess.run([sys.executable,'-B',*args],capture_output=True,text=True);print(json.dumps({'source':name,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}),flush=True)
