# Upbit KRW universe PR 4c: terms authority v2, IOC orders, unlisted and thin coins, E1 alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a universe profile read Upbit terms for the coin chosen at read time, renew to another coin, send IOC
limit orders and survive a held coin that is delisted or thinly traded, while fixed KRW-BTC profiles keep every
digest, request body and refusal they have today; and give the E1 poll the three new spec section 15 alerts.

**Architecture:** A version 2 terms authority (`UniverseTermsAuthority`, the rule sha256 instead of a symbol) beside
the unchanged v1 `TermsAuthority`; the parser records the observed maximum on every observation and only v1 still
fails when it moves. `renew_profile` gains `allow_symbol_change` for universe profiles. Upbit orders accept `ioc`,
added to the create body only for IOC orders. The account collector reads `market/all` before the ticker, records an
unlisted held coin at price 0 with an `unlisted` marker that the provider requires for price 0, and marks a coin with
a stale last trade at the best bid of a fresh book. E1 reads `market/all` for held coins outside the snapshot's
fail-whole path, values unlisted coins at 0 and raises the new alerts.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `dataclasses`, `decimal`, `fractions`,
`datetime`, `json`, `hashlib`. No new dependency.

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md), sections 10,
11 and 15.

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md)
(base, one branch and PR, no new dependency, offline tests, `focus` runner, byte-exact line endings, never `sed -i`,
commit trailer, PR body ending, the owner merges).

Constraints specific to this PR, verbatim from the spec:

- "Fixed profiles keep the v1 authority (one symbol). Universe profiles use a v2 authority with `universe_sha256`
  (the rule sha256) instead of `symbol`, tagged by version; `authority_digest` gets a v2 form." (section 10)
- "In a v2 authority, `maximum_notional_krw` is a buy cap: the parser records the observed maximum and never fails on
  it, and a coin whose observed maximum is below the cap is left out of the allow-list. `validate_observed_order`
  (`instrument_refresh.py:168-170`) checks every order, sells included, against the recorded observed maximum, and
  buys also against the v2 cap." (section 10)
- "The private account audit carries `terms_authority` (v1) or `universe_terms_authority` (v2);
  `tools/owner/rehearsal.py:364` checks whichever the profile uses. The audit bytes change, so the owner re-signs the
  strategy review." (section 10)
- "`renew_profile` gets `allow_symbol_change`. [...] Every check that can refuse (the terms parse, the rule-terms
  digest, the contract digest) runs before the head moves (`instrument_refresh.py:102`). The new profile is
  `replace(profile, symbol=verified.rules.symbol, instrument_rules=verified.rules)` [...] A fixed profile still
  refuses any symbol change." (section 10)
- "`execution_control/model.py:95-97`: Upbit accepts `gtc` and `ioc`; KIS stays `day`, OKX stays `gtc`;
  `execution_launch/profile.py:328-330`: a universe profile requires `ioc`; a fixed Upbit profile keeps `gtc`; [...]
  `execution_orders/upbit.py` `_build`: add `("time_in_force", "ioc")` to the create body only for IOC orders, so the
  gtc body stays byte-identical; `parse` requires a create response's `time_in_force` to equal `ioc` for an IOC
  order, otherwise `unknown(identity_mismatch)`." (section 11)
- "add `/v1/market/all` and `/v1/orderbook` to `_ALLOWED` and to `COLLECTOR_ROUTES`; read `market/all` first. A
  positive balance whose KRW market is not listed is left out of the ticker read and recorded as an unlisted position
  at price 0 with the read's time. The provider allows price 0 only for a position the capture marked unlisted; a
  listed balance whose last trade is at most 30 seconds old is marked at the trade price, as today. If the trade is
  older, the capture reads that coin's book and marks it at the best bid if the book is at most 10 seconds old;
  otherwise the capture fails closed, as today; the added reads count toward the capture's 30-second budget."
  (section 11)
- "**E1** applies the same rule: unlisted markets are left out of its ticker read (`execution/upbit_inquiry.py:94`)
  and valued at 0, not `None` (`execution/positions.py:33`), so the poll that raises the alerts keeps working."
  (section 11)
- "**E1 poll** (new catalogue entries [...]). It reads the held coin's `market/all` entry outside the Upbit snapshot's
  fail-whole path, so a failed read raises only an amber alert and never voids E1 positions. red: a held coin is no
  longer listed; red: a held coin is `warning`; amber: no snapshot in force at 09:45 KST." (section 15)

PR-specific rules that follow from the index:

- This PR is cut from `main` after PR 4b merged. The merge order (PR 0, 1, 2, 3, 4a, 4b) puts these names on `main`
  first and this plan uses them: PR 1 `core.compliance.rules.UNIVERSE_MARKET`, `FLAG_CLASSES`, `market_flags`,
  `Venue.universe_rule`; PR 2 `execution.upbit_inquiry.MARKET_ALL_PATH`, `market_all()` and the `("GET",
  "/v1/market/all")` entry in `ENDPOINTS` and `PUBLIC`; PR 3 `Context.universe`; PR 4b
  `LaunchProfile.universe_rule_sha256`, the universe forms of `rule_terms_digest` and `profile_contract_digest`, and
  `RULE` in `tests/launch_profile.py`. Task 1 Step 1 checks each one before any edit.
- Line numbers below are fd85850's. PR 4b replaces `execution_launch/instrument_refresh.py:75-76` with four lines, so
  every later line of that file moves down by 2; PR 2 changes `execution/upbit_inquiry.py`; PR 4b adds lines to
  `execution_launch/profile.py`, `tests/launch_profile.py` and the end of `tests/launch_instrument_refresh.py`.
  Every edit quotes the code it replaces; find it by that text.
- `tests/renewal_boundaries.py` pins five surfaces this PR changes: `execution_accounts/instrument_terms.py` (Tasks
  1 and 2), `execution_launch/instrument_refresh.py` (Tasks 2 and 4), `execution_accounts/model.py` (Task 6) and
  `execution/upbit_inquiry.py` (Task 8), plus two `CALLS` entries (Tasks 1 and 2). Each pin is updated by hand after
  the surface diff is reviewed; it is never regenerated blindly. The values stated below were computed from fd85850
  plus exactly the code in this plan; if PR 0 to PR 4b changed one of these surfaces, the printed value differs and
  the reviewed diff decides.
- No `driver.py` edit: the universe driver is PR 4d. No coordinator edit: the coordinator's `read(symbol)`,
  `allow_symbol_change` and toasts are PR 4e.

## File Structure

- Modify `execution_accounts/instrument_terms.py`: `UniverseTermsAuthority`, the v2 form of `authority_digest`, the
  v2 symbol and split market codes in `parse_term_receipts`, `TermsObservation.observed_maximum_krw`,
  `within_buy_cap`, `E1UpbitTermsSource.read(symbol=None)`.
- Modify `execution_launch/instrument_refresh.py`: `renew_profile(..., allow_symbol_change=False)`, the symbol move,
  the observed maximum and v2 buy cap in `validate_observed_order`.
- Modify `execution_control/model.py`, `execution_launch/profile.py`, `execution_orders/upbit.py`: IOC.
- Modify `tools/owner/rehearsal.py`: `universe_terms_authority` in the account audit and `_terms_authority`.
- Modify `execution_accounts/upbit_collector.py`, `execution_accounts/model.py`, `execution_accounts/provider.py`:
  the listing read, unlisted positions, the thin-coin book mark, the provider's marker rule.
- Modify `execution/snapshot.py`, `execution/upbit_inquiry.py`, `execution/positions.py`, `execution/checks.py`,
  `execution/poll.py`: `Snapshot.market_flags`, the held-coin listing read, the zero value, the alerts.
- Modify tests: `tests/launch_instrument_refresh.py`, `tests/renewal_boundaries.py`, `tests/control_model.py`,
  `tests/orders_codecs.py`, `tests/launch_profile.py`, `tests/launch_owner_rehearsal.py`, `tests/accounts_guards.py`,
  `tests/accounts_collector.py`, `tests/launch_account_interval.py`, `tests/accounts_provider.py`,
  `tests/launch_runner.py`, `tests/execution_fixtures.py`, `tests/execution_upbit.py`, `tests/accounts_readiness.py`,
  `tests/execution_snapshot.py`, `tests/execution_positions.py`, `tests/execution_checks.py`, `tests/execution_poll.py`.
- No new module, so no suite `MODULES` change.

## Contract notes

Additions to the index's PR 4c names (none changes a name the index states):

- `UniverseTermsAuthority` has `TermsAuthority`'s fields with `universe_sha256: str` in place of `symbol`.
- `TermsObservation.observed_maximum_krw: Decimal`, set by the parser for v1 and v2 (for v1 it equals the authority's
  maximum). `within_buy_cap(observation) -> bool`: `True` for v1, `observed_maximum_krw >= maximum_notional_krw`
  for v2. PR 4e builds the allow-list from it.
- `E1UpbitTermsSource.read(symbol=None)`: v1 accepts `None` or its own symbol, else `TERMS_SYMBOL_MISMATCH`; v2
  requires a KRW symbol, else `TERMS_KRW_SYMBOL_REQUIRED`.
- `renew_profile`: `allow_symbol_change=True` on a fixed profile refuses `RENEWAL_SYMBOL_CHANGE_REFUSED`; a symbol
  change without the flag keeps today's `RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH`. `validate_observed_order` adds
  `RENEWAL_BUY_ABOVE_UNIVERSE_CAP`.
- `execution_accounts.model.Position.unlisted: bool | None = None`, left out of `canonical` while `None`. Provider
  codes `POSITION_UNLISTED_MARKER_INVALID`, `POSITION_UNLISTED_PRICE_INVALID`; collector codes
  `COLLECTOR_BOOK_INVALID`, `COLLECTOR_BOOK_STALE_OR_FUTURE`.
- The collector reads `market/all` only when the first balance read holds a positive non-KRW balance, just before
  the ticker. Flat captures keep their 9 (collector) and 11 (interval) receipts.
- `execution.snapshot.Snapshot.market_flags: Mapping[str, str] | None = None` (held coin to its `FLAG_CLASSES`
  class), left out of `snapshot_sha256` and of `dump` while `None`; `load` takes rows with or without it.
- `execution.checks`: kinds `MARKET_FLAGS` and `UNIVERSE`; text keys `HELD_UNLISTED` (red), `HELD_WARNING` (red),
  `HELD_FLAGS_UNKNOWN` (amber), `UNIVERSE_NO_SNAPSHOT` (amber); `UNIVERSE_DEADLINE = time(9, 45)`;
  `universe_check(ctx, now) -> tuple[list[Alert], frozenset[tuple[str, str]]]`.
- `tools/owner/rehearsal.py`: `AccountAudit.universe_terms_authority: UniverseTermsAuthority | None = None` and
  `_terms_authority(profile, audit)`.

---

### Task 1: Terms authority v2, the market code split and `read(symbol)`

**Files:**
- Modify: `execution_accounts/instrument_terms.py:83-122` (new class, `authority_digest`), `:128` (annotation),
  `:160` and `:172-173` (`parse_term_receipts`), `:249` (annotation), `:260-269` (`read`)
- Modify: `tests/renewal_boundaries.py:28` (pin) and `:60` (`parse_term_receipts` calls)
- Test: `tests/launch_instrument_refresh.py:18` (import), helpers after `:87`, `:177-178`, new tests at the end

**Interfaces:**
- Consumes: `tests.launch_profile.RULE` (PR 4b).
- Produces:
  - `UniverseTermsAuthority(*, account_scope, universe_sha256, lot_size, min_quantity, maximum_notional_krw,
    provenance_sha256, identity_binding_sha256, valid_from, valid_until)`.
  - `authority_digest(authority: TermsAuthority | UniverseTermsAuthority) -> str` (v1 byte-identical).
  - `E1UpbitTermsSource.read(symbol: str | None = None) -> TermsObservation`.
  - Codes `TERMS_MARKET_INACTIVE`, `TERMS_MARKET_MISMATCHED` (replacing `TERMS_MARKET_INACTIVE_OR_MISMATCHED`),
    `TERMS_SYMBOL_MISMATCH`.

- [ ] **Step 1: Start the branch from main**

```bash
git fetch origin
git switch -c claude/universe-pr4c-terms-orders-accounts origin/main
git log --oneline -8
grep -n "universe_rule_sha256: str | None = None" execution_launch/profile.py
grep -n "^RULE = " tests/launch_profile.py
grep -n "^UNIVERSE_MARKET\|^FLAG_CLASSES\|^def market_flags" core/compliance/rules.py
grep -n "^MARKET_ALL_PATH\|^def market_all" execution/upbit_inquiry.py
grep -n "universe: Universe | None = None" core/compliance/model.py
```

Expected: the log shows the merge of PR 4b on top of the merges of PR 4a, PR 3, PR 2, PR 1 and PR 0; the greps print
one, one, three, two and one line. If anything is missing, stop and report; this PR is ordered after all of them.

- [ ] **Step 2: Write the failing tests**

In `tests/launch_instrument_refresh.py`, replace line 18:

```python
from tests.launch_profile import fixture_profile
```

with:

```python
from tests.launch_profile import RULE, fixture_profile
```

Insert after line 87 (the end of `refused`), with two blank lines on each side:

```python
def universe_authority(**changes):
    values = dict(account_scope="test-scope", universe_sha256=RULE, lot_size=D("0.01"),
        min_quantity=D("0.01"), maximum_notional_krw=D("2000000"),
        provenance_sha256="d"*64, identity_binding_sha256="e"*64,
        valid_from=NOW-timedelta(days=1), valid_until=NOW+timedelta(days=1))
    return T.UniverseTermsAuthority(**(values | changes))


def universe_bodies(symbol, max_total="2000000", tick="1"):
    chance, instruments = bodies()
    chance["market"].update(id=symbol, max_total=max_total)
    chance["market"]["ask"]["currency"] = symbol.split("-")[1]
    instruments[0].update(market=symbol, tick_size=tick)
    return chance, instruments


def universe_observed(symbol="KRW-BTC", now=NOW+timedelta(seconds=10), *, auth=None, max_total="2000000", tick="1"):
    chance, instruments = universe_bodies(symbol, max_total, tick)
    with patch.object(T, "current_terms", return_value=(answer(chance, now), answer(instruments, now))) as call:
        observation = T.E1UpbitTermsSource(authority=auth or universe_authority(), clock=lambda: now).read(symbol)
    call.assert_called_once_with(symbol)
    return observation
```

Replace lines 177-178:

```python
            (lambda c: c["market"].update(state="halted"), "TERMS_MARKET_INACTIVE_OR_MISMATCHED"),
            (lambda c: c["market"].update(id="KRW-ETH"), "TERMS_MARKET_INACTIVE_OR_MISMATCHED"),
```

with:

```python
            (lambda c: c["market"].update(state="halted"), "TERMS_MARKET_INACTIVE"),
            (lambda c: c["market"].update(id="KRW-ETH"), "TERMS_MARKET_MISMATCHED"),
```

Append to the end of the file (two blank lines before the first new line):

