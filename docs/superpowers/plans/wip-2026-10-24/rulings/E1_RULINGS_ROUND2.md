# Controller rulings on the E1 contract's open issues (round 2, 2026-10-25)

These amend E1_RULINGS.md. Apply them to e1/CONTRACT.md, e1/TASKS.md and e1/header.md before drafting tasks; where a
contract and this file disagree, this file wins. Items marked "spec rev 2" are departures from the approved E1 spec
rev 1 and must be listed in the plan header under "For E1 spec rev 2" so the owner sees them.

- E1R2-1 A second poller exits 0 with a message (spec 4 wins over X7): `EXIT_LOCKED = 0`.
- E1R2-2 Alerts dedupe per (venue, text_key) per Asia/Seoul date, and a level rise (amber to red) for the same venue
  and check always fires at once. An amber HOLDINGS_EXPLAINED never hides a red HOLDINGS_UNEXPLAINED, nor D15_LOAN a
  D15_EARN.
- E1R2-3 (spec rev 2) evidence.jsonl appends a record for a requirement only when its `met` value changes, or when the
  last record for that requirement is dated on an earlier Asia/Seoul date (a daily heartbeat on the first poll of each
  Seoul day). The lifting, re-blocking and 7-day expiry rules of spec 6 are unchanged; tests prove the fold gives the
  same `live_evidence` as one record per poll would on the same history.
- E1R2-4 (spec rev 2) inquiry records go to daily files `execution/inquiry-YYYYMMDD.jsonl` (Asia/Seoul date of the
  poll); nothing is ever deleted; E30's "from 00:00 yesterday" read opens only yesterday's and today's files.
- E1R2-5 Fixture fields marked [assumed]: accepted; the owner-gated first live poll (Task 14) is where a mismatch shows,
  and it fails that venue closed.
- E1R2-6 OKX `autoLoan`: the check stays strict (spec 5). If the first live poll shows `autoLoan` true on a spot-mode
  key, Task 14 stops and asks the owner; it never loosens the check itself.
- E1R2-7 KIS overseas service not enabled: Task 14 stops and asks the owner, as the contract says.
- E1R2-8 Missing keys raise an amber KEY_MISSING alert, once per venue per Seoul day (so a key deleted from .env shows).
- E1R2-9 (spec rev 2, stricter) KIS inquiry sends nothing unless `ctx.code_signed is True` in that poll's context:
  the KIS key can trade, so only owner-signed code may hold it on the network. Upbit and OKX (read-only keys) poll
  regardless. Until owner acts 1 and 2, the KIS snapshot is `ok: false` with error "code not signed" and no alert
  beyond one amber KIS_UNSIGNED a day.
- E1R2-10 requests, urllib3, certifi, idna and charset_normalizer stay outside the D14 hash, as spec 6.4 accepts for the
  venv; the plan header states it as a limit.
- E1R2-11 `_send` uses a `requests.Session()` with `trust_env = False` (no proxies, no REQUESTS_CA_BUNDLE, no .netrc)
  and `allow_redirects=False`; the guard pins that exact call.
- E1R2-12 "Not set" checks: one info-level row per Seoul day in alerts.jsonl (`level: "info"`, `sent: true`, never
  pushed) naming the skipped checks; no new file.
