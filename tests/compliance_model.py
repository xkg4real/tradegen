"""Shared model (Task 6; contract section 5; P2, P5): canonical JSON, hashes, sealed contexts and derived ids.

No network, no clock, no file writes; the shipped drafts are only read, by the ctx() fixture.
"""
from __future__ import annotations

import dataclasses
import math
from datetime import date, datetime, timezone

from core.compliance import model
from tests import compliance_fixtures as F

_PLAIN = [
    {"b": 1, "a": [1, 2.5, "x"], "c": {"z": None, "y": True}},
    ["한글", "é", -0.0, 1e-7, 10**20, False],
    {"nested": {"k": [{"q": 0.1}, []], "": {}}},
    "text", 3, 2.0, None,
]


def _raises(exc: type[BaseException], fn) -> None:
    """`fn()` must raise `exc`."""
    try:
        fn()
    except exc:
        return
    raise AssertionError(f"did not raise {exc.__name__}")


def test_canonical_json_matches_macro_schema():
    from core.ficc.macro_schema import canonical_json as reference
    for sample in _PLAIN:
        assert model.canonical_json(sample) == reference(sample), sample


def test_jsonable_handles_sets_tuple_keys_dates_and_dataclasses():
    @dataclasses.dataclass(frozen=True)
    class Inner:
        when: date
        tags: frozenset

    @dataclasses.dataclass(frozen=True)
    class Outer:
        inner: Inner
        book: dict

    one = Outer(inner=Inner(when=date(2026, 10, 23), tags=frozenset({"b", "a"})),
                book={("upbit", "BTC"): 0.5, "x": (1, 2)})
    two = Outer(inner=Inner(when=date(2026, 10, 23), tags=frozenset({"a", "b"})),
                book={"x": (1, 2), ("upbit", "BTC"): 0.5})
    assert model.jsonable(one) == {"inner": {"when": "2026-10-23", "tags": ["a", "b"]},
                                   "book": {"upbit|BTC": 0.5, "x": [1, 2]}}
    assert model.canonical_json(one) == model.canonical_json(two)
    assert model.jsonable(frozenset({("BTC", "USDT"), ("BTC", "KRW")})) == [["BTC", "KRW"], ["BTC", "USDT"]]
    assert model.jsonable(frozenset({1, "a"})) == ["a", 1]                  # mixed types sort by their JSON text
    names = [f"s{n:02d}" for n in range(20)]
    assert model.jsonable(frozenset(reversed(names))) == names               # not the set's own (salted) order
    for bad in (math.nan, math.inf, -math.inf):
        _raises(ValueError, lambda: model.jsonable({"x": [bad]}))
        _raises(ValueError, lambda: model.canonical_json(bad))
    _raises(TypeError, lambda: model.canonical_json({"x": object()}))
    _raises(TypeError, lambda: model.canonical_json(b"bytes"))
    _raises(ValueError, lambda: model.jsonable({1: "a", "1": "b"}))        # two keys that read the same


def test_intent_hash_is_stable_and_changes_with_any_field():
    base = F.intent()
    assert model.intent_hash(base) == model.intent_hash(F.intent()) and len(model.intent_hash(base)) == 64
    changes = {"venue": "okx", "symbol": "USDT", "counter_symbol": "USDT", "asset": "us_etp", "multiple": 2.0,
               "action": "sell", "financing": "credit", "quantity": 0.002, "notional_krw": 50_001.0,
               "destination_venue": "bithumb", "destination_address": "addr", "destination_network": "bitcoin",
               "destination_tag": "7", "route": "vpn", "on_behalf": "friend", "publishes_signal": True,
               "tags": frozenset({"spoof"}), "reservation_id": "R1"}
    assert set(changes) == {f.name for f in dataclasses.fields(model.Intent)}, "a new Intent field needs a case"
    for name, value in changes.items():
        assert model.intent_hash(dataclasses.replace(base, **{name: value})) != model.intent_hash(base), name
    _raises(ValueError, lambda: model.intent_hash(F.intent(quantity=math.nan)))


def test_seal_context_registers_and_hand_built_is_refused():
    sealed = F.ctx(active=model.ApprovedState.invalid("fixture"))
    assert model.is_sealed(sealed) and len(sealed.ctx_hash) == 64
    fields = {f.name: getattr(sealed, f.name) for f in dataclasses.fields(model.Context)}
    hand = model.Context(**fields)
    assert hand == sealed and not model.is_sealed(hand)                 # same fields, not sealed
    assert not model.is_sealed(dataclasses.replace(sealed, equity_krw=2.0))
    assert not model.is_sealed(None) and not model.is_sealed(object()) and not model.is_sealed(fields)
    again = model.seal_context(**fields)                               # a passed ctx_hash is ignored
    assert model.is_sealed(again) and again.ctx_hash == sealed.ctx_hash and again is not sealed
    changes = {"date": date(2026, 10, 24), "active": model.ApprovedState.invalid("other"),
               "snapshot": model.ApprovedState.invalid("s"), "owner": model.OwnerState.broken("x"),
               "code_hash": "d" * 64, "code_signed": False, "session": model.SessionState(), "equity_krw": 2.0,
               "holdings": {("upbit", "BTC"): 1.0}, "shorts": {("kis", "005930"): 1.0},
               "exposure": {"upbit": model.Exposure(held_krw=1.0)}, "live_evidence": frozenset({"deposit_krw_10m"})}
    assert set(changes) | {"ctx_hash"} == {f.name for f in dataclasses.fields(model.Context)}, \
        "a new Context field needs a case"
    for name, value in changes.items():                                # ctx_hash covers every field
        assert model.seal_context(**{**fields, name: value}).ctx_hash != sealed.ctx_hash, name
    _raises(TypeError, lambda: model.seal_context(**{**fields, "extra": 1}))
    _raises(ValueError, lambda: model.seal_context(**{**fields, "equity_krw": math.nan}))


