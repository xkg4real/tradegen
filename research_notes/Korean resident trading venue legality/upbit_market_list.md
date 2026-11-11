# Upbit KRW market list and flags for the universe rule

Recorded on 2026-11-11 (KST) for the optional `universe_rule` key of the upbit entry in `core/odds/venues.yaml` (Upbit KRW universe design, `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, sections 2 and 4). The design checked Upbit's public developer docs on 2026-11-11; this note records the facts the rule rests on, with their source. No API call was made.

| Fact | What the page says | Where TRADEGEN uses it | Source |
|---|---|---|---|
| Market list | `GET /v1/market/all` lists every trading pair. With `is_details=true`, each market object also carries `market_event`. | The daily snapshot's first read. `listed` is every `KRW-<base>` market in it whose base matches `[A-Z][A-Z0-9]{0,11}`. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Warning flag | `market_event.warning` is a boolean: the market is designated for investment warning. | Flag class `warning`: a held coin is sold and the coin is never bought. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Caution flags | `market_event.caution` holds five booleans: `PRICE_FLUCTUATIONS`, `TRADING_VOLUME_SOARING`, `DEPOSIT_AMOUNT_SOARING`, `GLOBAL_PRICE_DIFFERENCES`, `CONCENTRATION_OF_SMALL_ACCOUNTS`. | Flag class `caution`: a held coin is kept as the strategy decides, and the coin is not bought while any caution key is true. | https://docs.upbit.com/kr/reference/list-trading-pairs |
| Rate limit | The market group allows 10 calls per second per IP. | The transport's 0.2-second pacing keeps the daily build under it. | https://docs.upbit.com/kr/reference/list-trading-pairs |

Limits of this record:

- No API field announces a scheduled end of trading support, so a delisting is not seen before the market leaves the list; its flag class is then `absent`.
- A missing or non-boolean `warning` or known caution key gives the class `unknown`, never `unflagged`, so a changed response shape blocks buys instead of allowing them. An unknown caution key that is `true` gives `caution`.
- The daily candle facts the age and value reads rest on (candles close at 00:00 UTC, `to` is exclusive, a day with no trade may have no candle) come from the design, sections 2 and 5, not from this page. Section 17 of the design measures the zero-trade case before any freeze.
- The owner confirms the rule values when signing `approved {kind: venues}`.
