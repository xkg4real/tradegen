### Task 2: Loader: D15 and D16 by content, D15 rows blocking, review_by/max_leverage/{cap} bounds, exact row pins

**Files:**
- Modify: `core/compliance/rules.py` (LF; a D14 closure file; anchors: the constants `_BLOCKING` and
  `_MAX_REVIEW_DAYS` above `_match`; in `_row`: the axis-check block `if treatment not in _BLOCKING:`, the grey
  `{cap}` check with the `leverage =` line, the block from `policy_ref = item.get("policy_ref")` through the
  gated-row raise, and the `review_by` checks after `latest = max(r.date for r in reviews)`)
- Modify: `tests/compliance_tables.py` (LF; anchors: `test_d16_rows_need_requires_live`, `test_warning_slots`,
  `test_max_leverage`; new tests right above `test_requires_items_in_vocabulary` and right above
  `test_shipped_okx_warning_has_only_the_cap_slot`)
- Modify: `tests/compliance_cli.py` (LF; anchor: `test_render_has_no_rule_free_text`)
- Test: `tests/compliance_tables.py` (59 tests become 65), `tests/compliance_cli.py` (35 tests, one rewritten line)
- Not touched: `core/compliance/kr_rules.yaml`. It stays byte-identical and VALID, sha256
  `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79` (59,408 bytes) until Task 3.

**Interfaces:**
- Consumes:
  - `core.compliance.rules`, unchanged: `Invalid(reason)` (`.reason == str(exc)`), `ETP_ASSETS`
    (`{"krx_etp", "us_etp"}`), `_BLOCKING`, the result of `_match` (a read-only `Mapping[str, frozenset]`; on a
    non-blocking row the axis check guarantees `action`, `financing` and a `class` or `asset` key, and `any` is
    already refused),
    `_warning`, `_positive`, `parse_rules(raw: bytes) -> RulesTable`, and the `Row` fields `.match`,
    `.requires_owner`, `.requires_live`, `.treatment`, `.max_leverage`, `.warning`, `.review_by`, `.policy_ref`.
  - `tests/compliance_tables.py`, unchanged helpers: `_row(**over)` (a valid allow row `T-ALLOW` on upbit coin
    buy/sell for cash, covering all 38 matrix rows; review 2026-10-23, review_by 2026-11-23), `_grey(**over)` (a
    valid grey row `T-GREY` shaped like KR-OKX-SPOT), `_parse(*rows)`, `_bad(*rows_and_has) -> str` (asserts Invalid
    with every needle and returns the reason), `_refused(call, *has)`, `date`; in the compliance plan's Task 5 block
    (the `_t5_` helpers) `_t5_raw(kind)`, `_t5_shipped()` and `_t5_rules`.
  - Task 1: the widened guard lists. The new rules.py text was scanned with Task 1's checkers on 2026-10-24: no
    raw-text, def, verb, dynamic, allowlist, clock, seal or `__main__` hit.
- Produces:
  - In `core/compliance/rules.py`: the private constants `_MAX_LEVERAGE = 10.0`, `_D15_FINANCING`, `_D15_ACTIONS`,
    `_D16_ACTIONS`, `_D16_CLASSES`, `_D16_ASSETS`, and the seven reason strings of the table below. The signatures of
    `_row` and `parse_rules` are unchanged; every existing reason keeps its exact text (R10).
  - In `tests/compliance_tables.py`: the tests `test_d15_rows_never_let_credit_margin_lending_or_borrowing_through`,
    `test_a_d15_row_is_blocking`, `test_d16_by_content_needs_requires_live`,
    `test_review_by_is_not_before_the_latest_review`, `test_only_a_grey_row_states_a_cap` and
    `test_shipped_rows_that_can_let_through_are_pinned_exactly`; the constant `_T5_PINNED`
    (`{row id: (match as {key: set}, requires_owner, requires_live, treatment)}`, 15 rows in table order); and the
    private helper `_t5_pin_misses(table) -> list[str]`, which this task defines (it is not in Appendix A).
  - For later work: Task 3 edits only the KR-KIS-KRX-DERIV reason, so `_T5_PINNED` holds unchanged after it. Any
    later change to a shipped allow, gated or grey row (the odds plan included) updates its `_T5_PINNED` entry in
    the same commit.

