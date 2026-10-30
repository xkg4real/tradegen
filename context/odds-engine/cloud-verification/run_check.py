"""Odds plan Task 19 run check: the full-run record against the previous full run (the record of main at the branch
point, the follow-up's run), and README.md against the record. Reads files and git only, imports no repo code; run it
from the repo root."""
from __future__ import annotations

import ast
import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RECORD = Path("qa/acceptance_results.json")
LEDGER = "docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md"
MODULES = ("odds_guards", "odds_plan", "odds_costs", "odds_models", "odds_garch", "odds_simulate", "odds_locks",
           "odds_bold", "odds_report", "odds_pipeline", "odds_columns", "odds_bars", "odds_inputs", "odds_replay",
           "odds_cli")                                                            # CONTRACT 3.1
DRAFTS = dict(zip(MODULES, (18, 25, 23, 19, 17, 18, 14, 12, 41, 13, 14, 25, 12, 24, 12)))  # Tasks 1, 5-18: 287
TARGETS = dict(zip(MODULES, (5, 2, 2, 6, 25, 18, 12, 12, 12, 20, 30, 4, 12, 20, 20)))      # CONTRACT 3.4, seconds
ADDED = {f"compliance/compliance_{m}/{t}" for m, names in (
    ("tables", ("test_venue_odds_keys_parse_to_exact_tuples", "test_venue_odds_lookups_fall_back_and_answer_none",
                "test_venue_odds_lookups_are_pure_tuple_lookups", "test_check_extras_lives_in_the_parser",
                "test_shipped_venue_odds_values_are_the_sourced_ones")),              # Task 2 (4), Task 3 (1)
    ("store", ("test_signed_home_helpers_are_the_public_fixtures", "test_full_home_signs_the_odds_keywords",
               "test_calendar_in_force_is_the_sha_of_the_intact_signed_copy",
               "test_calendar_in_force_is_none_without_an_ok_owner_log",
               "test_calendar_in_force_counts_only_approvals_stamped_by_now",
               "test_calendar_in_force_refuses_a_naive_or_out_of_range_now",
               "test_calendar_line_maps_the_shared_calendar_approval")),            # Task 4 (7)
    ("gate", ("test_grey_rows_names_the_in_force_grey_rows_of_the_leg",
              "test_grey_rows_is_empty_when_nothing_can_be_looked_up"))) for t in names}  # Task 4 (2)
ODDS_ROW = ("| odds | `tests/odds_acceptance.py` over `tests/odds_*.py` | The odds engine, offline with every price "
            "feed faked: the single-leg plan whitelist and the named refusals in their fixed order, the cost ledger "
            "with the per-fill tick floor (the KRX stock sell tax inside it), floor-protected and stop-based stakes "
            "with lot rounding, the no-edge two-point bootstrap and GARCH-t with their pilot checks and corruption "
            "tests, the path engine (open and close checks, limit-down locks, the daily loss, rule dates, delisting "
            "stress, the OKX cap per entry), the ceiling, the KRX structural maximum and exact bold play, the "
            "HIDDEN_EDGE and CEILING_BREACH bug checks, the S_C3 replay against its pinned card with lower-bound "
            "Kelly, the report's sentence catalogue, outward number formats and language guard, the unsigned bar "
            "loader and its checked cache, the signed calendar, one seed per comparison, the CLI, and the odds guards "
            "(the import allowlist, no clock and no file I/O in the signed core) |")
KEYISH = re.compile(r"(?i)key|credential|token|\.env")
NEW = json.loads(RECORD.read_text(encoding="utf-8"))
BASE = subprocess.run(["git", "merge-base", "f3bedd3d24c3faa3b2881e8e515613e5b13a9c59", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
OLD = json.loads(subprocess.run(["git", "show", f"{BASE}:qa/acceptance_results.json"],
                                capture_output=True, check=True).stdout.decode("utf-8"))
RUN_DATE = datetime.date.fromtimestamp(RECORD.stat().st_mtime).isoformat()
record: list[str] = []          # problems that stop the task
readme: list[str] = []          # README.md lines that do not match the record
notes: list[str] = []           # G3-1 and G3-2 lines for the ledger
rulings: list[str] = []         # G3-2: a module over twice its target is the controller's ruling


def totals(rows: list[dict]) -> str:
    n = collections.Counter(r["status"] for r in rows)
    return f"{n['PASS']}/{len(rows)} passed, {n['FAIL']} failed, {n['NOT_RUN']} not run"


def cell(group: str) -> str:
    n = collections.Counter(r["status"] for r in NEW if r["test"].split("/", 1)[0] == group)
    return f"{n['PASS']} PASS / {n['NOT_RUN']} NOT_RUN" if n["NOT_RUN"] else f"{n['PASS']} PASS"


def safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ._:/,()=+-]", " ", text)[:100].strip()


old = {r["test"]: r for r in OLD}
new = {r["test"]: r for r in NEW}
record += [f"FAIL row {r['test']}" for r in NEW if r["status"] == "FAIL"]
if len(new) != len(NEW):
    record.append("duplicate test ids in the new record")
record += [f"unknown status {r['test']}" for r in NEW if r["status"] not in ("PASS", "FAIL", "NOT_RUN")]
record += [f"a row of the previous run is missing: {t}" for t in old if t not in new]
added = {t for t in new if t not in old and not t.startswith("odds/")}
changes = []
for t in new:
    if t in old and new[t]["status"] != old[t]["status"]:
        before, after, why = old[t]["status"], new[t]["status"], safe(new[t].get("reason", ""))
        changes.append(f"  - {t}: {before} -> {after}" + (f", {why}" if why else ""))
        platform_case = (sys.platform == "linux"
                         and t == "compliance/compliance_signer/test_stdin_terminal_check_follows_getconsolemode"
                         and new[t].get("reason") == "REFDATA: GetConsoleMode needs Windows")
        if platform_case:
            notes.append("  - Cloud platform ruling: GetConsoleMode requires Windows; one NOT_RUN retained, not PASS")
        if after == "NOT_RUN" and not KEYISH.search(why) and not platform_case:
            record.append(f"{t} turned NOT_RUN for a reason that names no key: stop and rule")
tree = ast.parse(Path("tests/odds_acceptance.py").read_bytes())
listed = next((ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(getattr(x, "id", "") == "MODULES" for x in n.targets)), None)
if listed != MODULES:
    record.append(f"tests/odds_acceptance.MODULES is not CONTRACT 3.1's list: {listed}")
defined = set()
for m in MODULES:
    path = Path("tests") / f"{m}.py"
    if not path.is_file():
        record.append(f"tests/{m}.py is missing, so the suite skips it")
        continue
    defined |= {f"odds/{m}/{n}" for n in re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M)}
