"""The `macro_daily` steps and gates, the verdict filter, replay, missed decisions, the app-start hook and the
labelled dry run (section 3.9 L1191-1250; R-35; R-19 rules 4-5; R-01 rule 7; section 8.8; TASK-M8-01..M8-07,
the pipeline side of M8-08, M8-12, M8-13; I-01 mechanics, I-03, I-06c bounds_ok clause, T-SCOPE-01, T-OBS-01..05,
T-CARD-03, T-REPLAY-01, T-CLOSE-01 and T-RO-02 workflow clauses; rulings 1, 2, 3.5, 3.11-3.13).

Twelve ordered entries, each `fn(ctx) -> dict` over the injected `Services` (store, registry, clocks, rules store,
book registry, alert store, clock, paths): nine skills and three automatic gates. Everything acting is read through
`contracts.read_input` / `pit_value`; the risk layer is called through `risk_layer.guard_acting` (an exception HALTs
exactly the books it feeds, OPS); `hedge_state` is never wrapped (its exception is the conservative default); the
context writers run through `context_log.run_context_step` (never a HALT); composition is `risk_layer.risk_layer`
(`vt x min(...)`, gross = min(composed, bound)); every artifact reaches disk through `macro_artifacts.write_built`.

State of the world this module is correct in: every card NOT_RUN, D5 pending, notionals null, the repository
UNVERSIONED: `admissions()` admits nothing (check (iii) refuses UNVERSIONED), the recommended book carries invariants
only (vt enters as 1.0). `default_services` wires the sibling hooks: `forward_display` (R-28 / R-29 on the US decision,
R-11 KR / R-12 US; display fields and their own books only, inside `run_context_step`), `forward_books` (each
FORWARD-SIM / refusal book's value; never `engine_feed`), `forward_monitor` (R-25 on the started records under
`<macro_dir>/forward/`; none can start before a header commit) and `lockouts` (`forward.locked_out` on the
governance log). The dry run (`--mode dry_run`) feeds the local vendor cache as `vendor_close` rows into a temp PIT
store, runs KR and US in `run_mode = backtest`, writes under `<macro_dir>/dry_run/` with the red-chip marker, and
keeps every book DISARMED (rulings 1).

Two wall clocks, both entry points: `main()` (the CLI; read once, pinned for the run) and the `on_app_start` default
(the app); every library function takes its clock.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import functools
import json
import os
import shutil
import sys
import tempfile
import threading
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping
from urllib.parse import quote
from zoneinfo import ZoneInfo

import core.calendars as _legacy_cal
from core.calendars import events as EV
from core.calendars import store as CS
from core.engine import books as B
from core.engine.state import EngineMode
from core.ficc import annotations as AN
from core.ficc import context_log as CL
from core.ficc import contracts as C
from core.ficc import lag_audit as LA
from core.ficc import macro_artifacts as MA
from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import cards as CARDS
from core.quant import gate_package as GP
from core.quant import instruments as INS
from core.quant import risk_layer as RL
from core.quant import sleeves as SL
from core.rules import governance as G
from core.rules.macro_rules import load_store
from core.skills import pipeline as PL
from core.skills.alerts import AlertStore, as_artifact

REPO_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = Path(__file__).resolve().parent / "macro_workflows" / "macro_daily.yaml"
CACHE_DIR = REPO_ROOT / "docs" / "asset_expansion" / "cache"
CARDS_ROOT = REPO_ROOT / "docs" / "macro_overlay"
MARKETS = ("KR", "US")                                       # the v2.0 daily markets (US books stay [] while D5 = none)
INSTRUMENT_BOOK = {"KR": "KRX_ETF_line", "US": "US_shares_KIS"}
LINES = {"KR": "069500"}                                     # the sleeve line per market (F-03: no sleeve registry; US none, D5)
NAV_SERIES = {"KR": "KRX_069500_OFFICIAL_CLOSE"}             # NAV_LINE_CLOSES
VT_CARD = {"KR": "MACRO-R06-KR-ETF", "US": "MACRO-R06-US"}
ADMISSION_SERIES = {"R-03": ("MOM_PAPER_LS_SERIES",), "R-06": ("KOSPI_OFFICIAL_CLOSE",), "R-31": ()}
PASS_DISPOSITIONS = ("RECOMMENDATION", "BUILD_AS_INSURANCE")
REFUSED_IN_RECOMMENDED = ("SPECIFICATION_ONLY", "FORWARD_SIM", "REFUSAL_BOOK", "DESCRIPTIVE")
RETRIES_MIN = (1, 5, 15, 60)                                 # data.ingest.retries_min (L4201); one attempt per invocation (F-14)
MONITOR_QUEUE = "forward_monitor_queue.jsonl"
REPLAY_IGNORE = ("run_mode",)                                # the audit's own label (live -> replay), not a datum
GOVERNANCE_LOG = "governance_events.jsonl"
DRY_RUN_MARKER = {"chip": "vendor data, not an official close, not a card run", "source": "docs/asset_expansion/cache",
                  "value_status": "vendor_close", "run_mode": "backtest", "books": "DISARMED"}
# the local vendor files that name a registered series exactly (never a stand-in for another id, P5)
DRY_RUN_CACHE = {"KRX_069500_OFFICIAL_CLOSE": ("yf_069500.KS.csv", "Yahoo"),
                 "KRX_005930_OFFICIAL_CLOSE": ("yf_005930.KS.csv", "Yahoo"),
                 "US_SLEEVE_OFFICIAL_CLOSE": ("yf_SPY.csv", "Yahoo"),
                 "VIXCLS": ("yf__VIX.csv", "Yahoo"), "VXVCLS": ("yf__VIX3M.csv", "Yahoo"),
                 "DEXKOUS": ("fred_DEXKOUS.csv", "FRED")}
UTC = timezone.utc
_STARTED = {"done": False}


class BookSeparationError(ValueError):
    """A book read a multiplier it may never read (I-03; section 10 item 22)."""


# --------------------------------------------------------------------------- #
# Services (constructor-injected; rulings 3.11)
# --------------------------------------------------------------------------- #
@dataclass
class Services:
    macro_dir: Path
    store: P.PITStore
    registry: C.Registry
    clocks: object
    rules: object
    book_registry: B.BookRegistry
    alerts: AlertStore
    clock: Callable[[], datetime]
    cal: object = None                      # a signed CalendarSet (gap tags, event calendar, ARM precondition)
    events: tuple = ()
    cards_root: Path = CARDS_ROOT
    run_mode: str = "live"
    vendor: str | None = None               # the declared vendor whose vendor_close rows a backtest may size on
    lines: Mapping[str, str] = field(default_factory=lambda: dict(LINES))
    baskets: Mapping[str, RL.Basket] | None = None
    nav: Callable | None = None             # (ctx, book_id) -> float | None; default: books.book_nav on the NAV line
    ingest: Callable | None = None          # (ctx) -> dict; the live data.ingest attempt (core.ficc.data._provider_rows)
    hedge_state: Callable = RL.hedge_state
    context_log_builder: Callable = CL.build_context_log
    forward_books: Callable | None = None   # (ctx) -> {books: {forward_sim:/refusal: id: value}}; default `_forward_books`
    forward_monitor: Callable | None = None  # (ctx, queued decision) -> None (R-25); default `_forward_monitor`
    forward_display: Callable | None = None  # (ctx, market) -> {forward_sim, refusal_books, forward_entries, refusal_entries, books}
    harness_hashes_at: Callable = lambda git_hash: None      # harness-source hashes of a git commit (no git here: check (iii) refuses)
    lockouts: Callable = lambda family, market, utc: False   # default_services: forward.locked_out on the governance log
    before_write: Callable | None = None    # test hook: (kind, obj) -> obj (I-06c injections)
    extras: Mapping = field(default_factory=dict)
    arm: bool = True
    session_anchor: list = field(default_factory=list)
    state_root: Path | None = None          # where the previous artifacts are read (a replay reads the live root)

    @property
    def artifacts_root(self) -> Path:
        return Path(self.state_root) if self.state_root is not None else Path(self.macro_dir)

    @property
    def run_log(self) -> Path:
        return Path(self.macro_dir) / PL.RUN_LOG

    @property
    def governance_log(self) -> Path:
        return Path(self.macro_dir) / GOVERNANCE_LOG


def sessions_around(clocks, market: str, anchor: date, back: int = 100, ahead: int = 130) -> list[date]:
    out = []
    for i in range(-back, ahead + 1):
        d = anchor + timedelta(days=i)
        try:
            if clocks.is_session(market, d):
                out.append(d)
        except Exception as exc:                               # noqa: BLE001  (an unsigned calendar is a refusal, not a session)
            raise ValueError(f"{market}: sessions unavailable around {anchor} ({type(exc).__name__}: {exc})") from exc
    return out


def default_services(macro_dir, clock: Callable[[], datetime], *, store=None, registry=None, clocks=None, rules=None,
                     cal=None, events=(), run_mode: str = "live", vendor: str | None = None, extras: Mapping | None = None,
                     arm: bool = True, cards_root=CARDS_ROOT, book_registry=None, alerts=None, **hooks) -> Services:
    """Production wiring under `macro_dir` (the only place a default store or registry is created, rulings 4)."""
    macro_dir = Path(macro_dir)
    registry = registry or C.default_registry()
    if clocks is None:
        from core.calendars.adapter import CalendarClocks
        clocks = CalendarClocks(registry, cal=cal)
    store = store or P.PITStore(macro_dir / "pit", registry=registry, clocks=clocks)
    rules = rules or load_store(rulings_log=macro_dir / GOVERNANCE_LOG)   # the effective store: owner rulings replayed (S1)
    anchor = [clock().date()]
    reg = book_registry or B.BookRegistry(macro_dir, clock=clock, sessions=lambda m: sessions_around(clocks, m, anchor[0]))
    hooks.setdefault("forward_display", _forward_display)
    hooks.setdefault("forward_books", _forward_books)
    hooks.setdefault("forward_monitor", _forward_monitor)
    hooks.setdefault("lockouts", functools.partial(_locked_out, macro_dir / GOVERNANCE_LOG))
    return Services(macro_dir, store, registry, clocks, rules, reg, alerts or AlertStore(macro_dir), clock, cal=cal,
                    events=tuple(events), cards_root=Path(cards_root), run_mode=run_mode, vendor=vendor,
                    extras=dict(extras or {}), arm=arm, session_anchor=anchor, **hooks)


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _served(ctx) -> tuple[str, str]:
    return f"recommended:{ctx.market}", f"specification:{ctx.market}"


def _rctx(ctx) -> P.RunContext:
    return P.RunContext(ctx.decision_utc, ctx.knowledge_utc, ctx.run_mode)


def _registered(reg: B.BookRegistry, books: Iterable[str]) -> tuple[str, ...]:
    ids = set(reg.ids())
    return tuple(b for b in books if b in ids)


def _alert(ctx, code: str, severity: str, component: str, *, series_id=None, books=(), detail: str = "",
           escalated: bool = False) -> dict:
    """One alert: a per-decision record for `macro_state.alerts[]` (deterministic id) + the persisted store row."""
    a = RL.alert(code, component, ctx.decision_utc, series_id=series_id, books=tuple(books), severity=severity,
                 escalated=escalated)
    ctx.state.setdefault("state_alerts", []).append(a)
    ctx.services.alerts.record_from(a, ctx.decision_utc, detail=detail)
    return a


def _consumer_for(b: C.Binding) -> str:
    return b.consumer or {"acting_exposure": "nav", "risk_model": "hedge_state", "forward_sim": "R-28_R-29",
                          "context": "display", "history": "R-22"}[b.role]


def _book_dict(book: B.BookRuntime) -> dict:
    d = dataclasses.asdict(book)
    d["mode"] = book.mode.value
    d["post_rearm_cap_until"] = book.post_rearm_cap_until.isoformat() if book.post_rearm_cap_until else None
    return d


def _book_from(d: Mapping) -> B.BookRuntime:
    d = dict(d)
    d["mode"] = EngineMode(d["mode"])
    d["post_rearm_cap_until"] = date.fromisoformat(d["post_rearm_cap_until"]) if d.get("post_rearm_cap_until") else None
    return B.BookRuntime(**d)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def previous_state(root, market: str, before: date) -> dict | None:
    """The latest written macro_state of the market decided before `before` (the carried state)."""
    d = Path(root) / "macro_state" / market
    if not d.is_dir():
        return None
    files = sorted(p for p in d.glob("*.json") if p.stem < before.isoformat())
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def _vt_carrier(market: str, rules, series_id: str | None) -> RL.VTResult:
    """A VTResult with no sigma for a decision whose close could not be read (the state carries the previous vt)."""
    block = rules.get("vol_target")
    p = block.get(market) or block["other_markets"]
    target = p.get("target_ann")
    return RL.VTResult(market, "sma20", "insufficient_history", None, float(target) if target else 0.0, None, 0, None, None,
                       "total", (), series_id or "", (), "fail_closed: close not read")


# --------------------------------------------------------------------------- #
# Verdict filter: admissions (R-35; TASK-M8-02; T-CARD-03; F-1, F-4, F-27)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AdmissionResult:
    admitted: dict                      # book_id -> tuple of rule ids
    refused: dict                       # rule_id -> reason
    integrity_failures: tuple           # rule ids that are PASS on paper but failed (i)-(iii)
    chain_ok: bool
    series: dict                        # acting series id -> True for every admitted factor (R-19 rule 5)


def load_cards(root) -> dict[str, dict | None]:
    """card_id -> the highest committed card file (raw JSON, re-hashed by `admissions`), None before a formal run."""
    out = {}
    for spec in CARDS.REGISTRY:
        files = sorted(CARDS.card_path(root, spec.card_id, 0).parent.glob(f"{spec.card_id}.r*.json")) if root else []
        out[spec.card_id] = json.loads(files[-1].read_text(encoding="utf-8")) if files else None
    return out


def verdict_rows(root) -> tuple[list[dict], bool]:
    """(rows, chain_ok) of cards/verdicts.jsonl; a broken chain blocks every admission until restored (T-CARD-03)."""
    path = CARDS.verdicts_path(root)
    check = CARDS.chain_verify(path, CARDS.VERDICT_ROW)
    if not check.ok:
        return [], False
    return CARDS.read_chain(path, CARDS.VERDICT_ROW), True


def package_of(store, macro_dir=None) -> dict:
    """`gate.package` with `status` from `gate_package.package_state` (NOT_FROZEN | FROZEN | BLOCKED; the one state
    reader) plus the manifest's harness-source hashes (what check (iii) compares a commit against)."""
    pkg = dict(store.get("gate.package"))
    pkg["status"] = GP.package_state(store, macro_dir)
    pkg["harness_sources"] = GP.build_manifest(store)["harness_sources"]
    return pkg


