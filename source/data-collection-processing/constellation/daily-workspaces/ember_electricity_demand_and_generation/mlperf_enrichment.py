"""Commit-pinned MLPerf evidence for result observations; no registry writes."""
import copy
import csv
import hashlib
import io
import json
import re
from pathlib import PurePosixPath
from urllib.parse import quote

from collection_storage import write_checked
from research_contract import ROOT, digest
from regulatory_collection import require, SourceIssue

VERSION = 'mlperf-evidence-v1'
CACHE = ROOT / 'mlperf-evidence-cache'
IDENTITY_FIELDS = ('ID','PrivateID','Location','Model','MlperfModel','UsedModel','Scenario','Category','Division','Suite','System','SystemName','Units')


def validate(repo, commit):
    require(re.fullmatch(r'mlcommons/inference_results_v[0-9]+\.[0-9]+', repo), 'mlperf_untrusted_repository')
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'mlperf_unpinned_commit')


def path_ok(path):
    require(isinstance(path,str) and not path.startswith('/') and '\\' not in path and
            all(x not in {'','..','.'} for x in path.split('/')), 'mlperf_invalid_artifact_path')
    return path


def cached(client, url, blob=None, json_result=False):
    CACHE.mkdir(exist_ok=True)
    key=digest([url,blob]); path=CACHE/(key+'.json')
    if path.exists():
        saved=json.loads(path.read_text()); raw=bytes.fromhex(saved['raw_hex'])
        require(hashlib.sha256(raw).hexdigest()==saved['sha256'], 'mlperf_cache_corrupt')
        if saved['evidence'] not in client.evidence: client.evidence.append(saved['evidence'])
    else:
        start=len(client.evidence)
        raw=client.get(url)
        require(isinstance(raw,bytes), 'mlperf_invalid_response')
        if blob:
            require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
                    'mlperf_artifact_blob_mismatch')
        require(len(client.evidence)>start, 'mlperf_missing_source_evidence')
        saved={'sha256':hashlib.sha256(raw).hexdigest(),'raw_hex':raw.hex(),'evidence':client.evidence[-1]}
        # Atomic immutable cache; duplicate requests are harmless and hash checked.
        import os,tempfile
        fd,tmp=tempfile.mkstemp(dir=CACHE)
        with os.fdopen(fd,'w') as out: json.dump(saved,out)
        os.replace(tmp,path)
    if blob:
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,
                'mlperf_artifact_blob_mismatch')
    return json.loads(raw) if json_result else raw


class Tree:
    def __init__(self, client, repo, commit):
        validate(repo,commit)
        self.client,self.repo,self.commit=client,repo,commit
        self.memo={}
    def read(self, sha, recursive=False):
        url='https://api.github.com/repos/'+self.repo+'/git/trees/'+sha+('?recursive=1' if recursive else '')
        data=cached(self.client,url,json_result=True)
        require(isinstance(data.get('tree'),list) and data.get('sha')==sha or
                (sha==self.commit and isinstance(data.get('tree'),list)), 'mlperf_tree_identity')
        return data
    def directory(self, path):
        path_ok(path)
        if path in self.memo: return self.memo[path]
        current=self.commit
        for part in path.split('/'):
            tree=self.read(current)
            require(tree.get('truncated') is False, 'mlperf_truncated_directory')
            match=next((e for e in tree['tree'] if e['path']==part and e['type']=='tree'),None)
            if match is None: return None
            current=match['sha']
        self.memo[path]=current
        return current
    def files(self, base):
        sha=self.directory(base)
        if sha is None: return []
        def walk(tree_sha,prefix):
            tree=self.read(tree_sha,True)
            if tree.get('truncated') is False:
                return [{**e,'path':prefix+'/'+e['path']} for e in tree['tree'] if e['type']=='blob']
            shallow=self.read(tree_sha)
            require(shallow.get('truncated') is False,'mlperf_truncated_directory')
            out=[]
            for e in shallow['tree']:
                if e['type']=='tree': out.extend(walk(e['sha'],prefix+'/'+e['path']))
                elif e['type']=='blob': out.append({**e,'path':prefix+'/'+e['path']})
            return out
        return walk(sha,base)


