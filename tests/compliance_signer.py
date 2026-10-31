"""The owner-kept signer tools/signer/sign.py (compliance plan Task 15; spec 6.4 "Signing", "The key file", 8.9;
P20, P27). The signer may not import the repo, so these tests load it by path and hold its copies (line format,
event schemas, log structure, store layout, code hash, QUANTGEN refusal) against owner.py, rules.py and model.py.
Its interactive path (typed code, passphrase) never runs here: the refusals are asserted, and the steps behind
them are called directly with the fixed test key in the temp TRADEGEN_HOME, which is the only place they write."""
from __future__ import annotations

import ast
import base64
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from core import isolation
from core.compliance import model, owner, rules
from tests import compliance_fixtures as fx
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
SIGNER_PATH = ROOT / "tools" / "signer" / "sign.py"
UTC = "2026-10-23T00:00:00Z"
PASS = "cat dog owl bee ant"                        # 19 characters, 5 different words of 3 letters: accepted
HUMAN = [0.0, 0.12, 0.25, 0.41, 0.55, 0.70, 0.86, 1.0]
BURST = [0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007]
_SIG64 = base64.b64encode(bytes(64)).decode("ascii")
_FILES = [["core/__init__.py", "b" * 64]]
_VALID = {                                          # one valid data object per owner and system kind
    "approved": {"kind": "rules", "sha256": "a" * 64},
    "code_approved": {"sha256": model.sha256_hex(model.canonical_json(_FILES)), "files": _FILES},
    "course_completed": {"course": "kofia_leveraged_1h", "evidence": "certificate 2026-10-20"},
    "broker_approval": {"item": "broker_eligibility", "evidence": "KIS letter"},
    "age_of_majority": {"birth_date": "2000-01-01", "evidence": "ID checked"},
    "cap_set": {"key": "okx_equity_share", "value": 0.1},
    "limit_set": {"total_loss_floor_krw": 21000.0, "daily_loss_krw": 5000.0},
    "withdrawal_address": {"venue": "upbit", "symbol": "BTC", "network": "bitcoin", "address": "bc1qtest",
                           "tag": None, "evidence": "Upbit deposit page"},
    "session_armed": {"session_id": "S1"},
    "session_ack": {"session_id": "S1", "row_id": "KR-OKX-SPOT", "warning_sha256": "c" * 64},
    "transfer_ack": {"intent_hash": "d" * 64, "warning_sha256": "e" * 64},
    "key_rotated": {"old_pubkey_b64": base64.b64encode(bytes(range(32))).decode("ascii"),
                    "new_pubkey_b64": base64.b64encode(bytes(32)).decode("ascii")},
    "system_halt": {"floor_krw": 21000.0},
    "system_disarm": {"session_id": "S1", "reason": "floor reached"},
}
_EDGES = (0, 1, 0.5, 1.0, -1, -0.0, True, False, 10 ** 400, float("nan"), float("inf"), "", " ", "\t", "x", "S1",
          "a" * 64, "A" * 64, "a" * 63, "2000-01-01", "2000-1-1", "2000-02-30", "２０００-01-01",
          "rules", "calendar", "code", "upbit", "okx_equity_share", "kofia_leveraged_1h", "age_of_majority",
          base64.b64encode(bytes(31)).decode("ascii"), base64.b64encode(bytes(33)).decode("ascii"),
          base64.b64encode(bytes(32)).decode("ascii").rstrip("="), None, [], ["x"], {}, [["core/x.py", "b" * 64]],
          [["b", "c" * 64], ["a", "c" * 64]], "bc1q‮tset")


