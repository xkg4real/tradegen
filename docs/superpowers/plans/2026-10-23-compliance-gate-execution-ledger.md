# Compliance plan: execution ledger (2026-10-24)

The subagent-driven execution record of `docs/superpowers/plans/2026-10-23-compliance-gate.md`: the pre-flight scan, every
task review, fix round, controller ruling (each with what it costs if wrong), deferred minor and parked finding.
Kept so the owner and GPT's 2026-10-30 check can audit every decision taken during execution.


Spec: docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md (rev 3.2, b5603f5), reachable.
Plan commit: 3351795. Started 2026-10-24.

## Setup rulings

- Ruling: work on branch `compliance-gate` in the main checkout (Task 1 creates it), not a separate git worktree — the
  tests resolve `ROOT/.venv` (Task 10 test, signer code-approve) and `core.isolation.QUANTGEN_REPO` is
  `parents[1].with_name("QUANTGEN")`; a worktree elsewhere has no `.venv` and a different sibling — cost if wrong: none
  to main (branch isolates commits); a stray uncommitted file in the shared checkout is visible to the owner.
- Ruling: Task 10 is a hard stop — the owner asked to be asked before the download (also a side effect outside the
  repo). Tasks 11-12 may run before it with PENDING NOT_RUNs; Tasks 13-15 wait for Task 10 (plan's own rule) — cost if
  wrong: only ordering.
- Ruling: implementers on sonnet (plan text carries complete code, but tasks are long multi-step with CRLF and
  Edit-anchor subtleties, so turn count favours mid tier over haiku); task reviewers on sonnet, opus for the
  security-sensitive tasks (7-9 gate, 11-13 owner/store, 15 signer); final whole-branch review on opus — cost if wrong:
  token spend only.

## Pre-flight scan (2026-10-24)

The drafting workflow already ran a cross-task consistency critic over all 15 drafts (23 findings, all fixed in the
drafts before assembly; listed in the plan's task texts). This scan re-checks the shared-file and interface pairs.

| Pair / task | Shared file or interface | Produces vs consumes | Finding |
|---|---|---|---|
| T1 -> T2 | tests/compliance_fixtures.py `temp_home` | T1 creates temp_home; T2 edits it to clear `_LINK_SCAN` | consistent (T2 quotes T1's ending; contract A.11 notes it) |
| T1 -> T10 | tests/compliance_guards.py | T1 ends with 14 guard tests; T10 appends a 15th | counts fixed in consistency pass (14/14 before T10, 15/15 after) |
| T1 -> all | tests/compliance_acceptance.MODULES | T1 lists all ten modules; later tasks only create them | consistent |
| T3 -> T4 | core/compliance/rules.py | T3 ends with derive_class rule-7 lines 212-214; T4 anchors Edit 2 there | consistent (T4 revised to T3's final text) |
| T4 -> T14 | core/compliance/rules.py | T4 docstring + approved_state ending; T14 edits both | T14 anchors confirmed unique by its drafter on assembled T3+T4 |
| T4 -> T5 | tests/compliance_tables.py | T4 creates (37 tests, last three lines anchor); T5 appends 18 | count fixed (52/55, 3 not run) |
| T4 -> T6 | rules.approved_state -> model.ApprovedState | T4 imports lazily; 2 tests PENDING until T6 | consistent; T6 expects them to turn PASS |
| T5 -> T8, T13, T14 | shipped kr_rules.yaml dates | KR-OKX-SPOT review_by 2026-11-22 | T8 boundary test uses a re-reviewed fixture row (P15); T13/T14 dates derived from shipped table |
| T6 -> T7-9, T11-13 | model types, seal_context, fixtures ctx/intent/approved | defined T6 | consistent (names verified defined in plan) |
| T7 -> T8 | core/compliance/gate.py lines 7-9, 196-211 | T7 writes fail-closed bodies; T8 replaces them quoting T7 text | consistent per T8 revision (37 gate tests after T8) |
| T8 -> T9 | gate.py lines 9-10, 516-521; render_warning moved to T8 | T9 consumes render_warning/warning_sha256 | consistent; contract A.7 amended |
| T7/8 -> T9 | tests/compliance_gate.py | T9 appends after T8's last line | consistent (38/47 then 47/47) |
| T10 -> T11-15 | cryptography availability | PENDING NotRun before T10 | ruling above; plan says T13-15 wait for T10 |
| T11 -> T12 | owner.py end, compliance_owner.py end | T12 Edit anchors = T11 final last lines | fixed in consistency pass (Task 12 old_string corrected) |
| T11 -> T13 | owner.py `_log_lines`, `_alert_rows`, `_hex64`, read_anchors snapshot "head" | T13 reuses them; writes snapshot `head` | consistent |
| T11/T13 -> T14 | owner._exclusive, load_context, alerts lock | T14 log() uses owner._exclusive(owner.log_path()) | consistent (consistency fix) |
| T11/T13 -> T15 | log line format, schemas, store layout, code_files, atomic write | signer copies them; tests assert byte equality | atomic _write_once fixed in consistency pass |
| T13 guard vs T1 | importlib.util in core | T13 must not import importlib.util in core | fixed: lazy try-import probe; T1 adds negative control |
| T1 / T16 | README.md, tests/run_all.py | T1 registers suite + README:816; T16 adds table row + Total | consistent |
| T2 | self | 15 isolation tests; suite 28/29 with 1 REFDATA | consistent after fix |
| T3 | self | 15 loader tests; rules.py 214 lines | consistent |
| T5 | self | 47 rows; tests check URLs come from research corpus | consistent |
| T10 | self | constraints.txt bytes edit, owner gate first | consistent |
| T16 | self | two REFDATA NOT_RUN allowed (symlink tests) | consistent after fix |

Residual risk: Edit anchors that span tasks were replayed by drafters on their own sandbox builds, not on one
end-to-end build of the assembled plan. The review loop is the net.

## Progress
Task 1: dispatched (BASE 3351795
Task 1: review 1 (3351795..21f4e64): spec OK, quality Approved; 1 Important (plan-mandated), 8 Minor
Task 1: Ruling: HTTP-verb guard is bypassable via urllib.request.urlopen (plan-mandated text) — extend the guard: ban imports of network modules (urllib, http, socket, ssl, smtplib, ftplib, imaplib, poplib, nntplib, telnetlib, xmlrpc, asyncio, webbrowser) in core/compliance and add urlopen/urlretrieve/create_connection to the forbidden call names, each with a positive control — spec says neither package can place an order or move money, the alert email is sent by the scheduled Claude task, not by code, and no planned core/compliance module imports any of these (grep of the plan: only tests import socket) — cost if wrong: a later task that needs a network import fails the guard and must amend it deliberately
Task 1: minor (deferred): _clock_hits flags `from time import sleep` but not time.sleep; clock_gettime absent; alias/getattr bypasses pass
Task 1: minor (deferred): _walk tags a directly nested def's body with outer names only (no effect on current predicates)
Task 1: minor (deferred): _wrap's finally-raise replaces fn()'s exception (chained traceback keeps it)
Task 1: minor (deferred): real ~/.tradegen/compliance listing check can fail an unrelated test if the daily job writes during a run
Task 1: minor (deferred): shipped-file clean asserts vacuous at this commit; no on-disk end-to-end control
Task 1: minor (deferred): registration test asserts the literal "paper, grokteam or compliance" (brittle; plan-mandated)
Task 1: minor (deferred): _main_block_hits misses reversed `"__main__" == __name__`; temp_home rmtree ignore_errors may leak temp dirs
Task 1: minor (deferred): compliance_acceptance imports temp_home lazily without need
Task 1: fix round 1/5 (code items addressed, 1 open — docstring still overclaims: multiprocessing.connection, logging.handlers.HTTPHandler, _socket, socketserver, selectors, wsgiref, xml.sax URL fetch pass; commits 21f4e64..585e898)
Task 1: fix round 2/5 (1 addressed, 0 open; commits 585e898..d2f89d8)
Task 1: minor (deferred): test_no_http_verb_calls docstring says getattr indirection matters only with a banned import — false (unittest.mock.asyncio, logging.config.dictConfig class strings reach banned modules); "xml.dom parsers that fetch" inaccurate (xml.sax fetches)
Task 1: minor (deferred): uncovered fetch/exec routes: xml.dom.xmlbuilder DOMEntityResolver, pydoc.locate, timeit/code/cProfile string execution, compile (covered only by the "not a proof" disclaimer)
Task 1: complete (commits 3351795..d2f89d8, review clean after 2 fix rounds)
Task 2: implemented 63d71c4; note: prereg also lists core/quant/gate_ledger.py — changed in Phase A (d47cea9), expected
Task 2: review 1 (d2f89d8..63d71c4): spec OK; 1 Important (plan-mandated memo key), 5 Minor
Task 2: Ruling: the link memo keyed on the resolved root makes the specified root-is-a-link refusal order-dependent (fail-open when the target was scanned first; false refusal of the target after the link) — keep the resolved-root memo key (Appendix A.4) but check `root.is_symlink() or root.is_junction()` in scan_links before the memo lookup, every call, and add an order-swap test — spec A0 says refuse a link under the state root; the check is two lstat calls — cost if wrong: none (stricter)
Task 2: minor (deferred): pyproject requires-python >=3.10 but Path.is_junction needs 3.12 (venv is 3.13)
Task 2: minor (deferred): KIS token is issued before the final-target check refuses, burning an issuance per call when the target is bad
Task 2: minor (deferred): ficc _cache_put sets _MEM before checked_target, so a refused key is later served from memory without re-raising
Task 2: minor (deferred): no test for a refusal propagating from config.ficc_cache_dir() itself
Task 2: minor (deferred): grokteam isolation test clears B._MANIFESTS instead of restoring it
Task 2: fix round 1/5 (1 addressed, 0 open; commits 63d71c4..75f14c1)
Task 2: minor (deferred): an ancestor of the state root that is a junction/symlink is not judged (only the root itself; OneDrive reparse points make ancestors a design question)
Task 2: complete (commits d2f89d8..75f14c1, review clean after 1 fix round)
Note for later dispatches: compliance_isolation has 16 tests (plan said 15), so any brief's whole-suite compliance count is one higher (one REFDATA NOT_RUN there).
Task 3: implemented 23d5b62; loader 15/15, guards 14/14, compliance modules 44/45 (1 REFDATA)
Ruling: commit trailers name the model that wrote the commit (each subagent's own harness attribution line), not the plan's hard-coded "Claude Opus 5.5" — the plan copied the controller's line; the user never asked for a specific model name — cost if wrong: trailer wording only. Tasks 1-3 commits (sonnet-written) carry "Opus 5.5"; left as is (rewriting branch history is churn), noted for the final report.
Task 3: review 1 (75f14c1..23d5b62): spec OK, quality Approved, 0 Important, 6 Minor
Task 3: minor (deferred): derive_class with |int| beyond 4300 digits raises ValueError from the f-string (outside load_strict's domain)
Task 3: minor (deferred): refusal reasons echo offending values unbounded (250 KB scalar -> 250 KB reason); truncate if reasons reach alerts/logs
Task 3: minor (deferred): "native date"/YAML 1.1 reasons carry no line number (plan-mandated text)
Task 3: minor (deferred): load_strict accepts bytearray (contract says bytes)
Task 3: minor (deferred): test_plain_scalars_load_as_expected uses dict equality (0==False, 3==3.0); cross-type duplicate keys and parse_date trailing newline untested
Task 3: complete (commits 75f14c1..23d5b62, review clean)
Task 4: implemented 7219250; tables 34/37 (2 PENDING model, 1 REFDATA); note: Row is unhashable (match is a mappingproxy) — key rows by row.id
Task 4: review 1 (23d5b62..7219250): spec OK to the brief; 1 Important (plan-mandated), 5 Minor
Task 4: Ruling: policy_ref pattern D[0-9]+ lets D016/D0016 hide a D16 citation from the requires.live rule — tighten to D[1-9][0-9]* (no leading zero) and add "D016" to the refused cases — spec D16 rows must carry requires.live; P28 already refuses the same leading-zero ambiguity — cost if wrong: a table spelling D016 becomes Invalid (fail closed)
Task 4: minor (deferred): Row/RulesTable not deepcopy/asdict-safe (mappingproxy); Task 6/14 must not asdict Row
Task 4: minor (deferred): calendar_sha256 lets OSError from read_bytes escape; empty dir hashes to empty sha256 (callers compare to approved hash)
Task 4: minor (deferred): review_by has no lower bound; max_leverage no upper bound
Task 4: minor (deferred): non-str settlement items, market bases, deposit symbols handled but untested
Task 4: minor (deferred): Formatter().parse(warning) runs twice per row
Task 4: fix round 1/5 (1 addressed, 0 open; commits 7219250..656dab9)
Task 4: minor (deferred): D0016 refused but untested
Task 4: complete (commits 23d5b62..656dab9, review clean after 1 fix round)
Task 5: implemented 7f50655; 18/18 new, tables 52/55
Task 5: review 1 (656dab9..7f50655, opus): no row looser than spec 5.3; 2 Important (plan-mandated), 4 Minor
Task 5: Ruling: KR-KIS-KRX-DERIV lists broker_eligibility under requires.owner, but spec 5.3 puts broker eligibility under requires.live (D16: owner snapshots are not evidence) — replace it with live item `broker_approval` (existing LIVE_REQUIREMENTS member; `broker_eligibility` as a live item is Invalid by Task 4's vocabulary), courses stay owner items — downstream tests (Task 5 subset check, Task 8 D16 test) still hold — cost if wrong: none today (requires.live always blocks until the execution spec)
Task 5: Ruling: OKX stablecoins have no in-gate exit (Upbit/OKX deposit facts list only BTC; P22), which conflicts with D11 "exits stay open" — do NOT add unverified USDT/USDC networks (a wrong network loses funds, which is what the deposit check exists to prevent); instead make KR-OKX-WITHDRAW's reason accurate (with the shipped venue facts only BTC to Upbit is a gate exit; stablecoins and other destinations exit manually in the exchange app until the owner signs a verified deposit network) and carry an owner act to Task 16's hand-off — fail closed, matches D11's manual-withdrawal fallback — cost if wrong: the owner exits OKX stablecoins by hand until they add a verified network
Task 5: minor (deferred): tests pin exact match dicts only for KR-OKX-SPOT; widening an allow row (e.g. sell_short on KR-KIS-US-SHARE, p2p_buy on KR-DOMESTIC-SPOT) passes all 18 tests — suggest exact {id: match, requires} pins for the ~15 rows that can let something through
Task 5: minor (deferred): no row lists 2027-01-01 in affected_by (tax date; crypto tax_basis depends on it)
Task 5: minor (deferred): report says trailer Sonnet while constraints said Opus (superseded by the attribution ruling)
Task 5: minor (deferred): KR-DRIFT lists a repo research path under sources (duplicates research; brief-mandated)
Task 5: fix round 1/5 (2 addressed, 0 open; commits 7f50655..62db970)
Task 5: minor (deferred): KR-KIS-KRX-DERIV reason text does not mention broker approval (cosmetic)
Task 5: complete (commits 656dab9..62db970, review clean after 1 fix round)
Owner act for the final report: add a verified USDT/USDC deposit network (and verify the BTC 'bitcoin' entry) in core/odds/venues.yaml before approving it; until then OKX stablecoins exit manually.
Task 6: implemented 4ab60e5; model 10/10, tables 54/55, aggregator 108/110 (2 REFDATA)
Task 6: review 1 (62db970..4ab60e5): spec OK, quality Approved, 0 Important, 5 Minor
Task 6: minor (deferred): jsonable stringifies non-tuple Mapping keys (frozenset/object keys give hash-seed-dependent canonical JSON)
Task 6: minor (deferred): "|".join tuple keys not injective across mappings (needs a "|" in a venue/symbol; plan-mandated A.5.1)
Task 6: minor (deferred): seal_context keeps the caller's dicts (mutation after sealing keeps is_sealed True with a stale ctx_hash; Task 13's load_context freezes copies)
Task 6: minor (deferred): no explicit jsonable(MappingProxyType) test; fixture-defaults test checks only part of A.5.4
Task 6: complete (commits 62db970..4ab60e5, review clean)
Task 7: implemented 7599017; gate 17/17, suite 125/127 (2 REFDATA)
Task 7: review 1 (4ab60e5..7599017, opus): code = brief; 2 Important (plan-mandated wiring), 4 Minor
Task 7: Ruling: history-map lookup must serve exits only — search state.history_maps for transfer_out only when destination_venue is in DOMESTIC_EXCHANGES (a withdraw candidate), and add "withdraw manually in the exchange app" for an unknown transfer symbol only for a domestic destination (folds Minor 1) — spec 6.2 step 0 allows earlier maps for exits only; retiring an instrument from the map must stop new exposure — cost if wrong: a deposit of a retired symbol to a grey venue is malformed (fail closed)
Task 7: Ruling: exit kinds (close_long, cover_short, withdraw) require financing == "cash"; credit/margin sells and buy_to_covers classify as new_exposure (KR-KIS-CREDIT out_of_scope or "no row" then blocks) — D15 forbids credit buying and margin; a margin sell can open a short; spec 6.2 step 3's exit definitions presuppose the cash owner of D15 — cost if wrong: a non-cash position (which D15 says never exists) must be closed by hand in the broker app; Task 8's credit test (a buy) is unaffected
Task 7: minor (deferred): exit on a vocabulary venue with no venue facts (e.g. held BTC on binance) is malformed: venue with no close-manually guidance
Task 7: minor (deferred): conduct rows keyed on an ETP class never fire and the loader does not refuse them (ponytail-marked)
Task 7: minor (deferred): report said "Deviations: None" despite the trailer change (superseded by the attribution ruling)
Task 7: fix 1 e72d0ee: history search also requires cash (consistent with the exits-only ruling; accepted)
Task 7: minor (deferred): a cash sell that classifies as new_exposure (settlement symbol or non-settlement counter) can still be looked up in history_maps — unreachable with the shipped venue markets
Task 7: fix round 1/5 (2 addressed, 0 open; commits 7599017..e72d0ee)
Task 7: minor (deferred): a domestic-destination transfer that fails the withdraw test can still carry a superseded instrument into new_exposure (step 6 then needs the same registered address + credited network, so it blocks); under a broken log a credit sell gets the snapshot's state_hash
Task 7: complete (commits 4ab60e5..e72d0ee, review clean after 1 fix round)
Task 8: implemented 0791ae7; gate 37/37, suite 145/147
Task 8: review 1 (e72d0ee..0791ae7, opus): code = brief; 1 Important (plan-mandated), 8 Minor
Task 8: Ruling: grey cap skipped a None-keyed reservation when the intent had no reservation id (k != None drops it) — count every reservation when intent.reservation_id is None, and _positions refuses non-str or empty reservation keys (state: positions invalid) — spec 6.2 step 5 excludes only the intent's OWN reservation; reproduced ALLOW over a 10% cap — cost if wrong: none (stricter)
Task 8: minor (deferred): per-session ack accepted with session_id None (needs Task 12 never to produce None; defence: require a non-empty str)
Task 8: minor (deferred): derived destination buy keeps the source intent's asset/multiple (asset-keyed rows, asset floor, P4 read the source); no shipped path
Task 8: minor (deferred): missing exposure entry counts as held 0 even with holdings on that venue
Task 8: minor (deferred): loader allows {cap} in non-grey warnings, so "the share you set" text could be ack-signed on a non-grey per_session row
Task 8: minor (deferred): address/tag rule duplicated in _dest_check and _credited
Task 8: minor (deferred): test_no_snapshot_means_manual_exits is a Task 7 regression pin in the Task 8 block
Task 8: fix round 1/5 (1 addressed, 0 open; commits 0791ae7..34b3be9)
Task 8: minor (deferred): _transfer carries the transfer's reservation_id into the synthetic destination buy, so a destination reservation with the same id is excluded (assumes globally unique ids)
Task 8: complete (commits e72d0ee..34b3be9, review clean after 1 fix round)
Task 9: implemented 90cc52f; gate 47/47, suite 155/157
Task 9: review 1 (34b3be9..90cc52f, opus): code = brief; 1 Important (plan-mandated), 9 Minor
Task 9: Ruling: the purity AST scan seeds model.py by hand and misses OwnerState.ok (runs on every decision) — scan every def in model.py, and seed every rules.py class (calendar_sha256 stays out: gate cannot reach it) — spec 8.8 purity; the AST layer is the backstop for aliased clock imports the traps cannot see — cost if wrong: none (all 18 model defs pass today)
Task 9: minor (deferred): two permits sharing one reservation_id both verify (120k vs a 100k cap); add "a reservation id names exactly one intent, reserved at its notional" to P36 / A.5.2 for the execution spec
Task 9: minor (deferred): a registered permit edited in place (object.__setattr__) still verifies (P5 discipline; digest-at-issue hardening possible)
Task 9: minor (deferred): a permit issued with session_id None verifies under any session-less context
Task 9: minor (deferred): malformed plans without leg/venue/symbol get decide's malformed: venue/symbol; a leg raising non-AttributeError gives internal error — fail closed, untested
Task 9: minor (deferred): _T9_FORBIDDEN lacks random/secrets/uuid and file-metadata names; purity loop could assert every issued permit verifies; gate.py:599 duplicates _choose_state's buy branch
Task 9: fix round 1/5 (1 addressed, 0 open; commits 90cc52f..6df420b)
Task 9: minor (deferred): purity scan does not read module-level imports of model.py/rules.py (Task 1's clock guard flags `from time import` anywhere in core/compliance, so it is covered there); used["model"]/from_model now dead code in the test
Task 9: complete (commits 34b3be9..6df420b, review clean after 1 fix round)
Task 10: owner asked 2026-10-24 (download gate); no answer yet — proceeding with Task 11 (PENDING NOT_RUNs allowed for Tasks 11-12 per the plan)
Task 11: implemented ddbea3a; owner 16/24 (8 PENDING crypto), suite 171/181 — re-run the 8 after Task 10
Task 11: review 1 (6df420b..ddbea3a, opus): code = brief; 2 Important (plan-mandated), 3 Minor; no way found for a forged/edited/reordered/truncated/wrong-key line to verify
Task 11: Ruling: read_pubkey can raise cryptography's UnsupportedAlgorithm (not a ValueError) for a well-formed SPKI of another key type — wrap it into ValueError("...: not an Ed25519 public key (...)"), add a test with an unknown-OID SPKI (PENDING until Task 10); callers treat OSError (e.g. the pem is a directory) as BROKEN, as for read_anchors — spec: a bad trust anchor means BROKEN, never a crash — cost if wrong: none
Task 11: Ruling: _UTC and _ISO_DATE use \d, so a non-ASCII year (fullwidth/Arabic-Indic digits) verifies in an unsigned system entry — use [0-9] (ASCII) and add a utc test case — later tasks parse Entry.utc with fromisoformat and compare strings — cost if wrong: none (stricter)
Task 11: minor (deferred): append_system_entry raises TypeError for an unhashable kind and OSError after a ~10 s Windows lock wait (Task 14 halt writer should expect OSError)
Task 11: minor (deferred): duplicate keys nested inside data are caught by the hook but untested
Task 11: design note for final review / GPT check: P20 lets the holder of a retired key rewrite history from the rotation point while keeping the first fingerprint; only anchors catch it (a padded forged log defeats the "#seq went down" residual)
Task 11: fix round 1/5 (2 addressed, 0 open; commits ddbea3a..c745819)
Task 11: minor (deferred): unknown-OID test may pass vacuously if cryptography maps it to ValueError rather than UnsupportedAlgorithm (fix handles both); non-ASCII digit literals in tests (style)
Task 11: complete (commits 6df420b..c745819, review clean after 1 fix round; 9 owner tests PENDING cryptography — re-run after Task 10)
Task 12: implemented b8416f3; owner 34/43 (9 PENDING crypto)
Task 12: review 1 (c745819..b8416f3, opus): code = brief; 2 Important (plan-mandated), 4 Minor
Task 12: Ruling: a signed loosening stamped earlier than the line before it skipped D12 (dated by its own stamp) — date every entry in the fold by the running maximum Asia/Seoul date over the log up to its seq (monotonic), never by a stamp earlier than any previous line — D12 "loosen only from the next date, never in an armed session, never after a halt"; the verifier checks stamp format only — cost if wrong: a legitimately backdated owner entry takes effect later (stricter)
Task 12: Ruling: entries stamped after now were ignored for every kind, so a future-stamped system_halt/system_disarm (clock stepped back) was dropped — system kinds and tightening cap_set/limit_set entries apply whatever their stamp; only loosenings (and other kinds) stamped after now stay ignored — D12 "tightening takes effect at once", D3 "halts for good" — cost if wrong: none (stricter)
Task 12: minor (deferred): owner_state never checks date against now_utc (Task 13 derives both from one now); malformed now_utc compared as a string
Task 12: minor (deferred): owner_state does not catch ArithmeticError (10**400 via hand-built LogCheck; verify_log refuses such data); in_force/history/code_approval raise KeyError on malformed hand-built entries
Task 12: minor (deferred): BROKEN path tested only via ValueError; no disarm-then-re-arm-on-the-loosening-date test
Task 12: fix round 1/5 (2 addressed, 1 new Important open — running-max dating applied to halts/armings moves restrictions later; commits b8416f3..a226766)
Task 12: Ruling (amends round-1 ruling 1): date each loosening as LATE as plausible (running maximum Asia/Seoul date over the log up to its seq) and each restriction (system_halt, session_armed, and the halt cutoff) as EARLY as plausible (the minimum of its own stamp date, the dates of every later line in seq order, and today's date); the halt cutoff is the minimum such halt date over all halts; each session keeps its earliest such arming date since its last disarm — a restriction cannot have happened after a line written after it or after now — cost if wrong: restrictions apply earlier than they really did (stricter)
Task 12: fix 2 752ad9d (owner 41/50, 9 PENDING); concern: future-stamped session_armed ignored (neither arms nor blocks) — left per round-1 ruling
Task 12: fix round 2/5 (A/A2/B/B3 addressed; 1 Important open — a session_armed stamped after now is ignored when finding the session's earliest arming date (N1/N1b), pre-existing since a226766; commits a226766..752ad9d)
Task 12: Ruling: for D12's blocking date, every session_armed counts whatever its stamp (dated early, as ruled), cleared by system_disarm; armed_sessions (which enables trading) keeps ignoring armings stamped after now — an arming is a restriction for D12 but a permission for trading, so it blocks early and enables late — cost if wrong: a loosening waits during a session armed with a future stamp (stricter)
Task 12: minor (deferred): tests/compliance_owner.py:923 is a ~180-character line (collapsed continuation)
Task 12: fix round 3/5 (1 addressed, 0 open; commits 752ad9d..0ca84ac)
Task 12: parked — a halt stamped ahead (system clock past Seoul midnight) with no later line stamped on/before the loosening's date lets a same-date loosening through after the halt (H2) — Ruling: accept and document for the final review and GPT's check; bounding the halt date by the latest stamp before it would revoke loosenings that were in force before the halt when no line sits between them (over-block); needs a clock skew past midnight — cost if wrong: under that skew a loosening survives a halt written the same Seoul day
Task 12: parked — a backdated loosening that is the first line of its day counts at once (T2): needs the owner's key and a backdated signer clock; no outside time anchor in the log — Ruling: known limit of round 1's dating, documented — cost if wrong: one loosening a day early
Task 12: note for Task 13: owner_state takes date and now_utc separately; load_context must derive both from one now (date = Asia/Seoul date of now)
Task 12: complete (commits c745819..0ca84ac, review clean after 3 fix rounds, 2 parked)
Task 13: BLOCKED on Task 10 (owner download approval pending); Tasks 13-15 need cryptography per the plan
Task 10: owner approved 2026-10-24 in chat: "Yes: download and install cryptography 49.0.0 from PyPI into TRADEGEN's .venv only, and pin it in requirements.txt, pyproject.toml and constraints.txt." — dispatching (BASE 0ca84ac)
Task 10: implemented 092140c; wheel 3.8 MB; guards 15/15; compliance 208/210 (2 REFDATA, no PENDING); owner 52/52; RECORD sha256 3b67ffba...0f9a
Task 10: review 1 (0ca84ac..092140c): spec OK, quality Approved, 0 Important, 2 Minor
Task 10: minor (deferred): pin test checks the dist metadata location, not cryptography.__file__; docstring claims coverage of UnsupportedAlgorithm it does not import
Task 10: complete (commits 0ca84ac..092140c, review clean)
Task 13: implemented f874720; store 28/28, owner 52/52, suite 236/238
Task 13: review 1 (092140c..f874720, opus): code = brief; 2 Important (plan-mandated), 6 Minor
Task 13: Ruling: _skipped treats `if __name__ != "__main__":` (and any TYPE_CHECKING name, even a local `TYPE_CHECKING = True`) as skipped, so an import there escapes the signed code closure — skip only a single `==` comparison of `__name__` with "__main__", and TYPE_CHECKING only when the name is `typing.TYPE_CHECKING` or was bound by `from typing import TYPE_CHECKING` and is not otherwise assigned in the module; add the `!=` and local-binding cases to the closure test — spec D14: every file whose code runs is signed — cost if wrong: a few more files in the closure (stricter); Task 15's signer copy must match
Task 13: Ruling: owner._calendar_stream follows file links and skips junctions while rules.calendar_sha256 refuses links — keep ONE framing: add `rules.calendar_stream(data_dir) -> bytes` (refusing links exactly as calendar_sha256 does today), make calendar_sha256 hash it, and have owner reuse it; store_get treats Invalid as None — the store and the approval must hash the same bytes; Tasks 14-15 copy this — cost if wrong: none (one implementation)
Task 13: minor (deferred): huge int in positions raises OverflowError in _amount (fail closed, but reason "internal error" and real owner state lost)
Task 13: minor (deferred): positions validated on one read and copied on another (a non-dict Mapping could differ)
Task 13: minor (deferred): a forged unsigned snapshot file can make superseded rules decide exits under a broken log (exits only; within spec 6.4 honest limits); possible cross-check against in_force at its seq
Task 13: minor (deferred): store_put can report success on a calendar folder with an extra file while store_get returns None (fail closed); repeated imports in owner.py
Task 13: fix 1 4968bd4; note for Tasks 14/15: owner._calendar_stream is gone — use rules.calendar_stream (briefs 14:21,:488; 15:15,:789)
Task 13: fix round 1/5 (2 addressed, 0 open; commits f874720..4968bd4)
Task 13: minor (deferred): a rebound guard name escapes the closure scan (`typing = SimpleNamespace(TYPE_CHECKING=True)`, `__name__ = "__main__"`); one-line hardening: require _binds(tree,"typing")==1 / _binds(tree,"__name__")==0 — Task 15's signer copy must match whatever owner.py does
Task 13: minor (deferred): store_dir() outside the try in store_get; a NUL byte in a calendar file name/content framing; UnicodeEncodeError on a lone-surrogate filename not caught; cosmetic long docstring lines
Task 13: complete (commits 092140c..4968bd4, review clean after 1 fix round)
Task 14: implemented b7fa408; cli 32/32, suite 269/271, cockpit 47/47, macro 419/540; real-home --check exit 3, writes nothing; adaptation: calendar line catches OSError/ValueError/RuntimeError (info line, outside exit code) — accepted
Task 14: review 1 (4968bd4..b7fa408, opus): code = brief + accepted adaptations; 2 Important (plan-mandated), 7 Minor
Task 14: Ruling: under `python -m core.compliance.rules` the file runs as __main__ while owner imports core.compliance.rules, so isinstance checks in _keyed fail and --check exits 4 whenever a draft differs from the signed table — make both CLIs single-identity: rules.main and alerts.main first re-import their canonical module (`from core.compliance import rules`/`alerts`) and delegate to it when they are not that module's own function, and _keyed also keys on the table kind rather than isinstance; add runpy-as-__main__ tests in a signed home with a differing draft for rules, and a runpy smoke for alerts — spec 5.4 names `python -m core.compliance.rules --check` — cost if wrong: none
Task 14: Ruling: the once-per-threshold rule counted the local toast row as delivered, so a failed push/email was never re-sent — count only `push` or `email` rows with result ok as sent; add a test with a toast-ok + email-fail history (alerts again next day) — spec 5.4 "a failed channel is announced on the others" and thresholds survive a missed run — cost if wrong: an extra alert
Task 14: minor (deferred): after a legitimate rotation, any other exit-3 cause leads with KEY CHANGED in due() (brief accepts "alerts more")
Task 14: minor (deferred): an unhashable item in an alerts.jsonl row or an unreadable alerts.jsonl kills the send line (Task 16 fallback still sends)
Task 14: minor (deferred): a torn alerts.jsonl line (disk full mid-write) makes the owner log BROKEN until hand-edited; truncate-back on exception would cover it
Task 14: minor (deferred): a stdout write failure exits 1, not 4 (alerts cross-check catches it)
Task 14: minor (deferred): first recorded fingerprint can come from an unverified key (exit-3 summary); consider recording only from code 0-2 summaries (P20-level)
Task 14: minor (deferred): calendar-line adaptations untested; footer prints the current fingerprint, spec says "the first recorded fingerprint ... in every alert email"
Task 14: fix round 1/5 (2 addressed, 0 open; commits b7fa408..177e14c)
Task 14: note for Task 16: the daily prompt must log push and email (only those rows suppress a repeat)
Task 14: complete (commits 4968bd4..177e14c, review clean after 1 fix round)
Task 15: implemented d98cc3e; signer 32/32, suite 304/306; interactive path covered only via seams (owner's first real run is the first full exercise)
Task 15: review 1 (177e14c..d98cc3e, opus): copies byte-faithful; 3 Important (2 plan-mandated), 6 Minor
Task 15: Ruling: stdin TTY refusal used isatty(), which is true for NUL on Windows — on Windows require GetConsoleMode on stdin's handle to succeed (failure = not a terminal), keep isatty elsewhere; test with sys.stdin = open(os.devnull) — spec 6.4 refuses when stdin is not a TTY — cost if wrong: none
Task 15: Ruling: passphrase rule counted inner blanks and compared words case-sensitively — count non-blank characters (>= 20) and compare words by casefold (>= 5 different alphabetic words of 3+ letters) — the plan's header says "20 non-blank characters"; where P39's text is looser the stricter reading wins — cost if wrong: a few passphrases refused
Task 15: Ruling: nothing stopped signing with a key that is not the key in force, which breaks the append-only log for good — in _commit, under the lock, refuse unless the unlocked key is the key in force: after the last key_rotated its new_pubkey_b64; with no rotation, the key that verifies the last signed line (any key for an empty log); a key_rotated entry is checked against the key in force before it; add the rotation steps to the help (keygen --key NEW, sign key_rotated with the old key, copy the new pem, then always pass --key NEW) — cost if wrong: none
Task 15: Ruling (elevated from Minor): _claude_ancestor fails open when the process table is empty or the signer's own pid is missing — treat "cannot see my own process" as "cannot rule out Claude" and refuse — spec 6.4: refuse when a parent process is the Claude app; a refusal check must fail closed — cost if wrong: the owner sees a refusal on a machine where Toolhelp32 fails and must report it
Task 15: minor (deferred): signer state_root lacks the root-is-link refusal/A0 scan and checks within=state_root() (gate is stricter and fails closed)
Task 15: minor (deferred): keygen edge cases (junction check after prompts; pem write failure leaves a key without pem; --key X.pem collides); non-BMP passphrase chars fail late; main() lets RecursionError/KeyboardInterrupt escape and argparse usage errors share exit 2 with refusals; no --help refusal test; report counting inaccuracies
Task 15: fix round 1/5 (4 addressed, 0 open; commits d98cc3e..e233db6)
Task 15: minor (deferred): ancestor walk returns False when a parent pid has exited; rotation help does not say the log reads BROKEN between steps 3 and 4; fingerprint needs the pem beside the key file; keygen weak-passphrase text does not mention blanks/capitals
Task 15: complete (commits 177e14c..e233db6, review clean after 1 fix round)
Task 16: dispatching Steps 1-6 only (verification, README row + Total, commit qa results, real-home --check); Step 7 (scheduled task) is an owner gate the controller asks; Steps 8-10 are controller bookkeeping; Step 9 (GPT) waits until after 2026-10-30 14:40
Task 16: steps 1-6 done 355f978; compliance 309/311, full 1037/1160 0 failed 123 not run; real-home --check exit 3 writes nothing
Final review (3351795..355f978, opus): ready "with fixes"; 0 Critical, 2 Important, ~10 Minor; no fail-open path found with the shipped tables
Final: Ruling: fix wave includes Important #1 (loader: non-blocking rows must name action and financing and class or asset; a gated row needs at least one requirement; conduct rows keyed on an ETP class refused) and Important #2 (exit fallback via history maps on explicit-market venues: close-long tests the counter is a settlement asset instead of is_market; a retired-coin withdrawal or an exit that still cannot be classified gets the manual advice; test rebuilt through approved_state), plus the cheap fail-closed or owner-facing minors the reviewer marked "worth doing now": exit-3 alert/--check wording (exits are manual under a broken log or with no snapshot), cap text f"{cap*100:g}%", grey new exposure refuses notional_krw <= 0 and holdings on a grey venue without an exposure entry, pyproject requires-python >=3.12, signer rotation help (BROKEN window between steps 3-4; write the new fingerprint on paper), alert footer prints both the current and the first recorded fingerprint, test_no_http_verb_calls docstring made true (+ pydoc/timeit/code/cProfile in DYNAMIC_MODULES) — the rest is carried to the execution spec or accepted per the reviewer's triage — cost if wrong: a slightly wider change set in one reviewed wave
Final: carried to the execution spec: ack accepted with session None and gate never reads ctx.session.armed; shared reservation_id; permit edited in place; append_system_entry TypeError/OSError; torn alerts.jsonl / owner.jsonl last line repair; KEY CHANGED after rotation in due(); KIS token burnt on refusal; system entry stamped far ahead blocks signer stamps; signer signs acks as bare hashes; P20 retired-key history rewrite; H2 halt-dating before execution writes system_halt
Final: fix wave 31657d7; compliance 315/317, cockpit 47/47, real-home --check exit 3; shipped data unchanged
Final: re-review of the fix wave (355f978..31657d7, opus): all 9 findings addressed, no new Critical/Important; end-to-end attack 343,224 intents x 4 scenarios x 2 sessions through load_context: 0 violations
Final: parked — xml.dom (incl. xml.dom.xmlbuilder DOMBuilder.parseURI / DOMEntityResolver) and profile/pdb/bdb/trace are not in the import bans — Ruling: park as a small guards follow-up; nothing in core/ imports xml or these modules and the T-RO-01/test_08/09 scans plus review cover current code — cost if wrong: a future core/compliance file could fetch a URL through xml.dom without tripping the guard
Final: parked — D15 is enforced only by row content: an explicit `financing: [cash, margin]` or `action: [..., lend, sell_short]` on an allow row still loads VALID (D16 has a loader check, D15 does not) — Ruling: park as loader hardening for the next table change; the shipped table is cash-only and every change needs the owner's signature — cost if wrong: a signed table that widens an allow row would be honoured
Final: carried — odds plan must not send a zero stake to screen() (it now reports malformed: notional_krw); execution spec must derive notional and held_krw from live prices (P19)
Final: review clean; workspace ledger committed as docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md before the workspace is deleted
