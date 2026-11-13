"""Windows coordinator: one account provider, serialized units, a cancellable schedule and the owned composition.

Explicit operation only. Import and construction read no clock, account, quote, head or journal, start no thread
and install no signal handler; run() works on the caller's thread until the schedule ends or close() is called.
There is no transport here: the account producer, the trusted heads, the quote source and the history adapter
arrive already constructed, and the only supported mode is "rehearsal" (exact DryRunAdapters over an isolated
state root, checked by runner.py). "controlled" is refused: the shipped interval producer is flat-only
(account_interval.py), so a filled entry would stop the account chain before the position could be managed.

A unit of work (startup, monitor, boundary, gap, slot, or an explicit cancel/exit) loads the checkpoint behind the
trusted head, runs the account prefetch, picks its time only after every fetch has finished, publishes exactly one
immutable frame that every provider call inside the unit sees (so same-tick redelivery advances the head once),
then does its control work; one work lock serializes units and operator calls. A slot unit reads the book at
prefetch_lead_seconds before the slot and only then runs the account capture, which may end inside the slot's
10 s window; it samples the book at or after the slot (received by the slot, at most 10 s old at sampling),
records it in the history adapter and feeds the Runner one prefetched timestamp, all by slot + 10 s, with the
account at most 30 s old and never newer than sampling. Monitors sit on the slot grid (window.start plus multiples
of monitor_seconds, strictly after the run start), so no monitor unit starts inside a slot's lead. Construction
refuses a slot within BOUNDARY_BAND of a Seoul midnight or, with a recovery condition, of 22:00 KST, so the
boundary unit alone handles a boundary; run() refuses a start less than STARTUP_BUDGET before the first slot's
prefetch, and a chain whose cutoff convention disagrees with the profile's recovery condition. The timer waits on
the cancel event in steps of at most one second and re-reads the injected wall clock after each, so a Windows
suspend shows up as skipped deadlines: a late slot is never run, moved or re-run, a late boundary is reported as
missed, and a gap unit reconciles before the next decision. A boundary capture is attempted exactly once, at
boundary_lead_seconds before the boundary; it spans the boundary only when the capture lasts longer than the lead
(the producer's own window and rules decide). The shortest Upbit capture, 9 requests, lasts at least 1.8 s because
the transport pauses 0.2 s after each one, so at the default lead of 1 s a boundary unit that starts on time spans
the boundary whenever its first reply lands within about 1 s (R19). compose() is the owned wiring of the reviewed
artifacts: loader -> make_fixed_driver with the history callables -> LiveHistory.bind -> ReviewVerifiers over
CurrentOwnerAuthority -> EvidencePackage.

Ceilings (ponytail): operator calls block on the work lock for at most one unit, which is bounded by the
dependencies' own timeouts; a slot's account capture must end with the book still inside its 10 s bound and the
history verified by slot + 10 s, that is about min(prefetch_lead_seconds + 5.5 s, 10 s - the book's stamp lag) of
capture in real time (8.5 s at lead 3, about 9 s at lead 8 with a stamp 1 s before the receipt), and a longer capture
loses the slot, which ends every later slot of the window because the history never backfills (monitoring
continues); nothing here retries a capture, a send or a boundary. Nothing here signs, arms, orders, reads
credentials or writes a file of its own.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from fractions import Fraction
import heapq
import re
import threading
from types import MappingProxyType
from typing import Callable, Iterable, Iterator, Mapping

from core.compliance.alerts import toast
from core.compliance.model import KST
from core.compliance.rules import universe_top_n
from core.isolation import state_root
from execution_accounts.baseline_bridge import BaselineFrame, ContinuousAccountProvider
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.instrument_terms import within_buy_cap
from execution_accounts.universe import TickerRead
from execution_control.capability import digest
from execution_control.controller import Controller, OrderState
from execution_control.dry_run import DryRunAdapter
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_control.store import Journal, JournalError
from execution_control.universe_odds import run_batch
from execution_launch.baseline_head import BaselineHead
from execution_launch.committed_account import CommittedAccountProvider
from execution_launch.committed_producer import CommittedAccountProducer
from execution_launch.driver import (DeploymentWindow, FixedDriverError, FixedDriverIdentity, describe_fixed_driver,
                                     make_fixed_driver, make_fixed_carry_driver)
from execution_launch.live_history import HistoryChain, LiveHistory, SlotUniverse
from execution_launch.history_storage import (HistoryStoragePolicy, MAX_POLICY_BYTES, parse_policy, policy_digest)
from execution_launch.instrument_refresh import renew_profile
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.profile import LaunchProfile, parse_profile_json, profile_contract_digest, risk_policy
from execution_launch.program import ProgramSpec, parse_program
from execution_launch.managed_behavior import resolve_behavior
from execution_launch.protective_state import ManagementEvent, policy_digest as management_policy_digest, state_digest
from execution_launch.protective_store import LedgerReferences, ProtectiveStore
from execution_launch.review_auth import MAX_DOCUMENT_BYTES, ReviewVerifiers
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult, active,
                                     dust, flat_in, prepare_launch_session)
from execution_launch.strategy import ForwardProtocol, evaluate_capture_json, parse_protocol, evidence_digest
from execution_launch.toast_queue import ToastQueue
from execution_launch.workflow import MAX_CAPTURE_BYTES, MAX_CONFIG_BYTES, artifact, read_file

SLOT_WINDOW = timedelta(seconds=10)      # the driver's execution slot and the quote freshness bound
ACCOUNT_AGE = timedelta(seconds=30)      # the runner's and the reducer's account freshness bound
BOUNDARY_BAND = 2 * SLOT_WINDOW          # calibration: no slot this close to a boundary, so the slot unit's tail
                                         # (its 10 s window plus the tick) and the boundary unit never overlap
MONITOR_UNIT_SECONDS = 5                 # calibration floor: one monitor unit (a capture plus load_context) fits
                                         # between a monitor and the next slot's prefetch
# ponytail: STARTUP_BUDGET is the knob; 15 s is about twice a measured startup unit with one transport retry (an
# 11-read capture of 2.2-3.3 s, a 2.2 s retry, load_context 1.4 s, the commit). Raise it for a slower link.
STARTUP_BUDGET = timedelta(seconds=15)   # the least time between run() and the first slot's prefetch
TERMS_REFRESH_AGE = timedelta(minutes=4)  # reobserve before the existing five-minute expiry
MAX_WAIT_SECONDS = 1.0                   # re-read the wall clock at least once a second (Windows suspend)
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
_RANK = {"boundary": 0, "slot": 1, "monitor": 2}
_KNOBS = {"monitor_seconds": (5, 20), "prefetch_lead_seconds": (1, 8), "boundary_lead_seconds": (1, 10)}
UNIVERSE_KIND = "universe_top1_momentum"  # the reviewed program kind of a universe profile (PR 4b)
UNIVERSE_WINDOW_MAX = timedelta(hours=72)  # spec section 10: the never-pruned renewal registry bounds the window
PRICE_AGE = timedelta(seconds=60)         # a ticker price is defined within 60 s of the slot (PR 4d PRICE_WINDOW_MS)


class CoordinatorError(ValueError):
    """Fixed UPPER_SNAKE codes only; never amounts, scopes, paths or upstream text."""


def _require(ok, code):
    if not ok:
        raise CoordinatorError(code)


def _aware(value):
    return type(value) is datetime and value.utcoffset() is not None


def _code(exc, default):
    """The fixed code of a known refusal type, else a coordinator code; upstream text never passes."""
    code = getattr(exc, "code", None)
    code = code if type(code) is str else str(exc)
    if isinstance(exc, ValueError) and type(exc) is not ValueError and _CODE.fullmatch(code) is not None:
        return code
    if isinstance(exc, JournalError):
        return "COORDINATOR_JOURNAL_REFUSED"
    return "COORDINATOR_CONTROL_REFUSED" if type(exc) is ValueError else default


def reconcile_orders(runner: Runner, now: datetime) -> int:
    """Public alias of Runner._reconcile; runner.py is a fixed-driver source file, so the alias lives here."""
    return runner._reconcile(now)


def history_head_name(window: DeploymentWindow) -> str:
    """The live-history head's directory name for one deployment window (lowercase, one head per window)."""
    return "live-history-" + digest(window)[:16]




def held_coins(account, minimum) -> tuple[str, ...]:
    """The held coins of one account capture (spec section 7): non-dust holdings, the largest value at its mark
    first, equal values by symbol."""
    held = [p for p in account.positions if not dust(p, minimum)]
    return tuple(p.symbol for p in sorted(held, key=lambda p: (-(Fraction(p.units) * Fraction(p.price)), p.symbol)))


def universe_state(snapshot, rule_sha256, at) -> str:
    """The status word for a snapshot at `at`: no_snapshot (none, or not in force), rule_mismatch or in_force."""
    if snapshot is None or not snapshot.valid_from <= at < snapshot.valid_until:
        return "no_snapshot"
    return "in_force" if snapshot.rule_sha256 == rule_sha256 else "rule_mismatch"




def choose_trade_coin(held, current, decided, flat) -> str:
    """Spec section 7, rules 1 to 3: the one held coin; with two or more, the trade coin if held, else the largest
    (the caller blocks buys); with none, the decided coin while flat in the trade coin, else the trade coin."""
    if len(held) == 1:
        return held[0]
    if held:
        return current if current in held else held[0]
    return decided if decided is not None and flat else current




