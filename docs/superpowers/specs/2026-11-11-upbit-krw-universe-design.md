# Upbit KRW universe, stage 1: one coin at a time

Date: 2026-11-11 (Asia/Seoul). Revision 3, after two adversarial reviews against the code (57 and 70 kept findings) and a citation
check against the code (37 corrections).
Status: design for owner review. This document does not authorize development by itself; the owner approves it first.
Real account setup, signatures, session arming and live operation stay separate owner actions.

Inputs: [compliance gate and odds design](2026-10-23-compliance-gate-and-odds-engine-design.md),
[E2/E3 execution design](2026-10-31-e2-e3-execution-design.md),
[equity-policy candidate](2026-10-30-equity-policy-and-strategy-design.md), and the code at `origin/main` fd85850.
Owner financial parameters remain private and are not written here.
This is software design, not legal, tax or investment advice. Neither the software nor its author is a licensed advisor.

## 1. Owner decisions (2026-11-11)

- **Candidate universe: every Upbit KRW market, automatically.** A coin becomes a candidate when it passes a signed
  eligibility rule. The owner signs the rule once, not each coin. This replaces the agent seed P22, which listed only
  BTC and USDT.
- **Structure: signed rule plus an automatic list.** The app builds the candidate list from Upbit's public market list
  and records it with receipt hashes. A stale or failed list blocks new buys and never blocks exits.
- **Holding mode, staged.** Stage 1 (this document) holds one coin at a time. A switch sells all of the held coin and
  then buys the new one. Stage 2, several coins at once, is a later and separate design (section 20).
- **Upbit flags: "warning sells, caution holds".** A held coin designated 투자유의 (`warning`) is sold. A held coin
  with only a 주의 (`caution`) flag is kept as the strategy decides, but is not bought again while flagged. Any
  flagged coin is out of the new-buy candidates.

Unchanged: the floor and total-loss rule (its own owner decision is still open), the derivatives and leverage bans,
the rules table, fixed-symbol KRW-BTC profiles, and every other venue.

**Choices this revision makes inside those decisions** (the owner may overrule any of them):
- The warning sale goes through the strategy: the decision made at the slot that first sees `warning` is cash, and
  the sell is sent at the next slot, one bar later. Revision 2 had a separate same-slot sell, which added an order
  path inside the slot's recording window.
- The study program freezes a candidate count N: only the N most liquid eligible coins can be bought. Every one of
  those N coins must pass the odds check on the day, or no session can be prepared.
- The per-coin odds run as a separate daily step before preparation, not inside it.
- For live slots, the app keeps the parsed Upbit flag and price values in the hash-chained history, with the sha256 of
  each raw body. It does not keep the raw bodies. The study keeps the raw bodies, as it does today.

## 2. Facts this design rests on

Code at fd85850 (file:line).

**One symbol is pinned throughout the launch stack.**
- The study rule is the constant `upbit-krw-single-asset-v1` (`execution_launch/study.py:58`, enforced at 172).
  `symbol` is a common term, so every candidate in a plan shares one symbol (`study.py:72`, `215`). The capture opens
  one quote source for `candidates[0].protocol.symbol` (`study.py:654`).
- The live quote source is built for one symbol (`tools/owner/rehearsal.py:371`), and the coordinator reads the book
  with no symbol argument (`execution_launch/coordinator.py:408-413`). The terms source is read the same way
  (`coordinator.py:444`).
- The driver pins time in force to `gtc` (`execution_launch/driver.py:162-163`) and refuses any other non-zero
  holding (`driver.py:315-316`); it compares the quote and the holding key with `protocol.symbol` (`271`, `303`).
- `LiveHistory` is built once from the launch profile (`coordinator.py:802`) and pins the coin in `_anchor`
  (`live_history.py:306-307`), `_derive` (`325`) and `_replay` (`409`); the paper capture and the evaluator pin it
  too (`paper_capture.py:196`, `strategy.py:290`).
- `profile_contract_digest` pins the coin twice: through the top-level `LaunchProfile.symbol`, which `profile_body`
  copies (`execution_launch/profile.py:85`, `261-262`), and through every `InstrumentRules` field except `asof`
  (`profile.py:269-273`, `306-308`). `rule_terms_digest(rules)` takes bare rules and hashes every field except `asof`
  (`profile.py:283-296`). `profile_digest` hashes everything, `asof` included (`profile.py:277-279`).
- Renewal refuses a changed symbol, rule-terms digest or contract digest (`execution_launch/instrument_refresh.py:72-75`,
  `95`) and builds the new profile by replacing only `instrument_rules` (`instrument_refresh.py:94`). `renew_profile`
  moves the process-wide chain head before the runner applies it (`instrument_refresh.py:102`); a later renewal from
  the old profile refuses as a fork (`83-84`), and rules issued by a renewal that is no longer the head refuse as
  `RENEWAL_NOT_CURRENT` (`123-125`). That check runs for every order on renewed rules (`160-161`, `166`); initial
  rules go through `observation_for_rules` (`162-164`). Every order is also checked against the observed maximum
  notional (`168-170`); a failure raises `RenewalError`, which the runner's catch-all turns into a stop.
- The digests are compared again by the runner on every tick (`execution_launch/runner.py:149-151`,
  `execution_launch/strategy.py:505-508`), the driver (`driver.py:166-168`), the workflow (`execution_launch/workflow.py:175-179`,
  `208`), history (`execution_launch/live_history.py:448`), the study (`study.py:247`, `255`, `447`, `479`), the
  review (`execution_launch/study_review.py:86-87`, `execution_launch/review_request.py:241-245`) and the example tool
  (`tools/research/prepare_launch_example.py:70`).
- The driver pins the full `profile_digest` taken at construction (`driver.py:244`) and reads the rules from that
  frozen profile (`driver.py:251`), while the runner swaps in each renewed profile (`runner.py:307`) and the
  coordinator renews every 4 minutes (`coordinator.py:80`). Because `profile_digest` includes `asof`, the first renewal
  should make the next tick refuse `FIXED_DRIVER_PROFILE_CHANGED`, which the runner's catch-all turns into a permanent
  stop (`runner.py:459-462`). This looks like an existing bug for KRW-BTC; its fix is the first PR (section 19).
- The terms authority binds symbol, lot, minimum quantity and maximum notional (`execution_accounts/instrument_terms.py:93-100`).
  The parser requires the observed maximum to equal the authority's (`instrument_terms.py:185-187`) and exactly one
  instrument (`192-194`); the tick is read from each observation (`201`).

**Session preparation is short and single-plan.**
- `PreparedSession` stores one `symbol` (`execution_control/session.py:28`, set at `175`) and the `rules_digest` of
  one `InstrumentRules` (computed at `133`, stored at `173`); `verify_session` compares both (`218-223`).
- All of `prepare_session`, the simulate call included, must finish within 30 seconds of the inputs' `now` and of the
  positions' time (`session.py:39`, `106-109`, checked again after simulate at `146`), with rules at most 5 minutes
  old (`40`, `111`). Expiry defaults to `now` plus 30 minutes and may be at most 24 hours (`88-91`). The plan's start
  must be the preparation's Seoul date (`92`). The selected plan's seed must match an earlier selection run (`117-126`).
- `Coordinator.prepare` holds the coordinator's work lock for the whole call and needs an account observation at most
  30 seconds old (`coordinator.py:713`, `722-724`). `prepare_launch_session` refuses a selected plan whose leg symbol
  is not the profile's coin (`runner.py:201-204`).
- The runner blocks a buy, without stopping, when the session is outside `prepared_at <= now < expires_at`
  (`runner.py:359-373`).

**The driver acts one bar after the decision.** `LiveHistory._derive` computes the decision for bar k at
`record_slot` k from the marks through k (`live_history.py:318-334`). The tick at slot k+1 checks that prior decision,
recomputes it from the whole history (`driver.py:276-290`) and trades toward it.

**The coordinator reads the book first.** A slot unit runs: the terms gate (`coordinator.py:510`), the book at the
prefetch lead (`514`), the account capture (`518`), the wait, the sample, `_publish` (`529`), `record_slot` (`533`),
then one tick (`536-538`). The account capture may end inside the slot's 10-second window (`coordinator.py:13-15`,
`34`). The lead is 1 to 8 seconds (`84`), and `monitor_seconds - lead` must be at least 5 (`301`). A monitor unit
renews terms first (`480`), then captures, publishes, calls `Controller.observe` (`491`) and reconciles. A failed
book read or capture refuses the slot (`411-413`, `542`); a slot that is not recorded is never backfilled and ends
every later slot of the window (`coordinator.py:36`, `live_history.py:15-16`, `323`).

**Terms failures.** A failed renewal sets `_terms_blocked` (`coordinator.py:457-458`), and the slot gate then refuses
every strategy slot at once (`510`), sells included. Explicit exits through `submit_exit` keep working until the rules
are 5 minutes old (`execution_control/controller.py:605`), about one minute after the failed 4-minute renewal.

