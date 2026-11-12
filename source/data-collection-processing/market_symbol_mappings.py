"""Reviewed, date-bounded provider aliases; never cross exchange listings."""
from datetime import date
import hashlib,json
from research_contract import digest

def validate(d, symbol, listing_ids):
    if d['symbol'] != symbol or sorted(d['listing_ids']) != sorted(listing_ids):
        raise ValueError('Market mapping listing mismatch')
    if d['target_symbol'] == symbol or d['target_symbol'].rsplit('.',1)[-1] != symbol.rsplit('.',1)[-1]:
        raise ValueError('Market mapping must retain exchange')
    date.fromisoformat(d['start'])
    if d.get('end_exclusive') and date.fromisoformat(d['end_exclusive']) <= date.fromisoformat(d['start']):
        raise ValueError('Invalid mapping dates')
    if not d.get('evidence') or not d.get('reviewer') or not d.get('explanation'):
        raise ValueError('Market mapping needs reviewed evidence')

def load(store,prefix,listings):
    obj=store.get(prefix+'/symbol-mappings.json')
    if not obj:return {}
    doc=json.loads(obj.body)
    if doc.get('schema_version')!=1 or doc.get('stream_id')!=prefix.rsplit('/',1)[-1]:
        raise ValueError('Market mapping stream mismatch')
    out={}
    for entry in doc['decisions']:
        if entry['status']!='active':continue
        d=entry['decision'];validate(d,d['symbol'],listings.get(d['symbol'],[]))
        if d['symbol'] in out:raise ValueError('Overlapping market mappings')
        for proof in d['evidence']:
            saved=store.get(proof['key'])
            if not saved or hashlib.sha256(saved.body).hexdigest()!=proof['sha256']:
                raise ValueError('Market mapping evidence mismatch')
        out[d['symbol']]=d
    return out

def segments(symbol,start,end,decision):
    if not decision:return [(symbol,start,end)]
    boundary=date.fromisoformat(decision['start'])
    until=date.fromisoformat(decision['end_exclusive']) if decision.get('end_exclusive') else end
    cuts=sorted({start,end,*[v for v in (boundary,until) if start<v<end]})
    return [(decision['target_symbol'] if boundary<=a<until else symbol,a,b)for a,b in zip(cuts,cuts[1:])]
