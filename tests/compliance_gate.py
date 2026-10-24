"""decide() steps 0-3 and 7, and the hard-coded floor (Task 7; spec 5.2, 6.1, 6.2; compliance tests 3, 4, 5, 8).

Steps 4-6 fail closed until Task 8, so nothing here asserts an ALLOW: only BLOCKs, kinds and reasons that stay true
once Task 8 fills them in. Helpers are prefixed `_t7_` so that later tasks appending to this file cannot shadow them.
"""
from __future__ import annotations

import dataclasses
import math
import random

from core.compliance import gate, model, rules
from tests import compliance_fixtures as F

_T7_VERDICTS = (model.ALLOW, model.ALLOW_EXIT, model.ACK_REQUIRED, model.BLOCK)
_T7_OPTION = "AAPL261218C00300000"                     # fixture-only symbol; the shipped map has no option
_T7_ADDRESS = ("upbit", "BTC", "bitcoin", "bc1qfixtureaddress", "")
_T7_WHEN = {"route_not_direct": {"route": "vpn"}, "on_behalf_not_self": {"on_behalf": "follower"},
            "publishes_signal": {"publishes_signal": True}}


def _t7_kis(symbol: str, **changes) -> model.Intent:
    """A KIS buy of a shipped-map symbol, asset and multiple copied from the map."""
    state = F.approved()
    inst = state.instruments.lookup(state.venues.venues["kis"].sections, symbol)
    assert inst is not None, f"{symbol} is not in the shipped instrument map"
    return F.intent(**{"venue": "kis", "symbol": symbol, "counter_symbol": inst.currency, "asset": inst.asset,
                       "multiple": inst.multiple, "quantity": 1.0, "notional_krw": 70_000.0, **changes})


def _t7_option(**changes) -> model.Intent:
    return F.intent(**{"venue": "kis", "symbol": _T7_OPTION, "counter_symbol": "USD", "asset": "us_option",
                       "multiple": 1.0, "quantity": 1.0, "notional_krw": 20_000.0, **changes})


def _t7_with_option(state: model.ApprovedState) -> model.ApprovedState:
    """`state` with one fixture US option added to its map (the shipped map has none)."""
    option = rules.Instrument(section="us", symbol=_T7_OPTION, asset="us_option", multiple=1.0, underlying=None,
                              cls="option", cost_book=None, currency="USD", tax_basis="unsupported",
                              source="fixture: not a real listing")
    entries = {**state.instruments.entries, ("us", _T7_OPTION): option}
    return dataclasses.replace(state, instruments=dataclasses.replace(state.instruments, entries=entries))


def _t7_floor_only() -> model.ApprovedState:
    """The shipped state with every rules row deleted except one harmless allow row."""
    state = F.approved()
    keep = tuple(r for r in state.rules.rows if r.id == "KR-KIS-KRX-SHARE")
    assert len(keep) == 1 and keep[0].treatment == "allow" and keep[0].kind == "venue"
    return dataclasses.replace(state, rules=dataclasses.replace(state.rules, rows=keep))


def _t7_withdraw(**changes) -> model.Intent:
    """OKX -> Upbit BTC on the bitcoin network, to the address _t7_owner() registers."""
    return F.intent(**{"venue": "okx", "counter_symbol": "", "action": "transfer_out",
                       "destination_venue": "upbit", "destination_address": _T7_ADDRESS[3],
                       "destination_network": "bitcoin", **changes})


def _t7_owner(**changes) -> model.OwnerState:
    """The fixture owner (contract 5.4) with _T7_ADDRESS registered; any field can be replaced, addresses included."""
    return dataclasses.replace(F.ctx(active=model.ApprovedState.invalid("unused")).owner,
                               **{"addresses": frozenset({_T7_ADDRESS}), **changes})


def _t7_has(d: model.Decision, prefix: str) -> bool:
    return any(r.startswith(prefix) for r in d.reasons)


def test_hand_built_context_is_refused():
    sealed = F.ctx()
    hand = model.Context(**{f.name: getattr(sealed, f.name) for f in dataclasses.fields(model.Context)})
    for c in (hand, dataclasses.replace(sealed, code_signed=True), None, object(), "ctx"):
        d = gate.decide(F.intent(), c)
        assert d.verdict == model.BLOCK and d.reasons == ("state: context not from load_context",), d
        assert (d.code_hash, d.ctx_hash, d.owner_head, d.date, d.state_hash) == ("", "", (0, ""), None, "")


def test_decision_records_provenance():
    c, i = F.ctx(), F.intent()
    d = gate.decide(i, c)
    assert d.intent_hash == model.intent_hash(i) and d.state_hash == c.active.state_hash != ""
    assert (d.code_hash, d.owner_head, d.ctx_hash, d.date) == (c.code_hash, c.owner.head, c.ctx_hash, c.date)
    assert d.kind == "new_exposure" and d.verdict in _T7_VERDICTS and len(d.decision_id) == 64
    assert gate.decide(i, c) == d                                        # deterministic
    assert d.ack is None or d.verdict == model.ACK_REQUIRED


def test_every_conduct_tag_and_predicate_blocks_exits_included():
    c = F.ctx(holdings={("upbit", "BTC"): 1.0, ("okx", "BTC"): 1.0}, shorts={("kis", "005930"): 10.0},
              owner=_t7_owner())
    bases = {"new_exposure": F.intent(), "close_long": F.intent(action="sell"),
             "cover_short": _t7_kis("005930", action="buy_to_cover"), "withdraw": _t7_withdraw()}
    cases = [({"tags": frozenset({t})}, f"conduct: {t}") for t in sorted(rules.TAGS)]
    cases += [(change, f"conduct: {name}") for name, change in sorted(_T7_WHEN.items())]
    for kind, base in bases.items():
        clean = gate.decide(base, c)
        assert clean.kind == kind and not _t7_has(clean, "conduct: "), (kind, clean.reasons)
        for change, reason in cases:
            d = gate.decide(dataclasses.replace(base, **change), c)
            assert d.verdict == model.BLOCK and d.kind == kind and reason in d.reasons, (kind, change, d.reasons)
    for asset in sorted(gate.FLOOR_ALL_ASSETS):                          # malformed here, and still conduct
        d = gate.decide(F.intent(action="sell", asset=asset), c)
        assert d.verdict == model.BLOCK and f"conduct: {asset}" in d.reasons, d.reasons


def test_shipped_conduct_rows_each_fire():
    rows = [r for r in F.approved().rules.rows if r.kind == "conduct"]
    assert rows, "the shipped table has no conduct rows"
    c = F.ctx()
    for row in rows:
        fields = {}
        for key, allowed in sorted(row.match.items()):
            values = sorted(allowed - {"any"})
            if not values:
                continue
            if key == "tag":
                fields["tags"] = frozenset(values[:1])
            elif key == "when":
                fields.update(_T7_WHEN[values[0]])
            elif key == "class":
                assets = sorted(a for a, cls in rules.ASSET_CLASS.items() if cls in allowed)
                assert assets, f"{row.id}: a conduct row keyed on an ETP class never fires (gate._conduct)"
                fields["asset"] = assets[0]
            else:
                fields[key] = values[0]
        d = gate.decide(F.intent(**fields), c)
        assert d.verdict == model.BLOCK and f"conduct: {row.id}" in d.reasons, (row.id, fields, d.reasons)


def test_floor_blocks_with_the_table_rows_deleted():
    state = _t7_floor_only()
    c = F.ctx(active=state, holdings={("kis", "IBIT"): 2.0, ("upbit", "BTC"): 1.0})
    for change, reason in [({"tags": frozenset({"spoof"})}, "conduct: spoof"),
                           ({"route": "vpn"}, "conduct: route_not_direct"),
                           ({"asset": "event_contract"}, "conduct: event_contract"),
                           ({"asset": "sports_bet"}, "conduct: sports_bet")]:
        for base in (F.intent(), F.intent(action="sell")):                     # new exposure and an exit
            d = gate.decide(dataclasses.replace(base, **change), c)
            assert d.verdict == model.BLOCK and reason in d.reasons, (change, d.reasons)
    cases = [(F.intent(venue=v, counter_symbol="USDT"), f"floor: {v}") for v in sorted(gate.FLOOR_NEW_VENUES)]
    cases += [(F.intent(venue="okx", counter_symbol="USDT", asset="crypto_perp_or_future"),
               "floor: okx crypto_perp_or_future"),
              (F.intent(venue="okx", counter_symbol="USDT", action="p2p_buy"), "floor: okx p2p_buy"),
              (F.intent(venue="okx", counter_symbol="USDT", action="p2p_sell"), "floor: okx p2p_sell"),
              (_t7_withdraw(venue="upbit", destination_venue="polymarket"), "floor: polymarket")]
    kis = state.venues.venues["kis"]
    spot = [s for s in sorted(rules.KNOWN_SPOT_CRYPTO_ETPS) if state.instruments.lookup(kis.sections, s)]
    assert {"IBIT", "GDLC", "EZPZ"} <= set(spot), spot
    cases += [(_t7_kis(s), "floor: etp_crypto_spot") for s in spot]
    cases += [(_t7_kis("005930", asset=a), f"floor: {a}") for a in sorted(gate.FLOOR_NEW_ASSETS)]
    for i, reason in cases:
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and reason in d.reasons, (i, d.reasons)
    write = gate.decide(_t7_option(action="write"), F.ctx(active=_t7_with_option(state)))
    assert write.verdict == model.BLOCK and write.kind == "new_exposure" and "floor: option write" in write.reasons
    sell = gate.decide(_t7_kis("IBIT", action="sell"), c)                   # a held IBIT can still be sold (D11)
    assert sell.kind == "close_long" and not _t7_has(sell, "floor: "), sell.reasons


def test_classification_goes_through_the_map():
    state, c = F.approved(), F.ctx()
    expected = {"TQQQ": "etp_leveraged", "252670": "etp_leveraged", "SH": "etp_index_inverse",
                "IBIT": "etp_crypto_spot", "GDLC": "etp_crypto_spot", "BITO": "etp_crypto_futures_1x"}
    for symbol, cls in expected.items():
        i = _t7_kis(symbol)
        inst, venue, bad = gate._validate(i, c, state)
        assert bad == [] and inst.cls == cls and venue.id == "kis", (symbol, bad)
        wrong = gate.decide(dataclasses.replace(i, multiple=i.multiple + 1.0), c)
        assert wrong.verdict == model.BLOCK and "malformed: multiple" in wrong.reasons, (symbol, wrong.reasons)
    assert (_t7_kis("252670").multiple, _t7_kis("TQQQ").multiple, _t7_kis("SH").multiple) == (-2.0, 3.0, -1.0)
    assert not _t7_has(gate.decide(_t7_kis("BITO"), c), "floor: ")
    assert "class" not in {f.name for f in dataclasses.fields(model.Intent)}     # the caller never supplies it
    lev = next(r for r in state.rules.rows if r.id == "KR-KIS-ETP-LEV")         # P12: `class` is the derived one
    assert gate._matches(lev, _t7_kis("TQQQ"), "etp_leveraged") and not gate._matches(lev, _t7_kis("SPY"), "etp_1x")
    swap = F.intent(venue="okx", symbol="USDT", counter_symbol="BTC", action="sell")   # (USDT, BTC) is no okx market
    d = gate.decide(swap, F.ctx(holdings={("okx", "USDT"): 100.0}))
    assert d.kind == "malformed" and "malformed: counter_symbol" in d.reasons, d.reasons
    okx = state.venues.venues["okx"]
    wide = dataclasses.replace(okx, markets=okx.markets | {("USDT", "USDC")})    # a fixture-only market
    venues = dataclasses.replace(state.venues, venues={**state.venues.venues, "okx": wide})
    listed = F.ctx(active=dataclasses.replace(state, venues=venues), holdings={("okx", "USDT"): 100.0})
    settle = gate.decide(F.intent(venue="okx", symbol="USDT", counter_symbol="USDC", action="sell"), listed)
    assert settle.kind == "new_exposure", settle.reasons                   # a settlement asset sold: no close_long
    both = F.ctx(holdings={("upbit", "BTC"): 1.0}, shorts={("kis", "005930"): 10.0})
    for financing in ("credit", "margin"):                                  # D15: only cash-financed intents are exits
        for i, exit_kind in ((F.intent(action="sell"), "close_long"),
                             (_t7_kis("005930", action="buy_to_cover"), "cover_short")):
            assert gate.decide(i, both).kind == exit_kind, i.action
            d = gate.decide(dataclasses.replace(i, financing=financing), both)
            assert d.kind == "new_exposure" and d.verdict == model.BLOCK, (i.action, financing, d.reasons)


