"""Pure-NumPy fallback kernels with exact mathematical parity to qlib_lab/_accel/kernels.cpp."""
from __future__ import annotations

from collections import deque
import math

import numpy as np


def rolling_moments_np(
    x: np.ndarray,
    window: int,
    min_periods: int,
    mode: int,
) -> np.ndarray:
    """Rolling moments matching kernels.cpp:rolling_moments_f64.

    mode: 0=Mean, 1=Std(ddof=1), 2=Var(ddof=1), 3=Skew, 4=Kurt, 5=Sum.
    """
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0 or window <= 0:
        return out
    if min_periods <= 0:
        min_periods = window

    # Two-stack Pébay-Welford queue in Python for exact numerical parity with kernels.cpp
    def _combine(a, b):
        if a[0] == 0:
            return b
        if b[0] == 0:
            return a
        na, mua, m2a, m3a, m4a = a
        nb, mub, m2b, m3b, m4b = b
        nt = na + nb
        dna, dnb, dnt = float(na), float(nb), float(nt)
        delta = mub - mua
        delta_n = delta / dnt
        delta_n2 = delta_n * delta_n
        term1 = delta * delta_n * dna * dnb
        mean = mua + delta_n * dnb
        m4 = (
            m4a
            + m4b
            + term1 * delta_n2 * (dna * dna - dna * dnb + dnb * dnb)
            + 6.0 * delta_n2 * (dna * dna * m2b + dnb * dnb * m2a)
            + 4.0 * delta_n * (dna * m3b - dnb * m3a)
        )
        m3 = m3a + m3b + term1 * delta_n * (dna - dnb) + 3.0 * delta_n * (dna * m2b - dnb * m2a)
        m2 = m2a + m2b + term1
        return (nt, mean, m2, m3, m4)

    empty = (0, 0.0, 0.0, 0.0, 0.0)
    front_vals: list[tuple] = []
    front_agg: list[tuple] = []
    back_vals: list[tuple] = []
    back_agg: list[tuple] = []

    for i in range(n):
        v = float(arr[i])
        s = (1, v, 0.0, 0.0, 0.0) if math.isfinite(v) else empty
        back_vals.append(s)
        back_agg.append(s if not back_agg else _combine(back_agg[-1], s))
        if len(front_vals) + len(back_vals) > window:
            if not front_vals:
                while back_vals:
                    bs = back_vals.pop()
                    front_vals.append(bs)
                    front_agg.append(bs if not front_agg else _combine(bs, front_agg[-1]))
                back_agg.clear()
            if front_vals:
                front_vals.pop()
                front_agg.pop()

        if not front_agg and not back_agg:
            cnt, mean, m2, m3, m4 = empty
        elif not front_agg:
            cnt, mean, m2, m3, m4 = back_agg[-1]
        elif not back_agg:
            cnt, mean, m2, m3, m4 = front_agg[-1]
        else:
            cnt, mean, m2, m3, m4 = _combine(front_agg[-1], back_agg[-1])

        if cnt < min_periods:
            continue
        if mode == 0:
            out[i] = mean
        elif mode == 5:
            out[i] = mean * float(cnt)
        elif mode == 2:
            if cnt >= 2:
                out[i] = max(0.0, m2 / float(cnt - 1))
        elif mode == 1:
            if cnt >= 2:
                out[i] = math.sqrt(max(0.0, m2 / float(cnt - 1)))
        elif mode == 3:
            if cnt >= 3:
                if m2 <= 1e-30:
                    out[i] = 0.0
                else:
                    dn = float(cnt)
                    out[i] = ((dn * math.sqrt(dn - 1.0)) / (dn - 2.0)) * m3 / (m2 ** 1.5)
        elif mode == 4:
            if cnt >= 4:
                if m2 <= 1e-30:
                    out[i] = 0.0
                else:
                    dn = float(cnt)
                    t1 = (dn * (dn + 1.0)) / ((dn - 1.0) * (dn - 2.0) * (dn - 3.0)) * ((dn - 1.0) ** 2) * m4 / (m2 * m2)
                    t2 = (3.0 * (dn - 1.0) ** 2) / ((dn - 2.0) * (dn - 3.0))
                    out[i] = t1 - t2
    return out


