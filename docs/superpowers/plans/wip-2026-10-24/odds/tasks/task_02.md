### Task 2: The venues parser learns the odds keys (`core/compliance/rules.py`)

**Files:**
- Modify: `core/compliance/rules.py` (anchors: the constant `_VENUE_OPTIONAL` with `_VENUE_REQUIRED` above it; the
  class `Venue`, its `deposits` field and its `quote_for` method; the parser `_venue(vid, entry, instruments)`, its def
  line and its `return Venue(...)` statement; LF, kept; a D14 closure file)
- Modify: `tests/compliance_tables.py` (anchors: `test_venue_shape_rules`, its `minimum_krw` line; the end of
  `test_deposit_entries` and the "Hashes and the approved state" banner below it; LF, kept)
- Test: `tests/compliance_tables.py`

**Interfaces:**
- Consumes (all unchanged, as of `5816d3c`):
  - `core.compliance.rules`: `Invalid(reason)` (`.reason == str(exc)`); `_keys(doc, where, required, optional)`
    (refuses a non-mapping with `"{where}: expected a mapping"`, then `"{where}: unknown key(s) [...]"`, then
    `"{where}: missing key(s) [...]"`); `_text(value, where)` (`"{where}: expected a non-empty string"`);
    `_member(value, where, vocab)` (`"{where}: {value!r} is not one of {sorted(vocab)}"`); `parse_date(value, what)`
    (`"{what}: expected a quoted YYYY-MM-DD date, got {value!r}"`, `"{what}: {value!r} is not a calendar date"`);
    `InstrumentMap.entries` (`(section, symbol) -> Instrument`), `Instrument.cost_book`; inside `_venue`, its locals
    `where` (`"venues: <id>"`), `sections`, `listed` (`{symbol: section}` over the venue's sections) and `settlement`.
  - `tests/compliance_tables.py`: `_dump(doc)`, `_refused(call, *has) -> str`, `_row()`, `_table(*rows)`,
    `_map_doc()` (krx 005930 `KRX_stock_book` and 252670 `KRX_ETF_line`; us TQQQ, SH, AAPL, IBIT, GDLC, BITO
    `US_shares_KIS`; crypto BTC, USDT, XRP `crypto_venue`), `_venues_doc()` (kis, upbit, okx), `_facts(vdoc, mdoc)`,
    `_need_model()`, and inside `test_venue_shape_rules` its `bad(mutate, *has)` and `v = "venues"`.
- Produces (Task 3, Task 5's `ODDS_VENUES`, Task 6's `costs.terms` and every later task rely on these exact names):
  - `rules._VENUE_OPTIONAL` gains `"lot"`, `"min_order"`, `"fee_extras"`, `"tick_ladder"`; the top-level keys stay
    `{schema, venues}`.
  - `rules._LADDER_BOOKS = frozenset({"KRX_stock_book", "US_shares_KIS", "crypto_venue"})`.
  - `rules.Venue` gains, after `deposits`, the hashable defaulted fields
    `lot: tuple[tuple[str, float], ...] = ()` (sorted `(symbol or "default", step > 0)`),
    `min_order: tuple[tuple[str, float], ...] = ()` (sorted `(settlement asset, minimum >= 0 in quote units)`),
    `fee_extras: tuple[float, float] | None = None` (`(phi_buy, phi_sell)` in KRW, each >= 0; None = absent),
    `tick_ladder: tuple[tuple[str, str, tuple[tuple[float, float], ...]], ...] = ()` (sorted `(cost book,
    effective_from "YYYY-MM-DD", ((price_from, tick), ...))`, prices in the book's quote currency) and
    `odds_sources: tuple[tuple[str, str], ...] = ()` (sorted `(odds key, its source)` for each odds key present);
    and the pure lookups `Venue.lot_for(symbol: str) -> float | None` (the symbol's step, else the `"default"` step,
    else None), `Venue.min_order_for(quote: str) -> float | None` and
    `Venue.ladder_for(book: str) -> tuple[str, tuple[tuple[float, float], ...]] | None`. Every number stored is a
    Python `float`.
  - Private parser helpers, each raising `Invalid` with a reason that starts `venues: <id>: <key>`:
    `_odds_number(value, where: str, *, positive: bool) -> float`, `_odds_lot(value, where, listed, sections)`,
    `_odds_min_order(value, where, settlement)`, `_check_extras(value, where) -> tuple[float, float]` (the spec's
    check_extras) and `_odds_ladder(value, where, sections, instruments)`.
  - Exact refusal texts, pinned by Step 1's tests: `{where}: expected a finite number > 0, got {value!r}` and
    `... >= 0, got {value!r}` (`_odds_number`); `venues: <id>: lot: units: expected a non-empty mapping of symbol
    (or default) to a step`; `venues: <id>: lot: units: {key!r} is not a symbol of sections [...]`;
    `venues: <id>: min_order: quote: expected a non-empty mapping of settlement asset to a minimum`;
    `venues: <id>: min_order: quote: {key!r} is not one of the settlement assets [...]`;
    `venues: <id>: tick_ladder: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]`;
    `venues: <id>: tick_ladder: books: KRX_ETF_line: its ladder is core/quant/instruments.py's`;
    `venues: <id>: tick_ladder: books: <book> is the cost book of no symbol in sections [...]`;
    `venues: <id>: tick_ladder: books: <book>: expected a non-empty list of [price_from, tick] rows`;
    `... <book>: {row!r} is not a [price_from, tick] row`; `... <book>: the first price_from must be 0, got {x!r}`;
    `... <book>: price_from {x!r} is not above the row before`.
  - In `tests/compliance_tables.py`: the constants `_ODDS_SOURCE`, `_KRX_LADDER` and `_RULES_IMPORTS`, the helper
    `_odds_venues_doc()`, and the tests `test_venue_odds_keys_parse_to_exact_tuples`,
    `test_venue_odds_lookups_fall_back_and_answer_none`, `test_venue_odds_lookups_are_pure_tuple_lookups` and
    `test_check_extras_lives_in_the_parser` (Task 3 reuses `_KRX_LADDER`).

**Plan decisions used:** Q3 (compliance-side prerequisites first, O3), Q17 (the four keys, their shapes and rules),
Q11 (O11: a missing minimum, lot or fixed charge makes a leg not tradable, an explicit signed 0 is allowed; this task
only stores absence as `()` / None, Task 6 turns it into NOT_TRADABLE); R2-13 (the DRIFT RULE).

What this task does and why:
- Spec 7.2 "Costs, minimums": minimums and ticks come from `venues.yaml`, and a missing entry gives NOT_TRADABLE.
  Spec 4 "Costs": extras in `venues.yaml` may only raise costs (`check_extras`). Today `_VENUE_OPTIONAL`
  (rules.py:637 at `5816d3c`) knows only `markets`, `quote_by_currency`, `default_quote` and `deposits`, so any odds
  key is `unknown key(s)` and the shipped file cannot carry one (`tests/compliance_tables.py:633` pins
  `minimum_krw` as unknown).
- After this task each of the four keys is an optional mapping with exactly its own keys and a mandatory non-empty
  `source`: `lot: {source, units: {<symbol> | default: step}}`, `min_order: {source, quote: {<settlement asset>:
  amount}}`, `fee_extras: {source, phi_buy, phi_sell}`, `tick_ladder: {source, effective_from: "YYYY-MM-DD", books:
  {<cost book>: [[price_from, tick], ...]}}`. Numbers are finite ints or floats, never bools; a lot step and a tick
  are > 0; a minimum, an extra and a price_from are >= 0 (an explicit 0 is a signed value, O11); a ladder starts at
  price_from exactly 0 and strictly increases; a ladder book is in `_LADDER_BOOKS` and is the cost book of at least
  one instrument in the venue's sections. `KRX_ETF_line` is refused by name: its ladder is the one copied from
  `core/quant/instruments.py` (Task 6), and a second, signed one could disagree with it. A key written as `null` is
  refused (`expected a mapping`); absence is the only way to leave a value out. `check_extras` lives in the parser,
  so a negative extra makes the venue file, and with it the whole approved state, INVALID.
- The lookups are plain tuple reads: no `parse_date` call and no file, clock or zone name. The gate's purity tests
  scan every `Venue` method (`tests/compliance_gate.py::test_gate_call_graph_has_no_clock_zone_file_or_socket` walks
  the rules classes the gate reaches for the `_T9_FORBIDDEN` names, and follows any module-level def a method names),
  and `test_purity_no_file_clock_zone_or_network` traps `rules.date`, `rules.Path` and `rules.os` during screen and
  decide. That is why `effective_from` is stored as its checked ISO text, not as a `date`, and why the lookups use
  local names that are no module-level def of rules.py (`check` or `main` would pull the clock into the scan).
  `rules.py` gains no import (`test_venue_odds_lookups_are_pure_tuple_lookups` pins the import set).
- Side effects, all intended and checked by tests that stay green unchanged: `model.seal_context` hashes the new
  fields into `ctx_hash` (all of them are `model.jsonable`: tuples, floats, None); `rules._changed` (the `--check`
  draft diff) names a changed odds field like any other field (`venue kis: lot, odds_sources changed`);
  `test_valid_fixture_venues_parse`'s `rules.Venue(...)` equality holds because every new field has a default; the
  shipped `core/odds/venues.yaml` is not touched here (Task 3), so every byte pin of `tests/compliance_gate.py`
  (:336-340, :695-697, :998-1000) and `test_shipped_venue_facts_p22` stay green; a route name of the follow-up's
  closure scan (`setattr`, `vars`, `globals`, `modules`, `__dict__`, ...) appears nowhere in the new text, so
  rules.py keeps its `TYPE_CHECKING` and `__main__` skips.
- Code hash: `rules.py` is a D14 closure file, so the code hash moves. No `code_approved` exists yet (owner act 2 is
  not done), so nothing is re-signed now; once the owner signs, any later closure change needs a fresh signature.
- Drift (R2-13): the follow-up changes both files of this task. In `rules.py` it inserts six constants above `_match`
  and edits four blocks of `_row` (so `_VENUE_OPTIONAL` moves down about 31 lines); in `tests/compliance_tables.py` it
  adds tests after :300 and above `test_shipped_okx_warning_has_only_the_cap_slot` and rewrites assertions in
  `test_d16_rows_need_requires_live`, `test_warning_slots` and `test_max_leverage` (so the `minimum_krw` line moves
  down several dozen lines). None of its edits touches an anchor of this task, so each old text below should match
  the merged file exactly. Re-read each file before each Edit; if an old text differs only because an earlier plan
  changed it, apply the same change to the current text, keep the earlier behaviour and add one line under "Drift
  rulings" in `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; if the change no longer makes sense,
  stop and rule.

- [ ] **Step 1: Write the failing tests**

  Two Edit-tool replacements in `tests/compliance_tables.py` (LF, kept). Re-read the file first (DRIFT RULE).

  **Edit T1**, `tests/compliance_tables.py`. Anchor: `test_venue_shape_rules`, its `minimum_krw` line (:633 at
  `5816d3c`) and the `okx="not a mapping"` line after it. The `minimum_krw` line stays: an unknown key is still
  refused. It is joined by near misses of the four exact key names (`odds_sources` is a `Venue` field, never a YAML
  key) and by one refusal line per rule of Q17, each on a doc that is valid except for the one value under test.
  Old text (exact):

```python
    bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")
    bad(lambda d: d[v].update(okx="not a mapping"), "venues: okx: expected a mapping")
```

  New text:

```python
    bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")
    # The odds keys (odds plan Task 2, Q17): only the exact names, then one refusal per rule.
    lot, low = {"source": "s", "units": {"BTC": 1e-8}}, {"source": "s", "quote": {"KRW": 5000}}
    fees = {"source": "s", "phi_buy": 0, "phi_sell": 0}
    ticks = {"source": "s", "effective_from": "2026-10-02", "books": {"KRX_stock_book": [[0, 1], [2000, 5]]}}
    for near in ("lots", "lot_size", "minimum", "min_orders", "fees", "fee_extra", "tick", "ticks", "odds_sources"):
        bad(lambda d, k=near: d[v]["upbit"].update({k: dict(lot)}), f"venues: upbit: unknown key(s) [{near!r}]")
    up, kis = "venues: upbit", "venues: kis: tick_ladder"
    bad(lambda d: d[v]["upbit"].update(lot=None), f"{up}: lot: expected a mapping")
    bad(lambda d: d[v]["upbit"].update(lot={"units": {"BTC": 1}}), f"{up}: lot: missing key(s) ['source']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "step": 1}), f"{up}: lot: unknown key(s) ['step']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "source": " "}), f"{up}: lot: source: expected a non-empty string")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {}}), f"{up}: lot: units: expected a non-empty mapping")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": [1]}), f"{up}: lot: units: expected a non-empty mapping")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {"btc": 1}}),
        f"{up}: lot: units: 'btc' is not a symbol of sections ['crypto']")
    bad(lambda d: d[v]["upbit"].update(lot={**lot, "units": {"005930": 1}}),
        f"{up}: lot: units: '005930' is not a symbol of sections ['crypto']")
    for step in (0, -1, True, "1"):
        bad(lambda d, s=step: d[v]["upbit"].update(lot={**lot, "units": {"BTC": s}}),
            f"{up}: lot: units: BTC: expected a finite number > 0, got {step!r}")
    bad(lambda d: d[v]["upbit"].update(min_order={"source": "s"}), f"{up}: min_order: missing key(s) ['quote']")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": []}),
        f"{up}: min_order: quote: expected a non-empty mapping of settlement asset to a minimum")
    bad(lambda d: d[v]["upbit"].update(min_order={**low, "quote": {"USDT": 1}}),
        f"{up}: min_order: quote: 'USDT' is not one of the settlement assets ['KRW']")
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
    bad(lambda d: d[v]["upbit"].update(fee_extras={**fees, "currency": "KRW"}),
        f"{up}: fee_extras: unknown key(s) ['currency']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_ETF_line": [[0, 1], [2000, 5]]}}),
        f"{kis}: books: KRX_ETF_line: its ladder is core/quant/instruments.py's")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock": [[0, 1]]}}),
        f"{kis}: books: 'KRX_stock' is not one of ['KRX_stock_book', 'US_shares_KIS', 'crypto_venue']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"crypto_venue": [[0, 1]]}}),
        f"{kis}: books: crypto_venue is the cost book of no symbol in sections ['krx', 'us']")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {}}),
        f"{kis}: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": []}}),
        f"{kis}: books: KRX_stock_book: expected a non-empty list of [price_from, tick] rows")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 1, 2]]}}),
        f"{kis}: books: KRX_stock_book: [0, 1, 2] is not a [price_from, tick] row")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[1, 1], [2000, 5]]}}),
        f"{kis}: books: KRX_stock_book: the first price_from must be 0, got 1")
    for rows in ([[0, 1], [2000, 5], [2000, 10]], [[0, 1], [5000, 10], [2000, 5]]):
        bad(lambda d, r=rows: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": r}}),
            f"{kis}: books: KRX_stock_book: price_from {rows[2][0]!r} is not above the row before")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 0]]}}),
        f"{kis}: books: KRX_stock_book: tick: expected a finite number > 0, got 0")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[0, 1], [-5, 1]]}}),
        f"{kis}: books: KRX_stock_book: price_from: expected a finite number >= 0, got -5")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "books": {"KRX_stock_book": [[False, 1]]}}),
        f"{kis}: books: KRX_stock_book: price_from: expected a finite number >= 0, got False")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "effective_from": "20261002"}),
        f"{kis}: effective_from: expected a quoted YYYY-MM-DD date, got '20261002'")
    bad(lambda d: d[v]["kis"].update(tick_ladder={**ticks, "effective_from": "2026-13-01"}),
        f"{kis}: effective_from: '2026-13-01' is not a calendar date")
    bad(lambda d: d[v]["kis"].update(tick_ladder={"source": "s", "books": ticks["books"]}),
        f"{kis}: missing key(s) ['effective_from']")
    bad(lambda d: d[v].update(okx="not a mapping"), "venues: okx: expected a mapping")
```

  **Edit T2**, `tests/compliance_tables.py`. Anchor: the last two lines of `test_deposit_entries` and the banner of
  the "Hashes and the approved state" section below it. The new section goes between them. Old text (exact):

```python
    vdoc["venues"]["upbit"]["deposits"] = [btc, {**btc, "network": "lightning"}]
    assert _facts(vdoc).venues["upbit"].deposits == {("BTC", "bitcoin", False), ("BTC", "lightning", False)}


# --------------------------------------------------------------------------- #
# Hashes and the approved state
```

  New text:

```python
    vdoc["venues"]["upbit"]["deposits"] = [btc, {**btc, "network": "lightning"}]
    assert _facts(vdoc).venues["upbit"].deposits == {("BTC", "bitcoin", False), ("BTC", "lightning", False)}


# --------------------------------------------------------------------------- #
# Venue odds keys (odds plan Task 2; Q17): lot, min_order, fee_extras, tick_ladder
# --------------------------------------------------------------------------- #
_ODDS_SOURCE = "UNVERIFIED: owner to confirm before approval"
_KRX_LADDER = [[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]
# rules.py imports exactly these (as of 5816d3c): the odds lookups add none (the gate's purity tests scan Venue)
_RULES_IMPORTS = frozenset({
    "__future__", "argparse", "codecs", "collections.abc", "core.compliance", "core.compliance.model",
    "cryptography.hazmat.primitives.asymmetric.ed25519", "dataclasses", "datetime", "hashlib", "json", "math", "os",
    "pathlib", "re", "string", "sys", "types", "typing", "yaml"})


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
        lot={"source": _ODDS_SOURCE, "units": {"default": 1e-8}},
        min_order={"source": _ODDS_SOURCE, "quote": {"KRW": 5000}},
        fee_extras={"source": _ODDS_SOURCE, "phi_buy": 12.5, "phi_sell": 0},
        tick_ladder={"source": _ODDS_SOURCE, "effective_from": "2026-01-01", "books": {"crypto_venue": [[0, 1]]}})
    return doc


def test_venue_odds_keys_parse_to_exact_tuples():
    facts = _facts(_odds_venues_doc())
    kis, upbit, okx = facts.venues["kis"], facts.venues["upbit"], facts.venues["okx"]
    ladder = tuple((float(p), float(t)) for p, t in _KRX_LADDER)
    assert kis.lot == (("005930", 1.0), ("default", 1.0)) and kis.min_order == (("KRW", 0.0), ("USD", 0.0))
    assert kis.fee_extras == (0.0, 0.0)                        # an explicit 0 is a signed value (O11)
    assert kis.tick_ladder == (("KRX_stock_book", "2026-10-02", ladder), ("US_shares_KIS", "2026-10-02", ((0.0, 0.01),)))
    assert kis.odds_sources == (("fee_extras", "https://example.invalid/kis-fees"),
                                ("lot", "https://example.invalid/kis-lot"),
                                ("min_order", "https://example.invalid/kis-min"),
                                ("tick_ladder", "https://example.invalid/ticks"))
    assert upbit.lot == (("default", 1e-8),) and upbit.min_order == (("KRW", 5000.0),)
    assert upbit.fee_extras == (12.5, 0.0) and upbit.tick_ladder == (("crypto_venue", "2026-01-01", ((0.0, 1.0),)),)
    assert upbit.odds_sources == tuple((k, _ODDS_SOURCE) for k in ("fee_extras", "lot", "min_order", "tick_ladder"))
    numbers = [n for _, n in (*kis.lot, *kis.min_order, *upbit.lot, *upbit.min_order)]
    numbers += [*kis.fee_extras, *upbit.fee_extras] + [x for _, _, rows in kis.tick_ladder for row in rows for x in row]
    assert numbers and all(type(n) is float for n in numbers), numbers        # a YAML int is stored as a float
    assert (okx.lot, okx.min_order, okx.fee_extras, okx.tick_ladder, okx.odds_sources) == ((), (), None, (), ())
    assert okx == _facts().venues["okx"]                     # an absent key is the default, so the leg is not tradable
    assert kis.markets == frozenset() and kis.quote_by_currency and kis.settlement == {"KRW", "USD"}
    assert upbit.markets == {("BTC", "KRW"), ("USDT", "KRW")} and upbit.default_quote == "KRW"
    assert len({kis, upbit, okx}) == 3                       # every field stays hashable
    _need_model()
    state = rules.approved_state(_table(_row()), _dump(_map_doc()), _dump(_odds_venues_doc()), seq=1)
    assert state.valid and state.venues.venues["upbit"] == upbit, state.reason


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
    Venue method and trap rules.date, rules.Path and rules.os, so no parse_date, file, clock or zone name, and no
    new import in rules.py."""
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
    tree = ast.parse(inspect.getsource(rules))
    imported = {n.module if isinstance(n, ast.ImportFrom) else a.name
                for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert imported == _RULES_IMPORTS, sorted(imported ^ _RULES_IMPORTS)


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
    assert rules._odds_number(0, "w", positive=False) == 0.0 and type(rules._odds_number(3, "w", positive=True)) is float


# --------------------------------------------------------------------------- #
# Hashes and the approved state
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: tracebacks, and exactly these five FAIL lines (every other line is a PASS, plus the one NOT_RUN line
  `NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink REFDATA: symlink creation needs Developer
  Mode`, which turns into a PASS where Developer Mode is on):

```
FAIL compliance_tables/test_check_extras_lives_in_the_parser AssertionError: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_odds_keys_parse_to_exact_tuples Invalid: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_odds_lookups_are_pure_tuple_lookups AttributeError: type object 'Venue' has no attribute 'lot_for'
FAIL compliance_tables/test_venue_odds_lookups_fall_back_and_answer_none Invalid: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_shape_rules AssertionError: (('venues: upbit: lot: expected a mapping',), "venues: upbit: unknown key(s) ['lot']")
```

  then the tail `63/69 passed, 5 failed, 1 not run` and exit code 1. (69 = the 65 tests the module holds once the
  follow-up has merged, plus the four new ones; if Task 1's ledger records another count for the merged module, the
  total is that count plus 4 and the failures are the same five.)

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `core/compliance/rules.py` (LF, kept). Re-read the file before each one (DRIFT
  RULE). Together they add about 115 lines, none longer than 120 characters, and no import.

  **Edit R1**, `core/compliance/rules.py`. Anchor: the constant `_VENUE_OPTIONAL` with `_VENUES_SCHEMA` and
  `_VENUE_REQUIRED` above it (rules.py:635-637 at `5816d3c`; about 31 lines lower once the follow-up has merged).
  Old text (exact):

```python
_VENUES_SCHEMA = "tradegen.venues/1"
_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits"})
```

  New text:

```python
_VENUES_SCHEMA = "tradegen.venues/1"
_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits",
                             "lot", "min_order", "fee_extras", "tick_ladder"})      # the odds keys (odds plan Q17)
