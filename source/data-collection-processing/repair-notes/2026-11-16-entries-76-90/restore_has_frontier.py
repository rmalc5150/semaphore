from ops import *
print(remote(T3,r'''import json,time
from research_contract import ROOT,load_json
import public_source_capture as pc
from constellation.control import Control
from constellation.historical_guard import dispatch_guard
from constellation.legacy_routes import manifest,specification
s=pc.boto3.client('s3',region_name='us-east-1');source='france_has_medicine_assessment_opinions';row=next(r for r in load_json(ROOT/'config/constellation-public-sources.json')['sources']if r['source']==source);key=pc.PREFIX+'/objects/'+source+'/cb06f6b3afb01b50de283e6718a67bb3bf5c0c3d80c708b66eed459fd7b84161';body=s.get_object(Bucket=pc.BUCKET,Key=key)['Body'].read();url='https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028-081531/url-has-20261028.csv';links=pc.discover(body,url,row,1);assert len(links)>1000;out={}
for mode in ('historical','daily'):
 statekey=pc.PREFIX+'/states/'+mode+'/'+source+'/'+row['raw_content_revision']+'.json';state,token=pc.read_json(s,statekey);assert state
 s.put_object(Bucket=pc.BUCKET,Key=BASE+'has-frontier-before-'+mode+'.json',Body=pc.encode(state),ServerSideEncryption='AES256')
 known=set(state['done'])|{r['url']for r in state['frontier']};added=0
 for link in links:
  if link['url']not in known and len(known)<5000:state['frontier'].append(link);known.add(link['url']);added+=1
 state['reviewed_link_export']={'source_url':url,'s3_uri':'s3://'+pc.BUCKET+'/'+key,'provider_links':len(links),'frontier_cap':5000,'note':'Provider export order retained; bounded frontier, not exhaustive historical coverage.'};pc.put(s,statekey,pc.encode(state),IfMatch=token);out[mode]={'links_discovered':len(links),'added':added,'frontier':len(state['frontier'])}
c=Control();route=next(r for r in manifest()['routes']if r['unit']=='constellation-public-'+source+'.service')
with dispatch_guard(c)as acquired:
 if not acquired:out['dispatch']='guard_busy; existing source queue left intact'
 else:
  assert c.allowed()
  with c.db()as q:q.execute("SELECT job_id,status FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') LIMIT 1",('legacy:'+route['unit'],));pending=q.fetchone()
  out['dispatch']={'retained':pending}if pending else {'registered':c.register(specification(route,'native-link-export-review-'+str(int(time.time()))))}
s.put_object(Bucket=pc.BUCKET,Key=BASE+'has-frontier-repair.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
'''.replace('BASE',repr(BASE)))['out'])
