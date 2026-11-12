"""Bounded replay list; each scope records its own capture/publication receipt."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
jobs=[['historical','cpsc_recalls','--reason','cpsc_missing','--pages','2'],
 ['daily','caiso_prices','--reason','caiso_columns','--pages','2'],
 ['daily','nih_reporter','--reason','source_http_404','--pages','2'],
 ['authenticated-historical','eia_retail_prices','--reason','authenticated_source_request_failed','--pages','4'],
 ['authenticated-historical','fda_ires_recalls','--reason','source_http_503','--pages','4'],
 ['daily','ted_notices','--reason','record exceeds','--pages','1'],
 ['authenticated-historical','edinet_filings','--reason','edinet_zip_expansion_limit','--pages','1'],
 ['historical','europe_pmc_fulltext','--reason','source_retries_exhausted','--pages','1'],
 ['daily','usgs_minerals','--reason','source_retries_exhausted','--pages','1']]
for args in jobs:
 print(json.dumps({'stage':'repair_batch_scope','arguments':args}),flush=True)
 try:
  code=subprocess.run([sys.executable,'-B',str(root/'repair_scope.py'),*args],timeout=900).returncode
 except subprocess.TimeoutExpired:code=124
 print(json.dumps({'stage':'repair_batch_scope_end','arguments':args,'exit_code':code}),flush=True)
