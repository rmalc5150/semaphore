"""Complete ANM's incomplete server chain without disabling TLS verification."""
import hashlib,os,tempfile
from pathlib import Path
from urllib.parse import urlsplit
import requests

# Public issuing intermediate independently verified to the existing trusted roots.
ANM_ISSUER_SHA256='505ca50c3930cedca888c4e1ebb0747cb485498547b60ea6bcd23cf78766aeeb'

def ca_bundle_for(url):
 if urlsplit(url).hostname!='dadosabertos.anm.gov.br':return True
 extra=(Path(__file__).resolve().parent/'config/anm-intermediate.pem').read_bytes()
 if hashlib.sha256(extra).hexdigest()!=ANM_ISSUER_SHA256:raise ValueError('anm_intermediate_checksum_mismatch')
 raw=Path(requests.certs.where()).read_bytes()+b'\n'+extra;sha=hashlib.sha256(raw).hexdigest();directory=Path('/dev/shm')/('constellation-verified-ca-'+str(os.getuid()));directory.mkdir(mode=0o700,exist_ok=True);target=directory/(sha+'.pem')
 if not target.exists():
  with tempfile.NamedTemporaryFile(dir=directory,delete=False)as f:f.write(raw);tmp=f.name
  os.replace(tmp,target)
 return str(target)
