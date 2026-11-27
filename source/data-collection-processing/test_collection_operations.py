"""Offline runner tests: date progress, dependency gating, resume and identities."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import date
import io
import json
import tempfile
import unittest
from unittest.mock import Mock

from collection_storage import CollectionRun, StorageSettings, task_spec
from research_contract import ROOT, load_json
import collection_operations as ops
import sec_filings as sec


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = StorageSettings(local_root=self.temp.name)
        self.store = self.settings.store()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.config = load_json(ROOT / "config/collection-operations.json")
        self.runner = ops.Operations(self.store, self.settings, self.config, self.universe, self.taxonomy)
        self.calls = []
        self.fail = set()
        self.runner.invoke = self.invoke
        self.start, self.end = date(2024, 6, 3), date(2024, 6, 6)

    def invoke(self, source, start, end, mode, inputs, refresh):
        self.calls.append((source, start, end, refresh, inputs))
        if (source, start) in self.fail:
            return {"status": "partial", "reason": "page_limit"}
        dataset = ("filings" if source in {"sec", "hkex-filings"} else "documents"
            if source == "documents" else source.replace("-", "_")
            if source in ops.disclosure.CATEGORIES else "research_records")
        spec = task_spec(ops.SOURCE_IDS[source], dataset, mode,
            self.runner.boundary(source, start), self.runner.boundary(source, end),
            {"inputs": inputs}, "fixture-1", self.universe, self.taxonomy)
        run = CollectionRun.start(self.store, spec, self.universe, self.taxonomy,
                                  self.settings, resume=not refresh, refresh=refresh)
        if not run.exhausted:
            run.commit_page([], exhausted=True)
        return {"status": "complete", "manifest": run.finish("complete", expected_records=0)}

    def run_ops(self, sources, mode="daily", start=None, end=None, max_windows=10, **kwargs):
        with redirect_stdout(io.StringIO()):
            return self.runner.run(sources, mode, start or self.start, end or self.end, max_windows, **kwargs)

    def test_historical_failure_moves_on_after_three_attempts_but_never_claims_complete(self):
        self.config['historical_gap_continue_after_attempts']=3
        self.runner.invoke=lambda *a,**kw:{'status':'failed','reason':'fixture_failure'}
        for n in (1,2):
            report=self.run_ops(['sec'],mode='historical',max_windows=1)
            self.assertEqual(report['sources']['sec']['next_date'],str(self.start))
        report=self.run_ops(['sec'],mode='historical',max_windows=1)
        self.assertEqual(report['sources']['sec']['next_date'],str(self.end))
        self.assertEqual(report['status'],'partial')
        self.assertEqual(len(report['sources']['sec']['accepted_gaps']),1)
        self.assertEqual(self.run_ops(['sec'],mode='historical')['status'],'partial')

    def test_healthy_bounded_partial_is_not_skipped_by_gap_policy(self):
        self.config['historical_gap_continue_after_attempts']=3
        self.fail.add(('sec',self.start))
        for _ in range(4):
            report=self.run_ops(['sec'],mode='historical',max_windows=1)
            self.assertEqual(report['sources']['sec']['next_date'],str(self.start))
            self.assertFalse(report['sources']['sec']['accepted_gaps'])

    def test_daily_window_gap_is_saved_before_advancing_and_can_be_replayed(self):
        self.config['daily_gap_continuation']=True
        def gap(source,start,end,mode,inputs,refresh):
            if start==self.start:
                return {'status':'failed','reason':'source_count_mismatch'}
            return self.invoke(source,start,end,mode,inputs,refresh)
        self.runner.invoke=gap
        report=self.run_ops(['sec'],max_windows=3)
        self.assertEqual(report['sources']['sec']['next_date'],str(self.end))
        self.assertEqual(self.runner.pending_dates('sec'),{str(self.start)})
        self.assertEqual(report['status'],'partial')
        self.runner.invoke=self.invoke
        self.assertEqual(self.run_ops(['sec'],max_windows=1)['status'],'complete')
        self.assertFalse(self.runner.pending_dates('sec'))

    def test_stuck_reconciliation_cannot_starve_later_pending_dates(self):
        self.config['daily_gap_continuation']=True
        self.run_ops(['sec'])
        self.runner.set_pending('sec',self.start,True)
        second=date(2024,6,4)
        self.runner.set_pending('sec',second,True)
        def gap(source,start,end,mode,inputs,refresh):
            if start==self.start:
                return {'status':'failed','reason':'source_count_mismatch'}
            return self.invoke(source,start,end,mode,inputs,refresh)
        self.runner.invoke=gap
        self.run_ops(['sec'],max_windows=1)
        report=self.run_ops(['sec'],max_windows=1)
        self.assertEqual(report['sources']['sec']['windows'][0]['start'],str(second))
        self.assertEqual(self.runner.pending_dates('sec'),{str(self.start)})

    def test_downtime_catchup_and_rerun_skip_completed_dates(self):
        report = self.run_ops(["sec"], max_windows=1)
        self.assertEqual(report["sources"]["sec"]["next_date"], "2024-06-04")
        self.assertEqual(report["status"], "partial")
        report = self.run_ops(["sec"])
        self.assertEqual(report["status"], "complete")
        self.assertEqual([c[1] for c in self.calls], [date(2024,6,3),date(2024,6,4),date(2024,6,5)])
        self.run_ops(["sec"])
        self.assertEqual(len(self.calls), 3)

    def test_partial_does_not_advance_and_independent_source_continues(self):
        self.fail.add(("sec", self.start))
        report = self.run_ops(["sec", "fda"])
        self.assertEqual(report["sources"]["sec"]["next_date"], str(self.start))
        self.assertEqual(report["sources"]["fda"]["status"], "complete")
        self.fail.clear()
        self.run_ops(["sec"])
        self.assertEqual(self.calls[-3][1], self.start)

    def test_changed_hkex_prefix_refreshes_after_cooldown_only(self):
        from collection_storage import write_json
        from datetime import datetime, timezone
        key = self.runner.outcome_key('hkex-filings', self.start, self.end, 'daily')
        failed = {'status': 'partial', 'reason': 'hkex_prefix_changed',
                  'finished_at': datetime.now(timezone.utc).isoformat()}
        write_json(self.store, key, failed)
        self.assertEqual(self.runner.window('hkex-filings', self.start, self.end, 'daily'), failed)
        self.assertFalse(self.calls)
        write_json(self.store, key, {**failed, 'finished_at': '2020-01-01T00:00:00Z'}, self.store.get(key).token)
        self.runner.window('hkex-filings', self.start, self.end, 'daily')
        self.assertTrue(self.calls[-1][3])

    def test_dependencies_expand_and_block_until_both_sources_complete(self):
        self.assertEqual(ops.selected_sources(["press-releases"]),
                         ["sec", "hkex-filings", "documents", "press-releases"])
        self.fail.add(("sec", self.start))
        sources = ops.selected_sources(["press-releases"])
        report = self.run_ops(sources, end=date(2024,6,4))
        self.assertEqual(report["sources"]["documents"]["windows"][0]["status"], "blocked")
        self.assertNotIn("documents", [c[0] for c in self.calls])
        self.fail.clear()
        report = self.run_ops(sources, end=date(2024,6,4))
        self.assertEqual(report["status"], "complete")

    def test_historical_preserves_partial_month_bounds(self):
        self.run_ops(["sec"], mode="historical", start=date(2024,6,27), end=date(2024,7,3))
        self.assertEqual([(c[1],c[2]) for c in self.calls],
                         [(date(2024,6,27),date(2024,7,1)),(date(2024,7,1),date(2024,7,3))])

    def test_uncommitted_success_never_advances_progress(self):
        self.runner.invoke = Mock(return_value={"status":"complete","manifest":"missing.json"})
        report = self.run_ops(["sec"])
        self.assertEqual(report["sources"]["sec"]["next_date"], str(self.start))
        self.assertEqual(report["sources"]["sec"]["windows"][0]["status"], "failed")

    def test_new_universe_has_independent_progress(self):
        self.run_ops(["sec"])
        other = deepcopy(self.universe)
        other["universe_version"] = "9.0.0"
        runner = ops.Operations(self.store, self.settings, self.config, other, self.taxonomy)
        self.assertNotEqual(runner.prefix, self.runner.prefix)

    def test_recent_refresh_and_partial_refresh_resume(self):
        self.run_ops(["sec"], end=date(2024,6,4))
        self.fail.add(("sec", self.start))
        report = self.run_ops(["sec"], end=date(2024,6,4), reconcile_days=1)
        self.assertEqual(report["status"], "partial")
        self.assertTrue(self.calls[-1][3])
        # Mimic the shared collector resuming the partially refreshed task.
        self.runner.invoke = Mock(return_value={"status":"partial","reason":"page_limit"})
        self.run_ops(["sec"], end=date(2024,6,4), reconcile_days=1)
        self.assertFalse(self.runner.invoke.call_args.args[-1])

    def test_stale_parent_is_not_used_for_new_derived_work(self):
        sources = ops.selected_sources(["documents"])
        self.run_ops(sources, end=date(2024,6,4))
        self.fail.add(("sec", self.start))
        self.runner.window("sec", self.start, date(2024,6,4), "daily", refresh=True)
        self.assertEqual(self.runner.window("documents", self.start, date(2024,6,4), "daily")["status"], "blocked")

    def test_failed_refresh_stays_pending_beyond_lookback(self):
        self.run_ops(["sec"], end=date(2024,6,4))
        self.fail.add(("sec", self.start))
        self.run_ops(["sec"], end=date(2024,6,4), reconcile_days=1)
        self.assertEqual(self.runner.pending_dates("sec"), {"2024-06-03"})
        # Even a later invocation with no lookback retries the pending date.
        self.run_ops(["sec"], end=date(2024,6,8), max_windows=10)
        self.assertEqual(self.calls[-1][1], self.start)
        self.assertFalse(self.calls[-1][3])

    def test_parent_revision_queues_existing_derived_date(self):
        self.run_ops(ops.selected_sources(["documents"]), end=date(2024,6,4))
        self.runner.window("sec", self.start, date(2024,6,4), "daily", refresh=True)
        self.assertIn(str(self.start), self.runner.pending_dates("documents"))
        self.run_ops(["documents"], end=date(2024,6,4))
        self.assertEqual(self.runner.pending_dates("documents"), set())

    def test_completed_recovery_clears_pending_with_one_window_budget(self):
        sources = ops.selected_sources(["documents"])
        self.fail.add(("documents", self.start))
        self.run_ops(sources, end=date(2024,6,4), max_windows=1)
        self.runner.set_pending("documents", self.start, True)
        self.fail.clear()
        result = self.run_ops(sources, end=date(2024,6,4), max_windows=1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.runner.pending_dates("documents"), set())

    def test_verified_cached_window_clears_stale_pending_without_replay(self):
        self.run_ops(ops.selected_sources(["documents"]), end=date(2024,6,4))
        self.runner.set_pending("documents", self.start, True)
        before = len(self.calls)
        result = self.runner.window("documents", self.start, date(2024,6,4), "daily")
        self.assertTrue(result["already_complete"])
        self.assertEqual(len(self.calls), before)
        self.assertEqual(self.runner.pending_dates("documents"), set())


class UniverseRolloutTests(unittest.TestCase):
    def test_both_cik_spellings_keep_identity_verification_gate(self):
        u = load_json(ROOT / "examples/sec-filings/universe.json")
        for i, identifier in enumerate(u["external_identifiers"]):
            if identifier["system"] == "sec_cik" and i % 2 == 0:
                identifier["system"] = "cik"
        matcher = sec.CompanyMatcher(u)
        self.assertTrue(matcher.match({"cik":"0000001001","company_name":""})[0])
        u["companies"][0]["review_status"] = "pending"
        matcher = sec.CompanyMatcher(u)
        confirmed, candidates = matcher.match({"cik":"0000001001","company_name":""})
        self.assertFalse(confirmed)
        self.assertTrue(candidates)

    def test_reviewed_universe_recognizes_cik_without_promoting_pending_company(self):
        u = load_json(ROOT / "config/company-universe.v0.2.json")
        matcher = sec.CompanyMatcher(u)
        self.assertEqual(len(matcher.ciks), 11)
        self.assertEqual(sum(len(matcher.match({"cik":cik,"company_name":""})[0])
                             for cik in matcher.ciks), 10)
        self.assertEqual(sec.arguments(["daily","2024-06-03"]).universe.name, "company-universe.v0.2.json")


if __name__ == "__main__":
    unittest.main()