**Controller.** Active order states are `RESERVED`, `DISPATCHING`, `ACKNOWLEDGED`, `UNKNOWN`, `PARTIAL` and
`CANCEL_REQUESTED` (`controller.py:26`). `OrderState` carries no side, symbol or time (`59-64`). `observe` loads the
context and returns a `RiskResult` (`433-442`). `reserve` and `dispatch` each run `_authorize`, which calls
`load_context` (`612`). `Controller.kill` ignores its `reason` argument: it records `owner_requested`, or `clock_ambiguous`
when the account clock check fails (`850-870`, reason at `863`), and writes the owner-log `system_disarm` with the
fixed reason `execution control kill` only when that check passes (`867`). `AccountObservation` has no per-coin price
(`controller.py:33-49`). The control journal accepts only a closed set of event kinds
(`execution_control/store.py:25-27`, `306-307`), and each row must carry exactly its kind's field set; a
`session_prepared` row must carry exactly the `PreparedSession` fields (`controller.py:151`, `170-171`).

**Program, evaluator and history.**
- `program.py` has two program kinds (cash, moving-average trend) over one mark series.
- The paper evaluator applies a whole target change in one bar (`strategy.py:348-349`), validates every bar against
  one `InstrumentRules` (`strategy.py:288-306`), and runs a lag-2 stress that must also be profitable (`strategy.py:433`,
  `517`). The runner refuses a buy while any order is active (`runner.py:444`).
- Family accounting is Bonferroni over the declared family (`strategy.py:442`). A plan's family must equal exactly its
  own candidates (`study.py:216`). A candidate needs at least `minimum_roundtrips` completed exits, with a protocol
  floor of 20 (`strategy.py:154`, `512`); a round trip counts when units return to zero (`strategy.py:374-375`).
- History rows are capped at 256 KiB (`execution_control/store.py:28`) and study captures at 16 MiB
  (`execution_launch/paper_capture.py:24`, checked only when written after the window, `study.py:662`). A sampled book
  must have been received by the slot (`paper_capture.py:136`). The live and paper quote parsers accept exactly one
  book per receipt (`execution_accounts/quotes.py:143-144`) and refuse a book over 10 seconds old (`155-156`).

**Compliance and accounts.**
- The rules table already allows any `coin`-class spot buy or sell for cash on Upbit (`KR-DOMESTIC-SPOT` in
  `core/compliance/kr_rules.yaml`). The blocks are the signed instrument map (BTC, USDT, USDC) and the venue market
  list in `core/odds/venues.yaml`.
- The venue parser has a closed key set (`core/compliance/rules.py:698`); an unknown key raises (`rules.py:372`) and
  makes the whole approved state invalid (`rules.py:928`). The signer signs the raw venues bytes without parsing them
  (`tools/signer/sign.py:1054-1055`).
- The gate looks symbols up only in signed instrument maps, plus earlier maps for exits (`core/compliance/gate.py:460`).
  Its own callers are `_validate` (`gate.py:156`), `_transfer` (`257`), `screen` (`630`, which `simulate` calls at
  `core/odds/simulate.py:445-447`) and `grey_rows` (`677`). The controller calls the private `gate._lookup` at
  `controller.py:519` (`_intent`, also used by `cancel`) and `584` (`_exact_caps`).
- `load_context` turns any exception in reading the state into a broken context with no snapshot
  (`core/compliance/owner.py:1005-1010`), which blocks every exit (`gate.py:103`).
- `core/compliance` may import only stdlib, yaml, cryptography, `core.isolation` and `core.compliance`
  (`tests/compliance_guards.py:190-193`).
- The account capture reads a fixed route set (`execution_accounts/upbit_collector.py:34-35`, pinned in
  `tests/accounts_guards.py:15-16`), needs a ticker for every coin with a balance above zero whose last trade is at
  most 30 seconds old (`upbit_collector.py:390`, `402`, `418-421`), and must finish within 30 seconds. The provider
  requires a positive price for each position (`execution_accounts/provider.py:234`) and a position for each inventory
  row (`243-245`). The per-holding price and time are kept in `AccountEvidence.positions`
  (`execution_accounts/model.py:155`), inside the `BaselineFrame` the coordinator publishes and keeps as
  `_latest_frame` (`execution_accounts/baseline_bridge.py:35-37`, `coordinator.py:427`).
- When the capture fails, every slot, `submit_exit` and `cancel` is refused (`coordinator.py:518`, `552`). An unpriced
  coin makes the E1 venue value `None` (`execution/positions.py:33`).
- `execution_accounts` may not write files (`tests/accounts_guards.py:11`, `95-96`). Pinned writers live in
  `execution_launch` or `execution_network` (`tests/launch_guards.py:14`, `PINNED_WRITES`). `execution_launch` may not
  reference `load_context` (`tests/launch_guards.py:22`) or hold `/v1/` literals (`:25`), but may import
  `core.compliance.owner` (`execution_launch/deployment.py:23`). `execution_control` may import only stdlib,
  `core.isolation`, `core.compliance`, `core.odds`, `execution.snapshot`, `execution.positions`, `execution_control`,
  `execution_orders`, and two pinned `execution_launch.instrument_refresh` names in `controller.py` and `session.py`
  (`tests/control_guards.py:15`, `23-26`, `62-85`, `103`); transport and key modules are refused (`97`), and so are
  `/v1/` literals (`122`).
- The Upbit public allowlist is `/v1/ticker`, `/v1/orderbook`, `/v1/orderbook/instruments`
  (`execution/upbit_inquiry.py:20`), pinned by `tests/execution_guards.py` and `tests/renewal_boundaries.py`.
- `core.compliance.alerts._toast` shows a Windows toast (`core/compliance/alerts.py:216`). The E1 poll is a separate
  process (`execution/poll.py:4`) and only raises alerts (`poll.py:11`).

**Odds.** Odds bars come from `core/oddsdata/bars.py` through `data.crypto.crypto_client`, outside the transport and
the signed closure; that import chain loads `.env` (`config.py:28`). History goes back up to 3650 days
(`bars.py:29`). The engine refuses fewer than 250 daily bars (`core/odds/plan.py:38`). The replay edge is BTC-only
(`plan.py:301-303`). One `simulate` call for a coin runs 12 columns of
200,000 or 1,000,000 paths each: 5 members at base and 2x costs, plus 2 delisting columns (`simulate.py:34`, `43`,
`523-527`, `749-752`).

**Rehearsal.** Controlled mode is refused (`coordinator.py:281`). The rehearsal account source accepts only flat
accounts (`execution_launch/account_interval.py:118`), the dry-run adapter never fills
(`execution_control/dry_run.py:3`), and the rehearsal runtime has no preparation provider
(`tools/owner/rehearsal.py:374`, `tools/owner/launch.py:223`), so every buy ends blocked at
`RUNNER_ACTUAL_PREPARED_SESSION_REQUIRED` (`runner.py:361-362`).

**Prior research.** `docs/research/2026-10-31-strategy-lab/results/summary.json` covered 8 assets and 21,408
configurations with no pass. Its only crypto assets are BTC (KRW and USDT) and ETH-USDT. It has no Upbit KRW altcoin
and no rotation rule.

