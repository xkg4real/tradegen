"""Regression tests for missing study evidence and cross-stage reuse. All data are synthetic."""
from __future__ import annotations

import copy
import unittest

from tools.research import direction_model_fit as fit
from tools.research import direction_stage1_evaluator as first
from tools.research import direction_stage2_replay as second
from tools.research._study_common import StudyError, kst_date_iso, sha256_ascii
from tools.research.test_direction_model_fit import _make_synthetic_dataset
from tools.research.test_direction_stage1_evaluator import _build_stage1_scenario, _coverage_table, _seal_snap
from tools.research.test_direction_stage2_replay import _make_daily_quote_doc, _make_obs


class DirectionGateEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study, hist, m, b1, b0 = _build_stage1_scenario()
        cls.study = study
        cls.m, cls.hist, cls.b0 = m, hist, b0
        cls.table = _coverage_table(study, hist)
        cls.first_args = dict(study=study, history=hist, m_snapshots=[m], b1_snapshots=[b1],
                              b0_snapshots=[b0], feature_table=cls.table)
        passed = first.evaluate_stage1(**cls.first_args)
        assert passed["outcome"] == "PASS"
        when = study["evaluation_end"] + 7200
        day = _make_daily_quote_doc(kst_date_iso(when), study["scope"], [_make_obs(1, when, study["scope"])])
        cls.second_args = dict(study=study, stage1_report=passed, stage1_history=hist, daily_quote_records=[day],
                               m_snapshots=[m], b1_snapshots=[b1])

    def test_b0_must_cover_the_same_windows(self):
        short = _seal_snap({**self.b0, "forecasts": self.b0["forecasts"][:1]})
        for snapshots in ([], [short]):
            with self.subTest(total=len(snapshots)):
                rep = first.evaluate_stage1(**{**self.first_args, "b0_snapshots": snapshots})
                self.assertFalse(rep["criterion2"]["beats_B0_point_estimate"])
                self.assertNotEqual(rep["outcome"], "PASS")

    def test_missing_and_absent_feature_rows_void_study(self):
        table = {**self.table, "rows": self.table["rows"][:28]}
        table["table_sha256"] = sha256_ascii({k: v for k, v in table.items() if k != "table_sha256"})
        for evidence in (None, table):
            rep = first.evaluate_stage1(**{**self.first_args, "feature_table": evidence})
            self.assertEqual((rep["outcome"], rep["stop_rule"]), ("VOID", "S1"))

    def test_missing_training_features_are_counted_against_price_calendar(self):
        bars, table = _make_synthetic_dataset(140)
        table["rows"] = table["rows"][::2]
        args = dict(bars=bars, feature_table=table, train_start=bars[30]["end"], train_end=bars[130]["end"],
                    frozen_at=bars[130]["end"] + 60)
        with self.assertRaisesRegex(StudyError, "FEATURE_TABLE_SHA256_MISMATCH"):
            fit.fit_and_freeze_models(**args)
        table["table_sha256"] = sha256_ascii({k: v for k, v in table.items() if k != "table_sha256"})
        with self.assertRaisesRegex(StudyError, "S1_MISSING_FEATURES_EXCEED_5PCT"):
            fit.fit_and_freeze_models(**args)

    def test_mixed_or_changed_stage_one_inputs_cannot_open_stage_two(self):
        changed_history = copy.deepcopy(self.hist)
        changed_history["bars"][-1]["return_bps"] += 1
        revised = _seal_snap({**self.m, "forecasts": self.m["forecasts"][1:]})
        changed_report = {**self.second_args["stage1_report"], "passing_directions": []}
        cases = (
            ({"stage1_report": changed_report}, "STAGE1_REPORT_HASH_MISMATCH"),
            ({"stage1_history": changed_history}, "STAGE1_HISTORY_CHANGED"),
            ({"study": {**self.study, "confidence": "0.61"}}, "STAGE1_STUDY_CHANGED"),
            ({"m_snapshots": [revised]}, "STAGE1_FORECASTS_CHANGED"),
        )
        for updates, code in cases:
            with self.subTest(reason=code), self.assertRaisesRegex(StudyError, code):
                second.run_stage2_replay(**{**self.second_args, **updates})
