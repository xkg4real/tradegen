"""One-use, request-bound dispatch capabilities; only the controller issues them.

This registry is process-local application discipline, not a sandbox against a
process allowed to replace signed Python code. It carries no credentials.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import threading
from datetime import date, datetime
from decimal import Decimal
from collections.abc import Mapping


def plain(value):
    """Detached canonical business values; never accept nonfinite money."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("nonfinite control value")
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("invalid control mapping key")
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(plain(item) for item in value)
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise ValueError("unsupported control value")


def digest(value) -> str:
    try:
        data = json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("invalid control digest") from None
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True, kw_only=True)
class _Capability:
    request_digest: str


_LOCK = threading.Lock()
_ISSUED: dict[int, tuple[_Capability, str]] = {}


def _issue(request):
    """Controller only: called after the durable pre-send transition."""
    item = _Capability(request_digest=digest(request))
    with _LOCK:
        _ISSUED[id(item)] = (item, item.request_digest)
    return item


def consume_capability(capability, request) -> None:
    """Consume even on a changed request: a failed attempt never revives a token."""
    with _LOCK:
        issued = _ISSUED.pop(id(capability), None)
    if issued is None or issued[0] is not capability or type(capability) is not _Capability:
        raise ValueError("dispatch capability not issued or already consumed")
    if capability.request_digest != issued[1] or digest(request) != issued[1]:
        raise ValueError("dispatch capability request mismatch")
