"""Shared vocabulary for the FICC core: the error type, tenor parsing, and the
handful of constants every module needs. Deliberately tiny."""
from __future__ import annotations

import re

TRADING_DAYS = 252
BP = 1e-4                                 # one basis point as a decimal rate

# The standard key-rate grid (years). Curves are bumped and KRDs reported here.
KEY_TENORS: tuple[float, ...] = (0.25, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)

# US Treasury constant-maturity grid, in the order FRED publishes it.
UST_TENORS: tuple[float, ...] = (1 / 12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0,
                                 10.0, 20.0, 30.0)


class FICCError(RuntimeError):
    """A provider or a pricer was asked and could not answer; the message says why."""


_TENOR_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([dwmy])\s*$", re.I)


def parse_tenor(text: str | float | int) -> float:
    """'3m' -> 0.25, '10y' -> 10.0, '2w' -> 2/52, '90d' -> 90/365. Numbers pass
    through as years. Raises FICCError on anything else."""
    if isinstance(text, (int, float)):
        if text <= 0:
            raise FICCError(f"Tenor must be positive, got {text}.")
        return float(text)
    m = _TENOR_RE.match(str(text))
    if not m:
        raise FICCError(f"Cannot read tenor {text!r}; use forms like 3m, 2y, 10y.")
    n, unit = float(m.group(1)), m.group(2).lower()
    years = {"d": n / 365.0, "w": n / 52.0, "m": n / 12.0, "y": n}[unit]
    if years <= 0:
        raise FICCError(f"Tenor must be positive, got {text!r}.")
    return years


def parse_forward_tenor(text: str) -> tuple[float, float]:
    """'5y5y' -> (5.0, 5.0): expiry/start then underlying length. '1y1y', '3m2y'."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?[dwmy])\s*(\d+(?:\.\d+)?[dwmy])\s*$", str(text), re.I)
    if not m:
        raise FICCError(f"Cannot read forward tenor {text!r}; use forms like 5y5y or 3m2y.")
    return parse_tenor(m.group(1)), parse_tenor(m.group(2))


def tenor_label(years: float) -> str:
    """0.25 -> '3m', 1/12 -> '1m', 2.0 -> '2y', 0.5 -> '6m'."""
    if years < 1.0:
        months = years * 12.0
        if abs(months - round(months)) < 1e-6:
            return f"{int(round(months))}m"
        weeks = years * 52.0
        if abs(weeks - round(weeks)) < 1e-6:
            return f"{int(round(weeks))}w"
        return f"{int(round(years * 365))}d"
    if abs(years - round(years)) < 1e-9:
        return f"{int(round(years))}y"
    return f"{years:g}y"


def bp_text(x: float, *, signed: bool = True) -> str:
    """Decimal -> basis-point text: 0.0025 -> '+25.0bp'."""
    return f"{x / BP:{'+' if signed else ''}.1f}bp"


def pct_text(x: float, *, decimals: int = 2, signed: bool = False) -> str:
    return f"{x * 100:{'+' if signed else ''}.{decimals}f}%"
