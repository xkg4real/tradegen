"""Read-only loss-floor state check: step 0 of the principal loss budget design (spec 2026-11-11, section 9.1).

    python -m tools.floor_state_check --state-root ROOT --head-root HEAD_ROOT
        --principal W0 --floor C --activation A
        [--candidate STATE.json --candidate-head HASH] [--session SESSION_ID] [--gate]

Run it from the repository root with the project's own Python. It reads the owner log, the control journal and the
reviewed account baseline of the home that TRADEGEN_HOME selects. It creates and writes nothing, and it prints fixed
codes and relations only: never an amount, a path, a digest or a session id.

--state-root does not select a home; it must equal the configured one. --floor is the budget floor C = W0 - LB.
With --candidate, rows S4, S7, S10 and S11 read that anchor file instead of the stored baseline.

Rows (the go values are in the design, section 9.1):
  S1   owner log verifies                    yes | empty | no
  S2   halt in the owner log                 none | present
  S3   halt in the control journal           none | present | no_journal
  S4   highest recorded peak against A       none | below | at_or_above
  S5   last journaled floor against C        none | above | equal | below
  S6   signed floor in force against C       unset | above | equal | below
  S7   anchor floor against C                none | null | above | equal | below
  S8   armed sessions                        none | present
  S9   home; control journal folder          default | custom; absent | present
  S10  anchor equity against W0              none | above | equal | below
  S11  anchor equity against highest floor   none | at_or_above | below
  S12  signed floor inside --session         not_requested | not_armed | unset | above | equal | below
Any row can also read "unreadable".

Exit 0: every row was read, and with --gate the go table holds. Exit 1: --gate and some row is not go.
Exit 2: an argument was refused, or some state could not be read.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

from core.compliance import model, owner
from core.isolation import state_root
from execution_accounts.baseline import restore_state
from execution_accounts.baseline_store import CheckpointStore
from execution_control.store import Journal
from execution_launch.baseline_head import BaselineHead, BaselineHeadError, CheckpointChain
from execution_launch.workflow import MAX_CONFIG_BYTES, read_file

UNREADABLE = "unreadable"
_BAD = object()                                    # a state that could not be read; never printed
_OPTIONS = ("state-root", "head-root", "principal", "floor", "activation", "candidate", "candidate-head", "session")
_AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?")
_HASH = re.compile(r"[0-9a-f]{64}")
_LABELS = {"S1": "owner log verifies", "S2": "halt in the owner log", "S3": "halt in the control journal",
           "S4": "highest recorded peak against A", "S5": "last journaled floor against C",
           "S6": "signed floor in force against C", "S7": "anchor floor against C", "S8": "armed sessions",
           "S9_home": "home", "S9_journal": "control journal folder", "S10": "anchor equity against W0",
           "S11": "anchor equity against highest floor", "S12": "signed floor inside --session"}
_GO = {"S1": ("yes",), "S2": ("none",), "S3": ("none", "no_journal"), "S4": ("none", "below"), "S6": ("equal",),
       "S7": ("equal",), "S10": ("equal", "below"), "S11": ("at_or_above",)}


class Refused(ValueError):
    """A fixed UPPER_SNAKE code: never an amount, a path or a digest."""


def _default_home() -> Path:
    return Path.home() / ".tradegen"


def _relation(value: Decimal, target: Decimal) -> str:
    return "above" if value > target else "below" if value < target else "equal"


def _arguments(argv) -> tuple[dict, bool]:
    args, gate, tokens = {}, False, list(argv)
    while tokens:
        token = tokens.pop(0)
        if token == "--gate" and not gate:
            gate = True
            continue
        key = token[2:] if token.startswith("--") else ""
        if key not in _OPTIONS or key in args or not tokens or not tokens[0] or tokens[0].startswith("--"):
            raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
        args[key] = tokens.pop(0)
    amounts = [args.get(key, "") for key in ("floor", "principal", "activation")]
    if ("state-root" not in args or "head-root" not in args or ("candidate" in args) != ("candidate-head" in args)
            or not all(_AMOUNT.fullmatch(text) for text in amounts)
            or not _HASH.fullmatch(args.get("candidate-head", "0" * 64))):
        raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
    floor, principal, activation = (Decimal(text) for text in amounts)
    if not 0 < floor < principal <= activation:
        raise Refused("STATE_CHECK_ARGUMENTS_INVALID")
    return args | {"floor": floor, "principal": principal, "activation": activation}, gate


def _home(explicit: str) -> Path:
    """The configured home. --state-root only confirms it (the rule of tools/owner/launch.py:111-115)."""
    try:
        actual = state_root().absolute()
    except (RuntimeError, OSError):                # the message names paths: never print it
        raise Refused("STATE_CHECK_STATE_ROOT_REFUSED") from None
    if not Path(explicit).is_absolute() or Path(explicit) != actual:
        raise Refused("STATE_CHECK_STATE_ROOT_MISMATCH")
    return actual


def _signed(state, floor: Decimal) -> str:
    value = state.limits.get("total_loss_floor_krw")
    return "unset" if value is None else _relation(Decimal(str(value)), floor)


def _owner_rows(now: datetime, floor: Decimal, session: str | None):
    """Rows S1, S2, S6, S8 and S12, then the signed floor in force (None when unset, _BAD when unreadable)."""
    day, stamp = now.astimezone(model.KST).date(), model.iso_utc(now)
    state, check = owner._owner_now(day, stamp, None)          # the read-only half of load_context (owner.py:947)
    if not state.ok:
        return dict(S1="no", S2=UNREADABLE, S6=UNREADABLE, S8=UNREADABLE,
                    S12=UNREADABLE if session else "not_requested"), _BAD
    rows = dict(S1="yes" if check.entries else "empty", S2="present" if state.halted_floors else "none",
                S6="unset" if "daily_loss_krw" not in state.limits else _signed(state, floor),
                S8="present" if state.armed_sessions else "none", S12="not_requested")
    if session:
        inside = owner._owner_now(day, stamp, session)[0]
        rows["S12"] = (UNREADABLE if not inside.ok else "not_armed" if session not in inside.armed_sessions
                       else _signed(inside, floor))
    value = state.limits.get("total_loss_floor_krw")
    return rows, None if value is None else Decimal(str(value))


def _stored(text) -> Decimal:
    value = Decimal(text) if type(text) is str else None
    if value is None or not value.is_finite() or value < 0:
        raise ValueError("journal amount")
    return value


def _journal_rows(home: Path, floor: Decimal):
    """Rows S3, S5 and the journal half of S9, then the journaled peak and the last journaled floor."""
    if not (home / "execution-control").exists():              # the journal's own folder (store.py:152)
        return dict(S3="no_journal", S5="none", S9_journal="absent"), None, None
    try:
        rows = Journal().snapshot()                            # creates nothing (store.py:232-253)
        risk = [row["data"] for row in rows if row["kind"] == "risk_snapshot"]
        peaks = [_stored(data["high_watermark"]) for data in risk]
        floors = [_stored(data["effective_floor"]) for data in risk if data["effective_floor"] is not None]
        halted = any(row["kind"] == "halt" for row in rows)
    except (RuntimeError, LookupError, TypeError, ValueError, ArithmeticError):
        return dict(S3=UNREADABLE, S5=UNREADABLE, S9_journal="present"), _BAD, _BAD
    last = floors[-1] if floors else None                      # the most recent, as controller.py:391-392 reads it
    return (dict(S3="present" if halted else "none", S5="none" if last is None else _relation(last, floor),
                 S9_journal="present"), max(peaks, default=None), last)


def _anchor(home: Path, head_root: str, candidate: str | None, candidate_head: str | None):
    """The candidate or the stored baseline state; None when neither a checkpoint nor a head exists; _BAD when
    it cannot be read. Every refusal of these readers is a fixed-code ValueError."""
    try:
        if candidate is not None:                              # the read setup-account makes (launch.py:141)
            return restore_state(read_file(candidate, MAX_CONFIG_BYTES), expected_head=candidate_head)
        store = CheckpointStore(root=home)
        head = BaselineHead(root=Path(head_root), name="account-baseline", chain=CheckpointChain(store))
        try:
            expected = head.read()
        except BaselineHeadError as exc:
            if str(exc) == "HEAD_NOT_INITIALIZED" and not (home / store._DIRECTORY / "checkpoint.json").exists():
                return None
            raise
        return store.load(expected_head=expected)
    except (ValueError, OSError, RuntimeError):
        return _BAD


def check(*, home: Path, head_root: str, principal: Decimal, floor: Decimal, activation: Decimal,
          candidate: str | None = None, candidate_head: str | None = None, session: str | None = None,
          now: datetime) -> dict[str, str]:
    """Every row by key. Reads only."""
    rows, signed = _owner_rows(now, floor, session)
    journal, peak, last = _journal_rows(home, floor)
    anchor = _anchor(home, head_root, candidate, candidate_head)
    rows |= journal
    rows["S9_home"] = "default" if home.is_relative_to(_default_home()) else "custom"
    peaks = [peak]
    if anchor is None:
        rows |= dict(S7="none", S10="none", S11="none")
    elif anchor is _BAD:
        rows |= dict(S7=UNREADABLE, S10=UNREADABLE, S11=UNREADABLE)
        peaks.append(_BAD)
    else:
        own = anchor.approved_effective_floor
        floors = [value for value in (own, last, signed) if value is not None]
        rows["S7"] = "null" if own is None else _relation(own, floor)
        rows["S10"] = _relation(anchor.equity_krw, principal)
        rows["S11"] = (UNREADABLE if any(value is _BAD for value in floors) else
                       "below" if floors and anchor.equity_krw < max(floors) else "at_or_above")
        peaks.append(anchor.high_watermark)
    peaks = [value for value in peaks if value is not None]
    rows["S4"] = (UNREADABLE if any(value is _BAD for value in peaks) else "none" if not peaks else
                  "below" if max(peaks) < activation else "at_or_above")
    return rows


def main(argv=None, *, now: datetime | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if tuple(argv) in ((), ("--help",), ("-h",)):
        print(__doc__)
        return 0
    try:
        args, gate = _arguments(argv)
        rows = check(home=_home(args["state-root"]), head_root=args["head-root"], principal=args["principal"],
                     floor=args["floor"], activation=args["activation"], candidate=args.get("candidate"),
                     candidate_head=args.get("candidate-head"), session=args.get("session"),
                     now=now or datetime.now(timezone.utc))
    except Refused as exc:
        print(json.dumps({"refused": str(exc)}))
        return 2
    except Exception:                              # no message is printed: it could name a path or an amount
        print(json.dumps({"refused": "STATE_CHECK_FAILED"}))
        return 2
    for key, label in _LABELS.items():
        print(f"{key:<11}{label:<38}{rows[key]}")
    verdict = "not_requested" if not gate else "go" if all(rows[key] in go for key, go in _GO.items()) else "no_go"
    print(json.dumps({"gate": verdict, "rows": rows}, sort_keys=True))
    return 2 if UNREADABLE in rows.values() else 1 if verdict == "no_go" else 0


if __name__ == "__main__":
    raise SystemExit(main())
