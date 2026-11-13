"""Actual E1 GET collector -> transport -> backed local read-batch archives.

Only transport _send and test credentials are synthetic. Request validation,
JWT/header construction, raw Answer/SourceReceipt parsing, collector accounting,
BundleStore publication and every archive readback are real implementations.
The supplied account identity/retention/fence evidence is invented test input,
never live source authentication, verified coverage, activation or order power.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from email.utils import format_datetime
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from execution import transport as T
from execution_accounts.provider import build_observation
from execution_accounts.upbit_collector import E1UpbitSource
from execution_launch import research_bundle_store as BS
from execution_launch import upbit_read_archive as A, upbit_read_format as F
from tests import accounts_collector as C, execution_fixtures as EF
from tests import launch_research_bundle_store as S


LIMITS = F.ReadBatchLimits(max_calls=32, max_attempts=64, max_records=194,
    max_body_bytes=16384, max_total_body_bytes=262144, max_record_bytes=32768,
    max_total_record_bytes=1048576)


@contextmanager
def fixture(*, with_order=False, initialize=True, provision=True, response=None):
    with S.fixture(provision=provision, initialize=initialize,
                   storage_limits=S.limits(max_catalog_records=512)) as e:
        home = Path(os.environ['TRADEGEN_HOME'])
        with EF.isolated(home), EF.fake_keys():
            wire = C.SyntheticSource(with_order=with_order)
            calls, headers, sleeps = [], [], []
            state = SimpleNamespace(at=C.NOW, clock_error=None)
            def clock():
                if state.clock_error is not None:
                    raise state.clock_error
                return state.at
            source = E1UpbitSource(account_scope=C.SCOPE, state_directory=home, clock=clock)
            def send(method, url, *, headers: dict, params, json_body, timeout):
                parts = urlsplit(url)
                assert method == 'GET' and parts.netloc == 'api.upbit.com'
                assert params is None and json_body is None and timeout == 10.0
                query = tuple(parse_qsl(parts.query, keep_blank_values=True))
                call = SimpleNamespace(index=len(calls)+1, method=method, path=parts.path, params=query)
                calls.append(call)
                saved_headers.append(dict(headers))
                # This helper only scripts original response bytes. Its receipt
                # object never enters E1 or the collector; E1 issues the real one.
                raw = wire.fetch(parts.path, query).raw_body
                value = (200, {'Date': format_datetime(C.NOW, usegmt=True)}, raw)
                if response is not None:
                    value = response(call, value, state)
                if isinstance(value, Exception):
                    raise value
                return value
            saved_headers = headers
            with patch.object(T, '_send', send), patch.object(T, '_sleep', sleeps.append):
                yield SimpleNamespace(store=e.store, storage=e, source=source, wire=wire, clock=clock,
                    time=state, calls=calls, headers=headers, sleeps=sleeps, home=home)


def collect(e, *, batch_id='integration-batch', limits=LIMITS, **changes):
    anchor, coverage, baseline = C.proofs()
    args = dict(store=e.store, batch_id=batch_id, anchor=anchor, coverage=coverage,
                risk_baseline=baseline, clock=e.clock, limits=limits)
    return A.collect_retained_upbit_batch(e.source, **(args | changes))


def archive(e, result, *, limits=LIMITS):
    return A.read_upbit_read_batch(e.store, result.last_confirmed_archive_digest, limits=limits)


def responses(read):
    return tuple(row for row in read.records if row.kind == 'ATTEMPT' and row.body['phase'] == 'RESPONSE')


def no_authority(value):
    assert value.source_authenticated is False and value.coverage_verified is False
    assert value.execution_ready is False


def refused(call, *codes):
    try:
        call()
    except A.ReadBatchArchiveError as exc:
        if codes:
            assert str(exc) in codes, (str(exc), codes)
        assert str(exc).startswith(('READ_BATCH_', 'READ_CAPTURE_'))
        return str(exc)
    raise AssertionError('read-batch boundary accepted an invalid operation')


def test_actual_e1_collector_reconciles_fill_and_fee_and_backs_every_original_response():
    with fixture(with_order=True) as e:
        result = collect(e)
        assert result.status == 'COLLECTED' and result.failure_code is None
        assert result.collection is not None and result.final_archive_digest == result.last_confirmed_archive_digest
        observed = build_observation(result.collection.bundle, now=C.NOW)
        assert observed.risk.equity == C.D('99995') and observed.fills[0].fee_amount == C.D(5)
        assert observed.reconciled_client_ids == {'client-1'}
        retained = archive(e, result)
        assert retained.status == 'COLLECTED' and retained.final_archive_digest == result.final_archive_digest
        assert any(call.path == '/v1/order' and call.params == (('uuid', 'order-1'),) for call in e.calls)
        ends = [row for row in retained.records if row.kind == 'FETCH_END']
        assert len(ends) == len(result.collection.receipts) == len(e.calls)
        assert len(responses(retained)) == len(e.calls)
        for row, receipt in zip(responses(retained), result.collection.receipts):
            raw = retained.payloads[row.ordinal]
            assert raw == receipt.raw_body and row.body['body_sha256'] == receipt.sha256
            assert row.body['body_bytes'] == len(raw) and row.body['status_code'] == 200
        close = retained.records[-1]
        assert close.kind == 'CLOSE' and close.body['collection_manifest_sha256'] == result.collection.manifest_sha256
        assert len(close.body['records']) == len(retained.records)-1
        for value in (result, retained):
            no_authority(value)


def test_repeated_identical_account_bytes_remain_distinct_observations_and_parent_graphs():
    with fixture() as e:
        result = collect(e)
        retained = archive(e, result)
        account_rows = [row for row in responses(retained) if row.body['path'] == '/v1/accounts']
        assert result.status == 'COLLECTED' and len(account_rows) >= 2
        assert len({row.ordinal for row in account_rows}) == len(account_rows)
        assert len({row.body['call_ordinal'] for row in account_rows}) == len(account_rows)
        assert len({row.body['body_sha256'] for row in account_rows}) == 1
        assert len({retained.payloads[row.ordinal] for row in account_rows}) == 1
        current = result.last_confirmed_archive_digest
        actual_rows = []
        while current is not None:
            snapshot = e.store.read_raw(current, require_backup=True)
            assert snapshot.backup_verified and snapshot.manifest.kind == 'RAW_ARCHIVED'
            row = F.parse_record(snapshot.files['record'])
            assert snapshot.manifest.parent_bundle_sha256 == row.previous_archive_digest
            assert snapshot.manifest.run_id == 'upbit-integration-batch'
            assert snapshot.manifest.revision_id == 'read-v1-' + str(row.ordinal).zfill(5)
            assert set(snapshot.files) == ({'record', 'body'} if row.ordinal in retained.payloads else {'record'})
            actual_rows.append(row)
            current = row.previous_archive_digest
        assert tuple(reversed(actual_rows)) == retained.records


def test_invalid_json_duplicate_json_keys_and_invalid_account_semantics_keep_exact_raw():
    bad_responses = (b'{bad JSON', b'[{"currency":"KRW","balance":"100000","balance":"1","locked":"0"}]',
                     b'[{"currency":"KRW","balance":"not-a-number","locked":"0"}]')
    for index, bad in enumerate(bad_responses):
        original = []
        def response(call, default, _state):
            actual = (200, default[1], bad) if call.index == 1 else default
            original.append(actual[2])
            return actual
        with fixture(response=response) as e:
            result = collect(e)
            assert result.status == 'REFUSED' and result.collection is None
            retained = archive(e, result)
            # Structural receipt errors stop immediately. Existing collector
            # balance-number validation follows the initial history queries.
            expected_paths = ('/v1/accounts',) if index < 2 else (
                '/v1/accounts', '/v1/orders/open', '/v1/orders/closed', '/v1/deposits', '/v1/withdraws')
            assert retained.status == 'REFUSED' and tuple(call.path for call in e.calls) == expected_paths
            rows = responses(retained)
            assert len(rows) == len(original) == len(expected_paths)
            assert tuple(retained.payloads[row.ordinal] for row in rows) == tuple(original)
            assert retained.payloads[rows[0].ordinal] == bad
            assert rows[0].body['body_sha256'] == hashlib.sha256(bad).hexdigest()
            assert all(row.body['body_sha256'] == hashlib.sha256(raw).hexdigest()
                       for row, raw in zip(rows, original))
            assert retained.records[-1].body['collection_manifest_sha256'] is None
            no_authority(result)


def test_auth_failure_body_is_saved_before_actual_e1_refuses_it():
    bad = b'{"error":{"name":"invalid_access_key","message":"fixture rejected credential"}}'
    def response(call, default, _state):
        return (401, default[1], bad)
    with fixture(response=response) as e:
        result = collect(e)
        retained = archive(e, result)
        assert result.status == retained.status == 'REFUSED' and result.collection is None
        assert len(e.calls) == 1 and responses(retained)[0].body['status_code'] == 401
        assert retained.payloads[responses(retained)[0].ordinal] == bad
        assert e.headers[0]['Authorization'].startswith('Bearer ')


def test_retry_keeps_first_429_or_503_and_second_response_under_one_logical_call():
    for status in (429, 503):
        first = b'{"error":{"name":"fixture_busy","message":"retryable response"}}'
        def response(call, default, _state):
            return (status, default[1], first) if call.index == 1 else default
        with fixture(response=response) as e:
            result = collect(e)
            retained = archive(e, result)
            assert result.status == 'COLLECTED' and result.collection is not None
            rows = [row for row in responses(retained) if row.body['call_ordinal'] == 1]
            assert [row.body['attempt'] for row in rows] == [1, 2]
            assert [row.body['status_code'] for row in rows] == [status, 200]
            assert retained.payloads[rows[0].ordinal] == first
            assert retained.payloads[rows[1].ordinal] == result.collection.receipts[0].raw_body
            assert len(e.calls) == len(result.collection.receipts)+1
            assert e.headers[0]['Authorization'] != e.headers[1]['Authorization']


def test_actual_connection_retry_records_error_without_exporting_exception_text():
    import requests
    secret = 'fixture-private-exception-text-do-not-export'
    def response(call, default, _state):
        return requests.exceptions.ConnectionError(secret) if call.index == 1 else default
    with fixture(response=response) as e:
        result = collect(e)
        retained = archive(e, result)
        errors = [row for row in retained.records if row.kind == 'ATTEMPT'
                  and row.body['phase'] == 'TRANSPORT_ERROR']
        assert result.status == 'COLLECTED' and len(errors) == 1
        assert errors[0].body['error_code'] == 'CONNECTION_ERROR'
        assert 'raw_body' not in errors[0].body
        assert errors[0].ordinal not in retained.payloads
        assert all(secret.encode() not in raw for raw in S.files(e.storage.base).values())


def test_later_failed_fetch_keeps_all_earlier_raw_and_never_publishes_a_collection():
    bad = b'{"error":{"name":"invalid_access_key","message":"fixture later failure"}}'
    def response(call, default, _state):
        return (401, default[1], bad) if call.index == 3 else default
    with fixture(response=response) as e:
        result = collect(e)
        retained = archive(e, result)
        assert result.status == 'REFUSED' and result.collection is None and len(e.calls) == 3
        rows = responses(retained)
        assert len(rows) == 3 and [row.body['status_code'] for row in rows] == [200, 200, 401]
        assert retained.payloads[rows[2].ordinal] == bad
        for row in rows[:2]:
            assert row.ordinal in retained.payloads and row.body['body_sha256'] == hashlib.sha256(
                retained.payloads[row.ordinal]).hexdigest()
        assert retained.records[-1].kind == 'CLOSE'
        assert retained.records[-1].body['collection_manifest_sha256'] is None


def test_response_storage_failure_preserves_confirmed_prefix_and_stops_before_further_http():
    with fixture() as e:
        actual, failures = e.store.archive_raw, []
        def fail_second_response(manifest, payloads, **kwargs):
            row = F.parse_record(payloads['record'])
            if failures or (row.kind == 'ATTEMPT' and row.body['phase'] == 'RESPONSE'
                            and row.body['call_ordinal'] == 2):
                failures.append(row.kind)
                raise BS.BundleStoreError('BUNDLE_STORE_IO_REFUSED')
            return actual(manifest, payloads, **kwargs)
        with patch.object(e.store, 'archive_raw', fail_second_response):
            result = collect(e)
        assert failures and result.status == 'INCOMPLETE' and result.collection is None
        assert result.final_archive_digest is None and len(e.calls) == 2
        retained = archive(e, result)
        assert retained.status == 'INCOMPLETE' and retained.final_archive_digest is None
        rows = responses(retained)
        assert len(rows) == 1 and rows[0].body['call_ordinal'] == 1
        assert retained.payloads[rows[0].ordinal] and not any(row.kind == 'CLOSE' for row in retained.records)


def test_missing_store_or_head_refuses_open_before_any_http_and_does_not_initialize():
    for provision, initialize in ((False, False), (True, False)):
        with fixture(provision=provision, initialize=initialize) as e:
            before = S.files(e.storage.base)
            refused(lambda: collect(e))
            assert not e.calls and S.files(e.storage.base) == before


def test_reused_batch_id_cannot_send_again_but_new_explicit_batch_can_collect():
    with fixture() as e:
        first = collect(e, batch_id='first-explicit-batch')
        assert first.status == 'COLLECTED'
        sent, before = len(e.calls), S.files(e.storage.base)
        refused(lambda: collect(e, batch_id='first-explicit-batch'), 'READ_BATCH_ID_REUSED')
        assert len(e.calls) == sent and S.files(e.storage.base) == before
        # Keep a new explicit run separate; no resumption mutates the old graph.
        second = collect(e, batch_id='second-explicit-batch')
        assert second.status == 'COLLECTED' and second.open_archive_digest != first.open_archive_digest
        assert archive(e, first).status == 'COLLECTED'


def test_competing_same_batch_cannot_send_while_the_actual_winner_is_in_flight():
    from threading import Event, Thread
    started, release = Event(), Event()
    outcomes, failures = [], []
    def response(call, default, _state):
        if call.index == 1:
            started.set()
            assert release.wait(10), 'fixture response release timed out'
        return default
    with fixture(response=response) as e:
        def winner():
            try:
                outcomes.append(collect(e, batch_id='concurrent-batch'))
            except BaseException as exc:
                failures.append(type(exc).__name__)
        worker = Thread(target=winner)
        worker.start()
        try:
            assert started.wait(10), failures
            assert len(e.calls) == 1
            refused(lambda: collect(e, batch_id='concurrent-batch'), 'READ_BATCH_ID_REUSED')
            assert len(e.calls) == 1
        finally:
            release.set()
            worker.join(20)
        assert not worker.is_alive() and not failures and len(outcomes) == 1
        assert outcomes[0].status == 'COLLECTED' and archive(e, outcomes[0]).status == 'COLLECTED'


def test_failed_or_rolled_back_receipt_clock_still_retains_already_returned_body():
    for failure in ('invalid', 'raised', 'rollback'):
        original = []
        def response(call, default, state):
            original.append(default[2])
            if failure == 'invalid':
                state.at = None
            elif failure == 'raised':
                state.clock_error = ValueError('fixture private clock text')
            else:
                state.at = C.NOW-timedelta(microseconds=1)
            return default
        with fixture(response=response) as e:
            result = collect(e)
            retained = archive(e, result)
            assert result.status == retained.status == 'REFUSED' and result.collection is None
            assert len(e.calls) == len(original) == 1
            row = responses(retained)[0]
            assert row.body['clock_status'] == {'invalid': 'INVALID', 'raised': 'RAISED',
                                                'rollback': 'ROLLBACK'}[failure]
            assert row.body['observed_at'] is None and retained.payloads[row.ordinal] == original[0]
            assert row.body['body_sha256'] == hashlib.sha256(original[0]).hexdigest()
            assert b'fixture private clock text' not in b''.join(S.files(e.storage.base).values())


def test_source_drift_during_actual_send_retains_response_under_original_open_then_refuses():
    for changed in ('account_scope', 'clock'):
        original = []
        def response(call, default, _state):
            original.append(default[2])
            if changed == 'account_scope':
                e.source.account_scope = 'changed-fixture-scope'
            else:
                e.source.clock = lambda: C.NOW
            return default
        with fixture(response=response) as e:
            result = collect(e)
            retained = archive(e, result)
            assert result.status == retained.status == 'REFUSED' and result.collection is None
            assert result.failure_code == 'READ_BATCH_SOURCE_CHANGED'
            assert len(e.calls) == len(original) == len(responses(retained)) == 1
            assert retained.records[0].body['account_scope'] == C.SCOPE
            row = responses(retained)[0]
            assert retained.payloads[row.ordinal] == original[0]
            assert row.body['body_sha256'] == hashlib.sha256(original[0]).hexdigest()
            ended = [item for item in retained.records if item.kind == 'FETCH_END']
            assert len(ended) == 1 and ended[0].body['status'] == 'REFUSED'
            assert ended[0].body['receipt'] is None
            assert retained.records[-1].kind == 'CLOSE'
            assert retained.records[-1].body['collection_manifest_sha256'] is None
            no_authority(result)
            no_authority(retained)


def test_prefix_without_close_is_incomplete_and_reader_never_reissues_collection_or_http():
    with fixture() as e:
        result = collect(e)
        complete = archive(e, result)
        prefix_digest = complete.records[-1].previous_archive_digest
        sent, before = len(e.calls), S.files(e.storage.base)
        with patch.object(T, '_send', side_effect=AssertionError('historical reader sent HTTP')):
            partial = A.read_upbit_read_batch(e.store, prefix_digest, limits=LIMITS)
        assert partial.status == 'INCOMPLETE' and partial.final_archive_digest is None
        assert partial.records == complete.records[:-1]
        assert not hasattr(partial, 'collection') and len(e.calls) == sent and S.files(e.storage.base) == before
        no_authority(partial)


def test_body_limit_records_unretained_response_without_truncating_or_collecting():
    limits = replace(LIMITS, max_body_bytes=8)
    with fixture() as e:
        result = collect(e, limits=limits)
        retained = archive(e, result, limits=limits)
        assert result.status == 'REFUSED' and result.collection is None and len(e.calls) == 1
        row = responses(retained)[0]
        assert row.body['body_status'] == 'LIMIT_EXCEEDED' and row.body['body_bytes'] > 8
        assert row.body['body_sha256'] is None and row.ordinal not in retained.payloads


def test_record_admission_preserves_refused_close_before_zero_or_one_actual_http_call():
    for maximum, expected_sends in ((5, 0), (6, 1)):
        limits = replace(LIMITS, max_records=maximum)
        with fixture() as e:
            result = collect(e, limits=limits)
            retained = archive(e, result, limits=limits)
            assert result.status == retained.status == 'REFUSED'
            assert result.failure_code == 'READ_BATCH_RESOURCE_LIMIT' and result.collection is None
            assert len(e.calls) == expected_sends and len(responses(retained)) == expected_sends
            assert retained.records[0].kind == 'OPEN' and retained.records[-1].kind == 'CLOSE'
            assert retained.records[-1].body['status'] == 'REFUSED'
            if expected_sends:
                assert len(retained.records) == maximum
                row = responses(retained)[0]
                assert retained.payloads[row.ordinal] == e.wire.fetch('/v1/accounts', ()).raw_body
            else:
                assert len(retained.records) == 2 and dict(retained.payloads) == {}


def test_actual_backup_damage_invalidates_historical_read_without_repair_or_http():
    with fixture() as e:
        result = collect(e)
        retained = archive(e, result)
        first = responses(retained)[0]
        path = S.chunk_path(e.store, retained.payloads[first.ordinal], backup=True)
        path.write_bytes(b'fixture damaged backup')
        before, sent = S.files(e.storage.base), len(e.calls)
        with patch.object(T, '_send', side_effect=AssertionError('reader sent HTTP')):
            refused(lambda: archive(e, result))
        assert S.files(e.storage.base) == before and len(e.calls) == sent
        no_authority(result)


def test_archive_exports_no_auth_headers_token_key_or_order_creation_path():
    with fixture(with_order=True) as e:
        result = collect(e)
        retained = archive(e, result)
        assert result.status == 'COLLECTED'
        sent_auth = [headers['Authorization'] for headers in e.headers if 'Authorization' in headers]
        assert sent_auth and all(value.startswith('Bearer ') for value in sent_auth)
        forbidden = [b'Authorization', b'Bearer ', *(value.encode() for value in sent_auth),
                     *(EF.FAKE_KEYS[name].encode() for name in ('UPBIT_ACCESS_KEY', 'UPBIT_SECRET_KEY'))]
        for raw in S.files(e.storage.base).values():
            assert all(value not in raw for value in forbidden)
        assert all(call.method == 'GET' for call in e.calls)
        assert all(call.path in ('/v1/accounts', '/v1/orders/open', '/v1/orders/closed', '/v1/order',
            '/v1/deposits', '/v1/withdraws', '/v1/ticker', '/v1/market/all', '/v1/orderbook') for call in e.calls)
        assert all(set(row.body).isdisjoint({'headers', 'token', 'json_body', 'authorization'})
                   for row in retained.records)
        assert 'Bearer ' not in repr(result) and 'raw_body' not in repr(retained)
        assert not (e.home/'no-such.env').exists()
