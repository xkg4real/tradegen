# Exceptional-day recovery cutoff

An explicitly configured `RecoveryCondition` adds a separate day-opening equity
check on the genuine first trading day and on a day whose previous realized net
profit is exactly zero. The only supported condition is:

```json
{"cutoff_seconds":79200,"timezone":"Asia/Seoul","reference":"day_start_marked_equity"}
```

The public profile template leaves this optional field null. Actual loss budgets
belong in the owner's private profile. The condition never grants permission to
go below the original-principal floor, the existing peak-based floor, an effective
signed floor or an existing halt. Ordinary positive-profit days keep their
configured fraction of prior realized net profit. Prior-loss days remain blocked
with zero allowance, even if an input also claims to be the first trading day.
The existing realized-profit target remains a target and does not enlarge risk
budgets or override a stop.

## Before and after the boundary

Before 22:00 Seoul, the configured exceptional-day loss budget and all ordinary
floors apply. At and after 22:00, two additional conditions must both hold:

1. Genuine evidence for the exact 22:00 boundary shows marked account equity at
   least equal to the same Seoul day's opening equity.
2. The current reconciled marked account equity remains at least that opening
   equity. Equality itself is not a breach.

`RecoveryCheckpoint` carries `cutoff_at`, exact `equity_krw` and a source digest.
The digest binds evidence content; it does not authenticate its origin. The
reviewed baseline/source integration must establish the real observation and
retain that checkpoint unchanged. Later recovery cannot repair an earlier
boundary shortfall. A balance observed after the boundary must not be relabelled
as the boundary balance; missing proof remains unverified. See the
[continuous baseline contract](account-baseline-contract.md).

The risk evaluator requires an explicit aware `now` for configured recovery
conditions. Account timestamps retain their actual values. A 21:59:59 observation
is insufficient at 22:00 even if it is otherwise within the account's freshness
window. The Controller checks during monitoring, reservation and dispatch, so a
reservation before the boundary does not authorize dispatch after it.

## History and persistence

Historical daily loss and the lifetime high-watermark are never reset after
recovery. The daily historical loss ceiling still applies independently; hitting
it remains a daily stop. `recovery_floor` is a separate diagnostic, not a lower or
higher replacement for the persistent `effective_floor`. This avoids silently
changing the lifetime floor when a new Seoul day begins.

A missing/invalid checkpoint, a boundary shortfall or a subsequent current-equity
shortfall latches the Controller's existing `daily_stopped` state for the rest of
that Seoul day. Restart and later supplied proof cannot erase that recorded stop.
It does not manufacture a permanent floor halt; an actual breach of an ordinary
floor still triggers the existing permanent halt behavior. Qualified reducing
exits and cancellation retain the existing execution/conduct checks. D12 signed
limit timing and existing floor-relaxation approvals are unchanged.

This latch is written when the Controller receives an observation and risk
evaluation returns an unverified or breached recovery result. A provider may
instead refuse missing, stale or malformed source evidence before producing any
observation. That blocks the operation; it does not imply that a risk snapshot
was written. Deployment monitoring must retain and handle that source failure.

The configured condition changes profile/policy binding digests and therefore
requires matching research/review/preparation artifacts. An unsigned JSON edit
does not modify an already approved session. No owner signature is created here.

## Operational limits

The external scheduler must keep monitoring through the boundary independently
of strategy signals, including recovery after a process interruption. A sleeping
Windows PC, missed source boundary, stale account state or missing coverage cannot
be reported as successful recovery. This implementation starts no timer, network
connection, automatic liquidation or signing operation. It checks and persists
the supplied evidence; it cannot guarantee that a position will regain value or
that a sale will complete by 22:00, and fees/slippage may cause an actual loss.

This software is not legal, tax or investment advice and is not a licensed adviser.
