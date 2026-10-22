"""Pre-registration of the GROKTEAM BOOK desk (grokteam.book), frozen once before its forward window opens.

    python -m grokteam.prereg --freeze     # writes grokteam/out/PREREG_book.json; refused after book.FREEZE_BY
    python -m grokteam.prereg              # lists what changed since the freeze (nothing, if the test still stands)

The record holds the hypotheses, every threshold the readout applies (book.VERDICT), the rules and accounts, the
logistic recalibration fitted on the whole archive by the latest full `python -m grokteam.book` run (refused unless
that run used exactly the code being frozen), the sha256 of the BOOK files and of every QUANTGEN file the desk calls
(byte copies in grokteam/out/frozen_book/, so a changed file can be restored), the numpy/scipy/pandas versions, its
trial-ledger rows and the events seen while designing. An identical re-freeze is a no-op and a different one is
refused. The forward window is every event whose decision
falls after `frozen_utc` and whose close is before book.FORWARD_END; it is read once, by the first run of
grokteam.book on or after that date, and never extended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grokteam import book as B  # noqa: E402

# The code the BOOK desk runs: its own files, then QUANTGEN's GARCH fit and forecast, the forecast tests (and validate
# under them), Holm, the ledger, the Binance client and the HTTP session. Other grokteam desks are not pinned.
BOOK_FILES = ("grokteam/__init__.py", "grokteam/book.py", "grokteam/prereg.py")
FROZEN_COPY = B.PREREG.parent / "frozen_book"
QUANTGEN_FILES = ("core/quant/garch.py", "core/quant/forecast_eval.py", "core/quant/validate.py",
                  "core/quant/gate_stats.py", "core/quant/gate_ledger.py", "data/crypto/crypto_client.py",
                  "data/net.py")

HYPOTHESES = dict(
    sample=f"every KXBTCD event whose decision (close - 30 min) is after frozen_utc and whose close is before "
           f"{B.FORWARD_END}; blinded (fetched, never replayed) until then; one look, by the first full grokteam.book "
           f"run at or after {B.FORWARD_END} 01:00 UTC with every forward event fetched, written once to "
           f"out/book/FORWARD_LOOK.json; never extended",
    unit="net return per $ of premium (fee included) of each bet on the fixed $60 shadow book; the $1,000 path is "
         "reported, not tested",
    model="GARCH(1,1)-t (core.quant.garch.fit_garch) on the last 2,000 hourly BTCUSDT log returns divided by their "
          "hour-of-day x weekend RMS, fed at x 0.01. An event's model is skipped (and counted toward max_skip) on a "
          "parameter bound (alpha, beta, omega, nu), a missing last bar, or a fit that did not converge UNLESS it "
          "carries garch.py's 'stationarity' flag (alpha + beta > 0.995): such fits are used. On the 2026 archive "
          "these were mostly stops on the 0.9995 penalty wall, plus a minority of interior stalls between 0.9967 "
          "and 0.9989 whose sigma lies within 0.93-1.06x of a refit with the cap relaxed (owner's ruling "
          "2026-10-22, before the freeze)",
    H_B0_skill="each model account's probability beats the market mid: per-event mean log loss (model - mid) on the "
               "scored strikes, Diebold-Mariano (forecast_eval.dm_test), t < 0 and two-sided p / 2 <= skill_p. "
               "PRED-GATED is scored with p_cal (the frozen calibration), PRED-LIT8 with p_raw. A fail is REJECT "
               "for that account whatever its P&L",
    H_B1_gated="PRED-GATED (the guide's BOOK with QUANTGEN's calibrated GARCH-t and a 2x-fee binary cost gate) "
               "earns more than 0 per $",
    H_B2_lit8="PRED-LIT8 (the guide as written: 8-point gap on the raw model) earns more than 0 per $",
    H_B3_flb="PRED-FLB (no model: the favourite nearest 93c) earns more than 0 per $",
    test="mean per-bet return, cluster-robust SE over 5-day UTC blocks, one-sided p from t(G - 1); Holm across the "
         "three accounts at holm_alpha",
    nulls="model accounts must beat the coin-flip side on the same strike (paired, p <= null_p); PRED-GATED must "
          "also beat PRED-FLB on 5-day block means (p <= null_p); NB0 (the market mid as forecast) is the skill bar",
    verdicts="REJECT: skill failed, or the 90% interval lies below 0. PAPER-CANDIDATE: Holm p <= holm_alpha, the "
             "90% interval above 0, the 2x-fee + 1-cent stress mean above 0, and the nulls beaten. INVALID: model "
             "skip rate above max_skip. Else INCONCLUSIVE. Reported with every verdict, never gated: MDE = "
             "mde_factor x sd / sqrt(n) and N* = ceil((mde_factor x sd / target_edge)^2) (at the 1% target the "
             "forward window cannot reach N*). validate.GATE is not run: it needs five years, so PAPER-CANDIDATE "
             "is the ceiling",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_digests() -> dict:
    return {f: sha(ROOT / f) for f in BOOK_FILES + QUANTGEN_FILES}


def versions() -> dict:
    import numpy, pandas, scipy
    return dict(python=sys.version.split()[0], numpy=numpy.__version__, scipy=scipy.__version__, pandas=pandas.__version__)


def _same_versions(a: dict | None, b: dict) -> bool:
    """Libraries exactly; Python on major.minor only: the Microsoft Store interpreter updates its patch level by
    itself, which changes no result here, while a numpy/scipy/pandas upgrade can move an optimiser."""
    cut = lambda v: {**v, "python": ".".join(str(v.get("python", "")).split(".")[:2])}   # noqa: E731
    return bool(a) and cut(a) == cut(b)


def _norm(x):
    return json.loads(json.dumps(x, sort_keys=True, default=str))


def record() -> dict:
    """What the freeze fixes; the archive calibration comes from the latest full book run on disk."""
    summary = B.OUT / "summary.json"
    if not summary.exists():
        raise SystemExit("run `python -m grokteam.book` on the full archive first: the freeze needs its calibration")
    s = json.loads(summary.read_text(encoding="utf-8"))
    cal = (s.get("calibration") or {}).get("archive")
    if s.get("smoke") or not cal:
        raise SystemExit(f"{summary} is a smoke run or has no archive calibration; run the full archive first")
    code = code_digests()
    if s.get("code") != code or s.get("model_digest") != B.model_digest():
        raise SystemExit(f"{summary} was produced by different code; rerun `python -m grokteam.book` and freeze then")
    return _norm(dict(hypotheses=HYPOTHESES, rules=B.RULES, accounts=B.ACCOUNTS, verdict=B.VERDICT,
                      windows=dict(archive_start=B.ARCHIVE_START, cal_end=B.CAL_END, forward_end=B.FORWARD_END),
                      calibration=cal, calibration_run_utc=s.get("run_utc"), model_digest=B.model_digest(),
                      code=code, versions=versions(), seen=sorted(B.SEEN), family=B.FAMILY, guide=B.GUIDE))


def freeze(now: datetime | None = None, ledger_dir: Path | None = None) -> dict:
    """Write PREREG_book.json once and register the three trial rows (rehearsed on a temporary copy of the ledger
    first). Refused after FREEZE_BY: forward events may already have been looked at."""
    from core.quant import gate_ledger as GL
    rec = record()
    if B.PREREG.exists():
        old = json.loads(B.PREREG.read_text(encoding="utf-8"))
        if {k: old.get(k) for k in rec} != rec:
            raise SystemExit(f"{B.PREREG} already holds a different record; a frozen record is not rewritten")
        return old
    now = now or datetime.now(timezone.utc)
    if now.date().isoformat() > B.FREEZE_BY:
        raise SystemExit(f"too late to freeze: it is after {B.FREEZE_BY}")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        B.register_trials(ledger_dir=Path(tmp))                # rehearsal: every row must validate
    import config as QC
    d = Path(ledger_dir or QC.macro_dir() / "ledgers")
    if (d / f"{B.FAMILY}.jsonl").exists():                     # the real ledger must verify before it is appended to
        GL.family_ledger(B.FAMILY, d).rows()
    reg = B.register_trials(ledger_dir=d)
    import shutil
    for f in rec["code"]:                                     # byte copies: a VOID is undone by restoring them
        (FROZEN_COPY / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, FROZEN_COPY / f)
    rec.update(frozen_utc=now.isoformat(timespec="seconds"),
               ledger=[dict(account=r.row["params"]["account"], config_id=r.row["config_id"], appended=r.appended)
                       for r in reg])
    B.PREREG.parent.mkdir(parents=True, exist_ok=True)
    B.PREREG.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def check(frozen: dict | None = None) -> list[str]:
    """What differs from the frozen record: code files, rules, accounts, verdict thresholds, model digest, library
    versions (Python on major.minor). A non-empty list voids the forward look until it is undone: changed files by
    restoring grokteam/out/frozen_book, a library by reinstalling the version in the record."""
    frozen = frozen or B.frozen()
    if not frozen:
        return ["not frozen"]
    now = _norm(dict(rules=B.RULES, accounts=B.ACCOUNTS, verdict=B.VERDICT, model_digest=B.model_digest()))
    out = [k for k in now if frozen.get(k) != now[k]]
    if not _same_versions(frozen.get("versions"), versions()):
        out.append("versions")
    code = code_digests()
    out += [f for f in sorted(set(code) | set(frozen["code"])) if code.get(f) != frozen["code"].get(f)]
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="GROKTEAM BOOK pre-registration")
    ap.add_argument("--freeze", action="store_true")
    a = ap.parse_args(argv)
    if a.freeze:
        rec = freeze()
        print(f"frozen {rec['frozen_utc']}: {len(rec['code'])} files pinned, ledger "
              + ", ".join(f"{x['account']} {x['config_id'][:8]}" for x in rec["ledger"]))
    else:
        diff = check()
        print("unchanged since the freeze" if not diff else "changed since the freeze: " + ", ".join(diff))


if __name__ == "__main__":
    main()
