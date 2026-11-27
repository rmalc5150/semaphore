import boto3,botocore.session,contextlib,io,json,runpy,sys
from pathlib import Path
import constellation.finish_aux_migration as remote_tools
aws=botocore.session.get_session();aws.get_component('credential_provider').remove('login')
session=boto3.Session(botocore_session=aws,region_name='us-east-1');boto3.DEFAULT_SESSION=session
remote_tools.session=session;remote_tools.ssm=session.client('ssm')
T3=remote_tools.T3;M7=remote_tools.M7
B='data-collection-059416028963-us-east-1-an'
BASE='research-data/constellation-backfill/repairs/entries-76-90-20261116/'
P=Path(__file__).parent
SOURCES=('nasa_power_weather_and_solar_resource', 'usgs_earthquakes', 'ucdp_organized_violence', 'arxiv', 'england_nhsbsa_prescribing_data', 'decodo_shared_web_retrieval_access_layer', 'sia_wsts_public_semiconductor_sales', 'semi_worldwide_equipment_billings', 'international_federation_of_robotics_world_robotics', 'iea_pvps_solar_deployment_reports', 'germany_g_ba_drug_benefit_assessments', 'france_has_medicine_assessment_opinions', 'nice_technology_appraisals', 'canada_cda_amc_cadth_reimbursement_reviews', 'france_assurance_maladie_open_medic')
def remote(instance,code):
 cap=io.StringIO()
 try:
  with contextlib.redirect_stdout(cap):remote_tools.remote(instance,code)
 except Exception as error:raise RuntimeError(cap.getvalue()[-10000:]or str(error))from error
 r=json.loads(cap.getvalue())
 if r['status']!='Success':raise RuntimeError(r)
 return r
if __name__=='__main__':runpy.run_path(sys.argv[1],run_name='__main__')
