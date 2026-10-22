# QUANTGEN / TRADEGEN split map

Date: 2026-10-23. Source: an eight-area read-only audit of `C:/Users/whydi/OneDrive/Desktop/QUANTGEN`, plus targeted checks of `grokteam/out/PREREG_book.json`, `paper_live/out*/HYPOTHESES_frozen.json`, `grokteam/book.py`, `grokteam/prereg.py` and `tests/macro_m5_integration.py`. No repo code was run or edited. See the provenance note at the end.

Definitions used here:
- **QUANTGEN** keeps quantitative-finance research: models, estimation, validation, FICC pricing, portfolio theory, backtests and gates. It may go as far as paper trading and never sends real orders.
- **TRADEGEN** starts as a full copy of today's QUANTGEN, so it inherits everything, the non-quant parts included. "Leaves QUANTGEN" below therefore means *removed from QUANTGEN after TRADEGEN holds a verified copy*. Nothing is lost.

---

## 1. Bottom line

- **What is clearly non-quantitative trading:**
  - the **GROKTEAM ("GrokBot") package**: `grokteam/`, the Kalshi KXBTCD BOOK desk benchmarking lazyowen's 7-bot Grok guide, frozen 2026-10-22;
  - its design note `research_notes/grokteam_benchmark_analysis_2026-10-21.md`;
  - the **LAZYOWEN accounts inside `paper_live/`**, ported from the 2026-10-06 Polymarket Grok $50 guide.
- **Two further non-quant pieces the readers found:**
  - the **inherited NEXTGEN trading-skills cockpit**: 11 `core/skills/*` modules plus 5 UI files. It runs the third-party `claude-trading-skills` repo (CANSLIM, VCP, Stockbee, Druckenmiller and parabolic-short planners);
  - two small heuristic or LLM pieces: `core/crypto/analytics.py::regime_score`, and the LLM "Positioning ideas" prompts in `core/ficc/insights.py`.
  - The cockpit is a judgement call for the owner (section 7, Q1). Its own content is discretionary or practitioner screening, not quant research.
- **What stays:** everything else, which is about 90% of the code: all of `core/quant` (33 modules), all of `core/ficc` except the LLM prompts, `core/crypto` quant tests, the macro overlay, calendars and PIT layer, data clients, the simulated operator engine, `paper_live` minus LAZYOWEN, every quant UI page, and every doc, report, council and tech-fund research file.
- **No real-order path exists anywhere.** Greps for KIS order endpoints (TTTC/VTTC/order-cash), place_order and submit_order found nothing. Upbit access is read-only. QUANTGEN already meets the "paper trading at most" limit.
- **Size of the change in QUANTGEN:**
  - delete 4 `grokteam` source files plus `grokteam/out/` and move 1 note;
  - optionally delete 16 cockpit files;
  - surgically edit about 25 MIXED files (section 3);
  - write 0 new quant code, except an optional port of 4 quant functions out of `grokteam/book.py` (Q9).
  - The test suite shrinks by 17 checks (grokteam) and, if the cockpit goes, by about 35 more (tests/acceptance.py cockpit half).
- **Why the timing matters:**
  - Frozen studies pin QUANTGEN's own core files. These are the GROKTEAM BOOK forward look on/after **2027-02-01** and the paper_live **H2 holdout readout about 2026-11-03**.
  - The split must therefore be **copy first, then remove in three phases** (section 4.4). Phase 1 can be done now. Phase 2 (LAZYOWEN) must wait for the H2 readout.

---

## 2. Leaves QUANTGEN (NON_QUANT_STRATEGY)

| path | what | why | breakage if removed | how to remove cleanly |
|---|---|---|---|---|
| `grokteam/__init__.py`, `grokteam/book.py`, `grokteam/prereg.py` | GROKTEAM BOOK desk. It paper-replays the guide's BOOK/SIZE rules (accounts PRED-GATED, PRED-LIT8, PRED-FLB) on Kalshi KXBTCD hourly BTC binaries, using a seasonal GARCH-t digital as the "own probability", and freezes and checks its pre-registration | Exists only to benchmark a copied LLM-bot trading guide (lazyowen.com, 2026-10-20) on a venue a Korean resident may not use | `tests/run_all.py:49` imports `grokteam.selfcheck` at module load, so the **whole runner dies** with ImportError. That includes `tests/macro_m0_harness.py`, which imports `tests.run_all`. Also README L763/L785/L786. No `core/`, `ui/`, `data/` or `paper_live/` file imports grokteam (selfcheck `test_no_paper_live_import` confirms paper_live is independent) | All three are **sha256-pinned** (section 4), so never edit them. (1) Copy the whole repo byte-for-byte to `Desktop/TRADEGEN`. (2) In TRADEGEN run `python -m grokteam.prereg` (check mode): it must list no changes. (3) Delete `grokteam/` from QUANTGEN **in the same change** as run_all.py L49/L65/L111 and README L763/L785/L786. Re-implement the reusable quant functions as new QUANTGEN code (Q9) |
| `grokteam/selfcheck.py` | 17 offline self-checks of the BOOK desk (fee/payoff, SIZE, digital probability, no look-ahead, block t, verdict, blinding, calibration, cache, ledger, version pin) | Tests only the guide desk | Same run_all.py lines as above. `qa/acceptance_results.json` loses 17 rows on the next run | Moves with the package. If the quant functions are ported, port `test_digital_probability`, `test_model_sees_only_closed_bars`, `test_calibration_recovers_identity` and `test_block_t` with them |
| `grokteam/out/` (`PREREG_book.json`, `frozen_book/`, `book/`, `book_smoke/`) | The frozen pre-registration record, byte copies of the 10 pinned files, and replay outputs | Artifacts of the guide benchmark | If `PREREG_book.json` disappears while `frozen_book/` exists, `book.main` exits ("the freeze happened and its record is lost") | Moves with the package, unchanged. `FORWARD_LOOK.json` will be written once, in TRADEGEN, on/after 2027-02-01 + 1 h |
| `research_notes/grokteam_benchmark_analysis_2026-10-21.md` | Analysis memo: verdict "No" on the guide's profit claims, rule portability table, BOOK and (unbuilt) MEME desk design, verdict rules, N*/MDE, skeptic ledger | Design note of the guide benchmark | The docstring of pinned `grokteam/__init__.py` names this path. Nothing imports it | Keep it at the **same relative path in TRADEGEN**, since the pinned docstring points there. Optionally keep a short QUANTGEN literature note made from its section 1 evidence table, section 3 statistical design and the skeptic-ledger items about QUANTGEN functions (see section 3) |
| `core/skills/index.py`, `entrypoints.py`, `params.py`, `readiness.py`, `runner.py`, `runs.py`, `diagnose.py`, `workflows.py`, `decisions.py`, `insights.py`, `wiring.py` (**owner confirm, Q1**) | The NEXTGEN cockpit backend. It catalogues and runs the external `claude-trading-skills` repo (72 skills; workflows such as swing-opportunity-daily, stockbee-ep-daily, shapiro-contrarian) from `~/Downloads/claude-trading-skills-main` | Practitioner and discretionary screeners, not quant models. QUANTGEN's own macro pipeline does not use this runner | `core/skills/__init__.py` eagerly imports 6 of them, so every quant import of `core.skills.macro_daily`/`pipeline`/`alerts` fails until the init is emptied. Also breaks: `main.py` (`reload_all`, 3 NAV rows), `ui/settings_page.py`, `ui/components.py` (`readiness.State`), `tests/acceptance.py` (cockpit suite), `tests/macro_m8_pipeline.py:132` (`import core.skills.workflows`) | One change: empty `core/skills/__init__.py`; delete the 11 files; inline a `State` enum in `ui/components.py`; edit `main.py`, `settings_page.py` and `config.py` as in section 3; split `tests/acceptance.py`; rewrite `macro_m8_pipeline.py:132` as a negative check (`importlib.util.find_spec("core.skills.workflows") is None`). Keep `core/skills/macro_daily.py`, `pipeline.py`, `alerts.py` and `macro_workflows/` |
| `ui/skills_page.py`, `ui/workflows_page.py`, `ui/runs_page.py`, `ui/param_form.py`, `ui/charts.py` (**owner confirm, Q1**) | Cockpit UI: skill catalogue and run panel, multi-skill workflows with decision gates, run history, argparse forms, insight charts | Serve only the cockpit | `main.py` imports the three page builders | Delete together with the backend row above |
| Outside the repo: `~/.nextgen/macro/ledgers/GROKTEAM-BOOK.jsonl`, `LAZYOWEN.jsonl`; `~/.nextgen/grokteam/` (env `GROKTEAM_DATA`); `~/.nextgen/runs/`; `~/Downloads/claude-trading-skills-main` | Trial ledgers of the guide families, the Kalshi/Binance cache, cockpit run history, and the third-party skills repo | State of the non-quant work | `grokteam/book.main` registers trials on **every** non-smoke run into `GROKTEAM_LEDGER_DIR` or `config.macro_dir()/ledgers`. The ledgers are append-only and hash-chained, and `tf_gov` counts global N over every family file there | **Never delete ledger rows.** Copy the two family files whole to TRADEGEN's ledger dir and point TRADEGEN at it (`QUANTGEN_MACRO_DIR` or `GROKTEAM_LEDGER_DIR` in TRADEGEN's `.env`). Whether QUANTGEN's copies stay counted is Q7 |
| LAZYOWEN code in `paper_live/` | See section 3 (MIXED) | Copied Polymarket-guide rules | See section 3 | **Not before the H2 readout (about 2026-11-03).** Phase 2 |

---

## 3. MIXED files: exact surgical split

Format: **remove** goes to TRADEGEN (or is deleted from QUANTGEN because TRADEGEN already holds the copy); **keep** stays in QUANTGEN; **then** lists the follow-up fixes.

### 3.1 GROKTEAM-related (Phase 1)

**`grokteam/book.py`** (pinned; moves **whole**; never cut in place)
- Quant functions to **re-implement as new, unpinned QUANTGEN code** (copy the logic, not the file):
  - `_group` and `model_at`: GARCH(1,1)-t de-seasonalised by hour-of-day x weekend RMS over 48 groups, with multi-step variance aggregation;
  - `p_above`: digital P(S_T > K) under unit-variance t or normal;
  - `fit_calibration` and `calibrate`: MLE logistic recalibration;
  - `skill`: log loss and Brier vs market mid, a one-sided DM, reliability tables;
  - `block_t`: CR1 cluster t over 5-day blocks with a t(G-1) CI;
  - the MDE/N* lines in `readout`;
  - the rolling-median basis estimator inside `strike_table`.
- TRADEGEN only:
  - constants `GUIDE`, `KALSHI`, `SERIES`/`FAMILY`, `ACCOUNTS`, `SEEN`, the ARCHIVE/FORWARD dates;
  - the Kalshi client: `kalshi`, `_slot`, `_throttled`, `settled_events`, `fetch_event`, `fetch_all`, `unsettled_in_window`;
  - `fee`, `buy`, `candidates`, `choose`, `stake`, `fill_price`, `run_accounts`;
  - `readout`/`verdict` (guide accounts), `trial_rows`, `register_trials`, `frozen`, `forward_gate`, `main`, `report_text`.
- Shared infra (QUANTGEN already has equivalents): `write_cached`, `read_cached`, `_manifest`, `binance_1m`, `hourly_bars`.

**`research_notes/grokteam_benchmark_analysis_2026-10-21.md`** (moves whole)
- Optional QUANTGEN literature extract:
  - section 1 evidence table: Kalshi taker/maker returns (Burgi, Deng & Whelan), LLM forecast Brier 0.126 vs market 0.111, meme-coin base rates;
  - section 3 statistical design: cluster t, DM skill gate, Holm, MDE = 2.4865 sd/sqrt(n), N*;
  - skeptic-ledger items about QUANTGEN functions: `dm_test` is two-sided; `block_bootstrap_ci` bootstraps the Sharpe, not the mean; `horizon_vol` is annualised; `BinancePublic` bars are stamped at open (a 1 h look-ahead trap).
