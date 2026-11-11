# Upbit KRW universe PR 1: compliance, pure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the pure `core/compliance` half of the Upbit KRW universe: the signed `universe_rule` parser and its sha256, the five flag classes, the exact request set, medians with finality from content, the snapshot file format with its encode helper and verification into a `Universe`, and the snapshot paths, plus the research note that records the rule's source URL.

**Architecture:** Everything lives in the three existing compliance modules the interface contract names. `rules.py` gets the rule dataclass, its strict sub-parser inside `_venue`, and one new section of pure functions over plain data (bytes and dicts, stdlib `json`, `Decimal`); `model.py` gets the frozen `Universe` record; `owner.py` gets two path functions that create nothing. No clock, no file, no network: the PR 2 builder supplies receipts and the PR 2 writer writes the bytes this code returns.

**Tech Stack:** Python 3.13 (venv at `TRADEGEN_PR9/.venv`, read-only), stdlib `json`, `hashlib`, `base64`, `decimal`, `datetime`, `dataclasses`, `re`; the repo's own test runner (`tests/run_all.py`, no pytest).

**Spec:** [2026-11-11-upbit-krw-universe-design.md](../specs/2026-11-11-upbit-krw-universe-design.md) (sections 4, 5 and 19 item 1). Index and interface contract: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md).

## Global Constraints

All constraints in the index apply: [2026-11-11-upbit-krw-universe-index.md](2026-11-11-upbit-krw-universe-index.md), "Global constraints". The ones this PR touches most, and this PR's own constraints copied verbatim from the spec:

- Index: "`core/compliance` imports only stdlib, `yaml`, `cryptography`, `core.isolation` and `core.compliance` (`tests/compliance_guards.py:190-193`)."
- Index: "`core/compliance/kr_rules.yaml`, `instruments.yaml` and `core/odds/venues.yaml` are not edited by these PRs; the owner adds `universe_rule` to `venues.yaml` and signs it after code-approve (spec section 16)."
- Index: "Line endings are byte-exact (`.gitattributes` is `* -text`). Python and YAML files are LF; `docs/superpowers` specs and plans are CRLF. Never `sed -i`. Before each commit, `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`." Research notes are LF too (`upbit_order_terms.md` is). Edit with the Edit or Write tool only.
- Index: "Tests are offline: fake `transport._send` seams and fixtures, all KEYLESS inputs, temporary state. Never call a real exchange, never read `.env`, never write the real `~/.tradegen` or `~/.nextgen`."
- Index: "The repository is public: no secrets, amounts, account data or personal data in code, tests, docs or PR text."
- Spec 4: "Fixed in code: KRW quote only, and the base symbol must match `[A-Z][A-Z0-9]{0,11}` (the strictest pattern already used by the collector, risk and continuous code)."
- Spec 4, flag classes, "one test used everywhere (snapshot, per-slot read, chooser, study)":
  - "`unflagged`: the market is present, `market_event.warning` is present and exactly `false`, all five known caution keys are present and exactly `false`, and no other caution key is `true`;"
  - "`warning`: present, and `warning` is exactly `true`;"
  - "`caution`: present, `warning` exactly `false`, and any caution key `true` (an unknown key included);"
  - "`unknown`: present, but `market_event` is missing or malformed, or `warning` or a known caution key is missing or not a boolean;"
  - "`absent`: not in the read."
  - "Only `unflagged` coins can be bought or enter the snapshot's eligible set."
- Spec 4: "Parser: add `universe_rule` to `_VENUE_OPTIONAL` with a strict sub-parser (known keys only; `quote` must be a settlement asset of the venue; `exclude` entries pass the symbol check; integers positive). Add `Venue.universe_rule: UniverseRule | None = None`."
- Spec 4: "`rule_sha256` is the sha256 of the canonical JSON of the parsed rule, so unrelated edits to `venues.yaml` do not invalidate snapshots."
- Spec 4: "The `source` URL is first recorded in a research note under `research_notes/`, because `tests/compliance_tables.py:1544-1553` refuses any `venues.yaml` URL that is missing from the research corpus."
- Spec 5, Requests, for candle day D (UTC): "1. One `GET /v1/market/all?is_details=true`. `listed` = every KRW market in it. 2. Filters with no further request: symbol pattern, `exclude`, flag class `unflagged`. 3. For each remaining market, two candle reads: age: `GET /v1/candles/days?market=X&to=<D - min_listing_days, 00:00 UTC>&count=1`. `to` is exclusive, so a returned candle is dated at least `min_listing_days + 1` days before D. Old enough iff one comes back. value: `GET /v1/candles/days?market=X&to=<D, 00:00 UTC>&count=<median_days>`. This excludes day D by construction. The median is taken over the calendar days D-30 to D-1, and a day with no candle counts as zero. 4. `eligible` = the markets that pass every test, each with its median daily value."
- Spec 5: "**Finality from content.** The build refuses unless no returned candle is dated D or later and the `market/all` server time is at or after D 00:00 UTC. `built_at` is the latest receipt server time and must be at or after D 00:10 UTC."
- Spec 5: "A snapshot file holds the canonical JSON of the rule it was built under, the receipts, and a manifest sha256. Each receipt has the 7 keys of `live_history`'s receipt shape: `path`, `params` (list of `[k, v]`), `account_scope`, `received_at`, `server_time`, `raw_body_b64`, `sha256`."
- Spec 5: "`rules.universe_eligible(rule, receipts)` parses the bodies itself (stdlib `json`) and returns `listed` and `eligible` with medians. It checks every receipt hash and that the set of `(path, params)` is exactly the set of requests the rule implies for that `market/all` body, so a snapshot cannot add, drop or swap receipts." (The index contract adds a `day` argument; this plan follows the contract.)
- Spec 5: "`rules.verify_universe_snapshot(raw_bytes, rule_sha256)` is pure and never calls `load_context`. It checks the manifest, the embedded rule's sha256 against the given one, recomputes `universe_eligible`, and returns a `Universe(day, rule_sha256, snapshot_sha256, built_at, valid_from, valid_until, listed, eligible)`."
- Spec 5: "A pure encode helper returns the canonical file bytes and the manifest sha256. The universe code in `core/compliance` writes no files; only `execution_launch/universe_store.py` writes the snapshot."
- Spec 5: "**In force.** `valid_from = max(built_at, D 00:40 UTC)` and `valid_until = D+1 00:40 UTC` (09:40 KST)."
- Spec 5: "Write-once and content-addressed: `owner.universe_path(D, sha256)` next to `owner.evidence_path()`."
- Never write the uppercase word that starts with `CANO` in a `core/compliance` file: `tests/compliance_guards.py:31` (`RAW_CS`) bans that substring case-sensitively. Lowercase "canonical" is fine.
- No new module-level def or class in `rules.py` may be named `quote`, `name`, `start`, `rows`, `book`, `steps`, `symbol`, `get` or `lot`: `test_venue_odds_lookups_are_pure_tuple_lookups` (`tests/compliance_tables.py:947-966`) refuses a Venue method that names a module-level def.
- No clock call (`datetime.now`, `date.today`, any `time.*`) anywhere in the new code (`tests/compliance_guards.py:408-426`).

**Deviations from the index's interface contract** (later plans build on these; each is compatible with the keyword calls PR 2, PR 3, PR 4a and PR 4d already write):

