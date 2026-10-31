r"""TRADEGEN owner signer (spec 6.4, D14). You keep this one file outside the repo and run it only in your own
Windows Terminal. It uses the standard library and `cryptography`, never imports the TRADEGEN repo, and refuses to
run under Claude, under a claude.exe parent process, when its parent chain stops before a Windows session process,
without a terminal on stdin, or without python.exe -I.

Owner act 1, once: set up the signer
  1. Copy tools\signer\sign.py from the repo to %USERPROFILE%\tradegen-signer\sign.py. Read all of it.
  2. In your own terminal run
       certutil -hashfile %USERPROFILE%\tradegen-signer\sign.py SHA256
     and write the hash on paper, away from the PC.
  3. Run
       C:\Users\whydi\OneDrive\Desktop\TRADEGEN\.venv\Scripts\python.exe -I %USERPROFILE%\tradegen-signer\sign.py keygen
     Choose a passphrase of at least 20 characters (blanks do not count), or at least 5 different words of 3 or
     more letters each (a changed capital does not make a word different).
     Write the fingerprint it prints on the same paper.
  4. Copy the .pem file it names to C:\Users\whydi\OneDrive\Desktop\TRADEGEN\core\compliance\owner_pubkey.pem.

Owner act 2, after you have reviewed every diff of the files it lists: sign the code hash (one command line)
  C:\Users\whydi\OneDrive\Desktop\TRADEGEN\.venv\Scripts\python.exe -I %USERPROFILE%\tradegen-signer\sign.py
      code-approve --repo C:\Users\whydi\OneDrive\Desktop\TRADEGEN
  Run it again whenever --check reports "code: UNSIGNED" and you have reviewed the change.

Every time, before you type the passphrase
  - open Windows Terminal yourself from the Start menu (an editor's terminal can be refused: its parent chain may
    stop at a launcher that has exited);
  - start it with python.exe -I, as above. -I keeps the folder of sign.py, the current folder and PYTHON*
    variables off the import path, so no .py file placed next to sign.py runs while you type;
  - run the certutil line again and compare it with the paper; on any difference stop and type nothing;
  - run  dir C:\Users\whydi\OneDrive\Desktop\TRADEGEN\.venv\Lib\site-packages\*.pth  and stop on any file but
    distutils-precedence.pth. Honest limit: -I does not cover the venv's site-packages. Its .pth files and the
    cryptography package run inside this process and could read the passphrase, and this check sees only the
    .pth names;
  - read what the screen says will be signed (entry number, UTC stamp, data), then type the code it shows (type it;
    a paste is refused).

Other commands
  approve --kind rules|instruments|venues|calendar --path P   owner acts 3 and 4 (calendar: the data folder)
  event KIND --data JSON    owner acts 5 and 6: cap_set, limit_set, age_of_majority, withdrawal_address,
                            course_completed, broker_approval, session_armed, session_ack, transfer_ack, key_rotated.
                            cap_set and limit_set: a tighter value applies at once; a looser one, including the
                            first one you set, applies only from the next Asia/Seoul date, never inside a session
                            armed on or before the day you set it, and never after a system_halt
  fingerprint               print the key file's fingerprint (no passphrase needed)

Key rotation, only when the key must change (the old key signs the change, the log stays one chain)
  1. keygen --key NEW\owner_key.enc      writes the new key file and NEW\owner_key.pem and prints the new raw public key
                                         and its fingerprint: write the new fingerprint on paper, away from the PC
  2. fingerprint                         prints the raw public key of the key file you use now (the old one)
  3. event key_rotated --data JSON       {"old_pubkey_b64": OLD, "new_pubkey_b64": NEW}, unlocking the OLD key file
  4. copy NEW\owner_key.pem over <repo>\core\compliance\owner_pubkey.pem, right after step 3. The owner log reads
     BROKEN between steps 3 and 4 (the repo key is still the old one), so until the copy, --check exits 3, new
     exposure is blocked and withdrawals are manual.
  5. from then on pass --key NEW\owner_key.enc to every command. The signer refuses any key that is not the one in
     force (the old one until step 3, the new one after it), because a line signed by another key breaks the log
     for good.

Claude never runs this file, never asks for your passphrase and never writes owner entries."""
from __future__ import annotations

import argparse
import ast
import base64
import binascii
import getpass
import hashlib
import json
import math
import os
import re
import secrets
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

KEY_FORMAT = "tradegen-owner-key/1"
SIG_DOMAIN = b"tradegen-owner-log/1\n"
GENESIS_PREV = "0" * 64
KDF_N, KDF_R, KDF_P = 2 ** 17, 8, 1
APPROVAL_KINDS = ("rules", "instruments", "venues", "calendar")
FILE_KINDS = ("rules", "instruments", "venues")
QUANTGEN_STATE = Path.home() / ".nextgen"                              # copies of core/isolation.py's two roots
QUANTGEN_REPO = Path.home() / "OneDrive" / "Desktop" / "QUANTGEN"
TYPED_MIN_GAP_S = 0.030                                                 # P27: the average gap between keystrokes
TYPED_BURST_S = 0.010                                                   # three gaps in a row below this: a paste
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
# Copies of core.compliance.rules vocabularies the owner log checks; a test keeps them equal to the repo's.
VENUES = frozenset({"kis", "upbit", "bithumb", "coinone", "korbit", "gopax", "okx", "binance", "bybit", "bitget",
    "hyperliquid", "pumpfun", "jupiter", "uniswap", "drift", "polymarket", "kalshi", "limitless", "myriad", "opinion",
    "predictfun", "robinhood", "cryptocom", "predictit", "sportsbook", "betman", "lotto", "speedon", "ibkr", "moomoo",
    "webull", "etoro", "offshore_fx_cfd", "kucoin", "mexc", "phemex", "xtcom", "bitrue", "coinw", "poloniex", "btcc",
    "bingx", "digifinex", "bitmart"})
OWNER_REQUIREMENTS = frozenset({"age_of_majority", "kofia_leveraged_1h", "kofia_single_stock_3h",
    "krx_mock_5h_5days", "kofia_derivatives_1h", "krx_derivatives_mock_3h", "elw_course", "us_option_course_1h",
    "us_option_mock_3h", "short_course_30m", "short_mock_1h", "broker_eligibility"})