def admissions(cards: Mapping[str, dict | None], rows: list[dict], package: Mapping, *, snapshot_id_at: Callable,
               harness_hashes_at: Callable, lockouts: Callable, decision_utc: datetime, chain_ok: bool = True,
               archive_check: Callable | None = None) -> AdmissionResult:
    """Pure admission rule for the recommended book (R-35): PASS with disposition RECOMMENDATION / BUILD_AS_INSURANCE,
    or an R-31 step with disposition INVARIANT_STEP; authenticated by (i) results_md5 + chain, (ii) the frozen
    package md5, (iii) the reproducible snapshot and a git commit whose harness sources hash to the manifest.
    Everything else stays in the specification book; a PASS that fails (i)-(iii) is an integrity failure."""
    frozen = package.get("status") == "FROZEN" and isinstance(package.get("definitions_md5"), str) \
        and package.get("definitions_md5") != "written_at_freeze"
    by_row = {(r.get("card_id"), r.get("revision"), r.get("results_md5")): r for r in rows}
    admitted: dict[str, list[str]] = {}
    refused: dict[str, str] = {}
    integrity: list[str] = []
    for spec in CARDS.REGISTRY:
        card = cards.get(spec.card_id)
        rule = spec.rule_id
        if card is None:
            refused[rule] = f"{spec.card_id}: {spec.verdict} ({spec.disposition}); no formal run"
            continue
        verdict, disp = card.get("verdict"), card.get("disposition")
        pass_like = verdict == "PASS" and disp in PASS_DISPOSITIONS
        invariant = spec.family_id == "R-31" and disp == "INVARIANT_STEP"
        if card.get("build_status_on_pass") == "BUILD_AS_INSURANCE" and verdict in ("NOT_RUN", "INSUFFICIENT_DATA"):
            refused[rule] = f"{spec.card_id}: BUILD_AS_INSURANCE while {verdict}: refused (L3770)"
            continue
        if not (pass_like or invariant):
            refused[rule] = f"{spec.card_id}: {verdict} / {disp}: stays in the specification book"
            continue
        reasons = []
        if MS.results_md5(card) != card.get("results_md5"):
            reasons.append("(i) the card file does not re-hash to its committed results_md5")
        if not chain_ok:
            reasons.append("(i) cards/verdicts.jsonl chain broken: every admission blocked until restored")
        else:
            row = by_row.get((card.get("card_id"), card.get("revision"), card.get("results_md5")))
            if row is None:
                reasons.append("(i) no verdict row for this card revision and results_md5")
            elif row.get("verdict") != verdict:
                reasons.append(f"(i) verdict row says {row.get('verdict')}, the card file says {verdict}")
        if not frozen:
            reasons.append("(ii) gate.package is not FROZEN")
        elif card.get("gate_package_md5") != package.get("definitions_md5"):
            reasons.append("(ii) gate_package_md5 differs from the frozen definitions_md5")
        try:
            snap = snapshot_id_at(card.get("knowledge_utc"))
        except Exception as exc:                               # noqa: BLE001
            snap = f"unavailable: {type(exc).__name__}: {exc}"
        if snap != card.get("data_snapshot_id"):
            reasons.append("(iii) data_snapshot_id does not reproduce from the store at the card's knowledge_utc")
        if archive_check is not None:
            why = archive_check(card)
            if why:
                reasons.append(f"(iii) {why}")
        gh = card.get("git_hash")
        if not gh or gh == MA.GIT_HASH:
            reasons.append("(iii) git_hash UNVERSIONED: owner must place the repository under git (rulings 3.1)")
        else:
            hashes = harness_hashes_at(gh)
            if not hashes or hashes != package.get("harness_sources"):
                reasons.append("(iii) git_hash is not a commit whose harness sources hash to the package manifest")
        if reasons:
            refused[rule] = f"{spec.card_id}: " + "; ".join(reasons)
            integrity.append(rule)
            continue
        if lockouts(spec.family_id, spec.market, decision_utc):
            refused[rule] = f"{spec.card_id}: family {spec.family_id} x {spec.market} locked out after a demotion (R-25)"
            continue
        admitted.setdefault(f"recommended:{spec.market}", []).append(rule)
    series = {}
    for book, rules in admitted.items():
        for rule in rules:
            fam = "-".join(rule.split("-")[:2])
            for sid in ADMISSION_SERIES.get(fam, ()):
                series[sid] = True
    return AdmissionResult({b: tuple(v) for b, v in admitted.items()}, refused, tuple(integrity), chain_ok, series)


def check_bindings(registry: C.Registry, result: AdmissionResult, derived: Mapping[str, tuple]) -> None:
    """Load-time assertion (T-SCOPE-01 (g)): a book that reads a factor whose acting inputs are not bound to it is
    refused."""
    for book, rules in result.admitted.items():
        for rule in rules:
            fam = "-".join(rule.split("-")[:2])
            for sid in ADMISSION_SERIES.get(fam, ()):
                bound = [v for k, v in derived.items() if k.startswith(sid + "|")]
                if not bound or not any(book in v for v in bound):
                    raise BookSeparationError(f"{book} reads {rule} but its acting input {sid} is not bound to it (R-19 rule 5)")


def compute_admissions(s: Services, ctx) -> AdmissionResult:
    cards = load_cards(s.cards_root)
    rows, ok = verdict_rows(s.cards_root)

    def archive_check(card) -> str | None:
        try:
            CARDS.verify_archive(s.cards_root, card)
            return None
        except CARDS.ArchiveLost as exc:
            return "; ".join(exc.reasons)
        except Exception as exc:                               # noqa: BLE001
            return f"archive unreadable: {type(exc).__name__}: {exc}"
    return admissions(cards, rows, package_of(s.rules, s.artifacts_root), decision_utc=ctx.decision_utc, chain_ok=ok,
                      snapshot_id_at=lambda k: P.data_snapshot_id(s.store, P.parse_utc(k)),
                      harness_hashes_at=s.harness_hashes_at, lockouts=s.lockouts, archive_check=archive_check)


# --------------------------------------------------------------------------- #
# Book separation (I-03; TASK-M8-03 runtime half; section 10 item 22)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FactorRead:
    rule_id: str
    verdict: str
    disposition: str
    source_book_kind: str              # recommended | specification | forward_sim | refusal


def assert_book_separation(book_id: str, reads: Iterable[FactorRead]) -> None:
    kind, _ = B.parse_book_id(book_id)
    for r in reads:
        why = None
        if kind == "recommended":
            if r.source_book_kind != "recommended":
                why = f"a {r.source_book_kind} multiplier"
            elif r.rule_id.startswith("R-04") or r.disposition in REFUSED_IN_RECOMMENDED:
                why = f"{r.rule_id} with disposition {r.disposition}"
            elif not ((r.verdict == "PASS" and r.disposition in PASS_DISPOSITIONS)
                      or (r.disposition == "INVARIANT_STEP" and r.rule_id.startswith("R-31"))):
                why = f"a non-PASS factor ({r.verdict} / {r.disposition})"
        elif kind == "specification":
            if r.source_book_kind in ("forward_sim", "refusal") or r.rule_id.startswith(("R-11", "R-12")) \
                    or r.disposition in ("FORWARD_SIM", "REFUSAL_BOOK"):
                why = f"{r.rule_id}: a FORWARD-SIM card's factor or a refusal multiplier"
        elif kind == "forward_sim":
            if r.source_book_kind == "refusal" or r.disposition == "REFUSAL_BOOK" or r.rule_id.startswith(("R-11", "R-12")):
                why = f"{r.rule_id}: a refusal multiplier"
        elif kind == "refusal" and r.source_book_kind != "refusal":
            why = f"{r.rule_id}: a refusal book reads its own multiplier only"
        if why:
            raise BookSeparationError(f"{book_id} may never read {why} (P7, L3770, section 10 item 22)")