def rolling_extrema_np(
    x: np.ndarray,
    window: int,
    min_periods: int,
    is_max: bool,
) -> np.ndarray:
    """Monotonic-deque rolling Max/Min matching kernels.cpp:rolling_extrema_f64."""
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0 or window <= 0:
        return out
    if min_periods <= 0:
        min_periods = window

    dq: deque[int] = deque()
    valid_count = 0
    for i in range(n):
        if i >= window and math.isfinite(float(arr[i - window])):
            valid_count -= 1
        left_bound = i - window + 1
        while dq and dq[0] < left_bound:
            dq.popleft()
        v = float(arr[i])
        if math.isfinite(v):
            valid_count += 1
            if is_max:
                while dq and arr[dq[-1]] <= v:
                    dq.pop()
            else:
                while dq and arr[dq[-1]] >= v:
                    dq.pop()
            dq.append(i)
        if valid_count >= min_periods and dq:
            out[i] = arr[dq[0]]
    return out


def ema_np(x: np.ndarray, alpha: float, min_periods: int = 1) -> np.ndarray:
    """Causal EMA matching kernels.cpp:ema_f64."""
    arr = np.asarray(x, dtype=np.float64).ravel()
    n = arr.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0:
        return out
    if min_periods <= 0:
        min_periods = 1
    state = 0.0
    seen = 0
    one_m = 1.0 - float(alpha)
    a = float(alpha)
    for i in range(n):
        v = float(arr[i])
        if not math.isfinite(v):
            continue
        state = v if seen == 0 else (a * v + one_m * state)
        seen += 1
        if seen >= min_periods:
            out[i] = state
    return out


