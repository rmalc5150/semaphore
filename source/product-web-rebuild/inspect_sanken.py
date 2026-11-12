from html.parser import HTMLParser
from pathlib import Path
import json
class Table(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None;self.texts=[]
 def handle_starttag(self,t,a):
  if t=='tr':self.row=[]
  if t in ['td','th']:self.cell=[]
 def handle_data(self,d):
  if self.cell is not None:self.cell.append(d)
 def handle_endtag(self,t):
  if t in ['td','th'] and self.cell is not None:
   if self.row is not None:self.row.append(' '.join(' '.join(self.cell).split()))
   self.cell=None
  if t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
for f in Path(__file__).resolve().parent.glob('sanken-*-table.html'):
 obj=Table();obj.feed(f.read_text().split('|split_content|')[0]);print(f.name,json.dumps(obj.rows))
