"""The poll checks of E1 spec 7 (plan Task 11; E7, E19, E20, E21, E31, E34, E39, E42, E43). Pure: no clock, no
file, no network.

run_checks compares one poll's three venue snapshots with each venue's prior state, the owner state and the limits,
and returns alerts; evaluated names the checks whose inputs were there, so only those clear; not_set names the checks
skipped for an unset input; due applies the once-a-day rule (E19) to the rows of alerts.jsonl. TEXT is the fixed
sentence catalogue: its slots carry counts, ISO times and not-set items only, never a balance or an address (E37).
E1 only alerts: no check halts, disarms, sells or withdraws."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from types import MappingProxyType

from core.compliance import model
from execution import positions, snapshot

KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "HOLDINGS_CHANGED", "OKX_CAP", "ADDRESS_LIST", "D15_LIVE",
         "HARD_BLOCK_LIVE", "FLOOR", "DAILY_LOSS", "OUTAGE", "CLOCK_SKEW",     # spec 7's eleven checks
         "EVIDENCE", "NOT_SET")                                              # the poller's own (E33, E43)
VENUE_NAMES = MappingProxyType({"kis": "KIS", "upbit": "Upbit", "okx": "OKX", "all": "TRADEGEN"})
KEY_EXPIRY_WARN = timedelta(days=30)
OUTAGE_POLLS = 3
CLOCK_SKEW_S = 60
STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")            # model.iso_utc's form
INT_SLOTS = frozenset({"n", "k", "added", "removed", "days", "seconds", "fills", "deposits", "withdrawals"})
TIME_SLOTS = frozenset({"expires", "when", "since"})
ITEM_SLOTS = frozenset({"skipped"})     # a "; "-joined str of NOT_SET_ITEMS (E43)
NOT_SET_ITEMS = frozenset(                # every string not_set can return (contract 15.1)
    {f"{VENUE_NAMES[v]}: keys not in .env" for v in snapshot.VENUES} | {"KIS: code not signed"}
    | {f"{c}: {r}" for c in ("FLOOR", "DAILY_LOSS", "OKX_CAP") for r in ("not set", "no live positions")}
    | {"ADDRESS_LIST: owner log not OK"})
TEXT = MappingProxyType({                 # text_key -> (kind, level, template); contract 15.3
    "KEY_MISSING": ("KEY_HEALTH", "amber", "{venue} keys are not in .env, so E1 did not read {venue}. If you "
                    "removed them on purpose, ignore this; it repeats once a day."),
    "KIS_UNSIGNED": ("KEY_HEALTH", "amber", "E1 sent nothing to KIS: the KIS key can also trade, and TRADEGEN's "
                     "code is not signed by you. KIS stays unread until you sign the code hash; this repeats once "
                     "a day."),
    "KEY_AUTH": ("KEY_HEALTH", "red", "{venue} refused E1's key with an authentication or permission error. Check "
                 "the key, its permissions and its registered IP."),
    "KEY_OKX_SELF_CHECK": ("KEY_HEALTH", "red", "OKX key is not read-only, or the OKX account is not spot mode with "
                           "borrowing off, or the key has no bound IP ({n} of 5 checks failed). OKX inquiry "
                           "stopped for this poll."),
    "KEY_EXPIRY": ("KEY_HEALTH", "amber", "An Upbit API key of this account expires in {days} days ({expires}). "
                   "Issue a new read-only key before then."),
    "FOREIGN_ORDER": ("FOREIGN_ORDER", "red", "{venue} shows {n} open order(s). E1 places no orders: check the "
                      "{venue} app now."),
    "HOLDINGS_EXPLAINED": ("HOLDINGS_CHANGED", "amber", "{venue} holdings changed in {n} symbol(s); {fills} new "
                           "fill(s), {deposits} deposit(s) and {withdrawals} withdrawal(s) explain them."),
    "HOLDINGS_UNEXPLAINED": ("HOLDINGS_CHANGED", "red", "{venue} holdings changed in {n} symbol(s), {k} of them "
                             "with no new fill, deposit or withdrawal to explain it ({fills} new fill(s), "
                             "{deposits} deposit(s) and {withdrawals} withdrawal(s) explain the rest). Check the "
                             "{venue} app now."),
    "ADDRESS_CHANGED": ("ADDRESS_LIST", "red", "Upbit's registered withdrawal addresses changed: {added} added, "
                        "{removed} removed."),
    "ADDRESS_UNSIGNED": ("ADDRESS_LIST", "red", "Upbit lists {n} withdrawal address(es) that no signed "
                         "withdrawal_address entry of yours names."),
    "D15_BORROW": ("D15_LIVE", "red", "OKX borrowing is switched on (spot borrow or auto-loan). D15 forbids "
                   "borrowing."),
    "D15_LOAN": ("D15_LIVE", "red", "{venue} shows {n} loan, credit or margin figure(s) above zero. D15 forbids "
                 "borrowing."),
    "D15_EARN": ("D15_LIVE", "red", "OKX shows {n} Earn or lending figure(s) above zero. D15 forbids lending."),
    "HARD_BLOCK_EVENTS": ("HARD_BLOCK_LIVE", "red", "OKX shows an event-contract (EVENTS) instrument. Prediction "
                          "markets are hard-blocked."),
    "HARD_BLOCK_DERIVATIVE": ("HARD_BLOCK_LIVE", "red", "OKX shows a derivative position (swap, futures or "
                              "option). Derivatives are hard-blocked."),
    "FLOOR": ("FLOOR", "red", "Live total equity is at or below your total-loss floor. E1 only alerts: nothing was "
              "sold, halted or disarmed."),
    "DAILY_LOSS": ("DAILY_LOSS", "red", "Live total equity fell by at least your daily loss limit since the first "
                   "poll of today ({since}). E1 only alerts."),
    "OKX_CAP": ("OKX_CAP", "red", "OKX holds more than your okx_equity_share cap of live total equity (USDT and "
                "USDC included)."),
    "OUTAGE": ("OUTAGE", "amber", "{venue} failed {n} polls in a row (the last at {when})."),
    "OUTAGE_CRASH": ("OUTAGE", "amber", "An E1 poll crashed at {when}; {venue} counts as failed for it. The next "
                     "poll runs as usual."),
    "CRASH_UNLOGGED": ("OUTAGE", "amber", "An E1 poll crashed at {when} and its alert could not be written. Check "
                       "~/.tradegen/execution on the PC."),
    "EVIDENCE_BROKEN": ("EVIDENCE", "amber", "E1's evidence log does not verify, so no D16 evidence is recorded or "
                        "counted. Move ~/.tradegen/execution/evidence.jsonl aside to start a new one."),
    "CLOCK_SKEW": ("CLOCK_SKEW", "amber", "This PC's clock is {seconds} seconds away from {venue}'s server time. "
                   "Fix the Windows clock."),
    "NOT_SET": ("NOT_SET", "info", "Checks skipped (not set): {skipped}."),
})
_FIELDS = MappingProxyType({key: frozenset(re.findall(r"\{(\w+)\}", template)) - {"venue"}
                            for key, (_kind, _level, template) in TEXT.items()})     # slot names per text_key
_ROW_KEYS = frozenset({"kind", "level", "sent", "slots", "text_key", "utc", "venue"})
_OKX_SELF_CHECK = ("okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan", "okx_no_ip")
_NOT_AN_OUTAGE = ("keys_missing", "code_unsigned")     # KEY_MISSING and KIS_UNSIGNED already say why (E31, E42)
_OK_KINDS = ("KEY_HEALTH", "FOREIGN_ORDER", "D15_LIVE", "HARD_BLOCK_LIVE", "OUTAGE")   # evaluated when ok (E19)


@dataclass(frozen=True, kw_only=True)
class Alert:
    venue: str                           # "kis" | "upbit" | "okx" | "all"
    kind: str                            # one of KINDS
    level: str                           # "red" | "amber" | "info" (NOT_SET only, E43) | "clear"
    text_key: str
    slots: Mapping[str, int | str] = field(default_factory=dict)   # ints, ISO times and NOT_SET items only


@dataclass(frozen=True, kw_only=True)
class Prior:
    last_ok: snapshot.Snapshot | None    # the venue's latest ok snapshot before this poll
    fails: int                           # not-ok polls in a row before this one; an ok snapshot or one flagged
                                         # keys_missing or code_unsigned ends the run (not set, not an outage)


@dataclass(frozen=True, kw_only=True)
class Limits:
    total_loss_floor_krw: float | None   # owner limit_set after D12 (None: not set)
    daily_loss_krw: float | None
    okx_equity_share: float | None       # owner cap_set
    day_start_equity_krw: float | None   # E34
    day_start_utc: str | None


_NO_PRIOR = Prior(last_ok=None, fails=0)


def limits_from(owner: model.OwnerState, day_start: tuple[float, str] | None) -> Limits:
    """The owner's limits and cap (None when not set; all None while the owner log is not OK, when every owner fact
    counts as absent) and the day's start (E34)."""
    limits, caps = (owner.limits, owner.caps) if owner.ok else ({}, {})
    equity, utc = day_start if day_start is not None else (None, None)
    return Limits(total_loss_floor_krw=limits.get("total_loss_floor_krw"),
                  daily_loss_krw=limits.get("daily_loss_krw"), okx_equity_share=caps.get("okx_equity_share"),
                  day_start_equity_krw=equity, day_start_utc=utc)


