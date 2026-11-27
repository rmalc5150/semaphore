# Historical gap register

Historical gap audit completed 21 November 2026 12:17 UTC. The configured historical target starts 1 January 2016.

- **111 flagged intervals** longer than five days and **159 intervals of five days or less** across **11 sources**. Every interval appears below.
- **436 reviewed unavailable scopes** with documented reasons. These are retained coverage limitations.
- **748 separate EODHD windows** across **202 symbols** require coverage verification. Their exact dates appear under EODHD.

Each interval includes its start and excludes its end. Multiple query scopes can overlap. Dates are requested coverage windows. Provider event dates and a sample-based January 2016 audit are in the [data-source overview](data-source-overview.txt). [Current S3 audit and full receipt references](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/summary-reports/cf4a7f0cf7204ec598bdf9d36f1061b1.json).

Provider and account actions are in the [owner checklist](historical-gap-actions.md). The interval replays in this register are operational work.

## Open intervals by source

| Source | Flagged | Shorter | Total |
| --- | ---: | ---: | ---: |
| bioRxiv / medRxiv preprints | 17 | 0 | 17 |
| Copernicus ERA5 / ERA5-Land | 2 | 0 | 2 |
| DataCite dissertations, datasets, software and usage | 34 | 0 | 34 |
| Japan EDINET corporate filings | 0 | 47 | 47 |
| EMA CTIS | 11 | 0 | 11 |
| England NHSBSA prescribing data | 2 | 0 | 2 |
| IMF PortWatch shipping activity | 9 | 13 | 22 |
| South Korea FSS OpenDART | 1 | 0 | 1 |
| UK MHRA | 1 | 0 | 1 |
| WTO Timeseries API | 10 | 0 | 10 |
| Zenodo research artifacts and usage | 24 | 99 | 123 |

For an interval repair, compare the exact scoped checkpoint, retain original evidence, and verify the committed originals and applicable Athena readback. Document reviewed unavailability only when the evidence establishes it.

### bioRxiv / medRxiv preprints

- For duplicate provider IDs, replay narrower windows per repository with stable source identifiers and verify identities across page boundaries. Keep full-text artifact validation for records that require it.
- For access denials, proxy throttles, or provider 503s, use the authorized acquisition route and resume the affected windows after the documented cooldown. The medRxiv pre-launch exclusions below apply to medRxiv only.

**biorxiv (earlier capture scope)**

Scope identifier `biorxiv_medrxiv_preprints|C145|specialist_historical|bbc24b2e27b47b6d3d7c3712`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2018-09-01 | 2018-10-01 | 30 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2018-11-01 | 2018-12-01 | 30 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/3bf11476ba52d0458d25fbeff68692c8da82b5628d7d4877b1638efe49951c31.json) |
| 2019-10-01 | 2019-11-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2020-02-01 | 2020-06-01 | 121 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) + 1 in audit |
| 2020-07-01 | 2020-08-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2022-03-01 | 2022-04-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2022-06-01 | 2022-07-01 | 30 | Flagged | `source_http_503` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/74fa4c0ba386e41d34f85fe4f6b5b6bb09ec4b16f23c0e17207d964a71f37ac0.json) |
| 2022-08-01 | 2022-10-01 | 61 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/3bf11476ba52d0458d25fbeff68692c8da82b5628d7d4877b1638efe49951c31.json) + 1 in audit |
| 2023-05-01 | 2023-06-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2024-08-01 | 2024-09-01 | 31 | Flagged | `source_http_503` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/09c3a9b8596e1192b41af436f19c9f3a35e53b854c9f7afeccab471943c1f8cf.json) |

**biorxiv (raw-v2 capture scope)**

Scope identifier `biorxiv_medrxiv_preprints|C145|specialist_historical|565f037c544927851340d014`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-01-01 | 2017-06-01 | 517 | Flagged | `pdf_proxy_http_429`, `source_retries_exhausted` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/04a23447742086abb8b756919fe88c9c34ef206352485c37c22afaff8f158fab.json) + 10 in audit |

**medrxiv (earlier capture scope)**

Scope identifier `biorxiv_medrxiv_preprints|C145|specialist_historical|3540522538635609279083c7`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2022-04-01 | 2022-05-01 | 30 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/f34d4f535f817453e237e8fac9b6eda08cdfebb1570a20e9bd3fe0882ff9a238.json) |
| 2022-12-01 | 2023-01-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/f34d4f535f817453e237e8fac9b6eda08cdfebb1570a20e9bd3fe0882ff9a238.json) |
| 2025-11-01 | 2025-12-01 | 30 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2026-01-01 | 2026-02-01 | 31 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/e44460c1996d0dc7e1f95eb98deab8358f7e5094d7d15e903ab046560be85c6c.json) |
| 2026-03-01 | 2026-05-01 | 61 | Flagged | `additional_duplicate_provider_ids` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/aefd98e9f1f665202bd9b42a55ad0fd3cbb8133c81967b18f60d1373f8a761db.json) + 1 in audit |
| 2026-06-01 | 2026-10-01 | 122 | Flagged | `additional_duplicate_provider_ids`, `source_http_403` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-biorxiv_medrxiv_preprints.service/executions/3bf11476ba52d0458d25fbeff68692c8da82b5628d7d4877b1638efe49951c31.json) + 1 in audit |

### Copernicus ERA5 / ERA5-Land

- Resume the two failed ERA5 single-level requests in the same CDS dataset and geographic rectangles. Reuse their provider task IDs if still resumable and verify each dated result file before closing its scope.

**Johannesburg · reanalysis-era5-single-levels**

Scope identifier `copernicus_era5_era5_land|C075|specialist_historical|a8718a61a89014d9cb7a398d`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2024-12-01 | 2025-01-01 | 31 | Flagged | `source_http_500` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-copernicus_era5_era5_land.service/executions/fb8f7fbb6dccb18c7a19f9fb8a6e5658627c34cb7d8381d1932be316c275592e.json) |

**Shanghai · reanalysis-era5-single-levels**

Scope identifier `copernicus_era5_era5_land|C075|specialist_historical|059e896ca1dbebda78acb13e`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2020-07-01 | 2020-08-01 | 31 | Flagged | `source_http_500` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-copernicus_era5_era5_land.service/executions/aaafac1b2a1194eb652baf020be8a0f5d4da83854ae36936640babca17fb1f3d.json) |

### DataCite dissertations, datasets, software and usage

- Refresh only the impacted dissertation, dataset, or software date ranges. Use shorter date partitions with stable cursor ordering, validate DOI counts against the completed provider response, and retain originals for the replay.

**Resource type dataset**

Scope identifier `datacite_dissertations_datasets_software_and_usage|C143|specialist_historical|e5227279777d6de88fc3674f`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-11-01 | 2016-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/eb97219f0f0c620dd6b86af4b4ec48304348968efc3c30990ca4320bbccbc473.json) |
| 2017-11-01 | 2017-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/76b71ff903f5a265e679866bf1df75ebbbb6d300a18c5335aaecd48bf49275f7.json) |
| 2018-02-01 | 2018-03-01 | 28 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/a7001f70ad66930adfcf460d23244d96d81de13ad98feca36a41371ed80636de.json) |
| 2018-11-01 | 2018-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/289b0179e5a43c455a4e069c4d12635d42327d6b0982a635cb34886f9100415a.json) |
| 2019-07-01 | 2020-02-01 | 215 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8296bcb076424d8042e9465b4408406e0172895f372cfca82df4858d9145332e.json) + 2 in audit |
| 2020-04-01 | 2020-06-01 | 61 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8652dfb34653706273187ad9eb061e8adb77719393d4cef3c82a612ea3f20a81.json) |
| 2020-07-01 | 2020-10-01 | 92 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8652dfb34653706273187ad9eb061e8adb77719393d4cef3c82a612ea3f20a81.json) |
| 2020-11-01 | 2020-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/4e9860dac18abc8549215d86f4fd6ef294e024c5699438d1e1115e14a53ca7b4.json) |
| 2021-01-01 | 2021-02-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8296bcb076424d8042e9465b4408406e0172895f372cfca82df4858d9145332e.json) |
| 2021-03-01 | 2021-04-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8296bcb076424d8042e9465b4408406e0172895f372cfca82df4858d9145332e.json) |
| 2021-06-01 | 2021-11-01 | 153 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/4e9860dac18abc8549215d86f4fd6ef294e024c5699438d1e1115e14a53ca7b4.json) |
| 2021-12-01 | 2022-07-01 | 212 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/4e9860dac18abc8549215d86f4fd6ef294e024c5699438d1e1115e14a53ca7b4.json) + 1 in audit |
| 2022-08-01 | 2022-11-01 | 92 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/ebd77759afe801e533e11b1e9ef6ae9329fbf8ead5c777adb3e564c902ec9032.json) |
| 2022-12-01 | 2023-01-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/ebd77759afe801e533e11b1e9ef6ae9329fbf8ead5c777adb3e564c902ec9032.json) |
| 2023-05-01 | 2023-06-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/76b71ff903f5a265e679866bf1df75ebbbb6d300a18c5335aaecd48bf49275f7.json) |
| 2023-10-01 | 2023-11-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/876cb719f103b96b0e7a03894725f1421e2439d374099df25b691d826afe0395.json) |
| 2023-12-01 | 2024-03-01 | 91 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/8296bcb076424d8042e9465b4408406e0172895f372cfca82df4858d9145332e.json) + 1 in audit |
| 2024-04-01 | 2024-05-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/18975de78d5dd02f15713597fff352744e51470f1f9198e8ceba831113fae315.json) |
| 2024-06-01 | 2024-09-01 | 92 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/18975de78d5dd02f15713597fff352744e51470f1f9198e8ceba831113fae315.json) + 1 in audit |
| 2025-05-01 | 2025-06-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/18975de78d5dd02f15713597fff352744e51470f1f9198e8ceba831113fae315.json) |
| 2025-10-01 | 2025-11-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/423fd939ba7326b9a9c9f8d20db20ff0f1c4ac76766912001b7ebce7bca0168c.json) |
| 2026-02-01 | 2026-04-01 | 59 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/2411f93b9479db3e08ffd45634cf6a1e4f3ee957fd9ea85bc19ca8e745da82cd.json) + 1 in audit |
| 2026-05-01 | 2026-08-01 | 92 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/2411f93b9479db3e08ffd45634cf6a1e4f3ee957fd9ea85bc19ca8e745da82cd.json) + 1 in audit |
| 2026-09-01 | 2026-10-26 | 55 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/38f1da028264f28c942eb162c8da1cfe614506e36b46e120c39d96501b14ee6f.json) |

**Resource type dissertation**

