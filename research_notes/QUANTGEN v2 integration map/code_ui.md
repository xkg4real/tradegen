# code_ui — map of the QUANTGEN UI subsystem (as built, 2026-10-05)

Scope read in full: `ui/macro_page.py` (232 l), `strategy_lab_page.py` (231), `quant_lab_page.py` (389), `signals_page.py` (214), `etf_page.py` (269), `crypto_page.py` (239), `components.py` (159), `charts.py` (148), `fcharts.py` (447), `qcharts.py` (238), `xcharts.py` (126), `param_form.py` (310), `settings_page.py` (287), `core/theme.py` (42), `core/numfmt.py` (114), `tests/flet_api_guard.py` (174), `main.py` (248). Also read because they carry reusable patterns: `ui/ai_panel.py` (82), `ui/trading_page.py` (393, HALTED banner), `ui/runs_page.py` (123, open-file pattern), `tests/run_all.py`.
Runtime: Python 3.13, `flet[all]==0.85.2` (pinned in `requirements.txt` and `pyproject.toml`), matplotlib Agg. All line refs are `file:line` in the repo at `C:/Users/whydi/OneDrive/Desktop/QUANTGEN`. Spec refs `SPEC:n` = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` line n; `R3:n` = `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/R3_TF_neural_link.md` line n.

---

## A. File by file

### A.1 `core/theme.py` — design tokens (the only palette source)

| Name | Value (verbatim) | Line |
|---|---|---|
| `RADII` | `{"sm": 8, "md": 12, "lg": 16, "pill": 999}` | 5 |
| `BREAKPOINTS` | `{"compact": 700, "medium": 1200}` (only `"compact"` is read: `main.py:224`) | 6 |
| `TRANSITION_MS` | `180` (AnimatedSwitcher duration, `main.py:119-120`) | 7 |
| `MODES` / `DEFAULT_MODE` | `("dark", "light", "system")` / `"system"` | 8-9 |

`@dataclass(frozen=True) class Palette` (11-23), field order = positional order of the constructors:

| token | DARK (25) | LIGHT (26) | Used for |
|---|---|---|---|
| `bg` | `#101417` | `#f5f7f6` | page background; console/code wells |
| `surface` | `#171d21` | `#ffffff` | cards, rail, chart figure background |
| `surface_2` | `#1d252a` | `#edf2f0` | chips, stat tiles, notices, bar tracks, legends |
| `border` | `#324047` | `#d2dcda` | 1 px borders, dividers, chart spines/grid |
| `text` | `#e7ecef` | `#192326` | primary text |
| `muted` | `#9eabb2` | `#647277` | secondary text, captions, neutral chips |
| `accent` | `#4f98a3` | `#01696f` | primary series, selected nav, "needs attention / info" chips |
| `accent_soft` | `#233b40` | `#d8e8e5` | defined, referenced nowhere in `ui/` or `main.py` |
| `success` | `#6daa45` | `#437a22` | positive / ready / PASS |
| `error` | `#d1637f` | `#a12c53` | negative / failure / REJECT / SYNTHETIC warnings |
| `on_accent` | `#071012` | `#ffffff` | text on accent fill (selected nav, primary button) |

API: `palette_for(mode: str, *, system_is_dark: bool = True) -> Palette` (29); `set_mode(mode: str, *, system_is_dark: bool = True) -> Palette` (35; unknown mode stored as `DEFAULT_MODE`); `active() -> Palette` (40); `active_mode() -> str` (41); `token_names() -> tuple[str, ...]` (42; = dataclass field names, consumed by the guard).
State: module global `_state = {"mode": DEFAULT_MODE, "palette": DARK}` (27). There is **no warning/amber token**; three-state colouring uses success / accent / error (+ muted for neutral).
As run: `main.py:100-104` forces `page.theme_mode = ft.ThemeMode.DARK`, `set_mode("dark")`. LIGHT and "system" exist but are never selected at runtime. Every page captures `pal = active()` once at build time, so a later mode change would need `cache.clear()` and a rebuild.

### A.2 `core/numfmt.py` — locale numeric formatting (pure, no Flet)

- `format_number(value: float, locale: Optional[str] = None, decimals: int = 0) -> str` (54) — grouped fixed-decimal; never raises; `None`/NaN/unparseable → `""`; no "-0".
- `format_price(value: float, currency: str = "", locale: Optional[str] = None, decimals: Optional[int] = None) -> str` (78) — default decimals 0 for `KRW`/`JPY`/`VND`, else 2; symbol table `_CCY` (27-31): KRW `₩`, USD `$`, EUR `€`, JPY `¥`, GBP `£`, CNY `¥`, HKD `HK$` lead with a space (`"₩ 1,234"`), VND `₫` trails.
- `format_compact(value: float, locale: Optional[str] = None, decimals: int = 1) -> str` (98) — suffixes `K/M/B/T` (`_COMPACT`, 94-95).
- `_SEP` (17-23): `de`, `vi`, `es` → `(".", ",")`; `ru`, `fr` → `(" ", ",")`; default `(",", ".")`.
- Only consumer: `ui/krx_page.py:19` (with `main.LOCALE = "en"`, `main.py:72`). Every other page formats with inline f-strings (`f"{x * 100:.2f}%"`, `f"{x / BP:+.1f}bp"`, `f"{x:,.2f}"`).

### A.3 `tests/flet_api_guard.py` — static lint over `ui/*.py` (4 tests; see C and D.6 for exact rules)

`UI = <repo>/ui`; `_ui_files()` = `sorted(UI.glob("*.py"))` (non-recursive). `_CHECKED_CONTROLS` (30-36), verbatim:
`"Dropdown", "TextField", "Button", "IconButton", "Text", "Container", "Row", "Column", "ResponsiveRow", "AlertDialog", "SnackBar", "Icon", "Divider", "VerticalDivider", "AnimatedSwitcher", "Image", "Checkbox", "ExpansionTile", "ProgressRing", "ProgressBar", "FilePicker", "ListTile", "Switch", "Slider", "Card", "Stack", "Tabs", "Tab", "Badge", "Tooltip"`.
`_params(control_name) -> set[str] | None` = parameter names of `getattr(ft, name).__init__`. `tests()` returns sorted `(name, fn)` of module-level `test_*`.

### A.4 `main.py` — entry, navigation, page registry

- `LOCALE = "en"` (72). `NAV` (74-94): tuple of `(key, label, ft.Icons.X)`, in rail order:
  `macro/Macro/PUBLIC_OUTLINED`, `rates/Rates/SSID_CHART_ROUNDED`, `bonds/Bonds/RECEIPT_LONG_OUTLINED`, `fx/FX/CURRENCY_EXCHANGE_OUTLINED`, `structuring/Structuring/LAYERS_OUTLINED`, `derivatives/Derivatives/STACKED_LINE_CHART_OUTLINED`, `etf/ETF/INVENTORY_2_OUTLINED`, `crypto/Crypto/CURRENCY_BITCOIN`, `lab/Strategy Lab/SCIENCE_OUTLINED`, `quant/Quant Lab/TROUBLESHOOT_OUTLINED`, `portfolio/Portfolio/PIE_CHART_OUTLINE`, `signals/Signals/CANDLESTICK_CHART_OUTLINED`, `trading/Execution/SPEED_ROUNDED`, `rules/Rules/RULE_FOLDER_OUTLINED`, `workflows/Workflows/ACCOUNT_TREE_OUTLINED`, `skills/Skills/EXTENSION_OUTLINED`, `krx/KRX/SHOW_CHART_ROUNDED`, `runs/Runs/HISTORY`, `settings/Settings/SETTINGS_OUTLINED` (19 entries).
- `main(page: ft.Page) -> None` (97): title `"QUANTGEN"`, `page.padding = 0`, window min 420 x 620, `page.bgcolor = pal.bg`. Constructs once: `gateway = KRXGateway()`, `rule_store = RuleStore()`, `engine = EngineRuntime(rule_store, QuoteFeed(gateway))` (107-113). `current = {"page": "macro"}` (start page), `cache: dict[str, ft.Control] = {}`.
- `build(name: str, **kwargs) -> ft.Control` (124-159). Dict `ficc` (125-129) maps `macro, rates, bonds, fx, structuring, derivatives, etf, crypto, lab` to builders all called as `builder(page, on_open_settings=lambda: navigate("settings"))`. Explicit branches: `quant`, `portfolio`, `signals` (same signature), `trading` → `build_trading_page(page, engine, on_open_rules=..., on_open_settings=...)`, `rules` → `build_rules_page(page, rule_store, on_changed=lambda: cache.pop("trading", None))`, `workflows` → `build_workflows_page(page, on_open_settings=..., on_open_skill=lambda sid: navigate("skills", focus=sid))`, `skills` → `build_skills_page(page, on_open_settings=..., focus_skill=kwargs.get("focus", ""))`, `krx` → `build_krx_page(page, gateway, locale=LOCALE, on_open_settings=...)`, `runs` → `build_runs_page(page)`. **Fallthrough (159): any unknown key returns `build_settings_page(page, on_reload=reload_catalogue)`** — a NAV key without a branch silently shows Settings.
- `navigate(name: str, *, focus: str = "", rebuild: bool = False) -> None` (161-171): drops the cache entry when `rebuild or name in ("runs", "trading") or (name == "skills" and focus)`; otherwise the built control is reused forever (state survives tab switches). Sets `content.content = ft.Container(cache[name], padding=24, expand=True)`; `render_nav()`; `page.update()`.
- `reload_catalogue()` (173): `core.skills.reload_all()`, `cache.clear()`, `navigate("settings", rebuild=True)`.
- Rail (179-221): width 220 / padding 14; compact (< `BREAKPOINTS["compact"]` = 700 px) → width 68 / padding 8, icons only with `tooltip=label`. Nav item = `ft.Container(ft.Row([Icon(size=18), Text(size=13)], spacing=10), padding=ft.Padding(12, 10, 12, 10), bgcolor=pal.accent if selected, border_radius=RADII["md"], ink=True)`; `nav_host = ft.Column(spacing=4)` — **the rail column has no scroll**; 19 items x ~38 px already need ~800 px of height against a 620 px minimum.
- `page.on_resize = resize` (236); layout `ft.Row([rail, ft.VerticalDivider(width=1, color=pal.border), content], expand=True, spacing=0, vertical_alignment=STRETCH)`; `content = ft.AnimatedSwitcher(content=ft.Container(), duration=TRANSITION_MS, reverse_duration=TRANSITION_MS, expand=True)`.
- Entry: `ft.run(main, assets_dir="assets")` (248).

