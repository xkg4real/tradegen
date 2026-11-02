"""Windows private-input loader: invented files under a temporary root, no owner data, no network."""
from contextlib import contextmanager, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_launch import cli, deployment, private_input, workflow as W
from execution_launch.deployment import MAX_MANIFEST_BYTES
from execution_launch.profile import MAX_PROFILE_BYTES, profile_body
from tests import compliance_fixtures as F
from tests.launch_profile import NOW, fixture_profile
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
RAW = json.dumps(profile_body(fixture_profile()))
MARKERS = ("secret-stream-marker", "secret-swap-marker", "secret-junction-marker", "secret-profile-marker",
           "secret-program-marker", "test-scope", "fixture-v1", "test-profile")
PRIVATE = cli._PRIVATE_COMPONENTS
LINK = "PRIVATE_INPUT_LINK_OR_PLACEHOLDER_REFUSED"


def _windows():
    if os.name != "nt":
        raise NotRun("REFDATA: Windows reparse, identity and attribute metadata need Windows")


@contextmanager
def _root():
    """A canonical temporary root (never the real home); the suite wrapper isolates TRADEGEN_HOME."""
    with tempfile.TemporaryDirectory(prefix="launch_private_input_") as directory:
        yield Path(os.path.realpath(directory))


def _redacted(text, *paths):
    for private in (*MARKERS, *map(str, paths)):
        assert private not in text, private


def _code(call, *paths):
    """The single fixed code of a loader refusal; no path or marker in its text."""
    try:
        call()
    except private_input.PrivateInputError as exc:
        assert len(exc.args) == 1 and type(exc.args[0]) is str
        _redacted(str(exc) + repr(exc), *paths)
        return str(exc)
    raise AssertionError("expected a private-input refusal")


def _read(path, maximum=MAX_PROFILE_BYTES, suffix=".json"):
    return private_input.read_private_file(str(path), maximum=maximum, suffix=suffix, private=PRIVATE)


def _invoke(module, argv, *paths):
    output = StringIO()
    with redirect_stdout(output):
        code = module.main(list(argv))
    _redacted(output.getvalue(), *paths)
    return code, json.loads(output.getvalue()), output.getvalue()


def _cli(path):
    code, report, output = _invoke(cli, ["--profile", str(path), "--now", NOW.isoformat()], path)
    assert code == 2 and report["execution_ready"] is False
    return report, output


def _cli_code(path):
    return _cli(path)[0]["issues"][0]["code"]


def _workflow_code(path, maximum=MAX_PROFILE_BYTES):
    try:
        W._read_file(str(path), maximum)
    except W.WorkflowError as exc:
        _redacted(str(exc), path)
        return str(exc)
    raise AssertionError("expected a workflow refusal")


def _meta(info, **changes):
    """A stat result copy with the fields the loader reads; `changes` fakes stale or flagged metadata."""
    fields = {name: getattr(info, name) for name in ("st_mode", "st_ino", "st_dev", "st_nlink", "st_size",
                                                      "st_file_attributes")}
    return SimpleNamespace(**{**fields, **changes})


def _write(path, text=RAW):
    path.write_text(text, encoding="utf-8")
    return path


def test_windows_path_rules_refuse_device_stream_namespace_and_private_forms():
    refused = (r"C:\fixture\profile.json:secret-stream-marker", r"C:\fixture\profile.json::$DATA",
               r"C:\fixture\CON.json", r"C:\fixture\nul", r"C:\fixture\COM1.json", r"C:\fixture\LPT9.json",
               r"C:\fixture\CONIN$.json", r"\\?\C:\fixture\profile.json", r"\\.\C:\fixture\profile.json",
               r"\\?\UNC\server\share\profile.json", r"\\server\share\profile.json", "//server/share/profile.json",
               r"\\.\pipe\profile.json", r"\??\C:\fixture\profile.json", r"C:profile.json",
               "C:\\fixture\\.tradegen.\\profile.json", "C:\\fixture\\.tradegen \\profile.json",
               r"C:\fixture\.TRADEGEN\profile.json", r"C:\Users\fixture\.nextgen\kis.json",
               r"C:\fixture\.env.local\p.json", r"C:\fixture\..\profile.json", r"C:\fixture\profile.txt",
               r"C:\fixture\profile.JSON", r"C:\fixture\pro*file.json", "C:\\fixture\\a\x01.json",
               "C:\\fixture\\a\x00.json", "", None, b"C:\\fixture\\p.json")
    with patch.object(private_input.os, "lstat", side_effect=AssertionError("metadata read")), \
            patch.object(private_input.os, "open", side_effect=AssertionError("file opened")):
        for path in refused:
            found = _code(lambda: private_input._checked_path(path, suffix=".json", private=PRIVATE))
            assert found == "PRIVATE_INPUT_PATH_REFUSED", (path, found)
        for path in (r"C:\fixture\private-profile.json", "C:/fixture/private-profile.json"):
            assert private_input._checked_path(path, suffix=".json", private=PRIVATE) == r"C:\fixture\private-profile.json"


