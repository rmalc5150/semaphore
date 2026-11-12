"""Install the tested metadata runtime schema, source policies and schedules.

Run on t3. Master credentials are used only for the additive migration. Worker
and controller runtime use the existing scoped metadata-engine credential.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import tarfile
import tempfile

from rds_management_access import settings
from metadata_engine_provision import mysql
from metadata_engine.source_policies import build
from metadata_engine.runtime_db import Database,encoded
from metadata_engine.controller import register_contract

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true');p.add_argument('--deploy-only',action='store_true');a=p.parse_args()
    session,instance,admin,bucket=settings()
    sql=(ROOT/'schemas/rds-metadata-runtime-v2.sql').read_text()
    if not a.deploy_only:mysql(instance,admin,sql)
    monitoring=json.loads((ROOT/'config/collection-monitoring.json').read_text())
    config={'version':'2.0.0','region':'us-east-1','bucket':bucket,
        'prefix':'research-data/constellation-backfill/metadata-engine/runtime-v2','db_secret':'metadata-engine/worker',
        'athena_database':'optima_metadata_engine','athena_workgroup':'optima-collected-data',
        'email_topic_arn':monitoring['email_topic_arn'],'email_recipient':monitoring['email'],
        'scan_page_size':10,
        # Reviewed sources keep running when an individual collection date has
        # no usable raw data.  Their date queue and pipeline-error queue are
        # installed separately and are reviewed before expanding this list.
        'verified_source_failure_handling':{
            'gleif_legal_entities':'queue_by_source_date',
            'eodhd':'queue_by_source_date',
            'eodhd_market':'queue_by_source_date',
            'hkex_prices':'queue_by_source_date',
            'sec_edgar':'queue_by_source_date',
            'sec_companyfacts':'queue_by_source_date',
            'edinet_filings':'queue_by_source_date',
            'finlight':'queue_by_source_date',
            'people_rss':'queue_by_source_date',
            'personnel_archive':'queue_by_source_date',
            'clinicaltrials_gov':'queue_by_source_date',
            'ema_ctis':'queue_by_source_date',
            'fda_openfda':'queue_by_source_date',
            'drugsfda_applications':'queue_by_source_date',
            'ema_medicines':'queue_by_source_date',
            'canada_noc':'queue_by_source_date',
            'chictr':'queue_by_source_date',
            'nmpa_trials':'queue_by_source_date',
            'pubmed_abstracts':'queue_by_source_date','europe_pmc_fulltext':'queue_by_source_date','crossref_proceedings':'queue_by_source_date','fda_dd_compliance_actions':'queue_by_source_date','fda_dd_import_refusals':'queue_by_source_date','fda_dd_inspections_citations':'queue_by_source_date','fda_ires_recalls':'queue_by_source_date','fda_product_codes':'queue_by_source_date','nih_reporter':'queue_by_source_date','nist_robotics_methods':'queue_by_source_date','nist_robotics_documents':'queue_by_source_date','usa_spending':'queue_by_source_date','ted_notices':'queue_by_source_date','uspto_assignment_histories':'queue_by_source_date','uspto_odp':'queue_by_source_date','google_patents_bigquery':'queue_by_source_date','cms_payments_catalog':'queue_by_source_date','cms_coverage':'queue_by_source_date','cms_coverage_documents':'queue_by_source_date',
            'uk_mhra':'queue_by_source_date',
            'japan_pmda':'queue_by_source_date',
        },
        'contracts':build(ROOT)}
    infra=json.loads((ROOT/'config/constellation-infrastructure.json').read_text())
    config.update(collection_host=infra['db_host'],collection_worker_secret=infra['worker_secret_arn'],collection_controller_secret=infra['controller_secret_arn'])
    config['build_sha256']=hashlib.sha256(b''.join(path.read_bytes() for path in sorted((ROOT/'metadata_engine').glob('*.py')))+(ROOT/'hkex_originals.py').read_bytes()).hexdigest()
    db=Database(config,session)
    if not a.deploy_only:
        with db.tx() as cursor:
            for contract in config['contracts'].values():register_contract(db,contract,cursor)
    names=['hkex_originals.py','collection_storage.py','research_contract.py','schemas/research-data.schema.json','test_metadata_engine.py','test_metadata_sec_documents.py','test_metadata_runtime.py','metadata_engine_sec_document_pilot.py','config/rds-us-east-1-ca-bundle.pem','config/constellation-source-registry.json','config/constellation-specialist-historical.json','config/constellation-public-sources.json']
    # Pure source validators reuse deterministic collector parsers.
    names += ['chictr_studies.py', 'clinicaltrials_studies.py', 'corporate_disclosures.py', 'decodo_scraping_api.py', 'ema_ctis_actions.py', 'fda_access.py', 'historical_policy.py', 'japan_pmda_designations.py', 'mhra_product_enrichment.py', 'nist_robotics.py', 'nmpa_drug_trials.py', 'nmpa_enrichment.py', 'patent_adjudication.py', 'patent_assignments.py', 'patent_bigquery_access.py', 'patent_bigquery_collection.py', 'patent_collection.py', 'patent_landscape.py', 'patent_prosecution.py', 'patent_query_plan.py', 'regulatory_athena.py', 'regulatory_collection.py', 'regulatory_sources.py', 's3_runtime_fs.py', 'sec_athena_pilot.py', 'sec_filings.py', 'sec_filings_legacy.py', 'streaming_release.py', 'ted_enrichment.py', 'ted_packages.py', 'uk_mhra_designations.py', 'uspto_patents.py', 'uspto_rate_limit.py', 'config/patent-document-exceptions.json']
    names += [str(p.relative_to(ROOT)) for p in (ROOT/'metadata_engine').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    with tempfile.TemporaryDirectory(prefix='metadata-runtime-') as directory:
        staged=Path(directory)
        # Generated runtime settings have no credential values.
        (staged/'metadata-engine.json').write_text(encoded(config))
        package=staged/'runtime.tgz'
        with tarfile.open(package,'w:gz') as tar:
            for name in names:tar.add(ROOT/name,arcname=name)
            tar.add(staged/'metadata-engine.json',arcname='config/metadata-engine.json')
        body=package.read_bytes()
    sha=hashlib.sha256(body).hexdigest();key='research-data/constellation-backfill/deployments/metadata-engine/runtime-'+sha+'.tgz'
    session.client('s3').put_object(Bucket=bucket,Key=key,Body=body,ServerSideEncryption='AES256',IfNoneMatch='*')
    base='/opt/constellation/metadata-engine-runtime'
    worker_unit='''[Unit]
Description=Validate and label committed raw data on m7i
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/opt/constellation/metadata-engine-runtime
ExecStart=/opt/constellation/legacy-venv/bin/python -B -m metadata_engine.worker --max-jobs 8 --max-seconds 210
Slice=constellation-workers.slice
MemoryHigh=402653184
MemoryMax=536870912
MemorySwapMax=0
CPUQuota=25%
TimeoutStartSec=300
TimeoutStopSec=20
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=ARROW_NUM_THREADS=1
Environment=MALLOC_ARENA_MAX=2
Nice=15
NoNewPrivileges=true
ProtectSystem=full
'''
    worker_timer='''[Unit]
Description=Process the committed metadata backlog every minute
[Timer]
OnBootSec=90
OnUnitInactiveSec=60
Persistent=true
[Install]
WantedBy=timers.target
'''
    # SSM executes a fixed script; no secret values occur in these arguments.
    worker_code="""import boto3,hashlib,io,os,subprocess,tarfile
