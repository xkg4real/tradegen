# Upbit KRW universe PR 2: public data readers, snapshot builder and writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the fixed public Upbit helpers, a read-only builder that turns one day's public answers into verified
universe snapshot bytes, the odds-batch candle reader `daily_bars`, the keyless per-slot flag and ticker source, and
a write-once snapshot store with its `snapshot --state-root <root>` command.

**Architecture:** `execution/upbit_inquiry.py` gains four fixed-parameter public GET helpers and two allowlisted paths.
`execution_accounts/universe.py` calls only those helpers under `inquiry_clock`, turns answers into `SourceReceipt`s
and plain receipts, and hands them to PR 1's pure `core.compliance.rules` functions; it writes nothing.
`execution_launch/universe_store.py` is the only writer: a new temporary file, fsync, then a rename to a name that does
not exist yet, behind pinned write shapes; its command builds and writes today's snapshot.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib only (`json`, `base64`, `hashlib`,
`decimal`, `dataclasses`, `os`), the repo's transport, collector, compliance and isolation modules. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md) sections 5, 7
(the per-slot source of steps 4 and 5) and 9 (the `daily_bars` bullet). Executors read the spec and the
[index](2026-11-11-upbit-krw-universe-index.md) before Task 1.

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(base fd85850, one branch and one PR, the owner merges, no new dependency, offline tests, byte-exact line endings,
`git diff --stat` equal to `git diff --stat --ignore-cr-at-eol` before each commit, commit and PR trailers, hand-updated
guard pins).

PR-specific constraints, verbatim from the spec:

- "`execution/upbit_inquiry.py` gets fixed-parameter, public-only helpers and path constants next to `current_terms`:
  `market_all()` (`is_details=true`), `daily_candles(market, to, count)` with `count` at most 200, and
  `orderbook_instruments(markets)`. Each returns a transport `Answer`; none pages or calls the keyed
  `/v1/orders/chance`. Every symbol passes `KRW-[A-Z][A-Z0-9]{0,11}`. Add the two new paths to `ENDPOINTS` and `PUBLIC`."
- "`execution_accounts/universe.py` is read-only, shaped like `E1UpbitTermsSource`: it calls the helpers under
  `inquiry_clock`, turns each `Answer` into a `SourceReceipt` (server time required), converts receipts to the plain
  shape, calls `rules.universe_eligible`, and returns the file bytes. It writes nothing. Pin it in
  `tests/accounts_guards.py` (`TRANSPORT_IMPORTS["universe.py"]`)."
- "`execution_launch/universe_store.py` writes the file (temporary file, fsync, then a link or rename to a name that
  does not exist yet) and holds the CLI `python -m execution_launch.universe_store snapshot --state-root <root>`. The
  CLI refuses unless `TRADEGEN_HOME` equals `--state-root`, like `tools.owner.launch setup-account`. Pin the writer in
  `tests/launch_guards.py` `PINNED_WRITES`."
- "Write-once and content-addressed: `owner.universe_path(D, sha256)` next to `owner.evidence_path()`. The writer
  opens with `O_EXCL` and never replaces a file, so a rebuild adds a file and never changes one that a session or
  history row already names."
- "The only retry is the transport's own single GET retry after a connection error or HTTP 429/5xx
  (`execution/transport.py:130-153`)."
- "If any request fails, no file is written for D, and buys that need the universe stop at 09:40 KST."
- "Steps 4 and 5 use a new keyless `execution_accounts` source (section 19, PR 2) with its own guard pins and body caps
  sized from the section 17 measurement. A failed read is recorded as `unavailable`."
- "Candles: `execution_accounts/universe.py` gets `daily_bars(markets)`, which pages the `daily_candles` helper under
  `inquiry_clock`, checks each receipt's path, params and sha256, keeps final bars only with the rules of `load_leg`'s
  `upbit_daily` path, and returns plain bars plus the receipt sha256 list. It imports no `core.oddsdata`, `data.*` or
  `config`."
- "Creating scheduled tasks is an owner act; Claude does not."

Line numbers below are at fd85850. PR 1 does not touch these files; if a line moved, find the quoted text instead.

---

## Test commands

Define once per shell (from the index):

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

A module that fails to import shows up as one test named `<module>/import`.

## Setup (before Task 1)

- [ ] **Step 1: Branch from main after PR 1 merged and confirm PR 1's names exist**

```bash
git fetch origin
git checkout -b claude/universe-pr2-data origin/main
"$PY" -X utf8 -c "from core.compliance import owner, rules; print(rules.UNIVERSE_MARKET.pattern, rules.UniverseRule, rules.UniverseError, rules.market_flags, rules.universe_requests, rules.encode_universe_snapshot, rules.verify_universe_snapshot, rules.universe_rule_sha256, owner.universe_path, owner.universe_dir, rules.Venue.__dataclass_fields__['universe_rule'].name)"
```

Expected: one line naming each object and ending in `universe_rule` (Task 6 reads `Venue.universe_rule`). An
`AttributeError` or `KeyError` means PR 1 is not merged yet: stop and report.

## File Structure

- Modify `execution/upbit_inquiry.py`: two allowlisted public paths, their constants and four fixed public helpers
  (`market_all`, `daily_candles`, `orderbook_instruments`, `tickers`) plus `candle_params`, the one place that writes
  a daily-candle query.
- Create `execution_accounts/universe.py`: every universe read. `build_universe_snapshot` (spec 5), `daily_bars`
  (spec 9), `UniverseSlotSource` (spec 7). Read-only; no key, no file, no `owner`.
- Create `execution_launch/universe_store.py`: the only universe writer (`write_snapshot`) and the `snapshot` command.
- Create `tests/accounts_universe.py`: offline tests and fixtures (market/all rows, candle server, routes) for
  `execution_accounts/universe.py`.
- Create `tests/launch_universe_store.py`: offline tests of the writer and the command.
- Modify `tests/execution_upbit.py`: helper tests. `tests/execution_guards.py` and `tests/renewal_boundaries.py`: the
  hand-updated allowlist and surface pins.
- Modify `tests/accounts_guards.py` (`TRANSPORT_IMPORTS`), `tests/accounts_acceptance.py` (`MODULES`),
  `tests/launch_guards.py` (`PINNED_WRITES` and a writer test), `tests/launch_acceptance.py` (`MODULES`).

---

### Task 1: Public Upbit universe helpers

**Files:**
- Modify: `execution/upbit_inquiry.py:6-12` (imports), `:18-20` (`ENDPOINTS` tail and `PUBLIC`), after `:24`
  (constants), after `:38` (helpers)
- Modify: `tests/execution_guards.py:1017-1020` and `:1037` (allowlist pins)
- Modify: `tests/renewal_boundaries.py:25` (surface pin of `execution/upbit_inquiry.py`)
- Test: `tests/execution_upbit.py` (import at `:12`, tests appended after `:244`)

**Interfaces:**
- Consumes: `execution.transport.request`, `Answer`, `InquiryRefused` (existing).
- Produces (index contract): `MARKET_ALL_PATH = "/v1/market/all"`, `CANDLES_DAYS_PATH = "/v1/candles/days"`,
  `market_all() -> Answer`, `daily_candles(market: str, to: datetime, count: int) -> Answer` (`count` 1..200),
  `orderbook_instruments(markets: Sequence[str]) -> Answer`, `tickers(markets: Sequence[str]) -> Answer`.
  Additions: `CANDLE_COUNT_MAX = 200` and `candle_params(market: str, to: datetime, count: int) ->
  tuple[tuple[str, str], ...]`, the exact query `(("market", m), ("to", "<YYYY-MM-DDTHH:MM:SS>Z"), ("count", "<n>"))`
  that `daily_candles` sends, so readers can rebuild a receipt's params without a `/v1/` literal. Every helper raises
  `InquiryRefused` before any key read or send for a market outside `KRW-[A-Z][A-Z0-9]{0,11}`, `KRW-KRW`, an empty,
  repeated or non-list/tuple market list, a naive `to` or a `count` outside 1..200.

- [ ] **Step 1: Write the failing tests and the hand-updated pins**

In `tests/execution_upbit.py`, after line 12 (`import re`) add:

```python
from datetime import timedelta, timezone
```

Append after line 244:

```python


def _refused(call):
    try:
        call()
    except upbit_inquiry.InquiryRefused:
        return
    raise AssertionError("a bad universe request was not refused")


def test_public_universe_helpers_send_fixed_keyless_gets():
    """Spec 5: market_all, daily_candles, orderbook_instruments and tickers are fixed public GETs with no
    Authorization header; the suite removed every key name, so they need no key."""
    routes = {("GET", "/v1/market/all"): [], ("GET", "/v1/candles/days"): [],
              ("GET", "/v1/orderbook/instruments"): [], ("GET", "/v1/ticker"): []}
    with EF.serve(routes) as calls:
        answers = (upbit_inquiry.market_all(), upbit_inquiry.daily_candles("KRW-BTC", EF.NOW, 200),
                   upbit_inquiry.orderbook_instruments(["KRW-BTC", "KRW-ETH"]),
                   upbit_inquiry.tickers(("KRW-BTC", "KRW-ETH")))
    assert [call["url"] for call in calls] == [
        "https://api.upbit.com/v1/market/all?is_details=true",
        "https://api.upbit.com/v1/candles/days?market=KRW-BTC&to=2026-10-24T00%3A00%3A00Z&count=200",
        "https://api.upbit.com/v1/orderbook/instruments?markets=KRW-BTC,KRW-ETH",
        "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH"]
    assert all(call["method"] == "GET" and "authorization" not in _headers(call) for call in calls)
    assert all(answer.body == [] and answer.raw_body == b"[]" for answer in answers)
    assert (upbit_inquiry.MARKET_ALL_PATH, upbit_inquiry.CANDLES_DAYS_PATH) == ("/v1/market/all", "/v1/candles/days")
    seoul = EF.NOW.astimezone(timezone(timedelta(hours=9)))
    assert upbit_inquiry.candle_params("KRW-BTC", seoul, 1) == (
        ("market", "KRW-BTC"), ("to", "2026-10-24T00:00:00Z"), ("count", "1"))


def test_public_universe_helpers_refuse_bad_input_before_any_send():
    """Every market passes KRW-[A-Z][A-Z0-9]{0,11} (KRW-KRW refused), a list is a non-empty list or tuple of distinct
    markets, `to` is aware and `count` is an int in 1..200; a refusal sends nothing (the suite's stub would)."""
    for market in ("KRW-btc", "KRW-KRW", "BTC-ETH", "KRW-", "KRW-ABCDEFGHIJKLM", " KRW-BTC", 7, None):
        _refused(lambda: upbit_inquiry.daily_candles(market, EF.NOW, 1))
        _refused(lambda: upbit_inquiry.orderbook_instruments([market]))
        _refused(lambda: upbit_inquiry.tickers([market]))
    for markets in ([], (), "KRW-BTC", ["KRW-BTC", "KRW-BTC"], {"KRW-BTC"}, None):
        _refused(lambda: upbit_inquiry.orderbook_instruments(markets))
        _refused(lambda: upbit_inquiry.tickers(markets))
    for to, count in ((EF.NOW.replace(tzinfo=None), 1), (EF.NOW.date(), 1), (EF.NOW, 0), (EF.NOW, 201),
                      (EF.NOW, True), (EF.NOW, "1")):
        _refused(lambda: upbit_inquiry.daily_candles("KRW-BTC", to, count))
    assert not EF.STRAYS, EF.STRAYS
```

