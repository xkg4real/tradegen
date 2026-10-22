"""Gate package v2.0.0: definitions manifest, freeze, verify, state (section 8.1.3 step 3, P11, R-21 rule 9 attempt
log contract, T-CARD-02; TASK-M7-16, M7-17).

`definitions_md5` is the md5 of a manifest listing (a) the canonical JSON of every `gate.*` block except
`gate.package` itself, (b) the harness source files (CRLF normalised to LF, brief F-31), (c) the md5 of every
acceptance fixture, (d) the seeds, (e) each family ledger's hash and the section 9.5 seed files, (f) the data
cut-off, the D6 rule and the recorded council answers. `freeze` refuses, with a list of reasons, until the
acceptance test has passed on the frozen reference data, the repository has an external timestamped anchor
(ruling 3.1: never `UNVERSIONED`) and the reference fixtures are present; it never fabricates a package. After a
freeze a change is a new package version re-run on every card (`new_package_version`); nothing in the package
changes after a card result has been seen (`verify_package` refuses on any mismatch).

reading: council answers not yet recorded are `null` in the manifest (never invented as "stands as written").
The acceptance attempt log is written by `core.quant.cardp.gate_acceptance_test` (the same hash chain as
`cards.chain_append`); this module only reads and chain-verifies it and the acceptance report.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

from core.ficc import macro_artifacts as MA
from core.ficc.macro_schema import canonical_json, md5_hex
from core.quant.cards import CardRefused, PackageNotFrozen, _write, chain_verify, read_chain
from core.rules import governance as G
from core.rules.macro_rules import MacroStore, load_store, validate_store_doc

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "macro"
Clock = Callable[[], datetime]
# (b) the source files of every R-21..R-24 / R-34 harness function plus the primitives they import (conservative
# coverage: an edit to any of them is a package change, L4820; brief spec_M7_cards A, spec_M7_gate_package B6)
HARNESS_SOURCES = ("core/quant/gate_stats.py", "core/quant/gate_ledger.py", "core/quant/cardp.py", "core/quant/cards.py",
                   "core/quant/card_lines.py", "core/quant/instruments.py", "core/quant/costed.py", "core/quant/validate.py",
                   "core/quant/strategies.py", "core/quant/gjr.py", "docs/macro_overlay_study.py")
# (c) the fixtures the acceptance test reads (names from tests/fixtures/macro/ACQUISITION.csv: F01, F02, F12, F22, F29)
REFERENCE_FIXTURES = ("krx_kospi_official_close_1997-01-03_2026-10-02.csv", "ecos_bok_call_rate_1997_2026-10.csv",
                      "french_daily_mktrf_rf_1926-07_2026-08.csv", "QX_EX1_qf3_trial_corr_diff.csv",
                      "ledger_seed_R-03.csv", "ledger_seed_R-06.csv", "ledger_seed_R-28.csv", "ledger_seed_R-31.csv")
COUNCIL_QUESTIONS = ("Q5_per_card_placebo_excess", "sharpe_neutral_timing_fragility", "primary_oos_line_of_future_cards")
ATTEMPT_ROW = ("attempt_no", "package_version", "outcome", "prev_row_md5")
REASON_ACCEPTANCE = "NOT_FROZEN: acceptance test not passed"
REASON_ANCHOR = "NOT_FROZEN: anchor UNVERSIONED (owner must place the repository under git)"
REASON_FIXTURES = "NOT_FROZEN: reference fixtures absent"


class PackageMismatch(CardRefused):
    """The re-hashed manifest differs from gate.package.definitions_md5 (T-CARD-02): nothing runs."""


class FreezeRefused(CardRefused):
    pass


@dataclass(frozen=True)
class FreezeResult:
    version: str
    definitions_md5: str
    acceptance_report_md5: str
    frozen_utc: str
    anchor: str
    manifest_path: Path


def _file_md5(path: Path) -> str | None:
    """md5 of a source file with CRLF normalised to LF (OneDrive / autocrlf never changes a hash, brief F-31)."""
    if not path.is_file():
        return None
    return md5_hex(path.read_bytes().replace(b"\r\n", b"\n"))


def build_manifest(store: MacroStore, *, root: Path = REPO_ROOT, sources: Sequence[str] = HARNESS_SOURCES,
                   fixture_dir: Path = FIXTURE_DIR, fixtures: Sequence[str] = REFERENCE_FIXTURES,
                   ledger_hashes: Mapping[str, str] | None = None, council_answers: Mapping[str, str | None] | None = None) -> dict:
    """The definitions manifest (L4820 (a)-(f)). Absent files hash to null and are listed under `absent`."""
    gate = {k: v for k, v in store.get("gate").items() if k != "package"}
    repro = store.get("reproducibility")
    acc = store.get("gate.acceptance_test")
    answers = {q: None for q in COUNCIL_QUESTIONS}
    answers.update(council_answers or {})
    m = {
        "gate_blocks": {k: canonical_json(v) for k, v in sorted(gate.items())},
        "harness_sources": {s: _file_md5(Path(root) / s) for s in sources},
        "fixtures": {f: _file_md5(Path(fixture_dir) / f) for f in fixtures},
        "seeds": {"seed_study": repro["seed_study"], "seed_research_bootstrap": repro["seed_research_bootstrap"],
                  "placebo": acc["placebo"]["seed"], "bootstrap": store.get("gate.stats.bootstrap.seed"),
                  "pc1_prime": store.get("gate.card_p_v2.pc1_prime.seed"), "emax": store.get("gate.step3.emax.seed"),
                  "rng": repro["determinism"]["rng"], "blas_threads": repro["determinism"]["blas_threads"]},
        "ledgers": dict(sorted((ledger_hashes or {}).items())),
        "data_cutoff": store.get("gate.evaluation.data_cutoff"),
        "d6_rule": store.get("gate.acceptance_test.cdar_guard.calibration"),
        "council_answers": answers,
        "md5_rules": {"header_md5": "header fields minus header_md5", "results_md5": "result fields minus results_md5 and the volatile fields",
                      "draft_md5": "header fields minus VOLATILE_AT_COMMIT", "source_md5": "bytes with CRLF normalised to LF"},
    }
    m["absent"] = sorted([f"source:{k}" for k, v in m["harness_sources"].items() if v is None] +
                         [f"fixture:{k}" for k, v in m["fixtures"].items() if v is None])
    return m


def definitions_md5(store: MacroStore, **kw) -> tuple[str, dict]:
    """(md5 of the canonical manifest, the manifest)."""
    m = build_manifest(store, **kw)
    return md5_hex(canonical_json(m)), m


def attempts_path(macro_dir) -> Path:
    return Path(macro_dir) / "gate" / "acceptance_runs.jsonl"


def report_path(macro_dir) -> Path:
    return Path(macro_dir) / "gate" / "acceptance_report.json"


def manifest_path(macro_dir) -> Path:
    return Path(macro_dir) / "gate" / "definitions_manifest.json"


def attempts(macro_dir) -> list[dict]:
    """Every attempt row of the hash-chained gate/acceptance_runs.jsonl (empty when no attempt was ever made)."""
    return read_chain(attempts_path(macro_dir), ATTEMPT_ROW)


def failures(macro_dir) -> int:
    """Failed attempts across all 2.x versions, never reset (R2-C3)."""
    return sum(1 for r in attempts(macro_dir) if r.get("outcome") == "fail")


def acceptance_passed(macro_dir) -> tuple[bool, str]:
    """True when the last attempt row says pass and the report file carries the same outcome; the detail says why not."""
    p = attempts_path(macro_dir)
    rows = attempts(macro_dir)
    if not rows:
        return False, f"no attempt in {p} (the acceptance test has never run; it needs the frozen reference data)"
    if failures(macro_dir) >= 2:
        return False, "two failed attempts across 2.x: no card can be evaluated under v2 (R2-C3)"
    last = rows[-1]
    if last.get("outcome") != "pass":
        return False, f"last attempt {last.get('attempt_no')} outcome {last.get('outcome')!r}"
    rp = report_path(macro_dir)
    if not rp.is_file():
        return False, f"acceptance_report.json absent at {rp}"
    try:
        rep = json.loads(rp.read_text(encoding="utf-8"))
    except ValueError as exc:
        return False, f"acceptance_report.json unreadable: {exc}"
    if rep.get("outcome") != "pass" or rep.get("attempt_no") != last.get("attempt_no"):
        return False, "acceptance_report.json does not match the last attempt"
    return True, f"attempt {last.get('attempt_no')} pass"


def package_state(store: MacroStore, macro_dir=None) -> str:
    """NOT_FROZEN | FROZEN | BLOCKED (two failed attempts across all 2.x versions)."""
    if macro_dir is not None and attempts_path(macro_dir).exists() and failures(macro_dir) >= 2:
        return "BLOCKED"
    pkg = store.get("gate.package")
    frozen = pkg.get("status") == "FROZEN" and all(isinstance(pkg.get(k), str) and pkg.get(k) != "written_at_freeze"
                                                  for k in ("definitions_md5", "acceptance_report_md5", "frozen_utc"))
    return "FROZEN" if frozen else "NOT_FROZEN"


def verify_package(store: MacroStore, *, macro_dir=None, **manifest_kw) -> dict:
    """Re-hash the manifest and compare with gate.package (called at every card run, T-CARD-02). Raises
    PackageNotFrozen before the freeze and PackageMismatch on any difference in a gate.* block, a harness source,
    an acceptance fixture, a seed, a ledger hash or the acceptance report. Returns the manifest."""
    state = package_state(store, macro_dir)
    if state != "FROZEN":
        raise PackageNotFrozen([f"gate.package.status {state}: no card runs before the freeze (P11, L2243)"])
    pkg = store.get("gate.package")
    got, manifest = definitions_md5(store, **manifest_kw)
    reasons = []
    if got != pkg["definitions_md5"]:
        reasons.append(f"definitions_md5 {got} != frozen {pkg['definitions_md5']} (a gate.* block, harness source, fixture, seed or ledger changed)")
    if macro_dir is not None:
        rp = report_path(macro_dir)
        rep_md5 = md5_hex(rp.read_bytes()) if rp.is_file() else None
        if rep_md5 != pkg["acceptance_report_md5"]:
            reasons.append(f"acceptance_report_md5 {rep_md5} != frozen {pkg['acceptance_report_md5']}")
    if reasons:
        raise PackageMismatch(reasons)
    return manifest


def freeze_reasons(store: MacroStore, anchor: str | None, macro_dir, *, fixture_dir: Path = FIXTURE_DIR,
                   fixtures: Sequence[str] = REFERENCE_FIXTURES, root: Path = REPO_ROOT, sources: Sequence[str] = HARNESS_SOURCES) -> list[str]:
    """The three refusal reasons of a freeze on this machine, each stated once with its detail."""
    reasons = []
    ok, detail = acceptance_passed(macro_dir)
    if not ok:
        missing = [s for s in sources if not (Path(root) / s).is_file()]
        reasons.append(f"{REASON_ACCEPTANCE}: {detail}" + (f"; harness sources absent {missing}" if missing else ""))
    if not anchor or anchor == MA.GIT_HASH:
        reasons.append(REASON_ANCHOR)
    absent = [f for f in fixtures if not (Path(fixture_dir) / f).is_file()]
    if absent:
        reasons.append(f"{REASON_FIXTURES}: {absent}")
    return reasons


def freeze(store_path, log_path, anchor: str | None, clock: Clock, *, macro_dir, root: Path = REPO_ROOT,
           fixture_dir: Path = FIXTURE_DIR, fixtures: Sequence[str] = REFERENCE_FIXTURES, sources: Sequence[str] = HARNESS_SOURCES,
           ledger_hashes: Mapping[str, str] | None = None, council_answers: Mapping[str, str | None] | None = None) -> FreezeResult:
    """Freeze package 2.0.0 (section 8.1.3 step 3). Refuses with FreezeRefused(reasons) unless the acceptance test
    passed, the anchor is versioned and every reference fixture is present. Otherwise writes gate.package
    {version, definitions_md5, acceptance_report_md5, frozen_utc, status: FROZEN, anchor} to the store file
    (validated before the write), the manifest under <macro_dir>/gate/, and a `package_freeze` governance event.
    Adoption counts as one header revision, never a ledger row (brief F-23)."""
    store = load_store(store_path)
    if store.get("gate.package").get("status") == "FROZEN":
        raise FreezeRefused([f"gate.package already FROZEN ({store.get('gate.package.definitions_md5')}); a change is a new package version"])
    reasons = freeze_reasons(store, anchor, macro_dir, fixture_dir=fixture_dir, fixtures=fixtures, root=root, sources=sources)
    if reasons:
        raise FreezeRefused(reasons)
    md5, manifest = definitions_md5(store, root=root, sources=sources, fixture_dir=fixture_dir, fixtures=fixtures,
                                    ledger_hashes=ledger_hashes, council_answers=council_answers)
    if manifest["absent"]:
        raise FreezeRefused([f"{REASON_ACCEPTANCE}: manifest entries absent {manifest['absent']}"])
    report_md5 = md5_hex(report_path(macro_dir).read_bytes())
    frozen_utc = MA.utc_stamp(clock())
    doc = json.loads(Path(store_path).read_text(encoding="utf-8"))
    pkg = doc["gate"]["package"]
    pkg.update({"definitions_md5": md5, "acceptance_report_md5": report_md5, "frozen_utc": frozen_utc, "status": "FROZEN",
                "anchor_commit": anchor})
    errs = validate_store_doc(doc)
    if errs:
        raise FreezeRefused(["store refused after the package write: " + " | ".join(errs)])
    _write(manifest_path(macro_dir), json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    _write(Path(store_path), json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    G.append_event(Path(log_path), {"kind": "package_freeze", "book_id": None, "rule_id": None, "key": "gate.package",
                                    "old": {"status": "NOT_FROZEN"},
                                    "new": {"version": pkg["version"], "definitions_md5": md5, "acceptance_report_md5": report_md5,
                                            "frozen_utc": frozen_utc, "anchor": anchor},
                                    "actor": "harness", "reason": "section 8.1.3 step 3: gate package frozen after a passing acceptance attempt",
                                    "refs": ["section 8.1.3 step 3", f"anchor:{anchor}"]}, clock)
    return FreezeResult(pkg["version"], md5, report_md5, frozen_utc, anchor, manifest_path(macro_dir))


def new_package_version(current: str) -> str:
    """The next package version: a change to anything in the manifest after a card result has been seen is a new
    2.x version, re-run on every card with its flips disclosed (L4827); never a patch of the frozen one."""
    major, minor, _patch = current.split(".")
    return f"{major}.{int(minor) + 1}.0"


def version_for_change(store: MacroStore, *, results_seen: bool, **manifest_kw) -> str | None:
    """None when the manifest still hashes to the frozen package; the frozen version while no card result has been
    seen (a bounded redesign stays inside the version, R2-C3); else the new version a changed package must carry."""
    pkg = store.get("gate.package")
    got, _ = definitions_md5(store, **manifest_kw)
    if got == pkg.get("definitions_md5"):
        return None
    return new_package_version(pkg["version"]) if results_seen else pkg["version"]
