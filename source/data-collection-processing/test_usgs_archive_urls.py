import unittest
from usgs_archive_urls import ARCHIVES, resolve
from usgs_minerals_enrichment import document_identity
from regulatory_collection import SourceIssue
class ArchiveTests(unittest.TestCase):
 def test_all_reviewed_urls_preserve_identity(self):
  for canonical, actual in ARCHIVES.items():
   self.assertEqual(document_identity(canonical),document_identity(actual))
   self.assertEqual(resolve(canonical),actual)
 def test_unknown_hosts_not_promoted(self):
  with self.assertRaises(SourceIssue):document_identity('https://example.com/mcs-2016-lithi.pdf')
 def test_recent_urls_unchanged(self):
  u='https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-lithium.pdf'
  self.assertEqual(resolve(u),u)