# The cost books a signed tick ladder may cover. KRX_ETF_line is not one: its ladder is core/quant/instruments.py's.
_LADDER_BOOKS = frozenset({"KRX_stock_book", "US_shares_KIS", "crypto_venue"})
```

  **Edit R2**, `core/compliance/rules.py`. Anchor: the class `Venue`, its `deposits` field and the def line of
  `is_market` below it (rules.py:314-316 at `5816d3c`). The new fields go right after `deposits`. Old text (exact):

```python
    deposits: frozenset = frozenset()                    # {(symbol, network, tag_required: bool)}

    def is_market(self, inst: Instrument, counter: str) -> bool:
```

  New text:

```python
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
```

  **Edit R3**, `core/compliance/rules.py`. Anchor: the class `Venue`, its `quote_for` method and the decorator and
  def line of `VenueFacts` below it (rules.py:324-330 at `5816d3c`). The three lookups follow `quote_for`. Old text
  (exact):

```python
    def quote_for(self, inst: Instrument) -> str:
        """What a buy of `inst` pays with here: its currency, or the venue's default quote."""
        return inst.currency if self.quote_by_currency else self.default_quote


@dataclass(frozen=True, kw_only=True)
class VenueFacts:
```

  New text:

```python
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
```

  **Edit R4**, `core/compliance/rules.py`. Anchor: the parser `_venue(vid, entry, instruments)`, from its def line
  through its `return Venue(...)` statement (rules.py:640-695 at `5816d3c`; about 31 lines lower once the follow-up
  has merged). The five helpers go right above `_venue`; the odds keys are read after `deposits`, so every earlier
  refusal keeps its exact text and order. The old text is the whole function, so a drift anywhere in it is seen.
  Old text (exact):

```python
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
    return Venue(id=vid, sections=sections, settlement=settlement, markets=frozenset(markets),
                 quote_by_currency=bool(by_currency), default_quote=default, deposits=frozenset(deposits))
