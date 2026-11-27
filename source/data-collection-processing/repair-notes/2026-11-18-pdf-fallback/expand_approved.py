import os,json,hashlib
from pathlib import Path
allowed=['biorxiv_medrxiv_preprints','hkex_news','disclosure_documents','usgs_minerals','nist_robotics_methods','europe_pmc_fulltext','uk_mhra','japan_pmda','canada_cda_amc_cadth_reimbursement_reviews','france_has_medicine_assessment_opinions','germany_g_ba_drug_benefit_assessments','iea_pvps_solar_deployment_reports']
base=Path('/opt/constellation/auxiliary-publication/source');helper=(base/'pdf_proxy_fallback.py').read_bytes();cfg=json.loads((base/'config/pdf-proxy-fallback.json').read_text());cfg.update(enabled=True,allowed_sources=allowed)
assert cfg['max_requests_per_day']==4 and cfg['max_pdf_bytes']==8388608
roots=[base,Path('/opt/constellation/capture-workers/source')]
for root in Path('/opt/constellation/legacy').glob('*'):
 name=root.name
 if name in ({'constellation-specialist-'+s+'.service'for s in allowed}|{'constellation-public-'+s+'.service'for s in allowed}|{'constellation-core-hkex-filings-historical.service','constellation-core-uk-historical.service','constellation-core-japan-historical.service','constellation-core-documents-historical.service'}):roots.append(root)
changed=[]
for root in roots:
 if not(root/'regulatory_collection.py').exists():continue
 for name,raw in [('pdf_proxy_fallback.py',helper),('config/pdf-proxy-fallback.json',(json.dumps(cfg,indent=2)+'\n').encode())]:
  target=root/name;old=target.read_bytes()if target.exists()else None
  if old==raw:continue
  if old is not None:
   backup=Path('/opt/constellation/tmp/pdf-fallback-approved-backup')/hashlib.sha256(str(root).encode()).hexdigest()[:12]/name;backup.parent.mkdir(parents=True,exist_ok=True)
   if not backup.exists():backup.write_bytes(old)
  tmp=target.with_suffix('.approved.tmp');tmp.write_bytes(raw);os.chmod(tmp,0o644);tmp.replace(target)
 changed.append(str(root))
print(json.dumps({'enabled_roots':changed,'allowed_sources':allowed,'shared_daily_requests':4,'max_pdf_bytes':8388608,'production_cache_seeded':False}))
