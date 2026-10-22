"""Family trial ledger, N_eff and step 3 of the gate (R-23; P13; section 10 item 36; TASK-M7-01/03/04/05).

Spec L2420-2530 (R-23), config `gate.step3` of the shipped store, brief spec_M7_gate_package B1. Every
configuration ever run in a card's family is one hash-chained row of `<ledger_dir>/<family_id>.jsonl`
(the harness is the only writer, research scripts included); the family hash is committed with every header;
step 3 deflates with `N_eff = max(N_clusters, N_equiv)` and computes the selection factor f at the run. The
Kish design effect is never computed anywhere (`scan_forbidden` is the static guard of T-STEP3-02) and a
revision count is never N.

Readings of what the spec leaves undefined ("reading:" in each docstring, spec line cited):
- ledger_hash = md5(canonical_json(sorted rows)) with rows ordered by their canonical JSON (L2445);
- each row also carries `row_md5` (its own content) so an edit of the LAST row is detected, not only a
  broken `prev_row_md5` chain (L2440 "a hand-edited row breaks the hash chain");
- a re-run of an identical configuration (same `config_id`) is the same trial: nothing is appended and the
  first row stands (L2473 "a ledger row is a distinct configuration");
- the common window of the difference series is the intersection of their indices (L2448 "on the common
  window"); fewer than 20 common observations -> CorrUnavailable;
- `t_fix` of the f = 1 route is the earliest anchored instant among the header commit and the published
  SPEC versions naming the configuration; an unanchored instant anywhere in that comparison refuses step 3
  (TASK-M7-05; rulings 3.1: the reason names the owner action);
- SE_null and the LW-HAC SE_obs are R-24 inputs (gate_stats, another package): step 3 takes them as
  arguments and uses SE_obs when SE_null is absent (L2464 "if fewer than 2: SE_obs");
- V_trials is printed when the family holds >= 30 independent trials, independent = N_clusters >= 30
  (brief F-18); it is the cross-trial variance of the rows' `delta_sr` values.

No wall clock: every instant is a parameter. No `config` import: the ledger directory is injected.
"""
from __future__ import annotations

import ast
import json
import math
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
import scipy.stats as sps
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.integrate import quad
from scipy.spatial.distance import squareform

from core.ficc.macro_schema import canonical_json, md5_hex
from core.quant import gate_stats as GS
from core.quant.validate import EULER_GAMMA, TRADING_DAYS

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMING_CLASSES = ("VALUE", "NON-COMPLIANT", "COMPLIANT")
PHASES = ("research", "card")
# Null-distribution runs are not configurations: they append no row (L2440; T-SEL-01 (f)).
NULL_DISTRIBUTION_KINDS = ("acceptance_placebo", "shift_panel", "gjr_null", "d4_panel")
RUN_KINDS = ("trial", "quick_check", "revision", "timing_lag", "variant") + NULL_DISTRIBUTION_KINDS
# The frozen row-set key (gate.step3.row_set.key, L2500); `book` is the row's `instrument_book`.
ROW_SET_KEY = ("rule", "params", "estimator", "window", "cap", "instrument_book", "rebalance", "timing_class",
               "start_convention")
READINGS = ("market_scoped", "family_wide")
REQUIRED_ROW = ("rule", "params", "timing_class", "span", "market", "run_utc", "phase", "script")
OPTIONAL_ROW = ("estimator", "window", "cap", "instrument_book", "rebalance", "start_convention", "cost",
                "results_md5", "diff_series_ref", "card_id", "delta_sr", "run_kind", "run_utc_anchor", "source")
CHAIN_FIELDS = ("row_md5", "prev_row_md5")
UNVERSIONED = "UNVERSIONED"
ANCHOR_KINDS = ("git", "external")
CARD_O_BAR = 0.95                       # gate.step3.card_o_bar
Z95 = float(sps.norm.ppf(0.95))
Z_CHECK = {"le_8_cells": 2.50, "beyond": 3.34}   # gate.stats.multiplicity.one_sided_z
N_MAX = 1.0e6
DRAWS = 200_000                         # gate.step3.emax.simulated_draws
SEED = 11                               # gate.step3.emax.seed
_CHUNK = 50_000
MIN_COMMON = 20
# Family by rule: what the spec states (QC_modules.csv is absent). R-29 is the R-06 family (brief B7); R-04 runs
# its step 3 on the R-03 ledger (TASK-M7-25). Anything else files by correlation or is refused (L2440).
RULE_FAMILY = {"R-03": "R-03", "R-04": "R-03", "R-06": "R-06", "R-29": "R-06", "R-28": "R-28", "R-31": "R-31"}
FILING_RHO = 0.5                        # gate.step3.ledger.filing_cluster_rho
# Per-period Sharpe ceilings: a per-period SR above these is an annualised figure passed with a per-period T
# (T-DSR-02 "an annualised SR with a daily T raises"); reading: 0.5/day = 7.9 annualised, 2/month = 6.9.
SR_PER_PERIOD_MAX = {"daily": 0.5, "monthly": 2.0}
PERIODS_PER_YEAR = {"daily": TRADING_DAYS, "monthly": 12}


class LedgerRefused(ValueError):
    """The ledger or a row is refused; nothing is written."""


class NullDistributionRun(LedgerRefused):
    """A placebo, shift-panel, GJR-null or D4-panel run: never a ledger row (L2440)."""


class CorrUnavailable(ValueError):
    """The difference-series correlation matrix cannot be built (a missing or degenerate series, L2516)."""


class UnanchoredTimestamp(ValueError):
    """An instant of the f = 1 route is not anchored to a git commit or an external anchor (TASK-M7-05)."""


class HeaderRefused(ValueError):
    """A header that declares `selection_factor` or lacks `ledger_hash_at_registration` (C-2, L2513)."""


class FamilyRefused(ValueError):
    """No family files the configuration by rule or by correlation (L2440)."""


