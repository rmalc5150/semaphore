"""Write the workbook evidence rollup and the unresolved-source review list."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from collections import Counter

from market_source_register import MANIFEST, ROOT
from source_pauses import is_paused

CONFIG = ROOT/'config'
PILOTS = CONFIG/'market-source-pilots.v1.json'
ROUTES = CONFIG/'market-source-routes.v1.json'
ACTIVE = CONFIG/'market-source-activation.v1.json'
LIVE = CONFIG/'market-source-live.v1.json'
OVERVIEW = ROOT.parent/'data-source-overview.txt'
REVIEW = ROOT.parent/'market-sources-without-raw-evidence.md'
MARKER = 'NOVEMBER 2026 MARKET WORKBOOK SOURCES\n'
END = 'END NOVEMBER 2026 MARKET WORKBOOK SOURCES\n'

BLOCKERS = {
    160:'Common Crawl target-domain CDX request returned HTTP 504. Verify 2016 CDX queries and matching WARC byte-range objects.',
    161:'Wayback availability response returned a 2020 capture for the 2016 request. Verify a matching 2016 Memento and permitted replay.',
    165:'Requires a configured billing project and a partition/column-limited HTTP Archive BigQuery query.',
    166:'Supplied Trends Explore CSVs for 2016–2020 were imported through the historical archive pipeline. The 2021 export is still open. A browser export probe returned HTTP 429.',
    168:'The public survey index points to the 2016 repository archive. Verify original data file/LFS downloads and the data-use terms.',
    172:'Choose RIPE and RouteViews collectors, prefixes and storage limits before retrieving original MRT files.',
    173:'Define tracked Wikidata QIDs and fetch entity revision payloads with an explicit 2016 cutoff.',
    174:'Needs a Companies House key and tracked company numbers for filing and original document access.',
    175:'Verify SIRENE versioned legal-unit and establishment stocks and the size of each original historical file.',
    179:'Review the Chile CMF 2016 issuer archive and establish a verified financial statement download or bank API credential.',
    180:'The 2016 follow-up is closed because manual and programmatic access are unavailable to the project.',
    181:'Locate an official competition open dataset or case documents from the Commission search portal.',
    185:'The CADE page returned unrelated public PDFs. Verify a case-specific open-data export or official proceeding document.',
    186:'The CCI orders page returned no reviewed links. Verify case-specific orders and pagination.',
    188:'Needs a permitted CourtListener token or selected officials’ case opinions from the bulk archive and a RECAP coverage scope.',
    189:'The workbook returns a legal notice and discovery portal. Locate a substantive Safety Gate weekly report or scoped data export.',
    192:'Choose a valid PRODCOM product/indicator key for each methodological period and retrieve a substantive observation export.',
    196:'Verify a current DOL key or use the official OSHA inspection/citation extracts and their data dictionary.',
    197:'Locate downloadable TRI state/year resources behind the official selector and verify a facility/chemical record.',
    199:'Select the EEA EU ETS observed emissions and allocation download from the data viewer or a verified versioned export.',
    200:'The stored token is verified for France actual total load. The January 2016 XML was retained and published, with one hour unavailable in the tested route.',
    202:'IRENA start page returned HTTP 403. Verify a supported IRENASTAT public query or sanctioned bulk export.',
    203:'The workbook TranStats table link returned HTTP 404. Verify a current T-100 table and native monthly archive download.',
    206:'OICA published a statistics dashboard and definitions. Locate an official country/year output table with actual production observations.',
    208:'OECD topic page returned HTTP 403. Establish a valid edition-specific TiVA SDMX query and obtain ICIO files separately.',
    211:'PPI portal returned discovery HTML. Verify its sanctioned project-level export and historical coverage.',
    212:'Publisher page returned data availability workbooks. Verify an actual IMF DIP bilateral-position export.',
    213:'FAO page returned discovery HTML. Locate a permitted FPMA market/commodity series export.',
    216:'Configure EUR-Lex subscription credentials or a permitted CELLAR discovery and document download path.',
    217:'The stored api-data-gov key returned EPA documents posted in January 2016. Extend the verified first-page capture with date-window pagination and scoped docket, comment and attachment requests.',
    218:'WTO case catalogue was reachable. Verify case-specific original dispute documents or an official structured export.',
    219:'Review LDA V1 schema, credentials/rate limits, then verify newest and 2016 filings.',
    222:'Choose the OECD CRS edition and flow, donor and sector dimensions for a bounded substantive export.',
    223:'Needs approved Earthdata/LAADS access, tile scope, product collection and storage limit.',
    224:'Needs approved USGS M2M credentials, an asset or tile catalogue and bounded original-scene downloads.',
    225:'Requires bounded Sentinel-1 and Sentinel-2 product selection, permitted download credentials and a scene byte budget.',
    226:'Supplied 2016 purchase-order archives were imported. Standalone ChileCompra tender exports remain open.',
    227:'Official trademark case-files index yielded archive links. Verify permitted bulk retrieval, package size and TSDR access separately.',
    228:'EAS grant search and exhibits require a permitted route and historical sample. Grantee registration alone covers a different dataset.',
    230:'Commercial reuse qualification remains open. Obtain terms and verify a scoped ITU data export.',
    231:'Needs approved BigQuery spend and a bounded PyPI partition scan. The 2016 start and undercount periods require explicit handling.',
    232:'Requires Global Trade Alert data or API permission for the intended use and a historical export.',
    233:'Verify a permitted CDC WONDER XML request and dataset-specific 2016 mortality variables and grouped output.',
    235:'Interactive FluView page returned no original downloads. Verify an official ILINet and laboratory export with season identifiers.',
    237:'Catalogue links did not expose the rates records. Locate a supported FluSurv-NET export with denominators.',
    239:'Verify CDC NHIS and BRFSS original downloads under the appropriate transport and archive-size limits.',
    245:'WHO portal returned a viewer page. Confirm WUENIC and JRF versioned observation exports.',
    246:'ECDC Atlas returned HTTP 429. Verify a permitted export or original epidemiological report after provider cooldown.',
    247:'EARS-Net and ESAC-Net provider pages yielded no reviewed dataset download. Resolve their independent annual tables or exports.',
    248:'Supplied VAERS 2016–2025 reports, symptoms and vaccine tables were imported from the annual archives.',
    250:'Needs the existing SEC EDGAR archive joined to original Schedule 13D and 13G submissions and amendment handling.',
    252:'The 2016 gap is accepted. The first verified Disclosure of Interests export is still open for 2017 onward.',
    253:'Original issuer event history PDFs use the manual monthly archive importer. Individual insider transaction and holdings exports remain open.',
    254:'Verify the permitted FCA NSM export for retained director-dealing documents and its archive range.',
    255:'Verify CNMV legacy/current search responses and an actual director transaction document from each route.',
    256:'The NBIM holdings page returned no reviewed asset-class download links. Verify holdings files and reporting dates.',
    258:'Commercial use restrictions and filer-specific retention remain open. Requires a permitted source-specific disclosure route.',
    259:'Senate eFD requires acknowledgement and has restrictions on use and retention. A permitted source-specific route is needed.',
    260:'OGE access, use and historical retention vary by official. Requires a permissible archive route.',
    261:'Needs documented permitted HATVP retention/reuse and independently verified pre-July-2017 archives.',
    262:'Needs licensed ASX access or first-party copies with documented permission.',
    263:'Needs verified AMF use permissions and historical director-transaction retention/export.',
    266:'FERC site returned HTTP 403 and the Report Viewer connection was reset. Retry the official 2013 Q3–present quarterly download.',
    267:'Obtain substantive METI workbooks with each of the three intended series represented, including a 2016 version.',
    271:'MHLW landing page yielded methodology PDFs. Verify dated production tables from e-Stat, including the methodology break.',
}


def load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def clean(value):
    return ' '.join(str(value or '').split()).replace('|','\\|')


def report_lines():
    manifest=load(MANIFEST)
    pilots=load(PILOTS)
    routes={(r['source'],r['dataset']):r for r in load(ROUTES).get('routes',[])}
    active=load(ACTIVE)
    live=load(LIVE)
    applied=live.get('deployed',False)
    catalog=manifest['sources']
    db_meta={}
    for row in live.get('metadata',[]):
        db_meta.setdefault(row['source_key'],{})[row['job_state']]=row['jobs']
    queue={}
    for row in live.get('historical',[]):
        key=row['source_key'].removeprefix('legacy:constellation-public-').removesuffix('.service')
        queue.setdefault(key,{})[row['status']]=row['jobs']
    rows=[]
    for entry in catalog:
        number,source,name=entry['catalog_entry'],entry['source_key'],entry['name']
        data=[]
        for dataset in entry['datasets']:
            outcomes=pilots.get(source,{}).get(dataset,{})
            proofs=[(mode,row['receipt']) for mode,row in outcomes.items() if row.get('receipt')]
            config=routes.get((source,dataset),{})
            policy=active.get(source,{}).get(dataset,{})
            modes=policy.get('modes',[])
            reasons={mode:', '.join(dict.fromkeys(a['reason'] for a in row.get('attempts',[])))
                     for mode,row in outcomes.items() if not row.get('receipt')}
            if not config:
                reasons['historical']=BLOCKERS.get(number,'The workbook describes this dataset, but its substantive provider file and route still need verification.')
            elif not proofs and not any(reasons.values()):
                reasons['historical']=BLOCKERS.get(number,'No qualifying original under the reviewed method.')
            data.append(dict(dataset=dataset,proofs=proofs,config=config,policy=policy,modes=modes,reasons=reasons))
        rows.append((number,source,name,entry,data))
    captured=sum(any(item['proofs'] for item in r[-1]) for r in rows)
    daily=sum(any('daily' in d['modes'] for d in r[-1]) for r in rows)
    historical=sum(any('historical' in d['modes'] for d in r[-1]) for r in rows)
    meta=sum(row.get('state')=='enabled' for row in {r['source_key']:r for r in live.get('metadata',[])}.values()) if applied else 0
    queue_total=Counter()
    metadata_total=Counter()
    for row in live.get('historical',[]):
        queue_total[row['status']]+=row['jobs']
    for row in live.get('metadata',[]):
        if row['job_state']:
            metadata_total[row['job_state']]+=row['jobs']
    top=[
        MARKER.rstrip(),'Updated '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'',
        f'  Registered {len(catalog)} market-workbook additions alongside the existing catalogue.',
        f'  First raw evidence captured and checksum verified in S3 for {captured} source families.',
        f"  {'Live deployment verified' if applied else 'Local activation prepared'} for {daily} recurring sources and {historical} historical sources.",
        f"  Recurring scheduler checkpoints observed for {len(live.get('daily_state_sources',[]))} sources.",
        '  Historical batches | '+', '.join(f'{value} {state}' for state,value in sorted(queue_total.items())),
        f'  Metadata enabled in the live registry for {meta} sources. The first-file check covers the exact sample and retained provider scope.',
        '  Metadata jobs | '+', '.join(f'{value} {state}' for state,value in sorted(metadata_total.items())),
        f'  {len(catalog)-captured} sources lack verified raw evidence. See market-sources-without-raw-evidence.md.',
        '  Historical collection targets 2016-01-01 through 2026-11-20, subject to the documented scope and provider archive.',
        '  Current provider files that include older observations retain their actual retrieval time and unknown first-public availability.',
        '  All account, permission and unresolved archive cases remain evidence-gated.','','Per-source first evidence and collection status','',
    ]
    no_evidence=['# Market workbook sources without verified raw evidence','',
        f'{len(catalog)-captured} of {len(catalog)} source families have no retained original that passed validation. Their metadata and recurring collection gates remain closed.',
        '', '| ID | Source | Blocker or next archive check | Official route |','| --- | --- | --- | --- |']
    for number,source,name,entry,data in rows:
        if is_paused(source):
            top.extend([f'  {number} {name} | Paused at owner request', ''])
            start=entry['fetch_guide']['Start URL — click to open']
            no_evidence.append(f'| {number} | {clean(name)} | Paused at owner request. | [Provider]({start}) |')
            continue
        proofs=any(item['proofs'] for item in data)
        top.append(f'  {number} {name} | '+('first raw evidence captured' if proofs else 'no verified raw evidence'))
        if entry['registration']=='conditional':
            top.append('    Workbook qualification | '+clean(entry['research'].get('Historical / access issue')))
        if entry['related_catalog_entries']:
            top.append('    Related existing IDs | '+', '.join(f'{i:03d}' for i in entry['related_catalog_entries']))
        for item in data:
            profile=item['config']; modes=item['modes']; modes_label='enabled' if applied else 'staged locally'
            statuses=[
                ('recurring '+modes_label+f" every {profile['check_days']} day(s)") if 'daily' in modes else 'recurring held',
                ('historical '+modes_label) if 'historical' in modes else 'historical proof/route open',
                ('metadata enabled' if applied and source in db_meta else 'metadata staged') if item['policy'].get('metadata') else 'metadata held',
            ]
            top.append('    '+item['dataset']+' | '+' | '.join(statuses))
            if profile.get('throughput_hold'):
                top.append('      '+profile['throughput_hold'])
            if queue.get(source) and 'historical' in modes:
                top.append('      Historical queue source totals | '+', '.join(f'{value} {state}' for state,value in sorted(queue[source].items())))
            if db_meta.get(source) and item['policy'].get('metadata'):
                top.append('      Metadata job source totals | '+', '.join(f'{value} {state}' for state,value in db_meta[source].items() if state))
            for mode,receipt in item['proofs']:
                validation=receipt['validation']
                top.append(f"      {mode} original | {receipt['retrieved_at']} | {receipt['bytes']:,} bytes | SHA-256 {receipt['sha256']}")
                top.append('      '+receipt['artifact_uri'])
                top.append('      '+receipt['source_url'])
                time_fields=[validation.get('observed_from'),validation.get('observed_through')]
                if all(time_fields):
                    top.append('      Provider dates present | '+' to '.join(time_fields))
                elif validation.get('provider_file_interval'):
                    top.append('      Provider file interval | '+validation['provider_file_interval'])
                if validation.get('pagination_incomplete'):
                    top.append('      Provider reports more pages for the captured query.')
            if item['reasons']:
                top.append('      Open | '+' / '.join(f'{mode} {value}' for mode,value in item['reasons'].items() if value))
        if not proofs:
            why=BLOCKERS.get(number)
            if not why:
                why=' / '.join(f"{item['dataset']} {', '.join(value for value in item['reasons'].values() if value)}" for item in data)
            start=entry['fetch_guide']['Start URL — click to open']
            no_evidence.append(f'| {number} | {clean(name)} | {clean(why or "No validated provider record in the attempted scope.")} | [Provider]({start}) |')
        top.append('')
    top.extend([END.rstrip(),'',''])
    return '\n'.join(top),'\n'.join(no_evidence)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overview',type=Path,default=OVERVIEW)
    parser.add_argument('--review',type=Path,default=REVIEW)
    args=parser.parse_args()
    top,review=report_lines()
    prior=args.overview.read_text()
    if prior.startswith('MARKET WORKBOOK ARCHIVE FOLLOW-UP\n'):
        prior=prior.split('END MARKET WORKBOOK ARCHIVE FOLLOW-UP\n\n',1)[1]
    if prior.startswith(MARKER):
        prior=prior.split(END+'\n',1)[1]
    args.overview.write_text(top+prior)
    args.review.write_text(review)
    if args.overview==OVERVIEW and args.review==REVIEW and (CONFIG/'market-archive-results.v1.json').exists():
        from market_archive_status import main as archive_status
        archive_status()


if __name__=='__main__':
    main()
