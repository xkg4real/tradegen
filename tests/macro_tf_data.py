"""Sprint 7 package A tests: shipped tech-fund data, the DNB-TF predicates, the council backlog registry,
the council pages and reports, and the DATA-6 flow log.

Hermetic: reads the repository only (the R3 bundle and the council bundle when present, for byte and line
cross-checks); every write goes to a tempfile directory. Nothing here acts.
"""
from __future__ import annotations

import ast
import collections
import copy
import json
import re
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from core import techfund as T
from core.ficc import flows_log as F
from core.quant import cards
from core.rules import backlog_registry as BR
from core.rules import macro_rules as M
from core.rules.macro_rules import RuleInput, RuleObject

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_R3 = ROOT / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research"
COUNCIL = ROOT / "QUANTGEN_Quant_Council_2026-10-03"
DISCLAIMERS = ("All panel members in these documents are simulated, fictional composites; nothing speaks for any real "
               "firm or person.", "Not investment advice: QUANTGEN is a read-only research desk with no order path.")
# tf_weights_register.md A.1 and tf_goldens_amendments.md A.1 (sha256 / sha256[:16] read on the bundle)
BRIEF_SHA = {"r3_weights_final.csv": "ee2f55a066ac6c33d8993c0eb72ed56f2d01d9b60ff1ea7c3375c8813c4ab7aa",
             "r3_weights_other_markets.csv": "ea55ca0de14f4aa8dfb49c74fd59759afc0942cceeb731d7c4f4f4a1d42ca06c",
             "r3_go_nogo.csv": "9c2a0cff755f1fbcfedae75668097fabb650ba5c28eb61aaeee31bb19d2839f5",
             "R3_TF_nodes.csv": "b9e4749c0a23db819a104ffed84927ff706bb02117967926980cac371683e45e",
             "R3_TF_edges.csv": "b0da1b01194cb802f4e3213f87c78668659c1aa6c0053f0994a52ad66d3002f1",
             "r3_focus_by_theme.json": "85705c549b760bf410ab19cc042fd24210a1db8f62d395364225cdd8252d2097",
             "r3_golden_values.csv": "ca2dfc3fd78d81c3", "r3_pair_share.csv": "66837d6562c7984c",
             "r3_pair_share_summary.csv": "4a82a1199409f13b", "r3_pair_share_2026_daily.csv": "669d359cb9cbe203"}


# --------------------------------------------------------------------------- #
# Shipped data: manifest, row counts, register classes, brief tables
# --------------------------------------------------------------------------- #
def test_tf_manifest_sha256_every_shipped_file():
    assert T.verify_manifest() == []
    listed = T.manifest()["files"]
    on_disk = {p.name for p in T.TF_DIR.iterdir() if p.is_file()} - {T.MANIFEST}
    assert set(listed) == on_disk and len(listed) == 15
    for name, want in BRIEF_SHA.items():
        assert listed[name]["sha256"].startswith(want), name
        src = BUNDLE_R3 / "datalab" / "results" / "r3" / name
        if src.is_file():                                   # verbatim copy of the bundle frame
            assert (T.TF_DIR / name).read_bytes() == src.read_bytes(), name
        assert listed[name]["provenance"].startswith("verbatim copy of"), name
    assert "quantgen_strategy_lab_cards.json" not in listed          # lossy derivative: not shipped
    with tempfile.TemporaryDirectory() as tmp:                      # fail closed on a changed byte
        root = Path(tmp) / "tf"
        shutil.copytree(T.TF_DIR, root)
        p = root / "r3_go_nogo.csv"
        p.write_bytes(p.read_bytes().replace(b"G-77", b"G-78"))
        assert any("r3_go_nogo.csv" in x for x in T.verify_manifest(root))
        try:
            T.register(root)
            raise AssertionError("tampered register was read")
        except T.TechfundDataError:
            pass
        (root / "extra.csv").write_text("a\n1\n", encoding="utf-8")
        assert any("extra.csv: not listed" in x for x in T.verify_manifest(root))
    # display-only: no book, rule or sizing module reads the tech-fund record (tf_weights_register E.4 item 5)
    acting = [*(ROOT / "core" / "engine").rglob("*.py"), *(ROOT / "core" / "rules").rglob("*.py"),
              *[ROOT / "core" / "quant" / f"{m}.py" for m in ("risk", "risk_layer", "sleeves", "optimize", "signals")]]
    readers = [p.relative_to(ROOT).as_posix() for p in acting if p.is_file()
               and re.search(r"core\.techfund|from core import .*\btechfund\b", p.read_text(encoding="utf-8"))]
    assert readers == [], readers