# --------------------------------------------------------------------------- #
# (1) macro.pit_snapshot
# --------------------------------------------------------------------------- #
def on_start(ctx) -> None:
    """The runner's first act: the served books' state before the decision (HALT pages, the replay restore point)."""
    reg = ctx.services.book_registry
    ctx.state["modes_before"] = {b: reg.get(b).mode.value for b in _registered(reg, _served(ctx))}
    ctx.state["books_before"] = {b: _book_dict(reg.get(b)) for b in _registered(reg, _served(ctx))}


def pit_snapshot(ctx) -> dict:
    s: Services = ctx.services
    try:
        deadline = PL.next_open_utc(s.clocks, ctx.market, ctx.session_date) - timedelta(minutes=30)
    except Exception:                                          # noqa: BLE001
        deadline = None
    schedule = {"trigger": "pit_snapshot", "attempt": 1, "retries_min": list(RETRIES_MIN),
                "decision_deadline": PL.iso(deadline), "one_attempt_per_invocation": True}
    report = None
    if ctx.run_mode == "live" and s.ingest is not None:
        report = s.ingest(ctx)                                 # one attempt; the retries ladder re-invokes the run (F-14)
    flags = (report or {}).get("flags", ()) if isinstance(report, Mapping) else ()
    ctx.state["stale_carry"] = tuple(f.obs_date for f in flags if getattr(f, "code", "") == "stale_carry")
    if ctx.run_mode == "live":
        ctx.pin_knowledge(ctx.clock())                         # the end of the fetches (L1002)
    elif ctx.knowledge_utc is None:
        raise ValueError(f"run_mode {ctx.run_mode}: knowledge_utc must be given (the artifact's, never now)")
    rctx = _rctx(ctx)
    adm = compute_admissions(s, ctx)
    derived = C.derive_bindings(s.registry, adm.series)
    check_bindings(s.registry, adm, derived)
    ctx.state.update(admissions=adm, derived_bindings=derived)
    inputs, bindings = {}, {}
    for sid in s.registry.series_ids():
        market = s.registry.market(sid)
        close = s.registry.obs_kind(sid) == "close"
        for b in s.registry.bindings(sid):
            if b.role == "history":
                continue
            if b.role == "acting_exposure" and market not in (None, ctx.market):
                continue                                       # another market's close is not decided at this close
            key = (sid, b.consumer)
            consumer = _consumer_for(b)
            resolved = s.registry.resolve_binding(sid, consumer)   # a shared consumer resolves to the acting binding (R-19 rule 5)
            req = ctx.session_date if (close and resolved.role == "acting_exposure") else None
            if resolved.role == "acting_exposure" and market not in (None, ctx.market):
                continue
            try:
                v = C.read_input(s.store, s.registry, sid, rctx, consumer, s.clocks, require_session=req, vendor=s.vendor)
            except Exception as exc:                           # noqa: BLE001  (a raising read is a missing input)
                v = P.MissingInput(sid, "missing", b.role, tuple(s.registry.book_ids(b)), detail=f"{type(exc).__name__}: {exc}")
            inputs[key], bindings[key] = v, b
    ctx.state.update(inputs=inputs, bindings=bindings)
    n_missing = sum(isinstance(v, P.MissingInput) for v in inputs.values())
    return {"status": "ok", "schedule": schedule, "knowledge_utc": PL.iso(ctx.knowledge_utc), "n_read": len(inputs),
            "n_missing": n_missing, "admitted": adm.admitted, "refused": adm.refused}


# --------------------------------------------------------------------------- #
# (2) gate data_ok (R-19 rule 4 by role and book)
# --------------------------------------------------------------------------- #
def data_ok(ctx) -> dict:
    s: Services = ctx.services
    derived = ctx.state["derived_bindings"]
    failed_by_book: dict[str, dict[str, int]] = {}
    components, forward_failed, labels = [], {}, []
    hedge_off = False
    for (sid, consumer), v in ctx.state["inputs"].items():
        b = ctx.state["bindings"][(sid, consumer)]
        fa = C.on_input_failure(sid, v, b)
        books = tuple(derived.get(f"{sid}|{b.consumer or '*'}", ())) if b.role == "acting_exposure" else tuple(s.registry.book_ids(b))
        if fa.status in ("ok", "disputed"):
            if fa.status == "disputed":
                _alert(ctx, "INPUT_DISPUTED", "warn", "data_ok", series_id=sid, books=books)
            continue
        if fa.role == "acting_exposure":
            for book in books:
                failed_by_book.setdefault(book, {})[sid] = b.halt_after_consecutive_decisions
            components.append({"series_id": sid, "status": fa.status, "books": list(books), "detail": fa.sets.get("detail", "")})
            _alert(ctx, "ACTING_INPUT_FAIL_CLOSED", "warn", "data_ok", series_id=sid, books=books, detail=fa.sets.get("detail", ""))
        elif fa.role == "risk_model":
            if fa.sets.get("hedge_credit_off"):
                hedge_off = True
            _alert(ctx, "RISK_MODEL_INPUT_STALE", "warn", "data_ok", series_id=sid, detail=fa.action)
        elif fa.role == "forward_sim":
            for book in books:
                forward_failed.setdefault(book, []).append(sid)
            _alert(ctx, "FORWARD_SIM_INPUT_FAIL_CLOSED", "warn", "data_ok", series_id=sid, books=books)
        else:
            labels.append({"series_id": sid, "status": fa.status})
    ctx.state.update(failed_by_book=failed_by_book, fail_closed=components, forward_failed=forward_failed,
                     context_labels=labels, hedge_credit_off=hedge_off)
    return {"status": "fail_closed" if components else "pass", "fail_closed": components, "forward_failed": forward_failed,
            "hedge_credit_off": hedge_off, "context_stale": labels}


# --------------------------------------------------------------------------- #
# (3) macro.lag_audit (independent of pit_value; T-LAG-01 runtime clause)
# --------------------------------------------------------------------------- #
def lag_audit(ctx) -> dict:
    s: Services = ctx.services
    reg = s.book_registry
    values = [v for v in ctx.state["inputs"].values() if isinstance(v, P.PITValue)]
    rep = LA.lag_audit(values, _rctx(ctx), ctx.market, s.registry, s.clocks)   # backtest: LookAheadError raises (a step error)
    roles = {}
    for (sid, _), b in ctx.state["bindings"].items():
        roles.setdefault(sid, set()).add(b.role)
    halted, hedge = [], False
    for x in rep["violations"]:
        sid = x["series_id"]
        if "acting_exposure" in roles.get(sid, ()):
            books = {b for k, v in ctx.state["derived_bindings"].items() if k.startswith(sid + "|") for b in v}
            for b in _registered(reg, sorted(books)):
                B.runtime_halt(reg, b, "OPS", "lag_audit_violation", ctx.decision_utc, component="macro.lag_audit", series_id=sid)
                halted.append(b)
            _alert(ctx, "LAG_AUDIT_VIOLATION", "page", "macro.lag_audit", series_id=sid, books=sorted(books), detail=x["check"])
        elif "risk_model" in roles.get(sid, ()):
            hedge = True
            _alert(ctx, "LAG_AUDIT_VIOLATION", "warn", "macro.lag_audit", series_id=sid, detail=x["check"])
    ctx.state["lag_audit"] = {"checked": rep["checked"], "violations": rep["violations"]}
    if hedge:
        ctx.state["hedge_credit_off"] = True
    return {"status": "fail" if rep["violations"] else "pass", "checked": rep["checked"], "violations": rep["violations"],
            "halted": sorted(set(halted))}


# --------------------------------------------------------------------------- #
# (4) macro.vol_and_overlays (M2 / M4 / M5 producers; composition by min())
# --------------------------------------------------------------------------- #
def _default_nav(ctx, book_id: str) -> float | None:
    s: Services = ctx.services
    sid, line = NAV_SERIES.get(ctx.market), s.lines.get(ctx.market)
    returns, costs = None, {}
    if sid and line:
        rows = [r for r in P.pit_window(s.store, sid, ctx.decision_utc, ctx.knowledge_utc, registry=s.registry, statuses=P.CLOSE_STATUSES)
                if RL._close_ok(r, ctx.run_mode, s.vendor)][-2:]     # official closes only (the declared vendor in a backtest, L1319)
        if len(rows) == 2 and rows[-1].obs_date == ctx.session_date:
            returns = {line: rows[-1].value / rows[-2].value - 1.0}
            try:
                costs = {line: INS.cost_per_side(INSTRUMENT_BOOK[ctx.market], price=rows[-1].value, on=ctx.session_date).bp}
            except Exception:                                  # noqa: BLE001  (an owner tick table: the cost stays unknown)
                costs = {}
    return B.book_nav(s.book_registry, book_id, returns, costs)


def _concentration(ctx, line: str | None):
    s: Services = ctx.services
    if ctx.market != "KR" or not line:
        return None, None
    basket = (s.baskets or {}).get(line)
    if basket is None:
        return None, {"component": "concentration_bound", "fail_closed": True,
                      "detail": "KODEX200_PDF basket not available (owner data item): no bound computed"}
    books = _registered(s.book_registry, _served(ctx))
    exp = RL.guard_acting("core/quant/risk_layer", books, s.book_registry, ctx.decision_utc, RL.lookthrough_exposure,
                          {line: 1.0}, {line: basket}, ctx.decision_utc, sessions=s.book_registry.sessions(ctx.market))
    if isinstance(exp, RL.ActingFailure):
        return None, exp
    if exp.fail_closed:
        return None, {"component": "lookthrough_exposure", "fail_closed": True, "detail": "; ".join(exp.reasons)}
    cb = RL.guard_acting("core/quant/risk_layer", books, s.book_registry, ctx.decision_utc, RL.concentration_bound,
                         ctx.market, ctx.decision_utc, None, exp, rules=s.rules)
    return (None, cb) if isinstance(cb, RL.ActingFailure) else (cb, None)


