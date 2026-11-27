"""Validate derived archive lineage against committed parents and original content."""
import json,hashlib
from metadata_engine.evidence import RawFailure,object_bytes,OversizedArtifact

def require(ok,reason):
    if not ok:raise RawFailure(reason)

def evidence(record,s3,bucket):
    p=record.get('payload',{});parent=p.get('data',{});source=parent.get('source')
    require(source in ('people_rss','finlight','marketaux','sec_edgar','hkex_news','disclosure_documents'),'personnel_unknown_parent_source')
    require(record['source_record_id']==p.get('parent_observation_id')==parent.get('observation_id'),'personnel_parent_observation_mismatch')
    require(p.get('parent_record_id')==parent.get('record_id')and record['source_url']==parent.get('source_url'),'personnel_parent_identity_mismatch')
    path=p.get('parent_manifest','');expected='manifests/collection_runs/source='+source+'/dataset='+parent.get('dataset','')+'/'
    require(path.startswith(expected)and path.endswith('/final.json'),'personnel_parent_manifest_invalid')
    # The archive's own committed manifest pins the exact upstream manifest.
    own='research-data/manifests/collection_runs/source=personnel_archive/dataset=people_source_records/'+record['run_id']+'/final.json'
    archive=json.loads(object_bytes(s3,bucket,own));scope=archive['task']['scope']
    require(scope.get('parent_manifest')==path,'personnel_archive_scope_mismatch')
    raw=object_bytes(s3,bucket,'research-data/'+path,expected=scope['parent_manifest_sha256']);manifest=json.loads(raw)
    require(manifest['status']=='complete'and manifest['exhausted'],'personnel_parent_not_complete')
    head=json.loads(object_bytes(s3,bucket,'research-data/checkpoints/'+manifest['task_id']+'/head.json'))
    require(path in head.get('terminal_history',[]),'personnel_parent_not_committed')
    batches={b['key']:b for page in manifest['pages']for b in page['batches']};proof=None
    for key in p.get('parent_batch_keys',[]):
        require(key in batches,'personnel_parent_batch_outside_manifest');batch=batches[key];body=object_bytes(s3,bucket,'research-data/'+key,expected=batch['sha256'])
        matches=[json.loads(line)for line in body.splitlines()if line]
        if any(r==parent for r in matches):
            proof={'artifact_kind':'parent_record','s3_uri':'s3://'+bucket+'/research-data/'+key,'sha256':batch['sha256'],'origin':'first_party_source','representation':'Exact committed upstream collected record; original content evidence separate.'};break
    require(proof is not None,'personnel_parent_record_not_in_committed_batch')
    if source=='people_rss':
        from metadata_engine.people_rss import evidence as rss_evidence
        content=rss_evidence(parent,s3,bucket)
    elif source in ('finlight','marketaux'):
        from metadata_engine.people_rss import evidence as article_evidence
        content=article_evidence(parent,s3,bucket,artifact_source=source)
    else:
        from urllib.parse import urlsplit
        from metadata_engine.evidence import substantive
        allowed={'sec_edgar':{'www.sec.gov'},'hkex_news':{'www1.hkexnews.hk'},'disclosure_documents':{'www.sec.gov','www1.hkexnews.hk'}}[source];content=[]
        for ref in parent.get('payload',{}).get('source_evidence',[]):
            if urlsplit(ref.get('source_url','')).hostname not in allowed:continue
            key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
            try:data=object_bytes(s3,bucket,key,expected=ref['sha256'])
            except OversizedArtifact:
                from metadata_engine.streaming import evidence
                artifact=evidence(parent,ref,{'allowed_hosts':list(allowed)},s3,bucket,'primary_document')
                artifact['artifact_kind']='source_content';content.append(artifact);continue
            try:
                if source=='hkex_news':
                    from hkex_originals import validate_original
                    validate_original(data,ref['source_url'])
                elif substantive(data)not in ('document','full_text'):continue
            except ValueError:continue
            content.append({'artifact_kind':'original_document','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'source_url':ref['source_url'],'origin':'first_party_source'})
    require(content,'personnel_original_source_content_missing')
    chosen=next((a for a in content if a['artifact_kind']=='full_text'),content[-1])
    return [proof,*content,{**chosen,'artifact_kind':'source_content','validation':'Committed upstream identity/manifest/batch and original source content verified; personnel relevance remains candidate-only.'}]