### A.5 `ui/components.py` — shared atoms (REUSE; all return Flet controls, all read `active()` at call time)

| Signature | Line | Shape |
|---|---|---|
| `colour_for(token: str) -> str` | 39 | `getattr(active(), token)`; raises AttributeError on a bad token |
| `chip(text: str, token: str = "muted", *, tooltip: str = "") -> ft.Container` | 45 | pill: Text size 11 W_500 in token colour; `padding=ft.Padding(8, 3, 8, 3)`, `bgcolor=pal.surface_2`, 1 px border in token colour, `RADII["pill"]`. "Carries a text label, never colour alone." |
| `readiness_chip(state: State, *, tooltip: str = "") -> ft.Container` | 58 | via `STATE_STYLE` |
| `run_status_chip(status: str) -> ft.Container` | 63 | via `RUN_STATUS_STYLE`; unknown → `(status or "unknown", "muted")` |
| `section(title: str, *, subtitle: str = "") -> ft.Column` | 68 | page header: title size 26 BOLD, subtitle size 13 muted, spacing 4 |
| `card(content: ft.Control, *, on_click: Optional[Callable] = None, col: Optional[dict] = None, tooltip: str = "") -> ft.Container` | 76 | padding 16, `pal.surface`, 1 px `pal.border`, `RADII["lg"]`, `ink` iff clickable |
| `notice(text: str, token: str = "accent", *, icon: str = ft.Icons.INFO_OUTLINE, action: Optional[ft.Control] = None) -> ft.Container` | 92 | banner: icon size 18 in token colour + selectable Text size 13 + optional action control; padding 14, `pal.surface_2`, 1 px token-colour border, `RADII["md"]` |
| `empty_state(title: str, detail: str, *, icon: str = ft.Icons.INBOX_OUTLINED, action: Optional[ft.Control] = None) -> ft.Container` | 111 | centred icon 40 / title 16 W_600 / detail 13 muted; padding 48, `expand=True` |
| `key_value(label: str, value: str, *, width: int = 132) -> ft.Row` | 132 | label size 12 muted fixed width; value size 12 selectable, `"—"` when empty |
| `mono(text: str, *, size: int = 11) -> ft.Text` | 141 | `font_family="Consolas, monospace"`, selectable |
| `stat(label: str, value: str, *, token: str = "text", tooltip: str = "") -> ft.Container` | 146 | metric tile: label size 10 muted over value size 16 W_600 in `getattr(pal, token, pal.text)`; `padding=ft.Padding(14, 10, 14, 10)`, `pal.surface_2`, border, `RADII["md"]` |

Constants: `STATE_STYLE: dict[State, tuple[str, str]]` (18-23): `READY → ("Ready", "success")`, `NEEDS_INPUT → ("Needs input", "accent")`, `MISSING_KEY → ("Key required", "error")`, `DOC_ONLY → ("Reference only", "muted")` (`core.skills.readiness.State` values `"ready" | "missing_key" | "needs_input" | "doc_only"`). `RUN_STATUS_STYLE: dict[str, tuple[str, str]]` (25-32): `ok → ("Succeeded","success")`, `failed → ("Failed","error")`, `timeout → ("Timed out","error")`, `cancelled → ("Cancelled","muted")`, `error → ("Could not start","error")`, `running → ("Running","accent")`.
Convention: every `(label, token)` style map is a module-level dict keyed by the enum/string; pages add their own (`_TOKEN`, `_REGIME_TOKEN`, `MODE_STYLE`, `OUTCOME_STYLE`, `STATUS_STYLE`).

### A.6 `ui/ai_panel.py` — the analysis card every result page ends with

`analysis_panel(page: ft.Page, *, kind: str, narrative: str, payload_fn: Callable[[], dict], deep_fn: Callable[..., "insights.Analysis"] | None = None) -> ft.Control` (26). Always shows the local narrative (chip `"engine: local"`); "Deep analysis" button is `disabled=not insights.ai_ready()` (needs `ANTHROPIC_API_KEY`); on click runs `deep(kind, payload_fn(), question=question.value or "")` inside `page.run_thread`; result is `core.quant.insights.Analysis(text: str, engine: str, error: str = "")`; `error` → `notice(result.error, "error", icon=ft.Icons.CLOUD_OFF_OUTLINED)`. Default `deep_fn` = `core.quant.insights.deep_analysis(kind: str, payload: dict, *, question: str = "")`; FICC pages pass `core.ficc.insights.deep_analysis`. The payload sent is exactly what the page computed (docstring 11-13). `kind` strings in use: `"macro_sheet"`, `"daily_market_commentary"`, `"weekly_fi_fx_strategy"`, `"strategy_gate"`, `"monte_carlo"`, `"signals_and_backtest"`, `"etf_structure"`, `"crypto_market"`.

### A.7 `ui/charts.py` — container bars for skill insights (no matplotlib)

`BAR_HEIGHT = 16`, `LABEL_WIDTH = 190`. `_track(score: float, token: str) -> ft.Control` (39; 0..100 fill via `expand` weights). `component_bar(component: Component, *, show_signal: bool = True) -> ft.Control` (59). `composite_bar(insight: Insight) -> ft.Control` (87; empty Container when `insight.score is None`). `insight_chart(insight: Insight, *, show_signal: bool = True) -> Optional[ft.Control]` (110; `None` when nothing to draw). Inputs are `core.skills.insights.Component(key, label, score, weight=0.0, signal="")` with property `band` (`>= 70 → "success"`, `>= 40 → "accent"`, else error) and `Insight(skill_id, source, score, zone, guidance, components, warnings, facts, quality, lines)` with `.empty`. Used by `ui/workflows_page.py`. Same bar idiom is re-implemented in `signals_page._signed_bar` and `portfolio_page._bar`.

### A.8 `ui/qcharts.py` — matplotlib → `ft.Image` (shared machinery + equity charts)

`matplotlib.use("Agg")` before pyplot (20) — required because charts are built in worker threads. `DPI = 110`.
Private helpers imported by the other chart modules (treat as the chart API):
- `_style(ax, pal, *, grid: bool = True) -> None` (36): facecolor `pal.surface`, spines `pal.border`, ticks `pal.muted` labelsize 8, grid `pal.border` alpha 0.35 lw 0.6, title `pal.text`, axis labels `pal.muted`.
- `_fig(w: float, h: float, pal)` → `(fig, ax)` (48), figure facecolor `pal.surface`.
- `_to_image(fig, *, expand: bool = True) -> ft.Image` (55): PNG `bbox_inches="tight"`, `plt.close(fig)`, returns `ft.Image(src=f"data:image/png;base64,{b64}", fit=ft.BoxFit.CONTAIN, expand=expand)`.
- `_thin_dates(dates, n_ticks: int = 6)` → `(idx, labels)` (65); `([], [])` on empty.
Charts (all `-> ft.Image`, width 7.5 in, title `fontsize=10, loc="left"`, legend fontsize 8 on `pal.surface_2`):
`price_chart(history: History, *, sma_windows: tuple[int, ...] = (50, 200))` (73); `fan_chart(history: History, mc: MCResult, *, tail_sessions: int = 90)` (94); `terminal_histogram(mc: MCResult)` (122); `equity_chart(bt: BacktestResult)` (140); `frontier_chart(frontier: Frontier, marked: list[OptimizedPortfolio] | None = None)` (161; cmap `viridis`); `corr_heatmap(corr: np.ndarray, symbols: tuple[str, ...])` (192; cmap `RdYlGn_r`, cell text hard-coded `#111111`, `expand=False`); `cond_vol_chart(history: History, fit: GarchFit, *, window: int = 20)` (211).

### A.9 `ui/fcharts.py` — FICC charts (15 functions; decimals scaled to %/bp here)

Helpers: `_legend(ax, pal, loc: str = "upper left", *args)` (37), `_twin_legend(ax, ax2, pal, loc: str)` (42), `_tenor_axis(ax, tenors: Sequence[float])` (48; log x), `_date_axis(ax, dates)` (55).
`curve_chart(report: CurveReport)` (64); `curve_history_chart(panel: CurvePanel, tenors: Sequence[float] = (2.0, 10.0, 30.0))` (95); `pca_chart(pca: PCAResult)` (113); `krd_chart(krd: dict[float, float], title: str = "Key-rate DV01")` (133); `scenario_chart(rows: Sequence[ScenarioRow])` (148); `price_yield_chart(bond: Bond, ytm: float)` (168); `caplet_chart(report: CapFloorReport)` (190); `smile_chart(strikes, vols, points: Sequence[SmilePoint], forward: float)` (219); `fx_spot_chart(series: Series, forward_points_line=None)` (238); `carry_equity_chart(bt: CarryBacktest)` (263); `carry_bar_chart(rows: Sequence[CarryRow])` (282); `payoff_chart(product)` (306; duck-typed, raises `ValueError("payoff_grid is empty.")`); `rate_fan_chart(sim: RateSimResult)` (334); `horizon_pv_hist(hpv: HorizonPV)` (359); `macro_z_chart(sheet: MacroSheet)` (374; group colours `{"rates": accent, "credit": error, "fx": success, "risk": muted}`, synthetic rows `hatch="//"`, dashed guides at z = -2, 2, title prints `curve/risk/USD/inflation` regime words). `__main__` self-check (404-447) renders 16 images offline.

### A.10 `ui/xcharts.py` — v3 charts (width 9.5 in, frameless legend fontsize 7)

`lines_chart(dates: Sequence[str], series: dict[str, np.ndarray], *, title: str = "", ylabel: str = "", hlines: Optional[dict[str, float]] = None, height: float = 3.2, pct: bool = False)` (14; series right-aligned on the date axis, colour cycle `[accent, text, success, error, muted]`; `pct=True` formats y as `f"{v:.1f}%"`, values must already be percent).
`smile_chart(points, fit=None, F: float = 0.0, *, title: str = "Implied volatility")` (35). `density_chart(rnd: dict, *, p_samples: Optional[np.ndarray] = None, title: str = "Risk-neutral density")` (57; keys `strikes`, `density`, `integral`, `F`). `equity_chart(dates: Sequence[str], equity: np.ndarray, bench: Optional[np.ndarray] = None, *, title: str = "Equity", labels: tuple[str, str] = ("strategy", "benchmark"))` (72). `bars_chart(labels: Sequence[str], values: Sequence[float], *, title: str = "", vmax: float = 100.0, annotate: Optional[Sequence[str]] = None)` (89; horizontal, `None`/non-finite drawn as 0.0, colour `>= 70 success`, `>= 40 accent`, else error). `premium_chart(dates, price, nav, premium_pct, *, title: str = "Price vs NAV")` (107; two stacked axes).

