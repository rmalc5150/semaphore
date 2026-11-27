"""Explicit initial scopes for new historical integrations; no network at planning time."""
from datetime import date,timedelta

def scopes(source,start,end,mode):
    if mode not in ('historical','daily'):return
    if source['adapter']=='additional_nhsbsa':
        if mode=='daily':
            yield end-timedelta(days=1),end,{'url':source['api'],'release_selection':'latest_available'},source['coverage_note']
        else:
            current=start.replace(day=1)
            while current<end:
                stop=min(date(current.year+(current.month==12),current.month%12+1,1),end)
                yield current,stop,{'url':source['api'],'period':current.strftime('%Y%m')},source['coverage_note']
                current=stop
        return
    if source['adapter']=='additional_portwatch':
        start=max(start,date(2019,1,1))
        if mode=='daily':end-=timedelta(days=7);start=max(start,end-timedelta(days=7))
        while start<end:
            stop=min(start+timedelta(days=1),end)
            yield start,stop,{'url':source['api'],'data_start':start.isoformat(),'data_end':stop.isoformat()},source['coverage_note']
            start=stop
        return
    if source['adapter']=='additional_unido':
        if mode=='daily':start=max(start,date(end.year-1,1,1))
        for year in range(start.year,end.year+1):
            a=max(start,date(year,1,1));b=min(end,date(year+1,1,1))
            if a>=b:continue
            for dataset in ('IIP','INDSTAT/4'):
                yield a,b,{'url':source['api'],'dataset':dataset,'data_start':a.isoformat(),'data_end':b.isoformat()},source['coverage_note']
        return
    if source['adapter'] in {'additional_'+k for k in ('ember','wto_timeseries','wto_qr','wto_eping','census','usda','comtrade','copernicus')}:
        yield from credential_scopes(source,start,end,mode)
        return
    if mode=='daily':
        if source['adapter']=='additional_nasa':end-=timedelta(days=3)
        start=max(start,end-timedelta(days=7))
    kind=source['adapter'];note=source['coverage_note'];base={'url':source['api']}
    if source.get('raw_content_revision'):base['raw_content_revision']=source['raw_content_revision']
    if kind=='additional_epo':
        if mode=='historical':
            periods=[(date(1900,1,1),date(2016,1,1))]
            periods += [(date(y,1,1),min(date(y+1,1,1),end)) for y in range(2016,end.year+1) if date(y,1,1)<end]
        else:
            periods=[(start,end)]
        for scope in source['scopes']:
            for a,b in periods:
                yield start,end,{**base,**scope,'purpose':'discovery','discovery_start':a.isoformat(),'discovery_end':b.isoformat(),'snapshot_end':end.isoformat()},note
        if mode=='daily':
            for shard in '0123456789abcdef':
                yield start,end,{**base,'purpose':'refresh','shard':shard,'snapshot_end':end.isoformat()},note
    elif kind in ('additional_fred','additional_nasa'):
        for year in range(start.year,end.year+1):
            begin=max(start,date(year,1,1));stop=min(date(year+1,1,1),end)
            if stop<=begin:continue
            for scope in source['scopes']:
                if kind=='additional_fred':
                    # FRED permits at most 2,000 vintage dates per JSON query.
                    # Three-year realtime intervals bound daily series safely.
                    realtime=date(2016,1,1)
                    while realtime<=end:
                        following=min(date(realtime.year+3,1,1),end+timedelta(days=1))
                        yield begin,stop,{**base,**scope,'realtime_start':realtime.isoformat(),'realtime_end':(following-timedelta(days=1)).isoformat()},note
                        realtime=following
                else:yield begin,stop,{**base,**scope,'realtime_end':end.isoformat()},note
    elif kind=='additional_zenodo':
        begin=start
        while begin<end:
            stop=min(begin+timedelta(days=1),end)
            yield begin,stop,base,note
            begin=stop
    elif kind=='additional_huggingface':
        for category in ('models','datasets'):yield start,end,{**base,'category':category},note
    else:
        begin=start
        while begin<end:
            stop=min(date(begin.year+(begin.month==12),begin.month%12+1,1),end)
            if kind=='additional_biorxiv':
                for repository in ('biorxiv','medrxiv'):yield begin,stop,{**base,'repository':repository},note
            elif kind=='additional_datacite':
                for resource in ('dataset','software','dissertation'):yield begin,stop,{**base,'resource':resource},note
            else:yield begin,stop,base,note
            begin=stop

def credential_scopes(source,start,end,mode):
    """Period partitions keep API requests bounded; daily snapshots revisit releases."""
    kind=source['adapter'].removeprefix('additional_');base={'url':source['api']};note=source['coverage_note']
    if mode=='daily':
        if kind=='wto_eping':start=max(start,end-timedelta(days=14))
        elif kind=='copernicus':
            end-=timedelta(days=7);start=max(start,end-timedelta(days=14))
        elif kind in ('wto_timeseries','wto_qr','usda','comtrade'):start=max(start,date(end.year-1,1,1))
        else:start=max(start,date(end.year-2,1,1))
    if kind in ('wto_timeseries','wto_qr','usda','comtrade'):
        for year in range(start.year,end.year+1):
            a=max(start,date(year,1,1));b=min(end,date(year+1,1,1))
            if a>=b:continue
            for scope in source['scopes']:
                if scope.get('no_time_dimension'):continue
                yield a,b,{**base,**scope,'year':year},note
        for scope in source['scopes']:
            if scope.get('no_time_dimension'):yield start,end,{**base,**scope},note+'; this indicator has no time dimension: current snapshot only, no 2016 event date inferred'
    else:
        begin=start.replace(day=1) if kind!='wto_eping' else start
        while begin<end:
            stop=min(date(begin.year+(begin.month==12),begin.month%12+1,1),end)
            for scope in source.get('scopes',[{}]):
                params={**base,**scope}
                if kind=='ember':params['url']=source['api']+'/'+scope['dataset']+'/monthly'
                elif kind=='census':params['url']=source['api']+'/'+scope['direction']+'/hs'
                yield begin,stop,params,note
            begin=stop
