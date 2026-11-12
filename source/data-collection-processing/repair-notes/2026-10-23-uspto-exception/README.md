# USPTO application 16545140 document exception

Authorized by the account owner on October 23, 2026. The exception applies only to office-action document-list/PDF retrieval for application 16545140. Other applications and petition decisions retain their normal retrieval/error handling.

Available index metadata is retained. Exception records carry `document_retrieval_status = excluded_by_owner`, the exact decision in `payload.data.document_exception`, and an immutable hashed copy of that decision in S3 source evidence. The exception does not claim the documents do not exist, were downloaded, or have verified historical availability. Existing successful PDFs remain usable.

Configuration: `config/patent-document-exceptions.json`. Deactivate its decision to resume document retrieval; an exception cache is not treated as a successful downloaded-document cache. Original failure evidence is retained. The previously required owner support task has been removed from the consolidated TODO.

Validation: 28 prosecution and monitoring tests pass, including metadata retention, no call to the excluded endpoint, other-application denial propagation, revocation, and preservation of normal PDF requirements.

Live replay and Athena evidence are recorded alongside this file. A bounded partial window is not complete history.

## Verified result

At 10:34 Madrid time on October 23, the original January 1, 2021 office-action scope advanced from **545 to 550 committed records**. Its current stop reason is `page_limit` (bounded continuation), replacing the application-specific HTTP 403. The historical day remains unfinished; no dates or records were falsely marked complete.

Shared Athena publication succeeded. Query `8e8c4908-5e74-4ba0-a589-2f47ed47c103` returned the application 16545140 record and confirmed `excluded_by_owner` plus the explicit decision. See `athena-verification.json` and `verify.sql`. The broader new USPTO batch verification was `0c083e9d-e8c5-4742-aa6c-3e0c6ea36c79` (35 records, including other committed work).

Monitoring suppresses only HTTP 403 outcomes with the exact application's document endpoint and matching active decision. Other application denials, undiagnosed 403s and all raw failure history remain intact. Removing the decision re-enables both retrieval and alerting.

The first replay could not acquire the shared lock and did not execute. The priority replay checkpointed workers, completed the page and Athena publication, and restored every pre-maintenance timer state. Paused Marketaux, Reddit, Bluesky and GitHub schedules remain paused. There is no account-owner support task remaining for this exception.

Final monitoring verification: no prosecution issues reported; verified progress timestamp is 08:34:12 UTC. The active `optima-patents-prosecution.service:source_http_403` incident is absent after reconciliation. No alerts were sent. All 65 previously active timers restored with zero mismatches.
