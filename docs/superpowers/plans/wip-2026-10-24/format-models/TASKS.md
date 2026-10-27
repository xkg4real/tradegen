# Compliance plan: task list (scope of each task; the drafter writes the full task text)

Spec section numbers refer to the rev 3.2 spec. "8.N" means spec section 8, compliance list item N.

## Task 1: Branch, package skeleton, compliance suite, static guards
- `git switch -c compliance-gate`.
- Create empty `core/compliance/__init__.py`.
- Add `"core.compliance.", "core.odds."` to `ACTING_MODULE_PREFIXES` in `core/ficc/context_log.py` (LF file; no
  wall-clock call may be added there: test_s4).
- Create `tests/compliance_acceptance.py` (contract section 3, including the `__main__` filter runner) and
  `tests/compliance_fixtures.py` with `temp_home()` only.
- Create `tests/compliance_guards.py`. Its tests scan every `core/compliance/*.py` (and `core/odds/*.py` when present):
  - raw text: no `private_key`, no `seed_phrase` (case-insensitive), no `CANO`;
  - AST: no def/async def named `transfer`, `withdraw` or `deposit_address`; no `.post/.put/.delete/.patch` calls;
    no `from core.engine import orders` or any `core.engine.orders` import;
  - the import allowlist (contract section 0);
  - the wall-clock scan (names, attributes, `from time import`, `monotonic`, `localtime`, `gmtime`), allowed only
    inside a FunctionDef named `main` in `rules.py` and `alerts.py`;
  - `seal_context` referenced only in `owner.py` (P5);
  - `core.ficc.context_log.static_isolation_report() == []`, plus a positive control:
    `scan_isolation({"core.compliance.gate": "from core.ficc import context_log\n"})` reports an import violation
    (check the real function name and signature in `core/ficc/context_log.py` before writing it);
  - `core/compliance/__init__.py` is 0 bytes.
  Each guard needs a positive control: a synthetic source string that must be caught.
- Register the suite in `tests/run_all.py` (CRLF): the import, the `compliance/` prefix in `tests()`, the `--suite`
  help text. Add the README suite-list mention at line 816. The README table row waits for Task 16.
- Verify: the compliance suite passes (guards only); `--suite cockpit`, `--suite macro` stay green.
  Restore `qa/acceptance_results.json` after each `--suite` run.

## Task 2: A0 isolation residual (spec section 4 "Isolation residual", 8.9 last bullet; P7, P8)
- `core/isolation.py`: `_env`, `_LINK_SCAN`, `checked_target`, `scan_links`, `state_root` (contract section 4).
- `config.py` (CRLF): `state_root()` delegates.
- Final-target checks, outside the swallowing try:
  - `data/krx/kis_client.py` `_store_token` (LF);
  - `data/krx/opendart_client.py` `_store_cache` (LF);
  - `core/quant/history.py` `_cached` write (CRLF);
  - `core/ficc/data.py` `_cache_put` (LF);
  - `grokteam/book.py` `write_cached`: the tmp file, the final path with `within=DATA`, and MANIFEST.jsonl (CRLF).
  State that `python -m grokteam.prereg` will now list book.py as changed, which is expected (book.py:11-14).
  Never touch `grokteam/out/frozen_book` or `PREREG_book.json`.
- `tests/compliance_isolation.py`:
  - fake QUANTGEN roots by swapping `core.isolation.QUANTGEN_STATE` / `QUANTGEN_REPO` (save/restore);
  - a junction via `_winapi.CreateJunction`; a hard link via `os.link`; a symlink via `os.symlink`, with
    `NotRun("REFDATA: symlink creation needs Developer Mode")` on OSError;
  - `checked_target` refuses each case and the `within` escape;
  - `scan_links` refuses each link case under a temp root, is memoised, and is cleared by `temp_home`;
  - `state_root()` honours `TRADEGEN_HOME` and refuses `~/.nextgen`;
  - each of the five writers, pointed at a hard-linked target, raises RuntimeError and leaves the linked file's
    bytes unchanged (patch `kis_client._TOKEN_PATH`, `opendart_client._CACHE_PATH`, `config.ficc_cache_dir`,
    `config.FICC_CACHE_TTL_SECONDS`, `book.DATA` with save/restore);
  - the existing tests `macro_m0_rules` (state paths) and grokteam selfcheck still pass.
