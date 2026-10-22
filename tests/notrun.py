"""NOT_RUN status and the fixture manifest loader for the macro suites (M0; T-HERM-01; rulings section 6).

A test that cannot run on this machine raises `NotRun("REFDATA: ...")` (reference data absent) or
`NotRun("OWNER: ...")` (owner input, credentials or live sessions). `tests/run_all.py` records it as
NOT_RUN with the reason; it is never counted as PASS or FAIL and never affects the exit code.

Fixtures under `tests/fixtures/macro/` are read only through `require_fixture`, which refuses an unlisted
file, a manifest row without licence, owner and md5, and an md5 that no longer matches.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "macro"
MANIFEST = FIXTURES / "MANIFEST.csv"
MANIFEST_COLUMNS = ("file", "source", "series", "span", "retrieved_at_utc", "value_status_rule",
                    "md5", "licence", "owner", "tests")
_REQUIRED = ("licence", "owner", "md5")
_NOT_FIXTURES = ("MANIFEST.csv", "README.md")


class NotRun(Exception):
    """Raised by a test that cannot run here; `.reason` starts with `REFDATA:` or `OWNER:`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def require_owner(what: str) -> NotRun:
    """`raise require_owner("signed 2027 KRX calendar")` -> NotRun("OWNER: ...")."""
    return NotRun(f"OWNER: {what}")


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _label(manifest: Path) -> str:
    try:
        return manifest.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return manifest.name


def load_manifest(manifest: Path = MANIFEST) -> dict[str, dict[str, str]]:
    """Rows keyed by `file`. Refuses a wrong header, a duplicate file, or a row lacking licence, owner or md5."""
    with manifest.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
            raise ValueError(f"{_label(manifest)}: header must be {','.join(MANIFEST_COLUMNS)}")
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            name = (row.get("file") or "").strip()
            missing = [c for c in _REQUIRED if not (row.get(c) or "").strip()]
            if not name or missing:
                raise ValueError(f"{_label(manifest)}: {name!r} lacks {missing or ['file']}; "
                                 "a file without licence, owner and md5 is not a fixture")
            if name in rows:
                raise ValueError(f"{_label(manifest)}: {name!r} listed twice")
            rows[name] = {k: (v or "").strip() for k, v in row.items()}
    return rows


def require_fixture(name: str, *, manifest: Path = MANIFEST) -> Path:
    """Path of a manifest-listed, md5-verified fixture; NotRun("REFDATA: ...") when it is unlisted, absent or changed."""
    rows = load_manifest(manifest)
    if name not in rows:
        raise NotRun(f"REFDATA: {name} not in {_label(manifest)}")
    path = manifest.parent / name
    if not path.is_file():
        raise NotRun(f"REFDATA: {name} listed in {_label(manifest)} but absent")
    found = md5_of(path)
    if found != rows[name]["md5"].lower():
        raise NotRun(f"REFDATA: {name} md5 {found} != manifest {rows[name]['md5']}; fixture refused")
    return path


def unlisted(manifest: Path = MANIFEST) -> list[tuple[str, str]]:
    """(relative file, md5) of every file beside the manifest that it does not list."""
    rows = load_manifest(manifest)
    out = []
    for path in sorted(manifest.parent.rglob("*")):
        if (not path.is_file() or path.name in _NOT_FIXTURES or "__pycache__" in path.parts
                or path.name.endswith(".fixtures.json")):      # a package's sidecar listing, not a fixture
            continue
        rel = path.relative_to(manifest.parent).as_posix()
        if rel not in rows:
            out.append((rel, md5_of(path)))
    return out


if __name__ == "__main__":
    # Prints a manifest row skeleton (file and md5 filled) for every unlisted fixture; fill the other columns by hand.
    for rel, digest in unlisted():
        print(",".join([rel, "", "", "", "", "", digest, "", "", ""]))