- TRADEGEN: section 2 (guide-rule portability), the MEME desk spec, the plan (`record.py`/`desk.py`, never built), section 6 decisions, the guide, DEX and pump.fun sources.

**`tests/run_all.py`**
- Remove: L49 `from grokteam.selfcheck import tests as grokteam_tests`, the `grokteam/{n}` term in `tests()` at L65, and "grokteam" in the `--suite` help at L111.
- Keep: everything else.
- Then: totals go from 848 to 831 (727 to 710 PASS as of 2026-10-22).

**`README.md`**
- Remove: L763 "or grokteam" in the suite list and the L785 grokteam Verification row; recount the L786 Total.
- If the cockpit goes: rewrite L3-4 ("skill cockpit all survive intact"), L738-747 ("Everything inherited from NEXTGEN"), and the cockpit row at about L777.
- Wording: "personal quant trading application" becomes "research".
- Then: no test asserts these lines. `tests/macro_ui_components.py` checks only the disclaimers, P0-P10 and the MACRO-R06-US text.

### 3.2 Cockpit-related (Phase 1, only if Q1 = move)

**`core/skills/__init__.py`**
- Remove: eager imports L4-10 (entrypoints, index, readiness, runner, runs, workflows), `__all__` and `reload_all()`.
- Keep: an empty package docstring.
- Then: `core.skills.macro_daily`, `pipeline` and `alerts` import cleanly without yaml or the cockpit.

**`config.py`** (not pinned, but a runtime dependency of pinned and frozen code)
- Remove:
  - `_DEFAULT_SKILLS_ROOT`, `skills_root`, `skills_root_valid`, `skill_python`, `SKILL_TIMEOUT_SECONDS`, `runs_dir`;
  - `SKILL_CREDENTIALS` (finviz, alpaca, fxmacrodata; fmp is shared, so keep the fmp helpers);
  - `KEYLESS_INTEGRATIONS`, `FILE_INPUT_INTEGRATIONS`, `skill_credential_present`, `skill_env`, `skill_provider_status`.
- **Keep untouched:** `macro_dir`, `HTTP_TIMEOUT_SECONDS`, `NO_DATA_GRACE_TICKS`, `upbit_ready`, `upbit_keys`, and every name the frozen and pinned code reads (`grokteam/book.py:737`, `prereg.py:131`, `paper_live/engine.py:101`, `data/net.py`, `data/crypto/crypto_client.py`). Keep all data, provider, engine, AI, gs_quant and FICC helpers too.

**`main.py`**
- Remove:
  - `from core.skills import reload_all`;
  - the imports of `build_workflows_page`, `build_skills_page` and `build_runs_page`;
  - NAV rows `workflows`, `skills` and `runs`, with their `build()`/`navigate` branches;
  - `reload_catalogue()`, and `on_reload=` on the settings page.
- Keep: the 16 quant NAV entries, `on_app_start(macro_daily)`, the shell and layout.

**`ui/settings_page.py`**
- Remove:
  - the imports `core.skills.index.all_skills` and `core.skills.readiness.summarize`;
  - the skills-root block (about L54), the `SKILL_PROVIDER` links including alpaca (about L29), the runs-dir row (about L185);
  - the ALPACA/FINVIZ lines in the `.env` snippet (about L195) and the reload-catalogue button.
- Keep: the KRX, FICC, KIS, crypto/Upbit read-only, gs_quant and Anthropic rows.

**`ui/components.py`**
- Remove: `from core.skills.readiness import State`.
- Keep: everything else. Inline a 4-value `State` enum for the chip style map.

**`.env.example`**
- Remove: the "Skill-library providers" block (`FINVIZ_API_KEY`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `FXMACRODATA_API_KEY`).
- Keep: the FMP, KIS, OPENDART, KRX, ANTHROPIC, GS, UPBIT (read-only), FICC cache and grace keys.

**`tests/acceptance.py`**
- Keep (QUANT_INFRA):
  - helpers `_read`, `_code_only` and `runtime_py`, imported by 7 macro modules (m0_harness, m1_fixtures, m1_pit, m2_costed, m5_fills_events, m7_integration, m7_ledger);
  - safety scans `test_08_no_broker_order_path` and `test_09`, which back README principle P0;
  - `test_10` to `test_18` (redaction, settings, regressions) and `test_21`/`test_22` (KRX gateway).
- Remove: `test_01` to `test_07b` (catalogue), `test_19`/`test_20`, and `test_23` to `test_46` (runner, argument reader, workflow gates).

**`tests/macro_m8_pipeline.py`**
- Change L132 `import core.skills.workflows as W` to a negative existence check. The assertion's intent (the macro pipeline is not routed through the legacy parser) survives.

### 3.3 Heuristic / LLM pieces (Phase 1, owner confirm)

**`core/crypto/analytics.py`** (Q3)
- Remove: `regime_score`, `RegimeComponent`, `RegimeScore`, `_sma` (about L178-280), and the docstring bullet citing the crypto-regime-analyzer skill. This is a re-authoring of that skill's hand-set bands (weights 25/20/15/15/15/10), which the skill itself calls "not validated allocation rules". Card C6 was never gated.
- Keep: `kimchi_premium`/`KimchiPremium`/`_hac_var`, `funding_carry`/`FundingCarry`, `eth_btc_test`, `weekday_table`, `garch_scorecard`/`GarchScorecard`, `_align`.
- Then: remove the `ui/crypto_page.py` L77 `out['regime'] = CA.regime_score(...)` call and the regime tile, and the README crypto line about the regime score (about L215). No test references `regime_score`.

**`core/ficc/insights.py`** (Q4)
- Remove: `REPORT_PROMPTS` "Positioning ideas"/"Positioning" clauses asking for 2-4 trades with entry, stop and target (about L539-557); `report_prompt()`; `deep_analysis()` (about L560-572); the self-check lines about L705-714.
- Keep: all `narrate_*` functions, the formatting helpers, and the re-export of `Analysis`/`ai_ready`. Relabel `narrate_weekly_strategy` (deterministic z-score leans) as a "descriptive read".
- Lighter alternative: keep `deep_analysis` as research commentary and delete only the Positioning clauses.
- Then:
  - `ui/macro_page.py`: Daily/Weekly report buttons at L50-51, the `report_prompt(kind)` call at L143, and the self-check at L268;
  - `tests/ficc_acceptance.py::test_report_prompt_and_deep_analysis_degrade_without_network` (L668-675).
  - `core/quant/insights.py` stays: it is narrative only and makes no trade decisions.

### 3.4 LAZYOWEN in paper_live (Phase 2, strictly after the H2 readout)

