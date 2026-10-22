"""Tech-fund research record (R3 round-3 synthesis, G-01..G-77) as shipped, read-only data. Display only.

`data/techfund/` holds verbatim copies of the bundle's R3 frames (weights, go/no-go register, nodes, edges,
golden values, pair share, focus by theme) and the integration briefs' tables as JSON (DNB-TF-01..17,
BL-TF-01..20, OQ-01..15, XS-01..22, CA-01..38), each listed in `MANIFEST.json` with sha256 and provenance.
Every read checks the file's sha256 against the manifest and raises `TechfundDataError` on a mismatch or a
missing file (fail closed: never a partial table).

Coordinator rulings 3.7-3.9: Council v2.0 governs where the two programmes differ; OQ and XS rows are
proposals pending owner confirmation; the 0-3 weights are display scores (macro sizing is IV_m x 1/K_m);
golden values are reference constants, never recomputed here. No v2 book, rule or acting module reads this.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path

TF_DIR = Path(__file__).resolve().parents[1] / "data" / "techfund"
MANIFEST = "MANIFEST.json"

# Register class from the decision prefix (first match wins); consistent with the R3 sub-table of the id:
# "GOVERNANCE option (owner)" sits in 10.4 (owner decisions), "SPEC BOOK ONLY" (G-13) in 10.1 (governance).
CLASS_PREFIX = (("BUILD", "BUILD"), ("INVARIANT", "INVARIANT"), ("GOVERNANCE option", "OWNER DECISION"),
                ("GOVERNANCE", "GOVERNANCE"), ("KEEP + GOVERNANCE", "GOVERNANCE"), ("SPEC BOOK ONLY", "GOVERNANCE"),
                ("FORWARD-SIM", "FORWARD-SIM"), ("BACKLOG", "BACKLOG"), ("OWNER DECISION", "OWNER DECISION"),
                ("CONTEXT", "CONTEXT"), ("DROP", "DROP"), ("DO-NOT-BUILD", "DROP"))
# R3 section 10 sub-tables by id range (R3:792; QA:168 counts 29 / 5 / 20 / 6 / 17)
SECTIONS = ((29, "10.1"), (34, "10.2"), (54, "10.3"), (60, "10.4"), (77, "10.5"))


class TechfundDataError(RuntimeError):
    """A shipped tech-fund file is missing, unlisted or differs from MANIFEST.json."""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def manifest(root: Path = TF_DIR) -> dict:
    try:
        return json.loads((Path(root) / MANIFEST).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise TechfundDataError(f"{MANIFEST} unreadable: {exc}") from exc


def _text(name: str, root: Path = TF_DIR) -> str:
    entry = manifest(root)["files"].get(name)
    if entry is None:
        raise TechfundDataError(f"{name} is not listed in {MANIFEST}")
    try:
        b = (Path(root) / name).read_bytes()
    except OSError as exc:
        raise TechfundDataError(f"{name} missing: {exc}") from exc
    if _sha(b) != entry["sha256"]:
        raise TechfundDataError(f"{name} sha256 {_sha(b)} != manifest {entry['sha256']}")
    return b.decode("utf-8-sig")


def rows(name: str, root: Path = TF_DIR) -> list[dict]:
    """Every row of a shipped CSV as text (csv.DictReader; cells hold commas and quotes; nothing coerced)."""
    return list(csv.DictReader(io.StringIO(_text(name, root), newline="")))


def _items(name: str, root: Path) -> list[dict]:
    return json.loads(_text(name, root))["items"]


def parse_final(final: str) -> tuple[int | None, str]:
    """(w, flag) of a weight-table `final` cell: the leading digit 0-3 (None for the 5 rows without a scalar)
    and "*" for one-panel cells (W4). The cell is always displayed whole; w / 3 is an XS-21 display proposal."""
    m = re.match(r"^(\d)(\*?)", final)
    return (int(m.group(1)), m.group(2)) if m else (None, "")


def weights(root: Path = TF_DIR) -> list[dict]:
    """r3_weights_final.csv (50 rows, R3 section 9.1-9.4) plus parsed `w` and `flag`."""
    out = rows("r3_weights_final.csv", root)
    for r in out:
        r["w"], r["flag"] = parse_final(r["final"])
    return out


def weights_other_markets(root: Path = TF_DIR) -> list[dict]:
    """r3_weights_other_markets.csv (6 rows; CONTEXT only, G-59): priors without a QUANTGEN data path."""
    return rows("r3_weights_other_markets.csv", root)


def register_class(decision: str) -> str:
    for prefix, cls in CLASS_PREFIX:
        if decision.startswith(prefix):
            return cls
    raise TechfundDataError(f"register decision {decision!r} has no class prefix")


def register_section(gid: str) -> str:
    n = int(gid[2:])
    return next(s for top, s in SECTIONS if n <= top)


def register(root: Path = TF_DIR) -> list[dict]:
    """r3_go_nogo.csv (G-01..G-77) plus `class` (decision prefix) and `section` (R3 sub-table by id)."""
    out = rows("r3_go_nogo.csv", root)
    for r in out:
        r["class"], r["section"] = register_class(r["decision"]), register_section(r["id"])
    return out


def nodes(root: Path = TF_DIR) -> list[dict]:
    return rows("R3_TF_nodes.csv", root)


def edges(root: Path = TF_DIR) -> list[dict]:
    return rows("R3_TF_edges.csv", root)


def goldens(root: Path = TF_DIR) -> list[dict]:
    """r3_golden_values.csv (GV-001..GV-523): reference constants; `line` is 1-based counting the header."""
    return rows("r3_golden_values.csv", root)


def dnb_tf_items(root: Path = TF_DIR) -> list[dict]:
    return _items("dnb_tf_items.json", root)


def backlog_tf_items(root: Path = TF_DIR) -> list[dict]:
    return _items("bl_tf_items.json", root)


def open_questions(root: Path = TF_DIR) -> list[dict]:
    return _items("oq_items.json", root)


def cross_spec_amendments(root: Path = TF_DIR) -> list[dict]:
    """XS-01..22 with `status` ADOPTED | CONFLICT | OPEN | PARTIAL against Council v2.0 (Council governs)."""
    return _items("xs_items.json", root)


def corrected_anchors(root: Path = TF_DIR) -> list[dict]:
    return _items("ca_items.json", root)


def verify_manifest(root: Path = TF_DIR) -> list[str]:
    """Every problem with the shipped set (empty = intact): missing, unlisted or changed files, row/col counts."""
    root = Path(root)
    try:
        listed = manifest(root)["files"]
    except TechfundDataError as exc:
        return [str(exc)]
    problems = [f"{p.name}: not listed in {MANIFEST}" for p in sorted(root.iterdir())
                if p.is_file() and p.name != MANIFEST and p.name not in listed]
    for name, entry in listed.items():
        path = root / name
        if not path.is_file():
            problems.append(f"{name}: missing")
            continue
        b = path.read_bytes()
        if _sha(b) != entry["sha256"] or len(b) != entry["bytes"]:
            problems.append(f"{name}: sha256/bytes differ from {MANIFEST}")
        elif name.endswith(".csv"):
            table = list(csv.reader(io.StringIO(b.decode("utf-8-sig"), newline="")))
            if (len(table) - 1, len(table[0])) != (entry["rows"], entry["cols"]):
                problems.append(f"{name}: {len(table) - 1} x {len(table[0])} != {entry['rows']} x {entry['cols']}")
    return problems
