from pathlib import Path
p=Path('/opt/constellation/auxiliary-publication/source/additional_source_apis.py');s=p.read_text();a=s.index('    if kind==\'additional_biorxiv\':');b=s.index('    if kind==\'additional_datacite\':',a);print(s[a:b])
