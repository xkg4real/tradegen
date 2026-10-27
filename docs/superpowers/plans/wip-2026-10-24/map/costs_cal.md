# Repo map: costs and calendars (area key `costs_cal`)

Repo: C:/Users/whydi/OneDrive/Desktop/TRADEGEN, git main at 995534b, `git status` clean before and after every probe.
Probes ran with `.venv/Scripts/python.exe -I` from the repo cwd. The scripts are in the scratchpad (`odds_plan/cps_probe.py`,
`krx_count.py`, `cal_probe.py`, `nyse_count.py`, `ast_probe.py`, `calsha.py`, `closure_costs_cal.py`). There were no
network calls. The fixture calendar was written into a scratchpad temp dir. Side effect: the first runs had no `-B`, so
Python refreshed gitignored `__pycache__/*.pyc` files under the repo (`.gitignore:3 __pycache__/`). Later runs used `-B`.

## A. cost_per_side: signature, rule, books

* [signature] The real signature is `cost_per_side(instrument_book, price=None, nav_fx=None, *, on=None, side="buy") -> CostQuote`. `nav_fx` is the third POSITIONAL parameter, not keyword-only. `on` and `side` are keyword-only.
   EVIDENCE: core/quant/instruments.py:168-169 `def cost_per_side(instrument_book: Any, price: Optional[float] = None, nav_fx: Any = None, *,` / `on: Optional[date] = None, side: str = "buy") -> CostQuote:`; inspect.signature printed `(instrument_book: 'Any', price: 'Optional[float]' = None, nav_fx: 'Any' = None, *, on: 'Optional[date]' = None, side: 'str' = 'buy') -> 'CostQuote'`
   IMPACT: The spec's form `cost_per_side(book, price=fill_price, on=fill_date, side=side)` (spec:176) is valid Python but passes no nav_fx. Pass it by keyword (`nav_fx=`) so a positional slip cannot shift it.
* [return type] CostQuote is a frozen dataclass `(bp, floor_bp, source, table_bp, stress_bp)`. `bp` is in basis points. `source` is "table" or "tick_floor". `stress_bp` = 2 × bp.
   EVIDENCE: core/quant/instruments.py:139-145 `class CostQuote:` / `bp: float` / `floor_bp: Optional[float]     # None for a class-only quote` / `source: str                   # "table" | "tick_floor"` / `table_bp: float` / `stress_bp: float              # the 2× line`
   IMPACT: κ = quote.bp × 1e-4 (spec:660). The stress column can use `quote.stress_bp` or `instruments.stress(bp)`. Never multiply by 2 by hand: use GATE["cost_stress"].
* [R-26 rule] The applied rate is max(table rate, floor). The floor is commission 1.4 bp + ½·tick/price·1e4 + sell tax (stock sells only). It can only raise a cost.
   EVIDENCE: core/quant/instruments.py:179-182 `tax_bp = _sell_tax_bp(on) if (side == "sell" and book.tax_side == "sell") else 0.0` / `floor_bp = tick_floor_bp(price, tick_size(book.tick_table, price, on), tax_bp=tax_bp)` / `bp = max(table_bp, floor_bp)`; :118-122 `def tick_floor_bp(price: float, tick: float, *, commission_bp: float = COMMISSION_BP, tax_bp: float = 0.0) -> float:` ... `return commission_bp + 0.5 * tick / price * 1e4 + tax_bp`; :19 `COMMISSION_BP = 1.4                # EX2 desk quote; owner confirms against the broker schedule (L2797)`
   IMPACT: `tick_floor_bp` is public and pure, so odds can reuse the exact repo formula with its own tick (venues.yaml) instead of re-deriving it.
* [table rates] COST_BP_PER_SIDE = krx_etf 3, krx_stock 35, us 50, crypto 10, futures 5, fx 10 bp. `cost_bp("KRX_LI_ETF")` falls back to 3 bp.
   EVIDENCE: core/quant/validate.py:78 `COST_BP_PER_SIDE = {"krx_etf": 3.0, "krx_stock": 35.0, "us": 50.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}`; :127-128 `if venue == "KRX_LI_ETF" and venue not in COST_BP_PER_SIDE:` / `return COST_BP_PER_SIDE["krx_etf"]`; :57 `"haircut": 0.6, "cost_stress": 2.0,`
   IMPACT: Read the rates through `cost_per_side(book)` or `validate.cost_bp`. Never copy the numbers into core/odds. tests/macro_m0_instruments.py:78 pins `assert V.COST_BP_PER_SIDE == TABLE`.
* [35 bp includes tax] The study runner's docstring records that the KRX stock 35 bp rate includes the sell tax.
   EVIDENCE: docs/asset_expansion_study.py:19 `(KRX ETF 3 bp, US via KIS 50 bp, KRX stock 35 bp incl. tax, crypto 10 bp,`
   IMPACT: This matches spec:179-181 ("charges that rate on both sides ... adds no separate tax").
* [books: the four the spec names] INSTRUMENT_BOOKS rows (book_id, market, venue, currency, cost_class, kind, tick_table, tax_side, lot_size, ...):
  - KRX_ETF_line: KRW, krx_etf, tick table "KRX_ETF".
  - KRX_stock_book: KRW, krx_stock, tick_table OWNER_INPUT, tax_side "sell".
  - US_shares_KIS: USD, us, tick_table OWNER_INPUT.
  - crypto_venue: venue and currency OWNER_INPUT, crypto, tick_table OWNER_INPUT.

  Every lot_size is OWNER_INPUT.
   EVIDENCE: core/quant/instruments.py:67 `_B("KRX_ETF_line", "KR", "KRX", "KRW", "krx_etf", "etf", "KRX_ETF", None, OWNER_INPUT, None, None),`; :68 `_B("KRX_stock_book", "KR", "KRX", "KRW", "krx_stock", "stock", OWNER_INPUT, "sell", OWNER_INPUT, None, None, True),`; :72 `_B("US_shares_KIS", "US", "US", "USD", "us", "stock", OWNER_INPUT, None, OWNER_INPUT, None, None, True),`; :74 `_B("crypto_venue", "CRYPTO", OWNER_INPUT, OWNER_INPUT, "crypto", "spot", OWNER_INPUT, None, OWNER_INPUT, None, None),`; :18 `OWNER_INPUT = None`
   IMPACT: Lots and minimums cannot come from instruments.py, so they come from venues.yaml (spec:137, 788). A missing entry gives NOT_TRADABLE.
