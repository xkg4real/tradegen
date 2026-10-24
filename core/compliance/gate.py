"""The compliance kernel (spec 6.1-6.2) and its hard-coded floor (spec 5.2).

Pure: no clock, no file, no network, no time zone. It reads only the intent and a Context that model.is_sealed
accepts (P5). decide() never raises: an internal error is BLOCK "state: internal error <type>"."""
from __future__ import annotations

import dataclasses
import math
import string
import weakref
from collections.abc import Mapping

from core.compliance import model, rules
from core.compliance.model import ACK_REQUIRED, ALLOW, ALLOW_EXIT, BLOCK, Decision, Intent

# The floor (spec 5.2): applies whatever the approved table says.
FLOOR_ALL_TAGS = rules.TAGS                                            # every intent, exits included
FLOOR_ALL_ASSETS = frozenset({"event_contract", "sports_bet"})
FLOOR_NEW_VENUES = frozenset(rules.PREDICTION_VENUES) | {"sportsbook", "bitmart"} | frozenset(rules.STATE_BLOCKED)
FLOOR_NEW_ASSETS = frozenset({"fx_pair", "cfd", "overseas_future", "overseas_crypto_derivative"})
FLOOR_NEW_CLASSES = frozenset({"etp_crypto_spot"})
_FLOOR_ALL_WHEN = rules.WHEN                                           # route, on-behalf and signal conduct
_OKX_P2P = frozenset({"p2p_buy", "p2p_sell"})

_VERDICTS = (ALLOW, ALLOW_EXIT, ACK_REQUIRED, BLOCK)
_EXIT_KIND = {"sell": "close_long", "buy_to_cover": "cover_short", "transfer_out": "withdraw"}
_CLOSE_MANUALLY = "close manually in the broker app"
_WITHDRAW_MANUALLY = "withdraw manually in the exchange app"
_RANKS = ("conduct: ", "floor: ", "malformed: ", "state: ", "unsigned code")
_TEXT = ("venue", "symbol", "counter_symbol", "asset", "action", "financing", "route", "on_behalf")
_VOCAB = (("venue", rules.VENUES), ("asset", rules.ASSETS), ("action", rules.ACTIONS),
          ("financing", rules.FINANCING))
_DESTINATION = ("destination_venue", "destination_address", "destination_network", "destination_tag")
_NO_COUNTER = frozenset({"transfer_out", "lend", "borrow"})            # P18: counter_symbol must be ""
_SLACK = 1 + 1e-12                                                      # float slack on unit comparisons


def decide(intent, ctx) -> Decision:
    """One decision for one intent (spec 6.2, steps 0-7). Never raises."""
    try:
        return _decide(intent, ctx)
    except Exception as exc:
        return _fallback(intent, ctx, f"state: internal error {type(exc).__name__}")


def _decide(intent, ctx) -> Decision:
    if not model.is_sealed(ctx):
        return _decision(intent, None, None, BLOCK, "malformed", ["state: context not from load_context"])
    if type(intent) is not Intent:
        return _decision(intent, ctx, None, BLOCK, "malformed", ["malformed: intent"])
    state, why = _choose_state(intent, ctx)                                                   # step 0
    inst, venue, bad = _validate(intent, ctx, state)                                          # step 1
    reasons = _conduct(intent, state) + _positions(intent, ctx) + ([why] if why else []) + bad  # step 2
    if bad:
        return _decision(intent, ctx, state, BLOCK, "malformed", reasons + _floor_new(intent, inst))
    if state is not None:
        kind = _classify(intent, ctx, inst, venue)                                            # step 3
    else:
        kind = _EXIT_KIND.get(intent.action, "new_exposure")
        if kind == "withdraw" and not _is(intent.destination_venue, rules.DOMESTIC_EXCHANGES):
            kind = "new_exposure"             # step 3: a transfer is an exit only toward a domestic exchange
    if kind == "new_exposure":                # step 1 for new exposure: an earlier map serves exits only, and the
        more = (["malformed: symbol", _manual(intent)]                    # caps count the stake, so it is > 0
                if state is not None and _retired(state, venue, intent.symbol) else [])
        more += [] if intent.notional_krw > 0 else ["malformed: notional_krw"]
        if more:
            return _decision(intent, ctx, state, BLOCK, "malformed", reasons + more + _floor_new(intent, inst))
    if state is None:                         # nothing usable: exits are manual, new exposure is refused
        extra = _floor_new(intent, None) if kind == "new_exposure" else \
            [_WITHDRAW_MANUALLY if kind == "withdraw" else _CLOSE_MANUALLY]
        return _decision(intent, ctx, None, BLOCK, kind, reasons + extra)
    verdicts, warnings, ack = ([BLOCK] if reasons else []), [], None
    if kind != "new_exposure":                                                                # step 4
        verdict, more, warns = _exit(intent, ctx, state, kind, inst, venue)
        verdicts.append(verdict)
        reasons, warnings = reasons + list(more), warnings + list(warns)
    else:                                                                                     # steps 5-6
        pre, floor = _preconditions(ctx, state), _floor_new(intent, inst)
        reasons += pre + floor
        if pre or floor:
            verdicts.append(BLOCK)
        if not pre:
            steps = [_new_exposure(intent, ctx, state, inst, venue)]
            if intent.action == "transfer_out":
                steps.append(_transfer(intent, ctx, state, inst, venue))
            for verdict, more, warns, step_ack in steps:
                verdicts.append(verdict)
                reasons, warnings, ack = reasons + list(more), warnings + list(warns), ack or step_ack
    verdict = _combine(verdicts)                                                              # step 7
    if verdict == BLOCK and not reasons:
        reasons.append("no row")
    return _decision(intent, ctx, state, verdict, kind, reasons, warnings, ack)


