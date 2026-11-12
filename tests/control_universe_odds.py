"""Universe odds batches and universe session preparation, in test-signed temporary homes only."""
import ast
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

from core.compliance import model as M, owner, rules
from core.odds import plan as odds_plan
from execution_control import session as S, universe_odds as U
from execution_control.capability import digest, plain
from execution_control.controller import _event_data, _fold
from execution_control.session import prepare_session
from execution_control.store import MAX_ROW_BYTES, Journal
from execution_launch.continuous_guard_commit import _PREPARE_KEYS
from tests import compliance_fixtures as F, odds_fixtures as OF
from tests.control_session import (_fixed_refusal, _preparation_args, refused, selected, signed_control,
                                   universe_context, universe_snapshot, verification)

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
BTC, ETH, XRP = 'KRW-BTC', 'KRW-ETH', 'KRW-XRP'
PREPARE_ROW = {key: 'a'*64 for key in _PREPARE_KEYS} | {'path_start': 'x', 'path_end': 'x', 'halt_required': False,
                                                        'required_records': []}


def coin_bars(market, *, n=600):
    """What PR 2's daily_bars returns for one market: final (ISO date, open, close) rows ending the day before the
    fixture start, and the sha256 of each candle receipt."""
    series = OF.fresh_series(n, end='2026-10-23', symbol=market)
    return SimpleNamespace(market=market, bars=tuple(zip(series.dates, series.open, series.close)),
                           receipt_sha256=(hashlib.sha256(market.encode('ascii')).hexdigest(),))


@contextmanager
def universe_env(eligible=((BTC, D('900000000000')),)):
    """A signed, unarmed control home whose load_context returns env.universe as the snapshot in force."""
    with signed_control(prepare=False, arm=False) as env:
        env.universe = universe_snapshot(env.now, eligible=eligible)
        env.bars = {market: coin_bars(market) for market, _ in eligible}
        with universe_context(universe=lambda ctx: env.universe):
            yield env


@contextmanager
def ruled_env(eligible):
    """universe_env under a test-signed venues file whose upbit entry carries PR 3's fixture universe_rule, and
    env.universe built under that rule's sha256: a coin no signed map lists then resolves as a derived instrument."""
    with universe_env(eligible) as env:
        doc = yaml.safe_load(OF.ODDS_VENUES)
        doc['venues']['upbit'] |= yaml.safe_load(F._UNIVERSE_RULE_YAML)
        F.approve(env.home, env.key, 'venues', OF._dump(doc))
        env.universe = replace(env.universe, rule_sha256=rules.universe_rule_sha256(F.universe_rule()))
        yield env


def batch(env, n=1):
    return U.run_batch(env.controller, selected(env.now)[0], env.bars, n=n, now=env.now, clock=lambda: env.now,
                       positions=env.observation.positions, positions_asof=env.observation.asof)


def batch_rows(env):
    with env.journal.transaction() as tx:
        return [row['data'] for row in tx.events if row['kind'] == 'universe_odds_batch']


def prepare(env, result, **overrides):
    return prepare_session(**_preparation_args(env, universe_batch=result, **overrides))


def prepared_rows(env):
    with env.journal.transaction() as tx:
        return [row['data'] for row in tx.events if row['kind'] == 'session_prepared']


def test_batch_simulates_exactly_the_top_n_and_journals_one_closed_row():
    eligible = ((ETH, D('500000000000')), (BTC, D('900000000000')), (XRP, D('100000000000')))
    with universe_env(eligible) as env:
        env.bars[ETH] = coin_bars(ETH, n=100)       # refused either way: not mapped, or fewer than 250 bars
        result = batch(env, n=2)
        template = selected(env.now)[0]
        assert [(coin.market, coin.passed) for coin in result.coins] == [(BTC, True), (ETH, False)]
        assert result.coins[0].plan_hash == odds_plan.plan_hash(template) == result.template_plan_hash
        assert result.coins[1].plan_hash == odds_plan.plan_hash(replace(template,
                                                                         leg=replace(template.leg, symbol='ETH')))
        assert result.coins[0].inputs_digest == digest(list(env.bars[BTC].receipt_sha256))
        assert result.coins[0].seed_hex != result.coins[1].seed_hex
        assert (result.seoul_date, result.n, result.prior_batches) == (env.now.astimezone(M.KST).date(), 2, 0)
        assert (result.rule_sha256, result.snapshot_sha256) == (env.universe.rule_sha256,
                                                                env.universe.snapshot_sha256)
        assert result.started_at == result.finished_at == env.now
        assert result.batch_digest == digest({k: v for k, v in plain(result).items() if k != 'batch_digest'})
        assert batch_rows(env) == [plain(result)] and U.registered_batch(result.batch_digest) is result


