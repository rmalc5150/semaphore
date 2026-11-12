from research_helpers import *
a=ev('https://www.destaco.com/gripping','Current manufacturer catalogue series filter; excludes generic accessory classes.')
b=ev('https://group.stabilus.com/stabilus4automation','Confirms Destaco within Stabilus group.')
names=["2P","3P","84A2-1","84A2-V","84L2-1","84L3-2","84N1","84af2","84A3","84N2","84N5","CP","DBG","DCT / CT","DGC/GC","DPDL","DPDS","DPE","DPG","DPL","DPP","DPS","DPW","eRDH","FUA","G110/G120","GR1","GR84","PPC","RA-CAM","RA-Toggle","RDH","REP-2","REP-3","RP","RP_5-10","RP-P","RPB","RPC","RPL/RPLC","RPM/RPMC","RPR","RPS","RPW","RTH","RUA","uRDH","uRTH"]
products=[p('DESTACO '+n+' Series','Gripper family.',a,'commercial',roles=['commercial_partner'],sector='robotics',sub='autonomy_and_components',typ='product') for n in names]
co=dict(company_id='cmp_27b854fc-575d-43cd-9f94-330f52b90f61',products=products,evidence=[a,b],status='partial',coverage_note='Forty-eight gripper families. Partial: individual configurations and other robotic tooling remain. Parent partner role; operating brand manufacture. No umbrella gripper duplicate.')
(out/'batch-0304.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