Scope identifier `datacite_dissertations_datasets_software_and_usage|C143|specialist_historical|b7e985e05c0e393ff92f4c34`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2023-05-01 | 2023-06-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/76b71ff903f5a265e679866bf1df75ebbbb6d300a18c5335aaecd48bf49275f7.json) |
| 2024-11-01 | 2024-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/7c69e18dd4074cb3f5f33b0824402be1d8c6d426a32fe90691f1aba3df50e46c.json) |
| 2025-06-01 | 2025-08-01 | 61 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/984a9ba1f61f580c72c1b08cf3a0a3392b60c4aecf0357030bb5e7fe2e1d625f.json) |
| 2026-01-01 | 2026-03-01 | 59 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/5e3a31515a073f805ed7ad98b9173a636d9714add1cbb57c9aef439c1fe6a79d.json) + 1 in audit |

**Resource type software**

Scope identifier `datacite_dissertations_datasets_software_and_usage|C143|specialist_historical|f843a17b94374926737d815b`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2024-08-01 | 2024-10-01 | 61 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/7c69e18dd4074cb3f5f33b0824402be1d8c6d426a32fe90691f1aba3df50e46c.json) + 1 in audit |
| 2025-04-01 | 2025-05-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/76b71ff903f5a265e679866bf1df75ebbbb6d300a18c5335aaecd48bf49275f7.json) |
| 2025-07-01 | 2025-08-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/99b69dc5d088579dd2fc8a73f53e3c4ea881baec6bb414123d2e9f34ad42e4a8.json) |
| 2026-02-01 | 2026-04-01 | 59 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/0427321a0c19fc3a7b86799773e5728d63c50421adb2c83264b55da636841097.json) + 1 in audit |
| 2026-05-01 | 2026-06-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/4e342aa54a6f7f574bbc312b3cfd59e17f5442fc5e56c6af79979530033f545d.json) |
| 2026-07-01 | 2026-10-26 | 117 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-datacite_dissertations_datasets_software_and_usage.service/executions/a48f396ffb01e5111596e80babe34c372da8e702f85af881f1ffbd9915ce2870.json) + 1 in audit |

### Japan EDINET corporate filings

- Resolve each affected filing ID against the EDINET index. Re-fetch the advertised original when available and verify ZIP or PDF type, archive members, and expected PDF pages. For truncation or expansion-limit cases, check the original response and use bounded extraction without relaxing archive integrity checks.
- When the provider has withdrawn a filing, record the specific ID and verified unavailability. Consider a permitted dated original archive if available. Replay remaining filings from the saved window checkpoint.

**Configured historical query**

Scope identifier `edinet_filings|S10|specialist_historical|712f7a31f2024ecd4022ddca`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2017-03-06 | 2017-03-07 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/eaf6c84c75b213540a7bf9e5edf8fce67d96f0a4a9a35f6ae79271d2aee73812.json) |
| 2017-07-31 | 2017-08-01 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/e9d4c2e097f5599c3da551492f87e6a4296ff921ee146c1e1b092b4d72f9546a.json) |
| 2017-09-08 | 2017-09-09 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/1812a7772eae0b616f57af80cd88539e65cb28c60c199125677d6db3022885e6.json) |
| 2017-11-07 | 2017-11-08 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/2ba85b3f6db84bc1669a5f45bc315fe7bdea4773da8a5f70692640ada8f1f7b0.json) |
| 2017-11-30 | 2017-12-01 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/2dde17081eb4426366df931cc82f5e29f9321343c717543914f24e34bc3240b6.json) |
| 2017-12-13 | 2017-12-15 | 2 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/0a0820e2cf6a820aded233fd1420487d09afc8eca6525335256f1a842f50f023.json) + 1 in audit |
| 2021-10-18 | 2021-10-23 | 5 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/c7a5d8f9c3e94bde582f440a60789fe0b6ea7f29e1be18aa8499164be158ac05.json) + 1 in audit |
| 2021-10-25 | 2021-10-30 | 5 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/dc2c3e7da53e365b3c42b7b906c1556fbd655d63e073511cf0a3314c4a11ad45.json) + 1 in audit |
| 2021-11-01 | 2021-11-03 | 2 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/f1465405c4487f8faca7a0211d433abae857aa48ef5096bc0163af0ec0f1814c.json) |
| 2021-11-04 | 2021-11-06 | 2 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/f1465405c4487f8faca7a0211d433abae857aa48ef5096bc0163af0ec0f1814c.json) |
| 2021-11-08 | 2021-11-13 | 5 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/1478dd1160ff7a40707cfe5282ad6646aafb41345b78ec1a62b4e15d21664028.json) + 1 in audit |
| 2021-11-15 | 2021-11-20 | 5 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/1478dd1160ff7a40707cfe5282ad6646aafb41345b78ec1a62b4e15d21664028.json) + 3 in audit |
| 2021-12-01 | 2021-12-02 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/c6f8a91105e73f2a9d7baf3819a32f9417a6702f033df4546d73acc9d395bf24.json) |
| 2021-12-06 | 2021-12-07 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/d5b2aa9a7ecd7516ce6f5a4e4b5970e9bc185ea938e2abf5ef04467828d46d27.json) |
| 2021-12-13 | 2021-12-14 | 1 | Recorded | `edinet_document_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/158163af4fa84bfd4831e9b01e0db4a143be7203857fda8c76315b6cf109aa5c.json) |
| 2021-12-20 | 2021-12-21 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/158163af4fa84bfd4831e9b01e0db4a143be7203857fda8c76315b6cf109aa5c.json) |
| 2021-12-22 | 2021-12-23 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/7207e503e9a5ef46531f8344e17e6cd49029501fde735c9c661640e71ec7011b.json) |
| 2021-12-27 | 2021-12-28 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/e909dd3e0b835fb04b6c15486618cab2a8c172b56a2aaf9ccdf284ae0838e9e7.json) |
| 2022-01-19 | 2022-01-20 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/3e22a6822265223e07f7d850d5c577deb83c1dd389e40ec7f9b26a4f1a77194d.json) |
| 2022-02-01 | 2022-02-02 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/a3053623cd6315fbb7e3c9a71395f6ca7581deadc8d47511107453a6da729017.json) |
| 2022-03-15 | 2022-03-16 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/2c1a7a5abdc4b50b9dee484ddb96ddc07c9ab96e8f831f06b31b2561d7a9b9a0.json) |
| 2022-03-28 | 2022-03-29 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/66758d3bee19886949b0087c9a822c1621a11785ad706894c5de64eba6e66888.json) |
| 2022-04-04 | 2022-04-05 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/0834d10e409d2021a50340562752b40311d3ca982c7cda61211354935a16567f.json) |
| 2022-04-14 | 2022-04-15 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/33b54ce6cc15675e6c5c60410d4fcb8c690d2229b12044420b558ad647cdc3e7.json) |
| 2022-04-21 | 2022-04-22 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/76136292e47c113b566823941062fb75116021c8706e44f443fab35121724c72.json) |
| 2022-04-25 | 2022-04-29 | 4 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/76136292e47c113b566823941062fb75116021c8706e44f443fab35121724c72.json) + 1 in audit |
| 2022-05-02 | 2022-05-03 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/ebe3fa76c6b8567c11328169993ce62bb9221f365f57c67844c50777d03cb770.json) |
| 2022-05-06 | 2022-05-07 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/ebe3fa76c6b8567c11328169993ce62bb9221f365f57c67844c50777d03cb770.json) |
| 2022-05-09 | 2022-05-10 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/e68f8e760b4732594365bf80194e7ce5a8347767f0a671ae0ab5318837ac1c87.json) |
| 2022-05-12 | 2022-05-13 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/e8981c6bd64e948a6587fc333674d04c487043898888b145c595a73b4c51a9cb.json) |
| 2022-05-16 | 2022-05-17 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/93b5c98332c52e6efdbce58ffc52c3141d27913a2930942ceb01bd8349a28921.json) |
| 2022-05-19 | 2022-05-20 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/e1a3b425f8cadb736ba5c24e1b7bc61c6c2232e84c53811c074c20804dbe1a4f.json) |
| 2022-05-30 | 2022-05-31 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/caf6a38b489841758f65244692c19c5c34aa28ce7c6462dbb872240323db55ba.json) |
| 2022-06-27 | 2022-06-28 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/d94a4a1e1fc851c95d1f4d4d7e5ec7cc29e48052aaf54e3e095c3f160e37e85c.json) |
| 2022-07-22 | 2022-07-23 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/25d970d43c16b1dc3806d81f7dd4631589c8d4f9afe7589d13cdac94a94b2625.json) |
| 2022-08-17 | 2022-08-19 | 2 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/014c463bc38c755de8e70332fbb1e0f43a917a5a9fe75923fff290ead9248f44.json) + 1 in audit |
| 2023-01-18 | 2023-01-19 | 1 | Recorded | `edinet_document_truncated` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/fc657a03b35d0935945910a9e94155d5ce7af8547175a0b8b1deb6c9455c5c62.json) |
| 2023-10-30 | 2023-11-03 | 4 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/c86590ec26d2a5ee3bad6b9b88e84de8c207409528e3d6deee62502d14e8c03b.json) |
| 2023-11-06 | 2023-11-11 | 5 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/c86590ec26d2a5ee3bad6b9b88e84de8c207409528e3d6deee62502d14e8c03b.json) + 1 in audit |
| 2023-11-13 | 2023-11-17 | 4 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/6cec47cf8649d3c801f983e6a1bbb5817a5c70aea3563c4c5a8f3f4ff44f5039.json) + 2 in audit |
| 2024-07-30 | 2024-07-31 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/a261a7b4a37abe89632c2d2a5749f99fa15c53029a3c5e118350dfeafe13a51c.json) |
| 2024-11-13 | 2024-11-14 | 1 | Recorded | `edinet_zip_expansion_limit` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/6997201bc3e36ba5dd52dc06be589da6aa479667b08ab63f85de26ba07526541.json) |
| 2025-10-15 | 2025-10-16 | 1 | Recorded | `interrupted` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/91bb54f2e81456164b035d1b2dbe81c0d4ab99e07425fd72a6e4c8037653a865.json) |
| 2025-11-07 | 2025-11-08 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/9be2d76cb7313736837166fc041c85e31003eb4593fdb17b9d15339abc6068ad.json) |
| 2025-11-11 | 2025-11-13 | 2 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/9be2d76cb7313736837166fc041c85e31003eb4593fdb17b9d15339abc6068ad.json) |
| 2026-01-06 | 2026-01-07 | 1 | Recorded | `edinet_document_format_invalid` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/70608a28b5b854dacd699becb5f2b230b6252d0a02420f732c1c8a6055ff8155.json) |
| 2026-04-28 | 2026-04-29 | 1 | Recorded | `edinet_pdf_page_count_mismatch` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-edinet_filings.service/executions/75a0de303b032b34be0ce15611747664d71b8ddd90c548c3a46831e603a30eb3.json) |

### EMA CTIS

- Refresh the affected CTIS windows with smaller date ranges and stable provider ordering. Reconcile duplicates and changing page totals against a complete scoped retrieval, then verify committed results and Athena coverage.

**Configured core historical query**

Scope identifier `ema|935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f|configured_legacy_scope`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-08-01 | 2016-10-01 | 61 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/7e5df6a2-4de5-4aa8-bea7-c7b0d01b7715.json) |
| 2017-08-01 | 2017-09-01 | 31 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/d332aa25-28e9-4776-8c43-09112af1d3fe.json) |
| 2020-08-01 | 2020-09-01 | 31 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/156fbe8d-597b-44d0-b6a8-ec42e191c5d8.json) |
| 2020-12-01 | 2021-01-01 | 31 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/d4df2ff6-470c-4359-95d5-6246045a8b40.json) |
| 2021-02-01 | 2021-03-01 | 28 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/f1c9872a-14a1-4063-801a-a2cc4a79696c.json) |
| 2021-07-01 | 2021-09-01 | 62 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/5ffd21c8-4212-4b14-9841-04c237e62cff.json) + 1 in audit |
| 2022-06-01 | 2022-08-01 | 61 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/19fe2933-25d9-4202-af49-2cedd6eb70b9.json) + 1 in audit |
| 2023-06-01 | 2023-08-01 | 61 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/5aab5fc4-53b1-415d-996a-435876c950be.json) |
| 2024-06-01 | 2024-08-01 | 61 | Flagged | `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/fb58f903-dffb-406f-813c-e812f1333cd5.json) |
| 2025-01-01 | 2025-03-01 | 59 | Flagged | `duplicate_provider_record`, `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/5e59e550-f932-4587-832e-2ceb562b4655.json) + 1 in audit |
| 2025-04-01 | 2026-10-26 | 573 | Flagged | `duplicate_provider_record`, `source_changed_during_pagination` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-ema-historical.service/reports/09e20748-6dfc-4b89-a6ae-53277161ab9c.json) + 18 in audit |

### England NHSBSA prescribing data

- Reconcile the affected periods with the official release catalogue. For HTTP 400, correct the dataset ID or time parameters. For an unpublished period, resume when the matching original release becomes available and retain the release evidence.

**Configured historical query**

Scope identifier `england_nhsbsa_prescribing_data|C080|specialist_historical|a6dcd1aa230331a77f59589a`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2020-11-01 | 2025-03-01 | 1581 | Flagged | `source_http_400` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-england_nhsbsa_prescribing_data.service/executions/0468335398d68e3c8aa0773bed5013d5c24ba9ff35b9611355449f4d6ba5e529.json) + 51 in audit |
| 2026-10-01 | 2026-11-16 | 46 | Flagged | `nhsbsa_release_not_yet_published` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-england_nhsbsa_prescribing_data.service/executions/10127162ca762f9e2e4b473b226a68cc215c9fc7e7e0a47e1ddd395091642b0d.json) + 1 in audit |

### IMF PortWatch shipping activity

- Validate the ArcGIS layer and the count response for the exact shipping scopes. Correct the count or feature-response parser, retry in smaller date windows, and reconcile stable feature IDs, counts, and provider dates.

**Configured historical query**

Scope identifier `imf_portwatch_shipping_activity|C069|specialist_historical|737c280b6fd8a491b6e30cff`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2019-01-22 | 2019-01-23 | 1 | Recorded | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/0d6160c0a7ee1fbb8b7cf7e35b7c05cfffd6e54412a4bd341ec21b6fb06340f6.json) |
| 2019-01-24 | 2019-01-27 | 3 | Recorded | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/44931968b72346d4b686f97209c8310a13299f3fce4eabf8b6d0230afa517f21.json) + 2 in audit |
| 2019-01-28 | 2019-02-03 | 6 | Flagged | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/1c308f799ca12ff25eed8f6d1718a2399f6ab9b23aba24eef73d31bc7ad857c9.json) + 5 in audit |
| 2019-02-04 | 2019-02-16 | 12 | Flagged | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/2387b340679f244a0d539c577de0a0c264138ebaf8f3df7791091cf4972d5aa8.json) + 11 in audit |
| 2019-02-17 | 2019-03-13 | 24 | Flagged | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/08da8b2aa7cfc6c65d01ec9419198c8fdb2386c6021833dc99f7fc63a57f6db2.json) + 23 in audit |
| 2019-03-14 | 2019-03-15 | 1 | Recorded | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/71a5900e38fcb743fd0da651049b49affb6ab3e9dc51564810db679b2d9a027e.json) |
| 2019-09-26 | 2019-12-02 | 67 | Flagged | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/048bd37696d6b884d74920d8fb7928dbe2bd239615e4dec728a5e91e5a5365eb.json) + 66 in audit |
| 2020-01-07 | 2020-01-18 | 11 | Flagged | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/0a1a86ae63b9eb7495fce400992782e82360446d0de6d80ffa4a9e0ec3ca2e0c.json) + 10 in audit |
| 2020-01-23 | 2020-01-24 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/2cb35912a78dbdf6ca9c34cc6b8cf7470a89af76eaccaa7b7f44702152e3e57b.json) |
| 2020-01-29 | 2020-03-17 | 48 | Flagged | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/0409ca37bc675d0a1a532acef8c81450c9046d8c171fe50a452094d79867a606.json) + 47 in audit |
| 2020-03-18 | 2020-07-13 | 117 | Flagged | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/014ce16e576da0bec19447af31aa0373d6a6ef14eb6be15300e3a337b6f75a78.json) + 116 in audit |
| 2020-07-17 | 2020-07-19 | 2 | Recorded | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/2ff0dd6ffa46df5eb6ed4b24903a5f12031097ca8e997aeb4ce5c49df9a4569e.json) + 1 in audit |
| 2020-07-27 | 2020-08-06 | 10 | Flagged | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/1a399efd48d8d720b37a418e4162d1a15b5bc7c0b05f0b9d4cde639511f1c703.json) + 9 in audit |
| 2020-08-11 | 2020-08-15 | 4 | Recorded | `portwatch_invalid_features`, `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/95724b3b64103e3e71750c2af3389c7d45e7f064f0c845f3aa066efa5bea98ae.json) + 3 in audit |
| 2020-08-17 | 2020-08-18 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/99bfeec3c27225802ab9c153b6dc1ad74a65d85d2e2a7ebe6f66c348c0b5f9ed.json) |
| 2020-08-19 | 2020-08-20 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/f01f2930794bd50275f66a36b12a8794732c1449b43654c77e77fbbbe5ec42e9.json) |
| 2020-08-23 | 2020-08-24 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/70059cc719265974c944e88a843131120419ae930bf612909e0a40a2f6ffbad7.json) |
| 2020-08-29 | 2020-08-30 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/96b97c53b53d144f095a0d9f248d519bee1fa8c906a53cbd56323839ef8bce49.json) |
| 2020-09-04 | 2020-09-05 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/86f89d67b797521de0e19002c5bce79e10ca5a2db690e28ee1eb2dc721aebdb6.json) |
| 2020-09-10 | 2020-09-11 | 1 | Recorded | `portwatch_invalid_features` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/a3ffbc4d48e38838de4050b281db95d1d75c80921aabf01eeb5edd70b165b59c.json) |
| 2020-10-04 | 2020-10-05 | 1 | Recorded | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/0925db32ed74dd6affe0c1c1c58a34c694a172f2e17af7348020cb9a038d3fbb.json) |
| 2021-04-22 | 2021-05-08 | 16 | Flagged | `portwatch_missing_count` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-imf_portwatch_shipping_activity.service/executions/0092ea9f0dd66a06a80779093e6549e7c215c273893e5b16d78e6dcb07ff45a9.json) + 15 in audit |

