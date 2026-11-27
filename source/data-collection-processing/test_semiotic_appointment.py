"""One reviewed appointment replay using public SEC excerpts as local fixtures."""
import json
import unittest
from datetime import date

from semiotic_registry import discover, empty, review
from semiotic_sandbox import build, encoded, identity, sha

SOURCES = (
    ("0001193125-24-200724", "2024-08-14", "000119312524200724/d848513d8k.htm",
     "Item 5.02",
     "approved the appointment of Brian Niccol as chief executive officer of the Company and chairman of the Board, effective September 9, 2024"),
    ("0001213900-25-006516", "2025-01-24", "000121390025006516/ea0224926-02.htm",
     "Executive Compensation",
     "appointment of Brian Niccol as ceo and chairman of the board of Starbucks, effective September 9, 2024"),
)
BASE = "https://www.sec.gov/Archives/edgar/data/829224/"


def snapshot(sources):
    observations = []
    for accession, filed, path, _, excerpt in sources:
        # Adapt the index CIK and reviewed excerpt into the sandbox input shape.
        # The hash identifies this fixture text, not the complete SEC document.
        text = "CIK 0000829224\n" + excerpt
        observations.append({
            "observation_id": identity("fixture_obs", [accession, text]),
            "record_id": accession,
            "quality_status": "accepted",
            "raw_completeness_status": "complete",  # Complete for the fixture only.
            "raw_s3_uri": None, "raw_sha256": None, "ingested_at": None,
            "available_at": {"value": filed, "precision": "day"},
            "payload": {"pages": [{"page": 1, "text": text}]},
        })
    return {"environment": "sandbox", "observations": observations,
            "observations_sha256": sha(encoded(observations))}


def replay():
    first = snapshot(SOURCES[:1])
    initial = empty()
    review_args = {"actor": "sandbox-review", "reason": "Issuer CIK checked against EDGAR filing index",
                   "at": "2026-11-18T12:00:00Z"}
    provisional = discover(initial, build(first, initial), **review_args)
    org_id = provisional["entities"][0]["entity_id"]
    registry = review(provisional, org_id, action="promote",
                      evidence_ids=[provisional["assertions"][0]["assertion_id"]],
                      canonical_name="Starbucks Corporation", **review_args)
    full = snapshot(SOURCES)
    graph = build(full, registry)
    linked = {edge["subject_id"]: edge["object_id"] for edge in graph["tables"]["edges"]}

    # These event fields were manually reviewed for this two-document pilot.
    # The reported name plus role/date is a scoped correlation key, not a person ID.
    events = {}
    for source, observation in zip(SOURCES, full["observations"], strict=True):
        accession, filed, path, section, quote = source
        obs_id = observation["observation_id"]
        organization = linked[obs_id]
        event_type, role = "personnel.appointment", "chief_executive_officer"
        appointee, effective = "Brian Niccol", "2024-09-09"
        event_id = identity("pilot_event", [organization, event_type, role, appointee, effective])
        event = events.setdefault(event_id, {
            "event_id": event_id, "type": event_type, "organization_id": organization,
            "role": role, "reported_appointee": appointee, "person_id": None,
            "announced_on": "2024-08-13", "stated_effective_on": effective,
            "evidence": [],
        })
        fixture_text = observation["payload"]["pages"][0]["text"]
        start = fixture_text.index(quote)
        event["evidence"].append({
            "observation_id": obs_id, "accession": accession, "url": BASE + path,
            "section": section, "quote": quote, "fixture_text_sha256": sha(fixture_text.encode()),
            "fixture_start": start, "fixture_end": start + len(quote),
            "filed_on": filed, "issuer_cik": "0000829224",
        })

    projections = []
    for cutoff in ("2024-08-13", "2024-08-15", "2025-01-25"):
        versions = []
        for event in events.values():
            # Conservative daily reconstruction: use a filing from the next
            # calendar day. This is a simulation, not operational replay.
            evidence = [e for e in event["evidence"] if e["filed_on"] < cutoff]
            if evidence:
                version = dict(event, evidence=evidence)
                version["version_id"] = identity("pilot_event_version", version)
                versions.append(version)
        projections.append({
            "cutoff": cutoff, "new_ceo_appointments": sum(
                date.fromisoformat(v["evidence"][0]["filed_on"]).toordinal() + 1 ==
                date.fromisoformat(cutoff).toordinal() for v in versions),
            "events": versions,
        })
    return {"mode": "sandbox_public_filing_reconstruction", "historically_eligible": False,
            "registry_snapshot_id": registry["snapshot_id"], "graph_release_id": graph["release_id"],
            "projections": projections}


class AppointmentReplayTest(unittest.TestCase):
    def test_appointment_count_and_evidence_visibility(self):
        before, first, later = replay()["projections"]
        self.assertEqual(before["events"], [])
        self.assertEqual(len(first["events"]), 1)
        self.assertEqual(len(later["events"]), 1)
        early, late = first["events"][0], later["events"][0]
        self.assertEqual(early["event_id"], late["event_id"])
        self.assertNotEqual(early["version_id"], late["version_id"])
        self.assertEqual([len(early["evidence"]), len(late["evidence"])], [1, 2])
        self.assertEqual([p["new_ceo_appointments"] for p in [before, first, later]], [0, 1, 0])
        self.assertLess(first["cutoff"], early["stated_effective_on"])
        self.assertEqual(early["evidence"][0]["accession"], "0001193125-24-200724")
        self.assertIsNone(early["person_id"])
        for row, evidence in zip(snapshot(SOURCES)["observations"], late["evidence"], strict=True):
            text = row["payload"]["pages"][0]["text"]
            self.assertEqual(text[evidence["fixture_start"]:evidence["fixture_end"]], evidence["quote"])


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
