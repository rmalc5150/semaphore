"""Resolve public Open Medic download links afresh; do not archive expiry tokens."""
import re
from html import unescape
from urllib.parse import urlsplit,urljoin,parse_qs,urlencode,urlunsplit
import requests

def stable_public_url(url):
 u=urlsplit(url)
 if u.hostname!='open-data-assurance-maladie.ameli.fr':return url
 q=parse_qs(u.query);q.pop('token',None);return urlunsplit(u._replace(query=urlencode(q,doseq=True)))

def fresh_download(url):
 u=urlsplit(url)
 if u.scheme!='https'or u.hostname!='open-data-assurance-maladie.ameli.fr':raise ValueError('openmedic_untrusted_host')
 q=parse_qs(u.query);path=q.get('file',[''])[0];match=re.fullmatch(r'Open_MEDIC_Base_Complete/OPEN_MEDIC_(20\d\d)\.zip',path)
 if not match:raise ValueError('openmedic_unreviewed_file')
 landing='https://'+u.netloc+'/medicaments/download.php?'+urlencode({'Dir_Rep':'Open_MEDIC_Base_Complete','Annee':match[1]})
 from constellation.shared_limits import admit
 admit(landing)
 r=requests.get(landing,timeout=(10,30),allow_redirects=False);r.raise_for_status()
 link=re.search(r'href=["\x27]([^"\x27]*download_file.php[^"\x27]*)',r.text)
 if not link:raise ValueError('openmedic_download_link_missing')
 target=urljoin(landing,unescape(link[1]));t=urlsplit(target)
 if t.scheme!='https'or t.netloc!=u.netloc or parse_qs(t.query).get('file')!=[path]:raise ValueError('openmedic_file_identity_mismatch')
 return target
