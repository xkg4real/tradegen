"""Section 7 macro rules store, section 7.1 rule objects and the section 10.3 refused shapes.

Rules implemented: R-33 (rules store, DO-NOT-BUILD predicates, and the tech-fund DNB-TF-01..17 of
`do_not_build.tf_items` evaluated over the rule object and its `extras["tf"]` descriptor), R-02 rules (1), (3), (4) bounds (P2, P8),
owner decisions D1-D6 with `{ref}` resolution (T-OWNER-01), config_hash (section 7 reproducibility).
Tasks: TASK-M0-04, M0-05, M0-06, M0-14, M0-15.

The shipped store `data/macro/rules_v2.0.0.json` is read-only. An owner ruling is a governance event
(`owner_ruling`) that `load_store(path, rulings_log=...)` replays onto the registry; the store file is
never rewritten and no acting parameter is edited in place. A refusal writes nothing but its log line.
The operator order-rule store (`Rule`, `validate`, `RuleStore`) is untouched; only Issue/Report/Severity
are reused.
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from core.ficc.macro_schema import header_issues
from core.quant.instruments import header_checks
from core.rules.governance import append_event, canonical_json, iso_utc, md5_hex, read_events
from core.rules.validation import Issue, Report, Severity

SHIPPED_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "macro" / "rules_v2.0.0.json"
STORE_VERSION = "2.0.0"
STORE_AS_OF = "2026-10-02"
TOP_LEVEL_KEYS = ("version", "as_of", "read_only", "owner_decisions", "time", "calendars", "data",
                  "data_contracts", "overlay", "base_weights", "vol_target", "families", "weights_prior",
                  "prior_haircuts", "risk_layer", "annotations", "events", "fill_model", "instruments",
                  "refusal_books", "cards", "sleeves", "context_log", "breaks", "monitoring", "gate",
                  "do_not_build", "reproducibility")

KINDS = ("INVARIANT", "CONVENTION", "CARD-O", "CARD-P", "CONTEXT", "GOVERNANCE")
CARD_KINDS = ("CARD-O", "CARD-P")
FACTORS = ("overlay", "vt", "vs", "ladder", "post_rearm_cap", "none")     # brief A-3 discriminator
BASES = ("active", "total")
FAMILIES = ("momentum", "reversal", "flow", "quality", "ts_trend", "market_gross")
BOOKS = ("recommended", "specification", "forward_sim", "refusal")
ROLES = ("acting_exposure", "forward_sim", "risk_model", "context", "history")
TIMINGS = ("live", "publication", "value_proxy")
SOURCE_KINDS = ("market_price", "published_series", "derived", "implied_vol", "regime_model", "ml_classifier")
ESTIMATOR_KINDS = ("sma", "ewma", "garch", "har", "comb", "ml")
LABEL_LAYERS = ("none", "conformal")
MARKETS = ("KR", "US", "JP", "CN", "HK", "TW", "CRYPTO", "FX")
INSTRUMENT_BOOKS = ("KRX_ETF_line", "KRX_stock_book", "KOSPI200_futures", "mini_KOSPI200_futures", "CME_micro_ES",
                    "US_shares_KIS", "KRX_listed_SP500_ETF", "crypto_venue", "FX_KRX_USD_futures",
                    "FX_broker_spot", "multi_line")
TIERS = ("A", "B", "C")
CLOSED_TIERS = ("A_provisional", "pooled")
DISPOSITIONS = ("RECOMMENDATION", "BUILD_AS_INSURANCE", "INVARIANT_STEP", "SPECIFICATION_ONLY", "FORWARD_SIM",
                "REFUSAL_BOOK", "DESCRIPTIVE")
N_GATE = "max(N_clusters, N_equiv)"
HEADER_FIELDS = ("instrument_book", "notional_nav", "rebalance", "no_trade_band", "cost_bp")
STOCK_BOOKS = ("KRX_stock_book", "US_shares_KIS")          # brief A-10: US shares extend item 33
ORDER_PATH_KEYS = frozenset({"order_path", "cancel_path", "withdrawal_path", "deposit_address_path",
                             "transfer_path", "broker_adapter", "execution_adapter", "order_client"})
LABEL_SERIES = ("DISPLAY_LABEL", "REGIME_READ", "ZSCORE")   # brief A-9: label-like acting series
REGISTRY_FIELDS = frozenset({"key", "value", "default", "options", "status", "effective_from", "rationale", "refs"})
OWNER_STATUSES = ("default", "owner_set", "pending")
DECISIONS = ("D1", "D2", "D3", "D4", "D5", "D6")
ESTIMATOR_ORDER = ("sma20", "ewma094", "ewma097", "garch_t", "gjr_t", "log_har_range", "comb")


class MacroRefusal(ValueError):
    """A store, ruling or rule object the validator refuses; nothing has been written."""


# --------------------------------------------------------------------------- #
# Bound assertions shared with core/quant (P2)
# --------------------------------------------------------------------------- #
def assert_overlay(x: float) -> float:
    if not 0.5 <= x <= 1.0:
        raise ValueError(f"overlay multiplier {x!r} outside [0.5, 1.0] (P2, section 10 item 2)")
    return x


def assert_vt(x: float) -> float:
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"vt {x!r} outside [0, 1.0] (P2)")
    return x


def assert_vs(x: float) -> float:
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"vs {x!r} outside [0, 1.0] (P2)")
    return x


# --------------------------------------------------------------------------- #
# Rule objects (section 7.1)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RuleInput:
    series_id: str
    role: str
    books: tuple[str, ...] = ()
    timing: str | None = None
    source_kind: str | None = None


@dataclass(frozen=True)
class RuleObject:
    """Section 7.1 fields verbatim; `factor` says which P2 bound applies (brief A-3).

    `disposition`, `evidence` and `extras` carry the header/card fields section 7.1 reaches with
    "any field" (items 21, 22, 23/32, 24, 35): notional_nav, rebalance, no_trade_band, cost_bp, flags.
    No field has a financial default; `output_range=None` means "emits no multiplier".
    """
    rule_id: str
    kind: str
    output_range: tuple[float, float] | None = None
    exposure_basis: str | None = None
    applies_to: str | None = None
    composition: str | None = None
    books: tuple[str, ...] = ()
    inputs: tuple[RuleInput, ...] = ()
    estimator: Mapping[str, Any] | None = None
    label_layer: str | None = None
    instrument_book: str | None = None
    market: str | None = None
    card_id: str | None = None
    tier: str | None = None
    header_md5: str | None = None
    results_md5: str | None = None
    n_rule: str | None = None
    factor: str | None = None
    disposition: str | None = None
    evidence: tuple[Mapping[str, Any], ...] = ()
    extras: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RuleObject":
        d = dict(d)
        d["inputs"] = tuple(i if isinstance(i, RuleInput) else RuleInput(**{**i, "books": tuple(i.get("books", ()))})
                            for i in d.get("inputs", ()))
        d["books"] = tuple(d.get("books", ()))
        d["evidence"] = tuple(d.get("evidence", ()))
        if d.get("output_range") is not None:
            d["output_range"] = tuple(d["output_range"])
        return cls(**d)

    @property
    def is_multiplier(self) -> bool:
        return self.output_range is not None


def _walk(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """(key, value) over every nested mapping of a rule object (item 21 "any field")."""
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k), v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _walk(v, path)


def _fields(obj: RuleObject) -> dict:
    return {"estimator": obj.estimator, "evidence": obj.evidence, "extras": obj.extras,
            "inputs": [vars(i) for i in obj.inputs]}


# --------------------------------------------------------------------------- #
# DO-NOT-BUILD labels (section 10.1, section 7 do_not_build)
# --------------------------------------------------------------------------- #
_SHIPPED_DNB: dict | None = None


def _shipped_dnb() -> dict:
    global _SHIPPED_DNB
    if _SHIPPED_DNB is None:
        with open(SHIPPED_STORE_PATH, encoding="utf-8") as fh:
            _SHIPPED_DNB = json.load(fh)["do_not_build"]
    return _SHIPPED_DNB


def dnb_item(n: int | str, dnb: Mapping | None = None) -> dict:
    """{label, basis, variants} of a section 10 item; labels stay as shipped (TASK-M0-15 is REFDATA)."""
    raw = (dnb or _shipped_dnb())["items"][str(n)]
    variants = raw if isinstance(raw, Mapping) else {"item": raw}
    parsed = {}
    for name, lab in variants.items():
        head, _, basis = lab.rpartition("_")
        parsed[name] = {"label": head or lab, "basis": basis if head else None, "raw": lab}
    first = next(iter(parsed.values()))
    return {"item": str(n), "label": first["label"], "basis": first["basis"], "variants": parsed}


def _label_text(items: Mapping, n: int, variant: str | None) -> str:
    raw = items[str(n)]
    if not isinstance(raw, Mapping):
        return f"{n} ({raw})"
    if variant in raw:
        return f"{n} ({variant}: {raw[variant]})"
    return f"{n} ({', '.join(f'{k}: {v}' for k, v in raw.items())})"


# --------------------------------------------------------------------------- #
# Rule-object validation (section 7.1, R-02 bounds, P8) and the 17 refused shapes (section 10.3)
# --------------------------------------------------------------------------- #
def _field_issues(obj: RuleObject) -> list[Issue]:
    err: list[Issue] = []

    def e(f: str, m: str) -> None:
        err.append(Issue(f, f"refused {obj.rule_id}: {m}", Severity.ERROR))

    if obj.kind not in KINDS:
        e("kind", f"kind {obj.kind!r} not in {KINDS}")
    rng = obj.output_range
    if rng is not None:
        if (len(rng) != 2 or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in rng)
                or rng[0] > rng[1]):
            e("output_range", "output_range must be [lo, hi] with lo <= hi")
        if obj.factor not in FACTORS or obj.factor == "none":
            e("factor", "a multiplier must declare factor in {overlay, vt, vs, ladder, post_rearm_cap}")
        if obj.exposure_basis not in BASES:            # P8: every multiplier declares its basis
            e("exposure_basis", "every multiplier declares exposure_basis in {active, total} (P8, T-BASIS-01)")
        if obj.factor == "vt" and obj.applies_to != "market_gross":
            e("applies_to", "vt applies to market_gross only; never to a family sleeve or ts_trend (P8, T-BASIS-01)")
        if obj.applies_to == "ts_trend":
            e("applies_to", "no multiplier on ts_trend: R-14 is exempt from overlays (T-BASIS-01)")
        if obj.applies_to == "market_gross" and obj.exposure_basis == "active":
            e("exposure_basis", "a market_gross multiplier scales total exposure (section 3.3)")
        if obj.applies_to in FAMILIES and obj.applies_to not in ("market_gross", "ts_trend") and obj.exposure_basis == "total":
            e("exposure_basis", "a family multiplier scales active exposure (section 3.3)")
    elif obj.factor not in (None, "none"):
        e("factor", "factor given but output_range is null")
    if obj.applies_to is not None and obj.applies_to not in FAMILIES:
        e("applies_to", f"applies_to {obj.applies_to!r} not in {FAMILIES}")
    for b in obj.books:
        if b not in BOOKS:
            e("books", f"book {b!r} not in {BOOKS}")
    for i, inp in enumerate(obj.inputs):
        if inp.role not in ROLES:
            e(f"inputs[{i}].role", f"role {inp.role!r} not in {ROLES}")
        if inp.timing is not None and inp.timing not in TIMINGS:
            e(f"inputs[{i}].timing", f"timing {inp.timing!r} not in {TIMINGS}")
        if inp.source_kind is not None and inp.source_kind not in SOURCE_KINDS:
            e(f"inputs[{i}].source_kind", f"source_kind {inp.source_kind!r} not in {SOURCE_KINDS}")
    if obj.estimator is not None:
        if not isinstance(obj.estimator, Mapping) or obj.estimator.get("kind") not in ESTIMATOR_KINDS:
            e("estimator", f"estimator needs {{name, kind}} with kind in {ESTIMATOR_KINDS}")
    if obj.label_layer is not None and obj.label_layer not in LABEL_LAYERS:
        e("label_layer", f"label_layer {obj.label_layer!r} not in {LABEL_LAYERS}")
    if obj.market is not None and obj.market not in MARKETS:
        e("market", f"market {obj.market!r} not in {MARKETS}")
    if obj.instrument_book is not None and obj.instrument_book not in INSTRUMENT_BOOKS:
        e("instrument_book", f"instrument_book {obj.instrument_book!r} not in section 6.5 enum")
    if obj.tier is not None and obj.tier not in TIERS and obj.tier not in CLOSED_TIERS:
        e("tier", f"tier {obj.tier!r} not in {TIERS}")
    if obj.disposition is not None and obj.disposition not in DISPOSITIONS:
        e("disposition", f"disposition {obj.disposition!r} not in {DISPOSITIONS}")
    return err


def dnb_violations(obj: RuleObject, *, previous: RuleObject | None = None,
                   verdicts: Mapping[str, str] | None = None, revision: Mapping[str, Any] | None = None,
                   dnb: Mapping | None = None) -> list[Issue]:
    """One predicate per `do_not_build.refused_shapes` key; each Issue names the section 10 item and label."""
    dnb = dnb or _shipped_dnb()
    items, shapes = dnb["items"], dnb["refused_shapes"]
    verdicts = verdicts or {}
    out: list[Issue] = []

    def refuse(fld: str, shape: str, detail: str, variants: Mapping[int, str] | None = None) -> None:
        ids = shapes[shape]
        ids = ids if isinstance(ids, list) else [ids]
        named = ", ".join(_label_text(items, n, (variants or {}).get(n)) for n in ids)
        out.append(Issue(fld, f"refused {obj.rule_id}: section 10 item{'s' if len(ids) > 1 else ''} {named} "
                              f"[{shape}]: {detail}", Severity.ERROR))

    rid = obj.rule_id
    rng = obj.output_range
    fac = obj.factor
    acting = [i for i in obj.inputs if i.role == "acting_exposure"]
    est = obj.estimator if isinstance(obj.estimator, Mapping) else {}

    # 1 order_path_or_broker_adapter (21)
    hits = [k for k, _ in _walk(_fields(obj)) if k in ORDER_PATH_KEYS]
    if hits or ("read_only" in obj.extras and obj.extras["read_only"] is not True):
        refuse("extras", "order_path_or_broker_adapter", f"order/transfer path or broker adapter field {hits or ['read_only']}")
    # 2 multiplier_weight_or_cap_above_1 (2, 8): the P2 bounds, Tier C
    if rng is not None and len(rng) == 2:
        lo, hi = rng
        if hi > 1.0:
            refuse("output_range", "multiplier_weight_or_cap_above_1", f"hi {hi!r} > 1.0 is Tier C (gate.tiers.C.allowed false)")
        if fac == "overlay" and not (0.5 <= lo <= hi <= 1.0):
            refuse("output_range", "multiplier_weight_or_cap_above_1", f"overlay range {list(rng)} outside [0.5, 1.0]")
        if fac in ("vt", "vs") and not (0.0 <= lo <= hi <= 1.0):
            refuse("output_range", "multiplier_weight_or_cap_above_1", f"{fac} range {list(rng)} outside [0, 1.0]")
        if fac in ("ladder", "post_rearm_cap") and not {lo, hi} <= {0.5, 1.0}:
            refuse("output_range", "multiplier_weight_or_cap_above_1", f"{fac} values {list(rng)} not in {{0.5, 1.0}}")
    if obj.tier == "C":
        refuse("tier", "multiplier_weight_or_cap_above_1", "tier C is not allowed (gate.tiers.C)")
    for k, v in _walk(obj.extras):
        if k in ("weight", "cap", "multiplier") and isinstance(v, (int, float)) and not isinstance(v, bool) and v > 1.0:
            refuse(f"extras.{k}", "multiplier_weight_or_cap_above_1", f"{k} {v!r} > 1.0")
    # 3 composition_not_min (31)
    if rng is not None and obj.composition != "min":
        refuse("composition", "composition_not_min", f"composition {obj.composition!r}; de-risk factors compose by min() only")
    # 4 regime_model_source_acting_or_displayed (11, 24, 27)
    for i, inp in enumerate(obj.inputs):
        if inp.source_kind == "regime_model":
            refuse(f"inputs[{i}].source_kind", "regime_model_source_acting_or_displayed",
                   f"{inp.series_id} is a regime-model state (role {inp.role}); never acting, never displayed (P19)",
                   {11: "smoothed_regime_probabilities"})
    # 5 smoothed_or_forward_looking_label (24)
    if obj.extras.get("smoothed") is True or obj.extras.get("forward_looking") is True:
        refuse("extras", "smoothed_or_forward_looking_label", "smoothed or forward-looking label; R-06 labels are causal and display only")
    for i, inp in enumerate(acting):
        if any(tag in inp.series_id.upper() for tag in LABEL_SERIES):
            refuse(f"inputs[{i}].series_id", "smoothed_or_forward_looking_label",
                   f"{inp.series_id}: a display label, the regime read or a sheet z-score may not gate exposure")
    # 6 ml_classifier_estimator_gate_or_label (11, 29)
    if est.get("kind") == "ml":
        refuse("estimator", "ml_classifier_estimator_gate_or_label", f"estimator {est.get('name')!r} of kind ml",
               {11: "11a_ml_vol_state_classifiers"})
    for i, inp in enumerate(obj.inputs):
        if inp.source_kind == "ml_classifier":
            refuse(f"inputs[{i}].source_kind", "ml_classifier_estimator_gate_or_label",
                   f"{inp.series_id} is an ML classifier output", {11: "11a_ml_vol_state_classifiers"})
    # 7 conformal_label_layer (28)
    if obj.label_layer == "conformal":
        refuse("label_layer", "conformal_label_layer", "Mondrian conformal layer on the display labels")
    # 8 sizing_estimator_max_over_implied (30)
    if fac in ("vt", "vs"):
        implied = [i.series_id for i in obj.inputs if i.source_kind == "implied_vol"]
        name = str(est.get("name", ""))
        if (est.get("combine") == "max" and implied) or ("max(" in name and "implied" in name.lower()):
            refuse("estimator", "sizing_estimator_max_over_implied", f"max() over implied vol {implied or name}")
        elif any(i.source_kind == "implied_vol" for i in acting) and est.get("kind") != "har":
            refuse("inputs", "sizing_estimator_max_over_implied",
                   f"implied vol {implied} sizes exposure outside HAR-IV (R-30)")
    # 9 estimator_change_outside_r30_revision (25)
    if previous is not None and previous.estimator != obj.estimator and (revision or {}).get("kind") != "r30_counted_revision":
        refuse("estimator", "estimator_change_outside_r30_revision",
               f"estimator {previous.estimator!r} -> {obj.estimator!r} without an R-30 counted revision")
    # 10 header_edit_after_results_md5 (23, 32)
    if previous is not None and previous.results_md5 and previous.card_id == obj.card_id:
        before = {"instrument_book": previous.instrument_book, **{k: previous.extras.get(k) for k in HEADER_FIELDS[1:]}}
        after = {"instrument_book": obj.instrument_book, **{k: obj.extras.get(k) for k in HEADER_FIELDS[1:]}}
        changed = [k for k in HEADER_FIELDS if before[k] != after[k]]
        if changed:
            refuse("card_id", "header_edit_after_results_md5",
                   f"{changed} edited after results_md5 {previous.results_md5}: a new card id is required")
    # 11 krx_stock_book_on_market_gross_scalar (33)
    if obj.instrument_book in STOCK_BOOKS and (obj.applies_to == "market_gross" or obj.exposure_basis == "total"):
        refuse("instrument_book", "krx_stock_book_on_market_gross_scalar",
               f"{obj.instrument_book} as a market-gross scalar (instruments.market_scalar_on_stock_book refused)")
    # 12 pooled_or_a_provisional_tier_after_results (34)
    if obj.tier in CLOSED_TIERS or (previous is not None and previous.results_md5 and obj.extras.get("pooled") and not previous.extras.get("pooled")):
        refuse("tier", "pooled_or_a_provisional_tier_after_results",
               f"tier {obj.tier!r} / pooled route: gate.tiers.A_provisional is closed")
    # 13 forward_record_cited_as_validation (35)
    for i, ev in enumerate(obj.evidence):
        if ev.get("kind") in ("forward_record", "forward_sim") and ev.get("use") == "validation":
            refuse(f"evidence[{i}]", "forward_record_cited_as_validation",
                   "a forward record can demote, never validate (P14)")
    val = obj.extras.get("validation")
    if isinstance(val, str) and ("forward_sim:" in val or "forward record" in val.lower()):
        refuse("extras.validation", "forward_record_cited_as_validation", f"{val!r} cites a forward book as validation")
    # 14 kish_or_other_n_eff_rule (36)
    if (obj.n_rule is not None and obj.n_rule != N_GATE) or (obj.kind in CARD_KINDS and obj.n_rule != N_GATE):
        refuse("n_rule", "kish_or_other_n_eff_rule", f"n_rule {obj.n_rule!r}; gate.step3.n_gate is {N_GATE!r}")
    kish = [k for k, v in _walk(_fields(obj)) if str(k).lower().startswith("kish") or (isinstance(v, str) and v.lower().startswith("kish"))]
    if kish:
        refuse("extras", "kish_or_other_n_eff_rule", f"Kish design effect named by {kish}")
    # 15 r28_instance_market_kr (37)
    if (rid.startswith("R-28") or obj.extras.get("family") == "R-28") and obj.market == "KR":
        refuse("market", "r28_instance_market_kr", "a KOSPI trend card never acts; Korea trend state is context only")
    # 16 recommended_book_reads_non_pass_multiplier (22)
    if "recommended" in obj.books:
        if obj.books and ({"forward_sim", "refusal"} & set(obj.books)):
            refuse("books", "recommended_book_reads_non_pass_multiplier", "recommended listed with a forward_sim or refusal book")
        if obj.kind in CARD_KINDS and verdicts.get(obj.card_id or "", "NOT_RUN") != "PASS" and not (
                rid.startswith("R-31") and obj.disposition == "INVARIANT_STEP"):
            refuse("books", "recommended_book_reads_non_pass_multiplier",
                   f"card {obj.card_id} verdict {verdicts.get(obj.card_id or '', 'NOT_RUN')}: only PASS reaches the recommended book (P7)")
    if obj.disposition == "INVARIANT_STEP" and not rid.startswith("R-31"):
        refuse("disposition", "recommended_book_reads_non_pass_multiplier", "INVARIANT_STEP is reserved for R-31 steps")
    # 17 value_timed_or_provisional_acting_input (19, 26)
    for i, inp in enumerate(obj.inputs):
        if inp.role == "acting_exposure" and (inp.timing == "value_proxy" or obj.extras.get("provisional") is True):
            refuse(f"inputs[{i}].timing", "value_timed_or_provisional_acting_input",
                   f"{inp.series_id} is value-timed or provisional; an acting input is publication-timed (P5)")
    # tech-fund DNB-TF-01..17 (`do_not_build.tf_items`; R3 gives no label, so each names its proposed one)
    for item in dnb.get("tf_items", ()):
        pred = item["predicate"]
        if (pred.get("scope") and not _tf_eval(pred["scope"], obj)) or any(_tf_eval(a, obj) for a in item.get("allow_list", ())):
            continue
        missing = [p for p in pred.get("require", ()) if not _tf_eval({"exists": p}, obj)]
        if missing or pred.get("when") is None or _tf_eval(pred["when"], obj):
            lab = item["label_proposed"]
            lab = ", ".join(f"{k}: {v}" for k, v in lab.items()) if isinstance(lab, Mapping) else lab
            why = f"cannot be evaluated, {missing} missing (fail closed)" if missing else item["text"]
            out.append(Issue(f"tf_items.{item['id']}", f"refused {rid}: tech-fund DO-NOT-BUILD {item['id']} "
                                                       f"(proposed label {lab}) [{item['id']}]: {why}", Severity.ERROR))
    return out


_ABSENT = object()


def _tf_get(obj: RuleObject, path: str, inp: Mapping | None) -> Any:
    """A rule-object field, `tf.<name>` from `extras["tf"]` (the tech-fund descriptor), or an input's field."""
    if inp is not None:
        return inp.get(path, _ABSENT)
    if path == "tf" or path.startswith("tf."):
        tf = obj.extras.get("tf", _ABSENT) if isinstance(obj.extras, Mapping) else _ABSENT
        return tf if path == "tf" or not isinstance(tf, Mapping) else tf.get(path[3:], _ABSENT)
    v = getattr(obj, path, _ABSENT)
    return list(v) if isinstance(v, tuple) else v


