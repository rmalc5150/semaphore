import json,tempfile,unittest
from collection_storage import StorageSettings,write_json
from research_contract import digest
from specialist_discovery_queue import discover

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.settings=StorageSettings(local_root=tmp.name);self.store=self.settings.store();self.state={'jobs':{}}
        self.prefix='operations/specialists/discovered-jobs/'
        for n in range(5):write_json(self.store,self.prefix+str(n)+'.json',{'source':'source'+str(n),'mode':'daily','ordinal':n})
    def scan(self,limit=2,capacity=128):
        return discover(self.store,self.settings,self.state,[self.prefix],'daily','default','universe','v1',limit,capacity)
    def test_scan_is_bounded_and_retains_unselected_jobs_across_passes(self):
        self.assertEqual(len(self.scan()),2)
        self.state=json.loads(json.dumps(self.state))
        self.assertEqual(len(self.scan()),4)
        self.assertEqual([j['ordinal']for j in self.scan()],[0,1,2,3,4])
    def test_capacity_does_not_advance_past_unread_jobs(self):
        first=self.scan(capacity=2);after=self.state['discovery_cursors'][self.prefix]
        self.scan(capacity=2);self.assertEqual(self.state['discovery_cursors'][self.prefix],after)
        identity=digest({'job':first[0],'universe_hash':'universe','version':'v1'});self.state['jobs'][identity]={'status':'complete'}
        next_jobs=self.scan(capacity=2)
        self.assertEqual({j['ordinal']for j in next_jobs},{1,2})
    def test_other_modes_are_not_admitted_but_scanning_continues(self):
        key=self.prefix+'0.json';write_json(self.store,key,{'source':'history','mode':'historical'},self.store.get(key).token)
        result=self.scan();self.assertEqual([j['ordinal']for j in result],[1])
        self.assertEqual(len(self.scan()),3)

if __name__=='__main__':unittest.main()