```python
def test_v1_authority_digest_is_byte_identical_and_v2_is_a_separate_form():
    assert T.authority_digest(authority()) == "728bd2d73418bcd1211500b20934924a28e468648419be126f73ecec3b1e2b04"
    v2 = T.authority_digest(universe_authority())
    assert v2 != T.authority_digest(authority())
    assert T.authority_digest(universe_authority(universe_sha256="f"*64)) != v2
    assert T.authority_digest(universe_authority(maximum_notional_krw=D("1000000"))) != v2
    refused(lambda: T.authority_digest(universe_authority(universe_sha256="KRW-BTC")), "TERMS_SOURCE_DIGEST_REQUIRED")
    refused(lambda: T.authority_digest(universe_authority(account_scope="bad scope")), "TERMS_SCOPE_INVALID")
    refused(lambda: T.authority_digest(object()), "TERMS_AUTHORITY_REQUIRED")


def test_v2_reads_the_symbol_named_at_read_time_and_v1_keeps_its_own():
    with registries():
        o = universe_observed("KRW-ETH")
        assert (o.rules.symbol, o.rules.source_digest) == ("KRW-ETH", T.authority_digest(universe_authority()))
        assert o.chance_receipt.params == (("market", "KRW-ETH"),)
        assert o.instruments_receipt.params == (("markets", "KRW-ETH"),)
        source = T.E1UpbitTermsSource(authority=universe_authority(), clock=lambda: NOW)
        for bad in (None, "BTC", "KRW-KRW", "KRW-eth"):
            refused(lambda bad=bad: source.read(bad), "TERMS_KRW_SYMBOL_REQUIRED")
        refused(lambda: T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW).read("KRW-ETH"),
                "TERMS_SYMBOL_MISMATCH")
        later = NOW+timedelta(seconds=20)
        c, i = bodies()
        with patch.object(T, "current_terms", return_value=(answer(c, later), answer(i, later))):
            assert T.E1UpbitTermsSource(authority=authority(), clock=lambda: later).read("KRW-BTC").rules.symbol == "KRW-BTC"
        assert observed(NOW+timedelta(seconds=30)).rules.symbol == "KRW-BTC"


def test_v2_parse_takes_its_symbol_only_from_one_exact_chance_query():
    with registries():
        o = universe_observed("KRW-ETH")
        for params in ((), (("market", "KRW-KRW"),), (("markets", "KRW-ETH"),), (("market", "KRW-BTC"),),
                       (("market", "KRW-ETH"), ("market", "KRW-BTC"))):
            refused(lambda params=params: T.parse_term_receipts(authority=o.authority,
                chance_receipt=replace(o.chance_receipt, params=params), instruments_receipt=o.instruments_receipt,
                requested_at=o.requested_at, checked_at=o.checked_at, now=o.checked_at),
                "TERMS_RECEIPT_SCOPE_MISMATCH")
        later = NOW+timedelta(seconds=20)
        c, i = universe_bodies("KRW-ETH")
        c["market"]["id"] = "KRW-XRP"
        with patch.object(T, "current_terms", return_value=(answer(c, later), answer(i, later))):
            refused(lambda: T.E1UpbitTermsSource(authority=universe_authority(), clock=lambda: later).read("KRW-ETH"),
                    "TERMS_MARKET_MISMATCHED")
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
focus launch launch_instrument_refresh/test_v
focus launch launch_instrument_refresh/test_terms_parser_rejects
```

Expected: exit 1. The three new tests `FAIL` with `AttributeError: module 'execution_accounts.instrument_terms' has
no attribute 'UniverseTermsAuthority'`; `test_terms_parser_rejects_halted_missing_asymmetric_and_changed_maximum`
fails with `AssertionError: ('TERMS_MARKET_INACTIVE_OR_MISMATCHED', 'TERMS_MARKET_INACTIVE')`.

- [ ] **Step 4: Add the v2 authority, its digest, the v2 parse and `read(symbol)`**

In `execution_accounts/instrument_terms.py`, replace lines 103-122 (all of `authority_digest`):

```python
def authority_digest(authority):
    _require(type(authority) is TermsAuthority, "TERMS_AUTHORITY_REQUIRED")
    _require(type(authority.account_scope) is str and
             _SCOPE.fullmatch(authority.account_scope) is not None, "TERMS_SCOPE_INVALID")
    _require(type(authority.symbol) is str and _SYMBOL.fullmatch(authority.symbol) is not None
             and authority.symbol != "KRW-KRW", "TERMS_KRW_SYMBOL_REQUIRED")
    for name in ("lot_size", "min_quantity", "maximum_notional_krw"):
        value = getattr(authority, name)
        _require(type(value) is Decimal, "TERMS_EXACT_NUMBER_REQUIRED")
        _number(value, positive=name != "min_quantity")
    start, end = _time(authority.valid_from), _time(authority.valid_until)
    _require(start < end, "TERMS_AUTHORITY_WINDOW_INVALID")
    return _digest({"version": "upbit-terms-authority-v1", "venue": "upbit", "market": "spot",
        "account_scope": authority.account_scope, "symbol": authority.symbol,
        "lot_size": decimal_text(authority.lot_size), "min_quantity": decimal_text(authority.min_quantity),
        "maximum_notional_krw": decimal_text(authority.maximum_notional_krw),
        "provenance_sha256": _sha(authority.provenance_sha256),
        "identity_binding_sha256": _sha(authority.identity_binding_sha256),
        "valid_from": start.isoformat(timespec="microseconds"),
        "valid_until": end.isoformat(timespec="microseconds")})
```

with (the class goes between `TermsAuthority` and `authority_digest`; the v1 body keeps every key and value, so its
digest is byte-identical):

```python
@dataclass(frozen=True, kw_only=True)
class UniverseTermsAuthority:
    """Version 2 for universe profiles (spec section 10): the signed rule's sha256 instead of one symbol.

    The symbol is chosen at read time. maximum_notional_krw is a buy cap, not an expected API value: the parser
    records the observed maximum and never fails on it. Review obligations are those of TermsAuthority.
    """
    account_scope: str
    universe_sha256: str
    lot_size: Decimal
    min_quantity: Decimal
    maximum_notional_krw: Decimal
    provenance_sha256: str
    identity_binding_sha256: str
    valid_from: datetime
    valid_until: datetime


def authority_digest(authority):
    _require(type(authority) in (TermsAuthority, UniverseTermsAuthority), "TERMS_AUTHORITY_REQUIRED")
    _require(type(authority.account_scope) is str and
             _SCOPE.fullmatch(authority.account_scope) is not None, "TERMS_SCOPE_INVALID")
    if type(authority) is TermsAuthority:
        _require(type(authority.symbol) is str and _SYMBOL.fullmatch(authority.symbol) is not None
                 and authority.symbol != "KRW-KRW", "TERMS_KRW_SYMBOL_REQUIRED")
        identity = {"version": "upbit-terms-authority-v1", "symbol": authority.symbol}
    else:
        identity = {"version": "upbit-terms-authority-v2", "universe_sha256": _sha(authority.universe_sha256)}
    for name in ("lot_size", "min_quantity", "maximum_notional_krw"):
        value = getattr(authority, name)
        _require(type(value) is Decimal, "TERMS_EXACT_NUMBER_REQUIRED")
        _number(value, positive=name != "min_quantity")
    start, end = _time(authority.valid_from), _time(authority.valid_until)
    _require(start < end, "TERMS_AUTHORITY_WINDOW_INVALID")
    return _digest(identity | {"venue": "upbit", "market": "spot",
        "account_scope": authority.account_scope,
        "lot_size": decimal_text(authority.lot_size), "min_quantity": decimal_text(authority.min_quantity),
        "maximum_notional_krw": decimal_text(authority.maximum_notional_krw),
        "provenance_sha256": _sha(authority.provenance_sha256),
        "identity_binding_sha256": _sha(authority.identity_binding_sha256),
        "valid_from": start.isoformat(timespec="microseconds"),
        "valid_until": end.isoformat(timespec="microseconds")})
```

Replace line 128:

```python
    authority: TermsAuthority = field(repr=False)
    requested_at: datetime
```

with:

```python
    authority: TermsAuthority | UniverseTermsAuthority = field(repr=False)
    requested_at: datetime
```

Replace line 160:

```python
    symbol = authority.symbol
```

with:

```python
    # v1 binds one symbol; v2 (spec section 10) takes the symbol of its one reviewed chance query.
    universe = type(authority) is UniverseTermsAuthority
    params = chance_receipt.params if type(chance_receipt) is SourceReceipt else None
    _require(not universe or (type(params) is tuple and len(params) == 1 and type(params[0]) is tuple
                              and len(params[0]) == 2 and params[0][0] == "market" and type(params[0][1]) is str
                              and _SYMBOL.fullmatch(params[0][1]) is not None and params[0][1] != "KRW-KRW"),
             "TERMS_RECEIPT_SCOPE_MISMATCH")
    symbol = params[0][1] if universe else authority.symbol
```

Replace lines 172-173:

```python
    _require(market.get("id") == symbol and market.get("state") == "active",
             "TERMS_MARKET_INACTIVE_OR_MISMATCHED")
```

with:

```python
    _require(market.get("id") == symbol, "TERMS_MARKET_MISMATCHED")
    _require(market.get("state") == "active", "TERMS_MARKET_INACTIVE")
```

Replace line 249:

```python
    authority: TermsAuthority = field(repr=False)
    clock: Callable = field(repr=False)
```

with:

```python
    authority: TermsAuthority | UniverseTermsAuthority = field(repr=False)
    clock: Callable = field(repr=False)
```

Replace lines 260-262:

```python
    def read(self):
        """Issue one bounded observation; no arbitrary path or method parameters."""
        authority_digest(self.authority)
```

with:

```python
    def read(self, symbol=None):
        """Issue one bounded observation; no arbitrary path or method parameters.

        A v1 authority reads its own symbol (``symbol`` is None or that symbol). A v2 authority reads the KRW market
        named here, chosen at read time (spec section 10).
        """
        authority_digest(self.authority)
        if type(self.authority) is TermsAuthority:
            _require(symbol is None or symbol == self.authority.symbol, "TERMS_SYMBOL_MISMATCH")
            symbol = self.authority.symbol
        else:
            _require(type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None and symbol != "KRW-KRW",
                     "TERMS_KRW_SYMBOL_REQUIRED")
```

and delete line 269:

```python
        symbol = self.authority.symbol
```

- [ ] **Step 5: Run the terms tests**

```bash
focus launch launch_instrument_refresh/
```

Expected: every `launch_instrument_refresh/...` row `PASS`, exit 0 (PR 4b's universe renewal test included; it uses
a v1 authority and no symbol change).

- [ ] **Step 6: Review the renewal surface change and update its pins**

```bash
focus control control_guards/test_renewal_validation
```

Expected before the update: exit 1, `FAIL control_guards/test_renewal_validation_has_only_reviewed_pure_calls_and_import_surfaces
AssertionError: ['execution_accounts/instrument_terms.py: initialization surface changed',
'execution_accounts/instrument_terms.py:parse_term_receipts: callable surface changed']`. Any other line means a
call that Step 4 does not contain; fix the code, not the pin.

Review: `git diff -- execution_accounts/instrument_terms.py` must show, outside function bodies, exactly the new
`UniverseTermsAuthority` class, the two widened `authority` annotations and the new `symbol=None` parameter of
`read`; inside `parse_term_receipts` the only new call is `_SYMBOL.fullmatch`. Then print the new surface:

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_accounts/instrument_terms.py').read_text(encoding='utf-8')))"
```

Expected output: `460adbdc092e4da47bccfefab259ea873ae2bc80cfec64c7e4233bfe7a07e2df` (computed from fd85850 plus
Step 4; if it differs, reconcile the code with Step 4 first).

In `tests/renewal_boundaries.py`, replace line 28:

```python
    "execution_accounts/instrument_terms.py": "7a87af0de172ba598c158ebf646be226c045bfed540a26671402af2198662dda",
```

with:

```python
    "execution_accounts/instrument_terms.py": "460adbdc092e4da47bccfefab259ea873ae2bc80cfec64c7e4233bfe7a07e2df",
```

and replace line 60:

```python
        "parse_term_receipts": ["InstrumentRules","TermsObservation","_digest","_number","_receipt","_require","_time","_time(r.received_at).isoformat","_time(r.server_time).isoformat","all","ask.get","authority_digest","before.isoformat","bid.get","chance.get","checked.isoformat","instrument.get","instruments[0].get","len","market.get","min","rules_digest","symbol.split","timedelta","tuple","type"],
```

with:

```python
        "parse_term_receipts": ["InstrumentRules","TermsObservation","_SYMBOL.fullmatch","_digest","_number","_receipt","_require","_time","_time(r.received_at).isoformat","_time(r.server_time).isoformat","all","ask.get","authority_digest","before.isoformat","bid.get","chance.get","checked.isoformat","instrument.get","instruments[0].get","len","market.get","min","rules_digest","symbol.split","timedelta","tuple","type"],
```

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS` (import ports, validation, effect closure), exit 0.

- [ ] **Step 7: Commit**

```bash
git diff --stat -- execution_accounts/instrument_terms.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py
git diff --stat --ignore-cr-at-eol -- execution_accounts/instrument_terms.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py
git add execution_accounts/instrument_terms.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py
git commit -m "$(cat <<'EOF'
feat(accounts): terms authority v2 and read-time symbol

UniverseTermsAuthority binds the universe rule sha256 instead of one
symbol; authority_digest gets a v2 form and the v1 digest stays byte for
byte (pinned). A v2 read takes the KRW symbol at read time and the parse
takes it only from one exact chance query. TERMS_MARKET_INACTIVE and
TERMS_MARKET_MISMATCHED replace the combined code (spec section 10). The
renewal surface pin and parse_term_receipts call set are updated after
review.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 2: Observed maximum, the v2 buy cap and `validate_observed_order`

**Files:**
- Modify: `execution_accounts/instrument_terms.py:133` (field), `:185-187` (maximum), `:212-214` (constructor),
  `:225-227` (`validate_issued_observation`), new `within_buy_cap` after `:228`
- Modify: `execution_launch/instrument_refresh.py:14-15` (import), `:168-170` (fd85850; `:170-172` after PR 4b)
- Modify: `tests/renewal_boundaries.py:28`, `:34` (pins) and `:50` (`validate_observed_order` calls)
- Test: `tests/launch_instrument_refresh.py`, new test at the end

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `TermsObservation.observed_maximum_krw: Decimal` (required; set by `parse_term_receipts`).
  - `within_buy_cap(observation: TermsObservation) -> bool`; `TERMS_OBSERVATION_REQUIRED` for anything else.
  - `validate_observed_order(order, rules, *, now)`: every order against the observed maximum
    (`RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM`), v2 buys also against the cap (`RENEWAL_BUY_ABOVE_UNIVERSE_CAP`).

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/launch_instrument_refresh.py`:

```python
def test_v2_records_the_observed_maximum_caps_buys_and_lets_a_held_coin_sell_above_the_cap():
    with registries():
        auth = universe_authority()                                    # buy cap 2,000,000
        o = universe_observed("KRW-ETH", auth=auth, max_total="3000000")
        assert o.observed_maximum_krw == D("3000000") and T.within_buy_cap(o)
        sell = Order(client_id="synthetic-sell", account_scope="test-scope", venue="upbit", market="spot",
                     symbol="KRW-ETH", side="sell", quantity=D("2500"), limit_price=D("1000"), quote_krw=D("1"))
        R.validate_observed_order(sell, o.rules, now=o.checked_at)      # 2,500,000: above the cap, a sell
        refused(lambda: R.validate_observed_order(replace(sell, side="buy"), o.rules, now=o.checked_at),
                "RENEWAL_BUY_ABOVE_UNIVERSE_CAP")
        R.validate_observed_order(replace(sell, side="buy", quantity=D("2000")), o.rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(sell, quantity=D("3000.01")), o.rules, now=o.checked_at),
                "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
        low = universe_observed("KRW-XRP", o.checked_at+timedelta(seconds=10), auth=auth, max_total="1000000")
        assert low.observed_maximum_krw == D("1000000") and not T.within_buy_cap(low)
        v1 = observed(o.checked_at+timedelta(seconds=20))
        assert v1.observed_maximum_krw == D("2000000") and T.within_buy_cap(v1)
        refused(lambda: T.within_buy_cap(None), "TERMS_OBSERVATION_REQUIRED")
        copy = T.parse_term_receipts(authority=o.authority, chance_receipt=o.chance_receipt,
            instruments_receipt=o.instruments_receipt, requested_at=o.requested_at,
            checked_at=o.checked_at, now=o.checked_at)
        assert copy == o
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus launch launch_instrument_refresh/test_v2_records_the_observed_maximum
```

