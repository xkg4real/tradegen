"""Series registry, data contracts, schedule-aware staleness, role-based failure actions (M1; R-19 rules 1-6;
P5, P16, P18; section 7 `data_contracts`).

`load_registry(path) -> Registry` (refuses: an acting binding without a contract, an acting/forward_sim binding
without a `books` key, a group name used as a series id, an unknown group or range-group member, a binding that
differs from the rules store's `data_contracts.roles`), `contract()`, `check_contract()`, `expected_available_utc()`
(the NEXT observation's due instant, never the age of last_obs), `is_stale() -> StaleCheck`, `on_input_failure()`,
`read_input()` (pit_value -> contract -> is_stale, the F-11 wrapper), `usable_cross_market()`,
`add_publication_bdays()`, `InputCounters` (per (book, series) and per book; HALT at the Nth miss, F-8).

Calendar functions come from a `clocks` object with close_print_bound_utc, publication_instant, next_expected_obs,
add_publication_bdays, is_session: `core.calendars.adapter.CalendarClocks` in production, `StubClocks` in tests.
Any calendar failure (unsigned file, coverage, unreadable schedule) is `CalendarUnavailable` here: every acting
input fails closed and the alert names the calendar (brief F-5).
Tests: T-SER-01/02, T-ROLE-01/02, T-STALE-01, T-H10-01, T-MISS-02, T-AVAIL-01, T-XMKT-01 (data clause).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from core.ficc import pit
from core.ficc.pit import MissingInput, PITStore, PITValue, PITError, named_series

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "data" / "macro" / "series_registry.yaml"
STORE_PATH = REPO_ROOT / "data" / "macro" / "rules_v2.0.0.json"
ROLES = pit.ROLES
CONSUMER_KINDS = ROLES
BOOK_KINDS = ("recommended", "specification")
DEFAULT_HALT_AFTER = 2            # data_contracts.on_failure.acting_exposure.halt_after_consecutive_decisions
BOOK_COUNTER_HALT_AFTER = 2       # ... book_counter_halt_after
CROSS_MARKET_BUFFER_S = 60        # data_contracts.cross_market.buffer_s
STATUS_OF = {"missing": "missing", "stale": "stale_missed_release", "provisional_intraday": "provisional_rejected",
             "session_mismatch": "session_mismatch", "synthetic_rejected": "synthetic_rejected"}
_BINDING_KEYS = ("role", "consumer", "books", "halt_after_consecutive_decisions", "action")


class RegistryError(ValueError):
    """The registry (or its agreement with the rules store) is refused at load; the message names the rule."""


class CalendarUnavailable(RuntimeError):
    """The publication calendar could not be read: every acting input fails closed (L1956)."""


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Binding:
    series_id: str
    role: str
    books: tuple[str, ...]
    consumer: str | None = None
    halt_after_consecutive_decisions: int = DEFAULT_HALT_AFTER
    action: str | None = None          # risk_model_covariance

    @property
    def dormant(self) -> bool:
        return self.role in ("acting_exposure", "forward_sim") and not self.books


@dataclass(frozen=True)
class DataContract:
    series_id: str
    dtype: str
    unit: str
    decimals: int
    range: tuple[float, float] | None
    abs_daily_return_max: float | None
    monotone_obs_date: bool
    schedule: str
    publication_schedule: dict
    grace_pub_bdays: int
    tolerance: dict
    obs_kind: str
    market: str | None
    timing_class: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class StaleCheck:
    """Fresh (reason None) | Stale("missing") | Stale("missed_release")."""
    reason: str | None = None

    @property
    def stale(self) -> bool:
        return self.reason is not None


def Fresh() -> StaleCheck:                  # noqa: N802  (spec names)
    return StaleCheck(None)


def Stale(reason: str) -> StaleCheck:       # noqa: N802
    if reason not in ("missing", "missed_release"):
        raise PITError(f"Stale reason {reason!r}: missing | missed_release")
    return StaleCheck(reason)


@dataclass(frozen=True)
class FailureAction:
    series_id: str
    role: str
    status: str                 # macro_state.inputs[].status
    action: str
    fail_closed: bool
    alert: bool
    halt: str                   # bound_books | never | that_book
    books: tuple[str, ...]
    counts: bool                # increments the failure counters
    sets: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Halt:
    book_id: str
    reason_code: str
    series_id: str


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Registry:
    series: dict
    groups: dict
    range_groups: dict
    group_bindings: dict
    consumers: dict
    schedules: dict
    primary_sources: dict
    path: Path
    md5: str

    def is_series(self, sid: str) -> bool:
        return sid in self.series

    def is_group(self, name: str) -> bool:
        return name in self.groups

    def members(self, name: str) -> tuple[str, ...]:
        return tuple(self.groups[name])

    def groups_of(self, sid: str) -> tuple[str, ...]:
        return tuple(g for g, m in self.groups.items() if sid in m)

    def obs_kind(self, sid: str) -> str:
        return self.series[sid]["obs_kind"]

    def market(self, sid: str) -> str | None:
        return self.series[sid].get("market")

    def schedule(self, sid: str) -> str:
        return self.series[sid]["schedule"]

    def bindings(self, sid: str) -> tuple[Binding, ...]:
        raw = list(self.series[sid].get("bindings") or [])
        for g in self.groups_of(sid):
            raw += list(self.group_bindings.get(g) or [])
        return tuple(_binding(sid, b) for b in raw)

    def resolve_binding(self, sid: str, consumer: str) -> Binding:
        """Exact consumer binding, else the consumer-less binding (binds every consumer), else: `nav` never raises
        (an acting binding to no book), a context consumer reads unbound, any other consumer raises (T-SER-02)."""
        if not self.is_series(sid):
            raise RegistryError(f"{sid!r} is not a registered series id" + (" (a group name)" if self.is_group(sid) else ""))
        bs = self.bindings(sid)
        for b in bs:
            if b.consumer == consumer:
                return b
        for b in bs:
            if b.consumer is None:
                return b
        if consumer == "nav":
            return Binding(sid, "acting_exposure", (), "nav")
        if self.consumers.get(consumer) == "context":
            return Binding(sid, "context", (), consumer)
        raise pit.UnboundConsumer(f"{consumer!r} has no binding for {sid} and is not a context consumer (R-19 rule 5)")

    def book_ids(self, b: Binding) -> tuple[str, ...]:
        """Bare book kinds -> `<kind>:<market>` of the series; qualified ids pass through."""
        market = self.market(b.series_id) or "KR"
        return tuple(f"{x}:{market}" if x in BOOK_KINDS else x for x in b.books)

    def series_ids(self) -> tuple[str, ...]:
        return tuple(self.series)


def _binding(sid: str, raw: dict) -> Binding:
    books = raw.get("books")
    return Binding(sid, raw["role"], tuple(books or ()), raw.get("consumer"),
                   int(raw.get("halt_after_consecutive_decisions", DEFAULT_HALT_AFTER)), raw.get("action"))


def _norm(entry) -> list[dict]:
    """A roles entry (scalar | mapping | list) as a list of mappings with the comparable keys only."""
    if isinstance(entry, str):
        entry = [{"role": entry}]
    elif isinstance(entry, dict):
        entry = [entry]
    out = []
    for e in entry:
        d = {k: e[k] for k in _BINDING_KEYS if k in e}
        if "books" in d:
            d["books"] = list(d["books"])
        out.append(d)
    return sorted(out, key=lambda d: str(sorted(d.items())))


def store_roles(path: Path = STORE_PATH) -> dict:
    import json
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(doc["data_contracts"]["roles"])


def _check_bindings(sid: str, raw_list, has_contract: bool, issues: list[str]) -> None:
    for b in raw_list or []:
        if not isinstance(b, dict) or b.get("role") not in ROLES:
            issues.append(f"{sid}: binding {b!r} has no valid role")
            continue
        if b["role"] in ("acting_exposure", "forward_sim") and "books" not in b:
            issues.append(f"{sid}: {b['role']} binding without a `books` key is refused (books: [] = dormant; T-ROLE-02)")
        if b.get("books") is not None and not isinstance(b["books"], list):
            issues.append(f"{sid}: books must be a list")
        if b["role"] == "acting_exposure" and not has_contract:
            issues.append(f"{sid}: an acting input without a contract cannot be registered (L1846)")


def load_registry(path=REGISTRY_PATH, *, roles: dict | None = None) -> Registry:
    """Load and validate; `roles` defaults to the shipped rules store's `data_contracts.roles` (a differing copy is
    refused, like an owner-decision literal). Pass `roles={}` to skip the cross-check."""
    path = Path(path)
    raw = path.read_bytes()
    doc = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("series"), dict):
        raise RegistryError(f"{path}: no `series` mapping")
    series = {k: v for k, v in doc["series"].items()}
    groups = {k: list(v) for k, v in (doc.get("groups") or {}).items()}
    range_groups = dict(doc.get("range_groups") or {})
    group_bindings = dict(doc.get("group_bindings") or {})
    consumers = dict(doc.get("consumers") or {})
    schedules = dict(doc.get("schedules") or {})
    issues: list[str] = []
    for sid, s in series.items():
        if not isinstance(s, dict):
            issues.append(f"{sid}: not a mapping")
            continue
        for k in ("source", "frequency", "obs_kind", "schedule", "grace_publication_bdays", "timing_class", "unit"):
            if k not in s:
                issues.append(f"{sid}: missing {k}")
        if s.get("obs_kind") not in pit.OBS_KINDS:
            issues.append(f"{sid}: obs_kind {s.get('obs_kind')!r}")
        if s.get("schedule") not in schedules:
            issues.append(f"{sid}: unknown schedule {s.get('schedule')!r}")
        if s.get("timing_class") not in ("live", "publication", "value_proxy"):
            issues.append(f"{sid}: timing_class {s.get('timing_class')!r}")
        if sid in groups:
            issues.append(f"{sid}: a group name is never a series id")
        if s.get("obs_kind") == "close" and not s.get("market"):
            issues.append(f"{sid}: a close-type series needs its market")
        _check_bindings(sid, s.get("bindings"), isinstance(s.get("contract"), dict), issues)
    for g, members in groups.items():
        for m in members:
            if m not in series:
                issues.append(f"group {g}: member {m!r} is not a registered series")
        has_contract = all(isinstance(series.get(m, {}).get("contract"), dict) for m in members)
        _check_bindings(g, group_bindings.get(g), has_contract, issues)
    for g in group_bindings:
        if g not in groups:
            issues.append(f"group_bindings {g}: no such group")
    for rg, spec in range_groups.items():
        for m in spec.get("members") or []:
            if m not in series:
                issues.append(f"range group {rg}: member {m!r} is not a registered series")
        if not (isinstance(spec.get("range"), list) and len(spec["range"]) == 2):
            issues.append(f"range group {rg}: range must be [lo, hi]")
    for c, kind in consumers.items():
        if kind not in CONSUMER_KINDS:
            issues.append(f"consumer {c}: kind {kind!r}")
    if roles is None:
        roles = store_roles()
    for sid, entry in roles.items():
        if sid in groups:
            have = group_bindings.get(sid)
        elif sid in series:
            have = series[sid].get("bindings")
        else:
            issues.append(f"rules store roles: {sid!r} is neither a series nor a group (T-SER-02)")
            continue
        if _norm(entry) != _norm(have or []):
            issues.append(f"{sid}: registry bindings {_norm(have or [])} differ from data_contracts.roles {_norm(entry)}")
    if issues:
        raise RegistryError(f"{path.name}: " + "; ".join(issues[:12]) + ("" if len(issues) <= 12 else f"; +{len(issues) - 12}"))
    return Registry(series, groups, range_groups, group_bindings, consumers, schedules,
                    dict(doc.get("primary_sources") or {}), path, hashlib.md5(raw).hexdigest())


_DEFAULT: Registry | None = None


def default_registry() -> Registry:
    """The shipped registry, loaded once per process (it is read-only; T-HERM-02)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load_registry()
    return _DEFAULT


