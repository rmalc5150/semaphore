from research_helpers import *
root='https://www.bruker.com/en/products-and-solutions/'
evidence=[];bp=[]
def group(path,items,desc,sector='biotech',sub='research_tools'):
 e=ev(root+path,'Current official catalogue explicitly lists these distinct instruments/platforms: '+', '.join(items)+'. Availability and regulatory scope vary by market; no approvals inferred.')
 evidence.append(e)
 for n in items:bp.append(p(n,desc,e,'commercial',['developer'],typ='product',sector=sector,sub=sub))
group('mass-spectrometry/timstof.html',['timsOmni','timsMetabo','timsUltra AIP','timsTOF HT','timsTOF MALDI PharmaPulse','timsTOF Pro 2','timsTOF fleX MALDI-2','timsTOF fleX','timsOmni Sigma','superlimator'],'Instrument or sample-preparation platform for life-science mass spectrometry.')
group('mass-spectrometry/maldi-tof.html',['neofleX','rapifleX MALDI PharmaPulse','rapifleX','microflex LRF','smartfleX'],'MALDI mass spectrometry instrument for analytical research.')
group('mass-spectrometry/mrms.html',['timsMRMS','solariX','scimaX'],'High-resolution magnetic resonance mass spectrometry instrument.')
group('mass-spectrometry.html',['SCiLS Lab','MetaboScape','Biopharma Compass'],'Software for life-science mass spectrometry data analysis.')
group('biosensors-for-molecular-interactions.html',['Triceratops SPR #64','SPR-32 Pro8','SPR-24 Pro8','heliX cyto','heliX+','proFIRE'],'Instrument for molecular interaction research or biosensor sample preparation.')
group('microbiology-and-diagnostics/microbial-identification.html',['MALDI Biotyper sirius','MALDI Biotyper sirius one','MBT Compass HT'],'Microbial identification instrument or associated analysis software.',sub='diagnostics')
group('microbiology-and-diagnostics/microbial-strain-typing.html',['IR Biotyper'],'Infrared spectroscopy system for microorganism strain typing.',sub='diagnostics')
group('microbiology-and-diagnostics/antimicrobial-susceptibility-testing.html',['MICRONAUT-AM','MICRONAUT-S Anaerobes MIC','UMIC'],'Broth microdilution antimicrobial susceptibility testing product.',sub='diagnostics')
group('semiconductor-solutions/ellipsometry-and-reflectometry-systems.html',['FilmTek 2000M TSV Robotic','FilmTek 6000 PAR-SE Robotic','FilmTek 4000 NIR Robotic','FilmTek 2000 PAR-SE Robotic'],'Optical film metrology system for semiconductor manufacturing.','semiconductors','semiconductor_equipment')
group('semiconductor-solutions/automated-x-ray-metrology-systems.html',['SIRIUS-RF','SIRIUS-FW','7300LSI','Delta-X','QCVelox-HR','QCVelox-E','QC5-R'],'X-ray metrology system for semiconductor films or wafers.','semiconductors','semiconductor_equipment')
group('semiconductor-solutions/automated-afm-and-cipt-systems.html',['InSight 300','InSight AFP','SmartProber TT','SmartProber P1'],'Probe-based semiconductor metrology system.','semiconductors','semiconductor_equipment')
group('semiconductor-solutions/mask-repair-and-wafer-cleaning.html',['fp-III','nm-VI','Rhazer-III','EL-C','Wafer Clean 2200'],'Semiconductor mask repair or wafer-cleaning system.','semiconductors','semiconductor_equipment')
group('fluorescence-microscopy/multiphoton-microscopes.html',['Ultima 2Pplus','Ultima Investigator Plus','Ultima In Vitro','OptoVolt Module','NeuraLeap','NeuraLight 3D Ultra'],'Multiphoton biological imaging instrument or named optical module.')
group('fluorescence-microscopy/light-sheet-microscopes.html',['Papilio5D','MuVi SPIM','InVi SPIM Lattice Pro','LCS SPIM','TruLive3D Imager','ACQUIFER HIVE','LuxBundle'],'Light-sheet biological imaging instrument or associated workflow software.')
group('fluorescence-microscopy/spatial-omics-solutions.html',['CellScape','Vutara VXL','PlexFlo'],'Spatial biology imaging or sequential labeling platform.')
# Current 2026 named releases are separate from older console generations.
N=ev('https://ir.bruker.com/press-releases/press-release-details/2026/Bruker-Unveils-New-NMR-Products-and-Workflow-Solutions-at-ENC-2026/default.aspx','2026 issuer announcement names AVANCE NEO-X, Fourier 80 Duo and Advanced Chemical Profiling 2.0.')
evidence.append(N)
for n,d in [('AVANCE NEO-X','NMR spectrometer electronics platform.'),('Fourier 80 Duo','Benchtop NMR spectrometer.'),('Advanced Chemical Profiling 2.0','NMR chemical quantification workflow software.')]:bp.append(p(n,d,N,'commercial',typ='product',sub='research_tools'))
A=ev('https://www.auriniapharma.com/investors-and-media/sec-filings/all-sec-filings/content/0001628280-20-003036/exhibit991-20191231xaif.htm','Historical voclosporin ophthalmic solution formulation (VOS) for dry eye is materially different from the oral LUPKYNIS formulation. Current lifecycle unresolved.')
companies=[company('Bruker Corporation',bp,evidence,'Reviewed mass spectrometry, biosensors, diagnostic systems, semiconductor metrology, microscopy and a 2026 NMR release. Remaining NMR/EPR, preclinical imaging, acquired subsidiaries, consumables, automation, legacy models and additional software prevent exhaustive coverage.'),company('Aurinia Pharmaceuticals Inc',[p('Voclosporin ophthalmic solution','Historical ocular voclosporin formulation for dry eye.',A,aliases=['VOS'])],[A],'Additional historical formulation identified; current three portfolio assets were already researched in batch 1. Full legacy inventory still being reconciled.')]
(out/'batch-0003.json').write_text(json.dumps({'companies':companies},indent=2))
