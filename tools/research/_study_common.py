"""Shared offline hardening helpers for Section-12 direction-model research tools.

Pure Python standard library only. Never an order, credential, signing, or owner-log input.
"""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from typing import Any


RESEARCH_FLAGS: dict[str, bool] = {
    "research_only": True,
    "live_eligible": False,
    "execution_ready": False,
    "source_authenticated": False,
    "owner_approval_verified": False,
}

UTC = timezone.utc
KST = timezone(timedelta(hours=9))

HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
HEX40_RE = re.compile(r"[0-9a-f]{40}\Z")
MARKET_RE = re.compile(r"KRW-[A-Z0-9]{1,20}\Z")
PRODUCER_RE = re.compile(r"[a-z0-9-]{1,64}\Z")
IDENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:\-/]{0,127}\Z")
DECIMAL_STR_RE = re.compile(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,16})?\Z")

DEFAULT_MAX_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_NODES = 2_000_000
FORBIDDEN_DIR_NAMES = frozenset({".tradegen", ".nextgen"})

FORBIDDEN_RESEARCH_IMPORT_PREFIXES = (
    "core.compliance",
    "core.odds",
    "core.isolation",
    "execution",
    "execution_control",
    "execution_orders",
    "execution_accounts",
    "execution_network",
    "execution_launch",
    "tools.owner",
    "tools.signer",
    "config",
    "main",
    "quantgpt",
    "quantgen",
    "qgpt",
)

LEGACY_LAUNCH_HELPERS = frozenset({
    "prepare_launch_example.py",
    "prepare_shortened_study.py",
})


class StudyError(ValueError):
    """Fixed-code research validation or I/O refusal."""


def require(condition: Any, code: str) -> None:
    if not condition:
        raise StudyError(code)


# --------------------------------------------------------------------------- #
# Regime A (TRADEGEN ASCII) vs Regime B (QUANTGEN / QuantGPT / DIDM UTF-8)
# --------------------------------------------------------------------------- #
def canonical_ascii_str(obj: Any) -> str:
    """Regime A: sorted compact ASCII JSON, NaN/Infinity refused."""
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StudyError("CANONICAL_ASCII_JSON_INVALID") from exc


def canonical_ascii_bytes(obj: Any) -> bytes:
    return canonical_ascii_str(obj).encode("ascii")


def sha256_ascii(obj: Any) -> str:
    return hashlib.sha256(canonical_ascii_bytes(obj)).hexdigest()


def canonical_utf8_str(obj: Any) -> str:
    """Regime B: sorted compact UTF-8 JSON (ensure_ascii=False), NaN/Infinity refused."""
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StudyError("CANONICAL_UTF8_JSON_INVALID") from exc


def canonical_utf8_bytes(obj: Any) -> bytes:
    try:
        return canonical_utf8_str(obj).encode("utf-8", "strict")
    except UnicodeError as exc:
        raise StudyError("CANONICAL_UTF8_JSON_INVALID") from exc


def sha256_utf8(obj: Any) -> str:
    return hashlib.sha256(canonical_utf8_bytes(obj)).hexdigest()