# --------------------------------------------------------------------------- #
# Anchors and instants (TASK-M7-05)
# --------------------------------------------------------------------------- #
def anchored(anchor) -> bool:
    """`git:<sha>` or `external:<ref>` with a non-empty ref; anything else (UNVERSIONED, None) is unanchored."""
    if not isinstance(anchor, str) or ":" not in anchor:
        return False
    kind, _, ref = anchor.partition(":")
    return kind in ANCHOR_KINDS and bool(ref.strip())


def repo_anchor(root: Path = REPO_ROOT) -> str:
    """`git:<sha>` of HEAD when the folder is a git repository, else UNVERSIONED (rulings 3.1)."""
    head = Path(root) / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref:"):
            ref = text[4:].strip()
            loose = Path(root) / ".git" / ref
            if loose.is_file():
                text = loose.read_text(encoding="utf-8").strip()
            else:                                   # after `git gc` / `git pack-refs` the ref lives in packed-refs only
                packed = (Path(root) / ".git" / "packed-refs").read_text(encoding="utf-8").splitlines()
                text = next((ln.split()[0] for ln in packed if ln.endswith(" " + ref)), "")
        return f"git:{text}" if re.fullmatch(r"[0-9a-f]{40}", text) else UNVERSIONED
    except OSError:
        return UNVERSIONED


def parse_utc(value) -> datetime:
    """ISO-8601 with 'Z' (or a tz-aware datetime) -> tz-aware UTC; naive input refused."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("instants must be tz-aware UTC")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str) or not value:
        raise ValueError(f"not an instant: {value!r}")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError(f"instant without a timezone: {value!r}")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class Anchor:
    """An externally anchored instant: the header commit or a published SPEC version (L2473)."""
    utc: str
    anchor: str
    what: str = "header_commit"
    config_ids: tuple = ()      # a SPEC version names the configurations it fixed; () = the commit (all)

    def require(self) -> datetime:
        if not anchored(self.anchor):
            raise UnanchoredTimestamp(f"{self.what} at {self.utc} is {self.anchor or 'unanchored'}: "
                                      "owner must place the repository under git or name an external anchor "
                                      "(TASK-M7-05; rulings 3.1)")
        return parse_utc(self.utc)


# --------------------------------------------------------------------------- #
# Rows
# --------------------------------------------------------------------------- #
def config_id(row: Mapping) -> str:
    """md5 of the canonical JSON of the frozen row-set key (L2500); params include signal, threshold, target,
    lookback, multiplier and lag, so two rows differing only there are two configurations (T-SEL-01 (h))."""
    return md5_hex(canonical_json({k: row.get(k) for k in ROW_SET_KEY}))


def _span(value) -> tuple[str, str]:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or not all(isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in value)
            or value[0] > value[1]):
        raise LedgerRefused(f"span must be [start, end] ISO dates, not {value!r}")
    return str(value[0]), str(value[1])


def validate_row(row: Mapping) -> dict:
    """The row as the ledger stores it (chain fields excluded); LedgerRefused on any missing or ill-typed field."""
    if not isinstance(row, Mapping):
        raise LedgerRefused("a ledger row is a mapping")
    out: dict = {}
    missing = [k for k in REQUIRED_ROW if row.get(k) in (None, "")]
    if missing:
        raise LedgerRefused(f"ledger row lacks {missing}")
    unknown = sorted(set(row) - set(REQUIRED_ROW) - set(OPTIONAL_ROW) - {"config_id", "family_id"} - set(CHAIN_FIELDS))
    if unknown:
        raise LedgerRefused(f"ledger row has unknown fields {unknown}")
    if row["timing_class"] not in TIMING_CLASSES:
        raise LedgerRefused(f"timing_class must be one of {TIMING_CLASSES}, not {row['timing_class']!r} (L2515)")
    if row["phase"] not in PHASES:
        raise LedgerRefused(f"phase must be one of {PHASES}")
    kind = row.get("run_kind", "trial")
    if kind not in RUN_KINDS:
        raise LedgerRefused(f"run_kind must be one of {RUN_KINDS}")
    if kind in NULL_DISTRIBUTION_KINDS:
        raise NullDistributionRun(f"{kind} runs are not configurations: no ledger row (L2440)")
    if not isinstance(row["params"], Mapping):
        raise LedgerRefused("params must be a mapping of every parameter of the run")
    parse_utc(row["run_utc"])
    for k in REQUIRED_ROW:
        out[k] = row[k]
    out["span"] = list(_span(row["span"]))
    out["params"] = dict(row["params"])
    for k in OPTIONAL_ROW:
        out[k] = row.get(k)
    out["run_kind"] = kind
    out["run_utc_anchor"] = row.get("run_utc_anchor") or UNVERSIONED
    out["config_id"] = config_id(out)
    return out


def _row_md5(row: Mapping) -> str:
    return md5_hex(canonical_json({k: v for k, v in row.items() if k not in CHAIN_FIELDS}))


@dataclass(frozen=True)
class LedgerCheck:
    ok: bool
    n_rows: int
    first_bad_line: int | None
    reason: str = ""

    def __bool__(self) -> bool:
        return self.ok


@dataclass(frozen=True)
class RegisterResult:
    row: dict
    appended: bool
    row_md5: str


_APPEND_LOCK = threading.Lock()


@contextmanager
def _exclusive(path: Path):
    """Serialise read-verify-append on one ledger across threads and processes (a sidecar `<file>.lock` with an
    OS byte lock). Two writers reading the same tail would both chain to it and break the ledger for good."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _APPEND_LOCK, open(str(path) + ".lock", "a+b") as fh:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)       # retries for about 10 s, then raises
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


