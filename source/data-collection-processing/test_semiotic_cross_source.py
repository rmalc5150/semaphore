"""Cross-source appointment reconciliation with a synthetic four-document corpus."""
from dataclasses import dataclass
from datetime import date
from itertools import permutations
import json
import re
import unittest

from semiotic_sandbox import build, encoded, identity, sha


@dataclass(frozen=True)
class Document:
    key: str
    source: str
    published: str
    text: str
    derived_from: str | None = None


DOCUMENTS = (
    Document("release", "company_release", "2024-08-13",
             "Avery Morgan will join as permanent CEO effective 2024-09-09."),
    Document("filing", "sec_filing", "2024-08-14",
             "The board appointed Avery Morgan as permanent CEO, effective 2024-09-09."),
    Document("news", "news", "2024-08-15",
             "According to the company release, Avery Morgan will join as permanent CEO effective 2024-09-09.",
             derived_from="release"),
    Document("interim", "company_release", "2024-08-13",
             "Jordan Ellis will serve as interim CEO beginning 2024-08-13."),
)
REGISTRY = {"snapshot_id": "synthetic-registry", "identifiers": [
    {"namespace": "CIK", "value": "0000012345", "entity_id": "fixture_company",
     "review_status": "verified"}
]}

# Narrow candidate extractor for this test. The adapters would provide explicit
# issuer references and republication lineage from their source contracts.
APPOINTMENT = re.compile(
    r"(?P<name>[A-Z][a-z]+ [A-Z][a-z]+) (?:will join|will serve)?\s*"
    r"as (?P<role>permanent|interim) CEO,? (?:effective|beginning) "
    r"(?P<effective>\d{4}-\d{2}-\d{2})\."
)


def replay(documents):
    observations = []
    for doc in documents:
        text = "CIK 0000012345\n" + doc.text
        observations.append({
            "observation_id": doc.key, "record_id": doc.key,
            "quality_status": "accepted", "raw_completeness_status": "complete",
            "raw_s3_uri": None, "raw_sha256": None, "ingested_at": None,
            "payload": {"pages": [{"page": 1, "text": text}]},
        })
    graph = build({"environment": "sandbox", "observations": observations,
                   "observations_sha256": sha(encoded(observations))}, REGISTRY)
    issuers = {edge["subject_id"]: edge["object_id"] for edge in graph["tables"]["edges"]}
    events = {}
    for doc in documents:
        text = doc.text
        match = APPOINTMENT.search(text)
        if not match:
            raise ValueError(f"no supported appointment in {doc.key}")
        fields = match.groupdict()
        date.fromisoformat(fields["effective"])
        event_id = identity("pilot_event", [issuers[doc.key], "personnel.appointment",
                            fields["role"], fields["name"].casefold(), fields["effective"]])
        event = events.setdefault(event_id, {
            "event_id": event_id, "type": "personnel.appointment", "organization_id": issuers[doc.key],
            "reported_appointee": fields["name"], "role": fields["role"],
            "effective_on": fields["effective"], "evidence": [],
        })
        event["evidence"].append({
            "id": doc.key, "source": doc.source, "published_on": doc.published,
            "provenance_root": doc.derived_from or doc.key, "start": match.start(),
            "end": match.end(), "quote": match[0],
        })
    result = sorted(events.values(), key=lambda event: event["event_id"])
    for event in result:
        event["evidence"].sort(key=lambda e: (e["published_on"], e["id"]))
        event["provenance_groups"] = sorted({e["provenance_root"] for e in event["evidence"]})
    return result


class CrossSourceAppointmentTest(unittest.TestCase):
    def test_replay_all_arrival_orders_and_evidence(self):
        expected = replay(DOCUMENTS)
        for order in permutations(DOCUMENTS):
            self.assertEqual(replay(order), expected)
        by_role = {event["role"]: event for event in expected}
        self.assertEqual(len(expected), 2)
        permanent, interim = by_role["permanent"], by_role["interim"]
        self.assertEqual([e["id"] for e in permanent["evidence"]], ["release", "filing", "news"])
        self.assertEqual(permanent["provenance_groups"], ["filing", "release"])
        self.assertEqual([e["id"] for e in interim["evidence"]], ["interim"])
        # Both original documents have the same issuer. Distinct roots do not
        # imply independent reporting. The news is explicitly a derivative.
        for event in expected:
            for item in event["evidence"]:
                text = next(doc.text for doc in DOCUMENTS if doc.key == item["id"])
                self.assertEqual(text[item["start"]:item["end"]], item["quote"])
        before_news = replay(DOCUMENTS[:2] + DOCUMENTS[3:])
        self.assertEqual([e["event_id"] for e in before_news], [e["event_id"] for e in expected])


if __name__ == "__main__":
    unittest.main(verbosity=2)
