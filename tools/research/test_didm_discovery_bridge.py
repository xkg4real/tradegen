"""Regression tests for discovery provenance, clocks, and payoff-specific bindings."""
import csv
import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.research import didm_discovery_bridge as bridge
from tools.research import didm_global_ranking as ranking


class DiscoveryBridge(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.archive = self.folder / "universe.csv.gz"
        self.rows = []
        self.bindings = []
        source = ranking.put_source(self.folder, b"fixture: dated independent exchange bulletin")
        self.base = dict(source_uri="fixture:exchange-bulletin", source_sha256=source)
        scope = dict(event_id="revenue-Q1", period="Q1", event_series="issuer", metric="revenue", unit="USD")
        ref = self.receipt("reference", **scope, value="100", reference_type="company_guidance",
                           published_at=10, received_at=11)
        obs = self.receipt("observation", **scope, version=1, value="120", published_at=80, received_at=81)
        self.study = dict(schema="tradegen.global_didm.v1", decision_at=100, numeraire="USD",
                          horizon_seconds=86400, benchmark="cash", candidates=[], reference=ref,
                          observations=[obs], **scope)

    def receipt(self, kind, **fields):
        return ranking.put_evidence(self.folder, dict(self.base, kind=kind, **fields))

    def add(self, product="equity", symbol="ABC", side="", status="not_flagged_delisted"):
        unit, venue = ("payoff_side", "KALSHI") if side else ("provider_reference_or_listing", "NYSE")
        source_id = symbol + side
        key = hashlib.sha256(source_id.encode()).hexdigest()
        row = dict(dataset="test", source_id=source_id, record_key=key, unit=unit, product_class=product,
                   symbol_or_contract=symbol, venue_or_chain=venue, mic="", side=side, parent_contract=symbol if side else "",
                   asof_basis="2026 provider snapshot", source_status=status, source_ref="fixture:snapshot",
                   execution_status="unverified")
        self.rows.append(row)
        binding = {"record_key": key}
        self.bindings.append(binding)
        return row, binding

    def listing(self, row, binding, **updates):
        listing = {k: row[k] for k in bridge.IDENTITY}
        listing.update(instrument_id=row["source_id"], family=bridge.FAMILIES[row["product_class"]],
                       venue=row["venue_or_chain"], symbol=row["symbol_or_contract"], payoff_id=row["side"] or "ordinary",
                       listing_status="listed", as_of=12, published_at=13, received_at=14, valid_through=130)
        listing.update(updates)
        binding["listing"] = self.receipt("listing", **listing)
        return {k: listing[k] for k in ("instrument_id", "family", "venue", "symbol", "payoff_id")}

    def run_bridge(self):
        with gzip.open(self.archive, "wt", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted(bridge.ARCHIVE_FIELDS))
            writer.writeheader()
            writer.writerows(self.rows)
        pin = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        return bridge.evaluate(self.archive, {"archive_sha256": pin, "bindings": self.bindings},
                               self.study, self.folder)

    def test_archive_is_discovery_only_and_receipt_gates_history(self):
        self.add()
        late, binding = self.add(symbol="LATE")
        self.listing(late, binding, received_at=105)
        inactive, binding = self.add(symbol="OLD", status="flagged_delisted")
        self.listing(inactive, binding, listing_status="delisted")
        self.add(product="index_reference", symbol="SPX")
        self.bindings.append({"record_key": "f" * 64})
        result = self.run_bridge()
        self.assertEqual([r["status"] for r in result["records"]], [
            "MISSING_DATED_LISTING", "LISTING_UNAVAILABLE_AT_DECISION", "INACTIVE_AT_DECISION",
            "REFERENCE_ONLY", "ABSENT_FROM_ARCHIVE"])
        self.assertEqual(result["records"][2]["discovery"]["source_status"], "flagged_delisted")
        self.assertEqual((result["matched"], result["scored"]), (4, 0))
        self.assertIsNone(result["submitted_subset_ranking"])
        self.study["information_clock"] = "public_reconstruction"
        self.assertEqual(self.run_bridge()["submitted"], 1)

    def test_kalshi_sides_remain_distinct_and_cannot_borrow_other_side(self):
        for side in ("YES", "NO"):
            row, binding = self.add(product="prediction_market", symbol="KX-EVENT", side=side)
            self.listing(row, binding)
        result = self.run_bridge()
        self.assertEqual(result["submitted"], 2)
        self.assertEqual(result["scored"], 0)
        self.assertEqual({r["payoff_id"] for r in result["submitted_subset_ranking"]["candidates"]}, {"YES", "NO"})
        self.listing(row, binding, payoff_id="YES")
        with self.assertRaisesRegex(ValueError, "payoff mismatch"):
            self.run_bridge()

    def test_unknown_payoff_remains_visible_without_blocking_a_binary_contract(self):
        unmodeled, _ = self.add(product="prediction_market", symbol="KX-MULTI", side="DRAW")
        row, binding = self.add(product="prediction_market", symbol="KX-EVENT", side="YES")
        self.listing(row, binding)
        result = self.run_bridge()
        self.assertEqual(result["records"][0]["discovery"]["side"], unmodeled["side"])
        self.assertEqual(result["records"][0]["status"], "UNMODELED_PAYOFF")
        self.assertEqual(result["submitted"], 1)

    def test_newer_delisting_flag_blocks_a_stale_listing(self):
        row, binding = self.add(symbol="OLD", status="flagged_delisted")
        row.update(dataset="listed", asof_basis="1970-01-01 provider snapshot")
        self.listing(row, binding)
        self.assertEqual(self.run_bridge()["records"][0]["status"], "DELISTED_AT_SNAPSHOT")

    def test_only_independently_supported_equity_scores(self):
        row, binding = self.add()
        identity = self.listing(row, binding)
        common = {k: self.study[k] for k in ("event_series", "metric", "unit", "horizon_seconds", "numeraire", "benchmark")}
        common.update(identity, return_basis=ranking.BASIS)
        binding["response"] = self.receipt("response", **common, intercept_bps="0", beta_bps="100",
                                           reference_type="company_guidance", score_method="relative_surprise_clamped_v1",
                                           published_at=15, received_at=17, training_end=13, valid_through=120)
        binding["costs"] = self.receipt("costs", **common, execution_bps="1", tax_bps="0", fx_bps="1",
                                        other_bps="0", published_at=22, received_at=23, valid_through=120)
        self.add(symbol="OUTSIDE_THE_REQUEST")
        self.bindings.pop()
        result = self.run_bridge()
        self.assertEqual(result["archive_records_by_unit"], {"provider_reference_or_listing": 2})
        self.assertEqual((result["requested"], result["submitted"], result["scored"]), (1, 1, 1))
        self.assertEqual(result["submitted_subset_ranking"]["candidates"][0]["net_excess_bps"], "18.0")
        self.assertFalse(result["execution_ready"])
        with self.assertRaisesRegex(ValueError, "archive hash mismatch"):
            bridge.evaluate(self.archive, {"archive_sha256": "0" * 64, "bindings": []}, self.study, self.folder)
