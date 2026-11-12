# PC clock against Upbit orderbook stamps: measurement and decision (2026-11-12)

Status: owner decision, 2026-11-12. The outcome is **a signed 1-second allowance in `execution_accounts/quotes.py`
plus an owner clock rule**. The code change is not made here. It is a small code PR after universe PR 5 and before
the single final code-approve. Line numbers below are on main `0757542`.

Updated the same day with the owner's second run. The first version said run 1 came about 14 hours after the last
sync. That was wrong: the Windows Time-Service log shows a sync at 09:02 KST, most likely minutes before run 1. The decision is
unchanged.

## The rule in question

`parse_orderbook` refuses a book whose stamp is later than the PC receipt time:
`timedelta(0) <= received-asof <= _MAX_AGE` (`execution_accounts/quotes.py:155-156`, code
`QUOTE_BOOK_STALE_OR_FUTURE`). The book stamp comes from Upbit's clock and the receipt time from the PC clock. So a PC
clock that runs behind Upbit by more than the book's stamp-to-receipt lag loses that read.

In a study this is fatal, not a lost slot. A refused probe read fails as `STUDY_PREWINDOW_PROBE_FAILED`
(`execution_launch/study.py:369`). Inside the window, the first refusal ends the trial for every candidate, and nothing
is backfilled (`execution_launch/study.py:15`, `:355-358`).

## Measurement

The owner ran `tools/clock_check.py` (PR #26) twice on their PC on 2026-11-12. Each run made 20 public KRW-BTC
orderbook reads, 1 s apart. The Windows Time-Service log shows a sync at 09:02 KST (events 37 and 35). PR #26 merged
at 09:03 KST, so run 1 most likely came within minutes of that sync. Run 2 came later that morning, before 09:49 KST.

Run 1:

```
CLOCK_CHECK symbol=KRW-BTC samples=20/20 admitted=18 reason=none
LAG_MS min=-4 median=64 max=879
DATE_MS min=24 median=548 max=926
RTT_MS min=342 median=440 max=735
REFUSED QUOTE_BOOK_STALE_OR_FUTURE=2 QUOTE_RECEIPT_STALE_OR_FUTURE=0 QUOTE_SERVER_CLOCK_MISMATCH=0
W32TM status=unavailable
```

Run 2:

```
CLOCK_CHECK symbol=KRW-BTC samples=20/20 admitted=19 reason=none
LAG_MS min=-10 median=65 max=968
DATE_MS min=19 median=349 max=945
RTT_MS min=347 median=378 max=805
REFUSED QUOTE_BOOK_STALE_OR_FUTURE=1 QUOTE_RECEIPT_STALE_OR_FUTURE=0 QUOTE_SERVER_CLOCK_MISMATCH=0
W32TM status=unavailable
```

What it shows:

- **The PC clock is behind Upbit, even right after a sync.** For every read, lag = (PC minus Upbit offset) + (book
  staleness + network delay). The second term is never negative, so the offset is at most `LAG_MS min`. That value
  is floored to whole ms: the PC was at least 3 ms behind in run 1 and at least 9 ms behind in run 2.
- **3 of 40 reads (7.5%) were refused** for that reason alone.
- **There is no sign of a large offset.** The HTTP Date header has one-second resolution. In both runs its offsets
  spread over about 20 to 950 ms, which fits an offset of tens of milliseconds at most.
- **`W32TM status=unavailable` means the Windows time service was stopped,** not that `w32tm` is missing. A read-only
  check the same morning found the service `Stopped` with start type `Manual` (trigger start), and `w32tm` answered
  0x80070426. The `SynchronizeTime` scheduled task last ran on 2026-11-11 at 19:08 KST with result 0, and the service
  also synced at 09:02 KST on 2026-11-12. It is off between syncs.
- RTT includes a new connection per request and local processing. It is not the network round trip.

## Why the strict rule cannot stand

A study reads one book per slot, and one refusal ends it. A 48-hour study at 300 s bars makes about 578 reads.

| Per-read refusal rate | Chance all 578 reads pass |
|---|---|
| 7.5% (as measured, 3 of 40) | about 0 |
| 1.6% (low end of the 95% interval for 3/40) | about 0.01% |
| 0.1% | about 56% |

Syncing alone does not fix this. Both runs most likely came within an hour of a sync and still had refused reads. NTP over the
internet sets the clock to within tens of milliseconds, either side of zero, and a clock only a few milliseconds behind
already refuses reads.

## Decision

1. **A signed allowance of 1,000 ms for a book stamped after the PC receipt.**
   - Only the lower bound of the book-time check changes: `-allowance <= received-asof <= _MAX_AGE`, with
     `now-asof <= _MAX_AGE` unchanged.
   - The 10-second staleness limit, the receipt-age check (`quotes.py:135`) and the 60-second HTTP Date check
     (`quotes.py:136`) stay as they are.
   - Cost: with the PC up to 1 s behind, a book's age can be under-read by up to 1 s against the 10 s limit.
   - A PC clock that runs ahead is unaffected. So is the midnight Seoul-day check (`execution_accounts/provider.py:163-165`).
   - Why 1 s: it is far above the measured offset (tens of milliseconds at most), with margin for a missed daily sync.
     It is still small next to the 10 s freshness limit.
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

- There was no run 24 hours after a sync, so the drift rate is unknown. The two runs give only upper bounds on the
  offset (-3 ms, then -9 ms), and upper bounds do not measure drift.
- The pre-study check in the owner rule catches drift before it matters.
- If a later run shows `LAG_MS min` below -500, sync more often. Do not raise the allowance without a new decision.

Not legal or investment advice.
