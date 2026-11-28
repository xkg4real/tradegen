"""Controlled Upbit owner launcher under independent review.

    python -m tools.owner.live --config PRIVATE_LIVE_CONFIG.json
    python -m tools.owner.live --config PRIVATE_LIVE_CONFIG.json --inspect-startup STARTUP_RECORD.json

The second form checks an existing local guard archive, completion, control
journal and separately retained heads. Its JSON result contains no order IDs,
balances, paths or signatures. It never starts a trading runtime. The startup
record has schema_version 1 and fields sealed_root, backup_root, archive_head,
archive_limits, guard_head, baseline_head, input_archive_sha256 and
completion_archive_sha256 (null when the completion is unavailable).

The staged interval source lacks production guard and held-position authority.
A valid configuration returns LIVE_PRODUCTION_AUTHORITY_REQUIRED before any
credential access, network request, state change, or order.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from threading import RLock
from typing import Callable

from core.compliance import owner
from core.isolation import checked_target
from execution import keys
from execution.transport import inquiry_guard
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, TradeFeeEvidence
from execution_accounts.instrument_terms import (
    E1UpbitTermsSource, TermsAuthority, UniverseTermsAuthority, authority_digest,
)
from execution_accounts.quotes import E1UpbitQuoteSource
from execution_accounts.universe import UniverseSlotSource, daily_bars
from execution_accounts.upbit_collector import E1UpbitSource, collect_order_fills, collect_trade_window
from execution_control.capability import digest
from execution_launch import evidence_objects as E
from execution_launch import protective_state as P
from execution_launch import protective_store as PS
from execution_launch.account_interval import UpbitIntervalSource
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import Composition, Coordinator, compose
from execution_launch.profile import preflight_profile, risk_policy
from execution_launch.strategy import evidence_digest, parse_protocol
from execution_launch.workflow import MAX_CONFIG_BYTES, read_file
from execution_orders.transport import Credentials, VenueOrderTransport
from tools.owner.launch import OwnerOperationError, OwnerRuntime, _object, _root, _time, read_window, serve
from tools.owner.planner import CurrentPlanner, MAX_PLAN_BYTES, parse_plan_template

MAX_AUDIT_BYTES = 1024 * 1024
MAX_SOURCE_DOCUMENT_BYTES = 1024 * 1024
MAX_AUTHORITY_CHECK_SECONDS = 30
_HASH = re.compile(r"[0-9a-f]{64}")
_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{1,18})?")
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_KINDS = frozenset({"opening_anchor", "coverage_review", "credential_identity", "history_retention",
                    "exclusive_fence", "transfer_scope", "instrument_terms", "fill_fees"})
_REQUIRED_KINDS = _KINDS - {"instrument_terms", "fill_fees"}
_CONFIG_FIELDS = frozenset({
    "schema_version", "kind", "profile", "program", "protocol", "capture", "review",
    "account_audit", "odds_template", "window", "evaluated_at", "monitor_until",
    "state_root", "head_root",
})
_AUDIT_FIELDS = frozenset({
    "schema_version", "kind", "account_scope", "deployment_window_digest",
    "baseline_anchor_sha256", "opening_anchor", "coverage", "trade_fees",
    "source_documents", "terms_authority",
})


class LiveError(OwnerOperationError):
    """Fixed diagnostic codes only; private paths, keys and payloads never enter output."""


def _need(ok: bool, code: str) -> None:
    if not ok:
        raise LiveError(code)


def _aware(value: object) -> bool:
    return type(value) is datetime and value.utcoffset() is not None


def _sha(value: object) -> str:
    _need(type(value) is str and _HASH.fullmatch(value) is not None, "LIVE_DIGEST_REQUIRED")
    return value


def _amount(value: object) -> Decimal:
    _need(type(value) is str and _MONEY.fullmatch(value) is not None, "LIVE_EXACT_AMOUNT_REQUIRED")
    return Decimal(value)


def _path(value: object) -> str:
    _need(type(value) is str and 0 < len(value) <= 4096 and "\x00" not in value, "LIVE_PATH_REQUIRED")
    return value


def _schema(body: object, allowed: set[str] | frozenset[str], code: str) -> dict:
    _need(type(body) is dict and set(body) == set(allowed), code)
    return body


def _dataclass_body(body: object, kind: type) -> dict:
    return _schema(body, {field.name for field in fields(kind)}, "LIVE_ACCOUNT_AUDIT_SCHEMA_INVALID")


class _LiveLock:
    """Exclusive non-blocking OS file lock preventing concurrent controlled live processes."""

    def __init__(self, root: Path) -> None:
        target = checked_target(root / "live.lock", "live runtime lock", within=root)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o600)
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
                os.fsync(fd)
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise LiveError("LIVE_LOCK_ALREADY_HELD") from None
        self._fd: int | None = fd
        self._lock = RLock()

    def release(self) -> None:
        with self._lock:
            fd = self._fd
            if fd is None:
                return
            self._fd = None
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                try:
                    os.close(fd)
                except OSError:
                    pass


def load_live_credentials(account_scope: str, *, key_reader: Callable = keys.read) -> Callable[[str, str], Credentials]:
    """Load Upbit order keys and verify strict separation from Upbit inquiry keys."""
    _need(type(account_scope) is str and _ID.fullmatch(account_scope) is not None, "LIVE_ACCOUNT_SCOPE_REQUIRED")
    def _resolve(venue: str, scope: str) -> Credentials:
        _need(venue == "upbit" and scope == account_scope, "LIVE_CREDENTIAL_SCOPE_MISMATCH")
        try:
            inq_ak, inq_sk = key_reader(("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"))
        except keys.KeyMissing:
            raise LiveError("LIVE_INQUIRY_CREDENTIALS_REQUIRED") from None
        try:
            ord_ak, ord_sk = key_reader(("UPBIT_ORDER_ACCESS_KEY", "UPBIT_ORDER_SECRET_KEY"))
        except keys.KeyMissing:
            raise LiveError("LIVE_ORDER_CREDENTIALS_REQUIRED") from None
        _need(all(type(v) is str and 0 < len(v) <= 4096 and not any(ord(c) < 32 or ord(c) == 127 for c in v)
                  for v in (inq_ak, inq_sk, ord_ak, ord_sk)), "LIVE_ORDER_CREDENTIALS_REQUIRED")
        _need(len({inq_ak, inq_sk} & {ord_ak, ord_sk}) == 0 and ord_ak != ord_sk,
              "LIVE_ORDER_INQUIRY_KEY_COLLISION")
        return Credentials(venue="upbit", account_scope=account_scope, access_key=ord_ak, secret_key=ord_sk)

    _resolve("upbit", account_scope)
    return _resolve


@dataclass(frozen=True, kw_only=True)
class LiveAccountAudit:
    account_scope: str
    window_digest: str
    baseline_anchor_sha256: str
    anchor: OpeningAnchor
    coverage: CoverageEvidence
    fees: tuple[TradeFeeEvidence, ...]
    terms_authority: TermsAuthority | None
    source_documents: tuple[tuple[str, str, str], ...]
    raw_sha256: str
    universe_terms_authority: UniverseTermsAuthority | None = None


def parse_live_audit(raw: bytes) -> LiveAccountAudit:
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_AUDIT_BYTES, "LIVE_ACCOUNT_AUDIT_TOO_LARGE")
    body = _object(raw)
    optional = {"universe_terms_authority"} if type(body) is dict and "universe_terms_authority" in body else set()
    _schema(body, _AUDIT_FIELDS | optional, "LIVE_ACCOUNT_AUDIT_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] in ("tradegen-controlled-live-audit/1", "tradegen-flat-account-rehearsal-audit/1"),
          "LIVE_ACCOUNT_AUDIT_KIND_INVALID")
    scope = body["account_scope"]
    _need(type(scope) is str and _ID.fullmatch(scope) is not None, "LIVE_ACCOUNT_SCOPE_REQUIRED")
    a = _dataclass_body(body["opening_anchor"], OpeningAnchor)
    _need(a["account_scope"] == scope
          and a["inventory_and_open_orders"] in ("verified-zero", "reviewed-snapshot"),
          "LIVE_ANCHOR_INVALID")
    anchor = OpeningAnchor(
        account_scope=scope, origin=_time(a["origin"]), cash_krw=_amount(a["cash_krw"]),
        source_sha256=_sha(a["source_sha256"]), inventory_and_open_orders=a["inventory_and_open_orders"],
    )
    c = _dataclass_body(body["coverage"], CoverageEvidence)
    _need(c["account_scope"] == scope, "LIVE_ACCOUNT_SCOPE_MISMATCH")
    requirements = {
        "identity_binding": "reviewed-credential-to-main-pocket",
        "history_retention": "reviewed-complete-since-origin",
        "transfer_scope": "reviewed-no-unreported-flows-or-pocket-transfers",
        "account_mode": "reviewed-krw-spot-cash-only",
    }
    _need(all(c[name] == value for name, value in requirements.items()), "LIVE_SOURCE_OBLIGATIONS_REQUIRED")
    coverage = CoverageEvidence(
        account_scope=scope, source_sha256=_sha(c["source_sha256"]),
        **{name: _time(c[name]) for name in ("history_from", "history_through", "quiescent_from", "quiescent_until")},
        **requirements,
    )
    _need(coverage.history_from <= anchor.origin <= coverage.history_through
          and coverage.quiescent_from < coverage.quiescent_until, "LIVE_COVERAGE_SPAN_INVALID")
    docs = body["source_documents"]
    _need(type(docs) is list and 6 <= len(docs) <= 64, "LIVE_SOURCE_DOCUMENTS_REQUIRED")
    documents, by_kind = [], {}
    for row in docs:
        _schema(row, {"kind", "path", "sha256"}, "LIVE_SOURCE_DOCUMENT_SCHEMA_INVALID")
        kind = row["kind"]
        _need(type(kind) is str and kind in _KINDS and (kind == "fill_fees" or kind not in by_kind),
              "LIVE_SOURCE_DOCUMENT_KIND_INVALID")
        sha = _sha(row["sha256"])
        by_kind.setdefault(kind, []).append(sha)
        documents.append((kind, _path(row["path"]), sha))
    _need(_REQUIRED_KINDS <= set(by_kind), "LIVE_SOURCE_DOCUMENTS_REQUIRED")
    _need(anchor.source_sha256 == by_kind["opening_anchor"][0]
          and coverage.source_sha256 == by_kind["coverage_review"][0], "LIVE_SOURCE_DOCUMENT_BINDING_INVALID")
    raw_fees = body["trade_fees"]
    _need(type(raw_fees) is list and len(raw_fees) <= 4096, "LIVE_FEE_EVIDENCE_INVALID")
    fees, seen = [], set()
    for row in raw_fees:
        _dataclass_body(row, TradeFeeEvidence)
        _need(all(type(row[name]) is str and _ID.fullmatch(row[name]) is not None for name in ("order_id", "fill_id")),
              "LIVE_FEE_EVIDENCE_INVALID")
        key = (row["order_id"], row["fill_id"])
        _need(key not in seen and _sha(row["source_sha256"]) in by_kind.get("fill_fees", ()),
              "LIVE_FEE_DOCUMENT_REQUIRED")
        seen.add(key)
        fees.append(TradeFeeEvidence(order_id=row["order_id"], fill_id=row["fill_id"],
                                     fee_krw=_amount(row["fee_krw"]), source_sha256=row["source_sha256"]))
    terms = None
    if body["terms_authority"] is not None:
        t = _dataclass_body(body["terms_authority"], TermsAuthority)
        _need(t["account_scope"] == scope and t["provenance_sha256"] in by_kind.get("instrument_terms", ())
              and t["identity_binding_sha256"] == by_kind["credential_identity"][0],
              "LIVE_TERMS_DOCUMENT_BINDING_INVALID")
        terms = TermsAuthority(
            account_scope=scope, symbol=t["symbol"],
            **{name: _amount(t[name]) for name in ("lot_size", "min_quantity", "maximum_notional_krw")},
            provenance_sha256=_sha(t["provenance_sha256"]),
            identity_binding_sha256=_sha(t["identity_binding_sha256"]),
            valid_from=_time(t["valid_from"]), valid_until=_time(t["valid_until"]),
        )
        authority_digest(terms)
    universe_terms = None
    if body.get("universe_terms_authority") is not None:
        u = _dataclass_body(body["universe_terms_authority"], UniverseTermsAuthority)
        _need(terms is None and u["account_scope"] == scope
              and u["provenance_sha256"] in by_kind.get("instrument_terms", ())
              and u["identity_binding_sha256"] == by_kind["credential_identity"][0],
              "LIVE_TERMS_DOCUMENT_BINDING_INVALID")
        universe_terms = UniverseTermsAuthority(
            account_scope=scope, universe_sha256=_sha(u["universe_sha256"]),
            **{name: _amount(u[name]) for name in ("lot_size", "min_quantity", "maximum_notional_krw")},
            provenance_sha256=_sha(u["provenance_sha256"]),
            identity_binding_sha256=_sha(u["identity_binding_sha256"]),
            valid_from=_time(u["valid_from"]), valid_until=_time(u["valid_until"]),
        )
        authority_digest(universe_terms)
    return LiveAccountAudit(
        account_scope=scope, window_digest=_sha(body["deployment_window_digest"]),
        baseline_anchor_sha256=_sha(body["baseline_anchor_sha256"]), anchor=anchor,
        coverage=coverage, fees=tuple(fees), terms_authority=terms,
        source_documents=tuple(documents), raw_sha256=hashlib.sha256(raw).hexdigest(),
        universe_terms_authority=universe_terms,
    )


def _terms_authority(profile, audit: LiveAccountAudit):
    universe = profile.universe_rule_sha256 is not None
    authority = audit.universe_terms_authority if universe else audit.terms_authority
    other = audit.terms_authority if universe else audit.universe_terms_authority
    if authority is None and other is None:
        return None
    _need(other is None and authority is not None
          and (authority.universe_sha256 == profile.universe_rule_sha256 if universe
               else authority.symbol == profile.symbol)
          and authority_digest(authority) == profile.instrument_rules.source_digest,
          "LIVE_TERMS_PROFILE_MISMATCH")
    return authority


def verify_source_documents(audit: LiveAccountAudit) -> None:
    _need(type(audit) is LiveAccountAudit, "LIVE_ACCOUNT_AUDIT_REQUIRED")
    for _kind, path, sha in audit.source_documents:
        suffix = Path(path).suffix
        _need(suffix in (".json", ".md", ".txt", ".pdf"), "LIVE_SOURCE_DOCUMENT_TYPE_INVALID")
        raw = read_file(path, MAX_SOURCE_DOCUMENT_BYTES, suffix=suffix)
        _need(hashlib.sha256(raw).hexdigest() == sha, "LIVE_SOURCE_DOCUMENT_CHANGED")


class _ReadGuard:
    """Fresh signed owner/code/source/implementation gate for live E1 inquiry reads."""

    def __init__(self, composition: Composition, audit: LiveAccountAudit, *, clock: Callable, monitor_until: datetime):
        _need(type(composition) is Composition and type(audit) is LiveAccountAudit and callable(clock),
              "LIVE_FIXED_COMPOSITION_REQUIRED")
        self._composition, self._audit = composition, audit
        self._clock, self._until = clock, monitor_until
        self._expires, self._failed, self._last = None, False, None
        self._lock = RLock()

    def _time_bounds(self, now: datetime) -> None:
        _need(_aware(now) and (self._last is None or now >= self._last), "LIVE_CLOCK_INVALID")
        self._last = now
        c = self._audit.coverage
        _need(c.quiescent_from <= now <= c.quiescent_until and now <= c.history_through
              and now <= self._until, "LIVE_ACCOUNT_FENCE_EXPIRED_OR_FUTURE")
        if self._expires is not None:
            _need(now < self._expires, "LIVE_REVIEW_EXPIRED")

    def check(self) -> None:
        with self._lock:
            _need(not self._failed, "LIVE_READ_AUTHORITY_LATCHED")
            try:
                now = self._clock()
                self._time_bounds(now)
                comp = self._composition
                bundle = comp.verifiers.assess_bundle(comp.profile, comp.evidence, comp.driver)
                body = bundle.body
                _need(body["audit_sha256"] == self._audit.raw_sha256, "LIVE_SIGNED_AUDIT_MISMATCH")
                expires = _time(body["expires_at"])
                _need(self._until < expires, "LIVE_WINDOW_EXCEEDS_REVIEW")
                _need(bundle.assessment.research_review_ready, "LIVE_QUALIFIED_REVIEW_REQUIRED")
                finished = self._clock()
                _need(_aware(finished) and _aware(bundle.verified_at)
                      and now <= bundle.verified_at <= finished < expires
                      and finished - now <= timedelta(seconds=MAX_AUTHORITY_CHECK_SECONDS),
                      "LIVE_AUTHORITY_CHECK_TOO_LATE")
                self._expires = expires
                self._time_bounds(finished)
            except Exception:
                self._failed = True
                raise

    def time_check(self) -> None:
        with self._lock:
            _need(not self._failed, "LIVE_READ_AUTHORITY_LATCHED")
            try:
                _need(self._expires is not None, "LIVE_READ_AUTHORITY_NOT_CHECKED")
                self._time_bounds(self._clock())
            except Exception:
                self._failed = True
                raise

    def transport_check(self, stage: str) -> None:
        if stage == "before_headers":
            self.check()
        else:
            self.time_check()


class _AccountSource:
    def __init__(self, source: E1UpbitSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitSource and type(guard) is _ReadGuard, "LIVE_FIXED_SOURCE_REQUIRED")
        self._source, self._guard, self.account_scope = source, guard, source.account_scope

    def fetch(self, path, params):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            receipt = self._source.fetch(path, params)
        self._guard.time_check()
        return receipt


class _QuoteSource:
    def __init__(self, source: E1UpbitQuoteSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitQuoteSource and type(guard) is _ReadGuard, "LIVE_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read(self, symbol=None):
        source = self._source if symbol is None else replace(self._source, symbol=symbol)
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = source.read()
        self._guard.time_check()
        return result


class _TermsSource:
    def __init__(self, source: E1UpbitTermsSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitTermsSource and type(guard) is _ReadGuard, "LIVE_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read(self, symbol=None):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read() if symbol is None else self._source.read(symbol)
        self._guard.time_check()
        return result


class _SlotSource:
    def __init__(self, source: UniverseSlotSource, guard: _ReadGuard):
        _need(type(source) is UniverseSlotSource and type(guard) is _ReadGuard, "LIVE_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read_flags(self):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read_flags()
        self._guard.time_check()
        return result

    def read_tickers(self, markets):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read_tickers(markets)
        self._guard.time_check()
        return result


def default_protective_limits() -> PS.StoreLimits:
    return PS.StoreLimits(
        object_limits=E.ObjectLimits(
            chunk_bytes=65536, max_payload_bytes=1024 * 1024, max_chunks=32, max_manifest_bytes=16384,
        ),
        object_budget=E.StoreBudget(max_bytes=64 * 1024 * 1024, max_objects=16384),
        max_journal_bytes=16 * 1024 * 1024,
        max_records=50000,
    )


def protective_store_for_deployment(*, root: Path, head_root: Path, window, profile, driver, identity,
                                    evidence, audit_sha256: str, monitor_until: datetime,
                                    code_sha256: str | None = None) -> PS.ProtectiveStore:
    """Build the deployment-bound ProtectiveStore handle; caller/operator provisions head separately."""
    _ = (driver, audit_sha256)
    c_sha = identity.deployment_code_sha256 if code_sha256 is None else code_sha256
    policy = P.ManagementPolicy(
        management_id=window.deployment_id,
        account_scope=profile.account_scope,
        venue=profile.venue,
        market=profile.market,
        quote_currency=profile.quote_currency,
        symbol=profile.symbol,
        code_sha256=c_sha,
        strategy_sha256=evidence.protocol.strategy_code_sha256,
        risk_policy_sha256=digest(risk_policy(profile)),
        holding_deadline=window.end,
        monitor_until=monitor_until,
    )
    binding = PS.StoreBinding(
        driver_identity_sha256=digest(identity),
        research_sha256=evidence_digest(evidence.result),
        source_sha256=evidence.result.inputs_digest,
    )
    return PS.ProtectiveStore(
        root=root / ("protective-" + window.deployment_id),
        head_root=head_root,
        head_name="protective-" + window.deployment_id,
        policy=policy,
        binding=binding,
        limits=default_protective_limits(),
    )


def load_live_config(raw: bytes) -> dict:
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_CONFIG_BYTES, "LIVE_CONFIG_TOO_LARGE")
    body = _object(raw)
    optional = {"history_storage"} if type(body) is dict and "history_storage" in body else set()
    _schema(body, _CONFIG_FIELDS | optional, "LIVE_CONFIG_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] == "tradegen-controlled-live/1", "LIVE_CONFIG_KIND_INVALID")
    for name in (_CONFIG_FIELDS | optional) - {"schema_version", "kind", "evaluated_at", "monitor_until"}:
        _path(body[name])
    _time(body["evaluated_at"])
    _time(body["monitor_until"])
    return body


def build_live(config_path: str, *, clock: Callable[[], datetime],
               key_reader: Callable = keys.read,
               bars_reader: Callable = daily_bars) -> OwnerRuntime:
    """Construct the controlled live OwnerRuntime with exclusive lock, separate order keys, and A2 store."""
    _need(callable(clock) and callable(key_reader) and callable(bars_reader), "LIVE_CLOCK_REQUIRED")
    config = load_live_config(read_file(config_path, MAX_CONFIG_BYTES))
    # This source can construct a preview. It cannot attest coverage or commit the
    # chronological guard transaction at a live controller boundary.
    intervals = UpbitIntervalSource(trade_window_collector=collect_trade_window,
                                    order_fill_collector=collect_order_fills)
    _need(intervals.execution_ready, "LIVE_PRODUCTION_AUTHORITY_REQUIRED")
    root = _root(Path(config["state_root"]))
    _need(not root.is_relative_to(Path.home() / ".tradegen"), "LIVE_ISOLATED_STATE_REQUIRED")
    lock = _LiveLock(root)
    try:
        hroot = Path(config["head_root"])
        protocol = parse_protocol(read_file(config["protocol"], MAX_CONFIG_BYTES))
        window = read_window(config["window"], universe=protocol.universe_rule_sha256 is not None)
        until = _time(config["monitor_until"])
        _need(window.end <= until <= window.end + timedelta(days=1), "LIVE_MONITOR_SPAN_INVALID")
        raw_audit = read_file(config["account_audit"], MAX_AUDIT_BYTES)
        audit = parse_live_audit(raw_audit)
        _need(audit.window_digest == digest(window), "LIVE_AUDIT_WINDOW_MISMATCH")
        creds_fn = load_live_credentials(audit.account_scope, key_reader=key_reader)
        now = clock()
        _need(_aware(now) and now < window.start, "LIVE_WINDOW_ALREADY_STARTED")
        _need(audit.coverage.quiescent_from <= now <= until <= audit.coverage.quiescent_until
              and until <= audit.coverage.history_through, "LIVE_ACCOUNT_FENCE_INCOMPLETE")

        # Closing an older arming requires a reconciled startup unit. Reading
        # config, or a failed build, must never mutate the owner's log.
        snap = owner.load_owner_snapshot(now)
        _need(snap.ok, "LIVE_OWNER_LOG_INVALID")
        _need(not snap.armed_sessions, "LIVE_RECONCILED_STARTUP_REQUIRED")

        store = CheckpointStore(root=root)
        head = BaselineHead(root=hroot, name="account-baseline", chain=CheckpointChain(store))
        state = store.load(expected_head=head.read())
        _need(state.account_scope == audit.account_scope and state.anchor_sha256 == audit.baseline_anchor_sha256,
              "LIVE_BASELINE_AUDIT_MISMATCH")
        _need(timedelta(0) <= now - state.asof <= timedelta(seconds=30), "LIVE_BASELINE_STALE_OR_FUTURE")

        comp = compose(
            profile_path=config["profile"], program_path=config["program"], protocol_path=config["protocol"],
            capture_path=config["capture"], review_path=config["review"], evaluated_at=_time(config["evaluated_at"]),
            window=window, clock=clock, head_root=hroot, history_storage_path=config.get("history_storage"),
        )
        _need((comp.profile.venue, comp.profile.market, comp.profile.quote_currency) == ("upbit", "spot", "KRW")
              and comp.profile.account_scope == audit.account_scope, "LIVE_PROFILE_SCOPE_MISMATCH")
        _need(preflight_profile(comp.profile, now=clock()).profile_complete, "LIVE_PROFILE_INCOMPLETE")

        template_plan = parse_plan_template(
            read_file(config["odds_template"], MAX_PLAN_BYTES),
            default_symbol=comp.profile.symbol.split("-", 1)[1],
        )

        guard = _ReadGuard(comp, audit, clock=clock, monitor_until=until)
        guard.check()
        verify_source_documents(audit)
        _need(hashlib.sha256(read_file(config["account_audit"], MAX_AUDIT_BYTES)).hexdigest() == audit.raw_sha256,
              "LIVE_ACCOUNT_AUDIT_CHANGED")
        guard.check()

        protective = protective_store_for_deployment(
            root=root, head_root=hroot, window=window, profile=comp.profile,
            driver=comp.driver, identity=comp.identity, evidence=comp.evidence,
            audit_sha256=audit.raw_sha256, monitor_until=until,
        )
        try:
            protective.head.read()
        except Exception:
            raise LiveError("LIVE_PROTECTIVE_STORE_NOT_INITIALIZED") from None

        source = _AccountSource(E1UpbitSource(account_scope=audit.account_scope, state_directory=root, clock=clock), guard)

        def prefetch(previous):
            return intervals.collect(
                source, previous=previous, anchor=audit.anchor, coverage=audit.coverage,
                clock=clock, trade_fees=audit.fees,
            )

        terms = None
        authority = _terms_authority(comp.profile, audit)
        if authority is not None:
            terms = _TermsSource(E1UpbitTermsSource(authority=authority, clock=clock), guard)

        universe = comp.profile.universe_rule_sha256 is not None
        order_transport = VenueOrderTransport(credentials=creds_fn)
        coordinator = Coordinator(
            mode="controlled",
            profile=comp.profile,
            evidence=comp.evidence,
            driver=comp.driver,
            implementation_verifier=comp.verifiers.implementation,
            adapters={"upbit": order_transport},
            account_source=intervals,
            account_prefetch=prefetch,
            trusted_head=head,
            quote_source=_QuoteSource(E1UpbitQuoteSource(symbol=comp.profile.symbol, clock=clock), guard),
            window=window,
            bar_seconds=comp.protocol.bar_seconds,
            monitor_until=until,
            clock=clock,
            history=comp.history,
            terms_source=terms,
            slot_source=_SlotSource(UniverseSlotSource(clock=clock), guard) if universe else None,
            program=comp.program if universe else None,
            protective_store=protective,
            owner_snapshot_provider=owner.load_owner_snapshot,
        )
        planner = CurrentPlanner(
            template=template_plan,
            symbol_provider=lambda: coordinator._profile.symbol,
            observation_provider=lambda: coordinator._observation,
            clock=clock,
            bars_reader=bars_reader,
        )
        return OwnerRuntime(coordinator, preparation_provider=planner, on_close=lock.release)
    except Exception:
        lock.release()
        raise


def inspect_startup(config_path: str, selection_path: str, *, clock: Callable) -> dict:
    """Reopen independently retained records using the existing dry, inspection-only reader."""
    from execution_control.dry_run import DryRunAdapter
    from execution_control.store import Journal
    from execution_launch.committed_startup import CommittedStartup
    from execution_launch.continuous_guard_commit import GuardChain, GuardCheckpointStore
    from execution_launch.profile import MAX_PROFILE_BYTES, parse_profile_json
    from execution_launch.research_bundle import open_explicit_store
    from execution_orders import upbit

    config = load_live_config(read_file(config_path, MAX_CONFIG_BYTES))
    root = _root(Path(config["state_root"]))
    _need(not root.is_relative_to(Path.home() / ".tradegen"), "LIVE_ISOLATED_STATE_REQUIRED")
    hroot = Path(config["head_root"])
    fields = {"schema_version", "sealed_root", "backup_root", "archive_head", "archive_limits",
              "guard_head", "baseline_head", "input_archive_sha256", "completion_archive_sha256"}
    selection = _schema(_object(read_file(selection_path, MAX_CONFIG_BYTES)), fields, "LIVE_STARTUP_RECORD_INVALID")
    _need(type(selection["schema_version"]) is int and selection["schema_version"] == 1,
          "LIVE_STARTUP_RECORD_INVALID")
    for key in ("sealed_root", "backup_root", "archive_head", "archive_limits", "guard_head", "baseline_head"):
        _path(selection[key])
    _need(selection["guard_head"] != selection["baseline_head"], "LIVE_STARTUP_RECORD_INVALID")
    input_digest = _sha(selection["input_archive_sha256"])
    completion = selection["completion_archive_sha256"]
    if completion is not None:
        _sha(completion)
    profile = parse_profile_json(read_file(config["profile"], MAX_PROFILE_BYTES))
    audit = parse_live_audit(read_file(config["account_audit"], MAX_AUDIT_BYTES))
    window = read_window(config["window"], universe=profile.universe_rule_sha256 is not None)
    _need(audit.account_scope == profile.account_scope and audit.window_digest == digest(window),
          "LIVE_STARTUP_BINDING_CHANGED")
    verify_source_documents(audit)
    archive = open_explicit_store(selection["sealed_root"], selection["backup_root"], selection["archive_head"],
                                  selection["archive_limits"])
    guard, baseline = GuardCheckpointStore(root=root), CheckpointStore(root=root)
    reader = CommittedStartup(archive_store=archive, journal=Journal(require_existing=True),
        guard_store=guard, guard_head=BaselineHead(root=hroot, name=selection["guard_head"], chain=GuardChain(guard)),
        baseline_store=baseline, baseline_head=BaselineHead(root=hroot, name=selection["baseline_head"],
                                                            chain=CheckpointChain(baseline)),
        profile=profile, adapters={"upbit": DryRunAdapter(upbit)}, isolated_state_root=root, clock=clock)
    result = reader.inspect(input_digest, completion)
    _need(result.account_anchor_sha256 == audit.baseline_anchor_sha256, "LIVE_STARTUP_BINDING_CHANGED")
    local_consistent = (result.durable_status == "CONSISTENT" and result.current_status == "FRESH"
                        and result.origin_ready and not result.permanent_halt
                        and not result.daily_stop_at_checkpoint and not result.path_entry_block)
    return {"command": "inspect-startup", "execution_ready": False, "new_entries_blocked": True,
            "local_status": "CONSISTENT" if local_consistent else "REVIEW_REQUIRED", "path_entry_block": result.path_entry_block,
            "source_authenticated": False, "durable_status": result.durable_status,
            "current_status": result.current_status, "restart_reason": result.reason,
            "account_observed_at": result.asof.isoformat(), "inspected_at": result.inspected_at.isoformat(),
            "permanent_halt": result.permanent_halt, "daily_stop_at_checkpoint": result.daily_stop_at_checkpoint,
            "origin_ready": result.origin_ready, "origin_reason": result.origin_reason,
            "app_open_count": result.app_open_count, "personal_open_count": result.personal_open_count,
            "unknown_order_count": result.unknown_order_count, "reason": "LIVE_PRODUCTION_AUTHORITY_REQUIRED"}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        _need(type(args) in (list, tuple) and all(type(v) is str for v in args), "LIVE_ARGUMENTS_INVALID")
        if tuple(args) in ((), ("--help",), ("-h",)):
            print(__doc__)
            return 0
        if len(args) == 4 and args[0] == "--config" and args[2] == "--inspect-startup":
            _need(all(v and not v.startswith("--") for v in (args[1], args[3])), "LIVE_ARGUMENTS_INVALID")
            report = inspect_startup(args[1], args[3], clock=lambda: datetime.now(timezone.utc))
            print(json.dumps(report, sort_keys=True, ensure_ascii=True))
            return 0 if report["local_status"] == "CONSISTENT" else 2
        _need(len(args) == 2 and args[0] == "--config" and bool(args[1]) and not args[1].startswith("--"),
              "LIVE_ARGUMENTS_INVALID")
        runtime = build_live(args[1], clock=lambda: datetime.now(timezone.utc))
        emit = lambda report: print(json.dumps(report, sort_keys=True, ensure_ascii=True), flush=True)
        emit({
            "command": "live-ready",
            "mode": "controlled",
            "live_order_transport": True,
            "held_positions_supported": True,
            "protective_hold_a2": True,
            "execution_ready": False,
            "commands": [
                "bootstrap", "odds", "prepare", "run", "status",
                "refresh-terms", "cancel-all", "exit", "stop", "disarm", "close",
            ],
        })
        serve(runtime, stream=sys.stdin, emit=emit)
        return 0
    except Exception as exc:
        from tools.owner.launch import _code
        code = str(exc) if type(exc) is LiveError else _code(exc)
        print(json.dumps({"execution_ready": False, "reasons": [code]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
