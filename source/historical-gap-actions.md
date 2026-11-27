# Historical gaps that need your action

21 November 2026 · UTC

Use this checklist for account access and scope decisions. The [full historical gap register](historical-gap-register.md) lists the date intervals, technical repairs, and evidence.

## Start here

### Google Patents BigQuery — historical catch-up

On 21 November 2026 at 16:53 UTC, C7 authenticated as the patent collector service account and completed the January 2016 BigQuery dry run. BigQuery estimated 47,135,127,425 bytes against the 50,000,000,000-byte cap. The C7 role is `constellation-backfill-worker` in AWS account `059416028963`.

- [x] In Google Cloud project `patent-research-508613` (project number `24037405713`), open **IAM & Admin → Workload Identity Federation**. Edit the AWS provider `optima-ec2` in pool `optima-patents-aws`.
- [x] Extend the provider condition to admit `arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/` as an additional allowed ARN prefix. Preserve the account restriction and the existing allowed controller role. If the current condition matches the original setup, use the expression below.
- [x] Verify that the C7 worker can impersonate `optima-patent-collector@patent-research-508613.iam.gserviceaccount.com`. The scoped **Workload Identity User** (`roles/iam.workloadIdentityUser`) member is listed below. The dry run verified effective access.

```text
assertion.account == '059416028963' &&
(
  assertion.arn.startsWith('arn:aws:sts::059416028963:assumed-role/lambdaEc2ForEc2Instance/') ||
  assertion.arn.startsWith('arn:aws:sts::059416028963:assumed-role/constellation-backfill-worker/')
)
```

```text
principalSet://iam.googleapis.com/projects/24037405713/locations/global/workloadIdentityPools/optima-patents-aws/attribute.aws_role/constellation-backfill-worker
```

The original job’s results became unavailable. The capped replacement query returned 41,413 publications and billed 47,135,588,352 bytes. All 14,500 saved publications matched by publication number and normalized content. The completed S3 manifest reuses the 29 existing raw batches and adds only the 26,913 missing publications.

Athena verified 41,413 distinct publications in `optima_patent_research.patent_backfill_publications` for `publication_month = '2016-01'` at 17:09 UTC on 21 November 2026. The collection and publication checkpoints both advanced to 1 February 2016. [Google Patents backfill operations](data-collection-processing/PATENT_BACKFILL_OPERATIONS.md)

The 21 November coverage audit found 69 published months from January 2021 through September 2026. The September release now contains 25,732 distinct publications. It reuses the 25,716 saved records and adds 16. September 24 is the latest publication date BigQuery supplies through the audit date.

On 21 November, the catch-up published 38,951 distinct publications for February 2016 and 51,616 for March 2016. Both checkpoints advanced to April 2016, leaving 57 months through December 2020. The controller’s `optima-patent-gap-catchup.timer` resumes under the existing 50 GB per-query ceiling and four-query UTC daily allowance. It verifies each monthly Athena release and stops at January 2021.

### OpenAlex — daily collection and backfill running

