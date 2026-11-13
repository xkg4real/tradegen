# Lossless evidence objects: P0a execution record

Historical checkpoint: this document describes its recorded revision. The later v3 integration and current validation are in [lossless-history-execution-log.md](lossless-history-execution-log.md).

The owner rejected replacing valid quotes with unavailable values to resolve record size. This step implements an isolated content-addressed byte store, without connecting it to live history or changing order decisions.

## Implemented

- Explicit root and explicit per-payload limits; immutable, canonical references bind the storage policy, complete payload hash/length and ordered chunk manifest.
- Exact bytes are preserved, including normal quote receipts and every holding. Strict bounded reads reject missing, altered, re-ordered, duplicate-key and malformed evidence.
- Verified temporary bytes are copied to an exclusively created final candidate, flushed and read back under the store lock. Existing objects are never overwritten. Final filename visibility is not atomic; a reference is issued only after all objects and the manifest are verified. Journal/head commitment is a separate responsibility.
- Partial files are retained. Interrupted new staging blocks further staging, while independently valid older references remain readable. No automatic repair, orphan adoption or deletion.
- Path/reparse/hardlink and opened-file identity checks, existing QUANTGEN isolation, exact writer call pins. No network, keys, signing, arm or order authority.

## Independent review changes

The review identified and fixed four boundaries: pending new data blocking unrelated existing reads; unidentified inodes; transient hard links conflicting with the existing state-root link scanner; and reused objects bypassing directory flush after an earlier final-manifest flush failure. Each has a meaningful regression. Exclusive final creation now avoids the transient hard-link problem entirely. Existing writer pins and trusted-head caller restrictions were preserved.

## Verification

Frozen tracked Python/YAML fingerprint: `08098dd8ce036b20963be4551c876349a03f2e7b50a4c6de1a2180dacf3ece8c`.

- New object-store tests: **24 PASS / 0 FAIL / 0 NOT_RUN**, 2.829 seconds.
- Existing history/driver plus five safety-boundary modules, deduplicated by test ID: **125 PASS / 0 FAIL / 0 NOT_RUN**, 14.019 seconds.
- Both reports recorded baseline HEAD a54a390 with the exact named changes frozen in the working tree. The delivered commit must match this fingerprint; it is not a claim that baseline a54a390 already contained the new module.
- Tests used 19 KEYLESS names, fake inputs, isolated state, OpenBLAS1. Tracked runtime/test bytes and real-home metadata were unchanged; QA acceptance output was restored. No real-home contents or credentials were read by this work.
- The synthetic large-inventory case preserves all 1500 holdings, parsed flags/tickers and a nonempty normal book in a payload exceeding the old 262144-byte row cap. Fault tests cover exclusive final creation, partial copy/flush, pending remnants, scanner interaction and final-directory-sync retries.

Detailed reports are retained in handoff context `upbit-universe/gpt-20261113/p0a-*`. Original PR34 full-suite results apply to its earlier implementation, not to this new revision; no new whole-repository full run is claimed at this component checkpoint.

## Not yet implemented or proved

P0b must bind references to a new history format/window identity, enforce finite whole-window/store quotas, validate referenced graphs before independent-head advancement, and preserve replay/decision equivalence. Existing v1/v2 history bytes and golden digests remain unchanged. The legacy first size fallback still exists until that integration replaces it; this component alone does not fix live history admission.

Windows directory power-loss durability, actual head CAS/replay integration, process termination and real-account incidents were not tested. The store provides per-payload parser ceilings, not operational quota selection or proof of complete market evidence. It does not create a signature or trust the manifest on its own.

The owner's separate deadline decision is no sale solely because a holding deadline expires; request new management approval instead. Driver/evaluator terminal-liquidation semantics require a new policy/protocol version in a later stage. This module does not alter them, existing loss limits, halts or trading authorization.
