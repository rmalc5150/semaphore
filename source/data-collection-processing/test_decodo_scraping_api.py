import json
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).parent))
import decodo_scraping_api


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class DecodoScrapingApiTests(unittest.TestCase):
    def test_gateway_failure_does_not_expose_response_body(self):
        opener = Mock(side_effect=HTTPError("https://example.test", 503, "error", {}, io.BytesIO(b"secret-body")))
        with self.assertRaises(decodo_scraping_api.ScrapeError) as error:
            decodo_scraping_api.scrape("https://example.test", "secret", opener=opener)
        self.assertEqual(str(error.exception), "scrape_gateway_http_503")
        self.assertTrue(error.exception.retryable)

    def test_target_failure_is_distinct_from_gateway(self):
        with patch.object(decodo_scraping_api, "scrape", return_value={"results": [{"status_code": 403}]}):
            with self.assertRaises(decodo_scraping_api.ScrapeError) as error:
                decodo_scraping_api.scrape_content("https://example.test", "secret")
        self.assertEqual(error.exception.stage, "target")
        self.assertFalse(error.exception.retryable)

    def test_pending_and_incomplete_results_are_retryable_without_exposing_body(self):
        for response in ({'results': []}, {'results': [{'status_code': 202, 'content': 'pending'}]},
                         {'results': [{'content': 'private-provider-response'}]}):
            with patch.object(decodo_scraping_api, 'scrape', return_value=response):
                with self.assertRaises(decodo_scraping_api.ScrapeError) as error:
                    decodo_scraping_api.scrape_content('https://example.test', 'secret')
            self.assertTrue(error.exception.retryable)
            self.assertNotIn('private', str(error.exception))

    def test_parse_token(self):
        response = {"SecretString": json.dumps({"decodo": " token "})}
        self.assertEqual(decodo_scraping_api.parse_token(response), "token")

    def test_prefer_web_scraping_token(self):
        response = {"SecretString": json.dumps({
            "decodo": "general-key",
            "decodo-web-scraping": " scraping-token ",
        })}
        self.assertEqual(decodo_scraping_api.parse_token(response), "scraping-token")

    def test_parse_username_password(self):
        response = {"SecretString": json.dumps({
            "decodo-username": "api-user",
            "decodo-password": "api-pass",
        })}
        self.assertEqual(
            decodo_scraping_api.parse_token(response),
            "YXBpLXVzZXI6YXBpLXBhc3M=",
        )

    def test_scrape_request(self):
        opener = Mock(return_value=Response({"results": [{"status_code": 200}]}))
        result = decodo_scraping_api.scrape(
            "https://example.test", "secret", geo="United States", opener=opener
        )
        request = opener.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Basic secret")
        self.assertEqual(
            json.loads(request.data),
            {"url": "https://example.test", "geo": "United States"},
        )
        self.assertEqual(result["results"][0]["status_code"], 200)


if __name__ == "__main__":
    unittest.main()
