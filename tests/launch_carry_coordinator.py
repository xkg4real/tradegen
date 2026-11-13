"""Carry-v2's actual final-slot path, with synthetic sources and real temporary signature verification.

The account pages/coverage and market prices are invented fixtures, not evidence of
live held-account completeness. The tests do not patch the strategy assessment,
issued callback, history authentication, risk/controller or approval verdicts.
Only disposable fixture keys, isolated files and DryRunAdapter are used.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import timedelta
from decimal import Decimal
import base64
import copy
import importlib.metadata
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner, rules
from core.compliance.model import KST
from core.isolation import state_root
from execution_accounts.baseline import BaselineAnchor, BaselineConventions, BaselineInterval
from execution_accounts.baseline_bridge import BaselineFrame, initialize_account_baseline
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import RiskBaseline, content_digest
from execution_control.capability import digest
from execution_control.dry_run import DryRunAdapter
from execution_control.store import GENESIS
from execution_launch import coordinator as C
from execution_launch import protective_store as PS
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_driver, make_fixed_carry_driver
from execution_launch.managed_behavior import FixedDecisionV2
from execution_launch.paper_capture import CaptureArchive, capture_json
from execution_launch.profile import profile_body, risk_policy
from execution_launch.program import parameters_json, program_json, target_fraction
from execution_launch.protective_state import ManagementEvent, ManagementPolicy, state_digest
from execution_launch.review_auth import review_body, review_signing_bytes
from execution_launch.review_request import build_review_request
from execution_launch.strategy import (PaperDecision, capture_history_digests, evidence_digest, protocol_json,
                                      register_protocol, run_paper_validation)
from execution_orders import upbit
from tests.accounts_provider import SCOPE, bundle, fill, order
from tests.launch_baseline_head import head_root
from tests.launch_coordinator import Books, FakeTime, compose_args, history_journal, private_inputs, seconds
from tests.launch_protective_store import limits
from tests.launch_review_auth import invented_provider, invented_verifier
from tests.launch_windows_owner_authority import keys, raw, real_code_hash, signed_home

D = Decimal
ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def memoized_pure_inputs():
    """Cache pure closure discovery/YAML parsing, never approval or signature verdicts.

    Unlike a root-only closure cache, every lookup hashes all current repository
    Python bytes and installed dependency RECORD bytes first. Added, removed or
    changed source inputs invalidate the cached real closure. YAML keys include
    the exact raw bytes and role, and callers receive independent parsed values.
    The tests use disposable homes and do not mutate production files.
    """
    real_files, real_load, closures, documents = owner.code_files, rules.load_strict, {}, {}

    def memo_files(root):
        root = Path(root).resolve()
        inputs = [(p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                  for p in sorted(root.rglob("*.py")) if p.is_file()]
        for name in owner._RECORD_DISTS:
            try:
                dist = importlib.metadata.distribution(name)
            except importlib.metadata.PackageNotFoundError:
                continue
            record = next((f for f in dist.files or () if f.name == "RECORD"
                           and f.parent.name.endswith(".dist-info")), None)
            if record is not None:
                inputs.append((f"venv:{name}-{dist.version}.dist-info/RECORD",
                               hashlib.sha256(Path(record.locate()).read_bytes()).hexdigest()))
        key = (root, tuple(inputs))
        if key not in closures:
            closures[key] = real_files(root)
        return list(closures[key])

    def memo_load(raw, what):
        key = (bytes(raw), what)
        if key not in documents:
            documents[key] = real_load(raw, what)
        return copy.deepcopy(documents[key])

    with patch.object(owner, "code_files", memo_files), patch.object(rules, "load_strict", memo_load):
        yield


class Accounts:
    """Complete synthetic pages. A known external GTC fill supplies inventory after the required flat start.

    This is a fixture source, not the unavailable production held-account issuer.
    Its constant account mark intentionally stays separate from the current book.
    """
    def __init__(self, fake, cash, window, *, late_fill=False, holding_fraction=D(1)):
        self.fake, self.initial, self.window, self.late_fill = fake, cash, window, late_fill
        self.holding_fraction = holding_fraction
        self.calls, self.prefetches = [], []
        self.fill_id, self.order_id, self.client_id = "carry-fixture-fill", "carry-fixture-gtc", "carry-fixture-client"

    def prefetch(self, previous):
        self.prefetches.append((self.fake.now, previous.state_digest))

    def account(self, now):
        units = self.initial / D(100) * self.holding_fraction
        first_at = self.window.start + seconds(20)
        late_at = self.window.end + seconds(5)
        first_quantity = units / D(2) if self.late_fill else units
        fills, orders, held = (), (), D(0)
        if now >= first_at:
            fills = (fill(side="buy", quantity=first_quantity, price=D(100), fee=D(0),
                          order=self.order_id, fid=self.fill_id, at=first_at),)
            held = first_quantity
            if self.late_fill and now >= late_at:
                fills += (fill(side="buy", quantity=units - first_quantity, price=D(100), fee=D(0),
                               order=self.order_id, fid="carry-fixture-late-fill", at=late_at),)
                held = units
            status = "partial" if held < units else "filled"
            orders = (order(side="buy", quantity=units, filled=held, price=D(100), oid=self.order_id,
                            client=self.client_id, status=status),)
        return bundle(now=now, opening=self.initial, cash=self.initial - held * D(100),
                      units=held, price=D(100), fills=fills, orders=orders).accounts

    def __call__(self, previous, now):
        self.calls.append(now)
        accounts = self.account(now)
        interval = BaselineInterval(account_scope=SCOPE, sequence=previous.sequence + 1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=now,
            equity_krw=self.initial, minimum_equity_krw=self.initial, maximum_equity_krw=self.initial,
            realized_net_total_krw=D(0), gross_external_inflows_krw=D(0), gross_external_outflows_krw=D(0),
            source_sha256=content_digest(accounts), coverage_sha256=hashlib.sha256(b"synthetic complete coverage").hexdigest())
        return BaselineFrame(interval=interval, accounts=accounts)


class RisingBooks(Books):
    def __init__(self, fake, window):
        super().__init__(fake, bid=100, ask=101)
        self.window, self.original = window, []

    def read(self):
        index = max(0, int((self.fake.now - self.window.start + seconds(3)).total_seconds()) // 60)
        self.bid, self.ask = 100 + index, 101 + index
        value = super().read()
        self.original.append(value)
        return value


def _reviewed(research, t0, window, *, carry):
    profile = replace(research.profile, instrument_rules=replace(research.profile.instrument_rules,
                                                               asof=t0 - seconds(30)))
    protocol, result, registry, decisions = research.protocol, research.result, research.registry, research.decisions
    capture = research.raw.decode("ascii") if type(research.raw) is bytes else research.raw
    factory = make_fixed_carry_driver
    if not carry:
        protocol = replace(protocol, schema_version=1, evaluator_revision="forward-paper-v1",
                           behavior_revision=None, terminal_accounting=None, management_behavior_sha256=None)
        registry = register_protocol(protocol)
        prefixes = capture_history_digests(research.bars)
        decisions = tuple(PaperDecision(bar_index=i, decided_at=bar.received_at, history_sha256=prefixes[i],
            target_fraction=target_fraction(research.program, tuple(row.mark for row in research.bars[:i+1])))
            for i, bar in enumerate(research.bars[:-1]))
        result = run_paper_validation(protocol, research.bars, decisions, profile.instrument_rules,
                                     registry=registry, source_kind="prospective_paper_capture", now=research.now)
        capture = capture_json(CaptureArchive(registry=registry, source_kind="prospective_paper_capture",
                                             bars=research.bars, decisions=decisions))
        factory = make_fixed_driver
    probe = factory(research.program, protocol, profile, window=window, history_provider=invented_provider,
                    history_verifier=invented_verifier, program_artifact=research.artifact)
    identity = describe_fixed_driver(probe)
    request = build_review_request(profile, protocol, result, now=research.now,
                                  program_artifact=research.artifact, parameters_json=research.parameters)
    key, _ = keys()
    body = review_body(request, asdict(identity), deployment_code_hash=real_code_hash(),
        audit_sha256=hashlib.sha256(b"synthetic carry coordinator source audit; never a real owner approval").hexdigest(),
        owner_fingerprint="SHA256:" + hashlib.sha256(raw(key)).hexdigest(),
        issued_at=t0 - seconds(30), expires_at=t0 + timedelta(hours=1))
    document = json.dumps({"body": body, "signature_b64": base64.b64encode(key.sign(review_signing_bytes(body))).decode("ascii")})
    files = {"profile.json": json.dumps(profile_body(profile)), "program.json": program_json(research.program),
             "protocol.json": protocol_json(protocol), "capture.json": capture, "review.json": document}
    return SimpleNamespace(profile=profile, protocol=protocol, result=result, identity=identity, files=files)


@contextmanager
def fixture(*, carry=True, late_fill=False, provision=True, holding_fraction=D(1)):
    from tests.launch_carry_strategy import fixture_capture
    research = fixture_capture(account_scope=SCOPE)
    t0 = research.now + seconds(30)  # rules/review are observed at research.now; the final slot stays within five minutes
    window = DeploymentWindow(deployment_id="carry-coordinator-fixture", start=t0 + seconds(20), end=t0 + seconds(260))
    monitor_until = window.end + seconds(40)
    with memoized_pure_inputs(), signed_home() as home, head_root() as hroot:
        reviewed = _reviewed(research, t0, window, carry=carry)
        fake = FakeTime(t0)
        source = Accounts(fake, reviewed.protocol.initial_cash_quote, window, late_fill=late_fill,
                          holding_fraction=holding_fraction)
        at = t0 - seconds(5)
        accounts = source.account(at)
        baseline = RiskBaseline(day_start_equity=source.initial, prior_high_watermark=source.initial,
            observed_daily_loss=D(0), approved_effective_floor=source.initial * D("0.75"),
            first_trading_day=at.astimezone(KST).date() - timedelta(days=5), asof=at,
            source_sha256=content_digest(accounts))
        anchor = BaselineAnchor(account_scope=SCOPE, baseline=baseline, equity_krw=source.initial,
            realized_net_total_krw=D(0), day_open_realized_net_total_krw=D(0), previous_day_realized_net_krw=D(0), sequence=0)
        conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
            external_flows="no_external_flows", max_interval_seconds=300, recovery_cutoff_seconds=None)
        state = initialize_account_baseline(conventions, anchor, accounts, now=at).state
        checkpoints = CheckpointStore(root=home)
        checkpoints.seed(state, expected_head=state.state_digest)
        baseline_head = BaselineHead(root=hroot, name="carry-account-head", chain=CheckpointChain(checkpoints))
        baseline_head.initialize_reviewed_head(state.state_digest)
        BaselineHead(root=hroot, name=C.history_head_name(window),
                     chain=C.HistoryChain(root=home, window=window)).initialize_reviewed_head(GENESIS)
        with private_inputs(reviewed.files) as paths:
            comp = C.compose(**compose_args(paths, research.now, window, fake.clock, hroot))
            protection = None
            if carry:
                policy = ManagementPolicy(management_id="carry-management-fixture", account_scope=SCOPE,
                    venue="upbit", market="spot", quote_currency="KRW", symbol=comp.profile.symbol,
                    code_sha256=comp.identity.deployment_code_sha256, strategy_sha256=comp.protocol.strategy_code_sha256,
                    risk_policy_sha256=digest(risk_policy(comp.profile)), holding_deadline=window.end,
                    monitor_until=monitor_until)
                protection = PS.ProtectiveStore(root=home / "carry-protective", head_root=hroot,
                    head_name="carry-protective-head", policy=policy,
                    binding=PS.StoreBinding(driver_identity_sha256=digest(comp.identity),
                        research_sha256=evidence_digest(comp.evidence.result), source_sha256=comp.evidence.result.inputs_digest),
                    limits=limits())
                if provision:
                    protection.provision_empty()
                    protection.head.initialize_reviewed_head(protection.genesis_digest)
            adapter, books, notices = DryRunAdapter(upbit), RisingBooks(fake, window), []
            args = dict(mode="rehearsal", profile=comp.profile, evidence=comp.evidence, driver=comp.driver,
                implementation_verifier=comp.verifiers.implementation, adapters={"upbit": adapter},
                account_source=source, account_prefetch=source.prefetch, trusted_head=baseline_head,
                quote_source=books, window=window, bar_seconds=60, monitor_until=monitor_until,
                clock=fake.clock, history=comp.history, monitor_seconds=20, prefetch_lead_seconds=3,
                wait=fake.wait, protective_store=protection, toast=lambda title, body: True)
            c = C.Coordinator(**args)
            c._toasts = SimpleNamespace(put=lambda title, body: notices.append((title, body)))
            yield SimpleNamespace(c=c, comp=comp, protection=protection, source=source, books=books, fake=fake,
                adapter=adapter, home=home, hroot=hroot, args=args, window=window, notices=notices,
                reviewed=reviewed, research=research)


def test_actual_final_slot_retains_inventory_and_confirms_one_persistent_management_request():
    with fixture() as env:
        status = env.c.run()
        assert env.window.end in env.comp.driver.callback.seen, status
        assert len(env.comp.history._slots) == 5 and isinstance(env.comp.history._slots[-1].decision, FixedDecisionV2)
        assert env.comp.history._frame().prior_decision == env.comp.history._slots[-2].decision
        assert status.last_tick.status == "blocked" and status.last_tick.decision_state == "long_target", status
        assert status.last_tick.execution_block_reasons == ("MANAGED_DEADLINE_REACHED",)
        assert not [r for r in env.adapter.requests if r.operation == "create"]
        assert env.c._observation.holdings[("upbit", SCOPE, "spot", env.comp.profile.symbol)] == env.source.initial / D(100)
        snapshot = env.protection.inspect()
        requests = [effect for effect in snapshot.outbox if effect.kind == "request_management_approval"]
        assert len(requests) == 1 and status.management_request_id == requests[0].intent_id
        assert status.management_deadline_recorded and status.management_source == "" and status.new_entry_blocked
        assert snapshot.journal_sequence == 1 and snapshot.state.can_reduce is False
        assert snapshot.ledger_refs == PS.LedgerReferences(**{field: None for field in asdict(snapshot.ledger_refs)})
        before = snapshot.head
        assert env.c._management_deadline(env.fake.now + seconds(20))
        assert env.protection.inspect().head == before and env.c.status().management_request_id == requests[0].intent_id
        rows = history_journal(env.home, env.window).read_bytes().splitlines()
        assert len(rows) == 6 and json.loads(rows[-1])["data"]["receipt"]["sha256"] == env.books.original[-1].receipt.sha256


def test_deadline_storage_failure_preserves_final_quote_and_blocks_dependent_execution():
    with fixture() as env:
        def fail_commit(*args):
            raise RuntimeError("PRIVATE-P2-STORAGE-DETAIL")
        with patch.object(env.protection.head, "compare_and_set", fail_commit):
            status = env.c.run()
        assert len(env.comp.history._slots) == 5
        assert env.window.end not in env.comp.driver.callback.seen
        assert not status.management_deadline_recorded and status.management_request_id is None
        assert status.management_source and status.new_entry_blocked
        assert not [r for r in env.adapter.requests if r.operation == "create"]
        assert "PRIVATE-P2" not in repr(status)
        last = json.loads(history_journal(env.home, env.window).read_bytes().splitlines()[-1])
        assert last["data"]["receipt"]["sha256"] == env.books.original[-1].receipt.sha256


def test_deadline_bridge_never_provisions_or_initializes_a_missing_protection_store():
    with fixture(provision=False) as env:
        status = env.c.run()
        assert not env.protection.root.exists() and not status.management_deadline_recorded
        assert status.management_source and status.new_entry_blocked
        assert not [r for r in env.adapter.requests if r.operation == "create"]


def test_carry_requires_exact_protection_context_and_keeps_controlled_mode_refused():
    with fixture() as env:
        for changes, code in (({"protective_store": None}, "COORDINATOR_PROTECTIVE_STORE_REQUIRED"),
                              ({"mode": "controlled"}, "COORDINATOR_MODE_UNSUPPORTED")):
            try:
                C.Coordinator(**(env.args | changes))
            except C.CoordinatorError as exc:
                assert str(exc) == code
            else:
                raise AssertionError("unsupported carry composition accepted")
        for change in ({"holding_deadline": env.window.end + seconds(1)}, {"symbol": "KRW-ETH"},
                       {"code_sha256": "f" * 64}, {"risk_policy_sha256": "f" * 64},
                       {"monitor_until": env.window.end + seconds(100)}):
            with patch.object(env.protection, "policy", replace(env.protection.policy, **change)):
                try:
                    C.Coordinator(**env.args)
                except C.CoordinatorError as exc:
                    assert str(exc) == "COORDINATOR_PROTECTIVE_BINDING_MISMATCH"
                else:
                    raise AssertionError("mismatched P2 context accepted")
        assert env.source.calls == [] and env.adapter.requests == []


def test_existing_gtc_late_fill_is_accounted_under_the_same_id_without_a_new_create():
    with fixture(late_fill=True) as env:
        observed = []
        env.fake.at(env.window.end + seconds(1), lambda: observed.append(env.c._observation))
        status = env.c.run()
        latest = env.c._observation
        assert observed and observed[0].holdings[("upbit", SCOPE, "spot", env.comp.profile.symbol)] == env.source.initial / D(200)
        assert latest.holdings[("upbit", SCOPE, "spot", env.comp.profile.symbol)] == env.source.initial / D(100)
        assert len(latest.fills) == 2 and {item.order_id for item in latest.fills} == {env.source.order_id}
        assert {item.fill_id for item in latest.fills} == {env.source.fill_id, "carry-fixture-late-fill"}
        assert status.management_deadline_recorded and not [r for r in env.adapter.requests if r.operation == "create"]
        # The existing fixed-driver outstanding-order refusal is preserved. This does not
        # claim a production held-account issuer or a resumed managed-order lifecycle.


def test_legacy_actual_final_slot_still_derives_its_original_terminal_exit():
    with fixture(carry=False) as env:
        import sys
        returned = []
        code = env.comp.driver.callback.__call__.__code__
        previous = sys.getprofile()
        def trace(frame, event, value):
            if frame.f_code is code and event == "return" and value is not None:
                returned.append((frame.f_locals["frame"].bars[-1].observed_at, value))
        try:
            sys.setprofile(trace)
            status = env.c.run()
        finally:
            sys.setprofile(previous)
        assert env.window.end in env.comp.driver.callback.seen, status
        assert returned[-1][0] == env.window.end and returned[-1][1].action == "exit"
        assert not status.management_deadline_recorded and env.protection is None
        assert status.last_tick.status in ("submitted", "blocked"), status
        # At least the actual old callback still returns exit; current control may refuse
        # an order according to its existing policy. Never relax that policy for this comparison.
        assert status.last_tick.decision_state is None
        assert env.comp.history._slots[-1].decision is None


def test_a_positive_entry_candidate_at_the_deadline_is_blocked_before_reserve():
    with fixture(holding_fraction=D("0.5")) as env:
        status = env.c.run()
        frame = env.comp.history._frame()
        assert env.window.end in env.comp.driver.callback.seen and frame.anchor.cash_quote > 0
        assert frame.prior_decision.state == "long_target" and frame.prior_decision.target_fraction == 1
        assert status.last_tick.status == "blocked" and status.last_tick.decision_state == "long_target"
        assert status.last_tick.execution_block_reasons == ("MANAGED_DEADLINE_REACHED",)
        assert env.c._controller.states() == () and env.adapter.requests == []
        assert status.management_deadline_recorded


def test_actual_callback_finishing_at_deadline_records_request_before_any_reserve():
    """A transparent return trace advances only the fixture clock after the actual issued callback.

    It neither substitutes the callback/result nor changes a verifier's verdict.
    This simulates time consumed after a valid pre-E decision and before reserve.
    """
    import sys
    with fixture(holding_fraction=D("0.5")) as env:
        c, start = env.c, env.window.start
        c.bootstrap()
        for index in range(3):
            slot = start + seconds(60 * index)
            env.fake.now = slot - seconds(3)
            c._slot(slot)
        penultimate = env.window.end - seconds(60)
        code = env.comp.driver.callback.__call__.__code__
        returned = []
        previous = sys.getprofile()
        def delay(frame, event, value):
            if frame.f_code is code and event == "return" and value is not None:
                returned.append(value)
                env.fake.now = env.window.end
        env.fake.now = penultimate - seconds(3)
        try:
            sys.setprofile(delay)
            c._slot(penultimate)
        finally:
            sys.setprofile(previous)
        assert returned and returned[-1].action == "entry"
        assert penultimate in env.comp.driver.callback.seen
        assert c.status().last_tick.status == "blocked"
        assert "MANAGED_DEADLINE_REACHED" in c.status().last_tick.reasons
        assert c.status().management_deadline_recorded and c.status().management_request_id
        assert len([item for item in env.protection.inspect().outbox if item.kind == "request_management_approval"]) == 1
        assert c._controller.states() == () and env.adapter.requests == []


def _unknown_references():
    return PS.LedgerReferences(account_head_sha256=None, orders_head_sha256=None, risk_head_sha256=None,
                               high_water_sha256=None, floor_sha256=None, halt_sha256=None,
                               source_evidence_sha256=None)


def _record_initial_management_event(env, kind):
    with env.protection.session() as writer:
        state = writer.snapshot().state
        event = ManagementEvent(sequence=state.sequence + 1, previous_state_sha256=state_digest(state),
                                at=env.fake.now, kind=kind)
        return writer.commit(event, authority=None, observations=None, ledger_refs=_unknown_references())


def test_slow_failed_protection_commit_cannot_discard_the_final_original_quote():
    with fixture() as env:
        def slow_failure(*args):
            env.fake.now += seconds(11)
            raise RuntimeError("PRIVATE-SLOW-STORE")
        with patch.object(env.protection.head, "compare_and_set", slow_failure):
            status = env.c.run()
        assert len(env.comp.history._slots) == 5
        row = json.loads(history_journal(env.home, env.window).read_bytes().splitlines()[-1])
        assert row["data"]["receipt"]["sha256"] == env.books.original[-1].receipt.sha256
        assert env.window.end not in env.comp.driver.callback.seen
        assert not status.management_deadline_recorded and status.management_source
        assert env.adapter.requests == [] and "PRIVATE-SLOW" not in repr(status)


def test_closed_management_does_not_append_restart_or_deadline_records_on_each_monitor():
    with fixture() as env:
        closed = _record_initial_management_event(env, "close")
        status = env.c.run()
        after = env.protection.inspect()
        assert after.head == closed.head and after.journal_sequence == closed.journal_sequence == 1
        assert after.state.phase == "closed" and after.state.renewal_request_id is None
        assert status.management_source == "COORDINATOR_MANAGEMENT_CLOSED"
        assert not status.management_deadline_recorded and status.management_request_id is None
        assert env.adapter.requests == []


def test_existing_management_history_records_one_restart_and_reuses_the_durable_request():
    with fixture() as env:
        _record_initial_management_event(env, "assessment")
        status = env.c.run()
        after = env.protection.inspect()
        assert after.journal_sequence == 2 and after.state.recovering
        assert len([effect for effect in after.outbox if effect.kind == "reconcile"]) == 1
        requests = [effect for effect in after.outbox if effect.kind == "request_management_approval"]
        assert len(requests) == 1 and status.management_request_id == requests[0].intent_id
        assert not after.state.can_enter and not after.state.can_reduce
        assert env.c._management_deadline(env.fake.now + seconds(20))
        assert env.protection.inspect().head == after.head and env.adapter.requests == []
