"""One normalised, hashed record per venue per poll (E1 spec 6 "Snapshot"; plan E4, E16, E30, E37), the daily
inquiry files, and the sidecar lock and JSONL helpers every E1 state file uses (spec 4 "State files").

Paths are computed at call time under `core.isolation.state_root()/"execution"`, so a test's TRADEGEN_HOME moves
them; computing one creates nothing. Every write goes through `checked_target` just before it opens, the lock file
included. No clock, no key and no network: the poller passes the time in."""
from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import threading
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from core.compliance import model
from core.isolation import checked_target, state_root

VENUES = ("kis", "upbit", "okx")
STALE_AFTER = timedelta(minutes=15)                 # an older snapshot gives no live positions (spec 6, E17)
FLAGS = frozenset({"keys_missing", "code_unsigned", "auth_error", "okx_perm", "okx_acct_lv", "okx_spot_borrow",
                   "okx_auto_loan", "okx_no_ip", "EVENTS", "derivative_position"})   # code_unsigned: KIS only, E42


class FieldError(ValueError):
    """A response field is missing or malformed. args[0] is the field's name, a literal of the parser; never its
    value (E37)."""


@dataclass(frozen=True, kw_only=True)
class Holding:
    units: float                          # total held, locked included
    locked: float = 0.0
    avg_cost: float | None = None         # in the venue's quote currency, where the venue gives one


@dataclass(frozen=True, kw_only=True)
class Order:
    id: str
    symbol: str
    side: str                             # "buy" | "sell"
    units: float
    price: float | None = None


@dataclass(frozen=True, kw_only=True)
class Move:
    """A fill, a deposit or a withdrawal."""
    id: str
    symbol: str
    counter: str = ""
    side: str                             # "buy" | "sell" | "in" | "out"
    units: float


@dataclass(frozen=True, kw_only=True)
class Address:
    currency: str
    net_type: str
    address: str
    secondary_address: str = ""


@dataclass(frozen=True, kw_only=True)
class Snapshot:
    """One venue at one poll (spec 6). `flags` is made a frozenset; snapshot_sha256 is always derived from every
    other field. A venue outside VENUES, a flag outside FLAGS or a number that is not finite is ValueError."""
    venue: str
    utc: str                              # the poll's now, model.iso_utc
    server_utc: str | None = None         # the venue's time (first Date header; OKX public/time), model.iso_utc
    clock_offset_s: float | None = None   # venue time minus the PC clock at receipt of that answer (E39)
    ok: bool
    error: str | None = None              # names, paths and codes only (E37)
    holdings: Mapping[str, Holding] = field(default_factory=dict)
    cash: Mapping[str, float] = field(default_factory=dict)          # fiat currency -> settled amount (E16)
    deposit_krw: float | None = None      # KIS dnca_tot_amt (D16 evidence); None elsewhere
    open_orders: tuple[Order, ...] = ()
    fills: tuple[Move, ...] = ()          # the venue's recent window (E16)
    deposits: tuple[Move, ...] = ()
    withdrawals: tuple[Move, ...] = ()
    withdrawal_addresses: tuple[Address, ...] = ()   # Upbit only
    key_expiry: str | None = None         # Upbit: earliest expire_at, model.iso_utc
    loans: Mapping[str, float] = field(default_factory=dict)         # name -> amount (E26)
    earn: Mapping[str, float] = field(default_factory=dict)          # OKX: name -> amount (E26)
    flags: frozenset = frozenset()        # subset of FLAGS
    prices_krw: Mapping[str, float] = field(default_factory=dict)    # symbol or currency -> KRW price used
    response_sha256: Mapping[str, str] = field(default_factory=dict) # path -> sha256 of the body; the OKX algo
                                          # calls use f"{path}?ordType={t}"; never a KIS query (E37)
    snapshot_sha256: str = ""             # set by __post_init__

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", frozenset(self.flags))     # a list or set hashes as the frozenset would
        if self.venue not in VENUES:
            raise ValueError("snapshot: venue is not kis, upbit or okx")
        if not self.flags <= FLAGS:
            raise ValueError("snapshot: a flag outside FLAGS")
        body = {k: v for k, v in model.jsonable(self).items() if k != "snapshot_sha256"}
        object.__setattr__(self, "snapshot_sha256", model.sha256_hex(model.canonical_json(body)))


_FIELDS = frozenset(f.name for f in dataclasses.fields(Snapshot))


def home() -> Path:
    """`<state root>/execution`, resolved at call time. Computing it creates nothing."""
    return state_root() / "execution"


def inquiry_path(day: date) -> Path:
    """The inquiry file of one Asia/Seoul date (E30): `inquiry-YYYYMMDD.jsonl`. Computing it creates nothing."""
    return home() / f"inquiry-{day:%Y%m%d}.jsonl"


