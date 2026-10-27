### Task 7: Data-layer A0 minors: the KIS token target is checked before the POST, the ficc memory cache after the check

**Files:**
- Modify: `data/krx/kis_client.py` (anchor: `KISClient.token`, the cache-miss branch inside `with _TOKEN_LOCK:`,
  kis_client.py:172-176; LF)
- Modify: `core/ficc/data.py` (anchor: `_cache_put`, data.py:269-279; LF)
- Modify: `tests/compliance_isolation.py` (anchors: the end of `test_kis_token_writer_refuses_a_hard_linked_target`,
  :247-258, where the new test goes in before `test_opendart_cache_writer_refuses_a_hard_linked_target`; and the
  `try` block of `test_ficc_cache_writer_refuses_a_hard_linked_target`, :295-306; LF)
- Test: `tests/compliance_isolation.py`

**Interfaces:**
- Consumes:
  - `core.isolation.checked_target(path, what: str = "path", *, within=None) -> Path`. It raises `RuntimeError`
    (`"<what> <path> is a hard link; writing it would change another file (A0)"` for a second name) and creates
    nothing (core/isolation.py:40-56).
  - `data.krx.kis_client`:
    - the module globals `_TOKEN_PATH` (kis_client.py:53), `_once` (the one-attempt `requests` module, :39) and
      `_TOKEN_LOCK` (:54);
    - `KISError(RuntimeError)` (:45);
    - `KISClient.token() -> str` (:169-196), `KISClient._cached_token()` (:146-155) and
      `KISClient._store_token(token, expires_in)` (:157-167, keeps its own `checked_target` at :158).
  - `config.kis_credentials() -> tuple[str, str]` (config.py:180). kis_client calls it through the module attribute,
    so patching `config.kis_credentials` reaches it: the T-RO-02 recorder of tests/macro_m1_pit.py:1067-1072.
  - `core.ficc.data._MEM: dict[str, tuple[float, Rows]]` (data.py:217) and `core.ficc.data._cache_put(key, rows)`
    (:269-279).
  - In `tests/compliance_isolation.py`: `VICTIM` (:23), `_fake_quantgen()` (:26-39), `_hard_linked(state, link)`
    (:58-64), `_refused(call, needle)` (:67-74) and `import config` (:18).
- Produces:
  - one new test, `tests/compliance_isolation.py::test_kis_token_is_refused_before_the_token_request`;
  - no new product name. `KISClient.token()` now raises the `checked_target` refusal on a cache miss before it reads
    a credential or builds the token request. Its one production caller, `_get`, still reads the credentials at
    kis_client.py:207 before it calls `token()` at :209; that read sends nothing, so no issuance is burnt.
    `_cache_put` now raises that refusal before it sets `_MEM[key]`.

**Plan decisions used:** R8, R12; R13 and the DRIFT RULE (Global Constraints).

What this task changes, and what it leaves alone:
- **The D14 closure.** Neither product file is in the closure: `core/__init__.py`, `core/isolation.py`,
  `core/compliance/*.py`, `core/odds/*.py` and their in-repo imports (owner.py:773). So the code hash does not move
  and no table changes.
- **The execution carry list.** R8 takes "KIS token burnt on refusal" off it (ledger:239). The executor writes that
  in the execution ledger when this task lands.
- **R12.** `_store_token` keeps its own `checked_target` (kis_client.py:158), which still guards a direct call. The
  existing `test_kis_token_writer_refuses_a_hard_linked_target` keeps proving it. The new check in `token()` is one
  line.
- **The tests' controls.** Each new refusal assertion has a positive control in the same test, so it cannot pass
  vacuously after the fix. The KIS test then points `_TOKEN_PATH` at a clean target and wants the recorder to see
  the credential read and the POST. The ficc test then puts a clean key and wants it in `_MEM`.
