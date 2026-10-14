#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime,timezone
import boto3
from sec_athena_pilot import run_query
ROOT=Path(__file__).resolve().parent
client=boto3.client('athena',region_name='us-east-1');rows=[]
for config_name,tables in [('eodhd-athena.json',['listing_inventory','company_profiles']),('patent-athena.json',['patent_publications','patent_assignment_histories','patent_assignment_events','patent_backfill_records'])]:
 config=json.loads((ROOT/'config'/config_name).read_text());db=config['database'];wc=client.get_work_group(WorkGroup=config['workgroup'])['WorkGroup']['Configuration'];assert wc.get('BytesScannedCutoffPerQuery')==104857600 and wc.get('EnforceWorkGroupConfiguration')
 sql=' UNION ALL '.join(f"SELECT '{t}' AS table_name,count(*) AS records FROM {db}.{t}" for t in tables)+' ORDER BY table_name'
 try:result={'database':db,'status':'query_succeeded','query':run_query(client,{'config':config},sql),'checked_at':datetime.now(timezone.utc).isoformat()}
 except Exception as exc:result={'database':db,'status':'failed','error_type':type(exc).__name__}
 rows.append(result)
(ROOT/'reports/source-pilot-query-verification.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True)