def test_credit_lend_and_borrow_block():
    # D15. Steps 4-6 fail closed until Task 8, so the BLOCK here only shows the intents are well formed. The row
    # matches are pinned directly; Task 8 asserts the reasons "out_of_scope: KR-KIS-CREDIT" and
    # "out_of_scope: KR-DOMESTIC-LENDING".
    rows = {r.id: r for r in F.approved().rules.rows}
    c = F.ctx(holdings={("upbit", "BTC"): 1.0})
    credit = _t7_kis("005930", financing="credit")
    d = gate.decide(credit, c)
    assert d.verdict == model.BLOCK and d.kind == "new_exposure", d.reasons
    assert gate._matches(rows["KR-KIS-CREDIT"], credit, "share")
    assert not gate._matches(rows["KR-KIS-CREDIT"], _t7_kis("005930"), "share")    # cash is not credit
    for action in ("lend", "borrow"):
        i = F.intent(action=action, counter_symbol="")
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == "new_exposure", (action, d.reasons)
        assert gate._matches(rows["KR-DOMESTIC-LENDING"], i, "coin"), action
    assert not gate._matches(rows["KR-DOMESTIC-LENDING"], F.intent(), "coin")      # a buy is not lending


def test_fail_closed_inputs_are_malformed():
    c = F.ctx(active=_t7_with_option(F.approved()), holdings={("upbit", "BTC"): 0.003, ("kis", "IBIT"): 1.0},
              shorts={("kis", "005930"): 1.0},
              exposure={"upbit": model.Exposure(held_krw=150_000.0, promised_sell_units={"BTC": 0.002})})
    w = _t7_withdraw(venue="upbit", destination_venue="bithumb")
    cases = [
        (F.intent(quantity=math.nan), "quantity"), (F.intent(quantity=math.inf), "quantity"),
        (F.intent(quantity=-0.001), "quantity"), (F.intent(quantity=0.0), "quantity"),
        (F.intent(quantity="0.001"), "quantity"), (F.intent(quantity=True), "quantity"),
        (F.intent(notional_krw=math.inf), "notional_krw"), (F.intent(notional_krw=-1.0), "notional_krw"),
        (F.intent(notional_krw=math.nan), "notional_krw"), (F.intent(multiple=math.nan), "multiple"),
        (F.intent(venue=5), "venue"), (F.intent(venue="UPBIT"), "venue"), (F.intent(symbol="btc"), "symbol"),
        (F.intent(symbol="DOGE"), "symbol"), (F.intent(asset="Crypto_coin"), "asset"),
        (F.intent(action="BUY"), "action"), (F.intent(financing="loan"), "financing"),
        (F.intent(publishes_signal="no"), "publishes_signal"), (F.intent(tags=frozenset({"pump"})), "tags"),
        (F.intent(tags=["spoof"]), "tags"), (F.intent(reservation_id=""), "reservation_id"),
        (F.intent(destination_venue="bithumb"), "destination_venue"),
        (F.intent(destination_address="bc1q"), "destination_address"),
        (dataclasses.replace(w, destination_address=None), "destination_address"),
        (dataclasses.replace(w, destination_network=""), "destination_network"),
        (dataclasses.replace(w, destination_tag=""), "destination_tag"),
        (dataclasses.replace(w, destination_venue="upbit"), "destination_venue"),
        (dataclasses.replace(w, destination_venue="Bithumb"), "destination_venue"),
        (dataclasses.replace(w, counter_symbol="KRW"), "counter_symbol"),
        (F.intent(counter_symbol="USDT"), "counter_symbol"), (F.intent(counter_symbol=""), "counter_symbol"),
        (_t7_kis("TQQQ", counter_symbol="KRW"), "counter_symbol"), (F.intent(action="lend"), "counter_symbol"),
        (F.intent(action="sell", quantity=0.004), "quantity"),               # beyond holdings
        (F.intent(action="sell", quantity=0.002), "quantity"),               # within holdings, beyond promised
        (dataclasses.replace(w, quantity=0.002), "quantity"),
        (_t7_option(action="sell"), "quantity"),                             # an option sell with no holding
        (_t7_kis("005930", action="buy_to_cover", quantity=2.0), "quantity"),   # beyond the short
        (F.intent(asset="us_etp"), "asset"), (_t7_kis("TQQQ", multiple=1.0), "multiple"),
    ]
    for i, field in cases:
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == "malformed" and f"malformed: {field}" in d.reasons, \
            (i, d.reasons)
    ok = gate.decide(F.intent(action="sell", quantity=0.001), c)            # exactly the free units
    assert ok.kind == "close_long" and not _t7_has(ok, "malformed: "), ok.reasons
    assert gate.decide(w, c).kind != "malformed"


def test_negative_positions_block():
    cases = [(F.ctx(exposure={"upbit": model.Exposure(held_krw=-1.0)}), F.intent(), "exposure"),
             (F.ctx(exposure={"upbit": model.Exposure(held_krw=0.0, reservations={"R": -5.0})}), F.intent(),
              "exposure"),
             (F.ctx(holdings={("upbit", "BTC"): -1.0}), F.intent(action="sell"), "holdings"),
             (F.ctx(shorts={("upbit", "BTC"): -1.0}), F.intent(), "shorts"),
             (F.ctx(equity_krw=0.0), F.intent(), "equity_krw")]
    for c, i, what in cases:
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and f"state: positions invalid ({what})" in d.reasons, d.reasons


def test_new_exposure_needs_active_owner_and_signed_code():
    held = {("upbit", "BTC"): 1.0}
    for c, reason in ((F.ctx(active=model.ApprovedState.invalid("rules: unapproved")), "state: rules: unapproved"),
                      (F.ctx(owner=model.OwnerState.broken("no owner key yet: owner act 1")),
                       "state: owner log no owner key yet: owner act 1"),
                      (F.ctx(code_signed=False, holdings=held), "unsigned code")):
        d = gate.decide(F.intent(), c)
        assert d.verdict == model.BLOCK and d.kind == "new_exposure" and reason in d.reasons, d.reasons
    sell = gate.decide(F.intent(action="sell"), F.ctx(code_signed=False, holdings=held))
    assert sell.kind == "close_long" and "unsigned code" not in sell.reasons      # exits ignore code_signed


def test_no_usable_state_sends_exits_to_the_app():
    held = {("upbit", "BTC"): 1.0, ("okx", "BTC"): 1.0}
    dead = model.ApprovedState.invalid("owner log broken")
    c = F.ctx(active=dead, holdings=held, owner=_t7_owner())
    sell = gate.decide(F.intent(action="sell"), c)
    assert sell.verdict == model.BLOCK and sell.kind == "close_long"
    assert "close manually in the broker app" in sell.reasons
    w = gate.decide(_t7_withdraw(), c)
    assert w.verdict == model.BLOCK and w.kind == "withdraw" and "withdraw manually in the exchange app" in w.reasons
    for dest in ("okx", "binance"):                                       # step 3: an offshore deposit is no exit
        t = gate.decide(_t7_withdraw(venue="upbit", destination_venue=dest), c)
        assert t.verdict == model.BLOCK and t.kind == "new_exposure", (dest, t.reasons)
        assert "state: owner log broken" in t.reasons and "withdraw manually in the exchange app" not in t.reasons
    over = gate.decide(F.intent(action="sell", quantity=5.0), c)          # holdings come from ctx: still step 1
    assert over.kind == "malformed" and "malformed: quantity" in over.reasons, over.reasons
    snap = F.ctx(active=dead, snapshot=F.approved(), holdings=held, owner=_t7_owner())
    d = gate.decide(F.intent(action="sell"), snap)
    assert d.kind == "close_long" and d.state_hash == F.approved().state_hash, d
    assert "close manually in the broker app" not in d.reasons
    buy = gate.decide(F.intent(), snap)                                   # the snapshot never serves new exposure
    assert buy.verdict == model.BLOCK and "state: owner log broken" in buy.reasons and buy.state_hash == ""
    snap2 = F.approved(seq=2)                                             # a snapshot distinct from the active state
    broken = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=snap2, holdings=held)
    d = gate.decide(F.intent(action="sell"), broken)                      # a broken log means the snapshot (D11)
    assert d.kind == "close_long" and d.state_hash == snap2.state_hash != broken.active.state_hash
    same = F.ctx(owner=model.OwnerState.broken("bad signature"), snapshot=F.approved(), holdings=held)
    t = gate.decide(_t7_withdraw(venue="upbit", destination_venue="okx"), same)   # the snapshot IS ctx.active here
    assert t.kind == "new_exposure" and "state: owner log bad signature" in t.reasons, t.reasons


def test_withdraw_classification():
    held = {("okx", "BTC"): 0.01}
    lightning = ("upbit", "BTC", "lightning", _T7_ADDRESS[3], "")          # registered, but upbit credits bitcoin only
    tagged = ("upbit", "BTC", "bitcoin", _T7_ADDRESS[3], "123")            # registered, but upbit takes no tag
    c = F.ctx(holdings=held, owner=_t7_owner(addresses=frozenset({_T7_ADDRESS, lightning, tagged})))
    w = _t7_withdraw()
    assert gate.decide(w, c).kind == "withdraw"
    for financing in ("credit", "margin"):                                  # D15: an exit is cash-financed
        assert gate.decide(dataclasses.replace(w, financing=financing), c).kind == "new_exposure", financing
    for change in ({"destination_network": "lightning"}, {"destination_address": "bc1qother"},
                   {"destination_tag": "123"}, {"destination_venue": "bithumb"}, {"destination_venue": "binance"}):
        assert gate.decide(dataclasses.replace(w, **change), c).kind == "new_exposure", change
    assert gate.decide(w, F.ctx(holdings=held)).kind == "new_exposure"      # no registered address
    okx_addr = ("okx", "BTC", "bitcoin", "bc1qokx", "")
    into_okx = F.ctx(holdings={("upbit", "BTC"): 1.0}, owner=_t7_owner(addresses=frozenset({okx_addr})))
    t = _t7_withdraw(venue="upbit", destination_venue="okx", destination_address="bc1qokx")
    assert gate.decide(t, into_okx).kind == "new_exposure"               # okx credits it, but is not domestic
    broken = F.ctx(holdings=held, owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=F.approved())
    d = gate.decide(w, broken)
    assert d.kind == "withdraw" and d.verdict == model.BLOCK, d.reasons


def test_history_maps_serve_exits_only():
    """Spec 6.2 steps 0 and 3 on states that rules.approved_state builds from real bytes, as load_context does. A
    coin retired from the map leaves venues.yaml too (parse_venues takes current symbols only), so its sell closes
    the long by its own test (cash, within the free units, for a settlement asset of the venue), not by a listed
    market. An earlier map never serves new exposure, and an exit it cannot classify is sent to the app."""
    old_map, old_venues = F.shipped_bytes("instruments"), F.shipped_bytes("venues")
    usdt = old_map[old_map.index(b"  USDT:\n"):old_map.index(b"  USDC:\n")]
    ibit = old_map[old_map.index(b"  IBIT:"):old_map.index(b"  FBTC:")]
    market = b"markets: [[BTC, KRW], [USDT, KRW]]"
    assert old_map.count(usdt) == old_map.count(ibit) == old_venues.count(market) == 1
    no_usdt, venues = old_map.replace(usdt, b""), old_venues.replace(market, b"markets: [[BTC, KRW]]")
    assert not F.approved(instruments=no_usdt).valid                     # the venue file must drop USDT as well
    kept = F.approved(instruments=no_usdt, venues=venues, history=(old_map,))
    lost = F.approved(instruments=no_usdt, venues=venues)
    assert kept.valid and lost.valid and kept.history_maps and not lost.history_maps, (kept.reason, lost.reason)
    usdt_address = ("upbit", "USDT", "ethereum", "0xfixtureaddress", "")
    held = {("upbit", "USDT"): 100.0, ("okx", "USDT"): 100.0}
    owner = _t8_okx_owner(addresses=frozenset({usdt_address, ("bithumb", *usdt_address[1:])}))
    okx = {"okx": model.Exposure(held_krw=0.0)}
    c = F.ctx(active=kept, holdings=held, owner=owner, exposure=okx)

    def usdt_intent(**changes) -> model.Intent:
        return F.intent(**{"symbol": "USDT", "quantity": 10.0, **changes})

    def withdraw(**changes) -> model.Intent:
        return _t7_withdraw(**{"symbol": "USDT", "quantity": 10.0, "destination_address": usdt_address[3],
                               "destination_network": "ethereum", **changes})

    sell = gate.decide(usdt_intent(action="sell"), c)                    # upbit lists no USDT market any more
    assert sell.verdict == model.ALLOW_EXIT and sell.kind == "close_long" and sell.reasons == (), sell.reasons
    buy = gate.decide(usdt_intent(), c)                                  # new exposure: the map in force only
    assert buy.verdict == model.BLOCK and buy.kind == "malformed" and buy.reasons == ("malformed: symbol",)
    credit = gate.decide(usdt_intent(action="sell", financing="credit"), c)     # not an exit (D15): not found
    assert credit.verdict == model.BLOCK and "malformed: symbol" in credit.reasons, credit.reasons
    for i, manual in (
            (usdt_intent(action="sell", counter_symbol="BTC"), "close manually in the broker app"),   # not settlement
            (usdt_intent(venue="okx", counter_symbol="USDC", action="sell"),       # a settlement asset sold: no exit
             "close manually in the broker app"),
            (withdraw(), "withdraw manually in the exchange app"),               # the deposit facts list no USDT
            (withdraw(venue="upbit", destination_venue="bithumb"), "withdraw manually in the exchange app")):
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == "malformed" and manual in d.reasons, (i, d.reasons)
        assert {"malformed: symbol", "malformed: counter_symbol"} & set(d.reasons), (i, d.reasons)
    offshore = gate.decide(withdraw(venue="upbit", destination_venue="okx"), c)   # no exit: no earlier map
    assert offshore.reasons == ("malformed: symbol",), offshore.reasons
    gone = F.ctx(active=lost, holdings=held, owner=owner, exposure=okx)
    for i, manual in ((usdt_intent(action="sell"), "close manually in the broker app"),
                      (withdraw(), "withdraw manually in the exchange app")):
        d = gate.decide(i, gone)
        assert d.verdict == model.BLOCK and {"malformed: symbol", manual} <= set(d.reasons), d.reasons
    broken = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=kept, holdings=held)
    snap = gate.decide(usdt_intent(action="sell"), broken)               # D11: the snapshot keeps its earlier maps
    assert snap.verdict == model.ALLOW_EXIT and snap.kind == "close_long", snap.reasons
    w = gate.decide(withdraw(), broken)
    assert w.verdict == model.BLOCK and w.reasons == ("withdraw manually in the exchange app",), w.reasons
    # kis quotes by currency and lists no markets, so a retired ticker sells for its currency as before
    no_ibit = F.approved(instruments=old_map.replace(ibit, b""), history=(old_map,))
    assert no_ibit.valid, no_ibit.reason
    held = {("kis", "IBIT"): 2.0}
    sold = gate.decide(_t7_kis("IBIT", action="sell"), F.ctx(active=no_ibit, holdings=held))
    assert sold.verdict == model.ALLOW_EXIT and sold.kind == "close_long" and sold.reasons == (), sold.reasons
    bought = gate.decide(_t7_kis("IBIT"), F.ctx(active=no_ibit, holdings=held))
    assert bought.kind == "malformed" and bought.reasons == ("malformed: symbol",), bought.reasons


