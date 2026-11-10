"""Fresh odds preparation; this module never signs or arms an owner session."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import uuid4
import re

from core.compliance import model, owner
from core.odds import models, plan as odds_plan, simulate
from execution_control.capability import digest, plain
from execution_control.model import rules_digest
from execution_control.store import guard_pending


@dataclass(frozen=True, kw_only=True)
class PreparedSession:
    session_id: str
    plan_hash: str
    input_digest: str
    policy_digest: str
    rules_digest: str
    code_hash: str
    state_hash: str
    seed_hex: str
    selection_seed_hex: str
    venue: str
    symbol: str
    account_scope: str
    market: str
    quote_currency: str
    stake_krw: str
    prepared_at: datetime
    expires_at: datetime
    record_digest: str


_PREPARED: dict[int, tuple[PreparedSession, str]] = {}
_PREPARATION_AGE = timedelta(seconds=30)
_RULES_AGE = timedelta(minutes=5)


class PreparationError(ValueError):
    """Fixed diagnostic codes; no planner/provider text is exposed."""


def _require(condition, code):
    if not condition:
        raise PreparationError(code)


def _aware(value):
    return type(value) is datetime and value.utcoffset() is not None



def prepare_session(*, journal, session_id: str, selected_plan, inputs, positions,
                    policy, instrument_rules, now: datetime, selection_seed_hex: str,
                    account_scope: str, market: str, quote_currency: str,
                    clock, positions_asof: datetime, completion_check=None,
                    expires_at: datetime | None = None) -> PreparedSession:
    """Actually rerun selected_plan with a fresh comparison seed before arming.

    Inputs and positions come from the caller's reconciled observations. A result
    with any red diagnostic cannot prepare a session. The original selected seed
    is required so seed freshness is independently checked. ``now`` is the
    input's observation time, not permission to backdate owner authority. The
    caller supplies an explicit clock and the reconciled positions' timestamp;
    production uses its actual clock, historical tests use an explicit virtual
    clock. The pure odds simulator retains its existing injected-time contract.
    No registry entry or preparation event is issued until simulation and lock
    acquisition finish with current account, inputs, rules and owner authority.
    Time and verified review expiry are checked again after persistence. If disk
    completion was too late, its durable audit row stays but no session is issued.
    ``completion_check`` adds the launcher's current review checks and returns
    their earliest verified expiry. That deadline is checked after final owner
    loading. It cannot replace this module's checks or grant authority with a
    boolean or an unverified timestamp.
    """
    _require(callable(clock), "SESSION_PREPARATION_CLOCK_REQUIRED")
    _require(completion_check is None or callable(completion_check), "SESSION_PREPARATION_CHECK_REQUIRED")
    _require(_aware(now) and _aware(positions_asof), "SESSION_PREPARATION_TIME_REQUIRED")
    if type(session_id) is not str or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", session_id) is None:
        raise ValueError("invalid session identity")
    if any(type(value) is not str or not value for value in (account_scope, market, quote_currency)):
        raise ValueError("explicit session account and market required")
    model.iso_utc(now)
    end = expires_at if expires_at is not None else now + timedelta(minutes=30)
    model.iso_utc(end)
    if not now < end or end - now > timedelta(hours=24):
        raise ValueError("invalid session expiry")
    if inputs.now != now or selected_plan.start != now.astimezone(model.KST).date():
        raise ValueError("session input date mismatch")
    last = None

    def current_time():
        nonlocal last
        try:
            stamp = clock()
        except Exception:
            raise PreparationError("SESSION_PREPARATION_CLOCK_REFUSED") from None
        _require(_aware(stamp), "SESSION_PREPARATION_CLOCK_INVALID")
        _require(last is None or stamp >= last, "SESSION_PREPARATION_CLOCK_ROLLBACK")
        _require(stamp.astimezone(model.KST).date() == now.astimezone(model.KST).date(),
                 "SESSION_PREPARATION_DAY_CHANGED")
        _require(timedelta(0) <= stamp-now <= _PREPARATION_AGE,
                 "SESSION_PREPARATION_INPUTS_STALE_OR_FUTURE")
        _require(positions_asof <= now and timedelta(0) <= stamp-positions_asof <= _PREPARATION_AGE,
                 "SESSION_PREPARATION_ACCOUNT_STALE_OR_FUTURE")
        _require(stamp < end, "SESSION_PREPARATION_EXPIRED")
        _require(_aware(instrument_rules.asof) and timedelta(0) <= stamp-instrument_rules.asof <= _RULES_AGE,
                 "SESSION_PREPARATION_RULES_STALE_OR_FUTURE")
        last = stamp
        return stamp

    started = current_time()
    if type(selection_seed_hex) is not str or len(selection_seed_hex) != 64:
        raise ValueError("selection seed required")
    try:
        bytes.fromhex(selection_seed_hex)
    except ValueError:
        raise ValueError("invalid selection seed") from None
    selected_seed = models.market_seed(models.data_hashes(inputs.series, inputs.replay),
                                      inputs.calendar_sha256, inputs.comparison_id, inputs.run_counter).hex()
    if selected_seed != selection_seed_hex:
        raise ValueError("selection input seed mismatch")
    fresh = replace(inputs, comparison_id=uuid4().hex, run_counter=1,
                    comparison_plans=1, comparison_typed=int(selected_plan.leg.edge_source == "assumed"))
    expected_seed = models.market_seed(models.data_hashes(fresh.series, fresh.replay),
                                      fresh.calendar_sha256, fresh.comparison_id, fresh.run_counter).hex()
    if expected_seed == selection_seed_hex:
        raise ValueError("market seed is not fresh")
    content = (odds_plan.plan_hash(selected_plan), digest(fresh), digest(policy), rules_digest(instrument_rules),
               model.canonical_json(positions))
    ctx = owner.load_context(started, positions, session_id=session_id)
    current_time()

    if ctx.session.armed or ctx.owner.armed_sessions:
        raise ValueError("prepare before owner session arming")
    report = simulate.simulate(selected_plan, ctx, fresh)
    if report.refused is not None or any(flag.level == "red" for flag in report.flags):
        raise ValueError("fresh odds preparation refused")
    if (not ctx.code_signed or not ctx.active.valid or report.plan_hash != odds_plan.plan_hash(selected_plan)
            or report.provenance.get("seed_hex") != expected_seed):
        raise ValueError("fresh odds result mismatch")
    current_time()  # reject an overlong simulation before waiting on the journal lock
    with journal.transaction() as tx:
        checked = current_time()  # lock acquisition may itself have consumed the freshness window
        review_deadline = None
        if completion_check is not None:
            review_deadline = completion_check(checked)
            _require(_aware(review_deadline) and checked < review_deadline,
                     "SESSION_PREPARATION_REVIEW_DEADLINE_REQUIRED")
        checked = current_time()
        current_ctx = owner.load_context(checked, positions, session_id=session_id)
        _require(model.is_sealed(current_ctx) and current_ctx.owner.ok and current_ctx.code_signed
                 and current_ctx.active.valid and not current_ctx.session.armed
                 and not current_ctx.owner.armed_sessions and current_ctx.ctx_hash == ctx.ctx_hash,
                 "SESSION_PREPARATION_OWNER_CHANGED")
        _require(content == (odds_plan.plan_hash(selected_plan), digest(fresh), digest(policy),
                 rules_digest(instrument_rules), model.canonical_json(positions)),
                 "SESSION_PREPARATION_CONTENT_CHANGED")
        # Copying a long journal and hashing input history are part of the work,
        # not free time after authorization. Finish them before the final clock.
        events = tx.events
        # A row inside a pending guard transaction would leave it unresumable; resume the guard first.
        _require(not guard_pending(events), "SESSION_PREPARATION_GUARD_PENDING")
        prepared_ids = {row["data"].get("session_id") for row in events if row["kind"] == "session_prepared"}
        committed_at = current_time()
        _require(review_deadline is None or committed_at < review_deadline,
                 "SESSION_PREPARATION_REVIEW_EXPIRED")
        fields = dict(plan_hash=report.plan_hash, input_digest=content[1], policy_digest=content[2],
                      rules_digest=content[3], code_hash=current_ctx.code_hash, state_hash=current_ctx.active.state_hash,
                      seed_hex=expected_seed, selection_seed_hex=selection_seed_hex,
                      venue=selected_plan.leg.venue, symbol=selected_plan.leg.symbol,
                      account_scope=account_scope, market=market, quote_currency=quote_currency,
                      stake_krw=str(selected_plan.stake_krw), prepared_at=committed_at, expires_at=end)
        actual_session_id = session_id + "-" + digest(fields)
        fields["session_id"] = actual_session_id
        prepared = PreparedSession(**fields, record_digest=digest(fields))
        if actual_session_id in prepared_ids:
            raise ValueError("session identity already prepared")
        payload = plain(dict(fields, record_digest=prepared.record_digest))
        append_at = current_time()  # even bounded record hashing must not cross a deadline
        _require(review_deadline is None or append_at < review_deadline,
                 "SESSION_PREPARATION_REVIEW_EXPIRED")
        tx.append("session_prepared", payload, now=committed_at)
    # fsync/unlock/transaction exit can also take time. A completed durable row
    # remains an inert audit event if this last check fails; never rewrite it or
    # register/return its object. verify_session still requires issued identity.
    issued_at = current_time()
    _require(review_deadline is None or issued_at < review_deadline,
             "SESSION_PREPARATION_REVIEW_EXPIRED")
    _PREPARED[id(prepared)] = (prepared, prepared.record_digest)
    return prepared


def verify_session(prepared, *, session_id: str, policy, instrument_rules, ctx, now: datetime, order, events) -> None:
    registered = _PREPARED.get(id(prepared))
    if type(prepared) is not PreparedSession or registered is None or registered[0] is not prepared:
        raise ValueError("session preparation not issued in this process")
    fields = {key: value for key, value in vars(prepared).items() if key != "record_digest"}
    bound = {key: value for key, value in fields.items() if key != "session_id"}
    label, separator, suffix = prepared.session_id.rpartition("-")
    if (not separator or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", label) is None
            or suffix != digest(bound) or digest(fields) != prepared.record_digest
            or prepared.record_digest != registered[1]):
        raise ValueError("session preparation changed")
    if order.venue == "upbit":
        quote, symbol = order.symbol.split("-")
    elif order.venue == "okx":
        symbol, quote = order.symbol.split("-")
    else:
        symbol, quote = order.symbol, "KRW" if order.market == "krx" else "USD"
    from execution_launch.instrument_refresh import rules_binding_matches, validate_observed_order
    validate_observed_order(order, instrument_rules, now=now)
    if (prepared.session_id != session_id or prepared.policy_digest != digest(policy)
            or not rules_binding_matches(prepared.rules_digest, instrument_rules,
                                         account_scope=order.account_scope, now=now)
            or not prepared.prepared_at <= now < prepared.expires_at
            or prepared.prepared_at.astimezone(model.KST).date() != now.astimezone(model.KST).date()
            or prepared.code_hash != ctx.code_hash or prepared.state_hash != ctx.active.state_hash
            or prepared.venue != order.venue or prepared.symbol != symbol
            or prepared.account_scope != order.account_scope or prepared.market != order.market
            or prepared.quote_currency != quote):
        raise ValueError("session preparation stale or mismatched")
    if not ctx.owner.ok or not ctx.code_signed or not ctx.session.armed:
        raise ValueError("owner session not signed and armed")
    found = [row for row in events if row["kind"] == "session_prepared"
             and row["data"].get("session_id") == session_id]
    if len(found) != 1 or found[0]["data"] != plain(prepared):
        raise ValueError("session preparation journal mismatch")