def _load_signer():
    spec = importlib.util.spec_from_file_location("tradegen_signer_under_test", SIGNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


signer = _load_signer()


def _need_crypto() -> None:
    if importlib.util.find_spec("cryptography") is None:
        raise NotRun("PENDING: cryptography not installed (Task 10)")


@contextlib.contextmanager
def _patched(obj, name, value):
    saved = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield value
    finally:
        setattr(obj, name, saved)


@contextlib.contextmanager
def _env_without_claude():
    saved = {k: v for k, v in os.environ.items()
             if k.upper() == "CLAUDECODE" or k.upper().startswith("CLAUDE_CODE_")}
    for k in saved:
        del os.environ[k]
    try:
        yield
    finally:
        for k in [k for k in os.environ if k.upper() == "CLAUDECODE" or k.upper().startswith("CLAUDE_CODE_")]:
            del os.environ[k]
        os.environ.update(saved)


class _Tty(io.StringIO):
    def isatty(self) -> bool:
        return True


def _never(*_a, **_k):
    raise AssertionError("an interactive prompt was reached")


def _typed(stamps, wrong=False):
    """A stand-in for _read_typed: it answers with the code shown in the prompt (or a wrong one) at `stamps`."""
    def read(prompt):
        code = prompt.split("(do not paste): ")[1].split()[0]
        return ("!" + code[1:] if wrong else code), stamps
    return read


def _home() -> Path:
    return Path(os.environ["TRADEGEN_HOME"])


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _quiet(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = fn(*args)
    return result, out.getvalue(), err.getvalue()


def _raises(fn, exc: type[BaseException]) -> BaseException:
    try:
        fn()
    except exc as caught:
        return caught
    raise AssertionError(f"{exc.__name__} not raised")


def _second_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def _raw(key) -> bytes:
    return key.public_key().public_bytes_raw()


def _b64(key) -> str:
    return base64.b64encode(_raw(key)).decode("ascii")


def _log_lines() -> list[bytes]:
    return owner.log_path().read_bytes().splitlines(keepends=True)


def _line(seq, prev, kind, data, utc=UTC, **extra) -> bytes:
    """One log line built by hand with its row_sha256 recomputed; `extra` adds keys such as a sig."""
    body = {"seq": seq, "prev_sha256": prev, "utc": utc, "kind": kind, "data": data}
    row = model.sha256_hex(model.canonical_json(body))
    return (model.canonical_json({**body, "row_sha256": row, **extra}) + "\n").encode("utf-8")


# --------------------------------------------------------------------------- #
# Standalone, and its copies agree with the repo
# --------------------------------------------------------------------------- #
def test_signer_is_standalone():
    """Standard library plus cryptography only; cryptography only inside functions; nothing that talks to a
    network; never the repo (spec 6.4: "one small file using only the standard library and cryptography")."""
    tree = ast.parse(SIGNER_PATH.read_text(encoding="utf-8"))
    in_function = {id(n) for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                   for n in ast.walk(f)}
    network = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "asyncio", "requests", "xmlrpc"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                top = name.split(".")[0]
                assert top in sys.stdlib_module_names or top == "cryptography", name
                assert top not in network, name
                assert top != "cryptography" or id(node) in in_function, f"module-level {name}"


def test_signer_copies_match_the_repo():
    assert signer.SIG_DOMAIN == owner.SIG_DOMAIN and signer.GENESIS_PREV == owner.GENESIS_PREV
    assert signer.APPROVAL_KINDS == owner.APPROVAL_KINDS
    assert set(signer.SCHEMAS) == set(owner.OWNER_KINDS), set(signer.SCHEMAS) ^ set(owner.OWNER_KINDS)
    assert set(signer.SYSTEM_SCHEMAS) == set(owner.SYSTEM_KINDS) and set(signer._DATA) == set(owner._DATA)
    assert signer.VENUES == rules.VENUES and signer.OWNER_REQUIREMENTS == rules.OWNER_REQUIREMENTS
    assert signer.QUANTGEN_STATE == isolation.QUANTGEN_STATE
    # The standalone signer pins the owner's Windows deployment; isolation follows the checkout.
    deployed = Path.home() / "OneDrive" / "Desktop" / "QUANTGEN"
    assert signer.QUANTGEN_REPO.resolve() == deployed.resolve()
    assert isolation.QUANTGEN_REPO.resolve() == ROOT.with_name("QUANTGEN").resolve()
    if ROOT.resolve() == deployed.with_name("TRADEGEN").resolve():
        assert signer.QUANTGEN_REPO.resolve() == isolation.QUANTGEN_REPO.resolve()
    sample = {"b": [1, 2.5, None, True], "a": {"z": "한국", "y": ""}}
    assert signer.canonical_json(sample) == model.canonical_json(sample)
    assert signer.sha256_hex("x") == model.sha256_hex("x")
    assert signer.fingerprint(b"\1" * 32) == owner.fingerprint(b"\1" * 32)
    assert signer._UTC.pattern == owner._UTC.pattern and signer._ISO_DATE.pattern == owner._ISO_DATE.pattern


# --------------------------------------------------------------------------- #
# Refusals (spec 6.4 "Where it runs"; spec 8.9)
# --------------------------------------------------------------------------- #
def test_main_refuses_under_claude_env_and_writes_nothing():
    with _env_without_claude(), _patched(signer.getpass, "getpass", _never), \
            _patched(signer, "_read_typed", _never):
        for name in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"):
            os.environ[name] = "1"
            try:
                for argv in (["keygen"], ["fingerprint"], ["approve", "--kind", "rules", "--path", "x"]):
                    code, _, err = _quiet(signer.main, argv)
                    assert code == 2 and f"{name} is set" in err, (argv, code, err)
            finally:
                del os.environ[name]
    assert list(_home().iterdir()) == [], list(_home().iterdir())


def test_main_refuses_claude_parent_and_non_tty_stdin():
    with _env_without_claude(), _patched(signer.getpass, "getpass", _never), \
            _patched(signer, "_read_typed", _never):
        with _patched(signer, "_claude_ancestor", lambda: True), _patched(sys, "stdin", _Tty()):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "claude.exe" in err and "has exited" in err, (code, err)
        with _patched(signer, "_claude_ancestor", lambda: False), _patched(sys, "stdin", io.StringIO("")):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "stdin is not a terminal" in err, (code, err)
        with _patched(signer, "_claude_ancestor", lambda: False), _patched(sys, "stdin", None):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "stdin is not a terminal" in err, (code, err)
    assert list(_home().iterdir()) == [], list(_home().iterdir())


def test_main_refuses_without_isolated_mode():
    """Without -I, Python puts sign.py's folder first on sys.path, so a getpass.py placed next to it would run
    inside the passphrase prompt (owner act 1 types python.exe -I)."""
    assert signer._isolated() == bool(sys.flags.isolated)
    with _env_without_claude(), _patched(signer.getpass, "getpass", _never), \
            _patched(signer, "_read_typed", _never), _patched(signer, "_claude_ancestor", lambda: False), \
            _patched(signer, "_stdin_is_terminal", lambda: True), _patched(signer, "_isolated", lambda: False):
        code, _, err = _quiet(signer.main, ["keygen"])
    assert code == 2 and "python.exe -I" in err, (code, err)
    assert list(_home().iterdir()) == [], list(_home().iterdir())


def test_a_null_device_is_not_a_terminal():
    """On Windows isatty() is true for any character device, NUL included (`cmd /c "... < NUL"`), so stdin counts
    as a terminal only when GetConsoleMode accepts its handle."""
    with open(os.devnull) as nul, _env_without_claude(), _patched(signer.getpass, "getpass", _never), \
            _patched(signer, "_read_typed", _never), _patched(signer, "_claude_ancestor", lambda: False), \
            _patched(sys, "stdin", nul):
        assert signer._stdin_is_terminal() is False
        code, _, err = _quiet(signer.main, ["keygen"])
    assert code == 2 and "stdin is not a terminal" in err, (code, err)
    assert list(_home().iterdir()) == [], list(_home().iterdir())


def test_stdin_terminal_check_follows_getconsolemode():
    """The Windows branch asks kernel32.GetConsoleMode about stdin's handle; a refusal, an exception or a missing
    stdin all mean "not a terminal". (A fake kernel32 stands in: no console is attached under the suite.)"""
    if os.name != "nt":
        raise NotRun("REFDATA: GetConsoleMode needs Windows")
    import ctypes
    asked = []

    def fake_dll(answer):
        def win_dll(name, use_last_error=False):
            def get_console_mode(handle, mode):
                asked.append((name, handle))
                if isinstance(answer, Exception):
                    raise answer
                return answer
            return type("K32", (), {"GetConsoleMode": staticmethod(get_console_mode)})()
        return win_dll

    with open(os.devnull) as nul, _patched(sys, "stdin", nul):
        for answer, expected in ((1, True), (0, False), (OSError("boom"), False)):
            with _patched(ctypes, "WinDLL", fake_dll(answer)):
                assert signer._stdin_is_terminal() is expected, answer
        assert [name for name, _ in asked] == ["kernel32"] * 3 and all(isinstance(h, int) for _, h in asked), asked
    with _patched(sys, "stdin", None), _patched(ctypes, "WinDLL", fake_dll(1)):
        assert signer._stdin_is_terminal() is False


def test_claude_ancestor_walk():
    """R5, R11: a claude.exe anywhere in the chain refuses, even above a session process, and so does a walk that
    breaks (an exited parent, a pid-reuse cycle, more than 256 steps) before it has passed a session process."""
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    terminal = {20: (21, "python.exe"), 21: (22, "powershell.exe"), 22: (23, "WindowsTerminal.exe"),
                23: (24, "svchost.exe"), 24: (25, "services.exe"), 25: (99, "wininit.exe")}      # 99 has exited
    assert signer._has_claude_ancestor(20, terminal) is False, "the owner's Windows Terminal chain (R11)"
    shell = {50: (51, "python.exe"), 51: (52, "cmd.exe"), 52: (53, "Explorer.EXE")}             # 53 has exited
    assert signer._has_claude_ancestor(50, shell) is False, "a console started from explorer.exe, any case (R11)"
    renamed = {1: (2, "python.exe"), 2: (3, "winlogon.exe"), 3: (4, "bash.exe"), 4: (5, "claude.exe"),
               5: (0, "explorer.exe")}                       # cmd.exe saved as winlogon.exe, run under Claude
    assert signer._has_claude_ancestor(1, renamed) is True, "a session process name never ends the walk"
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is True, "a pid-reuse cycle refuses"
    assert signer._has_claude_ancestor(5, {}) is True, "an empty table refuses"
    exited = {30: (31, "python.exe"), 31: (32, "Code.exe")}                                    # 32 has exited
    assert signer._has_claude_ancestor(30, exited) is True, "an editor terminal whose launcher has exited"
    assert signer._has_claude_ancestor(40, {40: (41, "python.exe"), 41: (0, "CLAUDE.EXE")}) is True, "any case"
    deep = {**{n: (n + 1, "python.exe") for n in range(1, 300)}, 300: (0, "wininit.exe")}
    assert signer._has_claude_ancestor(1, deep) is True, "the 256-step cap refuses"
    service = {60: (61, "python.exe"), 61: (62, "svchost.exe")}                                # 62 has exited
    assert signer._has_claude_ancestor(60, service) is True, "svchost.exe is no session process"
    roots = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})
    assert signer._SESSION_ROOTS == roots, "exactly the four session processes: one more makes the walk looser (R11)"
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())


