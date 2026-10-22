"""Sprint 7 integration (tech-fund register): the wiring between the four packages and the Council layer.

- The tech-fund card drafts as section 7.1 rule objects: `docs/techfund_study.rule_object` = draft card fields +
  `tf_books.CARD_RULES` descriptor; `macro_rules.validate_rule_object` (17 Council shapes + DNB-TF-01..17) passes
  every shipped draft and refuses the mutated shapes; the runner's refusal names the DNB hit first (fail closed).
- The drafts against the closed Council header schema where the fields overlap; the refused fields are declared in
  docs/techfund/SCHEMA_AMENDMENT.md and the schema is not loosened.
- FS-2 reads its R-03 scale from `sleeves.sleeve_vol_scale` (`tf_books.fs2_vol_scale`); MissingInput refuses.
- DATA-6: `core.ficc.flows_log` is a protected context module of the T-CTX-01 static scan.
Hermetic: synthetic PIT stores in tempfile directories; nothing written under ~/.nextgen or into the repo.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

import numpy as np

import docs.techfund_study as TS
from core.ficc import context_log as CL
from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import sleeves as SL
from core.quant import tf_books as TB
from core.rules import macro_rules as M
from tests.macro_m1_pit import REG
from tests.macro_m4_sleeves import DEC, KNOW, _paper_store

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "docs" / "techfund" / "SCHEMA_AMENDMENT.md"
HEADER_SCHEMA = ROOT / "core" / "ficc" / "schemas" / "model_card_header.macro.v2.0.json"


def _hits(obj, iid) -> list[str]:
    return [i.message for i in M.dnb_violations(obj) if f"[{iid}]" in i.message]


def _with_tf(cid: str, **tf) -> M.RuleObject:
    obj = TS.rule_object(cid)
    t = {**obj.extras["tf"], **tf}
    return M.RuleObject(**{**vars(obj), "extras": {**obj.extras, "tf": {k: v for k, v in t.items() if v is not None}}})


def test_tf_card_drafts_are_buildable_rule_objects_and_mutations_are_refused():
    assert list(TB.CARD_RULES) == list(TS.DRAFTS)
    for cid in TS.DRAFTS:
        obj = TS.rule_object(cid)
        assert TS.dnb_issues(cid) == [], (cid, TS.dnb_issues(cid))
        tf = obj.extras["tf"]
        assert tf["decision_time"] == "close" and tf["fill"] == "official_close" and tf["horizon_sessions"] >= 1
        assert "recommended" not in obj.books and obj.n_rule == M.N_GATE
        assert obj.books == (("specification",) if cid.startswith("SCR") else ("forward_sim",)), cid
    # the descriptor is what the predicates read: each mutation meets its DNB-TF shape
    assert _hits(_with_tf("FS-2", exclusions=None), "DNB-TF-04")                       # no F4 exclusion
    assert _hits(_with_tf("FS-2", name_cap=0.10), "DNB-TF-04")                         # name cap above 5%
    assert _hits(M.RuleObject(**{**vars(TS.rule_object("FS-2")), "books": ("specification",)}), "DNB-TF-04")
    assert _hits(M.RuleObject(**{**vars(TS.rule_object("FS-3")), "books": ("specification",)}), "DNB-TF-02")
    assert _hits(_with_tf("FS-5", role="alpha", horizon_sessions=5), "DNB-TF-07")       # KRX 1-week reversal
    assert _hits(_with_tf("SCR-1", screen_id="F5"), "DNB-TF-01")                        # attention-fade screen
    assert "cannot be evaluated" in _hits(_with_tf("SCR-1", fill=None), "DNB-TF-13")[0]  # fail closed (D-20)
    assert _hits(_with_tf("FS-1", fill="nxt_after_hours"), "DNB-TF-13")
    # the runner refuses on the DNB hit before the panel check (nothing written)
    saved = copy.deepcopy(TB.CARD_RULES["FS-2"])
    try:
        del TB.CARD_RULES["FS-2"]["extras"]["tf"]["exclusions"]
        why = TS.refusal("FS-2")
        assert why.startswith("DNB: ") and "[DNB-TF-04]" in why, why
        try:
            TS.run_card("FS-2")
            raise AssertionError("FS-2 ran")
        except TS.CardRefused as exc:
            assert exc.reason == why
    finally:
        TB.CARD_RULES["FS-2"] = saved
    assert not TS.refusal("FS-2").startswith("DNB")


test_tf_card_drafts_are_buildable_rule_objects_and_mutations_are_refused.test_ids = ["T-DNB-TF-01", "T-TF-CARD-01"]


def test_tf_drafts_validate_against_the_council_header_where_fields_overlap():
    schema_md5 = hashlib.md5(HEADER_SCHEMA.read_bytes()).hexdigest()
    doc = AMENDMENT.read_text(encoding="utf-8")
    for cid in TS.DRAFTS:
        d = TS.draft(cid)
        h = TS.header_overlap(d)
        assert h["issues"] == [], (cid, h["issues"])
        assert {"card_id", "hypothesis", "rule", "instrument_book", "costs", "data_span"} <= set(h["checked"]), cid
        assert set(h["amended"]) <= set(TS.HEADER_AMENDMENTS), cid
        assert h["deferred"] and all(p.startswith("/data_span/") for p in h["deferred"]), (cid, h["deferred"])
        for field in h["amended"] + h["extensions"]:
            assert f"`{field}`" in doc, f"{field} not declared in {AMENDMENT.name}"
        if d["class"] in ("CARD-O", "CARD-P"):
            assert "class" in h["checked"] and d["costs"]["per_side"] == "read_from_gate"
    assert TS.header_overlap(TS.draft("SCR-1"))["amended"] == ["benchmarks"]
    assert TS.header_overlap(TS.draft("FS-3"))["amended"] == ["class", "comparator"]
    # an undeclared mismatch on an overlapping field is reported, not absorbed
    bad = {**TS.draft("SCR-1"), "instrument_book": "KRX_stock", "comparator": "S_beta_typo"}
    issues = TS.header_overlap(bad)["issues"]
    assert any(i.startswith("/instrument_book: enum") for i in issues) and any(i.startswith("/comparator: enum") for i in issues)
    # the closed schema still refuses the amended values (it was not loosened)
    assert any(p == "/comparator" for p, _ in MS.registry().validate(MS.HEADER_ID, {"comparator": "S_beta"}))
    assert any(p == "/benchmarks/0" for p, _ in MS.registry().validate(MS.HEADER_ID, {"benchmarks": ["EW"]}))
    assert any(p == "/attribution" for p, _ in MS.registry().validate(MS.HEADER_ID, {"attribution": {}}))
    assert hashlib.md5(HEADER_SCHEMA.read_bytes()).hexdigest() == schema_md5


test_tf_drafts_validate_against_the_council_header_where_fields_overlap.test_ids = ["T-TF-CARD-01"]


def test_fs2_reads_its_r03_scale_from_sleeves_and_fails_closed_without_it():
    r = np.random.default_rng(11).normal(0, 0.239 / math.sqrt(252), 200)
    vs = TB.fs2_vol_scale(_paper_store(r), REG, DEC, KNOW, series_id="MOM_PAPER_LS_SERIES")
    assert isinstance(vs, SL.VSResult) and vs.status == "ok" and vs.market == "KR" and vs.family == "momentum"
    assert abs(vs.value - SL.vol_scale_from_returns(r)[0]) < 1e-12
    n = 60
    mom = np.linspace(-1.0, 1.0, n)
    U = np.ones(n, bool)
    excl = np.zeros(n, bool)
    excl[-1] = True                                                    # the top name is an F4 name
    book = TB.fs2_momentum_book(mom, U, excl, 0, vs=vs)
    assert book["book"] == "forward_sim:FS-2" and book["acting"] is False and book["vs"] == vs.value
    assert np.allclose(book["weights"], 0.05 * vs.value) and abs(book["cash"] - (1 - book["weights"].sum())) < 1e-12
    assert n - 1 not in book["members"]
    # no KR paper series is registered: MissingInput -> the book refuses (fail closed)
    miss = TB.fs2_vol_scale(_paper_store(r), REG, DEC, KNOW)
    assert isinstance(miss, P.MissingInput) and "(KR, momentum)" in miss.detail
    try:
        TB.fs2_momentum_book(mom, U, excl, 0, vs=miss)
        raise AssertionError("FS-2 built without its R-03 scale")
    except ValueError as exc:
        assert "fail closed" in str(exc)


test_fs2_reads_its_r03_scale_from_sleeves_and_fails_closed_without_it.test_ids = ["T-TF-FS-02"]


def test_flows_log_is_a_protected_context_module():
    assert "core.ficc.flows_log" in CL.PROTECTED_MODULES
    assert CL.static_isolation_report() == []
    hit = CL.scan_isolation({"core.quant.tf_books": "from core.ficc import flows_log\n", "core.ficc.flows_log": ""})
    assert [(v.module, v.kind) for v in hit] == [("core.quant.tf_books", "import")]


test_flows_log_is_a_protected_context_module.test_ids = ["T-DATA6-01"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
