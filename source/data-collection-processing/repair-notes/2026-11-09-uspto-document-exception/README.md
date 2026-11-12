# Exact USPTO document exception — November 9, 2026

Owner instruction: “Skip document MMOWZII4X158X88.”

Applied only to office-action document MMOWZII4X158X88 in application 35526479. The existing exception for application 16545140 remains separate. Other documents in application 35526479 still require normal retrieval.

- Updated the exception registry, collector matching and payload schema. Nineteen prosecution tests passed, including rejection of an exclusion applied to a different document in the same application.
- Verified the actual saved provider row now returns `excluded_by_owner` without making a provider request; no PDF capture is claimed. See live-verification.json.
- Archived the prior failed document receipt immutably before applying the exception. Original provider responses and the November 9 missing-list/HTTP 403 probe remain retained.
- Deployed the collector, registry and schema to daily/historical workspaces. Normal prosecution service continuation was requested using the existing shared lock.
- Removed the USPTO support task from the current owner action list. Full-window completion and Athena publication still require their normal verified receipts.
