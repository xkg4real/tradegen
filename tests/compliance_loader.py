"""Strict YAML loader, vocabulary and class derivation (compliance plan Task 3; spec 5.1, 5.2 "Loading", 8.1, 8.4)."""
from __future__ import annotations

from datetime import date

from core.compliance import rules


def _invalid(text, has: str) -> str:
    """Asserts load_strict refuses `text` (str or bytes) with a reason containing `has`; returns the reason."""
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    try:
        rules.load_strict(raw, "t")
    except rules.Invalid as exc:
        assert str(exc) == exc.reason and exc.reason.startswith("t: "), exc.reason
        assert has in exc.reason, (has, exc.reason)
        return exc.reason
    raise AssertionError(f"accepted {raw[:60]!r}; expected Invalid containing {has!r}")


def test_duplicate_keys_invalid():
    _invalid("a: 1\na: 2\n", "duplicate key 'a'")
    _invalid("m:\n  k: 1\n  k: 2\n", "duplicate key 'k'")
    _invalid("rows:\n  - {id: X, id: Y}\n", "duplicate key 'id'")
    _invalid("1: a\n1: b\n", "duplicate key 1")


def test_anchor_and_alias_invalid():
    _invalid("a: &x 1\nb: 2\n", "anchor &x")
    _invalid("a: &x {k: 1}\nb: 2\n", "anchor &x")
    _invalid("a: &x [1]\n", "anchor &x")
    _invalid("b: *x\n", "alias *x")
    _invalid("a: 1\nb: [*x]\n", "alias *x")


def test_explicit_tags_invalid():
    for text in ("a: !!str 1\n", "d: !!timestamp 2026-10-23\n", "s: !!set {a: null}\n", "b: !!binary aGk=\n",
                 "f: !!float .nan\n", "m: !!map {}\n", "x: ! plain\n"):
        _invalid(text, "explicit tag")


def test_unquoted_dates_invalid():
    for text in ("d: 2026-10-23\n", "t: 2026-10-23T09:00:00Z\n", "l: [2026-10-23]\n", "2026-10-23: x\n"):
        _invalid(text, "native date")


def test_yaml11_ambiguous_scalars_invalid():
    for value, kind in ((".nan", "float"), (".inf", "float"), ("-.inf", "float"), ("15:30", "int"),
                        ("0x1F", "int"), ("010", "int"), ("0b11", "int"), ("1_000", "int"), ("yes", "bool"),
                        ("no", "bool"), ("on", "bool"), ("Off", "bool"), ("True", "bool"), ("FALSE", "bool"),
                        ("NULL", "null"), ("Null", "null"), (".5", "float"), ("<<", "merge"), ("=", "value")):
        _invalid(f"v: {value}\n", f"reads as a YAML 1.1 {kind}")


def test_bom_and_encoding_invalid():
    _invalid(b"\xef\xbb\xbfa: 1\n", "UTF-8 BOM")
    _invalid(b"a: \xff\n", "not UTF-8")
    _invalid("a: 1\n".encode("utf-16"), "not UTF-8")
    _invalid("a: \ud55c\uad6d\n".encode("cp949"), "not UTF-8")


def test_size_cap():
    _invalid(b"a: " + b"x" * rules.MAX_TABLE_BYTES, "larger than 256 KB")
    _invalid(b"a: " + b"x" * (rules.MAX_TABLE_BYTES - 3) + b"\n", "larger than 256 KB")      # one byte over
    exact = b"a: " + b"x" * (rules.MAX_TABLE_BYTES - 4) + b"\n"
    assert len(exact) == rules.MAX_TABLE_BYTES == 262144
    assert rules.load_strict(exact, "t") == {"a": "x" * (rules.MAX_TABLE_BYTES - 4)}


def test_top_level_must_be_a_mapping():
    for text in ("", "# only a comment\n", "- 1\n- 2\n", "just text\n", "42\n", "null\n"):
        _invalid(text, "the top level must be a mapping")
    _invalid("a: 1\n---\nb: 2\n", "not YAML")


def test_other_refusals():
    _invalid("? [1, 2]\n: v\n", "a mapping key must be a scalar")
    _invalid("f: 1.0e400\n", "is not a finite number")
    _invalid("a: [1\n", "not YAML")
    _invalid("a: b: c\n", "not YAML")
    _invalid("a: \x00\n", "not YAML")
    _invalid("a: " + "[" * 30000 + "]" * 30000 + "\n", "unreadable (RecursionError)")
    _invalid("a: 1\nn: " + "9" * 19 + "\n", "line 2: an int has more than 18 digits")        # P28
    _invalid("n: -" + "9" * 5000 + "\n", "an int has more than 18 digits")      # not int_max_str_digits
    _invalid("1234567890123456789: x\n", "an int has more than 18 digits")
    assert rules.load_strict(b"n: -999999999999999999\nm: +999999999999999999\n", "t") == {
        "n": -999999999999999999, "m": 999999999999999999}
    try:
        rules.load_strict("a: 1\n", "t")
    except rules.Invalid as exc:
        assert exc.reason == "t: expected bytes, got str", exc.reason
    else:
        raise AssertionError("a str was accepted")