def slot_allow(*, snapshot, rule_sha256, n, flags, tickers, slot, blocks=()) -> tuple[frozenset, tuple[str, ...]]:
    """Spec section 7: the slot's buy allow-list and buy-block reasons. The list is the top-N of the snapshot in force
    that are unflagged in this slot's flag read and priced within PRICE_AGE of the slot in its ticker read; it is
    empty when any reason is set."""
    reasons = tuple(blocks)
    state = universe_state(snapshot, rule_sha256, slot)
    if state != "in_force":
        reasons += ("UNIVERSE_NO_SNAPSHOT" if state == "no_snapshot" else "UNIVERSE_RULE_MISMATCH",)
    if not flags.ok:
        reasons += ("UNIVERSE_FLAGS_UNAVAILABLE",)
    if not tickers.ok:
        reasons += ("UNIVERSE_TICKERS_UNAVAILABLE",)
    if reasons:
        return frozenset(), reasons
    return frozenset(m for m in universe_top_n(snapshot, n) if flags.flags.get(m) == "unflagged"
                     and m in tickers.prices and abs(tickers.prices[m][1] - slot) <= PRICE_AGE), ()


def _check_protective_binding(store, identity, profile, evidence, window, monitor_until):
    """P2 context commitments only; actual current owner code/research verification stays in ReviewVerifiers.

    policy.code_sha256 is this factory's source closure, not the owner's whole-code approval hash.
    source_sha256 binds the evaluated research inputs; it is not a claim about live account provenance.
    """
    _require(type(store) is ProtectiveStore and type(identity) is FixedDriverIdentity,
             "COORDINATOR_PROTECTIVE_STORE_REQUIRED")
    policy, binding = store.policy, store.binding
    management_policy_digest(policy)
    binding.__post_init__()
    _require(resolve_behavior(evidence.protocol) == "protective-carry-v2"
             and identity.factory_id == "tradegen-fixed-carry-v2"
             and (policy.account_scope, policy.venue, policy.market, policy.quote_currency, policy.symbol)
             == (profile.account_scope, profile.venue, profile.market, profile.quote_currency, profile.symbol)
             and policy.holding_deadline == window.end and policy.monitor_until == monitor_until
             and policy.code_sha256 == identity.deployment_code_sha256
             and policy.strategy_sha256 == evidence.protocol.strategy_code_sha256
             and policy.risk_policy_sha256 == digest(risk_policy(profile))
             and binding.driver_identity_sha256 == digest(identity)
             and binding.research_sha256 == evidence_digest(evidence.result)
             and binding.source_sha256 == evidence.result.inputs_digest,
             "COORDINATOR_PROTECTIVE_BINDING_MISMATCH")


@dataclass(frozen=True, kw_only=True)
class Due:
    kind: str                       # boundary, slot or monitor
    at: datetime                    # earliest start
    deadline: datetime              # latest start; a later item is skipped, never run late
    slot: datetime | None = None    # the slot time, or the boundary instant


def _boundaries(first: datetime, last: datetime, cutoff_seconds: int | None) -> Iterator[datetime]:
    """Every Seoul midnight and, with a cutoff, every 22:00 KST (midnight plus cutoff_seconds) in [first, last]."""
    day = first.astimezone(KST).date() - timedelta(days=1)       # so a midnight equal to `first` is yielded too
    while True:
        opening = datetime.combine(day, time(), tzinfo=KST)
        instants = [opening + timedelta(days=1)]
        if cutoff_seconds is not None:
            instants.append(opening + timedelta(seconds=cutoff_seconds))
        for instant in sorted(instants):
            if first <= instant <= last:
                yield instant
        if instants[0] > last:
            return
        day += timedelta(days=1)


