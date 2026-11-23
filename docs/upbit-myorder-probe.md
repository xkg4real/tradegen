# OQ18: private myOrder observation

This standalone research tool observes one authenticated Upbit `myOrder`
WebSocket session. It does not change the public A0 tool, D14 code, capture
allowlists, account state or trading permissions. It sends one subscription,
never an order, order test, cancellation, transfer, or `myAsset` subscription.

## Owner procedure

1. Use a **separate observation key** with the narrowest read permissions the
   owner has verified, and the intended IP restriction. Do not reuse QUANTGEN
   credentials or add order, transfer, withdrawal or pocket-management rights
   to make the probe pass. The repository's Upbit research records the exact
   `myOrder` permission requirement as undocumented; this tool cannot inspect
   or prove the key's permission list.
2. On the owner's Windows PC, use the existing environment containing
   `websockets==16.0` (already pinned in requirements and constraints). Check it
   without connecting or entering a key:

   ```powershell
   .\.venv\Scripts\python.exe -B tools\research\upbit_myorder_probe.py --check-dependencies
   ```

3. In a private interactive terminal, run a finite observation. Replace the
   output path with a **new file** in the day's records folder:

   ```powershell
   .\.venv\Scripts\python.exe -B tools\research\upbit_myorder_probe.py --duration-seconds 120 --max-events 100 --output "<records-folder>\myorder-observation-01.jsonl" --allow-private-network
   ```

4. Enter the separate Access Key and Secret Key only at the hidden local prompts.
   Never put keys in the command, chat, email, an output file or repository. There
   is no `.env`, credential-file or environment-variable fallback. A noninteractive
   or echoed prompt is refused. Credentials exist temporarily in process memory;
   the tool does not claim guaranteed memory erasure. It does not save them.
5. Let existing account activity occur naturally. **Do not place an order to
   manufacture a test event.** Silence is a valid observation. Review the final
   status and metadata file; keep the file private and report only the status,
   event count and diagnostic codes when coordinating work.

The duration is 1–3600 seconds, maximum observed events 1–1000, maximum message
64 KiB and inbound frame queue 8. Opening is bounded at 10 seconds, subscription
sending at 5 seconds, and closing at 2 seconds. The observation budget includes
connection and subscription; close cleanup can add up to 2 seconds. A failed
close aborts the transport. Existing files are never overwritten. There is no
automatic reconnection, credential broadening or quota retry.

## Interpret the result

| Result | Meaning |
|---|---|
| `SILENT_ENTITLEMENT_UNPROVEN` | TLS/WebSocket connected and the locally valid subscription was sent, but no qualifying myOrder event arrived. This does **not** establish server acceptance, entitlement, or a missing permission. |
| `MYORDER_EVENT_OBSERVED` | A structurally recognised myOrder message arrived. This establishes observed delivery during this session, not the complete permission list or production data coverage. |
| `AUTH_OR_PERMISSION_REJECTED` / `AUTH_REJECTED` | Authentication or permission was refused. The tool does not identify the exact missing privilege; diagnose without adding trading privileges. |
| `SUBSCRIPTION_REJECTED` | The server returned an error. Only allowlisted error names are kept; its message is discarded. |
| `RATE_LIMITED_STOP` | HTTP 429/418; stop. A numeric Retry-After is retained when provided. Coordinate shared usage before any separate later attempt. |
| `CONNECTION_CLOSED`, timeout, format or transport refusal | Observation stopped. Previously observed metadata remains; failure never grants permission or retries automatically. |

The report distinguishes connection, locally validated subscription, sent-but-
unconfirmed subscription and observed event. There is no invented subscription
acknowledgement. `provider_permission_state` remains `UNKNOWN` even after delivery.
`entitlement_confirmed`, `source_complete`, `fill_authority` and `execution_ready`
remain false. Presence of an `is_maker` field is only a schema observation; it does
not establish participant-side semantics, own-fill matching or fill authority.

Only timestamps, fixed diagnostic codes, message lengths, allowlisted state names,
counts and presence of predetermined field names are saved. Raw messages, UUIDs,
symbols, price/size/fee values, account identifiers, JWTs, keys, exception text and
raw-message hashes are not saved. The WebSocket logger is isolated and disabled
to prevent inherited debug logging from exposing the handshake or payloads.

## Endpoint, limits and evidence

The endpoint is fixed to `wss://api.upbit.com/websocket/v1/private`, with normal
TLS hostname and certificate verification. Redirects, proxies, compression and
Origin headers are disabled. JWT uses HS512, a fresh nonce and the raw secret,
matching the existing no-query algorithm without importing execution code.

OQ17 remains a shared-usage coordination issue. This tool makes one connection
attempt and sends one application subscription; WebSocket ping/pong control
frames may maintain the connection. It does not poll by IP, change IPs/accounts,
divide traffic across keys, or evade limits. Repository research records
connection limits of 5/s and message limits of 5/s and 100/min; these are dated
documentation, **not newly measured or guaranteed current limits**. If a provider
limit/permission changes or a 429/418 occurs, forward the diagnostic and revised
official limit to the project owner before another run. The tool does not update
the shared budget automatically.

Sources: repository [Upbit venue research](superpowers/plans/wip-2026-10-24/venues/upbit.md)
sections 5–6; [WebSocket guide](https://docs.upbit.com/kr/reference/websocket-guide),
[myOrder](https://docs.upbit.com/kr/reference/websocket-myorder),
[rate limits](https://docs.upbit.com/kr/reference/rate-limits).

Offline test command:

```text
python -B -m unittest tools.research.test_upbit_myorder_probe -v
```

Synthetic tests use dummy keys, fake connections, temporary files and a socket
guard. Real owner permissions, live delivery and Windows terminal behaviour have
not been tested in Cloud. A partial log or missing terminal row denotes an
unfinished observation, never a successful connection or entitlement check.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
