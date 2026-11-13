"""Explicit research archival and replay; no approval, recovery, home or live execution.

Original bytes are backed up before evaluation or semantic admission.
Plan parsing before archival only identifies expected input names; refusal is retained. A stored manifest is
never an issued research result: sealed replay validates every input again and
invokes the actual family evaluator at the original evaluation time.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from execution_launch import research_bundle_format as F
from execution_launch.research_bundle_store import BundleRoots, BundleStore, BundleStoreLimits
from execution_launch.evidence_objects import ObjectLimits, StoreBudget, EvidenceObjectError
from execution_launch import study as S, strategy as E
from execution_launch.study_evidence import evaluate_study_family
from execution_launch.study_receipts import validate_study_receipts, receipt_audit_digest
from execution_launch.profile import parse_profile_json, profile_digest, rule_terms_digest
from execution_launch.program import program_digest
from execution_launch.review_request import build_family_commitment
from execution_launch.workflow import read_file, _PRIVATE
from execution_launch.private_input import _REFUSED_ATTRIBUTES

_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}")
_SINGLE = ("plan", "profile", "source_receipts", "program_source", "capture_source_manifest",
           "prior_research", "registration_commitment")
_EXPLICIT_ROLES = frozenset(_SINGLE + ("source_file", "report"))
_AUTH_REQUIRED = "BUNDLE_MANIFEST_AUTHENTICATION_REQUIRED"


class ResearchBundleError(ValueError):
    """Fixed diagnostics; original paths and source bytes never enter error text."""


def _need(value, code):
    if not value:
        raise ResearchBundleError(code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _code(exc):
    value = str(exc)
    return value if isinstance(exc, ValueError) and _CODE.fullmatch(value) else "BUNDLE_RESEARCH_VALIDATION_REFUSED"


@dataclass(frozen=True, kw_only=True)
class BundleInputFile:
    role: str
    path: Path
    source_name: str | None = None
    required: bool = True


@dataclass(frozen=True, kw_only=True)
class StudyBundleInputs:
    files: tuple[BundleInputFile, ...]
    captures_directory: Path


@dataclass(frozen=True, kw_only=True)
class BundleFinalization:
    status: str
    input_archive_digest: str
    bundle_digest: str | None
    raw_backup_verified: bool
    verified_backup_verified: bool
    reasons: tuple[str, ...]
    source_authenticated: bool = False
    manifest_authenticated: bool = False
    execution_ready: bool = False
    automatic_recovery_supported: bool = False


@dataclass(frozen=True, kw_only=True)
class SealedEvaluation:
    bundle_digest: str
    input_archive_digest: str
    evaluated_at: datetime
    family: object
    reasons: tuple[str, ...] = (_AUTH_REQUIRED,)
    manifest_authenticated: bool = False
    execution_ready: bool = False


def _safe_path(path):
    _need(isinstance(path, Path) and path.is_absolute() and ".." not in path.parts
          and "\x00" not in str(path) and ":" not in str(path)[len(path.anchor):], "BUNDLE_INPUT_PATH_REFUSED")
    _need(not any(part.casefold() in _PRIVATE or part.casefold() == ".env"
                  or part.casefold().startswith(".env.") or part.startswith(".")
                  for part in path.parts[1:]), "BUNDLE_INPUT_PATH_REFUSED")
    return path


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _regular(info):
    return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_ino > 0
            and not getattr(info, "st_file_attributes", 0) & _REFUSED_ATTRIBUTES)


def _read_snapshot(path, maximum):
    """Bind before/read/after to one handle; opaque changed bytes stay evidence."""
    raw, descriptor, directory = None, None, None
    try:
        _safe_path(path)
        prefixes = tuple(reversed(path.parents))
        parents = []
        for prefix in prefixes:
            info = os.lstat(prefix)
            _need(stat.S_ISDIR(info.st_mode) and info.st_ino > 0
                  and not getattr(info, "st_file_attributes", 0) & _REFUSED_ATTRIBUTES,
                  "BUNDLE_INPUT_PATH_REFUSED")
            parents.append((info.st_dev, info.st_ino))
        before = os.lstat(path)
        _need(_regular(before), "BUNDLE_INPUT_PATH_REFUSED")
        if os.name == "nt":
            import ntpath
            from execution_launch.private_input import _checked_path
            absolute = _checked_path(str(path), suffix=path.suffix, private=_PRIVATE)
            _need(ntpath.normcase(os.path.realpath(absolute, strict=True)) == ntpath.normcase(absolute),
                  "BUNDLE_INPUT_PATH_REFUSED")
            descriptor = os.open(absolute, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
        else:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            directory = os.open(path.anchor, flags)
            opened = os.fstat(directory)
            _need((opened.st_dev, opened.st_ino) == parents[0], "BUNDLE_INPUT_CHANGED")
            for index, component in enumerate(path.parts[1:-1], 1):
                following = os.open(component, flags, dir_fd=directory)
                os.close(directory)
                directory = following
                opened = os.fstat(directory)
                _need((opened.st_dev, opened.st_ino) == parents[index], "BUNDLE_INPUT_CHANGED")
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
                                 | getattr(os, "O_CLOEXEC", 0), dir_fd=directory)
        opened = os.fstat(descriptor)
        _need(_regular(opened) and _identity(opened) == _identity(before), "BUNDLE_INPUT_CHANGED")
        if opened.st_size > maximum:
            return None, "LIMIT_EXCEEDED"
        # Ownership transfers only after fdopen succeeds; no second pathname read.
        handle = os.fdopen(descriptor, "rb")
        descriptor = None
        with handle:
            raw = handle.read(maximum + 1)
            after_handle = os.fstat(handle.fileno())
        if len(raw) > maximum:
            return None, "LIMIT_EXCEEDED"
        after = os.lstat(path)
        current_parents = tuple((info.st_dev, info.st_ino) for info in map(os.lstat, prefixes))
        if (not _regular(after_handle) or not _regular(after)
                or _identity(before) != _identity(after_handle) or _identity(before) != _identity(after)
                or tuple(parents) != current_parents or len(raw) != after.st_size):
            return raw, "CHANGED"
        return raw, "COLLECTED"
    except FileNotFoundError:
        return raw, "MISSING"
    except (OSError, ValueError, RuntimeError, TypeError):
        return raw, "REFUSED"
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def _inventory(directory, maximum):
    """One level of capture names only; no recursive or hidden-file collection."""
    _safe_path(directory)
    absolute, identity = S._capture_directory(directory)
    names = []
    count = 0
    descriptor = None
    try:
        target = absolute
        if os.name != "nt":
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
            descriptor = os.open(absolute.anchor, flags)
            for component in absolute.parts[1:]:
                following = os.open(component, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = following
            opened = os.fstat(descriptor)
            _need((opened.st_dev, opened.st_ino) == identity, "BUNDLE_INPUT_CHANGED")
            target = descriptor
        with os.scandir(target) as entries:
            for entry in entries:
                count += 1
                _need(count <= maximum, "BUNDLE_RESOURCE_LIMIT")
                if entry.name.casefold().endswith((".capture.json", ".incomplete.json")):
                    names.append(entry.name)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    _need(S._capture_directory(absolute) == (absolute, identity), "BUNDLE_INPUT_CHANGED")
    return tuple(sorted(names)), identity


def _snapshot(inputs, store, *, run_id, raw_revision_id, attempt_id, parent_bundle_sha256):
    _need(type(inputs) is StudyBundleInputs and type(inputs.files) is tuple
          and all(type(item) is BundleInputFile and item.role in _EXPLICIT_ROLES
                  and type(item.required) is bool and isinstance(item.path, Path)
                  for item in inputs.files), "BUNDLE_INPUTS_FORMAT_INVALID")
    limits = store.limits.format_limits
    files, observations, payloads, complete, total, overflow = [], [], {}, True, 0, False

    def inventory_limit():
        nonlocal complete, overflow
        complete, overflow = False, True
        if len(observations) < limits.max_files:
            observations.append(F.InputObservation(observation_id="i%06d" % len(observations),
                original_name="input inventory limit", role="other_input", study_id=None,
                source_name=None, required=True, status="LIMIT_EXCEEDED", logical_id=None))

    def observe(name, role, study_id, source_name, required, path=None, status=None):
        nonlocal complete, total, overflow
        # Reserve a bounded incident row before further I/O. Capacity exhaustion
        # cannot discard bytes already captured or pretend the inventory ended.
        if overflow:
            return
        if len(observations) >= limits.max_files-1:
            inventory_limit()
            return
        raw = None
        if status is None:
            remaining = min(limits.max_file_bytes, store.limits.object_limits.max_payload_bytes,
                            store.limits.object_limits.chunk_bytes*store.limits.object_limits.max_chunks,
                            limits.max_total_bytes-total)
            raw, status = _read_snapshot(path, remaining)
        metadata = dict(original_name=name, role=role, study_id=study_id,
                        source_name=source_name, required=required)
        logical, reference = None, None
        if raw is not None:
            try:
                reference = store.preview_payload(raw)
            except EvidenceObjectError as exc:
                if str(exc) != "EVIDENCE_OBJECT_LIMIT_EXCEEDED":
                    raise
                raw, status = None, "LIMIT_EXCEEDED"
        if raw is not None:
            logical = "f%06d" % len(files)
            files.append(F.BundleFile(logical_id=logical, **metadata, byte_count=len(raw),
                sha256=_sha(raw), payload_ref=reference))
            payloads[logical] = raw
            total += len(raw)
        observations.append(F.InputObservation(observation_id="i%06d" % len(observations),
            **metadata, status="COLLECTED" if raw is not None else status, logical_id=logical))
        if status != "COLLECTED":
            complete = False
            if raw is not None:
                observations.append(F.InputObservation(observation_id="i%06d" % len(observations),
                    original_name=name+" [changed input]", role="other_input", study_id=study_id,
                    source_name=None, required=True, status=status, logical_id=None))
                if len(observations) == limits.max_files:
                    overflow = True

    for item in inputs.files:
        observe(item.path.name, item.role, None, item.source_name, item.required, path=item.path)
    for role in _SINGLE:
        if not any(item.role == role for item in inputs.files):
            observe(role, role, None, None, True, status="MISSING")
    expected = None
    plan_files = [item for item in files if item.role == "plan"]
    if len(plan_files) == 1:
        try:
            plan = S.parse_study_plan(payloads[plan_files[0].logical_id])
            expected = tuple(sorted(candidate.protocol.study_id for candidate in plan.candidates))
        except (ValueError, TypeError, OSError, AttributeError, ArithmeticError):
            pass  # Invalid/historical plan bytes are preserved, never replaced by an invented candidate set.
    names, identity = (), None
    try:
        names, identity = _inventory(inputs.captures_directory, limits.max_files)
    except (ValueError, OSError, TypeError) as exc:
        observe("capture inventory", "other_input", None, None, True,
                status="LIMIT_EXCEEDED" if str(exc) == "BUNDLE_RESOURCE_LIMIT" else "REFUSED")
    for name in names:
        incomplete = name.casefold().endswith(".incomplete.json")
        suffix = ".incomplete.json" if incomplete else ".capture.json"
        identifier = name[:-len(suffix)]
        identifier = identifier if _ID.fullmatch(identifier) else None
        observe(name, "incomplete_capture" if incomplete else "capture", identifier, None, True,
                path=inputs.captures_directory/name)
    if expected is not None:
        for identifier in expected:
            if identifier+".capture.json" not in names:
                observe(identifier+".capture.json", "capture", identifier, None, True, status="MISSING")
    if identity is not None:
        try:
            unchanged = _inventory(inputs.captures_directory, limits.max_files) == (names, identity)
        except (ValueError, OSError, TypeError):
            unchanged = False
        if not unchanged:
            observe("capture inventory changed", "other_input", None, None, True, status="CHANGED")
    manifest = F.RawArchiveManifest(schema_version=1, kind="RAW_ARCHIVED", run_id=run_id,
        revision_id=raw_revision_id, attempt_id=attempt_id, parent_bundle_sha256=parent_bundle_sha256,
        storage_policy_sha256=store.limits.policy_sha256,
        object_policy_sha256=store.limits.object_limits.policy_sha256, expected_candidates=expected,
        inventory_complete=complete, observed_inputs=tuple(observations), files=tuple(files))
    return manifest, payloads


def _research(raw_manifest, payloads, *, evaluated_at):
    """Revalidate all source and receipt inputs before the first A0b evaluator call."""
    F.validate_payloads(raw_manifest, payloads)
    by_role = {}
    for item in raw_manifest.files:
        by_role.setdefault(item.role, []).append(item)
    _need(all(len(by_role.get(role, ())) == 1 for role in _SINGLE), "BUNDLE_INPUT_FILE_SET_INVALID")

    def one(role):
        return payloads[by_role[role][0].logical_id]

    plan = S.parse_study_plan(one("plan"))
    profile = parse_profile_json(one("profile"))
    ids = tuple(sorted(candidate.protocol.study_id for candidate in plan.candidates))
    _need(ids == raw_manifest.expected_candidates, "BUNDLE_CANDIDATE_SET_INVALID")
    source = S.capture_source_artifact(plan.candidates[0].protocol)
    _need(one("capture_source_manifest") == source, "BUNDLE_CURRENT_SOURCE_MISMATCH")
    source_members = json.loads(source)["files"]
    source_files = by_role.get("source_file", ())
    _need(len(source_files) == len(source_members)
          and {item.source_name for item in source_files} == set(source_members), "BUNDLE_SOURCE_FILE_SET_INVALID")
    _need(all(_sha(payloads[item.logical_id]) == source_members[item.source_name] for item in source_files),
          "BUNDLE_CURRENT_SOURCE_MISMATCH")
    _need(one("program_source") == S._fixed_file(S.PROGRAM_SOURCE)
          and _sha(one("prior_research")) == plan.prior_research_sha256,
          "BUNDLE_CURRENT_SOURCE_MISMATCH")
    _need(one("registration_commitment") == S.commitment_json(plan).encode("ascii"),
          "BUNDLE_REGISTRATION_COMMITMENT_MISMATCH")
    # A correctly recorded aborted attempt gets its distinct receipt diagnosis,
    # including when its retained snapshots have .incomplete.json names. This
    # diagnostic pass cannot issue a result or promote incomplete evidence.
    diagnostic_captures = by_role.get("capture", []) + by_role.get("incomplete_capture", [])
    if len(diagnostic_captures) == len(ids) and {item.study_id for item in diagnostic_captures} == set(ids):
        audit = validate_study_receipts(plan,
            {item.study_id: payloads[item.logical_id] for item in diagnostic_captures}, one("source_receipts"))
    else:
        raise ResearchBundleError("BUNDLE_CANDIDATE_SET_INVALID")
    # Apply the same name/role/required/candidate eligibility as verified
    # metadata before any result is issued. Recorded abort diagnosis stays first.
    F.validate_complete_inputs(raw_manifest)
    captures = by_role.get("capture", ())
    _need(len(captures) == len(ids) and {item.study_id for item in captures} == set(ids)
          and all(item.original_name == item.study_id+".capture.json" for item in captures),
          "BUNDLE_CANDIDATE_SET_INVALID")
    for candidate in plan.candidates:
        code = program_digest(candidate.program, one("program_source"))
        variant = replace(profile, strategy_id=candidate.program.strategy_id, strategy_code_sha256=code)
        S._bound_profile(variant, candidate.protocol)
    capture_bytes = {item.study_id: payloads[item.logical_id] for item in captures}
    family = evaluate_study_family(tuple(candidate.protocol for candidate in plan.candidates), capture_bytes,
        profile.instrument_rules, registry=plan.registry, now=evaluated_at)
    kinds = {row.result.source_kind for row in family.rows}
    _need(len(kinds) == 1, "BUNDLE_SOURCE_KIND_MISMATCH")
    commitment = build_family_commitment(plan_digest=S.validate_study_plan(plan),
        capture_digests=family.capture_digests,
        result_digests={row.study_id: E.evidence_digest(row.result) for row in family.rows})
    record = _json_bytes({"kind": "tradegen-research-evaluation-record/1",
        "evaluated_at": E._plain(evaluated_at), "family_commitment": commitment,
        "results": [{"study_id": row.study_id, "result_digest": E.evidence_digest(row.result),
                     "result": E._plain(row.result)} for row in family.rows]})
    return plan, profile, family, audit, commitment, record, kinds.pop()


def _verified_manifest(raw, raw_digest, store, payloads, *, revision_id, evaluated_at, evaluated):
    plan, profile, family, audit, commitment, record, source_kind = evaluated
    logical = "evaluation_record"
    _need(logical not in payloads, "BUNDLE_DERIVED_FILE_CONFLICT")
    derived = F.BundleFile(logical_id=logical, original_name="evaluation-record-"+_sha(record)[:16]+".json",
        role="evaluation_record", study_id=None, source_name=None, required=True, byte_count=len(record),
        sha256=_sha(record), payload_ref=store.preview_payload(record))
    capture_ids = {item.study_id: item.logical_id for item in raw.files if item.role == "capture"}
    protocol_by_id = {candidate.protocol.study_id: candidate.protocol for candidate in plan.candidates}
    first = plan.candidates[0].protocol
    manifest = F.VerifiedBundleManifest(schema_version=1, kind="VERIFIED_UNAPPROVED", run_id=raw.run_id,
        revision_id=revision_id, attempt_id=raw.attempt_id, parent_bundle_sha256=raw.parent_bundle_sha256,
        storage_policy_sha256=raw.storage_policy_sha256, object_policy_sha256=raw.object_policy_sha256,
        input_archive_digest=raw_digest, plan_digest=S.validate_study_plan(plan), profile_digest=profile_digest(profile),
        rules_digest=rule_terms_digest(profile.instrument_rules), registry_digest=E.validate_registry(plan.registry),
        source_digest=first.capture_source_code_sha256, family_digest=commitment["family_sha256"],
        receipt_audit_digest=receipt_audit_digest(audit), evaluator_revision=first.evaluator_revision,
        source_kind_claim=source_kind, capture_start=first.capture_start, capture_end=first.capture_end,
        evaluated_at=evaluated_at, candidates=tuple(sorted((F.CandidateEvidence(study_id=row.study_id,
            protocol_digest=E.evidence_digest(protocol_by_id[row.study_id]),
            capture_logical_id=capture_ids[row.study_id], result_digest=E.evidence_digest(row.result))
            for row in family.rows), key=lambda row: row.study_id)),
        files=tuple(sorted(raw.files+(derived,), key=lambda row: row.logical_id)))
    F.validate_verified_inputs(raw, manifest, limits=store.limits.format_limits)
    return manifest, payloads | {logical: record}


def finalize_study_bundle(inputs, store, *, run_id, raw_revision_id, verified_revision_id,
                          attempt_id, parent_bundle_sha256=None, evaluated_at):
    _need(type(store) is BundleStore, "BUNDLE_STORE_REQUIRED")
    _need(type(evaluated_at) is datetime and evaluated_at.utcoffset() is not None,
          "BUNDLE_EXPLICIT_EVALUATION_TIME_REQUIRED")
    _need(raw_revision_id != verified_revision_id, "BUNDLE_REVISION_REUSE_REFUSED")
    raw, payloads = _snapshot(inputs, store, run_id=run_id, raw_revision_id=raw_revision_id,
                            attempt_id=attempt_id, parent_bundle_sha256=parent_bundle_sha256)
    raw_bytes = F.raw_archive_bytes(raw, limits=store.limits.format_limits)
    receipt = store.archive_raw(raw_bytes, payloads)
    _need(receipt.backup_verified, "BUNDLE_RAW_BACKUP_REQUIRED")
    # Reopen catalog-backed originals; no working path is read after this point.
    archived = store.read_raw(receipt.bundle_digest, require_backup=True)
    try:
        evaluated = _research(archived.manifest, archived.files, evaluated_at=evaluated_at)
        verified, combined = _verified_manifest(archived.manifest, receipt.bundle_digest, store,
            dict(archived.files), revision_id=verified_revision_id, evaluated_at=evaluated_at, evaluated=evaluated)
    except (ValueError, TypeError, AttributeError, ArithmeticError, OSError) as exc:
        code = _code(exc)
        store.record_diagnostic(receipt.bundle_digest, code)
        return BundleFinalization(status="RAW_ARCHIVED", input_archive_digest=receipt.bundle_digest,
            bundle_digest=None, raw_backup_verified=True, verified_backup_verified=False, reasons=(code, _AUTH_REQUIRED))
    published = store.commit_verified(F.verified_bundle_bytes(verified, limits=store.limits.format_limits), combined)
    _need(published.backup_verified, "BUNDLE_VERIFIED_BACKUP_REQUIRED")
    return BundleFinalization(status="VERIFIED_UNAPPROVED", input_archive_digest=receipt.bundle_digest,
        bundle_digest=published.bundle_digest, raw_backup_verified=True, verified_backup_verified=True,
        reasons=(_AUTH_REQUIRED,))


def evaluate_sealed_study(store, bundle_digest):
    """Historical actual re-evaluation from complete backed-up bytes, never current approval."""
    _need(type(store) is BundleStore, "BUNDLE_STORE_REQUIRED")
    verified = store.read_verified(bundle_digest, require_backup=True)
    manifest = verified.manifest
    raw = store.read_raw(manifest.input_archive_digest, require_backup=True)
    F.validate_verified_inputs(raw.manifest, manifest, limits=store.limits.format_limits)
    F.validate_payloads(manifest, verified.files, limits=store.limits.format_limits)
    _need(all(verified.files[key] == value for key, value in raw.files.items()), "BUNDLE_INPUT_BYTES_MISMATCH")
    evaluated = _research(raw.manifest, raw.files, evaluated_at=manifest.evaluated_at)
    expected, payloads = _verified_manifest(raw.manifest, manifest.input_archive_digest, store, dict(raw.files),
        revision_id=manifest.revision_id, evaluated_at=manifest.evaluated_at, evaluated=evaluated)
    _need(F.verified_bundle_bytes(expected, limits=store.limits.format_limits) == verified.manifest_bytes
          and payloads == dict(verified.files), "BUNDLE_REPRODUCTION_MISMATCH")
    return SealedEvaluation(bundle_digest=bundle_digest, input_archive_digest=manifest.input_archive_digest,
                            evaluated_at=manifest.evaluated_at, family=evaluated[2])


def _document(raw, maximum=1024*1024):
    _need(type(raw) is bytes and len(raw) <= maximum, "BUNDLE_INPUT_DOCUMENT_INVALID")
    def pairs(rows):
        result = {}
        for key, value in rows:
            _need(key not in result, "BUNDLE_INPUT_DOCUMENT_INVALID")
            result[key] = value
        return result
    def invalid(value):
        raise ResearchBundleError("BUNDLE_INPUT_DOCUMENT_INVALID")
    try:
        body = json.loads(raw, object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
        _need(type(body) is dict, "BUNDLE_INPUT_DOCUMENT_INVALID")
        return body
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ResearchBundleError("BUNDLE_INPUT_DOCUMENT_INVALID") from None


def read_inputs(path):
    body = _document(read_file(path, 1024*1024))
    _need(set(body) == {"schema_version", "files", "captures_directory"}
          and type(body["schema_version"]) is int and body["schema_version"] == 1
          and type(body["files"]) is list and len(body["files"]) <= F.DEFAULT_LIMITS.max_files
          and type(body["captures_directory"]) is str, "BUNDLE_INPUT_DOCUMENT_INVALID")
    items = []
    for item in body["files"]:
        _need(type(item) is dict and set(item) == {"role", "path", "source_name", "required"}
              and type(item["path"]) is str, "BUNDLE_INPUT_DOCUMENT_INVALID")
        items.append(BundleInputFile(**(item | {"path": Path(item["path"])})))
    return StudyBundleInputs(files=tuple(items), captures_directory=Path(body["captures_directory"]))


def read_store_limits(path):
    body = _document(read_file(path, 65536), 65536)
    _need(set(body) == {"format_limits", "object_limits", "primary_budget", "backup_budget",
                        "max_catalog_bytes", "max_catalog_records"}, "BUNDLE_STORE_CONFIGURATION_INVALID")
    try:
        return BundleStoreLimits(format_limits=F.BundleLimits(**body["format_limits"]),
            object_limits=ObjectLimits(**body["object_limits"]), primary_budget=StoreBudget(**body["primary_budget"]),
            backup_budget=StoreBudget(**body["backup_budget"]), max_catalog_bytes=body["max_catalog_bytes"],
            max_catalog_records=body["max_catalog_records"])
    except (TypeError, ValueError):
        raise ResearchBundleError("BUNDLE_STORE_CONFIGURATION_INVALID") from None


def open_explicit_store(sealed_root, backup_root, head_name, limits_path):
    return BundleStore(roots=BundleRoots(sealed_root=Path(sealed_root), backup_root=Path(backup_root)),
                       limits=read_store_limits(limits_path), head_name=head_name)


def _arguments(argv):
    _need(type(argv) in (list, tuple) and all(type(item) is str for item in argv) and argv,
          "BUNDLE_ARGUMENTS_REQUIRED")
    if argv[0] == "provision":
        raise ResearchBundleError("BUNDLE_OPERATOR_PROVISION_REQUIRED")
    common = {"sealed-root", "backup-root", "head-name", "limits"}
    command = argv[0]
    required = {"finalize": common | {"inputs", "run-id", "raw-revision", "verified-revision", "attempt-id", "evaluated-at"},
                "inspect": common | {"digest"}, "evaluate": common | {"digest"}}
    _need(command in required and len(argv) % 2 == 1, "BUNDLE_ARGUMENTS_INVALID")
    optional = {"parent-bundle"} if command == "finalize" else set()
    values = {}
    for key, value in zip(argv[1::2], argv[2::2]):
        _need(key.startswith("--") and key[2:] in required[command] | optional
              and key[2:] not in values and value and not value.startswith("--"), "BUNDLE_ARGUMENTS_INVALID")
        values[key[2:]] = value
    _need(required[command] <= set(values), "BUNDLE_ARGUMENTS_REQUIRED")
    return command, values


def main(argv=None):
    """Offline explicit finalize/inspect/evaluate only; provisioning is an owner utility."""
    try:
        command, args = _arguments(sys.argv[1:] if argv is None else argv)
        store = open_explicit_store(args["sealed-root"], args["backup-root"], args["head-name"], args["limits"])
        if command == "finalize":
            at = datetime.fromisoformat(args["evaluated-at"])
            result = finalize_study_bundle(read_inputs(args["inputs"]), store, run_id=args["run-id"],
                raw_revision_id=args["raw-revision"], verified_revision_id=args["verified-revision"],
                attempt_id=args["attempt-id"], parent_bundle_sha256=args.get("parent-bundle"), evaluated_at=at)
            print(json.dumps(asdict(result), sort_keys=True))
            return 0 if result.status == "VERIFIED_UNAPPROVED" else 1
        if command == "evaluate":
            result = evaluate_sealed_study(store, args["digest"])
            print(json.dumps({"status": "REEVALUATED_UNAPPROVED", "bundle_digest": result.bundle_digest,
                "input_archive_digest": result.input_archive_digest, "evaluated_at": E._plain(result.evaluated_at),
                "result_digests": {row.study_id: E.evidence_digest(row.result) for row in result.family.rows},
                "reasons": list(result.reasons), "execution_ready": False, "manifest_authenticated": False}, sort_keys=True))
            return 0
        receipt = store.inspect(args["digest"])
        reader = store.read_raw if receipt.kind == "RAW_ARCHIVED" else store.read_verified
        stored = reader(args["digest"], require_backup=True)
        print(json.dumps({"status": receipt.kind, "bundle_digest": receipt.bundle_digest,
            "backup_verified": stored.backup_verified, "files": len(stored.files),
            "reasons": [_AUTH_REQUIRED], "execution_ready": False, "manifest_authenticated": False}, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, AttributeError, ArithmeticError, RecursionError) as exc:
        print(json.dumps({"status": "REFUSED", "reasons": [_code(exc)], "execution_ready": False,
                          "manifest_authenticated": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
