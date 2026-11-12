from research_helpers import *
a=ev('https://www.stryker.com/us/en/joint-replacement/systems/Mako_SmartRobotics_Overview.html','Current catalogue identifies Mako4, integrated Q Guidance, FP8000 camera and MICS3 tool system. Named robotic platform and dedicated components distinguished from procedure indications.')
b=ev('https://www.stryker.com/us/en/joint-replacement/systems/mako-spine.html','Mako Spine page identifies Q Guidance, Spine Guidance5 software and Copilot Smart Driver automatic depth stop; used with robotic workflow. Not independent fully autonomous surgery.')
c=ev('https://www.stryker.com/us/en/about/news/2026/stryker-expands-mako-robotics-portfolio.html','Issuer confirms actual US full commercial launch of Mako RPS handheld robotic system July16 2026, superseding earlier limited launch.')
d=ev('https://www.stryker.com/us/en/trauma-and-extremities/products/bio4.html','BIO4 viable bone matrix current offer. Manufactured by Osiris Therapeutics, not assumed manufactured by Stryker. Family listed volumes1/2.5/5/10cc; exact item codes unverified.')
e=ev('https://www.stryker.com/us/en/foot-and-ankle/products/augment.html','Current manufacturer/distributor page distinguishes Augment Bone Graft and Augment Injectable. Recombinant human PDGF-BB combination products. No other company reference brands attributed to Stryker.')
products=[]
for name,desc,source,typ in [
 ('Mako 4','Fourth-generation robotic-arm surgical platform supporting multiple procedure applications. Applications not counted as additional robot hardware.',a,'product'),
 ('Mako RPS','Handheld robotic power system for total knee replacement. US commercial launchJuly2026.',c,'product'),
 ('Q Guidance System','Optical surgical guidance platform integrated with Mako4 and robotic spine workflows.',a,'product'),
 ('FP8000 camera','Dedicated optical tracking camera in Q Guidance robotic navigation ecosystem.',a,'product'),
 ('MICS 3','Robotic cutting handpiece and attachment system integrated with Mako procedures.',a,'product'),
 ('Copilot Smart Driver','Robot-compatible surgical driver with software-controlled automatic planned-depth stop.',b,'product'),
 ('Spine Guidance 5 software','Surgical planning and navigation software with robotic Mako Spine/Copilot features.',b,'technology')]:
 products.append(p('Stryker '+name,desc,source,'commercial',typ=typ,sector='robotics',sub='medical_robotics',roles=['developer']))
products.append(p('BIO4 viable bone matrix','Cell-containing allogeneic bone matrix offered by Stryker and manufactured by Osiris. No independent FDA drug approval inferred.',d,'commercial',typ='product',roles=['commercial_partner'],attributes={'manufacturer':'Osiris Therapeutics','catalogue_volumes_cc':[1,2.5,5,10]}))
for name,desc in [('Augment Bone Graft','Recombinant human PDGF-BB combined with beta-tricalcium phosphate bone graft.'),('Augment Injectable','Injectable recombinant human PDGF-BB combination bone graft; distinct formulation from Augment Bone Graft.')]:
 products.append(p(name,desc,e,'commercial',typ='product',roles=['commercial_partner'],territory='United States'))
co=company('Stryker Corp.',products,[a,b,c,d,e],'Seven named robotic systems/components/software and three biological graft products entered. Mako4 multiple applications not represented as additional independent robot hardware. BIO4 third-party manufacture explicit. Need full biologics/tissue/nerve/cartilage portfolio and volume SKUs, Augment variants, historic Mako/RIO generations, separately marketed procedure software/Blueprint and any battery/semiconductor products. General implants and ordinary powered surgical tools not automatically robotics or biotech. Scope partial.')
(out/'batch-0171.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