**Upbit public documentation (checked 2026-11-11).**
- `GET /v1/market/all?is_details=true` returns, per market, `market_event.warning` (boolean, 투자유의) and
  `market_event.caution` with five boolean keys: `PRICE_FLUCTUATIONS`, `TRADING_VOLUME_SOARING`,
  `DEPOSIT_AMOUNT_SOARING`, `GLOBAL_PRICE_DIFFERENCES`, `CONCENTRATION_OF_SMALL_ACCOUNTS`
  (https://docs.upbit.com/kr/reference/list-trading-pairs). The market group allows 10 calls per second per IP.
- No API field announces a scheduled end of trading support (거래지원 종료).
- Limit orders accept `time_in_force` `ioc`, `fok` or `post_only` (https://docs.upbit.com/kr/reference/new-order).
- Daily candles close at 00:00 UTC (09:00 KST).
- A repo research note counted 289 KRW pairs in a live probe
  (`research_notes/QUANTGEN asset coverage expansion/crypto_strategies.md:28`).

## 3. Scope

In stage 1: the signed eligibility rule and the daily snapshot (sections 4, 5); how each part of the app sees the
snapshot (section 6); the per-slot sequence, held-coin events and buy limits (section 7); the gate, odds, session,
profile, terms, order, account-capture, driver and history changes needed to hold any eligible coin and to switch
(sections 8 to 12); a universe study type, so a rotation rule can be tested before it is armed (section 14).

Out of scope: several coins at once (stage 2), controlled mode and the held-position producer, the floor decision, the
tick-band fix for fixed-symbol profiles, tax computation (every switch realizes a gain or loss; crypto is tagged
taxable from 2027 in `instruments.yaml`, so the owner keeps records), and push or email delivery faster than the
existing 09:05 KST daily task.

## 4. Signed eligibility rule

`core/odds/venues.yaml`, upbit entry, new optional key. Shape and proposed defaults (the owner sets the values before
signing):

```yaml
    universe_rule:
      source: "https://docs.upbit.com/kr/reference/list-trading-pairs"
      quote: KRW
      exclude: [USDT, USDC]            # stablecoins and anything else the owner never wants as a candidate
      min_listing_days: 250            # a daily candle dated at least min_listing_days + 1 days before day D
      median_days: 30
      min_median_value_krw: 1000000000 # median daily trading value over calendar days D-30 .. D-1
```

- Fixed in code: KRW quote only, and the base symbol must match `[A-Z][A-Z0-9]{0,11}` (the strictest pattern already
  used by the collector, risk and continuous code).
- **Flag classes**, one test used everywhere (snapshot, per-slot read, chooser, study):
  - `unflagged`: the market is present, `market_event.warning` is present and exactly `false`, all five known caution
    keys are present and exactly `false`, and no other caution key is `true`;
  - `warning`: present, and `warning` is exactly `true`;
  - `caution`: present, `warning` exactly `false`, and any caution key `true` (an unknown key included);
  - `unknown`: present, but `market_event` is missing or malformed, or `warning` or a known caution key is missing or
    not a boolean;
  - `absent`: not in the read.
  Only `unflagged` coins can be bought or enter the snapshot's eligible set.
- `min_listing_days` defaults to 250 because the odds engine refuses fewer than 250 daily bars (`core/odds/plan.py:38`).
- The existing `markets: [[BTC, KRW], [USDT, KRW]]` line stays, so `tests/compliance_tables.py` keeps its pin and the
  signed instrument map keeps today's path (section 8).
- Parser: add `universe_rule` to `_VENUE_OPTIONAL` with a strict sub-parser (known keys only; `quote` must be a
  settlement asset of the venue; `exclude` entries pass the symbol check; integers positive). Add
  `Venue.universe_rule: UniverseRule | None = None`.
- `rule_sha256` is the sha256 of the canonical JSON of the parsed rule, so unrelated edits to `venues.yaml` do not
  invalidate snapshots.
- Approval: the owner's existing `approved {kind: venues}`. No rules or instruments approval.
- The `source` URL is first recorded in a research note under `research_notes/`, because
  `tests/compliance_tables.py:1544-1553` refuses any `venues.yaml` URL that is missing from the research corpus.

## 5. Daily universe snapshot

**Requests**, for candle day D (UTC):
1. One `GET /v1/market/all?is_details=true`. `listed` = every KRW market in it.
2. Filters with no further request: symbol pattern, `exclude`, flag class `unflagged`.
3. For each remaining market, two candle reads:
   - age: `GET /v1/candles/days?market=X&to=<D - min_listing_days, 00:00 UTC>&count=1`. `to` is exclusive, so a
     returned candle is dated at least `min_listing_days + 1` days before D. Old enough iff one comes back.
   - value: `GET /v1/candles/days?market=X&to=<D, 00:00 UTC>&count=<median_days>`. This excludes day D by
     construction. The median is taken over the calendar days D-30 to D-1, and a day with no candle counts as zero.
4. `eligible` = the markets that pass every test, each with its median daily value.

About 2 x 289 + 1 requests at the transport's 0.2-second pacing plus a new TLS connection each: 2 to 4 minutes. The
only retry is the transport's own single GET retry after a connection error or HTTP 429/5xx
(`execution/transport.py:130-153`).

**Finality from content.** The build refuses unless no returned candle is dated D or later and the `market/all`
server time is at or after D 00:00 UTC. `built_at` is the latest receipt server time and must be at or after
D 00:10 UTC.

**Format and verification in `core/compliance`, as plain data (stdlib only).**
- A snapshot file holds the canonical JSON of the rule it was built under, the receipts, and a manifest sha256. Each
  receipt has the 7 keys of `live_history`'s receipt shape: `path`, `params` (list of `[k, v]`), `account_scope`,
  `received_at`, `server_time`, `raw_body_b64`, `sha256`.
- `rules.universe_eligible(rule, receipts)` parses the bodies itself (stdlib `json`) and returns `listed` and
  `eligible` with medians. It checks every receipt hash and that the set of `(path, params)` is exactly the set of
  requests the rule implies for that `market/all` body, so a snapshot cannot add, drop or swap receipts.
- `rules.verify_universe_snapshot(raw_bytes, rule_sha256)` is pure and never calls `load_context`. It checks the
  manifest, the embedded rule's sha256 against the given one, recomputes `universe_eligible`, and returns a
  `Universe(day, rule_sha256, snapshot_sha256, built_at, valid_from, valid_until, listed, eligible)`.
- A pure encode helper returns the canonical file bytes and the manifest sha256. The universe code in `core/compliance` writes no
  files; only `execution_launch/universe_store.py` writes the snapshot.

**In force.** `valid_from = max(built_at, D 00:40 UTC)` and `valid_until = D+1 00:40 UTC` (09:40 KST). At most one
snapshot is in force at any instant: the one for the day whose window contains `now`. If several files for that day
verify (a manual rebuild), the earliest built wins. The Seoul calendar date is not used, because it would block every
buy from 00:00 KST until the daily build.

**Storage.** Write-once and content-addressed: `owner.universe_path(D, sha256)` next to `owner.evidence_path()`. The
writer opens with `O_EXCL` and never replaces a file, so a rebuild adds a file and never changes one that a session or
history row already names.

**Builder and writer.**
- `execution/upbit_inquiry.py` gets fixed-parameter, public-only helpers and path constants next to `current_terms`:
  `market_all()` (`is_details=true`), `daily_candles(market, to, count)` with `count` at most 200, and
  `orderbook_instruments(markets)`. Each returns a transport `Answer`; none pages or calls the keyed
  `/v1/orders/chance`. Every symbol passes `KRW-[A-Z][A-Z0-9]{0,11}`. Add the two new paths to `ENDPOINTS` and `PUBLIC`.
- `execution_accounts/universe.py` is read-only, shaped like `E1UpbitTermsSource`: it calls the helpers under
  `inquiry_clock`, turns each `Answer` into a `SourceReceipt` (server time required), converts receipts to the plain
  shape, calls `rules.universe_eligible`, and returns the file bytes. It writes nothing. Pin it in
  `tests/accounts_guards.py` (`TRANSPORT_IMPORTS["universe.py"]`).
- `execution_launch/universe_store.py` writes the file (temporary file, fsync, then a link or rename to a name that
  does not exist yet) and holds the CLI `python -m execution_launch.universe_store snapshot --state-root <root>`. The
  CLI refuses unless `TRADEGEN_HOME` equals `--state-root`, like `tools.owner.launch setup-account`. Pin the writer in
  `tests/launch_guards.py` `PINNED_WRITES`.

**Reading it back.** `owner.load_context` fills `ctx.universe` with the snapshot in force at `now` for the active
signed rule, or `None`. The read-back catches every exception and returns `None`; it can never break the context,
so exits never depend on it. Verification results are cached in-process by file sha256.

**Failure.** If any request fails, no file is written for D, and buys that need the universe stop at 09:40 KST. The
amber alert comes from the E1 poll (section 15).

**Schedule.** The owner registers the CLI once in Windows Task Scheduler at 09:12 KST with a retry at 09:27 KST, with
the same `TRADEGEN_HOME` as the runtime that reads it (one task per root if a rehearsal root and the default root are
both in use). Creating scheduled tasks is an owner act; Claude does not.

## 6. Who sees the universe, and how

- **Controller (the authority).** The gate and `verify_session` use `ctx.universe` from `load_context`.
- **Runner and coordinator.** `Controller.observe` returns its `RiskResult` with one new field, `universe`: the
  `Universe` from the context it just loaded, or `None`. The runner uses the value from its own `observe` call in the
  tick, so its buy checks see the same snapshot the controller will see. The coordinator keeps the value from its last
  monitor unit for the status and for the slot's buy allow-list.
- **LiveHistory, driver, evaluator.** They use only values recorded in the history rows or the capture (sections 12
  and 14), never `load_context` and never the state-root files at replay.
- `execution_launch` keeps its ban on referencing `load_context`.
- **Top-N.** The study program freezes `max_candidates` N (section 14). The candidate set at a slot is the N eligible
  coins of the snapshot in force with the largest median value, ties by symbol ascending.

## 7. Per-slot sequence and rules

**Terms.**
- *Mark*: the per-holding price and time in the last published `BaselineFrame` (`AccountEvidence.positions`). Section
  11 makes it the ticker trade price, a fresh best bid for a thin coin, or 0 for an unlisted coin.
- *Dust*: a holding worth less than the signed Upbit minimum order (5,000 KRW) at its mark. An unlisted holding is
  always dust; the vanish event below is keyed on the previous frame's held coin, not on this verdict.
- *Held coin*: a non-dust coin holding in scope.
- *Trade coin*: the coin in `profile.symbol`, whose rules are current and whose book each slot reads.
- *Flat in X*: no non-dust holding of X in the last published frame, no controller order in X in an active state, and
  no order in X updated at or after that frame's account time (so a fill the frame has not seen yet still counts).

**Choosing the trade coin** (in each monitor unit, after its capture and `_publish`, under the work lock):
1. Exactly one held coin: that coin.
2. Two or more held coins: keep `profile.symbol` if it is one of them, else the one with the largest value at its
   mark. Set the buy block `UNIVERSE_EXTRA_HOLDING` and raise a red toast; the owner sells the extra coin in the app.
3. No held coin: the target of the latest recorded decision, if it is a coin and the account is flat in
   `profile.symbol`; otherwise `profile.symbol`.

If the chosen coin differs from `profile.symbol`, the coordinator checks "flat in `profile.symbol`" before anything
else. Not flat is a normal outcome: no renewal is issued and nothing is raised. Flat: the coordinator reads the new
coin's terms and renews (section 10). The same-coin 4-minute refresh stays where it is today, at the start of the unit.

**Slot unit**, keeping today's book-first order:
1. Gate: `_ready`, and `_terms_blocked` only while a coin is held (below).
2. The trade coin's book at the prefetch lead. A failed or stale read marks the book `unavailable` instead of
   refusing the slot.
3. The account capture (it may end inside the slot window, as today).
4. The flag read: one `market/all?is_details=true`.
5. The ticker read: one `/v1/ticker` over `listed` of the snapshot in force intersected with the KRW markets of this
   slot's flag read. If the flag read failed, there is no ticker read.
6. Wait for the slot, sample the book (if any), `_publish`.
7. `record_slot`, in its own `try`. A failure is recorded in `reasons`; it never skips step 8.
8. The events below, each in its own `try`. A failure sets a reason, a status field and a toast, and never aborts the
   unit.
9. The tick, only if step 7 recorded this slot, the book is available and `tick <= slot + 10 s`, with the slot's buy allow-list. With no book the tick
   is skipped with `COORDINATOR_NO_TRADE_BOOK`; this is not a refusal, and the row is still recorded. A failed
   record skips the tick, because the driver would refuse a frame without this slot and the runner would stop for
   good (`live_history.py:344-348`, `runner.py:459-462`); the window then ends (section 12).

Steps 4 and 5 use a new keyless `execution_accounts` source (section 19, PR 2) with its own guard pins and body caps
sized from the section 17 measurement. A failed read is recorded as `unavailable`.

**Events** (step 8):

| Event | Action |
|---|---|
| The capture marks unlisted the coin that was the held coin in the previous published frame, or the held coin's terms read returns the new `TERMS_MARKET_INACTIVE` code | `Coordinator.stop()`, then `Coordinator._disarm_locked(reason="market_vanished")`, once per window. Red toast. The owner handles the coin in the app. |
| Any dust coin or other non-held coin with a balance is `warning` | Red toast, once per coin per day: clear it while it still trades (top it up above 5,000 KRW and sell it in the app). |
| The held coin is `unknown` or `absent` in the flag read | No buy at this slot. No forced sale. Amber toast. |
| The trade coin is held, the decided target is another coin or cash, and the tick returned `hold` because the whole sell is below the minimum at its limit price, for two slots in a row | Buy block `UNIVERSE_REMAINDER_UNSELLABLE`, red toast. The owner tops up and sells in the app. |

A held coin that is `warning` needs no event: the chooser decides cash (section 14, rule 1) and the next tick sells.
A held coin that is `caution` is kept as the chooser decides.

- `Coordinator.disarm` is split into a public wrapper that calls `stop()` and takes the lock, and a lock-free
  `_disarm_locked(reason)` for callers that hold it. It runs after `_publish`, so `Controller.kill` sees a fresh frame
  and writes the owner-log `system_disarm`. `Controller.kill` records the given reason instead of the fixed
  `owner_requested` (`clock_ambiguous` stays when the clock check fails; kill then returns `False` with no owner-log
  row, which counts as a failed disarm), and the automatic disarm uses its own coordinator code `COORDINATOR_UNIVERSE_DISARM`. If it
  fails, the sticky status field `disarm_failed` is set and a red toast is shown (section 15).
- `parse_term_receipts` splits `TERMS_MARKET_INACTIVE_OR_MISMATCHED` into `TERMS_MARKET_INACTIVE` and
  `TERMS_MARKET_MISMATCHED`.

**Terms failures.**
- While a coin is held, a terms failure keeps today's `_terms_blocked` behaviour, because exits need fresh rules.
  `TERMS_MARKET_INACTIVE` goes to the vanish event instead.
- While no coin is held, a terms read, parse or renewal failure never sets `_terms_blocked` and never refuses the
  slot. It sets the buy block `TERMS_TARGET_UNAVAILABLE`, and the row records it. The tick still runs: the trade coin
  is not held and its target is 0, so the tick holds. A cross-coin renewal that was issued but not applied is kept
  and retried as today; while it is pending, buys are blocked.

**Buy allow-list.** `Runner.tick` takes `entry_allow`, a set of symbols. For a universe profile a buy needs
`profile.symbol` in `entry_allow`, and a missing `entry_allow` blocks every buy. The coordinator builds it at each
slot: the top-N coins of the snapshot in force that are `unflagged` in this slot's flag read and have a defined
price in this slot's ticker read. It is empty when any buy block is set (`UNIVERSE_EXTRA_HOLDING`,
`UNIVERSE_REMAINDER_UNSELLABLE`, `TERMS_TARGET_UNAVAILABLE`, the flag or ticker read unavailable, no snapshot in
force, or the snapshot's rule sha256 not equal to the profile's). The runner then also checks, from its own
`observe`: the snapshot is in force, its sha256 equals the session's bound snapshot, and `profile.symbol` is in the
session's coin set (section 9). Every failure is a `blocked` result, never a runner stop. Strategy sells and
`submit_exit` never look at the allow-list.

**Sell guard.** `OrderState` gains `side`, `symbol` and `updated_at`. `Runner.tick` refuses a sell (status `blocked`,
`RUNNER_OUTSTANDING_ORDERS`, no stop) while a sell of the same symbol is in an active state. Today that case raises
in `_capacity` and stops the runner.

**A delisting with no prior `warning`** is caught only when the coin leaves `market/all`. By then the app may not be
able to sell it. That is a known limit of the public API.

## 8. Compliance gate

- `core/compliance/model.py`: add `Universe` (section 5) and `Context.universe: Universe | None = None`.
  `load_context` fills it and seals it into `ctx_hash`.
- `gate.py`:
  - Symbols in a signed instrument map keep today's path, unchanged.
  - **Exits never need a snapshot.** A cash sell for KRW on upbit of a coin held per `ctx.holdings`, whose symbol
    matches the pattern, resolves to a derived coin instrument in both the active state and the recovery snapshot,
    whatever the venue facts say. The derived instrument copies the signed BTC entry's fields (`crypto_coin` x1, class
    `coin`, `crypto_venue`, KRW, `crypto_22pct_from_2027`). The quantity is checked by the existing `_within_free`.
    A later venues approval that drops `universe_rule` therefore never traps a held coin.
  - **New exposure** on a derived coin needs a venue whose signed facts carry `universe_rule`, `ctx.universe` in
    force, and the symbol in `eligible`. Otherwise BLOCK `state: universe <reason>`.
  - **Recorded orders.** `cancel` builds its intent through `_intent` (`controller.py:754`), as `reserve` and
    `dispatch` do through `_authorize` (`641`); status reconciliation builds none and is unaffected. For an order
    already recorded in the journal, the lookup resolves the derived instrument whatever its side and the snapshot state, so a protective
    cancel is never refused. Only `reserve` and `dispatch` of a buy need the snapshot.
  - `_retired` is false for an eligible coin. The market test accepts (coin, rule quote).
  - Add a public `lookup(ctx, venue, symbol, exits)`. Switch to it at `gate.py:156` (`_validate`, passing the existing
    exit flag), `gate.py:630` (`screen`, `exits=False`; otherwise `simulate` refuses every derived coin), `gate.py:677`
    (`grey_rows`), `controller.py:519` and `584`, `plan.instrument`, and the market check at `core/odds/plan.py:320`.
    `gate.py:257` (`_transfer`) stays on the signed maps: a transfer of a derived coin stays blocked.

