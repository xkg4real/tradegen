"""Durability, isolation, crash and lock tests using only temporary control state."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import threading

from core import isolation
from execution_control.store import Journal, JournalError, Transaction

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)


@contextmanager
def _home():
    prior = os.environ.get("TRADEGEN_HOME")
    with tempfile.TemporaryDirectory(prefix="tradegen_control_") as name:
        os.environ["TRADEGEN_HOME"] = name
        isolation._LINK_SCAN.clear()
        try:
            yield Path(name), Journal()
        finally:
            if prior is None:
                os.environ.pop("TRADEGEN_HOME", None)
            else:
                os.environ["TRADEGEN_HOME"] = prior
            isolation._LINK_SCAN.clear()


def _events(journal):
    with journal.transaction() as tx:
        return tx.events


def _raises(call):
    try:
        call()
    except JournalError:
        return
    raise AssertionError("expected journal refusal")


def _process_writer(base, channel):
    os.environ["TRADEGEN_HOME"] = base
    journal = Journal()
    channel.send("ready")
    with journal.transaction() as tx:
        tx.append("reserved", {"client_id": "child"}, now=NOW)
    channel.send("written")
    channel.close()


def test_journal_restarts_with_exact_hash_chain_and_detached_events():
    with _home() as (home, journal):
        assert not (home / "execution-control").exists()
        payload = {"client_id": "first", "nested": {"amount": "12.5", "flags": [True, None]}}
        with journal.transaction() as tx:
            first = tx.append("reserved", payload, now=NOW)
            payload["nested"]["amount"] = "1000"
            first["data"]["nested"]["amount"] = "2000"
            copied = tx.events
            copied[0]["data"]["nested"]["flags"].append("changed")
            second = tx.append("dispatching", {"client_id": "first"}, now=NOW + timedelta(seconds=1))
        rows = _events(Journal())
        assert rows[0]["data"]["nested"] == {"amount": "12.5", "flags": [True, None]}
        assert second["prev_sha256"] == rows[0]["row_sha256"] and second["seq"] == 2
        assert rows[1] == second
        _raises(lambda: tx.append("unknown", {}, now=NOW))


def test_invalid_payloads_and_events_never_extend_the_journal():
    with _home() as (_home_path, journal):
        with journal.transaction() as tx:
            for payload in ({"amount": 1.2}, {"amount": Decimal("1")}, {"values": (1, 2)}, {1: "bad"},
                            {"value": 2 ** 80}, {"value": "x" * 4097}):
                _raises(lambda payload=payload: tx.append("reserved", payload, now=NOW))
            _raises(lambda: tx.append("arbitrary", {}, now=NOW))
            _raises(lambda: tx.append("reserved", {}, now=NOW.replace(tzinfo=None)))
            cyclic = {}; cyclic["again"] = cyclic
            _raises(lambda: tx.append("reserved", cyclic, now=NOW))
            assert tx.events == ()
        assert _events(journal) == ()


def test_torn_tail_is_preserved_and_blocks_replay():
    with _home() as (home, journal):
        with journal.transaction() as tx:
            tx.append("reserved", {"client_id": "first"}, now=NOW)
        path = home / "execution-control/journal.jsonl"
        broken = path.read_bytes() + b'{"incomplete":'
        path.write_bytes(broken)
        _raises(lambda: _events(journal))
        assert path.read_bytes() == broken


def test_truncated_valid_tail_is_detected_by_checkpoint():
    with _home() as (home, journal):
        with journal.transaction() as tx:
            tx.append("reserved", {"client_id": "first"}, now=NOW)
            tx.append("dispatching", {"client_id": "first"}, now=NOW)
        path = home / "execution-control/journal.jsonl"
        shortened = path.read_bytes().splitlines(keepends=True)[0]
        path.write_bytes(shortened)
        _raises(lambda: _events(Journal()))
        assert path.read_bytes() == shortened


def test_missing_anchor_or_journal_does_not_reset_state():
    for missing in ("checkpoint.json", "journal.jsonl"):
        with _home() as (home, journal):
            with journal.transaction() as tx:
                tx.append("reserved", {}, now=NOW)
            path = home / "execution-control" / missing
            path.unlink()
            _raises(lambda: _events(Journal()))
            assert not path.exists()


def test_changed_data_same_length_and_duplicate_json_keys_are_refused():
    with _home() as (home, journal):
        with journal.transaction() as tx:
            tx.append("reserved", {"n": 1}, now=NOW)
        path = home / "execution-control/journal.jsonl"
        original = path.read_bytes()
        changed = original.replace(b'"n":1', b'"n":2')
        assert changed != original and len(changed) == len(original)
        path.write_bytes(changed)
        _raises(lambda: _events(journal))
        path.write_bytes(original)
        anchor = home / "execution-control/checkpoint.json"
        anchor.write_bytes(anchor.read_bytes().replace(b'"schema":1', b'"schema":1,"schema":1'))
        _raises(lambda: _events(journal))


def test_checkpoint_failure_after_fsync_retains_unknown_tail_and_poisoned_transaction():
    with _home() as (home, journal):
        original = journal._anchor
        with journal.transaction() as tx:
            def fail(*args):
                raise OSError("synthetic durability failure")
            journal._anchor = fail
            try:
                _raises(lambda: tx.append("dispatching", {"client_id": "first"}, now=NOW))
                _raises(lambda: tx.append("rejected", {"client_id": "first"}, now=NOW))
            finally:
                journal._anchor = original
        raw = (home / "execution-control/journal.jsonl").read_bytes()
        assert b'"kind":"dispatching"' in raw
        _raises(lambda: _events(Journal()))
        assert (home / "execution-control/journal.jsonl").read_bytes() == raw


def test_transaction_exception_does_not_rollback_durable_event():
    with _home() as (_home_path, journal):
        try:
            with journal.transaction() as tx:
                tx.append("reserved", {"client_id": "first"}, now=NOW)
                raise ValueError("business refusal")
        except ValueError:
            pass
        else:
            raise AssertionError("caller exception swallowed")
        assert len(_events(journal)) == 1


def test_unissued_nested_and_cross_thread_transactions_cannot_append():
    with _home() as (_home_path, journal):
        _raises(lambda: Transaction(journal, [], 0).append("reserved", {}, now=NOW))
        with journal.transaction() as tx:
            _raises(lambda: _events(journal))
            outcomes = []
            def misuse():
                try:
                    tx.append("reserved", {}, now=NOW)
                except JournalError:
                    outcomes.append("refused")
            thread = threading.Thread(target=misuse)
            thread.start(); thread.join(timeout=3)
            assert not thread.is_alive() and outcomes == ["refused"] and tx.events == ()


def test_threads_cannot_oversubscribe_read_modify_append_capacity():
    with _home() as (_home_path, journal):
        accepted, failed = [], []
        def reserve(client):
            try:
                with journal.transaction() as tx:
                    used = sum(row["data"]["amount"] for row in tx.events)
                    if used + 7 <= 10:
                        tx.append("reserved", {"client_id": client, "amount": 7}, now=NOW)
                        accepted.append(client)
            except Exception as exc:
                failed.append(type(exc).__name__)
        threads = [threading.Thread(target=reserve, args=(str(n),)) for n in range(6)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        assert all(not thread.is_alive() for thread in threads) and not failed
        assert len(accepted) == 1 and len(_events(journal)) == 1


def test_processes_share_the_control_lock():
    with _home() as (home, journal):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_process_writer, args=(str(home), child))
        try:
            with journal.transaction() as tx:
                process.start()
                assert parent.poll(10) and parent.recv() == "ready"
                assert not parent.poll(0.1), "child wrote while parent held the lock"
                tx.append("reserved", {"client_id": "parent"}, now=NOW)
            assert parent.poll(10) and parent.recv() == "written"
            process.join(timeout=10)
            assert process.exitcode == 0
            assert [row["data"]["client_id"] for row in _events(journal)] == ["parent", "child"]
        finally:
            if process.is_alive(): process.terminate(); process.join(timeout=3)
            parent.close(); child.close()


def test_linked_targets_and_paths_outside_state_root_are_refused():
    with _home() as (home, journal):
        with journal.transaction() as tx:
            tx.append("reserved", {}, now=NOW)
        path = home / "execution-control/journal.jsonl"
        original = path.read_bytes()
        os.link(path, home / "second-name")
        _raises(lambda: _events(journal))
        assert path.read_bytes() == original
        _raises(lambda: Journal(home.parent / "outside-control"))
