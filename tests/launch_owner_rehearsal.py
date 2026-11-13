"""Standalone owner rehearsal with synthetic signatures, account receipts and temporary roots."""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from io import StringIO
from email.utils import format_datetime
from urllib.parse import parse_qsl, urlsplit
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.upbit_collector import E1UpbitSource
from execution_control.capability import digest
from execution_control.dry_run import DryRunAdapter
from execution_control.store import GENESIS
from execution_launch import strategy as evaluator
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import history_head_name
from execution_launch.driver import DeploymentWindow
from execution_launch.live_history import HistoryChain
from tests.launch_account_interval import ANCHOR, CONVENTIONS, COVERAGE, FEES, FakeUpbit, at, seed
from tests.launch_baseline_head import head_root
from tests.launch_coordinator import FakeTime, reviewed, memoized_pure_loads
from tests.launch_review_auth import document, review_fixture
from tests.launch_windows_owner_authority import signed_home
from tools.owner import rehearsal as R

D = Decimal


def plain(value):
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, dict): return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    return value


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected refusal " + code)


def write_audit(folder, state, window):
    documents = []
    for kind in sorted(R._REQUIRED_KINDS | {"fill_fees"}):
        path = folder / (kind + ".txt")
        raw = ("SYNTHETIC TEST ONLY: reviewed " + kind).encode()
        path.write_bytes(raw)
        documents.append({"kind": kind, "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
    hashes = {d["kind"]: d["sha256"] for d in documents}
    body = {"schema_version": 1, "kind": "tradegen-flat-account-rehearsal-audit/1",
        "account_scope": state.account_scope, "deployment_window_digest": digest(window),
        "baseline_anchor_sha256": state.anchor_sha256,
        "opening_anchor": plain(asdict(replace(ANCHOR, source_sha256=hashes["opening_anchor"]))),
        "coverage": plain(asdict(replace(COVERAGE, source_sha256=hashes["coverage_review"]))),
        "trade_fees": [plain(asdict(replace(f, source_sha256=hashes["fill_fees"]))) for f in FEES],
        "source_documents": documents, "terms_authority": None}
    return body


@contextmanager
def isolated_evaluations():
    """Give this fixture its own genuine evaluator records and restore its caller.

    Shared acceptance fixtures may retain issued results. Keep those exact
    objects, retain the production issuance cap inside this fixture, and avoid
    leaving a newly cached shared review fixture backed by removed records.
    """
    previous = dict(evaluator._EVALUATED)
    shared_review_was_cached = review_fixture.cache_info().currsize > 0
    evaluator._EVALUATED.clear()
    try:
        yield
    finally:
        if not shared_review_was_cached:
            review_fixture.cache_clear()
        evaluator._EVALUATED.clear()
        evaluator._EVALUATED.update(previous)


@contextmanager
def fixture(*, baseline_age_seconds=20):
    t0 = at(26, 20)
    # The full acceptance wrapper removes all key names. These are synthetic
    # presence markers only; keys.read below remains a hard refusal.
    with isolated_evaluations(), \
            patch.dict(os.environ, {"UPBIT_ACCESS_KEY": "<unset>", "UPBIT_SECRET_KEY": "<unset>"}), \
            memoized_pure_loads(), signed_home() as home, head_root() as heads, tempfile.TemporaryDirectory() as path:
        folder = Path(path).resolve()
        window = DeploymentWindow(deployment_id="owner-rehearsal", start=t0+timedelta(seconds=60),
                                  end=t0+timedelta(seconds=180))
        current = reviewed(t0, window)
        exchange = FakeUpbit()
        state, store, _, _ = seed(home, exchange, FEES, t0-timedelta(seconds=baseline_age_seconds), day_start=D("100000"),
            high=D("100100"), loss=D(0), realized=D(90), day_open=D(0), previous=None,
            conventions=replace(CONVENTIONS, recovery_cutoff_seconds=None))
        BaselineHead(root=heads, name="account-baseline", chain=CheckpointChain(store)).initialize_reviewed_head(state.state_digest)
        BaselineHead(root=heads, name=history_head_name(window),
                     chain=HistoryChain(root=home, window=window)).initialize_reviewed_head(GENESIS)
        audit = write_audit(folder, state, window)
        raw_audit = json.dumps(audit, sort_keys=True).encode()
        (folder / "account-audit.json").write_bytes(raw_audit)
        review = json.loads(current.files["review.json"])["body"]
        review["audit_sha256"] = hashlib.sha256(raw_audit).hexdigest()
        current.files["review.json"] = document(review)
        for name, text in current.files.items(): (folder / name).write_text(text)
        (folder / "window.json").write_text(json.dumps(plain(asdict(window))))
        config = {"schema_version": 1, "kind": "tradegen-flat-account-rehearsal/1",
            **{key: str(folder / (key + ".json")) for key in ("profile", "program", "protocol", "capture", "review", "window")},
            "account_audit": str(folder / "account-audit.json"), "evaluated_at": current.evaluated_at.isoformat(),
            "monitor_until": (t0+timedelta(seconds=210)).isoformat(), "state_root": str(home), "head_root": str(heads)}
        config_path = folder / "rehearsal.json"
        config_path.write_text(json.dumps(config))
        fake = FakeTime(t0)
        exchange.clock = fake.clock
        calls = []

        def fake_send(method, url, **kwargs):
            parsed = urlsplit(url)
            assert method == "GET" and parsed.scheme == "https" and parsed.netloc == "api.upbit.com"
            calls.append(parsed.path)
            receipt = exchange.fetch(parsed.path, tuple(parse_qsl(parsed.query)))
            return 200, {"Date": format_datetime(receipt.server_time.astimezone(timezone.utc), usegmt=True)}, receipt.raw_body
        def pace(seconds): fake.now += timedelta(seconds=seconds)
        with patch("execution.transport._send", side_effect=fake_send), \
                patch("execution.transport._headers", return_value=({}, None, None)), \
                patch("execution.transport._sleep", side_effect=pace), \
                patch("execution.transport._clock", side_effect=fake.clock), \
                patch("execution.keys.read", side_effect=AssertionError("credential read forbidden")), \
                patch("execution_orders.transport._send", side_effect=AssertionError("order network forbidden")):
            yield SimpleNamespace(home=home, heads=heads, folder=folder, config=config, path=config_path,
                fake=fake, state=state, window=window, audit=audit, raw_audit=raw_audit, current=current,
                calls=calls, exchange=exchange)


def test_help_and_invalid_cli_never_load_config_or_source():
    with patch.object(R, "build_rehearsal", side_effect=AssertionError("unexpected construction")):
        for args, expected in ((["--help"], 0), (["--config", "private", "--live"], 2),
                               (["--module", "private.dynamic"], 2)):
            output = StringIO()
            with redirect_stdout(output): code = R.main(args)
            assert code == expected
            if expected == 2:
                assert "private" not in output.getvalue() and not json.loads(output.getvalue())["execution_ready"]


def test_unsigned_complete_flags_and_unknown_live_options_are_not_configuration():
    with fixture() as e:
        for change in ({"mode": "controlled"}, {"complete": True}, {"source_factory": "private.module"}):
            refused(lambda: R.load_config(json.dumps(e.config | change).encode()), "REHEARSAL_CONFIG_SCHEMA_INVALID")
        invalid = e.audit | {"complete": True}
        refused(lambda: R.parse_account_audit(json.dumps(invalid).encode()), "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")
        invalid = json.loads(e.raw_audit)
        invalid["coverage"]["identity_binding"] = True
        refused(lambda: R.parse_account_audit(json.dumps(invalid).encode()), "REHEARSAL_SOURCE_OBLIGATIONS_REQUIRED")
        assert e.calls == []


def test_fixed_standalone_composition_bootstraps_actual_flat_collector_with_no_order_transport():
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        assert e.calls == []
        c = runtime._coordinator
        assert c._runner.mode == "rehearsal"
        assert all(type(adapter) is DryRunAdapter for adapter in c._controller.adapters.values())
        result = runtime.bootstrap()
        assert result["published_units"] == 1 and result["account_source"] == "", result
        assert e.calls and all(path.startswith("/v1/") for path in e.calls)
        assert all(not adapter.requests for adapter in c._controller.adapters.values())
        refused(runtime.prepare, "OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED")
        assert runtime.close()["closed"] and not result["execution_ready"]


def test_changed_signed_audit_refuses_before_any_account_or_public_request():
    with fixture() as e:
        altered = json.loads(e.raw_audit)
        altered["opening_anchor"]["cash_krw"] = "99999"
        (e.folder / "account-audit.json").write_text(json.dumps(altered))
        refused(lambda: R.build_rehearsal(str(e.path), clock=e.fake.clock), "REHEARSAL_SIGNED_AUDIT_MISMATCH")
        assert e.calls == []


def test_unreviewed_source_document_change_refuses_before_any_request():
    with fixture() as e:
        source_path = Path(e.audit["source_documents"][0]["path"])
        source_path.write_text("PRIVATE_UNREVIEWED_REPLACEMENT")
        refused(lambda: R.build_rehearsal(str(e.path), clock=e.fake.clock), "REHEARSAL_SOURCE_DOCUMENT_CHANGED")
        assert e.calls == []


def test_missing_independent_head_or_stale_baseline_is_never_seeded_or_repaired():
    with fixture() as e:
        (e.heads / "account-baseline" / "head.json").unlink()
        before = (e.home / "execution-baseline" / "checkpoint.json").read_bytes()
        refused(lambda: R.build_rehearsal(str(e.path), clock=e.fake.clock), "HEAD_NOT_INITIALIZED")
        assert not (e.heads / "account-baseline" / "head.json").exists()
        assert (e.home / "execution-baseline" / "checkpoint.json").read_bytes() == before and e.calls == []
    with fixture() as e:
        e.fake.now += timedelta(seconds=11)
        refused(lambda: R.build_rehearsal(str(e.path), clock=e.fake.clock), "REHEARSAL_BASELINE_STALE_OR_FUTURE")
        assert e.calls == []


def test_held_inventory_remains_a_flat_evidence_refusal_without_head_advancement():
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        before = (e.heads / "account-baseline" / "head.json").read_bytes()
        e.exchange.balances.append({"currency": "BTC", "balance": "0.1", "locked": "0"})
        report = runtime.bootstrap()
        assert report["account_source"] and report["new_entry_blocked"] and report["published_units"] == 0
        assert (e.heads / "account-baseline" / "head.json").read_bytes() == before
        assert all(not adapter.requests for adapter in runtime._coordinator._controller.adapters.values())
        runtime.close()


def test_fence_expiry_is_checked_before_each_read_and_latches_the_runtime():
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        c = runtime._coordinator
        # The fixed wrapper checks time before reaching even the fake E1 request.
        source = c._account_prefetch.__closure__
        wrapped = next(cell.cell_contents for cell in source if type(cell.cell_contents) is R._AccountSource)
        e.fake.now = datetime.fromisoformat(e.config["monitor_until"]) + timedelta(seconds=1)
        refused(lambda: wrapped.fetch("/v1/accounts", ()), "REHEARSAL_ACCOUNT_FENCE_EXPIRED_OR_FUTURE")
        assert e.calls == []
        e.fake.now -= timedelta(seconds=10)
        refused(lambda: wrapped.fetch("/v1/accounts", ()), "REHEARSAL_READ_AUTHORITY_LATCHED")
        assert e.calls == []
        runtime.close()


def test_source_document_symlink_and_float_money_are_not_accepted():
    with fixture() as e:
        raw = json.loads(e.raw_audit)
        raw["opening_anchor"]["cash_krw"] = 100000
        refused(lambda: R.parse_account_audit(json.dumps(raw).encode()), "REHEARSAL_EXACT_AMOUNT_REQUIRED")
        audit = R.parse_account_audit(e.raw_audit)
        first = Path(audit.source_documents[0][1])
        target = first.with_suffix(".original.txt")
        first.rename(target)
        first.symlink_to(target)
        try:
            R.verify_source_documents(audit)
        except ValueError:
            pass
        else:
            raise AssertionError("linked private proof accepted")
        assert e.calls == []


def test_authority_check_crossing_fence_refuses_before_read_and_latches():
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                       if type(cell.cell_contents) is R._AccountSource)
        e.fake.now = datetime.fromisoformat(e.config["monitor_until"]) - timedelta(seconds=1)
        v = wrapped._guard._composition.verifiers
        original = v._authority_provider

        def slow_authority(now):
            result = original(now)
            e.fake.now += timedelta(seconds=2)
            return result

        with patch.object(v, "_authority_provider", slow_authority):
            refused(lambda: wrapped.fetch("/v1/accounts", ()), "COLLECTOR_AUTHENTICATED_READ_FAILED")
        assert e.calls == []
        refused(lambda: wrapped.fetch("/v1/accounts", ()), "REHEARSAL_READ_AUTHORITY_LATCHED")
        runtime.close()


def test_no_positive_authority_cache_accepts_a_changed_review_on_next_read():
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                       if type(cell.cell_contents) is R._AccountSource)
        verifier = wrapped._guard._composition.verifiers
        # Identical clock: a previous successful construction cannot authorize this read.
        with patch.object(verifier, "_authority_provider", side_effect=R.RehearsalError("REHEARSAL_REVIEW_REVOKED")):
            refused(lambda: wrapped.fetch("/v1/accounts", ()), "COLLECTOR_AUTHENTICATED_READ_FAILED")
        assert e.calls == []
        runtime.close()