**`paper_live/config.py`** (byte-frozen)
- Remove:
  - dict `L` (L103-115, the guide's 8pp edge, half-Kelly, 6% stake, 5 positions, 3% slippage, 5pp decay exit, -40% halt);
  - `NAIVE_KAPPA` (L153) and its comment (L143-145);
  - `ACCOUNTS` rows LAZYOWEN-CAL, -NAIVE, -NAIVE-G1 and -NAIVE-G2 (L173-176);
  - `HYPOTHESES.H2_cost_gate` (L199-212) as defined. Its metric is LAZYOWEN-NAIVE-G2 minus LAZYOWEN-NAIVE.
- Keep: `WINDOW`/`START_EQUITY`, `COST_CLASS_BP`, sessions, universe and groups, the intraday logit settings, `Q` (QG-TACTICAL), `CORE` (QG-CORE), `TREND` (C3), `LOWCOST_BP`, rows QG-TACTICAL and QG-CORE, `H1_fidelity`, `H3_edge`, trials, and the KRX profile.
- Then: re-register a cost-gate hypothesis on a QG pair as a **new** freeze (Q6).

**`paper_live/engine.py`** (byte-frozen; `rule_digest` hashes the whole file)
- Remove:
  - `RULE_FAMILY['lazyowen']` (L69);
  - the lazyowen/`L`/naive-kappa branch of `trial_params` (L77-82);
  - the `p_naive = Phi(NAIVE_KAPPA*z60)` computation (about L588);
  - `Engine.step_lazyowen` (L686-746);
  - the `'lazyowen'` entry in the `Engine.step` dispatch (L864).
- Keep: snapshots, `garch_sigmas`, `ewma_sigma5`, `feature_row`, `trend_state`, `fit_logit`/`Model`, session bounds, Account/Position, `expected_move`, the cost gate (`_bp`/`_open`), `step_quantgen`, `step_trend`, `step_core`, `rule_digest`, `register_trials`.
- Then: every rule digest changes. That is expected after the readout.

**`paper_live/grid.py`**
- Remove: `GRID` rows LZNAIVE-k{0.25,0.5,1.0}-e8, LZNAIVE-k0.5-e{5,11} and LZCAL-e{2,5} (L33-37), and the `GridEngine.step_lazyowen` override (L98-104).
- Keep: the TREND-b*/h* variants, TACT-NOGATE, TREND-b5-h0.2-G1/G2, `trend_tables`, cost sensitivity and power lines.

**`paper_live/verdict.py`**
- Remove: `GATED, BASE = 'LAZYOWEN-NAIVE-G2', 'LAZYOWEN-NAIVE'` (L31). Re-target it to the new QG pair.
- Keep: `freeze`, `holdout_sessions`, `h1_fidelity`, `h3_edge`, and the paired-t / Newey-West machinery.

**`paper_live/analyze.py`**
- Remove: the `lz` filter (about L229), controls C-02 (stake <= 6%) and C-03 (<= 5 positions), and the LAZYOWEN half of C-11 (-40% halt) (L226-258).
- Keep: `usd`, `path_stats`, `bench`, `gate_stats`, `outcomes`, and the rest of `main()`.

**`paper_live/report.py`**
- Remove: `META['LAZYOWEN-CAL']` and `META['LAZYOWEN-NAIVE']` (L33-37), their `ORDER` entries (L39), and the grid base `'LZNAIVE-k0.5-e8'` (L128). Pick a QG base instead.
- Keep: `build()`, `main()` and the QG-* META.

**`paper_live/report_template.html`**
- Remove: the "QUANTGEN against the LAZYOWEN Grok bot" section (L215), the LAZYOWEN legend entries (L521), and the `#cmpTbl` "LAZYOWEN (Grok bot, Polymarket) vs QUANTGEN" table (L529).
- Keep: the rest. Reword the "LAZYOWEN's 48-hour checklist" controls header (L232).

**`paper_live/narrative.json`, `paper_live/compare_text.json`**
- Remove: the guide, Grok and Polymarket prose and the LAZYOWEN account narratives.
- Keep: the QG-TACTICAL/CORE/TREND, calibration, cost and power text. The already published Oct 7 and Oct 12 reports stay as historical artifacts. Regenerate only new ones.

**`paper_live/compare_pdf.py`**
- Remove: the LAZYOWEN-CAL and -NAIVE entries in `ACCTS`/`COL` (L26-27).

**`tests/paper_live_acceptance.py`**
- Rewrite:
  - the `_acc()` helper (`rules='lazyowen'`, used by test_02 to test_06) onto a QG rule set;
  - test_05 (gate_mult of LAZYOWEN-NAIVE/-CAL/-G1/-G2);
  - test_14 (`family_ledger('LAZYOWEN').n_raw == 4`; either drop it, or assert the frozen family still verifies);
  - test_15 with `_days_csv`/`_holdout` (columns `LAZYOWEN-NAIVE\|pnl` and `-G2\|pnl`).
- Keep: test_01, 07-13 (test_12 asserts the archived sameday shas), 16, 19, 20, test_17 (`ui.strategy_lab_page.register_trials`) and test_18 (`gate_ledger` concurrency).

`paper_live/replay.py` needs only a docstring edit (its one LAZYOWEN mention is a comment). `paper_live/run_live.py`, `calibrate.py`, `power.py` and `sameday.py` contain no LAZYOWEN code.

---

## 4. Frozen / pre-registered constraints

> **Superseded in TRADEGEN (2026-10-23).** The owner later decided that QUANTGEN keeps both frozen studies as the
> record and reads them out from its own baseline `eacd57d` (tag `studies-of-record-2026-10-23`). The plan below,
> where the GROKTEAM look runs "there", in TRADEGEN, no longer applies. TRADEGEN's `grokteam/` is permanently blinded
> and cannot re-freeze, and its `REPLAY_HOLDOUT` replay is refused. `python -m grokteam.prereg` in TRADEGEN
> therefore reports `grokteam/book.py` and `core/quant/gate_ledger.py` changed, by design. **Never** restore `grokteam/out/frozen_book` over it:
> the frozen copy would unblind the look and cache under QUANTGEN's `~/.nextgen/grokteam`.

### 4.1 GROKTEAM-BOOK pre-registration (forward look on/after 2027-02-01)

- **Record:** `grokteam/out/PREREG_book.json`, `frozen_utc` 2026-10-22T04:30:22Z.
- **Re-freeze impossible:** `prereg.freeze()` refuses once the record exists, and in any case after `FREEZE_BY` = 2026-10-25.
- **The forward look:**
  - `book.forward_gate` blinds forward events until `FORWARD_END` 2027-02-01 + 1 h.
  - The look is then taken **once** and written to `out/book/FORWARD_LOOK.json`.
  - Any difference reported by `prereg.check()` turns it into "VOID", until the files are restored from `out/frozen_book/` or the libraries are reinstalled.
- **What `prereg.check()` compares:** sha256 of the 10 files below (paths relative to `ROOT` = the parent of the `grokteam` package), plus `RULES`, `ACCOUNTS`, `VERDICT`, `model_digest()` (source of `model_at` and `_group` plus `garch.py`), and the library versions numpy 2.3.5, scipy 1.18.0, pandas 2.3.3 and Python 3.13 (major.minor).

| pinned file | sha256 prefix | other consumers in QUANTGEN | an edit or removal VOIDS |
|---|---|---|---|
| `core/quant/garch.py` | 2a8a0737 | `gjr.py` (imports private constants), `vol_estimators`, `montecarlo`, `lab`, `insights`, `crypto/analytics`, `equity_deriv`, 5 UI pages, frozen `paper_live/engine.py` | GROKTEAM look **and** model_digest. Also H2 (live sigmas), until about 2026-11-03 |
| `core/quant/forecast_eval.py` | 7c203d70 | `lab`, `docs/vol_backtest.py`, macro tests | GROKTEAM look |
| `core/quant/validate.py` | 68bc480f | about 40 importers. Frozen `paper_live/config.py` reads `cost_bp` | GROKTEAM look, and H2 if the costs change |
| `core/quant/gate_stats.py` | 3ae17e23 | `cardp`, `costed`, `forward`, `gate_ledger`, `tf_gov`. Frozen `paper_live/config.py` and `power.py` read `MDE_FACTOR` | GROKTEAM look, and H2 if `MDE_FACTOR` changes |
| `core/quant/gate_ledger.py` | 018eaa96 | `cardp`, `cards`, `tf_gov`, `ui/strategy_lab_page.py`, frozen `paper_live/engine.py` | GROKTEAM look |
| `data/crypto/crypto_client.py` | f799c510 | `history.py`, `ui/crypto_page.py`, settings | GROKTEAM look |
| `data/net.py` | 549c1af6 | `history.py`, `ficc/data.py`, KIS, KRX and OpenDART clients | GROKTEAM look |
| `grokteam/__init__.py` | 31c2a482 | none | GROKTEAM look |
| `grokteam/book.py` | b92c8af0 | none | GROKTEAM look |
| `grokteam/prereg.py` | caf55f47 | none | GROKTEAM look |

**Unpinned transitive runtime dependencies of the frozen book.** These are not hash-checked, so an edit silently changes frozen behaviour:
- `core/ficc/pit.py` (imported by `forecast_eval.py` L33);
- `core/ficc/macro_schema.py` plus `core/ficc/schemas/` (imported by `gate_ledger.py` L49);
- `core/rules/governance.py` (imported by `gate_ledger`);
- `core/rules/macro_rules.py` (imported by `forecast_eval`);
- `core/quant/risk_layer.py` and `vol_estimators.py` (lazy imports in `forecast_eval`);
- `core/ficc/contracts.py` (lazy in `pit`), `data/macro/series_registry.yaml`, `data/macro/rules_v2.0.0.json`;
- root `config.py` (`macro_dir`, `HTTP_TIMEOUT_SECONDS`, `NO_DATA_GRACE_TICKS`, `upbit_ready`, `upbit_keys`).

`grokteam/out/frozen_book/` holds no copy of any of these.

**Consequence for the split:**
- While `grokteam` runs from QUANTGEN, QUANTGEN cannot touch any of the files above until 2027-02-01.
- Once TRADEGEN holds a byte copy of the whole repo and the look is run **there**, the constraint moves to TRADEGEN's copies and QUANTGEN is freed from it. TRADEGEN must then keep those files byte-stable and the library versions pinned until the look is taken.

### 4.2 paper_live H2 cost-gate holdout (readout about 2026-11-03)

- **Records:** `paper_live/out/HYPOTHESES_frozen.json` (`frozen_utc` 2026-10-20T01:11:07Z, base profile) and `paper_live/out_krx/HYPOTHESES_frozen.json` (2026-10-20T01:11:09Z, KRX profile).
- **H2 is frozen with** "the rule digests of LAZYOWEN-NAIVE and -G2 (their settings and engine.py), the live sigmas they gate on, and byte copies of engine.py and config.py in out*/frozen_rule". Any change before the final holdout replay voids H2 unless the copies are restored.
- **Holdout sample:** the first 10 exchange sessions of each profile's anchor market after `frozen` (config L205). That gives about 2026-11-02/03. Confirm the exact last session per profile with `verdict.holdout_sessions()` before Phase 2.
- **What voids H2:**
  - any byte change to `paper_live/engine.py` or `config.py`;
  - any change to `config.HYPOTHESES` (verdict.py refuses);
  - any behaviour change in the modules the frozen engine calls at runtime: `core/quant/garch.py`, `vol_estimators.py`, `risk_layer.py` (`sma_vol`), `instruments.py` (`cost_per_side`), `validate.py` (`cost_bp`), `strategies.py` (`crypto_trend`), `gate_stats.py` (`MDE_FACTOR`), `gate_ledger.py`, `core/markets.py`, `core/calendars/__init__.py`, and root `config.py` (`macro_dir`).
- **Do not run** `paper_live.replay`, `grid`, `verdict` or `sameday` except for the holdout readout itself. They write into `out*/`.
- **Removing LAZYOWEN removes QUANTGEN's only confirmatory cost-gate test,** because H2 is defined on the LAZYOWEN pair. It must be re-registered on a QG pair as a new freeze, tested only on sessions after that freeze.

### 4.3 test_s4 insert-only rule (permanent, while `_backup/QUANTGEN_pre_v2_2026-10-05.zip` exists, which it does)

`tests/macro_m5_integration.py::test_s4_rulings_no_wall_clock_nothing_above_one_halted_outside_min_engine_untouched` (L326-354, ids T-RO-01, T-CAP-02) has three clauses:
- **`UNTOUCHED`:** `core/engine/state.py`, `runtime.py`, `feed.py` and `__init__.py` must stay **byte-identical** to the pre-v2 backup.
- **`ADD_ONLY`:** `core/engine/orders.py`, `core/engine/evaluator.py` and `ui/trading_page.py` may only **gain lines** versus the backup. The single allowed replace is widening a `from datetime import` line.
- **`S4_MODULES`:** books, orders, evaluator, events, annotations, context_log, macro_artifacts and risk_layer may not add new wall-clock calls.

Consequences:
- No split step may delete or alter a line in those files. None of them is non-quant, so the plan above does not touch them.
- Moving the operator rule engine out of QUANTGEN (Q2) would require rewriting T-RO-01/T-CAP-02 first.
- TRADEGEN inherits the same test, the backup zip and the rule. If TRADEGEN later wants to rework its engine, that test is TRADEGEN's to retire.

### 4.4 Other standing constraints

- **Append-only hash-chained logs:** gate-ledger family files in `~/.nextgen/macro/ledgers/*.jsonl` and `governance_events.jsonl`. Never delete or rewrite rows. `tf_gov` derives global N from every family file in the directory.
- **Byte-equality tests** (`tests/macro_tf_data.py`): `reports/QUANTGEN macro overlay research.md`, `reports/QUANTGEN_Quant_Council_Report.md` and `docs/council/*` must equal their sources in `QUANTGEN_Quant_Council_2026-10-03/`. Do not move or edit either side.
- **sha256-manifested research tables:** `data/techfund/MANIFEST.json` (`core/techfund.py`). The split leaves these untouched.
- **Macro gate package:** `core/quant/gate_package.py` is NOT_FROZEN today, so there is no deadline. Freezing it later fixes the harness definitions.

### 4.5 Safe ordering

| phase | when | what | constraint honoured |
|---|---|---|---|
| **0. Copy** | now, before any QUANTGEN edit | Copy the **entire** repo byte-for-byte, including `_backup/`, `grokteam/out/` and `paper_live/out*/`, to `C:/Users/whydi/OneDrive/Desktop/TRADEGEN`. Create a TRADEGEN Python env with numpy 2.3.5, scipy 1.18.0, pandas 2.3.3 and Python 3.13. In TRADEGEN run `python -m grokteam.prereg` (check): it must report no changes. Give TRADEGEN its own state dirs in its `.env` (`QUANTGEN_MACRO_DIR`, `NEXTGEN_TRADING_DIR`, `NEXTGEN_RUNS_DIR`, `GROKTEAM_DATA` optional) and copy `GROKTEAM-BOOK.jsonl` and `LAZYOWEN.jsonl` whole into TRADEGEN's ledger dir | 4.1 (look now runnable from TRADEGEN), 4.3 (zip copied) |
| **1. Remove guide-bot code and cockpit** | now, after Phase 0 passes | QUANTGEN: delete `grokteam/` plus run_all.py L49/65/111 plus README L763/785/786 in one change. Move the grokteam note (3.1). If Q1/Q3/Q4 say move, do the cockpit removal (3.2) and the regime_score and LLM-prompt edits (3.3). Run the suites | Touches no pinned file in TRADEGEN, no `paper_live` file, and no UNTOUCHED/ADD_ONLY file. `config.py` names used by frozen code are kept |
| **1b. Hold** | until the H2 readout | QUANTGEN must still not change the numerics or signatures of garch, vol_estimators, risk_layer, instruments, validate (`cost_bp`), strategies (`crypto_trend`), gate_stats, gate_ledger, markets or calendars | 4.2 |
| **2. Remove LAZYOWEN** | after the holdout replay and `verdict.json` exist for **both** profiles (about 2026-11-03 or later) | Apply 3.4. Re-register a cost-gate hypothesis on a QG pair with a new `verdict --freeze`. Leave the LAZYOWEN ledger rows in place | 4.2 discharged |
| **3. Free** | after Phase 2 | QUANTGEN core is now free to evolve: TRADEGEN owns the GROKTEAM pins. Only 4.3 and 4.4 remain. TRADEGEN keeps its 10 pinned files untouched until its look on/after 2027-02-01 | 4.1 lives in TRADEGEN |

---

## 5. Stays in QUANTGEN

**FICC**
- Curves and term structure: `core/ficc/curves.py`, `curve_models.py`.
- Bonds: `bonds.py`.
- Swaps and rates options: `swaps.py`.
- Short-rate models: `ratesim.py`.
- FX derivatives: `fx.py`.
- FX styles: `fx_styles.py`.
- Structured products: `structured.py`.
- Equity-index derivatives: `equity_deriv.py`.
- VIX and the volatility risk premium: `vol_products.py`.
- Macro sheet: `macro.py`.
- Macro and recession indicators, change points: `context_log.py`.
- FICC infrastructure: `common.py`, `data.py`, `__init__.py`.
- Narratives: `insights.py` minus the LLM "Positioning" prompts.
- UI: `ui/rates_page.py`, `bonds_page.py`, `fx_page.py`, `structuring_page.py`, `derivatives_page.py`, `macro_page.py`, `fcharts.py`, `xcharts.py`.

**Equity, crypto and portfolio quant**
- Simulation: `core/quant/montecarlo.py`.
- Optimisation: `optimize.py`.
- Risk statistics: `risk.py`.
- Tail risk and self-grading: `lab.py`.
- Stress scenarios: `scenarios.py`.
- Systematic strategy families: `strategies.py`.
- Factor sleeves: `sleeves.py`.
- Technical indicators, context only: `signals.py`.
- Rule backtests: `backtest.py`.
- KRX factor screens and books: `tf_screens.py`, `tf_books.py`.
- Volatility models: `garch.py`, `gjr.py`, `vol_estimators.py`.
- Crypto econometrics: `core/crypto/analytics.py` minus `regime_score`.
- UI: `ui/quant_lab_page.py`, `portfolio_page.py`, `signals_page.py`, `etf_page.py`, `crypto_page.py`, `qcharts.py`.

**Validation and gates**
- Validation gate: `core/quant/validate.py`.
- Gate statistics: `gate_stats.py`.
- Trial ledger: `gate_ledger.py`.
- Gate package: `gate_package.py`.
- CARD-P: `cardp.py`.
- Card registry: `cards.py`.
- Card lines: `card_lines.py`.
- Costed engine: `costed.py`.
- Forecast evaluation: `forecast_eval.py`.
- Forward monitoring: `forward.py`.
- Governance: `tf_gov.py`.
- Refusal books: `refusal.py`.
- UI: `ui/strategy_lab_page.py`, `macro_cards_view.py`, `research_view.py`.
- Studies: `docs/asset_expansion_study.py`, `macro_overlay_study.py`, `techfund_study.py`, `quant_lab_grading.py`, `vol_backtest.py`, `drift_study.py`, `bounded_innovation_sweep.py`, `verify_drift_check.py`, `b1_evidence/`, `b2_evidence/`.

**Macro overlay**
- Pipeline: `core/skills/macro_daily.py`, `pipeline.py`, `alerts.py`, `macro_workflows/macro_daily.yaml`.
- Rules and governance: `core/rules/macro_rules.py`, `governance.py`, `backlog_registry.py`, `validation.py`.
- Calendars: `core/calendars/*`.
- PIT and artifact layer: `core/ficc/pit.py`, `contracts.py`, `lag_audit.py`, `macro_schema.py`, `macro_artifacts.py`, `annotations.py`, `flows_log.py`, `schemas/`.
- Risk layer: `core/quant/risk_layer.py`.
- Forward-sim books: `forward_sim.py`.
- Parameters: `data/macro/*`.
- UI: `ui/macro_state_panel.py`.
- Spec: `QUANTGEN_Quant_Council_2026-10-03/`.

**Paper trading**
- Simulated operator engine: `core/engine/*` (state, runtime, feed, evaluator, orders, books).
- Operator rules: `core/rules/model.py`, `store.py`, `__init__.py`.
- UI: `ui/rules_page.py`, `trading_page.py`.
- `paper_live/` minus LAZYOWEN: `run_live`, `engine`, `config`, `calibrate`, `replay`, `sameday`, `grid`, `power`, `verdict`, `analyze`, `report`, `compare_pdf`, accounts QG-TACTICAL, QG-CORE, QG-TREND.

**Infrastructure**
- Config: `config.py` minus the skills section; `.env.example` minus skill keys.
- Shell: `main.py` minus the cockpit.
- Data clients: `data/net.py`, `data/kis_markets.py`, `data/crypto/*`, `data/fmp/*`, `data/krx/*`.
- Market and formatting helpers: `core/markets.py`, `numfmt.py`, `theme.py`, `techfund.py`.
- Data and analytics adapters: `core/quant/history.py`, `gsq.py`, `insights.py`, `instruments.py`.
- UI kit: `ui/components.py`, `ai_panel.py`, `krx_page.py`, `settings_page.py` minus skills.
- Tests: `tests/*` harness (run_all minus grokteam, macro_*, quant, ficc, expansion, engine, flet_api_guard, notrun, golden_tools, reference/, fixtures/, the safety half of acceptance.py).
- Build: `pyproject.toml`, `requirements*.txt`, `.claude/launch.json` (quantgen-web), `.claude/run_web.py`.

**Research record**
- `docs/*.md` and primers, `reports/*`, `research_notes/QUANTGEN asset coverage expansion/*`, `research_notes/QUANTGEN v2 integration map/*`, `research_notes/QUANTGEN technical and fundamental signals/`, `QUANTGEN_techfund_research_bundle/*`.
- Prediction-market legal sections (`other_assets.md` section 6, asset-coverage report L102/L184): **copy** to TRADEGEN, do not move.

---

## 6. Quant-topic inventory

This table seeds the formal-research-paper pipeline. A **[?]** marks a citation detail (venue, volume, number or attribution) not verified against the paper; check it before a paper cites it. "Cited in code" means the module's own docstring names the source. Otherwise the reference is the canonical source for the method.

| # | topic | files | models / methods | canonical academic basis | evidence in repo |
|---|---|---|---|---|---|
| 1 | GARCH(1,1) with Student-t innovations: MLE, guardrails, inference | `core/quant/garch.py`, `ui/quant_lab_page.py`, `docs/B1_FIX_BULLETIN.md`, `docs/B2_FIX_BULLETIN.md`, `docs/LR_formula.tex`, `docs/b1_evidence/`, `docs/b2_evidence/` | L-BFGS-B MLE on (omega, alpha, beta, eta=1/nu) with stationarity penalty and bound reporting; numerical-Hessian Wald SEs; delta-method persistence SE; profile-likelihood CI for nu; boundary LR t-vs-normal (50:50 chi-bar-square, 5% line 2.706); multi-step variance forecast | Engle (1982) Econometrica 50(4); Bollerslev (1986) J. Econometrics 31(3); Bollerslev (1987) REStat 69(3); Self & Liang (1987) JASA 82(398) (cited in code) | B1 (LR never negative), B2 coverage study (delta-method unconditional-vol CI covers 42-100%, so dropped); `tests/quant_acceptance.py` (GARCH recovery, LR null size); SPY and KODEX 200 left-tail under-coverage in `docs/asset_expansion/results.md` |
| 2 | Asymmetric volatility: GJR-GARCH with Hansen skewed-t | `core/quant/gjr.py`, `vol_estimators.py`, `docs/build_expansion_primer.py` | Threshold term on negative shocks, persistence alpha+beta+gamma/2; Student-t and Hansen skew-t innovations; OOS challenger to symmetric GARCH-t | Glosten, Jagannathan & Runkle (1993) J. Finance 48(5); Hansen (1994) IER 35(3) | D_* cards: GJR leaves breach counts unchanged, skew-t fixes them (REVISE on PIT only); `tests/macro_m3_estimators.py` |
| 3 | Bounded-t innovations and the exact martingale (drift) correction | `core/quant/garch.py`, `montecarlo.py`, `docs/bounded_innovation_sweep.py`, `docs/verify_drift_check.py` | c_A(sigma) = ln E[exp(sigma z) given abs(z) <= A], truncated-t redraw, choice of Z_BOUND; risk-neutral vs premium drift | Duan (1995) Mathematical Finance 5(1) (GARCH option pricing, LRNVR) | `docs/bounded_innovation_sweep.md` (952 paired simulations, 50k paths each) |
| 4 | Volatility estimator race | `core/quant/vol_estimators.py`, `risk_layer.py`, `optimize.py`, `paper_live/engine.py` (`ewma_sigma5`) | SMA20; EWMA lambda 0.94/0.97; GARCH-t; GJR-t; log-HAR on range variance (Garman-Klass plus overnight for KR, Parkinson for US); forecast combination; fail-closed `sigma_for_decision` | J.P. Morgan/Reuters RiskMetrics Technical Document (1996); Corsi (2009) J. Financial Econometrics 7(2); Parkinson (1980) J. Business 53(1); Garman & Klass (1980) J. Business 53(1) | `docs/vol_backtest/results.csv` (B5 rerun SPY / KODEX 200); `tests/macro_m3_estimators.py` |
| 5 | Volatility forecast comparison | `core/quant/forecast_eval.py`, `docs/vol_backtest.py` | QLIKE/MSE/tick loss; Diebold-Mariano with HLN correction and Bartlett HAC; Clark-West; Giacomini-White; Model Confidence Set (T_max, stationary bootstrap); staged estimator gate | Patton (2011) J. Econometrics 160(1); Diebold & Mariano (1995) JBES 13(3); Harvey, Leybourne & Newbold (1997) IJF 13(2); Clark & West (2007) J. Econometrics 138(1); Giacomini & White (2006) Econometrica 74(6); Hansen, Lunde & Nason (2011) Econometrica 79(2) | `tests/macro_m3_estimators.py`, `macro_m9_lab.py` |
| 6 | VaR / ES and density-forecast backtesting | `core/quant/forecast_eval.py`, `validate.py`, `lab.py`, `docs/quant_lab_grading.py` | Kupiec POF; Christoffersen independence and CC; Basel 250-day traffic light; PIT KS/chi2; Berkowitz LR; DGT correlograms; CRPS from samples; Acerbi-Szekely Z2 ES test; reliability table | Kupiec (1995) J. Derivatives 3(2); Christoffersen (1998) IER 39(4); Basel Committee (1996) backtesting framework; Diebold, Gunther & Tay (1998) IER 39(4); Berkowitz (2001) JBES 19(4); Gneiting & Raftery (2007) JASA 102(477); Acerbi & Szekely (2014) Risk (Dec.) | `docs/quant_lab/*.json` (SMOKE; formal run refuses until KRX official closes F01 exist); `tests/macro_m9_lab.py` |
| 7 | Tail risk: filtered historical simulation and EVT | `core/quant/lab.py` | FHS VaR/ES on the standardised-residual pool; GJR-t plus GPD ML on the top 10% of losses; max envelope | Barone-Adesi, Giannopoulos & Vosper (1999) J. Futures Markets 19(5); McNeil & Frey (2000) J. Empirical Finance 7(3-4) (cited in code) | `tests/macro_m9_lab.py` (M9 gate 2016-26) |
| 8 | Monte Carlo price paths and risk fans | `core/quant/montecarlo.py`, `ui/quant_lab_page.py`, `ui/qcharts.py` | GBM; Merton jump-diffusion (jumps from a 3-sigma split); stationary block bootstrap; GARCH-t paths; VaR/CVaR fans; drift modes premium/rf/zero/sample | Black & Scholes (1973) JPE 81(3); Merton (1976) JFE 3(1-2); Kunsch (1989) Ann. Statist. 17(3); Politis & Romano (1994) JASA 89(428); Rockafellar & Uryasev (2000) J. Risk 2(3) | `tests/quant_acceptance.py`; `docs/QUANTGEN_Models_Primer.pdf` |
| 9 | Out-of-sample expected-return (drift) estimation | `docs/drift_study.py`, `docs/drift_study/` | Trailing mean vs shrinkage vs zero drift, RMSE by horizon | Merton (1980) JFE 8(4); Goyal & Welch (2008) RFS 21(4) | 17 instruments 2005-2026: correlation -0.01, zero drift wins at every horizon |
| 10 | Intraday-seasonal GARCH-t and fat-tailed digital-option probability (port from `grokteam/book.py`, Q9) | `grokteam/book.py` (`_group`, `model_at`, `p_above`), to be re-implemented | Hour-of-day x weekend RMS de-seasonalisation (48 groups), 2,000-bar hourly GARCH-t, aggregated multi-step variance; P(S_T>K) = t_nu.sf(log(K/S)/(sigma sqrt((nu-2)/nu))) | Andersen & Bollerslev (1997) J. Empirical Finance 4(2-3); Black & Scholes (1973); Reiner & Rubinstein (1991) "Unscrambling the binary code", Risk 4 [?]; Praetz (1972) J. Business 45(1); Blattberg & Gonedes (1974) J. Business 47(2) | grokteam selfcheck `test_digital_probability`, `test_model_sees_only_closed_bars`; PREREG "model" text (persistence 0.9967-0.9995 within 0.93-1.06x sigma) |
| 11 | Strategy validation gate | `core/quant/validate.py`, `docs/asset_expansion_study.py`, `research_notes/QUANTGEN asset coverage expansion/validation_methodology.md` | Purged walk-forward IS 756 / OOS 126 with embargo; Lo SE; studentised circular block-bootstrap 90% CI; paired Sharpe-difference bootstrap vs benchmark; plateau share; regime split; 2x-cost survival | Lopez de Prado (2018) Advances in Financial Machine Learning, Wiley (ch. 7, 11-14); Lo (2002) FAJ 58(4); McLean & Pontiff (2016) J. Finance 71(1) | Run of record 2026-09-27 seed 11: 5 PASS / 11 REVISE / 18 REJECT (`docs/asset_expansion/results.md`, 34 cards); `tests/expansion_acceptance.py` |
| 12 | Block-bootstrap inference for Sharpe ratios | `core/quant/gate_stats.py`, `costed.py`, `cardp.py` | Politis-White automatic block length; circular and stationary resampling; Ledoit-Wolf influence-function HAC SE of dSR plus studentised bootstrap; QS/Bartlett long-run variance; paired circular 63-day research bootstrap | Politis & Romano (1994) JASA 89(428); Politis & White (2004) Econometric Reviews 23(1), corrected by Patton, Politis & White (2009) Econometric Reviews 28(4); Ledoit & Wolf (2008) J. Empirical Finance 15(5); Andrews (1991) Econometrica 59(3) | Verified against `arch` 8.0.0 to 1e-9 (module docstring); `tests/macro_m7_stats.py`, `macro_m2_costed.py` |
| 13 | Backtest overfitting and multiple testing | `core/quant/gate_stats.py`, `validate.py`, `tf_gov.py`, `grokteam/book.py` (Holm) | PSR; DSR (expected max Sharpe over all trials); PBO by CSCV; Harvey-Liu haircut; Benjamini-Yekutieli q; Benjamini-Hochberg FDR; Holm step-down; Lo autocorrelation-adjusted Sharpe; McLean-Pontiff decay haircut | Bailey & Lopez de Prado (2012) J. Risk 15(2) (PSR); Bailey & Lopez de Prado (2014) J. Portfolio Mgmt 40(5) (DSR); Bailey, Borwein, Lopez de Prado & Zhu (2017) J. Computational Finance 20(4) (PBO); Harvey & Liu (2015) J. Portfolio Mgmt 42(1); Harvey, Liu & Zhu (2016) RFS 29(1); Benjamini & Hochberg (1995) JRSS-B 57(1); Benjamini & Yekutieli (2001) Ann. Statist. 29(4); Holm (1979) Scand. J. Statist. 6(2) | `tests/macro_m7_stats.py`; `ui/strategy_lab_page.py` scorecard; harness defects fixed (edge on 2-value grids, PBO alone rejecting flat plateaus) |
| 14 | Data-snooping tests | `core/quant/tf_gov.py`, techfund `scripts/r2_idx_*` | White Reality Check; Hansen SPA (studentised, stationary bootstrap); factor attribution with NW t; minimum track record | White (2000) Econometrica 68(5); Hansen (2005) JBES 23(4); Bailey & Lopez de Prado (2012) J. Risk 15(2) (MinTRL) | `tests/macro_tf_gov.py`; `kr_index_spa.csv` (techfund datalab) |
| 15 | Trial ledger, N_eff and pre-registration governance | `core/quant/gate_ledger.py`, `cards.py`, `gate_package.py`, `core/rules/governance.py`, `paper_live/verdict.py`, `grokteam/prereg.py` | Hash-chained per-family trial ledger; N_eff = max(N_clusters, N_equiv) by hierarchical clustering of difference series; step-3 selection factor; blind header commits; frozen definitions manifest; frozen hypotheses with one-look holdouts | Harvey (2017) J. Finance 72(4) (presidential address); Bailey, Borwein, Lopez de Prado & Zhu (2014) Notices AMS 61(5); Nosek et al. (2018) PNAS 115(11); Lopez de Prado (2018) AFML | `tests/macro_m7_ledger.py`, `macro_m7_cards.py`; `paper_live/out*/HYPOTHESES_frozen.json`; `grokteam/out/PREREG_book.json` |
| 16 | Statistical power, MDE and HAC t-tests | `core/quant/gate_stats.py` (`MDE_FACTOR`), `paper_live/power.py`, `verdict.py` | MDE = (z_0.90 + z_0.80) SE = 2.1232 SE (one-sided alpha 0.10, 80% power); iid and Newey-West (lag 5) t; paired one-sided t; sessions needed (about 1,136 for annual SR 1) | Cohen (1988) Statistical Power Analysis, 2nd ed.; Bloom (1995) Evaluation Review 19(5); Newey & West (1987) Econometrica 55(3) | `paper_live/out*/power.json`; `tests/macro_m7_stats.py` |
| 17 | Sequential monitoring and change-point detection | `core/quant/forward.py`, `core/ficc/context_log.py` | One-sided CUSUM (k=0.25, bootstrap-calibrated h for ARL >= 20 y), catastrophic dMDD/dES/dSR bounds, circular placebo false-alarm budget; two-sided tabular CUSUM; Bayesian online change-point (hazard 1/250, Inverse-Gamma) | Page (1954) Biometrika 41(1/2); Adams & MacKay (2007) arXiv:0710.3742 (cited in code) | `tests/macro_m8_forward.py`, `macro_m6_context.py` (EX1 false-break test 1990-2026) |
| 18 | Probability models, calibration and proper scoring | `paper_live/engine.py` (`fit_logit`), `paper_live/calibrate.py`, `grokteam/book.py` (`fit_calibration`, `skill`) | Newton/IRLS L2 logistic by asset group (intercept dropped per drift study); OOS AUC; Brier vs 0.25; logistic recalibration p = expit(a + b logit p_raw); log loss; reliability tables | Cox (1958) JRSS-B 20(2) and Biometrika 45 (calibration); le Cessie & van Houwelingen (1992) Applied Statistics 41(1); Platt (1999) in Advances in Large Margin Classifiers; Hanley & McNeil (1982) Radiology 143(1); Brier (1950) Monthly Weather Review 78(1); Murphy & Winkler (1977) Applied Statistics 26(1); Gneiting & Raftery (2007) | `paper_live/out*/calibration.json` (OOS AUC 0.50-0.53); PREREG calibration a=-0.0237, b=0.9805, n=77,429 |
| 19 | Cluster-robust inference over calendar blocks (port, Q9) | `grokteam/book.py` (`block_t`) | CR1 cluster SE over 5-day UTC blocks, t(G-1) p and 90% CI; paired block means vs nulls | Liang & Zeger (1986) Biometrika 73(1); Cameron, Gelbach & Miller (2008) REStat 90(3); Cameron & Miller (2015) J. Human Resources 50(2) | grokteam selfcheck `test_block_t` |
| 20 | Backtest-vs-live fidelity (simulator implementation shortfall) | `paper_live/sameday.py`, `replay.py`, `verdict.py` (`h1_fidelity`) | Same-day replay with archived, sha-checked code; feed-delay re-stamping; gap <= max(0.5 x replay session sd, $0.25) | Perold (1988) J. Portfolio Mgmt 14(3) | `paper_live/out*/replay_sameday/summary.json`, `verdict.json` |
| 21 | Point-in-time data and publication-lag modelling | `core/ficc/pit.py`, `contracts.py`, `lag_audit.py`, `core/calendars/publication.py`, `clocks.py`, `data/macro/series_registry.yaml` | As-of reads with vintages; close+10 min quarantine; usable_at rules (H.15, H.10, BLS 08:30, FRED, ECOS); schedule-aware staleness; independent lag audit; positional-shift linter | Croushore & Stark (2001) J. Econometrics 105(1); Bailey, Borwein, Lopez de Prado & Zhu (2014) Notices AMS 61(5); Lopez de Prado (2018) AFML | `tests/macro_m1_pit.py`, `macro_m1_integration.py`, `macro_m1_calendars.py` |
| 22 | Portfolio optimisation | `core/quant/optimize.py`, `sleeves.py`, `strategies.py` (`risk_parity`), `ui/portfolio_page.py` | Markowitz frontier, max-Sharpe, min-vol (SLSQP, long-only capped); ERC risk parity; EWMA inverse-vol; Ledoit-Wolf constant-correlation shrinkage | Markowitz (1952) J. Finance 7(1); Sharpe (1966) J. Business 39(1); Maillard, Roncalli & Teiletche (2010) J. Portfolio Mgmt 36(4); Ledoit & Wolf (2004) J. Portfolio Mgmt 30(4) | S_E3 risk-parity card REJECT; `tests/macro_m4_sleeves.py`, `quant_acceptance.py` |
| 23 | Volatility targeting / volatility-managed portfolios | `core/quant/risk_layer.py`, `forward_sim.py` (R-29), `core/skills/macro_daily.py` (R-06), `paper_live/engine.py` (QG-CORE, QG-TACTICAL), `data/macro/rules_v2.0.0.json` | w = min(cap, target / sigma_hat) with SMA20/EWMA sigma; min() composition of multipliers; robustness grid on window and target | Moreira & Muir (2017) J. Finance 72(4); Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018) J. Portfolio Mgmt 45(1); Cederburg, O'Doherty, Wang & Yan (2020) JFE 138(1) | Capped vol target REJECT on SPY/KODEX at study costs; macro cards NOT RUN (package not frozen); `tests/macro_m2_risk.py` |
| 24 | Drawdown control | `core/engine/books.py`, `core/quant/risk_layer.py` (R-31), `data/macro/rules_v2.0.0.json` (D2, cdar_guard) | -15% whole-book hard stop; step-down exposure ladder with re-arm cap and dwell; CDaR acceptance guard | Grossman & Zhou (1993) Mathematical Finance 3(3); Chekhlov, Uryasev & Zabarankin (2005) IJTAF 8(1) | `tests/macro_m1_books.py`, `macro_m5_books.py`; R-31 card |
| 25 | Trend following | `core/quant/strategies.py` (`trend_switch`, `tsmom`, `crypto_trend`), `forward_sim.py` (R-28), `paper_live/engine.py` (`trend_state`) | 10-month SMA switch; TSMOM sign(12m) x 40%/sigma; crypto short-horizon vote with hysteresis | Faber (2007) J. Wealth Mgmt 9(4); Moskowitz, Ooi & Pedersen (2012) JFE 104(2); Hurst, Ooi & Pedersen (2017) J. Portfolio Mgmt 44(1); Liu & Tsyvinski (2021) RFS 34(6) | S_C3 crypto_trend PASS (SR_OOS 1.19/1.22; KRW-BTC p 0.038); CRY-1 controls REJECT (Binance after 2024-01-10 split, ETH replication); futures TSMOM REJECT |
| 26 | Cross-sectional momentum, vol-scaled momentum and the crash gate | `core/quant/strategies.py` (`xs_momentum`), `sleeves.py` (R-03/R-04), techfund `scripts/r2_kr_05_crash_controls.py` | 12-1 ranks; sleeve vol scale; crash-state gate; inverse-vol sleeve weights | Jegadeesh & Titman (1993) J. Finance 48(1); Barroso & Santa-Clara (2015) JFE 116(1); Daniel & Moskowitz (2016) JFE 122(2) | Sector momentum REJECT; `tests/macro_m4_sleeves.py` |
| 27 | Pairs trading and statistical arbitrage | `core/quant/strategies.py` (`pairs`), `core/ficc/curve_models.py` (fly ADF) | Engle-Granger spread, ADF, OU half-life, z entry/exit | Gatev, Goetzmann & Rouwenhorst (2006) RFS 19(3); Engle & Granger (1987) Econometrica 55(2); Dickey & Fuller (1979) JASA 74(366); Avellaneda & Lee (2010) Quantitative Finance 10(7) | Gold pair and Hyundai/Kia fail DSR; KODEX/TIGER REVISE (bid-ask bounce); ETH/BTC REJECT |
| 28 | Factor sleeves with Diebold-Mariano gating | `core/quant/sleeves.py` | Sleeve vol scale, DM gate on the specification book, R-15 admissibility, K/(K-1) re-weight | Asness, Moskowitz & Pedersen (2013) J. Finance 68(3); Diebold & Mariano (1995) | `tests/macro_m4_sleeves.py`, `macro_m4_integration.py` |
| 29 | KRX cross-sectional factors, capacity and costs | `core/quant/tf_screens.py`, `tf_books.py`, techfund `scripts/kr_*.py` | Quantile groups; MAX/lottery F1..F8 composite; net issuance; limit-lock mask; band selection; turnover cap; ADV capacity; break-even cost; NW IR | Bali, Cakici & Whitelaw (2011) JFE 99(2); Pontiff & Woodgate (2008) J. Finance 63(2); Fama & French (1993) JFE 33(1); Fama & French (2015) JFE 116(1); Novy-Marx & Velikov (2016) RFS 29(1) | R3 go/no-go register G-01..G-77; every KRX techfund card NOT RUN (panel absent); `tests/macro_tf_screens.py` |
| 30 | Technical trading rules with costed backtest (context only) | `core/quant/signals.py`, `backtest.py`, `ui/signals_page.py` | SMA/EMA/RSI/MACD scores and a fixed-weight composite (weights hand-set, not estimated); MA-cross and RSI-revert backtest at t+1 with costs vs buy-and-hold | Brock, Lakonishok & LeBaron (1992) J. Finance 47(5); Wilder (1978) New Concepts in Technical Trading Systems; Appel, MACD (Technical Analysis: Power Tools for Active Investors, 2005) [?] | README "context only"; DO-NOT-BUILD TF-12; techfund P7 audit finds most retail indicators unsupported |
| 31 | Transaction-cost modelling and the expected-move cost gate | `core/quant/instruments.py`, `validate.py` (`COST_BP_PER_SIDE`), `costed.py`, `card_lines.py`, `paper_live/engine.py` (`expected_move`, `_open`) | Per-side cost table; tick-size floor; KRX sell tax; 2x-cost stress; gate abs(2p-1) sigma_h sqrt(2/pi) > k x round-trip cost; execution variants A/B/C; overnight/intraday attribution; roll and basis | Roll (1984) J. Finance 39(4); Perold (1988) J. Portfolio Mgmt 14(3); Almgren & Chriss (2000) J. Risk 3(2); Novy-Marx & Velikov (2016) RFS 29(1); Kaminski & Lo (2014) J. Financial Markets 18 (stop-rule persistence) | `tests/macro_m0_instruments.py`; H2 counterfactual NAIVE -$5.66 to -$0.07/session (narrative.json); grid cost sensitivity |
| 32 | Execution and fill modelling | `core/engine/orders.py` (`FillModel`, `simulate_fill`, `limit_lock`, `inav_check`, `fill_tracking_error`), `core/calendars/regime.py` | Official close or closing-auction fills; KRX price-limit lock makes a bar non-fillable; ETF iNAV residual flag at 30 bp; bar-derived closes refused | Madhavan (2000) J. Financial Markets 3(3); Kim & Rhee (1997) J. Finance 52(2) | `tests/macro_m5_fills_events.py`, `macro_m0_harness.py` |
| 33 | Event windows and the VIX term-structure annotation | `core/calendars/events.py`, `core/engine/evaluator.py`, `core/ficc/annotations.py` | Scheduled-release windows block new entries (R-10); VIX >= VIX3M display annotation, no weight change (R-08) | Lucca & Moench (2015) J. Finance 70(1); Whaley (2000) J. Portfolio Mgmt 26(3); Johnson (2017) JFQA 52(6) | G-R08-02 CARD-P REJECT on file (10 of 10 cells); `tests/macro_m5_integration.py` |
| 34 | Korean market-structure regimes and structural breaks | `core/calendars/regime.py`, `core/calendars/data/kr_regime_tags.yaml` | Dated tags: +/-30% limit (2015-06-15), short-sale regimes, closing call, random end, sell tax, value-up (2024-02-26) | Andrews (1993) Econometrica 61(4); KRX/FSC regulatory notices | `tests/macro_m1_calendars.py` |
| 35 | Leveraged-ETF volatility drag | `core/quant/lab.py` (`letf_path_return`), `core/ficc/equity_deriv.py` (`letf_drag`), `ui/etf_page.py` | L R - L(L-1)/2 sum r^2 + carry, at realised and GARCH variance | Cheng & Madhavan (2009) J. Investment Mgmt 7(4); Avellaneda & Zhang (2010) SIAM J. Financial Math. 1(1) (cited in code) | M_E4 card REVISE; drag offered as a monitor |
| 36 | Stress scenarios | `core/quant/scenarios.py` | Seeded historical shock-window replays of factor series and books; SEP rate bands via short-rate paths | Historical stress testing practice (BCBS); short-rate sources as in #43 | `tests/macro_m9_scenarios.py` |
| 37 | Yield-curve construction | `core/ficc/curves.py` | Par bootstrap with log-linear DF interpolation; Nelson-Siegel and Svensson LS fits; 2s10s/5s30s/fly descriptors; steepener/flattener regime | Nelson & Siegel (1987) J. Business 60(4); Svensson (1994) NBER WP 4871 | `tests/ficc_acceptance.py` |
| 38 | Curve PCA and PCA-neutral butterfly | `core/ficc/curves.py`, `curve_models.py` | Eigen-decomposition of curve changes; 2s5s10s fly with zero PC1/PC2 loading; z entry abs(z)>2, exit at 0 or 60 sessions | Litterman & Scheinkman (1991) J. Fixed Income 1(1) (cited in code) | PCA fly offered as a monitor; `tests/expansion_acceptance.py` |
| 39 | Dynamic Nelson-Siegel forecasting | `core/ficc/curve_models.py` | Daily OLS betas with lambda 0.0609/month; direct-h AR(1); recursive OOS forecasts h=6,12 vs random walk; DM with NW | Diebold & Li (2006) J. Econometrics 130(2) (cited in code) | Card REJECT: 0 of 5 maturities beat the random walk |
| 40 | Bond carry and roll-down | `core/ficc/curve_models.py`, `bonds.py` | carry = (y_T - r_short) + D_mod (y_T - y_{T-h}); bond-level carry and roll repricing | Koijen, Moskowitz, Pedersen & Vrugt (2018) "Carry", JFE 127(2), eq. 15 (cited in code) | `tests/expansion_acceptance.py`, `ficc_acceptance.py` |
| 41 | Bond risk analytics | `core/ficc/bonds.py`, `ui/bonds_page.py` | Price/yield (Brent); Macaulay and modified duration; convexity; DV01; key-rate DV01 via triangular bumps; z-spread; parallel/twist scenarios; futures DV01 hedge | Macaulay (1938) NBER; Ho (1992) J. Fixed Income 2(2); Tuckman & Serrat, Fixed Income Securities (textbook) | `tests/ficc_acceptance.py` |
| 42 | Swaps, swaptions, caps and floors | `core/ficc/swaps.py`, `ui/rates_page.py` | Single-curve IRS par/PV/DV01/KRD; forward-swap grid; Black-76 and Bachelier pricers per annuity; implied-vol inversion and conversion; caplet strips; ATM straddle | Black (1976) JFE 3(1-2); Bachelier (1900) Theorie de la speculation; Brigo & Mercurio (2006) Interest Rate Models (textbook) | `tests/ficc_acceptance.py` |
| 43 | Short-rate term-structure models | `core/ficc/ratesim.py`, `core/quant/scenarios.py` | Vasicek, CIR (full-truncation Euler), Hull-White theta(t) from the initial curve; OLS calibration; closed-form ZCBs; horizon P&L distributions; SEP band sigma | Vasicek (1977) JFE 5(2); Cox, Ingersoll & Ross (1985) Econometrica 53(2); Hull & White (1990) RFS 3(4) | `tests/ficc_acceptance.py`, `macro_m9_scenarios.py` |
| 44 | FX forwards, options and smiles | `core/ficc/fx.py`, `ui/fx_page.py` | CIP forwards, points and implied basis; Garman-Kohlhagen price and Greeks (incl. vanna, volga); delta-to-strike; ATM/RR/BF smile; SABR lognormal expansion with beta fixed | Garman & Kohlhagen (1983) JIMF 2(3); Hagan, Kumar, Lesniewski & Woodward (2002) Wilmott Magazine (Sept.) (cited in code); Du, Tepper & Verdelhan (2018) J. Finance 73(3) | `tests/ficc_acceptance.py` |
| 45 | FX carry, momentum, dollar carry, forward-premium puzzle | `core/ficc/fx.py` (carry backtest), `fx_styles.py` | No-lookahead G10+KRW carry basket; cross-sectional momentum terciles; dollar-carry sign rule; Fama regression with HAC t | Lustig & Verdelhan (2007) AER 97(1); Lustig, Roussanov & Verdelhan (2011) RFS 24(11); Lustig, Roussanov & Verdelhan (2014) JFE 111(3) (cited); Menkhoff, Sarno, Schmeling & Schrimpf (2012a) J. Finance 67(2) (carry) and (2012b) JFE 106(3) (momentum, cited); Fama (1984) J. Monetary Economics 14(3) (cited) | G10 FX momentum and dollar-carry cards REJECT |
| 46 | Structured products by static replication | `core/ficc/structured.py`, `ui/structuring_page.py` | PPN = ZCB + participation call; reverse convertible = bond - put; dual-currency deposit = deposit - FX put; CMS steepener (no convexity adjustment); solved terms; FD Greeks; hedge sheet | Hull, Options, Futures and Other Derivatives (textbook replication); Garman & Kohlhagen (1983) | `tests/ficc_acceptance.py` |
| 47 | Equity-index derivatives and the implied-volatility surface | `core/ficc/equity_deriv.py`, `ui/derivatives_page.py`, `data/kis_markets.py` (option board) | Cost-of-carry fair value (continuous and KRX CD forms); Cboe implied forward; Black-76 IV; put-call parity and static-arbitrage checks; raw SVI with g(k) >= 0; model-free implied variance; Breeden-Litzenberger RND; box-spread rate; delta-hedger P&L identity | Gatheral (2004) SVI, Global Derivatives conference presentation; Gatheral & Jacquier (2014) Quantitative Finance 14(1) (cited); Breeden & Litzenberger (1978) J. Business 51(4) (cited by name); Demeterfi, Derman, Kamal & Zou (1999) J. Derivatives 6(4) [?]; Cboe VIX White Paper; Jackwerth (2000) RFS 13(2); Carr & Wu (2009) RFS 22(3) | Futures-basis card reconciles with the KIS theoretical within the dividend band; `tests/expansion_acceptance.py` |
| 48 | VIX term structure and the variance risk premium | `core/ficc/vol_products.py`, `context_log.py` (VRP) | Basis VIX3M/VIX - 1; hedged short-VX roll-down with rolling-beta hedge; VXX drift approx -basis/2 per month regression; VRP = VIX^2/12 - RV21 | Simon & Campasano (2014) J. Derivatives 21(3) (cited); Eraker & Wu (2017) JFE 125(1) (cited); Bollerslev, Tauchen & Zhou (2009) RFS 22(11) | `tests/expansion_acceptance.py`, `macro_m5_*` |
| 49 | Macro and recession indicators | `core/ficc/context_log.py`, `macro.py`, `ui/macro_page.py` | Estrella-Trubin yield-spread probit (T-bill bond-equivalent yield); Sahm rule; Taylor-rule residual range over 12 variants; SMA10m trend; RV21 percentile; 18-indicator z-score/percentile sheet with a 5-rule descriptive regime | Estrella & Trubin (2006) FRBNY Current Issues 12(5) (named in code); Sahm (2019) Hamilton Project/Brookings "Recession Ready" chapter; Taylor (1993) Carnegie-Rochester Conf. Series 39; Faber (2007) | `reports/QUANTGEN macro overlay research.md`; `tests/macro_m6_context.py`, `macro_ui_overlay.py` |
| 50 | Crypto econometrics | `core/crypto/analytics.py` (minus `regime_score`), `ui/crypto_page.py`, `data/crypto/crypto_client.py` | Kimchi premium ADF, half-life and HAC predictive regression; perpetual-funding carry decile event study; ADF on ln(ETH/BTC); weekday returns/volume; rolling GARCH-t VaR/PIT/QLIKE scorecard | Makarov & Schoar (2020) JFE 135(2) (cited); He, Manela, Ross & von Wachter (2022) "Fundamentals of perpetual futures", working paper [?]; Schmeling, Schrimpf & Todorov (2023) "Crypto carry", BIS WP 1087 [? number as cited in repo]; Baur, Cahill, Godfrey & Liu (2019) Finance Research Letters 31 [?] | Cards M_C1 kimchi REVISE, M_C4 funding PASS, M_C7 weekday PASS (no return effect), M_C8 ETH/BTC REJECT |
| 51 | Prediction markets as implied-probability data (research only, never positions) | `research_notes/QUANTGEN asset coverage expansion/other_assets.md` (section 6, Asset 12), `reports/QUANTGEN asset coverage expansion.md` (L102, K5 L184); currently exercised only by TRADEGEN-bound `grokteam` (PRED-FLB, market-mid benchmark) | YES price as probability; favourite-longshot bias; divergence vs the SOFR curve (K5 proposal, Brier gate); forecast skill of a model vs the market mid by DM | Wolfers & Zitzewitz (2004) J. Economic Perspectives 18(2); Snowberg & Wolfers (2010) JPE 118(4); Burgi, Deng & Whelan, Kalshi maker/taker returns working paper [? title, year]; Federal Reserve FEDS Note on Kalshi macro markets [? title, date] | Legal: Polymarket blocked by 방심위 2026-08-18, users investigated under 형법 도박죄, Kalshi eligibility for Korean residents UNVERIFIED; K5 not built |
| 52 | Kelly sizing for binary payoffs (literature only; current code is TRADEGEN-bound) | `grokteam/book.py` (`stake`), `paper_live/config.py` (`L.half_kelly`) | f* = (bq - (1-q))/b; half-Kelly with a cap and floor | Kelly (1956) Bell System Technical Journal 35(4); Thorp (2006) in Zenios & Ziemba (eds.) Handbook of Asset and Liability Management, vol. 1; MacLean, Thorp & Ziemba (2011) The Kelly Capital Growth Investment Criterion | LAZYOWEN money management held while its edge rule did not (`paper_live/narrative.json`); grokteam selfcheck `test_size_half_kelly_cap_and_floor` |

