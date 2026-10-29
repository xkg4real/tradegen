"""Compliance rules data: the closed vocabulary, the strict YAML loader, the class derivation, and the parsers of
the rules table, the instrument map and the venue facts with their hashes and the approved state (spec 5.1, 5.2),
plus the `--check` CLI (spec 5.4). No network. The data functions take no clock and write nothing, and `calendar_stream`
(and `calendar_sha256` through it) is the only file reader among them. check() also reads the repo drafts and writes
nothing itself (the only write is load_context's snapshot of a valid state); only main() reads the clock. A doubt
about a file is `Invalid`, never a guess."""
from __future__ import annotations

import codecs
import hashlib
import math
import os
import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from core.compliance.model import ApprovedState

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


# --------------------------------------------------------------------------- #
# Typed tables (contract 6.3)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, kw_only=True)
class Review:
    date: date
    by: str
    checked: str


@dataclass(frozen=True, kw_only=True)
class Row:
    id: str
    kind: str                                            # "venue" | "conduct"
    match: Mapping[str, frozenset]                       # keys from P12; values are vocabulary members or {"any"}
    treatment: str
    requires_owner: tuple[str, ...] = ()
    requires_live: tuple[str, ...] = ()
    ack: str | None = None
    cap_key: str | None = None
    auto_off: date | None = None
    max_leverage: float = 1.0                            # P4
    warning: str = ""
    reason: str
    basis: frozenset
    policy_ref: str | None = None
    sources: tuple[str, ...]
    research: tuple[str, ...]
    matrix_rows: tuple[int, ...] = ()                    # P14
    confidence: str
    effective_from: date                                 # P16
    effective_until: date | None = None
    review_by: date
    reviews: tuple[Review, ...]
    affected_by: tuple[date, ...] = ()                   # P15


@dataclass(frozen=True, kw_only=True)
class RulesTable:
    schema: str
    scope: str
    known_changes: tuple[date, ...]
    rows: tuple[Row, ...]


@dataclass(frozen=True, kw_only=True)
class Instrument:
    section: str
    symbol: str
    asset: str
    multiple: float
    underlying: str | None
    cls: str                                             # derived, and equal to the declared `class` (P10)
    cost_book: str | None
    currency: str
    tax_basis: str
    source: str


@dataclass(frozen=True, kw_only=True)
class InstrumentMap:
    entries: Mapping[tuple[str, str], Instrument]        # (section, symbol) -> Instrument

    def lookup(self, sections: tuple[str, ...], symbol: str) -> Instrument | None:
        """The entry for `symbol` in the first of `sections` that lists it (P9 makes that unique per venue)."""
        if not isinstance(symbol, str):
            return None
        for section in sections:
            inst = self.entries.get((section, symbol))
            if inst is not None:
                return inst
        return None


@dataclass(frozen=True, kw_only=True)
class Venue:
    id: str
    sections: tuple[str, ...]
    settlement: frozenset
    markets: frozenset                                   # {(base, quote)}; empty when quote_by_currency
    quote_by_currency: bool = False                      # kis: the counter must equal the instrument's currency
    default_quote: str | None = None                     # used by screen(); None when quote_by_currency
    deposits: frozenset = frozenset()                    # {(symbol, network, tag_required: bool)}
    # The odds keys (odds plan Q17), sorted and hashable; () or None where venues.yaml leaves a key out, which makes
    # that leg not tradable (O11). Every number is a float.
    lot: tuple[tuple[str, float], ...] = ()              # (symbol or "default", units step > 0)
    min_order: tuple[tuple[str, float], ...] = ()        # (settlement asset, minimum >= 0 in quote units)
    fee_extras: tuple[float, float] | None = None        # (phi_buy, phi_sell): fixed KRW charges per fill, each >= 0
    tick_ladder: tuple[tuple[str, str, tuple[tuple[float, float], ...]], ...] = ()
    #               (cost book, effective_from "YYYY-MM-DD", ((price_from, tick), ...)) in the book's quote currency
    odds_sources: tuple[tuple[str, str], ...] = ()       # (odds key, its source) for each odds key present

    def is_market(self, inst: Instrument, counter: str) -> bool:
        """(inst, counter) is a listed market of this venue."""
        if not isinstance(counter, str) or inst.section not in self.sections:
            return False
        if self.quote_by_currency:
            return counter == inst.currency and counter in self.settlement
        return (inst.symbol, counter) in self.markets

    def quote_for(self, inst: Instrument) -> str:
        """What a buy of `inst` pays with here: its currency, or the venue's default quote."""
        return inst.currency if self.quote_by_currency else self.default_quote

    # The odds lookups are plain tuple reads: the gate's purity tests scan every Venue method (no date, file or clock
    # name here, and no local name that is a module-level def of this file).
    def lot_for(self, symbol: str) -> float | None:
        """The lot step of `symbol` here: its own entry, else the venue's "default", else None (not tradable)."""
        if not isinstance(symbol, str):
            return None
        steps = dict(self.lot)
        return steps.get(symbol, steps.get("default"))

    def min_order_for(self, quote: str) -> float | None:
        """The smallest order paid in `quote` (a settlement asset), in `quote` units, or None (not tradable)."""
        if not isinstance(quote, str):
            return None
        return dict(self.min_order).get(quote)

    def ladder_for(self, book: str) -> tuple[str, tuple[tuple[float, float], ...]] | None:
        """(effective_from "YYYY-MM-DD", ((price_from, tick), ...)) of the signed ladder of cost `book`, or None."""
        for name, start, rows in self.tick_ladder:
            if name == book:
                return start, rows
        return None


@dataclass(frozen=True, kw_only=True)
class VenueFacts:
    venues: Mapping[str, Venue]


# --------------------------------------------------------------------------- #
# Field checks shared by the three parsers; every message names the file, the row or entry, and the field.
# --------------------------------------------------------------------------- #
def _keys(doc, where: str, required: frozenset, optional: frozenset = frozenset()) -> None:
    if not isinstance(doc, dict):
        raise Invalid(f"{where}: expected a mapping")
    unknown = sorted(str(k) for k in set(doc) - required - optional)
    if unknown:
        raise Invalid(f"{where}: unknown key(s) {unknown}")
    missing = sorted(required - set(doc))
    if missing:
        raise Invalid(f"{where}: missing key(s) {missing}")


