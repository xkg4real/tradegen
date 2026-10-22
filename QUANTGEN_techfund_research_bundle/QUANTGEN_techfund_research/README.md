# QUANTGEN technical and fundamental signals: research trail (2026-10-03)

This bundle holds everything behind the three deliverables (QUANTGEN_TECHFUND_INTEGRATION.md, QUANTGEN_TECHFUND_BACKLOG.md, and the research report).

- research_notes/: the context brief (00), the 14 round-1 position papers (P1-P7 professors, E1-E7 executives; all fictional composite personas), the round-2 chair resolutions with debate records (R2_PROF, R2_EXEC) and working notes, and the round-3 Neural Link synthesis (R3_TF_neural_link.md).
- datalab/: summaries of the four data labs (KRX round 1, US round 1, KRX round 2, index/gate round 2), their result CSVs, the R3 node and edge map, verification logs, and QUANTGEN's 16-card Strategy Lab record.
- scripts/: the lab scripts. They expect the KRX marcap parquet files (github.com/FinanceData/marcap) under /home/claude/data_raw/marcap/data/ and the US files under /home/claude/data_raw/us/; edit the paths in kr_common.py and us_common.py to rerun.
- qa/: the independent QA report, recomputation table and edit log.

All lab numbers are in-sample computations on price returns without dividends, not runs of QUANTGEN's gate.