- `UniverseRule` and `model.Universe` are `@dataclass(frozen=True, kw_only=True)` (the index writes `frozen=True` only), like every other record in these two modules. Build them with keywords.
- `UniverseRule.__post_init__` stores `exclude` as a sorted tuple, whatever order or sequence type the caller passes, so one rule has one form and one `universe_rule_sha256`. A rule built directly (PR 2's test fixture passes `exclude=("USDT", "USDC")`) hashes and encodes exactly like the parsed one.
- The sub-parser adds bounds the spec leaves open: `min_listing_days` 1..3650 (the age read's `to` stays a real date), `median_days` 1..200 (one candles/days read), `min_median_value_krw` >= 1. `quote` must be exactly `KRW` and a settlement asset; a `universe_rule` on any venue but upbit is `Invalid`.
- `listed` holds only the KRW markets that match `UNIVERSE_MARKET` (so `KRW-1INCH` is left out), the same set `market_flags` returns; PR 2's helpers refuse any other symbol anyway. `market_flags` also refuses a body that names one market twice.
- `universe_eligible(rule, receipts, day)` takes `day`, as the index says (spec section 5 writes `universe_eligible(rule, receipts)`).
- Receipt stamps must be `YYYY-MM-DDTHH:MM:SS.ffffffZ` (the form `execution_control.store._utc` writes and `live_history` stores), and `raw_body_b64` must be the one standard base64 text of the body.
- Snapshot file: `_universe_json({"day", "rule", "receipts", "manifest_sha256"})`, compact sorted-key ASCII JSON; the manifest is the sha256 of the same JSON without `manifest_sha256`, and `snapshot_sha256` is that manifest, which is also the file name.
- A caller's mistake (not a `UniverseRule` the parser would build, not a `date`, a bad `n`) raises plain `ValueError`. A file that is not the snapshot's JSON form is `UNIVERSE_MANIFEST_MISMATCH`; an embedded rule the parser refuses, or one not in parsed form, is `UNIVERSE_RULE_INVALID`.
- `Venue.universe_rule` defaults to `None`, but `model.jsonable` writes a `None` field as `null`, so every `ctx_hash` and `decision_id` changes value once with this PR. The index's "left out of its canonical encoding when `None`" rule is for persisted digests (profiles, protocols, programs, sessions); `ctx_hash` and `decision_id` are only ever recomputed in-process (`execution_control/session.py:158`, `execution_launch/profile.py:413-414`, `execution_launch/review_auth.py:159-160`, `execution_accounts/readiness.py:242-244`) and no test pins a value. `state_hash` (the file hashes and seq) and every odds `plan_hash` are unchanged.
- Flag reading where spec section 4's classes overlap: a `warning` that is exactly `true` gives `warning` even when `caution` is malformed (the held coin is sold, never kept as `unknown`); a missing or non-boolean known caution key gives `unknown` even when another caution key is `true`; an unknown caution key whose value is not a boolean is ignored (only an unknown key that is `true` makes `caution`).

**Running tests.** The repo has no pytest. In every shell, define this once (copied from the index):

```bash
PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
export TRADEGEN_RUNS_DIR="${SCRATCH:?set SCRATCH to your session scratchpad directory}/runs_scratch"
focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
```

`focus compliance compliance_tables/test_universe_rule` runs every compliance test whose name contains that text. Each printed row is `PASS <name>` or `FAIL <name> <ExceptionType>: <message>`; the exit code is 0 only when at least one row ran and none failed.

**Two tests depend on where the checkout is.** `compliance_guards/test_cryptography_is_pinned_installed_and_usable` (`tests/compliance_guards.py:583-584`) and `compliance_signer/test_commands_sign_exactly_what_was_shown` (`tests/compliance_signer.py:950`) require the interpreter to be the checkout's own `.venv`. They pass in `TRADEGEN_PR9` itself; in any other checkout (a fresh clone or worktree run with `TRADEGEN_PR9/.venv`) they fail on unmodified fd85850 with `cryptography loaded from ...TRADEGEN_PR9\.venv\..., not .venv` and `run the suite with .venv/Scripts/python.exe`. Before Task 1, run `focus compliance compliance_` once on the new branch and note which of these two fail. Wherever a step below expects "only PASS rows", those two noted rows, failing with exactly those messages, are the only allowed exception (`focus` then exits 1 for that reason alone); any other FAIL row stops the task.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `core/compliance/rules.py` | Modify | `UniverseRule`, `Venue.universe_rule` and its strict sub-parser; one new "Upbit KRW universe" section: rule sha256, flag classes, request set, receipt and candle checks, medians, snapshot encode and verify, top N. |
| `core/compliance/model.py` | Modify | The frozen `Universe` record. |
| `core/compliance/owner.py` | Modify | `universe_dir` and `universe_path` under the state root, creating nothing. |
| `research_notes/Korean resident trading venue legality/upbit_market_list.md` | Create | Records the rule's source URL and the flag fields, so a later `venues.yaml` may cite the URL. |
| `tests/compliance_tables.py` | Modify (append) | Rule parsing, value checks, rule sha256, research URL. |
| `tests/compliance_universe.py` | Create | Flag classes, request set, finality, medians, receipts, snapshot file, `Universe`, top N, no file access. |
| `tests/compliance_acceptance.py` | Modify | Registers `compliance_universe` in `MODULES`. |
| `tests/compliance_owner.py` | Modify (append) | The universe paths. |

Not touched: `core/odds/venues.yaml`, `core/compliance/kr_rules.yaml`, `core/compliance/instruments.yaml`, `core/compliance/gate.py`, every `execution*` package.

Spec section 19 snapshot tests that belong to later PRs: a failed request and a rebuild that leaves earlier files intact (PR 2, the builder and writer); the recompute in `load_context`, the 09:40 KST switch between two days' snapshots, and the read-back that raises `TypeError` (PR 3). This PR tests the in-force window values `verify_universe_snapshot` returns.

Line numbers in the **Files** blocks are those of fd85850. Later tasks edit files that earlier tasks already changed, so every edit is anchored on the quoted text, which stays unique; use the Edit tool with that text.

---

### Task 1: Rule parser, rule sha256 and research note

**Files:**
- Modify: `core/compliance/rules.py:9-20` (imports), `:306-307` (insert `UniverseRule` before `Venue`), `:322` (new `Venue` field), `:698-699` (`_VENUE_OPTIONAL`), `:789-790` (insert the sub-parser before `_venue` at 791), `:854-856` (`_venue`'s return), after `:930` (new section after `approved_state`, before the `--check` banner at 933)
- Create: `research_notes/Korean resident trading venue legality/upbit_market_list.md`
- Test: `tests/compliance_tables.py` (append after line 1624)

**Interfaces:**
- Consumes: `rules.Invalid`, `rules._keys(doc, where, required, optional=frozenset())`, `rules._text(value, where) -> str`, `rules._strs(value, where, vocab=None, *, empty=False) -> tuple[str, ...]`, `rules.approved_state(...)`; test helpers `_DROP`, `_dump`, `_refused(call, *has)`, `_row`, `_table`, `_map_doc`, `_venues_doc`, `_facts(vdoc=None, mdoc=None)`, `_need_model`, `_T5_REPO`, `_T5_RESEARCH_DIRS`, `_t5_re`.
- Produces:
  - `@dataclass(frozen=True, kw_only=True) class UniverseRule: source: str; quote: str; exclude: tuple[str, ...]; min_listing_days: int; median_days: int; min_median_value_krw: int`; `__post_init__` stores `exclude` as a sorted tuple, so a directly built rule equals the parsed one.
  - `Venue.universe_rule: UniverseRule | None = None`; `"universe_rule"` in `_VENUE_OPTIONAL`.
  - `_universe_rule(value, where: str, settlement) -> UniverseRule` (raises `Invalid`), `_count(value, where, most=None) -> int`.
  - `_rule_body(rule: UniverseRule) -> dict`, `_universe_json(value) -> bytes`, `universe_rule_sha256(rule: UniverseRule) -> str`.

- [ ] **Step 1: Cut the branch**

```bash
git fetch origin
git switch -c claude/universe-pr1-compliance-pure origin/main
git log --oneline -1
git status --short
focus compliance compliance_ | grep '^FAIL '
```

Expected: `git log` shows `fd85850` (or a later `main` commit if the owner merged PR 0 first); `git status` lists only the untracked `docs/superpowers` spec and plan files, which this plan never commits. The `grep` prints nothing, or only the two checkout-location rows named under "Running tests"; note them. Any other FAIL row on unmodified `main` stops the plan: report it.

- [ ] **Step 2: Write the failing tests**

Append to the end of `tests/compliance_tables.py` (after line 1624; keep LF line endings):

```python


# --------------------------------------------------------------------------- #
# Upbit KRW universe PR 1, Task 1 (universe spec section 4): the optional universe_rule of the upbit venue, its
# strict sub-parser, its sha256, and the research note that records its source URL.
# --------------------------------------------------------------------------- #
_U1_SOURCE = "https://docs.upbit.com/kr/reference/list-trading-pairs"
_U1_NOTE = _T5_REPO / "research_notes" / "Korean resident trading venue legality" / "upbit_market_list.md"
_U1_CAUTIONS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING", "GLOBAL_PRICE_DIFFERENCES",
                "CONCENTRATION_OF_SMALL_ACCOUNTS")


def _u1_rule_doc(**over) -> dict:
    """The spec section 4 rule with its proposed defaults; an override of _DROP deletes the key."""
    doc = {"source": _U1_SOURCE, "quote": "KRW", "exclude": ["USDT", "USDC"], "min_listing_days": 250,
           "median_days": 30, "min_median_value_krw": 1000000000}
    doc.update(over)
    return {k: v for k, v in doc.items() if v is not _DROP}


def _u1_venues(rule=None, **upbit) -> dict:
    """_venues_doc() with `rule` as the upbit universe_rule (left out when None) and other upbit keys overridden."""
    doc = _venues_doc()
    if rule is not None:
        doc["venues"]["upbit"]["universe_rule"] = rule
    doc["venues"]["upbit"].update(upbit)
    return doc


def _u1_rule(doc=None) -> rules.UniverseRule:
    return _facts(_u1_venues(_u1_rule_doc() if doc is None else doc)).venues["upbit"].universe_rule


def test_universe_rule_parses_into_the_upbit_venue():
    rule = _u1_rule()
    assert rule == rules.UniverseRule(source=_U1_SOURCE, quote="KRW", exclude=("USDC", "USDT"), min_listing_days=250,
                                      median_days=30, min_median_value_krw=1000000000), rule
    assert type(rule.exclude) is tuple                                   # sorted and hashable
    direct = rules.UniverseRule(source=_U1_SOURCE, quote="KRW", exclude=["USDT", "USDC"], min_listing_days=250,
                                median_days=30, min_median_value_krw=1000000000)
    assert direct == rule and direct.exclude == ("USDC", "USDT"), direct   # any input order: stored sorted
    with_rule, without = _facts(_u1_venues(_u1_rule_doc())), _facts()
    assert without.venues["upbit"].universe_rule is None                 # the key stays optional
    assert all(v.universe_rule is None for v in with_rule.venues.values() if v.id != "upbit")
    assert with_rule.venues["kis"] == without.venues["kis"] and with_rule.venues["okx"] == without.venues["okx"]
    assert with_rule.venues["upbit"].markets == without.venues["upbit"].markets      # markets keeps today's pin
    assert rules.Venue(id="x", sections=(), settlement=frozenset(), markets=frozenset()).universe_rule is None
    assert "universe_rule" in rules._VENUE_OPTIONAL
    try:
        rule.median_days = 1
    except AttributeError:                                               # dataclasses.FrozenInstanceError
        pass
    else:
        raise AssertionError("UniverseRule is not frozen")


def test_universe_rule_keeps_the_venue_parser_closed():
    """Today's closed-key failure stays for every other key, and universe_rule is itself a closed mapping."""
    where = "venues: upbit: universe_rule"
    _refused(lambda: _facts(_u1_venues(universe_rules=_u1_rule_doc())),
             "venues: upbit: unknown key(s) ['universe_rules']")
    _refused(lambda: _facts(_u1_venues(_u1_rule_doc(extra=1))), f"{where}: unknown key(s) ['extra']")
    _refused(lambda: _facts(_u1_venues(_u1_rule_doc(median_days=_DROP))), f"{where}: missing key(s) ['median_days']")
    for bad in ([], "KRW", 1):
        _refused(lambda: _facts(_u1_venues(bad)), f"{where}: expected a mapping")
    nulled = _venues_doc()
    nulled["venues"]["upbit"]["universe_rule"] = None
    _refused(lambda: _facts(nulled), f"{where}: expected a mapping")
    okx = _venues_doc()
    okx["venues"]["okx"]["universe_rule"] = _u1_rule_doc()
    _refused(lambda: _facts(okx), "venues: okx: universe_rule: only upbit carries a universe rule")
    _need_model()
    good_rules, good_map = _table(_row()), _dump(_map_doc())
    for doc in (_u1_venues(_u1_rule_doc(extra=1)), nulled, okx):
        state = rules.approved_state(good_rules, good_map, _dump(doc), seq=1)
        assert state.valid is False and "universe_rule" in state.reason, state.reason
    assert rules.approved_state(good_rules, good_map, _dump(_u1_venues(_u1_rule_doc())), seq=1).valid


def test_universe_rule_values_are_checked():
    where = "venues: upbit: universe_rule"

    def bad(has: str, **over) -> None:
        _refused(lambda: _u1_rule(_u1_rule_doc(**over)), f"{where}: {has}")

    for source in (" ", None, 1):
        bad("source: expected a non-empty string", source=source)
    for quote in ("USDT", None, "krw"):
        bad(f"quote: only KRW, a settlement asset of this venue, is supported; got {quote!r}", quote=quote)
    usdt = _u1_venues(_u1_rule_doc(), settlement=["USDT"], markets=[["BTC", "USDT"]], default_quote="USDT")
    _refused(lambda: _facts(usdt), f"{where}: quote: only KRW, a settlement asset of this venue, is supported; got 'KRW'")
    for base in ("usdt", "KRW-USDT", "A" * 13, "1INCH", " USDT"):
        bad(f"exclude: {base!r} is not a base symbol (A-Z, then at most 11 of A-Z or 0-9)", exclude=[base])
    bad("exclude: '' is not a non-empty string", exclude=[""])
    bad("exclude: 1 is not a non-empty string", exclude=[1])
    bad("exclude: an item is repeated", exclude=["USDT", "USDT"])
    bad("exclude: expected a list", exclude="USDT")
    for key, most in (("min_listing_days", 3650), ("median_days", 200)):
        for value in (0, -1, most + 1, True, 30.0, "30", None):
            bad(f"{key}: expected an int in 1..{most}, got {value!r}", **{key: value})
    for value in (0, -1, True, 1e9, "1000000000", None):
        bad(f"min_median_value_krw: expected an int >= 1, got {value!r}", min_median_value_krw=value)
    for empty in ([], None):
        assert _u1_rule(_u1_rule_doc(exclude=empty)).exclude == ()
    edge = _u1_rule(_u1_rule_doc(exclude=["B", "ABCDEFGHIJKL"], min_listing_days=3650, median_days=200,
                                 min_median_value_krw=1))
    assert (edge.exclude, edge.min_listing_days, edge.median_days, edge.min_median_value_krw) == (
        ("ABCDEFGHIJKL", "B"), 3650, 200, 1), edge


def test_universe_rule_sha256_is_the_rule_alone():
    """Spec section 4: the sha256 of the parsed rule's JSON, so unrelated venues.yaml edits leave it alone."""
    text = (b'{"exclude":["USDC","USDT"],"median_days":30,"min_listing_days":250,"min_median_value_krw":1000000000,'
            b'"quote":"KRW","source":"https://docs.upbit.com/kr/reference/list-trading-pairs"}')
    sha = rules.universe_rule_sha256(_u1_rule())
    assert sha == hashlib.sha256(text).hexdigest(), sha
    direct = rules.UniverseRule(source=_U1_SOURCE, quote="KRW", exclude=("USDT", "USDC"), min_listing_days=250,
                                median_days=30, min_median_value_krw=1000000000)
    assert rules.universe_rule_sha256(direct) == sha                   # a rule built in code hashes like the parsed one
    kis = _u1_venues(_u1_rule_doc())
    kis["venues"]["kis"]["source"] = "https://example.invalid/kis2"
    for doc in (_u1_venues(_u1_rule_doc(exclude=["USDC", "USDT"])),                   # another order, the same set
                _u1_venues(_u1_rule_doc(), source="https://example.invalid/upbit2"),    # the venue's own source
                kis):                                                                  # another venue
        assert rules.universe_rule_sha256(_facts(doc).venues["upbit"].universe_rule) == sha
    for key, value in (("source", "https://example.invalid/rule"), ("exclude", ["USDT"]), ("min_listing_days", 251),
                       ("median_days", 29), ("min_median_value_krw", 999999999)):
        assert rules.universe_rule_sha256(_u1_rule(_u1_rule_doc(**{key: value}))) != sha, key


def test_universe_rule_source_is_in_the_research():
    """Spec section 4: the rule's source URL is in the research corpus before venues.yaml may cite it (the check of
    test_shipped_urls_come_from_the_research), and the note records the flag fields the classes read."""
    corpus = b"\n".join(p.read_bytes() for d in _T5_RESEARCH_DIRS for p in sorted((_T5_REPO / d).rglob("*.md")))
    known = {u.rstrip(b".,;*") for u in _t5_re.findall(rb"https://[^\s)\]>\"'`|]+", corpus)}
    assert _U1_SOURCE.encode("ascii") in known
    raw = _U1_NOTE.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n"), "LF only, like the other research notes"
    note = raw.decode("utf-8")
    for needle in (_U1_SOURCE, "is_details=true", "`market_event.warning`", "10 calls per second",
                   *(f"`{key}`" for key in _U1_CAUTIONS)):
        assert needle in note, needle
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `focus compliance compliance_tables/test_universe_rule`
Expected: exit 1 with five FAIL rows. `test_universe_rule_parses_into_the_upbit_venue` fails with today's closed-key failure, `Invalid: venues: upbit: unknown key(s) ['universe_rule']`; the closed-parser and values tests fail with `AssertionError` (the reason is that same message, not the expected one); `test_universe_rule_sha256_is_the_rule_alone` fails with `AttributeError: module 'core.compliance.rules' has no attribute 'universe_rule_sha256'`; the research test fails with `AssertionError` (the URL is not in the corpus yet).

- [ ] **Step 4: Write the implementation in `core/compliance/rules.py`**

4a. Imports (lines 9-20). Replace lines 9-11:

```python
import codecs
import hashlib
import math
```

with:

```python
import codecs
import hashlib
import json
import math
```

and replace line 16, `from dataclasses import dataclass`, with:

```python
from dataclasses import asdict, dataclass
```

4b. Insert before the `Venue` dataclass (before line 306, `@dataclass(frozen=True, kw_only=True)`, which is followed by line 307, `class Venue:`):

```python
@dataclass(frozen=True, kw_only=True)
class UniverseRule:
    """The signed Upbit KRW eligibility rule (universe spec section 4); universe_rule_sha256() is its hash."""
    source: str
    quote: str                                           # "KRW": a settlement asset of the venue
    exclude: tuple[str, ...]                             # base symbols, sorted
    min_listing_days: int                                # 1 .. _MAX_LISTING_DAYS
    median_days: int                                     # 1 .. _MAX_CANDLES (one candle read)
    min_median_value_krw: int                            # >= 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "exclude", tuple(sorted(self.exclude)))   # one rule, one form, one sha256


```

4c. Replace line 322:

```python
    odds_sources: tuple[tuple[str, str], ...] = ()       # (odds key, its source) for each odds key present
```

with:

```python
    odds_sources: tuple[tuple[str, str], ...] = ()       # (odds key, its source) for each odds key present
    universe_rule: UniverseRule | None = None            # upbit only (universe spec section 4); None when absent
```

4d. Replace lines 698-699:

```python
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits",
                             "lot", "min_order", "fee_extras", "tick_ladder"})      # the odds keys (odds plan Q17)
```

with:

```python
_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits",
                             "lot", "min_order", "fee_extras", "tick_ladder",       # the odds keys (odds plan Q17)
                             "universe_rule"})                                      # universe spec section 4
```

4e. Insert between `_odds_ladder` (ends at line 788) and `def _venue(` (line 791), keeping two blank lines on each side:

```python
_UNIVERSE_RULE_KEYS = frozenset({"source", "quote", "exclude", "min_listing_days", "median_days",
                                 "min_median_value_krw"})
_UNIVERSE_BASE = re.compile(r"[A-Z][A-Z0-9]{0,11}")      # the base of KRW-<base> (universe spec section 4)
_MAX_LISTING_DAYS = 3650                                  # keeps the age read's `to` a real, sane date
_MAX_CANDLES = 200                                        # one candles/days read returns at most 200 days


def _count(value, where: str, most: int | None = None) -> int:
    """A positive int (bool refused), at most `most` when given."""
    if type(value) is not int or value < 1 or (most is not None and value > most):
        raise Invalid(f"{where}: expected an int in 1..{most}, got {value!r}" if most is not None
                      else f"{where}: expected an int >= 1, got {value!r}")
    return value


def _universe_rule(value, where: str, settlement) -> UniverseRule:
    """The strict `universe_rule` sub-parser (universe spec section 4): known keys only, the KRW quote, base symbols
    in `exclude` (UniverseRule stores them sorted), bounded positive integers."""
    _keys(value, where, _UNIVERSE_RULE_KEYS)
    quote = value["quote"]
    if quote != "KRW" or quote not in settlement:
        raise Invalid(f"{where}: quote: only KRW, a settlement asset of this venue, is supported; got {quote!r}")
    exclude = _strs(value["exclude"], f"{where}: exclude", empty=True)
    for base in exclude:
        if not _UNIVERSE_BASE.fullmatch(base):
            raise Invalid(f"{where}: exclude: {base!r} is not a base symbol (A-Z, then at most 11 of A-Z or 0-9)")
    return UniverseRule(source=_text(value["source"], f"{where}: source"), quote=quote, exclude=exclude,
                        min_listing_days=_count(value["min_listing_days"], f"{where}: min_listing_days",
                                                _MAX_LISTING_DAYS),
                        median_days=_count(value["median_days"], f"{where}: median_days", _MAX_CANDLES),
                        min_median_value_krw=_count(value["min_median_value_krw"], f"{where}: min_median_value_krw"))
```

4f. Replace `_venue`'s return, lines 854-856:

```python
    return Venue(id=vid, sections=sections, settlement=settlement, markets=frozenset(markets),
                 quote_by_currency=bool(by_currency), default_quote=default, deposits=frozenset(deposits),
                 odds_sources=tuple(sorted((key, entry[key]["source"]) for key in odds)), **odds)
```

with:

```python
    universe = None
    if "universe_rule" in entry:
        if vid != "upbit":
            raise Invalid(f"{where}: universe_rule: only upbit carries a universe rule")
        universe = _universe_rule(entry["universe_rule"], f"{where}: universe_rule", settlement)
    return Venue(id=vid, sections=sections, settlement=settlement, markets=frozenset(markets),
                 quote_by_currency=bool(by_currency), default_quote=default, deposits=frozenset(deposits),
                 odds_sources=tuple(sorted((key, entry[key]["source"]) for key in odds)), universe_rule=universe,
                 **odds)
```

4g. Insert after `approved_state` (its last line is 930, `        return ApprovedState.invalid(f"internal error {type(exc).__name__}")`) and before the `--check` banner (line 933), keeping two blank lines on each side. Tasks 2 to 4 append to the end of this section, so it always ends just before that banner:

```python
# --------------------------------------------------------------------------- #
# Upbit KRW universe (universe spec sections 4 and 5): the rule hash, the flag classes, the request set, the medians
# and the daily snapshot, all over plain data. Pure: no clock, no file, no network, no context.
# --------------------------------------------------------------------------- #
def _rule_body(rule: UniverseRule) -> dict:
    """The rule's six fields as JSON data, `exclude` as a list."""
    return {**asdict(rule), "exclude": list(rule.exclude)}


def _universe_json(value) -> bytes:
    """The one JSON form of the universe code: sorted keys, no spaces, ASCII, no NaN."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def universe_rule_sha256(rule: UniverseRule) -> str:
    """sha256 hex of the rule's own JSON (universe spec section 4), so unrelated venues.yaml edits leave it alone."""
    return hashlib.sha256(_universe_json(_rule_body(rule))).hexdigest()
```

- [ ] **Step 5: Write the research note**

Create `research_notes/Korean resident trading venue legality/upbit_market_list.md` with LF line endings and exactly this content:

```markdown
# Upbit KRW market list and flags for the universe rule

Recorded on 2026-11-11 (KST) for the optional `universe_rule` key of the upbit entry in `core/odds/venues.yaml` (Upbit KRW universe design, `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 2 and 4). The design checked Upbit's public developer docs on 2026-11-11; this note records the facts the rule rests on, with their source. No API call was made.

| Fact | What the page says | Where TRADEGEN uses it | Source |
|---|---|---|---|
| Market list | `GET /v1/market/all` lists every trading pair. With `is_details=true`, each market object also carries `market_event`. | The daily snapshot's first read. `listed` is every `KRW-<base>` market in it whose base matches `[A-Z][A-Z0-9]{0,11}`. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Warning flag | `market_event.warning` is a boolean: the market is designated for investment warning. | Flag class `warning`: a held coin is sold and the coin is never bought. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Caution flags | `market_event.caution` holds five booleans: `PRICE_FLUCTUATIONS`, `TRADING_VOLUME_SOARING`, `DEPOSIT_AMOUNT_SOARING`, `GLOBAL_PRICE_DIFFERENCES`, `CONCENTRATION_OF_SMALL_ACCOUNTS`. | Flag class `caution`: a held coin is kept as the strategy decides, and the coin is not bought while any caution key is true. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Rate limit | The market group allows 10 calls per second per IP. | The transport's 0.2-second pacing keeps the daily build under it. | https://docs.upbit.com/kr/reference/list-trading-pairs |

Limits of this record:

- No API field announces a scheduled end of trading support, so a delisting is not seen before the market leaves the list; its flag class is then `absent`.
- A missing or non-boolean `warning` or known caution key gives the class `unknown`, never `unflagged`, so a changed response shape blocks buys instead of allowing them. An unknown caution key that is `true` gives `caution`.
- The daily candle facts the age and value reads rest on (candles close at 00:00 UTC, `to` is exclusive, a day with no trade may have no candle) come from the design, sections 2 and 5, not from this page. Section 17 of the design measures the zero-trade case before any freeze.
- The owner confirms the rule values when signing `approved {kind: venues}`.
```

- [ ] **Step 6: Run the tests to see them pass**

```bash
focus compliance compliance_tables/test_universe_rule
focus compliance compliance_tables/
focus compliance compliance_gate/test_gate_call_graph_has_no_clock_zone_file_or_socket
focus compliance compliance_gate/test_purity_no_file_clock_zone_or_network
focus compliance compliance_guards/
```

Expected: every command exits 0 with only PASS rows (`compliance_tables/` keeps its 70 earlier tests passing, `test_shipped_urls_come_from_the_research` and `test_venue_odds_lookups_are_pure_tuple_lookups` included).

- [ ] **Step 7: Commit**

```bash
git add core/compliance/rules.py tests/compliance_tables.py "research_notes/Korean resident trading venue legality/upbit_market_list.md"
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -F - <<'EOF'
Parse the signed Upbit universe rule on the venue facts

Adds the optional universe_rule key of the upbit venue (universe spec section 4): UniverseRule,
Venue.universe_rule, a strict sub-parser (known keys, KRW quote, base symbols, bounded positive
integers) and universe_rule_sha256 over the rule alone, plus the research note that records the
rule's source URL. core/odds/venues.yaml is unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: the two `--stat` outputs are identical (three files).

---

### Task 2: Flag classes and the market list reader

**Files:**
- Modify: `core/compliance/rules.py:17` (the import `from datetime import date`, line 18 after Task 1 added `import json`; add the `decimal` import after it) and the end of the universe section added in Task 1 (after `universe_rule_sha256`, before the `--check` banner)
- Modify: `tests/compliance_acceptance.py:25-27` (`MODULES`)
- Create: `tests/compliance_universe.py`
- Test: `tests/compliance_universe.py`

**Interfaces:**
- Consumes: `rules._universe_json` (Task 1).
- Produces:
  - `class UniverseError(ValueError)`; `str(exc)` is the refusal code alone, one of `UNIVERSE_RULE_INVALID`, `UNIVERSE_BODY_INVALID`, `UNIVERSE_RECEIPT_INVALID`, `UNIVERSE_REQUEST_SET_MISMATCH`, `UNIVERSE_NOT_FINAL`, `UNIVERSE_MANIFEST_MISMATCH`, `UNIVERSE_RULE_MISMATCH`.
  - `UNIVERSE_MARKET = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")`.
  - `FLAG_CLASSES = ("unflagged", "warning", "caution", "unknown", "absent")`.
  - `flag_class(entry: Mapping | None) -> str`.
  - `market_flags(body: bytes) -> dict[str, str]` (raises `UniverseError("UNIVERSE_BODY_INVALID")`).
  - `_strict_json(raw, code: str)`: bytes to JSON data with `Decimal` fractions; any defect is `UniverseError(code)`.
  - Test helpers in `tests/compliance_universe.py`: `CAUTIONS`, `_entry(market, *, warning=False, **caution) -> dict`, `_body(value) -> bytes`, `_code(call) -> str`.

- [ ] **Step 1: Write the failing tests and register the module**

Create `tests/compliance_universe.py` (LF):

```python
"""Upbit KRW universe, pure compliance code (universe spec sections 4 and 5; plan PR 1): the flag classes, the
request set, finality from content, the medians, and the snapshot file with its verification. Every body is an
inline fixture; nothing reads the network, the clock or a file."""
from __future__ import annotations

import json

from core.compliance import rules

CAUTIONS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING", "GLOBAL_PRICE_DIFFERENCES",
            "CONCENTRATION_OF_SMALL_ACCOUNTS")


def _entry(market: str, *, warning=False, **caution) -> dict:
    """One market object of market/all?is_details=true; every known caution key is false unless given."""
    return {"market": market, "korean_name": "x", "english_name": market.split("-")[-1],
            "market_event": {"warning": warning, "caution": {**{key: False for key in CAUTIONS}, **caution}}}


def _body(value) -> bytes:
    return json.dumps(value).encode("utf-8")


def _code(call) -> str:
    """The refusal code of the UniverseError that `call()` raises."""
    try:
        call()
    except rules.UniverseError as exc:
        return str(exc)
    raise AssertionError("accepted; expected UniverseError")


# -- flag classes (spec section 4) ---------------------------------------------------------------------------------
def test_flag_classes_follow_spec_4_exactly():
    assert rules.FLAG_CLASSES == ("unflagged", "warning", "caution", "unknown", "absent")
    assert rules.flag_class(_entry("KRW-BTC")) == "unflagged"
    assert rules.flag_class(None) == "absent"                                        # a missing coin
    assert rules.flag_class(_entry("KRW-BTC", warning=True)) == "warning"
    assert rules.flag_class(_entry("KRW-BTC", warning=True, PRICE_FLUCTUATIONS=True)) == "warning"
    for key in CAUTIONS:
        assert rules.flag_class(_entry("KRW-BTC", **{key: True})) == "caution", key
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=True)) == "caution"   # an unknown key included
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=False)) == "unflagged"


def test_flag_class_unknown_for_a_missing_or_malformed_field():
    no_event = _entry("KRW-BTC")
    del no_event["market_event"]
    assert rules.flag_class(no_event) == "unknown"                                   # a missing market_event
    calm = {key: False for key in CAUTIONS}
    for event in (None, [], "warning", {"caution": calm}, {"warning": None, "caution": calm},
                  {"warning": 0, "caution": calm}, {"warning": "false", "caution": calm}, {"warning": False},
                  {"warning": False, "caution": None}, {"warning": False, "caution": []}):
        assert rules.flag_class({"market": "KRW-BTC", "market_event": event}) == "unknown", event
    for key in CAUTIONS:
        missing = _entry("KRW-BTC")
        del missing["market_event"]["caution"][key]
        assert rules.flag_class(missing) == "unknown", key                           # a missing key
        for bad in (None, 0, 1, "false", "true"):
            assert rules.flag_class(_entry("KRW-BTC", **{key: bad})) == "unknown", (key, bad)   # not a boolean
    assert rules.flag_class([]) == rules.flag_class("KRW-BTC") == "unknown"         # not a market object


def test_market_flags_reads_krw_markets_and_refuses_a_bad_body():
    assert issubclass(rules.UniverseError, ValueError)
    assert str(rules.UniverseError("UNIVERSE_BODY_INVALID")) == "UNIVERSE_BODY_INVALID"
    body = _body([_entry("KRW-BTC"), _entry("KRW-ADA", warning=True), _entry("KRW-DOGE", TRADING_VOLUME_SOARING=True),
                  {"market": "KRW-ETH"}, _entry("BTC-ETH"), _entry("USDT-BTC"), _entry("KRW-btc"),
                  _entry("KRW-ABCDEFGHIJKLM"), {"market": 1}, {"korean_name": "x"}])
    assert rules.market_flags(body) == {"KRW-BTC": "unflagged", "KRW-ADA": "warning", "KRW-DOGE": "caution",
                                        "KRW-ETH": "unknown"}
    assert rules.market_flags(b"[]") == {}
    for bad in (b"", b"{}", b"null", b'"KRW-BTC"', b"[1]", b'[["KRW-BTC"]]', b"[", b"\xff",
                b'[{"market": "KRW-BTC", "market": "KRW-ETH"}]', b'[{"market": "KRW-BTC", "x": NaN}]',
                b"[" * 100_000 + b"]" * 100_000, _body([_entry("KRW-BTC"), _entry("KRW-BTC")])):
        assert _code(lambda: rules.market_flags(bad)) == "UNIVERSE_BODY_INVALID", bad[:40]
    assert _code(lambda: rules.market_flags("[]")) == "UNIVERSE_BODY_INVALID"       # bytes only
```

Then in `tests/compliance_acceptance.py`, replace lines 25-27:

```python
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer")
```

with:

```python
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer", "compliance_universe")
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `focus compliance compliance_universe/`
Expected: exit 1 with three FAIL rows, each `AttributeError: module 'core.compliance.rules' has no attribute ...` naming `FLAG_CLASSES`, `flag_class` and `UniverseError` in turn.

- [ ] **Step 3: Write the implementation in `core/compliance/rules.py`**

3a. After the import line `from datetime import date`, add:

```python
from decimal import Decimal
```

3b. Append to the end of the universe section (after `universe_rule_sha256`, before the `--check` banner), two blank lines before:

```python
UNIVERSE_MARKET = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")     # KRW quote, a base that passes _UNIVERSE_BASE
FLAG_CLASSES = ("unflagged", "warning", "caution", "unknown", "absent")
_CAUTION_KEYS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING", "GLOBAL_PRICE_DIFFERENCES",
                 "CONCENTRATION_OF_SMALL_ACCOUNTS")          # market_event.caution's five known keys


