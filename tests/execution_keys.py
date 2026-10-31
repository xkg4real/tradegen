"""execution/keys.py, the .env reader (E1 Task 2; contract section 5; E2, E27, E28).

Every test runs with every E1 key name out of os.environ and keys._ENV_FILE at a missing file in the temp home
(tests.execution_fixtures.isolated), so the repo .env is never read. A test that needs a file writes one in the temp
home and points _ENV_FILE at it with `_env_file`, which restores it. Only E1 key names are used: isolated() restores
each of them, whatever a test sets. No assertion message ever holds a value read by keys.read.
"""
from __future__ import annotations

import ast
import contextlib
import os
from pathlib import Path

from execution import keys
from tests import execution_fixtures as F

ROOT = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _env_file(data: bytes):
    """keys._ENV_FILE -> a temp-home file holding exactly `data` (bytes, so a BOM and CRLF stay as written)."""
    path = Path(os.environ["TRADEGEN_HOME"]) / "test.env"
    path.write_bytes(data)
    keep = keys._ENV_FILE
    keys._ENV_FILE = path
    try:
        yield path
    finally:
        keys._ENV_FILE = keep


def _missing(names) -> keys.KeyMissing:
    """The KeyMissing that keys.read(names) raises; fails, without printing anything read, when values come back."""
    try:
        keys.read(names)
    except keys.KeyMissing as exc:
        return exc
    raise AssertionError(f"keys.read{tuple(names)!r} returned values")


def test_an_absent_name_falls_back_to_the_file():
    """A name absent from os.environ comes from .env, and the file is parsed at most once per call."""
    with _env_file(b"KIS_APP_KEY=file-value\nKIS_APP_SECRET=other\n"):
        assert "KIS_APP_KEY" not in os.environ
        assert keys.read(("KIS_APP_KEY",)) == ("file-value",)
        parsed, real_parse = [], keys._parse
        keys._parse = lambda text: parsed.append(1) or real_parse(text)
        try:
            assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("file-value", "other")
        finally:
            keys._parse = real_parse
        assert parsed == [1], parsed


def test_parser_handles_export_quotes_comments_and_no_expansion():
    data = (b"# a full-line comment\n"
            b"   # an indented comment: KIS_APP_SECRET=hidden\n"
            b"#KIS_APP_SECRET=hidden-too\n"
            b"\n"
            b"export UPBIT_ACCESS_KEY=exported\n"
            b'UPBIT_SECRET_KEY="double # kept" ignored after the quote\n'
            b"OKX_API_KEY='single'\n"
            b"OKX_API_SECRET=ab+c/d== # an inline comment\n"
            b"OKX_API_PASSPHRASE=pa#ss\n"
            b"KIS_APP_KEY=tabbed\t# a tab comment\n"
            b"KIS_BASE_URL=${KIS_APP_KEY}$HOME\n"
            b"  KIS_ACCOUNT_8 =  spaced  \n"
            b"a line without an equals sign\n"
            b"KIS_ACCOUNT_PD=first\n"
            b"KIS_ACCOUNT_PD=second\n")
    with _env_file(data):
        assert keys.read(("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY", "OKX_API_SECRET",
                          "OKX_API_PASSPHRASE", "KIS_APP_KEY", "KIS_BASE_URL", "KIS_ACCOUNT_8", "KIS_ACCOUNT_PD")) == (
            "exported", "double # kept", "single", "ab+c/d==", "pa#ss", "tabbed", "${KIS_APP_KEY}$HOME", "spaced",
            "second")
        assert _missing(("KIS_APP_SECRET",)).name == "KIS_APP_SECRET"       # only ever in comments
    assert keys._parse("A=1\nA=2\n") == {"A": "2"}
    assert keys._parse("export B='x' # y\n") == {"B": "x"}
    assert keys._parse("S=a=b==\n") == {"S": "a=b=="}                         # split at the first =
    assert keys._parse("#A=1\n  # B=2\n") == {}                              # comment lines never become keys


def test_a_bom_and_crlf_lines_are_read():
    with _env_file(b"\xef\xbb\xbfKIS_APP_KEY=first\r\nKIS_APP_SECRET=second\r\n"):
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("first", "second")


