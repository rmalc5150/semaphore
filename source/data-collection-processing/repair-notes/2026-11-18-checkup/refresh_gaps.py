import os,sys
from pathlib import Path
root=Path('/opt/constellation/summary-worker');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
from constellation.gaps import main
main()