def _text(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Invalid(f"{where}: expected a non-empty string")
    return value


def _member(value, where: str, vocab) -> str:
    if not isinstance(value, str) or value not in vocab:
        raise Invalid(f"{where}: {value!r} is not one of {sorted(vocab)}")
    return value


def _strs(value, where: str, vocab=None, *, empty: bool = False) -> tuple[str, ...]:
    """A YAML list of distinct non-empty strings (members of `vocab` when given); null is () when `empty`."""
    if value is None and empty:
        return ()
    if not isinstance(value, list) or not (value or empty):
        raise Invalid(f"{where}: expected a {'' if empty else 'non-empty '}list")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise Invalid(f"{where}: {item!r} is not a non-empty string")
        if vocab is not None and item not in vocab:
            raise Invalid(f"{where}: {item!r} is outside the vocabulary")
    if len(set(value)) != len(value):
        raise Invalid(f"{where}: an item is repeated")
    return tuple(value)


def _positive(value, where: str) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value <= 0):
        raise Invalid(f"{where}: expected a finite number > 0, got {value!r}")
    return float(value)


_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.\-]*")      # exact ids: no case variants of one symbol
_CURRENCY = re.compile(r"[A-Z]{2,10}")
_POLICY = re.compile(r"D[1-9][0-9]*(?:, D[1-9][0-9]*)*")      # owner decisions "D16" or "D15, D16"; no leading 0
_ROW_ID = re.compile(r"[A-Z][A-Z0-9-]{0,63}")       # alerts and reasons quote it; no prose, no newlines


def _symbol(value, where: str) -> str:
    if not isinstance(value, str) or not _SYMBOL.fullmatch(value):
        raise Invalid(f"{where}: {value!r} is not a symbol (quoted A-Z, 0-9, '.' or '-')")
    return value


# --------------------------------------------------------------------------- #
# Rules table (spec 5.2; contract "Row loader rules")
# --------------------------------------------------------------------------- #
_RULES_SCHEMA = "tradegen.kr_rules/4"
_MATCH_VOCAB = {"venue": VENUES, "asset": ASSETS, "class": CLASSES, "action": ACTIONS, "financing": FINANCING,
                "tag": TAGS, "when": WHEN}                                   # P12
_ROW_REQUIRED = frozenset({"id", "kind", "match", "treatment", "reason", "basis", "sources", "research",
                           "confidence", "effective_from", "review_by", "reviews"})
_ROW_OPTIONAL = frozenset({"requires", "ack", "grey", "max_leverage", "warning", "policy_ref", "matrix_rows",
                           "effective_until", "affected_by"})
_BLOCKING = frozenset({"hard_block", "out_of_scope"})      # conduct rows are hard_block, so `any` is legal there
_MAX_REVIEW_DAYS = 31
_MAX_LEVERAGE = 10.0                                       # R2: a typo cannot sign 1e6x
_D15_FINANCING = frozenset({"credit", "margin"})           # D15: no credit buying (margin included, ledger:131)
_D15_ACTIONS = frozenset({"lend", "borrow"})               # D15: no coin lending or borrowing
_D16_ACTIONS = frozenset({"sell_short"})                   # D16 by content (spec:70), whatever policy_ref says
_D16_CLASSES = frozenset({"etp_leveraged", "etp_single_stock", "krx_derivative", "elw"})
_D16_ASSETS = frozenset({"krx_derivative", "elw"})


def _match(value, where: str, treatment: str) -> Mapping[str, frozenset]:
    if not isinstance(value, dict) or not value:
        raise Invalid(f"{where}: expected a non-empty mapping")
    out = {}
    for key, items in value.items():
        if key not in _MATCH_VOCAB:
            raise Invalid(f"{where}: unknown key {key!r}")
        if items == ["any"]:
            if treatment not in _BLOCKING:
                raise Invalid(f"{where}.{key}: any is allowed only on hard_block, out_of_scope and conduct rows")
            out[key] = frozenset({"any"})
        else:
            out[key] = frozenset(_strs(items, f"{where}.{key}", _MATCH_VOCAB[key]))
    return MappingProxyType(out)                       # read-only: approved states are shared and cached


