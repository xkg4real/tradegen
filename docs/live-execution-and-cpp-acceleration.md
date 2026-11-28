# Controlled Live Execution, Protective Hold (A2), and C++20 Native Acceleration

## 1. Architecture Overview

This document describes the controlled live Upbit KRW spot execution architecture, Blocker 1 Approach A continuous interval valuation, BR-10 stale-ticker bid-gap protection (`Y`), Standing Amendment A2 durable Protective Hold, the D14-clean `CurrentPlanner`, and the `native/tradegen_fast` C++20 low-latency native engine.

### Key Modules

| Layer | Module | Responsibility |
| --- | --- | --- |
| E1 Inquiry | `execution/upbit_inquiry.py`, `execution/transport.py` | Read-only `/v1/trades/ticks` and `/v1/order` inquiry endpoints under `READ_CAPTURE_ENDPOINTS` allowlist. |
| Account Evidence | `execution_accounts/upbit_collector.py`, `execution_accounts/provider.py`, `execution_accounts/continuous.py` | Approach A trade-window backward pagination, order-detail fee reconciliation, BR-10 best-bid attachment & exact rational bid-gap check, and `<= 4`-market continuous equity fold. |
| Interval Producer | `execution_launch/account_interval.py` | Held-position continuous interval framing and deterministic `[prev, boundary)` / `[boundary, curr)` splitting across `22:00 KST` recovery and `00:00 KST` midnight boundaries. |
| Compliance & Signer | `core/compliance/owner.py`, `tools/signer/sign.py` | D12 fold semantics and CLI signing for `bid_gap_set`, `bid_gap_clear`, and `protective_terms_set` (`trailing_stop_x`, `halt_margin_krw`, `daily_margin_krw`). |
| Control & Orders | `execution_control/risk.py`, `execution_control/controller.py`, `execution_orders/transport.py` | `BID_GAP_BLOCKED` entry latch, `PERSISTENT_HALT` enforcement, `halt_line` / `daily_limit` exposure, and `VenueOrderTransport` single-attempt authenticated dispatch. |
| Runtime & A2 Hold | `execution_launch/runner.py`, `execution_launch/coordinator.py`, `execution_launch/protective_store.py` | `"controlled"` mode order boundary (`gtc` / `ioc`) and Standing Amendment A2 Protective Hold state transitions. |
| Owner Composition | `tools/owner/planner.py`, `tools/owner/live.py`, `tools/owner/launch.py` | Exclusive `live.lock`, separate order vs inquiry credentials, D14-clean `CurrentPlanner`, and console commands (`bootstrap`, `odds`, `prepare`, `run`, `status`, `refresh-terms`, `cancel-all`, `exit`, `stop`, `disarm`, `close`). |
| Native Engine | `native/tradegen_fast/`, `core/compliance/native_accel.py`, `data/_kis_native.py` | Zero-syscall C++20 shared library (`libtradegen_fast.so`, `TG_ABI_VERSION = 1`) with SHA-256 + `code_files()` manifest verification and `10^-18` fixed-point (`__int128` / `u256` / `u384` / `u512`) exact arithmetic. |

---

## 2. Safety & Accounting Invariants

1. **Blocker 1 Approach A & Multi-Coin Continuous Valuation**:
   - `collect_trade_window` pages `/v1/trades/ticks` backwards by `min_seq_id - 1`, deduplicating `sequential_id` and failing closed (`UPBIT_TRADE_COVERAGE_INCOMPLETE`) if `max_pages` or `max_prints` is reached before `timestamp_ms < start_ms` or `anchor_trade_id` is proven.
   - `collect_order_fills` reconciles `executed_volume == sum(trades.volume)` on `/v1/order` and allocates `paid_fee` at `10^-18` (`ROUND_DOWN`) with exact final-trade residual conservation.
   - `value_trade_paths` folds up to `4` held KRW spot markets (`<= 12,000` prints, `<= 512` fills) with exact FIFO lot cost release and conservative intra-millisecond `[min_equity_krw, max_equity_krw]` bounds.
2. **BR-10 Stale-Trade Bid-Gap `Y` & D12 Fold**:
   - When a held coin's last trade is older than `30s` (`trade_time <= received`), `_collect_marks` attaches `/v1/orderbook` level-0 `best_bid` (`<= 10s` old) without overwriting `mark_price = trade_price`.
   - `provider.py` evaluates `Fraction(best_bid) <= Fraction(mark_price) * (1 - Fraction(bid_gap_y))` (or `best_bid is None` / `bid_gap_y is None`), latching `BID_GAP_BLOCKED` on new entries while keeping reducing exits open.
   - Under D12, tightening (`y_new < y_cur`, smaller `trailing_stop_x`, larger `halt_margin_krw` / `daily_margin_krw`) applies immediately at `effective_from`, whereas initial settings or loosenings take effect only on a subsequent `Asia/Seoul` calendar day.