def test_plain_scalars_load_as_expected():
    doc = rules.load_strict((
        'q: "2026-10-23"\nq2: \'2026-10-23\'\ni: 42\nneg: -7\nplus: +3\nzero: 0\nf: 1.5\ng: -0.25\n'
        'e: 1.5e+3\ne2: 2e3\ndot: 1.\nt: true\nfa: false\nnu: null\nti: ~\nem:\ns: plain text\n'
        'code: 005930\noct: 0o17\nqyes: "yes"\nlst: [1, 2.0, "x", null]\nmap: {k: v}\n'
        'url: https://www.fsc.go.kr/no010101/87177\nhangul: \ud55c\uad6d\n').encode("utf-8"), "t")
    assert doc == {"q": "2026-10-23", "q2": "2026-10-23", "i": 42, "neg": -7, "plus": 3, "zero": 0, "f": 1.5,
                   "g": -0.25, "e": 1500.0, "e2": 2000.0, "dot": 1.0, "t": True, "fa": False, "nu": None,
                   "ti": None, "em": None, "s": "plain text", "code": "005930", "oct": "0o17", "qyes": "yes",
                   "lst": [1, 2.0, "x", None], "map": {"k": "v"}, "url": "https://www.fsc.go.kr/no010101/87177",
                   "hangul": "\ud55c\uad6d"}, doc
    assert type(doc["i"]) is int and type(doc["f"]) is float and type(doc["e2"]) is float
    assert doc["t"] is True and doc["fa"] is False and type(doc["q"]) is str


def test_parse_date():
    assert rules.parse_date("2026-10-23", "f") == date(2026, 10, 23)
    assert rules.parse_date("2028-02-29", "f") == date(2028, 2, 29)
    for bad in ("2026-10-23T00:00:00", "20261023", "2026-W43-5", "2026-02-30", "2026-1-5", " 2026-10-23",
                "\uff12026-10-23", 20261023, None, True, date(2026, 10, 23), ["2026-10-23"]):
        try:
            rules.parse_date(bad, "f")
        except rules.Invalid as exc:
            assert exc.reason.startswith("f: "), exc.reason
        else:
            raise AssertionError(f"parse_date accepted {bad!r}")


def test_derive_class_spec_rules():
    cases = (
        ("us_etp", 3, "index", "etp_leveraged"),                  # TQQQ, rule 4
        ("krx_etp", -2, "index", "etp_leveraged"),                # 252670 (a 2x inverse), rule 4
        ("us_etp", -1, "index", "etp_index_inverse"),             # SH, rule 3
        ("krx_etp", -1, "index", "etp_index_inverse"),            # 114800, rule 3
        ("krx_etp", -1, "basket", "etp_index_inverse"),           # rule 3
        ("us_etp", 2, "basket", "etp_leveraged"),                 # rule 4
        ("us_etp", -1, "single", "etp_single_stock"),             # a single-stock -1x, rule 2
        ("krx_etp", 2, "single", "etp_single_stock"),             # rule 2
        ("us_etp", 1, "crypto_spot", "etp_crypto_spot"),          # IBIT, rule 1
        ("us_etp", 1, "crypto_spot_basket", "etp_crypto_spot"),   # GDLC / EZPZ, rule 1
        ("us_etp", -1, "crypto_spot", "etp_crypto_spot"),         # rule 1 comes first
        ("us_etp", 2, "crypto_spot_basket", "etp_crypto_spot"),
        ("us_etp", 1, "crypto_futures", "etp_crypto_futures_1x"), # BITO, rule 5
        ("us_etp", 1, "index", "etp_1x"),                         # SPY, rule 6
        ("krx_etp", 1, "index", "etp_1x"),                        # 069500, rule 6
        ("us_etp", 1, "basket", "etp_1x"),
        ("us_etp", 1, "single", "etp_1x"),
        ("us_etp", 3.0, "index", "etp_leveraged"),
        ("us_etp", 1.0, "index", "etp_1x"),
        ("krx_share", 1, None, "share"),                          # rule 7
        ("us_share", 1, None, "share"),
        ("crypto_coin", 1, None, "coin"),
        ("crypto_coin", 1.0, None, "coin"),
        ("us_option", 1, None, "option"),
        ("konex_share", 1, None, "konex_share"),
    )
    for asset, multiple, underlying, want in cases:
        got = rules.derive_class(asset, multiple, underlying)
        assert got == want, (asset, multiple, underlying, got, want)
    for asset, cls in rules.ASSET_CLASS.items():
        assert rules.derive_class(asset, 1, None) == cls, asset


