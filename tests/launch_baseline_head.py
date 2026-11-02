"""Independent latest-head record: invented checkpoints in two temporary roots, no owner state, no network."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from unittest.mock import patch

from core import isolation
from execution_accounts.baseline import (
    BaselineError, _body, advance_baseline, restore_state, risk_baseline, state_json,
)
from execution_accounts.baseline_bridge import BaselineBridgeError, ContinuousAccountProvider, advance_account_baseline
from execution_accounts.baseline_store import CheckpointError, CheckpointStore
from execution_accounts.model import content_digest
from execution_launch.baseline_head import BaselineHead, BaselineHeadError, CheckpointChain, HeadRecord
from tests import compliance_fixtures as F
from tests import launch_driver as LD
from tests.accounts_baseline_integration import frame_for, initial, profit_frame

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
NAME = "baseline-head"


@contextmanager
def head_root():
    """A separately provisioned head root: a temporary folder beside (never inside) the temporary TRADEGEN_HOME."""
    root = Path(tempfile.mkdtemp(prefix="tradegen_head_"))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def stack(home, hroot):
    store = CheckpointStore(root=home)
    return store, BaselineHead(root=hroot, name=NAME, chain=CheckpointChain(store))


def seeded(home, hroot, state):
    store, head = stack(home, hroot)
    store.seed(state, expected_head=state.state_digest)
    head.initialize_reviewed_head(state.state_digest)
    return store, head


def counting_source(frame):
    calls = []

    def source(previous, now):
        calls.append(previous.state_digest)
        return frame
    return source, calls


def refused(call, code):
    try:
        call()
    except (BaselineHeadError, BaselineBridgeError, CheckpointError, BaselineError) as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def record_sequence(hroot):
    return json.loads((hroot / NAME / "head.json").read_bytes())["baseline_sequence"]


def test_crash_between_checkpoint_commit_and_head_advance_refuses_on_restart():
    state0 = initial(); frame1 = profit_frame(state0); end = frame1.interval.end
    state1 = advance_account_baseline(state0, frame1.interval, frame1.accounts, now=end).state
    with F.temp_home() as home, head_root() as hroot:
        store, head = seeded(home, hroot, state0)
        # (a) the checkpoint replace succeeded and the process died before the head advanced
        store.commit(state1, expected_previous_head=state0.state_digest)
        store2, head2 = stack(home, hroot)
        source, calls = counting_source(frame1)
        provider = ContinuousAccountProvider(source=source, store=store2, trusted_head=head2)
        refused(lambda: provider(end), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        assert calls == [] and head2.read() == state0.state_digest
        assert store2.load(expected_head=state1.state_digest) == state1
        refused(lambda: store2.seed(state0, expected_head=state0.state_digest), "BASELINE_STORE_ALREADY_INITIALIZED")
        refused(lambda: head2.initialize_reviewed_head(state1.state_digest), "HEAD_ALREADY_INITIALIZED")
    with F.temp_home() as home, head_root() as hroot:
        # (b) the head's own replace fails: the old record stays, the temporary file is evidence, nothing repairs
        store, head = seeded(home, hroot, state0)
        record = hroot / NAME / "head.json"; before = record.read_bytes()
        real = os.replace

        def failing(src, dst, *args, **kwargs):
            if Path(dst).name == "head.json":
                raise OSError("private detail")
            return real(src, dst, *args, **kwargs)
        source, calls = counting_source(frame1)
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=head)
        with patch("execution_launch.baseline_head.os.replace", failing):
            refused(lambda: provider(end), "BASELINE_TRUSTED_HEAD_UPDATE_FAILED")
        assert record.read_bytes() == before and (hroot / NAME / "head.tmp").is_file() and calls
        store2, head2 = stack(home, hroot)
        provider2 = ContinuousAccountProvider(source=source, store=store2, trusted_head=head2)
        refused(lambda: provider2(end), "BASELINE_TRUSTED_HEAD_READ_FAILED")
        refused(head2.read, "HEAD_INTERRUPTED_WRITE")
        refused(lambda: head2.compare_and_set(state0.state_digest, state1.state_digest), "HEAD_INTERRUPTED_WRITE")
        assert record.read_bytes() == before


def test_checkpoint_or_head_rollback_refuses_and_coherent_rollback_needs_the_source_chain():
    """A rollback of either root alone is refused by the mismatch. The head and the store accept a coherent pair
    of old files; only the source chain (a retained later frame) catches that case within 30 s."""
    state0 = initial()
    with F.temp_home() as home, head_root() as hroot:
        store, head = seeded(home, hroot, state0)
        checkpoint = home / "execution-baseline" / "checkpoint.json"; record = hroot / NAME / "head.json"
        supplied, calls = [frame_for(state0)], []

        def source(previous, now):
            calls.append(previous.state_digest)
            return supplied[0]
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=head)
        provider(supplied[0].interval.end); state1 = store.load(expected_head=head.read())
        c1, h1 = checkpoint.read_bytes(), record.read_bytes()
        supplied[0] = frame_for(state1); provider(supplied[0].interval.end); state2 = store.load(expected_head=head.read())
        c2, h2 = checkpoint.read_bytes(), record.read_bytes()
        frame3 = frame_for(state2); supplied[0] = frame3; end3 = frame3.interval.end
        calls.clear()
        checkpoint.write_bytes(c1)                                   # (i) checkpoint alone rolled back
        refused(lambda: provider(end3), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        assert calls == [] and head.read() == state2.state_digest
        checkpoint.write_bytes(c2)
        record.write_bytes(h1)                                       # (ii) head alone rolled back
        refused(lambda: provider(end3), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        assert calls == [] and store.load(expected_head=state2.state_digest) == state2
        record.write_bytes(h2)
        provider(end3); state3 = store.load(expected_head=head.read())        # (iii) reach state3, then roll both back
        assert state3.sequence == 3
        assert head.compare_and_set(state1.state_digest, state3.state_digest) is False
        checkpoint.write_bytes(c1); record.write_bytes(h1)
        assert head.read() == state1.state_digest and store.load(expected_head=state1.state_digest) == state1
        calls.clear()
        refused(lambda: provider(end3), "BASELINE_BRIDGE_EVIDENCE_REFUSED")
        assert calls == [state1.state_digest]
        refused(lambda: advance_baseline(state1, frame3.interval), "BASELINE_CHAIN_GAP_OR_ROLLBACK")


def test_old_coherent_rollback_is_refused_by_the_freshness_rule_and_the_driver_anchor_rule():
    """No frame is retained durably in this phase. An old coherent rollback of both roots is refused by the 30 s
    freshness rules (the reducer's maximum interval and risk_baseline) and by the fixed driver's 30 s account-anchor
    rule; a coherent rollback younger than 30 s with a fresh honest interval is indistinguishable from a tick."""
    state0 = initial()
    with F.temp_home() as home, head_root() as hroot:
        store, head = seeded(home, hroot, state0)
        checkpoint = home / "execution-baseline" / "checkpoint.json"; record = hroot / NAME / "head.json"
        frame1 = frame_for(state0)
        provider = ContinuousAccountProvider(source=lambda previous, now: frame1, store=store, trusted_head=head)
        provider(frame1.interval.end); state1 = store.load(expected_head=head.read())
        c1, h1 = checkpoint.read_bytes(), record.read_bytes()
        frame2 = frame_for(state1)
        ContinuousAccountProvider(source=lambda previous, now: frame2, store=store, trusted_head=head)(frame2.interval.end)
        assert store.load(expected_head=head.read()).sequence == 2
        checkpoint.write_bytes(c1); record.write_bytes(h1)                    # coherent rollback to state1
        late = state1.asof + timedelta(seconds=31)
        # (a) the retained frame redelivered after 30 s: the reducer returns state1 unchanged, risk_baseline refuses
        stale = ContinuousAccountProvider(source=lambda previous, now: frame1, store=store, trusted_head=head)
        refused(lambda: stale(late), "BASELINE_BRIDGE_EVIDENCE_REFUSED")
        refused(lambda: risk_baseline(state1, now=late, expected_head=state1.state_digest), "BASELINE_STALE_OR_FUTURE")
        # (b) an honest fresh interval from the rolled-back state spanning more than 30 s: maximum interval refuses
        fresh = ContinuousAccountProvider(source=lambda previous, now: frame_for(previous, end=now),
                                          store=store, trusted_head=head)
        refused(lambda: fresh(late), "BASELINE_BRIDGE_EVIDENCE_REFUSED")
        refused(lambda: advance_baseline(state1, frame_for(state1, end=late).interval), "BASELINE_TIME_GAP_OR_ROLLBACK")
        assert head.read() == state1.state_digest and checkpoint.read_bytes() == c1
        # the honest limit: within 30 s the same fresh interval is accepted as an ordinary tick
        assert fresh(state1.asof + timedelta(seconds=30)).risk.equity == D("1000")
        assert store.load(expected_head=head.read()).sequence == 2
    # (c) the fixed driver refuses an account anchor older than 30 s against the tick, even when it is consistent
    env = LD.fixture()
    account = env.observation.account
    for seconds, accepted in ((31, False), (30, True)):
        asof = env.observation.now - timedelta(seconds=seconds)
        env.frame = replace(env.frame, anchor=replace(env.frame.anchor, account_asof=asof))
        env.observation = replace(env.observation, account=replace(account, asof=asof, risk=replace(account.risk, asof=asof)))
        if accepted:
            assert LD.decide(env).action in ("entry", "hold", "exit")
        else:
            LD.reject(lambda: LD.decide(env), "FIXED_DRIVER_ACCOUNT_ANCHOR_TIME_INVALID")


def test_mutated_checkpoint_or_head_record_refuses_without_repair():
    state0 = initial(); frame1 = frame_for(state0); end = frame1.interval.end
    with F.temp_home() as home, head_root() as hroot:
        store, head = seeded(home, hroot, state0)
        provider = ContinuousAccountProvider(source=lambda previous, now: frame1, store=store, trusted_head=head)
        provider(end); state1 = store.load(expected_head=head.read())
        checkpoint = home / "execution-baseline" / "checkpoint.json"; record = hroot / NAME / "head.json"
        c1, h1 = checkpoint.read_bytes(), record.read_bytes()
        assert c1.count(b'"equity_krw":"1000"') == 1
        checkpoint.write_bytes(c1.replace(b'"equity_krw":"1000"', b'"equity_krw":"1001"'))
        refused(lambda: provider(end), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        checkpoint.write_bytes(c1)
        digest = state1.state_digest.encode("ascii")
        assert digest.upper() != digest and h1 == b'{"baseline_sequence":1,"head":"' + digest + b'","schema_version":1}'
        variants = (
            (b'{"baseline_sequence":1,"head":"' + digest + b'","head":"' + digest + b'","schema_version":1}',
             "HEAD_RECORD_INVALID"),
            (b'{"baseline_sequence": 1, "head": "' + digest + b'", "schema_version": 1}', "HEAD_RECORD_INVALID"),
            (h1.replace(digest, digest.upper()), "HEAD_RECORD_INVALID"),
            (b'{"baseline_sequence":true,"head":"' + digest + b'","schema_version":1}', "HEAD_RECORD_INVALID"),
            (b'{"baseline_sequence":1.0,"head":"' + digest + b'","schema_version":1}', "HEAD_RECORD_INVALID"),
            (b'{"baseline_sequence":1,"head":"' + digest + b'","note":"x","schema_version":1}', "HEAD_RECORD_INVALID"),
            (b'{"baseline_sequence":1,"head":"', "HEAD_RECORD_INVALID"),
            (h1 + b"\r\n", "HEAD_RECORD_INVALID"),
            (b"x" * 4097, "HEAD_FILE_REFUSED"),
        )
        for raw, code in variants:
            record.write_bytes(raw)
            refused(head.read, code)
            refused(lambda: provider(end), "BASELINE_TRUSTED_HEAD_READ_FAILED")
            assert record.read_bytes() == raw
            record.write_bytes(h1)
        record.write_bytes(b'{"baseline_sequence":1,"head":"' + b"b" * 64 + b'","schema_version":1}')
        assert head.read() == "b" * 64
        refused(lambda: provider(end), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        record.write_bytes(h1)
        alias = hroot / "alias"; os.link(record, alias)
        refused(head.read, "HEAD_FILE_REFUSED")
        refused(lambda: provider(end), "BASELINE_TRUSTED_HEAD_READ_FAILED")
        alias.unlink()
        assert provider(end).risk.equity == D("1000") and record.read_bytes() == h1


def test_concurrent_cas_has_one_winner_and_the_loser_writes_nothing():
    state0 = initial(); frame1 = frame_for(state0)
    state1 = advance_account_baseline(state0, frame1.interval, frame1.accounts, now=frame1.interval.end).state
    frame2 = frame_for(state1)
    state2 = advance_account_baseline(state1, frame2.interval, frame2.accounts, now=frame2.interval.end).state
    with F.temp_home() as home, head_root() as hroot:
        store, A = seeded(home, hroot, state0)
        _, B = stack(home, hroot)
        record = hroot / NAME / "head.json"
        store.commit(state1, expected_previous_head=state0.state_digest)                   # (a) two instances
        assert A.compare_and_set(state0.state_digest, state1.state_digest) is True
        after = record.read_bytes()
        assert B.compare_and_set(state0.state_digest, state1.state_digest) is False
        assert B.compare_and_set(state0.state_digest, "e" * 64) is False
        assert record.read_bytes() == after and B.read() == state1.state_digest
        refused(lambda: A.compare_and_set(state1.state_digest, state2.state_digest), "HEAD_TRANSITION_UNVERIFIED")  # (b)
        refused(lambda: A.compare_and_set(state1.state_digest, state1.state_digest), "HEAD_TRANSITION_UNVERIFIED")
        assert record.read_bytes() == after
        store.commit(state2, expected_previous_head=state1.state_digest)                   # (c) thread race
        entered, release, results = threading.Event(), threading.Event(), {}
        real_load = store.load

        def slow(**kwargs):
            entered.set()
            assert release.wait(5)
            return real_load(**kwargs)

        def run(name, head):
            results[name] = head.compare_and_set(state1.state_digest, state2.state_digest)
        with patch.object(store, "load", slow):
            first = threading.Thread(target=run, args=("A", A)); first.start()
            assert entered.wait(5)
            second = threading.Thread(target=run, args=("B", B)); second.start()
            release.set(); first.join(10); second.join(10)
        assert not first.is_alive() and not second.is_alive()
        assert (results["A"], results["B"]) == (True, False)
        assert A.read() == state2.state_digest and record_sequence(hroot) == 2
        frame3 = frame_for(state2); end3 = frame3.interval.end                           # (d) two providers
        loaded, gate, outcome = threading.Event(), threading.Event(), []

        def blocking_source(previous, now):
            loaded.set()
            assert gate.wait(5)
            return frame3
        store1, head1 = stack(home, hroot)
        P1 = ContinuousAccountProvider(source=blocking_source, store=store1, trusted_head=head1)
        store2, head2 = stack(home, hroot)
        P2 = ContinuousAccountProvider(source=lambda previous, now: frame3, store=store2, trusted_head=head2)

        def run_p1():
            try:
                P1(end3); outcome.append("returned")
            except BaselineBridgeError as exc:
                outcome.append(str(exc))
        worker = threading.Thread(target=run_p1); worker.start()
        assert loaded.wait(5)
        assert P2(end3).risk.equity == D("1000")
        gate.set(); worker.join(10)
        assert not worker.is_alive() and outcome == ["BASELINE_PROVIDER_COMMIT_REFUSED"]
        assert record_sequence(hroot) == 3 and A.read() == store.load(expected_head=A.read()).state_digest


def test_day_opening_peak_and_loss_resets_refuse_at_store_head_and_initialization():
    state0 = initial()
    with F.temp_home() as home, head_root() as hroot:
        store, head = seeded(home, hroot, state0)
        frame1 = frame_for(state0, minimum_equity_krw=D("980"), maximum_equity_krw=D("1010"))
        ContinuousAccountProvider(source=lambda previous, now: frame1, store=store, trusted_head=head)(frame1.interval.end)
        state1 = store.load(expected_head=head.read())
        assert (state1.day_start_equity, state1.high_watermark, state1.observed_daily_loss) == (D("1000"), D("1010"), D("20"))
        frame2 = frame_for(state1); state2 = advance_baseline(state1, frame2.interval)

        def reheaded(**changes):
            # A self-consistent local hash (the reducer's own digest body) still cannot authorize a historical reset.
            candidate = replace(state2, **changes)
            return replace(candidate, state_digest=content_digest(_body(candidate)))
        for changes, code in ((dict(day_start_equity=D("1010")), "BASELINE_STORE_DAILY_HISTORY_CHANGED"),
                              (dict(high_watermark=D("1000")), "BASELINE_STORE_PEAK_ROLLBACK"),
                              (dict(observed_daily_loss=D("0")), "BASELINE_STORE_DAILY_HISTORY_CHANGED")):
            candidate = reheaded(**changes)
            assert restore_state(state_json(candidate), expected_head=candidate.state_digest) == candidate
            refused(lambda: store.commit(candidate, expected_previous_head=state1.state_digest), code)
            refused(lambda: head.compare_and_set(state1.state_digest, candidate.state_digest), "HEAD_TRANSITION_UNVERIFIED")
            assert head.read() == state1.state_digest
        checkpoint = home / "execution-baseline" / "checkpoint.json"; c1 = checkpoint.read_bytes()
        checkpoint.write_bytes(state_json(reheaded(observed_daily_loss=D("0"))).encode("utf-8"))
        provider = ContinuousAccountProvider(source=lambda previous, now: frame2, store=store, trusted_head=head)
        refused(lambda: provider(frame2.interval.end), "BASELINE_PROVIDER_CHECKPOINT_REFUSED")
        checkpoint.write_bytes(c1)
        provider(frame2.interval.end)
        current = store.load(expected_head=head.read())
        assert (current.sequence, current.observed_daily_loss, current.high_watermark) == (2, D("20"), D("1010"))
        refused(lambda: store.seed(state0, expected_head=state0.state_digest), "BASELINE_STORE_ALREADY_INITIALIZED")
        refused(lambda: head.initialize_reviewed_head(state0.state_digest), "HEAD_ALREADY_INITIALIZED")
        with head_root() as fresh:
            other = BaselineHead(root=fresh, name=NAME, chain=CheckpointChain(store))
            refused(lambda: other.initialize_reviewed_head(state2.state_digest), "HEAD_SEED_REQUIRED")
            assert list(fresh.iterdir()) == []


def test_initialization_is_explicit_reviewed_once_and_same_tick_advances_once():
    state0 = initial(); frame = profit_frame(state0); end = frame.interval.end
    with F.temp_home() as home, head_root() as hroot:
        store, head = stack(home, hroot)
        assert list(hroot.iterdir()) == [] and not (home / "execution-baseline").exists()
        refused(head.read, "HEAD_NOT_INITIALIZED")
        source, calls = counting_source(frame)
        provider = ContinuousAccountProvider(source=source, store=store, trusted_head=head)
        refused(lambda: provider(end), "BASELINE_TRUSTED_HEAD_READ_FAILED")
        assert calls == [] and list(hroot.iterdir()) == [] and not (home / "execution-baseline").exists()
        refused(lambda: head.initialize_reviewed_head(state0.state_digest), "HEAD_SEED_REQUIRED")
        assert list(hroot.iterdir()) == []
        store.seed(state0, expected_head=state0.state_digest)
        refused(lambda: head.initialize_reviewed_head("d" * 64), "HEAD_SEED_REQUIRED")
        refused(lambda: head.initialize_reviewed_head("A" * 64), "HEAD_DIGEST_REQUIRED")
        assert list(hroot.iterdir()) == []
        record = head.initialize_reviewed_head(state0.state_digest)
        assert record == HeadRecord(schema_version=1, baseline_sequence=0, head=state0.state_digest)
        assert sorted(p.name for p in (hroot / NAME).iterdir()) == ["head.json", "head.lock"]
        assert (hroot / NAME / "head.json").read_bytes() == (
            b'{"baseline_sequence":0,"head":"' + state0.state_digest.encode("ascii") + b'","schema_version":1}')
        refused(lambda: head.initialize_reviewed_head(state0.state_digest), "HEAD_ALREADY_INITIALIZED")
        with patch.object(head, "compare_and_set", wraps=head.compare_and_set) as cas:
            for _ in range(4):
                assert provider(end).risk.equity == D("1018")
            assert cas.call_count == 1
        assert record_sequence(hroot) == 1 and len(calls) == 4


def test_head_root_is_explicit_local_existing_link_free_and_separate():
    state0 = initial()
    with F.temp_home() as home, head_root() as hroot:
        store = CheckpointStore(root=home); chain = CheckpointChain(store)
        refused(lambda: CheckpointChain(object()), "HEAD_STORE_REQUIRED")
        refused(lambda: BaselineHead(root=hroot, name=NAME, chain=object()), "HEAD_CHAIN_REQUIRED")
        for root in (str(hroot), Path("relative")):
            refused(lambda: BaselineHead(root=root, name=NAME, chain=chain), "HEAD_EXPLICIT_ROOT_REQUIRED")
        for name in ("", "Baseline-Head", "con", "a/b", "head.json", 5):
            refused(lambda: BaselineHead(root=hroot, name=name, chain=chain), "HEAD_NAME_REQUIRED")
        (home / "inner").mkdir()
        for root in (home, home / "inner", home.parent, ROOT / "tests"):
            refused(lambda: BaselineHead(root=root, name=NAME, chain=chain), "HEAD_ROOT_NOT_SEPARATE")
        refused(lambda: BaselineHead(root=hroot / "missing", name=NAME, chain=chain), "HEAD_ROOT_REFUSED")
        target = hroot / "target"; (target / "deeper").mkdir(parents=True)
        other = hroot / "other"; other.mkdir()
        F.directory_link(other / "j", target)
        for root in (other / "j", other / "j" / "deeper"):
            refused(lambda: BaselineHead(root=root, name=NAME, chain=chain), "HEAD_LINK_REFUSED")
        assert [p.name for p in target.iterdir()] == ["deeper"]
        if os.name == "nt":
            for root in (Path("\\\\?\\" + str(hroot)), Path("\\\\localhost\\C$\\x")):
                refused(lambda: BaselineHead(root=root, name=NAME, chain=chain), "HEAD_LOCAL_ROOT_REQUIRED")
        store.seed(state0, expected_head=state0.state_digest)
        head = BaselineHead(root=hroot, name=NAME, chain=chain)
        head.initialize_reviewed_head(state0.state_digest)
        assert head.read() == state0.state_digest
        with patch.dict(os.environ, {"TRADEGEN_HOME": str(target)}):      # the state root moved under the head root
            isolation._LINK_SCAN.clear()
            refused(head.read, "HEAD_ROOT_NOT_SEPARATE")
        isolation._LINK_SCAN.clear()
        assert head.read() == state0.state_digest