def sha256_raw(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Strict JSON parsing & tree validation
# --------------------------------------------------------------------------- #
def check_json_tree(
    value: Any,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    error_code: str = "JSON_LIMIT_OR_INVALID",
) -> Any:
    """Iterative validator: depth <= max_depth, finite floats, no lone UTF-16 surrogates."""
    pending: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while pending:
        node, depth = pending.pop()
        nodes += 1
        require(nodes <= max_nodes and depth <= max_depth, error_code)
        t = type(node)
        if t is dict:
            for k, v in node.items():
                require(type(k) is str, error_code)
                try:
                    k.encode("utf-8", "strict")
                except UnicodeError:
                    raise StudyError(error_code) from None
                pending.append((v, depth + 1))
        elif t is list:
            for item in node:
                pending.append((item, depth + 1))
        elif t is float:
            require(math.isfinite(node), "NONFINITE_JSON_NUMBER")
        elif t is str:
            try:
                node.encode("utf-8", "strict")
            except UnicodeError:
                raise StudyError(error_code) from None
        else:
            require(t in (int, bool, type(None)), error_code)
    return value


def check_token_caps(
    raw: bytes,
    *,
    max_containers: int,
    max_colons: int,
    max_commas: int,
    error_code: str = "JSON_TOKEN_CAP_EXCEEDED",
) -> None:
    require(
        raw.count(b"{") + raw.count(b"[") <= max_containers
        and raw.count(b":") <= max_colons
        and raw.count(b",") <= max_commas,
        error_code,
    )


def loads_strict_json(
    raw: bytes | str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_containers: int | None = None,
    max_colons: int | None = None,
    max_commas: int | None = None,
    size_error: str = "INPUT_SIZE_LIMIT",
) -> Any:
    if isinstance(raw, str):
        try:
            raw_bytes = raw.encode("utf-8", "strict")
        except UnicodeError:
            raise StudyError("JSON_INVALID_UTF8") from None
    elif type(raw) is bytes:
        raw_bytes = raw
    else:
        raise StudyError("JSON_INVALID_INPUT")

    require(len(raw_bytes) <= max_bytes, size_error)
    require(not raw_bytes.startswith(b"\xef\xbb\xbf"), "UTF8_BOM_REFUSED")

    if max_containers is not None and max_colons is not None and max_commas is not None:
        check_token_caps(
            raw_bytes,
            max_containers=max_containers,
            max_colons=max_colons,
            max_commas=max_commas,
            error_code=size_error,
        )

    try:
        text = raw_bytes.decode("utf-8", "strict")
    except UnicodeError:
        raise StudyError("JSON_INVALID_UTF8") from None

    def unique_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in items:
            require(k not in out, "DUPLICATE_JSON_KEY")
            out[k] = v
        return out

    def bad_constant(_token: str) -> None:
        raise StudyError("NONFINITE_JSON_NUMBER")

    try:
        parsed = json.loads(text, object_pairs_hook=unique_pairs, parse_constant=bad_constant)
    except StudyError:
        raise
    except (json.JSONDecodeError, RecursionError, OverflowError, ValueError):
        raise StudyError("MALFORMED_JSON") from None

    return check_json_tree(parsed, max_depth=max_depth, max_nodes=max_nodes)


# --------------------------------------------------------------------------- #
# Path, symlink, hardlink & atomic no-clobber I/O hardening
# --------------------------------------------------------------------------- #
def _is_reparse_or_symlink(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def _stat_identity(st: os.stat_result) -> tuple[int, int, int, int]:
    require(type(st.st_ino) is int and st.st_ino > 0 and type(st.st_dev) is int and st.st_dev >= 0, "PATH_REFUSED")
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)


def check_safe_path(path: Path | str, *, error_code: str = "PATH_REFUSED") -> Path:
    """Reject .tradegen / .nextgen components and any symlink on existing ancestors."""
    raw_path = Path(path)
    abs_path = Path(os.path.abspath(os.fspath(raw_path)))
    for candidate in (raw_path, abs_path):
        if any(part.casefold() in FORBIDDEN_DIR_NAMES for part in candidate.parts):
            raise StudyError(error_code)
    for ancestor in reversed((abs_path, *abs_path.parents)):
        try:
            st = ancestor.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise StudyError(error_code) from None
        if _is_reparse_or_symlink(st):
            raise StudyError(error_code)
        if ancestor != abs_path and not stat.S_ISDIR(st.st_mode):
            raise StudyError(error_code)
    return abs_path


def ensure_safe_directory(path: Path | str, *, error_code: str = "PATH_REFUSED") -> Path:
    target = check_safe_path(path, error_code=error_code)
    target.mkdir(parents=True, exist_ok=True)
    st = target.lstat()
    if _is_reparse_or_symlink(st) or not stat.S_ISDIR(st.st_mode):
        raise StudyError(error_code)
    return target


def read_safe_bytes(
    path: Path | str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    must_end_with: str | None = None,
    path_error: str = "PATH_REFUSED",
    size_error: str = "INPUT_SIZE_LIMIT",
) -> bytes:
    target = check_safe_path(path, error_code=path_error)
    if must_end_with is not None:
        require(target.name.lower().endswith(must_end_with.lower()), path_error)
    try:
        before = target.lstat()
    except OSError:
        raise StudyError(path_error) from None
    if _is_reparse_or_symlink(before) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise StudyError(path_error)
    require(0 < before.st_size <= max_bytes, size_error)

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, flags)
    except OSError:
        raise StudyError(path_error) from None
    try:
        opened = os.fstat(fd)
        if _is_reparse_or_symlink(opened) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise StudyError(path_error)
        require(_stat_identity(opened) == _stat_identity(before), "INPUT_CHANGED")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(max_bytes + 1)
        require(len(data) <= max_bytes, size_error)
        require(len(data) == before.st_size, "INPUT_CHANGED")
        require(_stat_identity(os.fstat(fd)) == _stat_identity(before), "INPUT_CHANGED")
        require(_stat_identity(target.lstat()) == _stat_identity(before), "INPUT_CHANGED")
    finally:
        os.close(fd)
    return data


