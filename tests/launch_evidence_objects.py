"""Lossless evidence objects over synthetic bytes in temporary stores.

These tests exercise only staging and read-back. They grant no history-head,
research approval, order or account authority and model no real account incident.
"""
from contextlib import contextmanager
from dataclasses import replace
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core import isolation
from execution_launch import evidence_objects as E
from tests.notrun import NotRun


def refused(call, *codes):
    try:
        call()
    except E.EvidenceObjectError as exc:
        assert str(exc) in codes, (str(exc), codes)
        return
    raise AssertionError("expected an evidence-object refusal: " + repr(codes))


def limits(**changes):
    return E.ObjectLimits(**(dict(chunk_bytes=256, max_payload_bytes=4096,
                                 max_chunks=16, max_manifest_bytes=4096) | changes))


@contextmanager
def store(policy=None):
    with tempfile.TemporaryDirectory(prefix="tradegen_evidence_objects_") as temporary:
        root = Path(temporary) / "store"
        yield E.EvidenceObjectStore(root=root, limits=limits() if policy is None else policy), root


def object_path(root, sha):
    return root / "objects" / (sha + ".blob")


def manifest(root, reference):
    return json.loads(object_path(root, reference.manifest_sha256).read_bytes())


def forged_manifest(root, reference, value):
    """Rehash a corrupt descriptor so tests reach strict parsing, not only the outer hash check."""
    raw = value if type(value) is bytes else E._canonical(value)
    sha = E._object_digest("manifest", raw)
    object_path(root, sha).write_bytes(raw)
    return replace(reference, manifest_sha256=sha, manifest_bytes=len(raw))


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def synthetic_inventory_payload():
    """A large fake inventory and a normal, nonempty book; no account identifiers."""
    raw_book = (b'[{"market":"KRW-BTC","timestamp":1924992000000,"level":0,'
                b'"total_ask_size":3,"total_bid_size":4,"orderbook_units":['
                b'{"ask_price":102,"bid_price":100,"ask_size":3,"bid_size":4}]}]')
    holdings = [["KRW-FAKE" + str(i), "1.00000000", "100.00", "2031-01-01T00:00:00Z"]
                for i in range(1500)]
    body = {"receipt": {"raw_body_b64": base64.b64encode(raw_book).decode("ascii"),
                        "sha256": hashlib.sha256(raw_book).hexdigest()},
            "holdings": holdings, "flags": [[row[0], "unflagged"] for row in holdings],
            "tickers": [[row[0], "100.00000000"] for row in holdings],
            "note": "Synthetic boundary fixture; not a real account."}
    raw = (json.dumps(body, ensure_ascii=True, indent=2) + "\r\n").encode("ascii")
    return raw, raw_book, holdings


def test_large_inventory_and_valid_book_survive_without_loss_or_substitution():
    raw, book, holdings = synthetic_inventory_payload()
    assert len(raw) > 262144, len(raw)
    policy = limits(chunk_bytes=65536, max_payload_bytes=2 * 1024 * 1024,
                    max_chunks=32, max_manifest_bytes=65536)
    with store(policy) as (objects, root):
        reference = objects.stage(raw)
        assert objects.read(reference) == raw
        restored = json.loads(objects.read(reference))
        assert restored["holdings"] == holdings
        assert len(restored["flags"]) == len(restored["tickers"]) == len(holdings)
        assert base64.b64decode(restored["receipt"]["raw_body_b64"]) == book
        assert restored["receipt"]["sha256"] == hashlib.sha256(book).hexdigest()
        assert reference.payload_bytes == len(raw)
        assert reference.payload_sha256 == hashlib.sha256(raw).hexdigest()
        assert E.EvidenceObjectStore(root=root, limits=policy).read(reference) == raw