def vol_and_overlays(ctx) -> dict:
    s: Services = ctx.services
    reg, m, dec, knw = s.book_registry, ctx.market, ctx.decision_utc, ctx.knowledge_utc
    rec, spec = _served(ctx)
    adm: AdmissionResult = ctx.state["admissions"]
    prev = previous_state(s.artifacts_root, m, ctx.session_date)
    ctx.state["previous"] = prev
    failed_by_book = ctx.state.setdefault("failed_by_book", {})
    failures: list = []
    # vt (R-06) through the guard: an exception HALTs the books the close feeds (OPS)
    vt_sid = RL.VT_SERIES.get(m)
    vt_books = _registered(reg, s.registry.book_ids(s.registry.resolve_binding(vt_sid, RL.VT_CONSUMER))) if vt_sid else ()
    armed_spec, armed_rec = B.ever_armed(reg, spec), B.ever_armed(reg, rec)
    vt = RL.guard_acting("core/quant/risk_layer", vt_books, reg, dec, RL.market_vol_target, s.store, s.registry, s.clocks, m,
                         dec, knw, book_ever_armed=armed_spec, rules=s.rules, run_mode=ctx.run_mode, vendor=s.vendor,
                         stale_carry=ctx.state.get("stale_carry", ())) if vt_sid else \
        P.MissingInput(f"VT:{m}", "missing", "acting_exposure", (), detail="no R-06 close series registered for the market")
    if isinstance(vt, RL.ActingFailure):
        failures.append(vt)
        ctx.state.setdefault("state_alerts", []).append(vt.alert)
        vt_res = P.MissingInput(vt_sid, "missing", "acting_exposure", vt_books, detail=vt.error)
    else:
        vt_res = vt
    prev_vt = ((prev or {}).get("vol") or {}).get("vt_weight_next")
    book_spec = RL.vt_for_book(vt_res, spec, ever_armed=armed_spec, prev_weight=prev_vt)
    if book_spec.missing is not None:
        for b in vt_books:
            failed_by_book.setdefault(b, {})[book_spec.missing.series_id] = C.DEFAULT_HALT_AFTER
    r06 = any(r.startswith("R-06") for r in adm.admitted.get(rec, ()))
    vt_rec = (book_spec.weight if book_spec.weight is not None else 0.0) if r06 else 1.0
    # hedge state (R-09): never wrapped by the guard; a raising hook is the conservative default (E4)
    try:
        hedge = s.hedge_state(s.store, s.registry, dec, knw, clocks=s.clocks, run_mode=ctx.run_mode, rules=s.rules)
    except Exception as exc:                                   # noqa: BLE001
        hedge = RL.HedgeState(True, False, False, None, ("risk_model_exception",), (), None, None,
                              (RL.alert("HEDGE_STATE_EXCEPTION", "hedge_state", dec, severity="warn"),), (),
                              (f"exception inside hedge_state: {type(exc).__name__}: {exc}",))
    if ctx.state.get("hedge_credit_off") and not hedge.hedge_credit_off:
        hedge = replace(hedge, hedge_credit_off=True, hedge_reasons=tuple(hedge.hedge_reasons) + ("risk_model_input_stale",))
    # vs / dm (R-03 / R-04): the momentum paper series of the market, specification book only
    vs, dm = {}, None
    if (m, "momentum") in SL.PAPER_SERIES:
        r = SL.sleeve_vol_scale(s.store, s.registry, m, "momentum", dec, knw, armed=armed_spec)
        vs["momentum"] = r
        if isinstance(r, P.MissingInput):
            for b in _registered(reg, r.books or (spec,)):
                failed_by_book.setdefault(b, {})[r.series_id] = C.DEFAULT_HALT_AFTER
        d = SL.dm_gate(s.store, s.registry, m, dec, knw, armed=armed_spec)
        if isinstance(d, P.MissingInput):
            for b in _registered(reg, d.books or (spec,)):
                failed_by_book.setdefault(b, {})[d.series_id] = C.DEFAULT_HALT_AFTER
        else:
            dm = d
    # the market line (F-03: one long-only line per market until a sleeve registry exists; US none while D5 = none)
    line = s.lines.get(m)
    cb, conc_note = _concentration(ctx, line)
    if isinstance(conc_note, RL.ActingFailure):
        failures.append(conc_note)
        ctx.state.setdefault("state_alerts", []).append(conc_note.alert)
    # per served book: NAV, R-07 / R-31 step, ladder term, cap, composition (min), gross target
    factors, targets, risk = {}, {}, {}
    nav_fn = s.nav or _default_nav
    for bid in _registered(reg, (rec, spec)):
        nav = nav_fn(ctx, bid)
        res = B.risk_step(reg, bid, dec, nav, rules=s.rules)
        if res.alert is not None:
            ctx.state.setdefault("state_alerts", []).append(res.alert)
            s.alerts.record_from(res.alert, dec)
        # R-31 steps act in the recommended book only once admitted (PASS, or INVARIANT_STEP at a frozen share <= 0.10:
        # verdict_filter authenticated the card, so the admission carries the frozen share; F-2)
        ladder, block = RL.ladder_for_book(res.ladder, bid, r31_pass=any(r.startswith("R-31") for r in adm.admitted.get(rec, ())))
        cap = B.post_rearm_cap(res.book)
        vt_b = vt_rec if bid == rec else (book_spec.weight if book_spec.weight is not None else 0.0)
        overlays: dict[str, float] = {}                        # total-basis overlays: none acts in v2.0 (R-28 / R-29 own books)
        reads = [FactorRead(d.rule_id, d.card.get("verdict", "NOT_RUN"), d.card.get("disposition", ""), "specification")
                 for d in ([dm] if dm is not None and bid == spec else [])]
        assert_book_separation(bid, reads)
        halted = reg.get(bid).halted
        factors[bid] = {"vt": vt_b, "overlays": overlays, "ladder": ladder, "post_rearm_cap": cap, "halted": halted}
        risk[bid] = {"ladder": res.ladder, "block": block, "nav": nav, "halted_now": res.halted_now}
        if line:
            g = RL.guard_acting("core/quant/risk_layer", (bid,), reg, dec, RL.risk_layer, vt_b, overlays, ladder, cap, cb, halted=halted)
            if isinstance(g, RL.ActingFailure):
                failures.append(g)
                ctx.state.setdefault("state_alerts", []).append(g.alert)
                targets[bid] = None
            else:
                targets[bid] = {line: float(g["gross"])}
    disp = {}
    if s.forward_display is not None:
        disp = CL.run_context_step("forward_display", s.forward_display, ctx, m).value or {}
    ctx.state.update(vt=vt, vt_res=vt_res, book_spec=book_spec, vt_rec=vt_rec, r06=r06, hedge=hedge, vs=vs, dm=dm,
                     cb=cb, conc_note=conc_note if isinstance(conc_note, dict) else None, factors=factors, targets=targets,
                     risk=risk, failures=failures, forward_display=disp)
    return {"status": "ok", "vt_status": book_spec.vt_status, "vt_weight_next": book_spec.weight, "vt_rec": vt_rec,
            "hedge_credit_off": hedge.hedge_credit_off, "by_book": {b: {k: v for k, v in f.items() if k != "overlays"} for b, f in factors.items()},
            "targets": targets, "acting_failures": [f.component for f in failures]}


# --------------------------------------------------------------------------- #
# (5) macro.build_artifacts (M6 builders; always written, also after an acting error)
# --------------------------------------------------------------------------- #
def _write(ctx, kind: str, obj: dict):
    s: Services = ctx.services
    if s.before_write is not None:
        obj = s.before_write(kind, obj)
    out = MA.write_built(s.macro_dir, kind, obj, ctx.clock)
    ctx.state.setdefault("written", []).append((out, obj))
    if out.path is not None:
        ctx.artifacts.append(Path(out.path).relative_to(s.macro_dir).as_posix())
    return out