def test_windows_reader_returns_exact_bytes_and_cli_reports_without_echo():
    _windows()
    with _root() as root:
        path = _write(root / "private-profile.json")
        before = sorted(os.listdir(root))
        assert _read(path) == RAW.encode("utf-8")
        report, _ = _cli(path)
        assert report["profile_complete"] is True and report["prerequisites_ready"] is False
        assert [item["code"] for item in report["issues"]] == ["SIGNED_CONTEXT_REQUIRED"]
        assert sorted(os.listdir(root)) == before


def test_windows_reader_refuses_junction_parents_at_any_depth():
    _windows()
    with _root() as root:
        real = root / "real"; real.mkdir(); _write(real / "private-profile.json")
        F.directory_link(root / "junction-dir", real)
        tree = root / "tree" / "sub"; tree.mkdir(parents=True); _write(tree / "private-profile.json")
        F.directory_link(root / "outer", root / "tree")
        for path in (root / "junction-dir" / "private-profile.json", root / "outer" / "sub" / "private-profile.json"):
            assert _code(lambda: _read(path), path) == LINK
            assert _cli_code(path) == "PROFILE_FILE_UNAVAILABLE_OR_REFUSED"
            assert _workflow_code(path) == "WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED"
            code, result, _ = _invoke(deployment, ["compare", "--left", str(path), "--right", str(path)], path)
            assert code == 2 and result["reason"] == "DEPLOYMENT_INPUT_REFUSED"


def test_windows_reader_refuses_file_and_directory_symlinks():
    _windows()
    with _root() as root:
        target = _write(root / "private-profile.json")
        real = root / "real"; real.mkdir(); _write(real / "private-profile.json")
        try:
            os.symlink(target, root / "sym.json")
            os.symlink(real, root / "symdir", target_is_directory=True)
        except OSError:
            raise NotRun("REFDATA: symlink creation needs Developer Mode") from None
        for path in (root / "sym.json", root / "symdir" / "private-profile.json"):
            assert _code(lambda: _read(path), path) == LINK
            assert _cli_code(path) == "PROFILE_FILE_UNAVAILABLE_OR_REFUSED"


def test_windows_reader_refuses_both_names_of_a_hard_link():
    _windows()
    with _root() as root:
        real = root / "real"; real.mkdir()
        target = _write(real / "private-profile.json")
        hard = root / "hard.json"; os.link(target, hard)
        for path in (target, hard):
            assert _code(lambda: _read(path), path) == "PRIVATE_INPUT_FILE_REFUSED"
            assert _cli_code(path) == "PROFILE_FILE_REFUSED"
        assert target.read_text(encoding="utf-8") == RAW


def test_windows_reader_refuses_short_name_aliases_including_private_roots():
    _windows()
    with _root() as root:
        aliases = []
        for long_name, short_name in ((".tradegen", "TRADEG~1"), ("long-directory-name", "LONG-D~1")):
            (root / long_name).mkdir()
            real = _write(root / long_name / "private-profile.json")
            alias = root / short_name / "private-profile.json"
            if not alias.exists():
                raise NotRun("REFDATA: 8.3 short names are disabled on this volume")
            assert os.path.samefile(alias, real)
            aliases.append(alias)
        for alias in aliases:                      # the lexical denial cannot see TRADEG~1; the alias rule refuses it
            assert _code(lambda: _read(alias), alias) == "PRIVATE_INPUT_ALIAS_REFUSED"
            assert _cli_code(alias) == "PROFILE_FILE_UNAVAILABLE_OR_REFUSED"