def test_transport_guards_nest_restore_and_refuse_before_headers_without_private_text():
    from execution import transport as T
    calls = []

    def outer(stage): calls.append(("outer", stage))
    def inner(stage):
        calls.append(("inner", stage))
        raise ValueError("PRIVATE_ACCOUNT_SENTINEL")
    with patch.object(T, "_headers", return_value=({}, None, None)) as headers, \
            patch.object(T, "_send", return_value=(200, {}, b"[]")) as send, \
            patch.object(T, "_sleep"), T.inquiry_clock(lambda: at(26, 20)):
        with T.inquiry_guard(outer):
            with T.inquiry_guard(inner):
                try:
                    T.request("upbit", "GET", "/v1/accounts")
                except T.InquiryRefused as exc:
                    assert str(exc) == "E1_GUARD_REFUSED"
                else:
                    raise AssertionError("nested guard was shadowed")
            assert not headers.called and not send.called
            assert calls == [("outer", "before_headers"), ("inner", "before_headers")]
            T.request("upbit", "GET", "/v1/accounts")
        before = len(calls)
        T.request("upbit", "GET", "/v1/accounts")
        assert len(calls) == before and headers.call_count == send.call_count == 2
        assert calls[2:] == [("outer", stage) for stage in
                             ("before_headers", "before_send", "after_response", "after_wait")]


