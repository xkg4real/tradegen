"""Compliance suite, Task 13: the write-once approved store, the D14 code hash, snapshots and load_context (spec 5.2
"What is in force", 6.4, 8.2; P6, P19, P20, P21, P24, P34). Every test builds its own temp TRADEGEN_HOME and writes
only inside it; owner logs are signed with the fixed test key, and owner.PUBKEY_PATH is pointed at a temp file (the
repo key is never read or written)."""
from __future__ import annotations

import ast
import contextlib
import datetime as _dt
import importlib.metadata
import json
import operator
import sys
from pathlib import Path

import core.isolation
from core.compliance import gate, model, owner, rules
from tests import compliance_fixtures as F
from tests.compliance_fixtures import HELD, NOW, TABLES
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]


def _raises(fn, exc: type[BaseException]) -> BaseException:
    try:
        fn()
    except exc as caught:
        return caught
    raise AssertionError(f"{exc.__name__} not raised")


def test_store_round_trip_and_layout():
    raw = F.shipped_bytes("venues")
    with F.temp_home() as home:
        sha = F.store_blob(home, "venues", raw, (4, "a" * 64))
        base = owner.store_dir() / "venues"
        assert sha == model.sha256_hex(raw) == rules.file_sha256(raw)
        assert (base / f"{sha}.yaml").read_bytes() == raw and owner.store_get("venues", sha) == raw
        anchor = (base / f"{sha}.anchor.json").read_bytes()
        assert anchor == model.canonical_json({"seq": 4, "row_sha256": "a" * 64}).encode("utf-8")
        assert F.store_blob(home, "venues", raw, (9, "b" * 64)) == sha, "the same bytes again are fine"
        assert (base / f"{sha}.anchor.json").read_bytes() == anchor, "the first anchor is kept (P34)"
        assert list(owner.home().glob(".*.tmp")) == [], "a temp file was left behind"
        assert owner.store_get("venues", "0" * 64) is None and owner.store_get("rules", sha) is None
        assert owner.store_get("venues", "not-a-sha") is None and owner.store_get("odds", sha) is None


def test_store_is_write_once_and_refuses_altered_bytes():
    raw = F.shipped_bytes("rules")
    with F.temp_home() as home:
        sha = F.store_blob(home, "rules", raw, (1, "a" * 64))
        (owner.store_dir() / "rules" / f"{sha}.yaml").write_bytes(raw + b"# altered\n")
        assert owner.store_get("rules", sha) is None, "bytes that no longer hash to their name were served"
        assert "exists with other bytes" in str(_raises(lambda: F.store_blob(home, "rules", raw, (1, "a" * 64)),
                                                        RuntimeError))
        _raises(lambda: owner.store_put("odds", raw, (1, "a" * 64)), ValueError)
        _raises(lambda: owner.store_put("rules", raw, (0, "a" * 64)), ValueError)
        _raises(lambda: owner.store_put("rules", raw, (1, "A" * 64)), ValueError)
        _raises(lambda: owner.store_put("rules", "text", (1, "a" * 64)), TypeError)


def test_a_write_that_dies_leaves_no_partial_file():
    """A write killed before its rename (a failing fsync stands in for the crash) leaves nothing under the final
    name and no temp file, so the anchors still read and the same put succeeds afterwards."""
    raw = F.shipped_bytes("venues")
    sha = model.sha256_hex(raw)
    with F.temp_home() as home:
        saved = owner.os.fsync

        def dies(fd):
            raise OSError("simulated crash before the rename")

        owner.os.fsync = dies
        try:
            _raises(lambda: F.store_blob(home, "venues", raw, (4, "a" * 64)), OSError)
        finally:
            owner.os.fsync = saved
        assert not (owner.store_dir() / "venues" / f"{sha}.yaml").exists(), "a torn file under the final name"
        assert list(owner.home().glob(".*.tmp")) == [] and owner.read_anchors() == []
        assert F.store_blob(home, "venues", raw, (4, "a" * 64)) == sha and owner.store_get("venues", sha) == raw


def test_store_writes_refuse_a_junction():
    """A0: a store directory alias (Windows junction/POSIX symlink) refuses writes."""
    with F.temp_home() as home:
        elsewhere = home / "elsewhere"                   # outside compliance/: only the refusal stops the write
        elsewhere.mkdir()
        owner.store_dir().mkdir(parents=True)
        F.directory_link(owner.store_dir() / "rules", elsewhere)
        _raises(lambda: F.store_blob(home, "rules", F.shipped_bytes("rules"), (1, "a" * 64)), RuntimeError)
        assert list(elsewhere.iterdir()) == [], "a file landed through the junction"


def test_calendar_store_matches_calendar_sha256():
    """P21: the calendar set is stored as a folder of its 17 files, named by rules.calendar_sha256."""
    data_dir = ROOT / "core" / "calendars" / "data"
    files = sorted(p.name for p in data_dir.iterdir() if p.is_file())
    stream = rules.calendar_stream(data_dir)
    with F.temp_home() as home:
        sha = F.store_blob(home, "calendar", stream, (2, "c" * 64))
        assert sha == rules.calendar_sha256(data_dir), "the stream is not what calendar_sha256 hashes"
        stored = owner.store_dir() / "calendar" / sha
        assert len(files) == 17 and sorted(p.name for p in stored.iterdir()) == files
        assert all((stored / name).read_bytes() == (data_dir / name).read_bytes() for name in files)
        assert owner.store_get("calendar", sha) == stream
        (stored / "extra.yaml").write_bytes(b"x: 1\n")
        assert owner.store_get("calendar", sha) is None, "a file added to a stored set went unnoticed"
        for junk in (b"", b"x", b"a\0b", b"b\0x\0a\0y\0", b"../up\0x\0"):
            _raises(lambda: owner.store_put("calendar", junk, (2, "c" * 64)), ValueError)


