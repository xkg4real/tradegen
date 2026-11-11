# Read-only Loss-floor State Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `tools/floor_state_check.py`, the read-only command of step 0 in the principal loss budget design: it reads the owner log, the control journal and the reviewed account baseline, and prints one fixed code per row S1 to S12.

**Architecture:** One script outside the signed code closure and one test module in the `execution_launch` suite. The script calls only read paths that already exist (`owner._owner_now`, `Journal.snapshot`, `BaselineHead.read`, `CheckpointStore.load`, `restore_state`) and compares what they return with three typed amounts. It never writes, never sets the environment and never prints an amount, a path, a digest or a session id.

**Tech Stack:** Python 3.13, standard library only, the repository's own modules. Tests are plain `assert` functions collected by `tests/launch_acceptance.py`.

**Spec:** `docs/superpowers/specs/2026-11-11-principal-loss-budget-design.md`, sections 8.2 and 9.1 (rows S1 to S12, inputs, output, reads). Base: `origin/main` at `249cc3d` (written at `59a4eb8`; universe PRs #21, #24 and #25 and docs PR #22 merged since. Every line this plan cites was checked again there: two had moved and are updated).

## Global Constraints

- The script lives at `tools/floor_state_check.py`. Not under `tools/owner/`. Never create `tools/__init__.py`. No file in the signed closure may import the script. Any of these three would change the code hash and unsign the code.
- No file under `core/compliance`, `core/odds`, `execution`, `execution_control`, `execution_orders`, `execution_accounts`, `execution_network`, `execution_launch` or `tools/owner` is edited.
- Reads only. Never call `load_context` (it writes a snapshot), `append_system_entry`, `Journal.transaction`, `seed`, `commit`, `initialize_reviewed_head` or `compare_and_set`. Never read or set `os.environ`. Never import `config` (it loads `.env`).
- `--state-root` does not select a home. It must equal `core.isolation.state_root().absolute()`; otherwise refuse. A relative value never equals it.
- Output: fixed codes only. Never print an exception message: the isolation and owner-log messages contain paths and log content. Ctrl-C during a read gets the fixed failure code too: a traceback names source paths.
- Exit 0: every row read (with `--gate`: and every gate row is go). Exit 1: `--gate` and a gate row is not go. Exit 2: an argument was refused or some state could not be read. An empty argument list is refused: it reads nothing, so it must not exit 0. Only `--help` or `-h` alone prints the usage.
- Tests call `main(argv)` in-process. No `subprocess`, no `sys.executable`, no `importlib.reload` (`tests/launch_guards.py:684-693`). Nothing touches state at module import. Every home and head root is temporary.
- New files are LF, UTF-8, no BOM. `tests/launch_acceptance.py` is LF. Check `git diff --stat` equals `git diff --stat --ignore-cr-at-eol`.
- Commit messages end with a `Co-Authored-By: Claude ... <noreply@anthropic.com>` trailer that names the model that wrote them.
- README totals and `qa/acceptance_results.json` are not changed by this plan. A `tests/run_all.py` run rewrites `qa/acceptance_results.json`; restore it with `git checkout -- qa/acceptance_results.json` after every run.

## File Structure

| File | Responsibility |
|---|---|
| Create `tools/floor_state_check.py` | Arguments, the home rule, the three readers, the row table, the gate, `main`. |
| Create `tests/launch_floor_state_check.py` | Fixtures for a temporary signed home, journal rows and an anchor; one test per behaviour. |
| Modify `tests/launch_acceptance.py:16` | Add the test module's stem to `MODULES`. |

## Contract

Command, run from the repository root:

```text
python -m tools.floor_state_check --state-root ROOT --head-root HEAD_ROOT --principal W0 --floor C --activation A
    [--candidate STATE.json --candidate-head HASH] [--session SESSION_ID] [--gate]
```

- `--floor` is the budget floor `C = W0 - LB`. The three amounts are plain decimal strings and must satisfy `0 < C < W0 <= A`.
- `--candidate` and `--candidate-head` come together. With them, rows S4, S7, S10 and S11 read that anchor file instead of the stored baseline, with the same call `setup-account` uses.
- Output: one line per row for the owner, then one JSON line `{"gate": ..., "rows": {...}}`. A refusal prints only `{"refused": CODE}`.

| Key | Reads | Values |
|---|---|---|
| `S1` | owner log verifies | `yes`, `empty` (verifies with no entry), `no` |
| `S2` | `system_halt` in the owner log | `none`, `present` |
| `S3` | `halt` row in the control journal | `none`, `present`, `no_journal` |
| `S4` | highest of the journaled peak and the anchor peak, against `A` | `none`, `below`, `at_or_above` |
| `S5` | last journaled effective floor against `C` | `none`, `above`, `equal`, `below` |
| `S6` | signed floor in force today against `C` | `unset`, `above`, `equal`, `below` |
| `S7` | anchor floor against `C` | `none`, `null`, `above`, `equal`, `below` |
| `S8` | armed sessions | `none`, `present` |
| `S9_home`, `S9_journal` | default or custom home; control journal folder | `default`, `custom`; `absent`, `present` |
| `S10` | anchor equity against `W0` | `none`, `above`, `equal`, `below` |
| `S11` | anchor equity against the highest of its own floor, the last journaled floor and the signed floor | `none`, `at_or_above`, `below` |
| `S12` | signed floor inside `--session` against `C` | `not_requested`, `not_armed`, `unset`, `above`, `equal`, `below` |

Every row except `S1`, `S9_home` and `S9_journal` can read `unreadable`; an owner log that cannot be read is `S1` `no`. Refusal codes: `STATE_CHECK_ARGUMENTS_INVALID`, `STATE_CHECK_STATE_ROOT_MISMATCH`, `STATE_CHECK_STATE_ROOT_REFUSED`, `STATE_CHECK_FAILED`.

Gate (spec 9.1): go when `S2` is `none`, `S3` is `none` or `no_journal`, `S4` is `none` or `below`, `S6` and `S7` are `equal`, `S10` is `equal` or `below`, `S11` is `at_or_above`, and `S12` is `not_requested` or `equal`.

Four readings of the spec that this plan fixes:

- S6 reads the signed floor only. The floor and the daily limit are signed in one `limit_set` entry, and a first setting of either waits one Seoul date, so the two are unset together. S1 is not in the gate: when the log does not verify or is empty, S6 is not `equal`.
- The spec's gate sentence names `none` for S3; its S3 row gives "none, or no journal" as go. A home that never ran has no journal, and that is the expected case at step 10, so the gate accepts `no_journal`.
- The spec does not say when a journal is "absent". Here: the folder `execution-control` under the home does not exist. A folder that exists but cannot be read by `Journal.snapshot()` is `unreadable`.
- The spec's gate sentence does not name S12; its S12 row gives `equal` as go, and no code checks it before the runner starts. Inside a session armed on or before the loosening's date, the signed floor is the earlier one, or unset. Its buys are refused (spec 2.5b), and when equity is below that earlier floor the first buy evaluation halts for good (spec 2.5a, 10.3). So with `--session` the gate also needs `S12` `equal`. Without `--session`, `S12` is `not_requested` and the gate is the gate of step 10.

---

### Task 1: Tests and registration

**Files:**
- Create: `tests/launch_floor_state_check.py`
- Modify: `tests/launch_acceptance.py:16`

**Interfaces:**
- Consumes: `tests.compliance_fixtures` (`temp_home`, `pubkey_at`, `owner_key`, `sign`), `tests.launch_baseline_head.head_root`, `execution_control.store.Journal`, `execution_accounts.baseline` (`BaselineAnchor`, `BaselineConventions`, `initialize_baseline`, `state_json`), `execution_accounts.baseline_store.CheckpointStore`, `execution_launch.baseline_head` (`BaselineHead`, `CheckpointChain`).
- Produces: the expectations Task 2 must meet: `tools.floor_state_check.main(argv=None, *, now=None) -> int`, the module attributes `state_root` and `_default_home`, and the output contract above.

- [ ] **Step 1: Write the test module**

<!-- file: tests/launch_floor_state_check.py -->
```python
"""Read-only loss-floor state check (tools/floor_state_check.py): rows, exit codes, no write and no echo."""
import ast
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from decimal import Decimal
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from core.compliance import owner
from core.compliance.model import KST
from execution_accounts.baseline import BaselineAnchor, BaselineConventions, initialize_baseline, state_json
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import RiskBaseline
from execution_control.store import Journal
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from tests import compliance_fixtures as F
from tests.launch_baseline_head import head_root
from tools import floor_state_check as S

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
W0, C, A = "100000", "80000", "150000"
SIGNED = "2026-10-23T03:00:00Z"                              # 12:00 on 23 October in Seoul
SAME_DAY = datetime(2026, 10, 23, 15, 0, tzinfo=KST)
NEXT_DAY = datetime(2026, 10, 24, 12, 0, tzinfo=KST)
ASOF = datetime(2026, 10, 24, 1, 0, tzinfo=timezone.utc)
ALL_NONE = {"S1": "empty", "S2": "none", "S3": "no_journal", "S4": "none", "S5": "none", "S6": "unset",
            "S7": "none", "S8": "none", "S9_home": "custom", "S9_journal": "absent", "S10": "none", "S11": "none",
            "S12": "not_requested"}


@contextmanager
def homes():
    """A temporary home that holds the test owner key, and a separate temporary head root."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"), head_root() as hroot:
        yield home, hroot, F.owner_key(home)


def listing(*roots):
    return sorted((str(path.relative_to(root)), path.stat().st_size, path.stat().st_mtime_ns)
                  for root in roots for path in root.rglob("*") if path.is_file())


def argv(home, hroot, **changes):
    values = {"state-root": str(home), "head-root": str(hroot), "principal": W0, "floor": C, "activation": A} | changes
    return [token for key, value in values.items() if value is not None for token in ("--" + key, value)]


def run(arguments):
    output = StringIO()
    with redirect_stdout(output):
        code = S.main(arguments, now=NEXT_DAY)
    return code, output.getvalue()


def invoke(home, hroot, *extra, now=NEXT_DAY, **changes):
    """(exit code, the JSON of the last line, the whole output). Fails if the run changed a file in either root."""
    before, output = listing(home, hroot), StringIO()
    with redirect_stdout(output):
        code = S.main(argv(home, hroot, **changes) + list(extra), now=now)
    assert listing(home, hroot) == before, "the state check changed a file"
    lines = output.getvalue().splitlines()
    report = json.loads(lines[-1])
    assert [(line.split()[0], line.split()[-1]) for line in lines[:-1]] == [
        (key, report["rows"][key]) for key in ALL_NONE], "the owner's table disagrees with the JSON line"
    return code, report, output.getvalue()


def limits(key, floor, utc=SIGNED):
    F.sign(key, "limit_set", {"total_loss_floor_krw": float(floor), "daily_loss_krw": 5000.0}, utc)


def anchor_state(*, floor=C, peak=W0, equity=W0):
    day = ASOF.astimezone(KST).date()
    base = RiskBaseline(day_start_equity=D(equity), prior_high_watermark=D(peak), observed_daily_loss=D("0"),
        approved_effective_floor=None if floor is None else D(floor), first_trading_day=day, asof=ASOF,
        source_sha256="a" * 64)
    anchor = BaselineAnchor(account_scope="state-check-fixture", baseline=base, equity_krw=D(equity),
        realized_net_total_krw=D("0"), day_open_realized_net_total_krw=D("0"),
        previous_day_realized_net_krw=None, sequence=0)
    conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=30)
    return initialize_baseline(conventions, anchor)


def seed(home, hroot, state):
    store = CheckpointStore(root=home)
    store.seed(state, expected_head=state.state_digest)
    BaselineHead(root=hroot, name="account-baseline",
                 chain=CheckpointChain(store)).initialize_reviewed_head(state.state_digest)


def risk(high, floor):
    return ("risk_snapshot", {"policy_digest": "a" * 64, "day": "2026-10-24", "high_watermark": high,
                              "day_start_equity": high, "effective_floor": floor, "calculated_floor": floor,
                              "daily_stopped": False, "floor_relaxation_approved": False})


def journal(*rows):
    with Journal().transaction() as tx:
        for kind, data in rows:
            tx.append(kind, data, now=ASOF)


def test_a_fresh_home_reads_none_in_every_row_and_nothing_is_created():
    with homes() as (home, hroot, _):
        code, report, text = invoke(home, hroot)
        assert code == 0 and report == {"gate": "not_requested", "rows": ALL_NONE}
        assert [line.split(None, 1)[1].rsplit(None, 1)[0] for line in text.splitlines()[:-1]] == [
            "owner log verifies", "halt in the owner log", "halt in the control journal",
            "highest recorded peak against A", "last journaled floor against C", "signed floor in force against C",
            "anchor floor against C", "armed sessions", "home", "control journal folder", "anchor equity against W0",
            "anchor equity against highest floor", "signed floor inside --session"], "the owner's labels"
        assert sorted(path.name for path in home.iterdir()) == ["owner_pubkey.pem"] and list(hroot.iterdir()) == []


def test_a_missing_owner_key_makes_the_owner_rows_unreadable_and_exits_2():
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"), head_root() as hroot:
        seed(home, hroot, anchor_state())
        code, report, _ = invoke(home, hroot, "--session", "ARMED7")
        rows = report["rows"]
        assert code == 2 and rows["S1"] == "no"
        assert [rows[key] for key in ("S2", "S6", "S8", "S12")] == ["unreadable"] * 4
        assert rows["S3"] == "no_journal" and rows["S7"] == "equal", "the other readers still report"
        assert rows["S11"] == "unreadable", "the signed floor is one of the three it compares"
        assert invoke(home, hroot)[1]["rows"]["S12"] == "not_requested"


def test_a_signed_floor_counts_from_the_next_seoul_date_and_is_compared_with_the_budget_floor():
    with homes() as (home, hroot, key):
        limits(key, C)
        assert invoke(home, hroot, now=SAME_DAY)[1]["rows"]["S6"] == "unset", "a first setting waits a day (D12)"
        rows = invoke(home, hroot)[1]["rows"]
        assert rows["S1"] == "yes" and rows["S6"] == "equal"
        assert invoke(home, hroot, floor="79999")[1]["rows"]["S6"] == "above"
        assert invoke(home, hroot, floor="80001")[1]["rows"]["S6"] == "below"
        early = datetime(2026, 10, 23, 15, 30, tzinfo=timezone.utc)        # 00:30 on 24 October in Seoul
        assert invoke(home, hroot, now=early)[1]["rows"]["S6"] == "equal", "the Seoul date, not the UTC date"


def test_an_owner_log_halt_and_an_armed_session_are_reported():
    with homes() as (home, hroot, key):
        limits(key, C)
        assert [invoke(home, hroot)[1]["rows"][key] for key in ("S2", "S8")] == ["none", "none"]
        F.sign(key, "session_armed", {"session_id": "ARMED7"}, "2026-10-24T01:00:00Z")
        owner.append_system_entry("system_halt", {"floor_krw": 80000.0}, NEXT_DAY)
        assert [invoke(home, hroot)[1]["rows"][key] for key in ("S2", "S8")] == ["present", "present"]


def test_the_floor_inside_a_session_armed_on_the_signing_date_is_the_earlier_one():
    with homes() as (home, hroot, key):
        limits(key, "90000", "2026-10-21T03:00:00Z")                      # in force from 22 October
        limits(key, C)                                                      # lower: counts from 24 October
        F.sign(key, "session_armed", {"session_id": "ARMED7"}, "2026-10-23T04:00:00Z")
        rows = invoke(home, hroot, "--session", "ARMED7")[1]["rows"]
        assert rows["S6"] == "equal" and rows["S12"] == "above", "the loosening does not count inside that session"
        assert invoke(home, hroot, "--session", "OTHER")[1]["rows"]["S12"] == "not_armed"
        assert invoke(home, hroot)[1]["rows"]["S12"] == "not_requested"


def test_journal_rows_give_the_halt_the_peak_and_the_last_floor():
    with homes() as (home, hroot, _):
        journal(risk("100000", None), ("kill", {"session_id": "ARMED7", "reason": "operator"}))
        rows = invoke(home, hroot)[1]["rows"]
        assert (rows["S3"], rows["S4"], rows["S5"], rows["S9_journal"]) == ("none", "below", "none", "present")
        journal(risk("120000", "90000"), risk("120000", "80000"))
        rows = invoke(home, hroot)[1]["rows"]
        assert (rows["S3"], rows["S4"], rows["S5"]) == ("none", "below", "equal"), "the last floor, not the highest"
        assert invoke(home, hroot, activation="120000")[1]["rows"]["S4"] == "at_or_above", "equality activates"
        assert invoke(home, hroot, floor="79999")[1]["rows"]["S5"] == "above"
        assert invoke(home, hroot, floor="80001")[1]["rows"]["S5"] == "below"
        journal(("halt", {"floor": "80000"}))
        assert invoke(home, hroot)[1]["rows"]["S3"] == "present"


def test_a_partial_journal_or_a_malformed_row_is_unreadable_and_exits_2():
    with homes() as (home, hroot, _):
        seed(home, hroot, anchor_state())
        journal(risk("100000", "80000"))
        (home / "execution-control" / "checkpoint.json").unlink()
        code, report, _ = invoke(home, hroot)
        assert code == 2 and [report["rows"][key] for key in ("S3", "S4", "S5", "S11")] == ["unreadable"] * 4
        assert report["rows"]["S9_journal"] == "present" and report["rows"]["S7"] == "equal"
    for data in ({}, risk("not a number", None)[1], risk("100000", 80000)[1], risk("NaN", None)[1],
                 risk("-1", None)[1], risk("100000", "Infinity")[1]):
        with homes() as (home, hroot, _):
            journal(("risk_snapshot", data))
            code, report, _ = invoke(home, hroot)
            assert code == 2 and report["rows"]["S4"] == "unreadable", data


def test_the_journal_folder_name_matches_the_store():
    with homes() as (home, _, _):
        assert Journal()._root == home / "execution-control"
        assert CheckpointStore._DIRECTORY == "execution-baseline"


def test_the_stored_anchor_gives_its_floor_peak_and_equity():
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state())
        code, report, _ = invoke(home, hroot)
        rows = report["rows"]
        assert code == 0 and (rows["S4"], rows["S7"], rows["S10"], rows["S11"]) == (
            "below", "equal", "equal", "at_or_above")
    for change, row, expected in (({"floor": "90000"}, "S7", "above"), ({"floor": "70000"}, "S7", "below"),
                                  ({"floor": None}, "S7", "null"),
                                  ({"equity": "120000", "peak": "120000"}, "S10", "above"),
                                  ({"equity": "90000"}, "S10", "below"), ({"equity": "75000"}, "S11", "below"),
                                  ({"peak": "150000"}, "S4", "at_or_above")):
        with homes() as (home, hroot, key):
            limits(key, C)
            seed(home, hroot, anchor_state(**change))
            assert invoke(home, hroot)[1]["rows"][row] == expected, (change, row)


def test_anchor_equity_is_compared_with_the_highest_of_three_floors():
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state())
        journal(risk("120000", "110000"))
        rows = invoke(home, hroot)[1]["rows"]
        assert rows["S11"] == "below" and rows["S4"] == "below", "the journaled floor is the highest"
    with homes() as (home, hroot, key):
        limits(key, "100001")
        seed(home, hroot, anchor_state())
        assert invoke(home, hroot)[1]["rows"]["S11"] == "below", "the signed floor is the highest"
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state(floor="100001"))
        assert invoke(home, hroot)[1]["rows"]["S11"] == "below", "its own floor is the highest"
    with homes() as (home, hroot, key):
        limits(key, W0)
        seed(home, hroot, anchor_state())
        assert invoke(home, hroot)[1]["rows"]["S11"] == "at_or_above", "equity at the floor is not below it"
    with homes() as (home, hroot, _):
        seed(home, hroot, anchor_state(floor=None))
        assert invoke(home, hroot)[1]["rows"]["S11"] == "at_or_above", "no floor at all"


def test_a_checkpoint_without_its_head_or_a_missing_head_root_is_unreadable():
    state = anchor_state()
    with homes() as (home, hroot, _):
        CheckpointStore(root=home).seed(state, expected_head=state.state_digest)       # the head was never set
        code, report, _ = invoke(home, hroot)
        assert code == 2 and [report["rows"][key] for key in ("S4", "S7", "S10", "S11")] == ["unreadable"] * 4
    with homes() as (home, hroot, _):
        code, report, _ = invoke(home, hroot / "missing")
        assert code == 2 and report["rows"]["S7"] == "unreadable"


def test_a_candidate_anchor_is_read_in_place_of_the_store():
    state = anchor_state()
    with homes() as (home, hroot, key), tempfile.TemporaryDirectory() as folder:
        limits(key, C)
        seed(home, hroot, anchor_state(floor="100001", peak="150000", equity="75000"))  # differs in every row
        path = Path(os.path.realpath(folder)) / "anchor.json"
        path.write_text(state_json(state), encoding="ascii")
        code, report, text = invoke(home, hroot, "--candidate", str(path), "--candidate-head", state.state_digest)
        rows = report["rows"]
        assert code == 0 and (rows["S4"], rows["S7"], rows["S10"], rows["S11"]) == (
            "below", "equal", "equal", "at_or_above")
        assert path.parent.name not in text and state.state_digest not in text
        code, report, _ = invoke(home, hroot, "--candidate", str(path), "--candidate-head", "d" * 64)
        assert code == 2 and report["rows"]["S7"] == "unreadable"


def test_the_gate_passes_on_the_go_table_and_fails_on_each_single_miss():
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state())
        code, report, _ = invoke(home, hroot, "--gate")
        assert code == 0 and report["gate"] == "go" and report["rows"]["S3"] == "no_journal"
        assert invoke(home, hroot)[1]["gate"] == "not_requested"
        for changes, why in (({"floor": "79999"}, "S6 and S7 above"), ({"activation": "100000"}, "S4 at the peak"),
                             ({"principal": "99999"}, "S10 above")):
            code, report, _ = invoke(home, hroot, "--gate", **changes)
            assert code == 1 and report["gate"] == "no_go", why
        assert invoke(home, hroot, "--gate", now=SAME_DAY)[0] == 1, "S6 unset on the signing date"
        journal(risk("100000", "80000"))
        code, report, _ = invoke(home, hroot, "--gate")
        assert code == 0 and report["rows"]["S3"] == "none", "a journal with no halt is go"
        journal(("halt", {"floor": "80000"}))
        assert invoke(home, hroot, "--gate")[0] == 1, "S3 present"
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state(floor="90000"))
        code, report, _ = invoke(home, hroot, "--gate")
        assert code == 1 and report["rows"]["S6"] == "equal", "S7 above alone"
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state(equity="90000"))
        assert invoke(home, hroot, "--gate")[0] == 0, "equity below the principal is go"
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state(equity="75000"))
        assert invoke(home, hroot, "--gate")[0] == 1, "S11 below"
        assert invoke(home, hroot)[0] == 0, "without --gate a no-go row is still exit 0"
    with homes() as (home, hroot, key):
        limits(key, C)
        seed(home, hroot, anchor_state())
        owner.append_system_entry("system_halt", {"floor_krw": 80000.0}, NEXT_DAY)
        assert invoke(home, hroot, "--gate")[0] == 1, "S2 present"
    with homes() as (home, hroot, key):
        limits(key, C)
        assert invoke(home, hroot, "--gate")[0] == 1, "no anchor: S7, S10 and S11 read none"
        code, report, _ = invoke(home, hroot / "missing", "--gate")
        assert code == 2 and report["gate"] == "no_go", "unreadable is exit 2 even with --gate"
    for signed, own, why in (("90000", C, "S6 above alone"), ("70000", C, "S6 below alone"),
                             (C, "70000", "S7 below alone"), (C, None, "S7 null alone")):
        with homes() as (home, hroot, key):
            limits(key, signed)
            seed(home, hroot, anchor_state(floor=own))
            assert invoke(home, hroot, "--gate")[0] == 1, why
    with homes() as (home, hroot, key):
        limits(key, "90000", "2026-10-21T03:00:00Z")
        limits(key, C)
        F.sign(key, "session_armed", {"session_id": "ARMED7"}, "2026-10-23T04:00:00Z")
        F.sign(key, "session_armed", {"session_id": "LATER8"}, "2026-10-24T01:00:00Z")
        seed(home, hroot, anchor_state())
        assert invoke(home, hroot, "--gate")[0] == 0, "S12 was not asked for"
        assert invoke(home, hroot, "--gate", "--session", "LATER8")[0] == 0, "S12 equal"
        assert invoke(home, hroot, "--gate", "--session", "ARMED7")[0] == 1, "S12 above"
        assert invoke(home, hroot, "--gate", "--session", "OTHER")[0] == 1, "S12 not_armed"
    with homes() as (home, hroot, key):
        limits(key, C)                                                      # a first setting: counts from 24 October
        F.sign(key, "session_armed", {"session_id": "ARMED7"}, "2026-10-23T04:00:00Z")
        seed(home, hroot, anchor_state())
        code, report, _ = invoke(home, hroot, "--gate", "--session", "ARMED7")
        assert code == 1 and report["rows"]["S12"] == "unset", "S12 unset"


def test_the_state_root_must_be_the_configured_home_and_nothing_is_read_otherwise():
    with homes() as (home, hroot, _):
        for other in (home / "other", Path("relative")):
            with patch.object(owner, "_owner_now", side_effect=AssertionError("owner log read")):
                code, text = run(argv(other, hroot))
            assert code == 2 and json.loads(text) == {"refused": "STATE_CHECK_STATE_ROOT_MISMATCH"}, other
        with patch.object(S, "state_root", side_effect=RuntimeError("state root " + str(home) + " is a symlink")):
            code, text = run(argv(home, hroot))
        assert code == 2 and json.loads(text) == {"refused": "STATE_CHECK_STATE_ROOT_REFUSED"}
        assert str(home) not in text
        with patch.object(S, "state_root", lambda: Path.cwd() / "relative"), \
                patch.object(owner, "_owner_now", side_effect=AssertionError("owner log read")):
            code, text = run(argv("relative", hroot))
        assert code == 2 and json.loads(text) == {"refused": "STATE_CHECK_STATE_ROOT_MISMATCH"}, "relative"


def test_bad_arguments_get_one_fixed_code_and_read_nothing():
    with homes() as (home, hroot, _):
        good = argv(home, hroot)
        cases = (argv(home, hroot, activation=None), argv(home, hroot, **{"state-root": None}),
                 argv(home, hroot, **{"head-root": None}), good + ["--bogus", "1"], good + ["--floor", C],
                 argv(home, hroot, candidate="x.json"), argv(home, hroot, principal="1e5"),
                 argv(home, hroot, principal="100,000"), argv(home, hroot, floor=W0),
                 argv(home, hroot, activation="99999"), argv(home, hroot, floor="0"),
                 argv(home, hroot, **{"candidate": "x.json", "candidate-head": "not-a-digest"}),
                 good + ["--gate", "--gate"], good + ["--session"], good + ["--session", ""], ["--floor"], [],
                 good + ["--session", "--gate"], argv(home, hroot, **{"candidate-head": "a" * 64}))
        for arguments in cases:
            with patch.object(owner, "_owner_now", side_effect=AssertionError("owner log read")):
                code, text = run(arguments)
            assert code == 2 and json.loads(text) == {"refused": "STATE_CHECK_ARGUMENTS_INVALID"}, arguments


def test_an_unexpected_failure_prints_a_fixed_code_and_no_message():
    with homes() as (home, hroot, _):
        for failure in (KeyError(str(home)), KeyboardInterrupt()):
            try:
                with patch.object(owner, "_owner_now", side_effect=failure):
                    code, text = run(argv(home, hroot))
            except KeyboardInterrupt:
                raise AssertionError("Ctrl-C left main as a traceback") from None
            assert code == 2 and json.loads(text) == {"refused": "STATE_CHECK_FAILED"} and str(home) not in text


def test_the_output_holds_no_amount_path_digest_or_session_id():
    state = anchor_state()
    with homes() as (home, hroot, key):
        limits(key, C)
        F.sign(key, "session_armed", {"session_id": "ARMED7"}, "2026-10-24T01:00:00Z")
        seed(home, hroot, state)
        journal(risk("123456", "80000"), ("halt", {"floor": "80000"}))
        _, report, text = invoke(home, hroot, "--session", "ARMED7", "--gate")
        assert "unreadable" not in report["rows"].values() and report["rows"]["S8"] == "present"
        for secret in (str(home), str(hroot), home.name, hroot.name, state.state_digest, W0, C, A, "123456",
                       "5000", "ARMED7"):
            assert secret not in text, secret


def test_the_home_is_reported_as_default_or_custom():
    with homes() as (home, hroot, _):
        assert invoke(home, hroot)[1]["rows"]["S9_home"] == "custom"
        with patch.object(S, "_default_home", lambda: home):
            assert invoke(home, hroot)[1]["rows"]["S9_home"] == "default"


def test_help_prints_the_usage_and_reads_nothing():
    for arguments in (["--help"], ["-h"]):
        with patch.object(S, "state_root", side_effect=AssertionError("home read")):
            code, text = run(arguments)
        assert code == 0 and "python -m tools.floor_state_check" in text


def test_the_script_has_no_write_environment_network_or_process_shape():
    tree = ast.parse((ROOT / "tools" / "floor_state_check.py").read_text(encoding="utf-8"))
    nodes = list(ast.walk(tree))
    imported = {alias.name.split(".")[0] for node in nodes if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in nodes if isinstance(node, ast.ImportFrom)}
    assert imported <= {"__future__", "datetime", "decimal", "json", "pathlib", "re", "sys", "core",
                        "execution_accounts", "execution_control", "execution_launch"}, imported
    used = {node.attr for node in nodes if isinstance(node, ast.Attribute)}
    used |= {node.id for node in nodes if isinstance(node, ast.Name)}
    banned = {"load_context", "append_system_entry", "write_snapshot", "store_put", "transaction", "seed", "commit",
              "initialize_reviewed_head", "compare_and_set", "environ", "getenv", "putenv", "open", "mkdir",
              "makedirs", "write_text", "write_bytes", "unlink", "rename", "replace", "remove", "rmtree", "touch",
              "chmod", "system", "popen"}
    assert not used & banned, used & banned


def test_the_script_is_outside_the_signed_code_closure():
    names = {name for name, _ in owner.code_files(ROOT)}
    assert "tools/owner/launch.py" in names and "tools/floor_state_check.py" not in names
    assert not (ROOT / "tools" / "__init__.py").exists()
```

- [ ] **Step 2: Register the module**

In `tests/launch_acceptance.py`, replace the last line of the `MODULES` tuple

```python
           "launch_universe_store")
```

with

```python
           "launch_universe_store", "launch_floor_state_check")
```

- [ ] **Step 3: Run it and see it fail**

Run from the repository root, with the keyless environment and no `TRADEGEN_RUNS_DIR`:

```bash
python -m tests.launch_acceptance launch_floor_state_check
```

Expected: one row `FAIL launch_floor_state_check/import` with `ImportError: cannot import name 'floor_state_check' from 'tools'`, and the counts `{'PASS': 0, 'FAIL': 1, 'NOT_RUN': 0}`. This command does not write `qa/acceptance_results.json`.

- [ ] **Step 4: Commit**

```bash
git add tests/launch_floor_state_check.py tests/launch_acceptance.py
git commit -m "Add failing tests for the read-only loss-floor state check"
```

---

### Task 2: The script

**Files:**
- Create: `tools/floor_state_check.py`
- Test: `tests/launch_floor_state_check.py`

**Interfaces:**
- Consumes: `owner._owner_now(day, now_utc, session_id) -> (OwnerState, LogCheck | None)` (`core/compliance/owner.py:947`, the read-only half of `load_context`); `Journal().snapshot() -> tuple[dict, ...]` (`execution_control/store.py:232`); `CheckpointStore(root=home).load(expected_head=...)` and `BaselineHead(root=..., name="account-baseline", chain=CheckpointChain(store)).read()`; `restore_state(read_file(path, MAX_CONFIG_BYTES), expected_head=...)` (the read at `tools/owner/launch.py:141`).
- Produces: `main(argv=None, *, now=None) -> int`; `check(*, home, head_root, principal, floor, activation, candidate=None, candidate_head=None, session=None, now) -> dict[str, str]`; module attributes `state_root` and `_default_home` (the tests patch both).

- [ ] **Step 1: Write the script**

<!-- file: tools/floor_state_check.py -->
```python
"""Read-only loss-floor state check: step 0 of the principal loss budget design (spec 2026-11-11, section 9.1).

    python -m tools.floor_state_check --state-root ROOT --head-root HEAD_ROOT
        --principal W0 --floor C --activation A
        [--candidate STATE.json --candidate-head HASH] [--session SESSION_ID] [--gate]

Run it from the repository root with the project's own Python. It reads the owner log, the control journal and the
reviewed account baseline of the home that TRADEGEN_HOME selects. It creates and writes nothing, and it prints fixed
codes and relations only: never an amount, a path, a digest or a session id.

--state-root does not select a home; it must equal the configured one. --floor is the budget floor C = W0 - LB.
With --candidate, rows S4, S7, S10 and S11 read that anchor file instead of the stored baseline.

Rows (the go values are in the design, section 9.1):
  S1   owner log verifies                    yes | empty | no
  S2   halt in the owner log                 none | present
  S3   halt in the control journal           none | present | no_journal
  S4   highest recorded peak against A       none | below | at_or_above
  S5   last journaled floor against C        none | above | equal | below
  S6   signed floor in force against C       unset | above | equal | below
  S7   anchor floor against C                none | null | above | equal | below
  S8   armed sessions                        none | present
  S9   home; control journal folder          default | custom; absent | present
  S10  anchor equity against W0              none | above | equal | below
  S11  anchor equity against highest floor   none | at_or_above | below
  S12  signed floor inside --session         not_requested | not_armed | unset | above | equal | below
Every row except S1 and S9 can also read "unreadable".

Exit 0: every row was read, and with --gate every gate row is go: S2, S3, S4, S6, S7, S10, S11, and S12 when
--session is given (S1, S5, S8 and S9 are shown, not gated). Exit 1: --gate and a gate row is not go.
Exit 2: an argument was refused or missing, or some state could not be read.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

from core.compliance import model, owner
from core.isolation import state_root
from execution_accounts.baseline import restore_state
from execution_accounts.baseline_store import CheckpointStore
from execution_control.store import Journal
from execution_launch.baseline_head import BaselineHead, BaselineHeadError, CheckpointChain
from execution_launch.workflow import MAX_CONFIG_BYTES, read_file

UNREADABLE = "unreadable"
_BAD = object()                                    # a state that could not be read; never printed
_OPTIONS = ("state-root", "head-root", "principal", "floor", "activation", "candidate", "candidate-head", "session")
_AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?")
_HASH = re.compile(r"[0-9a-f]{64}")
_LABELS = {"S1": "owner log verifies", "S2": "halt in the owner log", "S3": "halt in the control journal",
           "S4": "highest recorded peak against A", "S5": "last journaled floor against C",
           "S6": "signed floor in force against C", "S7": "anchor floor against C", "S8": "armed sessions",
           "S9_home": "home", "S9_journal": "control journal folder", "S10": "anchor equity against W0",
           "S11": "anchor equity against highest floor", "S12": "signed floor inside --session"}
_GO = {"S2": ("none",), "S3": ("none", "no_journal"), "S4": ("none", "below"), "S6": ("equal",), "S7": ("equal",),
       "S10": ("equal", "below"), "S11": ("at_or_above",), "S12": ("not_requested", "equal")}


class Refused(ValueError):
    """A fixed UPPER_SNAKE code: never an amount, a path or a digest."""


def _default_home() -> Path:
    return Path.home() / ".tradegen"


def _relation(value: Decimal, target: Decimal) -> str:
    return "above" if value > target else "below" if value < target else "equal"


def _arguments(argv) -> tuple[dict, bool]:
    args, gate, tokens = {}, False, list(argv)
    while tokens:
        token = tokens.pop(0)
        if token == "--gate" and not gate:
            gate = True
            continue
        key = token[2:] if token.startswith("--") else ""
        if key not in _OPTIONS or key in args or not tokens or not tokens[0] or tokens[0].startswith("--"):
            raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
        args[key] = tokens.pop(0)
    amounts = [args.get(key, "") for key in ("floor", "principal", "activation")]
    if ("state-root" not in args or "head-root" not in args or ("candidate" in args) != ("candidate-head" in args)
            or not all(_AMOUNT.fullmatch(text) for text in amounts)
            or not _HASH.fullmatch(args.get("candidate-head", "0" * 64))):
        raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
    floor, principal, activation = (Decimal(text) for text in amounts)
    if not 0 < floor < principal <= activation:
        raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
    return args | {"floor": floor, "principal": principal, "activation": activation}, gate


def _home(explicit: str) -> Path:
    """The configured home. --state-root only confirms it (the rule of tools/owner/launch.py:111-115)."""
    try:
        actual = state_root().absolute()
    except (RuntimeError, OSError):                # the message names paths: never print it
        raise Refused("STATE_CHECK_STATE_ROOT_REFUSED") from None
    if Path(explicit) != actual:
        raise Refused("STATE_CHECK_STATE_ROOT_MISMATCH")
    return actual


def _signed(state, floor: Decimal) -> str:
    value = state.limits.get("total_loss_floor_krw")
    return "unset" if value is None else _relation(Decimal(str(value)), floor)


def _owner_rows(now: datetime, floor: Decimal, session: str | None):
    """Rows S1, S2, S6, S8 and S12, then the signed floor in force (None when unset, _BAD when unreadable)."""
    day, stamp = now.astimezone(model.KST).date(), model.iso_utc(now)
    state, check = owner._owner_now(day, stamp, None)          # the read-only half of load_context (owner.py:947)
    if not state.ok:
        return dict(S1="no", S2=UNREADABLE, S6=UNREADABLE, S8=UNREADABLE,
                    S12=UNREADABLE if session else "not_requested"), _BAD
    rows = dict(S1="yes" if check.entries else "empty", S2="present" if state.halted_floors else "none",
                S6=_signed(state, floor),
                S8="present" if state.armed_sessions else "none", S12="not_requested")
    if session:
        inside = owner._owner_now(day, stamp, session)[0]
        rows["S12"] = (UNREADABLE if not inside.ok else "not_armed" if session not in inside.armed_sessions
                       else _signed(inside, floor))
    value = state.limits.get("total_loss_floor_krw")
    return rows, None if value is None else Decimal(str(value))


def _stored(text) -> Decimal:
    value = Decimal(text) if type(text) is str else None
    if value is None or not value.is_finite() or value < 0:
        raise ValueError("journal amount")
    return value


def _journal_rows(home: Path, floor: Decimal):
    """Rows S3, S5 and the journal half of S9, then the journaled peak and the last journaled floor."""
    if not (home / "execution-control").exists():              # the journal's own folder (store.py:152)
        return dict(S3="no_journal", S5="none", S9_journal="absent"), None, None
    try:
        rows = Journal().snapshot()                            # creates nothing (store.py:232-253)
        risk = [row["data"] for row in rows if row["kind"] == "risk_snapshot"]
        peaks = [_stored(data["high_watermark"]) for data in risk]
        floors = [_stored(data["effective_floor"]) for data in risk if data["effective_floor"] is not None]
        halted = any(row["kind"] == "halt" for row in rows)
    except (RuntimeError, LookupError, TypeError, ValueError, ArithmeticError):
        return dict(S3=UNREADABLE, S5=UNREADABLE, S9_journal="present"), _BAD, _BAD
    last = floors[-1] if floors else None                      # the most recent, as controller.py:391-392 reads it
    return (dict(S3="present" if halted else "none", S5="none" if last is None else _relation(last, floor),
                 S9_journal="present"), max(peaks, default=None), last)


def _anchor(home: Path, head_root: str, candidate: str | None, candidate_head: str | None):
    """The candidate or the stored baseline state; None when neither a checkpoint nor a head exists; _BAD when
    it cannot be read. Every refusal of these readers is a fixed-code ValueError."""
    try:
        if candidate is not None:                              # the read setup-account makes (launch.py:141)
            return restore_state(read_file(candidate, MAX_CONFIG_BYTES), expected_head=candidate_head)
        store = CheckpointStore(root=home)
        head = BaselineHead(root=Path(head_root), name="account-baseline", chain=CheckpointChain(store))
        try:
            expected = head.read()
        except BaselineHeadError as exc:
            if str(exc) == "HEAD_NOT_INITIALIZED" and not (home / store._DIRECTORY / "checkpoint.json").exists():
                return None
            raise
        return store.load(expected_head=expected)
    except (ValueError, OSError, RuntimeError):
        return _BAD


def check(*, home: Path, head_root: str, principal: Decimal, floor: Decimal, activation: Decimal,
          candidate: str | None = None, candidate_head: str | None = None, session: str | None = None,
          now: datetime) -> dict[str, str]:
    """Every row by key. Reads only."""
    rows, signed = _owner_rows(now, floor, session)
    journal, peak, last = _journal_rows(home, floor)
    anchor = _anchor(home, head_root, candidate, candidate_head)
    rows |= journal
    rows["S9_home"] = "default" if home.is_relative_to(_default_home()) else "custom"
    peaks = [peak]
    if anchor is None:
        rows |= dict(S7="none", S10="none", S11="none")
    elif anchor is _BAD:
        rows |= dict(S7=UNREADABLE, S10=UNREADABLE, S11=UNREADABLE)
        peaks.append(_BAD)
    else:
        own = anchor.approved_effective_floor
        floors = [value for value in (own, last, signed) if value is not None]
        rows["S7"] = "null" if own is None else _relation(own, floor)
        rows["S10"] = _relation(anchor.equity_krw, principal)
        rows["S11"] = (UNREADABLE if any(value is _BAD for value in floors) else
                       "below" if floors and anchor.equity_krw < max(floors) else "at_or_above")
        peaks.append(anchor.high_watermark)
    peaks = [value for value in peaks if value is not None]
    rows["S4"] = (UNREADABLE if any(value is _BAD for value in peaks) else "none" if not peaks else
                  "below" if max(peaks) < activation else "at_or_above")
    return rows


def main(argv=None, *, now: datetime | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if tuple(argv) in (("--help",), ("-h",)):
        print(__doc__)
        return 0
    try:
        args, gate = _arguments(argv)
        rows = check(home=_home(args["state-root"]), head_root=args["head-root"], principal=args["principal"],
                     floor=args["floor"], activation=args["activation"], candidate=args.get("candidate"),
                     candidate_head=args.get("candidate-head"), session=args.get("session"),
                     now=now or datetime.now(timezone.utc))
    except Refused as exc:
        print(json.dumps({"refused": str(exc)}))
        return 2
    except (Exception, KeyboardInterrupt):         # Ctrl-C too. No message: it could name a path or an amount
        print(json.dumps({"refused": "STATE_CHECK_FAILED"}))
        return 2
    for key, label in _LABELS.items():
        print(f"{key:<11}{label:<38}{rows[key]}")
    verdict = "not_requested" if not gate else "go" if all(rows[key] in go for key, go in _GO.items()) else "no_go"
    print(json.dumps({"gate": verdict, "rows": rows}, sort_keys=True))
    return 2 if UNREADABLE in rows.values() else 1 if verdict == "no_go" else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the module's tests**

```bash
python -m tests.launch_acceptance launch_floor_state_check
```

Expected: every row `PASS`, counts `{'PASS': 21, 'FAIL': 0, 'NOT_RUN': 0}`.

- [ ] **Step 3: Commit**

```bash
git add tools/floor_state_check.py
git commit -m "Add the read-only loss-floor state check (spec 9.1, step 0)"
```

---

### Task 3: Measured checks

**Files:** none changed.

- [ ] **Step 1: The launch suite and the closure pin**

```bash
python -m tests.launch_acceptance
python -m tests.compliance_acceptance test_code_files_is_the_import_closure
```

Expected: no `FAIL` row in the launch suite; the closure test passes, which shows the closure's file list did not change (the script is not in it). The test pins file names, not contents: that no closure file was edited is shown by the name list of Step 3. Together they show the code hash did not change.

- [ ] **Step 2: The whole suite, once**

```bash
python -m tests.run_all
git checkout -- qa/acceptance_results.json
```

Expected: the only `FAIL` rows are the two that need the repository's own `.venv` (`compliance_guards/test_cryptography_is_pinned_installed_and_usable`, `compliance_signer/test_commands_sign_exactly_what_was_shown`) on a PC that runs from another virtual environment. If `control_controller` rows fail with "the test touched the real ~/.tradegen", the owner used the same PC during the run: re-run `python -m tests.run_all --suite execution_control` and restore the JSON file again.

- [ ] **Step 3: Bytes and scope**

```bash
git diff --stat origin/main
git diff --stat --ignore-cr-at-eol origin/main
git diff --name-only origin/main
```

Expected: both stats equal; the names are exactly this plan, `tests/launch_acceptance.py`, `tests/launch_floor_state_check.py` and `tools/floor_state_check.py`.

---

## Spec coverage

| Spec 9.1 | Where |
|---|---|
| Inputs: `C`, `A`, `W0` typed; `--state-root` equal to the configured home; `--head-root`; candidate anchor with its head; armed session id | `_arguments`, `_home`, `_anchor`; tests for the state root, the arguments and the candidate |
| Output: fixed codes and relations, never amounts, paths or digests | `main`; `test_the_output_holds_no_amount_path_digest_or_session_id` |
| Exit 0 or 2; `--gate` | `main`, `_GO`; `test_the_gate_passes_on_the_go_table_and_fails_on_each_single_miss` |
| Reads: the pure owner fold, not `load_context`; `Journal.snapshot()`; head then store | `_owner_rows`, `_journal_rows`, `_anchor`; the listing check inside `invoke`; the source-shape test |
| Rows S1 to S12 | `check`; one test per reader |
| 8.2: outside the closure, nothing in the closure imports it | `test_the_script_is_outside_the_signed_code_closure` |

Not in this plan: the owner documents that describe step 0 (`docs/first-trade-owner-checklist.md`). They belong to the implementation pull request of the design (spec 12.5).