def priors(rows: list[dict]) -> dict[str, Prior]:
    """Per venue of snapshot.VENUES: the latest ok snapshot among `rows` (inquiry rows in file order, E30) and the
    not-ok polls in a row after it. A keys_missing or code_unsigned snapshot also ends the run, so the first real
    failure after keys arrive or the code is signed counts from 0. A row that does not load is skipped."""
    last_ok: dict[str, snapshot.Snapshot | None] = {v: None for v in snapshot.VENUES}
    fails = {v: 0 for v in snapshot.VENUES}
    for obj in rows:
        snap = _load(obj)
        venue = None if snap is None else snap.venue
        if venue not in fails:
            continue
        if snap.ok:
            last_ok[venue], fails[venue] = snap, 0
        elif any(f in snap.flags for f in _NOT_AN_OUTAGE):
            fails[venue] = 0
        else:
            fails[venue] += 1
    return {v: Prior(last_ok=last_ok[v], fails=fails[v]) for v in snapshot.VENUES}


def day_start(rows: list[dict], now: datetime) -> tuple[float, str] | None:
    """(equity_krw, utc) of the first poll on now's Seoul date whose three snapshots give live positions (E34), or
    None when there is none yet (the caller then starts the day at the current poll)."""
    today, polls = _seoul(now), {}
    for obj in rows:
        snap = _load(obj)
        if snap is not None and _seoul(_instant(snap.utc)) == today:
            polls.setdefault(snap.utc, {}).update({snap.venue: snap})   # insertion order: the file's order
    for utc, new in polls.items():
        live = positions.live_positions(new, _instant(utc))
        if live is not None:
            return live.equity_krw, utc
    return None


