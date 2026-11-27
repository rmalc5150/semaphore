"""Supply missing public intermediates for specific providers with TLS verification."""
import hashlib
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

import requests

_SECTIGO = ('anm-intermediate.pem', '505ca50c3930cedca888c4e1ebb0747cb485498547b60ea6bcd23cf78766aeeb')
_GLOBALSIGN = ('sernageomin-intermediate.pem', 'c5e33c47ffb2b81739dc8003611c251241f663712ac628787d6d48e4ed6799cd')
_ISSUERS = {
    'dadosabertos.anm.gov.br': _SECTIGO,
    'geocatmin.ingemmet.gob.pe': _SECTIGO,
    'geocatminapp.ingemmet.gob.pe': _SECTIGO,
    'www.sernageomin.cl': _GLOBALSIGN,
    'sernageomin.cl': _GLOBALSIGN,
}


def ca_bundle_for(url):
    issuer = _ISSUERS.get(urlsplit(url).hostname)
    if issuer is None:
        return True
    name, checksum = issuer
    extra = (Path(__file__).resolve().parent / 'config' / name).read_bytes()
    if hashlib.sha256(extra).hexdigest() != checksum:
        raise ValueError('provider_intermediate_checksum_mismatch')
    bundle = Path(requests.certs.where()).read_bytes() + b'\n' + extra
    digest = hashlib.sha256(bundle).hexdigest()
    directory = Path('/dev/shm') / f'constellation-verified-ca-{os.getuid()}'
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / (digest + '.pem')
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
            output.write(bundle)
        os.replace(output.name, target)
    return str(target)
