"""History-v3 integration regressions using synthetic receipts and isolated roots.

These exercise the actual collector, journal, independent head, object store,
restart and verification boundaries. No live account, credential or order API
is used. The large fixture is an artificial boundary reproduction, not a claim
that a real account experienced this failure.
"""
import base64
import builtins
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from execution_accounts.provider import build_observation
from execution_accounts.quotes import parse_orderbook
from execution_control.store import MAX_ROW_BYTES, _canonical, _utc
from execution_launch.evidence_objects import EvidenceObjectStore
from execution_launch.live_history import SIZE_FALLBACK, _row
from tests import accounts_collector as F
from tests import compliance_fixtures as CF
from tests import launch_live_history as LH
from tests import launch_universe_history as U


class ManyDustSource:
    """An invented, fully reconciled account with many unlisted unit positions."""
    account_scope = F.SCOPE

    def __init__(self, count):
        self.calls = []
        self.details = {}
        self.balances = [dict(currency="KRW", balance=str(100000 - count), locked="0")]
        for i in range(count):
            base = "X%011d" % i
            at = F.NOW - timedelta(seconds=3600 - 2 * i)
            detail = F.order_fixture()
            detail.update(uuid="order-%d" % i, identifier="client-%d" % i, market="KRW-" + base,
                          created_at=at.isoformat(), price="1", paid_fee="0")
            detail["trades"][0].update(uuid="fill-%d" % i, market="KRW-" + base, price="1", funds="1",
                                       created_at=(at + timedelta(seconds=1)).isoformat())
            self.details[detail["uuid"]] = detail
            self.balances.append(dict(currency=base, balance="1", locked="0"))

    def fetch(self, path, params):
        self.calls.append((path, params))
        args = dict(params)
        if path == "/v1/accounts":
            body = self.balances
        elif path == "/v1/orders/closed":
            lo, hi = int(args["start_time"]), int(args["end_time"])
            matching = [item for item in self.details.values()
                        if lo <= int(F.datetime.fromisoformat(item["created_at"]).timestamp() * 1000) <= hi]
            body = [{key: value for key, value in item.items() if key != "trades"} for item in matching[:1000]]
        elif path == "/v1/order":
            body = self.details[args["uuid"]]
        elif path == "/v1/market/all":
            body = [dict(market=U.BTC), dict(market=U.ETH)]
        elif path in ("/v1/orders/open", "/v1/deposits", "/v1/withdraws"):
            body = []
        else:
            raise AssertionError("unexpected synthetic route")
        return F.receipt(path, params, deepcopy(body))


_MODEL = ("_slots", "_chain", "_marks", "_prices", "_state", "_inputs", "recorded_allow",
          "_head", "_size", "_seq")


def model(env):
    return {name: getattr(env.h, name) for name in _MODEL}


def files(root):
    """All local fixture names and bytes, including orphan/pending files."""
    return {str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
            for path in root.rglob("*")}


def retained(env):
    return (files(LH.directory(env.window)), files(env.hroot), model(env), env.h._failed)


