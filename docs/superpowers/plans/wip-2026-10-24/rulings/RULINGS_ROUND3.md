# Controller rulings on the drafted tasks' open issues (round 3, 2026-10-28)

These rule on the open issues the task drafters reported. They amend the CONTRACT, TASKS and RULINGS files of each
plan; where a task text and this file disagree, this file wins. Every ruling either accepts a reading that refuses
more, or fixes which task owns a piece of work. None loosens a check.

## Both plans

- G3-1 Expected counts. Every count a task prints comes from the drafts, not from a run on the merged tree. A run
  with 0 failed and a different count passes; the executor writes the run's count and the reason in the ledger.
  A FAIL never passes.
- G3-2 Time budgets. A module over its contract target is recorded in the ledger with its measured time; no test is
  weakened or dropped to fit. A module over twice its target is a ruling for the controller, who may split it.
- G3-3 GitHub. The repo is public (owner, 2026-10-24). During execution the controller pushes the feature branch
  after each task's review passes and opens one pull request per plan at the end. Merging stays the owner's choice
  (superpowers:finishing-a-development-branch). No subagent pushes.
- G3-4 Real-home watch. A run that spans 09:00 to 09:10 KST can see the daily alert job write to the real
  `~/.tradegen/compliance` or `~/.tradegen/execution`. Write one ledger line and rerun outside that window.
- G3-5 Sandbox leftovers under the scratchpad (repo copies, about 165 MB) are not plan material and are not copied
  into the WIP folder.

## Odds plan

- O3-1 Task 1's stricter readings are accepted: `_CORE_ALSO_BANNED` binds `core/odds` only; `core.compliance`
  imports are limited to model, rules, gate and owner; `core/odds` holds only the Q1 files, `venues.yaml` and
  `__pycache__`; the name `open` counts as file I/O when read. Binding on Tasks 5 to 14: no local name `open` in
  `core/odds`.
- O3-2 Task 1 imports `CG._suite_names` from `tests.compliance_guards`: accepted (the name is fixed for E1 too).
- O3-3 `tests/odds_acceptance._main` imports `tests.odds_acceptance as suite` so `REAL_SEAMS` is the imported
  module's: accepted; Task 15's seam tests depend on it.
- O3-4 Task 3: `effective_from: "2026-10-02"` (the research note's as-of date) is accepted as the conservative
  date; the owner may sign a better-sourced one. The kis lot and min_order cite README line 161 as CONTRACT 4.2 says.
- O3-5 Task 4: `calendar_in_force` checks the whole owner state (stricter than the old line): accepted. The unused
  `import contextlib` in `tests/compliance_store.py` stays, because the follow-up's Edit T0 anchors on it.
- O3-6 Task 5 contract changes are adopted into CONTRACT 3.2, 5.3 and 14.2: the `series()` fixture's default is
  `start=None` (the walk ends the day before the plan's start); MULTI_LEG_UNSUPPORTED is for two or more legs; an
  empty legs list or a non-Leg item is UNSUPPORTED_PRODUCT sub `file`. Task 18's `load_plans` turns JSON ints for
  `stake_krw`, `target_krw` and `fx_krw_per_usd` into floats and builds `Plan(leg=<Leg>)` from a one-item list.
- O3-7 STATE_UNUSABLE sub `code` and LIMITS_UNSET sub `cap` have no catalogue sub text: Task 12's render prints the
  code's `why.*` sentence and ignores a sub that has no `sub.*` key. Binding on Task 12.
- O3-8 Task 6: an OKX cap that is not a finite number in (0, 1] gives `first_stake` 0.0, never TypeError (the gate's
  `_cap` rule); `kappa_bound` over every distinct date; the ladder `effective_from` check on every ladder;
  `kappa_bound` returns `math.inf` for `p_min <= 0`, which Tasks 12 and 14 render as `hidden.unbounded`. Accepted.
- O3-9 Task 11: the engine-run test asserts what the final draft asserts: `col.rungs == (k, k, k, 0, k)` and the
  mean-excess bound `-1e-6 <= excess <= 0.01`, with no second short run. "Leaves no path running" and "some path
  ends within KRW 1 of T" are dropped, because a lot of 1e-12 BTC with a KRW 0 minimum never reaches the floor.
  Also accepted: T11-2 (the Terms are built directly with every contract 6.2 field) and T11-3 (one chunk of 20,000
  paths through `OF.chunk(20_000)`). CONTRACT 16.1 follows. The Clopper-Pearson level is 0.999; a failure is a
  ruling, never a reseed.
- O3-10 Task 12: the catalogue keys `label.yes` and `label.no` are added to CONTRACT 10.4 (193 keys) and to the
  catalogue sha pin. `flags_for` reads `headline.reached`. Task 12 renders the replay card lines; Task 17 fills the
  mapping only and never edits `render` (DRIFT RULE if the lines are already there).
- O3-11 Task 14 wires `report.hidden_range` into bootstrap columns before passing `hidden_edge(headline)`, so a
  bootstrap card never prints the GARCH-t sentence. Binding on Task 14; the consistency check confirms it.
- O3-12 Task 15: `read_cached(source, symbol, start, end)` and `write_cached(part, start, end, now)`, the key's end
  being the first non-final date; the cache fails closed on a manifest line that does not parse. Accepted.
- O3-13 Task 16: the KR md5s are in file-id order (holidays_KRX, kr_regime_tags, kr_sessions); `begin_run`'s extra
  ValueErrors before any write are accepted. Tasks 12 to 14 and 18 follow that order.
- O3-14 Task 18: `--help` exits 0; one `replay_s_c3()` result is shared by every replay plan of one invocation (its
  inputs are the same cache). A KRX or US plan, after owner acts 1 to 3 and 5 but before act 4, makes its read-only
  quote calls before `simulate` refuses CALENDAR_UNSIGNED: accepted as a stated limit in the plan header (quote
  reads only, as cockpit test_21 already makes; no account or order call).
- O3-15 Task 17's replay growth line uses h = checks - 1 = 29 daily moves on a 30-day horizon ("2.9%" against
  "2.6%"), because that is the column the engine runs. `block_growth(R1, 10, 30) = 1.029918` stays a separate pin.
  TASKS, CONTRACT Q38 and 16.1 follow; the header's "For spec rev 3.3" list carries it.
- O3-16 `simulate.context_provenance(ctx)` is public (Task 13). Task 18 passes it to the CLI's own refusal cards,
  so every card it prints carries provenance except the loader's card, which has no context.
- O3-17 Task 10's readings are accepted and listed for spec rev 3.3: a daily-loss breach stops trading for the rest
  of that Asia/Seoul date whatever names the exit (spec 7.3); worst_gap counts a locked stop's queued fill;
  `force_exit_from` also blocks entries; the delisting sale pays the normal exit charge at p(1-h). Entries at the
  limit-up price fill in the odds engine (spec 7.2 locks only exits), while `core/engine/orders.simulate_fill`
  refuses them: recorded as a deferred minor and handed to E3, whose adapters use the venue's own answers.
- O3-18 The HIDDEN_EDGE range is set in `simulate._column` right after `run_column` (Task 14), not inside
  `run_column` (contract 10.3); `ColumnStats` compare through
  `dataclasses.replace(col, brackets=None, x_range=0.0 if math.isnan(col.x_range) else col.x_range)` (Tasks 9, 13).
  Both are contract 10.1 and 10.3 errata.
- O3-19 The departures the drafts point at all go into the header's "For spec rev 3.3" list, one bullet each: Task
  12 D1 to D3; Task 15's series dated on each market's own date; O3-15; O3-17; O3-18; Task 18's one `load_context`
  per distinct stake; O3-6's leg-count rule. Task 12 D4 (`label.yes`, `label.no`, 193 keys) and D5 (where
  `replay.noedge` sits) are CONTRACT 10.4 errata.
