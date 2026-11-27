"""Run after the Web Data API Bearer secret ARN is configured; one paid request."""
import json
from pathlib import Path
from decodo_web_data import capture
from collection_storage import StorageSettings,now
from regulatory_collection import EvidenceClient
from research_contract import ROOT
p=Path(__file__).parent
cfg=StorageSettings.load(ROOT/'config/collection-storage.s3.json');client=EvidenceClient(cfg.store(),'biorxiv_medrxiv_preprints')
doi='10.64898/2026.05.07.26352693';url='https://www.medrxiv.org/content/'+doi+'v2.full.pdf'
from regulatory_collection import SourceIssue
try:raw,proof=capture(client,url,doi,probe=True)
except SourceIssue as exc:
 result={'at':now(),'status':'failed','reason':exc.code,'diagnostics':exc.diagnostics,'source_evidence':client.evidence}
 (p/'pilot-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));raise SystemExit(1)
result={'at':now(),'status':'pdf_verified','url':url,'validation':proof,'source_evidence':client.evidence,
        'scope':'one PDF pilot; not full source history or Athena publication'}
(p/'pilot-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
