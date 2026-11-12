"""Read all named Constellation products without the retired tracking database."""
import json,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database

def read_products():
    config=json.loads((Path(__file__).resolve().parent/'config/metadata-engine.json').read_text());db=Database(config)
    # Names and product lifecycle states are evidence assertions, not legal identity.
    # One deterministic primary search name, with all other names retained as aliases.
    with db.tx()as c:
        c.execute("""SELECT HEX(e.entity_id) entity_hex,n.name_original,n.name_kind,n.review_status,n.known_at
          FROM entities e JOIN entity_names n USING(entity_id)
          WHERE e.entity_type='product' AND e.lifecycle_status IN ('active','provisional')
            AND n.review_status<>'rejected' AND (n.valid_to IS NULL OR n.valid_to>UTC_TIMESTAMP(6))
          ORDER BY e.entity_id,(n.review_status='verified') DESC,
                   (n.name_kind='canonical') DESC,n.known_at DESC,n.name_original,n.name_id""")
        rows=c.fetchall()
    products={};aliases=[]
    for r in rows:
        identity=str(uuid.UUID(hex=r['entity_hex']));name=r['name_original'].strip()
        if not name:continue
        if identity not in products:
            products[identity]={'product_id':identity,'canonical_name':name,'sector_id':None,
                'review_status':'verified' if r['review_status']=='verified' else 'pending',
                'row_version':None,'entity_id':identity,'name_kind':r['name_kind']}
        elif name!=products[identity]['canonical_name']:
            aliases.append({'product_id':identity,'alias':name,'review_status':r['review_status']})
    return {'products':list(products.values()),'aliases':aliases,'companies':[],
            'identity_scope':'All named Constellation product entities, including provisional; no fuzzy merges or inferred ownership/sector.'}
