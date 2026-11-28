"""Offline full-minute candle checks. Test authority is synthetic and cannot grant production finality."""
from dataclasses import replace
from datetime import timedelta

from execution.upbit_inquiry import candle_params
from execution_accounts.candle_audit import VerifiedMinuteFinality, audit_minutes
from execution_accounts.model import content_digest
from tests.accounts_path_checks import Archive, MARKET, MINUTE, NOW, SCOPE, receipt, refused, tick, window

STEP = timedelta(minutes=1)
SHA, STUDY = "a"*64, "b"*64


def candle(start, low=None, high=None, *, at=NOW, row_at=None):
    rows = [] if low is None else [dict(market=MARKET, unit=1,
        candle_date_time_utc=(row_at or start).strftime("%Y-%m-%dT%H:%M:%S"), low_price=low, high_price=high)]
    return receipt("/v1/candles/minutes/1", candle_params(MARKET, start+STEP, 1), rows, at=at)


def verified(challenge, raw):
    return VerifiedMinuteFinality(request_sha256=content_digest(challenge), authority_sha256=SHA,
        study_sha256=STUDY, final_after=challenge.minute_start+STEP+timedelta(seconds=3), verified_at=NOW)


def audit(paths, reads, **kwargs):
    return audit_minutes(paths, reads, market=MARKET, account_scope=SCOPE, first_minute=MINUTE, now=NOW,
                         **({"verify_finality":verified} | kwargs))


def test_full_minute_across_several_windows_checks_both_sides_at_low_price_only():
    src = Archive([tick(MINUTE, 5, 10), tick(MINUTE+timedelta(seconds=45), 9, 11), tick(MINUTE+STEP, 100, 12)])
    split = MINUTE + timedelta(seconds=30)
    paths = (window(src,end=split), window(src,start=split,end=MINUTE+STEP))
    r, = audit(paths,(candle(MINUTE, 4, 10),))
    assert r.status == "CHECKED" and [(f.kind,f.price) for f in r.findings] == [("CANDLE_LOW",4),("CANDLE_HIGH",4)]
    r, = audit(paths,(candle(MINUTE, 5, 9),))
    assert not r.findings and r.status == "CHECKED"
    r, = audit(paths,(candle(MINUTE, 5, 11),))
    assert len(r.findings) == 1 and r.findings[0].price == 5


def test_all_long_interval_minutes_are_checked_empty_price_is_never_invented():
    src = Archive([tick(MINUTE+STEP, 20, 8)])
    path = window(src, end=MINUTE+3*STEP)
    results = audit((path,), (candle(MINUTE, 7, 9), candle(MINUTE+STEP), candle(MINUTE+2*STEP)))
    assert tuple(r.status for r in results) == ("CHECKED",)*3
    assert [(f.kind,f.price) for r in results for f in r.findings] == [("CANDLE_MINUTE",7),("CANDLE_MINUTE",None)]
    assert results[0].findings[0].evidence_sha256 != results[1].findings[0].evidence_sha256


def test_missing_or_early_raw_and_unauthenticated_finality_can_never_make_a_finding():
    path = window(Archive([tick(MINUTE, 70, 1)]))
    r, = audit((path,), (None,))
    assert r.status == "MISSING_CANDLE_RECEIPT" and not r.findings
    raw = candle(MINUTE, 1, 5)
    for verifier in (None, lambda *_: None):
        r, = audit((path,), (raw,), verify_finality=verifier)
        assert r.status == "FINALITY_UNVERIFIED" and not r.findings
    for verifier in (lambda *_: True, lambda *_: {"candle_finality_proven":True}):
        refused("CANDLE_AUDIT_FINALITY_BINDING", lambda: audit((path,), (raw,), verify_finality=verifier))
    early = candle(MINUTE, 1, 5, at=MINUTE+STEP+timedelta(seconds=2))
    r, = audit((path,), (early,))
    assert r.status == "NEED_LATER_CAPTURE" and not r.findings


def test_both_receipt_and_server_clocks_must_reach_the_authenticated_boundary():
    path = window(Archive([tick(MINUTE, 5, 1)]))
    final_after = MINUTE + STEP + timedelta(seconds=3)
    raw = candle(MINUTE, 1, 5, at=final_after)
    for r in (replace(raw, received_at=final_after-timedelta(microseconds=1)),
              replace(raw, server_time=final_after-timedelta(microseconds=1))):
        checked, = audit((path,), (r,))
        assert checked.status == "NEED_LATER_CAPTURE" and not checked.findings
    checked, = audit((path,), (raw,))
    assert checked.status == "CHECKED" and checked.findings[0].kind == "CANDLE_LOW"


