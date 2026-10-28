### Task 3: Sourced odds values in the shipped venues.yaml (`core/odds/venues.yaml`)

**Files:**
- Modify: `core/odds/venues.yaml` (LF, kept; the venues draft the owner approves, not a closure file). Anchors: the
  header comment, its lines 2-4 (Edit V1); the `kis:` entry, its `quote_by_currency`, `deposits: []` and `source:`
  lines (Edit V2); the `upbit:` entry, the last line of its `deposits` block and its `source:` line (Edit V3).
- Modify: `tests/compliance_tables.py` (LF, kept). Anchor: `test_shipped_urls_come_from_the_research`, the last test
  of the file, its closing `for kind in _T5_SHIPPED:` loop (Edit T3).
- Test: `tests/compliance_tables.py`

**Interfaces:**
- Consumes:
  - Task 2: `rules.Venue.lot`, `.min_order`, `.fee_extras`, `.tick_ladder`, `.odds_sources`, `Venue.lot_for(symbol)`,
    `Venue.min_order_for(quote)`, `Venue.ladder_for(book)`; in `tests/compliance_tables.py` the constant
    `_KRX_LADDER` (`[[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]`).
  - `tests/compliance_tables.py`, unchanged since `5816d3c`: `_t5_shipped()` (`(RulesTable, InstrumentMap,
    VenueFacts)` of the three shipped drafts), `_t5_raw(kind) -> bytes`, `_t5_ref_ok(entry) -> bool` (True for any
    https URL; a repo path must exist and an `#L<n>` anchor must be a line of the file), `_T5_REPO`,
    `_T5_UNVERIFIED`, `_t5_re` (the `re` module); `test_shipped_urls_come_from_the_research` already checks every
    https URL of the shipped file against the research corpus.
- Produces:
  - `core/odds/venues.yaml` carrying exactly these odds values: kis `lot {"005930": 1, "069500": 1}`, kis
    `min_order {KRW: 0}`, kis `tick_ladder` (`KRX_stock_book`, `effective_from "2026-10-02"`), upbit
    `min_order {KRW: 5000}`; no `fee_extras` on any venue. Task 6's `test_terms_from_the_fixture_venues` (the shipped
    `kis.ladder_for("KRX_stock_book")` through `F.approved()`), Task 13's NOT_TRADABLE pipeline case (shipped venues
    through `F.approved()`) and Task 19's smoke run and hand-off rely on these values; Task 5's `ODDS_VENUES` mirrors
    them as a separate fixture. Every leg is NOT_TRADABLE on them until the owner acts (below).
  - In `tests/compliance_tables.py`: the constants `_T5_KIS_LOTS`, `_T5_KIS_TICKS`, `_T5_UPBIT_MIN` and the test
    `test_shipped_venue_odds_values_are_the_sourced_ones`.

**Plan decisions used:** Q18 (shipped values: only researched ones), Q3 (O3: sourced values only), Q11 (O11: a
missing lot, minimum or fixed charge is NOT_TRADABLE), RULINGS O4 (the class whitelist); RULINGS_ROUND2 R2-5 (the
replay leg needs only the Upbit lot beside the shipped Upbit minimum), R2-13 (the DRIFT RULE for
`tests/compliance_tables.py`).

