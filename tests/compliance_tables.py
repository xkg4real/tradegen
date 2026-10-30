"""Rules table, instrument map and venue file parsers, file hashes and the approved state (compliance plan Task 4;
spec 5.1, 5.2, 8.1; P4, P9, P10, P12-P15, P21). Every violation uses a small inline fixture, never the shipped files."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

import yaml

from core.compliance import rules
from tests.notrun import NotRun

_DROP = object()                                    # an override value that deletes the key
ALL_MATRIX = list(range(1, 39))
_ISSUER = "https://example.invalid/issuer"


def _dump(doc) -> bytes:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).encode("utf-8")


def _refused(call, *has: str) -> str:
    """Asserts `call()` raises rules.Invalid whose reason contains every `has`; returns the reason."""
    try:
        call()
    except rules.Invalid as exc:
        assert str(exc) == exc.reason and all(h in exc.reason for h in has), (has, exc.reason)
        return exc.reason
    raise AssertionError(f"accepted; expected Invalid containing {has}")


def _read_only(mapping, key) -> None:
    """Asserts a parsed mapping refuses assignment (the cached approved() fixture is shared across tests)."""
    try:
        mapping[key] = None
    except TypeError:
        return
    raise AssertionError(f"{type(mapping).__name__} accepted an assignment to {key!r}")


# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #
def _row(**over) -> dict:
    """A valid allow row (upbit coin buy/sell for cash) that covers every matrix row."""
    row = {"id": "T-ALLOW", "kind": "venue",
           "match": {"venue": ["upbit"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash"]},
           "treatment": "allow", "reason": "fixture row", "basis": ["legal"],
           "sources": ["https://www.fsc.go.kr/no010101/87177"], "research": ["reports/fixture.md#row 10"],
           "matrix_rows": list(ALL_MATRIX), "confidence": "high", "effective_from": "2021-03-25",
           "review_by": "2026-11-23", "reviews": [{"date": "2026-10-23", "by": "test", "checked": "fixture"}]}
    row.update(over)
    return {k: v for k, v in row.items() if v is not _DROP}


def _grey(**over) -> dict:
    """A valid grey row shaped like KR-OKX-SPOT (spec 5.2)."""
    base = {"id": "T-GREY", "treatment": "grey", "confidence": "low", "matrix_rows": [14],
            "match": {"venue": ["okx"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash"]},
            "requires": {"owner": ["age_of_majority"]}, "ack": "per_session",
            "grey": {"cap_key": "okx_equity_share", "auto_off": "2026-12-03"},
            "warning": "TRADEGEN caps everything you hold on OKX at {cap} of your equity.",
            "effective_until": "2027-02-18", "review_by": "2026-11-22", "affected_by": ["2026-12-03"]}
    base.update(over)
    return _row(**base)


def _table(*rows, **over) -> bytes:
    doc = {"schema": "tradegen.kr_rules/4", "scope": "Korean-resident individual, own funds only",
           "known_changes": ["2026-12-03", "2027-01-01", "2027-02-18"], "rows": list(rows) or [_row()]}
    doc.update(over)
    return _dump({k: v for k, v in doc.items() if v is not _DROP})


def _parse(*rows, **over) -> rules.RulesTable:
    return rules.parse_rules(_table(*rows, **over))


def _bad(*rows_and_has) -> str:
    """_bad(row..., "needle", ...): the table of the dict rows is Invalid with every str needle in its reason."""
    rows = [r for r in rows_and_has if isinstance(r, dict)]
    has = [h for h in rows_and_has if isinstance(h, str)]
    return _refused(lambda: _parse(*rows), *has)


def _entry(asset, multiple, underlying, cls, book, currency, tax="unsupported") -> dict:
    return {"asset": asset, "multiple": multiple, "underlying": underlying, "class": cls, "cost_book": book,
            "currency": currency, "tax_basis": tax, "source": _ISSUER}


def _map_doc() -> dict:
    us = "overseas_22pct_over_2.5m"
    return {"schema": "tradegen.instruments/1",
            "krx": {"005930": _entry("krx_share", 1, None, "share", "KRX_stock_book", "KRW", "krx_small_holder_exempt"),
                    "252670": _entry("krx_etp", -2, "index", "etp_leveraged", "KRX_ETF_line", "KRW")},
            "us": {"TQQQ": _entry("us_etp", 3, "index", "etp_leveraged", "US_shares_KIS", "USD", us),
                   "SH": _entry("us_etp", -1, "index", "etp_index_inverse", "US_shares_KIS", "USD", us),
                   "AAPL": _entry("us_share", 1, None, "share", "US_shares_KIS", "USD", us),
                   "IBIT": _entry("us_etp", 1, "crypto_spot", "etp_crypto_spot", "US_shares_KIS", "USD", us),
                   "GDLC": _entry("us_etp", 1, "crypto_spot_basket", "etp_crypto_spot", "US_shares_KIS", "USD", us),
                   "BITO": _entry("us_etp", 1, "crypto_futures", "etp_crypto_futures_1x", "US_shares_KIS", "USD", us)},
            "crypto": {"BTC": _entry("crypto_coin", 1, None, "coin", "crypto_venue", "KRW", "crypto_22pct_from_2027"),
                       "USDT": _entry("crypto_coin", 1, None, "coin", "crypto_venue", "KRW", "crypto_22pct_from_2027"),
                       "XRP": _entry("crypto_coin", 1, None, "coin", "crypto_venue", "KRW", "crypto_22pct_from_2027")}}


def _venues_doc() -> dict:
    return {"schema": "tradegen.venues/1", "venues": {
        "kis": {"sections": ["krx", "us"], "settlement": ["KRW", "USD"], "quote_by_currency": True,
                "source": "https://example.invalid/kis"},
        "upbit": {"sections": ["crypto"], "settlement": ["KRW"], "markets": [["BTC", "KRW"], ["USDT", "KRW"]],
                  "default_quote": "KRW",
                  "deposits": [{"symbol": "BTC", "network": "bitcoin", "tag_required": False},
                               {"symbol": "XRP", "network": "ripple", "tag_required": True}],
                  "source": "https://example.invalid/upbit"},
        "okx": {"sections": ["crypto"], "settlement": ["USDT", "USDC"], "markets": [["BTC", "USDT"]],
                "default_quote": "USDT", "source": "https://example.invalid/okx"}}}


def _map(doc=None) -> rules.InstrumentMap:
    return rules.parse_instruments(_dump(_map_doc() if doc is None else doc))


def _facts(vdoc=None, mdoc=None) -> rules.VenueFacts:
    return rules.parse_venues(_dump(_venues_doc() if vdoc is None else vdoc), _map(mdoc))


# --------------------------------------------------------------------------- #
# Rules table
# --------------------------------------------------------------------------- #
def test_valid_fixture_table_parses():
    conduct = _row(id="T-COND", kind="conduct", treatment="hard_block", match={"tag": ["spoof"]}, matrix_rows=[20])
    table = _parse(_row(), _grey(), conduct)
    assert table.schema == "tradegen.kr_rules/4" and table.scope.startswith("Korean-resident")
    assert table.known_changes == (date(2026, 12, 3), date(2027, 1, 1), date(2027, 2, 18))
    allow, grey, cond = table.rows
    assert allow.match == {"venue": {"upbit"}, "class": {"coin"}, "action": {"buy", "sell"}, "financing": {"cash"}}
    assert all(type(v) is frozenset for v in allow.match.values())
    assert (allow.kind, allow.treatment, allow.requires_owner, allow.requires_live) == ("venue", "allow", (), ())
    assert allow.ack is None and allow.cap_key is None and allow.auto_off is None and allow.policy_ref is None
    assert allow.max_leverage == 1.0 and allow.warning == "" and allow.affected_by == ()
    assert allow.basis == frozenset({"legal"}) and allow.matrix_rows == tuple(ALL_MATRIX)
    assert allow.sources == ("https://www.fsc.go.kr/no010101/87177",)
    assert allow.research == ("reports/fixture.md#row 10",)
    assert allow.effective_from == date(2021, 3, 25) and allow.effective_until is None
    assert allow.review_by == date(2026, 11, 23) and allow.confidence == "high"
    assert allow.reviews == (rules.Review(date=date(2026, 10, 23), by="test", checked="fixture"),)
    assert grey.cap_key == "okx_equity_share" and grey.auto_off == date(2026, 12, 3) and grey.ack == "per_session"
    assert grey.requires_owner == ("age_of_majority",) and grey.effective_until == date(2027, 2, 18)
    assert grey.affected_by == (date(2026, 12, 3),) and "{cap}" in grey.warning
    assert cond.kind == "conduct" and cond.match == {"tag": {"spoof"}}
    _read_only(allow.match, "venue")


def test_optional_keys_may_be_null():
    nulls = _row(id="T-NULLS", matrix_rows=None, requires=None, ack=None, grey=None, max_leverage=None,
                 warning=None, policy_ref=None, effective_until=None, affected_by=None)
    row = _parse(_row(), nulls).rows[1]
    assert (row.matrix_rows, row.requires_owner, row.requires_live, row.ack, row.cap_key) == ((), (), (), None, None)
    assert (row.max_leverage, row.warning, row.policy_ref, row.effective_until, row.affected_by) == (1.0, "", None,
                                                                                                    None, ())


def test_row_unknown_and_missing_keys():
    _bad(_row(colour="red"), "rules: row T-ALLOW", "unknown key(s) ['colour']")
    for key in ("kind", "match", "treatment", "reason", "basis", "sources", "research", "confidence",
                "effective_from", "review_by", "reviews"):
        _bad(_row(**{key: _DROP}), "rules: row T-ALLOW", f"missing key(s) ['{key}']")
    _bad(_row(id=_DROP), "rules: row 0: id")
    for bad in ("", 7, "X\nY", "kr-okx", "T ALLOW", "T_ALLOW", "-T", "T" * 65):
        _bad(_row(id=bad), "rules: row 0: id")
    assert _parse(_row(id="T" * 64)).rows[0].id == "T" * 64


def test_match_keys_and_vocabulary():
    _bad(_row(match={"venue": ["upbit"], "market": ["KRW"]}), "row T-ALLOW: match: unknown key 'market'")
    for key, good in (("venue", "upbit"), ("asset", "crypto_coin"), ("class", "coin"), ("action", "buy"),
                      ("financing", "cash"), ("tag", "spoof"), ("when", "publishes_signal")):
        _bad(_row(match={"venue": ["upbit"], key: [good, "bogus"]}), f"match.{key}", "'bogus' is outside")
        _parse(_row(treatment="hard_block", match={"venue": ["upbit"], key: [good]}))   # blocks: any one key will do
    _bad(_row(match={"venue": ["UPBIT"]}), "match.venue", "'UPBIT' is outside the vocabulary")
    _bad(_row(match={"venue": ["upbit"], "action": ["Buy"]}), "match.action", "'Buy' is outside")
    _bad(_row(match={}), "match: expected a non-empty mapping")
    _bad(_row(match=["upbit"]), "match: expected a non-empty mapping")
    _bad(_row(match={"venue": "upbit"}), "match.venue: expected a non-empty list")
    _bad(_row(match={"venue": []}), "match.venue: expected a non-empty list")
    _bad(_row(match={"venue": ["upbit", "upbit"]}), "match.venue: an item is repeated")


def test_any_only_on_hard_block_out_of_scope_and_conduct_rows():
    wide = {"venue": ["kis"], "class": ["any"], "action": ["buy"], "financing": ["credit"]}
    for treatment in ("allow", "gated", "grey"):
        _bad(_row(treatment=treatment, match=wide), "match.class: any is allowed only on hard_block")
    _bad(_row(match={"venue": ["any"]}), "match.venue: any is allowed only")
    for treatment in ("hard_block", "out_of_scope"):
        assert _parse(_row(treatment=treatment, match=wide)).rows[0].match["class"] == {"any"}
    conduct = _row(kind="conduct", treatment="hard_block", match={"venue": ["any"], "asset": ["event_contract"]})
    assert _parse(conduct).rows[0].match["venue"] == {"any"}
    _bad(_row(treatment="hard_block", match={"venue": ["any", "kis"]}), "match.venue", "'any' is outside")


def test_a_row_that_can_let_through_names_every_axis():
    """A missing match key matches everything (fail open by omission): an allow, gated or grey row names action,
    financing and a class or an asset, so a dropped financing cannot let a credit buy through. Blocking rows may
    stay wide."""
    full = {"venue": ["upbit"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash"]}
    base = _row(id="T-BASE")
    make = {"allow": lambda m: _row(id="T-ROW", match=m, matrix_rows=[]),
            "gated": lambda m: _row(id="T-ROW", match=m, matrix_rows=[], treatment="gated",
                                    requires={"owner": ["age_of_majority"]}),
            "grey": lambda m: _grey(id="T-ROW", match=m)}
    for treatment, row in make.items():
        assert _parse(base, row(full)).rows[1].treatment == treatment
        asset = {**{k: v for k, v in full.items() if k != "class"}, "asset": ["crypto_coin"]}
        assert _parse(base, row(asset)).rows[1].match["asset"] == {"crypto_coin"}      # an asset will do
        for drop, missing in (("action", "['action']"), ("financing", "['financing']"),
                              ("class", "['class or asset']")):
            _bad(base, row({k: v for k, v in full.items() if k != drop}), "row T-ROW: match",
                 f"an allow, gated or grey row names action, financing and a class or an asset; missing {missing}")
        _bad(base, row({"venue": ["upbit"]}), "row T-ROW: match", "missing ['action', 'financing', 'class or asset']")
    for treatment in ("hard_block", "out_of_scope"):
        assert _parse(base, _row(id="T-ROW", treatment=treatment, match={"venue": ["upbit"]}, matrix_rows=[]))


def test_a_gated_row_requires_something():
    """A gated row with no requirement would act as an allow row."""
    gated = {"id": "T-ROW", "treatment": "gated", "matrix_rows": []}
    for requires in (_DROP, None, {}, {"owner": [], "live": []}, {"owner": None}):
        _bad(_row(id="T-BASE"), _row(**gated, requires=requires), "row T-ROW: requires",
             "a gated row requires owner or live evidence")
    for requires in ({"owner": ["age_of_majority"]}, {"live": ["broker_approval"]}):
        assert _parse(_row(id="T-BASE"), _row(**gated, requires=requires)).rows[1].treatment == "gated"


def test_a_conduct_row_never_keys_on_an_etp_class():
    """gate._conduct shows a conduct row the class of the asset itself (rules.ASSET_CLASS), never a derived ETP
    class, so a conduct row keyed on one could never fire."""
    etp = sorted(rules.CLASSES - set(rules.ASSET_CLASS.values()))
    assert etp and all(c.startswith("etp_") for c in etp), etp
    for cls in etp:
        _bad(_row(id="T-COND", kind="conduct", treatment="hard_block", match={"venue": ["any"], "class": [cls]}),
             "row T-COND: match.class", f"a conduct row sees an asset's own class, never ['{cls}']")
    _bad(_row(id="T-COND", kind="conduct", treatment="hard_block", match={"class": ["share", "etp_1x"]}),
         "never ['etp_1x']")
    for cls in ("share", "coin", "any"):
        assert _parse(_row(id="T-COND", kind="conduct", treatment="hard_block", match={"class": [cls]}))


def test_conduct_rows_are_hard_block_and_venue_rows_name_venues():
    for treatment in ("allow", "gated", "grey", "out_of_scope"):
        _bad(_row(kind="conduct", treatment=treatment, match={"tag": ["spoof"]}), "a conduct row is hard_block")
    _bad(_row(kind="policy"), "row T-ALLOW: kind")
    _bad(_row(treatment="permitted"), "row T-ALLOW: treatment")
    _bad(_row(match={"class": ["coin"], "action": ["buy"]}), "match: a venue row names its venues")
    assert _parse(_row(kind="conduct", treatment="hard_block", match={"when": ["route_not_direct"]})).rows[0].kind \
        == "conduct"


def test_grey_rows_need_cap_auto_off_and_session_ack():
    _parse(_row(), _grey())
    _bad(_row(), _grey(grey=_DROP), "row T-GREY: grey: expected a mapping")
    _bad(_row(), _grey(grey={"auto_off": "2026-12-03"}), "row T-GREY: grey", "missing key(s) ['cap_key']")
    _bad(_row(), _grey(grey={"cap_key": "okx_equity_share"}), "missing key(s) ['auto_off']")
    _bad(_row(), _grey(grey={"cap_key": "", "auto_off": "2026-12-03"}), "grey.cap_key")
    _bad(_row(), _grey(grey={"cap_key": "okx_equity_share", "auto_off": "2026-12-3"}), "grey.auto_off")
    _bad(_row(), _grey(ack=_DROP), "row T-GREY: ack: a grey row needs ack: per_session")
    _bad(_row(), _grey(ack="per_transfer"), "a grey row needs ack: per_session")
    _bad(_row(), _grey(ack="weekly"), "row T-GREY: ack")
    _bad(_row(grey={"cap_key": "okx_equity_share", "auto_off": "2026-12-03"}), "only a grey row carries a cap")
    _bad(_row(), _grey(warning=None), "row T-GREY: warning: an ack: per_session row needs the warning")
    _bad(_row(), _grey(warning="  "), "row T-GREY: warning: an ack: per_session row needs the warning")
    _bad(_row(), _grey(warning="no slot"), "row T-GREY: warning: a grey row states its {cap}")
    _bad(_row(), _grey(warning="literal {{cap}} only"), "row T-GREY: warning: a grey row states its {cap}")
    _bad(_row(ack="per_session"), "row T-ALLOW: warning: an ack: per_session row needs the warning")
    assert _parse(_row(ack="per_session", warning="you trade here at your own risk")).rows[0].ack == "per_session"
    assert _parse(_row(ack="per_transfer")).rows[0].warning == ""     # contract 7: the destination row's warning


def test_d16_rows_need_requires_live():
    lev = {"id": "T-LEV", "treatment": "gated", "basis": ["legal", "policy"], "policy_ref": "D16",
           "match": {"venue": ["kis"], "class": ["etp_leveraged"], "action": ["buy"], "financing": ["cash"]},
           "matrix_rows": [25, 32]}
    _bad(_row(), _row(**lev), "row T-LEV: requires.live")
    _bad(_row(), _row(**lev, requires={"owner": ["kofia_leveraged_1h"]}), "row T-LEV: requires.live")
    _bad(_row(), _row(**{**lev, "policy_ref": "D15, D16"}), "row T-LEV: requires.live")
    ok = _parse(_row(), _row(**lev, requires={"owner": ["kofia_leveraged_1h"], "live": ["deposit_krw_10m"]})).rows[1]
    assert ok.requires_live == ("deposit_krw_10m",) and ok.requires_owner == ("kofia_leveraged_1h",)
    assert ok.policy_ref == "D16" and ok.basis == {"legal", "policy"}
    _bad(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}),
         "row T-LEV: requires.live: a row matching ['etp_leveraged']")         # not D16 by label, D16 by content
    one_x = {**lev["match"], "class": ["etp_1x"]}                               # D160 is not D16, nor is etp_1x
    _parse(_row(), _row(**{**lev, "policy_ref": "D160", "match": one_x}, requires={"owner": ["kofia_leveraged_1h"]}))
    _parse(_row(), _row(**{**lev, "policy_ref": "D15", "treatment": "out_of_scope"}))
    for ref in ("d16", "D-16", "D 16", "D16a", "owner decision 16", "D15,D16", "D15, D16,", 16, ["D16"],
                "D016", "D15, D016"):
        _bad(_row(), _row(**{**lev, "policy_ref": ref}), "row T-LEV: policy_ref")


def test_d15_rows_never_let_credit_margin_lending_or_borrowing_through():
    """D15 by content (R2, ledger:243): an allow, gated or grey row never matches financing credit or margin, nor
    action lend or borrow, whatever its policy_ref says. Blocking rows may (KR-KIS-CREDIT, KR-DOMESTIC-LENDING), and
    sell_short is D16 (spec:70), never D15."""
    coin = {"venue": ["upbit"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash"]}
    for make in (lambda m: _row(match=m),
                 lambda m: _row(match=m, treatment="gated", requires={"owner": ["age_of_majority"]})):
        for financing in (["cash", "margin"], ["credit"], ["margin"]):
            _bad(make({**coin, "financing": financing}),
                 "row T-ALLOW: match.financing: an allow, gated or grey row never matches")
        for action in (["buy", "lend"], ["borrow"]):
            _bad(make({**coin, "action": action}),
                 "row T-ALLOW: match.action: an allow, gated or grey row never matches")
    assert _bad(_row(match={**coin, "financing": ["credit"]})) == (
        "rules: row T-ALLOW: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit "
        "buying)")
    assert _bad(_row(match={**coin, "action": ["buy", "lend", "borrow"]})) == (
        "rules: row T-ALLOW: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin "
        "lending or borrowing)")
    okx = {"venue": ["okx"], "class": ["coin"], "action": ["buy", "sell"], "financing": ["cash", "margin"]}
    _bad(_row(), _grey(match=okx), "row T-GREY: match.financing", "['margin'] (D15")
    _bad(_row(), _grey(match={**okx, "financing": ["cash"], "action": ["buy", "borrow"]}), "row T-GREY: match.action",
         "['borrow'] (D15")
    wide = {**coin, "action": ["buy", "lend", "borrow"], "financing": ["credit", "margin"]}
    for treatment in ("hard_block", "out_of_scope"):
        row = _parse(_row(), _row(id="T-D15", treatment=treatment, match=wide, matrix_rows=[])).rows[1]
        assert row.match["financing"] == {"credit", "margin"} and row.match["action"] == {"buy", "lend", "borrow"}
    short = {"venue": ["kis"], "asset": ["krx_share"], "action": ["buy", "sell_short"], "financing": ["cash"]}
    row = _parse(_row(), _row(id="T-SHORT", treatment="gated", match=short, requires={"live": ["broker_approval"]},
                              matrix_rows=[])).rows[1]
    assert row.match["action"] == {"buy", "sell_short"} and row.requires_live == ("broker_approval",)


def test_a_d15_row_is_blocking():
    """D15 by label (R2): a row citing D15 is hard_block or out_of_scope, as a row citing D16 needs requires.live."""
    d15 = {"id": "T-D15", "policy_ref": "D15", "basis": ["policy"], "matrix_rows": []}
    for row in (_row(**d15), _row(**d15, treatment="gated", requires={"owner": ["age_of_majority"]}), _grey(**d15)):
        _bad(_row(), row, "row T-D15: treatment: a D15 row is hard_block or out_of_scope")
    assert _bad(_row(), _row(**d15)) == ("rules: row T-D15: treatment: a D15 row is hard_block or out_of_scope (D15 "
                                         "only keeps credit and lending out)")
    for ref in ("D15", "D10, D15"):
        for treatment in ("hard_block", "out_of_scope"):
            row = _parse(_row(), _row(**{**d15, "policy_ref": ref}, treatment=treatment)).rows[1]
            assert (row.policy_ref, row.treatment) == (ref, treatment)


def test_d16_by_content_needs_requires_live():
    """D16 by content (R2): a row that can let an intent through and matches sell_short, a leveraged or single-stock
    ETP, a KRX derivative or an ELW needs requires.live, whatever its policy_ref says. A row with no class axis that
    names an ETP asset matches every class that asset derives to, the leveraged and single-stock ones included."""
    kis = {"venue": ["kis"], "action": ["buy"], "financing": ["cash"]}
    matches = ({**kis, "asset": ["krx_share"], "action": ["sell_short"]}, {**kis, "class": ["etp_1x", "etp_leveraged"]},
               {**kis, "class": ["etp_single_stock"]}, {**kis, "class": ["krx_derivative"]},
               {**kis, "asset": ["krx_derivative"]}, {**kis, "class": ["elw"]}, {**kis, "asset": ["elw"]},
               {**kis, "asset": ["krx_etp"]}, {**kis, "asset": ["us_etp"]})
    live = {"owner": ["age_of_majority"], "live": ["broker_approval"]}
    for m in matches:
        d16 = {"id": "T-D16", "match": m, "matrix_rows": []}
        _bad(_row(), _row(**d16, treatment="gated", requires={"owner": ["age_of_majority"]}),
             "row T-D16: requires.live: a row matching")
        _bad(_row(), _row(**d16), "row T-D16: requires.live: a row matching")
        gated = _parse(_row(), _row(**d16, treatment="gated", requires=live)).rows[1]
        assert gated.requires_live == ("broker_approval",), m
        assert _parse(_row(), _row(**d16, treatment="out_of_scope")).rows[1].treatment == "out_of_scope"
    assert _bad(_row(), _row(id="T-D16", match=matches[1], matrix_rows=[])) == (
        "rules: row T-D16: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)")
    assert _bad(_row(), _row(id="T-D16", match=matches[7], matrix_rows=[])) == (
        "rules: row T-D16: requires.live: a row matching ['etp_leveraged', 'etp_single_stock'] needs live broker "
        "evidence (D16)")
    one_x = _row(id="T-1X", match={**kis, "asset": ["krx_etp"], "class": ["etp_1x"]}, matrix_rows=[])
    assert _parse(_row(), one_x).rows[1].match["class"] == {"etp_1x"}          # a class axis decides
    sell_short = {"venue": ["okx"], "class": ["coin"], "action": ["buy", "sell_short"], "financing": ["cash"]}
    _bad(_row(), _grey(match=sell_short), "row T-GREY: requires.live: a row matching ['sell_short']")


def test_review_by_is_not_before_the_latest_review():
    """R2 (ledger:103): review_by is never before the row's latest review, the earliest legal value being the review
    day itself; an earlier date is a typo, never a schedule."""
    assert _parse(_row(review_by="2026-10-23")).rows[0].review_by == date(2026, 10, 23)
    assert _bad(_row(review_by="2026-10-22")) == (
        "rules: row T-ALLOW: review_by: 2026-10-22 is before the review of 2026-10-23")
    two = [{"date": "2026-09-01", "by": "a", "checked": "x"}, {"date": "2026-10-23", "by": "b", "checked": "y"}]
    _bad(_row(reviews=two, review_by="2026-10-01"),
         "row T-ALLOW: review_by: 2026-10-01 is before the review of 2026-10-23")      # the latest review counts


def test_only_a_grey_row_states_a_cap():
    """R2 (ledger:146): only a grey row's warning has the {cap} slot, so the cap text an owner acks in a per_session
    warning is always a grey row's signed cap."""
    _bad(_row(warning="OKX is capped at {cap} of your equity."), "row T-ALLOW: warning: only a grey row states a {cap}")
    gated = _row(id="T-GATED", treatment="gated", ack="per_session", requires={"owner": ["age_of_majority"]},
                 warning="at most {cap} of your equity", matrix_rows=[])
    _bad(_row(), gated, "row T-GATED: warning: only a grey row states a {cap}")
    _bad(_row(), _row(id="T-OOS", treatment="out_of_scope", warning="{cap}", matrix_rows=[]),
         "row T-OOS: warning: only a grey row states a {cap}")
    assert _parse(_row(warning="literal {{cap}} braces")).rows[0].warning == "literal {{cap}} braces"
    assert "{cap}" in _parse(_row(), _grey()).rows[1].warning