| Check | Owner |
|---|---|
| The coin may be traded at all (signed map, or the signed rule for buys, or a held coin for KRW exits) | gate |
| The coin is in `eligible` of the snapshot in force | gate for derived coins; `verify_session` for every buy of a universe session, BTC included |
| The coin is in the session's top-N set and that set passed odds | `verify_session` (section 9) |
| No flag at this slot | the coordinator's allow-list (section 7) |

## 9. Odds batch and prepared session

**The per-coin odds run as their own step, before preparation.**
- The owner runs a new console command `odds` in the owner runtime (`tools/owner/launch.py`), after 09:40 KST, and
  again after Seoul midnight if a session is wanted then. It runs on the console thread, never under the
  coordinator's work lock and never inside a unit, so slots keep running.
- Candles: `execution_accounts/universe.py` gets `daily_bars(markets)`, which pages the `daily_candles` helper under
  `inquiry_clock`, checks each receipt's path, params and sha256, keeps final bars only with the rules of `load_leg`'s
  `upbit_daily` path, and returns plain bars plus the receipt sha256 list. It imports no `core.oddsdata`, `data.*` or
  `config`.
- `execution_control/universe_odds.py`, `run_batch(template, bars, now, clock)`:
  - loads its own context; refuses if a session is armed (as `session.py:138` does) or no snapshot is in force;
  - the coin set is exactly the top-N of the snapshot in force, with N from the reviewed program;
  - for each coin B, builds `plan.Inputs` from the plain bars with `now` = the batch time and `plan.start` = its
    Seoul date, and runs `simulate(replace(template, leg=replace(template.leg, symbol=B)), ctx, inputs)` with a fresh
    uuid4 `comparison_id`. B passes when `report.refused is None`, no flag is red, and the report's plan hash equals
    that plan's hash;
  - journals one row of a new control-journal kind `universe_odds_batch` (under 256 KiB, `store.py:28`): the
    template plan hash, the Seoul date, `code_hash`,
    `active.state_hash`, the owner head, the rule sha256, the snapshot sha256, N, per coin (coin, plan hash, seed,
    inputs digest over the receipt sha256 list, report digest, passed), the start and finish times, and how many
    batches were already run for this snapshot and day. The kind is added to `EVENT_KINDS` (`store.py:25-27`), gets
    a closed field shape in `controller._event_data` (`controller.py:150-175`, its digests in the hex check) and joins
    the inert kinds that `_fold` skips (`controller.py:232-233`);
  - registers the result in an in-process registry keyed by identity, like `_PREPARED` (`session.py:38`).
  It imports only `core.odds`, `core.compliance` and `execution_control`, holds no `/v1/` literal, and stays inside
  `tests/control_guards.py`.