- **Other suites.** No test outside this file calls the real `KISClient.token()` except cockpit/test_21
  (tests/acceptance.py:318). It reaches `token()` through `KRXGateway.daily` -> `KISClient.daily` -> `_get`
  (data/krx/gateway.py:90-98, kis_client.py:209), and only when KIS keys are set.
  - There, a clean target passes the new check. A refusal is the same `RuntimeError` that `_store_token` raised
    before, and the gateway's `except Exception` (gateway.py:97) still turns it into a failed answer.
  - The cockpit's read-only scans (test_08, test_09) run directly in Step 4. Step 4 does not add `--suite cockpit`:
    with KIS keys set, test_21 sends real KIS requests, the token POST to `/oauth2/tokenP` on a cache miss
    (kis_client.py:181) and the read-only daily-chart quotation GET (`KISClient.daily`, kis_client.py:273-281).
    The rest of the cockpit suite, test_21 included, runs once, in Task 8 Step 2's full run. There, when KIS keys
    are set, test_21 makes that read-only KIS quotation call, as every earlier full run did; the controller accepts
    this, and no key check is added. This task makes no KIS call.
  - engine test_89 replaces `client.token` (tests/engine_acceptance.py:1376).
  - T-RO-02 refuses in `_get` before any token (tests/macro_m1_pit.py:1073).
  - `_cache_put` changes only when `checked_target` refuses, and then it raises as before.
  - The engine, macro, expansion, ficc and quant suites still run in Step 4, because they load these modules.