def test_reasons_ranked_and_verdicts_combined():
    assert gate._ranked(["ack required: KR-OKX-SPOT", "no row", "state: x", "malformed: venue", "floor: okx p2p_buy",
                         "conduct: spoof", "unsigned code", "no row", "hard_block: KR-PREDICTION"]) == (
        "conduct: spoof", "floor: okx p2p_buy", "malformed: venue", "state: x", "unsigned code", "no row",
        "hard_block: KR-PREDICTION", "ack required: KR-OKX-SPOT")
    A, X, K, B = model.ALLOW, model.ALLOW_EXIT, model.ACK_REQUIRED, model.BLOCK
    for verdicts, want in (([], B), ([A], A), ([X], X), ([A, K], K), ([X, B], B), ([K, B, A], B), (["bogus"], B),
                           ([A, "ALLOW "], B)):
        assert gate._combine(verdicts) == want, verdicts
    d = gate.decide(F.intent(venue="polymarket", asset="event_contract", counter_symbol="USDC",
                             tags=frozenset({"spoof"})), F.ctx())
    assert d.reasons[0].startswith("conduct: ") and d.reasons.index("floor: polymarket") < \
        d.reasons.index("malformed: venue"), d.reasons


def test_internal_errors_become_block():
    for c, i in ((F.ctx(holdings={("upbit", "BTC"): "lots"}), F.intent(action="sell")),
                 (F.ctx(exposure={"upbit": "lots"}), F.intent())):
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == "malformed" and len(d.reasons) == 1, d.reasons
        assert d.reasons[0].startswith("state: internal error ") and d.ctx_hash == c.ctx_hash, d


def test_fuzzed_intents_never_raise():
    rng = random.Random(23)
    junk = (None, [], ["upbit"], {"a": 1}, (), 0, -1, 1.5, 1e308, -1e308, math.nan, math.inf, -math.inf, True, "",
            "UPBIT", 10 ** 30, b"x", object(), frozenset({1}), set(), frozenset({"spoof"}))
    good = {"venue": sorted(rules.VENUES), "symbol": ["BTC", "USDT", "USDC", "005930", "TQQQ", "IBIT", "DOGE"],
            "counter_symbol": ["", "KRW", "USD", "USDT", "BTC"], "asset": sorted(rules.ASSETS),
            "multiple": [1.0, -1.0, 2.0, 3.0, -2.0, 1], "action": sorted(rules.ACTIONS),
            "financing": sorted(rules.FINANCING), "quantity": [0.001, 1.0, 1e308], "notional_krw": [0.0, 5e4, 1e308],
            "destination_venue": [None, "upbit", "okx", "bithumb"], "destination_address": [None, _T7_ADDRESS[3]],
            "destination_network": [None, "bitcoin"], "destination_tag": [None, "7"], "route": ["direct", "vpn"],
            "on_behalf": ["self", "follower"], "publishes_signal": [False, True],
            "tags": [frozenset(), frozenset({"spoof"})], "reservation_id": [None, "R1"]}
    held = {("upbit", "BTC"): 1.0, ("okx", "BTC"): 1.0, ("kis", "IBIT"): 1.0}
    contexts = [F.ctx(holdings=held, shorts={("kis", "005930"): 1.0}, owner=_t7_owner()),
                F.ctx(active=model.ApprovedState.invalid("fixture"), snapshot=F.approved(), holdings=held)]
    for n in range(5000):
        fields = {k: (rng.choice(v) if rng.random() < 0.7 else rng.choice(junk)) for k, v in good.items()}
        c = contexts[n % 2] if n % 50 else rng.choice((None, object(), "ctx"))
        try:
            d = gate.decide(model.Intent(**fields), c)
        except Exception as exc:
            raise AssertionError(f"Random(23) case {n}: decide raised {exc!r} on {fields}") from exc
        assert type(d) is model.Decision and d.verdict in _T7_VERDICTS and (d.verdict != model.BLOCK or d.reasons), \
            (n, fields, d)
    for odd in (None, 5, "intent", vars(F.intent()), [F.intent()]):
        assert gate.decide(odd, contexts[0]).reasons == ("malformed: intent",)


def test_property_conduct_intents_always_block():
    rng = random.Random(23)
    state = F.approved()
    keys = sorted(state.instruments.entries)
    venues_for = {"krx": ["kis"], "us": ["kis"], "crypto": ["upbit", "okx", "bithumb", "coinone", "korbit"]}
    quote = {"kis": None, "upbit": "KRW", "bithumb": "KRW", "coinone": "KRW", "korbit": "KRW", "okx": "USDT"}
    every = {(v, s): 1.0 for v in sorted(rules.VENUES) for _, s in keys}
    c = F.ctx(holdings=every, shorts=every, owner=_t7_owner())
    kinds = set()
    for n in range(2000):
        action = rng.choice(sorted(rules.ACTIONS))
        key = ("crypto", "BTC") if action == "transfer_out" else rng.choice(keys)    # transfers move coins
        inst = state.instruments.entries[key]
        realistic = rng.random() < 0.7
        venue = rng.choice(venues_for[inst.section]) if realistic else rng.choice(sorted(rules.VENUES))
        counter = "" if action in ("transfer_out", "lend", "borrow") else \
            (quote.get(venue) or inst.currency) if realistic else rng.choice(["KRW", "USD", "USDT", "BTC"])
        conduct = rng.choice(("tag", "route", "on_behalf", "signal"))
        fields = dict(venue=venue, symbol=inst.symbol, counter_symbol=counter,
                      asset=inst.asset if realistic else rng.choice(sorted(rules.ASSETS)),
                      multiple=inst.multiple if realistic else rng.choice([1.0, -1.0, 2.0, 3.0]), action=action,
                      financing=rng.choice(sorted(rules.FINANCING)) if rng.random() < 0.2 else "cash",
                      quantity=rng.choice([0.001, 0.5, 1.0]), notional_krw=rng.choice([0.0, 5_000.0, 50_000.0]),
                      tags=frozenset(rng.sample(sorted(rules.TAGS), rng.randint(1, 3))) if conduct == "tag"
                      else frozenset(),
                      route="vpn" if conduct == "route" else "direct",
                      on_behalf="follower" if conduct == "on_behalf" else "self",
                      publishes_signal=conduct == "signal")
        if action == "transfer_out":
            fields.update(destination_venue=rng.choice(["upbit", "upbit", "bithumb", "okx"]),
                          destination_address=_T7_ADDRESS[3], destination_network="bitcoin")
        d = gate.decide(model.Intent(**fields), c)
        assert d.verdict == model.BLOCK and _t7_has(d, "conduct: "), (f"Random(23) case {n}", fields, d.reasons)
        kinds.add(d.kind)
    assert kinds == {"close_long", "cover_short", "withdraw", "new_exposure", "malformed"}, kinds


# --------------------------------------------------------------------------- #
# Task 8: steps 4-6 (spec 6.2 steps 4-6, D6, D11, D16; compliance tests 4, 6, 7). Helpers are prefixed `_t8_`;
# the `_t7_` helpers above are reused, never redefined.
# --------------------------------------------------------------------------- #
import datetime as _t8_dt  # noqa: E402

_T8_DAY = _t8_dt.date
_T8_OKX_ADDRESS = ("okx", "BTC", "bitcoin", "bc1qokxfixtureaddress", "")


def _t8_row(row_id: str, state: model.ApprovedState | None = None) -> rules.Row:
    rows = [r for r in (state or F.approved()).rules.rows if r.id == row_id]
    assert len(rows) == 1, row_id
    return rows[0]


def _t8_with_rows(state: model.ApprovedState, changes: dict) -> model.ApprovedState:
    """`state` with fields of the named rows replaced: {row_id: {field: value}}."""
    assert set(changes) <= {r.id for r in state.rules.rows}, changes
    rows = tuple(dataclasses.replace(r, **changes[r.id]) if r.id in changes else r for r in state.rules.rows)
    return dataclasses.replace(state, rules=dataclasses.replace(state.rules, rows=rows))


def _t8_with_instruments(state: model.ApprovedState, *extra: rules.Instrument) -> model.ApprovedState:
    entries = {**state.instruments.entries, **{(i.section, i.symbol): i for i in extra}}
    return dataclasses.replace(state, instruments=dataclasses.replace(state.instruments, entries=entries))


def _t8_fixture(symbol: str, asset: str, multiple: float, underlying: str | None) -> rules.Instrument:
    """A fixture-only KRX instrument (the shipped map has no single-stock ETP, KRX derivative or ELW)."""
    return rules.Instrument(section="krx", symbol=symbol, asset=asset, multiple=multiple, underlying=underlying,
                            cls=rules.derive_class(asset, multiple, underlying),
                            cost_book="KRX_ETF_line" if asset == "krx_etp" else None, currency="KRW",
                            tax_basis="unsupported", source="fixture: not a real listing")


def _t8_okx_ack(session: str = "S1", cap: str = "10%") -> tuple[str, str, str]:
    """The session ack the owner signs for KR-OKX-SPOT at the fixture cap of 10%."""
    return (session, "KR-OKX-SPOT", gate.warning_sha256(_t8_row("KR-OKX-SPOT"), {"cap": cap}))


def _t8_owner(**changes) -> model.OwnerState:
    """_t7_owner() (cap 10%, age flag, _T7_ADDRESS registered) with any field replaced, addresses included."""
    return dataclasses.replace(_t7_owner(), **changes)


def _t8_okx_owner(**changes) -> model.OwnerState:
    """_t8_owner with the S1 ack of KR-OKX-SPOT signed."""
    return _t8_owner(**{"session_acks": frozenset({_t8_okx_ack()}), **changes})


def _t8_okx_buy(**changes) -> model.Intent:
    """An OKX BTC buy for USDT, KRW 50,000."""
    return F.intent(**{"venue": "okx", "counter_symbol": "USDT", **changes})


def _t8_to_okx(**changes) -> model.Intent:
    """Upbit -> OKX, 0.001 BTC on the bitcoin network, to _T8_OKX_ADDRESS: a new-exposure transfer (step 6)."""
    return F.intent(**{"action": "transfer_out", "counter_symbol": "", "destination_venue": "okx",
                       "destination_address": _T8_OKX_ADDRESS[3], "destination_network": "bitcoin", **changes})


def test_render_warning_fills_only_the_cap_slot():
    row = _t8_row("KR-OKX-SPOT")
    text = gate.render_warning(row, {"cap": "10%"})
    assert "caps everything you hold on OKX at 10% of your equity." in text and "{" not in text, text
    assert gate.render_warning(row, {}) == row.warning.replace("{cap}", "")          # a missing slot renders ""
    assert gate.render_warning(row, {"cap": "10%", "other": "x"}) == text
    assert gate.warning_sha256(row, {"cap": "10%"}) == model.sha256_hex(text)
    assert gate.warning_sha256(row, {"cap": "20%"}) != gate.warning_sha256(row, {"cap": "10%"})
    odd = dataclasses.replace(row, warning="a {bogus} b {{x}} {cap}")
    assert gate.render_warning(odd, {"cap": "5%", "bogus": "B"}) == "a  b {x} 5%"     # only {cap} is a slot
    assert gate.render_warning(dataclasses.replace(row, warning="bad {"), {"cap": "5%"}) == ""
    assert gate.render_warning(_t8_row("KR-DOMESTIC-SPOT"), {"cap": "10%"}) == ""
    assert gate.render_warning(None, {}) == ""                                      # never raises