# --------------------------------------------------------------------------- #
# Steps 0-3 and 7
# --------------------------------------------------------------------------- #
def _choose_state(intent, ctx) -> tuple[model.ApprovedState | None, str | None]:
    """Step 0: the active state while it and the owner log are usable; otherwise the snapshot, for sell,
    buy_to_cover and transfer_out only (D11). Every later step uses the state returned here."""
    if ctx.owner.ok and _usable(ctx.active):
        return ctx.active, None
    if _is(intent.action, _EXIT_KIND) and _usable(ctx.snapshot):
        return ctx.snapshot, None
    return None, _why_no_active(ctx)


def _validate(intent, ctx, state) -> tuple[rules.Instrument | None, rules.Venue | None, list[str]]:
    """Step 1: every malformed field as "malformed: <field>". The map and venue facts come from `state`; with no
    state only the intent's own fields and its quantity against the caller's positions are checked."""
    bad = [f for f in _TEXT if type(getattr(intent, f)) is not str]
    bad += [f for f, vocab in _VOCAB if f not in bad and getattr(intent, f) not in vocab]
    if not _number(intent.multiple):
        bad.append("multiple")
    if not (_number(intent.quantity) and intent.quantity > 0):
        bad.append("quantity")
    if not (_number(intent.notional_krw) and intent.notional_krw >= 0):
        bad.append("notional_krw")
    if type(intent.publishes_signal) is not bool:
        bad.append("publishes_signal")
    if not (isinstance(intent.tags, (set, frozenset)) and all(_is(t, rules.TAGS) for t in intent.tags)):
        bad.append("tags")
    if not (intent.reservation_id is None or (type(intent.reservation_id) is str and intent.reservation_id)):
        bad.append("reservation_id")
    transfer = _is(intent.action, {"transfer_out"})
    for f in _DESTINATION:
        value = getattr(intent, f)
        if not transfer:
            ok = value is None
        elif f == "destination_tag":
            ok = value is None or (type(value) is str and value != "")
        else:
            ok = type(value) is str and value != ""
        if not ok:
            bad.append(f)
    if transfer and "destination_venue" not in bad and (intent.destination_venue not in rules.VENUES
                                                        or intent.destination_venue == intent.venue):
        bad.append("destination_venue")
    if "counter_symbol" not in bad and "action" not in bad and \
            (intent.counter_symbol == "") != (intent.action in _NO_COUNTER):
        bad.append("counter_symbol")
    # Holdings and shorts come from ctx, not from the state, so these quantity tests run with no usable state too.
    if not {"action", "quantity", "venue", "symbol"} & set(bad) and (
            (intent.action in ("sell", "transfer_out") and not _within_free(intent, ctx))
            or (intent.action == "buy_to_cover" and not intent.quantity <= _units(ctx.shorts, intent) * _SLACK)):
        bad.append("quantity")                                # open a short with sell_short, an option with write
    if state is None or "venue" in bad or "symbol" in bad:
        return None, None, [f"malformed: {f}" for f in bad]
    venue = state.venues.venues.get(intent.venue)
    if venue is None:                                         # a vocabulary venue without approved facts
        return None, None, [f"malformed: {f}" for f in bad + ["venue"]]
    # A transfer is an exit only toward a domestic exchange (spec 6.2 step 3); only a cash-financed exit may fall back
    # to the earlier maps (D15, spec 6.2 step 0). The manual advice follows the first test alone.
    exit_action = "action" not in bad and intent.action in _EXIT_KIND and (
        not transfer or _is(intent.destination_venue, rules.DOMESTIC_EXCHANGES))
    inst = _lookup(state, venue, intent.symbol, exit_action and intent.financing == "cash")
    if inst is None:
        manual = [_manual(intent)] if exit_action else []
        return None, venue, [f"malformed: {f}" for f in bad + ["symbol"]] + manual
    if "asset" not in bad and intent.asset != inst.asset:
        bad.append("asset")
    if "multiple" not in bad and intent.multiple != inst.multiple:
        bad.append("multiple")
    retired = _retired(state, venue, intent.symbol)
    if "action" not in bad and "counter_symbol" not in bad and intent.action in rules.TRADE_ACTIONS:
        # parse_venues lists only current symbols as markets, so a retired one sells for any settlement asset of a
        # venue with explicit markets (step 3's close-long test); kis quotes by currency and needs no market list
        if retired and intent.action == "sell" and not venue.quote_by_currency:
            listed = intent.counter_symbol in venue.settlement
        else:
            listed = venue.is_market(inst, intent.counter_symbol)
        if not listed:
            bad.append("counter_symbol")                      # not a listed market of this venue
    manual = [_manual(intent)] if retired and "counter_symbol" in bad else []
    return inst, venue, [f"malformed: {f}" for f in bad] + manual


