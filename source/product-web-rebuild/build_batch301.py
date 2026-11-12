from research_helpers import *
a=ev('https://amkor.com/packaging/laminate/','Current laminate offering families; dimension and ball-count variants not individually enumerated.')
b=ev('https://amkor.com/packaging/leadframe/','Current leadframe families; slash-grouped variants retained as published.')
c=ev('https://amkor.com/packaging/power-discrete/','Thirteen named power-package families, not customers power semiconductor die.')
d=ev('https://amkor.com/packaging/wafer-level-packaging/','Current wafer-level packaging offerings.')
e=ev('https://amkor.com/packaging/','Current technology navigation identifies enabling interconnect and integration platforms; broad category umbrellas excluded.')
products=[]
def add(names,src,desc):
 for n in names:products.append(p('Amkor '+n,desc,src,'commercial',roles=['developer','manufacturer'],sector='semiconductors',sub='materials_and_packaging',typ='technology'))
add(['CABGA/FBGA','DSMBGA','FCBGA','fcCSP','FlipStack CSP','Interposer PoP','PBGA/TEPBGA','Stacked CSP'],a,'Laminate package family.')
add(['ePad LQFP/TQFP','ePad TSSOP/MSOP/SOIC/SSOP','Flip Chip MicroLeadFrame','LQFP','MicroLeadFrame','SOIC','SSOP/QSOP','TQFP','TSSOP/MSOP'],b,'Leadframe package family.')
add(['D2PAK (TO-263)','DPAK (TO-252)','HSON8','LFPAK56','PowerCSP','PQFN','PSMC','SO8-FL','SOD123-FL','SOD128-FL','TO-220FP','TOLL','TSON8-FL'],c,'Power semiconductor package family.')
add(['WLCSP','WLFO/WLCSP+','WLSiP/WL3D'],d,'Wafer-level packaging family.')
add(['2.5D/3D TSV','3D Stacked Die','AiP/AoP','Chip-on-Chip','Copper Pillar','Edge Protection','Flip Chip interconnect','Optical Sensors packaging','Package-on-Package','S-Connect','S-SWIFT','SWIFT'],e,'Semiconductor integration or interconnect technology.')
co=dict(company_id='cmp_27d082df-f864-4b48-b0e1-b0c0dcbe770c',products=products,evidence=[a,b,c,d,e],status='partial',coverage_note='Forty-five named current packaging/interconnect families. Partial: company advertises more than 3000 formats/sizes; dimension, terminal-count and customer-specific configurations not all enumerated. Memory/MEMS/SiP broad headings and generic services excluded as redundant umbrellas pending individual named offering review. Packages and interconnect technologies not attributed as ownership of customer chip designs. Interposer PoP package distinct from general PoP integration process.')
(out/'batch-0301.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
