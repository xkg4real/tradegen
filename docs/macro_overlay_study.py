"""Macro card study runner (section 8.1.3 steps 3-5; R-35; TASK-M7-19, M7-21, M7-23, M7-24).

    python docs/macro_overlay_study.py                      # list every card with its status and commit preconditions
    python docs/macro_overlay_study.py --preflight           # the reasons a formal run is refused here
    python docs/macro_overlay_study.py --commit-headers      # commit the drafts blind (refused until the freeze)
    python docs/macro_overlay_study.py --run --only MACRO-R06-KR-ETF.r2 --knowledge-utc 2026-10-02T07:00:00Z --anchor <sha>

Order of work is fixed: harness tests -> acceptance test -> freeze -> header commits -> card runs. This runner
refuses to run any formal card before the freeze (`gate.package.status != FROZEN`), on a manifest mismatch
(T-CARD-02), on a broken governance / verdicts / attempts chain, without a versioned anchor, and for the registered
R-06 US 50 bp card (`rerun: false`). A refusal prints every reason and writes nothing: no error card, no partial
verdict (L2245), no `--quick` mode (B = 2,000 and seed 11 are frozen items, L4584). Listing works offline.

The formal evaluation is `evaluate_card`: the frozen gate harness in its fixed order (R-24 `se_ladder` /
`power_line` / `lw_hac_se` -> R-23 `step3` -> R-24 `pbo_on_claim` (step 4) -> R-34 `timing_profile` -> R-22 `episodes`, start band, midpoint
halves, regime lines -> R-21 `cardp_evaluate` per gating line -> `combine_card_verdict` -> `cards.write_card`,
`append_verdict`, `archive_snapshot`). Its inputs (`CardInputs`) come from the reference fixtures of the frozen
package (`card_inputs`), which are not on this machine: `run_card` refuses with the REFDATA reason after the
preflight and the header checks, and writes nothing. This file is a harness source of the package manifest.
"""
from __future__ import annotations

import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # single-threaded BLAS before numpy (T-REPRO-01b)
    os.environ.setdefault(_v, "1")

import argparse                                                  # noqa: E402
import json                                                      # noqa: E402
from dataclasses import dataclass                                # noqa: E402
from datetime import date, datetime, timedelta, timezone         # noqa: E402
from pathlib import Path                                         # noqa: E402
from typing import Callable, Mapping, Optional, Sequence         # noqa: E402

import numpy as np                                               # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.ficc import macro_artifacts as MA                      # noqa: E402
from core.ficc import macro_schema                               # noqa: E402
from core.quant import cardp as CP                               # noqa: E402
from core.quant import cards, gate_package as GP                 # noqa: E402
from core.quant import gate_ledger as GL                         # noqa: E402
from core.quant import gate_stats as GS                          # noqa: E402
from core.quant.cards import CardRefused                         # noqa: E402
from core.rules import governance as G                           # noqa: E402
from core.rules import macro_rules as M                          # noqa: E402

CARD_ROOT = ROOT / "docs" / "macro_overlay"
MODES = ("formal", "v12check", "reference")
# The reference fixtures each market's cards read (gate_package.REFERENCE_FIXTURES; ACQUISITION.csv F01, F02, F12)
MARKET_FIXTURES = {"KR": ("krx_kospi_official_close_1997-01-03_2026-10-02.csv", "ecos_bok_call_rate_1997_2026-10.csv"),
                   "US": ("french_daily_mktrf_rf_1926-07_2026-08.csv",)}
CONTROL_FIXTURE = "KR_SOX_KRW_gate_B3"
TIMING_KEYS = ("lags", "strict", "LP", "LF", "FR", "label", "live_feeds")


def ledgers_of(macro_dir) -> dict[str, GL.FamilyLedger]:
    """The family ledgers of every registered card, as working copies under `<macro_dir>/ledgers/` (rulings 2)."""
    d = Path(macro_dir) / "ledgers"
    return {fam: GL.family_ledger(fam, d) for fam in sorted({s.family_id for s in cards.REGISTRY})}


