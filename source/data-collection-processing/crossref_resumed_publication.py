"""Publish one verified Crossref window without the shared supervisor lock."""
import fcntl,json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from conference_athena import prepare,bridge_resumed
from window_publication import publish_pending

def main():
 with (ROOT/'.conference-athena.lock').open('a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 2
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();bridge_resumed(store,settings)
  with tempfile.TemporaryDirectory(prefix='crossref-publication-')as tmp:result=publish_pending(store,settings,'conferences',load_json(ROOT/'config/conference-athena.json'),prepare,Path(tmp),max_windows=1)
  print(json.dumps(result),flush=True)
  return int(result['status']=='failed')
if __name__=='__main__':raise SystemExit(main())
