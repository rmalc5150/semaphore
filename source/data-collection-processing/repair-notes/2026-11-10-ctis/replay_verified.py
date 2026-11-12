"""Replay only the four validated Finlight jobs with normal source locks and lease fencing."""
import json,time,uuid
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import process
IDS=('0455c691453a545ad64b4f3574d836c1a522dd058b68a2eea6a16a9e3cff56b1', '221477e16aad67c55eaadf268d0ed6f2526bbf91399e6dd8e6540d4c23d513d2', '88221e6d453ae350ea9cf6a48800deb055c9df2e4f6d58828b5371e639aa8289', 'd8b3db30c22e1bc5009126acf9701646341a9bc55ffda00a054ed0302eb66043', 'd4f6c42325bec4e41daf2b53753f840c8884bf6a2822133af4c2818827a2ac12', '97d304a7cd9437ee19f47474ea6e237600143244f34ac7ba46f8051ce0ceda97', '507966aa5adc6c5159e47a571744d231cb42f2948a4cdc5d24502ed728eee9c8', '88166356612a9dc9e70ec797348aabb27ba28b2fa561bf0e81cd0b0e7a6fb1b6', '686b1d44445b4a24cfe11662a5e74e7ff180eadab463a091cdb2fe7f8db58f26', 'f553d52426e6d8abdc7850e627db18ccdc607e993f21df2f0e4ea2fbbbaff1f5', '521be4d948a8e8df0e27e79b4cb859025e97c429c9d8b2097bde217750303480', 'f0a68e22aeafe98f657f67175088b68615b0a458cc5a94b5fd18eacace5a7aba', '1f3d48c35d1d791b5aafa4d35188c6bcb377e8b4592abe8a10a58ddcbd0a14cc', '1f38d754a768bf679751ed6835e029bfaa8ebbb7a27f38321d88e27b7b210194', 'dca10ec184dd14ab9714ad80b02b5a0e8bc19d5fe440409bf9992d428df6f6a8', '2345b09eddf08c6d3f7b2ee25831d1aecd7f778769ea4f3e207c1001001d9f12', '765bb0aea20a9d5bfe93d19eeb786caf9d1013f2bc2dd89a8e8fa28ebdbcde9b')
config=json.loads(Path('config/metadata-engine.json').read_text());db=Database(config);s3=db.session.client('s3');started=time.monotonic()
for _ in range(len(IDS)):
 with db.tx()as c:
  c.execute("SELECT state FROM engine_sources WHERE source_key='ema_ctis' FOR UPDATE SKIP LOCKED");source=c.fetchone()
  if not source or source['state']!='enabled':break
  c.execute("SELECT job_id FROM engine_jobs WHERE source_key='ema_ctis' AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1")
  if c.fetchone():break
  c.execute("SELECT * FROM engine_jobs WHERE source_key='ema_ctis' AND job_id IN %s AND state IN ('queued','retry') ORDER BY job_id LIMIT 1 FOR UPDATE",(IDS,));job=c.fetchone()
  if not job:break
  token=str(uuid.uuid4());c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']));c.execute("UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key='ema_ctis'");job['lease_token']=token
 process(db,s3,config,job)
 if time.monotonic()-started>240:break
with db.tx()as c:
 c.execute("SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id IN %s",(IDS,));results=c.fetchall()
print(json.dumps({'verified_replay_results':results},default=str),flush=True)
if any(r['state']!='accepted'for r in results):raise SystemExit(2)
