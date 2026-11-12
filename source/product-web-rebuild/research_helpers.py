import json
from pathlib import Path
from datetime import datetime,timezone
out=Path(__file__).resolve().parent
cohort=json.loads((out/'cohort.json').read_text())
now=datetime.now(timezone.utc).isoformat()
def ev(url,note):return {'source':'official_company_web_page','reference':url,'observed_at':now,'note':note,'retrieval_method':'assistant_web_browser'}
def p(name,desc,source,life='unknown',roles=['developer'],aliases=[],typ='development_program',sector='biotech',sub='therapeutics',**extra):
 return dict(canonical_name=name,description=desc,sector_id=sector,subsector_id=sub,product_type=typ,lifecycle_status=life,roles=roles,evidence=extra.pop('evidence',[source]),aliases=[dict(alias=a,alias_type='development_code' if any(c.isdigit() for c in a) else 'alternate_name') for a in aliases],**extra)
def company(name,products,evidence,note,status='partial'):
 c=next(c for c in cohort if c['canonical_name']==name)
 return dict(company_id=c['company_id'],products=products,evidence=evidence,status=status,coverage_note=note)
