#ifndef TRADEGEN_FAST_TG_ABI_H
#define TRADEGEN_FAST_TG_ABI_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TG_ABI_VERSION 1u

/* Status codes */
#define TG_OK 0
#define TG_FALLBACK_PRECISION 1
#define TG_ERR_INVALID (-1)
#define TG_ERR_NEGATIVE_STATE (-2)
#define TG_ERR_CAPACITY (-3)

/* Fixed-point signed 128-bit integer scaled by 10^18 (two's complement hi:lo). */
typedef struct tg_i128_t {
    int64_t hi;
    uint64_t lo;
} tg_i128_t;

/* HP-1: Multi-coin continuous interval fold + FIFO lot reducer */
#define TG_EVENT_MARK 0
#define TG_EVENT_BUY 1
#define TG_EVENT_SELL 2

typedef struct tg_fifo_lot_t {
    int32_t market_idx;
    int32_t reserved;
    tg_i128_t quantity;
    tg_i128_t cost_krw;
} tg_fifo_lot_t;

typedef struct tg_interval_event_t {
    int64_t at_ms;
    int32_t kind;        /* TG_EVENT_MARK, TG_EVENT_BUY, TG_EVENT_SELL */
    int32_t market_idx;  /* 0 .. num_markets - 1 */
    tg_i128_t quantity;
    tg_i128_t price;
    tg_i128_t fee_krw;
} tg_interval_event_t;

typedef struct tg_equity_point_t {
    tg_i128_t equity_krw;
    tg_i128_t realized_net_krw;
} tg_equity_point_t;

typedef struct tg_fold_output_t {
    tg_i128_t closing_equity_krw;
    tg_i128_t min_equity_krw;
    tg_i128_t max_equity_krw;
    tg_i128_t realized_net_krw;
    tg_i128_t closing_cash_krw;
    tg_i128_t closing_units[4];
    tg_i128_t closing_marks[4];
} tg_fold_output_t;

uint32_t tg_abi_version(void);

int32_t tg_fold_continuous_interval(
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
);

/* HP-2 & HP-4: Bid-gap check, order validation & sizing, book level validation */
int32_t tg_check_bid_gap(
    const tg_i128_t* best_bid,
    const tg_i128_t* mark_price,
    const tg_i128_t* bid_gap_y,
    int32_t has_best_bid,
    int32_t has_y,
    int32_t* out_triggered
);

typedef struct tg_order_check_in_t {
    tg_i128_t quantity;
    tg_i128_t limit_price;
    tg_i128_t quote_krw;
    tg_i128_t lot_size;
    tg_i128_t tick_size;
    tg_i128_t min_quantity;
    tg_i128_t min_notional_krw;
    int32_t require_integer_qty;
    int32_t require_exact_notional_fp18;
} tg_order_check_in_t;

#define TG_ORDER_VALID 0
#define TG_ORDER_FRACTIONAL_SHARES 1
#define TG_ORDER_OFF_LOT 2
#define TG_ORDER_OFF_TICK 3
#define TG_ORDER_BELOW_MIN_QTY 4
#define TG_ORDER_BELOW_MIN_NOTIONAL 5

typedef struct tg_order_check_out_t {
    int32_t code;
    int32_t exact_notional_fp18;
    tg_i128_t notional_krw;
} tg_order_check_out_t;

int32_t tg_validate_and_size_order(
    const tg_order_check_in_t* input,
    tg_order_check_out_t* output
);

typedef struct tg_book_level_in_t {
    int32_t has_bid;
    int32_t has_bid_size;
    int32_t has_ask;
    int32_t has_ask_size;
    tg_i128_t bid;
    tg_i128_t bid_size;
    tg_i128_t ask;
    tg_i128_t ask_size;
} tg_book_level_in_t;

typedef struct tg_book_metrics_out_t {
    int32_t valid;
    int32_t non_empty_levels;
    int32_t has_spread;
    int32_t has_imbalance;
    tg_i128_t spread;
    tg_i128_t imbalance_num;
    tg_i128_t imbalance_den;
} tg_book_metrics_out_t;

int32_t tg_validate_book_levels(
    const tg_book_level_in_t* levels,
    int32_t num_levels,
    int32_t allow_crossed,
    tg_book_metrics_out_t* output
);

/* HP-3: Strategy & carry evaluation kernels */
int32_t tg_ma_crossover(
    const tg_i128_t* marks,
    int32_t num_marks,
    int32_t fast_window,
    int32_t slow_window,
    int32_t* out_above
);

#define TG_FLAG_UNFLAGGED 0
#define TG_FLAG_WARNING 1
#define TG_FLAG_CAUTION 2
#define TG_FLAG_UNKNOWN 3
#define TG_FLAG_ABSENT 4

typedef struct tg_momentum_candidate_t {
    int32_t coin_id;
    int32_t flag_code;
    int32_t has_now_price;
    int32_t has_lag_price;
    tg_i128_t now_price;
    tg_i128_t lag_price;
} tg_momentum_candidate_t;

int32_t tg_universe_momentum_top1(
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
);

typedef struct tg_carry_bar_in_t {
    tg_i128_t bid;
    tg_i128_t ask;
    tg_i128_t mark;
    int64_t observed_us;
} tg_carry_bar_in_t;