### South Korea FSS OpenDART

- Resume the interrupted original-document collection for the recorded June 2024 scope and verify filing IDs, original document hashes, and committed Athena output.

**Configured historical query**

Scope identifier `south_korea_fss_opendart|C098|specialist_historical|6790594caca0dd18899b4fb1`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2024-06-01 | 2024-07-01 | 30 | Flagged | worker connection interrupted | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-south_korea_fss_opendart.service/executions/0c6fc07faebed19ca77ff4ad673c5bbf01405827d793f27cd5e39b159a42a1ab.json) |

### UK MHRA

- Find a dated original MHRA designation record or a permitted dated archive for the exact regulatory designation. Where no date can be established, record scoped unavailability with the evidence and preserve the distinction between snapshot and historical status.

**Configured core historical query**

Scope identifier `uk|935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f|configured_legacy_scope`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-01-01 | 2026-10-26 | 3951 | Flagged | `historical_designation_date_unavailable` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-core-uk-historical.service/reports/00c4cdd2-7daa-4ea7-83da-c756a27aacdc.json) + 129 in audit |

### WTO Timeseries API

- Verify the recorded indicator and period arguments against the configured WTO route. Split and replay supported periods under the existing quota. Inspect the 204 scope separately and document an empty or unavailable period only after checking the exact indicator semantics.

**WTO indicator BAT_BV_M**

Scope identifier `wto_timeseries_api|C071|specialist_historical|e38132c0fb1f68a6b33611f1`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-01-01 | 2020-01-01 | 1461 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/4761ff85714fe851b2bbd925f77edc5280d411ac63d6186dac1d0edb91346079.json) + 3 in audit |

**WTO indicator BAT_BV_X**

Scope identifier `wto_timeseries_api|C071|specialist_historical|3a8096bd5200c6d5683faf63`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-01-01 | 2018-01-01 | 731 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/1bd904dcc773f678e14f167b0fe866218e9aeb3b6144269f191fc6d4683d3c34.json) + 1 in audit |

**WTO indicator HS_A_0020**

Scope identifier `wto_timeseries_api|C071|specialist_historical|dacc23ea8281d54426525181`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2017-01-01 | 2018-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/e7a2832933a49a3df55942ac3c69ee9d5bfae735f957d8d6e090f39fc764912b.json) |

**WTO indicator HS_A_0050**

Scope identifier `wto_timeseries_api|C071|specialist_historical|61547a0f7f001f9bcfd1cdb6`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2017-01-01 | 2018-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/9e6a1af1238da0e8481c392f186148e38a95d2eeaa259a9afb89524700898a8d.json) |
| 2019-01-01 | 2020-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/cd22fc6d804f8ec5156cd264039498812a1ea1a5414d184937fdd8035e691117.json) |

**WTO indicator HS_P_0070**

Scope identifier `wto_timeseries_api|C071|specialist_historical|99e8f10d6a6882da7955df10`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2017-01-01 | 2019-01-01 | 730 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/9cb5de9cf0825ac3a845ed7933539d656f2e642eb3001f7fc6ba4b079375c7b4.json) + 1 in audit |

**WTO indicator ITS_CS_AM5**

Scope identifier `wto_timeseries_api|C071|specialist_historical|8ee10105d1dc985d55a29ac4`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-01-01 | 2017-01-01 | 366 | Flagged | `source_http_204` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/3b96676c64752f68d49b26580543128b7c94bf0d1f96ea61dd4f82ec0111552d.json) |

**WTO indicator ITS_CS_AM6**

Scope identifier `wto_timeseries_api|C071|specialist_historical|8ba58f1a2d9635341b9d71ba`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2019-01-01 | 2020-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/6ba4f3962fd808c64c9145e2c655a6b8bb17e716d84bc0763252f4d3b4d7fdea.json) |

**WTO indicator ITS_CS_AX6**

