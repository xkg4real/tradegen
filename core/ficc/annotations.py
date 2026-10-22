"""R-08 VIX >= VIX3M execution-state annotation (M5; TASK-M5-07; T-ANNOT-01, G-R08-01; spec L1592-1603).

`flag(D) = VIX(D) >= VIX3M(D)`: the threshold is parity and never tuned; the clearing rule is the raw parity
flag (no hysteresis). The annotation applies from the first decision after the 16:15 ET VIX close (the US close
of D+1, the KRX close of K >= D+1), which the registry's `VIXCLS` channel enforces inside `pit_value` (role
context, consumer R-08). **It changes no exposure**: no BLOCKED decision, no cut, no re-add; the book builder
asserts it (`assert_no_exposure_change`). The KIS spread-snapshot request is a record for the data layer
(read-only quotation endpoints, T-RO-02); while the KIS quote-field check is not run the record is written with
status `unverified_not_sent` and labelled UNVERIFIED (spec L44). The CARD-P REJECT (G-R08-02) stays on file as
a record only. Tech-fund XS-14: never count R-08 as factor-crash protection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from core.ficc import pit

RULE_ID = "R-08"
CONSUMER = "R-08"
VIX, VIX3M = "VIXCLS", "VXVCLS"
DEFAULT_LINES = ("069500",)                 # the KODEX 200 line of the default KR books
BUDGET_PER_YEAR = 14.0                      # annotations.vix_ts.switch_budget_per_year (store)
SWITCH_LOG_MULTIPLE = 2.0                   # "switches above 2x the budget of 14 a year are logged"
SWITCH_WINDOW = 252                         # trailing input dates (brief F-13)
REQUEST_STATUSES = ("queued", "unverified_not_sent")
ANNOTATION_STATUSES = ("ok", "stale", "missing")
KIS_VERIFIED_LABEL = "UNVERIFIED (KIS quote-field check not run; spec L44)"


@dataclass(frozen=True)
class SnapshotRequest:
    """A read-only KIS spread-snapshot request record (never an order; quotation endpoints only)."""
    lines: tuple[str, ...]
    requested_utc: str
    status: str                                     # queued | unverified_not_sent
    endpoint_kind: str = "kis_quotation_read_only"
    label: str = ""

    def __post_init__(self) -> None:
        if self.status not in REQUEST_STATUSES:
            raise ValueError(f"SnapshotRequest.status {self.status!r} not in {REQUEST_STATUSES}")


@dataclass(frozen=True)
class Annotation:
    rule_id: str
    vix_ge_vix3m: bool
    input_date: date | None
    vix: float | None = None
    vix3m: float | None = None
    status: str = "ok"                              # ok | stale | missing (context: labelled, never a failure)
    notes: tuple[str, ...] = ()
    kis_snapshot_request: SnapshotRequest | None = None
    transitions_trailing: int | None = None
    switch_log: bool = False                        # transitions in the trailing window > 2 x budget
    changes_exposure: bool = field(default=False, init=False)   # constant: an annotation never changes a weight

    def __post_init__(self) -> None:
        if self.status not in ANNOTATION_STATUSES:
            raise ValueError(f"Annotation.status {self.status!r} not in {ANNOTATION_STATUSES}")

    def macro_state_block(self) -> dict:
        """`macro_state.annotations` (schema: `vix_ge_vix3m` required, `notes[]`)."""
        return {"vix_ge_vix3m": bool(self.vix_ge_vix3m), "notes": list(self.notes)}


# --------------------------------------------------------------------------- #
# Pure arithmetic
# --------------------------------------------------------------------------- #
def parity_flag(vix: float, vix3m: float) -> bool:
    return float(vix) >= float(vix3m)


def parity_flags(vix_series, vix3m_series) -> list[tuple[date, bool]]:
    """Aligned on common dates (ascending). Each series is {date: value} or an iterable of (date, value)."""
    a = dict(vix_series.items() if hasattr(vix_series, "items") else vix_series)
    b = dict(vix3m_series.items() if hasattr(vix3m_series, "items") else vix3m_series)
    return [(d, parity_flag(a[d], b[d])) for d in sorted(set(a) & set(b))]


def spell_stats(flags) -> dict:
    """G-R08-01 anatomy: days, flagged share, spells (maximal runs of True), one-day and >= 5-day shares,
    transitions (off->on or on->off) per 252-day year."""
    bits = [bool(f[1] if isinstance(f, tuple) else f) for f in flags]
    n = len(bits)
    runs, run = [], 0
    for b in bits:
        if b:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    transitions = sum(1 for x, y in zip(bits, bits[1:]) if x != y)
    return {"n_days": n, "n_flagged": sum(bits), "share_flagged": (sum(bits) / n) if n else 0.0,
            "n_spells": len(runs), "share_one_day": (sum(1 for r in runs if r == 1) / len(runs)) if runs else 0.0,
            "share_ge5": (sum(1 for r in runs if r >= 5) / len(runs)) if runs else 0.0,
            "n_transitions": transitions, "transitions_per_year": (transitions / n * 252.0) if n else 0.0}


def transitions_trailing(flags, window: int = SWITCH_WINDOW) -> int:
    bits = [bool(f[1] if isinstance(f, tuple) else f) for f in flags][-window:]
    return sum(1 for x, y in zip(bits, bits[1:]) if x != y)


def kis_spread_snapshot_request(lines, requested_utc: datetime | str, *, kis_verified: bool = False) -> SnapshotRequest:
    """The request record. Without the KIS quote-field check it is `unverified_not_sent` and labelled UNVERIFIED."""
    stamp = requested_utc if isinstance(requested_utc, str) else pit.iso_utc(requested_utc)
    status = "queued" if kis_verified else "unverified_not_sent"
    return SnapshotRequest(tuple(lines), stamp, status, label="" if kis_verified else KIS_VERIFIED_LABEL)


def annotate(vix, vix3m, input_date, *, lines=DEFAULT_LINES, requested_utc=None, kis_verified: bool = False,
             history=None, status: str = "ok", budget_per_year: float = BUDGET_PER_YEAR) -> Annotation:
    """The pure annotation for one input date D. `history` = prior (date, flag) pairs for the switch log."""
    if vix is None or vix3m is None or input_date is None:
        return Annotation(RULE_ID, False, input_date, status="missing",
                          notes=("R-08: VIX / VIX3M input missing; annotation off, labelled (context role)",))
    on = parity_flag(vix, vix3m)
    notes = [f"R-08: VIX {float(vix):.2f} {'>=' if on else '<'} VIX3M {float(vix3m):.2f} on {input_date.isoformat()}"
             f" -> annotation {'on' if on else 'off'} (raw parity flag, never tuned; changes no weight)"]
    if status == "stale":
        notes.append("R-08: input stale, labelled (context input; never a failure)")
    request = None
    if on:
        stamp = requested_utc if requested_utc is not None else datetime.combine(input_date, datetime.min.time(),
                                                                                  tzinfo=timezone.utc)
        request = kis_spread_snapshot_request(lines, stamp, kis_verified=kis_verified)
        notes.append(f"R-08: KIS spread-snapshot request for {','.join(lines)}: {request.status}"
                     + (f" [{request.label}]" if request.label else ""))
    trailing, switch_log = None, False
    if history is not None:
        trailing = transitions_trailing(list(history) + [(input_date, on)])
        switch_log = trailing > SWITCH_LOG_MULTIPLE * budget_per_year
        if switch_log:
            notes.append(f"R-08: {trailing} switches in the trailing {SWITCH_WINDOW} input dates exceed "
                         f"{SWITCH_LOG_MULTIPLE:g} x the budget of {budget_per_year:g} a year: logged for review "
                         "(a logging rule only)")
    return Annotation(RULE_ID, on, input_date, float(vix), float(vix3m), status, tuple(notes), request,
                      trailing, switch_log)


def assert_no_exposure_change(weights_before, weights_after, *, tol: float = 0.0) -> None:
    """The book-builder assertion (spec L1601, L1634): an R-08 flag or an R-10 tag changes no weight."""
    a, b = dict(weights_before), dict(weights_after)
    if set(a) != set(b):
        raise AssertionError(f"annotation changed the held lines: {sorted(set(a) ^ set(b))}")
    moved = {k: (a[k], b[k]) for k in a if abs(float(a[k]) - float(b[k])) > tol}
    if moved:
        raise AssertionError(f"annotation changed exposure (R-08 / R-10 change no weight): {moved}")


# --------------------------------------------------------------------------- #
# PIT path (context role; a stale or missing input is labelled, never a failure)
# --------------------------------------------------------------------------- #
def vix_ge_vix3m(store: pit.PITStore, decision_utc: datetime, knowledge_utc: datetime, *, registry=None,
                 lines=DEFAULT_LINES, kis_verified: bool = False, consumer: str = CONSUMER,
                 history_n: int = SWITCH_WINDOW, run_mode: str = "live") -> Annotation:
    """Read VIXCLS and VXVCLS as-of the decision through `pit_value` (consumer R-08, role context; the production
    channel's usable-from rule is the registry's) and annotate the latest common input date D."""
    vix = pit.pit_value(store, VIX, decision_utc, knowledge_utc, consumer, registry=registry, run_mode=run_mode)
    vix3m = pit.pit_value(store, VIX3M, decision_utc, knowledge_utc, consumer, registry=registry, run_mode=run_mode)
    if isinstance(vix, pit.MissingInput) or isinstance(vix3m, pit.MissingInput):
        missing = [m.series_id for m in (vix, vix3m) if isinstance(m, pit.MissingInput)]
        return Annotation(RULE_ID, False, None, status="missing",
                          notes=(f"R-08: {','.join(missing)} not usable at {pit.iso_utc(decision_utc)}; annotation "
                                 "off, labelled (context role, never a failure)",))
    win_a = pit.pit_window(store, VIX, decision_utc, knowledge_utc, n=history_n + 1, registry=registry)
    win_b = pit.pit_window(store, VIX3M, decision_utc, knowledge_utc, n=history_n + 1, registry=registry)
    pairs = parity_flags({v.obs_date: v.value for v in win_a}, {v.obs_date: v.value for v in win_b})
    if not pairs:
        return Annotation(RULE_ID, False, None, status="missing",
                          notes=("R-08: no common VIX / VIX3M input date; annotation off, labelled",))
    d = pairs[-1][0]
    a = {v.obs_date: v.value for v in win_a}[d]
    b = {v.obs_date: v.value for v in win_b}[d]
    status = "stale" if d != max(vix.obs_date, vix3m.obs_date) else "ok"
    return annotate(a, b, d, lines=lines, requested_utc=decision_utc, kis_verified=kis_verified,
                    history=pairs[:-1], status=status)
