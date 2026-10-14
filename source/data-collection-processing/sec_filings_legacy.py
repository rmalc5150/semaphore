#!/usr/bin/env python3
"""Compatibility entrypoint for the existing SEC/HKEX disclosure pipeline."""
import argparse
import sys
from corporate_disclosures import S3_ROOT, sec_filings, upload
from clinicaltrials_studies import parse_date, period_bounds


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("period", choices=("day", "month"))
    p.add_argument("date", type=parse_date)
    p.add_argument("--s3-key")
    a = p.parse_args(argv)
    start, end = period_bounds(a.period, a.date)
    try:
        rows = sec_filings(start, end)
        key = a.s3_key or f"sec_filings_{a.period}_{start}_{end}.json"
        dst = upload({"source": "SEC EDGAR", "period": a.period, "startDate": str(start),
                      "endDate": str(end), "filingCount": len(rows), "filings": rows}, S3_ROOT + "sec/" + key)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Uploaded {len(rows)} SEC filings to {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
