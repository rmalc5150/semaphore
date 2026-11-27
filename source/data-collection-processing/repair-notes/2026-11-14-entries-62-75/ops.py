import boto3,botocore.session,contextlib,io,json,runpy,sys
from pathlib import Path
import constellation.finish_aux_migration as remote_tools
aws=botocore.session.get_session();aws.get_component('credential_provider').remove('login')
session=boto3.Session(botocore_session=aws,region_name='us-east-1');boto3.DEFAULT_SESSION=session
remote_tools.session=session;remote_tools.ssm=session.client('ssm')
T3=remote_tools.T3;M7=remote_tools.M7
B='data-collection-059416028963-us-east-1-an'
BASE='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
P=Path(__file__).parent
SOURCES=('sam_gov_opportunities','uspto_odp','bis_sdmx_api','fred_alfred_series_and_vintages','unido_iip_and_indstat','ilostat_labor_statistics','imf_portwatch_shipping_activity','ember_electricity_demand_and_generation','wto_timeseries_api','wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications','epo_ops_patent_legal_events','copernicus_era5_era5_land')
def remote(instance,code):
 cap=io.StringIO()
 try:
  with contextlib.redirect_stdout(cap):remote_tools.remote(instance,code)
 except Exception as error:raise RuntimeError(cap.getvalue()[-10000:]or str(error))from error
 r=json.loads(cap.getvalue())
 if r['status']!='Success':raise RuntimeError(r)
 return r
if __name__=='__main__':runpy.run_path(sys.argv[1],run_name='__main__')
