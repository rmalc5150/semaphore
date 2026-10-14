import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from people_movements import clusters, extract, historical_news, load_jsonl, merge_movements, parse_feed, workforce_trends


class PeopleMovementTests(unittest.TestCase):
    def test_appointment_with_prior_employer_and_expertise(self):
        item = extract({
            "source": "Company IR", "publishedAt": "2026-08-10T12:00:00Z",
            "title": "Proxygen appoints Chiara Conti as Chief Scientific Officer",
            "text": "Conti joins from Blueprint Medicines and brings targeted protein degradation expertise.",
            "url": "https://example.test/release",
        })
        self.assertEqual(item["person"], "Chiara Conti")
        self.assertEqual(item["newOrganization"], "Proxygen")
        self.assertEqual(item["oldOrganization"], "Blueprint Medicines")
        self.assertEqual(item["role"], "Chief Scientific Officer")
        self.assertIn("targeted protein degradation", item["expertise"])

    def test_direct_move(self):
        item = extract({"title": "Jane Smith leaves Merck to join Startup X as Head of Oncology", "date": "2026-08-01", "source": "test"})
        self.assertEqual((item["oldOrganization"], item["newOrganization"]), ("Merck", "Startup X"))
        self.assertEqual(item["direction"], "move")

    def test_prior_employer_stops_before_biography(self):
        item = extract({"title": "Acme appoints Jane Smith as Chief Medical Officer", "text": "Smith joins from Merck with oncology experience.", "date": "2026-08-01", "source": "test"})
        self.assertEqual(item["oldOrganization"], "Merck")

    def test_irrelevant_record_is_ignored(self):
        self.assertIsNone(extract({"title": "Company reports phase 2 results", "source": "test"}))

    def test_feed_and_merge_corroboration(self):
        xml = b"""<rss><channel><item><title>Acme appoints Jane Smith as Chief Medical Officer</title><link>https://a</link><pubDate>Mon, 10 Aug 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
        first = extract(parse_feed(xml, "A")[0])
        second = dict(first)
        second["evidence"] = [dict(first["evidence"][0], source="B", url="https://b")]
        result = merge_movements([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["evidence"]), 2)

    def test_historical_search_builds_exclusive_month_window(self):
        from unittest.mock import patch
        seen = []
        def fake_request(url):
            seen.append(url)
            return b"<rss><channel></channel></rss>"
        with patch("people_movements.request", fake_request):
            rows, errors = historical_news(date(2024, 2, 1), date(2024, 2, 29))
        self.assertEqual((rows, errors), ([], []))
        self.assertTrue(all("after%3A2024-02-01" in url for url in seen))
        self.assertTrue(all("before%3A2024-03-01" in url for url in seen))

    def test_cluster_detects_concentrated_hiring(self):
        rows = [extract({"person": name, "oldOrganization": old, "newOrganization": "Startup X", "role": role, "eventDate": day, "source": "test"}) for name, old, role, day in (
            ("Jane Smith", "Merck", "VP Oncology", "2026-01-01"),
            ("John Jones", "Seagen", "Principal Scientist", "2026-02-01"),
        )]
        result = clusters(rows)
        self.assertEqual(result[0]["movementCount"], 2)
        self.assertEqual(set(result[0]["sourceOrganizations"]), {"Merck", "Seagen"})

    def test_jsonl(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "licensed.jsonl"
            path.write_text(json.dumps({"person": "Jane Smith", "newOrganization": "Acme"}) + "\n")
            self.assertEqual(load_jsonl(path)[0]["source"], "licensed")

    def test_reported_headcount_takes_precedence(self):
        records = [
            {"organization": "China Bio", "researchHeadcount": 100, "asOfDate": "2025-12-31", "source": "Annual report"},
            {"organization": "China Bio", "researchHeadcount": 125, "asOfDate": "2026-12-31", "source": "Annual report"},
        ]
        trend = workforce_trends([], records)[0]
        self.assertEqual(trend["classification"], "increasing")
        self.assertEqual(trend["reportedHeadcountChange"], 25)
        self.assertEqual(trend["reportedHeadcountChangePct"], 0.25)
        self.assertEqual(trend["basis"], "reported_headcount")

    def test_movement_flow_is_only_likely(self):
        movements = [extract({"person": name, "newOrganization": "China Bio", "role": "Principal Scientist", "eventDate": day, "source": "test"}) for name, day in (("Jane Smith", "2026-01-01"), ("John Jones", "2026-02-01"))]
        trend = workforce_trends(movements, [])[0]
        self.assertEqual(trend["classification"], "likely_increasing")
        self.assertEqual(trend["observedNetFlow"], 2)

    def test_non_research_executive_does_not_change_rd_trend(self):
        movement = extract({"person": "Jane Smith", "newOrganization": "China Bio", "role": "Chief Financial Officer", "eventDate": "2026-01-01", "source": "test"})
        self.assertEqual(workforce_trends([movement], []), [])


if __name__ == "__main__":
    unittest.main()