```

  New text:

```python
def _odds_number(value, where: str, *, positive: bool) -> float:
    """A finite int or float, never a bool: > 0 when `positive`, else >= 0 (an explicit 0 is a signed value)."""
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < 0 or (positive and value == 0)):
        raise Invalid(f"{where}: expected a finite number {'> 0' if positive else '>= 0'}, got {value!r}")
    return float(value)


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
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All
  run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: every line PASS except the one NOT_RUN line of Step 2, then `68/69 passed, 0 failed, 1 not run` (exit
  code 0; with Developer Mode on, `69/69 passed, 0 failed, 0 not run`; a different merged count gives that count plus
  4, still with 0 failed).

  Overlap check, then the gate, whose byte pins, shipped-fact tests and both purity tests
  (`test_gate_call_graph_has_no_clock_zone_file_or_socket`, which now scans the three lookups, and
  `test_purity_no_file_clock_zone_or_network`) must stay green unchanged:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected, ending: `49/49 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the `--check` CLI, whose draft diff (`rules._changed`) now reads the new fields:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `36/36 passed, 0 failed, 0 not run` (exit code 0; 36 once the follow-up has merged).

  Overlap check, then the static guards and the store (Global Constraints: every task that touches
  `core/compliance`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run` (exit code 0). A failure names the offending file and
  text: fix `rules.py`, never the guard.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` (exit code 0; `test_code_files_is_the_import_closure` still
  sees the same closure, because rules.py gained no import).

  Overlap check, then the core-wide scans (Global Constraints: every task that changes `core/`), one at a time:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness
.venv/Scripts/python.exe -m tests.macro_tf_gov
.venv/Scripts/python.exe -m tests.macro_m7_ledger
.venv/Scripts/python.exe -m tests.macro_m8_forward
.venv/Scripts/python.exe -m tests.macro_m6_context
```

  Expected: each prints no FAIL line and ends with `0 failed` and exit code 0, with the same passed and not-run
  counts Task 1 recorded under "Runs" in the execution ledger.

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18) and the whole compliance suite, each
  followed by restoring the tracked results file:

```bash
.venv/Scripts/python.exe tests/run_all.py --suite cockpit
git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite compliance
git checkout -- qa/acceptance_results.json
```

  Expected: the cockpit run ends with `0 failed` and the counts Task 1 recorded; the compliance run lists every
  `compliance/...` row as PASS except the two REFDATA symlink rows (`compliance/compliance_isolation/
  test_symlinks_are_refused` and `compliance/compliance_tables/test_calendar_sha256_refuses_a_file_symlink`), and
  ends `329/331 passed, 0 failed, 2 not run; <path of qa/acceptance_results.json>` (the follow-up's 327 rows plus
  this task's 4), exit code 0. Then `git status --short` lists only ` M core/compliance/rules.py`,
  ` M tests/compliance_tables.py` and `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  Then the raw-text checks (git only; no overlap check needed):

```bash
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode" -- core/compliance/rules.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|setattr|delattr|globals\(|vars\(|locals\(|__dict__|__builtins__|\.(post|put|delete|patch|request)\(" -- core/compliance/rules.py
```

  Expected: both print nothing (exit code 1).

  Append the tails of these runs, one line each, under "Runs" in the execution ledger (LF; it stays untracked).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/rules.py tests/compliance_tables.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF). Then:

```bash
git commit -m "feat(compliance): venue odds keys lot, min_order, fee_extras and tick_ladder" -m "Odds plan Task 2 (Q17): the venues parser checks the four odds keys strictly, check_extras included, and Venue gains their defaulted fields and pure lookups." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