- The template plan must not use the BTC-only replay edge (`plan.py:301`).

**Preparation (universe form).** `Coordinator.prepare`, `prepare_launch_session` and `prepare_session` take the batch
object as well. Inside the unchanged 30-second window they:
- require the batch to be registered in this process and found in the journal;
- require its `code_hash`, `active.state_hash` and owner head to equal the current context's, its snapshot sha256 to
  equal `ctx.universe.snapshot_sha256`, and its Seoul date to equal the preparation's;
- require every one of the N coins to have passed; otherwise refuse. The remedy is a new study with a smaller N or
  another rule, never an ad hoc set;
- run the template plan's own fresh simulate as today, with its selection seed check (`session.py:117-146`); at
  `runner.py:201-204` the template's leg must be `upbit` and its symbol one of the N coins, instead of the profile's
  coin;
- bind `universe_batch_digest` into `PreparedSession` (`None` and left out for fixed sessions, section 10), so it enters the session id, the
  record digest and the journal row;
- cap `expires_at` at the earlier of the snapshot's `valid_until` and the next Seoul midnight, each less 60 seconds,
  so the runner's expiry check (`runner.py:359-373`) blocks buys before the controller would refuse them.

**Verification.** For a universe session, `verify_session` replaces `prepared.symbol == symbol` with: the order's
symbol is one of the batch's N coins and in `ctx.universe.eligible`, and `ctx.universe.snapshot_sha256` equals the
batch's. Every other check is unchanged. One session lasts at most until the next 09:40 KST or Seoul midnight; the
stake cap and every other session limit are unchanged. Arming stays the owner's act.

**Rules binding.** The session keeps the `rules_digest` of the profile's rules at preparation. Another coin's rules
reach the runner and controller only as a renewal in the same chain (section 10), so `rules_binding_matches` accepts
them through the chain's original digests. `session.py:218`, `runner.py:304` and `runner.py:367` stay unchanged.

The odds report's sentence that delistings and Upbit warnings are not modelled stays, and is extended to say that
rotation selection is not modelled either.

## 10. Profile, digests, terms authority and renewal

- **Universe profile.** `LaunchProfile` gets `universe_rule_sha256` (`None` for fixed profiles). A universe profile
  still carries `symbol` and `instrument_rules`; they mean the trade coin.
- **Digests.**
  - Every new field (on `LaunchProfile`, `ForwardProtocol`, `ProgramSpec` and `PreparedSession`) defaults to `None`
    and is left out of its canonical encoding when `None`: `profile_body`, `strategy._plain` and `protocol_json`
    (`strategy.py:65-67`, `172`, `600`), and the session's `fields` and `digest(fields)` (`session.py:172-180`). Each
    closed-key parser accepts the old key set or the old set plus the new keys: `strategy._object`
    (`strategy.py:567-569`, used by `parse_protocol` at `587`) and the `session_prepared` shape in
    `controller._event_data` (`controller.py:151`, `170-171`). Fixed profiles, protocols, programs and sessions
    therefore keep today's digests byte for byte, and existing journal rows still fold.
  - For a universe profile, `profile_contract_digest` leaves out the top-level `symbol` and `instrument_rules.symbol`,
    `tick_size` and `asof`. Lot, minimums, fees, `source_digest` and `universe_rule_sha256` stay pinned.
  - `rule_terms_digest(rules, *, universe_rule_sha256=None)`: with `None` it is today's function. With a value it
    drops `symbol`, `tick_size` and `asof` and adds the rule sha256 to the hashed body, so the two forms never collide.
    `InstrumentRules` gets no marker field, because `rules_digest` hashes every field and signed code reads it.
  - Every computing site passes the selector: `profile.universe_rule_sha256` at `instrument_refresh.py:75` (both
    sides use the old profile's value), `runner.py:151`, `driver.py:166`, `workflow.py:179` and `208`,
    `study.py:247` and `479`, `study_review.py:87` and `review_request.py:242`; `protocol.universe_rule_sha256` at
    `strategy._rule_terms` (`strategy.py:92-94`, used at `288`); the example profile's value at
    `prepare_launch_example.py:70`. Only with these changes do the comparisons in section 2 hold across coins.
  - `workflow._bound_profile` (`workflow.py:175-176`) compares venue, market, quote, strategy id and
    `universe_rule_sha256` instead of `symbol` for a universe protocol.
- **Terms authority.** Fixed profiles keep the v1 authority (one symbol). Universe profiles use a v2 authority with
  `universe_sha256` (the rule sha256) instead of `symbol`, tagged by version; `authority_digest` gets a v2 form.
  `E1UpbitTermsSource.read(symbol)` takes the symbol at read time for v2, at the coordinator's terms read (`coordinator.py:444`,
  reached from `_maybe_refresh_terms` and `refresh_instrument_rules`), at the cross-coin read of section 7 and in the
  rehearsal wiring. In a v2 authority, `maximum_notional_krw` is a buy cap: the parser records the observed maximum
  and never fails on it, and a coin whose observed maximum is below the cap is left out of the allow-list.
  `validate_observed_order` (`instrument_refresh.py:168-170`) checks every order, sells included, against the recorded
  observed maximum, and buys also against the v2 cap. The private
  account audit carries `terms_authority` (v1) or `universe_terms_authority` (v2); `tools/owner/rehearsal.py:364`
  checks whichever the profile uses. The audit bytes change, so the owner re-signs the strategy review.
- **Renewal to another coin.** `renew_profile` gets `allow_symbol_change`. The coordinator passes `True` only for a
  universe profile and only after its flat check (section 7). Every check that can refuse (the terms parse, the
  rule-terms digest, the contract digest) runs before the head moves (`instrument_refresh.py:102`). The new profile
  is `replace(profile, symbol=verified.rules.symbol, instrument_rules=verified.rules)`, so preflight's scope check
  (`profile.py:364-365`) and `_order`'s `symbol=self.profile.symbol` (`runner.py:351`) stay consistent. The contract
  digest, the `_HEADS` key and the client-id namespaces (`runner.py:267`, `346`, `384`) stay stable across coins. A
  fixed profile still refuses any symbol change. `Runner.refresh_instrument_rules` re-checks the same flat verdict.
- **Quote source.** The coordinator's book read takes the trade coin at read time (`coordinator.py:408-413`,
  `rehearsal.py:371`).
- **Registry bound.** `_MAX_ISSUED = 4096` is never pruned. The coordinator refuses to construct a universe window
  longer than 72 hours.
- `validate_order` still enforces the freshly observed tick on every order, and the controller's 5-minute rule
  (`controller.py:605`) is unchanged.

## 11. Orders and account capture

- **IOC.** A universe profile sends Upbit limit orders with `time_in_force: ioc`, so nothing rests on a thin book (a
  resting order would make the next slot refuse, `driver.py:323`, and stop the runner, `runner.py:462`). Sites:
  - `execution_control/model.py:95-97`: Upbit accepts `gtc` and `ioc`; KIS stays `day`, OKX stays `gtc`;
  - `execution_launch/profile.py:328-330`: a universe profile requires `ioc`; a fixed Upbit profile keeps `gtc`;
  - `execution_launch/driver.py:162-163`: expect `ioc` for a universe protocol, `gtc` for a fixed one;
  - `execution_orders/upbit.py` `_build`: add `("time_in_force", "ioc")` to the create body only for IOC orders, so the
    gtc body stays byte-identical; `parse` requires a create response's `time_in_force` to equal `ioc` for an IOC
    order, otherwise `unknown(identity_mismatch)`. Only a status read is terminal: create and cancel responses map
    to `accepted` (`upbit.py:87`), and a status response in state `cancel` maps to `canceled` with the filled quantity
    (`upbit.py:80-90`), so an IOC order's end comes from the next status read;
  - update the pins `tests/control_model.py` and `tests/renewal_boundaries.py` after review.
- The driver's limit-price rule is unchanged. A partial fill is continued at the next slot toward the same target.
- **Account capture** (`execution_accounts/upbit_collector.py`, `provider.py`, signed code):
  - add `/v1/market/all` and `/v1/orderbook` to `_ALLOWED` and to `COLLECTOR_ROUTES`;
  - read `market/all` first. A positive balance whose KRW market is not listed is left out of the ticker read and
    recorded as an unlisted position at price 0 with the read's time. The provider allows price 0 only for a position
    the capture marked unlisted;
  - a listed balance whose last trade is at most 30 seconds old is marked at the trade price, as today. If the trade
    is older, the capture reads that coin's book and marks it at the best bid if the book is at most 10 seconds old;
    otherwise the capture fails closed, as today;
  - the added reads count toward the capture's 30-second budget.
