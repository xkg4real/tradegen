"""E3 authenticated lifecycle acceptance in explicitly synthetic signed homes.

Only HTTP delivery is replaced. The real fresh-odds preparation, owner signature
verification, controller, journal, credentials binding, authentication and venue
codecs all run. AccountObservation/Fill inputs are independent fake authoritative
records; these tests do not claim that E1 supplies a production trading account
provider. No real credential, order, venue connection or home is used.
"""
from __future__ import annotations

import base64
from collections import deque
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from core.compliance import gate, model as M, owner, rules as compliance_rules
from core.odds import models
from core.oddsdata import inputs as odds_inputs
from execution_control.controller import AccountObservation, Controller, _fold
from execution_control.model import InstrumentRules, Order, decimal_text
from execution_control.risk import Fill, RiskObservation, RiskPolicy, account_fills
from execution_control.session import prepare_session
from execution_control.store import Journal
from execution_orders import transport as T
from tests import compliance_fixtures as F, odds_fixtures as OF
from tests.macro_m1_calendars import fixture_set

D = Decimal
SCOPE = "lifecycleAccount"
ACCESS = "lifecycle-test-access"
SECRET = "lifecycle-test-secret"
PASS = "lifecycle-test-passphrase"
TOKEN = "lifecycle-test-token"
ACCOUNT = "31415926"
ORG = "00123"
TRADE_DATE = "20261026"
_PATHS = {
    "upbit": {"create": ("POST", "/v1/orders"), "status": ("GET", "/v1/order"), "cancel": ("DELETE", "/v1/order")},
    "okx": {"create": ("POST", "/api/v5/trade/order"), "status": ("GET", "/api/v5/trade/order"),
            "cancel": ("POST", "/api/v5/trade/cancel-order")},
    "krx": {"create": ("POST", "/uapi/domestic-stock/v1/trading/order-cash"),
            "status": ("GET", "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"),
            "cancel": ("POST", "/uapi/domestic-stock/v1/trading/order-rvsecncl")},
    "nasd": {"create": ("POST", "/uapi/overseas-stock/v1/trading/order"),
             "status": ("GET", "/uapi/overseas-stock/v1/trading/inquire-ccnl"),
             "cancel": ("POST", "/uapi/overseas-stock/v1/trading/order-rvsecncl")},
}


def _refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("expected control refusal")


def _order(case):
    venue = "kis" if case in ("krx", "nasd") else case
    return Order(client_id="lifeBuy", account_scope=SCOPE, venue=venue,
                 market=case if venue == "kis" else "spot",
                 symbol={"krx": "005930", "nasd": "AAPL", "upbit": "KRW-BTC", "okx": "BTC-USDT"}[case],
                 side="buy", quantity=D("2") if venue == "kis" else D("0.0002"),
                 limit_price=D({"krx": "5000", "nasd": "10", "upbit": "100000000", "okx": "50000"}[case]),
                 quote_krw=D("1") if case in ("upbit", "krx") else D("1400"),
                 time_in_force="day" if venue == "kis" else "gtc")


def _broker_id(order):
    if order.venue == "upbit":
        return ("9d481227-c5c1-4b3c-960d-000000000001" if order.side == "buy" else
                "9d481227-c5c1-4b3c-960d-000000000002")
    return "10101" if order.side == "buy" else "20202"


def _quote(order):
    return "KRW" if order.venue == "upbit" or order.market == "krx" else "USD" if order.venue == "kis" else "USDT"


def _base(order):
    return order.symbol if order.venue == "kis" else "BTC"