def run_checks(prev: Mapping[str, Prior], new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
               now: datetime) -> list[Alert]:
    """Every alert of the check table (contract 15.1) for this poll: venue by venue in snapshot.VENUES order, then
    the checks over live positions. An unset limit or cap is skipped (not_set names it)."""
    out: list[Alert] = []
    for venue in snapshot.VENUES:
        if venue in new:
            out += _venue_alerts(venue, new[venue], prev.get(venue) or _NO_PRIOR, owner, now)
    live = positions.live_positions(new, now)
    if live is None:
        return out
    if limits.total_loss_floor_krw is not None and live.equity_krw <= limits.total_loss_floor_krw:
        out.append(_alert("all", "FLOOR"))
    if (limits.daily_loss_krw is not None and _has_start(limits)
            and limits.day_start_equity_krw - live.equity_krw >= limits.daily_loss_krw):
        out.append(_alert("all", "DAILY_LOSS", since=limits.day_start_utc))
    okx = live.exposure.get("okx")
    if (limits.okx_equity_share is not None and okx is not None
            and okx.held_krw > limits.okx_equity_share * live.equity_krw):
        out.append(_alert("okx", "OKX_CAP"))
    return out


def evaluated(prev: Mapping[str, Prior], new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
              now: datetime) -> frozenset[tuple[str, str]]:
    """The (venue, kind) pairs whose inputs were there this poll (E19): only their text_keys clear. A failed venue,
    no live positions or an owner log that is not OK clears nothing; ("all", "NOT_SET") is never here (E43)."""
    done: set[tuple[str, str]] = set()
    for venue in snapshot.VENUES:
        snap = new.get(venue)
        if snap is None:
            continue
        if snap.ok:
            done.update((venue, kind) for kind in _OK_KINDS)
            if (prev.get(venue) or _NO_PRIOR).last_ok is not None:
                done.add((venue, "HOLDINGS_CHANGED"))
                if venue == "upbit" and owner.ok:
                    done.add((venue, "ADDRESS_LIST"))
        if snap.clock_offset_s is not None:
            done.add((venue, "CLOCK_SKEW"))
    if positions.live_positions(new, now) is not None:
        if limits.total_loss_floor_krw is not None:
            done.add(("all", "FLOOR"))
        if limits.daily_loss_krw is not None and _has_start(limits):
            done.add(("all", "DAILY_LOSS"))
        if limits.okx_equity_share is not None:
            done.add(("okx", "OKX_CAP"))
    return frozenset(done)