def preflight(store: M.MacroStore, *, root=CARD_ROOT, macro_dir, anchor: str | None) -> list[str]:
    """Every reason a formal card run is refused here; an empty list means the runner may evaluate."""
    reasons = []
    state = GP.package_state(store, macro_dir)
    if state != "FROZEN":
        reasons.append(f"gate.package.status {state}: docs/macro_overlay_study.py refuses to run before the freeze (P11, L2243)")
    else:
        try:
            GP.verify_package(store, macro_dir=macro_dir)
        except CardRefused as exc:
            reasons += [f"package manifest: {r}" for r in exc.reasons]
    if not anchor or anchor == MA.GIT_HASH:
        reasons.append("anchor UNVERSIONED: owner must place the repository under git (ruling 3.1; R-35 check (iii))")
    log = Path(macro_dir) / "governance_events.jsonl"
    if log.exists() and not G.verify_chain(log):
        reasons.append(f"governance chain broken: {log}")
    vp = cards.verdicts_path(root)
    if vp.exists() and not cards.verify_verdict_chain(root):
        reasons.append(f"verdicts chain broken: {vp}")
    ap = GP.attempts_path(macro_dir)
    if ap.exists() and not cards.chain_verify(ap, GP.ATTEMPT_ROW):
        reasons.append(f"acceptance attempts chain broken: {ap}")
    if not list(GP.FIXTURE_DIR.glob(f"{CONTROL_FIXTURE}*")):
        reasons.append(f"R-34 positive control (fixture {CONTROL_FIXTURE}, LP >= 0.20) not run: REFDATA absent; every card run is blocked (L3454)")
    return reasons


# --------------------------------------------------------------------------- #
# Inputs of a formal run (R-22) and the evaluation chain (section 8.1.3 step 5)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CardInputs:
    """The R-22 inputs of one formal card run on its declared span (excess returns, official closes, the probe
    control, the archive rows). Built from the reference fixtures by `card_inputs`, or by a test from synthetic
    panels; `evaluate_card` never reads a file, a clock or a network."""
    books: CP.Books                                   # honest (L = 1) books on the data_span, last date == data_span.end
    data_fn: Callable[[int], CP.Books]                # lag L -> books (timing_profile, R-34); data_fn(1) == books
    closes: np.ndarray                                # official closes for the episode builder (R-22 rules 1-2)
    close_dates: Sequence[date]
    control: dict                                     # cardp.lookahead_positive_control(<probe of KR_SOX_KRW_gate_B3>)
    snapshot_rows: Sequence[Mapping]                  # PIT rows behind data_snapshot_id (archive, section 9.4 item 16)
    costs: Mapping                                    # {table_bp, floor_bp, applied_bp} from instruments.cost_per_side
    series: Optional[Mapping] = None                  # config_id -> difference series (step3); or a loader
    loader: Optional[Callable[[str], object]] = None
    neighbours: Optional[Sequence[Mapping]] = None    # the frozen pc6_axes runs: [{dES_21, dES_126, dSR}]
    configs: Optional[np.ndarray] = None              # step 4: (T, G) daily returns of the family ledger + frozen PC-6 grid on books.dates
    onsets: Optional[int] = None                      # costed.declustered_onsets for a discrete rule
    kind: str = "continuous"
    cells: Optional[int] = None                       # pre-registered cells (z-check bar)
    pvalues: Optional[Sequence[float]] = None         # variants' analytic HAC p (printed BY q / Holm)
    strict_fn: Optional[Callable[[], CP.Books]] = None
    acceptance_f: Optional[float] = None
    estimator_ok: bool = True
    claim_lines_ok: bool = True
    regime_tags_fn: Optional[Callable] = None


