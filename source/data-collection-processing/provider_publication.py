"""Extract source-declared publication dates separately from observation dates."""
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
import re


MAX_BYTES = 4 * 1024**2
HTML_FIELDS = {'article:published_time', 'govuk:first-published-at', 'dcterms.issued', 'citation_publication_date'}
REGIONAL_HTML_FIELDS = {'pubdate', 'publishdate'}
REGIONAL_SOURCES = {
    'china_nbs_industrial_production', 'china_miit_electronics_and_battery_statistics',
    'china_nea_power_statistics', 'china_mofcom_export_controls',
}
JSON_FIELDS = {
    'clinicaltrials_gov': ('studies.*.protocolSection.statusModule.studyFirstPostDateStruct.date',),
    'cpsc_recalls': ('*.RecallDate',),
    'datacite_dissertations_datasets_software_and_usage': ('data.*.attributes.publicationYear',),
    'ema_ctis': ('publishDate',),
    'ema_medicines': ('data.*.first_published_date',),
    'europe_pmc': ('resultList.result.*.firstPublicationDate',),
    'fda_ires_recalls': ('RESULT.*.ENFORCEMENTREPORTDT',),
    'federal_register': ('results.*.publication_date',),
    'federal_register_documents': ('publication_date',),
    'market_source_170': ('vulnerabilities.*.cve.published',),
    'market_source_173': ('query.pages.*.revisions.*.timestamp',),
    'market_source_176': ('results.*.dateparution',),
    'market_source_177': ('data.sumario.metadatos.fecha_publicacion',),
    'market_source_181': ('*.metadata.caseOfficialJournalPublicationsPublishedDates.*',
                          '*.metadata.decisionOfficialJournalPublicationsPublishedDates.*',
                          '*.metadata.casePressReleasesPublicationDates.*', '*.metadata.decisionPressReleasesPublicationDates.*'),
    'market_source_219': ('results.*.dt_posted',),
    'sam_gov_opportunities': ('opportunitiesData.*.postedDate',),
    'semantic_scholar_citation_context': ('data.*.publicationDate',
                                          'data.*.citingPaper.publicationDate', 'data.*.citedPaper.publicationDate'),
    'ted_notices': ('notices.*.publication-date',),
    'zenodo_research_artifacts_and_usage': ('hits.hits.*.metadata.publication_date',),
}


def publication_date(value, as_of):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    text = str(value).strip()
    if re.fullmatch(r'\d{8}', text):
        text = f'{text[:4]}-{text[4:6]}-{text[6:]}'
    if re.fullmatch(r'\d{4}/\d{2}/\d{2}(?:[ T].*)?', text):
        text = text.replace('/', '-', 2)
    suffix = r'(?:(?:T| )\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?|[+-]\d{2}:?\d{2})?'
    calendar_date = re.fullmatch(r'(\d{4})(?:-(\d{2})(?:-(\d{2})'+suffix+r')?)?', text)
    if not calendar_date:
        return None
    year, month, day = calendar_date.groups()
    try:
        first = date(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return None
    if first > as_of:
        return None
    precision = 'day' if day else 'month' if month else 'year'
    return first.isoformat()[:{'day': 10, 'month': 7, 'year': 4}[precision]], precision


def values_at(node, path):
    if not path:
        yield node
        return
    field, *remaining = path
    if field == '*':
        children = node.values() if isinstance(node, dict) else node if isinstance(node, list) else ()
        for child in children:
            yield from values_at(child, remaining)
    elif isinstance(node, dict) and field in node:
        yield from values_at(node[field], remaining)


def evidence(values, as_of, scope, not_before):
    dated = []
    for basis, value in values:
        if basis.endswith('.ENFORCEMENTREPORTDT') and isinstance(value, str):
            try:
                value = datetime.strptime(value, '%m/%d/%Y').date().isoformat()
            except ValueError:
                continue
        if basis.endswith('.first_published_date') and isinstance(value, str):
            try:
                value = datetime.strptime(value, '%d/%m/%Y').date().isoformat()
            except ValueError:
                continue
        parsed = publication_date(value, as_of)
        if parsed and (not not_before or parsed[0] >= not_before.isoformat()[:len(parsed[0])]):
            dated.append((*parsed, basis))
    if not dated:
        return None
    value, precision, basis = min(dated)
    return {'value': value, 'precision': precision, 'basis': basis, 'scope': scope}


class PublicationMeta(HTMLParser):
    def __init__(self, fields):
        super().__init__(convert_charrefs=True)
        self.fields = fields
        self.values = []
        self.head = False

    def handle_starttag(self, tag, attrs):
        if tag == 'head':
            self.head = True
        if tag == 'body':
            self.head = False
        if self.head and tag == 'meta':
            fields = dict(attrs)
            name = (fields.get('property') or fields.get('name') or '').lower()
            if name in self.fields:
                self.values.append((name, fields.get('content')))

    def handle_endtag(self, tag):
        if tag == 'head':
            self.head = False


def from_bytes(source, body, content_format, *, as_of=None, not_before=None):
    """Return a publication claim backed by the original bytes when available."""
    as_of = as_of or datetime.now(timezone.utc).date()
    if content_format == 'html':
        text = body[:MAX_BYTES].decode('utf-8', 'replace')
        if source == 'market_source_270':
            article = re.search(r'<h1 class="title">[^<]+</h1>\s*<div class="meta">(.*?)'
                                r'<div class="articleContent">', text, re.S)
            if article:
                days = re.findall(r'<i class="fa-regular fa-calendar"></i>\s*(\d{2}/\d{2}/\d{4})\s*</div>', article[1])
                if len(days) == 1:
                    try:
                        release = datetime.strptime(days[0], '%m/%d/%Y').date().isoformat()
                    except ValueError:
                        return None
                    return evidence([('A3 article calendar', release)], as_of, 'document', not_before)
        fields = HTML_FIELDS | (REGIONAL_HTML_FIELDS if source in REGIONAL_SOURCES else set())
        parser = PublicationMeta(fields)
        try:
            parser.feed(text)
            parser.close()
        except ValueError:
            return None
        dates = {parsed[0] for _, value in parser.values if (parsed := publication_date(value, as_of))}
        return evidence(parser.values, as_of, 'document', not_before) if len(dates) == 1 else None

    fields = JSON_FIELDS.get(source)
    if content_format != 'json' or (not fields and source != 'google_patents_bigquery') or len(body) > MAX_BYTES:
        return None
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        return None
    if source == 'google_patents_bigquery':
        try:
            columns = [item['name'] for item in document['schema']['fields']]
            index = columns.index('publication_date')
            values = [('schema.publication_date', row['f'][index]['v']) for row in document['rows']]
        except (KeyError, TypeError, ValueError, IndexError):
            return None
    else:
        values = ((field, value) for field in fields for value in values_at(document, field.split('.')))
    return evidence(values, as_of, 'record_in_file', not_before)


def from_path(source, path, content_format):
    if content_format != 'html' and (content_format != 'json' or source not in JSON_FIELDS and source != 'google_patents_bigquery'):
        return None
    with path.open('rb') as original:
        return from_bytes(source, original.read(MAX_BYTES + 1), content_format)
