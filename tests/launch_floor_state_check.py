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