def _warning(value, where: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Invalid(f"{where}: expected a string")
    try:
        parts = list(string.Formatter().parse(value))
    except ValueError as exc:
        raise Invalid(f"{where}: {exc}") from None
    for _, slot, spec, conversion in parts:
        if slot is not None and (slot not in WARNING_SLOTS or spec or conversion):
            raise Invalid(f"{where}: slot {{{slot}}} is not one of {sorted(WARNING_SLOTS)} (plain, no format)")
    return value


def _row(item, index: int, known: tuple[date, ...]) -> Row:
    rid = item.get("id") if isinstance(item, dict) else None
    if not isinstance(rid, str) or not _ROW_ID.fullmatch(rid):
        raise Invalid(f"rules: row {index}: id: expected an upper-case id like KR-OKX-SPOT (A-Z, 0-9, '-'; "
                      "at most 64 characters)")
    where = f"rules: row {rid}"
    _keys(item, where, _ROW_REQUIRED, _ROW_OPTIONAL)
    kind = _member(item["kind"], f"{where}: kind", ("venue", "conduct"))
    treatment = _member(item["treatment"], f"{where}: treatment", TREATMENTS)
    if kind == "conduct" and treatment != "hard_block":
        raise Invalid(f"{where}: treatment: a conduct row is hard_block")
    match = _match(item["match"], f"{where}: match", treatment)
    if kind == "venue" and "venue" not in match:
        raise Invalid(f"{where}: match: a venue row names its venues")
    if treatment not in _BLOCKING:              # a missing key matches everything, so a row that can let an intent
        missing = sorted({"action", "financing"} - set(match)) + ([] if {"class", "asset"} & set(match)
                                                                  else ["class or asset"])   # through names each axis
        if missing:
            raise Invalid(f"{where}: match: an allow, gated or grey row names action, financing and a class or an "
                          f"asset; missing {missing}")
        credit = sorted(match["financing"] & _D15_FINANCING)
        if credit:
            raise Invalid(f"{where}: match.financing: an allow, gated or grey row never matches {credit} (D15: no "
                          "credit buying)")
        lending = sorted(match["action"] & _D15_ACTIONS)
        if lending:
            raise Invalid(f"{where}: match.action: an allow, gated or grey row never matches {lending} (D15: no coin "
                          "lending or borrowing)")
    etp = sorted(match.get("class", frozenset()) - {"any", *ASSET_CLASS.values()})
    if kind == "conduct" and etp:               # gate._conduct shows a conduct row ASSET_CLASS classes only
        raise Invalid(f"{where}: match.class: a conduct row sees an asset's own class, never {etp}")

    requires = {} if item.get("requires") is None else item["requires"]
    _keys(requires, f"{where}: requires", frozenset(), frozenset({"owner", "live"}))
    owner = _strs(requires.get("owner"), f"{where}: requires.owner", OWNER_REQUIREMENTS, empty=True)
    live = _strs(requires.get("live"), f"{where}: requires.live", LIVE_REQUIREMENTS, empty=True)
    ack = item.get("ack")
    if ack is not None:
        _member(ack, f"{where}: ack", ACK_KINDS)
    grey = item.get("grey")
    cap_key = auto_off = None
    if treatment == "grey":
        _keys(grey, f"{where}: grey", frozenset({"cap_key", "auto_off"}))
        cap_key = _text(grey["cap_key"], f"{where}: grey.cap_key")
        auto_off = parse_date(grey["auto_off"], f"{where}: grey.auto_off")
        if ack != "per_session":
            raise Invalid(f"{where}: ack: a grey row needs ack: per_session")
    elif grey is not None:
        raise Invalid(f"{where}: grey: only a grey row carries a cap and an auto-off date")
    warning = _warning(item.get("warning"), f"{where}: warning")
    if ack == "per_session" and not warning.strip():                         # the owner acks its sha256
        raise Invalid(f"{where}: warning: an ack: per_session row needs the warning it acknowledges")
    slots = {slot for _, slot, _, _ in string.Formatter().parse(warning)}
    if treatment == "grey" and "cap" not in slots:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    if treatment != "grey" and "cap" in slots:                               # the cap is a grey row's (ledger:146)
        raise Invalid(f"{where}: warning: only a grey row states a {{cap}}")
    leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")
    if leverage > _MAX_LEVERAGE:
        raise Invalid(f"{where}: max_leverage: at most {_MAX_LEVERAGE:g}, got {leverage!r}")
    policy_ref = item.get("policy_ref")
    if policy_ref is not None:
        if not isinstance(policy_ref, str) or not _POLICY.fullmatch(policy_ref):
            raise Invalid(f"{where}: policy_ref: expected 'D<n>' or 'D<n>, D<n>, ...', got {policy_ref!r}")
        if "D16" in policy_ref.split(", ") and not live:
            raise Invalid(f"{where}: requires.live: a D16 row needs live broker evidence (requires.live)")
        if "D15" in policy_ref.split(", ") and treatment not in _BLOCKING:
            raise Invalid(f"{where}: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and "
                          "lending out)")
    classes = match.get("class", frozenset())
    if "class" not in match and match.get("asset", frozenset()) & ETP_ASSETS:   # no class axis: it matches every
        classes = frozenset({"etp_leveraged", "etp_single_stock"})               # class an ETP derives to
    d16 = sorted((match.get("action", frozenset()) & _D16_ACTIONS) | (classes & _D16_CLASSES)
                 | (match.get("asset", frozenset()) & _D16_ASSETS))
    if treatment not in _BLOCKING and d16 and not live:
        raise Invalid(f"{where}: requires.live: a row matching {d16} needs live broker evidence (D16)")
    if treatment == "gated" and not (owner or live):                         # else it would act as an allow row
        raise Invalid(f"{where}: requires: a gated row requires owner or live evidence")

    matrix = [] if item.get("matrix_rows") is None else item["matrix_rows"]
    if (not isinstance(matrix, list)
            or any(isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 38 for n in matrix)
            or len(set(matrix)) != len(matrix)):
        raise Invalid(f"{where}: matrix_rows: expected distinct ints in 1..38, got {matrix!r}")
    effective_from = parse_date(item["effective_from"], f"{where}: effective_from")
    until = item.get("effective_until")
    effective_until = None if until is None else parse_date(until, f"{where}: effective_until")
    if effective_until is not None and effective_until <= effective_from:
        raise Invalid(f"{where}: effective_until: {effective_until} is not after effective_from {effective_from}")

    reviews_raw = item["reviews"]
    if not isinstance(reviews_raw, list) or not reviews_raw:
        raise Invalid(f"{where}: reviews: expected a non-empty list")
    reviews = []
    for r in reviews_raw:
        _keys(r, f"{where}: reviews", frozenset({"date", "by", "checked"}))
        reviews.append(Review(date=parse_date(r["date"], f"{where}: reviews.date"),
                              by=_text(r["by"], f"{where}: reviews.by"),
                              checked=_text(r["checked"], f"{where}: reviews.checked")))
    affected_raw = item.get("affected_by")
    affected = () if affected_raw is None else tuple(
        parse_date(d, f"{where}: affected_by") for d in _strs(affected_raw, f"{where}: affected_by", empty=True))
    for d in affected:
        if d not in known:
            raise Invalid(f"{where}: affected_by: {d} is not in known_changes")
    review_by = parse_date(item["review_by"], f"{where}: review_by")
    latest = max(r.date for r in reviews)
    if review_by < latest:                                                   # a typo, never a schedule (ledger:103)
        raise Invalid(f"{where}: review_by: {review_by} is before the review of {latest}")
    if (review_by - latest).days > _MAX_REVIEW_DAYS:                         # P15: monthly
        raise Invalid(f"{where}: review_by: {review_by} is more than 31 days after the review of {latest}")
    upcoming = [d for d in affected if d > latest]
    if upcoming and review_by >= min(upcoming):                              # P15: before the change
        raise Invalid(f"{where}: review_by: {review_by} is not before the {min(upcoming)} change")

    return Row(id=rid, kind=kind, match=match, treatment=treatment, requires_owner=owner, requires_live=live,
               ack=ack, cap_key=cap_key, auto_off=auto_off, max_leverage=leverage, warning=warning,
               reason=_text(item["reason"], f"{where}: reason"),
               basis=frozenset(_strs(item["basis"], f"{where}: basis", BASIS)), policy_ref=policy_ref,
               sources=_strs(item["sources"], f"{where}: sources"),
               research=_strs(item["research"], f"{where}: research"),
               matrix_rows=tuple(matrix), confidence=_member(item["confidence"], f"{where}: confidence", CONFIDENCE),
               effective_from=effective_from, effective_until=effective_until, review_by=review_by,
               reviews=tuple(reviews), affected_by=affected)


def parse_rules(raw: bytes) -> RulesTable:
    """kr_rules.yaml bytes -> RulesTable; any schema, vocabulary, cadence or coverage violation is Invalid."""
    doc = load_strict(raw, "rules")
    _keys(doc, "rules", frozenset({"schema", "scope", "known_changes", "rows"}))
    if doc["schema"] != _RULES_SCHEMA:
        raise Invalid(f"rules: schema must be {_RULES_SCHEMA}, got {doc['schema']!r}")
    scope = _text(doc["scope"], "rules: scope")
    known = tuple(parse_date(d, "rules: known_changes")
                  for d in _strs(doc["known_changes"], "rules: known_changes", empty=True))
    if list(known) != sorted(known):
        raise Invalid("rules: known_changes: dates must be in ascending order")
    if not isinstance(doc["rows"], list) or not doc["rows"]:
        raise Invalid("rules: rows: expected a non-empty list")
    rows, ids = [], set()
    for index, item in enumerate(doc["rows"]):
        row = _row(item, index, known)
        if row.id in ids:
            raise Invalid(f"rules: row {row.id}: id: duplicate id")
        ids.add(row.id)
        rows.append(row)
    missing = sorted(set(range(1, 39)) - {n for row in rows for n in row.matrix_rows})
    if missing:                                                              # P14
        raise Invalid(f"rules: matrix rows {missing} are covered by no row")
    return RulesTable(schema=_RULES_SCHEMA, scope=scope, known_changes=known, rows=tuple(rows))


# --------------------------------------------------------------------------- #
# Instrument map (spec 5.1; P9, P10, P11)
# --------------------------------------------------------------------------- #
_INSTRUMENTS_SCHEMA = "tradegen.instruments/1"
_ENTRY_KEYS = frozenset({"asset", "multiple", "underlying", "class", "cost_book", "currency", "tax_basis", "source"})
# The odds engine's cost book per asset; every other asset is gate-only and carries null.
_COST_BOOK = {"krx_share": "KRX_stock_book", "krx_etp": "KRX_ETF_line", "us_share": "US_shares_KIS",
              "us_etp": "US_shares_KIS", "crypto_coin": "crypto_venue"}
# Spec 5.1's grouping of the asset kinds; its Futures and Other groups have no section, so the map cannot list them.
_SECTION_ASSETS = {"krx": frozenset({"krx_share", "konex_share", "krx_etp", "krx_derivative", "elw"}),
                   "us": frozenset({"us_share", "us_etp", "us_option"}),
                   "crypto": frozenset({"crypto_coin", "crypto_perp_or_future"})}


def _instrument(entry, section: str, symbol: str) -> Instrument:
    where = f"instruments: {section}/{symbol}"
    _keys(entry, where, _ENTRY_KEYS)
    asset = _member(entry["asset"], f"{where}: asset", ASSETS)
    if asset not in _SECTION_ASSETS[section]:
        raise Invalid(f"{where}: asset: {asset} does not belong in section {section}")
    underlying = entry["underlying"]
    if asset in ETP_ASSETS and underlying is None:
        raise Invalid(f"{where}: underlying: an ETP needs an underlying")
    if asset not in ETP_ASSETS and underlying is not None:
        raise Invalid(f"{where}: underlying: must be null for {asset}")
    if underlying is not None:
        _member(underlying, f"{where}: underlying", UNDERLYINGS)
    try:
        derived = derive_class(asset, entry["multiple"], underlying)
    except Invalid as exc:
        raise Invalid(f"{where}: {exc.reason}") from None
    declared = _member(entry["class"], f"{where}: class", CLASSES)
    if declared != derived:                                                  # P10
        raise Invalid(f"{where}: class: declared {declared}, derived {derived}")
    if section == "us" and symbol in KNOWN_SPOT_CRYPTO_ETPS and derived != "etp_crypto_spot":
        raise Invalid(f"{where}: a known spot-crypto ETP must derive etp_crypto_spot, not {derived}")   # P10
    book = _COST_BOOK.get(asset)
    if entry["cost_book"] != book:
        raise Invalid(f"{where}: cost_book: {asset} takes {book!r}, got {entry['cost_book']!r}")
    currency = entry["currency"]
    if not isinstance(currency, str) or not _CURRENCY.fullmatch(currency):
        raise Invalid(f"{where}: currency: expected an upper-case code, got {currency!r}")
    return Instrument(section=section, symbol=symbol, asset=asset, multiple=float(entry["multiple"]),
                      underlying=underlying, cls=derived, cost_book=book, currency=currency,
                      tax_basis=_member(entry["tax_basis"], f"{where}: tax_basis", TAX_BASES),
                      source=_text(entry["source"], f"{where}: source"))


def parse_instruments(raw: bytes) -> InstrumentMap:
    """instruments.yaml bytes -> InstrumentMap keyed by (section, symbol); a symbol may sit in two sections."""
    doc = load_strict(raw, "instruments")
    _keys(doc, "instruments", frozenset({"schema"}), frozenset(SECTIONS))
    if doc["schema"] != _INSTRUMENTS_SCHEMA:
        raise Invalid(f"instruments: schema must be {_INSTRUMENTS_SCHEMA}, got {doc['schema']!r}")
    entries = {}
    for section in SECTIONS:
        block = doc.get(section, {})
        if not isinstance(block, dict):
            raise Invalid(f"instruments: {section}: expected a mapping of symbols")
        for symbol, entry in block.items():
            _symbol(symbol, f"instruments: {section}")
            entries[(section, symbol)] = _instrument(entry, section, symbol)
    return InstrumentMap(entries=MappingProxyType(entries))


# --------------------------------------------------------------------------- #
# Venue facts (spec 5.1 "Venue facts"; P1, P9, P22)
# --------------------------------------------------------------------------- #
_VENUES_SCHEMA = "tradegen.venues/1"
_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits",
                             "lot", "min_order", "fee_extras", "tick_ladder"})      # the odds keys (odds plan Q17)
