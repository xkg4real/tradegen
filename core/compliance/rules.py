"""Compliance rules data: the closed vocabulary, the strict YAML loader and the class derivation (spec 5.1, 5.2
"Loading"). Pure: no clock, no network, no writes; a doubt about a file is `Invalid`, never a guess."""
from __future__ import annotations

import codecs
import math
import re
from datetime import date

import yaml

# --------------------------------------------------------------------------- #
# Vocabulary (spec 5.1; contract 6.1). Every id an intent or a row names must be an exact member.
# --------------------------------------------------------------------------- #
VENUES = frozenset({"kis", "upbit", "bithumb", "coinone", "korbit", "gopax", "okx", "binance", "bybit", "bitget",
    "hyperliquid", "pumpfun", "jupiter", "uniswap", "drift", "polymarket", "kalshi", "limitless", "myriad", "opinion",
    "predictfun", "robinhood", "cryptocom", "predictit", "sportsbook", "betman", "lotto", "speedon", "ibkr", "moomoo",
    "webull", "etoro", "offshore_fx_cfd", "kucoin", "mexc", "phemex", "xtcom", "bitrue", "coinw", "poloniex", "btcc",
    "bingx", "digifinex", "bitmart"})
DOMESTIC_EXCHANGES = ("upbit", "bithumb", "coinone", "korbit")
STATE_BLOCKED = ("kucoin", "mexc", "phemex", "xtcom", "bitrue", "coinw", "poloniex", "btcc", "bingx", "digifinex")
PREDICTION_VENUES = ("polymarket", "kalshi", "limitless", "myriad", "opinion", "predictfun", "robinhood",
                     "cryptocom", "predictit")
ASSETS = frozenset({"krx_share", "konex_share", "krx_etp", "krx_derivative", "elw", "us_share", "us_etp",
    "us_option", "overseas_future", "overseas_crypto_derivative", "crypto_coin", "crypto_perp_or_future", "fx_pair",
    "cfd", "event_contract", "sports_bet", "lottery"})
ETP_ASSETS = frozenset({"krx_etp", "us_etp"})
UNDERLYINGS = frozenset({"single", "index", "basket", "crypto_spot", "crypto_spot_basket", "crypto_futures"})
CLASSES = frozenset({"etp_crypto_spot", "etp_single_stock", "etp_index_inverse", "etp_leveraged",
    "etp_crypto_futures_1x", "etp_1x", "share", "konex_share", "coin", "option", "krx_derivative", "elw",
    "overseas_future", "overseas_crypto_derivative", "crypto_perp_or_future", "fx_pair", "cfd", "event_contract",
    "sports_bet", "lottery"})
ASSET_CLASS = {"krx_share": "share", "us_share": "share", "konex_share": "konex_share", "crypto_coin": "coin",
    "us_option": "option", "krx_derivative": "krx_derivative", "elw": "elw", "overseas_future": "overseas_future",
    "overseas_crypto_derivative": "overseas_crypto_derivative", "crypto_perp_or_future": "crypto_perp_or_future",
    "fx_pair": "fx_pair", "cfd": "cfd", "event_contract": "event_contract", "sports_bet": "sports_bet",
    "lottery": "lottery"}                            # ETP assets go through derive_class
ACTIONS = frozenset({"buy", "sell", "sell_short", "buy_to_cover", "write", "transfer_out", "lend", "borrow",
                     "p2p_buy", "p2p_sell"})
TRADE_ACTIONS = frozenset({"buy", "sell", "sell_short", "buy_to_cover", "write", "p2p_buy", "p2p_sell"})
FINANCING = frozenset({"cash", "credit", "margin"})
TAGS = frozenset({"copy_lead", "copy_follow", "fx_settlement", "unregistered_vasp_referral", "coordinated",
                  "self_match", "spoof", "layer", "mnpi", "false_statement", "self_issued_coin"})