def test_a_stored_calendar_set_with_a_link_is_not_stored():
    """One framing (rules.calendar_stream): a junction inside a stored calendar folder is refused, where reading the
    folder as plain files would skip it and still match the hash."""
    data_dir = ROOT / "core" / "calendars" / "data"
    with F.temp_home() as home:
        sha = F.store_blob(home, "calendar", rules.calendar_stream(data_dir), (2, "c" * 64))
        stored = owner.store_dir() / "calendar" / sha
        assert owner.store_get("calendar", sha) == rules.calendar_stream(data_dir)
        elsewhere = home / "elsewhere"
        elsewhere.mkdir()
        F.directory_link(stored / "linked", elsewhere)
        assert owner.store_get("calendar", sha) is None, "a stored calendar set holding a link was served"
        assert "is a link" in str(_raises(lambda: rules.calendar_stream(stored), rules.Invalid))
        assert rules.calendar_sha256(data_dir) == sha, "the real set still hashes to its stream"


def test_code_files_is_the_import_closure():
    """P6 on the real tree: core/__init__.py, core/isolation.py, core/compliance/*.py, core/odds/*.py, execution/*.py
    (E1 spec 8), recursive E2/E3 packages and the RECORD files of PyYAML and cryptography; never config.py, data/, core/quant/, core/calendars/
    or core/engine/ (the import allowlists keep the closure small)."""
    files = owner.code_files(ROOT)
    names = [name for name, _ in files]
    assert names == sorted(set(names)), "not sorted, or a repeat"
    repo = {name for name in names if not name.startswith("venv:")}
    expected = {"core/__init__.py", "core/isolation.py"} | {
        f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")} | {
        f"execution/{p.name}" for p in (ROOT / "execution").glob("*.py")} | {
        p.relative_to(ROOT).as_posix() for package in ("execution_control", "execution_orders", "execution_accounts", "execution_network", "execution_launch")
        for p in (ROOT / package).rglob("*.py")}
    assert repo == expected, sorted(repo ^ expected)
    assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)
    assert not any(name.startswith(("core/quant/", "core/calendars/", "core/engine/")) for name in repo), repo
    assert dict(files)["core/isolation.py"] == model.sha256_hex((ROOT / "core" / "isolation.py").read_bytes())
    assert owner.code_hash(ROOT) == model.sha256_hex(model.canonical_json(files)) == owner.code_hash(ROOT)
    venv = set(names) - repo
    yaml_record = f"venv:PyYAML-{importlib.metadata.version('PyYAML')}.dist-info/RECORD"
    assert yaml_record in venv, venv
    try:
        crypto_record = f"venv:cryptography-{importlib.metadata.version('cryptography')}.dist-info/RECORD"
    except importlib.metadata.PackageNotFoundError:
        raise NotRun("PENDING: cryptography not installed (Task 10)") from None
    assert venv == {yaml_record, crypto_record}, venv