def test_claude_ancestor_check_fails_closed():
    """Claude is ruled out only from a process table that holds this very process and whose parent chain reaches
    pid 0 or passes a Windows session process: a failed snapshot, an empty table, a table without our pid or a
    parent that has exited all read as "cannot rule it out" (R5)."""
    me = os.getpid()

    def broken():
        raise OSError("Process32FirstW failed")

    for table in (lambda: {}, lambda: {me + 1: (0, "python.exe")}, broken,
                  lambda: (_ for _ in ()).throw(TypeError("ctypes")), lambda: (_ for _ in ()).throw(ImportError("x"))):
        with _patched(signer, "_process_table", table):
            assert signer._claude_ancestor() is True, table
    with _patched(signer, "_process_table", lambda: {me: (0, "python.exe")}):
        assert signer._claude_ancestor() is False
    with _patched(signer, "_process_table", lambda: {me: (me + 1, "python.exe")}):
        assert signer._claude_ancestor() is True, "a parent that has exited refuses (R5)"
    with _patched(signer, "_process_table", lambda: {me: (7, "python.exe"), 7: (0, "Claude.exe")}):
        assert signer._claude_ancestor() is True


# --------------------------------------------------------------------------- #
# Key file, passphrase, typed code
# --------------------------------------------------------------------------- #
def test_key_file_round_trip_with_spec_parameters():
    _need_crypto()
    seed = bytes(range(32))
    raw = signer.seal_key(seed, PASS)
    header_line, body, end = raw.split(b"\n")
    assert end == b"" and header_line == signer.canonical_json(json.loads(header_line)).encode("utf-8")
    header = json.loads(header_line)
    assert set(header) == {"format", "kdf", "nonce_b64", "fingerprint"}, header
    assert header["format"] == "tradegen-owner-key/1"
    kdf = header["kdf"]
    assert (kdf["name"], kdf["n"], kdf["r"], kdf["p"]) == ("scrypt", 2 ** 17, 8, 1), kdf
    assert len(base64.b64decode(kdf["salt_b64"])) == 16 and len(base64.b64decode(header["nonce_b64"])) == 12
    assert header["fingerprint"] == owner.fingerprint(_raw(fx.test_key())), header
    assert len(base64.b64decode(body)) == 32 + 16                                # seed + GCM tag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM              # the spec's format, rebuilt here
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    aes_key = Scrypt(salt=base64.b64decode(kdf["salt_b64"]), length=32, n=2 ** 17, r=8, p=1).derive(PASS.encode())
    assert AESGCM(aes_key).decrypt(base64.b64decode(header["nonce_b64"]), base64.b64decode(body), header_line) == seed
    assert signer.open_key(raw, PASS) == seed
    try:
        signer.open_key(raw, PASS + " x")
    except ValueError:
        pass
    else:
        raise AssertionError("a wrong passphrase opened the key file")


def test_key_file_tampering_fails():
    _need_crypto()
    raw = signer.seal_key(bytes(range(32)), PASS)
    header_line, body, _ = raw.split(b"\n")
    header = json.loads(header_line)
    other = signer.canonical_json({**header, "fingerprint": "SHA256:" + "0" * 64}).encode("utf-8")
    sealed = bytearray(base64.b64decode(body))
    sealed[0] ^= 1
    slow = signer.canonical_json({**header, "kdf": {**header["kdf"], "n": 2 ** 14}}).encode("utf-8")
    no_fp = signer.canonical_json({k: v for k, v in header.items() if k != "fingerprint"}).encode("utf-8")
    with _patched(signer, "fingerprint", lambda pub: "SHA256:" + "0" * 64):
        lying = signer.seal_key(bytes(range(32)), PASS)                     # sealed under a false fingerprint
    for bad in (other + b"\n" + body + b"\n",                                  # header is the AAD
                header_line + b"\n" + base64.b64encode(bytes(sealed)) + b"\n",
                slow + b"\n" + body + b"\n",                                   # weaker KDF refused outright
                no_fp + b"\n" + body + b"\n",                                  # a header key missing
                raw.rstrip(b"\n"), lying):
        try:
            signer.open_key(bad, PASS)
        except ValueError:
            pass
        else:
            raise AssertionError(f"tampered key file accepted: {bad[:60]!r}")
    path = _home() / "no_fingerprint.enc"
    path.write_bytes(no_fp + b"\n" + body + b"\n")
    args = signer._parser().parse_args(["fingerprint", "--key", str(path)])
    try:
        _quiet(args.run, args)
    except ValueError:
        pass                                                                   # main() reports it; no KeyError
    else:
        raise AssertionError("fingerprint printed a header without its fingerprint key")


def test_passphrase_rule():
    assert not signer.passphrase_ok("a" * 19)
    assert signer.passphrase_ok("a" * 20)
    assert signer.passphrase_ok(PASS) and len(PASS) == 19
    assert not signer.passphrase_ok("cat dog owl bee")                          # 4 words, 15 characters
    assert not signer.passphrase_ok("a b c d e f")                              # words too short
    assert not signer.passphrase_ok(" " * 20) and not signer.passphrase_ok(" " * 19 + "a")      # blanks
    assert not signer.passphrase_ok("aaa aaa aaa aaa aaa")                      # one word five times
    assert not signer.passphrase_ok("123 456 789 012 345")                      # digits are not letters
    assert not signer.passphrase_ok("cat dog owl bee an1")                      # every word must be letters
    assert not signer.passphrase_ok("a" + " " * 18 + "b")                        # blanks inside do not count either
    assert not signer.passphrase_ok("Cat cat CAT cAt caT")                      # one word in five spellings
    assert not signer.passphrase_ok("a b c d e f g h i j k l m n o p q r s")     # 19 characters, 18 blanks
    assert signer.passphrase_ok("a b c d e f g h i j k l m n o p q r s t")       # 20 characters, blanks aside
    assert signer.passphrase_ok("Cat dog OWL bee ANT") and signer.passphrase_ok("one two six ten Ten four")
    assert signer.passphrase_ok("x" * 10 + " " * 5 + "y" * 10)


def test_typed_code_rejects_a_burst():
    rollover = [0.0, 0.12, 0.125, 0.13, 0.30, 0.45, 0.60, 0.75]                 # two keys pressed together: typed
    partial = [0.0, 2.0, 2.001, 2.002, 2.003, 2.004, 2.005, 2.006]               # one key, a pause, then a paste
    assert signer._typed_ok("k7m2p9qa", "k7m2p9qa", HUMAN)
    assert signer._typed_ok("k7m2p9qa", "k7m2p9qa", rollover)
    assert not signer._typed_ok("k7m2p9qa", "k7m2p9qa", BURST)                  # a paste
    assert not signer._typed_ok("k7m2p9qa", "k7m2p9qa", partial)                # averages 287 ms, still a burst
    assert not signer._typed_ok("k7m2p9qa", "k7m2p9qb", HUMAN)
    assert not signer._typed_ok("k7m2p9qa", "k7m2p9qa", [0.0])
    cap = _VALID["cap_set"]
    with _patched(signer, "_read_typed", _typed(HUMAN)):
        _, out, _ = _quiet(signer._confirm, "cap_set", cap, (0, ""), UTC)
    assert f"stamped {UTC}" in out, out
    for stamps, wrong in ((BURST, False), (partial, False), (HUMAN, True)):
        with _patched(signer, "_read_typed", _typed(stamps, wrong)):
            try:
                _quiet(signer._confirm, "cap_set", cap, (0, ""), UTC)
            except ValueError:
                pass
            else:
                raise AssertionError(f"a pasted or wrong code was accepted ({stamps}, wrong={wrong})")
    data = {**_VALID["withdrawal_address"], "evidence": "Upbit ‮ page"}
    with _patched(signer, "_read_typed", _typed(HUMAN)):
        _, out, _ = _quiet(signer._confirm, "withdrawal_address", data, (0, ""), UTC)
    assert "\\u202e" in out and "‮" not in out, out                     # shown as an escape, never rendered


