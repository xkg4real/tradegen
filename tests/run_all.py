"""Run the acceptance suite and write a machine-readable result file.

Two fixes over the previous runner, both of which made it unusable on this
machine:

  * stdout is forced to UTF-8. The default on Windows Korean locale is cp949,
    which cannot encode the em dash or the Hangul in provider labels, so the
    runner died with `UnicodeEncodeError` before printing its summary.
  * the output directory is created before writing. The old runner wrote to
    `qa/acceptance_results.json` without `mkdir`, so a clean checkout ended in
    `FileNotFoundError` after every test had already run.

v2 (M0): a third status. A test that raises `tests.notrun.NotRun(reason)` is
recorded as NOT_RUN with its reason, counted separately and never affects the
exit code. `--milestone M<k>` runs the exit set of a milestone (every test whose
`test_ids` has a registry row with `runs_from <= M<k>` and whose module, when
it is a `macro_m<j>_*` module, was built at M<j> <= M<k>: a clause deferred to
M<j> is asserted by an M<j> module, so it never blocks an earlier milestone,
spec 9.0a/9.0b); `--suite <prefix>` runs one suite.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from tests.acceptance import tests as cockpit_tests        # noqa: E402
from tests.engine_acceptance import tests as engine_tests  # noqa: E402
from tests.flet_api_guard import tests as ui_tests          # noqa: E402
from tests.quant_acceptance import tests as quant_tests     # noqa: E402
from tests.ficc_acceptance import tests as ficc_tests       # noqa: E402
from tests.expansion_acceptance import tests as expansion_tests   # noqa: E402
from tests.macro_acceptance import tests as macro_tests     # noqa: E402
from tests.paper_live_acceptance import tests as paper_tests     # noqa: E402
from grokteam.selfcheck import tests as grokteam_tests             # noqa: E402
from tests.compliance_acceptance import tests as compliance_tests  # noqa: E402
from tests.odds_acceptance import tests as odds_tests              # noqa: E402
from tests.notrun import NotRun                             # noqa: E402

REGISTRY = ROOT / "tests" / "macro_registry.csv"
OUT = ROOT / "qa" / "acceptance_results.json"


def tests():
    return ([(f"cockpit/{n}", f) for n, f in cockpit_tests()] +
            [(f"engine/{n}", f) for n, f in engine_tests()] +
            [(f"ui/{n}", f) for n, f in ui_tests()] +
            [(f"quant/{n}", f) for n, f in quant_tests()] +
            [(f"ficc/{n}", f) for n, f in ficc_tests()] +
            [(f"expansion/{n}", f) for n, f in expansion_tests()] +
            [(f"macro/{n}", f) for n, f in macro_tests()] +
            [(f"paper/{n}", f) for n, f in paper_tests()] +
            [(f"grokteam/{n}", f) for n, f in grokteam_tests()] +
            [(f"compliance/{n}", f) for n, f in compliance_tests()] +
            [(f"odds/{n}", f) for n, f in odds_tests()])


def runs_from() -> dict[str, int]:
    with REGISTRY.open(encoding="utf-8", newline="") as fh:
        return {row["test_id"]: int(row["runs_from"][1:]) for row in csv.DictReader(fh)}


def module_milestone(name: str) -> int:
    """`macro/macro_m2_risk/test_x` -> 2; 0 for any other module (no floor)."""
    stem = name.split("/")[1] if name.count("/") == 2 else ""
    tag = stem.split("_")[1] if stem.startswith("macro_m") else ""
    return int(tag[1:]) if tag[1:].isdigit() else 0


def select(entries, *, milestone: str | None = None, suite: str | None = None):
    if suite:
        entries = [(n, f) for n, f in entries if n.split("/", 1)[0] == suite]
    if milestone:
        k, table = int(milestone[1:]), runs_from()
        entries = [(n, f) for n, f in entries
                   if any(table.get(t, 99) <= k for t in getattr(f, "test_ids", ())) and module_milestone(n) <= k]
    return entries


def run(entries) -> list[dict]:
    results = []
    for name, fn in entries:
        started = time.perf_counter()
        row = {"test": name, "status": "PASS", "seconds": 0.0, "detail": ""}
        try:
            fn()
        except NotRun as exc:
            row["status"], row["reason"] = "NOT_RUN", exc.reason
        except Exception as exc:
            row["status"], row["detail"] = "FAIL", f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        row["seconds"] = round(time.perf_counter() - started, 4)
        results.append(row)
        print(f"{row['status']} {name} {row['detail'] or row.get('reason', '')}".rstrip())
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--milestone", help="run the exit set of M<k> via tests/macro_registry.csv")
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or odds")
    args = parser.parse_args(argv)
    if args.milestone and not re.fullmatch(r"M(10|[0-9])", args.milestone):
        parser.error("--milestone takes M0..M10")
    results = run(select(tests(), milestone=args.milestone, suite=args.suite))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    not_run = sum(r["status"] == "NOT_RUN" for r in results)
    print(f"\n{passed}/{len(results)} passed, {failed} failed, {not_run} not run; {OUT}")
    return 0 if results and failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
