"""Synthetic offline CLI checks; no actual owner profile or account state is read."""
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import cli
from execution_launch.profile import MAX_PROFILE_BYTES, LaunchProfile, profile_body
from tests.launch_profile import NOW, fixture_profile


def invoke(*argv):
    output = io.StringIO()
    with redirect_stdout(output):
        code = cli.main(list(argv))
    return code, json.loads(output.getvalue()), output.getvalue()


def write_profile(root, body=None):
    path = Path(root) / "synthetic-profile.json"
    path.write_text(json.dumps(profile_body(fixture_profile()) if body is None else body), encoding="utf-8")
    return path


def test_defaults_and_template_never_read_files_environment_home_clock_or_network():
    with ExitStack() as stack:
        for target in ("execution_launch.cli._read_profile", "os.open", "os.getenv", "pathlib.Path.home",
                       "pathlib.Path.read_bytes", "socket.create_connection", "socket.socket"):
            stack.enter_context(patch(target, side_effect=AssertionError("unexpected side effect")))
        stack.enter_context(patch.object(os._Environ, "__getitem__", side_effect=AssertionError("environment read")))
        code, report, _ = invoke()
        assert code == 2 and report["execution_ready"] is False
        assert report["issues"][0]["code"] == "PROFILE_REQUIRED"
        code, template, _ = invoke("--template")
        assert code == 0
        assert template == profile_body(LaunchProfile(schema_version=1, profile_id="example-unconfigured"))
        assert template["policy"]["first_day_loss_budget"] is None


def test_explicit_profile_checks_freshness_but_never_claims_owner_approval_or_execution():
    with tempfile.TemporaryDirectory(prefix="launch_cli_test_") as root:
        path = write_profile(root)
        code, report, output = invoke("--profile", str(path), "--now", NOW.isoformat())
        assert code == 2 and report["profile_complete"] is True
        assert report["prerequisites_ready"] is False and report["execution_ready"] is False
        assert [item["code"] for item in report["issues"]] == ["SIGNED_CONTEXT_REQUIRED"]
        for private in (str(path), "test-scope", "test-profile", "fixture-v1", '"2000"', "test-strategy"):
            assert private not in output
        assert len(report["profile_digest"]) == 64


def test_missing_or_invalid_now_refuses_before_any_profile_read():
    with patch("execution_launch.cli._read_profile", side_effect=AssertionError("must not read")):
        code, report, output = invoke("--profile", "/private-path-do-not-print.json")
        assert code == 2 and report["issues"][0]["code"] == "EXPLICIT_NOW_REQUIRED"
        for stamp in ("secret-invalid-time", "2026-10-23T01:00:00", "9999-12-31T23:59:59+00:00"):
            code, report, output = invoke("--profile", "/private-path-do-not-print.json", "--now", stamp)
            assert code == 2 and report["issues"][0]["code"] == "EXPLICIT_NOW_INVALID"
            assert "private-path-do-not-print" not in output and stamp not in output


def test_argument_errors_and_invalid_json_do_not_echo_values_or_paths():
    for args in (("--unrecognized-secret-value",), ("--profile",),
                 ("--template", "--profile", "secret-path.json"), ("--template", "--now", "secret-time"),
                 ("--profile", "one.json", "--profile", "two.json"), ("--profile=",)):
        code, report, output = invoke(*args)
        assert code == 2 and report["issues"][0]["code"] == "CLI_ARGUMENTS_INVALID"
        assert "secret" not in output
    with tempfile.TemporaryDirectory(prefix="launch_cli_test_") as root:
        path = write_profile(root, {"schema_version": 1, "profile_id": "valid", "private-key": "secret-body-value"})
        code, report, output = invoke("--profile", str(path), "--now", NOW.isoformat())
        assert code == 2 and report["issues"][0]["code"] == "PROFILE_SCHEMA_INVALID"
        assert "secret-body-value" not in output and str(path) not in output