def test_the_cap_text_keeps_its_digits():
    """{cap} shows the cap the owner signed, so the warning an ack signs says it: 0.5% is not "0%", 12.5% not "12%"."""
    row = _t8_row("KR-OKX-SPOT")
    for cap, text in ((0.1, "10%"), (0.005, "0.5%"), (0.125, "12.5%"), (0.333, "33.3%"), (1, "100%")):
        slots = gate._slots(row, F.ctx(owner=_t8_owner(caps={"okx_equity_share": cap})))
        assert slots == {"cap": text}, (cap, slots)
        assert f"at {text} of your equity." in gate.render_warning(row, slots)


def test_verdicts_follow_the_rows():
    c = F.ctx()
    for symbol in ("005930", "069500", "114800", "SH", "SPY", "AAPL", "BITO"):          # spec 8.4: BITO is ALLOW
        d = gate.decide(_t7_kis(symbol), c)
        assert d.verdict == model.ALLOW and d.kind == "new_exposure" and d.reasons == (), (symbol, d.reasons)
    for symbol in ("IBIT", "FBTC", "ETHA", "GDLC", "EZPZ"):
        d = gate.decide(_t7_kis(symbol), c)
        assert d.verdict == model.BLOCK, symbol
        assert {"floor: etp_crypto_spot", "hard_block: KR-KIS-CRYPTO-SPOT-ETP"} <= set(d.reasons), d.reasons
    for symbol in ("TQQQ", "252670"):
        d = gate.decide(_t7_kis(symbol), c)
        assert d.verdict == model.BLOCK and \
            "needs live broker evidence (execution spec): KR-KIS-ETP-LEV" in d.reasons, (symbol, d.reasons)
    for i in (F.intent(), F.intent(symbol="USDT"), F.intent(venue="bithumb"), F.intent(venue="coinone"),
              F.intent(venue="korbit")):
        d = gate.decide(i, c)
        assert d.verdict == model.ALLOW and d.reasons == (), (i.venue, i.symbol, d.reasons)
    for financing in ("credit", "margin"):                                              # D15
        d = gate.decide(_t7_kis("005930", financing=financing), c)
        assert d.verdict == model.BLOCK and d.reasons == ("out_of_scope: KR-KIS-CREDIT",), d.reasons
    for action in ("lend", "borrow"):                                                   # D15
        d = gate.decide(F.intent(action=action, counter_symbol=""), c)
        assert d.verdict == model.BLOCK and d.reasons == ("out_of_scope: KR-DOMESTIC-LENDING",), d.reasons
    p2p = gate.decide(_t8_okx_buy(action="p2p_buy"), c)
    assert p2p.verdict == model.BLOCK and {"floor: okx p2p_buy", "hard_block: KR-OKX-P2P"} <= set(p2p.reasons)
    for i in (_t7_kis("005930", action="write"), F.intent(action="p2p_buy"), _t7_kis("AAPL", action="sell_short")):
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.reasons == ("no row",), (i.action, d.reasons)
    early = gate.decide(F.intent(), F.ctx(date=_T8_DAY(2026, 6, 23)))     # KR-DOMESTIC-SPOT is in force from 06-24
    assert early.verdict == model.BLOCK and early.reasons == ("no row",), early.reasons


def test_gated_option_needs_owner_flags_then_the_session_ack():
    state = _t7_with_option(F.approved())
    row = _t8_row("KR-KIS-US-OPTION", state)
    need = sorted(row.requires_owner)
    assert need == ["broker_eligibility", "us_option_course_1h", "us_option_mock_3h"] and row.ack == "per_session"
    bare = gate.decide(_t7_option(), F.ctx(active=state))
    assert bare.verdict == model.BLOCK and \
        set(bare.reasons) == {f"requires {item}: KR-KIS-US-OPTION" for item in need}, bare.reasons
    flags = frozenset({"age_of_majority", *need})
    sha = gate.warning_sha256(row, {})                                      # no cap_key, so no slot
    ack = gate.decide(_t7_option(), F.ctx(active=state, owner=_t8_owner(flags=flags)))
    assert ack.verdict == model.ACK_REQUIRED and ack.reasons == ("ack required: KR-KIS-US-OPTION",)
    assert ack.ack == ("KR-KIS-US-OPTION", sha) and ack.warnings == (row.warning,)
    signed = _t8_owner(flags=flags, session_acks=frozenset({("S1", "KR-KIS-US-OPTION", sha)}))
    ok = gate.decide(_t7_option(), F.ctx(active=state, owner=signed))
    assert ok.verdict == model.ALLOW and ok.reasons == () and ok.ack is None, ok.reasons
    write = gate.decide(_t7_option(action="write"), F.ctx(active=state, owner=signed))
    assert write.verdict == model.BLOCK and \
        {"floor: option write", "hard_block: KR-KIS-US-OPTION-WRITE"} <= set(write.reasons), write.reasons


def test_okx_auto_off_at_the_asia_seoul_boundary():
    # Spec 8.7: ctx.date is the Asia/Seoul date of the decision moment, so 23:59:59 KST on 12-02 decides on 12-02
    # and 00:00:00 KST on 12-03 on 12-03. The gate sees only the date; load_context's conversion of a moment into it
    # is Task 13's test_decision_date_is_the_asia_seoul_date_of_now. The shipped KR-OKX-SPOT is due 2026-11-22 and
    # already stale on 12-02, so the boundary is tested on a re-reviewed row: a review on 2026-11-15 may move
    # review_by to 2026-12-02 (P15: within 31 days, before the 2026-12-03 affected_by date).
    row = _t8_row("KR-OKX-SPOT")
    review = dataclasses.replace(row.reviews[-1], date=_T8_DAY(2026, 11, 15))
    state = _t8_with_rows(F.approved(), {"KR-OKX-SPOT": {"review_by": _T8_DAY(2026, 12, 2),
                                                         "reviews": (*row.reviews, review)}})
    before = _t8_dt.datetime(2026, 12, 2, 23, 59, 59, tzinfo=model.KST).date()
    after = _t8_dt.datetime(2026, 12, 3, 0, 0, 0, tzinfo=model.KST).date()
    assert (before, after) == (_T8_DAY(2026, 12, 2), _T8_DAY(2026, 12, 3)), (before, after)
    ok = gate.decide(_t8_okx_buy(), F.ctx(active=state, date=before, owner=_t8_okx_owner()))
    assert ok.verdict == model.ALLOW and ok.reasons == (), ok.reasons
    off = gate.decide(_t8_okx_buy(), F.ctx(active=state, date=after, owner=_t8_okx_owner()))
    assert off.verdict == model.BLOCK and off.reasons == ("stale: review by 2026-12-02 passed (KR-OKX-SPOT)",
                                                          "auto_off 2026-12-03: KR-OKX-SPOT"), off.reasons
    shipped = gate.decide(_t8_okx_buy(), F.ctx(date=before, owner=_t8_okx_owner()))
    assert shipped.verdict == model.BLOCK and \
        shipped.reasons == ("stale: review by 2026-11-22 passed (KR-OKX-SPOT)",), shipped.reasons


def test_rows_are_in_force_from_effective_from_until_effective_until():
    # A gate-only fixture row, neither stale nor off in February: the loader would refuse this review_by (P15: it
    # crosses the 2026-12-03 and 2027-02-18 affected_by dates).
    later = _T8_DAY(2027, 3, 31)
    state = _t8_with_rows(F.approved(), {"KR-OKX-SPOT": {"review_by": later, "auto_off": later}})
    owner = _t8_okx_owner()
    last = gate.decide(_t8_okx_buy(), F.ctx(active=state, date=_T8_DAY(2027, 2, 17), owner=owner))
    assert last.verdict == model.ALLOW, last.reasons
    ended = gate.decide(_t8_okx_buy(), F.ctx(active=state, date=_T8_DAY(2027, 2, 18), owner=owner))
    assert ended.verdict == model.BLOCK and ended.reasons == ("no row",), ended.reasons    # effective_until
    first = _t8_row("KR-OKX-SPOT").effective_from
    assert gate.decide(_t8_okx_buy(), F.ctx(date=first, owner=owner)).verdict == model.ALLOW
    before = gate.decide(_t8_okx_buy(), F.ctx(date=_T8_DAY.fromordinal(first.toordinal() - 1), owner=owner))
    assert before.reasons == ("no row",), before.reasons


def test_okx_sell_for_usdt_is_an_exit_after_auto_off():
    c = F.ctx(date=_T8_DAY(2026, 12, 3), holdings={("okx", "BTC"): 0.01, ("okx", "USDT"): 100.0},
              owner=_t8_okx_owner())
    sell = gate.decide(_t8_okx_buy(action="sell"), c)
    assert sell.verdict == model.ALLOW_EXIT and sell.kind == "close_long" and sell.reasons == (), sell.reasons
    assert "stale: review by 2026-11-22 passed (KR-OKX-SPOT)" in sell.warnings
    assert gate.render_warning(_t8_row("KR-OKX-SPOT"), {"cap": "10%"}) in sell.warnings
    buy = gate.decide(_t8_okx_buy(), c)                                  # USDT -> BTC is a BTC buy: new exposure
    assert buy.verdict == model.BLOCK and buy.kind == "new_exposure"
    assert "auto_off 2026-12-03: KR-OKX-SPOT" in buy.reasons, buy.reasons
    usdt = gate.decide(_t8_okx_buy(symbol="USDT", counter_symbol="BTC", action="sell"), c)   # no USDT-BTC market
    assert usdt.verdict == model.BLOCK and "malformed: counter_symbol" in usdt.reasons, usdt.reasons


def test_withdrawal_to_upbit_ignores_stale_rows_and_unsigned_code():
    on = _T8_DAY(2026, 12, 3)
    assert on > _t8_row("KR-DOMESTIC-SPOT").review_by and on > _t8_row("KR-OKX-WITHDRAW").review_by
    c = F.ctx(date=on, code_signed=False, holdings={("okx", "BTC"): 0.01}, owner=_t8_owner())
    d = gate.decide(_t7_withdraw(), c)
    assert d.verdict == model.ALLOW_EXIT and d.kind == "withdraw" and d.reasons == (), d.reasons
    assert d.warnings == ("stale: review by 2026-11-22 passed (KR-OKX-WITHDRAW)",), d.warnings
    buy = gate.decide(F.intent(), F.ctx(date=on, code_signed=False))
    assert buy.verdict == model.BLOCK and "unsigned code" in buy.reasons     # the same context refuses a buy


def test_withdrawal_wrong_network_or_missing_tag_blocks():
    held = {("okx", "BTC"): 0.01}
    lightning = ("upbit", "BTC", "lightning", _T7_ADDRESS[3], "")
    c = F.ctx(holdings=held, owner=_t8_owner(addresses=frozenset({_T7_ADDRESS, lightning})))
    wrong = gate.decide(_t7_withdraw(destination_network="lightning"), c)
    assert wrong.verdict == model.BLOCK and wrong.kind == "new_exposure", wrong
    assert {"destination: upbit does not credit BTC on lightning", "out_of_scope: KR-OKX-WITHDRAW"} <= \
        set(wrong.reasons), wrong.reasons
    raw = F.shipped_bytes("venues")                                       # fixture venue file: Upbit wants a tag
    head, sep, tail = raw.partition(b"\n  okx:")
    assert sep and head.count(b"tag_required: false") == 1
    tagged = F.approved(venues=head.replace(b"tag_required: false", b"tag_required: true") + sep + tail)
    assert tagged.valid, tagged.reason
    assert tagged.venues.venues["upbit"].deposits == frozenset({("BTC", "bitcoin", True)})
    assert tagged.venues.venues["okx"].deposits == frozenset({("BTC", "bitcoin", False)})
    memo = ("upbit", "BTC", "bitcoin", _T7_ADDRESS[3], "4242")
    c2 = F.ctx(active=tagged, holdings=held, owner=_t8_owner(addresses=frozenset({_T7_ADDRESS, memo})))
    missing = gate.decide(_t7_withdraw(), c2)
    assert missing.verdict == model.BLOCK and missing.kind == "new_exposure"
    assert "destination: upbit needs a tag for BTC on bitcoin" in missing.reasons, missing.reasons
    tag = gate.decide(_t7_withdraw(destination_tag="4242"), c2)
    assert tag.verdict == model.ALLOW_EXIT and tag.kind == "withdraw", tag.reasons
    extra = gate.decide(_t7_withdraw(destination_tag="4242"),
                        F.ctx(holdings=held, owner=_t8_owner(addresses=frozenset({memo}))))
    assert extra.verdict == model.BLOCK and "destination: upbit takes no tag for BTC on bitcoin" in extra.reasons


