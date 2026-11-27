"""Reviewed capture commands; controller and worker use the same allowlist."""
JOBS={
 'edinet-documents-daily':['specialist_inputs.py','--lane','authenticated','--mode','daily','--source','edinet_filings','--max-jobs','1','--pages','1','--publish','0'],
 'authenticated-processing':['specialist_inputs.py','--lane','authenticated','--mode','daily','--source','fda_dd_inspections_classifications','--max-jobs','1','--pages','2','--publish','0'],
 'eia-daily-processing':['specialist_inputs.py','--lane','authenticated','--mode','daily','--source','eia_retail_prices','--max-jobs','1','--pages','2','--publish','0'],
 'eodhd-profiles':['eodhd_daily_cohort.py','--top-up','--max-pages','2','--report-dir','/opt/constellation/capture-workers/eodhd-reports'],
 'patents-daily':['patent_operations.py','daily','--config','config/patent-operations.m7-bounded.json','--max-pages','30','--max-windows','1'],
 'patents-prosecution':['patent_prosecution_operations.py','tick','--config','config/patent-prosecution-operations.m7-bounded.json'],
 'assignments-reviewed-daily':['grants_review_capture.py','--sources','uspto_assignment_histories','--mode','daily','--universe','config/crossref-resumed-universe.json'],
 'assignments-reviewed-historical':['grants_review_capture.py','--sources','uspto_assignment_histories','--mode','historical','--universe','config/crossref-resumed-universe.json'],
 'federal-register-daily-enrichment':['federal_register_daily.py'],
 'nist-robotics-daily':['nist_robotics_pipeline.py','--mode','daily'],
}
import json
from pathlib import Path
STAGED={'federal-register-daily-enrichment','nist-robotics-daily'}
activation=Path(__file__).resolve().parents[1]/'config/m7-document-capture-active.json'
enabled=set(json.loads(activation.read_text()))if activation.exists()else set()
UNITS={'optima-'+name+'.service':'optima-m7-capture-'+name+'.service'for name in JOBS if name not in STAGED or name in enabled}
SOURCE_SCOPES={'edinet-documents-daily':'edinet_filings','authenticated-processing':'fda_dd_inspections_classifications','eia-daily-processing':'eia_retail_prices'}
