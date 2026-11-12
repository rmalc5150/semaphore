import json
from pathlib import Path
from research_helpers import ev
cid='cmp_275a6203-11da-4fc8-87f6-e5efd6d5faba'; src='https://www.3i.com/about-us/'
m={'batch_id':'batch-0444','companies':[{'company_id':cid,'products':[],'evidence':[ev(src,'Official 3i page describes 3i as a private-equity and infrastructure investment company; it does not identify products developed or sold by 3i.')],'status':'complete','coverage_note':'No qualifying company-owned products identified. 3i is an investment manager; portfolio-company products are not attributed to 3i itself.'}]}
Path('/home/ec2-user/product-web-rebuild/batch-0444.json').write_text(json.dumps(m,indent=2))
