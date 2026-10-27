# Area: critic (completeness check, sample verification, new facts)

Repo `C:/Users/whydi/OneDrive/Desktop/TRADEGEN`, main at `995534b`, `git status --short` empty before and after.
Probes are in the scratchpad (`odds_plan/critic/verify.py`, `closure_probe.py`). Every Python run used
`.venv/Scripts/python.exe -B`, with `-I` except for the re-run of the models reader's replay probe, which ran with
TRADEGEN_HOME pointed at `odds_plan/critic/home`. No network call was made, nothing under the repo, ~/.tradegen or
~/.nextgen was written, and `.env` was read for variable NAMES only.

## 1. Sample verification of the eight reader files

* [method] 116 verbatim quotes, taken from all eight files (harness 22, guards 21, compliance_iface 16, data 15,
  models 15, costs_cal 12, followup 10, execution_ctx 6), were looked up at the line ranges the readers cited.
  Result: `116 checks, 0 misses`.
     EVIDENCE: scratchpad odds_plan/critic/verify.py output `116 checks, 0 misses`
     IMPACT: The readers' quotes and line numbers can be used as they are, apart from the corrections below.
* [non-quote checks, all confirmed] (a) Rule review dates: 25 rows say 2026-11-22 and 22 say 2026-11-23, out of 47
  rows. (b) Only KR-KIS-US-OPTION and KR-OKX-SPOT carry a warning. (c) The line endings of 23 files match the readers.
  (d) qa/acceptance_results.json holds 1166 rows: 1043 PASS and 123 NOT_RUN, 608.6 s in total. Compliance has 317
  rows (315 PASS, 2 NOT_RUN REFDATA symlink), 63.6 s. The slowest row is macro_m9_lab smoke at 45.55 s. (e) md5 of
  the upbit cache is de7eaec6f45d0dc12b2950f50433b89d, and md5 of results.csv is ca757e25f508b588cb2f361719ec83cd.
  (f) The S_C3 replay, re-run from the cache, reproduced every card statistic exactly in 4.99 s, and its pnl md5 is
  bbdcf17ca9462567fe351c54644bef0c. (g) The string literals RULE_CHANGE_IN_HORIZON and LIMITS_UNSET occur only in
  spec lines 538, 575, 700, 900 and 1045, plus one review file.
     EVIDENCE: `grep -o 'review_by: *"*[0-9-]*' core/compliance/kr_rules.yaml | sort | uniq -c` -> `25 2026-11-22`, `22 2026-11-23`; kr_rules.yaml:307 `- id: KR-KIS-US-OPTION`, :513 `- id: KR-OKX-SPOT`; replay output `sr_oos 1.2160250195674127 1.2160250195674127` ... `decision PASS chosen_last {'hysteresis': 0.667}` ... `pnl md5 bbdcf17ca9462567fe351c54644bef0c`; results summary `1166 ... Counter({'PASS': 1043, 'NOT_RUN': 123})`
     IMPACT: The models reader's bit-exact replay golden is independently confirmed. It is safe to pin it in the odds
     suite, on the cache fixture and NumPy 2.3.5.

## 2. Corrections to the reader files

* [CORRECTED data.md: plan hand-off line] The compliance plan's `yf.set_cache_location` bullet is at line 16742, not
  16743-16744, and the `nav_fx` bullet is at 16744. The content is as the reader states.
     EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate.md:16742 `- call `yf.set_cache_location` under the state root (the map found yfinance's shared sqlite cache in`; :16744 `- pass `nav_fx` and the `venues.yaml` tick ladder to `cost_per_side`, because the spec's literal per-fill call`
     IMPACT: Cite 16740-16746 for the hand-off list.
* [CORRECTED costs_cal.md: cost-table pin line] `assert V.COST_BP_PER_SIDE == TABLE` is at tests/macro_m0_instruments.py:80, not :78.
     EVIDENCE: tests/macro_m0_instruments.py:80 `assert V.COST_BP_PER_SIDE == TABLE`; :283 `assert mod.COST == TABLE and mod.COST is V.COST_BP_PER_SIDE`
     IMPACT: Any local copy of the rate table in core/odds needs its own equality test, in the style of :80.
