"""Offline sidecar configuration and destination tests; no connections or credentials."""
import ast
from contextlib import contextmanager
from contextvars import Context
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

from execution_network import route as R


@contextmanager
def _ca_exists(exists=True):
    previous = R.Path
    observed = []
    def metadata(path):
        observed.append(path)
        return SimpleNamespace(is_file=lambda: exists)
    R.Path = metadata
    try:
        yield observed
    finally:
        R.Path = previous


def _build(*, hosts=None, policy=None, status=None, proxy=None, ca=None):
    return R.build_managed_route(
        policy_snapshot={"version": 1, "http_proxy": R.MANAGED_PROXY} if policy is None else policy,
        runtime_status={"observations_current": True, "network_policy": {"state": "enforced", "mode": "restricted",
            "effective_allowed_hosts": ["api.upbit.com"] if hosts is None else hosts}} if status is None else status,
        proxy_url=R.MANAGED_PROXY if proxy is None else proxy,
        ca_bundle=R.MANAGED_CA_BUNDLE if ca is None else ca)


def _refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, str(exc)
        return
    raise AssertionError("invalid route accepted")


def test_default_direct_has_no_proxy_and_keeps_verified_tls():
    for url in ("https://api.upbit.com/v1/accounts", "https://www.okx.com/api/v5/public/time",
                "https://openapi.koreainvestment.com:9443/oauth2/tokenP"):
        options = R.route_options(url)
        assert dict(options.proxies) == {} and options.verify is True


def test_managed_route_requires_exact_enforced_current_host_metadata_and_public_ca():
    with _ca_exists() as observed:
        route = _build(hosts=["api.upbit.com", "github.com", "*.okx.com"])
    assert observed == ["/etc/ssl/certs/ca-certificates.crt"]
    assert route.permitted_hosts == frozenset({"api.upbit.com"})
    with R.managed_route(route):
        options = R.route_options("https://api.upbit.com/v1/accounts")
        assert dict(options.proxies) == {"http": "http://proxy:8080", "https": "http://proxy:8080"}
        assert options.verify == "/etc/ssl/certs/ca-certificates.crt"
        _refused(lambda: R.route_options("https://www.okx.com/api/v5/public/time"), "MANAGED_DESTINATION_BLOCKED")
    with _ca_exists(False):
        _refused(_build, "MANAGED_CA_BUNDLE_MISSING")


def test_missing_stale_and_unenforced_policy_cannot_enable_managed_routing():
    with _ca_exists() as observed:
        for policy in ({}, {"version": True, "http_proxy": R.MANAGED_PROXY},
                       {"version": 2, "http_proxy": R.MANAGED_PROXY},
                       {"version": 1, "http_proxy": "http://other:8080"}):
            _refused(lambda policy=policy: _build(policy=policy), "MANAGED_POLICY_OBSERVATION_REQUIRED")
        for status in ({}, {"observations_current": False},
                       {"observations_current": True, "network_policy": {"state": "pending", "mode": "unrestricted"}},
                       {"observations_current": True, "network_policy": {"state": "enforced", "mode": "unknown"}},
                       {"observations_current": True, "network_policy": {"state": "enforced", "mode": "restricted"}},
                       {"observations_current": True, "network_policy": {"state": "enforced", "mode": "restricted",
                                                                                 "effective_allowed_hosts": [True]}}):
            _refused(lambda status=status: _build(status=status), "MANAGED_POLICY_OBSERVATION_REQUIRED")
        for hosts in ([], ["*.upbit.com"], ["api.upbit.com:443"], ["api.upbit.com.attacker.invalid"]):
            _refused(lambda hosts=hosts: _build(hosts=hosts), "MANAGED_ROUTE_INVALID")
    assert observed == []


def test_unrestricted_platform_still_has_only_three_exact_execution_hosts():
    with _ca_exists():
        route = _build(status={"observations_current": True,
                              "network_policy": {"state": "enforced", "mode": "unrestricted"}})
    assert route.permitted_hosts == frozenset({"api.upbit.com", "openapi.koreainvestment.com", "www.okx.com"})
    with R.managed_route(route):
        _refused(lambda: R.route_options("https://attacker.invalid/"), "EXECUTION_DESTINATION_INVALID")


