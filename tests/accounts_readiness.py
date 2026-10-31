"""Readiness and E1 connection tests: temporary state, synthetic keys, fake HTTP."""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from datetime import timedelta
from io import StringIO
import json
import os
from pathlib import Path
from unittest.mock import patch

from core.compliance import model as M
from execution_accounts import cli
from execution_accounts.readiness import (CREDENTIAL_NAMES, HOSTS, E1InquiryReader, InquirySetupError,
    configuration_manifest, inspect_configuration, inquire_once)
from tests import compliance_fixtures as F, execution_fixtures as EF


def _runtime(*, allowed=True, current=True):
    return {"observations_current": current, "provider": "local", "network_policy": {
        "mode": "restricted", "state": "enforced",
        "effective_allowed_hosts": list(HOSTS.values()) if allowed else []}}


def _configuration(**changes):
    args = dict(present_names=tuple(name for names in CREDENTIAL_NAMES.values() for name in names),
                owner_public_key_present=False, runtime_status=_runtime())
    return inspect_configuration(**(args | changes))


def _call(reader, venue="upbit", now=EF.NOW, configuration=None):
    return inquire_once(venue=venue, now=now, reader=reader,
                        configuration=configuration or _configuration(), allow_read_only_probe=True)


def _refused(fn, code):
    try:
        fn()
    except InquirySetupError as exc:
        assert exc.code == code
    else:
        raise AssertionError("expected setup refusal")


def test_configuration_reads_names_never_environment_values_and_cannot_arm():
    class NamesOnly(Mapping):
        def __iter__(self):
            return iter(tuple(name for names in CREDENTIAL_NAMES.values() for name in names))
        def __len__(self):
            return sum(map(len, CREDENTIAL_NAMES.values()))
        def __getitem__(self, key):
            raise AssertionError("credential value read")
    report = _configuration(present_names=NamesOnly(), owner_public_key_present=True)
    assert report.owner_public_key_present and report.owner_signature_status == "NOT_CHECKED"
    assert not report.execution_ready and not report.account_evidence_ready
    assert all(v.probe_environment_ready and v.credential_status == "PRESENCE_UNVERIFIED" for v in report.venues)
    assert all(not v.inquiry_ready and not v.execution_ready for v in report.venues)


def test_missing_or_desired_only_network_configuration_never_becomes_verified():
    report = _configuration(present_names=(), runtime_status={"network_policy": _runtime()["network_policy"]})
    assert all(v.missing_names and v.network_status == "unverified" and not v.probe_environment_ready for v in report.venues)
    stale = _configuration(runtime_status=_runtime(current=False))
    assert all(v.network_status == "unverified" for v in stale.venues)
    desired = _runtime(); desired["network_policy"]["state"] = "pending"
    assert all(v.network_status == "unverified" for v in _configuration(runtime_status=desired).venues)
    wildcard = _runtime(); wildcard["network_policy"]["effective_allowed_hosts"] = ["*.upbit.com"]
    assert all(v.network_status == "blocked" for v in _configuration(runtime_status=wildcard).venues)


def test_cloud_proxy_requirement_is_not_mistaken_for_direct_e1_connectivity():
    startup = {"version": 1, "http_proxy": "http://proxy:8080", "http_network_policy": {
        "type": "restricted", "egress_rules": [{"host": host} for host in HOSTS.values()]}}
    report = _configuration(policy_snapshot=startup)
    assert all(v.network_status == "allowed" and v.proxy_path_required and not v.probe_environment_ready for v in report.venues)
    assert all("E1_PROXY_PATH_UNSUPPORTED" in v.reasons for v in report.venues)
    startup["http_network_policy"]["egress_rules"] = []
    report = _configuration(runtime_status=None, policy_snapshot=startup)
    assert all(v.network_status == "blocked" for v in report.venues)


def test_configuration_manifest_contains_names_hosts_and_no_operational_permission():
    manifest = configuration_manifest()
    assert manifest["allowed_https_hosts"] == list(HOSTS.values())
    assert manifest["credential_values_included"] is False and manifest["execution_ready"] is False
    assert manifest["credential_variable_names"] == {v: list(n) for v, n in CREDENTIAL_NAMES.items()}
    assert manifest["owner_signature_status"] == "NOT_CHECKED"


def test_probe_is_opt_in_and_blocked_configuration_never_calls_the_reader():
    calls = []
    reader = lambda now: calls.append(now)
    result = inquire_once(venue="upbit", now=EF.NOW, reader=reader, configuration=_configuration())
    assert not result.inquiry_connected and not calls
    result = _call(reader, configuration=_configuration(runtime_status=_runtime(allowed=False)))
    assert result.reasons == ("PROBE_CONFIGURATION_BLOCKED",) and not calls