def test_requires_items_in_vocabulary():
    _bad(_row(requires={"owner": ["age_19"]}), "row T-ALLOW: requires.owner", "'age_19' is outside")
    _bad(_row(requires={"live": ["deposit_krw_1m"]}), "row T-ALLOW: requires.live", "'deposit_krw_1m' is outside")
    _bad(_row(requires={"owner": ["broker_approval"]}), "requires.owner")        # a live item named as owner
    _bad(_row(requires={"live": ["broker_eligibility"]}), "requires.live")       # an owner item named as live
    _bad(_row(requires={"owner": ["age_of_majority"], "broker": ["x"]}), "requires: unknown key(s) ['broker']")
    _bad(_row(requires=["age_of_majority"]), "requires: expected a mapping")
    _bad(_row(requires={"owner": "age_of_majority"}), "requires.owner: expected a list")
    every = _row(requires={"owner": sorted(rules.OWNER_REQUIREMENTS), "live": sorted(rules.LIVE_REQUIREMENTS)})
    row = _parse(every).rows[0]
    assert set(row.requires_owner) == rules.OWNER_REQUIREMENTS and set(row.requires_live) == rules.LIVE_REQUIREMENTS


def test_warning_slots():
    for text in ("no slot at all", "literal {{cap}} braces", ""):    # {cap}: test_only_a_grey_row_states_a_cap
        assert _parse(_row(warning=text)).rows[0].warning == text
    for text, has in (("{equity} of x", "slot {equity}"), ("{cap!r}", "slot {cap}"), ("{cap:>5}", "slot {cap}"),
                      ("{}", "slot {}"), ("{0}", "slot {0}"), ("{cap.real}", "slot {cap.real}"),
                      ("open { brace", "warning"), ("close } brace", "warning")):
        _bad(_row(warning=text), "row T-ALLOW: warning", has)
    _bad(_row(warning=["x"]), "row T-ALLOW: warning: expected a string")