def padded_book(env, index=0):
    original = U.book(env, index)
    wire = json.loads(original.receipt.raw_body)
    wire[0]["padding"] = ""
    raw = json.dumps(wire, separators=(",", ":")).encode()
    wire[0]["padding"] = "x" * (131072 - len(raw))
    raw = json.dumps(wire, separators=(",", ":")).encode()
    assert len(raw) == 131072
    receipt = replace(original.receipt, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    return parse_orderbook(receipt, symbol=U.BTC, now=env.T(index))


def test_actual_collector_1500_holdings_and_full_size_book_survive_head_commit_and_restart():
    with U.head_root() as hroot:
        env = U.ubuild(hroot)
        slot = env.T(0)
        with patch.object(F, "NOW", slot), patch.object(F, "ORIGIN", slot - timedelta(days=1)), \
             patch.object(F, "SCOPE", env.profile.account_scope):
            source = ManyDustSource(1500)
            source.account_scope = env.profile.account_scope
            collection = F.collect(source)
            account = collection.bundle.accounts[0]
            observation = build_observation(collection.bundle, now=slot)
        assert len(account.positions) == 1500 and len(source.calls) < 2000
        assert all(item.units == 1 and item.price == 0 and item.unlisted is True for item in account.positions)
        book = padded_book(env)
        universe = U.reads(env, 0, U.SWITCH[0], flags={U.XRP: "caution"})
        env.c[0] = slot + LH.seconds(1)
        old_head = env.head.read()
        with patch.object(env.head, "compare_and_set", wraps=env.head.compare_and_set) as cas:
            head = env.h.record_slot(book, observation, trade_symbol=U.BTC, universe=universe,
                                     tick_size=U.D(1), positions=account.positions)
        cas.assert_called_once_with(old_head, head)
        assert head == env.head.read() and LH.sequence(env) == 2
        outer = LH.rows(env)[1]
        logical = U.logical_rows(env)[1]["data"]
        assert set(outer["data"]) == {"history_version", "index", "payload_ref"}
        assert outer["data"]["history_version"] == 3
        assert len(_canonical(outer) + b"\n") < 2048
        conceptual = _row(outer["seq"], old_head, "slot", logical, env.c[0])
        assert len(_canonical(conceptual) + b"\n") > MAX_ROW_BYTES
        assert base64.b64decode(logical["receipt"]["raw_body_b64"]) == book.receipt.raw_body
        assert logical["receipt"]["sha256"] == book.receipt.sha256
        assert logical["holdings"] == sorted(
            [item.symbol, "1", "0", _utc(item.asof), True, True] for item in account.positions)
        expected_universe = {
            "snapshot": {"day": slot.date().isoformat(), "sha256": "e" * 64, "top_n": [U.BTC, U.ETH]},
            "flags": {"sha256": "1" * 64, "exceptions": [[U.XRP, "caution"]]},
            "tickers": {"sha256": "2" * 64,
                        "prices": [[coin, "100", -2000] for coin in (U.BTC, U.ETH, U.XRP)]},
            "allow": [U.BTC, U.ETH], "reasons": [], "events": [],
        }
        assert _canonical(logical["universe"]) == _canonical(expected_universe)
        assert SIZE_FALLBACK not in logical["universe"]["reasons"]
        assert env.h.recorded_allow == frozenset({U.BTC, U.ETH})
        now = slot + LH.seconds(2)
        env.c[0] = now
        frame = env.h.provider(LH.obs(env, now))
        receipt = env.h.verifier(frame, env.identity, now)
        assert (frame.bars[0].bid, frame.bars[0].ask, frame.bars[0].source_sha256) == (
            book.bid, book.ask, book.receipt.sha256)
        before = retained(env)
        U.restart(env)
        assert retained(env) == before
        assert env.h.provider(LH.obs(env, now)) == frame
        assert env.h.verifier(frame, env.identity, now) == receipt
        assert U.logical_rows(env)[1]["data"] == logical
        # The next chooser evaluation consumes the price/state restored from
        # the large slot; it must not behave as if that slot had no prices.
        U.record(env, 1, U.SWITCH[1])
        assert U.logical_rows(env)[2]["data"]["decision"]["coin"] == U.BTC


def measured_capacity():
    """Observe real peak files during verified publication, not admission math."""
    with CF.temp_home(), U.head_root() as hroot:
        env = U.ubuild(hroot, storage_policy=U.policy(max_journal_bytes=9999))
        store = U.objects(env)
        store.initialize()
        peak = [0, 0]
        original = EvidenceObjectStore._read_file

        def observed(instance, path, maximum):
            result = original(instance, path, maximum)
            if instance.root == store.root:
                current = [item.stat().st_size for item in store.root.rglob("*") if item.is_file()]
                peak[0], peak[1] = max(peak[0], sum(current)), max(peak[1], len(current))
            return result

        header_bytes = LH.journal(env).stat().st_size
        with patch.object(EvidenceObjectStore, "_read_file", observed):
            U.record(env, 0, U.SWITCH[0])
        journal_bytes = LH.journal(env).stat().st_size
        # All target journal caps have the same decimal width as the calibration
        # cap, keeping the policy-bearing bound row's byte length unchanged.
        assert 1001 <= journal_bytes <= 9998
        assert peak[0] > 0 and peak[1] >= 4
        return peak[0], peak[1], header_bytes, journal_bytes


def quota_cases(field, exact):
    for delta in (-1, 0, 1):
        with CF.temp_home(), U.head_root() as hroot:
            policy = U.policy(**{"max_journal_bytes": 9999, field: exact + delta})
            env = U.ubuild(hroot, storage_policy=policy)
            U.objects(env).initialize()
            before = retained(env)
            if delta < 0:
                LH.refused(lambda: U.record(env, 0, U.SWITCH[0]), "HISTORY_STORAGE_LIMIT_EXCEEDED")
                assert retained(env) == before
                assert len(LH.rows(env)) == 1 and LH.sequence(env) == 1
            else:
                U.record(env, 0, U.SWITCH[0])
                assert len(LH.rows(env)) == 2 and LH.sequence(env) == 2
                assert U.logical_rows(env)[1]["data"]["universe"]["allow"] == [U.BTC, U.ETH]
                env.c[0] = env.T(0) + LH.seconds(2)
                frame = env.h.provider(LH.obs(env, env.T(0) + LH.seconds(2)))
                U.restart(env)
                assert env.h.provider(LH.obs(env, env.T(0) + LH.seconds(2))) == frame


def test_real_object_byte_quota_one_below_exact_and_one_above_peak():
    peak_bytes, _, _, _ = measured_capacity()
    quota_cases("max_window_bytes", peak_bytes)


def test_real_object_count_quota_one_below_exact_and_one_above_peak():
    _, peak_objects, _, _ = measured_capacity()
    quota_cases("max_window_objects", peak_objects)


def test_real_journal_byte_quota_one_below_exact_and_one_above_complete_row():
    _, _, header_bytes, total = measured_capacity()
    assert total > header_bytes
    quota_cases("max_journal_bytes", total)


def test_missing_or_same_size_corrupt_old_objects_refuse_after_successful_replay():
    for kind in ("manifest", "chunk"):
        for damage in ("missing", "changed"):
            with CF.temp_home(), U.head_root() as hroot:
                env = U.ubuild(hroot)
                for index in range(3):
                    U.record(env, index, U.SWITCH[index])
                U.restart(env)
                now = env.T(2) + LH.seconds(2)
                env.c[0] = now
                frame = env.h.provider(LH.obs(env, now))
                env.h.verifier(frame, env.identity, now)
                known = model(env)
                journal, head = LH.journal(env).read_bytes(), env.head.read()
                # Damage the first slot, not the current one: validating only
                # the latest payload or caching a successful replay is unsafe.
                reference = LH.rows(env)[1]["data"]["payload_ref"]
                folder = U.objects(env).root / "objects"
                target = folder / (reference["manifest_sha256"] + ".blob")
                if kind == "chunk":
                    manifest = json.loads(target.read_bytes())
                    target = folder / (manifest["chunks"][0]["sha256"] + ".blob")
                raw = target.read_bytes()
                if damage == "missing":
                    target.unlink()
                else:
                    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                    assert target.stat().st_size == len(raw)
                LH.refused(lambda: env.h.provider(LH.obs(env, now)), "HISTORY_STORE_RECORD_INVALID")
                LH.refused(lambda: env.h.verifier(frame, env.identity, now), "HISTORY_STORE_RECORD_INVALID")
                assert model(env) == known
                assert LH.journal(env).read_bytes() == journal and env.head.read() == head
                LH.refused(lambda: U.restart(env), "HISTORY_STORE_RECORD_INVALID")


def clock_after_graph_check(offset, expected):
    with U.head_root() as hroot:
        env = U.ubuild(hroot)
        U.record(env, 0, U.SWITCH[0])
        tick = env.T(0) + LH.seconds(9)
        env.c[0] = tick
        frame = env.h.provider(LH.obs(env, tick))
        original = env.h._durable_unchanged
        calls = []

        def advances_after_real_check():
            result = original()
            calls.append(True)
            env.c[0] = env.T(0) + offset
            return result

        before = retained(env)
        with patch.object(env.h, "_durable_unchanged", advances_after_real_check):
            if expected:
                LH.refused(lambda: env.h.verifier(frame, env.identity, tick), expected)
            else:
                receipt = env.h.verifier(frame, env.identity, tick)
                assert receipt.expires_at == env.T(0) + LH.seconds(10)
        assert calls and retained(env) == before


def test_verifier_rechecks_expiry_after_actual_object_graph_validation():
    clock_after_graph_check(LH.seconds(10) + timedelta(microseconds=1), "HISTORY_SLOT_WINDOW_CLOSED")


def test_verifier_rechecks_clock_rollback_after_actual_object_graph_validation():
    clock_after_graph_check(LH.seconds(8), "HISTORY_CLOCK_ROLLBACK")


def test_verifier_allows_completion_exactly_at_current_slot_expiry_boundary():
    clock_after_graph_check(LH.seconds(10), None)


def test_head_update_failure_retains_original_model_and_unadopted_complete_record():
    with U.head_root() as hroot:
        env = U.ubuild(hroot)
        U.record(env, 0, U.SWITCH[0])
        known = model(env)
        journal, head_files = LH.journal(env).read_bytes(), files(env.hroot)
        with patch.object(env.head, "compare_and_set", return_value=False):
            LH.refused(lambda: U.record(env, 1, U.SWITCH[1]), "HISTORY_TRUSTED_HEAD_UPDATE_REFUSED")
        assert model(env) == known and env.h._failed is True
        assert files(env.hroot) == head_files and LH.sequence(env) == 2
        assert LH.journal(env).read_bytes().startswith(journal) and len(LH.rows(env)) == 3
        assert U.logical_rows(env)[2]["data"]["universe"]["allow"] == [U.BTC, U.ETH]
        preserved = files(LH.directory(env.window))
        LH.refused(lambda: env.h.provider(LH.obs(env, env.T(1) + LH.seconds(2))), "HISTORY_RECONCILIATION_REQUIRED")
        LH.refused(lambda: U.restart(env), "HISTORY_HEAD_MISMATCH")
        assert files(LH.directory(env.window)) == preserved and files(env.hroot) == head_files


def test_partial_journal_write_keeps_complete_objects_and_original_model_for_reconciliation():
    with U.head_root() as hroot:
        env = U.ubuild(hroot)
        U.record(env, 0, U.SWITCH[0])
        known = model(env)
        journal, head_files = LH.journal(env).read_bytes(), files(env.hroot)
        object_names = set(files(U.objects(env).root))
        original_open = builtins.open

        class PartialAppend:
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
                return self.handle.write(raw[:len(raw) // 2])

        def partially_open(path, mode="r", *args, **kwargs):
            handle = original_open(path, mode, *args, **kwargs)
            return PartialAppend(handle) if Path(path) == LH.journal(env) and mode == "ab" else handle

        with patch("execution_launch.live_history.open", partially_open, create=True):
            LH.refused(lambda: U.record(env, 1, U.SWITCH[1]), "HISTORY_STORE_IO_REFUSED")
        assert model(env) == known and env.h._failed is True
        raw = LH.journal(env).read_bytes()
        assert raw.startswith(journal) and len(raw) > len(journal) and not raw.endswith(b"\n")
        assert files(env.hroot) == head_files
        after_objects = files(U.objects(env).root)
        assert set(after_objects) > object_names and "objects/pending.blob" not in after_objects
        preserved = files(LH.directory(env.window))
        LH.refused(lambda: env.h.provider(LH.obs(env, env.T(1) + LH.seconds(2))), "HISTORY_RECONCILIATION_REQUIRED")
        LH.refused(lambda: U.restart(env), "HISTORY_STORE_RECORD_INVALID")
        assert files(LH.directory(env.window)) == preserved and files(env.hroot) == head_files


def test_independent_head_refuses_malformed_logical_successor_despite_consistent_hashes():
    changes = (
        lambda slot: slot["anchor"].update(cash_quote="-1"),
        lambda slot: slot["anchor"].update(account_asof="not-a-timestamp"),
        lambda slot: slot.update(holdings=[[U.BTC, "1", "100", slot["anchor"]["account_asof"], 1, False]]),
        lambda slot: slot.update(holdings=[[U.BTC, "1.0", "100", slot["anchor"]["account_asof"], False, False]]),
        lambda slot: slot["receipt"].update(raw_body_b64="!!!"),
        lambda slot: slot.update(tick_size="1.0"),
        lambda slot: slot["universe"]["flags"].update(sha256="not-a-digest"),
        lambda slot: slot["decision"].update(hold_count=True),
        lambda slot: slot["decision"].update(coin="BTC"),
        lambda slot: slot["decision"].update(unrecognized=True),
    )
    for change in changes:
        with CF.temp_home(), U.head_root() as hroot:
            env = U.ubuild(hroot)
            U.record(env, 0, U.SWITCH[0])
            old_head, head_files = env.head.read(), files(env.hroot)
            known = model(env)
            # Produce a complete but uncommitted synthetic successor. This is
            # exactly the point where the independent head must inspect data,
            # rather than merely accepting correctly recomputed outer hashes.
            with patch.object(env.head, "compare_and_set", return_value=False):
                LH.refused(lambda: U.record(env, 1, U.SWITCH[1]), "HISTORY_TRUSTED_HEAD_UPDATE_REFUSED")
            U.rewrite_slot(env, 3, change)
            successor = LH.rows(env)[2]
            assert successor["prev_sha256"] == old_head
            preserved = files(LH.directory(env.window))
            LH.refused(lambda: env.head.compare_and_set(old_head, successor["row_sha256"]),
                       "HEAD_TRANSITION_UNVERIFIED")
            assert files(env.hroot) == head_files and env.head.read() == old_head
            assert files(LH.directory(env.window)) == preserved and model(env) == known


def test_tiny_bound_journal_budget_refuses_before_creating_history_infrastructure():
    with CF.temp_home(), U.head_root() as hroot:
        env = U.ubuild(hroot, storage_policy=U.policy(max_journal_bytes=1), bind=False)
        history = LH.directory(env.window)
        assert not history.exists()
        head_files, known = files(env.hroot), model(env)
        LH.refused(lambda: env.h.bind(env.d), "HISTORY_STORAGE_LIMIT_EXCEEDED")
        assert not history.exists() and files(env.hroot) == head_files
        assert model(env) == known and env.h._bound is False and env.h._failed is False


def test_mutated_policy_is_refused_before_bind_and_before_trusting_existing_history():
    for bound in (False, True):
        with CF.temp_home(), U.head_root() as hroot:
            env = U.ubuild(hroot, bind=bound)
            if bound:
                U.record(env, 0, U.SWITCH[0])
                env.c[0] = env.T(0) + LH.seconds(2)
                frame = env.h.provider(LH.obs(env, env.c[0]))
                env.h.verifier(frame, env.identity, env.c[0])
            before = retained(env)
            # A frozen dataclass is not a cryptographic binding. Simulate a
            # caller modifying its shared policy object after construction.
            object.__setattr__(env.storage_policy, "max_window_bytes", env.storage_policy.max_window_bytes + 1)
            if bound:
                LH.refused(lambda: env.h.provider(LH.obs(env, env.c[0])), "HISTORY_STORAGE_POLICY_MISMATCH")
                LH.refused(lambda: env.h.verifier(frame, env.identity, env.c[0]), "HISTORY_STORAGE_POLICY_MISMATCH")
                LH.refused(lambda: U.record(env, 1, U.SWITCH[1]), "HISTORY_STORAGE_POLICY_MISMATCH")
            else:
                LH.refused(lambda: env.h.bind(env.d), "HISTORY_STORAGE_POLICY_MISMATCH")
            assert retained(env) == before


def test_invalid_in_force_snapshot_digest_is_refused_before_any_slot_write():
    with CF.temp_home(), U.head_root() as hroot:
        env = U.ubuild(hroot)
        malformed = replace(U.snapshot(env), snapshot_sha256="not-a-sha256")
        inputs = U.reads(env, 0, U.SWITCH[0], snap=malformed)
        before = retained(env)
        LH.refused(lambda: U.record(env, 0, U.SWITCH[0], slot_universe=inputs), "HISTORY_INPUT_REQUIRED")
        assert retained(env) == before
        assert len(LH.rows(env)) == 1 and LH.sequence(env) == 1 and env.h._failed is False
        # Correcting the prefetched input may record that same slot; the invalid
        # attempt must not leave an appended row or poison the history instance.
        U.record(env, 0, U.SWITCH[0])
        assert len(LH.rows(env)) == 2 and LH.sequence(env) == 2


def test_unreferenced_orphan_or_pending_blocks_new_writes_but_preserves_verified_history_reads():
    for condition, code in (("over-budget-orphan", "HISTORY_STORAGE_LIMIT_EXCEEDED"),
                            ("pending", "HISTORY_STORAGE_UNAVAILABLE")):
        with CF.temp_home(), U.head_root() as hroot:
            env = U.ubuild(hroot, storage_policy=U.policy(max_window_bytes=65536))
            U.record(env, 0, U.SWITCH[0])
            now = env.T(0) + LH.seconds(2)
            env.c[0] = now
            frame = env.h.provider(LH.obs(env, now))
            receipt = env.h.verifier(frame, env.identity, now)
            objects = U.objects(env)
            if condition == "over-budget-orphan":
                # Inject an unrelated, individually valid synthetic object graph
                # using the standalone store API. No history row references it.
                # Its files fit per-object limits but exceed this window's total
                # write budget together with the previously committed graph.
                orphan = objects.stage(b"x" * 65536)
                assert orphan.manifest_sha256 != LH.rows(env)[1]["data"]["payload_ref"]["manifest_sha256"]
                assert sum(path.stat().st_size for path in objects.root.rglob("*") if path.is_file()) > 65536
            else:
                (objects.root / "objects" / "pending.blob").write_bytes(b"x")
            before = retained(env)
            U.restart(env)
            assert env.h.provider(LH.obs(env, now)) == frame
            assert env.h.verifier(frame, env.identity, now) == receipt
            assert retained(env) == before
            LH.refused(lambda: U.record(env, 1, U.SWITCH[1]), code)
            assert retained(env) == before
            assert len(LH.rows(env)) == 2 and LH.sequence(env) == 2 and env.h._failed is False