test_tf_manifest_sha256_every_shipped_file.test_ids = ["T-TF-DATA-01"]


def test_tf_row_counts_register_classes_nodes_goldens():
    w = T.weights()
    assert len(w) == 50 and len(T.weights_other_markets()) == 6
    assert len({(r["market"], r["family"], r["column"]) for r in w}) == 50
    assert sum(r["w"] is None for r in w) == 5 and sum(r["flag"] == "*" for r in w) == 6
    assert {r["w"] for r in w} <= {0, 1, 2, 3, None} and {r["column"] for r in w} == {"alpha", "screen", "protective"}
    reg = T.register()
    assert [r["id"] for r in reg] == [f"G-{n:02d}" for n in range(1, 78)]
    assert collections.Counter(r["class"] for r in reg) == {
        "BUILD": 9, "INVARIANT": 6, "GOVERNANCE": 14, "FORWARD-SIM": 5, "BACKLOG": 20, "OWNER DECISION": 3,
        "CONTEXT": 3, "DROP": 17}
    assert collections.Counter(r["section"] for r in reg) == {"10.1": 29, "10.2": 5, "10.3": 20, "10.4": 6, "10.5": 17}
    allowed = {"10.1": {"BUILD", "INVARIANT", "GOVERNANCE"}, "10.2": {"FORWARD-SIM"}, "10.3": {"BACKLOG"},
               "10.4": {"OWNER DECISION", "CONTEXT"}, "10.5": {"DROP"}}
    assert all(r["class"] in allowed[r["section"]] for r in reg)
    nodes = T.nodes()
    assert len(nodes) == 70 and collections.Counter(n["cls"] for n in nodes) == {
        "CORE-LINK": 29, "CORE-PROHIBITION": 18, "CONTESTED": 11, "ONE-SIDED": 8, "UNTESTED": 4}
    ids = {n["node_id"] for n in nodes}
    edges = T.edges()
    assert len(edges) == 85 and collections.Counter(e["type"] for e in edges) == {
        "qualifies": 50, "supports": 18, "refutes": 15, "conflicts": 2}
    assert all(e["source"] in ids and e["target"] in ids for e in edges)
    for r in w + reg:
        assert set(re.findall(r"TF-\d\d", r["nodes"])) <= ids
    g = T.goldens()
    assert [r["gv_id"] for r in g] == [f"GV-{n:03d}" for n in range(1, 524)]
    assert collections.Counter(r["status"] for r in g) == {"traced": 497, "derived": 20, "not traced": 6}
    share = {r["item"]: r["value"] for r in T.rows("r3_pair_share_summary.csv")}
    assert share["CR-07 share on 2026-09-29"] == "0.537062"            # reference constant (CR-07; R3:1295)
    try:
        T.register_class("SOMETHING NEW")
        raise AssertionError("unknown decision prefix accepted")
    except T.TechfundDataError:
        pass


test_tf_row_counts_register_classes_nodes_goldens.test_ids = ["T-TF-DATA-02"]


def _r3_lines():
    p = BUNDLE_R3 / "research_notes" / "R3_TF_neural_link.md"
    return p.read_text(encoding="utf-8").split("\n") if p.is_file() else None


def _cited(r3, refs, needles):
    for ref in refs:
        a, *b = [int(x) for x in re.split(r"[-–]", ref)]
        if any(any(n in r3[k - 1] for n in needles) for k in range(a, (b[0] if b else a) + 1)):
            return True
    return False


def test_tf_brief_tables_cite_r3_and_xs_statuses():
    dnb, bl, oq, xs, ca = (T.dnb_tf_items(), T.backlog_tf_items(), T.open_questions(),
                           T.cross_spec_amendments(), T.corrected_anchors())
    assert [d["id"] for d in dnb] == [f"DNB-TF-{n:02d}" for n in range(1, 18)]
    assert [d["id"] for d in bl] == [f"BL-TF-{n:02d}" for n in range(1, 21)]
    assert [d["id"] for d in oq] == [f"OQ-{n:02d}" for n in range(1, 16)]
    assert [d["id"] for d in xs] == [f"XS-{n:02d}" for n in range(1, 23)]
    assert [d["id"] for d in ca] == [f"CA-{n:02d}" for n in range(1, 39)]
    assert collections.Counter(d["status"] for d in xs) == {"ADOPTED": 6, "CONFLICT": 8, "OPEN": 6, "PARTIAL": 2}
    assert {d["id"] for d in xs if d["status"] == "PARTIAL"} == {"XS-09", "XS-10"}
    assert all(d["acting"] is False for d in bl + oq + xs)
    assert all(d["owner_status"] == "proposal pending owner confirmation" for d in oq + xs)
    assert all(d["label_r3"] == "not given" and d["label_proposed"] for d in dnb)    # R3 gives no label (D-1)
    r3 = _r3_lines()
    for d in dnb + bl + oq + xs + ca:
        assert d["r3_lines"], d["id"]
        if r3 is not None:
            needles = [d["id"], d.get("node") or d["id"], *d.get("g_ids", ())]
            assert _cited(r3, d["r3_lines"], needles), d["id"]


