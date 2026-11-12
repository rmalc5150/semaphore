"""S55 original documents and source-attributed technical/funding evidence.

Extraction produces reviewable source facts, never inferred awards or achieved performance.
"""
import csv
import hashlib
import io
import json
import re
import zipfile
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit

from lxml import html
from research_contract import digest

VERSION = 'doe-storage-evidence-v2'
ROOT_URL = 'https://www.energy.gov/oe/energy-storage'
HOSTS = {'www.energy.gov', 'energy.gov', 'cms.doe.gov', 'netl.doe.gov', 'www.netl.doe.gov',
         'eere-exchange.energy.gov', 'oced-exchange.energy.gov',
         'www.pnnl.gov', 'pnnl.gov', 'www.sandia.gov', 'sandia.gov', 'www.osti.gov', 'osti.gov'}
TOPIC = re.compile(r'storag|batter|rovi|liftoff|flow.system|long.duration|FOA.?3020|DE.FOA.0003020', re.I)
METRICS = {
    'cost': r'\b(?:cost|LCOS|CAPEX|OPEX)\b|\$\s*/\s*k[Ww]',
    'efficiency': r'\befficien(?:cy|cies)\b',
    'duration': r'\bduration\b|\b\d+(?:\.\d+)?\s*(?:hours?|hrs?)\b',
    'capacity_power': r'\bcapacity\b|\b\d+(?:\.\d+)?\s*(?:[kMG]W(?:h)?|Ah)\b',
    'lifetime_degradation': r'\blifetime\b|\bcycle life\b|\bdegrad(?:ation|e)\b',
    'safety': r'\bthermal runaway\b|\bflammability\b|\bsafety test\b',
}
FUNDING = re.compile(r'funding opportunity|\bFOA[- :\d]|DE-FOA-|\bgrant\b|\baward(?:ed|s)?\b|'
                     r'\bfunding\b|\bselected\b|\bselects\b|\brecipient\b|\bcost.share\b|\bproject milestone\b', re.I)
TECHNOLOGIES = {'lithium_ion': r'lithium.ion|li.ion', 'flow_battery': r'flow batter|vanadium|redox',
                'sodium_battery': r'sodium|Na.ion', 'zinc_battery': r'\bzinc\b', 'lead_acid': r'lead.acid',
                'thermal_storage': r'thermal (?:energy )?storage', 'hydrogen_storage': r'hydrogen',
                'pumped_hydro': r'pumped (?:storage|hydro)', 'compressed_air': r'compressed.air',
                'supercapacitor': r'supercapacitor', 'long_duration_storage': r'long.duration'}


def canonical(url, base=ROOT_URL):
    p = urlsplit(urljoin(base, url))
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        return None
    # DOE's public content links currently point at its CMS host. Use the public mirror.
    host = 'www.energy.gov' if p.hostname in {'energy.gov', 'cms.doe.gov'} else p.hostname
    return urlunsplit(('https', host, quote(p.path, safe='/%:@!$&\'()*+,;=-._~'), p.query, ''))


def relevant(url, label='', parent_topic=False):
    if not canonical(url):
        return False
    text = url + ' ' + label
    if re.search(r'privacy|accessibility|foia|contact.us|careers|/people/|/search|/user/|\.jpg|\.png|\.mp4|\.css|\.js(?:\?|$)', text, re.I):
        return False
    return bool(TOPIC.search(text) or (parent_topic and re.search(r'\.(pdf|xlsx|csv|docx)(?:\?|$)|/media/\d+|/FileContent\.aspx', url, re.I)))


def technologies(text):
    return [name for name, pattern in TECHNOLOGIES.items() if re.search(pattern, text, re.I)]


def evidence_class(text, title=''):
    combined = title + ' ' + text
    if re.search(r'template|data requirements|reference performance tests|test protocol', title, re.I):
        return 'requirements_or_template'
    if re.search(r'\btarget\b|\bgoal\b|\baim(?:s)?\b|\baspiration\b', text, re.I):
        return 'target_or_goal'
    if re.search(r'\bmodel(?:ed|led|ing)?\b|\bprojected\b|\bestimat(?:e|ed|es)\b|scenario', combined, re.I):
        return 'modeled_or_estimated'
    return 'source_statement_requires_measurement_review'


