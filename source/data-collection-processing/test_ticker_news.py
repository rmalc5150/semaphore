import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import ticker_news


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


class TickerNewsTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.end = datetime(2026, 8, 2, tzinfo=timezone.utc)

    def test_normalize_tickers(self):
        self.assertEqual(ticker_news.normalize_tickers([" aapl,MSFT", "AAPL"]), ["AAPL", "MSFT"])

    def test_parse_multiple_companies(self):
        self.assertEqual(ticker_news.parse_companies([
            "HUTCHMED", "hkex", "13", "Apple Inc.", "nasdaq", "aapl",
        ]), [
            {"company": "HUTCHMED", "exchange": "HKEX", "ticker": "13"},
            {"company": "Apple Inc.", "exchange": "NASDAQ", "ticker": "AAPL"},
        ])

    def test_company_folder(self):
        self.assertEqual(ticker_news.company_folder("Apple Inc."), "Apple-Inc")

    def test_safe_url_redacts_marketaux_token(self):
        request = ticker_news.Request("https://example.test/news?api_token=secret&symbols=AAPL")
        self.assertEqual(ticker_news.safe_url(request), "https://example.test/news")

    def test_parse_combined_api_key_secret(self):
        response = {"SecretString": json.dumps({
            "finlight-api-key": " finlight-secret ",
            "marketaux-api-key": "marketaux-secret",
        })}
        self.assertEqual(
            ticker_news.parse_api_keys(response, "newKeys"),
            ("finlight-secret", "marketaux-secret"),
        )

    def test_parse_combined_api_key_secret_reports_missing_field(self):
        response = {"SecretString": json.dumps({"finlight-api-key": "value"})}
        with self.assertRaisesRegex(ValueError, "marketaux-api-key"):
            ticker_news.parse_api_keys(response, "newKeys")

    @patch("ticker_news.datetime")
    def test_uploads_under_company_news_folder(self, mocked_datetime):
        mocked_datetime.now.return_value = datetime(2026, 8, 21, 12, 30, tzinfo=timezone.utc)
        client = unittest.mock.Mock()
        location = ticker_news.upload_company_news(
            {"company": "HUTCHMED", "exchange": "HKEX", "ticker": "13", "articles": []},
            s3_client=client,
        )
        call = client.put_object.call_args.kwargs
        self.assertEqual(call["Bucket"], ticker_news.S3_BUCKET)
        self.assertEqual(
            call["Key"],
            "HUTCHMED/news/HKEX/20260821T123000000000Z.json",
        )
        self.assertEqual(location, f"s3://{ticker_news.S3_BUCKET}/{call['Key']}")

    @patch("ticker_news.request_json")
    def test_finlight_request_and_provider_tag(self, request_json):
        request_json.return_value = {"articles": [{"title": "Apple news"}]}
        rows = ticker_news.fetch_finlight("secret", ["AAPL"], self.start, self.end, 10)
        request = request_json.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.headers["X-api-key"], "secret")
        self.assertEqual(body["tickers"], ["AAPL"])
        self.assertEqual(rows[0]["provider"], "finlight")

    @patch("ticker_news.request_json")
    def test_marketaux_request_does_not_put_token_in_output(self, request_json):
        request_json.return_value = {"meta": {"returned": 1}, "data": [{"title": "Tesla news"}]}
        rows = ticker_news.fetch_marketaux("secret", ["TSLA"], self.start, self.end, 10)
        request = request_json.call_args.args[0]
        self.assertIn("symbols=TSLA", request.full_url)
        self.assertEqual(rows, [{"provider": "marketaux", "title": "Tesla news"}])
        self.assertNotIn("secret", json.dumps(rows))


if __name__ == "__main__":
    unittest.main()
