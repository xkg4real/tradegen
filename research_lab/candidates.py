"""Frozen economic rule families; every signal uses its present/past prices only.

These 2,676 configurations are parameter variants of eight hypotheses, not
2,676 independent economic discoveries. No order or account interface exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json

import numpy as np
import pandas as pd

LOOKBACKS = (5, 10, 20, 40, 60, 90, 120, 180, 250)
REBALANCE = (1, 5, 21)
CAPS = (0.5, 1.0)
VOL_TARGETS = (None, 0.15)


@dataclass(frozen=True)
class RawRule:
    family: str
    parameters: tuple[tuple[str, float | int], ...]

    def mapping(self):
        return dict(self.parameters)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    raw_index: int
    family: str
    parameters: tuple[tuple[str, float | int], ...]
    rebalance_bars: int
    target_cap: float
    volatility_target: float | None

    def mapping(self):
        return asdict(self)


def raw_rules() -> tuple[RawRule, ...]:
    rows = []

    def add(family, **params):
        rows.append(RawRule(family, tuple(sorted(params.items()))))

    for lookback, threshold in itertools.product(LOOKBACKS, (0.0, 0.01, 0.03)):
        add("tsmom", lookback=lookback, threshold=threshold)
    for lookback, band in itertools.product(LOOKBACKS, (0.0, 0.005, 0.01)):
        add("sma", lookback=lookback, band=band)
    for fast, slow, band in itertools.product((5, 10, 20, 40), (60, 90, 120, 180, 250), (0.0, 0.005)):
        add("crossover", fast=fast, slow=slow, band=band)
    for entry, exit_ in itertools.product((10, 20, 40, 60, 90, 120), (5, 10, 20)):
        if exit_ < entry:
            add("donchian", entry=entry, exit=exit_)
    for lookback, entry, exit_ in itertools.product((10, 20, 40, 60, 90), (1.0, 1.5, 2.0), (0.0, 0.5)):
        add("zscore_reversion", lookback=lookback, entry=entry, exit=exit_)
    for lookback, lower, upper in itertools.product((5, 10, 14, 20, 30), (20, 30, 40), (50, 60)):
        add("rsi_reversion", lookback=lookback, lower=lower, upper=upper)
    for vol_window, momentum, quantile in itertools.product((20, 60, 120), (20, 60, 120), (0.3, 0.5, 0.7)):
        add("lowvol_trend", vol_window=vol_window, momentum=momentum, quantile=quantile)
    for lookback, depth, exit_fraction in itertools.product((60, 120, 250), (0.05, 0.1, 0.2), (0.25, 0.5, 0.75)):
        add("drawdown_reversion", lookback=lookback, depth=depth, exit_fraction=exit_fraction)
    if len(rows) != 223:
        raise AssertionError("frozen raw rule catalogue changed")
    return tuple(rows)


def catalogue() -> tuple[Candidate, ...]:
    rows = []
    for raw_index, raw in enumerate(raw_rules()):
        for rebalance, cap, vol in itertools.product(REBALANCE, CAPS, VOL_TARGETS):
            fields = dict(raw_index=raw_index, family=raw.family, parameters=raw.parameters,
                          rebalance_bars=rebalance, target_cap=cap, volatility_target=vol)
            digest = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"),
                                               allow_nan=False).encode()).hexdigest()[:16]
            rows.append(Candidate(f"{raw.family}-{digest}", **fields))
    if len(rows) != 2676 or len({row.candidate_id for row in rows}) != len(rows):
        raise AssertionError("frozen configuration catalogue changed")
    return tuple(rows)


def catalogue_bytes() -> bytes:
    return (json.dumps([row.mapping() for row in catalogue()], sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _state(enter, exit_, valid):
    out = np.zeros(len(enter), dtype=np.bool_)
    held = False
    for index in range(len(out)):
        if not valid[index]:
            held = False
        elif held:
            if exit_[index]:
                held = False
        elif enter[index]:
            held = True
        out[index] = held
    return out


def signal_matrix(close) -> np.ndarray:
    """Return date × 223 binary signals, including the untouched warm-up rows."""
    price = np.asarray(close, dtype=np.float64)
    if price.ndim != 1 or len(price) < 2 or not np.isfinite(price).all() or np.any(price <= 0):
        raise ValueError("finite positive one-dimensional prices required")
    series = pd.Series(price)
    logprice = np.log(series)
    logret = logprice.diff()
    changes = series.diff()
    cache = {}

    def cached(key, builder):
        if key not in cache:
            cache[key] = np.asarray(builder(), dtype=np.float64)
        return cache[key]

    def mean(window):
        return cached(("mean", window), lambda: series.rolling(window, min_periods=window).mean())

    def mom(window):
        return cached(("mom", window), lambda: series / series.shift(window) - 1.0)

    def vol(window):
        return cached(("vol", window), lambda: logret.rolling(window, min_periods=window).std(ddof=1))

    result = np.zeros((len(price), len(raw_rules())), dtype=np.bool_)
    for index, rule in enumerate(raw_rules()):
        p = rule.mapping()
        family = rule.family
        if family == "tsmom":
            value = mom(p["lookback"])
            signal = np.isfinite(value) & (value > p["threshold"])
        elif family == "sma":
            value = price / mean(p["lookback"]) - 1.0
            signal = np.isfinite(value) & (value > p["band"])
        elif family == "crossover":
            value = mean(p["fast"]) / mean(p["slow"]) - 1.0
            signal = np.isfinite(value) & (value > p["band"])
        elif family == "donchian":
            upper = cached(("prior_max", p["entry"]), lambda: series.shift(1).rolling(p["entry"]).max())
            lower = cached(("prior_min", p["exit"]), lambda: series.shift(1).rolling(p["exit"]).min())
            signal = _state(price > upper, price < lower, np.isfinite(upper) & np.isfinite(lower))
        elif family == "zscore_reversion":
            window = p["lookback"]
            center = cached(("logmean", window), lambda: logprice.rolling(window).mean())
            sigma = cached(("logsd", window), lambda: logprice.rolling(window).std(ddof=1))
            z = np.divide(np.log(price) - center, sigma, out=np.full(len(price), np.nan), where=sigma > 0)
            signal = _state(z < -p["entry"], z > -p["exit"], np.isfinite(z))
        elif family == "rsi_reversion":
            window = p["lookback"]
            gains = cached(("gain", window), lambda: changes.clip(lower=0).rolling(window).mean())
            losses = cached(("loss", window), lambda: (-changes.clip(upper=0)).rolling(window).mean())
            ratio = np.divide(gains, losses, out=np.full(len(price), np.inf), where=losses > 0)
            value = np.where((gains == 0) & (losses == 0), 50.0, 100.0 - 100.0 / (1.0 + ratio))
            signal = _state(value < p["lower"], value > p["upper"], np.isfinite(gains) & np.isfinite(losses))
        elif family == "lowvol_trend":
            current_vol = vol(p["vol_window"])
            limit = cached(("vol_quantile", p["vol_window"], p["quantile"]),
                           lambda: pd.Series(current_vol).shift(1).rolling(252, min_periods=252).quantile(p["quantile"]))
            momentum = mom(p["momentum"])
            signal = (np.isfinite(limit) & np.isfinite(current_vol) & np.isfinite(momentum)
                      & (current_vol <= limit) & (momentum > 0))
        elif family == "drawdown_reversion":
            peak = cached(("peak", p["lookback"]), lambda: series.rolling(p["lookback"]).max())
            dd = price / peak - 1.0
            signal = _state(dd < -p["depth"], dd > -p["depth"] * p["exit_fraction"], np.isfinite(dd))
        else:
            raise ValueError("unknown frozen family")
        result[:, index] = signal
    return result


def annual_volatility(close, annualization: int) -> np.ndarray:
    if annualization not in (252, 365):
        raise ValueError("declared trading calendar required")
    values = pd.Series(np.asarray(close, dtype=np.float64))
    return np.asarray(np.log(values).diff().rolling(20, min_periods=20).std(ddof=1) * np.sqrt(annualization))