In `tests/execution_guards.py`, replace lines 1017-1020:

```python
    upbit = frozenset({("GET", "/v1/accounts"), ("GET", "/v1/order"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"),
                       ("GET", "/v1/withdraws"), ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"),
                       ("GET", "/v1/api_keys"), ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker"),
                       ("GET", "/v1/orderbook"), ("GET", "/v1/orders/chance"), ("GET", "/v1/orderbook/instruments")})
```

with:

```python
    upbit = frozenset({("GET", "/v1/accounts"), ("GET", "/v1/order"), ("GET", "/v1/orders/open"), ("GET", "/v1/orders/closed"),
                       ("GET", "/v1/withdraws"), ("GET", "/v1/withdraws/coin_addresses"), ("GET", "/v1/deposits"),
                       ("GET", "/v1/api_keys"), ("GET", "/v1/status/wallet"), ("GET", "/v1/ticker"),
                       ("GET", "/v1/orderbook"), ("GET", "/v1/orders/chance"), ("GET", "/v1/orderbook/instruments"),
                       ("GET", "/v1/market/all"), ("GET", "/v1/candles/days")})
```

and replace line 1037:

```python
    assert upbit_inquiry.PUBLIC == frozenset({"/v1/ticker", "/v1/orderbook", "/v1/orderbook/instruments"})
```

with:

```python
    assert upbit_inquiry.PUBLIC == frozenset({"/v1/ticker", "/v1/orderbook", "/v1/orderbook/instruments",
                                              "/v1/market/all", "/v1/candles/days"})
```

In `tests/renewal_boundaries.py` line 25, replace the hash
`7244620f99bf1d7aa596c5155d887c94e8872dfb635273609f546653e6e4af24` with
`cdeb85aa8c1fbe5f63c5328716406cb298909fe82543207949106b6ecd5b7b10`, so the line reads:

```python
    "execution/upbit_inquiry.py": "cdeb85aa8c1fbe5f63c5328716406cb298909fe82543207949106b6ecd5b7b10",
```

This value is the surface (imports, top-level assignments and signatures; function bodies and docstrings excluded) of
the Step 3 file. It was computed from the exact Step 3 text, not regenerated from a later edit.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus execution execution_upbit/test_public_universe
focus execution execution_guards/test_allowlists_are_pinned
focus control control_guards/test_renewal_validation
```

Expected: both `execution_upbit` tests FAIL with `AttributeError: module 'execution.upbit_inquiry' has no attribute
'market_all'` (the second with `daily_candles`); `test_allowlists_are_pinned` FAILs with
`[('GET', '/v1/candles/days'), ('GET', '/v1/market/all')]`; the renewal test FAILs with
`execution/upbit_inquiry.py: initialization surface changed`.

- [ ] **Step 3: Implement the helpers**

In `execution/upbit_inquiry.py`, replace lines 6-12:

```python
import math
import re
from datetime import datetime

from core.compliance import model
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import AuthError, InquiryError, InquiryRefused, KeyMissing, request
```

with:

```python
import math
import re
from collections.abc import Sequence
from datetime import datetime, timezone

from core.compliance import model
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
from execution.transport import Answer, AuthError, InquiryError, InquiryRefused, KeyMissing, request
```

Replace lines 18-20:

```python
    ("GET", "/v1/orders/chance"), ("GET", "/v1/orderbook/instruments"),
})
PUBLIC = frozenset({"/v1/ticker", "/v1/orderbook", "/v1/orderbook/instruments"})
```

with:

```python
    ("GET", "/v1/orders/chance"), ("GET", "/v1/orderbook/instruments"), ("GET", "/v1/market/all"),
    ("GET", "/v1/candles/days"),
})
PUBLIC = frozenset({"/v1/ticker", "/v1/orderbook", "/v1/orderbook/instruments", "/v1/market/all",
                    "/v1/candles/days"})
```

After line 24 (`TERMS_INSTRUMENTS_PATH = "/v1/orderbook/instruments"`) insert:

```python
MARKET_ALL_PATH = "/v1/market/all"
CANDLES_DAYS_PATH = "/v1/candles/days"
CANDLE_COUNT_MAX = 200                    # Upbit's largest daily-candle page
```

After line 38 (`    return chance, instruments`, the last line of `current_terms`) insert:

```python


def _krw_market(market) -> str:
    """One KRW market such as KRW-BTC; InquiryRefused for anything else, before any key is read or request sent."""
    if (type(market) is not str or re.fullmatch(r"KRW-[A-Z][A-Z0-9]{0,11}", market) is None
            or market == "KRW-KRW"):
        raise InquiryRefused("upbit: invalid KRW market")
    return market


def _krw_markets(markets) -> str:
    """A non-empty list or tuple of distinct KRW markets, joined as Upbit's `markets` parameter."""
    if type(markets) not in (list, tuple) or not markets:
        raise InquiryRefused("upbit: invalid KRW market list")
    names = [_krw_market(m) for m in markets]
    if len(set(names)) != len(names):
        raise InquiryRefused("upbit: invalid KRW market list")
    return ",".join(names)


def market_all() -> Answer:
    """Every Upbit market with its warning and caution flags (is_details=true), one public GET."""
    return request("upbit", "GET", MARKET_ALL_PATH, (("is_details", "true"),))


