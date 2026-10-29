"""A0, the isolation residual (compliance plan Task 2; spec 4 "Isolation residual", 8.9 last bullet; P7, P8).

`core.isolation.checked_target` refuses a QUANTGEN path, a symlink, a junction, a hard link and an escape from
`within`; `scan_links` refuses a linked root, any link under a state root and an unlistable root, and is memoised
per root; `state_root` honours TRADEGEN_HOME and refuses QUANTGEN's state before any walk; each of the five writers
the loaders reach refuses a hard-linked target and leaves the other name's bytes alone. QUANTGEN is faked by swapping
`core.isolation.QUANTGEN_STATE` / `QUANTGEN_REPO` to temp dirs: no test here links to, walks or writes the real
~/.nextgen or the real QUANTGEN repo.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from pathlib import Path

import config
from core import isolation
from tests import compliance_fixtures
from tests.notrun import NotRun

VICTIM = b"QUANTGEN-OWNED: never written by TRADEGEN\n"


@contextlib.contextmanager
def _fake_quantgen():
    """Temp stand-ins for ~/.nextgen and the QUANTGEN repo; yields (state, repo, scratch)."""
    base = Path(tempfile.mkdtemp(prefix="a0_"))
    state, repo, scratch = base / "nextgen", base / "QUANTGEN", base / "scratch"
    for d in (state, repo, scratch):
        d.mkdir()
    keep = (isolation.QUANTGEN_STATE, isolation.QUANTGEN_REPO)
    try:
        isolation.QUANTGEN_STATE, isolation.QUANTGEN_REPO = state, repo
        yield state, repo, scratch
    finally:
        isolation.QUANTGEN_STATE, isolation.QUANTGEN_REPO = keep
        shutil.rmtree(base, ignore_errors=True)              # rmtree removes a junction without following it


def _junction(link: Path, target: Path) -> None:
    try:
        import _winapi
    except ImportError:
        raise NotRun("REFDATA: directory junctions need Windows") from None
    target.mkdir(parents=True, exist_ok=True)
    _winapi.CreateJunction(str(target), str(link))


def _symlink(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
    except OSError:
        raise NotRun("REFDATA: symlink creation needs Developer Mode") from None


def _hard_linked(state: Path, link: Path) -> Path:
    """`link` becomes a second name of a new file inside the fake QUANTGEN state; returns that file."""
    victim = state / f"victim_{link.name}"
    victim.write_bytes(VICTIM)
    link.parent.mkdir(parents=True, exist_ok=True)
    os.link(victim, link)
    return victim


def _refused(call, needle: str) -> str:
    """The RuntimeError message of `call()`, which must contain `needle`."""
    try:
        call()
    except RuntimeError as exc:
        assert needle in str(exc), exc
        return str(exc)
    raise AssertionError(f"not refused (wanted {needle!r})")


# --------------------------------------------------------------------------- #
# checked_target
# --------------------------------------------------------------------------- #
def test_checked_target_returns_the_path_and_creates_nothing():
    with _fake_quantgen() as (_state, _repo, scratch):
        new = scratch / "new" / "file.json"
        assert isolation.checked_target(new, "probe") == new and not (scratch / "new").exists()
        plain = scratch / "plain.json"
        plain.write_bytes(b"{}")
        assert isolation.checked_target(str(plain)) == plain                       # str in, Path out
        assert isolation.checked_target(scratch, within=scratch.parent) == scratch   # a folder is fine
        assert isolation.checked_target(scratch / "a" / "b.json", within=scratch) == scratch / "a" / "b.json"


def test_checked_target_refuses_quantgen_paths_and_aliases():
    with _fake_quantgen() as (state, repo, scratch):
        _refused(lambda: isolation.checked_target(state / "kis_token.json"), "inside QUANTGEN")
        _refused(lambda: isolation.checked_target(repo / "grokteam" / "out" / "x.json"), "inside QUANTGEN")
        _junction(scratch / "alias", state)
        _refused(lambda: isolation.checked_target(scratch / "alias" / "kis_token.json"), "inside QUANTGEN")
        assert not (state / "kis_token.json").exists()


def test_checked_target_refuses_junctions():
    with _fake_quantgen() as (_state, _repo, scratch):
        _junction(scratch / "j", scratch / "elsewhere")                          # harmless target, still refused
        _refused(lambda: isolation.checked_target(scratch / "j"), "junction")


def test_checked_target_refuses_hard_links():
    with _fake_quantgen() as (state, _repo, scratch):
        victim = _hard_linked(state, scratch / "token.json")
        _refused(lambda: isolation.checked_target(scratch / "token.json"), "hard link")
        alone = scratch / "alone.json"
        alone.write_bytes(b"{}")
        os.link(alone, scratch / "second.json")
        _refused(lambda: isolation.checked_target(alone), "hard link")             # either name of a shared file
        assert victim.read_bytes() == VICTIM


def test_checked_target_refuses_an_escape_from_within():
    with _fake_quantgen() as (_state, _repo, scratch):
        data = scratch / "data"
        _refused(lambda: isolation.checked_target(data / "kalshi" / ".." / ".." / "x.json", within=data), "outside")
        _refused(lambda: isolation.checked_target(scratch / "x.json", within=data), "outside")
        assert isolation.checked_target(data / "kalshi" / "e.json", within=data) == data / "kalshi" / "e.json"


def test_symlinks_are_refused():
    """NOT_RUN where os.symlink needs Developer Mode (this machine); junctions and hard links cover the rest."""
    with compliance_fixtures.temp_home(), _fake_quantgen() as (_state, _repo, scratch):
        (scratch / "real.txt").write_bytes(b"x")
        _symlink(scratch / "link.txt", scratch / "real.txt")
        _refused(lambda: isolation.checked_target(scratch / "link.txt"), "symlink")
        (scratch / "root").mkdir()
        _symlink(scratch / "root" / "s.txt", scratch / "real.txt")
        _refused(lambda: isolation.scan_links(scratch / "root"), "symlink")


# --------------------------------------------------------------------------- #
# scan_links and state_root
# --------------------------------------------------------------------------- #
def test_scan_links_refuses_junctions_and_hard_links():
    with compliance_fixtures.temp_home(), _fake_quantgen() as (state, _repo, scratch):
        clean = scratch / "clean"
        (clean / "macro" / "ledgers").mkdir(parents=True)
        (clean / "macro" / "ledgers" / "C3.jsonl").write_bytes(b"{}\n")
        isolation.scan_links(clean)
        assert isolation._LINK_SCAN[str(clean.resolve())] is None
        junction_home = scratch / "junction_home"
        (junction_home / "macro").mkdir(parents=True)
        _junction(junction_home / "macro" / "ledgers", scratch / "elsewhere")
        msg = _refused(lambda: isolation.scan_links(junction_home), "junction")
        assert str(junction_home / "macro" / "ledgers") in msg, msg
        _junction(scratch / "root_j", scratch / "elsewhere2")                  # the root itself is a junction
        _refused(lambda: isolation.scan_links(scratch / "root_j"), "junction")
        hard_home = scratch / "hard_home"
        hard_home.mkdir()
        _hard_linked(state, hard_home / "kis_token.json")
        msg = _refused(lambda: isolation.scan_links(hard_home), "hard link")
        assert str(hard_home / "kis_token.json") in msg, msg
        (scratch / "a_file").write_bytes(b"x")
        _refused(lambda: isolation.scan_links(scratch / "a_file"), "cannot list")   # an unlistable root fails closed
        missing = scratch / "not_yet"
        isolation.scan_links(missing)
        assert str(missing.resolve()) not in isolation._LINK_SCAN                  # scanned once it exists


def test_scan_links_judges_a_linked_root_on_every_call():
    """The memo is keyed on the resolved root, so a junction to a clean root shares its key: the link verdict must not
    come from, or go into, the memo (either scan order)."""
    with compliance_fixtures.temp_home(), _fake_quantgen() as (_state, _repo, scratch):
        target, link = scratch / "target", scratch / "link"
        target.mkdir()
        (target / "f.txt").write_bytes(b"x")
        _junction(link, target)
        key = str(target.resolve())
        isolation.scan_links(target)                                 # target first: clean, memoised
        assert isolation._LINK_SCAN[key] is None
        _refused(lambda: isolation.scan_links(link), "junction")     # the memo must not wave the junction through
        os.environ["TRADEGEN_HOME"] = str(link)
        _refused(isolation.state_root, "junction")
        assert isolation._LINK_SCAN[key] is None                     # and the junction's refusal is not stored
        isolation._LINK_SCAN.clear()
        _refused(lambda: isolation.scan_links(link), "junction")     # junction first
        assert key not in isolation._LINK_SCAN
        isolation.scan_links(target)                                 # the clean target is still clean
        assert isolation._LINK_SCAN[key] is None


def test_scan_links_is_memoised_and_cleared_by_temp_home():
    with compliance_fixtures.temp_home() as outer, _fake_quantgen() as (state, _repo, scratch):
        root = scratch / "home"
        root.mkdir()
        key = str(root.resolve())
        isolation.scan_links(root)
        assert isolation._LINK_SCAN[key] is None
        _hard_linked(state, root / "late.bin")
        isolation.scan_links(root)                                  # the clean memo answers: no second walk
        isolation._LINK_SCAN.pop(key)
        _refused(lambda: isolation.scan_links(root), "hard link")   # a fresh walk sees the link
        (root / "late.bin").unlink()
        _refused(lambda: isolation.scan_links(root), "hard link")   # and the refusal is memoised too
        isolation._LINK_SCAN["planted"] = None
        with compliance_fixtures.temp_home() as inner:
            assert isolation._LINK_SCAN == {} and os.environ["TRADEGEN_HOME"] == str(inner)
            isolation._LINK_SCAN["inner"] = None
        assert isolation._LINK_SCAN == {} and os.environ["TRADEGEN_HOME"] == str(outer) and not inner.exists()


def test_state_root_honours_tradegen_home():
    with compliance_fixtures.temp_home() as home:
        assert isolation.state_root() == home and config.state_root() == home
        assert isolation._LINK_SCAN[str(home.resolve())] is None
        for raw in (f'"{home}"', f"  '{home}'  "):
            os.environ["TRADEGEN_HOME"] = raw
            assert isolation.state_root() == home, raw
        seen, keep = [], isolation.scan_links
        try:
            isolation.scan_links = seen.append                      # the real default root is not walked here
            for raw in ("", "   ", "<your TRADEGEN state dir>"):
                os.environ["TRADEGEN_HOME"] = raw
                assert isolation.state_root() == Path.home() / ".tradegen", raw
        finally:
            isolation.scan_links = keep
        assert seen == [Path.home() / ".tradegen"] * 3, seen


def test_state_root_refuses_quantgen_and_a_linked_home():
    assert isolation.QUANTGEN_STATE == Path.home() / ".nextgen"     # the real name; compared, never stat'ed here
    with compliance_fixtures.temp_home(), _fake_quantgen() as (state, _repo, scratch):
        _hard_linked(state, scratch / "probe.bin")                  # state/victim_probe.bin now has st_nlink 2
        os.environ["TRADEGEN_HOME"] = str(state)
        _refused(isolation.state_root, "inside QUANTGEN")           # a scan-first state_root would say "hard link"
        _refused(config.state_root, "inside QUANTGEN")
        assert str(state.resolve()) not in isolation._LINK_SCAN     # refused before any walk
        _junction(scratch / "home_alias", state)
        os.environ["TRADEGEN_HOME"] = str(scratch / "home_alias")
        _refused(isolation.state_root, "inside QUANTGEN")
        linked = scratch / "linked_home"
        linked.mkdir()
        _hard_linked(state, linked / "kis_token.json")
        os.environ["TRADEGEN_HOME"] = str(linked)
        _refused(isolation.state_root, "hard link")
        _refused(config.state_root, "hard link")                    # config.state_root delegates (P7)


# --------------------------------------------------------------------------- #
# The five writers the reused loaders reach (P8: each refusal propagates)
# --------------------------------------------------------------------------- #
def test_kis_token_writer_refuses_a_hard_linked_target():
    from data.krx import kis_client
    with _fake_quantgen() as (state, _repo, scratch):
        target = scratch / "kis_token.json"
        victim = _hard_linked(state, target)
        keep = kis_client._TOKEN_PATH
        try:
            kis_client._TOKEN_PATH = target
            _refused(lambda: object.__new__(kis_client.KISClient)._store_token("t", 60.0), "hard link")
        finally:
            kis_client._TOKEN_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_kis_token_is_refused_before_the_token_request():
    """R8 (compliance-gate ledger:81): on a cache miss token() checks the cache target before it reads a credential
    or sends the token request, so a refused target burns no token issuance (KIS rate-limits issuance hard).
    _store_token keeps its own check for a direct call (R12, the test above)."""
    from data.krx import kis_client
    calls = []

    class _Once:                                        # stands in for requests: records the POST, then fails
        @staticmethod
        def post(url, **_kw):
            calls.append(f"POST {url}")
            raise ConnectionError("the token request was sent")

    with _fake_quantgen() as (state, _repo, scratch):
        target = scratch / "kis_token.json"
        victim = _hard_linked(state, target)            # VICTIM is not a token, so the cache misses
        keep = (kis_client._TOKEN_PATH, kis_client._once, config.kis_credentials)
        try:
            kis_client._TOKEN_PATH, kis_client._once = target, _Once
            config.kis_credentials = lambda: calls.append("credentials") or ("k", "s")   # the T-RO-02 recorder
            client = object.__new__(kis_client.KISClient)
            client.ready, client.base_url, client.timeout_s = True, "https://example.invalid", 1.0
            _refused(client.token, "hard link")
            assert calls == [], calls                   # no credential read, no token request
            kis_client._TOKEN_PATH = scratch / "clean" / "kis_token.json"   # control: a clean target reaches the POST
            _refused(client.token, "token request failed: ConnectionError")
            assert calls == ["credentials", "POST https://example.invalid/oauth2/tokenP"], calls
        finally:
            kis_client._TOKEN_PATH, kis_client._once, config.kis_credentials = keep
        assert victim.read_bytes() == VICTIM


def test_opendart_cache_writer_refuses_a_hard_linked_target():
    from data.krx import opendart_client
    with _fake_quantgen() as (state, _repo, scratch):
        target = scratch / "dart_corp_codes.json"
        victim = _hard_linked(state, target)
        keep = opendart_client._CACHE_PATH
        try:
            opendart_client._CACHE_PATH = target
            client = object.__new__(opendart_client.OpenDARTClient)
            _refused(lambda: client._store_cache({"005930": {"corp_code": "00126380", "corp_name": "x"}}),
                     "hard link")
        finally:
            opendart_client._CACHE_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_history_cache_writer_refuses_a_hard_linked_target():
    from core.quant import history as H
    dates = tuple(f"2026-09-{d:02d}" for d in range(1, 31))

    def fetch(symbol, days):
        return H.History(symbol, "UPBIT", dates, tuple(float(i) for i in range(1, 31)))

    with _fake_quantgen() as (state, _repo, scratch):
        victim = _hard_linked(state, scratch / "HIST_CRYPTO_BTC-KRW_30.json")
        keep = (config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir)
        try:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = 3600.0, (lambda: scratch)
            _refused(lambda: H._cached("CRYPTO", fetch, "BTC-KRW", 30), "hard link")
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
        assert victim.read_bytes() == VICTIM


def test_ficc_cache_writer_refuses_a_hard_linked_target():
    from core.ficc import data as D
    with _fake_quantgen() as (state, _repo, scratch):
        victim = _hard_linked(state, scratch / "A0_PROBE_1.json")
        keep = (config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir)
        try:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = 3600.0, (lambda: scratch)
            _refused(lambda: D._cache_put("A0_PROBE_1", [("2026-10-22", 1.0)]), "hard link")
            assert "A0_PROBE_1" not in D._MEM, "a refused key was cached in memory"
            D._cache_put("A0_PROBE_2", [("2026-10-22", 1.0)])                # control: a clean key is cached
            assert "A0_PROBE_2" in D._MEM, "a clean key was not cached in memory"
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
            D._MEM.pop("A0_PROBE_1", None)
            D._MEM.pop("A0_PROBE_2", None)
        assert victim.read_bytes() == VICTIM


def test_grokteam_writer_refuses_links_and_escapes():
    """The cache file, its .tmp sidecar and MANIFEST.jsonl are each checked before anything is written, and the file
    must stay inside DATA (Kalshi event tickers name files unsanitised)."""
    from grokteam import book as B
    with _fake_quantgen() as (state, _repo, scratch):
        data = scratch / "grokteam"
        keep = B.DATA
        try:
            B.DATA = data
            for folder, linked in (("a", "e.json.gz"), ("b", "e.json.gz.tmp"), ("c", "MANIFEST.jsonl")):
                victim = _hard_linked(state, data / folder / linked)
                _refused(lambda f=folder: B.write_cached(data / f / "e.json.gz", {"a": 1}), "hard link")
                assert victim.read_bytes() == VICTIM, folder
                assert sorted(p.name for p in (data / folder).iterdir()) == [linked], folder   # nothing written
            _refused(lambda: B.write_cached(data / "kalshi" / ".." / ".." / "escape.json.gz", {"a": 1}), "outside")
            assert not (scratch / "escape.json.gz").exists() and not (scratch / "escape.json.gz.tmp").exists()
            B.write_cached(data / "d" / "ok.json.gz", {"a": 1})                    # the normal case still writes
            B._MANIFESTS.clear()
            assert B.read_cached(data / "d" / "ok.json.gz") == {"a": 1}
        finally:
            B.DATA = keep
            B._MANIFESTS.clear()
