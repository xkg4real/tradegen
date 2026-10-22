# QUANTGEN technical and fundamental signals (pointer)

All personas in the research trail are simulated, fictional composites; nothing speaks for any real firm or person.
Not investment advice: QUANTGEN is a read-only research desk with no order path.
All lab numbers are in-sample computations on price returns without dividends, not runs of QUANTGEN's gate.

## Where the research lives

The full trail is the bundle `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/` (as delivered,
2026-10-03): `research_notes/` (context brief, 14 round-1 papers, round-2 chair resolutions, and the round-3
synthesis `R3_TF_neural_link.md` with the go/no-go register G-01..G-77), `datalab/` (lab summaries and result CSVs,
including `results/r3/`), `scripts/` and `qa/` (QA report, recomputation table, edit log).

The three deliverables the bundle README names (`QUANTGEN_TECHFUND_INTEGRATION.md`, `QUANTGEN_TECHFUND_BACKLOG.md`,
`quantgen_signal_neural_link.html`) were **never delivered**. The register's `§TF-n` targets therefore resolve to no
file; this build reconstructs only what the R3 text, its CSVs and the QA corrections bind.

## This build's reconstruction (Sprint 7)

- `data/techfund/`: verbatim copies of the R3 frames (`r3_weights_final.csv`, `r3_weights_other_markets.csv`,
  `r3_go_nogo.csv`, `R3_TF_nodes.csv`, `R3_TF_edges.csv`, `r3_golden_values.csv`, the three `r3_pair_share*.csv`,
  `r3_focus_by_theme.json`) and the integration briefs' tables as data (`dnb_tf_items.json`, `bl_tf_items.json`,
  `oq_items.json`, `xs_items.json`, `ca_items.json`; each row cites its R3 lines), all listed in `MANIFEST.json`
  with sha256 and provenance. Not shipped: `quantgen_strategy_lab_cards.json` (a lossy derivative of the repo's own
  cards) and `r3_ledger_claims.json`.
- `core/techfund.py`: read-only loaders (weights, register with its class, nodes, edges, goldens, DNB-TF, BL-TF, OQ,
  XS, CA) that verify every file against the manifest and fail closed.
- `data/macro/rules_v2.0.0.json` `do_not_build.tf_items`: DNB-TF-01..17 as machine predicates with PROPOSED labels
  (R3 gives none), enforced by `core.rules.macro_rules.dnb_violations`.
- Briefs: `research_notes/QUANTGEN v2 integration map/tf_weights_register.md`, `tf_dnb_backlog.md`,
  `tf_goldens_amendments.md`, `tf_core_link.md`, `tf_algorithms.md`, `tf_chairs_qa.md`; rulings 3.7-3.9 of
  `00_coordinator_rulings.md`.

## Standing rules (coordinator rulings 3.7-3.9)

Council v2.0 governs where the two programmes differ. The 0-3 weights are design priors and display scores, not gate
results (macro sizing is `IV_m x 1/K_m`; `w / 3` is the XS-21 proposal, display only). OQ-01..15 and XS-01..22 are
proposals pending owner confirmation; none changes an acting parameter. Tech-fund cards are CARD-O under the nine-step
gate with the GOV amendments as tightenings; their runs are NOT_RUN without the KRX all-stock panel, and the golden
values are pinned as reference constants. Existing displays the DNB list names stay as CONTEXT.