test_tf_brief_tables_cite_r3_and_xs_statuses.test_ids = ["T-TF-DATA-03"]


# --------------------------------------------------------------------------- #
# DNB-TF-01..17: each refuses its shape; the allow-list (or the near miss) passes
# --------------------------------------------------------------------------- #
_BASE_TF = {"signal_family": "other", "role": "alpha", "horizon_sessions": 21, "decision_time": "close",
            "fill": "official_close"}


def _ro(tf=None, **kw) -> RuleObject:
    base = dict(rule_id="TF-TEST", kind="CARD-O", books=("specification",), market="KR")
    base.update(kw)
    if tf is not None:
        base["extras"] = {"tf": {**_BASE_TF, **tf}}
    return RuleObject(**base)


def _inp(source_kind, role="acting_exposure", timing="publication"):
    return (RuleInput("TF_SERIES", role, ("specification",) if role == "acting_exposure" else (), timing, source_kind),)


def _tf_hits(obj, iid=None):
    return [i.message for i in M.dnb_violations(obj) if "tech-fund DO-NOT-BUILD" in i.message
            and (iid is None or f"[{iid}]" in i.message)]


_KR_STOCK = dict(market="KR", instrument_book="KRX_stock_book")
CASES = {   # id -> (refused shapes, allowed shapes)
    "DNB-TF-01": ([_ro({"signal_family": "attention_fade", "role": "screen", "screen_id": "F5", "rebalance": "monthly"})],
                  [_ro({"signal_family": "limit_lock", "role": "risk_control", "horizon_sessions": 0,
                        "screen_features": ["locked_limit_up_20s"]}, kind="INVARIANT")]),
    "DNB-TF-02": ([_ro({"signal_family": "low_vol", "role": "alpha"})],
                  [_ro({"signal_family": "low_vol", "role": "protective", "comparator": "S_beta"}, books=("forward_sim",)),
                   _ro({"signal_family": "low_vol", "role": "screen_input"})]),
    "DNB-TF-03": ([_ro({"signal_family": "size", "role": "alpha"}, market="US")],
                  [_ro({"signal_family": "size", "role": "attribution_factor"}, market="US")]),
    "DNB-TF-04": ([_ro(None, applies_to="momentum", **_KR_STOCK),
                   _ro({"signal_family": "momentum_12_1"}, applies_to="momentum", **_KR_STOCK)],
                  [_ro({"signal_family": "momentum_12_1", "exclusions": ["F4"], "vol_scale": "R-03", "name_cap": 0.05,
                        "long_only": True}, applies_to="momentum", books=("forward_sim",), **_KR_STOCK)]),
    "DNB-TF-05": ([cards.rule_object("MACRO-R06-US")], [cards.rule_object("MACRO-R06-US-FUT")]),
    "DNB-TF-06": ([_ro({"signal_family": "investor_flow"}, inputs=_inp("tf.investor_flow"))],
                  [_ro({"signal_family": "investor_flow", "role": "context"}, kind="CONTEXT", books=(),
                       inputs=_inp("tf.investor_flow", "context", "t-1_timestamped"))]),
    "DNB-TF-07": ([_ro({"signal_family": "st_reversal", "horizon_sessions": 5}, applies_to="reversal", **_KR_STOCK),
                   _ro(None, applies_to="reversal", **_KR_STOCK)],               # no descriptor: fail closed (D-20)
                  [_ro({"signal_family": "st_reversal", "role": "screen_guard", "rebalance": "monthly"},
                       applies_to="reversal", books=("forward_sim",), **_KR_STOCK)]),
    "DNB-TF-08": ([_ro({"signal_family": "quality", "role": "hedge"}, market="US", applies_to="quality"),
                   _ro({"signal_family": "quality", "role": "composite_leg", "prior_weight": 2}, applies_to="quality")],
                  [_ro({"signal_family": "quality", "role": "composite_leg", "prior_weight": 2}, market="US",
                       applies_to="quality")]),
    "DNB-TF-09": ([_ro({"signal_family": "pead"}, market="US")],
                  [_ro({"signal_family": "pead", "role": "flag"}, market="US", kind="CONTEXT", books=())]),
    "DNB-TF-10": ([_ro({"signal_family": "canslim"}, market="US", inputs=_inp("tf.product_screen"))],
                  [_ro({"signal_family": "revisions"}, market="US", inputs=_inp("tf.estimate_revision", timing="archive_timestamp"))]),
    "DNB-TF-11": ([_ro({"signal_family": "cape"}, market="US", inputs=_inp("tf.valuation_ratio"))],
                  [_ro({"signal_family": "cape", "role": "context"}, market="US", kind="CONTEXT", books=(),
                       inputs=_inp("tf.valuation_ratio", "context"))]),
    "DNB-TF-12": ([_ro({"signal_family": "rsi"}, inputs=_inp("tf.technical_indicator"))],
                  [_ro({"signal_family": "rsi", "family_ledger": "technical_rule", "family_id": "TECH-RSI-01",
                        "family_gate": "SPA", "repaint_check": "passed"}, inputs=_inp("tf.technical_indicator"))]),
    "DNB-TF-13": ([_ro({"signal_family": "opening_range", "horizon_sessions": 0}),
                   _ro({"signal_family": "ma_cross"}, **_KR_STOCK),
                   _ro({"signal_family": "momentum", "fill": "nxt_after_hours"}, market="US")],
                  [_ro({"signal_family": "lottery", "role": "screen", "screen_id": "F4", "rebalance": "monthly"},
                       **_KR_STOCK)]),                                         # SCR-1 at the close: allowed
    "DNB-TF-14": ([_ro({"signal_family": "llm_news"}, market="US", inputs=_inp("tf.llm_text"))],
                  [_ro({"signal_family": "llm_news", "role": "context"}, market="US", kind="CONTEXT", books=(),
                       inputs=_inp("tf.llm_text", "research_log"))]),
    "DNB-TF-15": ([_ro({"signal_family": "composite", "composite": True,
                        "combiner_terms": ["characteristic", "interaction_macro_x_characteristic"]})],
                  [_ro({"signal_family": "composite", "composite": True, "combiner_terms": ["characteristic"]})]),
    "DNB-TF-16": ([_ro({"signal_family": "st_reversal", "horizon_sessions": 7, "prior_weight": 2}, market="CRYPTO",
                       applies_to="reversal")],
                  [_ro({"signal_family": "ts_trend", "horizon_sessions": 252, "prior_weight": 2}, market="CRYPTO",
                       applies_to="ts_trend")]),                               # C3 trend control: out of scope
    "DNB-TF-17": ([_ro({"signal_family": "fx_trend", "prior_weight": 1}, market="FX")],
                  [_ro({"signal_family": "fx_trend", "backlog_id": "BL-TF-20", "pair": "USDKRW", "speed": "slow",
                        "cost_bp_per_side": 10, "horizon_sessions": 126}, market="FX", books=("forward_sim",))]),
}


