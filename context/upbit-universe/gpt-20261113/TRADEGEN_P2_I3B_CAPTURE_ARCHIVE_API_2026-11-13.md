# P2 I3b-archive exact API — 2026-11-13

Implementation contract, not source authentication, a current account assertion, or trading permission. Existing loss limits remain unchanged. This unit archives complete returned I3a stages; it does not invent receipts from an aborted collector.

## Pure format: execution_launch/guard_capture_format.py

Constants: `SCHEMA_VERSION=1`, `REPLAY_REVISION='guard-capture-material-v1'`, `PACKET_DOMAIN=b'tradegen-continuous-capture-packet/1\n'`. Fixed errors `GuardCaptureFormatError(ValueError)` with `CAPTURE_FORMAT_INVALID`, `CAPTURE_RESOURCE_LIMIT`, `CAPTURE_LIMITS_INVALID`, `CAPTURE_PAYLOAD_MISMATCH`, `CAPTURE_BASELINE_MISMATCH` only.

`CaptureFormatLimits` frozen/slotted/keyword-only, exact positive integers no bool, defaults are hard ceilings: `max_packet_bytes=64*1024*1024`, `max_baseline_bytes=65536`, `max_receipts=2000`, `max_receipt_bytes=8*1024*1024`, `max_total_receipt_bytes=64*1024*1024`, `max_total_bytes=128*1024*1024+65536`, `max_nodes=2000000`, `max_text_bytes=16*1024*1024`, `max_depth=24`, `max_rows=100000`. `DEFAULT_LIMITS`.

```python
@dataclass(frozen=True, kw_only=True, slots=True)
class CapturePayload:
    logical_id: str
    original_name: str
    byte_count: int
    sha256: str

@dataclass(frozen=True, kw_only=True, slots=True)
class EncodedCaptureArchive:
    packet_sha256: str
    previous_state_sha256: str
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime
    inventory: tuple[CapturePayload, ...]  # exact sorted whole payload set
    payloads: Mapping[str, bytes]         # detached MappingProxyType; repr=False

@dataclass(frozen=True, kw_only=True, slots=True)
class RetainedCapturePacket:
    packet_sha256: str
    previous_state_sha256: str
    staged: StagedContinuousCandidate     # repr=False; decoded private snapshot
    previous: BaselineState               # repr=False; actual baseline codec checked
    inventory: tuple[CapturePayload, ...]
    # properties source_authenticated/current_freshness_verified/guard_committed/execution_ready=False

build_capture_archive(staged, previous, *, limits=DEFAULT_LIMITS) -> EncodedCaptureArchive
parse_capture_archive(payloads: Mapping[str, bytes], *,
    expected_previous_state_sha256: str, limits=DEFAULT_LIMITS) -> RetainedCapturePacket
```

Logical payload keys are exactly `baseline`, `packet`, `receipt-000000` through count−1, sorted lexicographically. Display names exactly `baseline.json`, `packet.json`, `receipt-000000.bin` etc. No input-derived filesystem names. Raw response bytes are preserved independently, including whitespace and numeric spelling. Repeated raw bytes remain separate ordered receipt observations.

`packet` canonical JSON exact keys: `schema_version`, `replay_revision`, `previous_state_sha256`, `previous` (closed typed original predecessor), `staged` (closed typed original stage), `payloads` (ordered baseline+receipt inventory; packet itself excluded). Each inventory document exact keys `logical_id`, `original_name`, `byte_count`, `sha256`. Packet digest is SHA256(PACKET_DOMAIN + exact canonical packet bytes). The packet bytes bind all other payload hashes and lengths; the returned outer inventory additionally includes the packet bytes' ordinary SHA256. No circular self-hash. Run/revision identity uses full packet digest, never truncated.

Closed typed representation: plain null/bool/int/string; `{'$':'decimal','v':[sign,digits-string,exponent]}` preserving sign/digits/exponent and signed zero; `{'$':'datetime','v':canonical-UTC-iso}` and `date`; tuple tagged as `{'$':'tuple','v':[...]}`; exact allowlisted dataclass tag with exact named field object `{'$':'TypeName','v':{...}}`. Only `SourceReceipt.raw_body` may use `{'$':'receipt','v':'receipt-000000'}`. No arbitrary bytes field, import/eval/pickle/class name resolution. Explicit class/field/type schemas precede constructors; constructed fields must reencode identically so normalizing constructors cannot silently repair input. Decimal finite, digits<=512/exponent ±512, int bit length<=256, text scalar<=65536. Structural JSON admission happens before json.loads and typed tree construction, with duplicate keys, floats/nonfinite, extra fields, unknown tags refused.