def test_windows_reader_refuses_real_streams_and_device_names_before_metadata():
    _windows()
    with _root() as root:
        target = _write(root / "private-profile.json")
        stream = str(target) + ":secret-stream"
        with open(stream, "w", encoding="utf-8") as handle:
            handle.write('{"secret":"secret-stream-marker"}')
        with patch.object(private_input.os, "lstat", side_effect=AssertionError("metadata read")), \
                patch.object(private_input.os, "open", side_effect=AssertionError("file opened")):
            for path in (stream, str(root / "NUL"), str(root / "COM1.json"), r"\\.\pipe\profile.json"):
                assert _code(lambda: _read(path), path) == "PRIVATE_INPUT_PATH_REFUSED"
                assert _cli_code(path) == "PROFILE_FILE_REFUSED"


def test_windows_reader_bounds_size_with_honest_and_stale_metadata():
    _windows()
    with _root() as root:
        big = root / "big.json"; big.write_bytes(b" " * (MAX_PROFILE_BYTES + 1))
        assert _code(lambda: _read(big), big) == "PRIVATE_INPUT_FILE_REFUSED"
        assert _cli_code(big) == "PROFILE_FILE_REFUSED"
        lstat, fstat = os.lstat, os.fstat
        with patch.object(private_input.os, "lstat", lambda path: _meta(lstat(path), st_size=0)), \
                patch.object(private_input.os, "fstat", lambda fd: _meta(fstat(fd), st_size=0)):
            assert _code(lambda: _read(big), big) == "PRIVATE_INPUT_TOO_LARGE"
            assert _cli_code(big) == "PROFILE_JSON_TOO_LARGE"
            assert _workflow_code(big, W.MAX_CONFIG_BYTES) == "WORKFLOW_FILE_TOO_LARGE"


def test_windows_reader_detects_file_and_parent_swaps_between_check_and_open():
    _windows()
    with _root() as root:
        a = _write(root / "a.json", '{"a":"1"}')
        b = _write(root / "b.json", '{"secret":"secret-swap-marker"}')
        real_open = os.open

        def swap_file(path, flags, *rest):
            os.replace(b, a)
            return real_open(path, flags, *rest)

        with patch.object(private_input.os, "open", swap_file):
            assert _code(lambda: _read(a), a) == "PRIVATE_INPUT_IDENTITY_CHANGED"
        directory, other = root / "dir", root / "other"
        directory.mkdir(); other.mkdir()
        _write(directory / "p.json", '{"d":"1"}')
        _write(other / "p.json", '{"o":"secret-junction-marker"}')

        def swap_parent(path, flags, *rest):
            os.rename(directory, root / "dir-old")
            F.directory_link(directory, other)
            return real_open(path, flags, *rest)

        with patch.object(private_input.os, "open", swap_parent):
            assert _code(lambda: _read(directory / "p.json"), directory) == "PRIVATE_INPUT_IDENTITY_CHANGED"


def test_windows_reader_refuses_cloud_placeholder_and_offline_attributes():
    _windows()
    with _root() as root:
        target = _write(root / "private-profile.json")
        lstat = os.lstat

        def flagged(where, bits):
            def wrapper(path):
                info = lstat(path)
                if os.path.normcase(str(path)) == os.path.normcase(str(where)):
                    return _meta(info, st_file_attributes=info.st_file_attributes | bits)
                return info
            return wrapper

        for where, bits in ((target, 0x00400000), (root, 0x00040000), (root, 0x1000)):
            with patch.object(private_input.os, "lstat", flagged(where, bits)), \
                    patch.object(private_input.os, "open", side_effect=AssertionError("placeholder opened")):
                assert _code(lambda: _read(target), target) == LINK


def test_windows_reader_refuses_directories_missing_and_file_parent_paths():
    _windows()
    with _root() as root:
        (root / "folder.json").mkdir()
        target = _write(root / "private-profile.json")
        for path, code, cli_code in (
                (root / "folder.json", "PRIVATE_INPUT_FILE_REFUSED", "PROFILE_FILE_REFUSED"),
                (root / "missing.json", "PRIVATE_INPUT_UNAVAILABLE", "PROFILE_FILE_UNAVAILABLE_OR_REFUSED"),
                (target / "child.json", "PRIVATE_INPUT_UNAVAILABLE", "PROFILE_FILE_UNAVAILABLE_OR_REFUSED")):
            assert _code(lambda: _read(path), path) == code
            assert _cli_code(path) == cli_code