- [x] Obtain a working OpenAlex API key. [OpenAlex API authentication](https://help.openalex.org/api/authentication/)
- [x] Store the key in AWS Secrets Manager under `newKeys` → `openalex-api-key`. The field was verified on 21 November 2026.

The January 2016 probe returned 10 distinct works across two pages. The daily t3 job collects closed publication-date windows, and the C7 backfill imports the public works snapshot from the 2016 publication-date floor. A separate API catch-up lane covers dates between the snapshot and the daily origin. The current key returned an upgrade requirement for update-date queries. [Collection operations](data-collection-processing/RESEARCH_FEEDS.md)

### Japan KAKEN — application ID verified and collection running

- [ ] Describe the intended commercial use to NII before applying, as its registration guide requests. The guide provides the department contact and developer registration link. [NII developer registration](https://support.nii.ac.jp/en/cinii/api/developer)
- [x] Register for the CiNii application ID and store it under `newKeys` → `kaken-app-id`. The fiscal 2016 project query accepted the ID and reported 31,059 matches on 21 November 2026. [KAKEN API documentation](https://support.nii.ac.jp/en/kaken/api/api_outline)

The daily t3 collector snapshots projects active in Japan’s current fiscal year. The C7 backfill processes closed cohorts by research start fiscal year, beginning with FY2016. [Collection operations](data-collection-processing/RESEARCH_FEEDS.md)

### Finlight — 2016 archive access verified

- [x] The supplied API request returned 2016 articles. The project key reproduced the result and returned five articles from the configured sector queries on 4 January 2016.

The collector now has a separate 2016–2020 interval under its existing request budget. C7 completed 1 January and advanced the new cursor to 2 January 2016. The 4 January pilot independently published five articles in Athena. [2016 audit and raw evidence](historical-2016-capture-audit.md)

## Other feeds awaiting access or scope decisions

Work through these as the corresponding datasets are needed. For each, send the approved coverage and intended use along with the location of any credential you saved securely.

| Source | What you can provide |
| --- | --- |
| MarineTraffic | Confirm entitlement to historical vessel tracks and port calls, along with the date range, vessel or port scope, and allowed use. [MarineTraffic historical track documentation](https://servicedocs.marinetraffic.com/tag/Vessel-Historical-Track/) |
| Open Supply Hub | Confirm the desired geographic and date scope. Supply approved production API access or authorize a dated export that covers the required locations. [Open Supply Hub API](https://info.opensupplyhub.org/api) |
| Global Energy Monitor | Request access to the asset and ownership API, or approve named public tracker exports limited to their documented scope. [GEM Ownership Tracing API](https://api.globalenergymonitor.org/redoc) |
| IEA Global EV Data Explorer and Outlook | Confirm which countries and measures you need. If using the bulk Outlook 2026 product, confirm the applicable use terms and provide the authorized provider download. [IEA Global EV Outlook data product](https://www.iea.org/data-and-statistics/data-product/global-ev-outlook-2026) |
| Euromonitor Passport | Confirm Statistics API entitlement, series, markets, archive years, and permission for the intended use. [Euromonitor Passport API](https://www.euromonitor.com/solutions/passport/connect/api) |
| Meta Ad Library | Obtain approved Ad Library access for the intended countries and ad categories, then confirm the available archive years. [Meta Ad Library API](https://www.facebook.com/ads/library/api/) |
| TikTok Commercial Content | Confirm whether the available recent archive meets the requirement. For longer history, identify a permitted historical export or another approved source. The documented API retains ads until one year after they were last shown. [TikTok Commercial Content API](https://developers.tiktok.com/products/commercial-content-api) |
| LinkedIn Ad Library | Confirm access to the specific Ad Library API product and its historical date and geography scope. [LinkedIn Ad Library announcement](https://www.linkedin.com/blog/engineering/trust-and-safety/enhancing-transparency-with-linkedins-ad-library) |
| X Ads Repository | Obtain the DSA Ads Repository product permission for the existing app. Confirm the archive and geography needed for the intended use. [X Ads Transparency access](https://help.x.com/en/business-and-advertising/ads-transparency) |
| Sensor Tower / Pathmatics | Confirm the contracted advertising dataset, markets, years, and permitted historical export or API access. [Sensor Tower](https://sensortower.com/) |
| Dealroom | Confirm the licensed API or export, historical dataset scope, and permitted use. [Dealroom API access](https://dealroom.co/api/) |
| Altmetric | Obtain commercial rights for the exact endpoints and dates needed. [Altmetric API licensing](https://docs.altmetric.com/details-page-api/licensing/) |

Paid feeds previously deferred and the EDINET 2016 exclusion follow the decisions already recorded in the source overview. If a provider grants a narrower history than requested, record the grant and date range so the remaining gap stays visible.
