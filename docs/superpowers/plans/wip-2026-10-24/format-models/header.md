# TRADEGEN Compliance Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the compliance half of the approved spec. It covers:
- the rules, instrument and venue tables;
- the pure `decide()` kernel with permits and plan screening;
- the signed owner log;
- the approved-version store and signed code hash;
- `load_context()`;
- the `--check` CLI and alerts;
- the owner-kept signer;
- the isolation residual (A0).

No order is placed and no money moves.

**Architecture:** Rules are data. Three YAML tables are loaded by a strict loader into frozen dataclasses. A pure
kernel (`core/compliance/gate.py`) decides each intent from a sealed `Context`, which only `owner.load_context()`
builds. `load_context()`:
- hashes the code on disk;
- verifies the Ed25519-signed owner log;
- loads the latest owner-approved table bytes from an immutable store under `~/.tradegen/compliance/`.

The signer is a standalone file that the owner keeps outside the repo. The odds engine is a separate plan, written
after this one lands.

**Tech Stack:**
- Python 3.13.14 in `.venv`;
- PyYAML 6.0.3, with a strict `SafeLoader` subclass;
- `cryptography` 49.0.0 for Ed25519, scrypt and AES-256-GCM. It is installed by Task 10 after the owner approves
  the download;
- the stdlib `zoneinfo` with `tzdata` 2026.2;
- the repo's own runner `tests/run_all.py`. There is no pytest.

**Spec:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2, `b5603f5`). The
owner approved it on 2026-10-23. GPT's final check runs after 2026-10-30 14:40. Any valid finding becomes rev 3.3
and must be folded in before the task it affects runs; see Task 16.

> This is research and software design, not legal, tax or investment advice. Neither TRADEGEN nor its author is a
> licensed advisor.

## Global Constraints

Every task's requirements include this section. Values are copied from the spec and the verified repo map.

**Hard rules from the owner's brief**
- Never arm the system, place a live order, or enter credentials or keys.
- Never edit anything under `C:\Users\whydi\OneDrive\Desktop\QUANTGEN`. Never write under `~/.nextgen`. Never run
  anything while QUANTGEN's test suite runs.
- Never delete `grokteam/PREREG_book.json` or `grokteam/out/frozen_book/`.

**Signing and the owner log**
- Claude never runs `tools/signer/sign.py` with a real key. Claude never asks for or handles the owner's passphrase.
- Claude never writes to the real `~/.tradegen/compliance/owner.jsonl`.
- Tests build owner logs only inside a temporary `TRADEGEN_HOME` and sign them with a fixed test key.