Expected: exit 1, `FAIL ... TermsError: TERMS_MAXIMUM_CHANGED` (the v2 parse still compares the observed maximum
with the cap).

- [ ] **Step 3: Record the observed maximum and enforce the cap**

In `execution_accounts/instrument_terms.py`, replace line 133:

```python
    evidence_digest: str
```

(the last field of `TermsObservation`) with:

```python
    evidence_digest: str
    observed_maximum_krw: Decimal
```

Replace lines 185-187:

```python
    maximum = _number(market.get("max_total"), positive=True)
    _require(maximum >= minimum and maximum == authority.maximum_notional_krw,
             "TERMS_MAXIMUM_CHANGED")
```

with:

```python
    maximum = _number(market.get("max_total"), positive=True)
    # v2: the cap is a buy limit, so the observed maximum is recorded and never fails the parse (spec section 10).
    _require(maximum >= minimum and (universe or maximum == authority.maximum_notional_krw),
             "TERMS_MAXIMUM_CHANGED")
```

Replace lines 212-214:

```python
    return TermsObservation(rules=rules, authority=authority, requested_at=before,
        checked_at=checked, chance_receipt=chance_receipt, instruments_receipt=instruments_receipt,
        evidence_digest=evidence)
```

with:

```python
    return TermsObservation(rules=rules, authority=authority, requested_at=before,
        checked_at=checked, chance_receipt=chance_receipt, instruments_receipt=instruments_receipt,
        evidence_digest=evidence, observed_maximum_krw=maximum)
```

Replace lines 225-227:

```python
    _require(parsed.evidence_digest == observation.evidence_digest == saved[1]
             and rules_digest(parsed.rules) == rules_digest(observation.rules),
             "TERMS_OBSERVATION_CHANGED")
```

with:

```python
    _require(parsed.evidence_digest == observation.evidence_digest == saved[1]
             and rules_digest(parsed.rules) == rules_digest(observation.rules)
             and parsed.observed_maximum_krw == observation.observed_maximum_krw,
             "TERMS_OBSERVATION_CHANGED")
```

Insert after line 228 (`return parsed`, the end of `validate_issued_observation`), with two blank lines on each
side, so it sits between `validate_issued_observation` and `observation_for_rules`:

```python
def within_buy_cap(observation):
    """Spec section 10: a v2 coin is buyable only while its observed maximum is at least the reviewed cap.

    A v1 observation is always within its cap: the parse refused any other maximum.
    """
    _require(type(observation) is TermsObservation, "TERMS_OBSERVATION_REQUIRED")
    return (type(observation.authority) is not UniverseTermsAuthority
            or observation.observed_maximum_krw >= observation.authority.maximum_notional_krw)
```

In `execution_launch/instrument_refresh.py`, replace lines 14-15:

```python
from execution_accounts.instrument_terms import (TermsObservation, validate_issued_observation,
                                                  observation_for_rules)
```

with:

```python
from execution_accounts.instrument_terms import (TermsObservation, UniverseTermsAuthority,
                                                  validate_issued_observation, observation_for_rules)
```

Replace the docstring line of `validate_observed_order` and its last three lines (fd85850 `:158` and `:168-170`):

```python
    """Enforce the observed maximum too, when using a refreshed rule snapshot."""
```

```python
    maximum = observation.authority.maximum_notional_krw
    _require(Fraction(order.quantity) * Fraction(order.limit_price) * Fraction(order.quote_krw)
             <= Fraction(maximum), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
```

with:

```python
    """Every order against the observed maximum; a v2 buy also against the cap (spec section 10)."""
```

```python
    notional = Fraction(order.quantity) * Fraction(order.limit_price) * Fraction(order.quote_krw)
    _require(notional <= Fraction(observation.observed_maximum_krw), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
    _require(order.side != "buy" or type(observation.authority) is not UniverseTermsAuthority
             or notional <= Fraction(observation.authority.maximum_notional_krw), "RENEWAL_BUY_ABOVE_UNIVERSE_CAP")
```

- [ ] **Step 4: Run the terms and controller tests**

```bash
focus launch launch_instrument_refresh/
focus control control_controller/
```

Expected: every row `PASS`, exit 0 for each (v1 observed maximum equals the authority's, so every existing maximum
test keeps its result).

- [ ] **Step 5: Review the renewal surface change and update its pins**

```bash
focus control control_guards/test_renewal_validation
```

Expected before the update: exit 1, `AssertionError: ['execution_accounts/instrument_terms.py: initialization
surface changed', 'execution_launch/instrument_refresh.py: initialization surface changed',
'execution_launch/instrument_refresh.py:validate_observed_order: callable surface changed']`.

Review: `git diff -- execution_accounts/instrument_terms.py execution_launch/instrument_refresh.py` must show,
outside function bodies, exactly the new `observed_maximum_krw: Decimal` field, the new `within_buy_cap(observation)`
signature and the one new imported name `UniverseTermsAuthority`; inside `validate_observed_order` the only new call
is `type`. Print both surfaces:

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; [print(f, _surface(Path(f).read_text(encoding='utf-8'))) for f in ('execution_accounts/instrument_terms.py', 'execution_launch/instrument_refresh.py')]"
```

Expected: `execution_accounts/instrument_terms.py debf4f2f2e095214adf60a193bac5252b4c402373bf3d5e8e039182a74e6a9d0`
and `execution_launch/instrument_refresh.py f915417195062fea05a820756b3d4032c95eeef546a395f912bc968eb67591e5`.

In `tests/renewal_boundaries.py`, replace line 28:

```python
    "execution_accounts/instrument_terms.py": "460adbdc092e4da47bccfefab259ea873ae2bc80cfec64c7e4233bfe7a07e2df",
```

with:

```python
    "execution_accounts/instrument_terms.py": "debf4f2f2e095214adf60a193bac5252b4c402373bf3d5e8e039182a74e6a9d0",
```

replace line 34:

```python
    "execution_launch/instrument_refresh.py": "fc52e2ea59221ac5d3a6d0c3a170a8f5aa3e16fc830380d04dc11b30f7c732d1",
```

with:

```python
    "execution_launch/instrument_refresh.py": "f915417195062fea05a820756b3d4032c95eeef546a395f912bc968eb67591e5",
```

and replace line 50:

```python
        "validate_observed_order": ["Fraction","_BOUND.get","_require","observation_for_rules","rules_digest","validate_order","validate_renewal"],
```

with:

```python
        "validate_observed_order": ["Fraction","_BOUND.get","_require","observation_for_rules","rules_digest","type","validate_order","validate_renewal"],
```

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS`, exit 0.

- [ ] **Step 6: Commit**

```bash
FILES="execution_accounts/instrument_terms.py execution_launch/instrument_refresh.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(accounts): observed maximum and the v2 buy cap

Every observation records the venue's observed maximum. A v2 parse never
fails on it; within_buy_cap tells the allow-list whether a coin's maximum
reaches the reviewed cap. validate_observed_order checks every order,
sells included, against the observed maximum and v2 buys also against the
cap (spec section 10). Renewal pins and the call set are updated after
review.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 3: IOC orders for universe profiles

**Files:**
- Modify: `execution_control/model.py:95-97`
- Modify: `execution_launch/profile.py:328` (fd85850; find the quoted line, PR 4b moved it)
- Modify: `execution_orders/upbit.py:24-27` (`_build`) and `:71-75` (`parse`)
- Test: `tests/control_model.py:44`; `tests/orders_codecs.py` and `tests/launch_profile.py`, new tests at the end

**Interfaces:**
- Consumes: `LaunchProfile.universe_rule_sha256`, `RULE` in `tests/launch_profile.py` (PR 4b).
- Produces: `Order.time_in_force` in `{"gtc", "ioc"}` for Upbit; preflight `TIME_IN_FORCE_MISMATCH` unless a universe
  Upbit profile uses `ioc` and a fixed one `gtc`; the IOC create body `... ("identifier", id), ("time_in_force",
  "ioc")`; an IOC create response without `time_in_force: "ioc"` parses to `unknown(identity_mismatch)`.

- [ ] **Step 1: Write the failing tests**

In `tests/control_model.py`, replace line 44:

```python
    _raises(lambda: replace(order, time_in_force="ioc"))
```

with:

```python
    ioc = replace(order, time_in_force="ioc")                         # Upbit takes gtc or ioc (spec 11)
    assert ioc.time_in_force == "ioc" and order_digest(ioc) != order_digest(order)
    _raises(lambda: replace(order, time_in_force="fok"))
    _raises(lambda: replace(order, venue="okx", symbol="BTC-USDT", quote_krw=D("1300"), time_in_force="ioc"))
    _raises(lambda: replace(order, venue="kis", market="nasd", symbol="AAPL", quantity=D("1"), quote_krw=D("1300"),
                            time_in_force="ioc"))
```

Append to the end of `tests/orders_codecs.py`:

```python
def test_upbit_ioc_body_is_additive_bound_and_its_end_comes_from_status():
    order = _order(time_in_force="ioc")
    request = upbit.prepare(order, _rules(order))
    assert request.body == (("market", "KRW-BTC"), ("side", "bid"), ("volume", "2"), ("price", "100"),
                            ("ord_type", "limit"), ("identifier", "fixtureOrderA"), ("time_in_force", "ioc"))
    gtc = _order()
    assert upbit.prepare(gtc, _rules(gtc)).body == (("market", "KRW-BTC"), ("side", "bid"), ("volume", "2"),
        ("price", "100"), ("ord_type", "limit"), ("identifier", "fixtureOrderA"))   # byte-identical gtc body
    validate_request(request)
    _refused(lambda: validate_request(replace(request, body=request.body[:-1])))
    assert upbit.parse(_upbit_response(time_in_force="ioc"), request).status == "accepted"
    for response in (_upbit_response(), _upbit_response(time_in_force="gtc")):
        result = upbit.parse(response, request)
        assert (result.status, result.code) == ("unknown", "identity_mismatch"), result
    cancel = upbit.prepare_cancel(order, UUID)
    result = upbit.parse(_upbit_response(state="cancel", executed_volume="1", remaining_volume="1"), cancel)
    assert (result.status, result.filled_quantity) == ("accepted", D("1"))
    status = upbit.prepare_status(order, UUID)
    result = upbit.parse(_upbit_response(state="cancel", executed_volume="1", remaining_volume="1"), status)
    assert (result.status, result.filled_quantity) == ("canceled", D("1"))
```

Append to the end of `tests/launch_profile.py`:

```python
def test_a_universe_profile_requires_ioc_and_a_fixed_upbit_profile_keeps_gtc():
    fixed = fixture_profile()
    universe = replace(fixed, universe_rule_sha256=RULE, time_in_force="ioc")
    assert "TIME_IN_FORCE_MISMATCH" not in preflight_profile(fixed, now=NOW).reasons
    assert "TIME_IN_FORCE_MISMATCH" not in preflight_profile(universe, now=NOW).reasons
    assert "TIME_IN_FORCE_MISMATCH" in preflight_profile(replace(universe, time_in_force="gtc"), now=NOW).reasons
    assert "TIME_IN_FORCE_MISMATCH" in preflight_profile(replace(fixed, time_in_force="ioc"), now=NOW).reasons
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus control control_model/test_every_order_field_binds
focus control orders_codecs/test_upbit_ioc_body
focus launch launch_profile/test_a_universe_profile_requires_ioc
```

Expected: exit 1 for each: `ValueError: unsupported time_in_force` for the first two; the third fails its second
assertion (the universe profile with `ioc` reports `TIME_IN_FORCE_MISMATCH`).

- [ ] **Step 3: Accept IOC where the spec allows it**

In `execution_control/model.py`, replace lines 95-97:

```python
    expected_tif = "day" if order.venue == "kis" else "gtc"
    if type(order.time_in_force) is not str or order.time_in_force != expected_tif:
        raise ValueError("unsupported time_in_force")
```

with:

```python
    # Spec 11: Upbit takes gtc or ioc; KIS stays day and OKX gtc.
    expected_tif = ("day",) if order.venue == "kis" else ("gtc", "ioc") if order.venue == "upbit" else ("gtc",)
    if type(order.time_in_force) is not str or order.time_in_force not in expected_tif:
        raise ValueError("unsupported time_in_force")
```

In `execution_launch/profile.py`, replace (fd85850 line 328):

```python
        expected_tif = "day" if venue == "kis" else "gtc"
```

with:

```python
        # Spec 11: a universe Upbit profile sends IOC orders; a fixed Upbit profile keeps gtc.
        expected_tif = ("day" if venue == "kis" else
                        "ioc" if venue == "upbit" and profile.universe_rule_sha256 is not None else "gtc")
```

In `execution_orders/upbit.py`, replace lines 24-27:

```python
        body = (("market", order.symbol), ("side", "bid" if order.side == "buy" else "ask"),
                ("volume", decimal_text(order.quantity)), ("price", decimal_text(order.limit_price)),
                ("ord_type", "limit"), ("identifier", order.client_id))
        return make_request(order, operation=operation, method="POST", path="/v1/orders", body=body)
```

with:

```python
        body = (("market", order.symbol), ("side", "bid" if order.side == "buy" else "ask"),
                ("volume", decimal_text(order.quantity)), ("price", decimal_text(order.limit_price)),
                ("ord_type", "limit"), ("identifier", order.client_id))
        if order.time_in_force == "ioc":                # spec 11: only IOC adds a key; the gtc body is unchanged
            body += (("time_in_force", "ioc"),)
        return make_request(order, operation=operation, method="POST", path="/v1/orders", body=body)
```

Replace lines 71-75:

```python
        if (data.get("identifier") != order.client_id or data.get("market") != order.symbol
                or data.get("side") != ("bid" if order.side == "buy" else "ask")
                or data.get("ord_type") != "limit" or number(data["price"], positive=True) != order.limit_price
                or number(data["volume"], positive=True) != order.quantity):
            return unknown(request, "identity_mismatch")
```

with:

```python
        if (data.get("identifier") != order.client_id or data.get("market") != order.symbol
                or data.get("side") != ("bid" if order.side == "buy" else "ask")
                or data.get("ord_type") != "limit" or number(data["price"], positive=True) != order.limit_price
                or number(data["volume"], positive=True) != order.quantity
                or (request.operation == "create" and order.time_in_force == "ioc"
                    and data.get("time_in_force") != "ioc")):
            return unknown(request, "identity_mismatch")
```

- [ ] **Step 4: Run the order, model and profile tests**

```bash
focus control control_model/
focus control orders_codecs/
focus control orders_lifecycle/
focus launch launch_profile/
focus control control_guards/test_renewal_
```

Expected: every row `PASS`, exit 0 for each. `execution_control/model.py` and `execution_launch/profile.py` change
only function bodies and add no call to a reviewed callable, so the renewal pins do not move.

- [ ] **Step 5: Commit**

```bash
FILES="execution_control/model.py execution_launch/profile.py execution_orders/upbit.py tests/control_model.py tests/orders_codecs.py tests/launch_profile.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(orders): IOC limit orders for universe Upbit profiles

Upbit orders take gtc or ioc; KIS stays day and OKX gtc. A universe
profile must use ioc and a fixed Upbit profile keeps gtc. The create body
gains time_in_force=ioc only for IOC orders, so the gtc body is byte for
byte unchanged, and an IOC create response without time_in_force=ioc is
unknown(identity_mismatch) (spec section 11).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 4: Renewal to another coin with `allow_symbol_change`

**Files:**
- Modify: `execution_launch/instrument_refresh.py:54-56` (`renew_profile`), `:59-74` (`_renew_profile` head) and
  `:94` (fd85850; `:96` after PR 4b)
- Modify: `tests/renewal_boundaries.py:34` (pin)
- Test: `tests/launch_instrument_refresh.py:16` (import), new tests at the end