class FamilyLedger:
    """`<ledger_dir>/<family_id>.jsonl`: one canonical-JSON row per line, binary append, fsync, raises.

    Every row carries `row_md5` (its content) and `prev_row_md5` (the previous line's bytes); `rows()` refuses
    a chain that does not verify. Test runs point `path` at a temporary copy (T-HERM-02)."""

    def __init__(self, path: Path, family_id: str | None = None) -> None:
        from core.isolation import refuse_quantgen  # TRADEGEN: never open a QUANTGEN ledger, whoever passes the path
        self.path = refuse_quantgen(path, "ledger")
        self.family_id = family_id or self.path.stem

    # -- reading -------------------------------------------------------------
    def _lines(self) -> list[bytes]:
        if not self.path.exists():
            return []
        raw = self.path.read_bytes().split(b"\n")
        if raw and raw[-1] == b"":
            raw.pop()
        return raw

    def verify_chain(self) -> LedgerCheck:
        """Re-hash every line: bytes == canonical JSON, prev_row_md5 == previous line, row_md5 == content,
        config_id recomputes, family matches. A hand edit, a reformat, a dropped or moved line breaks it."""
        prev, n = None, 0
        for lineno, raw in enumerate(self._lines(), start=1):
            try:
                row = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return LedgerCheck(False, n, lineno, "unreadable line")
            if not isinstance(row, dict):
                return LedgerCheck(False, n, lineno, "not an object")
            if canonical_json(row).encode("utf-8") != raw:
                return LedgerCheck(False, n, lineno, "line is not its canonical JSON")
            if row.get("prev_row_md5") != prev:
                return LedgerCheck(False, n, lineno, "prev_row_md5 does not match the previous line")
            if row.get("row_md5") != _row_md5(row):
                return LedgerCheck(False, n, lineno, "row_md5 does not match the row content")
            try:
                clean = validate_row({k: v for k, v in row.items() if k not in CHAIN_FIELDS})
            except LedgerRefused as exc:
                return LedgerCheck(False, n, lineno, str(exc))
            if clean["config_id"] != row.get("config_id") or row.get("family_id") != self.family_id:
                return LedgerCheck(False, n, lineno, "config_id or family_id does not recompute")
            prev = md5_hex(raw)
            n += 1
        return LedgerCheck(True, n, None)

    def rows(self) -> list[dict]:
        """Every row of an intact chain; LedgerRefused on a broken one (fail closed, L2514)."""
        check = self.verify_chain()
        if not check:
            raise LedgerRefused(f"{self.path.name}: chain broken at line {check.first_bad_line}: {check.reason}")
        return [json.loads(raw.decode("utf-8")) for raw in self._lines()]

    def hash(self, rows: Sequence[Mapping] | None = None) -> str:
        """`md5(canonical_json(sorted(ledger_rows)))` (L2445); reading: rows sorted by their canonical JSON."""
        rows = self.rows() if rows is None else list(rows)
        return ledger_hash(rows)

    def snapshot(self, hash_value: str) -> list[dict]:
        """The prefix of rows whose hash equals `hash_value` (the snapshot a header's
        `ledger_hash_at_registration` names, L2473); LedgerRefused when no prefix has that hash."""
        rows = self.rows()
        for k in range(len(rows) + 1):
            if ledger_hash(rows[:k]) == hash_value:
                return rows[:k]
        raise LedgerRefused(f"{self.path.name}: ledger_hash {hash_value} names no snapshot of this ledger")

    @property
    def n_raw(self) -> int:
        return len(self.rows())

    # -- writing (the harness only) ------------------------------------------
    def append(self, row: Mapping) -> RegisterResult:
        """Validate, chain, append. A duplicate `config_id` appends nothing and returns the existing row
        (reading above). Raises on a broken chain, a refused row or a write failure; never swallows."""
        clean = validate_row(row)
        clean["family_id"] = self.family_id
        with _exclusive(self.path):
            existing = self.rows()
            for r in existing:
                if r["config_id"] == clean["config_id"]:
                    return RegisterResult(r, False, r["row_md5"])
            lines = self._lines()
            clean["prev_row_md5"] = md5_hex(lines[-1]) if lines else None
            clean["row_md5"] = _row_md5(clean)
            line = canonical_json(clean).encode("utf-8")
            with open(self.path, "ab") as fh:
                fh.write(line + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
        return RegisterResult(clean, True, md5_hex(line))

    def difference_series(self, loader: Callable[[str], object], rows: Sequence[Mapping] | None = None) -> dict:
        """{config_id: loader(diff_series_ref)}; a row without a reference or a loader failure -> CorrUnavailable."""
        out = {}
        for r in (self.rows() if rows is None else rows):
            ref = r.get("diff_series_ref")
            if not ref:
                raise CorrUnavailable(f"{self.family_id}: row {r['config_id']} has no stored difference series")
            try:
                out[r["config_id"]] = loader(ref)
            except Exception as exc:           # the loader names the file; step 3 fails closed on it
                raise CorrUnavailable(f"{self.family_id}: difference series {ref!r} unavailable: {exc}") from exc
        return out


def ledger_hash(rows: Sequence[Mapping]) -> str:
    return md5_hex(canonical_json(sorted((dict(r) for r in rows), key=canonical_json)))


def family_ledger(family_id: str, ledger_dir: Path) -> FamilyLedger:
    return FamilyLedger(Path(ledger_dir) / f"{family_id}.jsonl", family_id)


def register_trial(ledger: FamilyLedger, row: Mapping, *, script: str | None = None) -> RegisterResult:
    """The harness's single entry for every run of a registered rule's code path (research scripts, quick
    checks, revisions, timing lags, variants). Null-distribution runs raise NullDistributionRun and append
    nothing; a row without a timing class is refused; a duplicate configuration is the same trial."""
    row = dict(row)
    if script:
        row["script"] = script
    return ledger.append(row)


def assert_hash_at_run(ledger: FamilyLedger, ledger_hash_at_run: str) -> str:
    """After a run the card's `ledger_hash_at_run` must equal the stored ledger's hash (the run's own rows
    included) or the card is not written (L2513, T-LEDGER-01). Returns the stored hash."""
    stored = ledger.hash()
    if ledger_hash_at_run != stored:
        raise LedgerRefused(f"{ledger.family_id}: ledger_hash_at_run {ledger_hash_at_run} != stored {stored}; "
                            "card not written")
    return stored


def file_family(rule_id: str, d_new=None, families: Mapping[str, Mapping[str, object]] | None = None,
                *, rho: float = FILING_RHO) -> str:
    """Family by rule (RULE_FAMILY, the spec's QC_modules reading); else the family one of whose stored
    difference series correlates >= rho with `d_new` on the common window (the highest binds); else refused."""
    if rule_id in RULE_FAMILY:
        return RULE_FAMILY[rule_id]
    if d_new is None or not families:
        raise FamilyRefused(f"{rule_id}: no family by rule and no difference series to file by correlation")
    best, best_rho = None, -1.0
    for fam, series in families.items():
        for cid, s in series.items():
            c = diff_corr({"new": d_new, cid: s})[0, 1]
            if c > best_rho:
                best, best_rho = fam, float(c)
    if best is None or best_rho < rho:
        raise FamilyRefused(f"{rule_id}: no family's rows correlate >= {rho} (max {best_rho:.3f}); refused")
    return best


# --------------------------------------------------------------------------- #
# Correlation, clusters, E[max], N_equiv, N_eff (L2444-2467)
# --------------------------------------------------------------------------- #
def _aligned(series) -> np.ndarray:
    """(T, K) matrix of the difference series on their common window (index intersection for pandas Series,
    equal-length arrays otherwise)."""
    items = list(series.values()) if isinstance(series, Mapping) else list(series)
    if len(items) < 1:
        raise CorrUnavailable("no difference series")
    if any(s is None for s in items):
        raise CorrUnavailable("a difference series is missing")
    if all(hasattr(s, "index") and hasattr(s, "reindex") for s in items):
        common = items[0].index
        for s in items[1:]:
            common = common.intersection(s.index)
        common = common.sort_values()
        cols = [np.asarray(s.reindex(common), dtype=float) for s in items]
    else:
        cols = [np.asarray(s, dtype=float).ravel() for s in items]
        if len({c.size for c in cols}) > 1:
            raise CorrUnavailable(f"undated difference series of unequal length {sorted({c.size for c in cols})}: "
                                  "pass dated (indexed) series so the common window is their date intersection")
    X = np.column_stack(cols) if cols else np.empty((0, 0))
    X = X[np.all(np.isfinite(X), axis=1)]
    if X.shape[0] < MIN_COMMON:
        raise CorrUnavailable(f"common window has {X.shape[0]} observations (< {MIN_COMMON})")
    return X


def diff_corr(series) -> np.ndarray:
    """Pearson correlation of the stored difference series on the single common window (PSD by construction).
    A constant series (NaN correlation) -> CorrUnavailable."""
    X = _aligned(series)
    if X.shape[1] == 1:
        return np.ones((1, 1))
    with np.errstate(invalid="ignore", divide="ignore"):      # a constant series is refused below, not warned about
        C = np.corrcoef(X, rowvar=False)
    if not np.all(np.isfinite(C)):
        raise CorrUnavailable("a difference series has no variance on the common window")
    return C


def mean_offdiag(C: np.ndarray) -> float:
    C = np.asarray(C, dtype=float)
    k = C.shape[0]
    if k < 2:
        return 0.0
    return float((C.sum() - np.trace(C)) / (k * (k - 1)))


def linear_n_hat(rho_bar: float, n_raw: int) -> float:
    """BLdP eq. 9 (linear): rho + (1 - rho) * N_raw. Printed bound only; never the gate's N (L2450)."""
    return float(rho_bar + (1.0 - rho_bar) * n_raw)


def n_clusters(C: np.ndarray, rho_min: float = FILING_RHO) -> int:
    """Average linkage on sqrt(0.5 * (1 - rho)), cut at sqrt(0.5 * (1 - rho_min)) (= 0.5, i.e. rho >= 0.5)."""
    C = np.asarray(C, dtype=float)
    k = C.shape[0]
    if k < 2:
        return k
    D = np.sqrt(np.clip(0.5 * (1.0 - C), 0.0, None))
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="average")
    labels = fcluster(Z, t=math.sqrt(0.5 * (1.0 - rho_min)), criterion="distance")
    return int(len(set(labels.tolist())))