WHEN = frozenset({"route_not_direct", "on_behalf_not_self", "publishes_signal"})
TREATMENTS = frozenset({"hard_block", "gated", "grey", "allow", "out_of_scope"})
BASIS = frozenset({"legal", "policy", "platform"})                          # P13
CONFIDENCE = frozenset({"high", "medium", "low"})
ACK_KINDS = frozenset({"per_session", "per_transfer"})
OWNER_REQUIREMENTS = frozenset({"age_of_majority", "kofia_leveraged_1h", "kofia_single_stock_3h",
    "krx_mock_5h_5days", "kofia_derivatives_1h", "krx_derivatives_mock_3h", "elw_course", "us_option_course_1h",
    "us_option_mock_3h", "short_course_30m", "short_mock_1h", "broker_eligibility"})
LIVE_REQUIREMENTS = frozenset({"deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m", "cash_krw_30m",
    "broker_approval", "collateral_105pct"})
SECTIONS = ("krx", "us", "crypto")
TAX_BASES = frozenset({"krx_small_holder_exempt", "overseas_22pct_over_2.5m", "crypto_22pct_from_2027",
                       "unsupported"})
COST_BOOKS = frozenset({"KRX_stock_book", "KRX_ETF_line", "US_shares_KIS", "crypto_venue"})   # subset of
                                    # core.quant.instruments.INSTRUMENT_BOOKS; a test (not core) checks that
KNOWN_SPOT_CRYPTO_ETPS = frozenset({"IBIT", "FBTC", "ARKB", "ETHA", "GDLC", "EZPZ"})        # P10
MAX_TABLE_BYTES = 256 * 1024
WARNING_SLOTS = frozenset({"cap"})                  # the only {slot} a warning may contain


