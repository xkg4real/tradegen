# Continuous account risk baseline

`execution_accounts.baseline` reduces explicit, reviewed account-history intervals
to the existing `RiskBaseline` type. It performs no network calls, file operations,
credential access, owner-log loading, signing or activation. This removes the need
to manually update a static baseline on each observation; it does not manufacture
the authentic source feed or an initial lifetime history anchor.

## Explicit supported conventions

Construct `BaselineConventions` with three required fields and an optional explicit
recovery boundary:

- `daily_loss="maximum_net_equity_loss_from_day_open"`: the largest nonnegative
  difference between that Seoul day's opening marked account equity and the lowest
  marked equity observed in any complete covered interval during the day. Recovery
  cannot erase an earlier loss. This is an explicitly selected interpretation,
  not a new default for the owner's still-unresolved daily-loss choice.
  The owner approved the planned BR-16 exception on 2026-11-23 (OQ6). In a long
  interval spanning a detected suspend or restart, the first 30 seconds and the
  first account record after the gap count toward the loss. The remaining
  interior points are retained for audit. The implementation at `1fd8792` uses
  the existing convention above.
- `external_flows="no_external_flows"`: both gross incoming and gross outgoing
  external flows must be known and zero for every interval. Offsetting flows do
  not count as no flow. A funded account with no subsequent transfers is supported.
  Planned, not implemented at `1fd8792`: the
  [approach-A design](superpowers/specs/2026-11-20-blocker1-held-interval-approach-a-design.md)
  (BR-21, BR-22) adds flow and trade classification both while running and after
  a gap (OQ1). The owner approved OQ1–7 on 2026-11-23 with the protected-floor
  condition below for OQ2–3. The proposed treatment of unexplained residuals
  (OQ8) awaits separate review.
- `max_interval_seconds`: an explicit integer from1 to300. A longer uncovered time
  range refuses rather than interpolating missing peaks, troughs or activity.
  Planned: a separate gap interval kind whose path is rebuilt from the trade list,
  bounded by the list's reach instead (approach-A design BR-16, BR-17).
- `recovery_cutoff_seconds`: `None` preserves the original behavior. The only
  supported enabled value is the exact integer `79200`, meaning 22:00 Seoul time.
  The matching risk policy must independently enable the same recovery condition;
  a source convention does not choose a loss budget or lower any protected floor.

The existing profile's `externally_reconciled` convention can receive this reducer's
result only when the operator explicitly chooses and reviews the detailed convention
above. The reducer does not overwrite the profile or choose a policy for the owner.

Broader flow adjustment is unsupported in the current code. The existing Controller keeps
a monotone raw high-watermark and a fixed opening equity per day; decreasing a
cash-flow-adjusted peak after a withdrawal would not change that persisted control
history. Implementing that policy requires an agreed valuation convention and a
coherent Controller transition, not merely subtracting a transfer in this reducer.
In the revised OQ2 design (BR-22), deposits and withdrawals, including withdrawal
fees in the outflow, are excluded from trading profit and loss. Equity minus
cumulative net external flow gives a monotone adjusted peak and a fixed adjusted
day opening. A deposit adds to protection and creates no extra loss budget. A
withdrawal cannot lower the nominal KRW principal floor or the high-watermark
floor already protected under the existing policy. Evaluate actual marked equity
against the applicable protected nominal floor as well as checking the adjusted
limits. Carry the flow history and protected floors through a reviewed re-anchor.
If a direct withdrawal leaves actual equity below its protected floor, record it,
block new buys and alert. Existing halt and daily-stop rules at judged points
still apply. OQ3 replaces the old no-flow budget rule only with these protections.

## Anchor, advance and export

1. An authenticated account-history integration constructs `BaselineAnchor` from a
   reviewed `RiskBaseline`, current exact equity, cumulative realized net profit,
   the realized-profit total at day opening, previous-day net profit (or `None`
   only on the first trading day), account scope and a source sequence. The anchor
   must contain an honest day opening, prior lifetime peak, loss-to-date and actual
   first trading date. It is not a new-process snapshot or a first-day reset.
2. `initialize_baseline(conventions, anchor)` validates that evidence and returns
   an immutable state with a content digest. The original anchor's peak cannot be
   below its day-opening equity; a higher current equity does not repair a
   contradictory historical anchor. The state's peak includes the current equity.
3. For every new interval, supply `BaselineInterval` with the exact previous state
   digest, next sequence, previous observation time, new observation time, current
   equity, interval minimum/maximum equity, cumulative realized net profit, known
   gross external inflows/outflows and source/coverage digests. All values are
   exact bounded `Decimal`s already expressed in KRW using reviewed source and FX
   conventions. **The extrema are source evidence, not min/max of the endpoints.**
   One planned exception (approach-A design BR-16; not implemented at `1fd8792`)
   follows the owner's decision of 2026-11-20 that a gap is judged at the first
   account record after it. For a gap interval that spans a detected suspend or
   restart, judge the true gap endpoints and each point in the first 30 seconds
   measured from its original start. Splitting at midnight or a signed-limit
   boundary does not start a new 30-second allowance. Retain the lowest point
   of the entire reconstructed path in the audit record. The owner accepted the
   30-second rule (OQ6). A recovered dip in the exempt interior does not create a
   retrospective halt. A breach in the judged first 30 seconds still counts.
   The gap high raises the peak before judging the first record after the gap.
   A floor breach there halts; a daily-limit breach sets the daily stop. Earlier
   halts survive the gap. Ordinary retries or overruns are judged throughout.
   If the trade list cannot cover the gap, stop the chain, block entries and
   alert until a reviewed re-anchor. Today's re-anchor requires zero coins
   (including personal holdings) and zero open orders (OQ7).