def emax_sim(C: np.ndarray, draws: int = DRAWS, seed: int = SEED) -> float:
    """E[max_k Z_k], Z ~ N(0, C): eigen-decomposition draws (near-duplicate rows make C singular, so Cholesky
    fails), `default_rng(SeedSequence(seed))`, chunks of 50,000 rows (fixed, so the stream is deterministic)."""
    C = np.asarray(C, dtype=float)
    k = C.shape[0]
    if k == 1:
        return 0.0
    w, V = np.linalg.eigh(0.5 * (C + C.T))
    L = V * np.sqrt(np.clip(w, 0.0, None))
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    total, done = 0.0, 0
    while done < draws:
        m = min(_CHUNK, draws - done)
        Z = rng.standard_normal((m, k)) @ L.T
        total += float(Z.max(axis=1).sum())
        done += m
    return total / draws


def emax_iid_exact(n: float) -> float:
    """E[max of N iid N(0,1)] by the integral of x * N * phi(x) * Phi(x)^(N-1) on [-12, 12] (real N allowed)."""
    if n <= 1.0:
        return 0.0
    val, _err = quad(lambda x: x * n * sps.norm.pdf(x) * sps.norm.cdf(x) ** (n - 1.0), -12.0, 12.0, limit=200)
    return float(val)