def card_inputs(header: Mapping, *, fixture_dir: Path = GP.FIXTURE_DIR) -> CardInputs:
    """The inputs of a formal run come from the frozen reference fixtures of the card's market. None is on this
    machine: the refusal names each absent file (REFDATA, never a vendor substitute, rulings 1). A present file
    is still refused until its loader is written against the acquired layout (ACQUISITION.csv)."""
    market = _market(header)
    needed = MARKET_FIXTURES.get(market)
    if needed is None:
        raise CardRefused([f"{header.get('card_id')}: no reference fixture set for market {market!r}"])
    absent = [f for f in needed if not (Path(fixture_dir) / f).is_file()]
    if absent:
        raise CardRefused([f"REFDATA: {header.get('card_id')}: reference fixtures absent {absent}; a formal run reads frozen "
                           "fixtures only (T-FIX-01), never docs/asset_expansion/cache; nothing written"])
    raise CardRefused([f"REFDATA: {header.get('card_id')}: loader for {list(needed)} not written (column layout fixed at "
                       "acquisition, ACQUISITION.csv); nothing written"])


def _market(header: Mapping) -> str | None:
    """The card's market: the header's own field or the registry's (the committed header schema has none)."""
    spec = cards.BY_ID.get(header.get("card_id"))
    return header.get("market") or (spec.market if spec else None)


def _plain(x):
    """JSON-plain copy: numpy scalars, tuples, dates and Episode objects."""
    if isinstance(x, CP.Episode):
        return _plain({"peak": x.start, "trough": x.trough, "end": x.end, "depth": x.depth, "shock_type": x.shock_type,
                       "open": x.open, "regime_tags": dict(x.regime_tags), "window": list(x.window)})
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return [_plain(v) for v in x.tolist()]
    if isinstance(x, (date, datetime)):
        return x.isoformat()
    if isinstance(x, Mapping):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x


def _project(obj, s, root, reg):
    """The part of `obj` the closed card schema declares (model_card.macro: `unevaluatedProperties: false`; a field a
    rule writes is declared there, T-SCHEMA-03). Harness diagnostics beyond the schema (p_print, B, mean_block,
    shock_type, se_hac_nw10, ...) stay in the CardResult / step3 objects and are not card fields."""
    if isinstance(obj, Mapping):
        props = {}
        for a, r in reg._schemas_at(s, root):
            for k, v in (a.get("properties") or {}).items():
                props.setdefault(k, (v, r))
        if not props:
            return dict(obj)                                   # an open object (se_curve, regime_tags, ...)
        return {k: _project(v, props[k][0], props[k][1], reg) for k, v in obj.items() if k in props}
    if isinstance(obj, list):
        items = next(((a["items"], r) for a, r in reg._schemas_at(s, root) if isinstance(a.get("items"), Mapping)), None)
        return list(obj) if items is None else [_project(v, items[0], items[1], reg) for v in obj]
    return obj


def card_fields(results: Mapping) -> dict:
    """`results` projected onto the model_card.macro schema (the card's result fields)."""
    reg = macro_schema.registry()
    root = reg.by_id[macro_schema.schema_id("model_card.macro")]
    return _project(_plain(results), root, root, reg)


def _slice(b: CP.Books, start: date, end: date) -> CP.Books:
    """The books of a gating line: sessions in [start, end] (the start date's own return included)."""
    d = np.asarray([np.datetime64(x, "D") for x in b.dates])
    m = (d >= np.datetime64(start, "D")) & (d <= np.datetime64(end, "D"))
    if not m.any():
        raise CardRefused([f"gating line {start}..{end}: no session in the books"])
    # S is the line's own mean(m) x off (L2143, same days). build_books zero-fills the warm-up, so the leading flat
    # run is put back to NaN and the mean covers in-book days only, as same_exposure_static does on the full span.
    # ponytail: an overlay whose first in-book weights are exactly 0 reads them as warm-up; carry the NaN mask in Books if one exists
    lead = int(np.argmax(b.m != 0.0)) if (b.m != 0.0).any() else b.m.size
    w = np.where(np.arange(b.m.size) >= lead, b.m, np.nan)
    return CP.Books(b.on[m], b.off[m], CP.comparator_S(w[m], b.off[m]), b.m[m], tuple(x for x, k in zip(b.dates, m) if k),
                    None if b.on_2x is None else b.on_2x[m], b.synthetic_lookahead)