def _wire_reply(order, operation, *, filled=D("0"), state="open"):
    """Literal venue field schemas, independent of codec output construction."""
    qty, price, executed = map(decimal_text, (order.quantity, order.limit_price, filled))
    remaining = decimal_text(order.quantity - filled)
    broker = _broker_id(order)
    if order.venue == "upbit":
        return {"uuid": broker, "identifier": order.client_id, "market": order.symbol,
                "side": "bid" if order.side == "buy" else "ask", "ord_type": "limit",
                "volume": qty, "price": price, "executed_volume": executed, "remaining_volume": remaining,
                "state": {"open": "wait", "partial": "wait", "filled": "done", "canceled": "cancel"}[state],
                "paid_fee": decimal_text(filled * order.limit_price * D("0.001"))}
    if order.venue == "okx":
        if operation != "status":
            return {"code": "0", "data": [{"sCode": "0", "ordId": broker, "clOrdId": order.client_id}]}
        return {"code": "0", "data": [{"ordId": broker, "clOrdId": order.client_id, "instId": order.symbol,
                "instType": "SPOT", "tdMode": "cash", "side": order.side, "ordType": "limit", "sz": qty,
                "px": price, "accFillSz": executed, "avgPx": price if filled else "",
                "state": {"open": "live", "partial": "partially_filled", "filled": "filled", "canceled": "canceled"}[state],
                "fee": "-" + decimal_text(filled * order.limit_price * D("0.001")) if filled else "0",
                "feeCcy": "USDT"}]}
    if operation != "status":
        return {"rt_cd": "0", "output": {"ODNO": "30303" if operation == "cancel" else broker,
                "KRX_FWDG_ORD_ORGNO": ORG, "ORD_TMD": "100000"}}
    shared = {"odno": broker, "ord_dt": TRADE_DATE, "ord_gno_brno": ORG, "pdno": order.symbol,
              "sll_buy_dvsn_cd": "02" if order.side == "buy" else "01"}
    if order.market == "krx":
        return {"rt_cd": "0", "output1": [{**shared, "ord_qty": qty, "ord_unpr": price,
                "ord_dvsn_cd": "00", "excg_id_dvsn_cd": "KRX", "tot_ccld_qty": executed,
                "rmn_qty": "0" if state == "canceled" else remaining,
                "cnc_cfrm_qty": remaining if state == "canceled" else "0", "rjct_qty": "0",
                "cncl_yn": "Y" if state == "canceled" else "N", "avg_prvs": price if filled else "0"}]}
    return {"rt_cd": "0", "output": [{**shared, "ft_ord_qty": qty, "ft_ord_unpr3": price,
            "ovrs_excg_cd": "NASD", "ft_ccld_qty": executed, "ft_ccld_unpr3": price if filled else "0",
            "nccs_qty": "0" if state == "canceled" else remaining,
            "prcs_stat_name": "취소완료" if state == "canceled" else "fixture"}]}


class _Wire:
    """Queue exact in-memory replies and independently verify authenticated bytes."""
    def __init__(self, env):
        self.env = env
        self.pending = deque()
        self.calls = []
        self.providers = 0

    def expect(self, order, operation, *, filled=D("0"), state="open", error=None):
        self.pending.append((order, operation, _wire_reply(order, operation, filled=filled, state=state), error))

    def credentials(self, venue, account_scope):
        assert (venue, account_scope) == (self.env.order.venue, SCOPE)
        assert self.pending, "credentials resolved without a queued offline request"
        self.providers += 1
        operation = self.pending[0][1]
        rows = [json.loads(line) for line in (self.env.home / "execution-control" / "journal.jsonl").read_bytes().splitlines()]
        if operation in ("create", "cancel"):
            assert rows[-1]["kind"] == ("dispatching" if operation == "create" else "cancel_requested")
        return T.Credentials(venue=venue, account_scope=account_scope, access_key=ACCESS, secret_key=SECRET,
                             passphrase=PASS, bearer_token=TOKEN, account_number=ACCOUNT, account_product="01")

    def send(self, method, url, *, headers, body, timeout):
        assert self.pending, "unexpected HTTP attempt"
        order, operation, response, error = self.pending.popleft()
        parsed = urlsplit(url)
        assert (method, parsed.path) == _PATHS[self.env.case][operation]
        assert parsed.scheme == "https" and not parsed.username and not parsed.fragment
        assert parsed.netloc == {"upbit": "api.upbit.com", "okx": "www.okx.com", "kis": "openapi.koreainvestment.com:9443"}[order.venue]
        assert timeout == T.TIMEOUT_S and self.providers == len(self.calls) + 1
        payload = json.loads(body) if body else {}
        query = parse_qs(parsed.query, keep_blank_values=True)
        if order.venue == "upbit":
            header, claims, signature = headers["Authorization"].removeprefix("Bearer ").split(".")
            message = (header + "." + claims).encode("ascii")
            expected = base64.urlsafe_b64encode(hmac.new(SECRET.encode(), message, hashlib.sha512).digest()).rstrip(b"=").decode()
            assert hmac.compare_digest(signature, expected)
            claims = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
            represented = unquote(urlencode(list(payload.items()))) if body else unquote(parsed.query)
            assert claims["query_hash"] == hashlib.sha512(represented.encode()).hexdigest()
            assert claims["access_key"] == ACCESS and claims["query_hash_alg"] == "SHA512" and claims["nonce"]
        elif order.venue == "okx":
            request_path = parsed.path + ("?" + parsed.query if parsed.query else "")
            preimage = headers["OK-ACCESS-TIMESTAMP"].encode() + method.encode() + request_path.encode() + body
            expected = base64.b64encode(hmac.new(SECRET.encode(), preimage, hashlib.sha256).digest()).decode()
            assert hmac.compare_digest(headers["OK-ACCESS-SIGN"], expected)
            assert headers["OK-ACCESS-KEY"] == ACCESS and headers["OK-ACCESS-PASSPHRASE"] == PASS
        else:
            assert headers["authorization"] == "Bearer " + TOKEN
            assert headers["appkey"] == ACCESS and headers["appsecret"] == SECRET
            fields = payload if body else {key: value[0] for key, value in query.items()}
            assert fields["CANO"] == ACCOUNT and fields["ACNT_PRDT_CD"] == "01"
            expected_tr = ({"create": "TTTC0012U" if order.side == "buy" else "TTTC0011U", "cancel": "TTTC0013U", "status": "TTTC0081R"}
                           if order.market == "krx" else
                           {"create": "TTTT1002U" if order.side == "buy" else "TTTT1006U", "cancel": "TTTT1004U", "status": "TTTS3035R"})
            assert headers["tr_id"] == expected_tr[operation]
            if operation == "cancel":
                assert fields["ORGN_ODNO"] == _broker_id(order)
                assert fields["ORD_QTY"] == decimal_text(order.quantity / 2)
            if operation == "status" and order.market == "nasd":
                assert fields["ODNO"] == fields["ORD_GNO_BRNO"] == fields["ORD_DT"] == ""
        self.calls.append((operation, order.client_id, method, parsed.path))
        if error is not None:
            raise error
        return 200, {"tr_cont": "D"} if order.venue == "kis" else {}, json.dumps(response).encode()


