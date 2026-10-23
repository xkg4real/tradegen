"""Context log, context isolation and the break protocol (R-13, R-18; P9, P19; TASK-M6-01..04).

Three things live here, all CONTEXT: nothing in this module changes a weight.

1. `build_context_log(store, registry, decision_utc, knowledge_utc, ...)` -> one `quantgen.context_log` 2.0 per
   decision (section 6.4). Every item carries `obs_date`, `available_at_utc`, `retrieved_at_utc`, `vintage` and
   `stale`; revised series carry `first_release`, `latest`, `vintage_date`; the 18 sheet indicators appear with
   `from_sheet: true` and a causal trailing z-score; the R-13 derived items (in-house Sahm with NaN across a gap,
   the Estrella-Trubin probit on GS10 - BEY(TB3MS), the Taylor residual min-max range, VRP, the KOSPI SMA10m trend
   state, rv21 and its 3-year percentile) are pure calculators over PIT reads (consumer "R-13"). A never-acquired
   series yields no item (never a fabricated date), a synthetic value is excluded and alerted, a raising calculator
   loses its own item only; `acts` is the constant false. A log that fails validation is quarantined and alerted,
   never a HALT (`write_context_log`).
2. Isolation (T-CTX-01/02): `assert_not_acting_caller()` guards every reader here; `static_isolation_report()`
   is the AST import scan over the acting modules (no import of this module, the sheet or a refusal book, no
   protected callee, no protected artifact path); `run_context_step()` runs a context writer so that no exception
   reaches the acting path (section 3.8 L1178, L3370).
3. R-18: `log_break()` is the append-only declared-event log; an official framework change neutralises every
   macro-conditioned multiplier to 1.0 (push through the `neutralise` hook; the apply side is
   `macro_artifacts.build_overlay_decisions(neutralised=...)`), writes one `record_reset` governance event per
   target and the forward-record marker; a policy-direction flip is not an event kind. The statistical flag
   (CUSUM), the v1.2 2x-median scale flag and the BOCPD run-length probability (hazard 1/250) go to a write-only
   research log that nothing reads. `sync_market_structure_breaks` turns regime-tag transitions into
   `market_structure` rows. `reanchor_eligible` is true only for a declared, calendar-dated event after the header
   commit on a card that is neither demoted nor inside an R-25 lockout.

No wall clock: `decision_utc`, `knowledge_utc`, `clock` (zero-arg, tz-aware) and every path are injected.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

from core.ficc import contracts as C
from core.ficc import macro_artifacts as MA
from core.ficc import pit as P
from core.ficc.macro_schema import canonical_json, md5_hex, validate
from core.quant.risk_layer import alert as _alert
from core.rules import governance as G

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_CONSUMER = "R-13"
SCHEMA = "quantgen.context_log"
Z_WINDOW = 252                                    # section 3.6 rule 2: trailing, causal, display only
BREAK_LOG = "r18_break_log.jsonl"
RESEARCH_LOG = "r18_research_log.jsonl"
FORWARD_RECORD_MARKER = "forward_record_start_requested.jsonl"
RUN_LOG = "run_log.jsonl"
BREAK_KINDS = ("policy_framework_change", "market_structure", "scale_reanchor")
REANCHOR_KINDS = ("market_structure", "policy_framework_change")
LETF_RULE_CHANGE = date(2026, 7, 16)             # R-13 leverage row: logged as a structural break
DESCRIPTIVE_READ_NOTE = "descriptive read — not a regime model (P19)"
ALERT_ITEM_ERROR = "CONTEXT_ITEM_ERROR"
ALERT_LOG_INVALID = "CONTEXT_LOG_INVALID"
ALERT_SYNTHETIC = "CONTEXT_SYNTHETIC_EXCLUDED"
ALERT_STEP_ERROR = "CONTEXT_STEP_EXCEPTION"
COMPONENT = "core/ficc/context_log"

# T-CTX-01 (single source of truth; the test imports these). The card harness under core.quant is included.
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",
                          "core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act
ACTING_EXEMPT = ("core.quant.refusal", "core.quant.insights")      # refusal legs are protected; insights is narrative
# The workflow orchestrator (M8) calls the context writers inside `run_context_step`, so it may import this module;
# it may never read a context value: the callee and path checks apply to it, the import ban does not.
ORCHESTRATOR_MODULES = ("core.skills.macro_daily", "core.skills.pipeline")
PROTECTED_MODULES = ("core.ficc.context_log", "core.ficc.macro", "core.quant.refusal", "core.ficc.flows_log")   # flows: DATA-6 context
PROTECTED_CALLEES = ("read_context_log", "load_break_log", "macro_sheet", "guarded_macro_sheet",
                     "refusal_krw_leg", "refusal_rates_leg")
PROTECTED_PATH_FRAGMENTS = ("context_log/", "r18_break_log", "r18_research_log")
BUILDER_FORBIDDEN = {"core.ficc.macro_artifacts": ("core.ficc.context_log", "core.ficc.macro")}
_REPO_TOPS = ("core", "data", "ui", "docs", "config", "main")


class ContextIsolationError(RuntimeError):
    """A context reader was called from an acting module (T-CTX-01 runtime guard)."""


# --------------------------------------------------------------------------- #
# Isolation: runtime guard and static scan (TASK-M6-03)
# --------------------------------------------------------------------------- #
def is_acting_module(name: str) -> bool:
    if any(name == e or name.startswith(e + ".") for e in ACTING_EXEMPT):
        return False
    return name.startswith(ACTING_MODULE_PREFIXES)


def assert_not_acting_caller() -> None:
    """Walk the call stack; raise when any frame belongs to an acting module."""
    f = sys._getframe(1)
    while f is not None:
        name = f.f_globals.get("__name__", "")
        if is_acting_module(name):
            raise ContextIsolationError(f"{name} reads a context surface (P9; T-CTX-01): refused")
        f = f.f_back


@dataclass(frozen=True)
class IsolationViolation:
    module: str
    kind: str          # import | callee | path | builder
    detail: str


def _skip(node: ast.If) -> bool:
    t = node.test
    if isinstance(t, ast.Name) and t.id == "TYPE_CHECKING":
        return True
    if isinstance(t, ast.Attribute) and t.attr == "TYPE_CHECKING":
        return True
    if isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__":
        return any(isinstance(c, ast.Constant) and c.value == "__main__" for c in t.comparators)
    return False


def _nodes(node):
    """Every node, skipping `if TYPE_CHECKING:` and `if __name__ == "__main__":` bodies (their orelse is kept)."""
    if isinstance(node, ast.If) and _skip(node):
        for child in node.orelse:
            yield from _nodes(child)
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _nodes(child)


def _resolve_relative(module: str, level: int, target: str | None) -> str:
    base = module.split(".")
    if not module.endswith(".__init__"):
        base = base[:-1]
    base = base[:len(base) - (level - 1)] if level > 1 else base
    return ".".join(base + ([target] if target else []))


def imports_of(module: str, source: str) -> tuple[set[str], set[str], set[str]]:
    """(imported module names at any depth, protected callee references, protected path strings)."""
    tree = ast.parse(source)
    imports, callees, paths = set(), set(), set()
    for n in _nodes(tree):
        if isinstance(n, ast.Import):
            imports.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            mod = _resolve_relative(module, n.level, n.module) if n.level else (n.module or "")
            imports.add(mod)
            imports.update(f"{mod}.{a.name}" for a in n.names)
        elif isinstance(n, ast.Name) and n.id in PROTECTED_CALLEES:
            callees.add(n.id)
        elif isinstance(n, ast.Attribute) and n.attr in PROTECTED_CALLEES:
            callees.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            paths.update(f for f in PROTECTED_PATH_FRAGMENTS if f in n.value)
    return imports, callees, paths


def repo_modules(root: Path = REPO_ROOT) -> dict[str, str]:
    """dotted module name -> source for core/, data/ and config.py (the repo-internal import graph)."""
    out = {}
    for top in ("core", "data"):
        for p in sorted((root / top).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            parts = list(p.relative_to(root).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            out[".".join(parts)] = p.read_text(encoding="utf-8", errors="replace")
    cfg = root / "config.py"
    if cfg.is_file():
        out["config"] = cfg.read_text(encoding="utf-8", errors="replace")
    return out


def scan_isolation(sources: Mapping[str, str]) -> list[IsolationViolation]:
    """The static half of T-CTX-01 over `sources` (name -> source). A module whose name matches
    ACTING_MODULE_PREFIXES (minus ACTING_EXEMPT) may not import a PROTECTED_MODULE directly or through the
    transitive closure of repo-internal imports, name a PROTECTED_CALLEE, or carry a protected artifact path.
    `core.ficc.macro_artifacts` may not import context_log or the sheet (BUILDER_FORBIDDEN)."""
    graph: dict[str, set[str]] = {}
    refs: dict[str, tuple[set[str], set[str]]] = {}
    for name, src in sources.items():
        try:
            imps, callees, paths = imports_of(name, src)
        except SyntaxError as exc:
            return [IsolationViolation(name, "syntax", str(exc))]
        graph[name] = {i for i in imps if i.split(".")[0] in _REPO_TOPS}
        refs[name] = (callees, paths)

    def closure(start: str) -> set[str]:
        seen, todo = set(), [start]
        while todo:
            m = todo.pop()
            for i in graph.get(m, ()):
                for cand in (i, i.rsplit(".", 1)[0] if "." in i else i):
                    if cand not in seen and (cand in graph or cand in PROTECTED_MODULES):
                        seen.add(cand)
                        todo.append(cand)
        return seen

    out = []
    for name in sorted(sources):
        forbidden = PROTECTED_MODULES if is_acting_module(name) else BUILDER_FORBIDDEN.get(name)
        if forbidden:
            hit = sorted(closure(name) & set(forbidden))
            if hit:
                out.append(IsolationViolation(name, "import" if is_acting_module(name) else "builder",
                                              "imports (directly or transitively) " + ", ".join(hit)))
        if is_acting_module(name) or name in ORCHESTRATOR_MODULES:
            callees, paths = refs[name]
            if callees:
                out.append(IsolationViolation(name, "callee", "references " + ", ".join(sorted(callees))))
            if paths:
                out.append(IsolationViolation(name, "path", "names " + ", ".join(sorted(paths))))
    return out


def static_isolation_report(root: Path = REPO_ROOT) -> list[IsolationViolation]:
    return scan_isolation(repo_modules(root))


def guarded_macro_sheet(**kw):
    """The 18-indicator sheet behind the runtime guard (the legacy display path; never an acting input)."""
    assert_not_acting_caller()
    from core.ficc.macro import macro_sheet
    return macro_sheet(**kw)


def read_context_log(path) -> dict:
    """Guarded reader for the Macro page and the brief (never an acting module)."""
    assert_not_acting_caller()
    return json.loads(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Isolation guard for the acting path (B.0; T-CTX-02 "never fails the acting path")
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ContextStepResult:
    name: str
    ok: bool
    value: object = None
    error: str | None = None
    alert: dict | None = None
    logged: bool = False
    log_error: str | None = None


def _append_line(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as fh:                    # append-only, binary; a failed write raises (rulings 5)
        fh.write(canonical_json(obj).encode("utf-8") + b"\n")
        fh.flush()
        os.fsync(fh.fileno())


def run_context_step(name: str, fn: Callable, *args, run_log=None, decision_utc: datetime | None = None,
                     clock: Callable[[], datetime] | None = None, **kw) -> ContextStepResult:
    """Run a context writer (`build_context_log`, `log_break`, the research-log writers, the structure sync).
    Every exception is caught, recorded in `run_log` (run_log.jsonl) and returned as a labelled result; nothing
    propagates into the acting path, no book counter moves (L1178, L3370, risk_layer.never_halt_on)."""
    try:
        return ContextStepResult(name, True, fn(*args, **kw))
    except Exception as exc:                        # noqa: BLE001  (the whole point: isolate the acting path)
        error = f"{type(exc).__name__}: {exc}"
        when = decision_utc or (clock() if clock else None)
        a = _alert(ALERT_STEP_ERROR, COMPONENT, when, severity="warn") if when else None
        logged, log_error = False, None
        if run_log is not None:
            try:
                _append_line(Path(run_log), {"step": name, "ok": False, "error": error, "class": "context",
                                             "halt": "never", "decision_utc": P.iso_utc(when) if when else None,
                                             "utc": P.iso_utc(clock()) if clock else None})
                logged = True
            except Exception as log_exc:            # noqa: BLE001  (a failed run-log write is reported, not raised)
                log_error = f"{type(log_exc).__name__}: {log_exc}"
        return ContextStepResult(name, False, None, error, a, logged, log_error)


# --------------------------------------------------------------------------- #
# Pure calculators (R-13 definitions column; brief B.2)
# --------------------------------------------------------------------------- #
def bond_equivalent(discount_pct: float) -> float:
    """Treasury-bill discount (pct, 91-day) -> bond-equivalent yield (pct): 365 d / (360 - 91 d). Not in the
    spec text; the Estrella-Trubin convention, supported by the spec's 0.744 (May-2023)."""
    d = discount_pct / 100.0
    return 100.0 * (365.0 * d) / (360.0 - 91.0 * d)