def test_broken_owner_log_closes_with_the_snapshot_and_withdraws_manually():
    snap = _t8_with_rows(F.approved(seq=2), {"KR-DOMESTIC-SPOT": {"warning": "snapshot-only warning"}})
    c = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=snap,
              holdings={("upbit", "BTC"): 1.0, ("okx", "BTC"): 0.01}, shorts={("kis", "005930"): 3.0})
    for i, kind in ((F.intent(action="sell"), "close_long"), (_t7_kis("005930", action="buy_to_cover"),
                                                              "cover_short")):
        d = gate.decide(i, c)
        assert d.verdict == model.ALLOW_EXIT and d.kind == kind and d.reasons == (), (kind, d.reasons)
        assert d.state_hash == snap.state_hash != c.active.state_hash
        assert "snapshot: decided on the last approved snapshot (D11)" in d.warnings
    upbit = gate.decide(F.intent(action="sell"), c)
    assert "snapshot-only warning" in upbit.warnings, upbit.warnings      # the snapshot's rows, not ctx.active's
    okx = gate.decide(_t8_okx_buy(action="sell"), c)                     # a broken log has no caps to read
    assert okx.verdict == model.ALLOW_EXIT and okx.kind == "close_long", okx.reasons
    assert gate.render_warning(_t8_row("KR-OKX-SPOT"), {"cap": "the share you set"}) in okx.warnings, okx.warnings
    w = gate.decide(_t7_withdraw(), c)
    assert w.verdict == model.BLOCK and w.kind == "withdraw"
    assert w.reasons == ("withdraw manually in the exchange app",), w.reasons
    buy = gate.decide(F.intent(), c)
    assert buy.verdict == model.BLOCK and "state: owner log bad signature on entry 4" in buy.reasons


def test_invalid_active_state_closes_with_the_snapshot():
    held = {("upbit", "BTC"): 1.0, ("okx", "BTC"): 0.01}
    c = F.ctx(active=model.ApprovedState.invalid("rules: unapproved"), snapshot=F.approved(), holdings=held,
              shorts={("kis", "005930"): 3.0}, owner=_t8_owner())
    for i, kind in ((F.intent(action="sell"), "close_long"), (_t7_kis("005930", action="buy_to_cover"),
                                                              "cover_short"), (_t7_withdraw(), "withdraw")):
        d = gate.decide(i, c)
        assert d.verdict == model.ALLOW_EXIT and d.kind == kind and d.reasons == (), (kind, d.reasons)
        assert d.state_hash == F.approved().state_hash
    buy = gate.decide(F.intent(), c)
    assert buy.verdict == model.BLOCK and "state: rules: unapproved" in buy.reasons


def test_no_snapshot_means_manual_exits():
    c = F.ctx(active=model.ApprovedState.invalid("rules: unapproved"), holdings={("upbit", "BTC"): 1.0,
              ("okx", "BTC"): 0.01}, shorts={("kis", "005930"): 3.0}, owner=_t8_owner())
    for i, kind, manual in ((F.intent(action="sell"), "close_long", "close manually in the broker app"),
                            (_t7_kis("005930", action="buy_to_cover"), "cover_short",
                             "close manually in the broker app"),
                            (_t7_withdraw(), "withdraw", "withdraw manually in the exchange app")):
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == kind and d.reasons == ("state: rules: unapproved", manual), \
            (kind, d.reasons)


def test_conduct_still_blocks_exits():
    c = F.ctx(holdings={("upbit", "BTC"): 1.0, ("okx", "BTC"): 0.01}, shorts={("kis", "005930"): 3.0},
              owner=_t8_owner())
    for base in (F.intent(action="sell"), _t7_kis("005930", action="buy_to_cover"), _t7_withdraw()):
        assert gate.decide(base, c).verdict == model.ALLOW_EXIT, base
        for change, reason in (({"tags": frozenset({"spoof"})}, "conduct: KR-CONDUCT-MANIP"),
                               ({"route": "vpn"}, "conduct: KR-CONDUCT-ROUTE"),
                               ({"on_behalf": "follower"}, "conduct: KR-CONDUCT-OTHERS"),
                               ({"publishes_signal": True}, "conduct: KR-CONDUCT-SIGNALS")):
            d = gate.decide(dataclasses.replace(base, **change), c)
            assert d.verdict == model.BLOCK and reason in d.reasons, (base.action, change, d.reasons)


def test_exits_ignore_gates_caps_d16_leverage_and_hard_blocks():
    # D11 / spec 6.2 step 4: unmet owner gates, an unset or exceeded cap, D16 requires.live, max_leverage and
    # hard_block rows never block an exit. The shipped hard_block, D16 and leverage rows match buys only, so this
    # fixture widens three of them to sells (the shipped table has no such rows).
    def sells(row_id: str, **more) -> dict:
        row = _t8_row(row_id)
        return {"match": {**row.match, "action": row.match["action"] | {"sell"}}, **more}

    base = _t7_with_option(_t8_with_instruments(F.approved(), _t8_fixture("ZFUT", "krx_derivative", 1.0, None)))
    state = _t8_with_rows(base, {"KR-KIS-CRYPTO-SPOT-ETP": sells("KR-KIS-CRYPTO-SPOT-ETP"),
                                 "KR-KIS-KRX-DERIV": sells("KR-KIS-KRX-DERIV"),
                                 "KR-KIS-ETP-LEV": sells("KR-KIS-ETP-LEV", max_leverage=1.5)})
    held = {("kis", "ZFUT"): 1.0, ("kis", _T7_OPTION): 1.0, ("kis", "IBIT"): 2.0, ("kis", "TQQQ"): 1.0,
            ("okx", "BTC"): 0.01}
    bare = _t8_owner(flags=frozenset(), caps={})                         # no age flag, no course, no cap
    zfut = F.intent(venue="kis", symbol="ZFUT", counter_symbol="KRW", asset="krx_derivative", multiple=1.0,
                    action="sell", quantity=1.0, notional_krw=30_000.0)
    for i, row_id in ((zfut, "KR-KIS-KRX-DERIV"),                            # D16 requires.live, owner items unmet
                      (_t7_option(action="sell"), "KR-KIS-US-OPTION"),        # gated, owner items unmet
                      (_t7_kis("IBIT", action="sell"), "KR-KIS-CRYPTO-SPOT-ETP"),   # hard_block
                      (_t7_kis("TQQQ", action="sell"), "KR-KIS-ETP-LEV"),           # 3x above max_leverage 1.5
                      (_t8_okx_buy(action="sell"), "KR-OKX-SPOT")):                  # grey: cap unset, age unmet
        inst = state.instruments.lookup(state.venues.venues[i.venue].sections, i.symbol)
        assert row_id in {r.id for r in gate._in_force(state, i, inst.cls, F.ctx().date)}, row_id   # it matches
        d = gate.decide(i, F.ctx(active=state, holdings=held, owner=bare))
        assert d.verdict == model.ALLOW_EXIT and d.kind == "close_long" and d.reasons == (), (row_id, d.reasons)
    over = F.ctx(active=state, holdings=held, owner=_t8_okx_owner(),
                 exposure={"okx": model.Exposure(held_krw=10_000_000.0)})        # ten times the 10% cap
    assert gate.decide(_t8_okx_buy(action="sell"), over).verdict == model.ALLOW_EXIT
    shipped = gate.decide(_t7_kis("IBIT", action="sell"), F.ctx(holdings={("kis", "IBIT"): 2.0}))
    assert shipped.verdict == model.ALLOW_EXIT and shipped.reasons == (), shipped.reasons   # spec 8.3


def test_okx_ack_missing_wrong_or_other_session_is_ack_required():
    sha = _t8_okx_ack()[2]
    cases = {"missing": frozenset(), "wrong hash": frozenset({("S1", "KR-OKX-SPOT", "0" * 64)}),
             "old session": frozenset({_t8_okx_ack(session="S0")}),
             "other row": frozenset({("S1", "KR-DOMESTIC-SPOT", sha)}),
             "other cap text": frozenset({_t8_okx_ack(cap="20%")})}
    for name, acks in cases.items():
        d = gate.decide(_t8_okx_buy(), F.ctx(owner=_t8_owner(session_acks=acks)))
        assert d.verdict == model.ACK_REQUIRED and d.reasons == ("ack required: KR-OKX-SPOT",), (name, d.reasons)
        assert d.ack == ("KR-OKX-SPOT", sha), name
    ok = gate.decide(_t8_okx_buy(), F.ctx(owner=_t8_okx_owner()))
    assert ok.verdict == model.ALLOW and ok.reasons == () and ok.ack is None, ok.reasons
    assert ok.warnings == (gate.render_warning(_t8_row("KR-OKX-SPOT"), {"cap": "10%"}),)
    for session in (model.SessionState(session_id="S2", armed=True), model.SessionState()):
        d = gate.decide(_t8_okx_buy(), F.ctx(owner=_t8_okx_owner(), session=session))
        assert d.verdict == model.ACK_REQUIRED, session


def test_okx_cap_age_and_auto_off_block():
    owner = _t8_okx_owner()
    cases = [(F.ctx(owner=dataclasses.replace(owner, caps={})), "cap unset: KR-OKX-SPOT"),
             (F.ctx(owner=dataclasses.replace(owner, caps={"okx_equity_share": 0.0})), "cap unset: KR-OKX-SPOT"),
             (F.ctx(owner=dataclasses.replace(owner, caps={"okx_equity_share": 1.5})), "cap unset: KR-OKX-SPOT"),
             (F.ctx(owner=dataclasses.replace(owner, caps={"okx_equity_share": "0.1"})), "cap unset: KR-OKX-SPOT"),
             (F.ctx(owner=dataclasses.replace(owner, flags=frozenset())), "requires age_of_majority: KR-OKX-SPOT"),
             # held_krw is the caller's KRW value of everything on OKX, USDT included (P19, contract 5.2)
             (F.ctx(owner=owner, exposure={"okx": model.Exposure(held_krw=60_000.0)}), "cap exceeded: KR-OKX-SPOT"),
             (F.ctx(owner=owner, exposure={"okx": model.Exposure(held_krw=30_000.0, reservations={"R9": 30_000.0})}),
              "cap exceeded: KR-OKX-SPOT"),
             (F.ctx(owner=owner, date=_T8_DAY(2026, 12, 3)), "auto_off 2026-12-03: KR-OKX-SPOT")]
    for c, reason in cases:
        d = gate.decide(_t8_okx_buy(), c)
        assert d.verdict == model.BLOCK and reason in d.reasons and d.ack is None, (reason, d.reasons)
    edge = gate.decide(_t8_okx_buy(), F.ctx(owner=owner, exposure={"okx": model.Exposure(held_krw=50_000.0)}))
    assert edge.verdict == model.ALLOW, edge.reasons                       # exactly at the cap: 100,000 of 1,000,000
    own = gate.decide(_t8_okx_buy(reservation_id="R1"), F.ctx(owner=owner, exposure={
        "okx": model.Exposure(held_krw=50_000.0, reservations={"R1": 50_000.0})}))
    assert own.verdict == model.ALLOW, own.reasons                         # its own reservation is not counted twice
    # Only the intent's own reservation is excluded, and only when it has one: R2 alone pushes 60,000 + 50,000 over
    # the cap; a lone big R1 is its own.
    other = gate.decide(_t8_okx_buy(reservation_id="R1"), F.ctx(owner=owner, exposure={
        "okx": model.Exposure(held_krw=0.0, reservations={"R1": 50_000.0, "R2": 60_000.0})}))
    assert other.verdict == model.BLOCK and "cap exceeded: KR-OKX-SPOT" in other.reasons, other.reasons
    lone = gate.decide(_t8_okx_buy(reservation_id="R1"), F.ctx(owner=owner, exposure={
        "okx": model.Exposure(held_krw=0.0, reservations={"R1": 90_000.0})}))
    assert lone.verdict == model.ALLOW, lone.reasons
    # An intent with no reservation of its own counts every reservation, even one keyed None; such a key (or "" or
    # a non-str) makes the positions invalid, and the cap sum alone refuses it too.
    for key in (None, "", 7):
        exp = {"okx": model.Exposure(held_krw=0.0, reservations={key: 900_000.0})}
        d = gate.decide(_t8_okx_buy(), F.ctx(owner=owner, exposure=exp))
        assert d.verdict == model.BLOCK and "state: positions invalid (exposure)" in d.reasons, (key, d.reasons)
        assert gate._grey(_t8_row("KR-OKX-SPOT"), _t8_okx_buy(), F.ctx(owner=owner, exposure=exp)) == \
            ["cap exceeded: KR-OKX-SPOT"], key


