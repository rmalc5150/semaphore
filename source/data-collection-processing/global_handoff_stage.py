"""Stage new source bundles and the native FERC archive from a checked handoff."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import boto3

from source_access_archive_import import previous_archives
from temporary_archive_formats import archive_rows, safe_members
from temporary_archive_intake import put_checked, put_json
from temporary_archive_stage import BUCKET, CONTROL, REGION, source_id, staged_key, write_inventory

ROOT='global-data-handoff/data/'
GROUPS={
    'cnmv-legacy':'CNMV-Legacy-2016.zip',
    'cnmv-modern-snapshot':'CNMV-Modern-Register-Snapshot.zip',
    'fca':'FCA-PDMR-Notice-Index.zip',
    'gem-entities':'GEM-Current-Entities.zip',
    'nbim-opening':'NBIM-Opening-2015.zip',
}
FERC='FERC-Official-Q1-2016-Filings.zip'


def record(s3, file, name, size, sha, attachment):
    etag=f'"{sha}"'
    destination=staged_key(name,etag,size)
    put_checked(s3,destination,file,sha,size,'application/zip')
    result=s3.head_object(Bucket=BUCKET,Key=destination,ChecksumMode='ENABLED')
    return {'inbox_key':name,'inbox_etag':etag,'bytes':size,'source':source_id(name),'key':destination,
            'sha256_base64':result['ChecksumSHA256'],'etag':result['ETag'],
            'staged_at':result['LastModified'].isoformat(),'attachment':attachment}


def small(s3, archive, parent, workspace, previous):
    baseline=dict(previous_archives(s3,previous,{'CNMV-Date-Only-Capture.zip'}))
    with ZipFile(io.BytesIO(baseline['CNMV-Date-Only-Capture.zip'])) as earlier:
        ids=sorted({row['registry_number'] for row in csv.DictReader(io.StringIO(
            earlier.read('notifications.csv').decode('utf-8-sig')))})
    members=list(safe_members(archive))
    for group,name in GROUPS.items():
        root=f'{ROOT}{group}/'
        if group in ('cnmv-legacy','gem-entities'):
            manifests=[member for member in members if member.startswith(root) and member.endswith('/manifest.json')]
            if len(manifests)!=1:
                raise ValueError('handoff_group_manifest_ambiguous')
            root=manifests[0].rsplit('/',1)[0]+'/'
        path=workspace/name
        with ZipFile(path,'w') as bundle:
            for member in sorted(n for n in members if n.startswith(root)):
                relative=member.removeprefix(root)
                bundle.writestr(ZipInfo(relative),archive.read(member),compress_type=ZIP_DEFLATED)
            if group=='cnmv-modern-snapshot':
                bundle.writestr(ZipInfo('prior-registration-ids.json'),json.dumps(ids).encode(),compress_type=ZIP_DEFLATED)
        count=sum(1 for _ in archive_rows(path,source_id(name),name))
        if not count:
            raise ValueError('handoff_source_has_no_rows:'+group)
        with path.open('rb') as body:
            sha=hashlib.file_digest(body,'sha256').hexdigest()
            body.seek(0)
            yield record(s3,body,name,path.stat().st_size,sha,parent)
        print(json.dumps({'bundle':name,'validated_rows':count}),flush=True)


def ferc(s3, archive, parent):
    prefix=ROOT+'ferc/'
    original=archive.getinfo(prefix+'CSV_2016_Q1.zip')
    evidence,=json.loads(archive.read(prefix+'download-manifest.json'))
    if original.file_size!=evidence['bytes']:
        raise ValueError('ferc_handoff_archive_size_mismatch')
    evidence_key=f"{CONTROL}/handoff-provenance/{parent['sha256']}/ferc.json"
    put_json(s3,evidence_key,{
        'archive':evidence,'required_members':json.loads(archive.read(prefix+'filing-member-index.json')),
        'expected_counts':json.loads(archive.read(prefix+'content-validation.json'))['filing_csv_counts'],
    })
    with archive.open(original) as body:
        if hashlib.file_digest(body,'sha256').hexdigest()!=evidence['sha256']:
            raise ValueError('ferc_handoff_archive_digest_mismatch')
        body.seek(0)
        item=record(s3,body,FERC,original.file_size,evidence['sha256'],parent)
    return {'original':item,'provenance_key':evidence_key}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path)
    p.add_argument('phase',choices=('small','ferc'))
    p.add_argument('--checked-originals',type=Path,required=True)
    p.add_argument('--workspace',type=Path,default=Path('/tmp/optima-global-handoff'))
    p.add_argument('--previous')
    args=p.parse_args()
    args.workspace.mkdir(parents=True,exist_ok=True)
    references=json.loads(args.checked_originals.read_text())
    parent=references['full-handoff' if args.phase=='ferc' else 'project-handoff']
    s3=boto3.client('s3',region_name=REGION)
    with ZipFile(args.archive) as archive:
        if args.phase=='small':
            inventory,sha=write_inventory(s3,list(small(s3,archive,parent,args.workspace,args.previous)),[])
            result={'inventory':inventory,'sha256':sha}
        else:
            result=ferc(s3,archive,parent)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
