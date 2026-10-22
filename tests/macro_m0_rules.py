"""M0 package B tests: rules store, rule objects, DO-NOT-BUILD, owner decisions, governance chain.

Spec tests: T-CAP-01, T-BASIS-01, T-DNB-01, T-OWNER-01 (M0 clauses), governance chain, config_hash.
Hermetic: every write goes to a tempfile directory; the shipped store is read only and its md5 is
checked before and after. No network, no clock: a pinned `_CLOCK`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.ficc import macro_schema as S
from core.rules import governance as G
from core.rules import macro_rules as M
from core.rules.macro_rules import RuleInput, RuleObject
from tests.notrun import NotRun

_CLOCK = lambda: datetime(2026, 10, 6, 7, 0, 0, tzinfo=timezone.utc)   # noqa: E731
_SHIPPED_MD5 = hashlib.md5(M.SHIPPED_STORE_PATH.read_bytes()).hexdigest()


def _store_copy(tmp: Path, mutate=None) -> Path:
    doc = json.loads(M.SHIPPED_STORE_PATH.read_text(encoding="utf-8"))
    if mutate:
        mutate(doc)
    p = tmp / "rules.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _refused(mutate) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            M.load_store(_store_copy(Path(tmp), mutate))
        except M.MacroRefusal as exc:
            return str(exc)
    raise AssertionError("store was not refused")


def _vt(**over) -> RuleObject:
    base = dict(rule_id="R-06-KR-VT20", kind="CARD-P", output_range=(0.0, 1.0), exposure_basis="total",
                applies_to="market_gross", composition="min", books=("specification",),
                inputs=(RuleInput("KOSPI_OFFICIAL_CLOSE", "acting_exposure", ("specification",), "publication", "market_price"),),
                estimator={"name": "sma20", "kind": "sma"}, label_layer="none", instrument_book="KRX_ETF_line",
                market="KR", card_id="MACRO-R06-KR-ETF", tier="B", n_rule=M.N_GATE, factor="vt")
    base.update(over)
    return RuleObject(**base)


def _overlay(**over) -> RuleObject:
    base = dict(rule_id="R-04-DM", kind="CARD-O", output_range=(0.5, 1.0), exposure_basis="active",
                applies_to="momentum", composition="min", books=("specification",), market="US",
                card_id="MACRO-R04-US-DM", tier="B", n_rule=M.N_GATE, factor="overlay")
    base.update(over)
    return RuleObject(**base)


def _items_of(report, shape: str):
    return [i for i in report.errors if f"[{shape}]" in i.message]


# --------------------------------------------------------------------------- #
# T-CAP-01
# --------------------------------------------------------------------------- #
def test_cap_01_store_blocks_pass_bounds():
    store = M.load_store()
    assert store.get("overlay.cap") == 1.0 and store.get("vol_target.KR.cap") == 1.0
    assert store.get("gate.package.status") == "NOT_FROZEN" and len(store.get("do_not_build.tf_items")) == 17   # DNB-TF-01..17 (S7)
    assert store.get("gate.costs") == "read_from_gate"          # no rate lives in the store (P10)
    for mutate, needle in (
        (lambda d: d["vol_target"]["KR"].__setitem__("cap", 1.5), "vol_target.KR.cap"),
        (lambda d: d["overlay"].__setitem__("cap", 1.2), "overlay.cap"),
        (lambda d: d["overlay"].__setitem__("floor", 0.4), "overlay.floor"),
        (lambda d: d["overlay"].__setitem__("combine", "product"), "item 31"),
        (lambda d: d["cards"]["R-31_step_down"]["steps"][0].__setitem__("mult", 0.75), "R-31_step_down.steps"),
        (lambda d: d["refusal_books"]["S2_rates"].__setitem__("multiplier", 1.5), "S2_rates.multiplier"),
        (lambda d: d["gate"]["tiers"]["C"].__setitem__("allowed", True), "tiers.C"),
        (lambda d: d["gate"]["step3"].__setitem__("n_gate", "kish"), "item 36"),
        (lambda d: d.__setitem__("read_only", False), "read_only"),
    ):
        assert needle in _refused(mutate), needle
    assert hashlib.md5(M.SHIPPED_STORE_PATH.read_bytes()).hexdigest() == _SHIPPED_MD5


test_cap_01_store_blocks_pass_bounds.test_ids = ["T-CAP-01", "T-HERM-02"]


def test_cap_01_rule_object_bounds():
    for rng in ((0.49, 1.0), (0.5, 1.01), (0.0, 1.0)):
        r = M.validate_rule_object(_overlay(output_range=rng))
        hits = _items_of(r, "multiplier_weight_or_cap_above_1")
        assert hits and "item" in hits[0].message and "2 (harm_B)" in hits[0].message and "8 (inconclusive_B)" in hits[0].message, rng
    assert M.validate_rule_object(_overlay()).ok
    for fac in ("vt", "vs"):
        for rng in ((0.0, 1.01), (-0.1, 1.0)):
            r = M.validate_rule_object(_vt(output_range=rng, factor=fac, **({} if fac == "vt" else dict(applies_to="momentum", exposure_basis="active"))))
            assert _items_of(r, "multiplier_weight_or_cap_above_1"), (fac, rng)
    assert M.validate_rule_object(_vt(output_range=(0.0, 1.0))).ok
    assert _items_of(M.validate_rule_object(_vt(tier="C")), "multiplier_weight_or_cap_above_1")
    for fn, bad, good in ((M.assert_overlay, 0.49, 0.5), (M.assert_vt, 1.01, 0.0), (M.assert_vs, -0.01, 1.0)):
        assert fn(good) == good
        try:
            fn(bad)
            raise AssertionError(fn.__name__)
        except ValueError:
            pass


test_cap_01_rule_object_bounds.test_ids = ["T-CAP-01"]


# --------------------------------------------------------------------------- #
# T-BASIS-01 (rules-store predicate on applies_to)
# --------------------------------------------------------------------------- #
def test_basis_01_exposure_basis_predicates():
    r = M.validate_rule_object(_overlay(exposure_basis=None))
    assert r.for_field("exposure_basis") and not r.ok
    r = M.validate_rule_object(_vt(applies_to="momentum", exposure_basis="active"))
    assert any("market_gross" in i.message for i in r.for_field("applies_to"))
    r = M.validate_rule_object(_overlay(applies_to="ts_trend"))
    assert any("ts_trend" in i.message for i in r.for_field("applies_to"))
    r = M.validate_rule_object(_vt(exposure_basis="active"))
    assert r.for_field("exposure_basis")
    seeds = (
        _vt(),
        _vt(rule_id="R-29-US-FUT", books=("forward_sim",), market="US", instrument_book="CME_micro_ES",
            card_id="MACRO-R06-US-FUT", inputs=()),
        _overlay(rule_id="R-28-US-TREND", kind="CARD-P", exposure_basis="total", applies_to="market_gross",
                 books=("forward_sim",), instrument_book="CME_micro_ES", card_id="MACRO-R28-US-TREND"),
        _overlay(rule_id="R-31-KR-STEPS", kind="CARD-P", exposure_basis="total", applies_to="market_gross",
                 market="KR", instrument_book="KRX_ETF_line", card_id="MACRO-R31-KR-ETF", factor="ladder"),
        _overlay(rule_id="R-03-US-VS", output_range=(0.0, 1.0), factor="vs", instrument_book="US_shares_KIS",
                 card_id="MACRO-R03-US-MOM"),
        _overlay(),
        _overlay(rule_id="R-12-S2", kind="CARD-P", exposure_basis="total", applies_to="market_gross",
                 books=("refusal",), card_id="MACRO-R12-US-RATES"),
        RuleObject("R-14-TREND", "CARD-O", None, None, "ts_trend", None, ("specification",), market="US",
                   instrument_book="multi_line", card_id="MACRO-R14-MULTI-TREND", n_rule=M.N_GATE),
    )
    for s in seeds:
        rep = M.validate_rule_object(s)
        assert rep.ok, (s.rule_id, [i.message for i in rep.errors])
    rt = RuleObject.from_dict({**vars(_vt()), "inputs": [vars(i) for i in _vt().inputs], "output_range": [0.0, 1.0]})
    assert rt == _vt() and M.validate_rule_object(rt).ok


test_basis_01_exposure_basis_predicates.test_ids = ["T-BASIS-01"]


# --------------------------------------------------------------------------- #
# T-DNB-01
# --------------------------------------------------------------------------- #
def test_dnb_01_each_refused_shape():
    prev_results = _vt(results_md5="a" * 32, extras={"notional_nav": 1.0e8, "rebalance": "daily", "no_trade_band": 0.0, "cost_bp": 3.0})
    cases = {
        "order_path_or_broker_adapter": (_overlay(extras={"broker_adapter": "kis"}), {}),
        "multiplier_weight_or_cap_above_1": (_overlay(output_range=(0.5, 1.5)), {}),
        "composition_not_min": (_overlay(composition="product"), {}),
        "regime_model_source_acting_or_displayed": (_vt(inputs=(RuleInput("JUMP_STATE", "context", (), "live", "regime_model"),)), {}),
        "smoothed_or_forward_looking_label": (_overlay(extras={"smoothed": True}), {}),
        "ml_classifier_estimator_gate_or_label": (_vt(estimator={"name": "gbm", "kind": "ml"}), {}),
        "conformal_label_layer": (_vt(label_layer="conformal"), {}),
        "sizing_estimator_max_over_implied": (_vt(estimator={"name": "max(sma20, implied)", "kind": "sma", "combine": "max"},
                                                  inputs=(RuleInput("VIXCLS", "acting_exposure", (), "publication", "implied_vol"),)), {}),
        "estimator_change_outside_r30_revision": (_vt(estimator={"name": "gjr_t", "kind": "garch"}), {"previous": _vt()}),
        "header_edit_after_results_md5": (_vt(results_md5="a" * 32, instrument_book="KOSPI200_futures", extras=dict(prev_results.extras)),
                                          {"previous": prev_results}),
        "krx_stock_book_on_market_gross_scalar": (_vt(instrument_book="KRX_stock_book"), {}),
        "pooled_or_a_provisional_tier_after_results": (_vt(tier="A_provisional"), {}),
        "forward_record_cited_as_validation": (_vt(evidence=({"kind": "forward_record", "use": "validation"},)), {}),
        "kish_or_other_n_eff_rule": (_vt(n_rule="M/(1+(M-1)rho)"), {}),
        "r28_instance_market_kr": (_overlay(rule_id="R-28-KR", kind="CARD-P", exposure_basis="total",
                                            applies_to="market_gross", market="KR"), {}),
        "recommended_book_reads_non_pass_multiplier": (_vt(books=("recommended",)), {"verdicts": {"MACRO-R06-KR-ETF": "INSUFFICIENT_DATA"}}),
        "value_timed_or_provisional_acting_input": (_vt(inputs=(RuleInput("DEXKOUS", "acting_exposure", (), "value_proxy", "published_series"),)), {}),
    }
    dnb = M.load_store().do_not_build
    assert set(cases) == set(dnb["refused_shapes"]) == set(M._SHAPE_KEYS)
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "refusals.jsonl"
        for shape, (obj, kw) in cases.items():
            rep = M.validate_rule_object(obj, **kw)
            hits = _items_of(rep, shape)
            assert hits, shape
            ids = dnb["refused_shapes"][shape]
            for n in (ids if isinstance(ids, list) else [ids]):
                assert f" {n} (" in hits[0].message, (shape, hits[0].message)   # names the item ...
            assert any(lab in hits[0].message for lab in ("harm", "null", "inconclusive")), shape   # ... and its label
            assert M.log_refusal(log, obj, rep, _CLOCK) == len(rep.errors)
        assert os.listdir(tmp) == ["refusals.jsonl"]                    # nothing written but the refusal log
        rows = [json.loads(l) for l in log.read_bytes().split(b"\n") if l]
        assert len(rows) == len(cases) and rows[0]["utc"] == "2026-10-06T07:00:00Z"
        assert M.log_refusal(log, _vt(), M.validate_rule_object(_vt()), _CLOCK) == 0
    # the counted-revision and PASS routes are not refused
    assert M.validate_rule_object(_vt(estimator={"name": "gjr_t", "kind": "garch"}), previous=_vt(),
                                  revision={"kind": "r30_counted_revision"}).ok
    assert M.validate_rule_object(_vt(books=("recommended",)), verdicts={"MACRO-R06-KR-ETF": "PASS"}).ok
    assert M.validate_rule_object(_vt(instrument_book="KRX_stock_book"), ).ok is False
    assert M.validate_rule_object(_overlay(rule_id="R-03-US-VS", output_range=(0.0, 1.0), factor="vs",
                                           instrument_book="US_shares_KIS")).ok          # active sleeve on US shares
    assert hashlib.md5(M.SHIPPED_STORE_PATH.read_bytes()).hexdigest() == _SHIPPED_MD5


test_dnb_01_each_refused_shape.test_ids = ["T-DNB-01"]


def test_dnb_01_item_labels_and_split():
    items = M.load_store().get("do_not_build.items")
    assert set(items) == {str(n) for n in range(1, 38)}
    for n in range(1, 38):
        info = M.dnb_item(n)
        for name, v in info["variants"].items():
            if (n, name) in ((11, "11b_range_log_har"), (27, "prohibition")):
                continue
            assert v["label"] in ("harm", "null", "inconclusive") and v["basis"] in ("B", "E", "G"), (n, name, v)
    assert items["11"]["11a_ml_vol_state_classifiers"] == "harm_E" and items["11"]["11b_range_log_har"] == "admitted"
    assert "27 (jump_model: inconclusive_E" in M._label_text(items, 27, None) and "prohibition: binding_red_line_E1" in M._label_text(items, 27, None)
    assert _refused(lambda d: d["do_not_build"]["items"].__setitem__("7", "maybe_E")).count("harm/null/inconclusive") == 1
    assert "11" in _refused(lambda d: d["do_not_build"]["items"].__setitem__("11", "harm_E"))
    assert "17" in _refused(lambda d: d["do_not_build"]["refused_shapes"].pop("conformal_label_layer"))


test_dnb_01_item_labels_and_split.test_ids = ["T-DNB-01"]


# --------------------------------------------------------------------------- #
# T-OWNER-01
# --------------------------------------------------------------------------- #
def test_owner_01_registry_refs_and_ruling():
    store = M.load_store()
    for d in M.DECISIONS:
        e = M.owner_decision(store, d)
        v = store.raw(e["key"])
        assert M._is_scalar(v) and v == e["value"], d
        for p in e["refs"]:
            assert store.raw(p) == {"ref": e["key"]} and store.get(p) == e["value"], p
    assert M.owner_decision(store, "D5")["status"] == "pending" and store.get("instruments.us_line_choice") == "none"
    sites = list(M._ref_sites(store.doc))
    assert len(sites) == 7 and not list(M._ref_sites(store.resolve_refs()))
    assert store.get("vol_target.KR.notional_nav") is None                 # owner input, typed null
    # refused at load
    assert "literal copy that differs" in _refused(lambda d: d["cards"]["R-31_step_down"].__setitem__("hard_stop_level", -0.20))
    assert "literal copy of" in _refused(lambda d: d["cards"]["R-31_step_down"].__setitem__("hard_stop_level", -0.15))
    assert "exactly one key" in _refused(lambda d: d["cards"]["R-31_step_down"].__setitem__("hard_stop_level", {"ref": "risk_layer.drawdown.hard_stop.level", "other": 1}))
    assert "plain scalar" in _refused(lambda d: d["instruments"].__setitem__("us_line_choice", {"ref": "sleeves.US"}))
    assert "registry value" in _refused(lambda d: d["risk_layer"]["korea_caps"].__setitem__("template", "pair_35"))
    assert "D4" in _refused(lambda d: (d["owner_decisions"]["D4"].__setitem__("value", 0.2), d["monitoring"].__setitem__("false_demotion_budget_per_year", 0.2)))
    # a ruling: one governance event, store byte-identical, effective on reload
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        sp = _store_copy(tmp)
        before = sp.read_bytes()
        log = tmp / "governance_events.jsonl"
        h0 = M.load_store(sp).config_hash
        ev = M.apply_owner_ruling(sp, log, "D2", "-1.5*sigma_book", "owner", _CLOCK, rationale="sigma-scaled stop")
        assert sp.read_bytes() == before and ev["prev_row_md5"] is None and ev["kind"] == "owner_ruling"
        assert ev["key"] == "risk_layer.drawdown.hard_stop.level" and ev["old"] == -0.15 and ev["refs"] == ["D2", "cards.R-31_step_down.hard_stop_level"]
        chk = G.verify_chain(log)
        assert chk and chk.n_rows == 1 and chk.first_bad_line is None
        s2 = M.load_store(sp, rulings_log=log)
        d2 = M.owner_decision(s2, "D2")
        assert d2["status"] == "owner_set" and d2["value"] == "-1.5*sigma_book" and d2["default"] == -0.15
        assert s2.get("cards.R-31_step_down.hard_stop_level") == "-1.5*sigma_book" == s2.get(d2["key"])
        assert s2.config_hash != h0 and M.load_store(sp).config_hash == h0
        for d, bad in (("D4", 0.20), ("D5", "IBKR"), ("D1", "msci_30_60"), ("D2", -0.30)):
            try:
                M.apply_owner_ruling(sp, log, d, bad, "owner", _CLOCK)
                raise AssertionError((d, bad))
            except M.MacroRefusal:
                pass
        try:
            M.apply_owner_ruling(sp, log, "D4", 0.05, "operator", _CLOCK)
            raise AssertionError("actor")
        except M.MacroRefusal:
            pass
        att = tmp / "acceptance_runs.jsonl"
        att.write_bytes(b"{}\n")
        try:
            M.apply_owner_ruling(sp, log, "D6", "qf_blind_margin", "owner", _CLOCK, acceptance_log=att)
            raise AssertionError("D6 after an attempt")
        except M.MacroRefusal:
            pass
        ev2 = M.apply_owner_ruling(sp, log, "D4", 0.05, "owner", _CLOCK)
        assert ev2["prev_row_md5"] == G.md5_hex(log.read_bytes().split(b"\n")[0])
        assert G.verify_chain(log).n_rows == 2 and sp.read_bytes() == before
        s3 = M.load_store(sp, rulings_log=log)
        assert s3.get("monitoring.false_demotion_budget_per_year") == 0.05 and M.owner_decision(s3, "D4")["status"] == "owner_set"


test_owner_01_registry_refs_and_ruling.test_ids = ["T-OWNER-01"]


# --------------------------------------------------------------------------- #
# Governance chain (section 6.6)
# --------------------------------------------------------------------------- #
def _event(**over) -> dict:
    ev = {"kind": "book_state", "book_id": "recommended:KR", "rule_id": None, "key": "engine_state",
          "old": "DISARMED", "new": "ARMED", "actor": "runtime",
          "reason": "every acting input bound to the book fresh and past warm-up; calendars cover 60 sessions or more",
          "refs": ["§3.8"]}
    ev.update(over)
    return ev


def test_governance_chain_append_verify_tamper():
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "governance_events.jsonl"
        assert G.verify_chain(log) == (True, 0, None)
        md5s = [G.append_event(log, _event(), _CLOCK), G.append_event(log, _event(kind="halt", reason="hard stop"), _CLOCK),
                G.append_event(log, _event(kind="rearm", reason="t+10"), _CLOCK)]
        lines = log.read_bytes().split(b"\n")
        assert lines[-1] == b"" and len(lines) == 4 and b"\r" not in log.read_bytes()
        rows = [json.loads(l) for l in lines[:3]]
        assert rows[0]["prev_row_md5"] is None and rows[1]["prev_row_md5"] == md5s[0] and rows[2]["prev_row_md5"] == md5s[1]
        assert rows[0]["utc"] == "2026-10-06T07:00:00Z" and rows[0]["schema"] == "quantgen.governance_event"
        assert G.verify_chain(log) == (True, 3, None)
        # the 6.6 example line, typed samples in place of <uuid> and <md5>
        example = dict(_event(), schema="quantgen.governance_event", schema_version="2.0", event_id="1" * 32,
                       utc="2026-10-02T06:41:05Z", prev_row_md5="0" * 32)
        assert G.validate_event(example) == []
        assert G.validate_event({k: v for k, v in example.items() if k != "reason"}) == ["/reason: required"]
        assert G.validate_event(dict(example, extra=1)) == ["/extra: undeclared"]
        assert G.KINDS == S.enum_of("governance_event", "/kind") and "owner_ruling" in G.KINDS
        assert G.ACTORS == S.enum_of("governance_event", "/actor") and set(G.REQUIRED) >= {"prev_row_md5", "utc"}
        # refused before writing: bad kind, bad actor, no utc without a clock, stale prev_row_md5
        size = log.stat().st_size
        for bad, kw in ((_event(kind="rollback"), dict(clock=_CLOCK)), (_event(actor="bot"), dict(clock=_CLOCK)),
                        (_event(), {}), (_event(prev_row_md5="f" * 32), dict(clock=_CLOCK))):
            try:
                G.append_event(log, bad, **kw)
                raise AssertionError(bad)
            except ValueError:
                pass
        assert log.stat().st_size == size
        # tamper: rewrite line 2 canonically with another reason -> line 3's link breaks
        rows[1]["reason"] = "edited"
        lines[1] = G.canonical_json(rows[1]).encode("utf-8")
        log.write_bytes(b"\n".join(lines))
        chk = G.verify_chain(log)
        assert not chk and chk == (False, 2, 3)
        try:
            G.read_events(log)
            raise AssertionError("read_events must refuse a broken chain")
        except ValueError:
            pass
    # two in-process appenders (a Run and an Acknowledge on worker threads) never fork the chain
    import threading
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "governance_events.jsonl"
        workers = [threading.Thread(target=lambda: [G.append_event(log, _event(), _CLOCK) for _ in range(40)]) for _ in range(2)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
        assert G.verify_chain(log) == (True, 80, None)
        # tamper: a reformatted but semantically equal line is still a break (raw bytes are hashed)
        log.write_bytes(b"\n".join([lines[0], json.dumps(json.loads(lines[1]), indent=1).encode()]) + b"\n")
        assert G.verify_chain(log).first_bad_line == 2


test_governance_chain_append_verify_tamper.test_ids = ["T-OWNER-01", "T-SCHEMA-01", "T-OBS-05"]


# --------------------------------------------------------------------------- #
# config_hash / canonical JSON (section 7 reproducibility; T-REPRO-01a metadata)
# --------------------------------------------------------------------------- #
def test_config_hash_stable_and_canonical():
    a, b = M.load_store(), M.load_store()
    assert a.config_hash == b.config_hash and len(a.config_hash) == 32
    d = a.resolve_refs()
    d["gate"].pop("package")
    assert a.config_hash == G.md5_hex(G.canonical_json(d))
    with tempfile.TemporaryDirectory() as tmp:
        sp = _store_copy(Path(tmp), lambda d: d["gate"]["package"].__setitem__("frozen_utc", "2026-12-01T00:00:00Z"))
        assert M.load_store(sp).config_hash == a.config_hash        # gate.package is excluded
        sp = _store_copy(Path(tmp), lambda d: d["vol_target"]["KR"].__setitem__("target_ann", 0.18))
        assert M.load_store(sp).config_hash != a.config_hash
    assert G.canonical_json({"b": 1.0, "a": [0.1, 2, "é"]}) == '{"a":[0.1,2,"é"],"b":1.0}'
    try:
        a.get("vol_target.KR.target_ann_missing")
        raise AssertionError("no default, ever")
    except KeyError:
        pass


test_config_hash_stable_and_canonical.test_ids = ["T-REPRO-01a"]


def test_macro_dir_env_override():
    import config
    names = ("TRADEGEN_MACRO_DIR", "TRADEGEN_HOME", "QUANTGEN_MACRO_DIR")
    saved = {n: os.environ.get(n) for n in names}
    try:
        for n in names:
            os.environ.pop(n, None)
        os.environ["QUANTGEN_MACRO_DIR"] = "X:/quantgen_macro"            # QUANTGEN's variable never redirects TRADEGEN
        assert config.macro_dir() == Path.home() / ".tradegen" / "macro"
        os.environ["TRADEGEN_MACRO_DIR"] = "X:/macro_tmp"
        assert config.macro_dir() == Path("X:/macro_tmp")
        for n, v in (("TRADEGEN_MACRO_DIR", Path.home() / ".nextgen" / "macro"), ("TRADEGEN_HOME", Path.home() / ".nextgen")):
            os.environ.pop("TRADEGEN_MACRO_DIR", None)
            os.environ[n] = str(v)
            try:
                config.macro_dir()
                raise AssertionError(f"{n} into QUANTGEN's ~/.nextgen was accepted")
            except RuntimeError:
                pass
            os.environ.pop(n, None)
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v


def test_every_state_path_stays_out_of_quantgen():
    """TRADEGEN never resolves state into QUANTGEN (split 2026-10-23): every default lies under ~/.tradegen,
    QUANTGEN's variable names are ignored, and aliases of ~/.nextgen or of the QUANTGEN repo are refused by the
    resolver and by the ledger and governance writers before any I/O (metadata stats only, nothing written)."""
    import config
    from core.quant import gate_ledger as GL
    from core.rules import governance as GOV
    from data.krx import kis_client, opendart_client
    from grokteam import book
    q = config.QUANTGEN_STATE
    ours = ("TRADEGEN_HOME", "TRADEGEN_MACRO_DIR", "TRADEGEN_TRADING_DIR", "TRADEGEN_RUNS_DIR", "TRADEGEN_FICC_CACHE")
    theirs = {"QUANTGEN_MACRO_DIR": "macro", "NEXTGEN_TRADING_DIR": "trading", "NEXTGEN_RUNS_DIR": "runs",
              "NEXTGEN_FICC_CACHE": "ficc_cache", "GROKTEAM_LEDGER_DIR": "macro/ledgers"}
    saved = {n: os.environ.get(n) for n in (*ours, *theirs)}
    try:
        for n in ours:
            os.environ.pop(n, None)
        for n, sub in theirs.items():
            os.environ[n] = str(q / sub)                    # set to QUANTGEN's own dirs: must change nothing
        home = (Path.home() / ".tradegen").resolve()
        paths = {"state_root": config.state_root(), "macro": config.macro_dir(), "trading": config.trading_dir(),
                 "runs": config.runs_dir(), "ficc_cache": config.ficc_cache_dir(), "kis_token": kis_client._TOKEN_PATH,
                 "dart_cache": opendart_client._CACHE_PATH, "grokteam": book.DATA}
        for name, p in paths.items():
            assert p.resolve().is_relative_to(home), (name, p)
        aliases = [q / "macro" / "ledgers", Path("\\\\?\\" + str(q.resolve()) + "\\macro"),
                   Path(str(q).upper()) / "trading", config.QUANTGEN_REPO / "grokteam" / "out"]
        for p in aliases:
            for what, call in (("resolver", lambda p=p: config.refuse_quantgen(p)),
                               ("ledger", lambda p=p: GL.family_ledger("X", p)),
                               ("governance", lambda p=p: GOV.append_event(p / "governance_events.jsonl", {}))):
                try:
                    call()
                    raise AssertionError(f"{what} accepted {p}")
                except RuntimeError:
                    pass
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v


# --------------------------------------------------------------------------- #
# TASK-M0-15: E labels bootstrap (section 9.4 item 7) — reference data absent
# --------------------------------------------------------------------------- #
def test_m0_15_e_labels_bootstrap_refdata():
    items = M.load_store().get("do_not_build.items")
    e_labels = sum(1 for n in range(1, 38) for v in M.dnb_item(n, {"items": items})["variants"].values() if v["basis"] == "E")
    assert e_labels == 27                                   # labels stay as shipped until a logged B-label revision
    raise NotRun("REFDATA: qf3_dnb_classes.py and QF3 variant series absent")


test_m0_15_e_labels_bootstrap_refdata.test_ids = ["T-DNB-01"]


def tests():
    return sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
