# Controller rulings on the contract drafters' open issues (round 2, 2026-10-24)

These amend RULINGS.md. Apply them to odds/CONTRACT.md, odds/TASKS.md, odds/header.md and followup/* before drafting
tasks (the task drafters read this file too; where it and a contract disagree, this file wins).

## Odds
- R2-1 KRX stock sell tax (O11 amended): copy the repo's behaviour faithfully. For `KRX_stock_book`, kappa per fill is
  `max(table rate 35 bp, tick_floor_bp(price, ladder_tick(price), tax_bp=SELL_TAX_BP[fill year] if side == "sell" else
  0.0))`, exactly as `instruments.cost_per_side` puts the tax inside the floor; still no separate tax on top. A fill in
  a year missing from the copied `SELL_TAX_BP` raises the copied NotTradable and the leg is NOT_TRADABLE (equality test
  against the original on a grid that includes a 2027 sell). This is stricter than O11 as first written.
- R2-2 Band rounding (Q41): keep the per-edge rule of O10 (the lower edge at ETF ref 2,005 is 1,404); fix the stray
  "1,405" parenthetical. The order layer's `orders.limit_prices` (one tick for both edges) is not changed. Hand-off: E3
  (live order adapters) must take band edges from the venue's own quoted limit prices, never compute them; this is
  carried to E3, not E1.
- R2-3 Spec departures (Q46): accepted as plan decisions; the plan header lists them under "For spec rev 3.3" so the
  owner and GPT's 2026-10-30 check see them.
- R2-4 Fresh-seed rerun before arming: not built by the odds plan; `compare.fresh` says so; the hand-off goes to E2
  (arming), not E1.
- R2-5 The replay leg needs only `lot` and `min_order` from venues.yaml, not `fee_extras` (the card's 10 bp already
  includes fees and Upbit has no fixed fee). Bracket and buy-and-hold legs still need signed fee_extras.
- R2-6 Provenance helpers: copy `gate_ledger.repo_anchor` and `macro_artifacts.tree_hash` into
  `core/oddsdata/inputs.py` with equality tests; oddsdata imports neither module (drop the runtime sys.modules check).
- R2-7 HIDDEN_EDGE with an unbounded a-priori range prints "unavailable for this plan (no finite range)"; accepted as
  conservative.
- R2-8 STALE_DAYS 3 (crypto) / 14 (KRX, US) and the per-refit pilot checks are accepted plan decisions.
- R2-9 The GARCH corruption margins are confirmed by the implementer on the real "pilot" stream; if any falls under
  4 SE, the implementer raises the corruption factor, never lowers the threshold.

## Follow-up
- R2-10 Add `tracemalloc` and `pstats` to DYNAMIC_MODULES (both load code-adjacent data from files: pickle/marshal),
  each with a positive control; drop them from the negative-control list; `faulthandler` stays allowed.
- R2-11 Branch base: `compliance-followup` branches from main HEAD at execution time. Task 1 checks
  `git diff --stat 995534b HEAD -- . ':!docs'` prints nothing (only docs changed since the compliance merge) instead
  of pinning a hash.
- R2-12 The R4 denylist limit is stated as is (accepted).

## All three plans
- R2-13 DRIFT RULE (for the odds plan as well as E1): the odds plan is written against main 5816d3c but executes after
  the follow-up merges. Every odds Edit to a file the follow-up changes (core/compliance/rules.py, owner.py, alerts.py,
  tests/compliance_guards.py, tools/signer/sign.py, data/krx/kis_client.py, core/ficc/data.py, tests/compliance_tables.py)
  is written as "find this anchor and make this change"; Global Constraints carry the rule: re-read before each Edit; if
  the old text differs only because an earlier plan changed it, apply the same change to the current text, keep the
  earlier behaviour, and record a one-line ruling in the execution ledger.