def test_dnb_tf_predicates_refuse_shapes_and_pass_allow_lists():
    items = M.load_store().get("do_not_build.tf_items")
    rows = {d["id"]: d for d in T.dnb_tf_items()}
    assert [i["id"] for i in items] == list(rows) == list(CASES)
    for it in items:
        assert set(it) == {"id", "text", "label_proposed", "predicate", "allow_list", "r3_lines"}, it["id"]
        assert it["text"] == rows[it["id"]]["refused"] and it["r3_lines"] == rows[it["id"]]["r3_lines"]
        assert it["label_proposed"] == rows[it["id"]]["label_proposed"]
        assert it["predicate"]["scope"] or it["predicate"]["when"], it["id"]       # never "refuse everything"
    for iid, (refused, allowed) in CASES.items():
        for obj in refused:
            assert _tf_hits(obj, iid), (iid, obj)
        for obj in allowed:
            assert not _tf_hits(obj), (iid, _tf_hits(obj))
    assert "cannot be evaluated" in _tf_hits(_ro(None, applies_to="reversal", **_KR_STOCK), "DNB-TF-07")[0]
    assert "(proposed label trend: harm_E, vt15: null_E)" in _tf_hits(cards.rule_object("MACRO-R06-US"), "DNB-TF-05")[0]
    # Council governs its own objects: of the registered macro cards only the 50 bp US card (already REJECT,
    # DNB item 33) meets a tech-fund shape
    hit = {cid: bool(_tf_hits(cards.rule_object(cid))) for cid in cards.BY_ID}
    assert {cid for cid, h in hit.items() if h} == {"MACRO-R06-US"}, hit
    # the predicates are store data: an empty tf_items list refuses nothing; an unknown op refuses the store item
    dnb = copy.deepcopy(M._shipped_dnb())
    assert not [i for i in M.dnb_violations(CASES["DNB-TF-07"][0][0], dnb={**dnb, "tf_items": []}) if "DNB-TF" in i.message]
    bad = copy.deepcopy(dnb)
    bad["tf_items"][6]["predicate"]["when"] = {"path": "tf.role", "matches": "alpha"}
    try:
        M.dnb_violations(CASES["DNB-TF-07"][0][0], dnb=bad)
        raise AssertionError("unknown predicate op accepted")
    except M.MacroRefusal:
        pass