class UniverseError(ValueError):
    """A universe refusal. str(exc) is the refusal code alone (UNIVERSE_RULE_INVALID, UNIVERSE_BODY_INVALID,
    UNIVERSE_RECEIPT_INVALID, UNIVERSE_REQUEST_SET_MISMATCH, UNIVERSE_NOT_FINAL, UNIVERSE_MANIFEST_MISMATCH,
    UNIVERSE_RULE_MISMATCH), never a value read from a body or a file."""


def _unique(pairs) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("a repeated key")
        out[key] = value
    return out


def _no_constant(name):
    raise ValueError(f"{name} is not a JSON number")


def _strict_json(raw, code: str):
    """bytes -> JSON data with exact decimals (a JSON fraction is a Decimal), refusing a repeated key, NaN and
    Infinity; any defect is UniverseError(code)."""
    if type(raw) is not bytes:
        raise UniverseError(code)
    try:
        return json.loads(raw.decode("utf-8"), parse_float=Decimal, parse_constant=_no_constant,
                          object_pairs_hook=_unique)
    except (ValueError, RecursionError):                     # UnicodeDecodeError and JSONDecodeError included
        raise UniverseError(code) from None


def flag_class(entry: Mapping | None) -> str:
    """One market object of market/all?is_details=true -> its flag class (universe spec section 4); None (the market
    is not in the read) is "absent". A true warning decides first; only "unflagged" may be bought."""
    if entry is None:
        return "absent"
    event = entry.get("market_event") if isinstance(entry, Mapping) else None
    if not isinstance(event, Mapping) or type(event.get("warning")) is not bool:
        return "unknown"
    if event["warning"]:
        return "warning"
    caution = event.get("caution")
    if not isinstance(caution, Mapping) or any(type(caution.get(key)) is not bool for key in _CAUTION_KEYS):
        return "unknown"
    return "caution" if any(value is True for value in caution.values()) else "unflagged"