def _conduct(intent, state) -> list[str]:
    """Step 2: the all-intents floor and the conduct rows of `state`, for every intent, exits included. Conduct rows
    apply whatever their dates (they only ever block)."""
    out = [f"conduct: {t}" for t in sorted(_tags(intent) & FLOOR_ALL_TAGS)]
    out += [f"conduct: {w}" for w in sorted(_when(intent) & _FLOOR_ALL_WHEN)]
    if _is(intent.asset, FLOOR_ALL_ASSETS):
        out.append(f"conduct: {intent.asset}")
    if state is not None and state.rules is not None:
        # ponytail: the class seen here is ASSET_CLASS only, so the loader refuses a conduct row keyed on an ETP
        # class. Pass the looked-up Instrument if one ever needs it.
        cls = rules.ASSET_CLASS.get(intent.asset) if _is(intent.asset, rules.ASSETS) else None
        out += [f"conduct: {row.id}" for row in state.rules.rows
                if row.kind == "conduct" and _matches(row, intent, cls)]
    return out


def _classify(intent, ctx, inst, venue) -> str:
    """Step 3, on a valid intent: close_long, cover_short or withdraw when its exit test holds; else new_exposure.
    Only a cash-financed intent is an exit (D15). Under a broken owner log a domestic withdrawal stays a withdraw, so
    that step 4 can send it to the app."""
    action = intent.action
    if intent.financing != "cash":
        return "new_exposure"
    if (action == "sell" and inst.symbol not in venue.settlement and intent.counter_symbol in venue.settlement
            and _within_free(intent, ctx)):
        return "close_long"
    if action == "buy_to_cover" and intent.quantity <= _units(ctx.shorts, intent) * _SLACK:
        return "cover_short"
    if (action == "transfer_out" and intent.destination_venue in rules.DOMESTIC_EXCHANGES
            and _within_free(intent, ctx) and (not ctx.owner.ok or _credited(intent, ctx))):
        return "withdraw"
    return "new_exposure"


def _combine(verdicts) -> str:
    """Step 7: BLOCK beats ACK_REQUIRED beats ALLOW and ALLOW_EXIT; no verdict, or an unknown one, is BLOCK."""
    verdicts = list(verdicts)
    if not verdicts or BLOCK in verdicts or any(v not in _VERDICTS for v in verdicts):
        return BLOCK
    if ACK_REQUIRED in verdicts:
        return ACK_REQUIRED
    return ALLOW_EXIT if ALLOW_EXIT in verdicts else ALLOW