def _tf_eval(expr: Mapping, obj: RuleObject, inp: Mapping | None = None) -> bool:
    """The tf_items predicate language: all / any / not / any_input / exists / {path, op}. An absent or null
    field never matches a leaf; a store that names an unknown op is refused."""
    if "all" in expr:
        return all(_tf_eval(e, obj, inp) for e in expr["all"])
    if "any" in expr:
        return any(_tf_eval(e, obj, inp) for e in expr["any"])
    if "not" in expr:
        return not _tf_eval(expr["not"], obj, inp)
    if "any_input" in expr:
        return any(_tf_eval(expr["any_input"], obj, vars(i)) for i in obj.inputs)
    if "exists" in expr:
        return _tf_get(obj, expr["exists"], inp) not in (_ABSENT, None)
    v = _tf_get(obj, expr["path"], inp)
    (op, ref), = ((k, x) for k, x in expr.items() if k != "path")
    if v is _ABSENT or v is None:
        return False
    if op == "eq":
        return v == ref and isinstance(v, bool) == isinstance(ref, bool)
    if op == "in":
        return v in ref
    if op == "overlaps":
        return bool(set(v if isinstance(v, (list, tuple, set)) else [v]) & set(ref))
    if op in ("le", "lt", "ge", "gt"):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        return {"le": v <= ref, "lt": v < ref, "ge": v >= ref, "gt": v > ref}[op]
    raise MacroRefusal(f"do_not_build.tf_items: unknown predicate op {op!r}")