def referenced_ids(store_doc: dict) -> set[str]:
    """Series ids the rules store names outside `roles` (data.usdkrw, data.us10y, brent, card nav_fx)."""
    data = store_doc.get("data", {})
    ids = set(data.get("usdkrw", {}).get("input", [])) | {data.get("usdkrw", {}).get("proxy")}
    ids |= {data.get("us10y", {}).get("production")} | set(data.get("us10y", {}).get("history", []))
    ids |= set(data.get("brent_series", {}).values())
    ids |= {data.get("us10y", {}).get("live_proxy_history")}
    for card in store_doc.get("cards", {}).values():
        nav_fx = card.get("nav_fx") if isinstance(card, dict) else None
        if isinstance(nav_fx, dict):
            ids |= {nav_fx.get("series"), nav_fx.get("history")}
    return {i for i in ids if isinstance(i, str)}


_ALIAS = {"TREASURY_PAR": "UST_PAR_10Y"}      # data.us10y.history names the channel; the series id is UST_PAR_10Y


def unknown_ids(registry: Registry, ids) -> list[str]:
    return sorted(i for i in ids if not registry.is_series(_ALIAS.get(i, i)) and not registry.is_group(i))


# --------------------------------------------------------------------------- #
# Contract (R-19 rules 1 and 4)
# --------------------------------------------------------------------------- #
def contract(registry: Registry, series_id: str) -> DataContract:
    series_id = named_series(series_id)
    if not registry.is_series(series_id):
        raise RegistryError(f"{series_id!r}: unknown series id" + (" (a group name)" if registry.is_group(series_id) else ""))
    s = registry.series[series_id]
    c = s.get("contract") or {}
    rng = s.get("range")
    for rg, spec in registry.range_groups.items():
        if series_id in (spec.get("members") or []):
            rng = spec["range"]
    return DataContract(series_id, str(c.get("dtype", "float")), str(c.get("unit") or s.get("unit", "")),
                        int(c.get("decimals", 4)), tuple(float(x) for x in rng) if rng else None,
                        s.get("abs_daily_return_max"), True, s["schedule"], dict(s.get("publication_schedule") or {}),
                        int(s.get("grace_publication_bdays", 1)), dict(s.get("tolerance") or {}), s["obs_kind"],
                        s.get("market"), s["timing_class"], tuple(sorted({b.role for b in registry.bindings(series_id)})))