def test_transport_guard_rechecks_fence_after_headers_and_response():
    from execution import transport as T
    for delayed_phase in ("headers", "response"):
        with fixture() as e:
            runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
            wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                           if type(cell.cell_contents) is R._AccountSource)
            end = datetime.fromisoformat(e.config["monitor_until"])
            e.fake.now = end - timedelta(seconds=1)

            def headers(*args, **kwargs):
                if delayed_phase == "headers": e.fake.now = end + timedelta(seconds=1)
                return {}, None, None
            def send(*args, **kwargs):
                e.fake.now = end + timedelta(seconds=1)
                return 200, {}, b"[]"
            with patch.object(T, "_headers", side_effect=headers) as built, \
                    patch.object(T, "_send", side_effect=send) as sent, patch.object(T, "_sleep"), \
                    T.inquiry_clock(e.fake.clock), T.inquiry_guard(wrapped._guard.transport_check):
                try:
                    T.request("upbit", "GET", "/v1/accounts")
                except T.InquiryRefused as exc:
                    assert str(exc) == "E1_GUARD_REFUSED"
                else:
                    raise AssertionError("late request or response admitted")
                assert built.call_count == 1 and sent.call_count == (delayed_phase == "response")
            refused(wrapped._guard.check, "REHEARSAL_READ_AUTHORITY_LATCHED")
            runtime.close()