def test_prior_batches_count_earlier_batches_of_the_same_snapshot_and_day():
    with universe_env() as env:
        first, second = batch(env), batch(env)
        assert (first.prior_batches, second.prior_batches) == (0, 1)
        assert first.batch_digest != second.batch_digest and first.coins[0].seed_hex != second.coins[0].seed_hex
        env.universe = replace(env.universe, snapshot_sha256='6'*64)
        assert batch(env).prior_batches == 0 and len(batch_rows(env)) == 3


def test_registry_returns_only_the_issued_unchanged_batch():
    with universe_env() as env:
        result = batch(env)
        assert U.registered_batch(result.batch_digest) is result
        assert U.registered_batch('0'*64) is None and U.registered_batch(None) is None
        object.__setattr__(result, 'prior_batches', 5)
        assert U.registered_batch(result.batch_digest) is None


def test_batch_row_folds_as_an_inert_event():
    with universe_env() as env:
        batch(env)
        with env.journal.transaction() as tx:
            assert [row['kind'] for row in tx.events] == ['universe_odds_batch']
            orders, killed, halted, last = _fold(tx.events)
        assert (orders, killed, halted, last) == ({}, set(), False, env.now)
        assert env.controller.states() == ()
        assert env.controller.observe(now=env.now).universe is env.universe


def test_event_data_closes_the_batch_row_shape():
    with universe_env() as env:
        row = plain(batch(env))
    _event_data('universe_odds_batch', row)
    coin = row['coins'][0]
    for bad in (row | {'extra': 1}, {k: v for k, v in row.items() if k != 'n'}, row | {'owner_head': ''},
                row | {'coins': []}, row | {'n': 0}, row | {'prior_batches': -1},
                row | {'coins': [coin | {'passed': 'yes'}]}, row | {'coins': [coin | {'seed_hex': 'G'*64}]},
                row | {'coins': [{k: v for k, v in coin.items() if k != 'market'}]}):
        refused(lambda: _event_data('universe_odds_batch', bad))


def test_batch_refusals_happen_before_any_simulation_or_row():
    def simulated(*args, **kwargs):
        raise AssertionError('simulated before a refusal')
    with universe_env() as env, patch.object(U.simulate, 'simulate', simulated):
        template = selected(env.now)[0]

        def run(code, template=template, bars=None, **changes):
            args = dict(n=1, now=env.now, clock=lambda: env.now, positions=env.observation.positions,
                        positions_asof=env.observation.asof) | changes
            _fixed_refusal(lambda: U.run_batch(env.controller, template, env.bars if bars is None else bars,
                                               **args), code)
        for n in (0, U.MAX_COINS + 1, True, 1.0):
            run('UNIVERSE_BATCH_N_INVALID', n=n)
        for clock in (lambda: env.now + timedelta(seconds=31), lambda: env.now - timedelta(seconds=1), None):
            run('UNIVERSE_BATCH_CLOCK_INVALID', clock=clock)
        for leg in (replace(template.leg, edge_source=odds_plan.REPLAY_SOURCE), replace(template.leg, venue='okx')):
            run('UNIVERSE_BATCH_TEMPLATE_INVALID', template=replace(template, leg=leg))
        run('UNIVERSE_BATCH_BARS_MISSING', bars={})
        for changes in ({'market': ETH}, {'receipt_sha256': ()}, {'receipt_sha256': ('A'*64,)}, {'bars': ()},
                        {'bars': (('2026-10-22', 'x', 1.0),)}):
            run('UNIVERSE_BATCH_BARS_MISSING', bars={BTC: SimpleNamespace(**(vars(env.bars[BTC]) | changes))})
        with universe_context(code_signed=False):
            run('UNIVERSE_BATCH_STATE_UNUSABLE')
        positions = env.observation.positions
        for bad, asof in ((None, env.now), (replace(positions, equity_krw=0.0), env.now),
                          (positions, env.now.replace(tzinfo=None))):
            run('UNIVERSE_BATCH_POSITIONS_INVALID', positions=bad, positions_asof=asof)
        second = timedelta(seconds=1)
        for asof, started in ((env.now - 31*second, env.now),                  # stale
                              (env.now - 20*second, env.now + 15*second),      # stale by the first clock read
                              (env.now + second, env.now + second)):           # future
            run('UNIVERSE_BATCH_POSITIONS_STALE', positions_asof=asof, clock=lambda started=started: started)
        for universe in (None, universe_snapshot(env.now, eligible=())):
            env.universe = universe
            run('UNIVERSE_BATCH_NO_SNAPSHOT')
        env.universe = universe_snapshot(env.now)
        F.sign(env.key, 'session_armed', {'session_id': 'armed-elsewhere'}, M.iso_utc(env.now))
        run('UNIVERSE_BATCH_SESSION_ARMED')
        assert batch_rows(env) == [] and U._BATCHES == {}


