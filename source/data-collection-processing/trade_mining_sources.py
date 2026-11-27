"""Official download and query scopes for the trade and mining catalogue."""
from datetime import date, timedelta
import re
from urllib.parse import parse_qs, urlencode, urlsplit

MDIC = 'brazil_mdic_comex_stat_api'
COCHILCO = 'chile_cochilco_production_and_mining_economics'
SERNAGEOMIN = 'chile_sernageomin_mining_yearbooks'
SNIFA = 'chile_sma_snifa_environmental_compliance'
MINEM = 'peru_minem_mining_bulletins_and_yearbooks'
SIACAM = 'argentina_siacam_mining_indicators'
SIGMINE = 'brazil_anm_sigmine_and_cadastro_mineiro'
GEOCAT = 'peru_ingemmet_geocatmin'
COMEXT = 'eurostat_comext_goods_trade'
TRACE = 'climate_trace_industrial_assets_and_activity'

HOSTS = {
    MDIC: ['api-comexstat.mdic.gov.br'],
    COCHILCO: ['www.cochilco.cl', 'cochilco.cl'],
    SERNAGEOMIN: ['www.sernageomin.cl', 'sernageomin.cl'],
    SNIFA: ['drive.usercontent.google.com', 'drive.google.com'],
    MINEM: ['www.gob.pe', 'cdn.www.gob.pe'],
    SIACAM: ['www.mecon.gob.ar'],
    SIGMINE: ['dadosabertos.anm.gov.br'],
    GEOCAT: ['geocatmin.ingemmet.gob.pe'],
    COMEXT: ['ec.europa.eu'],
    TRACE: ['api.climatetrace.org'],
}
SOURCES = frozenset(HOSTS)
NCM = (85076000, 26040000, 28252010, 25041000)
SMA_EXPORTS = {'1hPEwmUFZpmD7xFbJy-kjhhzjplnUB1mH'}
TRACE_ASSETS = (1566956, 1566610, 1567260, 38089178, 1566957)
COMEXT_PATH = '/eurostat/api/comext/dissemination/sdmx/2.1/data/ds-045409/'
GEOCAT_PATH = '/arcgis/rest/services/serv_catastro_minero_wgs84/mapserver/0/query'
MONTH = r'20\d\d-(?:0[1-9]|1[0-2])'


def mdic_request(url):
    """Decode our recorded request locator into the exact provider POST."""
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if (parsed.scheme, parsed.netloc, parsed.path) != ('https', HOSTS[MDIC][0], '/general'):
        raise ValueError('mdic_request_endpoint_mismatch')
    if set(query) != {'language', 'flow', 'from', 'to'} or any(len(values) != 1 for values in query.values()):
        raise ValueError('mdic_request_scope_invalid')
    language, flow, start, stop = (query[k][0] for k in ('language', 'flow', 'from', 'to'))
    if (language != 'en' or flow not in ('import', 'export')
            or not re.fullmatch(MONTH, start) or not re.fullmatch(MONTH, stop)
            or start > stop or start[:4] != stop[:4]):
        raise ValueError('mdic_request_scope_invalid')
    return 'https://api-comexstat.mdic.gov.br/general?language=en', {
        'flow': flow, 'monthDetail': True, 'period': {'from': start, 'to': stop},
        'filters': [{'filter': 'ncm', 'values': list(NCM)}], 'details': ['ncm'],
        'metrics': ['metricFOB', 'metricKG'],
    }


