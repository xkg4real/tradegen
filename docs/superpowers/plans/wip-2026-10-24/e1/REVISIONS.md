# E1 drafts: revisions after the critic round (2026-10-25)

Each issue was checked against the repo (main `5816d3c`, read only), the approved E1 spec rev 1, E1_RULINGS.md, the
venue research and the follow-up and odds contracts before editing. My own offline checks are in
`scratchpad/odds_plan/e1/sandbox_reviser/` (`token_probe.py`: the new Upbit, KIS and TR token rules against every
must-fail control; `seal_fix_probe.py`: the new `seal_context` passes the compliance_model round trip and still raises
TypeError and ValueError; `lock_probe.py`: a read-only handle sees another handle's `msvcrt` lock). Still 14 tasks: the
oversized Task 2 was split by moving signing and sending into Task 3 (which already held the token cache), so no task
was renumbered. New plan decisions: E36 to E41. New CONTRACT section 20 (and a header section) lists 12 open issues.

## Critic 1: order-path safety and secrets

| # | Issue | Verdict | Reason |
|---|---|---|---|
| O1 | Nothing makes transport the only way out (blocker) | fixed | E36 and the 0.5 bullets "transport is the only way out" and "no rebinding from outside": `requests`, `_send` and the hosts only in transport, a from-import allowlist, literal `"GET"` on every outside `request`, `keys` only in transport and kis_inquiry (one `keys.read(ACCOUNT_NAMES)`), credential names only in transport, explicit stdlib allowlist (no subprocess, ctypes, socket), `send`/`connect`/`getresponse`/`urlopen`, `os.system` and friends and `sys.modules` banned; `test_transport_is_the_only_path` with must-fail controls. |
| O2 | Upbit exactness vacuous, KIS check circular, lower-case TR (major) | fixed | Token rules: every `(?i)/v1/(?:order\|withdraw)...` match must equal one of the four paths; every `/uapi/...` match must be one of nine GET paths written in the test; `/trading/order`, `/trading/daytime` banned; TR shape `(?i)` with boundaries and pinned; `[A-Z]{4}[0-9]{4}U` banned everywhere; controls verified in `token_probe.py`. |
| O3 | The real `_send` never runs; redirects would leak keys (major) | fixed | Verified in the venv: `allow_redirects` defaults to True and `rebuild_auth` strips only `Authorization`. `_send` is pinned (one call, `ast.unparse` equality, no verify/proxies/auth/hooks/stream) and run for real with `transport.requests` swapped; `serve()` asserts `params is None` and `timeout == 10.0`. `trust_env` left as open issue 11. |
| O4 | KEYLESS does not make E1 keyless (major) | fixed | C5: a name present in the environment decides alone (`<unset>` is missing, the file is not read); X2's "env wins" kept and now true; key test with a temp `.env`; Task 12 proves KEYLESS with placeholders set; no `importlib.reload` (C0.2). |
| O5 | A test could run E1 in a child process (major) | fixed | C0.2 rule (CLI tests in-process, second in-process lock handle) and `test_tests_start_no_process` over `tests/execution_*.py` with controls. |
| O6 | Redaction promised but not built (major) | fixed | E37: `FieldError(name)`, error text from venue, path, type name or field name only; `(ValueError, OSError)` from `_send` wrapped `from None` (probe output confirmed `float` and latin-1 messages quote values); `Answer.body` `repr=False`; sha keys never a KIS query; `test_no_secret_reaches_any_output`. |
| O7 | `kis_client._TOKEN_PATH` fixed at import (minor) | fixed | Confirmed `data/krx/kis_client.py:53`; Task 3 asserts `_TOKEN_PATH.is_relative_to(home)` just before `_store_token`, never constructs `KISClient()` or calls `.token()`. |
| O8 | `--pending` renders unverified rows (minor) | fixed | `checks.verify_row` (keys, text_key, kind, level, venue, slot names and types, stamps); a failed row gives the fixed `UNVERIFIED` sentence once; Task 12 forged-row test. |
| O9 | Current U-suffixed order TRs caught only upper-case (minor) | fixed | `ORDER_TR` raw ban over every execution file and `(?i)` TR shape (merged with O2). |
| O10 | Token POST takes params; `Answer` repr holds the body (minor) | fixed | Step 3 refuses the KIS POST unless `params is None` (test in Task 2); `body: object = field(repr=False)` with a repr test in Task 3. |
| O11 | Signing does not stop an edited E1 from sending (minor) | fixed | Honest point added to the header; the fail-closed `ctx.code_signed` check is open issue 9 for the owner. |
| O12 | README P0 "quotations only" becomes false (minor) | fixed differently | Spec 8 says P0 stays and P0 speaks of "the macro package"; the new README bullet says E1 also reads the KIS account, so the quotation sentence describes the macro package (C17). |

## Critic 2: repo fit

| # | Issue | Verdict | Reason |
|---|---|---|---|
| R1 | `live_evidence` breaks the ctx_hash round trip (blocker) | fixed | Confirmed (`compliance_model.py:84-90`, `model.py:233`); C13.1 `seal_context` hashes every field with defaults filled in; `seal_fix_probe.py` passes the round trip, the change case, TypeError and NaN; grep found no pinned ctx_hash. |
| R2 | Snapshots swallow `Refused` and unrouted `AssertionError` (major) | fixed | E38 narrows the caught set to venue errors (so `Refused`, `AssertionError` and `checked_target` refusals propagate) and `STRAYS` fails a passing test that made a stray send; harness self-test added. |
| R3 | DRIFT list misses files; test edits anchored by line only (major) | fixed | 0.6 now lists README, compliance_store, compliance_signer, compliance_gate, the kis_client names and `_suite_names` (checked in followup/CONTRACT.md:228-245, 694-697 and odds/CONTRACT.md:578-579); 13.5 quotes each old line; line numbers are hints. |
| R4 | Header File map cut off (major) | fixed | The header's sections 0, 1, File map and Open issues are regenerated from CONTRACT sections 0, 1, 2 and 20 (`sync_header.py`); verified byte-identical. |
| R5 | Registration test is a substring check (minor) | fixed | `"execution" in CG._suite_names(text)` for run_all and README (README.md:12 already says "execution"). |
| R6 | OKX calls `public/time` before reading keys (minor) | fixed | `transport.require_keys("okx")` first (names only), so a keyless OKX makes no call; Task 7 and Task 12 tests. |
| R7 | Link-scan memo makes every path raise (minor) | fixed | Confirmed `core/isolation.py` `scan_links`; Task 12 calls `snapshot.home()` before making a link, adds the link-from-start case, and E40's direct toast covers both. |
| R8 | EXIT_LOCKED 2 contradicts spec 4's exit 0 (minor) | kept (ruling) | X7 kept as instructed; listed as open issue 1 with the recommended `EXIT_LOCKED = 0`; owner gate 3 asks for a ruling before Task 12. |
| R9 | Task 9 runs only the compliance suite (minor) | fixed | Task 9 Verify adds `<KEYLESS> --suite odds`, the T-RO-01 one-liner and the old-reason grep. |
| R10 | Harness imports `execution` eagerly (minor) | fixed | C3.1 and C3.2: `_wrap` imports the fixtures lazily, `isolated()` imports transport and keys inside the context manager. |
| R11 | owner.py docstring grows to 129 columns (minor) | fixed | Measured 114 -> 130; C13.3 and C13.4 say rewrap the docstring and the sign.py comment to 120 columns. |
| R12 | requests and its dependencies are outside the D14 hash (minor) | fixed | Honest point in the header; adding them to `_RECORD_DISTS` (owner.py:603) is open issue 10. |
| R13 | `_write_token` makes its own temp name (minor) | fixed | `_write_token(path, tmp, token, expires_at)` writes the temp path checked before the POST; Task 3 test. |
| R14 | `--pending` creates the folder; C18 preamble wrong (minor) | fixed | `--pending` reads with no lock and creates nothing; `--mark-sent` locks only when the file exists; C18 now names the first paragraph and Task 14 shows a computed diff. |
| R15 | pyproject `packages.find` omits `execution*` (minor) | ruled: no change | `.venv` holds no editable install of TRADEGEN; E41 states E1 runs only from the repo root (`-m execution.poll`, start-in the repo). |
| R16 | evidence.jsonl re-verified on every `load_context` (minor) | open issue | Kept as spec 6 says; open issue 2 gives the owner the append-on-change plus daily heartbeat option. |

## Critic 3: spec coverage and testability

| # | Issue | Verdict | Reason |
|---|---|---|---|
| C1 | EXIT_LOCKED 2 vs spec 4 (major) | kept (ruling) | Same as R8: X7 kept, open issue 1. |
| C2 | HOLDINGS alert does not list the explaining moves (major) | fixed | Int slots `fills`, `deposits`, `withdrawals` (counts only) in both templates; Task 11 mixed-case test. |
| C3 | `due` clears checks that were never evaluated (major) | fixed | `checks.evaluated()` and `due(raw, done, rows, now)`: only an evaluated group clears; Task 11 FOREIGN_ORDER flaky-poll test. |
| C4 | Link refusals become EVIDENCE_BROKEN or a not-ok venue (major) | fixed | `EvidenceBroken` for chain defects only; E38 lets `checked_target`'s RuntimeError propagate as a crash; Task 10 and Task 12 hard-link tests. |
| C5 | A refused alerts write alerts nobody (major) | fixed | E40: the toast-only `CRASH_UNLOGGED`, once per process per Seoul date; Task 12 tests for a refused alerts.jsonl and for a link present from the start. |
| C6 | The loop mode is untested (major) | fixed | `poll._sleep` seam, `poll.poll_once` and `poll.datetime` patched; crash then success then KeyboardInterrupt test with the sleep length and the lock release. |
| C7 | The R-suffix rule has no test of its own (major) | fixed | Task 2 test with `TR_IDS` patched to pin `TTTC8434U`, refused with the R reason before any key read. |
| C8 | Exactness extraction undefined, no must-fail controls (major) | fixed | Same as O2. |
| C9 | Task 2's KIS header test cannot pass (major) | fixed | Signing, sending, answers and the KIS header test moved to Task 3 with the token cache; Task 2 is keys, allowlists, refusals and guards. |
| C10 | `_send` never run; timeout unrecorded (major) | fixed | Same as O3; `serve()` records `params` and `timeout`. |
| C11 | `--pending` trusts alerts.jsonl (major) | fixed | Same as O8. |
| C12 | Header File map empty (major) | fixed | Same as R4. |
| C13 | Cited open issues have no list (major) | fixed | CONTRACT section 20 and the header's "Open issues": 12 items with defaults, including OKX autoLoan (okx.md correction 4) and the KIS overseas service (kis.md 5.2); Task 14 stops for a ruling on both. |
| C14 | Real-home watch flaky once the owner's poller runs (major) | fixed | `_poller_running()` probes the real `poll.lock` read-only (verified in `lock_probe.py`); then only paths are compared for `execution/` and the token; a file entry stats itself; self-tests for both. |
| C15 | E19 per-text_key dedupe deviates from spec 7 (minor) | fixed differently | Reverted to spec 7 and X7, `(venue, kind)`, since the rulings bind; the safer per-text_key option is open issue 4. EVIDENCE_BROKEN got its own kind `EVIDENCE` so OUTAGE recoveries do not clear it. |
| C16 | CLOCK_SKEW compares a late Date header with the poll start (minor) | fixed | E39: `Answer.received_utc` and `Snapshot.clock_offset_s`; Task 11 test with the poll start a minute before the answer. |
| C17 | Retry on Timeout goes beyond spec 5 (minor) | fixed | `ReadTimeout` no longer retried; `ConnectTimeout` still is (verified: it subclasses `ConnectionError`); tests for both. |
| C18 | not_set strings unpinned and not persisted (minor) | partly fixed | Exact strings pinned in C15.1; persistence needs a new row type or a fifth state file, so it is open issue 12. |
| C19 | Task 5 `INQR_DVSN=01 always` conflicts with call 3 (minor) | fixed | Reworded: on every inquire-balance (TTTC8434R) call. |
| C20 | Task 9 Verify misses the odds suite (minor) | fixed | Same as R9. |
| C21 | No task creates the ledger (minor) | fixed | Task 1 creates and commits it (E35, file table row). |
| C22 | "after owner act 1" ambiguous (minor) | fixed | "main-spec owner act 1 (the signing key)" in C2 and the header's owner gates. |
| C23 | C18 preamble omits the first paragraph (minor) | fixed | Same as R14. |
| C24 | `_touchpoints` not extended (minor) | ruled: not added | E41: no other suite imports `execution`, the E1 suite patches `_send`, `hermetic()` refuses every connect; the DNS residual is shared by every suite. |
| C25 | KEY_MISSING red for a never-keyed venue (minor) | fixed | E31: missing keys are "not set" (spec 7), no alert and no OUTAGE; an amber alert for a deleted KIS key is open issue 8. |
| C26 | A re-issued bad KIS token loops issuance (minor) | fixed | `_next_issue_at` replaces `_last_issue`; a re-issued bad token raises AuthError and blocks issuing for 6 hours; Task 3 test. |
| C27 | Naive Upbit `expire_at` fails every poll (minor) | fixed | A value with no offset is read as Asia/Seoul; fixture variant and Task 6 test. |
| C28 | Error text unspecified (minor) | fixed | Same as O6. |
| C29 | `--pending` creates `~/.tradegen/execution` (minor) | fixed | Same as R14; Task 12 empty-home test. |
| C30 | Nothing enforces evidence.py as the only writer (minor) | fixed | `test_only_evidence_names_evidence_path` (Task 1). |
| C31 | Task 2 too large (minor) | fixed differently | Signing, sending, answers and the KIS header test moved into Task 3 instead of a new task, so no renumbering. |
| C32 | README status bullet's "retired only through..." becomes inaccurate (minor) | fixed | The new bullet says the P0 guards are narrowed file by file for kis_inquiry.py and upbit_inquiry.py. |

## Round-2 rulings folded in (E1_RULINGS_ROUND2.md, 2026-10-25)

All twelve open issues of CONTRACT section 20 are ruled. Repo read only (main `5816d3c`: `owner.load_context` and
`_context` at owner.py:964-1017, `model.is_sealed` at model.py:238, `F.ctx` at compliance_fixtures.py:65-78, the
signed-home helpers at compliance_store.py:242-299 that the odds plan moves public). Offline checks in
`e1/sandbox_round2/`: `send_probe.py` (requests 2.34.2: `trust_env = False` gives no proxies and `verify=True` under
`HTTPS_PROXY`/`REQUESTS_CA_BUNDLE`, `.netrc` is read only when `trust_env`; the `ast.unparse` text of the new `_send`,
which `SEND_SOURCE` equals), `fold_probe.py` (change-only plus daily heartbeat gives the same E18 fold as one record
per poll on 9,780 comparisons over random histories), `due_probe.py` (the new `due` on the level-rise, HOLDINGS,
D15, co-raised, flaky-poll and NOT_SET scenarios). The header's copies of CONTRACT sections 0, 1, 2 and 20 were
regenerated with `sandbox_round2/sync_header.py` and verified identical. Still 14 tasks, no renumbering; two new
decisions (E42, E43); open-issue numbers kept, each now stating its ruling.

| Ruling | Where folded | What changed |
|---|---|---|
| E1R2-1 lock exit 0 | E7, E23, C16 (constants, 16.1), C20.1; Task 12; TASKS coverage; header owner gates | `EXIT_LOCKED = 0` with the message and no poll; argument errors stay 4; Task 12's "check whether open issue 1 was ruled" step and header owner gate 3 removed (gates renumbered 1-5). |
| E1R2-2 dedupe per text_key, level rise at once | E7, E19, C15.2 (rewritten), C20.4; Task 11 | Dedupe per `(venue, text_key)`; a red is also fresh when the group's latest non-clear row today is amber; `fresh` lists amber and info before red, so a fired red is the group's latest row and does not refire; clears per text_key whose kind was evaluated. |
| E1R2-3 evidence on change (spec rev 2) | E18, C14 (`evidence.due`, `record`), C20.2; Task 10; header "For E1 spec rev 2" | A record only on a `met` change, a first record, or the first poll of a later Seoul day; Task 10 adds the boundary tests and the equivalence test (the same polls through `record` with `evidence.due` patched to True). |
| E1R2-4 daily inquiry files (spec rev 2) | E4, E28, E30 (rewritten), E34, C2 (state files), C3.1 (`_real_listing`), C8 (`inquiry_path(day)`, `read_since` deleted), C16.2 steps 2-3, C20.3; Tasks 1, 4, 12; header | `inquiry-YYYYMMDD.jsonl` per Seoul date under one `inquiry.lock`, never deleted; a poll reads yesterday's and today's files with `read_all`; the paths-only real-home watch ignores a new daily file. |
| E1R2-5 `[assumed]` fields accepted | C3.2, C19, C20.5; Task 14 | Marked accepted; a live mismatch fails that venue closed and is fixed in a follow-up. |
| E1R2-6 OKX autoLoan strict | C19, C20.6; Task 14; header gate 4 | Task 14 stops and asks the owner on `autoLoan` true with a spot-mode key; never loosened. |
| E1R2-7 KIS overseas service | C19, C20.7; Task 14; header gate 4 | Task 14 stops and asks the owner. |
| E1R2-8 KEY_MISSING amber daily | E31 (rewritten), C15 (table row, TEXT, OUTAGE, `Prior.fails`), C19, C20.8; Tasks 11, 12, 14; header gate 5 | Amber KEY_MISSING (kind KEY_HEALTH) once per venue per Seoul day; OUTAGE and the fail streak skip `keys_missing`; KEYLESS test now expects KEY_MISSING rows. |
| E1R2-9 KIS only under signed code (spec rev 2) | new E42, E24 (rewritten), E32, C2, C3.2, C8 (`code_unsigned` flag), C9 (`snapshot(now, ctx)` gate), C15 (KIS_UNSIGNED, OUTAGE, not_set), C16.2 step 0-1, C17 README bullet and row, C19, C20.9; Tasks 5, 11, 12, 14; header honest point, "For E1 spec rev 2", gates 4-5 | `poll_once` loads the context first with the placeholder (owner state and `code_signed` do not depend on positions, owner.py:997); `kis_inquiry.snapshot` returns `failed(..., "code not signed", flags={"code_unsigned"})` unless `model.is_sealed(ctx) and ctx.code_signed is True`; one amber KIS_UNSIGNED a day, nothing else; tests use `F.ctx()` and the odds plan's public `F.pubkey_at`/`F.full_home` for a signed home; the first live KIS read waits for the owner's signature. |
| E1R2-10 requests outside the hash | header honest point, C20.10 | Stated as a limit; `_RECORD_DISTS` unchanged. |
| E1R2-11 Session with trust_env off | E3, E12, C0.5 (verb, path and rebinding rules), C4.5 (`SEND_SOURCE` replaces `SEND_CALL`, controls), C6 (`_send`), C20.11; Task 2; header honest point | `_send` = one `requests.Session()`, `trust_env = False`, one `session.request(..., allow_redirects=False)`; the guard compares the whole function; Task 2 runs it with a fake Session and checks real `trust_env` behaviour offline. |
| E1R2-12 not-set info row | new E43, E23, C2, C15 (`NOT_SET` kind and text, `ITEM_SLOTS`, `NOT_SET_ITEMS`, `row()` sent rule, `verify_row`), C16.2 steps 6-9, C16.3, C16.4, C20.12; Tasks 11, 12 | One `level: "info"`, `sent: true` row a day in alerts.jsonl naming the skipped checks; never toasted, never in `--pending`; no new file. |

Other edits made while folding:
- Precedence list (CONTRACT preamble): the round-2 rulings first, above the spec for the three spec rev 2 items.
- DRIFT RULE (C0.6, already in Global Constraints): adds the odds plan's users of `model.py`, the compliance
  fixtures E1's tests now use (`temp_home`, `ctx`, `pubkey_at`, `full_home`; stop and rule if the last two are not
  public) and a re-grep for a pinned `ctx_hash` before Task 9's `seal_context` edit (also in Task 9 and Task 1).
- Header: the "For E1 spec rev 2" block after **Spec:** (E1R2-3, E1R2-4, E1R2-9), the architecture paragraph, two
  honest points rewritten (an edit that removes both the KIS check and its tests is not stopped by anything in E1,
  said plainly), "E1 to E43", and the open-issues section retitled "Open issues, all ruled".
- TASKS: the intro names the round-2 rulings; task headings cite the rulings and decisions they implement; the
  coverage table gains one row per ruling E1R2-1 to E1R2-12.
