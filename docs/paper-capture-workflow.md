# Deterministic program and paper capture workflow

This implementation produces reproducible decisions and evaluator input. It has
not selected a profitable strategy, performed an exchange capture or completed
source/owner review. The existing frozen study remains unchanged and still has
zero passing candidates. Synthetic fixtures are software tests only.

## Fixed programs

`execution_launch.program.ProgramSpec` has six explicit fields:

- `schema_version`: integer1.
- `strategy_id`: a stable identifier included in the protocol's full trial family.
- `kind`: `cash` or `moving_average_trend`.
- `fast_window` and `slow_window`: integer observation counts.
- `exposure_fraction`: an exact decimal, serialized as a plain decimal string.

Cash requires both windows and exposure to be zero. It is a baseline and cannot
meet a requirement for twenty completed roundtrips. The trend candidate requires
`1 <= fast_window < slow_window <= 4096` and exposure in `(0,1]`. After a complete
warm-up, it holds the supplied fraction only when the fast arithmetic mean is
strictly above the slow mean; equality and insufficient history hold cash. There
is no fitting, hidden default parameter choice, shorting or leverage.

`target_fraction(spec, marks)` consumes an explicit tuple of historical Decimal
marks. It uses exact rational means, independent of ambient Decimal precision.
Callers can pass the full known prefix or just its last slow-window observations;
the recorder uses the latter. No future observation is requested by this function.

`parse_program(raw)` rejects missing/unknown fields, duplicate keys, JSON floats,
nonfinite values, scientific decimal strings, bool windows and oversized inputs.
`program_json(spec)` exports the reviewed specification. `parameters_json(spec)`
returns the canonical parameter string for an eventual audited runner adapter.

`program_digest(spec, artifact_bytes)` uses the same artifact-SHA256/parameter
binding as `runner.program_digest`. The artifact must be the actual reviewed
source or package manifest, provided explicitly by the caller. Matching a digest
does not prove that a callback implements those bytes. This module does not
construct an order-generating runner callback or an implementation-review receipt.
Sizing, current holdings, lot rules, per-order costs and actual E2 authorization
remain responsibilities of a separately reviewed deployment adapter.

## Bind before capturing

Construct a complete `ForwardProtocol` with the exact program digest, strategy
ID, source-code artifact digest, profile/rule terms, capital, window, costs and
complete trial family. The protocol's existing statistical and scope rules still
apply. Register and publish it before the first observation through the existing
[prospective workflow](forward-strategy-validation.md). Neither a local hash
chain nor a caller-supplied timestamp proves genuine prior publication.

The recorder checks program/source artifacts and the registered protocol before
accepting observations. The capture duration must contain an exact bounded grid
of between2 and20,000 observations. No incomplete owner profile or absent review
is silently replaced by a completed prerequisite.

## Streaming observations

The pure library interface is:

```python
capture = PaperCapture(
    protocol, registry, program,
    program_artifact=reviewed_program_bytes,
    capture_source_artifact=reviewed_capture_source_bytes,
    clock=operator_clock,
)
decision = capture.append(paper_bar)
archive = capture.finish()
raw_capture = capture_json(archive)
```

Construction requires an explicit aware clock value between preregistration and
the capture start. The caller supplies the source and scheduling; this class
does not fetch, sleep, start a thread, read files or select a wall clock. Each
append reads the injected clock for the actual decision time. Slots are strictly
sequential and equal the preregistered grid; late decisions, future receipts,
gaps, duplicate slots, clock rollback and changes to the configuration refuse.
Each generated decision binds the exact available prefix hash. There is no API
for replacing previous observations or decisions. Export also checks the stored
history chains, including deliberately changed frozen records.

Every nonterminal row records a target decision. The last row is reserved for
the evaluator's required liquidation. `finish()` requires the full window;
`snapshot()` can archive an incomplete or failed trial without making it eligible
for evaluation. Preserve failures rather than replacing them with a new study
having the same identity.

The clock and supplied records are trusted integration inputs. This class cannot
prove that a malicious caller did not fake either. The prospective source label
is therefore still subject to independent original-record and publication review.

## Sampling a real prefetched orderbook

Exchange update times naturally differ from fixed observation slots. The optional
`sample_prefetched_book(book, slot=..., sampled_at=...)` bridge samples a book that
was **already received before the scheduled slot**. It does not rename exchange
timestamps or pretend a later response existed earlier.

- The original `OrderbookQuote.receipt` retains exact raw bytes, exchange update
  time and original HTTP receipt time. Reparse/record equality checks remain in
  the quote source's `to_runner_quote` function.
- The book must be fresh at both the scheduled slot and the actual sampling time.
  The quote source's ten-second boundary applies. A post-slot arrival, future
  observation, stale source or altered record refuses.
- The resulting `PaperBar.observed_at` is the scheduled **sampling slot**;
  `received_at` is when this sampling record was actually made. These are distinct
  from the original HTTP/exchange times. The mark is an explicitly derived
  midpoint, not a trade or guaranteed fill price.
- `PaperBar.source_sha256` is the digest of the unchanged original receipt. It
  binds the archived source bytes but does not authenticate them.

`PaperCapture.append_book(book)` performs this bridge with its injected clock and
next expected slot, checks the selected market, and records the decision at that
same time. `sampled_receipts` exposes immutable `(bar_index, original_receipt)`
pairs for separate archival. Retain these raw records with the capture. Generic
`append` callers must separately retain their own original records. Neither path
generates source authenticity, independent review or executable order permission.

## Batch replay and strict export

`replay_capture(protocol, registry, program, bars, program_artifact=...,
capture_source_artifact=..., source_kind=..., now=...)` reconstructs deterministic
decisions from an imported sequence. The only accepted labels are
`retrospective_replay` and `synthetic`. Matching dates, hashes or registration
records cannot upgrade a batch into prospective evidence. Reconstructed decision
times use the supplied receipt times and are explicitly historical simulation.

`parse_replay_input(raw)` accepts exactly:

```json
{"registry": [], "bars": [], "source_kind": "retrospective_replay"}
```

The empty arrays above show the envelope only; an actual record needs a valid
registry and complete bounded observations. The parser rejects decisions,
summary/PASS fields, unknown/duplicate keys, floating-point monetary tokens,
nonfinite values and oversized inputs. It returns `(registry, bars, source_kind)`.

`capture_json(archive)` produces exactly the existing evaluator schema:
`registry`, `source_kind`, `bars`, `decisions`. It does not write a file or include
an imported eligibility verdict. Pass the result to `evaluate_capture_json` with
the current rules and explicit evaluation time. Its unchanged causal, cost,
lot, delay, capital, sample and multiplicity checks compute the result again.
The separate review gate still rejects synthetic/retrospective evidence.

The [workflow CLI](launch-workflow.md) connects explicit program/protocol/bar files
to this batch path and then to the existing evaluator. No flag enables trading
or substitutes for genuine review, owner signatures or session activation.

This software is not legal, tax or investment advice and is not a licensed adviser.