# --------------------------------------------------------------------------- #
# Steps 4-6
# --------------------------------------------------------------------------- #
def _exit(intent, ctx, state, kind, inst, venue) -> tuple[str, list[str], list[str]]:
    """Step 4 (exits, D11): ALLOW_EXIT whatever the venue rows say (stale, auto-off, unmet gates, caps, D16,
    out_of_scope, hard_block), with the matching rows' warnings. Under a broken owner log a withdrawal is BLOCK,
    because its registered address cannot be verified."""
    if kind == "withdraw" and not ctx.owner.ok:
        return BLOCK, [_WITHDRAW_MANUALLY], []
    warnings = [] if state is ctx.active else ["snapshot: decided on the last approved snapshot (D11)"]
    for row in _in_force(state, intent, inst.cls, ctx.date):
        if ctx.date > row.review_by:
            warnings.append(_stale(row))
        warnings.append(render_warning(row, _slots(row, ctx)))
    return ALLOW_EXIT, [], [w for w in warnings if w]


def _new_exposure(intent, ctx, state, inst, venue) -> tuple[str, list[str], list[str], tuple | None]:
    """Step 5 (venue rows on ctx.date): no row in force is BLOCK "no row"; every matching row applies and the
    strictest wins. `ack: per_transfer` is never read: step 6 requires the per-transfer ack itself."""
    rows = _in_force(state, intent, inst.cls, ctx.date)
    reasons, ack = ([] if rows else ["no row"]), None
    for row in rows:
        more, need = _row_check(row, intent, ctx)
        reasons += more
        ack = ack or need
    warnings = [render_warning(row, _slots(row, ctx)) for row in rows]
    return _verdict(reasons), reasons, [w for w in warnings if w], ack


def _transfer(intent, ctx, state, inst, venue) -> tuple[str, list[str], list[str], tuple | None]:
    """Step 6 (the destination of a new-exposure transfer): decided as a buy of the same symbol there, the stricter
    result winning. It also needs a signed registered address that the destination credits and, for every grey row
    of the destination, a per-transfer ack (spec 6.2 step 6), whatever the source row's `ack` field says."""
    dest = state.venues.venues.get(intent.destination_venue)
    dest_inst = _lookup(state, dest, intent.symbol, False) if dest is not None else None
    if dest_inst is None:
        why = "has no approved venue facts" if dest is None else f"does not list {intent.symbol}"
        return BLOCK, [f"destination: {intent.destination_venue} {why}"], [], None
    buy = dataclasses.replace(intent, venue=dest.id, counter_symbol=dest.quote_for(dest_inst), action="buy",
                              destination_venue=None, destination_address=None, destination_network=None,
                              destination_tag=None)
    _, reasons, warnings, ack = _new_exposure(buy, ctx, state, dest_inst, dest)
    reasons += _floor_new(buy, dest_inst) + _positions(buy, ctx) + _dest_check(intent, ctx, dest)
    for row in _in_force(state, buy, dest_inst.cls, ctx.date):
        sha = warning_sha256(row, _slots(row, ctx))
        if row.treatment == "grey" and (_intent_hash(intent), sha) not in ctx.owner.transfer_acks:
            reasons.append(f"ack required: {row.id} per transfer")
            ack = ack or (row.id, sha)
    return _verdict(reasons), reasons, warnings, ack


# --------------------------------------------------------------------------- #
# Warnings and acks (spec 6.2 step 5)
# --------------------------------------------------------------------------- #
def render_warning(row, slots: Mapping[str, str]) -> str:
    """row.warning with {cap} filled from `slots`. Any other slot, or one that `slots` lacks, renders as ""; a
    warning that does not parse renders as "". Never raises."""
    try:
        return "".join(text + (str(slots[name]) if name in rules.WARNING_SLOTS and name in slots else "")
                       for text, name, _, _ in string.Formatter().parse(row.warning))
    except Exception:
        return ""


def warning_sha256(row, slots) -> str:
    """What an owner ack signs: the sha256 of the rendered warning."""
    return model.sha256_hex(render_warning(row, slots))


# --------------------------------------------------------------------------- #
# Step 4-6 helpers
# --------------------------------------------------------------------------- #
def _in_force(state, intent, cls, on) -> list:
    """The venue rows of `state` in force on `on` (effective_from <= on < effective_until) that match the intent."""
    return [row for row in state.rules.rows if row.kind == "venue" and row.effective_from <= on
            and (row.effective_until is None or on < row.effective_until) and _matches(row, intent, cls)]


