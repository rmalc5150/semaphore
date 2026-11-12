"""Match MHRA designation rows to original official CSV/XLSX attachments."""
import csv,io,hashlib
from datetime import date,datetime
from urllib.parse import urlsplit
from metadata_engine.evidence import object_bytes,RawFailure
from metadata_engine.runtime_db import fingerprint

def clean(value):
    if isinstance(value,(datetime,date)):return value.date().isoformat()if isinstance(value,datetime)else value.isoformat()
    return value.strip()if isinstance(value,str)else value

def rows_from(body,path):
    if path.lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(body),read_only=True,data_only=True)
        try:rows=list(book.active.iter_rows(values_only=True))
        finally:book.close()
        header=next((i for i,r in enumerate(rows)if sum(v is not None for v in r)>=2),None)
        if header is None:raise RawFailure('mhra_header_missing')
        keys=[str(v).strip()if v is not None else f'column_{i+1}'for i,v in enumerate(rows[header])]
        return [{keys[i]:clean(v)for i,v in enumerate(r)if i<len(keys)and v not in (None,'')}for r in rows[header+1:]if any(v not in (None,'')for v in r)]
    try:text=body.decode('utf-8-sig')
    except UnicodeError:text=body.decode('cp1252')
    lines=text.splitlines();header=next((i for i,l in enumerate(lines)if l.lstrip().lower().startswith('product name')),None)
    if header is None:raise RawFailure('mhra_header_missing')
    return [{str(k).strip():clean(v)for k,v in r.items()if k and v not in (None,'')}for r in csv.DictReader(io.StringIO('\n'.join(lines[header:])))]

def evidence(record,s3,bucket):
    if record.get('payload',{}).get('data',{}).get('category')=='medicine_document':return product_evidence(record,s3,bucket)
    data=record.get('payload',{}).get('data',{});url=record.get('source_url','');u=urlsplit(url)
    if not (u.scheme=='https'and u.netloc=='assets.publishing.service.gov.uk'and u.path.lower().endswith(('.csv','.xlsx'))):raise RawFailure('mhra_untrusted_attachment_url')
    category=data.get('category');status=data.get('registerStatus');row=data.get('record')
    if not isinstance(row,dict)or category not in ('orphan','ilap'):raise RawFailure('mhra_unsupported_register_record')
    expired='expired'in u.path.lower()
    expected_status='ilap_list'if category=='ilap'else 'expired_or_removed_orphan_register'if expired else 'current_orphan_register'
    if status is not None and status!=expected_status:raise RawFailure('mhra_register_status_mismatch')
    lower={k.lower().strip(' *'):str(v)for k,v in row.items()};parts=[lower[k]for k in ('designation number','product name','company name')if lower.get(k)]
    identity_category='orphan_expired'if expired and category=='orphan'else category
    suffix=fingerprint([s.casefold()for s in parts])
    allowed={identity_category+':'+suffix}
    legacy_identity=expired and category=='orphan' and status is None
    if legacy_identity:allowed.add('orphan:'+suffix)
    if not parts or record.get('source_record_id')not in allowed:raise RawFailure('mhra_row_identity_mismatch')
    refs=record.get('payload',{}).get('source_evidence',[])+record.get('source_evidence',[])
    for ref in refs:
        if ref.get('source_url')!=url or not ref.get('key')or not ref.get('sha256'):continue
        key=ref['key'];key=key if key.startswith('research-data/')else 'research-data/'+key
        raw=object_bytes(s3,bucket,key,expected=ref['sha256']);rows=rows_from(raw,u.path)
        if row not in rows:raise RawFailure('mhra_original_row_mismatch')
        return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':{'register':expected_status,'matching_original_row':True,'scope':'Full official register row; holder enrichment is separate, not a verified authorisation or complete medicine catalogue.'}}]
    raise RawFailure('mhra_original_attachment_missing')


def product_evidence(record,s3,bucket):
    import json
    data=record.get('payload',{}).get('data',{});document=data.get('catalogue_record',{});url=record.get('source_url','');u=urlsplit(url)
    if u.scheme!='https'or u.netloc!='mhraproducts4853.blob.core.windows.net'or not u.path.startswith('/docs/'):raise RawFailure('mhra_untrusted_document_url')
    if document.get('metadata_storage_path')!=url or record.get('source_record_id')!='product_document:'+hashlib.sha256(url.encode()).hexdigest():raise RawFailure('mhra_product_document_identity_mismatch')
    artifacts=[];refs=record.get('payload',{}).get('source_evidence',[])
    for ref in refs:
        origin=urlsplit(ref.get('source_url',''));key=ref.get('key','');key=key if key.startswith('research-data/')else 'research-data/'+key
        if not ref.get('sha256'):continue
        if origin.netloc=='mhraproducts4853.search.windows.net' and origin.path=='/indexes/products-index/docs':
            raw=object_bytes(s3,bucket,key,expected=ref['sha256'])
            try:response=json.loads(raw)
            except ValueError:raise RawFailure('mhra_catalogue_response_not_json')from None
            if document not in response.get('value',[]):raise RawFailure('mhra_original_catalogue_row_mismatch')
            kind='provider_record'
        elif ref.get('source_url')==url:
            raw=object_bytes(s3,bucket,key,expected=ref['sha256'])
            if hashlib.sha256(raw).hexdigest()!=data.get('document_sha256') or not raw.lstrip().startswith(b'%PDF-')or b'%%EOF'not in raw[-4096:]:raise RawFailure('mhra_document_pdf_mismatch')
            from pypdf import PdfReader
            text='\n'.join(p.extract_text()or ''for p in PdfReader(io.BytesIO(raw)).pages)
            if text!=data.get('text'):raise RawFailure('mhra_document_text_mismatch')
            kind='primary_document'
        else:continue
        artifacts.append({'artifact_kind':kind,'s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(raw),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'document_type':document.get('doc_type'),'scope':'Original public product-information document and exact official catalogue linkage; not current authorisation status or a historical vintage.'}})
    if {a['artifact_kind']for a in artifacts}!={'provider_record','primary_document'}:raise RawFailure('mhra_product_document_originals_missing')
    return artifacts