def emax_closed(n: float) -> float:
    """BLdP closed form (1 - g) * Phi_inv(1 - 1/N) + g * Phi_inv(1 - 1/(N e)), g = Euler-Mascheroni."""
    return float((1.0 - EULER_GAMMA) * sps.norm.ppf(1.0 - 1.0 / n)
                 + EULER_GAMMA * sps.norm.ppf(1.0 - 1.0 / (n * math.e)))


def emax_iid(n: float) -> float:
    """e(N) of L2454: 0 at N <= 1; the exact integral below 2 (never Euler-Mascheroni there); the closed form
    from 2. e drops at N = 2 from the exact 0.564 to the closed-form 0.520."""
    n = float(n)
    if n <= 1.0:
        return 0.0
    if n < 2.0:
        return emax_iid_exact(n)
    return emax_closed(n)


E_EXACT_2 = emax_iid_exact(2.0)        # 0.56419
E_CLOSED_2 = emax_closed(2.0)          # 0.51976


def _bisect(fn, lo: float, hi: float, target: float, iters: int = 100) -> float:
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def n_equiv(emax: float) -> float:
    """e_inverse: emax <= 0 -> 1; below the closed-form value at 2 -> bisect the exact integral on [1, 2);
    inside [0.520, 0.564] -> 2; else bisect the closed form on [2, 1e6] (capped at 1e6)."""
    if emax <= 0.0:
        return 1.0
    if emax < E_CLOSED_2:
        return _bisect(emax_iid_exact, 1.0, 2.0, emax)
    if emax <= E_EXACT_2:
        return 2.0
    if emax >= emax_closed(N_MAX):
        return N_MAX
    return _bisect(emax_closed, 2.0, N_MAX, emax)


@dataclass(frozen=True)
class NResult:
    N_raw: int
    rho_bar: float
    N_hat_linear: float
    N_clusters: int
    E_sim: float
    N_equiv: float
    N_eff: float

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def n_eff(series, *, draws: int = DRAWS, seed: int = SEED) -> NResult:
    """{N_raw, rho_bar, N_hat_linear, N_clusters, E_sim, N_equiv, N_eff = max(N_clusters, N_equiv)} (L1093)."""
    C = diff_corr(series)
    k = C.shape[0]
    rho = mean_offdiag(C)
    clusters = n_clusters(C)
    e_sim = emax_sim(C, draws, seed)
    n_eq = n_equiv(e_sim)
    return NResult(k, rho, linear_n_hat(rho, k), clusters, e_sim, n_eq, max(float(clusters), n_eq))


# --------------------------------------------------------------------------- #
# Deflated Delta-SR, DSR vs 0, PSR vs S (L2466; T-DSR-01/02)
# --------------------------------------------------------------------------- #
def deflated_dsr(delta_sr: float, se_obs: float, se_null: float, hurdle: float) -> float:
    """Phi((delta_SR - SE_null * hurdle) / SE_obs); the three inputs share one unit (annualised in the gate)."""
    if not (se_obs > 0) or not (se_null >= 0):
        raise ValueError("deflated_dsr needs SE_obs > 0 and SE_null >= 0")
    return float(sps.norm.cdf((delta_sr - se_null * hurdle) / se_obs))


def break_even_n(delta_sr: float, se_obs: float, se_null: float, bar: float = CARD_O_BAR) -> float | None:
    """The N at which the deflated value equals `bar` (L2478 "the break-even N"); None when it is below `bar`
    already at N = 1 or SE_null = 0 (no N moves it)."""
    if se_null <= 0:
        return None
    target = (delta_sr - se_obs * float(sps.norm.ppf(bar))) / se_null
    if target <= 0.0:
        return None
    return n_equiv(target)


def _moments(x: np.ndarray) -> tuple[float, float, float, int]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        raise ValueError("need at least 3 observations")
    sd = float(np.std(x, ddof=1))
    sr = float(np.mean(x) / sd) if sd > 0 else 0.0
    g3 = float(sps.skew(x)) if sd > 0 else 0.0
    g4 = float(sps.kurtosis(x, fisher=False)) if sd > 0 else 3.0
    return sr, g3, g4, int(x.size)


def psr(sr: float, T: int, *, units: str, benchmark_sr: float = 0.0, skew: float = 0.0, kurtosis: float = 3.0) -> float:
    """Probabilistic Sharpe ratio (BLdP 2012): Phi((SR - SR*) sqrt(T - 1) / sqrt(1 - g3 SR + (g4 - 1)/4 SR^2))
    with SR, SR* per period and T periods of the declared unit; an annualised SR with a per-period T raises
    (per-period ceilings |SR| <= 0.5/day, <= 2/month). One formula: `gate_stats.psr` (R-24) computes it."""
    if units not in SR_PER_PERIOD_MAX:
        raise ValueError(f"units must be one of {tuple(SR_PER_PERIOD_MAX)}")
    if abs(sr) > SR_PER_PERIOD_MAX[units] or abs(benchmark_sr) > SR_PER_PERIOD_MAX[units]:
        raise ValueError(f"|SR| {max(abs(sr), abs(benchmark_sr)):.3f} is not a per-{units[:-2]} value: an annualised "
                         f"Sharpe ratio was passed with a {units} T (T-DSR-02)")
    if T < 3:
        raise ValueError("T must be at least 3 periods")
    return GS.psr(float(sr), int(T), units=units, sr0=float(benchmark_sr), skew=float(skew), kurt=float(kurtosis))


def dsr_vs_zero(x, *, units: str, hurdle_sr: float = 0.0) -> float:
    """DSR vs 0 of a per-period excess-return series (printed on every CARD-P, L2470): PSR against the
    per-period hurdle (0, or sd_null * e(N) expressed per period)."""
    sr, g3, g4, T = _moments(x)
    return psr(sr, T, units=units, benchmark_sr=hurdle_sr, skew=g3, kurtosis=g4)


def psr_vs_s(x_rule, x_s, *, units: str) -> float:
    """PSR of the rule book against S's per-period Sharpe as the benchmark (printed, never gated, L2470)."""
    sr, g3, g4, T = _moments(x_rule)
    sr_s, _g3, _g4, _T = _moments(x_s)
    return psr(sr, T, units=units, benchmark_sr=sr_s, skew=g3, kurtosis=g4)