---

## 7. Open questions for the owner

1. **NEXTGEN trading-skills cockpit** (Skills, Workflows and Runs tabs; 16 files). Move it to TRADEGEN (recommended: its content is CANSLIM, VCP, Stockbee, Druckenmiller and parabolic-short practitioner screeners), or keep it in QUANTGEN as a research tool?
2. **Simulated operator rule engine** (`core/engine/*`, `core/rules/model.py`/`store.py`, Rules and Execution pages). It is classed PAPER_TRADING and stays. test_s4 forbids removing or altering it anyway. Confirm.
3. **`core/crypto/analytics.py::regime_score`.** Move it to TRADEGEN, or keep it in QUANTGEN only if it is gated as card C6?
4. **LLM report prompts in `core/ficc/insights.py`.** Delete only the "Positioning ideas" trade clauses and keep `deep_analysis` as research commentary (recommended), or move the whole Claude daily/weekly report to TRADEGEN?
5. **`signals.compute_signals`** (hand-weighted TA composite). Keep it as "context only" (recommended)?
6. **Replacing H2 after the readout.** Re-register the cost-gate hypothesis on QG-TACTICAL vs TACT-NOGATE as a new freeze, or keep the momentum-persistence "naive" account in QUANTGEN renamed as a neutral control (it is a z60 baseline, not Grok)?
7. **Ledger families GROKTEAM-BOOK and LAZYOWEN** in `~/.nextgen/macro/ledgers`. Leave the rows in QUANTGEN's directory (honest trial count, which also enters QUANTGEN's global N via `tf_gov`), or exclude those families from QUANTGEN's N once TRADEGEN owns copies?
8. **Shared machine state.** Both programs default to `~/.nextgen/*`. Should TRADEGEN get its own dirs via `QUANTGEN_MACRO_DIR`, `NEXTGEN_TRADING_DIR`, `NEXTGEN_RUNS_DIR` and `GROKTEAM_LEDGER_DIR` (recommended), and should the GROKTEAM forward look on/after 2027-02-01 run from TRADEGEN with the pinned library versions?
9. **Port the four reusable quant pieces** out of `grokteam/book.py` into QUANTGEN as new code: fat-tailed digital probability, logistic recalibration, DM skill vs a market benchmark, cluster block t. These would serve the K5 prediction-market data feed and a forecast-evaluation paper. If yes, which module and page?
10. **Research-paper pipeline.** Where should papers live (for example `research_notes/papers/<topic>/`), in what format (LaTeX/PDF via the existing reportlab primer kit, or Markdown), and which topics from section 6 come first?
11. **TRADEGEN legal scope.** The repo's own research already rates prediction markets as data-only for a Korean resident: Polymarket blocked 2026-08-18 with 도박죄 investigations, Kalshi eligibility unverified. Should TRADEGEN begin with a legal-venue review before any venue or asset is added? `research_notes/Korean resident trading venue legality/` exists and was not reviewed here.
12. **Wording.** Change "personal quant trading application" (pyproject, main.py docstrings) to "quantitative finance research application"?