4. `advance_baseline(state, interval)` rejects scope changes, missing coverage
   identifiers, contradictory extrema, time/sequence gaps, rollbacks and unsupported
   flows. Identical redelivery returns the same state and timestamp. A changed
   duplicate refuses. Peak and daily loss survive price recovery and process restart.
5. `risk_baseline(state, now=..., expected_head=...)` exports the existing provider
   type with the state's actual timestamp, first trading date and unchanged approved
   effective floor. The expected head must come from the caller's separately
   retained trusted checkpoint. More than30seconds old, future, or previous-Seoul-day
   state refuses. Export never stamps old evidence with `now` to make it fresh.

`state_json(state)` and `restore_state(raw, expected_head=...)` support explicit
private checkpoint storage. The reducer itself does not write it. Unknown fields,
duplicate JSON keys, ambiguous numeric inputs, damaged hashes and a rollback against
the separately retained expected head refuse. The checkpoint contains account
amounts and must not be printed in public diagnostics or committed to GitHub.

The caller must atomically persist each accepted state and its trusted expected
head before allowing dependent trading work. A restart restores that state; it
must not call `initialize_baseline` again to discard history. Neither a writable
hash chain nor matching two user-supplied hashes authenticates the source or proves
that a checkpoint is the latest one.

## Seoul midnight

Every interval represents `[start, end)` activity. Its `end` valuation is the
opening snapshot immediately before events timestamped exactly at `end`; extrema
include both adjoining snapshots. The trusted producer must establish this cut-off
and collect exact boundary evidence.

Planned, not implemented at `1fd8792` (approach-A design BR-11 and BR-12): a
boundary value may be rebuilt from a capture read within 30 seconds after the
boundary, minus the fills and flows stamped since the boundary, at each coin's
last trade before it. It is computed from evidence, not a later balance
relabelled. A boundary missed while the app runs still refuses; one missed
inside a gap that spans a suspend or restart is rebuilt and split there.

A transition to another Seoul day must end exactly at the next Seoul midnight.
Skipping across midnight to the first later poll refuses. The new opening equity
comes from that boundary snapshot; daily loss resets to zero there, while lifetime
peak, first trading date and approved effective floor persist. Events timestamped
at midnight belong to the next interval and therefore the new day. Previous-day
realized profit is the cumulative-profit difference across the completed day,
never inferred from equity changes. It is retained in reducer state for comparison
with the account provider's independently reconstructed FIFO daily result.

## Optional recovery boundary

For a configured first trading day or a day whose previous realized net profit
was exactly zero, the source must supply an interval ending exactly at 22:00
Seoul time. An interval from before that boundary to a later time refuses even
when its duration is otherwise valid. A pre-boundary observation also refuses
export after the boundary despite fitting the ordinary 30-second freshness
window. No timestamp is rewritten and no balance is interpolated.

The boundary creates `RecoveryCheckpoint(cutoff_at, equity_krw, source_sha256)`
from that exact endpoint. The account bridge reconciles the endpoint's actual
balance and binds its complete account evidence to the source digest. The proof
is retained unchanged through later recovery, repeated calls and process
restarts; its equity is never replaced with a later, better balance. Existing
daily maximum loss, lifetime high-watermark, first trading date and approved
floor remain intact. Only the next Seoul midnight clears that day's proof.
Planned (approach-A design BR-11, BR-12 and BR-16): a 22:00 value rebuilt within
the permitted running boundary retry window supplies proof. A required 22:00
boundary inside the exempt gap has no recovery proof and blocks new entries
for that day (OQ6). A missed running boundary still stops the chain when its
bounded retry fails.

An anchor exactly at the boundary can capture its actual value. An anchor after
the boundary has no proof and remains unknown; supplied historical proof is not
accepted as a shortcut to recreate a completed day. Restoring an existing trusted
checkpoint preserves its already established proof. The risk guard separately
distinguishes missing proof from an evidenced deadline breach and compares the
proof against the day's opening equity. Source evidence does not grant an order
permission or an exception to principal/high-watermark protection.

Disabled conventions continue using schema 1 with the original serialized field
shape and digest representation, so existing trusted heads still restore. The
enabled convention uses schema 2 with explicit boundary configuration and proof.
There is no automatic migration, reseeding or history reset. Moving an existing
deployment to the new convention requires a reviewed transition preserving its
full history and independently trusted head; this module does not provide a
shortcut that promotes local state to external authority.

## Integration boundary

The reducer accepts a valuation/history feed which has already established its
identity, interval coverage and money semantics. It does not call `build_observation`
with a dummy baseline, infer a peak from a fresh endpoint, or grant execution
permission. Pass the exported baseline into a complete `AccountBundle` and let the
existing provider reconcile account evidence normally. Compare its realized-profit
totals against the producer's totals before using the result in an automated loop.

The [checkpoint store and account bridge](account-baseline-integration.md) provide
local atomic persistence, exact account reconciliation and a callable provider.
The current full-scan Upbit collector does not supply the required continuous
interval extrema or an independently trusted durable head service. Connecting
those producers remains a production integration task. A static owner profile
or successful synthetic test does not establish that live integration.

This software is not legal, tax or investment advice and is not a licensed adviser.