def test_code_files_counts_lazy_imports_and_skips_main_and_type_checking():
    """P6 on a synthetic tree: a function-level import, relative imports (`.` and `..`) and an in-repo module outside
    core/ count, every ancestor __init__.py joins, and the TYPE_CHECKING (bare from typing, or `typing.`) and
    `__name__ == "__main__"` bodies do not (their else branch does). Anything else is scanned, because its body can run
    at import: an `!=` test, a bare TYPE_CHECKING that is a local (or rebound) name, and `not TYPE_CHECKING`; and a
    guard whose name the module rebinds or never imports plainly at its top level (typing rebound, `import os as
    typing`, no `import typing`, one inside a function only, `__name__` assigned or a parameter), or that the module
    can change without a binding (an attribute store, `__class__` included, setattr, globals(), sys.modules, a
    function's __globals__, a frame's f_globals, f_locals or f_builtins, gc.get_referents, gc.get_referrers or
    gc.get_objects), is scanned too (R4)."""
    sources = {
        "config.py": "",
        "core/__init__.py": "",
        "core/compliance/__init__.py": "",
        "core/compliance/a.py": ("import typing\n"
                                 "from typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.typed\n"
                                 "if typing.TYPE_CHECKING:\n    import core.typed2\n"
                                 "def f():\n    import config\n    from core.pkg import lazy\n    return config, lazy\n"
                                 "if __name__ == \"__main__\":\n    import core.cli\n"
                                 "else:\n    import core.kept\n"),
        "core/compliance/b.py": "if __name__ != \"__main__\":\n    import core.neq\n",
        "core/compliance/c.py": "TYPE_CHECKING = True\nif TYPE_CHECKING:\n    import core.local_tc\n",
        "core/compliance/d.py": ("from typing import TYPE_CHECKING\nTYPE_CHECKING = True\n"
                                 "if TYPE_CHECKING:\n    import core.rebound\n"),
        "core/compliance/e.py": "from typing import TYPE_CHECKING\nif not TYPE_CHECKING:\n    import core.negated\n",
        "core/compliance/f.py": "if \"__main__\" == __name__:\n    import core.rev_cli\n",
        "core/compliance/h.py": ("import types\nimport typing\ntyping = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.rebound_typing\n"),
        "core/compliance/i.py": "__name__ = \"__main__\"\nif __name__ == \"__main__\":\n    import core.rebound_main\n",
        "core/compliance/j.py": "import os as typing\nif typing.TYPE_CHECKING:\n    import core.alias_typing\n",
        "core/compliance/k.py": "if typing.TYPE_CHECKING:\n    import core.unbound_typing\n",
        "core/compliance/l.py": ("def main(__name__=None):\n    return __name__\n"
                                 "if __name__ == \"__main__\":\n    import core.param_main\n"),
        "core/compliance/m.py": ("import typing\ntyping.TYPE_CHECKING = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.stored_typing\n"),
        "core/compliance/n.py": ("import typing\nsetattr(typing, \"TYPE_CHECKING\", True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.setattr_typing\n"),
        "core/compliance/o.py": ("globals()[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.globals_main\n"),
        "core/compliance/p.py": ("import sys\nimport types\n"
                                 "sys.modules[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "import typing\nif typing.TYPE_CHECKING:\n    import core.modules_typing\n"),
        "core/compliance/q.py": ("import typing\ntyping.TYPE_CHECKING = True\nfrom typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.stored_bare\n"),
        "core/compliance/r.py": ("import sys\nsys._getframe().f_globals[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.frame_main\n"),
        "core/compliance/s.py": ("import sys\nfrom typing import TYPE_CHECKING\n"
                                 "sys._getframe().f_locals[\"TYPE_CHECKING\"] = True\n"
                                 "if TYPE_CHECKING:\n    import core.frame_bare\n"),
        "core/compliance/t.py": ("import types\nimport typing\nclass M(types.ModuleType):\n"
                                 "    TYPE_CHECKING = property(lambda self: True)\ntyping.__class__ = M\n"
                                 "if typing.TYPE_CHECKING:\n    import core.class_typing\n"),
        "core/compliance/u.py": ("def _f():\n    pass\n_f.__globals__[\"__name__\"] = \"__main__\"\n"
                                 "if __name__ == \"__main__\":\n    import core.fn_globals_main\n"),
        "core/compliance/v.py": ("import typing\ntyping.cast.__globals__[\"TYPE_CHECKING\"] = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.fn_globals_typing\n"),
        "core/compliance/w.py": ("import typing\ntyping.cast.__globals__[\"TYPE_CHECKING\"] = True\n"
                                 "from typing import TYPE_CHECKING\n"
                                 "if TYPE_CHECKING:\n    import core.fn_globals_bare\n"),
        "core/compliance/x.py": ("import gc, typing\ngc.get_referents(typing)[0][\"TYPE_CHECKING\"] = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.gc_typing\n"),
        "core/compliance/y.py": ("import sys, types\ndef _never():\n    import typing\n"
                                 "sys._getframe().f_builtins[\"typing\"] = types.SimpleNamespace(TYPE_CHECKING=True)\n"
                                 "if typing.TYPE_CHECKING:\n    import core.builtins_typing\n"),
        "core/compliance/z.py": ("import gc, typing\nfor o in gc.get_objects():\n"
                                 "    if isinstance(o, dict) and o.get(\"__name__\") == \"typing\":\n"
                                 "        o[\"TYPE_CHECKING\"] = True\n"
                                 "if typing.TYPE_CHECKING:\n    import core.gc_objects_typing\n"),
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "", "core/frame_main.py": "", "core/frame_bare.py": "",
        "core/class_typing.py": "",
        "core/fn_globals_main.py": "", "core/fn_globals_typing.py": "", "core/fn_globals_bare.py": "",
        "core/gc_typing.py": "", "core/builtins_typing.py": "", "core/gc_objects_typing.py": "",
        "core/pkg/__init__.py": "",
        "core/pkg/lazy.py": "from . import sibling\nfrom .. import upper\n",
        "core/pkg/sibling.py": "import json\n",
        "core/typed.py": "", "core/typed2.py": "", "core/cli.py": "", "core/kept.py": "", "core/upper.py": "",
        "core/unused.py": "",
    }
    with F.temp_home() as home:
        root = home / "code_tree"
        for rel, text in sources.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
        repo = {name for name, _ in owner.code_files(root) if not name.startswith("venv:")}
    assert repo == {"config.py", "core/__init__.py", "core/compliance/__init__.py", "core/compliance/a.py",
                    "core/kept.py", "core/pkg/__init__.py", "core/pkg/lazy.py", "core/pkg/sibling.py",
                    "core/upper.py",
                    "core/compliance/b.py", "core/compliance/c.py", "core/compliance/d.py", "core/compliance/e.py",
                    "core/compliance/f.py",
                    "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
                    "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
                    "core/compliance/p.py", "core/compliance/q.py", "core/compliance/r.py", "core/compliance/s.py",
                    "core/compliance/t.py", "core/compliance/u.py", "core/compliance/v.py", "core/compliance/w.py",
                    "core/compliance/x.py", "core/compliance/y.py", "core/compliance/z.py",
                    "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py",
                    "core/unbound_typing.py", "core/param_main.py", "core/stored_typing.py",
                    "core/setattr_typing.py", "core/globals_main.py", "core/modules_typing.py",
                    "core/stored_bare.py", "core/frame_main.py", "core/frame_bare.py", "core/class_typing.py",
                    "core/fn_globals_main.py", "core/fn_globals_typing.py", "core/fn_globals_bare.py",
                    "core/gc_typing.py", "core/builtins_typing.py", "core/gc_objects_typing.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
    trusted = "import typing\nfrom typing import TYPE_CHECKING\n"
    assert owner._guards(ast.parse(trusted)) == (True, True, True)
    nested = "def f():\n    import typing\n    from typing import TYPE_CHECKING\n"      # top level only
    assert owner._guards(ast.parse(nested)) == (False, False, True)
    for route in ("delattr(typing, 'x')", "vars(typing)", "locals()", "typing.__dict__", "import builtins\nbuiltins",
                  "__builtins__", "typing.__name__ = 'x'", "del typing.TYPE_CHECKING",
                  "import sys\nsys._getframe().f_builtins", "import gc\ngc.get_referrers(typing)",
                  "import gc\ngc.get_objects()"):
        assert owner._guards(ast.parse(trusted + route + "\n")) == (False, False, False), route


def test_snapshot_is_write_once_and_rebuilt_from_the_store():
    state = F.approved()
    older = F.shipped_bytes("instruments") + b"\n# an earlier approved map\n"
    with F.temp_home() as home:
        for kind in TABLES:
            F.store_blob(home, kind, F.shipped_bytes(kind), (2, "a" * 64))
        F.store_blob(home, "instruments", older, (1, "b" * 64))
        assert owner.latest_snapshot() is None
        path = owner.write_snapshot(state, (7, "c" * 64))
        assert path.parent == owner.snapshots_dir() and path.name == f"{state.seq:08d}-{state.state_hash[:16]}.json"
        assert owner.write_snapshot(state, (9, "d" * 64)) == path
        kept = json.loads(path.read_bytes())
        assert kept["head"] == [7, "c" * 64], "the first head is kept as the anchor (P34)"
        snap = owner.latest_snapshot()
        assert snap is not None and snap.valid and (snap.state_hash, snap.seq) == (state.state_hash, state.seq)
        assert len(snap.history_maps) == 1, "the earlier stored map is the exit fallback"
        kept["hashes"]["rules"] = "0" * 64
        path.write_bytes(model.canonical_json(kept).encode("utf-8"))
        _raises(lambda: owner.write_snapshot(state, (9, "d" * 64)), RuntimeError)
        assert owner.latest_snapshot() is None, "a snapshot naming missing bytes was used"
        _raises(lambda: owner.write_snapshot(model.ApprovedState.invalid("x"), (9, "d" * 64)), ValueError)


def test_latest_snapshot_skips_malformed_files():
    """A newer snapshot file that is malformed is skipped, never raised: the newest intact one is still the D11
    fallback."""
    state = F.approved()
    good = {"state_seq": state.seq, "hashes": dict(state.hashes), "head": [7, "c" * 64]}
    bad = {"1": json.dumps(good).encode("utf-8"),                                   # no state_hash
           "2": json.dumps([7, "c" * 64]).encode("utf-8"),                         # not an object
           "3": json.dumps({**good, "state_hash": state.state_hash, "hashes": ["x"]}).encode("utf-8"),
           "4": b"[" * 100_000 + b"]" * 100_000}                                    # nested past the recursion limit
    with F.temp_home() as home:
        for kind in TABLES:
            F.store_blob(home, kind, F.shipped_bytes(kind), (2, "a" * 64))
        owner.write_snapshot(state, (7, "c" * 64))
        for n, raw in bad.items():
            (owner.snapshots_dir() / f"99999999-{n:0>16}.json").write_bytes(raw)
            snap = owner.latest_snapshot()
            assert snap is not None and snap.state_hash == state.state_hash, n


# --------------------------------------------------------------------------- #
# load_context (spec 6.4, 8.2; P19, P24): temp homes signed with the fixed test key
# --------------------------------------------------------------------------- #
# NOW, HELD, TABLES and the signed-home helpers live in tests/compliance_fixtures.py (odds plan Task 4, Q21), so the
# odds suite builds the same homes; the old private names stay bound to them, so no test below changes.
_pubkey_at = F.pubkey_at
_owner_key = F.owner_key
_sign = F.sign
_approve = F.approve
_other_code = F.other_code
_full_home = F.full_home


def test_no_owner_key_blocks_every_new_exposure():
    """P24: before owner act 1 there is no owner_pubkey.pem, so owner state is BROKEN and nothing new passes."""
    F.test_key()                                    # NotRun PENDING without cryptography, which is reported first
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        ctx = owner.load_context(NOW, HELD)
        assert not ctx.owner.ok and ctx.owner.reason == "no owner key yet: owner act 1", ctx.owner.reason
        assert not ctx.active.valid and not ctx.code_signed and ctx.snapshot is None and model.is_sealed(ctx)
        assert ctx.owner.head == (0, "") and ctx.owner.fingerprint == ""
        for intent in (F.intent(), F.intent(venue="okx", counter_symbol="USDT"),
                       F.intent(venue="kis", symbol="005930", counter_symbol="KRW", asset="krx_share", quantity=1.0,
                                notional_krw=60_000.0)):
            assert gate.decide(intent, ctx).verdict == model.BLOCK, intent
        assert not (home / "compliance").exists(), "a load without a key wrote something"


def test_missing_cryptography_is_broken_before_the_key_check():
    """Spec 6.4: an ImportError means BROKEN with a reason naming the package, with or without a pem."""
    names = [k for k in sys.modules if k == "cryptography" or k.startswith("cryptography.")]
    saved = {k: sys.modules[k] for k in names}
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem") as pem:
        try:
            for k in names:
                sys.modules[k] = None
            sys.modules["cryptography"] = None
            for with_pem in (False, True):
                if with_pem:
                    pem.write_bytes(b"-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n")
                ctx = owner.load_context(NOW, HELD)
                assert ctx.owner.reason == "cryptography missing: install it (Task 10)", (with_pem, ctx.owner.reason)
                assert not ctx.active.valid and gate.decide(F.intent(), ctx).verdict == model.BLOCK
        finally:
            for k in [k for k in sys.modules if k == "cryptography" or k.startswith("cryptography.")]:
                del sys.modules[k]
            sys.modules.update(saved)


def test_full_home_allows_an_upbit_buy():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and ctx.active.valid and ctx.code_signed, (ctx.owner.reason, ctx.active.reason)
        assert ctx.date == _dt.date(2026, 10, 24) and model.is_sealed(ctx) and "age_of_majority" in ctx.owner.flags
        assert dict(ctx.active.hashes) == {kind: model.sha256_hex(F.shipped_bytes(kind)) for kind in TABLES}
        assert ctx.owner.fingerprint == owner.fingerprint(owner.read_pubkey(owner.PUBKEY_PATH))
        decision = gate.decide(F.intent(), ctx)
        assert decision.verdict == model.ALLOW, decision.reasons


def test_draft_change_blocks_nothing_until_signed():
    """The in-force bytes come from the store: a repo draft that differs from them changes nothing (spec 8.2)."""
    signed = F.shipped_bytes("rules") + b"\n# the signed version differs from the repo draft\n"
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, rules_raw=signed)
        ctx = owner.load_context(NOW, HELD)
        draft = (ROOT / "core" / "compliance" / "kr_rules.yaml").read_bytes()
        assert ctx.active.hashes["rules"] == model.sha256_hex(signed) != model.sha256_hex(draft)
        assert gate.decide(F.intent(), ctx).verdict == model.ALLOW


def test_only_the_latest_approval_counts():
    """A superseded file stays in the store but never counts again unless a new entry signs it (spec 5.2)."""
    old = F.shipped_bytes("rules") + b"\n# an earlier approved version\n"
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        key = _full_home(home, rules_raw=old)
        new = _approve(home, key, "rules", F.shipped_bytes("rules"))
        assert owner.store_get("rules", model.sha256_hex(old)) == old, "the old bytes are still on disk"
        assert owner.load_context(NOW, HELD).active.hashes["rules"] == new
        again = _approve(home, key, "rules", old)
        assert owner.load_context(NOW, HELD).active.hashes["rules"] == again == model.sha256_hex(old)


def test_entries_stamped_after_now_do_not_count():
    """An approval or a code approval stamped after `now` counts only from its stamp on (spec 6.4; _up_to)."""
    later = F.shipped_bytes("rules") + b"\n# signed with a stamp after now\n"
    stamp = "2026-10-25T00:00:00Z"
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        key = _full_home(home)
        F.store_blob(home, "rules", later,
                     _sign(key, "approved", {"kind": "rules", "sha256": model.sha256_hex(later)}, stamp))
        _other_code(key, stamp)
        before = owner.load_context(NOW, HELD)
        assert before.active.hashes["rules"] == model.sha256_hex(F.shipped_bytes("rules")) and before.code_signed
        after = owner.load_context(_dt.datetime(2026, 10, 25, 9, 0, tzinfo=model.KST), HELD)
        assert after.active.hashes["rules"] == model.sha256_hex(later) and not after.code_signed


def test_a_kind_without_a_signed_approval_is_unapproved():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _approve(home, _owner_key(home), "rules", F.shipped_bytes("rules"))
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and ctx.active.reason == "unapproved: no signed approval for instruments", ctx.active
        assert ctx.snapshot is None and gate.decide(F.intent(), ctx).verdict == model.BLOCK


def test_earlier_instrument_maps_are_the_exit_fallback():
    """The log's earlier instrument approvals, read back from the store, become history_maps (spec 6.2 step 0)."""
    newer = F.shipped_bytes("instruments") + b"\n# a later approved map\n"
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        current = _approve(home, _full_home(home), "instruments", newer)
        ctx = owner.load_context(NOW, HELD)
        assert ctx.active.valid and ctx.active.hashes["instruments"] == current, ctx.active.reason
        assert len(ctx.active.history_maps) == 1, "the shipped map approved first is the fallback"


def test_unsigned_code_blocks_new_exposure_not_exits():
    """The latest code_approved names another hash: a buy is BLOCK "unsigned code", a close still passes."""
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _other_code(_full_home(home))
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and ctx.active.valid and not ctx.code_signed
        buy = gate.decide(F.intent(), ctx)
        assert buy.verdict == model.BLOCK and "unsigned code" in buy.reasons, buy.reasons
        assert gate.decide(F.intent(action="sell"), ctx).verdict == model.ALLOW_EXIT


def test_altered_store_bytes_block_at_load():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        sha = model.sha256_hex(F.shipped_bytes("rules"))
        (owner.store_dir() / "rules" / f"{sha}.yaml").write_bytes(F.shipped_bytes("rules") + b"# edited\n")
        ctx = owner.load_context(NOW, HELD)
        assert not ctx.active.valid and ctx.active.reason.startswith("store: rules"), ctx.active.reason
        assert gate.decide(F.intent(), ctx).verdict == model.BLOCK


def test_unreadable_key_log_or_link_is_broken():
    """A pem that is no key, an unreadable alerts.jsonl and a link in the state root each give a BROKEN owner state
    that says why (A0 names the linked entry), never "internal error"; new exposure is BLOCK each time."""
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem") as pem:
        _full_home(home)
        good = pem.read_bytes()
        pem.write_bytes(b"not a key\n")
        contexts = [owner.load_context(NOW, HELD)]
        pem.write_bytes(good)
        owner.alerts_path().write_bytes(b"{not json\n")
        contexts.append(owner.load_context(NOW, HELD))
        owner.alerts_path().unlink()
        (home / "elsewhere").mkdir()
        F.directory_link(owner.home() / "linked", home / "elsewhere")
        core.isolation._LINK_SCAN.clear()                 # this root's earlier clean scan was memoised (P7)
        contexts.append(owner.load_context(NOW, HELD))
        reasons = [ctx.owner.reason for ctx in contexts]
        assert reasons[0].startswith("owner key unreadable ("), reasons
        assert reasons[1].startswith("owner log unreadable: alerts.jsonl line 1"), reasons
        assert reasons[2].startswith("owner log unreadable: ") and "linked" in reasons[2], reasons
        assert contexts[2].snapshot is None
        assert all(gate.decide(F.intent(), ctx).verdict == model.BLOCK for ctx in contexts)


def test_positions_are_validated():
    """P19: the caller's positions must be finite and >= 0 with equity > 0, or nothing is in force at all."""
    bad = (model.Positions(equity_krw=float("nan")), model.Positions(equity_krw=0.0),
           model.Positions(equity_krw=1e6, holdings={("upbit", "BTC"): -1.0}),
           model.Positions(equity_krw=1e6, exposure={"okx": model.Exposure(held_krw=float("inf"))}),
           {"equity_krw": 1e6})
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        for positions in bad:
            ctx = owner.load_context(NOW, positions)
            assert not ctx.active.valid and ctx.active.reason.startswith("positions: "), (positions, ctx.active)
            assert ctx.snapshot is None and ctx.equity_krw == 0.0 and model.is_sealed(ctx)
            for intent in (F.intent(), F.intent(action="sell")):
                assert gate.decide(intent, ctx).verdict == model.BLOCK, (positions, intent)


def test_context_keeps_its_own_copy_of_the_positions():
    """The sealed context holds read-only copies: changing the caller's dicts afterwards changes nothing it holds."""
    holdings, reservations = {("upbit", "BTC"): 0.01}, {"r1": 10.0}
    positions = model.Positions(equity_krw=1e6, holdings=holdings,
                                exposure={"okx": model.Exposure(held_krw=0.0, reservations=reservations)})
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        ctx = owner.load_context(NOW, positions)
        holdings[("upbit", "BTC")], reservations["r1"] = 5.0, 1e9
        assert ctx.holdings[("upbit", "BTC")] == 0.01 and ctx.exposure["okx"].reservations["r1"] == 10.0
        _raises(lambda: operator.setitem(ctx.holdings, ("upbit", "ETH"), 1.0), TypeError)
        _raises(lambda: operator.setitem(ctx.exposure["okx"].reservations, "r2", 1.0), TypeError)


def test_snapshot_written_then_used_when_the_log_breaks():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        first = owner.load_context(NOW, HELD)
        name = f"{first.active.seq:08d}-{first.active.state_hash[:16]}.json"
        assert [p.name for p in owner.snapshots_dir().iterdir()] == [name]
        assert first.snapshot is not None and first.snapshot.state_hash == first.active.state_hash
        again = owner.load_context(NOW, HELD)
        assert again.owner.ok and again.active.state_hash == first.active.state_hash, "its own snapshot broke it"
        newer = json.loads((owner.snapshots_dir() / name).read_bytes())
        del newer["state_hash"]                          # a newer malformed snapshot is skipped, never raised
        (owner.snapshots_dir() / "99999999-0000000000000000.json").write_bytes(json.dumps(newer).encode("utf-8"))
        skipped = owner.load_context(NOW, HELD)
        assert skipped.owner.ok and skipped.active.valid, (skipped.owner.reason, skipped.active.reason)
        assert skipped.snapshot is not None and skipped.snapshot.state_hash == first.active.state_hash
        with open(owner.log_path(), "ab") as fh:
            fh.write(b'{"seq": 99}\n')
        broken = owner.load_context(NOW, HELD)
        assert not broken.owner.ok and not broken.active.valid
        assert broken.snapshot is not None and broken.snapshot.state_hash == first.active.state_hash
        assert gate.decide(F.intent(action="sell"), broken).verdict == model.ALLOW_EXIT
        assert gate.decide(F.intent(), broken).verdict == model.BLOCK


def test_a_failed_snapshot_write_invalidates_the_state():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        owner.snapshots_dir().write_bytes(b"")          # a file where the snapshot folder belongs
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and not ctx.active.valid and ctx.active.reason.startswith("snapshot: "), ctx.active
        assert ctx.snapshot is None and gate.decide(F.intent(), ctx).verdict == model.BLOCK


def test_session_state_comes_from_the_log():
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        key = _full_home(home)
        _sign(key, "session_armed", {"session_id": "S1"})
        assert owner.load_context(NOW, HELD, session_id="S1").session == model.SessionState(session_id="S1", armed=True)
        assert owner.load_context(NOW, HELD, session_id="S2").session == model.SessionState(session_id="S2")
        odd = owner.load_context(NOW, HELD, session_id=5)
        assert odd.owner.reason == "load_context: internal error TypeError" and model.is_sealed(odd), odd.owner
        assert not odd.active.valid and not odd.code_signed and gate.decide(F.intent(), odd).verdict == model.BLOCK


def test_key_changed_since_the_first_alert_row():
    """P20: the first fingerprint recorded in alerts.jsonl must be the log's first key, else KEY CHANGED."""
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        row = {"utc": "2026-10-20T00:00:00Z", "channel": "toast", "result": "ok", "code": 3, "due": [],
               "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": "SHA256:" + "e" * 64}
        owner.alerts_path().write_bytes(model.canonical_json(row).encode("utf-8") + b"\n")
        ctx = owner.load_context(NOW, HELD)
        assert not ctx.owner.ok and ctx.owner.reason == "KEY CHANGED since 2026-10-20", ctx.owner.reason
        assert gate.decide(F.intent(), ctx).verdict == model.BLOCK


def test_naive_or_out_of_range_now_raises():
    """A naive `now`, a non-datetime, or one that cannot be converted to UTC or Asia/Seoul is ValueError."""
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for now in (_dt.datetime(2026, 10, 24, 9, 0), "2026-10-24", _dt.datetime(1, 1, 1, tzinfo=model.KST),
                    _dt.datetime(9999, 12, 31, 23, 59, tzinfo=_dt.timezone.utc)):
            _raises(lambda: owner.load_context(now, HELD), ValueError)


def test_decision_date_is_the_asia_seoul_date_of_now():
    """Spec 8 item 7, the moment-to-date side (Task 8 tests the gate on the dates): ctx.date is the Asia/Seoul date
    of `now` in whatever zone `now` is given, so 15:00 UTC on 12-02 is already 2026-12-03, the OKX auto_off day."""
    utc = _dt.timezone.utc
    pairs = ((_dt.datetime(2026, 12, 2, 14, 59, 59, tzinfo=utc), _dt.datetime(2026, 12, 2, 15, 0, 0, tzinfo=utc)),
             (_dt.datetime(2026, 12, 2, 23, 59, 59, tzinfo=model.KST),
              _dt.datetime(2026, 12, 3, 0, 0, 0, tzinfo=model.KST)))
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for before, after in pairs:
            assert owner.load_context(before, HELD).date == _dt.date(2026, 12, 2), before
            assert owner.load_context(after, HELD).date == _dt.date(2026, 12, 3), after


# --------------------------------------------------------------------------- #
# Odds plan Task 4 (Q19, Q21): calendar_in_force and the _calendar_approval it shares with the --check line, and the
# signed-home helpers as public fixtures. Every calendar case also checks that calendar_in_force(now) is the sha
# exactly when _calendar_approval(now) is ("ok", sha) (Q19).
# --------------------------------------------------------------------------- #
def _calendar_now(now: _dt.datetime) -> tuple[str, str]:
    """owner._calendar_approval(now), once calendar_in_force(now) is checked to agree with it (Q19)."""
    found = owner._calendar_approval(now)
    assert owner.calendar_in_force(now) == (found[1] if found[0] == "ok" else None), found
    return found


def _fixture_calendar() -> bytes:
    """The calendar stream of the signed temp-dir fixture set; imported here, as tests/compliance_tables.py does, so
    a broken macro module fails only the tests that need it."""
    from tests.macro_m1_calendars import fixture_set
    return rules.calendar_stream(fixture_set().data_dir)


def test_signed_home_helpers_are_the_public_fixtures():
    """Q21: the signed-home helpers live in tests/compliance_fixtures.py and this module's old names are bound to
    them, so these tests run the code the odds suite runs. They write only inside the temp home: approve refuses a
    state root other than its `home`, owner_key a pem and sign an owner log outside the temp dir (so never the
    repo's trust anchor or the real ~/.tradegen), each before writing. Every case stays inside temp homes even if a
    guard were missing."""
    import tempfile
    pairs = ((_pubkey_at, F.pubkey_at), (_owner_key, F.owner_key), (_sign, F.sign), (_approve, F.approve),
             (_other_code, F.other_code), (_full_home, F.full_home), (NOW, F.NOW), (HELD, F.HELD),
             (TABLES, F.TABLES))
    assert all(mine is theirs for mine, theirs in pairs), [mine for mine, theirs in pairs if mine is not theirs]
    assert TABLES == ("rules", "instruments", "venues") and NOW == _dt.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)
    assert HELD == model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})
    with F.temp_home() as home, F.temp_home():                          # the state root is another temp home
        _raises(lambda: _approve(home, None, "rules", b"x"), AssertionError)
        assert not owner.home().exists() and not (home / "compliance").exists()
    with F.temp_home() as home, _pubkey_at(home / "k.pem"):
        saved, tempfile.tempdir = tempfile.tempdir, str(home / "elsewhere")  # the pem and the log are outside it
        try:
            _raises(lambda: _owner_key(home), AssertionError)
            _raises(lambda: _sign(None, "approved", {}), AssertionError)
        finally:
            tempfile.tempdir = saved
        assert not (home / "k.pem").exists() and not owner.log_path().exists()
    with F.temp_home() as home, F.temp_home() as other, _pubkey_at(other / "k.pem"):   # in the temp dir, not in home
        _raises(lambda: _owner_key(home), AssertionError)
        assert not (other / "k.pem").exists()


