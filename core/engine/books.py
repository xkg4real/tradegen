"""Per-book runtime: DISARMED / ARMED / HALTED per book id, HALT scope, counters, persistence (section 3.8;
R-07 re-arm classes; R-19 rule 4 counters; TASK-M1-20, TASK-M1-17; T-ROLE-01, T-MISS-02, T-LAG-01 runtime clauses;
carrier for T-HALT-01, I-04b, T-STEP-05, T-SCOPE-01).

Additive beside `EngineState`: the operator engine's global state machine, manual acknowledge and `engine.json` are
untouched. `EngineMode` is reused for the three state names. The hooks never touch `EngineState`: a HALT is scoped
to one book id ("never 'the engine' as such", L1178).

Every function takes `decision_utc` explicitly; nothing here reads a wall clock. Book state lives in one JSON file
per book under `<path>/books/` (atomic replace, utf-8, a failed write raises). Every HALT, re-arm, arm, retire and
acknowledgement appends one `governance_events.jsonl` line through `core.rules.governance.append_event`.

The RISK rule (hard stop, risk-limit breach) needs the book's primary-market session calendar: `sessions(market)`
returns the sorted session dates (package B supplies it; tests stub it). Without it a RISK HALT is refused (fail
closed). Sessions are counted as decisions: one `step_decision` per market per close.

M5 (R-07 hard stop, R-31 ladder carrier, R-25 NAV, weight books; T-HALT-01, I-04, I-04b, T-STEP-05, T-MONO-01):
`risk_step` (= `hard_stop_check`) is the per-decision R-07 / R-31 step on the book's whole-book NAV (brief B.0 steps
1-3): NAV counter and OPS HALT at the 3rd unavailable decision, the re-arm attempt (a breach re-arms only once the
post-action target meets the limit: `limit_met`), the pure `risk_layer.ladder_step`, the RISK HALT through
`runtime_halt`. `book_nav` values the book from the ledger's held weights and injected returns / costs at the costed
engine's convention (earn t+1, cost on |dw| on the earning day, initial entry free); `record_decision` persists the
decided weights (HALTED -> 0; a blocked new entry = a decided target above the held weight, rulings 3.6; a
non-fillable order carried at its held weight) to an append-only ledger; `nav_path` reads it back. OPS triggers added:
`whole_book_nav_unavailable_gt_2_decisions`, `feed_heartbeat_loss_60s` (synthetic-only: against injected timestamps,
no v2.0 daily book reads the QuoteFeed, F-11), `operator_kill` (a card's on/off/S books killed and retired together).
`neutralise_rule` is the R-18 hook `context_log.log_break(neutralise=...)` pushes through: the neutralised map
(rule_id -> event_id) is a per-book carrier that `macro_artifacts.build_overlay_decisions(neutralised=...)` applies.

Sprint 4 wiring (tests/macro_m5_integration.py): `evaluator.evaluator_block` reads `block_new_entries` through
`risk_layer.ladder_for_book`; `orders.simulate_fill` supplies `fillable`; `sleeves.apply_market_gross` takes the
ladder term and `post_rearm_cap(book)`. # integration: the M8 pipeline derives `returns` from PIT official closes
# through NAV_LINE_CLOSES / nav_fx and `costs` from instruments.cost_per_side.
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping, NamedTuple, Sequence
from urllib.parse import quote

from core.engine.state import EngineMode
from core.ficc.macro_schema import enum_of
from core.rules import governance as G

MARKETS = enum_of("macro_state", "/market")                       # section 6.1 enum, one source
CLASSES = ("RISK", "OPS")
RISK_REASONS = ("hard_stop", "risk_limit_breach")                  # risk_layer.halted_triggers.RISK (L4355)
# OPS causes that need an operator re-arm (risk_layer.ops_rearm.operator_required_after, L4360; kill L1186).
OPERATOR_REARM = ("lag_audit_violation", "acting_field_schema_or_bounds_failure", "operator_kill")
REARM_REFUSED_SESSIONS = 10                                        # hard_stop.rearm_refused_sessions (L4350)
POST_REARM_DECISIONS = 10                                          # hard_stop.post_rearm_sessions (L4351)
POST_REARM_CAP = 0.5
DEFAULT_LIMIT = 2                                                  # halt_after_consecutive_decisions default (L1870)
BOOK_LIMIT = 2                                                     # book_counter_halt_after (L1870)
INPUT_STALE = "acting_input_stale:"                                # reason_code prefix, L1951
BOOK_COUNTER_REASON = "acting_input_fail_closed_beyond_declared_misses"
STEP_ERROR_REASON = "acting_step_error_beyond_limit"
NAV_REASON = "whole_book_nav_unavailable_gt_2_decisions"           # R-25; monitoring.nav_unavailable_ops_halt_after_decisions 2
NAV_LIMIT = 3                                                      # HALT when the counter reaches 3 (F-23; NAV_LINE_CLOSES limit 3)
HEARTBEAT_REASON = "feed_heartbeat_loss_60s"
HEARTBEAT_LOSS_S = 60.0                                            # risk_layer.heartbeat.loss_s
HEARTBEAT_RESTORED_S = 300.0                                       # heartbeat.auto_rearm_after_restored_min 5
BREACH_REASON = "risk_limit_breach"
RISK_BOOKS = ("recommended", "specification")                      # the hard stop and caps act here only (F-2, R-22 rule 6)
WEIGHT_TOL = 1e-9
_BOOK_ID = re.compile(r"^(?:(?:recommended|specification):(?:%s)|(?:forward_sim|refusal):R-\d+[A-Za-z0-9_-]*"
                      r"|card:[A-Za-z0-9_.-]+:(?:on|off|S))$" % "|".join(MARKETS))
_REFS = ["§3.8"]


class RearmRefused(ValueError):
    """The book stays HALTED: a cause has not cleared under its own rule."""


def parse_book_id(book_id: str) -> tuple[str, str | None]:
    """(kind, market) where market is known only for recommended:<m> / specification:<m>. Raises on a bad form."""
    if not isinstance(book_id, str) or not _BOOK_ID.match(book_id):
        raise ValueError("book id %r is not recommended:<market>, specification:<market>, forward_sim:<rule>, "
                         "refusal:<rule> or card:<card_id>:<on|off|S>" % (book_id,))
    kind, rest = book_id.split(":", 1)
    return kind, (rest if kind in ("recommended", "specification") else None)


def _iso(instant: datetime) -> str:
    return G.iso_utc(instant)


def _session(instant: datetime) -> date:
    if instant.tzinfo is None:
        raise ValueError("decision_utc must be tz-aware UTC")
    return instant.astimezone(timezone.utc).date()


def _reason_key(reason_code: str) -> str:
    return reason_code.split(":", 1)[0]


@dataclass(frozen=True)
class BookRuntime:
    """One book's persisted runtime state. Mutate only through `replace`; `halt` holds the section 6.1 shape."""
    book_id: str
    market: str | None = None                 # primary market (RISK session counting); derived for market books
    mode: EngineMode = EngineMode.DISARMED
    halt: dict | None = None
    post_rearm_cap_until: date | None = None  # last decided_session carrying the cap (artifact field)
    post_rearm_left: int = 0                  # decisions still inside the cap window, counted by step_decision
    nav: float | None = None
    hwm_hard: float | None = None
    ref_step: float | None = None
    consecutive_failures: dict = field(default_factory=dict)   # per acting series bound to the book
    book_counter: int = 0
    ever_armed: bool = False
    switch_counts: dict = field(default_factory=dict)          # "<from>-><to>" -> n
    # M5 carriers (not in the runtime[] entry): the R-31 ladder state, the weights ledger, the OPS counters
    step_mult: float = 1.0
    dwell_left: int = 0
    block_new_entries: bool = False
    held: dict = field(default_factory=dict)                   # instrument -> weight decided at the last decision
    prev_held: dict = field(default_factory=dict)              # the weights held before (the |dw| the costs charge)
    carried: dict = field(default_factory=dict)                # instrument -> target of a non-fillable order carried
    nav_failures: int = 0                                      # consecutive decisions with no whole-book NAV
    limit_met: bool | None = None                              # breach cure: post-action target meets the limit
    heartbeat_restored_utc: str | None = None
    neutralised: dict = field(default_factory=dict)            # R-18: rule_id -> framework-change event_id (M6 hook)

    def __post_init__(self):
        kind, market = parse_book_id(self.book_id)
        if market is not None and self.market not in (None, market):
            raise ValueError("%s belongs to market %s, not %s" % (self.book_id, market, self.market))
        if market is not None and self.market is None:
            object.__setattr__(self, "market", market)
        if self.market is not None and self.market not in MARKETS:
            raise ValueError("unknown market %r (section 6.1: %s)" % (self.market, ", ".join(MARKETS)))

    @property
    def halted(self) -> bool:
        return self.mode is EngineMode.HALTED