#define TG_DECISION_LONG 0
#define TG_DECISION_CASH 1
#define TG_DECISION_WARMUP 2
#define TG_DECISION_UNAVAILABLE 3

typedef struct tg_carry_decision_in_t {
    int32_t state;
    int32_t reserved;
    tg_i128_t target_fraction;
    int64_t decided_us;
} tg_carry_decision_in_t;

typedef struct tg_carry_fill_out_t {
    int32_t bar_index;
    int32_t action; /* 1 = entry, 2 = exit */
    tg_i128_t quantity;
    tg_i128_t price_quote;
    tg_i128_t fee_quote;
} tg_carry_fill_out_t;

typedef struct tg_carry_sim_out_t {
    int32_t completed_roundtrips;
    int32_t rejected_small_orders;
    int32_t num_fills;
    int32_t num_lots;
    tg_i128_t terminal_cash;
    tg_i128_t terminal_units;
    tg_i128_t terminal_basis;
    tg_i128_t realized_net_profit;
    tg_i128_t total_fees;
    tg_i128_t turnover;
} tg_carry_sim_out_t;

int32_t tg_simulate_carry(
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
);

/* HP-5: KIS market-data frame scanner & window metrics */
int32_t tg_kis_parse_caret_fields(
    const uint8_t* payload,
    size_t payload_len,
    int32_t expected_fields,
    int32_t max_field_len,
    int32_t* out_offsets,
    int32_t* out_lengths
);

typedef struct tg_kis_tick_in_t {
    int64_t observed_us;
    int64_t received_us;
    int32_t delay_seconds;
    int32_t state_code; /* 0 = reported, 1 = indicator, 2 = delayed, 3 = indicative/unknown */
    int32_t has_size;
    int32_t reserved;
    tg_i128_t price;
    tg_i128_t size;
} tg_kis_tick_in_t;

typedef struct tg_kis_metrics_out_t {
    int32_t sample_count;
    int32_t has_window_return;
    int32_t has_vwap;
    int32_t vwap_hi_overflow;
    tg_i128_t ret_num;
    tg_i128_t ret_den;
    uint64_t vwap_num_words[4]; /* little-endian u256 numerator of sum(price * size) */
    tg_i128_t vwap_den_fp18;    /* sum(size) in fp18 (multiply by 10^18 to match u256 scale) */
} tg_kis_metrics_out_t;

int32_t tg_kis_window_metrics(
    const tg_kis_tick_in_t* ticks,
    int32_t num_ticks,
    int64_t now_us,
    int64_t window_us,
    int32_t trade_fresh,
    tg_kis_metrics_out_t* output
);

/* HP-6a: Odds engine IEEE-754 f64 path state machine (0-ULP match with core/odds/simulate.py:_paths) */
#define TG_BOOK_CRYPTO_OR_US 0
#define TG_BOOK_KRX_ETF 1
#define TG_BOOK_KRX_STOCK 2

#define TG_SIZING_FLOOR_SAFE 0
#define TG_SIZING_STOP_BASED 1

#define TG_FRAC_FIXED 0
#define TG_FRAC_KELLY 1
#define TG_FRAC_BOLD 2

typedef struct tg_odds_spec_in_t {
    int32_t n_paths;
    int32_t n_checks;
    int32_t moonshot;
    int32_t has_bracket;
    int32_t sizing_kind;
    int32_t fraction_kind;
    int32_t has_fstar;
    int32_t has_cap_krw;
    int32_t has_delist_h;
    int32_t book_kind;
    int32_t n_ladder_rows;
    int32_t record_brackets;
    double w0;
    double target;
    double floor_val;
    double daily_loss;
    double mult;
    double take_profit;
    double stop;
    double fraction_val;
    double fstar;
    double cap_krw;
    double delist_h;
    double table_bp;
    double commission_bp;
    double quote_krw;
    double lot;
    double min_krw;
    double phi_buy;
    double phi_sell;
    double carry_mult;
    double cost_stress;
} tg_odds_spec_in_t;

int32_t tg_odds_run_paths_f64(
    const tg_odds_spec_in_t* spec,
    const double* ladder_starts,
    const double* ladder_steps,
    const int32_t* check_close,
    const int32_t* check_new_seoul_day,
    const int32_t* check_banded,
    const int32_t* check_can_enter_date,
    const int32_t* check_force_exit_date,
    const double* check_sell_tax_bp,
    const double* prices,   /* n_checks * n_paths row-major */
    const double* d_edges,  /* n_checks * n_paths if banded check else scalar per check */
    const double* u_edges,  /* n_checks * n_paths if banded check else scalar per check */
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
);

/* HP-6b: Adaptive bid-gap moving-block Monte Carlo kernel (BR-26) */
typedef struct tg_bid_gap_mc_out_t {
    double favorable_prob;
    double adverse_prob;
    double mean_net_return;
    double p05_net_return;
    double p95_net_return;
} tg_bid_gap_mc_out_t;

int32_t tg_adaptive_bid_gap_mc(
    const double* returns,
    int32_t n_obs,
    int32_t n_paths,
    int32_t horizon,
    int32_t block_len,
    double cost_hurdle,
    uint64_t seed,
    tg_bid_gap_mc_out_t* output
);

#ifdef __cplusplus
}
#endif

#endif /* TRADEGEN_FAST_TG_ABI_H */
