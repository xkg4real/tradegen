# Fixed cash/trend execution adapter

`execution_launch.driver.make_fixed_driver` connects the deterministic `ProgramSpec`
cash/trend candidates to the existing `StrategyDriver` callback. It neither qualifies
a strategy nor sends orders. The original program digest still binds the actual
`program.py` bytes and canonical parameters. A separate deployment content digest
binds the fixed adapter and its listed source dependencies. A trusted implementation
review must approve both; matching source hashes alone is not authenticity proof.

Explicit construction requires the program, forward protocol, launch profile,
`DeploymentWindow`, actual program artifact bytes, history provider, and trusted
history verifier. There are no default venues, account credentials, windows,
providers, clocks, reviewers or owner approvals. Current support is the existing
Upbit/KRW spot evaluator scope. No network, file write, scheduler or order dispatch
is implemented here. Only bounded reads of fixed public code paths occur on explicit
factory construction and identity checks; importing the module does nothing.

## Input contract

The provider receives `DecisionInput` and returns `HistoryFrame` with:

- The deployment window digest and the explicit prospective source label.
- The complete contiguous sample prefix from deployment start through this slot.
  Each `PaperBar` uses the same midpoint sampling convention as `append_book`.
- The prior slot's recorded `PaperDecision`, including its exact history digest.
- An immutable `AccountAnchor` containing original scoped settled cash, instrument
  units and account observation time for this execution slot.

The trusted verifier receives `(frame, fixed_driver_identity, now)` and returns a
`HistoryReceipt` binding the full frame and driver identity digests, source audit
digest, verification time and expiry. Returning `True`, an untyped claim, a wrong
digest or an expired receipt is refused. This is a required trust boundary: the
verifier must authenticate original quote/account receipts, genuine collection and
decision times, and a durable write-once anchor per deployment slot. It must reject
backfills, imported synthetic/replay data, and rewritten anchors after restart.
A label, checksum, local registry, or freshly constructed receipt does not prove
those facts. This module supplies **no production history verifier or durable
history service**; those remain explicit deployment dependencies. The shipped
adapter is `execution_launch/live_history.py` (`LiveHistory.provider` /
`LiveHistory.verifier` over a hash-chained journal of original receipts and
per-slot anchors behind an independent `BaselineHead`); its own ceilings are stated
in `docs/windows-first-trade-integration.md`.

Freshness checks require the already available quote to precede the sampling slot,
and both quote and sample to remain within 10 seconds of the actual execution clock.
The anchored account is at most 30 seconds old. The current runner quote and account
cash/units/asof must match the anchor. Extra inventory in the scoped account, locked
cash, outstanding cancellable orders, non-KRW conversion, off-lot holdings and
unreconciled account observations are refused. E2 still checks the authoritative
account, reservations, owner permissions, selected stake and all execution limits.

## Decision and sizing semantics

The target for slot `i` is recomputed exclusively from marks through slot `i-1`.
The recorded prior decision must match, and its timestamp must precede execution
by the protocol's minimum delay. Current prices size the order but cannot change
that target. First slot and trend warm-up hold cash; a deployment begins with the
protocol's initial cash and zero units. The **deployment** final slot targets zero,
independently of the earlier research capture's final timestamp.

Sizing copies the evaluator's base-cost, one-bar-delay equations with exact rational
arithmetic: current marked holdings and settled cash, configured fee and slippage,
adverse tick rounding, and floor/ceiling lot sizing. Below-minimum orders hold; final
unliquidatable dust raises a refusal. This means the allocation and limit construction
match the paper evaluator for identical inputs. Actual fills, queue priority, depth,
partial fills, cancellations and realized profit are not guaranteed by the paper
simulator or this callback. Live E2 refusal or non-fill can diverge from simulated
performance and requires fresh reconciliation before the next slot.

Stable signal IDs bind the whole fixed-driver identity and deployment slot, excluding
mutable cash, order size and side. A repeated authenticated frame produces the same
signal after restart. A post-fill changed account fails the original anchor match,
instead of generating another action. In-process checks also refuse changed prior
prefixes, slot rewrites and clock rollback. Across processes the trusted history
service must retain the original anchor; the runner's durable journal remains the
one-attempt order authority. The adapter does not create new authority or retry a
possibly submitted order.

## Implementation review binding

`describe_fixed_driver(driver)` accepts only the exact `StrategyDriver` and exact
callback object issued by this factory, with unchanged program/profile/protocol/
window and current source content. Copying a callback into a new `StrategyDriver`,
or providing equal artifact bytes with arbitrary code, is refused. This process-local
registry is application discipline, not isolation from code that can monkey-patch
Python. The trusted implementation review must bind `factory_id`,
`deployment_code_sha256`, `deployment_window_digest` and the existing implementation
binding; the owner-approved repository code hash covers the broader runtime.

`fixed_history_dependencies(driver)` returns the exact injected provider/verifier
objects after validating factory identity. The implementation-review verifier must
compare them with its explicitly approved upstream callables using object identity.
Those trusted runtime selections cannot come from imported JSON. The operator must
separately establish that these are the reviewed live integrations: neither the
signed fixed identity nor comparing callable identity authenticates their source,
behavior, storage or supplied receipts. Different upstream implementations can
otherwise share the same fixed strategy/sizing identity.

The deployment digest is SHA-256 of compact, sorted, ASCII JSON containing
`factory_id: "tradegen-fixed-cash-trend-v1"` and `files`, a mapping from each exact
path below to the SHA-256 of its raw bytes:

- `execution_launch/driver.py`
- `execution_launch/program.py`
- `execution_launch/strategy.py`
- `execution_launch/runner.py`
- `execution_launch/profile.py`
- `execution_control/model.py`
- `execution_control/capability.py`
- `execution_control/controller.py`

Existing research results are not regenerated, reclassified or automatically
approved. None of these APIs reads keys, signs a reviewer/owner document, prepares
or arms a session, supplies an execution permit, or bypasses research/E2 gates.
Fixture authentication in `tests/launch_driver.py` is invented for isolated tests
and must never be configured as a real source verifier.