def build_artifacts(ctx) -> dict:
    s: Services = ctx.services
    if ctx.knowledge_utc is None and ctx.run_mode == "live":
        ctx.pin_knowledge(ctx.clock())                         # pit_snapshot raised before pinning: the fail_closed artifact still carries an instant
    st, m, dec, knw = ctx.state, ctx.market, ctx.decision_utc, ctx.knowledge_utc
    reg, rctx = s.book_registry, _rctx(ctx)
    rec, spec = _served(ctx)
    prov = MA.provenance(clock=ctx.clock, knowledge_utc=P.iso_utc(knw), config_hash=s.rules.config_hash,
                         data_snapshot_id=P.data_snapshot_id(s.store, knw))
    st["provenance"] = prov
    effective = PL.next_session(s.clocks, m, ctx.session_date)
    prev = st.get("previous") if "previous" in st else previous_state(s.artifacts_root, m, ctx.session_date)
    prev_vt = ((prev or {}).get("vol") or {}).get("vt_weight_next")
    vt_sid = RL.VT_SERIES.get(m)
    vt_res = st.get("vt_res")
    book_spec = st.get("book_spec") or RL.BookVT(spec, prev_vt, "fail_closed", True,
                                                  P.MissingInput(vt_sid or f"VT:{m}", "missing", "acting_exposure", (), detail="acting step error"))
    vtr = vt_res if isinstance(vt_res, RL.VTResult) else _vt_carrier(m, s.rules, vt_sid)
    bk = book_spec if book_spec.weight is not None else replace(book_spec, weight=float(prev_vt) if prev_vt is not None else 0.0)
    vol = RL.vol_state(vtr, bk, None, instrument_book=INSTRUMENT_BOOK[m], rebalance="daily", no_trade_band=0.0,
                       recommended_pass=bool(st.get("r06")))
    hedge = st.get("hedge") or RL.HedgeState(True, False, False, None, ("risk_model_input_stale",), (), None, None, (), (),
                                              ("hedge_state not run: acting step error",))
    runtime = [e for e in reg.runtime_entries() if e["book_id"] in (rec, spec)]
    factors = st.get("factors") or {b: {"vt": 1.0 if b == rec else bk.weight, "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0,
                                        "halted": reg.get(b).halted} for b in _registered(reg, (rec, spec))}
    gap = None
    if s.cal is not None and m == "KR":
        gap = CL.run_context_step("gap_tags", EV.gap_tags, effective, s.events, cal=s.cal, cfg=s.rules.get("events")).value
    ann = CL.run_context_step("annotations", lambda: AN.vix_ge_vix3m(s.store, dec, knw, registry=s.registry, run_mode=ctx.run_mode).macro_state_block()).value
    regime = None
    if s.cal is not None and m == "KR":
        from core.calendars import regime as RG
        regime = CL.run_context_step("regime_tags", RG.regime_tags, "KR", ctx.session_date, cal=s.cal).value
    inputs = [v for v in st.get("inputs", {}).values() if isinstance(v, P.PITValue) and v.role != "context"]
    comps = [bk] + list(st.get("failures", ()))
    if ctx.acting_error:
        comps.append(RL.ActingFailure("macro_daily", "acting step error", (rec, spec), {}, True))
    disp = st.get("forward_display") or {}
    dm = st.get("dm")
    adm: AdmissionResult | None = st.get("admissions")
    extras = {**dict(s.extras), "derived_bindings": {k: list(v) for k, v in (st.get("derived_bindings") or {}).items()},
              "admissions": {"admitted": adm.admitted if adm else {}, "refused": adm.refused if adm else {}},
              "fail_closed_inputs": st.get("fail_closed", []), "forward_failed": st.get("forward_failed", {}),
              "context_labels": st.get("context_labels", []), "concentration_note": st.get("conc_note"),
              "acting_error": bool(ctx.acting_error)}
    state = MA.build_macro_state(m, rctx, provenance=prov, decided_session=ctx.session_date, effective_session=effective, vol=vol,
                                 hedge=hedge, runtime=runtime, rules=s.rules, book_factors=factors, concentration=st.get("cb"),
                                 gap=gap, ladder=B.ladder_state(reg.get(spec)) if spec in reg.ids() else None, inputs=inputs,
                                 lag_audit=st.get("lag_audit"), alerts=st.get("state_alerts", []), annotations=ann,
                                 dm_bear_state=(dm.flags.get("dm_bear_state") if dm is not None else None),
                                 refusal_books=disp.get("refusal_books"), forward_sim=disp.get("forward_sim"),
                                 acting_components=comps, regime_tags=regime, extras=extras, registry=s.registry, clocks=s.clocks)
    if ctx.acting_error or any(st.get("failed_by_book", {}).values()) or (st.get("conc_note") or {}).get("fail_closed"):
        state["fail_closed"] = True                            # any acting input failed closed (R-01 rule 6; T-MISS-02, T-ROLE-01)
    st["macro_state_obj"] = state
    spec_f = factors.get(spec, {"ladder": 1.0, "post_rearm_cap": 1.0})
    vt_card = CL.run_context_step("vt_card", CARDS.card_status, s.cards_root, VT_CARD[m], s.rules).value
    ladder_card = CL.run_context_step("ladder_card", CARDS.card_status, s.cards_root, "MACRO-R31-KR-ETF", s.rules).value if m == "KR" else None
    ods = MA.build_overlay_decisions(m, rctx, provenance=prov, effective_session=effective, vt=bk, vt_card=vt_card,
                                     vs=st.get("vs", {}), multipliers=[dm] if dm is not None else [], ladder=spec_f["ladder"],
                                     post_rearm_cap=spec_f["post_rearm_cap"], ladder_card=ladder_card,
                                     concentration_bound=(st["cb"].bound if st.get("cb") is not None else None),
                                     forward_sim=disp.get("forward_entries", ()), refusal=disp.get("refusal_entries", ()),
                                     neutralised=B.neutralised_rules(reg, spec) if spec in reg.ids() else None,
                                     registry=s.registry, clocks=s.clocks, extras=dict(s.extras))
    st["overlay_objs"] = ods
    outs = [_write(ctx, "macro_state", state)] + [_write(ctx, "overlay_decision", o) for o in ods]
    # context writers: through the isolation guard, quarantine on failure, never a HALT
    builder = functools.partial(s.context_log_builder, clock=ctx.clock)      # run_context_step consumes `clock` itself
    ctx_res = CL.run_context_step("context_log", builder, s.store, s.registry, dec, knw, clocks=s.clocks, rules=s.rules,
                                  run_mode=ctx.run_mode, run_log=s.run_log, decision_utc=dec)
    context = {"status": "error", "error": ctx_res.error}
    if ctx_res.ok:
        log = dict(ctx_res.value)
        log["extras"] = {**dict(log.get("extras") or {}), **dict(s.extras)}
        w = CL.run_context_step("context_log_write", CL.write_context_log, s.macro_dir, log, ctx.clock, run_log=s.run_log, decision_utc=dec)
        if w.ok:
            cw = w.value
            context = {"status": cw.status, "path": str(cw.path)}
            if cw.status == "written":
                ctx.artifacts.append(Path(cw.path).relative_to(s.macro_dir).as_posix())
            elif cw.alert is not None:
                _alert(ctx, cw.alert["code"], "warn", CL.COMPONENT, detail="; ".join(cw.issues))
        else:
            context = {"status": "error", "error": w.error}
    if context["status"] == "error":
        _alert(ctx, CL.ALERT_STEP_ERROR, "warn", CL.COMPONENT, detail=context.get("error") or "")
    calendar = {"status": "skipped", "reason": "no signed calendar set (owner: sign core/calendars/data)"}
    if s.cal is not None:
        e = CL.run_context_step("event_calendar", EV.build_event_calendar, s.events, provenance=prov, calendar_version=s.cal.version,
                                cal=s.cal, cfg=s.rules.get("events"), gap_sessions_for=[effective], run_log=s.run_log, decision_utc=dec)
        if e.ok:
            out = _write(ctx, "event_calendar", e.value)
            calendar = {"status": out.status, "path": str(out.path)}
        else:
            calendar = {"status": "error", "error": e.error}
            _alert(ctx, CL.ALERT_STEP_ERROR, "warn", "core/calendars/events", detail=e.error or "")
    return {"status": "ok", "written": [{"kind": o.kind, "status": o.status, "path": str(o.path)} for o, _ in st["written"]],
            "context_log": context, "event_calendar": calendar, "fail_closed": bool(state.get("fail_closed"))}


# --------------------------------------------------------------------------- #
# (6) gate bounds_ok (R-32; L1222-1227; I-06c M8 clause)
# --------------------------------------------------------------------------- #
def bounds_ok(ctx) -> dict:
    s: Services = ctx.services
    reg, dec = s.book_registry, ctx.decision_utc
    rec, spec = _served(ctx)
    halted, issues = [], []

    def halt_described(reason: str) -> None:
        for b in _registered(reg, (rec, spec)):
            B.runtime_halt(reg, b, "OPS", "acting_field_schema_or_bounds_failure", dec, component="bounds_ok")
            halted.append(b)
        _alert(ctx, MA.ALERT_ACTING, "page", "bounds_ok", books=(rec, spec), detail=reason)

    for out, obj in ctx.state.get("written", []):
        if out.kind in ("macro_state", "overlay_decision"):
            if out.status == "quarantined" and out.acting_failure:
                issues.append({"kind": out.kind, "class": "acting", "issues": list(out.issues)})
                halt_described(f"{out.kind}: " + "; ".join(out.issues)[:300])
            elif out.status != "written":
                issues.append({"kind": out.kind, "class": "display", "issues": list(out.issues)})
                _alert(ctx, MA.ALERT_DISPLAY, "warn", "bounds_ok", detail="; ".join(out.issues)[:300])
        elif out.status == "quarantined":
            issues.append({"kind": out.kind, "class": "refused", "issues": list(out.issues)})
            _alert(ctx, out.alert["code"] if out.alert else "ARTIFACT_REFUSED", "warn", "bounds_ok", detail="; ".join(out.issues)[:300])
    # min() recomputed from the recorded factors of the artifacts AS WRITTEN (L881): a product-composed path trips here
    on_disk = {}
    for out, _obj in ctx.state.get("written", []):
        if out.status != "quarantined" and out.path and Path(out.path).exists():
            on_disk.setdefault(out.kind, []).append(json.loads(Path(out.path).read_text(encoding="utf-8")))
    state = (on_disk.get("macro_state") or [{}])[0]
    bad = []
    for bid, f in (ctx.state.get("factors") or {}).items():
        line = ((state.get("concentration") or {}).get("by_book") or {}).get(bid)
        if line is None or f.get("halted"):
            continue
        try:
            RL.verify_composition(f["vt"], list(f["overlays"].values()), f["ladder"], f["post_rearm_cap"], line.get("composed"))
        except RL.CompositionError as exc:
            bad.append(f"{bid}: {exc}")
    for o in on_disk.get("overlay_decision") or []:
        vals = [x["value"] for x in o.get("multipliers", [])]
        want = min([1.0] + vals + [o.get("ladder") if o.get("ladder") is not None else 1.0, o.get("post_rearm_cap") if o.get("post_rearm_cap") is not None else 1.0])
        if abs(float(o.get("overlay_min", -1.0)) - want) > 1e-12:
            bad.append(f"{o.get('family')}: overlay_min {o.get('overlay_min')} != min() {want}")
    if bad:
        for out, obj in ctx.state.get("written", []):
            if out.kind in ("macro_state", "overlay_decision") and out.status != "quarantined" and out.path and Path(out.path).exists():
                MA.quarantine(s.macro_dir, out.kind, obj, bad, ctx.clock, cls="acting")
                Path(out.path).unlink()
        issues.append({"kind": "composition", "class": "acting", "issues": bad})
        halt_described("composition recomputed from the recorded factors differs: " + "; ".join(bad)[:300])
    return {"status": "fail" if any(i["class"] == "acting" for i in issues) else "pass", "issues": issues, "halted": sorted(set(halted))}


# --------------------------------------------------------------------------- #
# (7) gate verdict_filter (R-35; re-verifies the run-start admissions on the built artifacts; F-1)
# --------------------------------------------------------------------------- #
def verdict_filter(ctx) -> dict:
    s: Services = ctx.services
    rec, spec = _served(ctx)
    first: AdmissionResult = ctx.state["admissions"]
    adm = compute_admissions(s, ctx)
    problems = []
    if adm.admitted != first.admitted:
        problems.append("admissions changed between run start and the gate")
    rules = set(adm.admitted.get(rec, ()))
    state = ctx.state.get("macro_state_obj") or {}
    vol = state.get("vol") or {}
    if vol.get("vt_weight_recommended_book") not in (None, 1.0) and not any(r.startswith("R-06") for r in rules):
        problems.append(f"vt_weight_recommended_book {vol.get('vt_weight_recommended_book')} without an admitted R-06 card")
    for o in ctx.state.get("overlay_objs") or []:
        if o.get("vol_scale_recommended_book") != 1.0 and (o.get("vol_scale_card") or {}).get("verdict") != "PASS":
            problems.append(f"{o['family']}: vol_scale_recommended_book departs from 1.0 on a {o['vol_scale_card'].get('verdict')} card")
        if o.get("overlay_applied_recommended_book") != 1.0 and not rules:
            problems.append(f"{o['family']}: overlay_applied_recommended_book {o['overlay_applied_recommended_book']} without an admission")
        for x in list(o.get("forward_sim") or []) + list(o.get("refusal") or []):
            if (x.get("card") or {}).get("displayed_as") in ("recommendation", "insurance"):
                problems.append(f"{x.get('rule_id')}: a FORWARD-SIM / refusal entry displayed as a recommendation")
    for rule in adm.integrity_failures:
        G.append_event(s.governance_log, {"kind": "verdict_integrity", "book_id": rec, "rule_id": rule, "key": "verdict_filter",
                                          "old": "PASS", "new": "specification_book", "actor": "runtime", "refs": ["R-35"],
                                          "reason": adm.refused.get(rule, "")[:400], "utc": G.iso_utc(ctx.decision_utc)})
        _alert(ctx, "VERDICT_INTEGRITY", "page", "verdict_filter", books=(rec,), detail=adm.refused.get(rule, ""))
    if not adm.chain_ok:
        _alert(ctx, "VERDICT_INTEGRITY", "page", "verdict_filter", books=(rec,), detail="cards/verdicts.jsonl chain broken: every admission blocked")
    if problems:
        ctx.feed_blocked[rec] = "; ".join(problems)
        _alert(ctx, "VERDICT_INTEGRITY", "page", "verdict_filter", books=(rec,), detail="; ".join(problems))
    # bindings follow admission (R-19 rule 5): each derived-binding change is a governance event in the same run
    baseline = ((ctx.state.get("previous") or {}).get("extras") or {}).get("derived_bindings")
    if baseline is None:
        baseline = {k: list(v) for k, v in C.derive_bindings(s.registry, {}).items()}
    derived = {k: list(v) for k, v in ctx.state["derived_bindings"].items()}
    changes = [k for k in sorted(set(baseline) | set(derived)) if baseline.get(k) != derived.get(k)]
    for key in changes:
        G.append_event(s.governance_log, {"kind": "binding_change", "book_id": rec, "rule_id": None, "key": key,
                                          "old": baseline.get(key), "new": derived.get(key), "actor": "runtime", "refs": ["R-19 rule 5"],
                                          "reason": "derived binding follows admission (data_contracts.roles untouched)",
                                          "utc": G.iso_utc(ctx.decision_utc)})
    ok = not problems and adm.chain_ok and not adm.integrity_failures
    return {"status": "pass" if ok else "fail", "admitted": adm.admitted, "refused": adm.refused, "integrity_failures": list(adm.integrity_failures),
            "chain_ok": adm.chain_ok, "binding_changes": changes, "problems": problems}