_ITEMS = OWNER_REQUIREMENTS - {"age_of_majority"}      # that flag comes only from a birth date
_HEX64 = re.compile(r"[0-9a-f]{64}")
# ASCII digits only, as owner.py: `\d` also takes fullwidth and Arabic-Indic digits, and strptime reads some of them.
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_BODY_KEYS = ("seq", "prev_sha256", "utc", "kind", "data")
_LINE_KEYS = frozenset(_BODY_KEYS) | {"row_sha256"}
_TOKEN = re.compile(r"[!-~]+")                         # printable ASCII without spaces
_HEADER_KEYS = frozenset({"format", "kdf", "nonce_b64", "fingerprint"})
_KDF_KEYS = frozenset({"name", "n", "r", "p", "salt_b64"})


# --------------------------------------------------------------------------- #
# Line format, hashes and fingerprints (copies of core/compliance/model.py and owner.py)
# --------------------------------------------------------------------------- #
def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def fingerprint(pubkey_raw: bytes) -> str:
    return "SHA256:" + sha256_hex(pubkey_raw)


def entry_line(signing_key, seq: int, prev_sha256: str, kind: str, data: dict, utc: str) -> tuple[bytes, str]:
    """(line bytes, row_sha256) of one signed owner entry, byte for byte the owner.py format."""
    body = {"seq": seq, "prev_sha256": prev_sha256, "utc": utc, "kind": kind, "data": data}
    row = sha256_hex(canonical_json(body))
    sig = base64.b64encode(signing_key.sign(SIG_DOMAIN + row.encode("ascii"))).decode("ascii")
    return (canonical_json({**body, "row_sha256": row, "sig": sig}) + "\n").encode("utf-8"), row


# --------------------------------------------------------------------------- #
# Event data: copies of owner.py's checks (a test holds them equal both ways). Signing anything the gate rejects
# breaks the append-only log for good.
# --------------------------------------------------------------------------- #
def _hex64(v) -> bool:
    return isinstance(v, str) and _HEX64.fullmatch(v) is not None


