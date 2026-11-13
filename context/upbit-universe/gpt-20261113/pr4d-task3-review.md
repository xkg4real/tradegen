# PR4d Task 3 independent review

Reviewer: GPT child agent `universe_ioc`, which implemented Task 2 but did not implement Task 3.
Scope: the frozen `execution_launch/driver.py` delta against `f3e6ac3e1e5cdcb74740759ac2a28d4bdf89b298`, its four planned tests, and the relevant existing authentication, sizing and fixed-profile contracts. This review made no source/test edits and ran no acceptance suite again.

Verdict: **no new blocking finding in Task 3**. The separate, already documented Task 2 residual-row-size P2 remains unresolved and remains a final PR4d merge blocker; this verdict does not approve that gap or any proposed capacity amendment.

## Evidence identity

- Worktree: `/workspace/tradegen-universe-pr4d-1113`.
- Driver SHA-256: `e412781b6ede8f97da4af21fbbf948a6858615a4bb5dd7a251a33a28509f2be5`.
- Recomputed tracked Python/YAML source fingerprint: `1aac24a84d06886bdc132fc36bbab4428978f366dc86f8d8b22edba3886c9cfe`. It equals the frozen fingerprint in `task34-green-summary.json`; the fingerprint covers tests as well as runtime Python/YAML.
- Mechanically applied the Task 3 plan's import and four quoted before/after replacements to the base driver. The result equals the current driver exactly.
- AST comparison found only `_validate_frame` changed among top-level functions/classes. The import addition is the planned `UNIVERSE_MARKET` import. The four new Task 3 test ASTs equal the plan exactly.
- Driver remains LF with zero CR bytes. `git -c core.whitespace=cr-at-eol diff --check` passes. An initial plain diff check reported only the preserved CRLF bytes in the separate Task 4 `live_history.py` delta; the repository-prescribed CR-aware check resolves those format-only reports.

## Contracts checked

1. **Symbols and ticks.** Universe bars must be exact `UniverseBar` instances, use a valid KRW symbol, and carry a positive finite Decimal tick. Each booked bar checks positive bid/ask/mark, noncrossed prices, exact midpoint and bid/ask tick alignment using its own tick. The current bar additionally binds its symbol/tick to the observed renewed profile. Both quote and account holding anchors use that observed trade coin. The protocol benchmark is still a construction pin, not the per-tick traded symbol.
2. **Unavailable books.** Historical unbooked bars require all three price fields to be `None` and still pass symbol, tick and time checks. They never enter sizing as the current bar: `FIXED_DRIVER_BOOK_UNAVAILABLE` refuses that case before quote anchoring and `_sized_signal`. A subsequent booked slot can use a prefix containing unavailable bars, as specified.
3. **Prior decision and authentication.** The first slot requires no prior decision and no chooser inputs. Subsequent slots retain the prior index, prior-prefix digest and minimum-fill-delay checks, then recompute only the prior chooser decision from the carried inputs. Its target fraction must match. Current-slot prices affect sizing, not the delayed choice. The unchanged callback authenticates the full frame through the verifier and revalidates it afterward. `LiveHistory._verify` compares the full frame digest with the journal-derived frame and checks durable history. The test that changes carried prices deliberately supplies a fixture verifier; it is not evidence that production authentication accepts a rewritten frame.
4. **Two-slot switching and extra holdings.** A prior choice of another coin makes the current trade coin's target zero; after the coordinator renews the observed profile, the new coin can receive the positive target. Other coins' holdings cease to be a driver error only for a universe protocol. Nonnegative quantities, holding-key shape, account cash/equity identity, reservation refusal and current-coin lot alignment remain checked. The test covers the planned sell/next-slot buy quantities and residual old-coin dust. Coordinator flatness, renewal authority, unresolved orders and extra-holding policy remain separate integration responsibilities; Task 3 does not claim to implement them.
5. **Terminal behavior.** The window-end target is zero even when the prior choice names the current coin. Current-book requirements remain in force. The unchanged callback still refuses a terminal `hold` while current-coin units remain (`FIXED_DRIVER_TERMINAL_DUST_UNLIQUIDATED`). A valid terminal exit signal is not proof of a complete live IOC fill; remaining-fill handling belongs to the coordinator/operator path specified in section 12.
6. **Fixed behavior.** Fixed frames reject both universe extension fields. Fixed bars retain the same source/time/price/KRW checks; the fixed profile contract still binds its symbol, so replacing `protocol.symbol` with the observed profile symbol preserves its quote and holding comparisons. Other inventory still refuses for fixed profiles. `_sized_signal`, `_FixedCallback`, factory registration, authentication, duplicate-slot/prefix protection and order validation are AST-unchanged from the base. Existing golden frame/row digest tests passed in the frozen combined run.

## Validation reviewed

Read the plan Task 3 in `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4d-driver-history.md` and design sections 12 and 14 in `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, plus the current handoff constraints.

Inspected the existing test records rather than repeating broad tests:

- `task34-red-summary.json` and `task34-red-rows.json`: 11 tests, 5 PASS / 6 expected FAIL / 0 NOT_RUN before Task 3/4 implementation. All four Task 3 failures match the plan's expected errors.
- `task34-green-summary.json`, `task34-green-rows.json`, `task34-green.log`: **60 PASS / 0 FAIL / 0 NOT_RUN**, 7.445 seconds, 19 KEYLESS names, source unchanged and real-home metadata unchanged. The run covers 12 universe-history, 15 fixed live-history, 16 driver and 17 launch-guard tests. It includes the six planned Task 3/4 additions and the extra malformed-v2 regression (17 malformed cases in one test).
- All four Task 3 tests passed: two-slot switching; carried-input prior-decision recomputation; per-bar symbol/tick and unavailable-book handling; terminal target zero/no terminal decision.

No network, real APIs, credentials, signing, arming, live orders, dependency changes, stage, commit or push were performed by this review. Source ownership and delivery remain with the parent agent. These offline checks do not establish live readiness or trading profitability. This report is not legal, tax or investment advice; the reviewing agent is not a licensed adviser.