**Python and test runs**
- Interpreter: `.venv/Scripts/python.exe`, which is Python 3.13.14. Never `pip install` into the global Python
  (QUANTGEN's frozen studies pin it).
- A test is a zero-argument `test_*` function that raises on failure. There is no pytest.
- Overlap check: run it before every test command. It must print nothing; otherwise wait. QUANTGEN's Store Python
  runs as `python3.13.exe` with no `python.exe` beside it, so only a `python*` name filter sees it.
  - PowerShell tool:
    `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  - Git Bash prefix. The PowerShell script is in single quotes, so Bash leaves `$_` alone:
    `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- One test or module: `.venv/Scripts/python.exe -m tests.compliance_acceptance <module>/<test>`. This does not write
  `qa/acceptance_results.json`.
- One suite: `.venv/Scripts/python.exe tests/run_all.py --suite <name>`. This rewrites the tracked
  `qa/acceptance_results.json`. Restore it with `git checkout -- qa/acceptance_results.json` afterwards. Only Task 16
  commits that file.

**Files, line endings and commits**
- New files are UTF-8 with no BOM and LF endings.
- These files are CRLF and must stay CRLF: `tests/run_all.py`, `README.md`, `config.py`, `requirements.txt`,
  `pyproject.toml`, `core/quant/history.py`, `grokteam/book.py` and `grokteam/selfcheck.py`.
- `constraints.txt` is mixed: line 1 is LF and the rest are CRLF. Task 10 edits it with Python bytes I/O, because
  the Edit tool turns its line 1 into CRLF.
- Edit every other existing file only with the Edit tool, never `sed -i`.
- Before every commit, `git diff --cached --stat` must equal `git diff --cached --stat --ignore-cr-at-eol`.
- Work on branch `compliance-gate`, which Task 1 creates. Commit once per task. End each commit message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Guards on `core/**/*.py`.** They scan raw text, so docstrings and comments count.
- Never write upper-case `CANO` (so never `CANONICAL`), `KIS_ACCOUNT` or `ACNT_PRDT_CD`.
- Never write `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U` or `VTTC0802U`.
- Never write `private_key` or `seed_phrase` in any form. Use `load_pem_public_key` and `Ed25519PublicKey`, and name
  keys `signing_key`.
- Never call, and never define, a function named `transfer`, `withdraw` or `deposit_address`.
- Never use `.post`, `.put`, `.delete`, `.patch` or `.request` in `core/compliance`.
- No dynamic import in `core/compliance`: no star import, `__import__`, `import_module`, `exec` or `eval`, and no
  `importlib.util`, `importlib.machinery`, `runpy`, `pkgutil` or `zipimport`. Core code probes for `cryptography`
  with a lazy `import` inside `try`/`except ImportError`; `importlib.util.find_spec` is for tests only.
- Never import `core.engine.orders` in any form. Never import `core.quant.forward_sim`, `core.quant.refusal`,
  `core.ficc.context_log`, `core.ficc.macro`, `core.ficc.flows_log` or `core.skills.macro_daily`.
- `core/compliance/*.py` may import only the stdlib, `yaml`, `cryptography` (lazily, inside functions),
  `core.isolation` and `core.compliance.*`.
- No wall-clock call anywhere in `core/compliance/`, except in the CLI `main()` of `rules.py` and `alerts.py`.

**Writes and encodings**
- Every file the compliance code writes goes through `core.isolation.checked_target()` immediately before it is
  opened, temp and lock files included.
- Every text open passes `encoding="utf-8"`. CLI JSON output uses `ensure_ascii=True`.

**Values copied verbatim from the spec**
- Asia/Seoul is the decision date zone. OKX auto-off is `2026-12-03`.
- `known_changes`: `["2026-12-03", "2027-01-01", "2027-02-18"]`. Review cadence is monthly, at most 31 days.
  Crypto, transfer and OKX rows are due `2026-11-22`.
- The table file cap is 256 KB.
- scrypt parameters: n = 2^17, r = 8, p = 1, a 16-byte salt and a 12-byte nonce, with AES-256-GCM and the header as
  AAD.
- A passphrase needs at least 20 characters or 5 words. P39 narrows this to 20 non-blank characters, or 5
  different alphabetic words of 3 or more letters.
- The alert email goes only to `sapientia@korea.ac.kr`.
- Exit codes are 0, 1, 2, 3 and 4 (spec 5.4).
- Dependency: `cryptography==49.0.0` in `requirements.txt`, `pyproject.toml` and `constraints.txt`.

## Decisions this plan makes where the spec is silent or would break a guard

The tasks cite these as P1 to P39. Each one either fills a gap the spec leaves open or chooses a reading of the spec.
None of them loosens anything. GPT's 2026-10-30 check should read this list together with the spec.

Companion documents:
- **Appendix A** below is the interface contract the tasks were drafted against, with the drafting amendments
  folded in. Where a task's text and Appendix A differ, the task wins.
- **`docs/superpowers/plans/2026-10-23-compliance-gate-repo-map.md`** holds the 230 repo facts the plan rests on,
  each with file:line evidence, as mapped on 2026-10-23.

{{PLAN_DECISIONS}}

## File map

{{FILE_MAP}}

## Owner gates during execution

1. **Task 10.** Approve the `cryptography` 49.0.0 download from PyPI into `.venv` only.
2. **Task 16.** Approve the 09:00 KST scheduled alert task. It may send alerts only to you: an iOS push and an email
   to `sapientia@korea.ac.kr`. Approving it is the standing authority D5 describes, and it covers self-addressed
   alerts only.
3. **After this plan: owner acts 1 to 6 in spec section 11.** They are:
   - set up the signer;
   - sign the code hash;
   - approve the tables;
   - sign the calendars;
   - set the limits and the cap;
   - record your age and your withdrawal addresses.

   Until you do them, the shipped system is in a safe default: every new-exposure intent is BLOCK and `--check`
   exits 3.

---
