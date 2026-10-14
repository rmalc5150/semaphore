"""Additional official APIs. Historical event dates are not historical vintages."""
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from regulatory_collection import require, SourceIssue

KINDS = {'pubmed', 'drugsfda', 'sec_companyfacts', 'ema_json', 'canada_noc', 'cpsc', 'gleif', 'uspto_assignments'}


def fetch(client, job, cursor, item):
    kind, p = job['adapter'], job['parameters']
    url = p['url']
    if kind == 'gleif':
        data = client.json(url)
        record = data.get('data', {})
        require(record.get('id') == p['lei'], 'gleif_identity_mismatch')
        require(isinstance(record.get('attributes', {}).get('entity'), dict), 'gleif_missing_entity')
        return [item(p['lei'], record, url)], None
    if kind == 'uspto_assignments':
        from patent_collection import ODPClient
        odp = ODPClient(client.store)
        response = odp.application(p['application'])
        client.evidence.extend(odp.evidence)
        records = response.get('patentFileWrapperDataBag', [])
        require(response.get('count') == 1 and len(records) == 1 and records[0].get('applicationNumberText') == p['application'], 'assignment_application_mismatch')
        events = records[0].get('assignmentBag')
        require(isinstance(events, list), 'assignment_history_not_exposed')
        rows = []
        for event in events:
            day = (event.get('assignmentRecordedDate') or '')[:10]
            if job['mode'] == 'historical' and not (p['start'] <= day < p['end']):
                continue
            from research_contract import digest
            rows.append(item(digest({'application': p['application'], 'event': event}), {
                'application_number': p['application'], 'event': event, 'original_chain': events,
                'chain_completeness': 'not established', 'current_ownership': 'not established'}, url, day or None, 'derived'))
        return rows, None
    if kind in {'canada_noc', 'cpsc'}:
        data = json.loads(client.get(url, params=p.get('query')))
        require(isinstance(data, list), kind + '_response_shape')
        rows = []
        for row in data:
            identity = row.get('noc_number') if kind == 'canada_noc' else row.get('RecallID')
            day = (row.get('noc_date') if kind == 'canada_noc' else row.get('RecallDate')) or ''
            day = day[:10]
            require(identity is not None and len(day) == 10, kind + '_missing_identity_or_date')
            if kind == 'cpsc':
                require(p['start'] <= day < p['end'], 'cpsc_ignored_date_filter')
            if p['start'] <= day < p['end']:
                rows.append(item(identity, row, row.get('URL') or url, day))
        return rows, None
    if kind == 'pubmed':
        offset = int(cursor or 0)
        data = client.json(url, params={**p['query'], 'retstart': offset, 'retmax': 100, 'retmode': 'json', 'db': 'pubmed'})
        result = data.get('esearchresult', {})
        require('count' in result and isinstance(result.get('idlist'), list), 'pubmed_search_shape')
        total = int(result['count'])
        require(total <= 9999, 'pubmed_split_scope_required')
        ids = result['idlist']
        require(bool(ids) or offset == total, 'pubmed_missing_page')
        if not ids:
            return [], None
        raw = client.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', params={'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'xml'})
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            raise SourceIssue('pubmed_invalid_xml') from None
        rows = []
        for article in list(root):
            pmid = article.findtext('.//PMID')
            require(pmid in ids, 'pubmed_unexpected_pmid')
            rows.append(item(pmid, {'pmid': pmid, 'article_xml': ET.tostring(article, encoding='unicode'),
                'rights': 'metadata/abstract rights require review; not training eligible'}, 'https://pubmed.ncbi.nlm.nih.gov/' + pmid + '/'))
        require(sorted(r['id'] for r in rows) == sorted(ids), 'pubmed_incomplete_fetch')
        return rows, str(offset + len(ids)) if offset + len(ids) < total else None
    if kind == 'drugsfda':
        offset = int(cursor or 0)
        data = client.json(url, params={**p['query'], 'skip': offset, 'limit': 100}, no_matches=True)
        total = data.get('meta', {}).get('results', {}).get('total')
        rows = data.get('results')
        require(isinstance(total, int) and isinstance(rows, list), 'drugsfda_response_shape')
        require(total <= 25000, 'drugsfda_split_scope_required')
        require(bool(rows) or offset == total, 'drugsfda_missing_page')
        result = [item(r['application_number'], r, url) for r in rows]
        return result, str(offset + len(rows)) if offset + len(rows) < total else None
    if kind == 'sec_companyfacts':
        data = client.json(url)
        require(str(data.get('cik', '')).zfill(10) == p['cik'], 'sec_facts_cik_mismatch')
        require(isinstance(data.get('facts'), dict), 'sec_facts_shape')
        rows = []
        for namespace, concepts in data['facts'].items():
            for concept, detail in concepts.items():
                for unit, facts in detail.get('units', {}).items():
                    for fact in facts:
                        if p['start'] <= fact.get('filed', '') < p['end']:
                            from research_contract import digest
                            identity = digest({'cik': p['cik'], 'namespace': namespace, 'concept': concept, 'unit': unit, 'fact': fact})
                            rows.append(item(identity, {'cik': p['cik'], 'namespace': namespace, 'concept': concept,
                                'label': detail.get('label'), 'unit': unit, 'fact': fact}, url, fact['filed'], 'derived'))
        return rows, None
    data = json.loads(client.get(url))
    require(isinstance(data, dict), 'ema_json_shape')
    rows = data.get('data')
    # EMA exposes an update stamp plus the named medicine collection.
    if rows is None:
        arrays = [v for v in data.values() if isinstance(v, list)]
        require(len(arrays) == 1, 'ema_json_collection_changed')
        rows = arrays[0]
    require(isinstance(rows, list), 'ema_json_rows')
    result = []
    for row in rows:
        require(isinstance(row, dict) and row.get('ema_product_number'), 'ema_missing_product_id')
        raw_date = row.get('first_published_date') or ''
        day = None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                day = datetime.strptime(raw_date[:10], fmt).date().isoformat()
                break
            except ValueError:
                pass
        if job['mode'] == 'historical' and not (day and p['start'] <= day < p['end']):
            continue
        result.append(item(row['ema_product_number'], row, row.get('medicine_url') or url, day))
    return result, None
