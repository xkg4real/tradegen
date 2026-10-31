"""The E1 poller and its alert CLI (E1 spec 4 "Data flow per poll", 7 "Alert records and delivery" and "The poller",
10; plan C16).

    python -m execution.poll [--once] [--interval-min N]   poll every N minutes (1 to 60, default 5), or once
    python -m execution.poll --pending                     the unsent alerts as one JSON line, for the 09:05 task
    python -m execution.poll --mark-sent UTC               mark the alert rows of that poll sent

main() is the only wall-clock reader in execution/ (E11): it reads the clock once per poll, passes `now` down and
sets transport._clock for the three send-time needs. One poller at a time: a second one finds poll.lock held, says
so and exits 0 (E1R2-1). A crashed poll is alerted (OUTAGE_CRASH for every venue) and the next poll runs as usual;
when even that alert cannot be written, one toast says so (E40). E1 only alerts: it never halts, disarms, sells or
withdraws."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import time
import traceback
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.compliance import alerts, model, owner
from core.isolation import checked_target
from execution import checks, evidence, kis_inquiry, okx_inquiry, positions, snapshot, upbit_inquiry
from execution import transport  # only for transport._clock inside main (E11, E36)

DEFAULT_INTERVAL_MIN = 5
EXIT_OK, EXIT_LOCKED, EXIT_CRASH = 0, 0, 4           # E1R2-1: a second poller exits 0 with a message (spec 4)
PLACEHOLDER = model.Positions(equity_krw=1.0)        # E24: the only positions load_context ever gets from E1
UNVERIFIED = "An E1 alert row did not verify; read ~/.tradegen/execution/alerts.jsonl on the PC."
_LOCKED = "another E1 poller holds poll.lock; exiting"
_sleep = time.sleep                                  # the loop's and held_lock's seam; reads no clock
_unlogged: set = set()                               # Seoul dates on which CRASH_UNLOGGED was toasted (E40)


def alerts_path() -> Path:
    """execution/alerts.jsonl, E1's alert rows (spec 7); core/compliance/alerts.py keeps its own file."""
    return snapshot.home() / "alerts.jsonl"


def lock_path() -> Path:
    """execution/poll.lock, held by the one running poller (spec 4)."""
    return snapshot.home() / "poll.lock"


def _byte_lock(fh, lock: bool) -> None:
    """Locks byte 0 of `fh` without waiting (PermissionError or BlockingIOError when another handle holds it), or
    unlocks it."""
    fh.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK if lock else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB if lock else fcntl.LOCK_UN)


@contextlib.contextmanager
def held_lock() -> Iterator[bool]:
    """poll.lock: yields True when this handle took it (released on exit), False when another handle still holds it
    after 5 tries 0.2 s apart (so the test wrapper's instant probe of the real lock never makes a starting poller
    exit). A refused path (a link, QUANTGEN) raises before anything is opened."""
    checked_target(snapshot.home(), "E1 state folder").mkdir(parents=True, exist_ok=True)
    with open(checked_target(lock_path(), "E1 poll lock"), "a+b") as fh:
        got = False
        for attempt in range(5):
            if attempt:
                _sleep(0.2)
            try:
                _byte_lock(fh, True)
                got = True
                break
            except (PermissionError, BlockingIOError):  # another poller (or another handle here) holds it
                pass
        try:
            yield got
        finally:
            if got:
                _byte_lock(fh, False)


def _counts(snap: snapshot.Snapshot) -> dict:
    """How many records of each kind a snapshot holds: counts only, never an amount or an address (C16.3)."""
    return {"holdings": len(snap.holdings), "open_orders": len(snap.open_orders), "fills": len(snap.fills),
            "deposits": len(snap.deposits), "withdrawals": len(snap.withdrawals),
            "addresses": len(snap.withdrawal_addresses)}


