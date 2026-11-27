"""Render the full catalog's credential requirements; never handles key values."""
from collections import Counter
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Group rows by account/provider, not by the number of catalog entries or secrets.
GROUPS = [
 ('eodhd',[2,3],'stored','API token','Use existing EODHD secret; verify historic/delisted-security entitlement.','https://eodhd.com/financial-apis/'),
 ('edinet',[8],'stored','Subscription key','Use existing EDINET key.','https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0110.html'),
 ('finlight',[11],'stored','API key','Use existing finlight-api-key in newKeys; archive availability is separate.','https://docs.finlight.me/'),
 ('openfda',[17,18],'stored_optional','Optional API key','Existing FDA secret is configured; optional for basic requests, useful for quota.','https://open.fda.gov/apis/authentication/'),
 ('fda_dashboard',[32,33,34,35],'stored','Authorization user + key','One existing FDA-Data credential pair covers these dashboard routes.','https://datadashboard.fda.gov/ora/api/'),
 ('fda_enforcement',[36],'stored','Authorization user + key','Existing FDA-Enforcement credential pair.','https://www.accessdata.fda.gov/scripts/ires/'),
 ('fda_productcodes',[37],'stored','Authorization user + key','Existing FDA-ProductCodes credential pair.','https://www.accessdata.fda.gov/scripts/ora/pcb/'),
 ('google_patents',[39],'configured_identity','AWS/Google workload identity','No downloaded API key. Verify Google federation authorizes the new c7i IAM role before moving this job.','https://cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds'),
 ('uspto',[40,41,63,64],'stored','ODP API key','Reuse existing USPTO key; these entries are not four independent key applications.','https://data.uspto.gov/apis/getting-started'),
 ('reddit',[59],'paused_stored','OAuth client ID + secret and approved data access','Credentials are stored. Source remains paused; API approval and permitted scope are separate.','https://support.reddithelp.com/hc/en-us/articles/14945211791892-Reddit-Data-API-Wiki'),
 ('dataforseo',[60],'stored','API login + API password/basic authorization','Existing dataForSEO secret has login and encoded authorization; not a new API key.','https://docs.dataforseo.com/v3/auth/'),
 ('decodo',[81],'stored','Web Scraping API credential','Existing proxies secret contains decodo-web-scraping. Access layer, not an independent data publisher.','https://docs.decodo.com/'),
 ('eia',[55],'stored','API key','Reuse existing EIA key for the API. Generator archive downloads (53,54) do not require it.','https://www.eia.gov/opendata/register.php'),
 ('sam',[62],'stored','SAM.gov API key','Existing key is stored; account allowance still needs verification.','https://open.gsa.gov/api/get-opportunities-public-api/'),
 ('comtrade',[51],'obtain','Subscription key','Create account, My Comtrade > My API Portal > Generate API Key. Preview without a key is limited.','https://uncomtrade.org/docs/api-subscription-keys/'),
 ('fred_alfred',[66],'obtain','FRED API key','Create/sign in to a FRED account and request one key for FRED and ALFRED/vintage endpoints.','https://fred.stlouisfed.org/docs/api/api_key.html'),
 ('ember',[70],'obtain','API key','Register for the electricity-data API and verify the email.','https://ember-energy.org/data/api/'),
 ('wto',[71,72,73],'obtain','WTO API subscription key(s)','Register at the WTO portal; enable each needed API product. One account may require separate product subscriptions/keys.','https://apiportal.wto.org/'),
 ('epo_ops',[74],'obtain','Consumer key + consumer secret','Register an EPO developer application for OPS, then obtain OAuth client credentials.','https://www.epo.org/en/searching-for-patents/data/web-services/ops'),
 ('copernicus',[75],'obtain','CDS personal access token','Create CDS account, accept each requested dataset licence and copy the profile PAT.','https://cds.climate.copernicus.eu/how-to-api'),
 ('ucdp',[78],'obtain','Access token','Request API access from the maintainer using the instructions in the official documentation. Do not assume older anonymous examples still work.','https://ucdp.uu.se/apidocs/'),
 ('nice',[88],'obtain','Syndication API key and content licence','Apply for reuse/API access describing this commercial financial research use. Public webpages are a separate route.','https://www.nice.org.uk/reusing-our-content/nice-syndication-api'),
 ('opendart',[98],'obtain','Authentication key','Register at OpenDART and request an authentication key.','https://engopendart.fss.or.kr/uss/umt/EgovMberInsertView.do'),
 ('census',[118],'obtain','Census API key','Request and activate a Census key. Plan a keyed production collector; older keyless examples are not an access guarantee.','https://api.census.gov/data/key_signup.html'),
 ('usda_fas',[125],'obtain','FAS API key','Sign in to the FAS data portal and retrieve the PSD/Open Data API key.','https://apps.fas.usda.gov/opendataweb/home'),
 ('meta_ads',[131],'obtain','App credentials and access token','Complete Meta developer/identity and Ad Library access steps; obtain the token for the approved Ad Library scope.','https://www.facebook.com/ads/library/api/'),
 ('tiktok_ads',[132],'obtain','Approved app client key + secret/access token','Apply specifically for Commercial Content API access; approval and permitted use are prerequisites.','https://developers.tiktok.com/products/commercial-content-api'),
 ('linkedin_ads',[133],'obtain','Approved Ad Library API product + app credentials','Request the external Ad Library API product from LinkedIn developer portal; generic Marketing API access is not sufficient.','https://www.linkedin.com/blog/engineering/trust-and-safety/enhancing-transparency-with-linkedins-ad-library'),
 ('x_ads',[134],'obtain','Developer app bearer token','Create a developer app and use the Ads Repository export API instructions; verify account/product access.','https://help.x.com/en/business-and-advertising/ads-transparency'),
 ('openalex',[142],'obtain','Verified-email API key for bulk/cursor access','Create an account, verify the email, and obtain a key from settings. Current cursor access beyond page one requires a key.','https://help.openalex.org/api/authentication/'),
 ('kaken',[153],'obtain','NII/CiNii application ID','Register the application ID used by KAKEN; describe commercial use to NII as required by their guidance.','https://support.nii.ac.jp/en/kaken/api/api_outline'),
 ('cninfo',[92],'commercial_conditional','Provider-issued credentials if the commercial API is chosen','Public filing downloads are an alternative. No self-service key requirement has been verified for the chosen public route; request approved API access if needed.','https://webapi.cninfo.com.cn/'),
 ('importyeti',[114],'commercial_conditional','ImportYeti API key','Request API access; confirm volume, history and allowed storage/ML use. Free website access is not bulk API entitlement.','https://docs.importyeti.com/docs/getting-started'),
 ('importgenius',[115],'commercial_conditional','Enterprise API access token','Request an API-enabled plan and token from the implementation team; specify country and historical scope.','https://w3.importgenius.com/features/api-integration'),
 ('marinetraffic',[116],'commercial_conditional','Product-specific API key','Request historical vessel-track and port-call API entitlements, not only a website login.','https://servicedocs.marinetraffic.com/tag/Vessel-Historical-Track/'),
 ('kpler',[117],'commercial_conditional','Provisioned API credentials/token','Ask Kpler for cargo-flow API access and authentication for the contracted product; do not assume a MarineTraffic key covers it.','https://developers.kpler.com/'),
 ('euromonitor',[130],'commercial_conditional','API-enabled Passport credentials/subscription and OAuth token','Ask the account team for Statistics API entitlement and the credentials required by the current portal.','https://www.euromonitor.com/solutions/passport/connect/api'),
 ('sensortower',[135],'commercial_conditional','Provider-issued API credential; exact product scope to confirm','Request Sensor Tower/Pathmatics advertising API and historical entitlements. Exact credential format is not confirmed from public documentation.','https://sensortower.com/'),
 ('dealroom',[140],'commercial_conditional','Premium API key','Request the Premium API key and confirm use restrictions and historical coverage.','https://knowledge.dealroom.co/knowledge/dealroom-api-1'),
 ('altmetric',[157],'commercial_conditional','Details Page API key; Explorer key + secret if needed','Request commercial access appropriate to the endpoints; free academic permission is not a commercial entitlement.','https://docs.altmetric.com/details-page-api/licensing/'),
 ('ncbi',[25],'optional','NCBI API key','Optional for higher E-utilities throughput; email/tool identification and a conservative no-key limit can be used initially.','https://www.ncbi.nlm.nih.gov/books/NBK25497/'),
 ('bls',[57],'optional','BLS API registration key','Optional for registered API limits; public files and unregistered API access exist.','https://www.bls.gov/developers/home.htm'),
 ('github',[44],'paused_optional','Read-only GitHub token','Optional higher-limit credential; source stays paused and no token acquisition is required until you resume it.','https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api'),
 ('openaire',[144],'optional','OpenAIRE AAI account/access token','Authenticated access is recommended for production limits; use current OpenAIRE guidance or public bulk releases.','https://graph.openaire.eu/docs/7.2.0/apis/authentication/'),
 ('semantic_scholar',[148],'optional','Academic Graph API key','Recommended for sustained collection; some endpoints require it, many public endpoints do not.','https://www.semanticscholar.org/product/api'),
 ('huggingface',[156],'optional','Read-only Hugging Face token','Not needed for basic public metadata; useful for authenticated quotas or explicitly permitted gated assets.','https://huggingface.co/docs/hub/security-tokens'),
 ('wsts',[82],'license_not_key','No key/login for public Blue Book history; review reuse terms','WSTS now offers four decades of regional monthly billings as a free Excel download without login. Detailed products may have separate terms; no purchase is needed for this public history.','https://www.wsts.org/'),
 ('semi',[83],'license_not_key','Report/data licence; no general API key confirmed','Use public releases; request a licence if detailed historical equipment data are required.','https://www.semi.org/en/products-services/market-data'),
 ('ifr',[84],'license_not_key','World Robotics report/dataset licence','Public summaries are not the full licensed dataset; ask for machine-readable access and permitted use.','https://ifr.org/worldrobotics/'),
 ('iea_ev',[128],'license_not_key','IEA account/terms if the selected download requires them','The current Global EV Data Explorer is CC BY 4.0. A free IEA account may be used for downloads; no general API key is established for this public route.','https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer'),
 ('opensupplyhub',[121],'obtain','Approved API access + token','Apply for API access; after approval generate a token in My Account > Settings > API. Confirm commercial terms.','https://info.opensupplyhub.org/resources/api-documentation'),
]