@contextmanager
def _signed_lifecycle(case):
    """Real approvals and calendar, reduced simulation path counts, fake account inputs."""
    with F.temp_home() as home, F.pubkey_at(home / "lifecycle-anchor.pem"), OF.chunk(), OF.pilots():
        calendar = compliance_rules.calendar_stream(fixture_set().data_dir)
        key = F.full_home(home, venues_raw=OF.ODDS_VENUES, calendar_raw=calendar,
                          limits={"total_loss_floor_krw": 2000.0, "daily_loss_krw": 5000.0}, cap=0.1)
        order = _order(case)
        now = datetime(2026, 10, 27, 3, tzinfo=M.KST) if case == "nasd" else datetime(2026, 10, 26, 10, tzinfo=M.KST)
        lot = D("1") if order.venue == "kis" else D("0.00000001")
        instrument_rules = InstrumentRules(venue=order.venue, market=order.market, symbol=order.symbol,
            lot_size=lot, tick_size=D("10") if case == "krx" else D("0.01"), min_quantity=lot,
            min_notional_krw=D("5000") if case == "upbit" else D("1"), fee_fraction=D("0.001"),
            asof=now, source_digest="c" * 64)
        policy = RiskPolicy(version="lifecycle-v1", initial_equity=D("2000"), drawdown_activation_equity=D("8000"),
            positive_profit_loss_fraction=D("0.2"), peak_drawdown_fraction=D("0.25"),
            zero_profit_day_target_fraction=D("0.1"), first_day_loss_budget=D("10"), zero_profit_day_loss_budget=D("10"))
        observation = AccountObservation(positions=M.Positions(equity_krw=1000000.0,
                exposure={order.venue: M.Exposure(held_krw=0.0)}), account_scopes={order.venue: SCOPE},
            settled_cash_krw={(order.venue, SCOPE): D("1000000")}, holdings={},
            held_exposure_krw={(order.venue, SCOPE): D("0")},
            quote_currency_by_account={(order.venue, SCOPE): _quote(order)},
            inventory_exposure_krw={(order.venue, SCOPE): D("0")},
            quote_rates_krw={(order.venue, SCOPE, _quote(order)): order.quote_krw},
            risk=RiskObservation(equity=D("1000000"), prior_high_watermark=D("1000000"),
                day_start_equity=D("1000000"), current_day_realized_net_profit=D("0"),
                prior_day_realized_net_profit=D("100"), observed_daily_loss=D("0"),
                approved_effective_floor=D("750000"), is_first_trading_day=False, asof=now),
            asof=now, server_time=now, no_credit=True,
            venue_trade_dates={(order.venue, SCOPE, order.market): TRADE_DATE} if order.venue == "kis" else {})
        selected = OF.plan(venue=order.venue, symbol=_base(order), start=now.date(), horizon_days=1)
        series = OF.fresh_series(end=(selected.start - timedelta(days=1)).isoformat(),
            symbol=order.symbol if order.venue != "okx" else "BTC",
            source={"upbit": "UPBIT", "okx": "BINANCE:BTCUSDT*UPBIT:KRW-USDT", "krx": "KIS", "nasd": "YAHOO"}[case],
            price={"upbit": 50000000.0, "okx": 50000000.0, "krx": 5000.0, "nasd": 14000.0}[case],
            vol=0.005 if order.venue == "kis" else 0.02)
        calendar_set, calendar_sha, calendar_error = odds_inputs.calendar_for(now)
        assert not calendar_error
        market = "KR" if case == "krx" else "US" if case == "nasd" else "CRYPTO"
        days, limits, md5s, version, error = odds_inputs.sessions(market, selected.start, 1, calendar_set)
        assert days and not error
        inputs = OF.inputs(selected, series, now=now, sessions=days, price_limits=limits,
            calendar_sha256=calendar_sha if order.venue == "kis" else "", calendar_md5s=md5s,
            calendar_version=version, calendar_error=error)
        seed = models.market_seed(models.data_hashes(series, inputs.replay), inputs.calendar_sha256,
                                  inputs.comparison_id, inputs.run_counter).hex()
        journal = Journal()
        prepared = prepare_session(journal=journal, session_id="lifecycle", selected_plan=selected, inputs=inputs,
            positions=observation.positions, policy=policy, instrument_rules=instrument_rules, now=now,
            selection_seed_hex=seed, account_scope=SCOPE, market=order.market, quote_currency=_quote(order))
        assert prepared.seed_hex != seed
        F.sign(key, "session_armed", {"session_id": prepared.session_id}, M.iso_utc(now))
        if order.venue == "okx":
            ctx = owner.load_context(now, observation.positions, session_id=prepared.session_id)
            row = next(row for row in ctx.active.rules.rows if row.id == "KR-OKX-SPOT")
            F.sign(key, "session_ack", {"session_id": prepared.session_id, "row_id": row.id,
                "warning_sha256": gate.warning_sha256(row, {"cap": "10%"})}, M.iso_utc(now))
        env = SimpleNamespace(case=case, home=home, key=key, now=now, order=order, rules=instrument_rules,
            journal=journal, prepared=prepared, session_id=prepared.session_id, policy=policy, observation=observation)
        env.wire = _Wire(env)
        adapter = T.AuthenticatedTransport(credentials=env.wire.credentials)
        env.controller = Controller(journal=journal, account_provider=lambda stamp: env.observation, policy=policy,
            adapters={order.venue: adapter}, session_provider=lambda sid: prepared)
        saved = T._send
        T._send = env.wire.send
        try:
            yield env
            assert not env.wire.pending, "queued protocol exchange was not consumed"
            raw = (home / "execution-control" / "journal.jsonl").read_text()
            for value in (ACCESS, SECRET, PASS, TOKEN, ACCOUNT):
                assert value not in raw, "credential or account value entered durable journal"
        finally:
            T._send = saved


