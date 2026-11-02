"""Create wholly invented paper inputs in an explicitly selected NEW directory.

    python -m tools.research.prepare_launch_example --directory /tmp/new-example --now 2030-01-01T12:00:00+00:00

The cash baseline never trades and cannot qualify as a live strategy. No owner
values, credentials, approval or network access are used. Existing destinations
and linked/private parent paths are refused; partial writes are not repaired.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

from execution_control.model import InstrumentRules
from execution_launch import paper_capture, program
from execution_launch.profile import (
    AccountingConventions, LaunchProfile, PolicyInputs, profile_body,
    profile_contract_digest, rule_terms_digest,
)
from execution_launch.strategy import (
    EVALUATOR_REVISION, ForwardProtocol, PaperBar, protocol_json, register_protocol,
)
from execution_launch.workflow import WorkflowError, _artifact, _time

_PRIVATE = frozenset({'.tradegen', '.nextgen', '.ssh', '.aws', '.gnupg', '.azure', '.kube', '.git'})
_FILES = ('profile.json', 'protocol.json', 'program.json', 'bars.json')


def _require(condition, code):
    if not condition:
        raise WorkflowError(code)


def example_files(*, now):
    """Return exact input texts for a deliberately nonqualifying synthetic cash baseline."""
    _require(type(now) is datetime and now.utcoffset() is not None, 'EXAMPLE_AWARE_TIME_REQUIRED')
    now = now.astimezone(timezone.utc)
    end = now - timedelta(seconds=1)
    start = end - timedelta(hours=1)
    spec = program.ProgramSpec(schema_version=1, strategy_id='synthetic-cash-baseline',
        kind='cash', fast_window=0, slow_window=0, exposure_fraction=Decimal('0'))
    code = program.program_digest(spec, _artifact('program.py'))
    source = hashlib.sha256(_artifact('paper_capture.py')).hexdigest()
    rules = InstrumentRules(venue='upbit', market='spot', symbol='KRW-BTC',
        lot_size=Decimal('0.01'), tick_size=Decimal('1'), min_quantity=Decimal('0.01'),
        min_notional_krw=Decimal('10'), fee_fraction=Decimal('0.001'), asof=now,
        source_digest=hashlib.sha256(b'invented-instrument-terms-not-exchange-data').hexdigest())
    profile = LaunchProfile(schema_version=1, profile_id='synthetic-example-never-live',
        venue='upbit', market='spot', symbol='KRW-BTC', quote_currency='KRW',
        account_scope='synthetic-account-not-an-owner-account', time_in_force='gtc',
        strategy_id=spec.strategy_id, strategy_code_sha256=code, instrument_rules=rules,
        policy=PolicyInputs(version='synthetic-example', source_sha256='a'*64,
            initial_equity=Decimal('12000'), drawdown_activation_equity=Decimal('50000'),
            positive_profit_loss_fraction=Decimal('0.2'), peak_drawdown_fraction=Decimal('0.25'),
            zero_profit_day_target_fraction=Decimal('0.1'), first_day_loss_budget=None,
            zero_profit_day_loss_budget=None),
        conventions=AccountingConventions(valuation='marked_equity', daily_loss='externally_reconciled',
            external_flows='externally_cashflow_adjusted', realized_profit='fifo_all_fees_krw',
            fx='current_marks_execution_time_fills', rounding='fifo_floor_18dp_remainder_to_final',
            day_boundary='Asia/Seoul', first_day_scope='first_trading_day_only'))
    protocol = ForwardProtocol(schema_version=1, study_id='synthetic-example-no-real-study',
        strategy_id=spec.strategy_id, strategy_code_sha256=code,
        capture_source_id='synthetic-batch-no-real-feed', capture_source_code_sha256=source,
        evaluator_revision=EVALUATOR_REVISION, profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(rules), venue='upbit', market='spot', symbol='KRW-BTC',
        quote_currency='KRW', preregistered_at=start-timedelta(minutes=1), capture_start=start,
        capture_end=end, initial_cash_quote=Decimal('12000'), fee_fraction=Decimal('0.001'),
        slippage_bps=Decimal('0'), bar_seconds=60, minimum_fill_delay_seconds=1,
        minimum_observations=60, minimum_roundtrips=20, block_length=5,
        bootstrap_replications=999, family_members=(spec.strategy_id,), alpha=Decimal('0.05'),
        max_drawdown=Decimal('0.1'), review_max_age_seconds=86400, seed=773)
    registry = register_protocol(protocol)  # Synthetic timestamps, not genuine preregistration.
    bars = tuple(PaperBar(observed_at=start+timedelta(minutes=i),
        received_at=start+timedelta(minutes=i, seconds=1), bid=Decimal(100+i%5),
        ask=Decimal(100+i%5), mark=Decimal(100+i%5), quote_krw=Decimal('1'),
        source_sha256=hashlib.sha256(('invented-quote-'+str(i)).encode('ascii')).hexdigest())
        for i in range(61))
    archive = paper_capture.CaptureArchive(registry=registry, source_kind='synthetic', bars=bars, decisions=())
    envelope = json.loads(paper_capture.capture_json(archive))
    del envelope['decisions']
    return {'profile.json': json.dumps(profile_body(profile), indent=2, sort_keys=True)+'\n',
            'protocol.json': protocol_json(protocol), 'program.json': program.program_json(spec),
            'bars.json': json.dumps(envelope, indent=2, sort_keys=True)+'\n'}


def _plain(entry):
    """An lstat result that is neither a symlink nor any other reparse point (junction, mount, cloud placeholder)."""
    return (not stat.S_ISLNK(entry.st_mode)
            and not getattr(entry, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _write_windows(absolute, contents):
    """No dir_fd or O_NOFOLLOW on Windows: every ancestor is lstat-checked as a plain directory, mkdir is the
    exclusive create (an existing entry, a dangling link included, fails), and each file is created O_EXCL and then
    proven to be the directory entry just written (same volume and file index, no reparse point, one name)."""
    for ancestor in reversed(absolute.parents):
        entry = os.lstat(ancestor)
        _require(stat.S_ISDIR(entry.st_mode) and _plain(entry), 'EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS')
    os.mkdir(absolute, mode=0o700)
    made = os.lstat(absolute)
    _require(stat.S_ISDIR(made.st_mode) and _plain(made), 'EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS')
    for name in _FILES:
        target = absolute / name
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY | os.O_NOINHERIT, 0o600)
        try:
            opened, entry = os.fstat(descriptor), os.lstat(target)
            _require(_plain(entry) and entry.st_nlink == 1
                     and (entry.st_dev, entry.st_ino) == (opened.st_dev, opened.st_ino),
                     'EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS')
            raw = contents[name].encode('utf-8')
            while raw:
                written = os.write(descriptor, raw)
                _require(written > 0, 'EXAMPLE_WRITE_INCOMPLETE')
                raw = raw[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    final = os.lstat(absolute)
    _require(_plain(final) and (final.st_dev, final.st_ino) == (made.st_dev, made.st_ino),
             'EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS')


def write_new_directory(path, contents):
    """Write the four fixed files exclusively under a new, non-linked directory."""
    _require(type(path) is str and path and '\x00' not in path, 'EXAMPLE_DIRECTORY_REFUSED')
    candidate = Path(path)
    _require('..' not in candidate.parts and candidate.name not in ('', '.', '..'), 'EXAMPLE_DIRECTORY_REFUSED')
    absolute = Path(os.path.abspath(candidate))
    # Home directories are refused. Windows has no /tmp: its scratch area lives inside the profile, so on nt only
    # the interpreter's temporary directory is allowed under C:\Users (the rest of the profile stays refused).
    scratch = os.name == 'nt' and absolute.is_relative_to(Path(os.path.abspath(tempfile.gettempdir())))
    _require(len(absolute.parts) > 1 and (absolute.parts[1].casefold() not in ('home', 'root', 'users') or scratch),
             'EXAMPLE_HOME_DIRECTORY_REFUSED')
    _require(not any(part.casefold() in _PRIVATE or part.casefold() == '.env'
                     or part.casefold().startswith('.env.') for part in absolute.parts), 'EXAMPLE_DIRECTORY_REFUSED')
    _require(set(contents) == set(_FILES) and all(type(v) is str for v in contents.values()),
             'EXAMPLE_CONTENTS_INVALID')
    posix = (os.open in os.supports_dir_fd and os.mkdir in os.supports_dir_fd
             and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY'))
    _require(posix or os.name == 'nt', 'EXAMPLE_PLATFORM_UNSUPPORTED')
    if not posix:
        try:
            _write_windows(absolute, contents)
        except OSError:
            raise WorkflowError('EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS') from None
        return
    parent = child = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
        parent = os.open(absolute.anchor, flags)
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, flags, dir_fd=parent)
            os.close(parent); parent = next_fd
        os.mkdir(absolute.name, mode=0o700, dir_fd=parent)
        child = os.open(absolute.name, flags, dir_fd=parent)
        for name in _FILES:
            descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 mode=0o600, dir_fd=child)
            try:
                raw = contents[name].encode('utf-8')
                while raw:
                    written = os.write(descriptor, raw)
                    _require(written > 0, 'EXAMPLE_WRITE_INCOMPLETE')
                    raw = raw[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        os.fsync(child)
        os.fsync(parent)
    except OSError:
        raise WorkflowError('EXAMPLE_DIRECTORY_UNAVAILABLE_OR_EXISTS') from None
    finally:
        if child is not None:
            os.close(child)
        if parent is not None:
            os.close(parent)


def main(argv=None):
    try:
        args = sys.argv[1:] if argv is None else argv
        _require(type(args) in (list, tuple) and all(type(v) is str for v in args), 'EXAMPLE_ARGUMENTS_REQUIRED')
        if tuple(args) in (('--help',), ('-h',)):
            print(__doc__); return 0
        _require(len(args) == 4 and args[0] == '--directory' and args[2] == '--now', 'EXAMPLE_ARGUMENTS_REQUIRED')
        now = _time(args[3])
        contents = example_files(now=now)
        write_new_directory(args[1], contents)
        print(json.dumps({'workflow_complete': True, 'source_kind': 'synthetic',
            'files': list(_FILES), 'execution_ready': False, 'owner_approval_verified': False}, sort_keys=True))
        return 0
    except (WorkflowError, ValueError, TypeError, AttributeError, OSError, ArithmeticError):
        print(json.dumps({'workflow_complete': False, 'execution_ready': False,
                          'reasons': ['EXAMPLE_INPUT_OR_NEW_DIRECTORY_REFUSED']}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