**Interfaces:**
- Consumes: Tasks 1 to 3; PR 4b's universe `profile_contract_digest` and `rule_terms_digest`.
- Produces: `renew_profile(profile, observation, *, now, allow_symbol_change: bool = False) -> RulesRenewal`;
  `RENEWAL_SYMBOL_CHANGE_REFUSED` when the flag is not a bool or is `True` for a fixed profile.

- [ ] **Step 1: Write the failing tests**

In `tests/launch_instrument_refresh.py`, replace line 16:

```python
from execution_launch.profile import profile_contract_digest, profile_digest, rule_terms_digest
```

with:

```python
from execution_launch.profile import preflight_profile, profile_contract_digest, profile_digest, rule_terms_digest
```

Append to the end of the file:

```python
def universe_profile(auth=None, symbol="KRW-BTC"):
    auth = auth or universe_authority()
    base = fixture_profile(NOW)
    return replace(base, account_scope=auth.account_scope, symbol=symbol, time_in_force="ioc",
        universe_rule_sha256=RULE, instrument_rules=replace(base.instrument_rules, symbol=symbol,
            lot_size=auth.lot_size, min_quantity=auth.min_quantity, source_digest=T.authority_digest(auth)))


def test_universe_renewal_moves_to_another_coin_only_with_the_flag_and_keeps_its_contract():
    with registries():
        auth = universe_authority()
        p = universe_profile(auth)
        o = universe_observed("KRW-ETH", auth=auth, tick="5")
        refused(lambda: R.renew_profile(p, o, now=o.checked_at), "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH")
        refused(lambda: R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=1),
                "RENEWAL_SYMBOL_CHANGE_REFUSED")
        r = R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True)
        assert (r.profile.symbol, r.profile.instrument_rules.symbol) == ("KRW-ETH", "KRW-ETH")
        assert r.profile.instrument_rules.tick_size == D("5") and r.profile.time_in_force == "ioc"
        assert profile_contract_digest(r.profile) == profile_contract_digest(p) == r.contract_digest
        assert R.validate_renewal(r, previous_profile=p, now=o.checked_at) == r.profile
        assert preflight_profile(r.profile, now=o.checked_at).profile_complete
        back = universe_observed("KRW-BTC", o.checked_at+timedelta(seconds=10), auth=auth)
        again = R.renew_profile(r.profile, back, now=back.checked_at, allow_symbol_change=True)
        assert again.profile.symbol == "KRW-BTC" and again.contract_digest == r.contract_digest


def test_a_fixed_profile_refuses_the_symbol_change_flag_itself():
    with registries():
        p = profile(); o = observed()
        refused(lambda: R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True),
                "RENEWAL_SYMBOL_CHANGE_REFUSED")
        assert R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=False).profile.symbol == "KRW-BTC"


def test_a_coin_below_the_cap_is_not_buyable_but_a_held_coin_still_renews_and_sells():
    with registries():
        auth = universe_authority()
        p = universe_profile(auth)
        o = universe_observed("KRW-BTC", auth=auth, max_total="1000000")
        assert not T.within_buy_cap(o)                                 # left out of the allow-list (PR 4e)
        r = R.renew_profile(p, o, now=o.checked_at)
        sell = Order(client_id="synthetic-exit", account_scope="test-scope", venue="upbit", market="spot",
                     symbol="KRW-BTC", side="sell", quantity=D("900"), limit_price=D("1000"), quote_krw=D("1"),
                     time_in_force="ioc")
        R.validate_observed_order(sell, r.profile.instrument_rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(sell, side="buy", quantity=D("1500")),
            r.profile.instrument_rules, now=o.checked_at), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch launch_instrument_refresh/test_universe_renewal_moves
focus launch launch_instrument_refresh/test_a_fixed_profile_refuses
focus launch launch_instrument_refresh/test_a_coin_below_the_cap
```

Expected: exit 1 for the first two with `TypeError: renew_profile() got an unexpected keyword argument
'allow_symbol_change'` (the first test's opening refusal passes, then the keyword fails); the third `PASS`es already
(it needs no new code and pins the held-coin path).

- [ ] **Step 3: Add the flag and move the symbol**

In `execution_launch/instrument_refresh.py`, replace lines 54-56:

```python
def renew_profile(profile, observation, *, now):
    with _LOCK:
        return _renew_profile(profile, observation, now=now)
```

with:

```python
def renew_profile(profile, observation, *, now, allow_symbol_change=False):
    with _LOCK:
        return _renew_profile(profile, observation, now=now, allow_symbol_change=allow_symbol_change)
```

Replace lines 59-74:

```python
def _renew_profile(profile, observation, *, now):
    """Create a fresh snapshot only for identical reviewed terms and scope.

    Initial stale profile snapshots can be replaced by a genuinely new read.
    Once a contract has a process-local head, forks and old snapshots refuse.
    A receipt cannot be reused to refresh another profile/strategy in this process.
    """
    _time(now)
    _require(type(profile) is LaunchProfile and type(profile.instrument_rules) is InstrumentRules,
             "RENEWAL_PROFILE_RULES_REQUIRED")
    _require((profile.venue, profile.market, profile.quote_currency) == ("upbit", "spot", "KRW"),
             "RENEWAL_VENUE_UNSUPPORTED")
    verified = validate_issued_observation(observation, now=now)
    _require(profile.account_scope == verified.authority.account_scope
             and profile.symbol == verified.rules.symbol,
             "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH")
```

with:

```python
def _renew_profile(profile, observation, *, now, allow_symbol_change):
    """Create a fresh snapshot only for identical reviewed terms and scope.

    Initial stale profile snapshots can be replaced by a genuinely new read.
    Once a contract has a process-local head, forks and old snapshots refuse.
    A receipt cannot be reused to refresh another profile/strategy in this process.
    Only a universe profile may move to another coin, and only with allow_symbol_change
    (spec section 10); every refusing check below still runs before the head moves.
    """
    _time(now)
    _require(type(profile) is LaunchProfile and type(profile.instrument_rules) is InstrumentRules,
             "RENEWAL_PROFILE_RULES_REQUIRED")
    _require(type(allow_symbol_change) is bool
             and (not allow_symbol_change or profile.universe_rule_sha256 is not None),
             "RENEWAL_SYMBOL_CHANGE_REFUSED")
    _require((profile.venue, profile.market, profile.quote_currency) == ("upbit", "spot", "KRW"),
             "RENEWAL_VENUE_UNSUPPORTED")
    verified = validate_issued_observation(observation, now=now)
    _require(profile.account_scope == verified.authority.account_scope
             and (profile.symbol == verified.rules.symbol or allow_symbol_change),
             "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH")
```

Replace (fd85850 line 94):

```python
    current = replace(profile, instrument_rules=verified.rules)
```

with:

```python
    current = replace(profile, symbol=verified.rules.symbol, instrument_rules=verified.rules)
```

- [ ] **Step 4: Run the renewal, runner and coordinator tests**

```bash
focus launch launch_instrument_refresh/
focus launch launch_runner/
focus launch launch_coordinator/
```

Expected: every row `PASS`, exit 0 for each (the coordinator still calls `renew_profile` without the flag).

- [ ] **Step 5: Review the renewal surface change and update its pin**

```bash
focus control control_guards/test_renewal_validation
```

Expected before the update: exit 1, `AssertionError: ['execution_launch/instrument_refresh.py: initialization
surface changed']`. Review: `git diff -- execution_launch/instrument_refresh.py` must show, outside function bodies,
exactly the new keyword-only parameter of `renew_profile` (default `False`) and of `_renew_profile` (no default).

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_launch/instrument_refresh.py').read_text(encoding='utf-8')))"
```

Expected output: `11f9aaf16bb9528b30146a8887ec0b67a40c32baefd6fc81abd363d123539467`.

In `tests/renewal_boundaries.py`, replace line 34:

```python
    "execution_launch/instrument_refresh.py": "f915417195062fea05a820756b3d4032c95eeef546a395f912bc968eb67591e5",
```

with:

```python
    "execution_launch/instrument_refresh.py": "11f9aaf16bb9528b30146a8887ec0b67a40c32baefd6fc81abd363d123539467",
```

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS`, exit 0.

- [ ] **Step 6: Commit**

```bash
FILES="execution_launch/instrument_refresh.py tests/launch_instrument_refresh.py tests/renewal_boundaries.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(launch): universe renewal to another coin

renew_profile gets allow_symbol_change. Only a universe profile may set
it; the renewed profile takes the observed symbol and rules, keeps its
contract digest and head key, and passes preflight. Every refusing check
still runs before the head moves; a fixed profile refuses the flag
(spec section 10). The renewal surface pin is updated after review.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 5: Rehearsal audit `universe_terms_authority`

**Files:**
- Modify: `tools/owner/rehearsal.py:34` (import), `:100-110` (`AccountAudit`), `:116` (schema), `:166-181`
  (terms parse and return), new `_terms_authority` after `:181`, `:362-367` (`build_rehearsal`)
- Test: `tests/launch_owner_rehearsal.py`, new test at the end

**Interfaces:**
- Consumes: Task 1.
- Produces: `AccountAudit.universe_terms_authority: UniverseTermsAuthority | None = None`; the audit accepts the old
  key set or the old set plus `universe_terms_authority`; both authorities present refuses
  `REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID`; `_terms_authority(profile, audit) -> TermsAuthority |
  UniverseTermsAuthority | None` (`REHEARSAL_TERMS_PROFILE_MISMATCH`).

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/launch_owner_rehearsal.py`:

```python
def test_the_audit_carries_a_v1_or_a_v2_terms_authority_and_the_profile_picks_its_own():
    from execution_accounts import instrument_terms as T
    rule = hashlib.sha256(b"fixture-universe-rule").hexdigest()
    with fixture() as e:
        body = json.loads(e.raw_audit)
        terms_doc = hashlib.sha256(b"SYNTHETIC TEST ONLY: reviewed instrument_terms").hexdigest()
        body["source_documents"].append({"kind": "instrument_terms", "path": str(e.folder / "instrument_terms.txt"),
                                         "sha256": terms_doc})
        identity = next(d["sha256"] for d in body["source_documents"] if d["kind"] == "credential_identity")
        v2 = T.UniverseTermsAuthority(account_scope=body["account_scope"], universe_sha256=rule, lot_size=D("0.01"),
            min_quantity=D("0.01"), maximum_notional_krw=D("2000000"), provenance_sha256=terms_doc,
            identity_binding_sha256=identity, valid_from=e.fake.now-timedelta(days=1),
            valid_until=e.fake.now+timedelta(days=1))
        v1 = T.TermsAuthority(symbol="KRW-BTC", **{k: v for k, v in asdict(v2).items() if k != "universe_sha256"})

        def raw(**authorities):
            return json.dumps(body | {k: plain(asdict(v)) for k, v in authorities.items()}).encode()
        audit = R.parse_account_audit(raw(universe_terms_authority=v2))
        assert audit.universe_terms_authority == v2 and audit.terms_authority is None
        fixed = R.parse_account_audit(raw(terms_authority=v1))
        assert fixed.terms_authority == v1 and fixed.universe_terms_authority is None
        assert R.parse_account_audit(e.raw_audit).universe_terms_authority is None     # the old key set still parses
        refused(lambda: R.parse_account_audit(raw(terms_authority=v1, universe_terms_authority=v2)),
                "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        refused(lambda: R.parse_account_audit(raw(universe_terms_authority=replace(v2, identity_binding_sha256="f"*64))),
                "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        bad = json.loads(raw(universe_terms_authority=v2))
        bad["universe_terms_authority"]["symbol"] = "KRW-BTC"
        refused(lambda: R.parse_account_audit(json.dumps(bad).encode()), "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")

        def profile(universe, symbol, authority):
            return SimpleNamespace(universe_rule_sha256=universe, symbol=symbol,
                                   instrument_rules=SimpleNamespace(source_digest=T.authority_digest(authority)))
        assert R._terms_authority(profile(rule, "KRW-ETH", v2), audit) == v2
        refused(lambda: R._terms_authority(profile(None, "KRW-BTC", v2), audit), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        refused(lambda: R._terms_authority(profile("f"*64, "KRW-ETH", v2), audit), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        assert R._terms_authority(profile(None, "KRW-BTC", v1), fixed) == v1
        refused(lambda: R._terms_authority(profile(rule, "KRW-BTC", v1), fixed), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        refused(lambda: R._terms_authority(profile(None, "KRW-ETH", v1), fixed), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        assert R._terms_authority(profile(None, "KRW-BTC", v1), R.parse_account_audit(e.raw_audit)) is None
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
focus launch launch_owner_rehearsal/test_the_audit_carries
```

Expected: exit 1, `FAIL ... RehearsalError: REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID` (the closed key set refuses
`universe_terms_authority`).

- [ ] **Step 3: Parse the v2 authority and pick by profile**

In `tools/owner/rehearsal.py`, replace line 34:

```python
from execution_accounts.instrument_terms import E1UpbitTermsSource, TermsAuthority, authority_digest
```

with:

```python
from execution_accounts.instrument_terms import (E1UpbitTermsSource, TermsAuthority, UniverseTermsAuthority,
                                                 authority_digest)
```

Replace lines 108-110 (the end of `AccountAudit`):

```python
    terms_authority: TermsAuthority | None
    source_documents: tuple[tuple[str, str, str], ...]  # kind, explicit private path, reviewed bytes digest
    raw_sha256: str
```

with:

```python
    terms_authority: TermsAuthority | None
    source_documents: tuple[tuple[str, str, str], ...]  # kind, explicit private path, reviewed bytes digest
    raw_sha256: str
    universe_terms_authority: UniverseTermsAuthority | None = None   # v2, spec section 10; never with v1
```

Replace line 116:

```python
    body = _schema(_object(raw), _AUDIT_FIELDS, "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")
```

with:

```python
    body = _object(raw)
    # The old key set, or the old set plus the v2 authority (spec section 10).
    optional = {"universe_terms_authority"} if type(body) is dict and "universe_terms_authority" in body else set()
    _schema(body, _AUDIT_FIELDS | optional, "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")
```

Replace lines 177-181:

```python
        authority_digest(terms)
    return AccountAudit(account_scope=scope, window_digest=_sha(body["deployment_window_digest"]),
        baseline_anchor_sha256=_sha(body["baseline_anchor_sha256"]), anchor=anchor, coverage=coverage,
        fees=tuple(fees), terms_authority=terms, source_documents=tuple(documents),
        raw_sha256=hashlib.sha256(raw).hexdigest())
```

with:

```python
        authority_digest(terms)
    universe_terms = None
    if body.get("universe_terms_authority") is not None:
        u = _dataclass_body(body["universe_terms_authority"], UniverseTermsAuthority)
        _need(terms is None and u["account_scope"] == scope
              and u["provenance_sha256"] in by_kind.get("instrument_terms", ())
              and u["identity_binding_sha256"] == by_kind["credential_identity"][0],
              "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        universe_terms = UniverseTermsAuthority(account_scope=scope, universe_sha256=_sha(u["universe_sha256"]),
            **{name: _amount(u[name]) for name in ("lot_size", "min_quantity", "maximum_notional_krw")},
            provenance_sha256=_sha(u["provenance_sha256"]),
            identity_binding_sha256=_sha(u["identity_binding_sha256"]),
            valid_from=_time(u["valid_from"]), valid_until=_time(u["valid_until"]))
        authority_digest(universe_terms)
    return AccountAudit(account_scope=scope, window_digest=_sha(body["deployment_window_digest"]),
        baseline_anchor_sha256=_sha(body["baseline_anchor_sha256"]), anchor=anchor, coverage=coverage,
        fees=tuple(fees), terms_authority=terms, source_documents=tuple(documents),
        raw_sha256=hashlib.sha256(raw).hexdigest(), universe_terms_authority=universe_terms)


def _terms_authority(profile, audit):
    """The audit's terms authority for this profile: v2 for a universe profile, v1 for a fixed one (spec section 10).

    None when the audit carries neither. The other version must be absent and the authority's digest must be the
    profile's rules source.
    """
    universe = profile.universe_rule_sha256 is not None
    authority = audit.universe_terms_authority if universe else audit.terms_authority
    other = audit.terms_authority if universe else audit.universe_terms_authority
    if authority is None and other is None:
        return None
    _need(other is None and authority is not None
          and (authority.universe_sha256 == profile.universe_rule_sha256 if universe
               else authority.symbol == profile.symbol)
          and authority_digest(authority) == profile.instrument_rules.source_digest,
          "REHEARSAL_TERMS_PROFILE_MISMATCH")
    return authority
```

Replace lines 362-367:

```python
    terms = None
    if audit.terms_authority is not None:
        _need(audit.terms_authority.symbol == comp.profile.symbol
              and authority_digest(audit.terms_authority) == comp.profile.instrument_rules.source_digest,
              "REHEARSAL_TERMS_PROFILE_MISMATCH")
        terms = _TermsSource(E1UpbitTermsSource(authority=audit.terms_authority, clock=clock), guard)
```

with:

```python
    terms = None
    authority = _terms_authority(comp.profile, audit)
    if authority is not None:
        terms = _TermsSource(E1UpbitTermsSource(authority=authority, clock=clock), guard)
```

- [ ] **Step 4: Run the rehearsal tests**

```bash
focus launch launch_owner_rehearsal/
focus launch owner_guards/
```

Expected: every row `PASS`, exit 0 for each.

- [ ] **Step 5: Commit**

```bash
FILES="tools/owner/rehearsal.py tests/launch_owner_rehearsal.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(owner): rehearsal audit carries a v2 terms authority

The private account audit may carry universe_terms_authority beside the
old key set, never together with terms_authority, bound to the same
reviewed documents. _terms_authority picks v2 for a universe profile and
v1 for a fixed one and checks its digest against the profile's rules
(spec section 10). The audit bytes change only when the owner adds it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 6: Unlisted held coins in the account capture and the provider

**Files:**
- Modify: `execution_accounts/upbit_collector.py:34-35` (`_ALLOWED`), `:85-88` (fetch dispatch), `:390-392` (listing
  read), `:416-423` (positions)
- Modify: `execution_accounts/model.py:21` (`canonical`), `:73` (`Position`)
- Modify: `execution_accounts/provider.py:234`
- Modify: `tests/renewal_boundaries.py:29` (pin)
- Test: `tests/accounts_guards.py:15-16`, `:151`, `:211`, `:215`; `tests/accounts_collector.py:63-64`, `:82-85`, new
  tests at the end; `tests/launch_account_interval.py:120-123`; `tests/accounts_provider.py` and
  `tests/launch_runner.py`, new tests at the end

**Interfaces:**
- Consumes: PR 2's `("GET", "/v1/market/all")` E1 endpoint.
- Produces: `Position.unlisted: bool | None = None`; the provider accepts price 0 only with `unlisted is True`
  (`POSITION_UNLISTED_MARKER_INVALID`, `POSITION_UNLISTED_PRICE_INVALID`); `E1UpbitSource.fetch` accepts
  `/v1/market/all` and `/v1/orderbook`.

- [ ] **Step 1: Write the failing tests**

In `tests/accounts_guards.py`, replace lines 15-16:

```python
COLLECTOR_ROUTES = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed",
                              "/v1/order", "/v1/deposits", "/v1/withdraws", "/v1/ticker"})
