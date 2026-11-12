import urllib.request,re,json
from pathlib import Path
root=Path(__file__).resolve().parent
base='https://www.semicon.sanken-ele.co.jp'
paths=['MOSFET','IGBT','Transistor','RectifierDiode','FRD','HighVoltageDiode','SBD','SnubberDiode','TVSDiode','A_DiodeForAlternator','RoundLED','FlatLED','ChipLED','InfraredLED','A_LED','MCU']
for slug in paths:
 url=base+'/ctrl/en/product/category/'+slug+'/'
 html=urllib.request.urlopen(url,timeout=30).read().decode()
 cid=re.search(r'id="contentId" value="(\d+)"',html).group(1)
 req=urllib.request.Request(base+'/search/category3/searchProduct.jsp',data=('flgSubmit=&id='+cid).encode())
 data=urllib.request.urlopen(req,timeout=30).read().decode()
 (root/('sanken-'+slug+'-table.html')).write_text(data)
 print(slug,cid,len(data),flush=True)
