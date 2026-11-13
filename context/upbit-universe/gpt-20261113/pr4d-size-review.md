# PR4d G1 independent size review

Date: 2026-11-13. Status: read-only design review; PR4d runtime not implemented. No network, owner state, signing, journal append or tracked-source mutation was used. The scratch probe uses synthetic receipts and the existing real parsers, collector and account reconciler.

## Finding

**P2 — valid retained evidence can exceed the row cap after the planned fallback.** The unconditional statement that a row is never refused for size is false for inputs accepted by the current upstream contracts. This is reproduced at the planned serialization boundary, not a claim that unimplemented PR4d runtime was executed.

Evidence: `pr4d-size-probe.py` and `pr4d-size-probe.log` in this directory. The probe:

1. Builds 1,500 distinct, maximum-length KRW market identifiers with reconciled purchases and positive units. Their current market listing is absent, so the real collector records every position as unlisted at zero.
2. Runs `collect_upbit` with its default bounds, then `build_observation` again. Both succeed; 1,522 source requests are below the default 2,000. The largest source receipt is 278,901 bytes, below the 8 MiB receipt bound.
3. Uses a one-level BTC orderbook with an extra ignored JSON padding field to reach exactly 131,072 bytes. The real `parse_orderbook` and `sample_prefetched_book` both accept it. No field or source hash is forged after parsing.
4. Executes the plan's exact `_holding` function body for all validated positions. Serializes the planned fallback shape with the real `_row`, `_canonical` and `_receipt_body`, including its newline. Top-N is only BTC/ETH; reasons contain only `HISTORY_ROW_SIZE_FALLBACK`; events and allow are empty.

| Component | Bytes |
| --- | ---: |
| Serialized holdings | 103,501 |
| Serialized book receipt | 175,073 |
| Complete planned fallback row, newline included | 279,312 |
| Existing maximum | 262,144 |
| Excess | 17,168 |

The plan passes this final oversized data to `_append`, whose explicit limit rejects it. Replacing only its receipt with the canonical `"unavailable"` string reduces this example to 104,252 bytes; deriving with `book=None` is also required to make the resulting bar and hashes truthful.

This is an accepted-input contract reproduction. It does not establish that a real Upbit account has 1,500 delisted coins or that the exchange sends padded books. No real account or source availability was claimed.

## Bounds that narrow the original preflight note

- `ProgramSpec._validate` already bounds `max_candidates` to 1–4096 (`execution_launch/program.py:71–79`). It is therefore incorrect to call its effective top-N count unrestricted. A prepared universe odds batch is further limited to 64 (`execution_control/universe_odds.py:24,165`). The reproduction uses two.
- `parse_orderbook` has a 131,072-byte raw-body limit (`execution_accounts/quotes.py:24,137–138`). A valid book alone does not exceed the row cap after base64 encoding. Its extra unrecognized JSON fields are retained in the receipt, which makes combining it with valid holdings significant.
- `_plain` enforces finite decimal coefficients of at most 40 digits and exponents within ±30 (`execution_launch/strategy.py:58–75`). Numeric strings are not arbitrary unbounded text.
- The PR4e coordinator produces reasons/events from fixed code families (`pr4e-runner-coordinator` plan lines 2486–2502 and 2808–2834). This review does not assert a production-reachable oversized reason/event string.
- Holdings are not capped by top-N. PR4e explicitly forwards all `latest_frame.accounts[0].positions` (plan lines 2830–2836). Its `held_coins` excludes dust from strategy selection but does not remove dust from account evidence (lines 1644–1648). Account collection permits substantial inventory/history within its independent request and row budgets (`execution_accounts/upbit_collector.py:346–370`), and account reconciliation validates every position without a top-N count limit (`execution_accounts/provider.py:230–248`).

## Exact conflict and consequence

- Spec §12, lines 606–616: per-holding account anchors, trade-book receipt or unavailable, snapshot and parsed market inputs; fallback removes flag/ticker parts; unconditional no-size-refusal promise.
- PR4d plan lines 1251–1286: `_record_universe` retains holdings, snapshot and book receipt on both iterations. Only flags, tickers, allow and fallback reason change. If the second iteration remains too large, control still reaches `_append`.
- Current `live_history.py:351–357`: `_append` checks `len(canonical_row + newline) <= MAX_ROW_BYTES` and rejects excessive data before writing.
- PR4e plan lines 2837 onward: a history exception, except the two explicitly retried book errors, follows the missed-slot path. Thus the issue affects availability/history continuity, not a demonstrated unauthorized order or valuation relaxation.

There are no literal `bounded_slot` or `record_sized_universe` identifiers in the inspected PR4d plan. The inspected implementation is its actual `_record_universe` plus upstream contracts and §12.

## Proposed amendment, not implementation

Parent requested a concrete owner-review brief at `/workspace/outputs/TRADEGEN_PR4D_CAPACITY_AMENDMENT_2026-11-13.md`. Its scope is:

1. Preserve the existing first fallback: flags/tickers unavailable, allow empty, fixed reason.
2. If necessary, make the receipt unavailable and freshly derive all affected values with `book=None`. Keep all holdings, account anchor and snapshot evidence. No buy and no false quote anchor.
3. If retained evidence still cannot fit, return an explicit capacity refusal before append/head movement or in-memory slot/chooser state changes. Keep the original evidence intact and provide operator guidance through the coordinator's existing failure handling.
4. Withdraw the unconditional never-refused-for-size promise. Define bounded record capacity as an admission requirement, checking early when possible and again per slot. No holding trimming, fabricated evidence or cap increase.

Steps 2–4 amend the currently approved design; the parent will handle the owner's guideline-5 approval. Existing PR4d Task 1 foundations may proceed after PR #33 merge. No capacity-path implementation was performed here.

Required regression coverage: first and second fallback; empty recorded allow; bookless bar never a quote anchor; all account evidence preserved; replay produces identical decision/chain; residual overflow leaves journal/head/slot/chooser state unchanged; byte boundary includes newline; fixed frame and slot golden digests unchanged. A second fallback alone must not be advertised as proving arbitrary retained evidence can always fit.