### A.11 `ui/macro_page.py` — the page v2 extends

Constants: `_SOURCES` (30-32) `[("auto", "Auto (FRED + Yahoo, synthetic fallback)"), ("fred", "Live only (FRED + Yahoo, no fallback)"), ("synthetic", "Synthetic demo")]`; `_HEADLINE = ("DGS2", "DGS10", "DGS30", "T10Y2Y", "DFII10", "T10YIE", "VIXCLS", "BAMLH0A0HYM2", "DTWEXBGS")`; `_REGIME_TOKEN = {"risk-on": "success", "risk-off": "error"}`; `_COLUMNS = ("Group", "Indicator", "Last", "1d", "1w", "1m", "3m", "z (1y)", "pct (1y)", "Source")`; `_REPORTS = {"daily": ("Daily market commentary", "daily_market_commentary"), "weekly": ("Weekly rates/FX strategy", "weekly_fi_fx_strategy")}`.
Module functions (unit-aware formatting; the core hands over decimals):
- `_level(r: MacroRow) -> str` (43): `unit == "pct"` → `f"{r.last * 100:.2f}%"`; `"bp"` → `f"{r.last / BP:.0f}bp"`; `"fx"` and `r.last < 20` → 4 dp; else `f"{r.last:,.2f}"`.
- `_chg(r: MacroRow, chg: float | None) -> str` (53): `None` → `"-"`; pct/bp → `f"{chg / BP:+.1f}bp"`; small fx → `+.4f`; else `+.2f`.
- `build_macro_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control` (63).
Inner structure (closures): `provider_bar()` (chips from `config.ficc_provider_status()`), `cell(text, *, token="text") -> ft.DataCell`, `sign_token(x)`, `table(sheet)` (`ft.DataTable(column_spacing=16, heading_row_height=34, data_row_max_height=32)` inside `ft.Row([dt], scroll=ft.ScrollMode.AUTO)`), `sheet_analysis(sheet)`, `report(sheet, which)` (swaps `analysis_host.controls`), `render(sheet) -> list[ft.Control]`, `refresh(e=None)` (threaded worker).
`render` block order (128-161): (1) `notice("Synthetic data: " + sheet.note, "error", icon=SCIENCE_OUTLINED)` if `sheet.synthetic_ids`, elif note → muted notice; (2) chip row `as of {sheet.as_of}` + `{src}: {n}` per source (`"SYNTHETIC"` → error else success); (3) regime chip row `curve: / risk: / dollar: / breakevens: / real yields:`; (4) `rg.summary` text size 12 muted; (5) headline `stat` tiles (token error when `abs(z_1y) >= 2`); (6) table; (7) `card(fcharts.macro_z_chart(sheet))`; (8) two report buttons; (9) `analysis_host`.
Core inputs: `core.ficc.macro.macro_sheet(*, source: str = "auto", days: int = 504) -> MacroSheet`; `MacroSheet(as_of, rows: tuple[MacroRow, ...], regime: Regime, sources: dict[str, int], synthetic_ids: tuple[str, ...], note="")` + `.row(id)`; `MacroRow(id, label, group, unit, last, last_date, chg_1d, chg_1w, chg_1m, chg_3m, z_1y, pct_1y, source)`; `Regime(curve, risk, dollar, inflation, real_rates, summary)`; `daily_brief(sheet, *, top=5) -> dict`; `weekly_brief(sheet, curve_report=None, carry_rows=None) -> dict`; `core.ficc.insights.narrate_macro / narrate_daily_brief / narrate_weekly_strategy / report_prompt(kind) / deep_analysis`.
Errors: `(FICCError, ValueError)` → `notice(str(exc), "error", icon=ERROR_OUTLINE)`; any other `Exception` → `notice(f"{type(exc).__name__}: {exc}", ...)`. Initial state is an `empty_state` with an "Open Settings" action; nothing is fetched until Refresh. `__main__` self-check (206-232) asserts the formatters on synthetic rows.

### A.12 `ui/strategy_lab_page.py` — the existing model-card view

- `ROOT = Path(__file__).resolve().parents[1]`; `CARDS_DIR = ROOT / "docs" / "asset_expansion" / "cards"` (30-31).
- `_TOKEN = {"PASS": "success", "REVISE": "accent", "REJECT": "error", "INSUFFICIENT_DATA": "muted"}` (32); lookups use `_TOKEN.get(x, "muted")`.
- `FAMILIES` (34-46): `key → (label, weight_fn, grid, embargo)`; keys `trend_switch, vol_target, xs_momentum, tsmom, crypto_trend, risk_parity, pairs` (pairs fn is `None`, wrapped at run time).
- `run_family(family: str, symbols: list[str], *, source: str = "auto", cost_bps: float = 10.0, days: int = 5000, bootstrap_B: int = 1000) -> dict` (49) → keys `family, label, symbols, sources, notes, convention, panel, score, wf, equity, bench_equity, grid, chosen, cost_bps`. Uses `rf = 0.03 / 252`; **mutates the module global `V.GATE["bootstrap_B"]`** (70); raises `ValueError("pairs needs exactly two symbols: y then x")`.
- `narrative(r: dict) -> str` (80); `payload(r: dict) -> dict` (88).
- `build_strategy_lab_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control` (96).
- `load_cards() -> list[dict]` (221): `sorted(V.load_cards(CARDS_DIR), key=lambda c: ({"PASS": 0, "REVISE": 1, "REJECT": 2}.get(c.get("decision"), 3), c["card_id"]))`.
Card dict contract the page relies on (written by `core.quant.validate.ModelCard`, `validate.py:734-766`; 34 files on disk: 17 `strategy`, 9 `distribution`, 8 `model`; 5 PASS / 11 REVISE / 18 REJECT):
  - indexed with `[]` (KeyError if absent, raised **during page build, outside any worker**): `card_id`, `decision`, `kind`, `hypothesis`, `decision_reason`;
  - `.get`: `seed`, `results_md5`, `revise_target`, `lines`, `citations`, `stats` (`sr_oos`, `dsr`, `pbo` when a strategy), `tests`.
  - Full schema: `card_id, kind, hypothesis, rules, universe, data, costs, protocol, trials, seed, stats, tests, decision, decision_reason, revise_target, lines, decay_haircut, created, author, results_file, results_md5, citations`. `core.quant.validate.DECISIONS = ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")` (`validate.py:50`).
Section 1 "Validation scorecard": count chips per decision, a `ft.DataTable` with columns `("Card", "Kind", "Decision", "Reason", "Key numbers")` (decision cell is a `chip`; reason truncated to 70 chars), a `ft.Dropdown(label="Card")` whose `on_select` fills `detail` (decision chip, kind chip, `seed`, `results md5` first 8 chars, hypothesis italic, `Decision: …`, bullet lines, `Sources: …`). Empty directory → `notice("No cards yet: run python docs/asset_expansion_study.py", "accent")`.
Section 2 "Run a family through the gate": threaded; shows decision chip, 11 `stat` tiles (OOS Sharpe, Deflated Sharpe `>= 0.95`, PBO `<= 0.05`, OOS / IS, 2× costs, Years positive, Plateau, Trades, Max DD, Benchmark SR, Haircut SR), `xc.equity_chart`, bullet lines, `analysis_panel(kind="strategy_gate")`. Synthetic panel → `notice("Synthetic data in the panel: the verdict below is a toy.", "error")`.

### A.13 `ui/quant_lab_page.py`

Constants: `_SOURCES`, `_MODEL_LABELS` (`garch_t`, `gbm`, `jump`, `bootstrap`), `_DRIFTS` (`premium`, `zero`, `rf`, `sample`), `_DRIFT_SHORT`, `_RF_ASSUMED = 0.03`. Helpers: `_fmt_sessions`, `_fmt_pct` (`"n/a"` on NaN), `_fmt_nu`, `_with_interval(fit, name, value, fmt)`, `_risk_free(symbol: str = "") -> tuple[float, ft.Control]` (66; never raises; fallback chip `"rf 3.00% assumed (FRED unreachable)"` in error tone), `_garch_blocks(fit, horizon_vol: float) -> list[ft.Control]` (88; second stat strip + one chip per guardrail flag), `_study_chips() -> list[ft.Control]` (151; reads cards `D_Q_garch_spy`, `D_Q_garch_kodex200`, `D_Q_skewt_spy`, `D_Q_skewt_kodex200`; returns `[]` on any exception). `build_quant_lab_page(page, on_open_settings=None)` (177). `__main__` (341-389) is the reference headless UI driver: fake page `SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None)` + a `walk(c)` generator over `controls/rows/cells/columns/content/label`, then clicks `run_btn.on_click(None)` and asserts on rendered `ft.Text` values.

### A.14 `ui/signals_page.py`

`_signed_bar(score: float) -> ft.Control` (33; -100..100 centred bar), `_signal_block(report: SignalReport) -> ft.Control` (58; stance token `> 15 success`, `< -15 error`, else muted), `build_signals_page(page, on_open_settings=None)` (94). Displays `core.quant.signals.compute_signals(hist) -> SignalReport(symbol, last_price, composite, stance, components[label, score, weight, reason, value])` above `core.quant.backtest.run_backtest(hist, strategy=, params=, cost_bps=)`; `STRATEGIES` keys `ma_cross`, `momentum`, `rsi_revert`. v2 family tags / priors-as-filters (R-15) and the tech-fund weight table land next to this composite — the component row layout (label 170 px, bar, score 44 px, weight 32 px, reason line) is the existing pattern for "weight + reason" rows.

### A.15 `ui/etf_page.py`

