"""Small resumable CDS reanalysis downloads; credentials never enter evidence."""
import hashlib,json,re,time
from urllib.parse import urlsplit
import requests
from additional_source_apis import credentials,row
from regulatory_collection import require,SourceIssue
from research_contract import digest

API='https://cds.climate.copernicus.eu/api/retrieve/v1'

def call(client,method,url,body=None):
    u=urlsplit(url);require(u.scheme=='https' and u.hostname=='cds.climate.copernicus.eu' and u.path.startswith('/api/retrieve/v1/'),'copernicus_unreviewed_url')
    token=credentials().get('copernicus','').strip();require(bool(token),'additional_key_missing')
    from constellation.shared_limits import admit
    admit(url)
    try:
        r=requests.request(method,url,headers={'PRIVATE-TOKEN':token},json=body,timeout=(10,30),allow_redirects=False)
        require(len(r.content)<=2*1024**2,'copernicus_metadata_too_large')
        safe=r.content.replace(token.encode(),b'[REDACTED]')
        if '/results' in url and r.status_code==200:
            document=json.loads(safe)
            asset=document.get('asset',{}).get('value',{})
            if asset.get('href'):asset['href']=urlsplit(asset['href'])._replace(query='',fragment='').geturl()
            safe=json.dumps(document).encode()
        client.save(safe,url,'application/json')
        require(r.status_code in (200,201,202),'source_http_'+str(r.status_code))
        return r.json()
    except SourceIssue:raise
    except Exception:raise SourceIssue('copernicus_request_failed',True) from None

def fetch(client,job,cursor,item):
    from datetime import date,timedelta
    p=job['parameters'];start=p.get('data_start',job['start']);end=p.get('data_end',job['end']);state=json.loads(cursor) if cursor else {}
    days=[];day=date.fromisoformat(start)
    while day<date.fromisoformat(end):days.append(day.strftime('%d'));day+=timedelta(days=1)
    request={'variable':['2m_temperature','total_precipitation'],'year':[start[:4]],'month':[start[5:7]],'day':days,'time':[f'{h:02d}:00' for h in range(24)],'area':p['area'],'data_format':'netcdf','download_format':'unarchived'}
    if p['dataset']=='reanalysis-era5-single-levels':request['product_type']=['reanalysis']
    # Persist submitted job identity independently of page commits for crash recovery.
    key='constellation-backfill/copernicus/submissions/'+digest({'dataset':p['dataset'],'request':request})+'.json'
    saved=client.store.get(key)
    if saved:state=json.loads(saved.body)
    if not state.get('job_id'):
        # Single source invocation per mode; shared lock bounds concurrent submissions.
        from constellation.control import Control
        control=Control()
        with control.db() as db:
            db.execute("SELECT GET_LOCK('constellation:copernicus-submit',0) AS acquired");held=db.fetchone()['acquired']
            if not held:raise SourceIssue('copernicus_queue_wait',True)
            try:
                active=call(client,'GET',API+'/jobs?limit=100')['jobs']
                require(sum(r.get('status') in ('accepted','running') for r in active)<2,'copernicus_queue_wait')
                d=call(client,'POST',API+'/processes/'+p['dataset']+'/execution',{'inputs':request});identity=d.get('jobID')
                if not identity:
                    link=next((r['href'] for r in d.get('links',[]) if r.get('rel')=='monitor'),'');identity=link.rsplit('/',1)[-1]
                require(bool(re.fullmatch(r'[A-Za-z0-9-]+',identity or '')),'copernicus_job_id_missing')
                state={'job_id':identity}
                from collection_storage import write_json
                write_json(client.store,key,state)
            finally:db.execute("SELECT RELEASE_LOCK('constellation:copernicus-submit')")
    identity=state['job_id'];require(bool(re.fullmatch(r'[A-Za-z0-9-]+',identity)),'copernicus_invalid_job_id')
    status=call(client,'GET',API+'/jobs/'+identity).get('status')
    if status in ('accepted','running'):
        # A changing poll counter is an operational cursor, never a data row.
        return [],json.dumps({'job_id':identity,'poll':(json.loads(cursor).get('poll',0) if cursor else 0)+1})
    require(status=='successful','copernicus_job_'+str(status))
    result=call(client,'GET',API+'/jobs/'+identity+'/results');asset=result.get('asset',{}).get('value',{});url=asset.get('href','');u=urlsplit(url)
    require(u.scheme=='https' and u.hostname and (u.hostname.endswith('.ecmwf.int') or u.hostname.endswith('.climate.copernicus.eu')) and not u.username and not u.password,'copernicus_unreviewed_download')
    expected=int(asset['file:size']);require(0<expected<=16*1024**2,'copernicus_download_too_large_split_scope')
    try:
        # Signed provider URLs are used only in memory; saved provenance omits query.
        with requests.get(url,stream=True,timeout=(10,60),allow_redirects=False) as r:
            require(r.status_code==200,'source_http_'+str(r.status_code));chunks=[];size=0
            for chunk in r.iter_content(65536):size+=len(chunk);require(size<=expected,'copernicus_download_size_mismatch');chunks.append(chunk)
        body=b''.join(chunks);require(len(body)==expected,'copernicus_download_truncated')
        require(body.startswith((b'CDF',b'\x89HDF',b'PK\x03\x04')),'copernicus_not_netcdf')
        public_url=u._replace(query='',fragment='').geturl();client.save(body,public_url,asset.get('type','application/octet-stream'))
    except SourceIssue:raise
    except Exception:raise SourceIssue('copernicus_download_failed',True) from None
    payload={'dataset':p['dataset'],'reference_location':p['location'],'request':request,'request_id':identity,'artifact_sha256':hashlib.sha256(body).hexdigest(),'artifact_bytes':len(body),'data_start':start,'data_end_exclusive':end,'structured_weather_extraction':'pending; raw NetCDF captured','vintage_basis':'current reanalysis; not original historical forecasts'}
    return [row(item,digest(payload),payload,'https://cds.climate.copernicus.eu/datasets/'+p['dataset'],None)],None