# --------------------------------------------------------------------------- #
# (8) macro.engine_feed: recommended and specification books only, atomic per book, idempotent per decision
# --------------------------------------------------------------------------- #
def engine_feed(ctx) -> dict:
    s: Services = ctx.services
    reg, dec = s.book_registry, ctx.decision_utc
    out = {}
    for bid, target in (ctx.state.get("targets") or {}).items():
        kind, _ = B.parse_book_id(bid)
        if kind not in ("recommended", "specification"):
            raise ValueError(f"{bid}: engine_feed takes recommended and specification books only (never a FORWARD-SIM or refusal book, P7)")
        if bid in ctx.feed_blocked:
            out[bid] = {"delivered": False, "reason": ctx.feed_blocked[bid]}
            continue
        book = reg.get(bid)
        if book.mode is EngineMode.DISARMED:
            out[bid] = {"delivered": False, "reason": "DISARMED: receives nothing (L1180)"}
            continue
        if target is None:
            out[bid] = {"delivered": False, "reason": "no target: the composition failed closed; weights carried"}
            continue
        rows = B.ledger(reg, bid)
        if rows and rows[-1].get("session") == ctx.session_date.isoformat():
            out[bid] = {"delivered": True, "idempotent": True}
            continue
        payload = {"book_id": bid, "run_id": ctx.run_id, "decision_utc": PL.iso(dec), "session_date": ctx.session_date.isoformat(),
                   "effective_session": PL.next_session(s.clocks, ctx.market, ctx.session_date).isoformat(),
                   "weights": {i: (0.0 if book.halted else float(w)) for i, w in target.items()}, "blocked": []}
        try:
            d = B.record_decision(reg, bid, dec, target, block=ctx.state["risk"][bid]["block"])   # the M5 book API: all or none
            payload["blocked"] = list(d.blocked)
            _atomic_write(Path(s.macro_dir) / "engine_feed" / quote(bid, safe="") / f"{ctx.session_date.isoformat()}.json", MS.canonical_json(payload))
            out[bid] = {"delivered": True, "post_action": d.post_action, "blocked": list(d.blocked), "carried": d.carried}
        except Exception as exc:                               # noqa: BLE001  (the book stays on its previous weights)
            out[bid] = {"delivered": False, "error": f"{type(exc).__name__}: {exc}"}
            _alert(ctx, "ENGINE_FEED_FAILED", "page", "macro.engine_feed", books=(bid,), detail=out[bid]["error"])
    return {"status": "ok", "books": out}


# --------------------------------------------------------------------------- #
# (9)-(11) forward books, forward monitor, brief (sibling hooks; display only)
# --------------------------------------------------------------------------- #
def forward_books(ctx) -> dict:
    s: Services = ctx.services
    if s.forward_books is None:
        return {"status": "skipped", "reason": "integration: core/quant/forward.py (TASK-M8-08..10) and core/quant/refusal.py "
                                               "(TASK-M8-12/13) supply the FORWARD-SIM and refusal evaluators; display only"}
    out = s.forward_books(ctx)
    for bid in (out or {}).get("books", {}):
        if B.parse_book_id(bid)[0] in ("recommended", "specification"):
            raise BookSeparationError(f"{bid}: the forward evaluator never writes a recommended or specification book")
    return {"status": "ok", **(out or {})}


def _queue_path(s: Services) -> Path:
    return Path(s.macro_dir) / MONITOR_QUEUE


def read_monitor_queue(macro_dir) -> list[dict]:
    p = Path(macro_dir) / MONITOR_QUEUE
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_bytes().decode("utf-8").split("\n") if line.strip()]


def forward_monitor(ctx) -> dict:
    """R-25 monitor hook; an exception queues the decision and every queued decision is re-run at the next
    successful run (L1244-1245, T-OBS-04)."""
    s: Services = ctx.services
    this = {"market": ctx.market, "session_date": ctx.session_date.isoformat(), "decision_utc": PL.iso(ctx.decision_utc)}
    pending = [q for q in read_monitor_queue(s.macro_dir) if q != this] + [this]
    if s.forward_monitor is None:
        _atomic_write(_queue_path(s), "".join(MS.canonical_json(q) + "\n" for q in pending[:-1]))
        return {"status": "skipped", "queued": len(pending) - 1, "reason": "integration: core/quant/forward.py forward_monitor (TASK-M8-08)"}
    done = []
    try:
        for q in pending:
            s.forward_monitor(ctx, q)
            done.append(q)
    finally:
        left = [q for q in pending if q not in done]
        _atomic_write(_queue_path(s), "".join(MS.canonical_json(q) + "\n" for q in left))
    return {"status": "ok", "monitored": done}


# --------------------------------------------------------------------------- #
# The production hooks (wired by `default_services`; TASK-M8-08..10, M8-12/13): display, forward books, R-25 monitor
# --------------------------------------------------------------------------- #
FORWARD_DIR = "forward"                                       # <macro_dir>/forward/<card_id>.jsonl (R-25 records)


def _forward_display(ctx, market: str) -> dict:
    """R-28 / R-29 on the US decision and R-11 (KR) / R-12 (US) for the artifacts' display fields and their own
    books only; called inside `run_context_step` (an exception never HALTs) and never composed into a weight book."""
    from core.quant import forward_sim as FS
    from core.quant import refusal as RF
    s: Services = ctx.services
    fs = FS.display_books(s.store, ctx.decision_utc, ctx.knowledge_utc, market=market, registry=s.registry,
                          run_mode=ctx.run_mode, previous=(ctx.state.get("previous") or {}).get("forward_sim"))
    rf = RF.display_legs(s.store, ctx.decision_utc, ctx.knowledge_utc, market=market, registry=s.registry, run_mode=ctx.run_mode)
    return {**fs, **rf, "books": {**fs["books"], **rf["books"]}}


def _forward_books(ctx) -> dict:
    """Each FORWARD-SIM / refusal book's value from the display legs (display only, never `engine_feed`). A forward
    record starts at the first live decision after a header commit (R-25); decision rows need the card's forward
    on / off / S books, so nothing is appended while no header is committed."""
    started = sorted(p.stem for p in (Path(ctx.services.macro_dir) / FORWARD_DIR).glob("*.jsonl"))
    return {"books": dict((ctx.state.get("forward_display") or {}).get("books") or {}),
            "records": started or "not started: no committed header (R-25 starts at the first live decision after the commit)"}


def _forward_monitor(ctx, q: Mapping) -> None:
    """R-25 on every started, undemoted record of the queued decision's market: a demotion writes the governance event,
    the record's demotion row and the 6-month family x market lockout, and pages. Live runs only (replays and
    backtests are audits, section 8.8 (a))."""
    from core.quant import forward as FWD
    s: Services = ctx.services
    if ctx.run_mode != "live":
        return
    as_of = date.fromisoformat(q["session_date"])
    for path in sorted((Path(s.macro_dir) / FORWARD_DIR).glob("*.jsonl")):
        rec = FWD.ForwardRecord(path)
        meta = rec.meta
        if meta is None or rec.demoted is not None or meta.get("market") not in (None, q["market"]):
            continue
        th = FWD.AlarmThresholds(**{**meta["thresholds"], "tightened": tuple(meta["thresholds"].get("tightened") or ())})
        n12 = sum(bool(s.clocks.is_session(q["market"], as_of - timedelta(days=i))) for i in range(365))
        res = FWD.forward_monitor(rec, th, as_of=as_of, scheduled_12m=n12)
        if res.demotion is None:
            continue
        card = {"market": meta.get("market"), "family_id": meta.get("family"), "card_id": meta["card_id"], "verdict": "NOT_RUN",
                **(load_cards(s.cards_root).get(meta["card_id"]) or {})}
        d = FWD.demote(card, rec, res.demotion, governance_log=s.governance_log, decision_utc=P.parse_utc(q["decision_utc"]))
        s.alerts.raise_alert("FORWARD_DEMOTION", "page", "core/quant/forward", when=P.parse_utc(q["decision_utc"]),
                             books=(f"recommended:{q['market']}",),
                             detail=f"{d.card_id}: {d.old} -> {d.new} ({d.kind}: {d.reason}); lockout until {P.iso_utc(d.lockout_until)}")


def _locked_out(governance_log: Path, family: str, market: str, utc: datetime) -> bool:
    from core.quant.forward import locked_out
    return locked_out(governance_log, family, market, utc)


def brief(ctx) -> dict:
    s: Services = ctx.services
    od = s.rules.get("owner_decisions")
    pending = [d for d, e in od.items() if isinstance(e, Mapping) and e.get("status") == "pending"]
    actions = [k for k in ("sleeves.KR.notional_nav", "sleeves.US.notional_nav") if s.rules.get(k) is None]
    if MA.GIT_HASH == "UNVERSIONED":
        actions.append("repository under git (the freeze and verdict_filter check (iii) refuse UNVERSIONED)")
    return {"status": "ok", "owner_decisions_pending": pending, "owner_actions": actions,
            "alerts_open": len(s.alerts.open()), "books": {b: s.book_registry.get(b).mode.value for b in _registered(s.book_registry, _served(ctx))},
            "claude": "not called: the brief carries computed numbers only; no key is read and no text is parsed by an acting module"}


