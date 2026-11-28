#include "tg_abi.h"
#include "tg_fp128.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {

using tg::i128;
using tg::u128;
using tg::u256;
using tg::u384;

/* 512-bit unsigned integer (8 x 64-bit words, little-endian) for exact rational floor division */
struct u512 {
    uint64_t w[8]{0, 0, 0, 0, 0, 0, 0, 0};
};

int cmp_u512(const u512& a, const u512& b) noexcept {
    for (int i = 7; i >= 0; --i) {
        if (a.w[i] != b.w[i]) {
            return (a.w[i] < b.w[i]) ? -1 : 1;
        }
    }
    return 0;
}

void shl1_u512(u512* x) noexcept {
    uint64_t carry = 0;
    for (int i = 0; i < 8; ++i) {
        uint64_t next_carry = x->w[i] >> 63;
        x->w[i] = (x->w[i] << 1) | carry;
        carry = next_carry;
    }
}

void sub_u512_inplace(u512* a, const u512& b) noexcept {
    u128 borrow = 0;
    for (int i = 0; i < 8; ++i) {
        u128 av = a->w[i];
        u128 bv = static_cast<u128>(b.w[i]) + borrow;
        if (av >= bv) {
            a->w[i] = static_cast<uint64_t>(av - bv);
            borrow = 0;
        } else {
            a->w[i] = static_cast<uint64_t>((static_cast<u128>(1) << 64) + av - bv);
            borrow = 1;
        }
    }
}

u512 mul_u384_u128(const u384& a, u128 b) noexcept {
    uint64_t bw[2] = {static_cast<uint64_t>(b), static_cast<uint64_t>(b >> 64)};
    u512 out{};
    for (int i = 0; i < 6; ++i) {
        u128 carry = 0;
        for (int j = 0; j < 2; ++j) {
            u128 cur = static_cast<u128>(out.w[i + j]) + static_cast<u128>(a.w[i]) * static_cast<u128>(bw[j]) + carry;
            out.w[i + j] = static_cast<uint64_t>(cur);
            carry = cur >> 64;
        }
        int k = i + 2;
        while (carry != 0 && k < 8) {
            u128 cur = static_cast<u128>(out.w[k]) + carry;
            out.w[k] = static_cast<uint64_t>(cur);
            carry = cur >> 64;
            ++k;
        }
    }
    return out;
}

bool add_u384(const u384& a, const u384& b, u384* out) noexcept {
    u128 carry = 0;
    for (int i = 0; i < 6; ++i) {
        u128 cur = static_cast<u128>(a.w[i]) + static_cast<u128>(b.w[i]) + carry;
        out->w[i] = static_cast<uint64_t>(cur);
        carry = cur >> 64;
    }
    return carry == 0;
}

/* Binary long division of u512 by u512 -> quotient fits in u128 (or returns false on overflow/div0) */
bool div_floor_u512(const u512& num, const u512& den, u128* quot_out) noexcept {
    bool zero_den = true;
    for (int i = 0; i < 8; ++i) {
        if (den.w[i] != 0) {
            zero_den = false;
            break;
        }
    }
    if (zero_den) {
        return false;
    }
    if (cmp_u512(num, den) < 0) {
        *quot_out = 0;
        return true;
    }
    u512 rem{};
    u512 q{};
    for (int bit = 511; bit >= 0; --bit) {
        shl1_u512(&rem);
        rem.w[0] |= (num.w[bit >> 6] >> (bit & 63)) & 1ULL;
        if (cmp_u512(rem, den) >= 0) {
            sub_u512_inplace(&rem, den);
            q.w[bit >> 6] |= (1ULL << (bit & 63));
        }
    }
    for (int i = 2; i < 8; ++i) {
        if (q.w[i] != 0) {
            return false;
        }
    }
    u128 res = (static_cast<u128>(q.w[1]) << 64) | static_cast<u128>(q.w[0]);
    if (res > tg::MAX_MAG_FP18) {
        return false;
    }
    *quot_out = res;
    return true;
}

