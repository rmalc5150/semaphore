import urllib.request,re
from pathlib import Path
s=urllib.request.urlopen('https://www.coopersurgical.com/products/').read().decode();Path('/home/ec2-user/product-web-rebuild/cooper-products.html').write_text(s)
for x in re.findall(r'<script[^>]*src=[\"\']([^\"\']+)',s):print(x)
for x in re.findall(r'.{0,80}(?:wp-json|ajax|api/|graphql).{0,150}',s):print(x)