# The cost books a signed tick ladder may cover. KRX_ETF_line is not one: its ladder is core/quant/instruments.py's.
_LADDER_BOOKS = frozenset({"KRX_stock_book", "US_shares_KIS", "crypto_venue"})


def _odds_number(value, where: str, *, positive: bool) -> float:
    """A finite int or float, never a bool: > 0 when `positive` (as _positive), else >= 0, so that an explicit 0 is
    a signed value. A -0.0 is stored as 0.0 (`+ 0.0`), so a stored value never prints or serialises as -0.0."""
    if positive:
        return _positive(value, where)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise Invalid(f"{where}: expected a finite number >= 0, got {value!r}")
    return float(value) + 0.0


def _odds_lot(value, where: str, listed: dict, sections: tuple[str, ...]) -> tuple[tuple[str, float], ...]:
    """`lot: {source, units: {<symbol> | default: step}}` -> sorted (symbol or "default", step > 0); a symbol is one
    the venue's sections list."""
    _keys(value, where, frozenset({"source", "units"}))
    _text(value["source"], f"{where}: source")
    units = value["units"]
    if not isinstance(units, dict) or not units:
        raise Invalid(f"{where}: units: expected a non-empty mapping of symbol (or default) to a step")
    out = []
    for symbol, step in units.items():
        if symbol != "default" and (not isinstance(symbol, str) or symbol not in listed):
            raise Invalid(f"{where}: units: {symbol!r} is not a symbol of sections {list(sections)}")
        out.append((symbol, _odds_number(step, f"{where}: units: {symbol}", positive=True)))
    return tuple(sorted(out))


