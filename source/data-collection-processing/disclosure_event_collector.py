#!/usr/bin/env python3
import argparse, sys
from corporate_disclosures import S3_ROOT, EVENT_RULES, classify, read_s3, upload
from clinicaltrials_studies import parse_date, period_bounds
def run(category, description):
 if len(sys.argv)>1 and sys.argv[1] in ("daily","historical"):
  from disclosure_collection import main as shared_main
  return shared_main(category)
 p=argparse.ArgumentParser(description=description); p.add_argument("period",choices=("day","month")); p.add_argument("date",type=parse_date); p.add_argument("--s3-key"); a=p.parse_args(); start,end=period_bounds(a.period,a.date)
 sec_key=f"sec_filings_{a.period}_{start}_{end}.json"; hk_key=f"hkex_filings_{a.period}_{start}_{end}.json"
 try:
  sec=read_s3(S3_ROOT+"sec/"+sec_key).get("filings",[]); hk=read_s3(S3_ROOT+"hkex/"+hk_key).get("filings",[]); events=classify(category,sec,hk)
  key=a.s3_key or f"{category}_{a.period}_{start}_{end}.json"; dst=upload({"classification":category,"period":a.period,"startDate":str(start),"endDate":str(end),"methodology":{"keywords":EVENT_RULES[category]["keywords"],"secForms":EVENT_RULES[category]["sec_forms"],"note":"Keyword/form classification; review confidence and matchedTerms before treating an event as confirmed."},"eventCount":len(events),"events":events},S3_ROOT+"events/"+category+"/"+key)
 except Exception as e: print(f"error: {e}",file=sys.stderr); return 1
 print(f"Uploaded {len(events)} {category} events to {dst}"); return 0