PUBLIC = {
1:'https://www.gleif.org/en/lei-data/gleif-api',4:'https://www.hkex.com.hk/Market-Data',5:'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',6:'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',7:'https://www1.hkexnews.hk/search/titlesearch.xhtml',9:'internal:disclosure_candidates',10:'internal:disclosure_documents',13:'public:configured-publisher-rss',14:'internal:personnel_archive',15:'https://clinicaltrials.gov/data-api/api',16:'https://euclinicaltrials.eu/',19:'https://www.ema.europa.eu/en/medicines/download-medicine-data',20:'https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency',21:'https://www.pmda.go.jp/english/',22:'https://health-products.canada.ca/api/notice-of-compliance/',23:'https://www.chictr.org.cn/',24:'http://www.chinadrugtrials.org.cn/',26:'https://europepmc.org/RestfulWebService',27:'https://europepmc.org/RestfulWebService',28:'https://www.crossref.org/documentation/retrieve-metadata/rest-api/',29:'https://api.coverage.cms.gov/docs/',30:'https://api.coverage.cms.gov/docs/',31:'https://data.cms.gov/',38:'https://api.reporter.nih.gov/',42:'https://docs.ted.europa.eu/api/latest/index.html',43:'https://api.usaspending.gov/',45:'https://www.nist.gov/robotics',46:'https://github.com/mlcommons',47:'https://www.saferproducts.gov/RestWebServices/',48:'https://www.federalregister.gov/developers/documentation/api/v1',49:'https://www.trade.gov/consolidated-screening-list',50:'https://www.usgs.gov/centers/national-minerals-information-center',52:'https://www.energy.gov/oe/energy-storage',53:'https://www.eia.gov/electricity/data/eia860m/',54:'https://www.eia.gov/electricity/data/eia860/',56:'https://oasis.caiso.com/',58:'https://ror.readme.io/docs/client-id',61:'https://docs.bsky.app/docs/api/app-bsky-feed-search-posts',65:'https://data.bis.org/help/tools',67:'https://stat.unido.org/unido-statistics-portal-api',68:'https://rplumber.ilo.org/',69:'https://portwatch.imf.org/',76:'https://power.larc.nasa.gov/docs/services/api/',77:'https://earthquake.usgs.gov/fdsnws/event/1/',79:'https://info.arxiv.org/help/api/user-manual.html',80:'https://opendata.nhsbsa.net/pages/api',85:'https://iea-pvps.org/',86:'https://www.g-ba.de/bewertungsverfahren/nutzenbewertung/',87:'https://www.has-sante.fr/jcms/p_3546197/fr/open-data',89:'https://www.cda-amc.ca/',90:'https://www.data.gouv.fr/datasets/open-medic-base-complete-sur-les-depenses-de-medicaments-interregimes/',91:'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177182.html',93:'https://data.stats.gov.cn/english/',94:'https://www.miit.gov.cn/',95:'https://www.nea.gov.cn/',96:'https://www.nhsa.gov.cn/',97:'https://www.mofcom.gov.cn/',100:'https://openapi.twse.com.tw/',101:'https://www.sw.nat.gov.tw/',102:'https://ibm.gov.in/',103:'https://www.esdm.go.id/',104:'https://www.gov.br/anm/pt-br/centrais-de-conteudo/dados-abertos',105:'https://www.gov.br/anm/pt-br/assuntos/arrecadacao',106:'https://api-comexstat.mdic.gov.br/',107:'https://www.cochilco.cl/',108:'https://www.sernageomin.cl/anuario-de-la-mineria-de-chile/',109:'https://snifa.sma.gob.cl/',110:'https://www.gob.pe/minem',111:'https://www.argentina.gob.ar/produccion/mineria/siacam',112:'https://geo.anm.gov.br/',113:'https://geocatmin.ingemmet.gob.pe/',119:'https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access',120:'https://climatetrace.org/data',122:'https://wiki.openstreetmap.org/wiki/Overpass_API',123:'https://api.globalenergymonitor.org/redoc',124:'https://www.eea.europa.eu/en/datahub',126:'https://abve.org.br/',127:'https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/estatisticas-frota-de-veiculos-senatran',129:'https://www.fao.org/faostat/en/#data',136:'https://www.ycombinator.com/companies',137:'https://www.techstars.com/portfolio',138:'https://500.co/companies',139:'https://www.antler.co/portfolio',141:'https://wefunder.com/',143:'https://support.datacite.org/docs/api',145:'https://api.biorxiv.org/',146:'https://developer.osf.io/',147:'https://developers.zenodo.org/',149:'https://documentation.abes.fr/aidethesesfr/accueil/index.html',150:'https://dadosabertos.capes.gov.br/',151:'https://resources.research.gov/common/webapi/awardapisearch-v1.htm',152:'https://cordis.europa.eu/about/dataextractions',154:'https://bv.fapesp.br/en/',155:'https://gtr.ukri.org/resources/GtR-2-API-v1.7.5.pdf',158:'multiple:university-technology-transfer-offices'
}