- Run `--suite grokteam`, `--suite macro`, `--suite quant` and `--suite cockpit` afterwards (T-RO-02 re-execs
  kis_client; T-LEDGER-01).

## Task 3: Strict YAML loader, vocabulary, class derivation (spec 5.1, 5.2 "Loading"; 8.1 first bullet; 8.4 classes)
- `core/compliance/rules.py`: the vocabulary block, `Invalid`, `load_strict`, `parse_date`, `derive_class`.
- `tests/compliance_loader.py`:
  - duplicate keys, an anchor, an alias, an unquoted date, `.nan`, `.inf`, `15:30`, `0x1F`, `yes`/`no`, a BOM,
    non-UTF-8 bytes, a file over 256 KB and a non-mapping top level are each Invalid;
  - quoted dates and plain ints/floats/true/false/null load as expected;
  - `derive_class` covers every spec 5.1 rule: TQQQ (+3 index) -> etp_leveraged; 252670 (-2 index) -> etp_leveraged;
    SH (-1 index) -> etp_index_inverse; a single-stock -1 -> etp_single_stock; IBIT (crypto_spot) and GDLC
    (crypto_spot_basket) -> etp_crypto_spot; BITO (+1 crypto_futures) -> etp_crypto_futures_1x; -1 crypto_futures
    -> Invalid (P11); +1 index -> etp_1x; krx_share -> share; an ETP with no underlying -> Invalid.

## Task 4: Rules table, instrument map, venue file (spec 5.1 venue facts, 5.2; 8.1; P4, P9, P10, P12-P15)
- `core/compliance/rules.py`: Review, Row, RulesTable, Instrument, InstrumentMap, Venue, VenueFacts, parse_rules,
  parse_instruments, parse_venues, approved_state, file_sha256, calendar_sha256 (contract 6.3).
- `tests/compliance_tables.py`, using small inline fixture YAML strings (not the shipped files) for every violation:
  - every rule listed under "Row loader rules";
  - a D16 row without requires.live; `any` on an allow row; an out-of-vocabulary value; an unknown key;
  - the review cadence (31 days; affected_by);
  - matrix coverage 1..38 missing a number;
  - P10 declared class mismatch; GDLC mapped with a plain `basket` underlying -> Invalid (P10);
  - P9 duplicate symbol across a venue's sections;
  - a market base not in the map;
  - `approved_state` returns `invalid(...)` instead of raising, and its hashes are the raw sha256s;
  - `calendar_sha256` changes when one byte changes and is stable for the same bytes (use
    `tests.macro_m1_calendars.fixture_set().data_dir`).

## Task 5: The shipped tables (spec 5.3 seed rows, 5.1 venue facts; P1, P13-P17, P22, P23, P25)
- `core/compliance/kr_rules.yaml`: every seed row of spec 5.3, with the citation fixes of P25 from
  `map_digest.txt` (the "Matrix row N" facts give the URLs per matrix row; the "Disagreement:" facts give the fixes).
  - Exact sources and research paths for every row.
  - `reviews: [{date: "2026-10-23", by: claude-research, checked: "..."}]`.
  - Crypto, transfer and OKX rows: `review_by: "2026-11-22"`, `affected_by: ["2026-12-03"]`.
  - KR-TRANSFER-OUT and KR-OKX-SPOT: `effective_until: "2027-02-18"`, confidence low, the "about" noted in reason.
  - All other rows: `review_by: "2026-11-23"`.
  - `known_changes: ["2026-12-03", "2027-01-01", "2027-02-18"]`.
  - The KR-OKX-SPOT warning text from spec 5.2.
  - The whole file must be written out in the plan, not summarised.
- `core/compliance/instruments.yaml`:
  - krx: 005930, 069500, 252670, 114800;
  - us: TQQQ, SH, SPY, AAPL, IBIT, FBTC, ETHA, GDLC, EZPZ, BITO;
  - crypto: BTC, USDT, USDC.
  - Exact fields. `source` is an issuer or exchange URL where the repo or research has one; otherwise the literal
    string "UNVERIFIED: owner to confirm before approval". Do not invent URLs.
