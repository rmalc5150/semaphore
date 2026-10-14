import unittest

from strategic_transactions import extract, merge, money_values


class StrategicTransactionTests(unittest.TestCase):
    def test_license_economics_and_royalty(self):
        item = extract({"source": "IR", "title": "Acme and Beta enter exclusive license agreement", "text": "Acme receives $25 million upfront, up to $300 million in milestone payments and 8% royalties.", "eventDate": "2026-01-02"})
        self.assertEqual(item["categories"], ["licensing_agreement", "milestone_payment", "royalty_agreement"])
        self.assertEqual(item["parties"], ["Acme", "Beta"])
        self.assertEqual(item["royalty"]["ratePct"], 8.0)
        self.assertEqual([value["amount"] for value in item["economics"]], [25_000_000, 300_000_000])

    def test_acquisition(self):
        item = extract({"title": "Pfizer acquires ExampleBio for $2.5 billion", "date": "2025-03-01", "source": "news"})
        self.assertEqual(item["categories"], ["acquisition"])
        self.assertEqual(item["parties"], ["Pfizer", "ExampleBio"])
        self.assertEqual(item["economics"][0]["amount"], 2_500_000_000)

    def test_joint_venture(self):
        item = extract({"title": "Alpha and Gamma form joint venture", "eventDate": "2025-04-01", "source": "IR"})
        self.assertEqual(item["categories"], ["joint_venture"])

    def test_irrelevant(self):
        self.assertIsNone(extract({"title": "Company reports clinical data", "source": "news"}))

    def test_google_news_off_topic_acquisition_is_ignored(self):
        self.assertIsNone(extract({"title": "Industrial manufacturer acquires steel company", "date": "2025-01-01", "source": "Google News acquisition"}))

    def test_transaction_status(self):
        item = extract({"title": "Pfizer reportedly backs off acquisition of ExampleBio", "date": "2025-03-01", "source": "Google News acquisition"})
        self.assertEqual(item["status"], "terminated")

    def test_corroboration_merge(self):
        base = {"title": "Pfizer acquires ExampleBio for $2.5 billion", "date": "2025-03-01"}
        first = extract(dict(base, source="A", url="https://a")); second = extract(dict(base, source="B", url="https://b"))
        result = merge([first, second])
        self.assertEqual(len(result), 1); self.assertEqual(len(result[0]["evidence"]), 2)

    def test_currency_not_converted(self):
        values = money_values("RMB 100 million upfront and US$20 million milestone")
        self.assertEqual([(v["currency"], v["amount"]) for v in values], [("CNY", 100_000_000), ("USD", 20_000_000)])


if __name__ == "__main__": unittest.main()
