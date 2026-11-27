"""Reconcile the market source review with the archive and Athena receipts."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from market_source_register import PAID_EXCLUSIONS, ROOT, write
from source_pauses import is_paused

CONFIG=ROOT/'config'
RESULTS=CONFIG/'market-archive-results.v1.json'
ATTEMPTS=CONFIG/'market-archive-attempts.v1.json'
ATHENA=CONFIG/'market-archive-athena.v1.json'
BULK=CONFIG/'market-bulk-archive-results.v1.json'

NEXT={
    160:'Public Intel and reference-domain 2016 CDX requests returned HTTP 504. Decodo returned an incomplete index response. A matching CDX locator and WARC byte range remain open.',
    161:'June 2016 Intel France replay verified. Extend to the tracked domains only with a replay timestamp and verified original domain.',
    165:'The public HTTP Archive tables have a BigQuery free tier. An approved project and byte estimate are still needed before running a no-charge query.',
    166:'Eight independently scaled worldwide Explore CSVs cover 2016–2020. Weekly dates mark observations. The CSVs omit publication dates. The 2021 export is still open.',
    168:'Older editions and the matching survey questionnaire schema remain separate release checks.',
    172:'The captured scope is collector-day snapshots and native MRT aggregate counts. Global coverage and more snapshots require a separate bounded plan.',
    173:'The captured scope is one 2016 Wikidata revision. More tracked entity IDs need a reviewed cohort and revision cutoff.',
    174:'The Companies House public register and original ARM TM01 PDF were verified together for 6 January 2016. Broader company coverage requires a scoped filing-history route.',
    175:'The official catalogue lists both 2026 historical Parquet files at roughly 867 MB and 882 MB. Choose partitioned retrieval or a scoped export with disk and scan limits.',
    179:'The 2016 CMF archive returned an index without matching statement files. Decodo returned an incomplete response. Select issuer and reporting month in the official archive.',
    180:'The 2016 follow-up is closed because manual and programmatic access are unavailable to the project.',
    181:'The new capture covers the DG Competition antitrust export scoped to 2016 last decisions. Merger, state-aid and other categories remain separate.',
    185:'The 2016–17 CADE link redirected to the federal organization catalogue. Decodo returned an error. Locate the case dataset or official decision download.',
    186:'The originally listed order paths returned HTTP 404 and Decodo returned a gateway error. A separate publisher case-order PDF was checked directly.',
    188:'CourtListener public bulk opinions and API access are distinct from RECAP document and archive coverage. A scoped credential or eligible download remains open.',
    189:'Decodo rendered the public Safety Gate interface. A verified alert export or 2016 weekly original remains open.',
    192:'The attempted bounded 2016 PRODCOM JSON-stat route returned HTTP 404. Select the current dataflow and native historical product codes.',
    193:'The 2023-vintage official BDS exports contain historical observations. Update from a later edition when published.',
    196:'The OSHA data landing page returned HTTP 403 and legacy enforcement-data links redirected to the new DOL portal. A current public bulk archive or supported credential remains open.',
    197:'The captured TRI scope is the 2016 Basic Plus facility/chemical release summary for California, New York and Texas. Other states, tables and editions remain open.',
    199:'Use the verified-emissions and allowances distribution linked from the EEA data record. The outer datastore folder contains large unrelated distributions.',
    200:'The stored token worked for France actual total load. January 2016 covers 743 of 744 hours. The API returned no observations for the one missing hour.',
    202:'The recovered IRENA capacity report is a published 2016–2025 table edition. The structured IRENASTAT generation and capacity query remains separate.',
    203:'The official monthly summary contains 12 months of 2016. Carrier and origin/destination segment data remain open through the TranStats selector.',
    206:'The recovered OICA edition is contemporary. The legacy 2016 PDF path redirected to HTTP 404.',
    208:'A bounded official Japan TiVA series was attempted. Decodo discovered the ICIO archive link, whose separate binary response returned HTTP 403.',
    211:'Decodo and direct checks rendered PPI search or custom-query pages. An official project-level export with an explicit year range remains open.',
    212:'Decodo exposed IMF documentation and coverage workbooks. The bilateral investment-position export requires selected reporter, counterpart and vintage.',
    213:'Decodo rendered the FAO FPMA tool without a data link. Export actual market/commodity prices with currency, price type and market level.',
    216:'The recovered CELLAR scope is one published legal-expression RDF graph. Legal text and legislative event history are separate tasks.',
    217:'The stored api-data-gov key returned 1,464 January 2016 EPA matches. The first five document records were posted on 4 January 2016. Full pagination, docket details, comments and attachments remain open.',
    218:'The captured WTO page is one official dispute history. Complete documentary and bulk case coverage remain open.',
    219:'The captures are first pages, not full-year coverage. The provider paginates both filing and contribution results.',
    222:'The attempted OECD CRS 2016 dataflow route returned HTTP 404. Identify the current version and donor, sector and recipient dimensions.',
    223:'The 2016 official LAADS catalogue lists original VNP46A2 tile files. Select approved tiles and access credentials before downloading imagery.',
    224:'The public Landsat catalogue identifies download methods. Scene selection, storage scope and required credentials remain open.',
    225:'Copernicus OData returned a product catalogue record. Select actual Sentinel imagery and verify credentialed original download before counting imagery as captured.',
    226:'The supplied ChileCompra archives contain purchase-order lines issued in 2016. Standalone tender exports remain open.',
    227:'The official 2016 Case Files download returned an HTML application shell. Confirm the actual bulk file and distinct TSDR access.',
    228:'FCC EAS grant search returned HTTP 403 and a Decodo gateway error. A permitted grant and exhibit export is still needed.',
    230:'ITU DataHub permits noncommercial reuse. Permission for the project use remains unresolved.',
    231:'PyPI public tables have a BigQuery free tier. An approved no-charge query project and bounded daily partition estimate are needed.',
    233:'The official CDC WONDER form requires a verified grouped mortality export with rate units and suppression flags.',
    235:'The CDC FluView application and Decodo probe exposed public viewer pages. Native ILINet and laboratory export contents remain open.',
    237:'RESP-NET can provide a bounded recent-season sample. A 2016 FluSurv-NET export and complete clinical scope remain open.',
    239:'The 2016 NHIS and BRFSS originals are distinct archives. Survey rows use selected native fields and published weights.',
    245:'The recovered WHO workbook is WUENIC input documentation and source data. Separate final estimates and Joint Reporting Form exports remain open.',
    246:'Published annual epidemiological report scope. The separate ECDC Atlas export remains open.',
    247:'2016 public EARS-Net and ESAC-Net reports were checked as separate documents. Downloadable machine-readable tables remain a separate scope.',
    248:'The supplied VAERS annual packages cover 2016–2025. The report, symptom and vaccine files are available together for each year.',
    250:'The original filings and amendments are declarations of beneficial ownership. Additional issuers, forms and amendments require scoped EDGAR collection.',
    252:'The 2016 gap is accepted. The earliest year reported available under current access is 2017. The first verified notice export is still open.',
    253:'The issuer event history PDFs show filing and effective dates. Use the first-of-month checklist for subsequent filing months. Individual insider trades and holdings use separate reports.',
    254:'Decodo rendered the FCA NSM search interface. An official PDMR document export for the tracked issuers remains open.',
    255:'Decodo rendered the CNMV legacy portal. Retrieve issuer-specific records from both archive versions.',
    256:'Decodo rendered NBIM latest positions despite the 2016 query parameter. Use an official export with a verified reporting year.',
    257:'Decodo recovered four original public member pages for the May 2016 edition. The full PDF and current CSV were unavailable in the tested routes.',
    258:'House commercial-use and filer retention conditions require a permissible route before collection.',
    259:'Senate acknowledgement, use restrictions and retention remain subject to a permitted project-specific route.',
    260:'OGE eligible public records, filer reporting groups and retention need a permitted project-specific route.',
    261:'HATVP reuse and retention remain open. Structured open data starts in 2017, with earlier PDF evidence handled independently.',
    263:'AMF use conditions and the native 2016 retention scope need a documented permissible export.',
    266:'The official FERC viewer served its download index. Quarter link tests returned HTTP 404 and Decodo returned a gateway error. The correct post-Q2 2013 transaction and contract export remains open.',
    267:'The 2016 METI/e-Stat machinery yearbook includes published industrial tables. Dedicated extraction of robots, semiconductor equipment and machinery series remains separate.',
    271:'The 2016 publication uses the earlier MHLW methodology. Later monthly files and the 2019 break require separate editions and field mapping.',
}


def load(path):
    return json.loads(path.read_text()) if path.exists() else {}


def escape(value):
    return ' '.join(str(value).split()).replace('|','\\|')


def overlay(original):
    results=load(RESULTS)
    audit=load(ATTEMPTS)
    athena=load(ATHENA)
    bulk=load(BULK)
    verified={(r['source'],r['dataset']):r for r in athena.get('partitions',[])}
    per_source=defaultdict(list)
    totals_by_partition=defaultdict(int)
    for key,item in results.items():
        per_source[item['id']].append(item)
        if item.get('manifest'):
            totals_by_partition[(item['source'],item['dataset'])]+=item['records']
    verified={key:row for key,row in verified.items() if row['records']==totals_by_partition[key]}
    rows=[]
    totals=defaultdict(int)
    for line in original.splitlines():
        match=re.match(r'^\| (\d+) \| (.*?) \| (.*?) \| (.*) \|$',line)
        if not match:
            continue
        n,name,past,official=match.groups()
        number=int(n)
        proofs=[r for r in per_source[number] if 'raw' in r]
        checks=[(r,verified.get((r['source'],r['dataset']))) for r in proofs]
        captured=[(row,check) for row,check in checks if check]
        if number in PAID_EXCLUSIONS:
            state='Excluded from collection'
            details=PAID_EXCLUSIONS[number]+'. Verified absent from active collection and metadata queues.'
            links={
                232:'[GTA data products and access](https://globaltradealert.org/data-access)',
                262:'[ASX company news fees and licensing](https://www.asx.com.au/connectivity-and-data/information-services/company-news)',
            }
            official=links[number]
            totals['excluded']+=1
        elif is_paused(f'market_source_{number}'):
            state='Paused at owner request'
            details='Daily collection and historical backfill are paused.'
            totals['paused']+=1
        elif captured:
            state='Published in Athena'
            partitions = {(r['source'], r['dataset']): check for r, check in captured}
            details=', '.join(f"{check['records']:,} {'row' if check['records']==1 else 'rows'} in {dataset}"
                              for (_,dataset),check in partitions.items())+'. '+NEXT.get(number,'')
            totals['published']+=1
        elif n in bulk:
            release=bulk[n]
            state='Published in Athena'
            details=f"{release['records']:,} rows in {release['database']} from {len(release['archives'])} verified originals. "+NEXT.get(number,'')
            totals['published']+=1
        elif proofs:
            state='S3 captured, Athena verification open'
            details=', '.join(f"{r['records']:,} parsed rows in {r['dataset']}" for r in proofs)+'. '+NEXT.get(number,'')
            totals['retained']+=1
        else:
            state='No verified raw'
            details=NEXT.get(number,past)
            totals['open']+=1
        failed=[r.get('error') for r in per_source[number] if r.get('error')]
        if failed:
            details+=' File checks returned '+', '.join(dict.fromkeys(failed))+'.'
        discovery=audit.get(n,{}).get('decodo')
        if discovery:
            details+=f" Decodo {discovery['state'].replace('_',' ')}."
        if proofs:
            records=' '.join(dict.fromkeys(r['raw'].get('archive_s3_uri') or r['raw']['s3_uri'] for r in proofs))
            details+=' Original S3 '+records
        rows.append(f'| {n} | {name} | {state} | {escape(details)} | {official} |')
    publication=''
    if athena:
        publication=(f"\nVerified Athena releases cover {sum(r['records'] for r in athena['partitions']):,} rows in "
                     f"{len(athena['partitions'])} partitions of {athena['table']}. The most recent query was {athena['query_id']}.\n")
    return '\n'.join([
        '# Market workbook sources without verified raw evidence',
        '',
        f'Follow-up of {len(rows)} sources from the initial review. Updated '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')+'.',
        '',
        f"{totals['published']} sources now have verified Athena rows, {totals['retained']} have S3 originals awaiting Athena verification, "
        f"{totals['excluded']} paid routes were excluded, {totals['paused']} sources are paused, and {totals['open']} active sources still lack verified raw evidence.",
        publication,
        'The [first-of-month download checklist](market-monthly-download-checklist.md) lists the remaining manual exports and release checks.',
        '',
        '| ID | Source | Status | Follow-up evidence and remaining scope | Official route |',
        '| --- | --- | --- | --- | --- |',
        *rows,'',
    ]),totals


def main():
    from market_source_status import OVERVIEW, REVIEW, report_lines
    _,original=report_lines()
    review,totals=overlay(original)
    REVIEW.write_text(review)
    title='MARKET WORKBOOK ARCHIVE FOLLOW-UP\n'
    end='END MARKET WORKBOOK ARCHIVE FOLLOW-UP\n\n'
    overview=OVERVIEW.read_text()
    if overview.startswith(title):
        overview=overview.split(end,1)[1]
    summary=(title+
             f"Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
             f"  Follow-up of the 68 unresolved additions yielded {totals['published']} additional Athena-verified source families and {totals['retained']} with originals awaiting Athena verification.\n"
             f"  Excluded {totals['excluded']} paid routes and retained {totals['open']} sources without qualifying raw evidence for review.\n"
             '  See market-sources-without-raw-evidence.md for the exact dataset, original S3 reference and any remaining scope.\n\n')
    OVERVIEW.write_text(summary+end+overview)
    print(dict(totals))


if __name__=='__main__':
    main()
