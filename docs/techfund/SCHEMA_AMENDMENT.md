# Declared schema amendment: tech-fund card drafts vs the Council header schema

Status: **declared, not applied** (Sprint 7 integration, 2026-10-07). A proposal pending owner confirmation (rulings 3.7).

`core/ficc/schemas/model_card_header.macro.v2.0.json` is unchanged and stays closed (`unevaluatedProperties: false`).
The seven tech-fund drafts in this folder (`SCR-1`, `SCR-2`, `FS-1`..`FS-5`) are never committed as Council headers:
every run is NOT_RUN (KRX all-stock panel, KOSPI official closes or the L0 composite card absent; rulings 3.8), and a
header commit would also need the gate package frozen and the repository under git. Before a formal tech-fund run the
owner either approves a header schema revision that admits the fields below, or the runner maps them out of the header.

The check is `docs/techfund_study.header_overlap(draft)` (test `tests/macro_tf_integration.py`, T-TF-CARD-01): every
draft field that is also a header field validates against the header schema's own property schema, except the value
amendments of section 2 and the typed nulls of section 4. Each draft is also checked as a section 7.1 rule object by
`docs/techfund_study.dnb_issues` (the Council's 17 refused shapes and DNB-TF-01..17 over `tf_books.CARD_RULES`).

## 1. Fields validated against the header schema

`card_id`, `class` (CARD-O / CARD-P), `hypothesis`, `rule`, `instrument_book` (`KRX_stock_book`, `KRX_ETF_line`),
`costs` in the header form (`per_side: read_from_gate`, `floor: tick_floor`, `stress: 2.0`, `stress_line: printed`,
`printed_lines`), `comparator` (`overlay_off` for the CARD-O screens and FS-5, `S_same_average_exposure` for FS-1),
`data_span` (typed nulls, section 4).

## 2. Value amendments (header fields whose tech-fund value the closed schema refuses)

| Field | Tech-fund value | Header allows | Source |
|---|---|---|---|
| `benchmarks` | `EW`, `CW`, `CW_ex_pair`, `capped_CW` (SCR-1, SCR-2, FS-2) | buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk, current_recommended_book | GOV-1 long-only primary statistic vs the pre-registered benchmark set (R3:812; EC-T-06) |
| `comparator` | `S_beta` (FS-3) | S_same_average_exposure, overlay_off | GOV-11 / CR-01: S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat over the prior 252 sessions (OQ-03 proposal) |
| `class` | `descriptive` (FS-3), `forward_only` (FS-4) | CARD-O, CARD-P | register G-32 / G-33: FORWARD-SIM cells that are not gated cards (rule object kind CARD-P / CARD-O) |

## 3. Extension fields (not header fields; the closed schema refuses them as undeclared)

| Field | What it holds |
|---|---|
| `attribution` | GOV-3 block: factor set (KR: MKT SMB HML RMWq CMA UMD SEMI), factor-tilt threshold NW t 2.0 (OQ-15 proposal), display only |
| `beta_hat` | GOV-11: the S_beta comparator's beta (typed null), window 252 sessions, frozen at formation (FS-3) |
| `base_books` | B1 EW ALL, B2 VW ALL capped 5%, B3 top-200 VW capped 5%, B4 MOM_12_1 top quintile EW (screen cards) |
| `blocked_by` | the typed refusal reason (REFDATA / OWNER / PENDING / DNB) |
| `book` | the FORWARD-SIM book id `forward_sim:<card>` |
| `break_even` | GOV-7 pre-gate screen: REJECT if break-even < 2 x 35 bp; lab reference with file + line |
| `build_status` | SPECIFICATION_BOOK (SCR-1/2) or FORWARD_SIM (FS-1..5) |
| `comparator_text` | the plain-text comparator beside the header enum value |
| `construction` | the library calls that build the book (core.quant.tf_screens / tf_books / tf_gov) |
| `cost_detail` | per-side bp from validate.COST_BP_PER_SIDE, 2x stress, the itemised OWNER nulls (D-28: may only raise the rate) |
| `evaluation` | the nine-step gate with the GOV tightenings (GOV-1, -2, -4, -7, -3, -9, -5), step 8 and step 9 lines |
| `incubation` | GOV-10: clock 2026-10-01, >= 252 sessions from the first recorded session, never back-filled |
| `lab_reference` | lab constants (in sample, labelled, file + line), never recomputed (D-31) |
| `long_short` | L/S is a diagnostic only (GOV-1) |
| `market` | `KR` (the header has no top-level market field) |
| `node` | R3 node id (TF-nn) |
| `nulls` | every null leaf with its typed reason |
| `primary_statistic` | `long_only_net_excess` (GOV-1) |
| `proposal_status` | the rulings 3.7 label |
| `register_decision` | R3 go/no-go decision text |
| `register_id` | R3 register id (G-nn) |
| `ruling` | the chairs' ruling (CR-nn) |
| `run_status` | NOT_RUN |
| `screen_weight_by_book` | CR-06 priors 3 / 1 / 0 / 3 by base book (not a gate result, D-26) |
| `sign_split_rule` | EW and capped-VW signs differ -> REVISE (GOV-1) |
| `statistic_basis` | daily session differences (QA C4-1); goldens compared on their own basis only |
| `stress_windows` | GOV-9 fixed windows incl. 2026-06-22..07-30 (reporting only) |
| `trials` | GOV-2 trial count at registration (typed null) |
| `verdict` | null until a formal run |
| `what_would_change_it` | R3's settling condition, verbatim reference |

## 4. Typed nulls

`data_span.start` and `data_span.end` (and every other null leaf listed in a draft's `nulls`) are typed REFDATA /
OWNER / PENDING nulls until the first formal run; `header_overlap` reports them as `deferred`, never as valid.
