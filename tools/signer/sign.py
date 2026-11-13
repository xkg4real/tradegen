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
  review-approve            detached source/fixed implementation review; see docs/strategy-review-signing.md
  bundle-attest             exact archived-file identity only; no source, selection, trading or recovery approval
  research-revoke           restrict use of one exact signed research body; no deletion, order or liquidation
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
import ntpath
import os
import re
import secrets
import stat
import sys
import time
from contextlib import contextmanager, ExitStack
from collections.abc import Mapping
from dataclasses import dataclass, fields
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
_RESEARCH_REVOKED = 'research_attestation_revoked'
_RESEARCH_TARGET_DOMAIN = b'tradegen-research-attestation-revocation-target/1\n'
_RESEARCH_PURPOSES = frozenset({'research_archive_manifest_attestation',
    'strategy_source_and_fixed_implementation_review', 'strategy_source_and_fixed_carry_implementation_review'})
_RESEARCH_REASONS = frozenset({'OWNER_WITHDRAWN', 'EVIDENCE_UNTRUSTED', 'REVIEW_ERROR'})
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
    _RESEARCH_REVOKED: {'purpose': lambda v: type(v) is str and v in _RESEARCH_PURPOSES,
        'target_sha256': lambda v: type(v) is str and _hex64(v),
        'reason_code': lambda v: type(v) is str and v in _RESEARCH_REASONS},
}
SYSTEM_SCHEMAS = {                                     # never signed here; _head checks them in the log
    "system_halt": {"floor_krw": lambda v: _number(v) and v >= 0},
    "system_disarm": {"session_id": _text, "reason": _text},
}
_DATA = {**SCHEMAS, **SYSTEM_SCHEMAS}