- `core/odds/venues.yaml`: kis, upbit, bithumb, coinone, korbit, okx with P22 facts.
- Tests appended to `tests/compliance_tables.py`:
  - the three shipped files parse VALID;
  - `union(matrix_rows) == {1..38}`;
  - every D16 row has requires.live;
  - every seed row id of spec 5.3 is present;
  - every known spot ETP derives etp_crypto_spot;
  - `rules.COST_BOOKS <= core.quant.instruments.INSTRUMENT_BOOKS.keys()` (the test may import core.quant);
  - every `sources` entry is an https URL or a repo-relative path that exists;
  - the KR-OKX-SPOT warning renders with `{cap}` filled and has no other slot.

## Task 6: Shared model (contract section 5; P2, P5)
- `core/compliance/model.py`, complete.
- Fixtures added to `tests/compliance_fixtures.py`: `shipped_bytes`, `approved`, `ctx`, `intent`.
- `tests/compliance_model.py`:
  - canonical_json is byte-equal to `core.ficc.macro_schema.canonical_json` on plain samples (the test may import it);
  - jsonable handles frozenset, tuple keys, date and nested dataclasses, and raises on NaN;
  - intent_hash is stable and changes with any field;
  - `seal_context` registers and `is_sealed` refuses a hand-built `Context(...)`;
  - `Decision.decision_id` changes with any field;
  - `ApprovedState.invalid` gives `state_hash == ""`;
  - `iso_utc` refuses naive datetimes.

## Task 7: decide(), steps 0-3 and the floor (spec 6.1, 6.2 steps 0-3 and 7, 5.2 hard-coded floor; 8.3, 8.4, 8.5)
- `core/compliance/gate.py`:
  - decide() wiring every step;
  - `_choose_state`, `_validate`, `_conduct`, `_classify`, `_combine`;
  - the floor constants and reason-ordering helper.
  - Steps 4-6 helpers (`_exit`, `_new_exposure`, `_transfer`) exist but fail closed with BLOCK "no row" until
    Task 8 replaces their bodies. Say this explicitly in the task.
- `tests/compliance_gate.py`:
  - every conduct tag and `when` predicate BLOCKs, exits included;
  - the floor still BLOCKs with every table row deleted (an ApprovedState built from a rules table with only one
    harmless row);
  - a fixed-seed property test: 2,000 random intents from the vocabulary with a conduct tag are all BLOCK, using
    `numpy.random.default_rng(23)` or `random.Random(23)` in the test;
  - classification of TQQQ, 252670, SH, IBIT, GDLC, BITO goes through the map;
  - credit BLOCK (D15), lend/borrow BLOCK;
  - fail-closed inputs (NaN, inf, negative, wrong type, a case variant "UPBIT", an unknown tag, inconsistent
    transfer fields, an unlisted market, a sell beyond holdings or beyond promised units, an option sell with no
    holding, an asset/multiple disagreeing with the map) are BLOCK "malformed: ...";
  - 5,000 fuzzed intents (random types incl. None, lists, huge floats) never raise;
  - a hand-built Context is BLOCK "state: context not from load_context".

## Task 8: decide(), steps 4-6 (spec 6.2 steps 4-6, D6, D11, D16; 8.6, 8.7)
- Replace the bodies of `_exit`, `_new_exposure`, `_transfer` in gate.py.
- Tests appended to `tests/compliance_gate.py`, all from spec 8.6 and 8.7, with dates and the Asia/Seoul boundary
  as ctx.date values:
  - 2026-12-02 ALLOW and 2026-12-03 BLOCK for OKX BTC buy, with ctx.date set from
    `datetime(2026,12,2,23,59,59,tzinfo=KST).date()` and `datetime(2026,12,3,0,0,0,tzinfo=KST).date()`;
  - OKX BTC->USDT sell on 2026-12-03 ALLOW_EXIT while USDT->BTC is BLOCK;
  - OKX->Upbit withdrawal ALLOW_EXIT with KR-DOMESTIC-SPOT stale and code_signed False;
  - wrong network or missing tag BLOCK (fixture venue file with a tag-required coin);
  - broken owner log: closing uses the snapshot and withdrawal is manual;
  - invalid active with a valid snapshot: a close-long passes;
  - no snapshot: "close manually";
  - conduct still blocks exits;
  - ack missing / wrong hash / other session -> ACK_REQUIRED;
  - unset cap / over cap (USDT held included) / missing age / auto-off -> BLOCK;
  - stale row BLOCKs new exposure;
  - D16 short with every owner flag set stays BLOCK (requires.live);
  - leverage above max_leverage BLOCK;
  - an Upbit -> OKX transfer needs the per-transfer ack and a registered address.

