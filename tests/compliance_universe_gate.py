"""Upbit KRW universe PR 3 (spec 2026-11-11, sections 5 and 8): derived Upbit KRW coins at the gate and the snapshot
that load_context reads back. A coin no signed map lists resolves to a copy of the signed BTC entry for a KRW sell of
a held coin, for new exposure under the venue's signed universe_rule and for a recorded order. New exposure on it
also needs ctx.universe built under that rule with the coin eligible."""
from __future__ import annotations

import builtins
import dataclasses
import datetime as _dt
import types
from decimal import Decimal

from core.compliance import gate, model, owner, rules
from tests import compliance_fixtures as F

D23, D24 = _dt.date(2026, 10, 23), _dt.date(2026, 10, 24)

_SELL = {"action": "sell", "quantity": 10.0, "notional_krw": 10_000.0}


def _ruled() -> model.ApprovedState:
    """The shipped tables with universe_rule in upbit's venue facts (F.universe_venues_raw)."""
    return F.approved(venues=F.universe_venues_raw())


def _xrp(**changes) -> model.Intent:
    """F.intent for XRP: a buy of 10 XRP for KRW at KRW 50,000 unless `changes` say otherwise."""
    return F.intent(**{"symbol": "XRP", "quantity": 10.0, **changes})


def _grey(state) -> model.ApprovedState:
    """`state` with KR-DOMESTIC-SPOT signed grey, so grey_rows has a row to name for an upbit leg."""
    rows = tuple(dataclasses.replace(r, treatment="grey") if r.id == "KR-DOMESTIC-SPOT" else r
                 for r in state.rules.rows)
    return dataclasses.replace(state, rules=dataclasses.replace(state.rules, rows=rows))


def _plan(symbol: str, start):
    """A duck-typed upbit plan (P3): screen() and grey_rows() read leg.venue, leg.symbol, start and horizon_days."""
    return types.SimpleNamespace(leg=types.SimpleNamespace(venue="upbit", symbol=symbol), start=start,
                                 horizon_days=5)


def test_lookup_resolves_a_derived_coin_only_where_spec_8_says():
    """gate.lookup: the signed entry for a mapped symbol. For an Upbit symbol in no map whose KRW market matches the
    pattern, it returns a copy of the signed BTC entry under that symbol, for a recorded order (either side), an exit
    of a held coin, or new exposure under universe_rule; otherwise None. market_listed lists a derived coin against
    KRW only."""
    plain, ruled, c = F.approved(), _ruled(), F.ctx()
    upbit, ruled_upbit = plain.venues.venues["upbit"], ruled.venues.venues["upbit"]
    btc = plain.instruments.lookup(upbit.sections, "BTC")
    xrp = dataclasses.replace(btc, symbol="XRP")
    assert gate.lookup(c, plain, upbit, "BTC", False) is btc
    assert gate.lookup(c, ruled, ruled_upbit, "BTC", True) == btc
    for exits in (False, True):
        assert gate.lookup(c, plain, upbit, "XRP", exits) is None, exits
        assert gate.lookup(c, plain, upbit, "XRP", exits, recorded=True) == xrp, exits
    held = F.ctx(holdings={("upbit", "XRP"): 1.0})
    assert gate.lookup(held, plain, upbit, "XRP", True) == xrp             # an exit needs no rule
    assert gate.lookup(held, plain, upbit, "XRP", False) is None           # new exposure does
    assert gate.lookup(c, ruled, ruled_upbit, "XRP", False) == xrp
    assert gate.lookup(c, ruled, ruled_upbit, "XRP", True) is None         # nothing held: no exit
    for venue, symbol in ((plain.venues.venues["bithumb"], "XRP"), (upbit, "KRW"), (upbit, "xrp"), (upbit, 5),
                          (upbit, "A" * 13), (upbit, "X-Y")):
        assert gate.lookup(c, plain, venue, symbol, True, recorded=True) is None, (venue.id, symbol)
    assert gate.market_listed(plain, upbit, xrp, "KRW") and not gate.market_listed(plain, upbit, xrp, "USDT")
    assert gate.market_listed(plain, upbit, btc, "KRW") and not gate.market_listed(plain, upbit, btc, "USD")


def test_map_coins_keep_todays_path():
    """Spec 8: a symbol of a signed map is decided as before, with or without universe_rule and a snapshot."""
    ruled = _ruled()
    base = gate.decide(F.intent(), F.ctx())
    assert (base.verdict, base.kind, base.reasons) == (model.ALLOW, "new_exposure", ()), base.reasons
    for c in (F.ctx(active=ruled), F.ctx(active=ruled, universe=F.universe())):
        d = gate.decide(F.intent(), c)
        assert (d.verdict, d.kind, d.reasons) == (base.verdict, base.kind, base.reasons), d.reasons
        usdt = gate.decide(F.intent(symbol="USDT"), c)
        assert usdt.verdict == model.ALLOW, usdt.reasons


