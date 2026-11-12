"""Read current service, schedule, queue and memory diagnostics on both hosts."""
from constellation.finish_aux_migration import remote,T3,M7

CODE='''import subprocess,json
def run(args):
 r=subprocess.run(args,text=True,capture_output=True);print(r.stdout);print(r.stderr)
run(['free','-m'])
run(['systemctl','list-units','--all','--state=failed,activating','optima-*.service','constellation-*.service','--no-pager'])
run(['systemctl','list-unit-files','optima-*.timer','constellation-*.timer','--no-pager'])
run(['systemctl','show','optima-market-publication.service','optima-news-publication.service','optima-specialist-publication.service','-p','Result','-p','ExecMainStatus'])
'''
def main():
 remote(T3,CODE+'''\nfrom pathlib import Path
from metadata_engine.runtime_db import Database
cfg=json.loads(Path('/home/ec2-user/data-collection-processing/config/metadata-engine.json').read_text());db=Database(cfg)
with db.tx()as c:
 c.execute('SELECT s.state source_state,j.state job_state,COUNT(*) jobs FROM engine_jobs j JOIN engine_sources s ON j.source_key=s.source_key GROUP BY s.state,j.state');print('METADATA',json.dumps(c.fetchall(),default=str))
 c.execute("SELECT source_key,state FROM engine_sources WHERE state<>'enabled'");print('PAUSED_METADATA',json.dumps(c.fetchall(),default=str))
from constellation.control import Control
c=Control();print('HISTORICAL_CONTROL',json.dumps(c.get('control'),default=str))
with c.db()as cursor:
 cursor.execute("SELECT status,COUNT(*) jobs FROM backfill_jobs GROUP BY status");print('HISTORICAL_QUEUE',json.dumps(cursor.fetchall(),default=str))
''')
 remote(M7,CODE+'''\nrun(['journalctl','--since','15 minutes ago','-u','optima-m7-aux-specialist-publication.service','-u','optima-m7-aux-market-publication.service','-u','optima-m7-aux-news-publication.service','-n','25','--no-pager'])
''')
if __name__=='__main__':main()
