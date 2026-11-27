import os,sys,json
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
# This unrelated runtime was included by an over-broad filename match; its
# source was never allowed by the source guard. Restore its disabled flag.
p=Path('/opt/constellation/legacy/constellation-public-cninfo_mainland_china_company_disclosures.service/config/pdf-proxy-fallback.json')
if p.exists():
 c=json.loads(p.read_text());assert 'cninfo_mainland_china_company_disclosures'not in c['allowed_sources'];c['enabled']=False;tmp=p.with_suffix('.scopefix.tmp');tmp.write_text(json.dumps(c,indent=2)+'\n');tmp.replace(p)
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT
from uuid import uuid4
import pdf_proxy_fallback as f
cfg=f.settings();assert cfg['enabled']and len(cfg['allowed_sources'])==12
store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store();key=f.PREFIX+'/cache/nonexistent-permission-check.json';assert store.get(key)is None
receipt=f.PREFIX+'/attempts/permission-check-'+uuid4().hex+'.json';write_json(store,receipt,{'stage':'permission_validation','at':now(),'paid_requests':0,'production_cache_seeded':False});assert store.get(receipt)is not None
from constellation.control import Control
with Control().db()as q:
 q.execute('SELECT source_key,used_requests FROM backfill_quotas WHERE quota_day=UTC_DATE() AND source_key IN (%s,%s)',('decodo_proxy_pdf_requests','decodo_proxy_pdf_reserved_bytes'));quota=q.fetchall()
print(json.dumps({'enabled':cfg['enabled'],'allowed_sources':cfg['allowed_sources'],'shared_quota':quota,'cache_read_permission':True,'audit_write_permission':True,'no_production_cache_seed':True,'unapproved_source_disabled':True}))
