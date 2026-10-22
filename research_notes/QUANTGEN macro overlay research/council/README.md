# Quant Council working files (pointer; not on this machine)

All panel members in these documents are simulated, fictional composites; nothing speaks for any real firm or person.
Not investment advice: QUANTGEN is a read-only research desk with no order path.

The macro specification v2.0 (`QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`, header
and L6461-6477) cites its council sources under this folder. **None of them was delivered to this repository**; this
file keeps the cited path resolvable and nothing here is a reconstruction. No `QC_*`, `ASPEC_*`, `QF*` or `QX_*` file
is created by the build: a fixture or test whose source lives here fails closed (`NotRun("REFDATA: ...")`).

Cited and absent:

- `QC_COUNCIL_RESOLUTIONS.md` (twelve resolutions, owner decisions D1-D5), `QC_modules.csv` (34 modules),
  `QC_errata.csv`, `QC_errata_notes.md`, `QC_errata_verify.py`, `QC_ledger.csv`, `QC_docket.csv`,
  `QC_chair_votes_merged.csv` (361 docket items), `QC_P_professors_chair.md`, `QC_E_executives_chair.md`,
  `QC_Q_quant_chair.md`.
- Adversarial review: `00_ASPEC_ROUND_BRIEF.md`, `ASPEC_R1_*.md`, `ASPEC_R2_*.md`, `ASPEC_R3_*.md`, `ASPEC_R4_risk_officer.md`.
- One level up (`research_notes/QUANTGEN macro overlay research/`): `QX_DLA_data_lab_protective_cards.md`,
  `QX_DLB_data_lab_estimators_regimes.md`, `QX_PX1`, `QX_PX2`, `QX_EX1`, `QX_EX2`, `QF1`-`QF7`; scripts and results
  under `quantgen_macro_data/` (including `results/QF3_dnb_evidence_classes.csv`).

What is in the repository instead:

- `reports/QUANTGEN_Quant_Council_Report.md` and `reports/QUANTGEN macro overlay research.md` (copies of the council
  bundle's two reports, with the two disclaimers above as a header; the body is byte-identical).
- `docs/council/` (the two offline HTML pages and their embedded data: 361 ledger items, 34 modules, 60 nodes).
- `QUANTGEN_Quant_Council_2026-10-03/` (the bundle as delivered: specification, tasks, backlog, reports, pages).
- `data/backlog_registry.json` (the backlog's status board, council queue, settling tests, owner-decision keys,
  data acquisitions and data-quality log as a read-only registry; `acting: false` on every row).

Binding text: the specification v2.0 and the rules store `data/macro/rules_v2.0.0.json`; the reports are findings,
not rules (the overlay report's own precedence note).