def check_contract(c: DataContract, value: float, *, previous: float | None = None,
                   obs_date: date | None = None, previous_date: date | None = None) -> str | None:
    """None when the value honours its contract, else the violation (a missing input with the role's action)."""
    if value is None or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return "schema: value is not a finite number"
    if c.range and not (c.range[0] <= float(value) <= c.range[1]):
        return f"range: {value} outside [{c.range[0]}, {c.range[1]}] {c.unit}"
    if c.abs_daily_return_max is not None and previous:
        r = abs(float(value) / float(previous) - 1.0)
        if r > c.abs_daily_return_max:
            return f"range: |daily return| {r:.4f} > {c.abs_daily_return_max}"
    if c.monotone_obs_date and obs_date and previous_date and obs_date <= previous_date:
        return f"monotone: obs_date {obs_date} <= previous {previous_date}"
    return None


# --------------------------------------------------------------------------- #
# Staleness (R-19 steps 2-3, normative)
# --------------------------------------------------------------------------- #
def _calendar_call(series_id: str, fn, *args):
    """Run one clocks call; any calendar failure (CalendarUnsigned, CalendarCoverageError, an unreadable schedule)
    becomes CalendarUnavailable whose message names the calendar, so the input fails closed (never age-based)."""
    try:
        return fn(*args)
    except (CalendarUnavailable, PITError, RegistryError):
        raise
    except Exception as exc:
        raise CalendarUnavailable(f"{series_id}: publication calendar unreadable ({type(exc).__name__}: {exc})") from exc


