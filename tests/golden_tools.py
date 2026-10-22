"""Golden-value tolerance helpers and the goldens.csv loader (spec section 9.3 L5734-5738, section 9.4 L5996;
brief spec_goldens_fixtures B.3; rulings section 6).

`LEVEL1` / `LEVEL2` are the section 9.3 tolerance tables verbatim; `tol(kind, level)` reads them. A verdict derived
from a statistic within tolerance of its threshold is asserted as a class, never as a point (`assert_class`,
L5738). `golden(id)` reads `tests/fixtures/macro/goldens.csv` (one row per golden sub-value); a row whose status is
`pending` or `pre_patch_pending` raises `NotRun("PENDING: §9.4 item <n> ...")` when its value is asked for: no
number is invented in its place (L5996). The loader never substitutes a local-cache value.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from tests.notrun import FIXTURES, NotRun

GOLDENS = FIXTURES / "goldens.csv"
GOLDEN_COLUMNS = ("golden_id", "sub_id", "quantity", "value", "unit", "kind", "level", "mode", "runs_from", "timing",
                  "fixtures", "tests", "status", "source_line", "note")
MODES = ("v12_check", "reference_only", "frozen_v2", "print_only")
STATUSES = ("golden", "pre_patch_pending", "pending", "reference")
TIMINGS = ("COMPLIANT", "VALUE", "NON-COMPLIANT", "")
P_FLOOR = "<1/B"            # a resample count of 0 prints "< 1/B" and is asserted as p < 1/B (T-PZERO-01, L2631)

# Level 1 (L5734-5735), verbatim from the brief (decimals: 1 pp = 0.01), plus `exceedance`. `share` is the bootstrap
# share only (L5734); a deterministic fraction (staleness rate, days on, years positive, plateau) is a `ratio`.
LEVEL1 = {"sharpe": 0.01, "mdd": 0.01, "window_return": 0.01, "weight": 0.02, "share": 0.03,
          "exceedance": 0.003,        # B5 VaR exceedance rates and their bands: T-B5-01 4.70% +/- 0.3 pp (L5642)
          "p_hi": 0.01,   # p >= 0.05
          "p_lo": 0.005,  # p < 0.05
          "z": 0.05, "es_pp": 0.002,  # ES, CDaR and dES +/- 0.2 pp
          "count_exact": 0, "count_boot": 1, "percentile": 5, "qlike_ratio": 0.005, "se": 0.005,
          "vol_level": 0.001,         # +/- 0.1 pp
          "ratio": 0.01, "price": 0}
# Level 2 (L5736), production feeds (e.g. KIS KOSPI official closes); every deviation is explained in the acceptance
# report. No Level-2 tolerance exists for weights, shares, counts, z or ES: print, do not assert (brief F-22).
LEVEL2 = {"sharpe": 0.03, "window_return": 0.02, "mdd": 0.02, "p": 0.02}
KINDS = tuple(LEVEL1) + ("verdict", "text")


def tol(kind: str, level: int = 1) -> float:
    """Tolerance of a kind at Level 1 or 2; ValueError when Level 2 has none (print, do not assert)."""
    if kind not in LEVEL1:
        raise KeyError(f"unknown tolerance kind {kind!r}; kinds: {tuple(LEVEL1)}")
    if level == 1:
        return LEVEL1[kind]
    if level != 2:
        raise ValueError(f"level must be 1 or 2, not {level!r}")
    key = "p" if kind in ("p_hi", "p_lo") else kind
    if key not in LEVEL2:
        raise ValueError(f"Level 2 has no tolerance for {kind!r}: print, do not assert (L5736)")
    return LEVEL2[key]


def p_kind(p: float) -> str:
    """p-value tolerance kind by value: +/- 0.01 at p >= 0.05, +/- 0.005 below (L5735)."""
    return "p_hi" if p >= 0.05 else "p_lo"


def within(kind: str, got: float, want: float, level: int = 1) -> bool:
    got, want = float(got), float(want)
    return math.isfinite(got) and math.isfinite(want) and abs(got - want) <= tol(kind, level) + 1e-12


def assert_close(got: float, want: float, kind: str, level: int = 1, label: str = "") -> None:
    """`abs(got - want) <= tol(kind, level)` else AssertionError naming the golden."""
    if not within(kind, got, want, level):
        raise AssertionError(f"{label or kind}: got {got!r}, want {want!r} +/- {tol(kind, level)} "
                             f"(Level {level}, {kind}; deviation {float(got) - float(want):+.6g})")


def near_threshold(stat: float, threshold: float, kind: str, level: int = 1) -> bool:
    """True when the deciding statistic lies within tol(kind) of its threshold: the test must then use assert_class."""
    return abs(float(stat) - float(threshold)) <= tol(kind, level) + 1e-12


def assert_class(stat: float, threshold: float, kind: str, verdict: str, allowed, *, point: str | None = None,
                 level: int = 1, label: str = "") -> None:
    """Verdict near a threshold is asserted as a class (L5738, L5499): `verdict in allowed`. Away from the threshold
    the point verdict `point` (when given) must hold as well."""
    allowed = set(allowed)
    if verdict not in allowed:
        raise AssertionError(f"{label or 'verdict'}: {verdict!r} not in {sorted(allowed)} "
                             f"(stat {stat!r} vs threshold {threshold!r}, {kind})")
    if point is not None and not near_threshold(stat, threshold, kind, level) and verdict != point:
        raise AssertionError(f"{label or 'verdict'}: {verdict!r} != {point!r} although stat {stat!r} is not within "
                             f"{tol(kind, level)} of threshold {threshold!r}")


def assert_p_floor(p: float, B: int, label: str = "") -> None:
    """A golden printed as 0.000 / '<1/B' is asserted as p < 1/B, never as p == 0 (T-PZERO-01)."""
    assert B > 0 and 0.0 <= float(p) < 1.0 / B, f"{label or 'p'}: {p!r} is not below 1/B = {1.0 / B:.6g}"


# --------------------------------------------------------------------------- #
# goldens.csv
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GoldenRow:
    golden_id: str
    sub_id: str
    quantity: str
    value: float | str | None      # float when numeric; "<1/B" / verdict / text as str; None when pending
    unit: str
    kind: str
    level: int
    mode: str
    runs_from: str
    timing: str
    fixtures: tuple[str, ...]
    tests: tuple[str, ...]
    status: str
    source_line: str
    note: str

    @property
    def pending(self) -> bool:
        return self.status in ("pending", "pre_patch_pending")

    def want(self) -> float | str:
        """The value to assert against; NotRun("PENDING: ...") for a pending row (L5996)."""
        if self.pending:
            item = self.note.split(";")[0].strip() if self.note.startswith("§9.4") else "§9.4"
            raise NotRun(f"PENDING: {item} — {self.golden_id}/{self.sub_id} ({self.status}): no number is invented")
        if self.value is None:
            raise ValueError(f"{self.golden_id}/{self.sub_id}: no value")
        return self.value


@dataclass(frozen=True)
class Golden:
    golden_id: str
    rows: tuple[GoldenRow, ...]

    def row(self, sub_id: str) -> GoldenRow:
        for r in self.rows:
            if r.sub_id == sub_id:
                return r
        raise KeyError(f"{self.golden_id}: no sub_id {sub_id!r}; have {[r.sub_id for r in self.rows]}")

    def want(self, sub_id: str) -> float | str:
        return self.row(sub_id).want()

    @property
    def fixtures(self) -> tuple[str, ...]:
        out: list[str] = []
        for r in self.rows:
            out.extend(f for f in r.fixtures if f not in out)
        return tuple(out)


def _value(raw: str) -> float | str | None:
    raw = raw.strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return raw


_CACHE: dict[Path, dict[str, Golden]] = {}


def load_goldens(path: Path = GOLDENS) -> dict[str, Golden]:
    """Every golden keyed by id; refuses a wrong header, an unknown kind/mode/status/timing or a duplicate key."""
    if path in _CACHE:
        return _CACHE[path]
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != GOLDEN_COLUMNS:
            raise ValueError(f"{path.name}: header must be {','.join(GOLDEN_COLUMNS)}")
        rows: dict[str, list[GoldenRow]] = {}
        seen: set[tuple[str, str]] = set()
        for raw in reader:
            key = (raw["golden_id"], raw["sub_id"])
            if key in seen:
                raise ValueError(f"{path.name}: {key} listed twice")
            seen.add(key)
            if raw["kind"] not in KINDS or raw["mode"] not in MODES or raw["status"] not in STATUSES \
                    or raw["timing"] not in TIMINGS or int(raw["level"]) not in (1, 2):
                raise ValueError(f"{path.name}: {key} has an unknown kind/mode/status/timing/level: {raw}")
            value = _value(raw["value"])
            if raw["status"] in ("golden", "reference") and value is None:
                raise ValueError(f"{path.name}: {key} is {raw['status']} but has no value")
            rows.setdefault(raw["golden_id"], []).append(GoldenRow(
                raw["golden_id"], raw["sub_id"], raw["quantity"], value, raw["unit"], raw["kind"], int(raw["level"]),
                raw["mode"], raw["runs_from"], raw["timing"],
                tuple(x for x in raw["fixtures"].split(";") if x), tuple(x for x in raw["tests"].split(";") if x),
                raw["status"], raw["source_line"], raw["note"]))
    _CACHE[path] = {gid: Golden(gid, tuple(rs)) for gid, rs in rows.items()}
    return _CACHE[path]


def golden(golden_id: str, path: Path = GOLDENS) -> Golden:
    table = load_goldens(path)
    if golden_id not in table:
        raise KeyError(f"{golden_id} not in {path.name}")
    return table[golden_id]


def assert_golden(golden_id: str, got: dict, level: int = 1, path: Path = GOLDENS) -> list[tuple]:
    """Compare `got[sub_id]` with each golden sub-value; AssertionError listing every deviation; returns the
    (sub_id, got, want, kind, deviation) rows for the acceptance report. A pending row raises NotRun; a '<1/B'
    row takes `got[sub_id] = (p, B)`."""
    g, report, bad = golden(golden_id, path), [], []
    for sub_id, value in got.items():
        row = g.row(sub_id)
        want = row.want()
        if want == P_FLOOR:
            p, B = value
            ok = 0.0 <= float(p) < 1.0 / int(B)
            report.append((sub_id, p, want, row.kind, None))
        elif row.kind in ("verdict", "text") or isinstance(want, str):
            ok = str(value) in str(want).split("|")
            report.append((sub_id, value, want, row.kind, None))
        else:
            ok = within(row.kind, value, want, level)
            report.append((sub_id, value, want, row.kind, float(value) - float(want)))
        if not ok:
            bad.append(f"{sub_id}: got {value!r}, want {want!r} ({row.kind}, Level {level})")
    if bad:
        raise AssertionError(f"{golden_id} deviations: " + "; ".join(bad))
    return report