---

### Provenance note

The eight area audits used Read, Grep and Glob plus read-only shell text tools. Two readers ran a one-line `python -c`: one `json.load`-ed `HYPOTHESES_frozen.json` to list keys, the other printed `1`. Neither imported repo code nor wrote anything. Nothing in `out/`, `out_krx/`, `grokteam/out/`, `cache/` or the data payloads was modified. Line numbers are as of 2026-10-23. Re-check them before editing.

---

## 8. Critic addendum

A second read-only pass (Grep, Glob, `ls`/`sed`/`grep` text reads; no Python, no repo code run) checked sections 1-7 against the repository and against `~/.nextgen`. Each item gives **what** was missed or misclassified, **where**, and **why it matters**. Line numbers are as of 2026-10-23.

### 8.1 Breakage the plan does not list

1. **`tests/acceptance.py` test_10, test_11 and test_12 cannot be kept.**
   - Where: section 3.2 says keep `test_10` to `test_18`. But test_10 and test_11 import `core.skills.runner` (`_redact`), and test_12 imports `core.skills.runner.RunResult` (L185-214).
   - Why: once the cockpit goes they fail with ImportError. Kept set is really test_08, 09, 13-18, 21, 22 (10 tests). Removed set is 37, not "about 35". If secret redaction is still wanted, it needs a new non-cockpit home.