def expected_available_utc(registry: Registry, series_id: str, last_obs: date, clocks) -> datetime | None:
    """When the NEXT observation after `last_obs` is due: publication_instant(series, next_expected_obs(series,
    last_obs)). Never the availability of last_obs itself (L1015-1017; the negative control flags H.10 on ~80%)."""
    series_id = named_series(series_id)
    if not registry.is_series(series_id):
        raise RegistryError(f"{series_id!r}: unknown series id")
    d_next = _calendar_call(series_id, clocks.next_expected_obs, series_id, last_obs)
    return None if d_next is None else _calendar_call(series_id, clocks.publication_instant, series_id, d_next)


def add_publication_bdays(series_id: str, instant: datetime, n: int, clocks) -> datetime:
    """`n` publication business days after `instant` on the series' publication calendar."""
    return _calendar_call(series_id, clocks.add_publication_bdays, series_id, instant, int(n))


def stale_deadline_utc(registry: Registry, series_id: str, last_obs: date, clocks) -> datetime | None:
    due = expected_available_utc(registry, series_id, last_obs, clocks)
    if due is None:
        return None
    return add_publication_bdays(series_id, due, contract(registry, series_id).grace_pub_bdays, clocks)


def is_stale(store: PITStore, registry: Registry, series_id: str, decision_utc: datetime, knowledge_utc: datetime,
             clocks) -> StaleCheck:
    """R-19 step 3 verbatim: no visible record -> Stale("missing"); decision_utc > deadline -> Stale("missed_release");
    else Fresh. A schedule without an expected instant (as-posted, live quotes) cannot miss a release."""
    rec = pit.pit_last(store, series_id, decision_utc, knowledge_utc, registry=registry)
    if rec is None:
        return Stale("missing")
    deadline = stale_deadline_utc(registry, series_id, rec.obs_date, clocks)
    if deadline is not None and decision_utc > deadline:
        return Stale("missed_release")
    return Fresh()