def build():
    registry=json.loads((ROOT/'config/constellation-source-registry.json').read_text())
    by_entry={}
    for group,entries,status,credential,action,url in GROUPS:
        for n in entries:
            if n in by_entry:raise ValueError('Duplicate credential row')
            by_entry[n]={'credential_group':group,'access_status':status,'credential':credential,'action':action,'reference':url}
    rows=[]
    for entry in registry['sources']:
        n=entry['catalog_entry']
        if n>158:
            continue
        access=by_entry.get(n)
        if not access:
            if n not in PUBLIC:raise ValueError('Missing catalog row '+str(n))
            access={'credential_group':None,'access_status':'public_route_no_key','credential':'No API key for the selected public route',
                'action':'Use public metadata, files, reports or approved web retrieval. This is not a claim that an undocumented/private API is available.', 'reference':PUBLIC[n]}
        row={'catalog_entry':n,'source_key':entry['source_key'],'source_name':entry['catalog_name'],**access,'historical_start_target':'2016-01-01'}
        if n==5:row['action']='Configure a truthful organization/contact User-Agent; SEC does not issue an EDGAR API key.'
        if n in (23,24):row['action']='No publisher API key confirmed for public pages. Decodo is an access layer already configured; do not interpret captcha/session barriers as missing API keys.'
        if n in (29,30):row['action']='CMS Coverage API removed its API-key requirement in 2024. Some endpoints still require acceptance of a licence/token.'
        if n==49:row['action']='Use public screening-list downloads initially; a trade.gov API route can separately require a data.gov key.'
        if n==58:row['action']='ROR client-ID registration is currently paused; it is an identifier, not a secret/authentication key. API/public dumps remain available.'
        if n==61:row['access_status']='paused_public';row['action']='Keep paused. The selected public AppView search route does not require buying or requesting an API key.'
        if n==67:row['action']='UNIDO documents a public API. A 403/bot challenge is an access issue, not evidence that an API key is needed.'
        if n in (82,83,84,128):pass
        rows.append(row)
    return rows