def _record_alerts(raw: list, done: frozenset, now: datetime) -> list:
    """C16.2 steps 7 and 8: the once-a-day rule against alerts.jsonl under its lock, the fresh and clear rows
    appended, then one toast per fresh red or amber alert (an info row is never toasted). Returns the fresh alerts."""
    path, utc = alerts_path(), model.iso_utc(now)
    with snapshot.exclusive(path):
        fresh, clears = checks.due(raw, done, snapshot.read_all(path), now)
        snapshot.write_lines(path, [(model.canonical_json(checks.row(a, utc)) + "\n").encode("utf-8")
                                    for a in fresh + clears], "E1 alerts")
    for alert in fresh:
        if alert.level in ("red", "amber"):
            alerts._toast(f"TRADEGEN E1 {alert.level}", checks.render(alert))
    return fresh


def poll_once(now: datetime) -> dict:
    """One poll at `now` (spec 4 data flow; C16.2); returns the redacted summary (C16.3). Venue errors stay inside
    their snapshots (E38); anything else, a refused write included, propagates and main alerts it as a crash."""
    ctx = owner.load_context(now, PLACEHOLDER)           # first, before any venue is asked (E24, E42)
    today = now.astimezone(model.KST).date()
    upbit = upbit_inquiry.snapshot(now)
    okx = okx_inquiry.snapshot(now, upbit.prices_krw.get("USDT") if upbit.ok else None)
    kis = kis_inquiry.snapshot(now, ctx)                 # sends nothing unless ctx.code_signed is True (E42)
    new = {"kis": kis, "upbit": upbit, "okx": okx}
    # ponytail: only yesterday's and today's files are read (E30); a venue whose last ok snapshot is older is compared
    # again from its next ok snapshot. Read further back if a check ever needs a longer memory.
    rows = (snapshot.read_all(snapshot.inquiry_path(today - timedelta(days=1)))
            + snapshot.read_all(snapshot.inquiry_path(today)))
    prev, start = checks.priors(rows), checks.day_start(rows, now)
    with snapshot.exclusive(snapshot.home() / "inquiry"):
        snapshot.write_lines(snapshot.inquiry_path(today), [snapshot.dump(new[v]) for v in snapshot.VENUES],
                             "E1 inquiry log")
    own, done, recorded = [], set(), 0
    if kis.ok:
        try:
            recorded = len(evidence.record(kis, now))
        except evidence.EvidenceBroken:                  # fail closed: no live evidence counts (E33)
            recorded = "broken"
            own.append(checks.Alert(venue="kis", kind="EVIDENCE", level="amber", text_key="EVIDENCE_BROKEN"))
        done.add(("kis", "EVIDENCE"))
    live = positions.live_positions(new, now)
    if start is None and live is not None:               # the first live poll of the Seoul day is the start (E34)
        start = (live.equity_krw, model.iso_utc(now))
    limits = checks.limits_from(ctx.owner, start)
    raw = checks.run_checks(prev, new, ctx.owner, limits, now) + own
    done |= checks.evaluated(prev, new, ctx.owner, limits, now)
    skipped = checks.not_set(new, ctx.owner, limits, live)
    if skipped:                                          # E43: one info row a day, never toasted or sent
        raw.append(checks.Alert(venue="all", kind="NOT_SET", level="info", text_key="NOT_SET",
                                slots={"skipped": "; ".join(skipped)}))
    fresh = _record_alerts(raw, frozenset(done), now)
    return {"utc": model.iso_utc(now),
            "venues": {v: "ok" if new[v].ok else "error" for v in snapshot.VENUES},
            "errors": {v: new[v].error for v in snapshot.VENUES if not new[v].ok},
            "counts": {v: _counts(new[v]) for v in snapshot.VENUES},
            "evidence": recorded,
            "alerts": sum(a.level in ("red", "amber") for a in fresh),
            "not_set": list(skipped)}