What this task does and why:
- Spec 5.1 "Venue facts" and 7.2 "Costs, minimums": lots, minimums and ticks come from the signed `venues.yaml`; O3
  allows only values with a research source. These are the four that have one:
  - kis `lot` 1 for 005930 and 069500: the venue table of
    `research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md` gives a minimum ticket
    of "1 share" for KOSPI/KOSDAQ cash stocks (line 161) and "1 unit" for plain 1x ETFs (line 163); line 159 is only
    the header row. Both values cite `#L161`; the new test pins what lines 161 and 163 say, because `_t5_ref_ok`
    only checks that line 161 exists.
  - kis `min_order {KRW: 0}`: the same rows; the minimum is one lot, with no money minimum on top.
  - the KRX stock `tick_ladder`: the price-band table of
    `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/E2_nyse_microstructure_execution.md`
    lines 306-314, citing the KRX tick page (line 316). Its `effective_from` "2026-10-02" is the date the research
    states ("As of 2 October 2026", line 3); `costs.check_validity` (Task 6) refuses a KRX stock fill before it.
  - upbit `min_order {KRW: 5000}`: Upbit's KRW market docs, as confirmed in
    `research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas_verification.md:21`.
  Both https URLs are already in the research corpus, so `test_shipped_urls_come_from_the_research` covers them with
  no change. The new test also pins every value against the research text itself (lots: lines 161 and 163; the
  ladder: E2 lines 308-314, its URL line 316 and its date line 3; the Upbit minimum and its URL: line 21), so a typo
  made in both the YAML and the test's own expected value (a lot, the Upbit minimum, `_KRX_LADDER`), or a wrong
  date, fails.
- Not added, because no research source gives them: any `fee_extras`; an Upbit, OKX or US lot; a US or OKX minimum;
  any deposit network (an owner act, O3). 114800 and 252670 get no lot: the odds whitelist (O4: class share, etp_1x
  with multiple exactly +1, coin) refuses their classes (`etp_index_inverse`, `etp_leveraged`) as
  UNSUPPORTED_PRODUCT before any cost check, although line 163 covers a 1x inverse ETF; 005930 and 069500 are the
  only kis KRX symbols the engine supports. So in the shipped draft EVERY leg is NOT_TRADABLE: a kis KRX leg lacks
  `fee_extras`, a kis US leg lacks its lot and USD minimum, an upbit leg lacks its lot (and `fee_extras` unless it is
  the replay leg), and okx has nothing. That stays so until the owner adds explicit fixed charges (`fee_extras`, 0
  allowed) and the missing lots, and approves the venues file (owner act 3). The S_C3 replay leg needs only the Upbit
  lot beside the shipped Upbit minimum (R2-5). On a card the shipped draft shows the generic NOT_TRADABLE reason
  (`why.NOT_TRADABLE` of Task 12's catalogue, CONTRACT 10.4, raised by Task 13's pipeline: a minimum order, lot size
  or fixed charge is missing); that text does not name the owner act. The owner-act wording (explicit `fee_extras`,
  0 allowed, the missing lots, owner act 3) lives in the plan header's owner-acts list and in Task 19's hand-off.
  TASKS asks the card's refusal to name it too; Step 4 records that gap under "Deferred minors" for the coordinator.
- The header comment's clause "the odds plan adds lots, minimums and ticks later, which changes this file's sha256
  and needs a new approval." becomes "the odds plan added the sourced lots, minimums and the KRX stock tick ladder;
  every other odds value is absent until the owner adds it, so those legs are not tradable, and this file's sha256
  changed, so it needs a new approval." (CONTRACT 4.2, pinned word for word by the new test). Header line 4 ("A venue
  with no deposit entry for a coin credits none, so a withdrawal there fails closed.") stays as it is.
- Byte pins kept (`tests/compliance_gate.py:336-340, :695-697, :998-1000`, unchanged): no new line holds
  `tag_required`, `okx:` stays at two-space indent (the pins split the file at `\n  okx:`), and the upbit `markets`
  line keeps its exact flow form `markets: [[BTC, KRW], [USDT, KRW]]`. Every new number is an int, every quoted
  symbol a string, and the date a quoted string, so the strict loader reads the file and the `yaml.safe_load` /
  `yaml.dump` round trip of `tests/compliance_cli.py::test_check_draft_diff_lists_changed_entries_and_sources` still
  diffs only the two `markets` fields.
- The venues sha256 changes. No `approved {kind: venues}` exists yet (owner act 3 is not done), so nothing is
  re-signed now. `core/odds/venues.yaml` is data, not a closure file: the D14 code hash does not move.