def main():
    rows=build()
    summary=dict(Counter(g[2] for g in GROUPS))
    result={'checked_on':'2026-10-26','catalog_entries':len(rows),'credential_group_counts':summary,'values_included':False,
        'scope':'Existing config/Secrets Manager presence plus current official access documentation. Presence does not verify token validity, historic entitlement or commercial ML rights.',
        'groups':[dict(zip(('group','catalog_entries','status','credential','action','reference'),g)) for g in GROUPS], 'sources':rows}
    (ROOT/'config/source-access-requirements.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    with (ROOT/'constellation/source-access-requirements.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# API credentials and access checklist — October 26, 2026','',
        f'This is a checklist for the {len(rows)} original catalogue entries still in scope. Entries share credentials and many public download routes need none. The list contains no secret values.',
        '',f"There are **{summary.get('obtain',0)} new priority credential/account groups**, **{summary.get('commercial_conditional',0)} commercial or conditional groups**, and **{summary.get('optional',0)} optional upgrade groups**. Some priority groups require app approval or a licence, rather than a single key. WTO product subscriptions can issue separate keys. Existing credentials and intentional pauses are listed separately.",
        '', '“New” means not configured in the audited integration secrets; use a credential you already own elsewhere if appropriate. Stored means a nonempty field was found, not that a new authentication or entitlement test passed. Public-route classifications do not certify a public API, historical completeness or commercial reuse rights.',
        '', '## Obtain or locate these credentials first','', '| Provider / catalog rows | Obtain | Action / official instructions |','|---|---|---|']
    for group,entries,status,credential,action,url in GROUPS:
        if status=='obtain':lines.append(f"| {group} ({', '.join(map(str,entries))}) | {credential} | {action} [Official source]({url}) |")
    for status,title in [('commercial_conditional','Commercial or conditional access'),('optional','Optional higher-throughput access'),('license_not_key','Licences and accounts, not API keys'),('paused_optional','Paused optional credentials')]:
        lines+=['','## '+title,'','| Provider / catalog rows | Access needed | Action / official source |','|---|---|---|']
        for group,entries,kind,credential,action,url in GROUPS:
            if kind==status:lines.append(f"| {group} ({', '.join(map(str,entries))}) | {credential} | {action} [Official source]({url}) |")
    lines+=['','## Already configured','', '| Provider / catalog rows | Credential present or configured | Status |','|---|---|---|']
    for group,entries,status,credential,action,url in GROUPS:
        if status in {'stored','stored_optional','paused_stored','configured_identity'}:lines.append(f"| {group} ({', '.join(map(str,entries))}) | {credential} | {action} |")
    lines+=['','## Every catalog entry','', 'For a public file/report route, “no key” does not promise a supported API. Where no supported API has been identified, implementation/access review is still pending. Paid, conditional and paused sources remain gated.', '', '| # | Source | Credential/access | Action / reference |','|---|---|---|---|']
    for row in rows:
        ref=row['reference'];link=f"[Source]({ref})" if ref.startswith('https://') else ref
        lines.append(f"| {row['catalog_entry']} | {row['source_name']} | {row['credential']} ({row['access_status']}) | {row['action']} {link} |")
    lines+=['','Store acquired values in AWS Secrets Manager; do not paste keys into this document or commit them to source files. Request only needed read access. Key acquisition does not authorize restarting Reddit, Bluesky or GitHub.', '', '## Important current access details','',
        '- [OpenAlex authentication](https://help.openalex.org/api/authentication/): a verified key is required for cursor paging beyond the first page.',
        '- [UCDP API](https://ucdp.uu.se/apidocs/): token access is now required; older anonymous examples are obsolete.',
        '- [CMS Coverage API](https://api.coverage.cms.gov/docs/): no API key, with separate licensing tokens on some routes.',
        '- [ROR client identification](https://ror.readme.io/docs/client-id): registration is paused and the client ID is not an authorization secret.',
        '- [UN Comtrade](https://uncomtrade.org/docs/un-comtrade-api/): preview is keyless; the full API requires an account/key.',
        '- Regional reports, startup directories and university technology-transfer collections often have no single API or universal credential. Their public routes remain individually auditable; a made-up “key requirement” would not solve access or historical gaps.',
        '', 'The machine-readable companion is `config/source-access-requirements.json`; the CSV is `constellation/source-access-requirements.csv`.']
    (ROOT/'constellation/API_ACCESS_CHECKLIST.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'credential_group_counts':summary,'catalog_rows':len(rows),'source_status_counts':dict(Counter(r['access_status'] for r in rows))}))


if __name__=='__main__':main()