* [book set pinned; KRX stock refusal pinned] A test pins the exact set of books. It also requires `cost_per_side("KRX_stock_book", 70000.0)` to raise NotTradable, along with a non-KRW book without nav_fx and a 2025 stock sell.
   EVIDENCE: tests/macro_m0_instruments.py:92 `(("KRX_stock_book", 70000.0), {}),`; :93 `(("CME_micro_ES", 5000.0), {}),`; :94 `(("KRX_stock_book", 70000.0), {"on": date(2025, 1, 2), "side": "sell"}),`; :103 `assert set(INSTRUMENT_BOOKS) == {"KRX_ETF_line", "KRX_stock_book", ...`
   IMPACT: The odds plan must NOT add a KRX stock row to `instruments.TICK_TABLES` or set `KRX_stock_book.tick_table`, because T-COST-02 would fail. Keep the stock ladder in venues.yaml and compute the floor in core/odds.
* [reproduced: what raises] Read-only probe of each book at 2,005 KRW on 2026-11-02 (and other cases). The output was:
  - KRX_stock_book: `NotTradable: tick table None is an owner input` (buy or sell). A 2027 sell gives `NotTradable: stock sell tax for 2027 is an owner input (R-20 sell_tax_pct)` first.
  - KRX_ETF_line, KRX_listed_SP500_ETF, 252670, 069500: `OK bp=13.868827930174565 floor=13.868827930174565 src=tick_floor table=3.0 stress=27.73765586034913`.
  - US_shares_KIS, crypto_venue with nav_fx None: `NotTradable: ... a non-KRW book is valued through nav_fx (L2812); none given`. With nav_fx=1400.0: `NotTradable: tick table None is an owner input`.
  - Every book with price=None: OK at the table rate (35, 3, 50, 10).
  - KRX ETF on 2023-01-02: `NotTradable: KRX_ETF: no tick row effective on 2023-01-02`.
  - multi_line: `NotTradable: multi_line: no cost class of its own`.
   EVIDENCE: scratchpad odds_plan/cps_probe.py output (verbatim above); code: core/quant/instruments.py:107-108 `if table is None or table not in TICK_TABLES:` / `raise NotTradable(f"tick table {table!r} is an owner input; not tradable in the simulated book")`; :177-178 `if book.currency != "KRW" and nav_fx is None:` / `raise NotTradable(f"{label}: a non-KRW book is valued through nav_fx (L2812); none given")`; :150-151 `if year not in SELL_TAX_BP:` / `raise NotTradable(f"stock sell tax for {year} is an owner input (R-20 sell_tax_pct)")`
   IMPACT: Only the KRX ETF books can take the spec's literal per-fill call. KRX_stock_book, US_shares_KIS and crypto_venue raise however nav_fx is passed. The plan must say for each book how κ is computed:
  - ETF: `cost_per_side(book, price, on=, side=)`.
  - Others: `max(cost_per_side(book).bp, tick_floor_bp(price, venues_tick(price)))`, or the table rate alone where venues.yaml has no ladder.

  It must also map NotTradable to NOT_TRADABLE.
* [order of checks] The order is: resolve → no cost class → price None returns the table rate → the non-KRW nav_fx check → the sell tax (stock sells) → the tick lookup. So a KRX stock sell in 2027 fails on the TAX before the tick.
   EVIDENCE: core/quant/instruments.py:171-180 (body quoted above)
   IMPACT: A floor built in odds that reuses `_sell_tax_bp` (private) inherits the 2027 refusal. Choose the tax source deliberately (see open questions).
* [nav_fx meaning] nav_fx is only checked against None. Its value is never used in the arithmetic, because tick/price is currency-invariant. crypto_venue needs it too, because its currency is OWNER_INPUT (None ≠ "KRW"), even for KRW-quoted Upbit coins. Callers in the repo pass it through unchanged (card_lines). Card headers describe it as `{series, history, conversion_instant, role}`.
   EVIDENCE: core/quant/instruments.py:177 `if book.currency != "KRW" and nav_fx is None:`; :45 `currency: Optional[str]                 # "KRW" or not; a non-KRW book needs nav_fx (L2812)`; core/quant/card_lines.py:195 `q = cost_per_side(instrument_book, price, nav_fx, on=on)`; core/quant/instruments.py:337 `out.append(f"9 nav_fx: non-KRW book {non_krw} needs nav_fx {{series, history, conversion_instant, role}}")`
   IMPACT: The odds caller passes `nav_fx=plan.fx_krw_per_usd` (spec Plan field, spec:652) for US legs. It is a non-None marker that changes nothing numerically. It does not unblock US or crypto, because their tick table is still None.
* [price validation] With a price, `price <= 0` raises a plain ValueError (not NotTradable). NaN raises `NotTradable: KRX_ETF: no tick for price nan`.
   EVIDENCE: core/quant/instruments.py:120-121 `if not (math.isfinite(price) and price > 0) or not (math.isfinite(tick) and tick >= 0):` / `raise ValueError(...)`; probe output `price0 ValueError price 0.0 and tick 1.0 must be finite and positive`, `pricenan NotTradable KRX_ETF: no tick for price nan`
   IMPACT: odds validates fill prices (finite, > 0) before quoting. A ValueError must not be mislabelled as NOT_TRADABLE or crash a chunk.
* [side semantics] Only the exact string "sell" triggers the tax. Any other string, "SELL" included, is treated as a buy, without validation.
   EVIDENCE: core/quant/instruments.py:179 `if (side == "sell" and book.tax_side == "sell")`
   IMPACT: odds passes lowercase "buy" or "sell" from a fixed enum.
* [resolve inputs] `_resolve` accepts an InstrumentBook, an Instrument, a book-id string or a registry code ("252670", "069500"). Anything else raises NotTradable("unknown instrument or book"). The instrument map's `cost_book` is a book-id string from COST_BOOKS.
   EVIDENCE: core/quant/instruments.py:155-165 `def _resolve(x: Any) -> tuple[str, InstrumentBook, str]:` ... `raise NotTradable(f"unknown instrument or book {x!r}")`; core/compliance/rules.py:72 `COST_BOOKS = frozenset({"KRX_stock_book", "KRX_ETF_line", "US_shares_KIS", "crypto_venue"})`; :573-574 `_COST_BOOK = {"krx_share": "KRX_stock_book", "krx_etp": "KRX_ETF_line", "us_share": "US_shares_KIS",` / `"us_etp": "US_shares_KIS", "crypto_coin": "crypto_venue"}`
   IMPACT: odds passes `instrument.cost_book` (from the approved instrument map) as the first argument. It never uses `validate.cost_class` symbol inference (spec:182).
* [shipped instrument map books] core/compliance/instruments.yaml names KRX_stock_book ×1 (005930), KRX_ETF_line ×3 (069500, 252670, 114800), US_shares_KIS ×10 and crypto_venue ×3 (BTC, USDT, USDC; currency KRW).
   EVIDENCE: core/compliance/instruments.yaml:15 `cost_book: KRX_stock_book`; :24 `cost_book: KRX_ETF_line`; grep count `3 KRX_ETF_line / 1 KRX_stock_book / 10 US_shares_KIS / 3 crypto_venue`; :144 `currency: KRW` (BTC)
   IMPACT: The only whitelisted 1x KRX ETF in the map is 069500 (252670 is etp_leveraged and 114800 is etp_index_inverse, both outside the odds whitelist). The fixtures should use 069500 and 005930.

