// Deterministic C++17 native acceleration kernels for qlib_lab.
// Compiled with: g++ -std=c++17 -O3 -fno-fast-math -shared -fPIC
// Strictly IEEE-754 compliant (-fno-fast-math), causal, NaN-safe, zero global mutable state.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>

namespace {

constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr double kEps = 1e-15;

// Pébay (2008) / Terriberry (2007) parallel Welford moment tuple up to 4th central moment.
// Using two-stack sliding window queue guarantees O(T) time (independent of window W)
// with ZERO subtraction cancellation or floating-point drift.
struct MomentState {
    int64_t n = 0;
    double mean = 0.0;
    double m2 = 0.0;
    double m3 = 0.0;
    double m4 = 0.0;

    static MomentState singleton(double x) noexcept {
        if (!std::isfinite(x)) {
            return MomentState{};
        }
        return MomentState{1, x, 0.0, 0.0, 0.0};
    }

    static MomentState combine(const MomentState& a, const MomentState& b) noexcept {
        if (a.n == 0) return b;
        if (b.n == 0) return a;
        const int64_t n = a.n + b.n;
        const double na = static_cast<double>(a.n);
        const double nb = static_cast<double>(b.n);
        const double dn = static_cast<double>(n);
        const double delta = b.mean - a.mean;
        const double delta_n = delta / dn;
        const double delta_n2 = delta_n * delta_n;
        const double term1 = delta * delta_n * na * nb;

        MomentState out;
        out.n = n;
        out.mean = a.mean + delta_n * nb;
        out.m4 = a.m4 + b.m4
               + term1 * delta_n2 * (na * na - na * nb + nb * nb)
               + 6.0 * delta_n2 * (na * na * b.m2 + nb * nb * a.m2)
               + 4.0 * delta_n * (na * b.m3 - nb * a.m3);
        out.m3 = a.m3 + b.m3
               + term1 * delta_n * (na - nb)
               + 3.0 * delta_n * (na * b.m2 - nb * a.m2);
        out.m2 = a.m2 + b.m2 + term1;
        return out;
    }
};

class SlidingMomentQueue {
public:
    explicit SlidingMomentQueue(int64_t cap) {
        front_vals_.reserve(static_cast<size_t>(cap) + 2);
        front_agg_.reserve(static_cast<size_t>(cap) + 2);
        back_vals_.reserve(static_cast<size_t>(cap) + 2);
        back_agg_.reserve(static_cast<size_t>(cap) + 2);
    }

    void push(const MomentState& s) {
        back_vals_.push_back(s);
        if (back_agg_.empty()) {
            back_agg_.push_back(s);
        } else {
            back_agg_.push_back(MomentState::combine(back_agg_.back(), s));
        }
    }

    void pop() {
        if (front_vals_.empty()) {
            while (!back_vals_.empty()) {
                MomentState s = back_vals_.back();
                back_vals_.pop_back();
                front_vals_.push_back(s);
                if (front_agg_.empty()) {
                    front_agg_.push_back(s);
                } else {
                    front_agg_.push_back(MomentState::combine(s, front_agg_.back()));
                }
            }
            back_agg_.clear();
        }
        if (!front_vals_.empty()) {
            front_vals_.pop_back();
            front_agg_.pop_back();
        }
    }

    int64_t size() const noexcept {
        return static_cast<int64_t>(front_vals_.size() + back_vals_.size());
    }

    MomentState query() const noexcept {
        if (front_agg_.empty() && back_agg_.empty()) return MomentState{};
        if (front_agg_.empty()) return back_agg_.back();
        if (back_agg_.empty()) return front_agg_.back();
        return MomentState::combine(front_agg_.back(), back_agg_.back());
    }

private:
    std::vector<MomentState> front_vals_;
    std::vector<MomentState> front_agg_;
    std::vector<MomentState> back_vals_;
    std::vector<MomentState> back_agg_;
};

// Bivariate Pébay co-moment state for O(T) rolling Cov, Corr, Slope, Rsquare, Resi.
struct BivMomentState {
    int64_t n = 0;
    double mx = 0.0;
    double my = 0.0;
    double m2x = 0.0;
    double m2y = 0.0;
    double cxy = 0.0;

