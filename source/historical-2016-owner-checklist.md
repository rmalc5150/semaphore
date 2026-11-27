# 2016 backfill weekday checklist

Starts **Monday, 23 November 2026 UTC**. The schedule covers 36 account, selection, permission, and browser-download items. Monday and Tuesday have nine items each. Wednesday has 10 and Thursday has eight. Friday is available for replies, blocked downloads, and handing files back to Codex. I put requests that can take time on Monday and grouped related work together. [Full 2016 audit](historical-2016-capture-audit.md)

For each download, give Codex the source ID, untouched file, provider URL, date filters, and any publication or revision date the provider shows. For credentials, share the location in the project’s secrets store. If existing access is insufficient or the archive has no result, record what the provider said and move to the next item. Use existing access and free archives throughout this checklist.

## Monday, 23 November — Accounts and first exports

- [x] **011 Finlight.** Your API test confirmed 2016 access. The project key reproduced your result, and the configured sector queries returned January 2016 articles. The backfill is a collector task. [Audit and evidence](historical-2016-capture-audit.md)
- [x] **200 ENTSO-E.** The stored `entsoe` token worked for France actual total load. The January 2016 test verified 729 native load blocks in Athena. [Audit and evidence](historical-2016-capture-audit.md)
- [x] **217 Regulations.gov.** The stored `api-data-gov` key worked for EPA documents posted in January 2016. The first response was saved and five records were verified in Athena. [Audit and evidence](historical-2016-capture-audit.md)
- [ ] **231 PyPI downloads.** Provide an approved BigQuery project and name the packages for a single 2016 partition test. [PyPI public table](https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=pypi&t=file_downloads&page=table)
- [x] **166 Google Trends.** The 2016 exports are archived. Four later exports extend weekly coverage through 2020, bringing Athena to 1,044 observations. The 2021 historical export is still open. [Audit and evidence](historical-2016-capture-audit.md)
- [x] **248 VAERS.** The 2016–2025 ZIPs, including all three native tables per year, are archived and verified in Athena. [Audit and evidence](historical-2016-capture-audit.md)
- [ ] **226 ChileCompra.** Both semesters of 2016 purchase-order data for four sectors are archived. Select **Licitaciones** for the remaining standalone tender exports. [ChileCompra order and tender downloads](https://datos-abiertos.chilecompra.cl/descargas/ordenes-y-licitaciones)
- [x] **004 HKEX prices.** 2016 gap accepted. The earliest year reported available under current access is 2017. [HKEX Daily Quotations](https://www.hkex.com.hk/eng/stat/smstat/dayquot/qtn.asp)
- [x] **252 HKEX Disclosure of Interests.** 2016 gap accepted. The earliest year reported available under current access is 2017. [HKEX Disclosure of Interests](https://www2.hkexnews.hk/Shareholding-Disclosures/Disclosure-of-Interests?p=1&sc_lang=en)

## Tuesday, 24 November — Market disclosures, archive downloads, and scope

- [ ] **253 Canada SEDI individual insider transactions.** The issuer event history for 2016–2025 is already in Athena. For the separate transaction evidence check, run a January 2016 insider transaction report for a tracked issuer or insider and retain the original report and search selections. [SEDI public reports guide](https://www.sedi.ca/sedi/new_help/english/public/PDF_en/Viewing_Public_Reports-SEDI_%28FINAL%29.pdf)
- [ ] **254 FCA National Storage Mechanism.** The original notice index is in Athena and includes 2016 publications. The separate 2016 filing-document check remains open. [FCA National Storage Mechanism](https://www.fca.org.uk/markets/primary-markets/regulatory-disclosures/national-storage-mechanism)
- [x] **255 Spain CNMV.** The one-issuer 2016 pilot is complete. Twelve original legacy PDFs and their dated index records were verified in S3 and processed in Athena. [CNMV consultation](https://www.cnmv.es/portal/Consultas/Directivos-Consulta)
- [x] **256 Norges Bank holdings.** The 2015 opening snapshot is now in Athena alongside the December 2016 and subsequent holdings exports. [NBIM holdings](https://www.nbim.no/en/investments/all-investments/)
- [x] **266 FERC Electric Quarterly Reports.** All 2,217 native Q1 2016 filing packages are verified in S3. Their four data tables and 35,415,400 row-level metadata records are in Athena. [FERC EQR](https://ferc.gov/power-sales-and-markets/electric-quarterly-reports-eqr)
- [x] **189 EU Safety Gate.** Verified the earliest saved weekly report on January 8, 2016. Weekly originals and monthly XML exports are retained and queryable in Athena. [Safety Gate weekly reports](https://ec.europa.eu/safety-gate-alerts/screen/webReport)
- [x] **235 CDC FluView.** Official ILINet and laboratory CSVs for both pilot seasons and the 2016–October 2026 extract are retained and queryable in Athena. [CDC FluView](https://gis.cdc.gov/grasp/fluview/FluPortalDashboard.html)
- [ ] **121 Open Supply Hub.** Choose countries and a supplier or facility cohort. Confirm any existing access to an authorized 2016 archive or predecessor inventory. [Open Supply Hub API](https://info.opensupplyhub.org/api)
- [ ] **123 Global Energy Monitor.** The current asset and entity snapshots are in Athena. Choose the trackers, geographies, and facilities for the separate 2016 ownership check. [GEM Ownership API](https://api.globalenergymonitor.org/redoc)

## Wednesday, 25 November — Dataset scope and exports

- [ ] **128 IEA Global EV Outlook.** Confirm whether the public 2016 report covers what you need. If you already have authorized bulk access, specify the countries and measures for that separate export. [IEA Global EV Outlook 2016](https://www.iea.org/reports/global-ev-outlook-2016)
- [ ] **211 World Bank PPI.** Download the provider’s project-level data and codebook. Specify the countries and sectors to check for 2016 project events. [World Bank PPI Data](https://ppi.worldbank.org/en/ppidata)
- [ ] **212 IMF Direct Investment Positions.** Select one reporting economy and counterpart for 2016. Export the bilateral series with direction, equity and debt components, and edition information. [IMF DIP](https://data.imf.org/en/Datasets/DIP)
- [ ] **213 FAO FPMA.** Export 2016 prices for one country, market, commodity, and price type. Keep currency, unit, and the exact market selection. [FAO price tool](https://www.fao.org/giews/food-prices/price-tool/en/)
- [ ] **222 OECD CRS.** Export 2016 records for one donor, recipient, and sector. Include the code lists and indicate whether the values are commitments or disbursements. [OECD CRS](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.DCD.FSD&df%5Bds%5D=DcdDisseminateFinalDMZ&df%5Bid%5D=DSD_CRS%40DF_CRS&lc=en)
- [ ] **223 NASA Black Marble.** Specify one site or tile and a 2016 acquisition window. Confirm there is an Earthdata account authorized for the LAADS download. [NASA VNP46A2](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2)
- [ ] **224 USGS Landsat.** Provide one area, a 2016 date window, and the required product. Confirm the permitted project access for the original scene. [USGS Landsat data access](https://www.usgs.gov/landsat-missions/landsat-data-access)
- [ ] **225 Copernicus Sentinel.** Choose one area, a 2016 acquisition window, and the Sentinel product level. Confirm the account that can download the original SAFE package. [Copernicus Data Space](https://dataspace.copernicus.eu/)
- [ ] **116 MarineTraffic.** Check whether any existing entitlement covers 2016 track or port-call exports. If it does, provide one port or vessel and the allowed archive window. [MarineTraffic archive documentation](https://servicedocs.marinetraffic.com/tag/Vessel-Historical-Track/)
- [ ] **188 CourtListener / RECAP.** Choose a 2016 federal docket and one document number. Confirm which existing access covers the document and provide the original if available. [RECAP](https://www.courtlistener.com/recap/)

## Thursday, 26 November — Permission and retention checks

- [ ] **228 FCC Equipment Authorization.** Choose one tracked device with a 2016 grant and provide its FCC ID. If available through permitted access, save the grant and a linked exhibit. [FCC grants search](https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm)
- [ ] **230 ITU DataHub.** Ask for written confirmation that the intended use is permitted for the selected 2016 indicators and countries. [ITU DataHub](https://datahub.itu.int/)
- [ ] **233 CDC WONDER.** Export one approved grouped 2016 mortality table. Include the selected cause grouping, geography, age groups, denominators, and suppression flags. [CDC WONDER mortality](https://wonder.cdc.gov/deaths-by-underlying-cause.html)
- [ ] **258 US House disclosures.** Confirm that the intended project use is permitted. If confirmed, check the 2016 search for one tracked filer and save an original plus its index entry. [House disclosure portal](https://disclosures-clerk.house.gov/FinancialDisclosure)
- [ ] **259 US Senate disclosures.** Confirm that the intended project use is permitted. If confirmed, check one tracked filer’s 2016 record and preserve an available original and dated index. [Senate eFD](https://efdsearch.senate.gov/)
- [ ] **260 US Office of Government Ethics.** Confirm permitted use, then check one named 2016 official in the retained public archive. Use Form 201 only if that report requires a request and your use is eligible. [Office of Government Ethics](https://www.oge.gov/)
- [ ] **261 France HATVP.** Pick one official and check whether a permitted 2016 declaration PDF remains public. Save its original publication listing if available. [HATVP public declarations](https://www.hatvp.fr/consulter-les-declarations/?anchor=open-data)
- [ ] **263 France AMF BDIF.** Confirm permitted project use and check one tracked issuer for a retained 2016 director transaction declaration. Save the actual notice and dated result. [AMF BDIF](https://bdif.amf-france.org/)

## Friday, 27 November — Finish and hand off

Send Codex the completed files, credential locations, and any provider replies. Keep open items with their specific blocker so they can be picked up without repeating the search.
