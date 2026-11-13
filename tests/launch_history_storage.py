"""History v3 policy, context binding and finite storage admission over synthetic temporary data.

Codec fixtures deliberately do not claim account/quote/chooser validity: the
LiveHistory integration owns those semantic checks and independent-head commits.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

from execution_launch import evidence_objects as E
from execution_launch import history_storage as H
from tests.notrun import NotRun


def refused(call, *codes):
    try:
        call()
    except (H.HistoryStorageError, E.EvidenceObjectError) as exc:
        assert str(exc) in codes, (str(exc), codes)
        return
    raise AssertionError("expected history storage refusal: " + repr(codes))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def policy(**changes):
    values = dict(schema_version=1, history_version=3,
                  object_limits=E.ObjectLimits(chunk_bytes=128, max_payload_bytes=2048,
                                               max_chunks=16, max_manifest_bytes=4096),
                  max_window_bytes=1024 * 1024, max_window_objects=256, max_journal_bytes=1024 * 1024)
    return H.HistoryStoragePolicy(**(values | changes))


def context(**changes):
    values = dict(window_digest="1" * 64, driver_identity_digest="2" * 64, index=2,
                  sampled_at=datetime(2031, 1, 1, 0, 2, 1, 123456, timezone.utc))
    return H.SlotContext(**(values | changes))


def slot():
    return {"index": 2, "trade_symbol": "KRW-BTC", "tick_size": "1",
            "receipt": "unavailable", "anchor": {}, "holdings": [],
            "universe": {}, "decision": {}}


def budget(**changes):
    return E.StoreBudget(**(dict(max_bytes=1024 * 1024, max_objects=256) | changes))


@contextmanager
def object_store(*, initialize=True):
    with tempfile.TemporaryDirectory(prefix="tradegen_history_storage_") as temporary:
        root = Path(temporary) / "objects-for-window"
        objects = E.EvidenceObjectStore(root=root, limits=policy().object_limits)
        if initialize:
            objects.initialize()
        yield objects, root


def files(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def add_orphan(root, raw):
    sha = E._object_digest("chunk", raw)
    path = root / "objects" / (sha + ".blob")
    path.write_bytes(raw)
    return path


def test_policy_roundtrip_hash_and_object_policy_are_distinct():
    value = policy()
    raw = H.policy_bytes(value)
    assert H.parse_policy(raw) == value
    assert canonical(json.loads(raw)) == raw
    digest = H.policy_digest(value)
    assert len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)
    assert digest != value.object_limits.policy_sha256
    variants = (replace(value, max_window_bytes=value.max_window_bytes + 1),
                replace(value, max_window_objects=value.max_window_objects + 1),
                replace(value, max_journal_bytes=value.max_journal_bytes + 1),
                replace(value, object_limits=replace(value.object_limits, chunk_bytes=64)))
    assert len({digest, *(H.policy_digest(other) for other in variants)}) == len(variants) + 1


def test_policy_strict_fields_revisions_and_positive_finite_limits():
    raw = H.policy_bytes(policy())
    original = json.loads(raw)
    variants = [original | {"unexpected": "ignored-policy-field"},
                original | {"schema_version": True}, original | {"schema_version": 2},
                original | {"history_version": 2}, original | {"object_schema": 2},
                original | {"object_schema": True}, original | {"max_window_bytes": 0},
                original | {"max_window_objects": -1}, original | {"max_journal_bytes": True},
                original | {"object_limits": None},
                original | {"object_limits": original["object_limits"] | {"extra": 1}}]
    missing = dict(original)
    missing.pop("max_window_objects")
    variants.append(missing)
    for value in variants:
        refused(lambda value=value: H.parse_policy(canonical(value)), "HISTORY_STORAGE_POLICY_INVALID")
    duplicate = b'{"schema_version":1,' + raw[1:]
    refused(lambda: H.parse_policy(duplicate), "HISTORY_STORAGE_POLICY_INVALID")
    refused(lambda: H.parse_policy(raw + b"\n"), "HISTORY_STORAGE_POLICY_INVALID")
    refused(lambda: H.parse_policy(b'{"max_window_bytes":NaN}'), "HISTORY_STORAGE_POLICY_INVALID")


def test_slot_wrapper_preserves_exact_logical_values_without_claiming_execution_authority():
    original = slot()
    original["holdings"] = [["KRW-FAKE", "1.00000000", "100.00"]]
    raw = H.encode_slot_payload(original, context=context(), policy=policy())
    assert H.decode_slot_payload(raw, context=context(), policy=policy()) == original
    body = json.loads(raw)
    assert set(body) == {"schema", "window_digest", "driver_identity_digest", "index", "sampled_at", "slot"}
    assert body["slot"] == original
    assert body["sampled_at"] == "2031-01-01T00:02:01.123456Z"
    assert canonical(body) == raw
    # No reference/manifest identity means an encoded wrapper alone grants nothing.
    assert "payload_ref" not in body and "approved" not in body


def test_wrapper_is_bound_to_window_driver_slot_and_sampling_time():
    expected = context()
    raw = H.encode_slot_payload(slot(), context=expected, policy=policy())
    other_contexts = (replace(expected, window_digest="3" * 64),
                      replace(expected, driver_identity_digest="4" * 64),
                      replace(expected, index=expected.index + 1),
                      replace(expected, sampled_at=expected.sampled_at + timedelta(microseconds=1)))
    for different in other_contexts:
        refused(lambda different=different: H.decode_slot_payload(raw, context=different, policy=policy()),
                "HISTORY_STORAGE_CONTEXT_MISMATCH")


def test_wrapper_and_nested_slot_have_closed_keys_and_matching_indexes():
    raw = H.encode_slot_payload(slot(), context=context(), policy=policy())
    original = json.loads(raw)
    changes = (
        lambda value: value.update(extra="ignored"),
        lambda value: value.pop("sampled_at"),
        lambda value: value.update(schema=True),
        lambda value: value.update(schema=2),
        lambda value: value.update(index=True),
        lambda value: value["slot"].update(index=3),
        lambda value: value["slot"].update(extra="not-an-existing-slot-field"),
        lambda value: value["slot"].pop("holdings"),
        lambda value: value.update(slot=[]),
    )
    for change in changes:
        value = json.loads(json.dumps(original))
        change(value)
        refused(lambda value=value: H.decode_slot_payload(canonical(value), context=context(), policy=policy()),
                "HISTORY_STORAGE_PAYLOAD_INVALID", "HISTORY_STORAGE_CONTEXT_MISMATCH")
    duplicate = b'{"schema":1,' + raw[1:]
    refused(lambda: H.decode_slot_payload(duplicate, context=context(), policy=policy()),
            "HISTORY_STORAGE_PAYLOAD_INVALID")


def test_wrapper_rejects_noncanonical_time_and_index_coercion():
    raw = H.encode_slot_payload(slot(), context=context(), policy=policy())
    for changed in ("2031-01-01T00:02:01.123456+00:00", "2031-01-01T00:02:01.123456", "yesterday"):
        value = json.loads(raw)
        value["sampled_at"] = changed
        refused(lambda value=value: H.decode_slot_payload(canonical(value), context=context(), policy=policy()),
                "HISTORY_STORAGE_PAYLOAD_INVALID", "HISTORY_STORAGE_CONTEXT_MISMATCH")
    original = slot()
    original["index"] = True
    refused(lambda: H.encode_slot_payload(original, context=context(), policy=policy()),
            "HISTORY_STORAGE_PAYLOAD_INVALID", "HISTORY_STORAGE_CONTEXT_MISMATCH")


def test_wrapper_payload_limit_is_checked_at_exact_encoded_byte_boundary():
    raw = H.encode_slot_payload(slot(), context=context(), policy=policy())
    for limit in (len(raw) - 1, len(raw), len(raw) + 1):
        configured = policy(object_limits=replace(policy().object_limits, max_payload_bytes=limit))
        if limit < len(raw):
            refused(lambda: H.encode_slot_payload(slot(), context=context(), policy=configured),
                    "HISTORY_STORAGE_LIMIT_EXCEEDED")
            refused(lambda: H.decode_slot_payload(raw, context=context(), policy=configured),
                    "HISTORY_STORAGE_LIMIT_EXCEEDED", "HISTORY_STORAGE_PAYLOAD_INVALID")
        else:
            assert H.encode_slot_payload(slot(), context=context(), policy=configured) == raw
            assert H.decode_slot_payload(raw, context=context(), policy=configured) == slot()


def test_wrapper_does_not_coerce_float_bytes_or_nonfinite_evidence_into_numbers():
    for unsupported in (1.25, float("nan"), float("inf"), b"raw-bytes", ("tuple",)):
        original = slot()
        original["anchor"] = {"untrusted": unsupported}
        refused(lambda: H.encode_slot_payload(original, context=context(), policy=policy()),
                "HISTORY_STORAGE_PAYLOAD_INVALID")


def test_deeply_nested_payload_is_a_fixed_refusal_not_an_uncontained_recursion_error():
    original = slot()
    nested = []
    for _ in range(1500):
        nested = [nested]
    original["anchor"] = nested
    refused(lambda: H.encode_slot_payload(original, context=context(), policy=policy()),
            "HISTORY_STORAGE_PAYLOAD_INVALID", "HISTORY_STORAGE_LIMIT_EXCEEDED")


def test_mutation_between_prevalidation_and_serialization_cannot_issue_unreplayable_bytes():
    mutations = (
        (lambda body: body["slot"].update(anchor={"changed": 1.25}), "HISTORY_STORAGE_PAYLOAD_INVALID"),
        (lambda body: body["slot"].update(index=3), "HISTORY_STORAGE_CONTEXT_MISMATCH"),
        (lambda body: body["slot"].update(extra="after validation"), "HISTORY_STORAGE_PAYLOAD_INVALID"),
    )
    for mutate, expected in mutations:
        original = slot()
        real_canonical, changed, accepted = H._canonical, [], []

        def change_at_serialization(body):
            # A deterministic schedule for a caller changing its dict after the
            # final primitive check; no timing-dependent test thread is needed.
            if not changed and type(body) is dict and "slot" in body:
                mutate(body)
                changed.append(True)
            return real_canonical(body)

        with patch.object(H, "_canonical", side_effect=change_at_serialization):
            refused(lambda: accepted.append(H.encode_slot_payload(original, context=context(), policy=policy())),
                    expected)
        assert changed == [True] and accepted == []


def test_wrapper_envelope_depth_is_included_and_preserves_limit_diagnostic():
    for nesting in (H.MAX_CODEC_DEPTH - 2, H.MAX_CODEC_DEPTH - 1):
        original = slot()
        nested = []
        for _ in range(nesting):
            nested = [nested]
        original["anchor"] = nested
        # Both slot bodies fit by themselves; the envelope adds one level.
        H._primitive(original)
        if nesting == H.MAX_CODEC_DEPTH - 2:
            raw = H.encode_slot_payload(original, context=context(), policy=policy())
            assert H.decode_slot_payload(raw, context=context(), policy=policy()) == original
        else:
            refused(lambda: H.encode_slot_payload(original, context=context(), policy=policy()),
                    "HISTORY_STORAGE_LIMIT_EXCEEDED")


def test_policy_budget_and_journal_newline_bytes_obey_exact_boundaries():
    configured = policy(max_window_bytes=8192, max_window_objects=9, max_journal_bytes=64)
    assert H.policy_budget(configured) == E.StoreBudget(max_bytes=8192, max_objects=9)
    for row_bytes in (31, 32):
        assert H.admit_journal_row(configured, journal_bytes=32, next_row_bytes=row_bytes) == 32 + row_bytes
    # Caller supplies the serialized row including its newline: 32 bytes + 1 is refused.
    refused(lambda: H.admit_journal_row(configured, journal_bytes=32, next_row_bytes=33),
            "HISTORY_STORAGE_LIMIT_EXCEEDED")
    for existing, added in ((True, 1), (-1, 1), (0, True), (0, 0), (0, -1)):
        refused(lambda existing=existing, added=added: H.admit_journal_row(configured,
                journal_bytes=existing, next_row_bytes=added), "HISTORY_STORAGE_LIMIT_EXCEEDED")


def test_preview_is_pure_and_describes_exact_unique_objects_and_reference():
    raw = b"a" * 128 + b"a" * 128 + b"b"
    with object_store(initialize=False) as (objects, root):
        preview = objects.preview(raw)
        assert preview == E.preview_payload(raw, limits=policy().object_limits)
        assert not root.exists()
        assert len(preview.objects) == 3  # repeated first chunk is one object, plus last chunk and manifest
        assert [item.kind for item in preview.objects] == ["chunk", "chunk", "manifest"]
        assert [item.byte_count for item in preview.objects[:2]] == [128, 1]
        assert preview.objects[-1].sha256 == preview.reference.manifest_sha256
        objects.initialize()
        reference = objects.stage(raw, budget=budget())
        assert reference == preview.reference and objects.read(reference) == raw


def test_empty_inventory_counts_lock_and_orphans_without_trusting_them_as_references():
    with object_store() as (objects, root):
        initial = objects.inventory(budget=budget())
        assert initial.object_count == 1
        assert initial.byte_count == (root / "objects.lock").stat().st_size
        assert initial.pending is False
        orphan = b"unreferenced original bytes"
        add_orphan(root, orphan)
        measured = objects.inventory(budget=budget())
        assert measured.object_count == initial.object_count + 1
        assert measured.byte_count == initial.byte_count + len(orphan)
        assert len(measured.entries) == measured.object_count
        assert measured.pending is False


def test_physical_byte_and_object_peak_limits_include_temporary_copy_at_boundaries():
    raw = b"a" * 128 + b"b" * 128 + b"c"
    for dimension in ("bytes", "objects"):
        for offset in (-1, 0, 1):
            with object_store() as (objects, root):
                preview = objects.preview(raw)
                inventory = objects.inventory(budget=budget())
                # In this fixture the manifest is published last and is larger than every chunk.
                assert preview.objects[-1].byte_count > 128
                peak_bytes = inventory.byte_count + len(raw) + 2 * preview.objects[-1].byte_count
                peak_objects = inventory.object_count + len(preview.objects) + 1
                bound = budget(max_bytes=peak_bytes + offset) if dimension == "bytes" else budget(
                    max_objects=peak_objects + offset)
                before = files(root)
                if offset < 0:
                    refused(lambda: objects.stage(raw, budget=bound), "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
                    assert files(root) == before
                else:
                    reference = objects.stage(raw, budget=bound)
                    assert objects.read(reference) == raw


def test_impossible_empty_store_admission_creates_no_files_or_infrastructure():
    for bound in (budget(max_bytes=1), budget(max_objects=1)):
        with object_store(initialize=False) as (objects, root):
            refused(lambda: objects.stage(b"cannot fit", budget=bound), "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
            assert not root.exists()


def test_feasible_budget_does_not_silently_initialize_an_unbound_store():
    with object_store(initialize=False) as (objects, root):
        refused(lambda: objects.stage(b"feasible but not initialized", budget=budget()), "EVIDENCE_OBJECT_MISSING")
        assert not root.exists()


def test_nonfinite_or_coerced_budget_configuration_is_rejected_before_storage_creation():
    for changes in ({"max_bytes": True}, {"max_bytes": 0}, {"max_bytes": -1},
                    {"max_objects": True}, {"max_objects": 0}, {"max_objects": -1},
                    {"max_bytes": 1 << 80}, {"max_objects": 1 << 80}):
        with object_store(initialize=False) as (objects, root):
            refused(lambda: objects.stage(b"invalid quota", budget=budget(**changes)),
                    "EVIDENCE_OBJECT_INPUT_INVALID")
            assert not root.exists()


def test_deduplicated_retry_needs_no_temporary_budget_and_keeps_orphan_usage():
    raw = b"a" * 128 + b"b"
    with object_store() as (objects, root):
        reference = objects.stage(raw, budget=budget())
        add_orphan(root, b"retained orphan counts against this window")
        measured = objects.inventory(budget=budget())
        exact = budget(max_bytes=measured.byte_count, max_objects=measured.object_count)
        before = files(root)
        assert objects.stage(raw, budget=exact) == reference
        assert files(root) == before and objects.read(reference) == raw
        refused(lambda: objects.stage(raw, budget=replace(exact, max_bytes=exact.max_bytes - 1)),
                "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        refused(lambda: objects.stage(raw, budget=replace(exact, max_objects=exact.max_objects - 1)),
                "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        assert files(root) == before


def test_pending_data_is_in_physical_inventory_and_blocks_new_stage_without_blocking_old_read():
    with object_store() as (objects, root):
        raw = b"existing committed-reference bytes"
        reference = objects.stage(raw, budget=budget())
        initial = objects.inventory(budget=budget())
        pending = root / "objects" / "pending.blob"
        pending.write_bytes(b"interrupted uncommitted payload")
        measured = objects.inventory(budget=budget())
        assert measured.pending is True
        assert measured.object_count == initial.object_count + 1
        assert measured.byte_count == initial.byte_count + pending.stat().st_size
        before = files(root)
        refused(lambda: objects.stage(b"new data", budget=budget()), "EVIDENCE_OBJECT_INTERRUPTED_WRITE")
        assert objects.read(reference) == raw
        assert files(root) == before


def test_inventory_stops_at_one_entry_over_count_limit_instead_of_listing_the_whole_store():
    with object_store() as (objects, root):
        for raw in (b"orphan-one", b"orphan-two", b"orphan-three"):
            add_orphan(root, raw)
        before = files(root)
        real_scandir, read_entries = E.os.scandir, []

        class BoundedIterator:
            def __init__(self, iterator):
                self.iterator = iterator

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

            def close(self):
                self.iterator.close()

            def __iter__(self):
                return self

            def __next__(self):
                assert len(read_entries) < 2, "inventory scanned beyond the first over-limit entry"
                entry = next(self.iterator)
                read_entries.append(entry.name)
                return entry

        def bounded_scandir(path):
            iterator = real_scandir(path)
            return BoundedIterator(iterator) if Path(path) == root / "objects" else iterator

        with patch.object(E.os, "scandir", side_effect=bounded_scandir):
            refused(lambda: objects.inventory(budget=budget(max_objects=2)), "EVIDENCE_OBJECT_LIMIT_EXCEEDED")
        assert len(read_entries) == 2  # lock plus two object entries: first over the limit
        assert files(root) == before


def test_inventory_rejects_unknown_files_and_nested_directories_without_cleanup():
    for kind in ("file", "directory"):
        with object_store() as (objects, root):
            suspicious = root / "objects" / ("unrecognized.txt" if kind == "file" else "nested")
            if kind == "file":
                suspicious.write_bytes(b"must not be silently ignored")
            else:
                suspicious.mkdir()
            before = files(root)
            refused(lambda: objects.inventory(budget=budget()), "EVIDENCE_OBJECT_PATH_REFUSED")
            assert files(root) == before and suspicious.exists()


def test_inventory_does_not_count_symlinked_or_multilinked_orphans_as_safe_storage():
    for kind in ("symlink", "hardlink"):
        with object_store() as (objects, root):
            target = add_orphan(root, b"orphan content")
            outside = root.parent / "outside-evidence"
            try:
                if kind == "symlink":
                    outside.write_bytes(target.read_bytes())
                    target.unlink()
                    target.symlink_to(outside)
                else:
                    os.link(target, outside)
            except (NotImplementedError, OSError):
                raise NotRun("REFDATA: evidence link fixture cannot be created on this platform or volume") from None
            refused(lambda: objects.inventory(budget=budget()), "EVIDENCE_OBJECT_PATH_REFUSED")
            assert outside.read_bytes() == b"orphan content"


def test_two_budgeted_writers_cannot_each_reserve_the_same_remaining_window_space():
    with object_store() as (objects, root):
        other = E.EvidenceObjectStore(root=root, limits=policy().object_limits)
        ready = threading.Barrier(2)
        outcomes = []

        def writer(store_instance, raw):
            try:
                ready.wait(timeout=5)
                result = store_instance.stage(raw, budget=budget(max_objects=4))
                outcomes.append((raw, result, None))
            except Exception as exc:
                outcomes.append((raw, None, exc))

        threads = [threading.Thread(target=writer, args=(store_instance, raw), daemon=True)
                   for store_instance, raw in ((objects, b"a" * 64), (other, b"b" * 64))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        assert not any(thread.is_alive() for thread in threads), "budget staging did not finish"
        assert len(outcomes) == 2
        accepted = [(raw, result) for raw, result, error in outcomes if error is None]
        rejected = [error for _, _, error in outcomes if error is not None]
        assert len(accepted) == len(rejected) == 1
        assert type(rejected[0]) is E.EvidenceObjectError
        assert str(rejected[0]) == "EVIDENCE_OBJECT_LIMIT_EXCEEDED"
        assert objects.read(accepted[0][1]) == accepted[0][0]
        assert objects.inventory(budget=budget(max_objects=4)).object_count == 3