def test_derive_class_refuses():
    for asset, multiple, underlying in (
            ("us_etp", -1, "crypto_futures"),         # P11: an inverse bitcoin-futures ETP fits no class
            ("us_etp", 2, "crypto_futures"),          # P11
            ("us_etp", 1, None),                      # an ETP with no underlying
            ("krx_etp", -2, None),
            ("us_etp", 1, "commodity"),               # unknown underlying
            ("us_share", 1, "index"),                 # a non-ETP with an underlying
            ("crypto_coin", 1, "crypto_spot"),
            ("krx_share", -1, None),                  # P29: a non-ETP is always x1
            ("crypto_coin", 3, None),
            ("us_share", 1.5, None),
            ("bond", 1, None),                        # unknown asset
            ("US_ETP", 1, "index"),                   # case variant
            ("us_etp", 0, "index"),                   # P29
            ("us_etp", float("nan"), "index"),
            ("us_etp", float("inf"), "index"),
            ("us_etp", 10 ** 400, "index"),           # beyond float range: Invalid, not OverflowError
            ("krx_share", -10 ** 400, None),
            ("us_etp", True, "index"),
            ("us_etp", "3", "index"),
            ("us_etp", None, "index"),
            (None, 1, None),
            (["us_etp"], 1, "index"),
            ("us_etp", 1, ["index"])):
        try:
            got = rules.derive_class(asset, multiple, underlying)
        except rules.Invalid as exc:
            assert exc.reason.endswith("fits no class"), exc.reason
        else:
            raise AssertionError(f"{asset} x{multiple} on {underlying} derived {got}")


def test_derive_class_total_and_exclusive():
    reached = set(rules.ASSET_CLASS.values())
    for asset in sorted(rules.ETP_ASSETS):
        for underlying in sorted(rules.UNDERLYINGS):
            for multiple in (-3, -2, -1, -0.5, 0.5, 1, 2, 3):
                fits = not (underlying == "crypto_futures" and multiple != 1)
                try:
                    cls = rules.derive_class(asset, multiple, underlying)
                except rules.Invalid:
                    assert not fits, (asset, multiple, underlying)
                else:
                    assert fits and cls in rules.CLASSES, (asset, multiple, underlying, cls)
                    reached.add(cls)
    assert reached == rules.CLASSES, sorted(rules.CLASSES - reached)