def wilder_rsi_np(close: np.ndarray, period: int) -> np.ndarray:
    """Causal Wilder RSI matching kernels.cpp:wilder_rsi_f64."""
    arr = np.asarray(close, dtype=np.float64).ravel()
    n = arr.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 1 or period <= 0:
        return out
    avg_gain = 0.0
    avg_loss = 0.0
    valid_diffs = 0
    dp = float(period)
    eps = 1e-15
    for i in range(1, n):
        cur = float(arr[i])
        prev = float(arr[i - 1])
        if not (math.isfinite(cur) and math.isfinite(prev)):
            continue
        diff = cur - prev
        gain = diff if diff > 0.0 else 0.0
        loss = -diff if diff < 0.0 else 0.0
        valid_diffs += 1
        if valid_diffs < period:
            avg_gain += gain
            avg_loss += loss
        else:
            if valid_diffs == period:
                avg_gain = (avg_gain + gain) / dp
                avg_loss = (avg_loss + loss) / dp
            else:
                avg_gain = ((dp - 1.0) * avg_gain + gain) / dp
                avg_loss = ((dp - 1.0) * avg_loss + loss) / dp
            if avg_loss <= eps and avg_gain <= eps:
                out[i] = 50.0
            elif avg_loss <= eps:
                out[i] = 100.0
            else:
                out[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def wilder_atr_np(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Causal Wilder ATR matching kernels.cpp:wilder_atr_f64."""
    h_arr = np.asarray(high, dtype=np.float64).ravel()
    l_arr = np.asarray(low, dtype=np.float64).ravel()
    c_arr = np.asarray(close, dtype=np.float64).ravel()
    n = c_arr.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0 or period <= 0:
        return out
    atr = 0.0
    valid_tr = 0
    dp = float(period)
    for i in range(n):
        h = float(h_arr[i])
        lo = float(l_arr[i])
        c = float(c_arr[i])
        if not (math.isfinite(h) and math.isfinite(lo) and math.isfinite(c)):
            continue
        tr = h - lo
        if i > 0 and math.isfinite(float(c_arr[i - 1])):
            pc = float(c_arr[i - 1])
            tr = max(tr, abs(h - pc), abs(lo - pc))
        valid_tr += 1
        if valid_tr < period:
            atr += tr
        elif valid_tr == period:
            atr = (atr + tr) / dp
            out[i] = atr
        else:
            atr = ((dp - 1.0) * atr + tr) / dp
            out[i] = atr
    return out


def _sliding_biv_iter(x: np.ndarray, y: np.ndarray, window: int):
    def _combine(a, b):
        if a[0] == 0:
            return b
        if b[0] == 0:
            return a
        na, mxa, mya, m2xa, m2ya, cxya = a
        nb, mxb, myb, m2xb, m2yb, cxyb = b
        nt = na + nb
        dna, dnb, dnt = float(na), float(nb), float(nt)
        dx = mxb - mxa
        dy = myb - mya
        w = (dna * dnb) / dnt
        return (
            nt,
            mxa + dx * (dnb / dnt),
            mya + dy * (dnb / dnt),
            m2xa + m2xb + dx * dx * w,
            m2ya + m2yb + dy * dy * w,
            cxya + cxyb + dx * dy * w,
        )

    empty = (0, 0.0, 0.0, 0.0, 0.0, 0.0)
    front_vals: list[tuple] = []
    front_agg: list[tuple] = []
    back_vals: list[tuple] = []
    back_agg: list[tuple] = []

    for i in range(x.size):
        vx, vy = float(x[i]), float(y[i])
        s = (1, vx, vy, 0.0, 0.0, 0.0) if (math.isfinite(vx) and math.isfinite(vy)) else empty
        back_vals.append(s)
        back_agg.append(s if not back_agg else _combine(back_agg[-1], s))
        if len(front_vals) + len(back_vals) > window:
            if not front_vals:
                while back_vals:
                    bs = back_vals.pop()
                    front_vals.append(bs)
                    front_agg.append(bs if not front_agg else _combine(bs, front_agg[-1]))
                back_agg.clear()
            if front_vals:
                front_vals.pop()
                front_agg.pop()
        if not front_agg and not back_agg:
            yield i, empty
        elif not front_agg:
            yield i, back_agg[-1]
        elif not back_agg:
            yield i, front_agg[-1]
        else:
            yield i, _combine(front_agg[-1], back_agg[-1])


def rolling_biv_np(
    x: np.ndarray,
    y: np.ndarray,
    window: int,
    min_periods: int,
    is_corr: bool,
) -> np.ndarray:
    """Bivariate rolling Cov/Corr matching kernels.cpp:rolling_biv_f64."""
    xa = np.asarray(x, dtype=np.float64).ravel()
    ya = np.asarray(y, dtype=np.float64).ravel()
    n = xa.size
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0 or window <= 0:
        return out
    if min_periods < 2:
        min_periods = max(2, window)

    for i, (cnt, _mx, _my, m2x, m2y, cxy) in _sliding_biv_iter(xa, ya, window):
        if cnt < min_periods or cnt < 2:
            continue
        if is_corr:
            d2 = m2x * m2y
            if d2 > 1e-30:
                out[i] = min(1.0, max(-1.0, cxy / math.sqrt(d2)))
        else:
            out[i] = cxy / float(cnt - 1)
    return out


def rolling_ols_np(
    y: np.ndarray,
    window: int,
    min_periods: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rolling time-trend OLS (Slope, Rsquare, Resi) matching kernels.cpp:rolling_ols_f64."""
    ya = np.asarray(y, dtype=np.float64).ravel()
    n = ya.size
    slope_out = np.full(n, np.nan, dtype=np.float64)
    r2_out = np.full(n, np.nan, dtype=np.float64)
    resi_out = np.full(n, np.nan, dtype=np.float64)
    if n <= 0 or window <= 0:
        return slope_out, r2_out, resi_out
    if min_periods < 2:
        min_periods = max(2, window)

    t_idx = np.arange(n, dtype=np.float64)
    for i, (cnt, mx, my, m2x, m2y, cxy) in _sliding_biv_iter(t_idx, ya, window):
        yi = float(ya[i])
        if cnt < min_periods or cnt < 2 or not math.isfinite(yi) or m2x <= 1e-30:
            continue
        slp = cxy / m2x
        yhat = my + slp * (float(i) - mx)
        slope_out[i] = slp
        resi_out[i] = yi - yhat
        r2_out[i] = min(1.0, max(0.0, (cxy * cxy) / (m2x * m2y))) if m2y > 1e-30 else 0.0
    return slope_out, r2_out, resi_out


def hist_build_np(
    X_binned: np.ndarray,
    grad: np.ndarray,
    hess: np.ndarray,
    sample_idx: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """256-entry uint8 histogram builder matching kernels.cpp:hist_build_f64."""
    n_features = int(X_binned.shape[1])
    G = np.zeros((n_features, 256), dtype=np.float64)
    H = np.zeros((n_features, 256), dtype=np.float64)
    C = np.zeros((n_features, 256), dtype=np.int64)
    if sample_idx.size == 0:
        return G, H, C

    sub_x = X_binned[sample_idx]
    sub_g = grad[sample_idx]
    sub_h = hess[sample_idx]
    for f in range(n_features):
        bins_f = sub_x[:, f]
        G[f] = np.bincount(bins_f, weights=sub_g, minlength=256)
        H[f] = np.bincount(bins_f, weights=sub_h, minlength=256)
        C[f] = np.bincount(bins_f, minlength=256)
    return G, H, C


def hist_subtract_np(
    parent_G: np.ndarray,
    parent_H: np.ndarray,
    parent_count: np.ndarray,
    small_G: np.ndarray,
    small_H: np.ndarray,
    small_count: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parent-minus-smaller-child histogram subtraction matching kernels.cpp:hist_subtract_f64."""
    return (
        np.asarray(parent_G - small_G, dtype=np.float64),
        np.asarray(parent_H - small_H, dtype=np.float64),
        np.asarray(parent_count - small_count, dtype=np.int64),
    )


def hist_best_split_np(
    G: np.ndarray,
    H: np.ndarray,
    count: np.ndarray,
    n_finite_bins: np.ndarray,
    feature_mask: np.ndarray | None,
    min_samples_leaf: int,
    min_child_weight: float,
    reg_lambda: float,
    min_split_gain: float,
) -> tuple[int, int, bool, float]:
    """Best Newton split scan with NaN routing matching kernels.cpp:hist_best_split_f64."""
    n_features = int(G.shape[0])
    best_f = -1
    best_b = -1
    best_nan_left = True
    best_gain = 0.0

    for f in range(n_features):
        if feature_mask is not None and int(feature_mask[f]) == 0:
            continue
        nb = int(n_finite_bins[f])
        if nb <= 1:
            continue

        gf = G[f, :nb]
        hf = H[f, :nb]
        cf = count[f, :nb]

        g_nan = float(G[f, 255])
        h_nan = float(H[f, 255])
        c_nan = int(count[f, 255])

        g_tot = float(gf.sum()) + g_nan
        h_tot = float(hf.sum()) + h_nan
        c_tot = int(cf.sum()) + c_nan
        if c_tot < 2 * min_samples_leaf:
            continue

        parent_score = (g_tot * g_tot) / (h_tot + reg_lambda)
        g_pref_arr = np.cumsum(gf)[:-1]
        h_pref_arr = np.cumsum(hf)[:-1]
        c_pref_arr = np.cumsum(cf)[:-1]

        for b in range(nb - 1):
            g_pref = float(g_pref_arr[b])
            h_pref = float(h_pref_arr[b])
            c_pref = int(c_pref_arr[b])

            for nan_left in (1, 0):
                if c_nan == 0 and nan_left == 0:
                    continue
                gl = g_pref + (g_nan if nan_left else 0.0)
                hl = h_pref + (h_nan if nan_left else 0.0)
                cl = c_pref + (c_nan if nan_left else 0)

                gr = g_tot - gl
                hr = h_tot - hl
                cr = c_tot - cl

                if cl < min_samples_leaf or cr < min_samples_leaf:
                    continue
                if hl < min_child_weight or hr < min_child_weight:
                    continue

                gain = 0.5 * (
                    (gl * gl) / (hl + reg_lambda)
                    + (gr * gr) / (hr + reg_lambda)
                    - parent_score
                ) - min_split_gain

                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_f = f
                    best_b = b
                    best_nan_left = bool(nan_left)

    return best_f, best_b, best_nan_left, best_gain