def standard_files(client, repo, commit, base, system, location, measurement):
    candidates=[(base+'/systems/'+system+'.json','system_description'),
        (measurement+'/user.conf','measurement_configuration'),
        (measurement+'/mlperf.conf','measurement_configuration'),
        (measurement+'/README.md','measurement_configuration'),
        (location+'/accuracy/accuracy.txt','accuracy_report'),
        (location+'/performance/run_1/mlperf_log_summary.txt','performance_summary')]
    entries=[]
    for path,role in candidates:
        url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+quote(path,safe='/')
        missing=CACHE/(digest([url,'404'])+'.missing')
        if missing.exists(): continue
        try:
            raw=cached(client,url)
        except SourceIssue as exc:
            if exc.code=='source_http_404':
                CACHE.mkdir(exist_ok=True);missing.touch();continue
            raise
        entries.append({'path':path,'sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
                        'size':len(raw),'raw':raw,'identity_basis':'commit_url_and_computed_blob_hash'})
    return entries


def enrich(data, client):
    result=copy.deepcopy(data)
    repo,commit=data['repository'],data['commit'];validate(repo,commit)
    if 'result' not in data:
        result['enrichment']={'version':VERSION,'status':'supporting_artifact_retained',
            'specialist_ready':False,'event_candidate':False,
            'note':'Supporting artifact; correlate to a result before treating as benchmark evidence.'}
        return result
    row=data['result']; location=row.get('Location')
    if not location:
        result['enrichment']={'version':VERSION,'status':'review_required','specialist_ready':False,
            'gaps':['summary_missing_result_location'],'entity_resolution':'pending_rds_match'}
        return result
    location=path_ok(location);parts=location.split('/')
    require(len(parts)>=6 and parts[0] in {'open','closed'} and parts[2]=='results','mlperf_unrecognized_result_location')
    base='/'.join(parts[:2]); system=parts[3]
    trees=Tree(client,repo,commit)
    measurement=location.replace('/results/','/measurements/',1)
    inventory_mode='git_tree'
    try:
        require(not getattr(client,'_mlperf_tree_deferred',False),'mlperf_tree_deferred')
        all_files=trees.files(base+'/systems') + trees.files(measurement) + trees.files(location)
    except SourceIssue as exc:
        if exc.code not in {'github_public_hour_budget','source_http_403','source_http_429','mlperf_tree_deferred'}:
            raise
        client._mlperf_tree_deferred=True
        inventory_mode='standard_paths_api_deferred'
        all_files=standard_files(client,repo,commit,base,system,location,measurement)
    # Restrict evidence to this configuration and workload/scenario, never unrelated vendor results.
    measurement=location.replace('/results/','/measurements/',1)
    selected=[]
    for e in all_files:
        p=e['path']; name=PurePosixPath(p).name.lower()
        role=None
        if p==base+'/systems/'+system+'.json': role='system_description'
        elif p.startswith(measurement+'/') and (name.endswith(('.conf','.json','.md','.txt'))): role='measurement_configuration'
        elif p.startswith(location+'/'):
            if name=='accuracy.txt': role='accuracy_report'
            elif name=='mlperf_log_summary.txt': role='performance_summary'
            elif name=='mlperf_log_detail.txt': role='loadgen_detail'
            elif 'power' in name and name.endswith(('.txt','.json','.csv')): role='power_evidence'
        if role: selected.append((e,role))
    require(len(selected)<=100,'mlperf_artifact_scope_too_large')
    artifacts=[];gaps=[];total=0
    if inventory_mode != 'git_tree':
        gaps.append({'reason':'complete_directory_inventory_deferred','capture':'standard result/configuration paths only'})
    for entry,role in selected:
        path=path_ok(entry['path']);size=entry.get('size',0)
        artifact={'path':path,'role':role,'git_blob_sha':entry['sha'],'bytes':size,
                  'source_url':'https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+quote(path,safe='/'),
                  'identity_basis':entry.get('identity_basis','commit_git_tree_blob')}
        if size>512*1024 or total+size>2*1024*1024:
            artifact['status']='indexed_not_downloaded_size_limit';gaps.append({'path':path,'reason':artifact['status']})
        else:
            raw=entry['raw'] if 'raw' in entry else cached(client,artifact['source_url'],entry['sha'])
            require(len(raw)==size,'mlperf_artifact_size_mismatch')
            total+=len(raw)
            artifact.update(status='captured',sha256=hashlib.sha256(raw).hexdigest(),
                content=json.loads(raw) if path.endswith('.json') else raw.decode('utf-8-sig'))
        if artifact.get('status') == 'captured' and isinstance(artifact.get('content'), str):
            artifact['reported_fields'] = [{'label': m[1].strip(), 'value': m[2].strip()}
                for line in artifact['content'].splitlines()
                if (m := re.match(r'^([^:=]{1,160})\s*[:=]\s*(.{0,2048})$', line))]
        artifacts.append(artifact)
    roles={a['role'] for a in artifacts if a['status']=='captured'}
    for role in ['system_description','measurement_configuration','performance_summary','accuracy_report']:
        if role not in roles: gaps.append({'role':role,'reason':'required_evidence_not_captured'})
    system_data=next((a['content'] for a in artifacts if a['role']=='system_description' and a['status']=='captured'),{})
    candidates=[{'role':role,'name':str(value)} for role,value in [
        ('submitter',row.get('Submitter')),('tested_system',row.get('System') or row.get('SystemName')),
        ('processor',row.get('Processor')),('accelerator',row.get('Accelerator')),
        ('software',row.get('Software')),('model',row.get('UsedModel'))] if value]
    # Exclude daily retrieval time from semantic event/version keys.
    event_key=digest([repo,row.get('ID'),location,row.get('Scenario'),row.get('Suite')])
    content_version=digest([row,[(a['path'],a['git_blob_sha']) for a in artifacts]])
    result['enrichment']={'version':VERSION,'status':'enriched' if not gaps else 'review_required',
        'specialist_ready':all(r in roles for r in ['system_description','performance_summary']),
        'artifact_inventory':inventory_mode,'artifacts':artifacts,'gaps':gaps,'system_description':system_data,'entity_candidates':candidates,
        'entity_resolution':'pending_rds_match','event_candidate':{
            'type':'technology.benchmark_result','key':event_key,'content_version':content_version,
            'review_status':'pending','publication_date':None},
        'comparison_context':{k:row.get(k) for k in ['version','Suite','Category','Model','UsedModel','Scenario','Accuracy',
            'Performance_Result','Performance_Units','Nodes','weight_data_types','has_power','Processor','Accelerator','Software','Platform','Availability']},
        'limitations':['No inferred ownership, adoption, superiority, energy usage, cost or historical availability.',
            'Open division model substitution requires explicit comparability review.',
            'Artifact capture is scoped and size-bounded; gaps are explicit, not complete source-code capture.']}
    return result


def summary_page(client, snapshot, item):
    repo,commit=snapshot['repository'],snapshot['commit'];validate(repo,commit)
    path=path_ok(snapshot['summary_file'])
    url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+path
    raw=cached(client,url,snapshot['summary_blob_sha'])
    rows=json.loads(raw) if path.endswith('.json') else list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    require(isinstance(rows,list) and all(isinstance(r,dict) for r in rows),'mlperf_summary_shape')
    offset=snapshot.get('offset',0);out=[];page_bytes=0
    for row in rows[offset:offset+50]:
        data=enrich({'repository':repo,'commit':commit,'summary_file':path,'result':row,
            'measurement_note':'Source units, accuracy, scenario and power availability retained.'},client)
        identity=repo+':'+digest({k:row.get(k) for k in IDENTITY_FIELDS})
        out.append(item(identity,data,url,basis='derived'))
        page_bytes += len(json.dumps(data).encode())
        if page_bytes >= 8*1024*1024: break
    end=offset+len(out)
    return out,json.dumps({**snapshot,'offset':end}) if end<len(rows) else None
