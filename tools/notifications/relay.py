"""Standalone Windows alert relay. It can dispatch notices, never place orders or sign."""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from cryptography.exceptions import UnsupportedAlgorithm

from . import sources
from .providers import Android, ConfigurationError, Telegram, read_limited, setup_vapid

READERS = {
    "control_root": sources.scan_control,
    "compliance_log": sources.scan_compliance,
    "execution_alerts": sources.scan_execution,
}
MAX_ATTEMPTS = 5
LEASE = 120


def private_path(directory, name):
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError("private_path_invalid")
    return directory / name


def configuration(path):
    directory = path.absolute().parent
    config = json.loads(read_limited(path))
    if not isinstance(config, dict) or set(config) - {"origin", "telegram", "android", "sources"}:
        raise ConfigurationError("unknown_config_key")
    channels = {}
    if "telegram" in config:
        item = config["telegram"]
        token = read_limited(private_path(directory, item["token_file"]), 256).decode("ascii").strip()
        channels["telegram"] = Telegram(token, item["chat_id"], config["origin"])
    if "android" in config:
        item = config["android"]
        registration = json.loads(read_limited(private_path(directory, item["subscription"])))
        key = read_limited(private_path(directory, item["vapid_private_key"]))
        channels["android"] = Android(registration, key, config["origin"])
    inputs = config.get("sources")
    if not channels or not isinstance(inputs, dict) or not inputs or set(inputs) - READERS.keys():
        raise ConfigurationError("configure_channels_and_sources")
    return channels, {name: private_path(directory, path) for name, path in inputs.items()}


