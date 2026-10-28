# Rulings for the E1 (read-only account inquiry) implementation plan (2026-10-24)

Binding inputs for the E1 contract drafter. The spec is `docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md`
(rev 1, committed 5816d3c, APPROVED by the owner on 2026-10-24). The spec wins over these rulings except where a ruling
fills a gap the spec leaves. Repo facts: `map/execution_ctx.md`, `map/DIGEST.md` section 9, and the venue research in
`venues/kis.md`, `venues/upbit.md`, `venues/okx.md` (each has a skeptic "Verification" section at its end; where the
skeptic says WRONG, the skeptic wins).

## X1 Order of plans and drift (controller)
- E1 executes THIRD: after the compliance follow-up and the odds plan have merged. Branch `e1-account-inquiry` from the
  main of that day.
- The plan is written against main 5816d3c. The follow-up changes core/compliance/rules.py, owner.py, alerts.py,
  tests/compliance_guards.py, tools/signer/sign.py, data/krx/kis_client.py; the odds plan changes rules.py, owner.py
  (calendar_in_force), gate.py (grey_rows), tests/compliance_fixtures.py, tests/run_all.py and README. So every E1 Edit
  of those files must be written as "find this anchor (function or block, quoted) and make this change", and the plan's
  Global Constraints carry a DRIFT RULE: before each Edit, re-read the file; if the quoted old text differs only because
  an earlier plan changed it, apply the same change to the current text, keep every earlier plan's behaviour, and record
  a one-line ruling in the execution ledger; if the change no longer makes sense, stop and rule.
- The suite-list literal guard (tests/compliance_guards.py:483-489) is loosened by the follow-up plan, so E1 only adds
  "execution" to the --suite help and the README list.

## X2 Package and imports (spec 4)
- `execution/__init__.py` 0 bytes. Files exactly as spec 4 lists; tests in `tests/execution_*.py`.
- Imports: stdlib, `requests`, `core.isolation`, `core.compliance.*` only. `alerts._toast` is reached through the module
  (`from core.compliance import alerts` then `alerts._toast(title, body)`) so tests patch one seam; it is a documented
  cross-package use of a private seam.
- `keys.py`: a stdlib `.env` reader of the repo-root `.env` (`Path(__file__).resolve().parents[1] / ".env"`): lines
  `KEY=VALUE`, optional `export `, surrounding single or double quotes stripped, `#` full-line comments; no variable
  expansion. Returns only the requested names; a missing or blank value raises `KeyMissing(name)` (names only in the
  message). An environment variable of the same name wins over the file (so tests and the Task Scheduler can override).
  It never logs or returns a value to anything but transport.

## X3 Transport (spec 5)
- One public `request(venue, method, path, params=None, *, tr_id=None) -> Answer` (Answer: frozen dataclass with
  `body` (parsed JSON), `server_utc` (aware datetime from the `Date` header or None), `sha256` (hex over the raw body
  bytes)). The seam is `transport._send(method, url, *, headers, params, json_body, timeout) -> (status, headers, body_bytes)`
  using `requests.request` (never `data.net.session`, which may retry a POST that never reached the server).
- Allowlists: three frozensets of `(method, path)`, one frozenset of `(path, tr_id)` for KIS, and the host per venue.
  Exactly the endpoints in spec 5's three tables (no more). The KIS token POST is the only non-GET entry.
- Retry: a GET at most once more after 2 s on a connection error, HTTP 429 or 5xx; never a POST.
- Pacing per venue: KIS at most 5 requests/s; Upbit and OKX at most 5 requests/s (well under their limits).
- KIS token: read and write the SAME file and format as `data/krx/kis_client.py` (`state_root()/kis_token.json`,
  `{"access_token": ..., "expires_at": <epoch seconds>}`; reuse when `now < expires_at - 120`), compute
  `checked_target` BEFORE the POST, write atomically (tmp + os.replace, both checked), and issue at most once per 70 s
  per process (a module-level last-issue time). E1 must not import kis_client; a test proves both read each other's
  file.
