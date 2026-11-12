import urllib.request,urllib.parse,re,json
from pathlib import Path
root=Path(__file__).resolve().parent
pages={'3d-vgr':'vision/vision-sys/3d_vgr','2d-vgr':'vision/vision-sys/2d_vgr','bz-x1000':'microscope/fluorescence-microscope/bz-x1000','vk-x4000':'microscope/laser-microscope/vk-x4000'}
def read(u):
 return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20).read().decode()
for key,path in pages.items():
 try:
  page='https://www.keyence.com/products/'+path+'/models/';html=read(page)
  vals={field:re.search('var '+var+r'\s*=\s*"([^"]+)"',html).group(1) for field,var in [('groupID','kpi_currentGroupId'),('typeID','kpi_currentTypeId'),('seriesID','kpi_currentSeriesId')]}
  params={'siteID':1,'languageID':'en-US',**vals};url='https://www.keyence.com/data/api/seriesModels?'+urllib.parse.urlencode(params)
  data=json.loads(read(url));(root/('keyence-'+key+'-public-models.json')).write_text(json.dumps({'page':page,'catalogue_data_url':url,'data':data},indent=2))
  print(key,data.get('totalCount'),[(m['webProductName'],m['productTypeName']) for m in data.get('models',[])])
 except Exception as e:print(key,type(e).__name__,str(e)[:200])