def test_wrong_minute_market_range_query_and_receipt_hash_are_never_compared():
    path = window(Archive([tick(MINUTE, 5, 1)]))
    raw = candle(MINUTE, 3, 8)
    r, = audit((path,), (candle(MINUTE,3,8,row_at=MINUTE-STEP),))
    assert r.status == "TARGET_MINUTE_NOT_RETURNED" and not r.findings
    refused("CANDLE_AUDIT_WRONG_MINUTE", lambda: audit((path,), (candle(MINUTE,3,8,row_at=MINUTE+STEP),)))
    refused("CANDLE_AUDIT_RECEIPT_BINDING",lambda: audit((path,), (replace(raw,params=candle_params("KRW-ETH",MINUTE+STEP,1)),)))
    refused("CANDLE_AUDIT_RECEIPT_BINDING",lambda: audit((path,), (replace(raw,params=candle_params(MARKET,MINUTE+STEP,2)),)))
    refused("CANDLE_AUDIT_RECEIPT_BINDING",lambda: audit((path,), (replace(raw,path="/v1/candles/days"),)))
    refused("COLLECTOR_RECEIPT_DIGEST_MISMATCH",lambda: audit((path,), (replace(raw,raw_body=b"[]"),)))


def test_finality_cannot_be_replayed_against_changed_candle_or_trade_capture():
    path = window(Archive([tick(MINUTE, 5, 1)]))
    got = []
    def remember(c,r):
        proof = verified(c,r)
        got.append(proof)
        return proof
    raw = candle(MINUTE,3,8)
    audit((path,), (raw,), verify_finality=remember)
    stale = lambda *_: got[0]
    refused("CANDLE_AUDIT_FINALITY_BINDING",lambda: audit((path,), (candle(MINUTE,4,8),), verify_finality=stale))
    other = window(Archive([tick(MINUTE,6,1)]))
    refused("CANDLE_AUDIT_FINALITY_BINDING",lambda: audit((other,), (raw,), verify_finality=stale))
    refused("CANDLE_AUDIT_FINALITY_TIME",lambda: audit((path,), (raw,),
        verify_finality=lambda c,r: replace(verified(c,r),final_after=MINUTE)))


def test_full_coverage_rejects_partial_overlapping_or_mutated_trade_windows():
    src = Archive([tick(MINUTE, 5, 1), tick(MINUTE+STEP, 7, 2)])
    path = window(src)
    raw = candle(MINUTE,2,10)
    partial = window(src,start=MINUTE+timedelta(seconds=1),end=MINUTE+STEP)
    refused("CANDLE_AUDIT_PATH_GAP_OR_SCOPE",lambda: audit((partial,), (raw,)))
    refused("CANDLE_AUDIT_PATH_GAP_OR_SCOPE",lambda: audit((path,path), (raw,)))
    refused("CANDLE_AUDIT_PATH_GAP_OR_SCOPE",lambda: audit((path,), (raw,candle(MINUTE+STEP))))
    refused("PATH_CHECK_WINDOW_REPLAY_MISMATCH",lambda: audit((replace(path,prints=()),), (raw,)))


def test_offline_receipt_literal_does_not_grant_a_network_call():
    from tests.accounts_guards import problems
    source = '"/v1/candles/minutes/1"'
    assert not problems(source, "candle_audit.py")
    assert problems(source, "other.py") and problems(source, "nested/candle_audit.py")
    assert problems('request("upbit","GET","/v1/candles/minutes/1",params)', "candle_audit.py")


def test_trade_seen_at_boundary_by_one_window_cannot_disappear_from_the_next():
    split = MINUTE + timedelta(seconds=30)
    src = Archive([tick(MINUTE, 5, 1), tick(split, 7, 2)])
    a = window(src, start=MINUTE, end=split)
    other = Archive([tick(MINUTE, 5, 1)])
    b = window(other, start=split, end=MINUTE+STEP)
    refused("CANDLE_AUDIT_PRINT_COVERAGE_CONTRADICTION", lambda: audit((a,b), (candle(MINUTE,5,7),)))