def _text(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _number(v) -> bool:
    """A JSON int or float, not bool, finite as a float; an int too large for a float is refused."""
    try:
        return type(v) in (int, float) and math.isfinite(v)
    except OverflowError:
        return False


def _one_of(options):
    return lambda v: isinstance(v, str) and v in options


def _parses(v, pattern, parse) -> bool:
    if not (isinstance(v, str) and pattern.fullmatch(v)):
        return False
    try:
        parse(v)
    except ValueError:
        return False
    return True


def _iso_date(v) -> bool:
    return _parses(v, _ISO_DATE, date.fromisoformat)


def _utc(v) -> bool:
    return _parses(v, _UTC, lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def _b64_of(n: int):
    """Standard base64 with canonical padding of exactly `n` bytes."""
    def check(v) -> bool:
        if not isinstance(v, str):
            return False
        try:
            raw = base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            return False
        return len(raw) == n and base64.b64encode(raw).decode("ascii") == v
    return check


def _files(v) -> bool:
    """[[relpath, sha256], ...], non-empty, sorted by path with no repeat (the order of code_files)."""
    if not (isinstance(v, list) and v and all(isinstance(f, list) and len(f) == 2 and _text(f[0]) and _hex64(f[1])
                                              for f in v)):
        return False
    paths = [f[0] for f in v]
    return paths == sorted(set(paths))


SCHEMAS = {
    "approved": {"kind": _one_of(APPROVAL_KINDS), "sha256": _hex64},
    "code_approved": {"sha256": _hex64, "files": _files},
    "course_completed": {"course": _one_of(_ITEMS), "evidence": _text},
    "broker_approval": {"item": _one_of(_ITEMS), "evidence": _text},
    "age_of_majority": {"birth_date": _iso_date, "evidence": _text},
    "cap_set": {"key": _one_of(("okx_equity_share",)), "value": lambda v: _number(v) and 0 < v <= 1},
    "limit_set": {"total_loss_floor_krw": lambda v: _number(v) and v >= 0,
                  "daily_loss_krw": lambda v: _number(v) and v > 0},
    "withdrawal_address": {"venue": _one_of(VENUES), "symbol": _text, "network": _text, "address": _text,
                           "tag": lambda v: v is None or _text(v), "evidence": _text},
    "session_armed": {"session_id": _text},
    "session_ack": {"session_id": _text, "row_id": _text, "warning_sha256": _hex64},
    "transfer_ack": {"intent_hash": _hex64, "warning_sha256": _hex64},
    "key_rotated": {"old_pubkey_b64": _b64_of(32), "new_pubkey_b64": _b64_of(32)},   # P20: signed by the old key
}
SYSTEM_SCHEMAS = {                                     # never signed here; _head checks them in the log
    "system_halt": {"floor_krw": lambda v: _number(v) and v >= 0},
    "system_disarm": {"session_id": _text, "reason": _text},
}
_DATA = {**SCHEMAS, **SYSTEM_SCHEMAS}


def _data_problem(kind: str, data) -> str:
    """owner._data_problem: "" when `data` has exactly the keys of `kind` with valid values, else what is wrong."""
    schema = _DATA[kind]
    if not isinstance(data, dict):
        return "is not an object"
    if set(data) != set(schema):
        return f"keys {sorted(map(str, data))} are not {sorted(schema)}"
    bad = sorted(k for k, ok in schema.items() if not ok(data[k]))
    if bad:
        return f"has invalid {', '.join(bad)}"
    if kind == "code_approved" and data["sha256"] != sha256_hex(canonical_json(data["files"])):
        return "sha256 is not the hash of its files"
    return ""


def check_data(kind: str, data) -> None:
    """ValueError unless `data` is a valid owner entry of `kind` for owner.py, and passes the signer's own stricter
    rule: a withdrawal address (symbol, network, address, tag) is printable ASCII without spaces, so the screen
    shows the very characters that are signed."""
    if kind not in SCHEMAS:
        raise ValueError(f"{kind!r} is not an owner entry kind (system entries are never signed)")
    why = _data_problem(kind, data)
    if why:
        raise ValueError(f"{kind}: data {why}")
    if kind == "withdrawal_address":
        bad = [k for k in ("symbol", "network", "address", "tag")
               if data[k] is not None and not _TOKEN.fullmatch(data[k])]
        if bad:
            raise ValueError(f"withdrawal_address: {', '.join(bad)} must be printable ASCII without spaces")


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _parse_line(n: int, line: bytes, prev: str) -> dict:
    """owner._parse_line's checks of line `n`, signatures aside; ValueError naming the first defect."""
    if not isinstance(line, bytes) or not line.endswith(b"\n") or b"\n" in line[:-1] or b"\r" in line:
        raise ValueError("not one newline-terminated line")
    try:
        obj = json.loads(line[:-1].decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"unreadable ({exc})") from None
    if not isinstance(obj, dict):
        raise ValueError("not a JSON object")
    try:
        same = canonical_json(obj).encode("utf-8") == line[:-1]
    except (TypeError, ValueError):
        same = False
    if not same:
        raise ValueError("not its canonical JSON")
    kind = obj.get("kind")
    if not isinstance(kind, str) or kind not in _DATA:
        raise ValueError(f"unknown kind {kind!r}")
    signed = kind in SCHEMAS
    if signed and "sig" not in obj:
        raise ValueError(f"unsigned {kind} entry: only system_halt and system_disarm go unsigned")
    if not signed and "sig" in obj:
        raise ValueError(f"signature on a system entry ({kind})")
    if set(obj) != _LINE_KEYS | ({"sig"} if signed else set()):
        raise ValueError(f"line keys {sorted(obj)}")
    if type(obj["seq"]) is not int or obj["seq"] != n:
        raise ValueError(f"seq {obj['seq']!r}, expected {n}")
    if obj["prev_sha256"] != prev:
        raise ValueError("prev_sha256 does not chain to the line before")
    if not _utc(obj["utc"]):
        raise ValueError(f"utc {obj['utc']!r} is not YYYY-MM-DDTHH:MM:SSZ")
    if obj["row_sha256"] != sha256_hex(canonical_json({k: obj[k] for k in _BODY_KEYS})):
        raise ValueError("row_sha256 does not recompute")
    why = _data_problem(kind, obj["data"])
    if why:
        raise ValueError(f"{kind} data {why}")
    if signed and not _b64_of(64)(obj["sig"]):
        raise ValueError("sig is not base64 of 64 bytes")
    return obj


def _head(lines: list[bytes]) -> tuple[int, str]:
    """(seq, row_sha256) of the last line, or (0, "") for an empty log, after owner._structure's checks (the gate
    checks the signatures). ValueError names the first bad line: nothing is signed on a log the gate calls BROKEN."""
    prev = GENESIS_PREV
    for n, line in enumerate(lines, start=1):
        try:
            prev = _parse_line(n, line, prev)["row_sha256"]
        except (ValueError, ArithmeticError, RecursionError) as exc:      # RecursionError: a deeply nested line
            raise ValueError(f"owner log line {n}: {exc}; nothing was signed") from None
    return (len(lines), prev) if lines else (0, "")


# --------------------------------------------------------------------------- #
# The key file (spec 6.4 "The key file")
# --------------------------------------------------------------------------- #
def passphrase_ok(passphrase: str) -> bool:
    """At least 20 characters once every blank is left out, or at least 5 different words (compared without case)
    of 3 or more letters each (diceware-style: digits, repeated words and a changed capital do not count)."""
    words = passphrase.split()
    return (sum(not c.isspace() for c in passphrase) >= 20
            or (len({w.casefold() for w in words}) >= 5 and all(w.isalpha() and len(w) >= 3 for w in words)))


def _derive(passphrase: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=KDF_N, r=KDF_R, p=KDF_P).derive(passphrase.encode("utf-8"))


def _pub_raw(seed: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()


def seal_key(seed: bytes, passphrase: str) -> bytes:
    """The owner_key.enc bytes: line 1 the canonical JSON header {format, kdf (scrypt n=2**17, r=8, p=1, 16-byte
    salt), nonce_b64 (12 bytes), fingerprint}, line 2 base64 of AES-256-GCM(seed) with the header line as AAD."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(seed) != 32:
        raise ValueError("an Ed25519 seed is 32 bytes")
    salt, nonce = os.urandom(16), os.urandom(12)
    header = canonical_json({"format": KEY_FORMAT,
                             "kdf": {"name": "scrypt", "n": KDF_N, "r": KDF_R, "p": KDF_P,
                                     "salt_b64": base64.b64encode(salt).decode("ascii")},
                             "nonce_b64": base64.b64encode(nonce).decode("ascii"),
                             "fingerprint": fingerprint(_pub_raw(seed))}).encode("utf-8")
    sealed = AESGCM(_derive(passphrase, salt)).encrypt(nonce, seed, header)
    return header + b"\n" + base64.b64encode(sealed) + b"\n"


def _key_header(raw: bytes) -> tuple[bytes, dict, bytes]:
    """(header line, header, sealed seed) of owner_key.enc bytes; ValueError unless it is the spec's format with
    exactly the spec's header keys. Nothing here is authenticated: the header counts only once the passphrase
    opens the file (it is the AAD)."""
    try:
        parts = raw.split(b"\n")
        header = json.loads(parts[0])
        kdf = header["kdf"]
        ok = (len(parts) == 3 and parts[2] == b"" and set(header) == _HEADER_KEYS and set(kdf) == _KDF_KEYS
              and (header["format"], kdf["name"], kdf["n"], kdf["r"], kdf["p"])
              == (KEY_FORMAT, "scrypt", KDF_N, KDF_R, KDF_P))
        sealed = base64.b64decode(parts[1], validate=True)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise ValueError("not a tradegen-owner-key/1 file") from exc
    if not ok:
        raise ValueError("not a tradegen-owner-key/1 file with the spec's header and scrypt parameters")
    return parts[0], header, sealed


def open_key(raw: bytes, passphrase: str) -> bytes:
    """The 32-byte seed from owner_key.enc bytes. ValueError for a wrong passphrase or a changed file (the header
    is the AAD, so editing any byte of it fails too). The scrypt parameters are the constants, never the file's."""
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        header_line, header, sealed = _key_header(raw)
        key = _derive(passphrase, base64.b64decode(header["kdf"]["salt_b64"], validate=True))
        seed = AESGCM(key).decrypt(base64.b64decode(header["nonce_b64"], validate=True), sealed, header_line)
    except (InvalidTag, ValueError, KeyError, TypeError) as exc:
        raise ValueError("wrong passphrase, or the key file was changed") from exc
    if fingerprint(_pub_raw(seed)) != header["fingerprint"]:
        raise ValueError("the key file's fingerprint does not match its key")
    return seed


def _pem_raw(pem: bytes) -> bytes:
    """owner.read_pubkey: the raw 32 bytes of an Ed25519 public key in PEM; ValueError for any other key."""
    from cryptography.exceptions import UnsupportedAlgorithm
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    try:
        key = load_pem_public_key(pem)
    except (ValueError, UnsupportedAlgorithm) as exc:
        raise ValueError(f"not an Ed25519 public key ({exc})") from None
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("not an Ed25519 public key")
    return key.public_bytes_raw()


# --------------------------------------------------------------------------- #
# Paths and writes (copies of core/isolation.py's refusal and of checked_target, `within` included)
# --------------------------------------------------------------------------- #
def _refuse_quantgen(path, what: str = "path") -> Path:
    p = Path(path).resolve()
    for root in (QUANTGEN_STATE, QUANTGEN_REPO):
        if p.is_relative_to(root.resolve()) or (root.exists() and any(
                a.exists() and os.path.samefile(a, root) for a in (p, *p.parents))):
            raise RuntimeError(f"{what} {path} is inside QUANTGEN ({root}); TRADEGEN never writes there")
    return Path(path)


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return "" if value.startswith("<") and value.endswith(">") else value


def state_root() -> Path:
    """TRADEGEN_HOME, else ~/.tradegen; refused inside QUANTGEN."""
    return _refuse_quantgen(_env("TRADEGEN_HOME") or Path.home() / ".tradegen", "TRADEGEN_HOME")


def _home() -> Path:
    return state_root() / "compliance"


def _log_path() -> Path:
    return _home() / "owner.jsonl"


def _store_dir() -> Path:
    return _home() / "approved"


def _checked(path, within=None) -> Path:
    """Refuse QUANTGEN, a symlink, a junction or a hard-linked file as the target, and with `within` a target that
    resolves outside that folder (a linked folder on the way); creates nothing."""
    p = _refuse_quantgen(path, "target")
    if p.is_symlink() or p.is_junction():
        raise RuntimeError(f"{p} is a link; refused")
    if p.exists() and not p.is_dir():
        try:
            links = os.lstat(p).st_nlink
        except FileNotFoundError:                      # removed since exists(): no second name left to change
            links = 1
        if links > 1:
            raise RuntimeError(f"{p} is a hard link; refused")
    if within is not None and not p.resolve().is_relative_to(Path(within).resolve()):
        raise RuntimeError(f"{p} resolves outside {within} (a linked folder); refused")
    return p


def _write_new(path: Path, data: bytes, within) -> bool:
    """Creates `path` holding `data`; False, writing nothing, when it already exists. A copy of owner._write_new:
    the bytes go to a fresh temp file `.<name>.<12 hex>.tmp` (fsync) and os.rename moves it into place, so a crash
    never leaves a torn file under the final name; on Windows the rename refuses an existing target, which keeps
    the file write-once. The folder, the file and the temp file must resolve inside `within` and be no link. The
    temp file sits in the compliance home, or next to `path` when `within` is None (a --key path you chose)."""
    _checked(path.parent, within)
    path.parent.mkdir(parents=True, exist_ok=True)
    _checked(path, within)
    if path.exists():
        return False
    folder = path.parent if within is None else _home()
    tmp = _checked(folder / f".{path.name}.{os.urandom(6).hex()}.tmp", within)
    try:
        with open(tmp, "xb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        # ponytail: a POSIX rename replaces a target that appeared since exists(); use os.link off Windows
        os.rename(tmp, path)
    except FileExistsError:                            # Windows: `path` appeared since the check (write-once)
        tmp.unlink(missing_ok=True)
        return False
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return True


def _write_once(path: Path, data: bytes, within) -> None:
    """_write_new, and an existing file must already hold exactly `data` (the store never changes a stored file)."""
    if not _write_new(path, data, within) and _checked(path, within).read_bytes() != data:
        raise RuntimeError(f"{path} exists with other bytes; the approved store is write-once")


@contextmanager
def _exclusive(path: Path):
    """The owner log's sidecar `<log>.lock` byte lock, shared with owner.append_system_entry."""
    root = state_root()
    _checked(path.parent, root).mkdir(parents=True, exist_ok=True)
    with open(_checked(str(path) + ".lock", root), "a+b") as fh:
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


def _read_lines(path: Path) -> list[bytes]:
    return _checked(path, state_root()).read_bytes().splitlines(keepends=True) if path.exists() else []


# --------------------------------------------------------------------------- #
# The approved store (owner.py layout: <kind>/<sha256>.yaml, calendar/<sha256>/, <kind>/<sha256>.anchor.json)
# --------------------------------------------------------------------------- #
def calendar_files(data_dir: Path) -> list[tuple[str, bytes]]:
    """(name, bytes) of every regular file directly in `data_dir`, sorted by name, each read once; subfolders are
    not part of the set. rules.calendar_stream's rule: the folder itself, or an entry in it, that is a link
    refuses the whole set (ValueError here, Invalid there)."""
    root = Path(data_dir)
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        raise ValueError(f"calendar: {root} is not a plain directory")
    with os.scandir(root) as listing:
        found = sorted(listing, key=lambda e: e.name)
    out = []
    for e in found:
        if e.is_symlink() or e.is_junction():
            raise ValueError(f"calendar: {e.name} is a link")
        if e.is_file(follow_symlinks=False):
            out.append((e.name, Path(e.path).read_bytes()))
    return out


def _frame(files: list[tuple[str, bytes]]) -> bytes:
    """rules.calendar_stream's framing: each file as name + NUL + bytes + NUL."""
    return b"".join(name.encode("utf-8") + b"\0" + data + b"\0" for name, data in files)


def calendar_sha256(data_dir: Path) -> str:
    """P21: sha256 of the framed calendar set, as rules.calendar_sha256."""
    return sha256_hex(_frame(calendar_files(data_dir)))


def _put_blob(kind: str, raw: bytes) -> str:
    if kind not in FILE_KINDS:
        raise ValueError(f"{kind!r} is not one of {FILE_KINDS}")
    sha = sha256_hex(raw)
    _write_once(_store_dir() / kind / f"{sha}.yaml", raw, state_root())
    return sha


def _put_calendar(src_dir: Path, sha: str) -> None:
    files = calendar_files(src_dir)
    if sha256_hex(_frame(files)) != sha:
        raise RuntimeError("the calendar folder changed after it was shown; nothing was signed")
    dest = _store_dir() / "calendar" / sha
    for name, data in files:
        _write_once(dest / name, data, state_root())
    if sorted(p.name for p in dest.iterdir()) != [name for name, _ in files] or calendar_sha256(dest) != sha:
        raise RuntimeError(f"{dest} does not hold exactly the approved calendar set")


def _anchor_ok(anchor) -> None:
    seq, row_sha256 = anchor
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1 or not _hex64(row_sha256):
        raise ValueError("store: the anchor must be (seq >= 1, row_sha256)")


def _put_anchor(kind: str, sha: str, anchor: tuple[int, str]) -> None:
    """<kind>/<sha256>.anchor.json = {"seq", "row_sha256"} of the approval's log line; an existing anchor stays,
    since it already pins an earlier approval of the same bytes (P34)."""
    _anchor_ok(anchor)
    _write_new(_store_dir() / kind / f"{sha}.anchor.json",
               canonical_json({"seq": anchor[0], "row_sha256": anchor[1]}).encode("utf-8"), state_root())


def store_file(kind: str, raw: bytes, anchor: tuple[int, str]) -> str:
    """owner.store_put's layout for a table file: the bytes and their anchor; returns the sha256."""
    if kind not in FILE_KINDS:
        raise ValueError(f"{kind!r} is not one of {FILE_KINDS}")
    if not isinstance(raw, bytes):
        raise TypeError("store: raw must be bytes")
    _anchor_ok(anchor)                                  # before any write, as owner.store_put
    sha = _put_blob(kind, raw)
    _put_anchor(kind, sha, anchor)
    return sha


def store_calendar(src_dir: Path, anchor: tuple[int, str]) -> str:
    """The calendar set as calendar/<sha256>/ plus its anchor; returns the sha256."""
    _anchor_ok(anchor)
    sha = calendar_sha256(src_dir)
    _put_calendar(src_dir, sha)
    _put_anchor("calendar", sha, anchor)
    return sha


# --------------------------------------------------------------------------- #
# The D14 code hash: a copy of owner.code_files (P6). core/compliance, core/odds and execution .py files,
# recursive execution_control/, execution_orders/, execution_accounts/, execution_network/ and execution_launch/ files, every in-repo file they import at any depth
# (function bodies included), every ancestor package __init__.py, and the
# RECORD files of the cryptography and PyYAML installs. An `if` body that never runs at import is skipped (see
# _skipped); every other body is scanned.
# --------------------------------------------------------------------------- #
_RECORD_DISTS = ("cryptography", "PyYAML")


def _binds(tree: ast.AST, name: str) -> int:
    """How many times `name` is bound anywhere in `tree`, at any depth: by an import, an assignment of any kind, a
    def or class, a parameter, an except-as or a match capture (a keyword argument of that name counts too, which
    only makes callers scan more)."""
    count = 0
    for n in ast.walk(tree):
        if isinstance(n, ast.alias):
            bound = n.asname or n.name.split(".")[0]
        elif isinstance(n, ast.Name):
            bound = n.id if not isinstance(n.ctx, ast.Load) else None
        else:
            bound = getattr(n, "name", None) or getattr(n, "arg", None) or getattr(n, "rest", None)
        count += bound == name
    return count


def _typing_flag(tree: ast.AST) -> bool:
    """True when the bare name TYPE_CHECKING in `tree` is the one from a top-level `from typing import
    TYPE_CHECKING` and is never bound anywhere else; a local `TYPE_CHECKING = True` is code that runs (P6)."""
    imported = any(isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == "typing"
                   and any(a.name == "TYPE_CHECKING" and a.asname is None for a in n.names)
                   for n in tree.body)
    return imported and _binds(tree, "TYPE_CHECKING") == 1


def _guards(tree: ast.AST) -> tuple[bool, bool, bool]:
    """Which `if` guards of `tree` may skip their body (P6, R4): (bare TYPE_CHECKING, typing.TYPE_CHECKING,
    __name__ == "__main__"). The bare name needs _typing_flag; `typing.` needs `typing` bound exactly once, by a
    plain `import typing`; both imports count only as top-level statements of the module (one inside a function, a
    class, an `if` or a `try` does not); the `__main__` test needs `__name__` bound nowhere in the module. A rebound
    name (typing = SimpleNamespace(TYPE_CHECKING=True), __name__ = "__main__") loses its guard, and a module that
    can change these names without binding them (an attribute store of TYPE_CHECKING, __name__ or __class__, or any
    setattr, delattr, globals, vars, locals, modules, __dict__, builtins, __builtins__, f_globals, f_locals,
    f_builtins, __globals__, get_referents, get_referrers or get_objects) trusts no guard: the guarded body is scanned.
    Not seen: another module changing typing.TYPE_CHECKING first (the review of each hashed diff)."""
    plain = any(isinstance(n, ast.Import) and any(a.name == "typing" and a.asname is None for a in n.names)
                for n in tree.body)
    routes = {"setattr", "delattr", "globals", "vars", "locals", "modules", "__dict__", "builtins", "__builtins__",
              "f_globals", "f_locals", "f_builtins", "__globals__", "get_referents", "get_referrers", "get_objects"}
    if any((isinstance(n, ast.Name) and n.id in routes) or (isinstance(n, ast.Attribute) and (n.attr in routes or (
            n.attr in ("TYPE_CHECKING", "__name__", "__class__") and not isinstance(n.ctx, ast.Load))))
           for n in ast.walk(tree)):
        return False, False, False
    return _typing_flag(tree), plain and _binds(tree, "typing") == 1, _binds(tree, "__name__") == 0


def _skipped(node: ast.AST, guards: tuple[bool, bool, bool]) -> bool:
    """Whether `node` is an `if` whose body never runs at import and so is outside the code closure (P6):
    `if TYPE_CHECKING:`, `if typing.TYPE_CHECKING:` and a single `==` comparison of `__name__` with "__main__" in
    either order, each only while `guards` (see _guards) trusts its name. Every other test (`!=`, `not
    TYPE_CHECKING`, a local or rebound name) is scanned, since its body can run at import."""
    if not isinstance(node, ast.If):
        return False
    bare, dotted, main = guards
    t = node.test
    if isinstance(t, ast.Name):
        return t.id == "TYPE_CHECKING" and bare
    if isinstance(t, ast.Attribute):
        return dotted and t.attr == "TYPE_CHECKING" and isinstance(t.value, ast.Name) and t.value.id == "typing"
    if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, *t.comparators]
        return (main and any(isinstance(s, ast.Name) and s.id == "__name__" for s in sides)
                and any(isinstance(s, ast.Constant) and s.value == "__main__" for s in sides))
    return False


def _import_nodes(node: ast.AST, guards: tuple[bool, bool, bool]):
    """Every import statement at any depth, function bodies included; a skipped `if` keeps its `else`."""
    if _skipped(node, guards):
        for child in node.orelse:
            yield from _import_nodes(child, guards)
        return
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from _import_nodes(child, guards)


def _module_file(root: Path, dotted: str) -> Path | None:
    """The repo file of an in-repo module name; None for stdlib, third-party and attribute names."""
    parts = dotted.split(".")
    if not all(part.isidentifier() for part in parts):
        return None
    for candidate in (root.joinpath(*parts[:-1], parts[-1] + ".py"), root.joinpath(*parts, "__init__.py")):
        if candidate.is_file():
            return candidate
    return None


def _repo_imports(root: Path, path: Path) -> set[Path]:
    """The in-repo files `path` imports, relative imports resolved against its package."""
    package = list(path.relative_to(root).parent.parts)
    names: set[str] = set()
    tree = ast.parse(path.read_bytes())
    for node in _import_nodes(tree, _guards(tree)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
            continue
        base = package[:len(package) - node.level + 1] if node.level else []
        module = ".".join(base + ([node.module] if node.module else []))
        if module:
            names.add(module)
            names.update(f"{module}.{alias.name}" for alias in node.names)
    return {f for name in names if (f := _module_file(root, name)) is not None}


def code_files(repo_root: Path) -> list[tuple[str, str]]:
    """Sorted (relative POSIX path, sha256) of the D14 closure, with venv:<dist>-<version>.dist-info/RECORD rows."""
    root = Path(repo_root)
    todo = [p for base in (root / "core" / "compliance", root / "core" / "odds", root / "execution")
            for p in sorted(base.glob("*.py"))]
    todo.extend(p for base in (root / "execution_control", root / "execution_orders", root / "execution_accounts", root / "execution_network", root / "execution_launch")
                for p in sorted(base.rglob("*.py")))
    seen: set[Path] = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        todo.extend(_repo_imports(root, path))
        todo.extend(d / "__init__.py" for d in path.parents
                    if d != root and d.is_relative_to(root) and (d / "__init__.py").is_file())
    out = {p.relative_to(root).as_posix(): sha256_hex(p.read_bytes()) for p in seen}
    from importlib import metadata
    for name in _RECORD_DISTS:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        record = next((f for f in dist.files or () if f.name == "RECORD" and f.parent.name.endswith(".dist-info")),
                      None)
        if record is not None:
            out[f"venv:{name}-{dist.version}.dist-info/RECORD"] = sha256_hex(Path(record.locate()).read_bytes())
    return sorted(out.items())


def code_hash(repo_root: Path) -> str:
    return sha256_hex(canonical_json(code_files(repo_root)))


# --------------------------------------------------------------------------- #
# Refusals, confirmation and signing
# --------------------------------------------------------------------------- #
def _process_table() -> dict[int, tuple[int, str]]:
    """pid -> (parent pid, exe name) of every process, from a Toolhelp32 snapshot (Windows, stdlib ctypes)."""
    import ctypes
    from ctypes import wintypes

    class _Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    k32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Entry))
    k32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Entry))
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)                     # TH32CS_SNAPPROCESS
    if snap is None or snap == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    table = {}
    try:
        entry = _Entry()
        entry.dwSize = ctypes.sizeof(_Entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            table[entry.th32ProcessID] = (entry.th32ParentProcessID, entry.szExeFile)
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return table


# Windows session processes: a user's chain normally passes one of these before its top parent exits (R11).
_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})