def open_db(path):
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.execute("PRAGMA synchronous=FULL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            event TEXT NOT NULL, channel TEXT NOT NULL, state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, eligible INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '', PRIMARY KEY(event,channel)
        );
        CREATE INDEX IF NOT EXISTS ready_jobs ON jobs(channel,state,eligible);
        CREATE TABLE IF NOT EXISTS cooldown (channel TEXT PRIMARY KEY, until INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS health (source TEXT PRIMARY KEY, incident TEXT);
        CREATE TABLE IF NOT EXISTS attempts (
            event TEXT NOT NULL, channel TEXT NOT NULL, serial INTEGER NOT NULL,
            started INTEGER NOT NULL, ended INTEGER, result TEXT,
            PRIMARY KEY(event,channel,serial)
        );
    """)
    return db


@contextmanager
def transaction(db):
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def record(db, channels, ids, state="pending"):
    for key in ids:
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("bad_event_id")
        db.executemany("INSERT OR IGNORE INTO jobs(event,channel,state) VALUES (?,?,?)",
                       [(key, channel, state) for channel in channels])


def observe(db, channels, inputs, *, baseline=False):
    failed = []
    for name, path in inputs.items():
        try:
            ids = READERS[name](path)
        except sources.SourceError:
            failed.append(name)
            if baseline:
                continue
            with transaction(db):
                old = db.execute("SELECT incident FROM health WHERE source=?", (name,)).fetchone()
                incident = old[0] if old and old[0] else hashlib.sha256(uuid.uuid4().bytes).hexdigest()
                db.execute("INSERT OR REPLACE INTO health VALUES (?,?)", (name, incident))
                record(db, channels, (incident,))
            continue
        with transaction(db):
            record(db, channels, ids, "baseline" if baseline else "pending")
            db.execute("INSERT OR REPLACE INTO health VALUES (?,NULL)", (name,))
    return failed


def claim(db, channel, now):
    with transaction(db):
        cooling = db.execute("SELECT until FROM cooldown WHERE channel=?", (channel,)).fetchone()
        if cooling and cooling[0] > now:
            return None
        # After a crash, leave a durable record that the remote delivery outcome is unknown.
        expired = db.execute("""SELECT event,attempts FROM jobs WHERE channel=? AND
                                state='sending' AND eligible<=?""", (channel, now)).fetchall()
        for event, number in expired:
            db.execute("UPDATE attempts SET ended=?,result='outcome_unknown' "
                       "WHERE event=? AND channel=? AND serial=?", (now, event, channel, number))
            state = "needs_review" if number >= MAX_ATTEMPTS else "pending"
            db.execute("UPDATE jobs SET state=?,reason='outcome_unknown' WHERE event=? AND channel=?",
                       (state, event, channel))
        row = db.execute("""SELECT event,attempts FROM jobs WHERE channel=? AND
                            state='pending' AND eligible<=? ORDER BY eligible,rowid LIMIT 1""",
                         (channel, now)).fetchone()
        if not row:
            return None
        event, number = row[0], row[1] + 1
        db.execute("""UPDATE jobs SET state='sending', attempts=?, eligible=? WHERE event=? AND channel=?""",
                   (number, now + LEASE, event, channel))
        db.execute("INSERT INTO attempts(event,channel,serial,started) VALUES (?,?,?,?)",
                   (event, channel, number, now))
        return event, number


def finish(db, channel, event, number, receipt, now):
    state, due = receipt.state, now
    if state == "retry":
        state = "needs_review" if number >= MAX_ATTEMPTS else "pending"
        due += max(receipt.retry_after, min(300, 5 * 2 ** min(number - 1, 6)))
    with transaction(db):
        changed = db.execute("""UPDATE jobs SET state=?,eligible=?,reason=?
                                WHERE channel=? AND event=? AND state='sending' AND attempts=?""",
                             (state, due, receipt.reason, channel, event, number)).rowcount
        if not changed:
            return
        db.execute("UPDATE attempts SET ended=?,result=? WHERE event=? AND channel=? AND serial=?",
                   (now, receipt.reason, event, channel, number))
        if receipt.reason == "http_429" or receipt.retry_after:
            db.execute("""INSERT INTO cooldown VALUES (?,?) ON CONFLICT(channel) DO UPDATE
                          SET until=max(until,excluded.until)""", (channel, due))


def dispatch(db, channels, limit=8, clock=time.time):
    for _ in range(limit):
        claimed = False
        for name, provider in channels.items():
            job = claim(db, name, int(clock()))
            if job is None:
                continue
            claimed = True
            event, number = job
            receipt = provider.deliver(event)
            finish(db, name, event, number, receipt, int(clock()))
        if not claimed:
            break


def summary(db):
    return {
        "queues": [{"channel": c, "state": s, "count": n} for c, s, n in
                   db.execute("SELECT channel,state,count(*) FROM jobs GROUP BY channel,state ORDER BY 1,2")],
        "held": [{"channel": c, "reason": r, "count": n} for c, r, n in db.execute(
            "SELECT channel,reason,count(*) FROM jobs WHERE state='needs_review' GROUP BY channel,reason ORDER BY 1,2")],
        "source_errors": [s[0] for s in db.execute("SELECT source FROM health WHERE incident IS NOT NULL ORDER BY 1")],
    }


def retry(db, channel):
    # Reopen held events without resetting their recorded attempt counts.
    with transaction(db):
        rows = db.execute("SELECT event FROM jobs WHERE channel=? AND state='needs_review'", (channel,)).fetchall()
        for (event,) in rows:
            # Permit a single additional attempt, even if previous attempts exhausted the budget.
            db.execute("UPDATE jobs SET state='pending',eligible=0,reason='manual_retry' WHERE channel=? AND event=?",
                       (channel, event))
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    ops = parser.add_subparsers(dest="op", required=True)
    setup = ops.add_parser("setup-vapid")
    setup.add_argument("--private-key", type=Path, required=True)
    setup.add_argument("--public-config", type=Path, required=True)
    for name in ("baseline", "run", "queue-test", "status", "retry-held"):
        cmd = ops.add_parser(name)
        cmd.add_argument("--db", type=Path, required=True)
        if name in ("baseline", "run", "queue-test"):
            cmd.add_argument("--config", type=Path, required=True)
        if name == "run":
            cmd.add_argument("--deliver", action="store_true", required=True)
            cmd.add_argument("--once", action="store_true")
            cmd.add_argument("--interval", type=int, choices=range(5, 61), default=30, metavar="5..60")
        if name == "retry-held":
            cmd.add_argument("--channel", choices=("android", "telegram"), required=True)
    args = parser.parse_args(argv)
    if args.op == "setup-vapid":
        setup_vapid(args.private_key, args.public_config)
        print("Created notification key and public browser config.")
        return 0
    if args.op in ("status", "retry-held") and not args.db.is_file():
        raise ConfigurationError("missing_db")
    if args.op in ("run", "baseline", "queue-test"):
        channels, inputs = configuration(args.config)
    db = open_db(args.db)
    try:
        if args.op == "retry-held":
            print(json.dumps({"pending_again": retry(db, args.channel)}))
        elif args.op == "queue-test":
            with transaction(db):
                record(db, channels, (hashlib.sha256(uuid.uuid4().bytes).hexdigest(),))
            print("Queued one generic test notice per configured channel.")
        elif args.op == "status":
            print(json.dumps(summary(db)))
        elif args.op == "baseline":
            failed = observe(db, channels, inputs, baseline=True)
            print(json.dumps({"baseline_unavailable": failed, **summary(db)}))
            return 1 if failed else 0
        else:
            while True:
                observe(db, channels, inputs)
                dispatch(db, channels)
                if args.once:
                    print(json.dumps(summary(db)))
                    break
                time.sleep(args.interval)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError, RecursionError, UnsupportedAlgorithm, sqlite3.Error):
        sys.exit("Notification relay stopped. Check private configuration, local files and database.")
