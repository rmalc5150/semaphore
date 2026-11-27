"""Recover reported fields before flattened text loses their roles and coordinates."""
import io
import re
from zipfile import BadZipFile, ZipFile

from semiotic_sandbox import sha

VERSION = 'semiotic-structured-v2'
NUMBER = re.compile(r'[-+−]?\d[\d,. ]*(?:[Ee][-+]?\d+)?\s*%?')
UNIT = re.compile(r'\((%|USD|EUR|RON|N|mm|cm|m|km|s|ms|Hz|kg|g|°C|kWh|W)\)\s*$', re.I)


def reported(field, value, locator):
    return {'field': field, 'value': value, 'locator': locator, 'method': VERSION, 'status': 'source_reported'}


def json_field(field, value, path):
    return reported(field, value, {'coordinate_system': 'published_observation_json_pointer', 'path': path})


def profile_fields(observation):
    """Read source-profile paths against the verified published observation."""
    def read(path):
        value = observation
        for token in path.split('/')[1:]:
            key = token.replace('~1', '/').replace('~0', '~')
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    for field in observation.get('semiotic_source_profile', {}).get('field_paths', ()):
        path = field['path']
        value = read(path)
        if value is None or value == '':
            continue
        role = field.get('role')
        name = field['field']
        if name == 'geographic_coverage':
            value = {'role': role, **(value if isinstance(value, dict) else {'name': value})}
        else:
            value = {'role': role, 'value': value}
        if unit_path := field.get('unit_path'):
            value.update(unit=read(unit_path), unit_locator=unit_path)
        yield json_field(name, value, path)


def archive(observation, directory):
    for artifact in observation.get('raw_artifacts', []):
        digest = artifact.get('sha256', '').removeprefix('sha256:')
        if not re.fullmatch('[a-f0-9]{64}', digest) or artifact.get('representation'):
            continue
        path = directory / digest
        if path.is_file() and artifact.get('origin') == 'first_party_source':
            body = path.read_bytes()
            if sha(body) != digest:
                raise ValueError('staged original hash mismatch')
            yield artifact, body