# --------------------------------------------------------------------------- #
# (12) macro.run_record: the runner's epilogue (counters once per book, ARM, HALT pages, run-row fields)
# --------------------------------------------------------------------------- #
def run_record(ctx) -> dict:
    s: Services = ctx.services
    reg, dec = s.book_registry, ctx.decision_utc
    out = {}
    for bid in _registered(reg, _served(ctx)):
        failed = ctx.state.get("failed_by_book", {}).get(bid, {})
        ok = not ctx.acting_error and not failed
        book = reg.get(bid)
        if ctx.run_mode == "replay":
            out[bid] = _book_dict(book)                        # an audit: counters, ARM and HALT pages belong to the live run
            continue
        if s.arm and ctx.run_mode == "live" and ok and book.mode is EngineMode.DISARMED and not book.ever_armed \
                and CS.arm_precondition(ctx.session_date, ctx.market, cal=s.cal):
            B.arm(reg, bid, dec)
        res = B.step_decision(reg, bid, dec, ok, failed=tuple(failed), limits=dict(failed))
        out[bid] = _book_dict(res.book)
    halts = []
    for bid, before in (ctx.state.get("modes_before") or {}).items() if ctx.run_mode != "replay" else ():
        book = reg.get(bid)
        if book.halted and before != "HALTED" and book.halt:
            halts.append({"book_id": bid, "class": book.halt["class"], "reason_code": book.halt["reason_code"]})
            _alert(ctx, f"HALT_{book.halt['class']}", "page", "core/engine/books", books=(bid,), detail=book.halt["reason_code"])
    adm: AdmissionResult | None = ctx.state.get("admissions")
    return {"books": out, "books_before": ctx.state.get("books_before", {}), "halts": halts,
            "fail_closed_inputs": ctx.state.get("fail_closed", []), "forward_failed": ctx.state.get("forward_failed", {}),
            "admitted": adm.admitted if adm else {}}


STEPS = {"macro.pit_snapshot": pit_snapshot, "macro.lag_audit": lag_audit, "macro.vol_and_overlays": vol_and_overlays,
         "macro.build_artifacts": build_artifacts, "macro.engine_feed": engine_feed, "macro.forward_books": forward_books,
         "macro.forward_monitor": forward_monitor, "macro.brief": brief, "macro.run_record": run_record}
GATES = {"data_ok": data_ok, "bounds_ok": bounds_ok, "verdict_filter": verdict_filter}


def load_macro_pipeline(path=YAML_PATH) -> PL.Pipeline:
    return PL.load_pipeline(path, known_steps=STEPS, known_gates=GATES)


def run_decision(s: Services, market: str, session_date: date, *, run_mode: str | None = None,
                 knowledge_utc: datetime | None = None, pipeline: PL.Pipeline | None = None) -> dict:
    """One decision of one market through the pipeline; returns the run record (appended to run_log.jsonl)."""
    if market not in MARKETS:
        raise ValueError(f"market {market!r}: the v2.0 daily markets are {MARKETS}")
    if s.session_anchor:
        s.session_anchor[0] = session_date
    B.create_default_books(s.book_registry, [market])
    if (run_mode or s.run_mode) == "live" and PL.has_live_row(s.run_log, market, session_date):
        return replay(s, market, session_date)["run"]          # L1199: a later run of the decision is an audit on scratch state
    return PL.run_pipeline(pipeline or load_macro_pipeline(), market=market, session_date=session_date, clock=s.clock,
                           clocks=s.clocks, steps=STEPS, gates=GATES, run_log=s.run_log, services=s,
                           run_mode=run_mode or s.run_mode, knowledge_utc=knowledge_utc, alerts=s.alerts, on_start=on_start)


# --------------------------------------------------------------------------- #
# Missed decisions and the app-start hook (L1246-1250; T-OBS-02, T-OBS-05; rulings 3.13)
# --------------------------------------------------------------------------- #
def expected_decisions(clocks, market: str, since: date, until: date) -> list[tuple[str, date, datetime]]:
    """Every session of `market` strictly after `since` up to `until` inclusive, with its decision instant."""
    out, d = [], since
    while d < until:
        d += timedelta(days=1)
        if clocks.is_session(market, d):
            out.append((market, d, clocks.close_print_bound_utc(market, d)))
    return out


def check_missed(macro_dir, clocks, now: datetime, markets: Iterable[str] = MARKETS) -> list[dict]:
    """Expected decisions start after the first live run row of a market (F-15); the last expected one is the last
    session whose start bound (close + 10 min) has passed."""
    rows = PL.read_run_log(Path(macro_dir) / PL.RUN_LOG)
    out = []
    for m in markets:
        mine = sorted(r["session_date"] for r in rows if r.get("market") == m and r.get("run_mode", "live") == "live")
        if not mine:
            continue
        since = date.fromisoformat(mine[0])
        until = now.date()
        while until > since and not (clocks.is_session(m, until) and PL.earliest_start_utc(clocks, m, until) <= now):
            until -= timedelta(days=1)
        out += PL.missed_decisions(expected_decisions(clocks, m, since, until), rows)
    return out


def app_start(macro_dir, clock: Callable[[], datetime], *, clocks=None, markets: Iterable[str] = MARKETS) -> dict:
    """Governance-chain check (T-OBS-05) and the missed-decision page (T-OBS-02); never raises."""
    macro_dir = Path(macro_dir)
    alerts = AlertStore(macro_dir)
    now = clock()
    out = {"governance_chain_ok": True, "missed": [], "note": None}
    try:
        check = G.verify_chain(macro_dir / GOVERNANCE_LOG)
        if not check.ok:
            out["governance_chain_ok"] = False
            alerts.raise_alert("GOVERNANCE_LOG_BROKEN", "page", "core/rules/governance", when=now,
                               detail=f"{GOVERNANCE_LOG} chain broken at line {check.first_bad_line}: no admission or derived-binding change until restored")
    except Exception as exc:                                   # noqa: BLE001
        out["governance_chain_ok"] = False
        alerts.raise_alert("GOVERNANCE_LOG_BROKEN", "page", "core/rules/governance", when=now, detail=f"{type(exc).__name__}: {exc}")
    try:
        if clocks is None:
            from core.calendars.adapter import CalendarClocks
            clocks = CalendarClocks()
        missed = check_missed(macro_dir, clocks, now, markets)
        for d in missed:
            alerts.raise_alert("MISSED_DECISION", "page", f"macro_daily:{d['market']}:{d['session_date']}", when=P.parse_utc(d["decision_utc"]),
                               books=(f"recommended:{d['market']}", f"specification:{d['market']}"),
                               detail=f"{d['reason']}: the books carry their weights (section 8.8)")
        out["missed"] = missed
    except Exception as exc:                                   # noqa: BLE001  (an unsigned calendar: the check cannot run)
        out["note"] = f"missed-decision check not run: {type(exc).__name__}: {exc}"
        alerts.raise_alert("MISSED_DECISION_CHECK_UNAVAILABLE", "warn", "macro_daily", when=now, detail=out["note"])
    return out


def _app_start_safe(macro_dir, clock, clocks) -> dict:
    try:
        if macro_dir is None:
            import config
            macro_dir = config.macro_dir()
        return app_start(macro_dir, clock, clocks=clocks)
    except Exception as exc:                                   # noqa: BLE001  (the app entry never raises)
        return {"error": f"{type(exc).__name__}: {exc}"}


def on_app_start(macro_dir=None, clock: Callable[[], datetime] | None = None, *, clocks=None, background: bool = False,
                 force: bool = False) -> dict | None:
    """Once per process (module flag; `main.py` calls it inside try/except) and never raises (an error is returned
    as `{"error": ...}`). `background=True` runs it on a daemon thread so the first paint is never blocked. The clock
    defaults to the wall clock only here (the app entry)."""
    if _STARTED["done"] and not force:
        return None
    _STARTED["done"] = True
    clock = clock or (lambda: datetime.now(UTC))
    if background:
        threading.Thread(target=_app_start_safe, args=(macro_dir, clock, clocks), daemon=True, name="macro-app-start").start()
        return None
    return _app_start_safe(macro_dir, clock, clocks)


# --------------------------------------------------------------------------- #
# Replay (R-01 rule 7; T-REPLAY-01; section 8.8 (a): audits only)
# --------------------------------------------------------------------------- #
def _restore(reg: B.BookRegistry, s: Services, market: str, session_date: date) -> None:
    """Runtime state from before the decision: the live run row's `books_before` (the state at that run's start),
    else the previous live row's `books` (post-epilogue state); the ledger truncated to the sessions before it."""
    rows = [r for r in PL.read_run_log(s.run_log) if r.get("market") == market and r.get("run_mode", "live") == "live"]
    same = [r for r in rows if r.get("session_date") == session_date.isoformat() and r.get("books_before")]
    before = [r for r in rows if r.get("session_date", "") < session_date.isoformat() and r.get("books")]
    books = same[-1]["books_before"] if same else before[-1]["books"] if before else {}
    for bid, d in books.items():
        if bid in reg.ids():
            reg.save(_book_from(d))
    for bid in reg.ids():
        p = reg.books_dir / (quote(bid, safe="") + ".ledger.jsonl")
        if p.is_file():
            keep = [line for line in p.read_bytes().decode("utf-8").split("\n") if line.strip()
                    and json.loads(line).get("session", "") < session_date.isoformat()]
            p.write_bytes(("\n".join(keep) + ("\n" if keep else "")).encode("utf-8"))


def replay(s: Services, market: str, session_date: date, *, artifact: Mapping | None = None) -> dict:
    """Re-run a past decision at the artifact's `knowledge_utc` against a scratch copy of the runtime (never the
    live books, never `engine_feed`, never a forward record) and compare every artifact byte for byte after
    canonicalisation (generated_at_utc, git_hash and tree_hash excluded)."""
    root = Path(s.macro_dir)
    rel = MA.default_relpath("macro_state", {"market": market, "decided_session": session_date.isoformat()})
    orig = dict(artifact) if artifact is not None else json.loads((root / rel).read_text(encoding="utf-8"))
    knw = P.parse_utc(orig["knowledge_utc"])
    tmp = root / "replay" / f"{market}-{session_date.isoformat()}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    if s.book_registry.books_dir.is_dir():
        shutil.copytree(s.book_registry.books_dir, tmp / "books")
    reg = B.BookRegistry(tmp, clock=s.clock, sessions=s.book_registry.sessions)
    _restore(reg, s, market, session_date)
    scratch = replace(s, macro_dir=tmp, book_registry=reg, alerts=AlertStore(tmp), run_mode="replay", arm=False, state_root=root)
    record = run_decision(scratch, market, session_date, run_mode="replay", knowledge_utc=knw)
    for a in scratch.alerts.open("page"):
        if a["code"] == "VERDICT_INTEGRITY":
            s.alerts.raise_alert(a["code"], "page", "replay:" + a["component"], when=P.parse_utc(a["first_seen_utc"]),
                                 books=a["books"], detail=a.get("detail", ""))
    diffs: dict[str, list[str]] = {}
    new = json.loads((tmp / rel).read_text(encoding="utf-8")) if (tmp / rel).exists() else {}
    d = PL.compare_artifacts(orig, new, ignore=REPLAY_IGNORE)
    if d:
        diffs["macro_state"] = d
    for o in sorted((root / "overlay_decision" / market).glob(f"*/*.json")) if (root / "overlay_decision" / market).is_dir() else []:
        eff, fam = o.parent.name, o.stem
        mine = json.loads(o.read_text(encoding="utf-8"))
        if mine.get("decision_utc") != orig.get("decision_utc"):
            continue
        twin = tmp / "overlay_decision" / market / eff / f"{fam}.json"
        d = PL.compare_artifacts(mine, json.loads(twin.read_text(encoding="utf-8")) if twin.exists() else {}, ignore=REPLAY_IGNORE)
        if d:
            diffs[f"overlay_decision/{fam}"] = d
    return {"match": not diffs, "diffs": diffs, "run": record, "artifact": new, "scratch_dir": str(tmp)}