    static BivMomentState singleton(double x, double y) noexcept {
        if (!std::isfinite(x) || !std::isfinite(y)) {
            return BivMomentState{};
        }
        return BivMomentState{1, x, y, 0.0, 0.0, 0.0};
    }

    static BivMomentState combine(const BivMomentState& a, const BivMomentState& b) noexcept {
        if (a.n == 0) return b;
        if (b.n == 0) return a;
        const int64_t n = a.n + b.n;
        const double na = static_cast<double>(a.n);
        const double nb = static_cast<double>(b.n);
        const double dn = static_cast<double>(n);
        const double dx = b.mx - a.mx;
        const double dy = b.my - a.my;
        const double w = (na * nb) / dn;

        BivMomentState out;
        out.n = n;
        out.mx = a.mx + dx * (nb / dn);
        out.my = a.my + dy * (nb / dn);
        out.m2x = a.m2x + b.m2x + dx * dx * w;
        out.m2y = a.m2y + b.m2y + dy * dy * w;
        out.cxy = a.cxy + b.cxy + dx * dy * w;
        return out;
    }
};

class SlidingBivQueue {
public:
    explicit SlidingBivQueue(int64_t cap) {
        front_vals_.reserve(static_cast<size_t>(cap) + 2);
        front_agg_.reserve(static_cast<size_t>(cap) + 2);
        back_vals_.reserve(static_cast<size_t>(cap) + 2);
        back_agg_.reserve(static_cast<size_t>(cap) + 2);
    }

    void push(const BivMomentState& s) {
        back_vals_.push_back(s);
        if (back_agg_.empty()) {
            back_agg_.push_back(s);
        } else {
            back_agg_.push_back(BivMomentState::combine(back_agg_.back(), s));
        }
    }

    void pop() {
        if (front_vals_.empty()) {
            while (!back_vals_.empty()) {
                BivMomentState s = back_vals_.back();
                back_vals_.pop_back();
                front_vals_.push_back(s);
                if (front_agg_.empty()) {
                    front_agg_.push_back(s);
                } else {
                    front_agg_.push_back(BivMomentState::combine(s, front_agg_.back()));
                }
            }
            back_agg_.clear();
        }
        if (!front_vals_.empty()) {
            front_vals_.pop_back();
            front_agg_.pop_back();
        }
    }

    int64_t size() const noexcept {
        return static_cast<int64_t>(front_vals_.size() + back_vals_.size());
    }

    BivMomentState query() const noexcept {
        if (front_agg_.empty() && back_agg_.empty()) return BivMomentState{};
        if (front_agg_.empty()) return back_agg_.back();
        if (back_agg_.empty()) return front_agg_.back();
        return BivMomentState::combine(front_agg_.back(), back_agg_.back());
    }

private:
    std::vector<BivMomentState> front_vals_;
    std::vector<BivMomentState> front_agg_;
    std::vector<BivMomentState> back_vals_;
    std::vector<BivMomentState> back_agg_;
};

}  // namespace

