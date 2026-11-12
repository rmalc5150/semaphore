"""Bounded core source replays followed by normal verified publication."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
commands=[['collect_daily.py','--only','uk','--max-windows','1','--max-pages','3'],
 ['collect_historical.py','2021-01-01','2026-10-09','--config',str(root/'config/core-historical-schedule.json'),'--only','ema','--max-windows','1','--max-pages','2'],
 ['people_social_collection.py','--social-only'],
 ['nmpa_baseline.py','inventory','2026-09-22','--max-pages','1'],
 ['reddit_collection.py'],
 ['news_operations.py'],
 ['patent_operations.py','daily','--max-pages','2','--max-windows','1'],
 ['patent_prosecution_operations.py','daily'],
 ['specialist_inputs.py','--mode','daily','--source','eia_battery_generators','--max-jobs','1','--pages','1','--publish','0'],
 ['repair_scope.py','daily','caiso_prices','--reason','caiso_columns','--pages','2'],
 ['repair_scope.py','daily','github_sdk','--reason','No space left','--pages','2'],
 ['repair_scope.py','daily','uspto_assignments','--reason','No space left','--pages','2'],
 ['repair_scope.py','historical','mlperf_results','--reason','No space left','--pages','1'],
 ['repair_scope.py','authenticated-historical','sam_gov_opportunities','--reason','source_http_429','--pages','1'],
 ['repair_scope.py','historical','europe_pmc_fulltext','--reason','source_retries_exhausted','--pages','1'],
 ['research_publication.py','--owners','regulatory','disclosures','social','--max-windows','3']]
for args in commands:
 print(json.dumps({'stage':'core_repair_started','command':args}),flush=True)
 try:code=subprocess.run([sys.executable,'-B',*args],cwd=root,timeout=600).returncode
 except subprocess.TimeoutExpired:code=124
 print(json.dumps({'stage':'core_repair_finished','command':args,'exit_code':code}),flush=True)