def test_basis_confidence_and_citations():
    assert _parse(_row(basis=["legal", "policy", "platform"])).rows[0].basis == {"legal", "policy", "platform"}
    _bad(_row(basis=[]), "row T-ALLOW: basis: expected a non-empty list")
    _bad(_row(basis=["legal", "opinion"]), "row T-ALLOW: basis", "'opinion' is outside")
    _bad(_row(basis="legal"), "row T-ALLOW: basis")
    _bad(_row(confidence="certain"), "row T-ALLOW: confidence")
    _bad(_row(reason=""), "row T-ALLOW: reason")
    _bad(_row(sources=[]), "row T-ALLOW: sources")
    _bad(_row(sources=["https://a.example", "https://a.example"]), "row T-ALLOW: sources: an item is repeated")
    _bad(_row(research=[]), "row T-ALLOW: research")
    _bad(_row(research="reports/x.md"), "row T-ALLOW: research")
    _bad(_row(policy_ref=""), "row T-ALLOW: policy_ref")


def test_review_cadence_31_days_and_affected_by():
    assert _parse(_row(review_by="2026-11-23")).rows[0].review_by == date(2026, 11, 23)        # 31 days
    _bad(_row(review_by="2026-11-24"), "review_by", "more than 31 days after the review of 2026-10-23")
    two = [{"date": "2026-09-01", "by": "a", "checked": "x"}, {"date": "2026-10-23", "by": "b", "checked": "y"}]
    _parse(_row(reviews=two))                                                   # the latest review counts
    _bad(_row(reviews=list(reversed(two)), review_by="2026-11-24"), "more than 31 days")
    late = [{"date": "2026-11-15", "by": "a", "checked": "x"}]
    _parse(_row(reviews=late, review_by="2026-11-22", affected_by=["2026-12-03"]))
    _parse(_row(reviews=late, review_by="2026-12-02", affected_by=["2026-12-03"]))    # the day before
    _bad(_row(reviews=late, review_by="2026-12-03", affected_by=["2026-12-03"]),
         "review_by: 2026-12-03 is not before the 2026-12-03 change")
    _bad(_row(reviews=late, review_by="2026-12-10", affected_by=["2027-01-01", "2026-12-03"]),
         "is not before the 2026-12-03 change")                                 # the first change after the review
    known = ["2026-10-01", "2026-12-03", "2027-01-01", "2027-02-18"]
    _parse(_row(affected_by=["2026-10-01"]), known_changes=known)               # a change before the review is past
    _bad(_row(affected_by=["2026-11-01"]), "affected_by: 2026-11-01 is not in known_changes")
    _bad(_row(affected_by=["2026-12-3"]), "row T-ALLOW: affected_by")
    _bad(_row(affected_by=["2026-12-03", "2026-12-03"]), "affected_by: an item is repeated")


def test_reviews_shape():
    _bad(_row(reviews=[]), "row T-ALLOW: reviews: expected a non-empty list")
    _bad(_row(reviews=[{"date": "2026-10-23", "by": "test"}]), "reviews", "missing key(s) ['checked']")
    _bad(_row(reviews=[{"date": "2026-10-23", "by": "t", "checked": "c", "note": "n"}]), "unknown key(s) ['note']")
    _bad(_row(reviews=[{"date": "23 Oct 2026", "by": "t", "checked": "c"}]), "reviews.date")
    _bad(_row(reviews=[{"date": "2026-10-23", "by": "", "checked": "c"}]), "reviews.by")


def test_row_dates():
    _bad(_row(effective_from="2021-3-25"), "row T-ALLOW: effective_from")
    _bad(_row(effective_from=20210325), "row T-ALLOW: effective_from")
    _bad(_row(effective_until="2021-03-25"), "effective_until: 2021-03-25 is not after effective_from 2021-03-25")
    _bad(_row(effective_until="2020-01-01"), "effective_until")
    _bad(_row(review_by="next month"), "row T-ALLOW: review_by")
    unquoted = _table(_row()).replace(b"'2021-03-25'", b"2021-03-25")
    assert b"effective_from: 2021-03-25\n" in unquoted
    _refused(lambda: rules.parse_rules(unquoted), "rules: native date '2021-03-25'")


def test_ids_unique_and_matrix_rows_in_range():
    _bad(_row(), _row(matrix_rows=[1]), "rules: row T-ALLOW: id: duplicate id")
    for bad in ([0], [39], [True], ["1"], [1.0], [1, 1], 5, [[1]]):
        _bad(_row(), _row(id="T-2", matrix_rows=bad), "row T-2: matrix_rows")
    assert _parse(_row(), _row(id="T-2", matrix_rows=[])).rows[1].matrix_rows == ()


def test_matrix_coverage_lists_missing_rows():
    _bad(_row(matrix_rows=[n for n in ALL_MATRIX if n not in (7, 21)]),
         "rules: matrix rows [7, 21] are covered by no row")
    split = _parse(_row(matrix_rows=list(range(1, 20))), _row(id="T-2", matrix_rows=list(range(20, 39))))
    assert {n for r in split.rows for n in r.matrix_rows} == set(ALL_MATRIX)


def test_table_level_rules():
    for over, has in (({"known_changes": ["2027-01-01", "2026-12-03"]}, "rules: known_changes: dates must be in"),
                      ({"known_changes": ["2026-12-03", "2026-12-03"]}, "rules: known_changes: an item is repeated"),
                      ({"known_changes": ["2026-12-3"]}, "rules: known_changes"),
                      ({"schema": "tradegen.kr_rules/3"}, "rules: schema must be tradegen.kr_rules/4"),
                      ({"extra": "x"}, "rules: unknown key(s) ['extra']"),
                      ({"scope": _DROP}, "rules: missing key(s) ['scope']"),
                      ({"scope": ""}, "rules: scope"),
                      ({"rows": []}, "rules: rows: expected a non-empty list"),
                      ({"rows": "none"}, "rules: rows: expected a non-empty list"),
                      ({"rows": ["not a mapping"]}, "rules: row 0: id")):
        _refused(lambda: _parse(**over), has)
    assert _parse(known_changes=[]).known_changes == ()
    _refused(lambda: rules.parse_rules(b"- just a list\n"), "rules: the top level must be a mapping")


def test_max_leverage():
    assert _parse(_row(max_leverage=2.5)).rows[0].max_leverage == 2.5
    assert type(_parse(_row(max_leverage=3)).rows[0].max_leverage) is float
    for bad in (0, -1, -0.5, True, "2", [1]):
        _bad(_row(max_leverage=bad), "row T-ALLOW: max_leverage")
    _bad(_row(max_leverage=10 ** 400), "rules: line ", "has more than 18 digits")      # Invalid, never OverflowError
    assert _parse(_row(max_leverage=10)).rows[0].max_leverage == 10.0                 # R2: 10 itself is legal
    for bad in (10.5, 11, 1e6):
        _bad(_row(max_leverage=bad), "row T-ALLOW: max_leverage: at most 10")
    assert _bad(_row(max_leverage=10.5)) == "rules: row T-ALLOW: max_leverage: at most 10, got 10.5"


# --------------------------------------------------------------------------- #
# Instrument map
# --------------------------------------------------------------------------- #
def test_valid_fixture_map_parses():
    imap = _map()
    tq = imap.entries[("us", "TQQQ")]
    assert tq == rules.Instrument(section="us", symbol="TQQQ", asset="us_etp", multiple=3.0, underlying="index",
                                  cls="etp_leveraged", cost_book="US_shares_KIS", currency="USD",
                                  tax_basis="overseas_22pct_over_2.5m", source=_ISSUER)
    assert type(tq.multiple) is float and imap.entries[("krx", "252670")].multiple == -2.0
    classes = {key: inst.cls for key, inst in imap.entries.items()}
    assert classes == {("krx", "005930"): "share", ("krx", "252670"): "etp_leveraged",
                       ("us", "TQQQ"): "etp_leveraged", ("us", "SH"): "etp_index_inverse", ("us", "AAPL"): "share",
                       ("us", "IBIT"): "etp_crypto_spot", ("us", "GDLC"): "etp_crypto_spot",
                       ("us", "BITO"): "etp_crypto_futures_1x", ("crypto", "BTC"): "coin",
                       ("crypto", "USDT"): "coin", ("crypto", "XRP"): "coin"}
    assert imap.lookup(("krx", "us"), "TQQQ") is tq and imap.lookup(("crypto",), "TQQQ") is None
    assert imap.lookup(("krx", "us"), ["TQQQ"]) is None and imap.lookup((), "TQQQ") is None
    only = rules.parse_instruments(_dump({"schema": "tradegen.instruments/1", "crypto": _map_doc()["crypto"]}))
    assert set(only.entries) == {("crypto", "BTC"), ("crypto", "USDT"), ("crypto", "XRP")}
    _read_only(imap.entries, ("crypto", "ETH"))


def test_declared_class_must_equal_derived():                                   # P10
    for section, symbol, field, value, has in (
            ("us", "TQQQ", "class", "etp_1x", "us/TQQQ: class: declared etp_1x, derived etp_leveraged"),
            ("us", "SH", "class", "etp_leveraged", "us/SH: class: declared etp_leveraged, derived etp_index_inverse"),
            ("krx", "252670", "multiple", -1, "krx/252670: class: declared etp_leveraged, derived etp_index_inverse"),
            ("us", "IBIT", "class", "etp_1x", "us/IBIT: class: declared etp_1x, derived etp_crypto_spot"),
            ("crypto", "BTC", "class", "share", "crypto/BTC: class: declared share, derived coin"),
            ("us", "TQQQ", "class", "leveraged", "us/TQQQ: class: 'leveraged' is not one of")):
        doc = _map_doc()
        doc[section][symbol][field] = value
        _refused(lambda: _map(doc), f"instruments: {has}")


def test_known_spot_crypto_etps_must_derive_crypto_spot():                      # P10
    for symbol in sorted(rules.KNOWN_SPOT_CRYPTO_ETPS):
        doc = _map_doc()
        doc["us"][symbol] = _entry("us_etp", 1, "basket", "etp_1x", "US_shares_KIS", "USD")   # GDLC as a basket
        _refused(lambda: _map(doc), f"us/{symbol}: a known spot-crypto ETP must derive etp_crypto_spot, not etp_1x")
    doc = _map_doc()
    doc["us"]["IBIT"] = _entry("us_share", 1, None, "share", "US_shares_KIS", "USD")
    _refused(lambda: _map(doc), "us/IBIT: a known spot-crypto ETP must derive etp_crypto_spot, not share")
    doc = _map_doc()
    doc["us"]["EZPZ"] = _entry("us_etp", 1, "crypto_spot_basket", "etp_crypto_spot", "US_shares_KIS", "USD")
    doc["us"]["GDLC"]["underlying"] = "crypto_spot"
    imap = _map(doc)
    assert imap.entries[("us", "EZPZ")].cls == imap.entries[("us", "GDLC")].cls == "etp_crypto_spot"


def test_etp_underlying_rules():
    for section, symbol, changes, has in (
            ("us", "TQQQ", {"underlying": None}, "us/TQQQ: underlying: an ETP needs an underlying"),
            ("krx", "005930", {"underlying": "single"}, "krx/005930: underlying: must be null for krx_share"),
            ("us", "BITO", {"multiple": -1, "class": "etp_index_inverse"},
             "us/BITO: us_etp x-1 on crypto_futures fits no class"),                                     # P11
            ("us", "BITO", {"multiple": 2, "class": "etp_leveraged"}, "us/BITO: us_etp x2 on crypto_futures"),
            ("us", "TQQQ", {"underlying": "commodity"}, "us/TQQQ: underlying: 'commodity' is not one of"),
            ("us", "TQQQ", {"multiple": 0}, "us/TQQQ: us_etp x0 on index fits no class"),
            ("us", "TQQQ", {"multiple": "3"}, "us/TQQQ: us_etp x3 on index fits no class"),
            ("us", "TQQQ", {"multiple": True}, "us/TQQQ: us_etp xTrue on index fits no class"),
            ("us", "TQQQ", {"asset": "etf"}, "us/TQQQ: asset: 'etf' is not one of")):
        doc = _map_doc()
        doc[section][symbol].update(changes)
        _refused(lambda: _map(doc), f"instruments: {has}")
    doc = _map_doc()
    doc["us"]["TQQQ"]["multiple"] = 10 ** 400
    _refused(lambda: _map(doc), "instruments: line ", "has more than 18 digits")      # Invalid, never OverflowError


def test_entry_keys_symbols_and_sections():
    def bad(mutate, *has):
        doc = _map_doc()
        mutate(doc)
        _refused(lambda: _map(doc), *has)

    bad(lambda d: d["us"]["SH"].pop("source"), "instruments: us/SH: missing key(s) ['source']")
    bad(lambda d: d["us"]["SH"].update(name="ProShares Short S&P500"), "us/SH: unknown key(s) ['name']")
    bad(lambda d: d["us"]["SH"].update(source=""), "us/SH: source")
    bad(lambda d: d.update(jp={}), "instruments: unknown key(s) ['jp']")
    bad(lambda d: d.update(schema="tradegen.instruments/2"), "instruments: schema must be tradegen.instruments/1")
    bad(lambda d: d.pop("schema"), "instruments: missing key(s) ['schema']")
    bad(lambda d: d.update(krx=None), "instruments: krx: expected a mapping of symbols")
    bad(lambda d: d["crypto"].update(btc=dict(d["crypto"]["BTC"])), "instruments: crypto: 'btc' is not a symbol")
    bad(lambda d: d["us"].update({"BRK B": dict(d["us"]["AAPL"])}), "instruments: us: 'BRK B' is not a symbol")
    bad(lambda d: d["us"].update(SPY="not an entry"), "instruments: us/SPY: expected a mapping")
    bad(lambda d: d["krx"].update(BTC=dict(d["crypto"]["BTC"])),
        "instruments: krx/BTC: asset: crypto_coin does not belong in section krx")
    bad(lambda d: d["crypto"].update(AAPL=dict(d["us"]["AAPL"])), "crypto/AAPL: asset: us_share does not belong")
    bad(lambda d: d["us"].update(ESZ6=_entry("overseas_future", 1, None, "overseas_future", None, "USD")),
        "us/ESZ6: asset: overseas_future does not belong in section us")        # spec 5.1 Futures: no section
    unquoted = _dump(_map_doc()).replace(b"'252670':", b"252670:")
    assert b"\n  252670:\n" in unquoted
    _refused(lambda: rules.parse_instruments(unquoted), "instruments: krx: 252670 is not a symbol")
    _refused(lambda: rules.parse_instruments(b"schema: a\nschema: b\n"), "instruments: ", "duplicate key 'schema'")
    _refused(lambda: rules.parse_instruments(b"schema: &a x\n"), "instruments: ", "anchor &a")