def test_wrong_code_signs_nothing():
    """Spec 8.9 "needs the typed code": a pasted or a wrong code stops the command before the passphrase prompt;
    nothing reaches the store or the log."""
    draft = ROOT / "core" / "compliance" / "kr_rules.yaml"
    parser = signer._parser()
    for reader in (_typed(BURST), _typed(HUMAN, wrong=True)):
        for argv in (["approve", "--kind", "rules", "--path", str(draft)],
                     ["event", "cap_set", "--data", '{"key": "okx_equity_share", "value": 0.1}']):
            args = parser.parse_args(argv)
            with _patched(signer, "_read_typed", reader), _patched(signer, "_unlock", _never), \
                    _patched(signer.getpass, "getpass", _never):
                try:
                    _quiet(args.run, args)
                except ValueError as exc:
                    assert "nothing was signed" in str(exc), exc
                else:
                    raise AssertionError(f"{argv} went past a pasted or wrong code")
    assert not owner.log_path().exists() and not owner.store_dir().exists()
    assert list(_home().iterdir()) == [], list(_home().iterdir())


# --------------------------------------------------------------------------- #
# Log lines and event data agree with owner.py
# --------------------------------------------------------------------------- #
def test_entry_line_matches_the_fixture_and_verifies():
    _need_crypto()
    key = fx.test_key()
    data = {"key": "okx_equity_share", "value": 0.1}
    line, row = signer.entry_line(key, 1, owner.GENESIS_PREV, "cap_set", data, UTC)
    assert line == fx.signed_entry(key, 1, owner.GENESIS_PREV, "cap_set", data, utc=UTC)   # byte for byte
    assert json.loads(line)["row_sha256"] == row
    check = owner.verify_log([line], _raw(key), [])
    assert check.ok and check.head == (1, row), check.reason


def test_signer_and_system_entries_share_one_chain():
    _need_crypto()
    key = fx.test_key()
    s1 = signer._commit(key, "cap_set", {"key": "okx_equity_share", "value": 0.1}, utc=UTC)
    s2 = owner.append_system_entry("system_halt", {"floor_krw": 21000.0},
                                   datetime(2026, 10, 23, 1, tzinfo=timezone.utc))
    s3 = signer._commit(key, "session_armed", {"session_id": "S1"}, utc="2026-10-23T02:00:00Z")
    assert [s1[0], s2[0], s3[0]] == [1, 2, 3], (s1, s2, s3)
    check = owner.verify_log(_log_lines(), _raw(key), owner.read_anchors())
    assert check.ok and check.head == s3, check.reason
    before = owner.log_path().read_bytes()
    for kw, error in (({"utc": "2026-10-23T03:00:00Z", "expect_head": s2}, RuntimeError),   # not the head shown
                      ({"utc": "2026-10-23T01:59:59Z"}, RuntimeError),         # earlier than the head's stamp
                      ({"utc": "2026-10-23 03:00:00"}, ValueError),            # not the owner.py utc format
                      ({"utc": "２０２６-10-23T03:00:00Z"}, ValueError)):   # fullwidth digits
        try:
            signer._commit(key, "session_armed", {"session_id": "S2"}, **kw)
        except error:
            pass
        else:
            raise AssertionError(f"signed with {kw}")
    assert owner.log_path().read_bytes() == before
    lines = before.splitlines(keepends=True)
    owner.log_path().write_bytes(lines[0].replace(b"0.1", b"0.2") + b"".join(lines[1:]))
    try:
        signer._commit(key, "session_armed", {"session_id": "S2"}, utc="2026-10-23T03:00:00Z")
    except ValueError:
        pass
    else:
        raise AssertionError("extended a broken log")
    assert owner.log_path().read_bytes() == lines[0].replace(b"0.1", b"0.2") + b"".join(lines[1:])


def test_head_refuses_a_log_the_gate_calls_broken():
    """_head copies owner._structure (signatures aside): a log owner.py can extend, it extends; a log owner.py
    calls BROKEN is refused before anything is shown or signed."""
    g, halt = owner.GENESIS_PREV, {"floor_krw": 1.0}
    first = _line(1, g, "cap_set", _VALID["cap_set"], sig=_SIG64)
    second = _line(2, json.loads(first)["row_sha256"], "system_halt", halt)
    assert owner._structure([first, second])[1] == ""
    assert signer._head([first, second]) == (2, json.loads(second)["row_sha256"])
    assert signer._head([]) == (0, "")
    plain = _line(1, g, "system_halt", halt)
    broken = {
        "unsigned owner entry": [_line(1, g, "cap_set", _VALID["cap_set"])],
        "signed system entry": [_line(1, g, "system_halt", halt, sig=_SIG64)],
        "unknown kind": [_line(1, g, "nonsense", {}, sig=_SIG64)],
        "extra line key": [_line(1, g, "system_halt", halt, note="x")],
        "seq true": [_line(True, g, "system_halt", halt)],
        "utc format": [_line(1, g, "system_halt", halt, utc="2026-10-23 00:00:00")],
        "utc fullwidth digits": [_line(1, g, "system_halt", halt, utc="２０２６-10-23T00:00:00Z")],
        "bad data": [_line(1, g, "system_halt", {"floor_krw": -1.0})],
        "short sig": [_line(1, g, "cap_set", _VALID["cap_set"], sig="AAAA")],
        "CR line end": [plain[:-1] + b"\r\n"],
        "torn last line": [first, second[:-1]],
        "broken prev link": [first, _line(2, g, "system_halt", halt)],
        "duplicate key": [plain.replace(b'"kind":"system_halt"', b'"kind":"system_halt","kind":"system_halt"')],
        "nested past the recursion limit": [b"[" * 100_000 + b"]" * 100_000 + b"\n"],
    }
    for why, lines in broken.items():
        assert owner._structure(lines)[1] != "", why
        try:
            signer._head(lines)
        except ValueError:
            pass
        else:
            raise AssertionError(f"_head accepted a log owner.py calls BROKEN: {why}")
    path = owner.log_path()
    path.parent.mkdir(parents=True)
    path.write_bytes(b"".join(broken["unsigned owner entry"]))
    before = path.read_bytes()
    try:
        signer._commit(None, "session_armed", {"session_id": "S1"}, utc=UTC)       # refused before any key is used
    except ValueError:
        pass
    else:
        raise AssertionError("signed on top of a log owner.py calls BROKEN")
    assert path.read_bytes() == before


def _samples(key1, key2) -> list[tuple[str, dict]]:
    rotated = {"old_pubkey_b64": _b64(key1), "new_pubkey_b64": _b64(key2)}
    return [(kind, rotated if kind == "key_rotated" else _VALID[kind]) for kind in sorted(owner.OWNER_KINDS)]


def test_every_event_the_signer_accepts_verifies():
    """Signing an entry owner.py rejects would break the log for good, so each accepted kind must verify; the
    entries after key_rotated are signed by the new key."""
    _need_crypto()
    key1, key2 = fx.test_key(), _second_key()
    lines, prev, current = [], owner.GENESIS_PREV, key1
    for seq, (kind, data) in enumerate(_samples(key1, key2), start=1):
        signer.check_data(kind, data)
        line, prev = signer.entry_line(current, seq, prev, kind, data, UTC)
        lines.append(line)
        if kind == "key_rotated":
            current = key2
    assert {k for k, _ in _samples(key1, key2)} == set(owner.OWNER_KINDS)
    check = owner.verify_log(lines, _raw(key2), [])                             # the pem holds the newest key
    assert check.ok, check.reason
    assert check.first_key_fingerprint == owner.fingerprint(_raw(key1))         # P20


