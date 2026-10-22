# QUANTGEN v2 integration map: code_tests_data

Subsystem: the test harness (`tests/`), the architecture review (`docs/ARCHITECTURE_REVIEW.md`), and the local data that can back spec tests.
Mapped 2026-10-05 on Windows 11, Python 3.13.14, flet 0.85.2, numpy 2.3.5, pandas 2.3.3, scipy 1.18.0, matplotlib 3.11.0.
Baseline at mapping time: `qa/acceptance_results.json` written 2026-10-05 23:32 local, **266/266 PASS**, 155.2 s total
(cockpit 47 tests / 12.5 s, engine 89 / 2.4 s, ui 4 / 1.1 s, quant 53 / 70.1 s, ficc 56 / 3.9 s, expansion 17 / 65.3 s).
Line numbers are `file:line` in the repository as mapped. "Spec" = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`.
Inside tables a pipe that belongs to code is written `\|` (read it as `|`).

Contents: A file-by-file, B cross-file flows, C existing tests and registration, DI data inventory, D extension points, E gotchas, F ambiguities.

---

## A. File-by-file

### A.1 `tests/run_all.py` (70 lines): the only runner

| Item | Verbatim | Line |
|---|---|---|
| Root on path | `ROOT = Path(__file__).resolve().parents[1]`; `sys.path.insert(0, str(ROOT))` | 21-22 |
| cp949 guard | `for stream in (sys.stdout, sys.stderr): stream.reconfigure(encoding="utf-8", errors="replace")` inside `try/except Exception: pass` | 24-28 |
| Suite imports (import time, all six) | `from tests.acceptance import tests as cockpit_tests`, `tests.engine_acceptance -> engine_tests`, `tests.flet_api_guard -> ui_tests`, `tests.quant_acceptance -> quant_tests`, `tests.ficc_acceptance -> ficc_tests`, `tests.expansion_acceptance -> expansion_tests` | 30-35 |
| Registry | `def tests()` returns one list of `(f"<prefix>/{n}", f)`; prefixes in this order: `cockpit/`, `engine/`, `ui/`, `quant/`, `ficc/`, `expansion/` | 38-44 |
| Loop | for each `(name, fn)`: `fn()` with no arguments; `except Exception as exc` gives `status="FAIL"`, `detail=f"{type(exc).__name__}: {exc}"`, `traceback.print_exc()`; prints `f"{status} {name} {detail}".rstrip()` | 47-62 |
| Result row | `{"test": name, "status": "PASS"\|"FAIL", "seconds": round(perf_counter delta, 4), "detail": str}` | 56-61 |
| Output | `out = ROOT / "qa" / "acceptance_results.json"`; `out.parent.mkdir(parents=True, exist_ok=True)`; `json.dumps(results, indent=2, ensure_ascii=False)`, `encoding="utf-8"` (overwritten on every run) | 64-66 |
| Exit | prints `f"\n{passed}/{len(results)} passed; {out}"`; `raise SystemExit(0 if passed == len(results) else 1)` | 68-70 |

Behaviour that matters:
- The script body runs at import (no `main()`, no `if __name__`): importing `tests.run_all` runs the whole suite.
- No CLI arguments, no filter, no tiers, no timing budget, no per-test timeout.
- A test contract is: a zero-argument callable that raises on failure. No fixtures, no setup/teardown hooks, no pytest (pytest 8.4.2 is installed but unused; there is no `conftest.py`).
- An exception at import of any suite aborts the run before any test runs and before the JSON is written.
- Only `Exception` is caught: `SystemExit` or `KeyboardInterrupt` raised inside a test kills the runner without results.
- `tests/__init__.py` is one line: `"""NEXTGEN verification suite."""` (so `tests` is a package; `python -m tests.<suite>` works from ROOT).

### A.2 `tests/acceptance.py` (958 lines): "cockpit" suite, 47 tests

Purpose: the inherited NEXTGEN skill cockpit (catalogue, safety, regressions, execution, arguments, diagnosis, decision gates). It is also where the repository-wide static safety scans live.

Helpers (reuse these, do not rewrite them):

| Helper | Signature and behaviour | Line |
|---|---|---|
| `ROOT` | `Path(__file__).resolve().parents[1]` | 24 |
| `_read(path: Path) -> str` | `path.read_text(encoding="utf-8")` | 27-28 |
| `_code_only(path: Path) -> str` | `ast.parse`, strips docstrings of Module/ClassDef/FunctionDef/AsyncFunctionDef, returns `ast.unparse(tree)` (comments and docstrings gone) | 31-45 |
| `runtime_py() -> list[Path]` | every `*.py` under `ROOT/core`, `ROOT/data`, `ROOT/ui` (`rglob`, `__pycache__` skipped) plus `ROOT/main.py`, `ROOT/config.py` | 48-54 |
| `tests()` | `sorted((n, v) for n, v in globals().items() if n.startswith("test_") and callable(v))` | 956-958 |

Static scans that apply automatically to every new file under `core/`, `data/`, `ui/` (v2 code must pass them unchanged):

| Test | Scan | Forbidden content | Line |
|---|---|---|---|
| `test_08_no_broker_order_path` | raw text of `runtime_py()`, lower-cased (comments and docstrings INCLUDED) | `"order_cash"`, `"order-cash"`, `"place_order"`, `"submit_order"`, `"TTTC0802U"`, `"TTTC0801U"`, `"VTTC0802U"` | 169-175 |
| `test_09_no_account_credentials_requested` | raw text, case-sensitive | `"KIS_ACCOUNT"`, `"CANO"`, `"ACNT_PRDT_CD"` | 178-182 |
| `test_16_every_source_file_is_utf8_readable` | `runtime_py()` + `tests/acceptance.py` + `tests/run_all.py` decode as UTF-8 | any non-UTF-8 byte | 247-253 |
| `test_17_tests_never_read_without_an_encoding` | `_code_only` of `acceptance.py` and `run_all.py` only | regex `read_text\(\s*\)` | 256-262 |
| `test_18_eodhd_is_gone_from_the_runtime` | `_code_only` of `runtime_py()`, lower-cased | `"eodhd"`, `"quartr"` | 265-270 |
| `test_13_settings_page_shows_presence_not_values` | raw `ui/settings_page.py` | `"kis_credentials()"`, `"opendart_key()"`, `"_clean("` | 217-222 |
| `test_14_page_resize_handler_matches_the_flet_api` | `hasattr(ft.Page, "on_resize")`; `_code_only(main.py)` matches `page\.on_resize\s*=` and not `page\.on_resiz(ed\|e_d)\s*=` | - | 228-238 |
| `test_15_views_are_cached_across_navigation` | raw `main.py` contains `"cache"` and the literal `"cache[name] = build("` | - | 241-244 |
| `test_32_workflow_steps_are_never_launched_with_an_empty_command_line` | AST of `ui/*.py`: no `<x>.run_skill(a, ())` or `(a, [])` | - | 520-543 |
| `test_42_the_gate_reads_its_answers_rather_than_hard_coding_them` | AST of `ui/workflows_page.py`: a `show_gate` function that calls `options_for` and `_digest` | - | 799-815 |

The other cockpit tests (catalogue 01-07b, redaction 10-12, runner 19-20, KRX gateway 21-22, arguments 23-28, diagnosis 29-31 and 43-46, decision gates 33-37, insights 38-39, wiring 40-41 and 45) exercise `core/skills/*` against the EXTERNAL trading-skills repository at `config.skills_root()`; see E.3 and E.4 for what that implies.

Environment handling pattern used here (tests 07b, 10, 20; test 07 only pops and restores two env vars): save `os.environ[...]`, mutate, `importlib.reload(config)`, assert, restore in `finally`, reload again. `test_07b` documents why a key is blanked (`os.environ["FMP_API_KEY"] = ""`) instead of popped: `config` calls `load_dotenv()` at import, so a popped variable is re-read from `.env` on reload (139-143).

### A.3 `tests/engine_acceptance.py` (1398 lines): "engine" suite, 89 tests (not in the assigned read list; skimmed for structure)

- Imports: `from core.engine import (EngineMode, EngineState, Evaluator, HaltReason, OrderBook, OrderStatus, Outcome, Quote)`; `from core.rules import (CancelCondition, Comparator, Limits, OrderKind, PriceCondition, Rule, RuleStatus, Side, SizeMode, validate)` (13-17).
- Fixtures: `NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)` (19); `TRADING_NOW = datetime(2026, 8, 19, 2, 0, tzinfo=timezone.utc)` (313; 11:00 KST Wednesday); `KST = timezone(timedelta(hours=9))` (685).
- `_rule(**over) -> Rule` (22-32): defaults `name="test rule", symbol="005930", market="KRX", side=Side.BUY, size_mode=SizeMode.QUANTITY, size_value=Decimal(10), order_kind=OrderKind.MARKET, conditions=(PriceCondition(Comparator.AT_OR_BELOW, Decimal(70000)),), limits=Limits(max_triggers=3, max_order_amount=Decimal(10_000_000)), status=RuleStatus.ACTIVE`.
- `_quote(price=68000, previous=None, age_s=0) -> Quote` builds `Quote("005930", Decimal(price), Decimal(previous)|None, NOW - timedelta(seconds=age_s), "test")` (35-38).
- `_armed() -> tuple[EngineState, OrderBook, Evaluator]` (41-45).
- `_runtime(tmp, price=68000)` (316-341): `RuleStore(tmp / "rules.json")`, `EngineRuntime(store, QuoteFeed(_Gateway()), tick_seconds=999, state_path=tmp / "engine.json", clock=lambda: TRADING_NOW)`; `_tmpdir()` = `Path(tempfile.mkdtemp())` (344-347). This is the existing "temporary copy of the rules store" pattern.
- `_FakeFMP(rows=None, error=None, blocked=None)` with `.ready`, `.status()`, `.error_for(symbol)`, `.plan_blocked()`, `.quotes(symbols)`, `.calls` (527-551); `_fmp_row(symbol, price, *, as_of=None) -> data.fmp.FMPQuote` (554-560); `_flaky_runtime(tmp, outcomes, grace)` (975).
- `tests()` = `sorted(... startswith("test_") ...)` (1396-1398). Numbering 01-91 with 63 and 64 absent.
- Engine states and halt behaviour asserted here (binding for the v2 engine hooks): `EngineState().mode is EngineMode.DISARMED` at start (51-52); `halt()` then `arm()` returns `(False, message)` with `"Acknowledge"` in the message until `acknowledge()`, and acknowledging leaves `DISARMED` (55-65); `snapshot()` must not contain `"mode"` (68-75); an unacknowledged halt survives `restore()` via `requires_manual_rearm` (78-86); `halt()` is idempotent from any state (89-96); a stale quote gives `Outcome.HALTED` with `HaltReason.STALE_DATA`, a missing quote `HaltReason.NO_DATA` (110-122). `HaltReason` members seen: `STALE_DATA`, `LIMIT_BREACH`, `OPERATOR`, `NO_DATA`. `Outcome` members seen: `SKIPPED`, `HALTED`, `REJECTED` and a fired decision (`decision.fired`).
- Calendar tests 67-76 (878-973): `core.calendars.coverage("US")`, `is_trading_day(market, day) -> Optional[bool]` (None beyond coverage, test 71), `stale_markets()` rows with `"market"`, `"expired"` (test 73), `cal.source` keys `library == "exchange_calendars"`, `calendar`, `generated` (test 74), 20,000 lookups under 1.0 s (test 75).
- HTTP session tests 81-82 (1079-1167): `data.net.session` is the object bound as `_requests` in `core.ficc.data`, `core.quant.history`, `data.crypto.crypto_client`, `data.kis_markets`, and as `requests` in `data.krx.kis_client`, `data.krx.opendart_client`; the quote path (`data.fmp.quote_client._requests`, `data.krx.krx_market_client.requests`, `data.krx.kis_client._once`) is plain `requests`. `retry.total == 2`, `allowed_methods == {"GET"}`, `status_forcelist == {502, 503, 504}`, `respect_retry_after_header is False`. Test 82 starts a real `HTTPServer(("127.0.0.1", 0), ...)` on loopback.
- KIS pacing test 89 (1333-1393): patches `kis.time`, `kis.requests`, `kis._once`, `kis._last_call[0]`, `config.kis_credentials`; asserts `kis._MIN_GAP_S` spacing and one retry on `msg_cd == "EGW00201"`.

### A.4 `tests/flet_api_guard.py` (174 lines): "ui" suite, 4 tests

| Item | Verbatim | Line |
|---|---|---|
| Scope | `UI = Path(__file__).resolve().parents[1] / "ui"`; `_ui_files()` = `sorted(UI.glob("*.py"))` (top level only, not recursive) | 26, 39-40 |
| `_CHECKED_CONTROLS` | `"Dropdown", "TextField", "Button", "IconButton", "Text", "Container", "Row", "Column", "ResponsiveRow", "AlertDialog", "SnackBar", "Icon", "Divider", "VerticalDivider", "AnimatedSwitcher", "Image", "Checkbox", "ExpansionTile", "ProgressRing", "ProgressBar", "FilePicker", "ListTile", "Switch", "Slider", "Card", "Stack", "Tabs", "Tab", "Badge", "Tooltip"` | 30-36 |
| `_params(control_name) -> set[str] \| None` | `inspect.signature(getattr(ft, name).__init__).parameters` | 43-50 |
| `test_page_methods_exist` | every call `page.<attr>(...)` whose receiver is the bare name `page` must be in `dir(ft.Page)` (non-underscore) | 53-68 |
| `test_control_keywords_exist` | every keyword of `ft.<Control>(...)` for a checked control must be an `__init__` parameter (`**kwargs` splats skipped) | 71-95 |
| `test_control_attribute_assignments_exist` | for names assigned exactly once from `ft.<X>(...)`: `name.attr = ...` must be an `__init__` parameter or a class attribute | 98-149 |
| `test_theme_tokens_referenced_by_ui_exist` | every `pal.<attr>` must be in `core.theme.token_names()` | 152-169 |

Known Flet 0.85 facts encoded in the docstring (5-7, 101-105): `ft.Dropdown(on_select=...)` not `on_change`; `page.show_dialog(dialog)` not `page.open`; `page.pop_dialog()` not `page.close`; `TextField.helper` not `helper_text`.
`core/theme.py:11-23` `Palette` fields (the only legal `pal.` tokens): `bg, surface, surface_2, border, text, muted, accent, accent_soft, success, error, on_accent`. `DARK` and `LIGHT` are built POSITIONALLY (theme.py:25-26).

### A.5 `tests/quant_acceptance.py` (1003 lines): "quant" suite, 53 tests

Module docstring rule (1-11): hermetic by construction; synthetic series only; credential readers patched to a known state before anything that could reach a network.

Helpers:

| Helper | Signature and behaviour | Line |
|---|---|---|
| `_no_credentials()` | `@contextlib.contextmanager`; saves and replaces `config.fmp_ready = lambda: False`, `config.fmp_key = lambda: ""`, `config.kis_ready = lambda: False`, `config.anthropic_key = lambda: ""`; restores in `finally`. `fmp_key` is patched too because `fmp_history` reads the key, not the readiness flag (38-40) | 34-50 |
| `_trend_history(slope, *, days=300, noise=0.001, seed=3) -> History` | log-linear trend, `symbol="TREND"`, `source="SYNTHETIC"`; dates `f"2025-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}"`: fake 28-day months, unique and ascending only while `days <= 336`, duplicates beyond (the look-ahead test at 488 uses `f"2025-01-{i % 28 + 1:02d}"` for 100 days, which already repeats) | 53-59 |
| `_basket()` | `align_histories([synthetic_history(s) for s in ("AAPL", "MSFT", "NVDA", "TLT")])` | 402-404 |
| `_TRUE` | `dict(omega=2e-6, alpha=0.08, beta=0.90, nu=6.0)` | 578 |
| `_garch_history(*, n=1500, seed=11, drift=0.0) -> History` | `simulate_garch_series(...) + drift`, daily calendar dates from `date(2020, 1, 1)` | 581-589 |
| `tests()` | `[(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]` | 1001-1003 |

Patch points used (the complete list of what quant tests replace):
- `config.fmp_ready`, `config.fmp_key`, `config.kis_ready`, `config.anthropic_key` (34-50); `config.FICC_CACHE_TTL_SECONDS` (120, 131); `os.environ["NEXTGEN_FICC_CACHE"] = tempfile.mkdtemp()` (121).
- `core.quant.history.fmp_history` (115), `H._may_be_trading` (117, 137, 167), `H._CACHE_LIVE_TTL` (138, 142), `H._requests` replaced by a fake with `.get(url, **kwargs)` returning an object with `.status_code` and `.json()` (197-217).
- `core.ficc.data._yf_fetch = lambda tickers, period: {tickers[0]: list(rows)}` (287), `data.krx.kis_client.KISClient = _FakeKIS` with `.daily(code, **kwargs)` (282-288).

Constants asserted (binding names and values): `MODELS == ("garch_t", "gbm", "jump", "bootstrap")` (359); `DRIFTS == ("premium", "zero", "rf", "sample")` (742); `rep.engine in ("gs_quant", "local")` (378); `LR_5PCT` = 2.706 and the band `(2.706, 3.841]` (916); `BOUNDS`, `STATIONARITY_MAX`, `NU_NORMAL`, `Z95`, `Z_BOUND` imported from `core.quant.garch` (25-27). Source values, `core/quant/garch.py:70-94`: `TRADING_DAYS = 252`, `Z_BOUND = 22`, `BOUNDS = {"omega": (1e-12, inf), "alpha": (0.0, 0.5), "beta": (0.0, 0.999), "eta": (0.0, 0.4), "nu": (2.5, inf)}`, `STATIONARITY_MAX = 0.9995`, `LR_5PCT = 2.706`, `NU_NORMAL = 100.0`, `Z95 = 1.959964`, `_MIN_OBS = 100`.

Cache file contract asserted (100-191): file name `HIST_FMP_TSLA_120.json` under the cache dir; JSON keys `ts`, `live`, `symbol`, `source`, `note`, `adjustment`, `dates`, `closes`; a hit appends `"cached <stamp>"` to `note`; `live is False` is required for the full TTL; a file without `live` older than `_CACHE_LIVE_TTL` (600.0 s) is refetched; TTL 0 disables; a missing key bypasses the cache and raises `HistoryError`.

### A.6 `tests/ficc_acceptance.py` (781 lines): "ficc" suite, 56 tests

| Helper | Signature and behaviour | Line |
|---|---|---|
| `_no_network()` | `@contextlib.contextmanager`; `_boom(*_a, **_k)` raises `FICCError("offline (acceptance suite)")`; replaces `data._fred_fetch = data._yf_fetch = _boom` and sets `config.FICC_CACHE_TTL_SECONDS = 0.0`; restores all three in `finally` | 30-41 |
| `_raises(fn, exc=FICCError)` | passes iff `fn()` raises `exc`; else `AssertionError(f"expected {exc.__name__}")` | 44-49 |
| `_PAR`, `_UP` | 11 par yields each (decimals) on `UST_TENORS` | 52-53 |
| `_BOND` | `bonds.Bond(coupon=0.05, maturity=10.0, name="5% 10y")` | 54 |
| `_curve()`, `_up_curve()` | `curves.bootstrap_par_curve(UST_TENORS, _PAR\|_UP, date="2026-09-04", source="TEST")`, `@functools.lru_cache(maxsize=None)` | 57-64 |
| `_panel()`, `_report()` | `data.synthetic_curve_panel(days=200)`, `curves.analyze_curve(_panel())` (cached) | 67-74 |
| `_carry_inputs()` | spots `{pair: data.synthetic_fx(pair, days=300)}`, rates `{ccy: data.synthetic_series(f"RATE_{c}", days=300, kind="rate")}` over `data.G10_KRW` | 77-83 |
| `_sheet()` | `macro.macro_sheet(source="synthetic", days=300)` (cached) | 86-88 |
| `_ppn()` | `structured.principal_protected_note(_up_curve(), spot=1.10, vol=0.08, r_for_or_div=0.02, maturity=3.0)` | 91-94 |
| `_sofr()` | `data.load_short_rate("USD", source="synthetic", days=756)` | 469-471 |
| `_clean(text) -> str` | asserts `"None" not in text and "nan" not in text.split() and len(text) > 80` | 608-610 |
| `tests()` | same `sorted(globals().items())` form as quant | 761-763 |
| `__main__` | prints `PASS name (s)` / `FAIL name`, exits 1 on failure. Runs only as `python -m tests.ficc_acceptance` from ROOT (`python tests/ficc_acceptance.py` fails: `ModuleNotFoundError: No module named 'config'`, verified) | 766-781 |

Degradation contract asserted (126-150, 545-551): under `_no_network()`, `data.load_series("DGS10", days=100)` returns `source == "SYNTHETIC"` with `"FRED failed"` and `"offline"` in `note`; `data.load_fx_spot("USDKRW")` returns SYNTHETIC with `"YFINANCE failed"` in `note` and `label == "USD/KRW"`; `load_treasury_curve()`, `load_short_rate("USD")`, `load_many([...])` likewise; every explicit provider (`source="fred"`, `"yfinance"`) and an unknown source (`"bloomberg"`) raise `FICCError`; `data.probe()` returns `{"fred": {"ok": False, ...}, "yfinance": {"ok": False, ...}}`; `macro.macro_sheet(days=300)` gives `sources == {"SYNTHETIC": 18}`, `len(synthetic_ids) == 18`, `"18/18" in note`; `macro.macro_sheet(source="fred", days=300)` raises `FICCError`; `macro.macro_sheet(days=10)` raises `ValueError`. Synthetic results never enter `data._MEM` (111-123).

Enumerations asserted: curve `shape in ("normal", "flat", "inverted", "humped")` (208); `rep.regime in macro.CURVE_REGIMES`; `macro.RISK_REGIMES = ("risk-on", "risk-off", "neutral")`, `macro.DOLLAR_REGIMES = ("strong", "weak", "range")`, `macro.TREND_REGIMES = ("rising", "falling", "stable")` (core/ficc/macro.py:38-42); descriptor keys `"2s10s", "5s30s", "3m10y", "2s5s10s_fly", "level", "1y1y", "2y1y", "5y5y", "1y_fwd_1y_ahead"` (210-211); `len(macro.INDICATORS) == 18` (525, 541); `bonds.DEFAULT_SCENARIOS` names include `"+25bp parallel"`, `"-25bp parallel"`, `"+100bp parallel"`, `"-100bp parallel"`, `"bear steepener"`, `"bull flattener"` (282-287); swap forward keys `{"1y1y", "2y1y", "5y5y", "10y10y"}` (316).
Units: decimals inside `core/ficc` (`BP = 1e-4`, `TRADING_DAYS = 252`, `KEY_TENORS = (0.25, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)`, `UST_TENORS` = 11 tenors from 1/12 to 30, core/ficc/common.py:7-14); z-scores bounded `-6 <= z_1y <= 6`, percentiles in `[0, 1]` (527).

### A.7 `tests/expansion_acceptance.py` (332 lines): "expansion" suite, 17 tests

| Helper | Signature and behaviour | Line |
|---|---|---|
| `_selfcheck(rel: str)` | returns a function that runs `runpy.run_path(str(ROOT / rel), run_name="__main__")`; `__name__` set to `f"selfcheck_{rel...}"` | 28-33 |
| `_FakeKIS` | `ready = True`; `.calls: list[tuple[str, str, dict]]`; `._get(path, tr_id, params)` answers by path suffix (`display-board-callput`, `display-board-option-list`, `comp-interest`, futureoption `inquire-price`, `daily-ccnl`, `etfetn/v1/quotations/inquire-price`, `domestic-bond/v1/quotations/inquire-price`, `overseas-price/v1/quotations/price`, default 5-row page) with `{"rt_cd": "0", ...}` | 39-83 |
| `tests()` | an EXPLICIT list of `(name, fn)`; names have no `test_` prefix | 306-325 |
| `__main__` | `sys.path.insert(0, str(ROOT))` then runs all, no failure capture (same `import config` caveat as ficc) | 328-332 |

Fake transports and patch points:
- KIS asset domains: dependency injection, `KISMarkets(client=_FakeKIS())` (88); offline: `config.kis_ready = lambda: False` then `KISMarkets().etf_quote(...)` must raise `data.krx.kis_client.KISUnavailable` (122-137).
- Crypto: `cc._get = fake` where `fake(url, params=None, headers=None, *, label)` dispatches on `"candles"`, `"klines"`, `"accounts"` in the URL (158-171); `config.upbit_ready`, `config.upbit_keys` patched (177-179); `config.FICC_CACHE_TTL_SECONDS = 0.0` while calling `load_history("KRW-BTC", source="auto")` so no real cache file is read or written (186-192).
- ETF page: `km_mod.KISMarkets = _FakeKM`, `etf.load_history = lambda ...`, `config.kis_ready = lambda: True` (224-229).
- Source scan of `data/crypto/crypto_client.py` (154-156): forbidden `"/v1/orders"`, `"/v1/withdraws"`, `"/api/v3/order"`, `"private_key"`, `"seed_phrase"`, `"import ccxt"`, `"import web3"` (after removing the phrase `"No order, cancel, withdrawal"`).
- Gate test (264-287): `V.GATE["bootstrap_B"] = 300` (line 273; NOT restored, see E.6); `V.walk_forward(good, dates, turnover=turn, pnl_stress=good - 0.0001, embargo=1)`; `V.score_strategy(wf, grid=grid, full_pnl=good, n_trials=12)`; asserts `sg.ci90[0] > 0 and sg.sr_oos > 0.7`, `sn.decision != "PASS" and sn.dsr < 0.95`, `sg.dsr > sn.dsr`, `len(sg.lines) >= 8`; `V.kupiec(...)["p"] > 0.05`; `V.pit_tests(...)["ks_p"] > 0.05`; a `V.ModelCard(...)` serialises with `'"decision"'`.
- Causality test (290-303): for `S.trend_switch`, `S.vol_target`, `S.xs_momentum`, `S.tsmom`, `S.crypto_trend` and `S.pairs`: changing prices from row 600 leaves weights `[:599]` unchanged (`np.allclose`).
- Self-checks registered: `data/kis_markets.py`, `data/crypto/crypto_client.py`, `core/quant/validate.py`, `core/quant/strategies.py`, `core/ficc/equity_deriv.py`, `core/ficc/curve_models.py`, `core/ficc/fx_styles.py`, `core/ficc/vol_products.py`, `core/crypto/analytics.py` (316-324). All are offline (fake clients or seeded synthetic data; verified by reading each `__main__` head). NOT registered although they have a `__main__` block: `core/quant/gjr.py:206`, `core/quant/garch.py:719`, `core/ficc/data.py:663`.

### A.8 `qa/acceptance_results.json`

List of 266 rows `{"test", "status", "seconds", "detail"}`; the only machine-readable test output. Slowest rows at baseline: `expansion/selfcheck_validate` 46.5 s, `quant/test_lr_is_nonnegative_and_correctly_sized_under_the_null` 26.7 s, `quant/test_interval_coverage_on_simulated_t_garch` 17.9 s, `expansion/gate_noise_vs_edge` 9.3 s, `quant/test_rate_modes_make_the_discounted_price_a_martingale_for_every_model` 7.2 s, `expansion/selfcheck_crypto_analytics` 7.1 s, `cockpit/test_06_readiness_states_are_exhaustive` 5.7 s.

### A.9 `docs/ARCHITECTURE_REVIEW.md` (786 lines; written 2026-09-14, status section added later)

Scope (11-17): the Quant Lab (`core/quant/garch.py`, `montecarlo.py`, `history.py`, `docs/drift_study.py`, `tests/quant_acceptance.py`) plus an application map. Evidence tags `[RUN]`, `[DOC]`, `[REF]`, `[EXT]` (21-26). Severity: High = a displayed number is wrong or mislabelled; Medium = silent estimation or selection weakness; Low = consistency or naming (250-252).

Application map facts (52-97): views are built once and cached, rail order is the `NAV` tuple in `main.py`; `core/ficc` uses decimals inside and % / bp only in the UI; routing rule for both data layers: "explicit provider that fails RAISES; only "auto" degrades to labeled synthetic"; charts are matplotlib Agg rendered to base64 data-URI images because Flet has no chart control; `config.py` holds credentials by family, `~/.nextgen/ficc_cache (6 h)`, the trading dir for rules JSON, and the skill env; engine loop `DISARMED -> ARMED -> HALTED` on a background thread; `orders` is a simulated order book with NO broker order path.

Findings register (254-277) with status (status column: section 1.3 lines 146-246 of the review, plus code evidence where I checked it):

| ID | Sev. | Finding (short) | Status |
|---|---|---|---|
| A1 | High | rf / premium drift used one sample-vol convexity correction for every model | CLOSED 2026-09-16: per-model exact per-step correction; `MCResult.correction_annual`, `z_bound`; `mu_annual` is the effective log drift (173-181) |
| A2 | High | Student-t innovations give the terminal price no finite mean | CLOSED 2026-09-16: innovations bounded at `Z_BOUND` = 22 (band 14..30), redraw not rescale; `bound_note` on every GARCH-t run (151-172) |
| A3 | Medium | dividend convention of closes unstated | PARTLY in code: `History.adjustment` in `{"total", "split", ""}` (history.py:61-64) and `convention_warning` (history.py:101-113). The `rf - q` drift is not evidenced |
| A4 | Medium | FX pairs use the domestic rate in rf mode instead of `r_dom - r_for` | OPEN per the document |
| A5 | Low | jump calibration by a 3-sigma threshold | (iii) CLOSED (182-183); (i)-(ii) OPEN |
| A6 | Low | GARCH filter mean differs from the simulated drift | OPEN |
| B1 | High | nu capped at 30 broke nesting (negative LR) | CLOSED 2026-09-21: `eta = 1/nu` on `[0, 0.4]`, `LR_5PCT = 2.706`, `NU_NORMAL` chip (184-195) |
| B2 | Medium | no standard errors | CLOSED 2026-09-25: observed-information Wald SEs in `GarchFit.se` (keys `omega, alpha, beta, eta, persistence`), `se_note`, profile-likelihood interval for eta on a 41-point grid, cut 1.92 inside and 1.353 at eta = 0, `fit_garch(profile=False)` for loops (196-227) |
| B3 | Medium | finite-difference gradient, penalty plateau, three starts | OPEN (one start moved to beta0 = 0.94, 217-221) |
| B4 | Low | AIC parameter count and ddof inconsistency | OPEN ("B4 (AIC bookkeeping) is unchanged", 228) |
| B5 | High | model selection is in-sample; the vol model was never scored out of sample | Tooling exists: `core.quant.validate.score_distribution` (validate.py:673) and the `D_*` cards in `docs/asset_expansion/cards/`. The script the review names, `docs/vol_backtest.py` (688), does NOT exist. The spec builds on this finding (R-30, T-B5-01, G-B5-01..04) |
| B6 | Medium | no ACF check of squared standardised residuals | OPEN per the document |
| B7 | Medium | atypical fit not flagged | OPEN |
| B8 | Medium | no leverage term | `core/quant/gjr.py` exists (`fit_gjr`, `GJRFit`, `GAMMA_BOUNDS = (0.0, 0.5)`, `LAMBDA_BOUNDS = (-0.9, 0.9)`); adoption is decided by the cards, not by this review |
| B9 | Low | stochastic volatility not considered | OPEN (research) |
| C1 | Low | "stationary" bootstrap is a fixed 5-session circular block bootstrap | OPEN (`_simulate_bootstrap(rng, r, n_paths, horizon, block: int = 5)`, montecarlo.py:166) |
| C2 | Low | VaR / CVaR clipped at zero | OPEN per the document (`MCResult.var_pct` comment: "as +fraction of spot") |
| C3 | Medium | rate levels routed to a log-return model; ratesim OLS has no SE and clamps kappa at 0.01 | OPEN |
| C4 | Medium | no implied-vol channel into the P-fan | OPEN |
| C5 | Medium | P-simulator and Q-pricers share no path object | OPEN |
| D1 | Medium | data validation is a manual instruction | Function exists: `validate.data_checks(dates, closes, *, max_gap_sessions=5, stale_days=5, today=None) -> list[str]` (validate.py:241-269). Whether every loader calls it before a fit was not checked |
| D2 | Low | "same seed" is not common random numbers | OPEN |

Rules of the review that the spec inherits:
- B5 gate rule (528-531): "a model becomes or stays the default only if its VaR95 exceedance rate over >= 200 origins is within +/-2 binomial SE of 5 % and its PIT histogram passes a uniformity check."
- B5 measurement recipe (520-526): at each origin fit on the trailing window, simulate h in {1, 5, 21, 63} sessions, record the 1-day and h-day VaR95 exceedance rate (target 5 %), 90 % band coverage (target 90 %) and the PIT value; report per model and asset class with binomial standard errors.
- Target-architecture test list (692-694): rf-mode martingale test (A1), LR >= 0 and 5 % size (B1), interval coverage (B2), tighter recovery (B3), ACF of z^2 in band (B6), split detection (D1), EM recovers lambda (A5), bootstrap keeps lag-5 ACF (C1), FX rf median = CIP forward (A4). The first three exist in `tests/quant_acceptance.py`; the rest do not.
- "Nothing above requires a new dependency" (711-712).
- Appendix A (740-765): `docs/verify_drift_check.py`, run from the project root with `PYTHONPATH=.`, no network, about two minutes; series `simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=1000, seed=3)` plus 0.04 %/day; 100,000 paths, seeds 7, 8, 9, rf 3 %, ERP 4 %, 126 sessions.
- Stale statement inside the review: line 96 says the runner covers "engine + quant + FICC acceptance"; it now runs six suites.

### A.10 Test-facing APIs of the code under test (signatures the suites depend on)

`config.py` (348 lines). Every credential reader is a function re-read on each call through `_clean(name)` (33-40: strips, drops matching quotes, rejects `<placeholder>`). Module-level constants are read ONCE at import.

| Name | Kind | Value / env var | Line |
|---|---|---|---|
| `fmp_key() -> str`, `fmp_ready() -> bool` | fn | `FMP_API_KEY` | 132-137 |
| `kis_ready() -> bool`, `kis_credentials() -> tuple[str, str]` | fn | `KIS_APP_KEY`, `KIS_APP_SECRET` | 156-161 |
| `opendart_ready()`, `opendart_key()` | fn | `OPENDART_API_KEY` | 167-172 |
| `krx_key()`, `krx_ready()` | fn | `KRX_API_KEY` | 179-186 |
| `anthropic_key()`, `ai_ready()`, `ai_model()` | fn | `ANTHROPIC_API_KEY`, `QUANTGEN_AI_MODEL` (default `"claude-sonnet-5"`) | 269-278 |
| `gs_client_id()`, `gs_client_secret()` | fn | `GS_CLIENT_ID`, `GS_CLIENT_SECRET` | 281-286 |
| `upbit_ready()`, `upbit_keys()` | fn | `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY` | 308-313 |
| `skills_root() -> Path`, `skills_root_valid()` | fn | `NEXTGEN_SKILLS_ROOT`, default `~/Downloads/claude-trading-skills-main/claude-trading-skills-main` | 50-63 |
| `skill_python()` | fn | `NEXTGEN_SKILL_PYTHON` or `sys.executable` | 67-69 |
| `runs_dir() -> Path` | fn | `NEXTGEN_RUNS_DIR`, default `~/.nextgen/runs` | 75-77 |
| `trading_dir() -> Path` | fn | `NEXTGEN_TRADING_DIR`, default `~/.nextgen/trading` | 236-238 |
| `ficc_cache_dir() -> Path` | fn | `NEXTGEN_FICC_CACHE`, default `~/.nextgen/ficc_cache` | 334-336 |
| `FICC_CACHE_TTL_SECONDS` | const | `NEXTGEN_FICC_CACHE_TTL`, default `6 * 3600`; `0` disables | 331 |
| `SKILL_TIMEOUT_SECONDS` | const | `NEXTGEN_SKILL_TIMEOUT`, default 300 | 72 |
| `HTTP_TIMEOUT_SECONDS` | const | `NEXTGEN_HTTP_TIMEOUT`, default 12 | 193 |
| `QUOTE_MAX_AGE_SECONDS` | const | `NEXTGEN_QUOTE_MAX_AGE`, default 120 | 242 |
| `ENGINE_TICK_SECONDS` | const | `NEXTGEN_ENGINE_TICK`, default 5 | 245 |
| `NO_DATA_GRACE_TICKS` | const | `NEXTGEN_NO_DATA_GRACE`, default 3 (runtime caps at 10) | 254 |
| `FMP_MIN_INTERVAL_SECONDS` | const | `NEXTGEN_FMP_MIN_INTERVAL`, default 20 | 148 |
| `FMP_BASE_URL`, `KIS_BASE_URL`, `OPENDART_BASE_URL`, `KRX_BASE_URL`, `FRED_BASE_URL` | const | same-named env vars; defaults `https://financialmodelingprep.com/stable`, `https://openapi.koreainvestment.com:9443`, `https://opendart.fss.or.kr/api`, `https://data-dbg.krx.co.kr/svc/apis`, `https://fred.stlouisfed.org/graph/fredgraph.csv` | 142, 164, 175, 189, 328 |
| per-market quote age | env | `NEXTGEN_MAX_AGE_<code>` read in `core/markets.py:222` | - |

`core/quant/history.py` (504 lines):
- `TRADING_DAYS = 252` (47); `class HistoryError(RuntimeError)` (50).
- `@dataclass(frozen=True) class History` (54-64): `symbol: str`, `source: str` (`"FMP" | "KIS" | "YFINANCE" | "UPBIT" | "BINANCE" | "SYNTHETIC"`), `dates: tuple[str, ...]` (ISO, ascending), `closes: tuple[float, ...]`, `note: str = ""`, `adjustment: str = ""` (`"total"` = splits AND dividends; `"split"` = splits only; `""` = not applicable or unknown). Methods: `__len__`, `.last`, `.first_date`, `.last_date`, `.prices() -> np.ndarray`, `.log_returns()`, `.simple_returns()`.
- `_clean_rows(rows) -> (dates, closes)`: drops `None` and non-positive closes, sorts by date (93-98).
- Loaders, all `(symbol, *, days: int = 504) -> History`: `fmp_history` (119), `kis_history` (188), `synthetic_history(symbol, *, days=504, seed=None)` (228), `yf_history` (262), `crypto_history` (280), `kis_market_history` (292).
- `SOURCES = ("auto", "fmp", "kis", "yfinance", "crypto", "synthetic")` (454); `load_history(symbol, *, source="auto", days=504) -> History` (457-504). `auto` routing: `_looks_krx` -> KIS if `config.kis_ready()` else SYNTHETIC with note `"KIS credentials are not configured; ..."`; `_looks_crypto` -> crypto (keyless, NETWORK even with no keys); `_looks_yahoo` -> Yahoo (keyless, NETWORK even with no keys); `_looks_kis_market` -> KIS or SYNTHETIC; otherwise FMP if `config.fmp_ready()` else SYNTHETIC with note `"FMP_API_KEY is not configured; ..."`. Blank symbol or unknown source raises `HistoryError`.
- Cache: `_cached(provider, fetch, symbol, days)` (398-451); `_READY = {"FMP": lambda: bool(config.fmp_key()), "KIS": lambda: config.kis_ready()}` (352); `_CACHE_MIN_ROWS = 30`; `_CACHE_LIVE_TTL = 600.0`; file `config.ficc_cache_dir() / f"HIST_{provider}_{SYMBOL}_{days}.json"` (non `[A-Za-z0-9_.-]` replaced by `_`); payload `{"ts": time.time(), "live": bool, "symbol", "source", "note", "adjustment", "dates", "closes"}`.
- `_may_be_trading(provider, symbol, at=None) -> bool` (359-383), `_traded_since(provider, symbol, ts) -> bool` (386-395).

`core/ficc/data.py` (724 lines):
- `SOURCES = ("auto", "fred", "yfinance", "synthetic")` (64); `G10_KRW = ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "KRW")` (65); `_MIN_OBS = 5`.
- `@dataclass(frozen=True) class Series` (77-114): `id, label, source ("FRED" | "YFINANCE" | "SYNTHETIC"), dates, values, note=""`; `.last`, `.first_date`, `.last_date`, `.array()`, `.change(n) -> float | None`, `.window(n)`, `.scaled(factor)`.
- `CurveSnapshot(date, source, tenors, par_yields, note="")` (117-123); `CurvePanel(source, dates, tenors, yields: np.ndarray (T, K), note="")` with `.at(i)`, `.latest()` (126-143).
- The two network touchpoints (158-210): `Rows = list[tuple[str, float]]`; `_fred_fetch(ids: list[str], start: str) -> dict[str, Rows]`; `_yf_fetch(tickers: list[str], period: str) -> dict[str, Rows]` (yfinance `auto_adjust=True`).
- Cache (216-251): `_MEM: dict[str, tuple[float, Rows]]`; `_cache_key(provider, id, days)`; file `config.ficc_cache_dir() / f"{key}.json"` with `{"ts": now, "rows": rows}`; never raises; disabled when TTL <= 0.
- Public loaders: `load_many(ids, *, source="auto", days=756) -> dict[str, Series]` (474), `load_series(id, *, source="auto", days=756, label="")` (508), `load_treasury_curve(*, source="auto", days=504) -> CurvePanel` (513), `load_fx_spot(pair, *, source="auto", days=504)` (560), `load_short_rate(ccy="USD", *, source="auto", days=756)` (606), `load_policy_rates(ccys, *, source="auto", days=756)` (635), `probe() -> dict` (640), `synthetic_series(id, *, days=756, kind="level")` (293), `synthetic_curve_panel(*, days=504, seed=None)` (334), `synthetic_fx(pair, *, days=504)` (370). FRED rate series arrive in PERCENT; `load_series` returns them raw, `load_treasury_curve` and `load_short_rate` divide by 100 (docstring 20-22).

`data/net.py` (56 lines): `RETRY = Retry(total=2, backoff_factor=0.5, status_forcelist=(502, 503, 504), allowed_methods=("GET",), respect_retry_after_header=False, raise_on_status=False)`; `session = requests.Session()` with that adapter on `https://` and `http://`; `logging.getLogger("urllib3").setLevel(logging.ERROR)`.

`core/quant/validate.py` (869 lines; "the gate"):
- `TRADING_DAYS = 252`; `EULER_GAMMA = 0.5772156649015329`; `DECISIONS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")` (48-50).
- `GATE` (53-74), a mutable module dict, "change them here and nowhere else": `"w_is": 756, "w_oos": 126, "min_is": 504, "ci_level": 0.90, "bootstrap_B": 2000, "block": 10, "dsr_min": 0.95, "pbo_max": 0.05, "pbo_reject": 0.20, "oos_is_min": 0.5, "years_pos_min": 0.60, "plateau_min": 0.5, "trades_min": 100, "trades_floor": 30, "oos_years_min": 5, "haircut": 0.6, "cost_stress": 2.0, "pbo_min_configs": 8, "prob_loss_max": 0.10, "bench_p_max": 0.10, "var95_min_origins": 500, "var99_min_origins": 1000, "pit_ks_min": 0.05, "pit_ks_reject": 0.01, "kupiec_min": 0.05, "cc_min": 0.05, "exceed_reject_mult": 2.0, "nonconv_max": 0.05`.
- Statistics: `sharpe(daily) -> float` (80; ddof=1, x sqrt(252)); `lo_se(daily)` (89); `min_track_record(sr_annual, level=0.90)` (99; `252 * (z / SR)^2`); `block_bootstrap_ci(daily, *, block=10, B=2000, level=0.90, seed=11) -> tuple[float, float]` (106; studentised circular block bootstrap); `sharpe_diff_bootstrap(a, b, *, block=10, B=2000, level=0.90, seed=11) -> {"diff", "ci", "p"}` (129; paired; `p` = share of resampled differences <= 0); `expected_max_sharpe(n_trials, sr_sd)` (154); `deflated_sharpe(daily, *, n_trials, sr_sd_daily) -> float` (163); `pbo_cscv(pnl, *, S=8) -> {"pbo", "n_splits", "prob_loss", "slope"}` (183); `newey_west_t(d, lag)` (216); `dm_test(loss_a, loss_b, *, lag=0) -> {"t", "p", "mean_diff", "n"}` (230); `data_checks(...)` (241).
- Strategy loop: `@dataclass(frozen=True) class WalkForward` (275-285: `dates, pnl, pnl_stress, turnover, origins, chosen, is_sharpes, n_configs, note`); `walk_forward(pnl, dates, *, turnover=None, pnl_stress=None, w_is=GATE["w_is"], w_oos=GATE["w_oos"], embargo=0, min_is=GATE["min_is"]) -> WalkForward` (288; raises `ValueError` on length mismatch or too few sessions; defaults bound at definition time); `plateau_share(grid, sharpes, best, domain=None) -> tuple[float, bool]` (327); `year_stats(dates, pnl) -> dict` (364); `regime_split(pnl, bench, *, window=63) -> dict` (374); `@dataclass class StrategyScore` (389-423: `sr_oos, se_lo, ci90, sr_is, oos_is, dsr, pbo, pbo_slope, prob_loss_oos, sr_stress, turnover_annual, n_trades, n_sessions, years_positive, n_years, max_year_share, plateau, edge, regime, total_return, max_drawdown, haircut_sr, bench_sr, n_trials, n_configs=1, bench_diff, bench_p, bench_ci, bench_mdd, decision, reason, revise_target, lines`); `score_strategy(wf, *, grid, full_pnl, n_trials, bench_daily=None, seed=11, domain=None) -> StrategyScore` (426; reads `GATE["block"]`, `GATE["bootstrap_B"]`, `GATE["ci_level"]`, `GATE["haircut"]` at CALL time); `_decide_strategy(s)` (470-554).
- Decision order in `_decide_strategy` (519-554): (1) `n_trades < trades_floor or n_years < oos_years_min` -> `INSUFFICIENT_DATA`; (2) `dsr < dsr_min`, or `pbo_reject`, or (`sr_stress <= 0` and CI includes zero), or benchmark p > `bench_p_max` -> `REJECT`; (3) all hard and engineering checks -> `PASS` (reason `"every gate criterion met"`); (4) CI includes zero with DSR and PBO passing and `n_sessions < min_track_record` -> `INSUFFICIENT_DATA`; (5) else `REVISE` with `revise_target` keyed by the first failed of `"over-search", "execution", "regime", "plateau", "sample", "interval"`.
- Distribution loop: `kupiec(hits, alpha) -> {"n", "x", "rate", "lr", "p"}` (560); `christoffersen(hits, alpha) -> {"lr_ind", "p_ind", "lr_cc", "p_cc"}` (573); `traffic_light(hits99, window=250) -> "green" | "yellow" | "red"` (593; x <= 4 green, <= 9 yellow); `coverage_check(inband, level=0.90) -> {"coverage", "se", "ok", "n"}` (598); `pit_tests(u, *, lags=(1, 5, 20)) -> {"n", "ks_p", "chi2_p", "berkowitz_lr", "berkowitz_p", "mean", "acf_flags", "shape"}` (608); `crps(samples, x)` (645); `@dataclass class DistributionScore` (657-670); `score_distribution(*, hits95, hits99, inband90, pit, nonconv=None, horizon=1) -> DistributionScore` (673-728).
- Model card: `@dataclass class ModelCard` (734-757; NOT frozen), required fields in order `card_id, kind ("strategy" | "distribution" | "model"; the study also writes "error"), hypothesis, rules, universe, data, costs, protocol, trials, seed, stats, tests, decision, decision_reason, revise_target, lines`; defaults `decay_haircut = {"factor": GATE["haircut"], "source": "McLean-Pontiff 2016 26-58%"}`, `created = date.today().isoformat()`, `author = "QUANTGEN validation gate"`, `results_file = ""`, `results_md5 = ""`, `citations = []`; `.to_json()` (`ensure_ascii=False, indent=1`), `.save(directory) -> Path` (`<card_id>.json`, UTF-8); `load_cards(directory) -> list[dict]` (779; unreadable files skipped silently); `md5_of(path) -> str` (791; `""` if missing).

`core/quant/strategies.py` (469 lines): `BP = 1e-4`; `@dataclass(frozen=True) class Panel(dates, symbols, prices: np.ndarray T x N, sources=())` (40-48); `align_panel(histories) -> Panel` (51; raises `ValueError` under 60 shared sessions); `simulate(prices, weights, *, cost_bps=5.0, cash_daily=0.0) -> (pnl (T-1,), turnover (T-1,))` (69-90; weight row t is held over t -> t+1; `|dw|` at t charged on that session; `pnl = gross - turnover * cost_bps * BP`; the unallocated fraction of a long-only book earns `cash_daily`); `equity_curve(pnl)`; `summary(pnl) -> {"total_return", "ann_return", "ann_vol", "sharpe", "max_drawdown", "sessions"}`; `realised_vol(prices, window=22)`; `ewma_vol(prices, com=60.0)`; `trend_switch(prices, *, rule="sma", lookback=210, step=21, ...)`; `vol_target(prices, *, target, window=22, step=21, cap=1.0, band=0.10) -> weights` (190-209; `w = min(cap, target / sigma_hat)`, updated every `step` sessions and only when it moves by more than `band`); `xs_momentum`, `tsmom`, `pairs`, `crypto_trend`, `risk_parity`; `pnl_matrix(prices, fn, grid, *, cost_bps, cash_daily=0.0, stress=2.0) -> (pnl T-1 x G, pnl at stress x costs, turnover)` (379-389); `grid_from(**axes) -> list[dict]` (392).

`docs/asset_expansion_study.py` (the only script that writes `docs/asset_expansion/`): `COST = {"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}` (60; bp per side); `SEED = 11` (61); `_cached(name, loader)` writes `cache/<name with = ^ : / replaced by _>.csv` (68-79); `yf(symbol, start="1995-01-01")` uses `yfinance.download(symbol, start=start, auto_adjust=True, progress=False, threads=False)` and keeps `Close` (82-91); `fred(series_id, start="1990-01-01")` via `pandas_datareader` (94-104; the file keeps NaN rows); `upbit(market="KRW-BTC")`, `binance(symbol="BTCUSDT")` via `data.crypto.crypto_client` `.daily(..., days=4000)` (107-120); `binance_funding(symbol)` = `BinancePublic().funding(symbol, days=3000).daily()` (123-135); `panel(series, *, start=None) -> S.Panel` (inner join, `dropna`, needs >= 300 shared sessions; `sources = "STUDY"`); `rf_daily(index)` = `DGS3MO` forward-filled, `/ 100 / 252`, fallback `0.03 / 252` (148-153); `strategy_card(...)`, `model_card(...)`, `error_card(...)` build `V.ModelCard`; CLI `[--quick] [--only id1,id2] [--refresh]`; `--quick` sets `V.GATE["bootstrap_B"] = 300` (191-192).

---

## B. Cross-file flows

### B.1 Test run

```
python tests/run_all.py                       (cwd-independent: ROOT is derived from __file__)
  -> import config            -> load_dotenv() reads ROOT/.env (never open it; .env.example lists the keys)
  -> import the six suites    -> imports flet, matplotlib, scipy, core.*, data.*, ui.* (import failure = no run)
  -> cockpit (47)  external skills repo at config.skills_root(); subprocess runs; ~/.nextgen/runs writes; KRX gateway
  -> engine  (89)  tempfile.mkdtemp() stores; fake gateways; loopback HTTP server (test 82)
  -> ui      (4)   AST lint of ui/*.py against the installed flet
  -> quant   (53)  synthetic series; config readers patched; tmp cache dir
  -> ficc    (56)  synthetic; _no_network() for the degradation tests
  -> expansion (17) fake KIS / crypto transports; gate on synthetic P&L; nine module self-checks via runpy
  -> qa/acceptance_results.json ; exit code 0 or 1
```

### B.2 Persistence locations

| Location | Writer | Content | Redirect |
|---|---|---|---|
| `ROOT/qa/acceptance_results.json` | `tests/run_all.py:64-66` | test results | none |
| `~/.nextgen/ficc_cache/*.json` (84 files at mapping time) | `core/ficc/data._cache_put` (`<provider>_<id>_<days>.json`), `core/quant/history._cached` (`HIST_<provider>_<SYMBOL>_<days>.json`) | fetched series | `NEXTGEN_FICC_CACHE`; `NEXTGEN_FICC_CACHE_TTL=0` or `config.FICC_CACHE_TTL_SECONDS = 0.0` disables |
| `~/.nextgen/runs/<run_id>/` (497 dirs at mapping time) | `core/skills/runner._new_run_dir` (runner.py:188-192), `runs.record` writes `run.json`, runner writes `transcript.log` | skill runs | `NEXTGEN_RUNS_DIR` |
| `~/.nextgen/trading/rules.json`, `engine.json` (also present: `practice_checklist.json`, `safety.json`) | `core/rules/store.RuleStore(path=None)` (store.py:135), `core/engine/runtime` (runtime.py:79) | rules with edit history; engine halt state and trigger counts | `NEXTGEN_TRADING_DIR`; constructor arguments `RuleStore(path)`, `EngineRuntime(..., state_path=...)` |
| `~/.nextgen/kis_token.json` | `data/krx/kis_client._TOKEN_PATH` (kis_client.py:53) | KIS OAuth token cache | none (module constant) |
| `~/.nextgen/dart_corp_codes.json` | `data/krx/opendart_client._CACHE_PATH` (opendart_client.py:44) | corp-code map | none |
| `~/.nextgen/prefs.json`, `policy_events.jsonl` | not located in `core/`, `data/`, `ui/`, `main.py` by grep | unknown | unknown |
| `ROOT/data/calendars/<MARKET>.json` (22 markets) | shipped data, read by `core/calendars.py` (`DATA_DIR`, calendars.py:32) | keys `market, timezone, source {library, version, calendar, generated}, covers {from, to}, regular {open, close, break_start, break_end}, holidays [...], special_sessions {date: {open, close}}`; KRX and US cover `2026-01-01` to `2027-12-31`, generated `2026-08-18` | none |
| `ROOT/docs/asset_expansion/cache/*.csv` | `docs/asset_expansion_study.py` | study price cache (see DI.1) | `--refresh` re-downloads |
| `ROOT/docs/asset_expansion/cards/<card_id>.json` (34 cards) | study via `ModelCard`; rewritten by `write_results()` with `results_file`, `results_md5` | model cards | none |
| `ROOT/docs/asset_expansion/results.csv` (501 rows: `card, metric, value`), `results.md`, `manifest.json` | study `write_results()` | `manifest.json` keys: `run` ("2026-09-27"), `seed` (11), `results_md5` ("ca757e25f508b588cb2f361719ec83cd"; equals the current md5 of `results.csv`, verified), `quick` (false), `cards` (34), `rescored` (1), `decisions` (34) | none |

Readers of the cards: `ui/strategy_lab_page.py:31` (`CARDS_DIR = ROOT / "docs" / "asset_expansion" / "cards"`; sorted PASS, REVISE, REJECT, other), `ui/etf_page.py:120`, `ui/crypto_page.py:102`, `ui/quant_lab_page.py:159`. All index the dicts by `card_id`.

### B.3 Who calls the network, and how tests stop it

| Provider | Single touchpoint | How the existing tests neutralise it |
|---|---|---|
| FRED | `core.ficc.data._fred_fetch` | `_no_network()` (ficc_acceptance.py:30-41) or `source="synthetic"` |
| Yahoo | `core.ficc.data._yf_fetch` (also used by `core.quant.history.yf_history`) | `_no_network()`; or replaced by a lambda (quant_acceptance.py:287) |
| FMP history | `core.quant.history._requests.get` inside `fmp_history` | `config.fmp_key = lambda: ""` (raises before any request); or `H._requests = _HTTP(...)`; or `H.fmp_history = fake` |
| FMP quotes | `data.fmp.quote_client` (plain `requests`) | `_FakeFMP` injected into the feed |
| KIS | `data.krx.kis_client.KISClient._get` (session `requests`; `_once` for live quotes) | `config.kis_ready = lambda: False`; `kis.KISClient = _FakeKIS`; `KISMarkets(client=_FakeKIS())`; `client._get = lambda ...` |
| Upbit / Binance | `data.crypto.crypto_client._get(url, params=None, headers=None, *, label)` | `cc._get = fake` |
| OpenDART, KRX marketplace | `data.krx.opendart_client`, `data.krx.krx_market_client` | NOT neutralised (see E.3) |
| Anthropic | `core.quant.insights.deep_analysis`, `core.ficc.insights.deep_analysis` | `config.anthropic_key = lambda: ""` gives `result.text == ""` and `"ANTHROPIC_API_KEY" in result.error` |
| gs_quant session | `core.quant.gsq` | no credentials configured; `gsq.price_example_swap()` returns `{"ok": False, "detail": ...}` |

There is no global socket guard anywhere in the suite.

---

## C. Existing tests and how new ones are registered

### C.1 Registration (complete procedure today)

1. Create `tests/<name>_acceptance.py` that imports what it needs at module top (ROOT is already on `sys.path` when loaded through `run_all`).
2. Define zero-argument functions that raise on failure.
3. Export `def tests() -> list[tuple[str, Callable[[], None]]]`: either the `sorted(globals())` idiom (every module global whose name starts with `test_` and is callable is registered, imported names included) or an explicit list (the expansion style, which is also the only way to register a `_selfcheck(...)` closure).
4. Add one import line and one list line in `tests/run_all.py` (30-35 and 39-44) with a new prefix.
5. A module self-check is added as `("selfcheck_<x>", _selfcheck("<path from ROOT>.py"))` in `tests/expansion_acceptance.py:316-324` (the `__main__` block must only assert and print; it must not call `sys.exit`).

Order of execution: suites in the `run_all` list order; inside cockpit, engine, ui, quant, ficc alphabetical by function name; inside expansion the list order.

### C.2 Coverage by suite

| Suite (prefix) | n | What it asserts |
|---|---:|---|
| cockpit | 47 | catalogue parse (>= 60 skills, >= 8 workflows), entrypoints, readiness states, credential naming; static safety scans (A.2 table); redaction; runner on real skill scripts; KRX gateway degradation; argument reading; diagnosis; decision-gate options; insights; wiring |
| engine | 89 | DISARMED start, manual re-arm, halt persistence, emergency stop; stale / missing quote halts; duplicate triggers; caps; sessions, lunch breaks, holidays, half days; calendar coverage and provenance; rule store Decimal round trip and revisions; market routing; FMP client throttling and key redaction; grace window; HTTP retry policy; KIS pacing |
| ui | 4 | Flet API guard (A.4) |
| quant | 53 | see C.3 |
| ficc | 56 | see C.4 |
| expansion | 17 | see A.7 |

### C.3 quant (53), grouped as in the file

| Group | Tests | Key assertions |
|---|---|---|
| History (9) | `test_synthetic_is_deterministic_per_symbol`, `test_load_history_rejects_blank_and_unknown_source`, `test_auto_routing_falls_back_to_labeled_synthetic`, `test_explicit_provider_without_key_raises_not_simulates`, `test_history_cache_serves_a_rerun_without_asking_the_provider_again`, `test_fmp_history_asks_for_dividend_adjusted_closes_and_reports_refusals_honestly`, `test_the_cache_knows_when_a_market_may_be_trading`, `test_each_loader_states_its_return_convention`, `test_a_panel_mixing_total_and_price_return_series_is_called_out` | `auto` without keys: `source == "SYNTHETIC"` and `"FMP_API_KEY" in note` (US) or `"KIS" in note` (KRX); `source="fmp"` without a key raises `HistoryError`; FMP URL ends `/historical-price-eod/dividend-adjusted`; a row without `adjClose` is dropped and reported (`"1 session(s) without adjClose dropped"`); a response with no `adjClose` gives `"NOT dividend-adjusted"` and `adjustment == "split"`; an `{"Error Message": ...}` body raises without echoing the key; HTTP 429 raises with `"rate limit"`; adjustments `("split", "total", "")` for KIS, Yahoo `.KS`, `^VIX` |
| Monte Carlo (6) | `test_mc_is_seeded_and_reproducible`, `test_mc_fan_percentiles_are_ordered`, `test_mc_var_and_cvar_are_coherent`, `test_mc_target_probability_brackets`, `test_mc_jump_degrades_to_gbm_without_outliers`, `test_mc_all_models_run` | same seed same result; fan 5 <= 25 <= 50 <= 75 <= 95 and starts at spot; `0 <= var_pct <= 1`, `cvar_pct >= var_pct`; `(mc.garch is not None) == (model == "garch_t")` |
| Risk (3) | `test_risk_vol_and_drawdown_match_numpy_whatever_engine`, `test_risk_var_cvar_bounds`, `test_align_histories_requires_overlap` | vol = `std(ddof=1) * sqrt(252)` and max drawdown to 1e-6; disjoint histories raise `ValueError` |
| Optimizer (5) | `test_optimizer_weights_are_a_long_only_allocation`, `test_optimizer_objectives_actually_optimize`, `test_risk_parity_equalizes_risk_contributions`, `test_max_weight_cap_is_respected`, `test_frontier_is_traced_and_cloud_is_dominated` | objectives `"max_sharpe", "min_vol", "risk_parity", "equal_weight"`; weights sum to 1 (1e-6), `>= -1e-9`; `max_weight=0.4` respected |
| Signals (3) | `test_signals_read_the_trend_direction`, `test_signal_scores_and_weights_are_bounded`, `test_rsi_stays_in_bounds` | composite and component scores in `[-100, 100]`; every component has a `reason`; weights sum within 0.25 of 1 |
| Backtest (4) | `test_backtest_costs_only_hurt`, `test_backtest_has_no_lookahead`, `test_backtest_rejects_inverted_ma_params`, `test_backtest_exposure_and_drawdown_sane` | costs do not change `n_trades`; `momentum(lookback=1)` on a rising series equals `closes[-1] / closes[1] - 1` (decided at t, earns from t+1); `fast >= slow` raises `ValueError` |
| Insights, gs_quant, charts (5) | `test_narratives_state_their_numbers`, `test_deep_analysis_without_key_degrades_without_network`, `test_gsq_status_is_coherent`, `test_gsq_pricing_without_session_explains_itself`, `test_every_chart_renders_a_data_uri_image` | every chart `img.src.startswith("data:image/png;base64,")` and `len > 1000` |
| GARCH and drift (11) | `test_garch_recovers_parameters_on_simulated_series`, `test_garch_scaled_t_shocks_have_unit_variance`, `test_garch_respects_bounds_and_flags_on_gbm_series`, `test_garch_t_beats_normal_and_gbm_on_clustered_series`, `test_garch_forecast_variance_converges_to_unconditional`, `test_mc_default_model_is_garch_t_seeded_and_reproducible`, `test_mc_zero_drift_lowers_median_on_positive_drift_series`, `test_drift_modes_are_ordered_and_documented`, `test_drift_zero_centres_the_cone_and_sample_reproduces_the_mean`, `test_unknown_drift_raises`, `test_garch_narrative_states_persistence_and_nu` | recovery tolerances alpha 0.05, beta 0.06, nu in (4, 10); reference SEs omega 5.7e-7, alpha 0.0102, beta 0.0117, eta 0.0175, persistence 0.0065 within 15 %; `fit_garch(r[:50])` and `dist="cauchy"` raise `ValueError`; default drift mode `"premium"`; `"rf 4.00%"` and `"ERP 5.00%"` in `drift_note` |
| Bounded innovations (3) | `test_bounded_t_draws_respect_the_bound_and_keep_the_shape`, `test_martingale_correction_matches_quadrature_and_the_normal_closed_form`, `test_rate_modes_make_the_discounted_price_a_martingale_for_every_model` | `abs(z).max() <= Z_BOUND`; correction equals quadrature to 1e-7; for every model `abs(mean(P_T / spot) - exp(rate * H / 252)) < 3 * SE` with 40,000 paths; `f"bounded at ±{Z_BOUND:g}"` in `drift_note`, `f"capped at ±{Z_BOUND:g}"` in `bound_note` |
| B1 / B2 (4) | `test_lr_is_nonnegative_and_correctly_sized_under_the_null`, `test_interval_coverage_on_simulated_t_garch`, `test_intervals_reaching_a_bound_are_flagged`, `test_horizon_vol_describes_the_bounded_paths` | 200 null fits: LR >= 0, size <= `0.05 + 2 * sqrt(0.05 * 0.95 / n)`, share at eta = 0 in [0.30, 0.70]; 50 fits at T = 1000: coverage >= 0.85, fits without SE <= 10 % |

### C.4 ficc (56), grouped as in the file

| Group | n | Tests (prefix `test_`) |
|---|---:|---|
| Data | 5 | `data_synthetic_is_deterministic_and_labeled`, `data_synthetic_never_touches_the_cache`, `data_auto_degrades_to_synthetic_naming_the_provider`, `data_explicit_provider_raises_offline`, `data_shapes_are_clean` |
| Curves | 6 | `curve_bootstrap_round_trips_par_inputs` (1e-8), `curve_df_is_one_at_zero_and_monotone`, `curve_bumps_are_local_and_parallel`, `curve_ns_fit_is_tight` (rmse < 5 bp), `curve_report_uses_allowed_regime_and_shape_strings`, `curve_pca_explains_level_first` |
| Bonds | 9 | `bond_par_prices_at_100_and_yield_round_trips`, `bond_duration_matches_numeric_derivative`, `bond_convexity_is_positive_and_numeric`, `bond_flat_curve_reprices_the_yield`, `bond_krd_sums_to_dv01`, `bond_z_spread_round_trips`, `bond_scenarios_show_convexity`, `bond_analyze_requires_exactly_one_of_price_or_yield`, `futures_hedge_arithmetic` |
| Swaps | 8 | `swap_at_par_has_zero_pv_and_payer_dv01_positive`, `swap_krd_sums_to_dv01`, `swap_off_market_pv_is_minus_spread_times_annuity`, `swaption_put_call_parity`, `black_and_bachelier_agree_atm_and_implied_vols_round_trip`, `implied_vol_outside_no_arb_raises`, `cap_is_sum_of_caplets_and_cap_minus_floor_is_the_swap`, `atm_straddle_is_twice_the_atm_payer` |
| FX | 9 | `fx_forward_is_cip_and_its_basis_is_zero`, `fx_forward_points_follow_the_pip_rule`, `gk_parity_and_delta_bounds`, `gk_implied_vol_round_trips`, `strike_from_delta_round_trips`, `smile_ordering_follows_the_risk_reversal`, `sabr_reproduces_its_quotes`, `carry_table_inverts_usd_base_pairs`, `carry_backtest_is_sane_and_costs_only_hurt` |
| Rate simulation | 5 | `ratesim_is_seeded_and_reproducible`, `ratesim_vasicek_reverts_to_theta`, `ratesim_cir_stays_non_negative`, `ratesim_hull_white_matches_the_curve_at_t0`, `horizon_pv_var_is_a_non_negative_loss` |
| Macro | 3 | `macro_rows_are_bounded_and_regimes_are_from_the_sets`, `macro_briefs_are_json_payloads` (`daily_brief` keys `movers_z` (5), `curve`, `regime`; `weekly_brief` keys `weekly_changes` (18), `curve_report`), `macro_sheet_offline_auto_is_loudly_synthetic_and_fred_raises` |
| Structured | 5 | `ppn_fair_below_issue_with_positive_participation`, `reverse_convertible_coupon_beats_the_zcb_rate`, `dcd_enhanced_yield_beats_the_plain_deposit`, `steepener_note_warns_about_convexity`, `hedge_sheet_sizes_spot_swaps_and_futures` |
| Insights | 3 | `narratives_state_their_numbers`, `weekly_strategy_states_its_views` (`"Duration:"`, `"Curve:"`, `"FX:"`, `"Carry:"`), `report_prompt_and_deep_analysis_degrade_without_network` (prompt ids `"daily_market_commentary"`, `"weekly_fi_fx_strategy"`) |
| Charts | 1 | `every_fchart_renders_a_data_uri_image` (15 charts) |
| Regressions | 2 | `bond_carry_roll_is_a_holding_period_pnl`, `weekly_strategy_names_a_positive_carry_long` |

The macro tests lock the existing Macro sheet's shape: `MacroSheet` has `.rows`, `.sources`, `.regime` (`.curve`, `.risk`, `.dollar`, `.inflation`, `.real_rates`, `.summary`), `.note`, `.as_of`, `.synthetic_ids`, `.row(id)`; `MacroRow` has `z_1y`, `pct_1y`, `chg_3m`, `last_date`, `last`. v2 additions to `core/ficc/macro` must keep these passing.

---

## DI. Data inventory (decides which spec tests can run on local data)

Produced with pandas on 2026-10-05. Nothing under `/home/claude/...` exists on this machine: no `quantgen_macro_data/` (`CATALOG.md`, `scripts/`, `results/`, `QX_*.csv`), no `data_raw/marcap/*.parquet`, no `data_raw/us/*`, no `QC_modules.csv`, no `research_notes/QUANTGEN macro overlay research/`. No parquet engine is installed (`pyarrow` and `fastparquet` absent).

### DI.1 `docs/asset_expansion/cache/*.csv` (46 files, written 2026-09-26 01:28 to 2026-09-27 00:39 local by `docs/asset_expansion_study.py`)

Format: two columns, a date index (ISO `YYYY-MM-DD`; named `Date` for Yahoo, `DATE` for FRED, unnamed for Upbit / Binance) and ONE value column. Read with `pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]`. No OHLC, no volume, no retrieval timestamp inside the file (file mtime is the only retrieval evidence). All indexes are unique and ascending. "max gap" is in calendar days between consecutive rows.

| file | columns (index, value) | rows | first | last | NaN | <=0 | max gap (cal. days) | max abs log-ret | closes adjusted? |
|---|---|---:|---|---|---:|---:|---:|---:|---|
| `binance_BTCUSDT.csv` | `(unnamed)`, `binance_BTCUSDT` | 3327 | 2017-08-17 | 2026-09-25 | 0 | 0 | 1 | 0.503 | n/a: crypto spot close (USDT) |
| `binance_ETHUSDT.csv` | `(unnamed)`, `binance_ETHUSDT` | 3327 | 2017-08-17 | 2026-09-25 | 0 | 0 | 1 | 0.591 | n/a: crypto spot close (USDT) |
| `binance_funding_BTCUSDT.csv` | `(unnamed)`, `0` | 2573 | 2019-09-10 | 2026-09-25 | 0 | 324 | 1 | 5.006 | n/a: daily funding rate (fraction per day), not a price |
| `fred_DEXKOUS.csv` | `DATE`, `DEXKOUS` | 2535 | 2017-01-02 | 2026-09-18 | 109 | 0 | 3 | 0.037 | n/a: FRED noon fixing, KRW per USD |
| `fred_DGS3MO.csv` | `DATE`, `DGS3MO` | 9583 | 1990-01-01 | 2026-09-23 | 395 | 21 | 3 | 3.332 | n/a: FRED yield in PERCENT |
| `upbit_KRW-BTC.csv` | `(unnamed)`, `upbit_KRW-BTC` | 3288 | 2017-09-25 | 2026-09-25 | 0 | 0 | 1 | 0.402 | n/a: crypto spot close (KRW) |
| `yf_000270.KS.csv` | `Date`, `yf_000270.KS` | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 11 | 0.172 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_005380.KS.csv` | `Date`, `yf_005380.KS` | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 11 | 0.191 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_005930.KS.csv` | `Date`, `yf_005930.KS` | 6681 | 2000-01-04 | 2026-09-23 | 0 | 0 | 11 | 0.238 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_005935.KS.csv` | `Date`, `yf_005935.KS` | 5184 | 2005-09-29 | 2026-09-23 | 0 | 0 | 11 | 0.235 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_069500.KS.csv` | `Date`, `yf_069500.KS` | 4274 | 2007-01-29 | 2026-09-23 | 0 | 0 | 800 | 0.217 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_102110.KS.csv` | `Date`, `yf_102110.KS` | 4266 | 2009-04-17 | 2026-09-23 | 0 | 0 | 11 | 0.221 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_122630.KS.csv` | `Date`, `yf_122630.KS` | 4052 | 2010-02-22 | 2026-09-23 | 0 | 0 | 11 | 0.384 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_132030.KS.csv` | `Date`, `yf_132030.KS` | 3900 | 2010-10-01 | 2026-09-23 | 0 | 0 | 11 | 0.138 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_152380.KS.csv` | `Date`, `yf_152380.KS` | 3559 | 2012-01-20 | 2026-09-23 | 0 | 0 | 11 | 0.031 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_229200.KS.csv` | `Date`, `yf_229200.KS` | 2663 | 2015-10-01 | 2026-09-23 | 0 | 0 | 11 | 0.159 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_379800.KS.csv` | `Date`, `yf_379800.KS` | 1315 | 2021-04-09 | 2026-09-23 | 0 | 0 | 8 | 0.083 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_BTC-USD.csv` | `Date`, `yf_BTC-USD` | 4392 | 2014-09-17 | 2026-09-25 | 0 | 0 | 1 | 0.465 | n/a: crypto spot close (USD) |
| `yf_CL_F.csv` | `Date`, `yf_CL=F` | 6551 | 2000-08-23 | 2026-09-25 | 0 | 1 | 5 | 0.602 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_GC_F.csv` | `Date`, `yf_GC=F` | 6543 | 2000-08-30 | 2026-09-25 | 0 | 0 | 5 | 0.114 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_GLD.csv` | `Date`, `yf_GLD` | 5497 | 2004-11-18 | 2026-09-25 | 0 | 0 | 5 | 0.108 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_HG_F.csv` | `Date`, `yf_HG=F` | 6547 | 2000-08-30 | 2026-09-25 | 0 | 0 | 5 | 0.252 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_IAU.csv` | `Date`, `yf_IAU` | 5449 | 2005-01-28 | 2026-09-25 | 0 | 0 | 5 | 0.111 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_NG_F.csv` | `Date`, `yf_NG=F` | 6548 | 2000-08-30 | 2026-09-25 | 0 | 0 | 5 | 0.644 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_QQQ.csv` | `Date`, `yf_QQQ` | 6930 | 1999-03-10 | 2026-09-25 | 0 | 0 | 7 | 0.156 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_SI_F.csv` | `Date`, `yf_SI=F` | 6544 | 2000-08-30 | 2026-09-25 | 0 | 0 | 5 | 0.376 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_SPY.csv` | `Date`, `yf_SPY` | 7986 | 1995-01-03 | 2026-09-25 | 0 | 0 | 7 | 0.136 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_TLT.csv` | `Date`, `yf_TLT` | 6079 | 2002-07-30 | 2026-09-25 | 0 | 0 | 5 | 0.073 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_VIXY.csv` | `Date`, `yf_VIXY` | 3955 | 2011-01-04 | 2026-09-25 | 0 | 0 | 5 | 0.358 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLB.csv` | `Date`, `yf_XLB` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.133 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLE.csv` | `Date`, `yf_XLE` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.225 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLF.csv` | `Date`, `yf_XLF` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.182 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLI.csv` | `Date`, `yf_XLI` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.120 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLK.csv` | `Date`, `yf_XLK` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.149 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLP.csv` | `Date`, `yf_XLP` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.099 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLU.csv` | `Date`, `yf_XLU` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.121 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLV.csv` | `Date`, `yf_XLV` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.114 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_XLY.csv` | `Date`, `yf_XLY` | 6982 | 1998-12-22 | 2026-09-25 | 0 | 0 | 7 | 0.135 | YES: auto_adjust=True (splits AND dividends, total return) |
| `yf_ZB_F.csv` | `Date`, `yf_ZB=F` | 6538 | 2000-09-21 | 2026-09-25 | 0 | 0 | 5 | 0.099 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_ZC_F.csv` | `Date`, `yf_ZC=F` | 6554 | 2000-07-17 | 2026-09-25 | 0 | 0 | 14 | 0.269 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_ZF_F.csv` | `Date`, `yf_ZF=F` | 6544 | 2000-09-21 | 2026-09-25 | 0 | 0 | 5 | 0.021 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_ZN_F.csv` | `Date`, `yf_ZN=F` | 6532 | 2000-09-21 | 2026-09-25 | 0 | 0 | 12 | 0.035 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf_ZS_F.csv` | `Date`, `yf_ZS=F` | 6546 | 2000-09-15 | 2026-09-25 | 0 | 0 | 5 | 0.234 | NO: Yahoo continuous front future, not roll-adjusted |
| `yf__KS200.csv` | `Date`, `yf_^KS200` | 1 | 2026-09-23 | 2026-09-23 | 0 | 0 |  |  | n/a: index level |
| `yf__VIX.csv` | `Date`, `yf_^VIX` | 7988 | 1995-01-03 | 2026-09-25 | 0 | 0 | 7 | 0.768 | n/a: index level |
| `yf__VIX3M.csv` | `Date`, `yf_^VIX3M` | 5081 | 2006-07-17 | 2026-09-25 | 0 | 0 | 5 | 0.502 | n/a: index level |

Notes that change what a test may assume:
- Adjusted status: every `yf_<equity or ETF>` file is Yahoo `Close` with `auto_adjust=True` (asset_expansion_study.py:85), that is, adjusted for splits AND dividends = `History.adjustment == "total"`. The tech-fund labs state "All lab numbers are in-sample computations on price returns without dividends" (bundle README), so local Yahoo closes are NOT the labs' convention; and the macro spec's goldens are on KRX official closes and index levels. Local equity/ETF files therefore reproduce neither set of goldens to Level-1 tolerance.
- `yf_069500.KS.csv` (KODEX 200): 800-calendar-day hole between 2007-02-07 and 2009-04-17; continuous only from 2009-04-17 (`validate.data_checks` reports it as `"gap of 800 calendar days inside the series"`).
- `yf__KS200.csv` holds ONE row (2026-09-23, 1126.12). There is no `^KS11` (KOSPI) file. No KOSPI index history exists locally.
- `yf_CL_F.csv` contains one non-positive close (2020-04-20, -37.63); `_clean_rows` and the study's loader drop it; log returns across it are undefined.
- `yf_VIXY.csv` is reverse-split adjusted (first value 633,840; last 16.66).
- `yf_122630.KS.csv` (KODEX leverage) has five daily log moves beyond 0.2 in 2026 (2026-03-04, 06-23, 07-13, 07-28, 07-31), consistent with the 2026 KOSPI episode the specs describe; they are data, not errors.
- `fred_DEXKOUS.csv` and `fred_DGS3MO.csv` KEEP the NaN rows FRED returns for no-observation dates (109 and 395). In 2026 the DEXKOUS NaN dates are 2026-01-01, 01-19, 02-16, 05-25, 06-19, 07-03, 09-07 (US holidays). These rows are the only local evidence of "source-skipped" dates. `fred_DGS3MO.csv` also has 21 zero values (percent units).
- `binance_funding_BTCUSDT.csv`: column name is the literal `0`; values are daily sums of funding (fractions); 324 non-positive days are negative funding, not errors.
- Last dates: US Yahoo and crypto 2026-09-25; KRX Yahoo 2026-09-23; DGS3MO 2026-09-23; DEXKOUS 2026-09-18. Nothing covers 2026-09-29, 2026-09-30 or 2026-10-02, the dates the spec fixtures end on.
- Calendar-day series (crypto) include weekends (950, 938, 1254 weekend rows); joining them to weekday series needs an as-of rule.

### DI.2 Tech-fund lab outputs: `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/datalab/` (76 CSV and 3 JSON under `results/`, `verification/` and the datalab root)

These are RESULTS (metrics, verdicts, registers), not raw series. Integrity: `results/r2_kr/r2_kr_hashes.csv` lists sha256 and byte size for 27 files and all 27 match the local copies; `results/r2_idx/r2_idx_validation.csv` (rows `V8`) lists sha256 for 21 result files, 20 match and `r2_idx_claims.csv` does NOT match (local sha256 `66989ace0027388331252da66ed356c968b204c095ba35fb64e0c0f0c41906a9`, recorded `e8a4341764bb6d2fafd9b38e3b9674498b16fdaac02a7c09b6467c4bbee70b67`; no CRLF difference; no entry in `qa/qa_edit_log.json`); the three `charts/*.json` files it lists are not in the bundle.

| file (under datalab/) | rows | cols | columns | description |
|---|---:|---:|---|---|
| `results/kr/kr_index_spa.csv` | 126 | 3 | section, key, value | Hansen SPA test (arch SPA) over the 303-variant KOSPI timing-rule family, 1996-06-03..2026-09-29, net 3 bp/side, cash 0%; key/value settings and results. |
| `results/kr/kr_index_timing.csv` | 1188 | 5 | rule, cost_level, period, metric, value | Long table: KOSPI index timing rules (Buy & hold, SMA/TSM variants) x cost_level x period x metric (cagr, total_return, ann_vol, ...). |
| `results/kr/kr_key_numbers.csv` | 36 | 21 | signal, universe, weighting, ls_gross_ann, ls_gross_sharpe, ls_gross_nw_t, ls_net35_sharpe, ls_net70_sharpe, lo_net35_ann, lo_net35_sharpe, lo_net35_maxdd, lo_xs_net35_ann, ... (+9 more) | KRX cross-sectional sorts (MOM_12_1, MOM_6_1, ... x universe x EW/VW): L/S gross and net-35/70 bp Sharpe, long-only excess, turnover, positive-year share. |
| `results/kr/kr_validation.csv` | 68 | 5 | test, item, value, passed, note | Round-1 KRX lab validation checks (V0..: share-class code hygiene, look-ahead, engine); passed flags. |
| `results/r2_idx/r2_idx_averaging_autocorr.csv` | 6 | 6 | sample, acf1_month_end, acf1_month_average, acf1_shiller_price, vol_month_end, vol_month_average | ACF(1) and vol of monthly returns, month-end vs month-average prices (SPY, S&P 500, Shiller): averaging-bias diagnostic. |
| `results/r2_idx/r2_idx_averaging_bias.csv` | 15 | 23 | comparison, rule, sharpe_avg, sharpe_me, sharpe_bh_avg, sharpe_bh_me, max_dd_avg, max_dd_me, max_dd_bh_avg, max_dd_bh_me, cagr_avg, cagr_me, ... (+11 more) | Timing-rule Sharpe/MDD/CAGR on month-average vs month-end data; sharpe_inflation, timing_benefit_inflation, mdd_understatement_pp. |
| `results/r2_idx/r2_idx_averaging_meta.csv` | 5 | 2 | item, value | Data spans of the averaging study (shiller_last_dividend_month 2023-06, spy_first 1998-01-02, spy_last 2021-03-31). |
| `results/r2_idx/r2_idx_averaging_rules.csv` | 124 | 12 | source, window, rule, n_months, mean_ann, vol_ann, sharpe, cagr, max_dd, acf1, time_in_market, switches_per_year | Monthly timing rules (buy-and-hold, SMA10, TSM12, ...) per source/window: mean, vol, Sharpe, CAGR, MDD, acf1, time in market, switches/yr. |
| `results/r2_idx/r2_idx_claims.csv` | 9 | 6 | id, claim, claimed, ours, status, reason | Nine executive (E1/E3) claims re-checked: claimed vs ours, status (CONFIRMED ...). NOTE: local sha256 differs from the hash recorded in r2_idx_validation.csv V8. |
| `results/r2_idx/r2_idx_e1_checks.csv` | 10 | 10 | source, window, rule_mean, rule_vol, rule_rv, rule_mdd, bh_mean, bh_vol, bh_rv, bh_mdd | E1 Shiller 12-month-sign rule vs buy-and-hold by window (mean, vol, return/vol, MDD). |
| `results/r2_idx/r2_idx_e3_checks.csv` | 24 | 5 | window, claim, e3_value, ours, note | E3 (CTA) KOSPI/SPY trend claims vs lab recomputation, per window. |
| `results/r2_idx/r2_idx_gate_power_years.csv` | 780 | 9 | innovations, true_sr, rho, n_trials, step, years_50pct, years_50pct_txt, years_80pct, years_80pct_txt | Years of history needed for 50% / 80% gate pass probability by innovations, true_sr, rho, n_trials, step. |
| `results/r2_idx/r2_idx_gate_sim.csv` | 8580 | 10 | innovations, years, true_sr, rho, n_trials, step, pass_rate, mc_se, n_paths, analytic_iid | Simulated gate pass rates per step (step2_bootstrap, step2_lo_iid, step8_years, joint_2_3_5_8, ...) by innovations (iid_normal, kospi_cbb126, ...), years, true_sr, rho, n_trials; mc_se, n_paths 2000, analytic_iid. |
| `results/r2_idx/r2_idx_gate_source_diagnostics.csv` | 9 | 2 | item, value | Moments of the bootstrap source series for the gate simulation (source_obs 7912, ann_vol 0.15, skew ...). |
| `results/r2_idx/r2_idx_gate_step5_calibration.csv` | 99 | 7 | innovations, years, rho, share_p_le_0p10, share_p_le_0p05, mean_p, n_paths | Null size of the step-5 benchmark p-value (share p<=0.10 / <=0.05, mean p) by innovations/years/rho. |
| `results/r2_idx/r2_idx_golden_values.csv` | 30 | 8 | item, ours, spec, gap, level1_tol, level2_tol, within_level1, within_level2 | Macro spec 9.3 KOSPI VT20 goldens on the REBUILT KOSPI 2016-01-04..2026-09-29: ours vs spec, gap, level1_tol, level2_tol, within flags (30/30 within both). |
| `results/r2_idx/r2_idx_key_numbers.csv` | 17 | 3 | item, value, source | Headline protective-card numbers per KOSPI/SPY rule (dMDD vs S, tail ratio, DSR vs S with p, episodes) with source file. |
| `results/r2_idx/r2_idx_outperformance.csv` | 21 | 28 | market, book, rule_id, rule, set, start, end, sharpe_rule_1x, sharpe_rule_2x, sharpe_buy_hold, dsr_vs_S_1x, o_step5_p_block10, ... (+16 more) | CARD-O (beats buy-and-hold) per market/book/rule: Sharpe at 1x/2x cost, dsr_vs_S, step-5 p (block 10 and Politis-White block), step-2 CI, years positive, cardO_verdict. |
| `results/r2_idx/r2_idx_overlay_vs_sleeve.csv` | 36 | 32 | market, book, trend, form, rule, avg_exposure, min_exposure, sharpe_1x, dsr_vs_S_1x, mdd_1x, mdd_S, mdd_buy_hold, ... (+20 more) | Trend rule as sleeve (0 allowed) vs overlay clip[0.5,1] vs 0.5+0.5x: exposure, Sharpe, MDD vs static comparator S, PC-1..PC-5, verdict, episode and 2026 window returns. |
| `results/r2_idx/r2_idx_plateau_neighbours.csv` | 102 | 12 | market, centre, neighbour, avg_exposure, sharpe_1x, mdd_1x, mdd_S, dmdd_pp_1x, dsr_vs_S_1x, keeps, book, rule_id | PC-6 plateau: neighbour parameterisations of each centre rule (avg_exposure, sharpe_1x, mdd, dmdd_pp_1x, dsr_vs_S_1x, keeps). |
| `results/r2_idx/r2_idx_protective_episodes.csv` | 161 | 13 | episode, start_return, end_return, n_days, rule_return, S_return, buy_hold_return, benefit_vs_S, market, rule, cost_1x_bp, book, ... (+1 more) | Per drawdown episode x rule: rule_return, S_return (static same-exposure comparator), buy_hold_return, benefit_vs_S. |
| `results/r2_idx/r2_idx_protective_scorecard.csv` | 21 | 93 | market, rule, start, end, n_sessions, cost_1x_bp, cost_2x_bp, avg_exposure, turnover_per_year, cost_drag_1x_pct_yr, sharpe_rule_gross, mdd_rule_gross, ... (+81 more) | Full CARD-P scorecard per market x rule (KOSPI/SPY; SMA200, ENS, TSM12, VT20 ...): gross/1x/2x stats, comparator S, PC-1..PC-7, O-steps 2/3/5/6, de-clustered onsets, verdict / verdict_if_sufficient / cardO_verdict. |
| `results/r2_idx/r2_idx_r4b_crosscheck.csv` | 12 | 6 | item, ours, r4b, gap, tol, within | Reproduction of macro R4b Korea VT20 protective card: ours vs r4b, gap, tol, within (12 items). |
| `results/r2_idx/r2_idx_start_date_sensitivity.csv` | 80 | 34 | market, rule, start, end, n_sessions, avg_exposure, sharpe_rule_1x, sharpe_buy_hold, mdd_rule_1x, mdd_S, mdd_buy_hold, pc1_dmdd_pp_1x, ... (+22 more) | Scorecard subset re-run from alternative start dates (primary flag marks the main run). |
| `results/r2_idx/r2_idx_validation.csv` | 38 | 4 | test, what, passed, detail | V1-V8: perturbation no-look-ahead tests (265/265), planted look-ahead detected, t+1 earning, cost timing, golden reproduction 30/30, seed-11 rerun identity, sha256 of every r2_idx result/chart file. |
| `results/r2_idx/r2_idx_windows.csv` | 189 | 12 | market, book, rule_id, rule, window, first_return, last_return, cum_return, S_cum_return, buy_hold, avg_exposure_in_window, exposure_first_day | Cumulative return of each rule vs S vs buy-and-hold in named windows (2026 melt-up / crash / rebound ...), exposure in window. |
| `results/r2_kr/r2_kr_crash_controls.csv` | 2736 | 6 | sleeve, control, cost, period, metric, value | Long table: momentum sleeves x crash control (static, VS own-vol 12% cap 1, DM gate floor 0.5, ...) x cost x period x metric. |
| `results/r2_kr/r2_kr_crash_exposure_2026.csv` | 24 | 8 | sleeve, control, s_on_2026_06_22, s_on_2026_06_30, min_s_june_2026, first_cut_in_2026, cut_before_2026_07_01, sigma126_on_2026_06_22 | Scale s of each crash control on 2026-06-22 / 06-30, min in June, first cut date in 2026, sigma126. |
| `results/r2_kr/r2_kr_crash_windows.csv` | 318 | 4 | sleeve, control, window, cum_return_net35 | Net-35 bp cumulative return of sleeve x control in named crash/rebound windows. |
| `results/r2_kr/r2_kr_dm_gate_onsets.csv` | 9 | 1 | onset | Daniel-Moskowitz gate onset dates (9). |
| `results/r2_kr/r2_kr_dm_gate_sample.csv` | 377 | 7 | date, r24, sig_mkt, q23, bear, hivol, dm | DM-gate state per formation date: r24, sig_mkt, q23, bear, hivol, dm multiplier. |
| `results/r2_kr/r2_kr_excl_dsr_best.csv` | 1 | 10 | best_trial, ir_ann, sr_monthly, n_trials, dsr_pooled_variance, sr0_monthly_pooled, dsr_per_base_variance, sr0_monthly_per_base, dsr_null_variance, sr0_monthly_null | Deflated Sharpe of the best exclusion trial (trial id `B1\|F4_cut5`, 176 trials) under pooled / per-base / null trial-variance conventions. |
| `results/r2_kr/r2_kr_excl_f6_diagnostic.csv` | 1 | 6 | name_months_literal, name_months_netissuance, both, literal_only, netissuance_only, share_literal_not_confirmed | Overlap of literal vs net-issuance dilution flags (name-months). |
| `results/r2_kr/r2_kr_excl_gate.csv` | 8 | 41 | base, rank, filter, ann_diff_net35, ir_net35, n_trials, var_trial_sr_monthly, steps_passed, verdict, g1_walkforward_selected_oos_ir, g1_pass, g2_lo_ir, ... (+29 more) | Gate steps g1..g9 on exclusion filters per base book (B1/B2/..., F4/F1): walk-forward IR, Lo/bootstrap CI, DSR (3 conventions), PBO, bootstrap p, 2x-cost, plateau, years positive, haircut; verdict (REVISE). |
| `results/r2_kr/r2_kr_excl_jaccard.csv` | 64 | 5 | filter_a, filter_b, jaccard_mean, jaccard_2016_2026, share_of_ALL_a | Pairwise Jaccard overlap of exclusion filters F1..F8 (mean and 2016-2026). |
| `results/r2_kr/r2_kr_excl_limitlock.csv` | 8 | 8 | base, filter, entries, entries_at_locked_limit_up, share_entries_locked, exits, exits_at_locked_limit_down, share_exits_locked | Share of entries at locked limit-up and exits at locked limit-down per base/filter. |
| `results/r2_kr/r2_kr_excl_long.csv` | 35904 | 8 | base, filter, family, primary, cost, period, metric, value | Long table of every exclusion trial x cost x period x metric (ann_diff, te, ir, ...). |
| `results/r2_kr/r2_kr_excl_summary.csv` | 528 | 28 | base, filter, family, primary, cost, ann_diff, te, ir, nw_t, sharpe_filtered, sharpe_unfiltered, cagr_filtered, ... (+16 more) | Per base x filter x cost (gross/net35/net70): ann_diff, te, ir, nw_t, Sharpe and CAGR filtered vs unfiltered, MDD, turnover, bootstrap p and CI90, years positive, excluded shares. |
| `results/r2_kr/r2_kr_excl_thin_books.csv` | 17 | 3 | book, months_suspended, months_lt20_names | Books with suspended months or months with fewer than 20 names. |
| `results/r2_kr/r2_kr_excl_trials.csv` | 176 | 5 | base, filter, family, primary, ir_net35 | The 176-trial ledger of the exclusion study (base, filter, family, primary, ir_net35). |
| `results/r2_kr/r2_kr_excl_windows.csv` | 1232 | 6 | base, filter, window, filtered, unfiltered, diff | Filtered vs unfiltered book return in named crash/rebound windows. |
| `results/r2_kr/r2_kr_excl_years.csv` | 5456 | 6 | base, filter, year, diff, filtered, unfiltered | Calendar-year filtered / unfiltered / diff per base x filter. |
| `results/r2_kr/r2_kr_hashes.csv` | 27 | 3 | file, sha256, bytes | sha256 and byte size of every r2_kr result file (27/27 verified against the local copies). |
| `results/r2_kr/r2_kr_lowvol.csv` | 48 | 24 | book, cost, period, market, beta, beta_t, alpha_ann_rf0, alpha_t, r2, alpha_ann_if_rf2pct, alpha_ann_if_rf4pct, book_ann_mean, ... (+12 more) | Low-vol Q1 book vs market proxies: beta, alpha at rf 0/2/4%, captures, turnover, by cost/period. |
| `results/r2_kr/r2_kr_lowvol_windows.csv` | 24 | 9 | book, window, kind, book_return, vw_universe, ew_universe, kospi_rebuilt, book_minus_vw, book_minus_ew | Low-vol book in crash/rebound windows vs VW/EW universe and rebuilt KOSPI. |
| `results/r2_kr/r2_kr_mom_claims_long.csv` | 779 | 4 | claim, variant, metric, value | Long table: reproductions of published KRX momentum claims (KJFS / Eom design ...), variant x metric. |
| `results/r2_kr/r2_kr_mom_e7_ladder.csv` | 13 | 11 | step, group, ann_excess_net35, t, ann_excess_gross, n_days, avg_names, one_way_turnover_per_year, n_months, pct_pos_years, note | Step ladder from the E7 momentum construction to the lab construction (ann_excess_net35, t, names, turnover). |
| `results/r2_kr/r2_kr_mom_grid_long.csv` | 24304 | 8 | signal, turn_def, tercile, weighting, leg, period, metric, value | Long table: momentum signal x turnover definition x tercile x weighting x leg x period x metric. |
| `results/r2_kr/r2_kr_mom_kjfs_events.csv` | 40 | 11 | formation, code, name, contribution_to_leg_month, leg_month_return, event_day, unadjusted_day_return, krx_changesratio, cleaned_return, krx_adjustment_day, member_at_formation | Largest single-name contributions / corporate-action days in the KJFS replication (unadjusted vs KRX-adjusted returns). |
| `results/r2_kr/r2_kr_reproduce_r1.csv` | 26 | 8 | test, item, round2, round1, abs_diff, tol, passed, note | Round-2 reproduction of round-1 numbers at tol 1e-6 (26/26 passed). |
| `results/r2_kr/r2_kr_reversal.csv` | 120 | 14 | universe, weighting, sort, cost, period, mean_pct_month, nw_t, ann_mean, sharpe, max_dd, turnover_per_year, pct_pos_years, ... (+2 more) | Short-term reversal sorts by universe x weighting x sort x cost x period. |
| `results/r2_kr/r2_kr_stoploss.csv` | 32 | 13 | sleeve, weighting, cost, variant, sharpe, ann_mean, max_dd, worst_month, sharpe_2016_2026, stops_long, stops_short, turnover_per_year, ... (+1 more) | Stop-loss variants on momentum sleeves (no stop; 15% stop exit next close; ...): Sharpe, MDD, worst month, stops, turnover. |
| `results/r2_kr/r2_kr_stoploss_engine_check.csv` | 2 | 3 | check, run_books, stop_engine | Stop engine equals run_books with stops off (2 checks). |
| `results/r2_kr/r2_kr_validation.csv` | 16 | 5 | test, item, value, passed, note | Round-2 KR validation W0..: round-1 reproduction 26/26, formation arrays recomputed identical, etc. |
| `results/r3/R3_TF_edges.csv` | 85 | 5 | edge_id, source, target, type, reason | Edges of the R3 neural-link map: source node, target node, type (supports / refutes / qualifies), reason. |
| `results/r3/R3_TF_nodes.csv` | 70 | 32 | node_id, theme, label, fp, fe, fp_ledger, fp_other, fe_ledger, fe_other, prof_members, exec_members, ps, ... (+20 more) | Nodes TF-01..TF-70: theme, label, focus counts, evidence class, ruling (CR-xx), destination (SPEC section), decision, key_numbers, settling_test, claim and test ids. |
| `results/r3/r3_focus_by_theme.json` | 1 keys | - | JSON dict: by_theme | Focus counts per theme A.. (fp, fe, n). |
| `results/r3/r3_go_nogo.csv` | 77 | 11 | id, item, market, decision, ruling, evidence_for, evidence_against, indicative_gate, what_would_change_it, nodes, target | Go/no-go register G-01..G-77: item, market, decision, ruling, evidence_for / against, indicative_gate, what_would_change_it, nodes, target (spec section). |
| `results/r3/r3_golden_values.csv` | 523 | 13 | gv_id, card_or_rule, decision, quantity, market, period, gross_net, value, raw, source_file, line, status, ... (+1 more) | GV-001..GV-523: card_or_rule, decision, quantity, market, period, gross_net, value (display string), raw (number), source_file, line, status (497 traced / 20 derived / 6 not traced). |
| `results/r3/r3_ledger_claims.json` | 414 keys | - | JSON dict: E1-C01, E1-C02, E1-C03, E1-C04, E1-C05, ... (+409 more) | 414 claim ids (E1-C01 .. P7-..) -> claim record. Record keys: paper, claim, evidence, tier, implication, urls. |
| `results/r3/r3_pair_share.csv` | 8 | 12 | date, n_kospi_lines, n_common_lines, samsung_common_krw, samsung_pref_krw, skhynix_krw, kospi_all_lines_krw, kospi_common_only_krw, CR07_pair_incl_pref_over_all_lines, alt_pair_common_over_all_lines, alt_pair_common_over_common_only, alt_pair_incl_pref_over_common_plus_pref | Samsung Electronics (+pref) + SK hynix share of KOSPI market cap at year-ends: CR-07 definition and three alternatives. |
| `results/r3/r3_pair_share_2026_daily.csv` | 181 | 5 | Date, cr07_pair_share, alt_pair_common_over_all_lines, alt_pair_common_over_common_only, alt_pair_incl_pref_over_common_plus_pref | Daily 2026 pair share, 2026-01-02..2026-09-29 (CR-07 and alternatives). |
| `results/r3/r3_pair_share_summary.csv` | 16 | 2 | item, value | Summary items (CR-07 share on 2026-09-29 = 0.537062; first session > 0.45 = 2026-05-06 at 0.470159; ...). |
| `results/r3/r3_weights_final.csv` | 50 | 10 | market, family, column, prior, professors, executives, final, rule, reason, nodes | Final per-market family weights: market, family, column (alpha / ...), prior, professors, executives, final, rule (W1..), reason, nodes. |
| `results/r3/r3_weights_other_markets.csv` | 6 | 10 | market, XS-mom, ST-rev, value, quality, low-vol, flow, earn drift, TS-mom, exec TS trend alpha / protective | Family weights for the other markets (Europe, Japan, Taiwan, ...) across XS-mom, ST-rev, value, quality, low-vol, flow, earn drift, TS-mom. |
| `results/us/us_A4_valuation.csv` | 1588 | 6 | test, series, period, cost_level, metric, value | Long table: CAPE valuation regressions and valuation-timing tests (Shiller data). |
| `results/us/us_A_timing.csv` | 13579 | 6 | test, series, period, cost_level, metric, value | Long table: Shiller monthly 1872-03..2026-09 timing rules (BH, SMA, TSM ...) by cash convention, period, cost level. |
| `results/us/us_B_daily.csv` | 9958 | 6 | test, series, period, cost_level, metric, value | Long table: SPY daily rule family (322 variants), evaluation 1999-01-05..2021-03-31 (5596 days). |
| `results/us/us_C_factors.csv` | 2484 | 6 | test, series, period, cost_level, metric, value | Long table: French factor tests (archive 1926-07..2018-11): FM slopes, GRS, momentum etc. |
| `results/us/us_D_factor_etfs.csv` | 35 | 6 | test, series, period, cost_level, metric, value | Factor ETF 1-year and quarterly returns 2025-10..2026-10 (spliced). |
| `results/us/us_D_stocklake_closes_raw.csv` | 102 | 4 | symbol, date, close, note | Raw closes behind us_D (first bar and month-ends, 2025-04..). |
| `results/us/us_validation.csv` | 53 | 6 | test, series, period, cost_level, metric, value | US lab validation (signals use only data up to t; position t = signal t-1; ...). |
| `verification/exec_claim_matrix.csv` | 60 | 12 | prop_id, domain, proposition, supporting_claims, qualifying_or_contradicting_claims, holders_for, holders_against_or_qualifying, data_evidence, verification, panel_status, triage, resolution_item | X01..X60 propositions of the executive panel: supporting / contradicting claims, holders, data evidence, verification, panel_status, triage, resolution_item. |
| `verification/exec_verification_log.csv` | 103 | 10 | row, claim_id, paper, reviewer, number_as_printed, how_checked, value_found, status, consequence, source_tier_of_claim | Row-by-row recomputation log of executive claims: number_as_printed, how_checked, value_found, status (MATCH ...), consequence. |
| `verification/prof_claim_matrix.csv` | 60 | 12 | prop_id, domain, proposition, supporting_claims, contradicting_or_qualifying_claims, members_holding, members_dissenting, datalab_evidence_R1_and_R2, chair_verification_refs, panel_status, resolution_id, quantgen_implication | PM01..PM60 propositions of the professor panel with datalab evidence, verification refs, panel_status, resolution_id, quantgen_implication. |
| `verification/prof_cross_exam_verdicts.csv` | 209 | 6 | claim_id, paper, reviewer, claim, verdict, basis | Per-claim cross-examination verdict (CONFIRMED / UNVERIFIED / ...) with basis. |
| `verification/prof_v04_weekly_reversal.csv` | 72 | 11 | universe, tails, design, period, gross_pct_wk, t, SR_gross, net35_pct_wk, SR_net35, TO_wk, weeks | Weekly reversal check by universe/tails/design/period: gross vs net-35 bp %/week, t, Sharpe, turnover. |
| `verification/prof_verification_log.csv` | 118 | 9 | log_id, paper, claim_id, reviewer, number_as_printed, how_checked, value_found, status, consequence | V001.. verification log of professor claims: number_as_printed, how_checked, value_found, status, consequence. |
| `quantgen_strategy_lab_cards.json` | 4 keys | - | JSON dict: counts, strategies, fans, monitors | Snapshot of the QUANTGEN Strategy-Lab record used as context (counts: pass 5, revise 11, reject 18, insufficient 0; the bundle README calls it the 16-card Strategy Lab record). List lengths: strategies 16, fans 9, monitors 5. |

Golden-value facts:
- `results/r3/r3_golden_values.csv`: 523 rows; `status` counts `traced` 497, `derived` 20, `not traced` 6. `source_file` uses lab paths; map them to the bundle as `r2/kr/results/` -> `results/r2_kr/`, `r2/idx/results/` -> `results/r2_idx/`, `kr/results/` -> `results/kr/`, `us/results/` -> `results/us/`, `r3/results/` -> `results/r3/`, `r2/verification/` -> `verification/`. Of 36 distinct source files, 30 are local. Missing: `r2/verification/exec_chair_checks/c12_lowvol_samebeta.csv` (21 values, the S_beta low-vol comparator), `kr/results/kr_index_sanity.csv` (10 values), three `research_notes/QUANTGEN technical and fundamental signals/*.md` paths (4 values; the same documents are in the bundle under `research_notes/`), and `-` (6 values).
- `market` counts: `KRX` 319, `KOSPI (rebuilt)` 135, `SPY` 32, `simulated` 13, `KOSPI` 10, `US` 7, `-` 6, `crypto` 1. `gross_net` strings include `net 35 bp/side`, `net 3 bp/side (KRX ETF)`, `net KRX ETF 3bp`, `net US via KIS 50bp`, `net 70 bp/side (2x)`, `gross`.
- `results/r2_idx/r2_idx_golden_values.csv`: the macro spec section 9.3 KOSPI VT20 goldens (2016-01-04 to 2026-09-29, rebuilt KOSPI), with tolerances per row: `level1_tol` 0.01 (Sharpe, drawdown, window returns), 0.02 (average exposure, weights), 1.00 pp (dMDD); `level2_tol` 0.03 / 0.02 / 1.50. Spec values: VT20 Sharpe gross 0.638 (ours 0.632912), buy-and-hold Sharpe 0.634, VT20 max DD -0.368, buy-and-hold max DD -0.439, VT20 average exposure 0.925, static S max DD -0.413, dMDD VT20 vs S gross 4.5 pp, VT20 Sharpe net 3 bp 0.635, net 6 bp 0.632, dMDD net 3 bp 4.4 pp, dSR VT20 minus buy-and-hold 0.004, VT20 weight earning on 2026-06-22 0.3024, on 2026-06-23 0.3309, on 2026-07-30 0.2484, Jul-2026 crash window VT20 -0.122 vs buy-and-hold -0.386.
- `results/r3/r3_go_nogo.csv` `target` values point at sections `§TF-1` to `§TF-7` of `QUANTGEN_TECHFUND_INTEGRATION.md`, which is NOT in the bundle (only `research_notes/R3_TF_neural_link.md` and its inputs are). See F.2.

### DI.3 Spec fixtures against local data

Spec fixture list: spec 6018 (manifest) and 6022-6033 (acquisition register).

| Fixture the specs name | Local? | Nearest local file | What it can honestly support |
|---|---|---|---|
| KRX official KOSPI daily closes from 1997-01-03, Saturday sessions included | NO | none | nothing; the 30 VT20 goldens exist only as numbers (DI.2) |
| ECOS call rate (`BOK_CALL_RATE`); FRED `IRSTCI01KRM156N` monthly cash fixture | NO | none (`fred_DGS3MO.csv` is USD) | nothing |
| KODEX 200 PDF and constituents, iNAV, the 15:19 snapshots, daily opens | NO | `yf_069500.KS.csv` (adjusted close only) | synthetic-shape unit tests only |
| VIXCLS / VXVCLS | NO | `yf__VIX.csv` (1995-01-03 to 2026-09-25), `yf__VIX3M.csv` (2006-07-17 to 2026-09-25) | unit tests of ratio / label logic; not goldens |
| SOX, the six trend indices, Yahoo `^KS11`, `^GSPC`, `KRW=X`, `^TNX`, `^RUT` | NO | none | nothing |
| Yahoo SPY | PARTIAL | `yf_SPY.csv` 1995-01-03 to 2026-09-25, total-return adjusted | indicative US vol-target runs; not md5-equal to a 2026-10-02 fixture |
| French daily and monthly files (Mom, Mkt-RF, RF) | NO | none (`results/us/us_C_factors.csv` holds metrics only) | lookups of printed results only |
| FRED snapshot of 2026-10-02 (`DGS10`, `DTWEXBGS`, `DEXKOUS`, ...) | PARTIAL | `fred_DEXKOUS.csv` 2017-01-02 to 2026-09-18 with NaN rows; `fred_DGS3MO.csv` | the staleness RULE on a sub-span; not T-STALE-01's counts (its window is 2016-01-04 to 2026-09-25 and needs `DTWEXBGS`) |
| `QX_DLA_postpatch.csv`, `QX_DLA_korea_grid.csv`, `QX_EX1_qf3_trial_corr_diff.csv`, the DLB CSVs, the source-skipped list | NO | none | nothing (T-NEFF-01, G-KR-*, G-US-*, G-EST-* cannot be recomputed) |
| The synthetic store fixture of T-PROV-01 | build it | values are printed in spec 5612 | runnable now |
| KRX marcap parquet (tech-fund labs) | NO, and no parquet reader | none | SCR-1 / SCR-2 / INV-1 / INV-2 formulas on synthetic panels only |
| Shiller monthly, `spy_lean_daily.zip`, `vix_daily.csv` (tech-fund US lab) | NO | `yf_SPY.csv`, `yf__VIX.csv` | indicative only (different return convention) |
| Crypto daily closes and funding | YES | `binance_BTCUSDT.csv`, `binance_ETHUSDT.csv`, `upbit_KRW-BTC.csv`, `yf_BTC-USD.csv`, `binance_funding_BTCUSDT.csv` | T-CRYPTO-01 style conventions (UTC bar close, 365-day annualisation, as-of joins to weekday data) |

Classes of spec test by what they need:

| Class | Needs | Runnable on this machine now |
|---|---|---|
| Static and structural (T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-DNB-01, T-OWNER-01, T-BOOK-01 header clauses, T-COST-02/03) | code only | YES |
| Property and logic on synthetic input (T-CAP-01/02, T-LAG-01/02, T-SYN-01, T-PROV-01, T-FIX-01, T-ROLE-01, T-PZERO-01, T-PRIOR-01, I-04b on a synthetic NAV path, T-CRYPTO-01, the engine hooks, the fill model's limit-lock rule) | values printed in the spec text | YES |
| Published-example checks (T-DSR-01: 0.9505 at N 46, 0.9004 at N 100) | numbers printed in the spec | YES (inputs must be taken from the spec's rule table) |
| Calendar rules (T-CLOSE-02, T-SAT-01, T-REGIME-01, T-CAL-01) | effective-dated calendar data typed from official notices | PARTIAL: rule logic yes; shipped calendars cover only 2026-01-01 to 2027-12-31 |
| Fixture-lookup consistency (each traced `GV-nnn` equals the cell in its local source CSV; sha256 lists) | tech-fund CSVs | YES for 497 traced rows minus those whose source file is missing |
| Golden reproductions from raw series (G-KR-*, G-US-*, G-MOM-*, G-EST-*, T-R03-01, T-NEFF-01, I-07, I-08, I-09, I-16, T-STALE-01 counts, the tech-fund screens' excess returns) | raw reference data | NO |

---

## D. Extension points for v2

### D.1 Where the specs' test plan lands in this harness

| Spec requirement | Source | What exists | Smallest fit |
|---|---|---|---|
| Macro tests run inside `tests/run_all.py`, hermetic | spec 5489-5493, 919 | six suites, one registry function per suite (A.1) | one new suite module per programme (for example `tests/macro_acceptance.py`, `tests/techfund_acceptance.py`), each exporting `tests()`; two lines each in `run_all.py:30-44` |
| Fixtures in `tests/fixtures/macro/` with `MANIFEST.csv` (one row per file: file, source, series, span, `retrieved_at_utc`, the `value_status` and `available_at_source` rule, md5, tests that read it) | spec 5492, 6018 | directory does not exist; `core.quant.validate.md5_of(path) -> str` exists | create the directory; verify md5 with `md5_of`; resolve paths from `Path(__file__).parent` |
| `tests/fixtures/macro/ledger_seed_<family>.csv` (for example `ledger_seed_R-06.csv`: row id, source file and row, market, span, run_utc, params, timing class, book, cost, results md5, stored difference series) | spec 6020 | none; the tech-fund `results/r2_kr/r2_kr_excl_trials.csv` (176 rows) is an existing example of a trial ledger | new files |
| Reference mode and v1.2-check mode reachable only from `tests/reference/` and `docs/` with `reference_only=True`; `core/` cannot import that code | spec 5498, 5992 | `tests/reference/` does not exist; `docs/*.py` study scripts already import `core` one-way | new directory; a static test that no file under `core/` imports `tests` or `docs` (reuse `runtime_py()` and `ast`) |
| Tiers `fast` (unit; <= 10 minutes in total), `golden` (<= 2 hours), `freeze` (run only in the M7 freeze job; `run_all.py` verifies md5s and never recomputes) and a `runs_from: M<k>` per test, "Every row names its tier in the test registry" | spec 5496-5497, 5544-5558 | none: `run_all.py` has no arguments and no metadata; the result row has four keys | a module-level dict in each new suite (`{test_id: {"tier": ..., "runs_from": ...}}`) and an optional tier filter in `run_all.py`; default run = `fast` so the existing 155 s behaviour is unchanged |
| T-HERM-01 "passes with all network touchpoints patched to raise"; "No macro test may reach FRED, Yahoo, KIS, FMP, ECOS, Treasury or any other provider" | spec 5493, 5607 | per-provider patches only (B.3); no global guard | reuse `tests.ficc_acceptance._no_network` and `tests.quant_acceptance._no_credentials`; add one context manager that makes `socket.socket.connect` raise for non-loopback hosts so future providers are covered without listing them |
| T-HERM-02 "After `tests/run_all.py`, `core/rules` and every family ledger are byte-identical to their pre-run state; tests write only to temporary copies of the rules store, the ledgers and the artifact directory" | spec 5495, 5608 | `RuleStore(tmp / "rules.json")`, `EngineRuntime(..., state_path=tmp / "engine.json")`, `os.environ["NEXTGEN_FICC_CACHE"] = tempfile.mkdtemp()` | every new store (PIT store, family ledgers, context log, artifact directory, forward record) takes a path argument or honours an env override, and its tests pass a `tempfile.mkdtemp()` path; the test itself hashes the real locations before and after |
| T-RO-01 static scan "of the whole repository, including `core/skills` scripts and the commands of every workflow YAML" for order, cancel, withdrawal, deposit-address or transfer calls and order-client imports | spec 5605 | `test_08`, `test_09` (A.2), the crypto client scan (A.7) | extend the needle list in a new test using `tests.acceptance.runtime_py` and `_code_only`; note the skill scripts and workflow YAML live OUTSIDE the repository at `config.skills_root()` |
| T-RO-02 KIS allowlist "frozen in `config.py`"; HTTP transport patched to record every request | spec 5606 | `KISClient._get(path, tr_id, params, **kw)` is the single KIS transport; `_FakeKIS.calls` already records `(path, tr_id, params)` | allowlist constant in `config.py` checked inside `_get` before a request is built; the recording fake is the existing `_FakeKIS` pattern |
| T-SYN-01 "An "auto" provider that degrades to labelled synthetic data for an acting input -> `MissingInput`, `status="synthetic_rejected"`, `fail_closed=true`. The same provider for a context item is allowed and labelled." | spec 5611 | `auto` degrading to SYNTHETIC is locked in by `test_auto_routing_falls_back_to_labeled_synthetic`, `test_data_auto_degrades_to_synthetic_naming_the_provider`, `test_history_auto_still_degrades_without_keys` | do NOT change `load_history` / `load_series`; refuse at the new acting-input boundary by testing `source == "SYNTHETIC"` |
| T-REPRO-01a reproducibility fields `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`; rng `numpy_pcg64_seedsequence_spawned_children`, `blas_threads: 1`, `relative_tol: 1.0e-12` | spec 3924, 4684 | the repository is NOT a git repository (`git rev-parse` fails); existing code uses `np.random.default_rng(seed)` (PCG64) | see F.5 |
| JSON Schemas 2.0 (T-SCHEMA-01/02/03) | spec 915, 5539 | `jsonschema` is not installed and not in `requirements.txt` | a stdlib required-keys / enum / type check, or add the dependency (owner decision, F.6) |
| "Verdicts near a threshold" asserted as a class ("REJECT or INSUFFICIENT DATA"), never as a point | spec 5499 | `sn.decision != "PASS"` in the expansion gate test is the existing example | `assert decision in {...}` |
| Stochastic goldens name seed, B and block rule | spec 6018 | defaults `seed=11`, `B=2000`, `block=10` in `validate.py`; `GATE["bootstrap_B"]` is mutated by a test (E.6) | pass `seed`, `B`, `block` explicitly in every golden test |

### D.2 What already exists and must be reused, not duplicated

The macro spec never names `core/quant/validate.py`, `core/quant/strategies.py`, `ModelCard`, `walk_forward` or `score_strategy` (0 occurrences in the spec, the tasks JSON, the tasks markdown and the backlog). It places the gate harness in `core/quant/backtest` (`core/quant/backtest.timing_profile`, `.estimator_gate`, `.step3`, `.settling_run`, `.gate_acceptance_test`, `.excess_returns`, `.cost_per_side`; 91 mentions) while its module map says "harness **proposed**; the gate itself **exists**" (spec 914). The existing gate IS `core/quant/validate.py`.

| Need in the specs | Existing implementation (reuse) | Location |
|---|---|---|
| Annualised Sharpe, Lo SE, minimum track record | `sharpe`, `lo_se`, `min_track_record` | validate.py:80-103 |
| Circular block bootstrap CI (studentised) | `block_bootstrap_ci(daily, *, block=10, B=2000, level=0.90, seed=11)` | validate.py:106 |
| Paired Sharpe-difference bootstrap with a one-sided p (the "static same-exposure comparator S" and benchmark tests) | `sharpe_diff_bootstrap(a, b, *, block=10, B=2000, level=0.90, seed=11)` | validate.py:129 |
| Deflated Sharpe, expected maximum Sharpe | `deflated_sharpe(daily, *, n_trials, sr_sd_daily)`, `expected_max_sharpe(n_trials, sr_sd)` | validate.py:154-180 |
| PBO by CSCV | `pbo_cscv(pnl, *, S=8)` | validate.py:183 |
| Newey-West t, Diebold-Mariano | `newey_west_t(d, lag)`, `dm_test(loss_a, loss_b, *, lag=0)` | validate.py:216-235 |
| Kupiec, Christoffersen, traffic light, coverage, PIT, CRPS (B5, R-16, R-30 Stage 1) | `kupiec`, `christoffersen`, `traffic_light`, `coverage_check`, `pit_tests`, `crps`, `score_distribution` | validate.py:560-728 |
| Purged walk-forward, four verdicts, plain-language lines | `walk_forward`, `score_strategy`, `_decide_strategy`, `DECISIONS` | validate.py:288-554 |
| Model card with results md5 | `ModelCard`, `load_cards`, `md5_of` | validate.py:734-792 |
| Pre-fit data checks | `data_checks` | validate.py:241 |
| Costed weight-path engine, decide at t and earn from t+1, 2x cost stress | `strategies.simulate`, `strategies.pnl_matrix(..., stress=2.0)` | strategies.py:69, 379 |
| Volatility target capped at 1.0 | `strategies.vol_target(prices, *, target, window=22, step=21, cap=1.0, band=0.10)`; `realised_vol`, `ewma_vol` | strategies.py:119-209 |
| GARCH / GJR fits with bounds and flags (estimator harness fallbacks) | `garch.fit_garch(returns, *, dist="t", profile=True)`, `gjr.fit_gjr(returns, *, dist="t")` | garch.py:446, gjr.py:130 |
| Per-side cost table 3 / 35 / 50 / 10 / 5 / 10 bp | `COST` dict in `docs/asset_expansion_study.py:60` (matches spec 6456 exactly) | lives in a `docs/` script; R-26 wants one cost table in the rules store, after which the study should import it |
| Trading calendars, sessions, half days | `core/calendars.py` (`get`, `is_trading_day`, `special_session`, `coverage`, `stale_markets`, `summary`), `core/markets.py` (`is_open`, `codes`, `provider_for`) | data in `data/calendars/*.json` |
| Labelled degradation | `History.source` / `.note` / `.adjustment`, `Series.source` / `.note` | history.py:54, data.py:77 |
| Retrieval time and "bar may still be forming" | cache payload `ts` and `live` (history.py:445-448); `_may_be_trading` | a starting point for `retrieved_at_utc` and a provisional `value_status`; today they live only in the cache file, not on `History` |
| Shared HTTP session | `data.net.session` | any new provider client (ECOS, Treasury) should bind it as a module global and expose ONE fetch function, the pattern every hermetic patch relies on |
| Engine halt semantics | `EngineState.halt / acknowledge / arm / snapshot / restore`, `HaltReason`, `EngineMode` | engine tests 01-05 fix the contract (A.3) |
| Temporary stores in tests | `_tmpdir()`, `_runtime(tmp)` | engine_acceptance.py:316-347 |

### D.3 Naming collisions and mismatches between the specs and the repository

| # | Spec text | Repository fact | Consequence |
|---|---|---|---|
| 1 | `core/calendars/data/source_skipped.yaml`, `core/calendars/data/kr_regime_tags.yaml`, `core/calendars/data/` | `core/calendars.py` is a MODULE file; calendar data lives in `ROOT/data/calendars/` (`DATA_DIR`, calendars.py:32) | a directory `core/calendars/` next to `core/calendars.py` is a module / package name clash (a package with `__init__.py` would shadow the module and break every `from core import calendars`). Put the new data files beside the existing ones in `data/calendars/` |
| 2 | `core/skills/workflows/macro_daily.yaml`, `workflows/macro_daily.yaml` | `core/skills/workflows.py` is a MODULE that parses `<config.skills_root()>/workflows/*.yaml` in the EXTERNAL repository (workflows.py:166-171) | same clash; and a YAML placed inside this repository is invisible to `all_workflows()`. Any workflow that IS loaded through `all_workflows()` falls under cockpit tests 02, 05 (every step's `skill` must exist in the external index), 33-37 |
| 3 | prose verdict "INSUFFICIENT DATA" (75 occurrences), "four verdicts are PASS / REVISE / REJECT / INSUFFICIENT DATA" (spec 466) | code, cards and manifest use `"INSUFFICIENT_DATA"`; the spec's own schemas use `{"enum": ["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]}` (spec 4007) and `[..., "INSUFFICIENT_DATA", "NOT_RUN"]` (spec 3759) | use the underscore enum; tech-fund CSV strings such as `INSUFFICIENT DATA (sufficiency)`, `REJECT (step 5)`, `steps 2/5/6/8 pass` are lab prose, never compare against them |
| 4 | `core/quant/backtest` as the costed multi-rule engine and gate harness | `core/quant/backtest.py` (155 lines) is a single-asset signal backtest: `run_backtest(history, *, strategy="ma_cross", ...)`, `STRATEGIES = ("ma_cross", "momentum", "rsi_revert")`, `BacktestResult` (frozen) | see D.2; either add thin spec-named functions to `backtest.py` that delegate to `validate` / `strategies`, or record the mapping in one place. Do not write a second DSR / PBO / bootstrap |
| 5 | `core/quant/risk.market_vol_target` (SMA20 / 0.20 / cap 1), `sma_vol`, `ewma_vol` | `strategies.vol_target` (window 22, step 21, band 0.10, cap 1.0), `strategies.realised_vol(window=22)`, `strategies.ewma_vol(prices, com=60.0)` | same idea, different defaults and parameterisation (`com` vs a half-life); if new functions are added give them distinct names or explicit parameters, never silently different defaults under one name |
| 6 | gate package "frozen before any formal card run", md5-frozen | `GATE` is a mutable dict mutated by a test (expansion_acceptance.py:273) and by the study's `--quick` (asset_expansion_study.py:191-192) | the v2 package needs its own immutable constants (for example `types.MappingProxyType` or a frozen dataclass) and a hash; do not hang it on `GATE` |
| 7 | "The nine steps" with their fixed settings (spec 4758-4768): 1 purged walk-forward 756 / 126, embargo = holding period; 2 Lo SE and a 90% block bootstrap, 2,000 x 10-session blocks, interval must clear zero; 3 deflated Sharpe >= 0.95; 4 PBO <= 0.05 or the winner loses in <= 10% of splits, PBO > 0.2 with the winner losing is a REJECT; 5 bootstrapped Sharpe difference one-sided p <= 0.10; 6 rebuilt at 2x, Sharpe > 0, losing at 2x is a REJECT only when the interval includes zero, otherwise a REVISE; 7 >= 50% of neighbours keep >= half the Sharpe; 8 >= 60% of calendar years positive; 9 `live_sharpe_multiplier: 0.60`, reported, not gated | the code has no step numbers but matches one to one: `GATE` keys `w_is` 756 / `w_oos` 126 (1), `bootstrap_B` 2000 / `block` 10 / `ci_level` 0.90 (2), `dsr_min` 0.95 (3), `pbo_max` 0.05 / `prob_loss_max` 0.10 / `pbo_reject` 0.20 (4), `bench_p_max` 0.10 (5), `cost_stress` 2.0 (6), `plateau_min` 0.5 (7), `years_pos_min` 0.60 (8), `haircut` 0.6 (9) | differences to carry forward: the spec's key is `live_sharpe_multiplier`, the code's is `haircut`; the code has checks the nine-step table does not list (`oos_is_min` 0.5, `trades_min` 100, `trades_floor` 30, `oos_years_min` 5, `pbo_min_configs` 8); the v2 CARD-O addition runs PBO "only with >= 10 configurations" (spec 4763) against the code's 8 |
| 8 | haircut multiplier | `GATE["haircut"] = 0.6`; tech-fund `verification/exec_claim_matrix.csv` X02 records a x0.4 vs x0.6 dispute resolved to the macro spec's x0.6 ("REFUTED (method)") | keep 0.6 |
| 9 | `tests/run_all.py` listed as R-01's package ("`core/ficc/data`; `core/quant/history`; `tests/run_all.py`", spec 925) | `run_all.py` is only the runner | R-01's tests go in a suite module; `run_all.py` gets the registration lines only |
| 10 | "229" / "245 checks" (README), "engine + quant + FICC acceptance" (spec 919, review line 96) | 266 checks in six suites | any v2 statement of the test count must be recomputed from `qa/acceptance_results.json` |
| 11 | `ModelCard.kind` comment `"strategy" \| "distribution" \| "model"` | CARD-P / CARD-O classes and `model_card.macro` fields (T-SCHEMA-02: `family_id`, `ledger_hash`, `N_raw`, `N_clusters`, `N_equiv`, linear N-hat, `V_null`, power `{se, mde80}`, `timing_profile`, `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `cash_convention`, `start_band`, `episode_rule_version`, stability lines, `gjr_null_pct`) | `ModelCard` has no free-form slot except `rules`, `protocol`, `stats`, `tests` dicts; a new optional field must be appended AFTER `citations` with a default so the 34 stored cards and every positional constructor keep working; readers use dict keys, so extra keys are harmless |

### D.4 Constraints that bind new code

1. Frozen dataclasses (use `dataclasses.replace`; append new fields with defaults at the END): `History`, `Series`, `CurveSnapshot`, `CurvePanel`, `Panel`, `PairsDiagnostics`, `WalkForward`, `MCResult`, `GarchFit`, `GJRFit`, `Palette`, `RiskReport`, `BasketStats`, `SignalComponent`, `SignalReport`, `OptimizedPortfolio`, `Frontier`, `BacktestResult`, `Indicator`, `MacroRow`, `Regime`, `MacroSheet`. Mutable: `StrategyScore`, `DistributionScore`, `ModelCard`, the `GATE` dict. Tests construct `History` positionally with four arguments plus keywords (`History("VZ", "FMP", day, (1.0,), adjustment="total")`), so `symbol, source, dates, closes` must stay the first four fields.
2. `Palette` is built positionally in `DARK` and `LIGHT` (theme.py:25-26). There is no warning / amber token: only `success`, `error`, `accent`, `accent_soft`, `muted`. A new token means editing both constructors; a `pal.<name>` that is not a field fails `test_theme_tokens_referenced_by_ui_exist`.
3. Flet 0.85 guard: only `ui/*.py` at the top level is linted. Macro-page code must stay in `ui/macro_page.py` or another top-level `ui/*.py` to be covered. Controls outside `_CHECKED_CONTROLS` (for example `DataTable`) are not keyword-checked.
4. Look up credentials and switches as `config.<name>` at CALL time (history.py:351 comment: "Looked up through `config` at call time: tests swap these functions out."). `from config import fmp_key` defeats every hermetic patch and breaks after `importlib.reload(config)`.
5. One network touchpoint per provider, a module-level function or a module-global session, so a test can replace exactly one name (B.3).
6. Forbidden substrings anywhere under `core/`, `data/`, `ui/`, `main.py`, `config.py`, comments and docstrings included, case-insensitive: `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U`. Case-sensitive: `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD`. The second list forbids any upper-case identifier containing `CANO` (for example a constant named `CANONICAL_...`). The simulated close-auction fill model and the engine hooks must be named around this (the existing simulated book uses `OrderBook.place`).
7. UTF-8 everywhere: `read_text(encoding="utf-8")`, `write_text(..., encoding="utf-8")`, `open(..., encoding="utf-8")`, `json.dumps(..., ensure_ascii=False)`; console output only after the `reconfigure` in `run_all.py`.
8. Self-check blocks (`if __name__ == "__main__":`) assert and print; no `sys.exit`, no network, no writes outside a temp directory. They run in a fresh module namespace under `runpy` (E.7).
9. Decimals inside `core/ficc` and `core/quant` (percent and bp only in the UI); annualisation 252 for sessions (the specs add 365 for crypto, T-CRYPTO-01); ISO date strings in ascending tuples; costs in bp per side multiplied by `BP = 1e-4`; weights decided at the close of t earn from t+1.
10. `pyproject.toml` packages `core*`, `data*`, `ui*` and excludes `tests*`, `qa*`, `_legacy*`. Fixture files under `tests/fixtures/` are therefore never shipped; runtime data files (calendars, registries, schemas) must live under `data/` or `core/`.
11. No new dependency is free: `requirements.txt` has flet, pyyaml, requests, python-dotenv, tzdata, numpy, pandas, scipy, matplotlib, gs-quant, yfinance, pandas-datareader. Installed here but NOT declared: `arch`, `statsmodels`, `pykrx`, `pytest` (and `exchange_calendars`, declared only in `requirements-dev.txt`). `core/` must not import them.

### D.5 Tests the specs ask for that have a natural home next to an existing test

| New test | Sits beside | Reuse |
|---|---|---|
| Causality / no look-ahead of every new sizing rule (risk layer, vol target, sleeves, ladder) | `test_strategies_are_causal` (expansion_acceptance.py:290-303) | the perturb-after-row-600 pattern; the tech-fund labs used the same design (`r2_idx_validation.csv` V1: "weights at t unchanged when prices after t are perturbed", V1b: "the same test detects a planted look-ahead rule") |
| Risk layer composed by `min()`, nothing above 1.0 (T-CAP-01/02: "final = vt x min(overlays, ladder) and final/vt >= 0.5 on every non-HALTED day; a product-composed path raises") | optimizer weight tests (quant_acceptance.py:407-432) | pure numpy property test over random vectors in `[0.5, 1]^k` and ladder steps in `{1.0, 0.5}` |
| Hard stop, HALTED, re-arm (I-04b: a -15% book-NAV breach sets HALTED, refuses re-arm for 10 sessions, resets the reference at re-arm, runs 0.5x for 10 sessions) | engine tests 02-05, 77-91 | `EngineState`, `_runtime(tmp)`; per-book HALTED is new (the existing state is one global mode) |
| Schedule-aware staleness by role (T-ROLE-01: stale acting input -> fail closed + alert, HALTED only after the declared N; stale risk_model input -> `hedge_credit_off`, never HALTED; stale context input -> label only) | `test_the_cache_knows_when_a_market_may_be_trading` (quant_acceptance.py:252-272), engine tests 51-62 | pinned clocks (`datetime(..., tzinfo=timezone.utc)`), `core.markets.is_open` |
| PIT store and `value_status` (T-PROV-01, T-FIX-01) | `test_history_cache_serves_a_rerun_without_asking_the_provider_again` (the cache-file contract) | `tempfile.mkdtemp()`, explicit `ts` rewriting as at quant_acceptance.py:157-163 |
| Gate package v2 statistics (T-DSR-01/02, T-PBO-01, T-SE-01, T-PZERO-01 "no p-value is printed as 0 (prints < 1/B)") | `test_gate_rejects_noise_and_keeps_a_real_edge`, `selfcheck_validate` | the planted-edge / pure-noise matrices; note `sharpe_diff_bootstrap` can return `p == 0.0` today, so T-PZERO-01 needs a floor at the print site |
| Macro-page displays | `test_every_fchart_renders_a_data_uri_image`, `test_macro_*` (ficc), the four ui guard tests | charts must return an object whose `.src` starts with `data:image/png;base64,` |
| Tech-fund golden lookups | none | `pd.read_csv` of the bundle files; assert `raw` of each traced `GV-nnn` against its source cell |

---

## E. Gotchas

1. **README is behind the code.** README says "229 checks" (line 347) and "The whole suite is **245 checks**" (379), with "48 equity quant checks" and "125 inherited"; the real numbers are 266 = cockpit 47 + engine 89 + ui 4 + quant 53 + ficc 56 + expansion 17. README (377-378) lists the self-check of "GJR / skewed-t" in the expansion group, but `core/quant/gjr.py`'s `__main__` block is not registered (expansion_acceptance.py:316-324), so it never runs in the suite. README setup says "Python 3.10+"; this machine runs 3.13.14 and `.pyc` files are cpython-313.
2. **The product is still named NEXTGEN in code.** Env prefix `NEXTGEN_*`, home directory `~/.nextgen`, `config.py` docstring "NEXTGEN skill cockpit", `tests/__init__.py` "NEXTGEN verification suite". The only `QUANTGEN_*` env var is `QUANTGEN_AI_MODEL`.
3. **The suite is not fully hermetic when keys are configured, and they are configured here.** Presence check only (no values read): FMP, KIS, OpenDART, KRX and Anthropic are ready on this machine; Upbit and GS are not. `cockpit/test_21_krx_gateway_degrades_with_a_reason` calls `KRXGateway().daily("005930")` and `.filings("005930")` with no patch (acceptance.py:318-324): with keys present these are live KIS and OpenDART requests (the test took 1.97 s at baseline) and they can refresh `~/.nextgen/kis_token.json`. `test_22` builds a `KRXGateway()` too. The quant, ficc and expansion suites do patch their touchpoints.
4. **Cockpit tests depend on an external repository and write production state.** They need `~/Downloads/claude-trading-skills-main/claude-trading-skills-main` (`NEXTGEN_SKILLS_ROOT` overrides); without it `test_01` (>= 60 skills), `test_02` (>= 8 workflows) and `test_19` fail. `test_19`, `test_26`, `test_29` spawn real skill subprocesses and write `~/.nextgen/runs/<run_id>/` (497 run directories exist). This contradicts the letter of T-HERM-02 for the suite as a whole; the spec scopes T-HERM-01 to "the macro test suite".
5. **`importlib.reload(config)` runs three times in the cockpit suite** (tests 07b, 10, 20). It re-reads `.env` and rebinds every function and constant in `config`. Anything that cached `config.X` in another module before the reload keeps the old object. Because cockpit runs first, later suites see a freshly reloaded `config`.
6. **`V.GATE["bootstrap_B"] = 300` leaks.** `expansion/gate_noise_vs_edge` sets it (expansion_acceptance.py:273) and never restores it. Every in-process `score_strategy` call after that test, in any suite registered after it or later in the expansion list, bootstraps with B = 300 instead of 2000. A new suite appended after `expansion` in `run_all.py` inherits B = 300. Stochastic goldens must pass `B` explicitly or set and restore the key.
7. **`runpy` self-checks execute a second copy of the module** as `__main__`: module globals are fresh (so `selfcheck_validate` runs with `bootstrap_B = 2000` and takes 46 s), and classes defined there are different objects from the imported module's classes.
8. **Suites cannot be run as scripts.** `python tests/ficc_acceptance.py` fails with `ModuleNotFoundError: No module named 'config'` (verified); use `python -m tests.ficc_acceptance` from ROOT, or `python tests/run_all.py`. `expansion_acceptance.py`'s `__main__` inserts ROOT on `sys.path` only after the module-level `import config`.
9. **Keyless providers are reached by `auto`.** `load_history("KRW-BTC")`, `load_history("^VIX")`, `load_history("ZN=F")` go to Upbit / Binance / Yahoo with no key and no readiness switch (history.py:490-493). `_no_credentials()` does not stop them. A test that uses a crypto-shaped or Yahoo-shaped symbol must patch `data.crypto.crypto_client._get` or `core.ficc.data._yf_fetch`, or pass `source="synthetic"`.
10. **Clock-dependent behaviour.** `synthetic_series` / `synthetic_history` dates end at `date.today()`; `fmp_history` computes its start from `date.today()`; `ModelCard.created` defaults to `date.today()`; `data_checks(today=None)` uses `date.today()` and will report staleness on any frozen fixture (pass `today=`). `engine/test_73_calendar_coverage_is_not_already_expired` reads the real date; shipped calendars cover 2026-01-01 to 2027-12-31, so the suite turns red by itself when coverage expires. `_cached` uses `time.time()` and `datetime.now()`.
11. **Calendars are too short for the specs.** `data/calendars/KRX.json` and `US.json` cover 2026-2027 only (source `exchange_calendars 4.13.2`, generated 2026-08-18); `is_trading_day` returns `None` outside coverage (engine test 71). The specs need effective-dated KRX sessions back to 1997 (06:00Z closes before 2016-08-01, 06:30Z after, CSAT-day 07:30Z, Saturday sessions before 1998-12-12; spec 5527) and JPX, SSE, HKEX, TWSE, CME, Cboe calendars (spec 6033). `exchange_calendars` is a generator-time tool (`requirements-dev.txt`: "never imported by the application").
12. **Windows cp949.** The default console and file encoding on this machine is cp949; `run_all.py` reconfigures stdout and stderr, and `test_16` / `test_17` exist because the previous suite died on it. `test_17` only inspects `acceptance.py` and `run_all.py`, so a missing `encoding=` in a NEW test file is not caught by any test. Subprocesses get `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` only through `config.skill_env()`.
13. **The repository sits under OneDrive** (`C:/Users/whydi/OneDrive/Desktop/QUANTGEN`) and is not a git repository. Existing tests write temporary state with `tempfile.mkdtemp()` (outside OneDrive); follow that rather than writing scratch files into the tree. There is no VCS history to diff against and no commit hash to stamp.
14. **Fake dates in existing helpers.** `_trend_history` and `test_backtest_has_no_lookahead` generate dates with 28-day months and repeats; `_garch_history` uses consecutive calendar days including weekends. They are fine for the functions they test and unusable for anything calendar-aware (PIT store, staleness, `data_checks`).
15. **`tests()` by `globals()` registers imported names too.** In the cockpit, engine, ui, quant and ficc suites any module-level name starting with `test_` that is callable becomes a test, including something imported `from x import test_y`. Helpers must not start with `test_`.
16. **`run_all.py` writes into the tree on every run** (`qa/acceptance_results.json`) and catches only `Exception`. A failing import aborts everything; there is no partial result file.
17. **`_code_only` strips docstrings but `test_08` / `test_09` do not use it.** Naming a forbidden token in a comment "to explain the rule" inside `core/`, `data/` or `ui/` fails the suite. The test files themselves are outside `runtime_py()` and may name them.
18. **This run's helper script is broken.** `scratchpad/prep/readlines.py` (cited by this run's instructions) has a literal newline inside a string and raises `SyntaxError`; long lines were read with the Read tool instead. None of the files assigned here has a line over 1,900 characters.
19. **Yahoo `=F`, `^` and `/` are rewritten in cache file names** (`yf_CL_F.csv`, `yf__VIX.csv`) while the column header keeps the original symbol (`yf_CL=F`, `yf_^VIX`).
20. **`fred()` in the study writes NaN rows; `_cached()` drops them before writing.** FRED files keep holiday rows as empty cells; Yahoo, Upbit and Binance files do not. A loader must not treat the two families alike.

---

## F. Ambiguities, with the conservative reading

1. **Which document is the tech-fund specification.** `results/r3/r3_go_nogo.csv` targets sections `§TF-1` to `§TF-7`, and the bundle README names `QUANTGEN_TECHFUND_INTEGRATION.md` and `QUANTGEN_TECHFUND_BACKLOG.md` as deliverables, but neither file is on this machine; only `research_notes/R3_TF_neural_link.md` (sections 5, 6, 9, 10, 11, 13) and its inputs are. Conservative reading: implement only what R3 states with a decision of `BUILD NOW`, `INVARIANT` or `GOVERNANCE` and a traced golden value; everything whose detail lives only in the missing `§TF-n` text stays specification-book only with no exposure change.
2. **Golden values without their inputs.** Every numeric golden in both programmes was computed on data that is not local (DI.3). Conservative reading: a golden whose input series is absent is NOT asserted by a recomputation and is NOT replaced by a number computed from the Yahoo cache; it is either (a) asserted as a lookup against the bundled result CSV (tech-fund) or (b) registered as a test with status "not run: fixture missing" that fails closed for any card that depends on it (no formal card run, no PASS). No number is invented (spec 5996: "These are listed so that no number is invented in their place").
3. **Adjusted versus price-return closes.** Local Yahoo files are total-return adjusted; the tech-fund labs used price returns without dividends; the macro spec uses KRX official closes and excess returns over cash (R-22). The specs do not say which convention a local stand-in may use. Conservative reading: never mix; label any run on the local cache `adjustment="total"`, indicative, outside the fixture manifest.
4. **`r2_idx_claims.csv` hash mismatch** (DI.2). Cause unknown (no QA log entry). Conservative reading: do not use that file as a frozen fixture; if it must be used, record the new hash in the manifest with a note that it differs from the lab's `V8` row.
5. **`git_hash` and "anchored timestamps cite a git commit or an external anchor, never a hand-entered time"** (spec 3924, 6012) in a directory that is not a git repository. Conservative reading: `git_hash` is recorded as an explicit sentinel (not a fabricated hash) together with a content hash of the source tree as `config_hash`; the "f = 1 route" that depends on anchored publication instants (R-23) is treated as unavailable, so the selection factor takes the conservative (larger) value; no formal card run until the owner provides an anchor.
6. **JSON Schema validation without `jsonschema`.** The spec gives schemas (section 6) and tests (T-SCHEMA-01/02/03) but no library. Conservative reading: no new dependency without the owner; validate required keys, enums and types with the standard library and fail closed on any unknown `verdict` or `value_status` string.
7. **Scope of T-HERM-02.** "`core/rules` ... byte-identical" names a code package, while the rules store is `~/.nextgen/trading/rules.json`; and the existing cockpit suite writes `~/.nextgen/runs`. Conservative reading: the new suites must leave `config.trading_dir()`, `config.ficc_cache_dir()`, every new ledger / store path and `docs/asset_expansion/` byte-identical; the pre-existing cockpit writes are reported, not silently accepted, and are not extended.
8. **Scope of T-HERM-01.** It says "the macro test suite". The existing `cockpit/test_21` reaches KIS / OpenDART when keys are set. Conservative reading: the new suites install a socket-level guard for their own duration; fixing `test_21` (patching `config.kis_ready` / `config.opendart_ready`) is a separate one-line hardening the owner may want, since it changes an inherited test.
9. **Where the tiers and `runs_from` live.** The spec says "the test registry" without a format. Conservative reading: metadata beside the tests in the suite module; default `run_all.py` behaviour unchanged; `freeze`-tier results only md5-verified.
10. **Checks in the code that the nine-step table does not list** (D.3 row 7): `oos_is_min`, `trades_min` / `trades_floor`, `oos_years_min`, and `pbo_min_configs` 8 against the v2 addition's "only with >= 10 configurations". The tech-fund labs also speak of an "8-step harness" and print `g1..g9` columns (`r2_kr_excl_gate.csv`). Neither spec says whether the extra checks stay binding on v2 cards. Conservative reading: do not remove or loosen any existing check in `_decide_strategy`; the v2 gate package is additive (a v2 card must also clear the stricter of the two PBO floors), and existing cards keep their recorded verdicts.
11. **Existing 34 cards under a new gate.** Neither spec says whether `docs/asset_expansion/cards/*.json` are re-scored under gate package v2. Conservative reading: they are not touched (their `results_md5` matches `results.csv` today); new cards go to a new directory.
12. **Calendar depth.** The specs require regime tags and effective-dated closes from 1997 but the acquisition register leaves "Licence, owner and md5 columns ... filled when each file is acquired; a file without them is not a fixture" (spec 6035). Conservative reading: ship the rule logic and the documented dated constants the spec prints; mark any date outside shipped coverage as unknown (the existing `None` convention), never as a trading day.
13. **Data freshness of the local cache versus the spec's as-of date.** The cache ends 2026-09-18 to 2026-09-25; the spec's fixtures are "as of 2026-10-02, re-frozen after the 17:20 KST data patch". Conservative reading: nothing computed from the local cache is labelled with the spec's snapshot id.
