#!/usr/bin/env python3
import json
from pathlib import Path
from collection_storage import StorageSettings
import company_universe_athena as curator
import sec_athena_pilot
from research_contract import load_json
ROOT=Path(__file__).resolve().parent
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store()
root=curator.prepare(s,load_json(ROOT/'config/company-universe-athena.json'),ROOT/'config/company-universe.v0.4.json',ROOT/'config/sectors.v1.json',ROOT/'reports/company-universe-v0.4-coverage.json',ROOT/'reports/private-company-candidates-2026-09-25.json',ROOT/'config/company-id-registry.v0.4.json',ROOT/'reports/company-registry-verification-2026-09-22.json',ROOT/'company-universe-build',extra_artifacts=(ROOT/'config/company-admission-policy.json',ROOT/'reports/company-universe-v0.4-review.json',ROOT/'reports/company-source-review/captures.json'),admission_path=ROOT/'config/company-admission-ledger.v1.json')
curator.publish(store,s,root)
sec_athena_pilot.deploy(store,s,root,update_existing=True)
verification=json.loads((root/'athena-verification.json').read_text())
(ROOT/'reports/company-universe-v0.4-publication.json').write_text(json.dumps({'release_directory':str(root),'verification':verification},indent=2)+'\n')
print(json.dumps({'release_directory':str(root),'status':'verified'}),flush=True)