def test_transport_retry_wait_expiring_fence_prevents_second_header_and_send():
    from execution import transport as T
    import requests
    for connection_error in (False, True):
        with fixture() as e:
            runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
            wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                           if type(cell.cell_contents) is R._AccountSource)
            e.fake.now = datetime.fromisoformat(e.config["monitor_until"]) - timedelta(seconds=1)

            def send(*args, **kwargs):
                if connection_error: raise requests.exceptions.ConnectionError("PRIVATE_PROVIDER_SENTINEL")
                return 503, {}, b"{}"
            def wait(seconds): e.fake.now += timedelta(seconds=seconds)
            with patch.object(T, "_headers", return_value=({}, None, None)) as built, \
                    patch.object(T, "_send", side_effect=send) as sent, patch.object(T, "_sleep", side_effect=wait), \
                    T.inquiry_clock(e.fake.clock), T.inquiry_guard(wrapped._guard.transport_check):
                try:
                    T.request("upbit", "GET", "/v1/accounts")
                except T.InquiryRefused as exc:
                    assert str(exc) == "E1_GUARD_REFUSED"
                else:
                    raise AssertionError("expired retry proceeded")
                assert built.call_count == sent.call_count == 1
            runtime.close()


def test_transport_retry_reauthenticates_current_owner_before_second_key_access():
    from execution import transport as T
    with fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                       if type(cell.cell_contents) is R._AccountSource)
        v = wrapped._guard._composition.verifiers
        original = v._authority_provider
        sent_count = 0

        def authenticate(now):
            if sent_count: raise ValueError("PRIVATE_REVOKED_AUTHORITY")
            return original(now)
        def send(*args, **kwargs):
            nonlocal sent_count
            sent_count += 1
            return 503, {}, b"{}"
        with patch.object(v, "_authority_provider", authenticate), \
                patch.object(T, "_headers", return_value=({}, None, None)) as built, \
                patch.object(T, "_send", side_effect=send), patch.object(T, "_sleep"), \
                T.inquiry_clock(e.fake.clock), T.inquiry_guard(wrapped._guard.transport_check):
            try:
                T.request("upbit", "GET", "/v1/accounts")
            except T.InquiryRefused as exc:
                assert str(exc) == "E1_GUARD_REFUSED"
            else:
                raise AssertionError("stale authority permitted retry")
            assert built.call_count == sent_count == 1
        runtime.close()


