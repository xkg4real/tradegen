#include "tg_abi.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <utility>
#include <vector>

namespace {

inline bool kappa_scalar(
    double p,
    int32_t book_kind,
    int32_t n_ladder_rows,
    const double* ladder_starts,
    const double* ladder_steps,
    double table_bp,
    double commission_bp,
    double quote_krw,
    double mult,
    double sell_tax_bp,
    double* out_kappa
) noexcept {
    if (!(std::isfinite(p) && p > 0.0)) {
        return false;
    }
    double q = p / quote_krw;
    double bp = table_bp;
    if (book_kind == TG_BOOK_KRX_ETF || n_ladder_rows > 0) {
        /* Last row with ladder_starts[idx] <= q (matches np.searchsorted(starts, q, side="right") - 1) */
        int32_t idx = -1;
        for (int32_t r = 0; r < n_ladder_rows; ++r) {
            if (ladder_starts[r] <= q) {
                idx = r;
            } else {
                break;
            }
        }
        if (idx < 0) {
            return false;
        }
        double tick = ladder_steps[idx];
        double floor_bp = (commission_bp + (((0.5 * tick) / q) * 1e4)) + sell_tax_bp;
        bp = (table_bp >= floor_bp) ? table_bp : floor_bp;
    }
    *out_kappa = (bp * 1e-4) * mult;
    return true;
}

inline double liquidation_value(
    double cash,
    double units,
    bool locked,
    double p,
    double ks,
    double phis,
    double carry
) noexcept {
    double chi = locked ? carry : 1.0;
    double one_minus = 1.0 - (ks * chi);
    double max_term = (one_minus >= 0.0) ? one_minus : 0.0;
    double held_flag = (units > 0.0) ? 1.0 : 0.0;
    return (cash + ((units * p) * max_term)) - ((phis * chi) * held_flag);
}

/* SplitMix64 + xoshiro256** deterministic PRNG for HP-6b adaptive bid-gap MC */
struct Xoshiro256SS {
    uint64_t s[4];

    explicit Xoshiro256SS(uint64_t seed) noexcept {
        uint64_t z = seed;
        for (int i = 0; i < 4; ++i) {
            z += 0x9e3779b97f4a7c15ULL;
            uint64_t x = z;
            x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
            x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
            s[i] = x ^ (x >> 31);
        }
    }

    static inline uint64_t rotl(uint64_t x, int k) noexcept {
        return (x << k) | (x >> (64 - k));
    }

    inline uint64_t next_u64() noexcept {
        const uint64_t result = rotl(s[1] * 5ULL, 7) * 9ULL;
        const uint64_t t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = rotl(s[3], 45);
        return result;
    }

    inline double next_f64() noexcept {
        return static_cast<double>(next_u64() >> 11) * 0x1.0p-53;
    }

    inline uint32_t next_bounded(uint32_t bound) noexcept {
        /* Lemire unbiased bounded integer */
        uint64_t x = next_u64();
        __uint128_t m = static_cast<__uint128_t>(x) * static_cast<__uint128_t>(bound);
        uint64_t l = static_cast<uint64_t>(m);
        if (l < bound) {
            uint64_t threshold = (0ULL - bound) % bound;
            while (l < threshold) {
                x = next_u64();
                m = static_cast<__uint128_t>(x) * static_cast<__uint128_t>(bound);
                l = static_cast<uint64_t>(m);
            }
        }
        return static_cast<uint32_t>(m >> 64);
    }
};

} /* namespace */

