import concurrent.futures,hashlib,json,os,pathlib,subprocess
root=pathlib.Path(__file__).parent/'assets'
def curl(url,dst=None):
 args=['curl','-fLsS','--retry','2','--max-time','420']
 if dst:
  dst.parent.mkdir(parents=True,exist_ok=True)
  tmp=dst.with_name(dst.name+'.partial')
  subprocess.run([*args,url,'-o',str(tmp)],check=True)
  tmp.rename(dst)
  return
 return subprocess.check_output([*args,url])
def hf(name,repo,selected):
 api=f'https://huggingface.co/api/models/{repo}'
 rev=json.loads(curl(api))['sha']
 path=root/name; path.mkdir(exist_ok=True)
 (path/'revision.txt').write_text(repo+'@'+rev+'\n')
 rows=[r for r in json.loads(curl(f'{api}/tree/{rev}')) if r['path'] in selected]
 assert len(rows)==len(selected)
 def file(r):
  p=path/r['path']; curl(f'https://huggingface.co/{repo}/resolve/{rev}/{r["path"]}?download=true',p)
  assert p.stat().st_size==r['size']
  if lfs:=r.get('lfs'):
   with p.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==lfs['oid']
  print(name,p.name,p.stat().st_size,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: list(pool.map(file,rows))
def stanza():
 path=root/'stanza'
 curl('https://raw.githubusercontent.com/stanfordnlp/stanza-resources/main/resources_1.10.0.json',path/'resources.json')
 d=json.loads((path/'resources.json').read_text()); jobs={}
 for lang,pack in [('en','combined'),('ro','rrt')]:
  for proc in ('tokenize','mwt','pos','lemma','depparse'):
   if proc not in d[lang]:continue
   p=pack if proc in ('tokenize','mwt') else pack+'_nocharlm'
   m=d[lang][proc][p]; jobs[lang,proc,p]=m['md5']
   for dep in m.get('dependencies',[]):
    t,v=dep['model'],dep['package']; jobs[lang,t,v]=d[lang][t][v]['md5']
 def file(entry):
  (lang,proc,pack),md5=entry
  rel=f'{proc}/{pack}.pt'; dst=path/lang/rel
  curl(d['url'].format(lang=lang,resources_version='1.10.0',filename=rel),dst)
  with dst.open('rb') as f: assert hashlib.file_digest(f,'md5').hexdigest()==md5
  print(lang,rel,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: list(pool.map(file,jobs.items()))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 common={'config.json','sentencepiece.bpe.model','special_tokens_map.json','tokenizer_config.json'}
 jobs=[ex.submit(hf,'m2m','facebook/m2m100_418M',common|{'generation_config.json','pytorch_model.bin','vocab.json'}),
       ex.submit(hf,'e5','intfloat/multilingual-e5-small',common|{'model.safetensors','tokenizer.json'}),
       ex.submit(stanza),
       ex.submit(curl,'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz',root/'lid.176.ftz'),
       ex.submit(curl,'https://download.geonames.org/export/dump/cities15000.zip',root/'geo/cities15000.zip'),
       ex.submit(curl,'https://download.geonames.org/export/dump/countryInfo.txt',root/'geo/countryInfo.txt')]
 for job in jobs: job.result()
