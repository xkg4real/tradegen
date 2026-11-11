"""Upbit KRW universe, pure compliance code (universe spec sections 4 and 5; plan PR 1): the flag classes, the
request set, finality from content, the medians, and the snapshot file with its verification. Every body is an
inline fixture; nothing reads the network, the clock or a file."""
from __future__ import annotations

import json

from core.compliance import rules

CAUTIONS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING", "GLOBAL_PRICE_DIFFERENCES",
            "CONCENTRATION_OF_SMALL_ACCOUNTS")


def _entry(market: str, *, warning=False, **caution) -> dict:
    """One market object of market/all?is_details=true; every known caution key is false unless given."""
    return {"market": market, "korean_name": "x", "english_name": market.split("-")[-1],
            "market_event": {"warning": warning, "caution": {**{key: False for key in CAUTIONS}, **caution}}}


def _body(value) -> bytes:
    return json.dumps(value).encode("utf-8")


def _code(call) -> str:
    """The refusal code of the UniverseError that `call()` raises."""
    try:
        call()
    except rules.UniverseError as exc:
        return str(exc)
    raise AssertionError("accepted; expected UniverseError")


# -- flag classes (spec section 4) ---------------------------------------------------------------------------------
def test_flag_classes_follow_spec_4_exactly():
    assert rules.FLAG_CLASSES == ("unflagged", "warning", "caution", "unknown", "absent")
    assert rules.flag_class(_entry("KRW-BTC")) == "unflagged"
    assert rules.flag_class(None) == "absent"                                        # a missing coin
    assert rules.flag_class(_entry("KRW-BTC", warning=True)) == "warning"
    assert rules.flag_class(_entry("KRW-BTC", warning=True, PRICE_FLUCTUATIONS=True)) == "warning"
    for key in CAUTIONS:
        assert rules.flag_class(_entry("KRW-BTC", **{key: True})) == "caution", key
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=True)) == "caution"   # an unknown key included
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=False)) == "unflagged"


def test_flag_class_unknown_for_a_missing_or_malformed_field():
    no_event = _entry("KRW-BTC")
    del no_event["market_event"]
    assert rules.flag_class(no_event) == "unknown"                                   # a missing market_event
    calm = {key: False for key in CAUTIONS}
    for event in (None, [], "warning", {"caution": calm}, {"warning": None, "caution": calm},
                  {"warning": 0, "caution": calm}, {"warning": "false", "caution": calm}, {"warning": False},
                  {"warning": False, "caution": None}, {"warning": False, "caution": []}):
        assert rules.flag_class({"market": "KRW-BTC", "market_event": event}) == "unknown", event
    for key in CAUTIONS:
        missing = _entry("KRW-BTC")
        del missing["market_event"]["caution"][key]
        assert rules.flag_class(missing) == "unknown", key                           # a missing key
        for bad in (None, 0, 1, "false", "true"):
            assert rules.flag_class(_entry("KRW-BTC", **{key: bad})) == "unknown", (key, bad)   # not a boolean
    assert rules.flag_class([]) == rules.flag_class("KRW-BTC") == "unknown"         # not a market object


def test_market_flags_reads_krw_markets_and_refuses_a_bad_body():
    assert issubclass(rules.UniverseError, ValueError)
    assert str(rules.UniverseError("UNIVERSE_BODY_INVALID")) == "UNIVERSE_BODY_INVALID"
    body = _body([_entry("KRW-BTC"), _entry("KRW-ADA", warning=True), _entry("KRW-DOGE", TRADING_VOLUME_SOARING=True),
                  {"market": "KRW-ETH"}, _entry("BTC-ETH"), _entry("USDT-BTC"), _entry("KRW-btc"),
                  _entry("KRW-ABCDEFGHIJKLM"), {"market": 1}, {"korean_name": "x"}])
    assert rules.market_flags(body) == {"KRW-BTC": "unflagged", "KRW-ADA": "warning", "KRW-DOGE": "caution",
                                        "KRW-ETH": "unknown"}
    assert rules.market_flags(b"[]") == {}
    for bad in (b"", b"{}", b"null", b'"KRW-BTC"', b"[1]", b'[["KRW-BTC"]]', b"[", b"\xff",
                b'[{"market": "KRW-BTC", "market": "KRW-ETH"}]', b'[{"market": "KRW-BTC", "x": NaN}]',
                b"[" * 100_000 + b"]" * 100_000, _body([_entry("KRW-BTC"), _entry("KRW-BTC")])):
        assert _code(lambda: rules.market_flags(bad)) == "UNIVERSE_BODY_INVALID", bad[:40]
    assert _code(lambda: rules.market_flags("[]")) == "UNIVERSE_BODY_INVALID"       # bytes only
