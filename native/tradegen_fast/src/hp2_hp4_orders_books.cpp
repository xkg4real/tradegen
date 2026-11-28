#include "tg_abi.h"
#include "tg_fp128.hpp"

#include <cstdint>

extern "C" int32_t tg_check_bid_gap(
    const tg_i128_t* best_bid,
    const tg_i128_t* mark_price,
    const tg_i128_t* bid_gap_y,
    int32_t has_best_bid,
    int32_t has_y,
    int32_t* out_triggered
) {
    try {
        if (mark_price == nullptr || out_triggered == nullptr) {
            return TG_ERR_INVALID;
        }
        tg::i128 mark = tg::unpack_i128(*mark_price);
        if (mark <= 0) {
            return TG_ERR_INVALID;
        }
        if (!tg::in_fp18_range(mark)) {
            return TG_FALLBACK_PRECISION;
        }
        if (!has_best_bid || !has_y) {
            *out_triggered = 1;
            return TG_OK;
        }
        if (best_bid == nullptr || bid_gap_y == nullptr) {
            return TG_ERR_INVALID;
        }
        tg::i128 bid = tg::unpack_i128(*best_bid);
        tg::i128 y = tg::unpack_i128(*bid_gap_y);
        if (bid <= 0 || y < 0) {
            return TG_ERR_INVALID;
        }
        if (!tg::in_fp18_range(bid) || !tg::in_fp18_range(y)) {
            return TG_FALLBACK_PRECISION;
        }
        /* BR-26 ceiling: 0 <= y <= 0.05 (50000000000000000 in fp18) */
        constexpr tg::u128 MAX_Y_FP18 = static_cast<tg::u128>(50000000000000000ULL);
        tg::u128 uy = static_cast<tg::u128>(y);
        if (uy > MAX_Y_FP18) {
            return TG_ERR_INVALID;
        }
        /* Exact rational comparison:
         * Fraction(best_bid) <= Fraction(mark_price) * (1 - Fraction(bid_gap_y))
         * <=> bid_fp18 * 10^18 <= mark_fp18 * (10^18 - y_fp18)
         */
        tg::u256 lhs = tg::mul128_u256(static_cast<tg::u128>(bid), tg::SCALE_FP18);
        tg::u256 rhs = tg::mul128_u256(static_cast<tg::u128>(mark), tg::SCALE_FP18 - uy);
        *out_triggered = (tg::cmp_u256(lhs, rhs) <= 0) ? 1 : 0;
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_validate_and_size_order(
    const tg_order_check_in_t* input,
    tg_order_check_out_t* output
) {
    try {
        if (input == nullptr || output == nullptr) {
            return TG_ERR_INVALID;
        }
        tg::i128 qty = tg::unpack_i128(input->quantity);
        tg::i128 price = tg::unpack_i128(input->limit_price);
        tg::i128 fx = tg::unpack_i128(input->quote_krw);
        tg::i128 lot = tg::unpack_i128(input->lot_size);
        tg::i128 tick = tg::unpack_i128(input->tick_size);
        tg::i128 min_qty = tg::unpack_i128(input->min_quantity);
        tg::i128 min_notional = tg::unpack_i128(input->min_notional_krw);

        if (qty <= 0 || price <= 0 || fx <= 0 || lot <= 0 || tick <= 0 || min_qty < 0 || min_notional < 0) {
            return TG_ERR_INVALID;
        }
        if (!tg::in_fp18_range(qty) || !tg::in_fp18_range(price) || !tg::in_fp18_range(fx) ||
            !tg::in_fp18_range(lot) || !tg::in_fp18_range(tick) ||
            !tg::in_fp18_range(min_qty) || !tg::in_fp18_range(min_notional)) {
            return TG_FALLBACK_PRECISION;
        }

        tg::u128 uqty = static_cast<tg::u128>(qty);
        tg::u128 uprice = static_cast<tg::u128>(price);
        tg::u128 ufx = static_cast<tg::u128>(fx);
        tg::u128 ulot = static_cast<tg::u128>(lot);
        tg::u128 utick = static_cast<tg::u128>(tick);
        tg::u128 umin_qty = static_cast<tg::u128>(min_qty);
        tg::u128 umin_notional = static_cast<tg::u128>(min_notional);

        output->code = TG_ORDER_VALID;
        output->exact_notional_fp18 = 0;
        output->notional_krw = tg::pack_i128(0);

        if (input->require_integer_qty && (uqty % tg::SCALE_FP18) != 0) {
            output->code = TG_ORDER_FRACTIONAL_SHARES;
            return TG_OK;
        }
        if ((uqty % ulot) != 0) {
            output->code = TG_ORDER_OFF_LOT;
            return TG_OK;
        }
        if ((uprice % utick) != 0) {
            output->code = TG_ORDER_OFF_TICK;
            return TG_OK;
        }
        if (uqty < umin_qty) {
            output->code = TG_ORDER_BELOW_MIN_QTY;
            return TG_OK;
        }

        /* Exact u384 notional comparison:
         * (uqty * uprice * ufx) >= umin_notional * 10^36
         */
        tg::u256 qp = tg::mul128_u256(uqty, uprice);
        tg::u384 notional_scaled = tg::mul_u256_u128(qp, ufx);
        tg::u256 scale36 = tg::mul128_u256(tg::SCALE_FP18, tg::SCALE_FP18);
        tg::u384 min_scaled = tg::mul_u256_u128(scale36, umin_notional);

        if (tg::cmp_u384(notional_scaled, min_scaled) < 0) {
            output->code = TG_ORDER_BELOW_MIN_NOTIONAL;
            return TG_OK;
        }

        /* Also check exact fp18 representability of (qty * price * fx) / 10^36 */
        tg::u128 qp_fp18 = 0;
        tg::u128 rem1 = 0;
        if (tg::div_floor_u256_u128(qp, tg::SCALE_FP18, &qp_fp18, &rem1) && rem1 == 0) {
            tg::u256 qpf = tg::mul128_u256(qp_fp18, ufx);
            tg::u128 notional_fp18 = 0;
            tg::u128 rem2 = 0;
            if (tg::div_floor_u256_u128(qpf, tg::SCALE_FP18, &notional_fp18, &rem2) && rem2 == 0) {
                output->exact_notional_fp18 = 1;
                output->notional_krw = tg::pack_i128(static_cast<tg::i128>(notional_fp18));
            }
        }
        if (input->require_exact_notional_fp18 && !output->exact_notional_fp18) {
            return TG_FALLBACK_PRECISION;
        }
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_validate_book_levels(
    const tg_book_level_in_t* levels,
    int32_t num_levels,
    int32_t allow_crossed,
    tg_book_metrics_out_t* output
) {
    try {
        if (output == nullptr || num_levels < 0 || num_levels > 64 ||
            (num_levels > 0 && levels == nullptr)) {
            return TG_ERR_INVALID;
        }
        output->valid = 0;
        output->non_empty_levels = 0;
        output->has_spread = 0;
        output->has_imbalance = 0;
        output->spread = tg::pack_i128(0);
        output->imbalance_num = tg::pack_i128(0);
        output->imbalance_den = tg::pack_i128(0);

        bool missing_bid = false;
        bool missing_ask = false;
        bool have_prev_bid = false;
        bool have_prev_ask = false;
        tg::u128 prev_bid = 0;
        tg::u128 prev_ask = 0;
        tg::u128 best_bid = 0;
        tg::u128 best_ask = 0;
        bool have_best_bid = false;
        bool have_best_ask = false;
        tg::u128 bid_sum = 0;
        tg::u128 ask_sum = 0;
        int32_t non_empty = 0;

        for (int32_t i = 0; i < num_levels; ++i) {
            const tg_book_level_in_t& lv = levels[i];

            tg::i128 b_in = lv.has_bid ? tg::unpack_i128(lv.bid) : 0;
            tg::i128 bs_in = lv.has_bid_size ? tg::unpack_i128(lv.bid_size) : 0;
            tg::i128 a_in = lv.has_ask ? tg::unpack_i128(lv.ask) : 0;
            tg::i128 as_in = lv.has_ask_size ? tg::unpack_i128(lv.ask_size) : 0;

            if (b_in < 0 || bs_in < 0 || a_in < 0 || as_in < 0) {
                return TG_OK; /* invalid frame */
            }
            if (!tg::in_fp18_range(b_in) || !tg::in_fp18_range(bs_in) ||
                !tg::in_fp18_range(a_in) || !tg::in_fp18_range(as_in)) {
                return TG_FALLBACK_PRECISION;
            }

            /* _side semantics in data/kis_live.py:
             * if price is None or size is None or price == 0 or size == 0:
             *   forbid (price in (None, 0) and size is not None and size > 0)
             */
            bool bid_present = (lv.has_bid && lv.has_bid_size && b_in > 0 && bs_in > 0);
            if (!bid_present) {
                if ((!lv.has_bid || b_in == 0) && lv.has_bid_size && bs_in > 0) {
                    return TG_OK; /* invalid: positive size with zero/missing price */
                }
                missing_bid = true;
            } else {
                tg::u128 ub = static_cast<tg::u128>(b_in);
                tg::u128 ubs = static_cast<tg::u128>(bs_in);
                if (missing_bid || (have_prev_bid && !(ub < prev_bid))) {
                    return TG_OK;
                }
                prev_bid = ub;
                have_prev_bid = true;
                if (!have_best_bid) {
                    best_bid = ub;
                    have_best_bid = true;
                }
                if (tg::MAX_MAG_FP18 - bid_sum < ubs) {
                    return TG_FALLBACK_PRECISION;
                }
                bid_sum += ubs;
            }

            bool ask_present = (lv.has_ask && lv.has_ask_size && a_in > 0 && as_in > 0);
            if (!ask_present) {
                if ((!lv.has_ask || a_in == 0) && lv.has_ask_size && as_in > 0) {
                    return TG_OK;
                }
                missing_ask = true;
            } else {
                tg::u128 ua = static_cast<tg::u128>(a_in);
                tg::u128 uas = static_cast<tg::u128>(as_in);
                if (missing_ask || (have_prev_ask && !(ua > prev_ask))) {
                    return TG_OK;
                }
                prev_ask = ua;
                have_prev_ask = true;
                if (!have_best_ask) {
                    best_ask = ua;
                    have_best_ask = true;
                }
                if (tg::MAX_MAG_FP18 - ask_sum < uas) {
                    return TG_FALLBACK_PRECISION;
                }
                ask_sum += uas;
            }

            if (bid_present || ask_present) {
                ++non_empty;
            }
        }

        if (!allow_crossed && have_best_bid && have_best_ask && best_bid > best_ask) {
            return TG_OK;
        }

        output->valid = 1;
        output->non_empty_levels = non_empty;

        /* Best level spread if level 0 has both bid and ask */
        if (num_levels > 0 && have_best_bid && have_best_ask) {
            const tg_book_level_in_t& lv0 = levels[0];
            bool lv0_bid = (lv0.has_bid && lv0.has_bid_size && tg::unpack_i128(lv0.bid) > 0 && tg::unpack_i128(lv0.bid_size) > 0);
            bool lv0_ask = (lv0.has_ask && lv0.has_ask_size && tg::unpack_i128(lv0.ask) > 0 && tg::unpack_i128(lv0.ask_size) > 0);
            if (lv0_bid && lv0_ask) {
                tg::i128 sp = static_cast<tg::i128>(best_ask) - static_cast<tg::i128>(best_bid);
                output->has_spread = 1;
                output->spread = tg::pack_i128(sp);
            }
        }

        if (bid_sum + ask_sum > 0) {
            if (tg::MAX_MAG_FP18 - bid_sum < ask_sum) {
                return TG_FALLBACK_PRECISION;
            }
            tg::i128 num = static_cast<tg::i128>(bid_sum) - static_cast<tg::i128>(ask_sum);
            tg::i128 den = static_cast<tg::i128>(bid_sum + ask_sum);
            output->has_imbalance = 1;
            output->imbalance_num = tg::pack_i128(num);
            output->imbalance_den = tg::pack_i128(den);
        }

        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}
