"""Cross-venue checks begin with two independently replayed synthetic broker archives."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from execution_accounts.model import AccountBundle, CashBalance
from execution_accounts.okx_collector import collect_okx
from execution_accounts.provider import EvidenceError, assess_bundle, build_observation
from tests import accounts_kis_collector as kis
from tests import accounts_okx_collector as okx

D = Decimal


def _cash_only_kis(server_offset=0):
    # A KRW/USD account with no pre-existing shares or trades shares this
    # portfolio's first trading day. Cash from one venue never nets against the other.
    initial = kis._bundle()
    account = initial.accounts[0]
    pages = tuple(replace(p, rows=(), page_sha256="") for p in account.pages)
    observed = kis.NOW + timedelta(seconds=server_offset)
    account = replace(account, positions=(), pages=pages, server_time=observed,
                      balances=tuple(CashBalance(currency=b.currency, settled=b.amount, total=b.amount)
                                     for b in account.opening_cash))
    baseline = replace(initial.risk_baseline, first_trading_day=kis.NOW.date(),
                       prior_high_watermark=D("46100"), day_start_equity=D("46100"))
    bodies = kis._raw()
    for tr, out in (("TTTC8434R", "output1"), ("TTTS3012R", "output1"), ("TTTC0081R", "output1"),
                    ("TTTS3035R", "output"), ("CTRP6504R", "output1")):
        bodies[tr][out] = []
    bodies["TTTC8434R"]["output2"][0].update(dnca_tot_amt="100", nxdy_excc_amt="100", prvs_rcdl_excc_amt="100")
    bodies["CTRP6504R"]["output2"][0].update(frcr_dncl_amt_2="30", frcr_drwg_psbl_amt_1="30")
    source = kis.Archive(bodies=bodies, transform=lambda p: replace(p, receipt=replace(p.receipt, server_time=observed)))
    return kis._run(source, bundle=AccountBundle(accounts=(account,), risk_baseline=baseline)).bundle


def _okx_bundle(baseline, *, server_offset=0):
    now = kis.NOW
    args = okx.kwargs(now=now)
    args["risk_baseline"] = baseline
    source = okx.Archive(okx.fixture(now=now), now=now,
                         receipt_mutator=lambda r: replace(r, server_time=now + timedelta(seconds=server_offset)))
    return collect_okx(source, **args).bundle


def _refuses(bundle, reason):
    try:
        build_observation(bundle, now=kis.NOW)
    except EvidenceError as exc:
        assert exc.code == reason, (exc.code, reason)
    else:
        raise AssertionError("Expected " + reason)


def test_kis_and_okx_outputs_sum_whole_equity_with_independent_currency_and_spendable_scopes():
    a = _cash_only_kis()
    b = _okx_bundle(a.risk_baseline)
    together = AccountBundle(accounts=(*a.accounts, *b.accounts), risk_baseline=a.risk_baseline)
    obs = build_observation(together, now=kis.NOW)
    assert obs.risk.equity == D(100 + 30 * 1200) + D(6 * 1000) + D("0.9") * 5 * 1000
    assert obs.account_scopes == {"kis": kis.SCOPE, "okx": okx.SCOPE}
    assert obs.settled_cash_krw == {("kis", kis.SCOPE): D(100), ("okx", okx.SCOPE): D(6000)}
    assert obs.quote_rates_krw == {("kis", kis.SCOPE, "KRW"): D(1), ("kis", kis.SCOPE, "USD"): D(1200),
                                  ("okx", okx.SCOPE, "USDT"): D(1000)}
    assert obs.positions.exposure["okx"].reservations == {"fixtureA": 5000}
    assert obs.positions.exposure["kis"].reservations == {}
    status = assess_bundle(together, now=kis.NOW)
    assert status.account_count == 2 and status.fill_count == 1 and not status.execution_ready


def test_venue_receipts_individually_time_valid_but_clocks_diverge():
    a = _cash_only_kis(server_offset=40)
    b = _okx_bundle(a.risk_baseline, server_offset=-40)
    for bundle in (a, b):
        assert assess_bundle(bundle, now=kis.NOW).account_evidence_ready
    together = AccountBundle(accounts=(*a.accounts, *b.accounts), risk_baseline=a.risk_baseline)
    _refuses(together, "VENUE_CLOCK_DISAGREEMENT")


def test_cash_discrepancies_cannot_offset_across_venues():
    a = _cash_only_kis()
    b = _okx_bundle(a.risk_baseline)
    first, second = a.accounts[0], b.accounts[0]
    def alter(account, ccy, delta):
        balances = tuple(replace(row, total=row.total+delta, settled=row.settled+delta) if row.currency == ccy else row
                         for row in account.balances)
        return replace(account, balances=balances)
    # +1000 KRW at KIS and -1 USDT at OKX preserve total KRW equity arithmetically.
    together = AccountBundle(accounts=(alter(first, "KRW", D(1000)), alter(second, "USDT", D(-1))),
                             risk_baseline=a.risk_baseline)
    _refuses(together, "CASH_RECONCILIATION_MISMATCH")


def test_incompatible_first_day_history_cannot_pass_using_another_venue_anchor():
    prior = kis._run().bundle
    aligned = _cash_only_kis()
    later = _okx_bundle(aligned.risk_baseline)
    together = AccountBundle(accounts=(*prior.accounts, *later.accounts), risk_baseline=prior.risk_baseline)
    _refuses(together, "HISTORY_START_AFTER_FIRST_TRADING_DAY")
