"""
core/numfmt.py — pure, locale-aware numeric formatting for chart axes/labels.

No Flet, no I/O, no third-party deps — grouping separators, currency symbol and
placement, and compact volume suffixes are derived from small locale tables so
the whole thing is unit-testable offline. Values are formatted HERE and then
interpolated into i18n keys (never format inside the catalog), per the i18n
method. Uppercase technical notation is preserved by callers (this module
only produces the numeric portion).
"""
from __future__ import annotations

from typing import Optional

# Decimal / grouping separators by locale prefix. Default is en (comma group,
# dot decimal). de/ru/es(-ES)/vi use dot/space grouping with comma decimal.
_SEP = {
    "de": (".", ","),   # 1.234.567,89
    "ru": (" ", ","),   # 1 234 567,89
    "fr": (" ", ","),   # 1 234 567,89
    "vi": (".", ","),   # 1.234.567,89
    "es": (".", ","),   # 1.234.567,89
}
_DEFAULT_SEP = (",", ".")  # en, ko, ja, zh-* → 1,234,567.89

# Currency symbol + whether it leads (True) or trails (False) the amount.
_CCY = {
    "KRW": ("₩", True), "USD": ("$", True), "EUR": ("€", True),
    "JPY": ("¥", True), "GBP": ("£", True), "CNY": ("¥", True),
    "HKD": ("HK$", True), "VND": ("₫", False),
}


def _sep_for(locale: Optional[str]) -> tuple[str, str]:
    loc = (locale or "en").lower()
    for pre, sep in _SEP.items():
        if loc == pre or loc.startswith(pre + "-"):
            return sep
    return _DEFAULT_SEP


def _group(int_str: str, sep: str) -> str:
    neg = int_str.startswith("-")
    digits = int_str[1:] if neg else int_str
    parts = []
    while len(digits) > 3:
        parts.insert(0, digits[-3:])
        digits = digits[:-3]
    parts.insert(0, digits)
    out = sep.join(parts)
    return ("-" + out) if neg else out


def format_number(value: float, locale: Optional[str] = None,
                  decimals: int = 0) -> str:
    """Locale-grouped fixed-decimal number. Never raises; NaN/None → ''."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if v != v:  # NaN
        return ""
    grp, dec = _sep_for(locale)
    neg = v < 0
    v = abs(v)
    q = round(v, decimals)
    int_part = int(q)
    int_str = _group(str(int_part), grp)
    if decimals > 0:
        frac = q - int_part
        frac_str = f"{frac:.{decimals}f}"[2:]
        out = f"{int_str}{dec}{frac_str}"
    else:
        out = int_str
    return ("-" + out) if neg and q != 0 else out


def format_price(value: float, currency: str = "", locale: Optional[str] = None,
                 decimals: Optional[int] = None) -> str:
    """Locale + currency aware price. KRW/JPY/VND default to 0 decimals, others 2.
    Symbol placement follows the currency table (e.g. '₫' trails for VND)."""
    ccy = (currency or "").upper()
    if decimals is None:
        decimals = 0 if ccy in ("KRW", "JPY", "VND") else 2
    num = format_number(value, locale, decimals)
    if not num:
        return ""
    sym, lead = _CCY.get(ccy, ("", True))
    if not sym:
        return num
    return f"{sym} {num}" if lead else f"{num} {sym}"


_COMPACT = [(1_000_000_000_000, "T"), (1_000_000_000, "B"),
            (1_000_000, "M"), (1_000, "K")]


def format_compact(value: float, locale: Optional[str] = None,
                   decimals: int = 1) -> str:
    """Compact magnitude label for volume/market-cap axes, e.g. 14,360K → '14.36M'.
    Suffixes K/M/B/T are uppercase technical notation (kept as-is across locales)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if v != v:
        return ""
    neg = v < 0
    v = abs(v)
    for base, suffix in _COMPACT:
        if v >= base:
            num = format_number(v / base, locale, decimals)
            return ("-" if neg else "") + f"{num}{suffix}"
    return ("-" if neg else "") + format_number(v, locale, 0)
