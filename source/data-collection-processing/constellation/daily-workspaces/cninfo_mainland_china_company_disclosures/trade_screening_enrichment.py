"""S52 evidence-linked identities and exposure candidates. No legal determinations."""
import re
import unicodedata
from urllib.parse import urlsplit
from lxml import etree, html

VERSION = 'trade-screening-evidence-v1'
OFAC_EXPORT = 'https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/'
OFAC_UPDATES = 'https://ofac.treasury.gov/recent-actions/sanctions-list-updates'
HOSTS = {'ofac.treasury.gov', 'sanctionslist.ofac.treas.gov',
         'sanctionslistservice.ofac.treas.gov', 'sanctionssearch.ofac.treas.gov',
         'home.treasury.gov', 'www.treasury.gov', 'www.bis.gov', 'www.state.gov',
         'deccs.pmddtc.state.gov', 'www.federalregister.gov', 'www.govinfo.gov'}


def screening_identity(row):
    from research_contract import digest
    return digest({'list': row.get('source'), 'id': row.get('id') or digest(row)})


def official_url(url):
    p = urlsplit(url)
    return p.scheme == 'https' and p.hostname in HOSTS and not p.username and p.port in (None, 443)


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', str(value)).casefold() if c.isalnum())


def xml_entries(raw):
    """Yield original entry XML, retaining all authority fields and their paths."""
    import io
    seen = set()
    for _, entry in etree.iterparse(io.BytesIO(raw), events=('end',), tag='{*}sdnEntry',
                                   resolve_entities=False, no_network=True, load_dtd=False):
        uid = entry.findtext('{*}uid')
        if not uid or uid in seen:
            raise ValueError('Missing or duplicate OFAC entry UID')
        seen.add(uid)
        fields = {}
        for node in entry.iter():
            if len(node) == 0 and node.text and node.text.strip():
                names = []
                current = node
                while current is not entry:
                    names.append(etree.QName(current).localname)
                    current = current.getparent()
                fields.setdefault('/'.join(reversed(names)), []).append(node.text.strip())
        yield uid, {'fields': fields, 'entry_xml': etree.tostring(entry).decode()}
        entry.clear()
        while entry.getprevious() is not None:
            del entry.getparent()[0]
    if not seen:
        raise ValueError('No OFAC entries in authority response')


def document(raw, url):
    """Preserve paragraphs and source-published dates without inferring effective dates."""
    if raw.startswith(b'%PDF-'):
        import io
        from pypdf import PdfReader
        pages = PdfReader(io.BytesIO(raw)).pages
        return {'kind': 'pdf', 'paragraphs': [p.extract_text() or '' for p in pages],
                'links': [], 'dates': [], 'title': url.rsplit('/', 1)[-1]}
    root = html.fromstring(raw, base_url=url)
    for node in root.xpath('//script|//style|//nav|//footer|//header'):
        node.drop_tree()
    main = root.xpath('//main') or [root]
    paragraphs = [' '.join(n.text_content().split()) for n in main[0].xpath('.//p|.//li|.//tr|.//h1|.//h2|.//h3')]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        raise ValueError('Authority page has no readable content')
    from urllib.parse import urljoin
    links = sorted({urljoin(url, a.get('href')) for a in root.xpath('//a[@href]')})
    return {'kind': 'html', 'title': ' '.join(root.xpath('//title/text()')),
            'paragraphs': paragraphs, 'links': [u for u in links if official_url(u)],
            'dates': [{'value': n.get('datetime'), 'basis': 'authority_time_element'}
                      for n in root.xpath('//time[@datetime]')]}


def normalize(row, evidence):
    identities = [{'type': 'name', 'value': row.get('name'), 'path': 'data.name'}]
    for i, alias in enumerate(row.get('alt_names') or []):
        identities.append({'type': 'alias', 'value': alias, 'path': f'data.alt_names[{i}]'})
    relationships = []
    for i, ident in enumerate(row.get('ids') or []):
        typ, value = ident.get('type', ''), ident.get('number')
        identities.append({'type': typ, 'value': value, 'path': f'data.ids[{i}]'})
        if typ in {'Aircraft Operator', 'Vessel Owner', 'Vessel Operator'} and value:
            relationships.append({'name': value, 'role': typ.lower().replace(' ', '_'),
                                  'path': f'data.ids[{i}]', 'status': 'source_reported'})
    for name in re.findall(r'\(Linked To:\s*([^)]*)\)', row.get('remarks') or '', re.I):
        relationships.append({'name': name.strip(), 'role': 'linked_to',
                              'path': 'data.remarks', 'status': 'source_reported'})
    if row.get('vessel_owner'):
        relationships.append({'name': row['vessel_owner'], 'role': 'vessel_owner_reported',
                              'path': 'data.vessel_owner', 'status': 'source_reported'})
    return {'list': row.get('source'), 'entry_id': str(row.get('entity_number') or row.get('id')),
            'csl_id': str(row.get('id')), 'entity_type': row.get('type') or 'unknown',
            'identities': [i for i in identities if i['value']],
            'addresses': row.get('addresses') or [], 'relationships': relationships,
            'restrictions': {k: row.get(k) for k in ('programs', 'license_policy', 'license_requirement', 'remarks')},
            'explicit_dates': {k: row[k] for k in ('start_date', 'end_date') if row.get(k)},
            'evidence': evidence}