## Task 9: Permits, verify_permit, screen, warnings, purity (spec 6.3; 8.8; P3)
- gate.py: `permit`, `verify_permit`, `screen`, `render_warning`, `warning_sha256`.
- Tests:
  - verification excludes only the permit's own reservation;
  - two permits cannot share cap capacity;
  - forged permit / other intent / other session / other date refused;
  - a newer in-force state (higher seq) accepted; an older one refused;
  - screen() flags review_by / auto_off / effective_until inside [start, start+horizon) and sets exit_date;
  - screen() on a KRX share is allowed; on OKX it is ACK_REQUIRED-allowed when no ack;
  - purity: while `builtins.open`, `io.open`, `os.open`, `socket.socket.connect` and `time.time` are patched to
    raise (save/restore), decide/permit/verify_permit/screen run 200 varied intents without touching them;
  - an AST scan of gate.py finds no wall-clock call and no `ZoneInfo(` inside decide's call graph (no ZoneInfo
    anywhere in gate.py).

## Task 10: The cryptography dependency (spec 6.4 "The dependency"; owner approval gate)
- **Stop and ask the owner** before downloading: package `cryptography`, version `49.0.0`, source PyPI
  (https://pypi.org/project/cryptography/49.0.0/), the cp311-abi3-win_amd64 wheel (about 3 to 4 MB; state the
  actual size pip reports), installed into `.venv` only. Proceed only on an explicit yes.
- Add `cryptography==49.0.0`:
  - to `requirements.txt` (CRLF);
  - to `pyproject.toml` dependencies (CRLF);
  - to `constraints.txt` between `cookiecutter` and `curl_cffi` (CRLF line).
- Install: `.venv/Scripts/python.exe -m pip install "cryptography==49.0.0" -c constraints.txt`.
- Verify:
  - `pip freeze` diff shows only the new line;
  - `from_private_bytes`, `private_bytes_raw`, `public_bytes_raw`, `Scrypt` and `AESGCM` exist;
  - a sign/verify round trip works;
  - print the RECORD sha256.
- No new test module; the PENDING NotRuns from earlier tasks now run.

## Task 11: Owner log format and verification (spec 6.4 "The log", "Events"; 8.9; P20)
- `core/compliance/owner.py`: paths (8.1), constants, Entry, LogCheck, fingerprint, read_pubkey, verify_log,
  read_anchors, append_system_entry, the sidecar lock.
- `cryptography` is imported lazily inside the functions that need it. ImportError means LogCheck not ok
  ("cryptography missing: install it (Task 10)").
- Fixtures: `test_key`, `signed_entry`, `write_log`, `write_pubkey`.
- `tests/compliance_owner.py`:
  - a valid 5-entry log verifies;
  - an edited last line is caught;
  - a re-signed line with a wrong prev is caught;
  - an unsigned owner entry, and a signed system entry, are each caught;
  - a deleted system_halt (log shorter than an alerts.jsonl anchor) is caught;
  - a row_sha256 that differs from its snapshot anchor is caught;
  - non-canonical JSON (extra space) is caught;
  - duplicate JSON keys are caught;
  - a rotation signed by the old key verifies and moves the first-key fingerprint;
  - a rotation signed by the new key fails;
  - append_system_entry appends seq n+1 with the right prev and no sig, under the lock;
  - no line is written outside the temp home.

## Task 12: Owner state with D12 (spec 6.4 "Events", "D12"; D12; 8.9 loosening bullets)
- `owner.py`: `owner_state`, `in_force`, `history`, `code_approval`.
- Tests appended to `tests/compliance_owner.py`:
  - in_force takes the LATEST approval per kind, even when an older sha is re-listed later only as history;
  - a superseded hash restored later does not count unless re-signed as a new entry;
  - cap tighten applies at once;
  - cap loosen applies only from the next Asia/Seoul date;
  - a loosening is not applied while armed by an earlier session_armed;
  - a floor loosening below a system_halt floor is ignored;
  - daily-loss tighten and loosen;
  - age_of_majority flag from birth_date (19 years) at the boundary;
  - course and broker flags;
  - session armed/disarmed;
  - session acks and transfer acks collected;
  - addresses collected with tag "" for null;
  - KEY CHANGED when the first recorded fingerprint differs;
  - entries with a future utc ignored.