def recession_probit_et(gs10_pct: float, tb3ms_pct: float, alpha: float = -0.6045, beta: float = -0.7374) -> float:
    """P = Phi(alpha + beta x spread), spread = GS10 - BEY(TB3MS), monthly (R-13 L1679; context_log.probit)."""
    x = alpha + beta * (gs10_pct - bond_equivalent(tb3ms_pct))
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def taylor_residual_range(policy_pct: float, core_pce_yoy_pct: float, unrate: float, nrou: float, gdpc1: float,
                          gdppot: float, *, r_star=(0.5, 1.0, 2.0), a=(0.5, 1.0), pi_star: float = 2.0) -> tuple[float, float]:
    """EFFR minus R = r* + pi + 0.5 (pi - pi*) + a gap over 12 rules (3 r* x 2 gaps x 2 a); (min, max) only."""
    pi = core_pce_yoy_pct
    gaps = (2.0 * (nrou - unrate), 100.0 * (gdpc1 / gdppot - 1.0))          # okun_2x, cbo
    res = [policy_pct - (r + pi + 0.5 * (pi - pi_star) + ai * g) for r in r_star for g in gaps for ai in a]
    return (min(res), max(res))


def taylor_midpoint(lo: float, hi: float) -> float:
    return (lo + hi) / 2.0


def vrp(vix_level: float, daily_returns_21: Sequence[float]) -> float:
    """VIX^2 / 12 (monthly variance units) minus the sum of 21 squared daily simple returns (F-15)."""
    r = list(daily_returns_21)
    if len(r) != 21:
        raise ValueError(f"vrp needs exactly 21 daily returns, got {len(r)}")
    return (vix_level / 100.0) ** 2 / 12.0 - sum(x * x for x in r)


def trend_state_sma10m(month_end_closes: Sequence[float]) -> str:
    """'below' if the latest month-end close < the mean of the last 10 (incl. itself), else 'above' (R-28 rule 1)."""
    c = list(month_end_closes)
    if len(c) < 10:
        raise ValueError(f"trend_state_sma10m needs 10 month-end closes, got {len(c)}")
    return "below" if c[-1] < sum(c[-10:]) / 10.0 else "above"


