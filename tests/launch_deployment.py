"""Deployment hashes and setup diagnostics: synthetic documents, no owner state."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from core.compliance import owner
from execution_launch import deployment as D
from tests import compliance_fixtures as F

ROOT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def external_manifest(*, sources=None, records=None, platform="linux"):
    sources = sources if sources is not None else [["execution_launch/example.py", "a"*64]]
    records = records if records is not None else [["venv:PyYAML-6.0.2.dist-info/RECORD", "b"*64],
                                                ["venv:cryptography-44.0.0.dist-info/RECORD", "c"*64]]
    value = {"schema_version": 1, "kind": "tradegen-d14-deployment/1",
             "runtime": {"implementation": "cpython", "python_version": [3, 13, 16], "platform": platform},
             "repository_files": sources, "dependency_records": records,
             "code_hash": sha(sorted(sources+records)), "signature_verified": False, "execution_ready": False}
    return {**value, "manifest_sha256": sha(value)}


def refused(call, code):
    try:
        call()
    except D.DeploymentError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError("expected deployment refusal")


def invoke(*args):
    output = StringIO()
    with redirect_stdout(output):
        code = D.main(list(args))
    return code, json.loads(output.getvalue()), output.getvalue()


def test_default_setup_has_no_io_environment_or_implicit_time_and_keeps_unknowns():
    with ExitStack() as stack:
        for target in ("execution_launch.deployment.export_manifest", "execution_launch.deployment._read_profile",
                       "pathlib.Path.home", "pathlib.Path.open", "os.open", "os.getenv",
                       "socket.socket", "core.compliance.owner.load_context"):
            stack.enter_context(patch(target, side_effect=AssertionError("unexpected effect")))
        stack.enter_context(patch.object(os._Environ, "__getitem__", side_effect=AssertionError("environment read")))
        code, result, _ = invoke()
    assert code == 2 and not result["execution_ready"] and not result["signature_verified"]
    assert result["deployment_environment"] is None and not result["owner_approvals_checked"]
    assert result["first_limits"]["assumption"] == "UNKNOWN"
    assert result["first_limits"]["earliest_effective_seoul_date"] is None
    assert result["profile_template"]["policy"]["first_day_loss_budget"] is None
    config = result["configuration"]
    assert config["credential_values_included"] is False
    assert config["credential_variable_names"]["upbit"] == ["UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"]
    assert "api.upbit.com" in config["allowed_https_hosts"]


def test_first_limit_advisory_uses_seoul_next_day_without_claiming_effectiveness():
    for instant, expected in (("2026-11-01T15:01:00+00:00", "2026-11-03"),
                              ("2026-11-01T14:59:00+00:00", "2026-11-02")):
        result = D.setup_manifest(first_limits_at=datetime.fromisoformat(instant))
        assert result["first_limits"]["earliest_effective_seoul_date"] == expected
        assert result["first_limits"]["advisory_only"]
        assert result["first_limits"]["requires"] == ["VERIFIED_OWNER_LOG", "SESSION_AND_HALT_CHECKS"]
        assert not result["execution_ready"]
    for bad in ("secret-value", datetime(2026, 11, 2), datetime.max.replace(tzinfo=timezone.utc)):
        refused(lambda bad=bad: D.setup_manifest(first_limits_at=bad), "DEPLOYMENT_AWARE_LIMIT_TIME_REQUIRED")


def test_export_matches_actual_d14_closure_and_never_contains_absolute_paths():
    with patch.object(owner, "load_context", side_effect=AssertionError("owner state read")):
        result = D.export_manifest(repo_root=ROOT)
        assert result["code_hash"] == owner.code_hash(ROOT)
        assert sorted(result["repository_files"]+result["dependency_records"]) == [list(row) for row in owner.code_files(ROOT)]
    assert not result["signature_verified"] and not result["execution_ready"]
    assert str(ROOT) not in json.dumps(result)
    assert {path.split(":", 1)[1].split("-", 1)[0] for path, _ in result["dependency_records"]} == {"cryptography", "PyYAML"}
    assert D.parse_manifest(json.dumps(result)) == result


def test_manifest_comparison_separates_source_dependency_and_runtime_differences():
    original = external_manifest()
    changed = external_manifest(sources=[["execution_launch/example.py", "d"*64], ["execution_launch/new.py", "e"*64]],
        records=[["venv:PyYAML-6.0.2.dist-info/RECORD", "b"*64], ["venv:cryptography-44.0.0.dist-info/RECORD", "f"*64]],
        platform="win32")
    result = D.compare_manifests(original, changed)
    assert result["code_hash_matches"] is False and result["runtime_metadata_matches"] is False
    assert result["differences"]["repository_files"] == {"added": ["execution_launch/new.py"], "removed": [],
                                                           "changed": ["execution_launch/example.py"]}
    assert result["differences"]["dependency_records"]["changed"] == ["venv:cryptography-44.0.0.dist-info/RECORD"]
    metadata_only = D.compare_manifests(original, external_manifest(platform="win32"))
    assert metadata_only["code_hash_matches"] and not metadata_only["runtime_metadata_matches"]
    same = D.compare_manifests(original, deepcopy(original))
    assert same["code_hash_matches"] and same["runtime_metadata_matches"]
    assert not same["signature_verified"] and not same["execution_ready"]


def test_forged_authority_hash_changes_and_untrusted_rows_refuse():
    value = external_manifest()
    for field in ("signature_verified", "execution_ready"):
        mutated = deepcopy(value); mutated[field] = True
        refused(lambda mutated=mutated: D.validate_manifest(mutated), "DEPLOYMENT_AUTHORITY_CLAIM_REFUSED")
    bad = deepcopy(value); bad["repository_files"][0][1] = "d"*64
    refused(lambda: D.validate_manifest(bad), "DEPLOYMENT_CODE_HASH_MISMATCH")
    bad = deepcopy(value); bad["manifest_sha256"] = "f"*64
    refused(lambda: D.validate_manifest(bad), "DEPLOYMENT_MANIFEST_HASH_MISMATCH")
    for path in ("/private/owner.py", "../owner.py", ".tradegen/owner.py", "file//path.py", "x\\owner.py"):
        invalid = external_manifest(sources=[[path, "a"*64]])
        refused(lambda invalid=invalid: D.validate_manifest(invalid), "DEPLOYMENT_SOURCE_PATH_INVALID")
    invalid = external_manifest(records=[])
    refused(lambda: D.validate_manifest(invalid), "DEPLOYMENT_DEPENDENCY_RECORDS_REQUIRED")
    invalid = external_manifest(sources=[["z.py", "a"*64], ["a.py", "b"*64]])
    refused(lambda: D.validate_manifest(invalid), "DEPLOYMENT_FILE_ORDER_OR_DUPLICATE")
    invalid = external_manifest(sources=[["a.py", "a"*64], ["a.py", "a"*64]])
    refused(lambda: D.validate_manifest(invalid), "DEPLOYMENT_FILE_ORDER_OR_DUPLICATE")


def test_parser_rejects_duplicates_oversize_numbers_and_unknown_fields():
    refused(lambda: D.parse_manifest('{"schema_version":1,"schema_version":1}'), "DEPLOYMENT_DUPLICATE_JSON_KEY")
    for raw in ('{"schema_version":1.0}', '{"schema_version":NaN}'):
        refused(lambda raw=raw: D.parse_manifest(raw), "DEPLOYMENT_JSON_NUMBER_INVALID")
    refused(lambda: D.parse_manifest(b"\xff"), "DEPLOYMENT_JSON_INVALID")
    refused(lambda: D.parse_manifest(" "*(D.MAX_MANIFEST_BYTES+1)), "DEPLOYMENT_MANIFEST_TOO_LARGE")
    value = external_manifest(); value["private"] = "secret"
    refused(lambda: D.validate_manifest(value), "DEPLOYMENT_SCHEMA_INVALID")
    value = external_manifest(); value["schema_version"] = True
    refused(lambda: D.validate_manifest(value), "DEPLOYMENT_VERSION_UNSUPPORTED")


def test_export_rejects_other_checkout_and_linked_source_before_closure_read():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(owner, "code_files", side_effect=AssertionError("must not read source")):
            refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_CURRENT_CHECKOUT_REQUIRED")
            refused(lambda: D.export_manifest(repo_root="relative"), "DEPLOYMENT_REPO_REFUSED")
            package = root / "execution_launch"; package.mkdir()
            source = package / "source.py"; source.write_text("VALUE=1\n")
            linked = package / "linked.py"; linked.symlink_to(source)
            with patch.object(D, "_ROOT", root):
                refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_LINKED_SOURCE_REFUSED")
            linked.unlink(); os.link(source, linked)
            with patch.object(D, "_ROOT", root):
                refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_LINKED_SOURCE_REFUSED")
            # A junction (a reparse point that is not a symlink) in the source tree or above the checkout root.
            linked.unlink()
            real = root / "real-source"; real.mkdir(); (real / "module.py").write_text("VALUE=2\n", encoding="utf-8")
            F.directory_link(package / "junction", real)
            F.directory_link(root / "checkout-alias", root)
            with patch.object(D, "_ROOT", root):
                refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_LINKED_SOURCE_REFUSED")
                refused(lambda: D.export_manifest(repo_root=root / "checkout-alias"),
                        "DEPLOYMENT_CURRENT_CHECKOUT_REQUIRED")


def test_directory_links_are_refused_before_any_source_import_walk():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        package = root / "execution_launch"; package.mkdir()
        nested = package / "nested"; nested.mkdir()
        source = nested / "regular.py"; source.write_text("VALUE=1\n", encoding="utf-8")
        outside = root / "not-in-source-closure"; outside.mkdir()
        (outside / "secret.py").write_text("VALUE=2\n", encoding="utf-8")
        F.directory_link(nested / "linked-directory", outside)
        with patch.object(D, "_ROOT", root), \
                patch.object(owner, "_repo_imports", side_effect=AssertionError("must not inspect source AST")), \
                patch.object(owner, "code_files", side_effect=AssertionError("must not hash source")):
            refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_LINKED_SOURCE_REFUSED")


def test_regular_nested_sources_remain_scanned_and_nested_hardlinks_refuse():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        nested = root / "execution_launch" / "one" / "two"; nested.mkdir(parents=True)
        source = nested / "source.py"; source.write_text("VALUE=1\n", encoding="utf-8")
        with patch.object(D, "_ROOT", root), patch.object(owner, "_repo_imports", return_value=[]) as imports:
            assert D._source_tree(root) == root
            assert imports.call_count == 1 and imports.call_args.args == (root, source)
        os.link(source, nested / "hardlinked.py")
        with patch.object(D, "_ROOT", root), \
                patch.object(owner, "_repo_imports", side_effect=AssertionError("must not inspect source AST")), \
                patch.object(owner, "code_files", side_effect=AssertionError("must not hash source")):
            refused(lambda: D.export_manifest(repo_root=root), "DEPLOYMENT_LINKED_SOURCE_REFUSED")


def test_cli_compares_bounded_explicit_files_and_redacts_paths_and_rejected_arguments():
    with tempfile.TemporaryDirectory() as directory:
        left, right = Path(directory)/"left.json", Path(directory)/"right.json"
        left.write_text(json.dumps(external_manifest())); right.write_text(left.read_text())
        code, result, output = invoke("compare", "--left", str(left), "--right", str(right))
        assert code == 0 and result["code_hash_matches"] and not result["signature_verified"]
        assert directory not in output
        linked = Path(directory)/"linked.json"; linked.symlink_to(left)
        code, result, output = invoke("compare", "--left", str(linked), "--right", str(right))
        assert code == 2 and result["reason"] == "DEPLOYMENT_INPUT_REFUSED" and directory not in output
    for args in (("export", "--repo"), ("compare", "--left", "secret.json"), ("secret-mode",),
                 ("setup", "--first-limits-at", "secret-date"), ("setup", "--key", "secret-key")):
        code, result, output = invoke(*args)
        assert code == 2 and not result["signature_verified"] and "secret" not in output