def read_strict_json_file(
    path: Path | str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_containers: int | None = None,
    max_colons: int | None = None,
    max_commas: int | None = None,
    must_be_json_suffix: bool = True,
    path_error: str = "PATH_REFUSED",
    size_error: str = "INPUT_SIZE_LIMIT",
) -> tuple[Any, bytes]:
    raw = read_safe_bytes(
        path,
        max_bytes=max_bytes,
        must_end_with=".json" if must_be_json_suffix else None,
        path_error=path_error,
        size_error=size_error,
    )
    parsed = loads_strict_json(
        raw,
        max_bytes=max_bytes,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_containers=max_containers,
        max_colons=max_colons,
        max_commas=max_commas,
        size_error=size_error,
    )
    return parsed, raw


def atomic_publish_bytes(
    destination: Path | str,
    payload: bytes,
    *,
    max_bytes: int = 64 * 1024 * 1024,
    exists_error: str = "OUTPUT_EXISTS",
    path_error: str = "PATH_REFUSED",
) -> Path:
    """Atomic no-clobber write: mkstemp + fsync + os.link + unlink. Strictly LF."""
    require(type(payload) is bytes and len(payload) <= max_bytes, "OUTPUT_SIZE_LIMIT")
    require(b"\r\n" not in payload, "CRLF_NOT_ALLOWED")
    dest = check_safe_path(destination, error_code=path_error)
    require(not os.path.lexists(dest), exists_error)
    parent = dest.parent
    require(parent.exists() and not parent.is_symlink() and parent.is_dir(), path_error)

    fd, tmp_name = tempfile.mkstemp(prefix=".tg-res-", suffix=".tmp", dir=parent)
    tmp_path = Path(tmp_name)
    try:
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            raise
        try:
            os.link(tmp_path, dest)
        except FileExistsError:
            raise StudyError(exists_error) from None
        except OSError:
            raise StudyError(path_error) from None
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
    return dest


def atomic_publish_json_ascii(destination: Path | str, obj: Any, **kwargs: Any) -> tuple[Path, str]:
    raw = canonical_ascii_bytes(obj) + b"\n"
    dest = atomic_publish_bytes(destination, raw, **kwargs)
    return dest, hashlib.sha256(raw[:-1]).hexdigest()


def atomic_publish_json_utf8(destination: Path | str, obj: Any, **kwargs: Any) -> tuple[Path, str]:
    raw = canonical_utf8_bytes(obj) + b"\n"
    dest = atomic_publish_bytes(destination, raw, **kwargs)
    return dest, hashlib.sha256(raw[:-1]).hexdigest()


