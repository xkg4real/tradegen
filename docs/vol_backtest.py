"""B5 rerun on local vendor closes (R-30 rule 8; R-06 estimator row "B5 kept"; TASK-M3-03; backlog BL-G01 residual).

SMOKE / VENDOR DATA. Inputs are the Yahoo auto-adjusted close caches `docs/asset_expansion/cache/yf_SPY.csv` and
`yf_069500.KS.csv` (KODEX 200), each with its last row dropped (an intraday print, M1 T-FIX-01). They are not official
closes and not the frozen fixtures of G-B5-01..03 (`^KS11`, frozen SPY, the French Mkt-RF splice), so every line is
labelled SMOKE and nothing here is a golden assertion or a card run (rulings section 1). When a fixture of
`tests/fixtures/macro/MANIFEST.csv` is present its lines are added, labelled FIXTURE.

Sections written to `docs/vol_backtest/results.csv` (one row per line) and `manifest.json` (run, seed, mode, input
md5s, results md5):
  (a) the app's own study form: GARCH(1,1)-t (and GJR-t with --full) t-quantile VaR, trailing window 504, refit 21
      (--full: refit 7, the study's setting) from 2012-01-01 via `core.crypto.analytics.garch_scorecard`; the app's
      stored PIT p is a Kolmogorov-Smirnov p, the B5 rule is chi-square on 10 bins: both are printed (brief F-15);
  (c) SMA20 and EWMA(0.94) in FHS form and in normal form, origins from 2016-03-01 (residual pool from the earlier
      history), the section 9.3 G-B5 shape; with --full the expanding GARCH-t FHS line of `core.quant.vol_estimators`;
  (d) the G-B5-01..03 fixture lines when the fixtures exist, else NOT_RUN rows naming the file (REFDATA).
Seed 11 (`seed_study`). Offline: no provider module is imported. Runs in about one minute in the default mode.
`incumbent_b5_status(rows)` exposes the SMA20 FHS status per market for R-21's estimator-calibration cap (wired M7).
A sigma is never displayed as a normal-quantile VaR: the normal-form rows exist as the printed disclosure only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np                                                  # noqa: E402

from core.quant import forecast_eval as F                           # noqa: E402
from core.quant import validate as V                                # noqa: E402
from core.quant import vol_estimators as E                          # noqa: E402

SEED = 11
CACHE = ROOT / "docs" / "asset_expansion" / "cache"
OUT = ROOT / "docs" / "vol_backtest"
LABEL = "SMOKE: Yahoo auto-adjusted vendor closes, last row dropped; not an official close, not a card run"
SYMBOLS = {"SPY": ("yf_SPY.csv", "US"), "KODEX200": ("yf_069500.KS.csv", "KR")}
FIXTURES = {"G-B5-01": ("yahoo_KS11_1996-12_2026-10-02.csv", "KR"), "G-B5-02": ("yahoo_SPY_2015-12_2026-10-01.csv", "US"),
            "G-B5-03": ("U1: French Mkt-RF 1990-02 -> 2026-08 + ^GSPC Sep-2026 splice (alias, no file)", "US")}
ORIGINS_FROM = "2016-03-01"
COLUMNS = ("section", "symbol", "market", "model", "form", "window", "refit", "sample", "n_origins", "exceedance",
           "band_lo", "band_hi", "pit_chi2_p", "pit_ks_p", "kupiec_p", "cc_p", "b5_status", "label")


def md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_closes(name: str) -> tuple[list[str], np.ndarray]:
    """Dates and closes of a cache file with its last (intraday) row dropped."""
    with (CACHE / name).open(encoding="utf-8", newline="") as fh:
        rows = [(d, float(v)) for d, v in csv.reader(fh) if d != "Date" and v not in ("", "nan")]
    rows = rows[:-1]
    return [d for d, _ in rows], np.asarray([v for _, v in rows], dtype=float)


def _row(section, symbol, market, model, form, window, refit, sample, ev: dict, label=LABEL) -> dict:
    lo, hi = ev.get("band", (float("nan"), float("nan")))
    return {"section": section, "symbol": symbol, "market": market, "model": model, "form": form, "window": window,
            "refit": refit, "sample": sample, "n_origins": ev.get("n_origins", 0), "exceedance": ev.get("exceedance"),
            "band_lo": lo, "band_hi": hi, "pit_chi2_p": ev.get("pit_chi2_p"), "pit_ks_p": ev.get("pit_ks_p"),
            "kupiec_p": (ev.get("kupiec") or {}).get("p"), "cc_p": (ev.get("christoffersen") or {}).get("p_cc"),
            "b5_status": ev.get("status", "NOT_RUN"), "label": label}


def _status(n: int, in_band: bool, chi2_p: float) -> str:
    if n < F.MIN_ORIGINS:
        return "NOT_RUN"
    return "PASS" if (in_band and chi2_p >= F.PIT_P_MIN) else "FAIL"


def app_form(dates, closes, market: str, symbol: str, *, model: str, window: int = 504, refit: int = 21) -> dict:
    """(a) the app's rolling t-quantile scorecard from 2012-01-01 (`docs/asset_expansion_study.run_garch`)."""
    from core.crypto.analytics import garch_scorecard
    keep = [i for i, d in enumerate(dates) if d >= "2012-01-01"]
    ds, px = tuple(dates[i] for i in keep), closes[keep]
    sc = garch_scorecard(ds, px, window=window, refit=refit, model=model)
    hits = sc.hits95
    n = int(hits.size)
    pit = V.pit_tests(sc.pit)
    exceed = float(hits.mean())
    lo, hi = F.band(n)
    ev = {"n_origins": n, "exceedance": exceed, "band": (lo, hi), "pit_chi2_p": pit["chi2_p"], "pit_ks_p": pit["ks_p"],
          "kupiec": V.kupiec(hits, 0.05), "christoffersen": V.christoffersen(hits, 0.05),
          "status": _status(n, lo <= exceed <= hi, pit["chi2_p"])}
    return _row("a_app_form", symbol, market, model, "t_quantile", window, refit, f"{ds[0]}..{ds[-1]}", ev)