def _row_check(row, intent, ctx) -> tuple[list[str], tuple | None]:
    """One venue row in force, for new exposure: its BLOCK reasons; else the per-session ack it still needs, as
    (["ack required: <id>"], (row id, warning sha256)); else ([], None)."""
    out = [_stale(row)] if ctx.date > row.review_by else []
    if row.treatment not in ("allow", "gated", "grey"):              # hard_block, out_of_scope
        return out + [f"{row.treatment}: {row.id}"], None
    if row.requires_live:                                              # D16: no owner event satisfies these
        out.append(f"needs live broker evidence (execution spec): {row.id}")
    out += [f"requires {item}: {row.id}" for item in row.requires_owner if item not in ctx.owner.flags]
    if row.treatment == "grey":
        out += _grey(row, intent, ctx)
    leverage = abs(intent.multiple)                                    # P4; no row lets credit or margin through
    if leverage > row.max_leverage:
        out.append(f"leverage {leverage:g} above {row.max_leverage:g}: {row.id}")
    if out or row.ack != "per_session":
        return out, None
    sha = warning_sha256(row, _slots(row, ctx))
    if (ctx.session.session_id, row.id, sha) in ctx.owner.session_acks:
        return [], None
    return [f"ack required: {row.id}"], (row.id, sha)


def _grey(row, intent, ctx) -> list[str]:
    """D6: off from auto_off on; the cap must be set; the venue's held value (settlement assets included), plus
    every other reservation, plus this notional must not exceed cap x equity. Holdings there with no exposure entry
    would count as nothing held, so they are invalid positions."""
    out = [f"auto_off {row.auto_off}: {row.id}"] if ctx.date >= row.auto_off else []
    exposure = ctx.exposure.get(intent.venue)
    if exposure is None and any(type(k) is tuple and k[:1] == (intent.venue,) and v for k, v in ctx.holdings.items()):
        out.append("state: positions invalid (exposure)")
    cap = _cap(row, ctx)
    if cap is None:
        return out + [f"cap unset: {row.id}"]
    held = exposure.held_krw if exposure is not None else 0.0
    own = intent.reservation_id                     # only an intent that has a reservation excludes one
    others = (sum(v for k, v in exposure.reservations.items() if own is None or k != own)
              if exposure is not None else 0.0)
    if held + others + intent.notional_krw > cap * ctx.equity_krw:
        out.append(f"cap exceeded: {row.id}")
    return out


def _cap(row, ctx) -> float | None:
    """The owner's cap for the row's cap_key when it is a number in (0, 1], else None (unset)."""
    cap = ctx.owner.caps.get(row.cap_key) if row.cap_key else None
    return cap if _number(cap) and 0 < cap <= 1 else None


def _slots(row, ctx) -> dict:
    """The warning slots of `row`: {"cap": "10%"} when its cap is set. An unset or unreadable cap (a broken owner
    log) reads "the share you set"; a grey row then blocks new exposure with "cap unset", so no ack signs it."""
    cap = _cap(row, ctx)
    return {"cap": f"{cap * 100:g}%" if cap is not None else "the share you set"}


def _stale(row) -> str:
    return f"stale: review by {row.review_by} passed ({row.id})"


def _verdict(reasons) -> str:
    """BLOCK for any reason but a missing ack, ACK_REQUIRED for missing acks only, ALLOW for none."""
    if any(not r.startswith("ack required: ") for r in reasons):
        return BLOCK
    return ACK_REQUIRED if reasons else ALLOW


def _dest_check(intent, ctx, dest) -> list[str]:
    """Step 6's address test: a signed registered (venue, symbol, network, address, tag or "") on a network that
    `dest` credits for the symbol, with a tag exactly when it requires one."""
    network = intent.destination_network
    key = (dest.id, intent.symbol, network, intent.destination_address, intent.destination_tag or "")
    out = [] if key in ctx.owner.addresses else ["destination: address not registered"]
    tag_rules = [needs for symbol, net, needs in dest.deposits if (symbol, net) == (intent.symbol, network)]
    if not tag_rules:
        out.append(f"destination: {dest.id} does not credit {intent.symbol} on {network}")
    elif tag_rules[0] != bool(intent.destination_tag):
        need = "needs a tag" if tag_rules[0] else "takes no tag"
        out.append(f"destination: {dest.id} {need} for {intent.symbol} on {network}")
    return out


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _matches(row, intent, cls) -> bool:
    """P12: every key of row.match holds. `any` holds for everything; `tag` needs an overlap with intent.tags,
    `when` one true conduct predicate, `class` the derived class `cls`; the other keys compare the intent field."""
    for key, allowed in row.match.items():
        if "any" in allowed:
            continue
        if key == "tag":
            hit = bool(_tags(intent) & allowed)
        elif key == "when":
            hit = bool(_when(intent) & allowed)
        elif key == "class":
            hit = cls in allowed
        else:
            hit = _is(getattr(intent, key, None), allowed)
        if not hit:
            return False
    return True


