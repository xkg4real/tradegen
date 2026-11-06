# Current instrument terms and same-contract renewal

This path replaces an old observation with a new read. It does not change a
profile's economic contract or grant approval to trade. KIS and OKX renewal are
unsupported and refuse explicitly.

## Sources and scope

Checked against official documentation on 2026-11-06, without calling an API:

- [Upbit order availability](https://docs.upbit.com/kr/reference/available-order-information)
  defines the authenticated GET for a single market. It reports bid/ask and maker
  fee rates, the nested market's allowed sides/types, minimum/maximum notionals,
  state and asset currencies. The required key permission is order inquiry.
- [Upbit orderbook instruments](https://docs.upbit.com/kr/reference/list-orderbook-instruments)
  defines the public GET for a market's current tick and supported aggregation
  levels. Its schema includes `market`, `quote_currency`, `tick_size` and string
  `supported_levels`. The implementation requires KRW and native level `"0"`.

The signed E1 allowlist adds exactly those two GETs. `execution/upbit_inquiry.py`
retains their literal paths and constructs the exact single-market query. No
arbitrary URL, method, query or order request enters this source. Existing timeout,
retry, rate pacing and managed-route behavior are inherited from E1.

## Reviewed authority and receipts

`execution_accounts.instrument_terms.TermsAuthority` requires an opaque account
scope, exact KRW symbol, quantity lot and minimum, maximum notional, source-document
and identity-binding digests, and explicit validity dates. There are no guessed
values. The API does not establish which configured key corresponds to that opaque
scope or provide every quantity constraint. The owner/deployment review must
establish these inputs; constructing this record is not an electronic signature.
Its stable `authority_digest()` is the profile rules' `source_digest`.

`E1UpbitTermsSource(authority=..., clock=..., route=...).read()` performs the fixed
reads only when called. It verifies original bytes, request/receive clocks,
server clock bounds, market state and exact constraints. `asof` is the older
receipt instant, never a caller-supplied refreshed timestamp. The two reads must
complete within 30 seconds and the resulting snapshot remains usable for at most
five minutes. Unequal bid/ask/maker fees, different side minima, a changed maximum,
missing fields and unsupported markets refuse rather than collapse into a single
invented term.

Raw receipt hashes and times form a separate observation evidence digest. They
must not replace the stable source digest: that would silently change the frozen
research contract. Original bodies can contain balances and remain private, are
excluded from representations, and must not be committed or placed in public logs.

Only a read issued in this process enters the issuance registry. Pure parsing,
serialized copies and timestamp edits cannot issue observations. For a known
issued authority, a rule snapshot without a matching issued observation is refused.
Initial observed snapshots and later renewals both enforce the observed maximum
notional at the controller boundary, including sells.

## Applying a renewal

The owner coordinator may call the following under its work lock:

```python
observation = terms_source.read()
now = clock()
renewal = renew_profile(current_profile, observation, now=now)
current_profile = runner.refresh_instrument_rules(renewal, now=now)
```

`renew_profile` admits only an unchanged economic/source/profile contract. It
rejects stale or future evidence, receipt replay, clock rollback, scope changes and
branches from an obsolete profile snapshot. Its in-process chain permits the
original prepared session to reference a genuinely renewed observation. It retains
the original prepared object and session ID, owner arm, session expiry, code/state
hashes, strategy review and policy. It does not renew any of those authorities.
A changed lot, tick, fee, source, scope or other contract field requires a new
review/preparation instead of automatic replacement.

`Runner.refresh_instrument_rules` serializes against ticks, updates the full runtime
profile digest and launch wrapper together, and preserves the prepared object.
Renewal is permitted after a strategy stop so protective exits can use current
terms; it never clears the stop latch. Controller freshness, signed context, risk,
capacity, legal eligibility, order reconciliation and all other checks still run.
Coordinator monitoring can refresh before the five-minute expiry; a failed refresh
blocks entries while account monitoring and reconciliation continue.

The registry is process-local and bounded at 4,096 issued observations/renewals.
A restart cannot recreate an issued session/chain from JSON: fresh evidence,
reviewed restart and preparation remain necessary. Constructing the terms source
registers its authority without I/O, so stored snapshots under that authority
refuse until a fresh read. The legacy `InstrumentRules` format has no provenance
version tag: unknown-source legacy objects still use the pre-existing trusted
caller contract and are not authenticated by this feature. A new terms deployment
must construct its reviewed source and read fresh evidence before entering order
control; omitting that source does not constitute an authenticated restart. No background worker or API
call is started by importing or constructing any of these objects.

## Validation and limits

`tests/launch_instrument_refresh.py` uses invented data and a fake E1 transport.
It covers immutable identity, stale/future/time-relabelled receipts, malformed
payload/query/scope, changed source/economics, replay and fork refusal, exact
maximum notional, genuine-session continuity without extending its expiry, and
renewal after stop without restarting entries. Live PC behavior and actual account
identity are not established by these tests.

This is a development record, not legal, tax or investment advice. The author is
not a licensed adviser.