def test_proxy_auth_alternate_hosts_ports_paths_and_unverified_ca_are_refused():
    with _ca_exists() as observed:
        for proxy in ("", "https://proxy:8080", "http://proxy:8081", "http://user:password@proxy:8080",
                      "http://proxy:8080/", "http://proxy:8080?token=x", "http://proxy:8080#x",
                      "http://localhost:8080", "http://attacker.invalid:8080", True):
            _refused(lambda proxy=proxy: _build(proxy=proxy), "MANAGED_ROUTE_INVALID")
        for ca in ("", False, True, "/tmp/ca.pem", "/etc/ssl/certs/../certs/ca-certificates.crt"):
            _refused(lambda ca=ca: _build(ca=ca), "MANAGED_ROUTE_INVALID")
    assert observed == []


def test_destination_scheme_userinfo_port_and_hostname_refuse_before_route_selection():
    for url in ("http://api.upbit.com/v1/accounts", "https://@api.upbit.com/", "https://user@api.upbit.com/",
                "https://api.upbit.com:0/", "https://api.upbit.com:9443/", "https://api.upbit.com:bad/",
                "https://openapi.koreainvestment.com/", "https://www.okx.com:444/",
                "https://api.upbit.com.attacker.invalid/", "https://api.upbit.com./", "https://127.0.0.1/",
                "https://api.upbit.com/#x", "https://api.upbit.com/\n", b"https://api.upbit.com/", None, {}):
        _refused(lambda url=url: R.route_options(url), "EXECUTION_DESTINATION_INVALID")


def test_nested_context_is_restored_on_error_and_does_not_leak_to_new_context():
    with _ca_exists():
        outer, inner = _build(), _build(hosts=["www.okx.com"])
    with R.managed_route(outer):
        assert R.route_options("https://api.upbit.com/").verify == R.MANAGED_CA_BUNDLE
        assert Context().run(R.route_options, "https://api.upbit.com/").verify is True
        try:
            with R.managed_route(inner):
                _refused(lambda: R.route_options("https://api.upbit.com/"), "MANAGED_DESTINATION_BLOCKED")
                raise RuntimeError("synthetic failure")
        except RuntimeError:
            pass
        assert R.route_options("https://api.upbit.com/").verify == R.MANAGED_CA_BUNDLE
    assert R.route_options("https://api.upbit.com/").verify is True


def test_route_and_options_cannot_be_reconfigured_in_place():
    with _ca_exists():
        route = _build()
    try:
        route.proxy_url = "http://attacker.invalid:8080"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("route is mutable")
    options = R.route_options("https://api.upbit.com/")
    try:
        options.proxies["https"] = "http://attacker.invalid:8080"
    except TypeError:
        pass
    else:
        raise AssertionError("options are mutable")
    for changed in (replace(route, proxy_url="http://attacker.invalid:8080"), replace(route, ca_bundle=False),
                    replace(route, permitted_hosts=frozenset({"attacker.invalid"})),
                    replace(route, permitted_hosts=set(route.permitted_hosts))):
        _refused(lambda changed=changed: R.managed_route(changed).__enter__(), "MANAGED_ROUTE_INVALID")


def _source_problems(source):
    allowed = {"__future__", "collections.abc", "contextlib", "contextvars", "dataclasses", "pathlib", "types", "urllib.parse"}
    forbidden = {"environ", "getenv", "read_text", "read_bytes", "write_text", "write_bytes", "open", "unlink",
                 "request", "send", "urlopen", "connect", "system", "popen", "eval", "exec", "__import__"}
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            hits.extend(alias.name for alias in node.names if alias.name not in allowed or alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed or any(alias.asname or alias.name == "*" for alias in node.names):
                hits.append("import")
        elif isinstance(node, ast.Attribute) and node.attr in forbidden:
            hits.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in forbidden:
            hits.append(node.id)
    return hits


def test_routing_module_has_no_network_auth_environment_or_file_content_access():
    source = (Path(__file__).resolve().parents[1] / "execution_network" / "route.py").read_text(encoding="utf-8")
    assert not _source_problems(source), _source_problems(source)
    for negative in ("import requests", "from execution import keys", "import os", "x = os.environ",
                     "x = Path(p).read_text()", "session.request()", "open(p)", "exec(code)"):
        assert _source_problems(negative), negative
    assert R.MANAGED_PROXY == "http://proxy:8080" and R.MANAGED_CA_BUNDLE == "/etc/ssl/certs/ca-certificates.crt"
    assert dict(R.VENUE_PORTS) == {"api.upbit.com": 443, "openapi.koreainvestment.com": 9443, "www.okx.com": 443}