def test_successful_inquiry_returns_counts_without_balances_ids_addresses_or_permits():
    from execution.snapshot import Address, Holding, Move
    secret = "sensitive-fixture-never-in-summary"
    snap = EF.snap("upbit", holdings={secret: Holding(units=12345.67)}, cash={"KRW": 87654321.0},
        fills=(Move(id=secret, symbol=secret, side="buy", units=12.0),),
        withdrawal_addresses=(Address(currency="BTC", net_type="BTC", address=secret),))
    result = _call(lambda now: snap)
    raw = json.dumps(asdict(result))
    assert result.inquiry_connected and dict(result.counts)["holdings"] == 1
    assert dict(result.counts)["fills"] == 1 and dict(result.counts)["withdrawal_addresses"] == 1
    assert secret not in raw and "87654321" not in raw and "12345" not in raw
    assert not result.execution_ready and not result.account_evidence_ready
    assert "AUTHORITATIVE_ACCOUNT_EVIDENCE_REQUIRED" in result.reasons


def test_scope_age_future_and_server_day_disagreement_refuse_connectivity():
    assert _call(lambda now: EF.snap("okx")).reasons == ("INQUIRY_SCOPE_MISMATCH",)
    for seconds in (-31, 1):
        stamp = M.iso_utc(EF.NOW + timedelta(seconds=seconds))
        assert _call(lambda now: EF.snap("upbit", utc=stamp)).reasons == ("INQUIRY_STALE",)
    assert _call(lambda now: EF.snap("upbit", server_utc=None)).reasons == ("SERVER_CLOCK_REQUIRED",)
    day_start = EF.NOW.astimezone(M.KST).replace(hour=0, minute=0, second=1)
    previous_day = day_start - timedelta(seconds=2)
    snap = EF.snap("upbit", utc=M.iso_utc(day_start), server_utc=M.iso_utc(previous_day))
    assert _call(lambda now: snap, now=day_start).reasons == ("SERVER_CLOCK_MISMATCH",)


def test_mutated_records_and_provider_exceptions_do_not_leak_raw_text():
    snap = EF.snap("upbit", cash={"KRW": 1.0})
    snap.cash["KRW"] = 2.0
    assert not _call(lambda now: snap).inquiry_connected
    assert _call(lambda now: object()).reasons == ("INVALID_INQUIRY_RECORD",)
    def broken(now):
        raise RuntimeError("SECRET-from-provider")
    result = _call(broken)
    assert result.reasons == ("INQUIRY_FAILED",) and "SECRET" not in repr(result)
    snap = EF.snap("upbit", ok=False, error="SECRET-raw-response", flags={"auth_error"})
    result = _call(lambda now: snap)
    assert result.reasons == ("E1_INQUIRY_FAILED", "E1_AUTH_ERROR") and "SECRET" not in repr(result)


def test_e1_reader_requires_declared_credentials_and_explicit_isolated_home():
    with F.temp_home() as home:
        reader = E1InquiryReader(venue="upbit", state_directory=home)
        with patch.dict(os.environ, {}, clear=True):
            _refused(lambda: reader(EF.NOW), "CREDENTIAL_NAMES_MISSING")
        with EF.fake_keys(), patch.dict(os.environ, {"TRADEGEN_HOME": str(home / "other")}):
            _refused(lambda: reader(EF.NOW), "ISOLATED_STATE_REQUIRED")
        with EF.fake_keys(), patch.dict(os.environ, {"TRADEGEN_HOME": str(Path.home() / ".tradegen")}):
            reader = E1InquiryReader(venue="upbit", state_directory=Path.home() / ".tradegen")
            _refused(lambda: reader(EF.NOW), "ISOLATED_STATE_REQUIRED")


def test_upbit_reader_runs_existing_e1_client_with_fake_http_and_no_state_writer():
    with F.temp_home() as home, EF.fake_keys(), EF.serve(EF.upbit_routes()) as calls:
        result = _call(E1InquiryReader(venue="upbit", state_directory=home))
        assert result.inquiry_connected, result.reasons
        expected = ("/v1/accounts", "/v1/orders/open", "/v1/orders/closed", "/v1/withdraws",
                    "/v1/withdraws/coin_addresses", "/v1/deposits", "/v1/api_keys", "/v1/ticker")
        assert tuple((call["method"], call["path"]) for call in calls) == tuple(("GET", path) for path in expected)
        # E1 intentionally never calls the fixture's allowlisted wallet-status route.
        assert not list(home.iterdir())