- O3-20 File ownership (CONTRACT 2 and the header file map follow the tasks): `tests/odds_fixtures.py` Tasks 1, 5,
  9, 13 and 14 (Task 13 adds `calendar_signed`, `CAL_SHA`, `spy`, `owner_with`, `fresh_series`, `weekdays`,
  `pipeline_inputs`, `pipeline`; Task 14 adds `members`, `garch_series`); `core/odds/report.py` Tasks 9 and 12;
  `tests/odds_simulate.py` Tasks 9, 10, 17; `tests/odds_pipeline.py` Tasks 13, 14, 17; the `series()` default is
  `start=None`.
- O3-21 Measured margins that differ from the contract's sandbox numbers but still hold (Task 8's R2-9 margins on
  the real pilot stream) are accepted; the executor records the printed values under "Runs".
- O3-22 E2 hand-off items from the odds drafts: `first_stake = floor_units(cap x W0) x p0` can exceed cap x equity
  by one ulp, which the gate would BLOCK as "cap exceeded"; the odds engine's limit-up entries (O3-17).

## E1 plan

- E3-1 Task 1's stricter guards are accepted (the extra `os` write calls, `Path.symlink_to`/`hardlink_to`, a
  one-argument `.replace()`, a non-constant open mode, an uncalled `os.system`, the import allowlist forms).
- E3-2 Task 4: `write_lines` opens `a+b`; `load` turns RecursionError into ValueError; `flags` becomes a frozenset.
  Binding on Tasks 10 and 12: `write_lines` is called only inside `exclusive()` on the same folder.
- E3-3 Routes are keyed `(method, path)` (Task 5), so the three venues' routes merge with `|`; CONTRACT 3.2's
  comment follows. Task 12's `_routes()` accepts either key form. Binding on Tasks 3, 5, 6, 7 and 12.
- E3-4 Task 7's stricter readings (any EVENTS row sets EVENTS; any other nonzero non-MARGIN position sets
  `derivative_position`) are accepted. A live algo row without `px` is an E1R2-5 live follow-up.
- E3-5 Task 8: `live_positions` returns None when the venue sum is not finite (added to E17). An empty account is
  `Positions(equity_krw=0.0)` while `owner._positions_problem` refuses `<= 0`: E1 never passes live positions to
  `load_context` (E24), so this is an E2 hand-off item.
- E3-6 `checks.Alert` is `kw_only=True` (CONTRACT 15 wins over 16.2's positional examples); every caller names every
  field. Binding on Task 12.
- E3-7 Task 11: `due` skips any row that fails `verify_row`; `_is_stamp` requires a real instant; `limits_from`
  gives None while `owner.ok` is False. Accepted.
- E3-8 Task 12: the test-only memo of the signed `load_context` per Seoul date is accepted with its `ponytail:`
  comment; the E24 test still calls the real function unsigned. Over the 60 s suite budget, G3-2 applies.
