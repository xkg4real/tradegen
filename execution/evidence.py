"""D16 deposit-type evidence (E1 spec 6 "Evidence (E1-D4)"; plan E18, E33, E1R2-3): the KIS snapshot judged against
the four E1 items of core.compliance.owner.EVIDENCE_THRESHOLDS_KRW, appended as hash-chained records to
execution/evidence.jsonl. The one writer of that file, inside a poll that holds poll.lock; owner.evidence_in_force
folds it into Context.live_evidence.

A record is appended for an item only when it has none yet, when its `met` changes, or when its last record is dated
on another Asia/Seoul day than this poll (a daily heartbeat; after a clock stepped back, a re-stamp): E1R2-3, spec
rev 2, in place of one record per item per poll; the fold gives the same live_evidence either way.
collateral_105pct and broker_approval are never written. No clock: the poller passes `now`."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

from core.compliance import model, owner
from core.isolation import checked_target
from execution import snapshot

_DEPOSIT_ITEMS = ("deposit_krw_10m", "deposit_krw_15m", "deposit_krw_20m")


class EvidenceBroken(Exception):
    """evidence.jsonl does not verify (owner.evidence_chain); nothing was appended (E33). The text names a line number
    and a defect, never a value."""


def _seoul_day(utc: str) -> date:
    """The Asia/Seoul date of a stamp "YYYY-MM-DDTHH:MM:SSZ"."""
    return datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(model.KST).date()


def judge(kis: snapshot.Snapshot) -> list[tuple[str, bool, float]]:
    """(item, met, value_krw) for every E1 item the snapshot can judge, in the order of EVIDENCE_THRESHOLDS_KRW;
    nothing unless it is an ok KIS snapshot with a deposit_krw. The deposit items read deposit_krw (KIS
    dnca_tot_amt); cash_krw_30m adds each foreign cash amount at its KIS rate in prices_krw and is skipped when a rate
    is missing. A value below zero or not finite is unmet and written as 0.0: owner.evidence_chain refuses the value
    itself, and an item left unjudged would keep its last met record in force for up to 7 days."""
    if kis.venue != "kis" or not kis.ok or kis.deposit_krw is None:
        return []
    deposit = float(kis.deposit_krw)
    values = dict.fromkeys(_DEPOSIT_ITEMS, deposit)
    foreign = [c for c in kis.cash if c != "KRW"]
    if all(c in kis.prices_krw for c in foreign):
        values["cash_krw_30m"] = deposit + sum(kis.cash[c] * kis.prices_krw[c] for c in foreign)
    out = []
    for item, threshold in owner.EVIDENCE_THRESHOLDS_KRW.items():
        value = values.get(item)
        if value is not None:
            value = value if 0 <= value < math.inf else 0.0   # below zero or not finite: unmet, as 0.0 (point 3)
            out.append((item, value >= threshold, value))
    return out


def due(rows: list[dict], requirement: str, met: bool, now: datetime) -> bool:
    """E1R2-3: True when `rows` (the verified chain) hold no record of `requirement`, when its last record's `met`
    differs, or when that record is dated on another Asia/Seoul day than `now`: an earlier one (the daily heartbeat),
    or a later one after the clock stepped back (re-stamped at once, so its latest record carries the day of its last
    poll, as one record per poll would). A change of value_krw alone is never due: the fold reads only met, the
    dates and the chain."""
    today = _seoul_day(model.iso_utc(now))           # first: a naive now is ValueError, whatever rows hold
    last = next((row for row in reversed(rows) if row["requirement"] == requirement), None)
    return last is None or last["met"] != met or _seoul_day(last["utc"]) != today


def record(kis: snapshot.Snapshot, now: datetime) -> list[dict]:
    """Append the due records of this poll to evidence.jsonl, under its sidecar lock, and return them (often none).
    The file is checked (checked_target) before it is read and again before it is written; a refusal propagates (a
    crash, E33). A chain that does not verify raises EvidenceBroken and nothing is appended. A snapshot with nothing
    to judge touches no file."""
    judged = judge(kis)
    if not judged:
        return []
    utc = model.iso_utc(now)
    path = owner.evidence_path()
    with snapshot.exclusive(path):
        try:
            lines = checked_target(path, "E1 evidence log").read_bytes().splitlines(keepends=True)
        except FileNotFoundError:
            lines = []
        rows, why = owner.evidence_chain(lines)       # the same split and check as owner._live_evidence
        if why:
            raise EvidenceBroken(f"evidence.jsonl is broken ({why}); nothing appended")
        prev = rows[-1]["row_sha256"] if rows else owner.GENESIS_PREV
        new = []
        for requirement, met, value in judged:
            if not due(rows, requirement, met, now):
                continue
            body = {"seq": len(rows) + len(new) + 1, "prev_sha256": prev, "utc": utc, "requirement": requirement,
                    "met": met, "value_krw": value, "snapshot_sha256": kis.snapshot_sha256}
            new.append({**body, "row_sha256": model.sha256_hex(model.canonical_json(body))})
            prev = new[-1]["row_sha256"]
        snapshot.write_lines(path, [(model.canonical_json(row) + "\n").encode("utf-8") for row in new],
                             "E1 evidence log")
    return new
