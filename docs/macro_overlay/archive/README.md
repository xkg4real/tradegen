# docs/macro_overlay/archive — data snapshots behind formal cards (section 9.4 item 16; R-35 check (iii))

With every formal card, `core.quant.cards.archive_snapshot` writes `<card_id>.r<rev>/rows.jsonl` (the PIT store rows
behind the card's `data_snapshot_id`, sorted by `content_hash`, one canonical-JSON row per line) and `MD5LIST`
(`<md5>  rows.jsonl` and `<results_md5>  <card file>`). `cards.rederive_snapshot_id(rows)` is the md5 of the sorted
content hashes and must equal the card's `data_snapshot_id`; `cards.verify_archive` re-checks both.

A lost or altered archive is an integrity failure (`ArchiveLost`), never a reason to re-run silently: `verdict_filter`
(M8) drops every admission and steps exposure to the invariants-only level (L6013).

Empty on this machine: no formal card has run (the gate package is NOT_FROZEN).
