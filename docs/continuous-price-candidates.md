# Continuous held-position evidence candidates

This unit implements recording and independently verified valuation candidates.
**It does not enable held-position live trading.** The production account source
remains `UpbitIntervalSource`, which refuses after a fill or while holding a coin.

The owner selected continuous price recording. Implementing that choice requires
more than collecting samples. An account can drop below its protected floor and
recover between balance polls. Upbit book snapshots, minute candles, timestamps,
trade IDs and connection heartbeats do not by themselves prove that every
account valuation change was received. No production completeness verifier is
supplied by this change, and no real market API was called during development.

## Implemented contract

`execution_accounts.continuous` provides:

- `ContinuousPriceRecorder`: one explicit, bounded interval with an opening mark
  for each tracked KRW spot symbol. It preserves mark and fill ordering, including
  equal timestamps. An exact last-event duplicate is idempotent; a sequence gap,
  changed duplicate, clock regression or disconnect invalidates the entire
  recorder epoch. There is no reconnect, backfill, resume or reset shortcut.
- `ContinuousPath`: the untrusted candidate. Intervals are half-open
  `[start, end)`, with an endpoint immediately before events timestamped `end`.
  Candidates include a closing source watermark. Local sequence continuity is
  checked but is not described as venue-issued completeness proof.
- `verify_coverage`: calls a separately reviewed verifier with a challenge bound
  to the exact path, account capture, scope, stream epoch, timestamps and sequence
  bounds. Only a fully bound `VerifiedCoverage` receipt is accepted. A boolean,
  a `complete` field, or a matching local hash is insufficient. The verifier must
  authenticate the opening marks, all price changes and fills, their common
  ordering, the closing watermark, and the absence of omitted account changes.
  The verifier is a trusted code dependency, not a Python sandbox. The test
  verifier is invented test code and is never a production authority.
- `value_path`: reconciles complete historical fills and interval fills, includes
  fees at each fill, and derives cash, inventory, realized FIFO profit, minimum
  and maximum equity. It also retains an `EquityPoint` after every event so a
  peak followed by a loss cannot disappear from the evidence merely because
  the endpoint recovered. Realized profit in each point is the lifetime FIFO
  total, not only that day's result.

`archive_candidate` in `execution_launch.continuous_archive` writes an immutable,
private, content-addressed JSON record beneath the explicit configured state root
in `execution-price-paths/`. Link targets, different existing bytes and partial
records refuse. The archive is an audit copy of the candidate, not source
authentication, a retained verifier receipt, or a restart/re-anchor authority.
File writes remain in this explicitly checked launch integration; the account
recorder and valuation module perform no filesystem writes.

The bounds are 30 seconds, 64 symbols, 20,000 events, 128 interval fills and
20,000 prior fills. Bound violations refuse without truncation. FIFO prefix
calculations occur only at fills, not at each price mark. These are resource
bounds; they do not promise the collector meets a real Windows slot deadline.

## Account-capture integration

`preview_continuous_upbit_interval` in `execution_launch.account_interval`
combines a fenced, reconciled Upbit account capture with the verified path.
It reconstructs the opening cash and units from full history, checks all interval
fills and fees, reconciles closing cash and holdings, and uses the existing
baseline reducer and bridge to check the proposed interval's counters.

At 22:00 KST or midnight, a capture must bracket the boundary. The candidate's
marks reconstruct its exact boundary value; a ticker observed after the boundary
is not moved backwards in time. A late first balance read refuses. Temporary
midnight values used for the collector's structural self-check remain private
to the module and are not exposed to the path provider or published as a state.

The result is a `ContinuousIntervalPreview`, **not** a `BaselineFrame`.
`ContinuousAccountProvider` rejects this result type. Its `execution_ready`
property is always false.

`ContinuousUpbitCandidateSource.collect` offers an explicit integration point for
a pre-existing continuous recorder and the independently reviewed verifier. It
archives only candidates that passed the source and accounting checks. `latest()`
returns the audit candidate. Calling the object as an account-provider source
always raises `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`; there is no flag to
override this refusal. A failed capture clears the previous staged candidate.

## Why the live barrier remains

Minimum, maximum and endpoint values alone cannot enforce the owner's policy.
For example, a normalized path `100 → 110 → 105 → 115` has final equity and
high-watermark both `115`, and a minimum equal to its starting value. It still
crossed below the full-peak floor between `110` and `105`.

Before a held candidate can advance a live baseline, production integration must:

1. Establish actual venue completeness and common event ordering. A sampled
   feed or a user-supplied claim cannot supply it.
2. Bind the current signed owner limits, risk policy and existing E2 effective
   floor to every point in the path. Carry forward any D12 floor ratchet,
   including a threshold transition inside the interval. A profile's original
   floor is not necessarily the controller's current effective floor.
3. Detect intrainterval floor and daily-limit breaches before a recovery or
   midnight reset. Commit the required durable controller halt and protected
   state before publishing the endpoint, with crash and restart consistency
   against the separately trusted baseline head.
4. Preserve reviewed restart and re-anchor rules. A new process, successful
   later price sample, or new signature must not erase a permanent floor breach.

Those obligations are intentionally not replaced by a generic verifier callback
or an in-memory flag. The new code and tests provide evidence processing and
the explicit boundary that later integration must satisfy; they do not claim
an authorized live account, an executable strategy, a guaranteed floor, or a
profitable trade. Existing monetary and loss rules are unchanged.

## Validation

Synthetic tests in `tests/accounts_continuous.py` cover hidden intrainterval
drawdowns, buy/sell fees, round trips with equal endpoints, missing fills, strict
receipt binding, gap/disconnect poisoning, immutable archives, exact arithmetic,
22:00 and midnight reconstruction, and refusal to advance the live provider.
The existing flat-source tests continue to cover the original production path.

This is an engineering record, not legal, tax or investment advice. The author
is not a licensed adviser.