# --------------------------------------------------------------------------- #
# Failure action by role (R-19 rule 4; section 7 data_contracts.on_failure)
# --------------------------------------------------------------------------- #
def on_input_failure(series_id: str, check, binding: Binding) -> FailureAction:
    """`check` is a MissingInput, a StaleCheck or a PITValue (disputed/ok: not a failure). The binding supplies the
    role, the books (HALT scope) and the covariance action."""
    role = binding.role
    books = tuple(binding.books)
    if isinstance(check, PITValue):
        return FailureAction(series_id, role, "disputed" if check.dispute else "ok", "none", False, check.dispute,
                             "never", books, False)
    detail = {}
    if isinstance(check, MissingInput):
        status = STATUS_OF[check.reason]
        if check.detail:
            detail = {"detail": check.detail}            # the alert names the calendar / the refusal
    elif isinstance(check, StaleCheck):
        if not check.stale:
            return FailureAction(series_id, role, "ok", "none", False, False, "never", books, False)
        status = "missing" if check.reason == "missing" else "stale_missed_release"
    else:
        raise PITError(f"on_input_failure: unknown check {type(check).__name__}")
    if role == "acting_exposure":
        return FailureAction(series_id, role, status, "fail_closed", True, True, "bound_books", books, True, detail)
    if role == "risk_model":
        if binding.action == "risk_model_covariance":
            return FailureAction(series_id, role, status, "carry_last_valid_terms_stale_then_drop", False, True,
                                 "never", books, False, {"carry_max_decisions": 5, "sets_hedge_credit_off": False, **detail})
        return FailureAction(series_id, role, status, "conservative_default", False, True, "never", books, False,
                             {"hedge_credit_off": True, "hedge_failure_from": "USD_LIVE_PROXY",
                              "operator_alert_after_missed_releases": 2, **detail})
    if role == "context":
        return FailureAction(series_id, role, "stale" if status == "stale_missed_release" else status,
                             "label_stale", False, False, "never", books, False)
    if role == "forward_sim":
        return FailureAction(series_id, role, status, "fail_closed_that_book", True, True, "that_book", books, False)
    return FailureAction(series_id, role, status, "refuse_card_if_span_not_covered", True, True, "never", books, False)


def read_input(store: PITStore, registry: Registry, series_id: str, ctx: pit.RunContext, consumer: str, clocks, *,
               require_session: date | None = None, vendor: str | None = None) -> PITValue | MissingInput:
    """pit_value -> contract check -> is_stale; any failure is a MissingInput (F-11). An unreadable publication
    calendar fails the input closed (never observation-age staleness)."""
    v = pit.pit_value(store, series_id, ctx.decision_utc, ctx.knowledge_utc, consumer, require_session,
                      run_mode=ctx.run_mode, vendor=vendor, registry=registry)
    if isinstance(v, MissingInput):
        return v
    c = contract(registry, series_id)
    previous = None
    if c.abs_daily_return_max is not None:
        window = pit.pit_window(store, series_id, ctx.decision_utc, ctx.knowledge_utc, n=2, registry=registry,
                                statuses=pit.CLOSE_STATUSES)
        earlier = [w for w in window if w.obs_date < v.obs_date]
        previous = earlier[-1].value if earlier else None
    if check_contract(c, v.value, previous=previous) is not None:
        return MissingInput(series_id, "missing", v.role, v.books)
    if v.role == "context":
        return v
    try:
        check = is_stale(store, registry, series_id, ctx.decision_utc, ctx.knowledge_utc, clocks)
    except CalendarUnavailable as exc:
        return MissingInput(series_id, "missing", v.role, v.books, detail=str(exc))
    if check.stale:
        return MissingInput(series_id, "stale", v.role, v.books)
    return v