extern "C" {

// 1. O(T) Welford rolling moments: mode 0=Mean, 1=Std(ddof=1), 2=Var(ddof=1), 3=Skew, 4=Kurt, 5=Sum
void rolling_moments_f64(
    const double* x,
    int64_t n,
    int64_t window,
    int64_t min_periods,
    int32_t mode,
    double* out
) {
    if (n <= 0 || window <= 0) return;
    if (min_periods <= 0) min_periods = window;
    SlidingMomentQueue q(window);

    for (int64_t i = 0; i < n; ++i) {
        q.push(MomentState::singleton(x[i]));
        if (q.size() > window) {
            q.pop();
        }
        const MomentState s = q.query();
        if (s.n < min_periods) {
            out[i] = kNaN;
            continue;
        }
        if (mode == 0) {
            out[i] = s.mean;
        } else if (mode == 5) {
            out[i] = s.mean * static_cast<double>(s.n);
        } else if (mode == 2) {
            if (s.n < 2) {
                out[i] = kNaN;
            } else {
                out[i] = std::max(0.0, s.m2 / static_cast<double>(s.n - 1));
            }
        } else if (mode == 1) {
            if (s.n < 2) {
                out[i] = kNaN;
            } else {
                out[i] = std::sqrt(std::max(0.0, s.m2 / static_cast<double>(s.n - 1)));
            }
        } else if (mode == 3) {
            if (s.n < 3) {
                out[i] = kNaN;
            } else if (s.m2 <= 1e-30) {
                out[i] = 0.0;
            } else {
                const double dn = static_cast<double>(s.n);
                const double scale = (dn * std::sqrt(dn - 1.0)) / (dn - 2.0);
                out[i] = scale * s.m3 / std::pow(s.m2, 1.5);
            }
        } else if (mode == 4) {
            if (s.n < 4) {
                out[i] = kNaN;
            } else if (s.m2 <= 1e-30) {
                out[i] = 0.0;
            } else {
                const double dn = static_cast<double>(s.n);
                const double term1 = (dn * (dn + 1.0)) / ((dn - 1.0) * (dn - 2.0) * (dn - 3.0))
                                   * (dn - 1.0) * (dn - 1.0) * s.m4 / (s.m2 * s.m2);
                const double term2 = (3.0 * (dn - 1.0) * (dn - 1.0)) / ((dn - 2.0) * (dn - 3.0));
                out[i] = term1 - term2;
            }
        } else {
            out[i] = kNaN;
        }
    }
}

// 2. O(T) Monotonic-deque rolling Max / Min (is_max = 1 for Max, 0 for Min)
void rolling_extrema_f64(
    const double* x,
    int64_t n,
    int64_t window,
    int64_t min_periods,
    int32_t is_max,
    double* out
) {
    if (n <= 0 || window <= 0) return;
    if (min_periods <= 0) min_periods = window;

    std::vector<int64_t> dq(static_cast<size_t>(n));
    int64_t head = 0;
    int64_t tail = 0;
    int64_t valid_count = 0;

    for (int64_t i = 0; i < n; ++i) {
        if (i >= window && std::isfinite(x[i - window])) {
            --valid_count;
        }
        const int64_t left_bound = i - window + 1;
        while (head < tail && dq[static_cast<size_t>(head)] < left_bound) {
            ++head;
        }
        const double v = x[i];
        if (std::isfinite(v)) {
            ++valid_count;
            if (is_max != 0) {
                while (head < tail && x[dq[static_cast<size_t>(tail - 1)]] <= v) {
                    --tail;
                }
            } else {
                while (head < tail && x[dq[static_cast<size_t>(tail - 1)]] >= v) {
                    --tail;
                }
            }
            dq[static_cast<size_t>(tail++)] = i;
        }
        if (valid_count < min_periods || head == tail) {
            out[i] = kNaN;
        } else {
            out[i] = x[dq[static_cast<size_t>(head)]];
        }
    }
}

// 3. Causal EMA: alpha = 2 / (span + 1) passed directly by caller
void ema_f64(
    const double* x,
    int64_t n,
    double alpha,
    int64_t min_periods,
    double* out
) {
    if (n <= 0) return;
    if (min_periods <= 0) min_periods = 1;
    double state = 0.0;
    int64_t seen = 0;
    for (int64_t i = 0; i < n; ++i) {
        const double v = x[i];
        if (!std::isfinite(v)) {
            out[i] = kNaN;
            continue;
        }
        if (seen == 0) {
            state = v;
        } else {
            state = alpha * v + (1.0 - alpha) * state;
        }
        ++seen;
        out[i] = (seen >= min_periods) ? state : kNaN;
    }
}

// 4. Causal Wilder RSI
void wilder_rsi_f64(
    const double* close,
    int64_t n,
    int64_t period,
    double* out
) {
    if (n <= 0) return;
    if (period <= 0) {
        for (int64_t i = 0; i < n; ++i) out[i] = kNaN;
        return;
    }
    out[0] = kNaN;
    double avg_gain = 0.0;
    double avg_loss = 0.0;
    int64_t valid_diffs = 0;
    const double dp = static_cast<double>(period);

    for (int64_t i = 1; i < n; ++i) {
        const double cur = close[i];
        const double prev = close[i - 1];
        if (!std::isfinite(cur) || !std::isfinite(prev)) {
            out[i] = kNaN;
            continue;
        }
        const double diff = cur - prev;
        const double gain = diff > 0.0 ? diff : 0.0;
        const double loss = diff < 0.0 ? -diff : 0.0;
        ++valid_diffs;

        if (valid_diffs < period) {
            avg_gain += gain;
            avg_loss += loss;
            out[i] = kNaN;
        } else if (valid_diffs == period) {
            avg_gain = (avg_gain + gain) / dp;
            avg_loss = (avg_loss + loss) / dp;
            if (avg_loss <= kEps && avg_gain <= kEps) {
                out[i] = 50.0;
            } else if (avg_loss <= kEps) {
                out[i] = 100.0;
            } else {
                out[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss));
            }
        } else {
            avg_gain = ((dp - 1.0) * avg_gain + gain) / dp;
            avg_loss = ((dp - 1.0) * avg_loss + loss) / dp;
            if (avg_loss <= kEps && avg_gain <= kEps) {
                out[i] = 50.0;
            } else if (avg_loss <= kEps) {
                out[i] = 100.0;
            } else {
                out[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss));
            }
        }
    }
}

