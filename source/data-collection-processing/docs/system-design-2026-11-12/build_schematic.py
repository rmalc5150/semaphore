"""Build the verified system schematic as SVG, PNG, PDF and an offline viewer."""
from pathlib import Path
from html import escape
import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
W,H,S=1800,1610,2
INK='#142639';MUTED='#526578';BG='#f6f8fb';BLUE='#2e63b8';TEAL='#007f7d';PURPLE='#7750a7';GOLD='#b78325'
STAMP=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%d %B %Y · %H:%M %Z')
FONTS={}

class Canvas:
    def __init__(self):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
          '<title id="title">Optima current system schematic, 12 November 2026</title>',
          '<desc id="desc">Two-host AWS collection and metadata system: t3 controllers and remaining local capture; m7 historical workers, migrated processing and publishers; S3, MySQL, Glue, Athena, monitoring and shared lifecycle controls.</desc>',
          '<defs>'+''.join(f'<marker id="a{i}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto-start-reverse"><path d="M0,0 L10,4 L0,8 Z" fill="{c}"/></marker>'for i,c in enumerate((BLUE,TEAL,PURPLE,MUTED)))+'</defs>']
        self.im=Image.new('RGB',(W*S,H*S),BG);self.draw=ImageDraw.Draw(self.im)
        self.rect(0,0,W,H,BG,r=0)
    def font(self,size,bold=False):
        key=(size,bold)
        if key not in FONTS:FONTS[key]=ImageFont.truetype('/usr/share/fonts/cantarell/Cantarell-'+('Bold'if bold else'Regular')+'.otf',int(size*S))
        return FONTS[key]
    def rect(self,x,y,w,h,fill,stroke=None,r=14):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="1.5"'if stroke else'')+'/>')
        self.draw.rounded_rectangle((x*S,y*S,(x+w)*S,(y+h)*S),radius=r*S,fill=fill,outline=stroke,width=3 if stroke else 1)
    def text(self,x,y,value,size=20,color=INK,bold=False):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Cantarell,Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(str(value))}</text>')
        self.draw.text((x*S,y*S),str(value),font=self.font(size,bold),fill=color,anchor='ls')
    def wrapped(self,x,y,value,width,size=19,color=MUTED,leading=27):
        lines=[];line=''
        for word in value.split():
            candidate=(line+' '+word).strip()
            if self.font(size).getlength(candidate)/S>width and line:lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
        for line in lines:self.text(x,y,line,size,color);y+=leading
        return y
    def arrow(self,points,color=BLUE,dashed=False):
        idx=(BLUE,TEAL,PURPLE,MUTED).index(color)
        self.parts.append('<polyline points="'+' '.join(f'{x},{y}'for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"'+(' stroke-dasharray="7 6"'if dashed else'')+f' marker-end="url(#a{idx})"/>')
        for a,b in zip(points,points[1:]):
            if not dashed:self.draw.line([(a[0]*S,a[1]*S),(b[0]*S,b[1]*S)],fill=color,width=5)
            else:
                dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                for start in range(0,int(length),13):
                    end=min(start+7,length)
                    self.draw.line([((a[0]+dx*start/length)*S,(a[1]+dy*start/length)*S),((a[0]+dx*end/length)*S,(a[1]+dy*end/length)*S)],fill=color,width=5)
        (x0,y0),(x,y)=points[-2:];angle=math.atan2(y-y0,x-x0)
        head=[(x*S,y*S),((x-12*math.cos(angle)+5*math.sin(angle))*S,(y-12*math.sin(angle)-5*math.cos(angle))*S),((x-12*math.cos(angle)-5*math.sin(angle))*S,(y-12*math.sin(angle)+5*math.cos(angle))*S)]
        self.draw.polygon(head,fill=color)
    def card(self,x,y,w,h,title,lines,fill='#ffffff',stroke='#d9e1eb',color=INK,size=19,leading=25):
        self.rect(x,y,w,h,fill,stroke)
        self.text(x+18,y+32,title,21,color,True)
        at=y+62
        for line in lines:at=self.wrapped(x+18,at,line,w-36,size,leading=leading)+6
        assert at-leading-6<=y+h-6,(title,at,y+h)
    def save(self):
        (OUT/'system.svg').write_text('\n'.join(self.parts+['</svg>']))
        self.im.save(OUT/'system.png',optimize=True)
        self.im.save(OUT/'system.pdf','PDF',resolution=160,title='Optima current system schematic',author='Optima')

def diagram():
    c=Canvas()
    c.text(70,60,'OPTIMA',26,TEAL,True)
    c.text(70,110,'Current system design',42,INK,True)
    c.text(1030,65,STAMP,20,MUTED)
    c.text(1030,100,'Verified deployment · AWS us-east-1',20,MUTED)
    c.card(70,140,1660,85,'EXTERNAL DATA PROVIDERS',['APIs · filings · regulatory documents · scientific literature · market/news feeds · public datasets and archives'],size=20)
    c.rect(70,265,650,330,'#eaf1ff','#b5caed')
    c.rect(805,265,925,330,'#e6f5f2','#9fcfc8')
    c.text(90,300,'T3 · CONTROLLERS + LOCAL CAPTURE',24,BLUE,True)
    c.text(90,323,'t3.medium · 2 vCPU · 4 GiB nominal RAM',18,MUTED)
    c.text(825,300,'M7 · WORKER PROCESSING',24,TEAL,True)
    c.text(825,323,'m7i.large · 2 vCPU · 8 GiB nominal RAM · Linux',18,MUTED)
    c.card(90,340,285,133,'Local collection',[
        'Market/news, people, SAM.gov and small API capture.'],size=18)
    c.card(400,340,300,133,'Controllers + timers',[
        'Historical registration, metadata discovery/intake and m7 dispatch.'],size=18)
    c.card(90,490,610,83,'Health and readback checks',[
        'Local service checks + m7 execution snapshots through SSM.'],size=18)
    c.card(825,340,280,151,'Capture workers',[
        '15 historical executors.',
        '10 bounded lanes; EODHD, CMS and specialist catch-up.'],size=16,leading=22)
    c.card(1125,340,280,151,'Metadata workers',[
        'Validate raw evidence; extract document text and labels.',
        '2 lanes; 32 jobs / 210s each.'],size=16,leading=22)
    c.card(1425,340,285,151,'Publishers + verifier',[
        'Research, specialist, CMS, Crossref, FDA, grants, market, news, patents.',
        'Metadata + committed-Athena.'],size=16,leading=22)
    c.card(825,505,885,68,'Summary worker + shared resource pool',[
        'Queued gap/DB scans · 2 vCPU aggregate · 6.08 GiB soft / 6.76 GiB hard RAM · 20 GiB work volume'],size=16)
    c.arrow([(230,225),(230,265)])
    c.arrow([(960,225),(960,265)])
    c.arrow([(700,390),(825,390)],TEAL,True)
    c.text(729,376,'dispatch',15,TEAL);c.text(728,418,'EC2 / SSM',13,TEAL)
    c.arrow([(805,545),(700,545)],PURPLE,True)
    c.text(735,532,'SSM',16,PURPLE)
    c.arrow([(230,595),(230,665)])
    c.text(83,633,'committed capture',16,BLUE)
    c.arrow([(965,595),(965,625),(490,625),(490,665)])
    c.arrow([(490,665),(490,625),(965,625),(965,595)])
    c.text(572,617,'read raw · write labels / releases',17,BLUE)
    c.arrow([(1470,595),(1470,630),(1080,630),(1080,665)])
    c.text(1134,620,'catalogue + verify',17,BLUE)
    c.arrow([(1600,595),(1600,665)],TEAL,True)
    c.arrow([(1600,665),(1600,595)],TEAL,True)
    c.text(1496,652,'jobs / leases / graph',16,TEAL)
    c.rect(70,665,700,265,'#fff4d9','#e6d4a7')
    c.text(90,700,'S3 · EVIDENCE, RELEASES AND OPERATIONS',22,'#795513',True)
    c.text(90,728,'One shared collection bucket · research-data/',18,MUTED)
    c.card(90,744,660,72,'Original evidence',[
        'Raw bytes, normalized batches, checkpoints and immutable manifests.'],size=17)
    c.card(90,827,660,83,'Derived output + operational state',[
        'Parquet; queues and receipts; shared EODHD quota; summaries; health history.'],size=17)
    c.card(810,665,460,265,'GLUE + ATHENA',[
        'Glue registers schemas and partitions; Athena queries S3-backed tables and views.',
        'Publishers verify counts and readback before recording verified releases.',
        'Committed observations and metadata outputs remain separate analytical layers.'],fill='#fff4d9',stroke='#e6d4a7',size=19)
    c.card(1310,665,420,265,'RDS MYSQL · SHARED REGISTRY',[
        'semaphore · db.t4g.micro · MySQL 8.4.9',
        'constellation_operations: historical jobs, fenced leases, coverage and provider budgets.',
        'metadata_engine: intake jobs, cursors, artifacts, entities, evidence links and releases.'],fill='#fff4d9',stroke='#e6d4a7',size=18)
    c.arrow([(770,790),(810,790)])
    c.text(95,964,'Storage is durable; a completed process alone is not proof of verified data or complete coverage.',19,MUTED)
    c.arrow([(70,535),(35,535),(35,1055),(70,1055)],PURPLE,True)
    c.card(70,1000,350,172,'S3 HEALTH + HISTORY',[
        't3 collects host and m7 evidence.',
        'Current health, incidents, checks and recovery history.'],fill='#f1eafc',stroke='#cfbde4',size=19)
    c.card(470,1000,450,172,'INDEPENDENT WATCHDOG',[
        'EventBridge → Lambda every 30 minutes.',
        'CloudWatch logs and alarms provide an additional alert path.'],fill='#f1eafc',stroke='#cfbde4',size=19)
    c.card(970,1000,350,172,'SNS NOTIFICATIONS',[
        'Email and configured SMS paths.',
        'Delivery evidence is tracked separately from publish acceptance.'],fill='#f1eafc',stroke='#cfbde4',size=19)
    c.card(1370,1000,360,172,'OPERATOR / ANALYST',[
        'Receives alerts and reviews failures.',
        'Queries verified tables in Athena.'],fill='#f1eafc',stroke='#cfbde4',size=19)
    for x0,x1 in ((420,470),(920,970),(1320,1370)):c.arrow([(x0,1080),(x1,1080)],PURPLE)
    c.rect(70,1210,1040,220,'#ffffff','#b5caed')
    c.text(90,1245,'SHARED M7 LIFECYCLE · OWNED BY T3',22,BLUE,True)
    c.wrapped(90,1280,'Due work → serialized lifecycle lock → EC2 start if needed → SSM dispatch.',990,20,INK)
    c.wrapped(90,1320,'Every ~5 minutes: inspect eligible historical backlog, enabled metadata backlog, summary jobs, controller dispatches and active worker services.',990,19)
    c.wrapped(90,1380,'Stop only after 10 minutes of shared idle, then recheck activity. Busy or failed activity checks keep the instance running.',990,19)
    c.rect(1150,1210,580,220,'#eff2f5','#cbd3dd')
    c.text(1170,1245,'OUTSIDE THE ACTIVE PIPELINE',22,MUTED,True)
    c.wrapped(1170,1280,'Retired: tracking-dependent catalogue and matching jobs. Existing owner-requested source pauses remain in force.',540,19)
    c.wrapped(1170,1360,'Later model stages: event pipelines, specialist models, HMM and TFT training/testing. No corresponding services found on these hosts.',540,19)
    c.rect(70,1460,1660,73,'#e8edf3')
    c.text(90,1490,'SHARED ACCESS CONTROLS',18,INK,True)
    c.text(90,1516,'Scoped EC2 instance roles · Secrets Manager provider keys and separate DB logins · TLS · immutable evidence + conditional state updates',18,MUTED)
    c.text(70,1574,'Blue: data / publication     Dashed teal: execution / control     Purple: monitoring     Grey: retired or later-stage components',17,MUTED)
    c.save()

def inventory():
    mapping=[
      ('Controllers, schedules and m7 lifecycle','t3','Metadata discovery/intake, historical registration, SSM dispatch, shared autostop; systemd timers.'),
      ('Remaining local capture','t3','Market/news API capture, people, SAM.gov, reviewed ODP identifiers, ChiCTR and small public API/schedule checks.'),
      ('Health and daily readback audit','t3','Local systemd and evidence inspection plus real m7 execution snapshots; health and history persisted in S3.'),
      ('Native historical pool','m7','constellation-backfill@1..5: five configured native historical executors.'),
      ('Legacy historical pool','m7','constellation-legacy-worker@1..6: six configured isolated legacy executors.'),
      ('Public historical pool','m7','constellation-public-worker@1..4: four configured public artifact executors.'),
      ('Source-specific capture and document processing','m7','CMS coverage/discovery/payments; Crossref; FDA/Drugs@FDA; grants and NIH; Europe PMC and PubMed; NMPA; MHRA; EMA; PMDA; Canada NOC; disclosures; RSS repair; reviewed metadata continuation.'),
      ('Bounded migrated capture pool','m7','EDINET documents; FDA inspection classifications; EIA retail; EODHD profiles; patents daily and prosecution; assignment daily and historical; Federal Register document enrichment; NIST daily. Serialized under 2 GiB child-unit limits (EDINET 2.5 GiB), one CPU quota and 4.5 GiB shared-pool admission threshold (EDINET 4 GiB); durable state and shared provider pacing retained.'),
      ('EODHD inventory and CMS financial','m7','optima-m7-eodhd-inventory.service; optima-m7-cms-financial-resumed.service.'),
      ('Bounded specialist daily capture','m7','optima-m7-specialist-daily.service; source rotation with bounded discovery and durable cursors.'),
      ('Daily catch-up batch','m7','optima-m7-aux-collection-daily.service; t3 daily service is a dispatcher.'),
      ('Metadata engine workers','m7','optima-metadata-worker.service and optima-metadata-worker-extra.service, with timers; each batch accepts up to 32 jobs / 210 seconds. Service lanes do not equal concurrent database claims.'),
      ('Research publication','m7','optima-m7-research-publication.service. A bounded recovery unit and patent-petition publication unit also exist.'),
      ('Auxiliary publication','m7','Specialist; CMS catalogue/coverage; Crossref resumed plus an installed Crossref alias; FDA; grants; reviewed metadata; patent prosecution; market; news; metadata-engine publication.'),
      ('Committed-Athena index and verification','m7','optima-m7-committed-athena.service; t3 optima-committed-athena.service dispatches it.'),
      ('Queued gap audits and database summaries','m7','optima-m7-summary-worker.service. t3 enqueues/polls fixed-purpose S3 jobs and promotes completed reports.'),
      ('Independent watchdog','AWS Lambda','optima-collection-watchdog; enabled EventBridge Scheduler at :05 and :35 UTC (:05 and :35 CET); reserved alert state is in S3.'),
      ('Durable transactional state','RDS MySQL','semaphore, db.t4g.micro, MySQL 8.4.9, 20 GiB gp3 / 3,000 IOPS; constellation_operations and metadata_engine schemas.'),
      ('Durable evidence and releases','S3','data-collection-059416028963-us-east-1-an / research-data/. Logical stores in the schematic share this bucket.'),
      ('Analytical catalogue and query','Glue / Athena','Committed observation tables, metadata observations and owner-specific curated releases; verification receipts gate publication.'),
      ('API quota coordination','RDS + S3','Historical provider reservations, leases and cross-host USPTO/EDINET pacing use RDS. EODHD uses one conditional-write S3 counter across t3 and m7; daily ceiling 98,000, rolling rate 900/minute.'),
      ('Credentials and authorization','IAM / Secrets Manager','t3 role lambdaEc2ForEc2Instance; m7 role constellation-backfill-worker. API credentials and scoped database credentials are separate.'),
    ]
    pauses=json.loads((ROOT/'config/source-pauses.json').read_text())['sources']
    facts={'verified_date':'2026-11-12','display_timestamp':STAMP,'display_timezone':'Europe/Madrid','aws_region':'us-east-1',
      'scope':'Current Optima collection, processing, metadata, publication and monitoring deployment on the two identified EC2 hosts; model stages explicitly separated.',
      'hosts':{'t3':{'instance_id':'i-070bab0b09f794629','instance_type':'t3.medium','vcpus':2,'nominal_memory_gib':4},'m7':{'instance_id':'i-06241bd1c4e91c2fc','instance_type':'m7i.large','vcpus':2,'nominal_memory_gib':8,'work_volume_gib':20,'shared_memory_high_bytes':6526009344,'shared_memory_max_bytes':7260185395}},
      'rds':{'identifier':'semaphore','class':'db.t4g.micro','engine':'mysql','version':'8.4.9','storage_type':'gp3','storage_gib':20,'iops':3000,'throughput_mib_s':125,'schemas':['constellation_operations','metadata_engine']},
      'historical_executor_services':{'native':5,'legacy':6,'public':4},'source_pauses':pauses,
      'bounded_capture_pool':{'workers':10,'simultaneous_payloads':1,'unit_memory_max_bytes':2147483648,'slice_cpu_quota_percent':100,'shared_pool_admission_bytes':4831838208,'edinet_memory_max_bytes':2684354560,'edinet_admission_bytes':4294967296},
      'metadata_batch_limits':{'lanes':2,'max_jobs_per_lane':32,'max_seconds_per_batch':210},
      'model_stage_services_discovered':0,'retired':'tracking-dependent catalogue and matching jobs',
      'placement':[{'component':a,'execution':b,'details':d}for a,b,d in mapping],
      'evidence':['Live EC2 and RDS describe calls','Live systemd unit and template-instance inventories through SSM','Live Lambda configuration and EventBridge Scheduler configuration','constellation/m7_lifecycle.py','constellation/m7_research_publication_dispatch.py','constellation/m7_health.py','constellation/m7_summary_queue.py','config/constellation-infrastructure.json','config/metadata-engine.json','config/source-pauses.json','config/pipeline-health-registry.json','eodhd_quota.py'],
      'limitations':['Placement and design, not a certificate of complete data coverage or absence of source failures.','Small API capture and daily readback remain on t3; document processing, migrated capture, publishers and summaries run on m7.','Metadata-controller cycles currently dispatch the metadata publisher unconditionally, so they can wake m7 even with empty queues; the guard protects idle shutdown but this is not purely backlog-triggered startup.','No event/model-stage systemd services found on the inspected hosts; their monitoring registry entries do not prove deployment.','Historical source modules still contain older c7i labels; the live worker instance is m7i.large.','AWS acceptance of an SNS publish does not prove notification delivery.','Worker service counts are not job throughput or simultaneous database claim counts.']}
    (OUT/'deployment-facts.json').write_text(json.dumps(facts,indent=2))
    rows=''.join('<tr><td>'+escape(a)+'</td><td>'+escape(b)+'</td><td>'+escape(d)+'</td></tr>'for a,b,d in mapping)
    svg=(OUT/'system.svg').read_text()
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Optima current system design</title><style>
body{margin:0;background:#f6f8fb;color:#142639;font:17px/1.6 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:28px}nav{display:flex;gap:20px;flex-wrap:wrap}a{color:#2459a8}figure{margin:24px 0;background:white;border:1px solid #d9e1eb;border-radius:16px;overflow:auto}svg{display:block;width:100%;height:auto;min-width:1050px}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;vertical-align:top;padding:13px;border-bottom:1px solid #d9e1eb}th{background:#e8edf3}td:nth-child(2){white-space:nowrap;font-weight:600}.note{padding:18px 22px;background:#eaf1ff;border-radius:12px}code{font-size:.9em}h2{margin-top:35px}@media print{body{background:white;font-size:11px}main{padding:0}nav{display:none}figure{break-after:page;border:0}svg{min-width:0;width:100%}tr{break-inside:avoid}.note{background:#f5f7fa}@page{size:A3 landscape;margin:10mm}}
</style><main><h1>Optima — current system design</h1><p>__STAMP__ · Live placement and shared AWS services. This document shows the deployed collection and metadata system, with retired and later-stage components marked separately.</p><nav><a href="system.svg">Vector schematic</a><a href="system.pdf">PDF</a><a href="system.png">PNG</a><a href="system.mmd">Editable Mermaid source</a><a href="deployment-facts.json">Verified design facts</a></nav><figure>__SVG__</figure>
<h2>Execution and ownership</h2><table><thead><tr><th>Component</th><th>Execution / store</th><th>Current responsibility</th></tr></thead><tbody>__ROWS__</tbody></table>
<h2>Start and stop behavior</h2><p>The controller on t3 takes the shared lifecycle lock, starts m7 if needed, waits for SSM readiness, and dispatches the allowed worker unit. The shared autostop timer checks approximately every five minutes. Eligible historical backlog, enabled metadata backlog, unfinished summary jobs, local dispatch activity and active remote worker services keep m7 running. After ten minutes of shared idle, it checks again before stopping EC2. An activity-check failure does not authorize shutdown.</p><p><strong>Current wake-up behavior:</strong> each metadata-controller cycle unconditionally dispatches the metadata publisher before discovery. That cycle can wake m7 even when its queues are empty. The shared guard protects shutdown; startup is currently driven by these timers as well as work dispatch, rather than exclusively by a nonempty backlog.</p>
<h2>Data and publication boundaries</h2><p>Collectors preserve original evidence and commit manifests/checkpoints in S3. Metadata workers validate committed inputs, retain provenance, write labelled outputs and record entities/evidence links in the current metadata registry. Publishers prepare curated releases, register Glue partitions and verify Athena counts/readback; immutable receipts establish successful publication. RDS holds the transactional queues and graph. S3 holds source bytes, derived data and operational objects. Some provider budgets are RDS-backed; EODHD shares a single conditional-write S3 counter across the two hosts.</p>
<h2>Owner controls and later stages</h2><p>Configured source pauses: __PAUSES__. The abandoned <code>tracking</code> dependencies and their catalogue/matching jobs are retired. Product search uses the current <code>metadata_engine</code> registry and awaits eligible product entities. Event pipelines, specialist models, HMM and TFT training/testing have monitoring registry entries, but no corresponding services were found on either inspected host.</p>
<div class="note"><strong>Processing placement:</strong> market/news APIs, people, SAM.gov, small API capture and daily readback remain on t3. Ten additional bounded capture lanes, including EDINET, patent/assignment processing, EODHD profiles, Federal Register and NIST documents, join the publishers, committed-Athena, historical pools, metadata workers and queued summaries on m7. This schematic does not assert complete historical coverage or that every source error has been resolved.</div>
<h2>Verification notes</h2><p>Based on live EC2/RDS descriptions, systemd inventories on both hosts, the independent Lambda/Scheduler configuration and the current lifecycle, queue, metadata and monitoring code. The m7 worker pool has an aggregate two-vCPU quota and 6.76 GiB hard memory limit, leaving memory for Linux and system services. Its 20 GiB work volume contains code, local indexes and working files. Older historical-module labels that say “c7i” refer to routes now executing on the identified m7i.large instance. SNS acceptance and actual email/SMS delivery are distinct observations.</p></main></html>'''
    (OUT/'index.html').write_text(html.replace('__STAMP__',escape(STAMP)).replace('__SVG__',svg).replace('__ROWS__',rows).replace('__PAUSES__',escape(', '.join(pauses))))

if __name__=='__main__':
    diagram();inventory()
    print(json.dumps({'output_directory':str(OUT),'files':sorted(p.name for p in OUT.iterdir())}))