## Task 13: Approved store, code hash, snapshots, load_context (spec 5.2 "What is in force", 6.4; 8.2; P6, P19, P21, P24)
- `owner.py`: store_put, store_get, code_files, code_hash, write_snapshot, latest_snapshot, load_context.
- `core/compliance/owner_pubkey.pem` is NOT created (P24).
- Fixture: `store_blob`.
- `tests/compliance_store.py`:
  - no pubkey -> BROKEN "no owner key yet" and every new-exposure intent BLOCK;
  - a full temp home (test key, approvals for the shipped drafts stored, code_approved for the current
    code_hash) gives a context whose decide() ALLOWs an Upbit BTC buy;
  - a draft byte change blocks nothing until signed (the in-force bytes come from the store);
  - restoring an older approved file does not count; only the latest approved hash does;
  - an unsigned code hash (the latest code_approved names a different sha) blocks new exposure but not exits;
  - code_files lists exactly the expected closure for the current tree (core/__init__.py, core/isolation.py,
    core/compliance/*.py, plus venv RECORD entries) and contains no config.py and no data/;
  - a store blob whose bytes do not match its name is refused;
  - write-once store and snapshot (second put with other bytes errors);
  - load_context with a naive datetime raises ValueError;
  - positions validated: NaN equity, negative holding -> state invalid / BLOCK;
  - the snapshot is written after a successful load and used when the log is later broken.

## Task 14: --check CLI and alerts (spec 5.4; 8.2 exit 3/4 bullets; 8.10; P26)
- rules.py: `check`, `main`.
- `core/compliance/alerts.py`: `OWNER_ALERT_EMAIL`, `due`, `render`, `_toast`, `log`, `main`.
- `tests/compliance_cli.py`:
  - exit codes 0, 1, 2, 3 on temp homes built with the Task 13 fixtures and chosen `--today` dates;
  - 4 on an injected exception (patch owner.load_context to raise);
  - 4 on a missing cryptography (subprocess run with
    `python -c "import sys; sys.modules['cryptography'] = None; ..."`, env `TRADEGEN_HOME` = temp);
  - 4 on a bad `--today` and on an unknown flag;
  - the final stdout line is the JSON summary and matches the exit code;
  - draft-vs-in-force diff lists changed row ids;
  - alerts.due: daily on overdue and on 3/4; 14-day and 3-day thresholds once each; a missed run still alerts;
    a missing summary alerts;
  - render() output has no rule free text (insert a row with a unique reason sentence; assert it is absent);
  - log() rows carry head_seq/head_sha256/fingerprint;
  - `_toast` is patched in tests and never runs powershell;
  - alerts main with send true calls `_toast` once and logs "toast".

## Task 15: The owner-kept signer (spec 6.4 "Signing", "The key file"; 11 owner acts 1-2; 8.9 signer bullets; P27)
- `tools/signer/sign.py`, complete, standalone (stdlib + cryptography): keygen, approve (files and the calendar
  directory), code-approve, event, fingerprint; refusals in main(); typed code; passphrase rule; key-file format;
  store writes with anchors; the QUANTGEN refusal copy.
- `tests/compliance_signer.py` (loads the file with `importlib.util.spec_from_file_location`):
  - main() refuses under CLAUDECODE (present in this environment) and with non-TTY stdin, exit code non-zero and no
    file written;
  - the key file round-trips with n=2**17, r=8, p=1 and fails with a wrong passphrase;
  - a tampered header fails (AAD);
  - a 19-character passphrase is refused, 5 words accepted;
  - a signer-built log line equals `tests.compliance_fixtures.signed_entry` byte for byte and verifies with
    `owner.verify_log`;
  - signer `code_files(repo)` equals `owner.code_files(repo)`;
  - a signer store write equals `owner.store_put` layout;
  - the typed-code check rejects a burst.
- Also the owner-facing instructions block (owner acts 1-2 from spec 11) printed by `sign.py --help`.

## Task 16 (written by the coordinator, not a drafter)
Full suite with the overlap guard; README table row and Total line; commit `qa/acceptance_results.json`; memory and
hand-over notes; propose the 09:00 KST scheduled task (owner approval); the GPT checkpoint after 2026-10-30 14:40;
the plan-decision list P1-P27 copied into the plan.
