"""Explicit source scopes and archive windows; never manufacture snapshot history."""
from datetime import date, timedelta
from copy import deepcopy
from calendar import monthrange
from research_contract import ROOT, load_json


def months(start, end):
    cursor = start.replace(day=1)
    while cursor < end:
        following = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        yield cursor, min(following, end)
        cursor = following


def jobs(plan, universe, mode, today):
    historical_start = date.fromisoformat(plan['historical_start'])
    end = today + timedelta(days=1)
    if mode == 'historical':
        end = min(end, date.fromisoformat(plan['backfill_end_exclusive']))
    biotech = [c['canonical_name'] for c in universe['companies'] if c['collection_enabled']
               and any(s['sector_id'] == 'biotech' and s['review_status'] != 'rejected' for s in c['sectors'])]
    company_names = [c['canonical_name'] for c in universe['companies'] if c['collection_enabled']]
    for s in plan['sources']:
        if not s.get('enabled') or (mode == 'historical' and not s.get('historical')):
            continue
        kind = s['adapter']
        scopes = []
        from specialist_authenticated import KINDS as AUTH_KINDS, scopes as auth_scopes
        if kind.startswith('additional_'):
            from additional_source_plan import scopes as additional_scopes
            scopes=list(additional_scopes(s,historical_start,min(end,today),mode))
            if kind == 'additional_dart' and mode == 'historical' and s.get('original_document_bridge_end_exclusive'):
                # Keep pinned monthly scopes exactly as they were. The newer
                # missing range has nonoverlapping daily document checkpoints.
                bridge_end=min(today,date.fromisoformat(s['original_document_bridge_end_exclusive']))
                start=min(end,today)
                while start<bridge_end:
                    stop=start+timedelta(days=1)
                    scopes.append((start,stop,{'url':s['api'],'raw_content_revision':s['raw_content_revision']},s['coverage_note']))
                    start=stop
            if mode=='daily':
                scopes=[(a,b,{**p,'data_start':a.isoformat(),'data_end':b.isoformat()},note) for a,b,p,note in scopes]
        elif kind in AUTH_KINDS:
            begin = historical_start if mode == 'historical' else today - timedelta(days=7)
            if kind == 'eia_api' and mode == 'daily':
                begin = (today - timedelta(days=100)).replace(day=1)
            if kind == 'fda_dashboard' and mode == 'daily':
                begin = today - timedelta(days=120)
            scopes = list(auth_scopes(s, begin, min(end, today), mode))
        elif kind == 'gleif':
            enabled = {c['company_id'] for c in universe['companies'] if c['collection_enabled']}
            leis = sorted({i['value'] for i in universe['external_identifiers'] if i['system'] == 'lei'
                and i['entity_id'] in enabled and i['review_status'] == 'verified'})
            for lei in leis:
                scopes.append((today, end, {'url': s['api'] + lei, 'lei': lei},
                    'Current official legal entity identity for verified universe LEIs only; not dated ownership/membership reconstruction'))
        elif kind == 'uspto_assignments':
            windows = [(date(y, 1, 1), min(date(y + 1, 1, 1), end)) for y in range(historical_start.year, today.year + 1)] if mode == 'historical' else [(today, end)]
            for start, stop in windows:
                for application in s['applications']:
                    scopes.append((start, stop, {'url': s['api'] + application, 'application': application,
                        'start': start.isoformat(), 'end': stop.isoformat()},
                        'Eight reviewed US application assignment histories only; recorded events and entire original chain retained; chain completeness and legal title unverified'))
        elif kind in {'sec_companyfacts', 'ema_json', 'canada_noc'}:
            windows = [(date(y, 1, 1), min(date(y + 1, 1, 1), end)) for y in range(historical_start.year, today.year + 1)] if mode == 'historical' else [(today - timedelta(days=7), end)]
            if kind == 'canada_noc' and mode == 'daily' and s.get('full_inventory'):
                windows=[(date(1900,1,1),end)]
            for start, stop in windows:
                if kind == 'sec_companyfacts':
                    enabled = {c['company_id'] for c in universe['companies'] if c['collection_enabled']}
                    ciks = sorted({str(i['value']).zfill(10) for i in universe['external_identifiers']
                        if i['system'] == 'cik' and i['entity_id'] in enabled and i['review_status'] == 'verified'})
                    for cik in ciks:
                        scopes.append((start, stop, {'url': s['api'].format(cik=cik), 'cik': cik, 'start': start.isoformat(), 'end': stop.isoformat()},
                            'SEC tagged facts by filing date; current API restatements retained; not historical API vintages or narrative notes'))
                elif kind == 'canada_noc':
                    scopes.append((start, stop, {'url': s['api'], 'query': {'lang': 'en', 'type': 'json'}, 'start': start.isoformat(), 'end': stop.isoformat(), 'full_inventory': mode=='daily' and s.get('full_inventory',False)},
                        'Health Canada NOC decisions by issue date from current official bulk API; not original review dossiers or superseded vintages'))
                else:
                    scopes.append((start, stop, {'url': s['api'], 'start': start.isoformat(), 'end': stop.isoformat()},
                        'EMA current medicine metadata with historical first-publication dates; original EPAR PDFs and superseded vintages remain separate'))
        elif kind in {'pubmed', 'drugsfda', 'cpsc'}:
            windows = months(historical_start, end) if mode == 'historical' else [(today - timedelta(days=7), end)]
            for start, stop in windows:
                last = stop - timedelta(days=1)
                if kind == 'pubmed':
                    for topic in s['topics']:
                        scopes.append((start, stop, {'url': s['api'], 'query': {'term': topic, 'datetype': 'pdat', 'mindate': start.strftime('%Y/%m/%d'), 'maxdate': last.strftime('%Y/%m/%d')}},
                            'Topic-scoped PubMed metadata and abstracts; no complete full text or confirmed company/product joins'))
                elif kind == 'cpsc':
                    scopes.append((start, stop, {'url': s['api'], 'query': {'format': 'json',
                        'RecallDateStart': start.isoformat(), 'RecallDateEnd': last.isoformat()}, 'start': start.isoformat(), 'end': stop.isoformat()},
                        'CPSC dated recall records including products and hazards; no claim of all incidents or warranty/fleet reliability'))
                else:
                    scopes.append((start, stop, {'url': s['api'], 'query': {'search': 'submissions.submission_status_date:[' + start.strftime('%Y%m%d') + ' TO ' + last.strftime('%Y%m%d') + ']'}},
                        'DrugsFDA applications, submissions and original application-document URLs; original document extraction remains separate'))
        elif kind in {'bls', 'nih', 'comtrade', 'pdf', 'cms_coverage'}:
            years = range(historical_start.year, today.year + 1) if mode == 'historical' else [today.year]
            if kind == 'bls' and mode == 'daily':
                # Six years cover the retained archive, including annual seasonal revisions.
                years = range(historical_start.year, today.year + 1)
            if kind == 'nih':
                fiscal_year = today.year + (today.month >= 10)
                years = range(historical_start.year, fiscal_year + 1) if mode == 'historical' else [fiscal_year]
            for year in years:
                start, stop = date(year, 1, 1), min(date(year + 1, 1, 1), end)
                if kind == 'nih':
                    start = max(historical_start, date(year - 1, 10, 1))
                    stop = min(date(year, 10, 1), end)
                    for topic in s['topics']:
                        scopes.append((start, stop, {'url': s['api'], 'criteria': {'fiscal_years': [year], 'advanced_text_search':
                            {'operator': 'and', 'search_field': 'all', 'search_text': topic}}}, 'topic grant context; not confirmed company validation'))
                    for offset in range(0, len(biotech), 8):
                        scopes.append((start, stop, {'url': s['api'], 'criteria': {'fiscal_years': [year], 'org_names': biotech[offset:offset + 8]}},
                            'named biotech organizations in bounded eight-name batches; fuzzy matches retained as candidates; academic partners need reviewed links'))
                elif kind == 'bls':
                    for series in s['series']:
                        scopes.append((start, stop, {'url': s['api'] + series['id'], 'series': series['id'], 'year': year, 'unit': series['unit']}, 'US manufacturing wage proxy; not fully loaded customer labor cost'))
                elif kind == 'comtrade':
                    for reporter in s['reporters']:
                        for commodity in s['commodities']:
                            scopes.append((start, stop, {'url': s['api'], 'query': {'period': year, 'reporterCode': reporter,
                                'cmdCode': commodity, 'flowCode': 'M', 'partnerCode': 0, 'partner2Code': 0,
                                'customsCode': 'C00', 'motCode': 0, 'maxRecords': 500}}, 'annual imports, named reporters and HS codes only; country, exporter, grade and reporting-lag gaps retained'))
                elif kind == 'cms_coverage':
                    scopes.append((start, stop, {'url': s['api'] + 'national-coverage-annual/',
                        'query': {'year': year, 'document_type': 'NCD'}}, 'US Medicare NCD annual versions; local coverage, commercial payers, other countries and CPT-use rights remain separate'))
                    if mode == 'daily':
                        scopes.append((start, stop, {'url': s['api'] + 'national-coverage-ncd/', 'query': {}}, 'current national coverage inventory and version links; not complete payer access'))
                else:
                    for mineral in s['minerals']:
                        scopes.append((start, stop, {'url': s['api'].format(year=year, mineral=mineral), 'period': str(year),
                                      'event_date': None}, 'full USGS mineral reports, layout-checked statistics, footnotes, supply-chain evidence, vintage comparisons and unresolved entity exposure; historical availability unverified'))
        elif kind in {'ted', 'federal_register', 'epmc', 'usaspending'}:
            windows = months(historical_start, end) if mode == 'historical' else [(today - timedelta(days=7), end)]
            for start, stop in windows:
                last = stop - timedelta(days=1)
                if kind == 'ted':
                    for cpv in s['cpv']:
                        query = 'publication-date >= ' + start.strftime('%Y%m%d') + ' AND publication-date <= ' + last.strftime('%Y%m%d') + ' AND classification-cpv = ' + cpv
                        scopes.append((start, stop, {'url': s['api'], 'query': query,
                            'fields': list(dict.fromkeys(s['fields'] + ['ojs-number'])) if mode == 'daily' else s['fields']},
                            'EU CPV notices with daily-package XML; stages, suppliers and values are source-extracted and require specialist review'
                            if mode == 'daily' else 'EU CPV notice candidates; procurement stages, suppliers and contract values require notice XML follow-up'))
                elif kind == 'federal_register':
                    for topic in s['topics']:
                        scopes.append((start, stop, {'url': s['api'], 'query': {'conditions[term]': topic,
                            'conditions[publication_date][gte]': start.isoformat(), 'conditions[publication_date][lte]': last.isoformat(),
                            'order': 'oldest'}}, 'US policy notices; proposed/final/effective-date stages are distinct; other jurisdictions remain gaps'))
                elif kind == 'epmc':
                    for topic in s['topics']:
                        scopes.append((start, stop, {'url': s['api'], 'query': '(' + topic + ') AND FIRST_PDATE:[' + start.isoformat() + ' TO ' + last.isoformat() + ']'},
                            'topic literature metadata, abstracts, affiliations and references; original full text and comparator/SAP extraction remain separate'))
                else:
                    for offset in range(0, len(company_names), 8):
                        scopes.append((start, stop, {'url': s['api'], 'filters': {'time_period': [{'start_date': start.isoformat(), 'end_date': last.isoformat()}],
                            'award_type_codes': ['A', 'B', 'C', 'D'], 'recipient_search_text': company_names[offset:offset + 8]}, 'fields': s['fields']},
                            'named-universe US contract award candidates in eight-name batches; not complete transaction, grant, loan or subsidiary history'))
        elif kind == 'caiso':
            # Standard API retention is 39 months. Older windows are a separate
            # Historical OASIS downloader gap, not repeatedly failed API calls.
            index = today.year * 12 + today.month - 1 - 39
            retention = date(index // 12, index % 12 + 1,
                             min(today.day, monthrange(index // 12, index % 12 + 1)[1]))
            start = max(historical_start, retention) if mode == 'historical' else today - timedelta(days=1)
            while start < today:
                stop = start + timedelta(days=1)
                for node in s['nodes']:
                    scopes.append((start, stop, {'url': s['api'], 'query': {'queryname': 'PRC_LMP', 'version': 12, 'resultformat': 6,
                        'market_run_id': 'DAM', 'node': node, 'startdatetime': start.strftime('%Y%m%dT00:00-0000'),
                        'enddatetime': stop.strftime('%Y%m%dT00:00-0000')}}, 'CAISO DAM hub components with original ZIP/member provenance and precise interval timing. Dedicated S57 worker adds RTM/RTPD, ancillary prices, project nodes and older requester-pays archives. Current retrieved vintages only.'))
                start = stop
        elif kind == 'eia_xlsx':
            # Use only archive links actually discovered on the official index.
            for archive in s.get('archives', []):
                period = archive['period']
                start = date.fromisoformat(period + '-01')
                if start < historical_start or start > today:
                    continue
                if mode == 'daily':
                    recent = sorted({a['period'] for a in s['archives'] if a['period'] <= today.strftime('%Y-%m')})[-3:]
                    if period not in recent:
                        continue
                stop = next(months(start, end))[1]
                scopes.append((start, stop, {'url': archive['url'], 'period': period}, 'US EIA battery generator inventory; not financing, warranty, dispatch or world installed capacity'))
        elif kind == 'github':
            for repo in s['repositories']:
                scopes.append((today, end, {'url': 'https://api.github.com/repos/' + repo + '/releases'},
                               'named public SDK repositories and complete release pages; repository/product identity and historical compatibility need review'))
        elif kind == 'mlperf':
            repositories = s['repositories'] if mode == 'historical' else s['repositories'][-4:]
            for repository in repositories:
                scopes.append((historical_start, end, {'url': 'https://github.com/' + repository, 'repository': repository},
                    'commit-pinned MLPerf results with linked system, configuration, accuracy and performance evidence; explicit missing/size-limited artifacts; entity matching and event dispatch pending; historical availability unverified'))
        elif kind == 'ror':
            for name in s['institutions']:
                scopes.append((today, end, {'url': s['api'], 'query': name}, 'current institution identity candidates; no historical affiliation reconstruction'))
        else:
            scopes.append((today, end, {'url': s['api']}, s['coverage_note']))
        if kind=='drugsfda' and mode=='daily' and s.get('full_inventory') and s.get('inventory_execution')!='dedicated_worker':
            week=today-timedelta(days=today.weekday())
            ranges=[]
            for prefix in ('ANDA','NDA','BLA'):
                for digit in range(10):
                    query=f'application_number:[{prefix}{digit}00000 TO {prefix}{digit}99999]'
                    ranges.append(query)
                    scopes.append((week,week+timedelta(days=7),{'url':s['api'],'query':{'search':query,'sort':'application_number:asc'},'inventory_scope':'all_provider_applications','partition':prefix+str(digit)},
                        'Current all-provider DrugsFDA inventory, including inactive/discontinued products; weekly capture scope, not historical snapshots or all worldwide drugs'))
            scopes.append((week,week+timedelta(days=7),{'url':s['api'],'query':{'search':'NOT ('+' OR '.join(ranges)+')','sort':'application_number:asc'},'inventory_scope':'all_provider_applications','partition':'other_application_ids'},
                'All-provider inventory complement; retains unexpected application identifiers instead of silently excluding them'))
        for start, stop, parameters, note in scopes:
            if kind == 'nih' and mode == 'daily' and today.day != 1:
                parameters = deepcopy(parameters)
                parameters['criteria']['date_added'] = {'from_date': (today - timedelta(days=7)).isoformat(), 'to_date': today.isoformat()}
                note += '; daily newly-added seven-day overlap, monthly full fiscal-year revision check'
            # Every daily observation is a new first-observed snapshot, even
            # when its provider data describes a much older event period.
            window_start, window_end = (start, stop) if mode == 'historical' or parameters.get('inventory_scope') else (today, end)
            yield {'source_id': s['source_id'], 'source': s['source'], 'adapter': kind,
                'mode': mode, 'start': window_start.isoformat(), 'end': window_end.isoformat(),
                'parameters': parameters, 'coverage_note': note}
