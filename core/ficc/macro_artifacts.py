"""Artifact writer, provenance stamp, quarantine and the RNG convention for the section-6
artifacts (R-32, R-01 rule 4; TASK-M0-11), plus the M6 builders `build_macro_state` and
`build_overlay_decisions` (TASK-M6-05; R-32, R-09, R-10, R-30; T-HEDGE-01 and I-06c M6 clauses).

The builders compute no exposure: they copy the producers' results (M1-M5) into the section 6.1 /
6.2 shapes and call `risk_layer.risk_layer` / `compose_detail` for the composition lines. They never
import `core.ficc.context_log` or `core.ficc.macro` (T-CTX-01, BUILDER_FORBIDDEN). A schema failure
never raises: the artifact is returned flagged (`extras.validation_errors`, `extras.acting_failure`,
`fail_closed`) and `write_built` quarantines an acting failure (the M8 `bounds_ok` HALT scope) or
writes a display failure with its errors (never a HALT, L3370).

Roots and clocks are injected; this module never imports config and never reads a wall clock.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

from core.ficc import pit as _pit
from core.ficc.macro_schema import WHOLE_REFUSAL, canonical_json, check_artifact, md5_hex, short_name
from core.quant import risk_layer as RL

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_HASH = "UNVERSIONED"      # ruling 3.1: the folder is not a git repository; never a fabricated sha
TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")
Clock = Callable[[], datetime]
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class ArtifactRefused(Exception):
    def __init__(self, kind, issues, acting_failure, quarantine_path):
        super().__init__("%s refused (%d issue(s), acting=%s); quarantined at %s"
                         % (kind, len(issues), acting_failure, quarantine_path))
        self.kind, self.issues = kind, list(issues)
        self.acting_failure, self.quarantine_path = acting_failure, quarantine_path


def utc_stamp(dt: datetime) -> str:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("clock must return a tz-aware datetime")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def tree_hash(root: Path = REPO_ROOT) -> str:
    """sha256 over sorted relative paths + bytes of core/**/*.py, data/macro/**, config.py (ruling 3.1)."""
    root = Path(root)
    files = sorted({p for g in TREE_GLOBS for p in root.glob(g) if p.is_file()},
                   key=lambda p: p.relative_to(root).as_posix())
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def data_snapshot_id(content_hashes=()) -> str:
    # M0 stub of SPEC L1014 (md5 of the sorted content hashes); integration: replaced by core/ficc/pit.py (M1)
    return md5_hex("\n".join(sorted(content_hashes)))


def provenance(*, clock: Clock, knowledge_utc: str, config_hash: str, data_snapshot_id: str) -> dict:
    """The common provenance block (L3508). knowledge_utc is pinned by the caller, never "now"."""
    return {"schema_version": "2.0", "read_only": True, "generated_at_utc": utc_stamp(clock()),
            "knowledge_utc": knowledge_utc, "git_hash": GIT_HASH, "tree_hash": tree_hash(),
            "config_hash": config_hash, "data_snapshot_id": data_snapshot_id}


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def _slug(x) -> str:
    return _SAFE.sub("_", str(x)) or "_"


def default_relpath(kind: str, obj: dict) -> str:
    g = obj.get
    if kind == "macro_state":
        return "macro_state/%s/%s.json" % (_slug(g("market")), _slug(g("decided_session")))
    if kind == "overlay_decision":
        return "overlay_decision/%s/%s/%s.json" % (_slug(g("market")), _slug(g("effective_session")), _slug(g("family")))
    if kind == "context_log":
        return "context_log/%s.json" % _slug(str(g("decision_utc")).replace(":", ""))
    if kind == "event_calendar":
        return "event_calendar/%s.json" % _slug(g("calendar_version"))
    if kind == "model_card.macro":
        return "cards/%s.json" % _slug(g("card_id"))
    return "%s/%s.json" % (_slug(kind), md5_hex(canonical_json(obj))[:12])


def quarantine(root, kind: str, obj, issues, clock: Clock, *, cls: str = "refused") -> Path:
    """Content-addressed record under root/quarantine/ (a replayed failure does not multiply files)."""
    record = {"quarantined_utc": utc_stamp(clock()), "schema": kind, "class": cls, "issues": list(issues)}
    try:
        key = md5_hex(canonical_json(obj))
        record["artifact"] = obj
    except (TypeError, ValueError):
        record["artifact_repr"] = repr(obj)
        key = md5_hex(repr(obj))
    path = Path(root) / "quarantine" / ("%s__%s.json" % (_slug(kind), key[:12]))
    _atomic_write(path, canonical_json(record))
    return path


def write_artifact(root, kind: str, obj: dict, clock: Clock, relpath: str | None = None) -> Path:
    """The only path by which a section-6 artifact or card reaches disk. Validates first; an acting
    failure or a whole-refusal kind goes to root/quarantine/ and raises ArtifactRefused; a
    display-only failure is written with extras.validation_errors (never a HALT, R-32)."""
    kind = short_name(kind)
    ok, issues, acting = check_artifact(kind, obj)
    if ok:
        out = obj
    elif acting or kind in WHOLE_REFUSAL:
        raise ArtifactRefused(kind, issues, acting, quarantine(root, kind, obj, issues, clock,
                                                                cls="acting" if acting else "refused"))
    else:
        out = dict(obj)
        out["extras"] = dict(obj.get("extras") or {})
        out["extras"]["validation_errors"] = list(issues)
    path = Path(root) / (relpath or default_relpath(kind, out))
    _atomic_write(path, canonical_json(out))
    return path


# reproducibility.determinism.rng: numpy PCG64 seeded through SeedSequence, spawned children
def rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))


def child_rngs(seed: int, n: int) -> list[np.random.Generator]:
    return [np.random.Generator(np.random.PCG64(s)) for s in np.random.SeedSequence(seed).spawn(n)]


# --------------------------------------------------------------------------- #
# M6 builders (TASK-M6-05): assembly only, validated, fail closed
# --------------------------------------------------------------------------- #
FAMILIES = ("momentum", "reversal", "flow", "quality", "ts_trend")
PASS_DISPOSITIONS = ("RECOMMENDATION", "BUILD_AS_INSURANCE")
DECISIONS = ("D1", "D2", "D3", "D4", "D5", "D6")
ALERT_DISPLAY = "SCHEMA_DISPLAY_FIELD"
ALERT_ACTING = "SCHEMA_ACTING_FIELD"


def _iso(x) -> str | None:
    return None if x is None else _pit.iso_utc(x)


def _date(x) -> str:
    return x.isoformat() if isinstance(x, date) else str(x)


def not_run_card(card_id: str, cls: str = "CARD-P", label: str | None = None, disposition: str = "DESCRIPTIVE") -> dict:
    """A $defs/card before the first formal run (every macro card is NOT_RUN in v2.0)."""
    return card_of({"card_id": card_id, "class": cls, "verdict": "NOT_RUN", "disposition": disposition, "label": label})


def card_of(c: Mapping | None, card_id: str = "UNKNOWN") -> dict:
    """The seven $defs/card keys; `displayed_as` derived by S1/S2 when absent."""
    c = dict(c or {})
    verdict, disp = c.get("verdict", "NOT_RUN"), c.get("disposition", "DESCRIPTIVE")
    pass_like = verdict == "PASS" and disp in PASS_DISPOSITIONS
    shown = c.get("displayed_as") or ("invariant" if disp == "INVARIANT_STEP" else "recommendation" if pass_like and disp == "RECOMMENDATION"
                                      else "insurance" if pass_like else "refusal" if disp == "REFUSAL_BOOK" else "descriptive")
    return {"card_id": c.get("card_id", card_id), "class": c.get("class", "CARD-O"), "verdict": verdict, "disposition": disp,
            "displayed_as": shown, "label": c.get("label"), "results_md5": c.get("results_md5")}


def _pass_like(card: Mapping | None) -> bool:
    c = card_of(card)
    return c["verdict"] == "PASS" and c["disposition"] in PASS_DISPOSITIONS       # S1 (L3767)


def acts_in_recommended(card: Mapping | None) -> bool:
    return _pass_like(card) or card_of(card)["disposition"] == "INVARIANT_STEP"      # + S2 (L3768-3769)


def input_records(items: Sequence, *, registry=None, clocks=None, status: str = "ok") -> tuple[list[dict], list[str]]:
    """$defs/input records from dicts (as is) or PITValues (through `risk_layer.input_record`; needs registry +
    clocks, else listed as unrecorded). Deduped by content_hash; a MissingInput has no row to record (F-29)."""
    out, seen, unrecorded = [], set(), []
    for it in items:
        if isinstance(it, Mapping):
            rec = dict(it)
        elif isinstance(it, _pit.PITValue):
            if registry is None or clocks is None:
                unrecorded.append(it.series_id)
                continue
            rec = RL.input_record(it, registry, clocks, name=it.series_id, status=status)
        else:
            unrecorded.append(getattr(it, "series_id", repr(it)))
            continue
        key = rec.get("content_hash") or canonical_json(rec)
        if key not in seen:
            seen.add(key)
            out.append(rec)
    return out, unrecorded


def owner_decisions_block(rules) -> dict:
    """{canonical key: {decision, value, status}} for D1..D6 (every pending decision included; F-26, F-27)."""
    reg = rules["owner_decisions"] if isinstance(rules, Mapping) else rules.get("owner_decisions")
    return {e["key"]: {"decision": d, "value": e.get("value"), "status": e.get("status", "pending")}
            for d, e in reg.items() if d in DECISIONS and isinstance(e, Mapping) and "key" in e}


def _rt_entry(runtime: Sequence[Mapping], book_id: str) -> Mapping | None:
    return next((e for e in runtime if e.get("book_id") == book_id), None)


def hard_stop_state(entry: Mapping | None, decided_session: date | None = None) -> str:
    """armed | halted | rearm_refused | post_rearm_cap from the recommended book's runtime entry (R-07)."""
    if not entry:
        return "armed"
    halt = entry.get("halt") or {}
    causes = [c for c in halt.get("causes", []) if c.get("reason_code") == "hard_stop" and not c.get("cleared_utc")]
    if entry.get("engine_state") == "HALTED" and causes:
        nb = causes[0].get("rearm_not_before")
        if nb and decided_session is not None and decided_session < date.fromisoformat(nb):
            return "rearm_refused"
        return "halted"
    until = entry.get("post_rearm_cap_until")
    if until and (decided_session is None or decided_session <= date.fromisoformat(until)):
        return "post_rearm_cap"
    return "armed"


def ladder_flags(ladder) -> dict:
    """flags.ladder_* from a `risk_layer.LadderState` (None = ladder not run: no step, nothing blocked)."""
    if ladder is None:
        return {"ladder_step": "none", "ladder_dwell_left": 0, "block_new_entries": False, "ladder_steps_act_in": "specification"}
    step = ("hard_stop_-15" if ladder.halted else "step_-12" if ladder.step_mult < 1.0 and ladder.block_new_entries
            else "step_-8" if ladder.step_mult < 1.0 else "none")
    share = ladder.binding_share
    return {"ladder_step": step, "ladder_dwell_left": int(ladder.dwell_left), "block_new_entries": bool(ladder.block_new_entries),
            "ladder_steps_act_in": "recommended" if share is not None and share <= 0.10 else "specification"}


def _flag_result(kind: str, obj: dict) -> dict:
    """Validate in place: display errors are carried (written with extras.validation_errors), an acting error
    flags the artifact closed (quarantined by `write_built`)."""
    ok, issues, acting = check_artifact(kind, obj)
    if not ok:
        obj.setdefault("extras", {})["validation_errors"] = list(issues)
        obj["extras"]["acting_failure"] = bool(acting)
        if acting and "fail_closed" in obj:
            obj["fail_closed"] = True
    return obj


def build_macro_state(market: str, ctx, *, provenance: Mapping, decided_session: date, effective_session: date, vol: Mapping,
                      hedge, runtime: Sequence[Mapping], rules, book_factors: Mapping[str, Mapping], concentration=None,
                      pair: Mapping | None = None, gap: Mapping | None = None, ladder=None, inputs: Sequence = (),
                      lag_audit: Mapping | None = None, alerts: Sequence[Mapping] = (), annotations: Mapping | None = None,
                      dm_bear_state: bool | None = None, refusal_books: Mapping | None = None, forward_sim: Mapping | None = None,
                      acting_components: Sequence = (), regime_tags: Mapping | None = None, extras: Mapping | None = None,
                      registry=None, clocks=None) -> dict:
    """One `quantgen.macro_state` per market per decision (section 6.1) from the producers:
    `vol` = `risk_layer.vol_state(...)`; `hedge` = `HedgeState` (risk model; its failures never set fail_closed);
    `runtime` = `BookRegistry.runtime_entries()` of this market's books; `book_factors` = {book_id: {vt, overlays,
    ladder, post_rearm_cap, halted}} composed here through `risk_layer.risk_layer` into `concentration.by_book`;
    `concentration` = `ConcentrationBound` (M5), `ladder` = `LadderState` (M5), `gap` = {kr_open_gap_event,
    gap_sessions, var_display_scale} (M5); `inputs` = $defs/input records or PITValues; `acting_components` =
    objects with `.fail_closed` (BookVT, BaseWeights, ActingFailure): fail_closed is their OR. Always returns the
    dict; a schema failure is flagged, never raised (R-32)."""
    gap = dict(gap or {"kr_open_gap_event": False, "gap_sessions": 0})
    n_us = int(gap.get("gap_sessions", 0))
    gap.setdefault("var_display_scale", math.sqrt(max(n_us, 1)))
    rec_entry = _rt_entry(runtime, f"recommended:{market}")
    od = owner_decisions_block(rules)
    flags = {"hedge_credit_off": bool(hedge.hedge_credit_off), "hedge_failure": bool(hedge.hedge_failure),
             "classic_risk_off": bool(hedge.classic_risk_off), "hedge_reasons": list(hedge.hedge_reasons),
             "hedge_stale_inputs": list(hedge.hedge_stale_inputs), "fx_hedge_credit": hedge.fx_hedge_credit,
             "kr_open_gap_event": bool(gap["kr_open_gap_event"]), "gap_sessions": n_us,
             "var_display_scale": float(gap["var_display_scale"]), **ladder_flags(ladder),
             "hard_stop": hard_stop_state(rec_entry, decided_session),
             "hard_stop_level": od.get("risk_layer.drawdown.hard_stop.level", {}).get("value"),
             "engine_state": rec_entry.get("engine_state") if rec_entry else "DISARMED"}
    if dm_bear_state is not None:
        flags = {"dm_bear_state": bool(dm_bear_state), **flags}
    level = flags["hard_stop_level"]
    if not (isinstance(level, (int, float)) and not isinstance(level, bool) and math.isfinite(level)):
        flags.pop("hard_stop_level")    # the acting flag is a number; a D2 rule string ('-1.5*sigma_book', S1 dev. 13) is display
        if level is not None:
            extras = {"hard_stop_level_rule": level, **dict(extras or {})}
    by_book = {}
    for book_id, f in book_factors.items():
        by_book[book_id] = RL.risk_layer(f["vt"], f.get("overlays", {}), f.get("ladder", 1.0), f.get("post_rearm_cap", 1.0),
                                         concentration, halted=bool(f.get("halted", False)))
    pair = dict(pair or {})                      # the ConcentrationBound (M5) carries the template and the look-through share
    conc = {"template": getattr(concentration, "template", "") or od.get("risk_layer.korea_caps.template", {}).get("value", "msci_25_50"),
            "pair_share_kospi": pair.get("pair_share_kospi"),
            "pair_lookthrough_share": pair.get("pair_lookthrough_share", getattr(concentration, "pair_lookthrough_share", None)),
            "pair_risk_contribution": pair.get("pair_risk_contribution"),
            "absolute_bound": getattr(concentration, "absolute_bound", None), "active_bound": getattr(concentration, "active_bound", None),
            "aggregate_bound": getattr(concentration, "aggregate_bound", None), "semis_bound": getattr(concentration, "semis_bound", None),
            "by_book": by_book}
    recs, unrecorded = input_records(list(inputs) + list(hedge.inputs), registry=registry, clocks=clocks)
    seen, al = set(), []
    for a in list(alerts) + list(hedge.alerts):
        if a["alert_id"] not in seen:
            seen.add(a["alert_id"])
            al.append(dict(a))
    ex = {"unrecorded_inputs": unrecorded, "hedge_notes": list(getattr(hedge, "notes", ())), **dict(extras or {})}
    if regime_tags is not None:
        ex["regime_tags"] = dict(regime_tags)
    if lag_audit is None:                 # the required block defaults to empty; say the audit did not run (step error)
        ex.setdefault("lag_audit_status", "not_run")
    obj = {"schema": "quantgen.macro_state", **dict(provenance), "decision_utc": _iso(ctx.decision_utc),
           "decided_session": _date(decided_session), "effective_session": _date(effective_session), "market": market,
           "run_mode": ctx.run_mode, "inputs": recs, "lag_audit": dict(lag_audit or {"checked": 0, "violations": []}),
           "vol": dict(vol), "flags": flags, "annotations": dict(annotations or {"vix_ge_vix3m": False, "notes": []}),
           "refusal_books": dict(refusal_books or {"S1_krw_flag": None, "S2_rates_flag": None}),
           "forward_sim": dict(forward_sim or {"R28_below_sma10m": None, "R29_vt_weight_next": None}),
           "concentration": conc, "owner_decisions": od, "runtime": [dict(e) for e in runtime],
           "fail_closed": any(bool(getattr(c, "fail_closed", False)) for c in acting_components), "alerts": al, "extras": ex}
    return _flag_result("macro_state", obj)


def _rule_family(rule_id: str) -> str:
    parts = rule_id.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else rule_id


def _reason_lines(*objs) -> list[str]:
    out = []
    for o in objs:
        for r in getattr(o, "reasons", ()) or ():
            if r not in out:
                out.append(r)
    return out


def _record(market: str, ctx, provenance, effective_session, family: str, basis: str, *, vol_scale: float, vol_scale_card: dict,
            mults: Sequence[Mapping], ladder, post_rearm_cap, vt: float, reasons: list[str], extra_binding: Sequence[str],
            forward_sim, refusal, inputs, rule_versions, extras) -> dict:
    values = {m["rule_id"]: m["value"] for m in mults}
    spec = RL.compose_detail(vt, values, ladder if ladder is not None else 1.0, post_rearm_cap if post_rearm_cap is not None else 1.0)
    passing = {k: v for k, v in values.items() if acts_in_recommended(next(m["card"] for m in mults if m["rule_id"] == k))}
    rec = RL.compose_detail(1.0, passing, 1.0, post_rearm_cap if post_rearm_cap is not None else 1.0)   # F-10: ladder enters as 1.0 (M8)
    binding = list(dict.fromkeys(list(extra_binding) + list(spec.binding)))
    versions = {_rule_family(m["rule_id"]): "2.0" for m in mults}
    versions.update({_rule_family(x["rule_id"]): "2.0" for x in list(forward_sim) + list(refusal)})
    versions.update(rule_versions or {})
    obj = {"schema": "quantgen.overlay_decision", **dict(provenance), "decision_utc": _iso(ctx.decision_utc),
           "effective_session": _date(effective_session), "market": market, "family": family, "exposure_basis": basis,
           "vol_scale": float(vol_scale), "vol_scale_recommended_book": float(vol_scale) if _pass_like(vol_scale_card) else 1.0,
           "vol_scale_card": card_of(vol_scale_card), "multipliers": [dict(m) for m in mults],
           "ladder": ladder, "post_rearm_cap": post_rearm_cap, "composition": "min", "overlay_min": spec.overlay_min,
           "overlay_floor": 0.5, "overlay_cap": 1.0, "overlay_applied_spec_book": spec.overlay_min,
           "overlay_applied_recommended_book": rec.overlay_min,
           "forward_sim": [{**dict(x), "card": card_of(x.get("card"))} for x in forward_sim],
           "refusal": [{**dict(x), "card": card_of(x.get("card"))} for x in refusal],
           "binding": binding, "reasons": list(dict.fromkeys(reasons + list(spec.reasons))), "inputs": inputs,
           "rule_versions": versions, "extras": dict(extras or {})}
    return _flag_result("overlay_decision", obj)


def build_overlay_decisions(market: str, ctx, *, provenance: Mapping, effective_session: date, vt=None, vt_card: Mapping | None = None,
                            vs: Mapping | None = None, multipliers: Sequence = (), ladder: float = 1.0, post_rearm_cap: float = 1.0,
                            ladder_card: Mapping | None = None, concentration_bound: float | None = None, forward_sim: Sequence[Mapping] = (),
                            refusal: Sequence[Mapping] = (), rule_versions: Mapping | None = None, neutralised: Mapping | None = None,
                            families: Sequence[str] = FAMILIES, registry=None, clocks=None, extras: Mapping | None = None) -> list[dict]:
    """One `quantgen.overlay_decision` per family (active basis: vs from `vs[family]`, overlays whose `applies_to`
    is the family) plus one `market_gross` record (total basis: vt from `vt` (BookVT | VTResult | float), total
    overlays, ladder and post_rearm_cap). Composition by min() through `risk_layer.compose_detail`; the recommended
    line keeps only PASS / INVARIANT_STEP factors (every other enters as 1.0, L3769). `neutralised` (rule_id ->
    R-18 event_id, from the per-book runtime) maps a macro-conditioned multiplier to 1.0 with a reason (R-18 (i)).
    `forward_sim` / `refusal` entries are display only ({rule_id, value, would_apply_to, card}). Each record is
    validated and flagged, never raised."""
    vs, neutralised = dict(vs or {}), dict(neutralised or {})
    mults = [m for m in multipliers if getattr(m, "factor", "overlay") == "overlay"]

    def mult_rows(sel):
        rows, reasons = [], []
        for m in sel:
            row = {"rule_id": m.rule_id, "value": float(m.value), "exposure_basis": m.exposure_basis, "card": card_of(m.card, m.rule_id)}
            if m.rule_id in neutralised:
                row["value"] = 1.0
                reasons.append(f"R-18: {m.rule_id} neutralised to 1.0 by official framework change {neutralised[m.rule_id]} "
                               "(forward record started; no historical re-gate)")
            rows.append(row)
        return rows, reasons

    out = []
    for fam in families:
        r = vs.get(fam)
        sel = [m for m in mults if m.exposure_basis == "active" and m.applies_to in (fam, "")]
        rows, nreasons = mult_rows(sel)
        if isinstance(r, _pit.MissingInput):
            scale, card, reasons = 1.0, not_run_card(f"MACRO-R03-{market}-{fam.upper()}", "CARD-O"), [
                f"VS: {r.series_id} {r.reason} {r.detail}".strip() + "; fail_closed (state carried by the book builder)"]
        elif r is not None:
            scale, card, reasons = float(r.value), dict(r.card), _reason_lines(r)
        else:
            scale, card, reasons = 1.0, not_run_card(f"MACRO-R03-{market}-{fam.upper()}", "CARD-O"), []
        if fam == "ts_trend":
            reasons.append("R-14: ts_trend exempt from overlays and vt")
        elif fam in ("reversal", "quality", "flow"):
            reasons.append(f"R-05: {fam} fixed 1.0 (no overlay)")
        recs, unrec = input_records(list(getattr(r, "inputs", ()) or ()) + [i for m in sel for i in (m.inputs or ())], registry=registry, clocks=clocks)
        ex = {**dict(extras or {}), **({"unrecorded_inputs": unrec} if unrec else {})}
        out.append(_record(market, ctx, provenance, effective_session, fam, "active", vol_scale=scale, vol_scale_card=card, mults=rows,
                           ladder=None, post_rearm_cap=None, vt=1.0, reasons=reasons + _reason_lines(*sel) + nreasons,
                           extra_binding=[r.rule_id] if r is not None and not isinstance(r, _pit.MissingInput) and scale < 1.0 else [],
                           forward_sim=[], refusal=[], inputs=recs, rule_versions=rule_versions, extras=ex))
    # market_gross
    if isinstance(vt, RL.BookVT):
        vt_val, vt_reason = (vt.weight if vt.weight is not None else 0.0), ([] if vt.weight is not None else ["vt fail_closed with no previous state: no budget (0.0)"])
    elif isinstance(vt, RL.VTResult):
        vt_val, vt_reason = (vt.weight if vt.weight is not None else 1.0), ([] if vt.weight is not None else ["vt insufficient_history: warm-up 1.0"])
    elif vt is None:
        vt_val, vt_reason = 1.0, ["vt not run: 1.0"]
    else:
        vt_val, vt_reason = float(vt), []
    total = [m for m in mults if m.exposure_basis == "total"]
    rows, nreasons = mult_rows(total)
    gross_reasons = vt_reason + _reason_lines(vt, *total) + nreasons
    composed = RL.compose(vt_val, [m["value"] for m in rows], ladder, post_rearm_cap)
    extra = (["R-06-VT"] if vt_val < 1.0 else []) + (["concentration_bound"] if concentration_bound is not None and concentration_bound < composed else [])
    if concentration_bound is not None:
        gross_reasons.append(f"gross = min(composed {composed:.4f}, concentration_bound {concentration_bound:.4f}) (a risk limit, not an overlay)")
    recs, unrec = input_records(list(getattr(vt, "inputs", ()) or ()) + [i for m in total for i in (m.inputs or ())], registry=registry, clocks=clocks)
    ex = {**dict(extras or {}), **({"unrecorded_inputs": unrec} if unrec else {}), "ladder_card": card_of(ladder_card, "R-31") if ladder_card else None}
    out.append(_record(market, ctx, provenance, effective_session, "market_gross", "total", vol_scale=vt_val,
                       vol_scale_card=vt_card or not_run_card(f"MACRO-R06-{market}"), mults=rows, ladder=float(ladder),
                       post_rearm_cap=float(post_rearm_cap), vt=vt_val, reasons=gross_reasons, extra_binding=extra,
                       forward_sim=forward_sim, refusal=refusal, inputs=recs, rule_versions=rule_versions, extras=ex))
    return out


@dataclass(frozen=True)
class WriteOutcome:
    kind: str
    status: str                    # written | written_with_display_errors | quarantined
    path: Path | None
    acting_failure: bool = False
    issues: tuple[str, ...] = ()
    alert: dict | None = None


def write_built(root, kind: str, obj: dict, clock: Clock) -> WriteOutcome:
    """Write a built artifact, fail closed: an acting failure is quarantined (alert `page`; M8 `bounds_ok` HALTs
    the books it describes), a display failure is written with `extras.validation_errors` (alert `warn`, never a
    HALT). Validation never raises here; an I/O failure does."""
    kind = short_name(kind)
    when = _pit.parse_utc(obj["decision_utc"]) if isinstance(obj.get("decision_utc"), str) else clock()
    try:
        path = write_artifact(root, kind, obj, clock)
    except ArtifactRefused as refused:
        return WriteOutcome(kind, "quarantined", refused.quarantine_path, refused.acting_failure, tuple(refused.issues),
                            RL.alert(ALERT_ACTING if refused.acting_failure else ALERT_DISPLAY, "core/ficc/macro_artifacts", when,
                                     severity="page" if refused.acting_failure else "warn"))
    issues = tuple(check_artifact(kind, obj)[1])          # the writer carries them in the written copy (extras.validation_errors)
    if issues:
        return WriteOutcome(kind, "written_with_display_errors", path, False, issues,
                            RL.alert(ALERT_DISPLAY, "core/ficc/macro_artifacts", when, severity="warn"))
    return WriteOutcome(kind, "written", path)