def test_full_home_signs_the_odds_keywords():
    """Q21: full_home approves `venues_raw` instead of the shipped venues and `calendar_raw` as kind calendar, and
    signs `limits` as limit_set and `cap` as cap_set, after the entries it always signed. All are stamped
    2026-10-23T00:00:00Z, so the limits and the cap count from NOW's date on (D12). Without them the log is the
    same as before."""
    venues = F.shipped_bytes("venues") + b"\n# a signed venues version for the odds suite\n"
    stream = _fixture_calendar()
    limits = {"total_loss_floor_krw": 21_000.0, "daily_loss_krw": 5_000.0}
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, venues_raw=venues, calendar_raw=stream, limits=limits, cap=0.10)
        ctx = owner.load_context(NOW, HELD)
        assert ctx.owner.ok and ctx.active.valid and ctx.code_signed, (ctx.owner.reason, ctx.active.reason)
        assert ctx.active.hashes["venues"] == model.sha256_hex(venues) != model.sha256_hex(F.shipped_bytes("venues"))
        assert dict(ctx.owner.limits) == limits and dict(ctx.owner.caps) == {"okx_equity_share": 0.10}, ctx.owner
        assert _calendar_now(NOW) == ("ok", model.sha256_hex(stream))
        kinds = [json.loads(line)["kind"] for line in owner.log_path().read_bytes().splitlines()]
        assert kinds == ["approved"] * 3 + ["code_approved", "age_of_majority", "approved", "limit_set", "cap_set"]
        assert {json.loads(line)["utc"] for line in owner.log_path().read_bytes().splitlines()} == \
            {"2026-10-23T00:00:00Z"}
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home)
        ctx = owner.load_context(NOW, HELD)
        kinds = [json.loads(line)["kind"] for line in owner.log_path().read_bytes().splitlines()]
        assert kinds == ["approved"] * 3 + ["code_approved", "age_of_majority"], kinds
        assert dict(ctx.owner.limits) == {} and dict(ctx.owner.caps) == {}, ctx.owner
        assert ctx.active.hashes["venues"] == model.sha256_hex(F.shipped_bytes("venues"))
        assert _calendar_now(NOW) == ("none", "")


