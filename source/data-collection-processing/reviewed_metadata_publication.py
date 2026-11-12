"""Bounded source-specific publication keeps reviewed queues moving independently."""
import json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
from metadata_engine.reviewed_continuation import SOURCES

def main():
 db=Database(json.loads(Path('config/metadata-engine.json').read_text()));started=time.monotonic()
 for source in SOURCES:
  if time.monotonic()-started>240:break
  try:print(json.dumps({'source':source,'published_batches':publish(db,source_key=source)}),flush=True)
  except Exception as error:print(json.dumps({'source':source,'publication_error':type(error).__name__+': '+str(error)[:200]}),flush=True)
if __name__=='__main__':main()
