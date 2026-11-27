import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from collection_storage import StorageSettings, now
from nist_robotics import canonical,parse_document,product_mentions,evidence_event,ROOT_URL
import nist_robotics_pipeline as pipeline


class Tests(unittest.TestCase):
    def setUp(self):
        self.directory={'products':[{'product_id':'prd_1','canonical_name':'UR5e','sector_id':'robotics','review_status':'verified','archived_at':None}], 'aliases':[], 'companies':[]}
        self.doc=parse_document(b'<html><main><h1>Robot test study</h1><p>We mention UR5e in this study.</p></main></html>','https://www.nist.gov/publications/test')

    def test_safe_urls_and_offsite_exclusion(self):
        self.assertIsNone(canonical('https://example.org/a'))
        self.assertIsNone(canonical('http://www.nist.gov/a'))
        self.assertIsNone(canonical('https://user@www.nist.gov/a'))
        self.assertEqual(canonical('/robotics#x'), 'https://www.nist.gov/robotics')

    def test_extract_original_text_tables_and_relevant_links(self):
        raw=b'<html><main><nav>noise</nav><h1>Robotics</h1><p>Methods.</p><a href="/publications/robot-test">Robot test</a><a href="https://bad.example/robot">Robot</a><table><tr><th>Model</th></tr><tr><td>UR5e</td></tr></table></main></html>'
        d=parse_document(raw,ROOT_URL)
        self.assertNotIn('noise',d['text']);self.assertEqual(len(d['links']),1)
        self.assertEqual(d['tables'][0][1][0],'UR5e')

    def test_unchanged_semantics_ignore_navigation(self):
        a=parse_document(b'<html><main><nav>one</nav><h1>Method</h1><p>UR5e</p></main></html>',ROOT_URL)
        b=parse_document(b'<html><main><nav>two</nav><h1>Method</h1><p>UR5e</p></main></html>',ROOT_URL)
        self.assertEqual(a['semantic_hash'],b['semantic_hash'])

    def test_exact_models_only_no_substring_matches(self):
        matches=product_mentions(self.doc,self.directory)
        self.assertEqual(matches[0]['product_id'],'prd_1')
        self.assertEqual(matches[0]['relation'],'mentioned_not_proven_tested')
        self.assertFalse(product_mentions({**self.doc,'text':'UR5ePlus'},self.directory))

    def test_generic_name_needs_manufacturer_context(self):
        self.directory['products'][0]['canonical_name']='Spot'
        matches=product_mentions({**self.doc,'text':'Spot a difference in the image'},self.directory)
        self.assertEqual(matches[0]['match_status'],'ambiguous_name_review')
        self.assertIsNone(evidence_event(self.doc,'url',matches))

    def test_unverified_archived_and_non_robotics_excluded(self):
        for k,v in [('review_status','pending'),('archived_at','2026-01-01'),('sector_id','biotech')]:
            d=json.loads(json.dumps(self.directory));d['products'][0][k]=v
            self.assertFalse(product_mentions(self.doc,d))

    def test_home_page_no_event_and_evidence_not_test_result(self):
        matches=product_mentions(self.doc,self.directory)
        self.assertIsNone(evidence_event({**self.doc,'kind':'discovery'},ROOT_URL,matches))
        event=evidence_event(self.doc,'url',matches)
        self.assertEqual(event['status'],'candidate');self.assertIsNone(event['occurrence'])
        self.assertNotIn('benchmark_result',event['event_type'])
        self.assertEqual(event['event_id'],evidence_event(self.doc,'url',matches+[{**matches[0],'product_id':'prd_2'}])['event_id'])

    def test_csv_data_archived_and_suppression_strings_retained(self):
        d=parse_document(b'Model,Value\nUR5e,*\n','https://data.nist.gov/robot.csv')
        self.assertEqual(d['row_count'],1);self.assertEqual(d['sample_rows'][0]['Value'],'*')

    def test_dataset_metadata_links_to_actual_distributions(self):
        raw=json.dumps({'title':'Robot data','distribution':[{'downloadURL':'https://data.nist.gov/files/robot.csv'}]}).encode()
        d=parse_document(raw,'https://data.nist.gov/od/id/test')
        self.assertEqual(d['links'][0]['url'],'https://data.nist.gov/files/robot.csv')

    def test_empty_main_anchor_does_not_hide_article(self):
        raw=b'<html><a id="main-content"></a><main><h1>Robot study</h1><p>UR5e test description</p></main></html>'
        self.assertIn('UR5e',parse_document(raw,ROOT_URL)['text'])

    def test_email_waits_for_matching_after_capture(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(pipeline,'ROOT',Path(directory)):
            with pipeline.registry() as db:
                db.execute("INSERT INTO jobs VALUES ('job','backfill','2026-10-18','captured','[]')");db.commit()
                with patch.object(pipeline,'get_bytes',side_effect=AssertionError('No publication check before matching')):
                    self.assertIsNone(pipeline.notify(db,None,None,{'job_id':'job'},'job'))

    def test_daily_seed_recovers_when_shared_scheduler_has_no_receipt(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline,'ROOT',Path(directory)):
            settings=StorageSettings(local_root=directory+'/store')
            day=datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
            manifest={'status':'complete','exhausted':True,'finished_at':now(),'pages':[]}
            with pipeline.registry() as db, patch.object(pipeline,'capture_daily_landing',return_value=manifest) as landing:
                config={'max_depth':1,'max_documents_per_job':2}
                self.assertEqual(pipeline.seed(db,settings.store(),config,'daily',settings),'nist-daily-'+day)
                self.assertEqual(pipeline.seed(db,settings.store(),config,'daily',settings),'nist-daily-'+day)
                landing.assert_called_once()
                self.assertEqual(db.execute('SELECT url FROM docs').fetchone(),(ROOT_URL,))

    def test_queue_is_bounded_and_exclusions_visible(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(pipeline,'ROOT',Path(directory)):
            with pipeline.registry() as db:
                config={'max_depth':1,'max_documents_per_job':2}
                pipeline.enqueue(db,'job',ROOT_URL,0,config)
                pipeline.enqueue(db,'job','https://www.nist.gov/robot1',1,config)
                pipeline.enqueue(db,'job','https://www.nist.gov/robot2',1,config)
                pipeline.enqueue(db,'job','https://www.nist.gov/robot3',2,config)
                self.assertEqual(db.execute('SELECT count(*) FROM docs').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT count(*) FROM excluded').fetchone()[0],2)

if __name__=='__main__':unittest.main()