* [CORRECTED harness.md: T-HERM-01 does not enumerate touchpoints] T-HERM-01 runs a fixed dict of 14 probes. It does
  not loop over `_touchpoints()`, so adding a bars seam to `_touchpoints()` without a probe fails nothing. A probe is
  still advisable, but nothing forces one.
     EVIDENCE: tests/macro_acceptance.py:171-186 `probes = {` / `"fred": lambda: ficc_data._fred_fetch(["DGS10"], "2026-01-01"),` ... `"raw socket": lambda: socket.create_connection(("127.0.0.1", 9), timeout=0.2),` / `}`; :188-193 `for label, probe in probes.items():`
     IMPACT: If the bars seams go into `_touchpoints()`, the odds plan adds a probe by choice. The odds suite needs
     its own "every bars seam raises" test in either design.
* [CLARIFIED costs_cal.md / guards.md: closure counts] "instruments pulls 24 files" and "calendars store+clocks+regime
  37" count the closure of the import alone, which includes core/__init__.py and core/isolation.py. Measured against
  today's 8-file D14 closure, the additions are: instruments +22; store +34; clocks +34; regime +35. The guards reader
  wrote "only garch is cheap". In fact core.ficc.macro_schema is also +2, and core.compliance.model and core.isolation
  are +0.
     EVIDENCE: scratchpad odds_plan/critic/closure_probe.py output `base 8` / `core.quant.instruments: +22` / `core.calendars.store: +34` / `core.calendars.clocks: +34` / `core.calendars.regime: +35` / `core.quant.garch: +2` / `core.ficc.macro_schema: +2`
     IMPACT: In the plan, state every closure figure as "+N beyond today's 8 files".

## 3. New facts the odds plan needs (not established, or established without evidence, by the readers)

### 3.1 Provenance helpers named by spec 4 and 7.5

* [repo_anchor] `gate_ledger.repo_anchor(root=REPO_ROOT) -> str` reads `.git/HEAD`, then the loose ref or
  `packed-refs`. It returns `git:<40-hex>`, or `UNVERSIONED` on OSError or anything that is not a sha. It starts no
  subprocess, uses no network and reads no clock. The repo is a git repository today.
     EVIDENCE: core/quant/gate_ledger.py:122-136 `def repo_anchor(root: Path = REPO_ROOT) -> str:` / `head = Path(root) / ".git" / "HEAD"` ... `packed = (Path(root) / ".git" / "packed-refs").read_text(encoding="utf-8").splitlines()` / `return f"git:{text}" if re.fullmatch(r"[0-9a-f]{40}", text) else UNVERSIONED`; tests/macro_m7_ledger.py:147-153 (loose, packed and UNVERSIONED cases)
     IMPACT: It is safe to call from report code. Importing it costs +29 closure files (next bullet).
* [tree_hash] `macro_artifacts.tree_hash(root=REPO_ROOT) -> str` is a sha256 over sorted relpath + NUL + bytes + NUL of
  `core/**/*.py`, `data/macro/**/*` and `config.py`. It therefore covers every core/odds .py file, so it changes with
  every odds edit. venues.yaml is not covered. No test pins its value: tree_hash is a volatile field everywhere.
  `macro_artifacts.GIT_HASH = "UNVERSIONED"` is a stale constant ("the folder is not a git repository").
     EVIDENCE: core/ficc/macro_artifacts.py:34 `GIT_HASH = "UNVERSIONED"      # ruling 3.1: the folder is not a git repository; never a fabricated sha`; :35 `TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")`; :53-61 `def tree_hash(root: Path = REPO_ROOT) -> str:` ... `h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")`; tests/macro_m0_schemas.py:527 `S.VOLATILE_FIELDS == ("generated_at_utc", "git_hash", "tree_hash")`
     IMPACT: Use `repo_anchor()` for the git sha, never `macro_artifacts.GIT_HASH`. Record tree_hash as provenance
     only. Never compare it across runs as an identity check.
