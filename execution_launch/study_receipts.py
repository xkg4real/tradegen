"""Bounded checks of original study receipts against complete fixed captures.

No files, network, clock, evaluator, approval or order calls. A successful audit
establishes internal consistency of supplied bytes, never market provenance.
Raw preservation/backup happens in the caller before this validator is invoked.
"""
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import re

from execution_accounts.collector import SourceReceipt
from execution_accounts.quotes import parse_orderbook
from execution_launch import managed_behavior as M
from execution_launch import strategy as S
from execution_launch.capture_v2 import parse_capture_v2
from execution_launch.paper_capture import _bar, _decision, sample_prefetched_book
from execution_launch.program import parameters_json, parse_program
from execution_launch.study import StudyCandidate, StudyPlan, SELECTION_RULE, CARRY_SELECTION_RULE

_CODE = re.compile(r'[A-Z][A-Z0-9_]{0,95}')
_SHA = re.compile(r'[0-9a-f]{64}')
_RECEIPT = {'path', 'params', 'account_scope', 'received_at', 'server_time', 'raw_body_b64', 'sha256'}
_DOMAIN = b'tradegen-study-receipt-audit/1\n'


class StudyReceiptError(ValueError):
    """Fixed refusal only; original bytes remain the caller's archival concern."""


def _need(condition, code):
    if not condition:
        raise StudyReceiptError(code)


@dataclass(frozen=True, kw_only=True)
class ReceiptLimits:
    max_log_bytes: int = 64 * 1024 * 1024
    max_line_bytes: int = 512 * 1024
    max_records: int = 20002
    max_json_depth: int = 12
    max_json_nodes: int = 100000
    max_capture_bytes: int = 16 * 1024 * 1024
    max_total_capture_bytes: int = 128 * 1024 * 1024
    max_candidates: int = 128
    max_body_bytes: int = 131072

    def __post_init__(self):
        ceilings = (64 * 1024 * 1024, 512 * 1024, 20002, 12, 100000,
                    16 * 1024 * 1024, 128 * 1024 * 1024, 128, 131072)
        for field, maximum in zip(fields(type(self)), ceilings):
            value = getattr(self, field.name)
            _need(type(value) is int and 0 < value <= maximum, 'STUDY_RECEIPTS_LIMITS_INVALID')


DEFAULT_LIMITS = ReceiptLimits()


@dataclass(frozen=True, kw_only=True)
class ReceiptAudit:
    """Non-authoritative document; consumers must validate the raw inputs again."""
    plan_digest: str
    receipt_log_sha256: str
    capture_digests: tuple[tuple[str, str], ...]
    slot_count: int
    receipt_count: int


def receipt_audit_bytes(audit):
    _need(type(audit) is ReceiptAudit, 'STUDY_RECEIPTS_AUDIT_INVALID')
    try:
        _need(all(type(value) is str and _SHA.fullmatch(value) for value in
                  (audit.plan_digest, audit.receipt_log_sha256)), 'STUDY_RECEIPTS_AUDIT_INVALID')
        rows = audit.capture_digests
        _need(type(rows) is tuple and 1 <= len(rows) <= 128
              and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                      and S._ID.fullmatch(row[0]) and type(row[1]) is str and _SHA.fullmatch(row[1])
                      for row in rows), 'STUDY_RECEIPTS_AUDIT_INVALID')
        _need(tuple(row[0] for row in rows) == tuple(sorted({row[0] for row in rows}))
              and type(audit.slot_count) is int and 2 <= audit.slot_count <= 20000
              and type(audit.receipt_count) is int and audit.receipt_count == audit.slot_count + 1,
              'STUDY_RECEIPTS_AUDIT_INVALID')
        body = {'schema_version': 1, 'plan_digest': audit.plan_digest,
                'receipt_log_sha256': audit.receipt_log_sha256, 'capture_digests': rows,
                'slot_count': audit.slot_count, 'receipt_count': audit.receipt_count}
    except (AttributeError, TypeError):
        raise StudyReceiptError('STUDY_RECEIPTS_AUDIT_INVALID') from None
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def receipt_audit_digest(audit):
    return hashlib.sha256(_DOMAIN + receipt_audit_bytes(audit)).hexdigest()