## B. 2,005-KRW ETF claim

* [computed] tick_size("KRX_ETF", 2005) = 5 (prices strictly below 2,000 use 1). floor = 1.4 + 0.5·5/2005·1e4 = 13.8688 bp > 3 bp table, source "tick_floor". The spec claim "at least 13.8 bp per side" holds on buy and sell (ETF tax_side None). At exactly 2,000 the floor is 13.9 bp. At 1,999 it is 3.901 bp.
   EVIDENCE: core/quant/instruments.py:26-28 `TICK_TABLES ... = {` / `"KRX_ETF": ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),),`; probe `floor 2005: 13.868827930174565 floor 1999: 3.901250625312656 floor 2000: 13.9`; spec:1043 `the per-fill tick floor raises cost: a 2,005-KRW ETF fill costs at least 13.8 bp per side;`
   IMPACT: The ledger test can assert `cost_per_side("KRX_ETF_line", 2005.0, on=<2026 date>, side=s).bp >= 13.8` for both sides, and equality with buy (no tax added). A test date before 2023-12-11 raises NotTradable.
* [where the ETF floor binds] With tick 1, the ETF floor exceeds 3 bp for every price below 2,000. With tick 5, it binds below 15,625 KRW. KRX stock (35 bp, if odds uses the same formula): a buy floor binds only below 148.8 KRW (tick 1). A sell floor including the 20 bp tax binds below 367.6 KRW. US at a $0.01 tick binds only below about $1.03.
   EVIDENCE: scratchpad nyse_count.py output `KRX stock sell floor binds below 367.6470588235294 buy below 148.8095238095238 ETF tick1 binds below 3125.0 ETF tick5 binds below 15625.0` / `US tick 0.01 binds below USD 1.02880658436214`
   IMPACT: For KRX stocks and US shares the floor rarely binds, but the floor code path must still exist and be tested (spec section 8, ledger). For low-priced KRX ETFs it binds often.

## C. check_extras, fixed charges, venues.yaml

* [check_extras does not exist] There is no `check_extras` anywhere in the repo. The spec names it without a module. Round-1 review F2 proposed `odds.models.check_extras`: every extra ≥ 0, and a venue fee row applies as max(table_bp, fee_bp).
   EVIDENCE: grep for `check_extras` hits only docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:183 `Extras in venues.yaml may only raise costs (check_extras). Fixed charges φ_b and φ_s are taken from there.` and docs/superpowers/specs/2026-10-23-review-gate-odds/round1_claude_workflow.md:155 `venues.yaml extras are additive and checked by their own rule (odds.models.check_extras): every extra is ≥ 0.`
   IMPACT: The plan creates it, with a defined module and signature. Do NOT reuse `instruments.check_cost_policy`: it validates card headers (`{per_side: read_from_gate, floor: tick_floor}`, core/quant/instruments.py:192-197) and would call legitimate extras "lowered".
* [no fixed-charge data] No φ_b or φ_s (fixed per-order charges) exist in the repo outside the spec.
   EVIDENCE: grep for `fee_bp|phi_b|φ_b|fixed_charge|fixed charge` hits only spec:183, :662, :668-672, :685
   IMPACT: φ values are new venues.yaml data the owner signs. Default absent means 0 or NOT_TRADABLE: decide which and test it. R_exit = 4·φ_s (spec:664).
* [venues.yaml today] Only `schema`, `venues.<id>.{sections, settlement, quote_by_currency|markets, default_quote, deposits, source}` exist. The header says the odds plan adds lots, minimums and ticks.
   EVIDENCE: core/odds/venues.yaml:2-3 `# ... The compliance plan writes markets, settlement and deposits only; the` / `# odds plan adds lots, minimums and ticks later, which changes this file's sha256 and needs a new approval.`; :5 `schema: tradegen.venues/1`
   IMPACT: Any addition changes the venues sha256, so the owner re-approves `approved {kind: venues}`.
* [BLOCKER: compliance parser is strict] `parse_venues` allows only top-level {schema, venues} and venue keys {sections, settlement, source, markets, quote_by_currency, default_quote, deposits}. Unknown keys raise Invalid. A shipped test asserts that an Upbit `minimum_krw` key is refused.
   EVIDENCE: core/compliance/rules.py:636-637 `_VENUE_REQUIRED = frozenset({"sections", "settlement", "source"})` / `_VENUE_OPTIONAL = frozenset({"markets", "quote_by_currency", "default_quote", "deposits"})`; :642 `_keys(entry, where, _VENUE_REQUIRED, _VENUE_OPTIONAL)`; :701 `_keys(doc, "venues", frozenset({"schema", "venues"}))`; :340-342 `unknown = sorted(...)` / `raise Invalid(f"{where}: unknown key(s) {unknown}")`; tests/compliance_tables.py:633 `bad(lambda d: d[v]["upbit"].update(minimum_krw=5000), "venues: upbit: unknown key(s) ['minimum_krw']")`; :615 `bad(lambda d: d.update(extra=1), "venues: unknown key(s) ['extra']")`
   IMPACT: Adding lots, minimums, extras or the tick ladder to venues.yaml REQUIRES a core/compliance/rules.py change (new optional keys, or a `tradegen.venues/2` schema) and an edit of tests/compliance_tables.py:633. That changes the D14 code hash (owner re-signs code_approved) as well as the venues sha256. Otherwise `approved_state` would refuse the new file and block everything. The odds plan or the compliance follow-up must own this change explicitly.

## D. LIMIT_DOWN_CARRY_COST_MULTIPLIER and the band helpers

* [value] `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0` is a module-level literal assignment. ast.literal_eval reads `[(275, 2.0)]`.
   EVIDENCE: core/engine/orders.py:275 `LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0        # INV-2: "an assumption, not measured" (R3:802)`; scratchpad ast_probe.py output `[(275, 2.0)]`
   IMPACT: core/odds declares its own constant (spec:160). The test can assert equality without importing the engine: `ast.parse(Path("core/engine/orders.py").read_text("utf-8"))`, find the module-level `Assign` with target Name `LIMIT_DOWN_CARRY_COST_MULTIPLIER`, then `ast.literal_eval(node.value) == odds_constant`.