// 5. Causal Wilder ATR
void wilder_atr_f64(
    const double* high,
    const double* low,
    const double* close,
    int64_t n,
    int64_t period,
    double* out
) {
    if (n <= 0) return;
    if (period <= 0) {
        for (int64_t i = 0; i < n; ++i) out[i] = kNaN;
        return;
    }
    double atr = 0.0;
    int64_t valid_tr = 0;
    const double dp = static_cast<double>(period);

    for (int64_t i = 0; i < n; ++i) {
        const double h = high[i];
        const double l = low[i];
        const double c = close[i];
        if (!std::isfinite(h) || !std::isfinite(l) || !std::isfinite(c)) {
            out[i] = kNaN;
            continue;
        }
        double tr = h - l;
        if (i > 0 && std::isfinite(close[i - 1])) {
            const double pc = close[i - 1];
            tr = std::max({tr, std::abs(h - pc), std::abs(l - pc)});
        }
        ++valid_tr;
        if (valid_tr < period) {
            atr += tr;
            out[i] = kNaN;
        } else if (valid_tr == period) {
            atr = (atr + tr) / dp;
            out[i] = atr;
        } else {
            atr = ((dp - 1.0) * atr + tr) / dp;
            out[i] = atr;
        }
    }
}

// 6. O(T) Bivariate rolling Cov / Corr (is_corr = 1 for Corr, 0 for Cov)
void rolling_biv_f64(
    const double* x,
    const double* y,
    int64_t n,
    int64_t window,
    int64_t min_periods,
    int32_t is_corr,
    double* out
) {
    if (n <= 0 || window <= 0) return;
    if (min_periods < 2) min_periods = std::max<int64_t>(2, window);
    SlidingBivQueue q(window);

    for (int64_t i = 0; i < n; ++i) {
        q.push(BivMomentState::singleton(x[i], y[i]));
        if (q.size() > window) {
            q.pop();
        }
        const BivMomentState s = q.query();
        if (s.n < min_periods || s.n < 2) {
            out[i] = kNaN;
            continue;
        }
        if (is_corr != 0) {
            const double denom2 = s.m2x * s.m2y;
            if (denom2 <= 1e-30) {
                out[i] = kNaN;
            } else {
                const double r = s.cxy / std::sqrt(denom2);
                out[i] = std::clamp(r, -1.0, 1.0);
            }
        } else {
            out[i] = s.cxy / static_cast<double>(s.n - 1);
        }
    }
}

