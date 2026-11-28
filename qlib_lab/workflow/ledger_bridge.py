"""Bridge from qlib_lab experiments to `core.quant.gate_ledger` hash-chained FamilyLedger & N_eff."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.ficc.macro_schema import canonical_json, md5_hex
from core.isolation import checked_target, refuse_quantgen
from core.quant import gate_ledger
from qlib_lab import RESEARCH_FLAGS, sha256_hex


@dataclass(frozen=True)
class FamilyMultiplicitySummary:
    """Cumulative trial multiplicity state for a hypothesis family."""

    family_id: str
    config_id: str
    appended: bool
    row_md5: str
    ledger_hash: str
    n_raw: int
    n_clusters: int
    n_equiv: float
    n_eff: float
    rho_bar: float
    corr_available: bool
    corr_note: str
    research_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "config_id": self.config_id,
            "appended": self.appended,
            "row_md5": self.row_md5,
            "ledger_hash": self.ledger_hash,
            "n_raw": self.n_raw,
            "n_clusters": self.n_clusters,
            "n_equiv": self.n_equiv,
            "n_eff": self.n_eff,
            "rho_bar": self.rho_bar,
            "corr_available": self.corr_available,
            "corr_note": self.corr_note,
            "research_flags": dict(RESEARCH_FLAGS),
            **RESEARCH_FLAGS,
        }


def save_dated_diff_series(diff_dir: Path, series: pd.Series, *, prefix: str = "diff") -> str:
    """Persist a dated OOS return/loss-difference Series as zero-pickle NPZ + JSON dates."""
    refuse_quantgen(diff_dir, "diff_series_dir")
    diff_dir.mkdir(parents=True, exist_ok=True)

    clean_s = series.dropna().astype(np.float64)
    if isinstance(clean_s.index, pd.DatetimeIndex):
        dates = clean_s.index.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()
    else:
        dates = [str(x) for x in clean_s.index.tolist()]
    vals = np.ascontiguousarray(clean_s.to_numpy(dtype=np.float64))

    digest = hashlib.sha256(
        json.dumps({"dates": dates, "vals": [round(float(x), 12) for x in vals]}, sort_keys=True).encode("ascii")
    ).hexdigest()[:24]
    ref_name = f"{prefix}_{digest}"

    npz_path = checked_target(diff_dir / f"{ref_name}.npz", "diff_npz", within=diff_dir)
    idx_path = checked_target(diff_dir / f"{ref_name}.dates.json", "diff_dates", within=diff_dir)

    with npz_path.open("wb") as fh:
        np.savez_compressed(fh, values=vals)
    idx_payload = {"dates": dates, "npz_sha256": sha256_hex(npz_path.read_bytes())}
    idx_path.write_bytes((json.dumps(idx_payload, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii"))
    return ref_name


def load_dated_diff_series(diff_dir: Path, ref_name: str) -> pd.Series:
    """Load a dated OOS difference series saved by save_dated_diff_series (`allow_pickle=False`)."""
    npz_path = checked_target(diff_dir / f"{ref_name}.npz", "diff_npz", within=diff_dir)
    idx_path = checked_target(diff_dir / f"{ref_name}.dates.json", "diff_dates", within=diff_dir)
    meta = json.loads(idx_path.read_text(encoding="utf-8"))
    if meta.get("npz_sha256") != sha256_hex(npz_path.read_bytes()):
        raise ValueError(f"Tampered difference series NPZ {ref_name!r}")
    with np.load(npz_path, allow_pickle=False) as archive:
        vals = archive["values"].copy()
    return pd.Series(vals, index=pd.Index(meta["dates"]), dtype=np.float64)


def compute_family_multiplicity(
    ledger: gate_ledger.FamilyLedger,
    diff_dir: Path,
    *,
    draws: int = 25_000,
    seed: int = gate_ledger.SEED,
) -> tuple[int, int, float, float, float, bool, str]:
    """Compute `(n_raw, n_clusters, n_equiv, n_eff, rho_bar, corr_ok, note)` across all rows in `ledger`."""
    rows = ledger.rows()
    n_raw = len(rows)
    if n_raw == 0:
        return 0, 0, 1.0, 1.0, 0.0, True, "empty_ledger"

    def _loader(ref: str) -> pd.Series:
        return load_dated_diff_series(diff_dir, ref)

    try:
        series_map = ledger.difference_series(_loader, rows)
        res = gate_ledger.n_eff(series_map, draws=int(draws), seed=int(seed))
        return (
            int(res.N_raw),
            int(res.N_clusters),
            float(res.N_equiv),
            float(res.N_eff),
            float(res.rho_bar),
            True,
            "ok",
        )
    except gate_ledger.CorrUnavailable as exc:
        # Fail-closed conservative bound matching gate_ledger.step3 (CARD-P fallback: N_eff = max(n_raw, 1))
        conservative = float(max(n_raw, 1))
        return n_raw, max(n_raw, 1), conservative, conservative, 0.0, False, str(exc)


def register_trial_and_compute_neff(
    *,
    ledger_dir: Path,
    family_id: str,
    rule: str,
    params: Mapping[str, Any],
    span: tuple[str, str] | list[str],
    market: str,
    run_utc: str,
    diff_series: pd.Series,
    delta_sr: float | None = None,
    results_payload: Mapping[str, Any] | None = None,
    script: str = "qlib_lab.workflow",
    run_kind: str = "trial",
    timing_class: str = "COMPLIANT",
    phase: str = "research",
    instrument_book: str | None = None,
    cost: float | None = None,
    draws: int = 25_000,
    seed: int = gate_ledger.SEED,
) -> FamilyMultiplicitySummary:
    """Append a trial to `<ledger_dir>/<family_id>.jsonl`, verify hash chain, and return cumulative N_eff."""
    refuse_quantgen(ledger_dir, "ledger_dir")
    ledger_dir = Path(ledger_dir)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    diff_dir = ledger_dir / "diff_series"

    diff_ref = save_dated_diff_series(diff_dir, diff_series, prefix=family_id)
    res_md5 = md5_hex(canonical_json(dict(results_payload))) if results_payload is not None else md5_hex(diff_ref)

    row: dict[str, Any] = {
        "rule": str(rule),
        "params": dict(params),
        "timing_class": timing_class,
        "span": [str(span[0])[:10], str(span[1])[:10]],
        "market": str(market),
        "run_utc": str(run_utc),
        "phase": phase,
        "script": str(script),
        "diff_series_ref": diff_ref,
        "results_md5": res_md5,
        "delta_sr": float(delta_sr) if (delta_sr is not None and np.isfinite(delta_sr)) else None,
        "run_kind": run_kind,
        "run_utc_anchor": gate_ledger.repo_anchor(),
        "instrument_book": instrument_book,
        "cost": float(cost) if cost is not None else None,
    }

    ledger = gate_ledger.family_ledger(family_id, ledger_dir)
    reg_res = gate_ledger.register_trial(ledger, row)
    check = ledger.verify_chain()
    if not check.ok:
        raise gate_ledger.LedgerRefused(
            f"FamilyLedger {family_id} chain verification failed at line {check.first_bad_line}: {check.reason}"
        )

    l_hash = ledger.hash()
    n_raw, n_clust, n_eq, n_effective, rho_bar, corr_ok, note = compute_family_multiplicity(
        ledger, diff_dir, draws=draws, seed=seed
    )
    return FamilyMultiplicitySummary(
        family_id=family_id,
        config_id=str(reg_res.row["config_id"]),
        appended=bool(reg_res.appended),
        row_md5=str(reg_res.row_md5),
        ledger_hash=l_hash,
        n_raw=n_raw,
        n_clusters=n_clust,
        n_equiv=n_eq,
        n_eff=n_effective,
        rho_bar=rho_bar,
        corr_available=corr_ok,
        corr_note=note,
        research_flags=dict(RESEARCH_FLAGS),
    )