def not_set(new: Mapping[str, snapshot.Snapshot], owner: model.OwnerState, limits: Limits,
            live: model.Positions | None) -> tuple[str, ...]:
    """The checks skipped this poll, as NOT_SET_ITEMS strings in a fixed order (contract 15.1); no alert."""
    items: list[str] = []
    for venue in snapshot.VENUES:
        flags = new[venue].flags if venue in new else frozenset()
        if "keys_missing" in flags:
            items.append(f"{VENUE_NAMES[venue]}: keys not in .env")
        elif venue == "kis" and "code_unsigned" in flags:
            items.append("KIS: code not signed")
    for check, value in (("FLOOR", limits.total_loss_floor_krw), ("DAILY_LOSS", limits.daily_loss_krw),
                         ("OKX_CAP", limits.okx_equity_share)):
        if value is None:
            items.append(f"{check}: not set")
        elif live is None:
            items.append(f"{check}: no live positions")
    if not owner.ok:
        items.append("ADDRESS_LIST: owner log not OK")
    return tuple(items)


def due(raw: list[Alert], done: frozenset[tuple[str, str]], rows: list[dict], now: datetime
        ) -> tuple[list[Alert], list[Alert]]:
    """(fresh, clears) under the once-a-day rule (E19, contract 15.2), from today's rows of alerts.jsonl: a raw alert
    is fresh when its (venue, text_key) has no row today or its latest row today is a clear, or when it is red and
    the latest non-clear row today of its (venue, kind) is amber (a level rise fires at once). Fresh alerts keep raw
    order, amber and info before red. A key raised today, not raised now and whose kind was evaluated gets one clear.
    A row that does not verify (verify_row) counts for nothing, so a malformed line can never mute an alert."""
    today = _seoul(now)
    latest: dict[tuple[str, str], str] = {}
    group: dict[tuple[str, str], str] = {}
    for obj in rows:
        if not verify_row(obj) or _seoul(_instant(obj["utc"])) != today:
            continue
        key = (obj["venue"], obj["text_key"])
        latest[key] = obj["level"]
        if obj["level"] != "clear":
            group[(key[0], TEXT[key[1]][0])] = obj["level"]
    fresh = [a for a in raw if latest.get((a.venue, a.text_key), "clear") == "clear"
             or (a.level == "red" and group.get((a.venue, a.kind)) == "amber")]
    raised = {(a.venue, a.text_key) for a in raw}
    clears = [Alert(venue=venue, kind=TEXT[key][0], level="clear", text_key=key)
              for (venue, key), level in latest.items()
              if level != "clear" and (venue, TEXT[key][0]) in done and (venue, key) not in raised]
    return sorted(fresh, key=lambda a: a.level == "red"), clears


def render(alert: Alert) -> str:
    """The fixed sentence of a red, amber or info alert (a toast, or a line of --pending)."""
    return TEXT[alert.text_key][2].format(venue=VENUE_NAMES[alert.venue], **alert.slots)