def _odds_min_order(value, where: str, settlement: frozenset) -> tuple[tuple[str, float], ...]:
    """`min_order: {source, quote: {<settlement asset>: amount}}` -> sorted (asset, minimum >= 0 in quote units)."""
    _keys(value, where, frozenset({"source", "quote"}))
    _text(value["source"], f"{where}: source")
    quote = value["quote"]
    if not isinstance(quote, dict) or not quote:
        raise Invalid(f"{where}: quote: expected a non-empty mapping of settlement asset to a minimum")
    out = []
    for asset, amount in quote.items():
        if not isinstance(asset, str) or asset not in settlement:
            raise Invalid(f"{where}: quote: {asset!r} is not one of the settlement assets {sorted(settlement)}")
        out.append((asset, _odds_number(amount, f"{where}: quote: {asset}", positive=False)))
    return tuple(sorted(out))


def _check_extras(value, where: str) -> tuple[float, float]:
    """Spec 4 "Costs" check_extras, here in the parser: `fee_extras: {source, phi_buy, phi_sell}` -> (phi_buy,
    phi_sell), the fixed KRW charges per buy and per sell. Each is finite and >= 0, so an extra can only raise a
    cost, and a negative one makes the venue file Invalid."""
    _keys(value, where, frozenset({"source", "phi_buy", "phi_sell"}))
    _text(value["source"], f"{where}: source")
    return (_odds_number(value["phi_buy"], f"{where}: phi_buy", positive=False),
            _odds_number(value["phi_sell"], f"{where}: phi_sell", positive=False))


def _odds_ladder(value, where: str, sections: tuple[str, ...], instruments: InstrumentMap) -> tuple:
    """`tick_ladder: {source, effective_from, books: {<cost book>: [[price_from, tick], ...]}}` -> sorted (book,
    effective_from "YYYY-MM-DD", ((price_from, tick), ...)). The first price_from is exactly 0 and they strictly
    increase; every tick is > 0; a book is in _LADDER_BOOKS and is the cost book of a symbol in the venue's
    sections. The date is kept as its checked text, so Venue.ladder_for never parses one."""
    _keys(value, where, frozenset({"source", "effective_from", "books"}))
    _text(value["source"], f"{where}: source")
    start = parse_date(value["effective_from"], f"{where}: effective_from").isoformat()
    books = value["books"]
    if not isinstance(books, dict) or not books:
        raise Invalid(f"{where}: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]")
    used = {inst.cost_book for (section, _), inst in instruments.entries.items() if section in sections}
    out = []
    for book, rows in books.items():
        if book == "KRX_ETF_line":
            raise Invalid(f"{where}: books: KRX_ETF_line: its ladder is core/quant/instruments.py's")
        _member(book, f"{where}: books", _LADDER_BOOKS)
        if book not in used:
            raise Invalid(f"{where}: books: {book} is the cost book of no symbol in sections {list(sections)}")
        if not isinstance(rows, list) or not rows:
            raise Invalid(f"{where}: books: {book}: expected a non-empty list of [price_from, tick] rows")
        ladder: list[tuple[float, float]] = []
        for row in rows:
            if not isinstance(row, list) or len(row) != 2:
                raise Invalid(f"{where}: books: {book}: {row!r} is not a [price_from, tick] row")
            price = _odds_number(row[0], f"{where}: books: {book}: price_from", positive=False)
            tick = _odds_number(row[1], f"{where}: books: {book}: tick", positive=True)
            if not ladder and price != 0:
                raise Invalid(f"{where}: books: {book}: the first price_from must be 0, got {row[0]!r}")
            if ladder and price <= ladder[-1][0]:
                raise Invalid(f"{where}: books: {book}: price_from {row[0]!r} is not above the row before")
            ladder.append((price, tick))
        out.append((book, start, tuple(ladder)))
    return tuple(sorted(out))