- **Left as it is.**
  - `_cached_token()` still reads the token file before the check. A0 checks writes ("every writer ... checks its
    final target", spec 4 "Isolation residual"). A link present at the process's first `state_root()` scan of that
    root is refused by the link scan (kis_client.py:53 calls `config.state_root()` at import; the scan is memoised
    per root, refusals included, `scan_links` at core/isolation.py:99-102). A link created after that scan is read
    by `_cached_token()` unchecked, and a valid token in it is used. That is a read and no write, so it is outside
    A0 and R8. The controller rules that this token read path is left as is (a stated limit in the plan header's
    "Spec" list).
  - The `core/ficc/data.py` module docstring ("Cache failures are ignored, never raised") predates A0. It is not
    rewritten here.
- **Drift.** No earlier task of this plan touches these three files. Under the DRIFT RULE, re-read each file before
  its Edit anyway.

- [ ] **Step 1: Write the failing tests**

  Re-read `tests/compliance_isolation.py`. Then make two Edit-tool replacements. Keep LF.

  Edit 1. The anchor is the end of `test_kis_token_writer_refuses_a_hard_linked_target` and the `def` line of
  `test_opendart_cache_writer_refuses_a_hard_linked_target` (tests/compliance_isolation.py:255-261). The new test
  goes in between them. Old text (exact):

```python
            _refused(lambda: object.__new__(kis_client.KISClient)._store_token("t", 60.0), "hard link")
        finally:
            kis_client._TOKEN_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_opendart_cache_writer_refuses_a_hard_linked_target():
```

  New text:

```python
            _refused(lambda: object.__new__(kis_client.KISClient)._store_token("t", 60.0), "hard link")
        finally:
            kis_client._TOKEN_PATH = keep
        assert victim.read_bytes() == VICTIM


def test_kis_token_is_refused_before_the_token_request():
    """R8 (ledger:81): on a cache miss token() checks the cache target before it reads a credential or sends the
    token request, so a refused target burns no token issuance (KIS rate-limits issuance hard). _store_token keeps
    its own check for a direct call (R12, the test above)."""
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
```

  The control's `KISError` is a `RuntimeError`, so `_refused` catches it. The clean target's directory does not
  exist, so `_cached_token()` misses and `checked_target` passes it without creating anything.

  Edit 2. The anchor is the `try` block of `test_ficc_cache_writer_refuses_a_hard_linked_target`
  (tests/compliance_isolation.py:302-305). The `finally` that pops the key stays, and pops the control key too. The
  control writes `A0_PROBE_2.json` into the fake scratch directory, which `_fake_quantgen()` removes. Old text
  (exact):

```python
            _refused(lambda: D._cache_put("A0_PROBE_1", [("2026-10-22", 1.0)]), "hard link")
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
            D._MEM.pop("A0_PROBE_1", None)
```

  New text:

```python
            _refused(lambda: D._cache_put("A0_PROBE_1", [("2026-10-22", 1.0)]), "hard link")
            assert "A0_PROBE_1" not in D._MEM, "a refused key was cached in memory"
            D._cache_put("A0_PROBE_2", [("2026-10-22", 1.0)])                # control: a clean key is cached
            assert "A0_PROBE_2" in D._MEM, "a clean key was not cached in memory"
        finally:
            config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir = keep
            D._MEM.pop("A0_PROBE_1", None)
            D._MEM.pop("A0_PROBE_2", None)
```

- [ ] **Step 2: Run to verify it fails**

  First run the overlap check with the PowerShell tool. It must print nothing; if it prints a process, wait and run
  it again.

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then, from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_isolation/
```

  Expected: two tracebacks, these three lines among the 17 result lines, and then the summary. Exit code 1.

```text
FAIL compliance_isolation/test_ficc_cache_writer_refuses_a_hard_linked_target AssertionError: a refused key was cached in memory
FAIL compliance_isolation/test_kis_token_is_refused_before_the_token_request AssertionError: token request failed: ConnectionError
NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode

14/17 passed, 2 failed, 1 not run
```

  Why each one fails today:
  - **The KIS token test.** `token()` reads the credentials and calls `_once.post` before any check. The recorder
    raises, and `token()` turns that into `KISError("token request failed: ConnectionError")` (kis_client.py:187-188).
    The first `_refused` wants "hard link", so it raises an AssertionError with that message. The control is not
    reached.
  - **The ficc test.** `_cache_put` sets `_MEM["A0_PROBE_1"]` at data.py:273, before the refusal at :274. The control
    is not reached.

  If the KIS line instead names `HermeticViolation`, the `_once` patch did not take effect: re-check Edit 1.

- [ ] **Step 3: Implement**

  Edit 3: `data/krx/kis_client.py` (LF). Re-read the file. The anchor is the cache-miss branch inside
  `with _TOKEN_LOCK:` in `KISClient.token` (kis_client.py:172-176). The new line goes after `return cached` and
  before `config.kis_credentials()`. The same `app_key, app_secret = config.kis_credentials()` line also occurs in
  `_get` (:207), so the old text includes the lines above it to stay unique. `_store_token` is not touched. Old text
  (exact):

```python
        with _TOKEN_LOCK:
            cached = self._cached_token()
            if cached:
                return cached
            app_key, app_secret = config.kis_credentials()
```

  New text:

```python
        with _TOKEN_LOCK:
            cached = self._cached_token()
            if cached:
                return cached
            checked_target(_TOKEN_PATH, "KIS token cache")      # A0: refuse before the POST burns an issuance (R8)
            app_key, app_secret = config.kis_credentials()
```

  `checked_target` is already imported (kis_client.py:36).

  Edit 4: `core/ficc/data.py` (LF). Re-read the file. The anchor is the body of `_cache_put` (data.py:272-274).
  `_MEM[key] = (now, rows)` and the `checked_target` line swap places, and the moved line gets the R8 comment.
  `_cache_get`'s own `_MEM[key] = (ts, rows)` (:264) is not touched. Old text (exact):

```python
    now = time.time()
    _MEM[key] = (now, rows)
    target = checked_target(config.ficc_cache_dir() / f"{key}.json", "FICC cache")   # A0: a refusal propagates
```

  New text:

```python
    now = time.time()
    target = checked_target(config.ficc_cache_dir() / f"{key}.json", "FICC cache")   # A0: a refusal propagates
    _MEM[key] = (now, rows)   # after the check: a refused key is never served from memory (R8)
```

  Then check the line endings. Expected: each line reads `i/lf    w/lf    attr/-text`.

```bash
git ls-files --eol data/krx/kis_client.py core/ficc/data.py tests/compliance_isolation.py
```

- [ ] **Step 4: Run to verify it passes**

  Run the overlap check of Step 2 before EACH command below that starts Python. All run from the repo root in Git
  Bash. In Git Bash the overlap check can also be a prefix. The PowerShell script is in single quotes, so Bash leaves
  `$_` alone:
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.

  Overlap check, then the module:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_isolation/
```

  Expected:
  - 16 `PASS compliance_isolation/test_...` lines;
  - `NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode`;
  - then `16/17 passed, 0 failed, 1 not run`, and exit code 0.
  - With Developer Mode on, `17/17 passed, 0 failed, 0 not run`.

  Overlap check, then the repo-wide read-only guards: T-RO-01 on code with docstrings and comments stripped
  (`_code_only`, tests/macro_m0_harness.py:78), and cockpit test_08 and test_09 on raw text. `runtime_py()` scans
  core, data, ui, main.py and config.py. This calls the three test functions directly, does not start
  `tests/run_all.py`, and writes nothing. The raw-text checks over every file of `core/` (tests/compliance_guards.py)
  run in the compliance suite below.

```bash
.venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as ro; from tests.acceptance import test_08_no_broker_order_path as t8, test_09_no_account_credentials_requested as t9; ro(); t8(); t9(); print('guards ok')"
```

  Expected: `guards ok` (exit code 0).

  Then the compliance suite, and the five suites below that load these modules, one at a time. The cockpit suite also
  loads kis_client; it is left to Task 8 Step 2's full run, because its test_21 calls KIS when keys are set ("Other
  suites" above). Before each line, run the overlap check.
  Each line restores the tracked, CRLF `qa/acceptance_results.json` after its run.
  - Engine: test_89 stubs `client.token`; test_81 checks `kis._once`.
  - Macro: T-RO-02 re-runs kis_client from its source, and macro_m0_rules reads its state paths.
  - Expansion: fake KIS transports.
  - Ficc and quant: the FICC cache.

  If a line prints `exit 1` and no test lines, the prefixed overlap check found a running `run_all.py`: wait, then
  run that line again.

  Timeouts. Every `--suite` run imports all ten suites before it runs its own. In the 2026-10-24 record the tests
  took 64 s for compliance, 56 s for expansion, 56 s for quant and 416 s (about 7 minutes) for macro, against the
  Bash tool's 120 s default. So give each `--suite` line `timeout: 300000`, and the macro line `timeout: 600000` or
  start it with `run_in_background` and wait for its notification. Never start a second run in the meantime.

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite engine; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite macro; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite expansion; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite ficc; echo "exit $?"; git checkout -- qa/acceptance_results.json
.venv/Scripts/python.exe tests/run_all.py --suite quant; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: every run reports `0 failed` and prints `exit 0`. Each summary line ends with
  `; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`. The counts come from Tasks 1-7 for
  compliance and from README.md:831-836 for the other suites; when `0 failed` holds, the run's own numbers win:
  - compliance: `325/327 passed, 0 failed, 2 not run`. The 2 not run are the two REFDATA symlink tests,
    `compliance_isolation/test_symlinks_are_refused` and `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`.
  - engine: `92/92 passed, 0 failed, 0 not run`
  - macro: `419/540 passed, 0 failed, 121 not run`
  - expansion: `19/19 passed, 0 failed, 0 not run`
  - ficc: `56/56 passed, 0 failed, 0 not run`
  - quant: `53/53 passed, 0 failed, 0 not run`

  After the last line:

```bash
git status --short
```

  Expected exactly:

```text
 M core/ficc/data.py
 M data/krx/kis_client.py
 M tests/compliance_isolation.py
```

  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add data/krx/kis_client.py core/ficc/data.py tests/compliance_isolation.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical. All three files are LF. Expected:

```text
 core/ficc/data.py             |  2 +-
 data/krx/kis_client.py        |  1 +
 tests/compliance_isolation.py | 36 ++++++++++++++++++++++++++++++++++++
 3 files changed, 38 insertions(+), 1 deletion(-)
```

  Then:

```bash
git commit -m "fix(isolation): check the KIS token and ficc cache targets before side effects" -m "Task 7 (R8, R12): token() refuses a bad cache target before it reads a credential or sends the token POST; _cache_put sets _MEM only after checked_target." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  Then add a line to the execution ledger (`docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`,
  which the executor keeps): "KIS token burnt on refusal" (ledger:239) is closed by Task 7 (R8) and leaves the
  execution carry list.