def _crash_line(exc: BaseException) -> str:
    """{"crash": <type name>, "at": "<file name>:<line>"} of the innermost frame; never str(exc), which can quote a
    value (E37)."""
    frames = traceback.extract_tb(exc.__traceback__)
    at = f"{Path(frames[-1].filename).name}:{frames[-1].lineno}" if frames else ""
    return json.dumps({"crash": type(exc).__name__, "at": at}, ensure_ascii=True)


def _crash(now: datetime, exc: BaseException) -> None:
    """The crash path (C16.2; spec 7 "a crashed poll is logged and alerted"): the crash line, then OUTAGE_CRASH for
    every venue through the once-a-day rule. When that fails too, the toast-only CRASH_UNLOGGED, at most once per
    process per Seoul date, and the second crash line (E40)."""
    print(_crash_line(exc), flush=True)
    when = model.iso_utc(now)
    try:
        _record_alerts([checks.Alert(venue=v, kind="OUTAGE", level="amber", text_key="OUTAGE_CRASH",
                                     slots={"when": when}) for v in snapshot.VENUES], frozenset(), now)
    except Exception as again:                           # the alert rows cannot be written either
        day = now.astimezone(model.KST).date()
        if day not in _unlogged:
            _unlogged.add(day)
            alerts._toast("TRADEGEN E1 amber", checks.render(checks.Alert(
                venue="all", kind="OUTAGE", level="amber", text_key="CRASH_UNLOGGED", slots={"when": when})))
        print(_crash_line(again), flush=True)


def _line(row: dict) -> str | None:
    """`<KST time> <level>: <sentence>` for a row that verifies (verify_row also makes sure its utc is a real instant
    with a Seoul date); None otherwise."""
    if not checks.verify_row(row):
        return None
    kst = datetime.fromisoformat(row["utc"]).astimezone(model.KST)
    alert = checks.Alert(venue=row["venue"], kind=row["kind"], level=row["level"], text_key=row["text_key"],
                         slots=row["slots"])
    return f"{kst:%Y-%m-%d %H:%M} KST {row['level']}: {checks.render(alert)}"


def pending(rows: list) -> dict:
    """The --pending message (C16.4; E23): every unsent red or amber row in file order, each re-verified before it is
    rendered, since the 09:05 task forwards the text off the PC. Any row that fails gives the one UNVERIFIED line and
    none of its own text; a clear or info row never leaves the PC (E43)."""
    listed = [r for r in rows if isinstance(r, dict) and r.get("sent") is False
              and r.get("level") not in ("clear", "info")]
    if not listed:
        return {"send": False}
    body, red = [], 0
    for r in listed:
        line = _line(r)
        if line is None:
            if UNVERIFIED not in body:
                body.append(UNVERIFIED)
        else:
            body.append(line)
            red += r["level"] == "red"
    utcs = sorted({r["utc"] for r in listed if isinstance(r.get("utc"), str) and checks.STAMP.fullmatch(r["utc"])})
    return {"send": True, "subject": f"TRADEGEN E1: {len(listed)} alert(s), {red} red", "body": "\n".join(body),
            "utcs": utcs}


def _row_of(line: bytes) -> dict | None:
    """The JSON object on `line`, or None (a torn or foreign line, kept as it is)."""
    try:
        row = json.loads(line)
    except (ValueError, RecursionError):
        return None
    return row if isinstance(row, dict) else None


def mark_sent(utc: str) -> int:
    """Marks every unsent row of the poll stamped `utc` sent and keeps every other line byte for byte; returns how
    many rows changed (0 on a repeat). A missing alerts.jsonl is 0 and creates nothing. Takes the alerts lock, never
    poll.lock (E23)."""
    path = alerts_path()
    if not path.is_file():
        return 0
    with snapshot.exclusive(path):
        out, marked = [], 0
        for line in path.read_bytes().splitlines(keepends=True):
            row = _row_of(line)
            if row is not None and row.get("utc") == utc and row.get("sent") is False:
                line = (model.canonical_json({**row, "sent": True}) + "\n").encode("utf-8")
                marked += 1
            out.append(line)
        if marked:
            checked_target(path, "E1 alerts log")       # refused before a temp file exists
            tmp = path.with_name(f".alerts.jsonl.{os.urandom(6).hex()}.tmp")
            with open(checked_target(tmp, "E1 alerts temp"), "xb") as fh:
                fh.write(b"".join(out))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(checked_target(tmp, "E1 alerts temp"), checked_target(path, "E1 alerts log"))
    return marked