def spec_form(dates, closes, market: str, symbol: str, *, full: bool = False) -> list[dict]:
    """(c) SMA20 and EWMA(0.94) in FHS and normal form on origins from ORIGINS_FROM (section 9.3 G-B5 shape)."""
    r = closes[1:] / closes[:-1] - 1.0
    rd = dates[1:]
    start = next((i for i, d in enumerate(rd) if d >= ORIGINS_FROM), None)
    rows = []
    sample = f"{ORIGINS_FROM}..{rd[-1]} (pool from {rd[0]})"
    fcs = {"sma20": E.sma(r, 1), "ewma094": E.ewma(r, 1, 0.94)}
    if full:
        fcs["garch_t_expanding"] = E.garch_t(r, 1, min_years=2, refit_every=21)
    for name, fc in fcs.items():
        sig = np.sqrt(np.where(fc.ok & (fc.var > 0), fc.var, np.nan))
        for form in ("fhs", "normal"):
            ev = F.b5(r, sig, form=form, origins_from=start)
            rows.append(_row("c_spec_form", symbol, market, name, form, "expanding" if "garch" in name else (20 if name == "sma20" else "0.94"),
                             21 if "garch" in name else "-", sample, ev))
    return rows


def fixture_lines() -> list[dict]:
    """(d) the G-B5 fixture reproductions, NOT_RUN with the file name until the fixtures are listed in the manifest."""
    from tests.notrun import NotRun, require_fixture
    rows = []
    for gid, (name, market) in FIXTURES.items():
        try:
            path = require_fixture(name)
        except (NotRun, ValueError) as exc:
            rows.append(_row("d_fixture", gid, market, "sma20", "fhs", 20, "-", name, {"status": "NOT_RUN"},
                             label=f"REFDATA: {getattr(exc, 'reason', exc)}"))
            continue
        with path.open(encoding="utf-8", newline="") as fh:
            data = [(row["obs_date"], float(row["value"])) for row in csv.DictReader(fh) if row.get("value")]
        dates, closes = [d for d, _ in data], np.asarray([v for _, v in data], dtype=float)
        rows += [dict(x, label=f"FIXTURE {gid}: {name}") for x in spec_form(dates, closes, market, gid)]
    return rows


