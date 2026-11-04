# Offline launch workflow

`execution_launch.workflow` connects explicit files to the existing deterministic
program, paper recorder, evaluator and unsigned review-request builder. It gives
the operator executable steps before account configuration is available. It
never contacts an exchange, reads credentials, loads an owner log, signs, arms,
creates a background process or submits an order.

## Run a complete synthetic example

The generator writes four matching input files into an explicitly named **new**
directory. Every value and quote is invented; this cash baseline makes no trades,
cannot qualify as a live strategy, and supplies no owner approvals. Existing
directories, conventional home directories and linked/private destinations are
refused. Run from the repository
root using the configured Python environment, selecting a fresh output directory:

```sh
python -m tools.research.prepare_launch_example --directory /tmp/tradegen-synthetic-example --now 2030-01-01T12:00:00+00:00
python -m execution_launch.workflow record --profile /tmp/tradegen-synthetic-example/profile.json --protocol /tmp/tradegen-synthetic-example/protocol.json --program /tmp/tradegen-synthetic-example/program.json --bars /tmp/tradegen-synthetic-example/bars.json --now 2030-01-01T12:00:00+00:00 --emit-capture > /tmp/tradegen-synthetic-example/capture.json
python -m execution_launch.workflow evaluate --profile /tmp/tradegen-synthetic-example/profile.json --protocol /tmp/tradegen-synthetic-example/protocol.json --capture /tmp/tradegen-synthetic-example/capture.json --now 2030-01-01T12:00:00+00:00
python -m execution_launch.workflow request-review --profile /tmp/tradegen-synthetic-example/profile.json --protocol /tmp/tradegen-synthetic-example/protocol.json --program /tmp/tradegen-synthetic-example/program.json --capture /tmp/tradegen-synthetic-example/capture.json --now 2030-01-01T12:00:00+00:00 > /tmp/tradegen-synthetic-example/unsigned-review-request.json
```

Stop on any command failure. The example timestamp is deliberately synthetic,
not a claimed present observation. Expected evaluation: `source_kind=synthetic`,
60 observations, zero completed roundtrips, `math_qualified=false` and
`execution_ready=false`. The final file is an unsigned review request whose
authority flags remain false. Regenerate into another new directory after
changing the program or capture source; the example binds the actual installed
source bytes, so stale hashes are rejected. Keep real owner data out of examples.

## Inputs and commands

Use the repository's configured Python environment. All paths are explicit and
all times include a UTC offset. Files must be bounded regular JSON files; linked
paths, hard links, credential/state directories, duplicate keys and nonfinite
numbers are refused. Configuration files are limited to 64 KiB and capture files
to 16 MiB. The current file reader requires POSIX no-follow/descriptor support;
unsupported platforms refuse rather than weaken the boundary.

1. Prepare a private profile using the existing template:

   ```sh
   python -m execution_launch.cli --template
   ```

   Provide the instrument's exact lot, tick, minimum and fee terms and a private
   account scope. Missing exceptional-day loss budgets may remain null for
   offline arithmetic; this does not make the profile ready for execution.
   Actual initial capital, instrument terms, strategy identity and stable profile
   binding must agree with the study protocol. Changing those inputs later changes
   the binding and requires appropriate new evidence; do not relabel old results.

2. Create an explicit program specification. For example, the non-trading cash
   baseline uses the following complete schema:

   ```json
   {
     "schema_version": 1,
     "strategy_id": "research-cash-baseline",
     "kind": "cash",
     "fast_window": 0,
     "slow_window": 0,
     "exposure_fraction": "0"
   }
   ```

   The alternative `moving_average_trend` needs explicit fast/slow windows and
   exposure. No parameter set is selected or represented as profitable by this
   workflow. Inspect the actual installed program/capture code digests:

   ```sh
   python -m execution_launch.workflow inspect-program --program program.json
   ```

   The output supplies `program_digest`, `program_artifact_sha256` and
   `capture_source_code_sha256`. Use the program digest in the private profile
   and protocol. The capture digest identifies this installed batch recorder;
   an actual streaming feed may instead need a reviewed source/adapter manifest.
   A hash proves content identity, not origin, publication time or review.

