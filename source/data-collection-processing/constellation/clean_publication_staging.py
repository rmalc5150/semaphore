"""Clear one stopped publisher's dedicated, rebuildable EBS staging directory."""
from pathlib import Path
import re
import shutil
import sys

BASE=Path('/opt/constellation/tmp/publication-staging')

def clean(unit):
    if not re.fullmatch(r'optima-m7-[A-Za-z0-9_-]+\.service',unit):raise ValueError('Invalid publisher unit')
    root=BASE/unit
    if root.is_symlink()or root.resolve().parent!=BASE.resolve():raise ValueError('Staging directory escapes its dedicated root')
    if not root.exists():return
    for entry in root.iterdir():
        if entry.is_symlink()or not entry.is_dir():entry.unlink()
        else:shutil.rmtree(entry)

if __name__=='__main__':clean(sys.argv[1])