def _venue(vid: str, entry, instruments: InstrumentMap) -> Venue:
    where = f"venues: {vid}"
    _keys(entry, where, _VENUE_REQUIRED, _VENUE_OPTIONAL)
    sections = _strs(entry["sections"], f"{where}: sections", frozenset(SECTIONS))
    listed: dict[str, str] = {}
    for section, symbol in instruments.entries:
        if section in sections:
            if symbol in listed:                                             # P9
                raise Invalid(f"{where}: symbol {symbol} is listed in sections {listed[symbol]} and {section}")
            listed[symbol] = section
    settlement = frozenset(_symbol(s, f"{where}: settlement")
                           for s in _strs(entry["settlement"], f"{where}: settlement"))
    _text(entry["source"], f"{where}: source")
    by_currency = entry.get("quote_by_currency")
    if by_currency is not None and by_currency is not True:
        raise Invalid(f"{where}: quote_by_currency: only true may be written")
    markets, default = set(), None
    if by_currency:
        if "markets" in entry or "default_quote" in entry:
            raise Invalid(f"{where}: a quote_by_currency venue lists no markets and no default_quote")
    else:
        pairs = entry.get("markets")
        if not isinstance(pairs, list):
            raise Invalid(f"{where}: markets: expected a list of [base, quote] pairs (or quote_by_currency: true)")
        for pair in pairs:
            if not isinstance(pair, list) or len(pair) != 2:
                raise Invalid(f"{where}: markets: {pair!r} is not a [base, quote] pair")
            base, quote = _symbol(pair[0], f"{where}: markets"), _symbol(pair[1], f"{where}: markets")
            if base not in listed:
                raise Invalid(f"{where}: markets: base {base} is not a symbol of sections {list(sections)}")
            if quote not in settlement and quote not in listed:
                raise Invalid(f"{where}: markets: quote {quote} is neither a settlement asset nor a symbol of "
                              f"sections {list(sections)}")
            if base == quote or (base, quote) in markets:
                raise Invalid(f"{where}: markets: [{base}, {quote}] is repeated or trades a symbol for itself")
            markets.add((base, quote))
        default = entry.get("default_quote")
        if not isinstance(default, str) or default not in settlement:
            raise Invalid(f"{where}: default_quote: {default!r} is not one of the settlement assets")
    deposits = set()
    deposits_raw = [] if entry.get("deposits") is None else entry["deposits"]
    if not isinstance(deposits_raw, list):
        raise Invalid(f"{where}: deposits: expected a list")
    for dep in deposits_raw:
        _keys(dep, f"{where}: deposits", frozenset({"symbol", "network", "tag_required"}))
        symbol = _symbol(dep["symbol"], f"{where}: deposits.symbol")
        network = _text(dep["network"], f"{where}: deposits.network")
        if symbol not in listed:
            raise Invalid(f"{where}: deposits: {symbol} is not a symbol of sections {list(sections)}")
        if not isinstance(dep["tag_required"], bool):
            raise Invalid(f"{where}: deposits.tag_required: expected true or false")
        if any(d[:2] == (symbol, network) for d in deposits):
            raise Invalid(f"{where}: deposits: {symbol} on {network} is listed twice")
        deposits.add((symbol, network, dep["tag_required"]))
    odds: dict = {}                         # the odds keys (Q17); an absent one stays () or None: not tradable (O11)
    if "lot" in entry:
        odds["lot"] = _odds_lot(entry["lot"], f"{where}: lot", listed, sections)
    if "min_order" in entry:
        odds["min_order"] = _odds_min_order(entry["min_order"], f"{where}: min_order", settlement)
    if "fee_extras" in entry:
        odds["fee_extras"] = _check_extras(entry["fee_extras"], f"{where}: fee_extras")
    if "tick_ladder" in entry:
        odds["tick_ladder"] = _odds_ladder(entry["tick_ladder"], f"{where}: tick_ladder", sections, instruments)
    return Venue(id=vid, sections=sections, settlement=settlement, markets=frozenset(markets),
                 quote_by_currency=bool(by_currency), default_quote=default, deposits=frozenset(deposits),
                 odds_sources=tuple(sorted((key, entry[key]["source"]) for key in odds)), **odds)


def parse_venues(raw: bytes, instruments: InstrumentMap) -> VenueFacts:
    """venues.yaml bytes -> VenueFacts, checked against `instruments` (market bases, deposits and P9)."""
    doc = load_strict(raw, "venues")
    _keys(doc, "venues", frozenset({"schema", "venues"}))
    if doc["schema"] != _VENUES_SCHEMA:
        raise Invalid(f"venues: schema must be {_VENUES_SCHEMA}, got {doc['schema']!r}")
    block = doc["venues"]
    if not isinstance(block, dict) or not block:
        raise Invalid("venues: venues: expected a non-empty mapping")
    venues = {}
    for vid, entry in block.items():
        _member(vid, "venues: venue id", VENUES)
        venues[vid] = _venue(vid, entry, instruments)
    return VenueFacts(venues=MappingProxyType(venues))


# --------------------------------------------------------------------------- #
# Hashes and the approved state
# --------------------------------------------------------------------------- #
def file_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def calendar_stream(data_dir: Path) -> bytes:
    """P21: every regular file directly in `data_dir`, sorted by the name string, each framed as
    name + NUL + bytes + NUL (macro_artifacts.tree_hash's framing). A link in or as the directory is Invalid;
    subdirectories are not part of a calendar set. The one framing of the calendar set: calendar_sha256 hashes it
    and the owner's approved store (owner.store_put, owner.store_get) takes and rebuilds it."""
    root = Path(data_dir)
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        raise Invalid(f"calendar: {root} is not a plain directory")
    with os.scandir(root) as listing:
        found = sorted(listing, key=lambda e: e.name)
    parts = []
    for e in found:
        if e.is_symlink() or e.is_junction():
            raise Invalid(f"calendar: {e.name} is a link")
        if e.is_file(follow_symlinks=False):
            parts.append(e.name.encode("utf-8") + b"\0" + Path(e.path).read_bytes() + b"\0")
    return b"".join(parts)


