r"""TRADEGEN never touches QUANTGEN (split 2026-10-23): one refusal shared by config's path resolver and every writer
of persistent records (gate_ledger, governance). Standard library only, so pure modules such as gate_ledger (no
config import, T-LEDGER-01) can call it too.

A0 (compliance plan Task 2): `checked_target` is the final-target check a writer runs just before it opens a file,
temp and sidecar files included: QUANTGEN refused, no symlink, junction or hard link, optionally inside a folder.
`state_root` refuses a state root that holds a link, once per process and root (`scan_links`). This is path
discipline, not a security boundary."""
from __future__ import annotations

import os
from pathlib import Path

QUANTGEN_STATE = Path.home() / ".nextgen"                                        # its ledgers, frozen studies, KIS token
QUANTGEN_REPO = Path(__file__).resolve().parents[1].with_name("QUANTGEN")      # its frozen-study records
_LINK_SCAN: dict[str, str | None] = {}            # resolved state root -> None (clean) or the refusal message


def refuse_quantgen(path, what: str = "path") -> Path:
    r"""`path`, unless it lies inside QUANTGEN's state root or repository: then RuntimeError, before any I/O.
    Compared as resolved paths (case, 8.3 names, relative paths) and by file identity of every existing ancestor,
    which also catches \\?\, UNC-share and junction aliases of the same directory."""
    p = Path(path).resolve()
    for root in (QUANTGEN_STATE, QUANTGEN_REPO):
        if p.is_relative_to(root.resolve()) or (root.exists() and any(
                a.exists() and os.path.samefile(a, root) for a in (p, *p.parents))):
            raise RuntimeError(f"{what} {path} is inside QUANTGEN ({root}); TRADEGEN keeps its own state under "
                               "~/.tradegen and never reads or writes QUANTGEN's")
    return Path(path)


def _env(name: str) -> str:
    """An env var, stripped and unquoted; an unedited <placeholder> reads as unset (as config._clean)."""
    value = (os.environ.get(name) or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return "" if value.startswith("<") and value.endswith(">") else value


def checked_target(path, what: str = "path", *, within=None) -> Path:
    """`path`, checked just before a writer opens it: refused inside QUANTGEN, as a symlink or junction, as an existing
    file that has a second name (a hard link: writing it rewrites the other name too), or outside `within`.
    Creates nothing."""
    p = refuse_quantgen(path, what)
    if p.is_symlink() or p.is_junction():
        raise RuntimeError(f"{what} {path} is a symlink or junction; TRADEGEN writes real files only (A0)")
    if p.exists() and not p.is_dir():
        try:
            links = os.lstat(p).st_nlink
        except FileNotFoundError:                      # removed since exists(): no second name left to change
            links = 1
        if links > 1:
            raise RuntimeError(f"{what} {path} is a hard link; writing it would change another file (A0)")
    if within is not None and not p.resolve().is_relative_to(Path(within).resolve()):
        raise RuntimeError(f"{what} {path} lies outside {within} (A0)")
    return p


def _first_link(root: Path) -> str | None:
    """The refusal message when `root` itself or an entry under it is a link, a folder under it cannot be listed, or
    an entry cannot be stat'ed (fail closed); None when clean."""
    if root.is_symlink() or root.is_junction():
        return f"state root {root} is a symlink or junction; refused (A0)"

    def unlisted(err: OSError) -> None:
        if not isinstance(err, FileNotFoundError):     # a folder removed since its listing holds no link
            raise RuntimeError(f"state root {root}: cannot list {err.filename} ({type(err).__name__}); refused (A0)")

    # os.walk descends into a junction even with followlinks=False (3.13), so every entry of a folder is judged
    # before the walk goes below it. ponytail: one lstat per entry per process; memoise per subtree past ~100k files.
    try:
        for dirpath, dirnames, filenames in os.walk(root, onerror=unlisted, followlinks=False):
            here = Path(dirpath)
            for name in dirnames + filenames:
                if (here / name).is_symlink() or (here / name).is_junction():
                    return f"state root {root}: {here / name} is a symlink or junction; refused (A0)"
            for name in filenames:
                try:
                    if os.lstat(here / name).st_nlink > 1:
                        return f"state root {root}: {here / name} is a hard link; refused (A0)"
                except FileNotFoundError:              # removed by a writer since the listing: not a link
                    continue
                except OSError as exc:
                    return f"state root {root}: cannot stat {here / name} ({type(exc).__name__}); refused (A0)"
    except RuntimeError as exc:                        # raised by unlisted()
        return str(exc)
    return None


def scan_links(root) -> None:
    """RuntimeError when `root` or any entry under it is a symlink, a junction or a hard link, or cannot be listed or
    stat'ed. Memoised per resolved root, refusals included; a root that does not exist yet is not memoised."""
    root = Path(root)
    if not root.exists():
        return
    key = str(root.resolve())
    if key not in _LINK_SCAN:
        _LINK_SCAN[key] = _first_link(root)
    if _LINK_SCAN[key] is not None:
        raise RuntimeError(_LINK_SCAN[key])


def state_root() -> Path:
    """TRADEGEN_HOME, else ~/.tradegen: refused inside QUANTGEN before anything is walked, then refused when it holds
    a link (scan_links)."""
    root = refuse_quantgen(_env("TRADEGEN_HOME") or Path.home() / ".tradegen", "TRADEGEN_HOME")
    scan_links(root)
    return root
