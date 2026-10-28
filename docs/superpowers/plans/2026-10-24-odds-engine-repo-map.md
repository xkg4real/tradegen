# Odds engine plan: repo map (2026-10-24)

These are the verified repo facts the odds engine plan rests on: sections 0 to 7 and 10 of the 2026-10-24 repo map
digest, then its design questions for the odds plan and its open questions. They were mapped read-only with
file:line evidence (the critic re-checked the items marked (C)), and the plan's interface contract was drafted on
them. Sections 8 and 9 belong to the compliance follow-up and E1 maps and are left out. Where the plan's tasks and
this map disagree, the tasks win; the plan's Appendix A section 1.1 gives the decision that answers each design
question. Line numbers are as of commit `995534b` (the compliance merge), which equals `5816d3c`, the commit the
plan is written against, outside docs/.

```text
# DIGEST: repo map for the odds plan, the compliance follow-up and the execution design

Repo `C:/Users/whydi/OneDrive/Desktop/TRADEGEN`, `main` at `995534b`, tree clean. This digest merges eight reader maps
(harness, guards, compliance_iface, data, models, costs_cal, followup, execution_ctx) and the critic's own map
(critic.md), deduplicated. Every fact carries repo evidence (path:line `quote`).

Markers:
- (C) means the critic re-checked the quote or number against the tree in this pass. A scripted check of 116 quotes
  found 0 misses, and spot checks covered the rest.
- CORRECTED means a reader's claim was wrong or misleading, and the corrected text is given.
- The source maps are in the same folder; the reader name in brackets says where to find more detail.

Spec = docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md (rev 3.2). Plan = the compliance
plan docs/superpowers/plans/2026-10-23-compliance-gate.md. Ledger = its execution ledger
docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md.

---

## 0. Repo state and process rules

* [state] HEAD is 995534b on `main`, the only branch. The compliance branch is merged. core/odds holds only
  venues.yaml. (C)
     EVIDENCE: `git log --oneline -1` `995534b test: full run after the final review wave`; `ls core/odds` -> `venues.yaml`
     IMPACT: Both new plans branch from main. The odds plan creates every core/odds .py file.
* [no owner key yet] core/compliance/owner_pubkey.pem does not exist, so load_context returns BROKEN "no owner key yet:
  owner act 1", and every screen() result is BLOCK in the real home. (C)
     EVIDENCE: core/compliance/owner.py:24 `PUBKEY_PATH = Path(__file__).with_name("owner_pubkey.pem")   # the trust anchor; absent until owner act 1 (P24)`; :929 `return model.OwnerState.broken("no owner key yet: owner act 1"), None`
     IMPACT: No real-home odds run can produce a probability before owner acts 1-5. Manual checks expect the
     refusal. Tests use a temp home and the test key. Nothing is signed yet, so code edits cost no re-signing today.
* [no pytest] A test is a zero-argument `test_*` function that raises. No pytest is installed or used.
     EVIDENCE: plan:61 `- A test is a zero-argument `test_*` function that raises on failure. There is no pytest.`
     IMPACT: No fixtures, parametrize or monkeypatch. Use loops, helpers and save/restore in try/finally.
* [commands] One module or one test: `.venv/Scripts/python.exe -m tests.<suite>_acceptance <module>/[<test>]`. It never
  writes the results file and imports every suite (~7 s, reader-measured). One suite:
  `.venv/Scripts/python.exe tests/run_all.py --suite <name>; echo "exit $?"; git checkout -- qa/acceptance_results.json`.
  Run from the repo root.
     EVIDENCE: tests/compliance_acceptance.py:8-11 `.venv/Scripts/python.exe -m tests.compliance_acceptance [substring]` ... `It never writes` / `qa/acceptance_results.json.`; plan:70-73 `- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite <name>`. This rewrites the tracked` / `qa/acceptance_results.json`. Restore it with `git checkout -- qa/acceptance_results.json` afterwards.`
     IMPACT: Copy both forms into each plan, with the suite name substituted.
* [CORRECTED by harness, vs the earlier repo map: results file is TRACKED] qa/acceptance_results.json is tracked
  (committed in 995534b, 355f978 and d47cea9) and CRLF. Every `run_all` run overwrites it, `--suite` runs included. It
  holds 1166 rows: 1043 PASS and 123 NOT_RUN, 608.6 s. (C)
     EVIDENCE: tests/run_all.py:54 `OUT = ROOT / "qa" / "acceptance_results.json"`; `git ls-files --eol qa/acceptance_results.json` -> `i/crlf  w/crlf`; results summary `1166 ... {'PASS': 1043, 'NOT_RUN': 123}`
     IMPACT: Restore the file after every suite run. Only the final full-run task commits it.
* [overlap check] QUANTGEN shares the machine. Before every test command, run a check that prints nothing.
     EVIDENCE: plan:62-67 `- Overlap check: run it before every test command. It must print nothing; otherwise wait.` ... `Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" }`
     IMPACT: Carry the rule into both plans. The odds Monte Carlo is CPU-heavy: never run two suites at once.
* [line endings] `.gitattributes` is `* -text` ("Byte-exact"). CRLF: README.md, config.py, tests/run_all.py,
  core/quant/history.py, grokteam/book.py, qa/acceptance_results.json and the docs/asset_expansion/cache CSVs. LF:
  every core/compliance file, core/odds/venues.yaml, data/krx/kis_client.py, data/crypto/crypto_client.py,
  core/ficc/data.py, core/isolation.py, tools/signer/sign.py, and tests/compliance_*.py, macro_acceptance.py,
  macro_m0_rules.py and macro_m1_calendars.py. (C)
     EVIDENCE: `git ls-files --eol` (e.g. `i/crlf  w/crlf  attr/-text  tests/run_all.py`, `i/lf    w/lf    attr/-text  core/compliance/rules.py`); plan:75-76 `- New files are UTF-8 with no BOM and LF endings.`
     IMPACT: Edit CRLF files with the Edit tool only, never `sed -i`. New files are LF. Before each commit,
     `git diff --stat` must equal `git diff --stat --ignore-cr-at-eol`.
* [interpreter and pins] Python 3.13.14. Pinned: numpy 2.3.5, scipy 1.18.0, pandas 2.3.3, statsmodels 0.14.6,
  yfinance 1.4.1, curl_cffi 0.15.0, tzdata 2026.2, cryptography 49.0.0, PyYAML 6.0.3. requirements.txt and
  pyproject already declare numpy, scipy and yfinance (as >=), so no new dependency is needed. `arch` is not
  installed. (C)
     EVIDENCE: constraints.txt:1 `# TRADEGEN .venv as of 2026-10-23 (Python 3.13.14)...`; :55 `numpy==2.3.5`; :87 `scipy==1.18.0`; :106 `yfinance==1.4.1`; pyproject.toml `"numpy>=1.26", "pandas>=2.1", "scipy>=1.11", ...` `"yfinance>=0.2", ...` `"cryptography==49.0.0",`
     IMPACT: Record numpy.__version__ and the cryptography version (via importlib.metadata) in provenance. Never
     change the pins: the replay golden depends on them.

## 1. Test harness (wiring an `odds` suite like `compliance`)

* [runner registry] tests/run_all.py imports every suite's `tests()` at top level, with no try/except, ending with
  compliance (line 50). `tests()` concatenates `("<suite>/<name>", fn)`, ending with compliance (lines 66-67). (C)
     EVIDENCE: tests/run_all.py:50 `from tests.compliance_acceptance import tests as compliance_tests  # noqa: E402`; :66-67 `[(f"grokteam/{n}", f) for n, f in grokteam_tests()] +` / `[(f"compliance/{n}", f) for n, f in compliance_tests()])`
     IMPACT: Add `from tests.odds_acceptance import tests as odds_tests  # noqa: E402` and
     `+ [(f"odds/{n}", f) for n, f in odds_tests()]`. tests/odds_acceptance.py must import nothing at top level that
     can fail, or it kills every run.
* [--suite is an exact prefix match after full discovery] `select()` keeps names whose first segment equals the
  suite. Every suite is discovered first. An unknown or unwired suite gives 0 results and exit 1. (C)
     EVIDENCE: tests/run_all.py:83-84 `if suite:` / `entries = [(n, f) for n, f in entries if n.split("/", 1)[0] == suite]`; :124 `return 0 if results and failed == 0 else 1`
     IMPACT: The prefix must be exactly `odds`. Exit 1 with 0 results means the wiring is missing.
* [help text literal is pinned by a compliance test] The --suite help ends "paper, grokteam or compliance".
  compliance_guards asserts that this literal appears in run_all.py and in README.md:816. The ledger calls it brittle. (C)
     EVIDENCE: tests/run_all.py:113 `parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance")`; tests/compliance_guards.py:483-489 `def test_suite_is_registered_in_run_all_and_readme():` ... `assert "paper, grokteam or compliance" in (ROOT / "README.md").read_text(encoding="utf-8")`; ledger:69 `Task 1: minor (deferred): registration test asserts the literal "paper, grokteam or compliance" (brittle; plan-mandated)`
     IMPACT: Adding "odds" to the help and README breaks this test. Edit it in the same task (DQ25).
* [NOT_RUN and no timeout] `run()` records NOT_RUN plus the reason, and `seconds` for every row. There is no per-test
  timeout and no slow-test tier.
     EVIDENCE: tests/run_all.py:94-105 `except NotRun as exc:` / `row["status"], row["reason"] = "NOT_RUN", exc.reason` ... `row["seconds"] = round(time.perf_counter() - started, 4)`
     IMPACT: Every odds Monte Carlo test runs in full in every full run. Size tests deliberately (section 6, DQ14).
* [--milestone ignores non-macro tests] Selection needs `fn.test_ids` with registry rows. Compliance carries none.
     EVIDENCE: tests/run_all.py:86-88 `if any(table.get(t, 99) <= k for t in getattr(f, "test_ids", ())) and module_milestone(n) <= k]`
     IMPACT: Odds tests carry no `test_ids` and add no registry rows.
* [runner source rules] Every runtime_py() file, plus acceptance.py and run_all.py, must decode as UTF-8 (test_16).
  run_all.py and acceptance.py may not use a bare `read_text()` (test_17). (C)
     EVIDENCE: tests/acceptance.py:247-253 `def test_16_every_source_file_is_utf8_readable():`; :259-261 `for name in ("acceptance.py", "run_all.py"):` ... `assert not re.search(r"read_text\(\s*\)", source)`
     IMPACT: Keep run_all.py edits ASCII and encoding-explicit. core/odds may hold non-ASCII UTF-8 catalogue text.
* [aggregator to copy] tests/compliance_acceptance.py has an explicit MODULES tuple, skips absent modules, turns a
  broken import into one `<stem>/import` entry, and collects only `test_*` names defined in the module. `_wrap` runs each
  test inside `with hermetic(), temp_home():` and fails if a (path, size, mtime_ns) listing of the REAL
  ~/.tradegen/compliance changed. `_main` runs a substring of entries and never writes the results file. (C)
     EVIDENCE: tests/compliance_acceptance.py:22 `from tests.macro_acceptance import hermetic`; :25-28 `MODULES = ("compliance_guards", ...` / `_REAL_HOME = Path.home() / ".tradegen" / "compliance"      # fixed at import`; :43-56 `with hermetic(), temp_home():` ... `raise AssertionError(f"the test touched the real ~/.tradegen/compliance: {changed[:5]}")`; :70-71 `if name.startswith("test_") and callable(fn) and getattr(fn, "__module__", None) == module.__name__:`; :77-86 `def _main(argv: list[str]) -> int:` / `from tests.run_all import run`
     IMPACT: tests/odds_acceptance.py copies this shape. It lists every planned `odds_*` module up front (absent ones
     are skipped), watches the real `~/.tradegen/odds` (and compliance, since odds tests build owner logs), and adds
     the bars-seam patches (DQ3).
* [module naming] Macro discovery globs `tests/macro_*.py` and enforces the run_module tail. Nothing globs `odds_*`.
  The macro `run_module` tail sets no temp TRADEGEN_HOME and collects imported `test_*` names.
     EVIDENCE: tests/macro_acceptance.py:220 `for path in sorted(TESTS.glob("macro_*.py")):`; :250 `found = sorted((n, f) for n, f in namespace.items() if n.startswith("test_") and callable(f))`
     IMPACT: Name modules `tests/odds_*.py`, give them no `__main__` tail, and keep odds_acceptance.py and any
     odds_fixtures.py out of MODULES.
* [hermetic mechanics] `hermetic()` is re-entrant via `_DEPTH`. It saves `vars(obj).get(name, _MISSING)`, sets the
  patch, and restores in reverse order (delattr when the attribute was missing). `_touchpoints()` imports config,
  history and every data client lazily on each entry. Patches raise `HermeticViolation(RuntimeError)` from `_boom`, or
  `_Refuse()` for module-like objects. (C)
     EVIDENCE: tests/macro_acceptance.py:33-38 `class HermeticViolation(RuntimeError):` ... `def _boom(*_a, **_k):`; :52-60 `def _touchpoints() -> list[tuple[object, str, object]]:` / `import config`; :74-98 (DEPTH, save, restore)
     IMPACT: Use the same idiom and `_boom` for bars seams. Every guarded test process already imports config and
     the data clients.
* [the touchpoints covered] Patched: ficc `_fred_fetch`, `_yf_fetch`, `_requests`; history `_requests`; crypto `_get`,
  `_requests`; kis_markets, fmp, kis_client `requests`/`_once`/`KISClient._get`; opendart and krx_market `requests`;
  `data.net.session.request`; `socket.socket.connect`/`connect_ex`; `config.FICC_CACHE_TTL_SECONDS = 0.0`. yfinance and
  curl_cffi are NOT patched. (C)
     EVIDENCE: tests/macro_acceptance.py:61-71 `(ficc_data, "_fred_fetch", _boom), (ficc_data, "_yf_fetch", _boom), ...` / `(net.session, "request", _boom), ...` / `(config, "FICC_CACHE_TTL_SECONDS", 0.0),         # no disk cache answers or is written`; spec:166-168 `Every network call goes through a module-level seam` / `(for example `bars._yf_download`), which the test suites patch, because yfinance uses curl_cffi and bypasses a socket` / `patch.`
     IMPACT: Every bars network seam needs its own raising patch, plus a test that proves each one raises.
* [CORRECTED (harness): T-HERM-01 is a fixed probe dict] T-HERM-01 checks 14 named probes and does not iterate
  `_touchpoints()`. Adding a bars seam to `_touchpoints()` does not break it, and does not test the seam either. (C)
     EVIDENCE: tests/macro_acceptance.py:171-186 `probes = {` / `"fred": ...` ... `"raw socket": lambda: socket.create_connection(("127.0.0.1", 9), timeout=0.2),`; :188-193 `for label, probe in probes.items():`
     IMPACT: Wherever the bars seams are patched, the odds suite needs its own probe test.
* [seams must be looked up at call time] The guard swaps module attributes. A `from X import f` binding taken at import
  keeps the real function. history reads `_yf_fetch` inside the function for this reason. Tests also swap whole
  classes (`kis.KISClient = _FakeKIS`).
     EVIDENCE: core/quant/history.py:270-273 `FICC data module's single Yahoo touchpoint (patched to raise in tests)."""` / `from core.ficc.data import _yf_fetch, _period_for`; tests/quant_acceptance.py:286-288 `kis.KISClient = _FakeKIS`
     IMPACT: In bars.py, resolve clients and seams as module attributes at call time.
* [T-HERM-02 scope] The read-only trees are data/macro, core/rules, core/calendars/data, data/techfund,
  tests/fixtures/macro and docs/asset_expansion/cards. The home listing covers ~/.tradegen/macro and trading/rules.json.
  Neither core/odds nor ~/.tradegen/odds nor docs/asset_expansion/cache is watched. (C)
     EVIDENCE: tests/macro_acceptance.py:26-27 `READ_ONLY_TREES = ("data/macro", "core/rules", "core/calendars/data", "data/techfund",` / `"tests/fixtures/macro", "docs/asset_expansion/cards")`; :120-121 `roots = [home / "macro", home / "trading" / "rules.json"]`
     IMPACT: The odds wrapper, or one bracketing test, checks that venues.yaml, the study cache and the real
     ~/.tradegen/odds are untouched.
* [NotRun conventions] `NotRun(reason)`, with reasons starting REFDATA: or OWNER: (`require_owner`); the README also
  names PENDING. Compliance's only NOT_RUNs are two REFDATA symlink tests. (C)
     EVIDENCE: tests/notrun.py:25-35 `class NotRun(Exception):` / `"""Raised by a test that cannot run here; `.reason` starts with `REFDATA:` or `OWNER:`."""`; results: `('compliance/compliance_isolation/test_symlinks_are_refused', 'REFDATA: symlink creation needs Developer Mode')`
     IMPACT: Owner-act-dependent odds checks raise require_owner(...). Do not leave PENDING NOT_RUNs.
* [fixture manifest is macro-only] `require_fixture` and `unlisted()` work only on tests/fixtures/macro/MANIFEST.csv,
  and a macro test fails on any unlisted file there. tests/fixtures holds only macro/.
     EVIDENCE: tests/notrun.py:17-18 `FIXTURES = ROOT / "tests" / "fixtures" / "macro"` / `MANIFEST = FIXTURES / "MANIFEST.csv"`; tests/macro_m0_harness.py:282 `assert not unlisted(), ...`
     IMPACT: Put odds fixtures in code or in a new tests/fixtures/odds/, never in tests/fixtures/macro/.
* [temp_home] `temp_home()` makes `mkdtemp(prefix="tradegen_home_")`, sets TRADEGEN_HOME, clears
  `isolation._LINK_SCAN` on entry and exit, restores the variable and removes the dir. (C)
     EVIDENCE: tests/compliance_fixtures.py:15-31 `home = Path(tempfile.mkdtemp(prefix="tradegen_home_"))` / `os.environ["TRADEGEN_HOME"] = str(home)` / `isolation._LINK_SCAN.clear()`
     IMPACT: Reuse it as is. `core.isolation.state_root()` then resolves to the temp dir.
