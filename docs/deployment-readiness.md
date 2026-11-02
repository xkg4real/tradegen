# Deployment manifest and owner setup

The deployment utility exports the exact existing D14 code closure and compares two
explicit manifests. It also supplies a public setup template. It never reads owner
logs or credential values, signs, activates a session or contacts a venue.

```sh
python -m execution_launch.deployment setup
python -m execution_launch.deployment setup --first-limits-at 2026-11-02T10:00:00+09:00
python -m execution_launch.deployment export --repo <absolute-current-checkout>
python -m execution_launch.deployment compare --left <windows.json> --right <cloud.json>
```

Run `export` with the intended runtime's own interpreter, from the reviewed target
checkout. The explicit repository must be that current checkout; it is not an
arbitrary-file hash service. It checks source-tree metadata for linked or nonregular
Python files before invoking the existing `owner.code_files`. Keep the checkout and
interpreter exclusively controlled and unchanged throughout export; this diagnostic
is not a sandbox for a hostile or concurrently modified repository. No absolute
repository, interpreter or home path is included in output.

The command prints JSON to stdout and writes no file. If saving it locally, use a
normal private `.json` file outside credential/owner-state directories. Comparison
uses the existing bounded, no-follow file reader: at most64KiB; symlinks, hard links,
nonregular files and known private credential/state paths are refused. That file
reader currently requires POSIX support. The pure `parse_manifest` and
`compare_manifests` APIs accept explicitly supplied bytes/objects in another reviewed
integration. Export itself is independent of that POSIX reader.

## What the hashes mean

`repository_files` holds relative Python-source paths and hashes. `dependency_records`
holds the installed `cryptography` and `PyYAML` RECORD hashes. `code_hash` is the exact
existing owner/signer hash of their combined sorted list. A separate manifest hash
also binds schema, runtime metadata and diagnostic flags. Import rejects duplicate
keys, unexpected fields, unknown dependency entries, unsafe paths, unsorted/duplicate
rows, invalid hashes and positive approval claims.

Comparison reports added, removed and changed entries separately for source and
dependencies. Runtime metadata is compared separately: equal code hashes can coexist
with different platform labels. A matching hash establishes integrity/equality only;
it neither authenticates the submitted manifests nor verifies an owner signature.
All outputs retain `signature_verified=false` and `execution_ready=false`. Exit0 for
export/compare means the diagnostic completed; inspect `code_hash_matches` to learn
whether files match. Default/setup and rejected inputs exit2.

The current signer runs in the owner's Windows Terminal and requires the target
repository's own venv. Its signed hash includes that interpreter's dependency RECORD
files. The same Git commit on Windows and Cloud can therefore require different code
approval. Copying a public PEM or signed owner log does not make different hashes
equivalent. Remote manifest approval is not implemented by this tool. Choose the
actual deployment environment before relying on a transferred approval.

## Missing owner inputs and timing

Default/setup prints only credential variable names, exact venue hosts, an all-null
profile template and ordered operator actions. It does not inspect environment
values or assume that an account, public key or signed context exists. The example
is deliberately not a runnable trading profile. Known private owner decisions can
be filled locally while unresolved fields remain null.

`--first-limits-at` is an explicit assumption that limits are first being set at the
given aware time. The output is the following Asia/Seoul calendar date, not evidence
that limits will actually be effective. First settings and loosenings are governed
by D12's verified log order, session and halt conditions. Initial limits signed on
2026-11-02 KST cannot take effect before2026-11-03 KST under those existing rules.
Already-effective limits must be established through the actual owner workflow;
without that evidence their status remains unknown. The utility cannot backdate an
approval or bypass the delay.

After final code/table/limit approval, genuine account and prospective strategy
evidence and fresh preparation remain required. The owner reviews the actual issued
`prepared.session_id`; a placeholder or a manifest cannot replace it. See the
[owner checklist](first-trade-owner-checklist.md).

This software is not legal, tax or investment advice and is not a licensed adviser.
