"""Run a bounded metadata publication pass on m7."""
import json
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish

if __name__=='__main__':
    db=Database(json.loads((Path(__file__).parent/'config/metadata-engine.json').read_text()))
    print(json.dumps({'published_batches':publish(db)}),flush=True)