def _data_problem(kind: str, data) -> str:
    """owner._data_problem: "" when `data` has exactly the keys of `kind` with valid values, else what is wrong."""
    schema = _DATA[kind]
    if kind == _RESEARCH_REVOKED and type(data) is not dict:
        return 'is not an object'
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
# recursive execution_control/, execution_orders/, execution_accounts/, execution_network/, execution_launch/ and tools/owner/ files, every in-repo file they import at any depth
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
    todo.extend(p for base in (root / "execution_control", root / "execution_orders", root / "execution_accounts", root / "execution_network", root / "execution_launch", root / "tools" / "owner")
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


def _commit(signing_key, kind: str, data: dict, *, utc: str, expect_head: tuple[int, str] | None = None,
            research_input=None
            ) -> tuple[int, str]:
    """Append one signed entry stamped `utc` under the sidecar lock and return (seq, row_sha256). The chain must
    still end at `expect_head` (what the owner was shown), `utc` may not be earlier than the last line's, and
    `signing_key` must be the key in force (_wrong_key); an approval's anchor is written after the line."""
    check_data(kind, data)
    if kind == _RESEARCH_REVOKED and type(research_input) is not _ResearchRevocationInput:
        raise ValueError('research revocation requires its independently reviewed document')
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
        if kind == _RESEARCH_REVOKED:
            _research_recheck(research_input, data, signing_key, lines, utc)
            entries = tuple(json.loads(row) for row in lines)
            _research_anchor_inventory(entries)
            try:
                _research_flush_log(lines)
                _research_ensure_anchors(entries)
            except (OSError, ValueError, RuntimeError):
                raise RuntimeError('research restriction anchor is incomplete; existing log restrictions remain; retry exact input') from None
            _research_recheck(research_input, data, signing_key, lines, utc)
            if entries and entries[-1]['kind'] == kind and entries[-1]['data'] == data:
                return head
        line, row = entry_line(signing_key, head[0] + 1, head[1] or GENESIS_PREV, kind, data, utc)
        with open(_checked(path, state_root()), "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        if kind == _RESEARCH_REVOKED:
            try:
                _research_ensure_anchors(entries + (json.loads(line),))
            except (OSError, ValueError, RuntimeError):
                raise RuntimeError('research restriction was appended but its anchor is unconfirmed; preserve the log and retry exact input') from None
    if kind == "approved":
        _put_anchor(data["kind"], data["sha256"], (head[0] + 1, row))
    return head[0] + 1, row


def _key_path(args) -> Path:
    return Path(args.key) if args.key else _home() / "owner_key.enc"


def _sign(args, kind: str, data: dict, before=None) -> int:
    """Validate, stamp and show, take the typed code and the passphrase, run `before` (store writes), sign and
    append with exactly the stamp that was shown."""
    if kind == _RESEARCH_REVOKED:
        raise ValueError('use research-revoke with the original detached document')
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




# Detached review validators: standalone copies, checked against runtime contract.
_REVIEW_FACTORY_ID = "tradegen-fixed-cash-trend-v1"
_REVIEW_CARRY_FACTORY_ID = "tradegen-fixed-carry-v2"
_REVIEW_BEHAVIOR_REVISION = "protective-carry-v2"
_REVIEW_CARRY_EVALUATOR_REVISION = "forward-paper-carry-v2"
_REVIEW_TERMINAL_ACCOUNTING = "mark_open_positions"
_rr_MAX_REQUEST_BYTES = 65536

_rr_HASH = re.compile('[0-9a-f]{64}')

_rr_ID = re.compile('[A-Za-z][A-Za-z0-9_.:-]{0,95}')

_rr_KINDS = frozenset({'prospective_paper_capture', 'synthetic', 'retrospective_replay'})

_rr_BINDINGS = frozenset({'protocol_digest', 'evidence_digest', 'registry_digest', 'inputs_digest', 'profile_contract_digest', 'runtime_profile_digest', 'rule_terms_digest', 'program_digest', 'program_artifact_sha256', 'canonical_parameters_sha256', 'capture_source_code_sha256'})

_rr_AUTH_FLAGS = frozenset({'source_authenticated', 'implementation_authenticated', 'signature_verified', 'owner_context_verified', 'research_review_ready', 'execution_ready'})

_rr_CHECKS = ('original_source_identity_and_records', 'publication_before_capture', 'independent_capture_window', 'complete_candidate_and_retry_family', 'causal_decisions_match_frozen_program', 'fixed_runtime_driver_matches_reviewed_program', 'deployment_source_and_dependency_closure', 'capital_fees_rules_and_account_risk_applicability', 'effective_owner_limits_and_actual_session')

_rr_METRICS = frozenset({'observations', 'completed_roundtrips', 'total_return', 'max_drawdown', 'double_cost_total_return', 'extra_delay_total_return', 'family_adjusted_p'})

_rr_CARRY_NUMERIC = frozenset({'observations', 'completed_roundtrips', 'valuation_total_return', 'max_drawdown', 'double_cost_valuation_total_return', 'extra_delay_valuation_total_return', 'family_adjusted_p'})

_rr_CARRY_AMOUNTS = frozenset({'terminal_units', 'terminal_cash_quote', 'terminal_mark_quote', 'terminal_marked_equity_quote', 'terminal_inventory_cost_quote', 'realized_net_profit_quote', 'unrealized_net_profit_quote', 'total_fees_quote_exact', 'turnover_quote_exact'})

_rr_CARRY_METRICS = _rr_CARRY_NUMERIC | _rr_CARRY_AMOUNTS | {'terminal_observed_at', 'terminal_source_sha256'}

_rr_CARRY_FIELDS = frozenset({'behavior_revision', 'terminal_accounting', 'management_behavior_sha256'})

_rr_TOP = frozenset({'schema_version', 'artifact_kind', 'requested_at', 'capture_start', 'capture_end', 'evaluated_at', 'review_deadline', 'study_id', 'strategy_id', 'capture_source_id', 'evaluator_revision', 'source_kind_claim', 'bindings', 'computed_summary', 'profile_blockers', 'assessment_reasons', 'required_checks', 'reviewer_id', 'review_public_key', 'review_signature', 'deployment_code_hash', 'authority', 'request_sha256'})

_rr_FAMILY = frozenset({'plan_digest', 'members', 'family_sha256'})

_rr_MEMBER = frozenset({'study_id', 'capture_sha256', 'evidence_digest'})

class _rr_ReviewRequestError(ValueError):
    """Fixed diagnostics with no supplied value or provider text."""

def _rr_require(condition, code):
    if not condition:
        raise _rr_ReviewRequestError(code)

def _rr_stamp(value):
    _rr_require(type(value) is datetime and value.utcoffset() is not None, 'REVIEW_AWARE_TIME_REQUIRED')
    try:
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError, OverflowError):
        raise _rr_ReviewRequestError('REVIEW_TIME_INVALID') from None

def _rr_time(value):
    _rr_require(type(value) is str and len(value) <= 40, 'REVIEW_TIME_INVALID')
    try:
        stamp = datetime.fromisoformat(value)
        _rr_require(_rr_stamp(stamp) == value, 'REVIEW_TIME_FORMAT_INVALID')
        return stamp
    except (ValueError, TypeError, OverflowError):
        raise _rr_ReviewRequestError('REVIEW_TIME_INVALID') from None

def _rr_hash(value):
    return type(value) is str and _rr_HASH.fullmatch(value) is not None

def _rr_identifier(value):
    return type(value) is str and _rr_ID.fullmatch(value) is not None

def _rr_canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise _rr_ReviewRequestError('REVIEW_REQUEST_JSON_INVALID') from None

def _rr_validate_family(value):
    _rr_require(type(value) is dict and set(value) == _rr_FAMILY and _rr_hash(value['plan_digest']), 'REVIEW_FAMILY_SCHEMA_INVALID')
    members = value['members']
    _rr_require(type(members) is list and 1 <= len(members) <= 128 and all((type(row) is dict and set(row) == _rr_MEMBER and _rr_identifier(row['study_id']) and _rr_hash(row['capture_sha256']) and _rr_hash(row['evidence_digest']) for row in members)), 'REVIEW_FAMILY_SCHEMA_INVALID')
    ids = [row['study_id'] for row in members]
    _rr_require(ids == sorted(set(ids)), 'REVIEW_FAMILY_SCHEMA_INVALID')
    body = {'plan_digest': value['plan_digest'], 'members': members}
    _rr_require(_rr_hash(value['family_sha256']) and value['family_sha256'] == hashlib.sha256(_rr_canonical(body).encode('ascii')).hexdigest(), 'REVIEW_FAMILY_DIGEST_MISMATCH')

def _rr_build_family_commitment(*, plan_digest, capture_digests, result_digests):
    """Bind the entire evaluated family, including failures; this is not authentication.

    The study workflow computes these hashes from every raw capture and issued
    evaluation. A detached owner signature over a schema-2 request authenticates
    that reviewed family; the selector must recompute it before choosing a row.
    """
    _rr_require(type(capture_digests) is dict and type(result_digests) is dict and (set(capture_digests) == set(result_digests)) and all((_rr_identifier(name) for name in capture_digests)), 'REVIEW_FAMILY_SCHEMA_INVALID')
    body = {'plan_digest': plan_digest, 'members': [{'study_id': name, 'capture_sha256': capture_digests[name], 'evidence_digest': result_digests[name]} for name in sorted(capture_digests)]}
    value = body | {'family_sha256': hashlib.sha256(_rr_canonical(body).encode('ascii')).hexdigest()}
    _rr_validate_family(value)
    return value

def _rr_bind_review_family(request, commitment):
    """Create a new unsigned schema-2 request; never upgrade an existing signature."""
    _rr_validate(request)
    _rr_require(request['schema_version'] in (1, 3), 'REVIEW_FAMILY_ALREADY_BOUND')
    _rr_validate_family(commitment)
    body = {name: value for name, value in request.items() if name != 'request_sha256'}
    body.update(schema_version=2 if request['schema_version'] == 1 else 4, family_commitment=json.loads(_rr_canonical(commitment)))
    result = body | {'request_sha256': hashlib.sha256(_rr_canonical(body).encode('ascii')).hexdigest()}
    _rr_validate(result)
    return result

def _rr_carry_amount(value, *, signed=False):
    """Independent-review-friendly strict signed string codec, no app imports."""
    _rr_require(type(value) is str and 0 < len(value) <= 4096 and (re.fullmatch('-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?', value) is not None), 'REVIEW_REQUEST_SUMMARY_INVALID')
    amount = Decimal(value)
    _rr_require(len(amount.as_tuple().digits) <= 2048 and abs(amount.as_tuple().exponent) <= 2048 and (amount.copy_abs() <= Decimal('1e100')) and (signed or amount >= 0), 'REVIEW_REQUEST_SUMMARY_INVALID')
    text = format(amount, 'f')
    text = text.rstrip('0').rstrip('.') if '.' in text else text
    _rr_require(value == (text if amount else '0'), 'REVIEW_REQUEST_SUMMARY_INVALID')

def _rr_validate_metrics(metrics, *, carry):
    expected = _rr_CARRY_METRICS if carry else _rr_METRICS
    _rr_require(type(metrics) is dict and set(metrics) == expected, 'REVIEW_REQUEST_SUMMARY_INVALID')
    for name in _rr_CARRY_NUMERIC if carry else _rr_METRICS:
        value = metrics[name]
        _rr_require(type(value) is int and 0 <= value <= 100000 if name in ('observations', 'completed_roundtrips') else type(value) in (float, int) and math.isfinite(value), 'REVIEW_REQUEST_SUMMARY_INVALID')
    _rr_require(0 < metrics['family_adjusted_p'] <= 1 and 0 <= metrics['max_drawdown'] <= 1, 'REVIEW_REQUEST_SUMMARY_INVALID')
    if carry:
        for name in _rr_CARRY_AMOUNTS:
            _rr_carry_amount(metrics[name], signed=name in ('realized_net_profit_quote', 'unrealized_net_profit_quote'))
        _rr_time(metrics['terminal_observed_at'])
        _rr_require(_rr_hash(metrics['terminal_source_sha256']), 'REVIEW_REQUEST_SUMMARY_INVALID')

def _rr_validate(request):
    _rr_require(type(request) is dict and type(request.get('schema_version')) is int and (request['schema_version'] in (1, 2, 3, 4)), 'REVIEW_REQUEST_SCHEMA_INVALID')
    carry = request['schema_version'] in (3, 4)
    family_bound = request['schema_version'] in (2, 4)
    expected = _rr_TOP | (_rr_CARRY_FIELDS if carry else set()) | ({'family_commitment'} if family_bound else set())
    _rr_require(set(request) == expected, 'REVIEW_REQUEST_SCHEMA_INVALID')
    _rr_require(type(request['schema_version']) is int and request['schema_version'] in (1, 2, 3, 4) and (request['artifact_kind'] == 'unsigned_strategy_review_request'), 'REVIEW_REQUEST_SCHEMA_INVALID')
    stamps = {name: _rr_time(request[name]) for name in ('requested_at', 'capture_start', 'capture_end', 'evaluated_at', 'review_deadline')}
    _rr_require(stamps['capture_start'] < stamps['capture_end'] <= stamps['evaluated_at'] <= stamps['requested_at'] and stamps['review_deadline'] > stamps['capture_end'], 'REVIEW_REQUEST_CHRONOLOGY_INVALID')
    for name in ('study_id', 'strategy_id', 'capture_source_id', 'evaluator_revision'):
        _rr_require(_rr_identifier(request[name]), 'REVIEW_REQUEST_IDENTIFIER_INVALID')
    _rr_require((request['evaluator_revision'] == _REVIEW_CARRY_EVALUATOR_REVISION) == carry, 'REVIEW_REQUEST_REVISION_MISMATCH')
    if carry:
        _rr_require(request['behavior_revision'] == _REVIEW_BEHAVIOR_REVISION and request['terminal_accounting'] == _REVIEW_TERMINAL_ACCOUNTING and (request['management_behavior_sha256'] == _review_carry_behavior_digest()), 'REVIEW_REQUEST_BEHAVIOR_MISMATCH')
    _rr_require(type(request['source_kind_claim']) is str and request['source_kind_claim'] in _rr_KINDS, 'REVIEW_SOURCE_KIND_INVALID')
    bindings = request['bindings']
    _rr_require(type(bindings) is dict and set(bindings) == _rr_BINDINGS and all((_rr_hash(v) for v in bindings.values())), 'REVIEW_REQUEST_BINDING_INVALID')
    if family_bound:
        family = request['family_commitment']
        _rr_validate_family(family)
        member = next((row for row in family['members'] if row['study_id'] == request['study_id']), None)
        _rr_require(member is not None and member['evidence_digest'] == bindings['evidence_digest'], 'REVIEW_FAMILY_CANDIDATE_MISMATCH')
    summary = request['computed_summary']
    _rr_require(type(summary) is dict and set(summary) == {'mathematical_criteria_met', 'metrics'} and (type(summary['mathematical_criteria_met']) is bool), 'REVIEW_REQUEST_SUMMARY_INVALID')
    _rr_validate_metrics(summary['metrics'], carry=carry)
    for name in ('profile_blockers', 'assessment_reasons'):
        values = request[name]
        _rr_require(type(values) is list and len(values) <= 100 and all((type(v) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}', v) for v in values)), 'REVIEW_REQUEST_REASONS_INVALID')
    expected_checks = [{'id': name, 'reviewed': None, 'evidence_sha256': None} for name in _rr_CHECKS]
    _rr_require(request['required_checks'] == expected_checks, 'REVIEW_REQUEST_REVIEW_MUST_REMAIN_PENDING')
    for name in ('reviewer_id', 'review_public_key', 'review_signature', 'deployment_code_hash'):
        _rr_require(request[name] is None, 'REVIEW_REQUEST_CANNOT_CONTAIN_APPROVAL')
    authority = request['authority']
    _rr_require(type(authority) is dict and set(authority) == _rr_AUTH_FLAGS and all((value is False for value in authority.values())), 'REVIEW_REQUEST_CANNOT_GRANT_AUTHORITY')
    body = {name: value for name, value in request.items() if name != 'request_sha256'}
    _rr_require(_rr_hash(request['request_sha256']) and request['request_sha256'] == hashlib.sha256(_rr_canonical(body).encode('ascii')).hexdigest(), 'REVIEW_REQUEST_DIGEST_MISMATCH')

def _rr_review_request_json(request) -> str:
    """Serialize an unsigned request, rejecting added approval or PASS fields."""
    _rr_validate(request)
    raw = _rr_canonical(request)
    _rr_require(len(raw) <= _rr_MAX_REQUEST_BYTES, 'REVIEW_REQUEST_TOO_LARGE')
    return raw

def _rr_parse_review_request(raw: str | bytes) -> dict:
    """Inspect only request integrity; imported summaries are never recomputed evidence."""
    _rr_require(type(raw) in (str, bytes) and len(raw) <= _rr_MAX_REQUEST_BYTES, 'REVIEW_REQUEST_TOO_LARGE')

    def pairs(values):
        result = {}
        for key, value in values:
            _rr_require(key not in result, 'REVIEW_REQUEST_DUPLICATE_KEY')
            result[key] = value
        return result

    def invalid(value):
        raise _rr_ReviewRequestError('REVIEW_REQUEST_JSON_INVALID')
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        _rr_validate(result)
        return result
    except _rr_ReviewRequestError:
        raise
    except (ValueError, TypeError, UnicodeError, ArithmeticError, RecursionError):
        raise _rr_ReviewRequestError('REVIEW_REQUEST_JSON_INVALID') from None

_rv_REVIEW_DOMAIN = b'tradegen-strategy-review/1\n'

_rv_CARRY_REVIEW_DOMAIN = b'tradegen-strategy-review/2\n'

_rv_MAX_DOCUMENT_BYTES = 98304

_rv_MAX_REVIEW_SECONDS = 86400

_rv_REVIEW_CHECKS = ('original_source_identity_and_records', 'publication_before_capture', 'independent_capture_window', 'complete_candidate_and_retry_family', 'causal_decisions_match_frozen_program', 'fixed_runtime_driver_matches_reviewed_program', 'deployment_source_and_dependency_closure', 'capital_fees_rules_and_account_risk_applicability')

_rv_BODY = frozenset({'schema_version', 'purpose', 'request', 'driver_identity', 'deployment_code_hash', 'audit_sha256', 'owner_fingerprint', 'reviewer_id', 'issued_at', 'expires_at', 'approved_checks'})

_rv_IDENTITY = frozenset({'factory_id', 'program_digest', 'deployment_code_sha256', 'protocol_digest', 'profile_contract_digest', 'rule_terms_digest', 'deployment_window_digest'})

_rv_HASH = re.compile('[0-9a-f]{64}')

class _rv_ReviewAuthenticationError(ValueError):
    """Fixed diagnostics only, no external body, exception or private state."""

def _rv_need(value, code):
    if not value:
        raise _rv_ReviewAuthenticationError(code)

def _rv_canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError):
        raise _rv_ReviewAuthenticationError('REVIEW_DOCUMENT_INVALID') from None

def _rv_time(value):
    try:
        _rv_need(type(value) is str and len(value) <= 40, 'REVIEW_TIME_INVALID')
        stamp = datetime.fromisoformat(value)
        _rv_need(stamp.utcoffset() is not None and stamp.astimezone(timezone.utc).isoformat(timespec='microseconds') == value, 'REVIEW_TIME_INVALID')
        return stamp
    except (TypeError, ValueError, OverflowError):
        raise _rv_ReviewAuthenticationError('REVIEW_TIME_INVALID') from None

def _rv_stamp(value):
    _rv_need(type(value) is datetime and value.utcoffset() is not None, 'REVIEW_TIME_INVALID')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')

def _rv_hash(value):
    return type(value) is str and _rv_HASH.fullmatch(value) is not None

def _rv_validate_body(body):
    _rv_need(type(body) is dict and set(body) == _rv_BODY and (type(body['schema_version']) is int) and (body['schema_version'] in (1, 2)), 'REVIEW_DOCUMENT_SCHEMA_INVALID')
    carry = body['schema_version'] == 2
    expected_purpose = 'strategy_source_and_fixed_carry_implementation_review' if carry else 'strategy_source_and_fixed_implementation_review'
    _rv_need(body['purpose'] == expected_purpose, 'REVIEW_DOCUMENT_SCHEMA_INVALID')
    try:
        request = _rr_parse_review_request(_rv_canonical(body['request']))
    except _rr_ReviewRequestError:
        raise _rv_ReviewAuthenticationError('REVIEW_UNSIGNED_REQUEST_INVALID') from None
    _rv_need(request['source_kind_claim'] == 'prospective_paper_capture' and request['computed_summary']['mathematical_criteria_met'] is True and (request['assessment_reasons'] == ['STRATEGY_TRUSTED_REVIEW_REQUIRED']) and (set(request['profile_blockers']) <= {'SIGNED_CONTEXT_REQUIRED'}), 'REVIEW_REQUEST_NOT_ELIGIBLE')
    _rv_need(request['schema_version'] in ((3, 4) if carry else (1, 2)) and request['evaluator_revision'] in (('forward-paper-carry-v2',) if carry else ('forward-paper-v1', 'forward-universe-v1')), 'REVIEW_REVISION_FACTORY_MISMATCH')
    identity = body['driver_identity']
    expected_factory = _REVIEW_CARRY_FACTORY_ID if carry else _REVIEW_FACTORY_ID
    _rv_need(type(identity) is dict and set(identity) == _rv_IDENTITY and (identity['factory_id'] == expected_factory) and all((_rv_hash(v) for k, v in identity.items() if k != 'factory_id')), 'REVIEW_DRIVER_IDENTITY_INVALID')
    _rv_need(all((identity[key] == request['bindings'][key] for key in ('program_digest', 'protocol_digest', 'profile_contract_digest', 'rule_terms_digest'))), 'REVIEW_DRIVER_REQUEST_MISMATCH')
    _rv_need(_rv_hash(body['deployment_code_hash']) and _rv_hash(body['audit_sha256']), 'REVIEW_DIGEST_INVALID')
    fp = body['owner_fingerprint']
    _rv_need(type(fp) is str and fp.startswith('SHA256:') and _rv_hash(fp[7:]) and (body['reviewer_id'] == 'owner:' + fp[7:]), 'REVIEW_SIGNER_IDENTITY_INVALID')
    issued, expires = (_rv_time(body['issued_at']), _rv_time(body['expires_at']))
    _rv_need(_rv_time(request['requested_at']) <= issued < expires <= _rv_time(request['review_deadline']) and expires - issued <= timedelta(seconds=_rv_MAX_REVIEW_SECONDS), 'REVIEW_VALIDITY_INVALID')
    _rv_need(body['approved_checks'] == list(_rv_REVIEW_CHECKS), 'REVIEW_CHECKLIST_INCOMPLETE')
    return body

def _rv_review_body(request, driver_identity, *, deployment_code_hash, audit_sha256, owner_fingerprint, issued_at, expires_at):
    """Build strictly typed unsigned signing input; this grants no review status."""
    parsed = _rr_parse_review_request(_rr_review_request_json(request))
    carry = parsed['schema_version'] in (3, 4)
    body = {'schema_version': 2 if carry else 1, 'purpose': 'strategy_source_and_fixed_carry_implementation_review' if carry else 'strategy_source_and_fixed_implementation_review', 'request': parsed, 'driver_identity': dict(driver_identity), 'deployment_code_hash': deployment_code_hash, 'audit_sha256': audit_sha256, 'owner_fingerprint': owner_fingerprint, 'reviewer_id': 'owner:' + owner_fingerprint[7:], 'issued_at': _rv_stamp(issued_at), 'expires_at': _rv_stamp(expires_at), 'approved_checks': list(_rv_REVIEW_CHECKS)}
    return _rv_validate_body(body)

def _rv_review_signing_bytes(body):
    validated = _rv_validate_body(body)
    domain = _rv_CARRY_REVIEW_DOMAIN if validated['schema_version'] == 2 else _rv_REVIEW_DOMAIN
    return domain + _rv_canonical(validated).encode('ascii')


def _rv_parse_review_document(raw):
    """Independent existing source-envelope parser; parsing is not authentication."""
    _rv_need(type(raw) in (str, bytes) and len(raw) <= _rv_MAX_DOCUMENT_BYTES, 'REVIEW_DOCUMENT_TOO_LARGE')
    def pairs(items):
        result = {}
        for key, value in items:
            _rv_need(key not in result, 'REVIEW_DOCUMENT_DUPLICATE_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise _rv_ReviewAuthenticationError('REVIEW_DOCUMENT_INVALID')
    try:
        envelope = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        _rv_need(type(envelope) is dict and set(envelope) == {'body', 'signature_b64'}, 'REVIEW_ENVELOPE_INVALID')
        _rv_validate_body(envelope['body'])
        signature = envelope['signature_b64']
        _rv_need(type(signature) is str and len(signature) == 88, 'REVIEW_SIGNATURE_INVALID')
        decoded = base64.b64decode(signature, validate=True)
        _rv_need(len(decoded) == 64 and base64.b64encode(decoded).decode('ascii') == signature,
                 'REVIEW_SIGNATURE_INVALID')
        return envelope
    except _rv_ReviewAuthenticationError:
        raise
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError, binascii.Error):
        raise _rv_ReviewAuthenticationError('REVIEW_DOCUMENT_INVALID') from None

_REVIEW_SOURCES = (
    'execution_launch/driver.py',
    'execution_launch/program.py',
    'execution_launch/strategy.py',
    'execution_launch/runner.py',
    'execution_launch/profile.py',
    'execution_control/model.py',
    'execution_control/capability.py',
    'execution_control/controller.py',
    'execution_launch/evidence_objects.py',
    'execution_launch/history_storage.py',
    'execution_launch/live_history.py',
    'execution_launch/baseline_head.py',
    'execution_control/store.py',
    'core/isolation.py',
    'execution_launch/managed_behavior.py',
    'execution_launch/committed_account.py',
    'execution_accounts/baseline_bridge.py',
    'execution_accounts/baseline.py',
    'execution_accounts/baseline_store.py',
    'execution_accounts/continuous.py',
    'execution_accounts/model.py',
    'execution_accounts/provider.py',
    'execution_control/risk.py',
    'execution_launch/continuous_guard.py',
    'execution_launch/continuous_guard_commit.py',
    'execution_launch/committed_producer.py',
    'execution_launch/committed_startup.py',
    'execution_launch/coordinator.py',
    'execution_launch/account_interval.py',
    'execution_launch/continuous_archive.py',
    'execution_launch/guard_capture_material.py',
    'execution_launch/guard_capture_format.py',
    'execution_launch/guard_capture_archive.py',
    'execution_launch/guard_generation_format.py',
    'execution_launch/guard_generation_archive.py',
    'execution_launch/research_bundle_format.py',
    'execution_launch/research_bundle_store.py',
    'execution_accounts/collector.py',
    'execution_accounts/upbit_collector.py',
    'execution_control/owner_authority.py',
    'execution_control/dry_run.py',
    'core/compliance/model.py',
    'core/compliance/owner.py',
    'execution_launch/protective_state.py',
    'execution_launch/protective_store.py',
    'execution_launch/paper_capture.py',
)
# Independent copies of the reviewed source closures; never import repository code here.
_REVIEW_CARRY_SOURCES = _REVIEW_SOURCES + (
    'execution_launch/carry_evaluator.py',
    'execution_launch/capture_v2.py',
    'execution_launch/review_request.py',
)


def _review_carry_behavior_document():
    """Independent closed behavior contract; this signer never loads an app-defined policy."""
    return {"schema_version": 2, "behavior_revision": "protective-carry-v2",
        "evaluator_revision": "forward-paper-carry-v2", "factory_id": _REVIEW_CARRY_FACTORY_ID,
        "scope": ["upbit", "spot", "KRW", "fixed", "gtc"], "initial_condition": "flat_start",
        "entry_interval": "[start,deadline)", "deadline_action": "request_management_approval",
        "post_deadline_automatic_action": "blocked_without_separate_authority",
        "hold_rebalance_reduction": False, "failure_action": "block_dependent_action",
        "terminal_accounting": "mark_open_positions",
        "fifo_cost_allocation": "18dp_down_final_residual", "buy_fees": "included_in_cost",
        "sell_fees": "deducted_from_proceeds"}


def _review_carry_behavior_digest():
    return sha256_hex(canonical_json(_review_carry_behavior_document()))


def _review_path(path):
    """Explicit regular-file inputs/output, with no linked path components."""
    target = Path(path).absolute()
    for part in (target, *target.parents):
        _checked(part)
    return target


def _review_read(path, limit):
    target = _review_path(path)
    initial = os.lstat(target)
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1 or not 0 < initial.st_size <= limit:
        raise ValueError("review input must be a bounded regular file with one name")
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
             | getattr(os, "O_NONBLOCK", 0))
    descriptor = os.open(target, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= limit:
            raise ValueError("review input must be a bounded regular file with one name")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(descriptor)
        current = os.stat(target, follow_symlinks=False)
        if (len(raw) != before.st_size or len(raw) > limit
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (after.st_dev, after.st_ino) != (current.st_dev, current.st_ino)):
            raise ValueError("review input changed while reading")
        return raw
    finally:
        os.close(descriptor)


def _review_identity(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_no_duplicates,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid review number")))
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise ValueError("invalid fixed-driver manifest") from None
    if (type(value) is not dict or set(value) != _rv_IDENTITY
            or value["factory_id"] not in (_REVIEW_FACTORY_ID, _REVIEW_CARRY_FACTORY_ID)
            or not all(_rv_hash(v) for k, v in value.items() if k != "factory_id")):
        raise ValueError("invalid fixed-driver manifest")
    return value


def _review_source_hash(repo, *, factory_id=_REVIEW_FACTORY_ID):
    if factory_id not in (_REVIEW_FACTORY_ID, _REVIEW_CARRY_FACTORY_ID):
        raise ValueError("unsupported review factory")
    names = _REVIEW_CARRY_SOURCES if factory_id == _REVIEW_CARRY_FACTORY_ID else _REVIEW_SOURCES
    files = {name: sha256_hex(_review_read(repo / name, 1048576)) for name in names}
    return sha256_hex(canonical_json({"factory_id": factory_id, "files": files}))


def _review_identity_source_hash(repo, identity):
    # Preserve the legacy one-argument seam; carry uses its explicit closed closure.
    return (_review_source_hash(repo) if identity["factory_id"] == _REVIEW_FACTORY_ID
            else _review_source_hash(repo, factory_id=identity["factory_id"]))


def _confirm_review(body):
    print("About to attest source and fixed implementation review. This does not arm a session or place an order.")
    print("The live-history provider/verifier and fresh account integration require separate deployment review.")
    print("Verify every approved_checks item against your actual audit. No profitability is guaranteed.")
    if body["schema_version"] == 2:
        print("Carry-v2 valuation includes unrealized holdings; it is not realized net profit.")
        print("This review grants no separate post-deadline management or order authority.")
    print(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=True))
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed, stamps = _read_typed(f"Type this code to sign the review (do not paste): {code}\n> ")
    if not _typed_ok(code, typed, stamps):
        raise ValueError("review code was not typed exactly; nothing was signed")


def _cmd_review_approve(args):
    """Owner-only detached document. No owner event schema or ledger append."""
    repo = _refuse_quantgen(Path(args.repo).resolve(), "--repo")
    if Path(sys.prefix).resolve() != (repo / ".venv").resolve():
        raise ValueError("run review-approve with the deployment .venv Python and -I")
    output = _review_path(args.output)
    if output.exists() or not output.parent.is_dir():
        raise ValueError("review output must be a new file in an existing private folder")
    request = _rr_parse_review_request(_review_read(args.request, _rr_MAX_REQUEST_BYTES))
    identity = _review_identity(_review_read(args.driver_manifest, 8192))
    audit_path = _review_path(args.audit)
    if audit_path.suffix.lower() not in (".txt", ".md", ".pdf", ".json"):
        raise ValueError("review audit must be an explicit txt, md, pdf or json document")
    audit = _review_read(audit_path, 1048576)
    pem_path = repo / "core" / "compliance" / "owner_pubkey.pem"
    public = _pem_raw(_review_read(pem_path, 4096))
    closure = code_hash(repo)
    if identity["deployment_code_sha256"] != _review_identity_source_hash(repo, identity):
        raise ValueError("fixed-driver manifest does not match deployment source bytes")
    now = datetime.fromisoformat(_utc_now().replace("Z", "+00:00"))
    expires = _rv_time(args.expires_at)
    body = _rv_review_body(request, identity, deployment_code_hash=closure, audit_sha256=sha256_hex(audit),
        owner_fingerprint=fingerprint(public), issued_at=now, expires_at=expires)
    lines = _read_lines(_log_path())
    head = _head(lines)
    approvals = [json.loads(line) for line in lines if json.loads(line)["kind"] == "code_approved"]
    if not approvals or approvals[-1]["data"]["sha256"] != closure:
        raise ValueError("review and code-approve this exact deployment first")
    _confirm_review(body)
    key = _unlock(_key_path(args))
    if key.public_key().public_bytes_raw() != public:
        raise ValueError("unlocked review key does not match the current deployment PEM")
    with _exclusive(_log_path()):
        current = _read_lines(_log_path())
        if _head(current) != head or _wrong_key(key, "review_document", {}, current):
            raise ValueError("owner log or current signing key changed; review again")
        current_time = datetime.fromisoformat(_utc_now().replace("Z", "+00:00"))
        if not now <= current_time < min(expires, now + timedelta(minutes=5)):
            raise ValueError("review confirmation expired or clock moved; review again")
        if (_pem_raw(_review_read(pem_path, 4096)) != public or code_hash(repo) != closure
                or _review_identity_source_hash(repo, identity) != identity["deployment_code_sha256"]
                or sha256_hex(_review_read(audit_path, 1048576)) != body["audit_sha256"]):
            raise ValueError("review deployment, public key or audit changed; review again")
        if (_rr_parse_review_request(_review_read(args.request, _rr_MAX_REQUEST_BYTES)) != request
                or _review_identity(_review_read(args.driver_manifest, 8192)) != identity):
            raise ValueError("review inputs changed; review again")
        _review_path(output)
        if output.exists():
            raise ValueError("review output already exists; nothing was signed")
        signature = base64.b64encode(key.sign(_rv_review_signing_bytes(body))).decode("ascii")
        encoded = (canonical_json({"body": body, "signature_b64": signature}) + "\n").encode("ascii")
        if len(encoded) > _rv_MAX_DOCUMENT_BYTES:
            raise ValueError("review document too large")
        if not _write_new(output, encoded, None):
            raise ValueError("review output appeared; existing document was preserved")
    print("signed detached review; owner log unchanged; runtime verification and session gates still required")
    return 0


# Independent research-manifest codec. This copy never imports application code.

@dataclass(frozen=True, kw_only=True)
class _bf_PayloadReference:
    schema: int
    manifest_sha256: str
    manifest_bytes: int
    payload_sha256: str
    payload_bytes: int
    policy_sha256: str

    def __post_init__(self):
        _bf__need(type(self.schema) is int and self.schema == 1
            and all(_bf__hash(value) for value in (self.manifest_sha256, self.payload_sha256, self.policy_sha256))
            and type(self.manifest_bytes) is int and 0 < self.manifest_bytes <= 1048576
            and type(self.payload_bytes) is int and 0 < self.payload_bytes <= 67108864)

_bf__HASH = re.compile('[0-9a-f]{64}')
_bf__ID = re.compile('[A-Za-z][A-Za-z0-9_.:-]{0,95}')
_bf__LOGICAL = re.compile('[a-z][a-z0-9_-]{0,63}')
_bf__EMPTY_SHA = hashlib.sha256(b'').hexdigest()
_bf__RAW_DOMAIN = b'tradegen-research-raw-archive/1\x00'
_bf__VERIFIED_DOMAIN = b'tradegen-research-bundle/1\x00'
_bf__ROLES = frozenset({'plan', 'profile', 'registration_commitment', 'capture', 'incomplete_capture', 'source_receipts', 'program_source', 'capture_source_manifest', 'source_file', 'prior_research', 'report', 'other_input', 'evaluation_record'})
_bf__STATUSES = frozenset({'COLLECTED', 'MISSING', 'REFUSED', 'CHANGED', 'LIMIT_EXCEEDED', 'NOT_READ'})
_bf__REVISIONS = frozenset({'forward-paper-v1', 'forward-paper-carry-v2'})
_bf__SOURCES = frozenset({'prospective_paper_capture', 'synthetic', 'retrospective_replay'})
_bf__SINGLE_ROLES = frozenset({'plan', 'profile', 'registration_commitment', 'source_receipts', 'program_source', 'capture_source_manifest', 'prior_research', 'evaluation_record'})
_bf__RESERVED = frozenset({'con', 'prn', 'aux', 'nul', 'conin$', 'conout$'} | {prefix + digit for prefix in ('com', 'lpt') for digit in '123456789¹²³'})

class _bf_BundleFormatError(ValueError):
    """Fixed diagnostics only; no supplied names, values or OS messages."""

def _bf__need(value, code='BUNDLE_FORMAT_INVALID'):
    if not value:
        raise _bf_BundleFormatError(code)

def _bf__hash(value):
    return type(value) is str and _bf__HASH.fullmatch(value) is not None

def _bf__identifier(value):
    return type(value) is str and _bf__ID.fullmatch(value) is not None

def _bf__logical(value):
    return type(value) is str and _bf__LOGICAL.fullmatch(value) is not None

def _bf__name(value, maximum=1024):
    _bf__need(type(value) is str and value and ('\x00' not in value))
    try:
        _bf__need(len(value.encode('utf-8')) <= maximum, 'BUNDLE_RESOURCE_LIMIT')
    except UnicodeError:
        raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None

def _bf__stamp(value):
    try:
        _bf__need(type(value) is datetime and value.utcoffset() is not None)
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError, TypeError, OverflowError):
        raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None

def _bf__parse_time(value):
    _bf__need(type(value) is str and len(value) == 32)
    try:
        stamp = datetime.fromisoformat(value)
        _bf__need(_bf__stamp(stamp) == value)
        return stamp
    except (ValueError, TypeError, OverflowError):
        raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_BundleLimits:
    max_manifest_bytes: int = 4 * 1024 * 1024
    max_files: int = 2048
    max_file_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_candidates: int = 128
    max_name_bytes: int = 1024

    def __post_init__(self):
        ceilings = (4 * 1024 * 1024, 2048, 64 * 1024 * 1024, 512 * 1024 * 1024, 128, 1024)
        for field, ceiling in zip(fields(type(self)), ceilings):
            value = getattr(self, field.name)
            _bf__need(type(value) is int and 0 < value <= ceiling, 'BUNDLE_LIMITS_INVALID')
_bf_DEFAULT_LIMITS = _bf_BundleLimits()

def _bf__limits(value):
    _bf__need(type(value) is _bf_BundleLimits, 'BUNDLE_LIMITS_INVALID')
    try:
        value.__post_init__()
    except (AttributeError, TypeError):
        raise _bf_BundleFormatError('BUNDLE_LIMITS_INVALID') from None
    return value

def _bf__metadata(value):
    _bf__name(value.original_name)
    _bf__need(type(value.role) is str and value.role in _bf__ROLES)
    _bf__need(value.study_id is None or _bf__identifier(value.study_id))
    _bf__need(type(value.required) is bool)
    if value.source_name is not None:
        _bf__need(value.role == 'source_file')
        _bf__name(value.source_name)

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_BundleFile:
    logical_id: str
    original_name: str
    source_name: str | None
    role: str
    study_id: str | None
    required: bool
    byte_count: int
    sha256: str
    payload_ref: _bf_PayloadReference | None

    def __post_init__(self):
        _bf__need(_bf__logical(self.logical_id))
        _bf__metadata(self)
        _bf__need(type(self.byte_count) is int and 0 <= self.byte_count)
        _bf__need(self.byte_count <= _bf_DEFAULT_LIMITS.max_file_bytes, 'BUNDLE_RESOURCE_LIMIT')
        _bf__need(_bf__hash(self.sha256))
        if self.byte_count == 0:
            _bf__need(self.sha256 == _bf__EMPTY_SHA and self.payload_ref is None)
        else:
            _bf__need(type(self.payload_ref) is _bf_PayloadReference)
            try:
                self.payload_ref.__post_init__()
            except (ValueError, TypeError, AttributeError):
                raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None
            _bf__need(self.payload_ref.payload_bytes == self.byte_count and self.payload_ref.payload_sha256 == self.sha256)

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_InputObservation:
    observation_id: str
    original_name: str
    source_name: str | None
    role: str
    study_id: str | None
    required: bool
    status: str
    logical_id: str | None

    def __post_init__(self):
        _bf__need(_bf__logical(self.observation_id))
        _bf__metadata(self)
        _bf__need(type(self.status) is str and self.status in _bf__STATUSES)
        _bf__need(_bf__logical(self.logical_id) if self.status == 'COLLECTED' else self.logical_id is None)

def _bf__ordered(values, cls, attribute, maximum):
    _bf__need(type(values) is tuple)
    _bf__need(len(values) <= maximum, 'BUNDLE_RESOURCE_LIMIT')
    keys = []
    for value in values:
        _bf__need(type(value) is cls)
        value.__post_init__()
        keys.append(getattr(value, attribute))
    _bf__need(keys == sorted(set(keys)))

def _bf__files(manifest, limits):
    _bf__ordered(manifest.files, _bf_BundleFile, 'logical_id', limits.max_files)
    total = 0
    for file in manifest.files:
        _bf__name(file.original_name, limits.max_name_bytes)
        if file.source_name is not None:
            _bf__name(file.source_name, limits.max_name_bytes)
        _bf__need(file.byte_count <= limits.max_file_bytes, 'BUNDLE_RESOURCE_LIMIT')
        total += file.byte_count
        _bf__need(file.payload_ref is None or file.payload_ref.policy_sha256 == manifest.object_policy_sha256)
    _bf__need(total <= limits.max_total_bytes, 'BUNDLE_RESOURCE_LIMIT')

def _bf__base(manifest, kind, limits):
    _bf__need(type(manifest.schema_version) is int and manifest.schema_version == 1)
    _bf__need(type(manifest.kind) is str and manifest.kind == kind)
    _bf__need(all((_bf__identifier(value) for value in (manifest.run_id, manifest.revision_id, manifest.attempt_id))))
    _bf__need(manifest.parent_bundle_sha256 is None or _bf__hash(manifest.parent_bundle_sha256))
    _bf__need(_bf__hash(manifest.storage_policy_sha256) and _bf__hash(manifest.object_policy_sha256))
    _bf__files(manifest, limits)

def _bf__expected(values, limits):
    _bf__need(type(values) is tuple)
    _bf__need(len(values) <= limits.max_candidates, 'BUNDLE_RESOURCE_LIMIT')
    _bf__need(all((_bf__identifier(value) for value in values)) and values == tuple(sorted(set(values))))

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_RawArchiveManifest:
    schema_version: int
    kind: str
    run_id: str
    revision_id: str
    attempt_id: str
    parent_bundle_sha256: str | None
    storage_policy_sha256: str
    object_policy_sha256: str
    expected_candidates: tuple[str, ...] | None
    inventory_complete: bool
    observed_inputs: tuple[_bf_InputObservation, ...]
    files: tuple[_bf_BundleFile, ...]

    def __post_init__(self):
        _bf__raw(self, _bf_DEFAULT_LIMITS)

def _bf__raw(manifest, limits):
    _bf__need(type(manifest) is _bf_RawArchiveManifest)
    _bf__base(manifest, 'RAW_ARCHIVED', limits)
    _bf__need(type(manifest.inventory_complete) is bool)
    if manifest.expected_candidates is not None:
        _bf__expected(manifest.expected_candidates, limits)
    _bf__ordered(manifest.observed_inputs, _bf_InputObservation, 'observation_id', limits.max_files)
    lookup, collected = ({file.logical_id: file for file in manifest.files}, [])
    for row in manifest.observed_inputs:
        _bf__name(row.original_name, limits.max_name_bytes)
        if row.source_name is not None:
            _bf__name(row.source_name, limits.max_name_bytes)
        _bf__need(row.role != 'evaluation_record')
        if row.status == 'COLLECTED':
            _bf__need(row.logical_id in lookup)
            file = lookup[row.logical_id]
            _bf__need(all((getattr(file, name) == getattr(row, name) for name in ('original_name', 'source_name', 'role', 'study_id', 'required'))))
            collected.append(row.logical_id)
    _bf__need(len(collected) == len(set(collected)) and set(collected) == set(lookup))

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_CandidateEvidence:
    study_id: str
    protocol_digest: str
    capture_logical_id: str
    result_digest: str

    def __post_init__(self):
        _bf__need(_bf__identifier(self.study_id) and _bf__logical(self.capture_logical_id) and _bf__hash(self.protocol_digest) and _bf__hash(self.result_digest))

def _bf__safe_relative(name):
    _bf__name(name)
    _bf__need(not any((ord(char) < 32 or ord(char) == 127 for char in name)))
    _bf__need('\\' not in name and ':' not in name)
    parts = name.split('/')
    _bf__need(all((part and part not in ('.', '..') and (not part.endswith(('.', ' '))) and (part.split('.')[0].casefold() not in _bf__RESERVED) and (not any((char in '<>"|?*' for char in part))) for part in parts)))

@dataclass(frozen=True, kw_only=True, slots=True)
class _bf_VerifiedBundleManifest:
    schema_version: int
    kind: str
    run_id: str
    revision_id: str
    attempt_id: str
    parent_bundle_sha256: str | None
    storage_policy_sha256: str
    object_policy_sha256: str
    input_archive_digest: str
    plan_digest: str
    profile_digest: str
    rules_digest: str
    registry_digest: str
    source_digest: str
    family_digest: str
    receipt_audit_digest: str
    evaluator_revision: str
    source_kind_claim: str
    capture_start: datetime
    capture_end: datetime
    evaluated_at: datetime
    candidates: tuple[_bf_CandidateEvidence, ...]
    files: tuple[_bf_BundleFile, ...]

    def __post_init__(self):
        _bf__verified(self, _bf_DEFAULT_LIMITS)

def _bf__complete_files(files, single_roles):
    """Shared metadata eligibility only; no source validation or result issuance."""
    names, by_role = (set(), {})
    for file in files:
        _bf__need(file.role not in ('incomplete_capture', 'other_input'))
        _bf__safe_relative(file.original_name)
        name = file.original_name
        if file.role == 'source_file':
            _bf__need(file.source_name is not None)
            _bf__safe_relative(file.source_name)
            name = file.source_name
        key = (file.role, unicodedata.normalize('NFC', name).casefold())
        _bf__need(key not in names)
        names.add(key)
        by_role.setdefault(file.role, []).append(file)
    for role in single_roles:
        rows = by_role.get(role, [])
        _bf__need(len(rows) == 1 and rows[0].required and (rows[0].study_id is None) and (rows[0].byte_count > 0))
    _bf__need(by_role.get('source_file') and all((file.required and file.study_id is None and (file.byte_count > 0) for file in by_role['source_file'])))
    return by_role

def _bf__verified(manifest, limits):
    _bf__need(type(manifest) is _bf_VerifiedBundleManifest)
    _bf__base(manifest, 'VERIFIED_UNAPPROVED', limits)
    _bf__need(all((_bf__hash(getattr(manifest, name)) for name in ('input_archive_digest', 'plan_digest', 'profile_digest', 'rules_digest', 'registry_digest', 'source_digest', 'family_digest', 'receipt_audit_digest'))))
    _bf__need(type(manifest.evaluator_revision) is str and manifest.evaluator_revision in _bf__REVISIONS)
    _bf__need(type(manifest.source_kind_claim) is str and manifest.source_kind_claim in _bf__SOURCES)
    for instant in (manifest.capture_start, manifest.capture_end, manifest.evaluated_at):
        _bf__stamp(instant)
    _bf__need(manifest.capture_start < manifest.capture_end <= manifest.evaluated_at)
    _bf__ordered(manifest.candidates, _bf_CandidateEvidence, 'study_id', limits.max_candidates)
    _bf__need(manifest.candidates)
    by_role = _bf__complete_files(manifest.files, _bf__SINGLE_ROLES)
    captures = {file.logical_id: file for file in by_role.get('capture', [])}
    _bf__need(len(captures) == len(manifest.candidates))
    _bf__need({candidate.capture_logical_id for candidate in manifest.candidates} == set(captures))
    for candidate in manifest.candidates:
        file = captures[candidate.capture_logical_id]
        _bf__need(file.study_id == candidate.study_id and file.required and (file.byte_count > 0))

def _bf__plain(value):
    if type(value) is datetime:
        return _bf__stamp(value)
    if type(value) is tuple:
        return [_bf__plain(item) for item in value]
    if type(value) in (_bf_BundleFile, _bf_InputObservation, _bf_CandidateEvidence, _bf_PayloadReference, _bf_RawArchiveManifest, _bf_VerifiedBundleManifest):
        return {field.name: _bf__plain(getattr(value, field.name)) for field in fields(type(value))}
    _bf__need(value is None or type(value) in (str, int, bool))
    return value

def _bf__encode(manifest, validator, limits):
    limits = _bf__limits(limits)
    try:
        validator(manifest, limits)
        raw = json.dumps(_bf__plain(manifest), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    except _bf_BundleFormatError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError, UnicodeError):
        raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None
    _bf__need(len(raw) <= limits.max_manifest_bytes, 'BUNDLE_RESOURCE_LIMIT')
    return raw

def _bf_raw_archive_bytes(manifest, *, limits=_bf_DEFAULT_LIMITS):
    return _bf__encode(manifest, _bf__raw, limits)

def _bf_verified_bundle_bytes(manifest, *, limits=_bf_DEFAULT_LIMITS):
    return _bf__encode(manifest, _bf__verified, limits)

def _bf_raw_archive_digest(manifest, *, limits=_bf_DEFAULT_LIMITS):
    return hashlib.sha256(_bf__RAW_DOMAIN + _bf_raw_archive_bytes(manifest, limits=limits)).hexdigest()

def _bf_verified_bundle_digest(manifest, *, limits=_bf_DEFAULT_LIMITS):
    return hashlib.sha256(_bf__VERIFIED_DOMAIN + _bf_verified_bundle_bytes(manifest, limits=limits)).hexdigest()

def _bf__scan(raw):
    depth, nodes, quoted, escaped = (0, 0, False, False)
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            nodes += 1
            _bf__need(depth <= 12)
        elif char in (93, 125):
            depth -= 1
            _bf__need(depth >= 0)
        elif char in (44, 58):
            nodes += 1
        _bf__need(nodes <= 200000, 'BUNDLE_RESOURCE_LIMIT')
    _bf__need(depth == 0 and (not quoted))

def _bf__pairs(pairs):
    result = {}
    for key, value in pairs:
        _bf__need(key not in result)
        result[key] = value
    return result

def _bf__integer(value):
    _bf__need(len(value) <= 16)
    return int(value)

def _bf__number(value):
    raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID')

def _bf__keys(body, cls):
    _bf__need(type(body) is dict and set(body) == {field.name for field in fields(cls)})

def _bf__file(body):
    _bf__keys(body, _bf_BundleFile)
    reference = body['payload_ref']
    if reference is not None:
        _bf__keys(reference, _bf_PayloadReference)
        reference = _bf_PayloadReference(**reference)
    return _bf_BundleFile(**body | {'payload_ref': reference})

def _bf__parse(raw, cls, encoder, limits):
    limits = _bf__limits(limits)
    _bf__need(type(raw) is bytes and raw)
    _bf__need(len(raw) <= limits.max_manifest_bytes, 'BUNDLE_RESOURCE_LIMIT')
    _bf__scan(raw)
    try:
        body = json.loads(raw.decode('ascii'), object_pairs_hook=_bf__pairs, parse_int=_bf__integer, parse_float=_bf__number, parse_constant=_bf__number)
        _bf__keys(body, cls)
        _bf__need(type(body['files']) is list)
        _bf__need(len(body['files']) <= limits.max_files, 'BUNDLE_RESOURCE_LIMIT')
        body['files'] = tuple((_bf__file(file) for file in body['files']))
        if cls is _bf_RawArchiveManifest:
            _bf__need(type(body['observed_inputs']) is list)
            _bf__need(len(body['observed_inputs']) <= limits.max_files, 'BUNDLE_RESOURCE_LIMIT')
            for item in body['observed_inputs']:
                _bf__keys(item, _bf_InputObservation)
            body['observed_inputs'] = tuple((_bf_InputObservation(**row) for row in body['observed_inputs']))
            if body['expected_candidates'] is not None:
                _bf__need(type(body['expected_candidates']) is list)
                body['expected_candidates'] = tuple(body['expected_candidates'])
        else:
            _bf__need(type(body['candidates']) is list)
            _bf__need(len(body['candidates']) <= limits.max_candidates, 'BUNDLE_RESOURCE_LIMIT')
            for item in body['candidates']:
                _bf__keys(item, _bf_CandidateEvidence)
            body['candidates'] = tuple((_bf_CandidateEvidence(**row) for row in body['candidates']))
            for name in ('capture_start', 'capture_end', 'evaluated_at'):
                body[name] = _bf__parse_time(body[name])
        manifest = cls(**body)
        _bf__need(encoder(manifest, limits=limits) == raw)
        return manifest
    except _bf_BundleFormatError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, UnicodeError, RecursionError, KeyError):
        raise _bf_BundleFormatError('BUNDLE_FORMAT_INVALID') from None