# --------------------------------------------------------------------------- #
# Step 3 printed lines and the selection factor (L2468-2482, L2472-2474)
# --------------------------------------------------------------------------- #
def step3_lines(delta_sr: float, se_obs: float, se_null: float, n: NResult, *, cells: int | None = None,
                v_trials: float | None = None, pvalues: Sequence[float] | None = None) -> dict:
    """The printed block of every card: deflated at N_eff, N_raw and N_hat_linear (flag "step 3 borderline"
    when the N_hat_linear value is < 0.95), the break-even N, the one-sided z-check (2.50 for <= 8
    pre-registered cells, 3.34 beyond; 3.34 when the count is unknown, brief F-20). `pvalues` are the analytic
    HAC p-values of every tested variant the runner collected (L2579): BY q and Holm are printed from them,
    never gated; None when the runner supplied none."""
    at_eff = deflated_dsr(delta_sr, se_obs, se_null, emax_iid(n.N_eff))
    at_raw = deflated_dsr(delta_sr, se_obs, se_null, emax_iid(n.N_raw))
    at_hat = deflated_dsr(delta_sr, se_obs, se_null, emax_iid(n.N_hat_linear))
    z = delta_sr / se_obs
    z_bar = Z_CHECK["le_8_cells"] if (cells is not None and cells <= 8) else Z_CHECK["beyond"]
    return {
        "deflated_dSR": at_eff, "at_N_raw": at_raw, "at_N_hat_linear": at_hat,
        "borderline": bool(at_hat < CARD_O_BAR), "flag": "step 3 borderline" if at_hat < CARD_O_BAR else "",
        "break_even_N": break_even_n(delta_sr, se_obs, se_null),
        "z_check": {"z": float(z), "bar": z_bar, "cells": cells, "pass": bool(z >= z_bar)},
        "N_raw": n.N_raw, "N_hat_linear": n.N_hat_linear, "N_clusters": n.N_clusters, "N_equiv": n.N_equiv,
        "N_eff": n.N_eff, "E_sim": n.E_sim, "rho_bar": n.rho_bar,
        "SE_obs": float(se_obs), "SE_null": float(se_null), "V_trials": v_trials,
        "by_q": None if pvalues is None else [float(q) for q in GS.by_qvalue(pvalues)],
        "holm": None if pvalues is None else [float(q) for q in GS.holm_adjusted(pvalues)],
    }


def overlaps(span_a: Sequence[str], span_b: Sequence[str]) -> bool:
    """`any_overlap` (gate.step3.card_p.overlap_rule): the closed date intervals intersect."""
    return span_a[0] <= span_b[1] and span_b[0] <= span_a[1]


def combine_readings(f_by_reading: Mapping[str, float], acceptance_f: float | None = None) -> float:
    """The maximum over the defensible row-set readings binds (R2-C1; T-SEL-01 (g): 1.3 and 2.9 -> 2.9); at a
    card run the larger of it and the acceptance report's f binds, both printed, never a refusal (T-SEL-01 (e))."""
    f = max(float(v) for v in f_by_reading.values())
    if acceptance_f is not None:
        f = max(f, float(acceptance_f))
    return f


def t_fix(card: Mapping, commit: Anchor | None, spec_versions: Sequence[Anchor] = ()) -> datetime:
    """Earliest anchored instant at which this exact configuration was fixed: the header commit or a published
    SPEC version naming its config_id (L2473). Any unanchored instant used -> UnanchoredTimestamp."""
    commit = commit if commit is not None else Anchor(card.get("created_utc") or "", repo_anchor(), "header_commit")
    instants = [commit.require()]
    cid = card.get("config_id")
    for sv in spec_versions:
        if cid is not None and cid in sv.config_ids:
            instants.append(sv.require())
    return min(instants)


def selection_factor(card: Mapping, rows: Sequence[Mapping], *, fixed_at: datetime, series=None,
                     draws: int = DRAWS, seed: int = SEED) -> dict:
    """f under each reading (market_scoped, family_wide): 1.0 when no row of the reading overlaps the evaluation
    span with run_utc < t_fix (sensitivity rows run after the commit never count), else N_eff of the reading
    (Bonferroni). `series` maps config_id -> difference series; a missing one -> CorrUnavailable (the caller
    decides: CARD-O no verdict, CARD-P f = N_raw). Own-run rows and null runs are already excluded."""
    span = (card["data_span"]["start"], card["data_span"]["end"])
    out: dict = {"readings": {}, "n_eff": {}}
    for reading in READINGS:
        R = [r for r in rows if reading == "family_wide" or r.get("market") == card.get("market")]
        touched = []
        for r in R:
            if overlaps(r["span"], span):
                if not anchored(r.get("run_utc_anchor")):
                    raise UnanchoredTimestamp(f"ledger row {r['config_id']} run_utc {r['run_utc']} is "
                                              f"{r.get('run_utc_anchor') or 'unanchored'}: owner must place the "
                                              "repository under git or name an external anchor (TASK-M7-05)")
                if parse_utc(r["run_utc"]) < fixed_at:
                    touched.append(r)
        if not touched:
            out["readings"][reading] = 1.0
            out["n_eff"][reading] = None
            continue
        if series is None:
            raise CorrUnavailable(f"{reading}: no difference series supplied for {len(R)} rows")
        sub = {}
        for r in R:
            if r["config_id"] not in series:
                raise CorrUnavailable(f"{reading}: difference series of {r['config_id']} missing")
            sub[r["config_id"]] = series[r["config_id"]]
        res = n_eff(sub, draws=draws, seed=seed)
        out["readings"][reading] = res.N_eff
        out["n_eff"][reading] = res.as_dict()
    return out


