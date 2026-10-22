"""M7 package D: card registry, blind header commits, verdict chain, archive, printed lines, package freeze and the
study runner (T-CARD-01/02, T-BOOK-01 printed-line clause, T-BOOK-02, T-REPRO-01b, T-STEP-01..04, T-R03-01,
T-R04-01, T-R14-01, T-R06-US-01, I-07, I-09, I-15, I-16, T-CAP-02 stack clause). Hermetic: temporary copies of
the rules store, the governance log, the card root and the macro dir; synthetic cards only; every formal, golden
or owner clause raises NotRun with its reason. The freeze is never executed against the shipped store.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.ficc import macro_schema as S
from core.quant import card_lines as CL
from core.quant import cards
from core.quant import gate_package as GP
from core.quant import risk_layer as RL
from core.rules import governance as G
from core.rules import macro_rules as M
from tests.macro_m0_schemas import synthetic_card
from tests.notrun import NotRun, require_fixture

ROOT = Path(__file__).resolve().parents[1]
LEGACY_CARDS = ROOT / "docs" / "asset_expansion" / "cards"
DRAFTS = ROOT / "docs" / "macro_overlay" / "headers"
CLOCK = lambda: datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)   # noqa: E731
ANCHOR = "c" * 40
KR_SLEEVE, US_SLEEVE = 1.12e9, 1.04e9


def _md5_tree(d: Path) -> dict[str, str]:
    return {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.glob("*")) if p.is_file()}


_LEGACY_BEFORE = _md5_tree(LEGACY_CARDS)


def _store(tmp: Path, *, frozen: bool, signed: bool = True, extra=None) -> tuple[M.MacroStore, Path]:
    doc = json.loads(M.SHIPPED_STORE_PATH.read_text(encoding="utf-8"))
    if signed:
        doc["sleeves"]["KR"]["notional_nav"] = KR_SLEEVE
        doc["sleeves"]["US"]["notional_nav"] = US_SLEEVE
    if frozen:
        doc["gate"]["package"].update({"definitions_md5": "a" * 32, "acceptance_report_md5": "b" * 32,
                                       "frozen_utc": "2026-10-06T00:00:00Z", "status": "FROZEN", "anchor_commit": ANCHOR})
    if extra:
        extra(doc)
    p = tmp / "rules.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return M.load_store(p), p


class StubLedger:
    """Duck-typed R-23 family ledger (hash per family, N_raw per family); the harness appends at the run."""

    def __init__(self):
        self.rows = {"R-06": 3, "R-03": 26, "R-31": 6, "R-28": 94, "R-14": 1, "R-02": 1}

    def hash(self, fam):
        return hashlib.md5(f"{fam}:{self.rows.get(fam, 0)}".encode()).hexdigest()

    def n_raw(self, fam):
        return self.rows.get(fam, 1)


def _fill(d: dict) -> dict:
    """Fill the owner / refdata nulls of a draft with synthetic values (a signed store supplies the notional)."""
    cid = d["card_id"]
    d["data"]["history_file"] = "synthetic"
    if cid == "MACRO-R06-KR-ETF":
        d["costs"]["schedule"][0]["to"], d["costs"]["schedule"][1]["from"] = "2002-10-13", "2002-10-14"
        d["gating_lines"]["etf_era"]["from"] = "2002-11-01"
    if d.get("nav_fx"):
        d["nav_fx"]["conversion_instant"] = "15:30 KST"
    if d.get("roll_calendar"):
        d["roll_calendar"]["calendar"] = ["2026-12-18"]
    if d.get("history_first_close") is None:
        d["history_first_close"] = "1990-01-02"
    if d["data_span"].get("start") is None:
        d["data_span"]["start"] = "first_close_plus_warmup"
    if d.get("midpoint_halves") and d["midpoint_halves"].get("split_date") is None:
        d["midpoint_halves"]["split_date"] = cards.calendar_midpoint(d["history_first_close"], d["data_span"]["end"])
    return d


def _commit(tmp: Path, store, cid: str, rev=None, ledger=None, **kw) -> dict:
    d = _fill(cards.draft_header(cid, store, revision=rev))
    return cards.commit_header(d, store, ledger or StubLedger(), CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl", **kw)


def _refused(fn, needle: str) -> list[str]:
    try:
        fn()
    except cards.CardRefused as exc:
        hits = [r for r in exc.reasons if needle in r]
        assert hits, f"refused without {needle!r}: {exc.reasons}"
        return exc.reasons
    raise AssertionError(f"not refused ({needle!r})")


def _results(**over) -> dict:
    """Synthetic result fields (seed-11 fillers from the M0 fixture) for a given verdict / disposition."""
    card = synthetic_card()
    res = {k: v for k, v in card.items() if k in S.RESULT_FIELDS}
    res.update(over)
    return res


# --------------------------------------------------------------------------- #
# Registry and drafts
# --------------------------------------------------------------------------- #
def test_registry_every_card_not_run_and_drafts_in_sync():
    """Every registered card is NOT_RUN today except the registered US REJECT; the shipped drafts equal draft_header
    on the shipped store (typed nulls kept); each null is explained; the register of section 9.4 matches goldens.csv."""
    store = M.load_store()
    for spec in cards.REGISTRY:
        st = cards.card_status(None, spec.card_id, store)
        assert st["verdict"] == ("REJECT" if spec.card_id == "MACRO-R06-US" else "NOT_RUN") and st["results_md5"] is None, st
        assert not cards.check_display_invariant(st["verdict"], st["disposition"], st["displayed_as"]), st
        assert st["disposition"] not in cards.PASS_DISPOSITIONS
    assert [c.card_id for c in cards.REGISTRY if c.step4_header] == ["MACRO-R06-KR-ETF", "MACRO-R03-US-MOM", "MACRO-R14-MULTI-TREND",
                                                                       "MACRO-R31-KR-ETF", "MACRO-R28-US-TREND", "MACRO-R06-US-FUT"]
    assert cards.BY_ID["MACRO-R06-KR-ETF"].revisions == (2,) and cards.BY_ID["MACRO-R03-US-MOM"].revisions == (1, 2, 3)
    assert len(cards.BY_ID["MACRO-R06-KR-ETF"].conditions) == 5 and cards.BY_ID["MACRO-R06-KR-ETF"].label == cards.R06_KR_LABEL
    n = 0
    for spec in cards.REGISTRY:
        if not spec.step4_header:
            continue
        for rev in spec.revisions:
            shipped = json.loads(cards.draft_path(DRAFTS.parent, spec.card_id, rev).read_text(encoding="utf-8"))
            assert shipped == cards.draft_header(spec.card_id, store, revision=rev), (spec.card_id, rev)
            nulls = cards.owner_nulls(shipped)
            assert nulls and not any(v.startswith("UNEXPLAINED") for v in nulls.values()), nulls
            assert "notional_nav" in nulls and "gate_package_md5" in nulls, nulls
            assert shipped["label"] == spec.label and shipped["class"] == spec.cls and shipped["revision"] == rev
            n += 1
    assert n == 8
    assert cards.calendar_midpoint("1997-04-01", "2026-10-02") == "2012-01-01"
    assert [p["golden_id"] for p in cards.PENDING_VALUES] == [f"P94-{i:02d}" for i in range(1, 18)]
    rows = [ln.split(",")[0] for ln in (ROOT / "tests" / "fixtures" / "macro" / "goldens.csv").read_text(encoding="utf-8").splitlines()]
    assert all(p["golden_id"] in rows for p in cards.PENDING_VALUES)
    assert {p["item"] for p in cards.PENDING_VALUES if p["package_dependent"]} == {1, 4, 11, 12, 14}
    # the drafts refuse the schema for exactly the typed nulls (plus H4 on the null md5), never silently pass
    d = cards.draft_header("MACRO-R06-KR-ETF", store)
    assert any("/notional_nav" in m for m in S.header_issues(d, seed_study=11))
    # every series the headers name is registered with a contract (T-SER-02 scans the same set)
    from core.ficc import contracts as C
    ids = cards.referenced_series_ids(DRAFTS.parent, store)
    assert ids == cards.referenced_series_ids(None, store) and {"KOSPI_OFFICIAL_CLOSE", "BOK_CALL_RATE", "US_RF"} <= ids
    assert C.unknown_ids(C.default_registry(), ids) == []


test_registry_every_card_not_run_and_drafts_in_sync.test_ids = ["T-CARD-01", "T-BOOK-01"]


def test_r06_us_registered_reject_never_rerun():
    """T-R06-US-01: the verbatim label, rerun False, a record not a run; the runner refuses its id; vt > 1.0 fails."""
    store = M.load_store()
    reg = cards.registered_reject(store)
    assert reg["label"] == "REJECT (instrument: US shares via KIS, 50 bp, daily)" and reg["rerun"] is False
    assert reg["verdict"] == "REJECT" and reg["results_md5"] is None and reg["displayed_as"] == "descriptive"
    assert store.get("vol_target.US.registered_card.rerun") is False
    assert not cards.BY_ID["MACRO-R06-US"].rerun and not cards.BY_ID["MACRO-R06-US"].step4_header
    import docs.macro_overlay_study as study
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        _refused(lambda: study.run_card("MACRO-R06-US", 1, store=store, root=tmp / "root", macro_dir=tmp / "macro", anchor=ANCHOR,
                                        knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK), "never re-run")
        assert not (tmp / "root").exists() and not (tmp / "macro").exists()
    for bad in (1.0001, 1.5):
        try:
            M.assert_vt(bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    # the registered card's rule object is exactly the refused shape: a stock book as a market-gross scalar (DNB 33)
    r = M.validate_rule_object(cards.rule_object("MACRO-R06-US"))
    assert [i.message for i in r.errors if "[krx_stock_book_on_market_gross_scalar]" in i.message]
    r = M.validate_rule_object(M.RuleObject(**{**vars(cards.rule_object("MACRO-R06-US")), "output_range": (0.0, 1.5)}))
    assert any("[multiplier_weight_or_cap_above_1]" in i.message for i in r.errors)
    assert M.validate_rule_object(cards.rule_object("MACRO-R06-US-FUT")).ok


test_r06_us_registered_reject_never_rerun.test_ids = ["T-R06-US-01"]


# --------------------------------------------------------------------------- #
# T-CARD-01: header mechanics
# --------------------------------------------------------------------------- #
def test_card01_commit_refusals_before_the_freeze_and_with_nulls():
    """No header is committed here: NOT_FROZEN, UNVERSIONED and every typed null are listed in one refusal; a frozen
    store with nulls still refuses; nothing is written; gate/acceptance_runs.jsonl never appears."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=False, signed=False)
        d = cards.draft_header("MACRO-R06-KR-ETF", store)
        reasons = _refused(lambda: cards.commit_header(d, store, StubLedger(), CLOCK, "UNVERSIONED", root=tmp / "root", governance_log=tmp / "gov.jsonl"),
                           "NOT_FROZEN")
        assert any("owner must place the repository under git" in r for r in reasons)
        assert any(r.startswith("NULL notional_nav") for r in reasons) and any("NULL costs.schedule[0].to" in r for r in reasons)
        assert not any("NULL created_utc" in r or "NULL header_md5" in r for r in reasons)
        try:
            cards.commit_header(d, store, StubLedger(), CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl")
            raise AssertionError
        except cards.PackageNotFrozen:
            pass
        store2, _ = _store(tmp, frozen=True, signed=False)
        reasons = _refused(lambda: cards.commit_header(d, store2, StubLedger(), CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl"),
                           "NULL notional_nav")
        assert not any("NOT_FROZEN" in r for r in reasons)
        assert not (tmp / "root").exists() and not (tmp / "gov.jsonl").exists()
        assert not (tmp / "macro" / "gate" / "acceptance_runs.jsonl").exists()


test_card01_commit_refusals_before_the_freeze_and_with_nulls.test_ids = ["T-CARD-01", "I-07"]


def test_card01_commit_md5_cover_immutable_and_budget_on_synthetic_frozen_store():
    """On a temp store with a dummy frozen package and signed sleeves: the commit writes header_md5 over the header
    fields only, records the ledger hash and N_raw, appends a header_commit event; a mismatched md5, an edited
    header, a second commit, a foreign package citation, a declared selection_factor and a ninth searched parameter
    are refused."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=True)
        led = StubLedger()
        h = _commit(tmp, store, "MACRO-R06-KR-ETF", ledger=led)
        assert h["header_md5"] == S.header_md5(h) and h["created_utc"] == "2026-10-06T12:00:00Z"
        assert h["ledger_hash_at_registration"] == led.hash("R-06") and h["N_raw_at_registration"] == 3
        assert h["gate_package_md5"] == "a" * 32 and h["checks"] == "gate_package_2.0.0" and h["notional_nav"] == KR_SLEEVE
        assert set(h) <= S.HEADER_FIELDS and not (set(h) & S.RESULT_FIELDS)
        on_disk = cards.load_header(tmp / "root", "MACRO-R06-KR-ETF", 2)
        assert on_disk == h
        ev = G.read_events(tmp / "gov.jsonl")
        assert len(ev) == 1 and ev[0]["kind"] == "header_commit" and ev[0]["new"] == h["header_md5"] and ev[0]["actor"] == "harness"
        # md5 covers the header fields only: a result field never changes it; a header field does
        assert S.header_md5({**h, "verdict": "PASS", "results_md5": "x"}) == h["header_md5"]
        assert S.header_md5({**h, "rebalance": "weekly"}) != h["header_md5"]
        assert cards.draft_md5(h) == cards.draft_md5({**h, "header_md5": "0" * 32, "created_utc": "1999-01-01T00:00:00Z", "N_raw_at_registration": 99})
        assert cards.draft_md5(h) != cards.draft_md5({**h, "claim": "other"})
        # a hand-edited committed header re-hashes differently and is refused on read (T-CARD-01)
        p = cards.header_path(tmp / "root", "MACRO-R06-KR-ETF", 2)
        edited = json.loads(p.read_text(encoding="utf-8"))
        edited["rebalance"] = "weekly"
        p.write_text(S.canonical_json(edited), encoding="utf-8")
        _refused(lambda: cards.load_header(tmp / "root", "MACRO-R06-KR-ETF", 2), "differs from the committed")
        p.write_text(S.canonical_json(h), encoding="utf-8")
        assert cards.load_header(tmp / "root", "MACRO-R06-KR-ETF", 2) == h
        _refused(lambda: _commit(tmp, store, "MACRO-R06-KR-ETF", ledger=led), "IMMUTABLE")
        # foreign package citation, declared result field, CARD-P draft mismatch, parameter budget
        d = _fill(cards.draft_header("MACRO-R31-KR-ETF", store))
        _refused(lambda: cards.commit_header({**d, "gate_package_md5": "f" * 32}, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl"), "PACKAGE")
        _refused(lambda: cards.commit_header({**d, "selection_factor": {"value": 1.0}}, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl"), "selection_factor")
        logged = [json.loads(x) for x in (tmp / cards.REFUSAL_LOG).read_bytes().split(b"\n") if x]      # section 10.3: the refusal is logged
        assert logged[-1]["card_id"] == "MACRO-R31-KR-ETF" and any("selection_factor" in r["message"] for r in logged[-1]["refusals"])
        _refused(lambda: cards.commit_header(d, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl", acceptance_draft_md5="0" * 32), "DRAFT")
        _refused(lambda: cards.commit_header({**d, "searched_parameters": [f"p{i}" for i in range(9)]}, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl"), "BUDGET")
        h31 = cards.commit_header(d, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl", acceptance_draft_md5=cards.draft_md5(d))
        assert h31["owner_decisions"] == {"risk_layer.drawdown.hard_stop.level": -0.15}
        assert len(cards.committed_headers(tmp / "root")) == 2 and G.verify_chain(tmp / "gov.jsonl").n_rows == 2
        # R-14 stays refused: the council inputs (lines, notional) are not in the spec (F-10)
        _refused(lambda: _commit(tmp, store, "MACRO-R14-MULTI-TREND", ledger=led), "instrument_lines")


test_card01_commit_md5_cover_immutable_and_budget_on_synthetic_frozen_store.test_ids = ["T-CARD-01", "T-CARD-02"]


def test_card01_class_change_is_a_revision_claim_change_is_a_new_card():
    """Brief F-03: a class (or window, estimator, cash, band) change is revision + 1 under the same id; a claim,
    instrument-book, rebalance or band change is a new card id; the old header is untouched; both records exist;
    the ledger count at registration follows the harness's rows."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=True)
        led = StubLedger()
        h1 = _commit(tmp, store, "MACRO-R03-US-MOM", 1, ledger=led)
        rev = cards.next_header(h1, {"class": "CARD-P", "claim_type": "protection", "build_status_on_pass": "BUILD_AS_INSURANCE",
                                     "comparator": "S_same_average_exposure", "label": cards.DEFAULT_CARDP_LABEL})
        assert rev["card_id"] == h1["card_id"] and rev["revision"] == 2 and rev["header_md5"] is None
        try:
            cards.next_header(h1, {"claim": "a different claim"})
            raise AssertionError
        except cards.CardRefused as exc:
            assert "new card" in exc.reasons[0]
        new = cards.next_header(h1, {"instrument_book": "KRX_listed_SP500_ETF", "fill_model": "KRX_close_auction"}, new_card_id="MACRO-R03-US-ETF")
        assert new["card_id"] == "MACRO-R03-US-ETF" and new["revision"] == 1
        led.rows["R-03"] += 1                                    # the harness appended the revision's run row (F-04)
        rev["revision"] = 2
        h2 = cards.commit_header(rev, store, led, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl")
        assert h2["N_raw_at_registration"] == h1["N_raw_at_registration"] + 1 and h2["ledger_hash_at_registration"] != h1["ledger_hash_at_registration"]
        assert cards.load_header(tmp / "root", "MACRO-R03-US-MOM", 1) == h1
        assert {p.name for p in (tmp / "root" / "headers").glob("*.header.json")} == {"MACRO-R03-US-MOM.r1.header.json", "MACRO-R03-US-MOM.r2.header.json"}
        # a header edit after results_md5 under the same card id is refused by the DNB shape (items 23/32)
        prev = M.rule_of_header(M.RuleObject(**{**vars(cards.rule_object("MACRO-R03-US-MOM")), "results_md5": "a" * 32}), h1)
        r = M.validate_card_header({**h1, "rebalance": "weekly", "header_md5": S.header_md5({**h1, "rebalance": "weekly"})}, store,
                                   rule=cards.rule_object("MACRO-R03-US-MOM"), previous=prev)
        assert any("[header_edit_after_results_md5]" in i.message for i in r.errors)


test_card01_class_change_is_a_revision_claim_change_is_a_new_card.test_ids = ["T-CARD-01", "T-R03-01"]


def test_card01_displayed_as_iff_pass_and_disposition_table():
    """displayed_as in {recommendation, insurance} iff verdict PASS; the disposition table of brief B1."""
    kr = {"family_id": "R-06", "rule_id": "R-06-KR-VT20", "card_id": "MACRO-R06-KR-ETF", "build_status_on_pass": "BUILD_AS_INSURANCE", "class": "CARD-P"}
    assert cards.disposition_for(kr, "PASS") == ("BUILD_AS_INSURANCE", "insurance")
    assert cards.disposition_for({**kr, "build_status_on_pass": "BUILD_NOW"}, "PASS") == ("RECOMMENDATION", "recommendation")
    for v in ("NOT_RUN", "INSUFFICIENT_DATA"):
        assert cards.disposition_for(kr, v) == ("SPECIFICATION_ONLY", "descriptive")
    assert cards.disposition_for(kr, "REJECT") == ("DESCRIPTIVE", "descriptive")
    r31 = {"family_id": "R-31", "rule_id": "R-31-KR-STEP"}
    assert cards.disposition_for(r31, "NOT_RUN", binding_share=0.10) == ("INVARIANT_STEP", "invariant")
    assert cards.disposition_for(r31, "NOT_RUN", binding_share=0.1001) == ("SPECIFICATION_ONLY", "descriptive")
    assert cards.disposition_for({"family_id": "R-28"}, "NOT_RUN") == ("FORWARD_SIM", "descriptive")
    assert cards.disposition_for({"family_id": "R-06", "card_id": "MACRO-R06-US-FUT"}, "REJECT") == ("FORWARD_SIM", "descriptive")
    assert cards.disposition_for({"family_id": "R-12", "rule_id": "R-12-S2"}, "REJECT") == ("REFUSAL_BOOK", "refusal")
    assert cards.disposition_for({"family_id": "R-03", "rule_id": "R-04-DM"}, "NOT_RUN") == ("SPECIFICATION_ONLY", "descriptive")
    assert cards.disposition_for({"family_id": "R-03", "rule_id": "R-03-US-VS12"}, "NOT_RUN") == ("DESCRIPTIVE", "descriptive")
    for verdict in ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA", "NOT_RUN"):
        for disp in ("RECOMMENDATION", "BUILD_AS_INSURANCE", "INVARIANT_STEP", "SPECIFICATION_ONLY", "FORWARD_SIM", "REFUSAL_BOOK", "DESCRIPTIVE"):
            for shown in ("recommendation", "insurance", "invariant", "descriptive", "refusal"):
                ok = not cards.check_display_invariant(verdict, disp, shown)
                want = ((disp in cards.PASS_DISPOSITIONS) == (verdict == "PASS")) and \
                       ((shown in ("recommendation", "insurance")) == (verdict == "PASS" and disp in cards.PASS_DISPOSITIONS))
                assert ok == want, (verdict, disp, shown)


test_card01_displayed_as_iff_pass_and_disposition_table.test_ids = ["T-CARD-01"]


def test_card01_formal_headers_owner_blocked():
    raise NotRun("OWNER: sleeves.KR/US.notional_nav null, KODEX 200 listing date unsigned, no git anchor, gate.package NOT_FROZEN: "
                 "no formal header is committed on this machine")


test_card01_formal_headers_owner_blocked.test_ids = ["T-CARD-01"]


# --------------------------------------------------------------------------- #
# Cards, verdicts.jsonl, archive (T-REPRO-01b)
# --------------------------------------------------------------------------- #
def test_repro01b_results_md5_stable_volatile_excluded_nan_null_chain_and_archive():
    """results_md5 ignores generated_at_utc / git_hash / tree_hash / results_md5 and covers every other result field;
    NaN is written as null and the card validates; a verdict row chains; a hand edit breaks the chain; the archive
    re-derives data_snapshot_id and a lost archive is ArchiveLost."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=True)
        h = _commit(tmp, store, "MACRO-R06-KR-ETF")
        rows = [{"series_id": "KOSPI_OFFICIAL_CLOSE", "obs_date": f"2026-09-{d:02d}", "value": 7000.0 + d, "content_hash": hashlib.md5(str(d).encode()).hexdigest()}
                for d in (3, 1, 2)]
        res = _results(verdict="INSUFFICIENT_DATA", verdict_reason="underpowered", disposition="SPECIFICATION_ONLY", caps_applied=[],
                       data_snapshot_id=cards.rederive_snapshot_id(rows), knowledge_utc="2026-10-02T07:00:00Z", git_hash="UNVERSIONED",
                       gjr_null_pct=float("nan"), config_hash=store.config_hash)
        path = cards.write_card(tmp / "root", h, res, CLOCK, store=store)
        card = json.loads(path.read_text(encoding="utf-8"))
        assert path.name == "MACRO-R06-KR-ETF.r2.json" and card["gjr_null_pct"] is None and card["read_only"] is True
        assert len(card["tree_hash"]) == 64 and int(card["tree_hash"], 16) >= 0  # ruling 3.1 sha256 (volatile, outside results_md5)
        assert card["results_md5"] == S.results_md5(card) and card["header_md5"] == h["header_md5"]
        same = {**card, "generated_at_utc": "2001-01-01T00:00:00Z", "git_hash": "deadbeef", "tree_hash": "x", "results_md5": "y"}
        assert S.results_md5(same) == card["results_md5"]
        assert S.results_md5({**card, "verdict_reason": "stability"}) != card["results_md5"]
        assert S.results_md5({**card, "claim": "edited"}) == card["results_md5"]       # header fields are header_md5's
        assert not S.card_issues(card, committed_header=h, seed_study=11)
        # the display invariant and the NOT_RUN state are refused at write
        _refused(lambda: cards.write_card(tmp / "root", h, {**res, "verdict": "REJECT", "disposition": "RECOMMENDATION"}, CLOCK, store=store), "DNB 22")
        _refused(lambda: cards.write_card(tmp / "root", h, {**res, "verdict": "NOT_RUN"}, CLOCK, store=store), "NOT_RUN")
        # a refused card never lands beside the cards: it is quarantined with its errors (R-32 L3370)
        q = [json.loads(p.read_text(encoding="utf-8")) for p in (tmp / "root" / "quarantine").glob("*.json")]
        assert len(q) == 2 and all(x["schema"] == "model_card.macro" and x["issues"] for x in q)
        assert [p.name for p in (tmp / "root" / "cards").glob("*.json")] == ["MACRO-R06-KR-ETF.r2.json"]
        # verdicts.jsonl
        row = cards.append_verdict(tmp / "root", card)
        assert set(row) == set(cards.VERDICT_ROW) and row["prev_row_md5"] is None and row["results_md5"] == card["results_md5"]
        row2 = cards.append_verdict(tmp / "root", {**card, "revision": 3, "results_md5": card["results_md5"]})
        assert row2["prev_row_md5"] is not None and cards.verify_verdict_chain(tmp / "root").n_rows == 2
        vp = cards.verdicts_path(tmp / "root")
        lines = vp.read_bytes().split(b"\n")
        lines[0] = lines[0].replace(b"INSUFFICIENT_DATA", b"PASS")
        vp.write_bytes(b"\n".join(lines))
        chk = cards.verify_verdict_chain(tmp / "root")
        assert not chk and chk.first_bad_line == 2 and chk.n_rows == 1       # the next row's prev_row_md5 exposes the edit
        _refused(lambda: cards.read_chain(vp, cards.VERDICT_ROW), "chain broken")
        # archive
        d = cards.archive_snapshot(tmp / "root", card, rows)
        assert (d / "rows.jsonl").exists() and (d / "MD5LIST").exists()
        back = cards.verify_archive(tmp / "root", card)
        assert [r["content_hash"] for r in back] == sorted(r["content_hash"] for r in rows)
        assert cards.rederive_snapshot_id(back) == card["data_snapshot_id"]
        _refused(lambda: cards.archive_snapshot(tmp / "root", card, rows[:2]), "re-derive")
        (d / "rows.jsonl").write_text((d / "rows.jsonl").read_text(encoding="utf-8").replace("7001.0", "7001.5"), encoding="utf-8")
        try:
            cards.verify_archive(tmp / "root", card)
            raise AssertionError
        except cards.ArchiveLost:
            pass
        (d / "rows.jsonl").unlink()
        try:
            cards.verify_archive(tmp / "root", card)
            raise AssertionError
        except cards.ArchiveLost as exc:
            assert "integrity" in exc.reasons[0].lower() or "missing" in exc.reasons[0]
        assert cards.card_status(tmp / "root", "MACRO-R06-KR-ETF", store)["verdict"] == "INSUFFICIENT_DATA"
        assert cards.acting_revision(tmp / "root", "MACRO-R06-KR-ETF") is None


test_repro01b_results_md5_stable_volatile_excluded_nan_null_chain_and_archive.test_ids = ["T-REPRO-01b", "T-CARD-01"]


def test_repro01b_bootstrap_outputs_bit_identical_same_seed():
    """The same seed through SeedSequence-spawned PCG64 children gives bit-identical draws (relative diff 0)."""
    from core.ficc.macro_artifacts import child_rngs, rng
    a = [g.standard_normal(1000) for g in child_rngs(11, 4)]
    b = [g.standard_normal(1000) for g in child_rngs(11, 4)]
    assert all(np.array_equal(x, y) for x, y in zip(a, b)) and not np.array_equal(a[0], a[1])
    assert np.array_equal(rng(11).standard_normal(50), rng(11).standard_normal(50))


test_repro01b_bootstrap_outputs_bit_identical_same_seed.test_ids = ["T-REPRO-01b"]


# --------------------------------------------------------------------------- #
# Printed lines (T-BOOK-01 clause, T-BOOK-02, I-15, T-STEP-*, T-CAP-02 stack clause)
# --------------------------------------------------------------------------- #
def _synthetic_prices(n=600, seed=11):
    g = np.random.default_rng(seed)
    r = g.normal(0.0003, 0.012, n)
    closes = 1000.0 * np.cumprod(1.0 + r)
    opens = closes * (1.0 + g.normal(0.0, 0.004, n))
    sig = np.array([np.std(r[max(0, t - 19):t + 1], ddof=1) if t >= 19 else np.nan for t in range(n)]) * math.sqrt(252)
    w = np.where(np.isfinite(sig), np.minimum(1.0, 0.20 / np.where(np.isfinite(sig), sig, 1.0)), np.nan)
    return closes, opens, w, r


def test_book01_printed_lines_of_a_card():
    """T-BOOK-01 printed-line clause: instrument book, notional, rebalance, band, cost with the tick floor, the 2x
    line, execution variants A/B/C, the overnight/intraday attribution, turnover by regime, the stress line;
    never gated; the tick floor only raises."""
    closes, opens, w, _ = _synthetic_prices()
    h = {"instrument_book": "KRX_ETF_line", "notional_nav": KR_SLEEVE, "rebalance": "daily", "no_trade_band": 0.0}
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(closes.size)]
    tags = {d: {"price_limit": 0.30} for d in dates}
    lines = CL.card_lines(h, closes, w, opens=opens, dates=dates, regime_tags=tags, price=69.0, on=date(2026, 6, 1))
    assert lines["instrument_book"] == "KRX_ETF_line" and lines["notional_nav"] == KR_SLEEVE and lines["rebalance"] == "daily"
    c = lines["costs_per_side"]
    assert c["table_bp"] == 3.0 and c["applied_bp"] >= 72.0 and c["source"] == "tick_floor" and c["stress_line"] == {"multiplier": 2.0, "bp": 2.0 * c["applied_bp"]}
    ev = lines["exec_variants"]
    assert all(math.isfinite(ev[k]) for k in "ABC") and ev["B_reason"] is None
    assert lines["exec_variants_2x"]["A"] <= ev["A"] + 1e-12
    assert {"overnight", "intraday", "underlying_overnight_per_year"} <= set(lines["overnight_intraday"])
    assert lines["turnover_by_regime"]["by_regime"]["price_limit=0.3"] > 0 and lines["gated"] is False
    assert lines["stress_cost"]["mean_bp"] >= c["applied_bp"] and lines["stress_cost"]["gated"] is False
    no_opens = CL.exec_variants(closes, w, 3.0)
    assert no_opens["B"] is None and "opens absent" in no_opens["B_reason"]
    plain = CL.card_lines({**h, "instrument_book": "KRX_ETF_line"}, closes, w, price=112060.0, on=date(2026, 6, 1))
    assert plain["costs_per_side"]["applied_bp"] == 3.0 and plain["overnight_intraday"]["reason"].startswith("opens absent")
    # a constant weight path: A, B and C coincide up to the cost of the initial entry (free) and the one-day shift
    const = np.ones(closes.size)
    ev_c = CL.exec_variants(closes, const, 3.0, opens=closes)
    assert abs(ev_c["A"] - ev_c["B"]) < 0.05 and abs(ev_c["A"] - ev_c["C"]) < 0.05


test_book01_printed_lines_of_a_card.test_ids = ["T-BOOK-01", "T-BOOK-02", "T-COST-01"]


def test_book02_kospi_vt20_execution_variants_refdata():
    require_fixture("krx_kospi_official_close_1997-01-03_2026-10-02.csv")
    raise NotRun("REFDATA: KOSPI official closes and opens 1997-2026 (SR 0.448 / 0.450 / 0.465 +- 0.01)")


test_book02_kospi_vt20_execution_variants_refdata.test_ids = ["T-BOOK-02"]


def test_step01_header_mechanics_and_binding_share_of_a_synthetic_ladder():
    """T-STEP-01 header mechanics: the R-31 draft carries the D2 level by {ref} (never a literal), the claim verbatim,
    composition min; binding share = n_bind / n_sessions on a synthetic NAV path through the M5 ladder."""
    store = M.load_store()
    d = cards.draft_header("MACRO-R31-KR-ETF", store)
    assert d["owner_decisions"] == {"risk_layer.drawdown.hard_stop.level": -0.15} and store.raw("cards.R-31_step_down.hard_stop_level") == {"ref": "risk_layer.drawdown.hard_stop.level"}
    assert d["claim"] == "protection in persistent drawdowns; time-boxed; no Sharpe claim" and d["parameters"]["composition"] == "min"
    assert d["parameters"]["steps"] == [{"dd": -0.08, "mult": 0.5}, {"dd": -0.12, "mult": 0.5, "evaluator_block_new_entries": True}]
    assert d["start_band"] is None and d["midpoint_halves"] is None and d["class"] == "CARD-P" and d["comparator"] == "S_same_average_exposure"
    assert "binding_share" in d["printed_lines"] and "persistence_check" in d["printed_lines"]
    nav = [1.0] * 10 + [0.91] * 5 + [1.0] * 45                        # one -9% dip: 0.5x for exactly 21 decisions
    states = RL.ladder_path(nav, rules=store)
    mult = np.array([s.step_mult for s in states])
    assert CL.binding_share(mult) == 21 / 60 and abs(RL.binding_share_of(states) - 21 / 60) < 1e-12
    assert CL.binding_share(np.ones(50)) == 0.0
    try:
        CL.binding_share([1.2, 1.0])
        raise AssertionError
    except ValueError:
        pass
    r = np.random.default_rng(11).normal(0, 0.01, 300)
    pc = CL.persistence_check(r, mult[:300] < 1 if mult.size >= 300 else np.r_[mult < 1, np.zeros(300 - mult.size, bool)])
    assert pc["horizon"] == 21 and pc["gated"] is False and pc["unconditional"] is not None


test_step01_header_mechanics_and_binding_share_of_a_synthetic_ladder.test_ids = ["T-STEP-01", "I-15"]


def test_step04_placement_share_0p10_invariant_step_0p1001_specification_only():
    """T-STEP-04: an exact share <= 0.10 gives INVARIANT_STEP; 0.1001 keeps the steps in the specification book and
    the recommended book carries the hard stop only (ladder term 1.0); the US placement waits for D5."""
    assert RL.ladder_disposition(0.10) == "INVARIANT_STEP" and RL.ladder_disposition(0.1001) == "SPECIFICATION_ONLY"
    assert cards.disposition_for({"family_id": "R-31"}, "NOT_RUN", binding_share=0.10)[0] == "INVARIANT_STEP"
    assert cards.disposition_for({"family_id": "R-31"}, "NOT_RUN", binding_share=0.1001)[0] == "SPECIFICATION_ONLY"
    st = RL.LadderState(1.0, 1.0, 0.5, 10, True, False, None, 0, None)
    assert RL.ladder_for_book(st, "recommended:KR", binding_share=0.1001) == (1.0, False)
    assert RL.ladder_for_book(st, "specification:KR", binding_share=0.1001) == (0.5, True)
    assert RL.ladder_for_book(st, "recommended:KR", binding_share=0.10) == (0.5, True)
    assert M.load_store().get("sleeves.US.line") == "none"


test_step04_placement_share_0p10_invariant_step_0p1001_specification_only.test_ids = ["T-STEP-04", "I-15"]


def test_step02_binding_shares_refdata():
    raise NotRun("REFDATA: QX_EX1_ladder.csv inputs (KOSPI VT20 3 bp 1997-04-15..2026-10-02 ~19%; US VT15 5 bp ~10%)")


test_step02_binding_shares_refdata.test_ids = ["T-STEP-02", "I-15"]


def test_step03_dsr_vs_no_steps_reference_run_pending():
    raise NotRun("REFDATA: section 9.4 item 8 R-31 reference run (separate hwm_hard / ref_step) not frozen; KRX official closes absent")


test_step03_dsr_vs_no_steps_reference_run_pending.test_ids = ["T-STEP-03", "I-15"]


def test_cap02_stack_card_dormant_today_generated_at_two_pass_factors_product_refused():
    """T-CAP-02 stack clause: no de-risk factor is PASS today (None); two synthetic PASS total-basis factors generate
    a stack CARD-P draft (NOT_RUN, comparator S, benchmarks with current_recommended_book); a product composition is
    refused; the low-exposure share and rebound capture print."""
    store = M.load_store()
    pass_card = {"verdict": "PASS", "disposition": "BUILD_AS_INSURANCE"}
    vt = {"rule_id": "R-06-KR-VT20", "exposure_basis": "total", "card": pass_card, "header_commit_utc": "2026-11-01T00:00:00Z"}
    r28 = {"rule_id": "R-28-US-SMA10M", "exposure_basis": "total", "card": pass_card, "header_commit_utc": "2026-12-01T00:00:00Z"}
    not_run = {"rule_id": "R-06-KR-VT20", "exposure_basis": "total", "card": {"verdict": "NOT_RUN", "disposition": "SPECIFICATION_ONLY"}}
    assert cards.maybe_generate_stack_card("KR", [not_run], [], store=store) is None
    assert cards.maybe_generate_stack_card("KR", [vt], [], store=store) is None                      # one factor: no stack
    assert cards.maybe_generate_stack_card("KR", [r28], [{"rule_id": "R-07-caps", "exposure_basis": "total", "card": pass_card}], store=store) is None
    inv = {"rule_id": "R-31-KR-STEP", "exposure_basis": "total", "card": pass_card, "disposition": "INVARIANT_STEP"}
    assert cards.maybe_generate_stack_card("KR", [r28], [inv], store=store) is None
    stack = cards.maybe_generate_stack_card("KR", [r28], [vt], store=store)
    assert stack["card_id"] == "MACRO-STACK-KR" and stack["class"] == "CARD-P" and stack["stack"]["status"] == "NOT_RUN"
    assert stack["parameters"]["factors"] == ["R-06-KR-VT20", "R-28-US-SMA10M"] and stack["comparator"] == "S_same_average_exposure"
    assert "current_recommended_book" in stack["benchmarks"] and "low_exposure_share_le_0p25" in stack["printed_lines"]
    assert stack["notional_nav"] is None and "notional_nav" in cards.owner_nulls(stack)
    _refused(lambda: cards.maybe_generate_stack_card("KR", [{**r28, "composition": "product"}], [vt], store=store), "DNB 31")
    exposure = np.array([1.0, 0.5, 0.25, 0.2, 1.0, 0.1])
    assert abs(CL.low_exposure_share(exposure) - 0.5) < 1e-12
    dates = [date(2020, 3, 20) + timedelta(days=i) for i in range(100)]
    book, bh = np.full(100, 0.001), np.full(100, 0.002)
    rc = CL.rebound_capture(book, bh, dates, store.get("gate.evaluation.cost_episodes"))
    assert rc["rebound_2020"]["book"] < rc["rebound_2020"]["buy_and_hold"] and rc["rebound_2009"]["book"] is None
    assert cards.card_status(None, "MACRO-STACK-KR", store)["verdict"] == "NOT_RUN"


test_cap02_stack_card_dormant_today_generated_at_two_pass_factors_product_refused.test_ids = ["T-CAP-02"]


# --------------------------------------------------------------------------- #
# R-03 / R-04 / R-14
# --------------------------------------------------------------------------- #
def test_r03_01_revisions_committed_before_their_runs_lowest_passing_acts():
    """r1-r3 drafts differ in rule and parameters; each revision's md5 exists before its run (synthetic frozen store);
    acting_revision is the lowest PASSing one; the formal numbers are REFDATA."""
    store = M.load_store()
    d1, d2, d3 = (cards.draft_header("MACRO-R03-US-MOM", store, revision=r) for r in (1, 2, 3))
    assert d1["class"] == "CARD-O" and d1["comparator"] == "overlay_off" and d1["instrument_book"] == "US_shares_KIS"
    assert d2["parameters"]["target"] == "expanding_median_sigma126" and d2["parameters"]["min_obs"] == 252 and d3["parameters"]["vs"] == "min(1, (0.12/sigma126)^2)"
    assert len({cards.draft_md5(x) for x in (d1, d2, d3)}) == 3 and d1["nav_fx"]["role"] == "acting_exposure"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        fstore, _ = _store(tmp, frozen=True)
        led = StubLedger()
        hs = []
        for r in (1, 2, 3):
            hs.append(_commit(tmp, fstore, "MACRO-R03-US-MOM", r, ledger=led))
            led.rows["R-03"] += 1                                                     # the revision's run appends its row
        assert [h["N_raw_at_registration"] for h in hs] == [26, 27, 28] and len({h["header_md5"] for h in hs}) == 3
        for h, verdict in zip(hs, ("REVISE", "PASS", "PASS")):
            res = _results(verdict=verdict, verdict_reason=None if verdict == "PASS" else "PC6", disposition="RECOMMENDATION" if verdict == "PASS" else "DESCRIPTIVE",
                           first_failed_check=None if verdict == "PASS" else "PC6", permitted_fix=None if verdict == "PASS" else "widen_grid",
                           config_hash=fstore.config_hash, git_hash="UNVERSIONED")
            cards.write_card(tmp / "root", h, res, CLOCK, store=fstore)
        assert cards.acting_revision(tmp / "root", "MACRO-R03-US-MOM") == 2
        st = cards.card_status(tmp / "root", "MACRO-R03-US-MOM", fstore)
        assert st["verdict"] == "PASS" and st["displayed_as"] == "recommendation"
    raise NotRun("REFDATA: French Mom daily 1990-01-02..2026-08-31 and QX_EX1_qf3_trial_corr_diff.csv (dSR +0.273, deflated 0.98 / 0.947)")


test_r03_01_revisions_committed_before_their_runs_lowest_passing_acts.test_ids = ["T-R03-01"]


def test_r04_01_record_and_pooled_route_closed():
    """R-04 is a record (NOT_RUN, SPECIFICATION_ONLY, 'step 3 FAIL (indicative)'), not a step-4 header; validation
    refuses an A-provisional or pooled tier for a card already run; the step-3 number is REFDATA."""
    store = M.load_store()
    st = cards.card_status(None, "MACRO-R04-US-DM", store)
    assert st == {"card_id": "MACRO-R04-US-DM", "class": "CARD-O", "verdict": "NOT_RUN", "disposition": "SPECIFICATION_ONLY",
                  "displayed_as": "descriptive", "label": "step 3 FAIL (indicative)", "results_md5": None}
    assert store.get("families.momentum.dm_gate.label") == "step 3 FAIL" and store.get("families.momentum.dm_gate.books") == ["specification"]
    assert store.get("gate.tiers.A_provisional") == "closed" and store.get("families.momentum.dm_gate.a_provisional_route") == "closed"
    _refused(lambda: cards.draft_header("MACRO-R04-US-DM", store), "not a step-4 header")
    base = cards.rule_object("MACRO-R04-US-DM")
    for tier in ("A_provisional", "pooled"):
        r = M.validate_rule_object(M.RuleObject(**{**vars(base), "tier": tier, "results_md5": "a" * 32}))
        assert any("[pooled_or_a_provisional_tier_after_results]" in i.message for i in r.errors), tier
    assert M.validate_rule_object(base).ok
    raise NotRun("REFDATA: QF3 26-trial ledger series (deflated add-on 0.77 +- 0.02 at N_equiv 6.3)")


test_r04_01_record_and_pooled_route_closed.test_ids = ["T-R04-01"]


def test_r14_01_header_needs_multi_line_lines_and_the_diversification_claim():
    """T-R14-01: the draft declares multi_line + CARD-O diversification and the failure-mode text; without the lines
    or with another claim it is refused; vt / overlays never apply to ts_trend; goldens REFDATA."""
    store = M.load_store()
    d = cards.draft_header("MACRO-R14-MULTI-TREND", store)
    assert d["instrument_book"] == "multi_line" and d["class"] == "CARD-O" and d["claim_type"] == "diversification"
    assert any("not fast-crash protection" in x for x in d["printed_lines"]) and d["parameters"]["overlay_exempt"] is True
    assert "instrument_lines" in cards.owner_nulls(d)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        fstore, _ = _store(tmp, frozen=True)
        f = _fill(cards.draft_header("MACRO-R14-MULTI-TREND", fstore))
        f["instrument_lines"] = [{"market": "US", "instrument_book": "CME_micro_ES"}, {"market": "JP", "instrument_book": "KRX_listed_SP500_ETF"}]
        f["notional_nav"], f["nav_fx"] = US_SLEEVE, {"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE", "conversion_instant": "15:30 KST", "role": "acting_exposure"}
        f["roll_calendar"] = {"rule": "fixed", "calendar": ["2026-12-18"]}
        commit = lambda x: cards.commit_header(x, fstore, StubLedger(), CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl")   # noqa: E731
        _refused(lambda: commit({**f, "instrument_lines": None}), "instrument_lines")
        _refused(lambda: commit({**f, "instrument_lines": [{"market": "US", "instrument_book": "US_shares_KIS"}]}), "stock book")
        _refused(lambda: commit({**f, "claim_type": "outperformance", "class": "CARD-P"}), "claim")
        _refused(lambda: commit({**f, "instrument_book": "KRX_stock_book", "instrument_lines": None}), "notional_nav")
    r = M.validate_rule_object(M.RuleObject(**{**vars(cards.rule_object("MACRO-R06-KR-ETF")), "applies_to": "ts_trend"}))
    assert not r.ok
    raise NotRun("REFDATA: the 12 index series 2001-26 (SR 0.449; corr 0.03 / 0.34-0.36); COUNCIL: the index list (F-10)")


test_r14_01_header_needs_multi_line_lines_and_the_diversification_claim.test_ids = ["T-R14-01", "T-BASIS-01"]


# --------------------------------------------------------------------------- #
# Freeze (gate_package) and the study runner
# --------------------------------------------------------------------------- #
def test_freeze_refuses_with_exactly_the_three_reasons_here():
    """On temp copies of the shipped store and log: the freeze refuses with the three reasons (acceptance test not
    passed, anchor UNVERSIONED, reference fixtures absent); the store, the log and the macro dir are untouched;
    gate/acceptance_runs.jsonl stays absent; the manifest lists the harness sources and the absent fixtures."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, sp = _store(tmp, frozen=False, signed=False)
        before = sp.read_bytes()
        macro = tmp / "macro"
        try:
            GP.freeze(sp, tmp / "gov.jsonl", "UNVERSIONED", CLOCK, macro_dir=macro)
            raise AssertionError("froze")
        except GP.FreezeRefused as exc:
            assert len(exc.reasons) == 3, exc.reasons
            assert exc.reasons[0].startswith(GP.REASON_ACCEPTANCE) and exc.reasons[1] == GP.REASON_ANCHOR and exc.reasons[2].startswith(GP.REASON_FIXTURES)
            assert "krx_kospi_official_close_1997-01-03_2026-10-02.csv" in exc.reasons[2]
        assert sp.read_bytes() == before and not (tmp / "gov.jsonl").exists() and not macro.exists()
        assert not GP.attempts_path(macro).exists() and GP.attempts(macro) == []
        assert GP.package_state(store, macro) == "NOT_FROZEN" and M.load_store().get("gate.package.status") == "NOT_FROZEN"
        try:
            GP.verify_package(store, macro_dir=macro)
            raise AssertionError
        except cards.PackageNotFrozen:
            pass
        md5, manifest = GP.definitions_md5(store)
        assert set(manifest["harness_sources"]) == set(GP.HARNESS_SOURCES) and "package" not in manifest["gate_blocks"]
        assert manifest["seeds"]["seed_study"] == 11 and manifest["seeds"]["placebo"] == 11 and manifest["data_cutoff"] == {"KR": "2026-10-02", "US": "2026-10-01"}
        for f in GP.REFERENCE_FIXTURES:
            present = (GP.FIXTURE_DIR / f).is_file()
            assert (f"fixture:{f}" in manifest["absent"]) == (not present) and (manifest["fixtures"][f] is None) == (not present), f
        assert "fixture:krx_kospi_official_close_1997-01-03_2026-10-02.csv" in manifest["absent"]
        assert manifest["council_answers"] == {q: None for q in GP.COUNCIL_QUESTIONS} and manifest["d6_rule"] == "lowest_placebo_false_pass_rule"
        assert md5 == GP.definitions_md5(store)[0] and len(md5) == 32
    assert not (ROOT / "docs" / "macro_overlay" / "cards" / "verdicts.jsonl").exists()
    assert not list((ROOT / "docs" / "macro_overlay" / "headers").glob("*.header.json"))


test_freeze_refuses_with_exactly_the_three_reasons_here.test_ids = ["I-08", "T-GATE-01", "T-CARD-02", "I-07"]


def test_freeze_success_path_and_mismatch_detection_on_a_synthetic_package():
    """T-CARD-02: with synthetic fixtures, a passing attempt row + report and a versioned anchor, the freeze writes
    gate.package and a package_freeze event; afterwards an edit to a gate.* block, a harness source, a fixture, a seed
    or the report is detected by verify_package; a change after a result is a new 2.x version."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, sp = _store(tmp, frozen=False)
        macro, fx, src = tmp / "macro", tmp / "fixtures", tmp / "src"
        fx.mkdir()
        for f in GP.REFERENCE_FIXTURES:
            (fx / f).write_text(f"synthetic {f}\n", encoding="utf-8")
        sources = ("a.py", "b.py")
        src.mkdir()
        for s in sources:
            (src / s).write_bytes(b"x = 1\r\n")
        cards.chain_append(GP.attempts_path(macro), {"attempt_no": 1, "package_version": "2.0.0", "outcome": "pass", "utc": "2026-10-06T00:00:00Z"})
        GP.report_path(macro).write_text(json.dumps({"attempt_no": 1, "outcome": "pass"}), encoding="utf-8")
        res = GP.freeze(sp, tmp / "gov.jsonl", ANCHOR, CLOCK, macro_dir=macro, root=src, fixture_dir=fx, sources=sources,
                        ledger_hashes={"R-06": "f" * 32}, council_answers={"Q5_per_card_placebo_excess": "stands as written for 2.0.0"})
        frozen = M.load_store(sp)
        pkg = frozen.get("gate.package")
        assert pkg["status"] == "FROZEN" and pkg["definitions_md5"] == res.definitions_md5 and pkg["frozen_utc"] == "2026-10-06T12:00:00Z"
        assert pkg["acceptance_report_md5"] == hashlib.md5(GP.report_path(macro).read_bytes()).hexdigest() and pkg["anchor_commit"] == ANCHOR
        assert GP.package_state(frozen, macro) == "FROZEN" and res.manifest_path.exists()
        ev = G.read_events(tmp / "gov.jsonl")
        assert len(ev) == 1 and ev[0]["kind"] == "package_freeze" and ev[0]["new"]["definitions_md5"] == res.definitions_md5
        assert frozen.config_hash == store.config_hash                                   # gate.package is outside config_hash
        kw = dict(root=src, fixture_dir=fx, sources=sources, ledger_hashes={"R-06": "f" * 32}, council_answers={"Q5_per_card_placebo_excess": "stands as written for 2.0.0"})
        assert GP.verify_package(frozen, macro_dir=macro, **kw)["absent"] == []
        assert GP.version_for_change(frozen, results_seen=True, **kw) is None
        # CRLF -> LF normalisation never changes the hash; a code edit does
        (src / "a.py").write_bytes(b"x = 1\n")
        GP.verify_package(frozen, macro_dir=macro, **kw)
        (src / "a.py").write_bytes(b"x = 2\n")
        _refused(lambda: GP.verify_package(frozen, macro_dir=macro, **kw), "definitions_md5")
        assert GP.version_for_change(frozen, results_seen=True, **kw) == "2.1.0" and GP.version_for_change(frozen, results_seen=False, **kw) == "2.0.0"
        (src / "a.py").write_bytes(b"x = 1\n")
        (fx / GP.REFERENCE_FIXTURES[0]).write_text("changed\n", encoding="utf-8")
        _refused(lambda: GP.verify_package(frozen, macro_dir=macro, **kw), "definitions_md5")
        (fx / GP.REFERENCE_FIXTURES[0]).write_text(f"synthetic {GP.REFERENCE_FIXTURES[0]}\n", encoding="utf-8")
        _refused(lambda: GP.verify_package(frozen, macro_dir=macro, ledger_hashes={"R-06": "0" * 32}, **{k: v for k, v in kw.items() if k != "ledger_hashes"}), "definitions_md5")
        edited = M.MacroStore({**frozen.doc, "gate": {**frozen.doc["gate"], "step3": {**frozen.doc["gate"]["step3"], "card_o_bar": 0.9}}})
        _refused(lambda: GP.verify_package(edited, macro_dir=macro, **kw), "definitions_md5")
        seeded = M.MacroStore({**frozen.doc, "reproducibility": {**frozen.doc["reproducibility"], "seed_study": 12}})
        _refused(lambda: GP.verify_package(seeded, macro_dir=macro, **kw), "definitions_md5")
        GP.report_path(macro).write_text(json.dumps({"attempt_no": 1, "outcome": "pass", "x": 1}), encoding="utf-8")
        _refused(lambda: GP.verify_package(frozen, macro_dir=macro, **kw), "acceptance_report_md5")
        try:
            GP.freeze(sp, tmp / "gov.jsonl", ANCHOR, CLOCK, macro_dir=macro, root=src, fixture_dir=fx, sources=sources)
            raise AssertionError
        except GP.FreezeRefused as exc:
            assert "already FROZEN" in exc.reasons[0]
        assert GP.new_package_version("2.0.0") == "2.1.0" and GP.new_package_version("2.3.0") == "2.4.0"
        # a failed attempt log: two failures across 2.x block everything
        cards.chain_append(GP.attempts_path(macro), {"attempt_no": 2, "package_version": "2.1.0", "outcome": "fail"})
        cards.chain_append(GP.attempts_path(macro), {"attempt_no": 3, "package_version": "2.2.0", "outcome": "fail"})
        assert GP.package_state(frozen, macro) == "BLOCKED" and GP.acceptance_passed(macro)[0] is False


test_freeze_success_path_and_mismatch_detection_on_a_synthetic_package.test_ids = ["T-CARD-02", "T-GATE-04"]


def test_study_runner_dry_listing_offline_and_formal_runs_refused():
    """I-07 / I-16 refusal paths: the listing works offline on a temp macro dir; every formal card is refused with each
    reason printed; no card file, no verdicts row, no archive, no error card; --commit-headers refused; the legacy
    card directory and the shipped store are untouched; the formal values are REFDATA."""
    import docs.macro_overlay_study as study
    store = M.load_store()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        root, macro = tmp / "root", tmp / "macro"
        info = study.listing(store, root=root, macro_dir=macro, anchor=None)
        assert info["package"]["state"] == "NOT_FROZEN" and info["anchor"] == "UNVERSIONED"
        assert [c["card_id"] for c in info["cards"]] == [s.card_id for s in cards.REGISTRY]
        assert all(c["verdict"] == "NOT_RUN" for c in info["cards"] if c["card_id"] != "MACRO-R06-US")
        assert info["registered_reject"]["rerun"] is False and len(info["pending_values"]) == 17
        reasons = info["preflight"]
        assert any("NOT_FROZEN" in r for r in reasons) and any("owner must place the repository under git" in r for r in reasons)
        for cid, rev in (("MACRO-R06-KR-ETF", 2), ("MACRO-R03-US-MOM", 1), ("MACRO-R31-KR-ETF", 1), ("MACRO-R28-US-TREND", 1), ("MACRO-R06-US-FUT", 1)):
            got = _refused(lambda: study.run_card(cid, rev, store=store, root=root, macro_dir=macro, anchor="UNVERSIONED",
                                                  knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK), "NOT_FROZEN")
            assert got == reasons
        _refused(lambda: study.run_card("MACRO-R06-KR-ETF", 2, store=store, root=root, macro_dir=macro, anchor=ANCHOR,
                                        knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK, mode="v12check"), "never a card record")
        _refused(lambda: study.run_card("MACRO-BOGUS", 1, store=store, root=root, macro_dir=macro, anchor=ANCHOR,
                                        knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK), "not a registered")
        assert not root.exists() and not macro.exists()
        # the CLI, in-process, on the temp dirs (listing exit 0; refused run / commit exit 2; no quick mode)
        argv = ["--root", str(root), "--macro-dir", str(macro)]
        assert study.main(argv) == 0
        assert study.main(argv + ["--run", "--only", "MACRO-R06-KR-ETF.r2", "--knowledge-utc", "2026-10-02T07:00:00Z"]) == 2
        assert study.main(argv + ["--run", "--only", "MACRO-R06-KR-ETF.r2"]) == 2
        assert study.main(argv + ["--commit-headers"]) == 2
        try:
            study.main(argv + ["--quick"])
            raise AssertionError("--quick accepted")
        except SystemExit as exc:
            assert exc.code == 2
        assert not root.exists() and not macro.exists()
        # a frozen synthetic store with a committed header still refuses on the anchor and the manifest, writing nothing
        fstore, _ = _store(tmp, frozen=True)
        _commit(tmp, fstore, "MACRO-R06-KR-ETF")
        got = _refused(lambda: study.run_card("MACRO-R06-KR-ETF", 2, store=fstore, root=tmp / "root", macro_dir=macro, anchor=ANCHOR,
                                              knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK), "package manifest")
        assert not any("NOT_FROZEN" in r for r in got)
        assert not (tmp / "root" / "cards").exists() and not macro.exists()
    assert M.load_store().get("gate.package.status") == "NOT_FROZEN"
    raise NotRun("REFDATA: KRX official closes 1997-2026 (F01), BOK_CALL_RATE (F02), French files, QX_* tables; OWNER: notional, git anchor "
                 "(I-07 card lines, I-09 episode counts, I-16 formal verdict / header md5 / results md5)")


test_study_runner_dry_listing_offline_and_formal_runs_refused.test_ids = ["I-07", "I-09", "I-16", "T-R06-US-01"]


def test_i16_r06_kr_verdict_conditions_recorded_and_formal_run_refdata():
    """I-16: the four Resolution-1 conditions are data on the registry and the draft (gating lines, 32-start band with
    the integer floor, midpoint halves); the formal verdict is never computed here (R2-C1: never rescued)."""
    spec = cards.BY_ID["MACRO-R06-KR-ETF"]
    assert [c[:4] for c in spec.conditions[:4]] == ["(i) ", "(ii)", "(iii", "(iv)"]
    d = cards.draft_header("MACRO-R06-KR-ETF", M.load_store())
    assert d["gating_lines"]["full_span"] == "v2_PASS" and d["gating_lines"]["etf_era"]["to"] == "2025-12-31" and d["primary_oos_line"] == "etf_era"
    assert d["start_band"] == {"shape": "R-06_KR", "from": "1997-05", "to": "1999-12", "step": "month", "starts": 32, "require": {"no_reject": True, "pass_share_min": "2/3"}}
    assert 3 * 22 >= 2 * 32 > 3 * 21                                            # >= 22 of 32 as integers
    assert d["midpoint_halves"] == {"split": "calendar_midpoint", "split_date": "2012-01-01", "require": "no_reject"}
    assert d["outcomes"] == {"PASS": "BUILD-AS-INSURANCE", "INSUFFICIENT_DATA": "specification_book_control_regated_on_new_objective_episode", "REJECT": "archive"}
    assert d["searched_parameters"] == [] and d["estimator"] == "sma20" and d["parameters"]["cap"] == 1.0 and d["revision"] == 2
    raise NotRun("REFDATA: KRX official KOSPI closes from 1997-01-03 (F01), ECOS BOK_CALL_RATE (F02); OWNER: KODEX 200 listing date, "
                 "sleeves.KR.notional_nav, git anchor; package NOT_FROZEN -- the formal R-06 KR verdict is computed blind, never here")


test_i16_r06_kr_verdict_conditions_recorded_and_formal_run_refdata.test_ids = ["I-16"]


def test_zz_legacy_cards_and_shipped_store_untouched():
    """docs/asset_expansion/cards and the shipped store are byte-identical before and after this module; no v2 file
    reached them; the real card root holds drafts and READMEs only."""
    assert _md5_tree(LEGACY_CARDS) == _LEGACY_BEFORE and len(_LEGACY_BEFORE) == 34
    assert not [p for p in LEGACY_CARDS.glob("MACRO-*")]
    names = sorted(p.name for p in (ROOT / "docs" / "macro_overlay").rglob("*") if p.is_file())
    assert all(n.endswith(".draft.json") or n == "README.md" for n in names), names
    assert M.load_store().get("gate.package.definitions_md5") == "written_at_freeze"


test_zz_legacy_cards_and_shipped_store_untouched.test_ids = ["T-HERM-02", "I-07"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