# --------------------------------------------------------------------------- #
# Dry run on the local vendor cache (rulings 1; labelled; books DISARMED; offline)
# --------------------------------------------------------------------------- #
class DryRunClocks:
    """Labelled dry-run calendar for the vendor cache: weekday sessions minus the legacy generated holiday files
    (`data/calendars/{KRX,US}.json`, 2026-27; weekday fallback outside their coverage), fixed close bounds (KRX
    06:30:30Z from 2016-08-01 and 06:00:30Z before, NYSE 16:00 ET + 30 s) and rule-based publication instants.
    Never used by a live run: production clocks are the signed set through `core.calendars.adapter.CalendarClocks`."""
    VENUE = {"KR": "KRX", "US": "US"}
    NY, KST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
    label = "dry_run_weekday_stub (calendars unsigned)"

    def __init__(self, registry=None) -> None:
        self.registry = registry or C.default_registry()

    def is_session(self, market: str, d: date) -> bool:
        if d.weekday() >= 5:
            return False
        t = _legacy_cal.is_trading_day(self.VENUE.get(market, market), d)
        return True if t is None else bool(t)

    def _next(self, d: date, ok) -> date:
        d += timedelta(days=1)
        while not ok(d):
            d += timedelta(days=1)
        return d

    def _weekday(self, d: date) -> bool:
        return d.weekday() < 5

    def _ny(self, d: date, hh: int, mm: int) -> datetime:
        return datetime(d.year, d.month, d.day, hh, mm, tzinfo=self.NY).astimezone(UTC)

    def close_print_bound_utc(self, market: str, d: date) -> datetime:
        if not self.is_session(market, d):
            raise CS.NotASession(f"{market} {d.isoformat()} is not a session (dry-run calendar)")
        if market == "KR":
            return datetime(d.year, d.month, d.day, 6, 30, 30, tzinfo=UTC) if d >= date(2016, 8, 1) else datetime(d.year, d.month, d.day, 6, 0, 30, tzinfo=UTC)
        if market == "US":
            return self._ny(d, 16, 0) + timedelta(seconds=30)
        return datetime(d.year, d.month, d.day, 6, 0, tzinfo=UTC)

    def decision_time_utc(self, market: str, d: date) -> datetime:
        return self.close_print_bound_utc(market, d) - timedelta(seconds=30)

    def publication_instant(self, sid: str, d: date) -> datetime | None:
        s = self.registry.schedule(sid)
        if s == "KRX_CLOSE":
            return self.close_print_bound_utc("KR", d)
        if s == "NYSE_CLOSE":
            return self.close_print_bound_utc("US", d)
        if s == "FRED_H15":
            return self._ny(self._next(d, self._weekday), 16, 15)
        if s == "H10":
            monday = d + timedelta(days=7 - d.weekday())
            return self._ny(monday, 16, 15)
        if s == "TREASURY_PAR":
            return self._ny(d, 18, 0)
        if s == "VIXCLS":
            return self._ny(d, 16, 15)
        if s in ("BLS", "BEA"):
            return self._ny(d, 8, 30)
        if s == "ECOS_1530":
            return datetime(d.year, d.month, d.day, 15, 30, tzinfo=self.KST).astimezone(UTC)
        if s == "KODEX_PDF":
            n = self._next(d, lambda x: self.is_session("KR", x))
            return datetime(n.year, n.month, n.day, 8, 0, tzinfo=self.KST).astimezone(UTC)
        return None

    def next_expected_obs(self, sid: str, d: date) -> date | None:
        s = self.registry.schedule(sid)
        if s in ("FRED_H15", "H10"):
            return self._next(d, self._weekday)
        if s in ("KRX_CLOSE", "KODEX_PDF"):
            return self._next(d, lambda x: self.is_session("KR", x))
        if s in ("NYSE_CLOSE", "VIXCLS", "TREASURY_PAR"):
            return self._next(d, lambda x: self.is_session("US", x))
        if s in ("BLS", "BEA"):
            return P.add_months(d, 1)
        return None

    def add_publication_bdays(self, sid: str, instant: datetime | None, n: int) -> datetime | None:
        if instant is None:
            return None
        s = self.registry.schedule(sid)
        kr = s in ("KRX_CLOSE", "KODEX_PDF", "ECOS_1530")
        local = instant.astimezone(self.KST if kr else self.NY)
        d = local.date()
        ok = (lambda x: self.is_session("KR", x)) if kr else (lambda x: self.is_session("US", x)) if s in ("NYSE_CLOSE", "VIXCLS", "TREASURY_PAR") else self._weekday
        for _ in range(int(n)):
            d = self._next(d, ok)
        if s in ("KRX_CLOSE", "NYSE_CLOSE"):
            return self.close_print_bound_utc("KR" if s == "KRX_CLOSE" else "US", d)
        return local.replace(year=d.year, month=d.month, day=d.day).astimezone(UTC)

    def usable_at(self, sid: str, d: date, market: str) -> datetime | None:
        return self.publication_instant(sid, d)


def read_cache_csv(path: Path) -> list[tuple[date, float]]:
    """`Date,<symbol>` rows of the vendor cache; blank values skipped."""
    out = []
    with Path(path).open(encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if not row or row[0].lower() == "date":
                continue
            try:
                out.append((date.fromisoformat(row[0][:10]), float(row[1])))
            except (ValueError, IndexError):
                continue
    return out


def dry_run(macro_dir, *, clock: Callable[[], datetime], cache_dir: Path = CACHE_DIR, clocks=None,
            markets: Iterable[str] = MARKETS, rows_per_series: int = 900) -> dict:
    """The demonstrable end-to-end path on local vendor data: labelled, offline, never acting, never a verdict."""
    root = Path(macro_dir) / "dry_run"
    registry = C.default_registry()
    clocks = clocks or DryRunClocks(registry)
    if (root / "pit").is_dir():
        shutil.rmtree(root / "pit")                            # scratch rebuilt from the cache each run (rows of an older stamping never linger)
    store = P.PITStore(root / "pit", registry=registry, clocks=clocks)
    now = clock()
    ingested, last = {}, {}
    for sid, (name, source) in DRY_RUN_CACHE.items():
        path = Path(cache_dir) / name
        if not path.is_file():
            ingested[sid] = {"file": name, "status": "absent"}
            continue
        rows = read_cache_csv(path)[-rows_per_series:]
        fetched = datetime.fromtimestamp(path.stat().st_mtime, UTC)   # the file's real retrieval instant (L1283): a running bar stays provisional
        rep = P.ingest(store, sid, rows, source=source, retrieved_at_utc=fetched, registry=registry, clocks=clocks,
                       provider_mode="explicit", channel=f"dry_run:{name}")
        ingested[sid] = {"file": name, "appended": rep.appended, "logged": rep.logged, "flagged": len(rep.flags)}
        closes = [r["obs_date"] for r in store.rows(sid) if r["value_status"] in P.CLOSE_STATUSES]
        if closes:
            last[sid] = max(closes)                            # the decided session is the last stamped close, never a quote
    s = default_services(root, clock, store=store, registry=registry, clocks=clocks, run_mode="backtest", vendor="Yahoo",
                         extras={"dry_run": dict(DRY_RUN_MARKER, calendar=getattr(clocks, "label", type(clocks).__name__))},
                         arm=False)
    out = {"root": str(root), "ingested": ingested, "runs": {}}
    for m in markets:
        sid = NAV_SERIES.get(m) or RL.VT_SERIES.get(m)
        session = last.get(sid)
        if session is None:
            out["runs"][m] = {"status": "skipped", "reason": f"no cached rows for {sid}"}
            continue
        while not clocks.is_session(m, session):
            session -= timedelta(days=1)
        out["runs"][m] = run_decision(s, m, session, run_mode="backtest", knowledge_utc=now)
    out["books"] = {b: s.book_registry.get(b).mode.value for b in s.book_registry.ids()}
    return out


# --------------------------------------------------------------------------- #
# CLI: python -m core.skills.macro_daily --market KR --mode dry_run|live --macro-dir <path>
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import config
    parser = argparse.ArgumentParser(description="macro_daily: one decision of one market, or the labelled dry run")
    parser.add_argument("--market", default=None, choices=MARKETS, help="dry_run: default every market; live: default KR")
    parser.add_argument("--mode", default="dry_run", choices=("dry_run", "live"))
    parser.add_argument("--macro-dir", default=None)
    parser.add_argument("--session", default=None, help="YYYY-MM-DD (live: default = the clock's UTC date)")
    args = parser.parse_args(argv)
    macro_dir = config.refuse_quantgen(args.macro_dir, "--macro-dir") if args.macro_dir else config.macro_dir()
    now = datetime.now(UTC)          # the CLI entry's one wall-clock read (rulings 3.11), pinned for the whole run;
    clock = lambda: now              # noqa: E731  ponytail: the CLI ingests nothing; a CLI that fetches must pin knowledge after its fetches
    try:
        if args.mode == "dry_run":
            out = dry_run(macro_dir, clock=clock, markets=(args.market,) if args.market else MARKETS)
            runs = {m: (r.get("status"), [s["name"] for s in r.get("steps", []) if s["status"] == "error"]) for m, r in out["runs"].items() if isinstance(r, dict) and "steps" in r}
            print(json.dumps({"root": out["root"], "ingested": out["ingested"], "runs": runs, "books": out["books"],
                              "marker": DRY_RUN_MARKER["chip"]}, indent=2))
            return 0
        s = default_services(macro_dir, clock)
        session = date.fromisoformat(args.session) if args.session else clock().date()
        rec = run_decision(s, args.market or "KR", session, run_mode="live")
        print(json.dumps({k: rec[k] for k in ("run_id", "market", "session_date", "status", "late", "acting_error")}, indent=2))
        return 0 if rec["status"] == "ok" else 1
    except (PL.TooEarly, CS.NotASession, CS.CalendarUnsigned, ValueError) as exc:
        print(f"refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
