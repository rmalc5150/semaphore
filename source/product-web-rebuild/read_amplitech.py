import urllib.request,json
from pathlib import Path
u='https://shop.amplitechinc.com/products.json?limit=250'
d=json.load(urllib.request.urlopen(u));Path('/home/ec2-user/product-web-rebuild/amplitech-products.json').write_text(json.dumps(d,indent=2))
for p in d['products']: print(p['title'],p['product_type'],p['handle'])
print('TOTAL',len(d['products']))