# --------------------------------------------------------------------------- #
# Cross-market availability (R-19 rule 6; data_contracts.cross_market)
# --------------------------------------------------------------------------- #
def usable_cross_market(market: str, obs_date: date, decision_utc: datetime, clocks) -> bool:
    """close_print_bound_utc(m, D) + 60 s < decision_utc (strict)."""
    return clocks.close_print_bound_utc(market, obs_date) + timedelta(seconds=CROSS_MARKET_BUFFER_S) < decision_utc


# --------------------------------------------------------------------------- #
# Counters (R-19 rule 4; L1869-1871; F-8, F-16)
# --------------------------------------------------------------------------- #
class InputCounters:
    """input_counter[book][series]: consecutive decisions the input failed closed (reset at its next fresh decision);
    book_counter[book]: consecutive decisions any default-limit acting input bound to the book failed (reset when
    all are fresh). HALT(book, OPS) when an input counter reaches its binding's limit or the book counter reaches 2.
    Only `acting_exposure` bindings with books count; disputed and warm-up values are not failures."""

    def __init__(self) -> None:
        self.input: dict[str, dict[str, int]] = {}
        self.book: dict[str, int] = {}

    def step(self, registry: Registry, results: list[tuple[Binding, bool]]) -> list[Halt]:
        """`results` = [(binding, failed)] for one decision. Returns the HALTs to raise (idempotent for the runtime)."""
        halts: list[Halt] = []
        per_book: dict[str, list[tuple[Binding, bool]]] = {}
        for b, failed in results:
            if b.role != "acting_exposure":
                continue
            for book in registry.book_ids(b):
                per_book.setdefault(book, []).append((b, failed))
        for book, items in per_book.items():
            counters = self.input.setdefault(book, {})
            default_items = [(b, f) for b, f in items if b.halt_after_consecutive_decisions == DEFAULT_HALT_AFTER]
            if default_items and any(f for _, f in default_items):
                self.book[book] = self.book.get(book, 0) + 1
            elif default_items:
                self.book[book] = 0
            for b, failed in items:
                counters[b.series_id] = counters.get(b.series_id, 0) + 1 if failed else 0
                if failed and counters[b.series_id] >= b.halt_after_consecutive_decisions:
                    halts.append(Halt(book, f"acting_input_stale:{b.series_id}", b.series_id))
            if self.book.get(book, 0) >= BOOK_COUNTER_HALT_AFTER and not any(h.book_id == book for h in halts):
                sid = next((b.series_id for b, f in items if f), "")
                halts.append(Halt(book, f"acting_input_stale:{sid}", sid))
        return halts

    def state(self, book: str) -> dict:
        return {"consecutive_failures": dict(self.input.get(book, {})), "book_counter": int(self.book.get(book, 0))}


def derive_bindings(registry: Registry, admissions: dict[str, bool]) -> dict[str, tuple[str, ...]]:
    """Each acting binding's book list derived from admissions without editing the roles entry (R2-C4): a factor
    admitted to the recommended book adds `recommended`. In M1 no card is PASS, so derived == declared."""
    out = {}
    for sid in registry.series:
        for b in registry.bindings(sid):
            if b.role != "acting_exposure":
                continue
            books = list(registry.book_ids(b))
            market = registry.market(sid) or "KR"
            if admissions.get(sid) and f"recommended:{market}" not in books and books:
                books.append(f"recommended:{market}")
            out[f"{sid}|{b.consumer or '*'}"] = tuple(books)
    return out


__all__ = [n for n in dir() if not n.startswith("_")]