2. **`tests/macro_ui_components.py::test_shell_fixes_runs_page_delegates_and_the_rail_scrolls` reads `ui/runs_page.py`.**
   - Where: L120-127 (`(ROOT / "ui" / "runs_page.py").read_text(...)`; message "19 entries, 620 px").
   - Why: deleting the Runs page makes a *macro* suite test fail with FileNotFoundError. Section 3.2 does not list it. Keep the rail-scroll and `on_app_start` assertions and drop the runs_page clause.
3. **Removing `regime_score` breaks a registered test and more of the Crypto page than section 3.3 lists.**
   - Where:
     - `core/crypto/analytics.py` self-check L430-435 calls `regime_score` three times. It runs as `expansion/selfcheck_crypto_analytics` (`tests/expansion_acceptance.py:343`). So the claim "No test references `regime_score`" holds only for test-file text.
     - `ui/crypto_page.py` uses `a["regime"]` at L110, L122, L136, L141 (AI payload), L164, L220, L225 and in its self-check at L233. Its docstring at L1 also names it.
     - Also `docs/ASSET_EXPANSION_SPEC.md:177`, `docs/build_expansion_primer.py:662` and the built `docs/QUANTGEN_Expansion_Primer.pdf`.
   - Why: section 3.3 names only L77 and "the regime tile", so the change would ship a failing expansion suite and a page that raises KeyError.
