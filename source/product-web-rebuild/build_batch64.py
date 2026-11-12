from research_helpers import *
H=ev('https://www.hanagroup.com/AboutUs/History','Hana identifies Power Master Semiconductor as its Korean subsidiary. FT1 49 percent minority investment is not treated as ownership of all its products.')
U='https://www.powermastersemi.com/img/sub/PowerMaster%20Product%20Catalog_2026(EN).pdf'
E=ev(U,'Official March2026 image-based catalogue visually reviewed pages9 and11. Exact populated ordering-code cells transcribed; no codes extrapolated into blank cells. Other catalogue pages remain to review.')
ps=[]
def add(code,volts,mohm,package,generation,grade,page,life='commercial'):
 ps.append(p('PowerMaster '+code,'Silicon-carbide power MOSFET ordering model.',E,life,roles=['commercial_partner'],typ='product',sector='semiconductors',sub='chip_design',attributes={'brand':'PowerMaster Semiconductor','model':code,'voltage_v':volts,'typical_on_resistance_milliohm':mohm,'package':package,'generation':generation,'grade':grade,'catalogue_page':page},evidence=[E,H]))
# Page11: fully populated industrial650V matrix.
packages={'PCO':'bare die','PCT':'TOLL','PCLT':'TOLT','PCBF':'D2PAK-7L','PCW':'TO-247-3L','PCZ':'TO-247-4L','PCR':'TSPAK-LF'}
for n in [15,22,27,39,45]:
 for pre,pkg in packages.items():add(f'{pre}65N{n}M1B',650,n,pkg,1,'industrial',11)
# Page11: automotive650V is explicitly labelled development.
for n in [19,29,35,52]:
 for pre,pkg in {'PCO':'bare die','PCBF':'D2PAK-7L','PCRZ':'TSPAK-DBC','PCR':'TSPAK-LF'}.items():add(f'{pre}65N{n}M1BA',650,n,pkg,1,'automotive',11,'development')
# Page11: consumer650V on resistance quoted at Vgs18V; 15V values retained separately.
for n,n15 in [(130,175),(170,230),(245,331),(325,439),(500,675)]:
 for pre,pkg in {'PCO':'bare die','PCD':'DPAK','PCF':'TO-220F','PCS':'PQFN56','PCL':'PQFN88'}.items():
  add(f'{pre}65N{n}M1',650,n,pkg,1,'consumer',11);ps[-1]['attributes'].update({'resistance_gate_voltage_v':18,'on_resistance_milliohm_at_15v':n15})
for token,n in [('25',25),('32',32),('1K0',1000)]:
 for pre,pkg in {'PCO':'bare die','PCBF':'D2PAK-7L','PCW':'TO-247-3L','PCZN':'TO-247-4L Notch'}.items():add(f'{pre}170N{token}M1',1700,n,pkg,1,'industrial',11)
# Page9 industrialGen2:16mohm exists only in bare-die, TO247-3L/4L/Notch cells.
for n in [16,21,31,40,60,80]:
 for pre,pkg in {'PCO':'bare die','PCBF':'D2PAK-7L','PCW':'TO-247-3L','PCZ':'TO-247-4L','PCZN':'TO-247-4L Notch','PCRZ':'TSPAK-DBC','PCR':'TSPAK-LF'}.items():
  if n==16 and pre in ['PCBF','PCRZ','PCR']:continue
  add(f'{pre}120N{n}M2',1200,n,pkg,2,'industrial',9)
# Page9 automotiveGen2: blank TO247 Notch cells at60/80 and unoffered16 packages excluded.
for n in [16,21,31,40,60,80]:
 for pre,pkg in {'PCO':'bare die','PCBF':'D2PAK-7L','PCZN':'TO-247-4L Notch','PCRZ':'TSPAK-DBC','PCR':'TSPAK-LF'}.items():
  if n==16 and pre not in ['PCO','PCZN']:continue
  if n in [60,80] and pre=='PCZN':continue
  add(f'{pre}120N{n}M2A',1200,n,pkg,2,'automotive',9)
assert len({x['canonical_name']for x in ps})==len(ps)
cs=[company('Hana Microelectronics Public Company Limited',ps,[H,E],'Exact PowerMaster ordering models visually checked against populated cells on catalogue pages9 and11; automotive650V explicitly development. Captured1200VGen2 and650V/1700VGen1. Gen3/Gen5/JFET, diode, siliconMOSFET, IGBT and remaining catalogue pages require review. Parent link is group commercial association. Custom OSAT customer chips and package format categories are not invented as proprietary SKUs.')]
(out/'batch-0064.json').write_text(json.dumps({'companies':cs},indent=2));print(len(ps))