def test_fixture_ctx_is_sealed_and_valid():
    c = F.ctx()
    assert model.is_sealed(c)
    assert c.active.valid, c.active.reason
    assert c.active.seq == 3 and set(c.active.hashes) == {"rules", "instruments", "venues"}
    assert c.date == date(2026, 10, 23) and c.owner.ok and c.code_signed and c.session.armed
    assert F.approved() is F.approved()                                # parsed once per bytes
    assert F.approved(seq=1).valid and not F.approved(seq=True).valid  # typed cache: True is not 1
    i = F.intent()
    assert (i.venue, i.symbol, i.counter_symbol, i.action, i.quantity, i.notional_krw) == \
        ("upbit", "BTC", "KRW", "buy", 0.001, 50_000.0)


def test_decision_id_changes_with_any_field():
    d = model.Decision(verdict=model.ALLOW, kind="new_exposure", reasons=(), intent_hash="i" * 64,
                       state_hash="s" * 64, code_hash="c" * 64, owner_head=(10, "a" * 64), ctx_hash="x" * 64,
                       date=date(2026, 10, 23))
    assert len(d.decision_id) == 64 and dataclasses.replace(d).decision_id == d.decision_id
    assert dataclasses.replace(d, decision_id="forged").decision_id == d.decision_id     # always derived
    changes = {"verdict": model.BLOCK, "kind": "malformed", "reasons": ("no row",), "warnings": ("w",),
               "intent_hash": "j" * 64, "state_hash": "", "code_hash": "d" * 64, "owner_head": (11, "a" * 64),
               "ctx_hash": "y" * 64, "date": date(2026, 10, 24), "ack": ("KR-OKX-SPOT", "w" * 64)}
    assert set(changes) | {"decision_id"} == {f.name for f in dataclasses.fields(model.Decision)}
    for name, value in changes.items():
        assert dataclasses.replace(d, **{name: value}).decision_id != d.decision_id, name


def test_invalid_state_has_empty_state_hash():
    bad = model.ApprovedState.invalid("rules: larger than 256 KB")
    assert (bad.valid, bad.reason, bad.state_hash, bad.rules, bad.seq) == (False, "rules: larger than 256 KB",
                                                                          "", None, 0)
    good = model.ApprovedState(valid=True, hashes={"rules": "r" * 64}, seq=3)
    assert len(good.state_hash) == 64
    assert dataclasses.replace(good, seq=4).state_hash != good.state_hash
    assert dataclasses.replace(good, hashes={"rules": "q" * 64}).state_hash != good.state_hash


def test_iso_utc_refuses_naive():
    assert model.iso_utc(datetime(2026, 12, 3, 0, 0, 0, tzinfo=model.KST)) == "2026-12-02T15:00:00Z"
    assert model.iso_utc(datetime(2026, 10, 23, 1, 2, 3, tzinfo=timezone.utc)) == "2026-10-23T01:02:03Z"
    _raises(ValueError, lambda: model.iso_utc(datetime(2026, 10, 23, 1, 2, 3)))
    _raises(ValueError, lambda: model.iso_utc(date(2026, 10, 23)))


def test_constants_owner_state_and_sha256():
    assert (model.ALLOW, model.ALLOW_EXIT, model.ACK_REQUIRED, model.BLOCK) == \
        ("ALLOW", "ALLOW_EXIT", "ACK_REQUIRED", "BLOCK")
    assert model.KST.key == "Asia/Seoul"                               # not just any +09:00 zone
    b = model.OwnerState.broken("no owner key yet: owner act 1", head=(4, "b" * 64), fingerprint="SHA256:x")
    assert (b.ok, b.status, b.head, b.fingerprint, dict(b.caps), b.addresses) == \
        (False, "BROKEN", (4, "b" * 64), "SHA256:x", {}, frozenset())
    assert model.OwnerState(status="OK").ok and not model.SessionState().armed
    abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert model.sha256_hex("abc") == model.sha256_hex(b"abc") == abc


def test_dataclasses_are_frozen_and_keyword_only():
    for cls in (model.Intent, model.Exposure, model.Positions, model.ApprovedState, model.OwnerState,
                model.SessionState, model.Context, model.Decision, model.Permit, model.Screening):
        assert cls.__dataclass_params__.frozen, cls.__name__
        assert all(f.kw_only for f in dataclasses.fields(cls)), cls.__name__
    _raises(dataclasses.FrozenInstanceError, lambda: setattr(F.intent(), "quantity", 1.0))