def _anchor_of(header: Mapping, anchor: str | None) -> GL.Anchor:
    """The header commit as an anchored instant: `git:<sha>` from the runner's --anchor (or an `external:` ref)."""
    ref = anchor if isinstance(anchor, str) and ":" in anchor else (f"git:{anchor}" if anchor and anchor != MA.GIT_HASH else GL.UNVERSIONED)
    return GL.Anchor(header.get("created_utc") or "", ref, "header_commit")


def evaluate_card(header: Mapping, inputs: CardInputs, *, store: M.MacroStore, root, ledger: GL.FamilyLedger, anchor: str | None,
                  clock, knowledge_utc: str, seed: int | None = None, B: int | None = None, run_utc: str | None = None,
                  commit: GL.Anchor | None = None, script: str = "docs/macro_overlay_study.py") -> dict:
    """One formal card under the frozen package, in the fixed order of section 8.1.3 step 5. Returns the written
    card (a dict) after `cards.write_card`, `cards.append_verdict` and `cards.archive_snapshot`; any refusal
    raises CardRefused before anything is written. `seed` / `B` default to the store's reproducibility block
    (seed_study 11, 2,000 resamples) and are passed explicitly to every bootstrap. `ledger` is the card's family
    ledger: step 3 reads the snapshot the header names, the timing rows are registered on it, and
    `ledger_hash_at_run` is its hash after the run (`gate_ledger.assert_hash_at_run`)."""
    seed = int(store.get("reproducibility.seed_study") if seed is None else seed)
    B = int(store.get("gate.stats.bootstrap.resamples") if B is None else B)
    market, bk = _market(header), inputs.books
    if market is None:
        raise CardRefused([f"{header['card_id']}: no market (not a registered card and no market field)"])
    if header.get("class") != "CARD-P":
        raise CardRefused([f"{header['card_id']}: class {header.get('class')}: the CARD-O nine-step evaluator (step-2/5 studentized p, "
                           "the step-3 gate, UNDERPOWERED on step 5) is not built; the CARD-P lines never judge a CARD-O card; nothing written"])
    hist = date.fromisoformat(header["history_first_close"])
    span_end = date.fromisoformat(header["data_span"]["end"])
    if bk.dates[-1] != span_end:
        raise CardRefused([f"{header['card_id']}: the books end {bk.dates[-1]}, the header's data_span ends {span_end} (R-22 rule 4)"])
    if bk.synthetic_lookahead:
        raise CardRefused([f"{header['card_id']}: probe books never feed a verdict (C-4)"])
    if len(inputs.neighbours or ()) < CP.PC6_MIN_NEIGHBOURS:
        raise CardRefused([f"{header['card_id']}: the main line needs the frozen pc6_axes neighbour runs (>= {CP.PC6_MIN_NEIGHBOURS}): "
                           "PC-6 is a gating REVISE check (section 8.7), never skipped; nothing written"])
    if inputs.configs is None or np.ndim(inputs.configs) != 2 or np.shape(inputs.configs)[0] != bk.on.size:
        raise CardRefused([f"{header['card_id']}: step 4 needs the configuration set (family ledger + frozen PC-6 grid) aligned on "
                           "the books (R-24 rule 6); PBO is never imputed; nothing written"])
    on, S = bk.on, bk.S
    # R-24: SE ladder, power line, LW-HAC SE of delta-SR
    hac = GS.lw_hac_se(on, S)
    ladder = GS.se_ladder(on, S, B=B, seed=seed)
    power = GS.power_line(ladder, sessions=on.size, card_class=header["class"])
    GS.check_power_block(power)
    dsr = GS.delta_sr(on, S)
    # R-23: the selection factor from the family ledger (f = 1 only through anchored timestamps); the evaluation
    # span's start is the books' first session (the header states a convention, "first close + warm-up")
    card3 = {**header, "market": market, "data_span": {"start": bk.dates[0].isoformat(), "end": span_end.isoformat()}}
    try:
        s3 = GL.step3(card3, ledger, seed, delta_sr=dsr, se_obs=hac.se, se_null=None, series=inputs.series, loader=inputs.loader,
                      commit=commit or _anchor_of(header, anchor), acceptance_f=inputs.acceptance_f, cells=inputs.cells,
                      x_rule=on, x_s=S, pvalues=inputs.pvalues)
    except (GL.LedgerRefused, GL.HeaderRefused, GL.UnanchoredTimestamp, GL.CorrUnavailable, ValueError) as exc:
        raise CardRefused([f"{header['card_id']}: step 3 refused, no card written: {exc}"]) from exc
    # R-24 rule 6 (step 4): PBO on the card's own claim (CARD-P: block-wise dES95_21 vs S); < 10 configurations: not run
    try:
        s4 = GS.pbo_on_claim(inputs.configs, S, objective="des95_21")
    except ValueError as exc:
        raise CardRefused([f"{header['card_id']}: step 4 refused, no card written: {exc}"]) from exc
    ran = s4["pbo"] is not None
    step4 = {**s4, "ran": ran, "slope": s4["slope"] if ran and np.isfinite(s4["slope"]) else None,
             "pbo_null": GS.pbo_null(s4["n_configs"], S.size, seed=seed, objective="des95_21") if ran else None}
    # R-34: the timing profile; every lag is a family-ledger row (timing_lag, phase card)
    run_utc = run_utc or MA.utc_stamp(clock())
    config = {"rule": header["rule_id"], "params": dict(header.get("parameters") or {}), "estimator": header.get("estimator"),
              "instrument_book": header.get("instrument_book"), "rebalance": header.get("rebalance"),
              "span": [bk.dates[0].isoformat(), span_end.isoformat()], "market": market, "run_utc": run_utc, "phase": "card",
              "script": script, "card_id": header["card_id"], "run_kind": "timing_lag", "run_utc_anchor": _anchor_of(header, anchor).anchor}

    def ledger_append(_family_id, row):
        GL.register_trial(ledger, {**{k: v for k, v in row.items() if k != "lag"}, "params": {**row["params"], "lag": row["lag"]}})

    prof = CP.timing_profile({"card_id": header["card_id"], "family_id": header["family_id"], "config": config,
                              "live_feeds": header.get("live_feeds") or []},
                             inputs.data_fn, B=B, seed=seed, ledger_append=ledger_append, strict_fn=inputs.strict_fn, reported_dsr=dsr)
    if prof["lag_audit_violations"]:
        raise CardRefused([f"{header['card_id']}: {prof['lag_audit_violations']} lag-audit violations on honest rows; no card written"])
    # R-22: episodes, start band, midpoint halves, regime lines
    eps = CP.episodes(inputs.closes, inputs.close_dates, threshold=CP.theta_for(market), market=market, regime_tags_fn=inputs.regime_tags_fn)
    common = dict(eps=eps, timing=prof, control=inputs.control, power=power, kind=inputs.kind, onsets=inputs.onsets,
                  estimator_ok=inputs.estimator_ok, claim_lines_ok=inputs.claim_lines_ok, f_neff=s3["f_at_neff"], market=market)

    def line(start: date, end: date, **kw) -> CP.CardResult:
        b = _slice(bk, start, end)
        return CP.cardp_evaluate(b.on, b.off, b.S, header, s3["f"], seed, B, m=b.m, dates=b.dates, on_2x=b.on_2x, books=b, **common, **kw)

    shape = (header.get("start_band") or {}).get("shape", "default")
    starts = CP.start_band(shape, history_start=hist, span_end=span_end, sessions=bk.dates)
    verdicts = [line(s, span_end).verdict for s in starts]
    split, (h1a, h1b), (h2a, h2b) = CP.midpoint_halves(hist, span_end)
    halves = [line(h1a, h1b).verdict, line(h2a + timedelta(days=1), h2b).verdict]     # the split session counted once
    floor = CP.stability_floor(shape, verdicts, halves)
    band = {"shape": shape, "verdicts": verdicts, "halves": halves}
    main = line(bk.dates[0], span_end, neighbours=inputs.neighbours, band=band, step4=step4)
    regime = []
    parts = {"full_span": main.verdict}
    for rl in CP.regime_lines(market, hist, span_end, primary_oos_line=header.get("primary_oos_line", "full_span"),
                              gating_lines=header.get("gating_lines")):
        a, b = rl["span"]
        r = line(max(a, bk.dates[0]), min(b, span_end))
        regime.append({"line": rl["line"], "span": f"{a.isoformat()[:7]}..{b.isoformat()[:7]}", "verdict": r.verdict, "gated": rl["gated"],
                       "numbers": {"dSR": r.pc3["dSR"], "p_ni": r.pc3["p_ni"], "dES_21": r.pc1_prime["legs"][0]["dES"]}})
        if rl["gated"]:
            parts[rl["line"]] = r.verdict
    parts["floor"], parts["halves"] = bool(floor["floor_pass"]), not any(v == "REJECT" for v in halves)
    verdict, why = CP.combine_card_verdict(parts)                       # the one pure verdict function (I-16 (i)-(iv))
    reason = main.reason_code if verdict == main.verdict else why
    disposition, _ = cards.disposition_for(header, verdict)
    ledger_hash_at_run = GL.assert_hash_at_run(ledger, ledger.hash())
    p3 = s3["printed"]
    benefits = CP.episode_benefits(on, S, bk.dates, eps)
    positive = sum(x for x in benefits if x > 0)
    lines = dict(main.printed)
    lines.update({"lo_sr_20": GS.lo_adjusted_sr(on, 20), "lo_sr_all": GS.lo_adjusted_sr(on, 251), "by_q": p3["by_q"],
                  "hl_haircut": GS.harvey_liu_haircut(GS.sharpe_z(CP.sharpe(on), on.size), max(int(s3["n_raw"]), 1)),
                  "se_hac_nw10": hac.se_nw10, "with_risk_layer": None, "placebo_panel": None})
    results = {
        "generated_at_utc": MA.utc_stamp(clock()), "knowledge_utc": knowledge_utc, "git_hash": anchor or MA.GIT_HASH, "config_hash": store.config_hash,
        "data_snapshot_id": cards.rederive_snapshot_id(inputs.snapshot_rows),
        "verdict": verdict, "verdict_reason": reason, "caps_applied": list(main.caps_applied),
        "verdict_at_f1": main.verdict_at_f1, "verdict_at_f_neff": main.verdict_at_f_neff, "disposition": disposition,
        "first_failed_check": main.first_failed_check, "permitted_fix": main.permitted_fix, "ledger_hash_at_run": ledger_hash_at_run,
        "N_raw": int(s3["n_raw"]), "N_clusters": int(p3["N_clusters"]), "N_equiv": float(p3["N_equiv"]), "N_hat_linear": float(p3["N_hat_linear"]),
        "N_eff": float(p3["N_eff"]), "E_max_sim": float(p3["E_sim"]), "V_null": float(p3["SE_null"]) ** 2, "V_trials": p3["V_trials"],
        "selection_factor": s3["selection_factor"], "power": power.as_dict(),
        "timing_profile": {k: (None if prof[k] == "n/m" else prof[k]) for k in TIMING_KEYS} | {"LP": float(inputs.control["LP"])},
        "episodes": [{**_plain(e), "benefit_vs_S": bft, "share": (bft / positive if bft > 0 and positive > 0 else None), "post_trough_63": pt}
                     for e, bft, pt in zip(eps, benefits, lines["post_trough"])],
        "start_band_results": {"starts": [s.isoformat() for s in starts], "verdicts": verdicts, "n_pass": floor["n_pass"],
                               "n_starts": floor["n_starts"], "n_reject": floor["n_reject"], "floor_pass": floor["floor_pass"]},
        "midpoint_halves_results": {"h1": halves[0], "h2": halves[1]}, "regime_line_results": regime, "gjr_null_pct": None,
        "costs_per_side": {"table_bp": inputs.costs["table_bp"], "floor_bp": inputs.costs["floor_bp"], "applied_bp": inputs.costs["applied_bp"],
                           "stress_line": None, "roll_cost_line": None},
        "cost_stress": 2.0, "cost_episodes": [lines["cost_episodes"]],
        "pc4_section_8_6": {"positive": main.pc4["positive"], "n": main.pc4["n"], "max_share": main.pc4["max_share"]},
        "tests": {"PC1p": main.pc1_prime, "PC2": main.pc2, "PC3": main.pc3, "PC4": main.pc4, "PC5": main.pc5, "PC6": main.pc6, "PC7": main.pc7,
                  "step3": {**p3, "selection_factor": s3["selection_factor"], "pass": s3["verdict_contrib"]["pass"], "f_by_reading": s3["f_by_reading"],
                            "fixed_at": s3["fixed_at"], "fail_closed": s3["fail_closed"]},
                  "step4": {k: step4[k] for k in ("pbo", "winner_loses_share", "pbo_null", "slope", "n_configs")}},
        "printed": lines, "lag_audit_violations": int(prof["lag_audit_violations"]),
    }
    path = cards.write_card(root, header, card_fields(results), clock, store=store)
    card = json.loads(path.read_text(encoding="utf-8"))
    cards.append_verdict(root, card)
    cards.archive_snapshot(root, card, inputs.snapshot_rows)
    return card


