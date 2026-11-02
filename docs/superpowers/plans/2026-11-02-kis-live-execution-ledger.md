# KIS live market-data execution ledger

## Contract and implementation

- Inspected all22 uploaded XLSX references (353 sheets); catalogued32 public
  WebSocket contracts with1487 exact positional fields and source hashes/rows.
  Account/order notification channels, contradictory TR identifiers and unresolved
  source time/price scaling are not silently admitted. Original uploads and example
  authentication values are not committed.
- Added explicitly controlled market subscriptions, fixed HTTPS approval origins,
  memory-only approval state, bounded parsing/reconnect/buffers, exact decimals,
  exchange/receipt time separation and stale/delayed/partial-market labels.
  Compatible same-market trade/book companions share a session; no venue mixing.
- Added KIS Live navigation with latest trades, depth, spread, imbalance and sampled
  return/VWAP. Navigation, remount, in-flight start, stop timeout and window close
  retain/clean up the one session without silently starting another.
- Official references specify non-TLS WebSocket transport. The UI and runbook
  disclose it; no undocumented secure endpoint or automatic fallback is invented.
  These observations do not become authenticated execution evidence.

## Measured focused verification

- Final KIS suite: **45 PASS, 0 FAIL, 0 NOT_RUN** (catalog12, backend16, UI13,
  integration guards4). All HTTP/WebSocket paths are faked; swallowed unfaked
  transports and leaked market workers fail the suite.
- Existing cockpit and Flet API guards: **51 PASS, 0 FAIL, 0 NOT_RUN**.
- Independent read-only contract/security/lifecycle review found no remaining
  blocking issue. The source parser fields were compared with uploaded XML.
- Actual Chromium/Flet localhost preview found an Expanded child inside a wrapped
  header; fixed the layout and added a regression. The corrected screen rendered
  controls/cards/tables. Preview used an explicitly refusing session factory and a
  local Korean font only in the external preview harness; native Windows rendering
  still requires operator verification. No KIS connection was opened.
- The restricted Cloud network sandbox causes even a minimal asyncio.to_thread
  program to stall on loop shutdown. The identical program exits under the allowed
  localhost-capable test environment. KIS suite retains its own raw socket,
  HTTP/WebSocket and KEYLESS guards under that environment; no guard was relaxed.
- Initial UI helper traversal and suite-help registration failures were corrected;
  they are not counted as passing runs. Full integrated QA follows this source
  checkpoint and is reported separately in final validation.

No real key/account read, real API request, actual owner signature, activation or
order was performed. Frozen strategy research remains unchanged with zero passing
candidates. Runtime source is frozen for the final acceptance run.
