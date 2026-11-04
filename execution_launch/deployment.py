"""Offline deployment manifests; no signer, owner-state loader or live defaults.

    python -m execution_launch.deployment setup
    python -m execution_launch.deployment setup --first-limits-at <aware-ISO>
    python -m execution_launch.deployment export --repo <this-checkout>
    python -m execution_launch.deployment compare --left <a.json> --right <b.json>

Export hashes the explicitly selected current checkout and this interpreter's
dependency RECORD files. Compare checks supplied bytes, not their authenticity.
No command reads an owner log, private key, credential value or .env file.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys

from core.compliance import model as compliance
from core.compliance import owner
from execution_accounts.readiness import configuration_manifest
from execution_launch.cli import _read_profile
from execution_launch.profile import MAX_PROFILE_BYTES, LaunchProfile, ProfileError, profile_body

MAX_MANIFEST_BYTES = MAX_PROFILE_BYTES
_ROOT = Path(__file__).resolve().parents[1]
_HASH = re.compile(r"[0-9a-f]{64}")
_SOURCE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.py")
_RECORD = re.compile(r"venv:(cryptography|PyYAML)-[A-Za-z0-9_.+-]{1,80}\.dist-info/RECORD")
_PRIVATE = frozenset({".tradegen", ".nextgen", ".ssh", ".aws", ".gnupg", ".azure", ".kube"})
_FIELDS = frozenset({"schema_version", "kind", "runtime", "repository_files", "dependency_records",
                     "code_hash", "manifest_sha256", "signature_verified", "execution_ready"})


class DeploymentError(ValueError):
    """Fixed diagnostic only: no supplied path, account value or exception text."""


def _require(condition, code):
    if not condition:
        raise DeploymentError(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _code_hash(repository, dependencies):
    # Match the existing owner/signer D14 canonical list exactly.
    return _digest(sorted(repository + dependencies))


def _rows(rows, *, dependency):
    _require(type(rows) is list and len(rows) <= 2048, "DEPLOYMENT_FILE_LIST_INVALID")
    found = []
    distributions = set()
    for row in rows:
        _require(type(row) is list and len(row) == 2 and all(type(v) is str for v in row),
                 "DEPLOYMENT_FILE_ROW_INVALID")
        path, sha = row
        _require(len(path) <= 256 and _HASH.fullmatch(sha) is not None,
                 "DEPLOYMENT_FILE_ROW_INVALID")
        if dependency:
            match = _RECORD.fullmatch(path)
            _require(match is not None, "DEPLOYMENT_DEPENDENCY_PATH_INVALID")
            _require(match.group(1) not in distributions, "DEPLOYMENT_DUPLICATE_DEPENDENCY")
            distributions.add(match.group(1))
        else:
            parts = PurePosixPath(path).parts
            _require(_SOURCE.fullmatch(path) is not None and not PurePosixPath(path).is_absolute()
                     and all(part not in (".", "..") and not part.startswith(".") for part in parts)
                     and PurePosixPath(path).as_posix() == path,
                     "DEPLOYMENT_SOURCE_PATH_INVALID")
        found.append(path)
    _require(found == sorted(set(found)), "DEPLOYMENT_FILE_ORDER_OR_DUPLICATE")
    if dependency:
        _require(distributions == {"cryptography", "PyYAML"}, "DEPLOYMENT_DEPENDENCY_RECORDS_REQUIRED")
    else:
        _require(bool(rows), "DEPLOYMENT_SOURCE_FILES_REQUIRED")


def validate_manifest(value):
    """Validate complete supplied manifest integrity, without authenticating it."""
    try:
        _require(type(value) is dict and set(value) == _FIELDS, "DEPLOYMENT_SCHEMA_INVALID")
        _require(type(value["schema_version"]) is int and value["schema_version"] == 1
                 and value["kind"] == "tradegen-d14-deployment/1", "DEPLOYMENT_VERSION_UNSUPPORTED")
        _require(value["signature_verified"] is False and value["execution_ready"] is False,
                 "DEPLOYMENT_AUTHORITY_CLAIM_REFUSED")
        runtime = value["runtime"]
        _require(type(runtime) is dict and set(runtime) == {"implementation", "python_version", "platform"},
                 "DEPLOYMENT_RUNTIME_INVALID")
        for key in ("implementation", "platform"):
            _require(type(runtime[key]) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,31}", runtime[key]) is not None,
                     "DEPLOYMENT_RUNTIME_INVALID")
        version = runtime["python_version"]
        _require(type(version) is list and len(version) == 3
                 and all(type(v) is int and 0 <= v <= 999 for v in version), "DEPLOYMENT_RUNTIME_INVALID")
        _rows(value["repository_files"], dependency=False)
        _rows(value["dependency_records"], dependency=True)
        _require(type(value["code_hash"]) is str and _HASH.fullmatch(value["code_hash"]) is not None
                 and value["code_hash"] == _code_hash(value["repository_files"], value["dependency_records"]),
                 "DEPLOYMENT_CODE_HASH_MISMATCH")
        body = {key: item for key, item in value.items() if key != "manifest_sha256"}
        _require(type(value["manifest_sha256"]) is str and _HASH.fullmatch(value["manifest_sha256"]) is not None
                 and value["manifest_sha256"] == _digest(body), "DEPLOYMENT_MANIFEST_HASH_MISMATCH")
        _require(len(_canonical(value).encode("utf-8")) <= MAX_MANIFEST_BYTES, "DEPLOYMENT_MANIFEST_TOO_LARGE")
        return json.loads(_canonical(value))
    except DeploymentError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise DeploymentError("DEPLOYMENT_SCHEMA_INVALID") from None


def _pairs(items):
    out = {}
    for key, value in items:
        _require(key not in out, "DEPLOYMENT_DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _invalid_number(value):
    raise DeploymentError("DEPLOYMENT_JSON_NUMBER_INVALID")


def parse_manifest(raw):
    """Parse bounded UTF-8 JSON; reject duplicate keys and noninteger numbers."""
    _require(type(raw) in (str, bytes), "DEPLOYMENT_JSON_REQUIRED")
    try:
        encoded = raw.encode("utf-8") if type(raw) is str else raw
        _require(len(encoded) <= MAX_MANIFEST_BYTES, "DEPLOYMENT_MANIFEST_TOO_LARGE")
        value = json.loads(encoded.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_float=_invalid_number, parse_constant=_invalid_number)
        return validate_manifest(value)
    except DeploymentError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise DeploymentError("DEPLOYMENT_JSON_INVALID") from None


def _linked(path):
    """A symlink, or a directory that is any other reparse point (junction, mount point); an absent path is not one."""
    try:
        info = path.lstat()
    except (OSError, ValueError):
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _source_tree(repo_root):
    """Inspect metadata before the trusted D14 closure reader opens source files.

    This is a diagnostic for this reviewed checkout, not a hostile-code sandbox.
    Keep the checkout and interpreter unchanged/exclusively controlled during use.
    """
    _require(type(repo_root) in (str, Path) or isinstance(repo_root, Path), "DEPLOYMENT_REPO_REQUIRED")
    root = Path(repo_root)
    _require(root.is_absolute() and ".." not in root.parts
             and not any(part.casefold() in _PRIVATE or part.casefold().startswith(".env") for part in root.parts),
             "DEPLOYMENT_REPO_REFUSED")
    _require(all(not _linked(part) for part in (root, *root.parents)) and root.resolve() == _ROOT,
             "DEPLOYMENT_CURRENT_CHECKOUT_REQUIRED")
    # Follow only the existing D14 source graph, not unrelated study/data trees.
    # Inspect each source before reusing the owner's AST import walker.
    todo = []
    for relative, recursive in (("core/compliance", False), ("core/odds", False), ("execution", False),
                                ("execution_control", True), ("execution_orders", True),
                                ("execution_accounts", True), ("execution_network", True),
                                ("execution_launch", True)):
        base = root / relative
        _require(all(not _linked(p) for p in (base, *base.parents)), "DEPLOYMENT_LINKED_SOURCE_REFUSED")
        todo.extend(base.rglob("*.py") if recursive else base.glob("*.py"))
    seen, size = set(), 0
    while todo:
        target = todo.pop()
        if target in seen:
            continue
        _require(target.is_relative_to(root) and not target.name.startswith(".env") and not target.is_symlink()
                 and all(not _linked(p) for p in target.parents),
                 "DEPLOYMENT_LINKED_SOURCE_REFUSED")
        info = target.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "DEPLOYMENT_LINKED_SOURCE_REFUSED")
        seen.add(target); size += info.st_size
        _require(len(seen) <= 2048 and size <= 33554432, "DEPLOYMENT_SOURCE_SCAN_BOUND")
        todo.extend(owner._repo_imports(root, target))
        todo.extend(parent / "__init__.py" for parent in target.parents
                    if parent != root and parent.is_relative_to(root) and (parent / "__init__.py").is_file())
    return root


def export_manifest(*, repo_root):
    """Hash this explicit checkout with the running interpreter; no owner-state read."""
    try:
        root = _source_tree(repo_root)
        rows = [[path, sha] for path, sha in owner.code_files(root)]
        repository = [row for row in rows if not row[0].startswith("venv:")]
        dependencies = [row for row in rows if row[0].startswith("venv:")]
        body = {"schema_version": 1, "kind": "tradegen-d14-deployment/1",
                "runtime": {"implementation": sys.implementation.name,
                            "python_version": list(sys.version_info[:3]), "platform": sys.platform},
                "repository_files": repository, "dependency_records": dependencies,
                "code_hash": _code_hash(repository, dependencies),
                "signature_verified": False, "execution_ready": False}
        return validate_manifest({**body, "manifest_sha256": _digest(body)})
    except DeploymentError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError, RecursionError, SyntaxError):
        raise DeploymentError("DEPLOYMENT_EXPORT_REFUSED") from None


def compare_manifests(left, right):
    """Classify differences; matching untrusted hashes do not prove any signature."""
    left, right = validate_manifest(left), validate_manifest(right)
    changes = {}
    for key in ("repository_files", "dependency_records"):
        a, b = dict(left[key]), dict(right[key])
        changes[key] = {"added": sorted(set(b)-set(a)), "removed": sorted(set(a)-set(b)),
                        "changed": sorted(name for name in a.keys() & b.keys() if a[name] != b[name])}
    return {"schema_version": 1, "code_hash_matches": left["code_hash"] == right["code_hash"],
            "runtime_metadata_matches": left["runtime"] == right["runtime"],
            "differences": changes, "signature_verified": False, "execution_ready": False,
            "reasons": ["MANIFEST_INTEGRITY_ONLY", "OWNER_APPROVAL_NOT_CHECKED"]}


def setup_manifest(*, first_limits_at=None):
    """A public setup template; optional date is conditional on first limits today."""
    effective = None
    if first_limits_at is not None:
        try:
            _require(type(first_limits_at) is datetime and first_limits_at.utcoffset() is not None,
                     "DEPLOYMENT_AWARE_LIMIT_TIME_REQUIRED")
            effective = (first_limits_at.astimezone(compliance.KST).date()+timedelta(days=1)).isoformat()
        except (ValueError, OverflowError, TypeError):
            raise DeploymentError("DEPLOYMENT_AWARE_LIMIT_TIME_REQUIRED") from None
    return {"schema_version": 1, "configuration": configuration_manifest(),
            "profile_template": profile_body(LaunchProfile(schema_version=1, profile_id="deployment-unconfigured")),
            "deployment_environment": None, "owner_approvals_checked": False,
            "first_limits": {"assumption": "FIRST_SETTING" if first_limits_at is not None else "UNKNOWN",
                             "earliest_effective_seoul_date": effective, "advisory_only": True,
                             "requires": ["VERIFIED_OWNER_LOG", "SESSION_AND_HALT_CHECKS"]},
            "required_operator_actions": ["CHOOSE_DEPLOYMENT_AND_PROFILE", "CONFIGURE_SECURE_ACCOUNT_ACCESS",
                "COMPARE_DEPLOYMENT_CODE_CLOSURE", "REVIEW_AND_SIGN_CODE_TABLES_AND_LIMITS",
                "VERIFY_ACCOUNT_AND_STRATEGY_EVIDENCE", "PREPARE_AND_REVIEW_ACTUAL_SESSION_ID"],
            "signature_verified": False, "execution_ready": False}


def _arguments(argv):
    _require(type(argv) in (tuple, list) and all(type(v) is str for v in argv), "DEPLOYMENT_ARGUMENTS_INVALID")
    if not argv:
        return "setup", {}
    mode, *rest = argv
    allowed = {"setup": {"--first-limits-at"}, "export": {"--repo"}, "compare": {"--left", "--right"}}
    _require(mode in allowed and len(rest) % 2 == 0, "DEPLOYMENT_ARGUMENTS_INVALID")
    values = {}
    for key, value in zip(rest[::2], rest[1::2]):
        _require(key in allowed[mode] and key not in values and bool(value) and not value.startswith("--"),
                 "DEPLOYMENT_ARGUMENTS_INVALID")
        values[key] = value
    _require(mode == "setup" or set(values) == allowed[mode], "DEPLOYMENT_ARGUMENTS_INVALID")
    return mode, values


def main(argv=None):
    try:
        mode, args = _arguments(sys.argv[1:] if argv is None else argv)
        if mode == "setup":
            try:
                at = datetime.fromisoformat(args["--first-limits-at"]) if "--first-limits-at" in args else None
            except ValueError:
                raise DeploymentError("DEPLOYMENT_AWARE_LIMIT_TIME_REQUIRED") from None
            result = setup_manifest(first_limits_at=at)
        elif mode == "export":
            result = export_manifest(repo_root=args["--repo"])
        else:
            result = compare_manifests(parse_manifest(_read_profile(args["--left"])),
                                       parse_manifest(_read_profile(args["--right"])))
        print(_canonical(result) if mode == "export" else json.dumps(result, sort_keys=True, indent=2))
        return 0 if mode in ("export", "compare") else 2
    except (DeploymentError, ProfileError) as exc:
        code = str(exc) if isinstance(exc, DeploymentError) else "DEPLOYMENT_INPUT_REFUSED"
    except (OSError, ValueError, TypeError, RecursionError):
        code = "DEPLOYMENT_INPUT_REFUSED"
    print(json.dumps({"signature_verified": False, "execution_ready": False, "reason": code}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
