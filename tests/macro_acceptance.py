"""Macro suite aggregator and hermetic guard (M0; T-HERM-01, T-HERM-02; rulings sections 3.10 and 6).

`tests()` discovers every `tests/macro_*.py` module, wraps each of its `test_*` functions in the hermetic
guard, and brackets the suite with T-HERM-01 (every network touchpoint raises while the guard is armed)
and T-HERM-02 (the shipped read-only trees and TRADEGEN's `~/.tradegen` are byte-identical before and after).

The guard is armed around every macro test and restored in `finally`, not left in place for the whole
process: `engine/test_82` serves a loopback HTTP server through `data.net.session` and `cockpit/test_21`
reaches KIS when keys are present, so a process-wide patch at import would change inherited results.
"""
from __future__ import annotations

import contextlib
import csv
import functools
import hashlib
import importlib
import os
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
REGISTRY = TESTS / "macro_registry.csv"
# Shipped seeds and fixtures the suite may read but never write (rulings section 2; T-HERM-02).
READ_ONLY_TREES = ("data/macro", "core/rules", "core/calendars/data", "data/techfund",
                   "tests/fixtures/macro", "docs/asset_expansion/cards")
_MISSING = object()
_DEPTH = 0
_BEFORE: tuple[dict[str, str], tuple] | None = None


class HermeticViolation(RuntimeError):
    """A network touchpoint was called inside the macro suite."""


def _boom(*_a, **_k):
    raise HermeticViolation("network touchpoint called inside the macro suite (T-HERM-01)")


class _Refuse:
    """Stands in for a `requests` module or session: every attribute is a call that raises."""

    def __getattr__(self, name):
        return _boom


def _refuse_connect(self, *_a, **_k):
    raise HermeticViolation("socket connect refused inside the macro suite (T-HERM-01)")


def _touchpoints() -> list[tuple[object, str, object]]:
    import config
    from core.ficc import data as ficc_data
    from core.quant import history
    from data import kis_markets, net
    from data.crypto import crypto_client
    from data.fmp import quote_client
    from data.krx import kis_client, krx_market_client, opendart_client
    return [
        (ficc_data, "_fred_fetch", _boom), (ficc_data, "_yf_fetch", _boom), (ficc_data, "_requests", _Refuse()),
        (history, "_requests", _Refuse()),
        (crypto_client, "_get", _boom), (crypto_client, "_requests", _Refuse()),
        (kis_markets, "_requests", _Refuse()),
        (quote_client, "_requests", _Refuse()),
        (kis_client, "requests", _Refuse()), (kis_client, "_once", _Refuse()), (kis_client.KISClient, "_get", _boom),
        (opendart_client, "requests", _Refuse()), (krx_market_client, "requests", _Refuse()),
        (net.session, "request", _boom),                 # the shared session every other client binds
        (socket.socket, "connect", _refuse_connect), (socket.socket, "connect_ex", _refuse_connect),
        (config, "FICC_CACHE_TTL_SECONDS", 0.0),         # no disk cache answers or is written
    ]


@contextlib.contextmanager
def hermetic():
    """Patch every network touchpoint to raise; restore each one in `finally`. Re-entrant."""
    global _DEPTH
    if _DEPTH:
        _DEPTH += 1
        try:
            yield
        finally:
            _DEPTH -= 1
        return
    saved = []
    try:
        for obj, name, patch in _touchpoints():
            saved.append((obj, name, vars(obj).get(name, _MISSING)))
            setattr(obj, name, patch)
        _DEPTH += 1
        yield
    finally:
        _DEPTH = max(_DEPTH - 1, 0)
        for obj, name, original in reversed(saved):
            if original is _MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, original)


def tree_md5s() -> dict[str, str]:
    out = {}
    for rel in READ_ONLY_TREES:
        base = ROOT / rel
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                out[path.relative_to(ROOT).as_posix()] = hashlib.md5(path.read_bytes()).hexdigest()
    return out