* [tests may import orders] T-RO-01 scans only runtime files (core, data, ui, main.py, config.py) and docs/*.py, not tests. The compliance guards scope core/compliance and core/odds. A test file already imports orders.
   EVIDENCE: tests/macro_m0_harness.py:58 `ORDERS_IMPORTERS_ALLOWED = ("core/engine/", "core/skills/macro_daily.py", "core/skills/pipeline.py")`; :64 `files = runtime_py() + sorted(p for p in (ROOT / "docs").glob("*.py"))`; tests/acceptance.py:50 `for base in (ROOT / "core", ROOT / "data", ROOT / "ui"):`; tests/macro_m5_fills_events.py:21 `from core.engine import orders as O`
   IMPACT: tests/odds_acceptance.py may `from core.engine import orders` to compare the values. But that runs core/engine/__init__.py, which imports evaluator, orders and state (core/engine/__init__.py:2-5). The AST read is lighter and avoids engine import side effects, so prefer it.
* [odds may not import orders, in any form] tests/compliance_guards.py bans `core.engine.orders` (every import form), `core.quant.forward_sim`, `core.quant.refusal`, `core.ficc.context_log`, `core.ficc.macro`, `core.ficc.flows_log` and `core.skills.macro_daily` in core/compliance AND core/odds. It also bans star and dynamic imports (importlib.util, runpy, pkgutil, timeit, pydoc, code, cProfile, exec, eval) there.
   EVIDENCE: tests/compliance_guards.py:22 `COMPLIANCE, ODDS = CORE / "compliance", CORE / "odds"`; :43-44 `FORBIDDEN_MODULES = ("core.engine.orders", "core.quant.forward_sim", "core.quant.refusal", "core.ficc.context_log",` / `"core.ficc.macro", "core.ficc.flows_log", "core.skills.macro_daily")`; :300-301 `hits = [h for rel, src in _scope(COMPLIANCE, ODDS).items()` / `for h in _forbidden_hits(rel, src) + _dynamic_hits(rel, src)]`
   IMPACT: limit_prices, limit_lock and _round_toward must be reimplemented in core/odds (or moved to a pure module, which would touch orders.py, kept add-only by test_s4). The spec chose the local declaration.
* [band helper semantics to mirror] orders rounds the limit toward prev_close (floor above, ceil below) with ONE tick and an epsilon of 1e-9. It requires 0 < price_limit < 1 and tick > 0. A lock means the close EQUALS the tick-rounded limit (tolerance tick·1e-6), never a |r| ≥ limit test. The carry multiplier applies to a carried limit-down SELL.
   EVIDENCE: core/engine/orders.py:407-411 `def _round_toward(x: float, tick: float, prev_close: float) -> float:` / `if x >= prev_close:` / `return math.floor(x / tick + _EPS) * tick` / `return math.ceil(x / tick - _EPS) * tick`; :414-419 `def limit_prices(prev_close: float, price_limit: float, tick: float) -> tuple[float, float]:` ... `if not (prev_close > 0 and 0 < price_limit < 1 and tick > 0):`; :422-432 `def limit_lock(...)` ... `tol = tick * 1e-6`; :504-506 `if carried.reason == "limit_down_locked" and side == "SELL":` / `mult, reason = LIMIT_DOWN_CARRY_COST_MULTIPLIER, "carried_limit_down_exit_2x"`
   IMPACT: The spec's bands ("rounded to the tick ladder, D up and U down, then clamped so that D ≤ reference ≤ U", spec:727-729) match `_round_toward`. orders uses a single tick for both edges. With a price-dependent ladder the two edges can need different ticks. Example: ETF reference 2,005 gives a lower edge of 1,403.5, which rounds to 1,405 with tick 5 but 1,404 with the ladder's tick 1 (scratchpad probe). The plan must pick one rule and test it.

## E. Calendars: store API, signatures, refusal

* [load API] There is no `load()` function. The API is `CalendarSet(data_dir=None, *, config=None, buffer_s=None)`. Its members are: `.file(file_id)` (cached; raises CalendarUnsigned), `.refusal(file_id)` (never raises; returns str or None), `.holiday_set(set_id)`, `.require_covered(file_id, d)`, `.version`, `.manifest`, `.file_ids()`, `.market_config(market)`. Module functions: `default()`, `reload()`, `describe()`, `status()`, `check_coverage()`, `arm_precondition()`.
   EVIDENCE: core/calendars/store.py:214 `class CalendarSet:`; :221-222 `def __init__(self, data_dir: Path | None = None, *, config: dict | None = None,` / `buffer_s: int | None = None) -> None:`; :276 `def file(self, file_id: str) -> CalendarFile:`; :294-295 `def refusal(self, file_id: str) -> Optional[str]:` / `"""The refusal reason, or None when the file loads (never raises)."""`; :334 `def default() -> CalendarSet:`; :342 `def reload() -> None:`
   IMPACT: `simulate(..., cal: CalendarSet)` takes an injected set. Tests pass `fixture_set()`. Production builds `CalendarSet(<approved dir>)` (see the store layout below). Never call `default()` inside core/odds, so the set is always explicit.
* [config dependency] `CalendarSet.config` lazily imports `core.rules.macro_rules.load_store()` (shipped data/macro/rules_v2.0.0.json) when no config is injected. KR `is_session` needs it on Saturdays (`saturday_sessions_before`).
   EVIDENCE: core/calendars/store.py:233-237 `if self._config is None:` / `from core.rules.macro_rules import load_store      # the shipped store is read-only (T-HERM-02)` / `self._config = load_store().get("calendars")`; core/calendars/clocks.py:202-204 `if market == "KR" and d.weekday() == 5:` / `before = date.fromisoformat(cal.market_config("KR")["saturday_sessions_before"])`; data/macro/rules_v2.0.0.json:228 `"saturday_sessions_before": "1998-12-12",`
   IMPACT: Even with fixture_set, KR session counting reads the shipped macro rules store (read-only). The plan can inject `config=` in tests for hermeticity, or accept the read.
* [MANIFEST] MANIFEST.yaml version is 0.1.0-draft, `signed_off_by: null`, with 16 rows. Every row has `md5: null` and `signed_off_by: null` and lists test_ids. `CalendarSet.version` returns "unsigned" unless the manifest is signed.
   EVIDENCE: core/calendars/data/MANIFEST.yaml:1-4 `version: 0.1.0-draft` / `signed_off_by: null` / `signed_utc: null` / `status: 'UNSIGNED DRAFT: every row''s md5 and signed_off_by are null; the loader refuses every listed file'`; core/calendars/store.py:268-271 `def version(self) -> str:` ... `return str(v) if _signed(self.manifest.get("signed_off_by")) and v else "unsigned"`
   IMPACT: Provenance records `cal.version` and `cal.file(fid).md5` for each file used (spec:188, 934). The fixture prints version `1.0.0-fixture`.
* [md5 and signed_off_by] A file is refused (CalendarUnsigned) when:
  - file-level `signed_off_by` or `signed_utc` is empty;
  - `md5` ≠ content_md5 (md5 of canonical JSON minus the three signature fields);
  - the file has no MANIFEST row, or the manifest md5, version or signer differs;
  - the manifest row has no test id;
  - any row lacks one of the 5 row fields or its signed_off_by;
  - `covers` is missing or reversed.
   EVIDENCE: core/calendars/store.py:113-116 `def content_md5(doc: dict) -> str:` ... `body = {k: v for k, v in doc.items() if k not in SIGNATURE_FIELDS}`; :137-138 `if not _signed(doc.get("signed_off_by")):` / `raise CalendarUnsigned(f"{name}: signed_off_by is empty; an unsigned calendar file is refused (T-CAL-01)")`; :142-154 (md5, manifest, signer, test_ids checks); :164-165 `if not _signed(row.get("signed_off_by")):` / `raise CalendarUnsigned(f"{name}: rows[{i}] is unsigned")`
   IMPACT: The "store loads" half of CALENDAR_UNSIGNED is `cal.refusal(fid) is None` for each file the leg reads (spec:170).
* [what raises when unsigned: reproduced] On the shipped set:
  - `clocks.is_session("KR", 2026-11-02)` raises `CalendarUnsigned kr_sessions.yaml: signed_off_by is empty; an unsigned calendar file is refused (T-CAL-01)`;
  - US raises the same for holidays_NYSE.yaml;
  - `sessions_between("KR", ...)` raises the same;
  - `regime_tags("KR", d)` raises `CalendarUnsigned kr_regime_tags.yaml: ...`;
  - `is_session("CRYPTO", d)` → True;
  - `cal.version` → `unsigned`.
   EVIDENCE: scratchpad cal_probe.py output (quoted); core/calendars/store.py:67-68 `class CalendarUnsigned(Exception):`; :71-72 `class CalendarCoverageError(Exception):`
   IMPACT: Neither CalendarUnsigned nor CalendarCoverageError subclasses ValueError. Catch them by name and map them to CALENDAR_UNSIGNED. Crypto legs must not touch the calendar store at all.
* [shipped files and status] All 17 regular files in core/calendars/data are UNSIGNED DRAFTS (describe() says REFUSED), including MANIFEST.yaml. Coverage:
  - holidays_KRX: 2026-01-01..2027-12-31;
  - kr_sessions: 1995-01-01..2027-12-31;
  - kr_regime_tags: 1995-01-01..2027-12-31;
  - holidays_NYSE: 2025-01-01..2027-12-31.

  Current content md5s: holidays_KRX f0782ea21a395e5aecd3480071bf5ed6, holidays_NYSE 863ee0202f0bb1920d937694899dec2a, kr_regime_tags 4275b04c671f0977b05242d23abde364, kr_sessions 4155a7b24fdce46832a53d7135fe578c. These are unchanged since the earlier map.
   EVIDENCE: core/calendars/data/holidays_KRX.yaml:3 `status: UNSIGNED DRAFT - refused at load (R-20 rule 6, T-CAL-01)`; :5-7 `covers:` / `from: '2026-01-01'` / `to: '2027-12-31'`; :9 `signed_off_by: null`; holidays_NYSE.yaml:6 `from: '2025-01-01'`; kr_sessions.yaml:6 `from: '1995-01-01'`; probe `holidays_KRX.yaml REFUSED 0.1.0-draft {'from': '2026-01-01', 'to': '2027-12-31'} f0782ea21a395e5aecd3480071bf5ed6`
   IMPACT: Until the owner signs, only crypto plans run (spec:1125). Any odds test of KRX or US sessions uses fixture_set(). One test asserts that the shipped set refuses.
* [coverage ends 2027-12-31] A 30-day KR plan starting after 2027-12-02 crosses coverage. sessions_between raises `CalendarCoverageError kr_sessions v1.0.0-fixture covers 1995-01-01..2027-12-31; 2028-01-01 is outside`. regime_tags raises the same for 2028 dates. The draft notes "2027 must be signed before 2026-11-01".
   EVIDENCE: scratchpad cal_probe.py `past coverage: CalendarCoverageError ...`; core/calendars/store.py:323-328 `def require_covered(self, file_id: str, d: date) -> CalendarFile:` ... `raise CalendarCoverageError(...)`; holidays_KRX.yaml:18 `- 2027 must be signed before 2026-11-01 (spec L2101)`
   IMPACT: The spec names no refusal for out-of-coverage. Map CalendarCoverageError to CALENDAR_UNSIGNED (review F4 proposal) or add a reason, and test a horizon past 2027-12-31.
* [regime_tags price_limit] `regime_tags(market, d, *, cal=None) -> dict` is KR only. Other markets raise `KeyError "regime_tags: no regime-tag file for market 'US' (KR only)"`, and CRYPTO too. The KR price_limit is a fraction: 0.3 from 2015-06-15, open-ended (fixture also 0.3). It returns all 15 tags. The tag file carries the KOSPI schedule only.
   EVIDENCE: core/calendars/regime.py:62-66 `def regime_tags(market: str, d: date, *, cal: CalendarSet | None = None) -> dict:` / ... / `raise KeyError(f"regime_tags: no regime-tag file for market {market!r} (KR only)")`; :12 `Units are verbatim: price_limit is a fraction (0.30), sell_tax_pct is percent (0.20 = 0.20%).`; core/calendars/data/kr_regime_tags.yaml:70-76 `- effective_from: '2015-06-15'` / `effective_to: null` / ... `tag: price_limit` / `value: 0.3`; probe `regime price_limit fixture 2026-11-02: 0.3`; core/quant/tf_screens.py:514-515 `KOSPI reads regime_tags('KR', d)['price_limit'] ... the KR tag file carries the KOSPI schedule only, so KOSDAQ keeps the lab eras.`
   IMPACT: Call it only for KRX legs, with `cal=` injected. KONEX (±15%) is not in this file. If structural_max covers KONEX legs (spec:821), the 0.15 limit needs another signed source.
* [other KR tags the plan may want] Two more tags may matter:
  - `sell_tax_pct` is 0.2 (percent, 2026-01-01, open-ended), while instruments.SELL_TAX_BP holds only 2026.
  - `tick_regime` is only a label (`stocks_reformed_etf_w1_tick_below_w2000` from 2023-12-11), not a ladder.
   EVIDENCE: kr_regime_tags.yaml:389-396 `- effective_from: '2026-01-01'` / `effective_to: null` ... `tag: sell_tax_pct` / `value: 0.2`; :413-419 `tag: tick_regime` / `value: stocks_reformed_etf_w1_tick_below_w2000`; core/quant/instruments.py:20 `SELL_TAX_BP = {2026: 20.0}`
   IMPACT: The stock ladder cannot come from regime tags, so it comes from venues.yaml. If the KRX stock floor includes a tax, sell_tax_pct (×100 → bp) is a 2027-safe source. SELL_TAX_BP refuses 2027.
* [sessions_between endpoints] `sessions_between(market, lo, hi, *, cal=None) -> list[date]` includes BOTH endpoints. It returns `[]` when hi < lo, and `[d]` when lo == hi. CRYPTO returns every calendar day. Market codes are "KR", "US", "JP", "CN", "HK", "TW" and "CRYPTO". Others raise KeyError.
   EVIDENCE: core/calendars/clocks.py:223-229 `def sessions_between(market: str, lo: date, hi: date, *, cal: CalendarSet | None = None) -> list[date]:` / `out, probe = [], _date(lo)` / `while probe <= hi:`; :189-191 `if market == "CRYPTO":` ... `return True`; :97-99 `if market not in M1_MARKETS:` / `raise KeyError(...)`; probe `sessions_between KR same day: [datetime.date(2026, 11, 2)]`, `hi<lo: []`
   IMPACT: The half-open horizon [start, start+H) is `sessions_between(m, start, start + timedelta(days=H - 1), cal=cal)`. Using `start + H` adds a session (31-day closed windows reach 23). Map section krx → "KR", us → "US", crypto → "CRYPTO".
* [KR is_session reads two files] KR requires both kr_sessions and holidays_KRX to be covered and signed. US requires holidays_NYSE only.
   EVIDENCE: core/calendars/clocks.py:194-197 `if market == "KR":` / `cal.require_covered("kr_sessions", d)` / `cal.require_covered(f"holidays_{set_id}", d)`; core/calendars/store.py:42-44 `MARKET_FILES = {` / `"KR": ("kr_sessions", "holidays_KRX"),` / `"US": ("holidays_NYSE",),`
   IMPACT: For CALENDAR_UNSIGNED, KRX legs check kr_sessions, holidays_KRX and kr_regime_tags; US legs check holidays_NYSE.
* [the old calendar package is a different source] `core/calendars/__init__.py` serves `is_trading_day` from generated `data/calendars/*.json` (exchange_calendars). It is NOT the signed store.
   EVIDENCE: core/calendars/__init__.py:1-3 `"""Exchange holiday and special-session data, loaded from static JSON.` / `The files under data/calendars/ are generated offline by`; :144 `def is_trading_day(market: str, day: date) -> Optional[bool]:`; compliance plan Appendix A P21 (plan line ~16872) `data/calendars/*.json is excluded.`
   IMPACT: odds must use `core.calendars.clocks` and `store` with `cal=`, never `core.calendars.is_trading_day`.
* [calendar set approval: sha256 exists now] The earlier map said there is no calendar-set sha256. That is now STALE. `core.compliance.rules.calendar_stream(data_dir)` frames every regular file (sorted name + NUL + bytes + NUL; links refused), and `calendar_sha256` hashes it. The shipped draft set hashes to 42c7b8e00a8e7d3a29d824be15fc3164345278c84312bd4303be3ec39e827547 over 17 files.
   EVIDENCE: core/compliance/rules.py:721-738 `def calendar_stream(data_dir: Path) -> bytes:` ... `parts.append(e.name.encode("utf-8") + b"\0" + Path(e.path).read_bytes() + b"\0")`; :740-742 `def calendar_sha256(data_dir: Path) -> str:`; docs/superpowers/plans/2026-10-23-compliance-gate-repo-map.md:351 `[No calendar-set sha256] No function hashes a calendar set as a whole.` (stale); scratchpad calsha.py output
   IMPACT: The odds CALENDAR_UNSIGNED check compares the in-force `approved {kind: calendar}` sha256 with the set it simulates on. Reuse `rules.calendar_stream` / `calendar_sha256`; never write a second framing (ledger Task 13 ruling).
* [approved store layout] An approved calendar set is stored as the directory `<store_dir>/calendar/<sha256>/` holding the files. store_get rebuilds the stream and returns None if the bytes no longer hash to the name.
   EVIDENCE: core/compliance/owner.py:648 `or the directory calendar/<sha256>/ (then raw is rules.calendar_stream of the set), plus <kind>/<sha256>.anchor.json`; :675-680 `path = store_dir() / kind / (sha256 if kind == "calendar" else f"{sha256}.yaml")` ... `return raw if model.sha256_hex(raw) == sha256 else None`; :43-44 `def store_dir() -> Path:` / `return home() / "approved"`
   IMPACT: Production can run `CalendarSet(store_dir()/"calendar"/sha)` on exactly the approved bytes. The anchor json sits beside the directory, not in it.
* [Context does not carry the calendar approval] The rules CLI re-reads the owner log to find the calendar approval, because Context lacks it.
   EVIDENCE: core/compliance/rules.py:904-905 `"""The calendar draft (P21) against the latest calendar approval signed by moment (load_context's cut-off),` / `whose stored copy must be intact. The Context does not carry it, so the log is read and verified once more."""`; :916 `signed = owner.in_force(owner._up_to(log, model.iso_utc(moment))).get("calendar", ("", 0))[0]`
   IMPACT: The odds plan needs a supported way to get the in-force calendar sha256: a new Context field (a compliance change) or a public owner helper. Do not call private `owner._up_to` from core/odds.

## F. Session counts (16..22) computed

* [shipped holidays: 16..22 confirmed] The shipped holidays_KRX has 29 `closed` rows (no early-close or open kinds) in 2026-2027 and no weekend rows. Half-open 30-day windows (start + 0..29) for every start from 2026-01-01 to 2027-12-02 (701 starts) hold min 16 and max 22 KRX sessions, and the same in each year. Minimum starts: 2026-02-07, 2026-02-14, 2026-09-12, 2026-09-19, 2027-09-11, 2027-09-12. There are 246 sessions in 2026 and 247 in 2027.
   EVIDENCE: scratchpad krx_count.py output `30d half-open window sessions min 16 max 22 n_starts 701 last start 2027-12-02` / `2026 min 16 max 22` / `2027 min 16 max 22`; spec:92 `a 30-day window (half-open) holds **16 to 22** KRX sessions in 2026 and 2027`
   IMPACT: Cap (1.3/0.7)·1.3^(n−1) = 95.06× at n=16 and 458.83× at n=22, so the spec's "about 95× to 459×" holds. The smallest n that reaches 1,000× is 25 (n=24 gives 775.43×, n=25 gives 1,008.06×). A 30-day buy-and-hold KRX leg is therefore always IMPOSSIBLE at 1,000×. A test with a longer horizon (≥ 25 sessions) is not.
* [fixture: same 16..22] On the fixture set, `len(sessions_between("KR", d, d+29, cal=fixture_set()))` over the same starts gives min 16 and max 22. The fixture's 2026 and 2027 weekday closures match the shipped list. It also closes fixed dates every year, weekends included, which does not affect counts.
   EVIDENCE: scratchpad cal_probe.py `fixture 30d half-open min/max 16 22`; tests/macro_m1_calendars.py:109-115 `_KRX_EXTRA = {` ... `2026: ["02-16", "02-17", "02-18", "03-02", "05-01", "05-25", "08-17", "09-24", "09-25", "10-05", "10-09"],` / `2027: ["02-08", "02-09", "05-13", "08-16", "09-14", "09-15", "09-16", "10-04", "10-11", "12-27"],`; :118-122 `for md in ((1, 1), (3, 1), (5, 5), (6, 6), (8, 15), (10, 3), (12, 25), (12, 31)):`
   IMPACT: The "IMPOSSIBLE with N computed from the fixture calendar" test (spec:1030) can assert n in [16, 22] for a 30-day window and the matching cap.
* [NYSE] Shipped NYSE 30-day half-open windows over 2026-01-01..2027-12-02 starts hold 18..22 sessions. Early closes (13:00) are sessions: 2026-11-27, 2026-12-24 and 2027-11-26.
   EVIDENCE: scratchpad nyse_count.py `NYSE 30d half-open min/max 2026-01-01..2027-12-02 starts 18 22`, `early {'2026-11-27': '13:00', '2026-12-24': '13:00', '2027-11-26': '13:00'}`
   IMPACT: Useful bounds for US-leg step-count tests.
* [fixture facts] `fixture_set(key="main", docs=None) -> CalendarSet` writes signed temp files (signer "TEST-FIXTURE (not an owner sign-off)") and caches them per key per process. Coverage:
  - KRX, kr_sessions, kr_regime_tags: 1995-01-01..2027-12-31;
  - NYSE: 2006-01-01..2027-12-31.

  Fixture price_limit for 1995-Q1 is 0.046 (shipped: null).
   EVIDENCE: tests/macro_m1_calendars.py:22 `SIGNER = "TEST-FIXTURE (not an owner sign-off)"`; :245-251 `def fixture_set(key: str = "main", docs: dict | None = None) -> CalendarSet:` ... `_CACHE[key] = (tmp, CalendarSet(Path(tmp.name)))`; :151 `span = ("1995-01-01", "2027-12-31")`; :161 `docs["holidays_NYSE"] = _doc("holidays_NYSE", ("2006-01-01", "2027-12-31"), "NYSE", nyse_rows)`; :215 `"price_limit": [("1995-01-01", "1995-03-31", 0.046), ...`
   IMPACT: Import it from tests/odds_acceptance.py (the spec says so, spec:172). Do not invent another signer. A shipped-refuses test uses `store.CalendarSet()`.

## G. Ticks, lots and minimums in the repo or research

* [KRX stock tick ladder: research only] The ladder is <2,000: 1; 2,000-5,000: 5; 5,000-20,000: 10; 20,000-50,000: 50; 50,000-200,000: 100; 200,000-500,000: 500; ≥500,000: 1,000 KRW. Source: KRX global page, in a tracked research note "As of 2 October 2026". Another note says KRX ticks were not verified there.
   EVIDENCE: QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/research_notes/E2_nyse_microstructure_execution.md:304 `- **Tick sizes.** One tick ranges from 0.05% to 0.25% of price:` and :306-314 table rows `| below 2,000 | 1 |` ... `| 500,000 and above | 1,000 |`, :316 `— [KRX tick sizes](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp)`; QUANTGEN_techfund_research_bundle/.../P4_backtest_econometrics_costs.md:262 `KRX tick sizes were not verified here.`
   IMPACT: The venues.yaml stock ladder is owner-signed data marked UNVERIFIED with this source URL. It has an effective-from date (the 2023-01-25 reform per the regime tag) and a test for boundaries such as 1,999/2,000 and 49,999/50,000.
* [KRX ETF tick: in repo; research conflicts] Repo: 1 KRW below 2,000 and 5 KRW at or above, from 2023-12-11. The kr_regime_tags label agrees. One research note believed 5 won at every price level (UNVERIFIED).
   EVIDENCE: core/quant/instruments.py:27 `"KRX_ETF": ((date(2023, 12, 11), ((2000.0, 1.0), (math.inf, 5.0))),),`; kr_regime_tags.yaml:420 `unverified: 'spec L2045: ETFs 1 won tick below 2,000 won from 2023-12-11'`; research_notes/QUANTGEN asset coverage expansion/etf_strategies.md:98 `KRX ETF tick size (5 won is believed to apply to ETFs regardless of price level) — UNVERIFIED in this session`
   IMPACT: odds uses instruments' KRX_ETF table (through cost_per_side or tick_size) and does not duplicate it in venues.yaml.
* [Upbit KRW minimum 5,000] KRW 5,000 is confirmed by research from Upbit docs. It appears in the rules table and the spec only as prose.
   EVIDENCE: research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas_verification.md:21 `**Upbit 5,000 KRW minimum is confirmed** by Upbit's own docs.` ... `[Upbit docs](https://docs.upbit.com/kr/docs/krw-market-info)`; core/compliance/kr_rules.yaml:402 `reason: "KRW spot on the FIU-registered exchanges is legal at 1x (Upbit minimum order KRW 5,000)"`; spec:351, :776
   IMPACT: A structured minimum must be added to venues.yaml, which hits the strict-parser blocker in C.
* [Upbit KRW tick ladder: absent] No Upbit price-unit (tick) table exists in the repo or the research notes. Upbit's KRW fee of 0.05% is confirmed, below the 10 bp crypto table rate.
   EVIDENCE: grep for Upbit tick or 호가 found none; research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas_verification.md:21 `**Upbit KRW fee 0.05% is confirmed** for 2026`
   IMPACT: The crypto floor cannot be computed without new owner data. Either take the table rate only (price=None quote) for crypto, or have the owner sign an Upbit ladder. Rounding to the KRW tick for limit or bracket prices is likewise unavailable.
* [US lots, minimums, ticks: absent or uncertain] US_shares_KIS lot_size and tick are OWNER_INPUT. Research: fractional US shares "from KRW 1,000 at Toss (blog source, UNCERTAIN for other brokers)". KIS 미니스탁 minimums were not retrieved. No US tick ($0.01) fact is in the repo.
   EVIDENCE: core/quant/instruments.py:72 (row quoted above); research_notes/Korean resident trading venue legality/overseas_via_brokers.md:9 `fractional from KRW 1,000 at Toss (blog source, UNCERTAIN for other brokers)`; :38 `Official fractional-trading minimums and eligible-ticker lists for KIS (미니스탁), ... were not retrieved.`
   IMPACT: US lot, minimum and fractional flags are owner inputs in venues.yaml. Default to whole shares (round down) with no fractional unless signed.
* [KRX lot] Research: KOSPI/KOSDAQ cash stocks have a minimum ticket of 1 share. Domestic fractional trading was not researched.
   EVIDENCE: research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md:161 `| KOSPI/KOSDAQ cash stocks (KRX, NXT) | legal | yes | 1 share | 1x |`; :176 `Domestic fractional-share trading (소수점 거래) minimum tickets were not researched.`
   IMPACT: KRX lot = 1 share, whole units (owner-signed in venues.yaml).

## H. Import closure (D14) consequences of reusing these modules

* [code_files includes core/odds and everything it imports] The D14 code hash covers core/compliance/*.py, core/odds/*.py and every in-repo file they import at any depth, function-level imports included. Importing `core.quant.instruments` pulls 24 files into the closure: config.py, core/quant/history.py, validate.py, data/krx/kis_client.py, data/crypto/crypto_client.py, data/net.py, and others (through validate.cost_class's lazy history import). The calendars store, clocks and regime modules pull 37, including core/rules/macro_rules.py, core/ficc/contracts.py and pit.py.
   EVIDENCE: core/compliance/owner.py:767-773 `def code_files(repo_root: Path) -> list[tuple[str, str]]:` / `"""Sorted (relative POSIX path, sha256) of the D14 code closure (P6): core/compliance/*.py and core/odds/*.py,` / `every in-repo file they import at any depth,` ... `todo = [p for sub in ("compliance", "odds") for p in sorted((root / "core" / sub).glob("*.py"))]`; core/quant/validate.py:93 `from core.quant.history import _looks_crypto     # the same routing load_history uses`; scratchpad closure_costs_cal.py output `instruments 24 [...]` / `calendars store+clocks+regime 37 [...]`
   IMPACT: Once core/odds/*.py exists, any edit to those files changes code_hash, and the owner must re-sign code_approved. The plan should say so and list the closure. bars.py's data loaders add to it anyway.

## I. Compliance follow-up items touching this area (ledger)

* [calendar_sha256 OSError and empty set] Deferred minor: OSError from read_bytes escapes calendar_sha256, and an empty dir hashes to the empty-string sha256. Today's callers catch it: `_calendar_line` catches (Invalid, OSError), and store_get catches (OSError, rules.Invalid). An empty stream cannot be stored (`_calendar_files` needs ≥ 3 parts).
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md:102 `Task 4: minor (deferred): calendar_sha256 lets OSError from read_bytes escape; empty dir hashes to empty sha256 (callers compare to approved hash)`; core/compliance/rules.py:923 `except (Invalid, OSError):`; core/compliance/owner.py:678 `except (OSError, rules.Invalid):`; :636-638 `parts = raw.split(b"\0")` / `if len(parts) < 3 or len(parts) % 2 == 0 or parts[-1] != b"":`
   IMPACT: In the follow-up, wrap read errors in Invalid inside calendar_stream and refuse an empty set. Any new odds caller of calendar_sha256 must catch OSError until then.
* [calendar store framing minors] Three deferred minors: store_put can report success on a calendar folder with an extra file while store_get returns None; a NUL byte in a calendar file name or content breaks the framing; a lone-surrogate filename raises UnicodeEncodeError.
   EVIDENCE: execution-ledger.md:205 `Task 13: minor (deferred): store_put can report success on a calendar folder with an extra file while store_get returns None (fail closed)`; :209 `a NUL byte in a calendar file name/content framing; UnicodeEncodeError on a lone-surrogate filename not caught`
   IMPACT: These are candidates for the follow-up plan. Odds relies on store_get returning None (fail closed) for a damaged set.
* [calendar-line adaptations untested] Deferred minor.
   EVIDENCE: execution-ledger.md:220 `Task 14: minor (deferred): calendar-line adaptations untested;`
   IMPACT: Follow-up test item.
* [zero stake to screen()] Carried to odds: never send a zero stake to screen().
   EVIDENCE: execution-ledger.md:244 `Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw)`
   IMPACT: When the cost or minimum rules give STUCK_AT_START, refuse before calling screen().
* [compliance hand-off wording is not implementable] The plan's Step 10 says to "pass nav_fx and the venues.yaml tick ladder to cost_per_side". But cost_per_side has no tick parameter; it reads `book.tick_table` → TICK_TABLES only.
   EVIDENCE: docs/superpowers/plans/2026-10-23-compliance-gate.md:16744-16745 `- pass nav_fx and the venues.yaml tick ladder to cost_per_side, because the spec's literal per-fill call` / `raises NotTradable for KRX_stock_book, US_shares_KIS and crypto_venue today;`; core/quant/instruments.py:180 `tick_size(book.tick_table, price, on)`
   IMPACT: The odds plan computes the non-ETF floor itself with `instruments.tick_floor_bp`, or adds a tick parameter to instruments.py. The second option touches a T-COST-pinned module and the macro tree hash, so the first is the lazy, safe path.

## Open questions

1. KRX stock sell floor: should the odds floor include the 20 bp sell tax inside the max (the repo rule, which binds below about 368 KRW), or use tax 0 (a literal reading of "no separate sell tax")? If the tax is included, take it from regime_tags `sell_tax_pct` (valid in 2027) or from instruments.SELL_TAX_BP (2026 only; private `_sell_tax_bp` refuses 2027)?
2. US and crypto floors: is the floor applied at all? There is no signed tick: US $0.01 is not in the repo, and the Upbit KRW ladder is absent. Is `COMMISSION_BP = 1.4` (an "EX2 desk quote" for KRX) the right commission term for US or crypto, or is the class-only table rate (50 or 10 bp) the whole κ for those books until the owner signs ticks?
3. Band tick at each edge: one tick, as in orders.limit_prices, or the ladder's tick at each edge price (e.g. ETF ref 2,005: lower edge 1,405 vs 1,404)? The real KRX rounding rule is not in repo evidence.
4. Where does check_extras live (models.py per review F2, or plan.py), what is its signature, and does a missing φ entry mean φ = 0 or NOT_TRADABLE?
5. Venues schema: extend `_VENUE_OPTIONAL` in core/compliance/rules.py, or bump to `tradegen.venues/2` with a nested `odds:` block? Which plan (odds or compliance follow-up) owns the change, and the edit to tests/compliance_tables.py:633?
6. CalendarCoverageError, e.g. a horizon past 2027-12-31: map to CALENDAR_UNSIGNED or a new named reason? The spec lists none.
7. How does odds learn the in-force calendar sha256: a new Context field, or a public owner helper? Today only rules.py re-reads the log, and Context does not carry it.
8. US legs: are sessions counted on NYSE dates or on the Asia/Seoul date of the close (spec:166-167 maps bars to the Seoul close date)? Which date is `on=` for a US fill?
9. KONEX buy-and-hold (structural_max names KONEX legs, spec:821): there is no ±15% signed source (the regime file is the KOSPI schedule), and KONEX has no odds cost book. Refuse it?
10. Shipped holidays_KRX omits 2026-06-03, the local election day. That is outside knowledge: the draft is "cross-checked against exchange_calendars XKRX only" (holidays_KRX.yaml:16). It is a past date, and adding it leaves the 16..22 range unchanged (probe). It is still an owner verification item.
11. Should tests inject `config=` into fixture_set to avoid reading the shipped macro rules store for Saturday checks, or is that read acceptable?
