"""Council backlog as a read-only display registry (`data/backlog_registry.json`; QUANTGEN_MACRO_BACKLOG.md v2.0).

Six collections, frozen as of 2026-10-02: status_board (46), council_queue (22), settling_test (11),
owner_decision (6), data_acq (31), data_quality (22). `acting` is false on every row and no acting module
reads this file. Owner-decision rows carry the rules-store key only; the value in force is
`owner_decisions.D<n>` of the macro store (backlog L6, L371), never a literal here. The backlog priority
scale (P1-P3) and the council scale (P0-P2) are separate fields of separate collections, never merged.
`load_registry` refuses (ValueError) a count, id pattern, enum, reference or `acting` that does not hold.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "backlog_registry.json"
COUNTS = {"status_board": 46, "council_queue": 22, "settling_test": 11, "owner_decision": 6,
          "data_acq": 31, "data_quality": 22}
ID_PATTERNS = {"status_board": r"BL-[SCOUG]\d\d", "council_queue": r"CQ-\d\d", "settling_test": r"ST-\d\d",
               "owner_decision": r"D[1-6]", "data_acq": r"BL-D\d\d", "data_quality": r"DQ-\d\d"}
CLASSES = {"status_board": ("S", "C", "O", "U", "G"),
           "council_queue": ("VALID-SHADOW", "CONTESTED", "CONTEXT-ONLY", "OWNER-DECISION")}
STATUSES = ("OPEN", "MOVED", "RESOLVED", "CLOSED", "RETIRED", "OWNER-DECISION", "RECORD_ONLY")
SPEC_REF = re.compile(r"R-\d\d|M\d{1,2}|§.*")


def load_registry(path: Path | str = REGISTRY_PATH) -> dict[str, list[dict]]:
    """collection -> rows, validated; raises ValueError naming every problem."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    cols = doc["collections"]
    errs = [f"collections {sorted(cols)} != {sorted(COUNTS)}"] if set(cols) != set(COUNTS) else []
    st_ids = {r["item_id"] for r in cols.get("settling_test", ())}
    bld_ids = {r["item_id"] for r in cols.get("data_acq", ())}
    for name, want in COUNTS.items():
        got = cols.get(name, [])
        if len(got) != want:
            errs.append(f"{name}: {len(got)} rows, expected {want}")
        if len({r["item_id"] for r in got}) != len(got):
            errs.append(f"{name}: duplicate item_id")
        for r in got:
            rid = r.get("item_id", "?")
            if not re.fullmatch(ID_PATTERNS[name], rid) or r.get("collection") != name:
                errs.append(f"{name}: bad item_id/collection {rid!r}")
            if r.get("acting") is not False:
                errs.append(f"{rid}: acting must be false")
            if name in CLASSES and r.get("class") not in CLASSES[name]:
                errs.append(f"{rid}: class {r.get('class')!r} not in {CLASSES[name]}")
            if name == "status_board" and r.get("status") not in STATUSES:
                errs.append(f"{rid}: status {r.get('status')!r} not in {STATUSES}")
            if name == "owner_decision" and ("value" in r or not r.get("rules_key")):
                errs.append(f"{rid}: an owner-decision row carries its rules_key only, never a value")
            errs += [f"{rid}: settling test {s} unknown" for s in r.get("settling_test_ids", ()) if s not in st_ids]
            errs += [f"{rid}: blocking data {b} is not a data_acq row" for b in r.get("blocking_data", ())
                     if b not in bld_ids]
            errs += [f"{rid}: spec ref {s!r}" for s in r.get("spec_refs", ()) if not SPEC_REF.fullmatch(s)]
    if errs:
        raise ValueError(f"{Path(path).name} refused: " + " | ".join(errs))
    return cols