- Upbit JWT: HS512 built with stdlib hmac/hashlib/base64/json (no PyJWT), payload `{"access_key": ..., "nonce":
  str(uuid4())}`; when the request has parameters, also `"query_hash"` = SHA512 hex of the UNENCODED query string and
  `"query_hash_alg": "SHA512"`. Build that string once as `"&".join(f"{k}={v}" for k, v in params)` over an ordered
  list of pairs (array parameters as repeated `key[]=value` pairs), hash it, and send exactly the same string as the
  URL query (E1's parameters are ASCII dates, numbers and fixed words, so no encoding differs). Reuse nothing from
  data/crypto (its `upbit_jwt` lives in data/, outside E1's import rule).
- OKX signature: Base64(HMAC-SHA256(secret, timestamp + "GET" + requestPath-with-query + "")), timestamp ISO-8601 UTC
  with milliseconds and "Z"; refuse to send when |PC clock - OKX server time| > 25 s (from the last `public/time`).

## X4 Snapshots, positions, evidence (spec 6)
- Canonical JSON = `core.compliance.model.canonical_json`; hashes sha256 hex.
- `inquiry.jsonl`, `evidence.jsonl`, `alerts.jsonl` appended under an OS lock (reuse the sidecar-lock helper pattern of
  owner.append_system_entry: msvcrt on Windows, fcntl elsewhere; copy it into execution/ if it is private) with fsync;
  `poll.lock` is a separate exclusive lock held for the poller's lifetime.
- evidence.jsonl chain format mirrors the owner log's system lines: `{seq, prev_sha256, utc, requirement, met,
  value_krw, snapshot_sha256}` plus `row_sha256` over the canonical JSON of the other fields; seq starts at 1;
  prev_sha256 of the first line is 64 zeros.
- The fold that turns evidence lines into `live_evidence` lives in `core/compliance/owner.py` as a pure function
  `evidence_in_force(lines, today) -> frozenset[str]` (today = Asia/Seoul date of load_context's `now`), and
  `load_context` reads the file (path `core.isolation.state_root()/"execution"/"evidence.jsonl"`, refused links handled
  as for the owner log). A missing file = frozenset().

## X5 Compliance changes (spec 8)
- `model.Context` gains `live_evidence: frozenset = frozenset()` (default keeps every existing constructor call valid).
- `gate.py`: the D16 block (`if row.requires_live:` ... "needs live broker evidence (execution spec)") becomes: block
  unless `set(row.requires_live) <= ctx.live_evidence`; the reason names the missing items sorted:
  `f"needs live broker evidence: {row.id}: {', '.join(missing)}"`. Update the exact-reason tests that pin the old text.
- `owner.code_files` seeds add `execution/*.py` (non-recursive, like the others); tools/signer/sign.py's copy changes in
  lockstep; tests/compliance_store.py:137-150 and tests/compliance_signer.py:638 expectations add the execution files
  and still exclude config.py, data/, core/quant/, core/calendars/, core/engine/.

## X6 Guards (spec 8)
- `tests/acceptance.py` (CRLF!) `runtime_py()` adds `execution/**/*.py`. Check every caller of runtime_py (T-RO-01,
  test_08, test_09, and any other) still passes with the exceptions below, and add the positive control.
- T-RO-01 (`tests/macro_m0_harness.py`, LF): a per-file exception map
  `{"execution/kis_inquiry.py": {"CANO", "ACNT_PRDT_CD", "KIS_ACCOUNT", <the /trading/ path regex>},
    "execution/upbit_inquiry.py": {"/v1/orders", "/v1/withdraws"}}` applied ONLY to the text checks named; every other
  check (imports, calls, mutating HTTP) still runs on those files. test_09 (tests/acceptance.py) gets the same KIS
  exception for that one file. The exactness tests of spec 8 (every /trading/ path in kis_inquiry.py is allowlisted, every TR
  string ends in R and is pinned, no order path words; Upbit strings only inside the four exact paths) live in
  `tests/execution_guards.py`.
- `tests/execution_guards.py` also: the X2 import allowlist; no `.post/.put/.patch/.delete/.request` call in
  execution/ except `requests.request` inside `transport._send` and nothing else; no wall clock outside `poll.main()`;
  every write preceded by checked_target; private_key/seed_phrase raw ban; def-name ban; `execution/__init__.py` 0
  bytes; no import of `data.*`, `config`, `core.engine.*`.
- `core/ficc/context_log.py` ACTING_MODULE_PREFIXES adds `"execution."`; check T-CTX-01 still passes.

## X7 Checks, alerts, poller (spec 7)
- `checks.py` pure: `run_checks(prev, new, owner_state_view, limits, now) -> list[Alert]`; the sentence catalogue is a
  dict `TEXT[text_key] -> str.format template` whose slots are ints, venue names, kinds and ISO times only; a test scans
  every template and every produced slot for digits-with-currency patterns and address-like strings.
- Once-per-day: an alert kind fires at most once per (venue, kind) per Asia/Seoul date unless a later poll on that date
  cleared it; the state comes from `alerts.jsonl` itself (no separate file).
- `poll.py`: `main(argv)`; `--once`, `--interval-min` (int 1..60, default 5), `--mark-sent <utc>` (marks rows with that
  exact utc sent; idempotent); exit codes 0 ok, 2 another poller holds the lock, 4 crash in --once. The loop catches
  every exception per poll.
- The 09:05 daily task prompt change is the LAST task's owner gate: the plan prints the exact new prompt text and stops
  for the owner's approval; Claude never edits the scheduled task without that approval.

## X8 Tests (spec 9)
- Suite `execution` mirrors tests/compliance_acceptance.py; `_wrap` adds a nested patch of `execution.transport._send`
  with a refusing stub, and of `core.compliance.alerts._toast` with a recorder; a probe test proves an unpatched send is
  refused.
- Synthetic venue responses are Python dicts in `tests/execution_fixtures.py`, shaped like the official docs' examples
  (field names exactly as in the research tables), never captured from a live account.
- Test budget: the suite under 60 s.

## X9 Owner acts and the first live poll
- The plan's final task lists the six owner acts of spec 12 verbatim, and says the first live poll (`--once`) is run by
  Claude only after the owner says the keys are in `.env`, and only as `--once`, printing a redacted summary (venues,
  counts, ok/error, no balances).