4. **Phase 2 can strand the H2 readout outside TRADEGEN.**
   - Where: Phase 0 copies `paper_live/out*/` now. The holdout replay, `replay_holdout/` and the final `verdict.json` are written later, in QUANTGEN (about 2026-11-03).
   - Why: TRADEGEN, which keeps LAZYOWEN, would hold a pre-readout snapshot. Either re-sync `paper_live/out/` and `out_krx/` into TRADEGEN after the readout and before Phase 2, or state that the LAZYOWEN verdict of record lives only in QUANTGEN.

### 8.2 Misclassified as "stays, quant only"

5. **`core/quant/insights.py::_SYSTEM` (L263-279) asks the LLM for trades on every page.**
   - What: the shared system prompt calls QUANTGEN "a personal quantitative trading application" and asks for "what the trade expression would be". It is the `deep_fn` of every Analysis card: crypto, derivatives, ETF and Strategy Lab directly, and the other pages through `ui/ai_panel.py` and `core/ficc/insights.deep_analysis`. README L674-678 says the same thing ("the trade expression", "positioning with levels").
   - Why: section 3.3 says `core/quant/insights.py` "is narrative only and makes no trade decisions". The Positioning clauses in `core/ficc/insights.py` are only the report-format half of this. Add `_SYSTEM` and README L674-678 to Q4 and Q12.

### 8.3 Shared `~/.nextgen` state after a folder copy (every path)

Both copies resolve these paths from the same home directory. "env" means it can be redirected from TRADEGEN's `.env`. Note that `load_dotenv()` (config.py L26-28) never overrides a variable already set in the OS environment, so a machine-level value applies to both programs.

