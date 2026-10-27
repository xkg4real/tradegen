# Area: guards that new code under core/odds must pass (and the D14 closure question)

Repo: C:/Users/whydi/OneDrive/Desktop/TRADEGEN, main at 995534b, tree clean. All facts were checked against the current
tree. The closure numbers come from read-only probes in the scratchpad (`odds_plan/guards_probe.py`, `chain_probe.py`,
`full_probe.py`). Those probes call `owner._repo_imports` / `owner._module_file` and `context_log.scan_isolation` on
the real files and write nothing to the repo.

## 1. tests/compliance_guards.py: what scans core/odds today

* [scope: what reaches core/odds] `ODDS = CORE / "odds"` is defined. Only some guards include it. Raw text (full
  list): COMPLIANCE+ODDS. Forbidden modules + star/dynamic imports: COMPLIANCE+ODDS. Def names: all of CORE. seal_context:
  all of CORE. Empty `__init__`: ODDS when present. HTTP verbs, import allowlist, wall clock and `__main__` blocks:
  COMPLIANCE ONLY.
     EVIDENCE: tests/compliance_guards.py:22 `COMPLIANCE, ODDS = CORE / "compliance", CORE / "odds"`; :233 `_scope(COMPLIANCE, ODDS).items()` (raw); :300 `for rel, src in _scope(COMPLIANCE, ODDS).items()` (forbidden+dynamic); :244 `_scope(CORE)` (def); :373 `files = _scope(CORE)` (seal); :269 `_scope(COMPLIANCE).items() for h in _http_hits`; :340 `_scope(COMPLIANCE).items() for h in _allowlist_hits`; :361 `_scope(COMPLIANCE).items() for h in _clock_hits`; :385 `_scope(COMPLIANCE).items() for h in _main_block_hits`
     IMPACT: Today core/odds may import numpy, core.quant.*, data.*, yfinance and core.calendars.*, and may read the
     wall clock, without failing any compliance guard. If the plan wants those rules for odds, it must widen the four
     `_scope(COMPLIANCE)` calls on purpose, each with a positive control on a `core/odds/x.py` name.
* [scope is recursive, rel paths] `_sources` uses `rglob("*.py")` and skips `__pycache__`, so a subfolder of core/odds is
  scanned too. `_scope` asserts only that core/compliance/__init__.py exists, so a core/odds folder with no .py files is
  fine.
     EVIDENCE: tests/compliance_guards.py:69-71 `for p in sorted(base.rglob("*.py")):` / `if "__pycache__" not in p.parts:`; :77 `assert INIT in files, f"scan scope: {INIT} missing"`
     IMPACT: The guards see core/odds/**. The D14 seed list below is NOT recursive (see section 4).
* [raw text, full list, case-insensitive, docstrings and comments INCLUDED] For core/odds/**/*.py these are banned:
  private_key, seed_phrase, order_cash, order-cash, place_order, submit_order, tttc0802u, tttc0801u, vttc0802u,
  r18_research_log, r18_break_log, `context_log/`, `tests.reference`, reference_mode. Case-sensitive: CANO, KIS_ACCOUNT,
  ACNT_PRDT_CD.
     EVIDENCE: tests/compliance_guards.py:27-30 `RAW_CI = ("private_key", "seed_phrase", "order_cash", ... "context_log/", "tests.reference",` / `"reference_mode")` / `RAW_CS = ("CANO", "KIS_ACCOUNT", "ACNT_PRDT_CD")`; :229 `_raw_hits(X, "x = 1  # the CANONICAL form\n")` is a hit
     IMPACT: The report's sentence catalogue and every docstring must avoid these words. Never write upper-case
     "CANONICAL" (or any other "CANO" substring). Do not write "never reads context_log/" in prose. Do not name the
     reference package.
* [forbidden modules, any depth of the file, function level included] core/odds may not import core.engine.orders (in
  any form, `from core.engine import orders` and relative `..engine` included), core.quant.forward_sim,
  core.quant.refusal, core.ficc.context_log, core.ficc.macro, core.ficc.flows_log or core.skills.macro_daily. Sibling
  names such as core.ficc.macro_schema and core.engine.books are allowed.
     EVIDENCE: tests/compliance_guards.py:43-44 `FORBIDDEN_MODULES = ("core.engine.orders", "core.quant.forward_sim", "core.quant.refusal", "core.ficc.context_log",` / `"core.ficc.macro", "core.ficc.flows_log", "core.skills.macro_daily")`; :140 `t == m or t.startswith(m + ".")`; :283 `assert not _forbidden_hits(X, "from core.ficc import macro_schema\nfrom core.engine import books\n")`
     IMPACT: Declare `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` locally and add a test (in tests/, not core/) that
     asserts it equals the orders constant. This is the pattern spec 4 already names. The check is only on DIRECT
     imports: a transitive path to orders.py is not flagged (see section 4).
* [dynamic and star imports banned in core/odds] Banned: `from x import *`, `__import__`, `import_module`,
  `exec_module`, `load_module`, and `exec` and `eval` as ANY Name or Attribute (so `df.eval(...)` or a variable named
  eval also hits). Also every import form of importlib.util, importlib.machinery, runpy, pkgutil, zipimport, pydoc,
  timeit, code and cProfile. importlib.metadata stays allowed.
     EVIDENCE: tests/compliance_guards.py:49-51 `DYNAMIC_NAMES = frozenset({"__import__", "import_module", "exec_module", "load_module", "exec", "eval"})` / `DYNAMIC_MODULES = ("importlib.util", "importlib.machinery", "runpy", "pkgutil", "zipimport", "pydoc", "timeit",` / `"code", "cProfile")`; :153-156 `for node, _f in _walk(tree):` ... `if name in DYNAMIC_NAMES:`
     IMPACT: No pandas `.eval`, no `timeit`, no `cProfile` profiling in core/odds. A dynamic import cannot be used to
     keep the D14 closure small (and P6 already counts lazy imports, see section 4).
