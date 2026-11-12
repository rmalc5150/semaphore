from research_helpers import *
base='https://www.acmr.com/'
a=ev(base,'Manufacturer confirms development, manufacture and sale of semiconductor wafer fabrication equipment across wet processing, plating, deposition, track and polishing.')
rows=[
('ACM SAPS II','Single-wafer megasonic cleaning system with up to eight cleaning chambers.','tools-and-processes/wet-processing/ultra-c-saps-cleaning/'),
('ACM SAPS V','Single-wafer megasonic cleaning system with up to twelve cleaning chambers.','tools-and-processes/wet-processing/ultra-c-saps-cleaning/'),
('ACM SAPS VI','Separately manufacturer-listed SAPS single-wafer cleaning model; detailed configuration not established.','tools-and-processes/wet-processing/ultra-c-saps-cleaning/'),
('Ultra C TEBO','Single-wafer megasonic cleaning system designed for delicate patterned and high-aspect-ratio structures.','tools-and-processes/wet-processing/tebo-technology-systems/'),
('Ultra C Tahoe','Hybrid batch and single-wafer sulfuric peroxide cleaning system for semiconductor fabrication.','tools-and-processes/wet-processing/tahoe-cleaning-system/'),
('ACM Single Hot SPM','High-temperature sulfuric peroxide wafer cleaning and photoresist stripping system.','tools-and-processes/wet-processing/single-hot-spm/'),
('ACM Bevel Etch','Targeted wafer-edge wet etching and cleaning system.','tools-and-processes/wet-processing/bevel-etch-cleaning/'),
('Ultra C b','Contactless backside wafer cleaning and etching system using a Bernoulli chuck.','tools-and-processes/wet-processing/ultra-c-b-backside-cleaning/'),
('Ultra C s','Single-wafer frontside, backside and bevel scrubber cleaning system.','tools-and-processes/wet-processing/ultra-c-s-scrubber-cleaning/'),
('Ultra C wb','Cassette-less wet bench batch cleaning system for semiconductor wafers.','tools-and-processes/wet-processing/ultra-c-wb/'),
('Ultra ECP map','Copper electrochemical plating system for front-end dual-damascene structures.','electrochemical-plating/ecp-map/'),
('Ultra ECP 3d','Copper electrochemical plating system for through-silicon vias and 2.5D interposers.','electrochemical-plating/ultra-ecp-3d/'),
('Ultra Fn','Low-pressure vertical batch wafer furnace for deposition and thermal processing.','tools-and-processes/thermal-deposition-processing/ultra-fn-furnace/'),
('Ultra FnA','Batch atomic layer deposition furnace for silicon nitride and silicon carbonitride films.','tools-and-processes/thermal-deposition-processing/ultra-fna-furnace-tool/'),
('Ultra Fn atmospheric pressure oxidation/anneal','Atmospheric pressure thermal processing furnace using silicon carbide chamber components; distinct application configuration from low-pressure Fn.','tools-and-processes/thermal-deposition-processing/ultra-fn-atmospheric-pressure-oxidation-anneal-furnace-tool/'),
('Ultra Pmax','Plasma-enhanced chemical vapour deposition tool family; chamber options grouped without invented model numbers.','tools-and-processes/pecvd/ultra-pmax/'),
('Ultra Lith Track','300 mm coater/developer track platform supporting semiconductor photolithography.','tools-and-processes/track/ultra-lith-track/'),
('Ultra Lith KrF','Separately catalogued KrF coater/developer track configuration with 12 coating and 12 developing chambers.','tools-and-processes/track/track-systems-ultra-lith-krf/')]
products=[];evidence=[a]
for name,desc,path in rows:
 e=ev(base+path,'Direct manufacturer catalogue identifies this equipment model or configuration. Customer chips and wafer materials are not ACM-owned products.');evidence.append(e)
 products.append(p(name,desc,e,'commercial',typ='product',sector='semiconductors',sub='semiconductor_equipment',roles=['developer','manufacturer'],evidence=[a,e]))
co=company('ACM Research Inc',products,evidence,'Reviewed primary IC catalogue and individual model pages. SAPS family represented by three actual model identities; generic family not duplicated. Separate thermal and track configurations retained. Need SiCN PECVD mapping to Pmax before adding an overlapping family, advanced packaging/panel/reclaim/compound-semiconductor products, other wet processing tools, historical models and latest shipment status. Manufacturer dimension typo not copied.',status='partial')
(out/'batch-0190.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
