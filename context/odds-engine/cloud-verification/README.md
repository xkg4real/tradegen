# Cloud verification used for the odds handoff

These scripts preserve the actual Cloud adaptations. They assume the code checkout is `/workspace/tradegen`, the scratch directory is `/workspace/tradegen-session`, and Python 3.13 dependencies are installed in `/workspace/.venvs/tradegen`. Run them from the code checkout. Copy the scripts to scratch before use; the smoke writes its own plan beside its script.

Before any repository tests, activate the existing venv, set `TRADEGEN_HOME` to an isolated directory under `/workspace/tradegen-session/`, and set every name in `run-task-19.py`'s 19-item `keys` list to the literal `<unset>`. Do not load real key values. Run only one repository test process at a time.

- `python -I <scratch>/run_check.py` is read-only: it compares the QA record to the true branch point f3bedd3, checks every odds test ID and timing, and verifies README. Its one named Linux exception is the Windows GetConsoleMode test; no other new skip is allowed.
- `python <scratch>/run-task-19.py final` runs the full acceptance suite, writes raw results outside the code repo, checks the real default homes are unchanged, restores the prior QA record on failure, and preserves CRLF on success. It needs sandbox loopback/socket permission for two existing tests. External data calls stay blocked by test fixtures; no production data API is used.
- `python -I <scratch>/smoke.py` invokes the CLI through runpy in a fresh temporary home with all network/seam paths refused. The expected no-owner-key result is exit 2, STATE_UNUSABLE, provenance, no seam call, and no state entry. This does not verify the owner's PC or signatures.

These are reproducibility helpers, not a background quota monitor. Weekly GPT usage could not be read; CURRENT.md records unknown/unavailable and a 95% handoff threshold.