def test_derived_buys_need_the_rule_a_snapshot_in_force_and_eligibility():
    """Spec 8: new exposure on a derived coin needs universe_rule in the signed venue facts. Without it the symbol is
    unknown, as before. It also needs ctx.universe built under that rule (else "state: universe no_snapshot") and the
    coin in its eligible set (else "state: universe not_eligible"). With all three, the rows decide it as they decide
    BTC."""
    ruled = _ruled()
    no_rule = gate.decide(_xrp(), F.ctx(universe=F.universe()))
    assert no_rule.verdict == model.BLOCK and no_rule.reasons == ("malformed: symbol",), no_rule.reasons
    foreign = dataclasses.replace(F.universe(), rule_sha256="0" * 64)
    for c in (F.ctx(active=ruled), F.ctx(active=ruled, universe=foreign)):
        d = gate.decide(_xrp(), c)
        assert (d.verdict, d.kind, d.reasons) == (model.BLOCK, "new_exposure", ("state: universe no_snapshot",)), d
    doge = gate.decide(_xrp(symbol="DOGE"), F.ctx(active=ruled, universe=F.universe()))
    assert doge.verdict == model.BLOCK and doge.reasons == ("state: universe not_eligible",), doge.reasons
    ok = gate.decide(_xrp(), F.ctx(active=ruled, universe=F.universe()))
    assert (ok.verdict, ok.kind, ok.reasons) == (model.ALLOW, "new_exposure", ()), ok.reasons
    for bad, field in ((_xrp(counter_symbol="USDT"), "counter_symbol"), (_xrp(asset="us_etp"), "asset"),
                       (_xrp(symbol="xrp"), "symbol"), (_xrp(symbol="KRW"), "symbol")):
        d = gate.decide(bad, F.ctx(active=ruled, universe=F.universe()))
        assert d.verdict == model.BLOCK and f"malformed: {field}" in d.reasons, (field, d.reasons)


def test_held_coin_krw_exits_need_no_snapshot_and_survive_a_dropped_rule():
    """Spec 8: a cash sell for KRW of a held derived coin is ALLOW_EXIT close_long with no snapshot, with no rule (as
    after a venues approval that drops universe_rule), and from the recovery snapshot. _within_free checks its
    quantity, and its only market is (coin, KRW)."""
    held = {("upbit", "XRP"): 25.0}
    sell = _xrp(**_SELL)
    broken = model.OwnerState.broken("bad signature on entry 4")
    for c in (F.ctx(holdings=held), F.ctx(active=_ruled(), holdings=held),
              F.ctx(active=model.ApprovedState.invalid("fixture"), snapshot=F.approved(), holdings=held),
              F.ctx(owner=broken, snapshot=_ruled(), holdings=held)):
        d = gate.decide(sell, c)
        assert (d.verdict, d.kind) == (model.ALLOW_EXIT, "close_long"), d.reasons
    unheld = gate.decide(sell, F.ctx(active=_ruled(), universe=F.universe()))
    assert unheld.verdict == model.BLOCK, unheld.reasons
    assert {"malformed: symbol", "close manually in the broker app"} <= set(unheld.reasons), unheld.reasons
    over = gate.decide(_xrp(**{**_SELL, "quantity": 30.0}), F.ctx(holdings=held))
    assert over.verdict == model.BLOCK and "malformed: quantity" in over.reasons, over.reasons
    usdt = gate.decide(_xrp(**{**_SELL, "counter_symbol": "USDT"}), F.ctx(holdings=held))
    assert usdt.verdict == model.BLOCK and "malformed: counter_symbol" in usdt.reasons, usdt.reasons


def test_a_derived_coin_never_transfers():
    """Spec 8: _transfer stays on the signed maps, and a derived coin leaves only by a KRW sell. Its transfer, to a
    domestic exchange or abroad, is therefore an unknown symbol, and the domestic one is sent to the app."""
    c = F.ctx(active=_ruled(), universe=F.universe(), holdings={("upbit", "XRP"): 25.0})
    move = _xrp(action="transfer_out", counter_symbol="", quantity=10.0, notional_krw=10_000.0,
                destination_venue="bithumb", destination_address="rFixtureAddress", destination_network="ripple")
    home = gate.decide(move, c)
    assert home.verdict == model.BLOCK, home.reasons
    assert {"malformed: symbol", "withdraw manually in the exchange app"} <= set(home.reasons), home.reasons
    away = gate.decide(dataclasses.replace(move, destination_venue="okx"), c)
    assert away.verdict == model.BLOCK and away.reasons == ("malformed: symbol",), away.reasons


