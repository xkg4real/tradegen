"""Read-only configuration diagnostics and explicit E1 inquiry integration.

Presence is not credential validity. A successful bounded E1 inquiry is not
complete account evidence, an execution permit or an owner-session approval.
This module never reads a credential value or an owner ledger, and never signs,
arms, submits an order or writes state itself. Explicit E1 inquiry can use its
existing KIS token cache only under the caller's isolated state directory.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path

VENUES = ("kis", "upbit", "okx")
HOSTS = {"kis": "openapi.koreainvestment.com", "upbit": "api.upbit.com", "okx": "www.okx.com"}
CREDENTIAL_NAMES = {
    "kis": ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_8", "KIS_ACCOUNT_PD"),
    "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
    "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE"),
}
_COUNTS = ("holdings", "open_orders", "fills", "deposits", "withdrawals", "withdrawal_addresses")
_E1_FAILURE_FLAGS = frozenset({"keys_missing", "code_unsigned", "auth_error", "okx_perm", "okx_acct_lv",
                             "okx_spot_borrow", "okx_auto_loan", "okx_no_ip", "EVENTS", "derivative_position"})
_PROBE_CODES = frozenset({"INVALID_PROBE_INPUT", "ISOLATED_STATE_REQUIRED", "CREDENTIAL_NAMES_MISSING",
                         "KIS_SIGNED_CONTEXT_REQUIRED", "OKX_QUOTE_REQUIRED", "E1_INQUIRY_FAILED"})


class InquirySetupError(ValueError):
    """An allowlisted diagnostic, never a raw input, provider exception or secret."""
    def __init__(self, code: str):
        self.code = code if code in _PROBE_CODES else "INVALID_PROBE_INPUT"
        super().__init__(self.code)


@dataclass(frozen=True, kw_only=True)
class VenueConfiguration:
    venue: str
    present_names: tuple[str, ...]
    missing_names: tuple[str, ...]
    network_status: str
    proxy_path_required: bool
    probe_environment_ready: bool
    reasons: tuple[str, ...]
    credential_status: str = "PRESENCE_UNVERIFIED"
    inquiry_ready: bool = False
    account_evidence_ready: bool = False
    execution_ready: bool = False


@dataclass(frozen=True, kw_only=True)
class ConfigurationReport:
    venues: tuple[VenueConfiguration, ...]
    owner_public_key_present: bool
    owner_signature_status: str = "NOT_CHECKED"
    account_evidence_ready: bool = False
    execution_ready: bool = False


@dataclass(frozen=True, kw_only=True)
class InquirySummary:
    venue: str
    inquiry_connected: bool
    counts: tuple[tuple[str, int], ...] = ()
    reasons: tuple[str, ...] = ()
    account_evidence_ready: bool = False
    execution_ready: bool = False


def configuration_manifest() -> dict:
    """Reviewable host/variable-name configuration request, containing no values."""
    return {
        "schema_version": 1,
        "purpose": "read_only_account_inquiry",
        "allowed_https_hosts": [HOSTS[v] for v in VENUES],
        "kis_https_port": 9443,
        "credential_variable_names": {v: list(CREDENTIAL_NAMES[v]) for v in VENUES},
        "credential_values_included": False,
        "owner_public_key_relative_path": "core/compliance/owner_pubkey.pem",
        "credential_permissions": {
            "upbit": ["asset_inquiry", "order_inquiry", "deposit_inquiry", "withdrawal_inquiry"],
            "okx": ["read_only"],
            "kis": ["account_inquiry_requires_owner_signed_code"],
        },
        "network_caveat": "E1 disables environment proxies; Cloud proxy compatibility requires separate review",
        "owner_signature_status": "NOT_CHECKED",
        "account_evidence_ready": False,
        "execution_ready": False,
    }


def _network_status(venue: str, runtime_status: Mapping | None, policy_snapshot: Mapping | None) -> tuple[str, bool]:
    runtime = runtime_status if isinstance(runtime_status, Mapping) else {}
    startup = policy_snapshot if isinstance(policy_snapshot, Mapping) else {}
    proxy = isinstance(startup.get("http_proxy"), str) and bool(startup["http_proxy"])
    policy = runtime.get("network_policy")
    if runtime.get("observations_current") is True and isinstance(policy, Mapping) and policy.get("state") == "enforced":
        if policy.get("mode") == "unrestricted":
            return "allowed", proxy
        if policy.get("mode") == "restricted":
            names = policy.get("effective_allowed_hosts")
            if isinstance(names, list) and all(type(name) is str for name in names):
                return ("allowed" if HOSTS[venue] in names else "blocked"), proxy
        return "unverified", proxy
    # A startup snapshot can establish the listed restriction, but cannot prove
    # that a host is currently allowed. A missing/stale readiness observation is
    # never upgraded merely because its desired configuration contains the host.
    snapshot_policy = startup.get("http_network_policy")
    if startup.get("version") == 1 and isinstance(snapshot_policy, Mapping):
        entries = snapshot_policy.get("egress_rules")
        if snapshot_policy.get("type") == "restricted" and isinstance(entries, list):
            if all(isinstance(row, Mapping) and type(row.get("host")) is str for row in entries):
                if HOSTS[venue] not in {row["host"] for row in entries}:
                    return "blocked", proxy
    return "unverified", proxy


def inspect_configuration(*, present_names: Iterable[str], owner_public_key_present: bool,
                          runtime_status: Mapping | None = None,
                          policy_snapshot: Mapping | None = None) -> ConfigurationReport:
    """Use only explicit variable names, path existence and safe runtime metadata.

    `present_names` may be os.environ itself: iteration accesses names only, not
    values. Placeholders and blank variables therefore remain presence-unverified.
    `owner_public_key_present` is only an existence observation, never a signature.
    """
    if type(owner_public_key_present) is not bool:
        raise ValueError("invalid public-key presence observation")
    names = frozenset(present_names)
    if any(type(name) is not str for name in names):
        raise ValueError("invalid variable-name observation")
    output = []
    for venue in VENUES:
        present = tuple(name for name in CREDENTIAL_NAMES[venue] if name in names)
        missing = tuple(name for name in CREDENTIAL_NAMES[venue] if name not in names)
        network, proxy = _network_status(venue, runtime_status, policy_snapshot)
        reasons = ["CREDENTIAL_PRESENCE_UNVERIFIED", "OWNER_SIGNATURE_NOT_CHECKED",
                   "AUTHORITATIVE_ACCOUNT_EVIDENCE_REQUIRED"]
        if missing:
            reasons.append("CREDENTIAL_NAMES_MISSING")
        if network != "allowed":
            reasons.append("NETWORK_HOST_BLOCKED" if network == "blocked" else "NETWORK_OBSERVATION_REQUIRED")
        if proxy:
            reasons.append("E1_PROXY_PATH_UNSUPPORTED")
        if venue == "kis":
            reasons.append("KIS_SIGNED_CONTEXT_REQUIRED")
        output.append(VenueConfiguration(venue=venue, present_names=present, missing_names=missing,
            network_status=network, proxy_path_required=proxy,
            probe_environment_ready=not missing and network == "allowed" and not proxy,
            reasons=tuple(reasons)))
    return ConfigurationReport(venues=tuple(output), owner_public_key_present=owner_public_key_present)


def _aware(now: datetime) -> datetime:
    if type(now) is not datetime or now.utcoffset() is None:
        raise InquirySetupError("INVALID_PROBE_INPUT")
    return now


@dataclass(frozen=True, kw_only=True, repr=False)
class E1InquiryReader:
    """Explicit connection to existing read-only E1 clients; never a poll/log writer.

    The caller configures TRADEGEN_HOME before construction and supplies a fresh
    sealed owner context for KIS. Every required variable must be declared in the
    environment, preventing E1's fallback from opening a repository .env file.
    Credential validity is established only by the eventual authenticated query.
    This object performs no operation until called by an explicit probe.
    """
    venue: str
    state_directory: Path
    kis_context: object = field(default=None, repr=False)
    okx_usdt_krw: float | None = None

    def __call__(self, now: datetime):
        _aware(now)
        if self.venue not in VENUES:
            raise InquirySetupError("INVALID_PROBE_INPUT")
        if any(name not in os.environ for name in CREDENTIAL_NAMES[self.venue]):
            raise InquirySetupError("CREDENTIAL_NAMES_MISSING")
        configured = os.environ.get("TRADEGEN_HOME")
        if not configured or type(self.state_directory) not in (Path, type(Path())):
            raise InquirySetupError("ISOLATED_STATE_REQUIRED")
        try:
            expected = self.state_directory.resolve()
            if self.state_directory.absolute() != expected or expected != Path(configured).resolve() or any(
                    expected.is_relative_to((Path.home() / name).resolve()) for name in (".tradegen", ".nextgen")):
                raise InquirySetupError("ISOLATED_STATE_REQUIRED")
            from core.isolation import checked_target, state_root
            checked_target(self.state_directory, "isolated inquiry state")
            if state_root().resolve() != expected:
                raise InquirySetupError("ISOLATED_STATE_REQUIRED")
        except (OSError, RuntimeError, ValueError):
            raise InquirySetupError("ISOLATED_STATE_REQUIRED") from None
        if self.venue == "kis":
            from core.compliance import model
            try:
                intact = (model.is_sealed(self.kis_context) and self.kis_context.code_signed is True
                          and self.kis_context.date == now.astimezone(model.KST).date()
                          and self.kis_context.ctx_hash == model.sha256_hex(model.canonical_json({
                              item.name: getattr(self.kis_context, item.name)
                              for item in fields(model.Context) if item.name != "ctx_hash"})))
            except (ValueError, TypeError, AttributeError, ArithmeticError, RecursionError):
                intact = False
            if not intact:
                raise InquirySetupError("KIS_SIGNED_CONTEXT_REQUIRED")
            from execution import kis_inquiry
            return kis_inquiry.snapshot(now, self.kis_context)
        if self.venue == "okx":
            rate = self.okx_usdt_krw
            if type(rate) not in (float, int) or not math.isfinite(rate) or rate <= 0:
                raise InquirySetupError("OKX_QUOTE_REQUIRED")
            from execution import okx_inquiry
            return okx_inquiry.snapshot(now, float(rate))
        from execution import upbit_inquiry
        return upbit_inquiry.snapshot(now)


def inquire_once(*, venue: str, now: datetime, reader: Callable[[datetime], object],
                 configuration: ConfigurationReport, allow_read_only_probe: bool = False) -> InquirySummary:
    """Run one explicitly requested inquiry and return counts, never account values.

    An injected reader is required; no network/client is selected implicitly.
    The configuration observation is a diagnostic, not authorization or a permit.
    """
    _aware(now)
    if venue not in VENUES or type(configuration) is not ConfigurationReport or not callable(reader):
        raise InquirySetupError("INVALID_PROBE_INPUT")
    matches = [item for item in configuration.venues if item.venue == venue]
    if len(matches) != 1 or type(matches[0]) is not VenueConfiguration:
        raise InquirySetupError("INVALID_PROBE_INPUT")
    selected = matches[0]
    if allow_read_only_probe is not True:
        return InquirySummary(venue=venue, inquiry_connected=False, reasons=("READ_ONLY_PROBE_NOT_REQUESTED",))
    if not selected.probe_environment_ready:
        return InquirySummary(venue=venue, inquiry_connected=False, reasons=("PROBE_CONFIGURATION_BLOCKED",))
    try:
        snap = reader(now)
        from core.compliance import model
        from execution.snapshot import Snapshot, load
        if type(snap) is not Snapshot:
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("INVALID_INQUIRY_RECORD",))
        # Rebuild and rehash frozen-but-nested mappings before deriving any result.
        snap = load(model.jsonable(snap))
        if snap.venue != venue:
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("INQUIRY_SCOPE_MISMATCH",))
        observed = datetime.fromisoformat(snap.utc)
        if observed.utcoffset() is None or not timedelta(0) <= now - observed <= timedelta(seconds=30):
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("INQUIRY_STALE",))
        if not snap.ok:
            flags = tuple("E1_" + flag.upper() for flag in sorted(snap.flags & _E1_FAILURE_FLAGS))
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("E1_INQUIRY_FAILED",) + flags)
        if snap.server_utc is None:
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("SERVER_CLOCK_REQUIRED",))
        server = datetime.fromisoformat(snap.server_utc)
        if (server.utcoffset() is None or abs(now - server) > timedelta(seconds=60)
                or server.astimezone(model.KST).date() != now.astimezone(model.KST).date()):
            return InquirySummary(venue=venue, inquiry_connected=False, reasons=("SERVER_CLOCK_MISMATCH",))
        counts = tuple((name, len(getattr(snap, name))) for name in _COUNTS)
        return InquirySummary(venue=venue, inquiry_connected=True, counts=counts,
                              reasons=("INQUIRY_ONLY", "AUTHORITATIVE_ACCOUNT_EVIDENCE_REQUIRED"))
    except InquirySetupError as exc:
        return InquirySummary(venue=venue, inquiry_connected=False, reasons=(exc.code,))
    except Exception:
        return InquirySummary(venue=venue, inquiry_connected=False, reasons=("INQUIRY_FAILED",))