- **E1** applies the same rule: unlisted markets are left out of its ticker read (`execution/upbit_inquiry.py:94`) and
  valued at 0, not `None` (`execution/positions.py:33`), so the poll that raises the alerts keeps working.
- **Known limit.** A thin coin whose last trade is fresh is still marked at that trade price, which can sit above the
  executable bid by the spread. Equity, the floor and the daily-loss checks see that mark.
- **Dust.** The universe driver ignores holdings other than the trade coin; the coordinator handles them (section 7).
  Rehearsal still needs a fully flat account (`account_interval.py:118`), dust included.

## 12. Driver, history and coordinator

- **Driver pin (first PR, fixed-symbol profiles too).** `driver.py:244` compares
  `profile_contract_digest(observation.profile)` with `callback.identity.profile_contract_digest` instead of the full
  `profile_digest`. It also requires `observation.profile` to match the protocol's venue and market and
  `callback.profile`'s account scope. The tick
  check (`driver.py:251`, `262-263`), `_sized_signal` (`380`) and `validate_order` (`384-388`) read the rules and
  symbol from `observation.profile`. `callback.profile` stays for the account scope (`302`) and the identity rebuild
  (`435-439`). The chain itself stays checked in the runner (`runner.py:298`, `304-305`, `367-368`) and through
  `validate_observed_order` (`runner.py:356`).
- **Universe driver.**
  - A universe protocol's `symbol` is the benchmark `KRW-BTC`, never a trading pin, and a universe launch profile
    starts with that symbol, so the construction check (`driver.py:162-163`) keeps comparing them (with `ioc`). Every
    per-tick site that compares a traded symbol with `protocol.symbol` uses `observation.profile.symbol` instead: the
    quote anchor (`driver.py:271`) and the holding key (`303`). Holdings of other coins are not a driver error.
  - The target for `profile.symbol` is the decided fraction when the prior decision names that coin, otherwise 0;
    at the window end it is 0. A switch therefore happens on its own: the trade coin is sold, the coordinator renews
    to the new coin once the account is flat, and the next slot buys it. It takes two slots.
  - The prior-decision check recomputes that one decision from the chooser inputs the frame carries (below), not the
    whole history.
  - Each bar's price and tick checks use that bar's own symbol and tick. A bar whose book was `unavailable` has no
    price check and is never a quote anchor.
- **History row v2** (one row per slot, under the 256 KiB row cap):
  - the account anchor: per holding (symbol, units, mark, mark time, unlisted, dust);
  - the trade coin and its book receipt, or `unavailable`;
  - the snapshot in force: day, sha256 and the top-N list, or `unavailable`;
  - the flag read: the coins that are not `unflagged` with their class, the sha256 of the raw body, or `unavailable`;
  - the ticker read: per listed coin (market index, trade price and trade-time offset, in the section 14 encoding), the
    sha256 of the raw body, or `unavailable`;
  - the allow-list, the buy-block reasons and the events;
  - the chooser's decision (coin or cash, fraction) and its state (held decision h, hold count).
  If a row would exceed the cap, the flag and ticker parts are recorded as `unavailable` instead, and that slot has no
  buys. A row is never refused for size.
- **LiveHistory follows the trade coin.** `record_slot` takes the trade coin from the coordinator. `_anchor`
  (`live_history.py:306-307`) reads that coin's units, not the construction-time `self._profile.symbol` (LiveHistory is
  built once, `coordinator.py:802`), and `_derive` (`325`) and `_replay` (`409`) check each row's book against that
  row's recorded trade coin, not `protocol.symbol`.
- **The chooser runs in LiveHistory.** `_derive` runs the section 14 chooser at `record_slot` and at restart replay,
  incrementally: it keeps the last L+1 price vectors, h and the hold count. The `HistoryFrame` given to the driver
  carries bars with symbol, tick, book fields and a `universe_sha256` (the digest of that slot's universe record),
  plus the chooser inputs of the prior decision only (flags and top-N at k-1, prices at k-1 and k-1-L, h and the hold
  count before it). The chooser's per-tick cost then depends on the market count, not
  the slot index. The driver's per-bar checks and prefix digests stay linear in the slot index (`driver.py:247`,
  `252-264`, `284`, `377`, `379`, run twice per tick at `355` and `367`); the section 17 last-slot measurement covers
  them. The verifier keeps
  authenticating the frame against the durable journal, as today.
- **Raw bodies.** Live slots keep the parsed values above and the sha256 of each raw `market/all` and ticker body, not
  the bodies. Replay and the verifier use only the hash-chained rows.
- **Crash and missed slots.** A crash between a sell fill and the next buy is covered by the controller order
  journal, the startup reconcile, and the rule that no buy is sent while any order is uncertain, provided the restart
  records the next slot. If a slot is missed, the window ends (`live_history.py:15-16`, `323`): no later tick runs,
  including the window-end liquidation (`driver.py:290`), and whatever is held stays held. The coordinator then sets
  the sticky field `window_ended_missed_slot` and raises a red toast if a coin is held. The exit route is the
  operator's `Coordinator.submit_exit` while the coordinator still runs its monitor span, or the Upbit app. It needs
  a successful account capture and the held coin's book.
- **Window end.** The final liquidation is one IOC order. If a remainder is still held after it, a red toast asks the
  operator to use `submit_exit` or the app.
- **Coordinator.** Monitor units add the trade-coin choice and renewal after `_publish` (section 7). Slot units follow
  section 7. `CoordinatorStatus` gains `held_symbol`, `trade_symbol`, `snapshot_day`, `snapshot_sha256`,
  `universe_state`, `held_flag`, `allow_count`, `buy_block_reasons`, and the sticky `disarm_failed` and
  `window_ended_missed_slot`.
- The driver identity hashes `driver.py`, `program.py`, `strategy.py`, `runner.py`, `profile.py` and three
  `execution_control` files, including `controller.py`. These changes make a new identity, so a new history window
  (GENESIS), a new protocol and a new review are needed. Any in-flight KRW-BTC study or window finishes first.

## 13. Rehearsal coverage

Rehearsal never prepares or arms a session: its launcher passes no preparation provider (`rehearsal.py:374`), so
the shared console's `prepare` command refuses with `OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED`
(`tools/owner/launch.py:223`, dispatched at `257-262`), and the rehearsal command list (`rehearsal.py:391`) does not
offer it. Every buy ends `blocked` at `RUNNER_ACTUAL_PREPARED_SESSION_REQUIRED`
(`runner.py:361-362`). Rehearsal exercises the snapshot build and read-back, the flag and ticker reads, the allow-list,
buy decisions from cash, the trade-coin choice, renewal to a decided target while flat, the status fields and the
section 17 measurements. The odds batch, preparation with a batch, `verify_session`, buy submission, switches, sells,
IOC partial fills, dust, extra holdings and vanished coins are covered only by the offline fixture tests in section 19,
until the held-position producer exists. They are required end-to-end checks before controlled mode may be allowed for
a universe profile. The batch's runtime is measured by a separate read-only run on the owner's PC.

## 14. Universe study

**Program kind** `universe_top1_momentum` (program schema v2). Fields, all frozen per candidate: `lookback_slots` L,
`min_hold_slots` m (at least 1), `switch_margin` (a fraction, at least 0), `exposure_fraction`, `max_candidates` N
(at least 1), `universe_rule_sha256`.

**Prices.** `price_X(j)` is the `trade_price` from slot j's ticker read, defined only if X's trade time is within 60
seconds of slot j. `r_X(k) = price_X(k) / price_X(k - L) - 1`, defined only when both prices are defined. A slot whose
flag read or ticker read is `unavailable` gives no prices at all.

**Buy targets at k**: coins in the top-N of the snapshot in force at k, `unflagged` at k, with `r_X(k)` defined.

**Chooser.** One function of the recorded slot values and the decided path. It never reads anchors, fills or paper
holdings. The path starts in cash at the window's first slot. h is the last decided coin (or cash). The hold count is
the number of consecutive decisions for h. A skipped buy, a partial fill or dust never changes the decided path; the
driver keeps working toward it. A missed slot ends the window and the path. Decision at k:
1. h is `warning` at k: cash.
2. h is a coin and `r_h(k)` is undefined: keep h.
3. best = the buy target with the largest r; ties by symbol, ascending; none if there are no buy targets.
4. h is cash: best if `r_best > 0`, else cash.
5. Hold count of h below m: keep h.
6. `r_h <= 0` and (best is none or `r_best <= 0`): cash.
7. best is not h, `r_best > 0` and `r_best - r_h > switch_margin`: best.
8. Otherwise keep h.

m counts decisions. Because a switch takes two slots, a coin entered by a direct switch is held for at least m - 1
slots.

**Capture.**
- The snapshot is read through `rules.verify_universe_snapshot` from the capture process's state root, and its rule
  sha256 must equal the protocol's. The raw snapshot bytes, the raw flag bodies and the raw ticker bodies go to the
  uncapped `receipts.jsonl` sink (`study.py:382`).