def test_cost_book_currency_and_tax_basis():
    def bad(section, symbol, changes, *has):
        doc = _map_doc()
        doc[section][symbol].update(changes)
        _refused(lambda: _map(doc), f"instruments: {section}/{symbol}: ", *has)

    bad("krx", "005930", {"cost_book": "KRX_ETF_line"},
        "cost_book: krx_share takes 'KRX_stock_book', got 'KRX_ETF_line'")
    bad("krx", "005930", {"cost_book": None}, "cost_book: krx_share takes 'KRX_stock_book', got None")
    bad("krx", "252670", {"cost_book": "KRX_stock_book"}, "cost_book: krx_etp takes 'KRX_ETF_line'")
    bad("us", "SH", {"cost_book": "multi_line"}, "cost_book: us_etp takes 'US_shares_KIS'")
    bad("crypto", "BTC", {"cost_book": "US_shares_KIS"}, "cost_book: crypto_coin takes 'crypto_venue'")
    bad("us", "SH", {"tax_basis": "zero"}, "tax_basis")
    bad("us", "SH", {"tax_basis": None}, "tax_basis")
    bad("us", "SH", {"currency": "usd"}, "currency")
    bad("us", "SH", {"currency": None}, "currency")
    gate_only = _map_doc()
    gate_only["krx"]["KONEXFIX"] = _entry("konex_share", 1, None, "konex_share", None, "KRW")
    gate_only["us"]["OPTFIX"] = _entry("us_option", 1, None, "option", None, "USD")
    imap = _map(gate_only)
    assert imap.entries[("krx", "KONEXFIX")].cost_book is None and imap.entries[("us", "OPTFIX")].cls == "option"
    gate_only["krx"]["KONEXFIX"]["cost_book"] = "KRX_stock_book"
    _refused(lambda: _map(gate_only), "krx/KONEXFIX: cost_book: konex_share takes None")
    books = {inst.cost_book for inst in _map().entries.values()}
    assert books == rules.COST_BOOKS                     # the four odds books, each reached by one asset


def test_one_symbol_may_sit_in_two_sections_of_the_map():
    doc = _map_doc()
    doc["us"]["BTC"] = _entry("us_etp", 1, "crypto_spot", "etp_crypto_spot", "US_shares_KIS", "USD")
    imap = _map(doc)
    assert imap.lookup(("crypto",), "BTC").asset == "crypto_coin" and imap.lookup(("us",), "BTC").asset == "us_etp"
    assert imap.lookup(("krx",), "BTC") is None


# --------------------------------------------------------------------------- #
# Venue facts
# --------------------------------------------------------------------------- #
def test_valid_fixture_venues_parse():
    facts = _facts()
    kis, upbit, okx = facts.venues["kis"], facts.venues["upbit"], facts.venues["okx"]
    assert set(facts.venues) == {"kis", "upbit", "okx"}
    assert kis == rules.Venue(id="kis", sections=("krx", "us"), settlement=frozenset({"KRW", "USD"}),
                              markets=frozenset(), quote_by_currency=True, default_quote=None)
    assert upbit.markets == {("BTC", "KRW"), ("USDT", "KRW")} and upbit.default_quote == "KRW"
    assert upbit.deposits == {("BTC", "bitcoin", False), ("XRP", "ripple", True)} and okx.deposits == frozenset()
    assert okx.settlement == {"USDT", "USDC"} and not okx.quote_by_currency
    _read_only(facts.venues, "bithumb")


def test_venue_markets_and_quote():
    facts, imap = _facts(), _map()
    kis, upbit, okx = facts.venues["kis"], facts.venues["upbit"], facts.venues["okx"]
    samsung, tqqq, btc, usdt = (imap.entries[k] for k in (("krx", "005930"), ("us", "TQQQ"), ("crypto", "BTC"),
                                                         ("crypto", "USDT")))
    assert kis.is_market(samsung, "KRW") and not kis.is_market(samsung, "USD")
    assert kis.is_market(tqqq, "USD") and not kis.is_market(tqqq, "KRW") and not kis.is_market(btc, "KRW")
    assert kis.quote_for(samsung) == "KRW" and kis.quote_for(tqqq) == "USD"
    assert upbit.is_market(btc, "KRW") and upbit.is_market(usdt, "KRW") and not upbit.is_market(btc, "USDT")
    assert okx.is_market(btc, "USDT") and not okx.is_market(usdt, "BTC") and not okx.is_market(btc, "KRW")
    assert upbit.quote_for(btc) == "KRW" and okx.quote_for(btc) == "USDT"
    assert not upbit.is_market(samsung, "KRW") and not upbit.is_market(btc, None) and not upbit.is_market(btc, ["KRW"])
    vdoc = _venues_doc()
    vdoc["venues"]["kis"]["settlement"] = ["KRW"]
    assert not _facts(vdoc).venues["kis"].is_market(tqqq, "USD")     # its currency, but not a settlement asset


def test_p9_symbol_twice_in_one_venues_sections_invalid():
    mdoc = _map_doc()
    mdoc["us"]["BTC"] = _entry("us_etp", 1, "crypto_spot", "etp_crypto_spot", "US_shares_KIS", "USD")
    vdoc = _venues_doc()
    vdoc["venues"]["kis"]["sections"] = ["krx", "us", "crypto"]
    _refused(lambda: _facts(vdoc, mdoc), "venues: kis: symbol BTC is listed in sections us and crypto")
    facts = _facts(_venues_doc(), mdoc)                  # kis lists krx+us, upbit lists crypto: one BTC each
    assert facts.venues["kis"].sections == ("krx", "us") and facts.venues["upbit"].sections == ("crypto",)


def test_market_base_and_deposit_symbol_must_be_in_the_map():
    def bad(mutate, *has):
        vdoc = _venues_doc()
        mutate(vdoc["venues"])
        _refused(lambda: _facts(vdoc), *has)

    bad(lambda v: v["upbit"]["markets"].append(["ETH", "KRW"]), "venues: upbit: markets: base ETH is not a symbol")
    bad(lambda v: v["upbit"].update(markets=[["TQQQ", "KRW"]]), "venues: upbit: markets: base TQQQ is not a symbol")
    bad(lambda v: v["upbit"]["deposits"].append({"symbol": "ETH", "network": "ethereum", "tag_required": False}),
        "venues: upbit: deposits: ETH is not a symbol")


def test_venue_shape_rules():
    def bad(mutate, *has):
        vdoc = _venues_doc()
        mutate(vdoc)
        _refused(lambda: _facts(vdoc), *has)

    v = "venues"
    bad(lambda d: d[v].update(ftx=copy.deepcopy(d[v]["okx"])), "venues: venue id: 'ftx' is not one of")
    bad(lambda d: d[v].update(UPBIT=d[v].pop("upbit")), "venues: venue id: 'UPBIT' is not one of")
    bad(lambda d: d.update(venues={}), "venues: venues: expected a non-empty mapping")
    bad(lambda d: d.update(schema="tradegen.venues/0"), "venues: schema must be tradegen.venues/1")
    bad(lambda d: d.update(extra=1), "venues: unknown key(s) ['extra']")
    bad(lambda d: d[v]["kis"].update(markets=[]), "venues: kis: a quote_by_currency venue lists no markets")
    bad(lambda d: d[v]["kis"].update(default_quote="KRW"), "venues: kis: a quote_by_currency venue")
    bad(lambda d: d[v]["kis"].update(quote_by_currency=False), "venues: kis: quote_by_currency: only true")
    bad(lambda d: d[v]["upbit"].pop("markets"), "venues: upbit: markets: expected a list")
    bad(lambda d: d[v]["upbit"].pop("default_quote"), "venues: upbit: default_quote: None is not one of")
    bad(lambda d: d[v]["upbit"].update(default_quote="USDT"), "venues: upbit: default_quote: 'USDT' is not one of")
    bad(lambda d: d[v]["upbit"].update(markets=[["BTC"]]), "venues: upbit: markets: ['BTC'] is not a [base, quote]")
    bad(lambda d: d[v]["upbit"].update(markets=[["BTC", "KRW"], ["BTC", "KRW"]]),
        "upbit: markets: [BTC, KRW] is repeated")
    bad(lambda d: d[v]["upbit"].update(markets=[["BTC", "BTC"]]), "upbit: markets: [BTC, BTC]")
    bad(lambda d: d[v]["upbit"].update(markets=[["BTC", "krw"]]), "upbit: markets: 'krw' is not a symbol")
    bad(lambda d: d[v]["okx"].update(markets=[["BTC", "EUR"]]),
        "venues: okx: markets: quote EUR is neither a settlement asset nor a symbol")
    bad(lambda d: d[v]["upbit"].update(sections=[]), "venues: upbit: sections: expected a non-empty list")
    bad(lambda d: d[v]["upbit"].update(sections=["jp"]), "venues: upbit: sections", "'jp' is outside")
    bad(lambda d: d[v]["upbit"].update(settlement=[]), "venues: upbit: settlement: expected a non-empty list")
    bad(lambda d: d[v]["upbit"].pop("source"), "venues: upbit: missing key(s) ['source']")
    bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")
    # The odds keys (odds plan Task 2, Q17): only their exact names, a source each, then one refusal per rule.
    imap = _map()                           # parsed once: from here on, bad re-parses only the venue file

    def bad(mutate, *has):
        vdoc = _venues_doc()
        mutate(vdoc)
        _refused(lambda: rules.parse_venues(_dump(vdoc), imap), *has)

    lot, low = {"source": "s", "units": {"BTC": 1e-8}}, {"source": "s", "quote": {"KRW": 5000}}
    fees = {"source": "s", "phi_buy": 0, "phi_sell": 0}
    ticks = {"source": "s", "effective_from": "2026-10-02", "books": {"KRX_stock_book": [[0, 1], [2000, 5]]}}
    for near in ("lots", "lot_size", "minimum", "min_orders", "fees", "fee_extra", "tick", "ticks", "odds_sources"):
        bad(lambda d, k=near: d[v]["upbit"].update({k: dict(lot)}), f"venues: upbit: unknown key(s) [{near!r}]")
    for key, value, vid in (("lot", lot, "upbit"), ("min_order", low, "upbit"), ("fee_extras", fees, "upbit"),
                            ("tick_ladder", ticks, "kis")):
        at = f"venues: {vid}: {key}"
        bad(lambda d, k=key, w=vid: d[v][w].update({k: None}), f"{at}: expected a mapping")
        bad(lambda d, k=key, x=value, w=vid: d[v][w].update({k: {f: x[f] for f in x if f != "source"}}),
            f"{at}: missing key(s) ['source']")
        bad(lambda d, k=key, x=value, w=vid: d[v][w].update({k: {**x, "source": " "}}),
            f"{at}: source: expected a non-empty string")
        bad(lambda d, k=key, x=value, w=vid: d[v][w].update({k: {**x, "step": 1}}), f"{at}: unknown key(s) ['step']")
    up, tl = "venues: upbit", "venues: kis: tick_ladder"
    bad(lambda d: d[v]["upbit"].update(lot={"source": "s"}), f"{up}: lot: missing key(s) ['units']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {}}),
        f"{up}: lot: units: expected a non-empty mapping of symbol (or default) to a step")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": [1]}), f"{up}: lot: units: expected a non-empty mapping")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {"btc": 1}}),
        f"{up}: lot: units: 'btc' is not a symbol of sections ['crypto']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {"005930": 1}}),
        f"{up}: lot: units: '005930' is not a symbol of sections ['crypto']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {5930: 1}}),       # pre-flight P10: a YAML int key
        f"{up}: lot: units: 5930 is not a symbol of sections ['crypto']")
    for step in (0, -1, True, "1"):
        bad(lambda d, s=step: d[v]["upbit"].update(lot={**lot, "units": {"BTC": s}}),
            f"{up}: lot: units: BTC: expected a finite number > 0, got {step!r}")
    bad(lambda d: d[v]["upbit"].update(min_order={"source": "s"}), f"{up}: min_order: missing key(s) ['quote']")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": []}),
        f"{up}: min_order: quote: expected a non-empty mapping of settlement asset to a minimum")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": {"USDT": 1}}),
        f"{up}: min_order: quote: 'USDT' is not one of the settlement assets ['KRW']")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": {5000: 1}}),  # pre-flight P10: a YAML int key
        f"{up}: min_order: quote: 5000 is not one of the settlement assets ['KRW']")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": {"KRW": -1}}),
        f"{up}: min_order: quote: KRW: expected a finite number >= 0, got -1")
    bad(lambda d: d[v]["upbit"].update(fee_extras={**fees, "phi_sell": -1}),
        f"{up}: fee_extras: phi_sell: expected a finite number >= 0, got -1")
    bad(lambda d: d[v]["upbit"].update(fee_extras={**fees, "phi_buy": "0"}),
        f"{up}: fee_extras: phi_buy: expected a finite number >= 0, got '0'")
    bad(lambda d: d[v]["upbit"].update(fee_extras={**fees, "phi_buy": False}),
        f"{up}: fee_extras: phi_buy: expected a finite number >= 0, got False")
    bad(lambda d: d[v]["upbit"].update(fee_extras={"source": "s", "phi_buy": 0}),
        f"{up}: fee_extras: missing key(s) ['phi_sell']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_ETF_line": [[0, 1], [2000, 5]]}}),
        f"{tl}: books: KRX_ETF_line: its ladder is core/quant/instruments.py's")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock": [[0, 1]]}}),
        f"{tl}: books: 'KRX_stock' is not one of ['KRX_stock_book', 'US_shares_KIS', 'crypto_venue']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"crypto_venue": [[0, 1]]}}),
        f"{tl}: books: crypto_venue is the cost book of no symbol in sections ['krx', 'us']")
    bad(lambda d: d[v]["upbit"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 1]]}}),
        f"{up}: tick_ladder: books: KRX_stock_book is the cost book of no symbol in sections ['crypto']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {}}),
        f"{tl}: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": [["KRX_stock_book", [[0, 1]]]]}),
        f"{tl}: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": {"0": 1}}}),
        f"{tl}: books: KRX_stock_book: expected a non-empty list of [price_from, tick] rows")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": ["KRW"]}),
        f"{up}: min_order: quote: expected a non-empty mapping of settlement asset to a minimum")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": []}}),
        f"{tl}: books: KRX_stock_book: expected a non-empty list of [price_from, tick] rows")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 1, 2]]}}),
        f"{tl}: books: KRX_stock_book: [0, 1, 2] is not a [price_from, tick] row")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[1, 1], [2000, 5]]}}),
        f"{tl}: books: KRX_stock_book: the first price_from must be 0, got 1")
    for rows in ([[0, 1], [2000, 5], [2000, 10]], [[0, 1], [5000, 10], [2000, 5]]):
        bad(lambda d, r=rows: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": r}}),
            f"{tl}: books: KRX_stock_book: price_from {rows[2][0]!r} is not above the row before")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 0]]}}),
        f"{tl}: books: KRX_stock_book: tick: expected a finite number > 0, got 0")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 1], [-5, 1]]}}),
        f"{tl}: books: KRX_stock_book: price_from: expected a finite number >= 0, got -5")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[False, 1]]}}),
        f"{tl}: books: KRX_stock_book: price_from: expected a finite number >= 0, got False")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "effective_from": "20261002"}),
        f"{tl}: effective_from: expected a quoted YYYY-MM-DD date, got '20261002'")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "effective_from": "2026-13-01"}),
        f"{tl}: effective_from: '2026-13-01' is not a calendar date")
    bad(lambda d: d[v]["kis"].update(tick_ladder={"source": "s", "books": ticks["books"]}),
        f"{tl}: missing key(s) ['effective_from']")
    bad(lambda d: d[v].update(okx="not a mapping"), "venues: okx: expected a mapping")
    vdoc = _venues_doc()
    vdoc["venues"]["okx"]["markets"] = []                                # a markets venue may list none yet
    assert _facts(vdoc).venues["okx"].markets == frozenset()
    vdoc["venues"]["okx"]["markets"] = [["XRP", "BTC"]]                  # a quote may be a symbol of its sections
    assert _facts(vdoc).venues["okx"].markets == {("XRP", "BTC")}
    _refused(lambda: rules.parse_venues(b"schema: a\nschema: b\n", _map()), "venues: ", "duplicate key 'schema'")
    _refused(lambda: rules.parse_venues(b"schema: &a x\n", _map()), "venues: ", "anchor &a")
    _refused(lambda: rules.parse_venues(b"\xef\xbb\xbfschema: x\n", _map()), "venues: starts with a UTF-8 BOM")


