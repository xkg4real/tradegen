# Rules for every implementer and fixer (TRADEGEN, public repo xkg4real/tradegen)

These are hard rules. Breaking one is worse than not finishing.

## Shell and tests
- Use the Bash tool (Git Bash). Work only inside the worktree you are given. Never touch another checkout,
  never `git stash`, `git reset --hard`, `git switch`/`checkout` another branch, or rebase.
- Define once per shell (SCRATCH and the runs dir are given in your dispatch):
  ```bash
  SCRATCH=<local-path>
  PY="$HOME/OneDrive/Desktop/TRADEGEN_PR9/.venv/Scripts/python.exe"
  export TRADEGEN_RUNS_DIR="<runs dir from your dispatch>"
  focus() { "$PY" -X utf8 -c "import importlib,sys; from tests.run_all import run; s=importlib.import_module('tests.'+sys.argv[1]+'_acceptance'); rows=run([(n,f) for n,f in s.tests() if sys.argv[2] in n]); sys.exit(0 if rows and not any(r['status']=='FAIL' for r in rows) else 1)" "$@"; }
  ```
- The venv is read-only: never `pip install`, never create or modify a venv.
- Never modify the owner folders `~/OneDrive/Desktop/TRADEGEN` or `~/OneDrive/Desktop/TRADEGEN_PR9` (only *run* the
  interpreter at `TRADEGEN_PR9/.venv/Scripts/python.exe`). Never edit anything under `~/OneDrive/Desktop/QUANTGEN`.
- Tests are offline. No real exchange or network call, never read `.env`, never write the real `~/.tradegen` or
  `~/.nextgen`. Never run `tools/signer/sign.py`, never arm, never place an order, never enter or read keys.
- Do NOT run the full suite (`python -m tests.run_all`); the controller runs it. Run the focused tests the brief names.
  If you ever run anything that rewrites `qa/acceptance_results.json`, `git restore qa/acceptance_results.json`.

## Line endings (byte-exact repo, `.gitattributes` is `* -text`)
- NEVER use `sed -i`, `perl -i`, or any shell rewrite of a tracked file: it converts CRLF to LF silently.
  Edit with the Edit tool (it preserves endings) or the Write tool for new files, or Python `read_bytes`/`write_bytes`.
- Python and YAML files are LF, except `execution_launch/study.py` (CRLF). New files: LF unless the brief says otherwise.
- Before every commit: `diff <(git diff --stat) <(git diff --stat --ignore-cr-at-eol) && echo LF-OK` must print LF-OK.
  Also check staged: `diff <(git diff --cached --stat) <(git diff --cached --stat --ignore-cr-at-eol) && echo LF-OK`.

## Commits
- `git add` only the files your brief names (never `git add -A` / `.`; the `.superpowers/` folder and plan docs are
  never committed).
- Commit messages: use the message the brief gives; every message ends with the line
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never push. Never open a PR. Never merge.

## Content
- The repo is public: no secrets, keys, amounts, account data, personal data, or local paths containing a user name
  (e.g. `C:\Users\<name>`) in code, tests, docs or commit messages.
- Frozen/pinned files stay byte-identical. Never regenerate a pin in `tests/execution_guards.py` or
  `tests/renewal_boundaries.py`; if a pin test fails, stop and report.
- Follow the brief's code exactly unless it does not fit the code on disk; if it does not fit, or a stated expected
  test result differs from what you see, STOP and report (status BLOCKED or DONE_WITH_CONCERNS) with the exact output.
  Do not redesign silently.

## You do not dispatch subagents
Do all work yourself. Never spawn a helper or a reviewer.