def rv21_series(closes: Sequence[float], window: int = 21, ann: int = 252) -> np.ndarray:
    px = np.asarray(closes, dtype=float)
    r = px[1:] / px[:-1] - 1.0
    if r.size < window:
        return np.empty(0)
    return np.array([math.sqrt(float(np.var(r[i - window + 1:i + 1], ddof=1)) * ann) for i in range(window - 1, r.size)])


def rv21_and_percentile(closes: Sequence[float], *, history: int = 756) -> tuple[float, float, int]:
    """(rv21, percentile within the trailing `history` rv21 values incl. today, n used) (F-16)."""
    rv = rv21_series(closes)
    if rv.size == 0:
        raise ValueError("rv21 needs 22 closes")
    hist = rv[-history:]
    return float(rv[-1]), float((hist <= rv[-1]).mean()), int(hist.size)


def causal_zscore(values: Sequence[float], window: int = Z_WINDOW) -> tuple[float | None, str]:
    """z of the last value against the trailing `window` observations (population SD, as the sheet); None when
    fewer than 2 observations or SD 0. Label: trailing_<n>_obs."""
    x = np.asarray(list(values)[-window:], dtype=float)
    x = x[np.isfinite(x)]
    label = f"trailing_{x.size}_obs"
    if x.size < 2:
        return None, label
    sd = float(x.std())
    return (float((x[-1] - x.mean()) / sd) if sd > 0 else None), label


def sahm_inhouse(monthly: Mapping[date, float], obs_month: date) -> P.MonthlyValue:
    """3-month mean of U-3 minus the minimum of the 3-month means over the previous 12 months (F-13). Strict NaN
    propagation: any 3-month mean touching a missing month makes the value NaN (L1353)."""
    cur = P.rolling_mean(monthly, obs_month, 3)
    prev = [P.rolling_mean(monthly, P.add_months(obs_month, -i), 3) for i in range(1, 13)]
    bad = [m for m in [cur] + prev if m.flagged]
    if bad:
        return P.MonthlyValue(math.nan, True, "a 3-month mean in the lookback touches a missing month: NaN")
    return P.MonthlyValue(cur.value - min(m.value for m in prev), False)


def turbulence_absorption(returns: np.ndarray, *, window: int = 500, half_life: int = 250) -> tuple[float, float]:
    """Kritzman turbulence of the last row against the EW mean/cov of the `window` rows before it, and the
    absorption ratio (top N/5 eigenvalues / total) of that covariance (L1691; F-17 rounding n = max(1, round(N/5)))."""
    x = np.asarray(returns, dtype=float)
    if x.ndim != 2 or x.shape[0] < 3:
        raise ValueError("turbulence needs a (T, N) return panel with T >= 3")
    hist, y = x[-window - 1:-1], x[-1]
    w = 0.5 ** (np.arange(hist.shape[0])[::-1] / float(half_life))
    w /= w.sum()
    mu = w @ hist
    d = hist - mu
    sigma = (d * w[:, None]).T @ d
    turb = float((y - mu) @ np.linalg.pinv(sigma) @ (y - mu))
    ev = np.sort(np.linalg.eigvalsh(sigma))[::-1]
    n = max(1, int(round(ev.size / 5.0)))
    return turb, float(ev[:n].sum() / ev.sum()) if ev.sum() > 0 else float("nan")


# --------------------------------------------------------------------------- #
# Item catalogue (R-13 table; brief B.2). Ids marked (v) are spec-verbatim, the rest proposed.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ItemSpec:
    series_id: str
    name: str                      # ends with the unit in parentheses (F-9) once the registry unit is known
    row: str                       # R-13 row
    timing: str | None = None      # None: the registry timing_class
    from_sheet: bool = False
    note: str = ""


_SHEET_NOTES = {
    "T10Y2Y": "level and z only; never a probit prior (R-13)",
    "ZN=F": "continuous contract; changes not roll-adjusted (F-7)",
    "GC=F": "continuous contract; changes not roll-adjusted (F-7)",
    "DEXKOUS": "labelled proxy; production reads ECOS 15:30 or the 15:30:00 KST snapshot (R-11)",
    "DGS10": "also a risk-model input of corr63 (backtest channel) and the R-12 refusal book input",
}


def sheet_items() -> tuple[ItemSpec, ...]:
    """The 18 indicators of core/ficc/macro (TASK-M6-01: all CONTEXT; sheet timing per brief B.1)."""
    from core.ficc.macro import INDICATORS       # lazy: the sheet module pulls the provider stack (2.7 s)
    return tuple(ItemSpec(i.id, i.label, "existing_sheet", "publication" if i.source_hint == "FRED" else "value_proxy",
                          True, _SHEET_NOTES.get(i.id, "")) for i in INDICATORS)


LIVE_IDS = ("KOFIA_MARGIN_DEBT", "KRX_LETF_AUM_INDEX", "KRX_LETF_AUM_SINGLE_STOCK", "KRX_LETF_VALUE_TRADED",
            "KRX_LEVERAGED_SHARE", "VIX_1600ET_SNAPSHOT", "VIX3M_1600ET_SNAPSHOT", "KOSPI200_MFIV_1530KST",
            "KOSPI200_MFIV_1530")
RAW_ITEMS: tuple[ItemSpec, ...] = (
    ItemSpec("SAHMREALTIME", "Sahm rule, real-time", "sahm"),
    ItemSpec("UNRATE", "U-3 unemployment rate", "inflation_labour"),
    ItemSpec("ICSA", "Initial claims", "sahm"),
    ItemSpec("PAYEMS", "Nonfarm payrolls", "inflation_labour", note="known then vs known now"),
    ItemSpec("T10Y3M", "10y-3m spread", "probit"),
    ItemSpec("THREEFYTP10", "Kim–Wright 10y term premium", "real_yield_term_premium"),
    ItemSpec("^MOVE", "MOVE", "real_yield_term_premium"),
    ItemSpec("T5YIFR", "5y5y forward breakeven", "breakevens"),
    ItemSpec("BAA10Y", "Baa minus 10y", "credit"),
    ItemSpec("USD_LIVE_PROXY", "USD live proxy (DXY)", "fx", "live"),
    ItemSpec("ECOS_1530_CLOSE", "USD/KRW ECOS 15:30 close", "fx", "value_proxy", note="FX-regime metadata: see extras.regime_tags"),
    ItemSpec("USDKRW_1530_SNAPSHOT", "USD/KRW 15:30:00 KST snapshot", "fx", "live", note="FX-regime metadata: see extras.regime_tags"),
    ItemSpec("DCOILBRENTEU", "Dated Brent spot", "oil"),
    ItemSpec("BZ=F", "Brent front future", "oil", note="roll days excluded from changes (T-SER-01)"),
    ItemSpec("PCEPILFE", "Core PCE index", "inflation_labour", note="known then vs known now"),
    ItemSpec("PCEPI", "PCE index", "inflation_labour", note="known then vs known now"),
    ItemSpec("CPIAUCSL", "CPI index", "inflation_labour", note="known then vs known now"),
    ItemSpec("CPILFESL", "Core CPI index", "inflation_labour", note="known then vs known now"),
    ItemSpec("FEDFUNDS", "Effective fed funds, monthly", "policy"),
    ItemSpec("DFEDTARU", "Fed funds target, upper", "policy"),
    ItemSpec("USEPUINDXD", "Economic policy uncertainty", "epu", note="variance only (N-04)"),
    ItemSpec("BOK_BASE_RATE", "BoK base rate", "korea"),
    ItemSpec("KOSPI_NET_BUY_FOREIGN", "KOSPI net buy, foreign", "korea", note="final after close; no direction rule (DATA-6)"),
    ItemSpec("KOSPI_NET_BUY_INSTITUTION", "KOSPI net buy, institution", "korea", note="final after close; no direction rule (DATA-6)"),
    ItemSpec("KOSPI_NET_BUY_INDIVIDUAL", "KOSPI net buy, individual", "korea", note="final after close; no direction rule (DATA-6)"),
    ItemSpec("VKOSPI", "VKOSPI", "live_implied_vol", note="never a sizing input (section 10 item 30)"),
    ItemSpec("KOSPI200_MFIV_1530", "KOSPI200 MFIV 15:30 KST", "live_implied_vol", "live"),
    ItemSpec("KOSPI200_MFIV_1530KST", "KOSPI200 MFIV 15:30 KST snapshot", "live_implied_vol", "live"),
    ItemSpec("VIX_1600ET_SNAPSHOT", "VIX 16:00 ET snapshot", "live_implied_vol", "live"),
    ItemSpec("VIX3M_1600ET_SNAPSHOT", "VIX3M 16:00 ET snapshot", "live_implied_vol", "live"),
    ItemSpec("KOFIA_MARGIN_DEBT", "KOFIA margin debt", "leverage_flow", "live"),
    ItemSpec("KRX_LETF_AUM_INDEX", "Index leveraged-ETF AUM", "leverage_flow", "live"),
    ItemSpec("KRX_LETF_AUM_SINGLE_STOCK", "Single-stock leveraged-ETF AUM", "leverage_flow", "live"),
    ItemSpec("KRX_LETF_VALUE_TRADED", "Leveraged-ETF value traded", "leverage_flow", "live"),
    ItemSpec("KRX_LEVERAGED_SHARE", "Leveraged share of value traded", "leverage_flow", "live"),
    ItemSpec("FOMC_DECISION", "FOMC decision", "policy"),
    ItemSpec("FOMC_VOTE_SPLIT", "FOMC vote split", "policy"),
    ItemSpec("FOMC_DISSENT_DIRECTION", "FOMC dissent direction", "policy"),
    ItemSpec("SEP_TABLE2_BANDS", "SEP Table-2 error bands", "policy"),
)
LEVERAGE_IDS = ("KOFIA_MARGIN_DEBT", "KRX_LETF_AUM_INDEX", "KRX_LETF_AUM_SINGLE_STOCK", "KRX_LETF_VALUE_TRADED",
                "KRX_LEVERAGED_SHARE")