def post_rearm_cap(book: BookRuntime) -> float:
    """The post_rearm_cap term of min() for the weights decided at this decision (1.0 outside the window)."""
    return POST_REARM_CAP if book.mode is EngineMode.ARMED and book.post_rearm_left > 0 else 1.0


def to_runtime_entry(book: BookRuntime) -> dict:
    """The book's `macro_state.runtime[]` entry (section 6.1, L3608-3623), exactly those keys."""
    return {
        "book_id": book.book_id,
        "engine_state": book.mode.value,
        "halt": json.loads(json.dumps(book.halt)) if book.halt is not None else None,
        "post_rearm_cap_until": book.post_rearm_cap_until.isoformat() if book.post_rearm_cap_until else None,
        "nav": book.nav, "hwm_hard": book.hwm_hard, "ref_step": book.ref_step,
        "consecutive_failures": dict(book.consecutive_failures),
        "book_counter": book.book_counter,
    }


# --------------------------------------------------------------------------- #
# halt block helpers (section 6.1 shape; top level restates causes[0], L1179)
# --------------------------------------------------------------------------- #
def _cause(cls: str, reason_code: str, since: str, rearm_mode: str, rearm_not_before: date | None) -> dict:
    return {"class": cls, "reason_code": reason_code, "since_utc": since, "rearm_mode": rearm_mode,
            "rearm_not_before": rearm_not_before.isoformat() if rearm_not_before else None, "cleared_utc": None}


def _halt_block(causes: list[dict], component, series_id, ack_by=None, ack_utc=None) -> dict:
    first = causes[0]
    uncleared = [c for c in causes if not c.get("cleared_utc")]
    return {"class": first["class"], "reason_code": first["reason_code"], "component": component,
            "series_id": series_id, "since_utc": first["since_utc"], "rearm_not_before": first["rearm_not_before"],
            "rearm_mode": "operator" if any(c["rearm_mode"] == "operator" for c in uncleared) else "auto",
            "causes": causes, "ack_by": ack_by, "ack_utc": ack_utc}


