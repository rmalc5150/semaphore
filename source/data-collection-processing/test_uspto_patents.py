import argparse
import io
import unittest
from unittest.mock import patch

import uspto_patents


class USPTOTests(unittest.TestCase):
    def test_secret_formats(self):
        for secret in (' example ', '"example"', '{"API_KEY":"example"}', '{"USPTO":"example"}', '{"x-api-key":"example"}'):
            self.assertEqual(uspto_patents.parse_api_key(secret), "example")
        for secret in ('', '{}', '{"API_KEY":null}', '[]'):
            with self.assertRaises(ValueError):
                uspto_patents.parse_api_key(secret)

    @patch("uspto_patents.boto3.client")
    def test_default_secret_and_region(self, client):
        client.return_value.get_secret_value.return_value = {"SecretString": '{"API_KEY":"example"}'}
        self.assertEqual(uspto_patents.load_api_key(), "example")
        client.assert_called_once_with("secretsmanager", region_name="us-east-1")
        client.return_value.get_secret_value.assert_called_once_with(SecretId=uspto_patents.DEFAULT_SECRET_ID)

    @patch("uspto_patents.urlopen")
    def test_authenticated_request(self, urlopen):
        urlopen.return_value = io.BytesIO(b'{"patentFileWrapperDataBag":[]}')
        self.assertEqual(uspto_patents.fetch_application("16/123,456", "example"), {"patentFileWrapperDataBag": []})
        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.uspto.gov/api/v1/patent/applications/16123456")
        self.assertEqual(dict(request.header_items())["X-api-key"], "example")

    def test_invalid_number_never_requested(self):
        with patch("uspto_patents.urlopen") as request:
            with self.assertRaises(argparse.ArgumentTypeError):
                uspto_patents.fetch_application("../../search", "example")
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
