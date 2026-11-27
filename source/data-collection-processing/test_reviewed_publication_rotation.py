import contextlib,io,unittest
from unittest.mock import Mock,patch
import reviewed_metadata_publication as r
class Rotation(unittest.TestCase):
 def test_plan_prioritizes_full_older_batches_and_advances_cold_sources(self):
  def probe(_db,source,_target,*,daily):
   size,stamp={'old':(4,1),'new':(4,2),'small':(1,0),'cold':(0,0)}[source]
   candidates=[{'job_id':str(i),'finished_at':stamp} for i in range(max(size,1))]
   return None,candidates,{str(i):{} for i in range(size)}
  with patch.object(r,'publication_candidates',side_effect=probe):
   ready,cold=r.publication_order(Mock(),('new','cold','old','small'),2)
  self.assertEqual(list(ready),['old','new','small'])
  self.assertEqual(list(cold),['cold'])
  self.assertEqual(r.take_source((ready,),{'old'}),'new')
 def test_budget_exhaustion_resumes_with_next_source(self):
  db=Mock();db.cursor.side_effect=[{'offset':0},{'offset':1}]
  with patch.object(r,'Database',return_value=db),patch.object(r,'PUBLICATION_SOURCES',('a','b')),patch.object(r.Path,'read_text',return_value='{}'),patch.object(r,'publish',return_value=1)as publish,patch.object(r.time,'monotonic',side_effect=[0,0,241,0,0,241]),contextlib.redirect_stdout(io.StringIO()):r.main();r.main()
  self.assertEqual([c.kwargs['source_key']for c in publish.call_args_list],['a','b']);self.assertEqual(db.save_cursor.call_args_list[0].args[1],{'offset':1})
if __name__=='__main__':unittest.main()
