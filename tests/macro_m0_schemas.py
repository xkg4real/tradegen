"""M0 package A (R-32): T-SCHEMA-01/02/03, T-REPRO-01a and the M0 unit forms of I-06c, T-SCOPE-01(f)
and T-CARD-01. Hermetic: no network, every write goes to a tempfile directory.

Module-level test_* functions; `test_ids` names the spec tests each one covers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from core.ficc import macro_artifacts as A
from core.ficc import macro_schema as S

FIX = Path(__file__).resolve().parent / "fixtures" / "macro"
NAME_OF = {"macro_state": "macro_state", "overlay_decision": "overlay_decision", "event_calendar": "event_calendar",
           "context_log": "context_log", "governance_event": "governance_event",
           "model_card_header": "model_card_header.macro"}
RECORD = ("git_hash", "config_hash", "data_snapshot_id", "knowledge_utc", "seed", "results_md5", "gate_package_version",
          "gate_package_md5", "ledger_hash_at_registration", "ledger_hash_at_run")   # section 7 reproducibility.record
TS = "2026-10-02T06:40:45Z"
_PH = re.compile(r"<[^<>]*>")


def _clock():
    return datetime(2026, 10, 2, 6, 41, 7, tzinfo=timezone.utc)


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ---- typed placeholder fill (T-SCHEMA-01, L3510): a test helper, not runtime code --------------------
def fill(name, inst):
    reg = S.registry()
    root = reg.by_id[S.schema_id(name)]
    return _fill(reg, root, root, copy.deepcopy(inst))


def _fill(reg, s, root, v):
    alts = reg._schemas_at(s, root)
    if isinstance(v, str) and _PH.fullmatch(v):
        for a, _ in alts:
            t = a.get("type")
            t = t if isinstance(t, list) else [t]
            if a.get("format") == "date-time":
                return TS
            if a.get("format") == "date":
                return "2026-10-02"
            if "integer" in t:
                return 1
            if "number" in t:
                return 1.0e8
        return "0" * 32
    if isinstance(v, dict):
        for k in v:
            for a, r in alts:
                sub = (a.get("properties") or {}).get(k)
                if sub is None and isinstance(a.get("additionalProperties"), dict):
                    sub = a["additionalProperties"]
                if sub is not None:
                    v[k] = _fill(reg, sub, r, v[k])
                    break
            else:
                v[k] = _fill(reg, {}, root, v[k])
    if isinstance(v, list):
        hit = next(((a["items"], r) for a, r in alts if isinstance(a.get("items"), dict)), ({}, root))
        v[:] = [_fill(reg, hit[0], hit[1], x) for x in v]
    return v


def filled():
    return {k: fill(NAME_OF[k], v) for k, v in _load("schema_examples.json").items()}


def synthetic_card():
    card = dict(filled()["model_card_header"])
    card.update(_load("card_results_synthetic.json"))
    return _rehash(card)


def _rehash(card):
    card["header_md5"] = S.header_md5(card)
    card["results_md5"] = S.results_md5(card)
    return card


def _at(obj, pointer):
    for part in [p for p in pointer.split("/") if p]:
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def _required_of(name, pointer):
    reg = S.registry()
    sid = S.schema_id(name)
    node = reg.node_at(sid, pointer)
    return sorted({r for a, _ in reg._schemas_at(node, reg.by_id[sid]) for r in (a.get("required") or [])})


def _declared(name, pointer):
    """A rule-output pointer resolves to a declared position (open objects accept anything below)."""
    reg = S.registry()
    sid = S.schema_id(name)
    node = root = reg.by_id[sid]
    for part in [p for p in pointer.split("/") if p]:
        alts = reg._schemas_at(node, root)
        if not any(a.get("properties") or isinstance(a.get("items"), dict)
                   or isinstance(a.get("additionalProperties"), dict) for a, _ in alts):
            return True
        try:
            node, root = reg._step(node, root, part)
        except KeyError:
            return False
    return True


def _expand(spec):
    schema, _, ptr = spec.partition(":")
    m = re.search(r"\{([^}]*)\}", ptr)
    names = [n.strip() for n in m.group(1).split(",")] if m else [None]
    return [(schema, ptr if n is None else ptr.replace(m.group(0), n)) for n in names]


# ---- T-SCHEMA-01 -------------------------------------------------------------------------------------
def test_schema_01_examples_validate():
    reg = S.registry()
    assert len(reg.by_id) == 7
    reg.resolve("macro_state.v2.0#/$defs/input", reg.by_id[S.schema_id("overlay_decision")])
    reg.resolve("model_card_header.macro.v2.0#/$defs/fields", reg.by_id[S.CARD_ID])
    ex = filled()
    for key, obj in ex.items():
        assert S.validate(NAME_OF[key], obj) == [], (key, S.validate(NAME_OF[key], obj))
    ev_root = reg.by_id[S.schema_id("event_calendar")]
    for event in ex["event_calendar"]["events"]:
        errs = []
        reg._v(*reg.resolve("#/$defs/event", ev_root), event, "", errs)
        assert errs == []
    # required: top level and the nested lists, each removal reported at its pointer
    nested = {"macro_state": ["", "/inputs/0", "/vol", "/flags", "/runtime/0", "/lag_audit"],
              "overlay_decision": ["", "/multipliers/0", "/vol_scale_card"],
              "event_calendar": ["", "/events/0", "/events/0/windows/0"], "context_log": ["", "/items/0"],
              "governance_event": [""],
              "model_card_header": ["", "/costs", "/data", "/data_span", "/cash_convention", "/start_band",
                                    "/midpoint_halves", "/timing"]}
    sizes = {("macro_state", "/inputs/0"): 20, ("macro_state", "/vol"): 13, ("macro_state", "/flags"): 12,
             ("macro_state", "/runtime/0"): 5, ("overlay_decision", "/vol_scale_card"): 6,
             ("event_calendar", "/events/0"): 7, ("context_log", "/items/0"): 11, ("model_card_header", ""): 44,
             ("macro_state", ""): 23, ("overlay_decision", ""): 28, ("governance_event", ""): 12}
    for key, ptrs in nested.items():
        for ptr in ptrs:
            req = _required_of(NAME_OF[key], ptr)
            assert len(req) == sizes.get((key, ptr), len(req)) and req, (key, ptr, req)
            for name in req:
                obj = copy.deepcopy(ex[key])
                del _at(obj, ptr)[name]
                assert "%s/%s: required" % (ptr, name) in S.validate(NAME_OF[key], obj), (key, ptr, name)
    # undeclared: top level and nested positions
    undeclared = {"macro_state": ["", "/inputs/0", "/vol", "/flags", "/annotations", "/concentration", "/runtime/0"],
                  "overlay_decision": ["", "/multipliers/0", "/vol_scale_card"],
                  "event_calendar": ["", "/events/0", "/events/0/windows/0"], "context_log": ["", "/items/0"],
                  "governance_event": [""], "model_card_header": ["", "/costs", "/data", "/start_band/require"]}
    for key, ptrs in undeclared.items():
        for ptr in ptrs:
            obj = copy.deepcopy(ex[key])
            _at(obj, ptr)["zzz"] = 1
            assert "%s/zzz: undeclared" % ptr in S.validate(NAME_OF[key], obj), (key, ptr)
    ms = copy.deepcopy(ex["macro_state"])
    ms["alerts"] = [{"alert_id": "a", "code": "X", "severity": "warn", "component": "c", "first_seen_utc": TS, "count": 1,
                     "zzz": 1}]
    assert "/alerts/0/zzz: undeclared" in S.validate("macro_state", ms)
    # open positions and maps
    for key in ("macro_state", "overlay_decision", "context_log"):
        obj = copy.deepcopy(ex[key])
        obj["extras"] = {"zzz": {"anything": [1, 2]}}
        assert S.validate(NAME_OF[key], obj) == []
    hdr = copy.deepcopy(ex["model_card_header"])
    for ptr in ("/parameters", "/outcomes", "/owner_decisions", "/timing/inputs"):
        _at(hdr, ptr)["zzz"] = {"free": True}
    assert S.validate("model_card_header.macro", hdr) == []
    ms = copy.deepcopy(ex["macro_state"])
    ms["owner_decisions"]["x"] = {"decision": "D9", "value": 1, "status": "default"}
    ms["concentration"]["by_book"]["x"] = {}
    errs = S.validate("macro_state", ms)
    assert any(e.startswith("/owner_decisions/x/decision: enum") for e in errs)
    assert sum(e.startswith("/concentration/by_book/x/") and e.endswith("required") for e in errs) == 3
    od = copy.deepcopy(ex["overlay_decision"])
    od["rule_versions"]["R-99"] = 1
    assert any(e.startswith("/rule_versions/R-99: type") for e in S.validate("overlay_decision", od))
    # a header carrying a result field is refused
    for name in ("selection_factor", "timing_profile", "forward_record", "start_band_results"):
        hdr = copy.deepcopy(ex["model_card_header"])
        hdr[name] = {}
        assert "/%s: undeclared" % name in S.validate("model_card_header.macro", hdr)
    # bounds and consts
    cases = [("macro_state", "/vol", "vt_weight_next", 1.01, "maximum 1"),
             ("overlay_decision", "/multipliers/0", "value", 0.49, "minimum 0.5"),
             ("overlay_decision", "", "composition", "product", "const 'min'"),
             ("overlay_decision", "", "ladder", 0.25, "enum"),
             ("overlay_decision", "", "overlay_cap", 1.5, "const 1.0"),
             ("macro_state", "", "read_only", 1, "const True"),
             ("macro_state", "/flags", "gap_sessions", -1, "minimum 0"),
             ("macro_state", "", "generated_at_utc", "2026-10-02T06:41:07+00:00", "format date-time"),
             ("macro_state", "", "decided_session", "2026-10-2", "format date")]
    for key, ptr, field, value, msg in cases:
        obj = copy.deepcopy(ex[key])
        _at(obj, ptr)[field] = value
        errs = S.validate(NAME_OF[key], obj)
        assert any(e.startswith("%s/%s: %s" % (ptr, field, msg)) for e in errs), (field, errs)
    ms = copy.deepcopy(ex["macro_state"])
    ms["flags"]["gap_sessions"], ms["flags"]["var_display_scale"] = 0, 1
    assert S.validate("macro_state", ms) == []
    ms["runtime"][0]["halt"] = {"class": "OPS", "reason_code": "x", "since_utc": TS, "rearm_mode": "auto", "causes": []}
    assert "/runtime/0/halt/causes: minItems 1" in S.validate("macro_state", ms)
    # loader guards (unknown keyword, dangling $ref) and the extra keywords the rulings require
    gov = S.load_schema("governance_event")
    bad = copy.deepcopy(gov)
    bad["properties"]["reason"]["patternProperties"] = {}
    for broken in (bad, {"$id": "quantgen/x.v2.0", "type": "object", "properties": {"a": {"$ref": "#/$defs/nope"}}}):
        try:
            S.Registry([broken])
            raise AssertionError("SchemaLoadError expected")
        except S.SchemaLoadError:
            pass
    mini = S.Registry([{"$id": "quantgen/m.v2.0", "type": "object", "properties": {
        "s": {"type": "string", "pattern": "^ab"}, "l": {"type": "array", "maxItems": 1}, "n": {"exclusiveMaximum": 1},
        "u": {"anyOf": [{"type": "string"}, {"type": "null"}]}, "o": {"oneOf": [{"const": 1}, {"type": "integer"}]},
        "c": {"if": {"const": "x"}, "then": {"enum": ["y"]}, "else": {"type": "string"}}}}])
    bad = mini.validate("quantgen/m.v2.0", {"s": "ba", "l": [1, 2], "n": 1, "u": 1, "o": 1, "c": "x"})
    assert sorted(p for p, _ in bad) == ["/c", "/l", "/n", "/o", "/s", "/u"], bad
    assert mini.validate("quantgen/m.v2.0", {"s": "ab", "l": [], "n": 0.5, "u": None, "o": 2, "c": "z"}) == []


test_schema_01_examples_validate.test_ids = ["T-SCHEMA-01"]


# ---- T-SCHEMA-02 -------------------------------------------------------------------------------------
def test_schema_02_card_field_set():
    card = synthetic_card()
    assert S.validate("model_card.macro", card) == []
    ok, issues, acting = S.check_artifact("model_card.macro", card)
    assert ok and not issues and not acting
    names = ("family_id", "ledger_hash_at_registration", "ledger_hash_at_run", "N_raw", "N_clusters", "N_equiv",
             "N_hat_linear", "N_eff", "V_null", "selection_factor", "power", "timing_profile", "instrument_book",
             "rebalance", "no_trade_band", "notional_nav", "cash_convention", "start_band", "episode_rule_version",
             "start_band_results", "midpoint_halves_results", "gjr_null_pct", "git_hash", "config_hash",
             "data_snapshot_id", "knowledge_utc")
    assert len(names) == 26
    for name in names:
        c = copy.deepcopy(card)
        del c[name]
        assert S.validate("model_card.macro", c), name
    for sub in ("se_hac", "se_blk250", "se_plateau", "mde80", "power_at_0p05", "power_at_0p10"):
        c = copy.deepcopy(card)
        del c["power"][sub]
        assert "/power/%s: required" % sub in S.validate("model_card.macro", c)
    # H3: acting long-sample cards need both bands; other cards may leave them null
    hdr = filled()["model_card_header"]
    for k in ("start_band", "midpoint_halves"):
        h = copy.deepcopy(hdr)
        h[k] = None
        h["header_md5"] = S.header_md5(h)
        assert any(i.startswith("/%s: H3" % k) for i in S.header_issues(h)), k
    h = copy.deepcopy(hdr)
    h["start_band"] = h["midpoint_halves"] = None
    h["header_md5"] = S.header_md5(h)
    assert S.header_issues(h, acting_long_sample=False) == []
    hdr["header_md5"] = S.header_md5(hdr)
    assert S.header_issues(hdr, seed_study=11) == []
    assert any(i.startswith("/seed: H15") for i in S.header_issues(hdr, seed_study=12))
    # the Kish N-hat is never a field
    assert not S._any_name(S.registry().by_id, "kish")
    c = copy.deepcopy(card)
    c["kish_n"] = 3.0
    assert "/kish_n: undeclared" in S.validate("model_card.macro", c)
    # macro_state inputs and provenance; context_log items
    ms = filled()["macro_state"]
    req = _required_of("macro_state", "/inputs/0")
    assert len(req) == 20 and {"value_status", "session_date", "available_at_utc", "available_at_source",
                               "retrieved_at_utc", "content_hash", "vintage"} <= set(req)
    for name in req + ["schema", "schema_version", "read_only", "generated_at_utc", "knowledge_utc", "git_hash",
                       "config_hash", "data_snapshot_id"]:
        m = copy.deepcopy(ms)
        del (m["inputs"][0] if name in req else m)[name]
        assert S.validate("macro_state", m), name
    cl = filled()["context_log"]
    for name in ("series_id", "vintage", "retrieved_at_utc", "value_status", "stale"):
        c = copy.deepcopy(cl)
        del c["items"][0][name]
        assert "/items/0/%s: required" % name in S.validate("context_log", c)
    # K1-K4: one injected violation each, refused at /disposition
    for patch in ({"verdict": "PASS", "disposition": "SPECIFICATION_ONLY"},
                  {"verdict": "REVISE", "disposition": "RECOMMENDATION"},
                  {"disposition": "INVARIANT_STEP", "family_id": "R-06"},
                  {"verdict": "PASS", "disposition": "BUILD_AS_INSURANCE", "class": "CARD-O", "comparator": "overlay_off",
                   "claim_type": "outperformance"}):
        c = _rehash({**copy.deepcopy(card), **patch})
        ok, issues, acting = S.check_artifact("model_card.macro", c)
        assert not ok and not acting and any(i.startswith("/disposition: K") for i in issues), (patch, issues)
    c = _rehash({**copy.deepcopy(card), "verdict": "PASS", "disposition": "BUILD_AS_INSURANCE"})
    assert S.check_artifact("model_card.macro", c)[0]


test_schema_02_card_field_set.test_ids = ["T-SCHEMA-02"]


# ---- T-SCHEMA-03 -------------------------------------------------------------------------------------
RULE_OUTPUTS = {
    "R-01": ["macro_state:/inputs/*/{value_status,session_date,available_at_utc,retrieved_at_utc,role}",
             "macro_state:/lag_audit", "model_card.macro:/lag_audit_violations"],
    "R-03": ["overlay_decision:/{vol_scale,exposure_basis}"],
    "R-04": ["overlay_decision:/multipliers/*/{value,rule_id}", "overlay_decision:/multipliers/*/card/disposition"],
    "R-08": ["macro_state:/annotations/vix_ge_vix3m"],
    "R-13": ["context_log:/items/*/{vintage,retrieved_at_utc,first_release,latest,vintage_date,timing,stale}"],
    "R-19": ["macro_state:/inputs/*/{role,expected_available_utc,stale_deadline_utc,status}",
             "macro_state:/{fail_closed,alerts}", "macro_state:/flags/hedge_reasons", "context_log:/items/*/stale",
             "macro_state:/runtime/*/halt/{class,reason_code}"],
    "R-20": ["macro_state:/{decision_utc,effective_session}", "macro_state:/extras/regime_tags",
             "model_card.macro:/regime_line_results", "event_calendar:/events/*/{kr_open_gap_session,gap_sessions}",
             "macro_state:/flags/{kr_open_gap_event,gap_sessions}"],
    "R-21": ["model_card.macro:/tests/PC1p/legs/*/{h,dES,z,p,p_adj,pass}",
             "model_card.macro:/tests/PC1p/two_x/*/{h,dES,z,p,p_adj,pass}",
             "model_card.macro:/tests/PC2/{ratio_daily,ratio_horizon,ci90,horizon_used,pass}",
             "model_card.macro:/tests/PC3/{dSR,p10,pPW,block_PW,p_ni,p_adj,point_2x,pass}",
             "model_card.macro:/tests/{PC4,PC5,PC6,PC7}",
             "model_card.macro:/{caps_applied,verdict,verdict_reason,gjr_null_pct,verdict_at_f1,verdict_at_f_neff}",
             "model_card.macro:/printed/{dMDD,dCDaR95,dES99,bands,tuw,reentry_lag,post_trough,rolling_5y,with_risk_layer}",
             "model_card.macro:/printed/placebo_panel/{n,passes}"],
    "R-22": ["model_card.macro:/{episode_rule_version,regime_line_results,cost_episodes}",
             "model_card.macro:/episodes/*/{peak,trough,depth,window,benefit_vs_S,share,regime_tags,post_trough_63,open}",
             "model_card.macro:/tests/PC4/{positive,n,max_share}", "model_card.macro:/pc4_section_8_6/{positive,n,max_share}",
             "model_card_header.macro:/{cash_convention,history_first_close,start_band,regime_lines,primary_oos_line}",
             "model_card_header.macro:/data_span/{end,start}", "model_card_header.macro:/midpoint_halves/split_date",
             "model_card.macro:/start_band_results/{starts,verdicts,n_pass,n_starts,n_reject,floor_pass}",
             "model_card.macro:/midpoint_halves_results/{h1,h2}", "model_card.macro:/printed/with_risk_layer"],
    "R-23": ["model_card_header.macro:/{family_id,ledger_hash_at_registration,N_raw_at_registration}",
             "model_card.macro:/{ledger_hash_at_run,N_raw,N_clusters,N_equiv,N_hat_linear,N_eff,E_max_sim,V_null,V_trials}",
             "model_card.macro:/selection_factor/{value,rule,alt_value}",
             "model_card.macro:/tests/step3/{deflated_dSR,at_N_raw,at_N_hat_linear,borderline,break_even_N,z_check,by_q,dsr_vs0,psr_vs_S,selection_factor,pass}"],
    "R-24": ["model_card.macro:/power/{se_hac,se_blk250,se_plateau,se_curve,mde80,power_at_0p05,power_at_0p10,pc3_power_at_0,years_to_detect_0p05}",
             "model_card.macro:/tests/step2/{p_lw,p_hac,block,n_blocks}", "model_card.macro:/tests/step5/{p_lw,p_hac,block,n_blocks}",
             "model_card.macro:/tests/PC3/{p_lw,p_hac,block,n_blocks}",
             "model_card.macro:/tests/step4/{pbo,winner_loses_share,pbo_null,slope,n_configs}",
             "model_card.macro:/printed/{lo_sr_20,lo_sr_all,by_q,hl_haircut}", "model_card.macro:/verdict_reason"],
    "R-25": ["model_card.macro:/forward_record/{start_utc,first_registered_utc,months,dSR_vs_S,dES21,dMDD,cusum_S,alarms,switches,switch_p99,lag_audit_violations,demoted,demotion_reason,honesty_line,missed_decisions,gaps}"],
    "R-26": ["model_card_header.macro:/{instrument_book,instrument_lines,rebalance,no_trade_band,notional_nav,nav_fx,fill_model,roll_calendar}",
             "model_card.macro:/costs_per_side/{table_bp,floor_bp,applied_bp,stress_line,roll_cost_line}",
             "model_card.macro:/printed/exec_variants/{A,B,C}",
             "model_card.macro:/printed/{overnight_intraday,turnover_by_regime,stress_cost,roll_cost,ban_basis}",
             "overlay_decision:/extras/{instrument_book,contracts,w_target,w_held,band}"],
    "R-27": ["overlay_decision:/extras/{fill_model,decision_price_source,fill_status,flags}",
             "model_card.macro:/printed/fill_tracking_error"],
    "R-28": ["macro_state:/forward_sim/R28_below_sma10m", "overlay_decision:/forward_sim/*/rule_id",
             "overlay_decision:/forward_sim/*/card/{class,verdict,disposition,displayed_as}",
             "overlay_decision:/multipliers/*/{rule_id,exposure_basis}", "model_card_header.macro:/claim_lines",
             "model_card.macro:/claim_line_results/{stacked_dMDD,band,pass}",
             "model_card.macro:/pooling/{rule,n_onsets_own,n_onsets_pooled}", "model_card.macro:/gjr_null_pct",
             "model_card.macro:/snooping/{n_variants,share_dMDD_ge_3pp,deflated_prob_sr}"],
    "R-29": ["model_card_header.macro:/{card_id,instrument_book,notional_nav}",
             "model_card.macro:/{contracts_path,start_band_results}",
             "model_card.macro:/settling_run/{span,verdict,pc1_prime_1x,pc1_prime_2x,starts,n_pass,n_starts,n_reject,midpoint_halves}",
             "overlay_decision:/forward_sim/*/rule_id"],
    "R-30": ["macro_state:/vol/estimator",
             "macro_state:/vol/estimator_gate/{status,stage1,stage2_mcs_p,stage3_rank,fallback_used,reason}",
             "model_card.macro:/forecast_eval/qlike_mcs_p/*", "model_card.macro:/forecast_eval/mse_mcs_p/*",
             "model_card.macro:/forecast_eval/{christoffersen_p,es_z2,fan_pit_p,vol_of_vol,dMDD_vs_sma20,dSR_vs_sma20}"],
    "R-31": ["macro_state:/flags/{ladder_step,ladder_dwell_left,block_new_entries}", "macro_state:/runtime/*/{hwm_hard,ref_step}",
             "overlay_decision:/multipliers/*/rule_id", "overlay_decision:/multipliers/*/card/verdict",
             "model_card.macro:/printed/{binding_share,n_halts,persistence_check}"],
    "R-34": ["model_card.macro:/timing_profile/lags/*/{L,dSR,dMDD,dES21,lag_audit,timing_class}",
             "model_card.macro:/timing_profile/{strict,LP,LF,FR,label,live_feeds}"],
}
# Rule outputs with no section-6 schema (owned by M7/M8; a later schema is a visible change): R-21 acceptance_report.json,
# R-25 monitoring_report, R-23 family-ledger rows, R-35 cards/verdicts.jsonl and run_log.jsonl, gate/acceptance_runs.jsonl.
NO_SCHEMA = ("acceptance_report", "monitoring_report", "family_ledger", "verdicts.jsonl", "run_log.jsonl", "acceptance_runs.jsonl")


def _card(verdict, disposition, displayed_as, card_id="MACRO-X", cls="CARD-P"):
    return {"card_id": card_id, "class": cls, "verdict": verdict, "disposition": disposition,
            "displayed_as": displayed_as, "label": None, "results_md5": None}


def rule_instances():
    """One synthetic instance per rule, built from the fixtures and that rule's Outputs list."""
    ex, card = filled(), synthetic_card()
    out = {r: [] for r in RULE_OUTPUTS}
    base = {"macro_state": ex["macro_state"], "overlay_decision": ex["overlay_decision"],
            "context_log": ex["context_log"], "event_calendar": ex["event_calendar"], "model_card.macro": card}
    for r in ("R-01", "R-03", "R-04", "R-08", "R-13", "R-21", "R-22", "R-23", "R-24", "R-25", "R-34"):
        out[r] = [(k, copy.deepcopy(v)) for k, v in base.items()]
    ms = copy.deepcopy(ex["macro_state"])
    ms["inputs"][0]["status"], ms["fail_closed"] = "stale_missed_release", True
    ms["alerts"] = [{"alert_id": "a1", "code": "ACTING_INPUT_STALE", "severity": "page", "component": "R-19",
                     "series_id": "KOSPI_OFFICIAL_CLOSE", "books": ["specification:KR"], "first_seen_utc": TS, "count": 1}]
    cause = {"class": "OPS", "reason_code": "acting_input_stale:KOSPI_OFFICIAL_CLOSE", "since_utc": TS, "rearm_mode": "auto"}
    ms["runtime"][1]["halt"] = {**cause, "causes": [cause]}
    ms["runtime"][1]["engine_state"] = "HALTED"
    out["R-19"] = [("macro_state", ms), ("context_log", copy.deepcopy(ex["context_log"]))]
    ms = copy.deepcopy(ex["macro_state"])
    ms["extras"] = {"regime_tags": {"KRX_HOLIDAY_GAP": True, "n_US": 2}}
    ec = copy.deepcopy(ex["event_calendar"])
    ec["events"].append({"event_id": "KRX-GAP-2026-10-06", "type": "KRX_HOLIDAY_GAP", "region": "KR", "scheduled_utc": TS,
                         "status": "scheduled", "source": "core/calendars", "windows": [], "gap_sessions": 2,
                         "var_display_scale": 1.4142, "kr_open_gap_session": "2026-10-06"})
    out["R-20"] = [("macro_state", ms), ("event_calendar", ec), ("model_card.macro", copy.deepcopy(card))]
    od = copy.deepcopy(ex["overlay_decision"])
    od["extras"] = {"instrument_book": "KRX_ETF_line", "contracts": 0, "w_target": 0.685, "w_held": [0.7], "band": 0.0}
    out["R-26"] = [("overlay_decision", od), ("model_card.macro", copy.deepcopy(card))]
    od = copy.deepcopy(ex["overlay_decision"])
    od["extras"] = {"fill_model": "KRX_close_auction", "decision_price_source": "official_close", "fill_status": "filled",
                    "flags": ["LP_exempt_auction", "inav_residual_gt_30bp"]}
    out["R-27"] = [("overlay_decision", od), ("model_card.macro", copy.deepcopy(card))]
    od = copy.deepcopy(ex["overlay_decision"])
    od["forward_sim"] = [{"rule_id": "R-28", "value": 0.5, "would_apply_to": "US gross (FORWARD-SIM)",
                          "card": _card("NOT_RUN", "FORWARD_SIM", "descriptive", "MACRO-R28-US-TREND")},
                         {"rule_id": "R-29", "value": 1.0, "card": _card("NOT_RUN", "FORWARD_SIM", "descriptive", "MACRO-R06-US-FUT")}]
    ms = copy.deepcopy(ex["macro_state"])
    ms["forward_sim"] = {"R28_below_sma10m": False, "R29_vt_weight_next": 1.0}
    out["R-28"] = out["R-29"] = [("overlay_decision", od), ("macro_state", ms), ("model_card.macro", copy.deepcopy(card))]
    ms = copy.deepcopy(ex["macro_state"])
    ms["vol"].update({"estimator": "comb", "estimator_gate": {"status": "challenger_selected", "stage1": {"b5": "PASS"},
                                                             "stage2_mcs_p": 0.3, "stage3_rank": 1, "fallback_used": False,
                                                             "reason": None}})
    out["R-30"] = [("macro_state", ms), ("model_card.macro", copy.deepcopy(card))]
    ms = copy.deepcopy(ex["macro_state"])
    ms["flags"].update({"ladder_step": "step_-8", "ladder_dwell_left": 3, "block_new_entries": False})
    ms["runtime"][0].update({"hwm_hard": 1.0, "ref_step": 0.92})
    od = copy.deepcopy(ex["overlay_decision"])
    od.update({"market": "KR", "family": "market_gross", "exposure_basis": "total", "vol_scale": 0.694,
               "vol_scale_recommended_book": 1.0, "ladder": 1.0, "post_rearm_cap": None,
               "vol_scale_card": _card("NOT_RUN", "SPECIFICATION_ONLY", "descriptive", "MACRO-R06-KR-ETF"),
               "multipliers": [{"rule_id": "R-31", "value": 1.0, "exposure_basis": "total",
                                "card": _card("NOT_RUN", "INVARIANT_STEP", "invariant", "MACRO-R31-KR-ETF")}],
               "refusal": [{"rule_id": "R-12-S2", "value": 0.5, "would_apply_to": "US duration-sensitive gross (refusal book)",
                            "card": {"card_id": "MACRO-R12-US-RATES", "class": "CARD-P", "verdict": "REJECT",
                                     "disposition": "REFUSAL_BOOK", "displayed_as": "refusal", "label": None, "results_md5": None}}],
               "binding": ["none"]})
    out["R-31"] = [("macro_state", ms), ("overlay_decision", od), ("model_card.macro", copy.deepcopy(card))]
    return out


