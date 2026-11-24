# Amendment P1 to the passkey archive API: clientDataJSON members and the REJECTED close row

Date: 2026-11-24 (Asia/Seoul).
Status: owner-approved on 2026-11-24 (O11-3: "3a 3b 모두 권장 승인"). This document records two places where the
merged broker (PR #66, merge `e807b60`) differs from the 2026-11-13 passkey specs, and amends the specs to match the
code. It changes no code. It signs nothing, arms nothing and sends no order.

**Sources.** The specs live on the `handoff` branch under `context/upbit-universe/gpt-20261113/`. Each was written
once and not changed since; spec line numbers below refer to these blobs:

| Name | File | Commit | Blob |
|---|---|---|---|
| ARCHIVE | `TRADEGEN_PASSKEY_ARCHIVE_API_2026-11-13.md` | `c051016` | `49698bc` |
| FOUNDATION | `TRADEGEN_PASSKEY_FOUNDATION_API_2026-11-13.md` | `b0c148c` | `6a62230` |
| LEDGER | `TRADEGEN_PASSKEY_GRANT_LEDGER_API_2026-11-13.md` | `cbfb15b` | `0bca6fa` |

All three exist with these blobs at `cbfb15b` and at the handoff head `1a579bf`. Code citations are main `b828b2d`.
Where this document and those specs disagree, this document wins.

## P1-1. clientDataJSON: unknown members are ignored (O11-3a)

**Spec text replaced.** ARCHIVE:128 says only `{type, challenge, origin}` plus an optional `crossOrigin` are allowed,
and that `topOrigin` and any other member are refused. FOUNDATION:28 lists "unknown/duplicate keys ... 거절" next to the
JSON limits, which reads as covering clientDataJSON too.

**Why.** Chrome and Edge add a random extra member to clientDataJSON in some ceremonies (WebAuthn Level 3, 5.8.1, tells
relying parties to ignore unknown members for this reason). Under the old text about 1 in 5 real Chrome or Edge
approvals failed.

**New rule (ARCHIVE section 7, second bullet).** The two member-set sentences of ARCHIVE:128 are replaced: the
allowlist sentence (exact required `{type,challenge,origin}` plus an optional `{crossOrigin}` that must be exactly
false) and the refusal sentence ("topOrigin 및 미지원 필드는 거절한다"). The rest of that bullet stands: the
`type` values per ceremony and the exact decoded challenge comparison are repeated below so the bullet reads complete.

- clientDataJSON is admitted first exactly as `contract.decode` does it (`contract.py:114-162`): not empty, at most
  16 KiB and valid UTF-8 (else `PASSKEY_FORMAT_INVALID`, `contract.py:115` and `:161-162`; the request parsers refuse
  an oversize body earlier with the same code, `:310`, `:334`, `:462`, `:474`); depth at most 12 and at most 4096
  structural nodes (else `PASSKEY_RESOURCE_LIMIT`, `contract.py:138`); no duplicate keys, no JSON float or exponent
  number, no `NaN` or `Infinity`, integers of at most 19 characters within signed 64-bit, anywhere in the body (else
  `PASSKEY_FORMAT_INVALID`). FOUNDATION:28 still applies to duplicates and to every other JSON and CBOR structure.
- The body must be a JSON object, and `type`, `challenge` and `origin` are required. A missing one gives
  `PASSKEY_FORMAT_INVALID`.
- `topOrigin` is refused with `PASSKEY_ORIGIN_RP_INVALID`, whatever its value.
- `crossOrigin`, if present, must be exactly `false`; anything else gives `PASSKEY_ORIGIN_RP_INVALID`.
- Unchanged value checks: `type` is exactly the string `webauthn.create` for registration and `webauthn.get` for an
  assertion (else `PASSKEY_FORMAT_INVALID`); `origin` is a string exactly equal to the RP origin (else
  `PASSKEY_ORIGIN_RP_INVALID`): at registration the enrollment request's RP, taken from the config (`engine.py:348`,
  `webauthn_verify.py:165`), and at an assertion the stored credential's RP (`authority_replay.py:200`,
  `webauthn_verify.py:207`); the grant binds that RP only through its `config_sha256` and
  `initial_credential_sha256`; `challenge` is canonical unpadded base64url of exactly 32 bytes (else
  `PASSKEY_FORMAT_INVALID`) equal to the expected challenge (else `PASSKEY_CHALLENGE_INVALID`, public
  `PASSKEY_TARGET_CHANGED`).
- Every other member that passes the admission above is ignored. This includes the Level 2 `tokenBinding` member,
  which the RP never supported and Level 3 removed.
- The raw clientDataJSON bytes are kept unchanged and stay inside the signed data and the evidence digest, so an
  ignored member is still covered by the signature and by replay.