def _scan(raw, limits):
    """Bound depth and structural allocation before any JSON decoder runs."""
    quoted = escaped = False
    depth = nodes = 0
    for value in raw:
        if quoted:
            if escaped:
                escaped = False
            elif value == 92:
                escaped = True
            elif value == 34:
                quoted = False
            continue
        if value == 34:
            quoted = True
        elif value in (123, 91):
            depth += 1
            nodes += 1
        elif value in (125, 93):
            depth -= 1
        elif value in (44, 58):
            nodes += 1
        _need(depth >= 0, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
        _need(depth <= limits.max_json_depth and nodes <= limits.max_json_nodes,
              'STUDY_RECEIPTS_RESOURCE_LIMIT')


def _json(raw, limits):
    _scan(raw, limits)
    def unique(pairs):
        out = {}
        for key, value in pairs:
            _need(key not in out, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
            out[key] = value
        return out
    def invalid(_):
        raise StudyReceiptError('STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_float=invalid, parse_constant=invalid)
    except StudyReceiptError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise StudyReceiptError('STUDY_RECEIPTS_LOG_FORMAT_INVALID') from None


def _time(value):
    _need(type(value) is str and len(value) <= 40, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    try:
        result = datetime.fromisoformat(value)
        _need(result.utcoffset() is not None and result.astimezone(timezone.utc).isoformat(
            timespec='microseconds') == value, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
        return result
    except (ValueError, OverflowError):
        raise StudyReceiptError('STUDY_RECEIPTS_LOG_FORMAT_INVALID') from None


def _book(value, symbol, limits, *, slot=None):
    _need(type(value) is dict and set(value) == _RECEIPT
          and all(type(value[name]) is str for name in ('path', 'account_scope', 'raw_body_b64', 'sha256'))
          and type(value['params']) is list and len(value['params']) == 3
          and all(type(pair) is list and len(pair) == 2 and all(type(item) is str for item in pair)
                  for pair in value['params']), 'STUDY_RECEIPTS_RECEIPT_INVALID')
    encoded = value['raw_body_b64']
    _need(len(encoded) <= 4 * ((limits.max_body_bytes + 2) // 3), 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    try:
        body = base64.b64decode(encoded, validate=True)
        _need(len(body) > 0, 'STUDY_RECEIPTS_RECEIPT_INVALID')
        _need(len(body) <= limits.max_body_bytes, 'STUDY_RECEIPTS_RESOURCE_LIMIT')
        _need(base64.b64encode(body).decode('ascii') == encoded
              and hashlib.sha256(body).hexdigest() == value['sha256'], 'STUDY_RECEIPTS_RECEIPT_INVALID')
        _scan(body, limits)
        receipt = SourceReceipt(path=value['path'], params=tuple(tuple(pair) for pair in value['params']),
            account_scope=value['account_scope'], received_at=_time(value['received_at']),
            server_time=_time(value['server_time']), raw_body=body, sha256=value['sha256'])
        # For the probe no independent checked_at was recorded. Its original
        # received_at is an integrity-check reference, not an invented timestamp.
        return parse_orderbook(receipt, symbol=symbol, now=receipt.received_at if slot is None else slot)
    except StudyReceiptError:
        raise
    except (ValueError, TypeError, ArithmeticError, RecursionError):
        raise StudyReceiptError('STUDY_RECEIPTS_RECEIPT_INVALID') from None


def _plan(plan, limits):
    """Pure plan consistency only; installed source/profile checks remain upstream."""
    _need(type(plan) is StudyPlan and type(plan.schema_version) is int and plan.schema_version == 1
          and type(plan.candidates) is tuple and plan.candidates and type(plan.registry) is tuple,
          'STUDY_RECEIPTS_PLAN_INVALID')
    _need(len(plan.candidates) <= limits.max_candidates, 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    _need(all(type(candidate) is StudyCandidate for candidate in plan.candidates), 'STUDY_RECEIPTS_PLAN_INVALID')
    candidates = tuple(StudyCandidate(protocol=S.parse_protocol(S.protocol_json(candidate.protocol)),
        program=parse_program(parameters_json(candidate.program))) for candidate in plan.candidates)
    plan = replace(plan, candidates=candidates, registry=tuple(replace(row) for row in plan.registry))
    for value in (plan.plan_id, plan.asset, plan.risk_group):
        S._id(value)
    S._hash(plan.prior_research_sha256)
    registry_digest = S.validate_registry(plan.registry)
    first = candidates[0].protocol
    carry = first.evaluator_revision == M.CARRY_EVALUATOR_REVISION
    _need(first.evaluator_revision in (S.EVALUATOR_REVISION, M.CARRY_EVALUATOR_REVISION)
          and plan.selection_rule == (CARRY_SELECTION_RULE if carry else SELECTION_RULE),
          'STUDY_RECEIPTS_PLAN_INVALID')
    ids = tuple(candidate.program.strategy_id for candidate in candidates)
    studies = tuple(candidate.protocol.study_id for candidate in candidates)
    _need(ids == tuple(sorted(set(ids))) and len(set(studies)) == len(studies), 'STUDY_RECEIPTS_PLAN_INVALID')
    excluded = {'study_id', 'strategy_id', 'strategy_code_sha256', 'profile_contract_digest', 'family_members'}
    common = [{key:value for key,value in S._plain(candidate.protocol).items() if key not in excluded}
              for candidate in candidates]
    _need(all(value == common[0] for value in common), 'STUDY_RECEIPTS_PLAN_INVALID')
    for candidate in candidates:
        protocol = candidate.protocol
        _need(protocol.strategy_id == candidate.program.strategy_id and protocol.family_members == ids
              and (protocol.schema_version, protocol.evaluator_revision, protocol.symbol,
                   protocol.capture_start, protocol.capture_end, protocol.bar_seconds) ==
                  (first.schema_version, first.evaluator_revision, first.symbol,
                   first.capture_start, first.capture_end, first.bar_seconds)
              and any(row.study_id == protocol.study_id and row.protocol_digest == S.evidence_digest(protocol)
                      and row.registered_at == protocol.preregistered_at for row in plan.registry),
              'STUDY_RECEIPTS_PLAN_INVALID')
    spacing = timedelta(seconds=first.bar_seconds)
    _need((first.capture_end - first.capture_start) % spacing == timedelta(0), 'STUDY_RECEIPTS_PLAN_INVALID')
    slots = (first.capture_end - first.capture_start) // spacing + 1
    _need(2 <= slots <= 20000, 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    return plan, registry_digest, carry, slots


def validate_study_receipts(plan, captures, receipt_log, *, limits=DEFAULT_LIMITS):
    """Audit complete recorder bytes, preserving the distinction from interruption.

    A well-formed recorded end:error refuses with CAPTURE_ABORTED after all log
    rows are checked. That diagnostic does not certify partial capture files:
    recorder/sink failure can leave an archive one slot ahead of its log. Only a
    complete end:null reaches full candidate comparison and returns an audit.
    """
    _need(type(limits) is ReceiptLimits, 'STUDY_RECEIPTS_LIMITS_INVALID')
    try:
        limits = replace(limits)
    except (AttributeError, TypeError):
        raise StudyReceiptError('STUDY_RECEIPTS_LIMITS_INVALID') from None
    try:
        plan, registry_digest, carry, slots = _plan(plan, limits)
    except StudyReceiptError:
        raise
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        raise StudyReceiptError('STUDY_RECEIPTS_PLAN_INVALID') from None
    ids = {candidate.protocol.study_id for candidate in plan.candidates}
    _need(isinstance(captures, Mapping) and len(captures) == len(ids), 'STUDY_RECEIPTS_CAPTURE_FAMILY_INVALID')
    snapshot, total = {}, 0
    for key, raw in captures.items():
        _need(type(key) is str and key in ids and key not in snapshot and type(raw) is bytes,
              'STUDY_RECEIPTS_CAPTURE_FAMILY_INVALID')
        total += len(raw)
        _need(len(raw) <= limits.max_capture_bytes and total <= limits.max_total_capture_bytes,
              'STUDY_RECEIPTS_RESOURCE_LIMIT')
        snapshot[key] = raw
    _need(set(snapshot) == ids, 'STUDY_RECEIPTS_CAPTURE_FAMILY_INVALID')
    _need(type(receipt_log) is bytes, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    _need(len(receipt_log) <= limits.max_log_bytes, 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    # Check LF cardinality before allocating any split list.
    count = receipt_log.count(b'\n')
    _need(count <= limits.max_records, 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    _need(count >= 2 and receipt_log.endswith(b'\n'), 'STUDY_RECEIPTS_LOG_INCOMPLETE')
    lines = receipt_log.split(b'\n')[:-1]
    _need(all(len(line) > 0 for line in lines), 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    _need(all(len(line) <= limits.max_line_bytes for line in lines), 'STUDY_RECEIPTS_RESOURCE_LIMIT')
    rows = tuple(_json(line, limits) for line in lines)
    _need(all(type(row) is dict for row in rows) and set(rows[0]) == {'probe'}
          and set(rows[-1]) == {'end'}, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    end = rows[-1]['end']
    _need(end is None or type(end) is str and _CODE.fullmatch(end), 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
    first = plan.candidates[0].protocol
    probe = _book(rows[0]['probe'], first.symbol, limits)
    _need(probe.received_at < first.capture_start, 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
    books = []
    for index, row in enumerate(rows[1:-1]):
        _need(set(row) == {'slot', 'observed_at', 'receipt', 'decisions'}
              and type(row['slot']) is int and row['slot'] == index < slots,
              'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
        slot = first.capture_start + timedelta(seconds=index * first.bar_seconds)
        _need(_time(row['observed_at']) == slot, 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
        choices = row['decisions']
        _need(type(choices) is list and len(choices) == len(plan.candidates), 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
        for pair, candidate in zip(choices, plan.candidates):
            _need(type(pair) is list and len(pair) == 2 and type(pair[0]) is str
                  and pair[0] == candidate.program.strategy_id, 'STUDY_RECEIPTS_LOG_FORMAT_INVALID')
            try:
                if carry:
                    decision = M.parse_decision_document(pair[1])
                    _need(decision.bar_index == index and M.decision_document(decision) == pair[1],
                          'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
                elif index == slots - 1:
                    _need(pair[1] is None, 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
                else:
                    value = S._decimal(pair[1])
                    _need(value <= 1 and S._plain(value) == pair[1], 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
            except StudyReceiptError:
                raise
            except (ValueError, TypeError, AttributeError):
                raise StudyReceiptError('STUDY_RECEIPTS_LOG_FORMAT_INVALID') from None
        books.append(_book(row['receipt'], first.symbol, limits, slot=slot))
    if end is not None:
        raise StudyReceiptError('STUDY_RECEIPTS_CAPTURE_ABORTED')
    _need(len(books) == slots, 'STUDY_RECEIPTS_LOG_INCOMPLETE')
    for candidate_index, candidate in enumerate(plan.candidates):
        protocol, program = candidate.protocol, candidate.program
        try:
            if carry:
                archive = parse_capture_v2(protocol, snapshot[protocol.study_id])
                registry, source_kind, bars, decisions = archive.registry, archive.source_kind, archive.bars, archive.decisions
                _need(archive.program_parameters_json == parameters_json(program), 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
            else:
                registry, source_kind, bars, decisions = S._decode_paper_capture(snapshot[protocol.study_id])
            _need(source_kind == 'prospective_paper_capture' and S.validate_registry(registry) == registry_digest
                  and len(bars) == slots and len(decisions) == slots - (0 if carry else 1),
                  'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
            chain, marks = '', ()
            for index, (bar, book) in enumerate(zip(bars, books)):
                _bar(protocol, bar, index, bar.received_at)
                reproduced = sample_prefetched_book(book, slot=bar.observed_at, sampled_at=bar.received_at)
                _need(S._plain(bar) == S._plain(reproduced), 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
                logged = rows[index + 1]['decisions'][candidate_index][1]
                marks += (bar.mark,)
                if carry:
                    decision = decisions[index]
                    _need(decision.decided_at == bar.received_at and M.decision_document(decision) == logged,
                          'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
                elif index < slots - 1:
                    chain, expected = _decision(program, bar, index, bar.received_at, chain, marks)
                    _need(S._plain(decisions[index]) == S._plain(expected)
                          and S._plain(expected.target_fraction) == logged, 'STUDY_RECEIPTS_EVIDENCE_MISMATCH')
        except StudyReceiptError:
            raise
        except (ValueError, TypeError, AttributeError, ArithmeticError, RecursionError):
            raise StudyReceiptError('STUDY_RECEIPTS_CAPTURE_INPUT_INVALID') from None
    return ReceiptAudit(plan_digest=S.evidence_digest(plan), receipt_log_sha256=hashlib.sha256(receipt_log).hexdigest(),
        capture_digests=tuple(sorted((key, hashlib.sha256(raw).hexdigest()) for key, raw in snapshot.items())),
        slot_count=slots, receipt_count=slots + 1)