def test_deposit_entries():
    def bad(deposits, *has):
        vdoc = _venues_doc()
        vdoc["venues"]["upbit"]["deposits"] = deposits
        _refused(lambda: _facts(vdoc), *has)

    btc = {"symbol": "BTC", "network": "bitcoin", "tag_required": False}
    bad([{**btc, "tag_required": "no"}], "venues: upbit: deposits.tag_required: expected true or false")
    bad([{**btc, "tag_required": 0}], "deposits.tag_required")
    bad([{"symbol": "BTC", "network": "bitcoin"}], "venues: upbit: deposits", "missing key(s) ['tag_required']")
    bad([{**btc, "memo": "x"}], "deposits", "unknown key(s) ['memo']")
    bad([btc, {**btc, "tag_required": True}], "venues: upbit: deposits: BTC on bitcoin is listed twice")
    bad([{**btc, "network": ""}], "deposits.network")
    bad(btc, "venues: upbit: deposits: expected a list")
    vdoc = _venues_doc()
    vdoc["venues"]["upbit"]["deposits"] = None
    assert _facts(vdoc).venues["upbit"].deposits == frozenset()
    vdoc["venues"]["upbit"]["deposits"] = [btc, {**btc, "network": "lightning"}]
    assert _facts(vdoc).venues["upbit"].deposits == {("BTC", "bitcoin", False), ("BTC", "lightning", False)}


# --------------------------------------------------------------------------- #
# Venue odds keys (odds plan Task 2; Q17): lot, min_order, fee_extras, tick_ladder
# --------------------------------------------------------------------------- #
_KRX_LADDER = [[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]


def _odds_venues_doc() -> dict:
    """_venues_doc() with all four odds keys on kis and upbit and none on okx, written out of order on purpose."""
    doc = _venues_doc()
    doc["venues"]["kis"].update(
        tick_ladder={"source": "https://example.invalid/ticks", "effective_from": "2026-10-02",
                     "books": {"US_shares_KIS": [[0, 0.01]], "KRX_stock_book": _KRX_LADDER}},
        lot={"source": "https://example.invalid/kis-lot", "units": {"default": 1, "005930": 1}},
        min_order={"source": "https://example.invalid/kis-min", "quote": {"USD": 0, "KRW": 0}},
        fee_extras={"source": "https://example.invalid/kis-fees", "phi_buy": 0, "phi_sell": 0.0})
    doc["venues"]["upbit"].update(
        lot={"source": _T5_UNVERIFIED, "units": {"default": 1e-8}},
        min_order={"source": _T5_UNVERIFIED, "quote": {"KRW": 5000}},
        fee_extras={"source": _T5_UNVERIFIED, "phi_buy": 12.5, "phi_sell": 0},
        tick_ladder={"source": _T5_UNVERIFIED, "effective_from": "2026-01-01", "books": {"crypto_venue": [[0, 1]]}})
    return doc


def test_venue_odds_keys_parse_to_exact_tuples():
    facts = _facts(_odds_venues_doc())
    kis, upbit, okx = facts.venues["kis"], facts.venues["upbit"], facts.venues["okx"]
    ladder = tuple((float(p), float(t)) for p, t in _KRX_LADDER)
    assert kis.lot == (("005930", 1.0), ("default", 1.0)) and kis.min_order == (("KRW", 0.0), ("USD", 0.0))
    assert kis.fee_extras == (0.0, 0.0)                        # an explicit 0 is a signed value (O11)
    assert kis.tick_ladder == (("KRX_stock_book", "2026-10-02", ladder),
                               ("US_shares_KIS", "2026-10-02", ((0.0, 0.01),)))
    assert kis.odds_sources == (("fee_extras", "https://example.invalid/kis-fees"),
                                ("lot", "https://example.invalid/kis-lot"),
                                ("min_order", "https://example.invalid/kis-min"),
                                ("tick_ladder", "https://example.invalid/ticks"))
    assert upbit.lot == (("default", 1e-8),) and upbit.min_order == (("KRW", 5000.0),)
    assert upbit.fee_extras == (12.5, 0.0) and upbit.tick_ladder == (("crypto_venue", "2026-01-01", ((0.0, 1.0),)),)
    assert upbit.odds_sources == tuple((k, _T5_UNVERIFIED) for k in ("fee_extras", "lot", "min_order", "tick_ladder"))
    numbers = [n for _, n in (*kis.lot, *kis.min_order, *upbit.lot, *upbit.min_order)]
    numbers += [*kis.fee_extras, *upbit.fee_extras] + [x for _, _, rows in kis.tick_ladder for row in rows for x in row]
    assert numbers and all(type(n) is float for n in numbers), numbers        # a YAML int is stored as a float
    assert (okx.lot, okx.min_order, okx.fee_extras, okx.tick_ladder, okx.odds_sources) == ((), (), None, (), ())
    assert okx == _facts().venues["okx"]                     # an absent key is the default, so the leg is not tradable
    assert kis.markets == frozenset() and kis.quote_by_currency and kis.settlement == {"KRW", "USD"}
    assert upbit.markets == {("BTC", "KRW"), ("USDT", "KRW")} and upbit.default_quote == "KRW"
    assert len({kis, upbit, okx}) == 3                       # every field stays hashable
    _need_model()
    from core.compliance import model
    state = rules.approved_state(_table(_row()), _dump(_map_doc()), _dump(_odds_venues_doc()), seq=1)
    assert state.valid and state.venues.venues["upbit"] == upbit, state.reason
    assert model.jsonable(upbit)["min_order"] == [["KRW", 5000.0]]          # seal_context can hash the new fields


def test_venue_odds_lookups_fall_back_and_answer_none():
    facts = _facts(_odds_venues_doc())
    kis, upbit, okx = facts.venues["kis"], facts.venues["upbit"], facts.venues["okx"]
    assert kis.lot_for("005930") == 1.0 and kis.lot_for("TQQQ") == 1.0      # TQQQ: the venue's default step
    assert upbit.lot_for("BTC") == upbit.lot_for("XRP") == 1e-8 and okx.lot_for("BTC") is None
    vdoc = _odds_venues_doc()
    vdoc["venues"]["kis"]["lot"]["units"] = {"005930": 10, "AAPL": 0.5}    # no default: every other symbol has none
    narrow = _facts(vdoc).venues["kis"]
    assert (narrow.lot_for("005930"), narrow.lot_for("AAPL"), narrow.lot_for("TQQQ")) == (10.0, 0.5, None)
    assert kis.min_order_for("KRW") == kis.min_order_for("USD") == 0.0
    assert upbit.min_order_for("KRW") == 5000.0 and upbit.min_order_for("USDT") is None
    assert okx.min_order_for("USDT") is None
    assert kis.ladder_for("KRX_stock_book") == ("2026-10-02", tuple((float(p), float(t)) for p, t in _KRX_LADDER))
    assert kis.ladder_for("US_shares_KIS") == ("2026-10-02", ((0.0, 0.01),))
    assert kis.ladder_for("KRX_ETF_line") is None and upbit.ladder_for("crypto_venue") == ("2026-01-01", ((0.0, 1.0),))
    assert okx.ladder_for("crypto_venue") is None
    for venue in (kis, upbit, okx):
        assert venue.lot_for(None) is None and venue.lot_for(["BTC"]) is None and venue.min_order_for(None) is None
        assert venue.min_order_for(["KRW"]) is None and venue.ladder_for(None) is None


def test_venue_odds_lookups_are_pure_tuple_lookups():
    """lot_for, min_order_for and ladder_for read only the Venue's own tuples: the gate's purity tests scan every
    Venue method (following any module-level def it names) and trap rules.date, rules.Path and rules.os, so no
    parse_date, file, clock or zone name, and no name of a module-level def of rules.py."""
    import ast
    import inspect
    import textwrap
    banned = {"parse_date", "date", "datetime", "Path", "os", "open", "read_bytes", "read_text", "scandir", "now",
              "today", "time", "ZoneInfo", "zoneinfo", "environ", "getenv"}
    defs = {n.name for n in ast.parse(inspect.getsource(rules)).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    for fn in (rules.Venue.lot_for, rules.Venue.min_order_for, rules.Venue.ladder_for):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert names & banned == set(), (fn.__name__, names & banned)
        assert names & defs == set(), (fn.__name__, names & defs)              # the gate's scan follows these
        own = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
               and isinstance(n.value, ast.Name) and n.value.id == "self"}
        assert own <= {"lot", "min_order", "tick_ladder"}, (fn.__name__, own)
        assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)), fn.__name__


def test_check_extras_lives_in_the_parser():
    """Spec 4 "Costs": extras may only raise costs. A negative fixed charge makes the venue file, and so the whole
    approved state, INVALID; it never reaches the odds engine (O3)."""
    _need_model()
    vdoc = _odds_venues_doc()
    vdoc["venues"]["upbit"]["fee_extras"]["phi_sell"] = -1
    state = rules.approved_state(_table(_row()), _dump(_map_doc()), _dump(vdoc), seq=1)
    want = "venues: upbit: fee_extras: phi_sell: expected a finite number >= 0, got -1"
    assert not state.valid and state.reason == want, state.reason
    for value in (float("nan"), float("inf"), -float("inf"), -0.5, True, None, "0", [0]):
        _refused(lambda value=value: rules._check_extras({"source": "s", "phi_buy": value, "phi_sell": 0}, "w"),
                 f"w: phi_buy: expected a finite number >= 0, got {value!r}")
    assert rules._check_extras({"source": "s", "phi_buy": 0, "phi_sell": 250}, "w") == (0.0, 250.0)
    _refused(lambda: rules._check_extras({"source": "", "phi_buy": 0, "phi_sell": 0}, "w"),
             "w: source: expected a non-empty string")
    _refused(lambda: rules._odds_number(float("nan"), "w", positive=True), "w: expected a finite number > 0, got nan")
    _refused(lambda: rules._odds_number(0.0, "w", positive=True), "w: expected a finite number > 0, got 0.0")
    assert rules._odds_number(0, "w", positive=False) == 0.0
    assert str(rules._odds_number(-0.0, "w", positive=False)) == "0.0"     # stored unsigned: never shown as -0.0
    assert type(rules._odds_number(3, "w", positive=True)) is float


# --------------------------------------------------------------------------- #
# Hashes and the approved state
# --------------------------------------------------------------------------- #
def _need_model() -> None:
    if importlib.util.find_spec("core.compliance.model") is None:
        raise NotRun("PENDING: core/compliance/model.py (Task 6)")


def test_approved_state_returns_invalid_never_raises():
    _need_model()
    good_rules, good_map, good_venues = _table(_row()), _dump(_map_doc()), _dump(_venues_doc())
    bad_venues = _venues_doc()
    bad_venues["venues"]["upbit"]["markets"] = [["ETH", "KRW"]]
    for args, kwargs, prefix in (
            ((b"rows: [", good_map, good_venues), {"seq": 3}, "rules: not YAML"),
            ((_table(_row(kind="policy")), good_map, good_venues), {"seq": 3}, "rules: row T-ALLOW: kind"),
            ((good_rules, b"\xef\xbb\xbfschema: x\n", good_venues), {"seq": 3}, "instruments: starts with a UTF-8 BOM"),
            ((good_rules, good_map, _dump(bad_venues)), {"seq": 3}, "venues: upbit: markets: base ETH"),
            ((good_rules.decode("utf-8"), good_map, good_venues), {"seq": 3}, "rules: expected bytes, got str"),
            ((good_rules, good_map, good_venues), {"seq": -1}, "seq: expected an int >= 0"),
            ((good_rules, good_map, good_venues), {"seq": True}, "seq: expected an int >= 0"),
            ((good_rules, good_map, good_venues), {"seq": 3, "history_raws": None}, "internal error TypeError")):
        state = rules.approved_state(*args, **kwargs)
        assert state.valid is False and state.reason.startswith(prefix), (prefix, state.reason)
        assert state.rules is None and state.instruments is None and state.venues is None and dict(state.hashes) == {}