def validate_rule_object(obj: RuleObject, *, previous: RuleObject | None = None,
                         verdicts: Mapping[str, str] | None = None, revision: Mapping[str, Any] | None = None,
                         dnb: Mapping | None = None) -> Report:
    """All issues at once; every ERROR names the rule and, for a section 10 shape, the item and label."""
    return Report(tuple(_field_issues(obj) + dnb_violations(obj, previous=previous, verdicts=verdicts,
                                                            revision=revision, dnb=dnb)))


def rule_of_header(rule: "RuleObject | Mapping[str, Any]", header: Mapping[str, Any]) -> RuleObject:
    """The section 7.1 object a card header instantiates: the rule's fields under the header's book, card id,
    tier and header_md5, with the item 23/32 header fields carried in `extras`."""
    base = rule if isinstance(rule, RuleObject) else RuleObject.from_dict(rule)
    extras = {**base.extras, **{k: header[k] for k in HEADER_FIELDS[1:] if k in header}}
    over = {k: header[k] for k in ("instrument_book", "card_id", "tier", "header_md5") if header.get(k) is not None}
    return replace(base, extras=extras, **over)


def validate_card_header(header: Mapping[str, Any], store: "MacroStore", *, rule: "RuleObject | Mapping[str, Any] | None",
                         previous: RuleObject | None = None, verdicts: Mapping[str, str] | None = None,
                         committed_md5: str | None = None, contract_notional_krw: float | None = None,
                         acting_long_sample: bool = True) -> Report:
    """Commit-time header check (section 8.1.3 step 4; T-BOOK-01, T-OWNER-01): the schema and the pure header
    rules (core.ficc.macro_schema.header_issues), the twelve R-26 checks (core.quant.instruments.header_checks),
    the store's gate.card_header_required list, owner_decisions at commit, then the section 10.3 shapes on the
    rule object the header instantiates. `rule` is the section 7.1 object of header['rule_id']; None fails closed.
    Nothing is written; M7 commits only on `report.ok`."""
    header = dict(header)
    issues: list[Issue] = []

    def e(fld: str, msg: str) -> None:
        issues.append(Issue(fld, msg, Severity.ERROR))

    def store_get(key: str) -> Any:
        try:
            return store.get(key)
        except KeyError:
            return None

    for msg in header_issues(header, committed_md5=committed_md5, seed_study=store_get("reproducibility.seed_study"),
                             acting_long_sample=acting_long_sample):
        e(msg.split(":", 1)[0].strip("/") or "header", msg)
    for fld in store_get("gate.card_header_required") or ():
        if header.get(fld) is None:
            e(fld, f"gate.card_header_required: {fld} missing or null")
    for key, value in (header.get("owner_decisions") or {}).items():
        if store_get(key) != value:
            e("owner_decisions", f"{key} = {value!r} differs from the store value {store_get(key)!r} at commit (T-OWNER-01)")
    try:
        obj = rule_of_header(rule, header) if rule is not None else None
    except (TypeError, ValueError) as exc:
        e("rule", f"rule object for {header.get('rule_id')!r} incomplete: {exc}")
        obj = None
    for msg in header_checks(header, store_get, rule=vars(obj) if obj else None, contract_notional_krw=contract_notional_krw):
        e(msg.split(" ", 2)[1].rstrip(":"), msg)          # "<n> <field>: ..." -> field
    if obj is not None:
        issues += validate_rule_object(obj, previous=previous, verdicts=verdicts).errors
    return Report(tuple(issues))


