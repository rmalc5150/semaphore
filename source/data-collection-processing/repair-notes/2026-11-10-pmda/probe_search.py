import json,re
from pathlib import Path
from regulatory_collection import EvidenceClient
from collection_storage import StorageSettings
p=Path(__file__).parent;c=EvidenceClient(StorageSettings.load('config/collection-storage.s3.json').store(),'japan_pmda');u='https://www.pmda.go.jp/PmdaSearch/iyakuSearch/';html=c.get(u).decode('utf-8');(p/'search-page.html').write_text(html);print('scripts',re.findall(r'<script[^>]+src=[\"\x27]([^\"\x27]+)',html));print('forms',re.findall(r'<form[^>]+>',html));print('inputs',re.findall(r'<input[^>]+>',html)[:12]);(p/'search-page-evidence.json').write_text(json.dumps(c.evidence,indent=2))