def test_new_exposure_needs_a_stake_and_its_grey_venue_exposure():
    """The caps count caller numbers, so they fail closed: new exposure with notional_krw <= 0 is malformed on every
    row (the review's 1000-BTC OKX buy at notional 0 sat under the cap), and on a grey venue holdings without an
    exposure entry for it are invalid positions. Exits need no stake."""
    held, okx = {("upbit", "BTC"): 1.0}, {"okx": model.Exposure(held_krw=0.0)}
    deposit = _t8_to_okx()
    owner = _t8_okx_owner(addresses=frozenset({_T7_ADDRESS, _T8_OKX_ADDRESS}),
                          transfer_acks=frozenset({(model.intent_hash(i), _t8_okx_ack()[2])
                                                   for i in (deposit, dataclasses.replace(deposit, notional_krw=0.0))}))
    for i, c in ((_t8_okx_buy(quantity=1000.0, notional_krw=0.0), F.ctx(owner=owner, exposure=okx)),
                 (F.intent(notional_krw=0.0), F.ctx()), (_t7_kis("005930", notional_krw=0.0), F.ctx()),
                 (dataclasses.replace(deposit, notional_krw=0.0), F.ctx(owner=owner, holdings=held, exposure=okx)),
                 (F.intent(notional_krw=0.0), F.ctx(active=model.ApprovedState.invalid("rules: unapproved")))):
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and d.kind == "malformed" and "malformed: notional_krw" in d.reasons, \
            (i, d.reasons)
    stake = gate.screen(_t9_plan("kis", "005930", F.ctx().date, 5), F.ctx(), 0.0)
    assert not stake.allowed and "malformed: notional_krw" in stake.decision.reasons, stake.decision.reasons
    sell = gate.decide(F.intent(action="sell", notional_krw=0.0), F.ctx(holdings=held))
    assert sell.verdict == model.ALLOW_EXIT and sell.kind == "close_long", sell.reasons
    on_okx = {("okx", "BTC"): 0.5, **held}                               # held on OKX, but no OKX exposure given
    for i in (_t8_okx_buy(), deposit):
        d = gate.decide(i, F.ctx(owner=owner, holdings=on_okx))
        assert d.verdict == model.BLOCK and "state: positions invalid (exposure)" in d.reasons, (i, d.reasons)
        given = F.ctx(owner=owner, holdings=on_okx, exposure={"okx": model.Exposure(held_krw=40_000.0)})
        assert gate.decide(i, given).verdict == model.ALLOW, (i, gate.decide(i, given).reasons)
    assert gate.decide(_t8_okx_buy(), F.ctx(owner=owner, holdings=held)).verdict == model.ALLOW   # nothing on OKX


def test_stale_row_blocks_new_exposure_but_not_exits():
    assert gate.decide(F.intent(), F.ctx(date=_T8_DAY(2026, 11, 22))).verdict == model.ALLOW
    late = gate.decide(F.intent(), F.ctx(date=_T8_DAY(2026, 11, 23)))
    assert late.verdict == model.BLOCK and \
        late.reasons == ("stale: review by 2026-11-22 passed (KR-DOMESTIC-SPOT)",), late.reasons
    assert gate.decide(_t7_kis("005930"), F.ctx(date=_T8_DAY(2026, 11, 23))).verdict == model.ALLOW
    kis = gate.decide(_t7_kis("005930"), F.ctx(date=_T8_DAY(2026, 11, 24)))
    assert kis.reasons == ("stale: review by 2026-11-23 passed (KR-KIS-KRX-SHARE)",), kis.reasons
    sell = gate.decide(F.intent(action="sell"), F.ctx(date=_T8_DAY(2026, 11, 23), holdings={("upbit", "BTC"): 1.0}))
    assert sell.verdict == model.ALLOW_EXIT and sell.reasons == ()
    assert sell.warnings == ("stale: review by 2026-11-22 passed (KR-DOMESTIC-SPOT)",), sell.warnings


def test_d16_rows_stay_blocked_with_every_owner_flag_signed():
    state = _t8_with_instruments(F.approved(), _t8_fixture("ZSINGLE", "krx_etp", -1.0, "single"),
                                 _t8_fixture("ZFUT", "krx_derivative", 1.0, None),
                                 _t8_fixture("ZELW", "elw", 1.0, None))
    d16 = sorted(r.id for r in state.rules.rows if r.policy_ref == "D16")
    assert d16 == ["KR-KIS-ELW", "KR-KIS-ETP-LEV", "KR-KIS-KRX-DERIV", "KR-KIS-SHORT", "KR-KIS-SINGLE-ETP"], d16
    assert state.instruments.entries[("krx", "ZSINGLE")].cls == "etp_single_stock"      # spec 8.4: single-stock -1x

    def kis(symbol: str, **changes) -> model.Intent:
        inst = state.instruments.entries[("krx", symbol)]
        return F.intent(**{"venue": "kis", "symbol": symbol, "counter_symbol": "KRW", "asset": inst.asset,
                           "multiple": inst.multiple, "quantity": 1.0, "notional_krw": 30_000.0, **changes})
    every = F.ctx(active=state, owner=_t8_owner(flags=frozenset(rules.OWNER_REQUIREMENTS)))
    for row_id, i in (("KR-KIS-SHORT", kis("005930", action="sell_short")), ("KR-KIS-ETP-LEV", kis("252670")),
                      ("KR-KIS-SINGLE-ETP", kis("ZSINGLE")), ("KR-KIS-KRX-DERIV", kis("ZFUT")),
                      ("KR-KIS-ELW", kis("ZELW"))):
        d = gate.decide(i, every)
        assert d.verdict == model.BLOCK and d.kind == "new_exposure", (row_id, d.reasons)
        assert d.reasons == (f"needs live broker evidence (execution spec): {row_id}",), (row_id, d.reasons)


def test_leverage_above_max_leverage_blocks():
    lev = _t8_row("KR-KIS-ETP-LEV")
    assert lev.max_leverage == 3.0
    loose = _t8_with_rows(F.approved(), {"KR-KIS-ETP-LEV": {"treatment": "allow", "requires_owner": (),
                                                             "requires_live": (), "policy_ref": None,
                                                             "max_leverage": 2.0}})
    c = F.ctx(active=loose)
    assert gate.decide(_t7_kis("252670"), c).verdict == model.ALLOW            # -2x: |multiple| == max_leverage
    three = gate.decide(_t7_kis("TQQQ"), c)
    assert three.verdict == model.BLOCK and three.reasons == ("leverage 3 above 2: KR-KIS-ETP-LEV",), three.reasons
    inverse = gate.decide(_t7_kis("252670"), F.ctx(active=_t8_with_rows(loose, {"KR-KIS-ETP-LEV": {
        "max_leverage": 1.5}})))
    assert inverse.verdict == model.BLOCK and \
        inverse.reasons == ("leverage 2 above 1.5: KR-KIS-ETP-LEV",), inverse.reasons   # P4: |-2| = 2 > 1.5
    shipped = gate.decide(_t7_kis("TQQQ"), F.ctx())
    assert not _t7_has(shipped, "leverage "), shipped.reasons                  # 3x is within the shipped 3.0


def test_upbit_to_okx_transfer_needs_the_transfer_ack_and_a_registered_address():
    i = _t8_to_okx()
    sha = _t8_okx_ack()[2]
    full = _t8_okx_owner(addresses=frozenset({_T7_ADDRESS, _T8_OKX_ADDRESS}),
                         transfer_acks=frozenset({(model.intent_hash(i), sha)}))
    held = {("upbit", "BTC"): 0.01}
    ok = gate.decide(i, F.ctx(holdings=held, owner=full))
    assert ok.verdict == model.ALLOW and ok.kind == "new_exposure" and ok.reasons == (), ok.reasons
    assert ok.warnings == (gate.render_warning(_t8_row("KR-OKX-SPOT"), {"cap": "10%"}),)
    no_ack = F.ctx(holdings=held, owner=dataclasses.replace(full, transfer_acks=frozenset()))
    d = gate.decide(i, no_ack)
    assert d.verdict == model.ACK_REQUIRED and d.reasons == ("ack required: KR-OKX-SPOT per transfer",), d.reasons
    assert d.ack == ("KR-OKX-SPOT", sha)
    other = gate.decide(dataclasses.replace(i, quantity=0.002), F.ctx(holdings=held, owner=full))
    assert other.verdict == model.ACK_REQUIRED, other.reasons            # the ack names one intent hash
    for old_sha in ("0" * 64, _t8_okx_ack(cap="20%")[2]):                 # signed on other or older warning text
        signed = dataclasses.replace(full, transfer_acks=frozenset({(model.intent_hash(i), old_sha)}))
        d = gate.decide(i, F.ctx(holdings=held, owner=signed))
        assert d.verdict == model.ACK_REQUIRED and d.reasons == ("ack required: KR-OKX-SPOT per transfer",), \
            d.reasons
    plain = _t8_with_rows(F.approved(), {"KR-TRANSFER-OUT": {"ack": None}})   # the source row's field is informational
    d = gate.decide(i, F.ctx(active=plain, holdings=held, owner=dataclasses.replace(full, transfer_acks=frozenset())))
    assert d.verdict == model.ACK_REQUIRED and d.reasons == ("ack required: KR-OKX-SPOT per transfer",), d.reasons
    session = gate.decide(i, F.ctx(holdings=held, owner=dataclasses.replace(full, session_acks=frozenset())))
    assert session.verdict == model.ACK_REQUIRED and session.reasons == ("ack required: KR-OKX-SPOT",), \
        session.reasons                                                   # the destination is decided as a buy
    neither = gate.decide(i, F.ctx(holdings=held, owner=dataclasses.replace(
        full, session_acks=frozenset(), transfer_acks=frozenset())))
    assert neither.verdict == model.ACK_REQUIRED and set(neither.reasons) == {
        "ack required: KR-OKX-SPOT", "ack required: KR-OKX-SPOT per transfer"}, neither.reasons
    cases = [(F.ctx(holdings=held, owner=dataclasses.replace(full, addresses=frozenset({_T7_ADDRESS}))),
              "destination: address not registered"),
             (F.ctx(holdings=held, owner=full, exposure={"okx": model.Exposure(held_krw=60_000.0)}),
              "cap exceeded: KR-OKX-SPOT"),                                 # a deposit counts toward the OKX cap
             (F.ctx(holdings=held, owner=full, exposure={"okx": model.Exposure(held_krw=-1.0)}),
              "state: positions invalid (exposure)"),
             (F.ctx(holdings=held, owner=full, date=_T8_DAY(2026, 12, 3)), "auto_off 2026-12-03: KR-OKX-SPOT")]
    for c, reason in cases:
        d = gate.decide(i, c)
        assert d.verdict == model.BLOCK and reason in d.reasons, (reason, d.reasons)
    lightning = gate.decide(_t8_to_okx(destination_network="lightning"), F.ctx(holdings=held, owner=full))
    assert lightning.verdict == model.BLOCK and \
        "destination: okx does not credit BTC on lightning" in lightning.reasons, lightning.reasons
    binance = gate.decide(_t8_to_okx(destination_venue="binance"), F.ctx(holdings=held, owner=full))
    assert binance.verdict == model.BLOCK and \
        "destination: binance has no approved venue facts" in binance.reasons, binance.reasons
    clash = rules.Instrument(section="us", symbol="BTC", asset="us_etp", multiple=1.0, underlying="crypto_spot",
                             cls="etp_crypto_spot", cost_book="US_shares_KIS", currency="USD",
                             tax_basis="unsupported", source="fixture: a US ticker spelled BTC")
    kis = gate.decide(_t8_to_okx(destination_venue="kis"),
                      F.ctx(active=_t8_with_instruments(F.approved(), clash), holdings=held, owner=full))
    assert kis.verdict == model.BLOCK and {"floor: etp_crypto_spot", "hard_block: KR-KIS-CRYPTO-SPOT-ETP",
                                           "destination: kis does not credit BTC on bitcoin"} <= set(kis.reasons), \
        kis.reasons                                                       # decided as a buy there, floor included
    raw = F.shipped_bytes("venues")                                       # fixture venue file: OKX wants a tag
    head, sep, tail = raw.partition(b"\n  okx:")
    assert sep and tail.count(b"tag_required: false") == 1
    tagged = F.approved(venues=head + sep + tail.replace(b"tag_required: false", b"tag_required: true"))
    assert tagged.valid and tagged.venues.venues["okx"].deposits == frozenset({("BTC", "bitcoin", True)})
    memo = (*_T8_OKX_ADDRESS[:4], "1111")
    for tag, want in (("1111", ()), ("2222", ("destination: address not registered",))):   # the tag is in the key
        j = _t8_to_okx(destination_tag=tag)
        owner = dataclasses.replace(full, addresses=frozenset({_T7_ADDRESS, _T8_OKX_ADDRESS, memo}),
                                    transfer_acks=frozenset({(model.intent_hash(j), sha)}))
        d = gate.decide(j, F.ctx(active=tagged, holdings=held, owner=owner))
        assert d.verdict == (model.BLOCK if want else model.ALLOW) and d.reasons == want, (tag, d.reasons)


