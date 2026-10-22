"""Local persistence for operator-authored rules, with edit history (§7).

Rules live in one JSON file under `config.trading_dir()`. A single file rather
than one per rule because the whole set is always loaded together, and an
operator inspecting their own data should find one readable document rather
than a directory to reassemble.

Every save appends the *previous* revision to a per-rule history list, so the
edit history required by §7 is a consequence of how saving works rather than a
feature that can be forgotten. History is capped per rule; the cap discards the
oldest revisions, never the current one.

Writes are atomic (temp file + replace). A half-written rule file would be
worse than a missing one: the engine would arm against a truncated rule set.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from core.rules.model import (CancelCondition, Comparator, Limits, OrderKind,
                              PriceCondition, Rule, RuleStatus, Side, SizeMode)

HISTORY_LIMIT = 50


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #
def _dec(value: Optional[Decimal]) -> Optional[str]:
    return str(value) if value is not None else None


def _undec(value) -> Optional[Decimal]:
    return Decimal(str(value)) if value not in (None, "") else None


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _undt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def to_dict(rule: Rule) -> dict:
    return {
        "id": rule.id, "revision": rule.revision, "name": rule.name,
        "symbol": rule.symbol, "market": rule.market,
        "side": rule.side.value if rule.side else None,
        "size_mode": rule.size_mode.value if rule.size_mode else None,
        "size_value": _dec(rule.size_value),
        "order_kind": rule.order_kind.value if rule.order_kind else None,
        "limit_price": _dec(rule.limit_price),
        "conditions": [{"comparator": c.comparator.value, "level": _dec(c.level)}
                       for c in rule.conditions],
        "require_all_conditions": rule.require_all_conditions,
        "valid_from": _dt(rule.valid_from), "valid_to": _dt(rule.valid_to),
        "limits": {
            "max_triggers": rule.limits.max_triggers,
            "max_order_amount": _dec(rule.limits.max_order_amount),
            "max_daily_amount": _dec(rule.limits.max_daily_amount),
        },
        "cancel": {
            "after_seconds": rule.cancel.after_seconds,
            "if_price_beyond": (
                {"comparator": rule.cancel.if_price_beyond.comparator.value,
                 "level": _dec(rule.cancel.if_price_beyond.level)}
                if rule.cancel.if_price_beyond else None),
        },
        "status": rule.status.value, "trigger_count": rule.trigger_count,
        "created_at": _dt(rule.created_at), "updated_at": _dt(rule.updated_at),
        "confirmed_at": _dt(rule.confirmed_at), "notes": rule.notes,
    }


def from_dict(raw: dict) -> Rule:
    cancel_raw = raw.get("cancel") or {}
    beyond = cancel_raw.get("if_price_beyond")
    limits_raw = raw.get("limits") or {}
    return Rule(
        id=raw["id"], revision=int(raw.get("revision") or 1),
        name=raw.get("name", ""), symbol=raw.get("symbol", ""),
        market=raw.get("market", ""),
        side=Side(raw["side"]) if raw.get("side") else None,
        size_mode=SizeMode(raw["size_mode"]) if raw.get("size_mode") else None,
        size_value=_undec(raw.get("size_value")),
        order_kind=OrderKind(raw["order_kind"]) if raw.get("order_kind") else None,
        limit_price=_undec(raw.get("limit_price")),
        conditions=tuple(
            PriceCondition(Comparator(c["comparator"]), _undec(c["level"]))
            for c in raw.get("conditions", []) if c.get("level") is not None
        ),
        require_all_conditions=bool(raw.get("require_all_conditions", True)),
        valid_from=_undt(raw.get("valid_from")), valid_to=_undt(raw.get("valid_to")),
        limits=Limits(
            max_triggers=limits_raw.get("max_triggers"),
            max_order_amount=_undec(limits_raw.get("max_order_amount")),
            max_daily_amount=_undec(limits_raw.get("max_daily_amount")),
        ),
        cancel=CancelCondition(
            after_seconds=cancel_raw.get("after_seconds"),
            if_price_beyond=(PriceCondition(Comparator(beyond["comparator"]),
                                            _undec(beyond["level"]))
                             if beyond else None),
        ),
        status=RuleStatus(raw.get("status") or RuleStatus.DRAFT.value),
        trigger_count=int(raw.get("trigger_count") or 0),
        created_at=_undt(raw.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_undt(raw.get("updated_at")) or datetime.now(timezone.utc),
        confirmed_at=_undt(raw.get("confirmed_at")), notes=raw.get("notes", ""),
    )


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #
class RuleStore:
    """Thread-safe. The engine loop reads it while the UI writes to it."""

    def __init__(self, path: Optional[Path] = None):
        import config
        self.path = Path(path) if path else (config.trading_dir() / "rules.json")
        self._lock = threading.RLock()
        self._rules: dict[str, Rule] = {}
        self._history: dict[str, list[dict]] = {}
        self.load()

    # -- reads ---------------------------------------------------------------
    def all(self) -> tuple[Rule, ...]:
        with self._lock:
            return tuple(sorted(self._rules.values(),
                                key=lambda r: r.updated_at, reverse=True))

    def get(self, rule_id: str) -> Optional[Rule]:
        with self._lock:
            return self._rules.get(rule_id)

    def active(self) -> tuple[Rule, ...]:
        return tuple(r for r in self.all() if r.status is RuleStatus.ACTIVE)

    def by_id(self) -> dict[str, Rule]:
        with self._lock:
            return dict(self._rules)

    def history(self, rule_id: str) -> tuple[dict, ...]:
        with self._lock:
            return tuple(self._history.get(rule_id, ()))

    def symbols(self) -> tuple[tuple[str, str], ...]:
        """(symbol, market) pairs the engine needs quotes for."""
        seen = {(r.symbol, r.market) for r in self.active() if r.symbol}
        return tuple(sorted(seen))

    # -- writes --------------------------------------------------------------
    def save(self, rule: Rule) -> Rule:
        with self._lock:
            previous = self._rules.get(rule.id)
            if previous is not None and previous.revision != rule.revision:
                bucket = self._history.setdefault(rule.id, [])
                bucket.append(to_dict(previous))
                del bucket[:-HISTORY_LIMIT]
            self._rules[rule.id] = rule
            self._flush()
            return rule

    def delete(self, rule_id: str) -> bool:
        with self._lock:
            existed = self._rules.pop(rule_id, None) is not None
            self._history.pop(rule_id, None)
            if existed:
                self._flush()
            return existed

    def clear(self) -> None:
        """The whole-reset action in §7."""
        with self._lock:
            self._rules.clear()
            self._history.clear()
            self._flush()

    # -- disk ----------------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            self._rules.clear()
            self._history.clear()
            if not self.path.is_file():
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return          # a corrupt file must not stop the app launching
            for raw in payload.get("rules", []):
                try:
                    rule = from_dict(raw)
                except Exception:
                    continue    # one bad rule must not lose the rest
                self._rules[rule.id] = rule
            history = payload.get("history") or {}
            if isinstance(history, dict):
                self._history = {k: list(v) for k, v in history.items()
                                 if isinstance(v, list)}

    def _flush(self) -> None:
        """Atomic write. A truncated rule file would arm a partial rule set."""
        payload = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rules": [to_dict(r) for r in self._rules.values()],
            "history": self._history,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, temp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(temp, self.path)
        except Exception:
            pass                # never let a disk problem break the UI

    def export_to(self, destination: Path) -> Path:
        """The operator-confirmed export in §7."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(
            {"version": 1, "rules": [to_dict(r) for r in self.all()]},
            indent=2, ensure_ascii=False), encoding="utf-8")
        return destination
