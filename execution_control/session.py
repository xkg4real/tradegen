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


def prepare_session(*, journal, session_id: str, selected_plan, inputs, positions,
                    policy, instrument_rules, now: datetime, selection_seed_hex: str,
                    account_scope: str, market: str, quote_currency: str,
                    expires_at: datetime | None = None) -> PreparedSession:
    """Actually rerun selected_plan with a fresh comparison seed before arming.

    Inputs and positions come from the caller's reconciled observations. A result
    with any red diagnostic cannot prepare a session. The original selected seed
    is required so seed freshness is independently checked.
    """
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
    ctx = owner.load_context(now, positions, session_id=session_id)
    if ctx.session.armed or ctx.owner.armed_sessions:
        raise ValueError("prepare before owner session arming")
    report = simulate.simulate(selected_plan, ctx, fresh)
    if report.refused is not None or any(flag.level == "red" for flag in report.flags):
        raise ValueError("fresh odds preparation refused")
    if (not ctx.code_signed or not ctx.active.valid or report.plan_hash != odds_plan.plan_hash(selected_plan)
            or report.provenance.get("seed_hex") != expected_seed):
        raise ValueError("fresh odds result mismatch")
    fields = dict(plan_hash=report.plan_hash, input_digest=digest(fresh),
                  policy_digest=digest(policy), rules_digest=rules_digest(instrument_rules), code_hash=ctx.code_hash, state_hash=ctx.active.state_hash,
                  seed_hex=expected_seed, selection_seed_hex=selection_seed_hex,
                  venue=selected_plan.leg.venue, symbol=selected_plan.leg.symbol,
                  account_scope=account_scope, market=market, quote_currency=quote_currency,
                  stake_krw=str(selected_plan.stake_krw), prepared_at=now, expires_at=end)
    session_id = session_id + "-" + digest(fields)
    fields["session_id"] = session_id
    prepared = PreparedSession(**fields, record_digest=digest(fields))
    with journal.transaction() as tx:
        if any(row["kind"] == "session_prepared" and row["data"].get("session_id") == session_id
               for row in tx.events):
            raise ValueError("session identity already prepared")
        tx.append("session_prepared", plain(dict(fields, record_digest=prepared.record_digest)), now=now)
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
    if (prepared.session_id != session_id or prepared.policy_digest != digest(policy)
            or prepared.rules_digest != rules_digest(instrument_rules)
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