int bitlen_u128(u128 x) noexcept {
    if (x == 0) {
        return 0;
    }
    uint64_t hi = static_cast<uint64_t>(x >> 64);
    if (hi != 0) {
        return 128 - __builtin_clzll(hi);
    }
    uint64_t lo = static_cast<uint64_t>(x);
    return 64 - __builtin_clzll(lo);
}

/* Exact IEEE-754 binary64 round-to-nearest-even of signed num / unsigned den (matches Python float(Fraction(num, den))) */
double exact_ratio_to_f64(i128 num, u128 den) noexcept {
    if (num == 0) {
        return 0.0;
    }
    bool neg = (num < 0);
    u128 unum = tg::abs_i128(num);

    /* Shift unum or den so integer floor(shifted_num / shifted_den) lies in [2^53, 2^55)
     * with guard, round, and sticky bits preserved.
     * Specifically compute q = floor((unum * 2^s) / den) with 55..56 bits.
     */
    int bn = bitlen_u128(unum);
    int bd = bitlen_u128(den);
    /* We want unum * 2^shift / den in [2^54, 2^56).
     * Approximate log2(unum/den) is in (bn - bd - 1, bn - bd + 1).
     * Pick shift = 55 - (bn - bd).
     */
    int shift = 55 - (bn - bd);

    u512 big_num{};
    u512 big_den{};
    big_num.w[0] = static_cast<uint64_t>(unum);
    big_num.w[1] = static_cast<uint64_t>(unum >> 64);
    big_den.w[0] = static_cast<uint64_t>(den);
    big_den.w[1] = static_cast<uint64_t>(den >> 64);

    if (shift > 0) {
        for (int i = 0; i < shift; ++i) {
            shl1_u512(&big_num);
        }
    } else if (shift < 0) {
        for (int i = 0; i < -shift; ++i) {
            shl1_u512(&big_den);
        }
    }

    /* Long division big_num / big_den for small ~56-bit quotient + exact remainder */
    u512 rem{};
    uint64_t q = 0;
    for (int bit = 511; bit >= 0; --bit) {
        shl1_u512(&rem);
        rem.w[0] |= (big_num.w[bit >> 6] >> (bit & 63)) & 1ULL;
        if (cmp_u512(rem, big_den) >= 0) {
            sub_u512_inplace(&rem, big_den);
            if (bit < 64) {
                q |= (1ULL << bit);
            }
        }
    }
    bool rem_nonzero = false;
    for (int i = 0; i < 8; ++i) {
        if (rem.w[i] != 0) {
            rem_nonzero = true;
            break;
        }
    }

    /* Normalize so top bit is at position 52 (i.e. [2^52, 2^53)) with exact rounding.
     * Right now q >= 2^54 (since bn-1 - bd + 55 - (bn - bd) = 54, if unum*2^shift < den*2^54, q >= 2^54 unless ratio < 2^(bn-bd-1) impossible:
     * unum >= 2^(bn-1), den < 2^bd => unum/den > 2^(bn - bd - 1) => unum * 2^(55 - bn + bd) / den > 2^54!).
     * And unum < 2^bn, den >= 2^(bd-1) => unum/den < 2^(bn - bd + 1) => q < 2^56!
     * So bitlen(q) is ALWAYS 55 or 56!
     */
    int qbits = 64 - __builtin_clzll(q);
    int drop = qbits - 53; /* 2 or 3 bits to drop */
    uint64_t half = 1ULL << (drop - 1);
    uint64_t mask = (1ULL << drop) - 1ULL;
    uint64_t low_bits = q & mask;
    uint64_t sig = q >> drop;
    bool sticky = rem_nonzero || ((low_bits & (half - 1ULL)) != 0);
    bool round_bit = (low_bits & half) != 0;

    if (round_bit && (sticky || (sig & 1ULL) != 0)) {
        ++sig;
    }
    int exp2 = drop - shift;
    if (sig == (1ULL << 53)) {
        sig >>= 1;
        ++exp2;
    }
    double val = std::ldexp(static_cast<double>(sig), exp2);
    return neg ? -val : val;
}

