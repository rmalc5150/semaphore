"""Expand HKEX language notices into separately identified original filings."""
from datetime import datetime, timezone
import hashlib
import copy
import json
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

from collection_storage import S3Store, write_checked, write_json
from hkex_originals import API, OriginalError, document_url, language_notice, original_record, resolve_notice
from metadata_engine.sec_documents import NoRedirect


class ResolutionStore(S3Store):
    def get(self, key):
        from botocore.exceptions import ClientError
        try:
            return super().get(key)
        except ClientError as error:
            if error.response['Error']['Code'] not in ('AccessDenied','403') or not key.startswith('checkpoints/task_hkex_originals/'):
                raise
            args = self._args(key)
            page = self.client.list_objects_v2(Bucket=args['Bucket'],Prefix=args['Key'],MaxKeys=1)
            if not any(r['Key'] == args['Key'] for r in page.get('Contents',[])):
                return None
            raise


class Client:
    def __init__(self, s3, bucket, max_requests=30):
        self.store = ResolutionStore(bucket, 'research-data', client=s3)
        self.evidence = []; self.requests = 0; self.max_requests = max_requests; self.last_request = 0
    def get(self, url):
        original = urlsplit(url).path != urlsplit(API).path
        pointer = 'checkpoints/task_hkex_originals/url-cache/' + hashlib.sha256(url.encode()).hexdigest() + '.json'
        if original:
            document_url(url)
            saved = self.store.get(pointer)
            if saved:
                ref = json.loads(saved.body)
                if ref.get('source_url') != url: raise OriginalError('hkex_cached_url_identity_mismatch')
                cached = self.store.get(ref['key'])
                if cached is None or hashlib.sha256(cached.body).hexdigest() != ref['sha256']:
                    raise OriginalError('hkex_cached_original_checksum_mismatch')
                self.evidence.append(ref)
                return cached.body
        elif not url.startswith(API+'?'):
            raise OriginalError('hkex_untrusted_listing_url')
        if self.requests >= self.max_requests:
            raise TimeoutError('hkex_original_request_budget; saved resolutions resume next attempt')
        time.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic(); self.requests += 1
        try:
            with build_opener(NoRedirect()).open(Request(url, headers={
                'User-Agent':'Optima Holdings metadata-engine/2.0 support@optima-holdings.com',
                'Accept-Encoding':'identity'}), timeout=30) as response:
                if response.status != 200: raise OriginalError('hkex_original_http_'+str(response.status))
                body = response.read(32*1024*1024+1)
                if len(body) > 32*1024*1024: raise OriginalError('hkex_original_oversize')
                length = response.headers.get('Content-Length')
                if length is not None and int(length) != len(body): raise OriginalError('hkex_original_truncated_response')
                media = response.headers.get('Content-Type','application/octet-stream')
        except HTTPError as exc:
            if exc.code in (429,500,502,503,504): raise TimeoutError('hkex_original_http_'+str(exc.code)) from None
            raise OriginalError('hkex_original_http_'+str(exc.code)) from None
        except (URLError,TimeoutError) as exc:
            raise TimeoutError('hkex_original_transport_retry') from exc
        sha = hashlib.sha256(body).hexdigest(); key = 'source_documents/hkex_news/'+sha
        write_checked(self.store,key,body,content_type=media)
        ref = {'key':key,'sha256':sha,'source_url':url,
            'retrieved_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
        self.evidence.append(ref)
        if original: write_json(self.store,pointer,ref)
        return body
    def json(self,url,params):
        return json.loads(self.get(url+'?'+urlencode(params)))


def expand(record, client, s3, bucket):
    """Return (record, optional native-provider envelope) pairs and gap receipt."""
    refs = record.get('payload',{}).get('source_evidence',[])
    primary = next((r for r in refs if r.get('source_url') == record['source_url']),None)
    from metadata_engine.evidence import object_bytes,OversizedArtifact
    if primary is None:
        # Earlier metadata-only captures can be repaired by retrieving the exact
        # original URL already identified by their official HKEX listing.
        document_url(record['source_url'])
        raw = client.get(record['source_url'])
        record = copy.deepcopy(record)
        record['payload']['source_evidence'] = refs + [copy.deepcopy(client.evidence[-1])]
        record['payload']['document_capture'] = {'status':'captured', 'bytes':len(raw),
            'source_evidence':[copy.deepcopy(client.evidence[-1])],
            'recovered_after_metadata_capture':True}
    else:
        key = primary['key']
        if not key.startswith('research-data/'):key='research-data/'+key
        try:raw = object_bytes(s3,bucket,key,expected=primary['sha256'])
        except OversizedArtifact:
            from metadata_engine.streaming import evidence
            artifact=evidence(record,primary,{'allowed_hosts':['www1.hkexnews.hk']},s3,bucket,'primary_document')
            if artifact['validation']['format']!='pdf':raise OriginalError('hkex_large_office_validator_required')
            return [(record,None)],None
    if not language_notice(raw):
        return [(record,None)], None
    receipt = resolve_notice(record,raw,client)
    records = []
    for entry in receipt['originals']:
        proof=entry['listing_evidence'][0]; key=proof['key']
        if not key.startswith('research-data/'):key='research-data/'+key
        envelope={'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,
            'sha256':proof['sha256'],'origin':'first_party_source',
            'representation':'Original HKEX Chinese listing response; exact Chinese NEWS_ID retained.'}
        records.append((original_record(record,entry,receipt),envelope))
    gap={'notice_record_id':receipt['notice_record_id'],'english_version_status':receipt['english_version_status'],
        'resolution_id':receipt['resolution_id'],'original_record_ids':[str(e['row']['NEWS_ID'])for e in receipt['originals']],
        'relation':receipt['relation']}
    return records,gap
