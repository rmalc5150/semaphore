import json
from ops import session,B,BASE,P,remote,M7
s=session.client('s3')
try:
 raw=s.get_object(Bucket=B,Key=BASE+'capture-proof.json')['Body'].read();(P/'capture-proof.json').write_bytes(raw);d=json.loads(raw)
 for k,v in d.get('public',{}).items():print(k,v.get('status'),[(r.get('status'),r.get('reason'))for r in v.get('results',[])],v.get('reason'))
 print('NATIVE',[(k,v['collection'],v['verified_rows'])for k,v in d.get('native',{}).items()]);print('ORIGINALS',{k:d[k]for k in ['arxiv','nasa_power_weather_and_solar_resource','usgs_earthquakes']if k in d})
except s.exceptions.NoSuchKey:print('Proof not yet written')
print(remote(M7,"import subprocess;print(subprocess.run(['journalctl','-u','optima-review-7690-native-proof-20261116.service','-n','8','--no-pager'],capture_output=True,text=True).stdout)")['out'][-2800:])
