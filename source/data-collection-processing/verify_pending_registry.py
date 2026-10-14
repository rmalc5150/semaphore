#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
ROOT=Path(__file__).resolve().parent
u=json.loads((ROOT/'config/company-universe.v0.4.json').read_text());companies={c['company_id']:c for c in u['companies']}
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store();client=EvidenceClient(store,'company_registry_review');rows=[]
for e in u['external_identifiers']:
 if e['entity_id'] not in companies or companies[e['entity_id']]['review_status']!='pending' or e['system'] not in {'lei','cik'}:continue
 c=companies[e['entity_id']];url='https://api.gleif.org/api/v1/lei-records/'+e['value'] if e['system']=='lei' else 'https://data.sec.gov/submissions/CIK'+e['value'].zfill(10)+'.json'
 row={'company_id':c['company_id'],'candidate_name':c['canonical_name'],'system':e['system'],'identifier':e['value'],'source_url':url,'checked_at':datetime.now(timezone.utc).isoformat()}
 try:
  raw=client.get(url);d=json.loads(raw)
  if e['system']=='lei':
   a=d['data']['attributes'];entity=a['entity'];row.update(registry_name=entity['legalName']['name'],entity_status=entity.get('status'),registration_status=a.get('registration',{}).get('status'),country=entity.get('legalAddress',{}).get('country'),other_names=entity.get('otherNames',[]))
  else:row.update(registry_name=d.get('name'),former_names=d.get('formerNames',[]),tickers=d.get('tickers',[]))
  row.update(status='source_verified_identity_adjudication_required',sha256=hashlib.sha256(raw).hexdigest(),source_evidence=client.evidence[-1:])
 except Exception as exc:row.update(status='access_failed',error_type=type(exc).__name__)
 rows.append(row);(ROOT/'reports/pending-company-registry-refresh.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k not in ['source_evidence','former_names','other_names','tickers']}),flush=True)