extern "C" int32_t tg_odds_run_paths_f64(
    const tg_odds_spec_in_t* spec,
    const double* ladder_starts,
    const double* ladder_steps,
    const int32_t* check_close,
    const int32_t* check_new_seoul_day,
    const int32_t* check_banded,
    const int32_t* check_can_enter_date,
    const int32_t* check_force_exit_date,
    const double* check_sell_tax_bp,
    const double* prices,
    const double* d_edges,
    const double* u_edges,
    double* out_p,
    double* out_v,
    double* out_cost,
    double* out_x,
    int8_t* out_outcome,
    uint8_t* out_fp,
    uint8_t* out_entered,
    int64_t* out_entries,
    int64_t* out_wins,
    int64_t* out_losses,
    int64_t* out_unresolved,
    double* out_gap,
    double* out_cash_min,
    uint8_t* out_locked,
    int64_t* out_edge,
    int64_t* out_carried,
    double* out_stake,
    double* out_br_r,
    int64_t* out_br_d,
    int64_t max_brackets,
    int64_t* out_num_brackets
) {
    try {
        if (spec == nullptr || check_close == nullptr || check_new_seoul_day == nullptr ||
            check_banded == nullptr || check_can_enter_date == nullptr ||
            check_force_exit_date == nullptr || check_sell_tax_bp == nullptr ||
            prices == nullptr || d_edges == nullptr || u_edges == nullptr ||
            out_p == nullptr || out_v == nullptr || out_cost == nullptr || out_x == nullptr ||
            out_outcome == nullptr || out_fp == nullptr || out_entered == nullptr ||
            out_entries == nullptr || out_wins == nullptr || out_losses == nullptr ||
            out_unresolved == nullptr || out_gap == nullptr || out_cash_min == nullptr ||
            out_locked == nullptr || out_edge == nullptr || out_carried == nullptr ||
            out_stake == nullptr || out_num_brackets == nullptr) {
            return TG_ERR_INVALID;
        }

        const int32_t n_paths = spec->n_paths;
        const int32_t n_checks = spec->n_checks;
        if (n_paths < 1 || n_checks < 1 || spec->n_ladder_rows < 0 || spec->n_ladder_rows > 64) {
            return TG_ERR_INVALID;
        }
        if (spec->n_ladder_rows > 0 && (ladder_starts == nullptr || ladder_steps == nullptr)) {
            return TG_ERR_INVALID;
        }
        if (spec->fraction_kind == TG_FRAC_KELLY && !spec->has_fstar) {
            return TG_ERR_INVALID;
        }

        const bool moonshot = (spec->moonshot != 0);
        const bool has_bracket = (spec->has_bracket != 0);
        const int32_t sizing_kind = spec->sizing_kind;
        const int32_t fraction_kind = spec->fraction_kind;
        const bool has_cap_krw = (spec->has_cap_krw != 0);
        const bool has_delist_h = (spec->has_delist_h != 0);
        const int32_t book_kind = spec->book_kind;
        const int32_t n_ladder_rows = spec->n_ladder_rows;
        const bool record_brackets = (spec->record_brackets != 0);

        const double w0 = spec->w0;
        const double target = spec->target;
        const double floor_val = spec->floor_val;
        const double daily_loss = spec->daily_loss;
        const double mult = spec->mult;
        const double take_profit = spec->take_profit;
        const double stop = spec->stop;
        const double fraction_val = spec->fraction_val;
        const double fstar = spec->fstar;
        const double cap_krw = spec->cap_krw;
        const double delist_h = spec->delist_h;
        const double table_bp = spec->table_bp;
        const double commission_bp = spec->commission_bp;
        const double quote_krw = spec->quote_krw;
        const double lot = spec->lot;
        const double min_krw = spec->min_krw;
        const double phib = mult * spec->phi_buy;
        const double phis = mult * spec->phi_sell;
        const double carry = spec->carry_mult;
        const double reserve = (spec->cost_stress * spec->carry_mult) * spec->phi_sell;
        const double inf_val = std::numeric_limits<double>::infinity();

        /* Precompute offsets into d_edges and u_edges per check:
         * When check_banded[j] != 0, d_edges / u_edges has n_paths values; else 1 scalar value.
         */
        std::vector<size_t> band_offsets(static_cast<size_t>(n_checks), 0);
        size_t cur_band_off = 0;
        for (int32_t j = 0; j < n_checks; ++j) {
            band_offsets[static_cast<size_t>(j)] = cur_band_off;
            cur_band_off += (check_banded[j] != 0) ? static_cast<size_t>(n_paths) : 1u;
        }

        std::vector<std::vector<std::pair<double, int64_t>>> step_brackets;
        if (record_brackets) {
            step_brackets.resize(static_cast<size_t>(n_checks));
        }

        /* Cache-tiled execution over blocks of 1024 paths (fits comfortably in L1D cache) */
        constexpr int32_t TILE = 1024;
        std::vector<double> cash(TILE), units(TILE), booked(TILE), x(TILE);
        std::vector<double> entry(TILE), kb_e(TILE), gap(TILE), stake(TILE);
        std::vector<double> tp(TILE), sl(TILE), d_lock(TILE);
        std::vector<double> cash_min(TILE), day_ref(TILE), p_end(TILE), ks_end(TILE);
        std::vector<int64_t> j_e(TILE), entries(TILE), wins(TILE), losses(TILE);
        std::vector<int64_t> carried(TILE), edge(TILE), first(TILE);
        std::vector<int8_t> outcome(TILE);
        std::vector<uint8_t> done(TILE), entered(TILE), fp(TILE), x_set(TILE);
        std::vector<uint8_t> locked(TILE), lock_stop(TILE), day_stop(TILE), delisted(TILE);

        for (int32_t base = 0; base < n_paths; base += TILE) {
            const int32_t count = std::min(TILE, n_paths - base);

            for (int32_t i = 0; i < count; ++i) {
                cash[i] = w0;
                units[i] = 0.0;
                booked[i] = 0.0;
                x[i] = 0.0;
                entry[i] = 0.0;
                kb_e[i] = 0.0;
                gap[i] = 0.0;
                stake[i] = 0.0;
                tp[i] = inf_val;
                sl[i] = 0.0;
                d_lock[i] = 0.0;
                cash_min[i] = w0;
                day_ref[i] = w0;
                p_end[i] = 0.0;
                ks_end[i] = 0.0;
                j_e[i] = 0;
                entries[i] = 0;
                wins[i] = 0;
                losses[i] = 0;
                carried[i] = 0;
                edge[i] = 0;
                first[i] = -2;
                outcome[i] = 0;
                done[i] = 0;
                entered[i] = 0;
                fp[i] = 0;
                x_set[i] = 0;
                locked[i] = 0;
                lock_stop[i] = 0;
                day_stop[i] = 0;
                delisted[i] = 0;
            }

            for (int32_t j = 0; j < n_checks; ++j) {
                const double* p_row = prices + static_cast<size_t>(j) * static_cast<size_t>(n_paths) + static_cast<size_t>(base);
                const bool banded = (check_banded[j] != 0);
                const bool is_close = (check_close[j] != 0);
                const bool new_day = (j > 0) && (check_new_seoul_day[j] != 0);
                const bool force_exit_day = (check_force_exit_date[j] != 0);
                const bool can_enter_day = (check_can_enter_date[j] != 0);
                const double sell_tax = check_sell_tax_bp[j];
                const size_t boff = band_offsets[static_cast<size_t>(j)];
                const double* d_ptr = banded ? (d_edges + boff + static_cast<size_t>(base)) : (d_edges + boff);
                const double* u_ptr = banded ? (u_edges + boff + static_cast<size_t>(base)) : (u_edges + boff);

                for (int32_t i = 0; i < count; ++i) {
                    const double p = p_row[i];
                    const double d_edge = banded ? d_ptr[i] : d_ptr[0];
                    const double u_edge = banded ? u_ptr[i] : u_ptr[0];

                    if (new_day) {
                        day_ref[i] = liquidation_value(cash[i], units[i], locked[i] != 0, p_end[i], ks_end[i], phis, carry);
                        day_stop[i] = 0;
                    }
                    if (banded && !is_close) {
                        if ((p == d_edge) || (p == u_edge)) {
                            edge[i] += 1;
                        }
                    }

                    double ks = 0.0;
                    if (!kappa_scalar(p, book_kind, n_ladder_rows, ladder_starts, ladder_steps,
                                      table_bp, commission_bp, quote_krw, mult, sell_tax, &ks)) {
                        return TG_FALLBACK_PRECISION;
                    }

                    const double v = liquidation_value(cash[i], units[i], locked[i] != 0, p, ks, phis, carry);
                    if (!done[i] && !fp[i] && (v >= target)) {
                        fp[i] = 1;
                        if (!x_set[i]) {
                            x[i] = ((cash[i] + (units[i] * p)) + booked[i]) - w0;
                            x_set[i] = 1;
                        }
                    }

                    const bool breach = (!done[i]) && ((day_ref[i] - v) >= daily_loss);
                    if (breach) {
                        day_stop[i] = 1;
                    }

                    const bool live = (!done[i]) && (units[i] > 0.0);
                    const bool queued = live && (locked[i] != 0) && (p > d_lock[i]);
                    bool free_pos = live && (locked[i] == 0);
                    const bool gone = has_delist_h && free_pos && (static_cast<int64_t>(j) == (first[i] + 1));
                    if (gone) {
                        free_pos = false;
                    }

                    const bool reach = moonshot && free_pos && (v >= target);
                    bool win = free_pos && (!reach) && (p >= tp[i]);
                    bool loss = free_pos && (!reach) && (!win) && (p <= sl[i]);
                    const bool rest = free_pos && (!reach) && (!win) && (!loss);
                    const bool cut = rest && breach;
                    const bool rule = force_exit_day && rest && (!cut);
                    const bool trigger = reach || win || loss || cut || rule;
                    const bool stuck = banded && trigger && (!(p > d_edge));

                    if (stuck) {
                        locked[i] = 1;
                        d_lock[i] = d_edge;
                        lock_stop[i] = loss ? 1 : 0;
                        win = false;
                        loss = false;
                    }

                    const bool out_fill = (trigger && (!stuck)) || queued;
                    const bool filled = out_fill || gone;

                    if (filled) {
                        if (record_brackets && (win || loss)) {
                            const double min_ks = (1.0 <= ks) ? 1.0 : ks;
                            const double r_val = ((p / entry[i]) * (1.0 - min_ks)) - (1.0 + kb_e[i]);
                            const int64_t d_val = static_cast<int64_t>(j) - j_e[i];
                            step_brackets[static_cast<size_t>(j)].emplace_back(r_val, d_val);
                        }
                        if ((loss || (queued && (lock_stop[i] != 0))) && (p < sl[i])) {
                            const double g_val = (sl[i] - p) / entry[i];
                            if (g_val > gap[i]) {
                                gap[i] = g_val;
                            }
                        }
                        const double chi = queued ? carry : 1.0;
                        double charge = 0.0;
                        if (out_fill) {
                            const double kchi = ks * chi;
                            const double min_kchi = (1.0 <= kchi) ? 1.0 : kchi;
                            charge = ((units[i] * p) * min_kchi) + (phis * chi);
                        }
                        if (gone) {
                            double fee = 0.0;
                            if (delist_h < 1.0) {
                                const double q_del = p * (1.0 - delist_h);
                                double ks_del = 0.0;
                                if (!kappa_scalar(q_del, book_kind, n_ladder_rows, ladder_starts, ladder_steps,
                                                  table_bp, commission_bp, quote_krw, mult, sell_tax, &ks_del)) {
                                    return TG_FALLBACK_PRECISION;
                                }
                                const double min_ks_del = (1.0 <= ks_del) ? 1.0 : ks_del;
                                fee = ((units[i] * q_del) * min_ks_del) + phis;
                            }
                            charge = ((units[i] * p) * delist_h) + fee;
                        }

                        cash[i] = (cash[i] + (units[i] * p)) - charge;
                        booked[i] += charge;
                        units[i] = 0.0;
                        if (queued) {
                            locked[i] = 0;
                            lock_stop[i] = 0;
                            d_lock[i] = 0.0;
                        }
                        if (win) {
                            wins[i] += 1;
                        }
                        if (loss) {
                            losses[i] += 1;
                        }
                        if (queued) {
                            carried[i] += 1;
                        }
                        if (gone) {
                            delisted[i] = 1;
                        }
                        const bool reached = moonshot && (cash[i] >= target);
                        const bool floored = (!reached) && (cash[i] <= floor_val);
                        if (reached) {
                            outcome[i] = 1;
                        } else if (floored) {
                            outcome[i] = 2;
                        }
                        if (reached || floored) {
                            done[i] = 1;
                            if (!x_set[i]) {
                                x[i] = ((cash[i] + (units[i] * p)) + booked[i]) - w0;
                                x_set[i] = 1;
                            }
                        }
                        if (cash[i] < cash_min[i]) {
                            cash_min[i] = cash[i];
                        }
                    }

                    bool can = (!done[i]) && (units[i] == 0.0) && (!filled) && (!day_stop[i]) && (!delisted[i]);
                    if (!has_bracket) {
                        can = can && (!entered[i]);
                    }
                    if (!can_enter_day) {
                        can = false;
                    }

                    if ((j < n_checks - 1) && can) {
                        double kb = 0.0;
                        if (!kappa_scalar(p, book_kind, n_ladder_rows, ladder_starts, ladder_steps,
                                          table_bp, commission_bp, quote_krw, mult, 0.0, &kb)) {
                            return TG_FALLBACK_PRECISION;
                        }
                        double a = ((cash[i] - phib) - reserve) / (1.0 + kb);
                        if (sizing_kind == TG_SIZING_FLOOR_SAFE) {
                            const double a2 = (((cash[i] - floor_val) - phib) - reserve) / (1.0 + kb);
                            if (a2 < a) {
                                a = a2;
                            }
                        } else {
                            double ks_stop = 0.0;
                            if (!kappa_scalar(p * (1.0 - stop), book_kind, n_ladder_rows, ladder_starts, ladder_steps,
                                              table_bp, commission_bp, quote_krw, mult, sell_tax, &ks_stop)) {
                                return TG_FALLBACK_PRECISION;
                            }
                            const double a2 = (((cash[i] - floor_val) - phib) - phis) /
                                              ((stop + kb) + (ks_stop * (1.0 - stop)));
                            if (a2 < a) {
                                a = a2;
                            }
                        }
                        if (!(a >= 0.0)) {
                            a = 0.0;
                        }
                        if (has_cap_krw && (cap_krw < a)) {
                            a = cap_krw;
                        }

                        const double pl = p * lot;
                        const double max_min = (min_krw >= pl) ? min_krw : pl;
                        const double min_u = std::ceil((max_min / pl) - 1e-9) * lot;
                        const double m_krw = min_u * p;
                        const bool at_floor = (a < m_krw);

                        double s_stake = 0.0;
                        if (fraction_kind == TG_FRAC_FIXED) {
                            const double fc = fraction_val * cash[i];
                            s_stake = (fc <= a) ? fc : a;
                        } else if (fraction_kind == TG_FRAC_KELLY) {
                            const double kc = (fraction_val * fstar) * cash[i];
                            s_stake = (kc <= a) ? kc : a;
                        } else {
                            double ks_tp = 0.0;
                            if (!kappa_scalar(p * (1.0 + take_profit), book_kind, n_ladder_rows, ladder_starts, ladder_steps,
                                              table_bp, commission_bp, quote_krw, mult, sell_tax, &ks_tp)) {
                                return TG_FALLBACK_PRECISION;
                            }
                            const double kw = (kb >= ks_tp) ? kb : ks_tp;
                            const double c_w = take_profit - (kw * (2.0 + take_profit));
                            const bool bet = (c_w > 0.0) && (cash[i] < target);
                            const double denom = bet ? c_w : 1.0;
                            const double reach_s = (((target - cash[i]) + phib) + phis) / denom;
                            const double max_rm = (reach_s >= m_krw) ? reach_s : m_krw;
                            const double s1 = (std::ceil((max_rm / pl) - 1e-9) * lot) * p;
                            const double s2 = (std::floor((a / pl) + 1e-9) * lot) * p;
                            const double s_min = (s1 <= s2) ? s1 : s2;
                            s_stake = bet ? s_min : 0.0;
                        }

                        double buy_u = std::floor((s_stake / pl) + 1e-9) * lot;
                        if (at_floor || ((buy_u * p) < m_krw)) {
                            buy_u = 0.0;
                        }

                        if (at_floor) {
                            outcome[i] = 2;
                            done[i] = 1;
                            if (!x_set[i]) {
                                x[i] = ((cash[i] + (units[i] * p)) + booked[i]) - w0;
                                x_set[i] = 1;
                            }
                        }

                        if (buy_u > 0.0) {
                            const double charge = ((buy_u * p) * kb) + phib;
                            cash[i] -= (buy_u * p) + charge;
                            booked[i] += charge;
                            units[i] = buy_u;
                            entry[i] = p;
                            kb_e[i] = kb;
                            j_e[i] = static_cast<int64_t>(j);
                            if (!entered[i]) {
                                first[i] = static_cast<int64_t>(j);
                            }
                            const double up = buy_u * p;
                            if (up > stake[i]) {
                                stake[i] = up;
                            }
                            entered[i] = 1;
                            entries[i] += 1;
                            if (has_bracket) {
                                tp[i] = p * (1.0 + take_profit);
                                sl[i] = p * (1.0 - stop);
                            }
                            if (cash[i] < cash_min[i]) {
                                cash_min[i] = cash[i];
                            }
                        }
                    }

                    p_end[i] = p;
                    ks_end[i] = ks;
                }
            }

            /* Horizon settlement for this tile */
            for (int32_t i = 0; i < count; ++i) {
                const int32_t idx = base + i;
                const bool held = (units[i] > 0.0);
                const bool is_locked = (locked[i] != 0);
                const double chi = is_locked ? carry : 1.0;
                const double v_final = liquidation_value(cash[i], units[i], is_locked, p_end[i], ks_end[i], phis, carry);
                if (!x_set[i]) {
                    x[i] = ((cash[i] + (units[i] * p_end[i])) + booked[i]) - w0;
                    x_set[i] = 1;
                }
                const double kchi = ks_end[i] * chi;
                const double min_kchi = (1.0 <= kchi) ? 1.0 : kchi;
                const double final_cost = (booked[i] + ((units[i] * p_end[i]) * min_kchi)) +
                                          ((phis * chi) * (held ? 1.0 : 0.0));

                out_p[idx] = p_end[i];
                out_v[idx] = v_final;
                out_cost[idx] = final_cost;
                out_x[idx] = x[i];
                out_outcome[idx] = outcome[i];
                out_fp[idx] = fp[i];
                out_entered[idx] = entered[i];
                out_entries[idx] = entries[i];
                out_wins[idx] = wins[i];
                out_losses[idx] = losses[i];
                out_unresolved[idx] = has_bracket ? ((entries[i] - wins[i]) - losses[i]) : 0;
                out_gap[idx] = gap[i];
                out_cash_min[idx] = cash_min[i];
                out_locked[idx] = locked[i];
                out_edge[idx] = edge[i];
                out_carried[idx] = carried[i];
                out_stake[idx] = stake[i];
            }
        }

        int64_t total_br = 0;
        if (record_brackets) {
            for (int32_t j = 0; j < n_checks; ++j) {
                total_br += static_cast<int64_t>(step_brackets[static_cast<size_t>(j)].size());
            }
            if (total_br > 0) {
                if (out_br_r == nullptr || out_br_d == nullptr || total_br > max_brackets) {
                    *out_num_brackets = total_br;
                    return TG_ERR_CAPACITY;
                }
                int64_t pos = 0;
                for (int32_t j = 0; j < n_checks; ++j) {
                    for (const auto& pr : step_brackets[static_cast<size_t>(j)]) {
                        out_br_r[pos] = pr.first;
                        out_br_d[pos] = pr.second;
                        ++pos;
                    }
                }
            }
        }
        *out_num_brackets = total_br;
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_adaptive_bid_gap_mc(
    const double* returns,
    int32_t n_obs,
    int32_t n_paths,
    int32_t horizon,
    int32_t block_len,
    double cost_hurdle,
    uint64_t seed,
    tg_bid_gap_mc_out_t* output
) {
    try {
        if (returns == nullptr || output == nullptr || n_obs < 2 || n_paths < 1 ||
            n_paths > 2000000 || horizon < 1 || horizon > 10000 || block_len < 1 ||
            !std::isfinite(cost_hurdle) || cost_hurdle < 0.0) {
            return TG_ERR_INVALID;
        }
        for (int32_t i = 0; i < n_obs; ++i) {
            if (!std::isfinite(returns[i]) || returns[i] <= -1.0) {
                return TG_ERR_INVALID;
            }
        }

        const double restart_p = 1.0 / static_cast<double>(block_len);
        const uint32_t u_obs = static_cast<uint32_t>(n_obs);
        Xoshiro256SS rng(seed);

        std::vector<double> net_rets(static_cast<size_t>(n_paths));
        int64_t fav_count = 0;
        int64_t adv_count = 0;
        double sum_net = 0.0;

        for (int32_t p = 0; p < n_paths; ++p) {
            uint32_t idx = rng.next_bounded(u_obs);
            double wealth = 1.0;
            for (int32_t t = 0; t < horizon; ++t) {
                if (t > 0) {
                    if (block_len <= 1 || rng.next_f64() < restart_p) {
                        idx = rng.next_bounded(u_obs);
                    } else {
                        idx = (idx + 1u == u_obs) ? 0u : (idx + 1u);
                    }
                }
                wealth *= (1.0 + returns[idx]);
            }
            double net_r = (wealth - 1.0) - cost_hurdle;
            net_rets[static_cast<size_t>(p)] = net_r;
            sum_net += net_r;
            if (net_r > 0.0) {
                ++fav_count;
            } else if (net_r < -cost_hurdle) {
                ++adv_count;
            }
        }

        std::sort(net_rets.begin(), net_rets.end());
        auto quantile = [&](double q) -> double {
            if (n_paths == 1) {
                return net_rets[0];
            }
            double pos = q * static_cast<double>(n_paths - 1);
            size_t lo = static_cast<size_t>(std::floor(pos));
            size_t hi = static_cast<size_t>(std::ceil(pos));
            double frac = pos - static_cast<double>(lo);
            return net_rets[lo] + frac * (net_rets[hi] - net_rets[lo]);
        };

        output->favorable_prob = static_cast<double>(fav_count) / static_cast<double>(n_paths);
        output->adverse_prob = static_cast<double>(adv_count) / static_cast<double>(n_paths);
        output->mean_net_return = sum_net / static_cast<double>(n_paths);
        output->p05_net_return = quantile(0.05);
        output->p95_net_return = quantile(0.95);
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}