def test_windows_clis_keep_strict_duplicate_key_and_oversize_refusals():
    _windows()
    with _root() as root:
        profile = _write(root / "profile.json", '{"schema_version":1,"profile_id":"a","profile_id":"secret-profile-marker"}')
        program = _write(root / "program.json",
                         '{"schema_version":1,"strategy_id":"a","strategy_id":"secret-program-marker"}')
        manifest = _write(root / "manifest.json", '{"schema_version":1,"schema_version":1}')
        big_program = root / "big-program.json"; big_program.write_bytes(b" " * (W.MAX_CONFIG_BYTES + 1))
        big_manifest = root / "big-manifest.json"; big_manifest.write_bytes(b" " * (MAX_MANIFEST_BYTES + 1))
        assert _cli_code(profile) == "PROFILE_DUPLICATE_JSON_KEY"
        code, report, _ = _invoke(W, ["inspect-program", "--program", str(program)], program)
        assert code == 2 and report["reasons"] == ["PROGRAM_JSON_DUPLICATE_KEY"] and not report["execution_ready"]
        code, report, _ = _invoke(W, ["inspect-program", "--program", str(big_program)], big_program)
        assert code == 2 and report["reasons"] == ["WORKFLOW_FILE_REFUSED"]
        code, report, _ = _invoke(deployment, ["compare", "--left", str(manifest), "--right", str(manifest)], manifest)
        assert code == 2 and report["reason"] == "DEPLOYMENT_DUPLICATE_JSON_KEY"
        code, report, _ = _invoke(deployment, ["compare", "--left", str(big_manifest), "--right", str(manifest)],
                                  big_manifest)
        assert code == 2 and report["reason"] == "DEPLOYMENT_INPUT_REFUSED"


def test_windows_deployment_manifest_round_trip_matches_owner_and_signer_closure():
    _windows()
    from tools.signer import sign
    manifest = deployment.export_manifest(repo_root=ROOT)
    assert manifest["code_hash"] == owner.code_hash(ROOT)
    assert dict(owner.code_files(ROOT)) == dict(sign.code_files(ROOT))
    assert "execution_launch/private_input.py" in dict(manifest["repository_files"])
    assert manifest["runtime"] == {"implementation": "cpython", "python_version": list(sys.version_info[:3]),
                                   "platform": "win32"}
    with _root() as root:
        left, right = _write(root / "left.json", json.dumps(manifest)), _write(root / "right.json", json.dumps(manifest))
        code, result, _ = _invoke(deployment, ["compare", "--left", str(left), "--right", str(right)], root, ROOT)
        assert code == 0 and result["code_hash_matches"] and result["runtime_metadata_matches"]
        assert all(not rows for group in result["differences"].values() for rows in group.values())
        assert result["signature_verified"] is False and result["execution_ready"] is False
        real = root / "real"; real.mkdir(); _write(real / "left.json", json.dumps(manifest))
        F.directory_link(root / "junction", real)
        code, result, _ = _invoke(deployment, ["compare", "--left", str(root / "junction" / "left.json"),
                                               "--right", str(right)], root, ROOT)
        assert code == 2 and result["reason"] == "DEPLOYMENT_INPUT_REFUSED"


def test_reader_dispatch_is_os_name_gated_and_posix_reader_is_untouched():
    with _root() as root:
        path = _write(root / "private-profile.json")
        if os.name != "nt":
            with patch.object(cli, "read_private_file", side_effect=AssertionError("Windows loader on POSIX")), \
                    patch.object(W.private_input, "read_private_file", side_effect=AssertionError("Windows loader on POSIX")):
                assert cli._read_profile(str(path)) == RAW.encode("utf-8")
                assert W._read_file(str(path), W.MAX_CONFIG_BYTES) == RAW.encode("utf-8")
            return
        with patch.object(cli, "read_private_file", wraps=cli.read_private_file) as spy:
            assert cli._read_profile(str(path)) == RAW.encode("utf-8") and spy.call_count == 1
        with patch.object(W.private_input, "read_private_file", wraps=W.private_input.read_private_file) as spy:
            assert W._read_file(str(path), W.MAX_CONFIG_BYTES) == RAW.encode("utf-8") and spy.call_count == 1
        with patch.object(os, "name", "posix"):                      # the POSIX gate still fails closed
            for call, error, expected in ((lambda: cli._read_profile(str(path)), cli.ProfileError,
                                           "PROFILE_FILE_PLATFORM_UNSUPPORTED"),
                                          (lambda: W._read_file(str(path), W.MAX_CONFIG_BYTES), W.WorkflowError,
                                           "WORKFLOW_FILE_PLATFORM_UNSUPPORTED")):
                try:
                    call()
                except error as exc:
                    assert (exc.code if error is cli.ProfileError else str(exc)) == expected
                else:
                    raise AssertionError("a patched platform name opened the POSIX reader")
