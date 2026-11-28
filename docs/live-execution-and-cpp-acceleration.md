# Controlled Live Execution, Protective Hold (A2), and C++20 Native Acceleration

## 1. Architecture Overview

The production launcher refuses with `LIVE_PRODUCTION_AUTHORITY_REQUIRED` before accessing credentials, acquiring a lock, or changing any owner record. The independent review found no production source attesting the held interval, no chronological guard commit in this launcher, and no independently verified same-process protective-sale authority. Rehearsal tests exercise accounting and fault handling with synthetic inputs.

This document describes the proposed Upbit KRW spot execution architecture, Blocker 1 Approach A continuous interval valuation, BR-10 stale-ticker bid-gap monitoring (`Y`), Standing Amendment A2 durable Protective Hold, the D14-clean `CurrentPlanner`, and the `native/tradegen_fast` C++20 low-latency native engine.

### Key Modules

| Layer | Module | Responsibility |
| --- | --- | --- |
| E1 Inquiry | `execution/upbit_inquiry.py`, `execution/transport.py` | Read-only `/v1/trades/ticks` and `/v1/order` inquiry endpoints under `READ_CAPTURE_ENDPOINTS` allowlist. |
| Account Evidence | `execution_accounts/upbit_collector.py`, `execution_accounts/provider.py`, `execution_accounts/continuous.py` | Approach A trade-window backward pagination, order-detail fee reconciliation, BR-10 best-bid attachment & exact rational bid-gap check, and `<= 4`-market continuous equity fold. |
| Interval Producer | `execution_launch/account_interval.py` | Held-position continuous interval framing and deterministic `[prev, boundary)` / `[boundary, curr)` splitting across `22:00 KST` recovery and `00:00 KST` midnight boundaries. |
| Compliance & Signer | `core/compliance/owner.py`, `tools/signer/sign.py` | The optional exact `bid_gap_fraction` on `limit_set` follows the existing D12 fold. Standing protective authority still requires its deployment-bound approval implementation. |
| Control & Orders | `execution_control/risk.py`, `execution_control/controller.py`, `execution_orders/transport.py` | `BID_GAP_BLOCKED` entry refusal, `PERSISTENT_HALT` enforcement, `halt_line` / `daily_limit` exposure, and `VenueOrderTransport` single-attempt authenticated dispatch. |
| Runtime & A2 Hold | `execution_launch/runner.py`, `execution_launch/coordinator.py`, `execution_launch/protective_store.py` | Isolated dry-run order boundary (`gtc` / `ioc`) and Standing Amendment A2 Protective Hold state transitions. |
| Owner Composition | `tools/owner/planner.py`, `tools/owner/live.py`, `tools/owner/launch.py` | Proposed runtime wiring includes an exclusive `live.lock`, separate order vs inquiry credentials, D14-clean `CurrentPlanner`, and console commands (`bootstrap`, `odds`, `prepare`, `run`, `status`, `refresh-terms`, `cancel-all`, `exit`, `stop`, `disarm`, `close`). |
| Native Engine | `native/tradegen_fast/`, `core/compliance/native_accel.py`, `data/_kis_native.py` | Zero-syscall C++20 shared library (`libtradegen_fast.so`, `TG_ABI_VERSION = 1`) with SHA-256 + `code_files()` manifest verification and `10^-18` fixed-point (`__int128` / `u256` / `u384` / `u512`) exact arithmetic. |

---

## 2. Safety & Accounting Invariants

1. **Blocker 1 Approach A & Multi-Coin Continuous Valuation**:
   - `collect_trade_window` waits for the ticker server time, walks each UTC day separately, uses the last returned row as the cursor, and retains all source receipts. Exhausting the request budget refuses the interval. A ticker discrepancy is returned with its evidence and blocks interval use pending the durable BR-9 check.
   - `collect_order_fills` reconciles `executed_volume == sum(trades.volume)` on `/v1/order` and allocates `paid_fee` at `10^-18` (`ROUND_DOWN`) with exact final-trade residual conservation.
   - `value_trade_paths` folds up to `4` held KRW spot markets (`<= 12,000` prints, `<= 512` fills) with exact FIFO lot cost release and conservative intra-millisecond `[min_equity_krw, max_equity_krw]` bounds.
2. **BR-10 Stale-Trade Bid-Gap `Y` & D12 Fold**:
   - When a held coin's last trade is older than `30s` (`trade_time <= received`), `_collect_marks` attaches `/v1/orderbook` level-0 `best_bid` (`<= 10s` old) without overwriting `mark_price = trade_price`.
   - A stale held Upbit mark triggers the bid-gap check when the best bid is missing or at/below the mark multiplied by `1 - Y`. An explicitly missing signed Y uses zero for monitoring and blocks new entry independently. The provider reports the current observation. Persisting the BR-9 latch and its release remains open.
   - Under D12 a smaller signed Y applies immediately. An initial or larger Y requires a subsequent Seoul date and the existing halt and arming checks. Before and after claims retain the effective cap through guard-generation replay.
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
   - The staged composition in `tools/owner/live.py` uses an exclusive non-blocking OS lock (`live.lock` under `TRADEGEN_HOME`), verifies `UPBIT_ORDER_ACCESS_KEY` / `UPBIT_ORDER_SECRET_KEY` are configured and strictly distinct from `UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY` (`LIVE_ORDER_INQUIRY_KEY_COLLISION` on reuse), as part of the proposed composition. The current production entry point stops before these steps. A previous arming must be reconciled against current account and order evidence.

