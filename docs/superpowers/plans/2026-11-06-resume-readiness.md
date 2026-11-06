# November 6 continuation: rules review and study preparation

Base: main `06d06740cb1d275cd981e5750a212725ac21efbc`; handoff
`e1ebd6f6d251c41e9442cc87e0fd3158cbb370dc`. PR9, PR10 and PR11 are merged.
The November 5 handoff records completed code/table signing and a successful
owner check. These are reported owner results, not a new inspection of private
owner state. November 2's unsigned/setup status is historical.

## Latest owner decisions

The requested private Notion pages, read on November 6, contain answers that
supersede the handoff's three pending questions:

- Preserve the existing principal and high-watermark floors; explain costs.
- Use continuous price records for held positions.
- Shorten the research stage; continue toward real automated trading.

The shortening approval does not assert that any strategy passed, authorize an
agent signature/order, or waive the unchanged floor. Amounts, account scopes,
owner identifiers and local Windows paths stay private. Public goal records use
only ratios and dates: stage 1 about 7–7.5x by November 20 (latest November 25),
stage 2 about 10x during November 26–December 31, stage 3 about 5–5.5x during
January–February 2027. Withdrawals need a reviewed account transition; they must
not silently reset losses or the peak. Windows remains the operating environment;
this Cloud workspace is used for development and mocked verification.

## Work units

1. `rules-review-1122/research`: inventory all 47 rows, revisit primary sources
   and size-dependent conditions, record current law separately from proposals,
   and publish row-level conclusions. Correct demonstrated source errors.
   An inaccessible or inconclusive source remains unresolved; do not extend a
   row merely to avoid its deadline. Preserve allow/gated/block behavior unless
   an independently supported correction is explicitly included and reviewed.
2. `launch-quote-diagnostics-1`: prepare a bounded owner-run public-orderbook
   timing diagnostic. Development uses fake transport only. It reports receipt
   timing and existing parser refusals without loosening freshness rules,
   estimating an unidentifiable clock offset, or declaring live readiness.
3. `launch-shortened-study-1`: prepare a new 48-hour pilot registration using
   existing configurable protocol bounds, with costs, minimum roundtrips,
   family correction and authenticated review still required. The duration is
   an engineering choice under the owner's shortening approval, not a measured
   power claim. No old registration or frozen research changes. A shorter
   observation window does not guarantee a pass or a live-trading date.
4. `launch-resume-regression-1`: freeze runtime source, run focused and full
   acceptance with all 19 KEYLESS variables and isolated temporary state,
   investigate failures, and record measured results. This is the only unit in
   this plan allowed to commit QA and README test totals. Preserve CRLF and
   all inherited test identities; compare frozen study files with the base.
5. `launch-resume-delivery-1`: publish a reviewable feature PR, an updated
   continuation record and a concise owner report. No merge without this PR's
   approval. Checkpoint each complete unit; usage telemetry is unavailable.

The focused integration run reproduced an inherited Linux failure in the
deployment source-tree check: recursive globbing skips a symlinked directory,
so inspecting only the discovered Python files misses that linked subtree.
`cloud-compat-4` will inspect directory entries before descent, preserve Windows
reparse and file-hardlink refusals, and verify refusal before source contents are
read. This fixes the guard rather than skipping or weakening the failing test.

## Floor and fee example

Equality itself is permitted by `execution_control.risk.evaluate`. Normalize the
account and its protected peak to 1.000000. Buying a notional 0.500000 with an
illustrative fee rate 0.0005 costs 0.000250. If the asset is marked at that same
price immediately afterward, equity is 0.999750, below the unchanged floor of
1.000000; valuing at the bid or allowing for exit costs can reduce it further.
This is a conditional cost example, not a forecast or a fee quote.

The current odds sizing also allocates zero when available equity equals the
signed floor (`first_stake`), producing `STUCK_AT_START` before an order. The
monitor's equality rule and the order's available loss/cost budget are different
checks. Adding cash without changing how the initial capital and peak bind the
profile does not create an exception. No fee exemption, peak reset, loss-floor
loosening or guaranteed recovery is introduced here.

## Remaining integration

Continuous held-position evidence must establish complete valuation and fill
coverage, not infer intraperiod extrema from endpoints or minute candles.
Fresh instrument terms must propagate through profile, session, strategy and
order bindings without replacing a timestamp alone. Controlled coordination,
owner setup/session commands and authenticated selection remain separate work
units. Actual account evidence and owner actions cannot be substituted with
assumed input. Their absence does not prevent the independent development above.

No reliable target-hit probability has been measured. The earlier start/target
ratio is only a mathematical upper bound under a nonnegative supermartingale
model with no external funding, not an empirical probability. An unvalidated
strategy does not prove those assumptions. Multiplying stage bounds additionally
requires conditional stage assumptions; funding/withdrawals must be modelled.

This is engineering and research documentation, not legal, tax or investment
advice; the author is not a licensed adviser.
