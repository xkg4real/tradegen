# 02 — UI design brief for the v2 surfaces (Flet 0.85.2, dark desktop app)

Binding for Sprint 8 and for any earlier sprint that produces a display field. Source of the constraints:
`code_ui.md` (as-built design system and the API guard), the spec's UI box (SPEC:761-763, 1127-1133, 1248) and the
tech-fund display captions (R3:703). Design-system queries (ui-ux-pro-max, dense dashboard / dark) returned generic
guidance: chip labels stay on one line and never rely on colour alone; body text ≥ 12 px; 4.5:1 contrast; loading and
empty states always explain and offer the next action. No stack-specific Flet guidance exists in that database, so the
app's own conventions govern.

## 1. Information architecture

The rail does not scroll and already overflows at the 620 px minimum height, so **no new nav entry**. Everything v2
lives inside two existing pages and is switched with the app's own "view selector" pattern (`ft.Dropdown` + host
`ft.AnimatedSwitcher`, as `rates_page`/`fx_page` do), which also keeps the 180 ms transition the app already uses.

| Page | View (Dropdown) | Content | Data source (read-only, validated) |
|---|---|---|---|
| Macro | **Macro sheet** (default, unchanged) | the 18-indicator sheet, descriptive read relabelled "Descriptive read — not a regime model (P19)" | `core.ficc.macro.macro_sheet` |
| Macro | **Overlay state** | per-market state tiles, composition line, books, alerts, inputs, owner actions, context log, event calendar, dry-run/run buttons | latest `macro_state`, `overlay_decision`, `context_log`, `event_calendar` artifacts under `config.macro_dir()`; alerts store |
| Macro | **Model cards** | macro CARD-O/CARD-P cards (verdict + disposition chips, reason code, label verbatim), refusal books and FORWARD-SIM books in their own group ("not a recommendation"), gate package status, header drafts | `docs/macro_overlay/cards`, `headers`, `cards/verdicts.jsonl`, store `gate.package` |
| Macro | **Research register** | tech-fund weight table (market filter), go/no-go register (group filter + detail pane), DO-NOT-BUILD (macro items 1-37 + DNB-TF), backlog status board + council queue, the twelve council resolutions, proposals pending owner confirmation (XS, OQ), buttons "Open Quant Council page" / "Open Macro Neural Link page" | `core.techfund` loader over `data/techfund/*`, `data/macro/rules_v2.0.0.json`, `docs/pages/*.html` |
| Strategy Lab | existing | loader hardened with `.get` so a non-legacy card can never crash the page; a one-line notice pointing to Macro → Model cards for v2 cards | unchanged |
| Quant Lab | existing | self-grading strip (Kupiec, Christoffersen CC, ES 97.5 % Z2, Basel zone, fan PIT) with PASS/FAIL/NOT RUN chips (M9) | `core.quant.lab` |
| Signals | existing | header notice: "Context only — not a v2 signal (DO-NOT-BUILD TF-12). Nothing here feeds a book." | unchanged |

## 2. Hierarchy of the Overlay state view (what the eye must meet first)

1. **Market selector + run chips** (`market`, `decided_session`, `run_mode`, `read_only`, data snapshot). A dry run shows a
   red chip "VENDOR DATA · DRY RUN · not an official close · not a card run".
2. **Book tiles** (one `stat` tile per book: `recommended:<m>`, `specification:<m>`): engine state chip
   (DISARMED muted / ARMED success / HALTED error), `composed` as the big number, `gross`, `binding_factor` chip.
   A HALTED book gets a `notice(..., "error", action=Acknowledge)` banner directly under its tile with class, reason code,
   since, re-arm mode and `rearm_not_before`. Banners persist until acknowledged (core writes `ack_utc`).
3. **Composition line**, rendered verbatim as text: `composed = vt × min(1.0, overlays…, ladder, post_rearm_cap)` with the
   numbers substituted, then `gross = min(composed, bound)`. Beside it a **multiplier bar**: a track 0→1 with the fill at
   `composed`, a tick at `vt` and a tick at `0.5 × vt` (the floor). Floor and cap are drawn, never implied.
4. **Overlays table** (`overlay_decision` rows: family, basis, vol_scale, multipliers with rule id and card chip, ladder,
   post-re-arm cap, min, applied-in-spec / applied-in-recommended, binding, reasons).
5. **Vol strip**: `sigma_ann`, `target_ann`, `vt_weight_next`, `vt_status` chip, estimator + B5 + gate-status chips,
   the two volatility labels as chips captioned "volatility labels (display only)" — never near the sheet's descriptive read.
6. **Flags**: hedge (`hedge_credit_off`, reasons), ladder (`ladder_step`, dwell, block-new-entries, hard-stop state),
   gap (`kr_open_gap_event`, `gap_sessions`, `var_display_scale`), annotation (`vix_ge_vix3m`).
7. **Alerts** (severity → token: page error / warn warning / info muted), each with count, first seen, books, Acknowledge.
8. **Inputs table** (name, series, source, obs date, value, value_status chip, role, status chip, stale deadline, dispute).
9. **Open owner actions and decisions**: D1–D6 table (decision, canonical key, value, status chip default/owner_set/pending)
   followed by "Owner inputs the build needs" (calendar sign-off, KIS quote check, notionals, ECOS code, git) and
   "Proposals pending owner confirmation" (tech-fund XS-01..22, OQ-01..15) — each a row with a one-line text, no action.
