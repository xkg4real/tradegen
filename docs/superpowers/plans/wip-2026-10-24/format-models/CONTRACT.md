# Compliance plan: interface contract (binding for every task drafter)

Repo: `C:\Users\whydi\OneDrive\Desktop\TRADEGEN` (git, branch `main` at `b5603f5`).
Spec: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` rev 3.2. The owner approved it.
Repo facts: `scratchpad/map_digest.txt` (about 230 verified facts with file:line evidence). Read it for your area.

Everything below is fixed. If your task needs a name that is not here, define it inside your own module as a
private helper (leading underscore) and say so in the task's Interfaces block. Never rename anything here.

## 0. Global rules (every task obeys these; the plan copies them into "Global Constraints")

- Python is `C:/Users/whydi/OneDrive/Desktop/TRADEGEN/.venv/Scripts/python.exe` (3.13.14). Never `pip install`
  into the global Python. No pytest: a test is a zero-argument `test_*` function that raises on failure.
- Run one suite: `.venv/Scripts/python.exe tests/run_all.py --suite compliance` from the repo root. A suite run
  rewrites the TRACKED file `qa/acceptance_results.json`; restore it with `git checkout -- qa/acceptance_results.json`
  after every `--suite` run. Only the final full run (Task 16) commits it.
- Before every test command, check that no other python `run_all.py` is running (QUANTGEN shares the machine, and
  its Store Python runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it).
  It must print nothing; if it prints a process, wait; never run concurrently. PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`.
  Git Bash prefix (the PowerShell script in single quotes, so Bash does not expand `$_`):
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.
- New files are UTF-8, no BOM, LF line endings. Files that are CRLF today stay CRLF: `tests/run_all.py`,
  `README.md`, `config.py`, `requirements.txt`, `pyproject.toml`, `core/quant/history.py`, `grokteam/book.py`,
  `grokteam/selfcheck.py`; `constraints.txt` is mixed (line 1 LF, rest CRLF) and is edited with Python bytes I/O
  (Task 10), because the Edit tool turns its line 1 into CRLF. Edit other existing files only with the Edit tool.
  Never `sed -i`.
  Before each commit: `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`.
- Commit per task with the repo-local identity (already set) and end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Work on branch `compliance-gate` (Task 1 creates it).
- Guards that scan `core/**/*.py` (raw text includes docstrings and comments unless noted):
  - never write the upper-case letters `CANO` anywhere in core/ (so never `CANONICAL`; write `canonical` lower-case),
    nor `KIS_ACCOUNT`, `ACNT_PRDT_CD` (test_09, raw text);
  - never write `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`
    (test_08, raw text, case-insensitive; this also forbids e.g. "replace_order");
  - never write `private_key` or `seed_phrase` in core/ in any form, docstrings and comments included (T-RO-01 checks
    code; the compliance guard test added in Task 1 checks raw text). So never `load_pem_private_key`;
    use `load_pem_public_key`, `Ed25519PublicKey`;
  - never CALL a function named `transfer`, `withdraw`, `deposit_address`, `sign_transaction` and the rest of
    FORBIDDEN_CALLS; never DEFINE a function or method named `transfer`, `withdraw` or `deposit_address`
    (Task 1 adds the def-name check);
  - never pass a string containing `order`, `withdraw`, `transfer` or `deposit` to any `.post/.put/.delete/.patch`
    call (this includes `dict`-like `.put`); core/compliance never uses those methods, nor `.request`, at all;
  - no star import, `__import__`, `importlib.import_module`, `exec`, `eval`, nor any import of `importlib.util`,
    `importlib.machinery`, `runpy`, `pkgutil` or `zipimport` in core/compliance (`importlib.metadata` is allowed).
    Core code probes for `cryptography` with a lazy `import` inside `try`/`except ImportError`;
    `importlib.util.find_spec` is for tests only;
  - never import `core.engine.orders` in any form, nor `core.quant.forward_sim`, `core.quant.refusal`,
    `core.ficc.context_log`, `core.ficc.macro`, `core.ficc.flows_log`, `core.skills.macro_daily`;
  - never write `r18_research_log`, `r18_break_log`, `context_log/`, `tests.reference`, `reference_mode`;
  - no wall-clock call (`datetime.now`, `utcnow`, `date.today`, `time.time`, `time.monotonic`, `time.localtime`,
    `time.gmtime`, `from time import ...`) anywhere in `core/compliance/` except inside the CLI `main()` functions of
    `rules.py` and `alerts.py` (Task 1's guard enforces this).
- **Import allowlist for `core/compliance/*.py`** (Task 1's guard enforces it): stdlib, `yaml`, `cryptography`
  (only inside functions, lazily), `core.isolation`, `core.compliance.*`. Nothing else: not `config`, not numpy,
  not `core.quant.*`, not `core.ficc.*`, not `core.rules.*`, not `core.calendars.*`. This keeps the D14 signed
  code closure tiny (section 6). Tests may import anything.
- `core/compliance/__init__.py` stays empty (0 bytes). `python -m core.compliance.rules` blocks are exactly
  `if __name__ == "__main__":\n    raise SystemExit(main())`.
- Every `open`/`read_text`/`write_text` passes `encoding="utf-8"` (or uses bytes). CLI JSON lines use
  `json.dumps(..., ensure_ascii=True)`; CLIs reconfigure stdout to UTF-8 like `tests/run_all.py:35-39`.
- Every file the compliance code writes goes through `core.isolation.checked_target(path, what)` immediately
  before opening it (A0), temp/lock files included.
- Claude never runs the signer with a real key, never asks for a passphrase, never writes to the real
  `~/.tradegen/compliance/owner.jsonl`. Tests build owner logs only inside a temp `TRADEGEN_HOME`, with a test key.

## 1. Decisions this plan makes where the spec is silent, ambiguous, or would break a guard

Each task that implements one of these cites it as "Plan decision P<n>". **The authoritative list is the plan
header's P1 to P39**, which includes the amended P16, P20 and P25 and the decisions P28 to P39 that the tasks added.
The original P1 to P27 as first drafted follow.

- P1 `venues.yaml` stays at `core/odds/venues.yaml` (spec location) but is created by the compliance plan with only
  `sections`, `settlement`, `markets`/`quote`, `deposits`. The odds plan adds lots, minimums and ticks later (that
  changes its sha256, so the owner re-approves). No `core/odds/__init__.py` is created here.
- P2 Shared types live in a new `core/compliance/model.py` (pure, stdlib only), so `gate.py`, `owner.py` and
  `rules.py` share them without cycles.
- P3 `screen(plan, ctx, first_stake_krw)` is duck-typed: it reads `plan.leg.venue`, `plan.leg.symbol`, `plan.start`
  (a `date`) and `plan.horizon_days` (an `int`) only. `core/odds/plan.py` is the odds plan's job.
- P4 Optional row field `max_leverage` (number > 0, default 1.0). Effective leverage of an intent is
  `abs(multiple)` for `financing: cash` and is BLOCK above the matched row's `max_leverage` (spec 6.2 step 5).
- P5 Hand-built contexts: `model.seal_context(**fields)` registers the instance in a module-private
  `weakref.WeakValueDictionary`; `decide()` and `verify_permit()` BLOCK any context for which
  `model.is_sealed(ctx)` is False ("state: context not from load_context"). Only `core/compliance/owner.py` may
  reference `seal_context` inside core/ (Task 1's guard). This is discipline, not security.
- P6 The D14 code closure counts module-level AND function-level imports (TYPE_CHECKING and `__main__` bodies
  skipped), adds every ancestor package `__init__.py`, and adds the `RECORD` files of the `cryptography` and `PyYAML`
  dists. Because of the import allowlist, the closure is `core/__init__.py`, `core/isolation.py`,
  `core/compliance/*.py` (plus `core/odds/*.py` later). The data loaders A0 edits are NOT in it.
- P7 `core/isolation.py` gains `state_root()`; `config.state_root()` returns `core.isolation.state_root()`.
  The link scan raises `RuntimeError` (fail closed), memoised per resolved root; a root that does not exist yet is
  not memoised. The scan walks the effective root (`TRADEGEN_HOME` when set). Overrides outside it are covered by
  the per-writer `checked_target`.
- P8 A0 final-target checks run OUTSIDE the existing swallowing `try` blocks, so a refusal propagates. Reads stay as
  they are (the state-root scan covers in-root links). gate_ledger/governance stay out of A0 (residual, noted).
- P9 Instrument map is namespaced into sections `krx`, `us`, `crypto`; `venues.yaml` names each venue's sections.
  A symbol listed twice within the sections of one venue makes the venue file INVALID.
- P10 Each map entry stores a declared `class`; the map is INVALID when it differs from the derived class. Known
  spot-crypto ETP tickers (`IBIT`, `FBTC`, `ARKB`, `ETHA`, `GDLC`, `EZPZ`) in section `us` must derive
  `etp_crypto_spot`, or the map is INVALID.
- P11 Derivation rules 3 and 4 exclude `crypto_futures` underlyings; a crypto-futures ETP with multiple != +1 fits
  no class, so the map is INVALID (no research covers inverse/geared bitcoin-futures ETFs).
- P12 Match keys: `venue`, `asset`, `class`, `action`, `financing`, `tag` (any overlap), `when` (conduct
  predicates `route_not_direct`, `on_behalf_not_self`, `publishes_signal`). `KR-KIS-KRX-SHARE` and
  `KR-KIS-US-SHARE` match on `asset` (`krx_share`, `us_share`).
- P13 `basis` vocabulary is `legal`, `policy`, `platform` (platform-term blocks are labelled honestly).
- P14 Row fields `matrix_rows: [ints]` (may be empty) and `research: [strings]` replace the single research string;
  the 38-row coverage test is `union(matrix_rows) == {1..38}`.
- P15 Row field `affected_by: ["YYYY-MM-DD", ...]` (each must be in the table's `known_changes`): `review_by` must be
  at most 31 days after the latest review AND before the first `affected_by` date after that review.
- P16 `effective_from` is the date of the earliest cited source that establishes the treatment.
- P17 `KR-CONDUCT-SPORTS` matches every venue (the floor blocks `sports_bet` everywhere anyway, and Betman is
  out_of_scope under D10); the spec's "except betman" carve-out is dropped as unreachable.
- P18 `counter_symbol` defaults to `""`. It must be non-empty and form a listed market for `buy`, `sell`,
  `sell_short`, `buy_to_cover`, `write`, `p2p_buy`, `p2p_sell`; it must be `""` for `transfer_out`, `lend`,
  `borrow`.
- P19 `load_context(now, positions, *, session_id=None)`: `positions` (equity, holdings, shorts, venue exposure,
  reservations) is supplied by the caller until the execution spec adds live reads; `load_context` validates it
  (finite, >= 0, equity > 0) and hashes it into `ctx_hash`. Everything else is derived inside.
- P20 Key rotation: a `key_rotated` owner entry, signed by the old key, carries the new raw public key. The verifier
  walks rotations backwards from the repo `owner_pubkey.pem` to find the first key; the first fingerprint recorded in
  `alerts.jsonl` must equal that first key's fingerprint, else "KEY CHANGED since <date>".
- P21 The calendar approval covers every regular file in `core/calendars/data/` (17 files including `MANIFEST.yaml`
  and `market_closes.yaml`); `data/calendars/*.json` is excluded.
- P22 Upbit seed markets are KRW-quoted only: (BTC, KRW), (USDT, KRW). OKX: (BTC, USDT), (BTC, USDC).
  Deposits seed: upbit BTC on `bitcoin` (no tag), okx BTC on `bitcoin` (no tag); every other venue has none, so a
  withdrawal there fails closed. The missing-tag test uses a fixture venue file.
- P23 `KR-STATE-BLOCKED` lists only the 10 named ids; the other 17 KCSC sites fall under "unknown venue = BLOCK".
- P24 The shipped tree has no `owner_pubkey.pem` until owner act 1. Without it `load_context` returns owner state
  BROKEN("no owner key yet: owner act 1"), every new-exposure intent is BLOCK and `--check` exits 3.
- P25 Seed rows fix the citation mismatches the research mapping found (GOPAX, DRIFT, SHORT, KRX-DERIV, the conduct
  rows, OKX sources); see `map_digest.txt` "Disagreement:" facts.
- P26 The Windows toast is a `powershell.exe` subprocess behind the seam `alerts._toast(title, body) -> bool`.
- P27 The signer's "typed, not pasted" check rejects a code whose characters arrive less than 30 ms apart on
  average (a paste arrives in one burst); marked `# ponytail:` with its ceiling.

## 2. Files

```
core/isolation.py                 (modify; Task 2)   state_root, scan_links, checked_target
config.py                         (modify; Task 2)   state_root delegates
data/krx/kis_client.py, data/krx/opendart_client.py, core/quant/history.py, core/ficc/data.py, grokteam/book.py
                                  (modify; Task 2)   final-target checks
core/ficc/context_log.py          (modify; Task 1)   ACTING_MODULE_PREFIXES += ("core.compliance.", "core.odds.")
core/compliance/__init__.py       (create, empty; Task 1)
core/compliance/rules.py          (create; Tasks 3, 4, 14)
core/compliance/model.py          (create; Task 6)
core/compliance/gate.py           (create; Tasks 7, 8, 9)
core/compliance/owner.py          (create; Tasks 11, 12, 13)
core/compliance/alerts.py         (create; Task 14)
core/compliance/kr_rules.yaml     (create; Task 5)
core/compliance/instruments.yaml  (create; Task 5)
core/odds/venues.yaml             (create; Task 5)
tools/signer/sign.py              (create; Task 15)
tests/compliance_acceptance.py    (create; Task 1)  aggregator: tests()
tests/compliance_fixtures.py      (create; Task 1, extended by later tasks)
tests/compliance_guards.py        (Task 1)          static guards over core/compliance
tests/compliance_isolation.py     (Task 2)
tests/compliance_loader.py        (Task 3)
tests/compliance_tables.py        (Tasks 4, 5)
tests/compliance_model.py         (Task 6)
tests/compliance_gate.py          (Tasks 7, 8, 9)
tests/compliance_owner.py         (Tasks 11, 12)
tests/compliance_store.py         (Task 13)
tests/compliance_cli.py           (Task 14)
tests/compliance_signer.py        (Task 15)
tests/run_all.py, README.md       (modify; Task 1, Task 16)
requirements.txt, pyproject.toml, constraints.txt (modify; Task 10)
```

## 3. Test harness (Task 1 creates; later tasks only append module names / fixtures)

`tests/compliance_acceptance.py`:
```python
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer")
def tests() -> list[tuple[str, Callable[[], None]]]
```
- Imports each `tests.<module>` lazily inside `tests()`. A module that does not exist yet is skipped silently
  (so Task 1 can list all ten); a module that exists but fails to import yields one entry
  `("<module>/import", fn)` whose fn re-raises the import error.
- Each `test_*` function becomes `("<module>/<name>", wrapped)`, sorted by name within a module, modules in
  MODULES order. `wrapped()` runs `fn()` inside `tests.macro_acceptance.hermetic()` and
  `tests.compliance_fixtures.temp_home()`, and afterwards asserts that a listing of the REAL
  `Path.home() / ".tradegen" / "compliance"` (relative path, size, mtime_ns) is unchanged.
- `if __name__ == "__main__":` runs the entries whose name contains `sys.argv[1]` (all entries when no argument)
  with `tests.run_all.run`, prints `<passed>/<total> passed, <failed> failed, <not run> not run`, and exits 0 only
  when there is at least one entry and none failed. It does NOT write `qa/acceptance_results.json`.
- So the per-step test command in every task is
  `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/<test_name>` (one test) or
  `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/` (one module). Expected FAIL output names the
  test and the exception; expected PASS output ends `N/N passed, 0 failed, 0 not run`.
  Run the QUANTGEN overlap check (section 0) before each command.
- Tests that need `cryptography` before Task 10 has installed it raise
  `tests.notrun.NotRun("PENDING: cryptography not installed (Task 10)")`; after Task 10 they must pass, and Task 16
  asserts there is no PENDING NOT_RUN left in the compliance suite.

`tests/compliance_fixtures.py` (Task 1 creates `temp_home`; Tasks 6, 11, 13 add the rest):
```python
@contextlib.contextmanager
def temp_home() -> Iterator[Path]
    # mkdtemp(prefix="tradegen_home_"); sets os.environ["TRADEGEN_HOME"]; clears core.isolation._LINK_SCAN;
    # yields the Path; restores the previous value (pop if None) and clears _LINK_SCAN again in finally;
    # removes the temp dir with shutil.rmtree(ignore_errors=True).
def shipped_bytes(kind: str) -> bytes            # Task 6: "rules"|"instruments"|"venues" -> bytes of the shipped draft
def approved(rules=None, instruments=None, venues=None, *, seq=3, history=()) -> ApprovedState  # Task 6
def ctx(**overrides) -> Context                    # Task 6: a sealed Context for gate tests (see section 5.4)
def intent(**overrides) -> Intent                  # Task 6: default = upbit BTC buy for KRW, quantity 0.001, notional 50_000
def test_key() -> "Ed25519PrivateKey"              # Task 11: from_private_bytes(bytes(range(32))), cached; imports cryptography lazily
def signed_entry(key, seq, prev_sha256, kind, data, utc="2026-10-23T00:00:00Z") -> bytes   # Task 11: one log line
def write_log(home: Path, entries: list[tuple[str, dict]], key=None) -> list[bytes]          # Task 11
def write_pubkey(path: Path, key=None) -> None                                               # Task 11
def store_blob(home: Path, kind: str, raw: bytes, anchor: tuple[int, str]) -> str           # Task 13: returns sha256
```

## 4. `core/isolation.py` additions (Task 2; stdlib only)

```python
_LINK_SCAN: dict[str, str | None] = {}     # resolved root -> None (clean) or the refusal message

def _env(name: str) -> str                  # os.environ value stripped; surrounding quotes removed; "<...>" -> ""
def checked_target(path, what: str = "path", *, within=None) -> Path
    # refuse_quantgen(path, what); then RuntimeError if Path(path).is_symlink() or Path(path).is_junction();
    # if the path exists, is not a directory and os.lstat(path).st_nlink > 1: RuntimeError (hard link);
    # with `within`: RuntimeError unless Path(path).resolve().is_relative_to(Path(within).resolve()).
    # Returns Path(path). Never creates anything.
def scan_links(root) -> None
    # memoised by str(Path(root).resolve()); if root does not exist: return (not memoised);
    # walks os.walk(root, followlinks=False) with lstat: a symlink, a junction, or a non-directory with
    # st_nlink > 1 -> memo the message and raise RuntimeError(message naming the entry); clean -> memo None.
    # A memoised message raises again on every call.
def state_root() -> Path
    # root = refuse_quantgen(_env("TRADEGEN_HOME") or Path.home() / ".tradegen", "TRADEGEN_HOME");
    # scan_links(root); return root
```
`config.state_root()` becomes `return _isolation.state_root()` (import `core.isolation` as `_isolation`; keep the
existing `from core.isolation import QUANTGEN_REPO, QUANTGEN_STATE, refuse_quantgen` line).

## 5. `core/compliance/model.py` (Task 6; pure, stdlib only)

### 5.1 Constants and helpers
```python
ALLOW, ALLOW_EXIT, ACK_REQUIRED, BLOCK = "ALLOW", "ALLOW_EXIT", "ACK_REQUIRED", "BLOCK"
KST = zoneinfo.ZoneInfo("Asia/Seoul")      # built at import, never inside decide()
def canonical_json(obj) -> str             # json.dumps(jsonable(obj), sort_keys=True, separators=(",", ":"),
                                           #            ensure_ascii=False, allow_nan=False)
def sha256_hex(data: bytes | str) -> str   # str is encoded UTF-8
def jsonable(obj)                          # dataclass -> dict of fields (recursively); Mapping -> dict with keys
                                           # str(k) or "|".join(k) for tuple keys; set/frozenset -> sorted list;
                                           # tuple/list -> list; date -> isoformat(); float must be finite
                                           # (ValueError otherwise); str/int/bool/None as is; anything else TypeError
def iso_utc(moment: datetime) -> str       # aware datetime -> "%Y-%m-%dT%H:%M:%SZ"; naive -> ValueError
```

### 5.2 Dataclasses (all `@dataclass(frozen=True, kw_only=True)`)
```python
class Intent:
    venue: str; symbol: str; counter_symbol: str = ""; asset: str; multiple: float; action: str
    financing: str = "cash"; quantity: float; notional_krw: float
    destination_venue: str | None = None; destination_address: str | None = None
    destination_network: str | None = None; destination_tag: str | None = None
    route: str = "direct"; on_behalf: str = "self"; publishes_signal: bool = False
    tags: frozenset = frozenset(); reservation_id: str | None = None

class Exposure:
    held_krw: float                                   # KRW value of everything held on the venue (settlement included)
    reservations: Mapping[str, float] = field(default_factory=dict)        # reservation_id -> notional_krw
    promised_sell_units: Mapping[str, float] = field(default_factory=dict) # symbol -> units promised to unexpired sell permits

class Positions:                                      # caller-supplied (P19)
    equity_krw: float
    holdings: Mapping[tuple[str, str], float] = field(default_factory=dict)   # (venue, symbol) -> units
    shorts: Mapping[tuple[str, str], float] = field(default_factory=dict)
    exposure: Mapping[str, Exposure] = field(default_factory=dict)            # venue -> Exposure

class ApprovedState:
    valid: bool; reason: str = ""
    rules: "RulesTable | None" = None; instruments: "InstrumentMap | None" = None; venues: "VenueFacts | None" = None
    hashes: Mapping[str, str] = field(default_factory=dict)   # "rules"|"instruments"|"venues" -> sha256
    seq: int = 0                                     # largest owner-log seq among the three approvals in force
    history_maps: tuple = ()                         # earlier approved InstrumentMaps, newest first
    @classmethod
    def invalid(cls, reason: str) -> "ApprovedState"
    @property
    def state_hash(self) -> str                      # sha256_hex(canonical_json({"hashes": hashes, "seq": seq})); "" if not valid

class OwnerState:
    status: str                                      # "OK" | "BROKEN"
    reason: str = ""
    head: tuple[int, str] = (0, "")                  # (seq, row_sha256) of the last line
    caps: Mapping[str, float] = field(default_factory=dict)          # effective after D12, e.g. {"okx_equity_share": 0.1}
    limits: Mapping[str, float] = field(default_factory=dict)        # {"total_loss_floor_krw": .., "daily_loss_krw": ..}
    addresses: frozenset = frozenset()              # {(venue, symbol, network, address, tag_or_empty)}
    flags: frozenset = frozenset()                  # met `requires.owner` items, e.g. "age_of_majority"
    halted_floors: frozenset = frozenset()          # floor_krw values from system_halt entries
    armed_sessions: frozenset = frozenset()         # session ids armed and not disarmed
    session_acks: frozenset = frozenset()           # {(session_id, row_id, warning_sha256)}
    transfer_acks: frozenset = frozenset()          # {(intent_hash, warning_sha256)}
    fingerprint: str = ""                           # current owner key fingerprint
    @classmethod
    def broken(cls, reason: str, *, head=(0, ""), fingerprint="") -> "OwnerState"
    @property
    def ok(self) -> bool                             # status == "OK"

class SessionState:
    session_id: str | None = None; armed: bool = False

class Context:                                       # built ONLY through seal_context (P5)
    date: date                                       # Asia/Seoul date of the decision moment
    active: ApprovedState; snapshot: ApprovedState | None
    owner: OwnerState; code_hash: str; code_signed: bool; session: SessionState
    equity_krw: float
    holdings: Mapping[tuple[str, str], float]; shorts: Mapping[tuple[str, str], float]
    exposure: Mapping[str, Exposure]
    ctx_hash: str                                    # set by seal_context

class Decision:
    verdict: str; kind: str                          # kind: "close_long"|"cover_short"|"withdraw"|"new_exposure"|"malformed"
    reasons: tuple[str, ...]; warnings: tuple[str, ...] = ()
    intent_hash: str; state_hash: str; code_hash: str; owner_head: tuple[int, str]; ctx_hash: str
    date: date; decision_id: str                     # sha256_hex(canonical_json of every other field)
    ack: tuple[str, str] | None = None               # (row_id, warning_sha256) when verdict is ACK_REQUIRED

class Permit:
    decision_id: str; intent_hash: str; state_hash: str; state_seq: int
    session_id: str | None; reservation_id: str | None; date: date

class Screening:
    decision: Decision; allowed: bool                # verdict in (ALLOW, ACK_REQUIRED)
    flags: tuple[tuple[date, str, str], ...]         # (date, "review_by"|"auto_off"|"effective_until", row_id) in [start, start+horizon)
    exit_date: date | None                           # earliest flag date (the simulation exits there)
    screening_hash: str
```

### 5.3 Functions
```python
def intent_hash(intent: Intent) -> str                   # sha256_hex(canonical_json(intent))
def seal_context(**fields) -> Context                    # computes ctx_hash = sha256_hex(canonical_json(fields minus
                                                         # ctx_hash)), builds Context, registers it; P5
def is_sealed(ctx) -> bool                               # registry.get(id(ctx)) is ctx
```

### 5.4 Test fixtures built on model (Task 6 adds to compliance_fixtures)
`ctx(**overrides)` defaults: `date=date(2026, 10, 23)`, `active=approved()` built from the shipped drafts with
`seq=3`, `snapshot=None`, `owner=OwnerState(status="OK", head=(10, "a"*64), caps={"okx_equity_share": 0.10},
limits={"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}, flags=frozenset({"age_of_majority"}),
fingerprint="SHA256:test")`, `code_hash="c"*64`, `code_signed=True`, `session=SessionState(session_id="S1", armed=True)`,
`equity_krw=1_000_000.0`, `holdings={}`, `shorts={}`, `exposure={}`. It calls `model.seal_context`.

## 6. `core/compliance/rules.py` (Tasks 3, 4, 14)

### 6.1 Vocabulary (Task 3)
```python
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
```

### 6.2 Strict loader (Task 3)
```python
class Invalid(Exception):                    # .reason: str; str(exc) == reason
def load_strict(raw: bytes, what: str) -> dict
    # bytes > MAX_TABLE_BYTES -> Invalid(f"{what}: larger than 256 KB"); a UTF-8 BOM or non-UTF-8 -> Invalid;
    # any anchor or alias (yaml.parse event pass) -> Invalid; duplicate mapping key -> Invalid;
    # implicit resolvers restricted: bool only true/false, int only ^[-+]?[0-9]+$, float only decimal with optional
    # exponent (no .nan/.inf, no sexagesimal, no 0x/0o), null only null/~/empty; an unquoted timestamp -> Invalid
    # ("native date"); the top level must be a mapping. Uses a yaml.SafeLoader subclass (pure Python).
def derive_class(asset: str, multiple: float, underlying: str | None) -> str
    # spec 5.1 rules 1-7 with P11; raises Invalid("<asset> x<multiple> on <underlying> fits no class")
def parse_date(value, what: str) -> date    # a "YYYY-MM-DD" string -> date; anything else Invalid
```

### 6.3 Tables (Task 4)
```python
@dataclass(frozen=True, kw_only=True)
class Review: date: date; by: str; checked: str
@dataclass(frozen=True, kw_only=True)
class Row:
    id: str; kind: str                                   # "venue" | "conduct"
    match: Mapping[str, frozenset]                       # keys from P12; values are vocabulary members or {"any"}
    treatment: str; requires_owner: tuple[str, ...] = (); requires_live: tuple[str, ...] = ()
    ack: str | None = None; cap_key: str | None = None; auto_off: date | None = None; max_leverage: float = 1.0
    warning: str = ""; reason: str; basis: frozenset; policy_ref: str | None = None
    sources: tuple[str, ...]; research: tuple[str, ...]; matrix_rows: tuple[int, ...] = ()
    confidence: str; effective_from: date; effective_until: date | None = None; review_by: date
    reviews: tuple[Review, ...]; affected_by: tuple[date, ...] = ()
@dataclass(frozen=True, kw_only=True)
class RulesTable: schema: str; scope: str; known_changes: tuple[date, ...]; rows: tuple[Row, ...]
@dataclass(frozen=True, kw_only=True)
class Instrument:
    section: str; symbol: str; asset: str; multiple: float; underlying: str | None; cls: str
    cost_book: str | None; currency: str; tax_basis: str; source: str
@dataclass(frozen=True, kw_only=True)
class InstrumentMap:
    entries: Mapping[tuple[str, str], Instrument]        # (section, symbol) -> Instrument
    def lookup(self, sections: tuple[str, ...], symbol: str) -> Instrument | None
@dataclass(frozen=True, kw_only=True)
class Venue:
    id: str; sections: tuple[str, ...]; settlement: frozenset
    markets: frozenset                                   # {(base, quote)}; empty when quote_by_currency
    quote_by_currency: bool = False                      # kis: the counter must equal the instrument's currency
    default_quote: str | None = None                     # used by screen(); None when quote_by_currency
    deposits: frozenset = frozenset()                    # {(symbol, network, tag_required: bool)}
    def is_market(self, inst: Instrument, counter: str) -> bool
    def quote_for(self, inst: Instrument) -> str
@dataclass(frozen=True, kw_only=True)
class VenueFacts:
    venues: Mapping[str, Venue]

def parse_rules(raw: bytes) -> RulesTable                # raises Invalid; schema must be "tradegen.kr_rules/4"
def parse_instruments(raw: bytes) -> InstrumentMap       # raises Invalid; schema "tradegen.instruments/1"
def parse_venues(raw: bytes, instruments: InstrumentMap) -> VenueFacts   # raises Invalid; schema "tradegen.venues/1"
def approved_state(rules_raw: bytes, instruments_raw: bytes, venues_raw: bytes, *, seq: int,
                   history_raws: tuple[bytes, ...] = ()) -> ApprovedState   # never raises; invalid(reason) on error;
                   # hashes = sha256 of each raw; history_maps parsed from history_raws (unparseable ones skipped)
def file_sha256(raw: bytes) -> str
def calendar_sha256(data_dir: Path) -> str               # P21: sha256 over sorted (relpath POSIX + b"\0" + bytes + b"\0")
                                                         # of every regular file directly in data_dir
```
Row loader rules (Task 4 implements, each violation -> Invalid naming row id and field):
unknown keys; missing required keys; `match` keys outside P12; values outside vocabulary; `any` only on
`hard_block`/`out_of_scope` rows and conduct rows; `kind: conduct` rows are `hard_block`; `grey` rows need
`cap_key` and `auto_off` and `ack: per_session`; a row whose `policy_ref` is `D16` needs non-empty `requires_live`;
`requires.owner` items in OWNER_REQUIREMENTS, `requires.live` in LIVE_REQUIREMENTS; `warning` slots subset of
WARNING_SLOTS; `basis` non-empty subset of BASIS; `confidence` in CONFIDENCE; P15 review cadence; ids unique;
`matrix_rows` ints in 1..38. Table-level: `known_changes` sorted dates; the union of `matrix_rows` must be 1..38
(missing numbers listed in the reason).
YAML row shape (exact keys): `id, kind, match, treatment, requires: {owner: [...], live: [...]}, ack,
grey: {cap_key, auto_off}, max_leverage, warning, reason, basis, policy_ref, sources, research, matrix_rows,
confidence, effective_from, effective_until, review_by, reviews: [{date, by, checked}], affected_by`.
Required: id, kind, match, treatment, reason, basis, sources, research, confidence, effective_from, review_by,
reviews. Optional with defaults: requires, ack, grey, max_leverage, warning, policy_ref, matrix_rows,
effective_until, affected_by.

Instruments YAML: `schema: tradegen.instruments/1`, then `krx: {SYMBOL: entry}`, `us: {...}`, `crypto: {...}`;
entry keys exactly `asset, multiple, underlying, class, cost_book, currency, tax_basis, source`. ETP assets need an
underlying; non-ETP assets must have `underlying: null`. P10 checks. `cost_book` in COST_BOOKS or null (null only for
konex_share, us_option and other gate-only assets).

Venues YAML: `schema: tradegen.venues/1`, `venues: {id: {sections: [...], settlement: [...], markets: [[base, quote],
...] | quote_by_currency: true, default_quote: X, deposits: [{symbol, network, tag_required}], source: str}}`.
Ids in VENUES; sections in SECTIONS; every market base must be a symbol in one of the venue's sections; P9.

### 6.4 CLI (Task 14)
```python
def check(today: date, *, repo_root: Path | None = None) -> dict
    # returns {"code": int, "due": [..], "overdue": [..], "head_seq": int, "fingerprint": str, "lines": [str, ...]}
def main(argv=None) -> int
    # `--check [--today YYYY-MM-DD]`; exit 0 nothing due / 1 due within 14 days / 2 overdue / 3 invalid,
    # unapproved, unsigned code, broken log or KEY CHANGED / 4 the check itself failed (catches BaseException,
    # argparse errors via exit_on_error=False and SystemExit). Prints the human lines, then exactly one final
    # JSON line {"code","due","overdue","head_seq","fingerprint"} (ensure_ascii=True). The only wall clock is the
    # --today default, computed in main().
```
`check` imports `core.compliance.owner` inside the function (no import cycle).

## 7. `core/compliance/gate.py` (Tasks 7, 8, 9; pure)

```python
def decide(intent, ctx) -> Decision              # never raises; any internal exception -> BLOCK ("state: internal error <type>")
def permit(intent, ctx) -> Permit | None         # Permit only for ALLOW / ALLOW_EXIT
def verify_permit(p: Permit, intent, ctx_now) -> tuple[bool, str]
def screen(plan, ctx, first_stake_krw: float) -> Screening
def render_warning(row, slots: Mapping[str, str]) -> str      # row.warning with {cap} filled; unknown slot -> ""
def warning_sha256(row, slots) -> str                          # sha256_hex(render_warning(row, slots))
```
Internal step helpers (names fixed so Tasks 7-9 split cleanly; all private):
```python
_choose_state(intent, ctx) -> tuple[ApprovedState | None, str | None]   # step 0; (state, reason-if-none)
_validate(intent, ctx, state) -> tuple[Instrument | None, Venue | None, list[str]]   # step 1; malformed reasons
_conduct(intent, state) -> list[str]                            # step 2: conduct rows + all-intents floor
_classify(intent, ctx, inst, venue) -> str                      # step 3
_exit(intent, ctx, state, kind, inst, venue) -> tuple[str, list[str], list[str]]      # step 4 (verdict, reasons, warnings)
_new_exposure(intent, ctx, state, inst, venue) -> tuple[str, list[str], list[str], tuple | None]  # step 5 (+ack)
_transfer(intent, ctx, state, inst, venue) -> tuple[str, list[str], list[str], tuple | None]      # step 6
_combine(verdicts) -> str                                       # step 7: BLOCK > ACK_REQUIRED > ALLOW/ALLOW_EXIT
```
Floor constants (module level, Task 7):
```python
FLOOR_ALL_TAGS = rules.TAGS
FLOOR_ALL_ASSETS = frozenset({"event_contract", "sports_bet"})
FLOOR_NEW_VENUES = frozenset(rules.PREDICTION_VENUES) | {"sportsbook", "bitmart"} | frozenset(rules.STATE_BLOCKED)
FLOOR_NEW_ASSETS = frozenset({"fx_pair", "cfd", "overseas_future", "overseas_crypto_derivative"})
FLOOR_NEW_CLASSES = frozenset({"etp_crypto_spot"})
# plus: okx + (asset crypto_perp_or_future or action p2p_buy/p2p_sell); class option + action write
```
Reason strings (exact prefixes; tests match with `startswith`), strictest first in `Decision.reasons`:
```
"conduct: <row id or floor item>"        "floor: <item>"            "malformed: <field>"
"state: <why>"                           "unsigned code"            "no row"
"stale: review by <YYYY-MM-DD> passed (<row id>)"                   "hard_block: <row id>"
"out_of_scope: <row id>"                 "needs live broker evidence (execution spec): <row id>"
"requires <item>: <row id>"              "auto_off <YYYY-MM-DD>: <row id>"      "cap unset: <row id>"
"cap exceeded: <row id>"                 "leverage <x> above <max>: <row id>"   "ack required: <row id>"
"destination: <why>"                     "close manually in the broker app"
"withdraw manually in the exchange app"
```
Severity order for sorting reasons: conduct, floor, malformed, state, unsigned code, then everything else in the
order produced, ack required last.
Classification (step 3, spec 6.2):
- `close_long`: action `sell`, symbol not in `venue.settlement`, counter in `venue.settlement`, quantity within
  holdings minus `exposure[venue].promised_sell_units[symbol]`;
- `cover_short`: action `buy_to_cover`, quantity within `shorts`;
- `withdraw`: action `transfer_out`, destination in DOMESTIC_EXCHANGES, quantity within holdings minus promised,
  `(destination_venue, symbol, network, address, tag or "")` in `ctx.owner.addresses`, and the destination venue's
  deposits contain `(symbol, network, tag_required)` with a tag present iff required;
- `new_exposure`: everything else that is valid; `malformed` when step 1 found reasons.
Exits (step 4) ignore `code_signed` (spec test 6). Under `not ctx.owner.ok` a withdraw is BLOCK
"withdraw manually in the exchange app". A close with no usable state is BLOCK "close manually in the broker app".
Exit symbol lookup falls back to `state.history_maps` (newest first).
Grey cap: `exposure[venue].held_krw + sum(reservations except intent.reservation_id) + notional_krw >
cap * ctx.equity_krw` -> BLOCK "cap exceeded".
Ack: `(ctx.session.session_id, row.id, warning_sha256(row, slots)) in ctx.owner.session_acks`, slots
`{"cap": f"{cap:.0%}"}`; per-transfer: `(intent_hash(intent), warning_sha256(dest_row, slots)) in transfer_acks`.
Dates: rows in force when `effective_from <= ctx.date` and (`effective_until` is None or `ctx.date < effective_until`);
stale when `ctx.date > review_by`; auto-off BLOCK when `ctx.date >= auto_off`.
`verify_permit`: same intent hash, `decide(intent, ctx_now)` is ALLOW/ALLOW_EXIT, same session id, same
reservation id, same Asia/Seoul date, and `ctx_now.active.state_hash == p.state_hash` or
`ctx_now.active.seq > p.state_seq`. For the grey cap, `decide` already excludes only the intent's own reservation.
**Amended by Tasks 8 and 9:** `render_warning` and `warning_sha256` are defined in Task 8 (step 5's ack needs them);
`render_warning` never raises and renders any other or missing slot as `""`. Slots are `{"cap": f"{cap:.0%}"}`
when the cap is a number in (0, 1], else `{"cap": "the share you set"}`. Added reason spellings:
`"ack required: <row id> per transfer"` and the `destination: ...` texts listed in Task 8. The per-transfer ack is
required for every grey destination row (P38). `verify_permit` compares the state that `decide(intent, ctx_now)`
uses (`ctx_now.active`, or the snapshot for a snapshot exit; P35); the intent hash covers the reservation id; the
caller's promised sell units leave out the permit's own (P36). `screen()` decides on `ctx.date` and a plan must
start then (P37). Permits are registered process-locally like sealed contexts, so a hand-built or replaced Permit is
forged; the execution spec re-permits after a restart.

## 8. `core/compliance/owner.py` (Tasks 11, 12, 13)

### 8.1 Paths (call time, never module constants except PUBKEY_PATH)
```python
PUBKEY_PATH = Path(__file__).with_name("owner_pubkey.pem")   # tests swap this module attribute
def home() -> Path              # core.isolation.state_root() / "compliance"
def log_path() -> Path          # home() / "owner.jsonl"           (lock: str(log_path()) + ".lock")
def store_dir() -> Path         # home() / "approved"
def snapshots_dir() -> Path     # home() / "snapshots"
def alerts_path() -> Path       # home() / "alerts.jsonl"
```

### 8.2 Log format (Task 11)
```python
OWNER_KINDS = frozenset({"approved", "code_approved", "course_completed", "broker_approval", "age_of_majority",
    "cap_set", "limit_set", "withdrawal_address", "session_armed", "session_ack", "transfer_ack", "key_rotated"})
SYSTEM_KINDS = frozenset({"system_halt", "system_disarm"})
APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")
SIG_DOMAIN = b"tradegen-owner-log/1\n"
GENESIS_PREV = "0" * 64
```
- `body = {"seq": int, "prev_sha256": str, "utc": "YYYY-MM-DDTHH:MM:SSZ", "kind": str, "data": dict}`
- `row_sha256 = sha256_hex(canonical_json(body))`
- owner entries: `sig = base64.b64encode(signing_key.sign(SIG_DOMAIN + row_sha256.encode("ascii"))).decode("ascii")`;
  system entries carry no `sig` key.
- line bytes: `canonical_json({**body, "row_sha256": row_sha256, ["sig": sig]}).encode("utf-8") + b"\n"`.
- `prev_sha256` of seq 1 is GENESIS_PREV; otherwise the previous line's `row_sha256`.
- data schemas (exact keys; extra or missing keys -> BROKEN):
  `approved {kind, sha256}`; `code_approved {sha256, files: [[path, sha256], ...]}`;
  `course_completed {course, evidence}` (course in rules.OWNER_REQUIREMENTS); `broker_approval {item, evidence}`
  (item in rules.OWNER_REQUIREMENTS); `age_of_majority {birth_date, evidence}`; `cap_set {key, value}` (key
  "okx_equity_share", 0 < value <= 1); `limit_set {total_loss_floor_krw, daily_loss_krw}` (>= 0 and > 0);
  `withdrawal_address {venue, symbol, network, address, tag, evidence}` (tag str or null);
  `session_armed {session_id}`; `session_ack {session_id, row_id, warning_sha256}`;
  `transfer_ack {intent_hash, warning_sha256}`; `key_rotated {new_pubkey_b64}` (raw 32 bytes, base64);
  `system_halt {floor_krw}`; `system_disarm {session_id, reason}`.
  **Amended by Task 11:** `key_rotated {old_pubkey_b64, new_pubkey_b64}` (a signature does not reveal its key, so
  each rotation carries both); `withdrawal_address.tag` is a non-blank string, or null when there is none; venue ids
  are `rules.VENUES` members; `approved.kind` is one of APPROVAL_KINDS; `code_approved.files` is a non-empty list
  sorted by path with no repeats and `sha256 == sha256_hex(canonical_json(files))`; course and broker items exclude
  `age_of_majority`, which only an `age_of_majority` entry sets. Anchors everywhere are `(int >= 1, 64-hex)` or
  exactly `(0, "")`.
```python
@dataclass(frozen=True, kw_only=True)
class Entry: seq: int; utc: str; kind: str; data: Mapping; row_sha256: str; signed: bool
@dataclass(frozen=True, kw_only=True)
class LogCheck: ok: bool; reason: str; entries: tuple[Entry, ...]; head: tuple[int, str]; first_key_fingerprint: str
def fingerprint(pubkey_raw: bytes) -> str            # "SHA256:" + sha256_hex(pubkey_raw)
def read_pubkey(path: Path) -> bytes                 # PEM SubjectPublicKeyInfo -> raw 32 bytes (load_pem_public_key)
def verify_log(lines: list[bytes], pubkey_raw: bytes, anchors: list[tuple[int, str]]) -> LogCheck   # P20; never raises
def read_anchors() -> list[tuple[int, str]]          # from alerts.jsonl rows, snapshot files, store *.anchor.json files
def append_system_entry(kind: str, data: dict, now: datetime) -> tuple[int, str]
    # kind in SYSTEM_KINDS; takes the sidecar lock (msvcrt.locking / fcntl.flock, copied ~20 lines from
    # gate_ledger._exclusive), verifies the chain structure first (no signature check needed to append), appends
    # with fsync, returns (seq, row_sha256). checked_target on the log and lock paths.
```
BROKEN (spec 6.4) when: a bad signature on an owner entry; an unsigned line whose kind is not a system kind; a
signature on a system entry; a line that is not canonical JSON or whose row_sha256 does not recompute; seq not
consecutive from 1; a broken prev link; fewer than `seq` lines for some anchor; a line whose row_sha256 differs from
its anchor; an empty-file log is OK (no entries) but means nothing is approved.

### 8.3 Owner state (Task 12; pure)
```python
def owner_state(check: LogCheck, *, date: date, now_utc: str, session_id: str | None,
                fingerprint_now: str, first_recorded: tuple[str, str] | None) -> OwnerState
    # first_recorded = (fingerprint, utc) of the first alerts.jsonl row carrying one, or None.
    # BROKEN when check.ok is False, or when first_recorded is set and first_recorded[0] != check.first_key_fingerprint
    # ("KEY CHANGED since <utc date>"). Entries with utc > now_utc are ignored.
    # D12: caps and limits: a tightening applies from its entry; a loosening applies only when its Asia/Seoul date is
    # before `date`, and not while the session is armed by a session_armed entry that precedes it; a loosening of
    # total_loss_floor_krw below any system_halt floor_krw is ignored for good. Tighter = smaller cap, larger floor,
    # smaller daily loss.
    # flags: "age_of_majority" when birth_date + 19 years <= date; course_completed/broker_approval items.
    # armed_sessions: session_armed ids with no later system_disarm of the same id.
def in_force(check: LogCheck) -> dict[str, tuple[str, int]]     # kind -> (sha256, seq) of the LATEST approval per kind
def history(check: LogCheck, kind: str) -> list[tuple[str, int]] # earlier approvals of kind, newest first
def code_approval(check: LogCheck) -> str | None                  # sha256 of the latest code_approved
```

### 8.4 Store, code hash, snapshots, load_context (Task 13)
Store layout under `store_dir()`: `<kind>/<sha256>.yaml` for rules/instruments/venues (exact bytes);
`calendar/<sha256>/` directory holding the files; `<kind>/<sha256>.anchor.json` = canonical JSON `{"seq": n,
"row_sha256": s}`. Write-once: `open(path, "xb")`; when it exists, the bytes must be equal or it is an error.
```python
def store_put(kind: str, raw: bytes, anchor: tuple[int, str]) -> str          # returns sha256 (used by tests and signer format)
def store_get(kind: str, sha256: str) -> bytes | None                         # verifies sha256(bytes) == name
def code_files(repo_root: Path) -> list[tuple[str, str]]                      # P6, sorted (relpath POSIX, sha256)
def code_hash(repo_root: Path) -> str                                         # sha256_hex(canonical_json(code_files))
def write_snapshot(state: ApprovedState, head: tuple[int, str]) -> Path        # snapshots/<seq:08d>-<state_hash[:16]>.json
def latest_snapshot() -> ApprovedState | None
def load_context(now: datetime, positions: Positions, *, session_id: str | None = None) -> Context
    # spec 6.4 + P19/P20/P24; never raises except ValueError on a naive `now`; REPO_ROOT =
    # Path(__file__).resolve().parents[2] for code_files.
```
`code_files` dependency entries use the key `venv:<dist>-<version>.dist-info/RECORD` (dist names "cryptography" and
"PyYAML", found with `importlib.metadata.distribution(name)`; a missing dist is simply absent).
**Amended by Task 13 (P34):** every new store blob, anchor or snapshot file is written atomically through a temp
file `<compliance home>/.<name>.<12 hex>.tmp` (`xb`, fsync, `os.rename`); a blob with other bytes under the same
name is an error, while an existing anchor or snapshot is kept (the first anchor still pins an earlier log line).
Order of operations: an anchor file is written only after its approved line is in owner.jsonl; blob bytes may be
stored before the line (the signer does, and refuses to sign bytes not yet stored) or after it (test fixtures); a
missing blob is re-stored with the same anchor, never a second entry. Snapshot files hold
`{state_seq, state_hash, hashes, head}`. The calendar store takes the calendar stream (name, NUL, bytes, NUL per
file, sorted by the name string).

## 9. `core/compliance/alerts.py` (Task 14)
```python
OWNER_ALERT_EMAIL = "sapientia@korea.ac.kr"
def due(summary: dict | None, history: list[dict], today: date) -> list[dict]      # pure, spec 5.4 thresholds
def render(alert: dict, summary: dict) -> tuple[str, str]                          # fixed template; no rule free text
def _toast(title: str, body: str) -> bool                                          # P26 seam
def log(channel: str, result: str, summary: dict, now: datetime) -> None           # append to alerts.jsonl
def main(argv=None) -> int     # `--today D --summary JSON` -> prints {"send","subject","body"}, shows toast when send,
                               # logs channel "toast"; `--log CHANNEL ok|fail --summary JSON`
```
alerts.jsonl row: canonical JSON `{"utc", "channel", "result", "code", "due", "overdue", "head_seq", "head_sha256",
"fingerprint"}`.
**Amended by Task 14:** the `--check` summary (and `check()`) carries six keys,
`{"code","due","overdue","head_seq","head_sha256","fingerprint"}`. `alerts.main` also takes `--code N` (the exit
code of --check) and an optional `--today`. A summary that disagrees with `--code` or with its own lists, whose head
is not an owner-log line, or whose fingerprint is not `""` or `SHA256:<64 hex>` counts as missing and is alerted.
`log()` refuses a head that is not that line of owner.jsonl and appends under the owner-log sidecar lock
(`owner._exclusive(owner.log_path())`). `due()` raises `key_changed` only for an exit-3 summary. Overdue means
`review_by` after its day, or `auto_off`/`effective_until` from their own day on; due means 0 to 14 days ahead for
`review_by`, 1 to 14 for the other two. The calendar approval is an informational line, outside the exit code.

## 10. `tools/signer/sign.py` (Task 15; stdlib + cryptography; NOT under core/)
Commands: `keygen`, `approve --kind K --path P`, `code-approve --repo R`, `event KIND --data JSON`, `fingerprint`.
It re-implements (copies) the log line format, store layout, `code_files` and the QUANTGEN refusal, because it may
not import the repo; Task 15's tests assert byte-for-byte agreement with owner.py. Refusals live in `main()` only
(CLAUDECODE / CLAUDE_CODE_* env, a `claude.exe` ancestor via ctypes Toolhelp32, non-TTY stdin). Key file
`owner_key.enc`: first line = canonical JSON header `{"format": "tradegen-owner-key/1", "kdf": {"name": "scrypt",
"n": 131072, "r": 8, "p": 1, "salt_b64": ...}, "nonce_b64": ..., "fingerprint": ...}`, second line = base64 of
AES-256-GCM ciphertext of the 32-byte seed with AAD = the header line bytes. Passphrase: >= 20 characters or >= 5
words.
**Amended by Task 15:** P39 narrows the passphrase rule (20 non-blank characters, or 5 different alphabetic words of
3+ letters) and the typed code also refuses three consecutive gaps under 10 ms. `main()` refuses unless Python runs
with `-I`, and `code-approve` refuses unless run under `<repo>/.venv/Scripts/python.exe`. keygen writes
`owner_key.pem` next to `owner_key.enc` and never overwrites either; the owner copies the pem to
`core/compliance/owner_pubkey.pem`. Store writes copy Task 13's atomic write-once rule. The help text states D12 for
`cap_set` and `limit_set`.

## 11. Other amendments made while drafting

- 5.2 (Task 6): `Decision.decision_id` defaults to `""` and is always recomputed in `__post_init__`; `Decision.date`
  is `date | None` (None only for an unsealed context); `Context.ctx_hash` defaults to `""` and `seal_context`
  ignores a passed value; `is_sealed(None)` is False.
- 6.2 (Task 3, P28): the int pattern is `[-+]?(0|[1-9][0-9]*)` with at most 18 digits; explicit tags are Invalid.
- 6.3 (Task 4): `Row.match`, `InstrumentMap.entries` and `VenueFacts.venues` are `MappingProxyType`; a crypto
  entry's `currency` is `KRW`; `cost_book` must equal the asset's own book; on a `quote_by_currency` venue the counter
  must also be a settlement asset; the schema strings are private constants.
- 3 (Task 2): `temp_home()` clears `core.isolation._LINK_SCAN` (Task 2 adds that; Task 1's first version does not).