def _fill(env, order, index):
    quantity = order.quantity / 2
    return Fill(venue=order.venue, account_scope=SCOPE, order_id=_broker_id(order),
        fill_id=order.client_id + str(index), market=order.market, symbol=order.symbol, side=order.side,
        quantity=quantity, price=order.limit_price, quote_currency=_quote(order), quote_krw=order.quote_krw,
        fee_amount=quantity * order.limit_price * D("0.001"), fee_currency=_quote(order),
        executed_at=env.now, base_currency="" if order.venue == "kis" else _base(order),
        order_date=TRADE_DATE if order.venue == "kis" else "", broker_org_id=ORG if order.venue == "kis" else "")


def _account(env, fills, *client_ids):
    """Explicit synthetic full-history provider; derive consistent inventory/cash."""
    ledger = account_fills(tuple(fills))
    assert ledger.ok, ledger.reasons
    order = env.order
    held = sum((fill.quantity if fill.side == "buy" else -fill.quantity for fill in fills), D("0"))
    fees = sum((fill.fee_amount * fill.quote_krw for fill in fills), D("0"))
    cash_delta = sum(((-1 if fill.side == "buy" else 1) * fill.quantity * fill.price * fill.quote_krw
                      - fill.fee_amount * fill.quote_krw for fill in fills), D("0"))
    marked = held * order.limit_price * order.quote_krw
    positions = M.Positions(equity_krw=float(D("1000000") - fees), holdings={(order.venue, _base(order)): float(held)},
                            exposure={order.venue: M.Exposure(held_krw=float(marked))})
    env.observation = replace(env.observation, positions=positions,
        holdings={(order.venue, SCOPE, order.market, order.symbol): held},
        held_exposure_krw={(order.venue, SCOPE): marked},
        inventory_exposure_krw={(order.venue, SCOPE): marked},
        settled_cash_krw={(order.venue, SCOPE): D("1000000") + cash_delta}, fills=tuple(fills),
        reconciled_client_ids=frozenset(client_ids),
        risk=replace(env.observation.risk, equity=D("1000000") - fees,
                     current_day_realized_net_profit=ledger.realized_net_profit_krw))