test_dnb_tf_predicates_refuse_shapes_and_pass_allow_lists.test_ids = ["T-DNB-TF-01"]


# --------------------------------------------------------------------------- #
# Council backlog registry
# --------------------------------------------------------------------------- #
def test_backlog_registry_counts_keys_only_and_never_acting():
    reg = BR.load_registry()
    assert {k: len(v) for k, v in reg.items()} == {"status_board": 46, "council_queue": 22, "settling_test": 11,
                                                   "owner_decision": 6, "data_acq": 31, "data_quality": 22}
    assert all(r["acting"] is False for rows in reg.values() for r in rows)
    assert collections.Counter(r["status"] for r in reg["status_board"]) == {
        "OPEN": 34, "MOVED": 4, "RETIRED": 2, "RESOLVED": 2, "CLOSED": 2, "OWNER-DECISION": 1, "RECORD_ONLY": 1}
    assert collections.Counter(r["class"] for r in reg["status_board"]) == {"S": 2, "C": 14, "O": 14, "U": 7, "G": 9}
    assert collections.Counter(r["class"] for r in reg["council_queue"]) == {
        "VALID-SHADOW": 7, "CONTESTED": 3, "CONTEXT-ONLY": 9, "OWNER-DECISION": 3}
    assert collections.Counter(r["priority"] for r in reg["data_acq"]) == {"P1": 11, "P2": 11, "P3": 9}
    store = M.load_store()
    for r in reg["owner_decision"]:                    # keys only; the value in force lives in the store
        assert "value" not in r and "options" not in r
        assert r["rules_key"] == M.owner_decision(store, r["item_id"])["key"], r["item_id"]
    doc = json.loads(BR.REGISTRY_PATH.read_text(encoding="utf-8"))
    for mutate, needle in ((lambda d: d["collections"]["council_queue"][0].__setitem__("acting", True), "acting"),
                           (lambda d: d["collections"]["owner_decision"][0].__setitem__("value", "msci_25_50"), "rules_key only"),
                           (lambda d: d["collections"]["data_quality"].pop(), "data_quality: 21 rows"),
                           (lambda d: d["collections"]["status_board"][0].__setitem__("status", "LIVE"), "status"),
                           (lambda d: d["collections"]["status_board"][3]["blocking_data"].append("BL-D99"), "BL-D99")):
        bad = copy.deepcopy(doc)
        mutate(bad)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "reg.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            try:
                BR.load_registry(p)
                raise AssertionError(needle)
            except ValueError as exc:
                assert needle in str(exc), (needle, str(exc)[:300])


test_backlog_registry_counts_keys_only_and_never_acting.test_ids = ["T-BL-REG-01"]


# --------------------------------------------------------------------------- #
# Council pages and reports
# --------------------------------------------------------------------------- #
_QG = re.compile(r'<script type="application/json" id="qg-data">(.*?)</script>', re.S)