* [provenance imports are expensive and reach orders.py] Importing `core.ficc.macro_artifacts` adds 46 closure files.
  They include config.py, every data client and core/engine/{__init__,books,evaluator,orders,state}.py, through
  risk_layer -> core.engine.books -> core/engine/__init__.py. Importing `core.quant.gate_ledger` adds 29, including
  config.py and data/*, through gate_stats -> validate -> history.
     EVIDENCE: closure_probe.py `core.ficc.macro_artifacts: +46  config/data/engine: ['config.py', 'core/engine/__init__.py', 'core/engine/books.py', 'core/engine/evaluator.py', 'core/engine/orders.py', ...]`, `core.quant.gate_ledger: +29`; core/ficc/macro_artifacts.py:28-30 `from core.ficc import pit as _pit` / `from core.ficc.macro_schema import ...` / `from core.quant import risk_layer as RL`; core/quant/gate_ledger.py:51-53 `from core.ficc.macro_schema import canonical_json, md5_hex` / `from core.quant import gate_stats as GS` / `from core.quant.validate import EULER_GAMMA, TRADING_DAYS`
     IMPACT: Spec 4's "No core.engine.orders import" is checked only on direct imports. Importing tree_hash from
     core/odds passes every guard, yet it puts orders.py into the signed closure. The two helpers are 9 and 15 lines.
     A local copy plus an equality test against the repo function (run in tests/) avoids this. The alternative is
     to compute provenance in a caller outside core/odds.
* [other closure costs, per import, beyond today's 8 files] gate_stats (pw_block, LIVE_SHARPE_MULTIPLIER,
  block_indices) adds 23. tf_books (DELIST_STRESS) adds 53, orders.py included. instruments (cost_per_side,
  tick_size, tick_floor_bp) adds 22. validate adds 22. strategies adds 46, orders.py included. The calendar
  modules add 34-35. garch adds 2. macro_schema adds 2. data.crypto.crypto_client adds 20.
     EVIDENCE: closure_probe.py lines `core.quant.gate_stats: +23`, `core.quant.tf_books: +53 ... 'core/engine/orders.py'`, `core.quant.instruments: +22`, `core.quant.validate: +22`, `core.quant.strategies: +46 ... 'core/engine/orders.py'`, `data.crypto.crypto_client: +20`; core/quant/tf_books.py:32-33 `from core.quant.tf_screens import quantile_groups` / `from core.quant.validate import newey_west_t`; core/quant/instruments.py:16 `from core.quant.validate import COST_BP_PER_SIDE, GATE, cost_bp`; core/quant/gate_stats.py:30 `from core.quant import validate as V`
     IMPACT: The constant-only imports are expensive. Reading DELIST_STRESS through tf_books costs 53 files.
     Declare the constants locally (LIVE_SHARPE_MULTIPLIER = 0.60, DELIST_STRESS = (0.30, 1.00), the cost table if
     copied), and pin each with an equality test in tests/. This is the pattern spec 4 already uses for
     LIMIT_DOWN_CARRY_COST_MULTIPLIER.

### 3.2 Paths, hashing and helpers that cost nothing in the closure

* [state root without config] `core.isolation.state_root()` returns TRADEGEN_HOME (read straight from os.environ),
  else ~/.tradegen. It refuses QUANTGEN and runs the link scan. `refuse_quantgen` and `checked_target` live in the same
  stdlib-only file, which is already in the D14 closure. `config.state_root()` only delegates to it. `.env` sets no
  TRADEGEN_HOME today: its state-ish names are only NEXTGEN_SKILLS_ROOT and QUANTGEN_AI_MODEL.
     EVIDENCE: core/isolation.py:105-110 `def state_root() -> Path:` ... `root = refuse_quantgen(_env("TRADEGEN_HOME") or Path.home() / ".tradegen", "TRADEGEN_HOME")` / `scan_links(root)`; :32-37 `def _env(name: str) -> str:` / `value = (os.environ.get(name) or "").strip()`; config.py:62-65 `def state_root() -> Path:` ... `return _isolation.state_root()`; names-only .env scan `14 NEXTGEN_SKILLS_ROOT` / `53 QUANTGEN_AI_MODEL`
     IMPACT: Put the bars cache and odds state under `core.isolation.state_root() / "odds"`, resolved on every call.
     That adds 0 closure files. `config.state_path(...)`, which the data reader proposed, adds 20, and its env
     override would need dotenv. A TRADEGEN_HOME set only in .env would be missed when config is never imported.
     Today none is set.
* [canonical JSON and hashes] `core.compliance.model.canonical_json` is jsonable() followed by sorted-key, compact JSON
  with allow_nan=False. It gives the same text as macro_schema.canonical_json. It accepts `np.float64` (a float
  subclass). It REFUSES `np.int64`, `np.float32` and ndarrays with TypeError "not JSON data". `model.sha256_hex`
  exists. There is no md5 helper in model; `hashlib.md5` is stdlib.
     EVIDENCE: core/compliance/model.py:57-59 `def canonical_json(obj) -> str:` / `"""The same text as core.ficc.macro_schema.canonical_json, after jsonable(); NaN and inf refused."""`; :52 `raise TypeError(f"not JSON data: {type(obj).__name__}")`; probe output `int64 TypeError not JSON data: int64`, `float32 TypeError not JSON data: float32`, `ndarray TypeError not JSON data: ndarray`, `True 7b83489fa8e4c7b8a839c6d5245c1d7f` (model and macro_schema texts equal)
     IMPACT: Series hash = `hashlib.md5(model.canonical_json({...}).encode("utf-8")).hexdigest()`, with closure +0.
     Convert arrays with `.tolist()` first, so float64 stays float and int64 becomes int. macro_schema.md5_hex
     would add 2 files.
* [calendar provenance fields] `CalendarFile` has file_id, version, md5, covers_from, covers_to, coverage_calendar,
  signed_off_by, signed_utc, rows, doc and path. `CalendarSet.version` is "unsigned" unless the manifest is signed.
     EVIDENCE: core/calendars/store.py:76-87 `class CalendarFile:` / `file_id: str` / `version: str` / `md5: str` ...; :268-271 `def version(self) -> str:` ... `"unsigned"`
     IMPACT: Provenance records `cal.version` and `cal.file(fid).md5` for each file a leg reads: kr_sessions,
     holidays_KRX and kr_regime_tags for KRX; holidays_NYSE for US.

### 3.3 Calendar behaviour the simulator relies on

* [regime_tags falls back to the default set] `regime_tags(market, d, *, cal=None)` runs `cal = cal or default()`. It
  raises CalendarUnsigned when any tag has a row count other than one on date d, so a gap or an overlap in any tag
  refuses the whole call, not just price_limit.
     EVIDENCE: core/calendars/regime.py:62-75 `def regime_tags(market: str, d: date, *, cal: CalendarSet | None = None) -> dict:` / `cal = cal or default()` ... `if len(hits) != 1:` / `raise CalendarUnsigned(f"{FILE_ID} v{f.version}: {len(hits)} rows for {tag!r} on {d.isoformat()}")`
     IMPACT: core/odds must always pass `cal=` explicitly to regime_tags, is_session, sessions_between and
     decision_time_utc, each of which uses the same `cal or default()` fallback (clocks.py:192, :241, and eight more
     clocks functions at :265-393). A test should
     prove that no odds path calls `default()`, for example by patching `store.default` to raise.
* [the 15 KR regime tags; none marks IPO or reset days] The tags are price_limit, close_time_kst, saturday_session,
  closing_call, random_end, lunch_break, fx_regime, etf_available, short_sale_ban, short_sale_regime, sell_tax_pct,
  tick_regime, letf_rules, usdkrw_onshore_hours and value_up. None marks an IPO day, a reference-price reset or any
  other per-symbol special regime. Spec 13 defers "special KRX reference regimes".
     EVIDENCE: `grep -n "tag:" core/calendars/data/kr_regime_tags.yaml` (15 distinct tag names, e.g. :39 `tag: price_limit`, :99 `tag: close_time_kst`, :488 `tag: value_up`); spec:1167-1168 `- **Deferred techniques:** importance sampling, an intraday martingale path model, an OKX candle loader, special KRX` / `reference regimes.`
     IMPACT: SPECIAL_REGIME (spec 7.2) has no repo data source. The plan must pick one: owner-signed data
     (venues.yaml or a new list), passing KIS `flng_cls_code` through (a data/ edit), or a documented narrow
     detector. It must not claim detection it cannot do.
* [close times come from the macro rules store, not the signed calendar] The KR close is read from
  `cfg["close_kst"]` (effective-dated) and the US close from `cfg["close_et"]`. Both live in
  `CalendarSet.config` = `core.rules.macro_rules.load_store()["calendars"]` (data/macro/rules_v2.0.0.json) unless
  `config=` is injected. Only CN, HK and TW closes come from market_closes.yaml.
     EVIDENCE: core/calendars/clocks.py:130 `close = _hhmm(effective_config(cfg["close_kst"], d, "calendars.KR.close_kst")["time"], "close_kst")`; :143-144 `if market == "US":` / `return _hhmm(cfg["close_et"], "close_et"), cfg["tz"], frozenset(flags)`; data/macro/rules_v2.0.0.json:249 `"close_et": "16:00",`; core/calendars/store.py:233-237 (lazy macro_rules config)
     IMPACT: When bars or simulate judge finality, or the Seoul date of a US close, through `decision_time_utc`, they
     depend on data/macro (read-only, covered by tree_hash, not by the calendar approval). If the plan uses
     clocks for finality, say so. Otherwise use fixed close times (KRX 15:30 KST, NYSE 16:00 ET) plus the 10-minute
     margin.
* [the CLI already promises crypto-only] `rules._calendar_line` already prints "calendar: no signed approval, so KRX
  and US plans are refused (crypto plans only)". Its recipe: verify_log, then in_force over _up_to(log, moment), then
  store_get. `_log_lines` and `_up_to` are private; `verify_log`, `read_pubkey`, `read_anchors`, `in_force`,
  `store_get` and `code_approval` are public.
     EVIDENCE: core/compliance/rules.py:907-920 `log = owner.verify_log(owner._log_lines(owner.log_path()), owner.read_pubkey(owner.PUBKEY_PATH),` ... `return "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"`; core/compliance/owner.py:180 `def _log_lines(path: Path) -> list[bytes]:`, :457 `def _up_to(check: LogCheck, now_utc: str) -> LogCheck:`, :567 `def in_force(check: LogCheck) -> dict[str, tuple[str, int]]:`, :670 `def store_get(kind: str, sha256: str) -> bytes | None:`
     IMPACT: CALENDAR_UNSIGNED wording should match the --check line. A public `owner.calendar_in_force(now)` (a
     compliance follow-up item) would remove the two private calls from core/odds.

### 3.4 Tests that pin the venues.yaml bytes (the odds plan's venues.yaml edit must keep them true)

* [byte-level pins in tests/compliance_gate.py] Three tests edit the shipped venues bytes by text:
  (1) `raw.partition(b"\n  okx:")` with exactly one `tag_required: false` BEFORE okx;
  (2) the same partition with exactly one `tag_required: false` AFTER okx;
  (3) exactly one occurrence of `markets: [[BTC, KRW], [USDT, KRW]]`, the upbit line.
     EVIDENCE: tests/compliance_gate.py:695-697 `raw = F.shipped_bytes("venues")` / `head, sep, tail = raw.partition(b"\n  okx:")` / `assert sep and head.count(b"tag_required: false") == 1`; :998-1000 `assert sep and tail.count(b"tag_required: false") == 1`; :336-340 `market = b"markets: [[BTC, KRW], [USDT, KRW]]"` / `assert old_map.count(usdt) == old_map.count(ibit) == old_venues.count(market) == 1`
     IMPACT: Odds additions keep `okx:` as a two-space-indented venue key. They add no `tag_required` text
     anywhere, including any top-level block after `venues:`, and keep the upbit markets line in that exact
     flow form. Otherwise three compliance tests fail.
* [shape pins in tests/compliance_tables.py] The shipped venues file must stay UTF-8 with no BOM, LF, newline-ended and
  <= 256 KB. It holds exactly the six venues with the pinned sections, settlement, markets, default_quote and
  deposits. Each venue's `source` is a repo reference or "UNVERIFIED: owner to confirm before approval". Every https
  URL appears verbatim in the research corpus.
     EVIDENCE: tests/compliance_tables.py:897-902 `def test_shipped_files_are_utf8_lf_and_small():` ... `assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, kind`; :1089-1106 `def test_shipped_venue_facts_p22():` / `assert set(v) == {"kis", "upbit", "bithumb", "coinone", "korbit", "okx"}`; :1136-1138 `doc = _t5_rules.load_strict(_t5_raw("venues"), "venues")` / `assert _t5_ref_ok(entry["source"]) or entry["source"] == _T5_UNVERIFIED, vid`; :1141-1150 `def test_shipped_urls_come_from_the_research():`; core/compliance/rules.py:75 `MAX_TABLE_BYTES = 256 * 1024`
     IMPACT: New lot, minimum, tick and fee data carry either a research URL that is already in reports/ or
     research_notes/, or the UNVERIFIED marker. The parser change must keep these tests' venue equality, for
     example by giving the new Venue fields defaults (compliance_iface).
* [the store refuses an "odds" kind] `owner.store_put("odds", ...)` raises ValueError, and `store_get("odds", sha)` is
  None. The approved store holds only rules, instruments, venues and calendar.
     EVIDENCE: tests/compliance_store.py:41 `assert owner.store_get("venues", "not-a-sha") is None and owner.store_get("odds", sha) is None`; :52 `_raises(lambda: owner.store_put("odds", raw, (1, "a" * 64)), ValueError)`; core/compliance/owner.py:29 `APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")`
     IMPACT: Odds data (sentence catalogue, owner-typed inputs) cannot be approved through the store without a
     compliance change. Keep the catalogue in .py, which the code hash covers, or accept that a data file is unsigned.

### 3.5 Venue facts in research (minimums)

* [minimums: only Upbit is confirmed] Upbit KRW 5,000 is confirmed. Bithumb KRW 5,000 is stated, but its
  verification is marked unfinished. Coinone, Korbit and Gopax fee or minimum tables were not found. No OKX minimum
  order or lot size appears anywhere in reports/ or research_notes/.
     EVIDENCE: research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas.md:8 `The KRW-market minimum order is KRW 5,000 on both Upbit and Bithumb`; :50 `Upbit and Coinone support pages for current fees and minimums could not be fetched (403). 2026 fee tables for Bithumb, Coinone, Korbit and Gopax were not found.`; crypto_domestic_and_overseas_verification.md:14 `... the current Bithumb minimum order ... Those items are marked uncertain.`; grep `(?i)okx.{0,80}(minimum|min order|minSz|lot size)` over reports/ and research_notes/ -> no matches
     IMPACT: venues.yaml minimums: Upbit can cite the Upbit docs URL. Bithumb is UNVERIFIED. Coinone, Korbit and OKX
     have no source, so they are owner input. Spec 7.2 says "a missing entry gives NOT_TRADABLE", so legs on those
     venues are NOT_TRADABLE until the owner signs a value.

### 3.6 Repo-wide tests that will scan core/odds (beyond the readers' list)

* [test_18 token ban] runtime_py() code (docstrings stripped) may not contain the tokens "eodhd" or "quartr".
     EVIDENCE: tests/acceptance.py:265-270 `def test_18_eodhd_is_gone_from_the_runtime():` ... `for token in ("eodhd", "quartr"):`
     IMPACT: A trivial constraint, listed for completeness.
* [test_16 UTF-8] Every runtime_py() file must decode as UTF-8. It need not be ASCII, so the catalogue may hold
  "×", "≤" and "–".
     EVIDENCE: tests/acceptance.py:247-253 `def test_16_every_source_file_is_utf8_readable():` ... `except UnicodeDecodeError as exc:`
     IMPACT: Non-ASCII catalogue text is legal in core/odds. tests/run_all.py edits stay ASCII (harness).
* [cardp names] No core module other than core/quant/cardp.py may use a name `timing_probe` or `_run_lagged`.
     EVIDENCE: tests/macro_m7_cardp.py:502-503 `hits = _static_names(CORE, {"timing_probe", "_run_lagged", "_PROBE", "import:cardp"})` / `assert set(hits.get("timing_probe", [])) <= {"core/quant/cardp.py"} and set(hits.get("_run_lagged", [])) <= {"core/quant/cardp.py"}`
     IMPACT: Avoid those two identifiers in core/odds.
* [no language-guard precedent] No repo module or test implements a banned-word guard or a sentence catalogue. The
  only "forbidden words" test is compliance's raw-text guard.
     EVIDENCE: grep `(?i)banned word|forbidden word|FORBIDDEN_WORDS|BANNED =|_BANNED|word guard|language guard` over core/ui/tests -> only tests/compliance_guards.py:224 `def test_raw_text_has_no_forbidden_words():` and an unrelated tests/macro_m9_scenarios.py:294
     IMPACT: The catalogue, slot rendering and the whole-word ban list of spec 7.5 are new code. Whole words are
     banned, so the hyphenated "floor-safe" contains the banned word "safe" and must not reach rendered text. Use
     spec 10's wording, "Your floor holds even if this position goes to zero".

### 3.7 Packaging and the empty `__init__`

* [every other core subpackage is a regular package] calendars, compliance (0 bytes), crypto, engine, ficc, quant,
  rules and skills all have `__init__.py`. Only core/odds has none. pyproject uses `[tool.setuptools.packages.find]`
  with `include = ["core*", ...]`, which finds regular packages only.
     EVIDENCE: loop over core/*/ printed `core/compliance/ 0`, `core/odds/ ABSENT`, `core/quant/ 657` ...; pyproject.toml `[tool.setuptools.packages.find]` / `include = ["core*", "data*", "ui*"]`
     IMPACT: A 0-byte `core/odds/__init__.py` follows the precedent and passes the guard
     (tests/compliance_guards.py:408). It also adds core/odds/__init__.py to the D14 closure as an ancestor, so the
     closure tests' `glob("*.py")` sets pick it up automatically.