def matches(identity, directory):
    """Only reviewed list-scoped identifiers verify companies; names are candidates."""
    active = {c['company_id']: c for c in directory['companies']
              if not c.get('archived_at') and c['review_status'] != 'rejected'}
    targets = []
    if identity['entity_type'].casefold() not in {'aircraft', 'vessel', 'individual', 'person'}:
        targets.append(('listed_party', [i['value'] for i in identity['identities'] if i['type'] in {'name', 'alias'}]))
    targets += [(r['role'], [r['name']]) for r in identity['relationships']]
    result = {}
    for role, names in targets:
        names = {key(n) for n in names}
        for cid, company in active.items():
            if key(company['canonical_name']) in names:
                result[cid, role] = {'company_id': cid, 'role': role, 'status': 'candidate', 'basis': 'name_only'}
        for alias in directory['aliases']:
            if alias['company_id'] in active and alias['review_status'] != 'rejected' and key(alias['alias']) in names:
                result[alias['company_id'], role] = {'company_id': alias['company_id'], 'role': role,
                                                   'status': 'candidate', 'basis': 'alias_only'}
    # Explicit namespace includes the source list, avoiding collisions across authorities.
    expected = identity['list'] + '|' + identity['entry_id']
    if any(role == 'listed_party' for role, _ in targets):
        for ident in directory['identifiers']:
            cid = ident['company_id']
            if cid not in active or ident['review_status'] == 'rejected':
                continue
            if ident['namespace'] == 'trade_screening_entry' and ident['identifier_value'] == expected:
                verified = ident['review_status'] == active[cid]['review_status'] == 'verified'
                result[cid, 'listed_party'] = {'company_id': cid, 'role': 'listed_party',
                    'status': 'verified' if verified else 'candidate', 'basis': 'reviewed_list_scoped_identifier'}
    verified = [m for m in result.values() if m['status'] == 'verified']
    if len(verified) > 1:
        for m in verified:
            m.update(status='candidate', basis='conflicting_registry_identifiers')
    return list(result.values())


def exposures(company_matches, directory, assessed_at):
    products = {p['product_id']: p for p in directory.get('products', [])
                if p['review_status'] == 'verified' and not p.get('archived_at')}
    found = []
    for match in company_matches:
        for rel in directory.get('relationships', []):
            if rel['company_id'] != match['company_id'] or rel['product_id'] not in products:
                continue
            if rel['review_status'] != 'verified' or not rel.get('evidence'):
                continue
            day = assessed_at[:10]
            valid = (not rel.get('valid_from') or rel['valid_from'] <= day) and (not rel.get('valid_to') or day < rel['valid_to'])
            found.append({'product_id': rel['product_id'], 'company_id': rel['company_id'],
                          'company_match_status': match['status'], 'screened_party_role': match['role'],
                          'relationship': rel, 'relationship_valid_on_assessment_date': valid,
                          'status': 'potential_exposure_review_required' if valid else 'historical_relationship_context',
                          'assessment_date': day, 'restriction_applicability': 'not_determined'})
    return found


def enrich(row, evidence, directory, authority, notices, assessed_at):
    identity = normalize(row, evidence)
    company_matches = matches(identity, directory)
    linked_notices = []
    names = [i['value'] for i in identity['identities'] if i['type'] in {'name', 'alias'}]
    patterns = [re.compile(r'(?<!\w)' + re.escape(n) + r'(?!\w)', re.I) for n in names if len(key(n)) >= 5]
    for notice in notices:
        exact = identity['entry_id'] in notice.get('entry_ids', []) and 'Treasury' in (identity['list'] or '')
        fulltext = notice.get('fulltext') or '\n'.join(notice.get('paragraphs', []))
        relevant = [pattern for pattern in patterns if pattern.search(fulltext)]
        hits = [p for p in notice.get('paragraphs', []) if any(pattern.search(p) for pattern in relevant)] if relevant else []
        if exact or hits:
            linked_notices.append({'url': notice['url'], 'evidence': notice['evidence'],
                'dates': notice.get('dates', []), 'paragraphs': hits,
                'status': 'authority_entry_reference' if exact else 'name_candidate_review_required',
                'event_type': 'not_inferred'})
    return {'version': VERSION, 'assessed_at': assessed_at, 'identity': identity,
            'authority_entry': authority, 'related_notices': linked_notices,
            'notice_coverage': 'bounded_current_authority_pages_and_explicit_links; not_historical_archive',
            'company_matches': company_matches, 'product_exposures': exposures(company_matches, directory, assessed_at),
            'mapping_status': 'unmatched_directory_empty' if not directory['companies'] else
                              'matches_found' if company_matches else 'unmatched',
            'event_status': 'screening_context_only; event_pipeline_review_required',
            'gaps': ([] if authority.get('status') == 'entry_verified' else ['authority_entry_not_verified']) +
                    ([] if linked_notices else ['related_change_notice_not_resolved']),
            'point_in_time_eligible': False}