from pathlib import Path
s3=boto3.client('s3',region_name='us-east-1');r=s3.get_object(Bucket=BUCKET,Key=KEY)
try:body=r['Body'].read()
finally:r['Body'].close()
assert hashlib.sha256(body).hexdigest()==SHA
root=Path(BASE);root.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as tar:tar.extractall(root,filter='data')
for f in [root,*root.rglob('*')]:os.chown(f,1000,1000)
runtime='/opt/constellation/legacy-venv/bin/python'
subprocess.run([runtime,'-c','import pyarrow,pymysql,boto3'],check=True)
subprocess.run([runtime,'-B','-m','unittest','test_metadata_engine','test_metadata_sec_documents','test_metadata_runtime'],cwd=root,check=True)
# Apply the tested opt-in post-commit hook to existing worker source copies.
targets=[Path('/opt/constellation/source/collection_storage.py'),*Path('/opt/constellation/legacy').glob('*/collection_storage.py')]
for target in targets:
 if not target.is_file():continue
 temporary=target.with_suffix('.metadata-new');temporary.write_bytes((root/'collection_storage.py').read_bytes());os.chown(temporary,1000,1000);temporary.replace(target)
Path('/etc/systemd/system/optima-metadata-worker.service').write_text(UNIT)
Path('/etc/systemd/system/optima-metadata-worker.timer').write_text(TIMER)
subprocess.run(['systemctl','daemon-reload'],check=True)
if ACTIVATE:subprocess.run(['systemctl','enable','--now','optima-metadata-worker.timer'],check=True)
print('metadata_worker_ready; activated='+str(ACTIVATE))
""".replace('BUCKET',repr(bucket)).replace('KEY',repr(key)).replace('SHA',repr(sha)).replace('BASE',repr(base)).replace('UNIT',repr(worker_unit)).replace('TIMER',repr(worker_timer)).replace('ACTIVATE',repr(a.activate))
    command='/opt/constellation/.venv/bin/python -c '+shlex.quote(worker_code)
    worker_command=session.client('ssm').send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=180)['Command']['CommandId']
    # The controller uses its local established Python runtime and source tree.
    (ROOT/'config/metadata-engine.json').write_text(json.dumps(config,indent=2)+'\n')
    controller_slice=(ROOT/'systemd/optima-metadata.slice').read_text()
    controller_unit='''[Unit]
Description=Discover committed historical/daily metadata inputs, publish and email stops
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/data-collection-processing
ExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B -m metadata_engine.controller
Slice=optima-metadata.slice
MemoryHigh=201326592
MemoryMax=268435456
MemorySwapMax=0
CPUQuota=15%
TimeoutStartSec=240
Environment=PYTHONDONTWRITEBYTECODE=1
Nice=15
NoNewPrivileges=true
ProtectSystem=full
'''
    controller_timer='''[Unit]
Description=Discover new committed metadata inputs and deliver stop alerts
[Timer]
OnBootSec=60
OnUnitInactiveSec=120
Persistent=true
[Install]
WantedBy=timers.target
'''
    # Local source files are already on t3. SSM only installs the units here.
    controller_code="""from pathlib import Path
