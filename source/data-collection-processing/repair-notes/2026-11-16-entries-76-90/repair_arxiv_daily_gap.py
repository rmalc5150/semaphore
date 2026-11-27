from ops import *
print(remote(T3,'''import json
from constellation.control import Control
from constellation.historical_guard import dispatch_guard
from constellation.sources import PROVIDERS,VERSION
c=Control();spec={'source_key':'arxiv','dataset':PROVIDERS['arxiv']['dataset'],'geography':'global','start':'2026-10-27','end':'2026-10-28','edition':'current_retrieval','extractor_version':VERSION,'parameters':{}}
with dispatch_guard(c)as acquired:
 assert acquired and c.allowed()
 identity=c.register(spec)
state=c.get('job#'+identity);out={'job_id':identity,'status':state['status'],'spec':spec,'reason':'Replace an October-30 daily capture that stopped on duplicate provider IDs; preserve its partial originals and commit gate.'};c.s3.put_object(Bucket=c.config['bucket'],Key=BASE+'arxiv-gap-repair.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
'''.replace('BASE',repr(BASE)))['out'])
