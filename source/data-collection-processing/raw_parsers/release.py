"""Build a deterministic, installable source bundle of the shared parsers."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from raw_parsers import MODULES, __version__


def source_paths():
    """Repository-relative files needed by either runtime."""
    return tuple(f'raw_parsers/{name}.py' for name in ('__init__', *MODULES))


def build(root):
    files = {name: (Path(root) / name).read_bytes() for name in source_paths()}
    sums = {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}
    stamp = {'package': 'raw_parsers', 'version': __version__, 'files': sums}
    files['raw_parsers/manifest.json'] = (
        json.dumps(stamp, indent=2, sort_keys=True) + '\n').encode()
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as package:
        for name, body in sorted(files.items()):
            entry = ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, body, compress_type=ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Output directory')
    args = parser.parse_args()
    body = build(Path(__file__).resolve().parents[1])
    checksum = hashlib.sha256(body).hexdigest()
    args.directory.mkdir(parents=True, exist_ok=True)
    package = args.directory / f'raw-parsers-{__version__}.zip'
    if package.exists() and package.read_bytes() != body:
        parser.error('bundle already exists with different contents; use a new release version')
    package.write_bytes(body)
    package.with_suffix('.sha256').write_text(f'{checksum}  {package.name}\n')
    print(json.dumps({'version': __version__, 'bundle': str(package), 'sha256': checksum}))


if __name__ == '__main__':
    main()
