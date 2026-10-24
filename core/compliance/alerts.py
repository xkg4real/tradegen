"""Owner alerts for the daily compliance check (spec 5.4, D5; P26). `due()` decides from the --check summary and
the alerts.jsonl history which alerts are owed today; `render()` fills a fixed template with ids, dates and numbers
only, never rule free text; `_toast()` shows a Windows notification; `log()` appends the alerts.jsonl row, which
also anchors the owner log (seq, row_sha256) and records the key fingerprint (P20). The iOS push and the email are
sent by the daily Claude task, and only to OWNER_ALERT_EMAIL."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone

from core.compliance import model, rules
from core.isolation import checked_target

OWNER_ALERT_EMAIL = "sapientia@korea.ac.kr"
_CHANNELS = ("toast", "push", "email")
_RESULTS = ("ok", "fail")
_FIELDS = ("review_by", "auto_off", "effective_until")
_THRESHOLDS = (3, 14)                  # spec 5.4: the first run at or below 14 days left, again at or below 3
_MISSING = {"code": 4, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,63}")
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_FINGERPRINT = re.compile(r"SHA256:[0-9a-f]{64}")
_HEADLINES = {"summary_missing": "the daily check gave no usable summary",
              "failed": "the check itself failed (exit 4)",
              "state": "new exposure is blocked (exit 3)",
              "key_changed": "KEY CHANGED"}
_LINES = {"summary_missing": "The daily --check printed no readable summary line, or it did not match the exit "
                             "code. Treat new exposure as blocked and run the check by hand.",
          "failed": "The --check itself failed (exit 4). Treat new exposure as blocked and run the check by hand.",
          "state": "The --check found an invalid or unapproved table, unsigned code, a broken owner log or a "
                   "changed key (exit 3). New exposure is blocked; exits stay open (D11)."}
_OVERDUE = {"review_by": ("review overdue", "review by {when} has passed ({n} days late). New exposure under it "
                          "is blocked; exits stay open."),
            "auto_off": ("auto_off reached", "auto_off {when} is reached ({n} days ago). New exposure under it is "
                         "blocked; exits stay open."),
            "effective_until": ("effective_until reached", "effective until {when} has passed ({n} days ago). The "
                                "row is no longer in force; re-review the table.")}
_OVERDUE_UNKNOWN = ("(unrecognised field) overdue", "(unrecognised field) {when} ({n} days late).")
_TOAST_PS = "; ".join((
    "$ErrorActionPreference = 'Stop'",
    "[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
    "ContentType = WindowsRuntime]",
    "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02)",
    "$t = $x.GetElementsByTagName('text')",
    "[void]$t.Item(0).AppendChild($x.CreateTextNode($env:TRADEGEN_TOAST_TITLE))",
    "[void]$t.Item(1).AppendChild($x.CreateTextNode($env:TRADEGEN_TOAST_BODY))",
    r"$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'",
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show("
    "[Windows.UI.Notifications.ToastNotification]::new($x))",
))


def _int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _iso(value) -> date | None:
    if not (isinstance(value, str) and _DAY.fullmatch(value)):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _item(item, count: str) -> bool:
    return (isinstance(item, dict) and set(item) == {"row", "field", "date", count} and isinstance(item["row"], str)
            and item["field"] in _FIELDS and _iso(item["date"]) is not None and _int(item[count])
            and item[count] >= 0)


def _valid_summary(summary) -> bool:
    """A --check summary line as rules.main prints it: exactly rules._SUMMARY_KEYS, typed; the head an owner-log
    anchor as Task 11's read_anchors takes it (seq 0 exactly when the sha is ""); the fingerprint "" or
    SHA256:<64 hex>; and a code 0 to 2 that agrees with its due and overdue lists."""
    if not (isinstance(summary, dict) and set(summary) == set(rules._SUMMARY_KEYS)):
        return False
    code, seq, sha, fp = summary["code"], summary["head_seq"], summary["head_sha256"], summary["fingerprint"]
    return (_int(code) and 0 <= code <= 4
            and isinstance(summary["due"], list) and all(_item(i, "days_left") for i in summary["due"])
            and isinstance(summary["overdue"], list) and all(_item(i, "days_late") for i in summary["overdue"])
            and _int(seq) and seq >= 0 and isinstance(sha, str)
            and (sha == "" if seq == 0 else _HEX64.fullmatch(sha) is not None)
            and isinstance(fp, str) and (fp == "" or _FINGERPRINT.fullmatch(fp) is not None)
            and (code > 2 or code == (2 if summary["overdue"] else 1 if summary["due"] else 0)))


def _sent(history: list) -> set:
    """(row, field, date, threshold) of every due item that an alert row with result "ok" already carried."""
    out = set()
    for row in history:
        if not (isinstance(row, dict) and row.get("result") == "ok" and isinstance(row.get("due"), list)):
            continue
        for item in row["due"]:
            if isinstance(item, dict) and _int(item.get("days_left")):
                out.update((item.get("row"), item.get("field"), item.get("date"), t)
                           for t in _THRESHOLDS if item["days_left"] <= t)
    return out


def due(summary: dict | None, history: list[dict], today: date) -> list[dict]:
    """The alerts owed today, most severe first (spec 5.4). Every day: a missing or malformed summary, exit 4,
    exit 3 (headed by KEY CHANGED when its key fingerprint is not the first one recorded; owner_state accepts a
    signed rotation, which stays exit 0), each overdue item. Once per threshold: a row date at or below 14 days
    left, then at or below 3, counted as sent only when an "ok" row in `history` (alerts.jsonl, oldest first)
    carried it, so a missed or failed run alerts on the next one. Pure."""
    if not _valid_summary(summary):
        return [{"kind": "summary_missing"}]
    out = [{"kind": "failed"}] if summary["code"] == 4 else []
    if summary["code"] == 3:
        first = next((r for r in history if isinstance(r, dict) and isinstance(r.get("fingerprint"), str)
                      and r["fingerprint"]), None)
        if first is not None and summary["fingerprint"] and summary["fingerprint"] != first["fingerprint"]:
            out.append({"kind": "key_changed", "since": str(first.get("utc", ""))[:10]})
        out.append({"kind": "state"})
    out += [{"kind": "overdue", **item} for item in summary["overdue"]]
    sent = _sent(history)
    for item in sorted(summary["due"], key=lambda i: (i["date"], i["row"], i["field"])):
        left = (_iso(item["date"]) - today).days
        for threshold in _THRESHOLDS:
            if 0 <= left <= threshold:
                if (item["row"], item["field"], item["date"], threshold) not in sent:
                    out.append({"kind": "due", **item, "days_left": left, "threshold": threshold})
                break
    return out


def _id(value) -> str:
    return value if isinstance(value, str) and _ID.fullmatch(value) else "(unrecognised id)"


def _when(value) -> str:
    day = _iso(value)
    return day.isoformat() if day is not None else "(unrecognised date)"


def _num(value) -> str:
    return str(value) if _int(value) else "?"


def _field(value) -> str:
    return value if isinstance(value, str) and value in _FIELDS else "(unrecognised field)"


def _overdue(alert: dict) -> tuple[str, str]:
    """(subject end, line template) of an overdue alert, by its field."""
    field = alert.get("field")
    return _OVERDUE.get(field, _OVERDUE_UNKNOWN) if isinstance(field, str) else _OVERDUE_UNKNOWN


def _subject(alert: dict) -> str:
    kind = alert.get("kind")
    if kind == "due":
        return (f"TRADEGEN compliance: {_id(alert.get('row'))} {_field(alert.get('field'))} in "
                f"{_num(alert.get('days_left'))} days")
    if kind == "overdue":
        return f"TRADEGEN compliance: {_id(alert.get('row'))} {_overdue(alert)[0]}"
    return "TRADEGEN compliance: " + _HEADLINES.get(kind, "alert")


def _line(alert: dict) -> str:
    kind = alert.get("kind")
    if kind == "due":
        return (f"Rule {_id(alert.get('row'))}: {_field(alert.get('field'))} {_when(alert.get('date'))}, "
                f"{_num(alert.get('days_left'))} days left.")
    if kind == "overdue":
        return f"Rule {_id(alert.get('row'))}: " + _overdue(alert)[1].format(when=_when(alert.get("date")),
                                                                            n=_num(alert.get("days_late")))
    if kind == "key_changed":
        since = _when(alert.get("since"))
        return (f"KEY CHANGED since {since}: the key fingerprint below is not the one first recorded on {since}. "
                "Compare it with the fingerprint you wrote down away from the PC.")
    return _LINES.get(kind, "Unrecognised alert: run the check by hand.")


def _footer(summary) -> str:
    ok = _valid_summary(summary)
    fp = summary["fingerprint"] if ok else ""
    shown = fp if _FINGERPRINT.fullmatch(fp) else "none recorded yet" if ok and fp == "" else "unknown"
    return "\n".join((f"Owner log head: entry #{summary['head_seq'] if ok else '?'}",
                      f"Key fingerprint: {shown}",
                      "Check by hand: .venv/Scripts/python.exe -m core.compliance.rules --check",
                      f"Sent only to {OWNER_ALERT_EMAIL}."))


def render(alert: dict, summary: dict) -> tuple[str, str]:
    """(subject, body) from the fixed template (spec 5.4): row id, field, date and days left, the owner-log head as
    "entry #seq" and the key fingerprint. Only ids, dates and integers are interpolated, each re-validated."""
    return _subject(alert), _line(alert) + "\n\n" + _footer(summary)


def _toast(title: str, body: str) -> bool:
    """P26 seam: one Windows toast through powershell.exe (WinRT ToastNotificationManager); True when shown. The
    text travels in environment variables, never inside the script. Tests patch this and never run PowerShell."""
    env = {**os.environ, "TRADEGEN_TOAST_TITLE": title, "TRADEGEN_TOAST_BODY": body}
    try:
        done = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _TOAST_PS], env=env,
                              capture_output=True, timeout=60,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _in_log(seq: int, sha: str) -> bool:
    """True when owner.jsonl line `seq` records row_sha256 `sha`; seq 0 anchors nothing. An alerts.jsonl anchor
    the log does not have leaves it BROKEN for good (Task 11), so log() writes only anchors that hold."""
    from core.compliance import owner
    if seq == 0:
        return True
    lines = owner._log_lines(owner.log_path())
    try:
        return len(lines) >= seq and json.loads(lines[seq - 1]).get("row_sha256") == sha
    except (ValueError, RecursionError, AttributeError):
        return False


def log(channel: str, result: str, summary: dict, now: datetime) -> None:
    """Append one alerts.jsonl row, canonical JSON {utc, channel, result, code, due, overdue, head_seq,
    head_sha256, fingerprint}. Its head is an owner-log anchor (spec 6.4) and the first fingerprint recorded is the
    one the key is held to (P20). ValueError before anything is written for an unknown channel or result, a
    malformed summary, a naive `now`, or a head that is not that line of owner.jsonl (append-only, so the check
    holds under the lock too). The append takes the owner-log sidecar lock: a torn line would be BROKEN for good."""
    from core.compliance import owner
    if channel not in _CHANNELS or result not in _RESULTS:
        raise ValueError(f"log: channel must be one of {_CHANNELS} and result one of {_RESULTS}")
    if not _valid_summary(summary):
        raise ValueError("log: not a --check summary")
    row = {"utc": model.iso_utc(now), "channel": channel, "result": result,
           **{k: summary[k] for k in rules._SUMMARY_KEYS}}
    if not _in_log(summary["head_seq"], summary["head_sha256"]):
        raise ValueError(f"log: owner log entry #{summary['head_seq']} does not have that row_sha256")
    path = owner.alerts_path()
    with owner._exclusive(owner.log_path()), \
            open(checked_target(path, "alerts log", within=owner.home()), "ab") as fh:
        fh.write(model.canonical_json(row).encode("utf-8") + b"\n")
        fh.flush()
        os.fsync(fh.fileno())


def _history() -> list[dict]:
    """alerts.jsonl rows, oldest first; a line that does not parse is skipped here (it carries no authority)."""
    from core.compliance import owner
    path = owner.alerts_path()
    if not path.is_file():
        return []
    rows = []
    for line in path.read_bytes().splitlines():
        try:
            row = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _parse_summary(text: str | None, code: int | None) -> dict | None:
    """The --check JSON line, or None when it is missing, unreadable, malformed or disagrees with `code`."""
    if not text or not text.strip():
        return None
    try:
        summary = json.loads(text)
    except (ValueError, RecursionError):            # RecursionError: a deeply nested line
        return None
    if not _valid_summary(summary) or (code is not None and summary["code"] != code):
        return None
    return summary


def main(argv=None) -> int:
    """`python -m core.compliance.alerts [--today D] --summary JSON [--code N]` prints one JSON line {"send",
    "subject", "body"}; when send is true it also shows the toast and logs channel "toast". `--log CHANNEL ok|fail
    --summary JSON` appends the row for a channel the daily task used. --code is --check's exit code; a missing,
    unreadable or mismatched summary is itself an alert. A toast that failed, or a failed alerts.jsonl write, is
    told in the printed body (spec 5.4: a failed channel is announced on the others); the write failure also exits
    1. Exit 0 done, 1 refused or not recorded."""
    import argparse
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    now = datetime.now(timezone.utc)
    try:
        parser = argparse.ArgumentParser(prog="python -m core.compliance.alerts", exit_on_error=False)
        parser.add_argument("--today", help="an Asia/Seoul date, YYYY-MM-DD (default: today)")
        parser.add_argument("--summary", help="the JSON line --check printed last")
        parser.add_argument("--code", type=int, help="the exit code of --check")
        parser.add_argument("--log", nargs=2, metavar=("CHANNEL", "RESULT"), help="record one channel's result")
        args = parser.parse_args(argv)
        summary = _parse_summary(args.summary, args.code)
        if args.log:
            log(args.log[0], args.log[1], summary or _MISSING, now)
            print(json.dumps({"logged": args.log[0], "result": args.log[1]}, ensure_ascii=True))
            return 0
        today = (rules.parse_date(args.today, "--today") if args.today is not None
                 else now.astimezone(model.KST).date())
        alerts = due(summary, _history(), today)
        if not alerts:
            print(json.dumps({"send": False, "subject": "", "body": ""}, ensure_ascii=True))
            return 0
        subject = render(alerts[0], summary)[0] + (f" (+{len(alerts) - 1} more)" if len(alerts) > 1 else "")
        lines = [_line(a) for a in alerts]
        shown = _toast(subject, "\n".join(lines) + "\n\n" + _footer(summary))
        code = 0
        if not shown:
            lines.append("The Windows toast could not be shown.")
        try:
            log("toast", "ok" if shown else "fail", summary or _MISSING, now)
        except Exception as exc:                    # the alert still goes out; the job sees exit 1
            lines.append(f"Recording this alert in alerts.jsonl failed ({type(exc).__name__}); run the check by "
                         "hand.")
            print(f"log failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            code = 1
        body = "\n".join(lines) + "\n\n" + _footer(summary)
        print(json.dumps({"send": True, "subject": subject, "body": body}, ensure_ascii=True))
        return code
    except BaseException as exc:                    # argparse errors and SystemExit included: never a traceback
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
