#!/usr/bin/env python3
import argparse, sys
from corporate_disclosures import S3_ROOT, hkex_filings, upload
from clinicaltrials_studies import parse_date, period_bounds
def main():
 if len(sys.argv)>1 and sys.argv[1] in ("daily","historical"):
  from disclosure_collection import main as shared_main
  return shared_main("hkex")
 p=argparse.ArgumentParser(description="Collect HKEXnews filing metadata."); p.add_argument("period",choices=("day","month")); p.add_argument("date",type=parse_date); p.add_argument("--s3-key"); a=p.parse_args(); start,end=period_bounds(a.period,a.date)
 try:
  rows=hkex_filings(start,end); key=a.s3_key or f"hkex_filings_{a.period}_{start}_{end}.json"; dst=upload({"source":"HKEXnews","period":a.period,"startDate":str(start),"endDate":str(end),"filingCount":len(rows),"filings":rows},S3_ROOT+"hkex/"+key)
 except Exception as e: print(f"error: {e}",file=sys.stderr); return 1
 print(f"Uploaded {len(rows)} HKEX filings to {dst}"); return 0
if __name__=="__main__": raise SystemExit(main())