def test_approved_state_hashes_are_the_raw_sha256s():
    _need_model()
    raws = {"rules": _table(_row(), _grey()), "instruments": _dump(_map_doc()), "venues": _dump(_venues_doc())}
    older = _map_doc()
    del older["us"]["TQQQ"]
    oldest = _map_doc()
    del oldest["us"]
    history = (_dump(older), b"schema: [broken\n", _dump(oldest))
    state = rules.approved_state(raws["rules"], raws["instruments"], raws["venues"], seq=7, history_raws=history)
    assert state.valid is True and state.reason == "" and state.seq == 7
    assert dict(state.hashes) == {k: hashlib.sha256(v).hexdigest() for k, v in raws.items()}
    assert dict(state.hashes) == {k: rules.file_sha256(v) for k, v in raws.items()}
    assert [r.id for r in state.rules.rows] == ["T-ALLOW", "T-GREY"]
    assert ("us", "TQQQ") in state.instruments.entries and set(state.venues.venues) == {"kis", "upbit", "okx"}
    assert len(state.history_maps) == 2                                   # the unparseable map is skipped
    assert ("us", "TQQQ") not in state.history_maps[0].entries and ("us", "SH") in state.history_maps[0].entries
    assert not any(k[0] == "us" for k in state.history_maps[1].entries)  # newest first, order kept
    commented = raws["rules"] + b"# a comment changes the bytes, not the table\n"
    again = rules.approved_state(commented, raws["instruments"], raws["venues"], seq=7)
    assert again.rules == state.rules and again.hashes["rules"] != state.hashes["rules"]
    assert again.history_maps == ()


def test_file_sha256():
    raw = _table(_row())
    assert rules.file_sha256(raw) == hashlib.sha256(raw).hexdigest()
    assert rules.file_sha256(raw[:-1] + b" ") != rules.file_sha256(raw)
    assert rules.file_sha256(b"") == hashlib.sha256(b"").hexdigest()