def market_flags(body: bytes) -> dict[str, str]:
    """Every market of a market/all?is_details=true body whose id matches UNIVERSE_MARKET, with its flag class;
    UniverseError("UNIVERSE_BODY_INVALID") unless the body is a JSON list of objects naming no market twice."""
    data = _strict_json(body, "UNIVERSE_BODY_INVALID")
    if type(data) is not list or any(type(item) is not dict for item in data):
        raise UniverseError("UNIVERSE_BODY_INVALID")
    flags: dict[str, str] = {}
    for item in data:
        market = item.get("market")
        if type(market) is str and UNIVERSE_MARKET.fullmatch(market):
            if market in flags:
                raise UniverseError("UNIVERSE_BODY_INVALID")
            flags[market] = flag_class(item)
    return flags
```

- [ ] **Step 4: Run the tests to see them pass**

```bash
focus compliance compliance_universe/
focus compliance compliance_tables/
focus compliance compliance_gate/
focus compliance compliance_guards/
```

Expected: every command exits 0 with only PASS rows.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/rules.py tests/compliance_universe.py tests/compliance_acceptance.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -F - <<'EOF'
Add the Upbit flag classes and market list reader

flag_class follows universe spec section 4 exactly (unflagged, warning, caution, unknown, absent);
market_flags reads every KRW-<base> market of a market/all?is_details=true body through a strict
JSON reader (Decimal fractions, no repeated key, no NaN). New test module compliance_universe,
registered in the compliance suite.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: the two `--stat` outputs are identical (three files).

---

### Task 3: Request set, receipts, finality and medians

**Files:**
- Modify: `core/compliance/rules.py:9` (add `import base64` before `import codecs`), `:15` (`collections.abc`), `:17` (`datetime`), the `decimal` import added in Task 2, and the end of the universe section (after `market_flags`)
- Modify: `tests/compliance_universe.py` (import block; append a section)
- Test: `tests/compliance_universe.py`

**Interfaces:**
- Consumes: `UniverseRule`, `_universe_rule`, `_rule_body` (Task 1), `Invalid` (existing); `UniverseError`, `market_flags`, `_strict_json` (Task 2).
- Produces:
  - `universe_requests(rule: UniverseRule, market_all_body: bytes, day: date) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]`: sorted; `market/all` params `(("is_details", "true"),)`; candle params `("market", m), ("to", "<YYYY-MM-DD>T00:00:00Z"), ("count", "<n>")`.
  - `universe_eligible(rule: UniverseRule, receipts: Sequence[Mapping], day: date) -> tuple[tuple[str, ...], tuple[tuple[str, Decimal], ...]]`: `(listed, eligible)`, `listed` sorted, `eligible` sorted by market.
  - `_eligible(rule, receipts, day) -> tuple[tuple[str, ...], tuple[tuple[str, Decimal], ...], datetime]`: `(listed, eligible, built_at)`, used by Task 4.
  - `_RECEIPT_KEYS`, `_midnight(day: date) -> datetime`, `_IN_FORCE_AT = timedelta(minutes=40)`, used by Task 4.
  - `_typed(rule, day) -> None`: `ValueError` unless `day` is a `date` and `rule` is a `UniverseRule` the venue parser accepts (re-parsed through `_universe_rule(_rule_body(rule), ...)`).
  - A plain receipt is a mapping with exactly `path` (str), `params` (list of `[str, str]`), `account_scope` (`"public"`), `received_at` and `server_time` (`YYYY-MM-DDTHH:MM:SS.ffffffZ`, the form of `execution_control.store._utc`), `raw_body_b64` (the one standard base64 text of the body), `sha256` (lower-case hex of the body).
  - Test fixtures in `tests/compliance_universe.py`: `D`, `AT`, `SOURCE`, `RULE`, `RULE_SHA`, `AGE_TO`, `VALUE_TO`, `MARKETS`, `MENU`, `CANDIDATES`, `VALUES`, `OLD`, `LISTED`, `ELIGIBLE`, `_candle`, `_stamp`, `_receipt`, `_receipts`, `_key`, `_index`, `_value_error`.

- [ ] **Step 1: Write the failing tests**

In `tests/compliance_universe.py`, replace the import block:

```python
from __future__ import annotations

import json

from core.compliance import rules
```

with:

```python
from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from core.compliance import rules
```

Then append to the end of the file:

```python


# -- request set, receipts, finality and medians (spec section 5 "Requests", "Finality from content") -------------
D = date(2026, 11, 11)                                         # candle day D (UTC)
AT = datetime(2026, 11, 11, 0, 11, tzinfo=timezone.utc)        # every fixture receipt's server time: after D 00:10
SOURCE = "https://docs.upbit.com/kr/reference/list-trading-pairs"
RULE = rules.UniverseRule(source=SOURCE, quote="KRW", exclude=("USDC", "USDT"), min_listing_days=5, median_days=4,
                          min_median_value_krw=100)
RULE_SHA = rules.universe_rule_sha256(RULE)
AGE_TO, VALUE_TO = "2026-11-06T00:00:00Z", "2026-11-11T00:00:00Z"   # D - min_listing_days, and D
MARKETS = (_entry("KRW-BTC"), _entry("KRW-ETH"), _entry("KRW-SOL"), _entry("KRW-XRP"),
           _entry("KRW-ADA", warning=True), _entry("KRW-DOGE", TRADING_VOLUME_SOARING=True), _entry("KRW-USDT"),
           _entry("BTC-ETH"))                                  # KRW-BTC first: MARKETS[1:] drops a candidate
MENU = _body(MARKETS)
CANDIDATES = ("KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP")      # unflagged KRW markets that are not excluded
VALUES = {"KRW-BTC": {1: 400, 2: 300, 3: 200, 4: 100},         # n -> the value of day D-n; a missing n has no candle
          "KRW-ETH": {1: 50.5, 3: 1000, 4: 10},
          "KRW-SOL": {1: 150, 2: 150.5, 3: 99, 4: 151},
          "KRW-XRP": {1: 5000, 2: 5000, 3: 5000, 4: 5000}}
OLD = ("KRW-BTC", "KRW-ETH", "KRW-SOL")                         # KRW-XRP's age read comes back empty
LISTED = ("KRW-ADA", "KRW-BTC", "KRW-DOGE", "KRW-ETH", "KRW-SOL", "KRW-USDT", "KRW-XRP")
ELIGIBLE = (("KRW-BTC", Decimal(250)), ("KRW-SOL", Decimal("150.25")))   # KRW-ETH's median is 30.25 < 100


def _candle(market: str, day: date, value) -> dict:
    """One /v1/candles/days row: the fields the universe reads, plus one it ignores."""
    return {"market": market, "candle_date_time_utc": f"{day.isoformat()}T00:00:00", "candle_acc_trade_price": value,
            "candle_acc_trade_volume": 1.5}


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _receipt(path: str, params, body: bytes, server: datetime = AT) -> dict:
    """A plain receipt in live_history's 7-key shape."""
    return {"path": path, "params": [[k, v] for k, v in params], "account_scope": "public",
            "received_at": _stamp(server + timedelta(milliseconds=5)), "server_time": _stamp(server),
            "raw_body_b64": base64.b64encode(body).decode("ascii"), "sha256": hashlib.sha256(body).hexdigest()}


