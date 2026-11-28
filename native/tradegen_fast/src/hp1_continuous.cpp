#include "tg_abi.h"
#include "tg_fp128.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace {

using tg::i128;
using tg::u128;
using tg::u256;

struct LotState {
    u128 qty;
    u128 cost;
};

bool compute_equity(
    i128 cash,
    int32_t num_markets,
    const u128* units,
    const u128* marks,
    i128* out_eq,
    int32_t* err_code
) noexcept {
    if (cash < 0 || !tg::in_fp18_range(cash)) {
        *err_code = (cash < 0) ? TG_ERR_NEGATIVE_STATE : TG_FALLBACK_PRECISION;
        return false;
    }
    i128 total = cash;
    for (int32_t m = 0; m < num_markets; ++m) {
        if (units[m] == 0) {
            continue;
        }
        u128 val = 0;
        if (!tg::mul_fp18_exact(units[m], marks[m], &val)) {
            *err_code = TG_FALLBACK_PRECISION;
            return false;
        }
        if (!tg::add_checked_fp18(total, static_cast<i128>(val), &total)) {
            *err_code = TG_FALLBACK_PRECISION;
            return false;
        }
    }
    if (total <= 0) {
        *err_code = TG_ERR_NEGATIVE_STATE;
        return false;
    }
    *out_eq = total;
    return true;
}

} /* namespace */

extern "C" uint32_t tg_abi_version(void) {
    return TG_ABI_VERSION;
}

