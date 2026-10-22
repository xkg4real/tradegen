# tests/fixtures/macro — frozen post-close fixtures for the macro suites

Spec section 9.5 and the coordinator rulings (section 6). Every file in this directory is listed in
`MANIFEST.csv`; a test reads a fixture only through `tests.notrun.require_fixture("<file>")`, which raises
`NotRun("REFDATA: ...")` (reported as NOT_RUN, never PASS) when the file is unlisted, absent or its md5 differs.

## MANIFEST.csv columns

| column | meaning |
|---|---|
| `file` | path relative to this directory (posix separators) |
| `source` | origin: a path under `/home/claude/quantgen_macro_data/` per its `CATALOG.md`, under `research_notes/…/council/`, or `synthetic(seed=11)` |
| `series` | series ids the file carries (`;`-separated) |
| `span` | first and last observation, `YYYY-MM-DD..YYYY-MM-DD` |
| `retrieved_at_utc` | ISO-8601 UTC instant the data was retrieved (close-type rows must be retrieved at or after `close_print_bound_utc + 10 min`, T-FIX-01) |
| `value_status_rule` | the `value_status` and `available_at_source` rule the rows follow (e.g. `official_close; available_at = close_print_bound_utc`) |
| `md5` | md5 of the file bytes; a mismatch refuses the fixture |
| `licence` | data licence; required |
| `owner` | who acquired and signed off the file; required |
| `tests` | test ids that read it (`;`-separated) |

A row without `licence`, `owner` and `md5` is not a fixture: `load_manifest` refuses the whole manifest (spec L6035).

## Rules

- Nothing here is mutable state: T-HERM-02 hashes this directory before and after the macro suite.
- Synthetic fixtures are generated deterministically (seed 11) and listed like any other file, with
  `source = synthetic(seed=11)`; stochastic goldens also record B and the block rule in `value_status_rule`.
- Reference datasets are not on this machine; golden-value fixtures are generated at M1's exit from the frozen
  reference files and md5-frozen here. Until then the tests that need them report `NOT_RUN (REFDATA)`.
- To list unlisted files with their md5: `python -m tests.notrun` (run from the repository root).
- Registries, not data (M1 package D): `goldens.csv` (every section 9.3 / 9.4 golden value, read through
  `tests.golden_tools`) and `ACQUISITION.csv` (the section 9.5 acquisition register; licence/owner/md5 blank until
  acquired). Both are md5-listed here, so every edit of either refreshes its manifest row. `bldp_dsr_example.json`
  holds the published Bailey-Lopez de Prado inputs of G-DSR-01 (synthetic, exempt from the post-close rule).
- Generated fixtures (`python docs/macro_fixtures.py --reference /home/claude/quantgen_macro_data ...`) carry the
  section 4.1 provenance columns (`series_id` first) and are checked by `core.ficc.pit.check_fixture` (T-FIX-01).