**Plan decisions used:** R2 (F2), R10 (the check order and the three deliberate rewrites), R13 with the drift rule
(R2-13) of Global Constraints.

Notes (read before Step 1):
- The rules (R2). For a row whose treatment is allow, gated or grey:
  - D15 by content: it never matches financing `credit` or `margin`, nor action `lend` or `borrow`; margin is D15
    by the compliance plan's Task 7 ruling (ledger:131). `sell_short` is D16 (spec:70), never D15.
  - D16 by content: if its action includes `sell_short`, or its class includes `etp_leveraged`,
    `etp_single_stock`, `krx_derivative` or `elw`, or its asset includes `krx_derivative` or `elw`, it needs a
    non-empty `requires.live`, whatever its policy_ref says. A row with no `class` key that names the asset
    `krx_etp` or `us_etp` matches every class those assets derive to (gate.py:385-401 checks only the keys a row
    has; rules.py:213-224), so it counts as matching `etp_leveraged` and `etp_single_stock`. The D16 label rule
    (rules.py:491-492) stays.
  - The other three rules apply to every row:
    - D15 by label: a row whose policy_ref names D15 is `hard_block` or `out_of_scope`.
    - Bounds: `review_by` is not before the row's latest review date, and `max_leverage <= 10` (10 itself is legal).
    - Only a grey row's warning may hold the `{cap}` slot (ledger:146), so the cap text an owner acks always
      belongs to a grey row's signed cap.
- Check order inside `_row` (R10), so every existing reason keeps its text:
  1. `_match` (it refuses `any`), then the axis check, then D15 content (new, in the same block);
  2. the conduct-ETP check, `requires`, then the ack and grey checks;
  3. the warning slots, with `{cap}` only in grey (new);
  4. `max_leverage`, with the bound (new);
  5. the policy_ref format, the D16 label, then the D15 label (new);
  6. D16 content (new), then the gated-row requirement and the rest of `_row`;
  7. the `review_by` lower bound (new), before the 31-day check.
  So an existing fixture that broke two rules still fails on its old reason: the `any` test's credit row fails on
  `any`, and the "D15, D16" row of `test_d16_rows_need_requires_live` fails on the D16 label.
