import unittest,tempfile,json
from collection_storage import LocalStore,StorageSettings,write_json
from specialist_publication import bridge_drugsfda_inventory
class BoundedBridge(unittest.TestCase):
 def test_pages_resume_and_rotate_without_repeated_full_scan(self):
  with tempfile.TemporaryDirectory()as tmp:
   s=LocalStore(tmp);cfg=StorageSettings(local_root=tmp)
   for n in range(5):write_json(s,f'constellation-backfill/specialist-publication-queue/drugsfda-inventory/{n:03}.json',{'window_id':str(n),'manifests':[str(n)]})
   self.assertEqual(bridge_drugsfda_inventory(s,cfg,2),2)
   state=json.loads(s.get('operations/specialists/inventory-bridge-cursor.json').body)
   self.assertEqual(state['folder_index'],1);self.assertTrue(state['after']['drugsfda-inventory'].endswith('001.json'))
   for _ in range(7):self.assertEqual(bridge_drugsfda_inventory(s,cfg,2),0)
   self.assertEqual(bridge_drugsfda_inventory(s,cfg,2),2)
   self.assertIsNone(s.get('operations/specialists/publication-queue/4.json'))
   for _ in range(7):bridge_drugsfda_inventory(s,cfg,2)
   self.assertEqual(bridge_drugsfda_inventory(s,cfg,2),1)
   for n in range(5):self.assertIsNotNone(s.get(f'operations/specialists/publication-queue/{n}.json'))
 def test_bad_entry_is_logged_without_preventing_next_valid_entry(self):
  with tempfile.TemporaryDirectory()as tmp:
   s=LocalStore(tmp);cfg=StorageSettings(local_root=tmp)
   write_json(s,'constellation-backfill/specialist-publication-queue/drugsfda-inventory/001.json',{'missing':'identity'})
   write_json(s,'constellation-backfill/specialist-publication-queue/drugsfda-inventory/002.json',{'window_id':'ok','manifests':['m']})
   self.assertEqual(bridge_drugsfda_inventory(s,cfg,2),1)
   self.assertEqual(len(list((s.root/'operations/specialists/inventory-bridge-failures').glob('*.json'))),1)