def test_check_data_is_never_looser_than_owner():
    """The copy of owner._data_problem agrees with it both ways on every field of every kind against each edge
    value (types, huge ints, NaN, blanks, non-ASCII digits, base64 lengths, lists, None), and check_data never
    accepts what owner.py rejects."""
    assert set(_VALID) == set(owner._DATA)
    cases = []
    for kind, good in _VALID.items():
        cases.append((kind, good))
        cases += [(kind, {**good, field: edge}) for field in good for edge in _EDGES]
        cases += [(kind, {k: v for k, v in good.items() if k != field}) for field in good]
        cases += [(kind, {**good, "extra": 1}), (kind, None), (kind, [good])]
    for kind, data in cases:
        mine, theirs = signer._data_problem(kind, data), owner._data_problem(kind, data)
        assert (mine == "") == (theirs == ""), (kind, data, mine, theirs)
        if kind in signer.SCHEMAS:
            try:
                signer.check_data(kind, data)
            except ValueError:
                continue
            assert theirs == "", (kind, data, theirs)


def test_check_data_refuses_bad_events():
    """Each case is refused by the signer, and by owner._data_problem too unless the case names its signer-only
    rule."""
    good, wa = _VALID["cap_set"], _VALID["withdrawal_address"]
    for kind, data, signer_only in (
            ("cap_set", {**good, "extra": 1}, ""), ("cap_set", {"key": "okx_equity_share"}, ""),
            ("cap_set", {**good, "value": 1.5}, ""), ("cap_set", {**good, "value": 0}, ""),
            ("cap_set", {**good, "value": True}, ""), ("cap_set", {**good, "value": 10 ** 400}, ""),
            ("cap_set", {**good, "key": "other"}, ""),
            ("course_completed", {"course": "unknown", "evidence": "x"}, ""),
            ("course_completed", {"course": "age_of_majority", "evidence": "x"}, ""),
            ("age_of_majority", {"birth_date": "2000-13-01", "evidence": "x"}, ""),
            ("limit_set", {"total_loss_floor_krw": 0.0, "daily_loss_krw": 0.0}, ""),
            ("withdrawal_address", {**wa, "venue": "nowhere"}, ""),
            ("withdrawal_address", {**wa, "tag": ""}, ""),
            ("withdrawal_address", {**wa, "address": "bc1q‮tset"}, "printable ASCII"),   # a bidi override
            ("withdrawal_address", {**wa, "network": "bit coin"}, "printable ASCII"),
            ("withdrawal_address", {**wa, "tag": "１２"}, "printable ASCII"),
            ("approved", {"kind": "code", "sha256": "a" * 64}, ""),
            ("approved", {"kind": "rules", "sha256": "A" * 64}, ""),
            ("code_approved", {"sha256": "a" * 64, "files": [["core/x.py", "b" * 64]]}, ""),
            ("key_rotated", {"old_pubkey_b64": "AAAA", "new_pubkey_b64": "AAAA"}, ""),
            ("session_ack", {"session_id": "S1", "row_id": ["x"], "warning_sha256": "c" * 64}, ""),
            ("system_halt", {"floor_krw": 1.0}, "system kinds are never signed"),
            ("nonsense", {}, "unknown kind")):
        try:
            signer.check_data(kind, data)
        except ValueError:
            pass
        else:
            raise AssertionError(f"check_data accepted {kind} {data}")
        if not signer_only:
            assert owner._data_problem(kind, data) != "", (kind, data)
    huge = '{"key": "okx_equity_share", "value": 1' + "0" * 400 + "}"
    args = signer._parser().parse_args(["event", "cap_set", "--data", huge])
    with _patched(signer, "_read_typed", _never), _patched(signer.getpass, "getpass", _never):
        try:
            args.run(args)
        except ValueError:
            pass                                                               # not OverflowError: main() reports it
        else:
            raise AssertionError("a 401-digit cap went to the prompt")


# --------------------------------------------------------------------------- #
# Code hash and store layout agree with owner.py
# --------------------------------------------------------------------------- #
def test_code_files_match_owner():
    mine = signer.code_files(ROOT)
    theirs = [tuple(f) for f in owner.code_files(ROOT)]
    assert mine == theirs, sorted(set(mine) ^ set(theirs))
    assert signer.code_hash(ROOT) == owner.code_hash(ROOT)
    paths = {p for p, _ in mine}
    assert {"core/__init__.py", "core/isolation.py", "core/compliance/__init__.py"} <= paths, paths
    assert {f"core/compliance/{p.name}" for p in (ROOT / "core" / "compliance").glob("*.py")} <= paths, paths
    assert "config.py" not in paths and not any(p.startswith("data/") for p in paths), paths
    assert any(p.startswith("venv:PyYAML-") and p.endswith(".dist-info/RECORD") for p in paths), paths
    sources = {                                       # Task 13's synthetic tree (P6 edge cases)
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
        "core/compliance/g.py": "def main():\n    from core.compliance import g\n    return g\n",   # rules.main's shape
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
    tree = _home() / "code_tree"
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text, encoding="utf-8")
    mine = signer.code_files(tree)
    assert mine == [tuple(f) for f in owner.code_files(tree)], mine
    assert {p for p, _ in mine if not p.startswith("venv:")} == {
        "config.py", "core/__init__.py", "core/compliance/__init__.py", "core/compliance/a.py", "core/kept.py",
        "core/pkg/__init__.py", "core/pkg/lazy.py", "core/pkg/sibling.py", "core/upper.py",
        "core/compliance/b.py", "core/compliance/c.py", "core/compliance/d.py", "core/compliance/e.py",
        "core/compliance/f.py", "core/compliance/g.py",
        "core/compliance/h.py", "core/compliance/i.py", "core/compliance/j.py", "core/compliance/k.py",
        "core/compliance/l.py", "core/compliance/m.py", "core/compliance/n.py", "core/compliance/o.py",
        "core/compliance/p.py", "core/compliance/q.py", "core/compliance/r.py", "core/compliance/s.py",
        "core/compliance/t.py", "core/compliance/u.py", "core/compliance/v.py", "core/compliance/w.py",
        "core/compliance/x.py", "core/compliance/y.py", "core/compliance/z.py",
        "core/rebound_typing.py", "core/rebound_main.py", "core/alias_typing.py", "core/unbound_typing.py",
        "core/param_main.py", "core/stored_typing.py", "core/setattr_typing.py", "core/globals_main.py",
        "core/modules_typing.py", "core/stored_bare.py", "core/frame_main.py", "core/frame_bare.py",
        "core/class_typing.py", "core/fn_globals_main.py", "core/fn_globals_typing.py", "core/fn_globals_bare.py",
        "core/gc_typing.py", "core/builtins_typing.py", "core/gc_objects_typing.py",
        "core/neq.py", "core/local_tc.py", "core/rebound.py", "core/negated.py"}, mine


def test_closure_scan_helpers_are_identical_in_owner_and_signer():
    """R4: the signer's copy of the D14 closure scan is owner.py's, character for character, so a hardening in one
    file cannot be forgotten in the other (test_code_files_match_owner compares outputs on chosen trees only)."""
    import inspect
    for name in ("_binds", "_typing_flag", "_guards", "_skipped", "_import_nodes", "_module_file", "_repo_imports"):
        assert inspect.getsource(getattr(signer, name)) == inspect.getsource(getattr(owner, name)), name


def test_store_layout_matches_owner_store_put():
    store = owner.store_dir()
    raw = fx.shipped_bytes("rules")
    anchor = (3, "f" * 64)
    assert signer.store_file("rules", raw, anchor) == rules.file_sha256(raw)
    mine = _tree(store)
    shutil.rmtree(store)
    assert owner.store_put("rules", raw, anchor) == rules.file_sha256(raw)
    assert _tree(store) == mine, (sorted(_tree(store)), sorted(mine))
    assert signer.store_file("rules", raw, anchor) == rules.file_sha256(raw)    # same bytes again: fine
    assert signer.store_file("rules", raw, (9, "a" * 64)) == rules.file_sha256(raw)
    assert _tree(store) == mine, "the first anchor is kept (P34)"
    target = store / "rules" / f"{rules.file_sha256(raw)}.yaml"
    target.write_bytes(raw + b"#")
    try:
        signer.store_file("rules", raw, anchor)
    except RuntimeError:
        pass
    else:
        raise AssertionError("the store was not write-once")
    for call in (lambda: signer.store_file("calendar", raw, anchor), lambda: signer.store_file("odds", raw, anchor),
                 lambda: signer.store_file("rules", raw, (0, "f" * 64)),
                 lambda: signer.store_file("rules", raw, (True, "f" * 64)),
                 lambda: signer.store_file("rules", raw, (1, "F" * 64))):
        _raises(call, ValueError)
    _raises(lambda: signer.store_file("rules", "text", anchor), TypeError)


