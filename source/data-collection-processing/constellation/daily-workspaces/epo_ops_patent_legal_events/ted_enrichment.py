"""Evidence-preserving TED legacy/eForms XML enrichment; no company resolution."""
import copy
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
import xml.etree.ElementTree as ET
from fda_access import NoRedirect
from regulatory_collection import require, SourceIssue

VERSION = 'ted-xml-v1'

def local(tag):
    return tag.rsplit('}', 1)[-1]

def parse_xml(raw, identity):
    require(raw and len(raw) <= 16 * 1024 * 1024, 'ted_empty_or_oversize_xml')
    require(not re.search(br'<!\s*(DOCTYPE|ENTITY)', raw, re.I), 'ted_xml_entities_rejected')
    root = ET.fromstring(raw)
    require(local(root.tag) in {'TED_EXPORT', 'ContractNotice', 'ContractAwardNotice', 'PriorInformationNotice', 'ChangeNotice'}, 'ted_unrecognized_xml_root')
    # Require the provider publication number, not an incidental reference in prose.
    identifiers = [(e.text or '').strip() for e in root.iter() if local(e.tag) in {'NO_DOC_OJS', 'ND', 'NoticePublicationID', 'PublicationID'}]
    def canonical(x):
        legacy = re.fullmatch(r'(\d{4})/S\s+\d+-(\d+)', x)
        if legacy:
            x = legacy[2] + '-' + legacy[1]
        return re.sub(r'^0+(?=\d)', '', x)
    require(any(canonical(x) == canonical(identity) for x in identifiers), 'ted_xml_notice_identity_mismatch')
    def node(e):
        return {'tag': e.tag, 'attributes': dict(e.attrib), 'text': e.text,
                'tail': e.tail, 'children': [node(c) for c in e]}
    fields = []
    def walk(e, path):
        path = path + '/' + local(e.tag)
        if e.text and e.text.strip() or e.attrib:
            fields.append({'path': path, 'value': (e.text or '').strip(), 'attributes': dict(e.attrib)})
        for c in e:
            walk(c, path)
    walk(root, '')
    form_tags = {local(e.tag) for e in root.iter()}
    stage = {'ContractNotice':'competition', 'ContractAwardNotice':'award_notice',
             'PriorInformationNotice':'planning', 'ChangeNotice':'change_notice'}.get(local(root.tag), 'unknown')
    forms = [e for e in root.iter() if re.fullmatch(r'F\d{2}(?:_\d{4})?', local(e.tag))]
    form_names = sorted({local(e.tag) for e in forms})
    legacy = {'01':'planning','02':'competition','03':'award_notice','04':'planning',
              '05':'competition','06':'award_notice','14':'correction','15':'direct_award_intent','20':'contract_modification',
              '21':'mixed_notice_type','22':'mixed_notice_type','23':'mixed_notice_type','24':'competition','25':'award_notice'}
    stages = {legacy.get(local(e.tag)[1:3], 'unknown') for e in forms}
    if len(stages) == 1:
        stage = stages.pop()
    if 'mixed_notice_type' in stages or stage == 'mixed_notice_type':
        stage = 'unknown'
    # Keep context paths and attributes so lot values, currencies, roles and dates stay associated.
    select = lambda names: [f for f in fields if f['path'].rsplit('/',1)[-1] in names]
    return {'version': VERSION, 'specialist_ready': True, 'stage': stage, 'legacy_forms': form_names,
        'xml_tree': node(root), 'fields': fields,
        'dates': select({'DATE_CONCLUSION_CONTRACT','DATE_DISPATCH_NOTICE','DATE_PUBLICATION_NOTICE','DATE_RECEIPT_TENDERS','AwardDate','IssueDate','EndDate','StartDate'}),
        'parties': select({'OFFICIALNAME','RegistrationName','CompanyID','ID','Name'}),
        'values': select({'VAL_TOTAL','VAL_ESTIMATED_TOTAL','VAL_ESTIMATED','VAL_RANGE_TOTAL','LOW','HIGH','PayableAmount','EstimatedOverallContractAmount','TotalAmount','TaxExclusiveAmount'}),
        'references': select({'NO_DOC_OJS','NoticePublicationID','NoticeIdentifier','ContractFolderID','LOT_NO','CONTRACT_NO','ID'}),
        'review_status': 'source_extracted_unreviewed',
        'limitations': ['Notice stage is not proof of a successful award or payment.',
                       'Parties remain unresolved; preserve lot and currency context.',
                       'Current XML retrieval does not establish historical point-in-time availability.']}

