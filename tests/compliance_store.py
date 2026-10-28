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
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("rules", "instruments", "venues")


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
    """A0: a store folder that is a junction is refused before anything is written through it."""
    import _winapi
    with F.temp_home() as home:
        elsewhere = home / "elsewhere"                   # outside compliance/: only the refusal stops the write
        elsewhere.mkdir()
        owner.store_dir().mkdir(parents=True)
        _winapi.CreateJunction(str(elsewhere), str(owner.store_dir() / "rules"))
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
    import _winapi
    data_dir = ROOT / "core" / "calendars" / "data"
    with F.temp_home() as home:
        sha = F.store_blob(home, "calendar", rules.calendar_stream(data_dir), (2, "c" * 64))
        stored = owner.store_dir() / "calendar" / sha
        assert owner.store_get("calendar", sha) == rules.calendar_stream(data_dir)
        elsewhere = home / "elsewhere"
        elsewhere.mkdir()
        _winapi.CreateJunction(str(elsewhere), str(stored / "linked"))
        assert owner.store_get("calendar", sha) is None, "a stored calendar set holding a link was served"
        assert "is a link" in str(_raises(lambda: rules.calendar_stream(stored), rules.Invalid))
        assert rules.calendar_sha256(data_dir) == sha, "the real set still hashes to its stream"


def test_code_files_is_the_import_closure():
    """P6 on the real tree: core/__init__.py, core/isolation.py, core/compliance/*.py, core/odds/*.py and the RECORD
    files of PyYAML and cryptography; never config.py or data/ (the import allowlist keeps the closure small)."""
    files = owner.code_files(ROOT)
    names = [name for name, _ in files]
    assert names == sorted(set(names)), "not sorted, or a repeat"
    repo = {name for name in names if not name.startswith("venv:")}
    expected = {"core/__init__.py", "core/isolation.py"} | {
        f"core/{sub}/{p.name}" for sub in ("compliance", "odds") for p in (ROOT / "core" / sub).glob("*.py")}
    assert repo == expected, sorted(repo ^ expected)
    assert "config.py" not in repo and not any(name.startswith("data/") for name in repo)
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
    guard whose name the module rebinds or never imports plainly (typing rebound, `import os as typing`, no `import
    typing`, `__name__` assigned or a parameter), or that the module can change without a binding (an attribute store,
    setattr, globals(), sys.modules, a frame's f_globals or f_locals), is scanned too (R4)."""
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
        "core/neq.py": "", "core/local_tc.py": "", "core/rebound.py": "", "core/negated.py": "",
        "core/rev_cli.py": "",
        "core/rebound_typing.py": "", "core/rebound_main.py": "", "core/alias_typing.py": "",
        "core/unbound_typing.py": "", "core/param_main.py": "", "core/stored_typing.py": "",
        "core/setattr_typing.py": "", "core/globals_main.py": "", "core/modules_typing.py": "",
        "core/stored_bare.py": "", "core/frame_main.py": "", "core/frame_bare.py": "",
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
                    "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py",
                    "core/unbound_typing.py", "core/param_main.py", "core/stored_typing.py",
                    "core/setattr_typing.py", "core/globals_main.py", "core/modules_typing.py",
                    "core/stored_bare.py", "core/frame_main.py", "core/frame_bare.py",
                    "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, sorted(repo)
    trusted = "import typing\nfrom typing import TYPE_CHECKING\n"
    assert owner._guards(ast.parse(trusted)) == (True, True, True)
    for route in ("delattr(typing, 'x')", "vars(typing)", "locals()", "typing.__dict__", "import builtins\nbuiltins",
                  "__builtins__", "typing.__name__ = 'x'", "del typing.TYPE_CHECKING"):
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
NOW = _dt.datetime(2026, 10, 24, 9, 0, tzinfo=model.KST)
HELD = model.Positions(equity_krw=1_000_000.0, holdings={("upbit", "BTC"): 0.01})


@contextlib.contextmanager
def _pubkey_at(path: Path):
    """owner.PUBKEY_PATH pointed at `path` for the block, restored afterwards."""
    saved = owner.PUBKEY_PATH
    owner.PUBKEY_PATH = path
    try:
        yield path
    finally:
        owner.PUBKEY_PATH = saved


def _owner_key(home: Path):
    """The test key, its pem written to owner.PUBKEY_PATH, which must lie inside the temp home `home`: the repo's
    trust anchor is never written. NotRun PENDING without cryptography."""
    if not owner.PUBKEY_PATH.is_relative_to(home):
        raise AssertionError(f"{owner.PUBKEY_PATH} is outside the temp home {home}")
    key = F.test_key()
    F.write_pubkey(owner.PUBKEY_PATH, key)
    return key


def _sign(key, kind: str, data: dict, utc: str = "2026-10-23T00:00:00Z") -> tuple[int, str]:
    """Appends one signed owner entry to the temp home's log; returns its anchor (seq, row_sha256)."""
    path = owner.log_path()
    lines = path.read_bytes().splitlines() if path.is_file() else []
    prev = json.loads(lines[-1])["row_sha256"] if lines else owner.GENESIS_PREV
    line = F.signed_entry(key, len(lines) + 1, prev, kind, data, utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:
        fh.write(line)
    return len(lines) + 1, json.loads(line)["row_sha256"]


def _approve(home: Path, key, kind: str, raw: bytes) -> str:
    """Signs `approved {kind, sha256}` for `raw` and stores the bytes with that entry as their anchor."""
    return F.store_blob(home, kind, raw, _sign(key, "approved", {"kind": kind, "sha256": model.sha256_hex(raw)}))


def _other_code(key, utc: str = "2026-10-23T00:00:00Z") -> None:
    """Signs a code_approved that names a hash other than the code on disk."""
    files = sorted([list(f) for f in owner.code_files(owner.REPO_ROOT)] + [["core/compliance/zz.py", "0" * 64]])
    _sign(key, "code_approved", {"sha256": model.sha256_hex(model.canonical_json(files)), "files": files}, utc)


def _full_home(home: Path, *, rules_raw: bytes | None = None):
    """The test key at owner.PUBKEY_PATH, the three shipped drafts (or `rules_raw`) approved and stored, the current
    code hash signed and the owner's age recorded. Returns the key. NotRun PENDING without cryptography."""
    key = _owner_key(home)
    for kind in TABLES:
        _approve(home, key, kind, rules_raw if kind == "rules" and rules_raw is not None else F.shipped_bytes(kind))
    files = [list(f) for f in owner.code_files(owner.REPO_ROOT)]
    _sign(key, "code_approved", {"sha256": owner.code_hash(owner.REPO_ROOT), "files": files})
    _sign(key, "age_of_majority", {"birth_date": "2000-01-01", "evidence": "test fixture"})
    return key


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
    import _winapi
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
        _winapi.CreateJunction(str(home / "elsewhere"), str(owner.home() / "linked"))
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
