import json
from ops import remote,T3,M7,session,B,BASE,P
s=session.client('s3')
for name in ['replay-publication.json','statistics-capture.json']:
 try:
  raw=s.get_object(Bucket=B,Key=BASE+name)['Body'].read();(P/name).write_bytes(raw);print(name,raw.decode()[:4500])
 except s.exceptions.NoSuchKey:print(name,'not yet written')
for host,instance in [('t3',T3),('m7',M7)]:
 r=remote(instance,'''import subprocess,json
units=UNITS
out={u:subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','ExecMainExitTimestamp'],capture_output=True,text=True).stdout for u in units}
for u in units:
 out[u+' journal']=subprocess.run(['journalctl','-u',u,'-n','5','--no-pager'],capture_output=True,text=True).stdout
print(json.dumps(out))
'''.replace('UNITS',repr(['optima-daily-health-audit.service','optima-eodhd-inventory.service','optima-m7-database-summary.service','optima-people-collection.service','optima-source-schedule-daily.service']if host=='t3'else['optima-economic-replay-20261114.service','optima-native-statistics-proof-20261114.service'])))
 (P/('progress-'+host+'.json')).write_text(r['out']);print(host,r['out'][:5500])
