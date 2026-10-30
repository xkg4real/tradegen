"""Odds plan Task 19: the read-only isolated Cloud smoke (Q45). Runs `python -m core.oddsdata.run --plan <plan>` in this
process through runpy, the way `-m` runs it, with every network touchpoint refused (the macro suite's hermetic
guard) and the four bars seams replaced by stubs that record a call and raise; lists every folder and file under
the isolated TRADEGEN_HOME before and after. It writes only its own plan file, next to this script. Run it from the repo root."""
from __future__ import annotations

import contextlib
import datetime
import io
import json
import os
import runpy
import sys
import tempfile
import warnings
import zoneinfo
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path.cwd()
if not (REPO / "core" / "oddsdata" / "run.py").is_file():
    raise SystemExit("STOP: run this from the repo root")
sys.path.insert(0, str(REPO))
SMOKE_ROOT = Path(tempfile.mkdtemp(prefix="tradegen-odds-smoke-")) / "state"
os.environ["TRADEGEN_HOME"] = str(SMOKE_ROOT)
PLAN = Path(__file__).resolve().parent / "smoke_plan.json"
LEDGER = "docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md"
SEAMS = ("_kis_daily", "_upbit_daily", "_binance_daily", "_yf_download")


def listing() -> tuple:
    """(relative path, size, mtime_ns) of every folder and file under the isolated TRADEGEN_HOME, as
    tests/compliance_acceptance._real_listing lists them: the home itself is `.`, a folder `<path>/` with 0, 0."""
    rows = [(".", 0, 0)] if SMOKE_ROOT.exists() else []
    for dirpath, dirs, files in os.walk(SMOKE_ROOT):
        here = Path(dirpath)
        rows += [((here / n).relative_to(SMOKE_ROOT).as_posix() + "/", 0, 0) for n in dirs]
        for name in files:
            st = (here / name).stat()
            rows.append(((here / name).relative_to(SMOKE_ROOT).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


today = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Seoul")).date().isoformat()   # Q25: the plan starts today
leg = {"venue": "upbit", "symbol": "BTC", "model": "bootstrap", "bracket": None, "sizing": "floor_safe",
       "edge_source": "none", "assumed_p": None}
PLAN.write_text(json.dumps({"schema": "tradegen.odds_plan/1", "plans": [{
    "name": "smoke", "track": "compounding", "stake_krw": 42_000, "target_krw": 46_200, "fx_krw_per_usd": 1_400.0,
    "start": today, "horizon_days": 1, "leg": leg, "fraction": {"kind": "fixed", "value": 1.0}}]}), encoding="utf-8")
if (REPO / "core/compliance/owner_pubkey.pem").exists():
    raise SystemExit("STOP: unexpected owner key in the Cloud checkout")
before = listing()                                       # before any repo module is imported

import config                                            # noqa: E402  (runs load_dotenv, as hermetic() does)
from core.odds import report                             # noqa: E402
from core.oddsdata import bars                           # noqa: E402
from tests.macro_acceptance import hermetic              # noqa: E402

if config.state_root() != SMOKE_ROOT:                          # a TRADEGEN_HOME line in .env moves the CLI's home
    raise SystemExit("STOP: the state root is not the isolated TRADEGEN_HOME")
WHY = report.say("refused.head", why=report.say("why.STATE_UNUSABLE"))   # Task 12's catalogue, as Task 18's test
calls: list[str] = []


def stub(name: str):
    def seam(*_a, **_k):
        calls.append(name)
        raise RuntimeError(f"bars.{name} was called by the smoke")
    return seam


saved, argv = {n: getattr(bars, n) for n in SEAMS}, sys.argv
out, err, code, caught = io.StringIO(), io.StringIO(), None, []
try:
    for n in SEAMS:
        setattr(bars, n, stub(n))
    sys.argv = ["core.oddsdata.run", "--plan", str(PLAN)]
    with (hermetic(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err),
          warnings.catch_warnings(record=True) as caught):
        warnings.simplefilter("always")          # recorded, never printed, as in tests/odds_cli.py
        try:
            runpy.run_module("core.oddsdata.run", run_name="__main__", alter_sys=True)
        except SystemExit as exc:
            code = exc.code
finally:
    sys.argv = argv
    for n, fn in saved.items():
        setattr(bars, n, fn)
after = listing()
changed = sorted({row[0] for row in set(before) ^ set(after)})     # relative paths only (metadata)
problems = [f"exit {code}, not 2"] if code != 2 else []
problems += [f"stderr {err.getvalue()[:300]!r}"] if err.getvalue() else []
problems += [] if WHY in out.getvalue().splitlines() else ["no STATE_UNUSABLE card"]
problems += [f"seams called {calls}"] if calls else []
problems += [f"the isolated TRADEGEN_HOME changed: {len(changed)} path(s), listed above"] if changed else []
print(out.getvalue(), end="")
print("exit", code)
print("seams called:", calls)
print("warnings recorded:", len(caught))
if changed:
    print("the isolated TRADEGEN_HOME CHANGED (paths under it; a folder ends in /):", *changed, sep="\n  ")
else:
    print(f"the isolated TRADEGEN_HOME unchanged: {len(after)} entries")
if not problems:
    line = (f"- Task 19: isolated Cloud smoke (Q45; KEYLESS, hermetic, seams stubbed) on {today}: exit 2 STATE_UNUSABLE, "
            f"no seam called, the isolated TRADEGEN_HOME unchanged ({len(after)} entries)")
    print("APPEND: printf '%s\\n' " + f'"{line}"' + f" >> {LEDGER}")
print("OK" if not problems else "FAIL: " + "; ".join(problems))
sys.exit(1 if problems else 0)