Previous typed snapshot is linked to exact legacy `state_json(previous).encode()` bytes. Actual `restore_state(...expected_head=...)` and `risk_baseline` validate integrity; no latest-head/issuer authenticity claim. Raw metadata may be mathematically inconsistent: format admission does not run collector/material evaluation. Archive it first; audit failure must not delete it.

## Actual adapter: execution_launch/guard_capture_archive.py

```python
archive_guard_capture_packet(store: BundleStore, staged, previous, *,
    limits=DEFAULT_LIMITS) -> CaptureArchiveReceipt
read_guard_capture_packet(store: BundleStore, archive_digest: str, *,
    expected_previous_state_sha256: str, limits=DEFAULT_LIMITS) -> RetainedCapturePacket
replay_guard_capture_archive(store: BundleStore, archive_digest: str, *,
    expected_previous_state_sha256: str, limits=DEFAULT_LIMITS) -> ArchivedCaptureReplay
collect_archive_guard_capture(source: ContinuousUpbitCandidateSource, collector_source, *,
    store: BundleStore, previous: BaselineState, anchor, coverage, clock,
    trade_fees=(), limits=DEFAULT_LIMITS) -> CollectedCaptureArchive
```

Actual BundleStore exact type; no runtime provision/head seeding. Adapter builds RAW_ARCHIVED manifest: `run_id='capture-'+packet_sha256`, `revision_id='capture-packet-v1'`, `attempt_id='capture-'+packet_sha256`, parent=None, actual store policy/object digest, `expected_candidates=None`, `inventory_complete=True`; every inventory entry `role='other_input'`, source_name/study_id=None, required=True, and matching collected InputObservation. This is complete packet inventory, not study completeness or VERIFIED eligibility. File refs come from actual store preview_payload; archive_raw then require_backup=True readback; compare the entire expected manifest and inventory, not just payload digests. Read verifies this exact wrapper meaning and recomputes full packet-derived identity.

`CaptureArchiveReceipt` frozen carries archive_digest, packet_sha256, previous_state_sha256, path_sha256, manifest_sha256, observed_at, actual catalog_head `(sequence,sha256)`, backup_verified=True. No material hash until audit. Safety properties source_authenticated/current_freshness_verified/guard_committed/execution_ready=False; raw data excluded from repr.

`ArchivedCaptureReplay` frozen carries receipt, historical_replay=True, historical_evaluation_at (original staged.observed_at), capture_material_sha256, and repr-hidden material. Same four safety properties false. Historical replay calls actual `prepare_guard_capture_material(decoded.staged,decoded.previous,now=decoded.staged.observed_at)` only; no caller clock/now override, no new coverage callback, no fresh current-use assertion.

collect wrapper calls actual source.collect, then archive, then rereads by actual returned archive_digest and invokes historical replay. It never uses an unarchived original as the audited result. `CollectedCaptureArchive(receipt, replay: ArchivedCaptureReplay|None, audit_error_code: str|None)` retains the actual receipt when historical audit fails. If replay fails, the completed RAW archive remains available with a fixed audit error, never raw/private exception text. Composite replay success performs a final actual full readback/root/head check after material computation; it does not turn the historical evidence into a current account assertion.

Complete publication means actual primary+backup+catalog+retained head. Existing exact retry only; partial/orphan/head mismatch refuses without truncating/adopting/destroying original. No new storage engine. Current actual source completeness, owner checks, guard commit/publication and Coordinator/Runner integration remain unimplemented.

## Ownership and verification

Format + format tests: protective_hold_design. Adapter: pr4e_coordinator. Actual collection/store/restart tests: pr4e_owner. Independent review: revision_review. Root owns registry/guards/runtime/commit. No runtime until joint freeze. Meaningful tests cover closed schemas/types and decimal-scale/raw-byte roundtrip; bounded parsing before allocation; exact whole inventory; actual fake collector→primary+backup/head→newreader→I3a replay; archival success retained after audit refusal; old packet historical audit versus current freshness refusal; no auto seed/head adoption and interrupted publication existing refusal behavior.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
