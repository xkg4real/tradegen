# 01 — Sprint plan: QUANTGEN v2.0 (Council macro spec M0–M10 + tech-fund register)

**Dates:** 2026-10-06 (single agentic build; sprints run back to back, each gated by `python tests/run_all.py`)
**Team:** one coordinator + parallel implementer agents per sprint (disjoint file ownership; no git worktrees, so
ownership is the only isolation)
**Sprint goal (whole programme):** every module of the Council spec v2.0 and the tech-fund BUILD NOW / INVARIANT /
GOVERNANCE / FORWARD-SIM items exists in the repository as code, shipped data and hermetic tests; everything that
cannot run on this machine is reported as NOT_RUN with its reason, never faked; the app shows the new state,
cards, registers and open owner actions; the baseline 266 checks still pass.

Milestone order is fixed by the spec (M0 → M10); the tech-fund items are interleaved where their dependencies land.
Capacity is not the constraint (ultracode); coherence is. Hence: shared contracts in `00_coordinator_rulings.md`,
one integration/fix agent per sprint, a full-suite run before the next sprint starts.

## Sprint backlog

| Sprint | Milestones | Parallel work packages (owner → files) | Exit tests (runs_from) | Depends on |
|---|---|---|---|---|
| **S1 Scaffolding** | M0 (15 tasks) | A `schemas`: `core/ficc/schemas/*.json`, `core/ficc/macro_schema.py`, `core/ficc/macro_artifacts.py` (writer, provenance, quarantine, read_only stamp) · B `rules-store`: `data/macro/rules_v2.0.0.json`, `core/rules/macro_rules.py`, `core/rules/governance.py`, `config.macro_dir()` · C `harness`: `tests/notrun.py`, `tests/run_all.py` (NOT_RUN status, `--milestone`), `tests/macro_registry.csv`, `tests/macro_acceptance.py` skeleton with hermetic guard + T-HERM-01/02 + T-RO-01 static scan, `tests/fixtures/macro/MANIFEST.csv` + loader, GATE leak fix · D `instrument book`: `core/quant/validate.COST_BP_PER_SIDE`, `core/quant/cards.py` (cost_per_side with tick floor, R-26 header checks, T-COST-02/03, T-BOOK-01 header clauses), `docs/asset_expansion_study.py` import | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01, T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses), T-DNB-01, T-OWNER-01 | — |
| **S2 Data layer** | M1 (23 tasks) | A `pit`: `core/ficc/pit.py`, `core/ficc/contracts.py`, `core/ficc/lag_audit.py`, `data/macro/series_registry.yaml`, ingest hook + ficc_cache fix in `core/ficc/data.py`, `core/quant/history.py` status field · B `calendars`: package conversion, `clocks/publication/regime/events/store.py`, `core/calendars/data/*` (draft, unsigned → refused at load; test fixtures signed in temp dirs), `core/markets.py` market↔venue map · C `books`: `core/engine/books.py` (runtime states, counters, persistence; hooks the risk layer calls later) · D `owner scripts`: `docs/kis_quote_check.py` (never run here; records "not run"), `docs/macro_fixtures.py` (fixture generation, refuses without reference files) | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-XMKT-01, T-CAL-01/02, T-RO-02, G-POST-01 (data rows) | S1 |
| **S3 Risk, estimators, sleeves** | M2, M3, M4 (21 tasks) | A `risk_layer`: `core/quant/risk_layer.py` (+ re-exports in `risk.py`), golden engine in reference mode (`tests/reference/`) · B `estimators`: `core/quant/vol_estimators.py`, `core/quant/forecast_eval.py`, `docs/vol_backtest.py` · C `sleeves`: `core/quant/sleeves.py`, `signals.py` family field, `optimize.inverse_vol_weights`, derived PIT series registration · tests per package in `tests/macro_acceptance.py` (sections M2/M3/M4) | T-CAP-02, T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; T-B5-01, I-10, T-EST-01/02/04; T-R03-01 (sleeve-scale, years), T-PRIOR-01; G-KR-*, G-US-*, G-B5-*, G-EST-*, G-MOM-*, G-INTL-01, G-BOOK-01 as NOT_RUN(REFDATA) | S2 |
| **S4 Engine, events, context** | M5, M6 (21 tasks) | A `books+ladder`: hard stop, RISK/OPS classes, re-arm, post-re-arm cap, `drawdown_ladder` (R-31 pseudo-code), look-through + concentration bound, weight books, T-MONO-01 · B `fills+events`: `orders.fill_model/simulate_fill` (R-27 + INV-2), `evaluator.BLOCKED/annotate` (R-08), `core/calendars/events.py` (R-10 store, windows, `event_calendar` artifact), gap tags, VaR display scale · C `context`: `core/ficc/context_log.py` (R-13 items, R-18 break protocol, isolation guard), `macro_artifacts.build_macro_state/build_overlay_decisions`, regime-read relabel in `macro.py` | I-04, I-04b, I-06, I-06b/c, T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-HALT-01, T-STEP-05, T-BOOK-03, T-MONO-01, T-CTX-01/02, T-BREAK-01; G-LAD-* NOT_RUN | S3 |
| **S5 Gate package and cards** | M7 (30 tasks) | A `gate_stats` (R-24: studentized paired bootstrap, Politis-White, SE ladder, power/MDE, PBO on claim, Lo-adjusted Sharpe) · B `gate_ledger` (R-23: family ledger, N_eff = max(N_clusters, N_equiv), step3, selection factor f) · C `cardp` (R-21 PC-1′/PC-2/PC-3/do-no-harm/CDaR guard, R-22 episodes/excess/start band/regime lines/post-trough, R-34 timing profile + look-ahead control, placebo + negative-control acceptance test) · D `cards+freeze` (`core/quant/cards.py` registry/headers/verdicts/archive, `core/quant/gate_package.py` freeze that refuses here, `docs/macro_overlay_study.py` runner, header drafts for R-06 KR, R-03, R-14, R-31, R-28, R-29 with typed nulls) | T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04, I-05 (synthetic); I-08, I-07, I-09, I-15, I-16, T-GATE-01..03, card tests → NOT_RUN(REFDATA/OWNER) with the refusal reason asserted | S4 |
| **S6 Forward, workflow, lab, deferred** | M8, M9, M10 (19 tasks) | A `pipeline`: `core/skills/pipeline.py`, `core/skills/macro_daily.py`, `core/skills/macro_workflows/macro_daily.yaml`, `core/skills/alerts.py`, run log, missed decisions, replay, `verdict_filter` (R-35), app-start hook in `main.py` · B `forward`: `core/quant/forward.py` (R-25 monitoring, demotion, budget split), R-28/R-29 FORWARD-SIM builders, `core/quant/refusal.py` (R-11/R-12) · C `lab`: `core/quant/lab.py` (R-16 grading: Kupiec/Christoffersen/ES Z2/fan PIT, envelope, replays), Quant Lab wiring, R-17 clock branch + header predicate (M10) | I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-BASIS-01 (S2); I-11 (NOT_RUN), T-REPRO-01c; T-CRYPTO-01, T-FX-01 | S5 |
| **S7 Tech-fund register** | R3 G-01..G-34 | A `data+registry`: `data/techfund/*.csv` + `MANIFEST.json`, `core/techfund.py` loader (weights, go/no-go, nodes, goldens, DNB-TF, BL-TF, OQ, XS), `do_not_build.tf_items` predicates into `macro_rules.py` · B `screens`: `core/quant/tf_screens.py` (F4 lottery, F6 dilution, F1 turnover, base books B1–B4, band_select, cap_weights, limit_lock_mask, L0 z-score composite ML-1, FS-5 guard) · C `governance`: `core/quant/tf_gov.py` (attribution block, Politis-White d/d² blocks, SPA/StepM family gate, BH-FDR, break-even pre-gate screen GOV-7, S_beta book GOV-11, stress table GOV-9, contamination log GOV-10, prior haircuts GOV-8) + INV-1..5 wiring (fill model, bands, no stops) + DATA-5 flags into regime tags + DATA-6 flow logging stub + CRY-1 control cards in `docs/macro_overlay_study.py` | `tests/techfund_acceptance.py`: data integrity (sha256), reference-constant pins (pair share 53.71%, screen IRs, VT20 scorecard), synthetic-panel tests of every screen/statistic, DNB-TF refusals, invariant tests | S5 (gate), S4 (fills) |
| **S8 UI and documents** | spec section 3.1 displays; council/tech-fund docs | A `macro page v2` (state, books, alerts, owner actions, context log, event calendar, dry-run button) · B `cards + research tabs` (model-card view, refusal/FORWARD-SIM books, weight table, go/no-go, DNB, backlog, council resolutions, open-HTML buttons) · C `theme+components` (`warning` token, `VERDICT_STYLE`, chips, rail scroll) · D `docs`: copy Council reports/backlog/pages and tech-fund trail into `reports/`, `research_notes/`, `docs/pages/`; README v2 section | `tests/flet_api_guard.py` on new files; build-time smoke test of every new page builder with synthetic artifacts | S6, S7 |
| **S9 Review and verification** | all | Parallel reviewers by area (correctness, look-ahead/PIT, read-only invariants, bounds, hermeticity, UI guard) → fix agents → full suite → design critique → final report | `python tests/run_all.py` (all suites), static scans, manual app launch smoke test | S8 |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Parallel agents drift from the shared contract | integration failures, duplicated helpers | `00_coordinator_rulings.md` section 4 names every shared symbol; one integration agent per sprint runs the suite and reconciles |
| Reference data absent | goldens and formal card runs cannot run | NOT_RUN status with reasons; nothing faked; owner action list on the Macro page |
| Spend/rate limits interrupt a workflow | partial sprint | every workflow is resumable (`resumeFromRunId`); file ownership is disjoint so partial work is additive |
| Existing suites touch live network / real dirs when keys exist | flaky baseline | new suites are hermetic; legacy cockpit tests untouched (out of scope) but noted in the final report |
| Flet API guard rejects new UI | suite red | guard rules listed in the UI brief; UI agents run the guard before returning |
| OneDrive sync of many new files | slow writes | keep generated artifacts under `~/.nextgen/macro`, not the repo |

## Definition of done (per sprint)

- [ ] Every task of the sprint's milestone(s) has code, tests and (where blocked) a NOT_RUN test naming the blocker
- [ ] `python tests/run_all.py` shows 0 FAIL (baseline 266 still PASS)
- [ ] The integration agent's summary lists every file touched and every deviation from the rulings
- [ ] No new dependency; no order path; no multiplier above 1.0; no `datetime.now()` in acting code

## Key dates

| Date | Event |
|---|---|
| 2026-10-06 | S1 → S9 run back to back |
| 2026-11-01 | Owner deadline from the spec: sign the 2027 KRX/NYSE/Fed/SIFMA calendars (T-CAL-02) |
| 2027-01-01 | `locked_holdout_start` (spec section 7) — no card may read data after it for design |