`LETF` (34-36): `code → (beta, name, fee)` for `122630, 252670, 114800, 233740, 251340` (fee `0.0064`). `_CARD_FOR = {"trend": ("S_E1_trend_krx", "S_E1_trend_us"), "vol": ("S_E2_voltarget_kodex200", "S_E2_voltarget_spy")}` (index 0 for KRX, 1 otherwise). `_clean(code)`; `analyze(code: str, *, days: int = 504, source: str = "auto") -> dict` (45; keys `code, source, is_krx, quote, dates, price, nav, premium_pct, components, data_source, note, sleeve_dates, sleeve_basis, premium_stats{last, mean, sd, z, adf_p, half_life, abs_mean}, sleeves{trend, vol_target, buy_hold, equity_trend, equity_bh, cost_bps, exposure_trend}, letf{…}, verdicts{trend, vol}, verdict_reasons`); `narrative(a)`, `payload(a)`, `build_etf_page(page, on_open_settings=None)` (176). Conventions hard-coded in the page module: sleeve cost `3.0` bp (KRX) / `50.0` bp (other) per side, `rf = 0.03 / 252`, trend `rule="sma", lookback=210, step=21`, vol target `target=0.12, window=22, step=21`. Verdict display: `stat("Study verdict: trend", verdict, token="success" if verdict == "PASS" else "error", tooltip=reason)`; missing card → `"not run"`. Degradation: adjusted-close failure keeps raw close and writes `sleeve_basis = "raw NAV-series close, NOT split-adjusted (KIS 수정주가 unavailable: …)"` (72); LETF failure → `out["letf"] = {"beta", "name", "error"}`.

### A.16 `ui/crypto_page.py`

`MAJORS` (8 USDT pairs), `CRYPTO_DAYS = 365`. `_synthetic() -> dict`, `_live(days: int) -> dict`, `analyze(*, days: int = 730, source: str = "live") -> dict` (67; keys `source` (`"LIVE"`/`"SYNTHETIC"`), `usdkrw_source, kimchi, funding, funding_error, regime, ethbtc, weekday, garch{…}, premium_index, oi, btc_dates, btc, balances, balances_error, verdicts`), `narrative(a)`, `payload(a)`, `build_crypto_page(page, on_open_settings=None)` (147). Verdict chips for 7 card ids: `chip(f"{k.split('_', 2)[-1]}: {v}", "success" if v == "PASS" else "muted")` (173). Always-on read-only notice (166-168): `notice("Read-only: QUANTGEN never submits crypto orders, …", "accent", icon=ft.Icons.LOCK_OUTLINE)` — the wording model for v2 "not a recommendation" / read-only labels. Monospace table rows are plain `ft.Text(..., font_family="Consolas, monospace")` inside a `card`.

### A.17 `ui/param_form.py`

`class ParamForm(page, spec: Spec, *, on_change=None, initial=None)`; properties `control`, `subcommand`; methods `values() -> dict`, `missing() -> tuple[str, ...]`, `argv() -> tuple[str, ...]`, `preview() -> str`, `highlight(flags: tuple[str, ...]) -> None`. `_HELPER_ATTRS = ("helper", "helper_text")` with `_set_helper/_get_helper` (57-68): the sanctioned way to set a sub-label on either a TextField (`helper`) or a Dropdown (`helper_text`). Generated from `core.skills.params.Spec`; used by Skills and Workflows pages only. Not needed by v2 displays.

### A.18 `ui/settings_page.py`

`_SIGNUP` (24-37; provider id → sign-up text), `_ficc_status() -> list[dict]` (40; tolerant wrapper), `build_settings_page(page: ft.Page, *, on_reload: Optional[Callable] = None) -> ft.Control` (52). Provider entries are dicts `{"id", "label", "ready", "vars", "note"}` from `config.quant_provider_status()`, `config.ficc_provider_status()`, `config.skill_provider_status()`, `config.krx_provider_status()`, `config.crypto_provider_status()`; rendered by `provider_row(entry)` in `ft.ResponsiveRow([... col={"xs": 12, "md": 6}], spacing=10, run_spacing=10)`. Four probe buttons (KRX, FICC, KIS, crypto) each: replace host with ProgressRing(16) + text, `page.run_thread(worker)`, worker wraps the probe in `try/except Exception` and renders chips. Presence only: the page must never contain `kis_credentials()`, `opendart_key()` or `_clean(` (test_13). Root is `ft.Column(controls, spacing=14, expand=True, scroll=ft.ScrollMode.AUTO)`.

### A.19 `ui/trading_page.py` (reference for the HALTED banner)

`MODE_STYLE: dict[EngineMode, tuple[str, str, str]]` (30-34): `DISARMED → ("DISARMED", "muted", PAUSE_CIRCLE_OUTLINE)`, `ARMED → ("ARMED", "success", PLAY_CIRCLE_OUTLINE)`, `HALTED → ("HALTED", "error", REPORT_PROBLEM_OUTLINED)`; `OUTCOME_STYLE` (36-41). `state_banner(data: dict)` (123-193): `ft.Container(ft.Column(lines, spacing=8), padding=18, bgcolor=pal.surface, border=ft.Border.all(1, colour), border_radius=RADII["lg"])` with icon size 26 + label size 22 BOLD in the mode colour, buttons on the right, then reason text (`f"Stopped because of {reason.replace('_', ' ')}. {detail}"`) and the sentence "This program never re-arms itself. Acknowledge the halt, …". Acknowledge button appears when `data["needs_ack"]`. Data source `runtime.dashboard()`; live repaint via `runtime.on_update = refresh` (71) called from the engine thread, `page.update()` wrapped in `try/except`. `toast()` = `page.show_dialog(ft.SnackBar(ft.Text(message, color=pal.text), bgcolor=pal.surface_2))`. This banner is for the single global engine; v2 needs one state **per book** (SPEC:836, 3608-3623).

---

## B. Cross-file flows

### B.1 Page skeleton (every analysis page follows it)

```python
def build_x_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control:
    pal = active()
    <inputs>: ft.TextField(label=..., value=..., width=..., border_radius=RADII["md"]); ft.Dropdown(label=..., width=..., value=..., options=[ft.dropdown.Option(k, v) ...])
    busy = ft.ProgressRing(visible=False, width=20, height=20)
    result_host = ft.Column(spacing=14)

    def run(e=None) -> None:
        busy.visible = True; result_host.controls = []; page.update()
        def worker():
            try:
                <parse inputs>; <call core>
            except (DomainError, ValueError) as exc:
                result_host.controls = [notice(str(exc), "error", icon=ft.Icons.ERROR_OUTLINE)]; busy.visible = False; page.update(); return
            except Exception as exc:
                result_host.controls = [notice(f"{type(exc).__name__}: {exc}", "error", icon=ft.Icons.ERROR_OUTLINE)]; busy.visible = False; page.update(); return
            blocks = [...]            # notices → chip row → stat row → card(chart) → table → analysis_panel
            result_host.controls = blocks; busy.visible = False; page.update()
        page.run_thread(worker)

    result_host.controls = [empty_state(title, detail, icon=..., action=ft.Button("Open Settings", on_click=lambda e: on_open_settings()) if on_open_settings else None)]
    return ft.Column([
        section("Title", subtitle="…"),
        ft.Row([<inputs>, ft.Button("Run", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=run), busy], spacing=10, wrap=True),
        ft.Column([result_host], scroll=ft.ScrollMode.AUTO, expand=True),
    ], spacing=14, expand=True)
```
`main.navigate` wraps the returned control in `ft.Container(..., padding=24, expand=True)`.

### B.2 Scale as built

| Element | Values |
|---|---|
| Type | page title 26 BOLD; sub-section heading 15 W_600; card title 13-14 W_600; body / narrative 13; detail lines, key-value 12; table cells, chips, captions 11; stat label, bar captions 10; stat value 16 W_600; trading tile value 24 BOLD; state banner 22 BOLD; mono `"Consolas, monospace"` 11-12 |
| Spacing | page column 14; result host 14; input row 10 (wrap); stat row 10 (wrap); chip row 6 (wrap); bullet-line column 3-6; page padding 24 |
| Radii | inputs, notices, stat tiles, nav items `md` 12; cards, banners, analysis panel `lg` 16; bars `sm` 8; chips `pill` 999 |
| Padding | card 16; notice 14; stat `(14, 10, 14, 10)`; chip `(8, 3, 8, 3)`; empty state 48; banner 18; code well 12 |
| Tables | `ft.DataTable(columns=[ft.DataColumn(ft.Text(c, size=11, color=pal.muted), numeric=…)], rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(v, size=11))])], column_spacing=14..18, heading_row_height=32..34, data_row_max_height=32..34)` wrapped in `ft.Row([table], scroll=ft.ScrollMode.AUTO)`; long text column: `ft.Text(str(v), size=11, width=460)` with `data_row_min_height=34, data_row_max_height=88` (`structuring_page.py:119-130`) |
| Grids | `ft.ResponsiveRow([... col={"xs": 12, "md": 6}], spacing=10, run_spacing=10)`; tiles `col={"xs": 6, "md": 3}`; master/detail `{"xs": 12, "md": 5, "lg": 4}` / `{"xs": 12, "md": 7, "lg": 8}` |
| Charts | DPI 110; 7.5 in (qcharts/fcharts) or 9.5 in (xcharts) wide, 2.6-4.2 in tall; always inside `card(...)` |
| Status vocabulary | success = good/ready/PASS/live source; error = bad/REJECT/SYNTHETIC/at-bound; accent = informational/REVISE/needs input; muted = neutral/not run/cached |

### B.3 Threading

- Only mechanism: `page.run_thread(worker)` (sync signature `(handler, *args, **kwargs) -> None`). `page.run_task` (async) is never used. Worker mutates controls then calls `page.update()`; the busy ring is toggled before and after.
- Nothing may raise out of an event handler or worker (guard docstring `flet_api_guard.py:9-11`: an exception in a handler "takes down the whole application"). Hence the two-tier `except`.
- Chart functions run inside workers; `matplotlib.use("Agg")` in `ui/qcharts.py:20` must stay ahead of any pyplot import (fcharts/xcharts import `plt` and helpers from qcharts).
- Engine-driven repaint: `runtime.on_update = refresh` (`trading_page.py:71`), called from the engine thread; `page.update()` inside `try/except` because the page may be detached. `trading` is rebuilt on every navigation (`main.py:164`), which re-binds `on_update`.
- Headless tests replace the page with `SimpleNamespace(run_thread=lambda fn: fn(), update=lambda: None)`.

### B.4 Who calls whom

