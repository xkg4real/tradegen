"""Offline metrics for normalized, receipt-timed DIDM upside-event research."""
from __future__ import annotations
from bisect import bisect_left
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
import re
from statistics import median

BPS = 10000
PIN = re.compile(r"[0-9a-f]{64}")
FLAGS = {"research_only": True, "live_eligible": False, "execution_ready": False,
         "source_authenticated": False, "owner_approval_verified": False}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0, maximum=2**39):
    need(type(value) is int and minimum <= value <= maximum, "INVALID_INTEGER")
    return value


def number(value):
    need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,16})?", value),
         "DECIMAL_STRING_REQUIRED")
    return Fraction(value)


def display(value):
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 30
        return format(Decimal(value.numerator) / Decimal(value.denominator), ".8f")


def check_terms(t):
    need(type(t) is dict and set(t)-{"quote_gate"} == {
        "format", "market", "scope", "registered_at", "start", "end", "horizon_seconds", "max_gap_seconds",
        "early_seconds", "move_bps", "fee_bps", "slippage_bps", "fixed_y_bps", "confidence",
        "models", "binary_arms"}, "TERMS_SCHEMA")
    need(t["format"] == "tradegen-upside-terms-v1" and type(t["market"]) is str
         and re.fullmatch(r"KRW-[A-Z0-9]{1,20}", t["market"]) and type(t["scope"]) is str
         and 0 < len(t["scope"]) <= 140, "TERMS_SCOPE")
    start, end, horizon = integer(t["start"]), integer(t["end"]), integer(t["horizon_seconds"], 4, 2592000)
    need(integer(t["registered_at"]) < start < end and (end-start) % horizon == 0
         and (end-start)//horizon <= 100000, "UNREGISTERED_OR_INVALID_COHORT")
    gap = integer(t["max_gap_seconds"], 1, horizon)
    need(2*gap < horizon, "INVALID_GAP")
    integer(t["early_seconds"], 0, horizon)
    for name in ("move_bps", "fee_bps", "slippage_bps", "fixed_y_bps"):
        v = number(t[name])
        need(0 <= v < BPS and (name not in ("move_bps", "fixed_y_bps") or v > 0), "INVALID_BPS")
    need(number(t["fixed_y_bps"]) <= 500 and Fraction(1,2) < number(t["confidence"]) <= 1, "INVALID_GATE")
    need(t.get("quote_gate","recorder") in ("recorder","corroborated"), "INVALID_QUOTE_GATE")
    models, binary = t["models"], t["binary_arms"]
    need(type(models) is dict and len(models) <= 12 and not ({"fixed"} & models.keys())
         and all(type(k) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", k)
                 and type(v) is str and PIN.fullmatch(v) for k, v in models.items())
         and len(set(models.values())) == len(models) and type(binary) is list
         and all(type(k) is str for k in binary)
         and len(binary) == len(set(binary)) and set(binary) <= models.keys()
         and not ({"M", "B1"} & set(binary)), "MODEL_PINS")


def _signal_index(t, signals):
    updates = {arm: [] for arm in t["models"]}
    last = {}
    for f in signals:
        arm = f["arm"]
        need(arm in updates and f["market"] == t["market"] and f["model_sha256"] == t["models"][arm],
             "SIGNAL_SCOPE_OR_MODEL")
        a, issued, received, exp = (integer(f[k]) for k in ("as_of","issued_at","received_at","expires_at"))
        need(a <= issued <= received and a < exp and f["direction"] in ("up","down","neutral","unavailable"), "SIGNAL_TIME_OR_DIRECTION")
        if f["direction"] == "unavailable":
            need(f["p_up"] is None, "UNAVAILABLE_SIGNAL_INVALID")
            up = None
        elif arm in t["binary_arms"]:
            need(f["p_up"] is None and f["direction"] in ("up","neutral"), "BINARY_SIGNAL_INVALID")
            up = f["direction"] == "up"
        else:
            p = number(f["p_up"])
            need(p <= 1, "SIGNAL_PROBABILITY_INVALID")
            up = f["direction"] == "up" and p >= number(t["confidence"])
        prev = last.get(arm)
        need(prev is None or (a > prev[0] and received > prev[1]), "REVISED_OR_BACKDATED_SIGNAL")
        last[arm] = (a, received)
        updates[arm].append((received, exp, up, a))
    return {arm: ([r[0] for r in rows], rows) for arm, rows in updates.items()}


def _book(q):
    at, dated = integer(q["at"]), integer(q["bid_at"])
    mark_at = integer(q["last_trade_at"])
    need(type(q["same_second"]) is bool and type(q["blocked"]) is bool and dated <= at and mark_at <= at,
         "QUOTE_TIME_OR_FLAGS")
    if not q["same_second"] or dated != at or q["bid"] is None or q["ask"] is None:
        return at, None
    bid, ask, mark = (number(q[k]) for k in ("bid", "ask", "last_trade"))
    need(0 < bid < ask and mark > 0, "INVALID_OR_CROSSED_BOOK")
    return at, (at, bid, ask, mark, mark_at, q["blocked"])


def _update(index, arm, at):
    times, rows = index[arm]
    slot = bisect_left(times, at)
    if slot < len(times) and times[slot] == at:
        return None   # The new record may already have superseded the prior one.
    i = slot-1
    if i < 0 or at >= rows[i][1]:
        return None
    return rows[i]


def _net(exit_bid, entry_ask, costs):
    return (exit_bid / entry_ask * costs - 1) * BPS


def _event(rows, costs, move):
    trough = rows[0]
    for q in rows[1:]:
        if _net(q[1], trough[2], costs) >= move:
            return trough[0], q[0]
        if q[2] < trough[2]:  # first equal trough retained
            trough = q
    return None


def _window(t, rows, left, index, costs):
    scheduled_exit = left + t["horizon_seconds"] - t["max_gap_seconds"]
    terminal = next((i for i, (at, _) in enumerate(rows) if at >= scheduled_exit), None)
    if terminal is None or rows[0][0]-left > t["max_gap_seconds"]:
        return None, "SHORT_OR_MISSING_EDGE"
    included = rows[:terminal+1]
    if any(q is None for _, q in included):
        return None, "UNAVAILABLE_BOOK"
    if any(b[0]-a[0] > t["max_gap_seconds"] for a,b in zip(included, included[1:])):
        return None, "QUOTE_GAP"
    books = [q for _,q in included]
    if t.get("quote_gate") == "corroborated" and books[-1][-1]:
        return None, "EXIT_STATUS_OR_SIZE_UNUSABLE"
    if len(books) < 3:
        return None, "INSUFFICIENT_BOOKS"
    event = _event(books, costs, number(t["move_bps"]))
    y = number(t["fixed_y_bps"])/BPS
    def allowed(q):
        at, bid, _, mark, mark_at, blocked = q
        return not blocked and (at-mark_at <= 30 or bid > mark*(1-y))
    results = {}
    for arm in ["fixed", *index]:
        covered = 0
        decisions = 0
        signal = entry = post_onset = None
        was_eligible = False
        for i, q in enumerate(books[:-1]):
            next_book = books[i+1]
            if not allowed(q):
                was_eligible = False
                continue
            if next_book[0] >= scheduled_exit:
                continue
            decisions += 1
            # During the open interval use only the previous clean book and a
            # recorded signal already received strictly before the next ask.
            update = _update(index, arm, next_book[0]) if arm != "fixed" else None
            if update and update[3] > q[0]:
                update = None
            up = True if arm == "fixed" else (update[2] if update is not None else None)
            if arm == "fixed":
                alert_at = q[0] if not was_eligible else None
                decision_at = q[0]
            else:
                alert_at = update[0] if update else None
                decision_at = max(q[0], alert_at) if alert_at is not None else None
            was_eligible = True
            covered += int(up is not None)
            if (up is True and event and alert_at is not None and event[0] <= alert_at <= decision_at < event[1]
                    and post_onset is None):
                post_onset = decision_at
            if up is True and entry is None and allowed(next_book):
                signal, entry = decision_at, next_book
        close = books[-1]
        results[arm] = {"signal_at": signal, "post_onset_signal_at": post_onset, "entry_at": entry[0] if entry else None,
                        "net_bps": _net(close[1], entry[2], costs) if entry else Fraction(0),
                        "available": covered, "opportunities": decisions}
    return (event, results, books[-1][0]), None


def _summary(records, arm, early):
    events = hits = early_hits = anticipated = late = entries = false = opportunities = available = 0
    gains, entered_gains, event_gains, delays = [], [], [], []
    for event, arms, _ in records:
        r = arms[arm]
        pnl, signal, entry = r["net_bps"], r["signal_at"], r["entry_at"]
        gains.append(pnl)
        opportunities += r["opportunities"]
        available += r["available"]
        if entry is not None:
            entries += 1
            entered_gains.append(pnl)
        if event is None:
            false += int(entry is not None)
            continue
        events += 1
        event_gains.append(pnl)
        onset, crossed = event
        if r["post_onset_signal_at"] is not None:
            delays.append(r["post_onset_signal_at"] - onset)
        if entry is not None and entry < crossed:
            hits += 1
            early_hits += int(entry <= onset+early)
            anticipated += int(signal < onset)
        elif entry is not None:
            late += 1
    def mean(items):
        return display(sum(items, Fraction(0))/len(items)) if items else None
    cumulative = peak = max_drawdown = Fraction(0)
    for gain in gains:   # equal fixed unit notional each independent window, no compounding
        cumulative += gain
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak-cumulative)
    return dict(fixed_unit_notional_close_to_close_drawdown_bps=display(max_drawdown) if gains else None,
                windows=len(records), surge_events=events, entries=entries, detected_before_cross=hits,
                early_captures=early_hits, early_recall=display(Fraction(early_hits, events)) if events else None,
                anticipated_signals=anticipated, late_entries=late,
                false_entries=false, negative_windows=len(records)-events,
                recall=display(Fraction(hits, events)) if events else None,
                false_entry_rate=display(Fraction(false, len(records)-events)) if len(records)>events else None,
                post_onset_detected_delay_count=len(delays),
                median_post_onset_detected_signal_delay_seconds=display(median([Fraction(d) for d in delays])) if delays else None,
                eligible_decision_quotes=opportunities, covered_decision_quotes=available,
                mean_fixed_exit_net_bps_per_window=mean(gains), mean_fixed_exit_net_bps_per_entry=mean(entered_gains),
                mean_fixed_exit_net_bps_per_surge_window=mean(event_gains))