def test_chunk_boundary_and_payload_limit_roundtrip_exact_bytes():
    policy = limits()
    for size in (policy.chunk_bytes - 1, policy.chunk_bytes, policy.chunk_bytes + 1,
                 policy.max_payload_bytes - 1, policy.max_payload_bytes):
        raw = bytes(range(251)) * (size // 251) + bytes(range(size % 251))
        with store(policy) as (objects, _):
            reference = objects.stage(raw)
            assert objects.read(reference) == raw
            assert E.decode_reference(E.encode_reference(reference)) == reference


def test_bad_or_oversized_payload_refuses_before_store_files_are_created():
    for payload in (None, "text", bytearray(b"x"), b"", b"x" * 4097):
        with store() as (objects, root):
            refused(lambda: objects.stage(payload), "EVIDENCE_OBJECT_INPUT_INVALID",
                    "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
            assert not root.exists(), files(root)


def test_manifest_limit_accepts_exact_bound_and_refuses_one_byte_less_before_writes():
    with store() as (objects, _):
        size = objects.stage(b"manifest boundary").manifest_bytes
    for cap in (size - 1, size, size + 1):
        with store(limits(max_manifest_bytes=cap)) as (objects, root):
            if cap < size:
                refused(lambda: objects.stage(b"manifest boundary"), "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
                assert not root.exists()
            else:
                reference = objects.stage(b"manifest boundary")
                assert reference.manifest_bytes == size
                assert objects.read(reference) == b"manifest boundary"


def test_chunk_count_is_an_independent_admission_limit():
    with store(limits(chunk_bytes=64, max_chunks=2)) as (objects, root):
        refused(lambda: objects.stage(b"x" * 129), "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        assert not root.exists()
        assert objects.read(objects.stage(b"x" * 128)) == b"x" * 128


def test_duplicate_stage_and_fresh_instances_preserve_existing_object_bytes():
    raw = b"unchanged original\x00\r\n" * 40
    with store() as (objects, root):
        first = objects.stage(raw)
        before = files(root)
        assert objects.stage(raw) == first
        assert E.EvidenceObjectStore(root=root, limits=limits()).read(first) == raw
        assert files(root) == before


def test_changed_policy_cannot_reinterpret_an_existing_reference():
    with store() as (objects, root):
        reference = objects.stage(b"policy-bound bytes")
        other = E.EvidenceObjectStore(root=root, limits=limits(max_payload_bytes=8192, max_chunks=32))
        refused(lambda: other.read(reference), "EVIDENCE_OBJECT_POLICY_MISMATCH")


def test_reference_extra_fields_duplicate_keys_and_paths_refuse():
    with store() as (objects, _):
        reference = objects.stage(b"strict reference")
        raw = E.encode_reference(reference)
        body = json.loads(raw)
        invalid = [body | {"other": None}, body | {"manifest_sha256": "../outside"},
                   body | {"manifest_bytes": True}, body | {"payload_bytes": -1},
                   body | {"payload_sha256": "A" * 64}, body | {"policy_sha256": "0" * 63}]
        for value in invalid:
            refused(lambda value=value: E.decode_reference(E._canonical(value)),
                    "EVIDENCE_OBJECT_REFERENCE_INVALID")
        duplicate = b'{"schema":1,' + raw.lstrip()[1:]
        refused(lambda: E.decode_reference(duplicate), "EVIDENCE_OBJECT_REFERENCE_INVALID")
        refused(lambda: E.decode_reference(b" " * 4097), "EVIDENCE_OBJECT_REFERENCE_INVALID")


def test_reference_hash_and_lengths_are_rechecked_even_for_existing_objects():
    with store() as (objects, _):
        reference = objects.stage(b"bound byte lengths")
        for changed in (replace(reference, manifest_bytes=reference.manifest_bytes + 1),
                        replace(reference, payload_bytes=reference.payload_bytes + 1),
                        replace(reference, payload_sha256="0" * 64)):
            refused(lambda changed=changed: objects.read(changed), "EVIDENCE_OBJECT_HASH_MISMATCH",
                    "EVIDENCE_OBJECT_MANIFEST_INVALID", "EVIDENCE_OBJECT_REFERENCE_INVALID")


def test_manifest_tampering_after_successful_read_is_not_hidden_by_a_cache():
    with store() as (objects, root):
        reference = objects.stage(b"fresh read is required")
        assert objects.read(reference) == b"fresh read is required"
        target = object_path(root, reference.manifest_sha256)
        original = target.read_bytes()
        target.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_HASH_MISMATCH")
        assert target.read_bytes() != original


def test_missing_manifest_refuses_without_creating_a_replacement():
    with store() as (objects, root):
        reference = objects.stage(b"missing manifest")
        target = object_path(root, reference.manifest_sha256)
        target.unlink()
        before = files(root)
        refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_MISSING")
        assert files(root) == before and not target.exists()


def test_missing_or_corrupt_chunk_refuses_after_an_earlier_successful_read():
    for missing in (True, False):
        with store() as (objects, root):
            raw = b"a" * 256 + b"b" * 25
            reference = objects.stage(raw)
            assert objects.read(reference) == raw
            target = object_path(root, manifest(root, reference)["chunks"][0]["sha256"])
            if missing:
                target.unlink()
                refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_MISSING")
            else:
                target.write_bytes(b"z" * 256)
                refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_HASH_MISMATCH")


def test_corrupt_existing_chunk_is_never_overwritten_by_restaging():
    with store() as (objects, root):
        raw = b"existing chunk must remain forensic evidence"
        reference = objects.stage(raw)
        target = object_path(root, manifest(root, reference)["chunks"][0]["sha256"])
        damaged = b"!" * len(raw)
        target.write_bytes(damaged)
        before = files(root)
        refused(lambda: objects.stage(raw), "EVIDENCE_OBJECT_HASH_MISMATCH")
        assert target.read_bytes() == damaged and files(root) == before


def test_rehashed_manifest_rejects_bad_lengths_order_fields_duplicate_keys_and_paths():
    with store() as (objects, root):
        reference = objects.stage(b"a" * 256 + b"b" * 256 + b"c" * 13)
        original = manifest(root, reference)
        changes = (
            lambda value: value.update(extra="unrecognized"),
            lambda value: value.update(payload_bytes=value["payload_bytes"] + 1),
            lambda value: value.update(chunk_bytes=value["chunk_bytes"] + 1),
            lambda value: value["chunks"][0].update(bytes=255),
            lambda value: value["chunks"][0].update(index=True),
            lambda value: value["chunks"][0].update(path="../outside"),
            lambda value: value["chunks"][0].update(sha256="../outside"),
            lambda value: value["chunks"].reverse(),
            lambda value: value["chunks"].pop(),
        )
        for change in changes:
            value = json.loads(json.dumps(original))
            change(value)
            altered = forged_manifest(root, reference, value)
            refused(lambda: objects.read(altered), "EVIDENCE_OBJECT_MANIFEST_INVALID")
        raw = E._canonical(original)
        duplicate = b'{"schema":1,' + raw[1:]
        altered = forged_manifest(root, reference, duplicate)
        refused(lambda: objects.read(altered), "EVIDENCE_OBJECT_MANIFEST_INVALID")
        # Reordering hashes while keeping the descriptor indexes valid cannot manufacture another payload.
        value = json.loads(json.dumps(original))
        value["chunks"][0]["sha256"], value["chunks"][1]["sha256"] = (
            value["chunks"][1]["sha256"], value["chunks"][0]["sha256"])
        altered = forged_manifest(root, reference, value)
        refused(lambda: objects.read(altered), "EVIDENCE_OBJECT_HASH_MISMATCH")


def test_fsync_failure_returns_no_reference_and_does_not_adopt_partial_objects():
    with store() as (objects, root):
        accepted = []
        real_fsync = E.os.fsync

        def fail_file_flush(descriptor):
            if stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("injected evidence-file flush failure")
            return real_fsync(descriptor)

        with patch.object(E.os, "fsync", side_effect=fail_file_flush):
            refused(lambda: accepted.append(objects.stage(b"not durable")), "EVIDENCE_OBJECT_IO_REFUSED",
                    "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert accepted == []
        assert list((root / "objects").glob("[0-9a-f]" * 64 + ".blob")) == []
        assert (root / "objects" / "pending.blob").exists()
        before = files(root)
        refused(lambda: objects.stage(b"not durable"), "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert files(root) == before


def test_failed_new_stage_preserves_readability_of_an_existing_verified_reference():
    with store() as (objects, root):
        old_raw = b"existing evidence remains valid"
        old_reference = objects.stage(old_raw)
        old_files = files(root)
        accepted = []
        real_fsync = E.os.fsync

        def fail_file_flush(descriptor):
            if stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("injected new evidence-file flush failure")
            return real_fsync(descriptor)

        with patch.object(E.os, "fsync", side_effect=fail_file_flush):
            refused(lambda: accepted.append(objects.stage(b"different uncommitted evidence")),
                    "EVIDENCE_OBJECT_IO_REFUSED", "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert accepted == []
        interrupted_files = files(root)
        assert (root / "objects" / "pending.blob").exists()
        assert all(interrupted_files[name] == data for name, data in old_files.items())
        assert objects.read(old_reference) == old_raw
        assert E.EvidenceObjectStore(root=root, limits=limits()).read(old_reference) == old_raw
        refused(lambda: objects.stage(b"different uncommitted evidence"), "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert files(root) == interrupted_files
        old_chunk = object_path(root, manifest(root, old_reference)["chunks"][0]["sha256"])
        old_chunk.write_bytes(b"!" * len(old_raw))
        refused(lambda: objects.read(old_reference), "EVIDENCE_OBJECT_HASH_MISMATCH")
        assert (root / "objects" / "pending.blob").read_bytes() == interrupted_files["objects/pending.blob"]


def test_failure_after_chunk_publication_has_no_accepted_reference_or_implicit_resume():
    with store() as (objects, root):
        accepted, calls = [], []
        real_open = E.os.open

        def fail_manifest(path, flags, *args, **kwargs):
            name = Path(path).name
            if flags & os.O_EXCL and len(name) == 69 and name.endswith(".blob"):
                calls.append(name)
                if len(calls) == 3:
                    raise OSError("injected manifest exclusive-create failure")
            return real_open(path, flags, *args, **kwargs)

        raw = b"a" * 256 + b"b" * 256
        with patch.object(E.os, "open", side_effect=fail_manifest):
            refused(lambda: accepted.append(objects.stage(raw)), "EVIDENCE_OBJECT_IO_REFUSED",
                    "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert accepted == [] and len(calls) == 3
        assert len(list((root / "objects").glob("[0-9a-f]" * 64 + ".blob"))) == 2
        before = files(root)
        refused(lambda: objects.stage(raw), "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert files(root) == before


def test_retry_after_final_directory_sync_failure_flushes_reused_objects_before_returning_a_reference():
    """Inject the abstract directory-sync boundary; this is not a Windows power-loss durability claim."""
    with store() as (objects, root):
        accepted, object_syncs = [], []
        real_sync = E.EvidenceObjectStore._sync_directory
        raw = b"a" * 256 + b"b" * 25

        def fail_manifest_sync(self, path):
            if path == root / "objects":
                object_syncs.append(path)
                if len(object_syncs) == 3:
                    assert not (path / "pending.blob").exists()
                    raise OSError("injected final manifest directory sync failure")
            return real_sync(self, path)

        with patch.object(E.EvidenceObjectStore, "_sync_directory", fail_manifest_sync):
            refused(lambda: accepted.append(objects.stage(raw)), "EVIDENCE_OBJECT_IO_REFUSED")
        assert accepted == [] and len(object_syncs) == 3
        assert not (root / "objects" / "pending.blob").exists()
        assert len(list((root / "objects").glob("[0-9a-f]" * 64 + ".blob"))) == 3
        before = files(root)
        object_syncs.clear()

        def fail_retry_sync(self, path):
            if path == root / "objects":
                object_syncs.append(path)
                raise OSError("injected directory sync failure on object reuse")
            return real_sync(self, path)

        with patch.object(E.EvidenceObjectStore, "_sync_directory", fail_retry_sync):
            refused(lambda: accepted.append(objects.stage(raw)), "EVIDENCE_OBJECT_IO_REFUSED")
        assert accepted == [] and object_syncs == [root / "objects"]
        assert files(root) == before
        object_syncs.clear()

        def observe_successful_sync(self, path):
            if path == root / "objects":
                object_syncs.append(path)
            return real_sync(self, path)

        with patch.object(E.EvidenceObjectStore, "_sync_directory", observe_successful_sync):
            reference = objects.stage(raw)
        assert object_syncs == [root / "objects"]
        assert objects.read(reference) == raw and files(root) == before


def test_publication_remains_link_free_during_final_creation_flush_and_pending_removal():
    """Run the shared link scanner at publication boundaries, without a cached clean verdict."""
    with store() as (objects, root):
        events = []
        real_open, real_fsync, real_unlink = E.os.open, E.os.fsync, E.os.unlink

        def scan(event):
            isolation._LINK_SCAN.clear()
            isolation.scan_links(root)
            blobs = list((root / "objects").glob("*.blob"))
            assert all(os.lstat(path).st_nlink == 1 for path in blobs)
            events.append((event, any(path.name != "pending.blob" for path in blobs),
                           (root / "objects" / "pending.blob").exists()))

        def observed_open(path, flags, *args, **kwargs):
            descriptor = real_open(path, flags, *args, **kwargs)
            if flags & os.O_EXCL and Path(path).suffix == ".blob":
                scan("exclusive-create")
            return descriptor

        def observed_fsync(descriptor):
            scan("before-fsync")
            result = real_fsync(descriptor)
            scan("after-fsync")
            return result

        def observed_unlink(path, *args, **kwargs):
            scan("before-unlink")
            result = real_unlink(path, *args, **kwargs)
            scan("after-unlink")
            return result

        with patch.dict(isolation._LINK_SCAN, clear=True), \
                patch.object(E.os, "open", side_effect=observed_open), \
                patch.object(E.os, "fsync", side_effect=observed_fsync), \
                patch.object(E.os, "unlink", side_effect=observed_unlink), \
                patch.object(E.os, "link", side_effect=AssertionError("publication must not create hardlinks")), \
                patch.object(E.os, "rename", side_effect=AssertionError("publication must not rename over files")), \
                patch.object(E.os, "replace", side_effect=AssertionError("publication must not replace files")):
            raw = b"a" * 256 + b"b" * 25
            reference = objects.stage(raw)
            assert objects.read(reference) == raw
        assert ("exclusive-create", True, True) in events
        assert ("after-fsync", True, True) in events
        assert ("after-unlink", True, False) in events


def test_final_copy_write_or_flush_failure_preserves_forensic_files_without_a_reference():
    for phase in ("write", "fsync"):
        with store() as (objects, root):
            accepted, final_fd = [], [None]
            real_open, real_fdopen, real_fsync = E.os.open, E.os.fdopen, E.os.fsync

            def track_final(path, flags, *args, **kwargs):
                descriptor = real_open(path, flags, *args, **kwargs)
                name = Path(path).name
                if flags & os.O_EXCL and len(name) == 69 and name.endswith(".blob"):
                    final_fd[0] = descriptor
                return descriptor

            class InterruptedCopy:
                def __init__(self, handle):
                    self.handle = handle

                def __enter__(self):
                    self.handle.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.handle.__exit__(*args)

                def __getattr__(self, name):
                    return getattr(self.handle, name)

                def write(self, raw):
                    self.handle.write(raw[:len(raw) // 2])
                    self.handle.flush()
                    raise OSError("injected partial final copy")

            def interrupted_fdopen(descriptor, *args, **kwargs):
                handle = real_fdopen(descriptor, *args, **kwargs)
                return InterruptedCopy(handle) if phase == "write" and descriptor == final_fd[0] else handle

            def interrupted_fsync(descriptor):
                if phase == "fsync" and descriptor == final_fd[0]:
                    raise OSError("injected final file flush failure")
                return real_fsync(descriptor)

            raw = b"complete payload bytes need a durable final object"
            with patch.object(E.os, "open", side_effect=track_final), \
                    patch.object(E.os, "fdopen", side_effect=interrupted_fdopen), \
                    patch.object(E.os, "fsync", side_effect=interrupted_fsync):
                refused(lambda: accepted.append(objects.stage(raw)), "EVIDENCE_OBJECT_IO_REFUSED")
            assert accepted == [] and final_fd[0] is not None
            assert (root / "objects" / "pending.blob").read_bytes() == raw
            candidates = list((root / "objects").glob("[0-9a-f]" * 64 + ".blob"))
            assert len(candidates) == 1
            assert candidates[0].read_bytes() == (raw[:len(raw) // 2] if phase == "write" else raw)
            before = files(root)
            refused(lambda: objects.stage(raw), "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
            assert files(root) == before


def test_symlinked_object_is_refused_even_when_target_bytes_match():
    with store() as (objects, root):
        reference = objects.stage(b"symlink is not an evidence object")
        target = object_path(root, reference.manifest_sha256)
        external = root.parent / "external-manifest"
        external.write_bytes(target.read_bytes())
        target.unlink()
        try:
            target.symlink_to(external)
        except (NotImplementedError, OSError):
            raise NotRun("REFDATA: symlink creation unavailable on this platform or volume") from None
        refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_PATH_REFUSED")


def test_hardlinked_object_is_refused_even_when_content_is_unchanged():
    with store() as (objects, root):
        reference = objects.stage(b"hardlinks can mutate an object through an alias")
        target = object_path(root, reference.manifest_sha256)
        alias = root.parent / "hardlink-alias"
        try:
            os.link(target, alias)
        except (NotImplementedError, OSError):
            raise NotRun("REFDATA: hardlink creation unavailable on this platform or volume") from None
        refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_PATH_REFUSED")


def test_unknown_opened_file_identity_refuses_even_when_path_and_handle_both_report_zero():
    with store() as (objects, root):
        reference = objects.stage(b"identity must be established")
        before = files(root)
        real_lstat, real_fstat = E.os.lstat, E.os.fstat

        def without_inode(info):
            if not stat.S_ISREG(info.st_mode):
                return info
            return SimpleNamespace(**({name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
                                      | {"st_ino": 0}))

        with patch.object(E.os, "lstat", side_effect=lambda *args, **kwargs: without_inode(real_lstat(*args, **kwargs))), \
                patch.object(E.os, "fstat", side_effect=lambda *args, **kwargs: without_inode(real_fstat(*args, **kwargs))):
            refused(lambda: objects.read(reference), "EVIDENCE_OBJECT_PATH_REFUSED")
        assert files(root) == before


def test_symlinked_store_root_cannot_redirect_writes_outside_the_explicit_root():
    with tempfile.TemporaryDirectory(prefix="tradegen_evidence_path_") as temporary:
        base = Path(temporary)
        external = base / "external"
        external.mkdir()
        alias = base / "alias"
        try:
            alias.symlink_to(external, target_is_directory=True)
        except (NotImplementedError, OSError):
            raise NotRun("REFDATA: directory symlink creation unavailable on this platform or volume") from None
        refused(lambda: E.EvidenceObjectStore(root=alias, limits=limits()).stage(b"redirected"),
                "EVIDENCE_OBJECT_PATH_REFUSED")
        assert list(external.iterdir()) == []