`main.build` → `ui.<page>.build_*_page` → (`core.theme.active`, `ui.components.*`, `ui.ai_panel.analysis_panel`, one chart module) → core (`core.ficc.*`, `core.quant.*`, `core.crypto.analytics`, `data.*`). Chart modules: `fcharts`, `xcharts` → `qcharts._fig/_style/_to_image/_thin_dates`. `charts.py` → `components.chip/colour_for`. Pages never import each other. Model-card JSON is read by four UI modules through `core.quant.validate.load_cards(directory: Path) -> list[dict]` (`validate.py:779`; skips unparseable files, `[]` when the directory is missing): `strategy_lab_page.py:31/222`, `quant_lab_page.py:157-159`, `etf_page.py:120`, `crypto_page.py:100-102` — the path `…/docs/asset_expansion/cards` is constructed separately in each.

### B.5 Persistence and environment

| Location | Reader / writer |
|---|---|
| `docs/asset_expansion/cards/*.json` (34 cards; written by `docs/asset_expansion_study.py` via `ModelCard.save`) | read by Strategy Lab, Quant Lab, ETF, Crypto |
| `~/.nextgen/runs/<run_id>/` (`config.runs_dir()`, env `NEXTGEN_RUNS_DIR`) | Runs page reads; Workflows page writes `decision_step{n}.json` (`workflows_page.py:624-646`) — the only file the UI layer writes |
| `~/.nextgen/trading` (`config.trading_dir()`, env `NEXTGEN_TRADING_DIR`) | rules JSON, simulated order book, engine halt state (core) |
| `~/.nextgen/ficc_cache` (`config.ficc_cache_dir()`, env `NEXTGEN_FICC_CACHE`; TTL `NEXTGEN_FICC_CACHE_TTL`, default 6 h) | FICC/Yahoo/crypto fetch cache |
| `qa/acceptance_results.json` | written by `tests/run_all.py` |
| `assets/` | icons; `ft.run(main, assets_dir="assets")` |
| No UI preference file | theme/mode/locale are constants in code |

There is **no macro artifact directory function in `config.py`** (spec proposes one: SPEC:797). Existing naming pattern: `def trading_dir() -> Path: override = _clean("NEXTGEN_TRADING_DIR"); return Path(override) if override else (Path.home() / ".nextgen" / "trading")` (`config.py:236-238`).
Env vars that change what the UI shows: `ANTHROPIC_API_KEY` (enables Deep analysis), `QUANTGEN_AI_MODEL` (default `claude-sonnet-5`), `KIS_APP_KEY` + `KIS_APP_SECRET` (ETF KRX path, derivatives default board), `UPBIT_ACCESS_KEY` + `UPBIT_SECRET_KEY` (crypto holdings), `FMP_API_KEY`, `OPENDART_API_KEY`, `KRX_API_KEY`, `GS_CLIENT_ID` + `GS_CLIENT_SECRET`, `NEXTGEN_SKILLS_ROOT`, `NEXTGEN_SKILL_TIMEOUT`, `NEXTGEN_HTTP_TIMEOUT`, `NEXTGEN_ENGINE_TICK`, `NEXTGEN_NO_DATA_GRACE`, `NEXTGEN_QUOTE_MAX_AGE`. `.env` is loaded by `config.py` through `python-dotenv`; values are never shown in a widget.

---

## C. Tests covering this subsystem

Runner: `python tests/run_all.py` → 266 checks today (cockpit 47, engine 89, ui 4, quant 53, ficc 56, expansion 17), writes `qa/acceptance_results.json`, exit 0 iff all pass. No pytest. stdout/stderr are reconfigured to UTF-8 (`run_all.py:24-28`).

| File | Test | Asserts |
|---|---|---|
| `tests/flet_api_guard.py` | `test_page_methods_exist` | every `page.<attr>(...)` call (receiver is the bare name `page`) names a public attribute of `ft.Page` |
| | `test_control_keywords_exist` | every keyword of `ft.<C>(...)` for C in `_CHECKED_CONTROLS` is an `__init__` parameter (`**splat` skipped) |
| | `test_control_attribute_assignments_exist` | `name.attr = …` where `name` was assigned in that file only from one `ft.<Control>` type: `attr` is an `__init__` parameter or `hasattr(class, attr)` |
| | `test_theme_tokens_referenced_by_ui_exist` | every `pal.<x>` attribute is one of the 11 palette fields |
| `tests/acceptance.py` | `test_08_no_broker_order_path` | none of `order_cash, order-cash, place_order, submit_order, TTTC0802U, TTTC0801U, VTTC0802U` (case-insensitive) appears in any `.py` under `core/`, `data/`, `ui/` (recursive), `main.py`, `config.py` |
| | `test_09_no_account_credentials_requested` | none of `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD` (case-sensitive raw substring, comments and strings included) in the same files |
| | `test_13_settings_page_shows_presence_not_values` | `ui/settings_page.py` source has no `kis_credentials()`, `opendart_key()`, `_clean(` |
| | `test_14_page_resize_handler_matches_the_flet_api` | `ft.Page` has `on_resize`; `main.py` code assigns `page.on_resize =` and not `on_resized` |
| | `test_15_views_are_cached_across_navigation` | `main.py` source contains the literal `cache[name] = build(` |
| | `test_16_every_source_file_is_utf8_readable` | all runtime `.py` decode as UTF-8 |
| | `test_32_workflow_steps_are_never_launched_with_an_empty_command_line` | no `*.run_skill(x, ())` / `[]` literal in `ui/*.py` |
| | `test_42_the_gate_reads_its_answers_rather_than_hard_coding_them` | `ui/workflows_page.py` has `show_gate` calling `options_for` and `_digest` |
| `tests/quant_acceptance.py` | `test_every_chart_renders_a_data_uri_image` | 7 qcharts functions return `ft.Image` whose `src` starts with `data:image/png;base64,` and `len(src) > 1000` (after `set_mode("dark")`) |
| `tests/ficc_acceptance.py` | `test_every_fchart_renders_a_data_uri_image` | 15 fcharts images, same assertions |
| `tests/expansion_acceptance.py` | `test_etf_page_sleeves_use_adjusted_closes_and_survive_their_loss` (registered as `etf_page_adjusted_sleeves`) | `ui.etf_page.analyze` uses split-adjusted closes for sleeves, keeps quote/premium/basket when the adjusted series fails, and labels `sleeve_basis` with `NOT split-adjusted` |

Not covered by `run_all`: `ui/xcharts.py` (no chart test), `ui/components.py`, `ui/ai_panel.py`, and every page builder. Eleven UI modules carry an offline `if __name__ == "__main__":` self-check (`bonds, crypto, derivatives, etf, fcharts, fx, macro, quant_lab, rates, strategy_lab, structuring`) that is **not** registered; only core self-checks are (`expansion_acceptance.py:316-324`).

Registering new tests:
- A suite module exposes `tests() -> list[tuple[str, Callable]]`. `acceptance`, `engine_acceptance`, `flet_api_guard`, `quant_acceptance`, `ficc_acceptance` auto-collect every module-level `test_*` callable from `globals()` (sorted by name); `expansion_acceptance.tests()` is an explicit list.
- A new suite file needs two edits in `tests/run_all.py`: an import (30-35) and a line in `tests()` (38-44) with a prefix (`cockpit/`, `engine/`, `ui/`, `quant/`, `ficc/`, `expansion/`).
- A module self-check becomes a test with `("selfcheck_<name>", _selfcheck("ui/<file>.py"))` (`_selfcheck(rel)` runs `runpy.run_path(..., run_name="__main__")`, `expansion_acceptance.py:28-33`).
- Tests must be hermetic (patch network touchpoints), read files with `encoding="utf-8"` (test_17), and a new `ui/*.py` file is linted by the guard automatically.

---

## D. Extension points for v2

### D.1 What the specs ask the UI to show (binding names verbatim)

Spec statements: SPEC:761-763 (UI box: "macro_state panel, overlay_decision table, card verdict and disposition badges, relative and absolute vol labels, event calendar, context log, owner decisions D1–D5 (proposed). No regime-model state is displayed (P19)."); SPEC:1127-1133 (brief's macro_state section: vt and vs weights and both vol labels; flags and annotations; each card's verdict and disposition; FORWARD-SIM cards and refusal books marked "not a recommendation"; open owner decisions; event calendar); SPEC:1248 (alert sink: "a Macro-page banner (always; page alerts persist until acknowledged)"); TASK-M6-06 (`QUANTGEN_V2_TASKS.json`: panel, overlay_decision table, verdict and disposition badge, both volatility labels, event calendar, context log, every open owner decision D1–D6 with value and status; acceptance "§12 M6: the Macro page lists every open owner decision", T-DNB-01 "A displayed field whose source is a regime model is refused by validation"); TASK-M8-06 (T-OBS-03 "Page-severity alerts persist until acknowledged"); TASK-M9-02 (Quant Lab self-grading display, I-11); TASK-M5-14 ("the D2 owner page": invariants-only book with and without the −15% hard stop beside D2).

Fields to render, from schema `quantgen/macro_state.v2.0` (SPEC:3524-3652), one artifact per market per decision:

| Panel element | Source field(s) | Enum / bound (verbatim) |
|---|---|---|
| Header chips | `market`, `decided_session`, `effective_session`, `decision_utc`, `run_mode`, `read_only` | `market ∈ ["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]`; `run_mode ∈ ["live","backtest","replay"]`; `read_only` const `true` |
| vt | `vol.vt_weight_next` (specification book), `vol.vt_weight_recommended_book`, `vol.sigma_ann`, `vol.target_ann`, `vol.vt_status`, `vol.estimator`, `vol.estimator_b5`, `vol.estimator_gate.status`, `vol.instrument_book`, `vol.rebalance` | weights `0..1`; `vt_status ∈ ["ok","warmup","fail_closed"]`; `estimator ∈ ["sma20","ewma094","ewma097","garch_t","gjr_t","log_har_range","comb"]`; `estimator_b5 ∈ ["PASS","FAIL","NOT_RUN"]`; gate status `["registered_default","challenger_selected","fallback_to_sma20","NOT_RUN"]` |
| Vol labels (display only, never gating) | `vol.display_label_rel`, `vol.display_label_abs` (+ `label_method_rel` = `trailing756_quartiles_causal_filtered`, `label_method_abs` = `expanding_full_history_quartiles_causal_filtered`) | `["calm","normal","elevated","stressed"]` — volatility labels, not regime states (SPEC:655) |
| Composed multiplier per book | `concentration.by_book[book_id].composed`, `.gross`, `.binding_factor` | `0..1`; `binding_factor ∈ ["none","absolute_single_name","active_single_name","aggregate","semis"]`. Composition is `min()`: composed = vt × min(1.0, overlays, ladder, post_rearm_cap) ≥ 0.5 × vt (SPEC:821, 4793); nothing above 1.0 |
| Overlays table | `overlay_decision` (SPEC:3719-3763), one per market × family: `family`, `exposure_basis`, `vol_scale`, `vol_scale_recommended_book`, `multipliers[] {rule_id, value, exposure_basis, card}`, `ladder`, `post_rearm_cap`, `composition`, `overlay_min`, `overlay_applied_spec_book`, `overlay_applied_recommended_book`, `forward_sim[]`, `refusal[]`, `binding[]`, `reasons[]` | `family ∈ ["momentum","reversal","flow","quality","ts_trend","market_gross"]`; `exposure_basis ∈ ["active","total"]`; multiplier `value` 0.5..1.0; `ladder`, `post_rearm_cap ∈ [0.5, 1.0, null]`; `composition` const `"min"`; `overlay_floor` const 0.5; `overlay_cap` const 1.0 |
| Ladder state | `flags.ladder_step`, `flags.ladder_dwell_left`, `flags.block_new_entries`, `flags.ladder_steps_act_in`, `flags.hard_stop`, `flags.hard_stop_level` | `ladder_step ∈ ["none","step_-8","step_-12","hard_stop_-15"]`; `ladder_steps_act_in ∈ ["recommended","specification"]`; `hard_stop ∈ ["armed","halted","rearm_refused","post_rearm_cap"]` |
| HALTED banner (per book) | `runtime[] {book_id, engine_state, halt{class, reason_code, component, series_id, since_utc, rearm_not_before, rearm_mode, causes[], ack_by, ack_utc}, post_rearm_cap_until, nav, hwm_hard, ref_step, consecutive_failures, book_counter}`, `flags.engine_state`, `fail_closed` | `engine_state ∈ ["DISARMED","ARMED","HALTED"]`; `halt.class ∈ ["RISK","OPS"]`; `rearm_mode ∈ ["auto","operator"]`; `book_id` forms `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>` |
| Hedge / flags | `flags.hedge_credit_off`, `hedge_failure`, `classic_risk_off`, `hedge_reasons[]`, `hedge_stale_inputs[]`, `fx_hedge_credit`, `kr_open_gap_event`, `gap_sessions`, `var_display_scale`, `dm_bear_state`; `annotations.vix_ge_vix3m`, `annotations.notes[]` | `hedge_reasons ∈ ["ok","risk_model_input_stale","risk_model_exception","corr_positive","core_pce_ge_3"]` |
| Alerts | `alerts[] {alert_id, code, severity, component, series_id, books[], first_seen_utc, count, escalated, ack_utc}` | `severity ∈ ["info","warn","page"]`; page alerts persist until acknowledged |
| Owner decisions | `owner_decisions{<canonical key>: {decision, value, status}}` | `decision ∈ ["D1","D2","D3","D4","D5","D6"]`; `status ∈ ["default","owner_set","pending"]` |
| Inputs / staleness | `inputs[] {name, series_id, source, obs_date, value, value_status, role, books, status, stale_deadline_utc, dispute, …}`, `lag_audit {checked, violations[]}` | `value_status ∈ ["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]`; `role ∈ ["acting_exposure","forward_sim","risk_model","context","history"]`; `status ∈ ["ok","stale","stale_missed_release","missing","provisional_rejected","session_mismatch","synthetic_rejected","disputed","warmup"]` |
| Display-only books | `refusal_books {S1_krw_flag, S2_rates_flag}`, `forward_sim {R28_below_sma10m, R29_vt_weight_next}` | must be marked "not a recommendation" |
| Context log | `quantgen/context_log.v2.0` (SPEC:3868): required `…, decision_utc, as_of_utc, items, acts` | never acts |

