"""Offline regression tests for as-of event scores, immutable evidence and cross-market ranking."""
import copy
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.research import didm_global_ranking as g


class GlobalRanking(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.scope = dict(event_id="earnings_Q", event_series="issuer_revenue", metric="revenue", unit="USD_m", period="quarter_Q")
        self.common = dict(event_series="issuer_revenue", metric="revenue", unit="USD_m",
                           horizon_seconds=86400, numeraire="USD", benchmark="USD_cash",
                           return_basis=g.BASIS)
        self.src = g.put_source(self.root, b"fictional deterministic test source")
        self.base = dict(source_uri="fixture:test", source_sha256=self.src)
        self.observed = self.record("observation", **self.scope, version=1, published_at=90,
                                    received_at=92, value="110")
        self.reference = self.record("reference", **self.scope, published_at=10, received_at=11,
                                     reference_type="company_guidance", value="100")
        self.study = dict(schema="tradegen.global_didm.v1", **self.scope, decision_at=100,
                          horizon_seconds=86400, numeraire="USD",
                          benchmark="USD_cash", observations=[self.observed], reference=self.reference,
                          candidates=[self.instrument("ordinary", "stock", "ordinary"),
                                      self.instrument("inverse", "etf", "daily_inverse")])

    def record(self, kind, **fields):
        return g.put_evidence(self.root, dict(**self.base, kind=kind, **fields))

    def instrument(self, name, family, payoff, beta="1000", venue="TEST", symbol=None):
        identity = dict(instrument_id=name, family=family, venue=venue, symbol=symbol or name, payoff_id=payoff)
        response = self.record("response", **identity, **self.common, intercept_bps="0", beta_bps=beta,
                               reference_type="company_guidance", score_method="relative_surprise_clamped_v1",
                               published_at=18, received_at=20, training_end=17, valid_through=130)
        costs = self.record("costs", **identity, **self.common, published_at=40, received_at=41,
                            valid_through=110, execution_bps="10", fx_bps="2", tax_bps="1", other_bps="0")
        return dict(**identity, market_access="unknown", response=response, costs=costs)

    def run_study(self):
        return g.rank(self.study, self.root)

    def update(self, pin, **fields):
        import json
        r = json.loads((self.root / (pin + ".json")).read_bytes())
        return g.put_evidence(self.root, dict(r, **fields))

    def test_time_reference_and_revisions(self):
        before = self.run_study()
        revision = self.update(self.observed, version=2, supersedes=self.observed, value="140",
                               published_at=101, received_at=104)
        self.study["observations"].append(revision)
        self.assertEqual(before, self.run_study())
        self.study["decision_at"] = 104
        self.assertEqual(self.run_study()["event"]["score"], "0.4")
        self.study["observations"] = [revision]
        with self.assertRaisesRegex(ValueError, "revision chain"):
            self.run_study()

    def test_scale_cap_reference_and_instrument_specific_costs(self):
        self.study["observations"] = [self.update(self.observed, value="350")]
        self.study["candidates"][1] = self.instrument("inverse","etf","daily_inverse",beta="-300")
        res = self.run_study()
        self.assertEqual((res["event"]["raw_surprise"], res["event"]["score"]), ("2.5", "1"))
        self.assertEqual([r["net_excess_bps"] for r in res["candidates"]], ["987", "-313"])
        self.assertEqual(res["best_in_declared_universe"],"ordinary")
        self.assertFalse(res["execution_ready"])
        self.study["reference"] = self.update(self.reference,value="0")
        self.assertEqual(self.run_study()["event"]["status"], "ZERO_REFERENCE")
        self.study["reference"] = None
        self.assertIsNone(self.run_study()["best_among_scored"])

    def test_estimates_pre_event_comparability_and_cost_coverage(self):
        c = self.study["candidates"][0]
        param = (("response",{"training_end":95},"RESPONSE_NOT_PRE_EVENT"),
                 ("response",{"received_at":95},"RESPONSE_NOT_PRE_EVENT"),
                 ("response",{"reference_type":"survey_consensus"},"INCOMPARABLE_ESTIMATE"),
                 ("costs",{"fx_bps":None},"INCOMPLETE_COSTS"),
                 ("costs",{"valid_through":99},"ESTIMATE_UNAVAILABLE_AT_DECISION"),
                 ("response",{"numeraire":"KRW"},"INCOMPARABLE_ESTIMATE"),
                 ("response",{"payoff_id":"other_contract"},"INCOMPARABLE_ESTIMATE"),
                 ("response",{"horizon_seconds":172800},"INCOMPARABLE_ESTIMATE"),
                 ("response",{"benchmark":"ETF"},"INCOMPARABLE_ESTIMATE"))
        for key,fields,reason in param:
            with self.subTest(fields=fields):
                orig = c[key]; c[key] = self.update(orig, **fields)
                result = self.run_study()
                row = next(r for r in result["candidates"] if r["instrument_id"] == "ordinary")
                self.assertEqual(row["status"], reason)
                self.assertIsNone(row["rank"])
                self.assertIsNone(result["best_in_declared_universe"])
                c[key] = orig

    def test_partial_ties_and_binary_identity(self):
        self.assertIsNone(self.run_study()["best_among_scored"])
        self.assertIn("bond", self.run_study()["missing_families"])
        yes = self.instrument("contract_Y", "prediction", "yes:$1", symbol="X")
        no = self.instrument("contract_N", "prediction", "no:$1", symbol="X")
        for c in (yes, no):
            c["terms_sha256"] = self.src
            for k in ("response", "costs"):
                c[k] = self.update(c[k], terms_sha256=self.src)
        no["response"] = None
        self.study["candidates"] = [yes,no]
        result = self.run_study()
        self.assertEqual(result["declared_count"],2)
        self.assertEqual(result["best_among_scored"],"contract_Y")
        self.assertIsNone(result["best_in_declared_universe"])
        self.study["candidates"] += [dict(yes, instrument_id="alias")]
        with self.assertRaisesRegex(ValueError, "duplicate listed payoff"):
            self.run_study()

    def test_archive_receipt_does_not_backdate_publication(self):
        self.study["observations"] = [self.update(self.observed, received_at=200)]
        self.assertEqual(self.run_study()["event"]["status"],"EVENT_UNAVAILABLE")
        self.study["information_clock"] = "public_reconstruction"
        self.assertEqual(self.run_study()["event"]["score"],"0.1")
        self.study["reference"] = self.update(self.reference, published_at=91, received_at=93)
        self.assertEqual(self.run_study()["event"]["status"],"REFERENCE_NOT_KNOWN_BEFORE_EVENT")

    def test_no_positive_and_corrupt_evidence(self):
        for c in self.study["candidates"]:
            c["response"] = self.update(c["response"],beta_bps="10")
        self.assertEqual(self.run_study()["top_positive"],[])
        (self.root / (self.src+".blob")).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_study()

    def test_catalogue_roundtrip_reject_duplicate_column_and_hash(self):
        out = self.root/"catalog.csv"
        columns = ["instrument_id","family","venue","symbol","payoff_id","market_access","response","costs"]
        with out.open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader()
            writer.writerows(self.study["candidates"])
        data=out.read_bytes(); sha=hashlib.sha256(data).hexdigest()
        self.assertEqual(g.import_catalogue(out,sha),self.study["candidates"])
        study = dict(self.study, candidates=[], catalogue_sha256=sha, catalogue_as_of=90,
                     catalogue_received_at=101)
        with self.assertRaisesRegex(ValueError, "catalogue unavailable"):
            g.rank(study, self.root, out)
        study["information_clock"] = "public_reconstruction"
        self.assertEqual(g.rank(study,self.root,out)["declared_count"], 2)
        out.write_bytes(data+b"\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            g.import_catalogue(out,sha)


if __name__ == "__main__":
    unittest.main()