10. **Context log** (ExpansionTile, collapsed) and **Event calendar** (ExpansionTile, collapsed).
11. **Footer**: provenance (`schema`, `git_hash` UNVERSIONED chip, `tree_hash` short, `knowledge_utc`, `data_snapshot_id`).

Fail closed: no artifact → `empty_state("No macro state yet", "Run macro_daily (dry run on local vendor data) to see the
pipeline end to end; books stay DISARMED until official closes and signed calendars exist.", action=Run button)`.
Invalid or quarantined artifact → `notice(issues, "error")` and **no numbers**.

## 3. Tokens and shared components (Sprint 8-C owns these; earlier sprints must not add ad-hoc styles)

- `core/theme.py`: add `warning: str = "#d9a441"` (dark) / `"#8a5a00"` (light) as the LAST field of `Palette` with a default,
  so the positional `DARK`/`LIGHT` constructors keep working; add it to both constructors explicitly; `token_names()` picks it
  up for the guard. Contrast on `surface_2` (#1d252a): #d9a441 ≈ 7.9:1 (passes).
- `ui/components.py`:
  - `VERDICT_STYLE` = {PASS: ("PASS","success"), REVISE: ("REVISE","accent"), REJECT: ("REJECT","error"),
    INSUFFICIENT_DATA: ("INSUFFICIENT DATA","muted"), NOT_RUN: ("NOT RUN","muted"), UNVERIFIED: ("UNVERIFIED","warning")}
  - `DISPOSITION_STYLE` = {RECOMMENDATION: ("RECOMMENDATION","success"), BUILD_AS_INSURANCE: ("BUILD-AS-INSURANCE","accent"),
    INVARIANT_STEP: ("INVARIANT","accent"), SPECIFICATION_ONLY: ("SPECIFICATION BOOK","muted"),
    FORWARD_SIM: ("FORWARD-SIM · not a recommendation","muted"), REFUSAL_BOOK: ("REFUSAL BOOK · not a recommendation","muted"),
    DESCRIPTIVE: ("DESCRIPTIVE","muted")}
  - `ENGINE_STYLE` = {DISARMED: muted, ARMED: success, HALTED: error}; `INPUT_STATUS_STYLE` = {ok: success, warmup: accent,
    disputed: warning, stale/stale_missed_release/missing/provisional_rejected/session_mismatch/synthetic_rejected/fail_closed: error, not_run: muted}
  - `verdict_chip(verdict, *, tooltip="")`, `disposition_chip(d)`, `status_chip(style_map, key)` all via `chip` (word + colour).
  - `data_table(columns, rows, *, numeric_from=None, wide_last=False, row_height=36)` — the single DataTable helper
    (replaces a fourth private `_table`); long text columns go to a detail pane, not the table.
  - `multiplier_bar(composed, vt, *, width=260)` — container track with fill and two tick markers, labelled numerically.
  - `open_path(path)` — lifted from `runs_page.open_folder` (os.startfile / xdg-open, try/except); shows the path as
    selectable text when the file is missing.
- Chips never wrap: labels are short, full text in `tooltip`. Every chip carries its word.

## 4. Behaviour

- Every v2 view has its own **Refresh**; artifacts are re-read on Refresh (pages are cached forever otherwise).
- Long work (`macro_daily` dry run, card study refusal check) runs in `page.run_thread`, with the app's two-tier `except`
  and a `ProgressRing` + "Running… (hermetic, local data)" text while it runs; completion replaces the view in place.
- The **Run macro_daily** button offers two options in a small Dropdown: "Dry run (local vendor data)" and
  "Live (needs KIS, signed calendars)" — the second is disabled with a tooltip naming what is missing.
- Acknowledge calls `core.skills.alerts.acknowledge(alert_id, by="operator")`; the UI holds no alert state.
- The UI never computes exposure; it renders validated artifacts only (fail closed, see §2).

## 5. Accessibility and quality checklist (design critique applied at the end of Sprint 8)

- First impression: within two seconds the reader knows, per market, whether the recommended book is DISARMED/ARMED/HALTED
  and at what multiplier, and why (binding factor, failing input). Nothing else may be visually louder.
- No colour-only meaning; text ≥ 12 px except chip labels (11 px, as the app's chips already are); 4.5:1 contrast for text
  on `surface`/`surface_2` (tokens already pass; `warning` added at 7.9:1).
- Interactive targets: Flet buttons (≥ 36 px) and chips are not interactive (no hover-only affordances).
- Empty, loading and error states each say what happened and what to do next.
- Consistency: every verdict on every page goes through `verdict_chip` (fixes the four inconsistent ad-hoc colourings
  noted in `code_ui.md` E.11 where those lines are touched).
- Guard: every new UI module is flat in `ui/`, uses `pal.<token>` only, `ft.<Control>` keywords from the 0.85.2 signatures
  (`ft.Dropdown(on_select=…)`, `ft.Image(src=…)`, `ft.TextField(helper=…)`), `page.show_dialog/pop_dialog`, never `page.open`.