def _receipts(*, markets=MARKETS, values=VALUES, old=OLD, old_day=date(2026, 11, 5), server=AT, count=4) -> list:
    """market/all, then each candidate's age and value reads (newest candle first), as plain receipts."""
    out = [_receipt("/v1/market/all", [("is_details", "true")], _body(markets), server)]
    for market in CANDIDATES:
        age = [_candle(market, old_day, 1)] if market in old else []
        value = [_candle(market, D - timedelta(days=n), v) for n, v in sorted(values.get(market, {}).items())]
        out.append(_receipt("/v1/candles/days", [("market", market), ("to", AGE_TO), ("count", "1")], _body(age),
                            server))
        out.append(_receipt("/v1/candles/days", [("market", market), ("to", VALUE_TO), ("count", str(count))],
                            _body(value), server))
    return out


def _key(receipt: dict) -> tuple:
    return receipt["path"], tuple(tuple(pair) for pair in receipt["params"])


def _index(receipts: list, market: str, to: str) -> int:
    return next(i for i, r in enumerate(receipts) if ["market", market] in r["params"] and ["to", to] in r["params"])


def _value_error(call) -> None:
    """Asserts `call()` raises a plain ValueError: a caller's mistake, not a refusal code."""
    try:
        call()
    except rules.UniverseError as exc:
        raise AssertionError(f"a refusal code, not a caller error: {exc}") from None
    except ValueError:
        return
    raise AssertionError("accepted; expected ValueError")


def test_universe_requests_are_exactly_what_the_rule_implies():
    want = tuple(("/v1/candles/days", (("market", m), ("to", to), ("count", n)))
                 for m in CANDIDATES for to, n in ((AGE_TO, "1"), (VALUE_TO, "4")))
    want += (("/v1/market/all", (("is_details", "true"),)),)
    assert rules.universe_requests(RULE, MENU, D) == want
    assert tuple(sorted(_key(r) for r in _receipts())) == want
    spec = dataclasses.replace(RULE, min_listing_days=250, median_days=30, min_median_value_krw=1_000_000_000)
    assert rules.universe_requests(spec, _body([_entry("KRW-BTC")]), D) == (
        ("/v1/candles/days", (("market", "KRW-BTC"), ("to", "2026-03-06T00:00:00Z"), ("count", "1"))),
        ("/v1/candles/days", (("market", "KRW-BTC"), ("to", "2026-11-11T00:00:00Z"), ("count", "30"))),
        ("/v1/market/all", (("is_details", "true"),)))
    assert rules.universe_requests(dataclasses.replace(RULE, exclude=("BTC", "USDC", "USDT")), MENU, D) == want[2:]
    assert rules.universe_requests(RULE, b"[]", D) == want[-1:]
    assert rules.universe_requests(RULE, _body([_entry("KRW-BTC", PRICE_FLUCTUATIONS=None)]), D) == want[-1:]
    assert _code(lambda: rules.universe_requests(RULE, b"{}", D)) == "UNIVERSE_BODY_INVALID"
    _value_error(lambda: rules.universe_requests(RULE, MENU, datetime(2026, 11, 11, tzinfo=timezone.utc)))
    _value_error(lambda: rules.universe_requests(RULE, MENU, "2026-11-11"))
    _value_error(lambda: rules.universe_requests(dataclasses.asdict(RULE), MENU, D))
    for bad in ({"median_days": 0}, {"min_listing_days": 3651}, {"quote": "USDT"}, {"exclude": ("usdt",)},
                {"source": " "}, {"min_median_value_krw": True}):           # built in code, refused by the parser
        _value_error(lambda: rules.universe_requests(dataclasses.replace(RULE, **bad), MENU, D))
        _value_error(lambda: rules.universe_eligible(dataclasses.replace(RULE, **bad), _receipts(), D))


def test_universe_eligible_lists_krw_markets_and_takes_medians():
    listed, eligible = rules.universe_eligible(RULE, _receipts(), D)
    assert listed == LISTED and eligible == ELIGIBLE, (listed, eligible)
    assert all(type(median) is Decimal for _, median in eligible)

    def medians(values, rule=RULE, count=4):
        return rules.universe_eligible(rule, _receipts(values=values, count=count), D)[1]

    traded = {**VALUES, "KRW-ETH": {1: 50.5, 2: 300, 3: 1000, 4: 10}}          # [10, 50.5, 300, 1000]
    assert medians(traded) == (("KRW-BTC", Decimal(250)), ("KRW-ETH", Decimal("175.25")),
                               ("KRW-SOL", Decimal("150.25")))
    gaps = {**VALUES, "KRW-SOL": {1: 200, 4: 200}}                             # D-2, D-3 count as zero: [0, 0, 200, 200]
    assert medians(gaps) == (("KRW-BTC", Decimal(250)), ("KRW-SOL", Decimal(100)))   # 100 is not below 100
    older = {**VALUES, "KRW-BTC": {1: 400, 3: 200, 4: 100, 5: 10 ** 12}}        # D-5 is outside: [0, 100, 200, 400]
    assert medians(older)[0] == ("KRW-BTC", Decimal(150))
    odd = {m: {n: v for n, v in days.items() if n <= 3} for m, days in VALUES.items()}
    assert medians(odd, dataclasses.replace(RULE, median_days=3), 3) == (("KRW-BTC", Decimal(300)),
                                                                          ("KRW-SOL", Decimal(150)))
    assert rules.universe_eligible(dataclasses.replace(RULE, min_median_value_krw=251), _receipts(), D) == (LISTED, ())
    assert rules.universe_eligible(dataclasses.replace(RULE, min_median_value_krw=250), _receipts(), D) == (
        LISTED, (("KRW-BTC", Decimal(250)),))
    assert rules.universe_eligible(RULE, _receipts(old_day=date(2026, 11, 6)), D) == (LISTED, ())   # dated `to`
    assert rules.universe_eligible(RULE, _receipts(old=()), D) == (LISTED, ())
    _value_error(lambda: rules.universe_eligible(RULE, _receipts(), datetime(2026, 11, 11, tzinfo=timezone.utc)))


def test_finality_comes_from_content():
    utc = timezone.utc
    assert rules.universe_eligible(RULE, _receipts(server=datetime(2026, 11, 11, 0, 10, tzinfo=utc)), D) == (
        LISTED, ELIGIBLE)                                                       # built at D 00:10 exactly
    early = _receipts(server=datetime(2026, 11, 11, 0, 9, 59, 999999, tzinfo=utc))
    assert _code(lambda: rules.universe_eligible(RULE, early, D)) == "UNIVERSE_NOT_FINAL"

    def with_menu_at(moment: datetime) -> list:
        receipts = _receipts()
        receipts[0] = _receipt("/v1/market/all", [("is_details", "true")], MENU, moment)
        return receipts

    stale = with_menu_at(datetime(2026, 11, 10, 23, 59, 59, tzinfo=utc))      # the list read before D 00:00
    assert _code(lambda: rules.universe_eligible(RULE, stale, D)) == "UNIVERSE_NOT_FINAL"
    assert rules.universe_eligible(RULE, with_menu_at(datetime(2026, 11, 11, tzinfo=utc)), D) == (LISTED, ELIGIBLE)
    for n in (0, -1):                                                          # a value candle dated D or D+1
        values = {**VALUES, "KRW-BTC": {n: 1, 1: 400, 2: 300, 3: 200}}
        assert _code(lambda: rules.universe_eligible(RULE, _receipts(values=values), D)) == "UNIVERSE_NOT_FINAL", n
    for day in (D, D + timedelta(days=1)):                                     # an age candle dated D or later
        assert _code(lambda: rules.universe_eligible(RULE, _receipts(old_day=day), D)) == "UNIVERSE_NOT_FINAL", day


def test_a_snapshot_cannot_add_drop_or_swap_a_receipt():
    good, mismatch = _receipts(), "UNIVERSE_REQUEST_SET_MISMATCH"

    def code(receipts) -> str:
        return _code(lambda: rules.universe_eligible(RULE, receipts, D))

    for i in range(len(good)):
        assert code(good[:i] + good[i + 1:]) == mismatch, i                   # any one dropped, market/all included
    assert code(good + [good[3]]) == mismatch                                  # one repeated
    assert code(good + [good[0]]) == mismatch                                  # two market/all reads
    ada = _receipt("/v1/candles/days", [("market", "KRW-ADA"), ("to", VALUE_TO), ("count", "4")], b"[]")
    assert code(good + [ada]) == mismatch                                      # a warning coin's read added
    i = _index(good, "KRW-XRP", VALUE_TO)
    swapped = list(good)
    swapped[i] = _receipt("/v1/candles/days", [("market", "KRW-XRP"), ("to", VALUE_TO), ("count", "30")], b"[]")
    assert code(swapped) == mismatch                                           # another count
    swapped[i] = {**good[i], "params": list(reversed(good[i]["params"]))}
    assert code(swapped) == mismatch                                           # the same pairs in another order
    swapped[i] = {**good[i], "path": "/v1/candles/minutes/1"}
    assert code(swapped) == mismatch                                           # another path
    menu = _receipt("/v1/market/all", [("is_details", "true")], _body(MARKETS[1:]))
    assert code([menu] + good[1:]) == mismatch                                 # KRW-BTC left the list
    flagged = (_entry("KRW-BTC", warning=True),) + MARKETS[1:]
    assert code(_receipts(markets=flagged)) == mismatch                        # KRW-BTC is now warning
    assert code(_receipts(markets=MARKETS + (_entry("KRW-TRX"),))) == mismatch    # a new candidate without its reads
    assert rules.universe_eligible(RULE, list(reversed(good)), D) == (LISTED, ELIGIBLE)    # the order is free


def test_a_tampered_or_malformed_receipt_is_refused():
    good, invalid = _receipts(), "UNIVERSE_RECEIPT_INVALID"
    i = _index(good, "KRW-XRP", AGE_TO)
    assert good[i]["raw_body_b64"] == "W10=" and base64.b64decode("W11=", validate=True) == b"[]"

    def refused(receipt) -> str:
        changed = list(good)
        changed[i] = receipt
        return _code(lambda: rules.universe_eligible(RULE, changed, D))

    for change in ({"raw_body_b64": base64.b64encode(b"[ ]").decode("ascii")},     # another body, the old hash
                   {"sha256": "0" * 64}, {"sha256": good[i]["sha256"].upper()}, {"sha256": 1},
                   {"raw_body_b64": "W11="}, {"raw_body_b64": "W10=="}, {"raw_body_b64": "W1 0="},
                   {"raw_body_b64": "W10"}, {"raw_body_b64": "W10=!"}, {"raw_body_b64": None},
                   {"account_scope": "account"}, {"path": None}, {"params": "market=KRW-XRP"},
                   {"params": [["market", "KRW-XRP", "x"]]}, {"params": [[1, 2]]},
                   {"received_at": "2026-11-11T00:11:00Z"}, {"server_time": "2026-11-11T00:11:00.000000+00:00"},
                   {"server_time": "2026-13-11T00:11:00.000000Z"}, {"server_time": None}):
        assert refused({**good[i], **change}) == invalid, change
    assert refused({**good[i], "note": "x"}) == invalid                        # an eighth key
    assert refused({k: v for k, v in good[i].items() if k != "received_at"}) == invalid
    for receipts in ("receipts", b"receipts", {"path": "/v1/market/all"}, [None], [1], [good[0], "x"]):
        assert _code(lambda: rules.universe_eligible(RULE, receipts, D)) == invalid, receipts


def test_candle_bodies_are_checked():
    receipts = _receipts()
    i = _index(receipts, "KRW-BTC", VALUE_TO)

    def code(body: bytes) -> str:
        changed = list(receipts)
        changed[i] = _receipt("/v1/candles/days", [("market", "KRW-BTC"), ("to", VALUE_TO), ("count", "4")], body)
        return _code(lambda: rules.universe_eligible(RULE, changed, D))

    day1, bad = D - timedelta(days=1), "UNIVERSE_BODY_INVALID"
    assert code(_body([_candle("KRW-BTC", D - timedelta(days=n), 1) for n in range(1, 6)])) == bad   # 5 rows, count 4
    assert code(_body([_candle("KRW-ETH", day1, 1)])) == bad                                         # another market
    assert code(_body([_candle("KRW-BTC", day1, 1), _candle("KRW-BTC", day1, 2)])) == bad            # a repeated day
    for start in ("2026-11-10T09:00:00", "2026-11-10", "2026-11-31T00:00:00", "2026-11-10T00:00:00Z", None):
        assert code(_body([{**_candle("KRW-BTC", day1, 1), "candle_date_time_utc": start}])) == bad, start
    for value in (-1, -0.5, True, "1000", None, [1]):
        assert code(_body([_candle("KRW-BTC", day1, value)])) == bad, value
    no_value = _candle("KRW-BTC", day1, 1)
    del no_value["candle_acc_trade_price"]
    assert code(_body([no_value])) == bad
    for raw in (b"{}", b"[1]", b"[", b"\xff", b"", b'[{"market": "KRW-BTC", "market": "KRW-BTC"}]',
                b'[{"market": "KRW-BTC", "candle_date_time_utc": "2026-11-10T00:00:00", '
                b'"candle_acc_trade_price": NaN}]'):
        assert code(raw) == bad, raw
    assert rules.universe_eligible(RULE, receipts, D) == (LISTED, ELIGIBLE)    # the untouched receipts still pass
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `focus compliance compliance_universe/`
Expected: exit 1. The three Task 2 tests PASS; the six new tests FAIL with `AttributeError: module 'core.compliance.rules' has no attribute 'universe_requests'` (the requests test) or `... 'universe_eligible'` (the other five).