extern "C" int32_t tg_fold_continuous_interval(
    int32_t num_markets,
    const tg_i128_t* opening_cash_krw,
    const tg_i128_t* opening_units,
    const tg_i128_t* opening_marks,
    const tg_i128_t* opening_realized_krw,
    const tg_fifo_lot_t* opening_lots,
    int32_t num_opening_lots,
    const tg_interval_event_t* events,
    int32_t num_events,
    int32_t conservative_ms,
    tg_fold_output_t* out_summary,
    tg_equity_point_t* out_points,
    int32_t max_out_points,
    tg_fifo_lot_t* out_lots,
    int32_t max_out_lots,
    int32_t* out_num_lots
) {
    try {
        if (num_markets < 1 || num_markets > 4 || opening_cash_krw == nullptr ||
            opening_units == nullptr || opening_marks == nullptr ||
            opening_realized_krw == nullptr || out_summary == nullptr ||
            num_opening_lots < 0 || num_events < 0 ||
            (num_opening_lots > 0 && opening_lots == nullptr) ||
            (num_events > 0 && events == nullptr)) {
            return TG_ERR_INVALID;
        }
        if (out_points != nullptr && max_out_points < num_events + 2) {
            return TG_ERR_CAPACITY;
        }

        i128 cash = tg::unpack_i128(*opening_cash_krw);
        i128 realized = tg::unpack_i128(*opening_realized_krw);
        if (cash < 0) {
            return TG_ERR_NEGATIVE_STATE;
        }
        if (!tg::in_fp18_range(cash) || !tg::in_fp18_range(realized)) {
            return TG_FALLBACK_PRECISION;
        }

        u128 units[4]{0, 0, 0, 0};
        u128 marks[4]{0, 0, 0, 0};
        for (int32_t m = 0; m < num_markets; ++m) {
            i128 u = tg::unpack_i128(opening_units[m]);
            i128 mk = tg::unpack_i128(opening_marks[m]);
            if (u < 0 || mk <= 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(u) || !tg::in_fp18_range(mk)) {
                return TG_FALLBACK_PRECISION;
            }
            units[m] = static_cast<u128>(u);
            marks[m] = static_cast<u128>(mk);
        }

        std::vector<LotState> lots[4];
        size_t head_idx[4]{0, 0, 0, 0};
        u128 lot_sum[4]{0, 0, 0, 0};

        for (int32_t i = 0; i < num_opening_lots; ++i) {
            int32_t m = opening_lots[i].market_idx;
            if (m < 0 || m >= num_markets) {
                return TG_ERR_INVALID;
            }
            i128 lq = tg::unpack_i128(opening_lots[i].quantity);
            i128 lc = tg::unpack_i128(opening_lots[i].cost_krw);
            if (lq <= 0 || lc < 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(lq) || !tg::in_fp18_range(lc)) {
                return TG_FALLBACK_PRECISION;
            }
            u128 uq = static_cast<u128>(lq);
            if (tg::MAX_MAG_FP18 - lot_sum[m] < uq) {
                return TG_FALLBACK_PRECISION;
            }
            lot_sum[m] += uq;
            lots[m].push_back(LotState{uq, static_cast<u128>(lc)});
        }

        for (int32_t m = 0; m < num_markets; ++m) {
            if (lot_sum[m] != units[m]) {
                return TG_ERR_INVALID;
            }
        }

        int32_t err_code = TG_OK;
        i128 current_eq = 0;
        if (!compute_equity(cash, num_markets, units, marks, &current_eq, &err_code)) {
            return err_code;
        }
        i128 min_eq = current_eq;
        i128 max_eq = current_eq;

        if (out_points != nullptr) {
            out_points[0].equity_krw = tg::pack_i128(current_eq);
            out_points[0].realized_net_krw = tg::pack_i128(realized);
        }

        auto apply_fill = [&](const tg_interval_event_t& ev) -> int32_t {
            int32_t m = ev.market_idx;
            if (m < 0 || m >= num_markets) {
                return TG_ERR_INVALID;
            }
            i128 q_in = tg::unpack_i128(ev.quantity);
            i128 p_in = tg::unpack_i128(ev.price);
            i128 f_in = tg::unpack_i128(ev.fee_krw);
            if (q_in <= 0 || p_in <= 0 || f_in < 0) {
                return TG_ERR_INVALID;
            }
            if (!tg::in_fp18_range(q_in) || !tg::in_fp18_range(p_in) || !tg::in_fp18_range(f_in)) {
                return TG_FALLBACK_PRECISION;
            }
            u128 qty = static_cast<u128>(q_in);
            u128 price = static_cast<u128>(p_in);
            u128 fee = static_cast<u128>(f_in);

            u128 notional = 0;
            if (!tg::mul_fp18_exact(qty, price, &notional)) {
                return TG_FALLBACK_PRECISION;
            }

            if (ev.kind == TG_EVENT_BUY) {
                i128 outlay = 0;
                if (!tg::add_checked_fp18(static_cast<i128>(notional), static_cast<i128>(fee), &outlay)) {
                    return TG_FALLBACK_PRECISION;
                }
                i128 next_cash = 0;
                if (!tg::sub_checked_fp18(cash, outlay, &next_cash)) {
                    return TG_FALLBACK_PRECISION;
                }
                if (next_cash < 0) {
                    return TG_ERR_NEGATIVE_STATE;
                }
                if (tg::MAX_MAG_FP18 - units[m] < qty) {
                    return TG_FALLBACK_PRECISION;
                }
                cash = next_cash;
                units[m] += qty;
                lots[m].push_back(LotState{qty, static_cast<u128>(outlay)});
                return TG_OK;
            }

            if (ev.kind == TG_EVENT_SELL) {
                if (units[m] < qty) {
                    return TG_ERR_NEGATIVE_STATE;
                }
                i128 movement = 0;
                if (!tg::sub_checked_fp18(static_cast<i128>(notional), static_cast<i128>(fee), &movement)) {
                    return TG_FALLBACK_PRECISION;
                }
                i128 next_cash = 0;
                if (!tg::add_checked_fp18(cash, movement, &next_cash)) {
                    return TG_FALLBACK_PRECISION;
                }
                if (next_cash < 0) {
                    return TG_ERR_NEGATIVE_STATE;
                }

                u128 needed = qty;
                u128 cost_released = 0;
                while (needed > 0) {
                    if (head_idx[m] >= lots[m].size()) {
                        return TG_ERR_NEGATIVE_STATE;
                    }
                    LotState& front = lots[m][head_idx[m]];
                    u128 taken = (needed < front.qty) ? needed : front.qty;
                    u128 alloc = 0;
                    if (!tg::fifo_alloc_cost_fp18(front.cost, taken, front.qty, &alloc)) {
                        return TG_FALLBACK_PRECISION;
                    }
                    if (tg::MAX_MAG_FP18 - cost_released < alloc) {
                        return TG_FALLBACK_PRECISION;
                    }
                    cost_released += alloc;
                    needed -= taken;
                    if (taken == front.qty) {
                        ++head_idx[m];
                    } else {
                        front.qty -= taken;
                        front.cost -= alloc;
                    }
                }

                i128 profit = 0;
                if (!tg::sub_checked_fp18(movement, static_cast<i128>(cost_released), &profit)) {
                    return TG_FALLBACK_PRECISION;
                }
                i128 next_realized = 0;
                if (!tg::add_checked_fp18(realized, profit, &next_realized)) {
                    return TG_FALLBACK_PRECISION;
                }
                cash = next_cash;
                units[m] -= qty;
                realized = next_realized;
                return TG_OK;
            }

            return TG_ERR_INVALID;
        };

        if (!conservative_ms) {
            for (int32_t i = 0; i < num_events; ++i) {
                const tg_interval_event_t& ev = events[i];
                if (i > 0 && ev.at_ms < events[i - 1].at_ms) {
                    return TG_ERR_INVALID;
                }
                if (ev.kind == TG_EVENT_MARK) {
                    int32_t m = ev.market_idx;
                    if (m < 0 || m >= num_markets) {
                        return TG_ERR_INVALID;
                    }
                    i128 mk = tg::unpack_i128(ev.price);
                    if (mk <= 0) {
                        return TG_ERR_INVALID;
                    }
                    if (!tg::in_fp18_range(mk)) {
                        return TG_FALLBACK_PRECISION;
                    }
                    marks[m] = static_cast<u128>(mk);
                } else {
                    int32_t rc = apply_fill(ev);
                    if (rc != TG_OK) {
                        return rc;
                    }
                }
                if (!compute_equity(cash, num_markets, units, marks, &current_eq, &err_code)) {
                    return err_code;
                }
                if (current_eq < min_eq) {
                    min_eq = current_eq;
                }
                if (current_eq > max_eq) {
                    max_eq = current_eq;
                }
                if (out_points != nullptr) {
                    out_points[i + 1].equity_krw = tg::pack_i128(current_eq);
                    out_points[i + 1].realized_net_krw = tg::pack_i128(realized);
                }
            }
        } else {
            /* BR-4 conservative intra-millisecond evaluation:
             * Within each millisecond group, prints have unordered tie-breaking relative to
             * other prints and fills at the same millisecond. Evaluate min/max mark envelope
             * against holdings BEFORE fills and AFTER each fill at that millisecond.
             */
            int32_t idx = 0;
            while (idx < num_events) {
                int64_t ms = events[idx].at_ms;
                if (idx > 0 && ms < events[idx - 1].at_ms) {
                    return TG_ERR_INVALID;
                }
                int32_t end_idx = idx;
                while (end_idx < num_events && events[end_idx].at_ms == ms) {
                    ++end_idx;
                }

                u128 min_marks[4] = {marks[0], marks[1], marks[2], marks[3]};
                u128 max_marks[4] = {marks[0], marks[1], marks[2], marks[3]};
                u128 last_marks[4] = {marks[0], marks[1], marks[2], marks[3]};

                for (int32_t k = idx; k < end_idx; ++k) {
                    const tg_interval_event_t& ev = events[k];
                    if (ev.kind == TG_EVENT_MARK) {
                        int32_t m = ev.market_idx;
                        if (m < 0 || m >= num_markets) {
                            return TG_ERR_INVALID;
                        }
                        i128 mk = tg::unpack_i128(ev.price);
                        if (mk <= 0) {
                            return TG_ERR_INVALID;
                        }
                        if (!tg::in_fp18_range(mk)) {
                            return TG_FALLBACK_PRECISION;
                        }
                        u128 umk = static_cast<u128>(mk);
                        if (umk < min_marks[m]) {
                            min_marks[m] = umk;
                        }
                        if (umk > max_marks[m]) {
                            max_marks[m] = umk;
                        }
                        last_marks[m] = umk;
                    }
                }

                auto update_envelope = [&]() -> int32_t {
                    i128 lo_eq = 0;
                    i128 hi_eq = 0;
                    if (!compute_equity(cash, num_markets, units, min_marks, &lo_eq, &err_code)) {
                        return err_code;
                    }
                    if (!compute_equity(cash, num_markets, units, max_marks, &hi_eq, &err_code)) {
                        return err_code;
                    }
                    if (lo_eq < min_eq) {
                        min_eq = lo_eq;
                    }
                    if (hi_eq > max_eq) {
                        max_eq = hi_eq;
                    }
                    return TG_OK;
                };

                int32_t env_rc = update_envelope();
                if (env_rc != TG_OK) {
                    return env_rc;
                }

                for (int32_t k = idx; k < end_idx; ++k) {
                    const tg_interval_event_t& ev = events[k];
                    if (ev.kind == TG_EVENT_MARK) {
                        marks[ev.market_idx] = static_cast<u128>(tg::unpack_i128(ev.price));
                    } else {
                        int32_t rc = apply_fill(ev);
                        if (rc != TG_OK) {
                            return rc;
                        }
                        env_rc = update_envelope();
                        if (env_rc != TG_OK) {
                            return env_rc;
                        }
                    }
                    if (!compute_equity(cash, num_markets, units, marks, &current_eq, &err_code)) {
                        return err_code;
                    }
                    if (out_points != nullptr) {
                        out_points[k + 1].equity_krw = tg::pack_i128(current_eq);
                        out_points[k + 1].realized_net_krw = tg::pack_i128(realized);
                    }
                }

                for (int32_t m = 0; m < num_markets; ++m) {
                    marks[m] = last_marks[m];
                }
                if (!compute_equity(cash, num_markets, units, marks, &current_eq, &err_code)) {
                    return err_code;
                }
                if (current_eq < min_eq) {
                    min_eq = current_eq;
                }
                if (current_eq > max_eq) {
                    max_eq = current_eq;
                }
                idx = end_idx;
            }
        }

        if (out_points != nullptr) {
            out_points[num_events + 1].equity_krw = tg::pack_i128(current_eq);
            out_points[num_events + 1].realized_net_krw = tg::pack_i128(realized);
        }

        int32_t total_remaining_lots = 0;
        for (int32_t m = 0; m < num_markets; ++m) {
            total_remaining_lots += static_cast<int32_t>(lots[m].size() - head_idx[m]);
        }
        if (out_num_lots != nullptr) {
            *out_num_lots = total_remaining_lots;
        }
        if (out_lots != nullptr) {
            if (max_out_lots < total_remaining_lots) {
                return TG_ERR_CAPACITY;
            }
            int32_t pos = 0;
            for (int32_t m = 0; m < num_markets; ++m) {
                for (size_t j = head_idx[m]; j < lots[m].size(); ++j) {
                    out_lots[pos].market_idx = m;
                    out_lots[pos].reserved = 0;
                    out_lots[pos].quantity = tg::pack_i128(static_cast<i128>(lots[m][j].qty));
                    out_lots[pos].cost_krw = tg::pack_i128(static_cast<i128>(lots[m][j].cost));
                    ++pos;
                }
            }
        }

        out_summary->closing_equity_krw = tg::pack_i128(current_eq);
        out_summary->min_equity_krw = tg::pack_i128(min_eq);
        out_summary->max_equity_krw = tg::pack_i128(max_eq);
        out_summary->realized_net_krw = tg::pack_i128(realized);
        out_summary->closing_cash_krw = tg::pack_i128(cash);
        for (int32_t m = 0; m < 4; ++m) {
            out_summary->closing_units[m] = tg::pack_i128(m < num_markets ? static_cast<i128>(units[m]) : 0);
            out_summary->closing_marks[m] = tg::pack_i128(m < num_markets ? static_cast<i128>(marks[m]) : 0);
        }
        return TG_OK;
    } catch (...) {
        return TG_ERR_INVALID;
    }
}