# --------------------------------------------------------------------------- #
# Hash-chained append-only JSONL archive (Regime A ASCII)
# --------------------------------------------------------------------------- #
class HashChainedLog:
    """Exclusive append-only JSONL log with SHA-256 chain (seq, previous, data, sha256)."""

    def __init__(
        self,
        directory: Path | str,
        filename: str,
        *,
        lock_name: str = ".archive.lock",
        max_line_bytes: int = 4 * 1024 * 1024,
        max_archive_bytes: int = 1024 * 1024 * 1024,
    ) -> None:
        self.root = ensure_safe_directory(directory, error_code="ARCHIVE_PATH_REFUSED")
        self.path = check_safe_path(self.root / filename, error_code="ARCHIVE_PATH_REFUSED")
        self.lock_path = check_safe_path(self.root / lock_name, error_code="ARCHIVE_PATH_REFUSED")
        self.max_line_bytes = max_line_bytes
        self.max_archive_bytes = max_archive_bytes
        self.lock_fd: int | None = None
        self.seq = 0
        self.head_sha256 = "0" * 64
        self._entries: list[dict[str, Any]] = []

    def __enter__(self) -> HashChainedLog:
        try:
            self.lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise StudyError("ARCHIVE_LOCKED") from None
        try:
            self._entries = self._load_and_verify()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def close(self) -> None:
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def _load_and_verify(self) -> list[dict[str, Any]]:
        if not os.path.lexists(self.path):
            self.seq = 0
            self.head_sha256 = "0" * 64
            return []
        st = self.path.lstat()
        if _is_reparse_or_symlink(st) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise StudyError("ARCHIVE_PATH_REFUSED")
        require(st.st_size <= self.max_archive_bytes, "ARCHIVE_SIZE_LIMIT")
        entries: list[dict[str, Any]] = []
        seq = 0
        prev = "0" * 64
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags)
        try:
            with os.fdopen(fd, "rb", closefd=False) as stream:
                while True:
                    line = stream.readline(self.max_line_bytes + 1)
                    if not line:
                        break
                    require(
                        len(line) <= self.max_line_bytes
                        and line.endswith(b"\n")
                        and not line.endswith(b"\r\n"),
                        "ARCHIVE_TORN_OR_INVALID_LINE",
                    )
                    row = loads_strict_json(line[:-1], max_bytes=self.max_line_bytes, size_error="ARCHIVE_LINE_LIMIT")
                    require(
                        type(row) is dict and set(row) == {"seq", "previous", "data", "sha256"},
                        "ARCHIVE_CHAIN_BROKEN",
                    )
                    sha = row["sha256"]
                    body = {"seq": row["seq"], "previous": row["previous"], "data": row["data"]}
                    require(
                        row["seq"] == seq
                        and row["previous"] == prev
                        and type(sha) is str
                        and HEX64_RE.fullmatch(sha) is not None
                        and sha256_ascii(body) == sha
                        and canonical_ascii_bytes({**body, "sha256": sha}) == line[:-1],
                        "ARCHIVE_CHAIN_BROKEN",
                    )
                    entries.append(row)
                    seq += 1
                    prev = sha
        finally:
            os.close(fd)
        require(len(entries) > 0, "ARCHIVE_EMPTY_FILE")
        self.seq = seq
        self.head_sha256 = prev
        return entries

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def append(self, data: dict[str, Any]) -> dict[str, Any]:
        require(self.lock_fd is not None, "ARCHIVE_NOT_LOCKED")
        require(type(data) is dict, "ARCHIVE_ENTRY_INVALID")
        check_json_tree(data)
        body = {"seq": self.seq, "previous": self.head_sha256, "data": data}
        sha = sha256_ascii(body)
        full_row = {**body, "sha256": sha}
        raw = canonical_ascii_bytes(full_row) + b"\n"
        require(len(raw) <= self.max_line_bytes, "ARCHIVE_LINE_LIMIT")
        if os.path.lexists(self.path):
            st = self.path.lstat()
            if _is_reparse_or_symlink(st) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                raise StudyError("ARCHIVE_PATH_REFUSED")
            require(st.st_size + len(raw) <= self.max_archive_bytes, "ARCHIVE_SIZE_LIMIT")
        flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            cur = os.fstat(fd)
            if _is_reparse_or_symlink(cur) or not stat.S_ISREG(cur.st_mode) or cur.st_nlink != 1:
                raise StudyError("ARCHIVE_PATH_REFUSED")
            with os.fdopen(fd, "ab", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        self._entries.append(full_row)
        self.seq += 1
        self.head_sha256 = sha
        return full_row


def read_verified_chained_log(
    directory: Path | str,
    filename: str,
    *,
    pinned_head: str | None = None,
    max_line_bytes: int = 4 * 1024 * 1024,
    max_archive_bytes: int = 1024 * 1024 * 1024,
) -> tuple[list[dict[str, Any]], str]:
    """Read-only verification of a HashChainedLog without taking a write lock."""
    root = check_safe_path(directory, error_code="ARCHIVE_PATH_REFUSED")
    target = check_safe_path(root / filename, error_code="ARCHIVE_PATH_REFUSED")
    if not os.path.lexists(target):
        require(pinned_head in (None, "0" * 64), "ARCHIVE_HEAD_MISMATCH")
        return [], "0" * 64
    raw_all = read_safe_bytes(target, max_bytes=max_archive_bytes, path_error="ARCHIVE_PATH_REFUSED", size_error="ARCHIVE_SIZE_LIMIT")
    require(raw_all.endswith(b"\n") and b"\r\n" not in raw_all, "ARCHIVE_TORN_OR_INVALID_LINE")
    lines = raw_all.split(b"\n")[:-1]
    require(len(lines) > 0, "ARCHIVE_EMPTY_FILE")
    entries: list[dict[str, Any]] = []
    seq = 0
    prev = "0" * 64
    pin_seen = pinned_head is None
    for line in lines:
        require(len(line) <= max_line_bytes, "ARCHIVE_LINE_LIMIT")
        row = loads_strict_json(line, max_bytes=max_line_bytes, size_error="ARCHIVE_LINE_LIMIT")
        require(type(row) is dict and set(row) == {"seq", "previous", "data", "sha256"}, "ARCHIVE_CHAIN_BROKEN")
        sha = row["sha256"]
        body = {"seq": row["seq"], "previous": row["previous"], "data": row["data"]}
        require(
            row["seq"] == seq
            and row["previous"] == prev
            and type(sha) is str
            and HEX64_RE.fullmatch(sha) is not None
            and sha256_ascii(body) == sha
            and canonical_ascii_bytes({**body, "sha256": sha}) == line,
            "ARCHIVE_CHAIN_BROKEN",
        )
        entries.append(row)
        seq += 1
        prev = sha
        if pinned_head is not None and prev == pinned_head:
            pin_seen = True
    require(pin_seen, "ARCHIVE_HEAD_MISMATCH")
    return entries, prev


# --------------------------------------------------------------------------- #
# Decimal & time helpers
# --------------------------------------------------------------------------- #
def parse_decimal_str(
    value: Any,
    low: Decimal,
    high: Decimal,
    *,
    inclusive_low: bool = True,
    error_code: str = "INVALID_DECIMAL",
) -> Decimal:
    require(type(value) is str and DECIMAL_STR_RE.fullmatch(value) is not None, error_code)
    try:
        dec = Decimal(value)
    except InvalidOperation:
        raise StudyError(error_code) from None
    require((low <= dec if inclusive_low else low < dec) and dec <= high, error_code)
    return dec


def parse_epoch_int(value: Any, *, low: int = 0, high: int = 2**39, error_code: str = "INVALID_TIMESTAMP") -> int:
    require(type(value) is int and low <= value <= high, error_code)
    return value


def parse_aware_iso(value: Any, *, error_code: str = "INVALID_ISO_TIMESTAMP") -> datetime:
    require(type(value) is str and 0 < len(value) <= 64, error_code)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise StudyError(error_code) from None
    require(dt.utcoffset() is not None, error_code)
    return dt.astimezone(UTC)


def format_utc_microseconds(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="microseconds")


def kst_day_str(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, KST).strftime("%Y%m%d")


def kst_date_iso(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, KST).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Mandatory D14 + Self-Isolation Test Helper (used by every test_*.py)
# --------------------------------------------------------------------------- #
def _extract_imports(py_path: Path) -> list[str]:
    source = py_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 1:
                imports.append("..ESCAPED_RELATIVE_IMPORT")
            elif node.level == 1:
                imports.append(f".{node.module or ''}")
            elif node.module:
                imports.append(node.module)
    return imports


def _matches_prefix(mod_name: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if mod_name == prefix or mod_name.startswith(prefix + "."):
            return True
    return False


def _pinned_top_packages(repo_root: Path) -> set[str]:
    constraints = repo_root / "constraints.txt"
    pkgs: set[str] = {"yaml", "bs4", "PIL", "cv2", "dateutil", "dotenv", "slugify", "attr", " Crypto"}
    if constraints.is_file():
        for raw_line in constraints.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r"[=<>!~\[]", line, maxsplit=1)[0].strip()
            if pkg:
                pkgs.add(pkg)
                pkgs.add(pkg.lower())
                pkgs.add(pkg.replace("-", "_"))
                pkgs.add(pkg.replace("-", "_").lower())
    return pkgs


def assert_all_isolation_invariants(test_case: Any, repo_root: Path) -> None:
    """Run both D14 closure checks and the tools/research/*.py AST self-isolation check."""
    # 1 & 2: D14 closure checks (with 0.5s single retry if another agent is saving a file)
    if importlib.util.find_spec("yaml") is not None:
        closure: list[tuple[str, str]] | None = None
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                owner_mod = importlib.import_module("core.compliance.owner")
                closure = owner_mod.code_files(repo_root)
                break
            except (OSError, SyntaxError, ValueError) as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(0.5)
        if closure is None and last_exc is not None:
            raise last_exc
        assert closure is not None

        research_in_closure = [p for p, _ in closure if p.startswith("tools/research/")]
        test_case.assertEqual(research_in_closure, [], "tools/research/ leaked into D14 code_files closure")

        stdlib_names = set(sys.stdlib_module_names)
        pinned = _pinned_top_packages(repo_root)
        forbidden_in_d14 = ("quantgpt", "quantgen", "qgpt", "tools.research")

        for rel_path, _sha in closure:
            if rel_path.startswith("venv:") or not rel_path.endswith(".py"):
                continue
            full = repo_root / rel_path
            for attempt in range(2):
                try:
                    mod_imports = _extract_imports(full)
                    break
                except (OSError, SyntaxError):
                    if attempt == 0:
                        time.sleep(0.5)
                    else:
                        raise
            for imp in mod_imports:
                if imp.startswith("."):
                    continue
                test_case.assertFalse(
                    _matches_prefix(imp, forbidden_in_d14),
                    f"D14 module {rel_path} imports forbidden {imp}",
                )
                top = imp.split(".")[0]
                in_repo = (repo_root / top).exists() or (repo_root / f"{top}.py").exists()
                allowed = (
                    top in stdlib_names
                    or in_repo
                    or top in pinned
                    or top.lower() in pinned
                )
                test_case.assertTrue(
                    allowed,
                    f"D14 module {rel_path} imports unpinned external module {imp}",
                )

    # 3: AST self-isolation check across tools/research/*.py
    research_dir = repo_root / "tools" / "research"
    for py_file in sorted(research_dir.glob("*.py")):
        if py_file.name in LEGACY_LAUNCH_HELPERS:
            continue
        if py_file.name == "test_direction_forecast_adapter.py":
            # Pre-existing test file imports core.compliance.owner.code_files directly; check all others strictly.
            forbidden = tuple(p for p in FORBIDDEN_RESEARCH_IMPORT_PREFIXES if p != "core.compliance")
        else:
            forbidden = FORBIDDEN_RESEARCH_IMPORT_PREFIXES
        for imp in _extract_imports(py_file):
            test_case.assertFalse(
                imp.startswith(".."),
                f"Research file {py_file.name} uses parent-escaping relative import {imp}",
            )
            if imp.startswith("."):
                continue
            test_case.assertFalse(
                _matches_prefix(imp, forbidden),
                f"Research file {py_file.name} imports forbidden module {imp}",
            )
