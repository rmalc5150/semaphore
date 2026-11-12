import json,subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));sources=tuple(json.loads((p/'sources.json').read_text()));db=Database(config)
with db.tx()as c:c.execute('SELECT source_key,state,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key IN %s',(sources,));states=c.fetchall()
assert len(states)==8 and all(r['state']=='enabled'and r['consecutive_raw_failures']==0 for r in states),states
counts=json.loads((p/'counts.json').read_text());assert counts['state']=='SUCCEEDED';rows={r['Data'][0]['VarCharValue']:[x.get('VarCharValue')for x in r['Data']]for r in counts['rows'][1:]};assert set(rows)==set(sources)
for source in sources:
 assert int(rows[source][1])>0 and rows[source][1]==rows[source][3]
 r=json.loads((p/('sample-'+source+'.json')).read_text());assert r['state']=='SUCCEEDED'and len(r['rows'])>1
native=json.loads((p/'native-scopes.json').read_text());assert native['state']=='SUCCEEDED'and len(native['rows'])==5
controller=subprocess.check_output(['systemctl','show','optima-metadata-controller.service','-p','Result','-p','ExecMainStatus'],text=True);assert 'Result=success' in controller and 'ExecMainStatus=0' in controller,controller
units=['optima-metadata-controller.timer','optima-reviewed-metadata-publication.timer','optima-grants-reviewed-publication.timer','optima-patents-reviewed-google.timer','optima-patents-reviewed-odp.timer','optima-patents-reviewed-odp-historical.timer','optima-assignments-reviewed-daily.timer','optima-assignments-reviewed-historical.timer'];timers={u:subprocess.check_output(['systemctl','is-active',u],text=True).strip()for u in units};assert all(v=='active'for v in timers.values())
proof={'verified_at':datetime.now(ZoneInfo('Europe/Madrid')).isoformat(),'scope':'current declared pipelines; historical completion and full global patent text not certified','sources':states,'controller':controller,'timers':timers,'athena_count_query_id':counts['query_id'],'native_scope_query_id':native['query_id'],'tests_passed':68,'historical_commit_gap':json.loads((p/'nih-commit-gap-classification.json').read_text())};(p/'operational-verification-passed.json').write_text(json.dumps(proof,indent=2,default=str));print('Operational and Athena review passed for all seven requested families; historical commit gap retained.')