def test_the_step_5_universe_check_names_each_reason():
    """The step 5 universe check by itself. decide never reaches no_rule: its lookup already refuses a derived buy
    without the rule ("malformed: symbol"), so no_rule is defence in depth. The check returns no_rule, no_snapshot,
    not_eligible and then [] as each condition is met, and [] for a map coin."""
    plain, ruled = F.approved(), _ruled()
    upbit, ruled_upbit = plain.venues.venues["upbit"], ruled.venues.venues["upbit"]
    full = F.ctx(active=ruled, universe=F.universe())
    assert gate._universe(F.ctx(universe=F.universe()), plain, upbit, "XRP") == ["state: universe no_rule"]
    assert gate._universe(F.ctx(active=ruled), ruled, ruled_upbit, "XRP") == ["state: universe no_snapshot"]
    assert gate._universe(full, ruled, ruled_upbit, "DOGE") == ["state: universe not_eligible"]
    assert gate._universe(full, ruled, ruled_upbit, "XRP") == []
    assert gate._universe(F.ctx(), plain, upbit, "BTC") == []


def test_screen_and_grey_rows_see_a_derived_eligible_coin():
    """Spec 8: screen (exits=False) decides a derived leg as decide does, so simulate can run it. grey_rows names the
    grey rows matching it under the rule, and () without the rule."""
    ruled = _ruled()
    c = F.ctx(active=ruled, universe=F.universe())
    leg = _plan("XRP", c.date)
    s = gate.screen(leg, c, 42_000.0)
    assert s.allowed and s.decision.verdict == model.ALLOW and s.decision.reasons == (), s.decision.reasons
    assert s.decision.intent_hash == model.intent_hash(_xrp(quantity=1.0, notional_krw=42_000.0))
    blocked = gate.screen(leg, F.ctx(active=ruled), 42_000.0)
    assert not blocked.allowed and blocked.decision.reasons == ("state: universe no_snapshot",), blocked
    unknown = gate.screen(leg, F.ctx(universe=F.universe()), 42_000.0)
    assert not unknown.allowed and "malformed: symbol" in unknown.decision.reasons, unknown.decision.reasons
    assert gate.grey_rows(leg, c) == ()
    assert gate.grey_rows(leg, F.ctx(active=_grey(ruled), universe=F.universe())) == ("KR-DOMESTIC-SPOT",)
    assert gate.grey_rows(leg, F.ctx(active=_grey(F.approved()))) == ()


# --------------------------------------------------------------------------- #
# Read-back (spec 5): load_context fills ctx.universe with the verified snapshot in force for the active rule
# --------------------------------------------------------------------------- #
def _utc(*parts) -> _dt.datetime:
    return _dt.datetime(*parts, tzinfo=_dt.timezone.utc)


def _signed_home(home):
    """F.full_home with universe_rule in the approved venues; returns the test key."""
    return F.full_home(home, venues_raw=F.universe_venues_raw())


def _held_xrp() -> model.Positions:
    return model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "XRP"): 25.0})


def test_load_context_reads_the_snapshot_in_force_and_drops_it_with_the_rule():
    """Spec 5: the snapshot of candle day 2026-10-23, verified under the active rule, is ctx.universe at NOW
    (2026-10-24 09:00 KST), and an XRP buy is ALLOW. Once the owner approves venues without universe_rule, the
    universe is None, the buy is an unknown symbol, and a held XRP sell is still ALLOW_EXIT."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        key = _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        c = owner.load_context(F.NOW, _held_xrp())
        assert c.owner.ok and c.active.valid and c.code_signed, (c.owner.reason, c.active.reason)
        u = c.universe
        assert u is not None and u.day == D23 and u.rule_sha256 == rules.universe_rule_sha256(F.universe_rule())
        assert dict(u.eligible) == {"KRW-BTC": Decimal(2_000_000_000), "KRW-XRP": Decimal(2_000_000_000)}
        assert (u.built_at, u.valid_from, u.valid_until) == (
            _utc(2026, 10, 23, 0, 15), _utc(2026, 10, 23, 0, 40), _utc(2026, 10, 24, 0, 40))
        assert c.ctx_hash == model.context_hash(c)
        assert gate.decide(_xrp(), c).verdict == model.ALLOW
        F.approve(home, key, "venues", F.shipped_bytes("venues"))          # the owner drops universe_rule
        dropped = owner.load_context(F.NOW, _held_xrp())
        assert dropped.active.valid and dropped.universe is None, dropped.active.reason
        assert gate.decide(_xrp(), dropped).reasons == ("malformed: symbol",)
        sell = gate.decide(_xrp(**_SELL), dropped)
        assert (sell.verdict, sell.kind) == (model.ALLOW_EXIT, "close_long"), sell.reasons


def test_the_snapshot_in_force_switches_at_0940_kst():
    """Spec 5: candle day D's file is in force on [max(built_at, D 00:40 UTC), D+1 00:40 UTC), with D the UTC date of
    now minus 40 minutes. Before 09:40 KST on 10-23 nothing holds, because day 10-22 has no file. 10-23's file holds
    from 09:40 KST on 10-23 to 09:39:59 KST on 10-24. 10-24's file was built late, at 01:00 UTC, so it holds only
    from its built_at."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        F.universe_file(F.universe_rule(), D24, served=_utc(2026, 10, 24, 1, 0))
        for at, day in ((_utc(2026, 10, 23, 0, 39, 59), None), (_utc(2026, 10, 23, 0, 40), D23),
                        (_utc(2026, 10, 24, 0, 39, 59), D23), (_utc(2026, 10, 24, 0, 40), None),
                        (_utc(2026, 10, 24, 0, 59, 59), None), (_utc(2026, 10, 24, 1, 0), D24)):
            u = owner.load_context(at, F.HELD).universe
            assert (None if u is None else u.day) == day, (at, u)


