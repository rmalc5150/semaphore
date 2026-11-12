"""Count-reconciled date-added partitions for NIH's 15,000-record offset cap."""
import json
import time
from datetime import date
from regulatory_collection import require

CAP=15000

def response(client,url,criteria,offset=0,limit=100):
    client.sleep(max(0, 1.0 - (time.monotonic() - client.last_request)))
    data=client.json(url,body={'criteria':criteria,'offset':offset,'limit':limit,'sort_field':'appl_id','sort_order':'asc'})
    rows,total=data.get('results'),data.get('meta',{}).get('total')
    require(isinstance(rows,list) and type(total) is int and total>=0,'nih_response_shape')
    require(len(rows)<=limit and offset+len(rows)<=total and (bool(rows) or offset==total),'nih_missing_page')
    return rows,total

def page(client,job,cursor,item):
    p=job['parameters'];url=p['url'];criteria=p['criteria']
    state=json.loads(cursor) if cursor and cursor.startswith('{') else None
    def wrap(rows):
        return [item(r['appl_id'],r,r.get('project_detail_url') or url,(r.get('project_start_date') or '')[:10] or None) for r in rows]
    if state is None:
        offset=int(cursor or 0)
        require(offset<CAP,'nih_offset_cap_split_scope_required')
        rows,total=response(client,url,criteria,offset)
        if total<=CAP:
            return wrap(rows),str(offset+len(rows)) if offset+len(rows)<total else None
        require(offset==0,'nih_split_requires_fresh_cursor')
        requested=criteria.get('date_added',{})
        start=requested.get('from_date') or '2011-01-01';end=requested.get('to_date') or '2100-12-31'
        def count(a,b):
            return response(client,url,{**criteria,'date_added':{'from_date':a,'to_date':b}},limit=1)[1]
        require(count(start,end)==total,'nih_split_missing_undated_records')
        queue=[(start,end,total)];parts=[];splits=0
        while queue:
            a,b,n=queue.pop()
            if n<=CAP:
                if n:parts.append({'start':a,'end':b,'total':n})
                continue
            splits+=1;require(splits<=64 and a<b,'nih_single_day_result_cap')
            first,last=date.fromisoformat(a),date.fromisoformat(b);mid=first+(last-first)//2
            # NIH date_added uses [from_date, to_date): advancing one day
            # drops the entire split day. Keep adjacent ranges contiguous.
            require(first < mid < last, 'nih_single_day_result_cap')
            mid=mid.isoformat()
            left,right=count(a,mid),count(mid,b)
            require(left+right==n,'nih_split_count_changed')
            queue.extend([(mid,b,right),(a,mid,left)])
        state={'version':1,'parts':sorted(parts,key=lambda r:r['start']),'part':0,'offset':0,'total':total,'seen':[]}
    require(state.get('version')==1,'nih_cursor_version')
    part=state['parts'][state['part']]
    rows,total=response(client,url,{**criteria,'date_added':{'from_date':part['start'],'to_date':part['end']}},state['offset'],500)
    require(total==part['total'],'nih_split_count_changed')
    ids=[str(r['appl_id']) for r in rows]
    require(len(set(ids))==len(ids) and not set(ids).intersection(state['seen']),'nih_duplicate_page_refresh_required')
    state['seen'].extend(ids);state['offset']+=len(rows)
    if state['offset']==total:state['part']+=1;state['offset']=0
    done=state['part']==len(state['parts'])
    if done:require(len(state['seen'])==state['total'],'nih_split_final_count_mismatch')
    return wrap(rows),None if done else json.dumps(state,sort_keys=True)