def test_store_writes_are_atomic():
    """owner._write_new's rule: the bytes go to a temp file that os.rename moves into place, so a crash mid-write
    (here fsync raising, first in the blob's write, then in the anchor's) leaves no torn file under its final name
    and no temp file, and a re-run with the same anchor completes the store."""
    raw, anchor = fx.shipped_bytes("rules"), (3, "f" * 64)
    sha = rules.file_sha256(raw)
    blob = owner.store_dir() / "rules" / f"{sha}.yaml"
    anchor_path = owner.store_dir() / "rules" / f"{sha}.anchor.json"
    real_fsync = os.fsync
    for crash_at in (1, 2):
        calls = []

        def fsync(fd, crash_at=crash_at, calls=calls):
            calls.append(fd)
            if len(calls) == crash_at:
                raise OSError("simulated crash during fsync")
            real_fsync(fd)

        with _patched(signer.os, "fsync", fsync):
            try:
                signer.store_file("rules", raw, anchor)
            except OSError:
                pass
            else:
                raise AssertionError(f"fsync call {crash_at} raised, yet store_file returned")
        assert blob.exists() == (crash_at == 2) and not anchor_path.exists(), sorted(_tree(_home()))
        assert list(_home().rglob("*.tmp")) == [] and owner.read_anchors() == [], sorted(_tree(_home()))
        assert signer.store_file("rules", raw, anchor) == sha                      # the re-run completes it
        assert blob.read_bytes() == raw and list(_home().rglob("*.tmp")) == []
        assert json.loads(anchor_path.read_bytes()) == {"seq": 3, "row_sha256": "f" * 64}
        shutil.rmtree(owner.store_dir())


def test_calendar_store_and_hash_match_rules():
    src = _home() / "cal_src"
    src.mkdir()
    (src / "MANIFEST.yaml").write_bytes(b"version: 1\n")
    (src / "holidays_KRX.yaml").write_bytes(b"rows: []\n")
    (src / "sub").mkdir()
    (src / "sub" / "ignored.yaml").write_bytes(b"x")
    sha = signer.calendar_sha256(src)
    assert sha == rules.calendar_sha256(src)
    _raises(lambda: signer.store_calendar(src, (0, "e" * 64)), ValueError)
    assert not owner.store_dir().exists(), "a bad anchor was found only after the files were written"
    assert signer.store_calendar(src, (5, "e" * 64)) == sha
    assert signer.store_calendar(src, (5, "e" * 64)) == sha                      # idempotent
    dest = owner.store_dir() / "calendar" / sha
    assert _tree(dest) == {"MANIFEST.yaml": b"version: 1\n", "holidays_KRX.yaml": b"rows: []\n"}, _tree(dest)
    anchor = json.loads((owner.store_dir() / "calendar" / f"{sha}.anchor.json").read_bytes())
    assert anchor == {"seq": 5, "row_sha256": "e" * 64}, anchor
    assert owner.store_get("calendar", sha) == rules.calendar_stream(src)       # the gate rebuilds the same stream
    mine = _tree(owner.store_dir())
    shutil.rmtree(owner.store_dir())
    assert owner.store_put("calendar", rules.calendar_stream(src), (5, "e" * 64)) == sha
    assert _tree(owner.store_dir()) == mine, (sorted(_tree(owner.store_dir())), sorted(mine))
    (src / "holidays_KRX.yaml").write_bytes(b"rows: [1]\n")
    assert signer.calendar_sha256(src) != sha
    assert "changed after it was shown" in str(_raises(lambda: signer._put_calendar(src, sha), RuntimeError))


def test_calendar_refuses_links_like_rules():
    """rules.calendar_stream's one framing: a link as the folder or as an entry refuses the whole set (it is
    Invalid there, ValueError here), so the approval and the store hash the same bytes. Windows uses
    directory junctions; POSIX uses real directory symlinks."""
    plain, elsewhere, linked_dir = _home() / "plain", _home() / "elsewhere", _home() / "linked_dir"
    plain.mkdir()
    elsewhere.mkdir()
    (plain / "MANIFEST.yaml").write_bytes(b"version: 1\n")
    (elsewhere / "MANIFEST.yaml").write_bytes(b"version: 1\n")
    fx.directory_link(linked_dir, elsewhere)                      # the folder itself is a link
    assert signer.calendar_sha256(plain) == rules.calendar_sha256(plain)
    for folder in (linked_dir, _home() / "absent"):
        assert "not a plain directory" in str(_raises(lambda: rules.calendar_sha256(folder), rules.Invalid))
        assert "not a plain directory" in str(_raises(lambda: signer.calendar_sha256(folder), ValueError))
    fx.directory_link(plain / "linked", elsewhere)                # an entry is a link
    assert "is a link" in str(_raises(lambda: rules.calendar_sha256(plain), rules.Invalid))
    assert "is a link" in str(_raises(lambda: signer.calendar_sha256(plain), ValueError))
    _raises(lambda: signer.store_calendar(plain, (5, "e" * 64)), ValueError)
    assert not signer._store_dir().exists(), "a calendar set holding a link reached the store"   # not owner.*: the
    # junctions in this temp home make core.isolation refuse the whole state root (A0)


def test_writes_refuse_a_junctioned_folder():
    """owner._write_new's `within` rule: every folder and file the signer writes must resolve inside the state root,
    so a junctioned compliance folder refuses the store write and the log append before any folder is made."""
    root, outside = _home() / "root", _home() / "outside"
    root.mkdir()
    outside.mkdir()
    fx.directory_link(root / "compliance", outside)
    saved = os.environ["TRADEGEN_HOME"]
    os.environ["TRADEGEN_HOME"] = str(root)
    try:
        for write in (lambda: signer.store_file("rules", b"x: 1\n", (1, "f" * 64)),
                      lambda: signer._commit(None, "session_armed", {"session_id": "S1"}, utc=UTC)):
            try:
                write()
            except RuntimeError:
                pass
            else:
                raise AssertionError("wrote through a junction that leaves the state root")
    finally:
        os.environ["TRADEGEN_HOME"] = saved
    assert list(outside.iterdir()) == [], list(outside.iterdir())