**Code.** `tools/approval_broker/webauthn_verify.py:79-87` (`_client`), `tools/approval_broker/contract.py:79-87`
(`unb64`) and `:114-162` (`decode`). Test:
`tests/launch_passkey_webauthn.py:167`
(`test_unknown_client_member_verifies_but_top_origin_cross_origin_and_missing_members_refuse`).

## P1-2. A REJECTED close row carries its evidence (O11-3b)

**Spec text replaced.** ARCHIVE:148 (section 8.1) gives the REQUEST_CLOSED payload as
`{request_sha256, state, reason, evidence_sha256?, notification}`, and LEDGER section C5 says REQUEST_CLOSED uses the
section 8 fields exactly.

**Why.** ARCHIVE 8.3 closes an authenticated request whose target or current conditions changed with a fixed REJECTED
result, and the credential counter moves forward. A row that holds only the evidence digest cannot be checked again
when the ledger is replayed from its genesis. Replay could neither re-verify the assertion nor rebuild the counter.

**New rule (ARCHIVE 8.1 table, REQUEST_CLOSED row).**

```
REQUEST_CLOSED  {request_sha256:H, state:"EXPIRED"|"REJECTED", reason:Code, evidence_sha256:H?,
                 evidence:WebAuthnEvidenceV1 (REJECTED only), notification:NotificationV1}
```

- `state:"REJECTED"`: `evidence` is required, `evidence_sha256` must equal its digest, and `reason` must be one of
  the closing reasons (`REJECTION_REASONS` in `authority_contract.py`; at `b828b2d` these are
  `PASSKEY_TARGET_CHANGED`, `PASSKEY_OWNER_CHANGED`, `PASSKEY_GRANT_INVALID`, `PASSKEY_CLOCK_INVALID` and
  `PASSKEY_EXPIRED`).
- `state:"EXPIRED"`: no `evidence` member, `evidence_sha256` is null, the request must still be PENDING, and the
  row's time must be at or after `min(challenge_expires_at, approval_expires_at)`, or `challenge_expires_at` alone
  when `approval_expires_at` is null (`authority_replay.py:369-370`, `:382-383`). The engine writes
  `reason:"PASSKEY_EXPIRED"` on these rows (`engine.py:549-551`); replay does not check that reason yet.
- `state:"INVALIDATED"` is refused in a REQUEST_CLOSED row (`authority_replay.py:382`). This overrides LEDGER:92,
  which lists it there; INVALIDATED comes only from a registry-epoch change or AUTHORITY_DISABLED.
- Replay of a REJECTED row requires, among other checks: the request is PENDING and still live, that is before
  `min(challenge_expires_at, approval_expires_at)` at the row's time, and the digest and reason above match
  (`authority_replay.py:369-379`, the REQUEST_CLOSED REJECTED branch); the evidence names the same request and request
  ID; the registry epoch and grant are unchanged; the credential is still ACTIVE; `requested_at <= received_at <= `
  the row's time, inside the challenge window (`authority_replay.py:188-205`, `_assertion`). It then re-runs the
  WebAuthn verifier on the stored evidence at its original `received_at` and advances the credential counter from it.
  A row that fails any check is refused, and nothing after it is applied.
- LEDGER C5's "exact section 8 fields" now means the fields above.

**Code.** `tools/approval_broker/engine.py:546-560` (`_close`) writes the row as stated. The row parser
`tools/approval_broker/authority_contract.py:745-754` (exact key set, `evidence` only on REJECTED, the REJECTED digest
and reason) together with replay `tools/approval_broker/authority_replay.py:367-385` enforce it, except the EXPIRED
reason noted above. The parser is the only place that refuses an `evidence` member on an EXPIRED row. On its own the
parser is looser on two points: it also admits `state:"INVALIDATED"` and a non-null `evidence_sha256` on a
non-REJECTED row, which replay then refuses.
Tightening the parser to match is a later cleanup candidate; no spec change is needed for it. Tests:
`tests/launch_passkey_ledger.py:240`
(`test_rejected_close_replays_only_live_authenticated_evidence_and_advances_counter`) and
`tests/launch_passkey_engine.py:158`
(`test_actual_packet_modification_is_rejected_before_apply_and_on_current_read`).

## Not changed

- Which refusals close an authenticated request (ARCHIVE 8.3) is unchanged here. O11-1 and O11-7 change that in their
  own PRs, and each PR states its spec effect.
- The specs give only the public Code allowlist (ARCHIVE:172), not the internal-to-public mapping in `cli.py`
  (`_INTERNAL_CODES`). O11-7's own PR changes the public code for a signed counter regression
  (`PASSKEY_COUNTER_INVALID`) from `PASSKEY_REQUEST_REUSED` to `PASSKEY_SIGNATURE_INVALID` (at `b828b2d`, `cli.py:51`
  still maps it to `PASSKEY_REQUEST_REUSED`); both are in that allowlist, so no spec text changes.
- The `handoff` copies of the three specs are not edited by this PR. The next hand-off can point readers here.
