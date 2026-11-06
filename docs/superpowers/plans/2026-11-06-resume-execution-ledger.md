# November 6 continuation: execution record

Base: main `06d06740cb1d275cd981e5750a212725ac21efbc`. Implementation:
`43a1c5c` (rules research and corrections), `d5bac0a` (diagnostics, study draft,
deployment scan). PR: <https://github.com/xkg4real/tradegen/pull/12>.

## Completed units

- `rules-review-1122/research`: all 47 rows have a source/disposition entry in
  [the review](../../../research_notes/Korean%20resident%20trading%20venue%20legality/review_2026-11-06.md).
  Thirteen rows have explanatory/source corrections; match, requirements,
  treatment, caps, acknowledgements, auto-off and review deadlines are identical
  to the base. The tax note now distinguishes combined taxable domestic/overseas
  shares from the separate derivatives category. Current law, announced proposals
  and stricter product policies are separate. The full November deadline-renewal
  task remains open because listed source/eligibility questions are unresolved.
- `launch-quote-diagnostics-1`: bounded owner-run timing measurements through
  the existing public Upbit GET. Original bytes/times and normal quote refusal
  are preserved. Negative apparent age is measured, not repaired; no clock
  offset, synchronized-clock or execution-authority claim is made. No agent
  venue request was performed.
- `launch-shortened-study-1`: a new offline 48-hour pilot draft, 576 return
  intervals and 577 window books (plus the existing pre-window probe).
  Candidates, costs and statistical conditions are retained. New identifiers,
  fresh explicit profile terms and future publication remain required. A local
  ID difference cannot establish complete trial history or unseen observations.
- `cloud-compat-4`: deployment scans directory entries before descent, so a
  POSIX directory symlink cannot disappear from the source check. Windows
  reparse and file-hardlink refusals remain in place. Linked sources refuse
  before source AST inspection/hashing; ordinary nested files remain included.

## Findings and verification

The first combined launch run measured **281 PASS / 1 FAIL / 13 NOT_RUN**. The
failure reproduced an inherited Linux source-scan omission in `Path.rglob`,
unrelated to the new quote path. It was fixed, not skipped. The deployment suite
then passed **10/10**, including two new link/hardlink regression cases.

Focused verification: rules table **70/70**, timing diagnostic **18/18**,
shortened draft **7/7**, deployment **10/10**. Source and review responsibilities
were split; the draft tool received an independent read-only implementation
review. Legal statements were checked against official documents, with failed
retrievals and partial verification disclosed in the row-level report.

One complete source-frozen run on `d5bac0a` measured:

| Result | Count |
| --- | ---: |
| Total | 2354 |
| PASS | 2219 |
| FAIL | 0 |
| NOT_RUN | 135 |
| New tests, all PASS | 27 |
| Elapsed seconds | 587.208 |

The 135 skips are 121 inherited macro reference-data cases, 13 Windows
private-input cases (12 reader cases and one workflow case), and one Windows
console API case. This Linux run does not establish that those Windows cases
passed on the owner's PC. Every one of the base's 2327 test identities remains.
The two previously recorded Windows venv-location failures are not failures in
this run. Platform-specific PASS/NOT_RUN changes are not test removals.

All 19 credential inputs were explicitly KEYLESS, state was isolated, venue
transports were fake, and real-home metadata stayed unchanged. The two protected
frozen-research paths have no diff against the base. Actual connection, signing,
arming, orders and a qualified real strategy remain absent. Detailed measured
counts are in `qa/resume_20261106_validation.json`; full case results are in
`qa/acceptance_results.json`. QA/README were updated only in the regression unit
authorized by the plan, with existing CRLF preserved. The affected documentation,
QA and boundary-check modules then measured 149 PASS / 0 FAIL / 9 inherited
NOT_RUN. Runtime source did not change after the full run.

## Remaining work and owner effect

The new rules bytes need owner table approval after merge. The new quote and
deployment code needs owner code approval in the intended Windows interpreter;
the old signature cannot approve the new source. A new study must freeze the
new capture-source digest before collecting data. PR12 itself needs its own
merge approval under the handoff rules.

The unchanged principal/high-watermark floor can still leave no positive
cost/loss headroom. Equality alone is not a risk breach. Continuous held-position
coverage, automatic current instrument-term refresh, controlled coordination,
operator lifecycle commands, authenticated strategy selection and actual owner
evidence remain follow-up work. The selected continuous-tracking approach is
already an owner decision; do not ask the old three questions again.

No actual probability of the staged funding goals has been measured. A shorter
study is not a pass, and a review report is not a new signed or extended rule.

This is engineering and research documentation, not legal, tax or investment
advice; the author is not a licensed adviser.