3. **Standing Amendment A2 (Protective Hold)**:
   - **Zero Automatic Sales on Faults/Boundaries**: `missed_slot`, `missed_boundary`, `runner_error`, `clock_rollback`, `window.end` (`deadline`), process `restart`, or missing inputs **never** trigger an automatic sale; they cancel resting app `buy` orders and enter/maintain Protective Hold.
   - **Four Exclusive Protective Sell Triggers (`S`, `W`, `T`, `B`)**:
     - `S`: Genuine strategy cash or other-coin rotation verdict.
     - `W`: Market flag `warning`, `unknown`, or `absent` on the held coin.
     - `T`: Signed trailing stop $X$ breached from post-stop high $h$.
     - `B`: Signed pre-halt margin $M$ or daily-loss margin $M_d$ breached on flow-adjusted equity $Eq_{\text{adj}} = Eq - R_w$.
   - **Manual Coin Isolation**: Protective sells are strictly capped at reconciled app-owned holdings $q_{\text{app}}$ acquired during the deployment window; pre-existing manual coins are never sold by A2.
   - **`PERSISTENT_HALT` & A2 N2**: Under `PERSISTENT_HALT`, no protective sell is placed and resting app orders are cancelled, while explicit owner-tagged `exit` orders (`submit_owner_exit` / console `exit`) are preserved unless explicitly cancelled by the owner (`cancel-all` / `cancel`).
4. **Live Process & Key Isolation**:
   - `tools/owner/live.py` acquires an exclusive non-blocking OS lock (`live.lock` under `TRADEGEN_HOME`), verifies `UPBIT_ORDER_ACCESS_KEY` / `UPBIT_ORDER_SECRET_KEY` are configured and strictly distinct from `UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY` (`LIVE_ORDER_INQUIRY_KEY_COLLISION` on reuse), and disarms any leftover armed session on startup.

---

## 3. Operator CLI Reference

### Offline Signer (`tools/signer/sign.py`)

```bash
# Configure BR-10 bid-gap threshold Y in (0, 0.05]
python -m tools.signer.sign --key OWNER_KEY.pem bid-gap-set \
  --scope ACCT_SCOPE --y 0.02 --effective-from 2026-11-27T00:00:00Z

# Clear BR-10 bid-gap threshold
python -m tools.signer.sign --key OWNER_KEY.pem bid-gap-clear \
  --scope ACCT_SCOPE --reason "spread normalized"

# Configure Standing Amendment A2 protective terms
python -m tools.signer.sign --key OWNER_KEY.pem protective-terms-set \
  --scope ACCT_SCOPE --trailing-stop-x 0.04 \
  --halt-margin-krw 50000 --daily-margin-krw 25000
```

### Native Engine Build (`native/tradegen_fast/build_native.py`)

```bash
python native/tradegen_fast/build_native.py
```

### Controlled Live Launcher (`tools/owner/live.py`)

```bash
python -m tools.owner.live --config PRIVATE_LIVE_CONFIG.json
# Console line commands:
#   bootstrap | odds | prepare | run | status | refresh-terms
#   cancel-all | exit [QUANTITY [LIMIT_PRICE]] | stop | disarm | close
```

---

## 4. C++20 Native Acceleration (`libtradegen_fast.so`)

Compiled with `g++ -std=c++20 -O3 -fno-fast-math -ffp-contract=off -shared -fPIC` with zero file, network, clock, or environment syscalls. `core/compliance/native_accel.py` verifies `build_manifest.json` (`source_sha256` and `binary_sha256` bound into `owner.code_files()`) before loading via `/proc/self/fd/<fd>`, and falls back seamlessly to pure Python `Decimal` / `Fraction` whenever `TRADEGEN_DISABLE_NATIVE=1` is set or any input exceeds `10^-18` precision or `10^20` magnitude (`TG_FALLBACK_PRECISION`).

### Kernels & Differential Verification

| Kernel ID | C++20 Export | Python Bridge Caller | Arithmetic Discipline |
| --- | --- | --- | --- |
| HP-1 | `tg_fold_continuous_interval` | `execution_accounts/continuous.py` | Signed/unsigned 128-bit (`10^-18`) + `u256` FIFO cost allocation & ms equity fold |
| HP-2 | `tg_check_bid_gap` | `execution_accounts/provider.py` | `u256` exact cross-multiplied rational inequality |
| HP-3 | `tg_ma_crossover`, `tg_universe_momentum_top1`, `tg_simulate_carry` | `execution_launch/program.py`, `execution_launch/carry_evaluator.py` | `u256` / `u384` / `u512` exact integer ratios + exact IEEE-754 `binary64` return rounding |
| HP-4 | `tg_validate_and_size_order`, `tg_validate_book_levels` | `execution_control/model.py`, `core/compliance/native_accel.py` | `u256` exact lot/tick remainder & orderbook imbalance checks |
| HP-5 | `tg_kis_parse_caret_fields`, `tg_kis_window_metrics` | `data/_kis_native.py`, `data/kis_live.py` | Zero-allocation `^` field scanner + `u256` exact window VWAP |
| HP-6 | `tg_odds_mc_simulate`, `tg_bid_gap_mc_study` | `core/odds/simulate.py`, `core/compliance/native_accel.py` | Exact MT19937 64-bit word stream + IEEE-754 `binary64` 10,000-path Monte Carlo |

### Measured Latency Benchmarks (`tests.native_cpp_acceptance`)

| Workload | Pure Python (`ms`) | C++20 Native (`ms`) | End-to-End Speedup |
| --- | ---: | ---: | ---: |
| HP-1: 4-coin continuous fold (`4,000` prints + FIFO fills, 15 reps) | `67.74` | `55.67` | `1.22x` |
| HP-3: Protective-carry simulation (`2,000` bars, 25 reps) | `943.17` | `341.07` | `2.77x` |
| HP-6: Odds Monte Carlo (`10,000` paths x `20` days, 60 reps) | `3493.18` | `3309.01` | `1.06x` |

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