def test_council_pages_offline_with_one_parsing_data_block():
    docs = ROOT / "docs" / "council"
    data = {}
    for name, key in (("QUANTGEN_Quant_Council.html", "quant_council"),
                      ("QUANTGEN_Macro_Neural_Link.html", "macro_neural_link")):
        s = (docs / name).read_text(encoding="utf-8")
        assert s.count('id="qg-data"') == 1, name
        assert not any(bad in s for bad in ("<script src=", "<img src=", "fetch(")), name
        data[key] = json.loads(_QG.search(s).group(1))
        src = COUNCIL / "pages" / name
        if src.is_file():
            assert (docs / name).read_bytes() == src.read_bytes(), name
    qc, ml = data["quant_council"], data["macro_neural_link"]
    assert qc["ledger_n"] == 361 and len(qc["modules"]) == 34 and len(ml["nodes"]) == 60
    assert json.loads((docs / "council_pages_data.json").read_text(encoding="utf-8")) == data
    readme = (docs / "README.md").read_text(encoding="utf-8")
    assert all(d in readme for d in DISCLAIMERS)


test_council_pages_offline_with_one_parsing_data_block.test_ids = ["T-COUNCIL-DOCS-01"]


def test_council_reports_copied_with_both_disclaimers_verbatim():
    for dst, src in (("QUANTGEN_Quant_Council_Report.md", "QUANTGEN_Quant_Council_Report.md"),
                     ("QUANTGEN macro overlay research.md", "QUANTGEN_macro_overlay_research_report.md")):
        b = (ROOT / "reports" / dst).read_bytes()
        head, sep, body = b.partition(b"\n---\n\n")
        assert sep and all(d.encode("utf-8") in head for d in DISCLAIMERS), dst
        if (COUNCIL / "reports" / src).is_file():
            assert body == (COUNCIL / "reports" / src).read_bytes(), dst
    stub = ROOT / "research_notes" / "QUANTGEN macro overlay research" / "council"
    assert [p.name for p in stub.iterdir()] == ["README.md"]               # pointer only; no fabricated QC_*/ASPEC_*
    tf_readme = ROOT / "research_notes" / "QUANTGEN technical and fundamental signals" / "README.md"
    assert "QUANTGEN_techfund_research_bundle" in tf_readme.read_text(encoding="utf-8")


test_council_reports_copied_with_both_disclaimers_verbatim.test_ids = ["T-COUNCIL-DOCS-01"]


# --------------------------------------------------------------------------- #
# DATA-6 flow log: timestamps, t-1 history, never a direction
# --------------------------------------------------------------------------- #
def test_flows_log_records_not_available_and_never_emits_a_direction():
    when = datetime(2026, 10, 6, 7, 0, 0, tzinfo=timezone.utc)
    rows = F.record(date(2026, 10, 6), when)
    assert [r["investor_type"] for r in rows] == list(F.INVESTOR_TYPES)
    assert all(r["status"] == "not_available" and r["net_buy_krw"] is None and r["detail"] for r in rows)
    fake = lambda d: {t: {"net_buy_krw": v, "status": "final", "source": "synthetic",       # noqa: E731
                          "published_utc": "2026-10-05T07:30:00+00:00"}
                      for t, v in zip(F.INVESTOR_TYPES, (-1.0e11, 4.0e10, 6.0e10))}
    final = F.record(date(2026, 10, 5), when, fetch=fake)
    for r in rows + final:
        assert tuple(r) == F.FIELDS
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "flows.jsonl"
        assert F.append(p, final) == 3 and F.append(p, rows) == 3
        log = F.read(p)
    assert len(log) == 6 and F.usable_history(log, date(2026, 10, 5)) == []             # same session: not usable
    assert [r["investor_type"] for r in F.usable_history(log, date(2026, 10, 6))] == list(F.INVESTOR_TYPES)
    try:
        F.record(date(2026, 10, 6), datetime(2026, 10, 6, 7))
        raise AssertionError("naive timestamp accepted")
    except ValueError:
        pass
    # static guard: no direction / sign / side / signal anywhere in the module's names or row fields
    tree = ast.parse(Path(F.__file__).read_text(encoding="utf-8"))
    names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    names |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    bad = re.compile(r"direction|signal|sign\b|_sign|side|long|short|position|weight|multiplier", re.I)
    assert not [n for n in names | set(F.FIELDS) if bad.search(n)], names
    assert F.ACTS is False
    from core.ficc import context_log as CL      # context_log names it in PROTECTED_MODULES (S7 integration)
    importers = [m for m, src in CL.repo_modules(ROOT).items()
                 if m != "core.ficc.flows_log" and "core.ficc.flows_log" in CL.imports_of(m, src)[0]]
    assert importers == [] and "core.ficc.flows_log" in CL.PROTECTED_MODULES, importers


test_flows_log_records_not_available_and_never_emits_a_direction.test_ids = ["T-DATA6-01"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