struct CarryLot {
    u128 qty;
    u128 cost;
};

} /* namespace */

extern "C" int32_t tg_ma_crossover(
    const tg_i128_t* marks,
    int32_t num_marks,
    int32_t fast_window,
    int32_t slow_window,
    int32_t* out_above
) {
    try {
        if (out_above == nullptr || num_marks < 0 || num_marks > 20000 ||
            fast_window < 1 || slow_window <= fast_window || slow_window > 4096 ||
            (num_marks > 0 && marks == nullptr)) {
            return TG_ERR_INVALID;
        }
        for (int32_t i = 0; i < num_marks; ++i) {
            i128 v = tg::unpack_i128(marks[i]);
            if (v <= 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(v)) {
                return TG_FALLBACK_PRECISION;
            }
        }
        if (num_marks < slow_window) {
            *out_above = 0;
            return TG_OK;
        }
        u256 sum_fast{0, 0};
        u256 sum_slow{0, 0};
        for (int32_t i = num_marks - fast_window; i < num_marks; ++i) {
            u256 term{static_cast<u128>(tg::unpack_i128(marks[i])), 0};
            if (!tg::add_u256(sum_fast, term, &sum_fast)) {
                return TG_FALLBACK_PRECISION;
            }
        }
        for (int32_t i = num_marks - slow_window; i < num_marks; ++i) {
            u256 term{static_cast<u128>(tg::unpack_i128(marks[i])), 0};
            if (!tg::add_u256(sum_slow, term, &sum_slow)) {
                return TG_FALLBACK_PRECISION;
            }
        }
        u384 lhs = tg::mul_u256_u128(sum_fast, static_cast<u128>(slow_window));
        u384 rhs = tg::mul_u256_u128(sum_slow, static_cast<u128>(fast_window));
        *out_above = (tg::cmp_u384(lhs, rhs) > 0) ? 1 : 0;
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_universe_momentum_top1(
    const tg_momentum_candidate_t* top_candidates,
    int32_t num_candidates,
    int32_t held_coin_id,
    int32_t held_flag_code,
    int32_t held_has_now_price,
    int32_t held_has_lag_price,
    const tg_i128_t* held_now_price,
    const tg_i128_t* held_lag_price,
    int32_t hold_count,
    int32_t min_hold_slots,
    const tg_i128_t* switch_margin,
    int32_t* out_chosen_coin_id,
    int32_t* out_new_hold_count
) {
    try {
        if (out_chosen_coin_id == nullptr || out_new_hold_count == nullptr ||
            switch_margin == nullptr || num_candidates < 0 || num_candidates > 4096 ||
            hold_count < 0 || min_hold_slots < 1 || min_hold_slots > 4096 ||
            (num_candidates > 0 && top_candidates == nullptr)) {
            return TG_ERR_INVALID;
        }
        i128 sm_in = tg::unpack_i128(*switch_margin);
        if (sm_in < 0) {
            return TG_ERR_INVALID;
        }
        if (!tg::in_fp18_range(sm_in)) {
            return TG_FALLBACK_PRECISION;
        }
        u128 sm = static_cast<u128>(sm_in);

        /* Find best unflagged candidate with defined return r_X = now / lag - 1 */
        bool has_best = false;
        int32_t best_id = -1;
        u128 best_now = 0;
        u128 best_lag = 0;

        for (int32_t i = 0; i < num_candidates; ++i) {
            const tg_momentum_candidate_t& c = top_candidates[i];
            u128 c_now = 0;
            u128 c_lag = 0;
            if (c.has_now_price) {
                i128 v = tg::unpack_i128(c.now_price);
                if (v <= 0) return TG_ERR_INVALID;
                if (!tg::in_fp18_range(v)) return TG_FALLBACK_PRECISION;
                c_now = static_cast<u128>(v);
            }
            if (c.has_lag_price) {
                i128 v = tg::unpack_i128(c.lag_price);
                if (v <= 0) return TG_ERR_INVALID;
                if (!tg::in_fp18_range(v)) return TG_FALLBACK_PRECISION;
                c_lag = static_cast<u128>(v);
            }
            if (c.flag_code != TG_FLAG_UNFLAGGED || !c.has_now_price || !c.has_lag_price) {
                continue;
            }
            if (!has_best) {
                has_best = true;
                best_id = c.coin_id;
                best_now = c_now;
                best_lag = c_lag;
            } else {
                /* Compare c_now / c_lag vs best_now / best_lag; tie-break by smaller coin_id */
                u256 lhs = tg::mul128_u256(c_now, best_lag);
                u256 rhs = tg::mul128_u256(best_now, c_lag);
                int cmp = tg::cmp_u256(lhs, rhs);
                if (cmp > 0 || (cmp == 0 && c.coin_id < best_id)) {
                    best_id = c.coin_id;
                    best_now = c_now;
                    best_lag = c_lag;
                }
            }
        }

        bool has_r_h = false;
        u128 h_now = 0;
        u128 h_lag = 0;
        if (held_coin_id >= 0) {
            if (held_has_now_price) {
                if (held_now_price == nullptr) return TG_ERR_INVALID;
                i128 v = tg::unpack_i128(*held_now_price);
                if (v <= 0) return TG_ERR_INVALID;
                if (!tg::in_fp18_range(v)) return TG_FALLBACK_PRECISION;
                h_now = static_cast<u128>(v);
            }
            if (held_has_lag_price) {
                if (held_lag_price == nullptr) return TG_ERR_INVALID;
                i128 v = tg::unpack_i128(*held_lag_price);
                if (v <= 0) return TG_ERR_INVALID;
                if (!tg::in_fp18_range(v)) return TG_FALLBACK_PRECISION;
                h_lag = static_cast<u128>(v);
            }
            has_r_h = (held_has_now_price != 0) && (held_has_lag_price != 0);
        }

        int32_t decision = -1;
        bool best_positive = has_best && (best_now > best_lag);
        bool rh_nonpositive = has_r_h && (h_now <= h_lag);

        if (held_coin_id >= 0 && held_flag_code == TG_FLAG_WARNING) {
            decision = -1; /* rule 1 */
        } else if (held_coin_id >= 0 && !has_r_h) {
            decision = held_coin_id; /* rule 2 */
        } else if (held_coin_id < 0) {
            decision = best_positive ? best_id : -1; /* rules 3 & 4 */
        } else if (hold_count < min_hold_slots) {
            decision = held_coin_id; /* rule 5 */
        } else if (rh_nonpositive && !best_positive) {
            decision = -1; /* rule 6 */
        } else if (has_best && best_id != held_coin_id && best_positive) {
            /* rule 7: best_r - r_h > switch_margin
             * <=> (best_now / best_lag) - (h_now / h_lag) > sm / 10^18
             */
            u256 t1 = tg::mul128_u256(best_now, h_lag);
            u256 t2 = tg::mul128_u256(h_now, best_lag);
            if (tg::cmp_u256(t1, t2) > 0) {
                u256 diff = tg::sub_u256(t1, t2);
                u384 lhs = tg::mul_u256_u128(diff, tg::SCALE_FP18);
                u256 lags = tg::mul128_u256(best_lag, h_lag);
                u384 rhs = tg::mul_u256_u128(lags, sm);
                decision = (tg::cmp_u384(lhs, rhs) > 0) ? best_id : held_coin_id;
            } else {
                decision = held_coin_id;
            }
        } else {
            decision = held_coin_id; /* rule 8 */
        }

        *out_chosen_coin_id = decision;
        *out_new_hold_count = (decision == held_coin_id) ? (hold_count + 1) : 1;
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_simulate_carry(
    const tg_carry_bar_in_t* bars,
    const tg_carry_decision_in_t* decisions,
    int32_t num_bars,
    const tg_i128_t* initial_cash,
    const tg_i128_t* fee_fraction,
    const tg_i128_t* slip_fraction,
    const tg_i128_t* lot_size,
    const tg_i128_t* tick_size,
    const tg_i128_t* min_qty,
    const tg_i128_t* min_notional,
    int64_t deadline_us,
    int32_t lag,
    int32_t buy_hold,
    tg_carry_sim_out_t* out_summary,
    double* out_net_returns,
    tg_carry_fill_out_t* out_fills,
    int32_t max_fills,
    tg_fifo_lot_t* out_lots,
    int32_t max_lots
) {
    try {
        if (bars == nullptr || decisions == nullptr || initial_cash == nullptr ||
            fee_fraction == nullptr || slip_fraction == nullptr || lot_size == nullptr ||
            tick_size == nullptr || min_qty == nullptr || min_notional == nullptr ||
            out_summary == nullptr || out_net_returns == nullptr ||
            num_bars < 2 || num_bars > 20000 || (lag != 1 && lag != 2)) {
            return TG_ERR_INVALID;
        }

        i128 init_c = tg::unpack_i128(*initial_cash);
        i128 fee_in = tg::unpack_i128(*fee_fraction);
        i128 slip_in = tg::unpack_i128(*slip_fraction);
        i128 lot_in = tg::unpack_i128(*lot_size);
        i128 tick_in = tg::unpack_i128(*tick_size);
        i128 mq_in = tg::unpack_i128(*min_qty);
        i128 mn_in = tg::unpack_i128(*min_notional);

        if (init_c <= 0 || fee_in < 0 || slip_in < 0 || lot_in <= 0 || tick_in <= 0 || mq_in < 0 || mn_in < 0) {
            return TG_ERR_INVALID;
        }
        if (!tg::in_fp18_range(init_c) || !tg::in_fp18_range(fee_in) || !tg::in_fp18_range(slip_in) ||
            !tg::in_fp18_range(lot_in) || !tg::in_fp18_range(tick_in) ||
            !tg::in_fp18_range(mq_in) || !tg::in_fp18_range(mn_in)) {
            return TG_FALLBACK_PRECISION;
        }

        u128 cash = static_cast<u128>(init_c);
        u128 fee = static_cast<u128>(fee_in);
        u128 slip = static_cast<u128>(slip_in);
        u128 lot = static_cast<u128>(lot_in);
        u128 tick = static_cast<u128>(tick_in);
        u128 mq = static_cast<u128>(mq_in);
        u128 mn = static_cast<u128>(mn_in);

        if (slip >= tg::SCALE_FP18 || fee > tg::SCALE_FP18 / 5) {
            return TG_ERR_INVALID;
        }
        /* Ensure tick * 10^18 fits in u128 for fast exact tick rounding */
        u256 tick_scaled_256 = tg::mul128_u256(tick, tg::SCALE_FP18);
        if (tick_scaled_256.hi != 0) {
            return TG_FALLBACK_PRECISION;
        }
        u128 tick_scaled = tick_scaled_256.lo;

        u128 units = 0;
        u128 fees = 0;
        u128 turnover = 0;
        i128 realized = 0;
        u128 basis = 0;
        int32_t trips = 0;
        int32_t rejected = 0;
        int32_t fill_count = 0;

        std::vector<CarryLot> lots;
        size_t lot_head = 0;
        u128 prev_nav = cash;

        for (int32_t i = 1; i < num_bars; ++i) {
            i128 bid_in = tg::unpack_i128(bars[i].bid);
            i128 ask_in = tg::unpack_i128(bars[i].ask);
            i128 mark_in = tg::unpack_i128(bars[i].mark);
            if (bid_in <= 0 || ask_in <= 0 || mark_in <= 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(bid_in) || !tg::in_fp18_range(ask_in) || !tg::in_fp18_range(mark_in)) {
                return TG_FALLBACK_PRECISION;
            }
            u128 row_bid = static_cast<u128>(bid_in);
            u128 row_ask = static_cast<u128>(ask_in);
            u128 mark = static_cast<u128>(mark_in);

            u128 held_val = 0;
            if (!tg::mul_fp18_exact(units, mark, &held_val)) {
                return TG_FALLBACK_PRECISION;
            }
            if (tg::MAX_MAG_FP18 - cash < held_val || cash + held_val == 0) {
                return TG_FALLBACK_PRECISION;
            }
            u128 pre_nav = cash + held_val;

            int32_t action = 0; /* 0 = hold, 1 = entry, 2 = exit */
            u128 quantity = 0;
            u128 exec_ask = 0;
            u128 exec_bid = 0;

            if (i >= lag) {
                const tg_carry_decision_in_t& dec = decisions[i - lag];
                int32_t d_state = buy_hold ? TG_DECISION_LONG : dec.state;
                u128 target = buy_hold ? tg::SCALE_FP18 : static_cast<u128>(tg::unpack_i128(dec.target_fraction));
                if (!buy_hold && d_state == TG_DECISION_LONG) {
                    i128 tf = tg::unpack_i128(dec.target_fraction);
                    if (tf <= 0 || !tg::in_fp18_range(tf) || static_cast<u128>(tf) > tg::SCALE_FP18) {
                        return TG_FALLBACK_PRECISION;
                    }
                    target = static_cast<u128>(tf);
                }
                if (dec.decided_us > bars[i].observed_us) {
                    return TG_ERR_INVALID;
                }

                bool blocked = (bars[i].observed_us >= deadline_us) || (d_state == TG_DECISION_UNAVAILABLE);
                if (d_state == TG_DECISION_LONG) {
                    /* gap = target * pre_nav - held_val */
                    u256 t_nav = tg::mul128_u256(target, pre_nav);
                    u256 hv_36 = tg::mul128_u256(held_val, tg::SCALE_FP18);
                    if (tg::cmp_u256(t_nav, hv_36) > 0) {
                        action = 1;
                    }
                } else if (d_state == TG_DECISION_CASH && units > 0) {
                    action = 2;
                    /* cash_target at/after deadline is also blocked by MANAGED_AUTHORITY_UNAVAILABLE */
                }

                if (!blocked && (action == 1 || action == 2)) {
                    /* ask = ceil(row.ask * (1 + slip) / tick) * tick */
                    u256 ask_num = tg::mul128_u256(row_ask, tg::SCALE_FP18 + slip);
                    u128 ask_ticks = 0;
                    if (!tg::div_ceil_u256_u128(ask_num, tick_scaled, &ask_ticks)) {
                        return TG_FALLBACK_PRECISION;
                    }
                    u256 ask_p = tg::mul128_u256(ask_ticks, tick);
                    if (ask_p.hi != 0 || ask_p.lo > tg::MAX_MAG_FP18) {
                        return TG_FALLBACK_PRECISION;
                    }
                    exec_ask = ask_p.lo;

                    /* bid = floor(row.bid * (1 - slip) / tick) * tick */
                    u256 bid_num = tg::mul128_u256(row_bid, tg::SCALE_FP18 - slip);
                    u128 bid_ticks = 0;
                    if (!tg::div_floor_u256_u128(bid_num, tick_scaled, &bid_ticks)) {
                        return TG_FALLBACK_PRECISION;
                    }
                    u256 bid_p = tg::mul128_u256(bid_ticks, tick);
                    if (bid_p.hi != 0 || bid_p.lo > tg::MAX_MAG_FP18) {
                        return TG_FALLBACK_PRECISION;
                    }
                    exec_bid = bid_p.lo;
                    if (exec_bid == 0 || exec_ask == 0) {
                        return TG_ERR_INVALID;
                    }

                    if (action == 1) {
                        u256 t_nav = tg::mul128_u256(target, pre_nav);
                        u256 hv_36 = tg::mul128_u256(held_val, tg::SCALE_FP18);
                        u256 gap_36 = tg::sub_u256(t_nav, hv_36);
                        u256 scale36 = tg::mul128_u256(tg::SCALE_FP18, tg::SCALE_FP18);

                        /* denom_54 = ask*(1+fee)*(1-target) + target*mark*10^18 */
                        u256 ask_1pf = tg::mul128_u256(exec_ask, tg::SCALE_FP18 + fee); /* scale 10^36 */
                        u384 d_part1 = tg::mul_u256_u128(ask_1pf, tg::SCALE_FP18 - target); /* scale 10^54 */
                        u256 t_mark = tg::mul128_u256(target, mark); /* scale 10^36 */
                        u384 d_part2 = tg::mul_u256_u128(t_mark, tg::SCALE_FP18); /* scale 10^54 */
                        u384 denom_54{};
                        if (!add_u384(d_part1, d_part2, &denom_54)) {
                            return TG_FALLBACK_PRECISION;
                        }

                        /* k1 = floor((gap_36 * 10^36) / (denom_54 * lot)) */
                        u384 gap_54 = tg::mul_u256_u128(gap_36, tg::SCALE_FP18);
                        u512 num1 = mul_u384_u128(gap_54, tg::SCALE_FP18); /* scale 10^72 */
                        u512 den1 = mul_u384_u128(denom_54, lot); /* scale 10^72 */
                        u128 k1 = 0;
                        if (!div_floor_u512(num1, den1, &k1)) {
                            return TG_FALLBACK_PRECISION;
                        }

                        /* k2 = floor((cash * 10^36) / (ask_1pf * lot)) */
                        u384 cash_54 = tg::mul_u256_u128(scale36, cash);
                        u512 num2{};
                        for (int w = 0; w < 6; ++w) num2.w[w] = cash_54.w[w];
                        u384 den2_54 = tg::mul_u256_u128(ask_1pf, lot);
                        u512 den2{};
                        for (int w = 0; w < 6; ++w) den2.w[w] = den2_54.w[w];
                        u128 k2 = 0;
                        if (!div_floor_u512(num2, den2, &k2)) {
                            return TG_FALLBACK_PRECISION;
                        }

                        u128 lots_to_buy = (k1 < k2) ? k1 : k2;
                        u256 q_prod = tg::mul128_u256(lots_to_buy, lot);
                        if (q_prod.hi != 0 || q_prod.lo > tg::MAX_MAG_FP18) {
                            return TG_FALLBACK_PRECISION;
                        }
                        quantity = q_prod.lo;
                    } else {
                        quantity = units;
                    }
                }
            }

            if (quantity > 0) {
                u128 exec_price = (action == 1) ? exec_ask : exec_bid;
                u128 notional = 0;
                if (!tg::mul_fp18_exact(quantity, exec_price, &notional)) {
                    return TG_FALLBACK_PRECISION;
                }
                if (quantity < mq || notional < mn) {
                    ++rejected;
                } else {
                    u128 charge = 0;
                    if (!tg::mul_fp18_exact(notional, fee, &charge)) {
                        return TG_FALLBACK_PRECISION;
                    }
                    if (action == 1) {
                        if (tg::MAX_MAG_FP18 - notional < charge) {
                            return TG_FALLBACK_PRECISION;
                        }
                        u128 outlay = notional + charge;
                        if (cash < outlay || tg::MAX_MAG_FP18 - units < quantity || tg::MAX_MAG_FP18 - basis < outlay) {
                            return TG_FALLBACK_PRECISION;
                        }
                        cash -= outlay;
                        units += quantity;
                        basis += outlay;
                        lots.push_back(CarryLot{quantity, outlay});
                    } else {
                        if (units < quantity) {
                            return TG_ERR_NEGATIVE_STATE;
                        }
                        u128 needed = quantity;
                        u128 released = 0;
                        while (needed > 0) {
                            if (lot_head >= lots.size()) {
                                return TG_ERR_NEGATIVE_STATE;
                            }
                            CarryLot& front = lots[lot_head];
                            u128 taken = (needed < front.qty) ? needed : front.qty;
                            u128 alloc = 0;
                            if (!tg::fifo_alloc_cost_fp18(front.cost, taken, front.qty, &alloc)) {
                                return TG_FALLBACK_PRECISION;
                            }
                            if (tg::MAX_MAG_FP18 - released < alloc) {
                                return TG_FALLBACK_PRECISION;
                            }
                            released += alloc;
                            needed -= taken;
                            if (taken == front.qty) {
                                ++lot_head;
                            } else {
                                front.qty -= taken;
                                front.cost -= alloc;
                            }
                        }
                        if (notional < charge) {
                            return TG_FALLBACK_PRECISION;
                        }
                        u128 proceeds = notional - charge;
                        if (tg::MAX_MAG_FP18 - cash < proceeds || basis < released) {
                            return TG_FALLBACK_PRECISION;
                        }
                        cash += proceeds;
                        units -= quantity;
                        basis -= released;
                        i128 pnl = static_cast<i128>(proceeds) - static_cast<i128>(released);
                        if (!tg::add_checked_fp18(realized, pnl, &realized)) {
                            return TG_FALLBACK_PRECISION;
                        }
                        if (units == 0) {
                            ++trips;
                        }
                    }
                    if (tg::MAX_MAG_FP18 - fees < charge || tg::MAX_MAG_FP18 - turnover < notional) {
                        return TG_FALLBACK_PRECISION;
                    }
                    fees += charge;
                    turnover += notional;
                    if (out_fills != nullptr) {
                        if (fill_count >= max_fills) {
                            return TG_ERR_CAPACITY;
                        }
                        out_fills[fill_count].bar_index = i;
                        out_fills[fill_count].action = action;
                        out_fills[fill_count].quantity = tg::pack_i128(static_cast<i128>(quantity));
                        out_fills[fill_count].price_quote = tg::pack_i128(static_cast<i128>(exec_price));
                        out_fills[fill_count].fee_quote = tg::pack_i128(static_cast<i128>(charge));
                    }
                    ++fill_count;
                }
            }

            u128 post_held_val = 0;
            if (!tg::mul_fp18_exact(units, mark, &post_held_val)) {
                return TG_FALLBACK_PRECISION;
            }
            if (tg::MAX_MAG_FP18 - cash < post_held_val || cash + post_held_val == 0) {
                return TG_FALLBACK_PRECISION;
            }
            u128 nav = cash + post_held_val;
            i128 diff = static_cast<i128>(nav) - static_cast<i128>(prev_nav);
            out_net_returns[i - 1] = exact_ratio_to_f64(diff, prev_nav);
            prev_nav = nav;
        }

        int32_t rem_lots = static_cast<int32_t>(lots.size() - lot_head);
        if (out_lots != nullptr) {
            if (rem_lots > max_lots) {
                return TG_ERR_CAPACITY;
            }
            for (int32_t k = 0; k < rem_lots; ++k) {
                out_lots[k].market_idx = 0;
                out_lots[k].reserved = 0;
                out_lots[k].quantity = tg::pack_i128(static_cast<i128>(lots[lot_head + k].qty));
                out_lots[k].cost_krw = tg::pack_i128(static_cast<i128>(lots[lot_head + k].cost));
            }
        }

        out_summary->completed_roundtrips = trips;
        out_summary->rejected_small_orders = rejected;
        out_summary->num_fills = fill_count;
        out_summary->num_lots = rem_lots;
        out_summary->terminal_cash = tg::pack_i128(static_cast<i128>(cash));
        out_summary->terminal_units = tg::pack_i128(static_cast<i128>(units));
        out_summary->terminal_basis = tg::pack_i128(static_cast<i128>(basis));
        out_summary->realized_net_profit = tg::pack_i128(realized);
        out_summary->total_fees = tg::pack_i128(static_cast<i128>(fees));
        out_summary->turnover = tg::pack_i128(static_cast<i128>(turnover));
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}
