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
from datetime import datetime, time, timedelta
import heapq
import re
import threading
from typing import Callable, Iterable, Iterator, Mapping

from core.compliance.model import KST
from core.isolation import state_root
from execution_accounts.baseline_bridge import BaselineFrame, ContinuousAccountProvider
from execution_accounts.baseline_store import CheckpointStore
from execution_control.capability import digest
from execution_control.controller import Controller, OrderState
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_control.store import Journal, JournalError
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import (DeploymentWindow, FixedDriverError, FixedDriverIdentity, describe_fixed_driver,
                                     make_fixed_driver)
from execution_launch.live_history import HistoryChain, LiveHistory
from execution_launch.history_storage import (HistoryStoragePolicy, MAX_POLICY_BYTES, parse_policy, policy_digest)
from execution_launch.instrument_refresh import renew_profile
from execution_launch.paper_capture import sample_prefetched_book
from execution_launch.profile import LaunchProfile, parse_profile_json, risk_policy
from execution_launch.program import ProgramSpec, parse_program
from execution_launch.review_auth import MAX_DOCUMENT_BYTES, ReviewVerifiers
from execution_launch.runner import (EvidencePackage, LaunchSession, Runner, StrategyDriver, TickResult,
                                     prepare_launch_session)
from execution_launch.strategy import ForwardProtocol, evaluate_capture_json, parse_protocol
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
    """Builds and owns exactly one ContinuousAccountProvider, Journal, Controller and Runner over the explicit
    adapters; construction checks everything in the refusal-code order and creates no file."""
    def __init__(self, *, mode: str, profile: LaunchProfile, evidence: EvidencePackage, driver: StrategyDriver,
                 implementation_verifier: Callable, adapters: Mapping[str, object], account_source: Callable,
                 trusted_head: object, quote_source: object, window: DeploymentWindow, bar_seconds: int,
                 monitor_until: datetime, clock: Callable[[], datetime], account_prefetch: Callable | None = None,
                 history: object | None = None, terms_source: object | None = None,
                 monitor_seconds: int = 10, prefetch_lead_seconds: int = 3,
                 boundary_lead_seconds: int = 1,     # calibration (R19): under the shortest capture's 1.8 s (9
                                                     # requests, 0.2 s pace each), leaving ~1 s for the first reply
                 wait: Callable[[threading.Event, float], bool] = threading.Event.wait) -> None:
        _require(mode == "rehearsal", "COORDINATOR_MODE_UNSUPPORTED")
        _require(type(profile) is LaunchProfile and (profile.venue, profile.market, profile.quote_currency)
                 == ("upbit", "spot", "KRW"), "COORDINATOR_VENUE_UNSUPPORTED")
        _require(type(evidence) is EvidencePackage and type(driver) is StrategyDriver
                 and all(callable(f) for f in (clock, wait, account_source, implementation_verifier))
                 and (account_prefetch is None or callable(account_prefetch))
                 and callable(getattr(quote_source, "read", None)) and callable(getattr(trusted_head, "read", None))
                 and (history is None or callable(getattr(history, "record_slot", None)))
                 and (terms_source is None or callable(getattr(terms_source, "read", None))),
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
        self._store = CheckpointStore(root=root)                              # path metadata only
        self._board = _TickBoard()
        self._provider = ContinuousAccountProvider(source=self._board.account_frame, store=self._store,
                                                   trusted_head=trusted_head)
        self._journal = Journal()                                             # path checks only
        self._controller = Controller(journal=self._journal, account_provider=self._provider, policy=policy,
                                      adapters=adapters, session_provider=self._session_for)
        self._runner = Runner(profile=profile, quote_provider=self._board.quote, account_provider=self._provider,
                              evidence=evidence, driver=driver, implementation_verifier=implementation_verifier,
                              mode=mode, controller=self._controller, launch_session=None, isolated_state_root=root)
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

    # -- status ------------------------------------------------------------------------------------------------

    def status(self) -> CoordinatorStatus:
        with self._status_lock:
            return self._status

    def _update(self, **changes) -> None:
        with self._status_lock:
            self._status = replace(self._status, phase=self._phase,
                                   strategy_stopped=self._stopping.is_set() or self._runner.stopped, **changes)

    def _refused(self, stage, code, *, slot) -> None:
        """An account-step failure is kept apart from risk and order state; a slot's outcome is in `reasons`."""
        changes = {}
        if stage == "account":
            changes.update(account_source=code, new_entry_blocked=True)
        if stage == "control":
            changes["new_entry_blocked"] = True
        if slot or stage == "control":
            changes["reasons"] = (code,)
        self._update(**changes)

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
        if self._account_prefetch is not None:
            try:
                self._account_prefetch(previous)
            except Exception as exc:
                raise CoordinatorError(_code(exc, "COORDINATOR_ACCOUNT_SOURCE_FAILED")) from None

    def _read_book(self):
        self._update(in_flight="quote_source")
        try:
            return self._quote_source.read()
        except Exception as exc:
            raise CoordinatorError(_code(exc, "COORDINATOR_QUOTE_SOURCE_FAILED")) from None

    def _publish(self, previous, now, book):
        """The unit's one frame: from the producer without I/O, published, then observed through the provider."""
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

    def _refresh_terms(self):
        """Called under the work lock, before account/quote timing for a unit."""
        _require(self._terms_source is not None, "COORDINATOR_TERMS_SOURCE_REQUIRED")
        try:
            if self._pending_terms is None:
                observation = self._terms_source.read()
                now = self._time()             # actual receipt completes before the clock is chosen
                self._pending_terms = renew_profile(self._profile, observation, now=now)
            else:
                now = self._time()             # retry the issued object; never fork from the old snapshot
            renewal = self._pending_terms
            self._runner.refresh_instrument_rules(renewal, now=now)
            self._profile = renewal.profile
            self._pending_terms = None
            self._launch = self._runner.launch_session  # same actual PreparedSession, updated wrapper only
            self._terms_blocked = False
            self._update(instrument_source="", instrument_asof=self._profile.instrument_rules.asof)
            return self._profile.instrument_rules.asof
        except Exception as exc:
            self._terms_blocked = True
            code = _code(exc, "COORDINATOR_TERMS_SOURCE_FAILED")
            self._update(instrument_source=code, new_entry_blocked=True)
            raise CoordinatorError(code) from None

    def _maybe_refresh_terms(self):
        if self._terms_source is None:
            return
        rules = self._profile.instrument_rules
        now = self._now()
        if (self._terms_blocked or rules is None or rules.asof > now
                or now - rules.asof >= TERMS_REFRESH_AGE):
            self._refresh_terms()

    # -- units -------------------------------------------------------------------------------------------------

    def _monitor(self, kind) -> None:
        """Startup, monitor, boundary and gap units: account step, risk observation, reconciliation."""
        with self._work:
            stage = "account"
            try:
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
                stage = "control"
                self._update(in_flight="control")
                risk = self._controller.observe(now=now)
                self._ready = True
                reconcile_orders(self._runner, now)
                self._update(new_entry_blocked=risk.new_entry_blocked or self._terms_blocked, risk_reasons=risk.reasons,
                             recovery_status=risk.recovery_status, recovery_deadline=risk.recovery_deadline,
                             orders=self._controller.states())
            except Exception as exc:
                self._refused(stage, _code(exc, "COORDINATOR_DEPENDENCY_REFUSED"), slot=False)
            finally:
                self._board.clear()
                self._update(in_flight="")

    def _slot(self, slot) -> None:
        """One strategy slot: the book at the prefetch lead, then the account capture (it may end inside the slot
        window), the sample at or after the slot, the record, one Runner tick."""
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
                stage = "control"
                if self._history is not None:
                    self._update(in_flight="history")
                    self._history.record_slot(book, observation)
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

    def _explicit(self, action, *, with_book):
        """An operator unit (allowed after stop and after close): account step, then the action at that time."""
        with self._work:
            try:
                previous = self._load_previous()
                self._prefetch(previous)
                book = self._read_book() if with_book else None
                now = self._time()
                self._publish(previous, now, book)
                self._update(in_flight="control")
                state = action(now)
                self._update(orders=self._controller.states())
                return state
            except Exception as exc:
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
            strategy_done = self._stopping.is_set() or self._runner.stopped or due.at > self._window.end
            self._phase = "monitoring" if strategy_done else "running"
            self._update()
        if not self._closing.is_set():
            self._gap(timer, seen)

    def stop(self) -> None:
        """Strategy stop: no further slot runs; monitoring, cancel and exit stay available. No venue cancel."""
        self._stopping.set()
        self._runner.stop()
        self._update()

    def close(self, timeout: float = 0.0) -> bool:
        """Stop and end the schedule; True once run() has finished (at once when it never started)."""
        self._stopping.set()
        self._closing.set()
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
            if clock_valid and self._latest_frame is not None:
                self._board.publish(self._latest_frame, None)
            owner_recorded = self._controller.kill(launch.prepared.session_id,
                reason="owner_requested", now=now)
            self._update(new_entry_blocked=True, orders=self._controller.states(),
                reasons=("COORDINATOR_OWNER_DISARM_RECORDED" if owner_recorded
                         else "COORDINATOR_DISARM_JOURNAL_ONLY",))
            return DisarmResult(session_prepared=True, journal_kill_written=True,
                                owner_disarm_recorded=owner_recorded)
        except Exception as exc:
            self._update(new_entry_blocked=True, reasons=("COORDINATOR_DISARM_RECORD_REFUSED",))
            raise CoordinatorError(_code(exc, "COORDINATOR_DISARM_RECORD_REFUSED")) from None
        finally:
            self._board.clear()
            self._update(in_flight="")
            self._work.release()

    def prepare(self, *, selected_plan, inputs, selection_seed_hex: str, expires_at: datetime | None = None):
        """prepare_launch_session over the last unit's observation; the actual PreparedSession is kept here and
        served to the Controller by identity. Nothing is signed or armed."""
        with self._work:
            _require(not self._stopping.is_set(), "COORDINATOR_STOPPED")
            _require(not self._terms_blocked, "COORDINATOR_CURRENT_TERMS_REQUIRED")
            def preparation_clock():
                _require(not self._stopping.is_set() and not self._closing.is_set(), "COORDINATOR_STOPPED")
                _require(not self._terms_blocked, "COORDINATOR_CURRENT_TERMS_REQUIRED")
                return self._now()

            observation, now, actual = self._observation, getattr(inputs, "now", None), preparation_clock()
            _require(observation is not None and _aware(now) and observation.asof <= now <= actual
                     and actual - now <= ACCOUNT_AGE and actual - observation.asof <= ACCOUNT_AGE,
                     "COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT")
            try:
                launch = prepare_launch_session(profile=self._profile, evidence=self._evidence, driver=self._driver,
                    implementation_verifier=self._implementation_verifier, journal=self._journal,
                    selected_plan=selected_plan, inputs=inputs, positions=observation.positions, now=now,
                    selection_seed_hex=selection_seed_hex, expires_at=expires_at,
                    clock=preparation_clock, positions_asof=observation.asof)
            except Exception as exc:
                raise CoordinatorError(_code(exc, "COORDINATOR_DEPENDENCY_REFUSED")) from None
            self._launch = launch
            self._runner.launch_session = launch
            return launch.prepared

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
    root = state_root().absolute()
    head = BaselineHead(root=head_root, name=history_head_name(window),
                        chain=HistoryChain(root=root, window=window, storage_policy=storage_policy))
    history = LiveHistory(program, protocol, profile, window=window, root=root, clock=clock, trusted_head=head,
                          storage_policy=storage_policy)
    driver = make_fixed_driver(program, protocol, profile, window=window, history_provider=history.provider,
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