def home_listing() -> tuple:
    """(relative path, size, mtime_ns) of every file the macro suite must never touch under the home dir:
    `~/.tradegen/macro` (the v2 artifact root), the operator rules store `~/.tradegen/trading/rules.json`, and
    TRADEGEN_MACRO_DIR when set. Not all of `~/.tradegen`: the legacy cockpit tests write `~/.tradegen/runs` by
    design, so a concurrent full run tripped T-HERM-02 falsely (Sprint 4 coordinator ruling). QUANTGEN's
    `~/.nextgen` is not watched: since the 2026-10-23 split it belongs to the other program."""
    import config
    home = config.state_root()
    roots = [home / "macro", home / "trading" / "rules.json"]
    if os.environ.get("TRADEGEN_MACRO_DIR"):
        roots.append(Path(os.environ["TRADEGEN_MACRO_DIR"]))
    rows = []
    for root in roots:
        if root.is_file():
            st = root.stat()
            rows.append((root.as_posix(), st.st_size, st.st_mtime_ns))
            continue
        if not root.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                path = Path(dirpath) / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                rows.append((path.relative_to(root).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


def snapshot() -> tuple[dict[str, str], tuple]:
    return tree_md5s(), home_listing()


def _wrap(fn):
    @functools.wraps(fn)
    def run():
        global _BEFORE
        if _BEFORE is None:
            _BEFORE = snapshot()
        with hermetic():
            fn()
    return run


# --------------------------------------------------------------------------- #
# T-HERM-01 / T-HERM-02
# --------------------------------------------------------------------------- #
def test_t_herm_01_every_touchpoint_raises():
    """Inside the guard every provider transport, the shared session and raw sockets raise."""
    assert _DEPTH > 0, "the hermetic guard is not armed"
    from core.ficc import data as ficc_data
    from core.quant import history
    from data import kis_markets, net
    from data.crypto import crypto_client
    from data.fmp import quote_client
    from data.krx import kis_client, krx_market_client, opendart_client
    dead = "http://127.0.0.1:9/"
    probes = {
        "fred": lambda: ficc_data._fred_fetch(["DGS10"], "2026-01-01"),
        "yahoo": lambda: ficc_data._yf_fetch(["SPY"], "5d"),
        "ficc session": lambda: ficc_data._requests.get(dead),
        "history session": lambda: history._requests.get(dead),
        "crypto": lambda: crypto_client._get(dead, label="probe"),
        "kis_markets session": lambda: kis_markets._requests.get(dead),
        "fmp quotes": lambda: quote_client._requests.get(dead),
        "kis session": lambda: kis_client.requests.get(dead),
        "kis token transport": lambda: kis_client._once.post(dead),
        "kis _get": lambda: object.__new__(kis_client.KISClient)._get("/uapi/probe", "T", {}),
        "opendart": lambda: opendart_client.requests.get(dead),
        "krx marketplace": lambda: krx_market_client.requests.get(dead),
        "shared session": lambda: net.session.get(dead, timeout=0.2),
        "raw socket": lambda: socket.create_connection(("127.0.0.1", 9), timeout=0.2),
    }
    leaks = []
    for label, probe in probes.items():
        try:
            probe()
            leaks.append(label)
        except HermeticViolation:
            pass
    assert not leaks, f"touchpoints that did not raise: {leaks}"


test_t_herm_01_every_touchpoint_raises.test_ids = ["T-HERM-01"]


def test_t_herm_02_shipped_trees_and_home_untouched():
    """The read-only trees and ~/.tradegen are byte-identical to the snapshot taken before the first macro test."""
    assert _BEFORE is not None, "no snapshot: the macro suite has not run"
    before_md5, before_home = _BEFORE
    after_md5, after_home = snapshot()
    changed = sorted(k for k in set(before_md5) | set(after_md5) if before_md5.get(k) != after_md5.get(k))
    assert not changed, f"shipped read-only files changed during the macro suite: {changed}"
    added = sorted(set(after_home) - set(before_home))
    removed = sorted(set(before_home) - set(after_home))
    assert not added and not removed, f"the macro suite touched ~/.tradegen: added {added[:5]}, removed {removed[:5]}"


test_t_herm_02_shipped_trees_and_home_untouched.test_ids = ["T-HERM-02"]


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def tests():
    found = []
    for path in sorted(TESTS.glob("macro_*.py")):
        if path.name == Path(__file__).name:
            continue
        stem = path.stem
        try:
            module = importlib.import_module(f"tests.{stem}")
        except Exception as exc:                      # one broken module must not abort the whole run
            def broken(exc=exc):
                raise exc
            found.append((f"{stem}/import", broken))
            continue
        for name, fn in sorted(vars(module).items()):
            if name.startswith("test_") and callable(fn):
                found.append((f"{stem}/{name}", _wrap(fn)))
    return ([(test_t_herm_01_every_touchpoint_raises.__name__, _wrap(test_t_herm_01_every_touchpoint_raises))]
            + sorted(found)
            + [(test_t_herm_02_shipped_trees_and_home_untouched.__name__, _wrap(test_t_herm_02_shipped_trees_and_home_untouched))])


def run_module(namespace: dict) -> int:
    """`python -m tests.<module>`: run that module's `test_*` functions under the hermetic guard and print
    PASS / NOT_RUN / FAIL; exit status 1 on any FAIL or when no test was found (an empty run is not a pass).
    Every macro module ends with `raise SystemExit(run_module(globals()))`."""
    import sys
    import time
    import traceback
    from tests.notrun import NotRun
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")
    found = sorted((n, f) for n, f in namespace.items() if n.startswith("test_") and callable(f))
    counts = {"PASS": 0, "NOT_RUN": 0, "FAIL": 0}
    for name, fn in found:
        t0, status, detail = time.perf_counter(), "PASS", ""
        try:
            with hermetic():
                fn()
        except NotRun as exc:
            status, detail = "NOT_RUN", exc.reason
        except Exception as exc:                                       # noqa: BLE001
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        counts[status] += 1
        print(f"{status} {name} {detail} ({time.perf_counter() - t0:.1f}s)")
    print()
    print(f"{counts['PASS']}/{len(found)} passed, {counts['FAIL']} failed, {counts['NOT_RUN']} not run")
    return 0 if found and not counts["FAIL"] else 1


def implemented_in() -> dict[str, str]:
    """test id -> `tests/<module>.py::<function>;...` for every discovered test carrying `test_ids`."""
    out: dict[str, set[str]] = {}
    for name, fn in tests():
        stem, _, func = name.rpartition("/")
        for tid in getattr(fn, "test_ids", ()):
            out.setdefault(tid, set()).add("tests/%s.py::%s" % (stem or Path(__file__).stem, func))
    return {tid: ";".join(sorted(v)) for tid, v in out.items()}


def sync_registry(path: Path = REGISTRY) -> int:
    """Rewrite the registry's `implemented_in` column from the test modules; returns the number of rows changed."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = list(reader.fieldnames or ()), list(reader)
    impl, changed = implemented_in(), 0
    for row in rows:
        want = impl.get(row["test_id"], "")
        changed += row["implemented_in"] != want
        row["implemented_in"] = want
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return changed


if __name__ == "__main__":
    print("implemented_in rows changed:", sync_registry())