---

## 3. Operator CLI Reference

### Offline Signer (`tools/signer/sign.py`)

The independent signer accepts `event limit_set` with the original two money fields and an optional third field, `bid_gap_fraction`. Supply Y as a JSON number, strictly greater than zero and at most 0.05. The first Y and later increases become eligible on the next Seoul date subject to D12 arming and halt rules. A smaller Y applies immediately. A two-field declaration leaves the effective Y in force. Without a prior effective Y, it remains unset. The signer rejects decimal literals that its canonical number format would round to a different amount. Existing two-field signatures retain their original bytes.

The detached prototype commands for scoped bid gaps and standing terms have been withdrawn. A log containing such experimental events fails verification and requires owner review of its provenance. Preserve the original log. X, M and Md belong to a future deployment-bound `standing_armed` approval. A signed cap by itself authorizes neither an adaptive model nor a trade.

### Native Engine Build (`native/tradegen_fast/build_native.py`)

```bash
python native/tradegen_fast/build_native.py
```

### Production readiness

A valid live configuration currently produces exit code 2 and `LIVE_PRODUCTION_AUTHORITY_REQUIRED`. Existing owner armings and order state are preserved. A production release needs source coverage bound to the account and interval, independently retained guard and baseline heads with crash recovery, and protective authority bound to the deployment, approved code, research and expiry. The operator also needs checked startup recovery and the plan selection and signed bid-gap history defined in the launch specification. Until then, review behavior through the hermetic `tests.live_controlled_acceptance` suite and the isolated rehearsal.

---

## 4. C++20 Native Acceleration (`libtradegen_fast.so`)

Compiled with `g++ -std=c++20 -O3 -fno-fast-math -ffp-contract=off -shared -fPIC` with zero file, network, clock, or environment syscalls. `core/compliance/native_accel.py` checks both manifest digests and requires a binary digest independently pinned in the D14-covered loader. It loads only a sealed copy of those bytes via a retained Linux descriptor. The reviewed reference build uses Debian x86-64 g++ 14.2.0-19. An unreviewed toolchain output, a missing library, or unavailable sealed-image loading selects the Python implementation. The caller also falls back to pure Python `Decimal` / `Fraction` whenever `TRADEGEN_DISABLE_NATIVE=1` is set or any input exceeds `10^-18` precision or `10^20` magnitude (`TG_FALLBACK_PRECISION`).

### Kernels & Differential Verification

| Kernel ID | C++20 Export | Python Bridge Caller | Arithmetic Discipline |
| --- | --- | --- | --- |
| HP-1 | `tg_fold_continuous_interval` | `execution_accounts/continuous.py` | Signed/unsigned 128-bit (`10^-18`) + `u256` FIFO cost allocation & ms equity fold |
| HP-2 | `tg_check_bid_gap` | `execution_accounts/provider.py` | `u256` exact cross-multiplied rational inequality |
| HP-3 | `tg_ma_crossover`, `tg_universe_momentum_top1`, `tg_simulate_carry` | `execution_launch/program.py`, `execution_launch/carry_evaluator.py` | `u256` / `u384` / `u512` exact integer ratios + exact IEEE-754 `binary64` return rounding |
| HP-4 | `tg_validate_and_size_order`, `tg_validate_book_levels` | `execution_control/model.py`, `core/compliance/native_accel.py` | `u256` exact lot/tick remainder & orderbook imbalance checks |
| HP-5 | `tg_kis_parse_caret_fields`, `tg_kis_window_metrics` | `data/_kis_native.py`, `data/kis_live.py` | Zero-allocation `^` field scanner + `u256` exact window VWAP |
| HP-6 | `tg_odds_run_paths_f64`, `tg_adaptive_bid_gap_mc` | `core/odds/simulate.py`, `core/compliance/native_accel.py` | IEEE-754 pricing on supplied paths; SplitMix64-seeded xoshiro256** for adaptive bid-gap sampling |

### Reproducing the latency measurements

After building the reference kernel, run `python -m tests.native_cpp_acceptance latency_benchmarks`.
The JSON output reports mean milliseconds per repetition for each backend on the current host.
For HP-1 it folds four markets and 4,000 prints (five native and two Python repetitions).
HP-3 simulates 2,000 bars and evaluates moving averages (three native and two Python repetitions).
HP-6 uses 10,000 paths per scenario and a 10-day horizon (five native and two Python repetitions).
These workloads run offline and exclude venue, network, and broker latency.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