class Invalid(Exception):
    """A rules table, instrument map or venue file the gate must not use; `.reason` (== str(exc)) says why."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# --------------------------------------------------------------------------- #
# Strict loader (spec 5.2 "Loading"; P28)
# --------------------------------------------------------------------------- #
_STR = "tag:yaml.org,2002:str"
_STOCK = yaml.resolver.Resolver()      # PyYAML's YAML 1.1 rules, only to spot plain scalars that read two ways


class _Loader(yaml.SafeLoader):
    """Pure-Python SafeLoader with a closed scalar schema (bool true|false, decimal int of at most 18 digits, decimal
    float, null). Refuses anchors, aliases, explicit tags, duplicate or non-scalar keys, and every plain scalar that
    YAML 1.1 reads as a date, bool, number or null while this loader would read a string (`yes`, `15:30`, `.nan`)."""
    yaml_implicit_resolvers: dict = {}
    what = "yaml"

    def compose_node(self, parent, index):
        event = self.peek_event()
        line = event.start_mark.line + 1
        if isinstance(event, yaml.AliasEvent):
            raise Invalid(f"{self.what}: line {line}: alias *{event.anchor}")
        if event.anchor is not None:
            raise Invalid(f"{self.what}: line {line}: anchor &{event.anchor}")
        if event.tag is not None:
            raise Invalid(f"{self.what}: line {line}: explicit tag {event.tag}")
        return super().compose_node(parent, index)

    def resolve(self, kind, value, implicit):
        tag = super().resolve(kind, value, implicit)
        if kind is yaml.ScalarNode and implicit[0] and tag == _STR:
            stock = _STOCK.resolve(kind, value, implicit).rsplit(":", 1)[-1]
            if stock == "timestamp":
                raise Invalid(f"{self.what}: native date {value!r}; quote every date")
            if stock != "str":
                raise Invalid(f"{self.what}: {value!r} reads as a YAML 1.1 {stock}; quote it")
        return tag

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            line = key_node.start_mark.line + 1
            if not isinstance(key_node, yaml.ScalarNode):
                raise Invalid(f"{self.what}: line {line}: a mapping key must be a scalar")
            key = self.construct_object(key_node)
            if key in seen:
                raise Invalid(f"{self.what}: line {line}: duplicate key {key!r}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _finite_float(loader: _Loader, node) -> float:
    value = float(node.value)
    if not math.isfinite(value):
        raise Invalid(f"{loader.what}: {node.value!r} is not a finite number")
    return value


def _small_int(loader: _Loader, node) -> int:
    # The schema bounds an int, not the interpreter's int_max_str_digits setting.
    if len(node.value.lstrip("+-")) > 18:
        raise Invalid(f"{loader.what}: line {node.start_mark.line + 1}: an int has more than 18 digits")
    return int(node.value)


# No leading zeros: `005930` stays the string it is in YAML 1.1, and `010` (octal 8 in 1.1) is refused above.
for _tag, _pattern, _first in (
        ("bool", r"true|false", "tf"),
        ("int", r"[-+]?(?:0|[1-9][0-9]*)", "-+0123456789"),
        ("float", r"[-+]?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?", "-+0123456789"),
        ("null", r"null|~|", ("n", "~", ""))):
    _Loader.add_implicit_resolver(f"tag:yaml.org,2002:{_tag}", re.compile(rf"(?:{_pattern})\Z"), list(_first))
_Loader.add_constructor("tag:yaml.org,2002:float", _finite_float)
_Loader.add_constructor("tag:yaml.org,2002:int", _small_int)
del _tag, _pattern, _first


def load_strict(raw: bytes, what: str) -> dict:
    """One owner-approved YAML file -> its top-level mapping. Over 256 KB, a BOM, non-UTF-8 bytes, any YAML error
    or a top level that is not a mapping is Invalid, as is everything `_Loader` refuses."""
    if not isinstance(raw, (bytes, bytearray)):
        raise Invalid(f"{what}: expected bytes, got {type(raw).__name__}")
    if len(raw) > MAX_TABLE_BYTES:
        raise Invalid(f"{what}: larger than 256 KB")
    if raw.startswith(codecs.BOM_UTF8):
        raise Invalid(f"{what}: starts with a UTF-8 BOM")
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Invalid(f"{what}: not UTF-8 (byte {exc.start})") from None
    try:
        loader = _Loader(text)                       # the reader refuses control characters here
        loader.what = what
        try:
            doc = loader.get_single_data()
        finally:
            loader.dispose()
    except yaml.YAMLError as exc:
        raise Invalid(f"{what}: not YAML: {' '.join(str(exc).split())}") from None
    except RecursionError:
        raise Invalid(f"{what}: unreadable (RecursionError): nested too deep") from None
    if not isinstance(doc, dict):
        raise Invalid(f"{what}: the top level must be a mapping")
    return doc


_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def parse_date(value, what: str) -> date:
    """A quoted "YYYY-MM-DD" -> date; any other value (a week date, a compact date, a non-string) is Invalid."""
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise Invalid(f"{what}: expected a quoted YYYY-MM-DD date, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Invalid(f"{what}: {value!r} is not a calendar date") from None


# --------------------------------------------------------------------------- #
# Derived class (spec 5.1 rules 1-7; P11, P29)
# --------------------------------------------------------------------------- #
def derive_class(asset: str, multiple: float, underlying: str | None) -> str:
    """The `class` match key of a map entry, by the first spec 5.1 rule that applies. P11: the inverse and
    leveraged rules (3, 4) skip crypto_futures. P29: a non-ETP is always x1 with no underlying; an unknown asset or
    underlying, an ETP without an underlying, or a zero, bool, non-numeric or out-of-range multiple fits no class."""
    ok = (isinstance(asset, str) and (underlying is None or isinstance(underlying, str))
          and isinstance(multiple, (int, float)) and not isinstance(multiple, bool)
          and -1e6 < multiple < 1e6 and multiple != 0)       # exact int/float compare: refuses NaN, inf, huge ints
    if ok and asset in ETP_ASSETS:
        plain = underlying in ("index", "basket")
        if underlying in ("crypto_spot", "crypto_spot_basket"):
            return "etp_crypto_spot"                                           # rule 1
        if underlying == "single" and multiple != 1:
            return "etp_single_stock"                                          # rule 2
        if plain and multiple == -1:
            return "etp_index_inverse"                                         # rule 3
        if plain and multiple != 1:
            return "etp_leveraged"                                             # rule 4
        if underlying == "crypto_futures" and multiple == 1:
            return "etp_crypto_futures_1x"                                     # rule 5
        if underlying in ("single", "index", "basket"):
            return "etp_1x"                                                    # rule 6 (multiple is +1 here)
    elif ok and asset in ASSET_CLASS and underlying is None and multiple == 1:
        return ASSET_CLASS[asset]                                              # rule 7 (a non-ETP is always x1)
    raise Invalid(f"{asset} x{multiple} on {underlying} fits no class")
