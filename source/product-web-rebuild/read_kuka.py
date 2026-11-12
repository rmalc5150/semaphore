import urllib.request,re,json
from pathlib import Path
u='https://www.kuka.com/en-us/products/robotics-systems/industrial-robots'
s=urllib.request.urlopen(u).read().decode();Path('/home/ec2-user/product-web-rebuild/kuka-robots.html').write_text(s)
for pattern in [r'.{0,100}api.{0,200}',r'.{0,100}[Pp]roduct[Ss]earch.{0,200}',r'.{0,100}KR AGILUS.{0,150}']:
 for x in re.findall(pattern,s)[:12]: print(x)
