"""The engine's own state machine: DISARMED → ARMED → HALTED (§4, §5).

Three rules from the service contract are encoded here rather than left to the
UI, because a safety property enforced by a screen is not enforced at all:

  * **Start disarmed** (§5 "프로그램 시작 시 비활성 상태 유지"). A fresh
    `EngineState` is DISARMED. There is no constructor argument that starts it
    armed and no persisted field that restores ARMED.

  * **No automatic re-arm after restart** (§5 "재시작 후 자동 재활성화 방지").
    Halting records why and sets `requires_manual_rearm`. Only an explicit
    operator action clears it — not time passing, not the condition resolving,
    not a restart. `resume()` refuses while the flag is set.

  * **Emergency stop from anywhere** (§5 "전 화면에서 접근 가능한 긴급정지").
    `halt()` is callable in any state including DISARMED, is idempotent, and
    never raises. A kill switch that can throw is not a kill switch.

HALTED means "stop starting new things", not "abandon what is running". Open
simulated orders survive a halt so the operator can settle them deliberately;
that is the difference between a stop and a crash.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class EngineMode(str, Enum):
    DISARMED = "DISARMED"    # rules are not evaluated
    ARMED = "ARMED"          # rules are evaluated and may fire
    HALTED = "HALTED"        # stopped after an anomaly; needs a manual re-arm


class HaltReason(str, Enum):
    OPERATOR = "operator"                # the emergency stop was pressed
    STALE_DATA = "stale_data"            # quotes older than the freshness bound
    NO_DATA = "no_data"                  # provider returned nothing
    PROVIDER_ERROR = "provider_error"
    LIMIT_BREACH = "limit_breach"        # a daily cap was exceeded
    UNKNOWN_STATE = "unknown_state"      # §5 "불명확한 상태에서 신규 실행 차단"


@dataclass(frozen=True)
class Transition:
    at: datetime
    frm: EngineMode
    to: EngineMode
    reason: str = ""
    detail: str = ""


class EngineState:
    """Thread-safe. The evaluation loop and the UI both touch this."""

    def __init__(self, *, on_change: Optional[Callable[[Transition], None]] = None):
        self._lock = threading.RLock()
        self._mode = EngineMode.DISARMED          # always; see module docstring
        self._halt_reason: Optional[HaltReason] = None
        self._halt_detail = ""
        self._requires_manual_rearm = False
        self._history: list[Transition] = []
        self._on_change = on_change

    # -- reads ---------------------------------------------------------------
    @property
    def mode(self) -> EngineMode:
        with self._lock:
            return self._mode

    @property
    def is_armed(self) -> bool:
        return self.mode is EngineMode.ARMED

    @property
    def halt_reason(self) -> Optional[HaltReason]:
        with self._lock:
            return self._halt_reason

    @property
    def halt_detail(self) -> str:
        with self._lock:
            return self._halt_detail

    @property
    def requires_manual_rearm(self) -> bool:
        with self._lock:
            return self._requires_manual_rearm

    @property
    def history(self) -> tuple[Transition, ...]:
        with self._lock:
            return tuple(self._history)

    def describe(self) -> str:
        with self._lock:
            if self._mode is EngineMode.HALTED:
                why = self._halt_reason.value if self._halt_reason else "unknown"
                return f"HALTED ({why}) — manual re-arm required"
            return self._mode.value

    # -- writes --------------------------------------------------------------
    def _transition(self, to: EngineMode, reason: str = "", detail: str = "") -> Transition:
        record = Transition(datetime.now(timezone.utc), self._mode, to, reason, detail)
        self._mode = to
        self._history.append(record)
        del self._history[:-500]
        if self._on_change is not None:
            try:
                self._on_change(record)
            except Exception:
                pass          # a listener must never break the state machine
        return record

    def arm(self) -> tuple[bool, str]:
        """Explicit operator action. Refused while a halt is unacknowledged."""
        with self._lock:
            if self._requires_manual_rearm:
                why = self._halt_reason.value if self._halt_reason else "a halt"
                return False, (f"Acknowledge the halt ({why}) before arming. "
                               f"This program never re-arms itself.")
            if self._mode is EngineMode.ARMED:
                return True, "Already armed."
            self._transition(EngineMode.ARMED, reason="operator armed")
            return True, "Armed."

    def disarm(self, detail: str = "") -> None:
        """Ordinary stand-down. Unlike a halt, this needs no acknowledgement."""
        with self._lock:
            if self._mode is EngineMode.DISARMED:
                return
            self._halt_reason = None
            self._halt_detail = ""
            self._requires_manual_rearm = False
            self._transition(EngineMode.DISARMED, reason="operator disarmed",
                             detail=detail)

    def halt(self, reason: HaltReason = HaltReason.OPERATOR, detail: str = "") -> None:
        """Emergency stop. Callable from any state, idempotent, never raises."""
        with self._lock:
            self._halt_reason = reason
            self._halt_detail = detail
            self._requires_manual_rearm = True
            if self._mode is EngineMode.HALTED:
                return
            self._transition(EngineMode.HALTED, reason=reason.value, detail=detail)

    def acknowledge(self) -> None:
        """Operator has read the halt. Clears the flag but does NOT arm."""
        with self._lock:
            self._requires_manual_rearm = False
            self._transition(EngineMode.DISARMED, reason="halt acknowledged",
                             detail=self._halt_detail)
            self._halt_reason = None
            self._halt_detail = ""

    # -- persistence ---------------------------------------------------------
    def snapshot(self) -> dict:
        """What survives a restart.

        The mode is deliberately absent. Restoring it would re-arm the engine
        on launch, which §5 forbids; a restart always lands in DISARMED and the
        operator decides again.
        """
        with self._lock:
            return {
                "halt_reason": self._halt_reason.value if self._halt_reason else None,
                "halt_detail": self._halt_detail,
                "requires_manual_rearm": self._requires_manual_rearm,
            }

    def restore(self, snapshot: dict) -> None:
        """Reload an unacknowledged halt so a restart cannot launder it away."""
        with self._lock:
            raw = (snapshot or {}).get("halt_reason")
            try:
                self._halt_reason = HaltReason(raw) if raw else None
            except ValueError:
                self._halt_reason = HaltReason.UNKNOWN_STATE
            self._halt_detail = str((snapshot or {}).get("halt_detail") or "")
            self._requires_manual_rearm = bool(
                (snapshot or {}).get("requires_manual_rearm"))
            self._mode = EngineMode.DISARMED