* [gate fixtures] `shipped_bytes(kind)`; `approved(rules=None, instruments=None, venues=None, *, seq=3, history=())`,
  which reads the LIVE shipped bytes and is lru-cached; `ctx(**overrides)` returns a SEALED Context: date 2026-10-23,
  shipped drafts approved, owner OK with cap 0.10, limits {total_loss_floor_krw 21,000; daily_loss_krw 5,000},
  age_of_majority, code_signed True, session S1 armed, equity 1,000,000, no positions. (C)
     EVIDENCE: tests/compliance_fixtures.py:58 `def approved(rules=None, instruments=None, venues=None, *, seq=3, history=()):`; :65-78 `def ctx(**overrides):` ... `date=_date(2026, 10, 23)` ... `limits={"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}` ... `equity_krw=1_000_000.0`
     IMPACT: `gate.screen(plan, F.ctx(date=plan.start), float(stake))` works with no owner log. Override equity
     (42,000 is the spec's stake) and limits per test. Odds tests that change venues.yaml pass `approved(venues=...)`.
* [owner-log fixtures] `test_key()` is a fixed Ed25519 key from seed bytes 0..31. Also `signed_entry`, `write_log`,
  `write_pubkey`, and `store_blob` (refused outside the temp home). Never import `test_key` by name, or the harness
  collects it. (C)
     EVIDENCE: tests/compliance_fixtures.py:91 `# Never `from tests.compliance_fixtures import test_key` in a test module: the harness would collect it as a test.`; :95-104 `Ed25519PrivateKey.from_private_bytes(bytes(range(32)))`
     IMPACT: Use `from tests import compliance_fixtures as F` and call `F.test_key()`.
* [signed-home helpers are private to compliance_store] `_pubkey_at`, `_owner_key`, `_sign`, `_approve`, `_full_home`,
  `NOW = 2026-10-24 09:00 KST` and `HELD` build a passing `load_context` home. (C)
     EVIDENCE: tests/compliance_store.py:242-243 `NOW = _dt.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)` / `HELD = model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})`; :246-254 `def _pubkey_at(path: Path):`; :290-299 `def _full_home(home: Path, *, rules_raw: bytes | None = None):`
     IMPACT: Odds tests that need a real `load_context` (CALENDAR_UNSIGNED end to end) either import these privates
     or have the follow-up move them into compliance_fixtures (DQ24). Never point PUBKEY_PATH at the repo pem.
* [calendar fixture set] `tests.macro_m1_calendars.fixture_set(key="main", docs=None) -> CalendarSet` writes signed
  ("TEST-FIXTURE (not an owner sign-off)") files into a `TemporaryDirectory(prefix="quantgen_cal_")`, cached per key
  per process. Coverage: KRX, kr_sessions and kr_regime_tags 1995-2027; NYSE 2006-2027. price_limit is 0.30 from
  2015-06-15. (C)
     EVIDENCE: tests/macro_m1_calendars.py:22 `SIGNER = "TEST-FIXTURE (not an owner sign-off)"`; :245-251 `def fixture_set(key: str = "main", docs: dict | None = None) -> CalendarSet:` ... `_CACHE[key] = (tmp, CalendarSet(Path(tmp.name)))`
     IMPACT: The spec names it (spec:172). Make variants under new keys with `fixture_docs()`. The "quantgen"
     prefix is only a name: refuse_quantgen compares resolved paths.
* [study cache, not fixtures] docs/asset_expansion/cache has 46 tracked close-only CSVs, outside every read-only tree.
     EVIDENCE: `git ls-files docs/asset_expansion/cache | wc -l` = 46; tests/macro_m1_pit.py:612-615 (labelled local smoke with NotRun REFDATA when absent)
     IMPACT: The D13 replay fixture is upbit_KRW-BTC.csv (section 6). Bars tests need synthetic open/close rows.
* [save/restore patterns] FICC's `_no_network` uses a tuple save and a try/finally restore. compliance_store's
  `_pubkey_at` is a contextmanager swap. paper_live swaps `sys.modules["yfinance"]`. The compliance self-tests swap
  `CA._REAL_HOME`, `CA.TESTS` and `CA.MODULES`.
     EVIDENCE: tests/ficc_acceptance.py:35-41 `saved = (data._fred_fetch, data._yf_fetch, config.FICC_CACHE_TTL_SECONDS)`; tests/paper_live_acceptance.py:164-183 `sys.modules["yfinance"] = types.SimpleNamespace(download=lambda *a, **k: frame)`; tests/compliance_guards.py:436-464
     IMPACT: Fakes nest inside the wrapper's raising patch, and restoring puts the raising stub back. Mirror the
     three compliance harness self-tests for odds.
* [timing] Compliance has 317 tests and 63.6 s of test time, slowest 3.11 s. The whole run sums to 608.6 s (macro
  415.8 s). The heaviest tests are Monte Carlo or end-to-end, up to 45.6 s. The only in-test time asserts are ad hoc.
  (C)
     EVIDENCE: qa/acceptance_results.json rows (summed); tests/engine_acceptance.py:961-962 `assert elapsed < 1.0, f"20k lookups took {elapsed:.2f}s"`; plan:1120 `The macro suite takes many minutes (most of the 14-minute full run)`
     IMPACT: Set an odds budget, for example at most 15 s per test and about 2 min for the suite, and comment the sizes.
* [README places] The suite list is at README.md:816, the compliance row at :839 ("315 PASS / 2 NOT_RUN") and the
  Total at :840 ("1043/1166 passed, 0 failed, 123 not run"). No test counts suites or README rows. The README-claims
  test checks disclaimers and four stale strings only. (C)
     EVIDENCE: README.md:816, :839, :840; tests/macro_ui_components.py:138-143 `for stale in ("229 checks", "245 checks", "the equity six", "FICC sixteen"):`
     IMPACT: The wiring task edits :816 in step with the registration test. The last task adds the odds row and Total.

## 2. Guards that bind new code under core/odds

* [what scans core/odds] (C)
  - Raw text and forbidden/dynamic imports: COMPLIANCE + ODDS.
  - Def names and seal_context: all of CORE.
  - An empty `__init__`: ODDS, when the file exists.
  - The HTTP-verb ban, the import allowlist, the wall clock and `__main__` blocks: COMPLIANCE ONLY.
  - Scans are recursive (rglob), so core/odds subfolders are scanned too.
     EVIDENCE: tests/compliance_guards.py:22 `COMPLIANCE, ODDS = CORE / "compliance", CORE / "odds"`; :233 `_scope(COMPLIANCE, ODDS).items() for h in _raw_hits(rel, src)`; :244 `_scope(CORE).items() for h in _def_hits(rel, src)`; :269 `_scope(COMPLIANCE).items() for h in _http_hits(rel, src)`; :300 `_scope(COMPLIANCE, ODDS).items()`; :340 `_scope(COMPLIANCE).items() for h in _allowlist_hits(rel, src)`; :361 `_clock_hits`; :385 `_main_block_hits`; :69-71 `for p in sorted(base.rglob("*.py")):`
     IMPACT: core/odds may import numpy, scipy, core.quant, data clients and yfinance, and may read the clock,
     without failing a compliance guard. After every odds task, also run
     `-m tests.compliance_acceptance compliance_guards/` and `compliance_store/`.
* [raw words, docstrings and comments included] Case-insensitive: private_key, seed_phrase, order_cash, order-cash,
  place_order, submit_order, tttc0802u, tttc0801u, vttc0802u, r18_research_log, r18_break_log, `context_log/`,
  `tests.reference`, reference_mode. Case-sensitive: CANO, KIS_ACCOUNT, ACNT_PRDT_CD, so upper-case "CANONICAL"
  hits. (C)
     EVIDENCE: tests/compliance_guards.py:27-30 `RAW_CI = ("private_key", "seed_phrase", "order_cash", ...` / `"reference_mode")` / `RAW_CS = ("CANO", "KIS_ACCOUNT", "ACNT_PRDT_CD")`; :229 `_raw_hits(X, "x = 1  # the CANONICAL form\n")`
     IMPACT: The catalogue and every docstring avoid these. Write "canonical" in lower case and name streams
     "seed" or "stream".
* [forbidden modules, every import form, any depth of the file] core.engine.orders, core.quant.forward_sim,
  core.quant.refusal, core.ficc.context_log, core.ficc.macro, core.ficc.flows_log and core.skills.macro_daily. The
  check covers DIRECT imports only. Sibling names (core.ficc.macro_schema, core.engine.books) are allowed. (C)
     EVIDENCE: tests/compliance_guards.py:43-44 `FORBIDDEN_MODULES = ("core.engine.orders", ...`; :283 `assert not _forbidden_hits(X, "from core.ficc import macro_schema\nfrom core.engine import books\n")`
     IMPACT: Declare LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0 locally and test its equality (section 7). A transitive
     path to orders.py goes unflagged; see section 3.
* [dynamic and star imports banned in core/odds] `from x import *`, `__import__`, `import_module`, `exec_module` and
  `load_module` are banned. So are `exec` and `eval` as ANY Name or Attribute (`df.eval` hits), and every form of
  importlib.util, importlib.machinery, runpy, pkgutil, zipimport, pydoc, timeit, code and cProfile.
  importlib.metadata is allowed. (C)
     EVIDENCE: tests/compliance_guards.py:49-51 `DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})` / `DYNAMIC_MODULES = ("importlib.util", ...`
     IMPACT: No pandas `.eval` and no timeit or cProfile. A dynamic import cannot shrink the closure.
     `importlib.metadata.version("cryptography")` is fine for provenance.
* [def names core-wide] No function named transfer, withdraw or deposit_address anywhere in core/; transfer_out is
  fine. T-RO-01 also bans CALLS named transfer, withdraw and others.
     EVIDENCE: tests/compliance_guards.py:32 `DEF_NAMES = frozenset({"transfer", "withdraw", "deposit_address"})`; tests/macro_m0_harness.py:44-50 `FORBIDDEN_CALLS = frozenset({` ... `"transfer", "transfer_funds", ...`
     IMPACT: Ledger helpers use other names.
* [seal_context only in owner.py] No Name, Attribute or alias `seal_context` in core/ outside core/compliance/owner.py.
     EVIDENCE: tests/compliance_guards.py:58 `SEAL_USER = "core/compliance/owner.py"`; :204-207
     IMPACT: core/odds gets a Context only from `owner.load_context` or as an argument. Tests seal via F.ctx().
* [empty `__init__`] core/odds/__init__.py, if it exists, must be 0 bytes. core.odds.plan is asserted acting, while
  core.odds is not. Every other core subpackage has an `__init__.py` (core/compliance's is 0 bytes). pyproject's
  `packages.find` finds regular packages only. (C)
     EVIDENCE: tests/compliance_guards.py:395-396 `assert CL.is_acting_module("core.compliance.gate") and CL.is_acting_module("core.odds.plan")` / `assert not CL.is_acting_module("core.compliance") and not CL.is_acting_module("core.odds")`; :408 `assert not (ODDS / "__init__.py").exists() or not _init_hits(ODDS / "__init__.py"), "core/odds/__init__.py"`; pyproject.toml `include = ["core*", "data*", "ui*"]`
     IMPACT: Create a 0-byte core/odds/__init__.py (DQ18). Plan P1 deliberately created none.
* [allowlist if extended to core/odds] `_allowed` accepts only stdlib, yaml, cryptography, core.isolation and
  core.compliance. core.odds itself, numpy, scipy, config and core.quant all fail, and so do the stdlib
  NETWORK_MODULES.
     EVIDENCE: tests/compliance_guards.py:160-163 `return (top in sys.stdlib_module_names or top in ("yaml", "cryptography")` / `or any(name == p or name.startswith(p + ".") for p in ("core.isolation", "core.compliance")))`
     IMPACT: Extending it to core/odds needs "core.odds", numpy and scipy added, plus a per-file network carve-out
     for bars (DQ20).
* [HTTP-verb guard if extended] It flags ANY attribute call named post, put, delete, patch or request.
     EVIDENCE: tests/compliance_guards.py:33 `HTTP_VERBS = frozenset({"post", "put", "delete", "patch", "request"})`; :131
     IMPACT: Widening it to core/odds forbids `np.delete`, `np.put` and `ndarray.put` in simulate and models.
* [wall-clock guard if extended] It flags datetime.now/utcnow/today, date.today, every `time.*` reader (perf_counter
  and monotonic included) and any `from time import`. Only the CLI main() bodies of rules.py and alerts.py are exempt.
     EVIDENCE: tests/compliance_guards.py:53-57 `CLOCKS = {...}` / `CLOCK_IN_MAIN = ("core/compliance/rules.py", "core/compliance/alerts.py")`
     IMPACT: Seeds never depend on time (spec 7.3). If extended, bars takes `now` as an argument.
* [T-RO-01 (core, data, ui, main.py, config.py, docs/*.py; docstrings stripped, strings kept)] It bans order and
  withdraw endpoint strings, private_key and seed_phrase. Case-sensitively it bans KIS_ACCOUNT, CANO and ACNT_PRDT_CD,
  and `/uapi/.../trading/` paths. It bans 21 order-client import tops (ccxt, web3, pyupbit, binance, okx, bybit,
  bitcoin, ...) and 27 call names. It bans post/put/delete/patch on URLs containing order, withdraw, transfer or
  deposit. Only core/engine/ and two skills modules may import orders. The YAML scan covers only
  core/skills/macro_workflows. (C)
     EVIDENCE: tests/macro_m0_harness.py:28-60 (FORBIDDEN_TEXT_CI, FORBIDDEN_TEXT_CS, FORBIDDEN_PATH_RE, FORBIDDEN_IMPORTS, FORBIDDEN_CALLS, MUTATING_HTTP, ORDERS_IMPORTERS_ALLOWED at :58, WORKFLOW_YAML at :60)
     IMPACT: venues.yaml text is unguarded by T-RO-01; the venues approval covers it instead.
* [test_08 / test_09 (raw runtime text)] test_08 bans order_cash, order-cash, place_order, submit_order and the three
  TR ids. test_09 bans KIS_ACCOUNT, CANO and ACNT_PRDT_CD (case-sensitive). (C)
     EVIDENCE: tests/acceptance.py:169-175 `def test_08_no_broker_order_path():` ...; :178-182 `def test_09_no_account_credentials_requested():`
     IMPACT: Covered by the raw-word rule above. "replace_order" also hits, because it contains "place_order".
* [other core-wide scans]
  - test_18 bans "eodhd" and "quartr" in runtime code.
  - T-TREND-04 bans forward_sim and refusal imports for acting modules.
  - The reference-mode scan bans `tests.reference`, `reference_mode` and `reference_only=True` in core/**.
  - "r18_research_log" may appear only in context_log.py.
  - The Kish design-effect scan bans `X/(1+(X-1)*Y)` shapes, `kish*` names and revision-count N.
  - T-TF-GOV-06 bans a 0.4 multiplier on a line with live words.
  - cardp restricts `timing_probe` and `_run_lagged` to cardp.py.
  - test_s4 lists only engine files.
     EVIDENCE: tests/acceptance.py:265-270 `for token in ("eodhd", "quartr"):`; tests/macro_m8_forward.py:506-511; tests/macro_m2_costed.py:365-372; tests/macro_m6_context.py:506-509; tests/macro_m7_ledger.py:333-338; tests/macro_tf_gov.py:262-263 `_MULT_04 = ...` / `_LIVE_WORDS = re.compile(r"haircut|expected[ _]live|live[ _]sharpe|step[ _]?9|\bg9\b", re.I)`; tests/macro_m7_cardp.py:502-503; tests/macro_m5_integration.py:55-58
     IMPACT: Write "40% removed" as `1 - LIVE_SHARPE_MULTIPLIER`, never `0.4 * mu`. Rewrite any effective-N formula
     algebraically. Never pass reference_only=True. Do not edit core/engine/*.
* [T-CTX-01: core.odds. is acting] ACTING_MODULE_PREFIXES includes "core.compliance." and "core.odds.". The earlier
  repo map's list, which lacked them, is stale. Acting modules may not import a PROTECTED module, directly or
  transitively (function level included). They may not name a PROTECTED callee anywhere, and may not carry a
  protected path fragment in a string. Imports under TYPE_CHECKING or `__main__` are skipped. The runtime guard is
  frame-based. Under `python -m core.odds.x` the module's `__name__` is "__main__", so it is not seen as acting. (C)
     EVIDENCE: core/ficc/context_log.py:71-73 `ACTING_MODULE_PREFIXES = (...` / `"core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act`; :78-81 PROTECTED_MODULES / PROTECTED_CALLEES / PROTECTED_PATH_FRAGMENTS; :99-106 (frame walk); :116-124 (skips)
     IMPACT: No local variable named macro_sheet. Every candidate import was probed clean (garch, strategies,
     validate, gate_stats, instruments, tf_books, gate_ledger, macro_artifacts, calendars, crypto_client,
     kis_client, yfinance, numpy), and the static report is `[]`. T-CTX-01 does not constrain the closure choice.

## 3. The D14 code hash: what core/odds pulls into the signed closure

* [seeds include core/odds/*.py, NON-recursively] code_files seeds core/compliance/*.py and core/odds/*.py (top-level
  glob). It follows every in-repo import at any depth, function bodies included, and skips only TYPE_CHECKING
  (`from typing import TYPE_CHECKING` bound once), `typing.TYPE_CHECKING` and a single `__name__ == "__main__"`. It
  adds every ancestor `__init__.py` and the RECORD files of cryptography and PyYAML only. Today's closure is 8 repo
  files plus 2 RECORD rows. (C)
     EVIDENCE: core/compliance/owner.py:773 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`; :727-736 `_import_nodes` (`function bodies included`); :603 `_RECORD_DISTS = ("cryptography", "PyYAML")`; critic probe `base 8`
     IMPACT: Every core/odds/*.py file joins the closure automatically, along with everything it imports. A
     subfolder file escapes D14 unless a seeded file imports it, so keep core/odds flat. Laziness avoids
     import-time side effects, not signing.
* [third-party code is never hashed] numpy, scipy, yfinance, pandas, requests and curl_cffi resolve to no repo file.
     EVIDENCE: core/compliance/owner.py:739-747 `"""The repo file of an in-repo module name; None for stdlib, third-party and attribute names."""`
     IMPACT: A numpy upgrade needs no re-sign and goes undetected (spec 6.4 accepts the venv as outside). Record the
     numpy version in the report.
* [closure growth per import, beyond today's 8 files] (C; critic and guards probes agree)
  - +0: numpy, scipy, yfinance, core.isolation, core.compliance.model.
  - +2: core.quant.garch; core.ficc.macro_schema.
  - +20: data.crypto.crypto_client and data.krx.kis_client (the same 20: config.py, data/**, core/ficc/data.py,
    core/quant/history.py, core/markets.py ...).
  - +22: core.quant.validate; core.quant.instruments.
  - +23: core.quant.gate_stats.
  - +29: core.quant.gate_ledger.
  - +34: core.calendars.store; core.calendars.clocks.
  - +35: core.calendars.regime.
  - +46, core/engine/orders.py included: core.quant.strategies; core.ficc.macro_artifacts.
  - +53, orders.py included: core.quant.tf_books.
  - +55, a 63-file closure of 1,065,057 bytes: the spec's full import set.

  CLARIFIED: costs_cal's "24" and "37" count closure files including core/__init__.py and core/isolation.py.
     EVIDENCE: scratchpad odds_plan/critic/closure_probe.py (`core.quant.garch: +2`, `core.quant.gate_stats: +23`, `core.quant.tf_books: +53 ... 'core/engine/orders.py'`, `core.ficc.macro_artifacts: +46 ... 'core/engine/orders.py'`, `core.quant.gate_ledger: +29`); guards probe `SPEC SET adds 55 files, 1065057 bytes`
     IMPACT: Only garch, macro_schema, model and isolation are cheap. Even constant-only imports (DELIST_STRESS via
     tf_books, LIVE_SHARPE_MULTIPLIER via gate_stats, tree_hash via macro_artifacts) drag in config, the network
     clients and, for some, core/engine/orders.py. DQ1 is the plan's central decision.
* [why the closure explodes: hub edges] validate lazily imports history and instruments. history imports config at
  module level and every data client lazily. config lazily imports crypto_client and core.ficc.data. store lazily
  imports publication and core.rules.governance. risk_layer lazily imports core.engine.books, and
  core/engine/__init__.py imports orders.
     EVIDENCE: core/quant/validate.py:93-94 `from core.quant.history import _looks_crypto` / `from core.quant.instruments import INSTRUMENTS`; core/quant/history.py:44 `import config`; config.py:375 `from data.crypto.crypto_client import provider_status`; core/quant/risk_layer.py:551 `from core.engine import books as _books`; core/engine/__init__.py:4 `from core.engine.orders import OrderBook, OrderStatus, SimulatedOrder, order_id`
     IMPACT: No single helper can be picked from validate, instruments, gate_stats, tf_books, gate_ledger or
     macro_artifacts without signing the data layer.
* [re-sign on any closure change] code_hash is the sha256 of the canonical JSON of (path, sha256) pairs. load_context
  recomputes it on every call and sets code_signed only when it equals the latest code_approved. Otherwise the gate
  returns BLOCK "unsigned code" for new exposure (exits are unaffected). Measured cost: 0.20 s for 10 entries, 0.85 s
  for 63.
     EVIDENCE: core/compliance/owner.py:796-798 `def code_hash(repo_root: Path) -> str:`; :994 `current = code_hash(REPO_ROOT)`; :997 `signed = owner.ok and bool(current) and code_approval(check) == current`; core/compliance/gate.py:426 `return out + ([] if ctx.code_signed is True else ["unsigned code"])`
     IMPACT: Under the full import set, any edit to config.py, the data clients or core/engine blocks new exposure
     until the owner signs again. Build the Context once per comparison.
* [tests that pin the SMALL closure] compliance_store asserts that the repo part EQUALS core/__init__.py +
  core/isolation.py + core/{compliance,odds}/*.py, that config.py and data/ are absent, and that the venv rows are
  exactly PyYAML + cryptography. compliance_signer asserts that config.py and data/ are absent. (C)
     EVIDENCE: tests/compliance_store.py:137-140 `expected = {"core/__init__.py", "core/isolation.py"} | {` / `f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}` / `assert repo == expected, sorted(repo ^ expected)` / `assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)`; :150 `assert venv == {yaml_record, crypto_record}, venv`; tests/compliance_signer.py:638 `assert "config.py" not in paths and not any(p.startswith("data/") for p in paths), paths`
     IMPACT: numpy or yfinance only: both tests pass. garch: :139 fails (+2) and `expected` needs amending.
     Anything reaching data/ or config.py: both fail, and their stated intent must be rewritten, not just the sets.
* [spec vs plan contradiction] Spec 6.4 expects the closure to include config.py, core/calendars/** and the core/quant
  and data modules. Plan P6, the guard docstring and both closure tests assume it stays small.
     EVIDENCE: spec:584-587 `- their in-repo `.py` import closure, found by an AST import scan (for example `config.py`, `core/isolation.py`,` / ``core/calendars/**`, the `core/quant` and `data/` modules they reach).`; plan:16835-16838 `P6 ... Because of the import allowlist, the closure is `core/__init__.py`, `core/isolation.py`,` / ``core/compliance/*.py` (plus `core/odds/*.py` later).`; tests/compliance_guards.py:306-308
     IMPACT: The odds plan must choose and record the decision, and amend the losing side (DQ1).
* [signer copy] tools/signer/sign.py duplicates `_RECORD_DISTS` and `code_files`, seeding core/odds in the same way,
  and a test asserts the two agree. Updating the owner's copy is an owner act. (C)
     EVIDENCE: tools/signer/sign.py:693 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`; tests/compliance_signer.py:630-634 `mine = signer.code_files(ROOT)` ... `assert mine == theirs`; spec:598-599 `Updating the owner's copy is a` / `deliberate owner act: read the diff, re-hash, re-record.`
     IMPACT: Adding core/odds files needs no signer change. Changing the closure ALGORITHM (RECORD dists,
     recursive seeds, `_skipped`) needs both copies changed in lockstep, plus an owner act.
* [package `__getattr__` re-exports escape D14] core/calendars/__init__.py re-exports v2 names via
  `importlib.import_module`, so `from core.calendars import event_calendar` hashes only the `__init__`. (C)
     EVIDENCE: core/calendars/__init__.py:224-229 `def __getattr__(name: str):` ... `return getattr(importlib.import_module(f"{__name__}.{module}"), name)`
     IMPACT: Import concrete submodules (`core.calendars.store`, `.clocks`, `.regime`), never package re-exports.
     A candidate follow-up guard.
* [injected objects run unsigned code] D14 hashes what core/odds IMPORTS, not what it calls on injected objects (for
  example a caller-built CalendarSet). TYPE_CHECKING-only imports stay out of D14 and T-CTX-01.
     EVIDENCE: core/compliance/owner.py:750-764 `_repo_imports` reads Import/ImportFrom nodes only; :699-705 `_typing_flag`; spec:169 "`simulate()` takes `cal: CalendarSet`"
     IMPACT: Dependency injection keeps the closure small, but the injected code's integrity then rests on the data
     approvals and recorded hashes. The plan must say so in plain words.
* [import-time side effects] Importing config runs `load_dotenv()`. Importing data.krx.kis_client runs
  data/krx/__init__ -> gateway -> opendart_client, and binds `_TOKEN_PATH = config.state_root() / ...` at import, which
  runs the link scan.
     EVIDENCE: config.py:26-30 `from dotenv import load_dotenv` / `load_dotenv()`; data/krx/kis_client.py:53 `_TOKEN_PATH = config.state_root() / "kis_token.json"`; data/krx/__init__.py:2 `from data.krx.gateway import Answer, KRXGateway`
     IMPACT: If bars imports data clients, it does so lazily inside the seam functions, so `import core.odds.bars`
     stays side-effect-free.

## 4. Compliance interfaces the odds engine consumes (Appendix A contract as built)

### 4.1 gate.screen()

* [signature, never raises] `screen(plan, ctx, first_stake_krw: float) -> model.Screening`. Any exception becomes a
  BLOCK Screening, "state: internal error <type>". (C)
     EVIDENCE: core/compliance/gate.py:611 `def screen(plan, ctx, first_stake_krw: float) -> model.Screening:`; :616-619 (try/except -> `_fallback(None, ctx, f"state: internal error {type(exc).__name__}")`)
     IMPACT: Read the verdict from the Screening. Never rely on an exception.
* [P3 duck typing] It reads only `plan.leg`, `leg.venue`, `leg.symbol`, `plan.start` and `plan.horizon_days`, each via
  getattr with default None. A frozen kw_only Plan/Leg works (probe ALLOW).
     EVIDENCE: core/compliance/gate.py:623-625 `leg = getattr(plan, "leg", None)` / `venue_id, symbol = getattr(leg, "venue", None), getattr(leg, "symbol", None)` / `start, horizon = getattr(plan, "start", None), getattr(plan, "horizon_days", None)`; plan:16827-16828 `P3 ... it reads `plan.leg.venue`, `plan.leg.symbol`, `plan.start` / (a `date`) and `plan.horizon_days` (an `int`) only.`
     IMPACT: plan.py keeps these attribute names exactly. Model, bracket, sizing, edge_source and fraction are
     invisible to the gate.
* [start: exact type and equal to ctx.date (P37)] `type(start) is model.date` is required, so a datetime or a pandas
  Timestamp gives "malformed: plan". Under a sealed ctx, a start other than ctx.date gives "malformed: plan start".
  horizon must have `type(horizon) is int` and be > 0, so bool and numpy ints are refused. (C)
     EVIDENCE: core/compliance/gate.py:636-639 `if type(start) is not model.date or type(horizon) is not int or horizon <= 0:` ... `if start != ctx.date:`; plan:222-224 `P37 `screen()` decides the leg on `ctx.date`. Under a sealed context, a plan must start on `ctx.date`` ... `The odds engine screens a plan on its start date.`
     IMPACT: Plan.start is a plain `date` equal to the Asia/Seoul date of the `now` given to load_context. A
     future-start plan cannot be screened. plan.py stores `int(horizon_days)` and refuses bool. Tests use 2026-10-23.
* [stake type: numpy floats are malformed; zero is malformed] The stake becomes Intent.notional_krw, checked by
  `_number`: `type(v) is float` and finite, or `type(v) is int` with |v| < 2**63. A numpy.float64 gives "malformed:
  notional_krw". New exposure needs notional > 0, so 0, a negative or NaN gives BLOCK "malformed: notional_krw".
  The ledger carries this to odds. (C)
     EVIDENCE: core/compliance/gate.py:516-519 `def _number(value) -> bool:` / `if type(value) is float:` / `return math.isfinite(value)` / `return type(value) is int and abs(value) < 2 ** 63`; :62-67 `more += [] if intent.notional_krw > 0 else ["malformed: notional_krw"]`; ledger:244 `Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw)`
     IMPACT: Pass `float(stake)`. Decide STUCK_AT_START (after lot rounding and the venue minimum) BEFORE screen, and
     never call screen with 0. Test both.
* [the synthetic intent] screen decides a cash `buy`: quantity 1.0 (nominal), notional = stake,
  counter = `venue.quote_for(inst)`, and asset and multiple from the approved map. The intent hash can be
  reproduced.
     EVIDENCE: core/compliance/gate.py:630-633 `# quantity is nominal: a buy's verdict depends on its notional, never on its units` / `intent = Intent(venue=venue_id, symbol=symbol, counter_symbol=venue.quote_for(inst) if inst is not None else "", ...`
     IMPACT: The stake is the KRW notional of the first entry. On OKX the counter is USDT. simulate can rebuild the
     Intent and check `decision.intent_hash`.
* [no usable state / unsealed / unsigned] (C)
  - Sealed ctx but owner not OK or active unusable: BLOCK, kind new_exposure, reason "state: owner log <reason>" or
    "state: <reason>", no flags.
  - Unsealed ctx: BLOCK "state: context not from load_context".
  - code_signed not True: BLOCK "unsigned code".
     EVIDENCE: core/compliance/gate.py:627 `state = ctx.active if sealed and ctx.owner.ok and _usable(ctx.active) else None`; :486-489 `return f"state: owner log {ctx.owner.reason or ctx.owner.status}"`; :634-635 `if not sealed: return _screening(decide(intent, ctx), (), None)`; :423-426 `_preconditions`
     IMPACT: The first core/odds/*.py file changes the code hash, so screening stays "unsigned code" until the
     owner re-signs. Word "state: ..." refusals for the owner and print no probability (spec 9).
* [RULE_CHANGE_IN_HORIZON source: Screening.flags] For each venue row matching the leg, any review_by, auto_off or
  effective_until with `start <= date < start + horizon` is flagged as (date, field, row_id), sorted. exit_date is the
  earliest flag date. The literal "RULE_CHANGE_IN_HORIZON" appears only in the spec. (C)
     EVIDENCE: core/compliance/gate.py:643-651 `first, end = start.toordinal(), start.toordinal() + horizon` ... `for what, when in (("review_by", row.review_by), ("auto_off", row.auto_off),` ... `if when is not None and first <= when.toordinal() < end:`; :657 `exit_date = flags[0][0] if flags else None`; grep: only spec:538, :900 and a review file
     IMPACT: report.py raises RULE_CHANGE_IN_HORIZON when `screening.flags` is non-empty. simulate force-exits at
     exit_date, or at the next check point when that date is not a session (spec 6.3).
* [every horizon over about a month is cut at review_by] All 47 shipped rows have review_by 2026-11-22 (25 rows) or
  2026-11-23 (22 rows). A 60-day plan from 2026-10-24 exits at 2026-11-22 or 2026-11-23; a 10-day plan gets no flag.
  The OKX rows also carry effective_until 2027-02-18 and auto_off 2026-12-03. (C)
     EVIDENCE: `grep -o 'review_by...' core/compliance/kr_rules.yaml | uniq -c` -> `25 2026-11-22`, `22 2026-11-23`; core/compliance/kr_rules.yaml:507 `effective_until: "2027-02-18"`, :519 `grey: {cap_key: okx_equity_share, auto_off: "2026-12-03"}`; core/compliance/rules.py:524-525 (P15 monthly cadence)
     IMPACT: State the cut and test a forced exit at a rule date. Whether review_by should force an exit is DQ6.
* [flags ignore effective_from] A row that STARTS mid-horizon is not flagged. No shipped row has a future
  effective_from.
     EVIDENCE: core/compliance/gate.py:645-648 (only the three fields)
     IMPACT: A compliance follow-up item (section 8).
* [Screening and Decision] Screening is a frozen dataclass: decision, allowed (verdict in ALLOW or ACK_REQUIRED),
  flags, exit_date, screening_hash = sha256(canonical_json({decision, allowed, flags, exit_date, window})). The window
  is hashed but not stored. Decision has verdict, kind, reasons, warnings, intent_hash, state_hash, code_hash,
  owner_head, ctx_hash, date, decision_id and ack. A Screening is not registered the way permits are. (C)
     EVIDENCE: core/compliance/model.py:213-219 `class Screening:` ... `screening_hash: str`; core/compliance/gate.py:654-660 `body = {"decision": d, "allowed": allowed, "flags": flags, "exit_date": exit_date, "window": window}`; core/compliance/model.py:181-199 `class Decision:`
     IMPACT: To "refuse an unscreened plan", simulate recomputes screening_hash with window = (plan.start,
     plan.horizon_days), checks allowed, `decision.date == plan.start` and intent_hash. This is discipline, not
     security. Provenance takes code_hash, owner_head, state_hash and ctx_hash from screening.decision.
* [reason prefixes and order] "conduct: ", "floor: ", "malformed: <field>", "state: ...", "unsigned code", "no row",
  "stale: review by <date> passed (<id>)", "hard_block: <id>", "out_of_scope: <id>", "needs live broker evidence
  (execution spec): <id>", "requires <item>: <id>", "auto_off <date>: <id>", "cap unset: <id>", "cap exceeded: <id>",
  "leverage <x> above <max>: <id>", "ack required: <id>" and "destination: ...". They are ranked conduct, floor,
  malformed, state, unsigned code, then the rest, with ack required last.
     EVIDENCE: core/compliance/gate.py:29 `_RANKS = ("conduct: ", "floor: ", "malformed: ", "state: ", "unsigned code")`; :526-533 `_ranked`
     IMPACT: Map refusals by `startswith` on reasons[0] and show the row id. Internal names never reach rendered text.
* [GREY_LEG is not visible in the verdict] For an OKX BTC leg with no session ack: ACK_REQUIRED, allowed True,
  ('ack required: KR-OKX-SPOT',). Once acked it is plain ALLOW with ack None, but warnings still carry the OKX text.
  Only KR-KIS-US-OPTION and KR-OKX-SPOT carry warnings. auto_off and cap_key exist only on grey rows. The privates
  `_in_force(state, intent, cls, on)` and `_matches(row, intent, cls)` exist. (C)
     EVIDENCE: probe (compliance_iface) `okx BTC ACK_REQUIRED new_exposure True ('ack required: KR-OKX-SPOT',)`, `okx acked ALLOW None ()`; core/compliance/kr_rules.yaml:307, :513; core/compliance/gate.py:295 `def _in_force(state, intent, cls, on) -> list:`, :385 `def _matches(row, intent, cls) -> bool:`
     IMPACT: GREY_LEG needs the in-force matching rows' `treatment == "grey"`: either the privates, a copy, or a
     public helper or Screening field added by the follow-up (DQ5). ACK_REQUIRED counts as screenable and still
     raises GREY_LEG.
* [grey cap depends on ctx.equity_krw] OKX is BLOCK "cap exceeded" when held + other reservations + stake > cap ×
  ctx.equity_krw, BLOCK "cap unset" without okx_equity_share, and BLOCK on or after auto_off 2026-12-03. Only the
  first stake is screened.
     EVIDENCE: core/compliance/gate.py:334-339 `if held + others + intent.notional_krw > cap * ctx.equity_krw:`; :612-615 docstring `The plan's single leg decided on ctx.date as a cash buy of first_stake_krw`
     IMPACT: The equity passed through Positions decides OKX screening. Later OKX stakes (bold play after a win)
     are never screened (DQ7).
* [shipped-table verdicts per candidate leg (probe, stake 50,000)] ALLOW: kis 005930, 069500, SPY, AAPL, BITO; upbit
  BTC and USDT; bithumb, coinone and korbit BTC. ACK_REQUIRED: okx BTC. BLOCK: kis 252670 and TQQQ (live evidence),
  kis IBIT (floor: etp_crypto_spot), okx USDT (malformed: counter_symbol), gopax BTC (malformed: venue).
     EVIDENCE: compliance_iface probe lines `kis 005930 ALLOW ...` to `gopax BTC BLOCK malformed False (...)`
     IMPACT: The odds whitelist (share, etp_1x, coin; +1; long; cash) is narrower than the gate's ALLOW set. BITO
     (etp_crypto_futures_1x) is UNSUPPORTED_PRODUCT in plan.py before screening.

### 4.2 Context, limits, load_context

* [Context fields; limits live in owner state] Context has date, active, snapshot, owner, code_hash, code_signed,
  session, equity_krw, holdings, shorts, exposure and ctx_hash. Limits are in `ctx.owner.limits` and caps in
  `ctx.owner.caps`. There is no calendar field.
     EVIDENCE: core/compliance/model.py:165-178 `class Context:`; :139-140 `caps: Mapping[str, float] = field(default_factory=dict)` / `limits: Mapping[str, float] = field(default_factory=dict)`
     IMPACT: simulate's `limits` = ctx.owner.limits. L = limits["total_loss_floor_krw"], and the daily limit =
     limits["daily_loss_krw"].
* [unset = absent key] owner_state keeps only keys that have taken effect. BROKEN state has empty caps and limits. The
  only keys are total_loss_floor_krw, daily_loss_krw and okx_equity_share. Valid values: floor >= 0 (0 is a valid
  SET value), daily > 0, cap in (0, 1]. Values arrive as Python floats. (C)
     EVIDENCE: core/compliance/owner.py:436 `_LIMIT_KEYS = ("total_loss_floor_krw", "daily_loss_krw")`; :150-152 `"cap_set": {...lambda v: _number(v) and 0 < v <= 1}, "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0, "daily_loss_krw": lambda v: _number(v) and v > 0}`; :559-561
     IMPACT: LIMITS_UNSET = `not ctx.owner.ok or not {"total_loss_floor_krw", "daily_loss_krw"} <= set(ctx.owner.limits)`.
     Never treat L = 0 as unset. The literal LIMITS_UNSET is only in the spec (575, 700, 1045).
* [first setting takes effect the next Asia/Seoul day] An unset value counts as the tightest, so the first limit_set
  is a loosening and applies only from the next Seoul date. A loosening never applies inside an armed session or
  after a halt, and a halt floor raises total_loss_floor_krw for good.
     EVIDENCE: core/compliance/owner.py:483-484 `An unset cap or limit counts as the tightest, so setting one is a loosening.`; :525-528 `def loosening_counts(e, on) -> bool:`; :557-558 `values["total_loss_floor_krw"] = max(values["total_loss_floor_krw"], halt_floor)`
     IMPACT: On the day the owner signs limits, odds still says LIMITS_UNSET. The text says "limits take effect from
     the next day".
* [load_context real signature] `load_context(now, positions, *, session_id=None) -> Context`, not `load_context(now)`.
  now must be aware (ValueError otherwise). positions must be a model.Positions with equity_krw > 0, or active becomes
  invalid. With session_id None no session ack can match. (C)
     EVIDENCE: core/compliance/owner.py:964 `def load_context(now: _dt.datetime, positions: model.Positions, *, session_id: str | None = None) -> model.Context:`; :1004-1006 `problem = _positions_problem(positions)`; :156 `"session_ack": {"session_id": _text, ...}`; core/compliance/rules.py:801 (`model.Positions(equity_krw=1.0)` precedent)
     IMPACT: Build `model.Positions(equity_krw=float(W))` (DQ7) and an aware `now`. OKX stays ACK_REQUIRED
     (allowed) with session None.
* [load_context writes and re-hashes] It verifies the log against owner_pubkey.pem and the anchors, folds owner state,
  loads the in-force tables from the store, computes code_hash(REPO_ROOT), WRITES a snapshot when the active state is
  valid, reads the latest snapshot, and turns any other exception into a sealed BROKEN context.
     EVIDENCE: core/compliance/owner.py:987-1017 (`current = code_hash(REPO_ROOT)`, `write_snapshot(active, owner.head)`, `snapshot = latest_snapshot()`); :978-984
     IMPACT: It is not read-only: it creates <state_root>/compliance/snapshots/*.json. The odds suite runs under a
     temp home. Call it once per comparison.

### 4.3 Calendar approval

* [the calendar approval is not in Context] APPROVAL_KINDS includes "calendar", but load_context loads only the three
  tables. rules._calendar_line re-reads and re-verifies the log: verify_log(_log_lines(log_path()),
  read_pubkey(PUBKEY_PATH), read_anchors()), then in_force(_up_to(log, iso_utc(moment)))["calendar"], then store_get.
  `_log_lines` and `_up_to` are private. The CLI already prints "calendar: no signed approval, so KRX and US plans are
  refused (crypto plans only)". (C)
     EVIDENCE: core/compliance/owner.py:29 `APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")`; :602 `_TABLES = ("rules", "instruments", "venues")`; core/compliance/rules.py:903-920 `def _calendar_line(ctx, root: Path, moment) -> str:` ... `signed = owner.in_force(owner._up_to(log, model.iso_utc(moment))).get("calendar", ("", 0))[0]` ... `return "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"`
     IMPACT: Odds needs its own lookup: the privates, or a public `owner.calendar_in_force(now)` / a Context field
     added by the follow-up (DQ4). Word CALENDAR_UNSIGNED like the CLI.
* [calendar set framing, hash and store layout] `rules.calendar_stream(dir)` frames every regular file (sorted, name
  NUL bytes NUL; links refused), and `calendar_sha256` hashes it. The store keeps
  `<state_root>/compliance/approved/calendar/<sha>/` as a directory. store_get rebuilds the stream and returns None for
  a missing, altered or linked set. The shipped draft (17 files) hashes to 42c7b8e0...7547. `CalendarSet(data_dir=...)`
  accepts any directory. (C) CORRECTED (vs the earlier repo map): "No function hashes a calendar set as a whole"
  (docs/superpowers/plans/2026-10-23-compliance-gate-repo-map.md:351) is stale.
     EVIDENCE: core/compliance/rules.py:721-742 `def calendar_stream(data_dir: Path) -> bytes:` ... `def calendar_sha256(data_dir: Path) -> str:`; core/compliance/owner.py:670-680 `path = store_dir() / kind / (sha256 if kind == "calendar" else f"{sha256}.yaml")` ... `return raw if model.sha256_hex(raw) == sha256 else None`; plan:16872-16873 `P21 The calendar approval covers every regular file in `core/calendars/data/` (17 files including `MANIFEST.yaml`` / `and `market_closes.yaml`); `data/calendars/*.json` is excluded.`
     IMPACT: The approval covers the WHOLE set, not per market. Production verifies store_get(signed), then builds
     `CalendarSet(store_dir()/"calendar"/signed)`, with a TOCTOU window to document. Never load the repo draft
     unless its calendar_sha256 equals the signed sha. Reuse calendar_stream; never write a second framing.
     calendar_sha256 can still raise OSError (ledger:102), so catch it.

### 4.4 venues.yaml and the strict parser

* [current content] schema tradegen.venues/1, six venues.
  - kis: sections [krx, us], settlement [KRW, USD], quote_by_currency true, deposits [].
  - upbit: [crypto], KRW, markets [[BTC, KRW], [USDT, KRW]], default_quote KRW, deposits BTC on bitcoin with no tag
    (UNVERIFIED).
  - bithumb, coinone, korbit: [crypto], KRW, [[BTC, KRW]].
  - okx: [crypto], [USDT, USDC], markets [[BTC, USDT], [BTC, USDC]], default_quote USDT, deposits BTC on bitcoin
    (UNVERIFIED).
  - No lots, minimums, ticks or fees. The header says the odds plan adds them, which needs a new approval.
     EVIDENCE: core/odds/venues.yaml:2-3 `# ... The compliance plan writes markets, settlement and deposits only; the` / `# odds plan adds lots, minimums and ticks later, which changes this file's sha256 and needs a new approval.`; :5 `schema: tradegen.venues/1`; :16 `markets: [[BTC, KRW], [USDT, KRW]]   # KRW-quoted only (P22)`; :45 `markets: [[BTC, USDT], [BTC, USDC]]`
     IMPACT: The odds plan owns these additions. It keeps the deposits block as is and invents no networks (owner
     act, ledger:120).
* [ADDING KEYS TODAY MAKES THE FILE INVALID] The top level allows exactly {schema, venues}. A venue requires
  {sections, settlement, source} and allows {markets, quote_by_currency, default_quote, deposits}. Unknown keys raise
  Invalid. Tests pin that `minimum_krw` and a top-level `extra` are refused. (C)
     EVIDENCE: core/compliance/rules.py:636-637 `_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})` / `_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits"})`; :701 `_keys(doc, "venues", frozenset({"schema", "venues"}))`; tests/compliance_tables.py:633 `bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")`; :615 `bad(lambda d: d.update(extra=1), "venues: unknown key(s) ['extra']")`
     IMPACT: The order is: (1) extend rules.py (new optional keys with validation, Venue fields with defaults, amend
     the :633/:615 pins); (2) change venues.yaml; (3) the owner re-approves venues and re-signs the code. A signed
     venues file that the running parser refuses makes approved_state invalid, and everything new BLOCKs (DQ8).
* [byte-level pins on the shipped venues bytes] tests/compliance_gate.py partitions on `b"\n  okx:"` and needs exactly
  one `tag_required: false` before AND after it. It also needs exactly one `markets: [[BTC, KRW], [USDT, KRW]]` (the
  upbit line). (C; new, critic)
     EVIDENCE: tests/compliance_gate.py:695-697 `head, sep, tail = raw.partition(b"\n  okx:")` / `assert sep and head.count(b"tag_required: false") == 1`; :998-1000 `assert sep and tail.count(b"tag_required: false") == 1`; :336-340 `market = b"markets: [[BTC, KRW], [USDT, KRW]]"` ... `old_venues.count(market) == 1`
     IMPACT: Odds additions keep `okx:` at two-space indent, add no "tag_required" text anywhere, and keep the upbit
     markets line in exactly that flow form.
* [shape and provenance pins] The file must stay UTF-8 with no BOM, LF, newline-ended and <= 256 KB. It holds exactly
  six venues with pinned fields. Each venue `source` is a repo reference or "UNVERIFIED: owner to confirm before
  approval". Every https URL must already appear in reports/, research_notes/ or the techfund bundle. (C; new, critic)
     EVIDENCE: tests/compliance_tables.py:897-902 `assert not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, kind`; :1089-1106 `def test_shipped_venue_facts_p22():`; :1136-1138 `assert _t5_ref_ok(entry["source"]) or entry["source"] == _T5_UNVERIFIED, vid`; :1141-1150 `def test_shipped_urls_come_from_the_research():`; :801 `_T5_UNVERIFIED = "UNVERIFIED: owner to confirm before approval"`
     IMPACT: Record a source before citing it, or mark the data UNVERIFIED. Adding a seventh venue breaks the P22 pin.
* [approved copy, not the draft] The in-force venue bytes come from store_get of the latest approval and are parsed
  against the approved instrument map. The repo file is a draft that --check diffs.
     EVIDENCE: core/compliance/owner.py:947-961 `_approved_now` (`raws[kind] = store_get(kind, approvals[kind][0])`); core/compliance/rules.py:778-779 `_DRAFTS = (... ("venues", "core/odds/venues.yaml"))`
     IMPACT: Read lots, minimums, ticks and fees from `ctx.active.venues.venues[venue_id]`, never from the file on
     disk. A missing entry gives NOT_TRADABLE.
* [Venue API] Venue has id, sections, settlement, markets, quote_by_currency, default_quote, deposits, `is_market(inst,
  counter)` and `quote_for(inst)`; quote_for is inst.currency on kis and default_quote elsewhere. (C)
     EVIDENCE: core/compliance/rules.py:306-326 `class Venue:` ... `return inst.currency if self.quote_by_currency else self.default_quote`
     IMPACT: The leg quote currency is KRW for upbit and KRX, USD for US and USDT for okx.
* [the store refuses "odds"] store_put("odds", ...) raises ValueError. Only the four approval kinds are stored. (C; new)
     EVIDENCE: tests/compliance_store.py:52 `_raises(lambda: owner.store_put("odds", raw, (1, "a" * 64)), ValueError)`; :41 `owner.store_get("odds", sha) is None`
     IMPACT: An odds data file (catalogue, typed inputs) cannot be owner-approved without a compliance change (DQ19).

### 4.5 instruments.yaml

* [fields and classes] Each entry has asset, multiple, underlying, class, cost_book, currency, tax_basis and source.
  Instrument.cls is the derived class (it must equal the declared one). There are 17 entries:
  - krx: 005930 (share, KRX_stock_book, krx_small_holder_exempt); 069500 (etp_1x, KRX_ETF_line); 252670
    (etp_leveraged); 114800 (etp_index_inverse).
  - us (USD, US_shares_KIS, overseas_22pct_over_2.5m): TQQQ, SH, SPY (etp_1x), AAPL (share), IBIT, FBTC, ETHA, GDLC
    and EZPZ (etp_crypto_spot), BITO (etp_crypto_futures_1x).
  - crypto (currency KRW, crypto_venue, crypto_22pct_from_2027): BTC, USDT and USDC (coin).
     EVIDENCE: core/compliance/rules.py:571 `_ENTRY_KEYS = frozenset({"asset", "multiple", "underlying", "class", "cost_book", "currency", "tax_basis", "source"})`; :277-288 `class Instrument:`; core/compliance/instruments.yaml:9-164; tests/compliance_tables.py:894 `assert len(imap.entries) == 17 and len(facts.venues) == 6`
     IMPACT: The odds-eligible legs are kis 005930, AAPL, 069500 and SPY, and BTC/USDT/USDC where a market exists.
     plan.py checks `inst.cls in {"share","etp_1x","coin"} and inst.multiple == 1.0` on
     `ctx.active.instruments.lookup(venue.sections, symbol)`. cost_book and tax_basis come from the same Instrument.
* [class vocabulary] Classes include share, etp_1x, coin, konex_share and etp_crypto_futures_1x, among others. ETNs
  are not a separate asset: a KRX ETN would be krx_etp. derive_class rule 6 gives etp_1x for x1 single, index or
  basket ETPs. (C; new)
     EVIDENCE: core/compliance/rules.py:44-47 `CLASSES = frozenset({... "etp_crypto_futures_1x", "etp_1x", "share", "konex_share", "coin", ...})`; :225-226 `if underlying in ("single", "index", "basket"):` / `return "etp_1x"`
     IMPACT: KONEX shares are class konex_share, outside the whitelist, so structural_max never sees a KONEX leg. Say
     so (spec 7.4 names KONEX).

### 4.6 Provenance the gate already carries

* [context provenance] ctx.code_hash and code_signed; ctx.owner.head (seq, row_sha256); ctx.owner.fingerprint
  ("SHA256:<hex>", "" without a pem); ctx.active.hashes {rules, instruments, venues}, seq and state_hash; ctx.ctx_hash.
  The first recorded fingerprint is only reachable via the private `owner._first_recorded()`.
     EVIDENCE: core/compliance/model.py:136-147 `head: tuple[int, str] = (0, "") # (seq, row_sha256) of the last line` ... `fingerprint: str = ""`; core/compliance/rules.py:763-764 `hashes={"rules": file_sha256(rules_raw), ...}`; core/compliance/owner.py:913-918
     IMPACT: The report provenance reads these. The calendar sha is not among them (4.3).

## 5. Data: what core/odds/bars.py stands on

### 5.1 KRX (KIS daily)

* [the only KRX open/close source] `KISClient.daily(code, *, start=None, end=None, adjusted=True) -> list[dict]` calls
  FHKST03010100 on inquire-daily-itemchartprice. Rows are {date ISO, open, high, low, close, volume, source "KIS"},
  ascending. `_f` maps "", "-" and "None" to None. At most 100 rows per call. The default end is naive
  `datetime.now()`. `adjusted=True` sends FID_ORG_ADJ_PRC "0" (split- and rights-adjusted, no cash dividends). The
  raw fields flng_cls_code, prtt_rate and mod_yn are dropped. (C)
     EVIDENCE: data/krx/kis_client.py:273-274 `def daily(self, code: str, *, start: Optional[str] = None,` / `end: Optional[str] = None, adjusted: bool = True) -> list[dict]:`; :288 `"FID_ORG_ADJ_PRC": "0" if adjusted else "1",`; :292-306 (row build, sort); :125-130 `_f`; core/quant/history.py:226-227 `adjustment="split")`
     IMPACT: bars pages backwards itself, keeping whole rows; `history.kis_history` keeps closes only. It drops rows
     with open or close None or <= 0, labels adjustment "split", and drops the running last bar. SPECIAL_REGIME from
     flng_cls_code would need a data/ edit.
* [token and import side effects] `_TOKEN_PATH` is bound at import to `config.state_root()/"kis_token.json"`. The
  token is POSTed before checked_target (ledger minor, carried to execution). Constructing a KISClient sends nothing.
  hermetic patches `KISClient._get`, `requests` and `_once`. Tests swap the whole class. (C)
     EVIDENCE: data/krx/kis_client.py:53 `_TOKEN_PATH = config.state_root() / "kis_token.json"`; :181-195 (POST then `_store_token`); tests/macro_acceptance.py:66
     IMPACT: Bars tests never reach `token()`. Look up `kis_client.KISClient` at call time.

### 5.2 Crypto (Upbit, Binance)

* [Candles and the two dailies] `Candles(symbol, dates, close, open=(), ..., source, note)` is frozen; `to_history()`
  keeps closes only.
  - `UpbitPublic().daily(market="KRW-BTC", *, days=504)`: 200 rows per page, paged backwards for at most
    days//200+2 pages; date = candle_date_time_utc[:10].
  - `BinancePublic().daily(symbol="BTCUSDT", *, days=504, interval="1d", market="spot")`: 1,000 per call, the
    data-api host first; date = UTC date of the open time.
  - Missing Upbit fields become 0.0.
  - Every HTTP call goes through module-level `_get` (0.12 s gap), which hermetic patches. (C)
     EVIDENCE: data/crypto/crypto_client.py:65-84 `class Candles:`; :137 `def daily(self, market: str = "KRW-BTC", *, days: int = 504) -> Candles:`; :192-193 `def daily(self, symbol: str = "BTCUSDT", *, days: int = 504, interval: str = "1d",`; :161 `g = lambda k: tuple(float(rows[d].get(k) or 0.0) for d in ds)`; :112 `def _get(url: str, ...`
     IMPACT: bars reads c.dates, c.open and c.close directly and refuses open or close <= 0. Tests fake
     `crypto_client._get` (existing pattern) or a bars seam.
* [day boundary and running bar] An Upbit or Binance daily bar dated d spans 00:00Z d to 00:00Z d+1, which is 09:00
  KST. `clocks.decision_time_utc("CRYPTO", d)` = 00:00Z of d+1 and needs no calendar. The first page includes the
  still-forming candle, unmarked. grokteam drops a bar unless open + period <= now. (C)
     EVIDENCE: core/calendars/clocks.py:236-240 `CRYPTO: 00:00:00Z of d+1, the close of the venue's daily bar dated d` / `return datetime(d.year, d.month, d.day, tzinfo=UTC) + timedelta(days=1)`; grokteam/book.py:237 `keep = [i for i, t in enumerate(o) if t + 3600 <= now]`
     IMPACT: Keep bar d only when 00:00Z(d+1) <= fetched_at. Join BTCUSDT × KRW-USDT on the date string.
* [spans] KRW-BTC starts 2017-09-25, and the study cache has 3,288 gapless rows (2017-09-25..2026-09-25). BTCUSDT
  starts 2017-08-17. KRW-USDT exists (live probe 1,365.00 on 2026-09-25), but the repo has no listing date, fixture or
  cache for it. history routes KRW-, BTC- and USDT- prefixes to Upbit and everything else to Binance.
     EVIDENCE: data/crypto/crypto_client.py:6 `(KRW-BTC from 2017-09-25), 200 rows per call, 10 requests/s per IP.`; research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md:32-33; core/quant/history.py:290-292
     IMPACT: The PROXY_DATA fallback date is computed at runtime. bars needs its own (venue, symbol, quote) ->
     feed map; neither yaml holds feed ids.

### 5.3 US and FX (yfinance)

* [ficc._yf_fetch keeps closes only] It calls `_yf.download(tickers, period=..., progress=False, auto_adjust=True,
  threads=False)` and keeps "Close". `_period_for` maps day counts to "5d" through "10y", with no start or end.
  core/ficc/data.py imports yfinance at module level. (C)
     EVIDENCE: core/ficc/data.py:196-211 `def _yf_fetch(tickers: list[str], period: str) -> dict[str, Rows]:` ... `auto_adjust=True, threads=False)`; :52-55 `try:` / `import yfinance as _yf`
     IMPACT: bars has its own `_yf_download(tickers, start, end)` seam with explicit dates (yfinance `end` is
     exclusive) and a lazy yfinance import. It parses the (Price, Ticker) MultiIndex.
* [yfinance 1.4.1 facts] Signature: `download(tickers, start=None, end=None, ..., auto_adjust=True, ..., progress=True,
  ..., multi_level_index=True)`. Daily bars are tz-stripped (exchange-local date). curl_cffi `Session(impersonate=
  "chrome")` bypasses the socket patch. The only top-level cache setter is `set_tz_cache_location`;
  `yf.set_cache_location` does not exist. `yfinance.cache.set_cache_location(dir)` exists, moves the tz, cookie and
  ISIN DBs, writes them straight into dir (WAL), and closes an open DB. The default cache is %LOCALAPPDATA%\py-yfinance.
  (C)
     EVIDENCE: .venv/Lib/site-packages/yfinance/__init__.py:31 `from .cache import set_tz_cache_location`; cache.py:625-635 `def set_cache_location(cache_dir: str):`; multi.py:55-59, :138-139, :204-207; _http.py:21-25, :58-61; constraints.txt:21 `curl_cffi==0.15.0`
     IMPACT: Call `yfinance.set_tz_cache_location(str(<state_root>/"odds"/"yfinance"))` inside the seam, before
     the download. The redirect is process-wide. CORRECTED (data.md cited plan:16743-16744): the plan's hand-off
     text "call `yf.set_cache_location`" is at plan:16742, and names a function that does not exist.
* [adjustment labels and FX ticker] yf_history labels "" for ^, =F, =X, -USD and -KRW, and "total" otherwise. The spec
  writes KRW=X; FICC builds USDKRW=X.
     EVIDENCE: core/quant/history.py:280-282 `pays_no_dividend = s.startswith("^") or s.endswith(("=F", "=X", "-USD", "-KRW"))` ... `adjustment="" if pays_no_dividend else "total")`; spec:715 `- US legs: price × KRW=X;`; core/ficc/data.py:609 `ticker = f"{p}=X"`
     IMPACT: Pin `KRW=X`. The symbol is part of the series hash.
* [a US close always lands on the next Seoul date] 16:00 ET (13:00 on early-close days) is 05:00, 06:00, 02:00 or 03:00
  KST on D+1, in both EST and EDT (offline zoneinfo, tzdata 2026.2).
     EVIDENCE: data.md offline run `2026-01-02 16:00:00 -> 2026-01-03T06:00:00+09:00 1`, `2026-07-02 16:00:00 -> 2026-07-03T05:00:00+09:00 1`
     IMPACT: seoul_date = ny_date + 1. Test both EST and EDT.
* [Seoul zone constants already exist] `core.compliance.model.KST = zoneinfo.ZoneInfo("Asia/Seoul")`, built at import.
  calendars.events also names "Asia/Seoul". tzdata 2026.2 is pinned. (C)
     EVIDENCE: core/compliance/model.py:21 `KST = zoneinfo.ZoneInfo("Asia/Seoul")            # built at import; decide() never builds a zone`; core/calendars/events.py:120 `ET, KST = "America/New_York", "Asia/Seoul"`; constraints.txt:99 `tzdata==2026.2`
     IMPACT: Reuse model.KST (closure +0) and build any other zone once at module level.
* [paper_live is off-limits] paper_live silences all warnings at import, and grokteam rules out importing it.
     EVIDENCE: paper_live/engine.py:30 `warnings.filterwarnings("ignore")`; grokteam/book.py:20
     IMPACT: Copy the `df[t]["Open"]` idea only.

### 5.4 History, markers, PIT

* [History holds closes only; its status marks a whole series] `History(symbol, source, dates, closes, note,
  adjustment, status)`. `_cached` sets status "provisional_intraday" on the whole series whenever the market may be
  trading, which is always true for crypto. `_cached` keeps no opens or manifest and is off under hermetic (TTL 0).
     EVIDENCE: core/quant/history.py:55-69 `class History:`; :446-449; :425-429 `if ttl <= 0 or ...: return fetch(symbol, days=days)`
     IMPACT: bars defines its own bar type {symbol, source, dates, open, close, adjustment, status} and judges
     finality per bar.
* [auto routes fall back to SYNTHETIC] `load_history(source="auto")` and ficc `load_many` degrade to SYNTHETIC when
  keys are missing. The data clients carry no provisional, final or synthetic markers.
     EVIDENCE: core/quant/history.py:493-498, :509-513; core/ficc/data.py:541-543; `grep -rn "provisional\|is_final\|SYNTHETIC" data/` -> nothing
     IMPACT: bars calls providers explicitly and refuses SYNTHETIC.
* [PIT finality rule] `pit.stamp_close` treats a row as final only when retrieved at or after close + 10 min
  (QUARANTINE_MINUTES).
     EVIDENCE: core/ficc/pit.py:35 `QUARANTINE_MINUTES = 10`; :494-501
     IMPACT: Adopt the same 10-minute margin. pit is too heavy to import.
* [the FICC cache memo-before-check minor] `_cache_put` sets `_MEM` before checked_target (ledger minor).
     EVIDENCE: core/ficc/data.py:272-274 `now = time.time()` / `_MEM[key] = (now, rows)` / `target = checked_target(...)`
     IMPACT: In bars, update any memo only after the disk write passes its checks. The fix itself is a follow-up item.

### 5.5 The bars cache, final-target checks and paths

* [checked_target] `checked_target(path, what="path", *, within=None) -> Path` refuses QUANTGEN paths, symlinks and
  junctions, files with st_nlink > 1, and paths outside `within`. It creates nothing. (C)
     EVIDENCE: core/isolation.py:40-58 `def checked_target(path, what: str = "path", *, within=None) -> Path:` ... `Creates nothing.`
     IMPACT: Check the data file, the .tmp and the manifest, each `within=` the bars dir, before opening; then mkdir.
* [template: grokteam write_cached] It checks the file, the `.tmp` and MANIFEST.jsonl `within=DATA`, then mkdir, writes
  the tmp, `os.replace`s it and appends a `{file, sha256}` line. read_cached treats a missing manifest line as missing
  and raises on a sha mismatch. owner._write_new adds fsync and an `xb` write-once variant. (C)
     EVIDENCE: grokteam/book.py:134-149 `tmp = checked_target(path.with_name(path.name + ".tmp"), "grokteam cache tmp", within=DATA)` / `manifest = checked_target(path.parent / "MANIFEST.jsonl", "grokteam MANIFEST", within=DATA)`; core/compliance/owner.py:606-631 `_write_new`
     IMPACT: bars.py copies the pattern (it may not import grokteam). Refusals propagate (A0; plan:1212 `the odds plan must call `checked_target` on its file, its `.tmp` and its manifest.`).
* [state root without config: zero closure cost] `core.isolation.state_root()` reads TRADEGEN_HOME from os.environ
  (else ~/.tradegen), refuses QUANTGEN and runs the link scan. `config.state_root()` only delegates to it.
  `config.state_path(env, default)` adds env overrides but brings config.py (+20 files). .env sets no TRADEGEN_HOME.
  (C; new, critic)
     EVIDENCE: core/isolation.py:105-110 `def state_root() -> Path:` ... `root = refuse_quantgen(_env("TRADEGEN_HOME") or Path.home() / ".tradegen", "TRADEGEN_HOME")`; config.py:57-65 `def state_path(env: str, default: Path) -> Path:` ... `return _isolation.state_root()`; .env names-only scan (no TRADEGEN_HOME)
     IMPACT: Put the bars cache at `core.isolation.state_root() / "odds" / "bars"` and the yfinance DBs at `.../odds/yfinance`,
     resolved on every call. temp_home() then moves both. Add both to the state-path isolation test, which lists
     every state path and asserts it lies under ~/.tradegen (tests/macro_m0_rules.py:442-445 `"grokteam": book.DATA}`).
* [series hash helper: zero closure cost] `core.compliance.model.canonical_json` gives the same text as
  macro_schema's. It accepts np.float64 and refuses np.int64, np.float32 and ndarrays (TypeError). There is no md5
  helper in model. (C; new, critic)
     EVIDENCE: core/compliance/model.py:57-59 `def canonical_json(obj) -> str:` / `"""The same text as core.ficc.macro_schema.canonical_json, after jsonable(); NaN and inf refused."""`; :52 `raise TypeError(f"not JSON data: {type(obj).__name__}")`; critic probe (`int64 TypeError`, `ndarray TypeError`, texts equal)
     IMPACT: hash = `hashlib.md5(model.canonical_json({symbol, source, dates, open, close, adjustment, status}).encode()).hexdigest()`
     over `.tolist()` values. macro_schema.md5_hex would cost +2 files.

### 5.6 Fixtures and the study cache

* [no bar fixtures] Tests build bars inline through fakes: Upbit candles and Binance klines via `crypto_client._get`, a
  fake KISClient, a `_yf_fetch` lambda. The study cache CSVs are close-only.
     EVIDENCE: tests/expansion_acceptance.py:157-171; tests/quant_acceptance.py:282-288; docs/asset_expansion/cache/upbit_KRW-BTC.csv:1 `,upbit_KRW-BTC`
     IMPACT: Bars and TwoPointBootstrap fixtures are synthetic (open, close) rows with a non-SYNTHETIC source label,
     or the tests construct the bars object directly.
* [the study cache's last rows were running prices] upbit_KRW-BTC.csv was written at 2026-09-25 16:29:48Z (its mtime,
  preserved in the 10fcc69 root commit), and its last row is 2026-09-25. That candle closed 2026-09-26 00:00Z. yf_SPY.csv
  was written mid-session. The card (2026-09-26 18:34Z) and the manifest run date (2026-09-27) used these cached
  rows. (C)
     EVIDENCE: `TZ=UTC stat` -> `2026-09-25 16:29:48.102911500 +0000 docs/asset_expansion/cache/upbit_KRW-BTC.csv`, `2026-09-26 18:34:42 ... S_C3_crypto_trend_krwbtc.json`; tail `2026-09-25,113632000.0`; docs/asset_expansion/manifest.json `"run": "2026-09-27"`
     IMPACT: A fresh Upbit pull will very likely give a different 2026-09-25 close. That moves the input digest, and
     possibly the stats, so the replay's live-input rule needs a ruling (DQ13).
* [the card's data.source is boilerplate] It says "Yahoo adjusted close unless stated", but the runner loaded Upbit.
     EVIDENCE: docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json:37 `"source": "Yahoo adjusted close unless stated"`; docs/asset_expansion_study.py:732 `"S_C3_crypto_trend_krwbtc": lambda: run_crypto_trend("KRW-BTC", lambda: upbit("KRW-BTC"), "S_C3_crypto_trend_krwbtc"),`
     IMPACT: Provenance names Upbit KRW-BTC from the runner code.
* [KIS overseas alternatives exist but are out of spec] `KISMarkets.overseas_daily` and `usdkrw_daily` give open and
  close with KIS keys. A KIS series uses a split adjustment, while Yahoo's is total.
     EVIDENCE: data/kis_markets.py:459-475, :496-497
     IMPACT: Not used (the spec names yfinance). Mixing the two would trip history.convention_warning.

## 6. Models and statistics building blocks

### 6.1 Environment and seeds

* [no repo helper for Clopper-Pearson, empirical Bernstein, Kelly, bold play or Dubins-Savage] SciPy reproduces the
  spec's figures: at k = 0, n = 1e6 the one-sided 95% upper bound is 2.9957e-06; the two-sided exact interval from
  `binomtest` equals the one from `beta.ppf`.
     EVIDENCE: grep `clopper|betaincinv|beta\.ppf|binomtest|proportion_confint` -> only core/ficc/vol_products.py:44 `def rolling_beta(`; grep `(?i)kelly|bold play|dubins|empirical.bernstein|hoeffding` over core/tests/ui -> no matches; models probe `CP k=0 one-sided 95% upper 2.9957277863525433e-06`
     IMPACT: All of these are new code. Use `scipy.stats.beta.ppf` (0 closure files), and test it against
     `binomtest` for parity. Pin V's ddof in the plan.
* [seeds: SeedSequence passes through default_rng] garch.simulate_returns, simulate_garch_series and
  gate_stats.block_indices call `np.random.default_rng(seed)`. That accepts a SeedSequence (256-bit entropy plus
  spawn_key) and returns a Generator unchanged. The bit generator is PCG64. (C)
     EVIDENCE: core/quant/garch.py:686 `rng = np.random.default_rng(seed)`; :708; core/quant/gate_stats.py:94; models probe `SeedSequence ok True Generator passthrough True`
     IMPACT: Pass `SeedSequence(int.from_bytes(seed, "big"), spawn_key=(chunk, stream_id))` straight in. Say in the
     plan that this relies on default_rng's passthrough, not on the `int` annotation.

### 6.2 core/quant/garch.py (closure +2)

* [fit_garch] `fit_garch(returns, *, dist="t", profile=True) -> GarchFit` raises ValueError under 100 observations.
  mu is fixed at the sample mean. On 3,287 KRW-BTC returns: 0.32 s with profile=False, 1.35 s with profile=True,
  nu = 2.76 (eta bound nu = 2.5), persistence 0.9975. (C)
     EVIDENCE: core/quant/garch.py:446 `def fit_garch(returns: np.ndarray, *, dist: str = "t", profile: bool = True) -> GarchFit:`; :93 `_MIN_OBS = 100`; :78 `"nu": (2.5, math.inf)`
     IMPACT: GarchT catches the ValueError and drops the model with a named note. Use profile=False in the B = 20
     refit loop (about 6 s per crypto leg). Surface `fit.note` and the at_bound flags.
* [simulate_returns] `simulate_returns(fit, *, n_paths, horizon, seed=7, drift_daily=None, rate_daily=None,
  bound=Z_BOUND) -> (ret, avg_correction)`. With rate_daily, each step is `rate_daily - c(sigma_t) + eps`, using the
  path's own sigma. All z are drawn up front as an (n_paths, horizon) array. It returns log returns only, NOT the
  sigma paths. 200,000 x 30 takes 0.93 s at 48 MB per array (200k x 365 would be about 584 MB). The keyword is
  `bound`, and `Z_BOUND = 22` is an int. (C)
     EVIDENCE: core/quant/garch.py:674-676 `def simulate_returns(fit: GarchFit, *, n_paths: int, horizon: int, seed: int = 7,` / `drift_daily: float | None = None, rate_daily: float | None = None,` / `bound: float | None = Z_BOUND) -> tuple[np.ndarray, float]:`; :687-701 (z drawn up front; `c = martingale_correction(sig, fit.nu, fit.dist, bound)` / `ret[:, h] = float(rate_daily) - c + eps`); :71 `Z_BOUND = 22`
     IMPACT: Call `simulate_returns(fit, n_paths=..., horizon=..., seed=stream, rate_daily=0.0, bound=Z_BOUND)`.
     Pilot check 1 needs sigma, so models.py rebuilds it, by inverting eps or with its own loop (DQ12). For long
     horizons, sub-chunk or document the memory ceiling.
* [bounded innovations] A t draw beyond the bound is redrawn from the truncated t by inverse CDF. A fit with nu > 100
  or normal dist draws an unbounded normal. The number of RNG draws is data-dependent.
     EVIDENCE: core/quant/garch.py:600-611 `if dist != "t" or nu > NU_NORMAL: return rng.standard_normal(size=size)` ... `z[out] = s * d.ppf(lo + rng.random(n_out) * (hi - lo))`
     IMPACT: Never share one Generator between the GARCH innovations and any other consumer.
* [correction table and the independent quadrature] `_correction_table(nu, bound)` is lru_cached. It uses 3 panels x
  600 Gauss-Legendre nodes on a 4,000-point geometric sigma grid [1e-6, 0.25], and sums directly above 0.25.
  `martingale_correction` looks up `_correction_table` through module globals at call time. garch's `__main__`
  already checks the table against scipy `quad` to < 1e-7. Measured worst-case error: 3.74e-08 at nu 2.51, near 1e-16
  above sigma 0.25. One quad call takes about 3 ms. (C for the code)
     EVIDENCE: core/quant/garch.py:622-623 `@lru_cache(maxsize=32)` / `def _correction_table(nu: float, bound: float):`; :632 `x, w = np.polynomial.legendre.leggauss(600)`; :666 `z, wt, grid, ratio = _correction_table(float(nu), float(bound))`; :730-736 (quad self-check)
     IMPACT: c_table(sigma) := `garch.martingale_correction(sigma, fit.nu, fit.dist, Z_BOUND)`. c_quad uses
     scipy.integrate.quad on the same three panels. The corruption test patches `garch._correction_table`
     (restoring it in finally), with a gross corruption for the 4-SE check. Quad a binned or deduplicated set of
     pilot sigmas, not every draw.
* [normal branch; unbounded refusal] For normal or nu > 100 the correction is exactly sigma²/2. bound=None with t
  raises ValueError.
     EVIDENCE: core/quant/garch.py:662-665 `if dist != "t" or nu > NU_NORMAL: return 0.5 * sig ** 2` / `if bound is None: raise ValueError(...)`
     IMPACT: c_quad for effectively-normal fits is analytic. GarchT always passes bound=Z_BOUND.
* [statistical pilot margin] Fixture GARCH-t (nu 4.6), 200k x 30, rate 0: max |mean e^{cum r} - 1|/SE = 1.40, and
  2.32 per step. Zero LOG drift (`drift_daily=0.0`) gives a terminal mean of 1.0295 (z 49.6) and fails.
     EVIDENCE: models probes `rate0: max |mean-1|/SE 1.3975944400620446`, `zero log drift: terminal mean 1.0295164517176008 z-score 49.60209626637433`; core/quant/garch.py:695-696 `if rate_daily is None: ret[:, h] = drift + eps`
     IMPACT: Fix the pilot size and seed deterministically. The "drift zero fails" test can use
     `simulate_returns(fit, drift_daily=0.0)`.
* [parametric refit source] `simulate_garch_series(omega, alpha, beta, nu, *, n, seed, dist="t")` returns zero-mean
  returns with full tails and a 500-session burn-in.
     EVIDENCE: core/quant/garch.py:705-710
     IMPACT: B = 20 refit: series_b, then `fit_garch(series_b, profile=False)`, then simulate. A failed refit is left
     out with a note.
* [bounded_t_stats] `bounded_t_stats(nu, bound) -> (mass inside, variance)`. At nu 2.76 the variance is 0.896, so the
  cap removes about 10% of the innovation variance on BTC fits.
     EVIDENCE: core/quant/garch.py:642 `def bounded_t_stats(nu: float, bound: float) -> tuple[float, float]:`; models probe `(0.9999407621482272, 0.8958380575410665)`
     IMPACT: Optional card note. Reuse the wording idea, not montecarlo.
* [annualisation] GarchFit.cond_vol_last is annualised with 252. The sim divides by 252, so crypto's 365 does not
  distort the daily recursion.
     EVIDENCE: core/quant/garch.py:109 `cond_vol_last: float              # annualised sqrt(sigma^2_{T+1} * 252): next-session forecast`; :689 `s2 = np.full(n_paths, fit.cond_vol_last ** 2 / TRADING_DAYS)`
     IMPACT: Do not re-annualise.

### 6.3 Zero drift, demeaning and block bootstraps

* [montecarlo's drift="zero" is zero LOG drift] DRIFTS = ("premium", "zero", "rf", "sample"); zero -> ("log", 0.0).
  `run_monte_carlo(history, *, model="garch_t", n_paths=5000, horizon_days=126, ..., n_sample_paths=40, drift=...)`
  clamps paths to [200, 100000]; `n_sample_paths=n_paths` returns every path. Measured: bootstrap zero gives 1.00357
  and garch zero 1.00410. Bootstrap with rf=0 gives 0.99964, which passes at the terminal. (C for DRIFTS)
     EVIDENCE: core/quant/montecarlo.py:67 `DRIFTS = ("premium", "zero", "rf", "sample")`; :201-202 `if mode == "zero": return "log", 0.0`; :229-238, :308
     IMPACT: Tests may import montecarlo only to show failure. The odds engine never uses its drift modes. The
     "demeaning fails" test needs a path-dependent rule (stop or bracket) on serially dependent data.
* ["per-row demeaning" has no repo implementation] montecarlo demeans ADDITIVELY and uses circular blocks of 5. The
  multiplicative rev-1 form (rows × 1/mean(1+R_close)) exists only in the review text.
     EVIDENCE: core/quant/montecarlo.py:288-290 `r_dm = r - float(np.mean(r))`; :166 `def _simulate_bootstrap(rng, r, n_paths, horizon, block: int = 5)`; docs/superpowers/specs/2026-10-23-review-gate-odds/round1_claude_workflow.md:54
     IMPACT: Write a test-only rev-1 reference, with an AR(1) or trending fixture, a fixed seed and a stated z
     threshold.
* [pw_block] `gate_stats.pw_block(x, kind="circular")` defaults to CIRCULAR. It needs >= 20 finite observations and
  returns 1.0 when the long-run autocovariance is <= 0. It is capped at ceil(min(3√n, n/3)) and can return < 1 (white
  noise 0.62). On KRW-BTC, stationary gives r 2.03 and r² 88.57, with a cap of 172. Closure +23. (C)
     EVIDENCE: core/quant/gate_stats.py:72-77 `def pw_block(x, kind: str = "circular") -> float:`; :40-41; :44 `b_max = math.ceil(min(3 * math.sqrt(nobs), nobs / 3))`; :65-66
     IMPACT: Always pass kind="stationary". Floor b at 1. Decide whether the 2x variant is capped (177 > 172).
     Catch ValueError as a refusal (DQ11).
* [no reusable path-index generator] `gate_stats.block_indices(n, block, B, seed, kind)` returns B x n with an int
  block and a Python loop (2000 x 2530 takes 3.47 s). `forecast_eval.stationary_bootstrap_indices` gives one
  resample and drags in pit and macro_rules. The gate's own bootstraps are circular blocks of 10. (C)
     EVIDENCE: core/quant/gate_stats.py:86 `def block_indices(n: int, block: int, B: int, seed: int, kind: str = "circular") -> np.ndarray:`; :102 `# ponytail: per-row loop`; core/quant/validate.py:163-175
     IMPACT: TwoPointBootstrap needs its own vectorised Politis-Romano generator: restart with probability 1/b,
     else advance mod N. Kelly's μ_lb (B 2000 over 2,530 days, block 10) fits block_indices exactly.

### 6.4 The S_C3 replay (D13)

* [card] docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json:
  - rules: family crypto_trend, grid hysteresis [0, 0.222, 0.444, 0.667, 0.889], cost_bps_per_side 10.0, embargo 1;
  - data: sessions 3288, 2017-09-25..2026-09-25;
  - protocol: w_is 756, w_oos 126, min_is 504, ci_level 0.9, bootstrap_B 2000, block 10;
  - N_total 11, seed 11;
  - stats: sr_oos 1.2160250195674127, bench_sr 0.788830441182887, haircut_sr 0.7296150117404476, bench_diff
    0.4271945783845257, bench_ci [0.0334, 0.8346], decision PASS, chosen_last {hysteresis 0.667}, n_sessions 2530,
    n_trades 138, results_md5 ca757e25f508b588cb2f361719ec83cd.

  The card stores no lookbacks, mas or domain. (C)
     EVIDENCE: S_C3_crypto_trend_krwbtc.json:34-36 `"sessions": 3288,` / `"start": "2017-09-25",` / `"end": "2026-09-25",`; :43-50 protocol; :53 `"N_total": 11,`; :59 `"seed": 11,`; :61 `"sr_oos": 1.2160250195674127,`; :143 `"results_md5": "ca757e25f508b588cb2f361719ec83cd",`
     IMPACT: models.py pins lookbacks (7, 14, 21, 28), mas (10, 20, 50, 100, 200) and domain {"hysteresis": (0.0,
     0.889)}. Render the card text from the replayed StrategyScore.
* [APIs] Replay signatures (C):
  - `pnl_matrix(prices, fn, grid, *, cost_bps, cash_daily=0.0, stress=2.0)` returns a TUPLE (pnl T-1 x G, stress
    pnl, turnover) of SIMPLE returns, with cost per side × |Δw|.
  - `crypto_trend(prices, *, lookbacks=(7,14,21,28), mas=(10,20,50,100,200), hysteresis=0.2)`: long/flat, warm-up
    200.
  - `walk_forward(pnl, dates, *, turnover, pnl_stress, w_is, w_oos, embargo=0, min_is)`: the defaults are bound at
    import.
  - `score_strategy(wf, *, grid, full_pnl, n_trials, bench_daily=None, seed=11, domain=None)`: a bench whose length
    is wrong is silently dropped.
  - `GATE` is a mutable dict read at call time (the study's --quick mode mutates it).
     EVIDENCE: core/quant/strategies.py:379-381 `def pnl_matrix(...) -> tuple[np.ndarray, np.ndarray, np.ndarray]:`; :82 `ret = P[1:] / P[:-1] - 1.0`; :330-331; core/quant/validate.py:345-347; :492-494; :516 `has_b = bench_daily is not None and len(bench_daily) == len(p)`; :501 `ci = block_bootstrap_ci(p, block=GATE["block"], B=GATE["bootstrap_B"], ...)`; docs/asset_expansion_study.py:191-192 `V.GATE["bootstrap_B"] = 300`
     IMPACT: Unpack three arrays and pass dates[1:]. Wrap crypto_trend with the pinned lookbacks and mas. Pass w_is,
     w_oos, min_is and embargo from the card. Assert `{k: V.GATE[k] for k in card["protocol"]} == card["protocol"]`
     and len(bench) == len(wf.pnl). Bench = simple buy-and-hold mapped onto wf.dates. "Chosen 0.667" is the LAST
     origin's choice: the OOS stream mixes all five configs (chosen = (0,0,1,2,2,0,0,2,0,1,1,2,4,4,1,1,1,1,1,1,3)).
* [replay reproduces the card bit-exactly from the cache] Reading the cache with csv, then pnl_matrix -> walk_forward
  -> score_strategy, reproduces every card statistic to the last digit in about 5 s. OOS is 2019-10-23..2026-09-25
  (2,530 days). md5(wf.pnl bytes) = bbdcf17ca9462567fe351c54644bef0c. Mean 0.0014832/day, sd 0.019362; 40.3% of days
  are flat. (C: re-run by the critic, 4.99 s)
     EVIDENCE: replay probe output `sr_oos 1.2160250195674127 1.2160250195674127` ... `decision PASS chosen_last {'hysteresis': 0.667}` ... `pnl md5 bbdcf17ca9462567fe351c54644bef0c`
     IMPACT: Pin a strict golden (equality) on the cache fixture, alongside the spec's ±0.02 rule for live data.
     Define the digest on a canonical form if it must survive platforms.
* [result types and readers] WalkForward has dates (OOS), pnl, pnl_stress, turnover, origins, chosen, is_sharpes,
  n_configs and note. StrategyScore has sr_oos, ci90, dsr, pbo, bench_sr, bench_diff, bench_p, bench_ci, haircut_sr,
  n_trades, n_sessions, decision, ... and no chosen-params field. `validate.md5_of(path)` returns "" when the file is
  missing. `load_cards` swallows unreadable JSON.
     EVIDENCE: core/quant/validate.py:333-342 `class WalkForward:`; :455-489 `class StrategyScore:`; :859-860 `def md5_of(path: Path) -> str:`; :851-855 `except Exception: continue`
     IMPACT: Read the single card with json.loads and let errors raise. The card wording (0.79, 0.73, +0.43,
     +0.03..+0.83) comes from bench_sr, haircut_sr, bench_diff and bench_ci.
* [what ±0.02 misses] lookbacks 28->30 gives 1.3675 REVISE; mas 200->150 gives 1.3471; cost 10->9 gives 1.1959 (just
  outside); embargo 1->0 gives 1.2172 (INSIDE).
     EVIDENCE: models probe `embargo 1->0 (1.2172, 'PASS', {'hysteresis': 0.667})`, `cost 10->9 (1.1959, ...)`
     IMPACT: "A changed constant is refused" changes lookbacks or mas. Also compare the exact card inputs and, on
     the cache fixture, the digest.
* [cache file and results.csv] The cache file: header `,upbit_KRW-BTC`, 3,288 rows, CRLF, 75,588 bytes, md5
  de7eaec6f45d0dc12b2950f50433b89d. md5(results.csv bytes) = card results_md5 = manifest results_md5. results.csv
  aggregates 34 cards and cannot be regenerated. (C)
     EVIDENCE: md5sum `de7eaec6f45d0dc12b2950f50433b89d *docs/asset_expansion/cache/upbit_KRW-BTC.csv`, `ca757e25f508b588cb2f361719ec83cd *docs/asset_expansion/results.csv`; docs/asset_expansion/manifest.json:4 `"results_md5": "ca757e25f508b588cb2f361719ec83cd",`
     IMPACT: Compare a canonical digest of (dates, closes), not file bytes. Verify md5(results.csv) == card
     results_md5.
* [never import the study runner] At import it inserts the repo root into sys.path, reconfigures stdio, imports
  config, pandas, strategies and validate, and mkdirs docs/asset_expansion/{,cache,cards}. docs/ has no `__init__.py`.
     EVIDENCE: docs/asset_expansion_study.py:41-42 `sys.path.insert(0, str(ROOT))`; :57-58 `for d in (OUT, CACHE, CARDS): d.mkdir(parents=True, exist_ok=True)`; `ls docs/__init__.py` -> absent
     IMPACT: Test with an AST scan of core/odds plus a sys.modules check for both `docs.asset_expansion_study` and
     `asset_expansion_study`.
* [replay import cost] strategies imports history at module level, so config (load_dotenv) and data.net load. Closure
  +46, with core/engine/orders.py via risk -> risk_layer -> engine. (C)
     EVIDENCE: core/quant/strategies.py:32 `from core.quant.history import History, TRADING_DAYS`; critic probe `core.quant.strategies: +46 ... 'core/engine/orders.py'`
     IMPACT: Doing the replay inside core/odds/models.py signs the engine and the data layer (DQ1).

### 6.5 Constants, Kelly and closed forms

* [LIVE_SHARPE_MULTIPLIER] 0.60, which equals STATS, GATE["haircut"] and tf_gov.LIVE_MULTIPLIER (pinned by a test).
  The 0.4 live-word scan covers core/docs/ui. (C)
     EVIDENCE: core/quant/gate_stats.py:149 `LIVE_SHARPE_MULTIPLIER = 0.60`; tests/macro_tf_gov.py:283 `assert TG.LIVE_MULTIPLIER == 0.6 == GS.LIVE_SHARPE_MULTIPLIER == V.GATE["haircut"]`
     IMPACT: Import it (closure +23) or declare it locally with an equality test. Never write a literal 0.4.
* [DELIST_STRESS] `tf_books.DELIST_STRESS = (0.30, 1.00)`. tf_books.COST_PER_SIDE is an unrelated dict. Importing
  tf_books costs +53, orders.py included. (C)
     EVIDENCE: core/quant/tf_books.py:36 `DELIST_STRESS = (0.30, 1.00)`; :35 `COST_PER_SIDE = {"gross": 0.0, "net35": 0.0035, "net70": 0.0070}`
     IMPACT: Declare it locally and test equality. Book the haircut in the odds ledger.
* [Kelly on the real card is a boundary solution] μ_lb (stationary, b = 10, B = 2000, seed 11) = 0.000728/day, 0.49 x
  the mean. Rc = R - mean + 0.6 μ_lb has mean 0.000437. argmax mean ln(1 + f Rc) on [0, 1] is f = 1. The card column's
  Sharpe after the cut is 0.72961..., which equals haircut_sr. min R = -0.12 > -1.
     EVIDENCE: models probes `mu_lb ... 0.0007275941962222723`, `f* bounded 0.9999940391390134`, `card column Sharpe 0.7296150117404473 0.6*sr_oos 0.7296150117404476`
     IMPACT: Decide f* by the sign of the derivative at both ends, then bisect, so "f* within [0, 1]" holds
     exactly. The stake is c·W before affordability.
* [bold_even and the closed forms confirmed] An exact Fraction recursion at x = 1/1000 gives 0.1000%, 0.0816%, 0.0346%
  and 0.0106%, and 0.0400% at p = 0.49 with L at half the stake. The bracket counts are ceil 617 and 153. The 52.5%
  Kelly bets figure is 5,524.
     EVIDENCE: models probes `0.5 0.1000%`, `0.49 0.0816%`, `0.45 0.0346%`, `0.4 0.0106%`, `floor half, p=0.49 0.0400%`; spec:757-759, :97-98
     IMPACT: Implement with `fractions` (stdlib). NOTE (critic): spec 7.1 names a plan type `Fraction`, so use
     `fractions.Fraction` qualified, or rename (DQ23).

## 7. Costs and calendars

### 7.1 cost_per_side

* [signature and return] `cost_per_side(instrument_book, price=None, nav_fx=None, *, on=None, side="buy") ->
  CostQuote(bp, floor_bp, source "table"|"tick_floor", table_bp, stress_bp = 2·bp)`. nav_fx is the third POSITIONAL
  parameter. The rule is bp = max(table, floor) with floor = 1.4 + ½·tick/price·1e4 + sell tax (stock sells only).
  Only side == "sell" triggers the tax. price <= 0 raises ValueError. (C)
     EVIDENCE: core/quant/instruments.py:168-169 `def cost_per_side(instrument_book: Any, price: Optional[float] = None, nav_fx: Any = None, *,` / `on: Optional[date] = None, side: str = "buy") -> CostQuote:`; :179-182; :118-122 `def tick_floor_bp(...)` / `return commission_bp + 0.5 * tick / price * 1e4 + tax_bp`; :19 `COMMISSION_BP = 1.4`
     IMPACT: Pass nav_fx by keyword. κ = quote.bp × 1e-4. Validate fill prices before quoting, and do not label a
     ValueError NOT_TRADABLE.
* [table rates] krx_etf 3, krx_stock 35 (sell tax included), us 50, crypto 10, futures 5, fx 10 bp. `cost_stress` is
  2.0. A test pins the table: CORRECTED from costs_cal's :78, it is tests/macro_m0_instruments.py:80. (C)
     EVIDENCE: core/quant/validate.py:78 `COST_BP_PER_SIDE = {"krx_etf": 3.0, "krx_stock": 35.0, "us": 50.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}`; tests/macro_m0_instruments.py:80 `assert V.COST_BP_PER_SIDE == TABLE`; docs/asset_expansion_study.py:19 `KRX stock 35 bp incl. tax`
     IMPACT: Read the rates through cost_per_side or validate (closure +22), or copy them with an equality test.
     Charge the rate on both sides and add no tax.
* [books] KRX_ETF_line (tick table KRX_ETF); KRX_stock_book (tick OWNER_INPUT, tax_side sell); US_shares_KIS (USD,
  tick OWNER_INPUT); crypto_venue (venue and currency OWNER_INPUT). Every lot_size is OWNER_INPUT. A test pins the book
  set and requires KRX_stock_book(70000) to raise NotTradable.
     EVIDENCE: core/quant/instruments.py:67-74 (`_B("KRX_stock_book", ..., OWNER_INPUT, "sell", OWNER_INPUT, ...)`); tests/macro_m0_instruments.py:92 `(("KRX_stock_book", 70000.0), {}),`; :103 `assert set(INSTRUMENT_BOOKS) == {...`
     IMPACT: Do NOT add a KRX stock tick table to instruments.py, or T-COST-02 fails. Keep the stock ladder in
     venues.yaml.
* [what raises] Probed at 2,005 KRW on 2026-11-02:
  - KRX_stock_book: NotTradable (tick table None). A 2027 sell fails on the TAX first.
  - KRX_ETF_line: OK, 13.8688 bp (tick_floor).
  - US_shares_KIS and crypto_venue without nav_fx: NotTradable (non-KRW); with nav_fx: NotTradable (tick).
  - price=None: OK at the table rate.
  - An ETF on 2023-01-02: NotTradable (no tick row before 2023-12-11).

  nav_fx is only checked against None and never used in the arithmetic.
     EVIDENCE: costs_cal cps_probe output; core/quant/instruments.py:105-116 `def tick_size(table: Optional[str], price: float, on: Optional[date] = None) -> float:`; :177 `if book.currency != "KRW" and nav_fx is None:`; :150-151 `if year not in SELL_TAX_BP:`
     IMPACT: Only the ETF book takes the spec's literal per-fill call. For the others, κ = max(table rate,
     tick_floor_bp(price, venues_tick(price))) or the table rate alone. The plan's hand-off wording ("pass ... the
     tick ladder to cost_per_side") cannot be implemented: cost_per_side has no tick parameter.
* [resolve inputs and shipped books] `_resolve` accepts an InstrumentBook, an Instrument, a book-id string or a
  registry code. The instrument map's `cost_book` is a book-id string from COST_BOOKS. The shipped map uses
  KRX_stock_book x1 (005930), KRX_ETF_line x3 (069500, 252670, 114800), US_shares_KIS x10 and crypto_venue x3. The
  only whitelisted KRX ETF is 069500.
     EVIDENCE: core/quant/instruments.py:155-165 `def _resolve(x: Any) -> tuple[str, InstrumentBook, str]:`; core/compliance/rules.py:72 `COST_BOOKS = frozenset({"KRX_stock_book", "KRX_ETF_line", "US_shares_KIS", "crypto_venue"})`; core/compliance/instruments.yaml:15 `cost_book: KRX_stock_book`
     IMPACT: Pass `instrument.cost_book` as the first argument, never `validate.cost_class` inference (spec:182).
     Fixtures use 069500 and 005930.
* [2,005-KRW ETF claim holds] tick_size("KRX_ETF", 2005) = 5, so the floor is 13.8688 bp > 3 bp, on both sides. At
  1,999 it is 3.90. The ETF floor binds below 3,125 KRW (tick 1) or 15,625 (tick 5). The KRX stock floor binds only
  below 148.8 KRW (buy) or 367.6 KRW (sell, with tax). (C for the tick table)
     EVIDENCE: core/quant/instruments.py:27 `"KRX_ETF": ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),),`; costs_cal probe `floor 2005: 13.868827930174565`
     IMPACT: The ledger test asserts >= 13.8 bp for both sides with a 2026 date.
* [check_extras and φ do not exist] `check_extras` appears only in the spec and the review. There is no φ_b or φ_s
  data. `instruments.check_cost_policy` validates card headers, a different thing.
     EVIDENCE: grep `check_extras` -> spec:183 and round1_claude_workflow.md:155 only
     IMPACT: New code with a defined home. Decide what a missing φ means (DQ30).

### 7.2 Limit bands (orders.py constants to mirror)

* [LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0 and the band helpers] `_round_toward` floors above prev_close and ceils
  below, with one tick and eps 1e-9. `limit_prices` needs 0 < price_limit < 1 and tick > 0. A lock means close ==
  the tick-rounded limit (tol tick·1e-6). The carry multiplier applies to a carried limit-down SELL. Tests may import
  orders, but the AST read is lighter. (C)
     EVIDENCE: core/engine/orders.py:275 `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0        # INV-2: "an assumption, not measured" (R3:802)`; :407-411 `return math.floor(x / tick + _EPS) * tick`; :414-432; :504-506; tests/macro_m5_fills_events.py:21 `from core.engine import orders as O`
     IMPACT: Reimplement in core/odds. The equality test does an `ast.literal_eval` of the module-level assign.
     orders uses one tick for both edges, while the ladder may need different ticks per edge (ETF ref 2,005: lower
     edge 1,405 vs 1,404) (DQ28).

### 7.3 Calendars

* [store API] `CalendarSet(data_dir=None, *, config=None, buffer_s=None)` has `.file(fid)` (raises CalendarUnsigned),
  `.refusal(fid)` (never raises), `.version` ("unsigned" unless signed), `.holiday_set`, `.require_covered` and
  `.market_config`. CalendarFile has file_id, version, md5, covers_from, covers_to, signed_off_by, signed_utc, rows and
  doc. `.config` lazily loads `core.rules.macro_rules.load_store()["calendars"]` unless injected. (C)
     EVIDENCE: core/calendars/store.py:221-222 `def __init__(self, data_dir: Path | None = None, *, config: dict | None = None,`; :76-87 `class CalendarFile:` ... `md5: str`; :233-237 `from core.rules.macro_rules import load_store`; :268-271 `def version(self) -> str:`
     IMPACT: simulate takes an injected `cal`. Provenance records `cal.version` and `cal.file(fid).md5`.
     CALENDAR_UNSIGNED's "store loads" half is `cal.refusal(fid) is None` for each file the leg reads.
* [everything falls back to default() when cal is None] `cal or default()` appears in is_session, decision_time_utc,
  regime_tags and eight more clocks functions. regime_tags raises CalendarUnsigned when ANY tag has a row count other
  than one on d. (C; new, critic)
     EVIDENCE: core/calendars/clocks.py:192 `cal, d = cal or default(), _date(d)`; :241; core/calendars/regime.py:62-75 `cal = cal or default()` ... `if len(hits) != 1:` / `raise CalendarUnsigned(...)`
     IMPACT: Always pass cal=. Add a test that patches `store.default` to raise.
* [unsigned shipped set; refusal reproduced] All 17 files are unsigned drafts. is_session("KR"/"US"),
  sessions_between and regime_tags raise CalendarUnsigned; CRYPTO is always a session. Coverage: holidays_KRX
  2026-2027, kr_sessions and kr_regime_tags 1995-2027, holidays_NYSE 2025-2027. Past 2027-12-31 the call raises
  CalendarCoverageError. Neither exception subclasses ValueError.
     EVIDENCE: core/calendars/data/MANIFEST.yaml:1-4 `version: 0.1.0-draft` / `signed_off_by: null` ...; core/calendars/store.py:67-72 `class CalendarUnsigned(Exception):` / `class CalendarCoverageError(Exception):`; costs_cal cal_probe output
     IMPACT: Only crypto plans run until the owner signs. Catch both by name. Map coverage errors to a reason
     (DQ27). One test asserts that the shipped set refuses.
* [sessions_between and markets] `sessions_between(market, lo, hi, *, cal=None)` includes BOTH endpoints. Markets are
  KR, US, JP, CN, HK, TW and CRYPTO. KR reads kr_sessions and holidays_KRX; US reads holidays_NYSE. (C)
     EVIDENCE: core/calendars/clocks.py:223-229 `while probe <= hi:`; core/calendars/store.py:42-44 `MARKET_FILES = {` / `"KR": ("kr_sessions", "holidays_KRX"),` / `"US": ("holidays_NYSE",),`
     IMPACT: The half-open horizon is `sessions_between(m, start, start + timedelta(days=H - 1), cal=cal)`. Map
     krx -> KR, us -> US, crypto -> CRYPTO. KRX legs check kr_sessions, holidays_KRX and kr_regime_tags; US legs
     check holidays_NYSE.
* [close times come from the macro rules store] The KR close is `cfg["close_kst"]` (effective-dated) and the US close
  `cfg["close_et"]` = "16:00", both from data/macro/rules_v2.0.0.json. Only CN, HK and TW use market_closes.yaml. (C;
  new, critic)
     EVIDENCE: core/calendars/clocks.py:130 `close = _hhmm(effective_config(cfg["close_kst"], d, "calendars.KR.close_kst")["time"], "close_kst")`; :143 `return _hhmm(cfg["close_et"], "close_et"), cfg["tz"], frozenset(flags)`; data/macro/rules_v2.0.0.json:249 `"close_et": "16:00",`
     IMPACT: Finality via decision_time_utc depends on data/macro, which the calendar approval does not cover
     (DQ16).
* [regime tags: price_limit only; no special-regime data] price_limit is a fraction, 0.30 from 2015-06-15,
  open-ended. regime_tags is KR only (KeyError for others). The 15 tags include sell_tax_pct (0.2 percent from
  2026-01-01, open-ended) and tick_regime (a label, not a ladder). No tag marks an IPO day or reference reset. (C; tag
  list new)
     EVIDENCE: core/calendars/regime.py:62-66 `raise KeyError(f"regime_tags: no regime-tag file for market {market!r} (KR only)")`; core/calendars/data/kr_regime_tags.yaml:70-76 (price_limit 0.3), :389-396 (sell_tax_pct 0.2), :413-419 (tick_regime); `grep -n "tag:"` (15 distinct names)
     IMPACT: SPECIAL_REGIME has no data source (DQ21). sell_tax_pct ×100 -> bp is a 2027-safe tax source, while
     instruments.SELL_TAX_BP holds 2026 only.
* [16..22 sessions confirmed] Half-open 30-day windows over 2026-01-01..2027-12-02 hold 16-22 KRX sessions on the
  shipped holidays and on the fixture. The cap is 95.06x at 16 and 458.83x at 22; 1,000x needs 25 sessions. NYSE
  windows hold 18-22, with early closes on 2026-11-27, 2026-12-24 and 2027-11-26.
     EVIDENCE: costs_cal krx_count.py output `30d half-open window sessions min 16 max 22 n_starts 701`; spec:92
     IMPACT: The IMPOSSIBLE test asserts n in [16, 22] for 30 days. A >= 25-session horizon is not IMPOSSIBLE.
* [the old calendar package is different] `core.calendars.is_trading_day` serves generated data/calendars/*.json,
  not the signed store.
     EVIDENCE: core/calendars/__init__.py:1-3, :144 `def is_trading_day(market: str, day: date) -> Optional[bool]:`
     IMPACT: Never use it in core/odds.

### 7.4 Ticks, lots and minimums (research)

* [KRX stock ladder: research only] <2,000: 1; <5,000: 5; <20,000: 10; <50,000: 50; <200,000: 100; <500,000: 500;
  otherwise 1,000 KRW. The source is the KRX global page, "as of 2 October 2026". Another note says the ticks were not
  verified there.
     EVIDENCE: QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/E2_nyse_microstructure_execution.md:304-316; .../P4_backtest_econometrics_costs.md:262 `KRX tick sizes were not verified here.`
     IMPACT: The venues.yaml ladder is owner-signed and cites this URL (it is in the research corpus). Test the
     boundaries.
* [KRX ETF tick in repo] 1 KRW below 2,000 and 5 above, from 2023-12-11. One note conflicts, marked UNVERIFIED.
     EVIDENCE: core/quant/instruments.py:27; research_notes/QUANTGEN asset coverage expansion/etf_strategies.md:98
     IMPACT: Use the instruments table and do not duplicate it.
* [minimums: only Upbit confirmed] Upbit KRW 5,000 is confirmed. Bithumb 5,000 is stated, but its verification is
  unfinished. Coinone, Korbit and Gopax tables were not found. No OKX minimum or lot appears anywhere in the
  research. The Upbit KRW fee of 0.05% is confirmed. No Upbit tick table exists. US fractional trading is "from KRW
  1,000 at Toss (UNCERTAIN)", and the KIS minimums were not retrieved. The KRX lot is 1 share. (C; minimum detail
  new)
     EVIDENCE: research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas_verification.md:21 `**Upbit 5,000 KRW minimum is confirmed**`; crypto_domestic_and_overseas.md:8, :50; crypto_domestic_and_overseas_verification.md:14; .../overseas_via_brokers.md:9, :38; .../domestic_securities_derivatives.md:161
     IMPACT: Legs on venues without a signed minimum are NOT_TRADABLE. US defaults to whole shares. Crypto κ is the
     table rate unless the owner signs a tick ladder.

## 10. Report, provenance and language (new facts from the critic)

* [repo_anchor] `gate_ledger.repo_anchor(root=REPO_ROOT) -> str` reads .git/HEAD, then the loose ref or packed-refs, and
  returns `git:<sha>` or UNVERSIONED. It uses no subprocess, network or clock. (C)
     EVIDENCE: core/quant/gate_ledger.py:122-136 `def repo_anchor(root: Path = REPO_ROOT) -> str:` ... `return f"git:{text}" if re.fullmatch(r"[0-9a-f]{40}", text) else UNVERSIONED`; tests/macro_m7_ledger.py:147-153
     IMPACT: Importing it costs +29 closure files (config and data). It is 15 lines: copy it with an equality test,
     or compute it outside core/odds (DQ10).
* [tree_hash] `macro_artifacts.tree_hash(root=REPO_ROOT)` is a sha256 over core/**/*.py, data/macro/**/* and config.py,
  so every odds edit changes it. No test pins its value; it is a volatile field. `macro_artifacts.GIT_HASH =
  "UNVERSIONED"` is stale (the folder is a git repo now). (C)
     EVIDENCE: core/ficc/macro_artifacts.py:34 `GIT_HASH = "UNVERSIONED"      # ruling 3.1: the folder is not a git repository; never a fabricated sha`; :35 `TREE_GLOBS = ("core/**/*.py", "data/macro/**/*", "config.py")`; :53-61; tests/macro_m0_schemas.py:527 `S.VOLATILE_FIELDS == ("generated_at_utc", "git_hash", "tree_hash")`
     IMPACT: Importing it costs +46 closure files, core/engine/orders.py included, via risk_layer. It is 9 lines:
     copy it with an equality test, or compute it outside core/odds. Use repo_anchor, never GIT_HASH.
* [versions] `numpy.__version__` is 2.3.5. `importlib.metadata.version("cryptography")` is allowed in core/odds
  (importlib.metadata stays allowed) and is how owner.py reads RECORD files. (C)
     EVIDENCE: tests/compliance_guards.py:47 `importlib.metadata stays allowed: owner.py reads the RECORD files with it`; core/compliance/owner.py:594 `import importlib.metadata  # noqa: E402`
     IMPACT: The provenance version fields need no new dependency.
* [no language-guard precedent] The sentence catalogue, slot rendering and whole-word ban are new code. Spec 7.5 bans
  "safe" as a whole word. The internal name "floor_safe" and the hyphenated "floor-safe" (spec 10's table) must not
  reach rendered text. (C)
     EVIDENCE: grep for banned-word or language-guard code over core/ui/tests -> only tests/compliance_guards.py:224; spec:928-929 `Whole words banned: best, optimal, recommended, safe, guaranteed, ...`; spec:1093 `| Floor-safe sizing | ... | "Your floor holds even if this position goes to zero" |`
     IMPACT: The guard test tokenises catalogue text on word boundaries, hyphen included. Internal names never
     render (spec 7.5).
* [the catalogue's home decides whether it is signed] code_files hashes only .py files. The approved store accepts only
  rules, instruments, venues and calendar. So a catalogue kept in a YAML or JSON data file would be covered by NO
  signature, while one kept as Python constants is in the D14 code hash. (C)
     EVIDENCE: core/compliance/owner.py:773 `.glob("*.py")`; :29 `APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")`; tests/compliance_store.py:52 (store_put "odds" -> ValueError)
     IMPACT: Keep the catalogue in report.py (DQ19). test_16 allows non-ASCII UTF-8 there.

---

## Design questions for the odds plan

Each question lists the options with their evidence. Where a default fits the evidence, it is marked "lazy default".

**DQ1. What may core/odds import, given the D14 closure? (central decision)**
- A. Spec as written: import the data clients, strategies, validate, gate_stats, instruments, tf_books, calendars,
  gate_ledger and macro_artifacts directly. That makes a 63-file closure with config.py, the network clients and
  core/engine/orders.py. Any edit to them blocks new exposure until the owner re-signs. compliance_store:137-150,
  compliance_signer:638, plan P6 and the guard docstring must be rewritten. Evidence: spec:584-587; guards probe "SPEC
  SET adds 55 files"; critic probe (+46/+53 with orders.py).
- B. Small signed core: core/odds imports stdlib, numpy, scipy, core.isolation and core.compliance only, plus
  optionally garch (+2). Bars, CalendarSet, the replay output and provenance strings are produced by a caller outside
  core/odds and passed in with their hashes. Constants (LIVE_SHARPE_MULTIPLIER, DELIST_STRESS,
  LIMIT_DOWN_CARRY_COST_MULTIPLIER, the cost table, tick_floor_bp, repo_anchor, tree_hash, pw_block?) are copied, each
  with an equality test in tests/. Evidence: spec:160 (the precedent); closure probe.
- C. Hybrid: B for plan, simulate, bold and report; models keeps garch (+2); bars and the D13 replay live outside
  core/odds. Needs a spec ruling on file locations (spec:136-138 list them under core/odds).
- Non-options: lazy imports (still in the closure, owner.py:727-736), dynamic imports (banned, guards:300) and
  subfolders (escape D14; defeats it).
- Lazy default: C. It keeps the signed set reviewable and the existing closure tests' intent, amending
  compliance_store:137-139 for garch only. It needs an owner ruling because it departs from spec 4's file list.

**DQ2. How bars.py reaches the data clients.** Options: module-level imports (`import core.odds.bars` then runs
load_dotenv and the state-root scan through kis_client's import) or lazy imports inside each seam (no side effects,
same closure). Evidence: config.py:26-30; data/krx/kis_client.py:53. Lazy default: one module-level seam per source
(`_kis_daily`, `_upbit_daily`, `_binance_daily`, `_yf_download`), each importing its client inside, looked up at
call time.

**DQ3. Where the bars seams are patched in tests.** Options: (a) add them to `tests.macro_acceptance._touchpoints()`.
Every suite then imports core.odds.bars on every guard entry, a broken bars import breaks every guarded test, and
T-HERM-01 is not affected unless a probe is added (CORRECTED). (b) An odds-local nested patch in
`odds_acceptance._wrap` with the same save/restore idiom and `_boom`. Evidence: tests/macro_acceptance.py:52-98,
:171-193. Lazy default: (b), plus one odds probe test.

**DQ4. How simulate learns the calendar approval.** Options: (a) call owner's privates `_log_lines`/`_up_to` as
rules._calendar_line does; (b) the follow-up adds a public `owner.calendar_in_force(now)`; (c) add a Context field
(model.py and owner.py change, code hash). Then load from `store_dir()/calendar/<sha>/` (TOCTOU between store_get and
the load) or from the repo draft only when its calendar_sha256 equals the signed sha. Evidence:
core/compliance/rules.py:903-920; owner.py:670-680; model.py:165-178. Lazy default: (b), landed by the follow-up
before the odds simulate task. Tests use `fixture_set()` plus an approval in a temp home.

**DQ5. GREY_LEG detection.** Options: (a) reuse gate's private `_in_force`/`_matches`; (b) copy them into core/odds
(drift risk); (c) a public gate helper or a Screening field (`grey_rows`) in the follow-up (code hash).
"decision.warnings non-empty" is fragile, since KR-KIS-US-OPTION also warns. Evidence: gate.py:295, :385;
kr_rules.yaml:307, :513. Lazy default: (c).

**DQ6. Should review_by force a simulated exit?** Spec 6.3 says every review_by, auto_off or effective_until in the
horizon exits. The monthly cadence puts review_by at 2026-11-22/23 on every row, which caps every horizon at about 30
days. Option: exit only on auto_off or effective_until, and show review_by as RULE_CHANGE_IN_HORIZON wording.
Evidence: gate.py:643-651; kr_rules.yaml review_by counts; rules.py:524-525. This needs an owner ruling; the default
is the spec as written.

**DQ7. Which equity goes into `Positions(equity_krw=...)`, and how later OKX stakes are capped.** Options: the plan's W
(stake_krw) or the owner's real total equity, which is unknown to a simulation. Only the first stake is screened, so
bold-play stakes after a win can exceed cap × equity. Evidence: gate.py:334-339, :612-615; owner.py:964. Lazy
default: W, and every simulated OKX entry is capped at `ctx.owner.caps["okx_equity_share"] × W`, with the cap
stated on the card.

**DQ8. The venues.yaml extension.** Options: (a) new optional per-venue keys in `tradegen.venues/1`, with Venue fields
defaulted; (b) bump to `tradegen.venues/2` with a nested odds block, which refuses old signed bytes. Who owns the
rules.py change: the odds plan or the follow-up, batched with D15 for one re-sign? The edit must keep the byte pins
(okx partition, tag_required counts, the upbit markets line), the shape pins (LF, ≤ 256 KB, six venues, sources) and
research-only URLs. Evidence: rules.py:636-642, :701; tests/compliance_tables.py:615, :633, :897-902, :1089-1150;
tests/compliance_gate.py:336-340, :695-697, :998-1000. Lazy default: (a), as the first odds task, in the same
change as the parser and its tests.

**DQ9. The cost rate κ for books where cost_per_side raises.** KRX_stock_book, US_shares_KIS and crypto_venue raise
NotTradable at any price. Options: max(table rate, tick_floor_bp(price, venues ladder tick)) via instruments (+22
closure), or a local one-line copy of tick_floor_bp with an equality test, or the table rate alone where no ladder
is signed. Sub-questions: does the KRX stock sell floor include the 20 bp tax (from regime_tags sell_tax_pct, which
is 2027-safe, or SELL_TAX_BP, which is 2026 only)? Is COMMISSION_BP = 1.4 right for US and crypto? Evidence:
instruments.py:105-122, :168-182; kr_regime_tags.yaml:389-396; costs_cal probe. Lazy default: ETF through
cost_per_side; others max(table, local floor) with the owner-signed ladder; tax 0 inside the floor (the rate already
includes it); no floor for US or crypto until a tick is signed.

**DQ10. Provenance helpers.** Options: import gate_ledger.repo_anchor (+29) and macro_artifacts.tree_hash (+46, with
orders.py), or copy both (24 lines) with equality tests, or have the caller compute them. Evidence: critic section
10. Lazy default: local copies plus equality tests.

**DQ11. TwoPointBootstrap block length.** Options: import gate_stats.pw_block (+23) or copy the arch port (about 40
lines, verified to 1e-9 against arch) with an equality test. Floor b at 1 (pw_block returns 0.62 on white noise).
Cap the 2× variant at pw's own ceil(min(3√n, n/3)) or not (KRW-BTC: 177 > 172). Evidence: gate_stats.py:40-77;
models probe. This hinges on DQ1. Under B or C, copy it.

**DQ12. The GARCH pilot.** Pilot size and seed are unspecified. Is "e^{r_h}" cumulative or per step (margins 1.40 and
2.32 SE)? Rebuild sigma by inverting eps from ret, or run a parallel recursion? Quad over binned or deduplicated
pilot sigmas (about 3 ms per quad), at what resolution? How is "compounded" aggregated (sum of |log ratio| per path,
then max)? Evidence: garch.py:674-701; models probes. The plan must fix all four.

**DQ13. The D13 replay input digest.** The cache's last row (2026-09-25) is a running price, so a fresh
`UpbitPublic().daily("KRW-BTC", days=4000)` will not hash equal. Options: hash the cached file's rows as the
reference and accept live mismatches as CARD_NOT_REPRODUCED; cut the comparison window at 2026-09-24; or run the
replay from the cache only. Also: the canonical form of the closes-only digest (spec 7.2's {symbol, source, dates,
open, close, ...} does not fit a closes-only file). Evidence: data.md cache mtimes; models replay golden. Lazy
default: the replay runs on the cached closes (its golden is exact), and a live pull is a separate check.

**DQ14. CHUNK in tests.** CHUNK = 200,000 and a partial chunk is refused. Options: every simulate test pays one full
chunk (about 1 s per 30 steps for GARCH, more for the bracket logic), or CHUNK is a module constant that tests swap
with save/restore, while the refusal is still tested at the real value. Evidence: spec:812, :1053; harness timing.
Lazy default: swap in tests, plus one full-size test.

**DQ15. Bars cache location and switch.** Options: `core.isolation.state_root()/"odds"/"bars"` (+0 closure) or
`config.state_path("TRADEGEN_ODDS_BARS", ...)` (+20). Does the cache follow FICC_CACHE_TTL_SECONDS (0 under hermetic,
so it never runs in tests) or have its own switch? Is it a TTL, a pinned window or refetch-on-request (adjusted
series get rewritten)? Where does yfinance's DB go (`set_tz_cache_location`)? Evidence: core/isolation.py:105-110;
config.py:57-60; macro_acceptance.py:70; yfinance cache.py:625-638. Lazy default: core.isolation path, its own
switch, pinned by window and hash, refetch on request.

**DQ16. Dating and finality.** US: seoul_date = ny_date + 1 by fixed rule, or via decision_time_utc (needs a signed
cal and reads close_et from data/macro). KRW=X: its close instant is unknown offline. KRX and US finality: clocks, or
fixed 15:30 KST / 16:00 ET plus 10 minutes (early closes are then refetched late, which is harmless). Which date is
`on=` for a US fill? Evidence: clocks.py:130, :143, :235-246; data.md open questions 1-2, 7.

**DQ17. Feeds per venue.** bithumb, coinone and korbit KRW-BTC: Upbit KRW-BTC as a flagged proxy, or refused? OKX
BTC/USDC: BTCUSDC × KRW-USDC, or BTCUSDT as a proxy? The KRW-USDT listing date is found at runtime and recorded for
PROXY_DATA. Evidence: venues.yaml:13-46; data.md. This needs an owner ruling.

**DQ18. core/odds/__init__.py.** Options: create a 0-byte file (every other core subpackage has one; setuptools
`packages.find` needs regular packages; the guard accepts it), or leave a namespace package (plan P1 created none).
Evidence: critic `__init__` loop; pyproject; guards:408. Lazy default: 0-byte file.

**DQ19. Where the sentence catalogue lives.** Python constants in report.py are signed by D14. A data file is signed
by nothing, because the store refuses new kinds. Evidence: owner.py:29, :773; compliance_store.py:52. Lazy default:
report.py constants.

**DQ20. Odds-own static guards.** Options: widen the compliance allowlist, wall-clock, HTTP-verb and `__main__` guards
to core/odds with per-file allowlists (numpy everywhere; scipy and garch in models; network only via bars seams; and
the guards then ban `np.delete` and `np.put`), or write an odds-own guard module (for example "no clock in simulate,
bold or report", "no data/ import outside bars", "no package re-export import"). Evidence: guards section 2. Lazy
default: an odds-own guard module with positive controls; leave the compliance guards' scopes alone.

**DQ21. SPECIAL_REGIME detection.** No repo data marks IPO days or reference resets (15 regime tags, none per
symbol), and spec 13 defers special KRX regimes. Options: owner-signed per-symbol data in venues.yaml, KIS
`flng_cls_code` passed through (an edit to data/krx/kis_client.py), or a narrow documented detector (for example the
first session of a symbol's history). Evidence: critic section 3.3; kis_client.py:292-306. This needs an owner
ruling.

**DQ22. Persisted odds state.** The market seed uses a "run counter" and a "comparison id", and the card counts "K plans
(and J typed win rates) in this session". Nothing in the repo stores these. Options: a small JSON under
`state_root()/odds/` written with checked_target, or in-memory per process only (the counter then resets).
Evidence: spec:807-811, :922-924. Lazy default: a JSON file under state_root()/odds with the grokteam write
pattern.

**DQ23. The `Fraction` name.** Spec 7.1's plan type `Fraction` collides with `fractions.Fraction`, which bold_even needs
for exact arithmetic. Options: keep plan.Fraction and write `fractions.Fraction` qualified in bold.py, or rename the
plan type (spec text change). Evidence: spec:656; models bold_even probe.

**DQ24. Signed-home test helpers.** Options: import the privates from tests.compliance_store (legal, since only
defined test_* are collected), or move them into tests/compliance_fixtures.py (a follow-up test refactor). Evidence:
tests/compliance_store.py:242-299; compliance_acceptance.py:70-71.

**DQ25. The brittle registration literal.** Options: the odds plan edits `"paper, grokteam or compliance"` to `"..., compliance
or odds"` in the wiring task, or the follow-up first loosens the test to a per-suite check. Evidence:
tests/compliance_guards.py:483-489; ledger:69.

**DQ26. Plan order.** Follow-up first, then odds, then one owner re-sign? Before or after GPT's check (after
2026-10-30 14:40)? Batch every code-hash change (D15 loader, venues parser, public helpers, closure hardening) into
one signing. Evidence: ledger:235; owner.py:773.

**DQ27. CalendarCoverageError.** A horizon past 2027-12-31 raises CalendarCoverageError. Options: map it to
CALENDAR_UNSIGNED, or add a named reason (the spec lists none). Evidence: store.py:71-72, :323-328; costs_cal probe.

**DQ28. Band tick rounding per edge.** orders.limit_prices uses one tick for both edges. With a price-dependent ladder,
the lower edge can need a smaller tick (ETF ref 2,005: 1,405 vs 1,404). Pick one rule and test it. Evidence:
orders.py:407-432; costs_cal probe.

**DQ29. Kelly and the replay column.** Which seed or stream feeds μ_lb's stationary bootstrap (the card's 11, the
market seed, or a replay stream)? Is "block length of 10" an exact mean of 10? Which mean block does the
TESTED_REPLAY column use (card.protocol.block = 10, or pw_block of the OOS series)? Evidence: spec:679-681, :774-776;
gate_stats.block_indices truncates to int.

**DQ30. Fixed charges φ and check_extras.** A missing φ_b or φ_s: 0, or NOT_TRADABLE? Where does check_extras live
(models.py per review F2, or plan.py), and what is its signature? Evidence: spec:183, :662-665;
round1_claude_workflow.md:155. Lazy default: missing means NOT_TRADABLE for the venue's minimum and lot, and 0 for
φ only if the owner signs an explicit 0.

**DQ31. Variance in the empirical Bernstein bound.** ddof = 1 (Maurer-Pontil) or 0? Does R include both tails? Evidence:
spec:888. The plan pins it in a unit test against hand values.

**DQ32. The order of the odds refusals.** When several apply (owner BROKEN, LIMITS_UNSET, UNSUPPORTED_PRODUCT,
CALENDAR_UNSIGNED, STUCK_AT_START, a gate BLOCK), which is reported first? The gate already ranks its own reasons
(gate.py:29). The plan states a fixed order, for example: product checks first (plan.py), then state and limits,
then calendar, then sizing, then screen.

## Open questions (not answerable from the repo)

1. When does a Yahoo KRW=X daily bar close, and in which timezone? That sets its Seoul date. The only evidence: a
   2026-10-02 row was still provisional at 17:20 KST (QUANTGEN_MACRO_INTEGRATION.md:5715).
2. Is a Yahoo FX bar's Open a real opening print? How should a US leg's KRW price at the US open be formed, when the
   KRW=X open belongs to a different instant?
3. When did Upbit list KRW-USDT, and does its early history have gaps?
4. Owner rulings needed: DQ1 (closure strategy), DQ6 (review_by exits), DQ17 (proxy feeds), DQ21 (SPECIAL_REGIME
   data), and whether a signed closure that includes network data clients and core/engine/orders.py is acceptable.
5. Should numpy and scipy RECORD files join `_RECORD_DISTS`, so that an upgrade forces a re-sign? This needs owner.py
   and sign.py changed in lockstep and an owner act. Spec 6.4 currently accepts the venv as outside the hash.
6. Is `python -m core.odds.<x>` (where `__name__` is "__main__", so the T-CTX-01 runtime guard sees no acting frame)
   acceptable, as it is for the compliance CLIs?
7. Do injected CalendarSet methods running unsigned code satisfy the owner, with integrity resting on the signed
   calendar approval and the recorded md5s?
8. Is the macro rules store's close_kst and close_et (data/macro, outside the calendar approval) acceptable as the
   source of finality instants?
9. The ledger's "reviewer's triage" (ledger:238) is not in the repo. Were any deferred minors explicitly accepted
   there that this digest classes as FOLLOWUP?
10. H2 ownership: a fold-side fix in the follow-up (it flips tests/compliance_owner.py:958-960 and over-blocks), or
    the execution writer with a trusted clock? T2: an alerts.jsonl time bound (a contract change to owner_state), or
    keep it as a documented limit?
11. Ancestor junctions of the state root (OneDrive reparse points, ledger:86): in or out of the follow-up?
12. Execution: where do adapters live (under core/, which is scanned, or a new package that needs runtime_py()
    widened), and do they join the D14 closure? Does "halts for good" forbid re-arming? Should a new system kind
    exist for a daily stop? Separate TRADEGEN keys? A KIS mock-server phase? OKX private-API research? An immediate
    alert channel?
13. The harness reader measured 7.27 s for `import tests.run_all`. The critic did not re-measure it.
14. Does the owner want odds tests to inject `config=` into fixture_set, avoiding the read of the shipped macro rules
    store for Saturday and close-time lookups, or is that read-only access acceptable?
```