def test_valid_intents_never_hit_an_internal_error():
    state = _t7_with_option(F.approved())
    every = {(v, s): 1.0 for v in state.venues.venues for (_, s) in state.instruments.entries}
    owner = _t8_okx_owner(flags=frozenset(rules.OWNER_REQUIREMENTS),
                          addresses=frozenset({_T7_ADDRESS, _T8_OKX_ADDRESS}))
    verdicts, count = set(), 0
    for on in (_T8_DAY(2026, 10, 23), _T8_DAY(2026, 12, 3), _T8_DAY(2027, 2, 18)):
        c = F.ctx(active=state, date=on, owner=owner, holdings=every, shorts=every,
                  exposure={"okx": model.Exposure(held_krw=20_000.0, reservations={"R2": 5_000.0})})
        for venue in state.venues.venues.values():
            for (section, symbol), inst in sorted(state.instruments.entries.items()):
                if section not in venue.sections:
                    continue
                for action in sorted(rules.ACTIONS):
                    for financing in ("cash", "credit"):
                        fields = dict(venue=venue.id, symbol=symbol, asset=inst.asset, multiple=inst.multiple,
                                      action=action, financing=financing, quantity=0.5, notional_krw=10_000.0,
                                      counter_symbol="" if action in ("transfer_out", "lend", "borrow")
                                      else venue.quote_for(inst))
                        targets = ("upbit", "okx", "bithumb") if action == "transfer_out" else (None,)
                        for dest in targets:
                            if dest == venue.id:
                                continue
                            extra = {} if dest is None else dict(destination_venue=dest,
                                                                 destination_address=_T7_ADDRESS[3],
                                                                 destination_network="bitcoin")
                            d = gate.decide(model.Intent(**fields, **extra), c)
                            count += 1
                            verdicts.add(d.verdict)
                            assert not _t7_has(d, "state: internal error"), (fields, extra, d.reasons)
    assert count > 1000 and verdicts == {model.ALLOW, model.ALLOW_EXIT, model.ACK_REQUIRED, model.BLOCK}, \
        (count, verdicts)


# --------------------------------------------------------------------------- #
# Task 9: permits, verify_permit, screen and purity (spec 6.3; compliance test 8; P3). Helpers are prefixed `_t9_`;
# the `_t7_` and `_t8_` helpers above are reused, never redefined.
# --------------------------------------------------------------------------- #
import ast as _t9_ast  # noqa: E402
import builtins as _t9_builtins  # noqa: E402
import inspect as _t9_inspect  # noqa: E402
import io as _t9_io  # noqa: E402
import os as _t9_os  # noqa: E402
import pathlib as _t9_pathlib  # noqa: E402
import socket as _t9_socket  # noqa: E402
import time as _t9_time  # noqa: E402
import types as _t9_types  # noqa: E402

_T9_FORBIDDEN = frozenset({"now", "utcnow", "today", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter",
                           "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "clock_gettime",
                           "localtime", "gmtime", "ctime", "sleep", "fromtimestamp", "ZoneInfo", "zoneinfo", "open",
                           "read_bytes", "read_text", "write_bytes", "write_text", "scandir", "listdir", "urandom",
                           "system", "urlopen", "socket", "connect", "environ", "getenv"})


def _t9_plan(venue, symbol, start, horizon_days):
    """A duck-typed plan (P3): screen() reads only leg.venue, leg.symbol, start and horizon_days."""
    return _t9_types.SimpleNamespace(leg=_t9_types.SimpleNamespace(venue=venue, symbol=symbol), start=start,
                                     horizon_days=horizon_days)


def _t9_okx_ctx(reservations: dict | None = None, **changes) -> model.Context:
    """OKX with the S1 ack signed and nothing held: the cap is 10% of KRW 1,000,000 = KRW 100,000."""
    exposure = {"okx": model.Exposure(held_krw=0.0, reservations=reservations or {})}
    return F.ctx(**{"owner": _t8_okx_owner(), "exposure": exposure, **changes})


def _t9_names(node) -> set[str]:
    """Every Name, attribute name and imported module or name under `node`."""
    out = set()
    for n in _t9_ast.walk(node):
        if isinstance(n, _t9_ast.Name):
            out.add(n.id)
        elif isinstance(n, _t9_ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, (_t9_ast.Import, _t9_ast.ImportFrom)):
            out.update(part for a in n.names for part in a.name.split("."))
            out.update((getattr(n, "module", None) or "").split("."))
    return out - {""}


def _t9_scan(source: str, seeds=None) -> dict[str, set[str]]:
    """{def name: forbidden names} for the module-level defs of `source` that `seeds` reach through the module's own
    names; every def when `seeds` is None. The runtime traps patch module attributes, so only this scan sees an
    aliased clock import (`from time import time as _now`) inside a def."""
    defs = {n.name: n for n in _t9_ast.parse(source).body if isinstance(n, (_t9_ast.FunctionDef, _t9_ast.ClassDef))}
    todo, seen = (set(defs) if seeds is None else set(seeds) & set(defs)), set()
    while todo:
        name = todo.pop()
        seen.add(name)
        todo |= (_t9_names(defs[name]) & set(defs)) - seen
    return {name: _t9_names(defs[name]) & _T9_FORBIDDEN for name in sorted(seen)}


class _T9Trap:
    """Stands in for a file, clock, zone or socket name: every use is recorded, then raises."""

    def __init__(self, name: str, calls: list) -> None:
        self._name, self._calls = name, calls

    def __call__(self, *args, **kwargs):
        self._calls.append(self._name)
        raise AssertionError(f"the gate touched {self._name}")

    def __getattr__(self, attr: str):
        self._calls.append(f"{self._name}.{attr}")
        raise AssertionError(f"the gate touched {self._name}.{attr}")


def test_permit_only_for_allow_and_allow_exit():
    c = F.ctx(holdings={("upbit", "BTC"): 1.0})
    i = F.intent(reservation_id="R1")
    d, p = gate.decide(i, c), gate.permit(i, c)
    assert d.verdict == model.ALLOW and type(p) is model.Permit
    assert (p.decision_id, p.intent_hash, p.state_hash) == (d.decision_id, d.intent_hash, d.state_hash)
    assert (p.state_seq, p.session_id, p.reservation_id, p.date) == (3, "S1", "R1", c.date)
    assert gate.verify_permit(p, i, c) == (True, "ok")
    sell = F.intent(action="sell")
    assert gate.decide(sell, c).verdict == model.ALLOW_EXIT and gate.permit(sell, c) is not None
    assert gate.decide(_t8_okx_buy(), c).verdict == model.ACK_REQUIRED and gate.permit(_t8_okx_buy(), c) is None
    assert gate.permit(F.intent(venue="polymarket", counter_symbol="USDC"), c) is None
    for intent, context in ((None, c), ("intent", c), (F.intent(), None), (F.intent(), "ctx")):
        assert gate.permit(intent, context) is None
    snap = F.approved(seq=2)                               # a snapshot exit is permitted on the snapshot (D11)
    broken = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=snap,
                   holdings={("upbit", "BTC"): 1.0})
    ps = gate.permit(sell, broken)
    assert ps is not None and (ps.state_seq, ps.state_hash) == (2, snap.state_hash)
    assert gate.verify_permit(ps, sell, broken) == (True, "ok")


def test_verify_permit_excludes_only_its_own_reservation():
    a = _t8_okx_buy(reservation_id="R1", notional_krw=60_000.0)
    p = gate.permit(a, _t9_okx_ctx({"R1": 60_000.0}))
    assert p is not None
    assert gate.verify_permit(p, a, _t9_okx_ctx({"R1": 60_000.0})) == (True, "ok")      # not counted twice
    assert gate.verify_permit(p, a, _t9_okx_ctx({"R1": 60_000.0, "R2": 40_000.0})) == (True, "ok")   # at the cap
    assert gate.verify_permit(p, a, _t9_okx_ctx({"R1": 60_000.0, "R2": 40_001.0})) == \
        (False, "permit: decision now BLOCK (cap exceeded: KR-OKX-SPOT)")


def test_verify_permit_counts_only_other_permits_promised_units():
    held = {("upbit", "BTC"): 1.0}

    def promised(units: float) -> model.Context:           # units promised to unexpired sell permits
        return F.ctx(holdings=held, exposure={"upbit": model.Exposure(held_krw=0.0,
                                                                      promised_sell_units={"BTC": units})})

    sell = F.intent(action="sell", quantity=0.6, reservation_id="SELL-1")
    p = gate.permit(sell, promised(0.4))                   # 0.4 promised to other permits: 0.6 is free
    assert p is not None and gate.decide(sell, promised(0.4)).kind == "close_long"
    assert gate.verify_permit(p, sell, promised(0.4)) == (True, "ok")       # the caller leaves its own 0.6 out
    for others in (0.5, 1.0):                              # 0.5 + 0.6 > 1.0; 1.0 = 0.4 + its own 0.6 counted in
        assert gate.verify_permit(p, sell, promised(others)) == \
            (False, "permit: decision now BLOCK (malformed: quantity)"), others


def test_two_permits_cannot_share_cap_capacity():
    a = _t8_okx_buy(reservation_id="R1", notional_krw=60_000.0)
    b = _t8_okx_buy(reservation_id="R2", notional_krw=60_000.0)
    pa, pb = gate.permit(a, _t9_okx_ctx()), gate.permit(b, _t9_okx_ctx())        # each fits alone
    assert pa is not None and pb is not None
    both = _t9_okx_ctx({"R1": 60_000.0, "R2": 60_000.0})                       # both reserved at send time
    for p, i in ((pa, a), (pb, b)):
        assert gate.verify_permit(p, i, both) == (False, "permit: decision now BLOCK (cap exceeded: KR-OKX-SPOT)")
    one = _t9_okx_ctx({"R1": 60_000.0})
    assert gate.verify_permit(pa, a, one) == (True, "ok")
    assert gate.permit(b, one) is None                                         # R1 holds the capacity b needs


def test_forged_or_mismatched_permits_are_refused():
    i, c = F.intent(reservation_id="R1"), F.ctx()
    p = gate.permit(i, c)
    assert gate.verify_permit(p, i, c) == (True, "ok")
    fields = {f.name: getattr(p, f.name) for f in dataclasses.fields(model.Permit)}
    for forged in (model.Permit(**fields), dataclasses.replace(p), dataclasses.replace(p, state_seq=-1), None,
                   fields, "permit"):
        assert gate.verify_permit(forged, i, c) == (False, "permit: not issued by permit()"), forged
    hand = model.Context(**{f.name: getattr(c, f.name) for f in dataclasses.fields(model.Context)})
    for other, ctx_now, why in (
            (F.intent(reservation_id="R2"), c, "permit: intent differs"),      # the hash covers the reservation
            (F.intent(quantity=0.002, reservation_id="R1"), c, "permit: intent differs"),
            (None, c, "permit: intent differs"),
            (i, F.ctx(session=model.SessionState(session_id="S2", armed=True)), "permit: session differs"),
            (i, F.ctx(session=model.SessionState()), "permit: session differs"),
            (i, F.ctx(date=_T8_DAY(2026, 10, 24)), "permit: date differs"),
            (i, F.ctx(code_signed=False), "permit: decision now BLOCK (unsigned code)"),
            (i, hand, "permit: decision now BLOCK (state: context not from load_context)"),
            (i, None, "permit: decision now BLOCK (state: context not from load_context)")):
        assert gate.verify_permit(p, other, ctx_now) == (False, why), why
    okx = gate.permit(_t8_okx_buy(), F.ctx(owner=_t8_okx_owner()))          # issued while the ack was held
    assert okx is not None and gate.verify_permit(okx, _t8_okx_buy(), F.ctx()) == \
        (False, "permit: decision now ACK_REQUIRED (ack required: KR-OKX-SPOT)")


def test_newer_state_accepted_older_refused():
    i = F.intent()
    p = gate.permit(i, F.ctx())
    assert p.state_seq == 3
    newer = F.ctx(active=F.approved(seq=4))
    assert newer.active.state_hash != p.state_hash and gate.verify_permit(p, i, newer) == (True, "ok")
    same_seq = dataclasses.replace(F.approved(), hashes={**F.approved().hashes, "rules": "0" * 64})
    for older in (F.approved(seq=2), same_seq):
        assert gate.verify_permit(p, i, F.ctx(active=older)) == (False, "permit: state differs"), older.seq
    sell, held = F.intent(action="sell"), {("upbit", "BTC"): 1.0}       # a snapshot exit: the snapshot's seq counts
    dead = model.ApprovedState.invalid("rules: unapproved")
    ps = gate.permit(sell, F.ctx(active=dead, snapshot=F.approved(seq=2), holdings=held))
    assert ps.state_seq == 2
    assert gate.verify_permit(ps, sell, F.ctx(active=dead, snapshot=F.approved(seq=4), holdings=held)) == (True, "ok")
    assert gate.verify_permit(ps, sell, F.ctx(active=dead, snapshot=F.approved(seq=1), holdings=held)) == \
        (False, "permit: state differs")


