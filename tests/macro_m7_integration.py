"""Sprint 5 (M7) integration seams: the formal evaluation chain of docs/macro_overlay_study.py on a synthetic card
(R-24 -> R-23 -> R-34 -> R-22 -> R-21 -> cards), the header commit on a real R-23 family ledger under the package
state, the freeze manifest over the harness sources that exist, the runner's refusals with their reasons, one home
for PSR / the UNDERPOWERED rule / BY q and Holm, the rulings scan of the M7 modules, and the NOT_RUN carriers of
the post-freeze goldens (G-KR-L*, G-US-F*, G-PWR-*, G-DSR-02, G-LAD-04, T-GATE-02, T-EST-03). Hermetic: temporary
copies of the store, the governance log, the card root, the macro dir and the ledgers; synthetic panels only.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import math
import tempfile
from datetime import date
from pathlib import Path

import numpy as np

from core.ficc import macro_schema as S
from core.quant import cardp as CP
from core.quant import cards
from core.quant import forecast_eval as F
from core.quant import gate_ledger as GL
from core.quant import gate_package as GP
from core.quant import gate_stats as GS
from core.quant.instruments import cost_per_side
from core.rules import macro_rules as M
from tests.golden_tools import load_goldens
from tests.macro_m7_cardp import _control, regime_returns, shift, vt_decided
from tests.macro_m7_cards import ANCHOR, CLOCK, _fill, _refused, _store
from tests.macro_m7_ledger import ANCHOR as ROW_ANCHOR
from tests.macro_m7_ledger import _row
from tests.notrun import NotRun, load_manifest

ROOT = Path(__file__).resolve().parents[1]
SEED, B = 11, 20
M7_MODULES = ("core/quant/gate_stats.py", "core/quant/gate_ledger.py", "core/quant/cardp.py", "core/quant/cards.py",
              "core/quant/gate_package.py", "core/quant/card_lines.py", "docs/macro_overlay_study.py")
STAT_MODULES = ("core/quant/gate_stats.py", "core/quant/gate_ledger.py", "core/quant/cardp.py", "core/quant/card_lines.py")
# ACQUISITION.csv ids -> file names of the reference fixtures the post-freeze goldens read
FIXTURE_FILES = {"F01": "krx_kospi_official_close_1997-01-03_2026-10-02.csv", "F02": "ecos_bok_call_rate_1997_2026-10.csv",
                 "F10": "french_daily_mom_1990-01-02_2026-08-31.csv", "F13": "yahoo_KS11_1996-12_2026-10-02.csv",
                 "F14": "yahoo_GSPC_1990_2026-10-01.csv", "F21": "QX_DLA_korea_grid.csv", "F22": "QX_EX1_qf3_trial_corr_diff.csv",
                 "F23": "QX_DLB_power_se.csv / QX_DLB_power_sim.csv / QX_DLB_r03_dsr.csv", "U1": "french_daily_5f_2x3.csv + yahoo_GSPC_1990_2026-10-01.csv"}


def _study():
    import docs.macro_overlay_study as study
    return study


# --------------------------------------------------------------------------- #
# Synthetic inputs of a formal R-06 KR card on its declared span (1997-04-01 .. 2026-10-02)
# --------------------------------------------------------------------------- #
def _sessions(start=date(1997, 4, 1), end=date(2026, 10, 2)) -> list[date]:
    d = np.arange(np.datetime64(start, "D"), np.datetime64(end, "D") + 1, dtype="datetime64[D]")
    return [x.astype(date) for x in d[np.is_busday(d)]]


def _inputs(tmp: Path, ledger: GL.FamilyLedger, *, seed: int = SEED) -> tuple:
    """(CardInputs, series) on a seeded regime path over the R-06 KR span: honest books at 3 bp, a vt(20, 0.20)
    overlay, official-close episodes, the synthetic look-ahead control, 8 Moore neighbours, 3 archive rows."""
    study = _study()
    dates = _sessions()
    r = regime_returns(seed=seed, n_cycles=17)[: len(dates)]
    assert r.size == len(dates)
    quote = cost_per_side("KRX_ETF_line", price=40000.0, on=date(2026, 10, 2))
    decided = vt_decided(r)
    data_fn = lambda L: CP.build_books(shift(decided, L), r, quote.bp, dates)      # noqa: E731
    closes = 100.0 * np.cumprod(1.0 + r)
    neighbours, configs = [], [data_fn(1).on]
    for wm in (0.5, 1, 2):
        for tm in (0.75, 1, 1.25):
            if wm == 1 and tm == 1:
                continue
            b = CP.build_books(shift(vt_decided(r, 0.20 * tm, int(20 * wm)), 1), r, quote.bp, dates)
            legs = CP.pc1_prime(b.on, b.S, f=1.0, B=B, seed=seed)
            neighbours.append({"dES_21": legs[0]["dES"], "dES_126": legs[1]["dES"], "dSR": GS.delta_sr(b.on, b.S)})
            configs.append(b.on)
    rows = [{"series_id": "KOSPI_OFFICIAL_CLOSE", "obs_date": f"2026-09-{d:02d}", "value": 7000.0 + d,
             "content_hash": hashlib.md5(str(d).encode()).hexdigest()} for d in (3, 1, 2)]
    # two research-phase rows of the family, anchored and run before the commit, with their difference series
    rng = np.random.default_rng(seed)
    common = rng.standard_normal(3000)
    series = {}
    for k, ref in enumerate(("research_a", "research_b")):
        res = GL.register_trial(ledger, _row(params={"estimator": "sma", "window": 20 + 40 * k, "target": 0.20}, window=20 + 40 * k,
                                             run_utc=f"2026-09-0{k + 1}T00:00:00Z", diff_series_ref=ref, delta_sr=0.05 + 0.01 * k))
        series[res.row["config_id"]] = math.sqrt(0.6) * common + math.sqrt(0.4) * rng.standard_normal(3000)
    inputs = study.CardInputs(books=data_fn(1), data_fn=data_fn, closes=closes, close_dates=dates, control=_control(),
                              snapshot_rows=rows, costs={"table_bp": quote.table_bp, "floor_bp": quote.floor_bp, "applied_bp": quote.bp},
                              series=series, neighbours=neighbours, cells=4, pvalues=[0.02, 0.3, 0.07], configs=np.column_stack(configs))
    return inputs, series


def _committed(tmp: Path, store, ledger: GL.FamilyLedger, root: Path) -> dict:
    d = _fill(cards.draft_header("MACRO-R06-KR-ETF", store, revision=2))
    return cards.commit_header(d, store, {"R-06": ledger}, CLOCK, ANCHOR, root=root, governance_log=tmp / "gov.jsonl", macro_dir=tmp / "macro")


# --------------------------------------------------------------------------- #
# I-07 (synthetic): the formal evaluation chain writes one card, its verdict row and its archive
# --------------------------------------------------------------------------- #
def test_i07_formal_evaluation_chain_on_a_synthetic_card():
    """evaluate_card runs the frozen harness in its order on a synthetic frozen store: R-24 SE ladder / power line /
    LW-HAC SE -> R-23 step3 (f = N_eff of the two anchored research rows) -> R-34 timing profile (three ledger rows)
    -> R-22 episodes, the 32-start band, the midpoint halves, the four KR regime lines -> R-21 cardp_evaluate per line
    -> combine_card_verdict -> cards.write_card / append_verdict / archive_snapshot. The card validates, re-hashes,
    cites the ledger hash after the run, carries every power field and the lw_studentized PC-3, and a second run
    with the same seed is bit-identical (T-REPRO-01b)."""
    study = _study()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=True)
        lg = GL.family_ledger("R-06", tmp / "ledgers")
        inputs, series = _inputs(tmp, lg)
        root = tmp / "root"
        h = _committed(tmp, store, lg, root)
        assert h["ledger_hash_at_registration"] == lg.hash() and h["N_raw_at_registration"] == 2
        card = study.evaluate_card(h, inputs, store=store, root=root, ledger=lg, anchor=ANCHOR, clock=CLOCK,
                                   knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B)
        path = root / "cards" / "MACRO-R06-KR-ETF.r2.json"
        assert path.exists() and card["verdict"] in CP.VERDICTS and card["results_md5"] == S.results_md5(card)
        assert card["header_md5"] == h["header_md5"] and card["read_only"] is True and card["lag_audit_violations"] == 0
        assert not S.card_issues(card, committed_header=h, seed_study=11)
        # R-24: the power block is gate_stats.power_line over se_ladder; PC-3 is the studentized bootstrap
        for k in GS.POWER_FIELDS:
            assert k in card["power"], k
        assert abs(card["power"]["mde80"] - GS.MDE_FACTOR * card["power"]["se_plateau"]) < 1e-12
        pc3 = card["tests"]["PC3"]
        assert pc3["block_PW"] >= GS.BLOCK_FLOOR and pc3["p_lw"] > 0 and pc3["p_hac"] is not None and pc3["n_blocks"] > 0
        assert "p_form" not in pc3 and "se_hac_nw10" not in card["printed"]        # harness diagnostics beyond the closed schema are not card fields
        assert card["printed"]["lo_sr_20"]["lags"] == 20 and card["printed"]["hl_haircut"]["M"] == 2
        # R-23: f from step3 (the two rows ran before the commit and overlap the span) feeds the verdicts at f and at 1
        s3 = GL.step3({**h, "market": "KR", "data_span": {"start": inputs.books.dates[0].isoformat(), "end": "2026-10-02"}}, lg, SEED,
                      delta_sr=GS.delta_sr(inputs.books.on, inputs.books.S), se_obs=GS.lw_hac_se(inputs.books.on, inputs.books.S).se,
                      series=series, commit=GL.Anchor(h["created_utc"], f"git:{ANCHOR}"), cells=4, pvalues=inputs.pvalues)
        assert card["selection_factor"]["value"] == s3["f"] > 1.0 and card["selection_factor"]["rule"] == "computed_by_step3"
        assert card["N_raw"] == 2 and card["N_eff"] == s3["n_eff"] and card["tests"]["step3"]["by_q"] == s3["printed"]["by_q"]
        assert s3["printed"]["holm"] == [float(x) for x in GS.holm_adjusted(inputs.pvalues)]
        assert card["tests"]["step3"]["selection_factor"] == card["selection_factor"] and card["tests"]["step3"]["pass"] is None
        assert card["verdict_at_f1"] in CP.VERDICTS and card["verdict_at_f_neff"] in CP.VERDICTS
        # R-24 rule 6 (step 4): the grid's 9 configurations (< 10): PBO not run, stated on the card, never imputed
        assert card["tests"]["step4"] == {"pbo": None, "winner_loses_share": None, "pbo_null": None, "slope": None, "n_configs": 9}
        # R-34: every honest lag is a family-ledger row; the ledger hash after the run is the card's
        assert lg.n_raw == 5 and card["ledger_hash_at_run"] == lg.hash() != h["ledger_hash_at_registration"]
        lags = {r["params"]["lag"] for r in lg.rows() if r.get("run_kind") == "timing_lag"}
        assert lags == {1, 2, 3} and all(r["timing_class"] == "COMPLIANT" for r in lg.rows() if r.get("run_kind") == "timing_lag")
        assert [x["L"] for x in card["timing_profile"]["lags"]] == [1, 2, 3] and card["timing_profile"]["label"] in ("robust", "timing_fragile")
        assert card["timing_profile"]["LP"] == inputs.control["LP"] >= CP.LP_MIN
        # R-22: the band, the halves and the regime lines; the verdict is the worst of the gating parts (I-16 (i)-(iv))
        band = card["start_band_results"]
        assert band["n_starts"] == 32 and len(band["verdicts"]) == 32 and band["starts"][0] == "1997-05-01"
        assert set(card["midpoint_halves_results"]) == {"h1", "h2"}
        lines = {x["line"]: x for x in card["regime_line_results"]}
        assert set(lines) == {"pre_etf", "etf_era", "limits_30pct", "pre_design", "etf_era_to_present"} and lines["etf_era"]["gated"] and not lines["pre_design"]["gated"]
        # Resolution 1 (ii): the gated ETF-era line is the header's gating_lines span; the line to the present is printed only
        assert lines["etf_era"]["span"] == "2002-11..2025-12" and not lines["etf_era_to_present"]["gated"]
        worst = min([lines["etf_era"]["verdict"]] + (["INSUFFICIENT_DATA"] if not band["floor_pass"] else []), key=lambda v: CP.ORDER[v])
        assert CP.ORDER[card["verdict"]] <= CP.ORDER[worst]
        if card["verdict"] == "PASS":
            assert band["floor_pass"] and "REJECT" not in card["midpoint_halves_results"].values()
        assert len(card["episodes"]) == len(card["printed"]["post_trough"]) and all("peak" in e and "open" in e for e in card["episodes"])
        assert card["costs_per_side"] == {"table_bp": 3.0, "floor_bp": inputs.costs["floor_bp"], "applied_bp": 3.0, "stress_line": None, "roll_cost_line": None}
        assert card["cost_stress"] == 2.0 and card["gjr_null_pct"] is None
        assert not cards.check_display_invariant(card["verdict"], card["disposition"], cards.disposition_for(card, card["verdict"])[1])
        # the verdict row and the archive
        rows = cards.read_chain(cards.verdicts_path(root), cards.VERDICT_ROW)
        assert len(rows) == 1 and rows[0]["results_md5"] == card["results_md5"] and cards.verify_verdict_chain(root)
        assert len(cards.verify_archive(root, card)) == 3
        # T-REPRO-01b: the same seed and B reproduce the results bit for bit (the ledger rows are the same trials)
        card2 = study.evaluate_card(h, inputs, store=store, root=tmp / "root2", ledger=lg, anchor=ANCHOR, clock=CLOCK,
                                    knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B)
        assert card2["results_md5"] == card["results_md5"] and lg.n_raw == 5
        # fail closed: books that do not end at the header's span end, or probe books, write nothing
        short = CP.Books(inputs.books.on[:-1], inputs.books.off[:-1], inputs.books.S[:-1], inputs.books.m[:-1], inputs.books.dates[:-1], inputs.books.on_2x[:-1])
        _refused(lambda: study.evaluate_card(h, study.CardInputs(**{**vars(inputs), "books": short}), store=store, root=tmp / "root3", ledger=lg,
                                             anchor=ANCHOR, clock=CLOCK, knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B), "data_span")
        assert not (tmp / "root3").exists()
        # a CARD-O header (no nine-step evaluator) and absent step-4 configurations are refused before any ledger row
        n0 = lg.n_raw
        _refused(lambda: study.evaluate_card({**h, "class": "CARD-O"}, inputs, store=store, root=tmp / "root4", ledger=lg, anchor=ANCHOR,
                                             clock=CLOCK, knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B), "CARD-O")
        _refused(lambda: study.evaluate_card(h, study.CardInputs(**{**vars(inputs), "configs": None}), store=store, root=tmp / "root4", ledger=lg,
                                             anchor=ANCHOR, clock=CLOCK, knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B), "step 4")
        _refused(lambda: study.evaluate_card(h, study.CardInputs(**{**vars(inputs), "neighbours": None}), store=store, root=tmp / "root4", ledger=lg,
                                             anchor=ANCHOR, clock=CLOCK, knowledge_utc="2026-10-02T07:00:00Z", seed=SEED, B=B), "pc6_axes")
        assert lg.n_raw == n0 and not (tmp / "root4").exists()
    assert not (ROOT / "docs" / "macro_overlay" / "cards" / "verdicts.jsonl").exists()


test_i07_formal_evaluation_chain_on_a_synthetic_card.test_ids = ["I-07", "I-16", "T-BOOK-01", "T-COST-01", "T-REPRO-01b", "T-CARD-01", "T-LEDGER-01"]


# --------------------------------------------------------------------------- #
# Header commit on the real R-23 ledger under the package state
# --------------------------------------------------------------------------- #
def test_commit_header_reads_the_family_ledger_and_the_package_state():
    """commit_header takes `ledgers_of(macro_dir)` (one FamilyLedger per family): the header carries the family hash and
    N_raw; validate_card_header (R-26 header_checks) still runs; a BLOCKED package (two failed attempts under macro_dir)
    refuses the commit through gate_package.package_state; the governance event names the ledger hash."""
    study = _study()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        store, _ = _store(tmp, frozen=True)
        macro = tmp / "macro"
        ledgers = study.ledgers_of(macro)
        assert set(ledgers) == {s.family_id for s in cards.REGISTRY} and not (macro / "ledgers").exists()
        GL.register_trial(ledgers["R-06"], _row(run_utc="2026-09-01T00:00:00Z"))
        d = _fill(cards.draft_header("MACRO-R06-KR-ETF", store, revision=2))
        h = cards.commit_header(d, store, ledgers, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl", macro_dir=macro)
        assert h["ledger_hash_at_registration"] == ledgers["R-06"].hash() and h["N_raw_at_registration"] == 1
        from core.rules import governance as G
        ev = G.read_events(tmp / "gov.jsonl")
        assert ev[-1]["kind"] == "header_commit" and f"ledger:{h['ledger_hash_at_registration']}" in ev[-1]["refs"]
        # the R-26 checks still refuse a lowered cost (instruments.header_checks through validate_card_header)
        bad = _fill(cards.draft_header("MACRO-R03-US-MOM", store, revision=1))
        bad["costs"] = {**bad["costs"], "per_side_bp": 1.0}
        _refused(lambda: cards.commit_header(bad, store, ledgers, CLOCK, ANCHOR, root=tmp / "root", governance_log=tmp / "gov.jsonl", macro_dir=macro), "cost")
        # BLOCKED: two failed acceptance attempts across 2.x
        cards.chain_append(GP.attempts_path(macro), {"attempt_no": 1, "package_version": "2.0.0", "outcome": "fail"})
        cards.chain_append(GP.attempts_path(macro), {"attempt_no": 2, "package_version": "2.1.0", "outcome": "fail"})
        assert GP.package_state(store, macro) == "BLOCKED" and not cards.package_frozen(store, macro) and cards.package_frozen(store)
        reasons = _refused(lambda: cards.commit_header(_fill(cards.draft_header("MACRO-R31-KR-ETF", store, revision=1)), store, ledgers, CLOCK, ANCHOR,
                                                       root=tmp / "root", governance_log=tmp / "gov.jsonl", macro_dir=macro), "BLOCKED")
        assert reasons[0].startswith("NOT_FROZEN")


test_commit_header_reads_the_family_ledger_and_the_package_state.test_ids = ["T-CARD-01", "T-LEDGER-01", "T-GATE-04"]


# --------------------------------------------------------------------------- #
# The freeze manifest covers every harness source that exists; the freeze refuses here with its three reasons
# --------------------------------------------------------------------------- #
def test_freeze_manifest_covers_every_harness_source_and_refuses_here():
    store = M.load_store()
    for s in M7_MODULES:
        assert (s in GP.HARNESS_SOURCES or s == "core/quant/gate_package.py") and (ROOT / s).is_file(), s
    assert all((ROOT / s).is_file() for s in GP.HARNESS_SOURCES)
    md5, manifest = GP.definitions_md5(store)
    assert not [a for a in manifest["absent"] if a.startswith("source:")], manifest["absent"]
    assert all(isinstance(v, str) and len(v) == 32 for v in manifest["harness_sources"].values())
    with tempfile.TemporaryDirectory() as tmp:
        reasons = GP.freeze_reasons(store, "UNVERSIONED", Path(tmp) / "macro")
        assert len(reasons) == 3 and reasons[1] == GP.REASON_ANCHOR
        assert reasons[0].startswith(GP.REASON_ACCEPTANCE) and "harness sources absent" not in reasons[0]
        assert reasons[2].startswith(GP.REASON_FIXTURES) and "ledger_seed_R-06.csv" not in reasons[2]
    assert store.get("gate.package.status") == "NOT_FROZEN" and GP.package_state(store) == "NOT_FROZEN"


test_freeze_manifest_covers_every_harness_source_and_refuses_here.test_ids = ["T-CARD-02", "I-08"]


# --------------------------------------------------------------------------- #
# The study runner refuses a formal run and a header commit here, printing every reason; nothing is written
# --------------------------------------------------------------------------- #
def test_study_runner_refuses_formal_runs_and_commits_with_reasons_and_writes_nothing():
    study = _study()
    store = M.load_store()
    import config
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        root, macro = tmp / "root", tmp / "macro"
        reasons = study.preflight(store, root=root, macro_dir=macro, anchor=None)
        assert any(r.startswith("gate.package.status NOT_FROZEN") for r in reasons)
        assert any("owner must place the repository under git" in r for r in reasons)
        assert any(study.CONTROL_FIXTURE in r and "REFDATA" in r for r in reasons)
        # the inputs of a formal run are the reference fixtures: absent here, named in the refusal
        h = cards.draft_header("MACRO-R06-KR-ETF", store, revision=2)
        got = _refused(lambda: study.card_inputs(h), "REFDATA")
        assert all(f in got[0] for f in study.MARKET_FIXTURES["KR"])
        _refused(lambda: study.card_inputs({**h, "market": "JP"}), "no reference fixture set")
        # CLI: --commit-headers refused (exit 2) with every reason; no ledger file, no header, no governance log
        assert study.main(["--root", str(root), "--macro-dir", str(macro), "--commit-headers"]) == 2
        assert not root.exists() and not macro.exists()
        # a frozen synthetic store with a committed header: run_card refuses on the manifest even with inputs supplied
        fstore, _ = _store(tmp, frozen=True)
        lg = GL.family_ledger("R-06", tmp / "ledgers")
        _refused(lambda: _committed(tmp, fstore, lg, root), "N_raw_at_registration")      # an empty family ledger: no configuration was ever run
        GL.register_trial(lg, _row(run_utc="2026-09-01T00:00:00Z"))
        _committed(tmp, fstore, lg, root)
        got = _refused(lambda: study.run_card("MACRO-R06-KR-ETF", 2, store=fstore, root=root, macro_dir=macro, anchor=ANCHOR,
                                              knowledge_utc="2026-10-02T07:00:00Z", clock=CLOCK, inputs=None), "package manifest")
        assert not (root / "cards").exists() and not macro.exists()
    assert not GP.attempts_path(config.macro_dir()).exists()
    assert not (ROOT / "docs" / "macro_overlay" / "cards" / "verdicts.jsonl").exists()
    assert not list((ROOT / "docs" / "macro_overlay" / "headers").glob("*.header.json"))


test_study_runner_refuses_formal_runs_and_commits_with_reasons_and_writes_nothing.test_ids = ["I-07", "I-08", "T-GATE-01", "I-09"]


# --------------------------------------------------------------------------- #
# One home: PSR (gate_stats), the UNDERPOWERED rule, BY q and Holm in step 3
# --------------------------------------------------------------------------- #
def test_one_home_psr_underpowered_rule_by_q_and_holm():
    sr, T = 0.03, 2520
    assert GL.psr(sr, T, units="daily", benchmark_sr=0.01, skew=-0.5, kurtosis=5.0) == GS.psr(sr, T, units="daily", sr0=0.01, skew=-0.5, kurt=5.0)
    try:
        GL.psr(0.7, T, units="daily")
        raise AssertionError
    except ValueError as exc:
        assert "annualised" in str(exc)
    assert [round(x, 6) for x in GS.holm_adjusted([0.01, 0.04, 0.03])] == [0.03, 0.06, 0.06]
    q = GS.by_qvalue([0.01, 0.04, 0.03])
    assert np.all(q >= np.array([0.01, 0.04, 0.03])) and np.all(q <= 1.0)
    n = GL.NResult(3, 0.1, 2.5, 2, 1.2, 1.5, 2.0)
    lines = GL.step3_lines(0.2, 0.08, 0.08, n, cells=4, pvalues=[0.01, 0.04, 0.03])
    assert lines["by_q"] == [float(x) for x in q] and lines["holm"] == [float(x) for x in GS.holm_adjusted([0.01, 0.04, 0.03])]
    assert GL.step3_lines(0.2, 0.08, 0.08, n)["by_q"] is None
    # cardp's PC-3 p-value branch is gate_stats.apply_underpowered (rule 4): MDE80 > 0.10 -> underpowered, else inconclusive
    from tests.macro_m7_cardp import _checks
    v = CP.line_verdict(_checks(pc3={"dSR": 0.0, "p_ni": 0.2, "point_2x": 0.0}, power={"mde80": 0.2}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "underpowered")
    v = CP.line_verdict(_checks(pc3={"dSR": 0.0, "p_ni": 0.2, "point_2x": 0.0}, power={"mde80": 0.05}), 1.0)
    assert (v["verdict"], v["reason"]) == ("INSUFFICIENT_DATA", "inconclusive")


test_one_home_psr_underpowered_rule_by_q_and_holm.test_ids = ["T-DSR-02", "T-STEP3-01", "T-UNDERPOW-01"]


# --------------------------------------------------------------------------- #
# T-EST-05: the counted estimator switch (forecast_eval.check_declaration, the M7 proof)
# --------------------------------------------------------------------------- #
def test_t_est_05_counted_switch_refused_without_revision_and_row_accepted_with_the_proof():
    def refused(fn, needle):
        try:
            fn()
        except F.EstimatorSwitchRefused as exc:
            assert needle in str(exc), str(exc)
            return
        raise AssertionError(needle)
    refused(lambda: F.check_declaration("garch_t", "KRX_ETF_line", "SYN-R06-GARCH", None), "counted revision")
    refused(lambda: F.check_declaration("comb", "KRX_stock_book", "SYN-R06-COMB", None), "stock")
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": 1}), "M7")
    row = GL.validate_row(_row(params={"estimator": "comb", "window": 20, "target": 0.20}, estimator="comb"))
    row["row_md5"] = GL._row_md5(row)
    header = GL.bump_revision({"card_id": "SYN-R06-COMB", "revision": 1}, "R-30 estimator switch sma20 -> comb")
    card = {"class": "CARD-P", "verdict": "PASS", "results_md5": "d" * 32}
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": row, "header": header}), "card")
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": row, "card": card}), "header")
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"header": header, "card": card}), "ledger_row")
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": row, "header": header, "card": {**card, "verdict": "REVISE"}}), "PASS")
    refused(lambda: F.check_declaration("garch_t", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": row, "header": header, "card": card}), "ledger_row")
    assert F.check_declaration("comb", "KRX_ETF_line", "SYN-R06-COMB", {"ledger_row": row, "header": header, "card": card}) == "comb"
    refused(lambda: F.check_declaration("comb", "KRX_ETF_line", "MACRO-R06-KR-ETF", {"ledger_row": row, "header": header, "card": card}), "MACRO-R06-KR-ETF")


test_t_est_05_counted_switch_refused_without_revision_and_row_accepted_with_the_proof.test_ids = ["T-EST-05"]


# --------------------------------------------------------------------------- #
# Rulings scan of the M7 modules
# --------------------------------------------------------------------------- #
def test_rulings_scan_no_clock_no_gate_read_no_kish_no_new_dependency_no_card_keyed_convention():
    forbidden = {"datetime.now", "datetime.utcnow", "time.time", "date.today", "datetime.today"}
    third_party = {"numpy", "scipy", "pandas", "np", "sps"}
    import sys
    std = set(sys.stdlib_module_names)
    sources = {}
    for rel in M7_MODULES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        sources[rel] = src
        tree = ast.parse(src)
        # the only wall clock is the CLI clock of the runner's main (a --run is refused here); library code takes it injected
        hits = [(ast.unparse(n.func), getattr(n, "lineno", 0)) for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) in forbidden]
        main = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        allowed = range(main.lineno, main.end_lineno + 1) if (main is not None and rel.startswith("docs/")) else range(0)
        assert all(ln in allowed for _, ln in hits), (rel, hits)
        assert "GATE[" not in src and "GATE.get" not in src, rel
        mods = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | \
               {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        extra = {m for m in mods if m not in std and m not in third_party and m not in ("core", "config", "docs", "tests")}
        assert not extra, (rel, extra)
    from tests.acceptance import _code_only
    assert GL.scan_forbidden({rel: _code_only(ROOT / rel) for rel in M7_MODULES}) == []   # no Kish form, no author name in identifiers
    for rel in STAT_MODULES:                                                 # no convention keyed on a card (R-06 KR has no rescue path)
        assert "MACRO-R06-KR-ETF" not in sources[rel] and "R-06-KR" not in sources[rel], rel
    study = _study()
    for fn in (study.evaluate_card, study.card_inputs, study.preflight):
        assert "MACRO-R06" not in inspect.getsource(fn)
    # seeds and B explicit on every bootstrap entry point of the chain
    for fn in (GS.lw_studentized_boot, GS.se_ladder, CP.pc1_prime, CP.pc2, CP.pc3_noninferiority, CP.timing_profile):
        params = inspect.signature(fn).parameters
        assert "seed" in params and "B" in params, fn.__name__


test_rulings_scan_no_clock_no_gate_read_no_kish_no_new_dependency_no_card_keyed_convention.test_ids = ["T-STEP3-02", "T-REPRO-01b"]


# --------------------------------------------------------------------------- #
# Post-freeze goldens and reference clauses: NOT_RUN with their fixture names (never faked)
# --------------------------------------------------------------------------- #
def _refdata(ids, extra: str = "") -> NotRun:
    """NotRun naming every absent reference fixture of the goldens `ids` (goldens.csv fixtures column -> files)."""
    goldens, listed = load_goldens(), load_manifest()
    fids = []
    for gid in ids:
        for f in goldens[gid].fixtures:
            if f not in fids:
                fids.append(f)
    absent = [f"{f} {FIXTURE_FILES.get(f, '?')}" for f in fids if FIXTURE_FILES.get(f, "?").split(" ")[0] not in listed]
    assert absent, "every fixture listed: the golden can run"
    return NotRun(f"REFDATA: {'; '.join(absent)} not in tests/fixtures/macro/MANIFEST.csv; after the gate freeze (section 9.0b){extra}")


def test_g_kr_l01_l13_korea_long_history_goldens_after_the_freeze_refdata():
    ids = [f"G-KR-L{i:02d}" for i in range(1, 14)]
    assert {r.mode for gid in ids for r in load_goldens()[gid].rows} <= {"v12_check", "reference_only", "frozen_v2", "print_only"}
    raise _refdata(ids, "; v12_check reproductions of the R-06 KR long history (I-07 Level-1), the formal run on F01 (I-16); "
                        "the cap-1.5 variant of G-KR-L13 only through tests/reference")


test_g_kr_l01_l13_korea_long_history_goldens_after_the_freeze_refdata.test_ids = [f"G-KR-L{i:02d}" for i in range(1, 14)]


def test_g_us_f01_f10_us_fixture_goldens_after_the_freeze_refdata():
    ids = [f"G-US-F{i:02d}" for i in range(1, 11)]
    assert cards.registered_reject()["rerun"] is False          # G-US-F01 is a reference reproduction, never a card run
    raise _refdata(ids, "; U1 = French Mkt-RF 1990-02 -> 2026-08 spliced with ^GSPC Sep-2026 (loader not written)")


test_g_us_f01_f10_us_fixture_goldens_after_the_freeze_refdata.test_ids = [f"G-US-F{i:02d}" for i in range(1, 11)]


def test_g_pwr_01_02_gate_power_goldens_refdata():
    rng = np.random.default_rng(SEED)
    assert GS.lw_hac_se(rng.normal(0, 0.01, 500), rng.normal(0, 0.01, 500)).se_nw10 > 0   # both SEs printed (G-PWR-01 quotes NW10 and QS)
    raise _refdata(["G-PWR-01", "G-PWR-02"], "; SE(dSR) NW10 / QS / bootstrap ladder of US VT15 and KOSPI VT20 vs S, 300 paths per cell")


test_g_pwr_01_02_gate_power_goldens_refdata.test_ids = ["G-PWR-01", "G-PWR-02"]


def test_g_dsr_02_r03_net_of_cost_golden_refdata():
    raise _refdata(["G-DSR-02"], "; R-03 net of 50 bp on both legs (SR 0.6723, T 9,233, HAC SE 0.0716) on the R-03 ledger")


test_g_dsr_02_r03_net_of_cost_golden_refdata.test_ids = ["G-DSR-02"]


def test_g_lad_04_invariants_only_book_with_and_without_the_hard_stop_refdata():
    assert all(r.pending for r in load_goldens()["G-LAD-04"].rows)      # section 9.4 item 10: printed beside D2, never gated
    raise _refdata(["G-LAD-04"], "; section 9.4 item 10 pending: the invariants-only recommended KOSPI book with and without the -15% "
                                 "hard stop (HALT count, MDD, Sharpe) printed beside D2")


test_g_lad_04_invariants_only_book_with_and_without_the_hard_stop_refdata.test_ids = ["G-LAD-04"]


def test_t_gate_02_us_vt15_after_the_freeze_refdata():
    rej = cards.registered_reject()
    assert rej["rerun"] is False and rej["label"] == cards.US_REJECT_LABEL
    raise NotRun("REFDATA: U1 french_daily_5f_2x3.csv + yahoo_GSPC_1990_2026-10-01.csv not in tests/fixtures/macro/MANIFEST.csv; "
                 "after the gate freeze (section 9.0b): the v2 verdict on US VT15 50 bp is asserted as a class (INSUFFICIENT_DATA; "
                 "ES21 +1.65 pp, ES126 +3.8 pp), p_ni printed under R-24 and md5-frozen (section 9.4 item 14); the registered REJECT "
                 "label stays and the card is never re-run")


test_t_gate_02_us_vt15_after_the_freeze_refdata.test_ids = ["T-GATE-02"]


def test_t_est_03_comb_sized_book_refdata():
    raise NotRun("REFDATA: F13 yahoo_KS11_1996-12_2026-10-02.csv (OHLC) not in tests/fixtures/macro/MANIFEST.csv: the COMB sized book "
                 "(KOSPI 2001-26, 3 bp, target 20%, cap 1; vol-of-vol -22% +/- 2 pp vs SMA20, dMDD +2.8 pp, dSR CI [-0.042, +0.039]) "
                 "runs from M7 on the frozen fixture")


test_t_est_03_comb_sized_book_refdata.test_ids = ["T-EST-03"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
