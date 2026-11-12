"""Validate PMDA designation rows against the original ruled PDF table."""
import hashlib,re
from functools import lru_cache
from urllib.parse import urlsplit
from metadata_engine.evidence import object_bytes,RawFailure
from metadata_engine.pmda_tables import parse_pdf

@lru_cache(maxsize=4)
def parsed_pdf(body):return parse_pdf(body)

def evidence(record,s3,bucket):
    url=record.get('source_url','');u=urlsplit(url)
    if u.scheme!='https'or u.netloc!='www.pmda.go.jp'or u.path!='/files/000235895.pdf'or u.query:raise RawFailure('pmda_untrusted_designation_pdf')
    data=record.get('payload',{}).get('data',{});identity=record.get('source_record_id')
    for ref in record.get('payload',{}).get('source_evidence',[])+record.get('source_evidence',[]):
        if ref.get('source_url')!=url or not ref.get('sha256')or not ref.get('key'):continue
        key=ref['key'];key=key if key.startswith('research-data/')else 'research-data/'+key
        body=object_bytes(s3,bucket,key,expected=ref['sha256'])
        if not body.lstrip().startswith(b'%PDF-')or b'%%EOF'not in body[-4096:]:raise RawFailure('pmda_invalid_original_pdf')
        rows=parsed_pdf(body);matches=[r for r in rows if identity=='sakigake:'+r['designationDate']+':'+r['listNumber']]
        if len(matches)!=1:raise RawFailure('pmda_designation_identity_mismatch')
        row=matches[0]
        # Older captures retained four fields and typographic whitespace. Their
        # original PDF remains full; never promote the legacy flattened fields
        # to parsed holder relationships or a full-drug catalogue.
        if set(data)=={'designationDate','designationDateNative','listNumber','recordText'}:
            equal=all(data[k]==row[k]for k in ('designationDate','designationDateNative','listNumber')) and re.sub(r'\s+','',data['recordText'])==re.sub(r'\s+','',row['recordText'])
            scope='legacy designation text matched to original PDF; role fields not inferred'
        else:equal=data==row;scope='full parsed ruled-table row; no complete medicine-catalogue or historical-vintage inference'
        if not equal:raise RawFailure('pmda_original_designation_row_mismatch')
        return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':{'designation_id':identity,'original_pdf_and_row':True,'scope':scope}}]
    raise RawFailure('pmda_original_designation_pdf_missing')