```

with:

```python
COLLECTOR_ROUTES = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed",
                              "/v1/order", "/v1/deposits", "/v1/withdraws", "/v1/ticker",
                              "/v1/market/all", "/v1/orderbook"})          # spec 11: listing and thin-coin book
```

Replace line 151:

```python
                  "/v1/orderbook", "/v1/withdraws/coin_addresses"):
```

with:

```python
                  "/v1/withdraws/coin_addresses"):
```

Replace line 211:

```python
    for path in ("provider.py", "upbit_collector.py", "nested/quotes.py", ""):
```

with:

```python
    for path in ("provider.py", "nested/quotes.py", ""):
```

Replace line 215:

```python
    for route in COLLECTOR_ROUTES | {"/v1/orders", "/v1/orderbooks"}:
```

with:

```python
    for route in (COLLECTOR_ROUTES - {"/v1/orderbook"}) | {"/v1/orders", "/v1/orderbooks"}:
```

In `tests/accounts_collector.py`, replace lines 63-64 (the end of `SyntheticSource.__init__`):

```python
        self.deposits = []; self.withdrawals = []
        self.change_balances = False
```

with:

```python
        self.deposits = []; self.withdrawals = []
        self.change_balances = False
        self.listed = ["KRW-BTC"]                                       # market/all
```

Replace lines 82-85:

```python
        elif path == "/v1/ticker":
            body = [dict(market="KRW-BTC", trade_price=10000, timestamp=int(NOW.timestamp()*1000),
                         trade_timestamp=int(NOW.timestamp()*1000))]
        else:
```

with:

```python
        elif path == "/v1/ticker":
            body = [dict(market="KRW-BTC", trade_price=10000, timestamp=int(NOW.timestamp()*1000),
                         trade_timestamp=int(NOW.timestamp()*1000))]
        elif path == "/v1/market/all":
            body = None if self.listed is None else [dict(market=market) for market in self.listed]
        else:
```

Append to the end of `tests/accounts_collector.py`:

```python
def test_a_listed_coin_keeps_its_ticker_mark_after_one_listing_read():
    source = SyntheticSource(with_order=True)
    result = collect(source)
    paths = [path for path, _ in source.calls]
    assert paths.count("/v1/market/all") == 1 and paths.index("/v1/market/all") < paths.index("/v1/ticker")
    assert (("is_details", "true"),) in [params for path, params in source.calls if path == "/v1/market/all"]
    position = result.bundle.accounts[0].positions[0]
    assert (position.price, position.unlisted) == (D("10000"), None)


def test_an_unlisted_coin_is_left_out_of_the_ticker_and_recorded_at_price_zero_with_its_read_time():
    source = SyntheticSource(with_order=True)
    source.listed = ["KRW-ETH"]
    result = collect(source)
    assert not any(path == "/v1/ticker" for path, _ in source.calls)
    position = result.bundle.accounts[0].positions[0]
    listing = next(r for r in result.receipts if r.path == "/v1/market/all")
    assert (position.symbol, position.units, position.price, position.unlisted) == ("KRW-BTC", D("1"), D("0"), True)
    assert position.asof == listing.received_at
    observation = build_observation(result.bundle, now=NOW)
    assert observation.risk.equity == D("89995")                    # cash only: the unlisted coin is worth 0
    assert observation.holdings[("upbit", SCOPE, "spot", "KRW-BTC")] == D("1")


def test_a_failed_listing_read_inside_the_capture_fails_closed():
    class NoListing(SyntheticSource):
        def fetch(self, path, params):
            if path == "/v1/market/all":
                raise EvidenceError("COLLECTOR_AUTHENTICATED_READ_FAILED")
            return super().fetch(path, params)
    refusal(lambda: collect(NoListing(with_order=True)), "COLLECTOR_AUTHENTICATED_READ_FAILED")
    source = SyntheticSource(with_order=True)
    source.listed = None                                               # a JSON null is not a listing
    refusal(lambda: collect(source), "COLLECTOR_ROWS_INVALID")


def test_e1_binding_fetches_the_listing_and_the_book_as_fixed_gets():
    raw = b'[]'
    answer = Answer(body=[], server_utc=NOW, received_utc=NOW, sha256=hashlib.sha256(raw).hexdigest(), raw_body=raw)
    with tempfile.TemporaryDirectory() as temporary:
        with patch.dict(os.environ, {"TRADEGEN_HOME":temporary,"UPBIT_ACCESS_KEY":"","UPBIT_SECRET_KEY":""}, clear=True):
            with patch("execution_accounts.upbit_collector.request", return_value=answer) as stub:
                source = E1UpbitSource(account_scope=SCOPE, state_directory=Path(temporary), clock=lambda: NOW)
                source.fetch("/v1/market/all", (("is_details", "true"),))
                source.fetch("/v1/orderbook", (("markets", "KRW-BTC"), ("level", "0")))
                assert [c.args for c in stub.call_args_list] == [
                    ("upbit", "GET", "/v1/market/all", (("is_details", "true"),)),
                    ("upbit", "GET", "/v1/orderbook", (("markets", "KRW-BTC"), ("level", "0")))]
```

In `tests/launch_account_interval.py`, replace lines 120-123:

```python
        elif path == "/v1/ticker":
            body = [dict(market=market, trade_price=self.ticker, timestamp=_ms(now), trade_timestamp=_ms(now))
                    for market in query["markets"].split(",")]
        else:
```

with:

```python
        elif path == "/v1/ticker":
            body = [dict(market=market, trade_price=self.ticker, timestamp=_ms(now), trade_timestamp=_ms(now))
                    for market in query["markets"].split(",")]
        elif path == "/v1/market/all":                                    # every held coin is listed
            body = [dict(market="KRW-" + row["currency"]) for row in self.balances if row["currency"] != "KRW"]
        else:
```

Append to the end of `tests/accounts_provider.py`:

```python
def test_price_zero_needs_the_unlisted_marker_and_the_canonical_body_omits_an_absent_marker():
    from execution_accounts.model import canonical
    value = bundle(fills=(fill(),), opening=D("1000"), cash=D("798"), units=D("2"), orders=(order(),))
    assert build_observation(value, now=NOW).risk.equity == D("1038")          # 798 + 2 x 120
    position = value.accounts[0].positions[0]
    unlisted = change_account(value, positions=(replace(position, price=D("0"), unlisted=True),))
    observation = build_observation(unlisted, now=NOW)
    assert observation.risk.equity == D("798")
    assert observation.holdings[("upbit", SCOPE, "spot", "KRW-BTC")] == D("2")
    refused(change_account(value, positions=(replace(position, price=D("0")),)), "AMOUNT_OUT_OF_RANGE")
    refused(change_account(value, positions=(replace(position, unlisted=True),)), "POSITION_UNLISTED_PRICE_INVALID")
    for marker in (False, 1, "true"):
        refused(change_account(value, positions=(replace(position, price=D("0"), unlisted=marker),)),
                "POSITION_UNLISTED_MARKER_INVALID")
    assert "unlisted" not in canonical(position)
    assert canonical(replace(position, price=D("0"), unlisted=True))["unlisted"] is True
```

Append to the end of `tests/launch_runner.py`:

```python
def _with_unlisted_dust(env):
    # Spec 11: the provider keeps an unlisted coin's units in holdings and adds nothing to equity.
    env.observation = replace(env.observation,
        positions=replace(env.observation.positions, holdings={('upbit','BTC'):0.001, ('upbit','XYZ'):5.0}),
        holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001'),
                  ('upbit','fixture-account','spot','KRW-XYZ'):D('5')})


def test_unlisted_dust_next_to_the_held_coin_leaves_exit_cancel_and_ticks_working():
    with runner_fixture() as env:
        env.runner.launch_session = None
        _with_unlisted_dust(env)
        env.signal = replace(env.signal, action='exit')
        report = env.runner.tick(now=env.now)
        assert report.status == 'submitted' and report.order_status == 'ACKNOWLEDGED', report
        assert len(creates(env)) == 1
        canceled = env.runner.cancel(report.client_id, now=env.now)
        assert canceled.status in ('ACKNOWLEDGED', 'CANCEL_REQUESTED'), canceled
    with runner_fixture() as env:
        env.runner.stop(); env.runner.evidence = None
        _with_unlisted_dust(env)
        state = env.runner.submit_exit(replace(env.signal, action='exit'), now=env.now)
        assert state.status == 'ACKNOWLEDGED' and len(creates(env)) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus accounts accounts_guards/
focus launch accounts_collector/
focus accounts accounts_provider/test_price_zero
focus launch launch_runner/test_unlisted_dust
```

Expected: `accounts_guards/` exits 0 already: `READ_ROUTES` (and the macro harness, which calls the same
`problems`) reads the edited `COLLECTOR_ROUTES`, so the Step 1 guard edits only widen the routes the collector may
name; Step 4 reruns the module against the new collector code. Exit 1 for the next two:
`accounts_collector/test_e1_binding_fetches_the_listing...` fails with `COLLECTOR_ENDPOINT_REFUSED`, the listed
and unlisted tests fail (no `/v1/market/all` call; the unlisted case reads the ticker); the provider test fails with
`TypeError: ... unexpected keyword argument 'unlisted'`. The runner test `PASS`es already (the runner trades only its
own symbol); it pins that behavior.

- [ ] **Step 3: Read the listing and record unlisted coins**

In `execution_accounts/upbit_collector.py`, replace lines 34-35:

```python
_ALLOWED = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/order",
                      "/v1/deposits", "/v1/withdraws", "/v1/ticker"})
```

with:

```python
_ALLOWED = frozenset({"/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/order",
                      "/v1/deposits", "/v1/withdraws", "/v1/ticker", "/v1/market/all", "/v1/orderbook"})
```

Replace lines 85-88:

```python
                elif path == "/v1/withdraws":
                    answer = request("upbit", "GET", "/v1/withdraws", params)
                else:
                    answer = request("upbit", "GET", "/v1/ticker", params)
```

with:

```python
                elif path == "/v1/withdraws":
                    answer = request("upbit", "GET", "/v1/withdraws", params)
                elif path == "/v1/market/all":
                    answer = request("upbit", "GET", "/v1/market/all", params)
                elif path == "/v1/orderbook":
                    answer = request("upbit", "GET", "/v1/orderbook", params)
                else:
                    answer = request("upbit", "GET", "/v1/ticker", params)
```

Replace lines 390-392:

```python
    markets = tuple(sorted("KRW-"+base for base, amount in balances.items() if base != "KRW" and amount > 0))
    marks = {}
    if markets:
```

with:

```python
    held = tuple(sorted("KRW-"+base for base, amount in balances.items() if base != "KRW" and amount > 0))
    # Spec 11: the listing first. A held coin missing from it is unlisted: no ticker read, price 0, the read's time.
    listing = _rows(capture.get("/v1/market/all", (("is_details", "true"),))) if held else []
    listing_at = capture.receipts[-1].received_at
    current = {row.get("market") for row in listing if type(row.get("market")) is str}
    markets = tuple(symbol for symbol in held if symbol in current)
    marks = {}
    if markets:
```

Replace lines 416-423:

```python
    positions = []
    for symbol in markets:
        price, at, published = marks[symbol]
        require(timedelta(0) <= observed-at <= timedelta(seconds=30)
                and timedelta(0) <= observed-published <= timedelta(seconds=30),
                "COLLECTOR_TICKER_STALE_OR_FUTURE")
        positions.append(Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW",
            units=balances[symbol[4:]], price=price, asof=at))
```

with:

```python
    positions = []
    for symbol in held:
        if symbol not in current:
            price, at, unlisted = _ZERO, listing_at, True
        else:
            price, at, published = marks[symbol]
            unlisted = None
            require(timedelta(0) <= observed-at <= timedelta(seconds=30)
                    and timedelta(0) <= observed-published <= timedelta(seconds=30),
                    "COLLECTOR_TICKER_STALE_OR_FUTURE")
        positions.append(Position(market="spot", symbol=symbol, base_currency=symbol[4:], quote_currency="KRW",
            units=balances[symbol[4:]], price=price, asof=at, unlisted=unlisted))
```

In `execution_accounts/model.py`, replace line 21:

```python
        return {f.name: canonical(getattr(value, f.name)) for f in fields(value)}
```

with:

```python
        # Position.unlisted is left out while None, so every older evidence digest is unchanged (spec 11).
        return {f.name: canonical(getattr(value, f.name)) for f in fields(value)
                if not (f.name == "unlisted" and getattr(value, f.name) is None)}
```

Replace line 73 (the last field of `Position`):

```python
    asof: datetime