def failed(venue: str, utc: str, error: str, *, flags=frozenset(), server_utc=None, clock_offset_s=None) -> Snapshot:
    """A not-ok snapshot: no holdings, cash or lists, only the error text (names, paths and codes, E37)."""
    return Snapshot(venue=venue, utc=utc, server_utc=server_utc, clock_offset_s=clock_offset_s, ok=False,
                    error=error, flags=flags)


def dump(snap: Snapshot) -> bytes:
    """One inquiry line: the canonical JSON of every field (keys sorted) plus a newline, UTF-8."""
    return (model.canonical_json(snap) + "\n").encode("utf-8")


def load(obj: dict) -> Snapshot:
    """The Snapshot a dump() line holds, nested records rebuilt. ValueError unless `obj` has exactly the snapshot
    fields, every record rebuilds, snapshot_sha256 recomputes (a tampered row) and `obj` is the row dump() writes for
    that Snapshot (a look-alike container is refused); the text names no value."""
    if not isinstance(obj, dict) or set(obj) != _FIELDS:
        raise ValueError("snapshot row: not the snapshot fields")
    try:
        snap = Snapshot(
            venue=obj["venue"], utc=obj["utc"], server_utc=obj["server_utc"], clock_offset_s=obj["clock_offset_s"],
            ok=obj["ok"], error=obj["error"],
            holdings={k: Holding(**v) for k, v in obj["holdings"].items()},
            cash=dict(obj["cash"]), deposit_krw=obj["deposit_krw"],
            open_orders=tuple(Order(**o) for o in obj["open_orders"]),
            fills=tuple(Move(**m) for m in obj["fills"]),
            deposits=tuple(Move(**m) for m in obj["deposits"]),
            withdrawals=tuple(Move(**m) for m in obj["withdrawals"]),
            withdrawal_addresses=tuple(Address(**a) for a in obj["withdrawal_addresses"]),
            key_expiry=obj["key_expiry"], loans=dict(obj["loans"]), earn=dict(obj["earn"]),
            flags=obj["flags"], prices_krw=dict(obj["prices_krw"]),
            response_sha256=dict(obj["response_sha256"]))
        same = json.loads(dump(snap)) == obj            # dict() and tuple() above also take "", [] or pairs
    except (TypeError, ValueError, AttributeError, RecursionError) as exc:   # json nests deeper than jsonable recurses
        raise ValueError(f"snapshot row: {type(exc).__name__}") from None
    if snap.snapshot_sha256 != obj["snapshot_sha256"]:
        raise ValueError("snapshot row: snapshot_sha256 does not recompute")
    if not same:
        raise ValueError("snapshot row: not canonical")
    return snap


# ponytail: one process-wide lock for every path, as owner._exclusive; nesting two exclusive() calls in one thread
# deadlocks (no caller nests them: poll.py takes poll.lock with its own code). Per-path locks if one ever must.
_LOCK = threading.Lock()


@contextlib.contextmanager
def exclusive(path: Path) -> Iterator[None]:
    """Serialise read-and-append on `path` across threads and processes: a sidecar `<path>.lock` holding an OS byte
    lock (a copy of core.compliance.owner._exclusive, which is private). Creates the folder and the lock file only."""
    checked_target(path.parent, "E1 state folder").mkdir(parents=True, exist_ok=True)
    with _LOCK, open(checked_target(str(path) + ".lock", "E1 lock file"), "a+b") as fh:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)       # retries for about 10 s, then raises
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def write_lines(path: Path, lines: Sequence[bytes], what: str) -> None:
    """Append whole lines (each ending in a newline) to `path` with fsync; the caller holds exclusive(path) or, for
    the daily inquiry files, exclusive(home() / "inquiry"). A torn last line left by a crash stays isolated: a
    newline goes first when the file does not end in one. No lines: no file is opened or created."""
    if not lines:
        return
    with open(checked_target(path, what), "a+b") as fh:     # a+ reads the last byte; every write still appends
        end = fh.seek(0, os.SEEK_END)
        if end:
            fh.seek(end - 1)
            if fh.read(1) != b"\n":
                fh.write(b"\n")
        fh.write(b"".join(lines))
        fh.flush()
        os.fsync(fh.fileno())


def append_lines(path: Path, lines: Sequence[bytes], what: str) -> None:
    """write_lines under exclusive(path)."""
    with exclusive(path):
        write_lines(path, lines, what)


def read_all(path: Path) -> list[dict]:
    """Every JSON-object line of `path` in file order; a line that does not parse as one (a torn line, a foreign
    line, one nested too deep) is skipped; a missing file is []. Takes no lock and creates nothing."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return []
    rows = []
    for line in raw.split(b"\n"):
        try:
            obj = json.loads(line.decode("utf-8"))
        except (ValueError, RecursionError):            # UnicodeDecodeError and JSONDecodeError are ValueErrors
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows
