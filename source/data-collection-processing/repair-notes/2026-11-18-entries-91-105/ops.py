import boto3,botocore.session,contextlib,io,json,runpy,sys
from pathlib import Path
import constellation.finish_aux_migration as remote_tools
aws=botocore.session.get_session();aws.get_component('credential_provider').remove('login')
session=boto3.Session(botocore_session=aws,region_name='us-east-1');boto3.DEFAULT_SESSION=session
remote_tools.session=session;remote_tools.ssm=session.client('ssm')
T3=remote_tools.T3;M7=remote_tools.M7
B='data-collection-059416028963-us-east-1-an'
BASE='research-data/constellation-backfill/repairs/entries-91-105-20261118/'
P=Path(__file__).parent
SOURCES=('japan_mhlw_ndb_open_data', 'cninfo_mainland_china_company_disclosures', 'china_nbs_industrial_production', 'china_miit_electronics_and_battery_statistics', 'china_nea_power_statistics', 'china_nhsa_reimbursement_and_procurement', 'china_mofcom_export_controls', 'south_korea_fss_opendart', 'south_korea_kosis_statistical_openapi', 'taiwan_twse_mops_issuer_and_revenue_archives', 'taiwan_customs_trade_statistics', 'india_ibm_mineral_production', 'indonesia_esdm_and_geological_agency_mineral_statistics', 'brazil_anm_mineral_yearbook', 'brazil_anm_cfem_mining_royalties')
def remote(instance,code):
 cap=io.StringIO()
 try:
  with contextlib.redirect_stdout(cap):remote_tools.remote(instance,code)
 except Exception as error:raise RuntimeError(cap.getvalue()[-10000:]or str(error))from error
 r=json.loads(cap.getvalue())
 if r['status']!='Success':raise RuntimeError(r)
 return r
if __name__=='__main__':runpy.run_path(sys.argv[1],run_name='__main__')