def calendar_sha256(data_dir: Path) -> str:
    """P21: sha256 of calendar_stream(data_dir)."""
    return hashlib.sha256(calendar_stream(data_dir)).hexdigest()


def approved_state(rules_raw: bytes, instruments_raw: bytes, venues_raw: bytes, *, seq: int,
                   history_raws: tuple[bytes, ...] = ()) -> ApprovedState:
    """The three approved files as one state; never raises (any problem is ApprovedState.invalid(reason)).
    `history_raws` are earlier approved instrument maps, newest first; unparseable ones are skipped."""
    from core.compliance.model import ApprovedState          # lazy: no import cycle with model.py
    try:
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise Invalid(f"seq: expected an int >= 0, got {seq!r}")
        table = parse_rules(rules_raw)
        imap = parse_instruments(instruments_raw)
        facts = parse_venues(venues_raw, imap)
        history = []
        for old in history_raws:
            try:
                history.append(parse_instruments(old))
            except Invalid:
                continue
        return ApprovedState(valid=True, rules=table, instruments=imap, venues=facts,
                             hashes={"rules": file_sha256(rules_raw), "instruments": file_sha256(instruments_raw),
                                     "venues": file_sha256(venues_raw)},
                             seq=seq, history_maps=tuple(history))
    except Invalid as exc:
        return ApprovedState.invalid(exc.reason)
    except Exception as exc:                                  # never raises: an internal error is invalid too
        return ApprovedState.invalid(f"internal error {type(exc).__name__}")


# --------------------------------------------------------------------------- #
# --check (spec 5.4): what the daily job runs. Exit 0 nothing due, 1 due within 14 days, 2 overdue, 3 new exposure
# blocked, 4 the check itself failed.
# --------------------------------------------------------------------------- #
_SUMMARY_KEYS = ("code", "due", "overdue", "head_seq", "head_sha256", "fingerprint")   # the final JSON line
_DUE_DAYS = 14
_DRAFTS = (("rules", "core/compliance/kr_rules.yaml"), ("instruments", "core/compliance/instruments.yaml"),
           ("venues", "core/odds/venues.yaml"))
_LABELS = {"rules": "rules row", "instruments": "instrument", "venues": "venue"}
_LISTED = ("sources", "research")                  # spec 12: --check names each entry added or removed
_MEANING = {0: "nothing is due", 1: "something is due within 14 days", 2: "something is overdue",
            3: "new exposure is blocked (invalid or unapproved state, unsigned code, a broken owner log or a "
               "changed key); closing orders go through on the last approved snapshot, with none (as before owner "
               "act 1) close or withdraw manually in the app, and under a broken owner log withdraw manually",
            4: "the check itself failed"}


def check(today: date, *, repo_root: Path | None = None) -> dict:
    """The --check as data, as of the end of `today` (an Asia/Seoul date). load_context does the checking: the
    tables in force from the store, the owner log (chain, signatures, anchors), the key fingerprint against the first
    one recorded and the signed code hash. This adds the rows of the table in force that are due within 14 days or
    overdue, each repo draft against the version in force, and the calendar set. Returns _SUMMARY_KEYS plus
    "lines"; it writes nothing itself. A missing cryptography package raises ImportError here, so main() exits 4."""
    import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401  (spec 5.4: a missing package is exit 4)
    from datetime import datetime

    from core.compliance import model, owner
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    moment = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=model.KST)
    ctx = owner.load_context(moment, model.Positions(equity_krw=1.0))     # positions play no part in it (P19)
    problems = []
    if not ctx.active.valid:
        problems.append(f"state: INVALID: {ctx.active.reason}")
    if not ctx.owner.ok:
        problems += [f"owner log: BROKEN: {ctx.owner.reason}", "code: signature not checked (owner log not usable)"]
    elif not ctx.code_signed:
        problems.append(f"code: UNSIGNED: the code hash on disk {ctx.code_hash[:16]} is not the latest "
                        "code_approved; sign it after reviewing the diff")
    due, overdue = [], []
    for row in (ctx.active.rules.rows if ctx.active.valid else ()):
        for name in ("review_by", "auto_off", "effective_until"):
            when = getattr(row, name)
            if when is None:
                continue
            left = (when - today).days
            # the gate's dates: stale only after the review_by day; auto_off and effective_until bind on their own
            if left < 0 or (left == 0 and name != "review_by"):
                overdue.append({"row": row.id, "field": name, "date": when.isoformat(), "days_late": -left})
            elif left <= _DUE_DAYS:
                due.append({"row": row.id, "field": name, "date": when.isoformat(), "days_left": left})
    due.sort(key=lambda i: (i["date"], i["row"], i["field"]))
    overdue.sort(key=lambda i: (i["date"], i["row"], i["field"]))
    code = 3 if problems else 2 if overdue else 1 if due else 0
    seq, head_sha = ctx.owner.head
    lines = [f"TRADEGEN compliance check for {today.isoformat()} (Asia/Seoul)"]
    lines += problems or ["tables, owner log and code signature: OK"]
    lines.append(f"owner log head: entry #{seq}; key fingerprint {ctx.owner.fingerprint or 'none'}")
    lines += _draft_lines(ctx, root)
    lines.append(_calendar_line(ctx, root, moment))
    lines += [f"due: {i['row']} {i['field']} {i['date']} ({i['days_left']} days left)" for i in due]
    lines += [f"overdue: {i['row']} {i['field']} {i['date']} ({i['days_late']} days late)" for i in overdue]
    lines.append(f"exit {code}: {_MEANING[code]}")
    return {"code": code, "due": due, "overdue": overdue, "head_seq": seq, "head_sha256": head_sha,
            "fingerprint": ctx.owner.fingerprint, "lines": lines}