```

(inside `class Position`, after `price: Decimal`) with:

```python
    asof: datetime
    unlisted: bool | None = None          # True only for a held coin missing from market/all, at price 0 (spec 11)
```

In `execution_accounts/provider.py`, replace line 234:

```python
        _amount(position.units); _amount(position.price, positive=True); _fresh(position.asof, now)
```

with:

```python
        _require(position.unlisted is None or position.unlisted is True, "POSITION_UNLISTED_MARKER_INVALID")
        _amount(position.units); _amount(position.price, positive=position.unlisted is not True)
        _fresh(position.asof, now)
        _require(position.unlisted is not True or position.price == 0, "POSITION_UNLISTED_PRICE_INVALID")
```

- [ ] **Step 4: Run the account and launch tests that read the collector**

```bash
focus accounts accounts_guards/
focus accounts accounts_provider/
focus accounts accounts_continuous/
focus launch accounts_collector/
focus launch launch_account_interval/
focus launch launch_runner/
focus launch launch_owner_rehearsal/
focus launch launch_coordinator/
```

Expected: every row `PASS`, exit 0 for each. Flat captures still hold 9 (collector) and 11 (interval) receipts.

- [ ] **Step 5: Review the renewal surface change and update its pin**

```bash
focus control control_guards/test_renewal_validation
```

Expected before the update: exit 1, `AssertionError: ['execution_accounts/model.py: initialization surface
changed']`. Review: `git diff -- execution_accounts/model.py` must show, outside function bodies, exactly the new
`unlisted: bool | None = None` field of `Position`.

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution_accounts/model.py').read_text(encoding='utf-8')))"
```

Expected output: `e7807322ce6b91df9ada3724e43d64fb39f40bac328bfbcbdd0150498e6d52a2`.

In `tests/renewal_boundaries.py`, replace line 29:

```python
    "execution_accounts/model.py": "a3afc9c2d728bd6ebf63aac20f9e46d515781c6a4cc4747dd8bfe7d33640552a",
```

with:

```python
    "execution_accounts/model.py": "e7807322ce6b91df9ada3724e43d64fb39f40bac328bfbcbdd0150498e6d52a2",
```

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS`, exit 0.

- [ ] **Step 6: Commit**

```bash
FILES="execution_accounts/upbit_collector.py execution_accounts/model.py execution_accounts/provider.py tests/renewal_boundaries.py tests/accounts_guards.py tests/accounts_collector.py tests/launch_account_interval.py tests/accounts_provider.py tests/launch_runner.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(accounts): unlisted held coins at price 0 with a marker

The Upbit capture reads market/all before the ticker whenever a coin is
held. A held coin missing from the listing is left out of the ticker and
recorded at price 0 with the listing's time and unlisted=True; the
provider accepts price 0 only with that marker. Position.unlisted is
left out of canonical bodies while None, so older digests are unchanged
(spec section 11). Collector routes gain market/all and orderbook.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 7: Thin coin marked at a fresh best bid

**Files:**
- Modify: `execution_accounts/upbit_collector.py` new `_best_bid` after `_ms` (`:123-125`); the book reads before
  `observed = instant(clock())` (fd85850 `:410`); the positions loop written in Task 6
- Test: `tests/accounts_collector.py` (`SyntheticSource`, `:329-336`, new test at the end)

**Interfaces:**
- Consumes: Task 6.
- Produces: `_best_bid(body, symbol) -> tuple[Decimal, datetime]`; codes `COLLECTOR_BOOK_INVALID`,
  `COLLECTOR_BOOK_STALE_OR_FUTURE`.

- [ ] **Step 1: Write the failing tests**

In `tests/accounts_collector.py`, in `SyntheticSource.__init__`, replace the line added in Task 6:

```python
        self.listed = ["KRW-BTC"]                                       # market/all
```

with:

```python
        self.listed = ["KRW-BTC"]                                       # market/all
        self.trade_at = NOW; self.book_at = NOW                         # ticker last trade, book time
```

Replace the ticker branch:

```python
        elif path == "/v1/ticker":
            body = [dict(market="KRW-BTC", trade_price=10000, timestamp=int(NOW.timestamp()*1000),
                         trade_timestamp=int(NOW.timestamp()*1000))]
```

with:

```python
        elif path == "/v1/ticker":
            body = [dict(market="KRW-BTC", trade_price=10000, timestamp=int(NOW.timestamp()*1000),
                         trade_timestamp=int(self.trade_at.timestamp()*1000))]
        elif path == "/v1/orderbook":
            body = [dict(market=dict(params)["markets"], level=0, timestamp=int(self.book_at.timestamp()*1000),
                         orderbook_units=[dict(ask_price=10100, bid_price=9900, ask_size=1, bid_size=1)])]
```

Replace lines 329-336 (the whole `test_fresh_ticker_metadata_cannot_hide_a_stale_last_trade`):

```python
def test_fresh_ticker_metadata_cannot_hide_a_stale_last_trade():
    class StaleTrade(SyntheticSource):
        def fetch(self,path,params):
            if path == "/v1/ticker":
                return receipt(path,params,[dict(market="KRW-BTC",trade_price=10000,
                    timestamp=int(NOW.timestamp()*1000),trade_timestamp=int((NOW-timedelta(minutes=1)).timestamp()*1000))])
            return super().fetch(path,params)
    refusal(lambda: collect(StaleTrade(with_order=True)), "COLLECTOR_TICKER_STALE_OR_FUTURE")
```

with:

```python
def test_fresh_ticker_metadata_cannot_hide_a_stale_last_trade_or_a_stale_book():
    for book_at in (NOW-timedelta(minutes=1), NOW-timedelta(seconds=11), NOW+timedelta(seconds=1)):
        source = SyntheticSource(with_order=True)
        source.trade_at, source.book_at = NOW-timedelta(minutes=1), book_at
        refusal(lambda: collect(source), "COLLECTOR_BOOK_STALE_OR_FUTURE")

    class EmptyBook(SyntheticSource):
        def fetch(self, path, params):
            if path == "/v1/orderbook":
                self.calls.append((path, params))
                return receipt(path, params, [])
            return super().fetch(path, params)
    source = EmptyBook(with_order=True)
    source.trade_at = NOW-timedelta(minutes=1)
    refusal(lambda: collect(source), "COLLECTOR_BOOK_INVALID")
```

Append to the end of the file:

```python
def test_a_thin_coin_with_a_stale_last_trade_is_marked_at_a_fresh_best_bid():
    source = SyntheticSource(with_order=True)
    source.trade_at = NOW-timedelta(minutes=1)
    result = collect(source)
    assert [params for path, params in source.calls if path == "/v1/orderbook"] == [(("markets", "KRW-BTC"),
                                                                                     ("level", "0"))]
    paths = [path for path, _ in source.calls]
    assert paths.index("/v1/orderbook") > max(i for i, path in enumerate(paths) if path == "/v1/withdraws")
    position = result.bundle.accounts[0].positions[0]
    assert (position.price, position.asof, position.unlisted) == (D("9900"), NOW, None)
    assert build_observation(result.bundle, now=NOW).risk.equity == D("99895")     # 89995 + 9900
    fresh = SyntheticSource(with_order=True)
    collect(fresh)
    assert not any(path == "/v1/orderbook" for path, _ in fresh.calls)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus launch accounts_collector/test_fresh_ticker_metadata
focus launch accounts_collector/test_a_thin_coin
```

Expected: exit 1 for each: the first fails with `AssertionError: ('COLLECTOR_TICKER_STALE_OR_FUTURE',
'COLLECTOR_BOOK_STALE_OR_FUTURE')`; the second with `EvidenceError` code `COLLECTOR_TICKER_STALE_OR_FUTURE`.

- [ ] **Step 3: Read and use the book**

In `execution_accounts/upbit_collector.py`, insert after `_ms` (line 125), with two blank lines on each side:

```python
def _best_bid(body, symbol):
    """(best bid, book time) of one level-0 book of `symbol` (spec 11's thin-coin mark)."""
    require(type(body) is list and len(body) == 1 and type(body[0]) is dict, "COLLECTOR_BOOK_INVALID")
    book = body[0]
    units = book.get("orderbook_units")
    require(book.get("market") == symbol and type(book.get("timestamp")) is int
            and type(units) is list and len(units) > 0 and type(units[0]) is dict, "COLLECTOR_BOOK_INVALID")
    require(number(book.get("level"), json_number=True) == 0, "COLLECTOR_BOOK_INVALID")
    return (number(units[0].get("bid_price"), positive=True, json_number=True),
            _EPOCH + timedelta(milliseconds=book["timestamp"]))
```

Replace (fd85850 line 410):

```python
    observed = instant(clock())
```

with:

```python
    # Spec 11: a last trade older than 30 seconds is marked at the best bid of a book at most 10 seconds old.
    books = {symbol: _best_bid(capture.get("/v1/orderbook", (("markets", symbol), ("level", "0"))), symbol)
             for symbol in markets if capture.receipts[-1].received_at - marks[symbol][1] > timedelta(seconds=30)}
    observed = instant(clock())
```

In the positions loop written in Task 6, replace:

```python
        if symbol not in current:
            price, at, unlisted = _ZERO, listing_at, True
        else:
```

with:

```python
        if symbol not in current:
            price, at, unlisted = _ZERO, listing_at, True
        elif symbol in books:
            (price, at), unlisted = books[symbol], None
            require(timedelta(0) <= observed-at <= timedelta(seconds=10), "COLLECTOR_BOOK_STALE_OR_FUTURE")
        else:
```

- [ ] **Step 4: Run the collector and interval tests**

```bash
focus launch accounts_collector/
focus launch launch_account_interval/
focus accounts accounts_continuous/
focus accounts accounts_guards/
```

Expected: every row `PASS`, exit 0 for each.

- [ ] **Step 5: Commit**

```bash
FILES="execution_accounts/upbit_collector.py tests/accounts_collector.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(accounts): mark a thin coin at a fresh best bid

When a listed coin's last trade is older than 30 seconds, the capture
reads that coin's level-0 book after the race re-reads and marks it at
the best bid if the book is at most 10 seconds old; otherwise it fails
closed. The book read counts toward the 30-second budget (spec section
11).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 8: E1 `market_flags`, zero value for unlisted coins

**Files:**
- Modify: `execution/snapshot.py:19` (import), `:89-101` (field, validation, hash), `:123-147` (`dump`, `load`)
- Modify: `execution/upbit_inquiry.py:10-11` (import), `:93-94` and `:103-107` (the ticker and the snapshot), new
  `_held_flags` after `snapshot()` (fd85850 `:109`; PR 2 moves every one of these lines down, so find them by text)
- Modify: `execution/positions.py:31-35`
- Modify: `tests/renewal_boundaries.py:25` (pin)
- Test: `tests/execution_fixtures.py:267-299`; `tests/execution_upbit.py:15`, `:67`, `:69`, `:122`, new test at the
  end; `tests/accounts_readiness.py:197-198`; `tests/execution_snapshot.py:88`, `:184`, new test at the end;
  `tests/execution_positions.py`, new test at the end

**Interfaces:**
- Consumes: PR 1 `UNIVERSE_MARKET`, `FLAG_CLASSES`, `market_flags`; PR 2 `MARKET_ALL_PATH`, `market_all()`.
- Produces: `Snapshot.market_flags: Mapping[str, str] | None = None`; `venue_value_krw` values an `absent` coin at 0;
  `_held_flags(holdings, answers) -> dict[str, str]`.

- [ ] **Step 1: Add the listing fixture route**

```bash
grep -n '"/v1/market/all"' tests/execution_fixtures.py
```

If PR 2 already routes `("GET", "/v1/market/all")`, keep that entry and make its default body list `KRW-BTC`,
`KRW-ETH`, `KRW-USDT` and `KRW-XRP` as the unflagged entries below (add the ones missing); where PR 2 named the key
other than `market_all`, use PR 2's key in every test of this task. If the grep prints nothing, in
`tests/execution_fixtures.py` replace lines 276-277:

```python
    "ticker": ("GET", "/v1/ticker"),
}
```

with:

```python
    "ticker": ("GET", "/v1/ticker"),
    "market_all": ("GET", "/v1/market/all"),                # held-coin flags (universe spec 15)
}
```

and replace line 298:

```python
    "ticker": [{"market": "KRW-BTC", "trade_price": 100000000.0}, {"market": "KRW-USDT", "trade_price": 1400.0}],
```

with:

```python
    "ticker": [{"market": "KRW-BTC", "trade_price": 100000000.0}, {"market": "KRW-USDT", "trade_price": 1400.0}],
    "market_all": [{"market": m, "korean_name": "fixture", "english_name": "fixture",
                    "market_event": {"warning": False, "caution": dict.fromkeys(
                        ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING",
                         "GLOBAL_PRICE_DIFFERENCES", "CONCENTRATION_OF_SMALL_ACCOUNTS"), False)}}
                   for m in ("KRW-BTC", "KRW-ETH", "KRW-USDT", "KRW-XRP")],   # unflagged
```

- [ ] **Step 2: Write the failing tests**

In `tests/execution_upbit.py`, replace line 15:

```python
from execution import upbit_inquiry
```

with:

```python
from execution import positions, upbit_inquiry
```

Replace line 67:

```python
    assert [_path(c) for c in calls] == [PATH[n] for n in SIGNED] + [PATH["ticker"]]   # contract C10's order
```

with:

```python
    assert [_path(c) for c in calls] == [PATH[n] for n in SIGNED] + [PATH["market_all"], PATH["ticker"]]
```

Replace line 69:

```python
    for call in calls[:-1]:
```

with:

```python
    for call in calls[:len(SIGNED)]:                             # market/all and the ticker are public
```

Replace line 122:

```python
    assert set(snap.response_sha256) == {PATH[n] for n in SIGNED + ("ticker",)}
```

with:

```python
    assert set(snap.response_sha256) == {PATH[n] for n in SIGNED + ("market_all", "ticker")}
    assert dict(snap.market_flags) == {"BTC": "unflagged"}
```

Append to the end of `tests/execution_upbit.py`:

```python
def test_held_coin_flags_come_from_one_listing_read_and_an_unlisted_coin_is_not_asked_or_priced():
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]].append({"currency": "XYZ", "balance": "5", "locked": "0",
        "avg_buy_price": "0", "avg_buy_price_modified": False, "unit_currency": "KRW"})
    snap, calls = _run(routes)
    assert snap.ok, snap.error
    assert _query(calls[-1]) == "markets=KRW-BTC,KRW-USDT"                 # XYZ is not listed: not asked
    assert dict(snap.market_flags) == {"BTC": "unflagged", "XYZ": "absent"}
    assert positions.venue_value_krw(snap) == 20000.0 + 0.0001 * 100000000.0  # XYZ is worth 0, not unpriced
    bad = {"error": {"name": "validation_error", "message": "fixture: bad"}}
    snap, calls = _run(EF.upbit_routes(market_all=(400, bad)))
    assert snap.ok and dict(snap.market_flags) == {"BTC": "unknown"}, snap.error   # never a failed snapshot
    assert PATH["market_all"] not in snap.response_sha256 and _path(calls[-1]) == PATH["ticker"]
    snap, calls = _run(EF.upbit_routes(accounts=[dict(EF.UPBIT_BODIES["accounts"][0])]))
    assert snap.ok and snap.market_flags is None and PATH["market_all"] not in {_path(c) for c in calls}
```

In `tests/accounts_readiness.py`, replace lines 197-198:

```python
        expected = ("/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/withdraws",
                    "/v1/withdraws/coin_addresses", "/v1/deposits", "/v1/api_keys", "/v1/ticker")
```

with:

```python
        expected = ("/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/withdraws",
                    "/v1/withdraws/coin_addresses", "/v1/deposits", "/v1/api_keys", "/v1/market/all", "/v1/ticker")
```

In `tests/execution_snapshot.py`, replace line 88:

```python
    "prices_krw": {"BTC": 100_000_001.0, "USDT": 1_400.0}, "response_sha256": {"/v1/accounts": "b" * 64},
```

with:

```python
    "prices_krw": {"BTC": 100_000_001.0, "USDT": 1_400.0}, "response_sha256": {"/v1/accounts": "b" * 64},
    "market_flags": {"BTC": "warning"},
```

Replace line 184:

```python
        assert line == (model.canonical_json(s) + "\n").encode("utf-8")
```

with:

```python
        body = model.jsonable(s)
        del body["market_flags"]                                             # left out while None
        assert line == (model.canonical_json(body) + "\n").encode("utf-8")
```

Append to the end of `tests/execution_snapshot.py`:

```python
def test_market_flags_are_left_out_while_none_and_round_trip_when_set():
    old = _t4_full()
    assert "market_flags" not in json.loads(S.dump(old))
    flagged = dataclasses.replace(old, market_flags={"BTC": "warning", "XYZ": "absent"})
    obj = json.loads(S.dump(flagged))
    assert obj["market_flags"] == {"BTC": "warning", "XYZ": "absent"} and S.load(obj) == flagged
    assert flagged.snapshot_sha256 != old.snapshot_sha256
    for bad in ({"BTC": "listed"}, {"BTC": None}, {1: "absent"}, ["BTC"]):
        try:
            dataclasses.replace(old, market_flags=bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    assert _t4_raises(lambda: S.load(dict(obj, market_flags=None))).startswith("snapshot row:")
```

Append to the end of `tests/execution_positions.py`:

```python
def test_an_absent_coin_is_worth_zero_and_every_other_class_keeps_the_price_rule():
    held = dict(_upbit().holdings, XYZ=S.Holding(units=5.0))
    assert _close(positions.venue_value_krw(_upbit(holdings=held, market_flags={"BTC": "unflagged",
                                                                                "XYZ": "absent"})), UPBIT_KRW)
    for cls in ("warning", "caution", "unknown", "unflagged"):
        assert positions.venue_value_krw(_upbit(holdings=held, market_flags={"BTC": "unflagged", "XYZ": cls})) is None
    assert positions.venue_value_krw(_upbit(holdings=held)) is None              # no listing read: unpriced
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
focus execution execution_upbit/
focus execution execution_snapshot/
focus execution execution_positions/test_an_absent_coin
focus accounts accounts_readiness/test_upbit_reader
```

Expected: exit 1 for each: the call-order and readiness tests miss `/v1/market/all`; in `execution_snapshot` the
field-case check fails on the new `_T4_ALT` key, the dump test raises `KeyError: 'market_flags'` and the new test
raises `TypeError: ... unexpected keyword argument 'market_flags'`; the positions test raises that same `TypeError`.

- [ ] **Step 4: Add the field, the listing read and the zero value**

In `execution/snapshot.py`, replace line 19:

```python
from core.compliance import model
```

with:

```python
from core.compliance import model
from core.compliance.rules import FLAG_CLASSES
```

Replace lines 89-101:

```python
    prices_krw: Mapping[str, float] = field(default_factory=dict)    # symbol or currency -> KRW price used
    response_sha256: Mapping[str, str] = field(default_factory=dict) # path -> sha256 of the body; the OKX algo
                                          # calls use f"{path}?ordType={t}"; never a KIS query (E37)
    snapshot_sha256: str = ""             # set by __post_init__

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", frozenset(self.flags))     # a list or set hashes as the frozenset would
        if self.venue not in VENUES:
            raise ValueError("snapshot: venue is not kis, upbit or okx")
        if not self.flags <= FLAGS:
            raise ValueError("snapshot: a flag outside FLAGS")
        body = {k: v for k, v in model.jsonable(self).items() if k != "snapshot_sha256"}
        object.__setattr__(self, "snapshot_sha256", model.sha256_hex(model.canonical_json(body)))
```

with:

```python
    prices_krw: Mapping[str, float] = field(default_factory=dict)    # symbol or currency -> KRW price used
    response_sha256: Mapping[str, str] = field(default_factory=dict) # path -> sha256 of the body; the OKX algo
                                          # calls use f"{path}?ordType={t}"; never a KIS query (E37)
    market_flags: Mapping[str, str] | None = None   # Upbit: held coin -> its FLAG_CLASSES class from one market/all
                                          # read (universe spec 15); None when nothing was read, left out of the hash
    snapshot_sha256: str = ""             # set by __post_init__

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", frozenset(self.flags))     # a list or set hashes as the frozenset would
        if self.venue not in VENUES:
            raise ValueError("snapshot: venue is not kis, upbit or okx")
        if not self.flags <= FLAGS:
            raise ValueError("snapshot: a flag outside FLAGS")
        if self.market_flags is not None and not (isinstance(self.market_flags, Mapping) and all(
                isinstance(coin, str) and value in FLAG_CLASSES for coin, value in self.market_flags.items())):
            raise ValueError("snapshot: a market flag outside FLAG_CLASSES")
        body = {k: v for k, v in model.jsonable(self).items()
                if k != "snapshot_sha256" and not (k == "market_flags" and v is None)}
        object.__setattr__(self, "snapshot_sha256", model.sha256_hex(model.canonical_json(body)))
```

Replace lines 123-125:

```python
def dump(snap: Snapshot) -> bytes:
    """One inquiry line: the canonical JSON of every field (keys sorted) plus a newline, UTF-8."""
    return (model.canonical_json(snap) + "\n").encode("utf-8")
```

with:

```python
def dump(snap: Snapshot) -> bytes:
    """One inquiry line: the canonical JSON of every field (keys sorted; market_flags left out while None, so rows
    from before it keep their bytes) plus a newline, UTF-8."""
    body = model.jsonable(snap)
    if snap.market_flags is None:
        del body["market_flags"]
    return (model.canonical_json(body) + "\n").encode("utf-8")
```

Replace line 132:

```python
    if not isinstance(obj, dict) or set(obj) != _FIELDS:
```

with:

```python
    if not isinstance(obj, dict) or set(obj) not in (_FIELDS, _FIELDS - {"market_flags"}):
```

Replace lines 146-147:

```python
            flags=obj["flags"], prices_krw=dict(obj["prices_krw"]),
            response_sha256=dict(obj["response_sha256"]))
```

with:

```python
            flags=obj["flags"], prices_krw=dict(obj["prices_krw"]),
            response_sha256=dict(obj["response_sha256"]),
            market_flags=dict(obj["market_flags"]) if "market_flags" in obj else None)
```

In `execution/upbit_inquiry.py`, replace lines 10-11:

```python
from core.compliance import model
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
```

with:

```python
from core.compliance import model
from core.compliance.rules import UNIVERSE_MARKET, market_flags
from execution.snapshot import Address, FieldError, Holding, Move, Order, Snapshot, failed
```

Replace lines 93-94:

```python
        path = _TICKER
        markets = sorted({f"KRW-{c}" for c in holdings} | {"KRW-USDT"})     # KRW-USDT values OKX too (E32)
```

with:

```python
        path = _TICKER
        flags = _held_flags(holdings, answers) if holdings else {}
        markets = sorted({f"KRW-{c}" for c in holdings if flags[c] != "absent"}   # unlisted: not asked (spec 11)
                         | {"KRW-USDT"})                                         # KRW-USDT values OKX too (E32)
```

Replace lines 103-107:

```python
        return Snapshot(venue="upbit", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, open_orders=orders, fills=tuple(fills), deposits=deposits,
                        withdrawals=withdrawals, withdrawal_addresses=addresses,
                        key_expiry=model.iso_utc(min(expiries)) if expiries else None, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()})
```

with:

```python
        return Snapshot(venue="upbit", utc=utc, server_utc=server_utc, clock_offset_s=offset, ok=True,
                        holdings=holdings, cash=cash, open_orders=orders, fills=tuple(fills), deposits=deposits,
                        withdrawals=withdrawals, withdrawal_addresses=addresses,
                        key_expiry=model.iso_utc(min(expiries)) if expiries else None, prices_krw=prices,
                        response_sha256={p: a.sha256 for p, a in answers.items()}, market_flags=flags or None)
```

Insert after the end of `snapshot()` (the line `        return _failed(utc, path, exc, answers)`), with two
blank lines on each side:

```python
def _held_flags(holdings: dict, answers: dict) -> dict[str, str]:
    """Each held coin's flag class from one market/all read, outside the snapshot's fail-whole path (universe spec
    15): a failed or malformed read makes every held coin "unknown" (an amber alert), never a failed snapshot. A coin
    missing from a good read is "absent"; one whose market id the universe pattern cannot hold stays "unknown"."""
    try:
        answer = market_all()
        classes = market_flags(answer.raw_body)
    except _CONTAINED:
        return dict.fromkeys(holdings, "unknown")
    answers[MARKET_ALL_PATH] = answer
    return {coin: classes.get(f"KRW-{coin}", "absent" if UNIVERSE_MARKET.fullmatch(f"KRW-{coin}") else "unknown")
            for coin in holdings}
```

In `execution/positions.py`, replace lines 31-35:

```python
    for symbol, holding in snap.holdings.items():
        price = snap.prices_krw.get(symbol)
        if price is None or not price > 0 or holding.units < 0:
            return None
        total += holding.units * price
```

with:

```python
    absent = {coin for coin, cls in (snap.market_flags or {}).items() if cls == "absent"}
    for symbol, holding in snap.holdings.items():
        if symbol in absent and holding.units >= 0:
            continue                                # universe spec 11: an unlisted coin is worth 0, not unpriced
        price = snap.prices_krw.get(symbol)
        if price is None or not price > 0 or holding.units < 0:
            return None
        total += holding.units * price
```

- [ ] **Step 5: Run the E1 and readiness tests**

```bash
focus execution execution_upbit/
focus execution execution_snapshot/
focus execution execution_positions/
focus execution execution_poll/
focus execution execution_transport/
focus execution execution_guards/
focus accounts accounts_readiness/
```

Expected: every row `PASS`, exit 0 for each.

- [ ] **Step 6: Review the renewal surface change and update its pin**

```bash
focus control control_guards/test_renewal_validation
```

Expected before the update: exit 1, `AssertionError: ['execution/upbit_inquiry.py: initialization surface
changed']`. Review: `git diff -- execution/upbit_inquiry.py` must show, outside function bodies, exactly the new
import line `from core.compliance.rules import UNIVERSE_MARKET, market_flags` and the new
`_held_flags(holdings: dict, answers: dict) -> dict[str, str]` signature. This file's pin already carries PR 2's
change, so no value is stated here; once the diff is reviewed, print it:

```bash
"$PY" -B -X utf8 -c "from pathlib import Path; from tests.renewal_boundaries import _surface; print(_surface(Path('execution/upbit_inquiry.py').read_text(encoding='utf-8')))"
```

In `tests/renewal_boundaries.py`, replace the value on the `"execution/upbit_inquiry.py":` line (line 25) with the
printed value, then:

```bash
focus control control_guards/test_renewal_
```

Expected: all three `control_guards/test_renewal_...` rows `PASS`, exit 0.

- [ ] **Step 7: Commit**

```bash
FILES="execution/snapshot.py execution/upbit_inquiry.py execution/positions.py tests/renewal_boundaries.py tests/execution_fixtures.py tests/execution_upbit.py tests/accounts_readiness.py tests/execution_snapshot.py tests/execution_positions.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(e1): held-coin flags and a zero value for unlisted coins

When a coin is held, the Upbit snapshot reads market/all outside its
fail-whole path and records each held coin's flag class in
Snapshot.market_flags (left out of the hash and the row while None). An
unlisted coin is not asked of the ticker and is valued at 0; a failed read
marks every held coin unknown and never voids E1 positions (spec sections
11 and 15). The renewal surface pin is updated after review.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 9: E1 alerts for held coins and the 09:45 snapshot

**Files:**
- Modify: `execution/checks.py:14` (import), `:20-22` (`KINDS`), `:26` (deadline), `:84-85` (`TEXT`), `:199-200`
  (`evaluated`), new `universe_check` after `:214`, `:349-351` (`_venue_alerts`)
- Modify: `execution/poll.py:135-136`
- Test: `tests/execution_checks.py:137-138`, `:153-154`, `:776`, `:789`, new tests at the end;
  `tests/execution_poll.py`, new test at the end

**Interfaces:**
- Consumes: Task 8; PR 1 `Venue.universe_rule`; PR 3 `Context.universe`.
- Produces: kinds `MARKET_FLAGS`, `UNIVERSE`; text keys `HELD_UNLISTED`, `HELD_WARNING`, `HELD_FLAGS_UNKNOWN`,
  `UNIVERSE_NO_SNAPSHOT`; `UNIVERSE_DEADLINE`; `universe_check(ctx, now)`.

- [ ] **Step 1: Write the failing tests**

In `tests/execution_checks.py`, replace lines 137-138:

```python
    assert len(checks.KINDS) == 13 and len(set(checks.KINDS)) == 13
    assert len(checks.TEXT) == 24
```

with:

```python
    assert len(checks.KINDS) == 15 and len(set(checks.KINDS)) == 15
    assert len(checks.TEXT) == 28
```

Replace lines 153-154:

```python
    assert model.sha256_hex(model.canonical_json(dict(checks.TEXT))) == (
        "1055607ceb02cde19b81297fba5476709e1760278ef626a4b93900828e1fa258")
```

with:

```python
    assert model.sha256_hex(model.canonical_json(dict(checks.TEXT))) == (
        "adecfb4b24390f8ab53e60ab1360bd67f4cc5ee9a58b92ee01333d14cc0c98d4")
```

Replace line 776 (`return alerts`, the end of `_zoo`):

```python
    return alerts
```

with:

```python
    flags = {"BTC": "absent", "ETH": "warning", "XRP": "unknown"}
    held = _snap("upbit", cash={"KRW": 20_000.0}, holdings={c: snapshot.Holding(units=1.0) for c in flags},
                 market_flags=flags)
    alerts += checks.run_checks(_prev(), {"upbit": held}, owner, checks.limits_from(owner, None), NOW)
    return alerts
```

Replace line 789:

```python
    poller_own = {"OUTAGE_CRASH", "CRASH_UNLOGGED", "EVIDENCE_BROKEN", "NOT_SET"}
```

with:

```python
    poller_own = {"OUTAGE_CRASH", "CRASH_UNLOGGED", "EVIDENCE_BROKEN", "NOT_SET", "UNIVERSE_NO_SNAPSHOT"}
```

Append to the end of `tests/execution_checks.py`:

```python
def test_held_coin_flags_raise_counts_and_clear_only_after_a_full_listing_read():
    flags = {"BTC": "absent", "ETH": "warning", "XRP": "warning", "DOGE": "unknown", "SOL": "unflagged"}
    holdings = {c: snapshot.Holding(units=1.0) for c in flags}
    found = _run(_new(upbit=_snap("upbit", cash={"KRW": 20_000.0}, holdings=holdings, market_flags=flags)))
    assert found[("upbit", "HELD_UNLISTED")] == {"n": 1} and found[("upbit", "HELD_WARNING")] == {"n": 2}
    assert found[("upbit", "HELD_FLAGS_UNKNOWN")] == {"n": 1}
    owner = _owner()

    def done(snap):
        limits = checks.limits_from(owner, None)
        return ("upbit", "MARKET_FLAGS") in checks.evaluated(_prev(), _new(upbit=snap), owner, limits, NOW)
    assert not done(_snap("upbit", cash={"KRW": 20_000.0}, holdings=holdings, market_flags=flags))
    assert done(_snap("upbit", cash={"KRW": 20_000.0}, holdings=holdings, market_flags=dict(flags, DOGE="unflagged")))
    assert done(_snap("upbit", cash={"KRW": 20_000.0}))                     # nothing held, nothing to check
    assert not done(_failed("upbit"))


def test_universe_no_snapshot_is_amber_from_0945_kst_and_only_with_an_approved_rule():
    from types import SimpleNamespace

    def ctx(rule="signed-rule", universe=None, valid=True):
        venues = SimpleNamespace(venues={"upbit": SimpleNamespace(universe_rule=rule)})
        return SimpleNamespace(active=SimpleNamespace(valid=valid, venues=venues if valid else None),
                               universe=universe)
    before = datetime(2026, 10, 24, 0, 44, 59, tzinfo=timezone.utc)          # 09:44:59 KST
    after = datetime(2026, 10, 24, 0, 45, tzinfo=timezone.utc)               # 09:45:00 KST
    alerts, done = checks.universe_check(ctx(), after)
    assert [(a.venue, a.kind, a.level, a.text_key) for a in alerts] == [("upbit", "UNIVERSE", "amber",
                                                                         "UNIVERSE_NO_SNAPSHOT")]
    assert done == frozenset({("upbit", "UNIVERSE")})
    assert checks.universe_check(ctx(universe="in force"), after) == ([], frozenset({("upbit", "UNIVERSE")}))
    for c, now in ((ctx(), before), (ctx(rule=None), after), (ctx(valid=False), after)):
        assert checks.universe_check(c, now) == ([], frozenset())
```

Append to the end of `tests/execution_poll.py`:

```python
def test_every_poll_raises_and_clears_what_the_universe_check_returns():
    """Universe spec 15: poll_once records the universe check's alert and passes its evaluated pair to due()."""
    alert = checks.Alert(venue="upbit", kind="UNIVERSE", level="amber", text_key="UNIVERSE_NO_SNAPSHOT")
    seen, real = [], vars(checks)["universe_check"]

    def fake(ctx, now):
        seen.append(now)
        return [alert], frozenset({("upbit", "UNIVERSE")})
    checks.universe_check = fake
    try:
        with _signed(limits=LIMITS, cap=0.10), EF.fake_keys(), EF.serve(_routes()):
            poll.poll_once(NOW)
            rows = _rows()
    finally:
        checks.universe_check = real
    assert seen == [NOW] and checks.row(alert, UTC) in rows, rows
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
focus execution execution_checks/
focus execution execution_poll/test_every_poll_raises
```

Expected: exit 1 for each: the catalogue counts and pin fail; the held-coin test fails with
`KeyError: ('upbit', 'HELD_UNLISTED')` and the universe test with `AttributeError: module 'execution.checks' has no
attribute 'universe_check'`; the poll test fails at `vars(checks)["universe_check"]` with
`KeyError: 'universe_check'`. `test_no_balance_or_address_in_any_sentence` still `PASS`es here (the extra zoo poll
raises nothing until the texts exist, and the new `poller_own` name is not yet in `TEXT`); it covers the new
sentences after Step 3.

- [ ] **Step 3: Add the kinds, texts, checks and the poll wiring**

In `execution/checks.py`, replace line 14:

```python
from datetime import date, datetime, timedelta
```

with:

```python
from datetime import date, datetime, time, timedelta
```

Replace lines 20-22:

```python
KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "HOLDINGS_CHANGED", "OKX_CAP", "ADDRESS_LIST", "D15_LIVE",
         "HARD_BLOCK_LIVE", "FLOOR", "DAILY_LOSS", "OUTAGE", "CLOCK_SKEW",     # spec 7's eleven checks
         "EVIDENCE", "NOT_SET")                                              # the poller's own (E33, E43)