def _reserve(env, order):
    return env.controller.reserve(order, env.rules, session_id=env.session_id, now=env.now)


def _reconcile(env, order, *, filled, state):
    env.wire.expect(order, "status", filled=filled, state=state)
    return env.controller.reconcile(order.client_id, now=env.now)


def _lifecycle(case):
    with _signed_lifecycle(case) as env:
        buy = env.order
        assert _reserve(env, buy).status == "RESERVED" and not env.wire.calls
        env.wire.expect(buy, "create")
        state = env.controller.dispatch(buy.client_id, now=env.now)
        assert state.status == "ACKNOWLEDGED" and state.filled_quantity == 0
        assert state.venue_order_id == _broker_id(buy)
        assert env.controller.dispatch(buy.client_id, now=env.now) == state and len(env.wire.calls) == 1
        first, second = _fill(env, buy, 1), _fill(env, buy, 2)
        _account(env, (first,), buy.client_id)
        state = _reconcile(env, buy, filled=buy.quantity / 2, state="partial")
        assert state.status == "PARTIAL" and state.filled_quantity == buy.quantity / 2
        # A full status cannot release capacity before the provider has every fill/fee.
        state = _reconcile(env, buy, filled=buy.quantity, state="filled")
        assert state.status == "PARTIAL" and state.filled_quantity == buy.quantity / 2
        _account(env, (first, second), buy.client_id)
        state = _reconcile(env, buy, filled=buy.quantity, state="filled")
        assert state.status == "FILLED" and state.filled_quantity == buy.quantity
        count = len(env.wire.calls)
        assert env.controller.reconcile(buy.client_id, now=env.now) == state and len(env.wire.calls) == count
        env.observation = replace(env.observation, risk=replace(env.observation.risk, observed_daily_loss=D("5000")))
        assert env.controller.observe(now=env.now).new_entry_blocked
        assert env.controller.kill(env.session_id, reason="lifecycle test", now=env.now)
        _refused(lambda: _reserve(env, replace(buy, client_id="blockedEntry")))
        sell = replace(buy, client_id="lifeSell", side="sell")
        assert _reserve(env, sell).status == "RESERVED"
        env.wire.expect(sell, "create")
        assert env.controller.dispatch(sell.client_id, now=env.now).status == "ACKNOWLEDGED"
        sale = _fill(env, sell, 1)
        _account(env, (first, second, sale), buy.client_id, sell.client_id)
        state = _reconcile(env, sell, filled=sell.quantity / 2, state="partial")
        assert state.status == "PARTIAL" and state.filled_quantity == sell.quantity / 2
        env.observation = replace(env.observation, cancellable_quantities={sell.client_id: sell.quantity / 2})
        env.wire.expect(sell, "cancel", filled=sell.quantity / 2, state="canceled")
        canceled = env.controller.cancel(sell.client_id, now=env.now)
        assert canceled.status not in ("CANCELED", "FILLED")
        count = len(env.wire.calls)
        env.controller.cancel(sell.client_id, now=env.now)
        assert len(env.wire.calls) == count, "cancel acknowledgment caused duplicate mutation"
        with env.journal.transaction() as tx:
            record = _fold(tx.events)[0][sell.client_id]
            assert record["cancel_pending"] and record["filled"] == sell.quantity / 2
        replacement = replace(sell, client_id="remainingExit", quantity=sell.quantity / 2)
        _refused(lambda: _reserve(env, replacement))  # residual units still promised
        state = _reconcile(env, sell, filled=sell.quantity / 2, state="canceled")
        if case == "nasd":
            # The unsupported US terminal-cancel schema stays conservative.
            assert state.status not in ("CANCELED", "FILLED")
            _refused(lambda: _reserve(env, replacement))
            late_sale = _fill(env, sell, 2)
            _account(env, (first, second, sale, late_sale), buy.client_id, sell.client_id)
            state = _reconcile(env, sell, filled=sell.quantity, state="filled")
            assert state.status == "FILLED" and state.filled_quantity == sell.quantity
        else:
            assert state.status == "CANCELED" and state.filled_quantity == sell.quantity / 2
            assert _reserve(env, replacement).status == "RESERVED"
            assert env.controller.cancel(replacement.client_id, now=env.now).status == "CANCELLED_LOCAL"
        with env.journal.transaction() as tx:
            rows = tx.events
            assert sum(row["kind"] == "fill" for row in rows) == (4 if case == "nasd" else 3)
            assert not _fold(rows)[0][sell.client_id]["cancel_pending"]
        assert sum(operation == "create" for operation, *_ in env.wire.calls) == 2
        assert sum(operation == "cancel" for operation, *_ in env.wire.calls) == 1