def run_card(card_id: str, revision: int, *, store: M.MacroStore, root=CARD_ROOT, macro_dir, anchor: str | None,
             knowledge_utc: str, clock, mode: str = "formal", inputs: CardInputs | None = None) -> dict:
    """The written card, or CardRefused with every reason (nothing written; the card stays NOT_RUN)."""
    spec = cards.BY_ID.get(card_id)
    if spec is None:
        raise CardRefused([f"{card_id}: not a registered macro card"])
    if not spec.rerun:
        raise CardRefused([f"{card_id}: registered card {spec.label!r} is never re-run (vol_target.US.registered_card.rerun false, L4291)"])
    if mode not in MODES:
        raise CardRefused([f"mode {mode!r} not in {MODES}"])
    if mode != "formal":
        raise CardRefused([f"mode {mode}: harness outputs only, never a card record; reachable from tests/reference/ and docs/ through the "
                           "gate harness (cardp / costed reference mode); nothing written here"])
    reasons = preflight(store, root=root, macro_dir=macro_dir, anchor=anchor)
    if reasons:
        raise CardRefused(reasons)
    header = cards.load_header(root, card_id, revision)                    # re-hash; a mismatch is refused (T-CARD-01)
    pkg = store.get("gate.package")
    if header.get("gate_package_md5") != pkg["definitions_md5"] or header.get("gate_package_version") != pkg["version"]:
        raise CardRefused([f"{card_id}.r{revision}: header cites package {header.get('gate_package_version')} / {header.get('gate_package_md5')}, "
                           f"frozen {pkg['version']} / {pkg['definitions_md5']} (L2244)"])
    inputs = inputs if inputs is not None else card_inputs(header)        # REFDATA on this machine: refused here
    return evaluate_card(header, inputs, store=store, root=root, ledger=ledgers_of(macro_dir)[header["family_id"]], anchor=anchor,
                         clock=clock, knowledge_utc=knowledge_utc)