def _minutes(text: str) -> int:
    """--interval-min: a whole number of minutes from 1 to 60."""
    if not (text.isascii() and text.isdigit() and 1 <= int(text) <= 60):
        raise argparse.ArgumentTypeError("takes a whole number of minutes from 1 to 60")
    return int(text)


def _stamp(text: str) -> str:
    """--mark-sent: a poll's utc exactly as alerts.jsonl holds it."""
    if not checks.STAMP.fullmatch(text):
        raise argparse.ArgumentTypeError("takes a UTC stamp YYYY-MM-DDTHH:MM:SSZ")
    return text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m execution.poll",
                                     description="E1 read-only account inquiry: poll, or hand over unsent alerts.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="one poll, then exit (0 ok, 4 after a crash)")
    mode.add_argument("--pending", action="store_true", help="print the unsent alerts as one JSON line")
    mode.add_argument("--mark-sent", metavar="UTC", type=_stamp, help="mark the alert rows of that poll sent")
    parser.add_argument("--interval-min", metavar="N", type=_minutes,
                        help=f"minutes between polls, 1 to 60 (default {DEFAULT_INTERVAL_MIN}); the loop only")
    return parser


def main(argv: list[str] | None = None) -> int:
    """The CLI (C16.1). Every wall-clock read of execution/ is in this body (E11)."""
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if args.interval_min is not None and (args.once or args.pending or args.mark_sent is not None):
            parser.error("--interval-min applies to the loop only")
    except SystemExit as exc:                            # argparse printed the reason
        return EXIT_OK if exc.code == 0 else EXIT_CRASH
    if args.pending or args.mark_sent is not None:      # neither takes poll.lock or sets the clock
        try:
            out = pending(snapshot.read_all(alerts_path())) if args.pending else {"marked": mark_sent(args.mark_sent)}
        except Exception as exc:
            print(_crash_line(exc), flush=True)
            return EXIT_CRASH
        print(json.dumps(out, ensure_ascii=True), flush=True)
        return EXIT_OK
    transport._clock = lambda: datetime.now(timezone.utc)    # the OKX header and offset, the KIS token's age (E11)
    interval_s = (args.interval_min or DEFAULT_INTERVAL_MIN) * 60
    now = datetime.now(timezone.utc)
    try:
        with held_lock() as got:
            if not got:
                print(_LOCKED, flush=True)
                return EXIT_LOCKED
            while True:
                try:
                    print(json.dumps(poll_once(now), ensure_ascii=True), flush=True)
                    crashed = False
                except Exception as exc:                 # alerted; the next poll runs as usual (spec 7)
                    _crash(now, exc)
                    crashed = True
                if args.once:
                    return EXIT_CRASH if crashed else EXIT_OK
                elapsed = (datetime.now(timezone.utc) - now).total_seconds()
                # a clock stepped back (negative elapsed) still sleeps one interval at most (ledger ruling, Task 12)
                _sleep(min(float(interval_s), max(0.0, interval_s - elapsed)))
                now = datetime.now(timezone.utc)
    except KeyboardInterrupt:                            # Ctrl+C or the end of the task: the lock is released
        return EXIT_OK
    except Exception as exc:                             # poll.lock itself was refused (a link): E40
        _crash(now, exc)
        return EXIT_CRASH


if __name__ == "__main__":
    raise SystemExit(main())