def _bf_parse_raw_archive(raw: bytes, *, limits=_bf_DEFAULT_LIMITS):
    return _bf__parse(raw, _bf_RawArchiveManifest, _bf_raw_archive_bytes, limits)

def _bf_parse_verified_bundle(raw: bytes, *, limits=_bf_DEFAULT_LIMITS):
    return _bf__parse(raw, _bf_VerifiedBundleManifest, _bf_verified_bundle_bytes, limits)

def _bf_validate_complete_inputs(raw_archive, *, limits=_bf_DEFAULT_LIMITS):
    """Preflight every original's metadata before actual evaluation.

    This pure check proves neither source authenticity nor semantic validity.
    It does not construct result digests or a candidate evaluation document.
    Malformed/incomplete originals remain representable by the raw codec.
    """
    _bf_raw_archive_bytes(raw_archive, limits=limits)
    _bf__need(raw_archive.inventory_complete and raw_archive.expected_candidates and all((row.status == 'COLLECTED' for row in raw_archive.observed_inputs)), 'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    roles = _bf__complete_files(raw_archive.files, _bf__SINGLE_ROLES - {'evaluation_record'})
    captures = roles.get('capture', [])
    _bf__need(len(captures) == len(raw_archive.expected_candidates) and {file.study_id for file in captures} == set(raw_archive.expected_candidates), 'BUNDLE_CANDIDATE_SET_MISMATCH')
    _bf__need(all((file.required and file.byte_count > 0 for file in captures)))

def _bf_validate_verified_inputs(raw_archive, verified, *, limits=_bf_DEFAULT_LIMITS):
    """Check exact archival linkage only; never issue research or approval."""
    _bf_raw_archive_bytes(raw_archive, limits=limits)
    _bf_verified_bundle_bytes(verified, limits=limits)
    _bf__need(_bf_raw_archive_digest(raw_archive, limits=limits) == verified.input_archive_digest, 'BUNDLE_INPUT_ARCHIVE_MISMATCH')
    _bf__need(all((getattr(raw_archive, name) == getattr(verified, name) for name in ('run_id', 'attempt_id', 'storage_policy_sha256', 'object_policy_sha256'))) and raw_archive.revision_id != verified.revision_id, 'BUNDLE_INPUT_ARCHIVE_MISMATCH')
    _bf__need(raw_archive.inventory_complete and raw_archive.expected_candidates and all((row.status == 'COLLECTED' for row in raw_archive.observed_inputs)), 'BUNDLE_INPUT_ARCHIVE_INCOMPLETE')
    _bf__need(raw_archive.expected_candidates == tuple((row.study_id for row in verified.candidates)), 'BUNDLE_CANDIDATE_SET_MISMATCH')
    originals = {file.logical_id: file for file in raw_archive.files}
    derived = {file.logical_id: file for file in verified.files}
    _bf__need(set(originals) <= set(derived), 'BUNDLE_INPUT_FILE_MISMATCH')
    for name, file in originals.items():
        _bf__need(_bf__plain(file) == _bf__plain(derived[name]), 'BUNDLE_INPUT_FILE_MISMATCH')
    _bf__need(all((file.role in ('evaluation_record', 'report') for name, file in derived.items() if name not in originals)), 'BUNDLE_INPUT_FILE_MISMATCH')
    _bf__need({file.study_id for file in raw_archive.files if file.role == 'capture'} == set(raw_archive.expected_candidates), 'BUNDLE_CANDIDATE_SET_MISMATCH')

def _bf_validate_payloads(manifest, payloads: Mapping[str, bytes], *, limits=_bf_DEFAULT_LIMITS):
    """Check original bytes; object availability and semantic truth are separate."""
    if type(manifest) is _bf_RawArchiveManifest:
        _bf_raw_archive_bytes(manifest, limits=limits)
    else:
        _bf_verified_bundle_bytes(manifest, limits=limits)
    _bf__need(isinstance(payloads, Mapping), 'BUNDLE_PAYLOAD_MISMATCH')
    expected = {file.logical_id: file for file in manifest.files}
    _bf__need(len(payloads) == len(expected), 'BUNDLE_PAYLOAD_MISMATCH')
    seen = set()
    for name, raw in payloads.items():
        _bf__need(type(name) is str and name in expected and (name not in seen) and (type(raw) is bytes), 'BUNDLE_PAYLOAD_MISMATCH')
        seen.add(name)
        file = expected[name]
        _bf__need(len(raw) == file.byte_count and hashlib.sha256(raw).hexdigest() == file.sha256, 'BUNDLE_PAYLOAD_MISMATCH')
    _bf__need(seen == set(expected), 'BUNDLE_PAYLOAD_MISMATCH')


# Independent archive-attestation codec; no runtime application import.
_ba_PURPOSE = 'research_archive_manifest_attestation'
_ba_SCOPE = 'archive_manifest_identity'
_ba_REQUEST_DOMAIN = b'tradegen-research-archive-attestation-request/1\n'
_ba_SIGNING_DOMAIN = b'tradegen-research-archive-attestation/1\n'
_ba_FILE_SET_DOMAIN = b'tradegen-research-archive-file-set/1\n'
_ba_DOCUMENT_DOMAIN = b'tradegen-research-archive-attestation-document/1\n'
_ba_MAX_REQUEST_BYTES = 12 * 1024 * 1024
_ba_MAX_DOCUMENT_BYTES = 13 * 1024 * 1024
_ba_MAX_VALIDITY_SECONDS = 86400
_ba_APPROVED_CHECKS = ('exact_manifest_and_entire_file_inventory', 'all_available_original_bytes_match', 'raw_and_verified_link_exact', 'raw_incomplete_and_failure_statuses_visible', 'archive_only_scope_and_expiry_reviewed')
_ba__HASH = re.compile('[0-9a-f]{64}')
_ba__LOGICAL = re.compile('[a-z][a-z0-9_-]{0,63}')
_ba__EMPTY_SHA = hashlib.sha256(b'').hexdigest()
_ba__REQUEST_KEYS = frozenset({'schema_version', 'artifact_kind', 'purpose', 'scope', 'requested_at', 'expires_at', 'deployment_code_hash', 'bundle_kind', 'bundle_digest', 'input_archive_digest', 'raw_manifest_sha256', 'verified_manifest_sha256', 'raw_manifest', 'verified_manifest', 'payload_files', 'file_set_sha256', 'request_sha256'})
_ba__BODY_KEYS = frozenset({'schema_version', 'purpose', 'scope', 'request', 'deployment_code_hash', 'owner_fingerprint', 'reviewer_id', 'issued_at', 'expires_at', 'approved_checks'})
_ba__FILE_KEYS = frozenset({'logical_id', 'byte_count', 'sha256'})

class _ba_ArchiveAttestationError(ValueError):
    """Fixed codes only, never original data, paths or external error text."""

def _ba__need(value, code='ARCHIVE_ATTESTATION_FORMAT_INVALID'):
    if not value:
        raise _ba_ArchiveAttestationError(code)

def _ba__hash(value):
    return type(value) is str and _ba__HASH.fullmatch(value) is not None

def _ba__stamp(value):
    try:
        _ba__need(type(value) is datetime and value.utcoffset() is not None, 'ARCHIVE_ATTESTATION_TIME_INVALID')
        return value.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (ValueError, TypeError, OverflowError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_TIME_INVALID') from None

def _ba__time(value):
    _ba__need(type(value) is str and len(value) == 32, 'ARCHIVE_ATTESTATION_TIME_INVALID')
    try:
        instant = datetime.fromisoformat(value)
        _ba__need(_ba__stamp(instant) == value, 'ARCHIVE_ATTESTATION_TIME_INVALID')
        return instant
    except (ValueError, TypeError, OverflowError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_TIME_INVALID') from None

def _ba__fingerprint(value):
    return type(value) is str and value.startswith('SHA256:') and _ba__hash(value[7:])

def _ba__budget(value, maximum):
    pending, nodes, characters = ([(value, 0)], 0, 0)
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _ba__need(nodes <= 500000 and depth <= 16, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
        if type(item) is dict:
            _ba__need(len(item) <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
            for key, child in item.items():
                _ba__need(type(key) is str)
                characters += len(key)
                pending.append((child, depth + 1))
        elif type(item) is list:
            _ba__need(len(item) <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
            pending.extend(((child, depth + 1) for child in item))
        elif type(item) is str:
            characters += len(item)
        elif type(item) is int:
            _ba__need(-10 ** 15 < item < 10 ** 15)
        else:
            _ba__need(item is None or type(item) is bool)
        _ba__need(characters <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')

def _ba__canonical(value, maximum):
    _ba__budget(value, maximum)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID') from None
    _ba__need(len(raw) <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    return raw

def _ba__scan(raw):
    depth, nodes, quoted, escaped = (0, 0, False, False)
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            nodes += 1
            _ba__need(depth <= 16, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
        elif char in (93, 125):
            depth -= 1
            _ba__need(depth >= 0)
        elif char in (44, 58):
            nodes += 1
        _ba__need(nodes <= 500000, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    _ba__need(depth == 0 and (not quoted))

def _ba__pairs(pairs):
    body = {}
    for key, value in pairs:
        _ba__need(key not in body)
        body[key] = value
    return body

def _ba__integer(value):
    _ba__need(len(value) <= 16)
    return int(value)

def _ba__number(value):
    raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID')

def _ba__decode(raw, maximum):
    _ba__need(type(raw) is bytes and raw)
    _ba__need(len(raw) <= maximum, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    _ba__scan(raw)
    try:
        body = json.loads(raw.decode('ascii'), object_pairs_hook=_ba__pairs, parse_int=_ba__integer, parse_float=_ba__number, parse_constant=_ba__number)
    except _ba_ArchiveAttestationError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_FORMAT_INVALID') from None
    _ba__need(_ba__canonical(body, maximum) == raw)
    return body

def _ba__clone(body, maximum):
    return _ba__decode(_ba__canonical(body, maximum), maximum)

def _ba_payload_filename(logical_id: str) -> str:
    _ba__need(type(logical_id) is str and _ba__LOGICAL.fullmatch(logical_id) is not None, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    return 'p-' + logical_id + '.bin'

def _ba_file_set_digest(payload_files: list[dict]) -> str:
    _ba__need(type(payload_files) is list, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    _ba__need(len(payload_files) <= 2048, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    identifiers, total = ([], 0)
    for row in payload_files:
        _ba__need(type(row) is dict and set(row) == _ba__FILE_KEYS, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        _ba_payload_filename(row['logical_id'])
        _ba__need(type(row['byte_count']) is int and 0 <= row['byte_count'] <= 64 * 1024 * 1024 and _ba__hash(row['sha256']), 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        _ba__need(row['byte_count'] != 0 or row['sha256'] == _ba__EMPTY_SHA, 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
        identifiers.append(row['logical_id'])
        total += row['byte_count']
    _ba__need(identifiers == sorted(set(identifiers)), 'ARCHIVE_ATTESTATION_FILE_SET_INVALID')
    _ba__need(total <= 512 * 1024 * 1024, 'ARCHIVE_ATTESTATION_RESOURCE_LIMIT')
    return hashlib.sha256(_ba_FILE_SET_DOMAIN + _ba__canonical(payload_files, _ba_MAX_REQUEST_BYTES)).hexdigest()

def _ba__manifests(raw_body, verified_body):
    try:
        _ba__need(type(raw_body) is dict)
        raw_bytes = _ba__canonical(raw_body, _bf_DEFAULT_LIMITS.max_manifest_bytes)
        raw = _bf_parse_raw_archive(raw_bytes)
        verified, verified_bytes = (None, None)
        if verified_body is not None:
            _ba__need(type(verified_body) is dict)
            verified_bytes = _ba__canonical(verified_body, _bf_DEFAULT_LIMITS.max_manifest_bytes)
            verified = _bf_parse_verified_bundle(verified_bytes)
            _bf_validate_verified_inputs(raw, verified)
        return (raw, raw_bytes, verified, verified_bytes)
    except _bf_BundleFormatError as exc:
        code = ('ARCHIVE_ATTESTATION_RESOURCE_LIMIT' if str(exc) == 'BUNDLE_RESOURCE_LIMIT'
                else 'ARCHIVE_ATTESTATION_MANIFEST_INVALID')
        raise _ba_ArchiveAttestationError(code) from None

def _ba__request_hash(body):
    unsigned = {key: value for key, value in body.items() if key != 'request_sha256'}
    return hashlib.sha256(_ba_REQUEST_DOMAIN + _ba__canonical(unsigned, _ba_MAX_REQUEST_BYTES)).hexdigest()

def _ba__validate_request(request):
    _ba__need(type(request) is dict and set(request) == _ba__REQUEST_KEYS)
    _ba__need(type(request['schema_version']) is int and request['schema_version'] == 1)
    for key, expected in (('artifact_kind', 'unsigned_research_archive_attestation_request'), ('purpose', _ba_PURPOSE), ('scope', _ba_SCOPE)):
        _ba__need(type(request[key]) is str and request[key] == expected)
    start, end = (_ba__time(request['requested_at']), _ba__time(request['expires_at']))
    _ba__need(start < end and end - start <= timedelta(seconds=_ba_MAX_VALIDITY_SECONDS), 'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    _ba__need(_ba__hash(request['deployment_code_hash']), 'ARCHIVE_ATTESTATION_CODE_BINDING_INVALID')
    raw, raw_bytes, verified, verified_bytes = _ba__manifests(request['raw_manifest'], request['verified_manifest'])
    target = raw if verified is None else verified
    target_digest = _bf_raw_archive_digest(raw) if verified is None else _bf_verified_bundle_digest(verified)
    expected_files = [{'logical_id': file.logical_id, 'byte_count': file.byte_count, 'sha256': file.sha256} for file in target.files]
    _ba__need(type(request['bundle_kind']) is str and request['bundle_kind'] == target.kind and (request['bundle_digest'] == target_digest) and (request['input_archive_digest'] == _bf_raw_archive_digest(raw)) and (request['raw_manifest_sha256'] == hashlib.sha256(raw_bytes).hexdigest()) and (request['verified_manifest_sha256'] == (None if verified_bytes is None else hashlib.sha256(verified_bytes).hexdigest())), 'ARCHIVE_ATTESTATION_MANIFEST_BINDING_MISMATCH')
    if verified is not None:
        _ba__need(start >= verified.evaluated_at, 'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    supplied_digest = _ba_file_set_digest(request['payload_files'])
    _ba__need(_ba__canonical(request['payload_files'], _ba_MAX_REQUEST_BYTES) == _ba__canonical(expected_files, _ba_MAX_REQUEST_BYTES) and request['file_set_sha256'] == supplied_digest, 'ARCHIVE_ATTESTATION_FILE_SET_MISMATCH')
    _ba__need(_ba__hash(request['request_sha256']) and request['request_sha256'] == _ba__request_hash(request), 'ARCHIVE_ATTESTATION_REQUEST_DIGEST_MISMATCH')

def _ba_request_from_manifests(raw_manifest: bytes, verified_manifest: bytes | None, *, requested_at: datetime, expires_at: datetime, deployment_code_hash: str) -> dict:
    """Bind explicit canonical originals; no source authenticity or actual evaluation."""
    try:
        raw = _bf_parse_raw_archive(raw_manifest)
        verified = None if verified_manifest is None else _bf_parse_verified_bundle(verified_manifest)
        if verified is not None:
            _bf_validate_verified_inputs(raw, verified)
    except _bf_BundleFormatError as exc:
        code = ('ARCHIVE_ATTESTATION_RESOURCE_LIMIT' if str(exc) == 'BUNDLE_RESOURCE_LIMIT'
                else 'ARCHIVE_ATTESTATION_MANIFEST_INVALID')
        raise _ba_ArchiveAttestationError(code) from None
    target = raw if verified is None else verified
    files = [{'logical_id': file.logical_id, 'byte_count': file.byte_count, 'sha256': file.sha256} for file in target.files]
    request = {'schema_version': 1, 'artifact_kind': 'unsigned_research_archive_attestation_request', 'purpose': _ba_PURPOSE, 'scope': _ba_SCOPE, 'requested_at': _ba__stamp(requested_at), 'expires_at': _ba__stamp(expires_at), 'deployment_code_hash': deployment_code_hash, 'bundle_kind': target.kind, 'bundle_digest': _bf_raw_archive_digest(raw) if verified is None else _bf_verified_bundle_digest(verified), 'input_archive_digest': _bf_raw_archive_digest(raw), 'raw_manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(), 'verified_manifest_sha256': None if verified_manifest is None else hashlib.sha256(verified_manifest).hexdigest(), 'raw_manifest': _ba__decode(raw_manifest, _bf_DEFAULT_LIMITS.max_manifest_bytes), 'verified_manifest': None if verified_manifest is None else _ba__decode(verified_manifest, _bf_DEFAULT_LIMITS.max_manifest_bytes), 'payload_files': files, 'file_set_sha256': _ba_file_set_digest(files)}
    request['request_sha256'] = _ba__request_hash(request)
    return _ba_parse_archive_request(_ba__canonical(request, _ba_MAX_REQUEST_BYTES))

def _ba_archive_request_bytes(request: dict) -> bytes:
    copied = _ba__clone(request, _ba_MAX_REQUEST_BYTES)
    _ba__validate_request(copied)
    return _ba__canonical(copied, _ba_MAX_REQUEST_BYTES)

def _ba_parse_archive_request(raw: bytes) -> dict:
    request = _ba__decode(raw, _ba_MAX_REQUEST_BYTES)
    _ba__validate_request(request)
    return request

def _ba_archive_request_digest(request: dict) -> str:
    return _ba_parse_archive_request(_ba_archive_request_bytes(request))['request_sha256']

def _ba_validate_request_payloads(request: dict, payloads: Mapping[str, bytes]) -> None:
    request = _ba_parse_archive_request(_ba_archive_request_bytes(request))
    _ba__need(isinstance(payloads, Mapping), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
    expected = {row['logical_id']: row for row in request['payload_files']}
    _ba__need(len(payloads) == len(expected), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
    seen = set()
    for name, raw in payloads.items():
        _ba__need(type(name) is str and name in expected and (name not in seen) and (type(raw) is bytes), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
        row = expected[name]
        _ba__need(len(raw) == row['byte_count'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')
        seen.add(name)
    _ba__need(seen == set(expected), 'ARCHIVE_ATTESTATION_PAYLOAD_MISMATCH')

def _ba__validate_body(body):
    _ba__need(type(body) is dict and set(body) == _ba__BODY_KEYS)
    _ba__need(type(body['schema_version']) is int and body['schema_version'] == 1)
    _ba__need(type(body['purpose']) is str and body['purpose'] == _ba_PURPOSE and (type(body['scope']) is str) and (body['scope'] == _ba_SCOPE))
    _ba__validate_request(body['request'])
    request = body['request']
    _ba__need(_ba__hash(body['deployment_code_hash']) and body['deployment_code_hash'] == request['deployment_code_hash'], 'ARCHIVE_ATTESTATION_CODE_BINDING_INVALID')
    _ba__need(_ba__fingerprint(body['owner_fingerprint']) and type(body['reviewer_id']) is str and (body['reviewer_id'] == 'owner:' + body['owner_fingerprint'][7:]), 'ARCHIVE_ATTESTATION_SIGNER_INVALID')
    issued, expires = (_ba__time(body['issued_at']), _ba__time(body['expires_at']))
    _ba__need(body['expires_at'] == request['expires_at'] and _ba__time(request['requested_at']) <= issued < expires and (expires - issued <= timedelta(seconds=_ba_MAX_VALIDITY_SECONDS)), 'ARCHIVE_ATTESTATION_VALIDITY_INVALID')
    _ba__need(type(body['approved_checks']) is list and body['approved_checks'] == list(_ba_APPROVED_CHECKS), 'ARCHIVE_ATTESTATION_CHECKLIST_INVALID')

def _ba_attestation_body(request: dict, *, owner_fingerprint: str, issued_at: datetime) -> dict:
    copied = _ba_parse_archive_request(_ba_archive_request_bytes(request))
    body = {'schema_version': 1, 'purpose': _ba_PURPOSE, 'scope': _ba_SCOPE, 'request': copied, 'deployment_code_hash': copied['deployment_code_hash'], 'owner_fingerprint': owner_fingerprint, 'reviewer_id': 'owner:' + owner_fingerprint[7:] if type(owner_fingerprint) is str else None, 'issued_at': _ba__stamp(issued_at), 'expires_at': copied['expires_at'], 'approved_checks': list(_ba_APPROVED_CHECKS)}
    _ba__validate_body(body)
    return body

def _ba_attestation_signing_bytes(body: dict) -> bytes:
    copied = _ba__clone(body, _ba_MAX_DOCUMENT_BYTES)
    _ba__validate_body(copied)
    return _ba_SIGNING_DOMAIN + _ba__canonical(copied, _ba_MAX_DOCUMENT_BYTES)

def _ba_attestation_document_bytes(body: dict, signature: bytes) -> bytes:
    copied = _ba__clone(body, _ba_MAX_DOCUMENT_BYTES)
    _ba__validate_body(copied)
    _ba__need(type(signature) is bytes and len(signature) == 64, 'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    return _ba__canonical({'body': copied, 'signature_b64': base64.b64encode(signature).decode('ascii')}, _ba_MAX_DOCUMENT_BYTES)

def _ba_parse_attestation_document(raw: bytes) -> dict:
    envelope = _ba__decode(raw, _ba_MAX_DOCUMENT_BYTES)
    _ba__need(type(envelope) is dict and set(envelope) == {'body', 'signature_b64'})
    _ba__validate_body(envelope['body'])
    encoded = envelope['signature_b64']
    _ba__need(type(encoded) is str and len(encoded) == 88, 'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_SIGNATURE_INVALID') from None
    _ba__need(len(signature) == 64 and base64.b64encode(signature).decode('ascii') == encoded, 'ARCHIVE_ATTESTATION_SIGNATURE_INVALID')
    return envelope

def _ba_attestation_document_digest(raw: bytes) -> str:
    _ba_parse_attestation_document(raw)
    return hashlib.sha256(_ba_DOCUMENT_DOMAIN + raw).hexdigest()

def _ba_verify_attestation_signature(raw: bytes, *, public_key_raw: bytes) -> dict:
    """Verify exact bytes with a supplied key, NOT that key's trust or current use."""
    envelope = _ba_parse_attestation_document(raw)
    _ba__need(type(public_key_raw) is bytes and len(public_key_raw) == 32, 'ARCHIVE_ATTESTATION_PUBLIC_KEY_INVALID')
    body = envelope['body']
    _ba__need(body['owner_fingerprint'] == 'SHA256:' + hashlib.sha256(public_key_raw).hexdigest(), 'ARCHIVE_ATTESTATION_KEY_MISMATCH')
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(public_key_raw).verify(base64.b64decode(envelope['signature_b64']), _ba_attestation_signing_bytes(body))
    except (InvalidSignature, ValueError, TypeError):
        raise _ba_ArchiveAttestationError('ARCHIVE_ATTESTATION_SIGNATURE_UNVERIFIED') from None
    return body


# Independent native Windows directory pins; native acceptance remains platform-specific.
class _bw_WindowsPinError(ValueError):
    """Fixed code; never an OS message, path, or private file data."""
_bw__CODE = 'BUNDLE_PACKET_WINDOWS_PIN_REFUSED'
_bw__UNSUPPORTED = 'BUNDLE_PACKET_WINDOWS_PIN_UNSUPPORTED'
_bw__DRIVE = re.compile('[A-Za-z]:')
_bw__DIRECTORY = 16
_bw__REFUSED_ATTRIBUTES = 1024 | 4096 | 262144 | 4194304
_bw__MAX_CHARS = 32767

def _bw__need(condition, code=_bw__CODE):
    if not condition:
        raise _bw_WindowsPinError(code)

def _bw__lexical_path(value):
    _bw__need(hasattr(ntpath, 'splitroot') and hasattr(ntpath, 'isreserved'), _bw__UNSUPPORTED)
    _bw__need(type(value) is str and 0 < len(value) <= _bw__MAX_CHARS and ('\x00' not in value))
    normalized = value.replace('/', '\\')
    drive, root, tail = ntpath.splitroot(normalized)
    _bw__need(_bw__DRIVE.fullmatch(drive) is not None and root == '\\')
    parts = tail.split('\\') if tail else []
    _bw__need(all((part and part not in ('.', '..') and (not ntpath.isreserved(part)) for part in parts)))
    return drive.upper() + root + '\\'.join(parts)

def _bw__final_path(value):
    _bw__need(type(value) is str and value.startswith('\\\\?\\'))
    return _bw__lexical_path(value[4:])

@dataclass(frozen=True, kw_only=True)
class _bw_DirectoryInformation:
    attributes: int
    volume_serial: int
    file_index: int

    @property
    def identity(self):
        _bw__need(type(self.attributes) is int and self.attributes >= 0 and self.attributes & _bw__DIRECTORY and (not self.attributes & _bw__REFUSED_ATTRIBUTES))
        _bw__need(type(self.volume_serial) is int and 0 <= self.volume_serial < 2 ** 32 and (type(self.file_index) is int) and (0 < self.file_index < 2 ** 64))
        return (self.volume_serial, self.file_index)

class _bw_NativeDirectoryAPI:
    """Small injectable seam; fake APIs must emulate these four methods.

    The object is created only for the explicit Windows operation. No Windows
    DLL is loaded by importing this draft, and no app module is imported here.
    """

    def __init__(self):
        _bw__need(os.name == 'nt', _bw__UNSUPPORTED)
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [('low', wintypes.DWORD), ('high', wintypes.DWORD)]

        class HandleInformation(ctypes.Structure):
            _fields_ = [('attributes', wintypes.DWORD), ('created', FileTime), ('accessed', FileTime), ('written', FileTime), ('volume', wintypes.DWORD), ('size_high', wintypes.DWORD), ('size_low', wintypes.DWORD), ('links', wintypes.DWORD), ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]
        self._ctypes, self._info_type = (ctypes, HandleInformation)
        self._kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self._kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(HandleInformation)]
        self._kernel.GetFileInformationByHandle.restype = wintypes.BOOL
        self._kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        self._kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def open_directory(self, path):
        handle = self._kernel.CreateFileW(path, 128, 1, None, 3, 33554432 | 2097152, None)
        _bw__need(handle is not None and handle != self._ctypes.c_void_p(-1).value)
        return handle

    def information(self, handle):
        info = self._info_type()
        _bw__need(bool(self._kernel.GetFileInformationByHandle(handle, self._ctypes.byref(info))))
        return _bw_DirectoryInformation(attributes=int(info.attributes), volume_serial=int(info.volume), file_index=int(info.index_high) << 32 | int(info.index_low))

    def final_path(self, handle):
        buffer = self._ctypes.create_unicode_buffer(_bw__MAX_CHARS + 2)
        size = self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        _bw__need(0 < size < len(buffer))
        return buffer.value

    def close(self, handle):
        _bw__need(bool(self._kernel.CloseHandle(handle)))

class _bw_WindowsDirectoryPin:

    def __init__(self, api, rows):
        self._api, self._rows, self._closed = (api, tuple(rows), False)
        self.root_handle = rows[-1][1]
        self.identity = rows[-1][2]
        self.path = rows[-1][0]

    def check(self):
        _bw__need(not self._closed)
        for path, handle, identity in self._rows:
            current = self._api.information(handle)
            _bw__need(type(current) is _bw_DirectoryInformation and current.identity == identity)
            _bw__need(ntpath.normcase(_bw__final_path(self._api.final_path(handle))) == ntpath.normcase(path))

@contextmanager
def _bw__held_windows_directory(path, *, api=None):
    """Retain every native ancestor/root handle, or refuse without weaker fallback.

    `api` is a dependency-injection seam for hermetic contract tests, never a
    serialized input or an application-controlled trust flag.
    """
    path = _bw__lexical_path(path)
    try:
        native = _bw_NativeDirectoryAPI() if api is None else api
    except _bw_WindowsPinError:
        raise
    except (OSError, AttributeError, TypeError, RuntimeError):
        raise _bw_WindowsPinError(_bw__UNSUPPORTED) from None
    rows, handles, pin = ([], [], None)
    drive, root, tail = ntpath.splitroot(path)
    prefixes = [drive + root]
    for part in tail.split('\\') if tail else ():
        prefixes.append(ntpath.join(prefixes[-1], part))
    try:
        for prefix in prefixes:
            handle = native.open_directory(prefix)
            handles.append(handle)
            info = native.information(handle)
            _bw__need(type(info) is _bw_DirectoryInformation)
            identity = info.identity
            _bw__need(ntpath.normcase(_bw__final_path(native.final_path(handle))) == ntpath.normcase(prefix))
            rows.append((prefix, handle, identity))
        pin = _bw_WindowsDirectoryPin(native, rows)
        pin.check()
        try:
            yield pin
        finally:
            pin.check()
    except _bw_WindowsPinError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError):
        raise _bw_WindowsPinError(_bw__CODE) from None
    finally:
        if pin is not None:
            pin._closed = True
        close_failed = False
        for handle in reversed(handles):
            try:
                native.close(handle)
            except Exception:
                close_failed = True
        if close_failed:
            raise _bw_WindowsPinError(_bw__CODE) from None

class _bw__WindowsPinContext:
    """I/O-free construction; native pins exist only between enter and exit."""

    def __init__(self, path, *, api=None):
        self._context = _bw__held_windows_directory(path, api=api)
        self._pin = None
        self._used = False

    def __enter__(self):
        _bw__need(not self._used)
        self._used = True
        self._pin = self._context.__enter__()
        return self

    def check(self):
        _bw__need(self._pin is not None)
        self._pin.check()

    @property
    def root_handle(self):
        self.check()
        return self._pin.root_handle

    @property
    def identity(self):
        self.check()
        return self._pin.identity

    @property
    def path(self):
        self.check()
        return self._pin.path

    def __exit__(self, exc_type, exc, traceback):
        _bw__need(self._pin is not None)
        try:
            return self._context.__exit__(exc_type, exc, traceback)
        finally:
            self._pin = None

def _bw_pin_windows_directory(path, *, api=None):
    """Return an I/O-free context manager exposing enter/check/exit and root identity."""
    return _bw__WindowsPinContext(path, api=api)


def _bundle_identity(info, *, regular=False):
    if (type(info.st_ino) is not int or info.st_ino <= 0 or type(info.st_dev) is not int or info.st_dev < 0
            or getattr(info, 'st_file_attributes', 0) & (0x400 | 0x1000 | 0x00040000 | 0x00400000)
            or (regular and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))):
        raise ValueError('archive packet path identity refused')
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _bundle_directory(path):
    path = _review_path(path)
    if '..' in path.parts or ':' in str(path)[len(path.anchor):]:
        raise ValueError('archive packet directory refused')
    for part in (*reversed(path.parents), path):
        info = os.lstat(part)
        _bundle_identity(info)
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError('archive packet directory refused')
    return path, _bundle_identity(info)


class _BundlePin:
    """Retained directory/ancestor handles for a complete packet operation."""
    def __init__(self, path):
        self.path = Path(path).absolute()
        self.rows, self.native, self.descriptor = [], None, None

    def __enter__(self):
        self.path, _ = _bundle_directory(self.path)
        if os.name == 'nt':
            self.native = _bw_pin_windows_directory(str(self.path))
            self.native.__enter__()
        else:
            if os.open not in os.supports_dir_fd or not hasattr(os, 'O_DIRECTORY') or not hasattr(os, 'O_NOFOLLOW'):
                raise ValueError('archive packet platform cannot pin directories')
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
            try:
                previous = None
                for index, prefix in enumerate((*reversed(self.path.parents), self.path)):
                    fd = os.open(prefix.anchor if index == 0 else prefix.name, flags,
                                 **({} if previous is None else {'dir_fd':previous}))
                    try:
                        identity = _bundle_identity(os.fstat(fd))[:2]
                    except BaseException:
                        os.close(fd)
                        raise
                    self.rows.append((prefix, fd, identity))
                    previous = fd
                self.descriptor = self.rows[-1][1]
            except BaseException:
                self.__exit__(None, None, None)
                raise
        try:
            self.check()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def check(self):
        if self.native is not None:
            self.native.check()
        else:
            if not self.rows:
                raise ValueError('archive directory pin is closed')
            for path, descriptor, identity in self.rows:
                if (_bundle_identity(os.fstat(descriptor))[:2] != identity
                        or _bundle_directory(path)[1][:2] != identity):
                    raise ValueError('archive directory pin changed')

    def stat(self, name):
        self.check()
        return os.lstat(self.path / name) if self.native is not None else os.stat(
            name, dir_fd=self.descriptor, follow_symlinks=False)

    def open(self, name, flags, mode=0o600):
        self.check()
        return (os.open(self.path / name, flags | getattr(os, 'O_NOINHERIT', 0), mode)
                if self.native is not None else os.open(name, flags, mode, dir_fd=self.descriptor))

    def names(self, maximum):
        self.check()
        if self.descriptor is not None:
            os.lseek(self.descriptor, 0, os.SEEK_SET)
        return _bundle_names(self.path if self.descriptor is None else self.descriptor, maximum)

    def __exit__(self, exc_type, exc, traceback):
        try:
            if self.native is not None:
                return self.native.__exit__(exc_type, exc, traceback)
        finally:
            failed = False
            for _, descriptor, _ in reversed(self.rows):
                try:
                    os.close(descriptor)
                except OSError:
                    failed = True
            self.rows = []
            self.descriptor = None
            if failed:
                raise ValueError('archive directory handles did not close cleanly') from None


def _bundle_read(path, maximum, *, hash_only=False, empty=False, parent_pin=None):
    """One bounded original, pinned by opened identity; empty raw evidence is valid."""
    target = _review_path(path)
    if parent_pin is None:
        with _BundlePin(target.parent) as pinned:
            return _bundle_read(target, maximum, hash_only=hash_only, empty=empty, parent_pin=pinned)
    if parent_pin.path != target.parent:
        raise ValueError('archive read directory does not match its pin')
    initial = parent_pin.stat(target.name)
    identity = _bundle_identity(initial, regular=True)
    if not (0 if empty else 1) <= initial.st_size <= maximum:
        raise ValueError('archive packet input size refused')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    descriptor = parent_pin.open(target.name, flags)
    try:
        before = os.fstat(descriptor)
        if _bundle_identity(before, regular=True) != identity:
            raise ValueError('archive packet input replaced before reading')
        chunks, length, digest = [], 0, hashlib.sha256()
        while True:
            chunk = os.read(descriptor, min(65536, maximum - length + 1))
            if not chunk:
                break
            length += len(chunk)
            if length > maximum:
                raise ValueError('archive packet input size refused')
            digest.update(chunk)
            if not hash_only:
                chunks.append(chunk)
        after = _bundle_identity(os.fstat(descriptor), regular=True)
        current = _bundle_identity(parent_pin.stat(target.name), regular=True)
        if identity != after or after != current or length != before.st_size:
            raise ValueError('archive packet input changed while reading')
        value = (length, digest.hexdigest()) if hash_only else b''.join(chunks)
        return value, identity
    finally:
        os.close(descriptor)


def _bundle_names(directory, maximum):
    names = set()
    with os.scandir(directory) as listing:
        for entry in listing:
            if entry.name in names or len(names) >= maximum:
                raise ValueError('archive packet inventory exceeds its bound')
            names.add(entry.name)
    return names


def _bundle_packet(path, *, pins=None):
    root, root_identity = _bundle_directory(path)
    payload_root, payload_identity = _bundle_directory(root / 'payloads')
    if pins is None:
        with _BundlePin(root) as root_pin, _BundlePin(payload_root) as payload_pin:
            return _bundle_packet(root, pins=(root_pin, payload_pin))
    root_pin, payload_pin = pins
    if root_pin.path != root or payload_pin.path != payload_root:
        raise ValueError('archive packet pins do not match the requested directories')
    if root_pin.names(2) != {'request.json', 'payloads'}:
        raise ValueError('archive packet file set differs from the request')
    raw, request_identity = _bundle_read(root / 'request.json', _ba_MAX_REQUEST_BYTES, parent_pin=root_pin)
    request = _ba_parse_archive_request(raw)
    expected = {_ba_payload_filename(row['logical_id']) for row in request['payload_files']}
    if payload_pin.names(2048) != expected:
        raise ValueError('archive packet file set differs from the request')
    snapshot = [('request.json', sha256_hex(raw), request_identity)]
    for row in request['payload_files']:
        name = _ba_payload_filename(row['logical_id'])
        actual, identity = _bundle_read(payload_root / name, 64 * 1024 * 1024,
                                       hash_only=True, empty=True, parent_pin=payload_pin)
        if actual != (row['byte_count'], row['sha256']):
            raise ValueError('archive packet original bytes differ from the manifest')
        snapshot.append(('payloads/' + name, actual, identity))
    if (root_pin.names(2) != {'request.json', 'payloads'}
            or payload_pin.names(2048) != expected
            or _bundle_directory(root) != (root, root_identity)
            or _bundle_directory(payload_root) != (payload_root, payload_identity)):
        raise ValueError('archive packet inventory changed while reading')
    return request, (root_identity, payload_identity, tuple(snapshot))


def _bundle_write_new(path, encoded):
    """Exclusive final create; an interrupted partial file remains unusable evidence."""
    target = _review_path(path)
    with _BundlePin(target.parent) as pin:
        return _bundle_write_pinned(target, encoded, pin)


def _bundle_write_pinned(target, encoded, pin):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = pin.open(target.name, flags)
    try:
        identity = _bundle_identity(os.fstat(descriptor), regular=True)[:2]
        with os.fdopen(descriptor, 'wb', closefd=False) as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        final = _bundle_identity(os.fstat(descriptor), regular=True)
        if final[:2] != identity or final[2] != len(encoded) or _bundle_identity(pin.stat(target.name), regular=True) != final:
            raise ValueError('archive attestation output changed during write')
    finally:
        os.close(descriptor)
    readback, _ = _bundle_read(target, len(encoded), hash_only=True, parent_pin=pin)
    if readback != (len(encoded), sha256_hex(encoded)):
        raise ValueError('archive attestation output readback differs')
    if pin.descriptor is not None:
        os.fsync(pin.descriptor)
    pin.check()


def _confirm_bundle(body):
    print('About to attest the exact archived manifests and all available original files only.')
    print('Raw missing, incomplete and failure records remain visible; this does not validate their research.')
    print('No source authentication, strategy selection, trading, or automatic recovery authority is granted.')
    print(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=True))
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed, stamps = _read_typed(f'Type this code to attest the archive (do not paste): {code}\n> ')
    if not _typed_ok(code, typed, stamps):
        raise ValueError('archive confirmation was not typed exactly; nothing was signed')


def _bundle_verified_head(lines, public):
    """Independent full signature/rotation walk from the current deployment PEM.

    This does not replace the application's separate trusted anchors and sealed
    CurrentOwnerAuthority check. The older generic signer commands are unchanged.
    """
    head = _head(lines)
    if type(public) is not bytes or len(public) != 32:
        raise ValueError('archive current public key is invalid')
    entries = [json.loads(line) for line in lines]
    first = public
    for entry in reversed(entries):
        if entry['kind'] == 'key_rotated':
            if base64.b64decode(entry['data']['new_pubkey_b64']) != first:
                raise ValueError('archive owner key rotation does not reach the current PEM')
            first = base64.b64decode(entry['data']['old_pubkey_b64'])
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    verifier = Ed25519PublicKey.from_public_bytes(first)
    try:
        for entry in entries:
            if entry['kind'] in SCHEMAS:
                verifier.verify(base64.b64decode(entry['sig']), SIG_DOMAIN + entry['row_sha256'].encode('ascii'))
            if entry['kind'] == 'key_rotated':
                verifier = Ed25519PublicKey.from_public_bytes(base64.b64decode(entry['data']['new_pubkey_b64']))
    except (InvalidSignature, ValueError, TypeError):
        raise ValueError('archive owner log contains an invalid signature') from None
    return head


def _bundle_code_approval_at(approvals, at):
    """Latest verified code approval effective now, matching owner._up_to.

    ``approvals`` is an immutable (UTC stamp, code hash) snapshot of the fully
    verified head. Preserve log order: future rows do not supersede a current
    approval until their timestamp, including while confirmation is pending.
    """
    stamp = at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return next((code for utc, code in reversed(approvals) if utc <= stamp), None)


def _cmd_bundle_attest(args):
    """Archive-only detached scope; independent parser, no owner event or app imports."""
    repo = _refuse_quantgen(Path(args.repo).resolve(), '--repo')
    packet, _ = _bundle_directory(args.packet)
    with _BundlePin(packet) as root_pin, _BundlePin(packet / 'payloads') as payload_pin:
        return _bundle_attest_pinned(args, repo, packet, (root_pin, payload_pin))


def _bundle_attest_pinned(args, repo, packet, pins):
    if Path(sys.prefix).resolve() != (repo / '.venv').resolve():
        raise ValueError('run bundle-attest with the deployment .venv Python and -I')
    signer_file = Path(__file__).resolve()
    if signer_file.is_relative_to(repo) or signer_file.is_relative_to(packet):
        raise ValueError('run your separately reviewed signer copy outside the repository and packet')
    output = _review_path(args.output)
    if output.suffix.lower() != '.json' or output.exists() or output.is_relative_to(packet) or not output.parent.is_dir():
        raise ValueError('archive attestation output must be a new JSON file outside the packet')
    request, snapshot = _bundle_packet(packet, pins=pins)
    if args.expires_at != request['expires_at']:
        raise ValueError('archive expiry differs from the request')
    closure = code_hash(repo)
    if closure != request['deployment_code_hash']:
        raise ValueError('archive request does not match the current deployment code')
    pem_path = repo / 'core' / 'compliance' / 'owner_pubkey.pem'
    pem, pem_identity = _bundle_read(pem_path, 4096)
    public = _pem_raw(pem)
    now = datetime.fromisoformat(_utc_now().replace('Z', '+00:00'))
    body = _ba_attestation_body(request, owner_fingerprint=fingerprint(public), issued_at=now)
    lines = _read_lines(_log_path())
    head = _bundle_verified_head(lines, public)
    entries = tuple(json.loads(line) for line in lines)
    approvals = tuple((row['utc'], row['data']['sha256']) for row in entries if row['kind'] == 'code_approved')
    if _bundle_code_approval_at(approvals, now) != closure:
        raise ValueError('review and code-approve this exact deployment before archive attestation')
    _confirm_bundle(body)
    key = _unlock(_key_path(args))
    if key.public_key().public_bytes_raw() != public:
        raise ValueError('unlocked archive key does not match the current deployment PEM')
    with _exclusive(_log_path()):
        current = _read_lines(_log_path())
        if _bundle_verified_head(current, public) != head or _wrong_key(key, 'archive_attestation', {}, current):
            raise ValueError('owner log or current key changed; review the archive again')
        current_request, current_snapshot = _bundle_packet(packet, pins=pins)
        current_pem, current_pem_identity = _bundle_read(pem_path, 4096)
        if (current_request != request or current_snapshot != snapshot or current_pem != pem
                or current_pem_identity != pem_identity or code_hash(repo) != closure):
            raise ValueError('archive inputs, deployment or key changed; review again')
        expires = datetime.fromisoformat(request['expires_at'])
        signing_bytes = _ba_attestation_signing_bytes(body)
        current_time = datetime.fromisoformat(_utc_now().replace('Z', '+00:00'))
        if not now <= current_time < min(expires, now + timedelta(minutes=5)):
            raise ValueError('archive confirmation expired or clock moved; review again')
        if _bundle_code_approval_at(approvals, current_time) != closure:
            raise ValueError('current code approval changed during archive confirmation; review again')
        encoded = _ba_attestation_document_bytes(body, key.sign(signing_bytes))
        finished = datetime.fromisoformat(_utc_now().replace('Z', '+00:00'))
        if not current_time <= finished < min(expires, now + timedelta(minutes=5)):
            raise ValueError('archive signing expired or clock moved; nothing was published')
        if _bundle_code_approval_at(approvals, finished) != closure:
            raise ValueError('current code approval changed during archive signing; nothing was published')
        _bundle_write_new(output, encoded)
    print('signed archive identity only; owner log unchanged; source, selection and trading remain separate')
    return 0


def _research_revocation_data(value):
    """Strict independent event data; no target trust or signing authority."""
    if (type(value) is not dict or set(value) != {'purpose', 'target_sha256', 'reason_code'}
            or type(value['purpose']) is not str or value['purpose'] not in _RESEARCH_PURPOSES
            or type(value['target_sha256']) is not str or not _hex64(value['target_sha256'])
            or type(value['reason_code']) is not str or value['reason_code'] not in _RESEARCH_REASONS):
        raise ValueError('RESEARCH_REVOCATION_DATA_INVALID')
    return dict(value)


def _research_revocation_target(document, *, purpose):
    """Identity of the existing signed body, never of its signature or raw file."""
    if type(purpose) is not str or purpose not in _RESEARCH_PURPOSES:
        raise ValueError('RESEARCH_REVOCATION_PURPOSE_INVALID')
    if type(document) is not bytes:
        raise ValueError('RESEARCH_REVOCATION_DOCUMENT_INVALID')
    try:
        if purpose == 'research_archive_manifest_attestation':
            body = _ba_parse_attestation_document(document)['body']
            signed = _ba_attestation_signing_bytes(body)
        else:
            body = _rv_parse_review_document(document)['body']
            signed = _rv_review_signing_bytes(body)
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        raise ValueError('RESEARCH_REVOCATION_DOCUMENT_INVALID') from None
    if body['purpose'] != purpose:
        raise ValueError('RESEARCH_REVOCATION_PURPOSE_INVALID')
    return sha256_hex(_RESEARCH_TARGET_DOMAIN + signed)


@dataclass(frozen=True, kw_only=True)
class _ResearchRevocationInput:
    """Displayed input snapshot with retained directory pins; not a grant of trust."""
    document_path: Path
    document_identity: tuple
    document_sha256: str
    document_pin: _BundlePin
    pem_path: Path
    pem_identity: tuple
    public_pem: bytes
    public_raw: bytes
    pem_pin: _BundlePin
    purpose: str
    target_sha256: str
    reason_code: str


def _research_anchor_directory():
    return _checked(_store_dir() / 'research-attestations', state_root())


def _research_anchor_rows(entries):
    return {entry['row_sha256'] + '.anchor.json': canonical_json({
        'seq': entry['seq'], 'row_sha256': entry['row_sha256']}).encode('utf-8')
        for entry in entries if entry['kind'] == _RESEARCH_REVOKED}


def _research_anchor_inventory(entries):
    """Existing restrictive anchors must belong to this fully verified chain."""
    directory = _research_anchor_directory()
    if not directory.exists():
        return
    expected = _research_anchor_rows(entries)
    with _BundlePin(directory) as pin:
        names = pin.names(len(expected))
        if not set(names) <= set(expected):
            raise ValueError('research restriction anchor inventory is not part of the verified log')
        for name in names:
            raw, _ = _bundle_read(directory / name, 256, parent_pin=pin)
            if raw != expected[name]:
                raise ValueError('research restriction anchor differs from the verified log')


def _research_flush_file(pin, name, identity):
    flags = os.O_RDWR | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    descriptor = pin.open(name, flags)
    try:
        if _bundle_identity(os.fstat(descriptor), regular=True) != identity:
            raise ValueError('research restriction file changed before durable flush')
        os.fsync(descriptor)
        if _bundle_identity(os.fstat(descriptor), regular=True) != identity:
            raise ValueError('research restriction file changed during durable flush')
    finally:
        os.close(descriptor)


def _research_flush_log(lines):
    if not lines:
        return
    expected = hashlib.sha256()
    for line in lines:
        expected.update(line)
    reference = sum(map(len, lines)), expected.hexdigest()
    path = _log_path()
    with _BundlePin(path.parent) as pin:
        actual, identity = _bundle_read(path, reference[0], hash_only=True, parent_pin=pin)
        if actual != reference:
            raise ValueError('research restriction log changed before durable retry')
        _research_flush_file(pin, path.name, identity)
        reread, after = _bundle_read(path, reference[0], hash_only=True, parent_pin=pin)
        if reread != reference or after != identity:
            raise ValueError('research restriction log changed after durable retry')


@contextmanager
def _research_anchor_pin():
    """Create only beneath retained parents, then keep every child pinned."""
    with ExitStack() as stack:
        parent = stack.enter_context(_BundlePin(_home()))
        for name in ('approved', 'research-attestations'):
            parent.check()
            try:
                if parent.native is not None:
                    # Native retained handles deny write/delete sharing for each
                    # ancestor. No unpinned Windows fallback is supported.
                    os.mkdir(parent.path / name, mode=0o700)
                else:
                    if os.mkdir not in os.supports_dir_fd:
                        raise ValueError('research anchor platform cannot create beneath a retained parent')
                    os.mkdir(name, mode=0o700, dir_fd=parent.descriptor)
            except FileExistsError:
                pass
            parent.check()
            expected = _bundle_identity(parent.stat(name))[:2]
            child = stack.enter_context(_BundlePin(parent.path / name))
            if _bundle_directory(child.path)[1][:2] != expected:
                raise ValueError('research restriction directory identity changed')
            parent = child
        yield parent


def _research_ensure_anchors(entries):
    """Under the existing log lock: exact no-overwrite files and durable retry.

    POSIX fsync includes the newly created ancestor directories through the
    explicit state root. Windows file flush and retained directory handles are
    checked; this does not establish native Windows power-loss durability.
    """
    expected = _research_anchor_rows(entries)
    if not expected:
        return
    directory = _research_anchor_directory()
    with _research_anchor_pin() as pin:
        if pin.path != directory:
            raise ValueError('research restriction directory differs from the pinned path')
        for name, encoded in expected.items():
            target = directory / name
            if not target.exists():
                _bundle_write_new(target, encoded)
            raw, identity = _bundle_read(target, 256, parent_pin=pin)
            if raw != encoded:
                raise ValueError('research restriction anchor exists with different bytes')
            _research_flush_file(pin, name, identity)
            reread, after = _bundle_read(target, 256, parent_pin=pin)
            if reread != encoded or after != identity:
                raise ValueError('research restriction anchor changed after durable flush')
        if pin.descriptor is not None:
            root = state_root().absolute()
            for path, descriptor, _ in reversed(pin.rows):
                if path == root.parent or path == root or path.is_relative_to(root):
                    os.fsync(descriptor)
        pin.check()
    _research_anchor_inventory(entries)


def _research_recheck(snapshot, data, key, lines, utc):
    """Called inside the existing append lock immediately before entry signing."""
    if type(snapshot) is not _ResearchRevocationInput:
        raise ValueError('research revocation input required')
    expected = _research_revocation_data({'purpose': snapshot.purpose,
        'target_sha256': snapshot.target_sha256, 'reason_code': snapshot.reason_code})
    if _research_revocation_data(data) != expected or key.public_key().public_bytes_raw() != snapshot.public_raw:
        raise ValueError('research revocation target or current signing key changed')
    _bundle_verified_head(lines, snapshot.public_raw)
    pem, pem_identity = _bundle_read(snapshot.pem_path, 4096, parent_pin=snapshot.pem_pin)
    raw, identity = _bundle_read(snapshot.document_path,
        _ba_MAX_DOCUMENT_BYTES if snapshot.purpose == 'research_archive_manifest_attestation' else _rv_MAX_DOCUMENT_BYTES,
        parent_pin=snapshot.document_pin)
    if (pem != snapshot.public_pem or pem_identity != snapshot.pem_identity
            or identity != snapshot.document_identity or sha256_hex(raw) != snapshot.document_sha256
            or _research_revocation_target(raw, purpose=snapshot.purpose) != snapshot.target_sha256):
        raise ValueError('research revocation document or deployment key changed; review again')
    shown = datetime.fromisoformat(utc.replace('Z', '+00:00'))
    now = datetime.fromisoformat(_utc_now().replace('Z', '+00:00'))
    if not shown <= now < shown + timedelta(minutes=5):
        raise ValueError('research revocation confirmation expired or clock moved; review again')


def _cmd_research_revoke(args):
    repo, _ = _bundle_directory(args.repo)
    if Path(sys.prefix).resolve() != (repo / '.venv').resolve():
        raise ValueError('run research-revoke with the deployment .venv Python and -I')
    if Path(__file__).resolve().is_relative_to(repo):
        raise ValueError('run your separately reviewed signer copy outside the repository')
    document = _review_path(args.document)
    pem_path = repo / 'core' / 'compliance' / 'owner_pubkey.pem'
    with _BundlePin(document.parent) as document_pin, _BundlePin(pem_path.parent) as pem_pin:
        maximum = _ba_MAX_DOCUMENT_BYTES if args.purpose == 'research_archive_manifest_attestation' else _rv_MAX_DOCUMENT_BYTES
        raw, identity = _bundle_read(document, maximum, parent_pin=document_pin)
        target = _research_revocation_target(raw, purpose=args.purpose)
        data = _research_revocation_data({'purpose': args.purpose, 'target_sha256': target,
                                         'reason_code': args.reason_code})
        pem, pem_identity = _bundle_read(pem_path, 4096, parent_pin=pem_pin)
        public = _pem_raw(pem)
        snapshot = _ResearchRevocationInput(document_path=document, document_identity=identity,
            document_sha256=sha256_hex(raw), document_pin=document_pin, pem_path=pem_path,
            pem_identity=pem_identity, public_pem=pem, public_raw=public, pem_pin=pem_pin, **data)
        lines = _read_lines(_log_path())
        head = _bundle_verified_head(lines, public)
        _research_anchor_inventory(tuple(json.loads(row) for row in lines))
        utc = _utc_now()
        print('Restrict use of this exact research approval; preserve all original evidence.')
        print('This does not authenticate its past approval, delete data, place orders or liquidate holdings.')
        _confirm(_RESEARCH_REVOKED, data, head, utc)
        key = _unlock(_key_path(args))
        if key.public_key().public_bytes_raw() != public:
            raise ValueError('unlocked key does not match the current deployment PEM')
        seq, row = _commit(key, _RESEARCH_REVOKED, data, utc=utc, expect_head=head, research_input=snapshot)
    print(f'research approval restricted at owner entry #{seq}; target {target}; row {row}')
    return 0


def _cmd_event(args) -> int:
    if args.kind == _RESEARCH_REVOKED:
        raise ValueError('use research-revoke with the original detached document')
    data = json.loads(args.data)
    if args.kind in ("cap_set", "limit_set") and isinstance(data, dict):
        data = {k: float(v) if _number(v) else v for k, v in data.items()}     # caps and limits are floats
    return _sign(args, args.kind, data)


def _cmd_archive_authority_grant(args):
    from tools.approval_broker import contract as C
    try:
        return _archive_authority_grant(args)
    except C.PasskeyError:
        raise
    except (ValueError,RuntimeError,OSError,ImportError,TypeError,AttributeError,OverflowError):
        raise C.PasskeyError('PASSKEY_GRANT_SIGNING_REFUSED') from None


def _passkey_output(path, installation):
    from tools.approval_broker import bootstrap as B, contract as C
    target = _review_path(path)
    forbidden = (installation.locations.app_repo,installation.locations.app_environment,
        installation.locations.compliance_root,Path(B.__file__).resolve().parents[2],
        installation.broker_release_root,installation.rp_release_root,installation.ledger_roots.primary,
        installation.ledger_roots.backup,installation.ledger_roots.head,
        Path(installation.config.packet_inbox),*installation.dependency_roots)
    C.need(target.suffix.lower()=='.json' and not target.exists() and target.parent.is_dir()
           and not any(target.is_relative_to(root) for root in forbidden),'PASSKEY_OUTPUT_REFUSED')
    return target


def _archive_authority_grant(args):
    """Independent archive-only bootstrap grant; no owner-log or registry write.

    The separately installed reviewed package must be importable through the
    isolated interpreter. No repo/packet path is ever inserted into sys.path.
    Existing main() terminal/isolation/unlock/typed-confirmation gates remain.
    """
    from tools.approval_broker import authority_contract as A, bootstrap as B, contract as C
    from tools.approval_broker.cli import load_installation
    from tools.approval_broker.owner_view import OwnerReader
    from tools.approval_broker.release import verify_release
    installation = load_installation(Path(args.config))
    repo = installation.locations.app_repo
    C.need(installation.locations.compliance_root == _home(), 'PASSKEY_OWNER_LOCATION_INVALID')
    if Path(__file__).resolve().is_relative_to(repo) or Path(B.__file__).resolve().is_relative_to(repo):
        raise C.PasskeyError('PASSKEY_INDEPENDENT_SIGNER_REQUIRED')
    signer_path = _review_path(__file__)
    signer_raw,signer_identity = _bundle_read(signer_path,2*1024*1024)
    C.need(_bundle_read(installation.broker_release_root/'tools'/'signer'/'sign.py',2*1024*1024)[0]==signer_raw,
           'PASSKEY_RELEASE_CHANGED')
    clock = lambda: datetime.now(timezone.utc)
    reader = OwnerReader(locations=installation.locations,roots=installation.trust_roots,clock=clock)
    proposal_path = _review_path(args.proposal)
    raw,identity = _bundle_read(proposal_path,2*1024*1024)
    proposal = A.parse_proposal(raw)
    B.verify_bootstrap(proposal)
    first = reader.observe(retained=None)
    C.need(first.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
    output = _passkey_output(args.output,installation)
    C.need(output != proposal_path,'PASSKEY_OUTPUT_REFUSED')
    expiry = C.time_value(args.expires_at)
    verify_release(installation.broker_release_root,installation.broker_release,
                   dependency_roots=installation.dependency_roots)
    verify_release(installation.rp_release_root,installation.rp_release,dependency_roots=())
    confirmed = reader.observe(retained=first.evidence)
    C.need(confirmed.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
    checkpoint = A.OwnerCheckpoint(fingerprint=fingerprint(confirmed.evidence.public_key_raw),
        code_sha256=confirmed.deployment_code_sha256,owner_head=confirmed.evidence.head,
        observed_at=confirmed.evidence.observed_at)
    issued = clock()
    body = B.build_grant_body(proposal,config=installation.config,
        broker_release=installation.broker_release,rp_release=installation.rp_release,owner=checkpoint,
        recovery_fingerprint=fingerprint(installation.trust_roots.recovery_public_key_raw),
        issued_at=issued,expires_at=expiry)
    rows = tuple(json.loads(line) for line in confirmed.evidence.log_bytes.split(b'\n') if line)
    approvals = tuple((row['utc'],row['data']['sha256']) for row in rows if row['kind']=='code_approved')
    before_confirmation = clock()
    C.need(confirmed.completed_at <= issued <= before_confirmation < expiry
           and before_confirmation-confirmed.evidence.observed_at <= timedelta(seconds=30), 'PASSKEY_EXPIRED')
    C.need(_bundle_code_approval_at(approvals,before_confirmation)==confirmed.deployment_code_sha256,
           'PASSKEY_DEPLOYMENT_CHANGED')
    print('Archive-manifest identity authority only. No trading, source approval or current operational channel.')
    print(json.dumps(json.loads(body),indent=2,sort_keys=True,ensure_ascii=True))
    print('RP:',installation.config.rp_origin,'RP ID:',installation.config.rp_id)
    print('Credential public-key SHA256:',sha256_hex(proposal.initial_credential.public_key_cose))
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed,stamps = _read_typed(f'Type this code to grant archive authority (do not paste): {code}\n> ')
    C.need(_typed_ok(code,typed,stamps),'PASSKEY_CONFIRMATION_REFUSED')
    key = _unlock(_key_path(args))
    with _exclusive(installation.locations.compliance_root/'owner.jsonl'):
        current = load_installation(Path(args.config))
        C.need(current == installation,'PASSKEY_INSTALLATION_CHANGED')
        C.need(_bundle_read(signer_path,2*1024*1024)==(signer_raw,signer_identity),'PASSKEY_RELEASE_CHANGED')
        C.need(_bundle_read(proposal_path,2*1024*1024)==(raw,identity),'PASSKEY_TARGET_CHANGED')
        B.verify_bootstrap(proposal)
        verify_release(installation.broker_release_root,installation.broker_release,
                       dependency_roots=installation.dependency_roots)
        verify_release(installation.rp_release_root,installation.rp_release,dependency_roots=())
        latest = reader.observe(retained=confirmed.evidence)
        C.need(latest.deployment_problem is None,'PASSKEY_DEPLOYMENT_REFUSED')
        public = latest.evidence.public_key_raw
        C.need(key.public_key().public_bytes_raw()==public,'PASSKEY_OWNER_KEY_CHANGED')
        C.need(latest.evidence.head==confirmed.evidence.head and public==confirmed.evidence.public_key_raw
               and latest.deployment_code_sha256==confirmed.deployment_code_sha256,'PASSKEY_OWNER_CHANGED')
        rows = tuple(json.loads(line) for line in latest.evidence.log_bytes.split(b'\n') if line)
        approvals = tuple((row['utc'],row['data']['sha256']) for row in rows if row['kind']=='code_approved')
        signing = A.grant_signing_bytes(body)
        now = clock()
        C.need(issued <= latest.completed_at <= now < min(expiry,issued+timedelta(minutes=5))
               and now-latest.evidence.observed_at <= timedelta(seconds=30),
               'PASSKEY_EXPIRED')
        C.need(_bundle_code_approval_at(approvals,now)==latest.deployment_code_sha256,'PASSKEY_DEPLOYMENT_CHANGED')
        document = A.GrantDocument(body_bytes=body,signature=key.sign(signing))
        B.verify_grant_document(document,signer_public_key_raw=public)
        encoded = A.grant_bytes(document)
        finish = clock()
        C.need(now <= finish < min(expiry,issued+timedelta(minutes=5))
               and finish-latest.evidence.observed_at <= timedelta(seconds=30),
               'PASSKEY_EXPIRED')
        C.need(_bundle_code_approval_at(approvals,finish)==latest.deployment_code_sha256,'PASSKEY_DEPLOYMENT_CHANGED')
        _bundle_write_new(output,encoded)
    print('Signed archive authority grant; operational channel is not implemented; trading remains disabled.')
    return 0


def _cmd_archive_authority_disable(args):
    from tools.approval_broker import contract as C
    try:
        return _archive_authority_disable(args)
    except C.PasskeyError:
        raise
    except (ValueError,RuntimeError,OSError,ImportError,TypeError,AttributeError,OverflowError):
        raise C.PasskeyError('PASSKEY_DISABLE_SIGNING_REFUSED') from None


def _archive_authority_disable(args):
    """Sign a restrictive exact-head document; installation is a separate action."""
    from tools.approval_broker import authority_contract as A, bootstrap as B, contract as C
    from tools.approval_broker.cli import load_installation
    from tools.approval_broker.ledger import AuthorityLedger
    from tools.approval_broker.release import verify_release
    C.need(type(args.key) is str and bool(args.key),'PASSKEY_RECOVERY_KEY_REQUIRED')
    C.need(args.reason in ('DEVICE_LOST','AUTHORITY_COMPROMISED'),'PASSKEY_FORMAT_INVALID')
    installation = load_installation(Path(args.config))
    repo = installation.locations.app_repo
    C.need(not Path(__file__).resolve().is_relative_to(repo) and not Path(B.__file__).resolve().is_relative_to(repo),
           'PASSKEY_INDEPENDENT_SIGNER_REQUIRED')
    signer_path = _review_path(__file__)
    signer_raw,signer_identity = _bundle_read(signer_path,2*1024*1024)
    C.need(_bundle_read(installation.broker_release_root/'tools'/'signer'/'sign.py',2*1024*1024)[0]==signer_raw,
           'PASSKEY_RELEASE_CHANGED')
    output = _passkey_output(args.output,installation)
    ledger = AuthorityLedger(roots=installation.ledger_roots,installation=installation.ledger_installation)
    snapshot = ledger.inspect()
    C.need(snapshot.state.grant is not None and not snapshot.state.disabled,'PASSKEY_BOOTSTRAP_REQUIRED')
    recovery = installation.trust_roots.recovery_public_key_raw
    C.need(snapshot.state.grant.body['recovery_fingerprint']==fingerprint(recovery),'PASSKEY_RECOVERY_KEY_REQUIRED')
    verify_release(installation.broker_release_root,installation.broker_release,
                   dependency_roots=installation.dependency_roots)
    clock = lambda: datetime.now(timezone.utc)
    issued,expiry = clock(),C.time_value(args.expires_at)
    body = A.canonical(dict(schema=1,purpose='passkey_archive_authority_disable',
        authority_id=installation.config.authority_id,grant_sha256=snapshot.state.grant.digest,
        expected_head=A.head_document(snapshot.head),reason=args.reason,
        issued_at=C.stamp(issued),expires_at=C.stamp(expiry)))
    signing = A.disable_signing_bytes(body)  # Exact reason and <=300-second TTL.
    print('Restrict this exact archive authority only; no reset, replacement grant or trading authority.')
    print(json.dumps(json.loads(body),indent=2,sort_keys=True,ensure_ascii=True))
    print('Required recovery-key fingerprint:',fingerprint(recovery))
    code = ''.join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    typed,stamps = _read_typed(f'Type this code to sign the restriction (do not paste): {code}\n> ')
    C.need(_typed_ok(code,typed,stamps),'PASSKEY_CONFIRMATION_REFUSED')
    key = _unlock(_key_path(args))
    C.need(key.public_key().public_bytes_raw()==recovery,'PASSKEY_RECOVERY_KEY_REQUIRED')
    with ledger.operation() as operation:
        current = load_installation(Path(args.config))
        C.need(current==installation,'PASSKEY_INSTALLATION_CHANGED')
        C.need(_bundle_read(signer_path,2*1024*1024)==(signer_raw,signer_identity),'PASSKEY_RELEASE_CHANGED')
        verify_release(installation.broker_release_root,installation.broker_release,
                       dependency_roots=installation.dependency_roots)
        latest = operation.load()
        C.need(latest.head==snapshot.head and latest.context_sha256==snapshot.context_sha256
               and latest.state.grant is not None and latest.state.grant.digest==snapshot.state.grant.digest
               and not latest.state.disabled,'PASSKEY_TARGET_CHANGED')
        operation.check()
        now = clock()
        C.need(issued <= now < expiry,'PASSKEY_EXPIRED')
        document = A.DisableDocument(body_bytes=body,signature=key.sign(signing))
        B.verify_disable_document(document,recovery_public_key_raw=recovery)
        encoded = A.disable_bytes(document)
        finish = clock()
        C.need(now <= finish < expiry,'PASSKEY_EXPIRED')
        _bundle_write_new(output,encoded)
    print('Signed recovery restriction only; apply this document separately; ledger is unchanged.')
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sign.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, run, text in (("keygen", _cmd_keygen, "create the key file and the public key"),
                            ("fingerprint", _cmd_fingerprint, "print the key fingerprint"),
                            ("approve", _cmd_approve, "approve a table file or the calendar folder"),
                            ("code-approve", _cmd_code_approve, "sign the code hash of the repo"),
                            ("review-approve", _cmd_review_approve, "attest a prospective source and fixed implementation review"),
                            ("bundle-attest", _cmd_bundle_attest, "attest exact archived manifests and available file bytes only"),
                            ("research-revoke", _cmd_research_revoke, "restrict use of one exact research approval body"),
                            ("archive-authority-grant", _cmd_archive_authority_grant, "sign a separately verified archive-only passkey grant"),
                            ("archive-authority-disable", _cmd_archive_authority_disable, "sign an exact-head restriction with the explicit recovery key; does not install it"),
                            ("event", _cmd_event, "sign one owner event")):
        p = sub.add_parser(name, help=text)
        p.set_defaults(run=run)
        if name == 'archive-authority-disable':
            p.add_argument('--key',required=True,help='explicit independent recovery key file; no owner-key default')
        else:
            p.add_argument("--key", help="key file (default: ~/.tradegen/compliance/owner_key.enc)")
        if name == "approve":
            p.add_argument("--kind", required=True, choices=APPROVAL_KINDS)
            p.add_argument("--path", required=True, help="the file, or the calendar data folder")
        elif name == "code-approve":
            p.add_argument("--repo", required=True, help="the TRADEGEN repo folder")
        elif name == "review-approve":
            for flag in ("repo", "request", "driver-manifest", "audit", "expires-at", "output"):
                p.add_argument("--" + flag, required=True)
        elif name == "bundle-attest":
            for flag in ("repo", "packet", "expires-at", "output"):
                p.add_argument("--" + flag, required=True)
        elif name == 'research-revoke':
            p.add_argument('--repo', required=True)
            p.add_argument('--document', required=True)
            p.add_argument('--purpose', required=True, choices=sorted(_RESEARCH_PURPOSES))
            p.add_argument('--reason-code', required=True, choices=sorted(_RESEARCH_REASONS))
        elif name == 'archive-authority-grant':
            for flag in ('config','proposal','expires-at','output'):
                p.add_argument('--'+flag,required=True)
        elif name == 'archive-authority-disable':
            for flag in ('config','expires-at','output'):
                p.add_argument('--'+flag,required=True)
            p.add_argument('--reason',required=True,choices=('DEVICE_LOST','AUTHORITY_COMPROMISED'))
        elif name == "event":
            p.add_argument("kind", choices=sorted(set(SCHEMAS) - {"approved", "code_approved", _RESEARCH_REVOKED}))
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
