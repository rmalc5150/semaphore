"""Discover future pipeline workers and verify explicitly registered output receipts."""
from fnmatch import fnmatch

def inspect_stages(registry, units, inspect_unit, read_receipt, verify_artifact):
    stages={}
    for name, config in registry['stages'].items():
        matches=sorted(u for u in units if any(fnmatch(u,p) for p in config['unit_patterns']))
        jobs={u:inspect_unit(u) for u in matches}
        receipts=[]
        for key in config.get('receipt_keys',[]):
            try:
                doc=read_receipt(key)
                if not doc or doc.get('status')!='verified' or not doc.get('artifacts'):
                    raise ValueError('Verified output receipt with artifact references is missing')
                for artifact in doc['artifacts']:verify_artifact(artifact)
                receipts.append({'key':key,'status':'verified','verified_at':doc.get('verified_at'),
                                 'metrics':doc.get('metrics',{}),'validation':doc.get('validation',{}),
                                 'artifacts':doc['artifacts']})
            except Exception as exc:receipts.append({'key':key,'status':'verification_failed','error':str(exc)[:500]})
        stages[name]={'label':config['label'],'jobs':jobs,'receipts':receipts,
            'status':'awaiting_setup' if not matches and not receipts else
                ('verification_failed' if any(r['status']!='verified' for r in receipts) or any(j.get('inspection_error') or j.get('issues') for j in jobs.values()) else
                 ('outputs_verified' if receipts else 'awaiting_artifact_registration'))}
    return stages
