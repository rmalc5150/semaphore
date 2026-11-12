import json
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')))
count=publish(db,source_key='hkex_news');(p/'publication.json').write_text(json.dumps({'source':'hkex_news','verified_published_batches':count},indent=2));print('Verified and published HKEX batches:',count)
