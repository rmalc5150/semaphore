import unittest
from unittest.mock import Mock
from disclosure_collection import DisclosureClient
from regulatory_collection import EvidenceClient
class HkexOriginalLimit(unittest.TestCase):
 def test_official_original_limit_covers_reported_90mb_circular(self):
  c=DisclosureClient(Mock(),'hkex_news')
  self.assertEqual(c.response_limit('https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0930/2026093000289.pdf'),128*1024**2)
 def test_apis_other_hosts_and_signed_or_untrusted_paths_keep_existing_limit(self):
  c=DisclosureClient(Mock(),'hkex_news')
  for url in ('https://www1.hkexnews.hk/search/titleSearchServlet.do','https://example.org/huge.pdf','https://www1.hkexnews.hk/other/huge.pdf','https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0930/2026093000289.pdf?unexpected=true'):
   self.assertEqual(c.response_limit(url),64*1024**2)
  self.assertEqual(EvidenceClient(Mock(),'other').response_limit('https://example.org/huge.pdf'),64*1024**2)
