from research_helpers import *
a=ev('https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAISUhdeChlorineEngineers/assets.files/products/redox_flow_battery/thyssenkrupp_energy_storage_solutions.pdf','Historical issuer brochure describes modular vanadium redox-flow battery and integrated hydrogen storage offerings. No current2026 commercial availability or distinct order codes verified.')
b=ev('https://www.thyssenkrupp-polysius.com/en/products/automation/polab-amt','Current Polysius catalogue confirms AMT robot laboratory with ABB arm and AQCnet controller. System integration does not imply original manufacture of ABB robot arm.')
c=ev('https://www.thyssenkrupp-polysius.com/en/products/automation/polab-apm','Current catalogue distinguishes APM and APMplus sample-preparation modules integrated into robotic laboratories.')
d=ev('https://serviceportal.thyssenkrupp-polysius.com/fileadmin/content/assets/SER__Vor_Ort_Service_/EN/POLAB_Brochures_summary.pdf','Issuer brochure identifies Shuttle mobile-robot laboratory; legacy document current availability not conclusively established.')
e=ev('https://www.thyssenkrupp.com/de/pressedetailseite/thyssenkrupp-im-1-quartal-2025-2026--trotz-marktbedingter-umsatzruckgange-bereinigtes-ebit-uber-vorjahr--konzernprognose-fur-alle-kernsteuerungsgrossen-bestatigt-95038','February2026 parent confirms retained51percent TKMS majority after October2025 listing. Separate listing not complete divestiture.')
f=ev('https://www.finland.atlas-elektronik.com/atlas-elektronik/mine-warfare-systems/mcm-toolbox','Current TKMS ATLAS catalogue identifies autonomous MCM toolbox and constituent SeaFox/SeaCat platforms; bundled system distinguished from constituent vehicles.')
g=ev('https://www.finland.atlas-elektronik.com/atlas-elektronik/uncrewed-naval-systems/arcims','Current catalogue confirms ARCIMS autonomous/remote USV deployed with customers.')
h=ev('https://www.sonartech.atlas-elektronik.com/atlas-elektronik/uncrewed-naval-systems/seacat-mk1','Current SeaCat MK1 autonomous underwater vehicle catalogue. Exact configurations grouped; not separate invented SKUs.')
i=ev('https://www.na.atlas-elektronik.com/fileadmin/user_upload/01_Images/Solutions/Datenblaetter_zum_Download/140_IMCMS.pdf','Historical issuer brochure identifies SeaOtter MkII AUV and prior MkI. Current manufacturing availability unresolved.')
products=[]
for name,desc,source,life,typ in [
 ('polab AMT','Industrial robot-integrated sample handling laboratory; ABB arm is supplier component.','b','commercial','product'),
 ('polab APM','Sample-preparation module for integrated robotic laboratory workflows.','c','commercial','product'),
 ('polab APMplus','Expanded sample-preparation module; distinct named version from APM.','c','commercial','product'),
 ('polab AQCnet','Control and tracking software operating AMT robotic laboratory.','b','commercial','technology'),
 ('polab Shuttle','Mobile-robot sample transport laboratory system. Current orderability unverified.','d','unknown','product'),
 ('ATLAS ARCIMS','Uncrewed surface vessel capable of autonomous or remote operation.','g','commercial','product'),
 ('ATLAS SeaCat MK1','Modular autonomous underwater vehicle with optional remotely operated mode.','h','commercial','product'),
 ('ATLAS SeaFox','Underwater remotely operated inspection and mine-disposal system; variants grouped pending exact catalogue review.','f','commercial','product'),
 ('ATLAS MCM Toolbox','Integrated autonomous mine-countermeasure system built around ARCIMS and modular underwater systems.','f','commercial','product'),
 ('ATLAS SeaOtter MkII','Historical autonomous underwater vehicle; current production status unverified.','i','unknown','product')]:
 source=locals()[source]
 products.append(p(name,desc,source,life,typ=typ,sector='robotics',sub='industrial_robotics' if name.startswith('polab') else 'service_robotics',roles=['commercial_partner'],evidence=[source,e] if name.startswith('ATLAS') else [source]))
products.append(p('thyssenkrupp vanadium redox-flow battery system','Historical modular utility-scale flow battery offering; no unverified2018 forecast treated as actual current launch.',a,typ='product',sector='energy_storage',sub='batteries',roles=['commercial_partner'],attributes={'identity_scope':'system_family','current_availability':'unverified'}))
products.append(p('thyssenkrupp integrated hydrogen energy storage system','Historical integrated long-duration hydrogen storage offering described alongside flow batteries; no generation-only electrolyser counted as a storage product.',a,typ='product',sector='energy_storage',sub='hydrogen_storage',roles=['commercial_partner'],attributes={'identity_scope':'integrated_storage_system_family','current_availability':'unverified'}))
co=company('Thyssenkrupp AG O.N.',products,[a,b,c,d,e,f,g,h,i],'Twelve robotics/control/component and historical storage families reviewed. Current Polysius systems separate from Automation Engineering sold March2026; TKMS majority retained after listing. Current parent relationships conservatively commercial_partner. Need complete ATLAS variants/sonar-autonomy components/SeaOtterMkI and newer UUVs, historical Automation Engineering products with verified closing dates, robotics bearing/steering components with explicit applications, current flow/hydrogen storage status and battery material scope. No all-Agile-Robots portfolio attribution. Partial.')
(out/'batch-0173.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