import subprocess
# Daily services pick up the hook on their next invocation; no collector
# restart is needed. Paths remain inside the existing controller checkout.
root=Path('/home/ec2-user/data-collection-processing')
for target in (root/'constellation/daily-workspaces').glob('*/collection_storage.py'):
 temporary=target.with_suffix('.metadata-new');temporary.write_bytes((root/'collection_storage.py').read_bytes());temporary.replace(target)
units=subprocess.check_output(['systemctl','list-unit-files','--type=service','--no-legend'],text=True)
for row in units.splitlines():
 name=row.split()[0]
 if (name.startswith('optima-') or name.startswith('constellation-')) and 'metadata' not in name:
  directory=Path('/etc/systemd/system')/(name+'.d');directory.mkdir(exist_ok=True)
  (directory/'90-metadata-notify.conf').write_text('[Service]\\nEnvironment=METADATA_ENGINE_NOTIFY=1\\n')
Path('/etc/systemd/system/optima-metadata.slice').write_text(CONTROL_SLICE)
Path('/etc/systemd/system/optima-metadata-controller.service').write_text(UNIT)
Path('/etc/systemd/system/optima-metadata-controller.timer').write_text(TIMER)
subprocess.run(['systemctl','daemon-reload'],check=True)
if ACTIVATE:subprocess.run(['systemctl','enable','--now','optima-metadata-controller.timer'],check=True)
print('metadata_controller_ready; activated='+str(ACTIVATE))
""".replace('CONTROL_SLICE',repr(controller_slice)).replace('UNIT',repr(controller_unit)).replace('TIMER',repr(controller_timer)).replace('ACTIVATE',repr(a.activate))
    controller_command=session.client('ssm').send_command(InstanceIds=['i-070bab0b09f794629'],DocumentName='AWS-RunShellScript',Parameters={'commands':['/usr/bin/python3 -c '+shlex.quote(controller_code)]},TimeoutSeconds=120)['Command']['CommandId']
    print(json.dumps({'source_policies':len(config['contracts']),'catalog_entries':158,'worker_command':worker_command,'controller_command':controller_command,'activated':a.activate,'runtime_package_sha256':sha},indent=2))


if __name__=='__main__':main()