def test_screen_flags_rule_dates_inside_the_horizon():
    day = _T8_DAY

    def at(venue, symbol, start, horizon_days, stake=50_000.0):     # screened on its own start date
        return gate.screen(_t9_plan(venue, symbol, start, horizon_days), F.ctx(date=start), stake)

    okx = at("okx", "BTC", day(2026, 11, 1), 40)
    assert okx.flags == ((day(2026, 11, 22), "review_by", "KR-OKX-SPOT"),
                         (day(2026, 12, 3), "auto_off", "KR-OKX-SPOT")), okx.flags
    assert okx.allowed and okx.exit_date == day(2026, 11, 22)
    edge = at("okx", "BTC", day(2026, 11, 22), 11)                                       # [11-22, 12-03)
    assert edge.flags == ((day(2026, 11, 22), "review_by", "KR-OKX-SPOT"),), edge.flags
    assert edge.allowed                                                       # review_by is the last good day
    stale = at("okx", "BTC", day(2026, 11, 23), 10)                                      # [11-23, 12-03)
    assert stale.flags == () and stale.exit_date is None
    assert not stale.allowed and "stale: review by 2026-11-22 passed (KR-OKX-SPOT)" in stale.decision.reasons
    until = at("okx", "BTC", day(2027, 2, 10), 10)
    assert until.flags == ((day(2027, 2, 18), "effective_until", "KR-OKX-SPOT"),), until.flags
    assert not until.allowed and until.exit_date == day(2027, 2, 18)
    for start in (day(2026, 10, 22), day(2026, 11, 23), day(2027, 2, 10)):              # not on the context's date
        s = gate.screen(_t9_plan("okx", "BTC", start, 10), F.ctx(), 50_000.0)
        assert not s.allowed and s.decision.reasons == ("malformed: plan start",) and s.flags == (), start
    krx = at("kis", "005930", day(2026, 11, 1), 30, 40_000.0)
    assert krx.flags == ((day(2026, 11, 23), "review_by", "KR-KIS-KRX-SHARE"),), krx.flags
    shorter = at("okx", "BTC", day(2026, 11, 23), 9)
    assert shorter.flags == () and shorter.screening_hash != stale.screening_hash     # the window is hashed


def test_screen_verdicts():
    c, start = F.ctx(), _T8_DAY(2026, 10, 23)                    # a plan starts on its context's date
    krx = gate.screen(_t9_plan("kis", "005930", start, 5), c, 40_000.0)
    assert krx.allowed and krx.decision.verdict == model.ALLOW and krx.flags == () and krx.exit_date is None
    leg = model.Intent(venue="kis", symbol="005930", counter_symbol="KRW", asset="krx_share", multiple=1.0,
                       action="buy", quantity=1.0, notional_krw=40_000.0)
    assert krx.decision.intent_hash == model.intent_hash(leg)                          # a cash buy at the stake
    assert len(krx.screening_hash) == 64
    assert gate.screen(_t9_plan("kis", "005930", start, 5), c, 40_000.0).screening_hash == krx.screening_hash
    assert gate.screen(_t9_plan("kis", "005930", start, 5), c, 40_001.0).screening_hash != krx.screening_hash
    okx = gate.screen(_t9_plan("okx", "BTC", start, 5), c, 40_000.0)
    assert okx.allowed and okx.decision.verdict == model.ACK_REQUIRED and okx.decision.ack[0] == "KR-OKX-SPOT"
    acked = gate.screen(_t9_plan("okx", "BTC", start, 5), F.ctx(owner=_t8_okx_owner()), 40_000.0)
    assert acked.allowed and acked.decision.verdict == model.ALLOW
    over = gate.screen(_t9_plan("okx", "BTC", start, 5), F.ctx(owner=_t8_okx_owner()), 150_000.0)
    assert not over.allowed and "cap exceeded: KR-OKX-SPOT" in over.decision.reasons
    ibit = gate.screen(_t9_plan("kis", "IBIT", start, 5), c, 40_000.0)
    assert not ibit.allowed and "floor: etp_crypto_spot" in ibit.decision.reasons
    for bad in (_t9_plan("kis", "005930", "2026-10-23", 5), _t9_plan("kis", "005930", _t8_dt.datetime(2026, 10, 23), 5),
                _t9_plan("kis", "005930", start, 0), _t9_plan("kis", "005930", start, True),
                _t9_plan("kis", "005930", start, 5.0), _t9_types.SimpleNamespace(), None):
        s = gate.screen(bad, c, 40_000.0)
        assert not s.allowed and s.decision.reasons == ("malformed: plan",) and s.flags == (), bad
    nope = gate.screen(_t9_plan("kis", "NOPE", start, 5), c, 40_000.0)
    assert not nope.allowed and "malformed: symbol" in nope.decision.reasons
    stake = gate.screen(_t9_plan("kis", "005930", start, 5), c, math.nan)
    assert not stake.allowed and "malformed: notional_krw" in stake.decision.reasons
    long = gate.screen(_t9_plan("kis", "005930", start, 40), c, 40_000.0)              # [10-23, 12-02)
    assert long.flags == ((_T8_DAY(2026, 11, 23), "review_by", "KR-KIS-KRX-SHARE"),), long.flags
    for no_state, why in ((F.ctx(active=model.ApprovedState.invalid("rules: unapproved")), "state: rules: unapproved"),
                          (F.ctx(owner=model.OwnerState.broken("bad signature on entry 4")),
                           "state: owner log bad signature on entry 4")):
        s = gate.screen(_t9_plan("kis", "005930", start, 40), no_state, 40_000.0)
        assert not s.allowed and s.decision.reasons == (why,), s.decision.reasons
        assert s.decision.kind == "new_exposure" and s.flags == () and s.exit_date is None
    okx_plan = _t9_plan("okx", "BTC", _T8_DAY(2026, 11, 1), 40)                        # holds 11-22 and 12-03
    hand = model.Context(**{**{f.name: getattr(c, f.name) for f in dataclasses.fields(model.Context)},
                            "date": _T8_DAY(2026, 11, 1)})
    for unsealed in (None, hand):
        for plan in (_t9_plan("kis", "005930", start, 5), okx_plan):
            s = gate.screen(plan, unsealed, 40_000.0)
            assert not s.allowed and s.decision.reasons == ("state: context not from load_context",)
            assert s.flags == () and s.exit_date is None


def test_purity_no_file_clock_zone_or_network():
    rng = random.Random(9)
    held = {("upbit", "BTC"): 1.0, ("okx", "BTC"): 0.01, ("kis", "IBIT"): 2.0}
    okx = {"okx": model.Exposure(held_krw=1_000.0)}                     # a grey venue's holdings need their value
    contexts = [F.ctx(holdings=held, shorts={("kis", "005930"): 3.0}, exposure=okx,
                      owner=_t8_okx_owner(addresses=frozenset({_T7_ADDRESS, _T8_OKX_ADDRESS}))),
                F.ctx(holdings=held, exposure=okx),
                F.ctx(active=_t7_with_option(F.approved()), date=_T8_DAY(2026, 12, 3), holdings=held,
                      owner=_t8_owner()),
                F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"), snapshot=F.approved(),
                      holdings=held),
                F.ctx(active=model.ApprovedState.invalid("fixture"), holdings=held)]
    hand = model.Context(**{f.name: getattr(contexts[0], f.name) for f in dataclasses.fields(model.Context)})
    templates = [F.intent(), F.intent(action="sell"), _t8_okx_buy(), _t8_okx_buy(action="sell"), _t7_withdraw(),
                 _t8_to_okx(), _t7_kis("005930"), _t7_kis("TQQQ"), _t7_kis("IBIT", action="sell"),
                 _t7_kis("005930", action="buy_to_cover"), _t7_option(), F.intent(quantity=math.nan),
                 F.intent(tags=frozenset({"spoof"})), F.intent(venue="polymarket", counter_symbol="USDC")]
    cases = []
    for n in range(200):                                   # built first: the fixtures read the shipped drafts
        i = dataclasses.replace(rng.choice(templates), reservation_id=rng.choice((None, "R1", "R2")))
        c = hand if n % 25 == 0 else rng.choice(contexts)
        cases.append((i, c, _t9_plan(i.venue, i.symbol, c.date, rng.choice((5, 30, 60)))))   # starts on c.date
    names = ("date", "datetime", "time", "timezone", "ZoneInfo", "zoneinfo")
    assert not any(hasattr(gate, n) for n in names), [n for n in names if hasattr(gate, n)]   # gate binds none
    calls, missing, results = [], object(), []
    targets = ((_t9_builtins, "open"), (_t9_io, "open"), (_t9_os, "open"), (_t9_socket.socket, "connect"),
               (_t9_socket.socket, "connect_ex"), (_t9_time, "time"), (_t9_time, "time_ns"),
               (_t9_time, "perf_counter"), (_t9_time, "monotonic"), (model, "datetime"), (model, "timezone"),
               (model, "zoneinfo"), (model, "KST"), (rules, "date"), (rules, "Path"), (rules, "os"))
    saved = [(owner, name, vars(owner).get(name, missing)) for owner, name in targets]   # model.date stays: jsonable
    probes = (lambda: _t8_dt.date.today(), lambda: _t9_pathlib.Path(__file__).read_bytes(),
              lambda: _t9_os.open(__file__, _t9_os.O_RDONLY), lambda: _t9_socket.socket.connect(None, ("127.0.0.1", 9)))
    try:
        for owner, name, _ in saved:
            setattr(owner, name, _T9Trap(f"{owner.__name__}.{name}", calls))
        for probe in probes:                               # positive control: each trap catches what it stands for
            try:
                probe()
            except AssertionError:
                pass
        assert calls == ["time.time", "io.open", "os.open", "socket.connect"], calls
        calls.clear()
        for i, c, plan in cases:
            p = gate.permit(i, c)
            results.append((gate.decide(i, c), p, gate.verify_permit(p, i, c) if p is not None else None,
                            gate.screen(plan, c, i.notional_krw)))
    finally:
        for owner, name, value in saved:
            if value is not missing:
                setattr(owner, name, value)
            elif name in vars(owner):
                delattr(owner, name)
    assert calls == [], calls[:5]
    assert {d.verdict for d, _, _, _ in results} == {model.ALLOW, model.ALLOW_EXIT, model.ACK_REQUIRED, model.BLOCK}
    assert any(v == (True, "ok") for _, _, v, _ in results)
    assert any(s.allowed for *_, s in results) and any(s.flags for *_, s in results)    # screen ran for real
    for d, _, _, s in results:
        assert not any("internal error" in r for r in d.reasons + s.decision.reasons), (d.reasons, s.decision.reasons)


def test_gate_call_graph_has_no_clock_zone_file_or_socket():
    assert _t9_names(_t9_ast.parse("from datetime import datetime\nx = datetime.now()\n")) & _T9_FORBIDDEN == {"now"}
    assert _t9_names(_t9_ast.parse("import time\ntime.time()\n")) & _T9_FORBIDDEN == {"time"}
    assert _t9_names(_t9_ast.parse("p.read_bytes()\n")) & _T9_FORBIDDEN == {"read_bytes"}
    src = _t9_inspect.getsource(gate)
    tree = _t9_ast.parse(src)
    assert "ZoneInfo" not in src and "datetime" not in src
    assert _t9_names(tree) & _T9_FORBIDDEN == set(), _t9_names(tree) & _T9_FORBIDDEN
    imported = {n.module if isinstance(n, _t9_ast.ImportFrom) else a.name
                for n in _t9_ast.walk(tree) if isinstance(n, (_t9_ast.Import, _t9_ast.ImportFrom)) for a in n.names}
    assert imported <= {"__future__", "dataclasses", "math", "string", "weakref", "collections.abc",
                        "core.compliance", "core.compliance.model"}, imported
    from_model = {a.name for n in _t9_ast.walk(tree) if isinstance(n, _t9_ast.ImportFrom)
                  and n.module == "core.compliance.model" for a in n.names}
    used = {mod: {n.attr for n in _t9_ast.walk(tree) if isinstance(n, _t9_ast.Attribute)
                  and isinstance(n.value, _t9_ast.Name) and n.value.id == mod} for mod in ("model", "rules")}
    used["model"] |= from_model
    classes = {"Review", "Row", "RulesTable", "Instrument", "InstrumentMap", "Venue", "VenueFacts"}
    synthetic = ("class OwnerState:\n    @property\n    def ok(self):\n"
                 "        from time import time as _now\n        return _now() > 0\n\n\n"
                 "def clean():\n    return 1\n")
    assert _t9_scan(synthetic) == {"OwnerState": {"time"}, "clean": set()}      # an aliased clock import is caught
    scans = {"model": _t9_scan(_t9_inspect.getsource(model)),    # every def: OwnerState.ok runs on each decision
             "rules": _t9_scan(_t9_inspect.getsource(rules), used["rules"] | classes)}     # what gate.py can reach
    assert {"OwnerState", "Context", "ApprovedState"} <= set(scans["model"]) and classes <= set(scans["rules"]), scans
    for module, scan in scans.items():
        assert len(scan) >= 3, (module, scan)
        for name, hits in scan.items():
            assert hits == set(), (module, name, hits)