- [ ] **Step 3: Write the implementation in `core/compliance/rules.py`**

3a. Imports. Replace `import codecs` (line 9) with:

```python
import base64
import codecs
```

replace `from collections.abc import Mapping` with:

```python
from collections.abc import Mapping, Sequence
```

replace `from datetime import date` with:

```python
from datetime import date, datetime, timedelta, timezone
```

and replace `from decimal import Decimal` (added in Task 2) with:

```python
from decimal import Decimal, localcontext
```

3b. Append to the end of the universe section (after `market_flags`, before the `--check` banner), two blank lines before:

```python
_MARKET_ALL = ("/v1/market/all", (("is_details", "true"),))   # (path, params) of the one list read
_CANDLES_PATH = "/v1/candles/days"
_RECEIPT_KEYS = frozenset({"path", "params", "account_scope", "received_at", "server_time", "raw_body_b64",
                           "sha256"})                          # live_history's plain receipt shape
_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z")   # execution_control.store
_HEX64 = re.compile(r"[0-9a-f]{64}")
_CANDLE_START = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T00:00:00")
_FINAL_AFTER = timedelta(minutes=10)                           # built_at at or after D 00:10 UTC
_IN_FORCE_AT = timedelta(minutes=40)                           # D 00:40 UTC, 09:40 KST


def _typed(rule, day) -> None:
    """A caller's mistake is a plain ValueError, never a refusal code: not a date, or not a UniverseRule the venue
    parser would build (a rule built in code with median_days=0 would otherwise fail deep inside the median)."""
    if type(rule) is not UniverseRule or type(day) is not date:
        raise ValueError("universe: expected a UniverseRule and a date")
    try:
        _universe_rule(_rule_body(rule), "universe_rule", frozenset({"KRW"}))
    except Invalid as exc:
        raise ValueError(f"universe: {exc.reason}") from None


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _candle_request(market: str, to: date, count: int) -> tuple[str, tuple[tuple[str, str], ...]]:
    return _CANDLES_PATH, (("market", market), ("to", f"{to.isoformat()}T00:00:00Z"), ("count", str(count)))


def _candidates(rule: UniverseRule, flags: Mapping[str, str]) -> list[str]:
    """The markets that need candle reads, sorted: unflagged and not excluded (universe spec section 5, step 2)."""
    return [m for m in sorted(flags) if flags[m] == "unflagged" and m.removeprefix("KRW-") not in rule.exclude]


def universe_requests(rule: UniverseRule, market_all_body: bytes,
                      day: date) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """The exact (path, params) set the rule implies for this market/all body and candle day D, sorted: the list read,
    then for each candidate an age read (`to` D - min_listing_days, count 1) and a value read (`to` D, count
    median_days)."""
    _typed(rule, day)
    age_to = day - timedelta(days=rule.min_listing_days)
    wanted = [_MARKET_ALL]
    for market in _candidates(rule, market_flags(market_all_body)):
        wanted += [_candle_request(market, age_to, 1), _candle_request(market, day, rule.median_days)]
    return tuple(sorted(wanted))


def _stamp(value) -> datetime:
    if type(value) is not str or not _STAMP.fullmatch(value):
        raise UniverseError("UNIVERSE_RECEIPT_INVALID")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise UniverseError("UNIVERSE_RECEIPT_INVALID") from None


def _receipt(value) -> tuple[tuple, bytes, datetime]:
    """One plain receipt -> ((path, params), body, server time), after its keys, shape, stamps and hash."""
    if not isinstance(value, Mapping) or set(value) != _RECEIPT_KEYS:
        raise UniverseError("UNIVERSE_RECEIPT_INVALID")
    path, params, text, sha = value["path"], value["params"], value["raw_body_b64"], value["sha256"]
    if (type(path) is not str or type(params) is not list
            or any(type(p) is not list or len(p) != 2 or any(type(x) is not str for x in p) for p in params)
            or value["account_scope"] != "public" or type(text) is not str
            or type(sha) is not str or not _HEX64.fullmatch(sha)):
        raise UniverseError("UNIVERSE_RECEIPT_INVALID")
    _stamp(value["received_at"])
    server = _stamp(value["server_time"])
    try:
        body = base64.b64decode(text, validate=True)
    except ValueError:                                         # binascii.Error, and a non-ASCII text
        raise UniverseError("UNIVERSE_RECEIPT_INVALID") from None
    if base64.b64encode(body).decode("ascii") != text or hashlib.sha256(body).hexdigest() != sha:
        raise UniverseError("UNIVERSE_RECEIPT_INVALID")
    return (path, tuple((k, v) for k, v in params)), body, server


def _candles(body: bytes, market: str, most: int, day: date) -> dict:
    """A candles/days body -> {candle day: accumulated KRW trade value}. A candle dated D or later is not final."""
    data = _strict_json(body, "UNIVERSE_BODY_INVALID")
    if type(data) is not list or len(data) > most:
        raise UniverseError("UNIVERSE_BODY_INVALID")
    out: dict = {}
    for item in data:
        if type(item) is not dict or item.get("market") != market:
            raise UniverseError("UNIVERSE_BODY_INVALID")
        start, value = item.get("candle_date_time_utc"), item.get("candle_acc_trade_price")
        if (type(start) is not str or not _CANDLE_START.fullmatch(start)
                or type(value) not in (int, Decimal) or value < 0):
            raise UniverseError("UNIVERSE_BODY_INVALID")
        try:
            when = date.fromisoformat(start[:10])
        except ValueError:
            raise UniverseError("UNIVERSE_BODY_INVALID") from None
        if when >= day:
            raise UniverseError("UNIVERSE_NOT_FINAL")
        if when in out:
            raise UniverseError("UNIVERSE_BODY_INVALID")
        out[when] = value
    return out


def _median(values: list) -> Decimal:
    ordered, mid = sorted(values), len(values) // 2
    if len(ordered) % 2:
        return Decimal(ordered[mid])
    with localcontext(prec=60):                                # exact for any value Upbit reports
        return (Decimal(ordered[mid - 1]) + Decimal(ordered[mid])) / 2


def _eligible(rule: UniverseRule, receipts,
              day: date) -> tuple[tuple[str, ...], tuple[tuple[str, Decimal], ...], datetime]:
    """(listed, eligible, built_at) from plain receipts: every receipt and hash, the exact request set, finality, then
    the age test and the median over calendar days D-median_days .. D-1, a day with no candle counting as zero."""
    _typed(rule, day)
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        raise UniverseError("UNIVERSE_RECEIPT_INVALID")
    checked = [_receipt(value) for value in receipts]
    menus = [(body, server) for key, body, server in checked if key == _MARKET_ALL]
    if len(menus) != 1:
        raise UniverseError("UNIVERSE_REQUEST_SET_MISMATCH")
    menu, menu_time = menus[0]
    if tuple(sorted(key for key, _, _ in checked)) != universe_requests(rule, menu, day):
        raise UniverseError("UNIVERSE_REQUEST_SET_MISMATCH")
    built_at = max(server for _, _, server in checked)
    if menu_time < _midnight(day) or built_at < _midnight(day) + _FINAL_AFTER:
        raise UniverseError("UNIVERSE_NOT_FINAL")
    bodies = {key: body for key, body, _ in checked}
    flags = market_flags(menu)
    age_to = day - timedelta(days=rule.min_listing_days)
    eligible = []
    for market in _candidates(rule, flags):
        aged = _candles(bodies[_candle_request(market, age_to, 1)], market, 1, day)
        value = _candles(bodies[_candle_request(market, day, rule.median_days)], market, rule.median_days, day)
        median = _median([value.get(day - timedelta(days=n), 0) for n in range(1, rule.median_days + 1)])
        if any(when < age_to for when in aged) and median >= rule.min_median_value_krw:
            eligible.append((market, median))
    return tuple(sorted(flags)), tuple(eligible), built_at


def universe_eligible(rule: UniverseRule, receipts: Sequence[Mapping],
                      day: date) -> tuple[tuple[str, ...], tuple[tuple[str, Decimal], ...]]:
    """(listed, eligible) for candle day D (universe spec section 5): listed is every KRW-<base> market of the list
    read, eligible every candidate that is old enough with a median daily value of at least min_median_value_krw,
    sorted by market with its median. Refusals are UniverseError codes; a caller's mistake is ValueError."""
    listed, eligible, _ = _eligible(rule, receipts, day)
    return listed, eligible
```

- [ ] **Step 4: Run the tests to see them pass**

```bash
focus compliance compliance_universe/
focus compliance compliance_tables/
focus compliance compliance_gate/
focus compliance compliance_guards/
```

Expected: every command exits 0 with only PASS rows (`compliance_guards/test_no_wall_clock_outside_cli_main` and `test_imports_stay_on_the_allowlist` included).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/rules.py tests/compliance_universe.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -F - <<'EOF'
Check the universe request set, finality and medians

universe_requests gives the exact (path, params) set the signed rule implies for a market/all body
and candle day D; universe_eligible checks every plain receipt and its hash, refuses an added,
dropped or swapped receipt, takes finality from content (no candle dated D or later, the list read
at or after D 00:00 UTC, built_at at or after D 00:10 UTC) and takes Decimal medians over calendar
days with a missing day as zero (universe spec section 5).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: the two `--stat` outputs are identical (two files).

---

### Task 4: Snapshot encode, verify, `Universe` and top N

**Files:**
- Modify: `core/compliance/model.py:17-18` (`TYPE_CHECKING` imports), after `:161` (insert `Universe` after `SessionState`, before `Context` at 164)
- Modify: `core/compliance/rules.py:24-25` (`TYPE_CHECKING` import; line numbers at fd85850, before the earlier tasks added imports) and the end of the universe section (after `universe_eligible`)
- Modify: `tests/compliance_universe.py` (import block; append a section)
- Test: `tests/compliance_universe.py`

**Interfaces:**
- Consumes: `_universe_rule`, `_rule_body`, `_universe_json`, `universe_rule_sha256`, `parse_date`, `Invalid` (Task 1 and existing); `UniverseError`, `_strict_json` (Task 2); `_eligible`, `_RECEIPT_KEYS`, `_midnight`, `_IN_FORCE_AT` (Task 3).
- Produces:
  - `model.Universe`: `@dataclass(frozen=True, kw_only=True)`, fields in order `day: date; rule_sha256: str; snapshot_sha256: str; built_at: datetime; valid_from: datetime; valid_until: datetime; listed: tuple[str, ...]; eligible: tuple[tuple[str, Decimal], ...]`.
  - `encode_universe_snapshot(rule: UniverseRule, day: date, receipts: Sequence[Mapping]) -> tuple[bytes, str]`: the file bytes and the manifest sha256 (also the file name for `owner.universe_path`).
  - `verify_universe_snapshot(raw: bytes, rule_sha256: str) -> Universe`.
  - `universe_top_n(universe: Universe, n: int) -> tuple[str, ...]`.
  - Snapshot file: `_universe_json({"day": "<YYYY-MM-DD>", "rule": _rule_body(rule), "receipts": [plain receipts sorted by (path, params)], "manifest_sha256": m})` where `m = sha256(_universe_json` of the same object without `manifest_sha256`).

- [ ] **Step 1: Write the failing tests**

In `tests/compliance_universe.py`, replace the import block:

```python
from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from core.compliance import rules
```

with:

```python
from __future__ import annotations

import ast
import base64
import dataclasses
import hashlib
import inspect
import json
import os
import textwrap
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from core.compliance import model, rules
```

Then append to the end of the file:

```python


# -- snapshot file, verification, in-force window, top N (spec section 5 "Format and verification", "In force") ----
def _json(value) -> bytes:
    """The snapshot file's JSON form: sorted keys, no spaces, ASCII."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _resealed(doc: dict) -> bytes:
    """`doc` as a snapshot file with its manifest recomputed: a consistent edit of anything but the receipt hashes."""
    body = {key: doc[key] for key in ("day", "rule", "receipts")}
    return _json({**body, "manifest_sha256": hashlib.sha256(_json(body)).hexdigest()})


def _verify_code(raw, rule_sha256=RULE_SHA) -> str:
    return _code(lambda: rules.verify_universe_snapshot(raw, rule_sha256))


def test_snapshot_round_trip_and_in_force_window():
    utc = timezone.utc
    raw, sha = rules.encode_universe_snapshot(RULE, D, _receipts())
    doc = json.loads(raw)
    assert type(raw) is bytes and _json(doc) == raw and _resealed(doc) == raw and doc["manifest_sha256"] == sha
    assert doc["day"] == "2026-11-11" and doc["rule"] == {
        "source": SOURCE, "quote": "KRW", "exclude": ["USDC", "USDT"], "min_listing_days": 5, "median_days": 4,
        "min_median_value_krw": 100}
    assert [_key(r) for r in doc["receipts"]] == sorted(_key(r) for r in _receipts())     # stored in request order
    assert rules.encode_universe_snapshot(RULE, D, list(reversed(_receipts()))) == (raw, sha)   # input order is free
    universe = rules.verify_universe_snapshot(raw, RULE_SHA)
    assert universe == model.Universe(
        day=D, rule_sha256=RULE_SHA, snapshot_sha256=sha, built_at=AT,
        valid_from=datetime(2026, 11, 11, 0, 40, tzinfo=utc), valid_until=datetime(2026, 11, 12, 0, 40, tzinfo=utc),
        listed=LISTED, eligible=ELIGIBLE), universe
    assert universe.valid_from.astimezone(model.KST).isoformat() == "2026-11-11T09:40:00+09:00"
    assert universe.valid_until.astimezone(model.KST).isoformat() == "2026-11-12T09:40:00+09:00"
    late = _receipts()
    j = _index(late, "KRW-SOL", VALUE_TO)
    late[j] = _receipt(late[j]["path"], late[j]["params"], base64.b64decode(late[j]["raw_body_b64"]),
                       datetime(2026, 11, 11, 1, 5, tzinfo=utc))             # one read finished at 10:05 KST
    later = rules.verify_universe_snapshot(rules.encode_universe_snapshot(RULE, D, late)[0], RULE_SHA)
    assert later.built_at == later.valid_from == datetime(2026, 11, 11, 1, 5, tzinfo=utc)
    assert later.valid_until == universe.valid_until and later.eligible == ELIGIBLE
    assert _code(lambda: rules.encode_universe_snapshot(RULE, D, _receipts()[:-1])) == "UNIVERSE_REQUEST_SET_MISMATCH"
    early = _receipts(server=datetime(2026, 11, 11, 0, 9, tzinfo=utc))
    assert _code(lambda: rules.encode_universe_snapshot(RULE, D, early)) == "UNIVERSE_NOT_FINAL"


def test_a_tampered_snapshot_file_is_refused():
    raw, sha = rules.encode_universe_snapshot(RULE, D, _receipts())
    doc, manifest, mismatch = json.loads(raw), "UNIVERSE_MANIFEST_MISMATCH", "UNIVERSE_REQUEST_SET_MISMATCH"
    rule_with_float = {**doc, "rule": {**doc["rule"], "min_listing_days": 5.0}}      # parses to a Decimal
    for bad in (raw.replace(b'"median_days":4', b'"median_days":3'), raw + b"\n", b" " + raw, raw.decode("ascii"),
                b"", b"{}", b"[]", b"null", json.dumps(doc, indent=1).encode("ascii"), _json({**doc, "extra": 1}),
                _json({**doc, "manifest_sha256": "0" * 64}), _json({**doc, "manifest_sha256": sha.upper()}),
                _resealed({**doc, "day": "2026-11-31"}), _resealed({**doc, "day": 20261111}),
                _resealed(rule_with_float), raw.replace(b"{", b'{"day":"2026-11-11",', 1)):
        assert _verify_code(bad) == manifest, bad[:60]
    receipts = [dict(r) for r in doc["receipts"]]
    m = next(k for k, r in enumerate(receipts) if r["path"] == "/v1/market/all")
    receipts[m]["raw_body_b64"] = base64.b64encode(_body(MARKETS[1:])).decode("ascii")
    assert _verify_code(_resealed({**doc, "receipts": receipts})) == "UNIVERSE_RECEIPT_INVALID"   # body, old hash
    receipts[m]["sha256"] = hashlib.sha256(_body(MARKETS[1:])).hexdigest()
    assert _verify_code(_resealed({**doc, "receipts": receipts})) == mismatch      # KRW-BTC's reads are left over
    assert _verify_code(_resealed({**doc, "receipts": doc["receipts"][:-1]})) == mismatch          # one dropped
    assert _verify_code(_resealed({**doc, "receipts": doc["receipts"] + doc["receipts"][:1]})) == mismatch  # added
    assert _verify_code(_resealed({**doc, "day": "2026-11-12"})) == mismatch       # another day's request set
    assert _verify_code(_resealed({**doc, "receipts": {}})) == "UNIVERSE_RECEIPT_INVALID"
    other = dataclasses.replace(RULE, min_median_value_krw=1)
    assert _verify_code(raw, rules.universe_rule_sha256(other)) == "UNIVERSE_RULE_MISMATCH"   # the signed rule moved
    assert _verify_code(raw, RULE_SHA.upper()) == _verify_code(raw, None) == "UNIVERSE_RULE_MISMATCH"
    looser = _resealed({**doc, "rule": {**doc["rule"], "min_median_value_krw": 1}})
    assert _verify_code(looser) == "UNIVERSE_RULE_MISMATCH"                       # built under another rule
    assert rules.verify_universe_snapshot(looser, rules.universe_rule_sha256(other)).eligible == (
        ("KRW-BTC", Decimal(250)), ("KRW-ETH", Decimal("30.25")), ("KRW-SOL", Decimal("150.25")))
    for rule in ({**doc["rule"], "quote": "USDT"}, {**doc["rule"], "median_days": 0}, {**doc["rule"], "extra": 1},
                 {k: v for k, v in doc["rule"].items() if k != "source"}, {**doc["rule"], "exclude": ["USDT", "USDC"]},
                 None, []):
        assert _verify_code(_resealed({**doc, "rule": rule})) == "UNIVERSE_RULE_INVALID", rule


def test_universe_is_a_frozen_record_with_the_contract_fields():
    assert [f.name for f in dataclasses.fields(model.Universe)] == [
        "day", "rule_sha256", "snapshot_sha256", "built_at", "valid_from", "valid_until", "listed", "eligible"]
    assert [f.name for f in dataclasses.fields(rules.UniverseRule)] == [
        "source", "quote", "exclude", "min_listing_days", "median_days", "min_median_value_krw"]
    universe = rules.verify_universe_snapshot(rules.encode_universe_snapshot(RULE, D, _receipts())[0], RULE_SHA)
    for record, name in ((universe, "day"), (RULE, "median_days")):
        try:
            setattr(record, name, None)
        except dataclasses.FrozenInstanceError:
            continue
        raise AssertionError(f"{type(record).__name__} is not frozen")
    assert hash(universe) == hash(dataclasses.replace(universe)) and hash(RULE) == hash(dataclasses.replace(RULE))


def test_universe_top_n_takes_the_largest_medians():
    universe = rules.verify_universe_snapshot(rules.encode_universe_snapshot(RULE, D, _receipts())[0], RULE_SHA)
    assert rules.universe_top_n(universe, 1) == ("KRW-BTC",)
    assert rules.universe_top_n(universe, 5) == ("KRW-BTC", "KRW-SOL")
    tied = dataclasses.replace(universe, eligible=(("KRW-ADA", Decimal(7)), ("KRW-BTC", Decimal("9.0")),
                                                   ("KRW-ETH", Decimal(9)), ("KRW-XRP", Decimal(8))))
    assert rules.universe_top_n(tied, 3) == ("KRW-BTC", "KRW-ETH", "KRW-XRP")      # equal medians: market ascending
    assert rules.universe_top_n(dataclasses.replace(universe, eligible=()), 3) == ()
    for n in (0, -1, True, 1.0, "1", None):
        _value_error(lambda: rules.universe_top_n(universe, n))


def test_universe_code_writes_and_reads_no_file():
    """Spec section 5: the universe code in core/compliance writes no files, and verification never loads a context."""
    home = Path(os.environ["TRADEGEN_HOME"])                    # the compliance wrapper's temporary home
    before = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
    raw, sha = rules.encode_universe_snapshot(RULE, D, _receipts())
    assert rules.verify_universe_snapshot(raw, RULE_SHA).snapshot_sha256 == sha
    assert sorted(p.relative_to(home).as_posix() for p in home.rglob("*")) == before
    banned = {"open", "read_bytes", "read_text", "write_bytes", "write_text", "mkdir", "Path", "os", "environ",
              "getenv", "state_root", "load_context", "now", "today", "time", "urlopen"}
    for fn in (rules._rule_body, rules._universe_json, rules.universe_rule_sha256, rules._unique, rules._no_constant,
               rules._strict_json, rules.flag_class, rules.market_flags, rules._typed, rules._midnight,
               rules._candle_request, rules._candidates, rules.universe_requests, rules._stamp, rules._receipt,
               rules._candles, rules._median, rules._eligible, rules.universe_eligible, rules.encode_universe_snapshot,
               rules.verify_universe_snapshot, rules.universe_top_n, rules._universe_rule, rules._count):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not names & banned, (fn.__name__, names & banned)
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `focus compliance compliance_universe/`
Expected: exit 1. The nine earlier tests PASS; `test_universe_is_a_frozen_record_with_the_contract_fields` fails with `AttributeError: module 'core.compliance.model' has no attribute 'Universe'`, `test_universe_top_n_takes_the_largest_medians` with `AttributeError: module 'core.compliance.rules' has no attribute 'verify_universe_snapshot'`, and the other three new tests with `AttributeError: module 'core.compliance.rules' has no attribute 'encode_universe_snapshot'`.

- [ ] **Step 3: Write the implementation**

3a. `core/compliance/model.py`: replace lines 17-18:

```python
if TYPE_CHECKING:
    from core.compliance.rules import InstrumentMap, RulesTable, VenueFacts
```

with:

```python
if TYPE_CHECKING:
    from decimal import Decimal

    from core.compliance.rules import InstrumentMap, RulesTable, VenueFacts
```

and insert after `SessionState` (after line 161, `    armed: bool = False`), keeping two blank lines before `Context`:

```python


@dataclass(frozen=True, kw_only=True)
class Universe:
    """One verified daily Upbit KRW universe snapshot (universe spec section 5), as rules.verify_universe_snapshot
    returns it; `eligible` is sorted by market, each with its median daily KRW value."""
    day: date                                         # candle day D (UTC)
    rule_sha256: str                                  # universe_rule_sha256 of the signed rule
    snapshot_sha256: str                              # the file's manifest sha256, also its file name
    built_at: datetime                                # the latest receipt server time
    valid_from: datetime                              # max(built_at, D 00:40 UTC)
    valid_until: datetime                             # D+1 00:40 UTC (09:40 KST)
    listed: tuple[str, ...]
    eligible: tuple[tuple[str, Decimal], ...]
```

3b. `core/compliance/rules.py`: in the `TYPE_CHECKING` block (line 25 at fd85850), replace:

```python
    from core.compliance.model import ApprovedState
```

with:

```python
    from core.compliance.model import ApprovedState, Universe
```

3c. Append to the end of the universe section in `core/compliance/rules.py` (after `universe_eligible`, before the `--check` banner), two blank lines before:

```python
_SNAPSHOT_KEYS = frozenset({"day", "rule", "receipts", "manifest_sha256"})


def encode_universe_snapshot(rule: UniverseRule, day: date, receipts: Sequence[Mapping]) -> tuple[bytes, str]:
    """The snapshot file bytes and their manifest sha256, which is also the file name (owner.universe_path). The file
    is the universe JSON of {day, rule, receipts in request order, manifest_sha256}, and the manifest is the sha256 of
    that JSON without manifest_sha256. Refuses the receipts universe_eligible refuses. Writes nothing:
    execution_launch/universe_store.py writes the file."""
    _eligible(rule, receipts, day)
    plain = sorted(({key: value[key] for key in _RECEIPT_KEYS} for value in receipts),
                   key=lambda receipt: (receipt["path"], receipt["params"]))
    body = {"day": day.isoformat(), "rule": _rule_body(rule), "receipts": plain}
    manifest = hashlib.sha256(_universe_json(body)).hexdigest()
    return _universe_json({**body, "manifest_sha256": manifest}), manifest


def verify_universe_snapshot(raw: bytes, rule_sha256: str) -> Universe:
    """A snapshot file -> the Universe it proves (universe spec section 5), or UniverseError with the first refusal:
    the file form and its manifest, the embedded rule in parsed form and its sha256 against the signed one, then
    universe_eligible. Pure: it never loads a context, reads a clock or opens a file."""
    from core.compliance.model import Universe                # lazy: no import cycle with model.py
    doc = _strict_json(raw, "UNIVERSE_MANIFEST_MISMATCH")
    try:
        if type(doc) is not dict or set(doc) != _SNAPSHOT_KEYS or _universe_json(doc) != raw:
            raise ValueError("not the snapshot's JSON form")
        manifest = hashlib.sha256(_universe_json({key: doc[key] for key in ("day", "rule", "receipts")})).hexdigest()
        if doc["manifest_sha256"] != manifest:
            raise ValueError("the manifest does not match")
        day = parse_date(doc["day"], "day")
    except (TypeError, ValueError, Invalid):                   # TypeError: a JSON fraction became a Decimal
        raise UniverseError("UNIVERSE_MANIFEST_MISMATCH") from None
    try:
        rule = _universe_rule(doc["rule"], "universe_rule", frozenset({"KRW"}))
    except Invalid:
        raise UniverseError("UNIVERSE_RULE_INVALID") from None
    if _rule_body(rule) != doc["rule"]:
        raise UniverseError("UNIVERSE_RULE_INVALID")           # not the parsed form (an unsorted exclude)
    if universe_rule_sha256(rule) != rule_sha256:
        raise UniverseError("UNIVERSE_RULE_MISMATCH")
    listed, eligible, built_at = _eligible(rule, doc["receipts"], day)
    opens = _midnight(day) + _IN_FORCE_AT
    return Universe(day=day, rule_sha256=rule_sha256, snapshot_sha256=manifest, built_at=built_at,
                    valid_from=max(built_at, opens), valid_until=opens + timedelta(days=1), listed=listed,
                    eligible=eligible)