- Three existing assertions flip on purpose and are rewritten in Step 1 (R10):
  - tables:295, a gated etp_leveraged row citing D160 with no live evidence. It is VALID today and Invalid by D16
    content, so it becomes a `_bad` with that reason, plus an etp_1x line that keeps the "D160 is not D16" intent.
  - tables:316, `{cap}` in an allow row's warning, leaves the allow-row loop.
  - cli:576-577. `test_render_has_no_rule_free_text` appends " {cap}" to every shipped warning, so R2 would make its
    mutated table Invalid at the gated per_session row KR-KIS-US-OPTION ("rules: row KR-KIS-US-OPTION: warning: only
    a grey row states a {cap}", dry run 2026-10-24). The rewrite appends it to the grey row only. The table stays
    VALID and the test still proves that no rule free text renders. It passes before and after R2.
- The shipped table. Read-only probe of 2026-10-24: 47 rows. The 15 allow, gated and grey rows are all
  `financing: [cash]` and none has lend or borrow. The five rows matching sell_short or a D16 class all carry live
  evidence, and no row names an ETP asset without a class axis. The two D15 rows (KR-KIS-CREDIT,
  KR-DOMESTIC-LENDING) are out_of_scope. No review_by is before its review, max_leverage peaks at 3.0, and only
  KR-OKX-SPOT has `{cap}`. So the table parses VALID under R2 with no byte changed.
- Approved tables. R2 tightens the loader that re-parses every stored approval at every `load_context`
  (owner.py:960-961 calls `rules.approved_state`; rules.py:766-767 turns an `Invalid` into an invalid state). An
  approved table that broke R2 would therefore turn INVALID: new exposure blocked, and exits through the snapshot
  invalid too. No owner signature or table approval exists today (no `owner_pubkey.pem`; real-home `--check` exits
  3), so nothing changes in force now. Owner act 3 approves the table as Task 3 leaves it.
- The code hash. `core/compliance/rules.py` is in the D14 closure, so its hash moves. No `code_approved` exists yet,
  so there is nothing to re-sign. After owner act 2, every later change to it needs a fresh `code_approved`.
- Reason strings (exact; the row id follows `rules: row `):

| Rule | Reason |
|---|---|
| D15 content, financing | `rules: row <id>: match.financing: an allow, gated or grey row never matches ['credit'] (D15: no credit buying)` (the sorted hit list) |
| D15 content, action | `rules: row <id>: match.action: an allow, gated or grey row never matches ['borrow', 'lend'] (D15: no coin lending or borrowing)` |
| D15 label | `rules: row <id>: treatment: a D15 row is hard_block or out_of_scope (D15 only keeps credit and lending out)` |
| D16 content | `rules: row <id>: requires.live: a row matching ['etp_leveraged'] needs live broker evidence (D16)` (an ETP asset with no class axis lists `['etp_leveraged', 'etp_single_stock']`) |
| review_by | `rules: row <id>: review_by: 2026-10-22 is before the review of 2026-10-23` |
| max_leverage | `rules: row <id>: max_leverage: at most 10, got 10.5` |
| {cap} | `rules: row <id>: warning: only a grey row states a {cap}` |

- Fixture rule of the new tests: a row other than `_row()` itself gets its own id and `matrix_rows: []` and is
  passed after `_row()`, which covers the 38 matrix rows. A single `_row(**over)` override keeps id T-ALLOW and the
  full matrix.
- Every Edit below is an exact old/new pair quoted from the tree at `5816d3c` (equal to `995534b` outside docs/) with
  its anchor; the line numbers are those of that tree and only help find the anchor. Task 1 did not touch these
  three files. Before each Edit, re-read the file; if the old text is not found exactly once, apply the drift rule
  of Global Constraints.

- [ ] **Step 1: Write the failing tests**

  Six Edit-tool replacements: five in `tests/compliance_tables.py` and one in `tests/compliance_cli.py` (both LF,
  kept).

  Edit 1, `tests/compliance_tables.py`. Anchor: test_d16_rows_need_requires_live, the `"policy_ref": "D160"` line
  (tables:295). The first deliberate flip (R10): a gated etp_leveraged row citing D160 with no live evidence is D16 by
  content. Old text:

```python
    _parse(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}))   # not D16
```

  New text:

```python
    _bad(_row(), _row(**{**lev, "policy_ref": "D160"}, requires={"owner": ["kofia_leveraged_1h"]}),
         "row T-LEV: requires.live: a row matching ['etp_leveraged']")         # not D16 by label, D16 by content
    one_x = {**lev["match"], "class": ["etp_1x"]}                               # D160 is not D16, nor is etp_1x
    _parse(_row(), _row(**{**lev, "policy_ref": "D160", "match": one_x}, requires={"owner": ["kofia_leveraged_1h"]}))
```

  Edit 2, `tests/compliance_tables.py`. Anchor: the def line and first statement of test_requires_items_in_vocabulary
  (tables:302-303); the five new tests go right above it. Old text:

```python
def test_requires_items_in_vocabulary():
    _bad(_row(requires={"owner": ["age_19"]}), "row T-ALLOW: requires.owner", "'age_19' is outside")
```

  New text (the five loader tests, then the unchanged head of `test_requires_items_in_vocabulary`):

```python
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
```

  Edit 3, `tests/compliance_tables.py`. Anchor: test_warning_slots, its first loop (tables:316-317). The second
  deliberate flip (R10): `{cap}` leaves the allow-row loop. The `_bad` cases below the loop stay: `{cap!r}` and
  `{cap:>5}` still fail first in `_warning`. Old text:

```python
    for text in ("OKX is capped at {cap} of your equity.", "no slot at all", "literal {{cap}} braces", ""):
        assert _parse(_row(warning=text)).rows[0].warning == text
```

  New text:

```python
    for text in ("no slot at all", "literal {{cap}} braces", ""):    # {cap}: test_only_a_grey_row_states_a_cap
        assert _parse(_row(warning=text)).rows[0].warning == text
```

  Edit 4, `tests/compliance_tables.py`. Anchor: test_max_leverage, its last line (tables:413). `test_max_leverage`
  gains the bound cases. `1e6` is dumped as `1000000.0`, a decimal float the strict loader reads. Old text:

```python
    _bad(_row(max_leverage=10 ** 400), "rules: line ", "has more than 18 digits")      # Invalid, never OverflowError
```

  New text:

```python
    _bad(_row(max_leverage=10 ** 400), "rules: line ", "has more than 18 digits")      # Invalid, never OverflowError
    assert _parse(_row(max_leverage=10)).rows[0].max_leverage == 10.0                 # R2: 10 itself is legal
    for bad in (10.5, 11, 1e6):
        _bad(_row(max_leverage=bad), "row T-ALLOW: max_leverage: at most 10")
    assert _bad(_row(max_leverage=10.5)) == "rules: row T-ALLOW: max_leverage: at most 10, got 10.5"
```

  Edit 5, `tests/compliance_tables.py`. Anchor: the def line and first statement of
  test_shipped_okx_warning_has_only_the_cap_slot (tables:984-985); the pins and their test go right above it.
  `_T5_PINNED` was generated from the shipped table on 2026-10-24 and equals it, in table order. Its tuples keep the
  YAML order of `requires`. Of the two widenings ledger:113 names, the loader now refuses one (sell_short on
  KR-KIS-US-SHARE, D16 by content), and the pin catches the other (p2p_buy on KR-DOMESTIC-SPOT, which stays VALID
  under R2). Four pin controls follow: p2p_buy added (KR-DOMESTIC-SPOT), an owner requirement dropped
  (KR-KIS-US-OPTION), a row leaving the set (KR-KIS-ETP-1X turned hard_block) and a blocking row entering it
  (KR-KIS-CRYPTO-SPOT-ETP turned allow for cash, VALID under today's loader and under R2), so neither half of the
  symmetric difference in `_t5_pin_misses` goes unchecked. Each replaced byte string is checked to occur exactly once
  in the shipped bytes. Old text:

```python
def test_shipped_okx_warning_has_only_the_cap_slot():
    table, _, _ = _t5_shipped()
```

  New text:

```python
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
```

  Edit 6, `tests/compliance_cli.py`. Anchor: test_render_has_no_rule_free_text, the loop that rewrites every shipped
  row (cli:574-577). The third deliberate rewrite (R10). It passes under today's loader and keeps passing under R2.
  Old text:

```python
        if row.get("warning"):
            row["warning"] = UNIQUE + " {cap}"
```

  New text:

```python
        if row.get("warning"):
            row["warning"] = UNIQUE + (" {cap}" if row["treatment"] == "grey" else "")   # R2: {cap} is grey-only
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run it):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: eight tracebacks and these eight FAIL lines (the runner sorts by test name). Each is a case today's
  loader accepts:

```
FAIL compliance_tables/test_a_d15_row_is_blocking AssertionError: accepted; expected Invalid containing ('row T-D15: treatment: a D15 row is hard_block or out_of_scope',)
FAIL compliance_tables/test_d15_rows_never_let_credit_margin_lending_or_borrowing_through AssertionError: accepted; expected Invalid containing ('row T-ALLOW: match.financing: an allow, gated or grey row never matches',)
FAIL compliance_tables/test_d16_by_content_needs_requires_live AssertionError: accepted; expected Invalid containing ('row T-D16: requires.live: a row matching',)
FAIL compliance_tables/test_d16_rows_need_requires_live AssertionError: accepted; expected Invalid containing ("row T-LEV: requires.live: a row matching ['etp_leveraged']",)
FAIL compliance_tables/test_max_leverage AssertionError: accepted; expected Invalid containing ('row T-ALLOW: max_leverage: at most 10',)
FAIL compliance_tables/test_only_a_grey_row_states_a_cap AssertionError: accepted; expected Invalid containing ('row T-ALLOW: warning: only a grey row states a {cap}',)
FAIL compliance_tables/test_review_by_is_not_before_the_latest_review AssertionError: accepted; expected Invalid containing ()
FAIL compliance_tables/test_shipped_rows_that_can_let_through_are_pinned_exactly AssertionError: accepted; expected Invalid containing ("row KR-KIS-US-SHARE: requires.live: a row matching ['sell_short']",)
```

  The rest are 56 PASS lines (`test_warning_slots` among them) and
  `NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink` with its REFDATA reason. Then
  `56/65 passed, 8 failed, 1 not run` and exit code 1. With Windows Developer Mode on, the symlink test passes and
  the line reads `57/65 passed, 8 failed, 0 not run`. Before the pin test reaches its sell_short control, its four
  pin controls already pass, so the pins match the shipped table.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `35/35 passed, 0 failed, 0 not run` (exit code 0). The rewritten free-text test passes under
  today's loader.

- [ ] **Step 3: Implement**

  Five Edit-tool replacements in `core/compliance/rules.py` (LF, kept). Together they add 31 lines, none longer
  than 120 characters, and no banned word (the raw-text guard scans comments too).

  Edit 7. Anchor: the constants _BLOCKING and _MAX_REVIEW_DAYS above _match (rules.py:405-406). Old text:

```python
_BLOCKING = frozenset({"hard_block", "out_of_scope"})      # conduct rows are hard_block, so `any` is legal there
_MAX_REVIEW_DAYS = 31
```

  New text:

```python
_BLOCKING = frozenset({"hard_block", "out_of_scope"})      # conduct rows are hard_block, so `any` is legal there
_MAX_REVIEW_DAYS = 31
_MAX_LEVERAGE = 10.0                                       # R2: a typo cannot sign 1e6x
_D15_FINANCING = frozenset({"credit", "margin"})           # D15: no credit buying (margin included, ledger:131)
_D15_ACTIONS = frozenset({"lend", "borrow"})               # D15: no coin lending or borrowing
_D16_ACTIONS = frozenset({"sell_short"})                   # D16 by content (spec:70), whatever policy_ref says
_D16_CLASSES = frozenset({"etp_leveraged", "etp_single_stock", "krx_derivative", "elw"})
_D16_ASSETS = frozenset({"krx_derivative", "elw"})
```

  Edit 8. Anchor: _row, the axis check block `if treatment not in _BLOCKING:` (rules.py:454-459). D15 content goes
  right after the `missing` raise, inside the block that guarantees `match["financing"]` and `match["action"]` exist.
  Old text:

```python
    if treatment not in _BLOCKING:              # a missing key matches everything, so a row that can let an intent
        missing = sorted({"action", "financing"} - set(match)) + ([] if {"class", "asset"} & set(match)
                                                                  else ["class or asset"])   # through names each axis
        if missing:
            raise Invalid(f"{where}: match: an allow, gated or grey row names action, financing and a class or an "
                          f"asset; missing {missing}")
```

  New text:

```python
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
```

  Edit 9. Anchor: _row, the grey {cap} check and the `leverage =` line (rules.py:484-486). The slot set is computed
  once, `{cap}` outside grey is refused, and the `max_leverage` bound follows `_positive` (which already refuses 0,
  negatives, bools, NaN and inf). The bound's reason prints the value with `!r`, as `_positive`'s own reason does, so
  10.0000001 reads `got 10.0000001` (`:g` would print `got 10`), 11 reads `got 11.0` and 10.5 `got 10.5` (Appendix
  A section 4.2 check 3, amended 2026-10-25). Old text:

```python
    if treatment == "grey" and "cap" not in {slot for _, slot, _, _ in string.Formatter().parse(warning)}:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")
```

  New text:

```python
    slots = {slot for _, slot, _, _ in string.Formatter().parse(warning)}
    if treatment == "grey" and "cap" not in slots:
        raise Invalid(f"{where}: warning: a grey row states its {{cap}}")
    if treatment != "grey" and "cap" in slots:                               # the cap is a grey row's (ledger:146)
        raise Invalid(f"{where}: warning: only a grey row states a {{cap}}")
    leverage = 1.0 if item.get("max_leverage") is None else _positive(item["max_leverage"], f"{where}: max_leverage")
    if leverage > _MAX_LEVERAGE:
        raise Invalid(f"{where}: max_leverage: at most {_MAX_LEVERAGE:g}, got {leverage!r}")
```

  Edit 10. Anchor: _row, from `policy_ref = item.get("policy_ref")` through the gated-row raise (rules.py:487-494).
  The D15 label check follows the D16 label check inside the `policy_ref` block; D16 content follows the block and
  precedes the gated-row requirement. Old text:

```python
    policy_ref = item.get("policy_ref")
    if policy_ref is not None:
        if not isinstance(policy_ref, str) or not _POLICY.fullmatch(policy_ref):
            raise Invalid(f"{where}: policy_ref: expected 'D<n>' or 'D<n>, D<n>, ...', got {policy_ref!r}")
        if "D16" in policy_ref.split(", ") and not live:
            raise Invalid(f"{where}: requires.live: a D16 row needs live broker evidence (requires.live)")
    if treatment == "gated" and not (owner or live):                         # else it would act as an allow row
        raise Invalid(f"{where}: requires: a gated row requires owner or live evidence")
```

  New text:

```python
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
```

  Edit 11. Anchor: _row, `latest = max(r.date for r in reviews)` and the 31-day check (rules.py:523-525). Old text:

```python
    latest = max(r.date for r in reviews)
    if (review_by - latest).days > _MAX_REVIEW_DAYS:                         # P15: monthly
        raise Invalid(f"{where}: review_by: {review_by} is more than 31 days after the review of {latest}")
```

  New text:

```python
    latest = max(r.date for r in reviews)
    if review_by < latest:                                                   # a typo, never a schedule (ledger:103)
        raise Invalid(f"{where}: review_by: {review_by} is before the review of {latest}")
    if (review_by - latest).days > _MAX_REVIEW_DAYS:                         # P15: monthly
        raise Invalid(f"{where}: review_by: {review_by} is more than 31 days after the review of {latest}")
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 (PowerShell tool; it must print nothing) before each test command below (the
  module runs, the static-guard `-c` run and the suite run). All run from the repo root in Git Bash.

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected, ending: `64/65 passed, 0 failed, 1 not run` (exit code 0; the NOT_RUN is the REFDATA symlink test, and
  with Developer Mode on the line is `65/65 passed, 0 failed, 0 not run`).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected, ending: `35/35 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the gate and the store, which parse the shipped table through the fixtures and signed homes:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_gate/
```

  Expected, ending: `49/49 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/
```

  Expected, ending: `29/29 passed, 0 failed, 0 not run` (exit code 0).

  Overlap check, then the static guards, whose scans include the new rules.py text (comments too):

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected, ending: `16/16 passed, 0 failed, 0 not run` (exit code 0). A failure names the offending file and text:
  fix `rules.py`, never the guard.

  Overlap check, then the repo-wide read-only guards over `core/` (T-RO-01, test_08, test_09). This calls the three
  test functions directly, does not start `tests/run_all.py`, and writes nothing:

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as ro; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; ro(); t8(); t9(); print('guards ok')"
```

  Expected: `guards ok` (exit code 0).

  The shipped table is unchanged (a hash, not a test command, so no overlap check):

```bash
.venv/Scripts/python.exe -c "import hashlib; print(hashlib.sha256(open('core/compliance/kr_rules.yaml', 'rb').read()).hexdigest())"
```

  Expected: `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79`.

  Overlap check, then the compliance suite (it rewrites the tracked `qa/acceptance_results.json`, which is restored
  at once). Every `--suite` run first imports all ten suites (run_all.py:41-50), and the compliance tests alone took
  64 s in the 2026-10-24 record, against the Bash tool's 120 s default: give this line `timeout: 300000`; never
  start a second run meanwhile.

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `322/324 passed, 0 failed, 2 not run; ` followed by the path of `qa\acceptance_results.json`,
  then `exit 0` (with Developer Mode on: `324/324 passed, 0 failed, 0 not run`). Then:

```bash
git status --short
```

  Expected: exactly ` M core/compliance/rules.py`, ` M tests/compliance_cli.py` and ` M tests/compliance_tables.py`,
  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/rules.py tests/compliance_tables.py tests/compliance_cli.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (all three files are LF): `core/compliance/rules.py | 33`,
  `tests/compliance_cli.py | 2`, `tests/compliance_tables.py | 181`, each followed by its bar, and
  `3 files changed, 212 insertions(+), 4 deletions(-)`. If they differ, an edit converted line endings: run
  `git restore --staged <file>` then `git checkout -- <file>`, redo every Edit of that file with the Edit tool
  (Edits 1-5 for `tests/compliance_tables.py`, Edit 6 for `tests/compliance_cli.py`, Edits 7-11 for
  `core/compliance/rules.py`), then repeat Step 4 and this step. Then:

```bash
git commit -m "fix(compliance): loader refuses D15/D16 content, bounds review_by, max_leverage and {cap}; pin rows" -m "Task 2 (R2, R10): five checks in rules._row, three deliberate test rewrites (tables:295, :316, cli:576-577), five loader tests and the 15 exact row pins; kr_rules.yaml unchanged and VALID." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