def _iso(x) -> str | None:
    return None if x is None else P.iso_utc(x)


class _Reader:
    """PIT reads for the log: consumer R-13, never a raw frame. Remembers why a series had no item."""

    def __init__(self, store, registry, decision_utc, knowledge_utc, clocks, run_mode):
        self.store, self.registry, self.dec, self.knw, self.clocks, self.run_mode = store, registry, decision_utc, knowledge_utc, clocks, run_mode
        self.missing: list[dict] = []
        self.synthetic: list[str] = []

    def registered(self, sid: str) -> bool:
        return self.registry.is_series(sid)

    def value(self, sid: str, *, record_missing: bool = True) -> P.PITValue | None:
        if not self.registered(sid):
            if record_missing:
                self.missing.append({"series_id": sid, "reason": "unregistered"})
            return None
        try:
            v = P.pit_value(self.store, sid, self.dec, self.knw, CONTEXT_CONSUMER, run_mode=self.run_mode, registry=self.registry)
        except P.PITError:                            # a close with a consumer-less acting binding: labelled last read
            v = P.pit_last(self.store, sid, self.dec, self.knw, registry=self.registry)
            if v is None:
                v = P.MissingInput(sid, "missing", "context", ())
        if isinstance(v, P.MissingInput):
            last = P.pit_last(self.store, sid, self.dec, self.knw, registry=self.registry)
            if last is None:
                if record_missing:
                    self.missing.append({"series_id": sid, "reason": v.reason})
                return None
            return last
        if v.synthetic:
            self.synthetic.append(sid)
            return None
        return v

    def window(self, sid: str, n: int | None = None, statuses=None) -> list[P.PITValue]:
        if not self.registered(sid):
            return []
        return [v for v in P.pit_window(self.store, sid, self.dec, self.knw, n=n, registry=self.registry, statuses=statuses)
                if not v.synthetic]

    def monthly(self, sid: str) -> dict[date, float]:
        return {P.month_start(v.obs_date): v.value for v in self.window(sid)}

    def stale(self, sid: str) -> tuple[bool, str]:
        if self.clocks is None:
            return True, "calendar unavailable: no clocks"
        try:
            chk = C.is_stale(self.store, self.registry, sid, self.dec, self.knw, self.clocks)
        except Exception as exc:                     # noqa: BLE001  (context: labelled, never raised)
            return True, f"calendar unavailable: {exc}"
        return chk.stale, (f"stale: {chk.reason}" if chk.stale else "")

    def _visible(self, sid: str, obs_date: date) -> list[dict]:
        return [r for r in self.store.rows(sid) if r["obs_date"] == obs_date
                and r["available_at_utc"] <= self.dec and r["retrieved_at_utc"] <= self.knw]

    def has_vintages(self, sid: str) -> bool:
        return any(r.get("vintage") is not None for r in self.store.rows(sid) if r["retrieved_at_utc"] <= self.knw)

    def vintage_fields(self, sid: str, obs_date: date) -> dict:
        rows = self._visible(sid, obs_date)
        dated = [r for r in rows if r.get("vintage") is not None]
        if not dated:
            return {}
        first = [r for r in rows if r["value_status"] == "first_release"] or [min(dated, key=lambda r: r["vintage"])]
        latest = max(dated, key=lambda r: r["vintage"])
        return {"first_release": first[0]["value"], "latest": latest["value"], "vintage_date": latest["vintage"].isoformat()}


def _unit(registry, sid: str, fallback: str = "") -> str:
    return str(registry.series[sid].get("unit", fallback)) if registry.is_series(sid) else fallback


def _timing(registry, sid: str, spec: ItemSpec) -> str:
    if spec.timing is not None:
        return spec.timing
    return registry.series[sid]["timing_class"] if registry.is_series(sid) else "publication"


def _raw_item(rd: _Reader, spec: ItemSpec, v: P.PITValue) -> dict:
    stale, why = rd.stale(spec.series_id)
    notes = [n for n in (spec.note, why) if n]
    item = {"name": f"{spec.name} ({_unit(rd.registry, spec.series_id, 'level')})", "series_id": spec.series_id,
            "value": v.value, "obs_date": v.obs_date.isoformat(), "available_at_utc": _iso(v.available_at_utc),
            "retrieved_at_utc": _iso(v.retrieved_at_utc), "vintage": v.vintage.isoformat() if v.vintage else None,
            "source": f"{v.source} {v.channel}" if v.channel else v.source, "timing": _timing(rd.registry, spec.series_id, spec),
            "value_status": v.value_status, "stale": bool(stale)}
    if rd.has_vintages(spec.series_id):
        item.update(rd.vintage_fields(spec.series_id, v.obs_date))
        if v.vintage is None:
            item["value_status"] = "revised"
            notes.append("pre_vintage_history")
    if spec.from_sheet:
        z, label = causal_zscore([w.value for w in rd.window(spec.series_id)])
        item.update({"zscore_causal": z, "zscore_window": label, "from_sheet": True})
        notes.append("never thresholded")
    if spec.series_id in LEVERAGE_IDS and v.obs_date >= LETF_RULE_CHANGE:
        notes.append("structural break 2026-07-16")
    if notes:
        item["note"] = "; ".join(notes)
    return item


