### Task 2: The venues parser learns the odds keys (`core/compliance/rules.py`)

**Files:**
- Modify: `core/compliance/rules.py` (LF, kept; a D14 closure file). Anchors: the constant `_VENUE_OPTIONAL` with
  `_VENUES_SCHEMA` and `_VENUE_REQUIRED` above it and the def line of `_venue` below it (Edit R1); the class `Venue`,
  its `deposits` field (Edit R2) and its `quote_for` method (Edit R3); the parser `_venue(vid, entry, instruments)`,
  its `return Venue(...)` statement (Edit R4).
- Modify: `tests/compliance_tables.py` (LF, kept). Anchors: `test_venue_shape_rules`, its `minimum_krw` line and the
  `okx="not a mapping"` line after it (Edit T1); the last two lines of `test_deposit_entries` and the
  "Hashes and the approved state" banner below it (Edit T2).
- Test: `tests/compliance_tables.py`

**Interfaces:**
- Consumes (all unchanged, as of `5816d3c`; the follow-up renames none of them):
  - `core.compliance.rules`: `Invalid(reason)` (`.reason == str(exc)`); `_keys(doc, where, required, optional)`
    (`"{where}: expected a mapping"`, then `"{where}: unknown key(s) [...]"`, then `"{where}: missing key(s) [...]"`);
    `_text(value, where)` (`"{where}: expected a non-empty string"`); `_member(value, where, vocab)`
    (`"{where}: {value!r} is not one of {sorted(vocab)}"`); `_positive(value, where)`
    (`"{where}: expected a finite number > 0, got {value!r}"`); `parse_date(value, what)`
    (`"{what}: expected a quoted YYYY-MM-DD date, got {value!r}"`, `"{what}: {value!r} is not a calendar date"`);
    `InstrumentMap.entries` (`(section, symbol) -> Instrument`), `Instrument.cost_book`; inside `_venue` its locals
    `where` (`"venues: <id>"`), `sections` (a tuple), `listed` (`{symbol: section}` over the venue's sections) and
    `settlement` (a frozenset).
  - `tests/compliance_tables.py`: `_dump(doc)`, `_refused(call, *has) -> str` (every `has` is a substring of the
    reason), `_row()`, `_table(*rows)`, `_map_doc()` (krx 005930 `KRX_stock_book`, 252670 `KRX_ETF_line`; us TQQQ,
    SH, AAPL, IBIT, GDLC, BITO `US_shares_KIS`; crypto BTC, USDT, XRP `crypto_venue`), `_venues_doc()` (kis with
    sections krx and us, upbit and okx with section crypto), `_facts(vdoc, mdoc)`, `_need_model()`; inside
    `test_venue_shape_rules` its `bad(mutate, *has)` and `v = "venues"`; the module constant `_T5_UNVERIFIED`
    (`"UNVERIFIED: owner to confirm before approval"`, :801 at `5816d3c`, about 105 lines lower once the follow-up
    has merged; defined at import, so the new tests can read it although it sits further down).
- Produces (Task 3, Task 5's `ODDS_VENUES` and Task 6's `costs.terms` rely on these exact names):
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
    `Venue.ladder_for(book: str) -> tuple[str, tuple[tuple[float, float], ...]] | None`. Every stored number is a
    Python `float`.
  - Private parser helpers, each raising `Invalid` with a reason that starts `venues: <id>: <key>`:
    `_odds_number(value, where: str, *, positive: bool) -> float`,
    `_odds_lot(value, where: str, listed: dict, sections: tuple[str, ...]) -> tuple[tuple[str, float], ...]`,
    `_odds_min_order(value, where: str, settlement: frozenset) -> tuple[tuple[str, float], ...]`,
    `_check_extras(value, where: str) -> tuple[float, float]` (the spec's check_extras) and
    `_odds_ladder(value, where: str, sections: tuple[str, ...], instruments: InstrumentMap) -> tuple`.
  - Exact refusal texts (pinned by Step 1): `{where}: expected a finite number > 0, got {value!r}` and
    `{where}: expected a finite number >= 0, got {value!r}`;
    `venues: <id>: lot: units: expected a non-empty mapping of symbol (or default) to a step`;
    `venues: <id>: lot: units: {key!r} is not a symbol of sections [...]`;
    `venues: <id>: min_order: quote: expected a non-empty mapping of settlement asset to a minimum`;
    `venues: <id>: min_order: quote: {key!r} is not one of the settlement assets [...]`;
    `venues: <id>: tick_ladder: books: expected a non-empty mapping of cost book to [[price_from, tick], ...]`;
    `venues: <id>: tick_ladder: books: KRX_ETF_line: its ladder is core/quant/instruments.py's`;
    `venues: <id>: tick_ladder: books: {book!r} is not one of ['KRX_stock_book', 'US_shares_KIS', 'crypto_venue']`
    (the `_member` text);
    `venues: <id>: tick_ladder: books: <book> is the cost book of no symbol in sections [...]`;
    `venues: <id>: tick_ladder: books: <book>: expected a non-empty list of [price_from, tick] rows`;
    `... <book>: {row!r} is not a [price_from, tick] row`; `... <book>: the first price_from must be 0, got {x!r}`;
    `... <book>: price_from {x!r} is not above the row before`.
  - In `tests/compliance_tables.py`: the constant `_KRX_LADDER` (the KRX stock ladder as YAML lists; Task 3 reuses
    it), the helper `_odds_venues_doc()`, and the tests
    `test_venue_odds_keys_parse_to_exact_tuples`, `test_venue_odds_lookups_fall_back_and_answer_none`,
    `test_venue_odds_lookups_are_pure_tuple_lookups` and `test_check_extras_lives_in_the_parser`.

**Plan decisions used:** Q3 (compliance-side prerequisites first, O3), Q17 (the four keys, their shapes and rules),
Q11 (O11: a missing minimum, lot or fixed charge makes a leg not tradable, an explicit signed 0 is allowed; this task
only stores absence as `()` or None, and Task 6 turns it into NOT_TRADABLE); RULINGS_ROUND2 R2-13 (the DRIFT RULE).

What this task does and why:
- Spec 7.2 "Costs, minimums": minimums and ticks come from `venues.yaml`, and a missing entry is NOT_TRADABLE. Spec 4
  "Costs": extras in `venues.yaml` may only raise costs (`check_extras`). Today `_VENUE_OPTIONAL` (rules.py:637 at
  `5816d3c`) knows only `markets`, `quote_by_currency`, `default_quote` and `deposits`, so every odds key is an
  unknown key and the shipped file cannot carry one (`tests/compliance_tables.py:633` pins `minimum_krw` as unknown).
- After this task each odds key is an optional mapping with exactly its own keys and a mandatory non-empty `source`
  (the parser checks only that it is non-empty text; Task 3's shipped-file test checks that every shipped source is
  a repo reference, an https URL of the research corpus, or the literal `UNVERIFIED: owner to confirm before
  approval`). Stated limit: the source form of Q17 is checked on the shipped draft only, never on the file the owner
  signs, so a signed venues file with `source: x` still parses VALID (CONTRACT 4.1 asks only for non-empty text, as
  for the venue's own `source`); Step 4 records this under "Deferred minors" for the rev 3.3 fold-in. The shapes:
  `lot: {source, units: {<symbol> | default: step}}`, `min_order: {source, quote: {<settlement asset>:
  amount}}`, `fee_extras: {source, phi_buy, phi_sell}`, `tick_ladder: {source, effective_from: "YYYY-MM-DD", books:
  {<cost book>: [[price_from, tick], ...]}}`. Numbers are finite ints or floats, never bools; a lot step and a tick
  are > 0; a minimum, an extra and a price_from are >= 0 (an explicit 0 is a signed value, O11; a YAML `-0.0` is
  stored as `0.0`, so `model.jsonable` and the card never show `-0.0`; the file's sha256, and with it `ctx_hash`,
  still differ from those of a file that writes `0.0`); a ladder starts at price_from exactly 0 and strictly
  increases; a ladder book is in `_LADDER_BOOKS` and is the cost book of at least one instrument in the venue's
  sections. `KRX_ETF_line` is refused by name: its ladder is the one Task 6 copies from
  `core/quant/instruments.py`, and a second, signed ladder could disagree with it. A key written as `null` is refused
  (`expected a mapping`); leaving the key out is the only way to leave a value out. `check_extras` lives in the
  parser, so a negative extra makes the venue file, and with it the whole approved state, INVALID.
- The lookups are plain tuple reads: no `parse_date` call and no file, clock or zone name.
  `tests/compliance_gate.py::test_gate_call_graph_has_no_clock_zone_file_or_socket` AST-scans every `Venue` method
  for the `_T9_FORBIDDEN` names and follows every module-level def or class of rules.py a method names, and
  `test_purity_no_file_clock_zone_or_network` traps `rules.date`, `rules.Path` and `rules.os` during screen and
  decide. So `effective_from` is stored as its checked ISO text, never as a `date`, the lookups use only local names
  that no module-level def of rules.py carries, and `rules.py` gains no import (Step 4 checks the diff).
- Side effects, all intended and covered by tests that stay green unchanged: `model.seal_context` hashes the new
  fields into `ctx_hash` (tuples, floats and None are all `model.jsonable`); `rules._changed` (the `--check` draft
  diff) names a changed odds field like any other field; `test_valid_fixture_venues_parse`'s `rules.Venue(...)`
  equality holds because every new field has a default; the shipped `core/odds/venues.yaml` is not touched here
  (Task 3), so the byte pins of `tests/compliance_gate.py` (:336-340, :695-697, :998-1000) and
  `test_shipped_venue_facts_p22` stay green. No route name of the follow-up's closure scan (its Task 4: `setattr`,
  `delattr`, `globals`, `vars`, `locals`, `modules`, `__dict__`, `builtins`, `__builtins__`, `f_globals`,
  `f_locals`) appears in the new text, so rules.py keeps its `TYPE_CHECKING` and `__main__` skips (Step 4 greps all
  eleven).
- Code hash: `rules.py` is a D14 closure file, so the code hash moves. No `code_approved` exists yet (owner act 2 is
  not done), so nothing is re-signed now; once the owner signs, any later closure change needs a fresh signature.
- Drift (R2-13): the follow-up changes both files of this task. In `rules.py` it inserts six constants above `_match`
  and edits four blocks of `_row`, so `_VENUE_OPTIONAL` moves down about 31 lines; in `tests/compliance_tables.py` it
  adds tests after :300 and (with the `_T5_PINNED` constant) above `test_shipped_okx_warning_has_only_the_cap_slot`
  and rewrites assertions in `test_d16_rows_need_requires_live`, `test_warning_slots` and `test_max_leverage`, and
  follow-up Task 3 adds one assertion to `test_shipped_d16_rows_need_live_evidence`, so the `minimum_krw` line moves
  down several dozen lines. None of its edits touches an anchor of this task, so each old text below should match the
  merged file exactly. Re-read each file before each Edit. If an old text differs only because an earlier plan changed
  it, make the same change to the current text, keep the earlier behaviour, and add one line under "Drift rulings" in
  `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; if the change no longer makes sense, stop and
  rule.
- Covers spec 8, odds item 5 (groundwork: extras may only raise costs).

- [ ] **Step 1: Write the failing tests**

  Two Edit-tool replacements in `tests/compliance_tables.py` (LF, kept). Re-read the file first (DRIFT RULE).

  **Edit T1**, `tests/compliance_tables.py`. Anchor: `test_venue_shape_rules`, its `minimum_krw` line (:633 at
  `5816d3c`) and the `okx="not a mapping"` line after it. The `minimum_krw` line stays: an unknown key is still
  refused. It is joined by near misses of the four exact key names (`odds_sources` is a `Venue` field, never a YAML
  key), four shape checks per key (null, missing source, blank source, an extra key), and one refusal line per rule
  of Q17, each on a document that is valid except for the one value under test. The new lines first rebind the
  local `bad` to one that parses the instrument map once and re-parses only the venue file: the refusals are the
  same (`_facts(vdoc)` is `rules.parse_venues(_dump(vdoc), _map())`), and the test takes about 0.5 s instead of
  about 1 s (about 0.3 s before this task).
  Old text (exact):

```python
    bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")
    bad(lambda d: d[v].update(okx="not a mapping"), "venues: okx: expected a mapping")
```

  New text:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

  The odds aggregator `tests.odds_acceptance` lists only the `odds_*` modules (CONTRACT 3.1), so this task's tests
  run through the compliance aggregator. Overlap check with the PowerShell tool (it must print nothing; otherwise wait
  and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/; echo "exit $?"
```

  Expected: tracebacks, and exactly these five FAIL lines, in this order among the PASS lines. The one other non-PASS
  line is `NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink REFDATA: symlink creation needs
  Developer Mode`, which is a PASS where Windows Developer Mode is on.

```
FAIL compliance_tables/test_check_extras_lives_in_the_parser AssertionError: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_odds_keys_parse_to_exact_tuples Invalid: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_odds_lookups_are_pure_tuple_lookups AttributeError: type object 'Venue' has no attribute 'lot_for'
FAIL compliance_tables/test_venue_odds_lookups_fall_back_and_answer_none Invalid: venues: kis: unknown key(s) ['fee_extras', 'lot', 'min_order', 'tick_ladder']
FAIL compliance_tables/test_venue_shape_rules AssertionError: (('venues: upbit: lot: expected a mapping',), "venues: upbit: unknown key(s) ['lot']")
```

  Then the tail `63/69 passed, 5 failed, 1 not run` and `exit 1` (with Developer Mode on, `64/69 passed, 5 failed,
  0 not run`). 69 is the 65 tests the module holds once the follow-up has merged, plus the four new ones; if Task 1's
  ledger records another count for the merged module, the total is that count plus 4 and the five failures are the
  same.

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `core/compliance/rules.py` (LF, kept). Re-read the file before each one (DRIFT
  RULE). Together they add about 130 lines, none longer than 120 characters, and no import.

  **Edit R1**, `core/compliance/rules.py`. Anchor: the constant `_VENUE_OPTIONAL`, with `_VENUES_SCHEMA` and
  `_VENUE_REQUIRED` above it and the def line of `_venue` below it (rules.py:635-640 at `5816d3c`; about 31 lines
  lower once the follow-up has merged). The odds keys join `_VENUE_OPTIONAL`, and `_LADDER_BOOKS` and the five parser
  helpers go between the constants and `_venue`. Old text (exact):

```python
_VENUES_SCHEMA = "tradegen.venues/1"
_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits"})


def _venue(vid: str, entry, instruments: InstrumentMap) -> Venue:
```

  New text:

```python
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

  **Edit R4**, `core/compliance/rules.py`. Anchor: the parser `_venue(vid, entry, instruments)`, the last line of its
  deposits loop and its `return Venue(...)` statement (rules.py:693-695 at `5816d3c`). The odds keys are read after
  `deposits`, so every earlier refusal keeps its exact text and order. Old text (exact):

```python
        deposits.add((symbol, network, dep["tag_required"]))
    return Venue(id=vid, sections=sections, settlement=settlement, markets=frozenset(markets),
                 quote_by_currency=bool(by_currency), default_quote=default, deposits=frozenset(deposits))
```

  New text:

```python
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

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below. All run
  from the repo root in Git Bash. Give every Python command the Bash tool `timeout: 300000`, and the
  `--suite compliance` line `timeout: 600000` (as odds Task 4 does): a killed command skips whatever is chained after
  it, and for the two `--suite` lines that is the `git checkout` that restores the tracked CRLF results file.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/; echo "exit $?"
```

  Expected: every line PASS except the NOT_RUN line of Step 2, then `68/69 passed, 0 failed, 1 not run` and `exit 0`
  (with Developer Mode on, `69/69 passed, 0 failed, 0 not run`; a different merged count gives that count plus 4,
  still with 0 failed). `test_venue_shape_rules` takes well under a second; no budget binds `compliance_tables`.

  Overlap check, then the gate, whose byte pins, shipped-fact tests and both purity tests
  (`test_gate_call_graph_has_no_clock_zone_file_or_socket`, which now scans the three lookups, and
  `test_purity_no_file_clock_zone_or_network`) must stay green unchanged:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/; echo "exit $?"
```

  Expected, ending: `49/49 passed, 0 failed, 0 not run`, then `exit 0`.

  Overlap check, then the `--check` CLI, whose draft diff (`rules._changed`) now also reads the new fields:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/; echo "exit $?"
```

  Expected, ending: `36/36 passed, 0 failed, 0 not run` (36 once the follow-up has merged), then `exit 0`.

  Overlap check, then the static guards (Global Constraints: every task that touches `core/compliance`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run`, then `exit 0`. A failure names the offending file and text:
  fix `rules.py`, never the guard.

  Overlap check, then the store:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/; echo "exit $?"
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run`, then `exit 0` (`test_code_files_is_the_import_closure`
  still sees the same closure, because rules.py gained no import). For both, a fix wave of the follow-up may have
  changed the counts: the merged counts with `0 failed` are right.

  Overlap check, then the odds guards (rules.py is a D14 closure file; `test_code_closure_holds_no_data_layer`
  recomputes the closure):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/; echo "exit $?"
```

  Expected: no FAIL line, the summary line Task 1 recorded under "Runs" (`18/18 passed, 0 failed, 0 not run` at
  drafting), then `exit 0`.

  The core-wide scans (Global Constraints: every task that changes `core/`), one at a time, with the overlap check
  before each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_tf_gov; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m7_ledger; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m8_forward; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m6_context; echo "exit $?"
```

  Expected: no FAIL line; each summary line reads `N/M passed, 0 failed, K not run` with the same N, M and K that
  Task 1 recorded under "Runs" (at drafting, in this order: `11/11 passed, 0 failed, 0 not run`, `20/22 passed,
  0 failed, 2 not run`, `14/18 passed, 0 failed, 4 not run`, `17/23 passed, 0 failed, 6 not run`, `14/16 passed,
  0 failed, 2 not run`), each followed by `exit 0`.

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18 scan every `core/**/*.py`; it rewrites
  the tracked `qa/acceptance_results.json`, restored at once; Bash tool `timeout: 300000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the summary line `N/M passed, 0 failed, K not run; ` followed by the path of
  `qa\acceptance_results.json`, with the N, M and K Task 1 recorded (`47/47 passed, 0 failed, 0 not run` at
  drafting), then `exit 0`.

  Overlap check again, then the whole compliance suite (it rewrites the same file, restored at once; Bash tool
  `timeout: 600000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: every `compliance/...` row PASS except the two REFDATA symlink rows (`compliance/compliance_isolation/
  test_symlinks_are_refused` and `compliance/compliance_tables/test_calendar_sha256_refuses_a_file_symlink`), then
  `329/331 passed, 0 failed, 2 not run; ` followed by the path (the follow-up's 327 rows plus this task's 4; with
  Developer Mode on, `331/331 passed, 0 failed, 0 not run`), then `exit 0`.

  Then the text checks (git only; no overlap check needed):

```bash
git status --short
git diff -U0 -- core/compliance/rules.py | grep -E '^\+[[:space:]]*(import|from)[[:space:]]'
git grep -n -i -E "order_cash|order-cash|place_order|submit_order|tttc0802u|tttc0801u|vttc0802u|private_key|seed_phrase|/v1/orders|/v1/withdraws|/v1/deposits|/api/v3/order|/sapi/v1/capital|r18_research_log|r18_break_log|context_log/|tests\.reference|reference_mode|reference_only|/uapi/" -- core/compliance/rules.py
git grep -n -E "CANO|KIS_ACCOUNT|ACNT_PRDT_CD|\b(setattr|delattr|globals|vars|locals|modules|builtins|f_globals|f_locals)\b|__dict__|__builtins__|\.(post|put|delete|patch|request)\(" -- core/compliance/rules.py
git diff -U0 -- core/compliance/rules.py | grep -n -i -E '^\+.*(0\.4[[:space:]]*[*x×]|[*x×][[:space:]]*0\.4|kish|def (transfer|withdraw|deposit_address)\b)'
```

  Expected: `git status --short` lists exactly ` M core/compliance/rules.py`, ` M tests/compliance_tables.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; each of the four `grep` commands prints
  nothing (exit code 1): rules.py gained no import, no banned text, none of the eleven route names of the
  follow-up's closure scan (as a bare name or an attribute), no literal `0.4` next to `*`, `x` or `×`, no `kish`
  name and no def named `transfer`, `withdraw` or `deposit_address`.

  Record the runs in the execution ledger (LF; it stays untracked), with the Edit tool. At the end of its `## Runs`
  section (the end of the file), add one line per Python run above, in the order run, each
  `- Task 2: <the command after .venv/Scripts/python.exe>: <its summary line>` (the `; echo` part and the path after
  `;` left out); for example `- Task 2: -m tests.compliance_acceptance compliance_tables/: 68/69 passed, 0 failed,
  1 not run` and `- Task 2: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run`. Then replace the
  ledger's line `## Deferred minors` with that line followed by this one line (one line in the ledger): "- Task 2:
  the parser checks only that each odds-key source is non-empty text (CONTRACT 4.1); the source form of Q17 (a repo
  reference, an https URL of the research corpus, or the literal UNVERIFIED: owner to confirm before approval) is
  checked on the shipped draft only (Task 3), so an owner-signed venues file with source: x still parses VALID. For
  spec rev 3.3."

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