def test_schema_03_rule_outputs_declared():
    pointers = [(r, s, p) for r, specs in RULE_OUTPUTS.items() for spec in specs for s, p in _expand(spec)]
    assert len(pointers) >= 280, len(pointers)
    missing = [(r, s, p) for r, s, p in pointers if not _declared(s, p)]
    assert not missing, missing
    for s, p in (("macro_state", "/flags/nope"), ("model_card.macro", "/tests/step3/nope"), ("model_card.macro", "/kish"),
                 ("overlay_decision", "/multipliers/*/card/kish")):
        assert not _declared(s, p), (s, p)
    assert len(NO_SCHEMA) == 6
    inst = rule_instances()
    assert set(inst) == set(RULE_OUTPUTS)
    for rule, items in inst.items():
        assert items, rule
        for name, obj in items:
            ok, issues, _ = S.check_artifact(name, obj)
            assert ok, (rule, name, issues)
    # test of the test: an undeclared field outside extras makes the rule's case fail
    name, obj = inst["R-19"][0]
    obj["flags"]["bogus_acting"] = True
    ok, issues, acting = S.check_artifact(name, obj)
    assert not ok and acting and "/flags/bogus_acting: undeclared" in issues


test_schema_03_rule_outputs_declared.test_ids = ["T-SCHEMA-03"]


