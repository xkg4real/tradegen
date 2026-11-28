#include "tg_abi.h"
#include "tg_fp128.hpp"

#include <cstddef>
#include <cstdint>

extern "C" int32_t tg_kis_parse_caret_fields(
    const uint8_t* payload,
    size_t payload_len,
    int32_t expected_fields,
    int32_t max_field_len,
    int32_t* out_offsets,
    int32_t* out_lengths
) {
    try {
        if (expected_fields < 1 || max_field_len < 1 ||
            out_offsets == nullptr || out_lengths == nullptr ||
            (payload_len > 0 && payload == nullptr) ||
            payload_len > static_cast<size_t>(1 << 20)) {
            return TG_ERR_INVALID;
        }
        int32_t field_idx = 0;
        size_t field_start = 0;
        for (size_t i = 0; i < payload_len; ++i) {
            if (payload[i] == static_cast<uint8_t>('^')) {
                if (field_idx >= expected_fields) {
                    return TG_ERR_INVALID;
                }
                size_t flen = i - field_start;
                if (flen > static_cast<size_t>(max_field_len)) {
                    return TG_ERR_INVALID;
                }
                out_offsets[field_idx] = static_cast<int32_t>(field_start);
                out_lengths[field_idx] = static_cast<int32_t>(flen);
                ++field_idx;
                field_start = i + 1;
            }
        }
        /* Final trailing field after the last '^' (or entire payload if no '^') */
        if (field_idx != expected_fields - 1) {
            return TG_ERR_INVALID;
        }
        size_t last_len = payload_len - field_start;
        if (last_len > static_cast<size_t>(max_field_len)) {
            return TG_ERR_INVALID;
        }
        out_offsets[field_idx] = static_cast<int32_t>(field_start);
        out_lengths[field_idx] = static_cast<int32_t>(last_len);
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}

extern "C" int32_t tg_kis_window_metrics(
    const tg_kis_tick_in_t* ticks,
    int32_t num_ticks,
    int64_t now_us,
    int64_t window_us,
    int32_t trade_fresh,
    tg_kis_metrics_out_t* output
) {
    try {
        if (output == nullptr || num_ticks < 0 || num_ticks > 10000 ||
            window_us < 0 || (num_ticks > 0 && ticks == nullptr)) {
            return TG_ERR_INVALID;
        }
        output->sample_count = 0;
        output->has_window_return = 0;
        output->has_vwap = 0;
        output->vwap_hi_overflow = 0;
        output->ret_num = tg::pack_i128(0);
        output->ret_den = tg::pack_i128(0);
        for (int i = 0; i < 4; ++i) {
            output->vwap_num_words[i] = 0;
        }
        output->vwap_den_fp18 = tg::pack_i128(0);

        if (!trade_fresh || num_ticks == 0) {
            return TG_OK;
        }

        int32_t recent_count = 0;
        tg::u128 first_price = 0;
        tg::u128 last_price = 0;
        tg::u256 pv_sum{0, 0};
        tg::u128 vol_sum = 0;

        for (int32_t i = 0; i < num_ticks; ++i) {
            const tg_kis_tick_in_t& t = ticks[i];
            /* Validate price/size range even if filtered */
            tg::i128 p_in = tg::unpack_i128(t.price);
            if (p_in <= 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(p_in)) {
                return TG_FALLBACK_PRECISION;
            }
            tg::u128 sz = 0;
            if (t.has_size) {
                tg::i128 s_in = tg::unpack_i128(t.size);
                if (s_in < 0) {
                    return TG_ERR_INVALID;
                }
                if (!tg::in_fp18_range(s_in)) {
                    return TG_FALLBACK_PRECISION;
                }
                sz = static_cast<tg::u128>(s_in);
            }

            /* recent filter in data/kis_live.py:
             * tick.delay_seconds == 0 and tick.state not in ("indicative", "unknown")
             * and 0 <= now - tick.observed_at <= WINDOW_SECONDS and tick.received_at <= now
             */
            if (t.delay_seconds != 0 || t.state_code == 3) {
                continue;
            }
            if (now_us < t.observed_us || (now_us - t.observed_us) > window_us || t.received_us > now_us) {
                continue;
            }

            tg::u128 up = static_cast<tg::u128>(p_in);
            if (recent_count == 0) {
                first_price = up;
            }
            last_price = up;
            ++recent_count;

            /* weighted filter: tick.size is not None and tick.size > 0 and tick.state == "reported" (state_code == 0) */
            if (t.has_size && sz > 0 && t.state_code == 0) {
                if (tg::MAX_MAG_FP18 - vol_sum < sz) {
                    return TG_FALLBACK_PRECISION;
                }
                vol_sum += sz;
                tg::u256 prod = tg::mul128_u256(up, sz);
                if (!tg::add_u256(pv_sum, prod, &pv_sum)) {
                    return TG_FALLBACK_PRECISION;
                }
            }
        }

        output->sample_count = recent_count;
        if (recent_count >= 2) {
            output->has_window_return = 1;
            tg::i128 diff = static_cast<tg::i128>(last_price) - static_cast<tg::i128>(first_price);
            output->ret_num = tg::pack_i128(diff);
            output->ret_den = tg::pack_i128(static_cast<tg::i128>(first_price));
        }
        if (vol_sum > 0) {
            output->has_vwap = 1;
            output->vwap_num_words[0] = static_cast<uint64_t>(pv_sum.lo);
            output->vwap_num_words[1] = static_cast<uint64_t>(pv_sum.lo >> 64);
            output->vwap_num_words[2] = static_cast<uint64_t>(pv_sum.hi);
            output->vwap_num_words[3] = static_cast<uint64_t>(pv_sum.hi >> 64);
            output->vwap_den_fp18 = tg::pack_i128(static_cast<tg::i128>(vol_sum));
        }
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}
