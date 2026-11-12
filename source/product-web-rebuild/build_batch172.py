from research_helpers import *
base='https://www.stryker.com/us/en/trauma-and-extremities/products/'
rows=[
 ('ActiShield','actishield.html','Human chorion-based amniotic barrier membrane.'),
 ('ActiShield CF','actishield.html','Human amnion-only barrier membrane; distinct tissue form from ActiShield.'),
 ('AlloFiber','allofiber.html','Freeze-dried demineralized cortical bone fibers.'),
 ('AlloMatrix','allomatrix.html','Demineralized bone matrix grafting putty family containing calcium sulfate. Individual formulation SKUs unresolved.'),
 ('AlloPure Wedges','allopure-wedges.html','Bicortical and tricortical human allograft bone wedges; dimensions grouped pending item codes.'),
 ('AlloWrap DS','allowrap-ds-amniotic-membrane.html','Ready-to-use dual-layer human amniotic membrane.'),
 ('BioSkin amniotic wound matrix','bioskin.html','Dehydrated human chorion allograft wound covering.'),
 ('DBM Gel','dbm.html','Demineralized bone matrix gel with carrier; volume options grouped.'),
 ('DBM Putty','dbm.html','Demineralized bone matrix putty with carrier; volume options grouped.'),
 ('DBM Putty Plus','dbm.html','Demineralized bone matrix putty with cancellous chips; distinct composition from plain putty.'),
 ('FusionFlex','fusionflex.html','Dehydrated demineralized bone matrix sponge.'),
 ('GraftJacket NOW','graftjacket-now.html','Prehydrated human acellular dermal matrix for soft-tissue reinforcement.'),
 ('Ignite injectable stimulus','ignite.html','Graft system combining scaffold, demineralized bone matrix and patient bone marrow aspirate; not a prefilled donor-cell therapy.'),
 ('Neuroflex','neuroflex.html','Resorbable nerve conduit offered through Stryker; third-party brand ownership not inferred.'),
 ('NeuroMatrix','neuromatrix.html','Peripheral nerve conduit offered through Stryker; distinct named nerve repair product.'),
 ('NeuroMend','neuromend.html','Self-curling peripheral nerve wrap offered through Stryker.'),
 ('ProChondrix CR','prochondrix-cr.html','Cryopreserved fresh osteochondral allograft containing viable cells for cartilage repair.'),
 ('ProLayer','prolayer.html','Human acellular dermal matrix; distinct from porcine ProLayer Xenograft.'),
 ('ProLayer Xenograft','prolayer-xenograft0.html','Sterile acellular porcine dermal matrix.'),
 ('Tensix DBM','tensix.html','Prehydrated all-demineralized-bone-matrix graft putty. Descriptive composition label; exact SKU unverified.'),
 ('Tensix cancellous-chip mix','tensix.html','Demineralized bone matrix mixed with cancellous chips. Descriptive formulation label; exact SKU unverified.'),
 ('ViaFlow','https://www.stryker.com/us/en/foot-and-ankle/products/viaflow.html','Room-temperature flowable placental tissue matrix.'),
 ('ViaFlow C','https://www.stryker.com/us/en/foot-and-ankle/products/viaflow.html','Cryopreserved flowable placental tissue matrix, distinct storage/formulation from ViaFlow.')]
products=[];evidence=[]
for name,path,desc in rows:
 e=ev(path if path.startswith('https:') else base+path,'Direct Stryker product page verifies named biological graft or nerve-repair product. Commercial catalogue offer; jurisdiction-specific availability and detailed item codes unresolved. Third-party tissue processor/manufacturer ownership not inferred.')
 evidence.append(e)
 products.append(p('Stryker catalogue '+name,desc,e,'commercial',typ='product',roles=['commercial_partner'],territory='United States',attributes={'catalogue_name':name,'sku_scope':'named formulation or product family; individual sizes not expanded','regulatory_status':'not_normalized_from_biologics_category'}))
co=company('Stryker Corp.',products,list({e['reference']:e for e in evidence}.values()),'Added23 biological graft and nerve-repair families/formulations from individual catalogue pages. ActiShield/CF, DBM gel/putty/chip mixture, ProLayer human/porcine, Tensix compositions and ViaFlow/C kept distinct. Prior Mako ecosystem,BIO4 and Augment records remain. Need complete sizes/ordering codes, additional legacy spine biologics and current rights after spine transactions, robotic generations/application software/Blueprint and storage/chip products if any. Imbibe/X-Ream ordinary instruments and purely inorganic substitutes not automatically biotech. Third-party processing/manufacturing not claimed. Partial.')
(out/'batch-0172.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