def test_calendar_in_force_is_the_sha_of_the_intact_signed_copy():
    """Q19, O6: under an OK owner state the latest calendar approval stamped by `now` is in force while its stored
    copy is intact. The stored folder is the set itself; one changed or missing file there makes it
    ("store", sha), so None."""
    stream = _fixture_calendar()
    sha = model.sha256_hex(stream)
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, calendar_raw=stream)
        assert _calendar_now(NOW) == ("ok", sha) and owner.calendar_in_force(NOW) == sha
        assert _calendar_now(_dt.datetime(2026, 10, 24, 0, 0, tzinfo=_dt.timezone.utc)) == ("ok", sha)   # NOW in UTC
        stored = owner.store_dir() / "calendar" / sha
        assert rules.calendar_sha256(stored) == sha and rules.calendar_stream(stored) == stream
        first = sorted(stored.iterdir())[0]
        first.write_bytes(first.read_bytes() + b"# altered\n")
        assert _calendar_now(NOW) == ("store", sha) and owner.calendar_in_force(NOW) is None
        first.unlink()
        assert _calendar_now(NOW) == ("store", sha)


def test_calendar_in_force_is_none_without_an_ok_owner_log():
    """Q19: no owner key, a read error (OSError, ValueError or RuntimeError), a changed key or a broken log give
    ("log", ""), so None, even with a calendar approval in the log. Any other internal error propagates out of
    _calendar_approval, so --check exits 4 (spec 5.4, T4-R1-1), while calendar_in_force fails closed to None."""
    stream = _fixture_calendar()
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        assert _calendar_now(NOW) == ("log", "")                     # before owner act 1 there is no key at all
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        _full_home(home, calendar_raw=stream)
        assert _calendar_now(NOW) == ("ok", model.sha256_hex(stream))

        def boom(*args):
            raise RuntimeError("a refused link")

        def bug(*args):
            raise TypeError("a bug")

        saved, owner._owner_now = owner._owner_now, boom
        try:
            assert _calendar_now(NOW) == ("log", "")                 # _calendar_approval: a read error is "log"
        finally:
            owner._owner_now = saved
        saved, owner.store_get = owner.store_get, bug
        try:
            _raises(lambda: owner._calendar_approval(NOW), TypeError)   # _calendar_approval: any other error raises
            assert owner.calendar_in_force(NOW) is None                 # calendar_in_force: it fails closed
        finally:
            owner.store_get = saved
        assert _calendar_now(NOW)[0] == "ok"
        row = {"utc": "2026-10-20T00:00:00Z", "channel": "toast", "result": "ok", "code": 3, "due": [],
               "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": "SHA256:" + "e" * 64}
        owner.alerts_path().write_bytes(model.canonical_json(row).encode("utf-8") + b"\n")
        assert owner.load_context(NOW, HELD).owner.reason == "KEY CHANGED since 2026-10-20"
        assert _calendar_now(NOW) == ("log", "")
        owner.alerts_path().unlink()
        assert _calendar_now(NOW)[0] == "ok"
        with open(owner.log_path(), "ab") as fh:
            fh.write(b'{"seq": 99}\n')
        assert not owner.load_context(NOW, HELD).owner.ok and _calendar_now(NOW) == ("log", "")


