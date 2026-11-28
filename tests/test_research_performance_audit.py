import csv
import json

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
import io

from research_lab.performance_audit import FIELDS, audit, main


def make_study(path, *, changes=None):
    records = [
        dict(date="2024-01-03", net_return=-.01, gross_return=0, benchmark_return=-.01,
             held_weight=0, position=1, cost=.01, turnover=1),
        dict(date="2024-01-04", net_return=.089, gross_return=.1, benchmark_return=.1,
             held_weight=1, position=0, cost=.01, turnover=1),
        dict(date="2024-01-05", net_return=0, gross_return=0, benchmark_return=-.1,
             held_weight=0, position=0, cost=0, turnover=0),
    ]
    if changes:
        changes(records)
    span = {"start": "2024-01-03", "end": "2024-01-05", "n": 3}
    spec = dict(currency="USD", cost_bps_per_side=100, phases={"holdout": span})
    summary = dict(schema_version=1, study_id="fixture", assets={
        "AAA": dict(spec, status="evaluated", selected={"candidate_id": "fixed"}),
        "BBB": dict(spec, status="no_eligible_validation_candidate", selected=None),
        "CCC": dict(spec, status="insufficient_data", selected=None),
    })
    (path / "summary.json").write_text(json.dumps(summary))
    with (path / "selected_daily.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted(FIELDS))
        writer.writeheader()
        for record in records:
            writer.writerow(dict(record, asset="AAA", split="holdout", currency="USD", candidate_id="fixed"))


class PerformanceAuditTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)

    def test_compounds_paired_returns_and_uses_prior_exposure(self):
        make_study(self.path)
        selected, absent, insufficient = audit(self.path)["phases"]
        self.assertAlmostEqual(selected["strategy_return_pct"], 100 * (.99 * 1.089 - 1))
        self.assertAlmostEqual(selected["costed_buy_hold_return_pct"], 100 * (.99 * 1.1 * .9 - 1))
        self.assertAlmostEqual(selected["strategy_minus_buy_hold_pp"], 100 * (.99 * 1.089 - .99 * 1.1 * .9))
        self.assertAlmostEqual(selected["strategy_max_drawdown_pct"], 1)
        self.assertAlmostEqual(selected["buy_hold_max_drawdown_pct"], 10)
        self.assertAlmostEqual(selected["same_exposure_fee_drag_pp"], 10 - selected["strategy_return_pct"])
        self.assertEqual(selected["exposed_on_benchmark_up_days_pct"], 100)
        self.assertEqual(selected["exposed_on_benchmark_down_days_pct"], 0)
        self.assertEqual(selected["turnover_days"], 2)
        self.assertEqual(selected["days_with_exposure"], 1)
        self.assertEqual(absent["status"], "no_selected_candidate")
        self.assertEqual(insufficient["status"], "insufficient_data")
        self.assertNotIn("strategy_return_pct", absent)
        self.assertNotIn("strategy_return_pct", insufficient)

    def test_cash_in_falling_benchmark(self):
        def stay_cash(rows):
            for row in rows:
                row.update(net_return=0, gross_return=0, held_weight=0, position=0,
                           cost=0, turnover=0, benchmark_return=-.03)
        make_study(self.path, changes=stay_cash)
        selected = audit(self.path)["phases"][0]
        self.assertEqual(selected["status"], "cash_throughout")
        self.assertEqual(selected["strategy_return_pct"], 0)
        self.assertAlmostEqual(selected["costed_buy_hold_return_pct"], 100 * (.97**3 - 1))
        self.assertIsNone(selected["exposed_on_benchmark_up_days_pct"])

    def test_missing_row_reports_evidence_gap(self):
        make_study(self.path, changes=lambda rows: rows.pop(1))
        result = audit(self.path)["phases"][0]
        self.assertEqual(result["status"], "incomplete_selected_ledger")
        self.assertNotIn("strategy_return_pct", result)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.path)]), 1)

    def test_invalid_observations_rejected(self):
        for column, value in [("date", "2024-01-03"), ("net_return", float("nan")),
                              ("benchmark_return", -1), ("turnover", -1), ("held_weight", .9),
                              ("cost", .1), ("position", 1.01), ("gross_return", .20)]:
            with self.subTest(column=column):
                make_study(self.path, changes=lambda rows: rows[1].update({column: value}))
                with self.assertRaises(ValueError):
                    audit(self.path)

    def test_mismatched_summary_refused(self):
        make_study(self.path)
        path = self.path / "summary.json"
        summary = json.loads(path.read_text())
        summary["assets"]["AAA"]["holdout_benchmark"] = {"total_return": 0.5}
        path.write_text(json.dumps(summary))
        with self.assertRaisesRegex(ValueError, "differs"):
            audit(self.path)