| path | writer / reader | env override | in section 2/4.5? | risk if shared |
|---|---|---|---|---|
| `~/.nextgen/macro/ledgers/C3.jsonl`, `QG-CORE.jsonl`, `QG-TACTICAL.jsonl` (+ `.lock` sidecars) | `paper_live/engine.register_trials` (TREND -> C3, QG-*), `ui/strategy_lab_page.register_trials` (crypto_trend -> C3), `docs/techfund_study.py` (`FAMILY = "C3"`) | `QUANTGEN_MACRO_DIR` | **No**: only GROKTEAM-BOOK and LAZYOWEN are named | TRADEGEN's paper_live copy appends QG/C3 trials into QUANTGEN's families, which raises QUANTGEN's N and its DSR deflation. Today C3 holds 17 rows (paper_live TREND variants). If TRADEGEN is redirected to an empty dir instead, it loses that history. Copy all five family files, not two |
| `~/.nextgen/macro/` (`governance_events.jsonl`, `macro_state/`, alerts, book states, `dry_run/`) | `core/skills/macro_daily` (run at every app start: `main.py` `on_app_start(background=True)`), `core/engine/books.py`, `core/ficc/context_log.py`, `ui/macro_state_panel.py` | `QUANTGEN_MACRO_DIR` | Partly (named as the env to set) | Two open apps both write live macro artifacts and governance rows into one hash chain |
| `~/.nextgen/trading/rules.json`, `engine.json` | `core/rules/store.py:135`, `core/engine/runtime.py:79` | `NEXTGEN_TRADING_DIR` | Yes (env named) | Operator rules and engine state are shared |
| `~/.nextgen/ficc_cache/` (85 files) | `core/ficc/data.py`, `core/quant/history.py:428` | `NEXTGEN_FICC_CACHE` | **No** | Shared TTL cache. Low risk, but a stale or poisoned entry crosses programs, and `tests/quant_acceptance.py` already redirects it for this reason |
| `~/.nextgen/kis_token.json` | `data/krx/kis_client.py:53` | **none (hard-coded)** | **No** | One KIS OAuth token file for both programs, which share one KIS app key through the copied `.env`. A token refresh in one overwrites the other's token. Isolation needs a code change, and `data/krx/kis_client.py` is in the PIT/KIS chain |
| `~/.nextgen/dart_corp_codes.json` | `data/krx/opendart_client.py:44` | **none (hard-coded)** | **No** | Shared cache. Low risk |
| `~/.nextgen/runs/` (737 run dirs) | cockpit `core/skills/runs.py`, `runner.py` | `NEXTGEN_RUNS_DIR` | Yes | Covered |
| `~/.nextgen/grokteam/{binance,kalshi,model}` | `grokteam/book.py:60` | `GROKTEAM_DATA` | Yes | Covered |
| `~/.nextgen/policy_events.jsonl`, `prefs.json`, `trading/practice_checklist.json`, `trading/safety.json` | no writer in the current repo (legacy NEXTGEN) | n/a | **No** | Orphans. Decide whether TRADEGEN takes copies. Neither program should delete them |

6. **The test suite pins the default path, so isolation must be env-only.**
   - Where: `tests/macro_acceptance.py::home_listing` (T-HERM-02, L113-121) always snapshots `~/.nextgen/macro` and `~/.nextgen/trading/rules.json`, whatever `QUANTGEN_MACRO_DIR` says. `tests/macro_m0_rules.py:396-406` asserts `config.macro_dir() == Path.home()/".nextgen"/"macro"` when the env is unset.
   - Why: (a) TRADEGEN cannot change the default path in `config.py` without editing that test. (b) A TRADEGEN suite run, or an open TRADEGEN app writing at start-up, while QUANTGEN's macro suite runs makes QUANTGEN's T-HERM-02 fail falsely, and the reverse. The coordinator already hit this once with `~/.nextgen/runs` (docstring L115-117).
7. **The real `.env` is not in the plan (only `.env.example` is).**
   - Where: the repo-root `.env`, copied whole in Phase 0. It holds `NEXTGEN_SKILLS_ROOT` (L14), `FINVIZ_API_KEY`, `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`, `FXMACRODATA_API_KEY` (L20-23), `KIS_ACCOUNT_PD` (L31) and an unused `TYPESAFE_API_KEY` (L34). Values were not read.
   - Why: QUANTGEN keeps broker-adjacent keys after the cockpit leaves (Alpaca is a brokerage API, and a KIS account product code is the kind of value test_09 and T-RO-02 forbid in code). TRADEGEN gets the same KIS, FMP and Anthropic keys, so the two share rate limits, token and quota. Phase 1 should strip the skill keys from QUANTGEN's `.env`. TRADEGEN's `.env` should get the state-dir overrides and, where possible, its own API keys.
8. **Absolute paths and import-name collisions survive the copy.**
   - Where:
     - `.claude/settings.local.json` allow-rules run `PYTHONPATH=…/Desktop/QUANTGEN python tests/run_all.py` (L197, L265, L286). In a TRADEGEN session those run QUANTGEN's code.
     - `docs/b1_evidence/b1_experiment.py:15` (`sys.path.insert(0, r"…\Desktop\QUANTGEN")`).
     - `docs/drift_study.py:22` (a cache under QUANTGEN's scratchpad).
     - `paper_live/out*/verdict.json` `frozen_file` (absolute QUANTGEN path).
     - `pyproject.toml` `name = "quantgen"`, with generic top-level packages `core`, `data`, `ui`, `config`, `main`.
     - `.claude/launch.json` `quantgen-web` (it also carries an unrelated `godseye-dev` entry).
     - `main.py:98` `page.title = "QUANTGEN"`.
   - Why: a TRADEGEN run can silently import or write QUANTGEN. Two editable installs in one interpreter shadow each other. Use a separate venv, rename the TRADEGEN distribution, and rewrite the TRADEGEN copy of settings.local.json.

### 8.4 Dangling text and test registrations after removal

9. **README and in-app text that section 3.1/3.2 does not list:**
   - README L354: P0 cites "cockpit test_08 / test_09". The cited suite and file change when `acceptance.py` is split.
   - README L829: "The skill-insight bars (`ui/charts.py`)".
   - README L784: the paper row's "21 PASS" changes in Phase 2.
   - `ui/krx_page.py` L1 and L189 ("The skill library has no KRX coverage").
   - `config.py` docstring L1-16 ("Local configuration for the NEXTGEN skill cockpit").
   - `docs/ARCHITECTURE_REVIEW.md:60` (rail diagram with Workflows, Skills and Runs).
10. **Suite naming in `tests/run_all.py`.** The kept safety half of `tests/acceptance.py` is still registered as `cockpit/…` (L41, L57) and offered as `--suite cockpit` (L111; README L763). Rename it (for example `safety/`) in the same change, or the result file and README keep naming a component that no longer exists.
11. **Test-blind spots TRADEGEN inherits.**
    - The order-path scans `test_08`/`test_09` read only `runtime_py()` = `core/`, `data/`, `ui/`, `main.py`, `config.py` (`tests/acceptance.py` L48-54). They never see `paper_live/` or `grokteam/` (the Kalshi client).
    - TRADEGEN also inherits every P0 read-only guard: `config.KIS_QUOTATION_ALLOWLIST`, `data/krx/kis_client.check_quotation_path` (L56-72), test_08/09, `tests/macro_m0_harness.py` `FORBIDDEN_TEXT_CS` (T-RO-02) and README P0.
    - Why: section 4.3 notes only test_s4 as TRADEGEN's to retire. Any TRADEGEN execution path, and its Korean-law review, must retire these guards explicitly, not by a silent edit. Extending `runtime_py()` to every package is a cheap first step in both programs.

### 8.5 Unclassified files

12. **`paper_live/out/` code archives that carry LAZYOWEN rules:**
    - `backup_pre_fix1_2026-10-18/` to `backup_pre_fix4_2026-10-20/` (engine, config, grid, analyze, report and replay copies);
    - `config_pre_krx.py.bak`, `engine_pre_krx.py.bak`, `engine_pre_patch.py.bak`, `run_live_pre_patch.py.bak`;
    - `replay_prepatch/`;
    - `backtest_us_2026-10-20/` (including the script `run_us_backtest.py`, about 4,469 LAZYOWEN trade lines);
    - `out*/live/PREREG.json`, `AMENDMENTS.md`, `out*/dry/`.

    Section 3.4 covers only live source files and the published reports. Decide in Phase 2: keep as dated archives, or move. `frozen_rule/` and the `replay_sameday` archives that test_12 checks must stay.
13. **Research notes with TRADEGEN relevance that are not routed:**
    - `research_notes/Korean resident trading venue legality/` (7 files, 2026-10-23: crypto domestic/overseas, domestic securities and derivatives, overseas brokers, prediction markets and gambling, feasibility base rates, two verification notes);
    - `research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md` (Korean-resident venue and wallet access);
    - `kis_api_audit.md` (KIS endpoint audit).

    All are direct inputs to Q11. **Copy** them to TRADEGEN, as with the prediction-market sections.
14. **Test-pinned research paths that the paper pipeline (Q10) must not disturb.**
    - Where: `tests/macro_tf_data.py:349-352` asserts that `research_notes/QUANTGEN macro overlay research/council/` contains exactly `["README.md"]`, and that `research_notes/QUANTGEN technical and fundamental signals/README.md` names the techfund bundle.
    - Why: neither folder is in section 5's research-record list or in section 4.4. Writing papers into either folder, or renaming them, fails T-COUNCIL-DOCS-01.

### 8.6 Quant topics missing from the section 6 inventory

15. **Risk and performance measurement:** `core/quant/risk.py` (`analyze_history`, `align_histories`, `portfolio_point`) with the gs_quant offline cross-check, and `core/quant/gsq.py` (Marquee session tier for IRSwap pricing). Covers realised vol, max drawdown, Sharpe, the basket statistics feeding `optimize`, and engine labelling. Basis: Sharpe (1966; 1994 JPM 21(1)); Sortino & van der Meer (1991) JPM 17(4); Magdon-Ismail & Atiya (2004) Risk [?]. Section 5 lists the module, but no section 6 row seeds a paper.
16. **Timing fragility and shock-type evaluation:** `core/quant/cardp.py` (R-34 `timing_profile`, `FR_MAX` 0.5 fragility ratio, `SHOCK_TABLE` section 8.6, do-no-harm, the verdict order). It is a distinct validation idea (rebalance-timing luck, regime-stratified evaluation) and is not in rows 11-13. Basis: Hoffstein, Faber & Braun (2020) "Rebalance timing luck", J. Index Investing [?].
17. **Concentration bounds and two-name index concentration:** `core/quant/sleeves.py::apply_overlays` (`concentration_bound`, L608-699), R-07 single-name active-weight bound (`tests/macro_m5_books.py:135`), the `KRX_MARKET_CAPS_005930_000660_KOSPI` series, and techfund `r3_pair_share*`. KOSPI's Samsung and SK hynix weight is a Korea-specific portfolio-construction topic with no row. Basis: capped-index and active-share literature, for example Cremers & Petajisto (2009) RFS 22(9).
18. **Investor-type flows:** `core/ficc/flows_log.py` (DATA-6; foreign, institution and individual net buys; t-1 rule; open-leg test G-11 after three years). Basis: Choe, Kho & Stulz (1999) JFE 54(2); Froot, O'Connell & Seasholes (2001) JFE 59(2); Richards (2005) JFQA 40(1).
19. **ETF premium/discount, tracking error and LP behaviour:** `ui/etf_page.py`, `data/kis_markets.py` (NAV, premium history, basket, LP holdings). Row 32 covers only the iNAV fill flag, and row 35 only leveraged drag. Basis: Petajisto (2017) FAJ 73(1); Ben-David, Franzoni & Moussawi (2018) J. Finance 73(6).
20. **Research-record topics with no code yet (so no row), but already researched in the repo:**
    - Techfund bundle notes: P5 machine learning in asset pricing (Gu, Kelly & Xiu 2020 RFS 33(5)); E5 crowding and crash risk; P3 fundamental and accounting anomalies; E2 NYSE microstructure and execution; E6 corporate events; P4 backtest econometrics and costs;
    - `research_notes/QUANTGEN asset coverage expansion/bonds_commodities.md` (commodity carry, roll yield, futures term structure) and `index_futures_options.md`.

    For a portfolio of formal papers these are ready literature reviews. Add them as "literature-only" rows, like rows 51-52.