3. Supply a protocol built through `ForwardProtocol`/`protocol_json` and its
   immutable registration chain. The complete protocol schema and statistical
   requirements are documented in [forward validation](forward-strategy-validation.md).
   No command fabricates registration publication, current rule provenance or
   source review. Registration before a claimed capture date is not itself proof
   that publication occurred before data was observed.

4. For a batch replay, supply `bars.json` with exactly `registry`, `bars` and
   `source_kind`. Each bar has aware `observed_at`/`received_at`, decimal-string
   `bid`, `ask`, `mark`, `quote_krw`, and `source_sha256`; rows follow the declared
   protocol cadence. The only accepted batch labels are `synthetic` and
   `retrospective_replay`. The recorder generates causal history-bound decisions
   from the selected program rather than accepting supplied decisions or PASS.

   ```sh
   python -m execution_launch.workflow record --profile private-profile.json --protocol protocol.json --program program.json --bars bars.json --now 2030-01-01T12:00:00+00:00
   ```

   Replace the example timestamp with the actual explicit evaluation instant.
   The default result contains only counts, a capture digest, source classification
   and fixed diagnostics. It does not print private profile values or records.
   Add `--emit-capture` to explicitly print the full replay archive to stdout:

   ```sh
   python -m execution_launch.workflow record --profile private-profile.json --protocol protocol.json --program program.json --bars bars.json --now 2030-01-01T12:00:00+00:00 --emit-capture > private-capture.json
   ```

   The shell performs that explicitly requested redirection; the Python command
   itself never opens an output file. Choose the destination privately and avoid
   overwriting an existing capture. Batch input cannot be upgraded to prospective
   capture by a command flag or a JSON source label. The separate injected-clock
   streaming recorder remains an owner-operated library integration.

5. Recompute paper results from a complete archive:

   ```sh
   python -m execution_launch.workflow evaluate --profile private-profile.json --protocol protocol.json --capture private-capture.json --now 2030-01-01T12:00:00+00:00
   ```

   This calls the existing exact cost/lot evaluator, including delayed execution,
   cost stress and declared-family adjustment. The diagnostic contains return
   ratios, drawdown, observation/roundtrip counts, p-value and binding digests.
   Absolute cash, fees, turnover, account aliases and input paths are omitted.
   File input has no authenticated origin: synthetic input stays synthetic;
   other labels are treated as retrospective replay for this diagnostic. Neither
   successful arithmetic nor `math_qualified=true` establishes source review,
   owner approval or execution readiness.

6. Produce a review request when the complete original capture and program are
   ready for independent review:

   ```sh
   python -m execution_launch.workflow request-review --profile private-profile.json --protocol protocol.json --program program.json --capture private-capture.json --now 2030-01-01T12:00:00+00:00 > unsigned-review-request.json
   ```

   This command recomputes arithmetic and checks the actual installed program
   artifact/parameters against the profile/protocol. It preserves the file's
   original source **claim** for review inside an explicitly unsigned artifact;
   `source_authenticated` remains false. Reviewer identity, key and signature
   remain absent. The artifact is neither a `ReviewReceipt` nor an implementation
   verifier and cannot approve a runner. Do not edit its status to simulate review.

## Output and limits

Exit 0 means that an offline operation completed, including a negative strategy
result. Exit 2 means missing, invalid or mismatched input. No exit code grants
trading permission. The default invocation returns a fixed missing-input
diagnostic without reading any file or environment value.

This is paper recording/evaluation, not the authenticated E2 order-lifecycle
rehearsal. That rehearsal remains separately covered by the runner integration
and its isolated dry-adapter tests. Actual account evidence, current policy
baselines, source/implementation review, effective owner signatures and the real
process-issued prepared session remain necessary for controlled execution.

The existing frozen historical study remains unchanged with zero passing
candidates. No genuine prospective study, real signature or live order is
created by these commands. This software is not legal, tax or investment advice
and is not a licensed adviser.
