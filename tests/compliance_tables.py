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
        _parse(_row(match={"venue": ["upbit"], key: [good]}))
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
           "match": {"venue": ["kis"], "class": ["etp_leveraged"], "action": ["buy"]}, "matrix_rows": [25, 32]}
    _bad(_row(), _row(**lev), "row T-LEV: requires.live")
    _bad(_row(), _row(**lev, requires={"owner": ["kofia_leveraged_1h"]}), "row T-LEV: requires.live")
    _bad(_row(), _row(**{**lev, "policy_ref": "D15, D16"}), "row T-LEV: requires.live")
    ok = _parse(_row(), _row(**lev, requires={"owner": ["kofia_leveraged_1h"], "live": ["deposit_krw_10m"]})).rows[1]
    assert ok.requires_live == ("deposit_krw_10m",) and ok.requires_owner == ("kofia_leveraged_1h",)
    assert ok.policy_ref == "D16" and ok.basis == {"legal", "policy"}
    _parse(_row(), _row(**{**lev, "policy_ref": "D160"}))          # D160 is not D16
    _parse(_row(), _row(**{**lev, "policy_ref": "D15", "treatment": "out_of_scope"}))
    for ref in ("d16", "D-16", "D 16", "D16a", "owner decision 16", "D15,D16", "D15, D16,", 16, ["D16"]):
        _bad(_row(), _row(**{**lev, "policy_ref": ref}), "row T-LEV: policy_ref")


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
    for text in ("OKX is capped at {cap} of your equity.", "no slot at all", "literal {{cap}} braces", ""):
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
    import _winapi
    from tests.macro_m1_calendars import fixture_set
    root = Path(tempfile.mkdtemp(prefix="tradegen_cal_")) / "set"   # finally removes root.parent
    try:
        shutil.copytree(fixture_set().data_dir, root)
        other = root.parent / "elsewhere"
        other.mkdir()
        _winapi.CreateJunction(str(other), str(root / "linked"))
        _refused(lambda: rules.calendar_sha256(root), "calendar: linked is a link")
        _winapi.CreateJunction(str(root), str(root.parent / "alias"))
        _refused(lambda: rules.calendar_sha256(root.parent / "alias"), "is not a plain directory")
    finally:
        for link in (root / "linked", root.parent / "alias"):
            if link.is_junction():
                link.rmdir()                                            # removes the junction, not its target
        shutil.rmtree(root.parent, ignore_errors=True)
