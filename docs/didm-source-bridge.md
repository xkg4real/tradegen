# DIDM source bridge: offline inspection

`tools/research/didm_source_bridge.py` reads an **explicit offline copy** of a
QUANTGEN DIDM SQLite store or a bounded exchange JSON. It validates every supplied
record before writing a new private research report. It never activates trading,
authenticates a source, grants an approval, computes a trading probability,
downloads data, loads keys or starts a model. There is no application UI hookup.

## Contract reference

Reviewed QUANTGEN revision:
[`dec979a7fae65d5f749e12193fad3d0a9ce8ddf3`](https://github.com/xkg4real/quantgen/tree/dec979a7fae65d5f749e12193fad3d0a9ce8ddf3).

- [`core/didm/store/__init__.py`](https://github.com/xkg4real/quantgen/blob/dec979a7fae65d5f749e12193fad3d0a9ce8ddf3/core/didm/store/__init__.py), Git blob `9067a11727d57a3dc33162285451f5b309bf292e`.
- [`core/didm/llm/schema.py`](https://github.com/xkg4real/quantgen/blob/dec979a7fae65d5f749e12193fad3d0a9ce8ddf3/core/didm/llm/schema.py), Git blob `759872cccce6c2c1e034125b30ff8e6fa76061ad`.
- [`tools/didm/collect_daily.py`](https://github.com/xkg4real/quantgen/blob/dec979a7fae65d5f749e12193fad3d0a9ce8ddf3/tools/didm/collect_daily.py), Git blob `5604daf6025a619a5daeea9f4b0db4535796f254`.

These identify the reviewed format, **not the software that actually produced an
input file**. A file hash proves byte identity, not authenticity, ownership or
permission to trade. QUANTGEN's six official-source collectors already exist;
this bridge does not recreate them or modify QUANTGEN.

## Run locally

Close the collector and obtain a separate consistent SQLite snapshot on the
owner's computer. For a WAL database, use SQLite's backup mechanism in the source
application after coordinating with its writer; do not simply copy the main file
while discarding WAL. The bridge refuses an input with any `-wal`, `-shm` or
`-journal` sidecar. It does not checkpoint, repair, delete or open these sidecars.

```powershell
python -B tools/research/didm_source_bridge.py --database "D:\PrivateResearch\didm-snapshot.sqlite" --as-of "2026-11-22T22:00:00+09:00" --output "D:\PrivateResearch\didm-inspection-001.json"
```

Use the actual analysis cutoff, not this example date. All paths and the cutoff
are explicit. The output directory must already exist. A previous report is
never overwritten. A successful exit code 0 means only the offline input passed
these checks. Exit code 2 reports a fixed refusal reason; no partial report is
published. Standard output contains counts, hashes and reason codes, not input
paths, source titles or payloads. The full report contains private source data:
keep it outside Git and do not upload it without checking the data rights.

The original file is read with size/identity/mtime plus POSIX ctime or Windows
birthtime checks before and after. Windows requires Python 3.12+ with
`st_birthtime_ns`; it does not compare the known-inconsistent path/handle ctime.
The Windows branch has a synthetic regression test; native Windows validation
remains separate.
Only a private temporary copy is opened by SQLite using `mode=ro`,
`immutable=1`, `query_only=ON`, `trusted_schema=OFF`, an explicit transaction,
schema matching and integrity checking. `immutable` is never applied to the
owner's active database. The temporary copy is removed. A file being changed
during copying may be refused; this is not a backup service or proof against a
malicious writer preserving metadata. Source capture must still be coordinated.

Limits are 64 MiB per input, 250,000 source rows, 1 MiB per payload, 25,000 optional
scores, JSON depth 32, and 256 MiB per report. SQLite work has an instruction
budget. Exceeding a limit refuses the whole input instead of dropping records.
Publish uses a flushed temporary file and an atomic, no-clobber hard link. If the
destination filesystem does not support this, it refuses rather than falling
back to overwriting. Crash durability of the containing directory and managed
cloud-sync behavior are not established by this tool.

## Records, time and version behavior

- The exact `items` table and its two indexes are required. Extra tables, views,
  triggers or changed schema are refused. The input's `seq` and all eight QG
  record fields are preserved. Payload JSON text and its original SHA-256 remain
  unchanged; payload JSON must be finite, canonical, non-duplicated-key JSON.
- Known source/kind pairs are restricted to the pinned collector family. Raw
  payloads are retained as evidence; this is **not** a reimplementation of each
  provider's semantic validator. Unrecognized parser/schema versions refuse.
  Historical Kalshi rows without a parser version are retained and flagged.
- Every supplied version is validated, including future-received rows. Corrupt
  future data does not get silently skipped. All versions stay in the report.
  `selected_record_sha256` separately identifies the latest version known at the
  cutoff, using QG's receipt-time then payload-hash ordering per source/item.
- ALFRED vintage IDs remain separate items. An observation date is not an
  availability time. Source receipt timestamps are never backdated to a release
  date. ALFRED/OpenDART date precision and ECOS's unknown release time are flagged.
- Publication after receipt is preserved with a clock-anomaly gap, matching the
  V0 contract's choice not to reject it. No invented clock correction is applied.
- FinBERT baseline rows are retained as baseline inputs. They are not complete
  DIDM V0 scores. The actual QG daily collector does **not** write V0 score rows;
  ordinary SQLite imports consequently report `V0_MODEL_SCORES_MISSING`.
- Alpha Vantage/Tiingo/CryptoPanic historical rows can be inspected but are marked
  held. Their free-news access was already found unavailable; this does not
  enable those collectors or repeat key-setup requests. EODHD and Polymarket are
  not newly enabled by this bridge.

## Optional exchange format

`tradegen-didm-exchange-v1` is a **new TRADEGEN boundary format**, not a claim that
QUANTGEN already exports this format. Its exact root fields are `format`,
`contract` (the four constants in `CONTRACT`), `rows`, and `scores`. `rows` contain
the exact nine SQLite column names, including the original canonical JSON string
in `payload`. An empty `scores` list is valid and produces a missing-score gap.

Each optional score wrapper has exactly `source_record_sha256` and `score`.
The source record digest is SHA-256 of its nine-field object serialized with
UTF-8, `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`.
`score` must match the upstream `didm-score-v0` field names, finite bounds,
14 event types plus `none`, direction probability sum, ESS and entropy formulas.
Upstream's optional `schema_version` may be absent; no field is inserted. The
source ID and publication time must match the linked source record, and score
receipt cannot predate source receipt. A score received after the cutoff, or
linked to a superseded source version, is retained but not known at that cutoff.
`known_score_count` counts only scores whose receipt is within the cutoff and
whose source version is selected. Zero yields `NO_V0_SCORES_KNOWN_AT_AS_OF`, even
when `score_count` is positive because future or superseded scores are retained.
Duplicate score identities and missing links refuse the complete exchange.

```powershell
python -B tools/research/didm_source_bridge.py --export "D:\PrivateResearch\didm-exchange.json" --as-of "2026-11-22T22:00:00+09:00" --output "D:\PrivateResearch\didm-inspection-002.json"
```

No approval, expiry or return probability is inferred from these scores. Every
report has `research_only=true`, `live_eligible=false`, `execution_ready=false`,
`source_authenticated=false`, and `owner_approval_verified=false`.

## Remaining work and manual inputs

- Develop authenticated export/model manifests and an explicit freshness/expiry
  policy before making these records strategy inputs. V0 has no expiry field;
  this tool does not supply one or change a signed artifact.
- QUANTGEN's actual corpus, model cutoff/training evidence, independent
  performance validation, source-use rights and strategy review remain separate.
  Previously approved V0 rules and already completed source/key checks remain.
- The owner supplies an offline private snapshot when ready and runs the above
  CLI locally. It can be reported with just the non-sensitive summary; a private
  database or credentials need not be sent to an agent. This development step
  establishes no new 24-hour deadline.
- Any later application connection must preserve existing loss floors, risk
  gates, strategy approvals and live activation boundaries. None are modified
  here. QUANTGEN's research ledger is never written by TRADEGEN.

Verification: `python -B tools/research/test_didm_source_bridge.py` uses temporary
synthetic stores and exports. It does not use owner data or provider APIs.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