def enrich_notice(data, identity, client, prefer_package=False):
    require(re.fullmatch(r'\d+-\d{4}', identity), 'ted_invalid_notice_number')
    result = copy.deepcopy(data)
    linked = data.get('links', {}).get('xml', {})
    urls = list(dict.fromkeys(linked.values())) if isinstance(linked, dict) else []
    if not urls:
        urls = ['https://ted.europa.eu/en/notice/' + identity + '/xml']
    url = urls[0]
    parts = urlsplit(url)
    require(parts.scheme == 'https' and parts.hostname == 'ted.europa.eu' and parts.port in {None,443}
            and not parts.username and not parts.password and parts.path.endswith('/' + identity + '/xml'), 'ted_untrusted_xml_url')
    start = len(client.evidence)
    client.sleep(max(0, 0.5 - (time.monotonic() - client.last_request)))
    client.last_request = time.monotonic()
    method = 'individual_xml'
    try:
        require(not prefer_package and not getattr(client, '_ted_direct_unavailable', False), 'ted_direct_deferred')
        with build_opener(NoRedirect()).open(Request(url, headers={'User-Agent':'ProcurementDataCollector/1.0', 'Accept':'application/xml'}), timeout=20) as response:
            require(response.status == 200, 'ted_xml_http_' + str(response.status))
            raw = response.read(16 * 1024 * 1024 + 1)
        enrichment = parse_xml(raw, identity)
        client.save(raw, url, 'application/xml')
    except Exception as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)): raise
        client._ted_direct_unavailable = True
        from ted_packages import package_xml
        raw, _ = package_xml(data, identity, client)
        enrichment = parse_xml(raw, identity)
        method = 'daily_xml_package'
    enrichment['retrieval_method'] = method
    result.update(notice_xml=raw.decode('utf-8-sig'), enrichment=enrichment)
    return result, copy.deepcopy(client.evidence[start:])


def bounded_notice_items(identity, data, url, day, item_factory, threshold=1024*1024, chunk_chars=65536):
    """Keep oversized extracted notices queryable as ordered JSON content chunks.

    The parent remains a notice; child IDs are explicitly content records, not
    additional awards. Original XML evidence is retained by the caller.
    """
    import hashlib
    import json
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    raw = text.encode('utf-8')
    if len(raw) <= threshold:
        return [item_factory(identity, data, url, day)]
    checksum = hashlib.sha256(raw).hexdigest()
    pieces = [text[i:i+chunk_chars] for i in range(0, len(text), chunk_chars)]
    summary = {k:v for k,v in data.items() if k not in {'notice_xml', 'enrichment'}}
    # Search metadata can itself be large. It is also retained in full chunks.
    if len(json.dumps(summary,ensure_ascii=False).encode()) > threshold:
        summary = {'publication-number': identity}
    enrichment = data.get('enrichment', {})
    summary['enrichment'] = {k:enrichment[k] for k in ('version','stage','legacy_forms','review_status','limitations') if k in enrichment}
    summary['enrichment']['specialist_ready'] = False
    summary['enrichment']['status'] = 'full_content_in_ordered_chunks'
    summary['content_manifest'] = {'schema':'ted-json-chunks-v1','parent_notice_id':identity,
        'encoding':'UTF-8','format':'JSON','sha256':checksum,'bytes':len(raw),'chunk_count':len(pieces),
        'reassembly':'Concatenate content_text ordered by chunk_index, verify UTF-8 SHA256, then parse JSON.'}
    result = [item_factory(identity, summary, url, day)]
    for index, piece in enumerate(pieces):
        result.append(item_factory(identity+':content:'+str(index).zfill(6), {
            'record_type':'notice_content_chunk','parent_notice_id':identity,
            'chunk_index':index,'chunk_count':len(pieces),'content_sha256':checksum,
            'content_text':piece,'encoding':'UTF-8','format':'JSON'},url,day))
    return result