def ted_xml(body, artifact):
    from lxml import etree

    root = etree.fromstring(body, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    if etree.QName(root).localname not in {'ContractAwardNotice', 'ContractNotice', 'PriorInformationNotice'}:
        return
    tree = root.getroottree()

    def evidence(node, field, value):
        return reported(field, value, {'coordinate_system': 'xml_xpath', 'path': tree.getelementpath(node),
                                       'artifact_sha256': artifact['sha256']})

    if etree.QName(root).localname == 'ContractAwardNotice':
        yield evidence(root, 'event_role', 'contract_award_notice')
    ids = {'ContractFolderID': 'procurement_procedure', 'ID': 'eforms_id'}
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        tag = etree.QName(node).localname
        value = (node.text or '').strip()
        if not value:
            continue
        parents = [etree.QName(p).localname for p in node.iterancestors()]
        if tag == 'NoticeLanguageCode':
            yield evidence(node, 'original_language', {'RON': 'ro', 'ENG': 'en'}.get(value, value.lower()))
        if tag == 'ContractFolderID' or tag == 'ID' and (node.getparent() is root or parents[0] == 'ProcurementProjectLot'):
            yield evidence(node, 'identifier', {'type': 'lot' if parents[0] == 'ProcurementProjectLot' else ids[tag], 'id': value})
        if tag == 'IssueDate':
            yield evidence(node, 'date', {'role': parents[0], 'value': value})
        if tag == 'ItemClassificationCode' and node.get('listName') == 'cpv':
            yield evidence(node, 'provider_classification', {'system': 'CPV', 'code': value, 'role': parents[0]})
        if tag.endswith('Amount') and node.get('currencyID'):
            yield evidence(node, 'reported_amount', {'lexical_value': value, 'unit': node.get('currencyID'),
                                                     'role': tag, 'context': parents[0]})
        if tag in {'CountrySubentityCode', 'IdentificationCode', 'CityName'} and 'RealizedLocation' in parents:
            if tag != 'IdentificationCode' or 'Country' in parents:
                yield evidence(node, 'geographic_coverage', {'role': 'place_of_performance', 'name': value,
                              'code_system': {'CountrySubentityCode': 'NUTS', 'IdentificationCode': 'ISO 3166-1 alpha-3'}.get(tag)})
        if tag in {'AwardingCriterionTypeCode', 'AwardingCriterionDescription', 'EvaluationMethodTypeCode'} and 'AwardingCriterion' in parents:
            yield evidence(node, 'reporting_methodology', {'role': 'award_evaluation', 'description': value})


def numeric_cells(header, rows, start):
    for row_index in range(start, len(rows)):
        for col, value in enumerate(rows[row_index]):
            if not value or not NUMBER.fullmatch(value.strip()):
                continue
            label = header[col] if col < len(header) else None
            match = UNIT.search(label or '')
            yield {'row': row_index + 1, 'column': col + 1, 'value': value.strip(), 'column_label': label,
                   'unit': '%' if value.strip().endswith('%') else match[1] if match else None}


def table_value(header, rows, start, locator):
    values = list(numeric_cells(header, rows, start))
    if values:
        return {**reported('numerical_table', {'cells': values, 'rows': len(rows)}, locator), 'status': 'candidate'}
    return None


def pdf_tables(body, artifact):
    import pymupdf

    with pymupdf.open(stream=body, filetype='pdf') as doc:
        for page_no, page in enumerate(doc, 1):
            if page_no > 30:
                break
            for number, table in enumerate(page.find_tables().tables, 1):
                cells = table.extract()
                if not cells or len(cells) < 2:
                    continue
                header = table.header.names or cells[0]
                start = 0 if table.header.external else 1
                locator = {'coordinate_system': 'pdf_table', 'page': page_no, 'table': number,
                           'bbox': list(table.bbox), 'artifact_sha256': artifact['sha256']}
                if value := table_value(header, cells, start, locator):
                    yield value


def html_tables(body, artifact):
    from lxml import html

    document = html.fromstring(body)
    tree = document.getroottree()
    for table in document.xpath('//table'):
        if table.xpath('.//table|.//*[@rowspan or @colspan]'):
            continue
        rows = table.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')
        cells = [[' '.join(cell.text_content().split()) for cell in row.xpath('./th|./td')] for row in rows]
        if len(cells) < 2 or not cells[0]:
            continue
        header = cells[0] if rows[0].xpath('./th') else []
        locator = {'coordinate_system': 'html_xpath_table', 'path': tree.getpath(table),
                   'artifact_sha256': artifact['sha256']}
        if value := table_value(header, cells, int(bool(header)), locator):
            yield value


def extract(observation, archives):
    payload = observation['payload']
    data = payload.get('data') or {}
    source = observation['source_key']
    output = [json_field('identifier', {'type': source, 'id': observation['source_record_id']}, '/source_record_id')]
    for key in ('source_published_at', 'event_at', 'available_at'):
        if observation.get(key):
            output.append(json_field('date', {'role': key, 'value': observation[key]}, '/' + key))
    native_date_fields = {
        'arxiv': ('published', 'updated'),
        'google_patents_bigquery': ('priority_date', 'filing_date', 'publication_date', 'grant_date'),
        'nasa_power_weather_and_solar_resource': ('date',),
        'nist_robotics_methods': ('source_date',),
        'usa_spending': ('Start Date', 'End Date'),
    }
    parent = payload if source == 'arxiv' else data
    base = '/payload/' if source == 'arxiv' else '/payload/data/'
    for field in native_date_fields.get(source, ()):
        if parent.get(field) is not None:
            output.append(json_field('date', {'role': field, 'value': parent[field]}, base + field))
    for name in ('original_language', 'language'):
        if observation.get(name):
            output.append(json_field('original_language', observation[name], '/' + name))
    if source == 'nasa_power_weather_and_solar_resource':
        location = {key: data[key] for key in ('reference_location', 'latitude', 'longitude')}
        output.append(json_field('geographic_coverage', {'role': 'measurement_location', **location}, '/payload/data'))
        if sources := data.get('header', {}).get('sources'):
            output.append(json_field('reporting_methodology', {'role': 'input_products', 'sources': sources},
                                     '/payload/data/header/sources'))
    elif source == 'usgs_earthquakes':
        coords = data['geometry']['coordinates']
        output.append(json_field('geographic_coverage', {'role': 'epicenter', 'longitude': coords[0],
                                                          'latitude': coords[1]}, '/payload/data/geometry/coordinates'))
        props = data['properties']
        for key in ('time', 'updated'):
            if props.get(key) is not None:
                output.append(json_field('date', {'role': key, 'provider_value': props[key]},
                                         '/payload/data/properties/' + key))
        if props.get('place'):
            output.append(json_field('geographic_coverage', {'role': 'provider_place_description', 'name': props['place']},
                                     '/payload/data/properties/place'))
        for key, unit in [('mag', None), ('felt', 'responses'), ('sig', None)]:
            if props.get(key) is not None:
                output.append(json_field('reported_measurement', {'name': key, 'value': props[key], 'unit': unit},
                                         '/payload/data/properties/' + key))
        if len(coords) > 2:
            output.append(json_field('reported_measurement', {'name': 'depth', 'value': coords[2], 'unit': 'km'},
                                     '/payload/data/geometry/coordinates/2'))
        if props.get('magType'):
            output.append(json_field('reporting_methodology', {'role': 'magnitude_scale', 'value': props['magType']},
                                     '/payload/data/properties/magType'))
    elif source == 'usa_spending' and 'Award Amount' in data:
        output.append(json_field('reported_amount', {'value': data['Award Amount'], 'role': 'award_amount',
                                                     'unit': None}, '/payload/data/Award Amount'))
    errors = []
    for artifact, body in archive(observation, archives):
        try:
            if body.startswith(b'PK\x03\x04'):
                with ZipFile(io.BytesIO(body)) as bundle:
                    members = [item for item in bundle.infolist() if not item.is_dir()]
                    output.append(reported('native_file_structure', {'format': 'zip', 'member_count': len(members),
                        'members': [{'name': item.filename, 'bytes': item.file_size} for item in members[:100]]},
                        {'coordinate_system': 'zip_central_directory', 'artifact_sha256': artifact['sha256']}))
            elif source == 'ted_notices' and body.lstrip().startswith(b'<'):
                output.extend(ted_xml(body, artifact))
            elif body.startswith(b'%PDF-'):
                output.extend(pdf_tables(body, artifact))
            elif re.search(rb'<(?:!doctype\s+html|html\b)', body[:4096], re.I):
                output.extend(html_tables(body, artifact))
        except (ValueError, RuntimeError, SyntaxError, BadZipFile) as error:
            errors.append({'artifact_sha256': artifact['sha256'], 'error_type': type(error).__name__})
    return {'values': output, 'errors': errors}
