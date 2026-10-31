# E1 account inquiry execution ledger

Branch `gpt/execution-e1-e3`, based on merged main `f5503d6`. Owner approved PR #4 and #5 and requested E1 through E3 development on 2026-10-31. This ledger records software and hermetic verification; owner signing, live polls, scheduler configuration, arming and real orders are not performed.

## Drift rulings

- Task 1: Cloud uses Python 3.13.16 in `/workspace/.venvs/tradegen`, the existing 19-variable KEYLESS environment and temporary state. Post-odds registration anchors retain the odds suite. Existing CRLF files remain CRLF; exact byte-anchored edits substitute for the unavailable Edit tool.
- Task 1: To implement the owner's rapid parallel-development request, disjoint tasks were built concurrently against the binding interface contract. Shared fixtures/guards were merged by the controller, then all 228 tests ran serially. Tasks 1–12 are saved as one integrated source checkpoint instead of committing intermediate dependency-incomplete trees; all task ownership and individual counts remain recorded below.
- Task 3: Added a fail-closed correction for non-finite, Boolean, nonpositive or malformed token expiration values. Two regressions failed before the fix, then all 30 transport tests passed. Cases remain inside existing test functions; count unchanged.
- Task 4: The directory-link refusal test calls existing `compliance_fixtures.directory_link`, so Linux exercises an actual symbolic link instead of skipping a Windows-only junction test. Count unchanged.
- Task 9: No owner public-key file exists. Signed closure seeds include `execution/*.py` in owner and signer in lockstep. Search found no pinned Context-derived hashes. Existing odds calendar behavior is preserved.

## Deferred minors

- Task 5: Inquiry uses bounded first pages and KIS US holdings scope; this is not complete authoritative fill reconciliation for E2/E3. A cash-order endpoint alone does not establish that a broker account has borrowing disabled.
- Task 7: OKX inquiry requires an exact read-only key. Trading credentials need their own reviewed boundary; E3 must not weaken this self-check. An algo row without a usable price fails closed.
- Task 8: Empty E1 holdings can produce zero equity; execution entry admission must handle the compliance gate's positive-equity requirement explicitly.
- Task 10: Accepted judge non-finite/negative totals emit unmet evidence; the Seoul heartbeat compares dates for inequality, including clock reversal.
- Task 11: E1's inherited floor-at-equality condition is an alert only. It must not be reused as the new equity-policy entry boundary. Targets cannot enlarge loss budgets.
- Task 12: Test-only context memoization per Seoul date retains the plan's ponytail comment; unsigned-code test still reads the real context. Clock reversal caps sleep to one interval; five lock probes and real hard-link refusal cases remain intact.
- Task 14: Owner-held keys, code signature, approvals, scheduler setup and live polls remain unperformed. No credentials or real account data were accessed during development.

## Round-2 rulings as applied

- E1R2-1 (Task 12): `poll.EXIT_LOCKED = 0`; a second poller prints the lock message, exits 0 and polls nothing
  (`test_a_second_poller_exits_0_and_polls_nothing`); argument errors stay 4.
- E1R2-2 (Task 11): `checks.due` dedupes per (venue, text_key) per Asia/Seoul date, and an amber-to-red rise fires
  at once (`test_due_fires_once_per_venue_and_text_key_per_seoul_day`, `test_due_a_level_rise_fires_at_once`).
- E1R2-3 (Task 10, spec rev 2): evidence.jsonl gets a record on a `met` change or as the first poll's daily
  heartbeat, and the fold gives the same live_evidence as one record per poll
  (`test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll`,
  `test_the_first_poll_of_the_next_seoul_day_is_a_heartbeat_for_every_judged_item`).
- E1R2-4 (Tasks 4 and 12, spec rev 2): one `inquiry-YYYYMMDD.jsonl` per Seoul date, never deleted; a poll opens
  yesterday's and today's only (`test_two_seoul_days_land_in_two_files_under_one_lock_file`,
  `test_each_seoul_day_has_its_own_inquiry_file_and_a_poll_reads_two`).
- E1R2-5 (Tasks 5, 6 and 7): the `[assumed]` fixture fields are accepted; a missing or malformed field fails that
  venue closed and names only the field (`test_a_missing_or_malformed_field_fails_closed_with_its_name`,
  `test_a_malformed_field_fails_closed_with_names_only`); a live mismatch is Task 14's to record.
- E1R2-6 (Task 7): the OKX self-check stays strict on autoLoan
  (`test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip`); a spot-mode key (acctLv 1)
  with autoLoan true is Task 14's stop-and-ask, never a loosening.