def test_kis_reader_requires_fresh_sealed_signed_context_before_any_inquiry():
    with F.temp_home() as home, EF.fake_keys(), EF.serve(EF.kis_routes()) as calls:
        reader = E1InquiryReader(venue="kis", state_directory=home)
        assert _call(reader, venue="kis").reasons == ("KIS_SIGNED_CONTEXT_REQUIRED",)
        stale = F.ctx()
        assert _call(replace(reader, kis_context=stale), venue="kis").reasons == ("KIS_SIGNED_CONTEXT_REQUIRED",)
        unsigned = F.ctx(date=EF.NOW.astimezone(M.KST).date(), code_signed=False)
        assert _call(replace(reader, kis_context=unsigned), venue="kis").reasons == ("KIS_SIGNED_CONTEXT_REQUIRED",)
        mutated = F.ctx(date=EF.NOW.astimezone(M.KST).date(), code_signed=False)
        object.__setattr__(mutated, "code_signed", True)
        assert _call(replace(reader, kis_context=mutated), venue="kis").reasons == ("KIS_SIGNED_CONTEXT_REQUIRED",)
        assert not calls
        signed = F.ctx(date=EF.NOW.astimezone(M.KST).date())
        result = _call(replace(reader, kis_context=signed), venue="kis")
        assert result.inquiry_connected and calls
        assert all(call["method"] == "GET" or call["path"] == "/oauth2/tokenP" for call in calls)
        assert not (home / "compliance").exists() and not (home / "execution").exists()
        assert (home / "kis_token.json").exists()


def test_okx_reader_requires_explicit_quote_and_keeps_e1_readonly_self_check():
    with F.temp_home() as home, EF.fake_keys(), EF.serve(EF.okx_routes()) as calls:
        reader = E1InquiryReader(venue="okx", state_directory=home)
        assert _call(reader, venue="okx").reasons == ("OKX_QUOTE_REQUIRED",) and not calls
        result = _call(replace(reader, okx_usdt_krw=1400.0), venue="okx")
        assert result.inquiry_connected and all(call["method"] == "GET" for call in calls)
        assert not list(home.iterdir())


def test_default_cli_reads_only_metadata_and_never_owner_context_or_env_file():
    from core.compliance import owner
    with F.temp_home() as home:
        (home / ".env").write_text("UPBIT_ACCESS_KEY=SECRET-should-not-be-read\n")
        metadata = home / "policy.json"
        metadata.write_text(json.dumps({"version": 1, "http_network_policy": {"type": "restricted", "egress_rules": []}}))
        output = StringIO()
        original_open = Path.open
        def no_env_open(path, *args, **kwargs):
            assert path != home / ".env", "readiness opened the credential file"
            return original_open(path, *args, **kwargs)
        with patch.object(cli, "_ROOT", home), patch.object(owner, "load_context", side_effect=AssertionError("owner write")), patch.object(Path, "open", no_env_open), redirect_stdout(output):
            code = cli.main(["--network-policy", str(metadata)])
        report = json.loads(output.getvalue())
        assert code == 2 and report["execution_ready"] is False
        assert "SECRET-should-not-be-read" not in output.getvalue()
        assert "UPBIT_SECRET_KEY" in output.getvalue()  # Variable names are intentionally visible.
        assert not (home / "compliance").exists()
        output = StringIO()
        with redirect_stdout(output):
            assert cli.main(["--configuration-manifest"]) == 0
        assert json.loads(output.getvalue())["credential_values_included"] is False


def test_cli_rejects_nonmetadata_duplicate_nonfinite_and_linked_json_without_echo():
    with F.temp_home() as home:
        for name, body in ((".env", "SECRET=yes"), ("double.json", '{"x":1,"x":2}'),
                           ("float.json", '{"x":NaN}')):
            path = home / name; path.write_text(body)
            output = StringIO()
            with redirect_stdout(output):
                assert cli.main(["--network-policy", str(path)]) == 2
            assert json.loads(output.getvalue())["error"] == "READINESS_METADATA_UNAVAILABLE"
            assert "SECRET" not in output.getvalue()
        folder = home / "original"; folder.mkdir()
        (folder / "policy.json").write_text('{}')
        linked = home / "linked"; F.directory_link(linked, folder)
        output = StringIO()
        with redirect_stdout(output):
            assert cli.main(["--network-policy", str(linked / "policy.json")]) == 2
        assert json.loads(output.getvalue())["error"] == "READINESS_METADATA_UNAVAILABLE"