def candle_params(market: str, to: datetime, count: int) -> tuple[tuple[str, str], ...]:
    """The fixed query of one daily-candle page: `count` (1 to 200) candles dated before `to` (exclusive), in UTC."""
    if type(to) is not datetime or to.utcoffset() is None:
        raise InquiryRefused("upbit: candle time must be aware")
    if type(count) is not int or not 1 <= count <= CANDLE_COUNT_MAX:
        raise InquiryRefused("upbit: invalid candle count")
    return (("market", _krw_market(market)), ("to", to.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("count", str(count)))


def daily_candles(market: str, to: datetime, count: int) -> Answer:
    """One page of daily candles, one public GET; paging is the caller's."""
    return request("upbit", "GET", CANDLES_DAYS_PATH, candle_params(market, to, count))


def orderbook_instruments(markets: Sequence[str]) -> Answer:
    """Tick size and book levels of the given KRW markets, one public GET."""
    return request("upbit", "GET", TERMS_INSTRUMENTS_PATH, (("markets", _krw_markets(markets)),))


def tickers(markets: Sequence[str]) -> Answer:
    """The last trade of the given KRW markets, one public GET."""
    return request("upbit", "GET", _TICKER, (("markets", _krw_markets(markets)),))
```

The existing blank line 39 and `_ACCOUNTS = "/v1/accounts"` follow unchanged. `_TICKER` (line 47 today) is read at
call time.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus execution execution_upbit/test_public_universe
focus execution execution_guards/test_allowlists_are_pinned
focus control control_guards/test_renewal_validation
focus execution execution_upbit/
focus execution execution_guards/
```

Expected: every command exits 0 with no FAIL row. If the renewal test still reports a changed surface, the Step 3
text differs from this plan: diff it against the plan, never regenerate the pin. To print the surface for review:
`"$PY" -B -X utf8 -c "from tests.renewal_boundaries import _surface; print(_surface(open('execution/upbit_inquiry.py', encoding='utf-8').read()))"`.

- [ ] **Step 5: Commit**

```bash
git add execution/upbit_inquiry.py tests/execution_upbit.py tests/execution_guards.py tests/renewal_boundaries.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution/upbit_inquiry.py tests/execution_upbit.py tests/execution_guards.py tests/renewal_boundaries.py
git commit -m "$(cat <<'EOF'
Add fixed public Upbit universe helpers to the inquiry allowlist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 2: Read-only universe snapshot builder

**Files:**
- Create: `execution_accounts/universe.py`
- Create: `tests/accounts_universe.py`
- Modify: `tests/accounts_guards.py:20-25` (`TRANSPORT_IMPORTS`)
- Modify: `tests/accounts_acceptance.py:9-10` (`MODULES`)

**Interfaces:**
- Consumes (Task 1): `MARKET_ALL_PATH`, `CANDLES_DAYS_PATH`, `market_all() -> Answer`,
  `daily_candles(market, to, count) -> Answer`, `candle_params(market, to, count)`. (PR 1):
  `rules.UniverseRule`, `rules.universe_requests(rule, market_all_body: bytes, day: date)` (sorted `(path, params)`
  pairs including `("/v1/market/all", (("is_details", "true"),))`), `rules.encode_universe_snapshot(rule, day,
  receipts) -> tuple[bytes, str]`, `rules.verify_universe_snapshot(raw, rule_sha256) -> Universe`,
  `rules.universe_rule_sha256(rule) -> str`, `Universe.snapshot_sha256`. (existing):
  `execution_accounts.collector.SourceReceipt`, `execution.transport.Answer`, `inquiry_clock`.
- Produces (index contract): `build_universe_snapshot(rule: UniverseRule, day: date, *, clock) -> tuple[bytes, str]`.
  Additions: `class UniverseReadError(ValueError)` with codes `UNIVERSE_INPUT_INVALID`, `UNIVERSE_INQUIRY_FAILED`,
  `UNIVERSE_SERVER_TIME_REQUIRED`, `UNIVERSE_BODY_EMPTY_OR_OVERSIZED`, `UNIVERSE_RECEIPT_INVALID`,
  `UNIVERSE_REQUEST_INVALID`, `UNIVERSE_SNAPSHOT_MISMATCH` (PR 1's `UniverseError` codes pass through unchanged);
  `PUBLIC_SCOPE = "public"`; `MAX_MARKET_ALL_BODY`, `MAX_CANDLE_BODY` (provisional caps). Test fixtures other tests
  import: `tests.accounts_universe.DAY`, `BUILT`, `BUILT_HEADER`, `RULE`, `MARKET_ALL_RAW`, `candle()`,
  `candle_server()`, `routes(candles=None)`.
- Deviations from spec 5's wording, stated here: the builder does not call `rules.universe_eligible` itself, because
  `encode_universe_snapshot` and `verify_universe_snapshot` run it on the same receipts. The receipts reach
  `encode_universe_snapshot` in the order `rules.universe_requests` returns them (market/all at its sorted place,
  after the candle requests), which is the order PR 3's `tests/compliance_fixtures.universe_receipts` passes; the
  market/all read is still sent, and its receipt checked, before any candle read.

- [ ] **Step 1: Write the failing tests, register the module and pin the transport import**

Create `tests/accounts_universe.py`:

```python
"""Upbit universe reads (spec sections 5, 7 and 9): synthetic public answers through the fake transport._send only;
no venue call, key or file write."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from unittest.mock import patch
from urllib.parse import parse_qsl

from core.compliance import rules
from execution_accounts import universe as U
from tests import execution_fixtures as F

DAY = date(2026, 11, 11)                                    # candle day D, a Wednesday
BUILT = datetime(2026, 11, 11, 0, 12, tzinfo=timezone.utc)  # 09:12 KST, the scheduled build
BUILT_HEADER = "Wed, 11 Nov 2026 00:12:00 GMT"
LISTED = date(2020, 1, 1)
RULE = rules.UniverseRule(source="https://docs.upbit.com/kr/reference/list-trading-pairs", quote="KRW",
                          exclude=("USDT", "USDC"), min_listing_days=250, median_days=30,
                          min_median_value_krw=1_000_000_000)
CAUTION_KEYS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING",
                "GLOBAL_PRICE_DIFFERENCES", "CONCENTRATION_OF_SMALL_ACCOUNTS")


def market(name, *, warning=False, caution=()):
    """One market/all?is_details=true row."""
    return {"market": name, "korean_name": name, "english_name": name,
            "market_event": {"warning": warning, "caution": {key: key in caution for key in CAUTION_KEYS}}}


MARKETS = (market("KRW-BTC"), market("KRW-ETH"), market("KRW-USDT"),
           market("KRW-XYZ", caution=("PRICE_FLUCTUATIONS",)), market("BTC-ETH"))
MARKET_ALL_RAW = json.dumps(list(MARKETS)).encode("utf-8")


def candle(name, day, *, value=2_000_000_000.0, opening=100, closing=101):
    """One daily-candle row dated `day` (UTC), with Upbit's field names."""
    return {"market": name, "candle_date_time_utc": day.isoformat() + "T00:00:00",
            "candle_date_time_kst": day.isoformat() + "T09:00:00", "opening_price": opening,
            "high_price": max(opening, closing), "low_price": min(opening, closing), "trade_price": closing,
            "timestamp": int(datetime(day.year, day.month, day.day, 23, 59, tzinfo=timezone.utc).timestamp()) * 1000,
            "candle_acc_trade_price": value, "candle_acc_trade_volume": 1.0}


def candle_server(listed_since, *, header=BUILT_HEADER, last=DAY - timedelta(days=1)):
    """A serve() callable for daily candles like Upbit: the `count` newest candles dated before `to` (exclusive),
    newest first, of a market whose candles run from `listed_since` to `last`; `header` None sends no Date."""
    def answer(call):
        query = dict(parse_qsl(call["query"]))
        newest = min(last, datetime.fromisoformat(query["to"]).date() - timedelta(days=1))
        days = [newest - timedelta(days=n) for n in range(int(query["count"]))]
        body = [candle(query["market"], day) for day in days if day >= listed_since]
        return 200, ({} if header is None else {"Date": header}), json.dumps(body).encode("utf-8")
    return answer


def routes(candles=None):
    """serve() routes of one healthy build at BUILT."""
    return {("GET", "/v1/market/all"): lambda call: (200, {"Date": BUILT_HEADER}, MARKET_ALL_RAW),
            ("GET", "/v1/candles/days"): candles or candle_server(LISTED)}


def refused(call, code):
    try:
        call()
    except U.UniverseReadError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError(f"not refused: {code}")


def build():
    return U.build_universe_snapshot(RULE, DAY, clock=lambda: BUILT)


def test_builder_sends_exactly_the_rule_requests_and_returns_verified_bytes():
    with F.serve(routes()) as calls:
        raw, sha256 = build()
    expected = rules.universe_requests(RULE, MARKET_ALL_RAW, DAY)
    assert calls[0]["url"] == "https://api.upbit.com/v1/market/all?is_details=true"
    assert sorted((c["path"], tuple(parse_qsl(c["query"]))) for c in calls) == sorted(expected)
    assert len(calls) == len(expected) == 5          # market/all, then the age and value reads of KRW-BTC and KRW-ETH
    assert all(c["method"] == "GET" and "authorization" not in {k.lower() for k in c["headers"]} for c in calls)
    universe = rules.verify_universe_snapshot(raw, rules.universe_rule_sha256(RULE))
    assert universe.snapshot_sha256 == sha256 and universe.day == DAY
    assert universe.listed == ("KRW-BTC", "KRW-ETH", "KRW-USDT", "KRW-XYZ")
    assert universe.eligible == (("KRW-BTC", Decimal(2_000_000_000)), ("KRW-ETH", Decimal(2_000_000_000)))


def test_a_failed_read_fails_the_build_after_the_transport_retry_only():
    error = lambda call: (500, {"Date": BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with F.serve(routes(error)) as calls:
        refused(build, "UNIVERSE_INQUIRY_FAILED")
    assert [c["path"] for c in calls] == ["/v1/market/all", "/v1/candles/days", "/v1/candles/days"]
    with F.serve({("GET", "/v1/market/all"): error}) as calls:
        refused(build, "UNIVERSE_INQUIRY_FAILED")
    assert [c["path"] for c in calls] == ["/v1/market/all", "/v1/market/all"]


def test_answers_without_server_time_or_over_the_body_cap_and_bad_inputs_are_refused():
    with F.serve(routes(candle_server(LISTED, header=None))):
        refused(build, "UNIVERSE_SERVER_TIME_REQUIRED")
    with F.serve(routes()), patch.object(U, "MAX_CANDLE_BODY", 64):
        refused(build, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    with F.serve(routes()), patch.object(U, "MAX_MARKET_ALL_BODY", len(MARKET_ALL_RAW) - 1):
        refused(build, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    for changes in ({"clock": None}, {"day": "2026-11-11"}, {"rule": None}):
        args = {"rule": RULE, "day": DAY, "clock": lambda: BUILT} | changes
        refused(lambda: U.build_universe_snapshot(args["rule"], args["day"], clock=args["clock"]),
                "UNIVERSE_INPUT_INVALID")
```

In `tests/accounts_guards.py`, replace lines 20-25:

```python
TRANSPORT_IMPORTS = {
    "upbit_collector.py": frozenset({"inquiry_clock", "request"}),
    "quotes.py": frozenset({"Answer", "inquiry_clock", "request"}),
    "readiness.py": frozenset({"inquiry_clock"}),
    "instrument_terms.py": frozenset({"Answer", "inquiry_clock"}),
}
```

with:

```python
TRANSPORT_IMPORTS = {
    "upbit_collector.py": frozenset({"inquiry_clock", "request"}),
    "quotes.py": frozenset({"Answer", "inquiry_clock", "request"}),
    "readiness.py": frozenset({"inquiry_clock"}),
    "instrument_terms.py": frozenset({"Answer", "inquiry_clock"}),
    "universe.py": frozenset({"Answer", "inquiry_clock"}),
}
```

In `tests/accounts_acceptance.py`, replace lines 9-10:

```python
MODULES = ("accounts_guards", "accounts_provider", "accounts_readiness", "accounts_baseline", "accounts_quotes",
           "accounts_baseline_integration", "accounts_recovery", "accounts_continuous")
```

with:

```python
MODULES = ("accounts_guards", "accounts_provider", "accounts_readiness", "accounts_baseline", "accounts_quotes",
           "accounts_baseline_integration", "accounts_recovery", "accounts_continuous", "accounts_universe")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus accounts accounts_universe/
```

Expected: FAIL, one row `accounts_universe/import` with `ModuleNotFoundError: No module named
'execution_accounts.universe'`.

- [ ] **Step 3: Implement the builder**

Create `execution_accounts/universe.py`:

```python
"""Public Upbit universe reads (spec sections 5, 7 and 9): the daily snapshot builder, the odds candles and the
per-slot flag and ticker source. Every read is a fixed public GET of execution.upbit_inquiry under an explicit
inquiry_clock. Nothing here reads a key, writes a file or imports owner; only execution_launch/universe_store.py
writes the snapshot file."""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone

from core.compliance import rules
from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import CANDLES_DAYS_PATH, MARKET_ALL_PATH, candle_params, daily_candles, market_all
from execution_accounts.collector import SourceReceipt

PUBLIC_SCOPE = "public"                    # the plain receipt's account_scope (index contract, PR 1)
# ponytail: provisional body caps until the spec section 17 measurement sizes them from real answers
MAX_MARKET_ALL_BODY = 1024 * 1024
MAX_CANDLE_BODY = 256 * 1024
_MARKET_ALL_PARAMS = (("is_details", "true"),)


class UniverseReadError(ValueError):
    """A fixed refusal code; no body, market or provider text is quoted."""


def _require(condition, code):
    if not condition:
        raise UniverseReadError(code)


def _inquire(helper, *args):
    """One public helper call; any failure, after the transport's own single retry, is UNIVERSE_INQUIRY_FAILED."""
    try:
        return helper(*args)
    except Exception:
        raise UniverseReadError("UNIVERSE_INQUIRY_FAILED") from None


def _receipt(answer, path, params, cap):
    """(SourceReceipt, decoded body) of one public answer: the server time is required, the body is 1 to `cap` bytes
    and SourceReceipt.decode checks its sha256."""
    _require(type(answer) is Answer and answer.server_utc is not None, "UNIVERSE_SERVER_TIME_REQUIRED")
    _require(type(answer.raw_body) is bytes and 0 < len(answer.raw_body) <= cap, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    try:
        receipt = SourceReceipt(path=path, params=params, account_scope=PUBLIC_SCOPE,
                                received_at=answer.received_utc, server_time=answer.server_utc,
                                raw_body=answer.raw_body, sha256=answer.sha256)
        return receipt, receipt.decode()
    except (ValueError, TypeError, ArithmeticError, RecursionError):
        raise UniverseReadError("UNIVERSE_RECEIPT_INVALID") from None


def _stamp(moment):
    """ISO 8601 UTC with microseconds and Z, the text execution_control.store._utc writes."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _plain(receipt):
    """The 7-key plain receipt of core.compliance.rules (live_history's receipt shape)."""
    return {"path": receipt.path, "params": [[key, value] for key, value in receipt.params],
            "account_scope": receipt.account_scope, "received_at": _stamp(receipt.received_at),
            "server_time": _stamp(receipt.server_time),
            "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii"), "sha256": receipt.sha256}


def _candle_request(path, params):
    """(market, to, count) of one candle request the rule implies, refused unless daily_candles sends exactly it."""
    try:
        market, to, count = params[0][1], datetime.fromisoformat(params[1][1]), int(params[2][1])
        exact = path == CANDLES_DAYS_PATH and candle_params(market, to, count) == params
    except Exception:
        exact = False
    _require(exact, "UNIVERSE_REQUEST_INVALID")
    return market, to, count


def build_universe_snapshot(rule: rules.UniverseRule, day: date, *, clock) -> tuple[bytes, str]:
    """The snapshot of candle day `day` (UTC) under `rule`: one market/all read, then exactly the candle reads that
    rules.universe_requests implies for that body, in its order, all under `clock`. The receipts go to
    rules.encode_universe_snapshot in that same order, market/all at its sorted place. Returns the canonical file
    bytes and the manifest sha256 once rules.verify_universe_snapshot accepts them. Any failed read raises and nothing
    is returned; nothing is written here."""
    _require(type(rule) is rules.UniverseRule and type(day) is date and callable(clock), "UNIVERSE_INPUT_INVALID")
    with inquiry_clock(clock):
        first = _inquire(market_all)
        listing = _receipt(first, MARKET_ALL_PATH, _MARKET_ALL_PARAMS, MAX_MARKET_ALL_BODY)[0]
        receipts = []
        for path, params in rules.universe_requests(rule, first.raw_body, day):
            if (path, params) == (MARKET_ALL_PATH, _MARKET_ALL_PARAMS):
                receipts.append(listing)
                continue
            market, to, count = _candle_request(path, params)
            receipts.append(_receipt(_inquire(daily_candles, market, to, count), path, params, MAX_CANDLE_BODY)[0])
    raw, sha256 = rules.encode_universe_snapshot(rule, day, [_plain(receipt) for receipt in receipts])
    universe = rules.verify_universe_snapshot(raw, rules.universe_rule_sha256(rule))
    _require(universe.snapshot_sha256 == sha256, "UNIVERSE_SNAPSHOT_MISMATCH")
    return raw, sha256
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus accounts accounts_universe/
focus accounts accounts_guards/
```

Expected: both exit 0; three `accounts_universe` tests PASS; every `accounts_guards` test PASSes (the new file holds
no `/v1/` literal, no `request` name and imports only `Answer` and `inquiry_clock` from the transport).

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/universe.py tests/accounts_universe.py tests/accounts_guards.py tests/accounts_acceptance.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_accounts/universe.py tests/accounts_universe.py tests/accounts_guards.py tests/accounts_acceptance.py
git commit -m "$(cat <<'EOF'
Add the read-only Upbit universe snapshot builder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 3: Final daily candles for the odds batch (`daily_bars`)

**Files:**
- Modify: `execution_accounts/universe.py` (import block, constants, append)
- Test: `tests/accounts_universe.py` (import block, append)

**Interfaces:**
- Consumes (Task 1): `CANDLE_COUNT_MAX`, `CANDLES_DAYS_PATH`, `candle_params`, `daily_candles`. (Task 2): `_receipt`,
  `_inquire`, `_require`, `UniverseReadError`, `MAX_CANDLE_BODY`. (PR 1): `rules.UNIVERSE_MARKET`. (existing):
  `core.compliance.model.KST`.
- Produces (index contract): `@dataclass(frozen=True) class UniverseBars: market: str;
  bars: tuple[tuple[str, float, float], ...]; receipt_sha256: tuple[str, ...]`. The bar element type is stated here
  as the index asks: `(date ISO "YYYY-MM-DD" (UTC candle date), open KRW float, close KRW float)`, the row
  `zip(part.dates, part.open, part.close)` that `load_leg`'s `upbit_daily` path yields (`core/oddsdata/bars.py:335-336`,
  `400-402`), oldest first, one per date, both prices finite and above 0.
  `daily_bars(markets: Sequence[str], *, now: datetime, clock) -> dict[str, UniverseBars]`, keyed by market in input
  order. Window: `[Seoul date of now - 3650 days, UTC date of now)`, the `load_leg` window for a plan whose `start` is
  the Seoul date of `now`, cut at the last final crypto bar (bar d is final at 00:00 UTC of d + 1). Additions:
  `HISTORY_DAYS = 3650`; refusal codes `UNIVERSE_CANDLES_INVALID` and the Task 2 codes.

- [ ] **Step 1: Write the failing tests**

In `tests/accounts_universe.py`, replace the import block (from `from datetime import date, datetime, timedelta,
timezone` to `from tests import execution_fixtures as F`) with:

```python
import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl

from core.compliance import rules
from execution import transport
from execution_accounts import universe as U
from tests import execution_fixtures as F
```

Append:

```python


NOW = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)       # 10:00 KST: bars through 2026-11-10 are final


def bars(markets, now, server):
    with F.serve({("GET", "/v1/candles/days"): server}) as calls:
        result = U.daily_bars(markets, now=now, clock=lambda: now)
    return result, calls


def test_daily_bars_pages_back_to_the_listing_and_returns_plain_final_bars():
    server = candle_server(date(2025, 8, 18))
    result, calls = bars(["KRW-BTC"], NOW, server)
    assert [tuple(parse_qsl(c["query"])) for c in calls] == [
        (("market", "KRW-BTC"), ("to", "2026-11-11T00:00:00Z"), ("count", "200")),
        (("market", "KRW-BTC"), ("to", "2026-04-25T00:00:00Z"), ("count", "200")),
        (("market", "KRW-BTC"), ("to", "2025-10-07T00:00:00Z"), ("count", "200"))]
    got = result["KRW-BTC"]
    assert list(result) == ["KRW-BTC"] and got.market == "KRW-BTC" and len(got.bars) == 450
    assert got.bars[0] == ("2025-08-18", 100.0, 101.0) and got.bars[-1] == ("2026-11-10", 100.0, 101.0)
    assert all(type(d) is str and type(o) is float and type(c) is float for d, o, c in got.bars)
    assert got.receipt_sha256 == tuple(hashlib.sha256(server(c)[2]).hexdigest() for c in calls)


def test_daily_bars_window_ends_at_the_last_final_utc_day_and_starts_3650_days_before_the_seoul_date():
    late = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)   # 01:00 KST on 2026-11-11
    result, calls = bars(("KRW-ETH",), late, candle_server(date(2026, 11, 1)))
    assert [dict(parse_qsl(c["query"]))["to"] for c in calls] == ["2026-11-10T00:00:00Z"]
    assert [bar[0] for bar in result["KRW-ETH"].bars] == [
        (date(2026, 11, 1) + timedelta(days=n)).isoformat() for n in range(9)]
    result, calls = bars(["KRW-BTC"], NOW, candle_server(date(2010, 1, 1)))
    assert len(calls) == 19 and dict(parse_qsl(calls[-1]["query"]))["count"] == "50"
    assert len(result["KRW-BTC"].bars) == 3650 and result["KRW-BTC"].bars[0][0] == "2016-11-13"


def test_daily_bars_drops_the_rows_the_odds_loader_drops():
    rows = [candle("KRW-BTC", date(2026, 11, 11)),                       # not final at NOW: outside the window
            candle("KRW-BTC", date(2026, 11, 10)),
            candle("KRW-BTC", date(2026, 11, 10), opening=7),             # a repeated date: the first row wins
            candle("KRW-BTC", date(2026, 11, 9), opening=0),              # a price not above 0
            candle("KRW-BTC", date(2026, 11, 8), closing=-1),
            candle("KRW-BTC", date(2026, 11, 7)) | {"candle_date_time_utc": "2026-11-31T00:00:00"},
            candle("KRW-BTC", date(2026, 11, 6))]
    raw = json.dumps(rows).encode("utf-8")
    result, calls = bars(["KRW-BTC"], NOW, lambda call: (200, {"Date": BUILT_HEADER}, raw))
    assert len(calls) == 1                                                # 7 rows < 200: a short page ends paging
    assert result["KRW-BTC"].bars == (("2026-11-06", 100.0, 101.0), ("2026-11-10", 100.0, 101.0))


def test_daily_bars_refuses_malformed_pages_forged_receipts_and_bad_inputs():
    for raw in (b'{"not": "a list"}', b"[1]"):
        page = lambda call, raw=raw: (200, {"Date": BUILT_HEADER}, raw)
        with F.serve({("GET", "/v1/candles/days"): page}):
            refused(lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=lambda: NOW), "UNIVERSE_CANDLES_INVALID")
    forged = transport.Answer(body=[], server_utc=NOW, received_utc=NOW, sha256="0" * 64, raw_body=b"[]")
    with patch.object(U, "daily_candles", return_value=forged):
        refused(lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=lambda: NOW), "UNIVERSE_RECEIPT_INVALID")
    for call in (lambda: U.daily_bars([], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC", "KRW-BTC"], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-KRW"], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars("KRW-BTC", now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC"], now=NOW.replace(tzinfo=None), clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=None)):
        refused(call, "UNIVERSE_INPUT_INVALID")


def test_universe_module_imports_only_public_helpers_and_no_odds_loader_data_or_config():
    """Spec 9: no core.oddsdata, data.* or config import. Spec 7: the source is keyless, so from the execution
    package it takes only the transport's Answer and inquiry_clock and the public upbit_inquiry helpers, never the
    keyed snapshot or current_terms."""
    tree = ast.parse(Path(U.__file__).read_text(encoding="utf-8"))
    plain = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    named = {(node.module or "", alias.name) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
             for alias in node.names}
    modules = plain | {module for module, _name in named}
    assert not {m for m in modules if m.split(".")[0] in ("data", "config") or m.startswith("core.oddsdata")}, modules
    public = {("execution.transport", "Answer"), ("execution.transport", "inquiry_clock")} | {
        ("execution.upbit_inquiry", name) for name in ("CANDLE_COUNT_MAX", "CANDLES_DAYS_PATH", "MARKET_ALL_PATH",
                                                        "candle_params", "daily_candles", "market_all", "tickers")}
    assert {pair for pair in named if pair[0].split(".")[0] == "execution"} <= public, named
    assert not {m for m in plain if m.split(".")[0] == "execution"}, plain
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus accounts accounts_universe/test_daily_bars
```

Expected: FAIL, all four `test_daily_bars_*` tests with `AttributeError: module 'execution_accounts.universe' has no
attribute 'daily_bars'`.

- [ ] **Step 3: Implement `daily_bars`**

In `execution_accounts/universe.py`, replace the import block (from `import base64` to
`from execution_accounts.collector import SourceReceipt`) with:

```python
import base64
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math

from core.compliance import rules
from core.compliance.model import KST
from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import (CANDLE_COUNT_MAX, CANDLES_DAYS_PATH, MARKET_ALL_PATH, candle_params,
                                     daily_candles, market_all)
from execution_accounts.collector import SourceReceipt
```

After the line `_MARKET_ALL_PARAMS = (("is_details", "true"),)` insert:

```python
HISTORY_DAYS = 3650                        # core/oddsdata/bars.py HISTORY_DAYS, written out: no core.oddsdata import
_MAX_PAGES = HISTORY_DAYS // CANDLE_COUNT_MAX + 2
```

Append at the end of the file:

```python


@dataclass(frozen=True)
class UniverseBars:
    """One market's final daily bars, oldest first, as load_leg's upbit_daily rows: (UTC candle date ISO, open KRW,
    close KRW), both prices finite and above 0, one per date; and the sha256 of every candle page read, in order."""
    market: str
    bars: tuple[tuple[str, float, float], ...]
    receipt_sha256: tuple[str, ...]


def daily_bars(markets: Sequence[str], *, now: datetime, clock) -> dict[str, UniverseBars]:
    """Final daily bars of each market over [Seoul date of `now` - HISTORY_DAYS, UTC date of `now`): load_leg's
    window for a plan starting on that Seoul date, where a bar dated d is final at 00:00 UTC of d + 1. Pages
    daily_candles backwards under `clock`, CANDLE_COUNT_MAX rows at most a page, until a short page, a page with no
    new date or the window start."""
    _require(type(markets) in (list, tuple) and len(markets) > 0
             and all(type(m) is str and rules.UNIVERSE_MARKET.fullmatch(m) is not None and m != "KRW-KRW"
                     for m in markets)
             and len(set(markets)) == len(markets)
             and type(now) is datetime and now.utcoffset() is not None and callable(clock), "UNIVERSE_INPUT_INVALID")
    start = now.astimezone(KST).date() - timedelta(days=HISTORY_DAYS)
    end = now.astimezone(timezone.utc).date()
    with inquiry_clock(clock):
        return {market: _market_bars(market, start, end) for market in markets}


def _market_bars(market, start, end):
    seen, digests, before = {}, [], end
    for _ in range(_MAX_PAGES):
        count = min(CANDLE_COUNT_MAX, (before - start).days)
        if count < 1:
            break
        to = datetime(before.year, before.month, before.day, tzinfo=timezone.utc)
        params = candle_params(market, to, count)
        receipt, page = _receipt(_inquire(daily_candles, market, to, count), CANDLES_DAYS_PATH, params,
                                 MAX_CANDLE_BODY)
        _require(type(page) is list, "UNIVERSE_CANDLES_INVALID")
        digests.append(receipt.sha256)
        fresh = []
        for row in page:
            day, opening, closing = _candle(row)
            if day is None or day in seen:
                continue
            seen[day] = (day, opening, closing) if opening and closing else None
            fresh.append(day)
        if not fresh or len(page) < count:
            break
        before = date.fromisoformat(min(fresh))
    low, high = start.isoformat(), end.isoformat()
    bars = tuple(seen[day] for day in sorted(seen) if seen[day] is not None and low <= day < high)
    return UniverseBars(market=market, bars=bars, receipt_sha256=tuple(digests))


def _candle(row):
    """(date, open, close) of one candle row: the date None unless candle_date_time_utc starts with an ISO day, a
    price None unless it is a finite JSON number above 0 (core/oddsdata/bars.py _make_part)."""
    _require(type(row) is dict, "UNIVERSE_CANDLES_INVALID")
    return _day(row.get("candle_date_time_utc")), _price(row.get("opening_price")), _price(row.get("trade_price"))


def _day(stamp):
    text = stamp[:10] if type(stamp) is str else ""
    try:
        return text if date.fromisoformat(text).isoformat() == text else None
    except ValueError:
        return None


def _price(value):
    if type(value) not in (int, Decimal):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus accounts accounts_universe/
focus accounts accounts_guards/
```

Expected: both exit 0 (eight `accounts_universe` tests, every guard test PASS).

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/universe.py tests/accounts_universe.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_accounts/universe.py tests/accounts_universe.py
git commit -m "$(cat <<'EOF'
Add final daily Upbit candles for the universe odds batch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 4: Keyless per-slot flag and ticker source

**Files:**
- Modify: `execution_accounts/universe.py` (import block, constants, append)
- Test: `tests/accounts_universe.py` (append)

**Interfaces:**
- Consumes (Task 1): `market_all() -> Answer`, `tickers(markets) -> Answer`. (Task 2): `_require`,
  `MAX_MARKET_ALL_BODY`. (PR 1): `rules.market_flags(body: bytes) -> dict[str, str]`. (existing):
  `execution_accounts.collector.number`.
- Produces (index contract): `@dataclass(frozen=True) class FlagRead: ok: bool; received_at: datetime | None;
  sha256: str | None; flags: Mapping[str, str]`; `@dataclass(frozen=True) class TickerRead: ok: bool;
  received_at: datetime | None; sha256: str | None; prices: Mapping[str, tuple[Decimal, datetime]]` (trade price,
  aware UTC trade time); `class UniverseSlotSource: read_flags() -> FlagRead; read_tickers(markets: Sequence[str]) ->
  TickerRead`, never raising for a failed read. Additions: `UniverseSlotSource` is a frozen dataclass with one field
  `clock: Callable` (the caller's clock, as `E1UpbitQuoteSource` takes it; construction refuses a non-callable with
  `UNIVERSE_CLOCK_REQUIRED`); `MAX_TICKER_BODY` (provisional cap). `flags` and `prices` are read-only
  `MappingProxyType`s; a failed read has `ok=False`, both times and digests `None` and an empty mapping. A ticker body
  with a row that is not an object, names a market not requested or twice, or has no positive price or integer
  `trade_timestamp` fails the whole read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/accounts_universe.py`:

```python


TRADE_MS = int(BUILT.timestamp()) * 1000


def ticker(name, price):
    """One ticker row."""
    return {"market": name, "trade_price": price, "trade_timestamp": TRADE_MS, "timestamp": TRADE_MS}


def answered(raw):
    return lambda call: (200, {"Date": BUILT_HEADER}, raw)


def unavailable(read):
    mapping = read.flags if type(read) is U.FlagRead else read.prices
    return read.ok is False and read.received_at is None and read.sha256 is None and dict(mapping) == {}


def test_slot_source_reads_flags_and_prices_with_one_public_get_each():
    ticker_raw = json.dumps([ticker("KRW-BTC", 101), ticker("KRW-ETH", 2.5)]).encode("utf-8")
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    with F.serve({("GET", "/v1/market/all"): answered(MARKET_ALL_RAW),
                  ("GET", "/v1/ticker"): answered(ticker_raw)}) as calls:
        flags, prices = source.read_flags(), source.read_tickers(("KRW-BTC", "KRW-ETH"))
    assert [c["url"] for c in calls] == ["https://api.upbit.com/v1/market/all?is_details=true",
                                         "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH"]
    assert all("authorization" not in {k.lower() for k in c["headers"]} for c in calls)
    assert flags.ok and flags.received_at == BUILT and flags.sha256 == hashlib.sha256(MARKET_ALL_RAW).hexdigest()
    assert dict(flags.flags) == {"KRW-BTC": "unflagged", "KRW-ETH": "unflagged", "KRW-USDT": "unflagged",
                                 "KRW-XYZ": "caution"}
    assert prices.ok and prices.received_at == BUILT and prices.sha256 == hashlib.sha256(ticker_raw).hexdigest()
    assert dict(prices.prices) == {"KRW-BTC": (Decimal(101), BUILT), "KRW-ETH": (Decimal("2.5"), BUILT)}


def test_slot_source_failures_are_unavailable_reads_never_exceptions():
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    error = lambda call: (500, {"Date": BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with F.serve({("GET", "/v1/market/all"): error, ("GET", "/v1/ticker"): error}) as calls:
        assert unavailable(source.read_flags()) and unavailable(source.read_tickers(["KRW-BTC"]))
    assert len(calls) == 4                                    # each GET once more after the 5xx, nothing else
    with F.serve({("GET", "/v1/market/all"): answered(b'{"market": "KRW-BTC"}')}):
        assert unavailable(source.read_flags())
    for markets in ([], ["KRW-BTC", "KRW-BTC"], ["KRW-btc"], "KRW-BTC"):
        assert unavailable(source.read_tickers(markets))      # refused before any send
    for rows in ([ticker("KRW-ETH", 1)], [ticker("KRW-BTC", 1), ticker("KRW-BTC", 1)], [ticker("KRW-BTC", 0)],
                 [ticker("KRW-BTC", 1) | {"trade_timestamp": "1"}], [{"market": "KRW-BTC"}], {"KRW-BTC": 1}, ["row"]):
        with F.serve({("GET", "/v1/ticker"): answered(json.dumps(rows).encode("utf-8"))}):
            assert unavailable(source.read_tickers(["KRW-BTC"])), rows
    with F.serve({("GET", "/v1/ticker"): answered(json.dumps([ticker("KRW-BTC", 1)]).encode("utf-8"))}), \
            patch.object(U, "MAX_TICKER_BODY", 8):
        assert unavailable(source.read_tickers(["KRW-BTC"]))
    with F.serve({("GET", "/v1/market/all"): answered(MARKET_ALL_RAW)}), patch.object(U, "MAX_MARKET_ALL_BODY", 8):
        assert unavailable(source.read_flags())
    refused(lambda: U.UniverseSlotSource(clock=None), "UNIVERSE_CLOCK_REQUIRED")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus accounts accounts_universe/test_slot_source
```

Expected: FAIL, both tests with `AttributeError: module 'execution_accounts.universe' has no attribute
'UniverseSlotSource'`.

- [ ] **Step 3: Implement the source**

In `execution_accounts/universe.py`, replace the import block (from `import base64` to
`from execution_accounts.collector import SourceReceipt`) with:

```python
import base64
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import math
from types import MappingProxyType

from core.compliance import rules
from core.compliance.model import KST
from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import (CANDLE_COUNT_MAX, CANDLES_DAYS_PATH, MARKET_ALL_PATH, candle_params,
                                     daily_candles, market_all, tickers)
from execution_accounts.collector import SourceReceipt, number
```

Replace the line `MAX_CANDLE_BODY = 256 * 1024` with:

```python
MAX_CANDLE_BODY = 256 * 1024
MAX_TICKER_BODY = 1024 * 1024
```

Replace the line `_MAX_PAGES = HISTORY_DAYS // CANDLE_COUNT_MAX + 2` with:

```python
_MAX_PAGES = HISTORY_DAYS // CANDLE_COUNT_MAX + 2
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
```

Append at the end of the file:

```python


@dataclass(frozen=True)
class FlagRead:
    """One market/all?is_details=true read: every KRW market in it with its flag class, or ok=False and nothing."""
    ok: bool
    received_at: datetime | None
    sha256: str | None
    flags: Mapping[str, str]


@dataclass(frozen=True)
class TickerRead:
    """One ticker read: each returned market's (trade price, trade time), or ok=False and nothing."""
    ok: bool
    received_at: datetime | None
    sha256: str | None
    prices: Mapping[str, tuple[Decimal, datetime]]


_NO_FLAGS = FlagRead(ok=False, received_at=None, sha256=None, flags=MappingProxyType({}))
_NO_TICKERS = TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))


@dataclass(frozen=True)
class UniverseSlotSource:
    """The keyless per-slot reads of spec section 7, steps 4 and 5. A failed read is an ok=False result, never an
    exception, so the coordinator records it as unavailable and blocks buys only."""
    clock: Callable = field(repr=False)

    def __post_init__(self):
        _require(callable(self.clock), "UNIVERSE_CLOCK_REQUIRED")

    def read_flags(self) -> FlagRead:
        """One market/all read under the clock: each KRW market's flag class (rules.market_flags)."""
        try:
            with inquiry_clock(self.clock):
                answer = market_all()
            _require(type(answer) is Answer and 0 < len(answer.raw_body) <= MAX_MARKET_ALL_BODY,
                     "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
            flags = MappingProxyType(dict(rules.market_flags(answer.raw_body)))
        except Exception:
            return _NO_FLAGS
        return FlagRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, flags=flags)

    def read_tickers(self, markets: Sequence[str]) -> TickerRead:
        """One ticker read of `markets` (distinct KRW markets) under the clock: each returned market's trade price and
        trade time."""
        try:
            with inquiry_clock(self.clock):
                answer = tickers(markets)
            _require(type(answer) is Answer and 0 < len(answer.raw_body) <= MAX_TICKER_BODY,
                     "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
            prices = MappingProxyType(_ticker_prices(answer.raw_body, markets))
        except Exception:
            return _NO_TICKERS
        return TickerRead(ok=True, received_at=answer.received_utc, sha256=answer.sha256, prices=prices)


def _ticker_prices(raw, markets):
    """Each returned market's (trade price, trade time); a row that is not an object, names a market not requested
    or twice, or has no positive price or integer trade_timestamp refuses the whole read."""
    rows = json.loads(raw.decode("utf-8"), parse_float=Decimal)
    _require(type(rows) is list, "UNIVERSE_TICKERS_INVALID")
    wanted, prices = set(markets), {}
    for row in rows:
        _require(type(row) is dict and row.get("market") in wanted and row["market"] not in prices
                 and type(row.get("trade_timestamp")) is int, "UNIVERSE_TICKERS_INVALID")
        prices[row["market"]] = (number(row.get("trade_price"), positive=True, json_number=True),
                                 _EPOCH + timedelta(milliseconds=row["trade_timestamp"]))
    return prices
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus accounts accounts_universe/
focus accounts accounts_guards/
```

Expected: both exit 0 (ten `accounts_universe` tests, every guard test PASS).

- [ ] **Step 5: Commit**

```bash
git add execution_accounts/universe.py tests/accounts_universe.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_accounts/universe.py tests/accounts_universe.py
git commit -m "$(cat <<'EOF'
Add the keyless per-slot flag and ticker source

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 5: Write-once universe snapshot store

**Files:**
- Create: `execution_launch/universe_store.py`
- Create: `tests/launch_universe_store.py`
- Modify: `tests/launch_guards.py:36` (constant), `:65-66` (`PINNED_WRITES` entry), after `:531` (writer test)
- Modify: `tests/launch_acceptance.py:9-15` (`MODULES`)

**Interfaces:**
- Consumes (PR 1): `owner.universe_dir(day: date) -> Path`, `owner.universe_path(day: date, sha256: str) -> Path`
  (`<state root>/universe/<YYYY-MM-DD>/<sha256>.json`). (existing): `core.isolation.checked_target`,
  `state_root`.
- Produces (index contract): `write_snapshot(raw: bytes, day: date, sha256: str) -> Path`. Additions:
  `class UniverseStoreError(ValueError)` with codes `UNIVERSE_STORE_INPUT_INVALID`, `UNIVERSE_STORE_PATH_REFUSED`,
  `UNIVERSE_SNAPSHOT_EXISTS`, `UNIVERSE_STORE_REFUSED`. Deviation from the contract's "`O_EXCL`" note: `O_EXCL`
  creates the temporary file; the final name is reached by `os.rename` after an existence check (Windows refuses an
  existing target). `os.link` is not used because `core.isolation.state_root()` refuses any hard link under the
  root (`scan_links`), so a crash between link and unlink would lock out every later `state_root()` call.

- [ ] **Step 1: Write the failing tests, the pinned write shapes and register the module**

Create `tests/launch_universe_store.py`:

```python
"""The universe snapshot store and its command (spec section 5): temporary state only and synthetic public answers
through the fake transport._send; no venue call, key or real home."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from core.compliance import owner
from execution_launch import universe_store as US
from tests import accounts_universe as AU

SHA_A, SHA_B = "a" * 64, "b" * 64


def refused(call, code):
    try:
        call()
    except US.UniverseStoreError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError(f"not refused: {code}")


def names():
    return sorted(path.name for path in owner.universe_dir(AU.DAY).iterdir())


def test_a_rebuild_adds_a_file_and_leaves_the_earlier_one_intact():
    first = US.write_snapshot(b"first", AU.DAY, SHA_A)
    second = US.write_snapshot(b"second", AU.DAY, SHA_B)
    assert first == owner.universe_path(AU.DAY, SHA_A) and second == owner.universe_path(AU.DAY, SHA_B)
    assert first.read_bytes() == b"first" and second.read_bytes() == b"second"
    assert names() == [SHA_A + ".json", SHA_B + ".json"]


def test_an_existing_snapshot_is_refused_and_never_replaced():
    path = US.write_snapshot(b"first", AU.DAY, SHA_A)
    refused(lambda: US.write_snapshot(b"other", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert path.read_bytes() == b"first" and names() == [SHA_A + ".json"]


def test_a_snapshot_that_appears_during_the_write_is_kept_and_the_temporary_file_removed():
    """Windows rename refuses an existing name (the owner PC); see the ponytail note in write_snapshot for POSIX."""
    if os.name != "nt":
        return
    real = US.checked_target

    def racing(path, what="path", *, within=None):
        if what == "universe snapshot":
            Path(path).write_bytes(b"racer")
        return real(path, what, within=within)

    with patch.object(US, "checked_target", racing):
        refused(lambda: US.write_snapshot(b"mine", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert owner.universe_path(AU.DAY, SHA_A).read_bytes() == b"racer" and names() == [SHA_A + ".json"]


def test_bad_arguments_are_refused_before_any_write():
    for raw, day, sha256 in ((b"", AU.DAY, SHA_A), ("text", AU.DAY, SHA_A), (b"x", "2026-11-11", SHA_A),
                             (b"x", AU.DAY, "A" * 64), (b"x", AU.DAY, "a" * 63), (b"x", AU.DAY, None)):
        refused(lambda: US.write_snapshot(raw, day, sha256), "UNIVERSE_STORE_INPUT_INVALID")
    assert not owner.universe_dir(AU.DAY).parent.exists()
```

In `tests/launch_guards.py`, after line 36 (`CONTINUOUS_ARCHIVE = "execution_launch/continuous_archive.py"`) insert:

```python
UNIVERSE_STORE = "execution_launch/universe_store.py"
```

Replace lines 65-66 (the closing `    ),` of the `CONTINUOUS_ARCHIVE` entry and the closing `}` of `PINNED_WRITES`):

```python
    ),
}
```

with:

```python
    ),
    UNIVERSE_STORE: (
        'checked_target(directory, "universe directory", within=root).mkdir(mode=0o700, parents=True, exist_ok=True)',
        'os.open(checked_target(directory / name, "universe temporary file", within=directory), '
        'os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)',
        'os.fdopen(descriptor, "wb")',
        'os.rename(checked_target(directory / name, "universe temporary file", within=directory), '
        'checked_target(target, "universe snapshot", within=directory))',
        'os.unlink(checked_target(directory / name, "universe temporary file", within=directory))',
    ),
}
```

After line 531 (the last line of `test_continuous_archive_writes_are_exact_and_cannot_migrate_into_pure_modules`)
insert:

```python


def test_universe_store_writes_are_exact_and_cannot_migrate():
    source = (ROOT / UNIVERSE_STORE).read_text(encoding="utf-8")
    assert not problems(source, UNIVERSE_STORE), problems(source, UNIVERSE_STORE)
    calls = {ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)}
    assert _PINNED_WRITE_TREES[UNIVERSE_STORE] <= calls, "a pinned universe write shape is unused"
    write = "write outside pinned writer"
    for shape in PINNED_WRITES[UNIVERSE_STORE]:
        assert not problems(shape, UNIVERSE_STORE), shape
        for relative in ("", STUDY, "execution_launch/nested/universe_store.py", "execution_network/universe_store.py"):
            assert write in problems(shape, relative), (shape, relative)
    create, rename = PINNED_WRITES[UNIVERSE_STORE][1], PINNED_WRITES[UNIVERSE_STORE][3]
    for altered in (create.replace("os.O_EXCL", "os.O_TRUNC"), create.replace(" | os.O_EXCL", ""),
                    create.replace("within=directory", "within=other"), create.replace("0o600", "0o644"),
                    rename.replace("os.rename", "os.replace"), rename.replace("within=directory)", "within=root)"),
                    "os.replace(source, target)", "os.rename(source, target)", "os.link(source, target)",
                    "path.write_bytes(raw)", "os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)"):
        assert write in problems(altered, UNIVERSE_STORE), altered
    for extra in ("import requests", "owner.load_context(now)", "os.environ['TRADEGEN_HOME']", 'P = "/v1/ticker"'):
        assert problems(extra, UNIVERSE_STORE), extra
```

In `tests/launch_acceptance.py`, replace line 15:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal")
```

with:

```python
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal",
           "launch_universe_store")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_store/
focus launch launch_guards/test_universe_store_writes
```

Expected: FAIL, `launch_universe_store/import` with `ModuleNotFoundError: No module named
'execution_launch.universe_store'`, and the guard test with `FileNotFoundError` for
`execution_launch/universe_store.py`.

- [ ] **Step 3: Implement the writer**

Create `execution_launch/universe_store.py`:

```python
"""The daily Upbit universe snapshot store (spec section 5). write_snapshot writes one snapshot once, content
addressed, as owner.universe_path(day, sha256), through a new temporary file, fsync and a rename to a name that does
not exist yet. It never replaces a file, so a rebuild adds a file and never changes one that a session or history
row already names."""
from __future__ import annotations

import contextlib
from datetime import date
import os
from pathlib import Path
import re

from core.compliance import owner
from core.isolation import checked_target, state_root

_SHA = re.compile(r"[0-9a-f]{64}")
_FLAGS = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)


class UniverseStoreError(ValueError):
    """A fixed refusal code; no path or body is quoted."""


def _require(condition, code):
    if not condition:
        raise UniverseStoreError(code)


def write_snapshot(raw: bytes, day: date, sha256: str) -> Path:
    """Write `raw` once as owner.universe_path(day, sha256) and return that path. An existing snapshot is refused
    (UNIVERSE_SNAPSHOT_EXISTS) and kept; any failure removes the temporary file. The caller verified `raw`; this
    function checks only the shape of its arguments."""
    _require(type(raw) is bytes and len(raw) > 0 and type(day) is date and type(sha256) is str
             and _SHA.fullmatch(sha256) is not None, "UNIVERSE_STORE_INPUT_INVALID")
    try:
        root = state_root()
        directory, target = owner.universe_dir(day), owner.universe_path(day, sha256)
        _require(target.parent == directory, "UNIVERSE_STORE_PATH_REFUSED")
        _require(not target.exists(), "UNIVERSE_SNAPSHOT_EXISTS")
        checked_target(directory, "universe directory", within=root).mkdir(mode=0o700, parents=True, exist_ok=True)
        name = "." + sha256 + "." + os.urandom(6).hex() + ".tmp"
        descriptor = os.open(checked_target(directory / name, "universe temporary file", within=directory),
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FLAGS, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            # ponytail: Windows rename refuses an existing name; a POSIX rename would replace a file that appeared
            # since the check above (the same content-addressed bytes). Use link plus unlink if POSIX ever matters.
            os.rename(checked_target(directory / name, "universe temporary file", within=directory),
                      checked_target(target, "universe snapshot", within=directory))
        except BaseException:
            with contextlib.suppress(OSError, RuntimeError):
                os.unlink(checked_target(directory / name, "universe temporary file", within=directory))
            raise
    except UniverseStoreError:
        raise
    except FileExistsError:
        raise UniverseStoreError("UNIVERSE_SNAPSHOT_EXISTS") from None
    except (OSError, RuntimeError, ValueError):
        raise UniverseStoreError("UNIVERSE_STORE_REFUSED") from None
    return target
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_store/
focus launch launch_guards/
```

Expected: both exit 0; four `launch_universe_store` tests PASS (the race test returns early off Windows); every
`launch_guards` test PASSes, including `test_launch_suite_is_complete_registered_and_import_errors_fail`.

- [ ] **Step 5: Commit**

```bash
git add execution_launch/universe_store.py tests/launch_universe_store.py tests/launch_guards.py tests/launch_acceptance.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/universe_store.py tests/launch_universe_store.py tests/launch_guards.py tests/launch_acceptance.py
git commit -m "$(cat <<'EOF'
Add the write-once universe snapshot store

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 6: `snapshot --state-root <root>` command

**Files:**
- Modify: `execution_launch/universe_store.py` (docstring, import block, constant, append)
- Test: `tests/launch_universe_store.py` (import block, append)

**Interfaces:**
- Consumes (Task 2): `build_universe_snapshot(rule, day, *, clock) -> tuple[bytes, str]`, `UniverseReadError`.
  (Task 5): `write_snapshot`, `UniverseStoreError`. (PR 1): `rules.UniverseRule`, `rules.UniverseError`,
  `Venue.universe_rule`. (existing): `owner.latest_snapshot() -> ApprovedState | None` (`.venues.venues["upbit"]`),
  `state_root()`.
- Produces (index contract): `main(argv=None) -> int` for `snapshot --state-root <root>`: prints one JSON line,
  `{"command": "snapshot", "written": true, "day": "<YYYY-MM-DD>", "snapshot_sha256": "<hex>"}` and returns 0, or
  `{"command": "snapshot", "written": false, "reasons": ["<CODE>"]}` and returns 2 with nothing written. Codes:
  `UNIVERSE_ARGUMENTS_INVALID`, `UNIVERSE_STATE_ROOT_MISMATCH`, `UNIVERSE_NO_RULE`, every `UniverseReadError`,
  `UniverseStoreError` and `rules.UniverseError` code, else `UNIVERSE_SNAPSHOT_REFUSED`. Additions: `_active_rule()`
  reads the rule from `owner.latest_snapshot()`, the newest approved state on disk, because `execution_launch` may not
  reference `load_context` (`tests/launch_guards.py` `PRIVILEGED_REFERENCES`). A file built under a rule that is not
  in force is harmless: the read-back (PR 3) only uses snapshots whose rule sha256 matches the active signed rule.
  The candle day is the UTC date of the wall clock at the start of the run. The root check compares
  `Path(<root>)` with `state_root().absolute()` (TRADEGEN_HOME, else `~/.tradegen`), as `tools/owner/launch.py:111-115`
  does, because `execution_launch` may not read `os.environ`.

- [ ] **Step 1: Write the failing tests**

In `tests/launch_universe_store.py`, replace the import block (from `import os` to
`from tests import accounts_universe as AU`) with:

```python
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner, rules
from core.isolation import state_root
from execution_launch import universe_store as US
from tests import accounts_universe as AU
from tests import execution_fixtures as EF
```

Append:

```python


def run(argv):
    out = StringIO()
    with redirect_stdout(out):
        code = US.main(argv)
    return code, json.loads(out.getvalue())


def root_args():
    return ["snapshot", "--state-root", str(state_root().absolute())]


def not_written(reason):
    return 2, {"command": "snapshot", "written": False, "reasons": [reason]}


def test_command_writes_one_verified_snapshot_for_today():
    with patch.object(US, "_active_rule", return_value=AU.RULE), patch.object(US, "_wall_clock", return_value=AU.BUILT), \
            EF.serve(AU.routes()) as calls:
        code, out = run(root_args())
    assert code == 0 and out["written"] is True and out["day"] == "2026-11-11", out
    path = owner.universe_path(AU.DAY, out["snapshot_sha256"])
    universe = rules.verify_universe_snapshot(path.read_bytes(), rules.universe_rule_sha256(AU.RULE))
    assert universe.snapshot_sha256 == out["snapshot_sha256"] and len(calls) == 5
    assert names() == [path.name]


def test_command_refuses_another_root_or_bad_arguments_before_any_read():
    root = state_root().absolute()
    for argv, reason in ((["snapshot", "--state-root", str(root / "other")], "UNIVERSE_STATE_ROOT_MISMATCH"),
                         (["snapshot", "--state-root", "relative-root"], "UNIVERSE_STATE_ROOT_MISMATCH"),
                         (["snapshot"], "UNIVERSE_ARGUMENTS_INVALID"),
                         (["build", "--state-root", str(root)], "UNIVERSE_ARGUMENTS_INVALID"),
                         (["snapshot", "--state-root", str(root), "--force"], "UNIVERSE_ARGUMENTS_INVALID")):
        with patch.object(US, "_active_rule", return_value=AU.RULE):
            assert run(argv) == not_written(reason), argv
    assert not owner.universe_dir(AU.DAY).parent.exists()


def test_command_writes_nothing_when_a_read_fails():
    error = lambda call: (500, {"Date": AU.BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with patch.object(US, "_active_rule", return_value=AU.RULE), patch.object(US, "_wall_clock", return_value=AU.BUILT), \
            EF.serve(AU.routes(error)):
        assert run(root_args()) == not_written("UNIVERSE_INQUIRY_FAILED")
    assert not owner.universe_dir(AU.DAY).parent.exists()


def test_command_takes_the_rule_from_the_newest_approved_venue_facts():
    assert run(root_args()) == not_written("UNIVERSE_NO_RULE")          # the temporary home holds no approved state

    def state(rule):
        return SimpleNamespace(venues=SimpleNamespace(venues={"upbit": SimpleNamespace(universe_rule=rule)}))

    with patch.object(owner, "latest_snapshot", return_value=state(AU.RULE)):
        assert US._active_rule() == AU.RULE
    for value in (state(None), SimpleNamespace(venues=None), SimpleNamespace(venues=SimpleNamespace(venues={}))):
        with patch.object(owner, "latest_snapshot", return_value=value):
            refused(US._active_rule, "UNIVERSE_NO_RULE")
    assert US._code(RuntimeError("C:/private/path")) == "UNIVERSE_SNAPSHOT_REFUSED"
    assert US._code(US.UniverseStoreError("UNIVERSE_SNAPSHOT_EXISTS")) == "UNIVERSE_SNAPSHOT_EXISTS"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_universe_store/test_command
```

Expected: FAIL, all four `test_command_*` tests with an `AttributeError` naming `_active_rule` (raised by
`patch.object`) or `main`.

- [ ] **Step 3: Implement the command**

In `execution_launch/universe_store.py`, replace the module docstring (the first four lines) with:

```python
"""The daily Upbit universe snapshot store and its command (spec section 5).

    python -m execution_launch.universe_store snapshot --state-root <root>

builds the snapshot of today's UTC candle day under the Upbit universe rule of the newest approved state and writes
it with write_snapshot. It refuses unless <root> is this process's state root (TRADEGEN_HOME), and a failed read or
build writes nothing. write_snapshot writes one snapshot once, content addressed, as owner.universe_path(day,
sha256), through a new temporary file, fsync and a rename to a name that does not exist yet. It never replaces a
file, so a rebuild adds a file and never changes one that a session or history row already names. The owner
registers the command in Windows Task Scheduler (09:12 KST, retry 09:27 KST); no code creates the task."""
```

Replace the import block (from `import contextlib` to `from core.isolation import checked_target, state_root`) with:

```python
import contextlib
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from core.compliance import owner, rules
from core.isolation import checked_target, state_root
from execution_accounts.universe import UniverseReadError, build_universe_snapshot
```

After the line `_FLAGS = getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOINHERIT", 0)`
insert:

```python
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
```

Append at the end of the file:

```python


def _wall_clock() -> datetime:
    """The PC clock, aware UTC: the candle day and every receipt's received_at."""
    return datetime.now(timezone.utc)


def _active_rule() -> rules.UniverseRule:
    """The Upbit universe rule of the newest approved state on disk; UNIVERSE_NO_RULE when there is none.
    execution_launch never references load_context, so the approved venue facts are read directly."""
    state = owner.latest_snapshot()
    venue = None if state is None or state.venues is None else state.venues.venues.get("upbit")
    rule = None if venue is None else venue.universe_rule
    _require(type(rule) is rules.UniverseRule, "UNIVERSE_NO_RULE")
    return rule


def _code(exc: BaseException) -> str:
    """A refusal code worth printing: the fixed code of a universe refusal, else one generic code (no text leaks)."""
    text = str(exc)
    known = isinstance(exc, (UniverseStoreError, UniverseReadError, rules.UniverseError))
    return text if known and _CODE.fullmatch(text) is not None else "UNIVERSE_SNAPSHOT_REFUSED"


def main(argv=None) -> int:
    """`snapshot --state-root <root>`: build today's (UTC) snapshot and write it once. Prints one JSON line; returns
    0 when a file was written, 2 when nothing was written."""
    args = sys.argv[1:] if argv is None else list(argv)
    try:
        _require(len(args) == 3 and args[0] == "snapshot" and args[1] == "--state-root",
                 "UNIVERSE_ARGUMENTS_INVALID")
        explicit = Path(args[2])
        _require(explicit.is_absolute() and explicit == state_root().absolute(), "UNIVERSE_STATE_ROOT_MISMATCH")
        rule = _active_rule()
        day = _wall_clock().astimezone(timezone.utc).date()
        raw, sha256 = build_universe_snapshot(rule, day, clock=_wall_clock)
        write_snapshot(raw, day, sha256)
    except Exception as exc:
        print(json.dumps({"command": "snapshot", "written": False, "reasons": [_code(exc)]}, sort_keys=True))
        return 2
    print(json.dumps({"command": "snapshot", "written": True, "day": day.isoformat(), "snapshot_sha256": sha256},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
focus launch launch_universe_store/
focus launch launch_guards/
```

Expected: both exit 0 (eight `launch_universe_store` tests; every guard test, including
`test_universe_store_writes_are_exact_and_cannot_migrate`, PASS).

- [ ] **Step 5: Commit**

```bash
git add execution_launch/universe_store.py tests/launch_universe_store.py
diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol)
"$PY" -X utf8 -c "import sys; bad = [p for p in sys.argv[1:] if b'\r' in open(p, 'rb').read()]; print(bad); sys.exit(1 if bad else 0)" execution_launch/universe_store.py tests/launch_universe_store.py
git commit -m "$(cat <<'EOF'
Add the universe snapshot command with its state-root check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: `diff` prints nothing, the check prints `[]`, the commit succeeds.

---

### Task 7: Guards, full suite and pull request

**Files:**
- None changed. Runs the guard modules and the full suite, then opens the PR.

**Interfaces:**
- Consumes: everything above. Produces: one open PR for the owner to review and merge.

- [ ] **Step 1: Run every guard module**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: each exits 0. `renewal_boundaries` runs inside `control_guards`
(`control_guards/test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces`). A guard FAIL is fixed in
the task that caused it, never by regenerating a pin.

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
```

Expected: exit 0 and no FAIL row in the summary (NOT_RUN rows are allowed). It takes several minutes.

- [ ] **Step 3: Check the branch diff and push**

```bash
git status --short
diff <(git diff --stat origin/main...HEAD) <(git diff --stat --ignore-cr-at-eol origin/main...HEAD)
git push -u origin claude/universe-pr2-data
```

Expected: `git status --short` prints nothing, `diff` prints nothing, the push succeeds.

- [ ] **Step 4: Open the pull request (the owner merges; never merge)**

```bash
gh pr create --base main --head claude/universe-pr2-data \
  --title "Upbit KRW universe PR 2: public data readers, snapshot builder and writer" \
  --body "$(cat <<'EOF'
## Summary

Spec `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` sections 5 (snapshot builder and writer),
7 (the keyless per-slot flag and ticker source of steps 4 and 5) and 9 (`daily_bars` for the odds batch).

- `execution/upbit_inquiry.py`: fixed public helpers `market_all`, `daily_candles`, `orderbook_instruments`, `tickers`
  and `candle_params`; `/v1/market/all` and `/v1/candles/days` added to `ENDPOINTS` and `PUBLIC`.
- `execution_accounts/universe.py` (read-only, keyless): `build_universe_snapshot`, `daily_bars` (plain
  `(date, open, close)` bars plus receipt sha256s), `UniverseSlotSource` (`read_flags`, `read_tickers`, never raising).
- `execution_launch/universe_store.py`: `write_snapshot` (temporary file with O_EXCL, fsync, rename to a name that does
  not exist, never replaces) and `python -m execution_launch.universe_store snapshot --state-root <root>`.
- Guard pins updated by hand: `tests/execution_guards.py` (allowlist), `tests/renewal_boundaries.py` (surface of
  `execution/upbit_inquiry.py`), `tests/accounts_guards.py` (`TRANSPORT_IMPORTS["universe.py"]`),
  `tests/launch_guards.py` (`PINNED_WRITES` for the store and a writer test).

## Tests added

- `tests/execution_upbit.py`: exact keyless URLs of the four helpers; bad markets, lists, times and counts refused
  before any send.
- `tests/accounts_universe.py`: the exact request set through a fake `transport._send`; a failed read after the
  transport's single retry; missing server time; body caps; `daily_bars` paging, finality window, dropped rows,
  forged receipts and bad inputs; the slot source's reads and its `ok=False` failures; an import pin (only the
  transport's `Answer` and `inquiry_clock` and the public `upbit_inquiry` helpers; no `core.oddsdata`, `data` or
  `config`).
- `tests/launch_universe_store.py`: a rebuild leaves earlier files intact; an existing name is refused and kept; a
  name that appears during the write is kept (Windows); the command's state-root and argument checks; a failed read
  writes nothing; the rule source.

## Not verified

- No live Upbit call was made. The body caps are provisional until the spec section 17 measurement.
- The Windows Task Scheduler entry (09:12 KST, retry 09:27 KST) is an owner act and is not created here.
- Nothing reads a snapshot back yet (PR 3). The command takes the rule from the newest approved state on disk.
- On POSIX, `os.rename` would replace a file that appeared after the existence check (same content-addressed bytes).

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: `gh` prints the PR URL. Report it; the owner reviews and merges on GitHub.