odds = [r for r in NEW if r["test"].startswith("odds/")]
if not odds:
    record.append("the record holds no odds rows")
elif defined != {r["test"] for r in odds}:
    record.append(f"odds rows differ from the defined tests: {sorted(defined ^ {r['test'] for r in odds})[:5]}")
record += [f"odds row not PASS: {r['test']} {r['status']} {safe(r.get('reason', ''))}" for r in odds
           if r["status"] != "PASS"]
seconds = round(sum(r["seconds"] for r in odds), 1)
over = []
for m in MODULES if odds else ():
    rows = [r for r in odds if r["test"].startswith(f"odds/{m}/")]
    spent = round(sum(r["seconds"] for r in rows), 1)
    if len(rows) != DRAFTS[m]:
        notes.append(f"  - G3-1: {m} has {len(rows)} tests where the drafts expect {DRAFTS[m]}")
    if spent > TARGETS[m]:
        over.append(f"{m} {spent} s > {TARGETS[m]} s")
        notes.append(f"  - G3-2: {m} took {spent} s in the full run, over its {TARGETS[m]} s target")
    if spent > 2 * TARGETS[m]:
        rulings.append(f"RULING: {m} took {spent} s, over twice its {TARGETS[m]} s target (G3-2)")
if odds and added != ADDED:
    notes.append(f"  - G3-1: rows added outside odds differ from the drafts (Tasks 2 to 4): "
                 f"extra {sorted(added - ADDED)}, absent {sorted(ADDED - added)}")
groups = list(dict.fromkeys(r["test"].split("/", 1)[0] for r in NEW))
raw = Path("README.md").read_bytes()
if raw.count(b"\n") != raw.count(b"\r\n"):
    readme.append("a line of README.md does not end in CRLF")
lines = raw.decode("utf-8").split("\r\n")
for group in groups:
    found = [i for i, line in enumerate(lines) if line.startswith(f"| {group} | ")]
    if len(found) != 1 or lines[found[0]].rsplit("|", 2)[-2].strip() != cell(group):
        readme.append(f"the {group} row is not one row ending | {cell(group)} |")
total = re.compile(r"\| \*\*Total\*\* \| `tests/run_all\.py` \| \| " + re.escape(totals(NEW))
                   + r" \((\d{4}-\d{2}-\d{2}), " + re.escape("TRADEGEN `.venv`" if NEW == OLD else "Cloud Python 3.13 venv") + r"\) \|")
at = [i for i, line in enumerate(lines) if total.fullmatch(line)]
if len(at) != 1 or (NEW != OLD and total.fullmatch(lines[at[0]]).group(1) != RUN_DATE):
    readme.append(f"the Total row is not | **Total** | ... | {totals(NEW)} ({RUN_DATE}, Cloud Python 3.13 venv) |")
if "odds" in groups:
    row = [i for i, line in enumerate(lines) if line == f"{ODDS_ROW} {cell('odds')} |"]
    comp = [i for i, line in enumerate(lines) if line.startswith("| compliance | ")]
    if not (row and comp and at and comp[0] + 1 == row[0] == at[0] - 1):
        readme.append("the odds row of Task 19 is not between the compliance row and the Total row")
comp_delta = sum(t.startswith("compliance/") for t in new) - sum(t.startswith("compliance/") for t in old)
line = (f"- Task 19: full run (KEYLESS) {totals(NEW)} on {RUN_DATE}; previous full run {totals(OLD)}; "
        f"odds {cell('odds')} in {seconds} s; compliance {cell('compliance')} ({comp_delta:+d} rows); "
        f"status changes {len(changes)}")
print(f"previous full run (main at {BASE[:7]}):", totals(OLD))
print("this run:", totals(NEW), "on", RUN_DATE)
verdict = ("as the drafts expect" if added == ADDED else "(see G3-1)") if odds else ""
print(f"rows added outside odds: {len(added)} {verdict}".rstrip())
print("status changes:", len(changes))
if changes:
    print(*changes, sep="\n")
print("odds:", len(odds), "rows in", seconds, "s; modules over their CONTRACT 3.4 target:", over or "none")
print("README cells:", "; ".join(f"{g}={cell(g)}" for g in groups))
print(f"README Total: {totals(NEW)} ({RUN_DATE}, Cloud Python 3.13 venv)")
for extra in (*notes, *rulings):
    print(extra.strip())
if not record:                  # the Runs lines exist only for a record that stands
    print("APPEND: printf '%s\\n' " + " ".join(f'"{x}"' for x in [line, *changes, *notes]) + f" >> {LEDGER}")
print("record: OK" if not record else "record: FAIL: " + "; ".join(record))
print("README: matches the record" if not readme else "README: FAIL: " + "; ".join(readme))
sys.exit(1 if record or readme else 0)