def evaluate(terms, quotes, signals):
    """Evaluate normalized records; rows are passed in independently authenticated receipt order."""
    check_terms(terms)
    t = terms
    index = _signal_index(t, signals)
    prepared = []
    for q in quotes:
        need(q["market"] == t["market"] and q["scope"] == t["scope"], "QUOTE_OUTSIDE_COHORT")
        checked = _book(q)
        if t.get("quote_gate") == "corroborated" and q.get("corroborated") is not True:
            checked = (checked[0], None)
        prepared.append(checked)
    times = [r[0] for r in prepared]
    need(all(b>a for a,b in zip(times, times[1:])), "UNORDERED_OR_TIED_QUOTES")
    fee, slip = (number(t[k])/BPS for k in ("fee_bps","slippage_bps"))
    costs = (1-fee)*(1-slip)/((1+fee)*(1+slip))
    records, paired, omissions = [], [], Counter()
    audit = []
    for left in range(t["start"], t["end"], t["horizon_seconds"]):
        lower = bisect_left(times, left)
        upper = bisect_left(times, left+t["horizon_seconds"], lower)
        rec, reason = _window(t, prepared[lower:upper], left, index, costs)
        if reason:
            omissions[reason] += 1
            continue
        records.append(rec)
        common = all(a["available"] == a["opportunities"] for a in rec[1].values()) and rec[1]["fixed"]["opportunities"] > 0
        if common:
            paired.append(rec)
        audit.append({"start":left,"exit_at":rec[2],"onset_at":rec[0][0] if rec[0] else None,
                      "crossed_at":rec[0][1] if rec[0] else None,"paired":common,
                      "arms":{a: {**r,"net_bps":display(r["net_bps"])} for a,r in rec[1].items()}})
    def score(rows):
        return {a:_summary(rows,a,t["early_seconds"]) for a in ["fixed",*index]}
    comparisons = {}
    for arm in index:
        for other in (["fixed","B1"] if arm == "M" and "B1" in index else ["fixed"]):
            differences = [arms[arm]["net_bps"] - arms[other]["net_bps"] for _,arms,_ in paired]
            comparisons[f"{arm}_minus_{other}"] = {
                "windows":len(paired),
                "mean_net_bps_per_paired_window":display(sum(differences, Fraction(0))/len(paired)) if paired else None}
    status = "DESCRIPTIVE" if paired else "INSUFFICIENT_PAIRED_COVERAGE"
    if paired and omissions:
        status = "PARTIAL_COHORT"
    return {"format":"tradegen-upside-report-v1",**FLAGS, "actual_fill_count":None,"actual_realized_pnl":None,
            "scheduled_windows":(t["end"]-t["start"])//t["horizon_seconds"], "excluded_windows":dict(omissions),
            "all_complete_windows":score(records), "paired_complete_windows":score(paired),
            "coverage_excluded_from_paired":len(records)-len(paired),
            "status":status, "paired_comparisons":comparisons, "windows":audit}