def test_the_earliest_built_snapshot_wins_and_verification_is_cached():
    """Spec 5: two verified files for one candle day (a manual rebuild). The earliest built is in force. Each file is
    verified once per process, keyed by its sha256, however often load_context runs."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23, served=_utc(2026, 10, 23, 0, 20), markets=("KRW-BTC",))
        F.universe_file(F.universe_rule(), D23)                                       # served 00:15
        calls, real = [], rules.verify_universe_snapshot
        rules.verify_universe_snapshot = lambda raw, sha: calls.append(sha) or real(raw, sha)
        try:
            first = owner.load_context(F.NOW, F.HELD).universe
            again = owner.load_context(F.NOW, F.HELD).universe
        finally:
            rules.verify_universe_snapshot = real
        assert first is not None and first.built_at == _utc(2026, 10, 23, 0, 15), first
        assert [m for m, _ in first.eligible] == ["KRW-BTC", "KRW-XRP"] and again == first
        assert len(calls) == 2, calls


def test_a_tampered_or_foreign_snapshot_is_not_in_force():
    """Spec 5: a file whose receipts no longer match its request set and manifest, or a file built under another
    rule, does not verify. ctx.universe is then None and an XRP buy is BLOCK "state: universe no_snapshot", while the
    rest of the context stays intact."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        path = F.universe_file(F.universe_rule(), D23)
        raw = path.read_bytes()
        assert b"KRW-XRP" in raw
        path.write_bytes(raw.replace(b"KRW-XRP", b"KRW-XRQ"))
        F.universe_file(dataclasses.replace(F.universe_rule(), min_median_value_krw=5), D23)
        c = owner.load_context(F.NOW, F.HELD)
        assert c.owner.ok and c.active.valid and c.universe is None, (c.owner.reason, c.active.reason)
        assert gate.decide(_xrp(), c).reasons == ("state: universe no_snapshot",)


def test_a_read_back_error_never_breaks_the_context_or_a_held_coin_exit():
    """Spec 5 and 19: the read-back catches every exception. A TypeError raised inside it leaves ctx.universe None and
    the rest of the context intact: a held XRP sell is ALLOW_EXIT and an XRP buy is BLOCK "state: universe
    no_snapshot"."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        real = owner.universe_dir

        def broken(day):
            raise TypeError("fixture read-back failure")

        owner.universe_dir = broken
        try:
            c = owner.load_context(F.NOW, _held_xrp())
        finally:
            owner.universe_dir = real
        assert c.owner.ok and c.active.valid and c.code_signed and c.universe is None, (c.owner.reason,
                                                                                         c.active.reason)
        sell = gate.decide(_xrp(**_SELL), c)
        assert (sell.verdict, sell.kind) == (model.ALLOW_EXIT, "close_long"), sell.reasons
        assert gate.decide(_xrp(), c).reasons == ("state: universe no_snapshot",)


def test_the_read_back_recomputes_without_importing_execution():
    """Spec 19: load_context recomputes the snapshot (rules.verify_universe_snapshot over the receipts, with the cache
    cleared) and imports no execution* module on the way."""
    with F.temp_home() as home, F.pubkey_at(home / "owner_pubkey.pem"):
        _signed_home(home)
        owner._UNIVERSE_VERIFIED.clear()
        F.universe_file(F.universe_rule(), D23)
        names, real = [], builtins.__import__

        def spy(name, *args, **kwargs):
            names.append(name)
            return real(name, *args, **kwargs)

        builtins.__import__ = spy
        try:
            c = owner.load_context(F.NOW, F.HELD)
        finally:
            builtins.__import__ = real
        assert c.universe is not None and c.universe.day == D23
        assert [n for n in names if n.split(".")[0].startswith("execution")] == [], names
