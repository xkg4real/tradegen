# PC clock against Upbit orderbook stamps: measurement and decision (2026-11-12)

Status: owner decision, 2026-11-12. The outcome is **a signed 1-second allowance in `execution_accounts/quotes.py`
plus an owner clock rule**. The code change is not made here. It is a small code PR after universe PR 5 and before
the single final code-approve. Line numbers below are on main `0757542`.

## The rule in question

`parse_orderbook` refuses a book whose stamp is later than the PC receipt time:
`timedelta(0) <= received-asof <= _MAX_AGE` (`execution_accounts/quotes.py:155-156`, code
`QUOTE_BOOK_STALE_OR_FUTURE`). The book stamp comes from Upbit's clock and the receipt time from the PC clock. So a PC
clock that runs behind Upbit by more than the book's stamp-to-receipt lag loses that read.

In a study this is fatal, not a lost slot. A refused probe read fails as `STUDY_PREWINDOW_PROBE_FAILED`
(`execution_launch/study.py:369`). Inside the window, the first refusal ends the trial for every candidate, and nothing
is backfilled (`execution_launch/study.py:15`, `:355-358`).

## Measurement

The owner ran `tools/clock_check.py` (PR #26) once on their PC on 2026-11-12, about 14 hours after Windows last synced
the clock. The run used 20 public KRW-BTC orderbook reads, 1 s apart:

```
CLOCK_CHECK symbol=KRW-BTC samples=20/20 admitted=18 reason=none
LAG_MS min=-4 median=64 max=879
DATE_MS min=24 median=548 max=926
RTT_MS min=342 median=440 max=735
REFUSED QUOTE_BOOK_STALE_OR_FUTURE=2 QUOTE_RECEIPT_STALE_OR_FUTURE=0 QUOTE_SERVER_CLOCK_MISMATCH=0
W32TM status=unavailable
```

What it shows:

- **The PC clock is behind Upbit by at least 3 ms.** For every read, lag = (PC minus Upbit offset) + (book staleness
  + network delay). The second term is never negative, so the offset is at most `LAG_MS min`. That value is floored
  to whole ms, so the true minimum lag was between -4 and -3 ms.
- **2 of 20 reads (10%) were refused** for that reason alone.
- **There is no sign of a large offset.** The HTTP Date header has one-second resolution. Its offsets spread almost
  evenly over 24 to 926 ms, which fits an offset of tens of milliseconds at most.
- **`W32TM status=unavailable` means the Windows time service was stopped,** not that `w32tm` is missing. A read-only
  check the same morning found the service `Stopped` with start type `Manual` (trigger start), and `w32tm` answered
  0x80070426. The `SynchronizeTime` scheduled task last ran on 2026-11-11 at 19:08 KST with result 0. So Windows syncs
  about once a day and keeps the service off in between.
- RTT includes a new connection per request and local processing. It is not the network round trip.

## Why the strict rule cannot stand

A study reads one book per slot, and one refusal ends it. A 48-hour study at 300 s bars makes about 578 reads.

| Per-read refusal rate | Chance all 578 reads pass |
|---|---|
| 10% (as measured) | about 0 |
| 1.2% (low end of the 95% interval for 2/20) | under 0.1% |
| 0.1% | about 56% |

Syncing alone does not fix this. NTP over the internet sets the clock to within tens of milliseconds, either side of
zero. Here a clock only a few milliseconds behind already refused 10% of reads.

## Decision

1. **A signed allowance of 1,000 ms for a book stamped after the PC receipt.**
   - Only the lower bound of the book-time check changes: `-allowance <= received-asof <= _MAX_AGE`, with
     `now-asof <= _MAX_AGE` unchanged.
   - The 10-second staleness limit, the receipt-age check (`quotes.py:135`) and the 60-second HTTP Date check
     (`quotes.py:136`) stay as they are.
   - Cost: with the PC up to 1 s behind, a book's age can be under-read by up to 1 s against the 10 s limit.
   - A PC clock that runs ahead is unaffected. So is the midnight Seoul-day check (`execution_accounts/provider.py:163-165`).
   - Why 1 s: about 25 times the measured offset, enough margin for a missed daily sync. It is still small next to the
     10 s freshness limit.
2. **An owner clock rule.**
   - Keep the existing sync rule: sync at hh:mm:45, or mid-bar in a study, and never within 5 minutes of 22:00 or
     midnight.
   - Before freezing or starting a study, run `.\.venv\Scripts\python.exe -X utf8 -m tools.clock_check`. Go ahead only
     if it exits 0 and `LAG_MS min` is -500 or higher, half the allowance. Otherwise sync and run it again.

## The follow-up code PR (after universe PR 5, before the final code-approve)

- **Where.** Universe PR 5 moves the book-time check into a shared `_book` helper, used by the single and the batch
  parser (`docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr5-study.md`, the `_book` block near line 472). Make
  the change there, by text, as one named module constant marked as a calibration knob:
  `timedelta(milliseconds=-1000) <= received-asof`.
- **Tests that pin today's zero bound and must move to the new edge** (1,000 ms admitted, 1,001 ms refused):
  - `tests/accounts_quotes.py:106-108`: the 1 ms future stamp.
  - `tests/launch_quote_diagnostics.py`: the future-stamp cases near lines 112, 135 and 265, which use 1 to 2 ms
    future stamps.
  - The stale cases (10,001 ms, and `accounts_quotes.py:111`) stay as they are.
- **Why it must come before the final code-approve.** `quotes.py` is in the study `CAPTURE_FILES`
  (`execution_launch/study.py:60`) and in the D14 code hash. Changing it after a study plan is frozen makes that plan
  refuse with `STUDY_CAPTURE_SOURCE_CHANGED`. So the change lands before the final code-approve and before any study
  is frozen.
- **The allowance is a signed value.** This note records the owner's choice of 1,000 ms. The code stays unsigned until
  that final approval.

## Not measured

- There was no run right after a manual sync, and no run 24 hours after one, so the drift rate is unknown.
- The pre-study check in the owner rule catches drift before it matters.
- If a later run shows `LAG_MS min` below -500, sync more often. Do not raise the allowance without a new decision.

Not legal or investment advice.