# ---- T-REPRO-01a -------------------------------------------------------------------------------------
def test_repro_01a_provenance_and_canonical_json():
    reg = S.registry()
    required = set(reg.by_id[S.CARD_ID]["required"]) | set(reg.by_id[S.HEADER_ID]["$defs"]["fields"]["required"])
    assert set(RECORD) <= required
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        prov = A.provenance(clock=_clock, knowledge_utc=TS, config_hash="c" * 32, data_snapshot_id=A.data_snapshot_id())
        assert prov["git_hash"] == "UNVERSIONED" and len(prov["tree_hash"]) == 64 and prov["read_only"] is True
        assert prov["generated_at_utc"] == "2026-10-02T06:41:07Z" and prov["data_snapshot_id"] == hashlib.md5(b"").hexdigest()
        card = synthetic_card()
        card.update(prov)
        card = _rehash(card)
        p = A.write_artifact(root, "model_card.macro", card, _clock)
        assert p == root / "cards" / "MACRO-R06-KR-ETF.json"
        back = json.loads(p.read_text(encoding="utf-8"))
        for name in RECORD + ("tree_hash",):
            assert back[name] not in (None, ""), name
        assert back["read_only"] is True and back["seed"] == 11
        ex = filled()
        for key in ("macro_state", "overlay_decision", "event_calendar", "context_log"):
            obj = dict(ex[key])
            obj.update(A.provenance(clock=_clock, knowledge_utc=obj["knowledge_utc"], config_hash="c" * 32,
                                    data_snapshot_id="d" * 32))
            p1 = A.write_artifact(root, key, obj, _clock)
            assert p1.is_file() and p1.parent.name != "quarantine" and str(p1).startswith(str(root / key))
            back = json.loads(p1.read_text(encoding="utf-8"))
            for name in ("git_hash", "tree_hash", "config_hash", "data_snapshot_id", "knowledge_utc", "generated_at_utc"):
                assert back[name], (key, name)
            assert back["read_only"] is True and back["git_hash"] == "UNVERSIONED"
            b1 = p1.read_bytes()
            assert A.write_artifact(root, key, obj, _clock).read_bytes() == b1 and b1 == S.canonical_json(obj).encode("utf-8")
        assert not (root / "quarantine").exists()
    try:
        A.provenance(clock=_clock, config_hash="c", data_snapshot_id="d")
        raise AssertionError("knowledge_utc is never defaulted")
    except TypeError:
        pass
    try:
        A.utc_stamp(datetime(2026, 10, 2))
        raise AssertionError("naive clock refused")
    except ValueError:
        pass
    pin = {"b": 1.0, "a": [0.1, True, None, "é", 1e-07, 100000000.0, 3]}
    assert S.canonical_json(pin).encode("utf-8") == b'{"a":[0.1,true,null,"\xc3\xa9",1e-07,100000000.0,3],"b":1.0}'
    assert S.md5_hex(S.canonical_json(pin)) == "4e41d73e54f7559cf7d69a19f57c2d33"
    assert S.canonical_json({"z": 1, "a": {"y": 2, "b": 3}}) == S.canonical_json({"a": {"b": 3, "y": 2}, "z": 1})
    try:
        S.canonical_json({"x": float("nan")})
        raise AssertionError("NaN must be refused")
    except ValueError:
        pass
    art = {"generated_at_utc": TS, "git_hash": "UNVERSIONED", "tree_hash": "t", "market": "KR"}
    assert S.strip_volatile(art) == {"market": "KR"} and S.VOLATILE_FIELDS == ("generated_at_utc", "git_hash", "tree_hash")
    # header_md5 / results_md5 cover disjoint field sets
    card = synthetic_card()
    h0, r0 = S.header_md5(card), S.results_md5(card)
    c = {**card, "generated_at_utc": "2027-01-01T00:00:00Z", "git_hash": "x", "tree_hash": "y"}
    assert S.header_md5(c) == h0 and S.results_md5(c) == r0
    assert S.header_md5({**card, "verdict": "REJECT"}) == h0 and S.results_md5({**card, "N_raw": 4}) != r0
    assert S.header_md5({**card, "revision": 3}) != h0 and S.results_md5({**card, "revision": 3}) == r0
    assert S.header_md5({**card, "header_md5": "other"}) == h0 and S.results_md5({**card, "results_md5": "other"}) == r0
    assert not (S.HEADER_FIELDS & S.RESULT_FIELDS) and len(S.HEADER_FIELDS) == 52
    head, res = S.split_card(card)
    assert set(head) <= S.HEADER_FIELDS and set(res) <= S.RESULT_FIELDS and len(head) + len(res) == len(card)
    # RNG convention
    ref = np.random.Generator(np.random.PCG64(np.random.SeedSequence(11))).random()
    assert A.rng(11).random() == ref
    a, b = A.child_rngs(11, 2)
    a2, _ = A.child_rngs(11, 2)
    assert a.random() != b.random() and A.child_rngs(11, 2)[0].random() == a2.random()
    # M6 filled the builders (tests/macro_m6_context.py): they take (market, ctx, *, provenance, ...) and never a wall clock
    import inspect
    for builder in (A.build_macro_state, A.build_overlay_decisions):
        params = inspect.signature(builder).parameters
        assert list(params)[:2] == ["market", "ctx"] and "provenance" in params and params["provenance"].kind is inspect.Parameter.KEYWORD_ONLY


