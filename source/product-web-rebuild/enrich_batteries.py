from research_helpers import *
import sys,boto3
sys.path.insert(0,'/home/ec2-user/data-collection-processing')
from company_catalogue_pipeline import connection
m=json.loads((out/'batch-0010.json').read_text());cid=m['companies'][0]['company_id'];items=[]
for x in m['companies'][0]['products']:
 n=x['canonical_name'];family=x.get('attributes',{}).get('product_family');a={}
 if family:
  # Explicit voltage/capacity columns were reviewed on each family table.
  if family=='OPzV':
   v=12 if n.startswith('12V ') else 2
   ah=int(n.split()[-1]) if v==12 else int(n.split('OPzV')[1].rstrip('A'))
  elif family=='SDC':v=6 if n.startswith('SDC6-') else 12;ah=int(n.split('-')[1])
  elif family=='GFMG':v=6 if n.startswith('3GFMG') else 2;ah=int(n.split('-')[1])
  elif family=='GFM-C':v=12 if n.startswith('6GFM') else 2;ah=int(n.split('-')[1].rstrip('CL'))
  elif family in ['SAJ','FMJ','FT','DCS']:v=12;ah=int(n.split('-')[1])
  elif family in ['GFMD-C','GFM-H','GFMJ','FCP']:v=2;ah=int(n.split('-')[1].rstrip('CH'))
  else:continue
  a={'nominal_voltage_v':v,'nominal_capacity_ah':ah,'capacity_rating':'C10; endpoint 1.75 V/cell for SDC, 1.80 V/cell for other lead-acid series'}
 if n=='SHSIFP76100A':a={'nominal_voltage_v':76.8,'nominal_capacity_ah':100,'nominal_energy_kwh':7.68,'usable_energy_kwh':6.91,'chemistry':'LiFePO4'}
 if n=='Gripline G6-10-US':a={'nominal_energy_kwh':9.6,'rated_ac_output_w':6000,'intended_market':'US'}
 if n=='Gripline G5-10':a={'nominal_energy_kwh':9.6,'rated_ac_output_w':5000,'intended_market':'EU and Australia'}
 if n=='ESS-20H-1229kWh':a={'nominal_voltage_v':768,'rated_capacity_ah':1600,'rated_energy_kwh':1229,'standard_charge_discharge_power_kw':630}
 if n=='ESS-40H-2765kWh':a={'nominal_voltage_v':768,'rated_capacity_ah':3600,'rated_energy_kwh':2765,'standard_charge_discharge_power_kw':1250}
 if a:items.append((n,a))
(out/'battery-enrichment.json').write_text(json.dumps({'company_id':cid,'products':items},indent=2))
c=connection(boto3.Session(region_name='us-east-1'),False)
try:
 with c.cursor() as q:
  q.execute("SELECT GET_LOCK('optima_product_catalogue_v1',0) acquired");assert q.fetchone()['acquired']==1
  q.execute('SET @app_actor=%s,@app_change_reason=%s',('direct-web-product-rebuild/2026-10-20','Add voltage, capacity and energy from reviewed official model tables; correct CHS canonical designation to exact source wording'))
  for n,a in items:
   q.execute('UPDATE products p JOIN product_companies pc USING(product_id) SET p.attributes=JSON_MERGE_PATCH(p.attributes,CAST(%s AS JSON)) WHERE pc.company_id=%s AND p.canonical_name=%s',(json.dumps(a),cid,n))
   assert q.rowcount==1,(n,q.rowcount)
  q.execute("UPDATE products SET canonical_name='CHS coating system' WHERE canonical_name='Corline Heparin Surface'")
 c.commit();print(json.dumps({'enriched_battery_models':len(items)}))
except Exception:
 if c.open:c.rollback()
 raise
finally:c.close()