def log_refusal(path: Path, obj: RuleObject, report: Report, clock: Callable[[], datetime]) -> int:
    """Append one JSON line per refused object to the refusal log; nothing else is written.

    Returns the number of errors logged (0 when the report is ok and nothing was appended)."""
    if report.ok:
        return 0
    row = {"utc": iso_utc(clock()), "rule_id": obj.rule_id, "card_id": obj.card_id,
           "refusals": [{"field": i.field, "message": i.message} for i in report.errors]}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(canonical_json(row).encode("utf-8") + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    return len(report.errors)


# --------------------------------------------------------------------------- #
# Store: dotted paths, {ref} resolution, owner registry, block bounds, config_hash
# --------------------------------------------------------------------------- #
def _get_path(doc: Mapping, dotted: str) -> Any:
    node: Any = doc
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def _set_path(doc: dict, dotted: str, value: Any) -> None:
    *head, last = dotted.split(".")
    node = doc
    for part in head:
        node = node[part]
    node[last] = value


def _is_scalar(v: Any) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def _ref_sites(node: Any, path: str = "") -> Iterator[tuple[str, dict]]:
    if isinstance(node, dict):
        if "ref" in node:
            yield path, node
        else:
            for k, v in node.items():
                yield from _ref_sites(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _ref_sites(v, f"{path}[{i}]")


def resolve_refs(doc: Mapping) -> dict:
    """Deep copy with every `{ref: <dotted key>}` replaced by the scalar at that key; any other shape refused."""
    out = copy.deepcopy(dict(doc))
    for site, ref in _ref_sites(out):
        if set(ref) != {"ref"} or not isinstance(ref["ref"], str):
            raise MacroRefusal(f"{site}: a ref object has exactly one key 'ref' (section 7, T-OWNER-01); got {sorted(ref)}")
        try:
            target = _get_path(out, ref["ref"])
        except KeyError:
            raise MacroRefusal(f"{site}: ref target {ref['ref']!r} does not exist") from None
        if not _is_scalar(target):
            raise MacroRefusal(f"{site}: ref target {ref['ref']!r} must hold a plain scalar")
        _set_site(out, site, target)
    return out


def _set_site(doc: dict, site: str, value: Any) -> None:
    """Set a value at a site path that may index lists (`a.b[2].c`)."""
    node: Any = doc
    parts = site.replace("]", "").replace("[", ".").split(".")
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    last = parts[-1]
    if isinstance(node, list):
        node[int(last)] = value
    else:
        node[last] = value


class MacroStore:
    """The loaded section 7 document; read-only. `get` answers resolved values, `raw` the stored ones."""

    def __init__(self, doc: Mapping, path: Path | None = None):
        self._doc = copy.deepcopy(dict(doc))
        self._resolved = resolve_refs(self._doc)
        self.path = Path(path) if path is not None else None

    def get(self, dotted: str) -> Any:
        """Resolved value at a dotted key; KeyError when absent (no default, ever: section 7 has no financial defaults)."""
        return copy.deepcopy(_get_path(self._resolved, dotted))

    def raw(self, dotted: str) -> Any:
        return copy.deepcopy(_get_path(self._doc, dotted))

    def resolve_refs(self) -> dict:
        return copy.deepcopy(self._resolved)

    @property
    def doc(self) -> dict:
        return copy.deepcopy(self._doc)

    @property
    def config_hash(self) -> str:
        """md5 of the canonical JSON of the acting blocks: gate.package and history excluded."""
        d = copy.deepcopy(self._resolved)
        d.pop("history", None)
        d.get("gate", {}).pop("package", None)
        return md5_hex(canonical_json(d))

    @property
    def do_not_build(self) -> dict:
        return self.get("do_not_build")


def _admissible(d: str, entry: Mapping, value: Any) -> str | None:
    if d == "D4":   # options: [tighten_only_le_0p10] -- the owner may only tighten
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 < value <= 0.10:
            return f"{d}: value {value!r} must satisfy 0 < value <= 0.10 (tighten only)"
        return None
    if value not in entry["options"]:
        return f"{d}: value {value!r} not in options {entry['options']}"
    return None


def _owner_issues(doc: Mapping) -> list[str]:
    errs: list[str] = []
    registry = doc.get("owner_decisions")
    if not isinstance(registry, Mapping):
        return ["owner_decisions block missing"]
    for d in DECISIONS:
        entry = registry.get(d)
        if not isinstance(entry, Mapping):
            errs.append(f"owner_decisions.{d} missing")
            continue
        if set(entry) != REGISTRY_FIELDS:
            errs.append(f"owner_decisions.{d}: fields must be exactly {sorted(REGISTRY_FIELDS)}")
            continue
        if entry["status"] not in OWNER_STATUSES:
            errs.append(f"owner_decisions.{d}: status {entry['status']!r} not in {OWNER_STATUSES}")
        try:
            canon = _get_path(doc, entry["key"])
        except KeyError:
            errs.append(f"owner_decisions.{d}: canonical key {entry['key']!r} does not exist")
            continue
        if not _is_scalar(canon):
            errs.append(f"owner_decisions.{d}: canonical key {entry['key']!r} must hold a plain scalar")
        elif canon != entry["value"] or type(canon) is not type(entry["value"]):
            errs.append(f"owner_decisions.{d}: canonical key {entry['key']!r} holds {canon!r}, registry value {entry['value']!r}")
        for p in entry["refs"]:
            try:
                x = _get_path(doc, p)
            except KeyError:
                errs.append(f"owner_decisions.{d}: ref path {p!r} does not exist")
                continue
            if x != {"ref": entry["key"]}:
                what = "literal copy that differs from" if _is_scalar(x) and x != entry["value"] else "literal copy of"
                errs.append(f"owner_decisions.{d}: {p} is a {what} its canonical key {entry['key']!r}; "
                            f"only {{ref: {entry['key']}}} is allowed (T-OWNER-01)")
        problem = _admissible(d, entry, entry["value"])
        if problem:
            errs.append(problem)
    return errs


def _in_unit(lo: float, hi: float):
    return lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def _is(expected):
    return lambda v: v == expected and type(v) is type(expected)


# (path, predicate, message): the only store paths bound-checked (brief B3.3); never a name pattern.
_BLOCK_CHECKS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("overlay.floor", _is(0.5), "overlay floor is 0.5 (P2)"),
    ("overlay.cap", _is(1.0), "overlay cap is 1.0 (P2)"),
    ("overlay.combine", _is("min"), "combine must be min (section 10 item 31)"),
    ("overlay.floor_vs_vt_outside_halted", _is(0.5), "composed >= 0.5 x vt outside HALTED (T-CAP-02)"),
    ("overlay.zero_only_in", _is(["risk_layer", "book_HALTED"]), "0x comes only from the risk layer and HALTED"),
    ("vol_target.KR.cap", lambda v: _in_unit(0, 1)(v) and v > 0, "vol-target cap in (0, 1.0] (section 10 item 2)"),
    ("vol_target.US.cap", lambda v: _in_unit(0, 1)(v) and v > 0, "vol-target cap in (0, 1.0] (section 10 item 2)"),
    ("vol_target.other_markets.cap", lambda v: _in_unit(0, 1)(v) and v > 0, "vol-target cap in (0, 1.0]"),
    ("vol_target.KR.cap_permanent", _is(True), "cap 1.0 is permanent"),
    ("vol_target.US.cap_permanent", _is(True), "cap 1.0 is permanent"),
    ("vol_target.KR.exposure_basis", _is("total"), "vt scales total exposure (P8)"),
    ("vol_target.US.exposure_basis", _is("total"), "vt scales total exposure (P8)"),
    ("families.momentum.own_vol_scale.floor", _in_unit(0, 1), "vs floor in [0, 1.0]"),
    ("families.momentum.own_vol_scale.cap", _in_unit(0, 1), "vs cap in [0, 1.0]"),
    ("families.momentum.own_vol_scale.exposure_basis", _is("active"), "vs scales active exposure (P8)"),
    ("families.momentum.dm_gate.multiplier", _in_unit(0.5, 1), "overlay multiplier in [0.5, 1.0]"),
    ("families.momentum.dm_gate.exposure_basis", _is("active"), "dm_gate scales active exposure (P8)"),
    ("families.momentum.dm_gate.books", _is(["specification"]), "R-04 is specification book only"),
    ("families.reversal.overlay", _is("fixed_1.0"), "reversal overlay fixed at 1.0"),
    ("families.quality.overlay", _is("fixed_1.0"), "quality overlay fixed at 1.0"),
    ("families.flow.overlay", _is("fixed_1.0"), "flow overlay fixed at 1.0"),
    ("families.ts_trend.cap", _in_unit(0, 1), "ts_trend cap <= 1.0"),
    ("families.ts_trend.overlay_exempt", _is(True), "R-14 is exempt from overlays"),
    ("refusal_books.S1_krw.multiplier", _in_unit(0.5, 1), "overlay multiplier in [0.5, 1.0]"),
    ("refusal_books.S2_rates.multiplier", _in_unit(0.5, 1), "overlay multiplier in [0.5, 1.0]"),
    ("refusal_books.S1_krw.verdict", _is("REJECT"), "refusal book carries REJECT"),
    ("refusal_books.S2_rates.verdict", _is("REJECT"), "refusal book carries REJECT"),
    ("refusal_books.S1_krw.regate_queue", _is(False), "off the re-gate queue"),
    ("refusal_books.S2_rates.regate_queue", _is(False), "off the re-gate queue"),
    ("cards.R-28_trend_axis.rule.multiplier_below", _in_unit(0.5, 1), "overlay multiplier in [0.5, 1.0]"),
    ("cards.R-28_trend_axis.rule.multiplier_above", _in_unit(0.5, 1), "overlay multiplier in [0.5, 1.0]"),
    ("cards.R-28_trend_axis.rule.composition", _is("min"), "composition min (item 31)"),
    ("cards.R-28_trend_axis.rule.exposure_basis", _is("total"), "R-28 scales total exposure"),
    ("cards.R-29_US_FUT.rule.cap", _in_unit(0, 1), "vt cap <= 1.0"),
    ("cards.R-29_US_FUT.rule.exposure_basis", _is("total"), "R-29 scales total exposure"),
    ("cards.R-31_step_down.steps", lambda v: isinstance(v, list) and all(s.get("mult") in (0.5, 1.0) for s in v),
     "ladder steps multiply by 0.5 or 1.0 only"),
    ("cards.R-31_step_down.composition", _is("min"), "composition min (item 31)"),
    ("risk_layer.drawdown.hard_stop.post_rearm_cap", lambda v: v in (0.5, 1.0), "post_rearm_cap in {0.5, 1.0}"),
    ("risk_layer.drawdown.hard_stop.post_rearm_cap_in_min", _is(True), "post_rearm_cap enters min()"),
    ("risk_layer.drawdown.composition", _is("min"), "composition min (item 31)"),
    ("gate.tiers.B.bounds", _is([0.5, 1.0]), "tier B bounds [0.5, 1.0]"),
    ("gate.tiers.C.allowed", _is(False), "tier C is refused (section 10 item 2)"),
    # block-level DO-NOT-BUILD (brief B3.5)
    ("gate.step3.n_gate", _is(N_GATE), "section 10 item 36: n_gate is max(N_clusters, N_equiv)"),
    ("gate.step3.forbidden", lambda v: {"kish_design_effect", "revision_count_as_N"} <= set(v), "section 10 item 36"),
    ("gate.tiers.A_provisional", _is("closed"), "section 10 item 34: A_provisional closed"),
    ("cards.R-28_trend_axis.markets_refused", lambda v: "KR" in v, "section 10 item 37: R-28 refuses KR"),
    ("instruments.market_scalar_on_stock_book", _is("refused"), "section 10 item 33"),
    ("instruments.cost_floor.lower_than_table", _is("forbidden"), "section 10 item 23: costs never lowered"),
    ("gate.costs", _is("read_from_gate"), "costs live in the gate's code, never in the store (P10)"),
    ("monitoring.forward_record_can_raise_verdict", _is(False), "section 10 item 35 / P14"),
    ("breaks.bocpd.log_only", _is(True), "section 10 item 27: BOCPD research log only"),
    ("breaks.bocpd.displayed", _is(False), "section 10 item 27: BOCPD never displayed"),
    ("vol_target.display_labels.filtered_only", _is(True), "section 10 item 24: labels causal"),
    ("vol_target.display_labels.acts", _is(False), "section 10 item 24: labels never act"),
    ("vol_target.logged_alt_estimators", lambda v: not any("max(" in str(x) and "implied" in str(x) for x in v),
     "section 10 item 30: max(sma20, implied) retired"),
    ("vol_target.estimator_gate.stage3.complexity_order", lambda v: set(v) <= set(ESTIMATOR_ORDER),
     "section 10 items 11, 29: no ML estimator in the R-30 race"),
    ("do_not_build.labels", _is(["harm", "null", "inconclusive"]), "label vocabulary"),
    ("do_not_build.tf_items", lambda v: isinstance(v, list), "tech-fund items placeholder is a list"),
    ("gate.package.status", lambda v: v in ("NOT_FROZEN", "FROZEN"), "gate.package.status"),
)

_SHAPE_KEYS = ("order_path_or_broker_adapter", "multiplier_weight_or_cap_above_1", "composition_not_min",
               "regime_model_source_acting_or_displayed", "smoothed_or_forward_looking_label",
               "ml_classifier_estimator_gate_or_label", "conformal_label_layer", "sizing_estimator_max_over_implied",
               "estimator_change_outside_r30_revision", "header_edit_after_results_md5",
               "krx_stock_book_on_market_gross_scalar", "pooled_or_a_provisional_tier_after_results",
               "forward_record_cited_as_validation", "kish_or_other_n_eff_rule", "r28_instance_market_kr",
               "recommended_book_reads_non_pass_multiplier", "value_timed_or_provisional_acting_input")


def _dnb_block_issues(doc: Mapping) -> list[str]:
    errs: list[str] = []
    try:
        items = _get_path(doc, "do_not_build.items")
        shapes = _get_path(doc, "do_not_build.refused_shapes")
    except KeyError as exc:
        return [f"do_not_build block incomplete: {exc}"]
    if set(items) != {str(n) for n in range(1, 38)}:
        errs.append("do_not_build.items must be keyed '1'..'37'")

    def labelled(v: str) -> bool:
        head, _, basis = v.rpartition("_")
        return head in ("harm", "null", "inconclusive") and basis in ("B", "E", "G")
    for n, v in items.items():
        variants = v if isinstance(v, Mapping) else {"item": v}
        for name, lab in variants.items():
            ok = labelled(lab) or (n == "11" and name == "11b_range_log_har" and lab == "admitted") or \
                 (n == "27" and name == "prohibition" and lab == "binding_red_line_E1")
            if not ok:
                errs.append(f"do_not_build.items.{n}.{name}: {lab!r} is not a harm/null/inconclusive label")
    if not ({"11a_ml_vol_state_classifiers", "11b_range_log_har"} <= set(items.get("11", {}) if isinstance(items.get("11"), Mapping) else ())):
        errs.append("do_not_build.items.11 must be split into 11a (prohibited) and 11b (admitted)")
    if set(shapes) != set(_SHAPE_KEYS):
        errs.append(f"do_not_build.refused_shapes must be exactly the 17 section 10.3 keys; got {sorted(shapes)}")
    return errs


def validate_store_doc(doc: Mapping) -> list[str]:
    """Every refusal of the document at once (empty = valid). Order: header, owner registry, refs, blocks."""
    errs: list[str] = []
    if doc.get("version") != STORE_VERSION:
        errs.append(f"version must be {STORE_VERSION!r}")
    if doc.get("as_of") != STORE_AS_OF:
        errs.append(f"as_of must be {STORE_AS_OF!r}")
    if doc.get("read_only") is not True:
        errs.append("read_only must be true (P0)")
    missing = [k for k in TOP_LEVEL_KEYS if k not in doc]
    if missing:
        errs.append(f"missing section 7 blocks {missing}")
        return errs
    errs += _owner_issues(doc)
    try:
        resolve_refs(doc)
    except MacroRefusal as exc:
        errs.append(str(exc))
    for path, pred, msg in _BLOCK_CHECKS:
        try:
            v = _get_path(doc, path)
        except KeyError:
            errs.append(f"{path}: missing ({msg})")
            continue
        if not pred(v):
            errs.append(f"{path}: {v!r} refused: {msg}")
    errs += _dnb_block_issues(doc)
    return errs


def _replay_rulings(doc: dict, log_path: Path) -> dict:
    """Apply every `owner_ruling` event of an intact governance log to the registry and its canonical key."""
    registry = doc["owner_decisions"]
    by_key = {e["key"]: d for d, e in registry.items() if isinstance(e, Mapping) and "key" in e}
    for ev in read_events(log_path):
        if ev.get("kind") != "owner_ruling":
            continue
        d = by_key.get(ev.get("key"))
        if d is None:
            raise MacroRefusal(f"owner_ruling event {ev.get('event_id')} names unknown key {ev.get('key')!r}")
        entry = registry[d]
        entry["value"] = ev["new"]
        entry["status"] = "owner_set"
        entry["effective_from"] = ev["utc"]
        entry["rationale"] = ev["reason"]
        _set_path(doc, entry["key"], ev["new"])
    return doc


def load_store(path: Path | str = SHIPPED_STORE_PATH, rulings_log: Path | str | None = None) -> MacroStore:
    """Load and validate; a missing, corrupt or refused store raises (no macro store, no macro decision).

    `rulings_log` replays `owner_ruling` governance events onto the shipped document; the file itself
    is never modified. Tests pass temporary copies."""
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if rulings_log is not None and Path(rulings_log).exists():
        doc = _replay_rulings(doc, Path(rulings_log))
    errs = validate_store_doc(doc)
    if errs:
        raise MacroRefusal(f"rules store {path.name} refused: " + " | ".join(errs))
    return MacroStore(doc, path)


# --------------------------------------------------------------------------- #
# Owner decisions (Quick start table; section 8.10)
# --------------------------------------------------------------------------- #
def owner_decision(store: MacroStore, d: str) -> dict:
    """The registry entry {key, value, default, options, status, effective_from, rationale, refs}."""
    if d not in DECISIONS:
        raise KeyError(d)
    return store.raw(f"owner_decisions.{d}")


def apply_owner_ruling(store_path: Path | str, log_path: Path | str, d: str, value: Any, actor: str,
                       clock: Callable[[], datetime], *, rationale: str = "",
                       acceptance_log: Path | str | None = None) -> dict:
    """Append one `owner_ruling` governance event; the store file stays byte-identical.

    The ruling takes effect through `load_store(store_path, rulings_log=log_path)`. It is never an
    acting-parameter edit (never demotes) and never a gate-package change. D6 is accepted only before
    the first acceptance attempt (`acceptance_log` non-empty refuses). Returns the completed event."""
    if actor != "owner":
        raise MacroRefusal(f"an owner ruling is made by the owner, not {actor!r}")
    store = load_store(store_path, log_path)
    entry = owner_decision(store, d)
    problem = _admissible(d, entry, value)
    if problem:
        raise MacroRefusal(problem)
    if d == "D6" and acceptance_log is not None and Path(acceptance_log).exists() and Path(acceptance_log).stat().st_size:
        raise MacroRefusal("D6: a ruling is accepted only before the first acceptance attempt (R-21 9(d))")
    candidate = store.doc
    candidate["owner_decisions"][d]["value"] = value
    candidate["owner_decisions"][d]["status"] = "owner_set"
    _set_path(candidate, entry["key"], value)
    errs = validate_store_doc(candidate)
    if errs:
        raise MacroRefusal(f"{d} ruling {value!r} refused: " + " | ".join(errs))
    event = {"kind": "owner_ruling", "book_id": None, "rule_id": None, "key": entry["key"],
             "old": entry["value"], "new": value, "actor": actor,
             "reason": rationale or f"{d} owner ruling", "refs": [d, *entry["refs"]]}
    append_event(Path(log_path), event, clock)
    return event