def _floor_new(intent, inst) -> list[str]:
    """The new-exposure part of the floor (spec 5.2); exits never reach it (D11)."""
    asset_cls = rules.ASSET_CLASS.get(intent.asset) if _is(intent.asset, rules.ASSETS) else None
    cls = inst.cls if inst is not None else asset_cls
    out = [f"floor: {v}" for v in (intent.venue, intent.destination_venue) if _is(v, FLOOR_NEW_VENUES)]
    if _is(intent.asset, FLOOR_NEW_ASSETS):
        out.append(f"floor: {intent.asset}")
    if cls in FLOOR_NEW_CLASSES:
        out.append(f"floor: {cls}")
    if _is(intent.venue, {"okx"}):
        if _is(intent.asset, {"crypto_perp_or_future"}):
            out.append("floor: okx crypto_perp_or_future")
        if _is(intent.action, _OKX_P2P):
            out.append(f"floor: okx {intent.action}")
    if cls == "option" and _is(intent.action, {"write"}):
        out.append("floor: option write")
    return out


def _preconditions(ctx, state) -> list[str]:
    """Step 5's entry test: the active state under a valid owner log (never identity alone), and signed code."""
    out = [] if ctx.owner.ok and _usable(ctx.active) and state is ctx.active else [_why_no_active(ctx)]
    return out + ([] if ctx.code_signed is True else ["unsigned code"])


def _positions(intent, ctx) -> list[str]:
    """Caller-supplied positions (P19) must be finite and >= 0, equity > 0, and every reservation id a non-empty
    str; anything else blocks."""
    bad = [] if _number(ctx.equity_krw) and ctx.equity_krw > 0 else ["equity_krw"]
    if type(intent.venue) is str and type(intent.symbol) is str:
        bad += [name for name, book in (("holdings", ctx.holdings), ("shorts", ctx.shorts))
                if not _nonneg(_units(book, intent))]
        exposure = ctx.exposure.get(intent.venue)
        if exposure is not None and not (
                all(_nonneg(v) for v in (exposure.held_krw, *exposure.reservations.values(),
                                         *exposure.promised_sell_units.values()))
                and all(type(k) is str and k for k in exposure.reservations)):    # a reservation id is a real name
            bad.append("exposure")
    return [f"state: positions invalid ({', '.join(bad)})"] if bad else []


def _credited(intent, ctx) -> bool:
    """A signed registered (venue, symbol, network, address, tag or "") that the destination's approved deposit
    facts credit, with a tag present exactly when the destination requires one."""
    key = (intent.destination_venue, intent.symbol, intent.destination_network, intent.destination_address,
           intent.destination_tag or "")
    state, _ = _choose_state(intent, ctx)
    dest = state.venues.venues.get(intent.destination_venue) if key in ctx.owner.addresses and state else None
    return dest is not None and any(
        symbol == intent.symbol and network == intent.destination_network
        and bool(intent.destination_tag) == bool(tag_required) for symbol, network, tag_required in dest.deposits)


def _lookup(state, venue, symbol, exits: bool):
    """The symbol in the venue's sections; an exit also searches earlier approved maps, newest first."""
    for instruments in (state.instruments, *state.history_maps) if exits else (state.instruments,):
        inst = instruments.lookup(venue.sections, symbol)
        if inst is not None:
            return inst
    return None


def _retired(state, venue, symbol) -> bool:
    """The symbol is not in the map in force for the venue's sections (only an earlier map may know it)."""
    return state.instruments.lookup(venue.sections, symbol) is None


def _manual(intent) -> str:
    return _WITHDRAW_MANUALLY if intent.action == "transfer_out" else _CLOSE_MANUALLY


def _within_free(intent, ctx) -> bool:
    """quantity <= holdings minus the units already promised to unexpired sell permits."""
    exposure = ctx.exposure.get(intent.venue)
    promised = exposure.promised_sell_units.get(intent.symbol, 0.0) if exposure is not None else 0.0
    return intent.quantity + promised <= _units(ctx.holdings, intent) * _SLACK


def _units(book, intent) -> float:
    return book.get((intent.venue, intent.symbol), 0.0)


def _why_no_active(ctx) -> str:
    if not ctx.owner.ok:
        return f"state: owner log {ctx.owner.reason or ctx.owner.status}"
    return f"state: {ctx.active.reason or 'no approved state'}"