def _draft_lines(ctx, root: Path) -> list[str]:
    """Each repo draft against the version in force (spec 5.2: a draft counts only once signed) and, for a draft
    that differs, its changed rule rows, instruments and venues (spec 12)."""
    active = ctx.active if ctx.active.valid else None
    lines, draft_map = [], None
    for kind, rel in _DRAFTS:
        path = root / rel
        if not path.is_file():
            lines.append(f"{kind}: no draft at {rel}")
            continue
        raw = path.read_bytes()
        sha = file_sha256(raw)
        in_force = active.hashes.get(kind, "") if active is not None else ""
        if sha == in_force:
            lines.append(f"{kind}: the draft is the version in force ({sha[:16]})")
            continue
        lines.append(f"{kind}: the draft {sha[:16]} is not the version in force ({in_force[:16] or 'none'}); "
                     "it counts only once signed")
        if active is None:
            continue
        try:
            table = (parse_rules(raw) if kind == "rules" else parse_instruments(raw) if kind == "instruments"
                     else parse_venues(raw, draft_map if draft_map is not None else active.instruments))
        except Invalid as exc:
            lines.append(f"  {kind} draft INVALID: {exc}")
            continue
        if kind == "instruments":
            draft_map = table                           # the venues draft is read against the instruments draft
        lines += [f"  {_LABELS[kind]} {item}"
                  for item in _changed(_keyed(kind, getattr(active, kind)), _keyed(kind, table))]
    return lines


def _keyed(kind: str, table) -> dict:
    """A parsed table's entries by key, for the `kind` it was parsed as: rule rows by id, instruments as
    "section/symbol", venues by id. It goes by kind, not by class: run as `python -m`, this file is a second copy
    of the module that owner.py imports, and the classes of the two copies are different."""
    if kind == "rules":
        return {r.id: r for r in table.rows}
    if kind == "instruments":
        return {"/".join(key): inst for key, inst in table.entries.items()}
    return dict(table.venues)


def _changed(old: dict, new: dict) -> list[str]:
    """"<key>: added", "<key>: removed" or "<key>: <field>, <field> changed", sorted by key. A changed _LISTED
    field also gets one line per entry added or removed, repr'd so that no entry can pass for a line of its own."""
    from core.compliance import model
    out = []
    for key in sorted(set(old) | set(new)):
        if key not in old:
            out.append(f"{key}: added")
        elif key not in new:
            out.append(f"{key}: removed")
        else:
            a, b = model.jsonable(old[key]), model.jsonable(new[key])
            fields = sorted(f for f in a if a[f] != b.get(f))
            if fields:
                out.append(f"{key}: {', '.join(fields)} changed")
            for f in (f for f in _LISTED if f in fields):
                out += [f"{key}: {f} added {x!r}" for x in b[f] if x not in a[f]]
                out += [f"{key}: {f} removed {x!r}" for x in a[f] if x not in b[f]]
    return out


def _calendar_line(ctx, root: Path, moment) -> str:
    """The calendar draft (P21) against the latest calendar approval signed by `moment` (load_context's cut-off),
    whose stored copy must be intact. The Context does not carry it, so the log is read and verified once more."""
    from core.compliance import model, owner
    if not ctx.owner.ok:
        return "calendar: not checked (owner log not usable)"
    try:
        log = owner.verify_log(owner._log_lines(owner.log_path()), owner.read_pubkey(owner.PUBKEY_PATH),
                               owner.read_anchors())
    except (OSError, ValueError, RuntimeError):         # an unreadable key, anchor or log file means BROKEN (Task 11)
        return "calendar: not checked (owner log not usable)"
    if not log.ok:
        return "calendar: not checked (owner log not usable)"
    signed = owner.in_force(owner._up_to(log, model.iso_utc(moment))).get("calendar", ("", 0))[0]
    if not signed:
        return "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"
    if owner.store_get("calendar", signed) is None:
        return f"calendar: the signed version {signed[:16]} is missing or altered in the store"
    try:                                                # the one framing (Task 13), read once and hashed here
        draft = model.sha256_hex(calendar_stream(root / "core" / "calendars" / "data"))
    except (Invalid, OSError):                          # a link, a missing folder or an unreadable file: no draft
        draft = ""
    if draft == signed:
        return f"calendar: the draft is the version in force ({signed[:16]})"
    return (f"calendar: the draft {draft[:16] or 'none'} is not the version in force ({signed[:16]}); it counts "
            "only once signed")


def main(argv=None) -> int:
    """`python -m core.compliance.rules --check [--today YYYY-MM-DD]` (spec 5.4). Prints the human lines, then
    exactly one JSON line with _SUMMARY_KEYS, and returns the exit code. Everything that stops the check itself is
    exit 4: argparse errors and --help, a bad --today, a missing cryptography package, any exception. --today is an
    Asia/Seoul date; its default is the only wall clock in this module. Run as `python -m`, this file is a second
    copy of core.compliance.rules (owner.py imports the other one), so it hands over to that copy's main: one set
    of classes and one set of names (tests patch those)."""
    import argparse
    import json
    import sys
    from datetime import datetime

    from core.compliance import model
    from core.compliance import rules as canonical
    if canonical.main is not main:
        return canonical.main(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        parser = argparse.ArgumentParser(prog="python -m core.compliance.rules", exit_on_error=False)
        parser.add_argument("--check", action="store_true", help="check tables, owner log, code hash and key")
        parser.add_argument("--today", help="an Asia/Seoul date, YYYY-MM-DD (default: today)")
        args = parser.parse_args(argv)
        if not args.check:
            raise ValueError("nothing to do: pass --check")
        today = parse_date(args.today, "--today") if args.today is not None else datetime.now(model.KST).date()
        result = check(today)
    except BaseException as exc:                    # spec 5.4: a failure of the check itself is exit 4, never 0-3
        result = {"code": 4, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": "",
                  "lines": [f"check failed: {type(exc).__name__}: {exc}", f"exit 4: {_MEANING[4]}"]}
    for line in result["lines"]:
        print(line)
    print(json.dumps({k: result[k] for k in _SUMMARY_KEYS}, ensure_ascii=True))
    return result["code"]


if __name__ == "__main__":
    raise SystemExit(main())
