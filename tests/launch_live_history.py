"""Durable live history: invented Upbit book receipts and account anchors over a temporary state root and a
temporary head root; no network, credentials, owner state or real home."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import base64
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from core.isolation import state_root
from execution_accounts.collector import SourceReceipt
from execution_accounts.quotes import parse_orderbook, to_runner_quote
from execution_control.capability import digest
from execution_control.controller import AccountObservation
from execution_control.risk import RiskObservation
from execution_control.store import GENESIS, _canonical
from execution_launch.baseline_head import BaselineHead
from execution_launch.driver import AccountAnchor, describe_fixed_driver, history_frame_digest
from execution_launch.live_history import STORE_DIRECTORY, HistoryChain, LiveHistory
from execution_launch.runner import DecisionInput, Quote
from execution_launch.strategy import PaperBar, history_digest
from tests import compliance_fixtures as F
from tests import launch_driver as LD
from tests.launch_baseline_head import head_root

D = Decimal
SYMBOL = "KRW-BTC"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NAME = "live-history"


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def seconds(value):
    return timedelta(seconds=value)


def ms(at):
    delta = at - EPOCH
    return (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000


def book_at(env, i, received=-1, asof=-2, symbol=SYMBOL):
    """An invented single-level book for slot i: bid 100+i, ask 102+i, stamped relative to the slot."""
    slot = env.T(i)
    raw = json.dumps([{"market": symbol, "level": 0, "timestamp": ms(slot + seconds(asof)), "total_ask_size": 3,
                       "total_bid_size": 4, "orderbook_units": [{"ask_price": 102 + i % 10, "bid_price": 100 + i % 10,
                                                                 "ask_size": 3, "bid_size": 4}]}]).encode()
    when = slot + seconds(received)
    receipt = SourceReceipt(path="/v1/orderbook", params=(("markets", symbol), ("level", "0"), ("count", "30")),
                            account_scope="public-upbit-orderbook", received_at=when, server_time=when,
                            raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
    return parse_orderbook(receipt, symbol=symbol, now=when)


def account_at(env, asof, cash=D(10000), units=D(0)):
    profile = env.profile
    key = (profile.venue, profile.account_scope)
    inventory = units * D(101)
    equity = cash + inventory
    return AccountObservation(positions=M.Positions(equity_krw=float(equity), holdings={}, exposure={}),
        account_scopes={profile.venue: profile.account_scope}, settled_cash_krw={key: cash},
        holdings={(*key, profile.market, profile.symbol): units},
        held_exposure_krw={key: equity}, inventory_exposure_krw={key: inventory},
        quote_currency_by_account={key: "KRW"}, quote_rates_krw={(*key, "KRW"): D(1)},
        risk=RiskObservation(equity=equity, prior_high_watermark=equity, day_start_equity=equity,
            current_day_realized_net_profit=D(0), prior_day_realized_net_profit=D(10),
            observed_daily_loss=D(0), approved_effective_floor=None, is_first_trading_day=False, asof=asof),
        asof=asof, server_time=asof, no_credit=True)


def obs(env, now):
    """A DecisionInput whose only consulted field is `now` (provider-only calls)."""
    quote = Quote(venue="upbit", market="spot", symbol=SYMBOL, bid=D(100), ask=D(102), asof=now, source_sha256="0" * 64)
    return DecisionInput(now=now, profile=env.profile, quote=quote, account=account_at(env, now))


def chain_for(env):
    return HistoryChain(root=state_root().absolute(), window=env.window)


def attach(env, **changes):
    """A LiveHistory over the state root and `env.head`, plus a fixed driver wired to its exact callables."""
    env.h = LiveHistory(env.e.program, env.e.protocol, env.e.profile, window=env.window,
                        root=state_root().absolute(), clock=lambda: env.clock(), trusted_head=env.head)
    env.d = LD.construct(env.e, window=env.window, history_provider=env.h.provider,
                         history_verifier=env.h.verifier, **changes)


def build(hroot, *, deployment_id=None, name=NAME, bind=True):
    e = LD.fixture()
    window = e.window if deployment_id is None else replace(e.window, deployment_id=deployment_id)
    start = e.window.start
    env = SimpleNamespace(e=e, profile=e.profile, window=window, hroot=hroot, name=name, start=start,
                          c=[start - timedelta(minutes=5)], T=lambda i: start + timedelta(minutes=i))
    env.clock = lambda: env.c[0]
    env.head = BaselineHead(root=hroot, name=name, chain=chain_for(env))
    env.head.initialize_reviewed_head(GENESIS)
    attach(env)
    if bind:
        env.identity = env.h.bind(env.d)
    return env


def restart(env):
    """A new head instance, a new LiveHistory and a new fixed driver over the same roots, then bind."""
    env.head = BaselineHead(root=env.hroot, name=env.name, chain=chain_for(env))
    attach(env)
    env.identity = env.h.bind(env.d)
    return env.identity


def record(env, i, at=1, *, cash=D(10000), asof=None):
    env.c[0] = env.T(i) + seconds(at)
    return env.h.record_slot(book_at(env, i), account_at(env, asof or env.T(i) - seconds(1), cash))


def tick(env, i, at=2, *, cash=D(10000), asof=None, quote_at=None, driver=None):
    now = env.T(i) + seconds(at)
    env.c[0] = now
    driver = driver or env.d
    quote = to_runner_quote(book_at(env, i), now=now if quote_at is None else quote_at)
    observation = DecisionInput(now=now, profile=env.profile, quote=quote,
                                account=account_at(env, asof or env.T(i) - seconds(1), cash))
    return driver.callback(observation, driver.parameters_json)


def directory(window):
    return state_root() / STORE_DIRECTORY / digest(window)


def journal(env):
    return directory(env.window) / "history.jsonl"


def rows(env):
    return [json.loads(line) for line in journal(env).read_bytes().splitlines()]


def sequence(env):
    return json.loads((env.hroot / env.name / "head.json").read_bytes())["baseline_sequence"]


def rewrite(env, seq, change, *, rehash):
    """Edit row `seq` in place; with rehash, recompute prev_sha256/row_sha256 from that row onward (head untouched)."""
    table = rows(env)
    change(table[seq - 1])
    if rehash:
        for index in range(seq - 1, len(table)):
            row = table[index]
            row["prev_sha256"] = table[index - 1]["row_sha256"] if index else GENESIS
            body = {key: value for key, value in row.items() if key != "row_sha256"}
            row["row_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    journal(env).write_bytes(b"".join(_canonical(row) + b"\n" for row in table))


def change_bid(row):
    receipt = row["data"]["receipt"]
    before = base64.b64decode(receipt["raw_body_b64"])
    raw = before.replace(b'"bid_price": 101', b'"bid_price": 99')
    assert raw != before
    receipt["raw_body_b64"] = base64.b64encode(raw).decode("ascii")
    receipt["sha256"] = hashlib.sha256(raw).hexdigest()


def change_cash(row):
    assert row["data"]["anchor"]["cash_quote"] == "10000"
    row["data"]["anchor"]["cash_quote"] = "9999"


def test_history_and_anchor_identity_survive_restart():
    with head_root() as hroot:
        env = build(hroot)
        assert env.identity == describe_fixed_driver(env.d)
        for i in range(5):
            record(env, i)
        signal = tick(env, 4)
        frame = env.h.provider(obs(env, env.T(4) + seconds(2)))
        assert len(frame.bars) == 5 and frame.deployment_window_digest == digest(env.window)
        assert frame.source_kind == "prospective_paper_capture"
        for i, bar in enumerate(frame.bars):
            assert bar == PaperBar(observed_at=env.T(i), received_at=env.T(i) + seconds(1), bid=D(100 + i),
                                   ask=D(102 + i), mark=D(101 + i), quote_krw=D(1),
                                   source_sha256=book_at(env, i).receipt.sha256)
        prior = frame.prior_decision
        assert prior.bar_index == 3 and prior.target_fraction == D("0.5") and prior.decided_at == env.T(3) + seconds(1)
        assert prior.history_sha256 == history_digest(frame.bars[:4])
        assert frame.anchor == AccountAnchor(cash_quote=D(10000), units=D(0), account_asof=env.T(4) - seconds(1))
        assert (signal.action, signal.quantity, signal.limit_price) == ("entry", D("47.14"), D(107))
        assert sequence(env) == 6 and len(rows(env)) == 6
        restart(env)
        assert tick(env, 4) == signal
        assert env.h.provider(obs(env, env.T(4) + seconds(2))) == frame
        assert sequence(env) == 6 and len(rows(env)) == 6


def test_rewritten_history_refuses():
    with head_root() as hroot:
        env = build(hroot)
        for i in range(5):
            record(env, i)
        tick(env, 4)
        path, original = journal(env), journal(env).read_bytes()
        rewrite(env, 3, change_bid, rehash=False)
        refused(lambda: restart(env), "HISTORY_STORE_RECORD_INVALID")
        path.write_bytes(original)
        rewrite(env, 3, change_bid, rehash=True)
        refused(lambda: restart(env), "HISTORY_HEAD_MISMATCH")
        lines = original.splitlines(keepends=True)
        path.write_bytes(b"".join(lines[:-1]))
        refused(lambda: restart(env), "HISTORY_HEAD_MISMATCH")
        path.write_bytes(original[:-1])
        refused(lambda: restart(env), "HISTORY_STORE_RECORD_INVALID")
        path.write_bytes(original)
        restart(env)
        now = env.T(4) + seconds(2)
        env.c[0] = now
        frame = env.h.provider(obs(env, now))
        path.write_bytes(b"".join(lines[:-1]))
        refused(lambda: env.h.verifier(frame, env.identity, now), "HISTORY_STORE_CHANGED")
        path.write_bytes(original + b"{}\n")
        refused(lambda: env.h.verifier(frame, env.identity, now), "HISTORY_STORE_CHANGED")
        path.write_bytes(original)
        assert env.h.verifier(frame, env.identity, now).frame_digest == history_frame_digest(frame)


def test_rewritten_anchor_refuses():
    with head_root() as hroot:
        env = build(hroot)
        for i in range(5):
            record(env, i)
        tick(env, 4)
        path, original = journal(env), journal(env).read_bytes()
        rewrite(env, 6, change_cash, rehash=False)
        refused(lambda: restart(env), "HISTORY_STORE_RECORD_INVALID")
        path.write_bytes(original)
        rewrite(env, 6, change_cash, rehash=True)
        refused(lambda: restart(env), "HISTORY_HEAD_MISMATCH")
        path.write_bytes(original)
        restart(env)
        env.c[0] = env.T(4) + seconds(3)
        refused(lambda: env.h.record_slot(book_at(env, 4), account_at(env, env.T(4) - seconds(1), D(9999))),
                "HISTORY_SLOT_NOT_DUE")
        assert env.h.provider(obs(env, env.c[0])).anchor.cash_quote == D(10000)
        refused(lambda: tick(env, 4, 3, cash=D(9999)), "FIXED_DRIVER_ACCOUNT_ANCHOR_MISMATCH")
        assert journal(env).read_bytes() == original and sequence(env) == 6


def test_late_book_refuses_without_partial_state():
    with head_root() as hroot:
        env = build(hroot)
        before = journal(env).read_bytes()
        env.c[0] = env.T(0) + seconds(2)
        refused(lambda: env.h.record_slot(book_at(env, 0, received=1, asof=0.5), account_at(env, env.T(0) - seconds(1))),
                "CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT")
        assert journal(env).read_bytes() == before and sequence(env) == 1
        env.c[0] = env.T(0) + seconds(3)
        env.h.record_slot(book_at(env, 0), account_at(env, env.T(0) - seconds(1)))
        assert sequence(env) == 2 and len(rows(env)) == 2


def test_future_receipts_refuse():
    with head_root() as hroot:
        env = build(hroot)
        env.c[0] = env.T(0) + seconds(1)
        refused(lambda: env.h.record_slot(book_at(env, 0, received=5, asof=4), account_at(env, env.T(0) - seconds(1))),
                "QUOTE_RECEIPT_STALE_OR_FUTURE")
        refused(lambda: env.h.record_slot(book_at(env, 0), account_at(env, env.T(0) + seconds(5))),
                "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        assert sequence(env) == 1
        record(env, 0)
        early = env.T(0) + seconds(0.5)
        frame = env.h.provider(obs(env, early))
        refused(lambda: env.h.verifier(frame, env.identity, early), "HISTORY_VERIFIED_AFTER_TICK")
        env.c[0] = env.T(0) + seconds(2)
        refused(lambda: env.h.verifier(frame, env.identity, env.T(0) + seconds(3)), "HISTORY_TICK_IN_FUTURE")
        assert env.h.verifier(frame, env.identity, env.T(0) + seconds(2)).verified_at == env.T(0) + seconds(1)


def test_replaced_history_callbacks_refuse():
    with head_root() as hroot:
        env = build(hroot, bind=False)
        wrapped = LD.construct(env.e, window=env.window, history_provider=lambda o: env.h.provider(o),
                               history_verifier=env.h.verifier)
        refused(lambda: env.h.bind(wrapped), "HISTORY_CALLBACK_MISMATCH")
        assert not directory(env.window).exists()
        env.identity = env.h.bind(env.d)
        for i in range(5):
            record(env, i)
        now = env.T(4) + seconds(2)
        genuine = env.h.provider(obs(env, now))
        altered = replace(genuine, bars=genuine.bars[:-1] + (replace(genuine.bars[-1], received_at=env.T(4)),))
        substitute = LD.construct(env.e, window=env.window, history_provider=lambda o: altered,
                                  history_verifier=env.h.verifier)
        refused(lambda: tick(env, 4, driver=substitute), "FIXED_DRIVER_HISTORY_AUTH_FAILED")
        refused(lambda: env.h.verifier(altered, env.identity, now), "HISTORY_FRAME_NOT_RECORDED")
        refused(lambda: env.h.verifier(genuine, replace(env.identity, factory_id="other"), now), "HISTORY_IDENTITY_MISMATCH")
        assert tick(env, 4).action == "entry"
        object.__setattr__(env.d.callback, "history_verifier", LD.invented_authentication)
        refused(lambda: tick(env, 4), "FIXED_DRIVER_CALLBACK_CHANGED")


def test_missed_or_stale_slot_is_never_backfilled():
    with head_root() as hroot:
        env = build(hroot)
        for i in range(3):
            record(env, i)
        env.c[0] = env.T(3) + seconds(10) + timedelta(microseconds=1)
        refused(lambda: env.h.record_slot(book_at(env, 3), account_at(env, env.T(3) - seconds(1))), "HISTORY_SLOT_MISSED")
        env.c[0] = env.T(4) + seconds(1)
        refused(lambda: env.h.record_slot(book_at(env, 4), account_at(env, env.T(4) - seconds(1))), "HISTORY_SLOT_MISSED")
        refused(lambda: env.h.provider(obs(env, env.T(4) + seconds(2))), "HISTORY_SLOT_NOT_RECORDED")
        refused(lambda: tick(env, 4), "FIXED_DRIVER_HISTORY_PROVIDER_FAILED")
        restart(env)
        refused(lambda: record(env, 5), "HISTORY_SLOT_MISSED")
        assert sequence(env) == 4 and len(rows(env)) == 4
        late = SimpleNamespace(**vars(env))
        late.window = replace(env.window, deployment_id="invented-late-deployment")
        late.head = BaselineHead(root=hroot, name="live-history-late", chain=chain_for(late))
        late.head.initialize_reviewed_head(GENESIS)
        attach(late)
        env.c[0] = env.T(5)
        refused(lambda: late.h.bind(late.d), "HISTORY_WINDOW_ALREADY_STARTED")
        assert not directory(late.window).exists()
        assert sequence(env) == 4


def test_quote_age_is_at_most_ten_seconds():
    with head_root() as hroot:
        env = build(hroot)
        env.c[0] = env.T(0)
        env.h.record_slot(book_at(env, 0, received=-10, asof=-10), account_at(env, env.T(0) - seconds(1)))
        env.c[0] = env.T(1)
        refused(lambda: env.h.record_slot(book_at(env, 1, received=-10.001, asof=-10.001),
                                          account_at(env, env.T(1) - seconds(1))), "QUOTE_RECEIPT_STALE_OR_FUTURE")
        env.h.record_slot(book_at(env, 1), account_at(env, env.T(1) - seconds(1)))
        assert tick(env, 1, 8).action in ("hold", "entry")
        refused(lambda: tick(env, 1, 8.001, quote_at=env.T(1) + seconds(8)), "FIXED_DRIVER_QUOTE_ANCHOR_MISMATCH")


def test_account_age_is_at_most_thirty_seconds():
    with head_root() as hroot:
        env = build(hroot)
        env.c[0] = env.T(0)
        env.h.record_slot(book_at(env, 0), account_at(env, env.T(0) - seconds(30)))
        assert tick(env, 0, 0, asof=env.T(0) - seconds(30)).action == "hold"
        env.c[0] = env.T(1)
        refused(lambda: env.h.record_slot(book_at(env, 1), account_at(env, env.T(1) - seconds(30.000001))),
                "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        refused(lambda: env.h.record_slot(book_at(env, 1), account_at(env, env.T(1) + timedelta(microseconds=1))),
                "HISTORY_ACCOUNT_STALE_OR_FUTURE")
        assert sequence(env) == 2


def test_execution_slot_window_is_ten_seconds():
    with head_root() as hroot:
        env = build(hroot)
        env.c[0] = env.T(0) + seconds(10)
        env.h.record_slot(book_at(env, 0, received=0, asof=0), account_at(env, env.T(0) - seconds(1)))
        frame = env.h.provider(obs(env, env.c[0]))
        refused(lambda: env.h.verifier(frame, env.identity, env.c[0]), "HISTORY_SLOT_WINDOW_CLOSED")
        env.c[0] = env.T(1) + seconds(3)
        env.h.record_slot(book_at(env, 1), account_at(env, env.T(1) - seconds(1)))
        frame = env.h.provider(obs(env, env.T(1) + seconds(9)))
        env.c[0] = env.T(1) + seconds(10) + timedelta(microseconds=1)
        refused(lambda: env.h.verifier(frame, env.identity, env.T(1) + seconds(9)), "HISTORY_SLOT_WINDOW_CLOSED")
        refused(lambda: env.h.provider(obs(env, env.c[0])), "HISTORY_SLOT_NOT_RECORDED")
        env.c[0] = env.T(2) + seconds(10) + timedelta(microseconds=1)
        refused(lambda: env.h.record_slot(book_at(env, 2), account_at(env, env.T(2) - seconds(1))), "HISTORY_SLOT_MISSED")
        assert sequence(env) == 3


def test_receipt_verification_never_after_tick():
    with head_root() as hroot:
        env = build(hroot)
        for i in range(5):
            record(env, i)
        now = env.T(4) + seconds(2)
        env.c[0] = now
        frame = env.h.provider(obs(env, now))
        receipt = env.h.verifier(frame, env.identity, now)
        assert receipt.verified_at == env.T(4) + seconds(1) <= now
        assert receipt.expires_at == env.T(4) + seconds(10)
        assert receipt.source_audit_sha256 == env.head.read() == rows(env)[-1]["row_sha256"]
        assert receipt.frame_digest == history_frame_digest(frame)
        assert receipt.driver_identity_digest == digest(env.identity)
        size = journal(env).stat().st_size
        assert env.h.verifier(frame, env.identity, now) == receipt
        assert journal(env).stat().st_size == size and sequence(env) == 6


def test_identity_head_and_failures_fail_closed():
    with head_root() as hroot:
        env = build(hroot)
        root = state_root().absolute()
        fields = dict(program=env.e.program, protocol=env.e.protocol, profile=env.e.profile, window=env.window,
                      root=root, clock=env.clock, trusted_head=env.head)
        make = lambda **changes: LiveHistory(**(fields | changes))
        double = SimpleNamespace(read=lambda: GENESIS, compare_and_set=lambda old, new: True)
        for bad in (dict(clock=None), dict(trusted_head=double), dict(program=env.e.protocol), dict(root=str(root)),
                    dict(window=env.e.protocol)):
            refused(lambda: make(**bad), "HISTORY_INPUT_REQUIRED")
        refused(lambda: make(root=Path("relative")), "HISTORY_STORE_ROOT_MISMATCH")
        fresh = make()
        refused(lambda: fresh.provider(obs(env, env.T(0))), "HISTORY_NOT_BOUND")
        refused(lambda: fresh.verifier(None, env.identity, env.T(0)), "HISTORY_NOT_BOUND")
        refused(lambda: fresh.record_slot(book_at(env, 0), account_at(env, env.T(0))), "HISTORY_NOT_BOUND")
        refused(lambda: env.h.bind(env.d), "HISTORY_ALREADY_BOUND")
        refused(lambda: env.h.provider(None), "HISTORY_OBSERVATION_REQUIRED")
        # (a) a code change mid-deployment is a different identity
        record(env, 0)
        with patch("execution_launch.driver._sources", return_value=("0" * 64, env.e.artifact)):
            refused(lambda: restart(env), "HISTORY_IDENTITY_CHANGED")
        restart(env)
        refused(lambda: env.h.record_slot(book_at(env, 1), None), "HISTORY_ACCOUNT_REQUIRED")
        foreign_scope = replace(account_at(env, env.T(1) - seconds(1)), account_scopes={"upbit": "other-scope"})
        env.c[0] = env.T(1) + seconds(1)
        refused(lambda: env.h.record_slot(book_at(env, 1), foreign_scope), "HISTORY_ACCOUNT_SCOPE_MISMATCH")
        refused(lambda: env.h.record_slot(book_at(env, 1, symbol="KRW-ETH"), account_at(env, env.T(1) - seconds(1))),
                "HISTORY_BOOK_MARKET_MISMATCH")
        # the journal is the chain behind the head
        chain = chain_for(env)
        refused(lambda: chain.seed(GENESIS), "HISTORY_CHAIN_SEED_REQUIRED")
        refused(lambda: chain.seed("1" * 64), "HISTORY_CHAIN_SEED_REQUIRED")
        table = rows(env)
        assert chain.successor(table[-2]["row_sha256"], table[-1]["row_sha256"]) == 2
        refused(lambda: chain.successor(GENESIS, table[-1]["row_sha256"]), "HISTORY_CHAIN_TRANSITION_UNVERIFIED")
        refused(lambda: env.head.compare_and_set(env.head.read(), "a" * 64), "HEAD_TRANSITION_UNVERIFIED")
        assert env.head.compare_and_set("b" * 64, env.head.read()) is False
        # (b) a head that is not at GENESIS cannot start a fresh history
        foreign = BaselineHead(root=hroot, name="live-history-foreign",
                               chain=SimpleNamespace(seed=lambda d: 0, successor=lambda old, new: 1))
        foreign.initialize_reviewed_head("1" * 64)
        other = SimpleNamespace(**vars(env))
        other.window, other.head = replace(env.window, deployment_id="invented-fresh-deployment"), foreign
        attach(other)
        env.c[0] = env.start - timedelta(minutes=5)
        refused(lambda: other.h.bind(other.d), "HISTORY_HEAD_NOT_INITIALIZED")
        assert not directory(other.window).exists()
        # (e) a failing clock or head read is a fixed code without the private text
        def secret():
            raise RuntimeError("SECRET-CLOCK")
        env.clock = secret
        refused(lambda: env.h.record_slot(book_at(env, 1), account_at(env, env.T(1))), "HISTORY_CLOCK_FAILED")
        env.clock = lambda: env.c[0].replace(tzinfo=None)
        refused(lambda: env.h.record_slot(book_at(env, 1), account_at(env, env.T(1))), "HISTORY_CLOCK_FAILED")
        env.clock = lambda: env.c[0]
        with patch.object(env.head, "read", side_effect=RuntimeError("SECRET-HEAD")):
            refused(lambda: record(env, 1), "HISTORY_TRUSTED_HEAD_READ_FAILED")
            env.c[0] = env.T(0) + seconds(2)
            frame = env.h.provider(obs(env, env.c[0]))
            refused(lambda: env.h.verifier(frame, env.identity, env.c[0]), "HISTORY_TRUSTED_HEAD_READ_FAILED")
        assert sequence(env) == 2 and len(rows(env)) == 2
        # (d) a second instance on the same journal and head advances it; the first then refuses
        record(env, 1)
        twin = SimpleNamespace(**vars(env))
        attach(twin)
        twin.identity = twin.h.bind(twin.d)
        record(twin, 2)
        env.c[0] = env.T(1) + seconds(2)
        frame = env.h.provider(obs(env, env.c[0]))
        refused(lambda: env.h.verifier(frame, env.identity, env.c[0]), "HISTORY_HEAD_MISMATCH")
        env.c[0] = env.T(2) + seconds(2)
        refused(lambda: env.h.record_slot(book_at(env, 2), account_at(env, env.T(2) - seconds(1))), "HISTORY_HEAD_MISMATCH")
        assert sequence(env) == 4 and len(rows(env)) == 4
        # (c) a refused, failing or unconfirmed head advance poisons the instance; the file stays one row ahead
        outcomes = (("refused", lambda old, new: False, "HISTORY_TRUSTED_HEAD_UPDATE_REFUSED"),
                    ("failing", lambda old, new: (_ for _ in ()).throw(RuntimeError("SECRET-CAS")),
                     "HISTORY_TRUSTED_HEAD_UPDATE_FAILED"),
                    ("unconfirmed", lambda old, new: True, "HISTORY_TRUSTED_HEAD_CHANGED"))
        for label, cas, code in outcomes:
            case = build(hroot, deployment_id="invented-cas-" + label, name="live-history-cas-" + label)
            record(case, 0)
            case.head.compare_and_set = cas
            refused(lambda: record(case, 1), code)
            refused(lambda: case.h.provider(obs(case, case.T(1) + seconds(2))), "HISTORY_RECONCILIATION_REQUIRED")
            refused(lambda: record(case, 1), "HISTORY_RECONCILIATION_REQUIRED")
            assert len(rows(case)) == 3 and sequence(case) == 2
            refused(lambda: restart(case), "HISTORY_HEAD_MISMATCH")


def test_store_paths_are_isolated_and_link_free():
    with head_root() as hroot:
        env = build(hroot, bind=False)
        home, root = Path(os.environ["TRADEGEN_HOME"]), state_root().absolute()
        make = lambda root: LiveHistory(env.e.program, env.e.protocol, env.e.profile, window=env.window, root=root,
                                        clock=env.clock, trusted_head=env.head)
        (home / "other").mkdir()
        refused(lambda: make(home / "other"), "HISTORY_STORE_ROOT_MISMATCH")
        (home / "elsewhere").mkdir()
        F.directory_link(home / STORE_DIRECTORY, home / "elsewhere")
        refused(lambda: make(root), "HISTORY_STORE_PATH_REFUSED")
        refused(lambda: HistoryChain(root=root, window=env.window), "HISTORY_STORE_PATH_REFUSED")
        refused(lambda: env.h.bind(env.d), "HISTORY_STORE_PATH_REFUSED")
        assert not any((home / "elsewhere").iterdir())