- `capture.json` holds one table per distinct snapshot (sha256 to day, valid_from, valid_until and the top-N list) and
  compact per-slot frames: the snapshot sha256, the flag exceptions (coins that are not `unflagged`, with their
  class), and prices for listed coins. Fixed maxima: a market index below `MAX_FRAME_MARKETS = 320`, a flag class as
  one digit, a price as a decimal string of at most 16 characters, and a trade time as a signed millisecond offset
  from the slot within 60,000. A read with more than 320 markets is recorded as `unavailable`, never truncated; a coin
  whose price or trade time falls outside these maxima has no price at that slot.
- Books: for slot j, each candidate's chooser is updated incrementally on frames up to j-1, keeping the
  same bounded state as LiveHistory (the last L+1 price vectors, h and the hold count). The needed coins are the targets of
  decisions d[j-1] and d[j-2] of every candidate (what a flat lag-1 or lag-2 path buys) and the coin that each of the
  candidate's three evaluator paths (lag-1, lag-1 at double cost, lag-2) still holds (its sell, its mark and the
  terminal liquidation, including a sell deferred because its book was unusable). The capture replays each path from
  the recorded books and decisions with the evaluator's own step and the frozen instrument rules, so a sell deferred
  for any number of slots keeps its book request; because a replayed fill depends on the lot and minimums, a universe
  `capture` takes the profile (`--profile`) and checks its rules before any read. The set is deduplicated, cash
  skipped, plus KRW-BTC for the benchmark, intersected with the KRW markets in slot j's flag read. A needed coin missing from that read is recorded as `vanished` and not requested. If the flag read
  failed, the needed coins are requested as they are.
- New parsers return a result per market: `parse_orderbooks(receipt, symbols, now)` in `execution_accounts/quotes.py`
  and `parse_instruments(receipt, symbols)` in `execution_accounts/instrument_terms.py`. Each applies the existing
  single-market checks to each market on its own: `parse_orderbooks` keeps the 10-second book rule (`quotes.py:135`,
  `155-156`); `parse_instruments` applies `instrument_terms.py:192-201` and the receipt checks per market. If Upbit refuses several
  markets in one request (section 17), the capture sends one request per market. `parse_orderbook` and the
  single-instrument check stay as they are for the live runner.
- A book or tick that is `unavailable` or `vanished` is recorded and never raises `STUDY_CAPTURE_SOURCE_FAILED`. A
  stop, a missed slot, a sink failure or a failed account-free probe still ends every candidate's trial, as today.
- `CAPTURE_FILES` (`study.py:59-61`) gains `execution_accounts/instrument_terms.py`, `execution_accounts/universe.py`
  and `core/compliance/rules.py`, so `capture_source_code_sha256` binds every reader and parser the capture uses.
- A plan has at most 3 candidates (`STUDY_UNIVERSE_CANDIDATES_LIMIT`), so at most 16 books per slot (per candidate
  two decision targets and three held coins, plus KRW-BTC). A larger set is refused (`STUDY_CAPTURE_BOOKS_OVER_LIMIT`),
  never truncated; within the candidate cap it cannot occur.
- **Size.** A freeze check `STUDY_UNIVERSE_CAPTURE_SIZE` refuses a plan whose worst case (slots x the largest frame at
  `MAX_FRAME_MARKETS`, every coin flagged and every field at maximum length, plus 16 books, decisions and envelope)
  exceeds 12 MiB, leaving headroom under `MAX_CAPTURE_BYTES`. The check computes that worst case with the capture's
  own encoder, not from a prose estimate. A 48-hour window at 5-minute bars (577 slots) fits; any plan whose computed
  worst case is over 12 MiB is refused at freeze.

**Evaluator revision** `forward-universe-v1`:
- holds at most one coin; a switch sells A at the decision slot plus lag and buys B one slot later, like the live
  driver; the lag-2 stress uses the same rule;
- no buy at an execution slot where the target is not in that slot's top-N of the snapshot in force, is not
  `unflagged`, or has no usable book or tick; no sell of a coin at a slot with no usable book for it (the trade moves
  to the next slot that has one);