# --------------------------------------------------------------------------- #
# registry: one JSON file per book under <path>/books/, governance log beside it
# --------------------------------------------------------------------------- #
class BookRegistry:
    """Loads every `<path>/books/*.json` at construction; `save` writes atomically; `event` appends to the log.

    `clock` (zero-arg, tz-aware) stamps governance events; without one the decision instant is the stamp.
    `sessions(market) -> sorted session dates` is needed only by the RISK rule.
    """

    def __init__(self, path: Path, clock: Callable[[], datetime] | None = None, *,
                 sessions: Callable[[str], Sequence[date]] | None = None, governance_log: Path | None = None):
        self.path = Path(path)
        self.books_dir = self.path / "books"
        self.log = Path(governance_log) if governance_log else self.path / "governance_events.jsonl"
        self.clock, self.sessions = clock, sessions
        self._lock = threading.RLock()   # ponytail: guards single saves only; the workflow steps a book from one thread
        self._books: dict[str, BookRuntime] = {}
        for file in sorted(self.books_dir.glob("*.json")) if self.books_dir.is_dir() else []:
            book = _from_dict(json.loads(file.read_text(encoding="utf-8")))   # a corrupt file raises: never dropped
            if file.name != _file_name(book.book_id):
                raise ValueError("book file %s holds %s" % (file, book.book_id))
            self._books[book.book_id] = book

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._books))

    def all(self) -> tuple[BookRuntime, ...]:
        return tuple(self._books[k] for k in self.ids())

    def get(self, book_id: str) -> BookRuntime:
        try:
            return self._books[book_id]
        except KeyError:
            raise KeyError("book %r is not registered" % (book_id,)) from None

    def register(self, book: BookRuntime) -> BookRuntime:
        with self._lock:
            if book.book_id in self._books:
                raise ValueError("book %s is already registered" % book.book_id)
            return self.save(book)

    def save(self, book: BookRuntime) -> BookRuntime:
        with self._lock:
            self.books_dir.mkdir(parents=True, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=str(self.books_dir), suffix=".tmp")
            try:
                with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(_to_dict(book), fh, indent=2, ensure_ascii=False, sort_keys=True)
                os.replace(temp, self.books_dir / _file_name(book.book_id))
            except BaseException:
                if os.path.exists(temp):
                    os.unlink(temp)
                raise                                            # fail closed: a lost book state is never silent
            self._books[book.book_id] = book
            return book

    def event(self, kind: str, book: BookRuntime, decision_utc: datetime, *, actor: str, reason: str,
              key: str = "engine_state", old=None, new=None) -> str:
        ev = {"kind": kind, "book_id": book.book_id, "rule_id": None, "key": key, "old": old, "new": new,
              "actor": actor, "reason": reason, "refs": list(_REFS),
              "utc": _iso(self.clock() if self.clock else decision_utc)}
        return G.append_event(self.log, ev)

    def runtime_entries(self) -> list[dict]:
        return [to_runtime_entry(b) for b in self.all()]

    def session_offset(self, market: str | None, session: date, n: int) -> date:
        """The session `n` sessions after `session` on the market's calendar; refuses without a calendar."""
        if market is None or self.sessions is None:
            raise ValueError("RISK re-arm counting needs the book's primary market and a sessions(market) calendar")
        cal = list(self.sessions(market))
        if session not in cal:
            raise ValueError("%s is not a %s session" % (session, market))
        i = cal.index(session) + n
        if i >= len(cal):
            raise ValueError("calendar_coverage: %s has no session %d after %s" % (market, n, session))
        return cal[i]


def _file_name(book_id: str) -> str:
    return quote(book_id, safe="") + ".json"


def _to_dict(book: BookRuntime) -> dict:
    d = dataclasses.asdict(book)
    d["mode"] = book.mode.value
    d["post_rearm_cap_until"] = book.post_rearm_cap_until.isoformat() if book.post_rearm_cap_until else None
    d["version"] = 1
    return d


def _from_dict(d: dict) -> BookRuntime:
    d = dict(d)
    d.pop("version", None)
    d["mode"] = EngineMode(d["mode"])
    d["post_rearm_cap_until"] = date.fromisoformat(d["post_rearm_cap_until"]) if d.get("post_rearm_cap_until") else None
    return BookRuntime(**d)


def create_default_books(registry: BookRegistry, markets: Iterable[str]) -> tuple[BookRuntime, ...]:
    """recommended:<m> and specification:<m> for every market, DISARMED; existing books are left as they are."""
    out = []
    for m in markets:
        for kind in ("recommended", "specification"):
            bid = "%s:%s" % (kind, m)
            out.append(registry.get(bid) if bid in registry.ids() else registry.register(BookRuntime(bid)))
    return tuple(out)


def ever_armed(registry: BookRegistry, book_id: str) -> bool:
    """False only before the book's first ARMED decision: a short history is warm-up (neutral 1.0) only then (L1111)."""
    return registry.get(book_id).ever_armed


def card_trio(registry: BookRegistry, book_id: str) -> tuple[str, ...]:
    """A card's registered on / off / S book ids (retired and killed together, L1180); any other id alone."""
    kind, _ = parse_book_id(book_id)
    if kind != "card":
        return (book_id,)
    prefix = book_id.rsplit(":", 1)[0] + ":"
    return tuple(b for b in registry.ids() if b.startswith(prefix))


