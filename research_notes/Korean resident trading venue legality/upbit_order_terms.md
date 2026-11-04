# Upbit KRW order terms for the odds engine

Checked on 2026-11-05 (KST) for `core/odds/venues.yaml`. Everything below comes from Upbit's public developer docs. No API call was made.

| Value | What the page says | venues.yaml | Source |
|---|---|---|---|
| Quantity step (lot) | The order FAQ's market-buy example drops every digit from the 9th decimal place on and shows 0.33333333. It says the leftover usually comes from amounts that do not divide out to 8 decimal places. The limit-buy guide's sample code for KRW-BTC also rounds the volume down to `Decimal('1e-8')` before it places the order. An order quantity therefore carries at most 8 decimals, a step of 0.00000001. | `lot: {units: {default: 0.00000001}}` | https://docs.upbit.com/kr/docs/faq-order (page updated 2026-05-04); https://docs.upbit.com/kr/docs/limit-bid-order-creation (page updated 2026-07-14) |
| Fixed charge per fill | The order-information reference gives the fees only as rates: `bid_fee`, `ask_fee`, `maker_bid_fee` and `maker_ask_fee` are each a 수수료율 (sample value 0.0005). The limit-buy guide says a buy needs the order amount plus the fee on that amount, so the fee scales with the order. None of the pages read lists a fixed KRW charge per order. | `fee_extras: {phi_buy: 0, phi_sell: 0}` | https://docs.upbit.com/kr/reference/available-order-information (page updated 2026-11-04) |

Limits of this check:

- The 8-decimal step comes from two examples, the FAQ's market buy and the limit-buy sample code, both on KRW-BTC. No Upbit page states it as a rule or gives a quantity step per coin, so KRW-USDT rests on the same examples.
- "No fixed charge" is read from the absence of any fixed-amount fee field. Upbit does not say it in a sentence.
- The KRW minimum stays 5,000 KRW (https://docs.upbit.com/kr/docs/krw-market-info). That page has no fee rate today; it links to the customer-center guide instead.
- The owner confirms both values when signing `approved {kind: venues}`.