# --------------------------------------------------------------------------- #
# The commands, with the interactive steps replaced (spec 6.4: what is shown is what is signed)
# --------------------------------------------------------------------------- #
def test_commands_sign_exactly_what_was_shown():
    _need_crypto()
    key = fx.test_key()
    shown = []
    pub = _home() / "test_pubkey.pem"
    fx.write_pubkey(pub, key)
    draft = ROOT / "core" / "compliance" / "kr_rules.yaml"
    cal = _home() / "cal_src"
    cal.mkdir()
    (cal / "MANIFEST.yaml").write_bytes(b"version: 1\n")
    assert Path(sys.prefix).resolve() == (ROOT / ".venv").resolve(), "run the suite with .venv/Scripts/python.exe"
    with _patched(signer, "_confirm", lambda kind, data, head, utc: shown.append((kind, data, head, utc))), \
            _patched(signer, "_unlock", lambda path: key):
        parser = signer._parser()
        for argv in (["approve", "--kind", "rules", "--path", str(draft)],
                     ["approve", "--kind", "calendar", "--path", str(cal)],
                     ["event", "cap_set", "--data", '{"key": "okx_equity_share", "value": 1}'],
                     ["code-approve", "--repo", str(ROOT)]):
            args = parser.parse_args(argv)
            code, _, _ = _quiet(args.run, args)
            assert code == 0, argv
    cal_sha = signer.calendar_sha256(cal)
    lines = _log_lines()
    signed = [(json.loads(x)["kind"], json.loads(x)["data"], json.loads(x)["utc"]) for x in lines]
    assert signed == [(k, d, u) for k, d, _, u in shown], (signed, shown)    # kind, data and stamp as shown
    assert [h for _, _, h, _ in shown][0] == (0, ""), shown
    assert type(shown[2][1]["value"]) is float and type(signed[2][1]["value"]) is float, shown[2]   # caps are floats
    assert b'"value":1.0' in lines[2], lines[2]
    check = owner.verify_log(lines, owner.read_pubkey(pub), owner.read_anchors())
    assert check.ok, check.reason
    force = owner.in_force(check)
    assert force["rules"] == (rules.file_sha256(draft.read_bytes()), 1), force
    assert force["calendar"] == (cal_sha, 2), force
    assert owner.store_get("rules", force["rules"][0]) == draft.read_bytes()
    assert owner.store_get("calendar", cal_sha) is not None                     # the gate can read the copy
    assert owner.code_approval(check) == owner.code_hash(ROOT)
    with _patched(sys, "prefix", str(_home())), _patched(signer, "_read_typed", _never), \
            _patched(signer.getpass, "getpass", _never):
        args = signer._parser().parse_args(["code-approve", "--repo", str(ROOT)])
        try:
            args.run(args)
        except ValueError as exc:
            assert "run me with" in str(exc), exc
        else:
            raise AssertionError("code-approve ran outside the repo venv")


def test_commit_refuses_an_approval_whose_bytes_are_not_stored():
    """Spec 6.4 / Task 13's order: the blob is stored before the approved line, the anchor after it."""
    _need_crypto()
    key = fx.test_key()
    raw = fx.shipped_bytes("rules")
    sha = rules.file_sha256(raw)
    for data in ({"kind": "rules", "sha256": sha}, {"kind": "calendar", "sha256": "c" * 64}):
        assert "store its bytes" in str(_raises(lambda: signer._commit(key, "approved", data, utc=UTC), RuntimeError))
    assert not owner.log_path().exists(), "an approval was signed before its bytes were stored"
    signer._put_blob("rules", raw)
    assert not any((owner.store_dir() / "rules").glob("*.anchor.json")), "an anchor before its line"
    seq, row = signer._commit(key, "approved", {"kind": "rules", "sha256": sha}, utc=UTC)
    anchor = owner.store_dir() / "rules" / f"{sha}.anchor.json"
    assert json.loads(anchor.read_bytes()) == {"seq": seq, "row_sha256": row} and owner.read_anchors() == [(seq, row)]
    assert owner.verify_log(_log_lines(), _raw(key), owner.read_anchors()).ok


def test_key_rotated_must_name_the_key_that_signs_it():
    """P20: key_rotated is signed by the old key, so the command refuses data whose old key is not the unlocked
    one; with the right old key the rotated log verifies against the new key's pem."""
    _need_crypto()
    key1, key2 = fx.test_key(), _second_key()
    parser = signer._parser()
    with _patched(signer, "_confirm", lambda kind, data, head, utc: None), _patched(signer, "_unlock", lambda p: key1):
        wrong = {"old_pubkey_b64": _b64(key2), "new_pubkey_b64": _b64(key1)}
        args = parser.parse_args(["event", "key_rotated", "--data", json.dumps(wrong)])
        assert "not the key you unlocked" in str(_raises(lambda: _quiet(args.run, args), ValueError))
        assert not owner.log_path().exists()
        right = {"old_pubkey_b64": _b64(key1), "new_pubkey_b64": _b64(key2)}
        args = parser.parse_args(["event", "key_rotated", "--data", json.dumps(right)])
        assert _quiet(args.run, args)[0] == 0
    check = owner.verify_log(_log_lines(), _raw(key2), [])
    assert check.ok and check.first_key_fingerprint == owner.fingerprint(_raw(key1)), check.reason
    assert not owner.verify_log(_log_lines(), _raw(key1), []).ok, "the old pem must not verify a rotated log"


def _third_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(bytes(range(2, 34)))


def test_only_the_key_in_force_can_extend_the_log():
    """A line signed by any other key passes _head but makes owner.verify_log fail under every pem, for good. So
    under the lock, and before anything is written: after a key_rotated only its new key signs; with no rotation
    only the key that signed the last owner line; a log with no owner line takes any key."""
    _need_crypto()
    key1, key2, key3 = fx.test_key(), _second_key(), _third_key()
    armed = {"session_id": "S1"}
    stamp = iter(f"2026-10-23T{h:02d}:00:00Z" for h in range(1, 24))
    log = owner.log_path()

    def refused(key, kind="session_armed", data=armed, fragment="key"):
        before = log.read_bytes()
        assert fragment in str(_raises(lambda: signer._commit(key, kind, data, utc=next(stamp)), ValueError))
        assert log.read_bytes() == before, "a refused entry changed the log"

    owner.append_system_entry("system_halt", {"floor_krw": 1.0}, datetime(2026, 10, 23, tzinfo=timezone.utc))
    assert signer._commit(key3, "session_armed", armed, utc=next(stamp))[0] == 2   # no owner line yet: any key
    refused(key1, fragment="did not sign the log's last owner entry #2")           # now key3 is the owner key
    refused(key2)
    assert signer._commit(key3, "session_armed", {"session_id": "S2"}, utc=next(stamp))[0] == 3
    # rotate key3 -> key1; the old key is refused from then on, and so is every stranger
    refused(key3, "key_rotated", {"old_pubkey_b64": _b64(key1), "new_pubkey_b64": _b64(key2)},
            fragment="old_pubkey_b64 is not the key you unlocked")                 # names a key it is not
    assert signer._commit(key3, "key_rotated", {"old_pubkey_b64": _b64(key3), "new_pubkey_b64": _b64(key1)},
                          utc=next(stamp))[0] == 4
    refused(key3, fragment="not the key in force since entry #4")                  # the retired key
    refused(key2, fragment="not the key in force since entry #4")                  # a stranger
    refused(key1, "key_rotated", {"old_pubkey_b64": _b64(key3), "new_pubkey_b64": _b64(key2)},
            fragment="old_pubkey_b64 is not the key you unlocked")                 # right signer, wrong old key
    assert signer._commit(key1, "session_armed", {"session_id": "S3"}, utc=next(stamp))[0] == 5
    assert signer._commit(key1, "key_rotated", {"old_pubkey_b64": _b64(key1), "new_pubkey_b64": _b64(key2)},
                          utc=next(stamp))[0] == 6
    refused(key1, fragment="not the key in force since entry #6")
    assert signer._commit(key2, "session_armed", {"session_id": "S4"}, utc=next(stamp))[0] == 7
    check = owner.verify_log(_log_lines(), _raw(key2), [])
    assert check.ok and check.first_key_fingerprint == owner.fingerprint(_raw(key3)), check.reason


def test_a_command_with_the_wrong_key_stores_nothing():
    """The key is judged right after the passphrase, before `approve` stores any bytes."""
    _need_crypto()
    key1, key2 = fx.test_key(), _second_key()
    signer._commit(key1, "key_rotated", {"old_pubkey_b64": _b64(key1), "new_pubkey_b64": _b64(key2)}, utc=UTC)
    draft = ROOT / "core" / "compliance" / "kr_rules.yaml"
    before = owner.log_path().read_bytes()
    argv = ["approve", "--kind", "rules", "--path", str(draft)]
    with _patched(signer, "_confirm", lambda kind, data, head, utc: None):
        for key, ok in ((key1, False), (key2, True)):
            args = signer._parser().parse_args(argv)
            with _patched(signer, "_unlock", lambda path, key=key: key):
                if ok:
                    assert _quiet(args.run, args)[0] == 0
                    continue
                assert "not the key in force" in str(_raises(lambda: _quiet(args.run, args), ValueError))
            assert owner.log_path().read_bytes() == before and not owner.store_dir().exists()
    assert owner.verify_log(_log_lines(), _raw(key2), owner.read_anchors()).ok


