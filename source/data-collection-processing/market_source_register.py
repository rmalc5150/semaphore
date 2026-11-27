"""Import the market workbook into a versioned, reviewable source register."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from source_pauses import is_paused

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'config/market-source-register.v1.json'
CATALOG = ROOT / 'config/constellation-source-registry.json'

# These are workbook-scope datasets. Provider access and activation are tracked
# independently in market-source-routes.v1.json and the capture state.
SPLITS = {
    159: ('events', 'mentions', 'knowledge_graph'),
    164: ('github_events',), 167: ('posts', 'revisions'),
    170: ('cve', 'cpe'), 171: ('rfc', 'internet_drafts'),
    172: ('ripe_ris', 'routeviews'), 174: ('filing_index', 'filing_documents'),
    175: ('legal_units', 'establishments'), 178: ('dfp', 'itr'),
    179: ('issuer_ifrs', 'bank_statistics'), 180: ('sedar_plus', 'legacy_sedar'),
    188: ('opinions', 'recap'), 196: ('inspections', 'citations'),
    201: ('oil', 'gas'), 204: ('disaggregated_futures', 'disaggregated_combined', 'financial_futures', 'financial_combined', 'legacy_futures', 'legacy_combined'),
    205: ('financials', 'deposits'), 208: ('icio', 'tiva'),
    216: ('law', 'legislative_history'), 217: ('dockets', 'documents', 'comments'),
    219: ('registrations_and_reports', 'contributions'), 220: ('projects', 'contracts'),
    225: ('sentinel_1', 'sentinel_2'), 226: ('procurements', 'orders'),
    227: ('case_files', 'tsdr'), 228: ('grants', 'exhibits'),
    229: ('downloads', 'release_metadata'), 231: ('downloads', 'release_metadata'),
    233: ('underlying_cause', 'multiple_cause'), 235: ('ilinet', 'lab_surveillance'),
    236: ('rsv_archive_2010_2020', 'rsv_current'), 238: ('demographics', 'exam', 'lab', 'questionnaire'),
    239: ('nhis', 'brfss'), 240: ('uscs', 'seer'), 243: ('flunet', 'fluid'),
    245: ('wuenic', 'jrf'), 246: ('surveillance_atlas', 'annual_reports'),
    247: ('ears_net', 'esac_net'), 248: ('reports', 'vaccines', 'symptoms'),
    249: ('insider_bulk', 'insider_filings'), 250: ('schedule_13d', 'schedule_13g'),
    251: ('holdings_bulk', 'holdings_filings'), 252: ('legacy_interests', 'current_interests'),
    253: ('provider_data', 'issuer_events'),
    255: ('legacy_transactions', 'current_transactions'), 257: ('legacy_register', 'current_register'),
    264: ('final', 'preliminary'), 266: ('quarterly_transactions', 'contracts'),
    267: ('semiconductor_equipment', 'industrial_robots', 'machinery'),
    268: ('quarterly', 'annual'), 270: ('orders', 'shipments'),
}
RELATED = {159:[11], 164:[44], 174:[1], 177:[1],
           198:[120,124], 214:[15,16], 217:[48], 227:[40],
           249:[5], 250:[5], 251:[5], 252:[4,7],
           264:[54], 265:[54], 266:[56], 267:[82,83,84],
           268:[84], 269:[83], 270:[84], 271:[91], 272:[54]}
EXTENSIONS = {249,250,251,252,264,271}
OWNER_REMOVED = {12, 99, 191}
PAID_EXCLUSIONS = {
    232: 'Global Trade Alert licensed commercial data and API route',
    262: 'ASX commercial automated market announcements subscription route',
}


def cell_value(cell):
    if cell.hyperlink and cell.hyperlink.target:
        return cell.hyperlink.target
    v = cell.value
    if isinstance(v, str) and v.upper().startswith('=HYPERLINK('):
        match = re.match(r'=HYPERLINK\("((?:[^"]|"")*)"', v, re.I)
        if not match:
            raise ValueError(f'Unsupported hyperlink in {cell.coordinate}')
        return match[1].replace('""', '"')
    if isinstance(v, date):
        return v.isoformat()
    return v


def rows(sheet):
    headers = [c.value for c in sheet[6]]
    return [
        {name: cell_value(cell) for name, cell in zip(headers, row) if name and cell.value is not None}
        for row in sheet.iter_rows(min_row=7)
        if any(cell.value is not None for cell in row)
    ]


def keyed(records, field):
    indexed = {}
    for record in records:
        key = int(record[field])
        if key in indexed:
            raise ValueError(f'Duplicate workbook source ID {key}')
        indexed[key] = record
    return indexed


def build(workbook):
    from openpyxl import load_workbook
    book = load_workbook(workbook)
    main = keyed(rows(book['Sources']), 'ID')
    conditions = rows(book['Conditions'])
    additional = keyed([row for row in conditions if row.get('Type') == 'Additional; conditional'], 'ID / supplied ID')
    guide = keyed(rows(book['Fetch guide']), 'ID')
    if main.keys() & additional.keys() or main.keys() | additional.keys() != guide.keys():
        raise ValueError('Sources, additional Conditions and Fetch guide do not reconcile by ID')
    records = []
    for number, fetch in sorted(guide.items()):
        if number in OWNER_REMOVED:
            continue
        research = main.get(number) or additional[number]
        name = research['Source / dataset']
        if name != fetch['Source / dataset']:
            raise ValueError(f'Workbook title mismatch for ID {number}')
        keys = SPLITS.get(number, ('provider_data',))
        records.append({
            'catalog_entry': number, 'source_key': f'market_source_{number}', 'name': name,
            'registration': 'conditional' if number in additional else 'main',
            'related_catalog_entries': [entry for entry in RELATED.get(number, []) if entry not in OWNER_REMOVED],
            'historical_target_start': '2016-01-01',
            'datasets': list(keys), 'research': research, 'fetch_guide': fetch,
        })
    connections = rows(book['Connections'])
    for connection in connections:
        field = 'Outcome / validation data'
        if connection.get(field) == 'Companies House/SIRENE/ABN + BDS':
            connection[field] = 'Companies House/SIRENE + BDS'
    return {
        'schema_version': 1, 'workbook': workbook.name,
        'workbook_sha256': hashlib.sha256(workbook.read_bytes()).hexdigest(),
        'research_review_date': book['Sources']['B4'].value.date().isoformat(),
        'sources': records,
        'existing_corrections': [row for row in conditions if row.get('Type') == 'Existing-list correction'],
        'connections': connections,
        'collection_notes': rows(book['Collection notes']),
    }


def catalog_rows(manifest):
    for record in manifest['sources']:
        if record['catalog_entry'] in OWNER_REMOVED:
            continue
        paid = PAID_EXCLUSIONS.get(record['catalog_entry'])
        paused = is_paused(record['source_key'])
        yield {
            'catalog_entry': record['catalog_entry'], 'catalog_name': record['name'],
            'source_key': record['source_key'], 'datasets': record['datasets'],
            'lineage': 'workbook_extension' if record['catalog_entry'] in EXTENSIONS else 'workbook_addition',
            'related_catalog_entries': record['related_catalog_entries'],
            'evidence_role': 'publisher', 'readiness': 'excluded_payment_required' if paid else 'evidence_gated',
            'collector_status': 'excluded_from_collection' if paid else 'owner_paused' if paused else 'see_market_source_status',
            'historical_start_target': record['historical_target_start'],
            'historical_complete': False, 'missing_reason': paid or ('operator_paused' if paused else 'see_market_source_status'),
        }


def write(path, data):
    output = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(output)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    args = parser.parse_args()
    manifest = build(args.workbook)
    catalog = json.loads(CATALOG.read_text())
    expected_prior = set(range(1, 159)) - OWNER_REMOVED
    prior = [row for row in catalog['sources'] if row['catalog_entry'] in expected_prior]
    if {row['catalog_entry'] for row in prior} != expected_prior:
        raise SystemExit('The existing catalogue is missing expected entries')
    additions = list(catalog_rows(manifest))
    if any(row['catalog_entry'] <= 158 for row in additions):
        raise SystemExit('Workbook overlaps the existing catalogue')
    catalog.update(catalog_entries=len(prior)+len(additions), sources=prior+additions)
    write(MANIFEST, manifest)
    write(CATALOG, catalog)
    print(f"Imported {len(additions)} additions alongside {len(prior)} existing entries")


if __name__ == '__main__':
    main()
