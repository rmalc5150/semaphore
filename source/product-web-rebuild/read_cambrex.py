import urllib.request
from pathlib import Path
from pypdf import PdfReader
p=Path('/home/ec2-user/product-web-rebuild')
u='https://www.cambrex.com/wp-content/uploads/2025/01/cambrex-product-list-generic-apis-intermediates.pdf'
(p/'cambrex-products.pdf').write_bytes(urllib.request.urlopen(u).read())
s='\n'.join(x.extract_text() for x in PdfReader(p/'cambrex-products.pdf').pages);(p/'cambrex-products.txt').write_text(s);print(s)
