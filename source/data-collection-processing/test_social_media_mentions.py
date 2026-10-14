import json
import tempfile
import unittest
from pathlib import Path

from social_media_mentions import Mention, deduplicate, enrich, load_jsonl, sentiment, summary


class SocialMediaMentionTests(unittest.TestCase):
    def test_sentiment_and_negation(self):
        self.assertEqual(sentiment("great promising success")[1], "positive")
        self.assertEqual(sentiment("not good, serious risk")[1], "negative")
        self.assertEqual(sentiment("公司获批，增长强劲")[1], "positive")

    def test_engagement_prioritizes_shares_and_comments(self):
        shared = enrich(Mention("Acme", "x", "1", "a", "good", None, None, 4, 3, 2))
        liked = enrich(Mention("Acme", "x", "2", "b", "good", None, None, 0, 0, 10))
        self.assertGreater(shared.engagement_score, liked.engagement_score)

    def test_import_and_company_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wechat.jsonl"
            path.write_text(json.dumps({"platform": "wechat", "id": "wx1", "author": "Alice", "content": "Acme has a great launch", "shares": 8}) + "\n")
            rows = load_jsonl(path, ["Acme"])
        self.assertEqual((rows[0].company, rows[0].shares), ("Acme", 8))

    def test_dedup_and_summary(self):
        low = enrich(Mention("Acme", "reddit", "1", "alice", "bad", None, None, 0, 0, 1))
        high = enrich(Mention("Acme", "reddit", "1", "alice", "bad", None, None, 5, 0, 1))
        rows = deduplicate([low, high])
        self.assertEqual(len(rows), 1)
        report = summary(rows)[0]
        self.assertEqual((report["mentions"], report["comments"], report["negative"]), (1, 5, 1))


if __name__ == "__main__":
    unittest.main()
