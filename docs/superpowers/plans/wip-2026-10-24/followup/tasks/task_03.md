### Task 3: The KR-KIS-KRX-DERIV reason names broker approval (`core/compliance/kr_rules.yaml`)

**Files:**
- Modify: `core/compliance/kr_rules.yaml` (anchor: the `reason:` key of the row `- id: KR-KIS-KRX-DERIV`, line 204
  today, the row starts at :199; LF; a shipped table, outside the D14 code closure)
- Modify: `tests/compliance_tables.py` (anchor: `test_shipped_d16_rows_need_live_evidence`, :951-965 today, in the
  `_t5_` block (the compliance plan's Task 5); LF)
- Test: `tests/compliance_tables.py`

**Interfaces:**
- Consumes: the existing helpers of the `_t5_` block (the compliance plan's Task 5) of `tests/compliance_tables.py`:
  `_t5_shipped()` (:854, returns `(table, imap, venues)` parsed from the shipped files) and `_t5_row(table, row_id)`
  (:861); `rules.Row.reason` (`str`), `rules.Row.requires_live` (`tuple[str, ...]`). Task 2's loader (R2) must accept
  the edited table; it does (dry run below).
- Produces: no new name. The shipped rules table's bytes change on one line: 59,408 -> 59,425 bytes, sha256
  `127a3c913fdc7c0e07a19f8daae2c0548c782770c74b5b6a6578ec9551bd3b79` ->
  `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`.

**Plan decisions used:** R3; R13 and the drift rule (Global Constraints).

What this task does and why:
- The ledger (ledger:118, "KR-KIS-KRX-DERIV reason text does not mention broker approval (cosmetic)") recorded that
  the row's `requires.live` (:203) lists `broker_approval` while its reason (:204) names only deposits, courses and
  mock trading. R3 makes the reason start "KOSPI200 futures and options need broker approval, a broker deposit of
  KRW 10M (stage 1) ...". Only this line changes; the row's match, requires, treatment, sources and dates stay.
- The table sha changes. No approval exists yet (`core/compliance/owner_pubkey.pem` is absent, owner act 1 is not
  done), so nothing is re-signed; the owner's first rules approval (owner act 3) is of these edited bytes. Nothing in
  the repo pins the old sha or the old reason text (2026-10-24, `git grep -I -n <term> -- . ':!docs'`: `127a3c91`
  finds nothing; `KOSPI200 futures and options need` and `broker deposit of KRW` each find only kr_rules.yaml:204
  itself; the bare term `KOSPI200 futures` also hits about 27 files of prose, research notes and data, none of which
  quotes the reason); every test that reads the shipped table hashes it at run time.
- Not touched here (each is out of scope, Appendix A section 11): the 2027-01-01 `affected_by` item (ledger:114), any
  deposit network (the OKX USDT/USDC networks stay an owner act, ledger:112, :120), and the compliance plan's embedded
  copy of the old row (docs/superpowers/plans/2026-10-23-compliance-gate.md:5109, a historical record).
- Dry run (2026-10-24, a sandbox copy of the table and of the test file): exactly line 204 differs; the edited table
  parses VALID with 47 rows under today's `rules.parse_rules` and under the Task 2 (R2) sandbox copy of rules.py; the
  new assertion fails on today's table with the old reason as its message and passes on the edited one; the file
  stays LF, UTF-8 and under 256 KB (`test_shipped_files_are_utf8_lf_and_small`, tables:897-902).
- Drift: Task 2 edits `tests/compliance_tables.py` before this task (new tests after :300 and the `_T5_PINNED` block
  after :981), so the line numbers of `test_shipped_d16_rows_need_live_evidence` move down; find it by name. Neither
  Task 2 nor any earlier plan changes kr_rules.yaml. Re-read each file before its Edit; if the quoted old text differs
  only because an earlier plan changed it, apply the same change to the current text and write one ledger line.

- [ ] **Step 1: Write the failing test**

  In `tests/compliance_tables.py`, function `test_shipped_d16_rows_need_live_evidence`, add one assertion right after
  the `krx_deriv` lines (Edit tool; the file is LF).

  Old text (exact, two lines):

```python
    krx_deriv = _t5_row(table, "KR-KIS-KRX-DERIV")          # D16: broker eligibility is live evidence, not an owner snapshot
    assert "broker_approval" in krx_deriv.requires_live and "broker_eligibility" not in krx_deriv.requires_owner
```

  New text:

```python
    krx_deriv = _t5_row(table, "KR-KIS-KRX-DERIV")          # D16: broker eligibility is live evidence, not an owner snapshot
    assert "broker_approval" in krx_deriv.requires_live and "broker_eligibility" not in krx_deriv.requires_owner
    assert "broker approval" in krx_deriv.reason, krx_deriv.reason   # the reason names what requires.live asks (ledger:118)
```

  (The new line is Appendix A section 5's line exactly, 124 characters; the first old line is 125 characters today and
  stays as it is. The assertion checks presence only; the Step 3 size and sha check pins the exact new reason.)

- [ ] **Step 2: Run to verify it fails**

  Overlap check with the PowerShell tool (it must print nothing; otherwise wait and re-run):

```powershell
Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine
```

  Then from the repo root in Git Bash:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected: a traceback, the line

```
FAIL compliance_tables/test_shipped_d16_rows_need_live_evidence AssertionError: KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)
```

  and, ending, `63/65 passed, 1 failed, 1 not run` (exit code 1). The not-run test is the REFDATA symlink test; with
  Windows Developer Mode on it passes and the line reads `64/65 passed, 1 failed, 0 not run`. Any other failure means
  Task 2 did not land as written: stop and rule.

- [ ] **Step 3: Implement**

  In `core/compliance/kr_rules.yaml`, row `- id: KR-KIS-KRX-DERIV`, replace its `reason:` line (Edit tool; the file
  is LF; the line is one physical line, do not wrap it).

  Old text (exact, one line):

```
    reason: "KOSPI200 futures and options need a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```

  New text (exact, one line):

```
    reason: "KOSPI200 futures and options need broker approval, a broker deposit of KRW 10M (stage 1) or KRW 20M (stage 2: option writing, VKOSPI futures), at least 1h of course and 3h of mock trading; this row asks for the stage-2 deposit for every intent; refused until live broker evidence exists (D16)"
```

  Then check the bytes (read-only, from the repo root in Git Bash; no overlap check needed, it runs no test):

```bash
git diff --stat -- core/compliance/kr_rules.yaml
git diff --stat --ignore-cr-at-eol -- core/compliance/kr_rules.yaml
git ls-files --eol core/compliance/kr_rules.yaml
.venv/Scripts/python.exe -I -c "import hashlib, pathlib; b = pathlib.Path('core/compliance/kr_rules.yaml').read_bytes(); print(len(b), hashlib.sha256(b).hexdigest(), b.count(b'\r'))"
```

  Expected: each of the two `git diff --stat` commands prints exactly (git's leading space included)

```
 core/compliance/kr_rules.yaml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

  then `i/lf    w/lf    attr/-text            	core/compliance/kr_rules.yaml`; and
  `59425 74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd 0`. Another size or sha means the line
  was mistyped (or an earlier plan changed the table): fix the line, or stop and rule under the drift rule.

- [ ] **Step 4: Run to verify it passes**

  Overlap check (PowerShell tool, as in Step 2; it must print nothing), then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_tables/
```

  Expected, ending: `64/65 passed, 0 failed, 1 not run` (exit code 0; `65/65 passed, 0 failed, 0 not run` with
  Developer Mode on).

  Overlap check again, then the compliance suite (it parses the shipped table in compliance_gate, compliance_store,
  compliance_cli and compliance_signer too), then restore the results file (give this line `timeout: 300000`; never
  start a second run meanwhile):

```bash
.venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected, ending:

```
322/324 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  (324 rows, as after Task 2; the two not-run rows are the REFDATA symlink tests). Then
  `git status --short` lists only ` M core/compliance/kr_rules.yaml` and ` M tests/compliance_tables.py`, plus, if
  the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

```bash
git add core/compliance/kr_rules.yaml tests/compliance_tables.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical (both files are LF), each exactly (git's column padding included):

```
 core/compliance/kr_rules.yaml | 2 +-
 tests/compliance_tables.py    | 1 +
 2 files changed, 2 insertions(+), 1 deletion(-)
```

  Then:

```bash
git commit -m "fix(tables): KR-KIS-KRX-DERIV reason names broker approval" -m "R3 (ledger:118): the reason now names the broker approval its requires.live lists; table sha 74894f05..., no approval exists yet, owner act 3 approves these bytes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