def test_calendar_in_force_counts_only_approvals_stamped_by_now():
    """Q19: with no calendar approval it is ("none", ""); one stamped after `now` counts only from its stamp on
    (load_context's cut-off, _up_to); the latest approval in log order among those stamped by `now` wins."""
    stream = _fixture_calendar()
    sha = model.sha256_hex(stream)
    other = b"holidays_KRX.yaml\0x: 1\n\0"                              # a one-file calendar set
    after = _dt.datetime(2026, 10, 25, 9, 0, tzinfo=model.KST)          # 2026-10-25T00:00:00Z
    with F.temp_home() as home, _pubkey_at(home / "owner_pubkey.pem"):
        key = _full_home(home)
        assert _calendar_now(NOW) == ("none", "") and _calendar_now(after) == ("none", "")
        F.store_blob(home, "calendar", stream,
                     _sign(key, "approved", {"kind": "calendar", "sha256": sha}, "2026-10-25T00:00:00Z"))
        assert _calendar_now(NOW) == ("none", "") and _calendar_now(after) == ("ok", sha)
        newer = _approve(home, key, "calendar", other)                  # later in the log, stamped 2026-10-23
        assert _calendar_now(NOW) == ("ok", newer) and _calendar_now(after) == ("ok", newer)
        assert newer == model.sha256_hex(other) != sha