def _usable(state) -> bool:
    return (isinstance(state, model.ApprovedState) and state.valid is True and state.rules is not None
            and state.instruments is not None and state.venues is not None)


def _tags(intent) -> frozenset:
    tags = intent.tags
    return frozenset(t for t in tags if type(t) is str) if isinstance(tags, (set, frozenset, list, tuple)) \
        else frozenset()


def _when(intent) -> frozenset:
    """The conduct predicates that hold; a value of the wrong type counts as conduct (fail closed)."""
    return frozenset(name for name, holds in (
        ("route_not_direct", not _is(intent.route, {"direct"})),
        ("on_behalf_not_self", not _is(intent.on_behalf, {"self"})),
        ("publishes_signal", intent.publishes_signal is not False)) if holds)


def _is(value, members) -> bool:
    """`value in members` for an exact str only, so unhashable or odd values never raise."""
    return type(value) is str and value in members


def _number(value) -> bool:
    if type(value) is float:
        return math.isfinite(value)
    return type(value) is int and abs(value) < 2 ** 63


def _nonneg(value) -> bool:
    return _number(value) and value >= 0


def _ranked(reasons) -> tuple[str, ...]:
    """Strictest first: conduct, floor, malformed, state, unsigned code, the rest as produced, ack required last;
    duplicates dropped."""
    def rank(reason: str) -> int:
        if reason.startswith("ack required: "):
            return len(_RANKS) + 1
        return next((i for i, prefix in enumerate(_RANKS) if reason.startswith(prefix)), len(_RANKS))
    return tuple(sorted(dict.fromkeys(reasons), key=rank))


def _intent_hash(intent) -> str:
    """model.intent_hash, or a hash of repr() when a malformed intent is not JSON data (NaN, odd types)."""
    try:
        return model.intent_hash(intent)
    except Exception:
        return model.sha256_hex("unhashable intent " + repr(intent))


def _decision(intent, ctx, state, verdict, kind, reasons, warnings=(), ack=None) -> Decision:
    """The record (spec 6.1). `ctx` is None unless sealed, so nothing unverified is copied in."""
    return Decision(
        verdict=verdict, kind=kind, reasons=_ranked(reasons), warnings=tuple(dict.fromkeys(warnings)),
        intent_hash=_intent_hash(intent), state_hash=state.state_hash if state is not None else "",
        code_hash=ctx.code_hash if ctx is not None else "",
        owner_head=tuple(ctx.owner.head) if ctx is not None else (0, ""),
        ctx_hash=ctx.ctx_hash if ctx is not None else "", date=ctx.date if ctx is not None else None,
        ack=ack if verdict == ACK_REQUIRED else None)


def _fallback(intent, ctx, reason: str) -> Decision:
    try:
        return _decision(intent, ctx if model.is_sealed(ctx) else None, None, BLOCK, "malformed", [reason])
    except Exception:
        return Decision(verdict=BLOCK, kind="malformed", reasons=(reason,), intent_hash="", state_hash="",
                        code_hash="", owner_head=(0, ""), ctx_hash="", date=None)


# --------------------------------------------------------------------------- #
# Permits and plan screening (spec 6.3)
# --------------------------------------------------------------------------- #
_ISSUED: weakref.WeakValueDictionary = weakref.WeakValueDictionary()     # id(permit) -> permit, as model._SEALED


def permit(intent, ctx) -> model.Permit | None:
    """A Permit for an ALLOW or ALLOW_EXIT decision, else None. Never raises. Only a Permit that this function
    returned, and that its caller still holds, verifies: discipline, as P5 is for contexts."""
    try:
        d = decide(intent, ctx)
        if d.verdict not in (ALLOW, ALLOW_EXIT):
            return None
        state, _ = _choose_state(intent, ctx)
        issued = model.Permit(decision_id=d.decision_id, intent_hash=d.intent_hash, state_hash=d.state_hash,
                              state_seq=state.seq, session_id=ctx.session.session_id,
                              reservation_id=intent.reservation_id, date=ctx.date)
        _ISSUED[id(issued)] = issued
        return issued
    except Exception:
        return None