def test_batch_refuses_inside_a_pending_guard_transaction():
    with universe_env() as env:
        with env.journal.transaction() as tx:
            tx.append('continuous_guard_prepare', PREPARE_ROW, now=env.now)
        _fixed_refusal(lambda: batch(env), 'UNIVERSE_BATCH_GUARD_PENDING')
        with env.journal.transaction() as tx:
            assert [row['kind'] for row in tx.events] == ['continuous_guard_prepare']
        assert U._BATCHES == {}


def test_batch_never_calls_the_account_provider():
    """The batch runs on the console thread, off the coordinator's work lock (spec section 9), so it takes the
    caller's reconciled positions and never calls the live, non-reentrant account provider."""
    def provider(stamp):
        raise AssertionError('account provider called')
    with universe_env() as env:
        env.controller.account_provider = provider
        result = batch(env)
        assert result.coins[0].passed
        assert batch_rows(env) == [plain(result)] and U.registered_batch(result.batch_digest) is result


def test_largest_batch_row_fits_one_journal_row_and_folds():
    coin = U.CoinOdds(market='KRW-A' + 'Z'*11, plan_hash='a'*64, seed_hex='b'*64, inputs_digest='c'*64,
                      report_digest='d'*64, passed=True)
    largest = U.UniverseBatch(batch_digest='e'*64, seoul_date=F.NOW.astimezone(M.KST).date(),
                              template_plan_hash='f'*64, code_hash='1'*64, state_hash='2'*64, owner_head='3'*64,
                              rule_sha256='4'*64, snapshot_sha256='5'*64, n=U.MAX_COINS,
                              coins=(coin,) * U.MAX_COINS, started_at=F.NOW, finished_at=F.NOW,
                              prior_batches=2**62)
    row = plain(largest)
    _event_data('universe_odds_batch', row)
    assert len(json.dumps(row)) * 4 < MAX_ROW_BYTES
    with signed_control(prepare=False, arm=False) as env:
        with env.journal.transaction() as tx:
            tx.append('universe_odds_batch', row, now=env.now)
        assert env.controller.states() == ()


def test_universe_odds_imports_only_odds_compliance_and_control():
    source = (ROOT / 'execution_control' / 'universe_odds.py').read_text(encoding='utf-8')
    std = {'__future__', 'collections.abc', 'dataclasses', 'datetime', 'decimal', 'hashlib', 're', 'uuid'}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
        names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                 else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
        for name in names:
            assert (name in std or name in ('core.odds', 'core.compliance', 'execution_control')
                    or name.startswith(('core.odds.', 'core.compliance.', 'execution_control.'))), name
    assert '/v1/' not in source and 'oddsdata' not in source


