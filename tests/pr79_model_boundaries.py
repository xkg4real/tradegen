"""Reproduce held-out selection and online evidence boundaries using offline panels."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from qlib_lab.data.dataset import DatasetH, TSDatasetH, authorized_eval_context
from qlib_lab.data.handler import DataHandler, DataHandlerLP
from qlib_lab.data.labels import PurgedHorizonReturnLabel
from qlib_lab.data.loader import ExpressionDataLoader, StaticDataLoader
from qlib_lab.data.processors import StandardZScoreNorm
from qlib_lab.exceptions import FitLeakageError, SnapshotContractError, TestLabelLeakageError
from qlib_lab.models.direction import MultinomialDirectionModel
from qlib_lab.online.exporter import NonRevisionIndex
from qlib_lab.online.manager import OnlineManager
from tests.qlib_lab_workflow_online import _build_strong_direction_study_data


class ResearchBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.days = pd.date_range("2026-11-01", periods=8, tz="UTC")
        idx = pd.MultiIndex.from_product([self.days, ["KRW-BTC"]], names=["datetime", "instrument"])
        df = pd.DataFrame({("feature", "x"): range(8), ("label", "y"): range(8)}, index=idx)
        self.loader = StaticDataLoader(df)
        self.handler = DataHandler(data_loader=self.loader)
        self.segments = {"train": (self.days[0], self.days[3]), "test": (self.days[5], self.days[7]),
                         "overlapping": (self.days[4], self.days[6])}

    def test_held_out_date_selectors_protect_labels_and_callbacks(self):
        ds = DatasetH(self.handler, self.segments)
        for selector in ("overlapping", pd.Index([self.days[5]]), self.days[6]):
            with self.subTest(selector=selector), self.assertRaises(TestLabelLeakageError):
                ds.prepare(selector, col_set="label")
            self.assertEqual(list(ds.prepare(selector).columns), ["x"])
        with self.assertRaises(TestLabelLeakageError):
            ds.prepare("KRW-BTC", col_set="label", level="instrument")
        with self.assertRaises(TestLabelLeakageError):
            ds.prepare("test", col_set="feature", proc_func=lambda df: df)
        with authorized_eval_context():
            self.assertEqual(len(ds.prepare("test", col_set="label")), 3)

    def test_sampler_tuple_cannot_fetch_outside_split(self):
        ds = TSDatasetH(self.handler, self.segments, step_len=2)
        s = ds.prepare("test", col_set="feature")
        self.assertEqual(int(s[(self.days[5], "KRW-BTC")][-1, 0]), 5)
        with self.assertRaises(KeyError):
            s[(self.days[4], "KRW-BTC")]

    def test_embargo_also_removes_processor_fit_rows(self):
        proc = StandardZScoreNorm(fit_start_time=self.days[0], fit_end_time=self.days[3])
        handler = DataHandlerLP(data_loader=self.loader, infer_processors=[proc])
        with self.assertRaises(FitLeakageError):
            DatasetH(handler, self.segments, embargo_bars=2)

    def test_delayed_price_receipt_keeps_ended_outcomes_out_of_training(self):
        epochs = [int(day.timestamp()) for day in self.days]
        known = list(epochs)
        known[2] = epochs[6]
        raw = pd.DataFrame({"datetime": epochs, "instrument": "KRW-BTC", "return_bps": 12,
                            "close": 100.0, "known_at": known})
        handler = DataHandlerLP(data_loader=ExpressionDataLoader(
            raw, feature_expressions={"x": "$close"}, on_lag_violation="nan",
            label_config=PurgedHorizonReturnLabel(horizon_bars=2, step_seconds=86400)))
        ds = DatasetH(handler, self.segments)
        train = ds.prepare("train", col_set="label", data_key=DataHandlerLP.DK_L)
        self.assertTrue(train.empty)
        clocks = handler.fetch(col_set="meta")
        self.assertEqual(clocks["label_end_utc"].iloc[0], epochs[2])
        self.assertEqual(clocks["label_known_at"].iloc[0], epochs[6])

    def test_two_index_writers_observe_the_same_first_forecast(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forecasts.jsonl"
            first = NonRevisionIndex(path)
            second = NonRevisionIndex(path)
            fc = {"market": "KRW-BTC", "as_of": 1700000000, "horizon_seconds": 7200, "direction": "up"}
            self.assertEqual(first.check_and_commit("a" * 64, [fc]), 1)
            self.assertEqual(second.check_and_commit("a" * 64, [fc]), 0)
            with self.assertRaisesRegex(SnapshotContractError, "FORECAST_REVISED"):
                second.check_and_commit("a" * 64, [{**fc, "direction": "down"}])
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_challenger_cannot_be_scored_on_dates_before_its_freeze(self):
        _, ds, _ = _build_strong_direction_study_data(200)
        model = MultinomialDirectionModel().fit(ds)
        cutoff = ds.effective_training_cutoff()
        last = int(ds.segments["test"][1].timestamp())
        champ = model.to_frozen_spec(model_name="champ", model_version="1", training_cutoff=cutoff, frozen_at=cutoff)
        newer = model.to_frozen_spec(model_name="new", model_version="2", training_cutoff=cutoff, frozen_at=last)
        with tempfile.TemporaryDirectory() as tmp:
            manager = OnlineManager(state_dir=Path(tmp), champion_spec=champ, challengers={"new": newer})
            result = manager.routine(last, ds, evaluation_start=ds.segments["train"][0])
        self.assertEqual(result["challenger_evaluations"]["new"]["n_closed_windows"], 0)
        self.assertFalse(result["promotion_candidates"])
