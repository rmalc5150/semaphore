"""Verify and atomically select a shared parser ZIP for a worker's Python environments."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def activate(archive, expected_sha256, releases):
    archive = Path(archive).read_bytes()
    digest = hashlib.sha256(archive).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Parser release SHA-256 mismatch')
    manifest_name = 'raw_parsers/manifest.json'
    with ZipFile(BytesIO(archive)) as bundle:
        names = bundle.namelist()
        if len(set(names)) != len(names) or manifest_name not in names:
            raise ValueError('Missing manifest or duplicate archive entries')
        manifest = json.loads(bundle.read(manifest_name))
        version = manifest['version']
        if manifest['package'] != 'raw_parsers' or not re.fullmatch(r'\d+\.\d+\.\d+', version):
            raise ValueError('Invalid parser package or version')
        entries = manifest['files']
        if (set(names) != set(entries) | {manifest_name} or 'raw_parsers/__init__.py' not in entries
                or any(not re.fullmatch(r'raw_parsers/[a-zA-Z_]\w*\.py', n) for n in entries)):
            raise ValueError('Unexpected file in parser release')
        contents = {name: bundle.read(name) for name in names}
    for name, sha in entries.items():
        if hashlib.sha256(contents[name]).hexdigest() != sha:
            raise ValueError('Parser source SHA-256 mismatch for ' + name)
        compile(contents[name], name, 'exec')

    releases = Path(releases).resolve()
    releases.mkdir(parents=True, exist_ok=True)
    release = releases / f'{version}--{digest}'
    current = releases / 'current'
    if current.exists() and (not current.is_symlink() or current.resolve().parent != releases):
        raise ValueError('Refusing to replace an unmanaged parser path')
    if release.is_symlink():
        raise ValueError('Release directory must not be a symbolic link')
    if release.exists():
        same = all((release / name).is_file() and (release / name).read_bytes() == body
                   for name, body in contents.items())
        extra = {p.name for p in (release / 'raw_parsers').iterdir()} - {'__pycache__'}
        if not same or extra != {Path(name).name for name in contents}:
            raise ValueError('An installed release differs from its verified ZIP')
    with TemporaryDirectory(dir=releases, prefix='.parser-stage-') as directory:
        stage = Path(directory)
        if not release.exists():
            candidate = stage / 'release'
            (candidate / 'raw_parsers').mkdir(parents=True)
            for name, body in contents.items():
                (candidate / name).write_bytes(body)
            candidate.replace(release)
        desired = stage / 'current'
        desired.symlink_to(release.name, target_is_directory=True)
        desired.replace(current)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--releases', type=Path, required=True)
    args = parser.parse_args()
    print(activate(args.archive, args.sha256, args.releases))


if __name__ == '__main__':
    main()
