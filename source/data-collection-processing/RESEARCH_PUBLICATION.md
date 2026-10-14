# Recurring SEC, regulatory and disclosure publication

`research_publication.py` discovers completed, committed task heads and queues
one partition per exact task. It uses existing source-specific curators and
the shared verified window publisher. Partial or failed refreshes cannot
replace published partitions. Successful refreshes of the same task replace
its partition only after the new release is uploaded and query counts match;
query failures roll back partition locations.

The enabled `optima-research-publication.timer` runs every 15 minutes. Each
run processes up to two windows for each of SEC, regulatory and disclosures.
Their existing Athena databases and original pilot tables are retained;
recurring tables have the `_windows` suffix.

The first live verified partitions contained 2,237 SEC filings, one regulatory
clinical-trial record, and 903 HKEX disclosures. These are individual verified
windows, not coverage totals or assertions that all collected data is published.

Task identity includes source, window, scope, collector and configuration.
Different scopes or universe versions can overlap. Consumers must deduplicate
record/observation identifiers across partitions and must not count repeated
company dimensions as separate companies. These are source observations for
future event reconstruction, not automatically unified events.

Company-profile Athena refresh is still separate outstanding work. This timer
does not publish EODHD cohorts or automatically approve identity matches.