- each bar is checked and rounded with its own recorded symbol and tick (not `strategy.py:290`'s single symbol); lot, minimums and fees come from the common rules;
- NAV marks the held coin at its book midpoint, or at `price_X(j)` when the book is unavailable. If neither exists,
  that candidate ends as a disclosed failed trial; a stale mark is never carried forward. The KRW-BTC benchmark
  follows the same rule; if it cannot be marked, the trial ends for every candidate, as today;
- a vanished coin fails only the candidates whose lag-1 or lag-2 path holds it at that slot; others continue;
- the terminal liquidation is assumed to fill fully at the bid, as today. Live uses one IOC order there (section 12);
  that difference is disclosed in the review. If the held coin has no usable book at the terminal slot, that
  candidate ends as a disclosed failed trial; no ticker-price fill is assumed;
- it returns the existing `ValidationResult` and `PaperMetrics` and registers its result in `_EVALUATED`
  (`strategy.py:444-445`), so `assess_strategy` accepts it (`498-500`). `_protocol` (`strategy.py:135`, also reached
  from `parse_protocol` and the runner's tick) accepts `forward-universe-v1` as well as `forward-paper-v1`. The block
  p-value, the Sharpe bound, `build_family_commitment`, `bind_review_family`, the study review and the external signer
  are unchanged.

The study does not model the preparation-time odds check (every top-N coin must pass, or nothing is armed), the keyed
`/v1/orders/chance` refusals, or time with no armed session.

**Study rule** `upbit-krw-universe-top1-v1`, accepted alongside the old rule. The freeze-time feasibility check
becomes program-specific: warm-up L, and at most `(returns - L + 1) // max(m, 2)` round trips. A candidate needs at
least `minimum_roundtrips` (at least 20) completed exits in the window or it is excluded, whatever its returns. L, m,
the margin and the window length must make the expected number of exits clearly exceed 20.

**Family accounting.** One frozen rotation candidate is one family member; the coin it picks is not a separate test.
Every variant of L, m, margin, exposure or N and every universe-rule variant is another member. Retries count too:
`build_study_plan` takes `prior_attempts`, the registered `study_id`s of earlier attempts for the same selection, and
each protocol's `family_members` becomes the sorted union of this plan's candidate ids and those ids. `study.py:216`
changes to "every candidate carries the same family tuple and the tuple contains every candidate id". The larger K
then applies to the feasibility check, the Sharpe bound and the family-adjusted p.

**Honest limits.** There is no prior evidence for a rotation rule in this repo. A 48-hour window may not allow 20
round trips at all. A winner is never forced: no qualified candidate means no launch.

## 15. Alerts

- **E1 poll** (new catalogue entries; a toast at once, push and email through the 09:05 KST daily task). It reads the
  held coin's `market/all` entry outside the Upbit snapshot's fail-whole path, so a failed read raises only an amber
  alert and never voids E1 positions.
  - red: a held coin is no longer listed;
  - red: a held coin is `warning`;
  - amber: no snapshot in force at 09:45 KST.
- **Coordinator toasts** (in-process, toast only, no push or email), through a new public
  `core.compliance.alerts.toast(title, body)` wrapper over `_toast`, allowed in the launch guards. `_toast` runs
  PowerShell synchronously with a 60-second timeout (`core/compliance/alerts.py:216-226`), so the coordinator never
  calls it inside a unit: it queues each toast for one background thread and keeps the once-per-window or once-per-day
  dedupe itself:
  - red: the universe disarm ran, or failed;
  - red: the window ended by a missed slot while a coin is held;
  - red: an extra held coin; an unsellable remainder; a remainder after the window-end liquidation;
  - red: a dust or other non-held coin is `warning`;
  - amber: the held coin's flag is `unknown` or `absent`.

A snapshot failure at 09:12 to 09:40 KST therefore reaches push and email about a day later. A faster delivery task is
out of scope.

## 16. Approvals and order

1. The owner merges the stage-1 PRs (section 19), after any in-flight KRW-BTC study or window has finished.
2. `code-approve` on the merged head. This must come first: the current venue parser rejects `universe_rule`, so
   signing the venues file before the code would invalidate the approved state and block every buy.
3. The owner sets the `universe_rule` values, checks the edited file with the venues parser (a parse-only check
   command, or `tests/compliance_tables.py`), and only then signs `approved {kind: venues}`. A typo would otherwise
   invalidate the whole approved state.
4. The owner adds the v2 `universe_terms_authority` to the private account audit and re-signs the strategy review.
5. A new universe study is frozen, captured and selected. Only a qualified result can be batched, prepared and armed.

No rules approval and no instruments approval are needed.

## 17. Measure before any freeze

On the owner's PC, read-only; public endpoints except one owner-run keyed read:
- book freshness of thin eligible coins against the 10-second rule (`execution_launch/quote_diagnostics.py --symbol`),
  and `trade_timestamp` gaps against the 30-second capture rule and the 60-second price rule;
- the body size and market count of `market/all?is_details=true` and of `/v1/ticker` over about 289 markets, and any
  limit on markets per ticker request (these size the new body caps and `MAX_FRAME_MARKETS`);
- whether `/v1/orderbook` and `/v1/orderbook/instruments` accept several markets in one request, and the body size;
- whether `/v1/orders/chance` still reports `active` for a `warning` coin (a keyed read-only inquiry the owner runs);
- whether a delisted market leaves `market/all`, and whether Upbit skips daily candles on zero-trade days;
- the odds batch over N coins, candle paging included (up to about 19 pages of 200 rows per coin for 3650 days);
- `load_context` with snapshot verification, cold and cached, against the monitor unit and the tick;
- the monitor unit (capture with its added reads, the trade-coin choice and any renewal reads, `observe`, reconcile)
  against `monitor_seconds - prefetch_lead_seconds`;
- the slot unit: the book received by the slot within the lead; the capture, flag read and ticker read against about
  min(lead + 5.5 s, 10 s minus the book's stamp lag);
- `record_slot` plus the tick at the last slot of a 72-hour window at the shortest allowed bar (synthetic journal),
  within slot + 10 s; if it does not fit, raise the minimum bar or shorten the maximum window for universe protocols;
- the study capture's chooser update plus its reads against `_PREFETCH_LEAD`, and a real frame's size against the
  section 14 bound.

## 18. Spec and document amendments

- [Compliance spec](2026-10-23-compliance-gate-and-odds-engine-design.md): 5.1 venue facts (universe rule), 5.2 what
  is in force (the universe is runtime data admitted by the signed rule), 6.1 Intent and Context (derived coins,
  `Context.universe`), 6.2 steps 0, 1 and 5 (KRW exits of held coins; derived-coin buys need a snapshot in force).
- Docs that say "single market": `docs/launch-workflow.md`, `docs/remaining-market-readiness-2026-11-06.md`,
  `docs/upbit-quote-contract.md`, `docs/instrument-term-renewal.md`, `docs/quote-timing-diagnostics.md`.

## 19. Delivery

Six PRs, each with offline tests through the existing `transport._send` seams and fixtures:
0. **Driver pin** (section 12, first bullet), for fixed profiles too. It is the separate driver-renewal task; it lands
   first, with a test of a fixed KRW-BTC tick after a same-terms renewal.
1. **Compliance, pure:** a research note recording the rule's source URL, the `universe_rule` parser, `UniverseRule`, `Venue.universe_rule`, `rule_sha256`, the flag
   classes, `universe_eligible`, `verify_universe_snapshot`, the snapshot format, the encode helper and
   `owner.universe_path`. Safe to merge early: no signed venues file carries the rule until the owner signs it after
   code-approve.
2. **Data:** the public helpers in `execution/upbit_inquiry.py`; `execution_accounts/universe.py` (snapshot builder,
   `daily_bars`, and the per-slot flag and ticker source with its pins and body caps); `execution_launch/universe_store.py`
   and its CLI.
3. **Gate:** `Universe`, `Context.universe`, the read-back in `load_context`, the gate exit, buy and recorded-order
   paths, the public `lookup` and its callers, and the compliance-spec amendments.
4. **Execution** (may be split): `RiskResult.universe`; `OrderState` fields; `Controller.kill` reason; the odds batch,
   its `universe_odds_batch` journal kind and its console command; the session's batch binding, expiry cap and verification; universe profile, digests,
   selectors and terms authority v2; renewal with `allow_symbol_change`; the quote source symbol; IOC; collector,
   provider and E1 changes for unlisted and thin coins; the universe driver; history row v2 and the chooser in
   LiveHistory; the coordinator sequence, trade-coin choice, events, `_disarm_locked`, allow-list, toasts, status
   fields and the 72-hour bound; the runner's allow-list and sell guard.
5. **Study:** the program kind and chooser, the evaluator revision, the capture with its parsers, `CAPTURE_FILES` and size check,
   `prior_attempts`, the candidate cap, the study draft tooling (`tools/research/prepare_shortened_study.py`,
   `prepare_launch_example.py`), and the docs.

**Tests:**
- rule parsing, including unknown keys and today's closed-key failure;
- flag classes: a missing coin, a missing `market_event`, a missing or non-boolean key, an unknown caution key;
- snapshot: the exact request set, finality from content, recompute in `load_context` without importing
  `execution_*`, the in-force window and the 09:40 KST switch, a failed request, a tampered receipt, a rebuild that
  leaves earlier files intact, and a read-back that raises `TypeError` while a held-coin exit still gets ALLOW_EXIT;
- gate: map coins unchanged; derived-coin buys need a snapshot in force and eligibility; KRW exits of a held coin with
  no snapshot, in the recovery state, and after the rule is dropped; a cancel of a derived-coin buy with no snapshot;
  `screen` and `simulate` on a derived eligible coin; `grey_rows` for a derived coin;
- odds and session: an unregistered or tampered batch; a batch whose code hash, state hash, owner head, snapshot or
  date differs; a batch with one failed coin; the expiry cap; `verify_session` for a coin outside the N and after the
  snapshot changes; the template's selection-seed check; a journal with a pre-change `session_prepared` row
  still folds; a `universe_odds_batch` row folds as inert;
- digests and renewal: a fixed profile's and protocol's digests byte-identical to today's; the same rules give
  different fixed and universe digests; a renewal from A to B keeps the contract digest and passes preflight; a fixed
  profile refuses a symbol change; a symbol change is not issued while an IOC order in A is uncertain with zero A
  balance, A keeps renewing, and a later A fill can still be sold; the session rules binding holds across a switch;
  a v2 maximum below the cap leaves the coin out of the allow-list and still renews a held coin; a held-coin
  sell above the v2 cap passes; a partial IOC sell leaves under 5,000 KRW of A at its frame mark, the next monitor unit
  counts the account flat in A and renews to B, and the next slot buys B;
- per-slot: a terms failure while flat records the slot and blocks buys only; a held coin's terms failure keeps
  today's block; a failed flag or ticker read is recorded and blocks buys only; a book failure records a no-book bar
  and skips the tick; a `record_slot` failure still runs the events and skips the tick without stopping the runner; an event failure still records the slot;
- events: a vanished held coin stops the coordinator and disarms once, with the kill reason and the owner
  `system_disarm`; `Controller.kill` raising inside `_disarm_locked` sets `disarm_failed`, queues the red toast, and
  the slot is still recorded; a slow toast does not delay the tick; an extra holding blocks buys without stopping the runner; an unsellable remainder; a dust coin with
  `warning`; a held coin with `unknown` flags is not sold;
- account capture: a thin coin marked by the bid; an unlisted dust coin next to a held coin, with `submit_exit`,
  `cancel` and slots still working; a failed `market/all` read inside the capture fails closed;
- orders: the IOC create body, the gtc body unchanged, `validate_request` refusing an IOC body without the field, an
  IOC cancel with a partial fill, the sell guard;
- driver and history: the two-slot switch; a crash with a restart before the next slot; a crash that misses a slot
  ends the window and sets the status field; the prior-decision check from carried inputs; per-bar tick checks; the
  row size fallback; the 72-hour bound;
- study: the chooser cases, one family member per frozen rotation, `prior_attempts` in K, the candidate cap, frame
  causality of book selection, a lag-2 switch (A, A, B, B) with the terminal bar, the warning exit through rule 1, a
  failed ticker frame, one stale book among several, a vanished non-held coin, a vanished coin held only in the lag-2
  path, an unavailable held-coin book marked from the ticker, one at the terminal slot, an unavailable
  benchmark, the worst-case size at 577
  slots and a long window refused at freeze, and an evaluator run on a capture alone;
- guards that must stay green: `tests/compliance_guards.py` and `tests/control_guards.py` (unchanged),
  `tests/accounts_guards.py` and `tests/launch_guards.py` (new entries), `tests/execution_guards.py` and
  `tests/renewal_boundaries.py` (pins updated after review, not regenerated blindly), `tests/launch_study.py` and
  `tests/compliance_tables.py`.

## 20. Stage 2 hook

Stage 2 holds several coins at once. It starts only after a separate multi-coin study qualifies and the owner signs
it; an amount threshold, if any, lives in private configuration. Stage 1 keeps it possible without building it:
decisions and anchors are lists of (symbol, fraction or units), and the driver caps their length at 1.

## 21. Real odds

- Without a real edge, no method that keeps the floor can beat (W0 - F) / (T - F), where W0 is the start, F the floor
  and T the target (the odds card's wording, `core/odds/report.py:231`).
- Stage 1 does not keep the floor. A buy is sized as `exposure_fraction` of NAV, and the live floor reacts only after
  equity is already below it (`execution_control/risk.py:283`), so one held coin can gap below F between slots. For
  stage 1 the general no-edge bound is W0 / T. Any chance above (W0 - F) / (T - F) comes only from breaking the floor.
- Widening the universe does not raise either ceiling. Under a deadline, higher volatility can raise the chance of
  reaching T in time, but never above the ceiling; expected end wealth stays at W0 less fees, so the chance of ending
  at or below F rises more. Each switch costs fees (the engine assumes 10 bp per side).
- Only a real edge changes this, and only a qualified study can show one. This repo has no such evidence for altcoins
  or rotation yet.
- Stage 1 does not resolve the open floor decision. While the floor equals the start equity, no coin can start.