def test_approve_refuses_an_empty_calendar_folder_before_any_prompt():
    empty = _home() / "empty_cal"
    empty.mkdir()
    args = signer._parser().parse_args(["approve", "--kind", "calendar", "--path", str(empty)])
    with _patched(signer, "_read_typed", _never), _patched(signer, "_unlock", _never), \
            _patched(signer.getpass, "getpass", _never):
        assert "no files" in str(_raises(lambda: args.run(args), ValueError))
    assert not owner.log_path().exists() and not owner.store_dir().exists()


def test_keygen_writes_key_and_public_key():
    _need_crypto()
    key_path = _home() / "compliance" / "owner_key.enc"
    args = signer._parser().parse_args(["keygen"])
    for answers in (["a" * 19], ["correct horse battery staple x", "different"]):
        with _patched(signer.getpass, "getpass", lambda prompt, a=iter(answers): next(a)):
            try:
                _quiet(args.run, args)
            except ValueError:
                pass
            else:
                raise AssertionError(f"keygen accepted {answers}")
        assert not key_path.exists() and not key_path.with_suffix(".pem").exists()
    with _patched(signer.getpass, "getpass", lambda prompt, a=iter([PASS, PASS]): next(a)):
        code, out, _ = _quiet(args.run, args)
    assert code == 0, out
    pem_raw = owner.read_pubkey(key_path.with_suffix(".pem"))
    assert owner.fingerprint(pem_raw) in out
    seed = signer.open_key(key_path.read_bytes(), PASS)
    assert signer._pub_raw(seed) == pem_raw
    fp_args = signer._parser().parse_args(["fingerprint"])
    code, out, _ = _quiet(fp_args.run, fp_args)
    assert code == 0 and out.count(owner.fingerprint(pem_raw)) == 2, out
    with _patched(signer.getpass, "getpass", _never):
        try:
            _quiet(args.run, args)
        except ValueError as exc:
            assert "already exists" in str(exc), exc
        else:
            raise AssertionError("keygen overwrote a key")
    assert list(_home().rglob("*.tmp")) == [], list(_home().rglob("*.tmp"))


def test_keygen_with_an_explicit_key_path_writes_beside_it():
    """`--key PATH` is the owner's own choice (a rotation key, say): it is checked as a final target only, its temp
    file sits next to it, and nothing lands in the state root."""
    _need_crypto()
    key_path = _home() / "elsewhere" / "second_key.enc"
    args = signer._parser().parse_args(["keygen", "--key", str(key_path)])
    with _patched(signer.getpass, "getpass", lambda prompt, a=iter([PASS, PASS]): next(a)):
        code, out, _ = _quiet(args.run, args)
    assert code == 0, out
    assert sorted(p.name for p in key_path.parent.iterdir()) == ["second_key.enc", "second_key.pem"]
    assert signer._pub_raw(signer.open_key(key_path.read_bytes(), PASS)) == owner.read_pubkey(
        key_path.with_suffix(".pem"))
    assert sorted(p.name for p in _home().iterdir()) == ["elsewhere"], "keygen --key wrote into the state root"


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def test_pem_reader_maps_the_errors_read_pubkey_maps():
    """_pem_raw copies owner.read_pubkey, including the UnsupportedAlgorithm -> ValueError mapping."""
    _need_crypto()
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

    def spki(oid: bytes) -> bytes:                  # a well-formed SubjectPublicKeyInfo naming algorithm `oid`
        def der(tag: int, body: bytes) -> bytes:
            return bytes([tag, len(body)]) + body
        body = der(0x30, der(0x30, der(0x06, oid)) + der(0x03, b"\x00" + bytes(range(32))))
        return b"-----BEGIN PUBLIC KEY-----\n" + base64.b64encode(body) + b"\n-----END PUBLIC KEY-----\n"

    pem = _home() / "k.pem"
    fx.write_pubkey(pem)
    assert signer._pem_raw(pem.read_bytes()) == owner.read_pubkey(pem) == _raw(fx.test_key())
    for bad in (X25519PrivateKey.from_private_bytes(bytes(32)).public_key().public_bytes(
                    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
                b"-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n",
                spki(bytes([0x2B, 0xCE, 0x0F, 0x01])),                           # OID 1.3.9999.1: no such algorithm
                b"not a pem"):
        pem.write_bytes(bad)
        _raises(lambda: owner.read_pubkey(pem), ValueError)
        _raises(lambda: signer._pem_raw(bad), ValueError)


def test_quantgen_refusal_and_link_targets():
    """Both QUANTGEN roots are swapped for fake folders inside the temp home, so the real ~/.nextgen is never
    touched; test_signer_copies_match_the_repo holds the real constants equal to core.isolation's."""
    fake_state, fake_repo = _home() / "fake_nextgen", _home() / "fake_quantgen"
    fake_state.mkdir()
    fake_repo.mkdir()
    saved = os.environ["TRADEGEN_HOME"]
    with _patched(signer, "QUANTGEN_STATE", fake_state), _patched(signer, "QUANTGEN_REPO", fake_repo):
        try:
            for inside in (fake_state / "tradegen", fake_repo / "state"):
                os.environ["TRADEGEN_HOME"] = str(inside)
                try:
                    signer.state_root()
                except RuntimeError:
                    pass
                else:
                    raise AssertionError(f"TRADEGEN_HOME {inside} inside QUANTGEN was accepted")
        finally:
            os.environ["TRADEGEN_HOME"] = saved
        for inside in (fake_state / "x.txt", fake_repo / "x.txt"):
            try:
                signer._checked(inside)
            except RuntimeError:
                pass
            else:
                raise AssertionError(f"target {inside} inside QUANTGEN was accepted")
    assert list(fake_state.iterdir()) == [] and list(fake_repo.iterdir()) == []
    target = _home() / "a.txt"
    target.write_bytes(b"a")
    os.link(target, _home() / "b.txt")
    try:
        signer._checked(_home() / "b.txt")
    except RuntimeError:
        pass
    else:
        raise AssertionError("a hard-linked target was accepted")


def test_help_names_owner_acts_1_and_2():
    text = signer._parser().format_help()
    for needle in ("certutil -hashfile %USERPROFILE%\\tradegen-signer\\sign.py SHA256", "away from the PC",
                   "keygen", "code-approve", "owner_pubkey.pem", "at least 20 characters",
                   "at least 5 different words", "python.exe -I", "site-packages\\*.pth",
                   "Claude never runs this file", "from the next Asia/Seoul date", "blanks do not count",
                   "Key rotation", "keygen --key NEW\\owner_key.enc", "event key_rotated", "copy NEW\\owner_key.pem",
                   "owner_pubkey.pem", "pass --key NEW\\owner_key.enc to every command",
                   "reads BROKEN between steps 3 and 4", "write the new fingerprint on paper",
                   "open Windows Terminal yourself from the Start menu",               # R5, R11
                   "when its parent chain stops before a Windows session process"):
        assert needle in " ".join(text.split()), needle
    assert "python.exe %USERPROFILE%" not in text, "every command line starts python.exe -I"
    parser = signer._parser()
    assert parser.parse_args(["approve", "--kind", "calendar", "--path", "d"]).run is signer._cmd_approve
    assert parser.parse_args(["event", "limit_set", "--data", "{}"]).run is signer._cmd_event