def _switch(book: BookRuntime, to: EngineMode) -> dict:
    key = "%s->%s" % (book.mode.value, to.value)
    counts = dict(book.switch_counts)
    counts[key] = counts.get(key, 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# transitions
# --------------------------------------------------------------------------- #
def arm(registry: BookRegistry, book_id: str, decision_utc: datetime) -> BookRuntime:
    """DISARMED -> ARMED, automatic from the initial state only; the caller has checked inputs, calendars, header."""
    book = registry.get(book_id)
    if book.mode is EngineMode.ARMED:
        return book
    if book.mode is EngineMode.HALTED:
        raise ValueError("%s is HALTED: use runtime_rearm" % book_id)
    if book.ever_armed:
        raise ValueError("%s is retired: a retired book never re-arms (L1180)" % book_id)
    new = replace(book, mode=EngineMode.ARMED, ever_armed=True, consecutive_failures={}, book_counter=0,
                  switch_counts=_switch(book, EngineMode.ARMED))
    registry.save(new)
    registry.event("book_state", new, decision_utc, actor="runtime", old="DISARMED", new="ARMED",
                   reason="every acting input bound to the book fresh and past warm-up; calendars cover 60 sessions or more")
    return new


def retire(registry: BookRegistry, book_id: str, decision_utc: datetime, by: str, reason: str = "retired") -> BookRuntime:
    """ARMED or HALTED -> DISARMED: owner action only, logged; never re-arms. A card's on / off / S books are
    retired together, never singly (L1180): the named book's state is returned."""
    if not by:
        raise ValueError("retiring a book names the owner")
    for bid in card_trio(registry, book_id):
        book = registry.get(bid)
        if book.mode is EngineMode.DISARMED:
            continue
        new = replace(book, mode=EngineMode.DISARMED, halt=None, post_rearm_left=0, post_rearm_cap_until=None,
                      switch_counts=_switch(book, EngineMode.DISARMED))
        registry.save(new)
        registry.event("book_state", new, decision_utc, actor="owner", old=book.mode.value, new="DISARMED",
                       reason="%s (by %s)" % (reason, by))
    return registry.get(book_id)


class Kill(NamedTuple):
    books: tuple                   # the HALTED BookRuntime(s)
    integrity_trigger: bool        # a kill of a card's forward books is an R-25 operational integrity trigger (L1186)


def operator_kill(registry: BookRegistry, book_id: str, operator: str, decision_utc: datetime) -> Kill:
    """`runtime_halt(book, "OPS", "operator_kill")`: logged, re-armed by the operator, never a demotion; a card book's
    kill reaches all three of its books and is the R-25 integrity trigger the M8 forward monitor consumes."""
    if not operator:
        raise ValueError("an operator kill names the operator")
    ids = card_trio(registry, book_id)
    books = tuple(runtime_halt(registry, b, "OPS", "operator_kill", decision_utc, component="operator:%s" % operator)
                  for b in ids)
    return Kill(books, parse_book_id(book_id)[0] == "card")


def coverage_halt(registry: BookRegistry, decision_utc: datetime, component: str = "core/calendars"):
    """The `halt(book_id, cls, reason)` hook of `core.calendars.store.check_coverage` bound to this registry and
    decision: every book that reads a calendar whose coverage the decision date has left HALTs (OPS,
    `calendar_coverage`); the OPS re-arm is automatic once the decision date is inside coverage again."""
    return lambda book_id, cls, reason: runtime_halt(registry, book_id, cls, reason, decision_utc, component=component)


def runtime_halt(registry: BookRegistry, book_id: str, cls: str, reason: str, decision_utc: datetime,
                 component: str | None = None, series_id: str | None = None) -> BookRuntime:
    """HALT that book only. Idempotent per cause (same class and reason_code); a new cause joins halt.causes[];
    never extends rearm_not_before, never resets a reference. A DISARMED book holds nothing: no-op."""
    if cls not in CLASSES:
        raise ValueError("halt class must be RISK or OPS, not %r" % (cls,))
    if not reason:
        raise ValueError("a HALT names its reason_code")
    book = registry.get(book_id)
    if book.mode is EngineMode.DISARMED:
        return book
    key = _reason_key(reason)
    if cls == "RISK" and key not in RISK_REASONS:
        raise ValueError("RISK reason_code must be one of %s" % (RISK_REASONS,))
    causes = [dict(c) for c in (book.halt or {}).get("causes", [])]
    if any(c["class"] == cls and c["reason_code"] == reason and not c.get("cleared_utc") for c in causes):
        return book                                               # idempotent for its own cause
    session = _session(decision_utc)
    if cls == "RISK":
        cause = _cause(cls, reason, _iso(decision_utc), "auto",
                       registry.session_offset(book.market, session, REARM_REFUSED_SESSIONS))
    else:
        cause = _cause(cls, reason, _iso(decision_utc), "operator" if key in OPERATOR_REARM else "auto", None)
    causes.append(cause)
    old = book.halt or {}
    halt = _halt_block(causes, old.get("component", component) if book.halt else component,
                       old.get("series_id", series_id) if book.halt else series_id,
                       old.get("ack_by"), old.get("ack_utc"))
    was = book.mode
    new = replace(book, mode=EngineMode.HALTED, halt=halt,
                  switch_counts=_switch(book, EngineMode.HALTED) if was is not EngineMode.HALTED else book.switch_counts)
    registry.save(new)
    registry.event("halt", new, decision_utc, actor="runtime", old=was.value, new="HALTED",
                   reason="%s %s%s%s" % (cls, reason, " component=%s" % component if component else "",
                                         " series=%s" % series_id if series_id else ""))
    return new


def runtime_rearm(registry: BookRegistry, book_id: str, mode: str, decision_utc: datetime,
                  operator: str | None = None, cleared: Iterable[str] | None = None) -> BookRuntime:
    """HALTED -> ARMED once every cause has cleared under its own rule; otherwise raises RearmRefused.

    RISK causes clear at the decision whose session is >= rearm_not_before (t+10), in either mode; a
    `risk_limit_breach` cause also needs its cure: `book.limit_met` (written by `risk_step` from the post-action
    target) must not be False (None = no cure test supplied, the M1 contract; a HALTED book's zero exposure never
    counts, L1179). OPS auto causes clear when the caller certifies them (`cleared` names reason codes; None = every
    OPS auto cause). Operator-mode causes clear only with mode="operator" and a named operator. Partial clears are
    recorded (`cleared_utc`) even when the book stays HALTED.
    """
    if mode not in ("auto", "operator"):
        raise ValueError("re-arm mode is auto or operator")
    if mode == "operator" and not operator:
        raise ValueError("an operator re-arm names the operator")
    book = registry.get(book_id)
    if book.mode is not EngineMode.HALTED or not book.halt:
        raise RearmRefused("%s is %s, not HALTED" % (book_id, book.mode.value))
    session, now = _session(decision_utc), _iso(decision_utc)
    certified = None if cleared is None else set(cleared)
    causes, blocking = [], []
    for c in book.halt["causes"]:
        c = dict(c)
        if not c.get("cleared_utc"):
            if c["class"] == "RISK":
                nb = date.fromisoformat(c["rearm_not_before"]) if c.get("rearm_not_before") else None
                if nb is not None and session < nb:
                    blocking.append("%s refused before %s" % (c["reason_code"], nb))
                elif _reason_key(c["reason_code"]) == BREACH_REASON and book.limit_met is False:
                    blocking.append("%s: the post-action target does not meet the limit (a HALTED book's zero "
                                    "exposure never counts, L1179)" % c["reason_code"])
                else:
                    c["cleared_utc"] = now
            elif c["rearm_mode"] == "operator":
                if mode == "operator":
                    c["cleared_utc"] = now
                else:
                    blocking.append("%s needs an operator re-arm" % c["reason_code"])
            elif certified is None or c["reason_code"] in certified:
                c["cleared_utc"] = now
            else:
                blocking.append("%s has not cleared" % c["reason_code"])
        causes.append(c)
    halt = _halt_block(causes, book.halt.get("component"), book.halt.get("series_id"),
                       book.halt.get("ack_by"), book.halt.get("ack_utc"))
    if blocking:
        registry.save(replace(book, halt=halt))
        raise RearmRefused("%s stays HALTED: %s" % (book_id, "; ".join(blocking)))
    risk = any(c["class"] == "RISK" for c in causes)
    hard = any(c["reason_code"] == "hard_stop" for c in causes)
    new = replace(
        book, mode=EngineMode.ARMED, halt=None, ever_armed=True, switch_counts=_switch(book, EngineMode.ARMED),
        limit_met=None, heartbeat_restored_utc=None,
        # the cap window starts at the actual re-arm decision (L1179); an OPS re-arm leaves a running window alone
        post_rearm_left=POST_REARM_DECISIONS if risk else book.post_rearm_left,
        post_rearm_cap_until=(registry.session_offset(book.market, session, POST_REARM_DECISIONS - 1)
                              if risk else book.post_rearm_cap_until),
        # after a hard stop both references reset to the NAV at re-arm; a breach or an OPS cause resets nothing
        hwm_hard=book.nav if hard else book.hwm_hard, ref_step=book.nav if hard else book.ref_step)
    registry.save(new)
    registry.event("rearm", new, decision_utc, actor="operator" if mode == "operator" else "runtime",
                   old="HALTED", new="ARMED",
                   reason="%s re-arm%s; causes cleared: %s%s" % (
                       mode, " by %s" % operator if operator else "", ", ".join(c["reason_code"] for c in causes),
                       "; post_rearm_cap 0.5 for %d decisions" % POST_REARM_DECISIONS if risk else ""))
    return new


def acknowledge(registry: BookRegistry, book_id: str, by: str, when: datetime) -> BookRuntime:
    """Operator acknowledgement of a HALT: logged, never required for a re-arm (L1179)."""
    book = registry.get(book_id)
    if book.mode is not EngineMode.HALTED or not book.halt:
        raise ValueError("%s is not HALTED" % book_id)
    if not by:
        raise ValueError("an acknowledgement names the operator")
    halt = dict(book.halt, ack_by=by, ack_utc=_iso(when))
    new = replace(book, halt=halt)
    registry.save(new)
    registry.event("book_state", new, when, actor="operator", key="halt.ack_by", old=book.halt.get("ack_by"),
                   new=by, reason="operator acknowledged the HALT (logged, never required)")
    return new


class StepResult(NamedTuple):
    book: BookRuntime
    post_rearm_cap: float          # the min() term for the weights decided at this decision


def step_decision(registry: BookRegistry, book_id: str, decision_utc: datetime, ok: bool, *,
                  failed: Iterable[str] = (), limits: Mapping[str, int] | None = None,
                  default_limit: int = DEFAULT_LIMIT, book_limit: int = BOOK_LIMIT) -> StepResult:
    """One decision of one book (R-19 rule 4). `ok` = every acting input bound to the book is fresh; `failed`
    names the acting series that failed closed (`limits` their halt_after_consecutive_decisions; default 2).
    `ok=False` with no series = an acting step error counted on the book counter.

    Counters advance; at their limit the book HALTs (OPS) with reason `acting_input_stale:<series>` or the
    book-counter reason; a fresh decision resets them and auto re-arms a book HALTED on input causes. A DISARMED
    book never HALTs (warm-up before the first ARMED decision is not a failure). Call once per decision, last.
    """
    failed = tuple(dict.fromkeys(failed))
    if ok and failed:
        raise ValueError("ok=True contradicts failed=%r" % (failed,))
    limits = dict(limits or {})
    book = registry.get(book_id)
    cf = {s: n for s, n in book.consecutive_failures.items() if s in failed}
    for s in failed:
        cf[s] = cf.get(s, 0) + 1
    default_hit = (not ok) and (not failed or any(limits.get(s, default_limit) == default_limit for s in failed))
    book = registry.save(replace(book, consecutive_failures=cf, book_counter=book.book_counter + 1 if default_hit else 0))
    if ok and book.mode is EngineMode.HALTED:
        inputs = [c["reason_code"] for c in book.halt["causes"]
                  if c["reason_code"].startswith(INPUT_STALE) or c["reason_code"] in (BOOK_COUNTER_REASON, STEP_ERROR_REASON)]
        try:
            runtime_rearm(registry, book_id, "auto", decision_utc, cleared=inputs)
        except RearmRefused:
            pass                                                   # stays HALTED under another cause's rule
    elif not ok and book.mode is not EngineMode.DISARMED:
        at_limit = [s for s in failed if cf[s] >= limits.get(s, default_limit)]
        for s in at_limit:
            runtime_halt(registry, book_id, "OPS", INPUT_STALE + s, decision_utc, series_id=s)
        if default_hit and not at_limit and book.book_counter >= book_limit:   # inputs failing on alternate decisions
            runtime_halt(registry, book_id, "OPS", BOOK_COUNTER_REASON if failed else STEP_ERROR_REASON,
                         decision_utc, series_id=failed[-1] if failed else None)
    book = registry.get(book_id)
    cap = post_rearm_cap(book)
    if cap < 1.0:
        book = registry.save(replace(book, post_rearm_left=book.post_rearm_left - 1))
    return StepResult(book, cap)


# --------------------------------------------------------------------------- #
# M5: R-07 hard stop / R-31 ladder carrier, NAV counter, breach cure (brief B.0 steps 1-3)
# --------------------------------------------------------------------------- #
def _rl():
    from core.quant import risk_layer                            # lazy: keeps this module's import light
    return risk_layer


def rearm_not_before(book: BookRuntime) -> date | None:
    """The latest `rearm_not_before` among the uncleared RISK causes (F-24); None when none."""
    dates = [date.fromisoformat(c["rearm_not_before"]) for c in (book.halt or {}).get("causes", [])
             if c["class"] == "RISK" and not c.get("cleared_utc") and c.get("rearm_not_before")]
    return max(dates) if dates else None


def ladder_state(book: BookRuntime, binding_share: float | None = None):
    """The book's `LadderState` (R-31 names, L3271) from its persisted carriers; `post_rearm_left` counts the
    decisions still carrying the 0.5 cap, this one included (read before `step_decision` decrements it)."""
    RL = _rl()
    return RL.LadderState(book.hwm_hard, book.ref_step, book.step_mult, book.dwell_left, book.block_new_entries,
                          book.halted, rearm_not_before(book), book.post_rearm_left, binding_share)


class RiskStep(NamedTuple):
    book: BookRuntime
    ladder: object                 # risk_layer.LadderState after this decision
    halted_now: bool               # the hard stop fired at this decision
    alert: dict | None             # NAV unavailable (step state held, hard stop still armed; L3337)


def risk_step(registry: BookRegistry, book_id: str, decision_utc: datetime, nav, *, rules=None, config=None,
              limit_met: bool | None = None, level_ref: str | None = None) -> RiskStep:
    """One decision of R-07 / R-31 on the book's whole-book NAV, before the composition and before `step_decision`.

    1. `nav` None (or a MissingInput): the step state is held, an alert raised, the NAV counter advances; at
       `NAV_LIMIT` the book HALTs (OPS, `whole_book_nav_unavailable_gt_2_decisions`), re-armed automatically at the
       first decision with a NAV (no reset, no cap). The hard stop stays armed on the last NAV.
    2. HALTED: the re-arm is attempted (RISK causes at or after t+10; a breach only with `limit_met` True; input
       causes stay with `step_decision`; other OPS causes with their own clearers).
    3. ARMED (recommended / specification books only, F-2): `risk_layer.ladder_step`; a hard stop HALTs the book
       (RISK, `hard_stop`, component drawdown_ladder, a governance review event) with the steps cleared.
    The level is D2 through the R-31 card's `{ref}` (`level_ref`, default risk_layer.drawdown.hard_stop.level).
    """
    RL = _rl()
    cfg = config if isinstance(config, RL.LadderConfig) else RL.ladder_config(rules, level_ref=level_ref or RL.HARD_STOP_LEVEL_REF)
    book = registry.get(book_id)
    if nav is not None and not isinstance(nav, (int, float)):
        nav = None                                               # a MissingInput: NAV unavailable
    alert = None
    if nav is None:
        n = book.nav_failures + 1
        book = registry.save(replace(book, nav_failures=n))
        alert = RL.alert("WHOLE_BOOK_NAV_UNAVAILABLE", "book_nav", decision_utc, series_id="NAV_LINE_CLOSES",
                         books=(book_id,), severity="page" if n >= NAV_LIMIT else "warn", escalated=n >= NAV_LIMIT)
        if n >= NAV_LIMIT and book.mode is EngineMode.ARMED:
            book = runtime_halt(registry, book_id, "OPS", NAV_REASON, decision_utc, component="book_nav", series_id="NAV_LINE_CLOSES")
        return RiskStep(book, ladder_state(book), False, alert)
    # the turnover |held - prev_held| book_nav charged is consumed with this NAV: an unrecorded decision never pays it twice
    book = registry.save(replace(book, nav=float(nav), nav_failures=0, limit_met=limit_met, prev_held=dict(book.held)))
    if book.mode is EngineMode.HALTED:
        try:
            book = runtime_rearm(registry, book_id, "auto", decision_utc, cleared=[NAV_REASON])
        except RearmRefused:
            book = registry.get(book_id)                         # stays HALTED under another cause's rule
    if book.mode is not EngineMode.ARMED or parse_book_id(book_id)[0] not in RISK_BOOKS:
        return RiskStep(book, ladder_state(book), False, alert)
    state = RL.ladder_step(ladder_state(book), float(nav), cfg)
    book = registry.save(replace(book, hwm_hard=state.hwm_hard, ref_step=state.ref_step, step_mult=state.step_mult,
                                 dwell_left=state.dwell_left, block_new_entries=state.block_new_entries))
    if state.halted:
        book = runtime_halt(registry, book_id, "RISK", "hard_stop", decision_utc, component="drawdown_ladder")
    return RiskStep(book, ladder_state(book), state.halted, alert)


hard_stop_check = risk_step        # the task's name: hard_stop_check(registry, book_id, decision_utc, nav, level_ref=...)


# --------------------------------------------------------------------------- #
# M5: NAV valuation and the weight books (section 3.8 L1181, L1184, L1187; R-02 no reallocation)
# --------------------------------------------------------------------------- #
def _ledger_path(registry: BookRegistry, book_id: str) -> Path:
    return registry.books_dir / (quote(book_id, safe="") + ".ledger.jsonl")


def _check_weights(w: Mapping[str, float], what: str) -> dict:
    out = {}
    for i, x in w.items():
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not (abs(float(x)) <= 1.0 + WEIGHT_TOL):
            raise ValueError("%s weight %r for %s outside [-1, 1] (nothing above 1.0, P2)" % (what, x, i))
        out[str(i)] = float(x)
    if sum(abs(x) for x in out.values()) > 1.0 + WEIGHT_TOL:
        raise ValueError("%s gross %.6f > 1.0: a weight path above 1.0 is a refused configuration (P2)" % (what, sum(abs(x) for x in out.values())))
    return out


def book_nav(registry: BookRegistry, book_id: str, returns: Mapping[str, float] | None, costs: Mapping[str, float], *,
             nav0: float = 1.0) -> float | None:
    """The whole-book NAV at this decision from the ledger: the weights decided at the previous decision (`held`)
    earn `returns` (instrument -> simple return from the previous close to this close, already in the book's NAV
    currency through nav_fx), and |held - prev_held| is charged `costs` (bp per side, the tick floor applied) on this
    earning day; the initial entry is free (costed_path's convention, bit-identical). None when a held instrument
    has no return (NAV unavailable: fail closed, never interpolated); a missing cost raises (never defaulted)."""
    book = registry.get(book_id)
    base = nav0 if book.nav is None else book.nav
    if not book.held:
        return float(base)
    if returns is None:
        return None
    gross, charge = 0.0, 0.0
    for i, w in book.held.items():
        r = returns.get(i)
        if w != 0.0 and (r is None or not math.isfinite(float(r))):
            return None
        gross += w * float(r or 0.0)
        dw = abs(w - book.prev_held.get(i, 0.0))
        if dw > WEIGHT_TOL and book.prev_held:
            if i not in costs:
                raise ValueError("no pre-registered cost for %s: never defaulted (P10)" % i)
            charge += dw * float(costs[i]) * 1e-4
    for i, w0 in book.prev_held.items():                        # an exit also pays its |dw|
        if i not in book.held and abs(w0) > WEIGHT_TOL:
            if i not in costs:
                raise ValueError("no pre-registered cost for %s: never defaulted (P10)" % i)
            charge += abs(w0) * float(costs[i]) * 1e-4
    return float(base) * (1.0 + gross - charge)


def new_entries(held: Mapping[str, float], target: Mapping[str, float]) -> tuple[str, ...]:
    """Rulings 3.6: a new entry is a decided target weight above the held weight of that instrument; decreases and
    exits are never new entries (so never blocked)."""
    return tuple(sorted(i for i, w in target.items() if float(w) > float(held.get(i, 0.0)) + WEIGHT_TOL))


class Decision(NamedTuple):
    book: BookRuntime
    nav: float | None
    target: dict                   # the weights as decided (0 when HALTED)
    post_action: dict              # what the book holds after blocks and carried orders
    new_entries: tuple
    blocked: tuple
    carried: dict


def record_decision(registry: BookRegistry, book_id: str, decision_utc: datetime, target: Mapping[str, float], *,
                    fillable: Mapping[str, bool] | None = None, block: bool | None = None) -> Decision:
    """Persist one decision of a weight book (brief B.0 steps 4-7): HALTED sets every target to 0 (the book earns 0
    from t+1, L1178); `block` (default: the book's own `block_new_entries` where the steps act, i.e. specification
    books) holds every new entry at its held weight; a non-fillable instrument (`fillable[i]` False: a limit-locked
    order, R-27) stays at its held weight and is carried. The post-action weights become `held`, the previous `held`
    becomes `prev_held` (the |dw| the next valuation charges); one ledger line is appended (binary append, raises)."""
    book = registry.get(book_id)
    tgt = _check_weights(target, "target")
    if book.halted:
        tgt = {i: 0.0 for i in tgt}
    if block is None:
        block = book.block_new_entries and _rl().steps_act_in(book_id, None)
    entries = new_entries(book.held, tgt)
    blocked = entries if block else ()
    post = dict(tgt)
    for i in blocked:
        post[i] = book.held.get(i, 0.0)
    carried = {}
    for i, w in tgt.items():
        if fillable is not None and not fillable.get(i, True) and abs(w - book.held.get(i, 0.0)) > WEIGHT_TOL:
            carried[i] = w
            post[i] = book.held.get(i, 0.0)
    for i, w0 in book.held.items():                             # an instrument the target drops is an exit to 0
        if i not in post and abs(w0) > WEIGHT_TOL:
            if fillable is not None and not fillable.get(i, True):
                carried[i], post[i] = 0.0, w0
            else:
                post[i] = 0.0
    post = {i: w for i, w in _check_weights(post, "post-action").items()}
    new = replace(book, held=post, prev_held=dict(book.held), carried=carried)
    registry.save(new)
    row = {"session": _session(decision_utc).isoformat(), "decision_utc": _iso(decision_utc), "engine_state": new.mode.value,
           "nav": new.nav, "target": tgt, "post_action": post, "new_entries": list(entries), "blocked": list(blocked),
           "carried": carried, "step_mult": new.step_mult, "post_rearm_cap": post_rearm_cap(new)}
    registry.books_dir.mkdir(parents=True, exist_ok=True)
    with open(_ledger_path(registry, book_id), "ab") as fh:       # fail closed: a lost ledger line raises
        fh.write((json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    return Decision(new, new.nav, tgt, post, entries, blocked, carried)


def ledger(registry: BookRegistry, book_id: str) -> list[dict]:
    path = _ledger_path(registry, book_id)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_bytes().decode("utf-8").split("\n") if line.strip()]


def nav_path(registry: BookRegistry, book_id: str) -> list[tuple[date, float]]:
    """(session, NAV) per recorded decision with a NAV: the whole-book path `risk_layer.drawdown_ladder` folds."""
    return [(date.fromisoformat(r["session"]), float(r["nav"])) for r in ledger(registry, book_id) if r.get("nav") is not None]


# --------------------------------------------------------------------------- #
# M6 hook (R-18): a framework change neutralises a macro-conditioned multiplier to 1.0 from the next decision
# --------------------------------------------------------------------------- #
def neutralise_rule(registry: BookRegistry, rule_id: str, event_id: str, decision_utc: datetime,
                    books: Iterable[str] | None = None) -> tuple[str, ...]:
    """The `neutralise(rule_id, event_id)` hook of `context_log.log_break`: record on every registered book (or
    `books`) that `rule_id` enters as 1.0 from the next decision (R-18 (i); no historical re-gate). Idempotent per
    (book, rule); the `record_reset` governance event is log_break's, written once per rule, not per book. Returns
    the book ids written. `decision_utc` is the decision the hook ran at (persisted beside the event id)."""
    if not rule_id or not event_id:
        raise ValueError("neutralise_rule names the rule and the framework-change event")
    out = []
    for bid in (tuple(books) if books is not None else registry.ids()):
        book = registry.get(bid)
        if book.neutralised.get(rule_id) == event_id:
            continue
        registry.save(replace(book, neutralised={**book.neutralised, rule_id: event_id}))
        out.append(bid)
    return tuple(out)


def neutralised_rules(registry: BookRegistry, book_id: str) -> dict:
    """{rule_id: event_id} the book carries: the `neutralised` argument of `build_overlay_decisions`."""
    return dict(registry.get(book_id).neutralised)


# --------------------------------------------------------------------------- #
# M5: feed heartbeat (OPS; synthetic-only against injected instants, F-11 / A-9)
# --------------------------------------------------------------------------- #
def heartbeat_check(registry: BookRegistry, book_id: str, now_utc: datetime, last_success_utc: datetime | None) -> BookRuntime:
    """Loss > 60 s during a session HALTs (OPS, `feed_heartbeat_loss_60s`; new intraday entries are blocked at once
    through the HALTED state); the book re-arms automatically once the feed has been restored for 5 minutes. Both
    instants are injected: no v2.0 daily book reads the QuoteFeed, so this trigger is exercised synthetically only."""
    book = registry.get(book_id)
    lost = last_success_utc is None or (now_utc - last_success_utc).total_seconds() > HEARTBEAT_LOSS_S
    if lost:
        if book.heartbeat_restored_utc:
            book = registry.save(replace(book, heartbeat_restored_utc=None))
        return runtime_halt(registry, book_id, "OPS", HEARTBEAT_REASON, now_utc, component="QuoteFeed") if book.mode is EngineMode.ARMED else book
    causes = (book.halt or {}).get("causes", [])
    if not any(c["reason_code"] == HEARTBEAT_REASON and not c.get("cleared_utc") for c in causes):
        return book
    if not book.heartbeat_restored_utc:
        return registry.save(replace(book, heartbeat_restored_utc=_iso(now_utc)))
    restored = datetime.fromisoformat(book.heartbeat_restored_utc.replace("Z", "+00:00"))
    if (now_utc - restored).total_seconds() < HEARTBEAT_RESTORED_S:
        return book
    try:
        return runtime_rearm(registry, book_id, "auto", now_utc, cleared=[HEARTBEAT_REASON])
    except RearmRefused:
        return registry.get(book_id)
