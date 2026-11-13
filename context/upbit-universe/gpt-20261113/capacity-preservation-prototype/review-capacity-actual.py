"""Actual original PR4d capacity refusal, under the approved offline verifier.

This is a scratch-only regression probe, not a capacity policy implementation.
"""
import ast
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import verify
from tests import accounts_collector as F
from tests import launch_acceptance as A
from tests import launch_universe_history as U
from tests.control_acceptance import _wrap
from execution_accounts.provider import build_observation
from execution_accounts.quotes import parse_orderbook
from execution_control.store import MAX_ROW_BYTES, _canonical
from execution_launch.live_history import LiveHistoryError, _row


def actual_residual_capacity_refusal():
    # Reuse only the earlier synthetic source class, not its old checkout imports
    # or standalone serialization. Every runtime call below uses this worktree.
    old_probe = Path('/workspace/tradegen-session/universe-1113/pr4d-size-probe.py').read_text()
    node = next(n for n in ast.parse(old_probe).body if isinstance(n, ast.ClassDef) and n.name == 'ManyDustSource')
    ns = dict(F=F, timedelta=timedelta, deepcopy=deepcopy)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'reused-synthetic-source', 'exec'), ns)

    with U.head_root() as hroot:
        env = U.ubuild(hroot)
        slot = env.T(0)
        with patch.object(F, 'NOW', slot), patch.object(F, 'ORIGIN', slot-timedelta(days=1)), \
             patch.object(F, 'SCOPE', env.profile.account_scope):
            source = ns['ManyDustSource'](1500)
            source.account_scope = env.profile.account_scope
            collection = F.collect(source)
            account = collection.bundle.accounts[0]
            observation = build_observation(collection.bundle, now=slot)
        assert len(account.positions) == 1500 and len(source.calls) < 2000
        assert all(p.units == 1 and p.price == 0 and p.unlisted is True for p in account.positions)

        original = U.book(env, 0)
        wire = json.loads(original.receipt.raw_body)
        wire[0]['padding'] = ''
        raw = json.dumps(wire, separators=(',', ':')).encode()
        wire[0]['padding'] = 'x' * (131072-len(raw))
        raw = json.dumps(wire, separators=(',', ':')).encode()
        assert len(raw) == 131072
        receipt = replace(original.receipt, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())
        book = parse_orderbook(receipt, symbol=U.BTC, now=slot)
        env.c[0] = slot + timedelta(seconds=1)

        journal = U.LH.journal(env)
        journal_before = journal.read_bytes()
        head_before = env.head.read()
        names = ('_slots', '_chain', '_marks', '_prices', '_state', '_inputs',
                 'recorded_allow', '_head', '_size', '_seq', '_failed')
        memory_before = {name: getattr(env.h, name) for name in names}
        with patch.object(env.h, '_append', wraps=env.h._append) as attempted:
            try:
                env.h.record_slot(book, observation, trade_symbol=U.BTC,
                                  universe=U.reads(env, 0, U.SWITCH[0]), tick_size=U.D(1),
                                  positions=account.positions)
            except LiveHistoryError as exc:
                assert str(exc) == 'HISTORY_STORE_RECORD_INVALID', str(exc)
            else:
                raise AssertionError('original residual-cap refusal was not reproduced')
            assert attempted.call_count == 1
            kind, data, at = attempted.call_args.args
            line = _canonical(_row(memory_before['_seq']+1, head_before, kind, data, at)) + b'\n'
            assert len(line) > MAX_ROW_BYTES
            assert data['universe']['flags'] == data['universe']['tickers'] == 'unavailable'
            assert data['universe']['allow'] == []
            assert data['universe']['reasons'] == ['HISTORY_ROW_SIZE_FALLBACK']
            assert data['receipt'] != 'unavailable' and len(data['holdings']) == 1500
        assert journal.read_bytes() == journal_before
        assert env.head.read() == head_before
        assert {name: getattr(env.h, name) for name in names} == memory_before
        result = dict(positions=len(account.positions), collector_requests=len(source.calls),
                      book_raw_bytes=len(raw), actual_fallback_row_bytes=len(line), cap=MAX_ROW_BYTES,
                      refusal='HISTORY_STORE_RECORD_INVALID', journal_unchanged=True,
                      independent_head_unchanged=True, memory_unchanged=True,
                      memory_fields=list(names), second_fallback_implemented=False)
        (verify.OUT/'review-capacity-actual-evidence.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    # The existing launcher supplies all 19 KEYLESS variables, the suite wrapper,
    # source/home checks, isolated roots and QA restoration. Only test discovery
    # is replaced in memory to run this scratch function.
    entries = [('review_capacity/residual_refusal_preserves_state', _wrap(actual_residual_capacity_refusal))]
    with patch.object(A, 'tests', return_value=entries):
        sys.argv = ['verify.py', '--label', 'review-capacity-actual', 'launch:review_capacity/']
        raise SystemExit(verify.main())