def test_blank_placeholder_and_missing_values_raise_key_missing_with_names_only():
    data = (b"KIS_APP_KEY=\nKIS_APP_SECRET=   \nUPBIT_ACCESS_KEY=<your Upbit access key>\n"
            b"UPBIT_SECRET_KEY='<unset>'\nOKX_API_KEY=\"\"\nKIS_BASE_URL=set\n")
    with _env_file(data):
        for name in ("KIS_APP_KEY", "KIS_APP_SECRET", "UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY", "OKX_API_KEY",
                     "OKX_API_SECRET"):                                         # the last is not in the file
            exc = _missing((name,))
            assert exc.name == name and exc.args == (f"{name} is not set in .env or the environment",), exc.args
            assert "<" not in str(exc) and "unset" not in str(exc), str(exc)
        assert _missing(("KIS_BASE_URL", "UPBIT_SECRET_KEY", "KIS_APP_KEY")).name == "UPBIT_SECRET_KEY"   # the first
    assert not keys._ENV_FILE.exists()                                          # the suite's missing file
    assert _missing(("OKX_API_PASSPHRASE",)).name == "OKX_API_PASSPHRASE"


def test_the_environment_decides_alone():
    """A name present in os.environ is never looked up in .env: '<unset>' or a blank value there is missing even
    when the file holds the name, so the KEYLESS prefix keeps E1 keyless."""
    with _env_file(b"".join(f"{n}=file-{n.lower()}\n".encode("ascii") for n in F.FAKE_KEYS)):
        for value in ("<unset>", "", "   ", " <unset> "):
            os.environ["KIS_APP_KEY"] = value
            assert _missing(("KIS_APP_KEY",)).name == "KIS_APP_KEY", repr(value)
        os.environ["KIS_APP_KEY"] = "  env-value  "
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("env-value", "file-kis_app_secret")
        for name in F.FAKE_KEYS:                                                 # the KEYLESS prefix
            os.environ[name] = "<unset>"
        for name in F.FAKE_KEYS:
            assert _missing((name,)).name == name
    keep = keys._ENV_FILE
    try:
        keys._ENV_FILE = Path(os.environ["TRADEGEN_HOME"])                      # a folder: reading it fails
        os.environ["KIS_APP_KEY"], os.environ["KIS_APP_SECRET"] = "a", "b"
        assert keys.read(("KIS_APP_KEY", "KIS_APP_SECRET")) == ("a", "b")       # so the file was not read
        try:
            keys.read(("KIS_APP_KEY", "KIS_BASE_URL"))                         # KIS_BASE_URL is not in os.environ
        except OSError:
            pass                                                                # only an unreadable file fails
        else:
            raise AssertionError("a name absent from os.environ did not read .env")
    finally:
        keys._ENV_FILE = keep


def test_only_the_requested_names_come_back():
    with _env_file(b"KIS_APP_KEY=k\nKIS_APP_SECRET=s\nOKX_API_SECRET=o\n"):
        assert keys.read(("OKX_API_SECRET", "KIS_APP_KEY")) == ("o", "k")
        assert keys.read(["KIS_APP_SECRET"]) == ("s",)
        assert keys.read(()) == ()


def test_a_bad_name_is_refused_before_anything_is_read():
    keep = keys._ENV_FILE
    try:
        keys._ENV_FILE = Path(os.environ["TRADEGEN_HOME"])                      # reading it would raise OSError
        for names in (("kis_app_key",), ("1ABC",), ("A-B",), ("A B",), ("",), ("A=B",), ("KIS_APP_KEY", "x"),
                      (None,), ("_A",), "KIS_APP_KEY", "ABC"):              # "ABC": each letter is a good name
            try:
                keys.read(names)
            except ValueError as exc:
                assert str(exc) == "keys: bad name", str(exc)
            else:
                raise AssertionError(f"keys.read({names!r}) was not refused")
    finally:
        keys._ENV_FILE = keep


def test_the_suite_never_reads_the_repo_env():
    home = Path(os.environ["TRADEGEN_HOME"])
    assert keys._ENV_FILE == home / "no-such.env" and not keys._ENV_FILE.exists(), keys._ENV_FILE
    assert keys._ENV_FILE.resolve() != (ROOT / ".env").resolve()
    for name in F.KEY_NAMES:
        assert name not in os.environ, name
        assert _missing((name,)).name == name


def test_the_default_env_file_is_the_repo_root_env():
    """Checked from the source text: a reload would point _ENV_FILE back at the real .env in the middle of the suite
    (contract 0.2)."""
    tree = ast.parse((ROOT / "execution" / "keys.py").read_text(encoding="utf-8"))
    found = [ast.unparse(n.value) for n in tree.body
             if isinstance(n, ast.Assign) and [ast.unparse(t) for t in n.targets] == ["_ENV_FILE"]]
    assert found == ["Path(__file__).resolve().parents[1] / '.env'"], found
    assert Path(keys.__file__).resolve().parents[1] == ROOT, keys.__file__