def row(alert: Alert, utc: str) -> dict:
    """The alerts.jsonl row; red and amber rows wait for the daily task (sent false), clear and info rows never
    leave the PC (sent true)."""
    return {"kind": alert.kind, "level": alert.level, "sent": alert.level in ("clear", "info"),
            "slots": dict(alert.slots), "text_key": alert.text_key, "utc": utc, "venue": alert.venue}


def verify_row(obj: object) -> bool:
    """True only for a row of the shape row() writes (contract 15.2): the seven keys, a catalogue text_key with its
    own kind and level (or "clear"), a known venue, a bool sent, a stamp utc, and exactly the template's slots with
    ints, stamps and not-set items in them (none for a clear row). --pending re-checks every row with it."""
    if not isinstance(obj, dict) or set(obj) != _ROW_KEYS:
        return False
    key, level, slots = obj["text_key"], obj["level"], obj["slots"]
    if not isinstance(key, str) or key not in TEXT or not isinstance(slots, dict):
        return False
    if obj["kind"] != TEXT[key][0] or level not in (TEXT[key][1], "clear") or type(obj["sent"]) is not bool:
        return False
    if not isinstance(obj["venue"], str) or obj["venue"] not in VENUE_NAMES:
        return False
    if not _is_stamp(obj["utc"]):
        return False
    if set(slots) != (frozenset() if level == "clear" else _FIELDS[key]):
        return False
    return all(_slot_ok(name, value) for name, value in slots.items())


def _slot_ok(name: str, value: object) -> bool:
    if name in INT_SLOTS:
        return type(value) is int
    if name in TIME_SLOTS:
        return _is_stamp(value)
    if name in ITEM_SLOTS:
        return isinstance(value, str) and all(item in NOT_SET_ITEMS for item in value.split("; "))
    return False


def _venue_alerts(venue: str, snap: snapshot.Snapshot, prior: Prior, owner: model.OwnerState,
                  now: datetime) -> list[Alert]:
    """The per-venue rows of the check table, in table order."""
    flags, out = snap.flags, []
    if "keys_missing" in flags:
        out.append(_alert(venue, "KEY_MISSING"))
    if venue == "kis" and "code_unsigned" in flags:
        out.append(_alert(venue, "KIS_UNSIGNED"))
    if "auth_error" in flags:
        out.append(_alert(venue, "KEY_AUTH"))
    failed = sum(f in flags for f in _OKX_SELF_CHECK)
    if venue == "okx" and failed:
        out.append(_alert(venue, "KEY_OKX_SELF_CHECK", n=failed))
    if venue == "upbit" and snap.ok and _is_stamp(snap.key_expiry):
        left = _instant(snap.key_expiry) - now
        if left <= KEY_EXPIRY_WARN:
            out.append(_alert(venue, "KEY_EXPIRY", days=max(0, left.days), expires=snap.key_expiry))
    if snap.ok and snap.open_orders:
        out.append(_alert(venue, "FOREIGN_ORDER", n=len(snap.open_orders)))
    if snap.ok and prior.last_ok is not None:
        out += _holdings(venue, prior.last_ok, snap)
    listed = _address_set(snap)
    if venue == "upbit" and snap.ok and prior.last_ok is not None and listed != _address_set(prior.last_ok):
        before = _address_set(prior.last_ok)
        out.append(_alert(venue, "ADDRESS_CHANGED", added=len(listed - before), removed=len(before - listed)))
    if venue == "upbit" and snap.ok and owner.ok:
        signed = {(symbol, address, tag) for _dest, symbol, _network, address, tag in owner.addresses}
        if listed - signed:
            out.append(_alert(venue, "ADDRESS_UNSIGNED", n=len(listed - signed)))
    if venue == "okx" and ("okx_spot_borrow" in flags or "okx_auto_loan" in flags):
        out.append(_alert(venue, "D15_BORROW"))
    loans = sum(value > 0 for value in snap.loans.values())
    if snap.ok and loans:
        out.append(_alert(venue, "D15_LOAN", n=loans))
    earn = sum(value > 0 for value in snap.earn.values())
    if venue == "okx" and snap.ok and earn:
        out.append(_alert(venue, "D15_EARN", n=earn))
    if venue == "okx" and "EVENTS" in flags:
        out.append(_alert(venue, "HARD_BLOCK_EVENTS"))
    if venue == "okx" and "derivative_position" in flags:
        out.append(_alert(venue, "HARD_BLOCK_DERIVATIVE"))
    if not snap.ok and not any(f in flags for f in _NOT_AN_OUTAGE) and prior.fails + 1 >= OUTAGE_POLLS:
        out.append(_alert(venue, "OUTAGE", n=prior.fails + 1, when=snap.utc))
    if snap.clock_offset_s is not None and abs(snap.clock_offset_s) > CLOCK_SKEW_S:
        out.append(_alert(venue, "CLOCK_SKEW", seconds=round(abs(snap.clock_offset_s))))
    return out


