"""Retain actual E1 GET attempts in existing immutable, backed raw archives.

All public values are finite archival observations, never source/coverage
authentication or trading permissions. Interrupted prefixes remain historical
facts; no automatic resume, provisioning, head adoption or current-use lease.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
from types import MappingProxyType

from execution.transport import UpbitReadEvent, capture_upbit_reads
from execution.upbit_inquiry import READ_CAPTURE_ENDPOINTS
from execution_accounts.collector import OpeningAnchor, CoverageEvidence, TradeFeeEvidence, SourceReceipt
from execution_accounts.model import RiskBaseline, content_digest
from execution_accounts.provider import EvidenceError
from execution_accounts.upbit_collector import E1UpbitSource, CollectionResult, collect_upbit
from execution_control.risk import RecoveryCheckpoint
from execution_launch import upbit_read_format as F
from execution_launch import research_bundle_format as B
from execution_launch import research_bundle_store as S
from execution_launch.evidence_objects import decode_reference


class ReadBatchArchiveError(ValueError):
    """Fixed, private-data-free READ_BATCH_* diagnostics."""


def _need(condition, code='READ_BATCH_CHAIN_INVALID'):
    if not condition:
        raise ReadBatchArchiveError(code)


class _Inert:
    @property
    def source_authenticated(self): return False

    @property
    def coverage_verified(self): return False

    @property
    def execution_ready(self): return False


@dataclass(frozen=True, kw_only=True)
class ReadBatchResult(_Inert):
    batch_id: str
    open_archive_digest: str
    last_confirmed_archive_digest: str
    final_archive_digest: str | None
    status: str
    failure_code: str | None
    collection: CollectionResult | None = field(repr=False)


@dataclass(frozen=True, kw_only=True)
class ReadBatchArchive(_Inert):
    batch_id: str
    last_archive_digest: str
    status: str
    records: tuple[F.ReadBatchRecord, ...] = field(repr=False)
    payloads: object = field(repr=False)
    final_archive_digest: str | None


def _store(store):
    _need(type(store) is S.BundleStore, 'READ_BATCH_STORE_REQUIRED')
    store._configuration()


def _code(exc, fallback='READ_BATCH_ARCHIVE_REFUSED'):
    if type(exc) in (ReadBatchArchiveError, F.ReadBatchFormatError) and str(exc) in F.ERROR_CODES:
        return str(exc)
    if type(exc) is S.BundleStoreError and str(exc) in ('BUNDLE_STORE_ALREADY_PUBLISHED', 'BUNDLE_STORE_ID_REUSED'):
        return 'READ_BATCH_ID_REUSED'
    # Foreign exception text, including apparent diagnostic strings, is never copied.
    return fallback


def _scope(record):
    body = record.body
    if record.kind in ('FETCH_BEGIN', 'ATTEMPT'):
        _need(('GET', body['path']) in READ_CAPTURE_ENDPOINTS)
    elif record.kind == 'FETCH_END' and body['receipt'] is not None:
        _need(('GET', body['receipt']['path']) in READ_CAPTURE_ENDPOINTS)


def _manifest(store, record, raw_body, limits):
    raw = F.record_bytes(record, limits=limits); _scope(record)
    present = record.kind == 'ATTEMPT' and record.body['body_status'] == 'PRESENT'
    _need(type(raw_body) is bytes if present else raw_body is None)
    payloads = {'record':raw}
    if present:
        _need(len(raw_body) == record.body['body_bytes']
              and hashlib.sha256(raw_body).hexdigest() == record.body['body_sha256'])
        payloads['body'] = raw_body
    names = {'record':'record.json', 'body':'response.bin'}
    files = tuple(B.BundleFile(logical_id=name, original_name=names[name], source_name=None,
        role='other_input', study_id=None, required=True, byte_count=len(value),
        sha256=hashlib.sha256(value).hexdigest(), payload_ref=store.preview_payload(value))
        for name, value in sorted(payloads.items()))
    observations = tuple(B.InputObservation(observation_id=item.logical_id, original_name=item.original_name,
        source_name=None, role='other_input', study_id=None, required=True, status='COLLECTED',
        logical_id=item.logical_id) for item in files)
    manifest = B.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED', run_id='upbit-'+record.batch_id,
        revision_id='read-v1-'+str(record.ordinal).zfill(5), attempt_id='upbit-'+record.batch_id,
        parent_bundle_sha256=record.previous_archive_digest, storage_policy_sha256=store.limits.policy_sha256,
        object_policy_sha256=store.limits.object_limits.policy_sha256, expected_candidates=None,
        inventory_complete=True, observed_inputs=observations, files=files)
    encoded = B.raw_archive_bytes(manifest, limits=store.limits.format_limits)
    return encoded, payloads, B.raw_archive_digest(manifest, limits=store.limits.format_limits)


def _read_one_locked(store, catalog, digest, limits, totals):
    """Bounded exact metadata admission BEFORE full primary/backup payload reads."""
    _need(F._hash(digest) and digest in catalog.entries)
    entry = catalog.entries[digest]
    _need(entry.row['kind'] == 'RAW_ARCHIVED' and entry.backed)
    reference = decode_reference(S._canonical(entry.row['manifest_ref']))
    _need(reference.payload_bytes <= min(store.limits.format_limits.max_manifest_bytes, 65536),
          'READ_BATCH_RESOURCE_LIMIT')
    raw = store._objects(False).read(reference)
    manifest, actual_digest = store._manifest('RAW_ARCHIVED', raw)
    _need(actual_digest == digest and manifest.expected_candidates is None and manifest.inventory_complete is True)
    names = tuple(item.logical_id for item in manifest.files)
    _need(names in (('record',), ('body', 'record')))
    observations = []
    for item in manifest.files:
        maximum = limits.max_record_bytes if item.logical_id == 'record' else limits.max_body_bytes
        _need(item.byte_count <= maximum, 'READ_BATCH_RESOURCE_LIMIT')
        _need(item.original_name == ('record.json' if item.logical_id == 'record' else 'response.bin')
              and item.role == 'other_input' and item.source_name is None and item.study_id is None
              and item.required is True)
        index = 0 if item.logical_id == 'record' else 1
        totals[index] += item.byte_count
        _need(totals[index] <= (limits.max_total_record_bytes if index == 0 else limits.max_total_body_bytes),
              'READ_BATCH_RESOURCE_LIMIT')
        observations.append(B.InputObservation(observation_id=item.logical_id, original_name=item.original_name,
            source_name=None, role='other_input', study_id=None, required=True, status='COLLECTED',
            logical_id=item.logical_id))
    _need(manifest.observed_inputs == tuple(observations))
    retained = store._validate_graph(catalog, digest, require_backup=True)
    _need(retained.manifest_bytes == raw)
    record = F.parse_record(retained.files['record'], limits=limits)
    body = retained.files.get('body')
    expected, payloads, expected_digest = _manifest(store, record, body, limits)
    _need(expected == raw and expected_digest == digest and dict(retained.files) == payloads)
    return record, body


def _chain(records, digests, payloads, limits):
    _need(records and records[0].kind == 'OPEN')
    batch, opened = records[0].batch_id, records[0].body
    _need(opened['limits_sha256'] == F.limits_digest(limits))
    clock = F.time_value(opened['started_at'])
    calls, attempts, active, phase, last, failed = 0, 0, None, None, None, False
    for index, record in enumerate(records):
        _need(record.batch_id == batch and record.ordinal == index
              and record.previous_archive_digest == (digests[index-1] if index else None))
        body = record.body
        if index == 0: continue
        if record.kind == 'FETCH_BEGIN':
            _need(active is None and not failed and body['call_ordinal'] == calls+1)
            when = F.time_value(body['requested_at']); _need(when >= clock); clock = when
            calls += 1; active = body; phase = None; last = None
        elif record.kind == 'ATTEMPT':
            _need(active is not None and body['call_ordinal'] == calls
                  and body['path'] == active['path'] and body['params'] == active['params'])
            previously_failed = failed
            if body['clock_status'] == 'OK':
                when = F.time_value(body['observed_at']); _need(when >= clock); clock = when
            else:
                failed = True
            if body['phase'] == 'BEFORE_SEND':
                expected = 1 if last is None else 2
                _need(not previously_failed and body['attempt'] == expected and (phase is None or
                    phase in ('RESPONSE', 'TRANSPORT_ERROR') and last['attempt'] == 1))
                if last is not None:
                    _need(last['clock_status'] == 'OK' and
                          (last['phase'] == 'TRANSPORT_ERROR' and last['error_code'] == 'CONNECTION_ERROR'
                           or last['phase'] == 'RESPONSE' and last['error_code'] is None
                           and last['body_status'] == 'PRESENT'
                           and (last['status_code'] == 429 or last['status_code'] >= 500)))
                attempts += 1; _need(attempts <= limits.max_attempts, 'READ_BATCH_RESOURCE_LIMIT')
            else:
                _need(not previously_failed and phase == 'BEFORE_SEND' and last['clock_status'] == 'OK'
                      and last['attempt'] == body['attempt'])
            phase = body['phase']; last = body
            if body['phase'] == 'RESPONSE' and (body['body_status'] != 'PRESENT' or body['error_code'] is not None):
                failed = True
        elif record.kind == 'FETCH_END':
            _need(active is not None and body['call_ordinal'] == calls)
            if body['status'] == 'RETURNED':
                receipt = body['receipt']
                _need(not failed and phase == 'RESPONSE' and last['clock_status'] == 'OK'
                      and last['body_status'] == 'PRESENT' and last['error_code'] is None and last['status_code'] == 200
                      and receipt['path'] == active['path'] and receipt['params'] == active['params']
                      and receipt['account_scope'] == opened['account_scope']
                      and receipt['received_at'] == last['observed_at'] and receipt['sha256'] == last['body_sha256'])
            else:
                failed = True
            active = None; phase = None; last = None
        elif record.kind == 'CLOSE':
            _need(index == len(records)-1 and body['records'] == tuple(enumerate(digests[:-1]))
                  and body['calls'] == calls and body['attempts'] == attempts)
            if body['clock_status'] == 'OK': _need(F.time_value(body['finished_at']) >= clock)
            if body['status'] == 'COLLECTED': _need(active is None and not failed and calls > 0)
        else:
            raise ReadBatchArchiveError('READ_BATCH_CHAIN_INVALID')
    return records[-1].body['status'] if records[-1].kind == 'CLOSE' else 'INCOMPLETE'


def read_upbit_read_batch(store, last_archive_digest, *, limits=F.DEFAULT_LIMITS):
    failure, result = None, None
    try:
        _store(store); F.checked_limits(limits)
        _need(F._hash(last_archive_digest), 'READ_BATCH_INPUT_INVALID')
        with store._locked():
            try:
                catalog = store._load()
                cursor, reverse, digests, bodies, totals, seen = last_archive_digest, [], [], {}, [0, 0], set()
                while cursor is not None:
                    _need(cursor not in seen and len(reverse) < limits.max_records, 'READ_BATCH_RESOURCE_LIMIT')
                    seen.add(cursor)
                    record, body = _read_one_locked(store, catalog, cursor, limits, totals)
                    reverse.append(record); digests.append(cursor)
                    if body is not None: bodies[record.ordinal] = body
                    cursor = record.previous_archive_digest
                records, ordered = tuple(reversed(reverse)), tuple(reversed(digests))
                status = _chain(records, ordered, bodies, limits)
                if records[-1].kind == 'CLOSE':
                    _need({key for key, entry in catalog.entries.items()
                           if entry.row['run_id'] == 'upbit-'+records[0].batch_id} == seen)
                _need(store._load() == catalog, 'READ_BATCH_ARCHIVE_REFUSED')
                result = ReadBatchArchive(batch_id=records[0].batch_id, last_archive_digest=last_archive_digest,
                    status=status, records=records, payloads=MappingProxyType(dict(sorted(bodies.items()))),
                    final_archive_digest=last_archive_digest if records[-1].kind == 'CLOSE' else None)
            except (ReadBatchArchiveError, F.ReadBatchFormatError) as exc:
                failure = exc
        if failure is not None: raise failure
        return result
    except Exception as exc:
        raise ReadBatchArchiveError(_code(exc)) from None


def _clock(clock, previous=None):
    try:
        value = clock()
    except Exception:
        return None, 'RAISED'
    try:
        value = F.time_value(F.stamp(value))
    except (ValueError, TypeError, OverflowError):
        return None, 'INVALID'
    return (None, 'ROLLBACK') if previous is not None and value < previous else (value, 'OK')


def _inputs(anchor, coverage, baseline, trade_fees, limits):
    _need(type(anchor) is OpeningAnchor and type(coverage) is CoverageEvidence
          and type(baseline) is RiskBaseline and type(trade_fees) is tuple
          and len(trade_fees) <= 100000, 'READ_BATCH_INPUT_INVALID')
    nodes, size = 0, 0
    classes = (OpeningAnchor, CoverageEvidence, RiskBaseline, TradeFeeEvidence, RecoveryCheckpoint)
    def walk(value, depth=0):
        nonlocal nodes, size
        nodes += 1
        _need(nodes <= 250000 and depth <= 12, 'READ_BATCH_RESOURCE_LIMIT')
        kind = type(value)
        if kind in classes:
            expected = {item.name for item in fields(kind)}
            actual = vars(value)
            _need(type(actual) is dict and len(actual) == len(expected)
                  and all(name in actual for name in expected), 'READ_BATCH_INPUT_INVALID')
            result = kind(**{name:walk(getattr(value, name), depth+1) for name in expected})
        elif kind is tuple:
            _need(len(value) <= 100000, 'READ_BATCH_RESOURCE_LIMIT')
            result = tuple(walk(item, depth+1) for item in value)
        elif kind is str:
            _need(len(value) <= 65536, 'READ_BATCH_RESOURCE_LIMIT'); size += len(value)*12
            result = value
        elif kind is Decimal:
            _need(value.is_finite(), 'READ_BATCH_INPUT_INVALID')
            # Inspect a bounded quantum without materializing a caller's huge
            # coefficient tuple. No quantization, rounding or value changes.
            exponent = next((power for power in range(-40, 41)
                             if value.same_quantum(Decimal((0, (1,), power)))), None)
            _need(exponent is not None and value.adjusted()-exponent+1 <= 60,
                  'READ_BATCH_INPUT_INVALID')
            size += 128; result = value
        elif kind is datetime: F.stamp(value); size += 32; result = value
        elif kind is date: size += 10; result = value
        elif value is None: size += 4; result = None
        else: raise ReadBatchArchiveError('READ_BATCH_INPUT_INVALID')
        _need(size <= limits.max_record_bytes, 'READ_BATCH_RESOURCE_LIMIT')
        return result
    snapshot = walk((anchor, coverage, baseline, trade_fees))
    _need(all(type(item) is TradeFeeEvidence for item in snapshot[3]), 'READ_BATCH_INPUT_INVALID')
    return snapshot


class _Batch:
    def __init__(self, source, store, batch_id, clock, limits, started):
        self.source, self.store, self.batch_id, self.clock, self.limits = source, store, batch_id, clock, limits
        self.scope, self.directory = source.account_scope, source.state_directory
        self.latest, self.records, self.digests = started, [], []
        self.total_body, self.total_record, self.calls, self.attempts = 0, 0, 0, 0
        self.sink_failed, self.failure = False, None

    @property
    def account_scope(self): return self.scope

    def source_check(self):
        _need(type(self.source) is E1UpbitSource and self.source.clock is self.clock
              and self.source.account_scope == self.scope
              and type(self.source.state_directory) is type(self.directory)
              and self.source.state_directory == self.directory, 'READ_BATCH_SOURCE_CHANGED')

    def append(self, kind, body, raw=None):
        try:
            # Storage is bound to the frozen OPEN, not mutable source fields.
            # An already-received response must survive a later source refusal.
            value = F.ReadBatchRecord(schema_version=1, batch_id=self.batch_id, ordinal=len(self.records),
                previous_archive_digest=self.digests[-1] if self.digests else None, kind=kind, body=body)
            encoded, payloads, digest = _manifest(self.store, value, raw, self.limits)
            added = len(payloads['record']); count = 0 if raw is None else len(raw)
            _need(len(self.records) < self.limits.max_records
                  and self.total_record+added <= self.limits.max_total_record_bytes
                  and self.total_body+count <= self.limits.max_total_body_bytes, 'READ_BATCH_RESOURCE_LIMIT')
            self.store.archive_raw(encoded, payloads, require_new=kind == 'OPEN')
            actual = self.store.read_raw(digest, require_backup=True)
            _need(actual.manifest_bytes == encoded and dict(actual.files) == payloads,
                  'READ_BATCH_ARCHIVE_REFUSED')
            self.records.append(value); self.digests.append(digest)
            self.total_record += added; self.total_body += count
        except Exception as exc:
            self.sink_failed = True; self.failure = _code(exc)
            raise ReadBatchArchiveError(self.failure) from None

    def admission(self, *, send=False):
        # Capacity estimates are not reservations against another writer/OS failure.
        remaining = 4 if send else 5
        _need(len(self.records)+remaining <= self.limits.max_records
              and self.total_record+remaining*self.limits.max_record_bytes <= self.limits.max_total_record_bytes
              and self.total_body+self.limits.max_body_bytes <= self.limits.max_total_body_bytes,
              'READ_BATCH_RESOURCE_LIMIT')
        if send: _need(self.attempts < self.limits.max_attempts, 'READ_BATCH_RESOURCE_LIMIT')
        else: _need(self.calls < self.limits.max_calls, 'READ_BATCH_RESOURCE_LIMIT')

    def event(self, event):
        try:
            _need(type(event) is UpbitReadEvent, 'READ_BATCH_TRANSPORT_REFUSED')
            if event.phase == 'BEFORE_SEND':
                self.source_check()
                self.admission(send=True); self.attempts += 1
            body = {item.name:getattr(event, item.name) for item in fields(UpbitReadEvent) if item.name != 'raw_body'}
            self.append('ATTEMPT', body, event.raw_body)
            self.source_check()
            if event.clock_status == 'OK':
                _need(event.observed_at >= self.latest, 'READ_BATCH_CLOCK_REFUSED')
                self.latest = event.observed_at
        except Exception as exc:
            self.failure = self.failure or _code(exc, 'READ_BATCH_TRANSPORT_REFUSED')
            raise ReadBatchArchiveError(self.failure) from None

    def fetch(self, path, params):
        try:
            self.source_check(); self.admission()
            _need(type(path) is str and ('GET', path) in READ_CAPTURE_ENDPOINTS
                  and type(params) is tuple, 'READ_BATCH_INPUT_INVALID')
            requested, state = _clock(self.clock, self.latest)
            _need(state == 'OK', 'READ_BATCH_CLOCK_REFUSED')
            self.latest = requested; self.calls += 1
            self.append('FETCH_BEGIN', dict(call_ordinal=self.calls, path=path, params=params, requested_at=requested))
        except Exception as exc:
            self.failure = self.failure or _code(exc, 'READ_BATCH_INPUT_INVALID')
            raise ReadBatchArchiveError(self.failure) from None
        try:
            with capture_upbit_reads(self.event, call_ordinal=self.calls, not_before=requested,
                                    max_body_bytes=self.limits.max_body_bytes):
                receipt = E1UpbitSource.fetch(self.source, path, params)
            self.source_check()
            _need(type(receipt) is SourceReceipt, 'READ_BATCH_SOURCE_CHANGED')
            last = self.records[-1]
            _need(last.kind == 'ATTEMPT' and last.body['phase'] == 'RESPONSE'
                  and last.body['body_status'] == 'PRESENT' and last.body['clock_status'] == 'OK'
                  and receipt.path == path and receipt.params == params and receipt.account_scope == self.scope
                  and F.stamp(receipt.received_at) == last.body['observed_at']
                  and receipt.sha256 == last.body['body_sha256'], 'READ_BATCH_SOURCE_CHANGED')
            info = {name:getattr(receipt, name) for name in
                    ('path', 'params', 'account_scope', 'received_at', 'server_time', 'sha256')}
            self.append('FETCH_END', dict(call_ordinal=self.calls, status='RETURNED', receipt=info, error_code=None))
            return receipt
        except Exception as exc:
            if self.failure is None:
                self.failure = _code(exc, 'READ_BATCH_COLLECTOR_REFUSED' if isinstance(exc, EvidenceError)
                                     else 'READ_BATCH_TRANSPORT_REFUSED')
            if not self.sink_failed:
                self.append('FETCH_END', dict(call_ordinal=self.calls, status='REFUSED', receipt=None,
                                             error_code=self.failure))
            raise ReadBatchArchiveError(self.failure) from None


def collect_retained_upbit_batch(source, *, store, batch_id, anchor, coverage, risk_baseline,
                                clock, trade_fees=(), limits=F.DEFAULT_LIMITS):
    try:
        F.checked_limits(limits); _store(store)
        _need(type(source) is E1UpbitSource and callable(clock) and source.clock is clock,
              'READ_BATCH_SOURCE_REQUIRED')
        _need(type(batch_id) is str and F._ID.fullmatch(batch_id) is not None, 'READ_BATCH_INPUT_INVALID')
        anchor, coverage, risk_baseline, trade_fees = _inputs(anchor, coverage, risk_baseline, trade_fees, limits)
        _need(type(source.account_scope) is str and source.account_scope == anchor.account_scope == coverage.account_scope
              and isinstance(source.state_directory, Path), 'READ_BATCH_INPUT_INVALID')
        started, clock_status = _clock(clock)
        _need(clock_status == 'OK', 'READ_BATCH_CLOCK_REFUSED')
        _need(source.clock is clock and source.account_scope == anchor.account_scope == coverage.account_scope,
              'READ_BATCH_SOURCE_CHANGED')
        batch = _Batch(source, store, batch_id, clock, limits, started)
        batch.source_check()
        batch.append('OPEN', dict(account_scope=batch.scope, started_at=started,
            limits_sha256=F.limits_digest(limits), anchor_sha256=content_digest(anchor),
            coverage_sha256=content_digest(coverage), baseline_sha256=content_digest(risk_baseline),
            trade_fees_sha256=content_digest(trade_fees)))
    except Exception as exc:
        raise ReadBatchArchiveError(_code(exc, 'READ_BATCH_INPUT_INVALID')) from None
    collection, error = None, None
    try:
        collection = collect_upbit(batch, anchor=anchor, coverage=coverage, risk_baseline=risk_baseline,
            clock=clock, trade_fees=trade_fees, max_requests=limits.max_calls, max_rows=100000)
        _need(type(collection) is CollectionResult, 'READ_BATCH_COLLECTOR_REFUSED')
        batch.source_check()
    except Exception as exc:
        error = batch.failure or _code(exc, 'READ_BATCH_COLLECTOR_REFUSED')
    if not batch.sink_failed:
        finished, clock_status = _clock(clock, batch.latest)
        if clock_status != 'OK': error = error or 'READ_BATCH_CLOCK_REFUSED'
        try:
            batch.append('CLOSE', dict(status='COLLECTED' if error is None else 'REFUSED', error_code=error,
                collection_manifest_sha256=collection.manifest_sha256 if error is None else None,
                records=tuple(enumerate(batch.digests)), calls=batch.calls, attempts=batch.attempts,
                finished_at=finished, clock_status=clock_status))
            actual = read_upbit_read_batch(store, batch.digests[-1], limits=limits)
            _need(actual.records == tuple(batch.records) and actual.status == ('COLLECTED' if error is None else 'REFUSED'))
            if error is None:
                batch.source_check()
            return ReadBatchResult(batch_id=batch_id, open_archive_digest=batch.digests[0],
                last_confirmed_archive_digest=batch.digests[-1], final_archive_digest=batch.digests[-1],
                status=actual.status, failure_code=error, collection=collection if error is None else None)
        except Exception as exc:
            error = _code(exc)
    return ReadBatchResult(batch_id=batch_id, open_archive_digest=batch.digests[0],
        last_confirmed_archive_digest=batch.digests[-1], final_archive_digest=None,
        status='INCOMPLETE', failure_code=error or batch.failure or 'READ_BATCH_ARCHIVE_REFUSED', collection=None)