def pdf_hyperlinks(page):
    """Resolve only URI action fields, not cyclic PDF structure/annotation graphs."""
    from pdfminer.pdftypes import resolve1
    links = []
    for reference in resolve1(page.page_obj.annots) or []:
        annotation = resolve1(reference)
        if not isinstance(annotation, dict): continue
        action = resolve1(annotation.get('A'))
        if not isinstance(action, dict): continue
        uri = resolve1(action.get('URI'))
        if isinstance(uri, bytes): uri = uri.decode('utf-8', errors='replace')
        if isinstance(uri, str): links.append(uri)
    return links


def parse_document(raw, url, max_pages=100, max_cells=30000):
    """Read HTML, PDF, XLSX and CSV. Original bytes remain the complete evidence."""
    sections, tables, links, excluded = [], [], [], []
    limits, source_date = [], None
    title = unquote(urlsplit(url).path.rsplit('/', 1)[-1])
    kind, status = 'unknown', 'text_extracted'
    if raw.startswith(b'%PDF-'):
        import pdfplumber
        kind = 'pdf'
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            title = (pdf.metadata or {}).get('Title') or title
            total_pages = len(pdf.pages)
            if total_pages > max_pages:
                limits.append({'kind': 'page_limit', 'total': total_pages, 'processed': max_pages})
            for number, page in enumerate(pdf.pages[:max_pages], 1):
                text = page.extract_text() or ''
                sections.append({'page': number, 'text': text})
                for table in page.find_tables():
                    rows = table.extract()
                    tables.append({'page': number, 'bbox': list(table.bbox), 'rows': rows,
                                   'page_context': text[:6000]})
                # Retain relevant official links embedded in reports as discovery candidates.
                try:
                    annotations = pdf_hyperlinks(page)
                except Exception as exc:
                    annotations = []
                    limits.append({'kind':'pdf_annotation_link_gap','page':number,'error':type(exc).__name__})
                for annotation in annotations:
                    target = canonical(annotation, url)
                    if target and relevant(target, parent_topic=True):
                        links.append({'url': target, 'label': 'PDF hyperlink'})
                page.close()
        if sum(len(s['text'].strip()) for s in sections) < 100:
            status = 'ocr_needed'
    elif raw.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if sum(i.file_size for i in members) > 128 * 1024 * 1024:
                raise ValueError('Archive expansion cap')
            names = {i.filename for i in members}
            if 'xl/workbook.xml' not in names:
                return {'title': title, 'kind': 'archive', 'sections': [], 'tables': [], 'links': [],
                        'excluded_links': [], 'source_date': None, 'text': '', 'limits': [],
                        'extraction_status': 'unsupported_archive_original_saved',
                        'archive_members': sorted(names), 'semantic_hash': hashlib.sha256(raw).hexdigest()}
        import openpyxl
        kind = 'xlsx'
        workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        cells = 0
        try:
            for sheet in workbook:
                rows = []
                for row in sheet.iter_rows():
                    cells += len(row)
                    if cells > max_cells:
                        limits.append({'kind': 'cell_limit', 'processed': max_cells})
                        break
                    values = [{'coordinate': cell.coordinate, 'value': cell.value.isoformat() if hasattr(cell.value, 'isoformat') else cell.value,
                               'formula': cell.data_type == 'f', 'number_format': cell.number_format}
                              for cell in row if cell.value is not None]
                    if values:
                        rows.append(values)
                tables.append({'sheet': sheet.title, 'cell_rows': rows,
                               'formula_values': 'original_formulas_preserved_not_evaluated'})
                sections.append({'sheet': sheet.title, 'text': '\n'.join(
                    ' | '.join(str(c['value']) for c in row) for row in rows)})
                if cells > max_cells:
                    break
        finally:
            workbook.close()
    elif urlsplit(url).path.lower().endswith('.csv'):
        kind = 'csv'
        reader = csv.reader(io.StringIO(raw.decode('utf-8-sig')))
        rows, cells = [], 0
        for row in reader:
            cells += len(row)
            if cells > max_cells:
                limits.append({'kind': 'cell_limit', 'processed': max_cells}); break
            rows.append(row)
        tables.append({'rows': rows})
        sections.append({'text': '\n'.join(' | '.join(row) for row in rows)})
    else:
        if b'<html' not in raw.lower()[:8192] and b'<!doctype html' not in raw.lower()[:8192]:
            raise ValueError('Unsupported or non-document response')
        kind = 'html'
        root = html.fromstring(raw)
        published = root.xpath('//meta[@name="citation_publication_date"]/@content|//meta[@property="article:published_time"]/@content')
        if published and re.match(r'^\d{4}-\d{2}-\d{2}', published[0]):
            source_date = {'value': published[0][:10], 'source_value': published[0], 'basis': 'explicit_publication_metadata'}
        main = (root.xpath('//main') or [root])[0]
        for node in main.xpath('.//script|.//style|.//nav|.//header|.//footer|.//*[contains(@class,"breadcrumb")]'):
            node.drop_tree()
        title = ' '.join(main.xpath('.//h1//text()')).strip() or ' '.join(root.xpath('//title/text()')).strip() or title
        topic = bool(TOPIC.search(url + ' ' + title))
        for anchor in main.xpath('.//a[@href]'):
            label = ' '.join(anchor.text_content().split())
            original = urljoin(url, anchor.get('href'))
            target = canonical(original, url)
            if target and relevant(target, label, topic):
                links.append({'url': target, 'label': label, 'original_url': original})
            elif re.search(r'\.(pdf|xlsx|csv|docx)(?:\?|$)', original, re.I) or TOPIC.search(label):
                excluded.append({'url': original, 'label': label, 'reason': 'outside_official_host_or_topic_scope'})
        for index, node in enumerate(main.xpath('.//h1|.//h2|.//h3|.//p|.//li|.//tr')):
            text = ' '.join(node.text_content().split())
            if text:
                sections.append({'html_block': index, 'tag': node.tag, 'text': text})
        for index, table in enumerate(main.xpath('.//table')):
            tables.append({'html_table': index, 'rows': [[
                ' '.join(cell.text_content().split()) for cell in row.xpath('./th|./td')]
                for row in table.xpath('.//tr')]})
        if not sections:
            text = ' '.join(main.text_content().split())
            if not text:
                raise ValueError('Empty main document')
            sections = [{'html_block': 0, 'text': text}]
    text = '\n'.join(section['text'] for section in sections)
    if len(text) > 4 * 1024 * 1024:
        limits.append({'kind': 'text_limit', 'original_characters': len(text)})
        # Retain bounded indexed sections; original file is archived.
        selected, size = [], 0
        for section in sections:
            if size + len(section['text']) > 4 * 1024 * 1024: break
            selected.append(section); size += len(section['text'])
        sections = selected; text = '\n'.join(s['text'] for s in sections)
    return {'title': str(title), 'kind': kind, 'text': text, 'sections': sections, 'tables': tables,
            'links': list({link['url']: link for link in links}.values()), 'excluded_links': excluded,
            'source_date': source_date, 'extraction_status': status, 'limits': limits,
            'technologies': technologies(str(title) + ' ' + text),
            'semantic_hash': digest([str(title), re.sub(r'\s+', ' ', text).strip(), tables])}