def test_both_terms_gets_are_individually_guarded_before_credentials():
    from execution import transport as T
    from execution_accounts.instrument_terms import E1UpbitTermsSource
    from tests import launch_instrument_refresh as TF
    with TF.registries(), fixture() as e:
        runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
        wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                       if type(cell.cell_contents) is R._AccountSource)
        v = wrapped._guard._composition.verifiers
        original = v._authority_provider
        sent = []
        authority = TF.authority(account_scope=e.state.account_scope,
            valid_from=e.fake.now-timedelta(days=1), valid_until=e.fake.now+timedelta(days=1))
        source = R._TermsSource(E1UpbitTermsSource(authority=authority, clock=e.fake.clock), wrapped._guard)

        def authenticate(now):
            if sent: raise ValueError("PRIVATE_SECOND_GET_REVOKED")
            return original(now)
        def send(method, url, **kwargs):
            sent.append(url)
            return 200, {}, b"{}"
        with patch.object(v, "_authority_provider", authenticate), \
                patch.object(T, "_headers", return_value=({}, None, None)) as built, \
                patch.object(T, "_send", side_effect=send), patch.object(T, "_sleep"):
            refused(source.read, "TERMS_INQUIRY_FAILED")
            assert len(sent) == built.call_count == 1 and "/v1/orders/chance" in sent[0]
        refused(wrapped._guard.check, "REHEARSAL_READ_AUTHORITY_LATCHED")
        runtime.close()


def test_current_authority_is_loaded_once_per_request_and_slow_collections_still_refuse():
    for seconds_per_load in (1.5, 4.0):
        with fixture(baseline_age_seconds=0) as e:
            runtime = R.build_rehearsal(str(e.path), clock=e.fake.clock)
            wrapped = next(cell.cell_contents for cell in runtime._coordinator._account_prefetch.__closure__
                           if type(cell.cell_contents) is R._AccountSource)
            v = wrapped._guard._composition.verifiers
            original = v._authority_provider
            original_head = (e.heads / "account-baseline" / "head.json").read_bytes()
            start = e.fake.now
            loads = []

            def slow_current_authority(now):
                authority = original(now)
                loads.append(now)
                e.fake.now += timedelta(seconds=seconds_per_load)
                return authority
            with patch.object(v, "_authority_provider", slow_current_authority):
                report = runtime.bootstrap()
            assert len(loads) == len(e.calls) > 0, (len(loads), len(e.calls))
            elapsed = e.fake.now - start
            if seconds_per_load == 1.5:
                assert elapsed <= timedelta(seconds=30), elapsed
                assert report["published_units"] == 1 and report["account_source"] == "", report
                assert (e.heads / "account-baseline" / "head.json").read_bytes() != original_head
            else:
                assert elapsed > timedelta(seconds=30), elapsed
                assert report["published_units"] == 0 and report["account_source"] and report["new_entry_blocked"], report
                assert (e.heads / "account-baseline" / "head.json").read_bytes() == original_head
            runtime.close()