def test_calendar_sha256_stable_and_byte_sensitive():                           # P21
    from tests.macro_m1_calendars import fixture_set
    src = fixture_set().data_dir
    base = Path(tempfile.mkdtemp(prefix="tradegen_cal_"))      # every copy lives under it; finally removes it
    try:
        first, second = shutil.copytree(src, base / "first"), shutil.copytree(src, base / "second")
        names = sorted(p.name for p in first.iterdir() if p.is_file())
        assert "MANIFEST.yaml" in names and len(names) >= 2
        expected = hashlib.sha256(b"".join(n.encode("utf-8") + b"\0" + (first / n).read_bytes() + b"\0"
                                           for n in names)).hexdigest()
        assert rules.calendar_sha256(src) == rules.calendar_sha256(first) == rules.calendar_sha256(second) == expected
        (second / "notes").mkdir()                                       # a subdirectory is not in the set
        assert rules.calendar_sha256(second) == expected
        target = second / names[-1]
        data = bytearray(target.read_bytes())
        data[len(data) // 2] ^= 0x01                                     # flip one bit of one byte
        target.write_bytes(bytes(data))
        assert rules.calendar_sha256(second) != expected
        data[len(data) // 2] ^= 0x01
        target.write_bytes(bytes(data))
        assert rules.calendar_sha256(second) == expected
        (second / names[-1]).rename(second / ("z" + names[-1]))           # the name is hashed too
        assert rules.calendar_sha256(second) != expected
        _refused(lambda: rules.calendar_sha256(second / "missing"), "calendar: ", "is not a plain directory")
        _refused(lambda: rules.calendar_sha256(target.with_name("z" + names[-1])), "is not a plain directory")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_calendar_sha256_refuses_a_file_symlink():
    """NOT_RUN where os.symlink needs Developer Mode (this machine); the junction test covers the directory link."""
    from tests.macro_m1_calendars import fixture_set
    base = Path(tempfile.mkdtemp(prefix="tradegen_cal_"))
    try:
        root = shutil.copytree(fixture_set().data_dir, base / "set")
        try:
            os.symlink(root / "MANIFEST.yaml", root / "zz_link.yaml")
        except OSError:
            raise NotRun("REFDATA: symlink creation needs Developer Mode") from None
        _refused(lambda: rules.calendar_sha256(root), "calendar: zz_link.yaml is a link")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_calendar_sha256_refuses_a_junction():
    from tests.compliance_fixtures import directory_link
    from tests.macro_m1_calendars import fixture_set
    root = Path(tempfile.mkdtemp(prefix="tradegen_cal_")) / "set"   # finally removes root.parent
    try:
        shutil.copytree(fixture_set().data_dir, root)
        other = root.parent / "elsewhere"
        other.mkdir()
        directory_link(root / "linked", other)
        _refused(lambda: rules.calendar_sha256(root), "calendar: linked is a link")
        directory_link(root.parent / "alias", root)
        _refused(lambda: rules.calendar_sha256(root.parent / "alias"), "is not a plain directory")
    finally:
        for link in (root / "linked", root.parent / "alias"):
            if link.is_junction():
                link.rmdir()                                            # removes the junction, not its target
            elif link.is_symlink():
                link.unlink()
        shutil.rmtree(root.parent, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Task 5: the shipped drafts (core/compliance/kr_rules.yaml, core/compliance/instruments.yaml,
# core/odds/venues.yaml). Names carry a _t5_ / _T5_ prefix so they never shadow the Task 4 helpers above.
# --------------------------------------------------------------------------- #
import re as _t5_re
import string as _t5_string
from datetime import date as _t5_date
from pathlib import Path as _T5Path

from core.compliance import rules as _t5_rules

_T5_REPO = _T5Path(__file__).resolve().parents[1]
_T5_SHIPPED = {"rules": _T5_REPO / "core" / "compliance" / "kr_rules.yaml",
               "instruments": _T5_REPO / "core" / "compliance" / "instruments.yaml",
               "venues": _T5_REPO / "core" / "odds" / "venues.yaml"}
_T5_UNVERIFIED = "UNVERIFIED: owner to confirm before approval"
_T5_RESEARCH_DIRS = ("reports", "research_notes", "QUANTGEN_techfund_research_bundle")
_T5_REVIEW = _t5_date(2026, 10, 23)
# spec 5.3, with the slash ids split into their rows
_T5_SEED_IDS = frozenset({
    "KR-KIS-KRX-SHARE", "KR-KIS-KONEX", "KR-KIS-ETP-1X", "KR-KIS-ETP-INVERSE", "KR-KIS-ETP-LEV", "KR-KIS-SINGLE-ETP",
    "KR-KIS-CRYPTO-FUT-ETF", "KR-KIS-CRYPTO-SPOT-ETP", "KR-KIS-KRX-DERIV", "KR-KIS-ELW", "KR-KIS-CREDIT",
    "KR-KIS-SHORT", "KR-KIS-US-SHARE", "KR-KIS-US-OPTION", "KR-KIS-US-OPTION-WRITE", "KR-KIS-CRYPTO-DERIV",
    "KR-KIS-FUT-FX-CFD", "KR-DOMESTIC-SPOT", "KR-GOPAX", "KR-DOMESTIC-LENDING", "KR-DOMESTIC-CRYPTO-DERIV",
    "KR-TRANSFER-OUT", "KR-OKX-SPOT", "KR-OKX-WITHDRAW", "KR-OKX-DERIV", "KR-OKX-P2P", "KR-OFFSHORE-CEX",
    "KR-STATE-BLOCKED", "KR-BITMART", "KR-HYPERLIQUID", "KR-DEX", "KR-DRIFT", "KR-PREDICTION", "KR-SPORTSBOOK",
    "KR-IBKR", "KR-RETAIL-APPS", "KR-OFFSHORE-FX-CFD", "KR-LOTTERY-RACING", "KR-CONDUCT-EVENT", "KR-CONDUCT-SPORTS",
    "KR-CONDUCT-ROUTE", "KR-CONDUCT-OTHERS", "KR-CONDUCT-FX", "KR-CONDUCT-SIGNALS", "KR-CONDUCT-PROMOTE",
    "KR-CONDUCT-MANIP"})
_T5_EXTRA_IDS = frozenset({"KR-CONDUCT-COPY"})       # KR-CONDUCT-OTHERS' copy-trading tags, as their own row
_T5_TREATMENTS = {
    "allow": {"KR-KIS-KRX-SHARE", "KR-KIS-KONEX", "KR-KIS-ETP-1X", "KR-KIS-ETP-INVERSE", "KR-KIS-CRYPTO-FUT-ETF",
              "KR-KIS-US-SHARE", "KR-DOMESTIC-SPOT", "KR-TRANSFER-OUT"},
    "gated": {"KR-KIS-ETP-LEV", "KR-KIS-SINGLE-ETP", "KR-KIS-KRX-DERIV", "KR-KIS-ELW", "KR-KIS-SHORT",
              "KR-KIS-US-OPTION"},
    "grey": {"KR-OKX-SPOT"},
    "out_of_scope": {"KR-KIS-CREDIT", "KR-GOPAX", "KR-DOMESTIC-LENDING", "KR-OKX-WITHDRAW", "KR-OFFSHORE-CEX",
                     "KR-HYPERLIQUID", "KR-DEX", "KR-DRIFT", "KR-LOTTERY-RACING"},
}
_T5_POLICY = {"D16": {"KR-KIS-ETP-LEV", "KR-KIS-SINGLE-ETP", "KR-KIS-KRX-DERIV", "KR-KIS-ELW", "KR-KIS-SHORT"},
              "D15": {"KR-KIS-CREDIT", "KR-DOMESTIC-LENDING"},
              "D10": {"KR-OFFSHORE-CEX", "KR-HYPERLIQUID", "KR-DEX", "KR-DRIFT", "KR-LOTTERY-RACING"},
              "D11": {"KR-OKX-WITHDRAW"}}
# crypto, transfer and OKX rows: due 2026-11-22, before the 2026-12-03 FX Act change (spec 5.3 "Dates")
_T5_CRYPTO_IDS = frozenset({
    "KR-KIS-CRYPTO-FUT-ETF", "KR-KIS-CRYPTO-SPOT-ETP", "KR-KIS-CRYPTO-DERIV", "KR-DOMESTIC-SPOT", "KR-GOPAX",
    "KR-DOMESTIC-LENDING", "KR-DOMESTIC-CRYPTO-DERIV", "KR-TRANSFER-OUT", "KR-OKX-SPOT", "KR-OKX-WITHDRAW",
    "KR-OKX-DERIV", "KR-OKX-P2P", "KR-OFFSHORE-CEX", "KR-STATE-BLOCKED", "KR-BITMART", "KR-HYPERLIQUID", "KR-DEX",
    "KR-DRIFT", "KR-CONDUCT-ROUTE", "KR-CONDUCT-OTHERS", "KR-CONDUCT-COPY", "KR-CONDUCT-FX", "KR-CONDUCT-SIGNALS",
    "KR-CONDUCT-PROMOTE", "KR-CONDUCT-MANIP"})
_T5_OKX_WARNING = (
    "OKX is not registered with Korea's FIU. The FSC tells users of unregistered exchanges to withdraw their money. "
    "You get no Korean user protection, and withdrawals can be frozen. Upbit may stop transfers to OKX without "
    "notice. New rules start on 2026-12-03 and about 2027-02-18. TRADEGEN turns OKX off on 2026-12-03 and caps "
    "everything you hold on OKX at {cap} of your equity.")                      # spec 5.2, verbatim
_T5_CLASSES = {
    ("krx", "005930"): "share", ("krx", "069500"): "etp_1x", ("krx", "252670"): "etp_leveraged",
    ("krx", "114800"): "etp_index_inverse", ("us", "TQQQ"): "etp_leveraged", ("us", "SH"): "etp_index_inverse",
    ("us", "SPY"): "etp_1x", ("us", "AAPL"): "share", ("us", "IBIT"): "etp_crypto_spot",
    ("us", "FBTC"): "etp_crypto_spot", ("us", "ETHA"): "etp_crypto_spot", ("us", "GDLC"): "etp_crypto_spot",
    ("us", "EZPZ"): "etp_crypto_spot", ("us", "BITO"): "etp_crypto_futures_1x", ("crypto", "BTC"): "coin",
    ("crypto", "USDT"): "coin", ("crypto", "USDC"): "coin"}


def _t5_raw(kind: str) -> bytes:
    return _T5_SHIPPED[kind].read_bytes()


def _t5_shipped():
    """(RulesTable, InstrumentMap, VenueFacts) of the shipped drafts; any Invalid propagates."""
    table = _t5_rules.parse_rules(_t5_raw("rules"))
    imap = _t5_rules.parse_instruments(_t5_raw("instruments"))
    return table, imap, _t5_rules.parse_venues(_t5_raw("venues"), imap)


def _t5_row(table, row_id: str):
    hits = [r for r in table.rows if r.id == row_id]
    assert len(hits) == 1, (row_id, len(hits))
    return hits[0]


def _t5_slots(text: str) -> set[str]:
    return {name for _, name, _, _ in _t5_string.Formatter().parse(text) if name is not None}


def _t5_ref_ok(entry: str) -> bool:
    """An https URL, or a repo-relative path that exists. An `#L<n>` anchor must be a line of that file, and a
    `#compliance-matrix row <n>` anchor one of the 38 matrix rows."""
    if entry.startswith("https://"):
        return True
    path, _, anchor = entry.partition("#")
    target = _T5_REPO / path
    if not (path and ":" not in path and not path.startswith(("/", "\\"))
            and ".." not in _T5Path(path).parts and target.exists()):
        return False
    if m := _t5_re.fullmatch(r"L(\d+)", anchor):
        return target.is_file() and 1 <= int(m[1]) <= len(target.read_bytes().splitlines())
    if m := _t5_re.fullmatch(r"compliance-matrix row (\d+)", anchor):
        return 1 <= int(m[1]) <= 38
    return True


def test_shipped_tables_parse_valid():
    """The three drafts parse VALID; approved_state over them is Task 6's test (it needs core/compliance/model.py)."""
    table, imap, facts = _t5_shipped()
    assert table.schema == "tradegen.kr_rules/4"
    assert table.scope == "Korean-resident individual, own funds only"
    assert table.known_changes == (_t5_date(2026, 12, 3), _t5_date(2027, 1, 1), _t5_date(2027, 2, 18))
    assert len(imap.entries) == 17 and len(facts.venues) == 6


def test_shipped_files_are_utf8_lf_and_small():
    for kind, path in _T5_SHIPPED.items():
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, kind
        raw.decode("utf-8")
        assert raw.endswith(b"\n") and len(raw) <= _t5_rules.MAX_TABLE_BYTES, (kind, len(raw))


def test_shipped_matrix_rows_cover_1_to_38():
    table, _, _ = _t5_shipped()
    covered = {n for r in table.rows for n in r.matrix_rows}
    assert covered == set(range(1, 39)), sorted(set(range(1, 39)) - covered)


def test_shipped_seed_row_ids_present():
    table, _, _ = _t5_shipped()
    ids = [r.id for r in table.rows]
    assert len(ids) == len(set(ids))
    assert _T5_SEED_IDS <= set(ids), sorted(_T5_SEED_IDS - set(ids))
    assert set(ids) - _T5_SEED_IDS == _T5_EXTRA_IDS, sorted(set(ids) - _T5_SEED_IDS)


def test_shipped_treatments_follow_spec_5_3():
    table, _, _ = _t5_shipped()
    for treatment in ("allow", "gated", "grey", "out_of_scope"):
        assert {r.id for r in table.rows if r.treatment == treatment} == _T5_TREATMENTS[treatment], treatment
    for ref, ids in _T5_POLICY.items():
        assert {r.id for r in table.rows if r.policy_ref == ref} == ids, ref
        assert all("policy" in _t5_row(table, rid).basis for rid in ids), ref
    assert {r.policy_ref for r in table.rows} == set(_T5_POLICY) | {None}
    assert {r.id for r in table.rows if r.kind == "conduct"} == {i for i in _T5_SEED_IDS | _T5_EXTRA_IDS
                                                                 if i.startswith("KR-CONDUCT-")}
    for r in table.rows:                     # a row that can let something through names every axis exactly
        if r.treatment in ("allow", "gated", "grey"):
            assert {"venue", "action", "financing"} <= set(r.match) and {"asset", "class"} & set(r.match), r.id
            assert r.match["financing"] == frozenset({"cash"}), r.id
            assert all("any" not in values for values in r.match.values()), r.id


def test_shipped_rows_cannot_lose_an_axis():
    """The review's reproductions on the shipped table: KR-DOMESTIC-SPOT without `financing` (it would ALLOW an
    Upbit margin or credit buy), without `action` as well (sell_short, p2p_buy), and KR-KIS-US-OPTION gated on
    nothing (an allow row) are each Invalid."""
    raw = _t5_raw("rules")
    spot = b"match: {venue: [upbit, bithumb, coinone, korbit], class: [coin], action: [buy, sell], financing: [cash]}"
    option = b"requires: {owner: [us_option_course_1h, us_option_mock_3h, broker_eligibility], live: []}"
    assert raw.count(spot) == 1 and raw.count(option) == 1
    for old, new, has in (
            (spot, spot.replace(b", financing: [cash]", b""), "missing ['financing']"),
            (spot, spot.replace(b", action: [buy, sell], financing: [cash]", b""), "missing ['action', 'financing']"),
            (option, b"requires: {owner: [], live: []}", "a gated row requires owner or live evidence")):
        _refused(lambda: _t5_rules.parse_rules(raw.replace(old, new)), has)


def test_shipped_d16_rows_need_live_evidence():
    table, _, _ = _t5_shipped()
    for r in table.rows:
        if r.policy_ref == "D16":
            assert r.treatment == "gated" and r.requires_live, r.id
    assert set(_t5_row(table, "KR-KIS-SHORT").requires_live) == {"broker_approval", "collateral_105pct"}
    assert set(_t5_row(table, "KR-KIS-SINGLE-ETP").requires_live) == {"cash_krw_30m"}
    krx_deriv = _t5_row(table, "KR-KIS-KRX-DERIV")          # D16: broker eligibility is live evidence, not an owner snapshot
    assert "broker_approval" in krx_deriv.requires_live and "broker_eligibility" not in krx_deriv.requires_owner
    assert "broker approval" in krx_deriv.reason, krx_deriv.reason   # the reason names what requires.live asks (ledger:118)
    assert krx_deriv.reason.startswith("KOSPI200 futures and options need broker approval, "), krx_deriv.reason   # R3
    assert not _t5_row(table, "KR-KIS-US-OPTION").requires_live      # gated on owner evidence, not D16
    assert _t5_row(table, "KR-KIS-ETP-LEV").max_leverage == 3.0
    assert _t5_row(table, "KR-KIS-SINGLE-ETP").max_leverage == 2.0
    for r in table.rows:
        if r.id not in ("KR-KIS-ETP-LEV", "KR-KIS-SINGLE-ETP"):
            assert r.max_leverage == 1.0, r.id


def test_shipped_okx_spot_is_the_d6_grey_row():
    table, _, _ = _t5_shipped()
    row = _t5_row(table, "KR-OKX-SPOT")
    assert row.match == {"venue": frozenset({"okx"}), "class": frozenset({"coin"}),
                         "action": frozenset({"buy", "sell"}), "financing": frozenset({"cash"})}
    assert (row.ack, row.cap_key, row.auto_off) == ("per_session", "okx_equity_share", _t5_date(2026, 12, 3))
    assert set(row.requires_owner) == {"age_of_majority"} and not row.requires_live
    assert row.effective_until == _t5_date(2027, 2, 18) and row.confidence == "low"
    assert {"https://www.fsc.go.kr/no010101/87177", "https://www.okx.com/help/risk-compliance-disclosure",
            "https://www.fsc.go.kr/no010101/87499"} <= set(row.sources)
    assert row.effective_from != _t5_date(2021, 3, 25)        # P25: the spec example's date has no source
    assert _t5_row(table, "KR-KIS-US-OPTION").ack == "per_session"
    assert _t5_row(table, "KR-TRANSFER-OUT").ack == "per_transfer"
    assert {r.id for r in table.rows if r.ack is not None} == {"KR-OKX-SPOT", "KR-KIS-US-OPTION", "KR-TRANSFER-OUT"}


_T5_PINNED = {                                   # (match, requires_owner, requires_live, treatment), ledger:113
    "KR-KIS-KRX-SHARE": ({"venue": {"kis"}, "asset": {"krx_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                         (), (), "allow"),
    "KR-KIS-KONEX": ({"venue": {"kis"}, "class": {"konex_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                     (), (), "allow"),
    "KR-KIS-ETP-1X": ({"venue": {"kis"}, "class": {"etp_1x"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                      (), (), "allow"),
    "KR-KIS-ETP-INVERSE": ({"venue": {"kis"}, "class": {"etp_index_inverse"}, "action": {"buy", "sell"},
                            "financing": {"cash"}}, (), (), "allow"),
    "KR-KIS-ETP-LEV": ({"venue": {"kis"}, "class": {"etp_leveraged"}, "action": {"buy"}, "financing": {"cash"}},
                       ("kofia_leveraged_1h",), ("deposit_krw_10m",), "gated"),
    "KR-KIS-SINGLE-ETP": ({"venue": {"kis"}, "class": {"etp_single_stock"}, "action": {"buy"}, "financing": {"cash"}},
                          ("kofia_single_stock_3h", "krx_mock_5h_5days"), ("cash_krw_30m",), "gated"),
    "KR-KIS-CRYPTO-FUT-ETF": ({"venue": {"kis"}, "class": {"etp_crypto_futures_1x"}, "action": {"buy", "sell"},
                               "financing": {"cash"}}, (), (), "allow"),
    "KR-KIS-KRX-DERIV": ({"venue": {"kis"}, "class": {"krx_derivative"}, "action": {"buy", "sell_short", "write"},
                          "financing": {"cash"}}, ("kofia_derivatives_1h", "krx_derivatives_mock_3h"),
                         ("broker_approval", "deposit_krw_10m", "deposit_krw_20m"), "gated"),
    "KR-KIS-ELW": ({"venue": {"kis"}, "class": {"elw"}, "action": {"buy"}, "financing": {"cash"}},
                   ("elw_course",), ("deposit_krw_15m",), "gated"),
    "KR-KIS-SHORT": ({"venue": {"kis"}, "asset": {"krx_share"}, "action": {"sell_short"}, "financing": {"cash"}},
                     ("short_course_30m", "short_mock_1h"), ("broker_approval", "collateral_105pct"), "gated"),
    "KR-KIS-US-SHARE": ({"venue": {"kis"}, "asset": {"us_share"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                        (), (), "allow"),
    "KR-KIS-US-OPTION": ({"venue": {"kis"}, "class": {"option"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                         ("us_option_course_1h", "us_option_mock_3h", "broker_eligibility"), (), "gated"),
    "KR-DOMESTIC-SPOT": ({"venue": {"bithumb", "coinone", "korbit", "upbit"}, "class": {"coin"},
                          "action": {"buy", "sell"}, "financing": {"cash"}}, (), (), "allow"),
    "KR-TRANSFER-OUT": ({"venue": {"bithumb", "coinone", "korbit", "upbit"}, "class": {"coin"},
                         "action": {"transfer_out"}, "financing": {"cash"}}, (), (), "allow"),
    "KR-OKX-SPOT": ({"venue": {"okx"}, "class": {"coin"}, "action": {"buy", "sell"}, "financing": {"cash"}},
                    ("age_of_majority",), (), "grey"),
}


def _t5_pin_misses(table) -> list[str]:
    """The ids where the allow, gated and grey rows of `table` and _T5_PINNED differ: an id in only one of the two,
    or a row whose (match, requires_owner, requires_live, treatment) is not its pin."""
    rows = {r.id: r for r in table.rows if r.treatment in ("allow", "gated", "grey")}
    misses = sorted(set(rows) ^ set(_T5_PINNED))
    for rid in sorted(set(rows) & set(_T5_PINNED)):
        r = rows[rid]
        if ({k: set(v) for k, v in r.match.items()}, r.requires_owner, r.requires_live, r.treatment) != _T5_PINNED[rid]:
            misses.append(rid)
    return misses


def test_shipped_rows_that_can_let_through_are_pinned_exactly():
    """The 15 shipped rows that can let an intent through, pinned exactly (R2). ledger:113: widening an allow row
    (sell_short on KR-KIS-US-SHARE, p2p_buy on KR-DOMESTIC-SPOT) passed every test of the compliance plan's Task 5.
    Now the loader refuses the first (D16 by content) and the pin catches the second, a dropped owner requirement,
    and a row leaving or entering the set; a deliberate change to one of these rows edits its pin in the same commit."""
    raw = _t5_raw("rules")
    spot = b"match: {venue: [upbit, bithumb, coinone, korbit], class: [coin], action: [buy, sell], financing: [cash]}"
    us = b"match: {venue: [kis], asset: [us_share], action: [buy, sell], financing: [cash]}"
    option = b"requires: {owner: [us_option_course_1h, us_option_mock_3h, broker_eligibility], live: []}"
    one_x = b"match: {venue: [kis], class: [etp_1x], action: [buy, sell], financing: [cash]}\n    treatment: allow\n"
    etp = b"match: {venue: [kis], class: [etp_crypto_spot], action: [buy]}\n    treatment: hard_block\n"
    opened = etp.replace(b"[buy]}", b"[buy], financing: [cash]}").replace(b"hard_block", b"allow")
    assert all(raw.count(old) == 1 for old in (spot, us, option, one_x, etp))
    for old, new, missed in ((spot, spot.replace(b"[buy, sell]", b"[buy, sell, p2p_buy]"), ["KR-DOMESTIC-SPOT"]),
                             (option, option.replace(b", broker_eligibility", b""), ["KR-KIS-US-OPTION"]),
                             (one_x, one_x.replace(b"allow", b"hard_block"), ["KR-KIS-ETP-1X"]),   # a row leaves
                             (etp, opened, ["KR-KIS-CRYPTO-SPOT-ETP"])):           # a blocking row turns allow
        assert _t5_pin_misses(_t5_rules.parse_rules(raw.replace(old, new))) == missed, missed
    _refused(lambda: _t5_rules.parse_rules(raw.replace(us, us.replace(b"[buy, sell]", b"[buy, sell, sell_short]"))),
             "row KR-KIS-US-SHARE: requires.live: a row matching ['sell_short']")
    table, _, _ = _t5_shipped()
    assert len(_T5_PINNED) == 15 and _t5_pin_misses(table) == [], _t5_pin_misses(table)


def test_shipped_okx_warning_has_only_the_cap_slot():
    table, _, _ = _t5_shipped()
    row = _t5_row(table, "KR-OKX-SPOT")
    assert row.warning == _T5_OKX_WARNING
    assert _t5_slots(row.warning) == {"cap"}
    text = row.warning.format(cap="10%")
    assert text.endswith("caps everything you hold on OKX at 10% of your equity.")
    assert "{" not in text and "}" not in text
    for r in table.rows:
        if r.id != "KR-OKX-SPOT":
            assert _t5_slots(r.warning) == set(), r.id
    assert {r.id for r in table.rows if r.warning} == {"KR-OKX-SPOT", "KR-KIS-US-OPTION"}


def test_shipped_review_cadence_and_dates():
    """Pins the 2026-10-23 seed review. A monthly re-review changes these dates on purpose, here too."""
    table, _, _ = _t5_shipped()
    for r in table.rows:
        assert [(v.date, v.by) for v in r.reviews] == [(_T5_REVIEW, "claude-research")], r.id
        assert r.effective_from <= _T5_REVIEW, r.id          # every seed row is in force on its review date
        if r.id in _T5_CRYPTO_IDS:
            assert r.review_by == _t5_date(2026, 11, 22) and _t5_date(2026, 12, 3) in r.affected_by, r.id
        else:
            assert r.review_by == _t5_date(2026, 11, 23) and r.affected_by == (), r.id
    assert [r.id for r in table.rows if r.effective_until is not None] == ["KR-TRANSFER-OUT", "KR-OKX-SPOT"]
    for rid in ("KR-TRANSFER-OUT", "KR-OKX-SPOT"):
        row = _t5_row(table, rid)
        assert row.effective_until == _t5_date(2027, 2, 18) and row.confidence == "low", rid
        assert "about 2027-02-18" in row.reason and _t5_date(2027, 2, 18) in row.affected_by, rid


def test_shipped_conduct_rows_match_every_venue():
    table, _, _ = _t5_shipped()
    conduct = [r for r in table.rows if r.kind == "conduct"]
    for r in conduct:
        assert r.treatment == "hard_block" and r.match["venue"] == frozenset({"any"}), r.id
        assert len(set(r.match) - {"venue"}) == 1, r.id          # one axis per row, so no AND can narrow it
    assert {t for r in conduct for t in r.match.get("tag", ())} == set(_t5_rules.TAGS)
    assert {w for r in conduct for w in r.match.get("when", ())} == set(_t5_rules.WHEN)
    assert {a for r in conduct for a in r.match.get("asset", ())} == {"event_contract", "sports_bet"}
    assert _t5_row(table, "KR-CONDUCT-SPORTS").match["asset"] == frozenset({"sports_bet"})       # P17
    assert _t5_row(table, "KR-STATE-BLOCKED").match["venue"] == frozenset(_t5_rules.STATE_BLOCKED)   # P23
    assert _t5_row(table, "KR-PREDICTION").match["venue"] == frozenset(_t5_rules.PREDICTION_VENUES)


def test_shipped_citation_fixes_p13_p25():
    """Blocks resting on platform terms or owner policy are not labelled legal only, and each row's matrix rows
    are the ones the research actually covers."""
    table, _, _ = _t5_shipped()
    platform = {"KR-KIS-US-OPTION-WRITE", "KR-DOMESTIC-CRYPTO-DERIV", "KR-OKX-DERIV", "KR-OKX-P2P",
                "KR-PREDICTION", "KR-RETAIL-APPS", "KR-CONDUCT-ROUTE"}
    assert {r.id for r in table.rows if "platform" in r.basis} == platform
    assert _t5_row(table, "KR-OKX-DERIV").basis == _t5_row(table, "KR-OKX-P2P").basis == frozenset({"platform"})
    assert _t5_row(table, "KR-CONDUCT-ROUTE").basis == frozenset({"policy", "platform"})
    assert "policy" in _t5_row(table, "KR-KIS-FUT-FX-CFD").basis
    no_matrix_row = {"KR-KIS-CRYPTO-FUT-ETF", "KR-KIS-CRYPTO-SPOT-ETP", "KR-KIS-CRYPTO-DERIV", "KR-GOPAX",
                     "KR-CONDUCT-FX", "KR-CONDUCT-SIGNALS"}
    assert {r.id for r in table.rows if not r.matrix_rows} == no_matrix_row
    assert _t5_row(table, "KR-DRIFT").matrix_rows == (5,)
    assert _t5_row(table, "KR-CONDUCT-MANIP").matrix_rows == (10, 16)
    assert {r.id for r in table.rows if 20 in r.matrix_rows} == {"KR-CONDUCT-OTHERS", "KR-CONDUCT-COPY"}
    assert _t5_row(table, "KR-CONDUCT-PROMOTE").matrix_rows == (13,)       # the FSC 2026-06-24 warning's row
    assert {r.id for r in table.rows if 10 in r.matrix_rows} == {"KR-DOMESTIC-SPOT", "KR-CONDUCT-MANIP"}
    short = _t5_row(table, "KR-KIS-SHORT")
    assert short.confidence == "low" and "unverified" in short.reason
    derivs = _t5_row(table, "KR-KIS-KRX-DERIV")
    assert {"kofia_derivatives_1h", "krx_derivatives_mock_3h"} <= set(derivs.requires_owner)


def test_shipped_instrument_map_entries_and_classes():
    _, imap, _ = _t5_shipped()
    assert {k: v.cls for k, v in imap.entries.items()} == _T5_CLASSES
    for (section, symbol), inst in imap.entries.items():
        assert (inst.section, inst.symbol) == (section, symbol)
        assert inst.cls == _t5_rules.derive_class(inst.asset, inst.multiple, inst.underlying), symbol
        assert inst.tax_basis in _t5_rules.TAX_BASES and inst.cost_book in _t5_rules.COST_BOOKS, symbol
        assert inst.currency == {"krx": "KRW", "us": "USD", "crypto": "KRW"}[section], symbol
    assert imap.entries[("krx", "252670")].multiple == -2.0 and imap.entries[("us", "TQQQ")].multiple == 3.0
    assert imap.entries[("krx", "114800")].multiple == -1.0 and imap.entries[("us", "SH")].multiple == -1.0
    assert imap.entries[("us", "BITO")].underlying == "crypto_futures"


def test_shipped_known_spot_crypto_etps_derive_etp_crypto_spot():
    _, imap, _ = _t5_shipped()
    shipped = {sym for (sec, sym) in imap.entries if sec == "us"} & _t5_rules.KNOWN_SPOT_CRYPTO_ETPS
    assert shipped == {"IBIT", "FBTC", "ETHA", "GDLC", "EZPZ"}
    for sym in shipped:
        inst = imap.entries[("us", sym)]
        assert inst.asset == "us_etp" and inst.underlying in ("crypto_spot", "crypto_spot_basket"), sym
        assert inst.cls == "etp_crypto_spot" == _t5_rules.derive_class(inst.asset, inst.multiple, inst.underlying)
    assert {sym for (_, sym), i in imap.entries.items() if i.underlying == "crypto_spot_basket"} == {"GDLC", "EZPZ"}
    for inst in imap.entries.values():
        if inst.underlying in ("crypto_spot", "crypto_spot_basket"):
            assert inst.cls == "etp_crypto_spot", inst.symbol


def test_shipped_cost_books_are_quant_books():
    from core.quant.instruments import INSTRUMENT_BOOKS
    assert set(_t5_rules.COST_BOOKS) <= set(INSTRUMENT_BOOKS)
    _, imap, _ = _t5_shipped()
    assert {inst.cost_book for inst in imap.entries.values()} == set(_t5_rules.COST_BOOKS)
    assert imap.entries[("krx", "005930")].cost_book == "KRX_stock_book"
    assert imap.entries[("krx", "252670")].cost_book == "KRX_ETF_line" == INSTRUMENT_BOOKS["KRX_ETF_line"].book_id


def test_shipped_venue_facts_p22():
    _, _, facts = _t5_shipped()
    v = facts.venues
    assert set(v) == {"kis", "upbit", "bithumb", "coinone", "korbit", "okx"}
    assert v["kis"].sections == ("krx", "us") and v["kis"].quote_by_currency
    assert v["kis"].markets == frozenset() and v["kis"].default_quote is None
    assert v["kis"].settlement == frozenset({"KRW", "USD"})
    assert v["upbit"].markets == frozenset({("BTC", "KRW"), ("USDT", "KRW")})        # KRW-quoted only
    assert v["okx"].markets == frozenset({("BTC", "USDT"), ("BTC", "USDC")})
    assert v["okx"].settlement == frozenset({"USDT", "USDC"}) and v["okx"].default_quote == "USDT"
    for vid in ("upbit", "bithumb", "coinone", "korbit"):
        assert v[vid].settlement == frozenset({"KRW"}) and v[vid].default_quote == "KRW", vid
    for vid in ("upbit", "bithumb", "coinone", "korbit", "okx"):
        assert v[vid].sections == ("crypto",) and not v[vid].quote_by_currency, vid
    assert v["upbit"].deposits == v["okx"].deposits == frozenset({("BTC", "bitcoin", False)})
    for vid in ("kis", "bithumb", "coinone", "korbit"):
        assert v[vid].deposits == frozenset(), vid             # a withdrawal there fails closed
    assert set(_t5_rules.DOMESTIC_EXCHANGES) <= set(v)


def test_shipped_venue_markets_resolve():
    _, imap, facts = _t5_shipped()
    v = facts.venues
    sam, spy = imap.entries[("krx", "005930")], imap.entries[("us", "SPY")]
    btc, usdt = imap.entries[("crypto", "BTC")], imap.entries[("crypto", "USDT")]
    assert v["kis"].is_market(sam, "KRW") and v["kis"].is_market(spy, "USD")
    assert not v["kis"].is_market(spy, "KRW") and not v["kis"].is_market(sam, "USD")
    assert not v["kis"].is_market(btc, "KRW")                      # coins are not in kis's sections
    assert (v["kis"].quote_for(sam), v["kis"].quote_for(spy)) == ("KRW", "USD")
    assert v["upbit"].is_market(btc, "KRW") and v["upbit"].is_market(usdt, "KRW")
    assert not v["upbit"].is_market(btc, "USDT") and v["upbit"].quote_for(btc) == "KRW"
    assert v["okx"].is_market(btc, "USDT") and v["okx"].is_market(btc, "USDC")
    assert not v["okx"].is_market(usdt, "BTC") and v["okx"].quote_for(btc) == "USDT"
    assert imap.lookup(v["kis"].sections, "BTC") is None and imap.lookup(v["upbit"].sections, "SPY") is None
    assert imap.lookup(v["kis"].sections, "252670") is imap.entries[("krx", "252670")]


def test_shipped_sources_are_https_or_repo_paths():
    table, imap, _ = _t5_shipped()
    for r in table.rows:
        assert r.sources and r.research, r.id
        for entry in r.sources:
            assert _t5_ref_ok(entry), (r.id, entry)
        for entry in r.research:
            assert not entry.startswith("https://") and _t5_ref_ok(entry), (r.id, entry)
    for inst in imap.entries.values():
        assert inst.source.startswith("https://") or inst.source == _T5_UNVERIFIED, inst.symbol
    doc = _t5_rules.load_strict(_t5_raw("venues"), "venues")
    for vid, entry in doc["venues"].items():
        assert _t5_ref_ok(entry["source"]) or entry["source"] == _T5_UNVERIFIED, vid


def test_shipped_urls_come_from_the_research():
    """No invented URL: every https URL in the three drafts is exactly a URL of the repo's research notes, so a
    truncated one fails. A new source is recorded in reports/ or research_notes/ before it is cited here."""
    corpus = b"\n".join(p.read_bytes() for d in _T5_RESEARCH_DIRS for p in sorted((_T5_REPO / d).rglob("*.md")))
    known = {u.rstrip(b".,;*") for u in _t5_re.findall(rb"https://[^\s)\]>\"'`|]+", corpus)}
    for kind in _T5_SHIPPED:
        urls = _t5_re.findall(r'https://[^"\s]+', _t5_raw(kind).decode("utf-8"))
        assert urls, kind
        for url in urls:
            assert url.encode("utf-8") in known, (kind, url)


# --------------------------------------------------------------------------- #
# Odds plan Task 3 (Q18): the sourced odds values of the shipped venues.yaml. No research source gives a fixed
# charge, an Upbit, OKX or US lot, or a US or OKX minimum, so those stay absent and every leg is not tradable until
# the owner adds them (an explicit 0 included) and approves the venues file (O11; a replay leg needs only the Upbit
# lot, R2-5).
# --------------------------------------------------------------------------- #
_T5_KIS_LOTS = "research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md#L161"
_T5_KIS_TICKS = "https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp"
_T5_UPBIT_MIN = "https://docs.upbit.com/kr/docs/krw-market-info"


def test_shipped_venue_odds_values_are_the_sourced_ones():
    _, _, facts = _t5_shipped()
    v = facts.venues
    kis, upbit = v["kis"], v["upbit"]
    assert kis.odds_sources == (("lot", _T5_KIS_LOTS), ("min_order", _T5_KIS_LOTS),
                                ("tick_ladder", _T5_KIS_TICKS)), kis.odds_sources
    assert kis.lot == (("005930", 1.0), ("069500", 1.0)) and kis.min_order == (("KRW", 0.0),)
    ladder = tuple((float(p), float(t)) for p, t in _KRX_LADDER)
    assert kis.tick_ladder == (("KRX_stock_book", "2026-10-02", ladder),), kis.tick_ladder
    assert upbit.odds_sources == (("min_order", _T5_UPBIT_MIN),) and upbit.min_order == (("KRW", 5000.0),)
    assert upbit.lot == () and upbit.tick_ladder == ()
    for vid, venue in v.items():
        assert venue.fee_extras is None, vid                 # no fixed charge is researched: not tradable (O11)
        if vid not in ("kis", "upbit"):
            assert (venue.lot, venue.min_order, venue.tick_ladder, venue.odds_sources) == ((), (), (), ()), vid
        for key, source in venue.odds_sources:
            assert _t5_ref_ok(source) or source == _T5_UNVERIFIED, (vid, key, source)
    assert kis.lot_for("005930") == kis.lot_for("069500") == 1.0 and kis.lot_for("SPY") is None
    assert kis.min_order_for("KRW") == 0.0 and kis.min_order_for("USD") is None    # a US leg has no signed minimum
    assert upbit.lot_for("BTC") is None and upbit.min_order_for("KRW") == 5000.0
    assert kis.ladder_for("KRX_stock_book") == ("2026-10-02", ladder) and kis.ladder_for("KRX_ETF_line") is None
    # _t5_ref_ok only checks that a cited line exists; pin what the research says for every shipped value
    path, _, anchor = _T5_KIS_LOTS.partition("#")
    lines = (_T5_REPO / path).read_bytes().splitlines()
    stocks, etfs = lines[160].decode("utf-8"), lines[162].decode("utf-8")
    assert anchor == "L161" and stocks.startswith("| KOSPI/KOSDAQ cash stocks"), stocks
    assert f"| {kis.lot_for('005930'):g} share |" in stocks, stocks     # the parsed lot is the one the research gives
    assert etfs.startswith("| Plain 1x ETF/ETN") and f"| {kis.lot_for('069500'):g} unit |" in etfs, etfs
    e2 = (_T5_REPO / "QUANTGEN_techfund_research_bundle" / "QUANTGEN_techfund_research" / "research_notes"
          / "E2_nyse_microstructure_execution.md").read_bytes().decode("utf-8").splitlines()
    bands = e2[307:314]                              # lines 308-314: the seven KRX price bands and their ticks
    nums = [[float(n.replace(",", "")) for n in _t5_re.findall(r"\d[\d,]*", band)] for band in bands]
    research = tuple((0.0 if "| below " in band else n[0], n[-1]) for band, n in zip(bands, nums))
    assert research == ladder and _T5_KIS_TICKS in e2[315], research
    day = _t5_date.fromisoformat(kis.tick_ladder[0][1])        # the parsed effective_from is the research's date
    assert e2[2].startswith(f"As of {day.day} {day:%B %Y}."), e2[2]
    up = (_T5_REPO / "research_notes" / "Korean resident trading venue legality"
          / "crypto_domestic_and_overseas_verification.md").read_bytes().decode("utf-8").splitlines()[20]
    assert f"Upbit {upbit.min_order_for('KRW'):,.0f} KRW minimum is confirmed" in up and _T5_UPBIT_MIN in up, up
    # the header clause of CONTRACT 4.2, word for word, in place of the old "ticks later" clause; line 4 unchanged
    head = _t5_raw("venues").split(b"\nschema:", 1)[0].decode("utf-8")
    flat = " ".join(line.removeprefix("# ") for line in head.splitlines())
    clause = ("The compliance plan writes markets, settlement and deposits only; the odds plan added the sourced "
              "lots, minimums and the KRX stock tick ladder; every other odds value is absent until the owner adds "
              "it, so those legs are not tradable, and this file's sha256 changed, so it needs a new approval.")
    assert clause in flat and "ticks later" not in head and head.endswith(
        "\n# A venue with no deposit entry for a coin credits none, so a withdrawal there fails closed."), head