def test_universe_session_binds_the_batch_and_verification_follows_the_snapshot():
    with universe_env() as env:
        result = batch(env)
        prepared = prepare(env, result)
        assert prepared.universe_batch_digest == result.batch_digest
        record = {k: v for k, v in vars(prepared).items() if k != 'record_digest'}
        assert prepared.session_id == 'freshness-' + digest({k: v for k, v in record.items() if k != 'session_id'})
        assert prepared.record_digest == digest(record)
        rows = prepared_rows(env)
        assert rows == [plain(prepared)] and rows[0]['universe_batch_digest'] == result.batch_digest
        env.prepared, env.session_id = prepared, prepared.session_id
        F.sign(env.key, 'session_armed', {'session_id': env.session_id}, M.iso_utc(env.now))
        verification(env)
        reserved = env.controller.reserve(env.order, env.rules, session_id=env.session_id, now=env.now)
        assert reserved.status == 'RESERVED'
        env.universe = replace(env.universe, snapshot_sha256='6'*64)
        _fixed_refusal(lambda: verification(env), 'session preparation stale or mismatched')


def test_universe_session_refuses_unregistered_or_tampered_batches():
    with universe_env() as env:
        result = batch(env)
        before = dict(S._PREPARED)
        for candidate in (replace(result), plain(result)):
            _fixed_refusal(lambda: prepare(env, candidate), 'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        _fixed_refusal(lambda: prepare(env, result, journal=Journal(env.home / 'other-control')),
                       'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        with env.journal.transaction() as tx:                     # a second identical row: not exactly one
            tx.append('universe_odds_batch', plain(result), now=env.now)
        _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        object.__setattr__(result, 'n', 2)
        _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_UNREGISTERED')
        assert S._PREPARED == before and prepared_rows(env) == []


def test_universe_session_refuses_a_stale_batch():
    with universe_env() as env:
        result = batch(env)
        for changes in ({'code_hash': '0'*64},
                        {'active': lambda ctx: replace(ctx.active, seq=ctx.active.seq + 1)},
                        {'owner': lambda ctx: replace(ctx.owner, head=(ctx.owner.head[0] + 1, 'f'*64))},
                        {'universe': lambda ctx: replace(ctx.universe, snapshot_sha256='6'*64)},
                        {'universe': None}):
            with universe_context(**changes):
                _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_STALE')
        env.now += timedelta(days=1)
        env.observation = replace(env.observation, asof=env.now, server_time=env.now,
                                  risk=replace(env.observation.risk, asof=env.now))
        env.rules = replace(env.rules, asof=env.now)
        _fixed_refusal(lambda: prepare(env, result), 'SESSION_UNIVERSE_BATCH_STALE')
        assert prepared_rows(env) == []


def test_universe_session_refuses_a_failed_coin_or_another_template():
    with universe_env(((BTC, D('900000000000')), (ETH, D('500000000000')))) as env:
        env.bars[ETH] = coin_bars(ETH, n=100)
        failed = batch(env, n=2)
        _fixed_refusal(lambda: prepare(env, failed), 'SESSION_UNIVERSE_BATCH_FAILED')
        result = batch(env, n=1)
        plan = selected(env.now)[0]
        for other in (replace(plan, stake_krw=41_000.0), replace(plan, leg=replace(plan.leg, symbol='ETH')),
                      replace(plan, leg=replace(plan.leg, venue='okx'))):                # KRW-BTC is a batch coin
            _fixed_refusal(lambda: prepare(env, result, selected_plan=other), 'SESSION_UNIVERSE_TEMPLATE_INVALID')
        refused(lambda: prepare(env, result, selection_seed_hex='0'*64))      # the selection-seed check stays
        assert prepared_rows(env) == []


def test_universe_session_caps_expiry_at_snapshot_end_and_seoul_midnight():
    with universe_env() as env:
        result = batch(env)
        # env.now is 09:00 KST; a UTC snapshot end must not turn the KST expiry into a UTC one.
        env.universe = replace(env.universe, valid_until=(env.now + timedelta(minutes=10)).astimezone(timezone.utc))
        capped = prepare(env, result)
        assert capped.expires_at == env.now + timedelta(minutes=9)
        assert capped.expires_at.utcoffset() == env.now.utcoffset() == timedelta(hours=9)
        env.universe = replace(env.universe, valid_until=env.now + timedelta(days=2))
        late = prepare(env, result, session_id='late', expires_at=env.now + timedelta(hours=23))
        assert late.expires_at == datetime(2026, 10, 25, tzinfo=M.KST) - timedelta(seconds=60)
        env.universe = replace(env.universe, valid_until=env.now + timedelta(seconds=30))
        _fixed_refusal(lambda: prepare(env, result, session_id='gone'), 'SESSION_PREPARATION_EXPIRED')


def test_universe_session_symbol_needs_a_batch_coin_eligible_in_the_same_snapshot():
    from execution_control.session import _symbol_ok
    with universe_env(((BTC, D('900000000000')), (ETH, D('500000000000')))) as env:
        result = batch(env, n=1)
        prepared = SimpleNamespace(universe_batch_digest=result.batch_digest, symbol='BTC')
        current = SimpleNamespace(universe=env.universe)

        def order(market):
            return SimpleNamespace(symbol=market)
        assert _symbol_ok(prepared, order(BTC), 'BTC', current)
        assert not _symbol_ok(prepared, order(ETH), 'ETH', current)          # eligible, but outside the N
        for universe in (replace(env.universe, eligible=((ETH, D('500000000000')),)),   # no longer eligible
                         replace(env.universe, snapshot_sha256='6'*64), None):
            assert not _symbol_ok(prepared, order(BTC), 'BTC', SimpleNamespace(universe=universe))
        unregistered = SimpleNamespace(universe_batch_digest='0'*64, symbol='BTC')
        assert not _symbol_ok(unregistered, order(BTC), 'BTC', current)
        fixed = SimpleNamespace(universe_batch_digest=None, symbol='BTC')
        assert _symbol_ok(fixed, order(BTC), 'BTC', None) and not _symbol_ok(fixed, order(ETH), 'ETH', None)


def test_a_fixed_preparation_refuses_a_coin_only_the_universe_rule_resolves():
    """Spec section 9 rules out an ad hoc set: under a signed universe_rule with a snapshot in force, an Upbit coin
    that no signed map lists resolves as a derived instrument, so preparing it without a batch refuses. The mapped
    KRW-BTC fixed session prepares as before."""
    with ruled_env(((BTC, D('900000000000')), (ETH, D('500000000000')))) as env:
        plan = selected(env.now)[0]
        eth = replace(plan, leg=replace(plan.leg, symbol='ETH'))
        _fixed_refusal(lambda: prepare(env, None, selected_plan=eth), 'SESSION_UNIVERSE_BATCH_REQUIRED')
        assert prepared_rows(env) == []
        fixed = prepare(env, None)
        assert (fixed.symbol, fixed.universe_batch_digest) == ('BTC', None)
        assert prepared_rows(env) == [plain(S._record(fixed))]          # the fixed row keeps its old key set


def test_universe_session_trades_a_batch_coin_other_than_the_one_it_was_prepared_with():
    """Rotation: under a signed universe_rule, both coins of an n=2 batch pass, the session is prepared for BTC and
    its symbol check accepts an ETH buy. A coin eligible in the snapshot but outside the batch stays refused."""
    from execution_control.session import _symbol_ok
    eligible = ((BTC, D('900000000000')), (ETH, D('500000000000')), (XRP, D('100000000000')))
    with ruled_env(eligible) as env:
        result = batch(env, n=2)
        assert [(coin.market, coin.passed) for coin in result.coins] == [(BTC, True), (ETH, True)]
        prepared = prepare(env, result)
        assert (prepared.symbol, prepared.universe_batch_digest) == ('BTC', result.batch_digest)
        current = owner.load_context(env.now, env.observation.positions, session_id=prepared.session_id)
        assert _symbol_ok(prepared, replace(env.order, symbol=ETH), 'ETH', current)
        assert not _symbol_ok(prepared, replace(env.order, symbol=XRP), 'XRP', current)
