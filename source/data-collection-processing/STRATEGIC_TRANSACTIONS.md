# Strategic transaction collector

`strategic_transactions.py` collects and multi-labels biotech licensing
agreements, acquisitions, joint ventures, milestone payments, and royalty
agreements. Day and month runs use date-bounded news searches; structured or
licensed records can be added with repeatable `--input-jsonl` arguments.

```bash
python3 strategic_transactions.py day 2026-08-12
python3 strategic_transactions.py month 2024-01
python3 collect_historical.py 2024-01 2026-07 --only strategic-transactions --continue-on-error
```

Default output is written to:

```text
s3://processed-059416028963-us-east-1-an/strategic-transactions/
```

Input objects accept `source`, `title`, `text`, `url`, `publishedAt` or
`eventDate`. Optional structured overrides include `categories`, `parties`,
`assets`, `therapeuticAreas`, `geography`, and `status`. Outputs retain original
currencies and distinguish upfront, milestone, transaction-value, and
unspecified amounts. Classification and extraction are review-priority signals,
not confirmation that a transaction closed or a payment was received.