- E1R2-7 (Task 14): no code; KIS overseas calls that fail because the overseas service is not enabled are Task 14's
  stop-and-ask.
- E1R2-8 (Tasks 11 and 12): one amber KEY_MISSING per venue per Seoul day, never an OUTAGE
  (`test_missing_keys_alert_once_a_day_never_as_an_outage_and_clear_when_ok`,
  `test_keyless_signed_home_sends_nothing_and_alerts_key_missing`).
- E1R2-9 (Tasks 5, 11 and 12, spec rev 2): KIS sends nothing, the token POST included, unless the poll's sealed
  context has code_signed True; one amber KIS_UNSIGNED a day
  (`test_kis_sends_nothing_and_reads_no_key_unless_the_code_is_signed`,
  `test_unsigned_kis_alerts_once_a_day_and_nothing_else`,
  `test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day`).
- E1R2-10 (plan header): requests, urllib3, certifi, idna and charset_normalizer stay outside the D14 hash, stated
  as a limit in the header; owner._RECORD_DISTS is unchanged on this branch.
- E1R2-11 (Task 2): `_send` opens one requests.Session() with trust_env False and sends with allow_redirects=False,
  pinned by the guard (`test_send_is_pinned`, `test_send_opens_one_session_with_trust_env_off_and_no_redirects`).
- E1R2-12 (Tasks 11 and 12): one info-level NOT_SET row a day in alerts.jsonl, sent true, never toasted and never
  pending (`test_due_writes_the_not_set_row_once_a_day_and_never_clears_it`,
  `test_the_not_set_row_is_written_once_a_day_and_never_sent`).

## Runs

- Task 1: 2026-10-31T14:59:34+09:00, guards/package/registration; execution_guards 24/24, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 2: 2026-10-31T14:59:34+09:00, keys/allowlist; execution_keys 9/9, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 3: 2026-10-31T14:59:34+09:00, transport/token; execution_transport 30/30, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 4: 2026-10-31T14:59:34+09:00, snapshot/JSONL; execution_snapshot 17/17, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 5: 2026-10-31T14:59:34+09:00, KIS inquiry; execution_kis 19/19, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 6: 2026-10-31T14:59:34+09:00, Upbit inquiry; execution_upbit 11/11, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 7: 2026-10-31T14:59:34+09:00, OKX inquiry; execution_okx 18/18, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 8: 2026-10-31T14:59:34+09:00, live positions; execution_positions 13/13, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 9: 2026-10-31T14:59:34+09:00, compliance evidence fold; execution_evidence 22/22, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 10: 2026-10-31T14:59:34+09:00, evidence writer; included in execution_evidence 22/22 (8 fold +14 writer cases), PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 11: 2026-10-31T14:59:34+09:00, poll checks; execution_checks 43/43, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 12: 2026-10-31T14:59:34+09:00, poller/alert CLI; execution_poll 22/22, PASS in serial E1 run. Plan-source/diff self-review complete.
- Task 12: integrated E1 run: 228/228 PASS, 0 FAIL, 0 NOT_RUN. Root command: `python -m tests.execution_acceptance` under KEYLESS and hermetic wrapper. Full inherited regression follows in Task 13.

- Task 13: full run (KEYLESS) 1584/1706 passed, 0 failed, 122 not run on 2026-10-31; previous full run 1355/1477 passed, 0 failed, 122 not run; execution 228 PASS in 14.4 s; compliance 341 PASS / 1 NOT_RUN (+1); status changes 0
- Task 13: source `94fb3cb0b3e82c3177b51eb57bbea199c80854be`, Python 3.13.16 `/workspace/.venvs/tradegen/bin/python`, all 19 KEYLESS names asserted, isolated TRADEGEN_HOME, actual home metadata unchanged; full wall time 402.010 s. The 122 inherited NOT_RUN rows are unchanged (121 unavailable macro inputs, one Windows-only console check).
- Task 13: initial full run had 2 environment failures (missing worktree `.venv` mapping), 1582 PASS and 122 NOT_RUN. Restored the QA record, mapped the Cloud venv into each worktree without changing tests, then both targeted checks and the full rerun passed. No source/test weakening.
- Task 13: external plan run/README checks retain all count, missing-test, NOT_RUN and time assertions; Cloud-only path/date adaptation uses the actual merged base and Asia/Seoul. README and QA retain CRLF, ledger LF. Independent polling/evidence/position reviews completed.
- Task 14: owner setup checklist and exact pinned daily-prompt helper prepared outside the repository; no scheduler, notification, live poll, key access, signature or arming performed. Live setup remains an owner task, not a software acceptance PASS.