def test_the_audit_carries_a_v1_or_a_v2_terms_authority_and_the_profile_picks_its_own():
    from execution_accounts import instrument_terms as T
    rule = hashlib.sha256(b"fixture-universe-rule").hexdigest()
    with fixture() as e:
        body = json.loads(e.raw_audit)
        terms_doc = hashlib.sha256(b"SYNTHETIC TEST ONLY: reviewed instrument_terms").hexdigest()
        body["source_documents"].append({"kind": "instrument_terms", "path": str(e.folder / "instrument_terms.txt"),
                                         "sha256": terms_doc})
        identity = next(d["sha256"] for d in body["source_documents"] if d["kind"] == "credential_identity")
        v2 = T.UniverseTermsAuthority(account_scope=body["account_scope"], universe_sha256=rule, lot_size=D("0.01"),
            min_quantity=D("0.01"), maximum_notional_krw=D("2000000"), provenance_sha256=terms_doc,
            identity_binding_sha256=identity, valid_from=e.fake.now-timedelta(days=1),
            valid_until=e.fake.now+timedelta(days=1))
        v1 = T.TermsAuthority(symbol="KRW-BTC", **{k: v for k, v in asdict(v2).items() if k != "universe_sha256"})

        def raw(**authorities):
            return json.dumps(body | {k: plain(asdict(v)) for k, v in authorities.items()}).encode()
        audit = R.parse_account_audit(raw(universe_terms_authority=v2))
        assert audit.universe_terms_authority == v2 and audit.terms_authority is None
        fixed = R.parse_account_audit(raw(terms_authority=v1))
        assert fixed.terms_authority == v1 and fixed.universe_terms_authority is None
        assert R.parse_account_audit(e.raw_audit).universe_terms_authority is None     # the old key set still parses
        refused(lambda: R.parse_account_audit(raw(terms_authority=v1, universe_terms_authority=v2)),
                "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        refused(lambda: R.parse_account_audit(raw(universe_terms_authority=replace(v2, identity_binding_sha256="f"*64))),
                "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        bad = json.loads(raw(universe_terms_authority=v2))
        bad["universe_terms_authority"]["symbol"] = "KRW-BTC"
        refused(lambda: R.parse_account_audit(json.dumps(bad).encode()), "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")

        def profile(universe, symbol, authority):
            return SimpleNamespace(universe_rule_sha256=universe, symbol=symbol,
                                   instrument_rules=SimpleNamespace(source_digest=T.authority_digest(authority)))
        assert R._terms_authority(profile(rule, "KRW-ETH", v2), audit) == v2
        refused(lambda: R._terms_authority(profile(None, "KRW-BTC", v2), audit), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        refused(lambda: R._terms_authority(profile("f"*64, "KRW-ETH", v2), audit), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        assert R._terms_authority(profile(None, "KRW-BTC", v1), fixed) == v1
        refused(lambda: R._terms_authority(profile(rule, "KRW-BTC", v1), fixed), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        refused(lambda: R._terms_authority(profile(None, "KRW-ETH", v1), fixed), "REHEARSAL_TERMS_PROFILE_MISMATCH")
        assert R._terms_authority(profile(None, "KRW-BTC", v1), R.parse_account_audit(e.raw_audit)) is None


def test_rehearsal_storage_artifact_is_explicit_path_and_forwarded_without_defaults():
    with fixture() as env:
        for value in (None, "", [], True):
            refused(lambda: R.load_config(json.dumps(env.config | {"history_storage": value}).encode()),
                    "REHEARSAL_PATH_REQUIRED")
        assert "history_storage" not in R.load_config(json.dumps(env.config).encode())
        selected = str(env.folder / "explicit-storage-policy.json")
        config = env.config | {"history_storage": selected}
        assert R.load_config(json.dumps(config).encode())["history_storage"] == selected
        env.path.write_text(json.dumps(config))
        with patch.object(R, "compose", side_effect=R.RehearsalError("SYNTHETIC_STOP_BEFORE_COMPOSITION")) as compose_call:
            refused(lambda: R.build_rehearsal(str(env.path), clock=env.fake.clock),
                    "SYNTHETIC_STOP_BEFORE_COMPOSITION")
        assert compose_call.call_count == 1
        assert compose_call.call_args.kwargs["history_storage_path"] == selected
        assert env.calls == []


def test_universe_adapters_name_the_coin_and_guard_every_read():
    from execution import transport as T
    from execution_accounts.instrument_terms import E1UpbitTermsSource
    from execution_accounts.quotes import E1UpbitQuoteSource
    from execution_accounts.universe import UniverseSlotSource
    seen, checks, stages = [], [], []
    guard = object.__new__(R._ReadGuard)
    guard.time_check = lambda: checks.append(1)
    guard.transport_check = lambda stage: stages.append(stage)
    clock = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)
    quote_source = E1UpbitQuoteSource(symbol="KRW-BTC", clock=clock)

    def record(*value):
        T._check_inquiry_guard("before_headers")
        seen.append(value)
        return value

    def book_read(source):
        assert source.clock is clock and source.route is quote_source.route
        return record("book", source.symbol)
    with patch.object(E1UpbitQuoteSource, "read", book_read), \
            patch.object(E1UpbitTermsSource, "read", lambda self, symbol=None: record("terms", symbol)), \
            patch.object(UniverseSlotSource, "read_flags", lambda self: record("flags")), \
            patch.object(UniverseSlotSource, "read_tickers", lambda self, markets: record("tickers", markets)):
        quotes = R._QuoteSource(quote_source, guard)
        terms = R._TermsSource(object.__new__(E1UpbitTermsSource), guard)
        slots = R._SlotSource(UniverseSlotSource(clock=clock), guard)
        assert quotes.read() == ("book", "KRW-BTC")
        assert quotes.read("KRW-XRP") == ("book", "KRW-XRP")
        assert terms.read() == ("terms", None)
        assert terms.read("KRW-XRP") == ("terms", "KRW-XRP")
        assert slots.read_flags() == ("flags",)
        assert slots.read_tickers(("KRW-BTC",)) == ("tickers", ("KRW-BTC",))
    assert quote_source.symbol == "KRW-BTC"
    assert seen == [("book", "KRW-BTC"), ("book", "KRW-XRP"), ("terms", None), ("terms", "KRW-XRP"),
                    ("flags",), ("tickers", ("KRW-BTC",))]
    assert len(checks) == 12 and stages == ["before_headers"] * 6
    T._check_inquiry_guard("before_headers")  # wrapper restored the context; no leaked authority callback
    assert len(stages) == 6
    refused(lambda: R._SlotSource(object(), guard), "REHEARSAL_FIXED_SOURCE_REQUIRED")
    refused(lambda: R._SlotSource(UniverseSlotSource(clock=clock), object()), "REHEARSAL_FIXED_SOURCE_REQUIRED")


def test_universe_adapter_guard_refusals_block_before_read_and_after_changed_authority():
    from execution_accounts.instrument_terms import E1UpbitTermsSource
    from execution_accounts.quotes import E1UpbitQuoteSource
    from execution_accounts.universe import UniverseSlotSource
    clock = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)
    guard = object.__new__(R._ReadGuard)
    guard.transport_check = lambda stage: None
    quotes = R._QuoteSource(E1UpbitQuoteSource(symbol="KRW-BTC", clock=clock), guard)
    terms = R._TermsSource(object.__new__(E1UpbitTermsSource), guard)
    slots = R._SlotSource(UniverseSlotSource(clock=clock), guard)
    calls = []
    with patch.object(E1UpbitQuoteSource, "read", lambda self: calls.append("book") or object()), \
            patch.object(E1UpbitTermsSource, "read", lambda self, symbol=None: calls.append("terms") or object()), \
            patch.object(UniverseSlotSource, "read_flags", lambda self: calls.append("flags") or object()), \
            patch.object(UniverseSlotSource, "read_tickers", lambda self, markets: calls.append("tickers") or object()):
        reads = (quotes.read, lambda: quotes.read("KRW-XRP"), terms.read, lambda: terms.read("KRW-XRP"),
                 slots.read_flags, lambda: slots.read_tickers(("KRW-BTC",)))
        for read in reads:
            with patch.object(guard, "time_check", create=True,
                              side_effect=R.RehearsalError("SYNTHETIC_AUTHORITY_REFUSED")):
                refused(read, "SYNTHETIC_AUTHORITY_REFUSED")
        assert calls == []
        for read in reads:
            with patch.object(guard, "time_check", create=True,
                              side_effect=[None, R.RehearsalError("SYNTHETIC_AUTHORITY_CHANGED")]) as checks:
                refused(read, "SYNTHETIC_AUTHORITY_CHANGED")
                assert checks.call_count == 2
    assert calls == ["book", "book", "terms", "terms", "flags", "tickers"]
