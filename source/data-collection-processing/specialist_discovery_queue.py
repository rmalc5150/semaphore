"""Bound specialist child-queue planning while retaining every pending input."""
import json
from research_contract import digest

def discover(store,settings,state,prefixes,mode,lane,universe_hash,version,limit=100,capacity=128):
    pending=state.setdefault('discovered_pending',{})
    cursors=state.setdefault('discovery_cursors',{})
    for key,job in list(pending.items()):
        identity=digest({'job':job,'universe_hash':universe_hash,'version':version})
        if state.get('jobs',{}).get(identity,{}).get('status')in ('complete','accepted_unavailable'):
            del pending[key]
    remaining=limit
    for prefix in dict.fromkeys(prefixes):
        if remaining<=0 or len(pending)>=capacity:break
        after=cursors.get(prefix,'')
        if hasattr(store,'client'):
            base=settings.s3_prefix.strip('/')+'/'if settings.s3_prefix.strip('/')else''
            args={'Bucket':settings.s3_bucket,'Prefix':base+prefix,'MaxKeys':min(remaining,capacity-len(pending))}
            if after:args['StartAfter']=base+after
            page=store.client.list_objects_v2(**args)
            keys=[r['Key'][len(base):]for r in page.get('Contents',[])]
            more=bool(page.get('IsTruncated'))
        else:
            from window_publication import list_keys
            available=sorted(k for k in list_keys(store,settings,prefix)if k>after)
            keys=available[:min(remaining,capacity-len(pending))];more=len(available)>len(keys)
        processed=0
        for key in keys:
            if remaining<=0 or len(pending)>=capacity:break
            raw=store.get(key)
            if raw is None:raise ValueError('Specialist discovery object disappeared: '+key)
            job=json.loads(raw.body);processed+=1;remaining-=1;cursors[prefix]=key
            if job['mode']==mode and job.get('execution_lane','default')==lane:
                pending[key]=job
        if processed==len(keys)and not more:cursors[prefix]=''
    return list(pending.values())
