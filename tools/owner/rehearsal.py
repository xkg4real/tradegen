"""Explicit standalone flat-account rehearsal, using fixed read-only E1 sources.

    python -m tools.owner.rehearsal --config PRIVATE_CONFIG.json

The console accepts bootstrap/run/status/refresh-terms/stop/disarm/close. It
constructs only exact DryRunAdapters; there is no live mode, order credential
loader, signer, arming operation, import path or callback in the JSON schema.
Preparation from a serialized plan is not implemented: prepare reports the
existing missing-current-planner-input refusal rather than fabricating inputs.

Account evidence is not made complete by parsing JSON. The account-audit bytes
must be bound by an actually authenticated current detached owner review, and
the owner must have reviewed the referenced original evidence and exclusive
account fence. The original collector's coverage/identity/reconciliation checks
remain in force. Held inventory, fills, flows, gaps and missed boundaries stop
the flat interval producer. No setup/re-anchor is performed by this launcher.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
from threading import RLock
from typing import Callable

from execution.transport import inquiry_guard
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, TradeFeeEvidence
from execution_accounts.instrument_terms import E1UpbitTermsSource, TermsAuthority, authority_digest
from execution_accounts.quotes import E1UpbitQuoteSource
from execution_accounts.upbit_collector import E1UpbitSource
from execution_control.capability import digest
from execution_control.dry_run import DryRunAdapter
from execution_launch.account_interval import UpbitIntervalSource
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import Composition, Coordinator, compose
from execution_launch.profile import preflight_profile
from execution_launch.workflow import MAX_CONFIG_BYTES, read_file
from execution_orders import upbit
from tools.owner.launch import OwnerRuntime, _object, _root, _time, read_window, serve

MAX_AUDIT_BYTES = 1024 * 1024
MAX_SOURCE_DOCUMENT_BYTES = 1024 * 1024
MAX_AUTHORITY_CHECK_SECONDS = 30
_HASH = re.compile(r"[0-9a-f]{64}")
_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{1,18})?")
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_KINDS = frozenset({"opening_anchor", "coverage_review", "credential_identity", "history_retention",
                    "exclusive_fence", "transfer_scope", "instrument_terms", "fill_fees"})
_REQUIRED_KINDS = _KINDS - {"instrument_terms", "fill_fees"}
_CONFIG_FIELDS = frozenset({"schema_version", "kind", "profile", "program", "protocol", "capture", "review",
    "account_audit", "window", "evaluated_at", "monitor_until", "state_root", "head_root"})
_AUDIT_FIELDS = frozenset({"schema_version", "kind", "account_scope", "deployment_window_digest",
    "baseline_anchor_sha256", "opening_anchor", "coverage", "trade_fees", "source_documents", "terms_authority"})


class RehearsalError(ValueError):
    """Fixed diagnostic codes only; private paths/evidence never enter output."""


def _need(ok, code):
    if not ok:
        raise RehearsalError(code)


def _aware(value):
    return type(value) is datetime and value.utcoffset() is not None


def _sha(value):
    _need(type(value) is str and _HASH.fullmatch(value), "REHEARSAL_DIGEST_REQUIRED")
    return value


def _amount(value):
    _need(type(value) is str and _MONEY.fullmatch(value), "REHEARSAL_EXACT_AMOUNT_REQUIRED")
    return Decimal(value)


def _path(value):
    _need(type(value) is str and 0 < len(value) <= 4096 and "\x00" not in value,
          "REHEARSAL_PATH_REQUIRED")
    return value


def _schema(body, allowed, code):
    _need(type(body) is dict and set(body) == set(allowed), code)
    return body


def _dataclass_body(body, kind):
    return _schema(body, {field.name for field in fields(kind)}, "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")


@dataclass(frozen=True, kw_only=True)
class AccountAudit:
    account_scope: str
    window_digest: str
    baseline_anchor_sha256: str
    anchor: OpeningAnchor
    coverage: CoverageEvidence
    fees: tuple[TradeFeeEvidence, ...]
    terms_authority: TermsAuthority | None
    source_documents: tuple[tuple[str, str, str], ...]  # kind, explicit private path, reviewed bytes digest
    raw_sha256: str


def parse_account_audit(raw: bytes) -> AccountAudit:
    """Strict parsing only; no source/reviewer/credential authenticity is conferred."""
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_AUDIT_BYTES, "REHEARSAL_ACCOUNT_AUDIT_TOO_LARGE")
    body = _schema(_object(raw), _AUDIT_FIELDS, "REHEARSAL_ACCOUNT_AUDIT_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] == "tradegen-flat-account-rehearsal-audit/1", "REHEARSAL_ACCOUNT_AUDIT_KIND_INVALID")
    scope = body["account_scope"]
    _need(type(scope) is str and _ID.fullmatch(scope), "REHEARSAL_ACCOUNT_SCOPE_REQUIRED")
    a = _dataclass_body(body["opening_anchor"], OpeningAnchor)
    _need(a["account_scope"] == scope and a["inventory_and_open_orders"] == "verified-zero",
          "REHEARSAL_ZERO_ANCHOR_REQUIRED")
    anchor = OpeningAnchor(account_scope=scope, origin=_time(a["origin"]), cash_krw=_amount(a["cash_krw"]),
        source_sha256=_sha(a["source_sha256"]), inventory_and_open_orders=a["inventory_and_open_orders"])
    c = _dataclass_body(body["coverage"], CoverageEvidence)
    _need(c["account_scope"] == scope, "REHEARSAL_ACCOUNT_SCOPE_MISMATCH")
    requirements = {"identity_binding": "reviewed-credential-to-main-pocket",
        "history_retention": "reviewed-complete-since-origin",
        "transfer_scope": "reviewed-no-unreported-flows-or-pocket-transfers",
        "account_mode": "reviewed-krw-spot-cash-only"}
    _need(all(c[name] == value for name, value in requirements.items()), "REHEARSAL_SOURCE_OBLIGATIONS_REQUIRED")
    coverage = CoverageEvidence(account_scope=scope, source_sha256=_sha(c["source_sha256"]),
        **{name: _time(c[name]) for name in ("history_from", "history_through", "quiescent_from", "quiescent_until")},
        **requirements)
    _need(coverage.history_from <= anchor.origin <= coverage.history_through
          and coverage.quiescent_from < coverage.quiescent_until,
          "REHEARSAL_COVERAGE_SPAN_INVALID")
    docs = body["source_documents"]
    _need(type(docs) is list and 6 <= len(docs) <= 64, "REHEARSAL_SOURCE_DOCUMENTS_REQUIRED")
    documents, by_kind = [], {}
    for row in docs:
        _schema(row, {"kind", "path", "sha256"}, "REHEARSAL_SOURCE_DOCUMENT_SCHEMA_INVALID")
        kind = row["kind"]
        _need(type(kind) is str and kind in _KINDS and (kind == "fill_fees" or kind not in by_kind),
              "REHEARSAL_SOURCE_DOCUMENT_KIND_INVALID")
        sha = _sha(row["sha256"])
        by_kind.setdefault(kind, []).append(sha)
        documents.append((kind, _path(row["path"]), sha))
    _need(_REQUIRED_KINDS <= set(by_kind), "REHEARSAL_SOURCE_DOCUMENTS_REQUIRED")
    _need(anchor.source_sha256 == by_kind["opening_anchor"][0]
          and coverage.source_sha256 == by_kind["coverage_review"][0], "REHEARSAL_SOURCE_DOCUMENT_BINDING_INVALID")
    raw_fees = body["trade_fees"]
    _need(type(raw_fees) is list and len(raw_fees) <= 4096, "REHEARSAL_FEE_EVIDENCE_INVALID")
    fees, seen = [], set()
    for row in raw_fees:
        _dataclass_body(row, TradeFeeEvidence)
        _need(all(type(row[name]) is str and _ID.fullmatch(row[name]) for name in ("order_id", "fill_id")),
              "REHEARSAL_FEE_EVIDENCE_INVALID")
        key = row["order_id"], row["fill_id"]
        _need(key not in seen and _sha(row["source_sha256"]) in by_kind.get("fill_fees", ()),
              "REHEARSAL_FEE_DOCUMENT_REQUIRED")
        seen.add(key)
        fees.append(TradeFeeEvidence(order_id=row["order_id"], fill_id=row["fill_id"],
                                     fee_krw=_amount(row["fee_krw"]), source_sha256=row["source_sha256"]))
    terms = None
    if body["terms_authority"] is not None:
        t = _dataclass_body(body["terms_authority"], TermsAuthority)
        _need(t["account_scope"] == scope and t["provenance_sha256"] in by_kind.get("instrument_terms", ())
              and t["identity_binding_sha256"] == by_kind["credential_identity"][0],
              "REHEARSAL_TERMS_DOCUMENT_BINDING_INVALID")
        terms = TermsAuthority(account_scope=scope, symbol=t["symbol"],
            **{name: _amount(t[name]) for name in ("lot_size", "min_quantity", "maximum_notional_krw")},
            provenance_sha256=_sha(t["provenance_sha256"]),
            identity_binding_sha256=_sha(t["identity_binding_sha256"]),
            valid_from=_time(t["valid_from"]), valid_until=_time(t["valid_until"]))
        authority_digest(terms)
    return AccountAudit(account_scope=scope, window_digest=_sha(body["deployment_window_digest"]),
        baseline_anchor_sha256=_sha(body["baseline_anchor_sha256"]), anchor=anchor, coverage=coverage,
        fees=tuple(fees), terms_authority=terms, source_documents=tuple(documents),
        raw_sha256=hashlib.sha256(raw).hexdigest())


def verify_source_documents(audit: AccountAudit) -> None:
    """Compare the exact local source bytes named by the signed audit, without claiming their truth."""
    _need(type(audit) is AccountAudit, "REHEARSAL_ACCOUNT_AUDIT_REQUIRED")
    for _kind, path, sha in audit.source_documents:
        suffix = Path(path).suffix
        _need(suffix in (".json", ".md", ".txt", ".pdf"), "REHEARSAL_SOURCE_DOCUMENT_TYPE_INVALID")
        raw = read_file(path, MAX_SOURCE_DOCUMENT_BYTES, suffix=suffix)
        _need(hashlib.sha256(raw).hexdigest() == sha, "REHEARSAL_SOURCE_DOCUMENT_CHANGED")


class _ReadGuard:
    """Fresh signed code/source/implementation gate for fixed read-only sources.

    Every check authenticates current owner authority and the reviewed code,
    source and implementation, with no positive authority cache. The exclusive
    account fence is checked before and after this potentially expensive work.
    A failure latches the runtime. Owner attestation is not independent proof of
    the reviewed external account obligations.
    """
    def __init__(self, composition: Composition, audit: AccountAudit, *, clock: Callable, monitor_until: datetime):
        _need(type(composition) is Composition and type(audit) is AccountAudit and callable(clock),
              "REHEARSAL_FIXED_COMPOSITION_REQUIRED")
        self._composition, self._audit = composition, audit
        self._clock, self._until = clock, monitor_until
        self._expires, self._failed, self._last = None, False, None
        self._lock = RLock()

    def _time_bounds(self, now):
        _need(_aware(now) and (self._last is None or now >= self._last), "REHEARSAL_CLOCK_INVALID")
        self._last = now
        c = self._audit.coverage
        _need(c.quiescent_from <= now <= c.quiescent_until and now <= c.history_through
              and now <= self._until, "REHEARSAL_ACCOUNT_FENCE_EXPIRED_OR_FUTURE")
        if self._expires is not None:
            _need(now < self._expires, "REHEARSAL_REVIEW_EXPIRED")

    def check(self):
        with self._lock:
            _need(not self._failed, "REHEARSAL_READ_AUTHORITY_LATCHED")
            try:
                now = self._clock()
                self._time_bounds(now)
                comp = self._composition
                bundle = comp.verifiers.assess_bundle(comp.profile, comp.evidence, comp.driver)
                body = bundle.body
                _need(body["audit_sha256"] == self._audit.raw_sha256, "REHEARSAL_SIGNED_AUDIT_MISMATCH")
                expires = _time(body["expires_at"])
                _need(self._until < expires, "REHEARSAL_WINDOW_EXCEEDS_REVIEW")
                _need(bundle.assessment.research_review_ready, "REHEARSAL_QUALIFIED_REVIEW_REQUIRED")
                finished = self._clock()
                _need(_aware(finished) and _aware(bundle.verified_at)
                      and now <= bundle.verified_at <= finished < expires
                      and finished - now <= timedelta(seconds=MAX_AUTHORITY_CHECK_SECONDS),
                      "REHEARSAL_AUTHORITY_CHECK_TOO_LATE")
                self._expires = expires
                self._time_bounds(finished)
            except Exception:
                self._failed = True
                raise

    def time_check(self):
        """Recheck the complete request/response interval without restamping authority."""
        with self._lock:
            _need(not self._failed, "REHEARSAL_READ_AUTHORITY_LATCHED")
            try:
                _need(self._expires is not None, "REHEARSAL_READ_AUTHORITY_NOT_CHECKED")
                self._time_bounds(self._clock())
            except Exception:
                self._failed = True
                raise

    def transport_check(self, stage):
        # Full fresh owner/code/source authentication on EVERY request attempt,
        # including the second terms GET and any transport retry. Other stages
        # check elapsed time after headers, response and pacing before admission.
        if stage == "before_headers":
            self.check()
        else:
            self.time_check()


class _AccountSource:
    def __init__(self, source: E1UpbitSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitSource and type(guard) is _ReadGuard, "REHEARSAL_FIXED_SOURCE_REQUIRED")
        self._source, self._guard, self.account_scope = source, guard, source.account_scope

    def fetch(self, path, params):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            receipt = self._source.fetch(path, params)
        self._guard.time_check()
        return receipt


class _QuoteSource:
    def __init__(self, source: E1UpbitQuoteSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitQuoteSource and type(guard) is _ReadGuard, "REHEARSAL_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read(self):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read()
        self._guard.time_check()
        return result


class _TermsSource:
    def __init__(self, source: E1UpbitTermsSource, guard: _ReadGuard):
        _need(type(source) is E1UpbitTermsSource and type(guard) is _ReadGuard, "REHEARSAL_FIXED_SOURCE_REQUIRED")
        self._source, self._guard = source, guard

    def read(self):
        self._guard.time_check()
        with inquiry_guard(self._guard.transport_check):
            result = self._source.read()
        self._guard.time_check()
        return result


def load_config(raw: bytes) -> dict:
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_CONFIG_BYTES, "REHEARSAL_CONFIG_TOO_LARGE")
    body = _schema(_object(raw), _CONFIG_FIELDS, "REHEARSAL_CONFIG_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] == "tradegen-flat-account-rehearsal/1", "REHEARSAL_CONFIG_KIND_INVALID")
    for name in _CONFIG_FIELDS - {"schema_version", "kind", "evaluated_at", "monitor_until"}:
        _path(body[name])
    _time(body["evaluated_at"]); _time(body["monitor_until"])
    return body


def build_rehearsal(config_path: str, *, clock: Callable) -> OwnerRuntime:
    """Construct the one fixed composition; no account/quote request happens until a console command.

    Existing state/head/history bindings and current authentic review are mandatory.
    This function never seeds or repairs them. The injected clock is application code,
    not an input field; the standalone main uses the actual UTC wall clock.
    """
    _need(callable(clock), "REHEARSAL_CLOCK_REQUIRED")
    config = load_config(read_file(config_path, MAX_CONFIG_BYTES))
    root = _root(Path(config["state_root"]))
    _need(not root.is_relative_to(Path.home() / ".tradegen"), "REHEARSAL_ISOLATED_STATE_REQUIRED")
    hroot = Path(config["head_root"])
    window = read_window(config["window"])
    until = _time(config["monitor_until"])
    _need(window.end <= until <= window.end + timedelta(days=1), "REHEARSAL_MONITOR_SPAN_INVALID")
    raw_audit = read_file(config["account_audit"], MAX_AUDIT_BYTES)
    audit = parse_account_audit(raw_audit)
    _need(audit.window_digest == digest(window), "REHEARSAL_AUDIT_WINDOW_MISMATCH")
    now = clock()
    _need(_aware(now) and now < window.start, "REHEARSAL_WINDOW_ALREADY_STARTED")
    _need(audit.coverage.quiescent_from <= now <= until <= audit.coverage.quiescent_until
          and until <= audit.coverage.history_through, "REHEARSAL_ACCOUNT_FENCE_INCOMPLETE")
    store = CheckpointStore(root=root)
    head = BaselineHead(root=hroot, name="account-baseline", chain=CheckpointChain(store))
    state = store.load(expected_head=head.read())
    _need(state.account_scope == audit.account_scope and state.anchor_sha256 == audit.baseline_anchor_sha256,
          "REHEARSAL_BASELINE_AUDIT_MISMATCH")
    _need(timedelta(0) <= now - state.asof <= timedelta(seconds=30), "REHEARSAL_BASELINE_STALE_OR_FUTURE")
    comp = compose(profile_path=config["profile"], program_path=config["program"], protocol_path=config["protocol"],
        capture_path=config["capture"], review_path=config["review"], evaluated_at=_time(config["evaluated_at"]),
        window=window, clock=clock, head_root=hroot)
    _need((comp.profile.venue, comp.profile.market, comp.profile.quote_currency) == ("upbit", "spot", "KRW")
          and comp.profile.account_scope == audit.account_scope, "REHEARSAL_PROFILE_SCOPE_MISMATCH")
    _need(preflight_profile(comp.profile, now=clock()).profile_complete, "REHEARSAL_PROFILE_INCOMPLETE")
    guard = _ReadGuard(comp, audit, clock=clock, monitor_until=until)
    guard.check()  # actual current signature/code/source/implementation, before source construction or any E1 call
    verify_source_documents(audit)
    _need(hashlib.sha256(read_file(config["account_audit"], MAX_AUDIT_BYTES)).hexdigest() == audit.raw_sha256,
          "REHEARSAL_ACCOUNT_AUDIT_CHANGED")
    guard.check()  # file checks did not consume the review/fence/authority interval
    source = _AccountSource(E1UpbitSource(account_scope=audit.account_scope, state_directory=root, clock=clock), guard)
    intervals = UpbitIntervalSource()

    def prefetch(previous):
        return intervals.collect(source, previous=previous, anchor=audit.anchor, coverage=audit.coverage,
                                 clock=clock, trade_fees=audit.fees)

    terms = None
    if audit.terms_authority is not None:
        _need(audit.terms_authority.symbol == comp.profile.symbol
              and authority_digest(audit.terms_authority) == comp.profile.instrument_rules.source_digest,
              "REHEARSAL_TERMS_PROFILE_MISMATCH")
        terms = _TermsSource(E1UpbitTermsSource(authority=audit.terms_authority, clock=clock), guard)
    coordinator = Coordinator(mode="rehearsal", profile=comp.profile, evidence=comp.evidence, driver=comp.driver,
        implementation_verifier=comp.verifiers.implementation, adapters={"upbit": DryRunAdapter(upbit)},
        account_source=intervals, account_prefetch=prefetch, trusted_head=head,
        quote_source=_QuoteSource(E1UpbitQuoteSource(symbol=comp.profile.symbol, clock=clock), guard),
        window=window, bar_seconds=comp.protocol.bar_seconds, monitor_until=until, clock=clock,
        history=comp.history, terms_source=terms)
    return OwnerRuntime(coordinator)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        _need(type(args) in (list, tuple) and all(type(v) is str for v in args), "REHEARSAL_ARGUMENTS_INVALID")
        if tuple(args) in ((), ("--help",), ("-h",)):
            print(__doc__)
            return 0
        _need(len(args) == 2 and args[0] == "--config" and bool(args[1]) and not args[1].startswith("--"),
              "REHEARSAL_ARGUMENTS_INVALID")
        runtime = build_rehearsal(args[1], clock=lambda: datetime.now(timezone.utc))
        emit = lambda report: print(json.dumps(report, sort_keys=True, ensure_ascii=True), flush=True)
        emit({"command": "rehearsal-ready", "mode": "rehearsal", "live_order_transport": False,
              "account_requests_started": False, "held_positions_supported": False,
              "external_source_obligations_automatically_proven": False, "execution_ready": False,
              "commands": ["bootstrap", "run", "status", "refresh-terms", "stop", "disarm", "close"]})
        serve(runtime, stream=sys.stdin, emit=emit)
        return 0
    except Exception as exc:
        from tools.owner.launch import _code
        code = str(exc) if type(exc) is RehearsalError else _code(exc)
        print(json.dumps({"execution_ready": False, "reasons": [code]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
