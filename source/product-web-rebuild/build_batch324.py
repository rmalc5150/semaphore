from research_helpers import *
a=ev('https://compumedicsneuroscan.com/products/','Reviewed first of two catalogue pages; issuer request-quote offerings, including hardware and CURRY modules.')
b=ev('https://compumedicsneuroscan.com/products/page/2/','Reviewed final catalogue page. Cap families grouped; channel counts and connectors are configurations, not invented identities.')
c=ev('https://www.compumedics.com.au/en/product-category/brain-research/','Neuroscan is issuer neuroscience-research business.')
products=[]
for code,label in [('X','Data acquisition'),('S','Signal processing'),('SBA','Source analysis'),('D','Digitizer'),('I','Image processing')]:
 products.append(p('CURRY 9 '+code,label+' software module.',a,life='commercial',typ='product',sub='research_tools'))
for family in ['SynAmps RT','Neuvo']:
 for channels in [64,128,256]:
  products.append(p(f'{family} {channels}-channel Amplifier','Neuroscience EEG amplifier.',a,life='commercial',typ='product',sub='research_tools'))
for name,desc in [('Grael 4K PSG:EEG Amplifier','Combined recording amplifier.'),('Grael 4K EEG Amplifier','EEG amplifier.'),('Grael LT EEG Amplifier','EEG recording amplifier.'),('Siesta Wireless EEG Amplifier','Wireless EEG amplifier.'),('MicroMagLink RT','EEG/MRI and EEG/MEG interface.'),('STIM2','Neuroscience stimulus-presentation system.'),('Quik-Cap Neo Net','Gel electrode-cap family.'),('Quik-Cap Hydro Net','Saline electrode-cap family.')]:
 products.append(p(name,desc,a,life='commercial',typ='product',sub='research_tools'))
for name,desc in [('Quik-Cap Silicone Array','EEG silicone electrode-array family.'),('Quik-Cap','EEG electrode-cap family; connector and channel configurations grouped.'),('fMRI Compatible Quik-Cap','MRI-compatible electrode-cap family.')]:
 products.append(p(name,desc,b,life='commercial',typ='product',sub='research_tools'))
co=dict(company_id='cmp_14805ccb-6bed-41f5-84e9-090f6a3f0b0c',products=products,evidence=[a,b,c],status='partial',coverage_note='Both Neuroscan catalogue pages reviewed. Added 22 module, amplifier and electrode-family identities alongside previously recorded CURRY umbrella and Orion. Cap channel counts, connector compatibility and sizes grouped within families. Third-party NDI/Polhemus digitizers and sleep-only Grael PSG not included pending role/scope review. Partial: third-party offered research accessories, broader Compumedics qualifying catalogue and legacy offerings remain; not a claim of exhaustive SKU coverage.')
(out/'batch-0324.json').write_text(json.dumps({'companies':[co]},indent=2));print(len(products))
