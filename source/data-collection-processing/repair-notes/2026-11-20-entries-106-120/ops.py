import boto3,botocore.session,contextlib,io,json,runpy,sys
from pathlib import Path
import constellation.finish_aux_migration as remote_tools
aws=botocore.session.get_session();aws.get_component('credential_provider').remove('login')
session=boto3.Session(botocore_session=aws,region_name='us-east-1');boto3.DEFAULT_SESSION=session
remote_tools.session=session;remote_tools.ssm=session.client('ssm')
T3=remote_tools.T3;M7=remote_tools.M7
B='data-collection-059416028963-us-east-1-an'
BASE='research-data/constellation-backfill/repairs/entries-106-120-20261120/'
P=Path(__file__).parent
SOURCES=('brazil_mdic_comex_stat_api', 'chile_cochilco_production_and_mining_economics', 'chile_sernageomin_mining_yearbooks', 'chile_sma_snifa_environmental_compliance', 'peru_minem_mining_bulletins_and_yearbooks', 'argentina_siacam_mining_indicators', 'brazil_anm_sigmine_and_cadastro_mineiro', 'peru_ingemmet_geocatmin', 'importyeti_shipment_and_supplier_relationships', 'importgenius_international_shipments', 'marinetraffic_historical_vessel_tracks_and_port_calls', 'kpler_commodity_cargo_flows', 'us_census_international_trade_api', 'eurostat_comext_goods_trade', 'climate_trace_industrial_assets_and_activity')
def remote(instance,code):
 cap=io.StringIO()
 try:
  with contextlib.redirect_stdout(cap):remote_tools.remote(instance,code)
 except Exception as error:raise RuntimeError(cap.getvalue()[-10000:]or str(error))from error
 r=json.loads(cap.getvalue())
 if r['status']!='Success':raise RuntimeError(r)
 return r
if __name__=='__main__':runpy.run_path(sys.argv[1],run_name='__main__')
