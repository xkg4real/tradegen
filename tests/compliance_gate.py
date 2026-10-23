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
    full = F.approved()
    entries = {k: v for k, v in full.instruments.entries.items() if k != ("us", "IBIT")}
    state = dataclasses.replace(full, instruments=dataclasses.replace(full.instruments, entries=entries),
                                history_maps=(full.instruments,))
    held = {("kis", "IBIT"): 2.0}
    sell = gate.decide(_t7_kis("IBIT", action="sell"), F.ctx(active=state, holdings=held))
    assert sell.kind == "close_long" and not _t7_has(sell, "malformed: "), sell.reasons
    buy = gate.decide(_t7_kis("IBIT"), F.ctx(active=state, holdings=held))
    assert buy.kind == "malformed" and "malformed: symbol" in buy.reasons
    gone = F.ctx(active=dataclasses.replace(state, history_maps=()), holdings=held)
    d = gate.decide(_t7_kis("IBIT", action="sell"), gone)
    assert d.verdict == model.BLOCK and {"malformed: symbol", "close manually in the broker app"} <= set(d.reasons)


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
