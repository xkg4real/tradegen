"""Quant Lab out-of-sample 2016-26 grading run (R-16 rule (3); I-11; TASK-M9-02; section 12 M9).

The formal run grades the envelope max(fast FHS, GJR-EVT) on the KOSPI fixture (official closes from 2005 or earlier
through 2026-10-02) and REFUSES without it: `NotRun("REFDATA: ...")` naming the fixture, exit 2, nothing written.
No vendor substitute is ever asserted against the I-11 thresholds.

`--smoke` is a labelled dry run on the local vendor closes (`docs/asset_expansion/cache/yf_069500.KS.csv` KODEX 200
from 2007-01-29, `yf_SPY.csv`), each with its last (intraday) row dropped: SMOKE / VENDOR DATA, not an official close,
not the fixture (KODEX 200 reaches ten years only in 2017, so its "2016-26" line cannot start in 2016), not a card run
(rulings section 1). Its verdict is printed as a labelled line and gates nothing.

Outputs: `docs/quant_lab/<symbol>.json` (the report, `lab.grade_to_json`) and `docs/quant_lab/manifest.json`
(run, label, seed, config_hash, input md5s, results_md5 over the canonical JSON). Seed 11 (`seed_study`).
Offline: no provider module is imported; no clock is read (knowledge_utc = the last close in the file).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np                                                  # noqa: E402

from core.ficc.macro_schema import canonical_json                   # noqa: E402
from core.quant import lab                                          # noqa: E402

SEED = lab.SEED
CACHE = ROOT / "docs" / "asset_expansion" / "cache"
OUT = ROOT / "docs" / "quant_lab"
LABEL = ("SMOKE: VENDOR DATA — Yahoo auto-adjusted closes (docs/asset_expansion/cache), last row dropped; "
         "not an official close, not the I-11 KOSPI fixture, not a card run; gates nothing")
SYMBOLS = {"KODEX200": ("yf_069500.KS.csv", "KR"), "SPY": ("yf_SPY.csv", "US")}
# F01 official closes first, F13 the Yahoo ^KS11 fixture as the frozen vendor alternative (both manifest-listed only).
KOSPI_FIXTURES = ("krx_kospi_official_close_1997-01-03_2026-10-02.csv", "yahoo_KS11_1996-12_2026-10-02.csv")


def md5_file(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_closes(name: str) -> tuple[list[str], np.ndarray]:
    """Dates and closes of a cache file with its last (intraday) row dropped."""
    with (CACHE / name).open(encoding="utf-8", newline="") as fh:
        rows = [(d, float(v)) for d, v in csv.reader(fh) if d != "Date" and v not in ("", "nan")]
    rows = rows[:-1]
    return [d for d, _ in rows], np.asarray([v for _, v in rows], dtype=float)


def config_hash() -> str:
    from core.rules.macro_rules import load_store
    return load_store().config_hash


def grade(symbol: str, market: str, dates, closes, *, label: str, refit_every: int = lab.REFIT_EVERY,
          cfg_hash: str | None = None, seed: int = SEED) -> dict:
    ctx = lab.LabContext(seed=seed, knowledge_utc=f"{dates[-1]}T23:59:59Z (last close in the file)", config_hash=cfg_hash,
                         package_version="quant_lab_grading 2.0", refit_every=refit_every, label=label)
    g = lab.grade_lab(market, (dates, closes), ctx)
    out = lab.grade_to_json(g)
    out.update(symbol=symbol, label=label)
    return out


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def run_smoke(*, out: Path = OUT, refit_every: int = lab.REFIT_EVERY, symbols=SYMBOLS, with_config_hash: bool = True) -> dict:
    cfg = config_hash() if with_config_hash else None
    reports, inputs = {}, {}
    for symbol, (name, market) in symbols.items():
        dates, closes = load_closes(name)
        inputs[name] = md5_file(CACHE / name)
        reports[symbol] = grade(symbol, market, dates, closes, label=LABEL, refit_every=refit_every, cfg_hash=cfg)
    results_md5 = hashlib.md5(canonical_json(reports).encode("utf-8")).hexdigest()
    manifest = {"run": "smoke", "label": LABEL, "seed": SEED, "refit_every": refit_every, "config_hash": cfg,
                "inputs_md5": inputs, "results_md5": results_md5, "git_hash": lab.GIT_HASH,
                "verdicts": {s: f"{r['verdict']} ({LABEL.split(':')[0]}; gates nothing)" for s, r in reports.items()}}
    for symbol, rep in reports.items():
        _write(out / f"{symbol}.json", json.dumps(rep, indent=1, sort_keys=True))
    _write(out / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True))
    return manifest


def run_formal(*, out: Path = OUT, refit_every: int = lab.REFIT_EVERY) -> int:
    """The I-11 run: refuses (exit 2, nothing written) until a KOSPI fixture is manifest-listed."""
    from tests.notrun import NotRun, require_fixture
    reasons = []
    for name in KOSPI_FIXTURES:
        try:
            path = require_fixture(name)
            break
        except NotRun as exc:
            reasons.append(exc.reason)
    else:
        print("formal run refused (nothing written):")
        for why in reasons:
            print("   ", why)
        return 2
    with path.open(encoding="utf-8", newline="") as fh:
        data = [(row["obs_date"], float(row["value"])) for row in csv.DictReader(fh) if row.get("value")]
    dates, closes = [d for d, _ in data], np.asarray([v for _, v in data], dtype=float)
    label = f"FIXTURE {name}: I-11 out-of-sample 2016-26 grading (official closes); displayed, never acting"
    rep = grade("KOSPI", "KR", dates, closes, label=label, refit_every=refit_every, cfg_hash=config_hash())
    _write(out / "KOSPI.json", json.dumps(rep, indent=1, sort_keys=True))
    manifest = {"run": "formal", "fixture": name, "fixture_md5": md5_file(path), "seed": SEED, "config_hash": rep["repro"]["config_hash"],
                "results_md5": hashlib.md5(canonical_json(rep).encode("utf-8")).hexdigest(), "verdict": rep["verdict"]}
    _write(out / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True))
    print("M9 gate:", rep["verdict"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--smoke", action="store_true", help="labelled dry run on the local vendor closes")
    ap.add_argument("--refit-every", type=int, default=lab.REFIT_EVERY)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    if a.smoke:
        m = run_smoke(out=a.out, refit_every=a.refit_every)
        for s, v in m["verdicts"].items():
            print(f"{s}: {v}")
        print(LABEL)
        return 0
    return run_formal(out=a.out, refit_every=a.refit_every)


if __name__ == "__main__":
    sys.exit(main())