def facts(document, max_facts=400):
    technical, funding = [], []
    title = document['title']
    for section in document['sections']:
        # PDFs are indexed by page; restrict statements to small text windows rather than
        # pairing every number/organization on a whole page into a fabricated fact.
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])|\n\s*\n', section['text'])
        for part_index, text in enumerate(parts):
            if not text.strip(): continue
            windows = [text[i:i+1800] for i in range(0, len(text), 1500)]
            for window_index, passage in enumerate(windows):
                location = {k: v for k, v in section.items() if k != 'text'}
                location.update(part=part_index, window=window_index)
                metric_names = [name for name, pattern in METRICS.items() if re.search(pattern, passage, re.I)]
                numbers = re.findall(r'(?<!\w)(?:\$\s*)?\d[\d,]*(?:\.\d+)?\s*(?:%|million|billion|\$?/kWh|\$?/kW|MWh|MW|kWh|kW|hours?|cycles?|years?)?', passage, re.I)
                common = {'supporting_text': passage, 'location': location, 'technologies': technologies(passage),
                          'review_status': 'pending', 'numeric_tokens': numbers,
                          'relation_status': 'source_context_only; numbers_not_automatically_assigned_to_products'}
                if metric_names and (numbers or document['kind'] == 'xlsx'):
                    technical.append({**common, 'metric_candidates': metric_names,
                        'evidence_class': evidence_class(passage, title), 'normalized_measurement': None,
                        'conditions_and_assumptions': 'Review source passage, source tables, adjacent footnotes and report methodology'})
                if FUNDING.search(passage):
                    stages = []
                    for stage, pattern in [('opportunity', r'funding opportunity|\bFOA\b|DE-FOA-'),
                        ('selection', r'\bselect(?:ed|s|ion)\b'), ('award_announcement', r'\baward(?:ed|s)?\b'),
                        ('disbursement_statement', r'\bdisburs|\bpaid\b'), ('project_milestone_statement', r'project milestone|commissioned|operational')]:
                        if re.search(pattern, passage, re.I): stages.append(stage)
                    funding.append({**common, 'stage_mentions': stages,
                        'amount_mentions': re.findall(r'\$\s*\d[\d,.]*(?:\s*(?:million|billion|thousand))?', passage, re.I),
                        'project_or_opportunity_ids': sorted(set(re.findall(r'\b(?:DE-(?:FOA|LC|EE|OE|AR|FE)-?[A-Z0-9]{5,}|FOA\s*[-:]?\s*\d{3,})\b', passage, re.I))),
                        'named_parties_and_amount_allocation': 'Requires source-table or passage review; program totals are not individual awards',
                        'actual_payment_confirmed': False})
    technical_tables, funding_tables = [], []
    for index, table in enumerate(document['tables']):
        # A funding sentence elsewhere on the page does not turn a technical table
        # into an award table. Classify using table content only.
        text = json.dumps(table.get('rows', table.get('cell_rows', [])), ensure_ascii=False, default=str)
        ref = {'table_index': index, 'location': {k: v for k, v in table.items() if k not in {'rows', 'cell_rows', 'page_context'}},
               'review_status': 'pending', 'units_and_headers': 'Preserved in original extracted table; no inferred conversions'}
        if any(re.search(pattern, text, re.I) for pattern in METRICS.values()):
            technical_tables.append(ref)
        if FUNDING.search(text):
            funding_tables.append(ref)
            rows = table.get('rows', [])
            if not rows and table.get('cell_rows'):
                def column(cell):
                    number = 0
                    for letter in re.match(r'[A-Z]+',cell['coordinate'])[0]: number = number*26+ord(letter)-64
                    return number-1
                width = max((column(c)+1 for row in table['cell_rows'] for c in row),default=0)
                rows = []
                for row in table['cell_rows']:
                    values = [None]*width
                    for cell in row: values[column(cell)] = cell['value']
                    rows.append(values)
            header_index = next((i for i,row in enumerate(rows[:5]) if any(
                re.search(r'recipient|awardee|lead organization|project name|project title|federal share|award amount',str(c or ''),re.I) for c in row)),None)
            if header_index is not None:
                headers = rows[header_index]
                for row_number,row in enumerate(rows[header_index+1:],header_index+2):
                    fields = [{'source_header':str(h or ''),'source_value':v,'column':col+1}
                              for col,(h,v) in enumerate(zip(headers,row)) if h and v is not None and str(v).strip()]
                    if fields:
                        funding.append({'fact_kind':'source_table_row','location':{'table_index':index,'row':row_number,**ref['location']},
                            'source_fields':fields,'review_status':'pending','stage_mentions':[],
                            'actual_payment_confirmed':False,
                            'relation_status':'Same-row source fields preserved; entity identity, award stage and amount allocation require review'})
    return {'technical': technical[:max_facts], 'funding': funding[:max_facts],
            'technical_tables': technical_tables, 'funding_tables': funding_tables,
            'limits': [{'kind': 'fact_limit', 'category': name, 'total': len(value), 'indexed': max_facts}
                       for name, value in [('technical', technical), ('funding', funding)] if len(value) > max_facts]}


def directory_mentions(document, directory):
    """Exact registry mentions only; mentions never establish recipient/test relationships."""
    text = document['text']; result = []
    companies = {c['company_id']: c for c in directory.get('companies', [])
                 if c['review_status'] == 'verified' and not c.get('archived_at')}
    products = {p['product_id']: p for p in directory.get('products', [])
                if p['review_status'] == 'verified' and not p.get('archived_at')}
    names = [('company', cid, c['canonical_name']) for cid, c in companies.items()]
    names += [('product', pid, p['canonical_name']) for pid, p in products.items()]
    names += [('company', a['company_id'], a['alias']) for a in directory.get('aliases', [])
              if a['company_id'] in companies and a['review_status'] == 'verified']
    for kind, identity, name in names:
        if len(name.strip()) < 3: continue
        match = re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I)
        if match:
            result.append({'entity_type': kind, 'entity_id': identity, 'matched_name': name,
                           'status': 'name_candidate_review_required', 'relationship': 'mentioned_only',
                           'supporting_text': text[max(0,match.start()-150):match.end()+150]})
    return result