def _holdings(venue: str, last: snapshot.Snapshot, snap: snapshot.Snapshot) -> list[Alert]:
    """HOLDINGS_EXPLAINED or HOLDINGS_UNEXPLAINED when a symbol's units changed since the last ok snapshot: a
    changed symbol is explained by a new fill naming it (symbol or counter) or a new deposit or withdrawal of it."""
    changed = {s for s in set(last.holdings) | set(snap.holdings) if _differs(_units(last, s), _units(snap, s))}
    if not changed:
        return []
    fills = _new_moves(last.fills, snap.fills)
    deposits = _new_moves(last.deposits, snap.deposits)
    withdrawals = _new_moves(last.withdrawals, snap.withdrawals)
    explained = {m.symbol for m in fills + deposits + withdrawals} | {m.counter for m in fills}
    counts = {"fills": sum(m.symbol in changed or m.counter in changed for m in fills),
              "deposits": sum(m.symbol in changed for m in deposits),
              "withdrawals": sum(m.symbol in changed for m in withdrawals)}
    unexplained = len(changed - explained)
    if unexplained:
        return [_alert(venue, "HOLDINGS_UNEXPLAINED", n=len(changed), k=unexplained, **counts)]
    return [_alert(venue, "HOLDINGS_EXPLAINED", n=len(changed), **counts)]


def _alert(venue: str, text_key: str, **slots: int | str) -> Alert:
    kind, level, _template = TEXT[text_key]
    return Alert(venue=venue, kind=kind, level=level, text_key=text_key, slots=slots)


def _load(obj: object) -> snapshot.Snapshot | None:
    """snapshot.load(obj), or None for a row that does not load or whose utc is not a model.iso_utc stamp."""
    try:
        snap = snapshot.load(obj)
    except (LookupError, TypeError, ValueError, AttributeError):
        return None
    return snap if _is_stamp(snap.utc) else None


def _units(snap: snapshot.Snapshot, symbol: str) -> float:
    held = snap.holdings.get(symbol)
    return 0.0 if held is None else held.units


def _differs(a: float, b: float) -> bool:
    return abs(a - b) > 1e-12 * max(1.0, abs(a), abs(b))


def _new_moves(before: tuple, after: tuple) -> list:
    ids = {m.id for m in before}
    return [m for m in after if m.id not in ids]


def _address_set(snap: snapshot.Snapshot) -> frozenset[tuple[str, str, str]]:
    return frozenset((a.currency, a.address, a.secondary_address or "") for a in snap.withdrawal_addresses)


def _has_start(limits: Limits) -> bool:
    return limits.day_start_equity_krw is not None and limits.day_start_utc is not None


def _is_stamp(value: object) -> bool:
    """A model.iso_utc string that names a real instant with a Seoul date (STAMP alone admits month 13, and
    9999-12-31T15:00:00Z and later overflow in KST)."""
    if not isinstance(value, str) or STAMP.fullmatch(value) is None:
        return False
    try:
        _seoul(_instant(value))
    except (ValueError, OverflowError):
        return False
    return True


def _instant(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)            # aware UTC: Python 3.11+ reads the "Z"


def _seoul(moment: datetime) -> date:
    return moment.astimezone(model.KST).date()
