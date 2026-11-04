"""Opt-in managed sidecar routing; no network, credentials or environment access.

The caller supplies non-secret configuration observations. They are configuration
claims, not authenticated account evidence. The platform sidecar remains the
actual destination-policy enforcement point. Nothing here changes that policy.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlsplit

MANAGED_PROXY = "http://proxy:8080"
MANAGED_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"
VENUE_PORTS = MappingProxyType({"api.upbit.com": 443, "openapi.koreainvestment.com": 9443, "www.okx.com": 443})


@dataclass(frozen=True, kw_only=True)
class ManagedRoute:
    proxy_url: str
    ca_bundle: str
    permitted_hosts: frozenset[str]


@dataclass(frozen=True, kw_only=True)
class RouteOptions:
    proxies: Mapping[str, str]
    verify: bool | str


_ACTIVE_ROUTE: ContextVar[ManagedRoute | None] = ContextVar("tradegen_managed_route", default=None)


def _validate(route: ManagedRoute) -> None:
    if (type(route) is not ManagedRoute or type(route.proxy_url) is not str
            or route.proxy_url != MANAGED_PROXY or type(route.ca_bundle) is not str
            or route.ca_bundle != MANAGED_CA_BUNDLE or type(route.permitted_hosts) is not frozenset
            or not route.permitted_hosts
            or any(type(host) is not str or host not in VENUE_PORTS for host in route.permitted_hosts)):
        raise ValueError("MANAGED_ROUTE_INVALID")


def build_managed_route(*, policy_snapshot: Mapping, runtime_status: Mapping,
                        proxy_url: str, ca_bundle: str) -> ManagedRoute:
    """Validate explicit metadata and configured sidecar/CA values without reading env.

    The owner/runtime integration supplies its inherited non-secret proxy and CA
    selectors. Supported managed routing is intentionally fixed to this Cloud
    sidecar and system trust store; unsupported settings never fall back direct.
    A current enforced observation is required. Rebuild after a policy change or
    process restart; these supplied observations are not proof of API permission.
    """
    if (not isinstance(policy_snapshot, Mapping) or policy_snapshot.get("version") != 1
            or type(policy_snapshot.get("version")) is not int
            or policy_snapshot.get("http_proxy") != MANAGED_PROXY
            or not isinstance(runtime_status, Mapping)
            or runtime_status.get("observations_current") is not True):
        raise ValueError("MANAGED_POLICY_OBSERVATION_REQUIRED")
    network = runtime_status.get("network_policy")
    if not isinstance(network, Mapping) or network.get("state") != "enforced":
        raise ValueError("MANAGED_POLICY_OBSERVATION_REQUIRED")
    if network.get("mode") == "unrestricted":
        hosts = frozenset(VENUE_PORTS)
    elif network.get("mode") == "restricted":
        configured = network.get("effective_allowed_hosts")
        if type(configured) is not list or any(type(host) is not str for host in configured):
            raise ValueError("MANAGED_POLICY_OBSERVATION_REQUIRED")
        hosts = frozenset(host for host in configured if host in VENUE_PORTS)
    else:
        raise ValueError("MANAGED_POLICY_OBSERVATION_REQUIRED")
    route = ManagedRoute(proxy_url=proxy_url, ca_bundle=ca_bundle, permitted_hosts=hosts)
    _validate(route)
    # Inspect only the public system trust-store metadata, never credential files.
    if not Path(route.ca_bundle).is_file():
        raise ValueError("MANAGED_CA_BUNDLE_MISSING")
    return route


@contextmanager
def managed_route(route: ManagedRoute):
    """Explicit context-local routing, restored after success or exception.

    Does not prepare/approve an account or session, obtain credentials, open a
    connection or grant a transport capability. No global monkeypatch is needed.
    """
    _validate(route)
    token = _ACTIVE_ROUTE.set(route)
    try:
        yield route
    finally:
        _ACTIVE_ROUTE.reset(token)


def route_options(url: str) -> RouteOptions:
    """Return only proxy and TLS selectors for the existing E1/E3 HTTP seams."""
    if type(url) is not str:
        raise ValueError("EXECUTION_DESTINATION_INVALID")
    try:
        target = urlsplit(url)
        valid = (target.scheme == "https" and target.username is None
                 and target.password is None and not target.fragment and target.hostname in VENUE_PORTS
                 and (443 if target.port is None else target.port) == VENUE_PORTS[target.hostname]
                 and not any(char.isspace() or ord(char) < 32 for char in url))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("EXECUTION_DESTINATION_INVALID")
    route = _ACTIVE_ROUTE.get()
    if route is None:
        return RouteOptions(proxies=MappingProxyType({}), verify=True)
    _validate(route)
    if target.hostname not in route.permitted_hosts:
        raise ValueError("MANAGED_DESTINATION_BLOCKED")
    return RouteOptions(proxies=MappingProxyType({"http": route.proxy_url, "https": route.proxy_url}),
                        verify=route.ca_bundle)