def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case), even above a Windows
    session process (a process name is only a file name). The walk goes on to pid 0 or until it breaks: at a pid
    missing from the table (a parent that has exited), a pid-reuse cycle or 256 steps. A break returns True (Claude
    cannot be ruled out) unless the walk has passed a session process (_SESSION_ROOTS): a user chain's top parent
    has normally exited (explorer.exe's, wininit.exe's), and Windows Terminal runs under svchost.exe, services.exe
    and wininit.exe (R11)."""
    seen, rooted = set(), False
    while pid != 0:
        if pid not in table or pid in seen or len(seen) >= 256:
            return not rooted
        seen.add(pid)
        parent, exe = table[pid]
        if exe.lower() == "claude.exe":
            return True
        rooted = rooted or exe.lower() in _SESSION_ROOTS
        pid = parent
    return False


def _claude_ancestor() -> bool:
    """Fails closed: True (Claude cannot be ruled out) unless a process table was read and holds this very process,
    so a failed snapshot, an empty table or a table without our own pid never lets the signer run."""
    try:
        table = _process_table()
    except Exception:
        return True
    if os.getpid() not in table:
        return True
    return _has_claude_ancestor(os.getpid(), table)


def _isolated() -> bool:
    """True under python.exe -I (a seam for the tests)."""
    return bool(sys.flags.isolated)


def _stdin_is_terminal() -> bool:
    """True when stdin is a real console. On Windows isatty() is true for any character device, NUL included, so
    stdin counts only if GetConsoleMode accepts its handle; any failure (no stdin, a closed or odd one, no
    ctypes) means "not a terminal"."""
    try:
        if os.name != "nt":
            return bool(sys.stdin.isatty())
        import ctypes
        import msvcrt
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetConsoleMode.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.GetConsoleMode.restype = wintypes.BOOL
        return bool(k32.GetConsoleMode(msvcrt.get_osfhandle(sys.stdin.fileno()), ctypes.byref(wintypes.DWORD())))
    except Exception:
        return False


def _refusal() -> str:
    """Why this process may not sign (spec 6.4 "Where it runs"), or ""."""
    names = sorted(k for k in os.environ if k.upper() == "CLAUDECODE" or k.upper().startswith("CLAUDE_CODE_"))
    if names:
        return f"{names[0]} is set: run me in your own terminal, never under Claude"
    if _claude_ancestor():
        return ("a parent process is claude.exe, or the parent chain stops at a process that has exited: open Windows "
                "Terminal yourself from the Start menu and run me there, never under Claude")
    if not _stdin_is_terminal():
        return "stdin is not a terminal: type the passphrase yourself"
    if not _isolated():
        # a reminder, not the defence: a module loaded before main() could fake this flag; the -I you type is it
        return ("not started with python.exe -I: without it a .py file next to sign.py, in the current folder or "
                "on PYTHONPATH could run while you type the passphrase")
    return ""


def _typed_ok(code: str, typed: str, stamps: list[float]) -> bool:
    """P27: `typed` equals `code`, its keystrokes arrived at least 30 ms apart on average, and no three gaps in a
    row were under 10 ms (one key, a pause, then a paste of the rest averages well above 30 ms)."""
    # ponytail: a timing heuristic. It passes a script that types slowly into the console, and a paste split into
    # pieces of at most three characters with pauses between them. Ceiling: anything that can write to your
    # console. Upgrade path: a hardware confirmation such as a security-key touch.
    if typed != code or len(stamps) < 2:
        return False
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    burst = any(all(g < TYPED_BURST_S for g in gaps[i:i + 3]) for i in range(len(gaps) - 2))
    return sum(gaps) / len(gaps) >= TYPED_MIN_GAP_S and not burst


def _read_typed(prompt: str) -> tuple[str, list[float]]:
    """(text, keystroke times) typed at the console up to Enter, echoed; Backspace edits, Ctrl+C aborts."""
    import msvcrt
    print(prompt, end="", flush=True)
    chars, stamps = [], []
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            print()
            return "".join(chars), stamps
        stamps.append(time.perf_counter())
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\b":
            if chars:
                chars.pop()
                print("\b \b", end="", flush=True)
            continue
        chars.append(ch)
        print(ch, end="", flush=True)


def _confirm(kind: str, data: dict, head: tuple[int, str], utc: str) -> None:
    """Show exactly what will be signed, its UTC stamp included and anything outside ASCII as an escape, then
    require a fresh random code, typed (not pasted)."""
    print(f"About to sign owner log entry #{head[0] + 1} (after #{head[0]} {head[1][:16] or 'start of log'}), "
          f"stamped {utc}. Check the stamp against the real time in UTC:")
    print(json.dumps({"kind": kind, "data": data}, indent=2, sort_keys=True, ensure_ascii=True))
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed, stamps = _read_typed(f"Type this code to sign it (do not paste): {code}\n> ")
    if not _typed_ok(code, typed, stamps):
        raise ValueError("the code was not typed exactly, or it arrived as a paste; nothing was signed")


def _unlock(key_path: Path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    seed = open_key(_checked(key_path).read_bytes(), getpass.getpass("Passphrase: "))
    return Ed25519PrivateKey.from_private_bytes(seed)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _wrong_key(signing_key, kind: str, data: dict, lines: list[bytes]) -> str:
    """"" when `signing_key` is the key owner.verify_log will expect on the line after `lines` (already checked by
    _head), else why not. A line signed by any other key would make the log BROKEN under every pem, for good. The
    key in force is: after the last key_rotated, its new_pubkey_b64; with no rotation, the key that signed the
    last owner line; with no owner line yet, any key. A key_rotated must also name the key you unlocked as old."""
    mine = signing_key.public_key().public_bytes_raw()
    if kind == "key_rotated" and base64.b64decode(data["old_pubkey_b64"]) != mine:
        return "key_rotated: old_pubkey_b64 is not the key you unlocked"
    entries = [json.loads(line) for line in lines]
    rotations = [e for e in entries if e["kind"] == "key_rotated"]
    if rotations:
        if base64.b64decode(rotations[-1]["data"]["new_pubkey_b64"]) != mine:
            return (f"the key you unlocked ({fingerprint(mine)}) is not the key in force since entry "
                    f"#{rotations[-1]['seq']} (key_rotated): pass --key with the new key file")
        return ""
    signed = [e for e in entries if e["kind"] in SCHEMAS]
    if signed:
        from cryptography.exceptions import InvalidSignature
        try:
            signing_key.public_key().verify(base64.b64decode(signed[-1]["sig"]),
                                            SIG_DOMAIN + signed[-1]["row_sha256"].encode("ascii"))
        except InvalidSignature:
            return (f"the key you unlocked ({fingerprint(mine)}) did not sign the log's last owner entry "
                    f"#{signed[-1]['seq']}: it is not the owner key of this log")
    return ""


def _commit(signing_key, kind: str, data: dict, *, utc: str, expect_head: tuple[int, str] | None = None
            ) -> tuple[int, str]:
    """Append one signed entry stamped `utc` under the sidecar lock and return (seq, row_sha256). The chain must
    still end at `expect_head` (what the owner was shown), `utc` may not be earlier than the last line's, and
    `signing_key` must be the key in force (_wrong_key); an approval's anchor is written after the line."""
    check_data(kind, data)
    if not _utc(utc):
        raise ValueError(f"utc {utc!r} is not YYYY-MM-DDTHH:MM:SSZ; nothing was signed")
    if kind == "approved":
        name = data["sha256"] if data["kind"] == "calendar" else f"{data['sha256']}.yaml"
        if not (_store_dir() / data["kind"] / name).exists():
            raise RuntimeError(f"approved {data['kind']} {data['sha256'][:16]}: store its bytes before signing")
    path = _log_path()
    with _exclusive(path):
        lines = _read_lines(path)
        head = _head(lines)
        if expect_head is not None and head != expect_head:
            raise RuntimeError("the owner log changed while you confirmed; nothing was signed, run it again")
        last = json.loads(lines[-1])["utc"] if lines else ""
        if utc < last:
            raise RuntimeError(f"the stamp {utc} is earlier than entry #{head[0]}'s {last}: check the PC clock; "
                               "nothing was signed")
        why = _wrong_key(signing_key, kind, data, lines)
        if why:
            raise ValueError(f"{why}; nothing was signed")
        line, row = entry_line(signing_key, head[0] + 1, head[1] or GENESIS_PREV, kind, data, utc)
        with open(_checked(path, state_root()), "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    if kind == "approved":
        _put_anchor(data["kind"], data["sha256"], (head[0] + 1, row))
    return head[0] + 1, row


def _key_path(args) -> Path:
    return Path(args.key) if args.key else _home() / "owner_key.enc"


def _sign(args, kind: str, data: dict, before=None) -> int:
    """Validate, stamp and show, take the typed code and the passphrase, run `before` (store writes), sign and
    append with exactly the stamp that was shown."""
    check_data(kind, data)
    lines = _read_lines(_log_path())
    head = _head(lines)
    utc = _utc_now()
    _confirm(kind, data, head, utc)
    signing_key = _unlock(_key_path(args))
    why = _wrong_key(signing_key, kind, data, lines)         # early, so `before` stores nothing; _commit checks
    if why:                                                  # again under the lock
        raise ValueError(f"{why}; nothing was signed")
    if before is not None:
        before()
    seq, row = _commit(signing_key, kind, data, utc=utc, expect_head=head)
    print(f"signed: owner log entry #{seq} ({kind}), stamped {utc}, row_sha256 {row}")
    return 0


def _cmd_keygen(args) -> int:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key_path = _key_path(args)
    pem_path = key_path.with_suffix(".pem")
    within = None if args.key else state_root()
    for p in (key_path, pem_path):
        if p.exists():
            raise ValueError(f"{p} already exists; keygen never overwrites a key")
    passphrase = getpass.getpass("New passphrase (20+ characters, or 5+ different words of 3+ letters): ")
    if not passphrase_ok(passphrase):
        raise ValueError("passphrase too weak: use at least 20 characters, or at least 5 different words of 3+ "
                         "letters")
    if getpass.getpass("Type it again: ") != passphrase:
        raise ValueError("the two passphrases differ; nothing was written")
    signing_key = Ed25519PrivateKey.generate()
    public = signing_key.public_key()
    _write_once(key_path, seal_key(signing_key.private_bytes_raw(), passphrase), within)
    _write_once(pem_path, public.public_bytes(serialization.Encoding.PEM,
                                              serialization.PublicFormat.SubjectPublicKeyInfo), within)
    raw = public.public_bytes_raw()
    print(f"key file:    {key_path}")
    print(f"public key:  {pem_path}  -> copy it to <repo>\\core\\compliance\\owner_pubkey.pem")
    print(f"fingerprint: {fingerprint(raw)}  -> write it on the paper with the signer's hash")
    print(f"raw public key (base64, for a later key_rotated): {base64.b64encode(raw).decode('ascii')}")
    return 0


def _cmd_fingerprint(args) -> int:
    key_path = _key_path(args)
    _, header, _ = _key_header(_checked(key_path).read_bytes())
    print(f"key file header {key_path}: {header['fingerprint']} (checked only when the passphrase opens it)")
    pem = key_path.with_suffix(".pem")
    if pem.is_file():
        raw = _pem_raw(pem.read_bytes())
        print(f"public key {pem}: {fingerprint(raw)} (raw base64 {base64.b64encode(raw).decode('ascii')})")
    return 0


def _cmd_approve(args) -> int:
    kind, src = args.kind, Path(args.path)
    if kind == "calendar":
        files = calendar_files(src)
        if not files:
            raise ValueError(f"calendar: {src} holds no files")
        sha = sha256_hex(_frame(files))
        return _sign(args, "approved", {"kind": kind, "sha256": sha}, before=lambda: _put_calendar(src, sha))
    raw = src.read_bytes()
    return _sign(args, "approved", {"kind": kind, "sha256": sha256_hex(raw)}, before=lambda: _put_blob(kind, raw))


def _cmd_code_approve(args) -> int:
    repo = _refuse_quantgen(Path(args.repo).resolve(), "--repo")
    venv = (repo / ".venv").resolve()
    if Path(sys.prefix).resolve() != venv:
        raise ValueError(f"run me with {venv / 'Scripts' / 'python.exe'} -I: the code hash covers that venv's "
                         "cryptography and PyYAML RECORD files")
    files = code_files(repo)
    return _sign(args, "code_approved", {"sha256": sha256_hex(canonical_json(files)),
                                         "files": [list(f) for f in files]})


def _cmd_event(args) -> int:
    data = json.loads(args.data)
    if args.kind in ("cap_set", "limit_set") and isinstance(data, dict):
        data = {k: float(v) if _number(v) else v for k, v in data.items()}     # caps and limits are floats
    return _sign(args, args.kind, data)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sign.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, run, text in (("keygen", _cmd_keygen, "create the key file and the public key"),
                            ("fingerprint", _cmd_fingerprint, "print the key fingerprint"),
                            ("approve", _cmd_approve, "approve a table file or the calendar folder"),
                            ("code-approve", _cmd_code_approve, "sign the code hash of the repo"),
                            ("event", _cmd_event, "sign one owner event")):
        p = sub.add_parser(name, help=text)
        p.set_defaults(run=run)
        p.add_argument("--key", help="key file (default: ~/.tradegen/compliance/owner_key.enc)")
        if name == "approve":
            p.add_argument("--kind", required=True, choices=APPROVAL_KINDS)
            p.add_argument("--path", required=True, help="the file, or the calendar data folder")
        elif name == "code-approve":
            p.add_argument("--repo", required=True, help="the TRADEGEN repo folder")
        elif name == "event":
            p.add_argument("kind", choices=sorted(set(SCHEMAS) - {"approved", "code_approved"}))
            p.add_argument("--data", required=True, help="the event data as one JSON object")
    return parser


def main(argv=None) -> int:
    """Refuse first (spec 6.4), then run one command. 2 refused, 1 failed, 0 signed or printed."""
    reason = _refusal()
    if reason:
        print(f"sign.py refused: {reason}", file=sys.stderr)
        return 2
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        print(f"sign.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