### 3.8 Hermetic helpers to reuse

* [HermeticViolation and _boom] The guard raises `HermeticViolation(RuntimeError)` from `_boom`. `_Refuse` stands in
  for a requests module. Both live in tests/macro_acceptance.py, and `_touchpoints()` imports config, history and every
  data client on every `hermetic()` entry.
     EVIDENCE: tests/macro_acceptance.py:33-38 `class HermeticViolation(RuntimeError):` ... `def _boom(*_a, **_k):` / `raise HermeticViolation("network touchpoint called inside the macro suite (T-HERM-01)")`; :52-60 `def _touchpoints() -> list[tuple[object, str, object]]:` / `import config` ...
     IMPACT: The odds wrapper patches the bars seams with the same `_boom`, so one exception type means "network
     inside a suite". Every guarded test process already imports config and the data clients, so the odds suite's
     wall time includes them whatever bars.py imports.

### 3.9 Name clash

* [Fraction] Spec 7.1 names a plan type `Fraction` (`fraction: Fraction  # fixed(f) | kelly(c <= 0.5) | bold()`). The
  models reader recommends `fractions.Fraction` for an exact bold_even.
     EVIDENCE: spec:656 `fraction: Fraction               # fixed(f) | kelly(c <= 0.5) | bold()`; models.md "Implement bold_even with fractions.Fraction (stdlib)"
     IMPACT: bold.py should `import fractions` and write `fractions.Fraction(...)`, or plan.py names its type
     differently. Do not let `from fractions import Fraction` shadow plan.Fraction in any module that needs both.

## Open questions

* The harness reader measured 7.27 s to import tests.run_all. The critic did not re-measure it, to avoid importing
  every suite.
* Should provenance (repo_anchor, tree_hash) be computed in core/odds from local copies, or by a caller outside
  core/odds that passes the strings in? The spec only says "Every report records" them.
* Is the macro rules store's close_kst and close_et (data/macro, unsigned by the calendar approval) acceptable as the
  source of finality instants, or must the odds plan pin its own close times?
* SPECIAL_REGIME: which data source does the owner accept, given that no repo file marks IPO or reset days?