Card badges, schema `$defs.card` (SPEC:3757-3762) and `model_card.macro` (SPEC:4007, 4012):
- `class ∈ ["CARD-O","CARD-P"]`.
- `verdict ∈ ["PASS","REVISE","REJECT","INSUFFICIENT_DATA","NOT_RUN"]` on an overlay_decision card; a written model card has `["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]`.
- `disposition ∈ ["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]`.
- `displayed_as ∈ ["recommendation","insurance","invariant","descriptive","refusal"]`; rule (SPEC:3767): `displayed_as ∈ {"recommendation","insurance"}` iff `verdict = "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`; `"invariant"` iff `disposition = INVARIANT_STEP`.
- `label`: "the text displayed with the verdict, byte-identical to the rule's label" (SPEC:3938) — print it verbatim, do not compose it in the UI.
- BUILD-AS-INSURANCE "is not a fifth verdict" (SPEC:4786): render it as a second (disposition) chip beside the verdict chip, with the insurance label and premium shown.
- Every verdict carries a reason code: `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id (SPEC:4779).

Tech-fund tables (data already on disk, UTF-8 CSV):
- Weight table: `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/datalab/results/r3/r3_weights_final.csv` — header `market, family, column, prior, professors, executives, final, rule, reason, nodes` (50 rows); `…/r3_weights_other_markets.csv` — header `market, XS-mom, ST-rev, value, quality, low-vol, flow, earn drift, TS-mom, exec TS trend alpha / protective` (6 rows). Caption text to carry (R3:703): "Weights are 0-3 design priors, not gate results; any weight of 2 or more still needs a PASS card before it can feed the displayed book. Proposed normalisation base_weight = w / 3 (never above 1.0x)."
- Go/no-go register: `…/datalab/results/r3/r3_go_nogo.csv` — header `id, item, market, decision, ruling, evidence_for, evidence_against, indicative_gate, what_would_change_it, nodes, target`; 77 rows `G-01..G-77`; groups in R3:794-878: BUILD NOW / INVARIANT / GOVERNANCE, FORWARD-SIM, BACKLOG, OWNER DECISION and CONTEXT, DROP and DO-NOT-BUILD.
- Offline pages (the only two `.html` files in the repo): `QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Quant_Council.html` (363,667 bytes, title "QUANTGEN Quant Council") and `QUANTGEN_Quant_Council_2026-10-03/pages/QUANTGEN_Macro_Neural_Link.html` (373,902 bytes, title "QUANTGEN Macro Neural Link"); self-contained, open in any browser.

### D.2 Where each surface lives; what to reuse

| v2 surface | Put it in | Reuse (do not duplicate) | New code needed |
|---|---|---|---|
| Macro state per market | `ui/macro_page.py`, as an extra section above the existing sheet (TASK-M6-06 package: "ui/ Macro page"); if the file grows, a flat sibling `ui/macro_state_panel.py` exposing `macro_state_blocks(state: dict, decisions: list[dict]) -> list[ft.Control]` | `stat` (vt, composed, σ̂), `chip` (labels, flags, statuses), `notice` (alerts), `card`, `key_value` (provenance), the `table()` DataTable idiom at `macro_page.py:84-103` | a pure dict → blocks renderer; a market selector (`ft.Dropdown`, `on_select`) |
| HALTED banner | same module | `trading_page.MODE_STYLE` vocabulary and the `state_banner` container recipe (`trading_page.py:189-193`); `notice(text, "error", icon=ft.Icons.REPORT_PROBLEM_OUTLINED, action=ft.Button("Acknowledge", …))` already gives a bordered banner with an action slot | one banner per `runtime[]` entry whose `engine_state == "HALTED"`; text from `halt.class`, `halt.reason_code`, `halt.since_utc`, `halt.rearm_mode`, `halt.rearm_not_before` |
| Alerts | same module | `notice` with token by severity: `page → "error"`, `warn → "accent"`, `info → "muted"` | acknowledge action must call a core function that records `ack_utc`; the UI holds no alert state |
| Owner decisions D1–D6 | same module | `key_value` or a 4-column DataTable (`decision`, canonical key, `value`, `status`); `chip(status, token)` with `pending → "accent"`, `owner_set → "success"`, `default → "muted"` | read-only display; the rules store owns the values |
| Context log | same module, collapsed by default | `ft.ExpansionTile(title=…, controls=[…], expanded=False)` exactly as `param_form.py:294-301` (ExpansionTile is a guard-checked control) | — |
| Model-card view (CARD-O / CARD-P) | extend `ui/strategy_lab_page.py` section 1 (SPEC:845 "model cards … → Strategy Lab"; SPEC:3911 "Map them onto the app's actual card format; do not run a parallel registry") | `_TOKEN`, `load_cards()`, the scorecard DataTable + Dropdown + detail column; `core.quant.validate.load_cards` | an adapter that maps a macro card (`verdict`, `class`, `disposition`, `displayed_as`, `label`, `claim`) onto the keys the page indexes (`decision`, `kind`, `hypothesis`, `decision_reason`); a second chip for disposition |
| Verdict chips | one shared helper in `ui/components.py`, e.g. `verdict_chip(verdict: str, *, tooltip: str = "") -> ft.Container` driven by a `VERDICT_STYLE: dict[str, tuple[str, str]]` map beside `STATE_STYLE` | `chip`; today's four mappings from `_TOKEN` | proposed map (labels as displayed, token): `PASS → ("PASS","success")`, `REVISE → ("REVISE","accent")`, `REJECT → ("REJECT","error")`, `INSUFFICIENT_DATA → ("INSUFFICIENT DATA","muted")`, `NOT_RUN → ("NOT RUN","muted")`, `UNVERIFIED → ("UNVERIFIED","muted")`; disposition chips: `BUILD_AS_INSURANCE → ("BUILD-AS-INSURANCE","accent")`, `FORWARD_SIM → ("FORWARD-SIM · not a recommendation","muted")`, `REFUSAL_BOOK → ("REFUSAL BOOK · not a recommendation","muted")`, `SPECIFICATION_ONLY → ("SPECIFICATION BOOK","muted")`, `INVARIANT_STEP → ("INVARIANT","accent")`, `RECOMMENDATION → ("RECOMMENDATION","success")`, `DESCRIPTIVE → ("DESCRIPTIVE","muted")`. Then replace the four ad-hoc PASS tests in `etf_page.py:225,233,235`, `crypto_page.py:173`, `quant_lab_page.py:167,172` only if touching those lines anyway |
| Refusal book view | Strategy Lab (cards with disposition `REFUSAL_BOOK`) and a labelled row group on the Macro panel | `chip`, DataTable; the crypto read-only `notice` wording pattern | a fixed "not a recommendation" label on every row; never styled with `success` |
| Tech-fund weight table and go/no-go register | Strategy Lab (governance record) or a new flat page `ui/research_page.py` if a nav entry is wanted | the long-text table recipe `structuring_page._table` (`width=460`, `data_row_max_height=88`); `chip` for `final` weight and `decision`; a filter `ft.Dropdown` by market / decision group | CSV loading with `csv` + `encoding="utf-8-sig"` in a small core loader (keep I/O out of the page so it is testable); 77 rows x 11 columns is too wide for one DataTable row — show `id, item, market, decision, indicative_gate, target` in the table and the long evidence columns in a detail pane (Dropdown → detail, as the card view does) |
| Links to the two HTML pages | buttons on the Macro page header row and/or Strategy Lab | `runs_page.open_folder` (`runs_page.py:37-44`): `os.startfile(str(path))` on `os.name == "nt"`, `subprocess.run(["xdg-open", str(path)], check=False)` otherwise, wrapped in `try/except Exception: pass`; lift it into `ui/components.py` as a shared `open_path(path)` rather than copying. Alternatives present in Flet 0.85.2: `ft.Button(url=…)` and `page.launch_url(url)` (sync) | check `path.is_file()` first and show the path as selectable text when it is missing (labelled degradation) |
| Quant Lab self-grading (TASK-M9-02) | `ui/quant_lab_page.py` beside `_study_chips()` and `_garch_blocks()` | `stat`, `chip`, `qcharts` helpers | new stat strip (Kupiec, Christoffersen CC, ES 97.5% Z2, Basel zone, PIT) |
| macro_daily workflow | `core/skills/workflows/macro_daily.yaml` shown by the existing `ui/workflows_page.py` (decision gates, evidence digest) | whole page | none in `ui/` unless the gate kinds differ from `decision_gate` |

### D.3 Registering a new page (if one is added)

1. `ui/<name>_page.py` with `def build_<name>_page(page: ft.Page, on_open_settings: Optional[Callable] = None) -> ft.Control`.
2. `main.py`: import it; add `("<key>", "<Label>", ft.Icons.<ICON>)` to `NAV`; add `"<key>": build_<name>_page` to the `ficc` dict (125-129) — without this the key falls through to Settings.
3. If the page must reflect state written elsewhere (artifacts from a workflow run), either give it its own Refresh button (the Macro page pattern) or add its key to the rebuild tuple at `main.py:164`. Keep the literal `cache[name] = build(` intact (test_15).
4. The rail does not scroll; a 20th entry worsens the overflow at small heights. Prefer sections inside Macro / Strategy Lab over new nav entries, or add `scroll=ft.ScrollMode.AUTO` to the rail column in the same change.

### D.4 Data contract between core and the new displays

- Follow the page rule stated at `macro_page.py:11-13`: formatting happens in the page; the core hands over decimals / dicts. A renderer that takes plain dicts (the validated artifacts) is testable without Flet event plumbing: build it, walk the control tree (`quant_lab_page.py:349-357`), assert on `ft.Text.value`.
- The UI must not compute exposure. `composed`, `overlay_min`, `vt_weight_next` are read from the artifact; the page may only format them. If an artifact is missing, quarantined or fails schema validation, show `notice(…, "error")` and no numbers (fail closed, no stale value presented as current); if it carries `extras.validation_errors`, show them in a notice (SPEC:3771).
- A FORWARD-SIM value or a refusal-book value is never placed in the same stat strip as the recommended book's numbers.
- No colour-only signalling: every chip carries its word (`components.py:46`).

### D.5 Naming collisions and duplicates to be aware of

- `equity_chart`: `qcharts.equity_chart(bt)` vs `xcharts.equity_chart(dates, equity, bench=None, *, title=, labels=)`. `smile_chart`: `fcharts.smile_chart(strikes, vols, points, forward)` vs `xcharts.smile_chart(points, fit=None, F=0.0, *, title=)`. Always call through the module alias (`qcharts.`, `fcharts.`, `xc.`).
- `_table(columns, rows)` exists three times with slightly different row heights (`fx_page.py:90`, `rates_page.py:76`, `structuring_page.py:119`), plus bespoke tables in `macro_page.py:84` and `strategy_lab_page.py:135`. A v2 table helper should go in `ui/components.py` once (e.g. `data_table(columns, rows, *, numeric_from=None, wide_last=False)`) and be used by the new surfaces; do not add a fourth private copy.
- `narrative(…)` / `payload(…)` / `analyze(…)` are module-level names in `strategy_lab_page`, `etf_page`, `crypto_page`, `derivatives_page` — import the module, not the names.
- "Regime": `core.ficc.macro.Regime` (curve/risk/dollar/inflation/real_rates words), `core.crypto.analytics` regime score zones `RISK_ON / NEUTRAL / RISK_OFF`, and v2's volatility labels `calm / normal / elevated / stressed`. The v2 labels must not be presented as, or mixed with, the first two (SPEC:1126).
- "verdict" vs "decision": existing cards use `decision`; v2 schemas use `verdict`; v2 `owner_decisions[*].decision` is `D1..D6`; `overlay_decision` is an artifact name. Keep the JSON keys verbatim and adapt at the loader.
- `EngineMode` (`core/engine/state.py:32-35`, values `"DISARMED"`, `"ARMED"`, `"HALTED"`) matches the v2 `engine_state` enum strings; `trading_page.MODE_STYLE` is keyed by the enum member, the artifact carries strings → look up with `EngineMode(value)` or key a new map by string.
- Card ids: existing `S_*`, `D_*`, `M_*` (e.g. `S_E1_trend_krx`); v2 `MACRO-R06-KR-ETF`, `MACRO-R03-US-MOM`, `MACRO-R14-MULTI-TREND`, `MACRO-R31-KR-ETF`, `MACRO-R28-US-TREND`, `MACRO-R06-US-FUT` (SPEC:4822-4824); tech-fund ids `SCR-1`, `FS-1`, … No clash, but `crypto_page.py:173` derives a chip label with `k.split('_', 2)[-1]`, which assumes the underscore form.

### D.6 Constraints

Flet 0.85 API guard — exactly what fails `python tests/run_all.py`:
1. Calling `page.<x>(...)` where `<x>` is not a public attribute of `ft.Page`. Known bad: `page.open(…)`, `page.close(…)`. Valid and used: `page.update()`, `page.run_thread(fn)`, `page.show_dialog(control)`, `page.pop_dialog()`; also present in 0.85.2: `page.launch_url(url)`, `page.can_launch_url(url)`, `page.run_task(coro_fn)`, `page.scroll_to(…)`, `page.schedule_update()`. Only the bare receiver name `page` is checked (`self.page.x()` is not).
2. Passing a keyword that is not an `__init__` parameter to any of the 30 `_CHECKED_CONTROLS` when written as `ft.<Name>(...)`. Known bad: `ft.Dropdown(on_change=…)` (it is `on_select`), `ft.Image(src_base64=…)` (use `src="data:image/png;base64,…"`), `ft.Dropdown(helper=…)` (it is `helper_text`), `ft.TextField(helper_text=…)` (it is `helper`).
3. Assigning `name.attr = …` when `name` is assigned in that file only from one `ft.<Control>` type and the class has no such field/property (e.g. `field.helper_text = "…"` on a TextField). The name → type map is per file, not per scope: reusing one variable name for two control types anywhere in the file silently disables the check for that name.
4. Reading `pal.<token>` where `<token>` is not one of `bg, surface, surface_2, border, text, muted, accent, accent_soft, success, error, on_accent`. A new token must be added to `Palette` **and** to both `DARK` and `LIGHT` positional constructors (the dataclass is frozen and positional).
Not checked by the guard (so verify by hand against Flet 0.85.2): `ft.DataTable / DataColumn / DataRow / DataCell`, `ft.ButtonStyle`, `ft.Padding`, `ft.Border`, `ft.BorderSide`, `ft.Markdown`, `ft.TabBar / TabBarView`, `ft.SegmentedButton`, `ft.ListView`, `ft.dropdown.Option`, anything imported by name instead of `ft.<Name>`, dynamic `getattr(pal, token)` / `colour_for(token)` with a bad token string (fails at first paint), and any file in a sub-directory of `ui/` (the glob is `ui/*.py`). Keep new UI modules flat in `ui/`.

Flet 0.85.2 facts (probed on this machine):
- Absent: `ft.LineChart`, `ft.BarChart`, `ft.WebView` (no in-app HTML: the offline pages can only be opened externally). Present and usable: `ft.DataTable`, `ft.ExpansionTile(title=, controls=, expanded=)`, `ft.Tabs(content=, length=, selected_index=, on_change=)` + `ft.TabBar(tabs=[ft.Tab(label=)])` + `ft.TabBarView(controls=)`, `ft.Markdown(value=, selectable=)`, `ft.Banner`, `ft.SegmentedButton`, `ft.Button(url=)`, `ft.Container(url=)`. None of Tabs / Markdown / Banner / SegmentedButton is used anywhere in the app today; sub-views are switched with a "Tool" `ft.Dropdown` (`rates_page`, `fx_page`, `bonds_page`, `structuring_page`). Reusing the Dropdown + host pattern for the market selector avoids an untested control.
- Spelling in use: `ft.Button` (not ElevatedButton), `ft.Border.all(1, colour)`, `ft.Padding(l, t, r, b)`, `ft.Alignment.CENTER`, `ft.Icons.<NAME>`, `ft.FontWeight.W_600`, `ft.ScrollMode.AUTO`, `ft.BoxFit.CONTAIN`, `ft.ThemeMode.DARK`, `ft.run(main, …)`.
- Dialogs and toasts: `page.show_dialog(ft.AlertDialog(...))`, `page.pop_dialog()`, `page.show_dialog(ft.SnackBar(ft.Text(msg, color=pal.text), bgcolor=pal.surface_2))` (`rules_page.py:108-161`, `trading_page.py:75`).
- Services: `page.services.append(ft.FilePicker())`.

Other constraints:
- Read-only: no order path may appear in `ui/` (test_08/test_09 word lists in C; SPEC:305, T-RO-01). Avoid the raw substrings `CANO`, `KIS_ACCOUNT`, `ACNT_PRDT_CD`, `place_order`, `submit_order`, `order_cash` in any UI source text, including comments and labels.
- P19 (SPEC:653-656): no regime-model state on any page; T-DNB-01 refuses a displayed field whose source is a regime model.
- `Palette` is frozen; `MacroRow`, `MacroSheet`, `Regime`, `Indicator` are frozen dataclasses — renderers must not mutate inputs.
- Secrets: Settings shows presence only; no widget may hold a key value (test_13).
- All new source files UTF-8; any file read in tests with explicit `encoding="utf-8"`.

---

## E. Gotchas

1. **A v2 card JSON in `docs/asset_expansion/cards/` crashes Strategy Lab at build time.** `build_strategy_lab_page` indexes `c["decision"]`, `c["kind"]`, `c["hypothesis"]`, `c["decision_reason"]` (lines 101, 109-112, 121, 129-132) synchronously, outside any worker; `load_cards` sort uses `c["card_id"]`. A `model_card.macro` file (keys `verdict`, `class`, `claim`) or a header-only file dropped in that directory raises `KeyError` inside `navigate`. ETF, Crypto and Quant Lab read the same directory with `.get`, so they survive. Keep macro cards in their own directory or adapt them in the loader before the page sees them. (`cards/verdicts.jsonl` is not matched by the `*.json` glob.)
2. **`FilePicker` is async in Flet 0.85.2 but called synchronously.** `inspect.iscoroutinefunction(ft.FilePicker.pick_files)` and `…get_directory_path` are both True; `param_form._browse` (165-185) calls them without awaiting, so `files[0]` raises `TypeError` (caught → helper text `picker failed: TypeError`) and the directory branch assigns a coroutine object to `field.value`. The guard cannot see this (it checks names, not awaitability). Do not copy this pattern; a v2 "open file" needs no picker.
3. **`run_family` mutates the shared gate config from a worker thread**: `V.GATE["bootstrap_B"] = bootstrap_B` (`strategy_lab_page.py:70`), also done in tests (`expansion_acceptance.py:273`). The v2 gate package is frozen by md5 (SPEC:4820); a UI path that writes into `GATE` conflicts with that and must not be reused for formal card runs.
4. **Pages are cached forever.** Strategy Lab reads the cards once at first build; new cards or artifacts written while the app is open are not shown until restart, `reload_catalogue`, or a rebuild rule. A Macro state panel must re-read on Refresh.
5. **Unknown NAV key → Settings page**, silently (`main.py:159`).
6. **Rail does not scroll** and already exceeds the 620 px minimum window height with 19 items.
7. **Windows / cp949**: default stdout encoding on this machine is cp949; `tests/run_all.py` reconfigures to UTF-8, but a module run directly (`python ui/etf_page.py`) that prints Hangul (`KODEX 레버리지`, `수정주가`, `억`, `₩`) or `→`, `×`, `ν`, `—` can raise `UnicodeEncodeError` unless `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` is set. UI strings already contain Hangul and symbols; fonts render them in Flet, but `font_family="Consolas, monospace"` has no Hangul glyphs (falls back).
8. **Dark only in practice.** `main.py` forces dark; LIGHT is untested in the running app. `corr_heatmap` hard-codes `#111111` cell text; `frontier_chart` and `corr_heatmap` use matplotlib colormaps outside the palette. Charts are baked PNGs in the palette active when they were drawn.
9. **The regime read is displayed as chips** (`curve:`, `risk: risk-on/risk-off`, `dollar:`, `breakevens:`, `real yields:`), in `rg.summary`, and in the `macro_z_chart` title; the docstring calls them "regime chips". The method (`core/ficc/macro.py:161-186`) is threshold rules on z-scores and 20-session changes, not a Markov/HMM/jump/mixture/change-point model, so SPEC:1125 does not force removal, but SPEC:1126 says it is "never presented as a regime state". See Ambiguities 2.
10. **z-scores are thresholded for colour** (`abs(z_1y) >= 2` → error tone in the table and tiles). This is display only; SPEC:1123 forbids thresholding for exposure, not for colour. Do not wire these into any multiplier.
11. **Verdict colouring is inconsistent across pages**: Strategy Lab maps PASS → success, REVISE → accent, REJECT → error, INSUFFICIENT_DATA → muted; ETF maps everything that is not PASS (including `"not run"`) → error; Crypto maps PASS → success, everything else → muted; Quant Lab's VaR-study chip maps PASS → muted and non-PASS → error (`quant_lab_page.py:167`) while its skew-t chip maps PASS → success, else muted (172). A shared `verdict_chip` fixes this for new surfaces.
12. **Hard-coded conventions inside page modules**: `rf = 0.03 / 252` (`etf_page.py:81`, `strategy_lab_page.py:61`), `_RF_ASSUMED = 0.03` (`quant_lab_page.py:42`), ETF sleeve costs 3 bp / 50 bp per side, default strategy cost 10 bp. v2 pre-registered costs (P10) and cash conventions (R-22) live in the rules store; the pages' descriptive numbers must stay labelled as in-sample descriptive (as `etf_page.narrative` already says) and must not be read as card results.
13. **`analyze()` functions live in page modules** (`etf_page.analyze`, `crypto_page.analyze`, `strategy_lab_page.run_family`, `derivatives_page.snapshot`): business logic inside `ui/`, imported by tests (`expansion_acceptance.py:206`). New v2 logic belongs in `core/`; only the dict → controls rendering belongs in `ui/`.
14. **README drift**: README says "229 checks" (line 347) and "245 checks" (line 379); the runner collects 266. README "Charts" says "the equity six and the FICC sixteen"; `qcharts` has 7 chart functions and `fcharts` 15 (16 images in its self-check). The Settings env template still says "NEXTGEN reads these" and omits nothing v2 needs yet. Module docstrings (`components.py`, `settings_page.py`, `config.py`) still say NEXTGEN; `pyproject.toml` already declares `version = "2.0.0"`.
15. **`BREAKPOINTS["medium"]`, `Palette.accent_soft`, `MODES`/"system"/"light"** are defined but unused.
16. **`analysis_panel` default `deep_fn` is the equity engine**; `quant_lab_page` and `signals_page` rely on the default, FICC/v3 pages pass one explicitly. Any v2 panel that sends artifacts to the Claude API must send computed numbers only ("receives the computed numbers only and never decides", SPEC:1253).
17. **`stat(token=…)` falls back to `pal.text` on a bad token** (`getattr(pal, token, pal.text)`), while `chip`/`notice`/`colour_for` raise `AttributeError` at paint time on a bad token string — neither is caught by the guard.
18. **`ft.DataColumn(numeric=…)`** right-aligns; the Macro table sets `numeric=i >= 2 and c != "Source"`. DataTable controls are not guard-checked, so a wrong keyword there fails only when the table is first painted (inside a worker → the two-tier `except` turns it into an error notice; in a synchronous build path it takes the page down).

---

## Ambiguities (conservative reading: no exposure change, specification book only, fail closed)

1. **Owner decisions D1–D5 vs D1–D6.** SPEC:762 (UI box) and SPEC:6465 say D1–D5; the schema enum (SPEC:3607) and TASK-M6-06 list D1–D6. Reading: list all six; an absent key is shown as `status: default` with the council default value, never hidden.
2. **Existing regime chips under P19.** The spec leaves the classification to BL-G06 / TASK-M6-01 ("If the regime read comes from a regime model … schedule its removal from every page. Otherwise keep it only as a causal descriptive text in the brief"). The code is rule-based. Reading: keep the text, relabel the chip row and chart title as a descriptive read (not "regime"), never reuse `calm / normal / elevated / stressed`, and keep it visually separate from the v2 volatility labels; it feeds nothing.
3. **`UNVERIFIED` and `FORWARD-SIM` and `BUILD-AS-INSURANCE` as "verdict chips".** None is in a verdict enum. `UNVERIFIED` is a label on claims and priors (SPEC:482, 697, 1727), `FORWARD-SIM` and `BUILD-AS-INSURANCE` are build statuses / dispositions (SPEC:4785-4789). Reading: render them as separate status/disposition chips next to the verdict chip, in neutral tone (`muted`, or `accent` for insurance), never `success`; the verdict chip itself shows only the five schema values.
4. **`INSUFFICIENT DATA` vs `INSUFFICIENT_DATA`.** Prose uses a space, JSON and `validate.DECISIONS` use an underscore. Reading: store and compare the underscore form; display with a space.
5. **Where macro cards are stored.** SPEC:3911 says map onto the app's card format and "do not run a parallel registry"; SPEC:3487 names `cards/verdicts.jsonl`. The directory is not stated (the existing one is `docs/asset_expansion/cards/`). Reading: same registry, separate sub-directory or filename prefix, loaded through one function that returns the existing dict shape; until a card has an authenticated formal result its chip is `NOT RUN` and it appears only in the specification / descriptive listing.
6. **Alert acknowledgement.** SPEC:1248 and T-OBS-03 require page alerts to persist until acknowledged, and the schema has `ack_utc` / `ack_by`, but no function or file for writing the acknowledgement is named in the ranges read. Reading: the UI calls a core function that appends a governance event and sets `ack_utc`; with no such function available the banner stays visible (never auto-dismiss).
7. **HALT re-arm from the UI.** Existing banner text says "This program never re-arms itself"; v2 RISK halts re-arm automatically after 10 sessions (`rearm_mode: auto`), OPS halts clear with their cause (SPEC:837-840). Reading: the Macro banner shows `rearm_mode` and `rearm_not_before` and offers acknowledgement only; no "Arm" button on the Macro page.
8. **"Event calendar" display.** Required by SPEC:762 and SPEC:1133; its artifact schema was outside the ranges read here. Reading: render it as a plain dated table from the validated artifact; if absent, an `empty_state`, not synthetic rows.
9. **Opening local HTML.** `os.startfile` is the only proven path in this codebase (Windows); `ft.Button(url="file:///…")` / `page.launch_url` behaviour for `file://` on the desktop client is untested here. Reading: use the `os.startfile` pattern and show the file path as selectable text beside the button.
10. **Weight table "Final" column vs displayed book.** R3:703 states weights are design priors and "any weight of 2 or more still needs a PASS card before it can feed the displayed book". Reading: the table is labelled "design priors, not gate results" and is shown outside any recommended-book panel.