def listing(store: M.MacroStore, *, root=CARD_ROOT, macro_dir, anchor: str | None) -> dict:
    """The offline dry listing: every card, its status, its commit preconditions, the package state, the refusal reasons."""
    return {"package": {"state": GP.package_state(store, macro_dir), **store.get("gate.package")},
            "anchor": anchor or MA.GIT_HASH,
            "cards": cards.list_cards(root, store),
            "registered_reject": cards.registered_reject(store),
            "pending_values": [{k: v for k, v in p.items() if k != "package_dependent"} for p in cards.PENDING_VALUES],
            "preflight": preflight(store, root=root, macro_dir=macro_dir, anchor=anchor)}


def _print_listing(info: dict) -> None:
    pkg = info["package"]
    print(f"gate.package {pkg.get('version')} status {info['package']['state']} definitions_md5 {pkg.get('definitions_md5')} anchor {info['anchor']}")
    for c in info["cards"]:
        print(f"  {c['card_id']:<22} {c['class']:<6} {c['family_id']:<5} {c['verdict']:<9} {c['disposition']:<19} {c['build_status']:<19} "
              f"{c['instrument_book']:<22} label={c['label']!r}")
        for path, why in (c.get("owner_nulls") or {}).items():
            print(f"      null {path}: {why}")
    print("  registered REJECT:", info["registered_reject"]["label"], "rerun", info["registered_reject"]["rerun"])
    print("formal run preflight:")
    for r in info["preflight"]:
        print("   refused:", r)
    if not info["preflight"]:
        print("   ok")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", default="", help="comma-separated card ids, optionally with .r<rev>")
    ap.add_argument("--mode", default="formal", choices=MODES)
    ap.add_argument("--run", action="store_true", help="evaluate the formal cards (refused before the freeze)")
    ap.add_argument("--commit-headers", action="store_true", help="commit the drafts blind (refused before the freeze)")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--knowledge-utc", default=None, help="pinned knowledge instant of a formal run (ISO-8601 Z)")
    ap.add_argument("--anchor", default=MA.GIT_HASH, help="the repository commit of the manifest and headers (never fabricated)")
    ap.add_argument("--root", default=str(CARD_ROOT))
    ap.add_argument("--macro-dir", default=None, help="defaults to config.macro_dir()")
    ap.add_argument("--store", default=str(M.SHIPPED_STORE_PATH))
    args = ap.parse_args(argv)
    import config
    args.macro_dir = str(config.refuse_quantgen(args.macro_dir, "--macro-dir") if args.macro_dir else config.macro_dir())
    store = M.load_store(args.store, rulings_log=Path(args.macro_dir) / "governance_events.jsonl")
    root = Path(args.root)
    info = listing(store, root=root, macro_dir=args.macro_dir, anchor=args.anchor)
    if not (args.run or args.commit_headers):
        _print_listing(info)
        return 0
    wanted = [x for x in args.only.split(",") if x] or [f"{s.card_id}.r{r}" for s in cards.REGISTRY if s.step4_header for r in s.revisions]
    rc = 0
    clock = lambda: datetime.now(timezone.utc)          # CLI entry only; the library takes the clock injected  # noqa: E731
    if args.commit_headers:
        ledgers = ledgers_of(args.macro_dir)
        for item in wanted:
            cid, _, rev = item.partition(".r")
            try:
                draft = cards.draft_header(cid, store, revision=int(rev) if rev else None)
                cards.commit_header(draft, store, ledgers, clock, args.anchor, root=root,
                                    governance_log=Path(args.macro_dir) / "governance_events.jsonl", macro_dir=args.macro_dir)
                print(f"header committed: {item}")
            except CardRefused as exc:
                rc = 2
                print(f"header commit refused: {item}")
                for r in exc.reasons:
                    print("   ", r)
    if args.run:
        if not args.knowledge_utc:
            print("refused: a formal run needs --knowledge-utc (pinned, never now)")
            return 2
        for item in wanted:
            cid, _, rev = item.partition(".r")
            try:
                run_card(cid, int(rev or cards.BY_ID[cid].revisions[0]), store=store, root=root, macro_dir=args.macro_dir, anchor=args.anchor,
                         knowledge_utc=args.knowledge_utc, clock=clock, mode=args.mode)
            except CardRefused as exc:
                rc = 2
                print(f"formal run refused: {item} (card record unchanged; nothing written)")
                for r in exc.reasons:
                    print("   ", r)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