Scope identifier `wto_timeseries_api|C071|specialist_historical|8bb8dfbfafef3d343f34248b`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2018-01-01 | 2019-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/b45632e8ec79ede15a5e7dd7977bdb20ad1426cbd1b0f4d076c74c4d2cc9bc26.json) |

**WTO indicator TP_A_0010**

Scope identifier `wto_timeseries_api|C071|specialist_historical|76d5f97382bacad56874b5dd`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2018-01-01 | 2019-01-01 | 365 | Flagged | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-wto_timeseries_api.service/executions/5aaa50f35b2325b12589e89ef26861dc1510e0105adfa7484e6bd9df9cc6545b.json) |

### Zenodo research artifacts and usage

- For changes during pagination, refresh affected queries over shorter dates with stable record/version identity. Split oversized responses by date or query partition and reconcile the completed result counts.
- For connection failures or interrupted jobs, use the recovered database connection and resume from the retained checkpoint. Replay the exact windows after any provider retry cooldown and verify committed output.

**Configured historical query**

Scope identifier `zenodo_research_artifacts_and_usage|C147|specialist_historical|972d7e8166bf09bd002ee3a8`

| Start | End exclusive | Days | Status | Recorded cause | Audit receipt |
| --- | --- | ---: | --- | --- | --- |
| 2016-09-30 | 2016-10-01 | 1 | Recorded | `source_http_500` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5a426baae84b4f21ea8b44354751ad0065358f8de30881564ab2e74e1950758b.json) |
| 2017-09-01 | 2017-10-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5f938f24c2a0798d7c1896c819523bf6b0ec4748235ba72ccc09f4a2b47e03aa.json) |
| 2018-07-01 | 2018-09-01 | 62 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/214c08e0dc9d0921e4276ff9c80ba3da8fc2e8a1eea992fa32e76cf2a2b95b15.json) + 1 in audit |
| 2018-12-01 | 2019-01-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/42c8576747a195f736113c7d9342855c46ad677b1ed29bc1e334ff1aebfe0da1.json) + 1 in audit |
| 2019-02-01 | 2019-03-01 | 28 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/b679d07cb8d843bec9ebe398f3ee80ad2db0c790e512fffe12d0774f7ea24ddd.json) + 1 in audit |
| 2019-04-01 | 2019-05-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/bd76e63f69850efbc653254c200344f67ffa15c876481ff1582a35a60d832a96.json) + 1 in audit |
| 2019-08-01 | 2019-09-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d487e872c60bf001c8e7163c742da7d0af548af45c89c5845560f0be596cc13b.json) |
| 2019-12-01 | 2020-01-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d487e872c60bf001c8e7163c742da7d0af548af45c89c5845560f0be596cc13b.json) |
| 2020-06-03 | 2020-06-04 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/3d5e0f202bb5e5a6bbaa8c98c182b5d5a6bdfc9d7bfb37c21eb117c66b16f825.json) |
| 2020-11-01 | 2021-01-01 | 61 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/a7a55f7b1321a345c91ef62fb7ffcdbdff0a4786586ca46017c586ca9b2930ed.json) + 1 in audit |
| 2021-01-26 | 2021-01-27 | 1 | Recorded | `additional_request_failed` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/76f0dad9953dd5a7b66f29852f899ebc27f65cd7c931bc67174165845e08aed3.json) |
| 2021-03-15 | 2021-03-16 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ed35314d624b361c521abfdafdff49d532631e00d6b6905b2e22704ce17e9272.json) |
| 2021-04-09 | 2021-04-10 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/42c1ad1644be6865c3593c4bbd5eff59582e7aab98f549a2635b27780cb02f58.json) |
| 2021-04-15 | 2021-04-16 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/42c1ad1644be6865c3593c4bbd5eff59582e7aab98f549a2635b27780cb02f58.json) |
| 2021-06-08 | 2021-06-09 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/cae960ee144d27242de8fddb6d6f868118fa36ba52ee61f64379a39ecf4dbe05.json) |
| 2021-09-01 | 2021-10-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/33bd380b637e6232367055b5bd6a10539a08d9f8a24178cd70b1024e725c50a1.json) + 1 in audit |
| 2021-11-01 | 2021-12-01 | 30 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/04ccb568513d7f92ff4c9ffdcc076bf5a9167ea898a70087f2b9b3f40b466d63.json) + 1 in audit |
| 2022-03-01 | 2022-04-01 | 31 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d8ed880be2b20a80452ce2a2e74c05fdd56d6eaffef366fd1ad44682554fbcab.json) + 1 in audit |
| 2022-05-01 | 2022-07-01 | 61 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/7549b07f9f820d1c35ea387685f8aa3f6172f1aaacf13d14cf5ecbce5f9cd55b.json) + 2 in audit |
| 2022-11-18 | 2022-11-19 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d49c3341a649e1af3641f5f92eda1f6bb71be000eaf0210021598f79d820c9e8.json) |
| 2022-11-21 | 2022-11-23 | 2 | Recorded | worker connection interrupted, database connection timed out | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/20a1a697db4f95042608962a7a8975faea7f8f7f626bc866a5ac92590e372dcd.json) |
| 2022-12-01 | 2022-12-02 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/50c1e95cabd76ca2120c627eb5024c142f0bd813fbf410e8a0126fbdb8651491.json) |
| 2023-01-01 | 2023-03-01 | 59 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/11ef1208080af276de5261f66f24806ae700f866fc67cde3f66b3c4f70793399.json) + 1 in audit |
| 2023-04-29 | 2023-04-30 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/cbd6e259f65541113b4c8675f90845c3794cb79e3c2c5dd186b012a38514605c.json) |
| 2023-06-20 | 2023-06-21 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c5ddfcb8066f72e6411b4eed3f4107152c9130862928d5981f3e8632aa4ce16b.json) |
| 2023-07-07 | 2023-07-08 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/40c8e4b1198d381b583f9e19090cbd7ebf2a58b5f3f6ab42bc89e9519b59418e.json) |
| 2023-09-26 | 2023-09-27 | 1 | Recorded | `additional_response_too_large_split_scope` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/44a13e53db83b58e432efb59ff7e4b79ead1b6044ff5a31bb74f1a212ab60bfa.json) |
| 2023-10-11 | 2023-10-12 | 1 | Recorded | `interrupted` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/9f9aab519f98492dab931eb1f38e62172d07f67d893ec4c4a78d33ad436bda6d.json) |
| 2023-10-14 | 2023-10-21 | 7 | Flagged | database connection refused, database connection timed out | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/9f9aab519f98492dab931eb1f38e62172d07f67d893ec4c4a78d33ad436bda6d.json) + 1 in audit |
| 2023-10-23 | 2023-10-30 | 7 | Flagged | database connection refused, database connection timed out | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/804da844db04a5936e70bb4d4b524b35704871a2d8abc40b2de39f5d6935c1b6.json) |
| 2023-10-31 | 2023-11-07 | 7 | Flagged | database connection refused, database connection timed out | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d8a346e26ca5ba96a9b60f271e16b1ec6bfdc5c8d615798adb9e7c10f7a3b9eb.json) |
| 2023-12-15 | 2023-12-16 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/85a8854407d6009a0e5267910b1d075ca826f550c61b4a16de50a55cdd7504f0.json) |
| 2024-01-08 | 2024-01-09 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/fc57989e532ccfe27d947f4d860085e71d18785f1ab82ebe59e29d76cea4f704.json) |
| 2024-01-11 | 2024-01-12 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/fc57989e532ccfe27d947f4d860085e71d18785f1ab82ebe59e29d76cea4f704.json) |
| 2024-03-11 | 2024-03-12 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2f7be73d03e48f12fc7384b29d329bbc76d2efa2f4acdc648e9e267ca51d6a3a.json) |
| 2024-04-09 | 2024-04-10 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2a4c370f97b69188adab417f81d1c9c2dc286ae57c1eb964f0bdc57dbbcfa70c.json) |
| 2024-04-19 | 2024-04-20 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/dda13402a439797653cf304876274f54d76f3dda41173498f69e3a1aa4db5f65.json) |
| 2024-05-16 | 2024-05-17 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/47c72d8d3c868dc04ae026cb3dfafa135745f80fccb13265441dacd41007ddda.json) |
| 2024-05-20 | 2024-05-21 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/bf83bb1abdfbff1c8ca80b6fe977e6046f0e5b934224c2e653e0170af523abe1.json) |
| 2024-05-29 | 2024-05-30 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d5633f6e6ba134ce8d801affd620f9554ab6284af3a8265cca695ba1817664ba.json) |
| 2024-06-26 | 2024-06-27 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ea62fe9defedf171e42ea3b5b1185a1ec5146dc9930a73a677a42571cd6105da.json) |
| 2024-07-24 | 2024-07-25 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ddd397c31ea689130c502e8b7a3790015c6936a84ca9705e5ce0797137090d2a.json) |
| 2024-07-31 | 2024-08-01 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/34c1b1a092d75039cf169923ee0f34775bb96ea3904a8c26ea73896d8d336832.json) |
| 2024-08-12 | 2024-08-13 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f6e53528b1490c8cb47b5ff7a38d5527970e39cd13c38f6ba614a62af8ca8edc.json) |
| 2024-08-20 | 2024-08-21 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d9670ec86f732a9a71cc653e448003402e297455e9cf44a6f369c92e2367e19e.json) |
| 2024-09-30 | 2024-10-01 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f104a54a719d6bbc994729b2282676112681b1886d74945b78725df1105e802a.json) |
| 2024-11-05 | 2024-11-06 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/680bb40847fa8380fe8d645ed1f4da390de1f1f11a19891ecb379fbde9d0edf8.json) |
| 2024-12-01 | 2024-12-02 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/d8b694edd99e838c6cd95714827a4e03d8de149cf853d8c9d5f22a9a56ac552b.json) |
| 2024-12-30 | 2025-01-01 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ce5dae1139b463cf31dcee593c2ea6112f1ef8af5bf2cd20ca52a100e0900b8b.json) |
| 2025-01-21 | 2025-01-22 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/79b072aa74bc6abd707cd67622f1367a6b9724cc09d5e7632dd4a56a45ecf361.json) |
| 2025-01-27 | 2025-01-28 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/79b072aa74bc6abd707cd67622f1367a6b9724cc09d5e7632dd4a56a45ecf361.json) |
| 2025-02-22 | 2025-02-23 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/9b87b145ef858ba06e4408d8959475d7c32251349b57baf77dce2d65fd813122.json) |
| 2025-03-11 | 2025-03-12 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5824fbad5e74227fed982e7dd44155b3b75b2f801a7f80edb1d68ede753747f0.json) |
| 2025-05-02 | 2025-05-03 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5c529876a7ecf68b3b05130185d3bdb498594a48f317164608eb895e8c2edc1c.json) |
| 2025-05-09 | 2025-05-10 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5c529876a7ecf68b3b05130185d3bdb498594a48f317164608eb895e8c2edc1c.json) |
| 2025-05-19 | 2025-05-20 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f19e97f91c802908c926314a09e85304760fb80d7f9fd0369b9db734c154dbfa.json) |
| 2025-05-21 | 2025-05-22 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f19e97f91c802908c926314a09e85304760fb80d7f9fd0369b9db734c154dbfa.json) |
| 2025-06-03 | 2025-06-04 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5cc350b5fd676690f56cda0d67ac62d8bd2d44771f16eda19975a96f16610d50.json) |
| 2025-06-18 | 2025-06-19 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/22bddc21f40d6994c7c96ba1d10aeaa93823e10648a5134631237c82ab065d6c.json) |
| 2025-06-30 | 2025-07-01 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c07e7218177affbe0fa7315628b10235df8b7bbd4d1adf669fa29717518b6cb9.json) |
| 2025-07-03 | 2025-07-04 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c07e7218177affbe0fa7315628b10235df8b7bbd4d1adf669fa29717518b6cb9.json) |
| 2025-07-15 | 2025-07-16 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/35dcefa432859fcf9b1144ef41e6f44767f56bf4b4f5428d6df6755dbf658405.json) |
| 2025-07-21 | 2025-07-22 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/35dcefa432859fcf9b1144ef41e6f44767f56bf4b4f5428d6df6755dbf658405.json) |
| 2025-07-31 | 2025-08-02 | 2 | Recorded | `source_changed_refresh_required`, `source_http_503` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/4158064c5d0fcc653eedf0a8bd9e4665cc5a33b0fb4db8dd289967c764d3de03.json) + 1 in audit |
| 2025-08-08 | 2025-08-09 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2b0d73874f48fd5bdb6be62737a052c9930fcc2c079bba0a09fb14b2a3cee9db.json) |
| 2025-08-13 | 2025-08-14 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2b0d73874f48fd5bdb6be62737a052c9930fcc2c079bba0a09fb14b2a3cee9db.json) |
| 2025-08-20 | 2025-08-22 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/491ded53efba25f5d6a3614b87e977e7e980e4280c7ef72f765e6887b792efc1.json) |
| 2025-08-29 | 2025-08-31 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/686f88fb322ecf9dfedf6cef4942ede570a5808a3b7821c696cd4d629ff1822d.json) + 1 in audit |
| 2025-09-03 | 2025-09-04 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/686f88fb322ecf9dfedf6cef4942ede570a5808a3b7821c696cd4d629ff1822d.json) |
| 2025-09-10 | 2025-09-11 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c0496726c38227190c0e613812b8964ed3d5318fecdabb0872b9fa6b81b1f0e1.json) |
| 2025-09-17 | 2025-09-19 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/85df2f60365c52d3994562c5886adb9875b5059cf783f3b53c97efffbe1f1e64.json) |
| 2025-09-25 | 2025-09-26 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/071685603ea7ffddb422441881ba4107902c7bc4fe26a4016611d68b673af831.json) |
| 2025-09-30 | 2025-10-03 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/071685603ea7ffddb422441881ba4107902c7bc4fe26a4016611d68b673af831.json) + 1 in audit |
| 2025-10-06 | 2025-10-08 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ab781f08a3391f45acd7415b98ffb59ca8aff38d08b3b8feca2e16cab5c22404.json) |
| 2025-10-09 | 2025-10-10 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2b4bd16cbf5bd6862cda927f757a1dac3004a09e4f099f777e81e132c89958e8.json) |
| 2025-10-12 | 2025-10-13 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2b4bd16cbf5bd6862cda927f757a1dac3004a09e4f099f777e81e132c89958e8.json) |
| 2025-10-21 | 2025-10-24 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c14e798ac95f1870c966cc448107d915bf14147cff7342f2e3272b0de9ce09d9.json) |
| 2025-10-27 | 2025-10-29 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/a53990bd55501c09ca69c6db8463337a6a64bdd22219f12eba8cfe9b1ae3a60c.json) |
| 2025-10-30 | 2025-11-01 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/a53990bd55501c09ca69c6db8463337a6a64bdd22219f12eba8cfe9b1ae3a60c.json) |
| 2025-11-06 | 2025-11-07 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/526a7c57a85cc15142ef32da0c1f5d72dc16f4bef8203620354b5032ea0273f1.json) |
| 2025-11-14 | 2025-11-15 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/94391c5d67cc34d5886532697b6ef55f34785a79b7c5beac00a80482ec051be2.json) |
| 2025-11-19 | 2025-11-20 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/87e46f5996508a933da3965046aa402b86472a07ce3ffb9f454e07f4a11e0b1a.json) |
| 2025-11-22 | 2025-11-23 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/87e46f5996508a933da3965046aa402b86472a07ce3ffb9f454e07f4a11e0b1a.json) |
| 2025-11-27 | 2025-11-29 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/62e93cf7a2d01bed716b14f3d40691dc741a5be00dc67f5b857ac9029b4d5ff1.json) |
| 2025-12-05 | 2025-12-06 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2db6c35292542b2aac0e0e0f69b1afb3b54c81ac5940b95e3a52064080258bcd.json) |
| 2025-12-08 | 2025-12-13 | 5 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/2db6c35292542b2aac0e0e0f69b1afb3b54c81ac5940b95e3a52064080258bcd.json) + 1 in audit |
| 2025-12-15 | 2025-12-16 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/7832a2ccaeecd6cfd2fd7f80dd10a8adcb5b1c49cc7751d249ca0579d2cbd8aa.json) |
| 2025-12-17 | 2025-12-19 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/7832a2ccaeecd6cfd2fd7f80dd10a8adcb5b1c49cc7751d249ca0579d2cbd8aa.json) |
| 2025-12-24 | 2025-12-25 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/c0a1f2cf99ae79e13a9697866121510960eb07fd60dfa91b303c93e21ed57e61.json) |
| 2026-01-01 | 2026-01-02 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/bc545727dee913095ef3b19449ed2bc653b01e5453f6ed62a84b331b19c8e4ff.json) |
| 2026-01-06 | 2026-01-09 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/77e25301346d76c5e54745b939bc8c6c6ad4f8dc4c6668adc1d799f10b83ef02.json) |
| 2026-01-12 | 2026-01-17 | 5 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/77e25301346d76c5e54745b939bc8c6c6ad4f8dc4c6668adc1d799f10b83ef02.json) + 1 in audit |
| 2026-01-19 | 2026-01-20 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/fc2cb72d9107066a788d6dba4030154fb4fbb6085b0c7bb83436f3b5a158bbd8.json) |
| 2026-01-21 | 2026-01-24 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f5e0ced7b7834f2a0089075529c45446f845ac3c4e0166bace76d652961294a0.json) |
| 2026-01-26 | 2026-01-27 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/f5e0ced7b7834f2a0089075529c45446f845ac3c4e0166bace76d652961294a0.json) |
| 2026-01-28 | 2026-01-30 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/b900657b2b0115df4354a6f48b9c4f51c258ed1e5a6ad2f2bee3be64e4d02c3f.json) + 1 in audit |
| 2026-01-31 | 2026-02-06 | 6 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/b900657b2b0115df4354a6f48b9c4f51c258ed1e5a6ad2f2bee3be64e4d02c3f.json) |
| 2026-02-08 | 2026-02-11 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/016574c8b119fd2595e3f1bb35a8c67bbcf6a191c7bcf1e8a093d7e5f674532f.json) |
| 2026-02-12 | 2026-02-15 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/016574c8b119fd2595e3f1bb35a8c67bbcf6a191c7bcf1e8a093d7e5f674532f.json) + 1 in audit |
| 2026-02-19 | 2026-02-26 | 7 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/7f1db3be25a9b429845e59ffa3f4bc2705c106d20a4b7ea2ab633bd5d0e2e7db.json) + 1 in audit |
| 2026-03-02 | 2026-03-03 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/558e3f06ecd5b22064de04f030bc4c21ece33a0e649e8669ed576baefc48c03e.json) |
| 2026-03-04 | 2026-03-05 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/558e3f06ecd5b22064de04f030bc4c21ece33a0e649e8669ed576baefc48c03e.json) |
| 2026-03-07 | 2026-03-08 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/558e3f06ecd5b22064de04f030bc4c21ece33a0e649e8669ed576baefc48c03e.json) |
| 2026-03-09 | 2026-03-12 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/558e3f06ecd5b22064de04f030bc4c21ece33a0e649e8669ed576baefc48c03e.json) + 1 in audit |
| 2026-03-13 | 2026-03-14 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/8fb7e3006ffe5a2dfe62511e9c0a35cb0fc3ddcd1cffffa8f2cb98f5e916ef23.json) |
| 2026-03-16 | 2026-03-21 | 5 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/8fb7e3006ffe5a2dfe62511e9c0a35cb0fc3ddcd1cffffa8f2cb98f5e916ef23.json) + 1 in audit |
| 2026-03-22 | 2026-03-23 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/e81d6ee6c6719fa70655891ff372b9e8de709e24b9c4c6df98dcb273d3e054a6.json) |
| 2026-03-24 | 2026-03-25 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/e81d6ee6c6719fa70655891ff372b9e8de709e24b9c4c6df98dcb273d3e054a6.json) |
| 2026-03-26 | 2026-03-27 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ebeb75aabb02f18d06196517b5f9216f6a6d4268176a045eb614f5c56d19eadc.json) |
| 2026-03-30 | 2026-04-02 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/ebeb75aabb02f18d06196517b5f9216f6a6d4268176a045eb614f5c56d19eadc.json) |
| 2026-04-05 | 2026-04-07 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/a65d2aaaaff144db656f491da1f86d6d16d075701913da46bdd3fb7629f950d7.json) |
| 2026-04-08 | 2026-04-09 | 1 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/a65d2aaaaff144db656f491da1f86d6d16d075701913da46bdd3fb7629f950d7.json) |
| 2026-04-10 | 2026-04-13 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/5a337523fb11e96db81280195bbe3e4b34adbaa664e81a1049d6227e89727609.json) + 1 in audit |
| 2026-04-14 | 2026-05-09 | 25 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/05c73e7ad4c40c3f6ec7e017209ef3a2d226eade9016ea025856fc8afa0448c3.json) + 3 in audit |
| 2026-05-10 | 2026-05-14 | 4 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/dc2c2c4f0b07197ed5c1c2938cda30fac23ddfe8934432202fe653fd09782343.json) + 1 in audit |
| 2026-05-15 | 2026-05-17 | 2 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/dc2c2c4f0b07197ed5c1c2938cda30fac23ddfe8934432202fe653fd09782343.json) |
| 2026-05-18 | 2026-05-31 | 13 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/64ca7f3fda0733ba39dbabc03b1f9138fb6976080331a187ee4f80f7cdcb8d48.json) + 2 in audit |
| 2026-06-01 | 2026-06-06 | 5 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/b683402887625792b7884c3871fdc7b933775c0340d9391a8be550102372a3f0.json) |
| 2026-06-07 | 2026-06-16 | 9 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/89a1b45f0711ecc70dee73bc6ab6753edbec1a12c1f7a33c751179effb5b9e42.json) + 1 in audit |
| 2026-06-17 | 2026-07-04 | 17 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/36c67a25752c4704e0a163e304ab4ffc2b86782c9de2bd58defb9cd265a9e959.json) + 2 in audit |
| 2026-07-05 | 2026-08-19 | 45 | Flagged | worker connection interrupted, database connection refused, database connection timed out, `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/4ad40d735cfc6612b1b5b489885edf9b309060081b36b9143afbb4f8cff6f919.json) + 7 in audit |
| 2026-08-20 | 2026-08-23 | 3 | Recorded | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/e8b3bd59f1b8f04077e7619346110a9806033258639bf4fb988e803c6789883d.json) |
| 2026-08-24 | 2026-10-26 | 63 | Flagged | `source_changed_refresh_required` | [Receipt](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/legacy-operation-receipts/constellation-specialist-zenodo_research_artifacts_and_usage.service/executions/192eab9e120686e2afd0509d97c101408e5ee4417f432f3fa36b805b54214f1c.json) + 8 in audit |

## EODHD historical market coverage

Historical checkpoint checked 21 November 2026 13:02 UTC. The provider returned empty data for 748 windows across 202 symbols. Each window below has an unresolved coverage decision.

Verify exchange and ticker history, listing or delisting dates, and trading calendars for each window. Replay valid listing periods under the shared EODHD quota. Preserve empty windows until recovered or supported by reviewed listing or provider evidence.

The same checkpoint has 184 unattempted windows added by the 2016 expansion. Those are scheduled capture. The daily gap totals are tracked separately.

[EODHD historical checkpoint](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/operations/market/automation/73d86afe67f4dc0c545538c8917092c07b4bedb8f92bc1cdb4334e66c029f886/historical.json)

| Symbol | Unresolved date intervals with exclusive ends |
| --- | --- |
| 000075.KO | 2026-01-01 → 2026-09-01 |
| 000413.SHE | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 000584.SHE | 2026-01-01 → 2026-09-01 |
| 000670.SHE | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0007J0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 000885.KO | 2026-01-01 → 2026-09-01 |
| 0008Z0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 000976.SHE | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 000982.SHE | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 000995.KO | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0009K0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 0013.HK | 2016-01-01 → 2017-01-01 |
| 001570.KO | 2026-01-01 → 2026-09-01 |
| 0015G0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 0017J0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 007630.KO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0082N0.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 00D.F | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 015540.KO | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 016790.KQ | 2026-01-01 → 2026-09-01 |
| 01X.F | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 023890.KQ | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0300.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01 |
| 031390.KQ | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 032980.KQ | 2026-01-01 → 2026-09-01 |
| 033110.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 036180.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 039230.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 041590.KQ | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 043220.KQ | 2026-01-01 → 2026-09-01 |
| 043290.KQ | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 04I.F | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 04IC.F | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 04X.F | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| 0501.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 054630.KQ | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 057500.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 05Y.XETRA | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0600.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 062860.KQ | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0638.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 065160.KQ | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0666.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| 0668.HK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| 09R.F | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 0A3_old.F | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0A4D.LSE | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 0A4U.LSE | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0A9E.LSE | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 0BF1.F | 2026-01-01 → 2026-09-01 |
| 0C1.F | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0C1_old.F | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0C8.F | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0D1J.LSE | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 0DOL.LSE | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 1704.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 1729.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 1787.TWO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 1CO.XETRA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01 |
| 2311.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2325.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2437.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2448.TW | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2928.TWO | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2EM.XETRA | 2021-01-01 → 2022-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 2QO.XETRA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3383.TW | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3559.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3579.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3592.TWO | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3698.TW | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 3K-BAT.BK | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 4949.TWO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 4OR.XETRA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 4XT.XETRA | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 5233.TWO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 5305.TW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 5GH.XETRA | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 600083.SHG | 2026-01-01 → 2026-09-01 |
| 600175.SHG | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 600200.SHG | 2026-01-01 → 2026-09-01 |
| 600705.SHG | 2026-01-01 → 2026-09-01 |
| 6287.TWO | 2026-01-01 → 2026-09-01 |
| 6423.TWO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 6446.TWO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 6452.TW | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 6589.TWO | 2026-01-01 → 2026-09-01 |
| 6789.TWO | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 6919.TWO | 2021-01-01 → 2022-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| 6D81.XETRA | 2026-01-01 → 2026-09-01 |
| 703.XETRA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 7768.TWO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| 8GM.XETRA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| A2MB34.SA | 2021-01-01 → 2022-01-01 |
| A2RR34.SA | 2021-01-01 → 2022-01-01 |
| A2ZT34.SA | 2021-01-01 → 2022-01-01<br>2026-01-01 → 2026-09-01 |
| AAAP_old.US | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABB-U.ST | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABB.MC | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABBN.MX | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABBV.NEO | 2021-01-01 → 2022-01-01 |
| ABBV.PA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABBV.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABBV19.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| ABBV80.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| ABHBY.US | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| ABLI.ST | 2026-01-01 → 2026-09-01 |
| ABT.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| ABT.SN | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ABT.SW | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ACL_old.AU | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ACN.BA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01 |
| ACOG.V | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ACPH.BR | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ACST.V | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ACTI-BTA.ST | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ADDV-BTA-B.ST | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2026-01-01 → 2026-09-01 |
| ADL.MC | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ADVANT19.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| ADVANT23.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| AEGIR.ST | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AESANDES.SN | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AESGENER.SN | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AEZS.TO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AIAI.TO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| AIP.JSE | 2026-01-01 → 2026-09-01 |
| AKBM-ME.OL | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AKU.TO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ALAB01.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| ALACT.PA | 2026-01-01 → 2026-09-01 |
| ALCYB.PA | 2026-01-01 → 2026-09-01 |
| ALDEI.PA | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ALELIO.ST | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ALLR.ST | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ALT-R.BK | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ALVO-SDB.ST | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| AMAT.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| AMAT.TO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| AMAT01.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| AMAT23.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| AMNI.ST | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ANASAC.SN | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ARM.BA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| ASAP.ST | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ASIT.BR | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ASML.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| ASML.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| ATCO-IL-A.ST | 2021-01-01 → 2022-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ATE.TO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ATLNEE.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ATORX-BTU.ST | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AUP.TO | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AVGO.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| AVGO.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| AWKN.NEO | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| AZO.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| AZO.TO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| B1DX34.SA | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| B2RK34.SA | 2021-01-01 → 2022-01-01<br>2026-01-01 → 2026-09-01 |
| BAI.AS | 2026-01-01 → 2026-09-01 |
| BAS.SW | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BAT-3K-R.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BAT-3K.BK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BAYNN.MX | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BCPG-R.BK | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BDMS-R.BK | 2026-01-01 → 2026-09-01 |
| BGBIO.OL | 2026-01-01 → 2026-09-01 |
| BH-R.BK | 2026-01-01 → 2026-09-01 |
| BIO.MC | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BIO3.HM | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| BIONOR.OL | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| BIOS.BR | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| BIOV.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| BML.WAR | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| CAJN.MX | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| CORRE.IR | 2026-01-01 → 2026-09-01 |
| DD.BA | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| DD.MX | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| ESP.AS | 2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| FITBIO.HE | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| GILD.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| GLW.SW | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| GRW.IR | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| GYQ.IR | 2026-01-01 → 2026-09-01 |
| HON.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| JNJ.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |
| KDS.AS | 2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| KNRS.SW | 2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| LKFT.AS | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01 |
| MDXH.BR | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| MMMM.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01 |
| MTLS.BR | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| MYCO.NEO | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| NEU.MC | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| NIPS.JK | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| NVS.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01 |
| OVXA.IR | 2026-01-01 → 2026-09-01 |
| PLAIS.AT | 2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| QCOM.BA | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| SAC.VI | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01<br>2024-01-01 → 2025-01-01<br>2025-01-01 → 2026-01-01<br>2026-01-01 → 2026-09-01 |
| SUNN.NEO | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01<br>2023-01-01 → 2024-01-01 |
| VLA.VI | 2021-01-01 → 2022-01-01<br>2022-01-01 → 2023-01-01 |

## Reviewed unavailability

Every scope entry in the current register is listed here by decision and scope. The date pairs give the original exclusive-end windows.

### ALFRED DTWEXBGS earlier vintages · 11 scope entries

The reviewed vintage catalogue begins 4 February 2019. Keep the requested 2016–2018 vintage period unavailable. The wider dates in the table describe the observation windows for those vintage queries.

[Decision evidence](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/source_documents/fred_alfred_series_and_vintages/c1e592c762b177ae54c0196313a17c6c04ec95a601c1718a32ae2e3da902e535)

Scope identifier `fred_alfred_series_and_vintages|C066|specialist_historical|7bf8a801a3c95cd2d5dbd008`

- 2016-01-01 → 2017-01-01 · 2017-01-01 → 2018-01-01 · 2018-01-01 → 2019-01-01 · 2019-01-01 → 2020-01-01 · 2020-01-01 → 2021-01-01
- 2021-01-01 → 2022-01-01 · 2022-01-01 → 2023-01-01 · 2023-01-01 → 2024-01-01 · 2024-01-01 → 2025-01-01 · 2025-01-01 → 2026-01-01
- 2026-01-01 → 2026-10-26

### EDINET 2016 · 366 scope entries

Honor the approved 2016 exclusion. Continue repairs for the later EDINET windows listed above.

[Decision evidence](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/constellation-backfill/repairs/2026-11-16-edinet-scope/owner-decision.json)

Scope identifier `edinet_filings|S10|specialist_historical|712f7a31f2024ecd4022ddca`

- 2016-01-01 → 2016-01-02 · 2016-01-02 → 2016-01-03 · 2016-01-03 → 2016-01-04 · 2016-01-04 → 2016-01-05 · 2016-01-05 → 2016-01-06
- 2016-01-06 → 2016-01-07 · 2016-01-07 → 2016-01-08 · 2016-01-08 → 2016-01-09 · 2016-01-09 → 2016-01-10 · 2016-01-10 → 2016-01-11
- 2016-01-11 → 2016-01-12 · 2016-01-12 → 2016-01-13 · 2016-01-13 → 2016-01-14 · 2016-01-14 → 2016-01-15 · 2016-01-15 → 2016-01-16
- 2016-01-16 → 2016-01-17 · 2016-01-17 → 2016-01-18 · 2016-01-18 → 2016-01-19 · 2016-01-19 → 2016-01-20 · 2016-01-20 → 2016-01-21
- 2016-01-21 → 2016-01-22 · 2016-01-22 → 2016-01-23 · 2016-01-23 → 2016-01-24 · 2016-01-24 → 2016-01-25 · 2016-01-25 → 2016-01-26
- 2016-01-26 → 2016-01-27 · 2016-01-27 → 2016-01-28 · 2016-01-28 → 2016-01-29 · 2016-01-29 → 2016-01-30 · 2016-01-30 → 2016-01-31
- 2016-01-31 → 2016-02-01 · 2016-02-01 → 2016-02-02 · 2016-02-02 → 2016-02-03 · 2016-02-03 → 2016-02-04 · 2016-02-04 → 2016-02-05
- 2016-02-05 → 2016-02-06 · 2016-02-06 → 2016-02-07 · 2016-02-07 → 2016-02-08 · 2016-02-08 → 2016-02-09 · 2016-02-09 → 2016-02-10
- 2016-02-10 → 2016-02-11 · 2016-02-11 → 2016-02-12 · 2016-02-12 → 2016-02-13 · 2016-02-13 → 2016-02-14 · 2016-02-14 → 2016-02-15
- 2016-02-15 → 2016-02-16 · 2016-02-16 → 2016-02-17 · 2016-02-17 → 2016-02-18 · 2016-02-18 → 2016-02-19 · 2016-02-19 → 2016-02-20
- 2016-02-20 → 2016-02-21 · 2016-02-21 → 2016-02-22 · 2016-02-22 → 2016-02-23 · 2016-02-23 → 2016-02-24 · 2016-02-24 → 2016-02-25
- 2016-02-25 → 2016-02-26 · 2016-02-26 → 2016-02-27 · 2016-02-27 → 2016-02-28 · 2016-02-28 → 2016-02-29 · 2016-02-29 → 2016-03-01
- 2016-03-01 → 2016-03-02 · 2016-03-02 → 2016-03-03 · 2016-03-03 → 2016-03-04 · 2016-03-04 → 2016-03-05 · 2016-03-05 → 2016-03-06
- 2016-03-06 → 2016-03-07 · 2016-03-07 → 2016-03-08 · 2016-03-08 → 2016-03-09 · 2016-03-09 → 2016-03-10 · 2016-03-10 → 2016-03-11
- 2016-03-11 → 2016-03-12 · 2016-03-12 → 2016-03-13 · 2016-03-13 → 2016-03-14 · 2016-03-14 → 2016-03-15 · 2016-03-15 → 2016-03-16
- 2016-03-16 → 2016-03-17 · 2016-03-17 → 2016-03-18 · 2016-03-18 → 2016-03-19 · 2016-03-19 → 2016-03-20 · 2016-03-20 → 2016-03-21
- 2016-03-21 → 2016-03-22 · 2016-03-22 → 2016-03-23 · 2016-03-23 → 2016-03-24 · 2016-03-24 → 2016-03-25 · 2016-03-25 → 2016-03-26
- 2016-03-26 → 2016-03-27 · 2016-03-27 → 2016-03-28 · 2016-03-28 → 2016-03-29 · 2016-03-29 → 2016-03-30 · 2016-03-30 → 2016-03-31
- 2016-03-31 → 2016-04-01 · 2016-04-01 → 2016-04-02 · 2016-04-02 → 2016-04-03 · 2016-04-03 → 2016-04-04 · 2016-04-04 → 2016-04-05
- 2016-04-05 → 2016-04-06 · 2016-04-06 → 2016-04-07 · 2016-04-07 → 2016-04-08 · 2016-04-08 → 2016-04-09 · 2016-04-09 → 2016-04-10
- 2016-04-10 → 2016-04-11 · 2016-04-11 → 2016-04-12 · 2016-04-12 → 2016-04-13 · 2016-04-13 → 2016-04-14 · 2016-04-14 → 2016-04-15
- 2016-04-15 → 2016-04-16 · 2016-04-16 → 2016-04-17 · 2016-04-17 → 2016-04-18 · 2016-04-18 → 2016-04-19 · 2016-04-19 → 2016-04-20
- 2016-04-20 → 2016-04-21 · 2016-04-21 → 2016-04-22 · 2016-04-22 → 2016-04-23 · 2016-04-23 → 2016-04-24 · 2016-04-24 → 2016-04-25
- 2016-04-25 → 2016-04-26 · 2016-04-26 → 2016-04-27 · 2016-04-27 → 2016-04-28 · 2016-04-28 → 2016-04-29 · 2016-04-29 → 2016-04-30
- 2016-04-30 → 2016-05-01 · 2016-05-01 → 2016-05-02 · 2016-05-02 → 2016-05-03 · 2016-05-03 → 2016-05-04 · 2016-05-04 → 2016-05-05
- 2016-05-05 → 2016-05-06 · 2016-05-06 → 2016-05-07 · 2016-05-07 → 2016-05-08 · 2016-05-08 → 2016-05-09 · 2016-05-09 → 2016-05-10
- 2016-05-10 → 2016-05-11 · 2016-05-11 → 2016-05-12 · 2016-05-12 → 2016-05-13 · 2016-05-13 → 2016-05-14 · 2016-05-14 → 2016-05-15
- 2016-05-15 → 2016-05-16 · 2016-05-16 → 2016-05-17 · 2016-05-17 → 2016-05-18 · 2016-05-18 → 2016-05-19 · 2016-05-19 → 2016-05-20
- 2016-05-20 → 2016-05-21 · 2016-05-21 → 2016-05-22 · 2016-05-22 → 2016-05-23 · 2016-05-23 → 2016-05-24 · 2016-05-24 → 2016-05-25
- 2016-05-25 → 2016-05-26 · 2016-05-26 → 2016-05-27 · 2016-05-27 → 2016-05-28 · 2016-05-28 → 2016-05-29 · 2016-05-29 → 2016-05-30
- 2016-05-30 → 2016-05-31 · 2016-05-31 → 2016-06-01 · 2016-06-01 → 2016-06-02 · 2016-06-02 → 2016-06-03 · 2016-06-03 → 2016-06-04
- 2016-06-04 → 2016-06-05 · 2016-06-05 → 2016-06-06 · 2016-06-06 → 2016-06-07 · 2016-06-07 → 2016-06-08 · 2016-06-08 → 2016-06-09
- 2016-06-09 → 2016-06-10 · 2016-06-10 → 2016-06-11 · 2016-06-11 → 2016-06-12 · 2016-06-12 → 2016-06-13 · 2016-06-13 → 2016-06-14
- 2016-06-14 → 2016-06-15 · 2016-06-15 → 2016-06-16 · 2016-06-16 → 2016-06-17 · 2016-06-17 → 2016-06-18 · 2016-06-18 → 2016-06-19
- 2016-06-19 → 2016-06-20 · 2016-06-20 → 2016-06-21 · 2016-06-21 → 2016-06-22 · 2016-06-22 → 2016-06-23 · 2016-06-23 → 2016-06-24
- 2016-06-24 → 2016-06-25 · 2016-06-25 → 2016-06-26 · 2016-06-26 → 2016-06-27 · 2016-06-27 → 2016-06-28 · 2016-06-28 → 2016-06-29
- 2016-06-29 → 2016-06-30 · 2016-06-30 → 2016-07-01 · 2016-07-01 → 2016-07-02 · 2016-07-02 → 2016-07-03 · 2016-07-03 → 2016-07-04
- 2016-07-04 → 2016-07-05 · 2016-07-05 → 2016-07-06 · 2016-07-06 → 2016-07-07 · 2016-07-07 → 2016-07-08 · 2016-07-08 → 2016-07-09
- 2016-07-09 → 2016-07-10 · 2016-07-10 → 2016-07-11 · 2016-07-11 → 2016-07-12 · 2016-07-12 → 2016-07-13 · 2016-07-13 → 2016-07-14
- 2016-07-14 → 2016-07-15 · 2016-07-15 → 2016-07-16 · 2016-07-16 → 2016-07-17 · 2016-07-17 → 2016-07-18 · 2016-07-18 → 2016-07-19
- 2016-07-19 → 2016-07-20 · 2016-07-20 → 2016-07-21 · 2016-07-21 → 2016-07-22 · 2016-07-22 → 2016-07-23 · 2016-07-23 → 2016-07-24
- 2016-07-24 → 2016-07-25 · 2016-07-25 → 2016-07-26 · 2016-07-26 → 2016-07-27 · 2016-07-27 → 2016-07-28 · 2016-07-28 → 2016-07-29
- 2016-07-29 → 2016-07-30 · 2016-07-30 → 2016-07-31 · 2016-07-31 → 2016-08-01 · 2016-08-01 → 2016-08-02 · 2016-08-02 → 2016-08-03
- 2016-08-03 → 2016-08-04 · 2016-08-04 → 2016-08-05 · 2016-08-05 → 2016-08-06 · 2016-08-06 → 2016-08-07 · 2016-08-07 → 2016-08-08
- 2016-08-08 → 2016-08-09 · 2016-08-09 → 2016-08-10 · 2016-08-10 → 2016-08-11 · 2016-08-11 → 2016-08-12 · 2016-08-12 → 2016-08-13
- 2016-08-13 → 2016-08-14 · 2016-08-14 → 2016-08-15 · 2016-08-15 → 2016-08-16 · 2016-08-16 → 2016-08-17 · 2016-08-17 → 2016-08-18
- 2016-08-18 → 2016-08-19 · 2016-08-19 → 2016-08-20 · 2016-08-20 → 2016-08-21 · 2016-08-21 → 2016-08-22 · 2016-08-22 → 2016-08-23
- 2016-08-23 → 2016-08-24 · 2016-08-24 → 2016-08-25 · 2016-08-25 → 2016-08-26 · 2016-08-26 → 2016-08-27 · 2016-08-27 → 2016-08-28
- 2016-08-28 → 2016-08-29 · 2016-08-29 → 2016-08-30 · 2016-08-30 → 2016-08-31 · 2016-08-31 → 2016-09-01 · 2016-09-01 → 2016-09-02
- 2016-09-02 → 2016-09-03 · 2016-09-03 → 2016-09-04 · 2016-09-04 → 2016-09-05 · 2016-09-05 → 2016-09-06 · 2016-09-06 → 2016-09-07
- 2016-09-07 → 2016-09-08 · 2016-09-08 → 2016-09-09 · 2016-09-09 → 2016-09-10 · 2016-09-10 → 2016-09-11 · 2016-09-11 → 2016-09-12
- 2016-09-12 → 2016-09-13 · 2016-09-13 → 2016-09-14 · 2016-09-14 → 2016-09-15 · 2016-09-15 → 2016-09-16 · 2016-09-16 → 2016-09-17
- 2016-09-17 → 2016-09-18 · 2016-09-18 → 2016-09-19 · 2016-09-19 → 2016-09-20 · 2016-09-20 → 2016-09-21 · 2016-09-21 → 2016-09-22
- 2016-09-22 → 2016-09-23 · 2016-09-23 → 2016-09-24 · 2016-09-24 → 2016-09-25 · 2016-09-25 → 2016-09-26 · 2016-09-26 → 2016-09-27
- 2016-09-27 → 2016-09-28 · 2016-09-28 → 2016-09-29 · 2016-09-29 → 2016-09-30 · 2016-09-30 → 2016-10-01 · 2016-10-01 → 2016-10-02
- 2016-10-02 → 2016-10-03 · 2016-10-03 → 2016-10-04 · 2016-10-04 → 2016-10-05 · 2016-10-05 → 2016-10-06 · 2016-10-06 → 2016-10-07
- 2016-10-07 → 2016-10-08 · 2016-10-08 → 2016-10-09 · 2016-10-09 → 2016-10-10 · 2016-10-10 → 2016-10-11 · 2016-10-11 → 2016-10-12
- 2016-10-12 → 2016-10-13 · 2016-10-13 → 2016-10-14 · 2016-10-14 → 2016-10-15 · 2016-10-15 → 2016-10-16 · 2016-10-16 → 2016-10-17
- 2016-10-17 → 2016-10-18 · 2016-10-18 → 2016-10-19 · 2016-10-19 → 2016-10-20 · 2016-10-20 → 2016-10-21 · 2016-10-21 → 2016-10-22
- 2016-10-22 → 2016-10-23 · 2016-10-23 → 2016-10-24 · 2016-10-24 → 2016-10-25 · 2016-10-25 → 2016-10-26 · 2016-10-26 → 2016-10-27
- 2016-10-27 → 2016-10-28 · 2016-10-28 → 2016-10-29 · 2016-10-29 → 2016-10-30 · 2016-10-30 → 2016-10-31 · 2016-10-31 → 2016-11-01
- 2016-11-01 → 2016-11-02 · 2016-11-02 → 2016-11-03 · 2016-11-03 → 2016-11-04 · 2016-11-04 → 2016-11-05 · 2016-11-05 → 2016-11-06
- 2016-11-06 → 2016-11-07 · 2016-11-07 → 2016-11-08 · 2016-11-08 → 2016-11-09 · 2016-11-09 → 2016-11-10 · 2016-11-10 → 2016-11-11
- 2016-11-11 → 2016-11-12 · 2016-11-12 → 2016-11-13 · 2016-11-13 → 2016-11-14 · 2016-11-14 → 2016-11-15 · 2016-11-15 → 2016-11-16
- 2016-11-16 → 2016-11-17 · 2016-11-17 → 2016-11-18 · 2016-11-18 → 2016-11-19 · 2016-11-19 → 2016-11-20 · 2016-11-20 → 2016-11-21
- 2016-11-21 → 2016-11-22 · 2016-11-22 → 2016-11-23 · 2016-11-23 → 2016-11-24 · 2016-11-24 → 2016-11-25 · 2016-11-25 → 2016-11-26
- 2016-11-26 → 2016-11-27 · 2016-11-27 → 2016-11-28 · 2016-11-28 → 2016-11-29 · 2016-11-29 → 2016-11-30 · 2016-11-30 → 2016-12-01
- 2016-12-01 → 2016-12-02 · 2016-12-02 → 2016-12-03 · 2016-12-03 → 2016-12-04 · 2016-12-04 → 2016-12-05 · 2016-12-05 → 2016-12-06
- 2016-12-06 → 2016-12-07 · 2016-12-07 → 2016-12-08 · 2016-12-08 → 2016-12-09 · 2016-12-09 → 2016-12-10 · 2016-12-10 → 2016-12-11
- 2016-12-11 → 2016-12-12 · 2016-12-12 → 2016-12-13 · 2016-12-13 → 2016-12-14 · 2016-12-14 → 2016-12-15 · 2016-12-15 → 2016-12-16
- 2016-12-16 → 2016-12-17 · 2016-12-17 → 2016-12-18 · 2016-12-18 → 2016-12-19 · 2016-12-19 → 2016-12-20 · 2016-12-20 → 2016-12-21
- 2016-12-21 → 2016-12-22 · 2016-12-22 → 2016-12-23 · 2016-12-23 → 2016-12-24 · 2016-12-24 → 2016-12-25 · 2016-12-25 → 2016-12-26
- 2016-12-26 → 2016-12-27 · 2016-12-27 → 2016-12-28 · 2016-12-28 → 2016-12-29 · 2016-12-29 → 2016-12-30 · 2016-12-30 → 2016-12-31
- 2016-12-31 → 2017-01-01

### WTO TP_B_0180 · 1 scope entries

Preserve this indicator as periodless. Historical year coverage requires a different indicator with a time dimension.

[Decision evidence](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/source_documents/wto_timeseries_api/f11682f54e43e8f758591f73af5b7bb1cef934a78515b1c125a27b1b38ffda1e)

Scope identifier `wto_timeseries_api|C071|specialist_historical|b884f9423eada6f5c55f3b31`

- 2016-01-01 → 2017-01-01

### WTO TP_B_0380 · 1 scope entries

Preserve this indicator as periodless. Historical year coverage requires a different indicator with a time dimension.

[Decision evidence](https://s3.console.aws.amazon.com/s3/object/data-collection-059416028963-us-east-1-an?region=us-east-1&prefix=research-data/source_documents/wto_timeseries_api/a41f34222f7f34d146672e72abc15817838c0c72a8d96392301eb944d79466c0)

Scope identifier `wto_timeseries_api|C071|specialist_historical|6b804af9bfb76b6b771edd03`

- 2016-01-01 → 2017-01-01

### medRxiv before launch · 57 scope entries

Retain the reviewed pre-launch exclusions through May 2019. Collect from launch onward and keep bioRxiv in its own scope.

[Decision evidence](https://www.cshl.edu/cshl-and-plos-partner-to-host-papers-on-medrxiv/)

Scope identifier `biorxiv_medrxiv_preprints|C145|specialist_historical|3540522538635609279083c7`

- 2016-01-01 → 2016-02-01 · 2016-02-01 → 2016-03-01 · 2016-03-01 → 2016-04-01 · 2016-04-01 → 2016-05-01 · 2016-05-01 → 2016-06-01
- 2016-06-01 → 2016-07-01 · 2016-07-01 → 2016-08-01 · 2016-08-01 → 2016-09-01 · 2016-09-01 → 2016-10-01 · 2016-10-01 → 2016-11-01
- 2016-11-01 → 2016-12-01 · 2016-12-01 → 2017-01-01 · 2017-01-01 → 2017-02-01 · 2017-02-01 → 2017-03-01 · 2017-03-01 → 2017-04-01
- 2017-04-01 → 2017-05-01 · 2017-05-01 → 2017-06-01 · 2017-06-01 → 2017-07-01 · 2017-07-01 → 2017-08-01 · 2017-08-01 → 2017-09-01
- 2017-09-01 → 2017-10-01 · 2017-10-01 → 2017-11-01 · 2017-11-01 → 2017-12-01 · 2017-12-01 → 2018-01-01 · 2018-01-01 → 2018-02-01
- 2018-02-01 → 2018-03-01 · 2018-03-01 → 2018-04-01 · 2018-04-01 → 2018-05-01 · 2018-05-01 → 2018-06-01 · 2018-06-01 → 2018-07-01
- 2018-07-01 → 2018-08-01 · 2018-08-01 → 2018-09-01 · 2018-09-01 → 2018-10-01 · 2018-10-01 → 2018-11-01 · 2018-11-01 → 2018-12-01
- 2018-12-01 → 2019-01-01 · 2019-01-01 → 2019-02-01 · 2019-02-01 → 2019-03-01 · 2019-03-01 → 2019-04-01 · 2019-04-01 → 2019-05-01
- 2019-05-01 → 2019-06-01

Scope identifier `biorxiv_medrxiv_preprints|C145|specialist_historical|424c40ae68f6ee9591af4874`

- 2016-01-01 → 2016-02-01 · 2016-02-01 → 2016-03-01 · 2016-03-01 → 2016-04-01 · 2016-04-01 → 2016-05-01 · 2016-05-01 → 2016-06-01
- 2016-06-01 → 2016-07-01 · 2016-07-01 → 2016-08-01 · 2016-08-01 → 2016-09-01 · 2016-09-01 → 2016-10-01 · 2016-10-01 → 2016-11-01
- 2016-11-01 → 2016-12-01 · 2016-12-01 → 2017-01-01 · 2017-01-01 → 2017-02-01 · 2017-02-01 → 2017-03-01 · 2017-03-01 → 2017-04-01
- 2017-04-01 → 2017-05-01

## Access and route barriers outside the interval audit

| Source or stream | Coverage or route gap | Repair method |
| --- | --- | --- |
| OpenAlex scholarly graph | The `newKeys` → `openalex-api-key` field passed the January 2016 cursor test. Daily collection uses publication dates. The account returned an upgrade requirement for update-date queries. | Daily on t3, C7 import of the 14 October 2026 public works snapshot from the 2016 publication-date floor, and an API catch-up lane between the snapshot and daily origin. Coverage reflects committed batches. [Collection operations](data-collection-processing/RESEARCH_FEEDS.md) |
| Japan KAKEN | The application ID in `newKeys` → `kaken-app-id` was accepted on 21 November 2026. The FY2016 query reported 31,059 project matches. | Daily snapshot of projects active in the current Japanese fiscal year on t3. C7 processes closed cohorts by research start fiscal year from FY2016. [Collection operations](data-collection-processing/RESEARCH_FEEDS.md) |
| Google Patents BigQuery | Athena verified January–March 2016 and all 69 months from January 2021 through September 2026. The revised September release added 16 publications and contains 25,732 distinct publications. The 21 November BigQuery source audit found September 24, 2026 as its latest publication date. | The controller timer `optima-patent-gap-catchup.timer` collects and verifies the 57 remaining months from April 2016 through December 2020 under the existing 50 GB query cap and four-query UTC daily allowance. The September verification query is `7e28b4c6-b5ce-4513-81af-8c4aeddb26a2`. The source coverage report is `7eab3a1a955c5fedc41079fe2635505df2aef4074807c45dad457733631d023a`. |
| Finlight | Verified historical windows run from 2021-01-01 through 2023-03-30 in the 12:43 UTC checkpoint. The next historical date is 2023-03-31, and daily coverage starts 2026-09-23. Earlier archive access remains unverified. | Confirm 2016–2020 entitlement. Continue the scoped backfill under its quota and release the accepted metadata batches through verified publication. |
| USPTO prosecution | The legacy C7 office-action and petition split route still requires validation. | Validate the existing split lane with dated original documents and independent publication receipts. |
| Personnel announcement archives | Published history starts in 2021. The independent C7 archive route needs split-lane validation. | Use permitted dated publisher archives for 2016–2020, validate the isolated collector, and report remaining unavailable years. |
| NIST robotics documents | The older C7 archive route still requires workspace and provider-scope validation. | Validate an original-document archive run on C7, then roll out within the existing limits. |
| GEM and IEA EV | Current public route evidence is discovery material or rejected downloads. | Validate the approved native API/export scope listed in the owner checklist. |
| 500 Global, France theses.fr, and Wefunder/Republic | The raw audit found discovery material or insufficient originals for metadata. | Collect and verify native company/cohort records, thesis metadata with the required artifact, or permitted campaign originals before marking the scopes covered. |

The owner checklist includes the other audited credential and scope gates for MarineTraffic, Open Supply Hub, and the conditional advertising and commercial feeds.

## Collection still in progress

The audit recorded 1,274 Copernicus scopes waiting for provider capacity. Keep them in the existing queue. This count is separate from the two failed ERA5 scopes above.

The delivery target and the provider’s actual publication history are tracked per source. See the January audit in the [data-source overview](data-source-overview.txt) for enabled routes still awaiting early-date verification, independent access layers, and the eight prior pauses or deferrals.