def universe_top_n(universe: Universe, n: int) -> tuple[str, ...]:
    """The n eligible markets with the largest median daily value, largest first; equal medians by market."""
    if type(n) is not int or n < 1:
        raise ValueError("universe_top_n: n must be an int >= 1")
    ranked = sorted(universe.eligible, key=lambda pair: (-pair[1], pair[0]))
    return tuple(market for market, _ in ranked[:n])
```

- [ ] **Step 4: Run the tests to see them pass**

```bash
focus compliance compliance_universe/
focus compliance compliance_model/
focus compliance compliance_gate/
focus compliance compliance_tables/
focus compliance compliance_guards/
```

Expected: every command exits 0 with only PASS rows (`compliance_gate/test_gate_call_graph_has_no_clock_zone_file_or_socket` scans every def of `model.py`, `Universe` included).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/model.py core/compliance/rules.py tests/compliance_universe.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -F - <<'EOF'
Encode and verify the daily universe snapshot

encode_universe_snapshot returns the snapshot file bytes (the rule, the plain receipts and a
manifest sha256) and the manifest; verify_universe_snapshot checks the file form, the manifest,
the embedded rule and its sha256 against the signed one, recomputes universe_eligible and returns
the frozen model.Universe with valid_from = max(built_at, D 00:40 UTC) and valid_until =
D+1 00:40 UTC (universe spec section 5). universe_top_n ranks the eligible coins by median.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: the two `--stat` outputs are identical (three files).

---

### Task 5: Snapshot paths under the state root

**Files:**
- Modify: `core/compliance/owner.py` (insert after line 1060, the last line of `evidence_path()` at 1058-1060)
- Test: `tests/compliance_owner.py` (append after line 993)

**Interfaces:**
- Consumes: `owner.evidence_path()`, `owner._hex64(v) -> bool` (line 84), `core.isolation.state_root()`; test helpers `_home()`, `_same(a, b)`, `_raises(fn, exc_type, text)`, `_listing(root)`.
- Produces: `owner.universe_dir(day: date) -> Path` (`<state root>/universe/<YYYY-MM-DD>`) and `owner.universe_path(day: date, sha256: str) -> Path` (`<state root>/universe/<YYYY-MM-DD>/<sha256>.json`); both raise `ValueError` for a bad argument and create nothing.

- [ ] **Step 1: Write the failing test**

Append to the end of `tests/compliance_owner.py`:

```python


# --------------------------------------------------------------------------- #
# Upbit KRW universe PR 1, Task 5 (universe spec section 5 "Storage"): the snapshot paths under the state root
# --------------------------------------------------------------------------- #
from datetime import date as _u5_date  # noqa: E402

from core import isolation as _u5_isolation  # noqa: E402


def test_universe_paths_sit_under_the_state_root_and_create_nothing():
    home = _home()
    before = _listing(home)
    day, sha = _u5_date(2026, 11, 11), "0123456789abcdef" * 4
    assert _same(_u5_isolation.state_root(), home)
    assert _same(owner.universe_dir(day), home / "universe" / "2026-11-11")
    assert _same(owner.universe_path(day, sha), home / "universe" / "2026-11-11" / f"{sha}.json")
    assert _same(owner.universe_path(day, sha).parents[2], owner.evidence_path().parents[1])   # the same root
    for bad in ("2026-11-11", datetime(2026, 11, 11, tzinfo=timezone.utc), None, 20261111):
        _raises(lambda: owner.universe_dir(bad), ValueError, "day must be a date")
        _raises(lambda: owner.universe_path(bad, sha), ValueError, "day must be a date")
    for bad in (sha.upper(), sha[:-1], sha + "0", "g" * 64, None, 1):
        _raises(lambda: owner.universe_path(day, bad), ValueError, "sha256 must be 64 lower-case hex digits")
    assert _listing(home) == before and not (home / "universe").exists(), "computing a path must create nothing"
```

- [ ] **Step 2: Run the test to see it fail**

Run: `focus compliance compliance_owner/test_universe_paths`
Expected: exit 1, one FAIL row: `AttributeError: module 'core.compliance.owner' has no attribute 'universe_dir'`.

- [ ] **Step 3: Write the implementation**

In `core/compliance/owner.py`, insert after line 1060 (`    return state_root() / "execution" / "evidence.jsonl"`), keeping two blank lines before `def _evidence_row(` (line 1063):

```python


def universe_dir(day: date) -> Path:
    """`<state root>/universe/<YYYY-MM-DD>`: the folder of candle day D's snapshot files (Upbit KRW universe spec
    section 5 "Storage"). Creates nothing."""
    if type(day) is not date:
        raise ValueError("universe_dir: day must be a date")
    return state_root() / "universe" / day.isoformat()


def universe_path(day: date, sha256: str) -> Path:
    """`<state root>/universe/<YYYY-MM-DD>/<sha256>.json`, under the same root as evidence_path(); the name is the
    snapshot's manifest sha256, and only execution_launch/universe_store.py writes there. Creates nothing."""
    if not _hex64(sha256):
        raise ValueError("universe_path: sha256 must be 64 lower-case hex digits")
    return universe_dir(day) / f"{sha256}.json"
```

- [ ] **Step 4: Run the tests to see them pass**

```bash
focus compliance compliance_owner/
focus compliance compliance_guards/
```

Expected: both exit 0 with only PASS rows (`compliance_owner/` is its 52 earlier tests plus the new one).

- [ ] **Step 5: Commit**

```bash
git add core/compliance/owner.py tests/compliance_owner.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -F - <<'EOF'
Add the universe snapshot paths under the state root

owner.universe_dir(D) and owner.universe_path(D, sha256) name <state root>/universe/<D>/<sha256>.json,
next to evidence_path(), and create nothing (universe spec section 5 "Storage"). Only the PR 2
writer will write there.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

Expected: the two `--stat` outputs are identical (two files).

---

### Task 6: Guards, full suite and the pull request

**Files:**
- Create (outside the repo): `$SCRATCH/pr1_body.md` (the PR body)
- No repo file changes.

**Interfaces:**
- Consumes: every name produced by Tasks 1 to 5.
- Produces: a pushed branch `claude/universe-pr1-compliance-pure` and one open PR against `main`. The owner merges it; never merge it.

- [ ] **Step 1: Run the guards and the touched suites**

```bash
focus compliance compliance_
focus control control_guards/
focus accounts accounts_guards/
focus launch launch_guards/
focus execution execution_guards/
focus odds odds_
```

Expected: every command exits 0 with no FAIL row, except the two checkout-location rows noted before Task 1 (see "Running tests"). `control_guards/` also runs `tests/renewal_boundaries.py` (`tests/control_guards.py:196-201`); `odds_` covers every reader of `Venue`. Checked in memory at planning time against fd85850 with Tasks 1 to 5 applied: compliance 368 tests (20 new), `control_guards` 13, `accounts_guards` 11, `launch_guards` 16, `execution_guards` 24, `odds_` 287, no FAIL beyond those two rows.

- [ ] **Step 2: Run the full suite, then restore its results file**

```bash
"$PY" -X utf8 -m tests.run_all > "$SCRATCH/pr1_full_suite.txt" 2>&1; echo "exit $?"
grep -c '^FAIL ' "$SCRATCH/pr1_full_suite.txt"
git restore qa/acceptance_results.json
git status --short
```

Expected: the `grep -c` count is `0`, or only the two checkout-location rows noted before Task 1 fail; `git status --short` lists only the untracked `docs/superpowers` files (the restore puts back the tracked results file the run rewrote; it is never committed). For any other FAIL row, check it on `origin/main` in a separate worktree:

```bash
git worktree add --detach ../pr1-main-check origin/main
(cd ../pr1-main-check && focus <suite> <module>/<test_name>)
git worktree remove ../pr1-main-check
```

A test that fails there too is pre-existing: add a bullet for it under "Unverified" in the PR body below, in the form "`<suite>/<module>/<test_name>` also fails on unmodified `main` (<its FAIL line>)", and do not fix it in this PR. Known candidate (PR 0's plan saw it on fd85850): `launch_owner_ops/test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle`. A test that fails only on this branch is a defect of this PR: stop, report it with its line from the output file, and do not push or open the PR.

- [ ] **Step 3: Check the branch**

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --stat --ignore-cr-at-eol origin/main...HEAD
```

Expected: five commits (Tasks 1 to 5); the two `--stat` outputs are identical and list exactly `core/compliance/model.py`, `core/compliance/owner.py`, `core/compliance/rules.py`, `research_notes/Korean resident trading venue legality/upbit_market_list.md`, `tests/compliance_acceptance.py`, `tests/compliance_owner.py`, `tests/compliance_tables.py`, `tests/compliance_universe.py`. `core/odds/venues.yaml` is not among them.

- [ ] **Step 4: Push and open the PR**

Write `$SCRATCH/pr1_body.md` with exactly this content, with two adjustments: delete the last "Unverified" bullet (the two checkout-location tests) if both passed in your runs, and add one bullet per pre-existing failure found in Step 2, in the form given there:

```markdown
## Summary

Upbit KRW universe, PR 1 of the stage 1 plan (design spec `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 4 and 5; section 19 item 1). Pure `core/compliance` code only:

- `rules.py`: the optional `universe_rule` key of the upbit venue with a strict sub-parser (`UniverseRule`, `Venue.universe_rule`) and `universe_rule_sha256` over the rule alone; the five flag classes (`flag_class`, `market_flags`); the exact request set (`universe_requests`); receipt and candle checks, finality from content and Decimal medians over calendar days with a missing day as zero (`universe_eligible`); the snapshot encode helper and `verify_universe_snapshot`, which returns a `Universe` in force from max(built_at, D 00:40 UTC) to D+1 00:40 UTC; `universe_top_n`.
- `model.py`: the frozen `Universe` record.
- `owner.py`: `universe_dir` and `universe_path` under the state root, next to `evidence_path()`; they create nothing.
- `research_notes/Korean resident trading venue legality/upbit_market_list.md`: records the rule's source URL, so a later `venues.yaml` may cite it.

## Not in this PR

- `core/odds/venues.yaml` is unchanged. No signed venues file carries `universe_rule` until the owner adds it and signs `approved {kind: venues}` after code-approve (spec section 16).
- No network read, snapshot writer or CLI (PR 2); no `Context.universe`, read-back or gate change (PR 3).

## Tests

- `tests/compliance_tables.py`: rule parsing (known keys only, today's closed-key failure for any other key, upbit only), value checks, the rule sha256, the research URL.
- `tests/compliance_universe.py` (new, registered in `tests/compliance_acceptance.py`): flag classes (a missing coin, a missing `market_event`, a missing or non-boolean key, an unknown caution key), the exact request set, finality from content, medians, receipt and candle checks, an added, dropped or swapped receipt, a tampered receipt or file, the rule sha mismatch, the in-force window, `universe_top_n`, and no file access.
- `tests/compliance_owner.py`: the universe paths create nothing.
- Guards: `compliance_guards`, `control_guards` (with `renewal_boundaries`), `accounts_guards`, `launch_guards`, `execution_guards`; the odds suite; the full suite with no FAIL.

## Unverified

- The Upbit facts come from the design's record of Upbit's developer docs (checked 2026-11-11); no API call was made. The candle fields read (`market`, `candle_date_time_utc`, `candle_acc_trade_price`) and whether Upbit skips daily candles on zero-trade days are measured in spec section 17 before any freeze.
- The code hash changes, so the owner code-approves again before any signed use.
- Every `ctx_hash` and `decision_id` changes value once, because `Venue` gains the `universe_rule` field (written as `null` when absent). Both are recomputed in-process only; no stored digest, profile, protocol, program or session changes.
- `compliance_guards/test_cryptography_is_pinned_installed_and_usable` and `compliance_signer/test_commands_sign_exactly_what_was_shown` were run from a checkout without its own `.venv`, where they fail on unmodified `main` too (they require the checkout's own interpreter).

This is software design, not legal, tax or investment advice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Then:

```bash
git push -u origin claude/universe-pr1-compliance-pure
gh pr create --base main --head claude/universe-pr1-compliance-pure --title "Upbit KRW universe PR 1: signed rule, flag classes and snapshot verification" --body-file "$SCRATCH/pr1_body.md"
```

Expected: `gh` prints the PR URL. Report that URL. Do not merge, approve or enable auto-merge; the owner merges on GitHub.