def run(*, full: bool = False, out: Path = OUT, run_date: str = "unset", symbols=SYMBOLS) -> list[dict]:
    rows, inputs = [], {}
    models = ("garch_t", "gjr_t") if full else ("garch_t",)
    refit = 7 if full else 21
    for symbol, (name, market) in symbols.items():
        if not (CACHE / name).is_file():
            rows.append(_row("a_app_form", symbol, market, "-", "-", "-", "-", name, {"status": "NOT_RUN"},
                             label=f"REFDATA: {name} absent from docs/asset_expansion/cache"))
            continue
        inputs[name] = md5_file(CACHE / name)
        dates, closes = load_closes(name)
        for model in models:
            rows.append(app_form(dates, closes, market, symbol, model=model, refit=refit))
        rows += spec_form(dates, closes, market, symbol, full=full)
    rows += fixture_lines()
    write(rows, out, inputs=inputs, run_date=run_date, mode="full" if full else "quick")
    return rows


def incumbent_b5_status(rows: list[dict]) -> dict:
    """market -> SMA20 FHS B5 status of the smoke run (R-21's estimator-calibration cap reads the formal line at M7)."""
    return {r["market"]: r["b5_status"] for r in rows if r["section"] == "c_spec_form" and r["model"] == "sma20" and r["form"] == "fhs"}


def write(rows: list[dict], out: Path, *, inputs: dict, run_date: str, mode: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    text = ",".join(COLUMNS) + "\n" + "".join(
        ",".join("" if r.get(c) is None else (f"{r[c]:.6g}" if isinstance(r[c], float) else str(r[c]).replace(",", ";"))
                 for c in COLUMNS) + "\n" for r in rows)
    _atomic(out / "results.csv", text)
    manifest = {"run": run_date, "seed": SEED, "mode": mode, "label": LABEL, "read_only": True,
                "inputs_md5": inputs, "results_md5": hashlib.md5(text.encode("utf-8")).hexdigest(),
                "incumbent_b5_status": incumbent_b5_status(rows), "origins_from": ORIGINS_FROM,
                "b5_rule": "5% VaR exceedance within +-2 binomial SE over >= 200 origins and PIT chi2 (10 bins) p >= 0.01",
                "note": "SMOKE on vendor closes; the G-B5 goldens stay NOT_RUN until the fixtures are listed"}
    _atomic(out / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return out


def _atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--full", action="store_true", help="refit 7, GJR-t and the expanding GARCH-t FHS line (several minutes)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    rows = run(full=args.full, out=Path(args.out), run_date=date.today().isoformat())   # CLI entry only (ruling 3.11)
    for r in rows:
        ex = "" if r["exceedance"] is None or not math.isfinite(r["exceedance"]) else f"{100 * r['exceedance']:.2f}%"
        print(f"{r['section']:<12} {r['symbol']:<9} {r['model']:<18} {r['form']:<10} n={r['n_origins']:<5} {ex:>7} "
              f"chi2 p={r['pit_chi2_p'] if r['pit_chi2_p'] is None else round(r['pit_chi2_p'], 4)!s:<8} {r['b5_status']:<8} {r['label'][:60]}")
    print("incumbent SMA20 FHS B5:", incumbent_b5_status(rows), "->", Path(args.out) / "results.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