* [def-name ban is core-wide] No function or method in core/** (core/odds included) may be named transfer, withdraw
  or deposit_address. transfer_out and is_withdraw_exit are fine.
     EVIDENCE: tests/compliance_guards.py:32 `DEF_NAMES = frozenset({"transfer", "withdraw", "deposit_address"})`; :243 `assert not _def_hits(X, "def transfer_out():\n    pass\ndef is_withdraw_exit():\n    pass\n")`; :244 `_scope(CORE)`
     IMPACT: Applies to odds helper names such as a ledger `transfer` step. Use other names.
* [seal_context only in owner.py, core-wide] Any Name, Attribute or import alias `seal_context` anywhere in core/
  other than core/compliance/owner.py fails.
     EVIDENCE: tests/compliance_guards.py:58 `SEAL_USER = "core/compliance/owner.py"`; :204-207 `(isinstance(n, ast.Name) and n.id == "seal_context")` / `or (isinstance(n, ast.Attribute) and n.attr == "seal_context")` / `or (isinstance(n, ast.alias) and n.name == "seal_context")`
     IMPACT: core/odds gets a Context only from `owner.load_context(now, positions)`, or as an argument. Odds tests
     build contexts through load_context in a temp home (tests/ is not scanned).
* [core/odds/__init__.py must be 0 bytes if it exists] The guard tolerates its absence (P1).
     EVIDENCE: tests/compliance_guards.py:408 `assert not (ODDS / "__init__.py").exists() or not _init_hits(ODDS / "__init__.py"), "core/odds/__init__.py"`; :218 `return [] if path.is_file() and path.stat().st_size == 0`
     IMPACT: The plan either creates an empty `core/odds/__init__.py` or leaves core.odds a namespace package. Both
     pass. No code (no re-exports) may go in it.
* [T-CTX-01 prefix test already names core.odds.plan] The guard asserts that core.odds.plan is acting and core.odds is not.
     EVIDENCE: tests/compliance_guards.py:395-396 `assert CL.is_acting_module("core.compliance.gate") and CL.is_acting_module("core.odds.plan")` / `assert not CL.is_acting_module("core.compliance") and not CL.is_acting_module("core.odds")`
     IMPACT: Already satisfied. Do not rename the prefix.
* [what the allowlist would demand IF extended to core/odds] `_allowed` accepts only stdlib, yaml, cryptography and
  the prefixes core.isolation and core.compliance. core.odds itself is NOT on it, so even `from . import plan` inside
  core/odds would fail. numpy, scipy, yfinance, config, core.quant.* and core.calendars.* fail. NETWORK_MODULES fail
  even though they are stdlib. cryptography must be imported inside a function.
     EVIDENCE: tests/compliance_guards.py:160-163 `return (top in sys.stdlib_module_names or top in ("yaml", "cryptography")` / `or any(name == p or name.startswith(p + ".") for p in ("core.isolation", "core.compliance")))`; :310-312 `for src in ("import numpy\n", "import config\n", "from core.quant import instruments\n",` / `"from core import isolation, quant\n", "from core.calendars.store import CalendarSet\n",`
     IMPACT: Extending the allowlist to core/odds as written cannot work: the odds engine needs at least numpy
     (vectorised simulator, SeedSequence, spec 7.3). The extension must add "core.odds" to the prefixes and numpy (and
     scipy if GarchT stays) to the third-party set. It also needs new positive and negative controls.
* [HTTP-verb guard IF extended would hit numpy calls] `_http_hits` flags ANY attribute call named post, put, delete,
  patch or request, whatever the object.
     EVIDENCE: tests/compliance_guards.py:33 `HTTP_VERBS = frozenset({"post", "put", "delete", "patch", "request"})`; :131 `if (isinstance(n.func, ast.Attribute) and name in HTTP_VERBS) or name in NETWORK_CALLS:`
     IMPACT: If the plan widens this guard to core/odds, simulate.py and models.py must avoid `np.delete`, `np.put`
     and `ndarray.put`. A requests-style `.request` in bars.py would also hit.
* [wall-clock guard IF extended] It flags datetime.now/utcnow/today, date.today, and every `time.*` reader in CLOCKS
  (perf_counter and monotonic included), through aliases too. Any `from time import ...` is flagged. Only the CLI
  main() bodies of compliance rules.py and alerts.py are exempt.
     EVIDENCE: tests/compliance_guards.py:53-57 `CLOCKS = {"datetime": {"now", "utcnow", "today"}, "date": {"today"},` / `"time": {"time", "time_ns", "monotonic", ... "perf_counter", ...` / `CLOCK_IN_MAIN = ("core/compliance/rules.py", "core/compliance/alerts.py")`
     IMPACT: Seeds must never depend on time (spec 7.3: the seed comes from data hashes, the calendar digest, the
     comparison id and a run counter). If the plan extends this guard, bars.py takes `now` as an argument to drop a
     provisional last bar, and any odds CLI main must join CLOCK_IN_MAIN.
* [the network-module ban exists only inside the allowlist checker] NETWORK_MODULES (urllib, http, socket, ssl,
  asyncio, multiprocessing, logging.handlers, xml.sax and others) is enforced only by `_allowlist_hits`, which is
  COMPLIANCE-only.
     EVIDENCE: tests/compliance_guards.py:39-41 `NETWORK_MODULES = ("urllib", "http", "socket", "_socket", ...` ; :169-172 `for m in NETWORK_MODULES if t == m or t.startswith(m + ".")]` / `... a network module; core/compliance never needs one`
     IMPACT: core/odds may import socket or urllib today. bars.py legitimately reaches the network (spec 4: "network
     via seams"), so a ban for odds would need a per-file carve-out, or bars must live outside core/odds.
* [suite-registration guard pins a literal that an "odds" suite would change] The guard asserts that the exact text
  "paper, grokteam or compliance" appears in tests/run_all.py and README.md.
     EVIDENCE: tests/compliance_guards.py:488-489 `assert "paper, grokteam or compliance" in (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")` / `... in (ROOT / "README.md").read_text(encoding="utf-8")`; tests/run_all.py:113 `"run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance"`; README.md:816 same list
     IMPACT: Adding "odds" to the --suite help and the README list (e.g. "..., grokteam, compliance or odds") breaks
     this compliance guard. The odds plan must update the literal in the same task. run_all.py and README.md are CRLF
     (A.0): use the Edit tool only.

## 2. Repo-wide guards (T-RO-01, test_08, test_09, test_s4, other core-wide scans)

* [T-RO-01 scope covers core/odds] It scans runtime_py() (core/**, data/**, ui/**, main.py, config.py) plus docs/*.py,
  with docstrings stripped and string literals kept.
     EVIDENCE: tests/acceptance.py:48-54 `for base in (ROOT / "core", ROOT / "data", ROOT / "ui"):` ... `files.extend([ROOT / "main.py", ROOT / "config.py"])`; tests/macro_m0_harness.py:63-64 `files = runtime_py() + sorted(p for p in (ROOT / "docs").glob("*.py"))`; tests/acceptance.py:31-45 `_code_only` drops docstrings
     IMPACT: Every core/odds .py file is in scope.
* [T-RO-01 lists (verbatim, unchanged since the earlier map)] Text CI: order_cash, order-cash, place_order,
  submit_order, tttc0802u, tttc0801u, vttc0802u, /v1/orders, /v1/withdraws, /v1/deposits/generate_coin_address,
  /api/v3/order, /sapi/v1/capital/withdraw, /sapi/v1/capital/deposit, private_key, seed_phrase. Text CS: KIS_ACCOUNT,
  CANO, ACNT_PRDT_CD. Path regex /uapi/.../trading/. 21 banned import tops (ccxt, web3, pyupbit, binance, okx, bybit and
  others). 27 banned call names (withdraw, transfer, deposit_address, create_order ...). post/put/delete/patch on a URL
  containing order/withdraw/transfer/deposit.
     EVIDENCE: tests/macro_m0_harness.py:28-35 `FORBIDDEN_TEXT_CI = (` ... `"private_key", "seed_phrase",` / `FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")`; :36 `FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")`; :38-42 `FORBIDDEN_IMPORTS = frozenset({` / `"ccxt", "web3", "pyupbit", "binance", ...`; :44-50 `FORBIDDEN_CALLS = frozenset({`; :51-52 `MUTATING_HTTP = frozenset({"post", "put", "delete", "patch"})` / `MUTATING_URL_WORDS = ("order", "withdraw", "transfer", "deposit")`
     IMPACT: core/odds must not import ccxt or okx, must not call `.withdraw()` or `.transfer()`, and must not carry
     Binance or Upbit order endpoint strings. yfinance and numpy are NOT banned by T-RO-01.
* [T-RO-01 orders-import rule is direct-only] Outside core/engine/, core/skills/macro_daily.py and
  core/skills/pipeline.py, no file may `import core.engine.orders` or `from core.engine import OrderBook|SimulatedOrder|OrderStatus|order_id`.
     EVIDENCE: tests/macro_m0_harness.py:57-59 `ORDERS_IMPORTERS_ALLOWED = ("core/engine/", "core/skills/macro_daily.py", "core/skills/pipeline.py")` / `ORDERS_NAMES = {"OrderBook", "SimulatedOrder", "OrderStatus", "order_id"}`; :153-158 `if isinstance(node, ast.Import) and any(a.name == "core.engine.orders" ...`
     IMPACT: The same as the compliance FORBIDDEN_MODULES rule. A transitive reach (risk_layer -> core.engine ->
     orders) is not flagged by either.
* [T-RO-01 YAML scan does not cover venues.yaml] Only core/skills/macro_workflows/*.yaml is scanned. The compliance
  raw-text guards read .py files only.
     EVIDENCE: tests/macro_m0_harness.py:60 `WORKFLOW_YAML = ROOT / "core" / "skills" / "macro_workflows"`; :136-137 `if WORKFLOW_YAML.is_dir():` / `hits += [h for p in sorted(WORKFLOW_YAML.glob("*.yaml")) for h in _yaml_offences(p)]`; tests/compliance_guards.py:69 `base.rglob("*.py")`
     IMPACT: Extending core/odds/venues.yaml (lots, ticks) is unguarded text-wise. It is covered by the venues
     approval (its sha256 changes, so the owner re-approves; P1).
* [test_08 raw text, case-insensitive] It reads the raw text of runtime_py(), docstrings and comments included, and
  fails on order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U and VTTC0802U.
     EVIDENCE: tests/acceptance.py:169-175 `def test_08_no_broker_order_path():` / `needles = ["order_cash", "order-cash", "place_order", "submit_order",` / `"TTTC0802U", "TTTC0801U", "VTTC0802U"]` / `blob = "\n".join(_read(p) for p in runtime_py()).lower()`
     IMPACT: The report's "not in these numbers" box (spec 7.5: "unfilled orders", "broker refusals") is fine, but
     no text may contain "place_order" or "replace_order".
* [test_09 raw text, case-sensitive] It fails on KIS_ACCOUNT, CANO or ACNT_PRDT_CD anywhere in runtime_py() raw text.
     EVIDENCE: tests/acceptance.py:178-182 `def test_09_no_account_credentials_requested():` / `for name in ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD"):`
     IMPACT: Same "CANONICAL" trap as above, in .py comments and docstrings.
* [test_s4 does not cover core/odds] It checks a fixed list of 8 files for wall-clock calls and keeps the engine
  files untouched or add-only.
     EVIDENCE: tests/macro_m5_integration.py:55-58 `S4_MODULES = ("core/engine/books.py", "core/engine/orders.py", ... "core/quant/risk_layer.py")` / `UNTOUCHED = ("core/engine/state.py", "core/engine/runtime.py", "core/engine/feed.py", "core/engine/__init__.py")` / `ADD_ONLY = ("core/engine/orders.py", "core/engine/evaluator.py", "ui/trading_page.py")`; :321 `if (name in ("datetime", "date") and node.func.attr in ("now", "utcnow", "today")) or (name == "time" and node.func.attr == "time")`
     IMPACT: The odds plan must not edit core/engine/*. Reading the orders constant is a test-side assertion only.
* [T-TREND-04 scan covers core.odds (acting)] For every acting module in core/** (core.odds.* now included), a DIRECT
  import of core.quant.forward_sim, core.quant.refusal or their submodules fails.
     EVIDENCE: tests/macro_m8_forward.py:506-511 `if CL.is_acting_module(name) or name.startswith("core.ficc.") or name.startswith("core.skills."):` ... `any(i in ("core.quant.forward_sim", "core.quant.refusal", "core.quant.forward_sim.trend_axis") or i.startswith(("core.quant.forward_sim.", "core.quant.refusal."))`
     IMPACT: Redundant with FORBIDDEN_MODULES, but it is a second test that will name core/odds if this is violated.
* [reference-mode scan covers core/**] No core module may name `tests.reference` or `reference_mode` in code, nor
  pass `reference_only=True`.
     EVIDENCE: tests/macro_m2_costed.py:365-372 `for path in sorted(CORE.rglob("*.py")):` / `if "tests.reference" in code or "reference_mode" in code:` / `if isinstance(node, ast.keyword) and node.arg == "reference_only" and \`
     IMPACT: If odds calls `costed_path`/`vt_weights`, it must not pass reference_only=True.
* [r18_research_log may appear only in context_log.py] A raw-text scan of core/ui/docs/config/main requires that only
  core/ficc/context_log.py contains "r18_research_log".
     EVIDENCE: tests/macro_m6_context.py:506-509 `for p in list((ROOT / "core").rglob("*.py")) + ...` / `"r18_research_log" in p.read_text(...)` / `assert hits == ["core/ficc/context_log.py"], hits`
     IMPACT: Already implied by RAW_CI. A third test names the same failure.
* [Kish design-effect scan covers core/**] No core code may implement `X / (1 + (X - 1) * Y)` in either operand
  order, define, import or call a `kish*` name, or assign a revision count to N.
     EVIDENCE: tests/macro_m7_ledger.py:333-338 `files = [p for base in ("core", "docs") for p in (ROOT / base).rglob("*.py") ...` / `hits = GL.scan_forbidden(sources)`; core/quant/gate_ledger.py:864-871 `design = (r"\b\w+\s*/\s*\(\s*" + one + r"\s*\+\s*(?:" + paren_m1 ...` / `"revision_count_as_N": re.compile(r"\b[nN]_?(?:raw|eff|equiv|clusters)\s*=\s*[^\n]*revision"),`
     IMPACT: An effective-N or variance-inflation formula in models.py, simulate.py or report.py (for example for the
     HIDDEN_EDGE bound or the bracket count n) must not have that shape. Rewrite it algebraically.
* [0.4 live-multiplier scan covers core/**] It flags a line that carries a live word (haircut, expected_live,
  live_sharpe, step9, g9) together with a 0.4 multiplier.
     EVIDENCE: tests/macro_tf_gov.py:262-263 `_MULT_04 = re.compile(r"(?<![\d.])0\.40?\s*(\*|x\b|×)|(\*|×|\bx)\s*0\.40?(?![\d])")` / `_LIVE_WORDS = re.compile(r"haircut|expected[ _]live|live[ _]sharpe|step[ _]?9|\bg9\b", re.I)`; :286-290 `for base in ("core", "docs", "ui"):`; core/quant/gate_stats.py:149 `LIVE_SHARPE_MULTIPLIER = 0.60`
     IMPACT: The D13 card column multiplies by LIVE_SHARPE_MULTIPLIER (spec 7.2). Use 0.60, or a local constant
     test-asserted equal to gate_stats', and never 0.4 on a line with live words.

## 3. T-CTX-01 (core/ficc/context_log.py; tests/macro_m6_context.py)

* [prefix now includes core.odds.] `ACTING_MODULE_PREFIXES` gained "core.compliance." and "core.odds." (trailing
  dot), so core.odds.* modules are acting and the package core.odds is not.
     EVIDENCE: core/ficc/context_log.py:71-73 `ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",` / `"core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",` / `"core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act`; :93-96 `return name.startswith(ACTING_MODULE_PREFIXES)`
     IMPACT: Every core/odds file is held to the acting rules below. (The earlier repo map's list, without these two
     prefixes, is out of date.)
* [what acting forbids] An acting module may not import a PROTECTED_MODULE, directly or through the transitive
  closure of repo-internal imports (core, data, config; function-level included). It also may not name a
  PROTECTED_CALLEE (as a Name or Attribute anywhere) or carry a string constant that contains a protected path
  fragment.
     EVIDENCE: core/ficc/context_log.py:78-81 `PROTECTED_MODULES = ("core.ficc.context_log", "core.ficc.macro", "core.quant.refusal", "core.ficc.flows_log")` / `PROTECTED_CALLEES = ("read_context_log", "load_break_log", "macro_sheet", "guarded_macro_sheet",` / `"refusal_krw_leg", "refusal_rates_leg")` / `PROTECTED_PATH_FRAGMENTS = ("context_log/", "r18_break_log", "r18_research_log")`; :195 `graph[name] = {i for i in imps if i.split(".")[0] in _REPO_TOPS}`; :211-222
     IMPACT: core/odds must not even use a local variable named `macro_sheet`. The transitive rule means that
     anything core/odds imports must itself stay clean.
* [the candidate imports are T-CTX-01-clean] A synthetic core.odds.plan was scanned against the real repo graph,
  importing in turn numpy, core.quant.garch, core.quant.strategies, data.crypto.crypto_client, data.krx.kis_client,
  yfinance, core.calendars.store, all of them together, and the full spec set (garch, strategies, validate,
  gate_stats, instruments, tf_books, gate_ledger, macro_artifacts, calendars store/clocks/regime, crypto_client,
  kis_client). Every scan gave `[]`, and the real report is `[]`.
     EVIDENCE: probe output `T-CTX-01 all together: []`, `T-CTX-01 spec set: []`, `T-CTX-01 current report: []` (scan via core/ficc/context_log.py:183 `def scan_isolation(sources: Mapping[str, str])`, repo graph :166-180 `repo_modules`)
     IMPACT: T-CTX-01 does not constrain the closure choice. It constrains only what core/odds names directly.
* [scan skips TYPE_CHECKING and `__main__` bodies] Imports under `if TYPE_CHECKING:` or `if __name__ == "__main__":`
  are invisible to T-CTX-01.
     EVIDENCE: core/ficc/context_log.py:116-124 `if isinstance(t, ast.Name) and t.id == "TYPE_CHECKING":` ... `return any(isinstance(c, ast.Constant) and c.value == "__main__" for c in t.comparators)`
     IMPACT: Annotations such as `CalendarSet` may be imported under TYPE_CHECKING (D14 skips these too, see below).
* [runtime guard is frame based] `assert_not_acting_caller` walks the stack and refuses when any frame's `__name__`
  is acting, so any core.odds frame on the stack makes the context readers raise ContextIsolationError.
     EVIDENCE: core/ficc/context_log.py:99-106 `while f is not None:` / `name = f.f_globals.get("__name__", "")` / `if is_acting_module(name):` / `raise ContextIsolationError(...)`
     IMPACT: odds must never call into the macro sheet or context log readers, even indirectly. Under
     `python -m core.odds.x` that module's `__name__` is "__main__" and not acting (the same gap the compliance CLIs
     have).
* [T-CTX-01 positive controls are fixed names] The test's controls use core.quant.risk, core.engine.books and
  core.calendars.x. No odds name is needed there, because compliance_guards already adds the core.odds.plan
  assertion.
     EVIDENCE: tests/macro_m6_context.py:181-199 `report = CL.static_isolation_report()` / `assert report == [], report` ... `ctl = CL.scan_isolation({"core.quant.risk": "from core.ficc import context_log\n"})`
     IMPACT: No change needed in macro_m6_context.py.

## 4. The D14 code-hash closure (core/compliance/owner.py; tools/signer/sign.py)

* [seeds already include core/odds/*.py, NON-recursively] The seeds are `core/compliance/*.py` and `core/odds/*.py`
  (top-level glob). Today core/odds has no .py file, so the current closure is 8 repo files plus 2 RECORD rows.
     EVIDENCE: core/compliance/owner.py:773 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`; :768-771 docstring `core/compliance/*.py and core/odds/*.py, every in-repo file they import at any depth, every ancestor package __init__.py, and the RECORD files of the cryptography and PyYAML installs`; probe `CURRENT code_files paths: ['core/__init__.py', 'core/compliance/__init__.py', 'core/compliance/alerts.py', 'core/compliance/gate.py', 'core/compliance/model.py', 'core/compliance/owner.py', 'core/compliance/rules.py', 'core/isolation.py', 'venv:PyYAML-6.0.3.dist-info/RECORD', 'venv:cryptography-49.0.0.dist-info/RECORD']`
     IMPACT: Every core/odds/*.py file the plan adds joins the signed closure automatically, and so does everything it
     imports. A file under a SUBfolder (core/odds/sub/x.py) is NOT seeded, and escapes D14 unless a seeded file
     imports it. The guards do scan it (rglob). Keep core/odds flat. The subfolder gap is a compliance follow-up item.
* [the closure follows in-repo imports at any depth, function bodies included] Only `if TYPE_CHECKING:` (bound by
  `from typing import TYPE_CHECKING` exactly once), `if typing.TYPE_CHECKING:` and a single
  `__name__ == "__main__"` comparison are skipped. Every ancestor `__init__.py` is added.
     EVIDENCE: core/compliance/owner.py:727-736 `"""Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""`; :708-724 `_skipped`; :781-782 `todo.extend(d / "__init__.py" for d in path.parents` / `if d != root and d.is_relative_to(root) and (d / "__init__.py").is_file())`
     IMPACT: A lazy `def f(): from data.crypto import crypto_client` still pulls the whole data layer into the
     signed closure. Laziness avoids import-time side effects only, not signing.
* [third-party imports are never followed or hashed, except two RECORD files] `_module_file` returns None for any
  name with no repo file, so numpy, scipy, yfinance, pandas, statsmodels, requests and curl_cffi are invisible. Only
  the RECORD files of cryptography and PyYAML are hashed.
     EVIDENCE: core/compliance/owner.py:739-747 `"""The repo file of an in-repo module name; None for stdlib, third-party and attribute names."""` ... `for candidate in (root.joinpath(*parts[:-1], parts[-1] + ".py"), root.joinpath(*parts, "__init__.py")):`; :603 `_RECORD_DISTS = ("cryptography", "PyYAML")        # their RECORD files stand for the installed packages (P6)`; :784-792; probe `== numpy: seeds=[] adds 0 repo files`, `== yfinance: seeds=[] adds 0 repo files`
     IMPACT: Importing numpy or yfinance from core/odds does not change the closure. A numpy, scipy or yfinance
     upgrade does NOT change the code hash, so it needs no re-sign and also goes undetected. Spec 6.4 accepts this
     ("edit the venv or .env. Both are outside the code hash"), and the report records the NumPy version (spec 7.5).
     Installed: numpy 2.3.5, scipy 1.18.0, yfinance 1.4.1, pandas 2.3.3, statsmodels 0.14.6, requests 2.34.2,
     curl_cffi 0.15.0, all with RECORD files. constraints.txt pins numpy==2.3.5 and scipy==1.18.0.
* [ANSWER: closure growth per candidate import (beyond today's 8 files)] Measured with owner's own `_repo_imports`
  and ancestor rule:
  - `import numpy` -> +0
  - `import yfinance` -> +0
  - `from core.quant import garch` -> +2 (core/quant/__init__.py, docstring only, 657 bytes; core/quant/garch.py, which imports only math, dataclasses, functools, numpy, scipy)
  - `from data.crypto import crypto_client` -> +20
  - `from data.krx import kis_client` -> +20 (the same 20: config.py, core/calendars/__init__.py, core/ficc/{__init__,common,data}.py, core/markets.py, core/quant/{__init__,history}.py, data/__init__.py, data/crypto/*, data/fmp/*, data/kis_markets.py, data/krx/{__init__,gateway,kis_client,krx_market_client,opendart_client}.py, data/net.py)
  - `from core.calendars import store` -> +34
  - `from core.quant import strategies` -> +46, which includes core/engine/{__init__,books,evaluator,orders,state}.py
  - all seven together -> +50
  - the full spec set named in spec 4/7 (adds validate, gate_stats, instruments, tf_books, gate_ledger, macro_artifacts, calendars clocks/regime) -> +55 files, 1,065,057 bytes, a 63-file closure
     EVIDENCE: probe lines `== core.quant.garch: ... adds 2 repo files: ['core/quant/__init__.py', 'core/quant/garch.py']`, `== core.quant.strategies: ... adds 46 repo files: [... 'core/engine/orders.py' ...]`, `== data.crypto: ... adds 20 repo files`, `== core.calendars.store: ... adds 34 repo files`, `ALL candidates together add 50 repo files`, `SPEC SET adds 55 files, 1065057 bytes`; core/quant/garch.py:60-68 `import math` ... `import numpy as np` / `from scipy import stats` ...; core/quant/__init__.py (docstring only)
     IMPACT: Only garch is cheap. Everything else drags in config.py, the network clients (data/net.py,
     kis_client, crypto_client, fmp, opendart) and, through strategies or tf_books or macro_artifacts, the engine
     including orders.py.
* [why the closure explodes: three hub edges] (1) core/quant/validate.py lazily imports core.quant.history and
  instruments. (2) core/quant/history.py imports config at module level and every data client lazily. (3) config.py
  lazily imports data.crypto.crypto_client and core.ficc.data. Also core/calendars/store.py lazily imports
  publication and core.rules.governance, which leads through macro_rules -> instruments -> validate. And
  risk_layer lazily imports core.engine.books, which reaches orders.py through core/engine/__init__.py.
     EVIDENCE: core/quant/validate.py:93-94 `from core.quant.history import _looks_crypto     # the same routing load_history uses` / `from core.quant.instruments import INSTRUMENTS   # instruments imports this module`; core/quant/history.py:44 `import config`, :199 `from data.krx.kis_client import KISClient`, :287 `from data.crypto.crypto_client import BinancePublic, CryptoError, UpbitPublic`; config.py:375 `from data.crypto.crypto_client import provider_status`, :397 `from core.ficc.data import fred_ready, yfinance_ready`; core/calendars/store.py:353 `from core.calendars import publication`, :457 `from core.rules.governance import append_event, read_events`; core/quant/risk_layer.py:551 `from core.engine import books as _books`; core/engine/__init__.py:4 `from core.engine.orders import OrderBook, OrderStatus, SimulatedOrder, order_id`; chain probe `core/quant/strategies.py -> core/quant/risk.py -> core/quant/risk_layer.py -> core/engine/__init__.py -> core/engine/orders.py`
     IMPACT: Anything that touches core.quant.validate (instruments.cost_per_side, gate_stats.pw_block,
     validate.walk_forward/score_strategy, tf_books, gate_ledger) costs about 22 or more files. The plan cannot pick
     "just one helper" from these modules without signing the data layer.
* [ANSWER: yes, the owner re-signs whenever any closure file changes] code_hash is sha256 over the canonical JSON of
  (path, sha256(bytes)) for every closure file. load_context recomputes it on every call and sets code_signed only
  if it equals the latest code_approved. The gate then refuses new exposure with "unsigned code" (exits are
  unaffected, D11).
     EVIDENCE: core/compliance/owner.py:783 `out = {p.relative_to(root).as_posix(): model.sha256_hex(p.read_bytes()) for p in seen}`; :796-798 `def code_hash(repo_root: Path) -> str:` / `return model.sha256_hex(model.canonical_json(code_files(repo_root)))`; :994 `current = code_hash(REPO_ROOT)`; :997 `signed = owner.ok and bool(current) and code_approval(check) == current`; core/compliance/gate.py:426 `return out + ([] if ctx.code_signed is True else ["unsigned code"])`
     IMPACT: Under the full-spec import set, any byte change in 63 files (config.py, data/net.py, kis_client.py,
     history.py, core/ficc/data.py, core/engine/*, core/rules/* ...) blocks new exposure until the owner signs again,
     and the signing prompt lists all 63 files. Under the small set, only core/compliance, core/odds, core/isolation.py
     and core/__init__.py (+2 for garch) matter.
* [cost per load_context] code_hash parses and hashes every closure file on each load_context call. Measured
  0.20 s for today's 10-entry closure and 0.85 s for the 63-file spec-set closure (hashing only, same machine).
     EVIDENCE: probe output `current code_hash s 0.2 files 10 | spec-set closure s 0.849 files 63`; core/compliance/owner.py:994
     IMPACT: Minor, but an odds comparison that calls load_context per plan would pay it each time. Build the Context
     once per comparison.
* [package re-exports via `__getattr__` escape the closure] core/calendars/__init__.py re-exports the v2 names
  lazily through `importlib.import_module(f"{__name__}.{module}")`. `from core.calendars import event_calendar` puts
  only core/calendars/__init__.py in the closure, and the real module (events.py) is never hashed. The spec-set
  closure lists adapter, clocks, publication, regime and store, but NOT events.py.
     EVIDENCE: core/calendars/__init__.py:208-218 `_V2_EXPORTS = {` ... `"events": ("Event", "load_events", "event_calendar", "release_status"),`; :224-229 `def __getattr__(name: str):` ... `return getattr(importlib.import_module(f"{__name__}.{module}"), name)`; core/compliance/owner.py:763-764 `names.update(f"{module}.{alias.name}" for alias in node.names)` / `return {f for name in names if (f := _module_file(root, name)) is not None}`
     IMPACT: If core/odds uses calendars, import from the concrete submodule (`from core.calendars.store import
     CalendarSet`, `from core.calendars.clocks import sessions_between`), never a package-level re-export. No guard
     catches this today (the dynamic-import ban scans only the core/odds source). Candidate guard for the follow-up
     plan.
* [TYPE_CHECKING imports stay out of the closure] An annotation-only import under `if TYPE_CHECKING:`, with
  `from typing import TYPE_CHECKING` bound exactly once, is skipped by D14 and by T-CTX-01.
     EVIDENCE: core/compliance/owner.py:699-705 `return imported and _binds(tree, "TYPE_CHECKING") == 1`; :716-717 `if isinstance(t, ast.Name):` / `return t.id == "TYPE_CHECKING" and bare_flag`
     IMPACT: core/odds can type `cal: CalendarSet` without signing the calendar stack, if the object is injected by
     the caller.
* [injected objects run unsigned code] D14 hashes what core/odds IMPORTS, not what it CALLS on objects passed in
  (for example `cal.sessions(...)` on a CalendarSet built by the caller).
     EVIDENCE: core/compliance/owner.py:750-764 `_repo_imports` reads only Import/ImportFrom nodes; spec 4 line 169 "`simulate()` takes `cal: CalendarSet`"
     IMPACT: Dependency injection keeps the closure small, but the injected code's integrity then rests on the data
     approvals (calendar signed approval, series md5s recorded in the report), not on the code hash. The plan must say
     so honestly (explain-guardrails rule).
* [tests that pin the SMALL closure would fail if odds imports in-repo modules] compliance_store asserts that the
  repo part of code_files EQUALS core/__init__.py + core/isolation.py + core/{compliance,odds}/*.py, that config.py
  and data/ are absent, and that the venv rows are exactly PyYAML + cryptography. compliance_signer asserts that
  config.py and data/ are absent.
     EVIDENCE: tests/compliance_store.py:137-140 `expected = {"core/__init__.py", "core/isolation.py"} | {` / `f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}` / `assert repo == expected, sorted(repo ^ expected)` / `assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)`; :150 `assert venv == {yaml_record, crypto_record}, venv`; tests/compliance_signer.py:638 `assert "config.py" not in paths and not any(p.startswith("data/") for p in paths), paths`
     IMPACT: Importing only numpy or yfinance -> both tests still pass. Importing core.quant.garch ->
     compliance_store:139 fails (+2 files). The plan must amend `expected` deliberately. Importing anything that
     reaches data/ or config.py -> both tests fail, and the plan must rewrite their intent ("never config.py or
     data/"), not just the sets.
* [the signer holds a byte-faithful copy of the closure code] tools/signer/sign.py duplicates `_RECORD_DISTS` and
  `code_files`, which seed core/odds the same way. A test asserts the two agree on the real tree and on a synthetic
  tree. Spec 6.4 says updating the owner's copy of the signer is an owner act.
     EVIDENCE: tools/signer/sign.py:596-601 `# The D14 code hash: a copy of owner.code_files (P6). core/compliance and core/odds .py files, ...` / `_RECORD_DISTS = ("cryptography", "PyYAML")`; :690-693 `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`; tests/compliance_signer.py:630-634 `mine = signer.code_files(ROOT)` / `theirs = [tuple(f) for f in owner.code_files(ROOT)]` / `assert mine == theirs`; spec 2026-10-23-...design.md:598-599 "The repo copy (`tools/signer/sign.py`, outside `core/`) is only a proposal. Updating the owner's copy is a deliberate owner act: read the diff, re-hash, re-record."
     IMPACT: Adding core/odds files needs NO signer change (both seed core/odds already). Changing the closure
     algorithm (for example adding numpy/scipy to `_RECORD_DISTS`, recursive seeds, or excluding files) needs both
     copies changed in lockstep, compliance_store:150 amended, and an owner act to re-verify the signer. Avoid it in
     the odds plan unless the owner rules for it.
* [design-doc contradiction to resolve] Spec 6.4 expects the closure to include "config.py ..., core/calendars/**,
  the core/quant and data/ modules they reach". Plan P6, the guard docstring and both closure tests assume it stays
  core/__init__.py + core/isolation.py + core/compliance (+ core/odds files).
     EVIDENCE: docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:584-587 `- their in-repo .py import closure, found by an AST import scan (for example config.py, core/isolation.py,` / `core/calendars/**, the core/quant and data/ modules they reach).`; docs/superpowers/plans/2026-10-23-compliance-gate.md:143-146 `Because of the import allowlist, the closure is core/__init__.py, core/isolation.py,` / `core/compliance/*.py (plus core/odds/*.py later). The data loaders A0 edits are NOT in it.`; tests/compliance_guards.py:306-308 `so the D14 signed closure stays core/__init__.py, core/isolation.py and core/compliance (P6)`
     IMPACT: The odds plan must pick one, record it as an odds-plan decision, and amend whichever side loses.
* [import-time side effects of the data clients] Importing config runs `load_dotenv()`, which loads the shared .env
  keys into os.environ. Importing data.krx.kis_client calls `config.state_root()` at module level, which runs the
  state-root link scan.
     EVIDENCE: config.py:26-30 `try:` / `from dotenv import load_dotenv` / `load_dotenv()`; data/krx/kis_client.py:53 `_TOKEN_PATH = config.state_root() / "kis_token.json"`
     IMPACT: If bars.py imports data clients at module level, importing core.odds.bars loads the .env keys and
     touches the state root. Import them lazily inside the seam functions, or keep them out of core/odds.
* [the data clients read the wall clock themselves] UpbitPublic paging uses `datetime.now(timezone.utc)`, the KIS
  daily range defaults use naive `datetime.now()`, and history uses `date.today()`/`time.time()`.
     EVIDENCE: data/crypto/crypto_client.py:232 `end = datetime.now(timezone.utc)`; data/krx/kis_client.py:277-278 `end = end or datetime.now().strftime("%Y%m%d")` / `start = start or (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")`; core/quant/history.py:131 `start = (date.today() - timedelta(days=int(days * 1.6) + 10)).isoformat()`
     IMPACT: Even a clock-clean core/odds reads the clock through these clients. Pass explicit `end`/`start` and
     `now`, and record retrieval time as data.
* [hermetic touchpoints are a fixed list] `hermetic()` patches named seams in the existing clients plus
  socket.connect. A new seam in core/odds/bars.py (for example `bars._yf_download`) is not patched unless the odds
  plan adds it. yfinance uses curl_cffi, which bypasses the socket patch (spec 4).
     EVIDENCE: tests/macro_acceptance.py:52-71 `def _touchpoints()` ... `(ficc_data, "_yf_fetch", _boom),` ... `(socket.socket, "connect", _refuse_connect),`; spec design.md:166-168 "Every network call goes through a module-level seam (for example `bars._yf_download`), which the test suites patch, because yfinance uses curl_cffi and bypasses a socket patch."
     IMPACT: The odds plan adds each bars seam to `_touchpoints` (or to the odds aggregator's wrapper), plus a
     positive control showing that an unpatched call raises.

## 5. Options for the key design question (what core/odds may import)

* [Option A, spec as written: import directly] core/odds/bars.py imports data.crypto.crypto_client,
  data.krx.kis_client and yfinance. models.py imports core.quant.garch, strategies and validate (D13 steps), plus
  gate_stats (pw_block). Costs come from instruments.cost_per_side, bands from regime_tags, provenance from
  gate_ledger.repo_anchor and macro_artifacts.tree_hash.
     EVIDENCE: spec design.md:161-165 `KRX from KIS daily rows;` / `Upbit KRW-* and Binance *USDT from data.crypto Candles;` / `US from yfinance.`; :738 `It fits with garch.fit_garch and simulates with simulate_returns(...)`; :765-769 `strategies.pnl_matrix(...)` / `validate.walk_forward(...)` / `validate.score_strategy(...)`; :176 `instruments.cost_per_side(book, price=fill_price, on=fill_date, side=side).bp`; :157 `regime_tags("KR", d)["price_limit"]`; :185-186 `gate_ledger.repo_anchor()` / `macro_artifacts.tree_hash()`; probe `SPEC SET adds 55 files`
     IMPACT: All guards pass. The closure becomes 63 files including config.py, the network clients and
     core/engine/orders.py. The owner re-signs on any change to any of them. compliance_store:137-150 and
     compliance_signer:638 must be rewritten, and P6 plus the guard docstring amended. This matches spec 6.4's text.
* [Option B, small signed core with injected inputs] core/odds imports only stdlib, numpy, scipy (and optionally
  core.quant.garch, +2 files), core.isolation and core.compliance. Bars, CalendarSet, cost tables, price limits and
  provenance strings are produced by a caller outside core/odds and passed in, with their hashes recorded in the
  report. The repo constants are copied locally, each with an equality test (LIMIT_DOWN_CARRY_COST_MULTIPLIER is
  the precedent; DELIST_STRESS=(0.30, 1.00) and LIVE_SHARPE_MULTIPLIER=0.60 the same way).
     EVIDENCE: spec design.md:160 "`LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` is declared locally, and a test asserts it equals the orders constant."; core/quant/tf_books.py:36 `DELIST_STRESS = (0.30, 1.00)`; core/quant/gate_stats.py:149 `LIVE_SHARPE_MULTIPLIER = 0.60`; spec :780 "Series hashes are md5 of canonical JSON {symbol, source, dates, open, close, adjustment, status}."
     IMPACT: The closure stays 8 + core/odds files (+2 with garch), the existing closure tests keep their intent, and
     the allowlist guard can be widened to core/odds. Two spec items then move or need a ruling: bars.py "on the data
     clients" (spec 4 lists it under core/odds), and the D13 replay's direct calls to strategies and validate (spec 7.2),
     which reach the data layer.
* [Option C, hybrid] Option B for plan, simulate, bold and report. models.py keeps `core.quant.garch` (+2 files, no
  data layer). bars.py moves outside core/odds (for example a data-side loader that core/odds never imports), and the
  D13 replay runs in a caller module outside core/odds that hands its digests and returns in.
     EVIDENCE: probe `== core.quant.garch: ... adds 2 repo files`; chain probe `core/quant/strategies.py -> core/quant/history.py -> data/krx/kis_client.py`
     IMPACT: The smallest deviation from the spec that keeps the signed set reviewable. compliance_store:137-139 gains
     the two quant files. Needs a spec ruling on the file location for bars and the replay.
* [non-options] Lazy imports do not shrink the closure: function bodies are scanned (owner.py:727-736). Dynamic
  imports are banned in core/odds (compliance_guards.py:300-302). A core/odds subfolder escapes the D14 seeds
  (owner.py:773), but using that on purpose would defeat D14. Do not.
     EVIDENCE: core/compliance/owner.py:773 `.glob("*.py")`; tests/compliance_guards.py:300 `_scope(COMPLIANCE, ODDS)` with `_dynamic_hits`
     IMPACT: The plan must state the chosen option and the per-file allowlist explicitly.

## 6. Parked guard items (for the compliance follow-up plan)

* [parked: xml.dom and profile/pdb/bdb/trace not banned] The final review parked them as "a small guards follow-up".
  DYNAMIC_MODULES lacks profile, pdb, bdb and trace. xml.dom.minidom is explicitly allowed (negative control).
     EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:242 `Final: parked — xml.dom (incl. xml.dom.xmlbuilder DOMBuilder.parseURI / DOMEntityResolver) and profile/pdb/bdb/trace are not in the import bans`; tests/compliance_guards.py:50-51 `DYNAMIC_MODULES = (... "pydoc", "timeit",` / `"code", "cProfile")`; :332-333 `assert not _allowlist_hits(X, ... "from xml.etree import ElementTree\nfrom xml.dom import minidom\n")`
     IMPACT: The follow-up adds xml.dom.xmlbuilder (or all of xml.dom except minidom?) to NETWORK_MODULES, and
     profile, pdb, bdb and trace to DYNAMIC_MODULES, each with a positive control. It must then fix the minidom
     negative control (minidom imports xmlbuilder).
* [deferred: clock guard misses time.sleep and clock_gettime; alias or getattr bypasses]
     EVIDENCE: execution-ledger.md:64 `Task 1: minor (deferred): _clock_hits flags `from time import sleep` but not time.sleep; clock_gettime absent; alias/getattr bypasses pass`; tests/compliance_guards.py:54-56 `"time": {"time", "time_ns", "monotonic", ... "thread_time_ns"}}` (no clock_gettime)
     IMPACT: Add clock_gettime/clock_gettime_ns to CLOCKS["time"]. Decide whether sleep counts.
* [deferred: `__main__` block check misses the reversed comparison] `_main_block_hits` matches only the exact
  unparse `__name__ == '__main__'`, while owner `_skipped` accepts either order.
     EVIDENCE: execution-ledger.md:70 `_main_block_hits misses reversed `"__main__" == __name__``; tests/compliance_guards.py:213 `if isinstance(n, ast.If) and ast.unparse(n.test) == "__name__ == '__main__'"`; core/compliance/owner.py:720-723 `sides = [t.left, *t.comparators]`
     IMPACT: Accept both orders, with a positive control.
* [deferred: rebound guard names escape the closure scan] `typing = SimpleNamespace(TYPE_CHECKING=True)` or
  `__name__ = "__main__"` makes an import look skipped. The proposed one-line hardening must be mirrored in the signer.
     EVIDENCE: execution-ledger.md:208 `a rebound guard name escapes the closure scan (...); one-line hardening: require _binds(tree,"typing")==1 / _binds(tree,"__name__")==0 — Task 15's signer copy must match`; core/compliance/owner.py:718-719 `if isinstance(t, ast.Attribute):` / `return t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"`
     IMPACT: Any change to `_skipped` changes owner.py AND tools/signer/sign.py, an owner act for the off-PC signer
     copy. Batch it with any other closure-algorithm change (recursive seeds, package `__getattr__`).
* [deferred: compile() and other exec routes uncovered]
     EVIDENCE: execution-ledger.md:75 `uncovered fetch/exec routes: xml.dom.xmlbuilder DOMEntityResolver, pydoc.locate, timeit/code/cProfile string execution, compile (covered only by the "not a proof" disclaimer)`; tests/compliance_guards.py:49 DYNAMIC_NAMES has no "compile"
     IMPACT: pydoc, timeit, code and cProfile were added in the final wave. compile is still open. Add "compile" to
     DYNAMIC_NAMES (re.compile is an Attribute named compile and would then hit, so the check needs care: ban only
     the bare Name `compile`).
* [deferred: brittle registration literal] It is also the hazard named in section 1.
     EVIDENCE: execution-ledger.md:69 `registration test asserts the literal "paper, grokteam or compliance" (brittle; plan-mandated)`
     IMPACT: The follow-up or the odds plan should replace it with a check that `select(..., suite="compliance")`
     finds entries and that the help text lists every suite.
* [new gap found here: D14 seeds are non-recursive] A .py file in a subfolder of core/compliance or core/odds is
  scanned by the guards but is not seeded into the signed closure.
     EVIDENCE: core/compliance/owner.py:773 and tools/signer/sign.py:693 `sorted((root / "core" / sub).glob("*.py"))`; tests/compliance_guards.py:69 `base.rglob("*.py")`
     IMPACT: Either seed with rglob (in both copies, which is an owner act) or add a guard that core/compliance and
     core/odds hold no .py below the top level. The guard is cheaper and needs no signer change.
* [new gap found here: package `__getattr__` re-exports escape D14] See section 4.
     EVIDENCE: core/calendars/__init__.py:224-229
     IMPACT: Candidate guard: core/compliance and core/odds may not import a name from a package whose `__init__`
     defines `__getattr__`. Or document it as a limit.

## Open questions

- Which option (A full closure / B injected inputs / C hybrid) does the owner want? Spec 6.4 text (design.md:584-587)
  supports A. Plan P6, guard docstring compliance_guards.py:306-308 and tests compliance_store.py:130-150 /
  compliance_signer.py:638 assume the closure stays small. Under A, any edit to config.py, the data clients or the
  engine blocks new exposure until a re-sign.
- Under B or C, may the D13 replay call core.quant.strategies/validate from a module OUTSIDE core/odds, and may bars.py
  live outside core/odds? Spec 4 lists both bars.py and the replay under core/odds (design.md:136-138).
- Should the allowlist, wall-clock, HTTP-verb and `__main__` guards be widened to core/odds? If so, with what per-file
  allowlist (numpy everywhere? scipy and core.quant.garch only in models.py? network only in bars.py, or nowhere)?
  Note the np.delete/np.put hit under the HTTP guard.
- Should numpy and scipy RECORD files join `_RECORD_DISTS`? That would make a numpy upgrade need a re-sign. It needs
  owner.py + tools/signer/sign.py in lockstep, compliance_store.py:150, and an owner act to re-verify the signer.
  Spec 6.4 currently accepts the venv as outside the code hash.
- Create an empty `core/odds/__init__.py`, or leave core.odds a namespace package? Both pass the guards. Not verified:
  whether any other tool (UI imports, the run_all collector) assumes a regular package.
- Is `python -m core.odds.<x>` (where `__name__` is "__main__", so the T-CTX-01 runtime guard sees it as non-acting) a
  concern worth a guard, or accepted as it is for the compliance CLIs?
- If odds needs calendar functions, does the plan accept that injected CalendarSet methods run unsigned code (integrity
  then rests on the signed calendar approval), or must core/odds import core.calendars.clocks/store (+34 files)?
- Follow-up scope: are the two new gaps here (non-recursive D14 seeds; package `__getattr__` re-exports) in the
  compliance follow-up plan or the odds plan? The `_skipped` rebinding fix and recursive seeds both touch the signer
  (owner act). A "no subfolders" guard does not.
