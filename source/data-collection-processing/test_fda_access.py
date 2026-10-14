import io
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit
from regulatory_collection import EvidenceClient, SourceIssue


class FDAAccessTests(unittest.TestCase):
    def test_fda_auth_not_in_evidence_url(self):
        response = io.BytesIO(b'{"results":[]}')
        response.headers = {}
        opener = Mock(return_value=response)
        client = EvidenceClient(None, 'test', opener=opener, sleeper=lambda _: None)
        client.save = Mock(return_value=b'{}')
        with patch('fda_access.api_key', return_value='synthetic-key'):
            client.get('https://api.fda.gov/drug/drugsfda.json', {'limit': 1})
        request = opener.call_args.args[0]
        self.assertTrue(request.get_header('Authorization').startswith('Basic '))
        self.assertNotIn('api_key', request.full_url)
        self.assertNotIn('synthetic-key', str(client.save.call_args))

    def test_no_secret_lookup_for_other_hosts(self):
        response = io.BytesIO(b'{}'); response.headers = {}
        client = EvidenceClient(None, 'test', opener=Mock(return_value=response), sleeper=lambda _: None)
        client.save = Mock()
        with patch('fda_access.api_key') as key:
            client.get('https://example.org/')
        key.assert_not_called()

    def test_http_fails_before_credential_lookup(self):
        with patch('fda_access.api_key') as key:
            with self.assertRaises(SourceIssue):
                EvidenceClient(None, 'test').get('http://api.fda.gov/drug/drugsfda.json')
        key.assert_not_called()