def _derived(rd: _Reader, series_id: str, name: str, value, inputs: Sequence[P.PITValue], *, timing: str = "publication",
             note: str = "", range_=None, obs_date: date | None = None, value_status: str | None = None) -> dict:
    """A derived item: provenance from its inputs (latest available_at / retrieved_at / vintage); value_status
    `vendor_derived` (the section 6.4 examples) unless the caller names a gap (`vendor_derived_across_gap`)."""
    if not inputs:
        raise ValueError(f"{series_id}: a derived item needs its inputs")
    stale = any(rd.stale(i.series_id)[0] for i in {i.series_id: i for i in inputs}.values())
    vint = [i.vintage for i in inputs if i.vintage is not None]
    if value is not None and isinstance(value, float) and not math.isfinite(value):
        value = None
    item = {"name": name, "series_id": series_id, "value": value,
            "obs_date": (obs_date or max(i.obs_date for i in inputs)).isoformat(),
            "available_at_utc": _iso(max(i.available_at_utc for i in inputs)),
            "retrieved_at_utc": _iso(max(i.retrieved_at_utc for i in inputs)),
            "vintage": max(vint).isoformat() if vint else None,
            "source": "derived from " + "/".join(dict.fromkeys(i.series_id for i in inputs)), "timing": timing,
            "value_status": value_status or "vendor_derived", "stale": bool(stale)}
    if range_ is not None:
        item["range"] = [float(range_[0]), float(range_[1])]
    if note:
        item["note"] = note
    return item


def _latest_window(rd: _Reader, sid: str, n: int) -> list[P.PITValue]:
    return rd.window(sid, n=n)


def _change(rd: _Reader, sid: str, n: int, name: str, out_id: str) -> dict | None:
    w = _latest_window(rd, sid, n + 1)
    if len(w) < n + 1:
        return None
    return _derived(rd, out_id, name, w[-1].value - w[0].value, [w[0], w[-1]], note=f"change over {n} observations")


def _monthly_inputs(rd: _Reader, sid: str, months: Sequence[date]) -> list[P.PITValue]:
    by = {P.month_start(v.obs_date): v for v in rd.window(sid)}
    return [by[m] for m in months if m in by]


def _yoy_item(rd: _Reader, sid: str, out_id: str, name: str) -> dict | None:
    m = rd.monthly(sid)
    if not m:
        return None
    obs = max(m)
    y = P.yoy(m, obs)
    missing = rd.registry.series[sid].get("missing_months") or ()
    status = P.vendor_status_across_gap([P.add_months(obs, -i) for i in range(13)], [date.fromisoformat(str(x)) for x in missing])
    ins = _monthly_inputs(rd, sid, [obs, P.add_months(obs, -12)])
    return _derived(rd, out_id, name, None if y.flagged else y.value * 100.0, ins, obs_date=obs, value_status=status,
                    note="calendar offset, never positional shift" + (f"; {y.reason}" if y.flagged else ""))


def _calc_sahm(rd):
    m = rd.monthly("UNRATE")
    if not m:
        return None
    obs = max(m)
    s = sahm_inhouse(m, obs)
    ins = _monthly_inputs(rd, "UNRATE", [P.add_months(obs, -i) for i in range(15)])
    missing = [date.fromisoformat(str(x)) for x in (rd.registry.series["UNRATE"].get("missing_months") or ())]
    return _derived(rd, "SAHM_INHOUSE", "Sahm rule, in-house (pp)", None if s.flagged else s.value, ins, obs_date=obs,
                    value_status=P.vendor_status_across_gap([P.add_months(obs, -i) for i in range(15)], missing),
                    note="3m mean of U-3 minus the min of the previous 12 3m means; a gap gives NaN" + (f"; {s.reason}" if s.flagged else ""))


def _calc_unrate_3m(rd):
    m = rd.monthly("UNRATE")
    if not m:
        return None
    obs = max(m)
    c = P.calendar_change(m, obs, 3, kind="diff")
    return _derived(rd, "UNRATE_3M_CHANGE", "U-3 3-month change (pp)", None if c.flagged else c.value,
                    _monthly_inputs(rd, "UNRATE", [obs, P.add_months(obs, -3)]), obs_date=obs, note="calendar offset")


def _calc_icsa_4wk(rd):
    w = _latest_window(rd, "ICSA", 4)
    if len(w) < 4:
        return None
    return _derived(rd, "ICSA_4WK_AVG", "Initial claims, 4-week average (count)", sum(v.value for v in w) / 4.0, w)


def _calc_probit(rd, rules):
    g, t = rd.value("GS10"), rd.value("TB3MS")
    if g is None or t is None:
        return None
    p = rules.get("probit", {})
    val = recession_probit_et(g.value, t.value, p.get("alpha", -0.6045), p.get("beta", -0.7374))
    return _derived(rd, "RECESSION_PROBIT_ET", "Recession probit (E-T coefficients) (probability)", val, [g, t],
                    note="published coefficients; spread = GS10 - BEY(TB3MS), monthly; 10y-2y is never a prior")


def _calc_taylor(rd, rules):
    pce = rd.monthly("PCEPILFE")
    un = rd.monthly("UNRATE")
    if not pce or not un:
        return None
    obs = max(m for m in pce if m in un)
    pi = P.yoy(pce, obs)
    eff = {P.month_start(v.obs_date): v for v in rd.window("EFFR")}
    carried = {sid: rd.value(sid) for sid in ("NROU", "GDPC1", "GDPPOT")}
    if pi.flagged or obs not in eff or any(v is None for v in carried.values()):
        return None
    tf = rules.get("taylor_family", {})
    lo, hi = taylor_residual_range(eff[obs].value, pi.value * 100.0, un[obs], carried["NROU"].value, carried["GDPC1"].value,
                                   carried["GDPPOT"].value, r_star=tuple(tf.get("r_star", (0.5, 1.0, 2.0))),
                                   a=tuple(tf.get("a", (0.5, 1.0))), pi_star=float(tf.get("pi_star", 2.0)))
    ins = _monthly_inputs(rd, "PCEPILFE", [obs, P.add_months(obs, -12)]) + _monthly_inputs(rd, "UNRATE", [obs]) + [eff[obs]] + list(carried.values())
    return _derived(rd, "TAYLOR_RESIDUAL_RANGE", "Taylor residual range (pp)", None, ins, obs_date=obs, range_=(lo, hi),
                    note="never thresholded; EFFR monthly; quarterly inputs carried as-of (no interpolation)")


def _calc_vrp(rd):
    vix = rd.value("VIX_1600ET_SNAPSHOT", record_missing=False)
    px = rd.window("SPX_OFFICIAL_CLOSE", n=22, statuses=P.CLOSE_STATUSES)
    if vix is None or len(px) < 22:
        return None
    r = [b.value / a.value - 1.0 for a, b in zip(px, px[1:])]
    return _derived(rd, "VRP_US", "Variance risk premium, US (monthly variance)", vrp(vix.value, r), [vix] + px, timing="live",
                    note="VIX^2/12 minus 21-day realised variance (sum of squared simple returns)")


def _calc_kospi_rv21(rd):
    px = rd.window("KOSPI_OFFICIAL_CLOSE", n=777, statuses=P.CLOSE_STATUSES)
    if len(px) < 22:
        return None
    rv, pct, n = rv21_and_percentile([v.value for v in px])
    return [_derived(rd, "KOSPI_RV21", "KOSPI rv21 (decimal, annualised)", rv, px[-22:], timing="live"),
            _derived(rd, "KOSPI_RV21_PCTILE_3Y", "KOSPI rv21 percentile, trailing 3y (share)", pct, px, timing="live",
                     note=f"within the trailing {n} rv21 values")]


def _calc_kospi_trend(rd):
    px = rd.window("KOSPI_OFFICIAL_CLOSE", statuses=P.CLOSE_STATUSES)
    ends: dict[date, P.PITValue] = {}
    for v in px:
        ends[P.month_start(v.obs_date)] = v                     # the last close of each month
    months = sorted(ends)
    if len(months) < 11:
        return None
    closes = [ends[m] for m in months[:-1]][-10:]               # completed months only (R-28 rule 1: month-end closes)
    return _derived(rd, "KOSPI_TREND_SMA10M", "KOSPI trend state, SMA10m (above|below)",
                    trend_state_sma10m([c.value for c in closes]), closes, timing="live",
                    note="context only; R-28 has no Korea instance (section 10 item 37)")