// 7. O(T) Rolling Time-Trend OLS: Slope, Rsquare, Resi
void rolling_ols_f64(
    const double* y,
    int64_t n,
    int64_t window,
    int64_t min_periods,
    double* out_slope,
    double* out_r2,
    double* out_resi
) {
    if (n <= 0 || window <= 0) return;
    if (min_periods < 2) min_periods = std::max<int64_t>(2, window);
    SlidingBivQueue q(window);

    for (int64_t i = 0; i < n; ++i) {
        const double ti = static_cast<double>(i);
        const double yi = y[i];
        q.push(BivMomentState::singleton(ti, yi));
        if (q.size() > window) {
            q.pop();
        }
        const BivMomentState s = q.query();
        if (s.n < min_periods || s.n < 2 || !std::isfinite(yi) || s.m2x <= 1e-30) {
            if (out_slope) out_slope[i] = kNaN;
            if (out_r2) out_r2[i] = kNaN;
            if (out_resi) out_resi[i] = kNaN;
            continue;
        }
        const double slope = s.cxy / s.m2x;
        const double yhat = s.my + slope * (ti - s.mx);
        const double resi = yi - yhat;
        double r2 = 0.0;
        if (s.m2y > 1e-30) {
            r2 = std::clamp((s.cxy * s.cxy) / (s.m2x * s.m2y), 0.0, 1.0);
        }
        if (out_slope) out_slope[i] = slope;
        if (out_r2) out_r2[i] = r2;
        if (out_resi) out_resi[i] = resi;
    }
}

// 8. Fast uint8 255-bin (+ bin 255 = NaN) HistGBDT histogram builder
void hist_build_f64(
    const uint8_t* X_binned,     // (n_total_samples, n_features) row-major
    const double* grad,          // (n_total_samples,)
    const double* hess,          // (n_total_samples,)
    const int32_t* sample_idx,   // (n_node_samples,)
    int64_t n_total_samples,
    int64_t n_node_samples,
    int64_t n_features,
    double* out_G,               // (n_features, 256)
    double* out_H,               // (n_features, 256)
    int64_t* out_count           // (n_features, 256)
) {
    if (n_features <= 0 || n_node_samples < 0) return;
    const int64_t total_bins = n_features * 256;
    std::fill(out_G, out_G + total_bins, 0.0);
    std::fill(out_H, out_H + total_bins, 0.0);
    std::fill(out_count, out_count + total_bins, int64_t{0});

    for (int64_t s = 0; s < n_node_samples; ++s) {
        const int64_t row = static_cast<int64_t>(sample_idx[s]);
        if (row < 0 || row >= n_total_samples) continue;
        const double g = grad[row];
        const double h = hess[row];
        const uint8_t* x_row = X_binned + row * n_features;
        int64_t f = 0;
        for (; f + 3 < n_features; f += 4) {
            const int64_t b0 = (f + 0) * 256 + static_cast<int64_t>(x_row[f + 0]);
            const int64_t b1 = (f + 1) * 256 + static_cast<int64_t>(x_row[f + 1]);
            const int64_t b2 = (f + 2) * 256 + static_cast<int64_t>(x_row[f + 2]);
            const int64_t b3 = (f + 3) * 256 + static_cast<int64_t>(x_row[f + 3]);
            out_G[b0] += g; out_H[b0] += h; out_count[b0] += 1;
            out_G[b1] += g; out_H[b1] += h; out_count[b1] += 1;
            out_G[b2] += g; out_H[b2] += h; out_count[b2] += 1;
            out_G[b3] += g; out_H[b3] += h; out_count[b3] += 1;
        }
        for (; f < n_features; ++f) {
            const int64_t b = f * 256 + static_cast<int64_t>(x_row[f]);
            out_G[b] += g;
            out_H[b] += h;
            out_count[b] += 1;
        }
    }
}

