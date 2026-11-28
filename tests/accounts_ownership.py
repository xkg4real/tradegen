"""Synthetic Upbit OQ12 bootstrap and mixed-ownership journal regressions."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from execution_accounts.model import content_digest
from execution_accounts.ownership import (PersonalOrderRecord, SignedPersonalOrders, personal_order_terms,
                                          reconcile_first_order)
from execution_control.capability import digest, plain
from execution_control.controller import _fill_key
from execution_control.model import InstrumentRules, Order, order_digest
from execution_control.store import GENESIS, Journal
from tests import accounts_provider as F
from tests.compliance_fixtures import temp_home


def review(*orders, scope=F.SCOPE, wrong_key=False, changed_original=False):
    key = Ed25519PrivateKey.generate()
    public = (Ed25519PrivateKey.generate() if wrong_key else key).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    records = []
    for order in orders:
        original = ("reviewed synthetic statement for " + order.order_id).encode()
        record = PersonalOrderRecord(account_scope=scope, order_id=order.order_id,
            terms_sha256=personal_order_terms(scope, order), source_sha256=hashlib.sha256(original).hexdigest())
        records.append((record, key.sign(record.message()), b"changed" if changed_original else original))
    return SignedPersonalOrders(public, tuple(records))


def assess(b, events=(), **kw):
    account = b.accounts[0]
    options = dict(now=F.NOW, account_sha256=content_digest(account),
                   journal_head=events[-1]["row_sha256"] if events else GENESIS)
    return reconcile_first_order(account, events, **(options | kw))


def audit_journal(*items, scope=F.SCOPE):
    """Build an actual validated journal snapshot without a controller, key or dispatch."""
    with temp_home():
        journal = Journal()
        with journal.transaction() as tx:
            for row, fills, status in items:
                order = Order(client_id=row.client_id, venue="upbit", account_scope=scope, market="spot",
                    symbol=row.symbol, side=row.side, quantity=row.quantity, limit_price=row.limit_price,
                    quote_krw=D(1))
                rules = InstrumentRules(venue="upbit", market="spot", symbol=row.symbol, lot_size=D("0.00001"),
                    tick_size=D("1"), min_quantity=D(0), min_notional_krw=D(0), fee_fraction=D(0),
                    asof=F.NOW, source_digest=F.SHA)
                identity = dict(client_id=row.client_id, order_digest=order_digest(order))
                arguments = dict(request_digest=F.SHA, permit_digest=F.SHA)
                tx.append("reserved", identity | arguments | dict(order=plain(order), rules=plain(rules),
                          session_id="fixture", trade_date=""), now=F.NOW)
                tx.append("dispatching", identity | arguments, now=F.NOW)
                if status == "UNKNOWN":
                    tx.append("unknown", identity | dict(venue_order_id="", metadata=[]), now=F.NOW)
                    continue
                response = dict(venue_order_id=row.order_id, metadata=[])
                tx.append("acknowledged", identity | response, now=F.NOW)
                for f in fills:
                    tx.append("fill", identity | dict(fill_key=_fill_key(f), fill_digest=digest(f), fill=plain(f)),
                              now=F.NOW)
                tx.append("reconciled", identity | response | dict(status=status,
                          filled_quantity=str(row.filled_quantity)), now=F.NOW)
        return journal.snapshot()


def test_flat_bootstrap_requires_fresh_matching_account_and_complete_physical_journal():
    b = F.bundle()
    ok = assess(b)
    assert ok.origin_ready and not ok.execution_ready and ok.unreserved_cash_krw == D("1000000")
    for kw in (dict(now=F.NOW+timedelta(seconds=31)), dict(account_sha256="1"*64),
               dict(journal_head="2"*64)):
        result = assess(b, **kw)
        assert not result.origin_ready and result.unreserved_cash_krw is None


def test_personal_fills_holdings_and_resting_orders_are_separated_without_changing_account_risk():
    purchase = F.order(client="")
    personal_buy = F.order(oid="rest-buy", client="manual-1", filled=D(0), status="open")
    personal_sell = F.order(oid="rest-sell", client="", side="sell", quantity=D(1), filled=D(0), status="open")
    b = F.bundle(orders=(purchase, personal_buy, personal_sell), fills=(F.fill(),), cash=D(999798), units=D(2))
    ok = assess(b, personal_source=review(purchase, personal_buy, personal_sell))
    assert ok.origin_ready and not ok.execution_ready and ok.app_open_count == 0 and ok.personal_open_count == 2
    assert ok.personal_open_order_ids == ("rest-buy", "rest-sell") and not ok.app_open_order_ids
    assert ok.whole_account_equity_krw == D(1000038) and ok.unreserved_cash_krw == D(999598)
    assert ok.personal_reserved_cash_krw == D(200)
    p, = ok.positions
    assert (p.app_units, p.personal_units, p.free_app_units) == (0, 2, 0)
    assert "rest-buy" not in repr(ok) and "999598" not in repr(ok)


def test_unmatched_empty_or_app_looking_identifier_never_establishes_origin():
    for client in ("", "lr1234567890-lookslikeours", "personal"):
        row = F.order(oid="unresolved", client=client, filled=D(0), status="open")
        b = F.bundle(orders=(row,))
        result = assess(b)
        assert result.reason == "OWNERSHIP_ORDER_ORIGIN_UNKNOWN" and result.unknown_order_ids == (row.order_id,)
        assert result.unknown_order_count == 1 and result.unreserved_cash_krw is None
        assert row.order_id not in repr(result)


def test_review_binds_scoped_venue_order_and_immutable_terms_but_survives_partial_fill():
    row = F.order(filled=D(0), status="open")
    source = review(row)
    partial = F.order(filled=D(1), status="partial")
    b = F.bundle(orders=(partial,), fills=(F.fill(quantity=D(1)),), units=D(1), cash=D(999898))
    assert assess(b, personal_source=source).origin_ready
    assert assess(b, personal_source=review(row, wrong_key=True)).reason == "OWNERSHIP_REVIEW_INVALID"
    assert assess(b, personal_source=review(row, changed_original=True)).reason == "OWNERSHIP_REVIEW_INVALID"
    assert not assess(b, personal_source=review(row, scope="different")).origin_ready
    for bad in (replace(row, limit_price=D(102)), replace(row, client_id="another"),
                replace(row, quantity=D(3)), replace(row, side="sell")):
        assert assess(b, personal_source=review(bad)).reason == "OWNERSHIP_REVIEW_INVALID"
    assert not assess(b, personal_source=review(row, row)).origin_ready


def test_authenticated_collector_net_balance_and_lock_are_not_deducted_twice():
    from tests import accounts_collector as C
    source = C.SyntheticSource(with_order=True)
    source.detail.update(state="wait", volume="2", remaining_volume="1", locked="10005", identifier="")
    source.balances[0].update(balance="79990", locked="10005")
    account, = C.collect(source).bundle.accounts
    row, = (r for p in account.pages if p.kind == "orders" for r in p.rows)
    ok = reconcile_first_order(account, (), now=C.NOW, account_sha256=content_digest(account),
        journal_head=GENESIS, personal_source=review(row, scope=C.SCOPE))
    assert ok.origin_ready and ok.personal_reserved_cash_krw == 10005
    assert ok.unreserved_cash_krw == 79990 and ok.whole_account_equity_krw == 99995
    assert ok.positions[0].free_app_units == 0 and ok.positions[0].personal_units == 1


def test_independent_authenticated_origin_reader_can_supply_original_without_an_owner_signature():
    row = F.order(filled=D(0), status="open")
    original = b"fixture of a separately authenticated personal-channel report"

    class Source:
        def read_personal_orders(self, scope, ids):
            assert scope == F.SCOPE and ids == (row.order_id,)
            return ((PersonalOrderRecord(account_scope=scope, order_id=row.order_id,
                    terms_sha256=personal_order_terms(scope, row), source_sha256=hashlib.sha256(original).hexdigest()),
                    original),)

    assert assess(F.bundle(orders=(row,)), personal_source=Source()).personal_open_count == 1


def test_account_pagination_and_exact_fill_coverage_are_required():
    held = F.bundle(fills=(F.fill(),), cash=D(999798), units=D(2))
    assert assess(held).reason == "OWNERSHIP_FILL_WITHOUT_ORDER"
    account = held.accounts[0]
    missing = F.change_account(held, pages=tuple(p for p in account.pages if p.kind != "orders"))
    assert not assess(missing).origin_ready
    row = F.order(filled=D(0), status="open")
    open_b = F.bundle(orders=(row,))
    net = replace(open_b.accounts[0].balances[0], settled=D(999800))
    assert assess(F.change_account(open_b, balances=(net,)), personal_source=review(row)).reason == (
        "OWNERSHIP_CASH_BASIS_UNCONFIRMED")


def test_journaled_order_origin_uses_both_ids_exact_terms_fills_and_scope():
    app = F.order(client="old-profile-namespace")
    f = F.fill()
    events = audit_journal((app, (f,), "FILLED"))
    b = F.bundle(orders=(app,), fills=(f,), cash=D(999798), units=D(2))
    ok = assess(b, events)
    assert ok.origin_ready and ok.positions[0].free_app_units == 2 and ok.positions[0].personal_units == 0
    assert assess(b, events, personal_source=review(app)).reason == "OWNERSHIP_ORDER_CONFLICT"
    assert not assess(b, events[:-1], journal_head=events[-1]["row_sha256"]).origin_ready
    changed = dict(events[-1], data=events[-1]["data"] | {"filled_quantity": "0"})
    assert assess(b, events[:-1]+(changed,)).reason == "OWNERSHIP_JOURNAL_INVALID"
    wrong = replace(f, fill_id="another-fill")
    assert assess(F.page_rows(b, "fills", (wrong,)), events).reason == "OWNERSHIP_FILL_CONFLICT"
    assert assess(F.page_rows(b, "orders", (replace(app, client_id="different"),)), events).reason == (
        "OWNERSHIP_JOURNAL_ORDER_UNRESOLVED")
    assert not assess(b, audit_journal((app, (f,), "FILLED"), scope="other-account")).origin_ready


def test_unknown_dispatch_or_missing_app_order_defers_new_entries():
    row = F.order(oid="app-open", client="app-ns", filled=D(0), status="open")
    app = audit_journal((row, (), "ACKNOWLEDGED"))
    b = F.bundle(orders=(row,))
    good = assess(b, app)
    assert good.origin_ready and good.app_open_order_ids == ("app-open",) and good.unreserved_cash_krw == 999800
    assert not assess(F.bundle(), app).origin_ready
    unknown = audit_journal((row, (), "UNKNOWN"))
    assert not assess(b, unknown, personal_source=review(row)).origin_ready
    pruned = tuple(dict(r) for r in app[1:])
    assert not assess(b, pruned).origin_ready


def test_mixed_same_coin_hand_sale_charges_free_app_first_and_keeps_both_owners_in_equity():
    app = F.order(oid="app", client="a", quantity=D(2), filled=D(2))
    hand = F.order(oid="hand", client="", quantity=D(3), filled=D(3))
    sell = F.order(oid="hand-sell", client="", side="sell", quantity=D(1), filled=D(1))
    a = F.fill(order="app", fid="app-fill", fee=D(0), at=F.NOW-timedelta(seconds=3))
    p = F.fill(order="hand", fid="owner-fill", quantity=D(3), fee=D(0), at=F.NOW-timedelta(seconds=2))
    sale = F.fill(order="hand-sell", fid="sold", side="sell", quantity=D(1), fee=D(0),
                  at=F.NOW-timedelta(seconds=1))
    events = audit_journal((app, (a,), "FILLED"))
    b = F.bundle(orders=(app, hand, sell), fills=(a, p, sale), units=D(4), cash=D(999600))
    ok = assess(b, events, personal_source=review(hand, sell))
    assert ok.origin_ready and ok.whole_account_equity_krw == 1000080
    pos, = ok.positions
    assert (pos.app_units, pos.free_app_units, pos.personal_units) == (1, 1, 3)
    tied = F.page_rows(b, "fills", (p, a, replace(sale, executed_at=a.executed_at)))
    assert assess(tied, events, personal_source=review(hand, sell)).reason == "OWNERSHIP_FILL_SEQUENCE_UNRESOLVED"


def test_locked_app_sales_are_subtracted_even_with_large_personal_inventory_and_historical_ambiguity_refuses():
    a = F.fill(order="app", fid="app-fill", quantity=D(2), fee=D(0), at=F.NOW-timedelta(seconds=3))
    p = F.fill(order="owner", fid="p-fill", quantity=D(8), fee=D(0), at=F.NOW-timedelta(seconds=2))
    app = F.order(oid="app", client="a")
    hand = F.order(oid="owner", client="", quantity=D(8), filled=D(8))
    locked = F.order(oid="locked", client="apped", side="sell", filled=D(0), status="open")
    personal = F.order(oid="owed", client="", side="sell", quantity=D(5), filled=D(0), status="open")
    events = audit_journal((app, (a,), "FILLED"), (locked, (), "ACKNOWLEDGED"))
    b = F.bundle(orders=(app, hand, locked, personal), fills=(a, p), units=D(10), cash=D(999000))
    ok = assess(b, events, personal_source=review(hand, personal))
    assert ok.origin_ready and ok.positions[0].free_app_units == 0 and ok.positions[0].personal_units == 8
    sale = F.order(oid="hand-sold", client="", side="sell", quantity=D(1), filled=D(1))
    f = F.fill(order="hand-sold", fid="sold", side="sell", quantity=D(1), fee=D(0), at=F.NOW-timedelta(seconds=1))
    b = F.bundle(orders=(app, hand, locked, personal, sale), fills=(a, p, f), units=D(9), cash=D(999100))
    assert assess(b, events, personal_source=review(hand, personal, sale)).reason == "OWNERSHIP_LOCK_HISTORY_REQUIRED"