```

with:

```python
KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "HOLDINGS_CHANGED", "OKX_CAP", "ADDRESS_LIST", "D15_LIVE",
         "HARD_BLOCK_LIVE", "FLOOR", "DAILY_LOSS", "OUTAGE", "CLOCK_SKEW",     # spec 7's eleven checks
         "EVIDENCE", "NOT_SET",                                              # the poller's own (E33, E43)
         "MARKET_FLAGS", "UNIVERSE")                                         # universe spec 15
```

Replace line 26:

```python
CLOCK_SKEW_S = 60
```

with:

```python
CLOCK_SKEW_S = 60
UNIVERSE_DEADLINE = time(9, 45)        # universe spec 15: a snapshot must be in force by 09:45 KST
```

Replace lines 84-85 (the last entry of `TEXT` and its closing line):

```python
    "NOT_SET": ("NOT_SET", "info", "Checks skipped (not set): {skipped}."),
})
```

with:

```python
    "NOT_SET": ("NOT_SET", "info", "Checks skipped (not set): {skipped}."),
    "HELD_UNLISTED": ("MARKET_FLAGS", "red", "{n} coin(s) held at {venue} are no longer listed in its KRW market, so E1 "
                      "values them at 0. Check the {venue} app now."),
    "HELD_WARNING": ("MARKET_FLAGS", "red", "{n} coin(s) held at {venue} carry its investment warning. Check the "
                     "{venue} app now."),
    "HELD_FLAGS_UNKNOWN": ("MARKET_FLAGS", "amber", "E1 could not read {venue}'s market list for {n} held coin(s) this "
                           "poll, so their listing and warning checks were skipped."),
    "UNIVERSE_NO_SNAPSHOT": ("UNIVERSE", "amber", "No universe snapshot is in force at 09:45 KST today. Universe buys "
                             "stay blocked until the snapshot task writes one."),
})
```

Replace lines 199-200:

```python
        if snap.ok:
            done.update((venue, kind) for kind in _OK_KINDS)