def _calc_usdjpy_dist(rd):
    v = rd.value("DEXJPUS", record_missing=False)
    return None if v is None else _derived(rd, "USDJPY_DIST_TO_160", "USD/JPY distance to 160 (JPY)", 160.0 - v.value, [v],
                                           note="160-164 is the intervention hazard zone")


def _calc_brent_spread(rd):
    a, b = rd.value("DCOILBRENTEU", record_missing=False), rd.value("BZ=F", record_missing=False)
    if a is None or b is None:
        return None
    return _derived(rd, "BRENT_DATED_MINUS_BZF", "Dated Brent minus BZ=F (USD/bbl)", a.value - b.value, [a, b],
                    note=f"dates {a.obs_date} / {b.obs_date}")


def _calc_payems_change(rd):
    m = rd.monthly("PAYEMS")
    if not m:
        return None
    obs = max(m)
    c = P.mom(m, obs)
    return _derived(rd, "PAYEMS_CHANGE_1M", "Payrolls, monthly change (thousands)", None if c.flagged else (m[obs] - m[P.add_months(obs, -1)]),
                    _monthly_inputs(rd, "PAYEMS", [obs, P.add_months(obs, -1)]), obs_date=obs, note="known then vs known now")


def _calc_turbulence(rd, rules):
    uni = rules.get("turbulence_universe")
    if not uni or not rd.registry.is_group(uni):
        rd.missing.append({"series_id": "TURBULENCE", "reason": "context_log.turbulence_universe not declared (F-17)"})
        rd.missing.append({"series_id": "ABSORPTION_RATIO", "reason": "context_log.turbulence_universe not declared (F-17)"})
        return None
    cols, ins = [], []
    for sid in rd.registry.members(uni):
        w = rd.window(sid, n=502, statuses=P.CLOSE_STATUSES)
        cols.append({v.obs_date: v.value for v in w})
        ins.extend(w[-1:])
    dates = sorted(set.intersection(*(set(c) for c in cols)))
    if len(dates) < 30:
        return None
    px = np.array([[c[d] for c in cols] for d in dates])
    turb, ar = turbulence_absorption(px[1:] / px[:-1] - 1.0)
    return [_derived(rd, "TURBULENCE", "Kritzman turbulence (Mahalanobis)", turb, ins, timing="live", note="display only; never a multiplier"),
            _derived(rd, "ABSORPTION_RATIO", "Absorption ratio (share)", ar, ins, timing="live", note="display only; never a multiplier")]


def default_calculators() -> dict[str, Callable]:
    """series_id -> fn(reader, rules_block) returning an item, a list of items or None."""
    return {
        "SAHM_INHOUSE": lambda rd, r: _calc_sahm(rd), "UNRATE_3M_CHANGE": lambda rd, r: _calc_unrate_3m(rd),
        "ICSA_4WK_AVG": lambda rd, r: _calc_icsa_4wk(rd), "RECESSION_PROBIT_ET": _calc_probit,
        "TAYLOR_RESIDUAL_RANGE": _calc_taylor,
        "DFII10_CHG_20D": lambda rd, r: _change(rd, "DFII10", 20, "10y real yield, 20-obs change (pct)", "DFII10_CHG_20D"),
        "DFII10_CHG_63D": lambda rd, r: _change(rd, "DFII10", 63, "10y real yield, 63-obs change (pct)", "DFII10_CHG_63D"),
        "BAMLH0A0HYM2_CHG_21D": lambda rd, r: _change(rd, "BAMLH0A0HYM2", 21, "HY OAS, 21-obs change (pct)", "BAMLH0A0HYM2_CHG_21D"),
        "BAA10Y_CHG_21D": lambda rd, r: _change(rd, "BAA10Y", 21, "Baa minus 10y, 21-obs change (pct)", "BAA10Y_CHG_21D"),
        "PCEPILFE_YOY": lambda rd, r: _yoy_item(rd, "PCEPILFE", "PCEPILFE_YOY", "Core PCE YoY (pct)"),
        "CPIAUCSL_YOY": lambda rd, r: _yoy_item(rd, "CPIAUCSL", "CPIAUCSL_YOY", "CPI YoY (pct)"),
        "CPILFESL_YOY": lambda rd, r: _yoy_item(rd, "CPILFESL", "CPILFESL_YOY", "Core CPI YoY (pct)"),
        "PAYEMS_CHANGE_1M": lambda rd, r: _calc_payems_change(rd), "VRP_US": lambda rd, r: _calc_vrp(rd),
        "KOSPI_RV21": lambda rd, r: _calc_kospi_rv21(rd), "KOSPI_TREND_SMA10M": lambda rd, r: _calc_kospi_trend(rd),
        "USDJPY_DIST_TO_160": lambda rd, r: _calc_usdjpy_dist(rd), "BRENT_DATED_MINUS_BZF": lambda rd, r: _calc_brent_spread(rd),
        "TURBULENCE": _calc_turbulence,
    }


@lru_cache(maxsize=1)
def _shipped_store():
    from core.rules.macro_rules import load_store                # lazy: scipy
    return load_store()


def _rules_block(rules, key: str) -> dict:
    rules = _shipped_store() if rules is None else rules
    try:
        return dict(rules[key] if isinstance(rules, Mapping) else rules.get(key))
    except KeyError:
        return {}


def _config_hash(rules) -> str:
    rules = _shipped_store() if rules is None else rules
    return md5_hex(canonical_json(rules)) if isinstance(rules, Mapping) else rules.config_hash


