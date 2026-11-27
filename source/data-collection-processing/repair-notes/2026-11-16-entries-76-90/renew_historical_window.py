from ops import *
print(remote(T3,'''import json,time
from constellation.control import Control
from constellation.historical_guard import dispatch_guard
c=Control()
with dispatch_guard(c)as acquired:
 assert acquired,'dispatch_guard_busy_retry'
 old=c.get('control');assert old['enabled']is True,'preserve_deliberate_global_pause'
 c.s3.put_object(Bucket=c.config['bucket'],Key=BASE+'historical-control-before.json',Body=json.dumps(old,default=str).encode(),ServerSideEncryption='AES256')
 expiry=max(int(old['stop_after_epoch']),int(time.time())+7*86400)
 with c.db()as q:q.execute('UPDATE backfill_control SET stop_after_epoch=%s WHERE singleton=1 AND enabled=1 AND stop_after_epoch=%s',(expiry,old['stop_after_epoch']))
 new=c.get('control');print(json.dumps({'before':old,'after':new,'allowed':c.allowed()}))
'''.replace('BASE',repr(BASE)))['out'])
