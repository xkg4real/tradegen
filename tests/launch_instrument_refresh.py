"""Current terms and session renewal using invented receipts and fake E1 only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import format_datetime
import hashlib
import json
import os
from unittest.mock import patch

from execution import transport, upbit_inquiry
from execution_accounts import instrument_terms as T
from execution_control.model import Order, rules_digest
from execution_launch import instrument_refresh as R
from execution_launch.profile import preflight_profile, profile_contract_digest, profile_digest, rule_terms_digest
from execution_launch.runner import Runner
from tests.launch_profile import RULE, fixture_profile

D = Decimal
NOW = datetime(2026, 10, 23, 1, tzinfo=timezone.utc)


@contextmanager
def registries():
    with patch.dict(os.environ, {"UPBIT_ACCESS_KEY": "<unset>", "UPBIT_SECRET_KEY": "<unset>"}), \
         patch.object(T, "_ISSUED", {}), patch.object(T, "_OBSERVED_RULES", {}), \
         patch.object(T, "_AUTHORITIES", set()), patch.object(R, "_ISSUED", {}), \
         patch.object(R, "_HEADS", {}), patch.object(R, "_BOUND", {}), patch.object(R, "_USED", set()):
        yield


def authority(**changes):
    values = dict(account_scope="test-scope", symbol="KRW-BTC", lot_size=D("0.01"),
        min_quantity=D("0.01"), maximum_notional_krw=D("2000000"),
        provenance_sha256="d"*64, identity_binding_sha256="e"*64,
        valid_from=NOW-timedelta(days=1), valid_until=NOW+timedelta(days=1))
    return T.TermsAuthority(**(values | changes))


def profile(auth=None, now=NOW):
    auth = auth or authority()
    base = fixture_profile(now)
    return replace(base, account_scope=auth.account_scope, symbol=auth.symbol,
        instrument_rules=replace(base.instrument_rules, symbol=auth.symbol,
            lot_size=auth.lot_size, min_quantity=auth.min_quantity, source_digest=T.authority_digest(auth)))


def bodies(auth=None):
    auth = auth or authority()
    chance = {"bid_fee": "0.001", "ask_fee": "0.001", "maker_bid_fee": "0.001", "maker_ask_fee": "0.001",
        "market": {"id": auth.symbol, "state": "active", "order_sides": ["bid", "ask"],
            "bid_types": ["limit", "price"], "ask_types": ["limit", "market"],
            "bid": {"currency": "KRW", "min_total": "20"},
            "ask": {"currency": auth.symbol.split("-")[1], "min_total": "20"},
            "max_total": str(auth.maximum_notional_krw)},
        "bid_account": {"balance": "PRIVATE_FAKE_BALANCE"}}
    instruments = [{"market": auth.symbol, "tick_size": "1", "quote_currency": "KRW", "supported_levels": ["0", "1000"]}]
    return chance, instruments


def answer(body, now):
    raw = json.dumps(body, separators=(",", ":")).encode()
    return transport.Answer(body=body, server_utc=now, received_utc=now,
        sha256=hashlib.sha256(raw).hexdigest(), raw_body=raw)


def observed(now=NOW+timedelta(seconds=10), *, auth=None, chance=None, instruments=None, server=None):
    auth = auth or authority()
    default_chance, default_instruments = bodies(auth)
    answers = (answer(default_chance if chance is None else chance, now),
               answer(default_instruments if instruments is None else instruments, now))
    if server is not None:
        answers = tuple(replace(a, server_utc=server) for a in answers)
    with patch.object(T, "current_terms", return_value=answers):
        return T.E1UpbitTermsSource(authority=auth, clock=lambda: now).read()


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        assert "PRIVATE_FAKE_BALANCE" not in str(exc)
        return
    raise AssertionError("expected current-terms refusal")


def universe_authority(**changes):
    values = dict(account_scope="test-scope", universe_sha256=RULE, lot_size=D("0.01"),
        min_quantity=D("0.01"), maximum_notional_krw=D("2000000"),
        provenance_sha256="d"*64, identity_binding_sha256="e"*64,
        valid_from=NOW-timedelta(days=1), valid_until=NOW+timedelta(days=1))
    return T.UniverseTermsAuthority(**(values | changes))


def universe_bodies(symbol, max_total="2000000", tick="1"):
    chance, instruments = bodies()
    chance["market"].update(id=symbol, max_total=max_total)
    chance["market"]["ask"]["currency"] = symbol.split("-")[1]
    instruments[0].update(market=symbol, tick_size=tick)
    return chance, instruments


def universe_observed(symbol="KRW-BTC", now=NOW+timedelta(seconds=10), *, auth=None, max_total="2000000", tick="1"):
    chance, instruments = universe_bodies(symbol, max_total, tick)
    with patch.object(T, "current_terms", return_value=(answer(chance, now), answer(instruments, now))) as call:
        observation = T.E1UpbitTermsSource(authority=auth or universe_authority(), clock=lambda: now).read(symbol)
    call.assert_called_once_with(symbol)
    return observation

def test_same_terms_refresh_is_new_observation_and_preserves_contract_and_policy():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        assert R.validate_renewal(r, previous_profile=p, now=o.checked_at) == r.profile
        assert r.profile.instrument_rules.asof == o.chance_receipt.received_at
        assert profile_digest(p) != profile_digest(r.profile)
        assert profile_contract_digest(p) == profile_contract_digest(r.profile)
        assert rule_terms_digest(p.instrument_rules) == rule_terms_digest(r.profile.instrument_rules)
        assert r.profile.policy is p.policy and r.profile.conventions is p.conventions
        assert r.profile.instrument_rules.source_digest == T.authority_digest(o.authority)
        assert r.profile.instrument_rules.source_digest != o.evidence_digest
        assert o.evidence_digest not in repr(r) and "PRIVATE_FAKE_BALANCE" not in repr(o)


def test_pure_decoding_serialized_copy_and_fabricated_renewal_are_not_issued():
    with registries():
        p = profile(); o = observed()
        parsed = T.parse_term_receipts(authority=o.authority, chance_receipt=o.chance_receipt,
            instruments_receipt=o.instruments_receipt, requested_at=o.requested_at,
            checked_at=o.checked_at, now=o.checked_at)
        assert parsed == o
        refused(lambda: R.renew_profile(p, parsed, now=o.checked_at), "TERMS_OBSERVATION_NOT_ISSUED")
        refused(lambda: R.renew_profile(p, replace(o), now=o.checked_at), "TERMS_OBSERVATION_NOT_ISSUED")
        r = R.renew_profile(p, o, now=o.checked_at)
        refused(lambda: R.validate_renewal(replace(r), now=o.checked_at), "RENEWAL_NOT_ISSUED")


def test_relabelled_timestamp_and_mutated_receipt_cannot_renew():
    with registries():
        p = profile(); o = observed()
        object.__setattr__(o.rules, "asof", o.rules.asof+timedelta(seconds=1))
        refused(lambda: R.renew_profile(p, o, now=o.checked_at), "TERMS_OBSERVATION_CHANGED")
        o = observed()
        object.__setattr__(o.chance_receipt, "raw_body", b'{}')
        refused(lambda: R.renew_profile(p, o, now=o.checked_at), "TERMS_RECEIPT_INVALID")


def test_replay_fork_and_nonmonotonic_server_observation_refuse():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        refused(lambda: R.renew_profile(p, o, now=o.checked_at), "RENEWAL_STALE_PROFILE_OR_FORK")
        refused(lambda: R.renew_profile(r.profile, o, now=o.checked_at), "RENEWAL_OBSERVATION_NOT_NEWER")
        stale_server = observed(o.checked_at+timedelta(seconds=10), server=o.checked_at)
        refused(lambda: R.renew_profile(r.profile, stale_server, now=stale_server.checked_at),
                "RENEWAL_RECEIPT_REPLAY_OR_CLOCK_ROLLBACK")
        later = observed(o.checked_at+timedelta(seconds=20))
        second = R.renew_profile(r.profile, later, now=later.checked_at)
        assert R.rules_binding_matches(r.old_rules_digest, second.profile.instrument_rules,
                                      account_scope=p.account_scope, now=later.checked_at)
        refused(lambda: R.validate_renewal(r, now=later.checked_at), "RENEWAL_NOT_CURRENT")
        assert not R.rules_binding_matches("0"*64, second.profile.instrument_rules,
                                          account_scope=p.account_scope, now=later.checked_at)


def test_freshness_boundary_future_and_authority_expiry_preserve_refusal():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        R.validate_renewal(r, now=o.rules.asof+timedelta(minutes=5))
        refused(lambda: R.validate_renewal(r, now=o.rules.asof+timedelta(minutes=5, microseconds=1)),
                "TERMS_STALE_OR_FUTURE")
        assert not R.rules_binding_matches(r.old_rules_digest, r.profile.instrument_rules,
            account_scope=p.account_scope, now=o.rules.asof+timedelta(minutes=6))
        refused(lambda: T.validate_issued_observation(o, now=o.checked_at-timedelta(microseconds=1)),
                "TERMS_AUTHORITY_EXPIRED_OR_FUTURE")
        refused(lambda: observed(auth=authority(valid_until=NOW)), "TERMS_AUTHORITY_EXPIRED_OR_FUTURE")
        refused(lambda: observed(server=NOW-timedelta(minutes=2)), "TERMS_SERVER_CLOCK_MISMATCH")


def test_scope_identity_source_and_economic_changes_never_become_a_renewal():
    with registries():
        p = profile(); o = observed()
        for changes, code in (({"account_scope": "other-scope"}, "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH"),
            ({"symbol": "KRW-ETH"}, "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH"),
            ({"venue": "okx"}, "RENEWAL_VENUE_UNSUPPORTED"),
            ({"venue": "kis"}, "RENEWAL_VENUE_UNSUPPORTED")):
            refused(lambda changes=changes: R.renew_profile(replace(p, **changes), o, now=o.checked_at), code)
        for field, value in (("fee_fraction", D("0.002")), ("tick_size", D("2")),
                             ("lot_size", D("0.1")), ("source_digest", "f"*64)):
            changed = replace(p, instrument_rules=replace(p.instrument_rules, **{field: value}))
            refused(lambda: R.renew_profile(changed, o, now=o.checked_at), "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")
        changed = observed(auth=authority(identity_binding_sha256="f"*64))
        refused(lambda: R.renew_profile(p, changed, now=changed.checked_at), "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")


def test_terms_parser_rejects_halted_missing_asymmetric_and_changed_maximum():
    with registries():
        for transform, code in (
            (lambda c: c["market"].update(state="halted"), "TERMS_MARKET_INACTIVE"),
            (lambda c: c["market"].update(id="KRW-ETH"), "TERMS_MARKET_MISMATCHED"),
            (lambda c: c["market"].update(ask_types=["market"]), "TERMS_LIMIT_ORDERS_UNSUPPORTED"),
            (lambda c: c["market"]["bid"].update(currency="USDT"), "TERMS_CURRENCY_MISMATCH"),
            (lambda c: c["market"]["ask"].update(min_total="21"), "TERMS_ASYMMETRIC_MINIMUM_UNSUPPORTED"),
            (lambda c: c["market"].update(max_total="1000000"), "TERMS_MAXIMUM_CHANGED"),
            (lambda c: c.update(ask_fee="0.002"), "TERMS_ASYMMETRIC_FEE_UNSUPPORTED"),
            (lambda c: c.pop("maker_bid_fee"), "TERMS_EXACT_NUMBER_REQUIRED"),
            (lambda c: c.update(bid_fee=float("nan")), "TERMS_RECEIPT_INVALID")):
            c, _ = bodies(); transform(c)
            refused(lambda: observed(chance=c), code)
        for i, code in (([], "TERMS_SINGLE_INSTRUMENT_REQUIRED"),
            ([{"market":"KRW-ETH","tick_size":"1"}], "TERMS_SINGLE_INSTRUMENT_REQUIRED"),
            ([{"market":"KRW-BTC","tick_size":"0","quote_currency":"KRW","supported_levels":["0"]}], "TERMS_NUMBER_INVALID"),
            ([{"market":"KRW-BTC","tick_size":True,"quote_currency":"KRW","supported_levels":["0"]}], "TERMS_EXACT_NUMBER_REQUIRED")):
            refused(lambda: observed(instruments=i), code)


def test_receipt_envelope_hash_request_order_and_query_are_checked():
    with registries():
        o = observed()
        for receipt, code in ((replace(o.chance_receipt, params=(("market", "KRW-ETH"),)), "TERMS_RECEIPT_SCOPE_MISMATCH"),
            (replace(o.chance_receipt, account_scope="other"), "TERMS_RECEIPT_SCOPE_MISMATCH"),
            (replace(o.chance_receipt, received_at=o.checked_at+timedelta(seconds=1)), "TERMS_RECEIPT_OUTSIDE_REQUEST"),
            (replace(o.chance_receipt, sha256="a"*64), "TERMS_RECEIPT_INVALID")):
            refused(lambda: T.parse_term_receipts(authority=o.authority, chance_receipt=receipt,
                instruments_receipt=o.instruments_receipt, requested_at=o.requested_at,
                checked_at=o.checked_at, now=o.checked_at), code)
        refused(lambda: T.parse_term_receipts(authority=o.authority, chance_receipt=o.chance_receipt,
            instruments_receipt=o.instruments_receipt, requested_at=o.requested_at-timedelta(seconds=31),
            checked_at=o.checked_at, now=o.checked_at), "TERMS_REQUEST_WINDOW_INVALID")


def test_raw_payload_clock_error_and_provider_exception_are_redacted():
    with registries():
        with patch.object(T, "current_terms", side_effect=RuntimeError("PRIVATE_FAKE_BALANCE")):
            refused(lambda: T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW).read(),
                    "TERMS_INQUIRY_FAILED")
        c, i = bodies(); good = answer(i, NOW)
        for bad, code in ((replace(answer(c, NOW), server_utc=None), "TERMS_SERVER_TIME_REQUIRED"),
            (replace(answer(c, NOW), received_utc=NOW+timedelta(seconds=1)), "TERMS_RECEIPT_OUTSIDE_REQUEST")):
            with patch.object(T, "current_terms", return_value=(bad, good)):
                refused(lambda: T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW).read(), code)


def test_maximum_notional_of_refreshed_terms_is_enforced_without_rounding():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        order = Order(client_id="synthetic-buy", account_scope="test-scope", venue="upbit", market="spot",
                      symbol="KRW-BTC", side="buy", quantity=D("2000"), limit_price=D("1000"), quote_krw=D("1"))
        R.validate_observed_order(order, r.profile.instrument_rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(order, quantity=D("2000.01")),
            r.profile.instrument_rules, now=o.checked_at), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")


def test_runner_accepts_issued_renewal_only_and_keeps_runtime_mutation_guard():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        runner = Runner(profile=p, quote_provider=lambda now: None, account_provider=lambda now: None)
        assert runner.refresh_instrument_rules(r, now=o.checked_at) is r.profile
        assert runner.profile == r.profile and runner._profile_digest == profile_digest(r.profile)
        refused(lambda: runner.refresh_instrument_rules(r, now=o.checked_at), "RENEWAL_PREVIOUS_PROFILE_MISMATCH")
        later = observed(o.checked_at+timedelta(seconds=10))
        second = R.renew_profile(r.profile, later, now=later.checked_at)
        runner._lock.acquire()
        try:
            refused(lambda: runner.refresh_instrument_rules(second, now=later.checked_at),
                    "RUNNER_CONCURRENT_TICK_REFUSED")
        finally:
            runner._lock.release()
        runner.refresh_instrument_rules(second, now=later.checked_at)
        runner.profile = replace(runner.profile, account_scope="other-scope")
        refused(lambda: runner.refresh_instrument_rules(second, now=later.checked_at), "RUNNER_PROFILE_MUTATED")


def test_actual_e1_fake_transport_uses_two_pinned_gets_and_only_chance_authenticates():
    from tests import execution_fixtures as EF
    from tests import compliance_fixtures as CF
    with registries(), CF.temp_home() as home, EF.isolated(home), EF.fake_keys():
        c, i = bodies()
        routes = {("GET", upbit_inquiry.TERMS_CHANCE_PATH): lambda call: (200,
            {"Date": format_datetime(NOW, usegmt=True)}, json.dumps(c).encode()),
            ("GET", upbit_inquiry.TERMS_INSTRUMENTS_PATH): lambda call: (200,
            {"Date": format_datetime(NOW, usegmt=True)}, json.dumps(i).encode())}
        with EF.serve(routes) as calls:
            o = T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW).read()
        assert len(calls) == 2 and all(call["method"] == "GET" for call in calls)
        assert calls[0]["path"] == upbit_inquiry.TERMS_CHANCE_PATH
        assert calls[1]["path"] == upbit_inquiry.TERMS_INSTRUMENTS_PATH
        assert "Authorization" in calls[0]["headers"] and "Authorization" not in calls[1]["headers"]
        assert calls[0]["url"].endswith("?market=KRW-BTC")
        assert calls[1]["url"].endswith("?markets=KRW-BTC")
        assert all(call["json_body"] is None for call in calls)
        T.validate_issued_observation(o, now=NOW)


def test_fixed_terms_helper_rejects_paths_queries_other_markets_before_transport():
    with patch.object(upbit_inquiry, "request", side_effect=AssertionError("not reached")) as call:
        for value in (None, 1, "KRW-BTC&market=KRW-ETH", "KRW-BTC,KRW-ETH", "BTC-USDT", "KRW-KRW", "/v1/orders"):
            try:
                upbit_inquiry.current_terms(value)
            except transport.InquiryRefused:
                pass
            else:
                raise AssertionError("invalid scope admitted")
        assert not call.called


def test_new_chain_does_not_extend_owner_session_expiry_or_accept_fabricated_preparation():
    from core.compliance import model as M
    from execution_control.session import prepare_session
    from tests import compliance_fixtures as CF
    from tests.control_session import signed_control, selected, verification, refused as session_refused
    with registries(), signed_control(prepare=False) as env:
        auth = authority(account_scope="fixture-account", lot_size=env.rules.lot_size,
                         min_quantity=env.rules.min_quantity)
        p = profile(auth=auth, now=env.now)
        p = replace(p, instrument_rules=replace(p.instrument_rules,
            min_notional_krw=env.rules.min_notional_krw, tick_size=env.rules.tick_size,
            fee_fraction=env.rules.fee_fraction))
        env.rules = p.instrument_rules
        plan, inputs, seed = selected(env.now)
        env.prepared = prepare_session(journal=env.journal, session_id="fixture", selected_plan=plan,
            inputs=inputs, positions=env.observation.positions, policy=env.policy, instrument_rules=env.rules,
            now=env.now, selection_seed_hex=seed, account_scope="fixture-account", market="spot", quote_currency="KRW",
            clock=lambda: env.now, positions_asof=env.observation.asof)
        env.session_id = env.prepared.session_id
        CF.sign(env.key, "session_armed", {"session_id": env.session_id}, M.iso_utc(env.now))
        original = env.prepared
        later = env.now+timedelta(minutes=6)
        c, i = bodies(auth); c["market"]["bid"]["min_total"] = c["market"]["ask"]["min_total"] = "5000"
        o = observed(later, auth=auth, chance=c, instruments=i)
        r = R.renew_profile(p, o, now=later)
        env.rules = r.profile.instrument_rules
        verification(env, now=later)
        assert env.prepared is original and env.prepared.expires_at == env.now+timedelta(minutes=30)
        session_refused(lambda: verification(env, prepared=replace(env.prepared), now=later))
        # Even a new real observation cannot extend the originally armed session.
        end = env.prepared.expires_at
        last = observed(end, auth=auth, chance=c, instruments=i)
        end_renewal = R.renew_profile(r.profile, last, now=end)
        env.rules = end_renewal.profile.instrument_rules
        session_refused(lambda: verification(env, now=end))


def test_initial_issued_terms_enforce_maximum_and_reject_unissued_timestamp():
    with registries():
        o = observed()
        order = Order(client_id="synthetic-initial", account_scope="test-scope", venue="upbit", market="spot",
                      symbol="KRW-BTC", side="buy", quantity=D("2000"), limit_price=D("1000"), quote_krw=D("1"))
        R.validate_observed_order(order, o.rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(order, quantity=D("2000.01")),
            o.rules, now=o.checked_at), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
        unissued = replace(o.rules, asof=o.rules.asof+timedelta(seconds=1))
        refused(lambda: R.validate_observed_order(order, unissued, now=unissued.asof),
                "TERMS_UNISSUED_RULE_SNAPSHOT")
        refused(lambda: R.validate_observed_order(replace(order, account_scope="other-scope"),
            o.rules, now=o.checked_at), "TERMS_UNISSUED_RULE_SNAPSHOT")


def test_stopped_runner_can_refresh_for_protective_exit_without_restarting_entries():
    with registries():
        p = profile(); runner = Runner(profile=p, quote_provider=lambda now: None, account_provider=lambda now: None)
        runner.stop()
        later = NOW+timedelta(minutes=6)
        o = observed(later); r = R.renew_profile(p, o, now=later)
        runner.refresh_instrument_rules(r, now=later)
        assert runner.stopped and runner.profile is r.profile
        result = runner.tick(now=later)
        assert result.status == "stopped" and result.reasons == ("RUNNER_STOPPED",)


def test_native_instrument_quote_currency_and_levels_are_not_assumed():
    with registries():
        for transform, code in ((lambda i: i[0].update(quote_currency="USDT"), "TERMS_CURRENCY_MISMATCH"),
            (lambda i: i[0].pop("quote_currency"), "TERMS_CURRENCY_MISMATCH"),
            (lambda i: i[0].update(supported_levels=["1000"]), "TERMS_NATIVE_BOOK_UNSUPPORTED"),
            (lambda i: i[0].update(supported_levels=[0]), "TERMS_NATIVE_BOOK_UNSUPPORTED")):
            _, i = bodies(); transform(i)
            refused(lambda: observed(instruments=i), code)


def test_controller_checks_observed_maximum_before_any_account_or_order_work_on_both_sides():
    from execution_control.controller import Controller
    with registries():
        o = observed()
        for side in ("buy", "sell"):
            order = Order(client_id="synthetic-controller", account_scope="test-scope", venue="upbit",
                          market="spot", symbol="KRW-BTC", side=side, quantity=D("2000.01"),
                          limit_price=D("1000"), quote_krw=D("1"))
            # No controller instance/state is needed: the bound must refuse first.
            refused(lambda: Controller._authorize(None, None, order, o.rules, "synthetic", o.checked_at,
                {}, set(), set()), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")


def test_simultaneous_renewers_cannot_fork_one_contract_head():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    with registries():
        p = profile(); observations = [observed(), observed(NOW+timedelta(seconds=20))]
        gate = Barrier(2)
        def run(o):
            gate.wait()
            try:
                return R.renew_profile(p, o, now=o.checked_at)
            except R.RenewalError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, observations))
        assert sum(type(v) is R.RulesRenewal for v in results) == 1
        assert results.count("RENEWAL_STALE_PROFILE_OR_FORK") == 1


def test_mutated_prior_chain_cannot_smuggle_an_unrelated_prepared_rules_digest():
    with registries():
        p = profile(); o = observed(); r = R.renew_profile(p, o, now=o.checked_at)
        object.__setattr__(r, "original_rule_digests", r.original_rule_digests | {"f"*64})
        later = observed(o.checked_at+timedelta(seconds=10))
        refused(lambda: R.renew_profile(r.profile, later, now=later.checked_at), "RENEWAL_RECORD_CHANGED")


def test_restart_source_registration_rejects_saved_snapshot_until_new_read():
    with registries():
        p = profile()
        with patch.object(T, "current_terms", side_effect=AssertionError("construction does no I/O")) as call:
            source = T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW)
            assert not call.called
        refused(lambda: T.observation_for_rules(p.instrument_rules, account_scope=p.account_scope, now=NOW),
                "TERMS_UNISSUED_RULE_SNAPSHOT")
        c, i = bodies()
        with patch.object(T, "current_terms", return_value=(answer(c, NOW), answer(i, NOW))):
            current = source.read()
        assert T.observation_for_rules(current.rules, account_scope=p.account_scope, now=NOW).rules == current.rules


def test_missing_credential_names_refuse_before_fixed_helper_or_fallback():
    with registries(), patch.object(upbit_inquiry, "request", side_effect=AssertionError("no request")) as call:
        source = T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW)
        for name in ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"):
            with patch.dict(os.environ):
                os.environ.pop(name)
                refused(source.read, "TERMS_ENV_CREDENTIAL_NAMES_REQUIRED")
        assert not call.called


def test_universe_profile_renews_across_a_tick_change_and_keeps_its_contract():
    with registries():
        rule = hashlib.sha256(b"fixture-universe-rule").hexdigest()
        p = replace(profile(), universe_rule_sha256=rule)
        stale = replace(p, instrument_rules=replace(p.instrument_rules, tick_size=D("5")))
        o = observed()
        r = R.renew_profile(stale, o, now=o.checked_at)
        assert r.profile.instrument_rules.tick_size == D("1") and r.profile.universe_rule_sha256 == rule
        assert profile_contract_digest(r.profile) == profile_contract_digest(stale)
        assert R.validate_renewal(r, previous_profile=stale, now=o.checked_at) == r.profile
        fee = replace(p, instrument_rules=replace(p.instrument_rules, fee_fraction=D("0.002")))
        refused(lambda: R.renew_profile(fee, o, now=o.checked_at), "RENEWAL_ECONOMIC_OR_SOURCE_CHANGE")


def test_v1_authority_digest_is_byte_identical_and_v2_is_a_separate_form():
    assert T.authority_digest(authority()) == "728bd2d73418bcd1211500b20934924a28e468648419be126f73ecec3b1e2b04"
    v2 = T.authority_digest(universe_authority())
    assert v2 != T.authority_digest(authority())
    assert T.authority_digest(universe_authority(universe_sha256="f"*64)) != v2
    assert T.authority_digest(universe_authority(maximum_notional_krw=D("1000000"))) != v2
    refused(lambda: T.authority_digest(universe_authority(universe_sha256="KRW-BTC")), "TERMS_SOURCE_DIGEST_REQUIRED")
    refused(lambda: T.authority_digest(universe_authority(account_scope="bad scope")), "TERMS_SCOPE_INVALID")
    refused(lambda: T.authority_digest(object()), "TERMS_AUTHORITY_REQUIRED")


def test_v2_reads_the_symbol_named_at_read_time_and_v1_keeps_its_own():
    with registries():
        o = universe_observed("KRW-ETH")
        assert (o.rules.symbol, o.rules.source_digest) == ("KRW-ETH", T.authority_digest(universe_authority()))
        assert o.chance_receipt.params == (("market", "KRW-ETH"),)
        assert o.instruments_receipt.params == (("markets", "KRW-ETH"),)
        source = T.E1UpbitTermsSource(authority=universe_authority(), clock=lambda: NOW)
        for bad in (None, "BTC", "KRW-KRW", "KRW-eth"):
            refused(lambda bad=bad: source.read(bad), "TERMS_KRW_SYMBOL_REQUIRED")
        refused(lambda: T.E1UpbitTermsSource(authority=authority(), clock=lambda: NOW).read("KRW-ETH"),
                "TERMS_SYMBOL_MISMATCH")
        later = NOW+timedelta(seconds=20)
        c, i = bodies()
        with patch.object(T, "current_terms", return_value=(answer(c, later), answer(i, later))):
            assert T.E1UpbitTermsSource(authority=authority(), clock=lambda: later).read("KRW-BTC").rules.symbol == "KRW-BTC"
        assert observed(NOW+timedelta(seconds=30)).rules.symbol == "KRW-BTC"


def test_v2_parse_takes_its_symbol_only_from_one_exact_chance_query():
    with registries():
        o = universe_observed("KRW-ETH")
        for params in ((), (("market", "KRW-KRW"),), (("markets", "KRW-ETH"),), (("market", "KRW-BTC"),),
                       (("market", "KRW-ETH"), ("market", "KRW-BTC"))):
            refused(lambda params=params: T.parse_term_receipts(authority=o.authority,
                chance_receipt=replace(o.chance_receipt, params=params), instruments_receipt=o.instruments_receipt,
                requested_at=o.requested_at, checked_at=o.checked_at, now=o.checked_at),
                "TERMS_RECEIPT_SCOPE_MISMATCH")
        later = NOW+timedelta(seconds=20)
        c, i = universe_bodies("KRW-ETH")
        c["market"]["id"] = "KRW-XRP"
        with patch.object(T, "current_terms", return_value=(answer(c, later), answer(i, later))):
            refused(lambda: T.E1UpbitTermsSource(authority=universe_authority(), clock=lambda: later).read("KRW-ETH"),
                    "TERMS_MARKET_MISMATCHED")


def test_v2_records_the_observed_maximum_caps_buys_and_lets_a_held_coin_sell_above_the_cap():
    with registries():
        auth = universe_authority()                                    # buy cap 2,000,000
        o = universe_observed("KRW-ETH", auth=auth, max_total="3000000")
        assert o.observed_maximum_krw == D("3000000") and T.within_buy_cap(o)
        sell = Order(client_id="synthetic-sell", account_scope="test-scope", venue="upbit", market="spot",
                     symbol="KRW-ETH", side="sell", quantity=D("2500"), limit_price=D("1000"), quote_krw=D("1"))
        R.validate_observed_order(sell, o.rules, now=o.checked_at)      # 2,500,000: above the cap, a sell
        refused(lambda: R.validate_observed_order(replace(sell, side="buy"), o.rules, now=o.checked_at),
                "RENEWAL_BUY_ABOVE_UNIVERSE_CAP")
        R.validate_observed_order(replace(sell, side="buy", quantity=D("2000")), o.rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(sell, quantity=D("3000.01")), o.rules, now=o.checked_at),
                "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
        low = universe_observed("KRW-XRP", o.checked_at+timedelta(seconds=10), auth=auth, max_total="1000000")
        assert low.observed_maximum_krw == D("1000000") and not T.within_buy_cap(low)
        v1 = observed(o.checked_at+timedelta(seconds=20))
        assert v1.observed_maximum_krw == D("2000000") and T.within_buy_cap(v1)
        refused(lambda: T.within_buy_cap(None), "TERMS_OBSERVATION_REQUIRED")
        copy = T.parse_term_receipts(authority=o.authority, chance_receipt=o.chance_receipt,
            instruments_receipt=o.instruments_receipt, requested_at=o.requested_at,
            checked_at=o.checked_at, now=o.checked_at)
        assert copy == o


def universe_profile(auth=None, symbol="KRW-BTC"):
    auth = auth or universe_authority()
    base = fixture_profile(NOW)
    return replace(base, account_scope=auth.account_scope, symbol=symbol, time_in_force="ioc",
        universe_rule_sha256=RULE, instrument_rules=replace(base.instrument_rules, symbol=symbol,
            lot_size=auth.lot_size, min_quantity=auth.min_quantity, source_digest=T.authority_digest(auth)))


def test_universe_renewal_moves_to_another_coin_only_with_the_flag_and_keeps_its_contract():
    with registries():
        auth = universe_authority()
        p = universe_profile(auth)
        o = universe_observed("KRW-ETH", auth=auth, tick="5")
        refused(lambda: R.renew_profile(p, o, now=o.checked_at), "RENEWAL_ACCOUNT_OR_SYMBOL_MISMATCH")
        refused(lambda: R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=1),
                "RENEWAL_SYMBOL_CHANGE_REFUSED")
        r = R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True)
        assert (r.profile.symbol, r.profile.instrument_rules.symbol) == ("KRW-ETH", "KRW-ETH")
        assert r.profile.instrument_rules.tick_size == D("5") and r.profile.time_in_force == "ioc"
        assert profile_contract_digest(r.profile) == profile_contract_digest(p) == r.contract_digest
        assert R.validate_renewal(r, previous_profile=p, now=o.checked_at) == r.profile
        assert preflight_profile(r.profile, now=o.checked_at).profile_complete
        back = universe_observed("KRW-BTC", o.checked_at+timedelta(seconds=10), auth=auth)
        again = R.renew_profile(r.profile, back, now=back.checked_at, allow_symbol_change=True)
        assert again.profile.symbol == "KRW-BTC" and again.contract_digest == r.contract_digest


def test_a_fixed_profile_refuses_the_symbol_change_flag_itself():
    with registries():
        p = profile(); o = observed()
        refused(lambda: R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=True),
                "RENEWAL_SYMBOL_CHANGE_REFUSED")
        assert R.renew_profile(p, o, now=o.checked_at, allow_symbol_change=False).profile.symbol == "KRW-BTC"


def test_a_coin_below_the_cap_is_not_buyable_but_a_held_coin_still_renews_and_sells():
    with registries():
        auth = universe_authority()
        p = universe_profile(auth)
        o = universe_observed("KRW-BTC", auth=auth, max_total="1000000")
        assert not T.within_buy_cap(o)                                 # left out of the allow-list (PR 4e)
        r = R.renew_profile(p, o, now=o.checked_at)
        sell = Order(client_id="synthetic-exit", account_scope="test-scope", venue="upbit", market="spot",
                     symbol="KRW-BTC", side="sell", quantity=D("900"), limit_price=D("1000"), quote_krw=D("1"),
                     time_in_force="ioc")
        R.validate_observed_order(sell, r.profile.instrument_rules, now=o.checked_at)
        refused(lambda: R.validate_observed_order(replace(sell, side="buy", quantity=D("1500")),
            r.profile.instrument_rules, now=o.checked_at), "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")


def test_order_validation_refuses_an_inflated_issued_or_renewed_observed_maximum():
    for renewed in (False, True):
        with registries():
            auth = universe_authority()
            observation = universe_observed("KRW-ETH", auth=auth, max_total="3000000")
            rules = observation.rules
            if renewed:
                renewal = R.renew_profile(universe_profile(auth), observation,
                    now=observation.checked_at, allow_symbol_change=True)
                rules = renewal.profile.instrument_rules
            sell = Order(client_id="synthetic-tamper-sell", account_scope="test-scope",
                venue="upbit", market="spot", symbol="KRW-ETH", side="sell",
                quantity=D("3500"), limit_price=D("1000"), quote_krw=D("1"), time_in_force="ioc")
            refused(lambda: R.validate_observed_order(sell, rules, now=observation.checked_at),
                    "RENEWAL_ORDER_ABOVE_OBSERVED_MAXIMUM")
            # Bypass frozen dataclass assignment as an adversarial mutation of an issued object.
            object.__setattr__(observation, "observed_maximum_krw", D("4000000"))
            refused(lambda: R.validate_observed_order(sell, rules, now=observation.checked_at),
                    "TERMS_OBSERVATION_CHANGED")
