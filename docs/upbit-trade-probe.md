# A0 public trade-list measurement

`tools/research/upbit_trade_probe.py` implements the independent measurement step
in [PR #65 section 7](https://github.com/xkg4real/tradegen/pull/65), based on spec
commit `761416705cb3ed5fc5450a0c8d88b118f9192c8f`. It is outside the D14 and
capture closures. No app, account, signing, order, or activation module is imported.
It does not change A1/A2, the loss policy, or an existing research bundle.

## Run on the measurement PC

Use a fresh output directory in the day's records folder. Do not place observations
inside an owner home, the repository, or a signed research bundle. Example from the
repository root in PowerShell (replace the output folder with the chosen folder):

```powershell
.\.venv\Scripts\python.exe -B tools\research\upbit_trade_probe.py --market KRW-BTC --output "<records-folder>\upbit-a0-BTC" --cycles 1000 --allow-public-network
```

This performs public GET requests only. `--allow-public-network` is mandatory;
without it nothing is requested or written. No key, account, `.env`, or token is
read. Do not supply any credential. The fixed host is `https://api.upbit.com`,
redirects and ambient proxy configuration are disabled, and only the trade-list,
ticker and one-minute-candle paths are available. A trailing-slash diagnostic is a
single additional request per session, enabled only by `--probe-trailing-slash`.

The default pacing is two requests per second. The configurable maximum is five,
including all pages and the diagnostic. This is a per-process start-to-start
ceiling, **not an IP-wide budget**: coordinate QUANTGEN or other readers sharing
the IP. Do not run several probe processes together to increase throughput.
HTTP 429 or 418 records the response and `Retry-After`, then stops the entire run.
It does not force a rate-limit condition or retry automatically. Before restarting,
honour the recorded wait and diagnose other readers. No 429/418 observation means
that behaviour is unobserved, not tested successfully on the venue.

### Windows PC with changing public IPs (OQ17)

On each cooperating public-probe command, add this option using the same
ordinary folder on a local disk. For example, in PowerShell use
`--coordination-dir "$env:LOCALAPPDATA\TRADEGEN-A0\public-budget"`. Keep the
directory stable across market, output-folder, router, VPN and hotspot changes.
Use a local folder outside OneDrive or another sync service. The probe never
looks up, records or switches the public IP. A second cooperating run exits
before its first request while a session owns this directory.

A 429 or 418 stops the run and persists a hold in `upbit-public-cooldown.json`.
With a usable `Retry-After`, later runs refuse before making any requests until
the deadline (UTC Unix seconds). HTTP-date values also require a valid response
`Date` to account for clock skew. Keep the PC clock accurate. When the wait
is unknown or the marker is malformed, later runs report
`PUBLIC_BUDGET_REVIEW_REQUIRED`. A process kill or failed hold write can leave
`upbit-public-session.lock` and cause `PUBLIC_BUDGET_BUSY_OR_UNREVIEWED`.
For manual recovery, verify that all participating runs have stopped, preserve
the marker and measurement evidence, and check the provider's current
restriction. Remove a stale lock or unresolved marker only after confirming
collection can resume. A valid timed hold expires automatically on the next run.

QUANTGEN, another PC, or a reader using a different directory can still consume
the same venue allowance. Agree on one measurement window or allocate a
conservative combined request budget across those readers whenever they may
share a network. A network change alone never clears the hold. Omitting this
option preserves the per-process behaviour described above.

`--cycles` is finite (default 1), `--max-pages` bounds each UTC-day walk (default
20), and `--pause-seconds` pauses between completed cycles (default 5). Run around
09:00 KST to gather a UTC-day boundary example, and for hours or days if needed.
Actual cycle duration includes six separate measurements and can substantially
exceed five seconds. Ctrl+C records an interruption when storage is available.

## What is measured and preserved

Every response retains the exact bytes in base64, SHA-256, allowed headers, request
parameters, send/receipt times and monotonic latency in `observations.jsonl`.
HTTP `Date` offset is relative to the local request midpoint, with an explicit
one-second quantisation allowance plus half the measured latency. It is an
observation, **not a trusted clock synchronisation or a latency proof**.

Each cycle samples three separate fresh half-open intervals `[S,E)`, one per
SETTLE target (0.5, 1 and 2 seconds). For each target it schedules the first
trade-list read, then reads **that same interval again later** to check stability.
The future E leaves room for the preceding ticker read and rate pacing. This
avoids an impossible schedule in which six serialized reads of one interval would
make every later target late even on a fast connection. The three different
target groups have different intervals; their raw trade lists are never compared
as if they covered one window. This is a measurement design choice, not an A1/A2
policy change.

The probe records the unit's starting offset, the **actual first trade-list
request** offset and the last page's receipt time. A fixed 0.1-second tolerance
reports `trade_settle_target_met`. Slow responses or rate pacing can still miss a
first-read target; those remain marked as missed. The second read is explicitly a
later observation, not a second simultaneous read at the target. Compare actual
offsets and the recorded pair's stability when analysing settlement delay.

Each measurement contains ticker first, the bounded trade walk, and one lagging
minute candle. Trade pages request `count=500`; subsequent cursors use the last
received row's identifier, without treating numeric identifiers as chronological.
The walk retains duplicate and conflicting-ID checks, filters `[S,E)`, and records
whether it reached a prior trade or an empty page before the page cap. At 09:00 KST
it reads both UTC days and verifies `days_ago` against the response Date. It omits
`days_ago` for the current day rather than assuming a wire value of 0 is supported. At the
last UTC second it omits ambiguous `to` instead of wrapping it into the same day's
00:00. A local/server day disagreement stops and preserves the response.

The probe records:

- Repeat-window differences, pages, ticker matches inside the observed walk's
  comparable range, and the first locally observed receipt of each trade.
- Prices sharing a millisecond as an **unordered set**, with raw rows retained.
- ASK/BID counts. Which participant `ask_bid` represents remains
  `UNRESOLVED_WITH_PUBLIC_ONLY_DATA`; the tool does not manufacture own-fill proof.
- Candle equality within each pair's observed window, only when both responses
  identify the requested target minute. A sparse market's older candle is marked
  as a target mismatch; missing candles remain unknown. Stability is not a
  guarantee of future finality. Earlier candles can change.
- Public-read unit duration (excluding the deliberate SETTLE scheduling wait,
  retaining rate pacing) and whether it exceeds the five-second monitor budget;
  total measurement duration and the excluded wait are also retained.
  **Whole account/commit/owner-read duration is NOT_MEASURED**. This probe
  cannot establish that the full production monitor or slot fits its envelope.
- Optional trailing-slash rejection, naturally occurring HTTP errors, and whether
  the chosen interval crossed 09:00 KST.

Page-limit exhaustion, a ticker mismatch, changed repeated windows, or an observed
public read taking more than five seconds produces `NO_GO_OBSERVED` for that cycle.
Otherwise the result is `REVIEW_REQUIRED`. Every output keeps `source_complete`
and `execution_ready` false. There is no automatic GO: source completeness,
settlement latency, candle finality, full unit timing and the interpretation of
ASK/BID require review and any additional evidence identified by that review.

## Resume and failure handling

Rerunning with the same output directory and identical configuration validates the
entire existing sequence/hash chain before appending a new session. It never
overwrites old responses or turns a failed session into a success. Another writer
is refused. The response limit is 2 MiB, one log row is bounded, the log is limited
to 1 GiB, and a session keeps at most 200,000 first-observed trade identifiers.
Rotate into a new output directory for additional observations.

An interrupted partial row is retained and refuses resume. Preserve that directory
and start a new one. An abrupt process kill may leave `.probe.lock`; verify that
the process is no longer running before preserving the old directory and starting
a new one. Do not edit or truncate the old evidence to make resume pass. A hash
chain detects accidental changes only; this measurement archive has **no trusted
signature, independent backup, or protection from a malicious local writer**.
It is not an approved research archive and does not replace PR5 storage.

Transport and format failures retain their received evidence where available and
use fixed diagnostic codes. A short body compared with `Content-Length`, or an
incomplete chunked response, is recorded as `HTTP_BODY_INCOMPLETE` and stops the
session before JSON can be used, even if the partial bytes form valid JSON.
`Content-Length` and `Transfer-Encoding` are retained with the response headers.
Only the bounded prefix exposed by the HTTP library can be saved; for a chunked
failure this may exclude bytes from the unfinished chunk. A body read failure
without available bytes records empty bytes, retained headers and
`HTTP_RESPONSE_FAILED`; this does not claim the socket received an empty body.
Protocol failures before headers use `TRANSPORT_FAILED`. Raw exception text is
never retained. A storage failure stops collection; it does not
promise to log to storage that is failing. Paths involving `.tradegen` or
`.nextgen`, symlinks/reparse points and multiply linked log files are refused.

## Offline validation

```text
python -B -m unittest tools.research.test_upbit_trade_probe -v
```

The tests use synthetic responses, an injected clock, temporary directories and a
socket connection guard. They exercise pagination, UTC-day crossing, repeat reads,
rate limits, shared-run contention, cross-session cooldown expiry and manual
holds, partial writes/resume, response bounds, transport restrictions and
truthful refusal/incomplete output. Venue measurements and Windows native execution
must be reported separately. No real API request is needed for this test command.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
