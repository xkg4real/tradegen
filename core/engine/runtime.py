"""Ties the engine together and runs it on a background thread.

`EngineRuntime` owns the state machine, the order book, the evaluator and the
quote feed, and exposes the small surface the UI actually needs: arm, disarm,
halt, acknowledge, and a stream of decisions to display.

Design points worth stating:

  * **The loop runs only while armed.** A disarmed engine makes no network
    request. There is no "just polling quietly in the background" state — if
    the dashboard says DISARMED, nothing is happening.

  * **A tick is atomic per rule, not per pass.** Each rule is evaluated, and
    its trigger count persisted, before the next is considered. A crash halfway
    through a pass therefore cannot replay the rules that already fired, since
    their incremented counts are already on disk and the deterministic order id
    would collide.

  * **Everything the operator did not see is still recorded.** Decisions are
    kept in a bounded ring and journalled to disk, so "why did nothing happen
    at 09:31" has an answer after the fact.

  * **The state snapshot is written on every transition**, not on shutdown. A
    process killed while halted must still refuse to arm on next launch.

  * **A missing quote gets a short, counted grace; a halt is still final.** A
    symbol may miss `no_data_grace` passes (default 3) for a reason that can
    clear by itself before the engine halts. The first miss of an episode is
    written to the decision log and the dashboard names the symbol while it
    lasts. The next pass is the retry — there is no separate reconnect loop,
    and the quote clients make one attempt each — and once halted the engine
    still never re-arms itself. Arming starts a fresh window.

  * **Freshness is judged after the fetch.** The clock is read again once the
    quotes are in, so time spent waiting on a slow provider counts against
    every quote taken earlier in the same pass.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from core import calendars, markets
from core.engine.evaluator import Decision, Evaluator, Outcome
from core.engine.feed import QuoteFeed
from core.engine.orders import OrderBook
from core.engine.state import EngineMode, EngineState, HaltReason
from core.rules.model import RuleStatus
from core.rules.store import RuleStore

DECISION_RING = 400


class EngineRuntime:
    def __init__(self, store: RuleStore, feed: QuoteFeed, *,
                 tick_seconds: Optional[float] = None,
                 max_quote_age_s: Optional[float] = None,
                 no_data_grace: Optional[int] = None,
                 state_path: Optional[Path] = None,
                 on_update: Optional[Callable[[], None]] = None,
                 clock: Optional[Callable[[], datetime]] = None):
        import config
        self.store = store
        self.feed = feed
        self.tick_seconds = (tick_seconds if tick_seconds is not None
                             else config.ENGINE_TICK_SECONDS)
        # Capped: a mistyped NEXTGEN_NO_DATA_GRACE=1000 must not switch the
        # missing-data halt off.
        self.no_data_grace = min(10, max(0, int(no_data_grace if no_data_grace is not None
                                                else config.NO_DATA_GRACE_TICKS)))
        self.state_path = Path(state_path) if state_path else (
            config.trading_dir() / "engine.json")
        self.on_update = on_update
        # Injectable so a test can pin "now" to a moment when a given venue is
        # trading. Freshness is judged per market session, so a tick at real
        # wall-clock time only fires when that market happens to be open.
        self._now = clock or (lambda: datetime.now(timezone.utc))

        self.state = EngineState(on_change=lambda _t: self._persist())
        self.book = OrderBook()
        self.evaluator = Evaluator(
            self.state, self.book,
            max_quote_age_s=(max_quote_age_s if max_quote_age_s is not None
                             else config.QUOTE_MAX_AGE_SECONDS))

        self._decisions: deque[Decision] = deque(maxlen=DECISION_RING)
        self._lock = threading.RLock()
        # Only one evaluation pass at a time. Overlapping passes would each
        # read the same trigger_count and fire a rule twice.
        self._tick_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._wake = threading.Event()
        self._stopping = False
        self._last_tick: Optional[datetime] = None
        # Last (outcome, reason) recorded per rule, so an unchanged verdict is
        # not re-logged on every pass.
        self._last_verdict: dict[str, tuple[str, str]] = {}

        self._restore()

    # -- operator actions ----------------------------------------------------
    def arm(self) -> tuple[bool, str]:
        was_armed = self.state.is_armed
        ok, message = self.state.arm()
        if ok:
            if not was_armed:
                # A real arming starts a fresh grace window and a fresh log
                # episode. Pressing Arm on an already armed engine must not,
                # or the window could be reset forever.
                self.feed.clear_misses()
                with self._lock:
                    self._last_verdict.clear()
            self._ensure_thread()
            self._wake.set()
        self._notify()
        return ok, message

    def disarm(self) -> None:
        self.state.disarm()
        self._notify()

    def halt(self, reason: HaltReason = HaltReason.OPERATOR, detail: str = "") -> None:
        self.state.halt(reason, detail)
        self._notify()

    def acknowledge(self) -> None:
        self.state.acknowledge()
        self._notify()

    # -- reads ---------------------------------------------------------------
    @property
    def mode(self) -> EngineMode:
        return self.state.mode

    def decisions(self, limit: int = 50) -> tuple[Decision, ...]:
        """Newest first.

        Sorted by timestamp rather than insertion order: the two coincide while
        the engine is running, but a journal reloaded from disk need not be in
        order, and the log claims to be chronological.
        """
        with self._lock:
            ordered = sorted(self._decisions, key=lambda d: d.at, reverse=True)
        return tuple(ordered[:limit])

    @property
    def last_tick(self) -> Optional[datetime]:
        with self._lock:
            return self._last_tick

    def dashboard(self) -> dict:
        """Everything the status page shows, computed in one consistent read."""
        counts = self.book.counts_today()
        rules = self.store.all()
        recent = self.decisions(limit=200)
        today = datetime.now(timezone.utc).date()
        rejected_today = sum(
            1 for d in recent
            if d.outcome is Outcome.REJECTED and d.at.date() == today)
        fired_today = sum(
            1 for d in recent
            if d.outcome is Outcome.FIRED and d.at.date() == today)
        return {
            "venues": self._venue_status(rules),
            "degraded": self._degraded(rules),
            "calendar_stale": calendars.stale_markets(),
            "mode": self.state.mode,
            "describe": self.state.describe(),
            "halt_reason": self.state.halt_reason,
            "halt_detail": self.state.halt_detail,
            "needs_ack": self.state.requires_manual_rearm,
            "active_rules": sum(1 for r in rules if r.status is RuleStatus.ACTIVE),
            "total_rules": len(rules),
            "fired_today": fired_today,
            "rejected_today": rejected_today,
            "orders_today": counts,
            "open_orders": self.book.open_orders(),
            "notional_today": self.book.notional_today(),
            "last_tick": self.last_tick,
        }

    def _degraded(self, rules) -> list[tuple[str, int, str]]:
        """Symbols of active rules on a trading venue whose last quote fetch
        failed: the engine is armed but cannot evaluate them."""
        now = self._now()
        watched = {r.symbol for r in rules
                   if r.status is RuleStatus.ACTIVE
                   and markets.is_open(r.market, now) is not False}
        return [row for row in self.feed.degraded() if row[0] in watched]

    def _venue_status(self, rules) -> list[dict]:
        """Per-venue trading state, so a quiet dashboard explains itself.

        Without this the operator sees an armed engine, active rules and no
        activity, with the reason buried one line deep in the decision log.
        """
        now = self._now()
        out: dict[str, dict] = {}
        for rule in rules:
            if rule.status is not RuleStatus.ACTIVE or not rule.market:
                continue
            entry = out.get(rule.market)
            if entry is None:
                # Must go through the calendar-aware path, or the dashboard
                # would report a public holiday as open while the engine skips.
                market = markets.get(rule.market)
                if market is None:
                    state, why = "unknown", "not a known venue"
                else:
                    state, why = market.trading_state(now)
                entry = out[rule.market] = {
                    "code": rule.market,
                    "open": True if state == "open" else (
                        False if state == "closed" else None),
                    "why": why,
                    "describe": (market.describe(now) if market
                                 else "not a known venue"),
                    "rules": 0,
                }
            entry["rules"] += 1
        return [out[k] for k in sorted(out)]

    # -- the loop ------------------------------------------------------------
    def _ensure_thread(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopping = False
            self._thread = threading.Thread(target=self._loop, daemon=True,
                                            name="nextgen-engine")
            self._thread.start()

    def _loop(self) -> None:
        while not self._stopping:
            if self.state.is_armed:
                try:
                    self.tick()
                except Exception as exc:
                    # An unexpected failure inside evaluation is exactly the
                    # "unclear state" §5 says must stop new execution.
                    self.state.halt(HaltReason.UNKNOWN_STATE,
                                    f"{type(exc).__name__}: {exc}")
                    self._notify()
            self._wake.wait(self.tick_seconds)
            self._wake.clear()

    def stop(self) -> None:
        self._stopping = True
        self._wake.set()

    def tick(self) -> list[Decision]:
        """One evaluation pass over every active rule.

        Non-reentrant: if a pass is already running (the background loop, or a
        manual tick from the UI), this returns empty rather than queueing a
        second concurrent pass over the same rules.
        """
        if not self._tick_lock.acquire(blocking=False):
            return []
        try:
            return self._tick_locked()
        finally:
            self._tick_lock.release()

    def _tick_locked(self) -> list[Decision]:
        now = self._now()
        rules = self.store.active()
        if not rules:
            with self._lock:
                self._last_tick = now
            return []

        # Only ask providers about venues that are actually trading. Overnight
        # this is the difference between spending an API quota on markets that
        # cannot move and spending nothing. The evaluator checks the session
        # before it looks at the quote, so a closed rule still produces its
        # SKIPPED decision from a `None` quote.
        tradeable = [r for r in rules if markets.is_open(r.market, now) is not False]
        asked = {(r.symbol, r.market) for r in tradeable}
        quotes = self.feed.fetch_many(asked) if asked else {}
        # Read the clock again: a slow or failing symbol can hold the fetch for
        # many seconds, and measured from the earlier `now` a quote taken at
        # the start of the pass would still look brand new when its rule is
        # finally evaluated.
        started, now = now, self._now()
        produced: list[Decision] = []
        graced: dict[int, str] = {}         # id() of a decision skipped in grace -> its error

        for rule in rules:
            if not self.state.is_armed:
                break                      # a halt mid-pass stops the pass
            quote = quotes.get(rule.symbol)
            grace = self._grace(rule.symbol) if quote is None else ""
            decision = self.evaluator.evaluate(
                rule, quote,
                # A rule whose venue was shut when the fetch set was chosen was
                # never asked about. Judge it at that same instant: otherwise a
                # venue opening mid-pass would read as "open, no quote" and
                # halt the engine. The next pass picks it up.
                now=now if (rule.symbol, rule.market) in asked else started,
                quote_error=self.feed.last_error(rule.symbol),
                quote_grace=grace)
            if grace and f"miss {grace}" in decision.reason:
                graced[id(decision)] = self.feed.last_error(rule.symbol)
            produced.append(decision)
            if decision.fired:
                # Persist the incremented count before moving on, so a crash
                # cannot replay this trigger.
                self.store.save(rule.record_trigger())

        # Cancel sweep uses the rule set as-is; ids are stable across the pass.
        produced.extend(self.evaluator.sweep_cancellations(
            self.store.by_id(), {k: v for k, v in quotes.items() if v}, now=now))

        with self._lock:
            # Record only what changed. A five-second tick against a closed
            # market would otherwise write the same "US is closed" line 720
            # times an hour and push every real event out of the ring.
            for decision in produced:
                # A grace episode is one line, not one per pass: the miss
                # count changes every pass and would otherwise push real
                # events (a FIRED decision) out of the ring.
                # A change of cause inside an episode is still logged.
                signature = (decision.outcome.value,
                             "in grace: " + graced[id(decision)] if id(decision) in graced
                             else decision.reason)
                if self._last_verdict.get(decision.rule_id) == signature:
                    continue
                self._last_verdict[decision.rule_id] = signature
                self._decisions.append(decision)
            self._last_tick = now
        self._persist()
        self._notify()
        return produced

    def _grace(self, symbol: str) -> str:
        """"2 of 3" while this symbol's missing quote is still inside the grace
        window, "" once it is not (or never was): the evaluator halts on ""."""
        misses = self.feed.misses(symbol)
        if (0 < misses <= self.no_data_grace
                and not self.feed.is_permanent(symbol)):
            return f"{misses} of {self.no_data_grace}"
        return ""

    # -- practice ------------------------------------------------------------
    def reset_practice(self) -> None:
        """Clears the simulated book, decisions and crossing history (§3)."""
        self.book.reset()
        self.feed.reset()
        with self._lock:
            self._decisions.clear()
            self._last_verdict.clear()
        self._persist()
        self._notify()

    # -- persistence ---------------------------------------------------------
    def _persist(self) -> None:
        payload = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "state": self.state.snapshot(),
            "orders": self.book.snapshot(),
            "decisions": [
                {"rule_id": d.rule_id, "rule_name": d.rule_name,
                 "outcome": d.outcome.value, "reason": d.reason,
                 "at": d.at.isoformat(),
                 "quote_price": str(d.quote_price) if d.quote_price is not None else None}
                for d in list(self._decisions)[-DECISION_RING:]
            ],
        }
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=str(self.state_path.parent),
                                            suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(temp, self.state_path)
        except Exception:
            pass

    def _restore(self) -> None:
        if not self.state_path.is_file():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.state.restore(payload.get("state") or {})
        self.book.restore(payload.get("orders") or [])
        for raw in payload.get("decisions") or []:
            try:
                price = raw.get("quote_price")
                self._decisions.append(Decision(
                    rule_id=raw["rule_id"], rule_name=raw.get("rule_name", ""),
                    outcome=Outcome(raw["outcome"]), reason=raw.get("reason", ""),
                    at=datetime.fromisoformat(raw["at"]),
                    quote_price=Decimal(price) if price is not None else None,
                ))
            except Exception:
                continue

    def _notify(self) -> None:
        if self.on_update is None:
            return
        try:
            self.on_update()
        except Exception:
            pass          # a UI refresh failure must not stop the engine
