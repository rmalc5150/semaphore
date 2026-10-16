import hashlib
import json
import sqlite3
from unittest.mock import Mock, patch
from test_people_social_collection import SourceTests
from test_finlight_content import BODY
from people_rss_content import Capture
from collection_storage import write_checked
from research_contract import seal_record
import finlight_content_backfill as b


class PeopleContentTests(SourceTests):
    def test_rss_full_body_and_archive_keeps_nested_content(self):
        from people_social_collection import collect_feed
        from personnel_archive import collect
        from regulatory_collection import EvidenceClient
        client=EvidenceClient(self.store,'people_rss')
        raw=b'<rss><channel><item><title>Company appoints chief scientist</title><link>https://example.org/news</link><description>Short summary</description><pubDate>Thu, 24 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        with patch('people_social_collection.ROOT',self.root), patch.object(client,'get',side_effect=lambda url:client.save(raw,url)), patch.object(Capture,'publisher',return_value=(BODY,'publisher_html')):
            result=collect_feed(self.store,self.settings,self.u,self.t,'test','https://example.org/feed',self.day,client)
        self.assertEqual(result['status'],'complete',result)
        manifest=json.loads(self.store.get(result['manifest']).body)
        batch=manifest['pages'][0]['batches'][0]
        parent=json.loads(self.store.get(batch['key']).body.splitlines()[0])
        self.assertEqual(parent['payload']['data']['text'],'Short summary')
        self.assertEqual(parent['payload']['data']['content'],BODY)
        archive=collect(self.store,self.settings,result['manifest'])
        self.assertEqual(archive['status'],'complete',archive)
        m=json.loads(self.store.get(archive['manifest']).body)
        output=json.loads(self.store.get(m['pages'][0]['batches'][0]['key']).body.splitlines()[0])
        self.assertEqual(output['payload']['data']['payload']['data']['content'],BODY)
        self.assertEqual(output['payload']['full_text']['status'],'captured')

    def test_backfill_includes_undated_rss_and_emails_after_archive_gate(self):
        from people_social_collection import record
        from collection_storage import CollectionRun,task_spec
        spec=task_spec('people_rss','people_source_records','daily','2026-10-14T00:00:00Z','2026-10-15T00:00:00Z',{},'test',self.u,self.t)
        run=CollectionRun.start(self.store,spec,self.u,self.t,self.settings)
        parent=record(run,'rss-identity','https://example.org/news',{'url':'https://example.org/news','text':'RSS summary'},None,[],'RSS snapshot')
        raw=(json.dumps(parent)+'\n').encode();key='test/rss.jsonl';sha=hashlib.sha256(raw).hexdigest();write_checked(self.store,key,raw)
        index=self.root/'index.sqlite3'
        with sqlite3.connect(index) as db:
            db.execute('CREATE TABLE batches (key TEXT,sha256 TEXT,source TEXT,dataset TEXT)')
            db.execute('INSERT INTO batches VALUES (?,?,?,?)',(key,sha,'people_rss','people_source_records'))
        config=dict(provider='people_rss',dataset='people_source_records',date_basis='snapshot_ingestion',snapshot_start='2021-01-01T00:00:00Z',snapshot_cutoff='2099-01-01T00:00:00Z',start='2021-01-01',end_exclusive='2026-10-16',max_batches_per_invocation=100,max_articles_per_invocation=10,max_attempts=3,scope_note='Saved RSS inventory',email_topic_arn='arn:topic',email_recipient='owner@example.com')
        sns=Mock();sns.get_paginator.return_value.paginate.return_value=[{'Subscriptions':[dict(Protocol='email',Endpoint='owner@example.com',SubscriptionArn='arn:confirmed')]}];sns.publish.return_value={'MessageId':'accepted'}
        with b.registry(self.root/'registry.sqlite3') as db,patch.object(Capture,'publisher',return_value=(BODY,'publisher_html')),patch.object(b,'archive_ready',return_value=False):
            state=b.run(self.store,self.settings,config,self.u,self.t,None,sns,db,index)
            self.assertEqual(state['counts'],{'captured':1});sns.publish.assert_not_called()
            manifest=db.execute('SELECT manifest FROM articles').fetchone()[0];m=json.loads(self.store.get(manifest).body);output=json.loads(self.store.get(m['pages'][0]['batches'][0]['key']).body.splitlines()[0])
            self.assertIsNone(output['event_at']);self.assertEqual(output['source_record_id'],'rss-identity')
            with patch.object(b,'archive_ready',return_value=True):
                b.run(self.store,self.settings,config,self.u,self.t,None,sns,db,index)
                b.run(self.store,self.settings,config,self.u,self.t,None,sns,db,index)
            self.assertEqual(sns.publish.call_count,1)

    def test_completion_waits_for_archive_receipts_and_new_catalog(self):
        import people_content_backfill as p
        from pathlib import Path
        config={'snapshot_cutoff':'2026-10-15T10:00:00Z'}
        with patch.object(p,'ROOT',self.root):
            (self.root/'reports').mkdir()
            catalog=self.root/'reports/committed-athena-latest.json'
            catalog.write_text(json.dumps({'status':'verified','started_at':'2026-10-15T12:00:00Z'}))
            with b.registry(p.registry_path(config)) as db:
                db.execute('INSERT INTO articles(url,parent,lineage,status,manifest) VALUES (?,?,?,?,?)',('https://example.org/a','{}','{}','captured','manifest.json'))
            self.assertFalse(p.archive_ready(self.store,config))
            with sqlite3.connect(p.registry_path(config)) as db:
                db.execute('INSERT INTO archive_receipts VALUES (?,?)',('manifest.json','2026-10-15T13:00:00Z'))
            self.assertFalse(p.archive_ready(self.store,config))
            catalog.write_text(json.dumps({'status':'verified','started_at':'2026-10-15T14:00:00Z'}))
            self.assertTrue(p.archive_ready(self.store,config))