```

with:

```python
        if snap.ok:
            done.update((venue, kind) for kind in _OK_KINDS)
            if venue == "upbit" and "unknown" not in (snap.market_flags or {}).values():
                done.add((venue, "MARKET_FLAGS"))          # every held coin has a class from a good read
```

Insert after the end of `evaluated` (line 214, `return frozenset(done)`), with two blank lines on each side:

```python
def universe_check(ctx: model.Context, now: datetime) -> tuple[list[Alert], frozenset[tuple[str, str]]]:
    """UNIVERSE_NO_SNAPSHOT (universe spec 15) and whether it was evaluated: only from 09:45 KST and only while the
    approved venues carry an Upbit universe rule; amber when no snapshot is in force (ctx.universe is None)."""
    venues = ctx.active.venues if ctx.active.valid else None
    upbit = venues.venues.get("upbit") if venues is not None else None
    if upbit is None or upbit.universe_rule is None or now.astimezone(model.KST).time() < UNIVERSE_DEADLINE:
        return [], frozenset()
    alerts = [] if ctx.universe is not None else [_alert("upbit", "UNIVERSE_NO_SNAPSHOT")]
    return alerts, frozenset({("upbit", "UNIVERSE")})
```

Replace lines 349-351 (the end of `_venue_alerts`):

```python
    if snap.clock_offset_s is not None and abs(snap.clock_offset_s) > CLOCK_SKEW_S:
        out.append(_alert(venue, "CLOCK_SKEW", seconds=round(abs(snap.clock_offset_s))))
    return out
```

with:

```python
    if snap.clock_offset_s is not None and abs(snap.clock_offset_s) > CLOCK_SKEW_S:
        out.append(_alert(venue, "CLOCK_SKEW", seconds=round(abs(snap.clock_offset_s))))
    if venue == "upbit" and snap.ok and snap.market_flags:          # universe spec 15, counts only
        classes = list(snap.market_flags.values())
        for text_key, cls in (("HELD_UNLISTED", "absent"), ("HELD_WARNING", "warning"),
                              ("HELD_FLAGS_UNKNOWN", "unknown")):
            if cls in classes:
                out.append(_alert(venue, text_key, n=classes.count(cls)))
    return out
```

In `execution/poll.py`, replace lines 135-136:

```python
    raw = checks.run_checks(prev, new, ctx.owner, limits, now) + own
    done |= checks.evaluated(prev, new, ctx.owner, limits, now)
```

with:

```python
    universe_raw, universe_done = checks.universe_check(ctx, now)       # universe spec 15
    raw = checks.run_checks(prev, new, ctx.owner, limits, now) + own + universe_raw
    done |= checks.evaluated(prev, new, ctx.owner, limits, now) | universe_done
```

- [ ] **Step 4: Run the E1 tests**

```bash
focus execution execution_checks/
focus execution execution_poll/
focus execution execution_guards/
```

Expected: every row `PASS`, exit 0 for each. The fixture homes carry no `universe_rule`, so every existing poll
test sees no new row.

- [ ] **Step 5: Commit**

```bash
FILES="execution/checks.py execution/poll.py tests/execution_checks.py tests/execution_poll.py"
git diff --stat -- $FILES
git diff --stat --ignore-cr-at-eol -- $FILES
git add $FILES
git commit -m "$(cat <<'EOF'
feat(e1): alerts for unlisted and warning coins and a missing snapshot

New catalogue entries (universe spec 15): red HELD_UNLISTED and
HELD_WARNING, amber HELD_FLAGS_UNKNOWN for a failed listing read, and
amber UNIVERSE_NO_SNAPSHOT from 09:45 KST while an approved Upbit
universe rule has no snapshot in force. The held-coin checks clear only
after a full listing read. The catalogue pin is updated.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Expected: the two `--stat` outputs are identical before `git add`.

### Task 10: Guards, full suite and pull request

**Files:**
- No code change. Read-only checks, then push and open the PR.

**Interfaces:**
- Consumes: Tasks 1 to 9.
- Produces: one PR against `main` that the owner reviews and merges.

- [ ] **Step 1: Run the guard modules**

```bash
focus compliance compliance_guards/
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
```

Expected: every row `PASS`, exit 0 for each. `control_guards/test_renewal_*` runs `tests/renewal_boundaries.py` with
the pins of Tasks 1, 2, 4, 6 and 8.

- [ ] **Step 2: Run the full suite**

```bash
"$PY" -X utf8 -m tests.run_all
```

Expected: the last line reads `N/N passed, 0 failed, K not run; ...` with 0 failed (NOT_RUN rows are allowed and
listed with their reason), exit 0.

- [ ] **Step 3: Check line endings and the branch diff**

```bash
git diff --stat origin/main...HEAD
git diff --stat --ignore-cr-at-eol origin/main...HEAD
git status --short
```

Expected: the two `--stat` outputs are identical; `git status --short` is empty (the full suite's result file is
ignored by git or outside the tracked tree; if it shows up, leave it uncommitted).

- [ ] **Step 4: Push and open the PR (the owner merges; never merge with tools)**

```bash
git push -u origin claude/universe-pr4c-terms-orders-accounts
gh pr create --base main --head claude/universe-pr4c-terms-orders-accounts \
  --title "Upbit KRW universe PR 4c: terms authority v2, IOC orders, unlisted and thin coins, E1 alerts" \
  --body "$(cat <<'EOF'
## Summary

- Terms authority v2 (spec section 10): `UniverseTermsAuthority` binds the rule sha256 instead of a symbol;
  `authority_digest` gets a v2 form and the v1 digest is pinned byte for byte. `E1UpbitTermsSource.read(symbol)`
  takes the coin at read time for v2. Every observation records `observed_maximum_krw`; a v2 parse never fails on
  it and `within_buy_cap` tells the allow-list whether the coin reaches the cap. `TERMS_MARKET_INACTIVE` and
  `TERMS_MARKET_MISMATCHED` replace the combined code.
- `validate_observed_order` checks every order, sells included, against the observed maximum and v2 buys also
  against the cap (`RENEWAL_BUY_ABOVE_UNIVERSE_CAP`).
- `renew_profile(..., allow_symbol_change=False)`: only a universe profile may move to another coin; the contract
  digest and head key stay, every refusing check runs before the head moves, and a fixed profile refuses the flag.
- IOC (spec section 11): Upbit orders take `gtc` or `ioc`; a universe profile requires `ioc`; the IOC create body
  adds `time_in_force=ioc` and the gtc body is byte for byte unchanged; an IOC create response without it is
  `unknown(identity_mismatch)`.
- Rehearsal audit: optional `universe_terms_authority` (never with `terms_authority`); the profile picks v1 or v2.
- Account capture: `market/all` before the ticker when a coin is held; an unlisted held coin is recorded at price 0
  with `unlisted=True`, which the provider requires for price 0; a coin whose last trade is older than 30 seconds
  is marked at the best bid of a book at most 10 seconds old, otherwise the capture fails closed.
- E1 (spec sections 11 and 15): the held coins' `market/all` read sits outside the snapshot's fail-whole path;
  `Snapshot.market_flags` (left out of the hash and row while `None`); an unlisted coin is not asked of the ticker
  and is valued at 0; alerts `HELD_UNLISTED` (red), `HELD_WARNING` (red), `HELD_FLAGS_UNKNOWN` (amber) and
  `UNIVERSE_NO_SNAPSHOT` (amber, from 09:45 KST with an approved rule).

## Tests added

- `tests/launch_instrument_refresh.py`: v1 digest pin; v2 read at read time and v1 symbol refusal; v2 chance query
  binding; market code split; observed maximum and buy cap; held-coin sell above the cap passes; renewal A to B and
  back with the flag (contract kept, `validate_renewal`, preflight complete); refusal without the flag; a fixed
  profile refuses the flag; a coin below the cap is not buyable but still renews and sells.
- `tests/control_model.py`, `tests/orders_codecs.py`, `tests/launch_profile.py`: IOC acceptance per venue, the IOC
  and unchanged gtc bodies, `validate_request` refusing a stripped IOC body, the response identity rule, IOC cancel
  with a partial fill and its status read; universe profiles require `ioc`.
- `tests/launch_owner_rehearsal.py`: v1 or v2 audit authority, both refused, and the profile's choice.
- `tests/accounts_collector.py`, `tests/accounts_provider.py`, `tests/accounts_guards.py`,
  `tests/launch_account_interval.py`, `tests/launch_runner.py`: listing read order, unlisted coin at price 0 with
  its read time, a failed listing read fails closed, the E1 binding's two new fixed GETs, the thin-coin best bid and
  stale or invalid books, the provider's marker rule and canonical omission, unlisted dust next to the held coin
  with exit, cancel and a later stopped exit working.
- `tests/execution_upbit.py`, `tests/execution_snapshot.py`, `tests/execution_positions.py`,
  `tests/accounts_readiness.py`, `tests/execution_checks.py`, `tests/execution_poll.py`: call order, flags,
  failed listing read, zero value, `market_flags` encoding, the new catalogue (pinned) and its counts, the 09:45
  check and its poll wiring.
- `tests/renewal_boundaries.py`: the surfaces of `instrument_terms.py`, `instrument_refresh.py`,
  `execution_accounts/model.py` and `upbit_inquiry.py` and two call sets are updated by hand after review.

## Not verified here

- No live Upbit read: the IOC `time_in_force` response field, the `market/all` detail shape and the level-0 book
  fields are from Upbit's documentation and fixtures only.
- The coordinator does not yet call `read(symbol)`, `allow_symbol_change` or `within_buy_cap`, and the driver still
  expects `gtc` (PR 4d and PR 4e). The rehearsal builds a v2 terms source, whose `read()` without a symbol refuses
  until PR 4e passes the trade coin.
- The account audit with a v2 authority changes its bytes, so the owner re-signs the strategy review when adding it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: `gh` prints the PR URL. Stop here; the owner reviews and merges.

## Summary

Ten tasks: the v2 terms authority and read-time symbol (1), the observed maximum and buy cap (2), IOC (3), renewal to
another coin (4), the rehearsal audit (5), unlisted coins in the capture and provider (6), the thin-coin book (7),
E1 `market_flags` and the zero value (8), the E1 alerts (9), and the guards, suite and PR (10).

## Not planned here

- `execution_launch/driver.py:162-163` (expect `ioc` for a universe protocol): the fixed driver also pins the
  protocol symbol, so the universe driver of PR 4d owns this line.
- The coordinator's `read(symbol)` at `coordinator.py:444`, `allow_symbol_change` after its flat check, the
  allow-list from `within_buy_cap`, `_TermsSource.read(symbol)` in the rehearsal, and the coordinator toasts: PR 4e.
- The E1 contract document's catalogue text (contract 15.3) is not edited; `tests/execution_checks.py` pins the
  catalogue itself.