def test_upbit_authenticated_partial_final_kill_exit_and_cancel_lifecycle():
    _lifecycle("upbit")


def test_kis_krx_authenticated_partial_final_kill_exit_and_cancel_lifecycle():
    _lifecycle("krx")


def test_kis_us_authenticated_partial_final_kill_exit_and_ambiguous_cancel_lifecycle():
    _lifecycle("nasd")


def test_okx_authenticated_partial_final_grey_ack_kill_exit_and_cancel_lifecycle():
    _lifecycle("okx")


def test_current_foreign_fx_binds_new_orders_but_preserves_existing_cancel_and_reconcile():
    with _signed_lifecycle('okx') as env:
        buy=env.order
        _refused(lambda:_reserve(env,replace(buy,quote_krw=D('1'))))
        assert not env.wire.calls
        assert _reserve(env,buy).status=='RESERVED'
        original_rates=env.observation.quote_rates_krw
        changed_rates={(buy.venue,SCOPE,_quote(buy)):buy.quote_krw+D('100')}
        env.observation=replace(env.observation,quote_rates_krw=changed_rates)
        _refused(lambda:env.controller.dispatch(buy.client_id,now=env.now))
        assert not env.wire.calls
        env.observation=replace(env.observation,quote_rates_krw=original_rates)
        env.wire.expect(buy,'create')
        assert env.controller.dispatch(buy.client_id,now=env.now).status=='ACKNOWLEDGED'
        first=_fill(env,buy,1)
        _account(env,(first,),buy.client_id)
        env.observation=replace(env.observation,quote_rates_krw=changed_rates)
        assert _reconcile(env,buy,filled=buy.quantity/2,state='partial').status=='PARTIAL'
        env.wire.expect(buy,'cancel',filled=buy.quantity/2,state='canceled')
        env.controller.cancel(buy.client_id,now=env.now)
        assert _reconcile(env,buy,filled=buy.quantity/2,state='canceled').status=='CANCELED'
        sell=replace(buy,client_id='fxSell',side='sell',quantity=buy.quantity/2)
        _refused(lambda:_reserve(env,sell))
        sell=replace(sell,quote_krw=changed_rates[(buy.venue,SCOPE,_quote(buy))])
        assert _reserve(env,sell).status=='RESERVED'
        env.observation=replace(env.observation,quote_rates_krw=original_rates)
        _refused(lambda:env.controller.dispatch(sell.client_id,now=env.now))
        assert env.controller.cancel(sell.client_id,now=env.now).status=='CANCELLED_LOCAL'
        assert sum(operation=='create' for operation,*_ in env.wire.calls)==1