def test_private_directories_env_parent_traversal_and_non_json_are_denied_before_open():
    with patch("os.open", side_effect=AssertionError("private path must never be opened")):
        for path in ("/example/.tradegen/profile.json", "/example/.nextgen/profile.json",
                     "/example/.ssh/profile.json", "/example/.aws/profile.json", "/example/.env/profile.json",
                     "/example/.env.private/profile.json", "/example/.env.json", "/example/data.txt",
                     "/example/../profile.json", "bad\x00name.json"):
            code, report, output = invoke("--profile", path, "--now", NOW.isoformat())
            assert code == 2 and report["issues"][0]["code"] == "PROFILE_FILE_REFUSED"
            assert path not in output


def test_symlink_files_and_parents_and_hard_links_are_refused():
    with tempfile.TemporaryDirectory(prefix="launch_cli_test_") as root:
        root = Path(root)
        target = write_profile(root)
        linked_file = root / "linked.json"
        linked_file.symlink_to(target)
        linked_dir = root / "linked-dir"
        linked_dir.symlink_to(root, target_is_directory=True)
        for path in (linked_file, linked_dir / target.name):
            code, report, output = invoke("--profile", str(path), "--now", NOW.isoformat())
            assert code == 2 and report["issues"][0]["code"] == "PROFILE_FILE_UNAVAILABLE_OR_REFUSED"
            assert str(path) not in output
        hard_link = root / "hard-linked.json"
        os.link(target, hard_link)
        code, report, _ = invoke("--profile", str(hard_link), "--now", NOW.isoformat())
        assert code == 2 and report["issues"][0]["code"] == "PROFILE_FILE_REFUSED"


def test_oversize_missing_directory_and_non_regular_files_are_bounded_refusals():
    with tempfile.TemporaryDirectory(prefix="launch_cli_test_") as root:
        root = Path(root)
        oversized = root / "oversized.json"
        oversized.write_bytes(b" " * (MAX_PROFILE_BYTES + 1))
        directory = root / "directory.json"
        directory.mkdir()
        for path in (oversized, directory, root / "missing.json"):
            code, report, output = invoke("--profile", str(path), "--now", NOW.isoformat())
            assert code == 2 and not report["execution_ready"]
            assert report["issues"][0]["code"] in ("PROFILE_FILE_REFUSED", "PROFILE_FILE_UNAVAILABLE_OR_REFUSED")
            assert str(path) not in output
        # An inaccurate/stale size cannot defeat the independent bounded read.
        with patch("execution_launch.cli.os.fstat", return_value=SimpleNamespace(
                st_mode=stat.S_IFREG | 0o600, st_size=0, st_nlink=1)):
            code, report, _ = invoke("--profile", str(oversized), "--now", NOW.isoformat())
            assert code == 2 and report["issues"][0]["code"] == "PROFILE_JSON_TOO_LARGE"
        fifo = root / "fifo.json"
        os.mkfifo(fifo)
        code, report, _ = invoke("--profile", str(fifo), "--now", NOW.isoformat())
        assert code == 2 and report["issues"][0]["code"] == "PROFILE_FILE_REFUSED"


def test_truncated_utf8_and_duplicate_json_remain_redacted_parser_refusals():
    with tempfile.TemporaryDirectory(prefix="launch_cli_test_") as root:
        path = Path(root) / "invalid.json"
        for raw in (b"\xff", b'{"schema_version":1,"profile_id":"a","profile_id":"secret-profile"}'):
            path.write_bytes(raw)
            code, report, output = invoke("--profile", str(path), "--now", NOW.isoformat())
            assert code == 2 and not report["execution_ready"]
            assert report["issues"][0]["code"] in ("PROFILE_JSON_OR_SCHEMA_INVALID", "PROFILE_DUPLICATE_JSON_KEY")
            assert "secret-profile" not in output and str(path) not in output
