# Full raw-data source audit — initial conservative register

Checked 2026-10-30T15:48:22Z. This is a reconciliation of all 158 catalog entries against the
October 30 status evidence, committed-manifest summary, collector-status notes,
and the documented bounded SEC pilot. It did not run collectors, alter schedules,
purchase access, or restart owner-paused sources.

## Result

| Outcome | Entries |
| --- | ---: |
| `access_blocked` | 42 |
| `access_layer_only` | 4 |
| `metadata_only` | 1 |
| `not_tested` | 12 |
| `owner_paused` | 4 |
| `partial_content` | 94 |
| `verified_sample_complete` | 1 |

The register is [raw-source-audit-register.json](constellation/status/raw-source-audit-register.json)
and [CSV](constellation/status/raw-source-audit-register.csv). Each catalog entry
has one outcome. `partial_content` means that rows/manifests/artifact signals
exist, not that substantive original content was checked. Thus it is not a
success state for contract acceptance.

## Only verified raw sample

`sec_edgar` is the sole `verified_sample_complete` result. The bounded SEC
pilot verified original accession `0000950170-24-067660` (CRISPR Therapeutics
AG 8-K): 931,431 bytes, 11 embedded documents, SHA-256
`ca11cb9b18e68330810e97f392f72c3051eaaa1900117053e9cca7580a927e21`, including
independent S3 read-back. This does not certify SEC corpus, form, exhibit, or
historical completeness.

Europe PMC metadata is explicitly `metadata_only`: the current metadata route
does not demonstrate original publication full text or supplements. The contract
must require those raw artifacts when the use case requires them.

## Bounded payload probe

On 30 October 2026 this audit host ran the read-only validator against the
latest `sec_edgar` final-manifest sample. The attempt stopped before reading S3
with `NoCredentialsError: Unable to locate credentials`. This is an audit-host
credential-path failure, not a source or payload result, and it does not alter
the separately documented SEC pilot validation. The validator is
`constellation/status/validate_bounded_raw_samples.py`; run it on the m7i
worker under its instance role to produce payload checksum/MIME evidence.

## Required next audit pass

For every `partial_content` source, choose a bounded committed final manifest
and raw object; record URI, checksum, byte count, identity, MIME/content test,
and required-artifact check. Reject HTML block/discovery pages. Then update only
the affected entry to `verified_sample_complete` if the specific sample passes.
For `access_blocked`, preserve the stated entitlement/credential/owner path and
do not infer provider unavailability. `access_layer_only` entries are not
providers and must remain non-certifying routes.

Status evidence is deliberately preserved per entry in the machine-readable
register. Its report-date provenance is `data-source-status-2026-10-26.md`,
refreshed 30 October 2026; the file name has not been renamed.
