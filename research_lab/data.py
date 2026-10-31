"""Offline, hash-pinned daily-close inputs for exploratory strategy research.

No network, credentials, account state, protected holdout, price filling or raw
cache writes are available here. ``root`` always denotes a repository root.
The selected caches were inspected in earlier research; a chronological split
does not turn them into independent or prospective confirmation.
"""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
import math
from pathlib import Path
from typing import TypedDict


CUTOFF = "2026-09-24"
ASSETS = ("SPY", "QQQ", "GLD", "TLT", "TIGER200", "BTC_KRW", "BTC_USDT", "ETH_USDT")
_CACHE = Path("docs/asset_expansion/cache")
_SPECS = {
    "SPY": ("yf_SPY.csv", "USD", 252, "provider_adjusted_close"),
    "QQQ": ("yf_QQQ.csv", "USD", 252, "provider_adjusted_close"),
    "GLD": ("yf_GLD.csv", "USD", 252, "provider_adjusted_close"),
    "TLT": ("yf_TLT.csv", "USD", 252, "provider_adjusted_close"),
    "TIGER200": ("yf_102110.KS.csv", "KRW", 252, "provider_adjusted_close"),
    "BTC_KRW": ("upbit_KRW-BTC.csv", "KRW", 365, "unadjusted_spot_close"),
    "BTC_USDT": ("binance_BTCUSDT.csv", "USDT", 365, "unadjusted_spot_close"),
    "ETH_USDT": ("binance_ETHUSDT.csv", "USDT", 365, "unadjusted_spot_close"),
}


class SeriesData(TypedDict):
    asset_id: str
    dates: tuple[str, ...]
    close: tuple[float, ...]
    annualization: int
    currency: str
    provider: str
    symbol: str
    time_basis: str
    source_path: str
    source_sha256: str
    selected_rows_sha256: str
    data_manifest_sha256: str
    adjustment_status: str
    prior_use: str


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _root(root: Path | str | None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate research manifest key")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError("nonfinite research manifest constant")


def _manifest(root: Path) -> tuple[dict, str]:
    path = root / "research_lab/data_manifest.json"
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("linked research manifest refused")
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("invalid research manifest JSON") from exc
    if (type(manifest) is not dict or manifest.get("schema_version") != 1
            or manifest.get("cutoff_inclusive") != CUTOFF
            or type(manifest.get("inventory")) is not list
            or len(manifest["inventory"]) != 46
            or manifest.get("inventory_file_count") != 46
            or type(manifest.get("selection")) is not dict
            or set(manifest["selection"]) != set(ASSETS)
            or manifest.get("inventory_sha256") != _sha(_canonical(manifest["inventory"]))
            or manifest.get("selection_sha256") != _sha(_canonical(manifest["selection"]))):
        raise ValueError("research manifest contract or fingerprint mismatch")
    inventory = {row["path"]: row for row in manifest["inventory"]}
    if len(inventory) != 46:
        raise ValueError("duplicate inventory path")
    for asset, (name, currency, annualization, adjustment) in _SPECS.items():
        item = manifest["selection"][asset]
        expected = (_CACHE / name).as_posix()
        if (type(item) is not dict or item.get("path") != expected
                or item.get("currency") != currency or item.get("annualization") != annualization
                or item.get("adjustment_status") != adjustment or expected not in inventory
                or item.get("source_sha256") != inventory[expected]["sha256"]):
            raise ValueError("selected research series metadata mismatch")
    return manifest, _sha(raw)


def manifest_digest(*, root: Path | str | None = None) -> str:
    """SHA256 of the exact validated manifest bytes, for protocol/run binding."""
    return _manifest(_root(root))[1]


def _load_one(asset: str, root: Path, manifest: dict, manifest_sha: str) -> SeriesData:
    if type(asset) is not str or asset not in _SPECS:
        raise ValueError("asset is outside the fixed research universe")
    item = manifest["selection"][asset]
    # The path comes from the code allowlist, never a caller-supplied filename.
    path = root / _CACHE / _SPECS[asset][0]
    if path.is_symlink() or path.resolve() != path:
        raise ValueError("linked research data refused")
    raw = path.read_bytes()
    if _sha(raw) != item["source_sha256"]:
        raise ValueError("research source hash mismatch: " + asset)
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    if len(rows) < 2 or len(rows[0]) != 2:
        raise ValueError("research data needs a date and close column")
    previous = None
    selected = []
    dates = []
    closes = []
    for row in rows[1:]:
        if len(row) != 2:
            raise ValueError("malformed research data row")
        try:
            stamp = date.fromisoformat(row[0])
            close = float(row[1])
        except ValueError as exc:
            raise ValueError("invalid research date or close") from exc
        if (stamp.isoformat() != row[0] or not math.isfinite(close) or close <= 0
                or (previous is not None and stamp <= previous)):
            raise ValueError("nonpositive, nonfinite or unordered research data")
        previous = stamp
        if row[0] <= CUTOFF:
            selected.append(row)
            dates.append(row[0])
            closes.append(close)
    selected_sha = _sha(_canonical(selected))
    if (not dates or len(dates) != item["rows"] or dates[0] != item["start"]
            or dates[-1] != item["end"] or selected_sha != item["selected_rows_sha256"]):
        raise ValueError("research filtered-row fingerprint mismatch")
    if item["annualization"] == 365:
        if any((date.fromisoformat(b) - date.fromisoformat(a)).days != 1
               for a, b in zip(dates, dates[1:])):
            raise ValueError("missing crypto daily bar")
    return SeriesData(asset_id=asset, dates=tuple(dates), close=tuple(closes),
                      annualization=item["annualization"], currency=item["currency"],
                      provider=item["provider"], symbol=item["symbol"], time_basis=item["time_basis"],
                      source_path=item["path"], source_sha256=item["source_sha256"],
                      selected_rows_sha256=selected_sha, data_manifest_sha256=manifest_sha,
                      adjustment_status=item["adjustment_status"], prior_use=item["prior_use"])


def load_series(asset: str, *, root: Path | str | None = None) -> SeriesData:
    """Load one of eight pinned native-currency series through the fixed cutoff.

    Dates and closes are immutable tuples; no dates/prices are forward-filled.
    ``provider_adjusted_close`` is not an independent total-return certification.
    """
    base = _root(root)
    manifest, manifest_sha = _manifest(base)
    return _load_one(asset, base, manifest, manifest_sha)


def load_assets(*, root: Path | str | None = None) -> dict[str, SeriesData]:
    """Load the entire fixed universe against a single manifest snapshot."""
    base = _root(root)
    manifest, manifest_sha = _manifest(base)
    return {asset: _load_one(asset, base, manifest, manifest_sha) for asset in ASSETS}