def in_scope(url, source, discovery=False):
    parsed = urlsplit(url)
    path = parsed.path.lower()
    query = parse_qs(parsed.query)
    if (parsed.scheme != 'https' or parsed.netloc not in HOSTS[source] or parsed.fragment):
        return False
    if source == MDIC:
        try:
            mdic_request(url)
        except ValueError:
            return False
        return True
    if source == COCHILCO:
        return bool(re.fullmatch(r'/web/download/\d+/20\d{2}/\d+/(?:base-de-datos-)?anuario-de-estadisticas-[a-z0-9-]+\.(?:xlsx|pdf)', path)
                    or discovery and path == '/web/anuario-de-estadisticas-del-cobre-y-otros-minerales/')
    if source == SERNAGEOMIN:
        if path == '/':
            return (set(query) == {'mode', 'safm_file', 'sig'} and query['mode'] == ['view']
                    and len(query['safm_file']) == len(query['sig']) == 1
                    and query['safm_file'][0].isdigit() and bool(re.fullmatch('[0-9a-f]{64}', query['sig'][0])))
        return bool(re.fullmatch(r'/pdf/anuario/anuario[a-z0-9_-]+\.pdf', path)
                    or discovery and path == '/anuarios-mineria-chile/')
    if source == SNIFA:
        return (path in ('/download', '/uc') and len(query.get('id', [])) == 1
                and query['id'][0] in SMA_EXPORTS and query.get('export') == ['download']
                and set(query) == {'id', 'export'})
    if source == MINEM:
        if parsed.hostname == 'cdn.www.gob.pe':
            return bool(re.fullmatch(r'/uploads/document/file/\d+/[^/]*(?:bem-|boletin|minera|minero|am-20\d{2}-excel-de-anexos)[^/]*\.(?:xlsx|pdf)', path))
        return discovery and bool(re.fullmatch(
            r'/institucion/minem/(?:colecciones/(?:6-boletin-estadistico-minero|[^/]*anuario[^/]*)|informes-publicaciones/\d+-[^/]*(?:boletin-estadistico-minero|anuario-minero|prepublicacion-del-bem)[^/]*)', path))
    if source == SIACAM:
        return bool(re.fullmatch(r'/dataset/ipi-minero/ipi-minero-(?:series|variaciones|ramas-de-actividad|produccion-litio)\.csv', path))
    if source == SIGMINE:
        return bool(re.fullmatch(r'/sigmine/(?:processos_minerarios/[a-z]{2}|area_servidao|arrendamento|bloqueio|protecao_fonte|reservas_garimpeiras)\.zip', path)
                    or re.fullmatch(r'/scm/(?:alvara_de_pesquisa|cessoes_de_direitos|guia_de_utilizacao_autorizada|licenciamento|plg|portaria_de_lavra|registro_de_extracao_publicado|relatorio_de_pesquisa_aprovado|requerimento_de_[a-z_]+)\.csv', path)
                    or discovery and path in ('/sigmine/', '/sigmine/processos_minerarios/', '/scm/'))
    if source == GEOCAT:
        ids = query.get('objectIds', [''])
        return (path == GEOCAT_PATH and len(ids) == 1 and bool(re.fullmatch(r'\d+(?:,\d+){0,49}', ids[0]))
                and query == {'objectIds': ids, 'outFields': ['*'], 'returnGeometry': ['true'], 'f': ['json']})
    if source == COMEXT:
        if not re.fullmatch(COMEXT_PATH + r'[am]\.de\.us\.(?:850760|260400|282520|250410)\.[12]\.value_in_euros', path):
            return False
        return (set(query) == {'startPeriod', 'endPeriod', 'format'} and query['format'] == ['SDMX-CSV']
                and all(len(query[k]) == 1 and re.fullmatch(r'20\d\d(?:-(?:0[1-9]|1[0-2]))?', query[k][0])
                        for k in ('startPeriod', 'endPeriod'))
                and query['startPeriod'][0] <= query['endPeriod'][0])
    if source == TRACE:
        return (path in {f'/v7/sources/{asset}' for asset in TRACE_ASSETS}
                and set(query) == {'start', 'end', 'timeGranularity', 'gas'}
                and query['gas'] == ['co2e_100yr'] and query['timeGranularity'] == ['year']
                and all(len(query[k]) == 1 and re.fullmatch(r'20\d{2}', query[k][0])
                        for k in ('start', 'end'))
                and 2021 <= int(query['start'][0]) <= int(query['end'][0]))
    return False


def discover(body, url, source, depth):
    from regional_source_review import Page
    found = {}
    for target, label in Page(body).links(url):
        target = target.split('#', 1)[0]
        if target == url or not in_scope(target, source, discovery=True):
            continue
        if source == SERNAGEOMIN and 'safm_file=' in target and 'anuario de la miner' not in label.lower():
            continue
        found[target] = {'url': target, 'depth': depth + 1}
    return sorted(found.values(), key=lambda entry: not in_scope(entry['url'], source))


def request_seeds(source, mode, today):
    """Refresh closed trade periods while preserving the historical query frontier."""
    if source not in (MDIC, COMEXT, TRACE):
        return None
    month = date.fromisoformat(today).replace(day=1)
    last = month - timedelta(days=1)
    if source == MDIC:
        if mode == 'daily':
            first = (month - timedelta(days=75)).replace(day=1)
            if first.year != last.year:
                first = date(last.year, 1, 1)
            windows = [(first.strftime('%Y-%m'), last.strftime('%Y-%m'))]
        else:
            windows = [(f'{y}-01', f'{y}-12' if y < last.year else last.strftime('%Y-%m'))
                       for y in reversed(range(2016, last.year + 1))]
        return ['https://api-comexstat.mdic.gov.br/general?' + urlencode(
            {'language': 'en', 'flow': flow, 'from': start, 'to': stop})
            for start, stop in windows for flow in ('import', 'export')]
    if source == COMEXT:
        if mode == 'daily':
            freq, start, stop = 'M', (month - timedelta(days=120)).strftime('%Y-%m'), last.strftime('%Y-%m')
        else:
            freq, start, stop = 'A', '2016', str(month.year - 1)
        query = urlencode({'startPeriod': start, 'endPeriod': stop, 'format': 'SDMX-CSV'})
        return ['https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-045409/'
                f'{freq}.DE.US.{product}.{flow}.VALUE_IN_EUROS?{query}'
                for product in (850760, 260400, 282520, 250410) for flow in (1, 2)]
    end = month.year - 1
    start = end if mode == 'daily' else 2021
    return [f'https://api.climatetrace.org/v7/sources/{asset}?start={start}&end={end}&timeGranularity=year&gas=co2e_100yr'
            for asset in TRACE_ASSETS]