def verify_permit(p, intent, ctx_now) -> tuple[bool, str]:
    """At send time: (True, "ok") only for a permit from permit(), for the same intent (its hash covers the
    reservation id), whose decision under ctx_now is still ALLOW or ALLOW_EXIT, in the same session and Asia/Seoul
    date, on a state with the permit's hash or a higher seq: the state that decision used, so the snapshot for a
    snapshot exit. decide() counts every reservation but the intent's own; the caller's promised sell units must
    likewise leave this permit's own units out. Never raises."""
    try:
        if type(p) is not model.Permit or _ISSUED.get(id(p)) is not p:
            return False, "permit: not issued by permit()"
        if _intent_hash(intent) != p.intent_hash:
            return False, "permit: intent differs"
        d = decide(intent, ctx_now)
        if d.verdict not in (ALLOW, ALLOW_EXIT):
            return False, f"permit: decision now {d.verdict} ({d.reasons[0]})"
        state, _ = _choose_state(intent, ctx_now)          # the state d used: the snapshot for a snapshot exit
        for what, same in (("session", ctx_now.session.session_id == p.session_id),
                           ("date", ctx_now.date == p.date),
                           ("state", d.state_hash == p.state_hash or state.seq > p.state_seq)):
            if not same:
                return False, f"permit: {what} differs"
        return True, "ok"
    except Exception as exc:
        return False, f"permit: internal error {type(exc).__name__}"


def screen(plan, ctx, first_stake_krw: float) -> model.Screening:
    """The plan's single leg decided on ctx.date as a cash buy of `first_stake_krw` on its venue (P3: reads
    plan.leg.venue, plan.leg.symbol, plan.start and plan.horizon_days only), with every review_by, auto_off and
    effective_until of the venue rows matching it inside [start, start + horizon_days) flagged; the simulation exits
    on the earliest. The plan must start on ctx.date. Never raises."""
    try:
        return _screen(plan, ctx, first_stake_krw)
    except Exception as exc:
        return _screening(_fallback(None, ctx, f"state: internal error {type(exc).__name__}"), (), None)


def _screen(plan, ctx, first_stake_krw) -> model.Screening:
    leg = getattr(plan, "leg", None)
    venue_id, symbol = getattr(leg, "venue", None), getattr(leg, "symbol", None)
    start, horizon = getattr(plan, "start", None), getattr(plan, "horizon_days", None)
    sealed = model.is_sealed(ctx)
    state = ctx.active if sealed and ctx.owner.ok and _usable(ctx.active) else None    # decide()'s state for a buy
    venue = state.venues.venues.get(venue_id) if state is not None and _is(venue_id, rules.VENUES) else None
    inst = _lookup(state, venue, symbol, False) if venue is not None else None
    # quantity is nominal: a buy's verdict depends on its notional, never on its units
    intent = Intent(venue=venue_id, symbol=symbol, counter_symbol=venue.quote_for(inst) if inst is not None else "",
                    asset=inst.asset if inst is not None else "", multiple=inst.multiple if inst is not None else 0.0,
                    action="buy", quantity=1.0, notional_krw=first_stake_krw)
    if not sealed:
        return _screening(decide(intent, ctx), (), None)                  # "state: context not from load_context"
    if type(start) is not model.date or type(horizon) is not int or horizon <= 0:
        return _screening(_decision(intent, ctx, None, BLOCK, "malformed", ["malformed: plan"]), (), None)
    if start != ctx.date:                  # the rows are read on ctx.date: a later start would miss [ctx.date, start)
        return _screening(_decision(intent, ctx, None, BLOCK, "malformed", ["malformed: plan start"]), (), None)
    if state is None:                      # the real cause, not the empty fields of a leg nothing could look up
        return _screening(_decision(intent, ctx, None, BLOCK, "new_exposure", [_why_no_active(ctx)]), (),
                          (start, horizon))
    first, end = start.toordinal(), start.toordinal() + horizon
    flags = []
    for row in state.rules.rows if inst is not None else ():
        if row.kind == "venue" and _matches(row, intent, inst.cls):
            for what, when in (("review_by", row.review_by), ("auto_off", row.auto_off),
                               ("effective_until", row.effective_until)):
                if when is not None and first <= when.toordinal() < end:
                    flags.append((when, what, row.id))
    return _screening(decide(intent, ctx), tuple(sorted(flags)), (start, horizon))


def _screening(d, flags, window) -> model.Screening:
    """The hashed Screening: allowed for ALLOW and ACK_REQUIRED; exit_date is the earliest flag date."""
    allowed = d.verdict in (ALLOW, ACK_REQUIRED)
    exit_date = flags[0][0] if flags else None
    body = {"decision": d, "allowed": allowed, "flags": flags, "exit_date": exit_date, "window": window}
    return model.Screening(decision=d, allowed=allowed, flags=flags, exit_date=exit_date,
                           screening_hash=model.sha256_hex(model.canonical_json(body)))