// 9. Parent-minus-smaller-child histogram subtraction in O(F * 256)
void hist_subtract_f64(
    const double* parent_G,
    const double* parent_H,
    const int64_t* parent_count,
    const double* small_G,
    const double* small_H,
    const int64_t* small_count,
    int64_t n_features,
    double* large_G,
    double* large_H,
    int64_t* large_count
) {
    const int64_t total_bins = n_features * 256;
    for (int64_t i = 0; i < total_bins; ++i) {
        large_G[i] = parent_G[i] - small_G[i];
        large_H[i] = parent_H[i] - small_H[i];
        large_count[i] = parent_count[i] - small_count[i];
    }
}

// 10. Best split finder across all features, 255 finite bins, and both NaN routing directions
void hist_best_split_f64(
    const double* G,                 // (n_features, 256)
    const double* H,                 // (n_features, 256)
    const int64_t* count,            // (n_features, 256)
    const int32_t* n_finite_bins,    // (n_features,) number of active finite bins <= 255
    const uint8_t* feature_mask,     // (n_features,) 1 if feature allowed, 0 if masked out
    int64_t n_features,
    int64_t min_samples_leaf,
    double min_child_weight,
    double reg_lambda,
    double min_split_gain,
    int32_t* out_best_feature,
    int32_t* out_best_bin,
    int32_t* out_nan_go_left,
    double* out_best_gain
) {
    int32_t best_f = -1;
    int32_t best_b = -1;
    int32_t best_nan_left = 1;
    double best_gain = 0.0;

    for (int64_t f = 0; f < n_features; ++f) {
        if (feature_mask != nullptr && feature_mask[f] == 0) continue;
        const int32_t nb = n_finite_bins[f];
        if (nb <= 1) continue;

        const double* gf = G + f * 256;
        const double* hf = H + f * 256;
        const int64_t* cf = count + f * 256;

        double g_fin = 0.0;
        double h_fin = 0.0;
        int64_t c_fin = 0;
        for (int32_t b = 0; b < nb; ++b) {
            g_fin += gf[b];
            h_fin += hf[b];
            c_fin += cf[b];
        }
        const double g_nan = gf[255];
        const double h_nan = hf[255];
        const int64_t c_nan = cf[255];

        const double g_tot = g_fin + g_nan;
        const double h_tot = h_fin + h_nan;
        const int64_t c_tot = c_fin + c_nan;
        if (c_tot < 2 * min_samples_leaf) continue;

        const double parent_score = (g_tot * g_tot) / (h_tot + reg_lambda);

        double g_pref = 0.0;
        double h_pref = 0.0;
        int64_t c_pref = 0;

        for (int32_t b = 0; b < nb - 1; ++b) {
            g_pref += gf[b];
            h_pref += hf[b];
            c_pref += cf[b];

            // Direction 0: NaN goes right; Direction 1: NaN goes left
            // Evaluate nan_left = 1 first as deterministic tie-breaker when c_nan == 0
            for (int32_t nan_left = 1; nan_left >= 0; --nan_left) {
                if (c_nan == 0 && nan_left == 0) continue;
                const double gl = g_pref + (nan_left ? g_nan : 0.0);
                const double hl = h_pref + (nan_left ? h_nan : 0.0);
                const int64_t cl = c_pref + (nan_left ? c_nan : 0);

                const double gr = g_tot - gl;
                const double hr = h_tot - hl;
                const int64_t cr = c_tot - cl;

                if (cl < min_samples_leaf || cr < min_samples_leaf) continue;
                if (hl < min_child_weight || hr < min_child_weight) continue;

                const double gain = 0.5 * (
                    (gl * gl) / (hl + reg_lambda) +
                    (gr * gr) / (hr + reg_lambda) -
                    parent_score
                ) - min_split_gain;

                if (gain > best_gain + 1e-12) {
                    best_gain = gain;
                    best_f = static_cast<int32_t>(f);
                    best_b = b;
                    best_nan_left = nan_left;
                }
            }
        }
    }

    *out_best_feature = best_f;
    *out_best_bin = best_b;
    *out_nan_go_left = best_nan_left;
    *out_best_gain = best_gain;
}

}  // extern "C"