test_repro_01a_provenance_and_canonical_json.test_ids = ["T-REPRO-01a"]


# ---- field classes, quarantine, card refusals (M0 unit forms of I-06c, T-SCOPE-01 (f), T-CARD-01) -------
def test_field_classes_and_quarantine():
    ex = filled()
    ms = ex["macro_state"]
    assert S.field_class("macro_state", "/flags/gap_sessions") == "display"
    assert S.field_class("macro_state", "/vol/vt_weight_next") == "acting"
    assert S.field_class("macro_state", "/flags/new_flag") == "acting"          # unclassified = acting
    assert S.field_class("macro_state", "/inputs/1/value", ms) == "display"      # role context
    assert S.field_class("macro_state", "/inputs/0/value", ms) == "acting"       # role acting_exposure
    assert S.field_class("macro_state", "/inputs/0/value") == "acting"           # no instance: fail closed
    assert S.field_class("overlay_decision", "/reasons/0") == "display"
    assert S.field_class("context_log", "/items/0/stale") == "context"
    assert S.enum_of("macro_state", "/runtime/*/halt/class") == ("RISK", "OPS")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = copy.deepcopy(ms)
        a["annotations"]["bogus"] = 1
        a["inputs"][1]["value"] = "x"
        a["flags"]["gap_sessions"] = -1
        ok, issues, acting = S.check_artifact("macro_state", a)
        assert not ok and len(issues) == 3 and not acting
        p = A.write_artifact(root, "macro_state", a, _clock)
        back = json.loads(p.read_text(encoding="utf-8"))
        assert back["extras"]["validation_errors"] == issues and "validation_errors" not in a.get("extras", {})
        b = copy.deepcopy(a)
        b["inputs"][0]["value"] = "x"
        b["vol"]["vt_weight_next"] = 2
        b["flags"]["new_flag"] = True
        ok, issues, acting = S.check_artifact("macro_state", b)
        assert not ok and len(issues) == 6 and acting
        b["market"] = "US"
        try:
            A.write_artifact(root, "macro_state", b, _clock)
            raise AssertionError("acting failure must raise")
        except A.ArtifactRefused as exc:
            assert exc.acting_failure and exc.quarantine_path.is_file() and exc.quarantine_path.parent == root / "quarantine"
            q = json.loads(exc.quarantine_path.read_text(encoding="utf-8"))
            assert q["class"] == "acting" and q["issues"] == exc.issues and q["artifact"]["market"] == "US"
        assert not (root / "macro_state" / "US").exists()
        cl = copy.deepcopy(ex["context_log"])
        del cl["items"][0]["stale"]
        ok, issues, acting = S.check_artifact("context_log", cl)
        assert not ok and not acting
        try:
            A.write_artifact(root, "context_log", cl, _clock)
            raise AssertionError("refused kinds never reach the artifact directory")
        except A.ArtifactRefused as exc:
            assert not exc.acting_failure and exc.quarantine_path.is_file()
        assert not (root / "context_log").exists() and len(list((root / "quarantine").iterdir())) == 2
        cl = copy.deepcopy(ex["context_log"])
        cl["as_of_utc"] = "2026-10-02T06:30:31Z"
        assert any(i.startswith("/as_of_utc: S8") for i in S.check_artifact("context_log", cl)[1])
        assert not S.check_artifact("macro_state", "not a dict")[0]
    # T-CARD-01 unit forms: header md5, committed header, displayed_as iff PASS
    card = synthetic_card()
    c = {**card, "header_md5": "0" * 32}
    assert any(i.startswith("/header_md5: K5") for i in S.check_artifact("model_card.macro", c)[1])
    committed = S.split_card(card)[0]
    assert S.card_issues(card, committed_header=committed) == []
    assert any(i.startswith("/revision: K8") for i in S.card_issues(card, committed_header={**committed, "revision": 9}))
    hdr = ex["model_card_header"]
    hdr["header_md5"] = S.header_md5(hdr)
    assert S.header_issues(hdr, committed_md5=hdr["header_md5"]) == []
    assert any(i.startswith("/header_md5: H4") for i in S.header_issues(hdr, committed_md5="0" * 32))
    assert any(i.startswith("/no_trade_band: H9") for i in S.header_issues({**hdr, "no_trade_band": 0.10}))
    assert any(i.startswith("/roll_calendar: H10") for i in S.header_issues({**hdr, "instrument_book": "mini_KOSPI200_futures"}))
    od = copy.deepcopy(ex["overlay_decision"])
    od["vol_scale_card"]["displayed_as"] = "recommendation"
    ok, issues, acting = S.check_artifact("overlay_decision", od)
    assert not ok and acting and any(i.startswith("/vol_scale_card/displayed_as: S1") for i in issues)
    od = copy.deepcopy(ex["overlay_decision"])
    od["vol_scale_card"].update({"verdict": "PASS", "disposition": "RECOMMENDATION", "displayed_as": "recommendation"})
    assert any(i.startswith("/vol_scale_recommended_book: S3") for i in S.check_artifact("overlay_decision", od)[1])
    od["vol_scale_recommended_book"] = 0.5
    assert S.check_artifact("overlay_decision", od)[0]
    od["overlay_applied_spec_book"] = 0.75
    assert any(i.startswith("/overlay_applied_spec_book: S5") for i in S.check_artifact("overlay_decision", od)[1])
    od = copy.deepcopy(ex["overlay_decision"])
    od["extras"] = {"w_target": 1.2}
    ok, issues, acting = S.check_artifact("overlay_decision", od)
    assert not ok and acting and "/extras/w_target: bounds [0, 1]" in issues


test_field_classes_and_quarantine.test_ids = ["I-06c", "T-SCOPE-01", "T-CARD-01"]


def test_fixture_listing_md5():
    rows = _load("macro_m0_schemas.fixtures.json")
    assert {r["file"] for r in rows} == {"schema_examples.json", "card_results_synthetic.json"}
    for r in rows:
        assert hashlib.md5((FIX / r["file"]).read_bytes()).hexdigest() == r["md5"], r["file"]
        assert r["tests"] and "owner" in r and "licence" in r


test_fixture_listing_md5.test_ids = ["T-HERM-02"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
