"""Bounded independent daily/historical continuation of the native DOI collector."""
import argparse,fcntl,json,os,signal
from datetime import date,datetime,timezone
from contextlib import contextmanager
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from conference_collection import advance
from historical_policy import historical_start
PREFIX='constellation-backfill/conferences-resumed'
@contextmanager
def deadline(seconds):
 def expired(*_):raise TimeoutError('crossref_per_mode_deadline')
 old=signal.signal(signal.SIGALRM,expired);signal.alarm(seconds)
 try:yield
 finally:signal.alarm(0);signal.signal(signal.SIGALRM,old)
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--mode',choices=('daily','historical','both'),default='both')
 requested=parser.parse_args().mode
 with open('/opt/constellation/tmp/crossref-resumed.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  os.environ['CONSTELLATION_CONFERENCE_OPERATION_PREFIX']=PREFIX;settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/crossref-resumed-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');today=datetime.now(timezone.utc).date();origin=date(2026,9,23)
  for mode,start,end in [('daily',origin,today),('historical',historical_start(),origin)]:
   if requested not in ('both',mode):continue
   try:
    with deadline(110):result=advance(store,settings,universe,taxonomy,mode,start,end,max_pages=24,resume_recent_cursor=True)
   except Exception as error:result={'status':'failed','reason':type(error).__name__+': '+str(error)[:200]}
   entry={'source':'crossref_proceedings','mode':mode,'at':now(),**result};write_json(store,PREFIX+'/receipts/'+today.isoformat()+'/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True)
if __name__=='__main__':main()