- Drift (R2-13): the follow-up changed `tests/compliance_tables.py` (tests after :300, a test and the `_T5_PINNED`
  block above `test_shipped_okx_warning_has_only_the_cap_slot`, one added assertion in
  `test_shipped_d16_rows_need_live_evidence`, and rewritten assertions), not the end of the file where this task
  appends; the follow-up does not touch `core/odds/venues.yaml`. Re-read each file before each Edit. If an old
  text differs only because an earlier plan changed it, make the same change to the current text, keep the earlier
  behaviour, and add one line under "Drift rulings" in the execution ledger; if the change no longer makes sense, stop
  and rule.
- Covers spec 8, odds items 5 (the tick floor's inputs) and 6 (NOT_TRADABLE groundwork).

- [ ] **Step 1: Write the failing test**

  One Edit-tool replacement in `tests/compliance_tables.py` (LF, kept). Re-read the file first (DRIFT RULE).

  **Edit T3**, `tests/compliance_tables.py`. Anchor: `test_shipped_urls_come_from_the_research`, the last test of the
  file, its closing `for kind in _T5_SHIPPED:` loop (the last five lines of the file at `5816d3c`). The new section
  goes after it, at the end of the file. Old text (exact):

```python
    for kind in _T5_SHIPPED:
        urls = _t5_re.findall(r'https://[^"\s]+', _t5_raw(kind).decode("utf-8"))
        assert urls, kind
        for url in urls:
            assert url.encode("utf-8") in known, (kind, url)
```

  New text:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash (the odds aggregator lists only `odds_*` modules, so this test runs through
  the compliance aggregator; Bash tool `timeout: 300000`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/test_shipped_venue_odds_values_are_the_sourced_ones; echo "exit $?"
```

  Expected: a traceback, then

```
FAIL compliance_tables/test_shipped_venue_odds_values_are_the_sourced_ones AssertionError: ()

0/1 passed, 1 failed, 0 not run
exit 1
```

  (the shipped kis entry has no odds key yet, so its `odds_sources` is the empty default).

- [ ] **Step 3: Implement**

  Three Edit-tool replacements in `core/odds/venues.yaml` (LF, kept). Re-read the file first (DRIFT RULE; the
  follow-up does not change it, so each old text should match exactly). Indentation is spaces only: four before
  each new key of a venue, six inside the `tick_ladder` block.

  **Edit V1**, `core/odds/venues.yaml`. Anchor: the header comment, lines 2-4. The clause from "the odds plan adds"
  to "needs a new approval." is replaced; line 4 stays. Old text (exact):

```yaml
# as `approved {kind: venues}` are in force. The compliance plan writes markets, settlement and deposits only; the
# odds plan adds lots, minimums and ticks later, which changes this file's sha256 and needs a new approval.
# A venue with no deposit entry for a coin credits none, so a withdrawal there fails closed.
```

  New text:

```yaml
# as `approved {kind: venues}` are in force. The compliance plan writes markets, settlement and deposits only; the
# odds plan added the sourced lots, minimums and the KRX stock tick ladder; every other odds value is absent until
# the owner adds it, so those legs are not tradable, and this file's sha256 changed, so it needs a new approval.
# A venue with no deposit entry for a coin credits none, so a withdrawal there fails closed.
```

  **Edit V2**, `core/odds/venues.yaml`. Anchor: the `kis:` entry, its `quote_by_currency`, `deposits: []` and
  `source:` lines (lines 10-12 at `5816d3c`). The three odds keys go after `deposits: []`. Old text (exact):

```yaml
    quote_by_currency: true        # a KRX code trades for KRW, a US ticker for USD
    deposits: []
    source: "docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md#5.1 venue facts"
```

  New text:

```yaml
    quote_by_currency: true        # a KRX code trades for KRW, a US ticker for USD
    deposits: []
    lot: {source: "research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md#L161", units: {"005930": 1, "069500": 1}}
    min_order: {source: "research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md#L161", quote: {KRW: 0}}
    tick_ladder:
      source: "https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp"
      effective_from: "2026-10-02"
      books: {KRX_stock_book: [[0, 1], [2000, 5], [5000, 10], [20000, 50], [50000, 100], [200000, 500], [500000, 1000]]}
    source: "docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md#5.1 venue facts"
```

  **Edit V3**, `core/odds/venues.yaml`. Anchor: the `upbit:` entry, the BTC line of its `deposits` block and its
  `source:` line (lines 19-20 at `5816d3c`). The minimum goes after the deposits block. Old text (exact):

```yaml
      - {symbol: BTC, network: bitcoin, tag_required: false}
    source: "https://api.upbit.com/v1/market/all?is_details=false"
```

  New text:

```yaml
      - {symbol: BTC, network: bitcoin, tag_required: false}
    min_order: {source: "https://docs.upbit.com/kr/docs/krw-market-info", quote: {KRW: 5000}}
    source: "https://api.upbit.com/v1/market/all?is_details=false"
```

  The file grows from 49 to 57 lines (2,031 to 2,799 bytes); its sha256 becomes
  `283c143f800b7ddc6db8b1b2dd77c8624da1a3e5d4a2fe9e4ca6dbec7dfa042a` (sandbox, 2026-10-28, applied to the
  `5816d3c` bytes). The owner approves a later version of this file in owner act 3, after adding the missing values;
  this draft alone leaves every leg not tradable.

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before EACH Python command below, never
  two at once. All run from the repo root in Git Bash. Give every Python command the Bash tool `timeout: 300000`,
  and the `--suite compliance` line `timeout: 600000`: `compliance_store/` alone can run past the 120 s default, and
  a killed command skips whatever is chained after it. This task changes `core/odds/venues.yaml`, so the core-wide
  scans run as well (Global Constraints: every task that changes `core/`); they read only `.py` files, so their
  counts do not move.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/; echo "exit $?"
```

  Expected: every line PASS (`test_shipped_tables_parse_valid`, `test_shipped_files_are_utf8_lf_and_small`,
  `test_shipped_venue_facts_p22`, `test_shipped_sources_are_https_or_repo_paths` and
  `test_shipped_urls_come_from_the_research` included) except the one NOT_RUN line
  `NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink REFDATA: symlink creation needs Developer
  Mode`, then `69/70 passed, 0 failed, 1 not run` and `exit 0` (with Developer Mode on, `70/70 passed, 0 failed,
  0 not run`; a different merged count gives Task 2's total plus 1, still with 0 failed).

  Overlap check, then the gate, whose three byte pins (`test_history_maps_serve_exits_only` and the two tagged-deposit
  partitions at `\n  okx:`) and shipped-fact tests read the edited file:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/; echo "exit $?"
```

  Expected, ending: `49/49 passed, 0 failed, 0 not run`, then `exit 0`.

  Overlap check, then the CLI, whose `test_check_code_0_and_alert_rows_are_accepted` signs the shipped drafts and
  whose `test_check_draft_diff_lists_changed_entries_and_sources` round-trips the edited file through
  `yaml.safe_load` and `yaml.dump`:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/; echo "exit $?"
```

  Expected, ending: `36/36 passed, 0 failed, 0 not run`, then `exit 0`.

  Overlap check, then the static guards (Global Constraints: every task that touches `core/odds` or
  `tests/compliance_*`):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run`, then `exit 0`.

  Overlap check again, then the store:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/; echo "exit $?"
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run`, then `exit 0` (its store tests use the shipped venues bytes
  as an opaque blob). For the guards and the store, a fix wave of the follow-up may have changed the counts: the
  merged counts with `0 failed` are right.

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

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18; it rewrites the tracked
  `qa/acceptance_results.json`, restored on the same line; Bash tool `timeout: 300000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: the summary line `N/M passed, 0 failed, K not run; ` followed by the path of
  `qa\acceptance_results.json`, with the N, M and K Task 1 recorded (`47/47 passed, 0 failed, 0 not run` at
  drafting), then `exit 0`.

  Overlap check again, then the whole compliance suite (it rewrites the same file, restored on the same line; Bash
  tool `timeout: 600000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: every `compliance/...` row PASS except the two REFDATA symlink rows
  (`compliance/compliance_isolation/test_symlinks_are_refused` and
  `compliance/compliance_tables/test_calendar_sha256_refuses_a_file_symlink`), then
  `330/332 passed, 0 failed, 2 not run; ` followed by the path (Task 2's 331 rows plus this task's 1; with
  Developer Mode on, `332/332 passed, 0 failed, 0 not run`), then `exit 0`.

  Then the file checks (git and coreutils only; no overlap check needed):

```bash
git status --short
git diff --stat -- core/odds/venues.yaml
sha256sum core/odds/venues.yaml
git grep -n -E "tag_required|^  okx:|markets: \[\[BTC, KRW\], \[USDT, KRW\]\]" -- core/odds/venues.yaml
```

  Expected: `git status --short` lists exactly ` M core/odds/venues.yaml`, ` M tests/compliance_tables.py` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; the stat shows
  `core/odds/venues.yaml | 10 +++++++++-` (9 insertions, 1 deletion); `sha256sum` prints
  `283c143f800b7ddc6db8b1b2dd77c8624da1a3e5d4a2fe9e4ca6dbec7dfa042a *core/odds/venues.yaml` (Git Bash marks binary
  mode with `*`); the grep prints exactly these four lines (the upbit markets line, the two deposit lines and the
  `okx:` line the byte pins rely on):

```
core/odds/venues.yaml:23:    markets: [[BTC, KRW], [USDT, KRW]]   # KRW-quoted only (P22)
core/odds/venues.yaml:26:      - {symbol: BTC, network: bitcoin, tag_required: false}
core/odds/venues.yaml:50:  okx:
core/odds/venues.yaml:56:      - {symbol: BTC, network: bitcoin, tag_required: false}
```

  Record the runs in the execution ledger (LF; it stays untracked), with the Edit tool. At the end of its `## Runs`
  section (the end of the file), add one line per Python run above, in the order run, each
  `- Task 3: <the command after .venv/Scripts/python.exe>: <its summary line>` (the `; echo` part and the path after
  `;` left out), for example `- Task 3: -m tests.compliance_acceptance compliance_tables/: 69/70 passed, 0 failed,
  1 not run`, then the line `- Task 3: core/odds/venues.yaml sha256
  283c143f800b7ddc6db8b1b2dd77c8624da1a3e5d4a2fe9e4ca6dbec7dfa042a` (one line in the ledger). Then add this one line
  (one line in the ledger) at the end of the `## Deferred minors` section, after its last `- Task` line and before
  the blank line above `## Runs`: "- Task 3: TASKS asks the card's NOT_TRADABLE refusal to name the owner act
  (explicit fee_extras, 0 allowed, the missing lots, approve the venues file); CONTRACT 10.4 why.NOT_TRADABLE does
  not, so only the plan header and Task 19 carry it. For the coordinator / spec rev 3.3."

- [ ] **Step 5: Commit**

```bash
git add core/odds/venues.yaml tests/compliance_tables.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF). Then:

```bash
git commit -m "feat(odds): sourced lots, minimums and the KRX stock tick ladder in venues.yaml" -m "Odds plan Task 3 (Q18): only researched odds values ship; with no fixed charges and no Upbit, OKX or US lot, every leg stays not tradable until the owner adds and approves them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Afterwards `git status --short` prints only `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
