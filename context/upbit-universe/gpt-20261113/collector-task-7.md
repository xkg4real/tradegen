# PR 4c Task 7 — stale trade fallback to a fresh bid

Status: implementation and focused checks complete; final shared-source integration pending.

## Implemented

- A listed holding whose last trade is older than 30 seconds reads one level-zero orderbook after the race rereads.
- Marks at the best bid only when the book is at most 10 seconds old and not from the future.
- Added read remains within the existing full-capture 30-second budget and final receipt fencing.
- Fresh ticker marks and zero unlisted marks retain their separate paths.
- Updated stale-ticker test to require stale/future/empty-book refusal and added fresh-best-bid test.

## Verification

- RED: **0 PASS / 2 FAIL**, exactly COLLECTOR_TICKER_STALE_OR_FUTURE vs expected book fallback/refusal.
- GREEN: collector + interval + continuous + guards + provider: **104 PASS / 0 FAIL / 0 NOT_RUN**.
- Logs: collector-task-7-red.log and collector-task-7-green.log.
- After the reviewed Task6 listing correction, the same focus set plus 2 regressions passed **106/106** (`collector-listing-hardening-green.log`).
- Implementation follows quoted plan; no additional pinned initialization surface change.

## Conditions

- Base main `971a5389208c85d34fdd6479c96580e9b8fcc68d`; shared worktree, no commit/stage/push by this worker.
- Offline wrappers, 19 KEYLESS variables, explicit scratch runs and matplotlib directories; existing venv only.
- No real service/API, credentials, signing, arming, owner state or order used.
- Source files remain LF. `tests/launch_account_interval.py` was CRLF at base and remains entirely CRLF.
- Scoped diff stats match with and without `--ignore-cr-at-eol`. Plain `diff --check` flags the retained CRLF terminators as whitespace; no added spaces before those terminators.
- Parent owns the reviewed renewal surface pin and final stable integration run.
