"""Stage public artifact collectors with bounded, explicit official-site scopes."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]

def main():
    registry=json.loads((ROOT/'config/constellation-source-registry.json').read_text())['sources']
    existing={r['catalog_entry'] for r in registry if r['catalog_entry']<65}
    # Existing native historical routes handle the other original public entries.
    extra={1,4,7,16,23,24,27,28,30,31,45,49,52,54,58}
    skip={76,77,79,81,143,145,147,151,156}
    selected={}
    for line in (ROOT/'constellation/API_ACCESS_CHECKLIST.md').read_text().splitlines():
        if not line.startswith('| ') or 'public_route_no_key' not in line:continue
        fields=[x.strip() for x in line.split('|')]
        try:n=int(fields[1])
        except ValueError:continue
        if n in skip or (n in existing and n not in extra):continue
        links=re.findall(r'\[Source\]\(([^)]+)\)',line)
        if links:selected[n]=[links[-1]]
    selected[24]=['https://www.chinadrugtrials.org.cn/']
    # Actual datasets / archive indexes, rather than API documentation pages.
    selected.update({
        4:['https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities?sc_lang=en'],
        28:['https://api.crossref.org/works?filter=type:proceedings-article,from-pub-date:2016-01-01&rows=1000&cursor=*'],
        58:['https://api.ror.org/organizations?query=research'],
        65:['https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.?startPeriod=2016-01-01&format=csv'],
        67:['https://stat.unido.org/portal/dataset/getDataset/IIP','https://stat.unido.org/portal/dataset/getDataset/INDSTAT/4'],
        68:['https://rplumber.ilo.org/files/indicator/UNE_2UNE_SEX_AGE_NB_A.rds'],
        80:['https://opendata.nhsbsa.net/api/3/action/package_list'],
        82:['https://www.wsts.org/67/Historical-Billings-Report'],
        85:['https://iea-pvps.org/publications/'],
        88:['https://www.nice.org.uk/guidance/published?ngt=Technology%20appraisal%20guidance'],
        89:['https://www.cda-amc.ca/','https://www.cda-amc.ca/sites/default/files/DRR/2024/SR0860_Patient_and_Clinician_Group_Input.pdf'],
        90:['https://www.data.gouv.fr/api/1/datasets/open-medic-base-complete-sur-les-depenses-de-medicaments-interregimes/'],
        92:['https://www.cninfo.com.cn/new/index'],
        93:['https://data.stats.gov.cn/english/?cn=C01','https://www.stats.gov.cn/english/PressRelease/'],
        100:['https://openapi.twse.com.tw/v1/opendata/t187ap03_L','https://openapi.twse.com.tw/v1/opendata/t187ap05_L'],
        119:['https://ec.europa.eu/eurostat/web/international-trade-in-goods/database'],
        122:['https://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%5Btimeout%3A25%5D%3Bnwr%5B%22industrial%22%5D%5B%22name%22%5D%2833%2C-113%2C34%2C-112%29%3Bout%20center%3B'],
        129:['https://bulks-faostat.fao.org/production/FoodBalanceSheets_E_All_Data_(Normalized).zip'],
        128:['https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer'],
        144:['https://api.openaire.eu/search/projects?format=json&size=100'],
        146:['https://api.osf.io/v2/registrations/?page%5Bsize%5D=100'],
        149:['https://theses.fr/'],
        148:['https://api.semanticscholar.org/graph/v1/paper/search?query=robotics&limit=100&fields=paperId,title,year,publicationDate,citationCount'],
        152:['https://cordis.europa.eu/data/cordis-h2020projects-csv.zip','https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip'],
        155:['https://gtr.ukri.org/gtr/api/projects?f=json&s=100&p=1'],
        158:['https://otl.stanford.edu/annual-report','https://tlo.mit.edu/about/annual-reports']})
    # Public report summaries are distinct from the providers' licensed full products.
    selected[83]=['https://www.semi.org/en/news-resources/press']
    selected[84]=['https://ifr.org/ifr-press-releases/']
    sources=[]
    for n,seeds in sorted(selected.items()):
        entry=registry[n-1];hosts=set()
        for url in seeds:
            h=urlsplit(url).hostname;hosts.update((h,h[4:] if h.startswith('www.') else 'www.'+h))
        if n==82:hosts.add('www.wsts.org')
        note='Public archive discovery and linked raw documents; dated coverage and structured extraction require separate verification.'
        if n in (65,68,129,152):note={65:'BIS central-bank policy-rate daily CSV from 2016; selected dataflow only.',68:'ILOSTAT annual unemployment-by-sex/age RDS snapshot. Original vintages and forecast/observation separation are not yet extracted.',129:'FAOSTAT normalized Food Balance Sheets bulk ZIP; year filtering and table extraction pending.',152:'CORDIS H2020 and Horizon Europe public project CSV archives; pre-programme coverage is not asserted.'}[n]
        if n==82:note='WSTS public regional monthly semiconductor billings workbook; detailed paid products are excluded.'
        if n in (83,84):note='Public press releases and report summaries only; licensed full historical datasets are excluded.'
        if n==122:note='Named industrial facilities in a Phoenix reference bounding box, current OSM snapshot only; not global coverage or reconstructed 2016 facilities.'
        if n==148:note='Public Semantic Scholar robotics keyword metadata sample, at most the first public result page. Full citation-context coverage needs a dedicated adapter and potentially a key.'
        if n==144:note='Public OpenAIRE project metadata sample. This capture does not yet paginate the full graph or assert historical completeness.'
        if n==158:note='Initial Stanford and MIT public technology-transfer report indexes only; broader universities require additional configured publisher URLs.'
        if n==88:note='Public NICE appraisal pages and linked reports only; syndication API and licensed reuse access remain separate.'
        source={'catalog_entry':n,'source':entry['source_key'],'name':entry['catalog_name'],'seeds':seeds,'hosts':sorted(hosts),'max_depth':3,'decodo':n in (4,7,16,23,24,69,86,88,89,92,93,94,95,96,97,101,102,103,107,108,109,110,111,112,113,126,128,136,137,138,139,141,154,158),'scope_note':note}
        if n in (68,129,152):source.update(asset_only=True,signature='1f8b' if n==68 else '504b')
        if n==65:source.update(asset_only=True,accept='text/csv')
        if n==90:
            # The dataset page is an API index.  Its resource URLs are the
            # substantive Open Medic releases and reside on data.gouv's CDN.
            source.update(catalog_index=True,asset_only=True)
            hosts.add('files.data.gouv.fr')
            source['hosts']=sorted(hosts)
        if not source.get('asset_only') and n not in (28,58,80,100,122,144,146,148,155):source['decodo']=True
        sources.append(source)
    (ROOT/'config/constellation-public-sources.json').write_text(json.dumps({'schema_version':1,'historical_start_target':'2016-01-01','historical_host':'c7i','daily_host':'t3','sources':sources},indent=2)+'\n')
    path=ROOT/'config/constellation-legacy-routes.json';data=json.loads(path.read_text())
    for source in sources:
        unit='constellation-public-'+source['source']+'.service'
        row={'unit':unit,'catalog_entry':source['catalog_entry'],'public_capture_source':source['source'],'route_kind':'independent_public_historical','argv':['public_source_capture.py','--source',source['source'],'--mode','historical','--limit','6'],'start_target':'2016-01-01','end_exclusive':'2026-10-26','cadence_seconds':300,'timeout_seconds':900,'execution_enabled':False,'activation_staged':True,'remaining_requirements':['deploy_and_live_validation'],'validation_basis':source['scope_note']}
        prior=next((r for r in data['routes'] if r['unit']==unit),None)
        if prior and prior.get('execution_enabled'):row.update(execution_enabled=True,activation_staged=False,remaining_requirements=[])
        data['routes']=[r for r in data['routes'] if r['unit']!=unit]+[row]
    path.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'staged_public_sources':len(sources),'catalog_entries':[s['catalog_entry'] for s in sources]}))

if __name__=='__main__':main()
