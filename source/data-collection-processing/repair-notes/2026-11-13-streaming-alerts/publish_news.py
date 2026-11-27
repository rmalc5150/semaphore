import fcntl,json
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from news_athena import prepare
from window_publication import publish_pending
with (ROOT/'.news-athena.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
 result=publish_pending(settings.store(),settings,'news',load_json(ROOT/'config/news-athena.json'),prepare,ROOT/'news-window-build',1,window_ids={'a4f88981d57caae6d8e1c843afc729a424c2324dcfd125178449f10e8b545964'})
 print(json.dumps(result),flush=True)
 assert result['status']!='failed'