def test_calendar_in_force_refuses_a_naive_or_out_of_range_now():
    """Q19: a naive `now`, a non-datetime, or one that cannot be converted to UTC or Asia/Seoul is ValueError from
    calendar_in_force and _calendar_approval alike (load_context's checks); nothing else raises."""
    with F.temp_home() as home, _pubkey_at(home / "absent.pem"):
        for now in (_dt.datetime(2026, 10, 24, 9, 0), "2026-10-24", _dt.date(2026, 10, 24), None,
                    _dt.datetime(1, 1, 1, tzinfo=model.KST),
                    _dt.datetime(9999, 12, 31, 23, 59, tzinfo=_dt.timezone.utc)):
            _raises(lambda: owner.calendar_in_force(now), ValueError)
            _raises(lambda: owner._calendar_approval(now), ValueError)
        assert owner.calendar_in_force(NOW) is None


def test_calendar_line_maps_the_shared_calendar_approval():
    """Q19: rules._calendar_line (the --check line) reads owner._calendar_approval at the check's moment and maps its
    four outcomes onto its four lines; under an owner state that is not OK it reads nothing."""
    draft = rules.calendar_sha256(ROOT / "core" / "calendars" / "data")
    other, seen = "a" * 64, []
    cases = ((("log", ""), "calendar: not checked (owner log not usable)"),
             (("none", ""), "calendar: no signed approval, so KRX and US plans are refused (crypto plans only)"),
             (("store", other), f"calendar: the signed version {other[:16]} is missing or altered in the store"),
             (("ok", draft), f"calendar: the draft is the version in force ({draft[:16]})"),
             (("ok", other), f"calendar: the draft {draft[:16]} is not the version in force ({other[:16]}); it counts "
                             "only once signed"))
    saved = owner._calendar_approval
    try:
        for result, line in cases:
            owner._calendar_approval = lambda now, result=result: seen.append(now) or result
            assert rules._calendar_line(F.ctx(), ROOT, NOW) == line, result
        broken = F.ctx(owner=model.OwnerState.broken("bad signature on entry 4"))
        assert rules._calendar_line(broken, ROOT, NOW) == "calendar: not checked (owner log not usable)"
    finally:
        owner._calendar_approval = saved
    assert seen == [NOW] * len(cases), seen