def schedule(*, window: DeploymentWindow, bar_seconds: int, start: datetime, monitor_until: datetime,
             monitor_seconds: int, prefetch_lead_seconds: int, boundary_lead_seconds: int,
             cutoff_seconds: int | None) -> Iterator[Due]:
    """Slots (prefetch lead before each slot at or after start), monitors (window.start + k * monitor_seconds,
    strictly after start, up to monitor_until) and boundaries (each Seoul midnight and, with a cutoff, each 22:00
    in (start, monitor_until]), merged lazily."""
    step, lead, monitor = timedelta(seconds=bar_seconds), timedelta(seconds=prefetch_lead_seconds), timedelta(seconds=monitor_seconds)

    def slots():
        for index in range((window.end - window.start) // step + 1):
            slot = window.start + index * step
            if slot >= start:
                yield Due(kind="slot", at=slot - lead, deadline=slot, slot=slot)

    def monitors():
        count = (start - window.start) // monitor + 1
        while window.start + count * monitor <= monitor_until:
            at = window.start + count * monitor
            yield Due(kind="monitor", at=at, deadline=at + monitor)
            count += 1

    def boundaries():
        for boundary in _boundaries(start, monitor_until, cutoff_seconds):
            if boundary > start:
                yield Due(kind="boundary", at=boundary - timedelta(seconds=boundary_lead_seconds),
                          deadline=boundary, slot=boundary)
    return heapq.merge(boundaries(), slots(), monitors(), key=lambda due: (due.at, _RANK[due.kind]))


class CancellableTimer:
    """Iterator over sorted Due items: an item is returned once its start has come, skipped and counted once its
    deadline has passed; cancel.set() ends the iteration within one wait. The wait is on the cancel event and
    capped at max_wait_seconds, and the injected wall clock is re-read after every wait."""
    def __init__(self, items: Iterable[Due], *, clock: Callable[[], datetime], cancel: threading.Event,
                 wait: Callable[[threading.Event, float], bool] = threading.Event.wait,
                 max_wait_seconds: float = MAX_WAIT_SECONDS) -> None:
        self._items, self._clock, self._cancel, self._wait = iter(items), clock, cancel, wait
        self._max, self._pending = max_wait_seconds, None
        self._missed = {"boundary": 0, "slot": 0, "monitor": 0}

    def __iter__(self) -> "CancellableTimer":
        return self

    def __next__(self) -> Due:
        while True:
            if self._cancel.is_set():
                raise StopIteration
            if self._pending is None:
                self._pending = next(self._items)
            item = self._pending
            now = self._clock()
            _require(_aware(now), "COORDINATOR_CLOCK_INVALID")
            if now > item.deadline:
                self._missed[item.kind] += 1
                self._pending = None
                continue
            if now >= item.at:
                self._pending = None
                return item
            self._wait(self._cancel, min((item.at - now).total_seconds(), self._max))

    @property
    def missed(self) -> dict[str, int]:
        return dict(self._missed)


@dataclass(frozen=True, kw_only=True)
class CoordinatorStatus:
    """Immutable, sanitized: fixed codes, counts, instants and the Controller's order states; never equity, scope,
    paths or upstream text."""
    phase: str = "new"                  # new, running, monitoring or closed
    strategy_stopped: bool = False
    in_flight: str = ""                 # "", account_source, quote_source, history or control
    published_units: int = 0            # units whose frame reached the provider
    account_source: str = ""            # the last account step's failure code; "" after a success
    account_asof: datetime | None = None
    instrument_source: str = ""        # current-term renewal failure, independently visible
    instrument_asof: datetime | None = None
    new_entry_blocked: bool = True
    risk_reasons: tuple[str, ...] = ()
    recovery_status: str | None = None
    recovery_deadline: datetime | None = None
    last_tick: TickResult | None = None
    missed_slots: int = 0
    missed_boundaries: int = 0
    data_gap_at: datetime | None = None
    orders: tuple[OrderState, ...] = ()
    reasons: tuple[str, ...] = ()       # the last slot tick's reasons, or the last refused slot or control step
    held_symbol: str | None = None      # universe: the largest held coin of the last published frame
    trade_symbol: str | None = None     # universe: profile.symbol, the coin whose rules are current
    snapshot_day: date | None = None    # universe: the snapshot of the last monitor
    snapshot_sha256: str | None = None
    universe_state: str | None = None   # universe: in_force, no_snapshot or rule_mismatch
    held_flag: str | None = None        # universe: the held coin's class in the last slot's flag read
    allow_count: int = 0                # universe: the size of the last slot's buy allow-list
    buy_block_reasons: tuple[str, ...] = ()
    disarm_failed: bool = False         # sticky: the universe disarm recorded no system disarm
    notification_failed: bool = False   # sticky local enqueue failure, never delivery or approval evidence
    management_deadline_recorded: bool = False  # narrow P2 deadline bridge, not reconciliation or authority
    management_request_id: str | None = None
    management_source: str = ""          # fixed failure code; no storage paths or unverified request success
    window_ended_missed_slot: bool = False  # sticky: a slot the history did not record ended the window


@dataclass(frozen=True, kw_only=True)
class DisarmResult:
    local_strategy_stopped: bool = True
    session_prepared: bool
    journal_kill_written: bool
    owner_disarm_recorded: bool
    venue_orders_cancelled: bool = False
    positions_liquidated: bool = False
    pending: bool = False


class _TickBoard:
    """Internal: the one published frame and book of the unit in progress; the provider's source and the Runner's
    quote provider read only from here, so nothing is fetched after the tick time is chosen."""
    def __init__(self) -> None:
        self._frame, self._book = None, None

    def publish(self, frame, book) -> None:
        self._frame, self._book = frame, book

    def clear(self) -> None:
        self._frame, self._book = None, None

    def account_frame(self, previous, now):
        frame = self._frame
        _require(frame is not None and frame.interval.end <= now, "COORDINATOR_NO_PUBLISHED_TICK")
        return frame

    def quote(self, now):
        _require(self._book is not None, "COORDINATOR_NO_PUBLISHED_TICK")
        from execution_accounts.quotes import to_runner_quote
        return to_runner_quote(self._book, now=now)


class Coordinator:
    """Own the legacy frame runtime, or adopt one explicit committed producer runtime.

    The committed branch has no provider/Controller/Runner until actual startup
    reconciliation. It creates a separate launch Runner over that same runtime;
    neither publication nor history advances the committed baseline again.
    """
    def __init__(self, *, mode: str, profile: LaunchProfile, evidence: EvidencePackage, driver: StrategyDriver,
                 implementation_verifier: Callable, adapters: Mapping[str, object], account_source: Callable | None,
                 trusted_head: object, quote_source: object, window: DeploymentWindow, bar_seconds: int,
                 monitor_until: datetime, clock: Callable[[], datetime], account_prefetch: Callable | None = None,
                 history: object | None = None, terms_source: object | None = None,
                 monitor_seconds: int = 10, prefetch_lead_seconds: int = 3,
                 boundary_lead_seconds: int = 1,     # calibration (R19): under the shortest capture's 1.8 s (9
                                                     # requests, 0.2 s pace each), leaving ~1 s for the first reply
                 wait: Callable[[threading.Event, float], bool] = threading.Event.wait,
                 slot_source: object | None = None, program: object | None = None,
                 toast: Callable[[str, str], bool] = toast,
                 protective_store: ProtectiveStore | None = None,
                 committed_producer: CommittedAccountProducer | None = None) -> None:
        _require(mode == "rehearsal", "COORDINATOR_MODE_UNSUPPORTED")
        _require(type(profile) is LaunchProfile and (profile.venue, profile.market, profile.quote_currency)
                 == ("upbit", "spot", "KRW"), "COORDINATOR_VENUE_UNSUPPORTED")
        _require(type(evidence) is EvidencePackage and type(driver) is StrategyDriver
                 and all(callable(f) for f in (clock, wait, implementation_verifier, toast))
                 and (callable(account_source) if committed_producer is None else account_source is None)
                 and (account_prefetch is None or callable(account_prefetch))
                 and callable(getattr(quote_source, "read", None)) and callable(getattr(trusted_head, "read", None))
                 and (history is None or callable(getattr(history, "record_slot", None)))
                 and (terms_source is None or callable(getattr(terms_source, "read", None))),
                 "COORDINATOR_INTEGRATIONS_REQUIRED")
        if committed_producer is not None:
            _require(type(committed_producer) is CommittedAccountProducer and account_prefetch is None,
                     "COORDINATOR_COMMITTED_INTEGRATIONS_REQUIRED")
            _require(profile.universe_rule_sha256 is None, "COORDINATOR_COMMITTED_FIXED_REQUIRED")
        universe = profile.universe_rule_sha256 is not None    # spec section 10: a universe launch profile
        carry = resolve_behavior(evidence.protocol) == "protective-carry-v2"
        _require(not universe or (callable(getattr(slot_source, "read_flags", None))
                                  and callable(getattr(slot_source, "read_tickers", None))
                                  and terms_source is not None
                                  and callable(getattr(history, "decided_symbol", None))
                                  and getattr(program, "kind", None) == UNIVERSE_KIND
                                  and getattr(program, "universe_rule_sha256", None) == profile.universe_rule_sha256
                                  and type(getattr(program, "max_candidates", None)) is int
                                  and program.max_candidates >= 1),
                 "COORDINATOR_INTEGRATIONS_REQUIRED")
        knobs = {"monitor_seconds": monitor_seconds, "prefetch_lead_seconds": prefetch_lead_seconds,
                 "boundary_lead_seconds": boundary_lead_seconds}
        _require(all(type(value) is int and _KNOBS[name][0] <= value <= _KNOBS[name][1] for name, value in knobs.items())
                 and type(bar_seconds) is int and bar_seconds >= 20 and _aware(monitor_until),
                 "COORDINATOR_SCHEDULE_INVALID")
        _require(type(window) is DeploymentWindow and _aware(window.start) and _aware(window.end),
                 "COORDINATOR_WINDOW_INVALID")
        step, span = timedelta(seconds=bar_seconds), window.end - window.start
        _require(span > timedelta(0) and span % step == timedelta(0) and 2 <= span // step + 1 <= 20000,
                 "COORDINATOR_WINDOW_INVALID")
        _require(not universe or span <= UNIVERSE_WINDOW_MAX, "COORDINATOR_WINDOW_INVALID")
        _require(bar_seconds % monitor_seconds == 0 and monitor_seconds - prefetch_lead_seconds >= MONITOR_UNIT_SECONDS,
                 "COORDINATOR_SCHEDULE_INVALID")              # monitors on the slot grid; one monitor unit per lead
        try:
            identity = describe_fixed_driver(driver)
        except FixedDriverError as exc:
            if str(exc) != "FIXED_DRIVER_NOT_ISSUED":
                raise
            identity = None                                  # a fixture driver: rehearsal only, no history needed
        if identity is not None:
            _require(history is not None, "COORDINATOR_HISTORY_REQUIRED")
            _require(digest(window) == identity.deployment_window_digest
                     and bar_seconds == getattr(evidence.protocol, "bar_seconds", None),
                     "COORDINATOR_WINDOW_BINDING_MISMATCH")
        _require(window.end <= monitor_until <= window.end + timedelta(days=1), "COORDINATOR_MONITOR_SPAN_UNSUPPORTED")
        _require(not carry or (identity is not None and type(protective_store) is ProtectiveStore),
                 "COORDINATOR_PROTECTIVE_STORE_REQUIRED")
        _require(carry or protective_store is None, "COORDINATOR_PROTECTIVE_BEHAVIOR_UNSUPPORTED")
        if carry:
            _check_protective_binding(protective_store, identity, profile, evidence, window, monitor_until)
        policy = risk_policy(profile)
        cutoff = None if policy.recovery_condition is None else policy.recovery_condition.cutoff_seconds
        if cutoff is not None:
            boundary = datetime.combine(window.end.astimezone(KST).date(), time(), tzinfo=KST) + timedelta(seconds=cutoff)
            _require(window.end >= boundary or monitor_until >= boundary + timedelta(seconds=monitor_seconds),
                     "COORDINATOR_MONITOR_ENDS_BEFORE_CUTOFF")
        for boundary in _boundaries(window.start - BOUNDARY_BAND, window.end + BOUNDARY_BAND, cutoff):
            index = (boundary - window.start) // step                 # the grid points around the boundary (the
            for slot in (window.start + (index + k) * step for k in (-1, 0, 1)):   # one before it when it is on the grid)
                _require(not (window.start <= slot <= window.end and abs(slot - boundary) <= BOUNDARY_BAND),
                         "COORDINATOR_SLOT_NEAR_BOUNDARY")
        root = state_root().absolute()
        self._committed_producer = committed_producer
        self._committed_unit, self._committed_account = None, None
        self._committed_reconciliation = None
        self._committed_root = root
        self._committed_adapters = None if committed_producer is None else dict(adapters)
        self._committed_contract = profile_contract_digest(profile) if committed_producer is not None else None
        self._committed_policy = digest(policy) if committed_producer is not None else None
        if committed_producer is None:
            self._store = CheckpointStore(root=root)                              # path metadata only
            self._board = _TickBoard()
            self._provider = ContinuousAccountProvider(source=self._board.account_frame, store=self._store,
                                                       trusted_head=trusted_head)
            self._journal = Journal()                                             # path checks only
            self._controller = Controller(journal=self._journal, account_provider=self._provider, policy=policy,
                                          adapters=adapters, session_provider=self._session_for)
            self._runner = Runner(profile=profile, quote_provider=self._board.quote, account_provider=self._provider,
                                  evidence=evidence, driver=driver, implementation_verifier=implementation_verifier,
                                  mode=mode, controller=self._controller, launch_session=None, isolated_state_root=root,
                                  clock=self._now if carry else None,
                                  deadline_record=self._management_deadline if carry else None)
        else:
            _require(set(self._committed_adapters) == {"upbit"}
                     and type(self._committed_adapters["upbit"]) is DryRunAdapter,
                     "COORDINATOR_COMMITTED_REHEARSAL_REQUIRED")
            self._store, self._journal = committed_producer._baseline_store, committed_producer._journal
            self._board = _TickBoard()
            self._provider, self._controller, self._runner = None, None, None
        self._profile, self._evidence, self._driver = profile, evidence, driver
        self._implementation_verifier, self._head = implementation_verifier, trusted_head
        self._account_source, self._account_prefetch = account_source, account_prefetch
        self._quote_source, self._history, self._window = quote_source, history, window
        self._terms_source, self._terms_blocked = terms_source, False
        self._pending_terms = None
        self._bar_seconds, self._monitor_until, self._cutoff = bar_seconds, monitor_until, cutoff
        self._clock, self._wait, self._knobs = clock, wait, knobs
        self._work, self._status_lock = threading.Lock(), threading.Lock()
        self._stopping, self._closing, self._finished = threading.Event(), threading.Event(), threading.Event()
        self._started, self._ready, self._phase = False, False, "new"
        self._last_time, self._observation, self._launch, self._published = None, None, None, 0
        self._latest_frame = None
        self._status = CoordinatorStatus()
        self._universe, self._slot_source, self._program = universe, slot_source, program
        self._carry, self._protective_store, self._driver_identity = carry, protective_store, identity
        self._toasts, self._toasted = ToastQueue(toast), set()        # spec section 15: queued, deduped here
        self._snapshot, self._held, self._extra = None, None, False   # _held None: no frame read yet
        self._vanished, self._disarmed, self._terms_unavailable = False, False, False
        self._remainder_ticks, self._remainder = 0, False
        self._within_cap = True                 # PR 4c: the trade coin's last terms read is within its v2 buy cap
        self._committed_session_provider = self._session_for
        if committed_producer is not None:
            self._committed_configuration()
            committed_producer._bind_startup(session_provider=self._committed_session_provider)

    def _committed_configuration(self):
        """Check actual pinned composition, never a caller-supplied readiness claim."""
        producer = self._committed_producer
        _require(type(producer) is CommittedAccountProducer, "COORDINATOR_COMMITTED_BINDING_CHANGED")
        producer._configuration()
        _require(producer._root == self._committed_root == state_root().absolute()
                 and producer._baseline_store is self._store and producer._baseline_head is self._head
                 and producer._journal is self._journal and producer._clock is self._clock
                 and profile_contract_digest(producer._profile) == self._committed_contract
                 and profile_contract_digest(self._profile) == self._committed_contract
                 and digest(risk_policy(producer._profile)) == self._committed_policy
                 and digest(risk_policy(self._profile)) == self._committed_policy
                 and set(producer._adapters) == set(self._committed_adapters) == {"upbit"}
                 and all(producer._adapters[key] is value and type(value) is DryRunAdapter
                         for key, value in self._committed_adapters.items()),
                 "COORDINATOR_COMMITTED_BINDING_CHANGED")
        if self._runner is not None:
            provider, controller, journal = producer._runtime_components()
            _require(type(provider) is CommittedAccountProvider and type(controller) is Controller
                     and provider is self._provider and controller is self._controller and journal is self._journal
                     and controller.journal is journal and controller.account_provider is provider
                     and controller._completion_clock is self._clock
                     and controller.session_provider is self._committed_session_provider
                     and set(controller.adapters) == set(self._committed_adapters)
                     and all(controller.adapters[key] is value for key, value in self._committed_adapters.items())
                     and self._runner.account_provider is provider and self._runner.controller is controller,
                     "COORDINATOR_COMMITTED_BINDING_CHANGED")
            self._runner._controller_boundary()

    def _adopt_committed_runtime(self):
        self._committed_configuration()
        if self._runner is not None:
            return
        provider, controller, journal = self._committed_producer._runtime_components()
        _require(type(provider) is CommittedAccountProvider and type(controller) is Controller
                 and journal is self._journal and controller.journal is journal
                 and controller.account_provider is provider and controller._completion_clock is self._clock
                 and controller.session_provider is self._committed_session_provider,
                 "COORDINATOR_COMMITTED_BINDING_CHANGED")
        # The startup Runner and its initial binding remain untouched. This is
        # the launch consumer of the same genuinely reconciled runtime.
        runner = Runner(profile=self._profile, quote_provider=self._board.quote, account_provider=provider,
                        evidence=self._evidence, driver=self._driver,
                        implementation_verifier=self._implementation_verifier, mode="rehearsal",
                        controller=controller, launch_session=None, isolated_state_root=self._committed_root,
                        clock=self._now if self._carry else None,
                        deadline_record=self._management_deadline if self._carry else None)
        self._provider, self._controller, self._runner = provider, controller, runner
        if self._stopping.is_set():
            runner.stop()
        self._committed_configuration()

    def _committed_completion(self, completed_at):
        _require(_aware(completed_at) and (self._last_time is None or completed_at >= self._last_time),
                 "COORDINATOR_CLOCK_ROLLBACK")
        self._last_time = completed_at

    def _current_committed(self, now):
        self._ready = False
        self._committed_configuration()
        _require(self._runner is not None and self._committed_unit is not None,
                 "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
        pair, account, result = self._committed_producer._current_unit(self._committed_unit, now=now)
        self._committed_completion(pair.completed_at)
        self._committed_configuration()
        _require(result.final_control_head == pair.committed.observed_control_head
                 and pair.committed.transaction_id == self._committed_unit.transaction_id,
                 "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
        self._committed_reconciliation = result
        self._ready = (result.status in ("RECONCILED", "RECONCILED_OPEN")
                       and not result.unresolved_client_ids and not result.external_order_ids)
        self._observation, self._committed_account = pair.account, account
        return pair


    # -- status ------------------------------------------------------------------------------------------------

    def status(self) -> CoordinatorStatus:
        with self._status_lock:
            return self._status

    def _update(self, **changes) -> None:
        with self._status_lock:
            self._status = replace(self._status, phase=self._phase,
                                   strategy_stopped=self._stopping.is_set() or (self._runner is not None and self._runner.stopped)
                                   or changes.get("window_ended_missed_slot", self._status.window_ended_missed_slot),
                                   **changes)

    def _refused(self, stage, code, *, slot) -> None:
        """An account-step failure is kept apart from risk and order state; a slot's outcome is in `reasons`."""
        changes = {}
        if self._committed_producer is not None and stage in ("account", "control"):
            self._ready = False
        if stage == "account":
            changes.update(account_source=code, new_entry_blocked=True)
        if stage == "control":
            changes["new_entry_blocked"] = True
        if slot or stage == "control":
            changes["reasons"] = (code,)
        self._update(**changes)


    def _toast_once(self, key, level, body) -> None:
        """Queue one coordinator toast (spec section 15) unless `key` was already toasted in this window; keys carry
        the Seoul date where the dedupe is once per day."""
        if key not in self._toasted:
            self._toasted.add(key)
            try:
                self._toasts.put("TRADEGEN universe " + level, body)
            except Exception:
                # A notification channel cannot veto evidence, reconciliation or a durable disarm.
                # Keep failure visible without copying transport text, inferring delivery, or retrying an action.
                self._update(notification_failed=True)

    def _holding(self) -> bool:
        """True while a coin is held or the holdings are not known yet (no frame read): exits need fresh rules."""
        return self._held is None or bool(self._held)

    # -- the clock and the account step shared by every unit ---------------------------------------------------

    def _now(self):
        try:
            value = self._clock()
        except Exception:
            raise CoordinatorError("COORDINATOR_CLOCK_INVALID") from None
        _require(_aware(value), "COORDINATOR_CLOCK_INVALID")
        return value

    def _time(self):
        """A unit time: aware and never earlier than any previous one."""
        value = self._now()
        _require(self._last_time is None or value >= self._last_time, "COORDINATOR_CLOCK_ROLLBACK")
        self._last_time = value
        return value

    def _load_previous(self):
        try:
            previous = self._store.load(expected_head=self._head.read())
        except Exception:
            raise CoordinatorError("COORDINATOR_CHECKPOINT_REFUSED") from None
        _require((previous.conventions.recovery_cutoff_seconds is None) == (self._cutoff is None),
                 "COORDINATOR_CUTOFF_MISMATCH")                 # R15: every unit's load checks the cutoff agreement
        return previous

    def _prefetch(self, previous) -> None:
        self._update(in_flight="account_source")
        if self._committed_producer is not None:
            self._ready = False
            self._committed_configuration()
            unit = self._committed_producer._collect_current()
            self._committed_completion(unit.completed_at)
            self._adopt_committed_runtime()
            self._committed_unit = unit
            return
        if self._account_prefetch is not None:
            try:
                self._account_prefetch(previous)
            except Exception as exc:
                raise CoordinatorError(_code(exc, "COORDINATOR_ACCOUNT_SOURCE_FAILED")) from None

    def _read_book(self):
        self._update(in_flight="quote_source")
        try:
            return self._quote_source.read(self._profile.symbol) if self._universe else self._quote_source.read()
        except Exception as exc:
            raise CoordinatorError(_code(exc, "COORDINATOR_QUOTE_SOURCE_FAILED")) from None

    def _publish(self, previous, now, book):
        """Publish a legacy frame or revalidate the actual committed unit; never advance it twice."""
        if self._committed_producer is not None:
            pair = self._current_committed(now)
            self._board.publish(None, book)  # committed accounts are never read from the tick board
            self._published += 1
            self._held = held_coins(self._committed_account, self._profile.instrument_rules.min_notional_krw)
            self._update(published_units=self._published, account_source="", account_asof=pair.account.asof,
                         held_symbol=self._held[0] if self._held else None, trade_symbol=self._profile.symbol)
            return pair.account
        try:
            frame = self._account_source(previous, now)
        except Exception as exc:
            raise CoordinatorError(_code(exc, "COORDINATOR_ACCOUNT_SOURCE_FAILED")) from None
        _require(type(frame) is BaselineFrame and frame.interval.end <= now, "COORDINATOR_ACCOUNT_FRAME_INVALID")
        self._board.publish(frame, book)
        self._published += 1
        self._update(published_units=self._published)
        observation = self._provider(now)
        self._observation = observation
        self._latest_frame = frame
        self._update(account_source="", account_asof=observation.asof)
        return observation

    def _await(self, slot) -> None:
        """Wait for the slot on the stopping event, in capped steps, re-reading the wall clock after each."""
        while not self._stopping.is_set():
            remaining = (slot - self._now()).total_seconds()
            if remaining <= 0:
                return
            self._wait(self._stopping, min(remaining, MAX_WAIT_SECONDS))

    def _refresh_terms(self, symbol=None):
        """Called under the work lock, before account/quote timing for a unit. A universe profile reads the terms of
        `symbol` (another coin, after _universe_monitor's flat check) or of its trade coin (spec section 10)."""
        _require(self._terms_source is not None, "COORDINATOR_TERMS_SOURCE_REQUIRED")
        target = symbol or self._profile.symbol
        try:
            if self._pending_terms is None:
                observation = self._terms_source.read(target) if self._universe else self._terms_source.read()
                if self._universe:
                    # ponytail: follows the last read even if its renewal fails; buys are blocked while one is pending
                    self._within_cap = within_buy_cap(observation)
                now = self._time()             # actual receipt completes before the clock is chosen
                self._pending_terms = renew_profile(self._profile, observation, now=now,
                                                    allow_symbol_change=target != self._profile.symbol)
            else:
                target = self._pending_terms.profile.symbol
                now = self._time()             # retry the issued object; never fork from the old snapshot
            renewal = self._pending_terms
            frame = self._latest_frame
            if self._committed_producer is not None:
                self._committed_configuration()
                _require(self._runner is not None, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                account = self._committed_account
            else:
                account = None if frame is None else frame.accounts[0]
            self._runner.refresh_instrument_rules(renewal, now=now, account=account)
            self._profile = renewal.profile
            self._pending_terms = None
            self._launch = self._runner.launch_session  # same actual PreparedSession, updated wrapper only
            self._terms_blocked = self._terms_unavailable = False
            self._update(instrument_source="", instrument_asof=self._profile.instrument_rules.asof)
            return self._profile.instrument_rules.asof
        except Exception as exc:
            code = _code(exc, "COORDINATOR_TERMS_SOURCE_FAILED")
            if not self._universe or self._held is None:
                self._terms_blocked = True     # unknown holdings require current rules
            elif code == "TERMS_MARKET_INACTIVE" and target in self._held:
                self._vanished = True          # only the actual inquiry target can establish this event
            elif self._held:
                self._terms_blocked = True     # another market's failure is not evidence this holding vanished
            else:
                self._terms_unavailable = True  # no coin held: buys blocked only (TERMS_TARGET_UNAVAILABLE)
            self._update(instrument_source=code, new_entry_blocked=True)
            raise CoordinatorError(code) from None

    def _maybe_refresh_terms(self):
        if self._terms_source is None:
            return
        rules = self._profile.instrument_rules
        now = self._now()
        if (self._terms_blocked or self._terms_unavailable or self._pending_terms is not None or rules is None
                or rules.asof > now or now - rules.asof >= TERMS_REFRESH_AGE):
            self._refresh_terms()


    def _holdings(self, now) -> None:
        """After each universe _publish (spec section 7): the held coins of the new frame, the vanish latch (a coin
        held in the previous frame now marked unlisted at 0), the extra-holding block and its toast, and the
        unsellable-remainder reset once the trade coin is no longer held."""
        account = self._latest_frame.accounts[0]
        held = held_coins(account, self._profile.instrument_rules.min_notional_krw)
        if any(p.symbol in (self._held or ()) and p.price == 0 for p in account.positions):
            self._vanished = True
        self._held, self._extra = held, len(held) > 1
        if self._extra:
            self._toast_once("extra:" + now.astimezone(KST).date().isoformat(), "red",
                             "Two or more coins are held. Buys are blocked. Review management of the extra holding.")
        if self._profile.symbol not in held:
            self._remainder_ticks, self._remainder = 0, False
        self._update(held_symbol=held[0] if held else None, trade_symbol=self._profile.symbol)


    def _universe_monitor(self, now) -> None:
        """Spec section 7, in each monitor unit after _publish and the observe: choose the trade coin; for another
        coin, renew only while flat in the trade coin with no renewal pending (not flat is a normal outcome). Also
        the management-renewal notice at the window end; a deadline alone never submits an exit."""
        account, current = self._latest_frame.accounts[0], self._profile.symbol
        states = self._controller.states()
        flat = flat_in(current, account.positions, states, asof=account.observed_at,
                       minimum=self._profile.instrument_rules.min_notional_krw)
        choice = choose_trade_coin(self._held, current, self._history.decided_symbol(), flat)
        if not self._vanished and choice != current and flat and self._pending_terms is None:
            try:
                self._refresh_terms(choice)
            except CoordinatorError:
                pass                    # buys stay blocked (TERMS_TARGET_UNAVAILABLE); retried at the next monitor
        if now > self._window.end + SLOT_WINDOW and self._held and not any(active(s) for s in states):
            self._toast_once("window-end", "red",
                             "The management window ended with a holding. Request new management approval. "
                             "Existing permissions and loss protection remain in force; nothing is extended automatically.")
        self._update(trade_symbol=self._profile.symbol)


    def _events(self, flags, account, day) -> list:
        """Spec section 7, step 8: the (code, action) pairs this slot raises, in the table's order. Codes are
        recorded with the slot; the actions run after record_slot, each in its own try."""
        events = []
        if self._vanished:
            events.append(("UNIVERSE_MARKET_VANISHED", self._vanish))
        held = set(self._held or ())
        if flags.ok:
            warned = [p.symbol for p in account.positions
                      if p.symbol not in held and p.units > 0 and flags.flags.get(p.symbol) == "warning"]
            if warned:
                def warn():
                    for coin in warned:
                        self._toast_once("warning:" + coin + ":" + day, "red", coin + " has a market warning. Check the remaining balance, "
                                         "order minimum and available management options. No automatic top-up is performed.")
                events.append(("UNIVERSE_OTHER_COIN_WARNING", warn))
            if any(flags.flags.get(coin, "absent") in ("unknown", "absent") for coin in held):
                events.append(("UNIVERSE_HELD_FLAG_UNCERTAIN", lambda: self._toast_once(
                    "held-flag:" + day, "amber", "The held coin's flag is unknown or absent. No buy at this slot.")))
        return events

    def _vanish(self) -> tuple[str, ...]:
        """The vanish event (spec section 7): stop, then the lock-free disarm with reason market_vanished, once per
        window. A kill that records no system disarm counts as failed: sticky disarm_failed and a red toast."""
        if self._disarmed:
            return ()
        self._disarmed = True
        self.stop()
        try:
            result = self._disarm_locked(reason="market_vanished", code="COORDINATOR_UNIVERSE_DISARM",
                                         republish=False)
            failed = result.session_prepared and not result.owner_disarm_recorded
        except CoordinatorError:
            failed = True
        if failed:
            self._update(disarm_failed=True)
            self._toast_once("disarm-failed", "red", "The universe disarm did not complete. Disarm the session by "
                             "hand and handle the coin in the Upbit app.")
        else:
            self._toast_once("vanished", "red", "The held coin left the Upbit KRW market. The strategy is stopped. "
                             "Check the reported session disarm status and management options for the holding.")
        return ("COORDINATOR_UNIVERSE_DISARM",)

    def _after_tick(self, last, acted, day) -> None:
        """The unsellable-remainder event (spec section 7): the trade coin held, the decision the tick acted on
        another coin or cash, and a hold result (the whole sell under the minimum at its limit price), two ticks in a
        row. The block stays until the trade coin is no longer held (_holdings)."""
        if (last is not None and last.status == "hold" and acted != self._profile.symbol
                and self._profile.symbol in (self._held or ())):
            self._remainder_ticks += 1
        else:
            self._remainder_ticks = 0
        if self._remainder_ticks >= 2 and not self._remainder:
            self._remainder = True
            self._toast_once("remainder:" + day, "red", "The held coin's remainder is below the Upbit minimum. "
                             "Buys are blocked. Review its balance, order minimum and management options; "
                             "no top-up or liquidation is triggered by this notice.")

    def _management_deadline(self, now) -> bool:
        """Persist the due deadline before dependent dispatch; no fabricated authority, facts or ledger heads.

        Re-delivery only reads the independently verified existing request. Opening an existing
        writable lifecycle first records restart as P2 requires; that event is not account reconciliation.
        This method runs outside a Controller transaction and closes P2's writer before Runner work.
        """
        if not self._carry or now < self._window.end:
            return True
        try:
            _check_protective_binding(self._protective_store, self._driver_identity, self._profile,
                                      self._evidence, self._window, self._monitor_until)
            refs = LedgerReferences(account_head_sha256=None, orders_head_sha256=None, risk_head_sha256=None,
                                    high_water_sha256=None, floor_sha256=None, halt_sha256=None,
                                    source_evidence_sha256=None)
            with self._protective_store.session() as writer:
                snapshot = writer.snapshot()
                closed = snapshot.state.phase == "closed"
                if not closed and (not snapshot.state.deadline_seen or snapshot.state.renewal_request_id is None):
                    if snapshot.restart_required:
                        event = ManagementEvent(sequence=snapshot.state.sequence + 1,
                            previous_state_sha256=state_digest(snapshot.state), at=now, kind="restart")
                        snapshot = writer.commit(event, authority=None, observations=None, ledger_refs=refs)
                    if not snapshot.state.deadline_seen or snapshot.state.renewal_request_id is None:
                        event = ManagementEvent(sequence=snapshot.state.sequence + 1,
                            previous_state_sha256=state_digest(snapshot.state), at=now, kind="deadline")
                        snapshot = writer.commit(event, authority=None, observations=None, ledger_refs=refs)
                request = snapshot.state.renewal_request_id
                confirmed = (snapshot.state.deadline_seen and type(request) is str
                             and any(item.kind == "request_management_approval" and item.intent_id == request
                                     for item in snapshot.outbox))
            # Leave the store's I/O boundary before raising a coordinator diagnostic.
            # A closed lifecycle is an authoritative state, not a storage failure.
            _require(not closed, "COORDINATOR_MANAGEMENT_CLOSED")
            _require(confirmed, "COORDINATOR_MANAGEMENT_REQUEST_UNCONFIRMED")
            self._update(management_deadline_recorded=True, management_request_id=request,
                         management_source="", new_entry_blocked=True)
            self._toast_once("management:" + request, "red", "The management deadline has been recorded. "
                             "New management approval is required. No permission is extended automatically.")
            return True
        except Exception as exc:
            code = _code(exc, "COORDINATOR_PROTECTIVE_STORE_FAILED")
            self._update(management_deadline_recorded=False, management_request_id=None,
                         management_source=code, new_entry_blocked=True)
            self._toast_once("management-storage", "red", "The management event could not be confirmed. "
                             "Dependent strategy execution is blocked; a storage failure is not a sell signal.")
            return False

    # -- units -------------------------------------------------------------------------------------------------

    def _monitor(self, kind) -> None:
        """Startup, monitor, boundary and gap units: account step, risk observation, reconciliation."""
        with self._work:
            stage = "account"
            try:
                if self._carry:
                    self._management_deadline(self._time())
                try:
                    self._maybe_refresh_terms()
                except CoordinatorError:
                    pass  # risk monitoring/reconciliation continue; strategy slots remain blocked
                previous = self._load_previous()
                self._prefetch(previous)
                if self._closing.is_set():
                    return
                now = self._time()
                self._publish(previous, now, None)
                if self._universe:
                    self._holdings(now)
                stage = "control"
                self._update(in_flight="control")
                if self._committed_producer is not None:
                    # The producer has already done actual reconciliation and a
                    # current account-only Controller read. Risk for a new entry
                    # is checked by Runner at its own decision boundary; no old
                    # display projection is presented as a current risk result.
                    now = self._time()
                    self._management_deadline(now)
                    result = self._committed_reconciliation
                    self._update(new_entry_blocked=True, risk_reasons=(), recovery_status=None,
                                 recovery_deadline=None, orders=self._controller.states(),
                                 reasons=() if not result.reason else (result.reason,))
                    return
                risk = self._controller.observe(now=now)
                self._ready = True
                reconcile_orders(self._runner, now)
                if self._universe:
                    self._snapshot = risk.universe
                    self._update(snapshot_day=None if risk.universe is None else risk.universe.day,
                                 snapshot_sha256=None if risk.universe is None else risk.universe.snapshot_sha256,
                                 universe_state=universe_state(risk.universe, self._profile.universe_rule_sha256, now))
                    self._universe_monitor(now)
                local_block = (self._terms_blocked or self._terms_unavailable or self._stopping.is_set()
                               or (self._carry and (now >= self._window.end or bool(self.status().management_source))))
                if self._universe:
                    local_block = (local_block or self._extra or self._remainder or self._vanished
                                   or self._pending_terms is not None or not self._within_cap
                                   or self.status().window_ended_missed_slot or now > self._window.end)
                self._update(new_entry_blocked=risk.new_entry_blocked or local_block,
                             risk_reasons=risk.reasons, recovery_status=risk.recovery_status,
                             recovery_deadline=risk.recovery_deadline, orders=self._controller.states())
            except Exception as exc:
                self._refused(stage, _code(exc, "COORDINATOR_DEPENDENCY_REFUSED"), slot=False)
            finally:
                self._board.clear()
                self._update(in_flight="")

    def _slot(self, slot) -> None:
        """One strategy slot: the book at the prefetch lead, then the account capture (it may end inside the slot
        window), the sample at or after the slot, the record, one Runner tick."""
        if self._universe:
            return self._universe_slot(slot)
        with self._work:
            stage = "gate"                                  # the gate is no account step: `reasons` only
            try:
                _require(self._ready, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                _require(not self._terms_blocked, "COORDINATOR_CURRENT_TERMS_REQUIRED")
                stage = "account"
                previous = self._load_previous()
                stage = "quote"
                book = self._read_book()
                if self._stopping.is_set():
                    return
                stage = "account"
                self._prefetch(previous)
                if self._stopping.is_set():
                    return
                stage = "quote"
                self._await(slot)
                if self._stopping.is_set():
                    return
                now = self._time()
                _require(slot <= now <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                sample_prefetched_book(book, slot=slot, sampled_at=now)
                stage = "account"
                observation = self._publish(previous, now, book)
                if self._committed_producer is not None:
                    now = self._time()
                    _require(slot <= now <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                    sample_prefetched_book(book, slot=slot, sampled_at=now)
                    _require(self._ready, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                stage = "control"
                if self._history is not None:
                    self._update(in_flight="history")
                    self._history.record_slot(book, observation)
                # Preserve the current original receipt before a potentially slow P2 write.
                # The actual post-record time still confirms E synchronously before Runner work.
                management_ready = self._management_deadline(self._time())
                if not management_ready:
                    self._update(last_tick=None, reasons=(self.status().management_source,))
                    return
                tick = self._time()
                _require(tick <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                self._update(in_flight="control")
                results = self._runner.run((tick,), max_steps=1, should_stop=self._stopping.is_set)
                last = results[0] if results else None
                self._update(last_tick=last, orders=self._controller.states(),
                             reasons=() if last is None else last.reasons)
            except Exception as exc:
                self._refused(stage, _code(exc, "COORDINATOR_DEPENDENCY_REFUSED"), slot=True)
            finally:
                self._board.clear()
                self._update(in_flight="")


    def _universe_slot(self, slot) -> None:
        """Spec section 7's slot unit for a universe profile: the gate, the trade coin's book at the prefetch lead
        (None when unavailable, never a refusal), the account prefetch, the flag and ticker reads, the sample,
        _publish, record_slot in its own try, then one tick with the recorded allow-list, only when the slot is
        recorded, the strategy is not stopping and the book is available."""
        with self._work:
            if self._stopping.is_set() or self.status().window_ended_missed_slot:
                return
            stage, recorded = "gate", False
            try:
                _require(self._ready, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                _require(not (self._terms_blocked and self._holding() and not self._vanished),
                         "COORDINATOR_CURRENT_TERMS_REQUIRED")
                stage = "account"
                previous = self._load_previous()
                try:
                    book = self._read_book()
                except CoordinatorError:
                    book = None                              # step 2: unavailable, never a refusal
                if self._stopping.is_set():
                    return
                self._prefetch(previous)
                if self._stopping.is_set():
                    return
                flags = self._slot_source.read_flags()
                in_force = universe_state(self._snapshot, self._profile.universe_rule_sha256, slot) == "in_force"
                markets = tuple(m for m in self._snapshot.listed if m in flags.flags) if flags.ok and in_force else ()
                if markets:
                    tickers = self._slot_source.read_tickers(markets)
                else:                                        # no ticker read (step 5)
                    tickers = TickerRead(ok=False, received_at=None, sha256=None, prices=MappingProxyType({}))
                stage = "quote"
                self._await(slot)
                if self._stopping.is_set():
                    return
                now = self._time()
                _require(slot <= now <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                if book is not None:
                    try:
                        sample_prefetched_book(book, slot=slot, sampled_at=now)
                    except Exception:
                        book = None                          # a stale book is unavailable, never a refusal
                stage = "account"
                observation = self._publish(previous, now, book)
                self._holdings(now)
                stage = "control"
                day = now.astimezone(KST).date().isoformat()
                events = self._events(flags, self._latest_frame.accounts[0], day)
                codes = tuple(code for code, _ in events)
                blocks = ()
                if self._extra:
                    blocks += ("UNIVERSE_EXTRA_HOLDING",)
                if self._remainder:
                    blocks += ("UNIVERSE_REMAINDER_UNSELLABLE",)
                if self._terms_unavailable or self._terms_blocked or self._pending_terms is not None:
                    blocks += ("TERMS_TARGET_UNAVAILABLE",)
                if "UNIVERSE_HELD_FLAG_UNCERTAIN" in codes:
                    blocks += ("UNIVERSE_HELD_FLAG_UNCERTAIN",)         # spec section 7: no buy at this slot
                allow, reasons = slot_allow(snapshot=self._snapshot, rule_sha256=self._profile.universe_rule_sha256,
                                            n=self._program.max_candidates, flags=flags, tickers=tickers, slot=slot,
                                            blocks=blocks)
                if not self._within_cap:
                    allow -= {self._profile.symbol}
                held = self._held[0] if self._held else None
                self._update(in_flight="history", allow_count=len(allow), buy_block_reasons=reasons,
                             held_flag=flags.flags.get(held, "absent") if flags.ok and held else None)
                acted = None
                options = dict(trade_symbol=self._profile.symbol,
                               universe=SlotUniverse(snapshot=self._snapshot, flags=flags, tickers=tickers,
                                                     allow=allow, reasons=reasons, events=codes),
                               tick_size=self._profile.instrument_rules.tick_size,
                               positions=self._latest_frame.accounts[0].positions)
                try:
                    acted = self._history.decided_symbol()   # before the record, inside its failure boundary
                    try:
                        self._history.record_slot(book, observation, **options)
                    except Exception as exc:
                        if book is None or _code(exc, "") not in ("HISTORY_BOOK_OFF_TICK",
                                                                  "HISTORY_BOOK_MARKET_MISMATCH"):
                            raise
                        book = None                          # PR 4d: refused before any write; record without it
                        self._history.record_slot(None, observation, **options)
                    recorded = True
                except Exception as exc:
                    reasons += (_code(exc, "COORDINATOR_HISTORY_REFUSED"),)
                    self._slot_missed()
                for code, action in events:                  # step 8: each event in its own try
                    try:
                        reasons += action() or ()
                    except Exception:
                        reasons += ("COORDINATOR_EVENT_FAILED",)
                        try:
                            self._toast_once("event-failed:" + code + ":" + day, "red",
                                             code + " did not complete. Check the console status.")
                        except Exception:
                            self._update(notification_failed=True)
                if not recorded or self._stopping.is_set() or self._vanished:
                    self._update(reasons=reasons)
                    return
                if book is None:
                    self._update(reasons=reasons + ("COORDINATOR_NO_TRADE_BOOK",))
                    return
                tick = self._time()
                _require(tick <= slot + SLOT_WINDOW, "COORDINATOR_SLOT_WINDOW_MISSED")
                self._update(in_flight="control")
                results = self._runner.run((tick,), max_steps=1, should_stop=self._stopping.is_set,
                                           entry_allow=self._history.recorded_allow)
                last = results[0] if results else None
                self._after_tick(last, acted, day)
                self._update(last_tick=last, orders=self._controller.states(),
                             reasons=reasons + (() if last is None else last.reasons))
            except Exception as exc:
                self._refused(stage, _code(exc, "COORDINATOR_DEPENDENCY_REFUSED"), slot=True)
                if not recorded:
                    self._slot_missed()
            finally:
                self._board.clear()
                self._update(in_flight="")

    def _slot_missed(self) -> None:
        """Spec section 12: a slot the history did not record ends the window. Sticky status and, while a coin is
        held, one red toast. No later slot is synthesized or executed from this incomplete window."""
        self._update(window_ended_missed_slot=True, new_entry_blocked=True)
        if self._held:
            self._toast_once("missed", "red", "A missed slot ended strategy execution while a coin is held. Monitoring continues. "
                             "Review the data failure and request management approval if needed; this is not a sell signal.")

    def _explicit(self, action, *, with_book):
        """An operator unit (allowed after stop and after close): account step, then the action at that time."""
        with self._work:
            try:
                previous = self._load_previous()
                self._prefetch(previous)
                book = self._read_book() if with_book else None
                now = self._time()
                self._publish(previous, now, book)
                if self._universe:
                    self._holdings(now)
                self._update(in_flight="control")
                if self._committed_producer is not None:
                    now = self._time()
                state = action(now)
                self._update(orders=self._controller.states())
                return state
            except Exception as exc:
                if self._committed_producer is not None:
                    self._ready = False
                raise CoordinatorError(_code(exc, "COORDINATOR_DEPENDENCY_REFUSED")) from None
            finally:
                self._board.clear()
                self._update(in_flight="")

    def _gap(self, timer, seen) -> int:
        """Skipped deadlines since the last check (a suspend, or an overrun) mean a data gap: reconcile first."""
        missed = timer.missed
        total = sum(missed.values())
        if total != seen:
            self._update(missed_slots=missed["slot"], missed_boundaries=missed["boundary"], data_gap_at=self._now())
            self._monitor("gap")
            if self._universe and missed["slot"] and not self._stopping.is_set():
                self._slot_missed()          # spec section 12: a missed slot ends the history window
        return total

    def _session_for(self, session_id):
        launch = self._launch
        return launch.prepared if launch is not None and launch.prepared.session_id == session_id else None

    # -- public contract ---------------------------------------------------------------------------------------

    def run(self) -> CoordinatorStatus:
        with self._status_lock:                             # test-and-set: one run per instance
            _require(not self._started, "COORDINATOR_ALREADY_RUN")
            self._started = True
        try:
            if not self._closing.is_set():
                self._run()
        finally:
            if self._runner is not None:
                self._runner.stop()
            self._board.clear()
            self._phase = "closed"
            self._update()
            self._finished.set()
        return self.status()

    def _run(self) -> None:
        start = self._time()
        step, lead = timedelta(seconds=self._bar_seconds), timedelta(seconds=self._knobs["prefetch_lead_seconds"])
        first = self._window.start + max(0, -((self._window.start - start) // step)) * step   # the first slot at or after start
        _require(first > self._window.end or first - lead - start >= STARTUP_BUDGET, "COORDINATOR_START_TOO_LATE")
        with self._work:                                          # R15 before any unit: COORDINATOR_CUTOFF_MISMATCH
            try:
                self._load_previous()
            except CoordinatorError as exc:
                if str(exc) != "COORDINATOR_CHECKPOINT_REFUSED":  # the startup unit reports a checkpoint refusal
                    raise
        self._phase = "running"
        self._update()
        timer = CancellableTimer(schedule(window=self._window, bar_seconds=self._bar_seconds, start=start,
                                          monitor_until=self._monitor_until, cutoff_seconds=self._cutoff,
                                          **self._knobs), clock=self._now, cancel=self._closing, wait=self._wait)
        self._monitor("startup")
        seen = 0
        for due in timer:
            seen = self._gap(timer, seen)
            if due.kind == "slot":
                if not self._stopping.is_set():
                    self._slot(due.slot)
            else:
                self._monitor(due.kind)
            strategy_done = (self._stopping.is_set() or (self._runner is not None and self._runner.stopped)
                             or due.at > self._window.end or self.status().window_ended_missed_slot)
            self._phase = "monitoring" if strategy_done else "running"
            self._update()
        if not self._closing.is_set():
            self._gap(timer, seen)

    def stop(self) -> None:
        """Strategy stop: no further slot runs; monitoring, cancel and exit stay available. No venue cancel."""
        self._stopping.set()
        if self._runner is not None:
            self._runner.stop()
        self._update()

    def close(self, timeout: float = 0.0) -> bool:
        """Stop and end the schedule; True once run() has finished (at once when it never started)."""
        self._stopping.set()
        self._closing.set()
        if self._runner is not None:
            self._runner.stop()
        self._update()
        with self._status_lock:
            started = self._started
        return True if not started else self._finished.wait(timeout)

    def refresh_instrument_rules(self) -> datetime:
        """Explicit same-contract renewal; no arming, session lifetime or economic change."""
        with self._work:
            # Explicit protective exits remain available even after close. Renewal never
            # clears either latch or restarts the schedule.
            return self._refresh_terms()

    def bootstrap(self) -> CoordinatorStatus:
        """Perform one serialized account/risk/reconciliation unit before owner preparation.

        This does not start the schedule, prepare a session or activate anything. A failed
        account capture remains visible in status; callers must inspect the result.
        """
        with self._status_lock:
            _require(not self._started, "COORDINATOR_ALREADY_RUN")
        _require(not self._closing.is_set() and not self._stopping.is_set(), "COORDINATOR_STOPPED")
        self._monitor("bootstrap")
        return self.status()

    def disarm(self, *, timeout: float = 1.0) -> DisarmResult:
        """Stop slots now; acquire the unit lock boundedly before a durable local kill.

        A busy unit returns pending=True and makes no claim that a kill or owner
        system-disarm was recorded. Retry after the unit ends. No network read is
        started here: the last genuine published frame keeps its original times,
        and Controller.kill falls back to a journal-only kill if it is stale.
        Venue cancellation/liquidation is never implied. Journal/owner file writes
        retain their existing OS-lock/durability boundary once the unit lock is held.
        """
        _require(type(timeout) in (int, float) and 0 <= timeout <= 5, "COORDINATOR_DISARM_TIMEOUT_INVALID")
        self.stop()
        if not self._work.acquire(timeout=timeout):
            self._update(new_entry_blocked=True, reasons=("COORDINATOR_DISARM_PENDING",))
            return DisarmResult(session_prepared=self._launch is not None, journal_kill_written=False,
                                owner_disarm_recorded=False, pending=True)
        try:
            return self._disarm_locked(reason="owner_requested", code=None, republish=True)
        finally:
            self._board.clear()
            self._update(in_flight="")
            self._work.release()

    def _disarm_locked(self, *, reason, code, republish) -> DisarmResult:
        """The durable kill under a work lock the caller holds (spec section 7). `republish` re-publishes the last
        genuine frame for the owner's disarm; the universe disarm runs inside a slot unit right after its own
        _publish, so the board already holds that unit's frame. `code` replaces the owner codes in `reasons`."""
        try:
            launch = self._launch
            if launch is None:
                self._update(new_entry_blocked=True)
                return DisarmResult(session_prepared=False, journal_kill_written=False,
                                    owner_disarm_recorded=False)
            clock_valid = True
            try:
                now = self._time()
            except Exception:
                clock_valid = False
                now = self._last_time
                if now is None:
                    from datetime import timezone
                    now = datetime(1970, 1, 1, tzinfo=timezone.utc)
            if self._committed_producer is not None:
                self._committed_configuration()
            if republish and clock_valid and self._latest_frame is not None:
                self._board.publish(self._latest_frame, None)
            owner_recorded = self._controller.kill(launch.prepared.session_id, reason=reason, now=now)
            self._update(new_entry_blocked=True, orders=self._controller.states(),
                reasons=(code or ("COORDINATOR_OWNER_DISARM_RECORDED" if owner_recorded
                                  else "COORDINATOR_DISARM_JOURNAL_ONLY"),))
            return DisarmResult(session_prepared=True, journal_kill_written=True,
                                owner_disarm_recorded=owner_recorded)
        except Exception as exc:
            self._update(new_entry_blocked=True, reasons=("COORDINATOR_DISARM_RECORD_REFUSED",))
            raise CoordinatorError(_code(exc, "COORDINATOR_DISARM_RECORD_REFUSED")) from None

    def prepare(self, *, selected_plan, inputs, selection_seed_hex: str, expires_at: datetime | None = None,
                universe_batch=None):
        """prepare_launch_session over the last unit's observation; the actual PreparedSession is kept here and
        served to the Controller by identity. Nothing is signed or armed."""
        with self._work:
            _require(not self._stopping.is_set(), "COORDINATOR_STOPPED")
            _require(not self._terms_blocked, "COORDINATOR_CURRENT_TERMS_REQUIRED")
            _require(not (self._universe and self.status().window_ended_missed_slot),
                     "COORDINATOR_HISTORY_WINDOW_ENDED")
            def preparation_clock():
                _require(not self._stopping.is_set() and not self._closing.is_set(), "COORDINATOR_STOPPED")
                _require(not self._terms_blocked, "COORDINATOR_CURRENT_TERMS_REQUIRED")
                at = self._now()
                _require((not self._universe or at <= self._window.end)
                         and (not self._carry or at < self._window.end), "COORDINATOR_MANAGEMENT_RENEWAL_REQUIRED")
                return at

            actual = preparation_clock()
            if self._committed_producer is not None:
                self._current_committed(actual)
                _require(self._ready, "COORDINATOR_STARTUP_RECONCILE_REQUIRED")
                actual = self._time()
            observation, now = self._observation, getattr(inputs, "now", None)
            _require(observation is not None and _aware(now) and observation.asof <= now <= actual
                     and actual - now <= ACCOUNT_AGE and actual - observation.asof <= ACCOUNT_AGE,
                     "COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT")
            try:
                launch = prepare_launch_session(profile=self._profile, evidence=self._evidence, driver=self._driver,
                    implementation_verifier=self._implementation_verifier, journal=self._journal,
                    selected_plan=selected_plan, inputs=inputs, positions=observation.positions, now=now,
                    selection_seed_hex=selection_seed_hex, expires_at=expires_at, universe_batch=universe_batch,
                    clock=preparation_clock, positions_asof=observation.asof)
            except Exception as exc:
                raise CoordinatorError(_code(exc, "COORDINATOR_DEPENDENCY_REFUSED")) from None
            self._launch = launch
            self._runner.launch_session = launch
            return launch.prepared


    def odds_batch(self, template, read_bars):
        """Spec section 9: the per-coin odds batch on the caller's (console) thread, never under the work lock and
        never inside a unit. `read_bars(markets, now=, clock=)` reads the daily bars of the top-N of the last
        monitor's snapshot; run_batch reloads the snapshot in force from its own context and journals the batch."""
        _require(self._universe, "COORDINATOR_UNIVERSE_REQUIRED")
        snapshot = self._snapshot
        _require(snapshot is not None, "UNIVERSE_NO_SNAPSHOT")
        try:
            bars_at = self._now()
            day = bars_at.astimezone(KST).date()
            _require(universe_state(snapshot, self._profile.universe_rule_sha256, bars_at) == "in_force",
                     "UNIVERSE_NO_SNAPSHOT")
            n = self._program.max_candidates
            bars = read_bars(universe_top_n(snapshot, n), now=bars_at, clock=self._clock)
            observation = self._observation                 # exactly one read, after the potentially slow I/O
            now = self._now()                                # validity is measured after bars and observation
            _require(now >= bars_at, "COORDINATOR_CLOCK_ROLLBACK")
            _require(now.astimezone(KST).date() == day, "COORDINATOR_ODDS_DAY_CHANGED")
            _require(observation is not None and _aware(observation.asof)
                     and observation.asof <= now and now - observation.asof <= ACCOUNT_AGE,
                     "COORDINATOR_ODDS_ACCOUNT_NOT_CURRENT")
            return run_batch(self._controller, template, bars, n=n, now=now, clock=self._clock,
                             positions=observation.positions, positions_asof=observation.asof)
        except Exception as exc:
            raise CoordinatorError(_code(exc, "COORDINATOR_ODDS_BATCH_FAILED")) from None

    def cancel(self, client_id: str) -> OrderState:
        """A cancel request through the Runner; an acknowledgement, not a confirmed cancellation."""
        return self._explicit(lambda now: self._runner.cancel(client_id, now=now), with_book=False)

    def submit_exit(self, exit_signal) -> OrderState:
        """An explicit reducing exit through the Runner; a repeat returns the existing state."""
        return self._explicit(lambda now: self._runner.submit_exit(exit_signal, now=now), with_book=True)


# -- the owned composition ------------------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class Composition:
    profile: LaunchProfile
    program: ProgramSpec
    protocol: ForwardProtocol
    window: DeploymentWindow
    driver: StrategyDriver
    identity: FixedDriverIdentity
    history: LiveHistory
    authority: CurrentOwnerAuthority
    verifiers: ReviewVerifiers
    evidence: EvidencePackage


def compose(*, profile_path: str, program_path: str, protocol_path: str, capture_path: str, review_path: str,
            evaluated_at: datetime, window: DeploymentWindow, clock: Callable[[], datetime], head_root,
            history_storage_path: str | None = None) -> Composition:
    """Wire the reviewed artifacts for one deployment window in the integration guide's order: the private-input
    loader (every file a bounded local .json), the capture re-evaluated at the original evaluator time, the fixed
    driver over the installed program artifact with the live history's exact callables, LiveHistory.bind (the
    history head must already hold GENESIS from the operator step, and the clock must still be before
    window.start), ReviewVerifiers over a CurrentOwnerAuthority on the same clock, then the EvidencePackage.
    Nothing here fetches, signs, arms or orders; every refusal is the fixed code of the stage that refused."""
    profile = parse_profile_json(read_file(profile_path, MAX_CONFIG_BYTES))
    program = parse_program(read_file(program_path, MAX_CONFIG_BYTES))
    protocol = parse_protocol(read_file(protocol_path, MAX_CONFIG_BYTES))
    storage_policy = read_history_storage(protocol, history_storage_path)
    result = evaluate_capture_json(protocol, read_file(capture_path, MAX_CAPTURE_BYTES), profile.instrument_rules,
                                   now=evaluated_at)
    document = read_file(review_path, MAX_DOCUMENT_BYTES)
    prepared = _compose_driver(profile=profile, program=program, protocol=protocol, window=window,
                               clock=clock, head_root=head_root, storage_policy=storage_policy)
    history, driver, identity = prepared.history, prepared.driver, prepared.identity
    authority = CurrentOwnerAuthority(clock=clock)
    verifiers = ReviewVerifiers(document, clock=clock, authority_provider=authority,
                                approved_history_provider=history.provider, approved_history_verifier=history.verifier)
    evidence = EvidencePackage(protocol=protocol, result=result, review_verifier=verifiers.source)
    return Composition(profile=profile, program=program, protocol=protocol, window=window, driver=driver,
                       identity=identity, history=history, authority=authority, verifiers=verifiers, evidence=evidence)


@dataclass(frozen=True, kw_only=True)
class DriverComposition:
    """Actual fixed driver and history wiring before a detached review is signed."""
    profile: LaunchProfile
    program: ProgramSpec
    protocol: ForwardProtocol
    window: DeploymentWindow
    driver: StrategyDriver
    identity: FixedDriverIdentity
    history: LiveHistory


def read_history_storage(protocol: ForwardProtocol, path: str | None) -> HistoryStoragePolicy | None:
    """Read one explicit policy and check the frozen protocol binding; no default or state write.

    Omitted legacy policies remain omitted. LiveHistory decides whether an existing
    legacy universe journal can be read; it refuses fresh legacy universe writes.
    """
    _require(type(protocol) is ForwardProtocol, "COORDINATOR_HISTORY_STORAGE_PROTOCOL_REQUIRED")
    expected = protocol.history_storage_sha256
    if path is None:
        _require(expected is None, "COORDINATOR_HISTORY_STORAGE_REQUIRED")
        return None
    policy = parse_policy(read_file(path, MAX_POLICY_BYTES))
    _require(expected is not None and policy_digest(policy) == expected,
             "COORDINATOR_HISTORY_STORAGE_MISMATCH")
    return policy


def _compose_driver(*, profile, program, protocol, window, clock, head_root,
                    storage_policy: HistoryStoragePolicy | None = None) -> DriverComposition:
    # Re-check the actual loaded profile after configuration reads: a caller's universe
    # flag cannot widen a fixed-profile window if an artifact changes between reads.
    _require(type(profile) is LaunchProfile and type(window) is DeploymentWindow
             and _aware(window.start) and _aware(window.end), "COORDINATOR_WINDOW_INVALID")
    maximum = UNIVERSE_WINDOW_MAX if profile.universe_rule_sha256 is not None else timedelta(hours=24)
    _require(timedelta(0) < window.end - window.start <= maximum, "COORDINATOR_WINDOW_SPAN_UNSUPPORTED")
    root = state_root().absolute()
    head = BaselineHead(root=head_root, name=history_head_name(window),
                        chain=HistoryChain(root=root, window=window, storage_policy=storage_policy))
    history = LiveHistory(program, protocol, profile, window=window, root=root, clock=clock, trusted_head=head,
                          storage_policy=storage_policy)
    behavior = resolve_behavior(protocol)
    factory = make_fixed_carry_driver if behavior == "protective-carry-v2" else make_fixed_driver
    driver = factory(program, protocol, profile, window=window, history_provider=history.provider,
                     history_verifier=history.verifier, program_artifact=artifact("program.py"))
    identity = history.bind(driver)
    return DriverComposition(profile=profile, program=program, protocol=protocol, window=window,
                             driver=driver, identity=identity, history=history)


def compose_driver(*, profile_path: str, program_path: str, protocol_path: str,
                   window: DeploymentWindow, clock: Callable[[], datetime], head_root,
                   history_storage_path: str | None = None) -> DriverComposition:
    """Exportable actual driver identity without requiring a review that signs that identity.

    The operator must first initialize this window's independent history head to GENESIS.
    This binds (or verifies an existing binding of) the history journal and constructs no
    authority/review verifier. It does not claim source authentication or owner approval.
    """
    profile = parse_profile_json(read_file(profile_path, MAX_CONFIG_BYTES))
    program = parse_program(read_file(program_path, MAX_CONFIG_BYTES))
    protocol = parse_protocol(read_file(protocol_path, MAX_CONFIG_BYTES))
    storage_policy = read_history_storage(protocol, history_storage_path)
    return _compose_driver(profile=profile, program=program, protocol=protocol, window=window,
                           clock=clock, head_root=head_root, storage_policy=storage_policy)