def test_vocabulary_is_consistent():
    """Every constant is exactly contract 6.1, type included; then the invariants that tie them together."""
    assert rules.VENUES == {"kis", "upbit", "bithumb", "coinone", "korbit", "gopax", "okx", "binance", "bybit",
                            "bitget", "hyperliquid", "pumpfun", "jupiter", "uniswap", "drift", "polymarket", "kalshi",
                            "limitless", "myriad", "opinion", "predictfun", "robinhood", "cryptocom", "predictit",
                            "sportsbook", "betman", "lotto", "speedon", "ibkr", "moomoo", "webull", "etoro",
                            "offshore_fx_cfd", "kucoin", "mexc", "phemex", "xtcom", "bitrue", "coinw", "poloniex",
                            "btcc", "bingx", "digifinex", "bitmart"}
    assert rules.DOMESTIC_EXCHANGES == ("upbit", "bithumb", "coinone", "korbit")
    assert rules.STATE_BLOCKED == ("kucoin", "mexc", "phemex", "xtcom", "bitrue", "coinw", "poloniex", "btcc", "bingx",
                                   "digifinex")
    assert rules.PREDICTION_VENUES == ("polymarket", "kalshi", "limitless", "myriad", "opinion", "predictfun",
                                       "robinhood", "cryptocom", "predictit")
    assert rules.ASSETS == {"krx_share", "konex_share", "krx_etp", "krx_derivative", "elw", "us_share", "us_etp",
                            "us_option", "overseas_future", "overseas_crypto_derivative", "crypto_coin",
                            "crypto_perp_or_future", "fx_pair", "cfd", "event_contract", "sports_bet", "lottery"}
    assert rules.ETP_ASSETS == {"krx_etp", "us_etp"}
    assert rules.UNDERLYINGS == {"single", "index", "basket", "crypto_spot", "crypto_spot_basket", "crypto_futures"}
    assert rules.CLASSES == {"etp_crypto_spot", "etp_single_stock", "etp_index_inverse", "etp_leveraged",
                             "etp_crypto_futures_1x", "etp_1x", "share", "konex_share", "coin", "option",
                             "krx_derivative", "elw", "overseas_future", "overseas_crypto_derivative",
                             "crypto_perp_or_future", "fx_pair", "cfd", "event_contract", "sports_bet", "lottery"}
    assert rules.ASSET_CLASS == {"krx_share": "share", "us_share": "share", "konex_share": "konex_share",
                                 "crypto_coin": "coin", "us_option": "option", "krx_derivative": "krx_derivative",
                                 "elw": "elw", "overseas_future": "overseas_future",
                                 "overseas_crypto_derivative": "overseas_crypto_derivative",
                                 "crypto_perp_or_future": "crypto_perp_or_future", "fx_pair": "fx_pair",
                                 "cfd": "cfd", "event_contract": "event_contract", "sports_bet": "sports_bet",
                                 "lottery": "lottery"}
    assert rules.ACTIONS == {"buy", "sell", "sell_short", "buy_to_cover", "write", "transfer_out", "lend", "borrow",
                             "p2p_buy", "p2p_sell"}
    assert rules.TRADE_ACTIONS == {"buy", "sell", "sell_short", "buy_to_cover", "write", "p2p_buy", "p2p_sell"}
    assert rules.FINANCING == {"cash", "credit", "margin"}
    assert rules.TAGS == {"copy_lead", "copy_follow", "fx_settlement", "unregistered_vasp_referral", "coordinated",
                          "self_match", "spoof", "layer", "mnpi", "false_statement", "self_issued_coin"}
    assert rules.WHEN == {"route_not_direct", "on_behalf_not_self", "publishes_signal"}
    assert rules.TREATMENTS == {"hard_block", "gated", "grey", "allow", "out_of_scope"}
    assert rules.BASIS == {"legal", "policy", "platform"}                                            # P13
    assert rules.CONFIDENCE == {"high", "medium", "low"}
    assert rules.ACK_KINDS == {"per_session", "per_transfer"}
    assert rules.OWNER_REQUIREMENTS == {"age_of_majority", "kofia_leveraged_1h", "kofia_single_stock_3h",
                                        "krx_mock_5h_5days", "kofia_derivatives_1h", "krx_derivatives_mock_3h",
                                        "elw_course", "us_option_course_1h", "us_option_mock_3h", "short_course_30m",
                                        "short_mock_1h", "broker_eligibility"}
    assert rules.LIVE_REQUIREMENTS == {"deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m", "cash_krw_30m",
                                       "broker_approval", "collateral_105pct"}
    assert rules.SECTIONS == ("krx", "us", "crypto")
    assert rules.TAX_BASES == {"krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027",
                               "unsupported"}
    assert rules.COST_BOOKS == {"KRX_stock_book", "KRX_ETF_line", "US_shares_KIS", "crypto_venue"}
    assert rules.KNOWN_SPOT_CRYPTO_ETPS == {"IBIT", "FBTC", "ARKB", "ETHA", "GDLC", "EZPZ"}           # P10
    assert rules.MAX_TABLE_BYTES == 262144 and rules.WARNING_SLOTS == {"cap"}
    for name in ("VENUES", "ASSETS", "ETP_ASSETS", "UNDERLYINGS", "CLASSES", "ACTIONS", "TRADE_ACTIONS", "FINANCING",
                 "TAGS", "WHEN", "TREATMENTS", "BASIS", "CONFIDENCE", "ACK_KINDS", "OWNER_REQUIREMENTS",
                 "LIVE_REQUIREMENTS", "TAX_BASES", "COST_BOOKS", "KNOWN_SPOT_CRYPTO_ETPS", "WARNING_SLOTS"):
        assert type(getattr(rules, name)) is frozenset, name
    assert type(rules.ASSET_CLASS) is dict
    assert set(rules.DOMESTIC_EXCHANGES) | set(rules.STATE_BLOCKED) | set(rules.PREDICTION_VENUES) <= rules.VENUES
    assert "bitmart" not in rules.STATE_BLOCKED and all(v == v.lower() for v in rules.VENUES)        # P23
    assert set(rules.ASSET_CLASS) | rules.ETP_ASSETS == rules.ASSETS
    assert not set(rules.ASSET_CLASS) & rules.ETP_ASSETS
    assert set(rules.ASSET_CLASS.values()) <= rules.CLASSES
    assert rules.TRADE_ACTIONS <= rules.ACTIONS
    assert rules.ACTIONS - rules.TRADE_ACTIONS == {"transfer_out", "lend", "borrow"}
    assert not rules.OWNER_REQUIREMENTS & rules.LIVE_REQUIREMENTS
    words = (rules.VENUES | rules.ASSETS | rules.UNDERLYINGS | rules.CLASSES | rules.ACTIONS | rules.FINANCING
             | rules.TAGS | rules.WHEN | rules.TREATMENTS)
    assert "any" not in words                  # "any" is the match wildcard, never a vocabulary member