def _check_header(card: Mapping) -> None:
    if "selection_factor" in card:
        raise HeaderRefused("a header that declares selection_factor is refused: f is computed by step3 (C-2)")
    if not card.get("ledger_hash_at_registration"):
        raise HeaderRefused("a header without ledger_hash_at_registration is refused (L2513)")
    if card.get("class") not in ("CARD-O", "CARD-P"):
        raise HeaderRefused("card class must be CARD-O or CARD-P")
    for k in ("card_id", "family_id", "market", "data_span"):
        if not card.get(k):
            raise HeaderRefused(f"header lacks {k}")


def step3(card: Mapping, ledger: FamilyLedger, seed: int = SEED, *, delta_sr: float, se_obs: float,
          se_null: float | None = None, series=None, loader: Callable[[str], object] | None = None,
          commit: Anchor | None = None, spec_versions: Sequence[Anchor] = (), acceptance_f: float | None = None,
          draws: int = DRAWS, cells: int | None = None, x_rule=None, x_s=None, units: str = "daily",
          pvalues: Sequence[float] | None = None) -> dict:
    """Step 3 of a card (L2468-2482). `card` is the header (class, card_id, family_id, market, data_span,
    ledger_hash_at_registration, optional config_id); `delta_sr`, `se_obs`, `se_null` are the R-24 numbers of the
    card's Delta-SR vs its comparator (SE_null absent -> SE_obs; `gate_stats.lw_hac_se(on, S).se` in the runner);
    `pvalues` the variants' analytic HAC p-values for the printed BY q / Holm lines. Rows = the ledger snapshot the header names,
    minus the card's own run rows (card_id, phase card). CARD-O: pass iff deflated >= 0.95; CARD-P: not gated,
    f = max over readings of the selection factor (1 only through anchored timestamps), f_at_1 and f_at_neff
    with the deflated value at each printed. C unavailable: CARD-O raises (no verdict written); CARD-P f = N_raw.
    Returns a plain dict: f, f_at_1, f_at_neff, dsr_at_1, dsr_at_neff, n_raw, n_eff, verdict_contrib, printed."""
    _check_header(card)
    rows = [r for r in ledger.snapshot(card["ledger_hash_at_registration"])
            if not (r.get("card_id") == card["card_id"] and r.get("phase") == "card")]
    if series is None and loader is not None and rows:
        series = ledger.difference_series(loader, rows)
    fixed_at = t_fix(card, commit, spec_versions)
    n_raw = len(rows)
    se_null = se_obs if se_null is None else se_null
    v_trials = None
    deltas = [r["delta_sr"] for r in rows if isinstance(r.get("delta_sr"), (int, float))]
    fail_closed = None
    try:
        sel = selection_factor(card, rows, fixed_at=fixed_at, series=series, draws=draws, seed=seed)
        full = sel["n_eff"].get("family_wide")
        if full is None and rows:
            full = n_eff({r["config_id"]: series[r["config_id"]] for r in rows}, draws=draws, seed=seed).as_dict() \
                if series is not None and all(r["config_id"] in series for r in rows) else None
    except CorrUnavailable as exc:
        if card["class"] == "CARD-O":
            raise CorrUnavailable(f"CARD-O step 3 fails closed, no verdict written: {exc}") from exc
        fail_closed = str(exc)
        sel = {"readings": {r: float(max(n_raw, 1)) for r in READINGS}, "n_eff": {r: None for r in READINGS}}
        full = None
    if full is None:
        n = NResult(max(n_raw, 1), 0.0, float(max(n_raw, 1)), max(n_raw, 1), 0.0, float(max(n_raw, 1)),
                    float(max(n_raw, 1)))
    else:
        n = NResult(**full)
    if n.N_clusters >= 30 and len(deltas) >= 30:
        v_trials = float(np.var(np.asarray(deltas, dtype=float), ddof=1))
    lines = step3_lines(delta_sr, se_obs, se_null, n, cells=cells, v_trials=v_trials, pvalues=pvalues)
    f = combine_readings(sel["readings"], acceptance_f)
    dsr_at_1 = deflated_dsr(delta_sr, se_obs, se_null, emax_iid(1.0))
    dsr_at_neff = lines["deflated_dSR"]
    if card["class"] == "CARD-O":
        contrib = {"gated": True, "pass": bool(dsr_at_neff >= CARD_O_BAR), "bar": CARD_O_BAR}
    else:
        contrib = {"gated": False, "pass": None, "bar": None}
    if x_rule is not None:
        lines["dsr_vs0"] = dsr_vs_zero(x_rule, units=units)
        lines["psr_vs_S"] = psr_vs_s(x_rule, x_s, units=units) if x_s is not None else None
    else:
        lines["dsr_vs0"] = lines["psr_vs_S"] = None
    alt = 1.0 if f != 1.0 else n.N_eff
    return {
        "card_id": card["card_id"], "card_class": card["class"], "family_id": ledger.family_id,
        "f": f, "f_at_1": 1.0, "f_at_neff": n.N_eff, "f_by_reading": sel["readings"], "acceptance_f": acceptance_f,
        "selection_factor": {"value": f, "rule": "computed_by_step3", "alt_value": alt},
        "dsr_at_1": dsr_at_1, "dsr_at_neff": dsr_at_neff,
        "n_raw": n_raw, "n_eff": n.N_eff, "n_by_reading": sel["n_eff"],
        "verdict_contrib": contrib, "fixed_at": fixed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fail_closed": fail_closed, "printed": lines,
    }


# --------------------------------------------------------------------------- #
# Revisions: adoption of a package counts as one revision, never a row (L4820; brief F-23)
# --------------------------------------------------------------------------- #
def bump_revision(header: Mapping, reason: str) -> dict:
    """A copy of the header with `revision` + 1 and the reason appended to `revision_reasons` (a counted
    revision: a class/claim change, an R-30 estimator switch, a package adoption). Never a ledger row and
    never N (L2446)."""
    out = dict(header)
    out["revision"] = int(header.get("revision", 1)) + 1
    out["revision_reasons"] = list(header.get("revision_reasons", ())) + [reason]
    return out


