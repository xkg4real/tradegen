# docs/macro_overlay/cards — formal macro model cards (R-35; section 8.1.3 steps 4-5)

This directory holds `model_card.macro` files and the hash-chained `verdicts.jsonl`. It is empty by design on this
machine: the gate package is `NOT_FROZEN` (no reference data, no git anchor, owner inputs null), so no formal header
is committed and no formal card is run. Every macro card is `NOT_RUN`; the recommended book carries the invariants only.

Layout once a formal run exists (written only by `docs/macro_overlay_study.py` through `core.quant.cards`):

| Path | Content |
|---|---|
| `../headers/<card_id>.r<rev>.draft.json` | the header draft with typed nulls where an owner input, the freeze, the ledger or a fixture is missing (`cards.owner_nulls` names each) |
| `../headers/<card_id>.r<rev>.header.json` | the committed header, immutable, `header_md5` over the header fields (never on this machine until the freeze) |
| `<card_id>.r<rev>.json` | header ∪ results, validated against `quantgen/model_card.macro.v2.0`, `results_md5` over the result fields minus the volatile ones |
| `verdicts.jsonl` | one canonical-JSON row per formal result: `card_id, revision, header_md5, results_md5, verdict, disposition, gate_package_md5, data_snapshot_id, git_hash, ledger_hash_at_run, prev_row_md5` (append-only; a hand edit breaks the chain and blocks every admission, T-CARD-03) |
| `../archive/<card_id>.r<rev>/` | the store rows behind the card's `data_snapshot_id`, md5-listed (section 9.4 item 16) |

Registered records that are not runs (`core.quant.cards.REGISTRY`):

- `MACRO-R06-US`: `"REJECT (instrument: US shares via KIS, 50 bp, daily)"`, `rerun: false` (L1575, L4291); never re-run, never rebuilt.
- `MACRO-R04-US-DM`: `NOT_RUN`, `SPECIFICATION_ONLY`, label `"step 3 FAIL (indicative)"`; no pooled or A-provisional route (DNB 34).
- `MACRO-STACK-KR`: the stack CARD-P generator is dormant (no de-risk factor is PASS).

Never write a v2 card into `docs/asset_expansion/cards/` (legacy readers glob that directory whole).