# --------------------------------------------------------------------------- #
# The log (TASK-M6-02; T-CTX-02)
# --------------------------------------------------------------------------- #
def build_context_log(store, registry, decision_utc: datetime, knowledge_utc: datetime, *, clocks, clock, rules=None,
                      run_mode: str = "live", specs: Sequence[ItemSpec] | None = None, calculators: Mapping | None = None,
                      extra_items: Sequence[dict] = (), data_snapshot: str | None = None) -> dict:
    """One context_log per decision from PIT reads (consumer R-13) and the pure calculators. `acts` is false.
    Fail-closed, context variant: stale -> labelled; no visible record -> omitted (extras.missing_items); synthetic
    -> excluded and alerted; a raising calculator -> its item omitted (extras.item_errors), the rest unaffected.
    `clock` stamps generated_at_utc (the only wall clock, a volatile field). Returns the dict; `write_context_log`
    validates and writes or quarantines. Never raises on data: only on a bad call. (Not guarded: the M8
    orchestrator writes it inside `run_context_step`; the readers are guarded.)"""
    rd = _Reader(store, registry, decision_utc, knowledge_utc, clocks, run_mode)
    block = _rules_block(rules, "context_log")
    items, errors, alerts = [], [], []
    for spec in list(specs if specs is not None else sheet_items() + RAW_ITEMS):
        try:
            v = rd.value(spec.series_id)
            if v is not None:
                items.append(_raw_item(rd, spec, v))
        except Exception as exc:                     # noqa: BLE001  (one item, never the log)
            errors.append({"series_id": spec.series_id, "error": f"{type(exc).__name__}: {exc}"})
    for sid, fn in (calculators if calculators is not None else default_calculators()).items():
        try:
            out = fn(rd, block)
        except Exception as exc:                     # noqa: BLE001
            errors.append({"series_id": sid, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if out is None:
            if not any(m["series_id"] == sid for m in rd.missing):
                rd.missing.append({"series_id": sid, "reason": "inputs not visible"})
            continue
        items.extend(out if isinstance(out, list) else [out])
    items.extend(dict(i) for i in extra_items)
    for e in errors:
        alerts.append(_alert(ALERT_ITEM_ERROR, COMPONENT, decision_utc, series_id=e["series_id"], severity="info"))
    for sid in rd.synthetic:
        alerts.append(_alert(ALERT_SYNTHETIC, COMPONENT, decision_utc, series_id=sid, severity="warn"))
    snap = data_snapshot if data_snapshot is not None else P.data_snapshot_id(store, knowledge_utc)
    log = {"schema": SCHEMA, **MA.provenance(clock=clock, knowledge_utc=P.iso_utc(knowledge_utc), config_hash=_config_hash(rules),
                                              data_snapshot_id=snap),
           "decision_utc": P.iso_utc(decision_utc), "as_of_utc": P.iso_utc(decision_utc), "acts": False, "items": items,
           "extras": {"run_mode": run_mode, "missing_items": rd.missing, "synthetic_excluded": sorted(set(rd.synthetic)),
                      "item_errors": errors, "alerts": alerts, "descriptive_read": DESCRIPTIVE_READ_NOTE,
                      "n_from_sheet": sum(1 for i in items if i.get("from_sheet"))}}
    issues = validate(SCHEMA, log)
    if issues:
        log["extras"]["validation_errors"] = issues
    return log


@dataclass(frozen=True)
class ContextWrite:
    status: str                    # written | quarantined
    path: Path | None
    issues: tuple[str, ...] = ()
    alert: dict | None = None


def write_context_log(root, log: dict, clock: Callable[[], datetime]) -> ContextWrite:
    """Validate and write under <root>/context_log/; a refused log goes to <root>/quarantine/ with its errors and
    raises alert CONTEXT_LOG_INVALID (warn). Never a HALT, never an exception for a bad log (R-32, L3865)."""
    try:
        return ContextWrite("written", MA.write_artifact(root, "context_log", log, clock))
    except MA.ArtifactRefused as refused:
        dec = log.get("decision_utc") if isinstance(log, dict) else None
        when = P.parse_utc(dec) if isinstance(dec, str) else clock()
        return ContextWrite("quarantined", refused.quarantine_path, tuple(refused.issues),
                            _alert(ALERT_LOG_INVALID, COMPONENT, when, severity="warn"))


# --------------------------------------------------------------------------- #
# R-18 break protocol (TASK-M6-04; T-BREAK-01)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BreakEvent:
    kind: str
    effective_date: date
    declared_utc: datetime
    source: str                              # the official notice / statement reference; never empty
    market: str | None = None
    tag: str | None = None
    old: object = None
    new: object = None
    note: str = ""
    event_id: str = ""                       # sha1(kind|market|tag|effective_date|new): idempotent

    def __post_init__(self) -> None:
        if self.kind not in BREAK_KINDS:
            raise ValueError(f"break kind {self.kind!r} is not one of {BREAK_KINDS} (a policy-direction flip is not a trigger, L1781)")
        if not self.source:
            raise ValueError("a break event names its official source")
        if self.declared_utc.tzinfo is None:
            raise ValueError("declared_utc must be tz-aware UTC")
        if not self.event_id:
            key = "|".join([self.kind, self.market or "", self.tag or "", self.effective_date.isoformat(), json.dumps(self.new, sort_keys=True, default=str)])
            object.__setattr__(self, "event_id", hashlib.sha1(key.encode("utf-8")).hexdigest()[:16])

    def row(self) -> dict:
        d = asdict(self)
        d["effective_date"] = self.effective_date.isoformat()
        d["declared_utc"] = P.iso_utc(self.declared_utc)
        return d


@dataclass(frozen=True)
class BreakResult:
    event: BreakEvent
    appended: bool
    targets: tuple[str, ...] = ()
    neutralised: dict = field(default_factory=dict)      # rule_id -> event_id (the apply side reads this map)
    governance_rows: tuple[str, ...] = ()
    marker: Path | None = None
    hook_applied: bool = False


def _read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_break_log(root) -> list[dict]:
    """Declared events (the Macro page calendar panel). Guarded: never an acting reader."""
    assert_not_acting_caller()
    return _read_jsonl(Path(root) / BREAK_LOG)


def macro_conditioned_rules(rules) -> tuple[str, ...]:
    """Rule ids whose object carries `macro_conditioned: true` (F-18). Empty in the shipped v2.0 store."""
    rules = _shipped_store() if rules is None else rules
    doc = dict(rules) if isinstance(rules, Mapping) else rules.resolve_refs()
    out = []

    def walk(node, path):
        if isinstance(node, Mapping):
            if node.get("macro_conditioned") is True:
                out.append(str(node.get("rule_id") or node.get("card_id") or path))
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
    walk(doc, "")
    return tuple(dict.fromkeys(out))


def log_break(root, event: BreakEvent, *, decision_utc: datetime, knowledge_utc: datetime, rules=None,
              clock: Callable[[], datetime] | None = None, neutralise: Callable[[str, str], object] | None = None,
              governance_log=None) -> BreakResult:
    """Append a declared event (idempotent by event_id). A `policy_framework_change` additionally neutralises every
    macro-conditioned multiplier to 1.0: push through `neutralise(rule_id, event_id)` (the per-book runtime hook
    `core.engine.books.neutralise_rule`: pass `lambda rid, eid: books.neutralise_rule(registry, rid, eid, decision_utc)`;
    `books.neutralised_rules(registry, book_id)` then feeds `build_overlay_decisions(neutralised=...)`),
    one `record_reset` governance event per target (section 6.6 forward-record reset) and the forward-record marker
    for M8's monitor. There is no historical re-gate. Nothing reads the break log on the acting side."""
    root = Path(root)
    path = root / BREAK_LOG
    if any(r.get("event_id") == event.event_id for r in _read_jsonl(path)):
        return BreakResult(event, False)
    stamp = P.iso_utc(clock() if clock else decision_utc)
    _append_line(path, {**event.row(), "decision_utc": P.iso_utc(decision_utc), "knowledge_utc": P.iso_utc(knowledge_utc),
                        "git_hash": MA.GIT_HASH, "config_hash": _config_hash(rules), "logged_utc": stamp})
    if event.kind != "policy_framework_change":
        return BreakResult(event, True)
    targets = macro_conditioned_rules(rules)
    neutralised, rows, applied = {}, [], False
    log = Path(governance_log) if governance_log else root / "governance_events.jsonl"
    for rid in targets:
        if neutralise is not None:
            neutralise(rid, event.event_id)
            applied = True
        neutralised[rid] = event.event_id
        rows.append(G.append_event(log, {
            "kind": "record_reset", "book_id": None, "rule_id": rid, "key": "multiplier", "old": "macro_conditioned",
            "new": 1.0, "actor": "runtime", "utc": stamp, "refs": ["R-18"],
            "reason": f"R-18 official framework change {event.event_id}: multiplier shrunk to 1.0; forward record starts; no historical re-gate"}))
    marker = None
    if targets:
        marker = root / FORWARD_RECORD_MARKER
        _append_line(marker, {"event_id": event.event_id, "rule_ids": list(targets), "requested_utc": stamp,
                              "decision_utc": P.iso_utc(decision_utc), "knowledge_utc": P.iso_utc(knowledge_utc),
                              "note": "a forward record starts at the first live macro_daily decision (M8), never before (L5310)"})
    return BreakResult(event, True, targets, neutralised, tuple(rows), marker, applied)


def sync_market_structure_breaks(root, market: str, *, cal, decision_utc: datetime, knowledge_utc: datetime, rules=None,
                                 clock: Callable[[], datetime] | None = None) -> list[BreakEvent]:
    """One `market_structure` row per regime-tag transition of the signed tag file (R-20 L2051); idempotent by
    event_id. Returns the events appended by this call. Cards read the tags through `regime_tags`, never this log."""
    from core.calendars import regime                              # context -> calendars is the allowed direction
    if market != "KR":
        return []
    f = cal.file(regime.FILE_ID)
    out = []
    for tag, spans in regime._table(cal).items():
        for (_lo, _hi, old), (lo, _nhi, new) in zip(spans, spans[1:]):
            ev = BreakEvent("market_structure", lo, decision_utc, f"{regime.FILE_ID} v{f.version} (signed {f.signed_off_by})",
                            market=market, tag=tag, old=old, new=new,
                            note="structural break 2026-07-16: leveraged-ETF rules" if tag == "letf_rules" and lo == LETF_RULE_CHANGE else "")
            if log_break(root, ev, decision_utc=decision_utc, knowledge_utc=knowledge_utc, rules=rules, clock=clock).appended:
                out.append(ev)
    return out


def reanchor_eligible(root, card_header: Mapping, event_id: str, *, lockouts: Sequence[tuple[str, str]] = (),
                      demoted: bool = False) -> bool:
    """Scale thresholds re-anchor only on a declared event (L1786): the event is in the break log with a re-anchor
    kind, effective-dated after the header commit, the header states its re-anchoring window (`reanchor_window`,
    F-21: absent from the section 6.5 schema until M7 defines it), the card is not demoted and its family x market
    is not inside an R-25 lockout. A research-log row can never qualify (different file, no event_id)."""
    ev = next((r for r in _read_jsonl(Path(root) / BREAK_LOG) if r.get("event_id") == event_id), None)
    if ev is None or ev.get("kind") not in REANCHOR_KINDS or demoted:
        return False
    if not str(card_header.get("reanchor_window") or ""):
        return False
    created = str(card_header.get("created_utc") or "")[:10]
    try:
        commit = date.fromisoformat(created)
    except ValueError:
        return False
    if date.fromisoformat(ev["effective_date"]) <= commit:
        return False
    key = (str(card_header.get("family_id") or ""), str(card_header.get("market") or ev.get("market") or ""))
    return key not in {tuple(x) for x in lockouts}


# --------------------------------------------------------------------------- #
# R-18 research log: write only (statistical flag, v1.2 scale flag, BOCPD); no reader exists
# --------------------------------------------------------------------------- #
def log_research(root, kind: str, payload: Mapping, *, decision_utc: datetime, knowledge_utc: datetime,
                 data_snapshot_id: str = "") -> Path:
    path = Path(root) / RESEARCH_LOG
    _append_line(path, {"kind": kind, **dict(payload), "decision_utc": P.iso_utc(decision_utc),
                        "knowledge_utc": P.iso_utc(knowledge_utc), "data_snapshot_id": data_snapshot_id, "acts": False})
    return path


def cusum_flags(x: Sequence[float], *, k: float = 0.5, h: float = 5.0, min_obs: int = 60) -> list[dict]:
    """Two-sided tabular CUSUM on the expanding causal z of `x` (mean / sd of the history before each point); reset
    after an alarm. Log-only defaults (F-20); every row records method and parameters."""
    rows, s_pos, s_neg, hist = [], 0.0, 0.0, []
    for i, xi in enumerate(x):
        z, flag = None, False
        if len(hist) >= min_obs:
            mu, sd = float(np.mean(hist)), float(np.std(hist, ddof=1))
            z = (xi - mu) / sd if sd > 0 else 0.0
            s_pos, s_neg = max(0.0, s_pos + z - k), max(0.0, s_neg - z - k)
            flag = s_pos > h or s_neg > h
            if flag:
                s_pos = s_neg = 0.0
        hist.append(xi)
        rows.append({"kind": "policy_stat_flag", "i": i, "x": float(xi), "z": z, "s_pos": s_pos, "s_neg": s_neg, "flag": flag,
                     "method": "cusum", "params": {"k": k, "h": h, "min_obs": min_obs, "z": "expanding_causal"}})
    return rows


def scale_flag_v12(closes: Sequence[float], *, window: int = 21, median_window: int = 756, run: int = 60) -> dict:
    """The v1.2 trigger demoted to a logged flag (L1787): rv21 above 2x its trailing 3-year median for `run`
    consecutive sessions. Returns the last session's row; `flag` is true from the 60th consecutive session."""
    rv = rv21_series(closes, window)
    length = 0
    for t in range(rv.size):
        med = float(np.median(rv[max(0, t - median_window + 1):t + 1]))
        length = length + 1 if (t + 1 >= min(median_window, 2 * window) and rv[t] > 2.0 * med) else 0
    med = float(np.median(rv[-median_window:])) if rv.size else float("nan")
    return {"kind": "scale_flag_v12", "rv21": float(rv[-1]) if rv.size else None, "median_756": med, "run_length": length,
            "flag": length >= run, "params": {"window": window, "median_window": median_window, "run": run}}


def bocpd_scale_prob(returns: Sequence[float], *, hazard: str = "1/250", prior: tuple[float, float] = (2.0, 1e-4),
                     short_run: int = 21, max_run: int = 1000) -> dict:
    """Adams-MacKay run-length recursion, zero-mean Gaussian returns with an Inverse-Gamma(alpha, beta) variance
    prior, constant hazard; logged value = posterior mass on run length < `short_run`. Research log only (P19)."""
    from scipy.special import gammaln
    num, den = hazard.split("/")
    hz = float(num) / float(den)
    a0, b0 = prior
    R, A, B = np.array([1.0]), np.array([a0]), np.array([b0])
    for x in np.asarray(returns, dtype=float):
        nu, s2 = 2.0 * A, B / A
        pred = np.exp(gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(nu * np.pi * s2) - (nu + 1) / 2 * np.log1p(x * x / (nu * s2)))
        growth = R * pred * (1.0 - hz)
        R = np.concatenate([[float((R * pred * hz).sum())], growth])
        R = R / R.sum() if R.sum() > 0 else np.array([1.0])
        A, B = np.concatenate([[a0], A + 0.5]), np.concatenate([[b0], B + 0.5 * x * x])
        R, A, B = R[:max_run], A[:max_run], B[:max_run]
    return {"kind": "scale_bocpd_prob", "prob": float(R[:short_run].sum()), "hazard": hazard, "prior": list(prior),
            "short_run": short_run, "model": "zero_mean_gaussian_inverse_gamma_variance"}


def ex1_passes(rec: Mapping | None) -> bool:
    """EX1 (L1782): <= 1 false break a decade on 1990-2026 and flags within 6 months of 2012 and 2020."""
    if not isinstance(rec, Mapping):
        return False
    try:
        return (float(rec["false_breaks_per_decade"]) <= 1.0 and bool(rec["flags_within_6m_2012"])
                and bool(rec["flags_within_6m_2020"]) and bool(rec.get("results_md5")))
    except (KeyError, TypeError, ValueError):
        return False


def check_breaks_config(rules=None) -> list[str]:
    """The `breaks` block gate (section 7 L4471-4476). The statistical leg stays log-only until a passing
    `ex1_test` record exists; BOCPD stays log-only and undisplayed; re-anchoring on declared events only."""
    b = _rules_block(rules, "breaks")
    issues = []
    if b.get("policy_trigger") != "official_framework_change":
        issues.append("breaks.policy_trigger must be official_framework_change")
    if b.get("statistical_trigger") != "log_only" and not ex1_passes(b.get("ex1_test")):
        issues.append("breaks.statistical_trigger must stay log_only until EX1's test passes (<= 1 false break a decade "
                      "on 1990-2026; flags within 6 months of 2012 and 2020)")
    if b.get("scale_reanchor") != "declared_events_only":
        issues.append("breaks.scale_reanchor must be declared_events_only")
    bo = b.get("bocpd") or {}
    if bo.get("hazard") != "1/250" or bo.get("log_only") is not True or bo.get("displayed") is not False:
        issues.append("breaks.bocpd must be {hazard: 1/250, log_only: true, displayed: false} (section 10 item 27)")
    return issues