def record_adoption(ledgers: Sequence[FamilyLedger], headers: Sequence[Mapping], *, governance_log: Path,
                    clock: Callable[[], datetime], version: str, definitions_md5: str, actor: str = "harness") -> dict:
    """Package adoption: one `package_freeze` governance event (the M0 appender), every header's revision
    incremented, and NO ledger row appended (asserted on every family). Returns {headers, row_md5, n_rows}.
    integration: called by gate_package.freeze() after a real acceptance pass; never on this machine."""
    from core.rules.governance import append_event
    before = {lg.family_id: lg.n_raw for lg in ledgers}
    event = {"kind": "package_freeze", "actor": actor, "key": "gate.package",
             "old": {"status": "NOT_FROZEN"}, "new": {"version": version, "definitions_md5": definitions_md5},
             "reason": f"gate package {version} adopted: one counted revision per family, no ledger row",
             "refs": [lg.family_id for lg in ledgers]}
    row_md5 = append_event(Path(governance_log), event, clock)
    bumped = [bump_revision(h, f"package_adoption:{version}") for h in headers]
    after = {lg.family_id: lg.n_raw for lg in ledgers}
    if after != before:
        raise LedgerRefused(f"adoption appended ledger rows: {before} -> {after}")
    return {"headers": bumped, "row_md5": row_md5, "n_rows": after}


# --------------------------------------------------------------------------- #
# Static guard (T-STEP3-02; gate.step3.forbidden)
# --------------------------------------------------------------------------- #
def forbidden_patterns() -> dict[str, re.Pattern]:
    """Regexes over docstring-free code: the design-effect shape `X / (1 + (X - 1) * Y)` in either operand
    order, the name of its author, and a revision count assigned to N. Built from pieces so this module's own
    code never matches itself."""
    one = r"1(?:\.0)?"
    paren_m1 = r"\(\s*\w+\s*-\s*" + one + r"\s*\)"
    design = (r"\b\w+\s*/\s*\(\s*" + one + r"\s*\+\s*(?:" + paren_m1 + r"\s*\*\s*[\w.]+|[\w.]+\s*\*\s*"
              + paren_m1 + r")\s*\)")
    return {
        "kish_design_effect": re.compile(design),
        # the name as a definition, an import or a call (a refusal predicate may name it in a local variable)
        "kish_name": re.compile(r"(?:\b(?:def|class|import|from)\s+\w*{0}|\b{0}\w*\s*\()".format("".join(["k", "ish"])),
                                re.IGNORECASE),
        "revision_count_as_N": re.compile(r"\b[nN]_?(?:raw|eff|equiv|clusters)\s*=\s*[^\n]*revision"),
    }


def strip_strings(code: str) -> str:
    """The code with every string constant blanked: the name pattern scans identifiers, not labels such as the
    section 10 item key `..._or_other_n_eff_rule` or `gate.step3.forbidden` entries."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node.value = ""
    return ast.unparse(tree)


def scan_forbidden(sources: Mapping[str, str]) -> list[str]:
    """`{label: code_text}` (docstrings and comments stripped) -> ["label: pattern" ...] for every hit; [] means
    no code path implements the Kish design effect or uses a revision count as N. The design-effect shape is
    searched in the whole code, the name in identifiers only."""
    hits = []
    for label, text in sources.items():
        names_only = strip_strings(text)
        for name, pattern in forbidden_patterns().items():
            if pattern.search(names_only if name == "kish_name" else text):
                hits.append(f"{label}: {name}")
    return hits


# --------------------------------------------------------------------------- #
# Research-phase seeds (section 9.5 L6020; TASK-M7-02): structure shipped, values from absent files are null
# --------------------------------------------------------------------------- #
SEED_COLUMNS = ("row_id", "source_file", "source_row", "market", "span", "run_utc", "params", "timing_class", "book",
                "cost", "results_md5", "difference_series", "comment")
SEED_VALUE_COLUMNS = ("span", "run_utc", "timing_class", "results_md5", "difference_series")


def load_seed(path: Path) -> list[dict]:
    """Rows of a `ledger_seed_<family>.csv` with `null` cells as None and `params` parsed; refuses a wrong header.
    A seed row becomes a ledger row only through `register_trial` once the harness has regenerated its values
    from the reference files (R2-C1); a row with a null value column is not registrable (REFDATA)."""
    import csv
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != SEED_COLUMNS:
            raise LedgerRefused(f"{Path(path).name}: header must be {','.join(SEED_COLUMNS)}")
        rows = []
        for raw in reader:
            row = {k: (None if (v or "").strip() in ("", "null") else v.strip()) for k, v in raw.items()}
            if row["params"] is not None:
                row["params"] = json.loads(row["params"])
            if row["cost"] is not None:
                row["cost"] = float(row["cost"])
            rows.append(row)
    ids = [r["row_id"] for r in rows]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        raise LedgerRefused(f"{Path(path).name}: row ids must be unique and non-empty")
    return rows


def seed_missing(rows: Sequence[Mapping]) -> list[str]:
    """Row ids whose value columns are still null (the REFDATA reason of the seed tests)."""
    return [r["row_id"] for r in rows if any(r.get(c) is None for c in SEED_VALUE_COLUMNS)]


def temp_copy(ledger: FamilyLedger, directory: Path | None = None) -> FamilyLedger:
    """A temporary copy for test runs (T-HERM-02): the production ledger is never written by a test."""
    tmp = Path(directory) if directory else Path(tempfile.mkdtemp(prefix="ledger_"))
    dst = tmp / ledger.path.name
    if ledger.path.exists():
        dst.write_bytes(ledger.path.read_bytes())
    return FamilyLedger(dst, ledger.family_id)
