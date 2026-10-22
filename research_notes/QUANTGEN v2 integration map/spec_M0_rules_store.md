# spec_M0_rules_store — QUANTGEN v2.0 implementation brief

M0 area: rules-store entries (§7), rule objects and validation (§7.1), owner-decision registry, R-02 bounds, DO-NOT-BUILD predicates (§10.3), tick-floor cost model and R-26 header checks, read-only scan, hermetic macro harness, fixture manifest, reproducibility record, governance-event appender.

- Spec = `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md`; `L<n>` = its line number.
- **VERBATIM** blocks were copied from the spec by script (not retyped). **PROPOSED** = this brief's mapping onto real files (the spec calls its own paths "proposed", L89, L379). Field names, parameters, bounds, formulas, test thresholds, enums and status strings are binding (L89).
- Tasks covered: TASK-M0-01..07 and 11..15. TASK-M0-08/09/10 (JSON Schema registry, card schemas, acting/display field classes) belong to the schema brief; only their interfaces appear here.
- Rule when silent (L89): no exposure change, specification book only, fail closed.

## 0. Findings that change the plan (verified on this machine, 2026-10-05)

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F1 | `core/rules` today is an **operator order-rule** store, not a config store. `Rule` = symbol/side/size/order_kind/conditions; `RuleStore` writes `config.trading_dir()/rules.json` as `{"version":1,"saved_at","rules":[…],"history":{rule_id:[…]}}`, and `_flush()` rebuilds the payload from those four keys only. | `core/rules/model.py:117-150`, `core/rules/store.py:130-231` | Any extra top-level key in `rules.json` is erased at the next operator save. The macro store must be a **separate file with separate classes**. Do not touch `Rule`, `RuleStore`, `validate`. |
| F2 | The gate's per-venue cost table is **not** in `core/quant/validate.py`. It is `COST = {"krx_etf": 3.0, "us": 50.0, "krx_stock": 35.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}` at `docs/asset_expansion_study.py:60`. `validate.py:53-57` holds only `GATE["cost_stress"] = 2.0`. | grep; `core/` never imports `docs/` | "Costs are defined once, in the gate's code" (L591) is not true yet. Move the dict into `core/quant/validate.py` and alias it from the docs script (B5). |
| F3 | The repository is **not a git repository** (`git rev-parse` fails; no `.git`). | shell | `git_hash` (required on every artifact, L3508) and the freeze anchor "repository_commit_before_any_card_run" (L4501) have no source. See blocker B-1. |
| F4 | `jsonschema` is **not installed** and not in `requirements.txt` (PyYAML 6.0.3, numpy 2.3.5, scipy 1.18.0 are). | `import jsonschema` fails | The §6 schemas need draft 2020-12 with `unevaluatedProperties` (L3506, L3509). Schema brief decides: add `jsonschema>=4.18` or hand-roll. The appender below needs only a 12-key check. |
| F5 | The §7 YAML (L4135–L4684) parses with `yaml.safe_load` into 28 top-level keys. Three conversions are needed, nothing else (no unquoted dates, no sexagesimal times, no yes/no/on/off tokens). | script | See C1 "YAML to JSON". |
| F6 | All 14 rule config blocks (R-19…R-31, R-34) equal their §7 copies line for line after comment stripping. | script diff over L1898–L3447 vs L4135–L4684 | L4132's "the rule governs and this listing is fixed" needs no fix today. |
| F7 | `prep/readlines.py` has a `SyntaxError` at line 4 (a literal newline inside a string). | run | Other readers cannot print long lines with it. |
| F8 | `core/calendars.py` and `core/markets.py` are single modules; `core/ficc/macro.py` is a single module. §7 cites `core/calendars/data/…` (L4174, L4192, L4229). | `ls core` | Package conversion or another data dir is an M1 decision; M0 stores the path strings verbatim. |
| F9 | No workflow YAML exists in the repo. `core/skills/workflows.py` parses `<config.skills_root()>/workflows/*.yaml`, an external repository. `config.SKILL_CREDENTIALS` forwards Alpaca keys to external skill subprocesses. | `core/skills/workflows.py:1`, `config.py:84-89` | T-RO-01's "commands of every workflow YAML" has no in-repo target until M8 adds `macro_daily.yaml`. Scope of the scan: ambiguity A-13. |
| F10 | Existing safety scans to reuse: `tests/acceptance.py:31` `_code_only()` (AST docstring strip), `:48` `runtime_py()`, `:169` `test_08_no_broker_order_path`, `:178` `test_09_no_account_credentials_requested`; `tests/expansion_acceptance.py:155`. Network guard pattern: `tests/ficc_acceptance.py:31` `_no_network()`. Atomic write pattern: `core/rules/store.py:216-231`. md5 helper: `core/quant/validate.py:791` `md5_of`. | read | Reuse; do not re-implement. |
| F11 | All 29 `/uapi/…` string literals in `core/`, `data/`, `ui/` contain `/quotations/`. HTTP `.post(` occurs at exactly four places: `core/quant/insights.py:312` (Claude API), `data/krx/kis_client.py:158` (`/oauth2/tokenP`), `data/krx/krx_market_client.py:111,120` (KRX OTP and CSV download). | grep | These are the allowlist seeds for T-RO-01. |
| F13 | Sibling briefs in this folder name the same code differently: `spec_constitution.md` uses one module `core/rules/macro_rules.py` plus `core/rules/macro_rules_v2.json` (shipped default) with a runtime copy under `config.trading_dir()`; `spec_architecture.md` uses `core/rules/macro_rules.py` plus `data/macro/rules_v2.0.0.json`. All three agree on `core/rules/governance.py` and `tests/macro_acceptance.py`. | grep of the folder | `macro_store.py` and `macro_validation.py` below are section labels; every function here fits one module `core/rules/macro_rules.py` if the coordinator prefers it. The store's location is the one real disagreement (A-1). |
| F12 | Local data: `docs/asset_expansion/cache/*.csv` end 2026-09-18…2026-09-25 (Yahoo adjusted closes; `yf_069500.KS.csv` 2007-01-29…2026-09-23). None reaches 2026-10-02. `QC_modules.csv`, `qf3_dnb_classes.py`, `QF3_dnb_evidence_classes.csv`, `QX_*` files are not on the machine. | `ls`, `find` | Every M0 test in this brief is SYNTH; TASK-M0-15 is REFDATA with no local substitute. |

## A. Scope

| Task | Deliverable (one line) | Target files (E = exists, N = new, PROPOSED) |
|---|---|---|
| M0-01 | Static read-only scan over the repo (T-RO-01); `read_only: true` stamped by every artifact writer | `tests/macro_acceptance.py` (N); reuse `tests/acceptance.py` helpers (E) |
| M0-02 | Hermetic macro suite + test registry (tier, `runs_from`, §9.0b clause deferrals) | `tests/macro_acceptance.py` (N), `tests/macro_registry.py` (N), `tests/run_all.py` (E, +import, +list entry, +before/after state hash) |
| M0-03 | Fixture manifest and md5-verifying loader | `tests/fixtures/macro/MANIFEST.csv` (N), loader function inside `tests/macro_acceptance.py` |
| M0-04 | §7.1 rule object, validation engine, R-02 bounds, exposure-basis predicate | `core/rules/macro_validation.py` (N) |
| M0-05 | The v2.0.0 store file with every §7 block; macro artifact dir in config | `core/rules/macro_rules.json` (N, data), `core/rules/macro_store.py` (N), `config.py` (E, +2 functions) |
| M0-06 | Owner-decision registry D1–D6, `{ref}` resolver, load-time refusal, ruling → governance event | `core/rules/macro_store.py` |
| M0-07 | Hash-chained `governance_events.jsonl` appender and chain verifier | `core/rules/governance.py` (N); schema `quantgen/governance_event.v2.0` from the schema brief |
| M0-11 | Canonical JSON, `config_hash`, reproducibility record, RNG convention | `canonical_json`/`md5_hex`/`config_hash` in `core/rules/macro_store.py`; the artifact writer itself in the schema brief's module |
| M0-12 | `cost_per_side`, `stress_cost_line`, tick table, instrument metadata, gate cost table as single source | `core/quant/validate.py` (E, +`COST_BPS_PER_SIDE`), `docs/asset_expansion_study.py` (E, alias), `core/quant/backtest.py` (E, +functions; spec path L2775), `core/markets.py` (E, +`Instrument` table; spec path L2774) |
| M0-13 | R-26 header checks: required fields, enums, band rule, notional equality, granularity floor, stock-book refusal, sleeve-notional change event | `core/rules/macro_validation.py` (`validate_card_header`), `core/rules/macro_store.py` (`set_sleeve_notional`) |
| M0-14 | 17 refused shapes as predicates; 37 labelled items; item 11 split | `core/rules/macro_validation.py`; `do_not_build` block in the store |
| M0-15 | Replace E labels by bootstrapped B labels (spike) | not runnable here (REFDATA); only the logged-revision path `label_update` is built |

Out of scope here: `core/ficc/macro` schemas and artifact validator (M0-08/09/10).

## B. Build spec

Exceptions (PROPOSED, one class is enough): `class MacroRefusal(ValueError)` with attributes `code: str` (a `refused_shapes` key or a check id below), `rule_id: str | None`, `items: tuple` (§10 item ids), `labels: tuple[str, ...]`, `detail: str`. Message format: `refused <rule_id>: §10 item <n> (<label>) <code>: <detail>`. "The refusal names the item and its label. It is logged in the store's edit history, and nothing is written" (L6231).

### B1. `config.py` (E) — two functions (L4126)

```python
def macro_artifact_dir() -> Path:   # env NEXTGEN_MACRO_DIR, else Path.home()/".nextgen"/"macro"  (beside runs/, trading/)
def macro_rules_path() -> Path:     # env NEXTGEN_MACRO_RULES, else <repo>/core/rules/macro_rules.json
```
- Sub-paths under the artifact dir used by this area: `quarantine/` (L3370), `governance_events.jsonl` (L1249–L1250; location PROPOSED, A-6). Later milestones add `gate/acceptance_runs.jsonl` (L4531), `cards/verdicts.jsonl` (L4827), `run_log.jsonl` (L1239), `fetch_log.jsonl` (L4202).
- "Decision times are calendar lookups (R-20), not constants" (L4126): add **no** decision-time constant to `config.py`.
- T-RO-02 (M1) later freezes the KIS quotation allowlist in `config.py` (L5606); not M0.

### B2. `core/rules/macro_store.py` (N) — the store

**File** `core/rules/macro_rules.json` (PROPOSED layout): the 28 §7 top-level keys at the top level (so every canonical dotted key such as `risk_layer.korea_caps.template` is a plain path), plus `rules` (list of §7.1 rule objects, B3) and `history` (list, below). No key contains a dot (script-verified), so dotted paths are unambiguous.

```python
def canonical_json(obj) -> str
#   json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
#   = "UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace" (L4683, L5616); Python's json prints floats with repr.
def md5_hex(data: bytes | str) -> str
def load(path: Path | None = None) -> MacroStore          # path None -> config.macro_rules_path()
def validate_store(doc: dict) -> None                      # raises MacroRefusal; called by load() and before every write

class MacroStore:                                          # holds the raw doc; never mutates in place
    def get(self, dotted: str)                             # resolved value ({ref} replaced); missing key -> KeyError (no default, ever)
    def raw(self, dotted: str)                             # unresolved value
    def resolved(self) -> dict                             # deep copy with every {ref} replaced
    def config_hash(self) -> str                           # md5_hex(canonical_json(doc minus "history" minus "saved_at"))
    def rule(self, rule_id: str) -> dict | None            # §7.1 object
    def history(self) -> tuple[dict, ...]
    def edit(self, dotted: str, new, *, actor: str, reason: str, kind: str = "acting_param_edit", revision: dict | None = None) -> MacroStore
    def save_rule(self, obj: dict, *, actor: str, reason: str, revision: dict | None = None) -> MacroStore
    def rule_on(self, decision: str, value, *, rationale: str, effective_from: str, events_path: Path) -> MacroStore
    def set_sleeve_notional(self, market: str, notional_krw: float, *, effective_from: str, signed_by: str, events_path: Path) -> tuple[MacroStore, list[str]]
```

**load / fail-closed.**
- Missing file, unreadable JSON, or a document that fails `validate_store` → raise. Do **not** copy `RuleStore.load`'s "return on a corrupt file" (`store.py:201-204`): with no valid macro store there is no macro decision.
- "The store's model is immutable and has no financial defaults, so every number below must be written explicitly" (L4127): a missing key raises `KeyError`; no accessor takes a default argument.
- Writes are atomic (temp file + `os.replace`, as `store.py:224-229`), and unlike `RuleStore._flush` a write error **raises**.
- Tests never call `load()` without a path (T-HERM-02).

**validate_store(doc), in this order.**
1. `doc["version"] == "2.0.0"`, `doc["as_of"] == "2026-10-02"`, `doc["read_only"] is True` (L4135–L4137). The 28 top-level §7 keys are all present.
2. Owner registry and refs (below).
3. Block bounds table B3.3 and the block-level DO-NOT-BUILD checks B3.5.
4. Every object in `doc["rules"]` passes `validate_rule_object` (B3).

**`{ref}` resolution (L65, L4130, L4139).**
- A ref is a dict with **exactly one key**, `"ref"`, whose value is a dotted path. A dict that has `"ref"` and any other key → refused at load ("any other shape is refused at load", L65).
- The target must exist and hold a scalar (str, int, float, bool) or `null`. A target that is itself a ref, a dict or a list → refused.
- §7 contains 7 refs (script-extracted): `vol_target.KR.notional_nav → sleeves.KR.notional_nav`; `instruments.us_line_choice → sleeves.US.line`; `cards.R-28_trend_axis.us_sleeve → sleeves.US.line`; `cards.R-28_trend_axis.notional_nav → sleeves.US.notional_nav`; `cards.R-29_US_FUT.notional_nav → sleeves.US.notional_nav`; `cards.R-29_US_FUT.us_sleeve_and_line → sleeves.US.line`; `cards.R-31_step_down.hard_stop_level → risk_layer.drawdown.hard_stop.level`. Three of them point at sleeve notionals, which are owner inputs, not owner decisions; so the resolver is generic.
- A ref to a `null` target resolves to `None`; every consumer that needs the number must refuse on `None` (B6 check 5).

**Owner-decision registry (L65–L74, L4130, L4138–L4152, L5443–L5455).** For `n` in 1..6, with `D = doc["owner_decisions"]["D<n>"]`:
1. `set(D) == {"key","value","default","options","status","effective_from","rationale","refs"}`; `D["status"] ∈ {"default","owner_set","pending"}` (L4138).
2. `raw(D["key"])` exists, is a scalar, and equals `D["value"]` ("Each D1–D6 canonical key exists and holds a scalar equal to `owner_decisions.D<n>.value`", L5672).
3. Every path in `D["refs"]` holds exactly `{"ref": D["key"]}`. A literal there that differs from the canonical value → refused at load (binding, L5672). A literal that equals it is also refused (conservative reading of "never a literal copy", L65; A-2).
4. `D["value"]` is admissible: D1, D3, D5, D6 `value ∈ options`; D2 `value ∈ [-0.15, "-1.5*sigma_book"]`; D4 `0 < value ≤ 0.10` (`options: [tighten_only_le_0p10]`; "the owner may only tighten it", L5453).

**`rule_on(decision, value, …)` — an owner ruling (L65, L4130, L5444–L5446).**
1. Build the candidate doc: `D.value = value`, canonical key `= value`, `D.status = "owner_set"`, `D.effective_from`, `D.rationale`. `D.default` never changes.
2. `validate_store(candidate)`; refusal → history entry `kind: "refusal"`, raise, nothing else written.
3. D6 only: refuse when `<artifact_dir>/gate/acceptance_runs.jsonl` exists and is non-empty ("an owner ruling is accepted only before the first acceptance attempt; any later change is a new package version and a counted trial", L74, L4152).
4. Write the store atomically with a history entry `kind: "owner_ruling"`, then append one governance event (B4): `kind: "owner_ruling"`, `key: D.key`, `old`, `new`, `actor: "owner"`, `reason: rationale`, `refs: ["D<n>", *D.refs]`, `book_id: null`, `rule_id: null`. If the append raises, restore the previous store bytes and re-raise.
5. A ruling is **not** an acting-parameter edit and never demotes a card (L65, L1186, L5446); it is **not** a gate-package change (L5445). The history `kind` must stay distinguishable from `acting_param_edit` for R-25 (M8).
6. Dependent cards: "a card whose header depends on the key (D2 for R-31) gets a new counted revision before its next run" (L65, L5446). M0 has no cards; `rule_on` returns the store and the caller reads `D.refs` to find dependants. The card's `owner_decisions` field "records the values at commit and is checked only at commit" (L5672) → B6 check 12.

**History entry (PROPOSED fields; "The store's edit history is the revision log", L4128).**
`{seq: int, utc: "<ISO-8601 Z>", actor: "owner"|"operator"|"runtime"|"harness"|"council", kind: "seed"|"acting_param_edit"|"card_revision"|"owner_ruling"|"notional_change"|"package_freeze"|"label_update"|"refusal", path: str|null, old, new, reason: str, revision: {card_id, revision}|null, refusal: {rule_id, code, items, labels}|null}`.
- `actor` reuses the §6.6 enum (L4108).
- `config_hash` excludes `history` so that a logged refusal does not change every artifact's hash (A-5).
- R-25 (M8) reads `kind == "acting_param_edit" and revision is None` as its trigger `acting_param_edit_outside_revision` (L4479, L4894). M0 records; it does not demote. Path classification: every path is acting unless the entry's kind is `owner_ruling`, `notional_change`, `package_freeze` or `label_update` (conservative, mirrors L3370 "unclassified is acting"; A-7).

**`edit` / `save_rule`.** Build the candidate, run `validate_store`; for `save_rule` also run the pair predicates of B3.4 against the stored object with the same `rule_id`. Refusal → log `refusal`, raise, state unchanged. Lowering `instruments.cost_floor.commission_bp` is refused (A-8).

**`set_sleeve_notional` (L2811).** Sets `sleeves.<market>.notional_nav` (a positive number, KRW), history `kind: "notional_change"`, governance event `kind: "notional_change"` (`key: "sleeves.<market>.notional_nav"`, `actor: "owner"`). Returns the card ids of futures-line rule objects that now fail the granularity floor (B6 check 8). "It never re-opens a verdict, and a futures-line card registered after the change is a new card counted in its family ledger" (L2811).

**Cost-table reference.** `def cost_table() -> Mapping[str, float]` returns `core.quant.validate.COST_BPS_PER_SIDE` after asserting `store.get("gate.costs") == "read_from_gate"` (L4616). The store never holds a rate (L4129).

### B3. `core/rules/macro_validation.py` (N) — rule objects, bounds, basis, DO-NOT-BUILD

#### B3.1 Rule object (§7.1, VERBATIM table L4691–L4705)

| Field | Values | Refused when (§10 item) |
|---|---|---|
| `rule_id`, `kind` | string; `kind` ∈ {INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE} | — |
| `output_range` | [lo, hi] | hi > 1.0, an overlay outside [0.5, 1.0], vt or vs outside [0, 1.0] (2, 8) |
| `exposure_basis` | active, total | missing on an acting rule (P8) |
| `applies_to` | the §6.2 `family` enum (momentum, reversal, flow, quality, ts_trend, market_gross) | a vt (R-06) rule on anything but `market_gross`; any multiplier on `ts_trend` (R-14 is exempt from overlays; P8, T-BASIS-01; its runtime check runs from M4 and M7, §9.0b) |
| `composition` | min | anything but `min` (31) |
| `books[]` | recommended, specification, forward_sim, refusal | the recommended book reading a non-PASS, FORWARD-SIM or refusal multiplier (22); `INVARIANT_STEP` only for R-31 |
| `inputs[]` | `{series_id, role, books, timing, source_kind}`; `source_kind` ∈ {market_price, published_series, derived, implied_vol, regime_model, ml_classifier} | a `regime_model` source acting or displayed, or a smoothed or forward-looking label (11, 24, 27); an `ml_classifier` source (11, 29); a value-timed or provisional acting input (19, 26); an acting input without a contract or binding (R-19) |
| `estimator` | `{name, kind}`; `kind` ∈ {sma, ewma, garch, har, comb, ml} | `ml` (11, 29); max(SMA20, implied) sizing (30); a change outside an R-30 counted revision (25) |
| `label_layer` | none, conformal | conformal (28) |
| `instrument_book`, `market` | the §6.5 and §6.1 enums | a KRX stock book as a market-gross scalar (33); an R-28 instance with market KR (37) |
| `card_id`, `tier`, `header_md5`, `results_md5` | strings or null | a header edit after `results_md5` exists (23, 32); a pooled or A-provisional tier added after results (34) |
| `n_rule` | the R-23 rule | the Kish form or any other N_eff rule (36) |
| any field | — | an order, cancel, withdrawal, deposit-address or transfer path, or a broker adapter (21); a forward record cited as validation (35) |

Enums the table points to:
- `applies_to` = §6.2 `family` (L3730): `momentum, reversal, flow, quality, ts_trend, market_gross`.
- `market` = §6.1 (L3538): `KR, US, JP, EU, TW, CN, HK, IN, EM, CRYPTO, FX`.
- `instrument_book` = §6.5 (L3947): `KRX_ETF_line, KRX_stock_book, KOSPI200_futures, mini_KOSPI200_futures, CME_micro_ES, US_shares_KIS, KRX_listed_SP500_ETF, crypto_venue, FX_KRX_USD_futures, FX_broker_spot, multi_line`.
- `inputs[].role` (L3648): `acting_exposure, forward_sim, risk_model, context, history`. `inputs[].timing` (L3647): `live, publication, value_proxy`.
- `tier` (L3939): `A, B, C`. `n_rule`: the only accepted value is the string of `gate.step3.n_gate` = `max(N_clusters, N_equiv)` (L4570).

PROPOSED addition (§7.1 has no field that says which bound applies; A-3): `factor ∈ {"overlay","vt","vs","ladder","post_rearm_cap","none"}`, required on every object whose `output_range` is not null.

```python
def validate_rule_object(obj: dict, store_doc: dict, *, verdicts: Mapping[str, str] = {}) -> None      # raises MacroRefusal
def validate_rule_edit(old: dict, new: dict, *, revision: dict | None) -> None                          # pair predicates (B3.4 rows 9, 10, 12)
```

#### B3.2 Field checks that are not DO-NOT-BUILD shapes

| Check id | Refuse when | Source |
|---|---|---|
| `kind_enum` | `kind ∉ {INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE}` | L4693 |
| `exposure_basis_missing` | `output_range` not null and `exposure_basis ∉ {"active","total"}` | L4695, L1506 (3), P8 L568–L570, T-BASIS-01 |
| `vt_not_on_market_gross` | `factor == "vt"` and `applies_to != "market_gross"` | L4696, L894 |
| `multiplier_on_ts_trend` | `applies_to == "ts_trend"` and `output_range` not null (any multiplier) | L4696, L894, `families.ts_trend.overlay_exempt: true` L4326 |
| `basis_level_mismatch` (inferred, A-4) | `applies_to == "market_gross"` and `exposure_basis != "total"`; or a family and `exposure_basis != "active"` | L865, L870 |
| `invariant_step_reserved` | `disposition == "INVARIANT_STEP"` and the rule is not R-31 | L4698, L4089 |
| `us_line_none` (M0-13) | `market == "US"`, `applies_to == "market_gross"`, `books ∩ {recommended, specification} ≠ ∅` while `sleeves.US.line == "none"` | task M0-13; L4247 (`US_SLEEVE_OFFICIAL_CLOSE … books: []`), L73 |
| `acting_input_unbound` | an `inputs[]` entry with `role == "acting_exposure"` whose `series_id` has no key in `data_contracts.roles` | L4699 |

The S2 clause of T-BASIS-01 ("S2 applied to momentum raises an error", L5628; `refusal_books.S2_rates.excludes: [momentum, ls_factor_sleeves, KR]`, L4411) runs from M8 (L5550, L5559).

#### B3.3 Bounds (R-02 rules (1), (3), (4): L1506; P2: L508–L517; Tier C: L4864)

Rule object: `output_range = [lo, hi]`.
- `factor == "overlay"`: `0.5 ≤ lo ≤ hi ≤ 1.0`.
- `factor ∈ {"vt","vs"}`: `0.0 ≤ lo ≤ hi ≤ 1.0`. ("They have no floor", L512.)
- `factor ∈ {"ladder","post_rearm_cap"}`: `{lo, hi} ⊆ {0.5, 1.0}` (L872, L3738–L3739).
- Any `hi > 1.0` → refused as Tier C with items 2 and 8 (L513, L4694, L4864). `tier == "C"` → refused (`gate.tiers.C: {allowed: false}`, L4612).
- "0× comes only from the risk layer" (L514–L517): an overlay with `lo < 0.5` is refused; 0 is legal only as `lo` of `vt`/`vs`. HALTED is a runtime state, never a rule output (L874).
- The clause "The overlay layer cannot emit 0" of T-CAP-01 is a runtime clause and joins at M2 (L5570).

Store blocks: bound these paths and **only** these (a name pattern such as `*mult*` would refuse the spec's own store; see the exclusions).

| Path | §7 value | Check |
|---|---|---|
| `overlay.floor`, `overlay.cap` | 0.5, 1.0 | `== 0.5`, `== 1.0` |
| `overlay.combine` | `min` | `== "min"` (L881: "the rules store refuses `combine ≠ min`") |
| `overlay.floor_vs_vt_outside_halted` | 0.5 | `== 0.5` |
| `overlay.zero_only_in` | `[risk_layer, book_HALTED]` | equality |
| `vol_target.KR.cap`, `vol_target.US.cap`, `vol_target.other_markets.cap` | 1.0 | `0 < cap ≤ 1.0`; `cap_permanent is True` on KR and US |
| `vol_target.KR.exposure_basis`, `vol_target.US.exposure_basis` | `total` | `== "total"` |
| `families.momentum.own_vol_scale.{floor, cap}` | 0.0, 1.0 | `0.0 ≤ floor ≤ cap ≤ 1.0`; `exposure_basis == "active"` |
| `families.momentum.dm_gate.multiplier` | 0.5 | `0.5 ≤ m ≤ 1.0`; `exposure_basis == "active"`; `books == ["specification"]` |
| `families.{reversal,quality,flow}.overlay` | `fixed_1.0` | equality |
| `families.ts_trend.cap` | 1.0 | `≤ 1.0`; `overlay_exempt is True` |
| `refusal_books.S1_krw.multiplier`, `refusal_books.S2_rates.multiplier` | 0.75, 0.5 | `0.5 ≤ m ≤ 1.0`; `verdict == "REJECT"`; `regate_queue is False` |
| `cards.R-28_trend_axis.rule.{multiplier_below, multiplier_above}` | 0.5, 1.0 | each in `[0.5, 1.0]`; `rule.composition == "min"`; `rule.exposure_basis == "total"` |
| `cards.R-29_US_FUT.rule.cap` | 1.0 | `≤ 1.0`; `rule.exposure_basis == "total"` |
| `cards.R-31_step_down.steps[*].mult` | 0.5, 0.5 | each in `{0.5, 1.0}`; `composition == "min"` |
| `risk_layer.drawdown.hard_stop.post_rearm_cap` | 0.5 | in `{0.5, 1.0}`; `post_rearm_cap_in_min is True` |
| `risk_layer.drawdown.composition` | `min` | `== "min"` |
| `gate.tiers.B.bounds` | `[0.5, 1.0]` | equality |
| `gate.tiers.C.allowed` | `false` | `is False` |

Not exposure multipliers; never bound-checked: `gate.card_p_v2.pc6_axes.*` (`window_mult [0.5, 1, 2]`, `target_mult [0.75, 1, 1.25]`, `threshold_mult`, `lookback_or_dwell_mult`), `gate.stats.live_sharpe_multiplier 0.60`, `gate.stats.power.mde_factor 2.1232`, `instruments.stress_line.multiplier` (a cost factor ≥ 1), `risk_layer.korea_caps.lookthrough.leveraged_multiplier: L`, `events.multi_session_gap.var_display_scale`, `prior_haircuts.*`, `weights_prior` (0–3 integers are admissibility filters, L4328), the item numbers under `do_not_build.refused_shapes`.

#### B3.4 The 17 refused shapes (§10.3 VERBATIM table L6233–L6252, then the predicates)

| Refused shape | Items | Check |
|---|---|---|
| An order, cancel, withdrawal, deposit-address or transfer path; a broker execution adapter | 21 | T-RO-01 (static scan), T-RO-02 (runtime guard) |
| A multiplier, weight or vol-target cap above 1.0 | 2, 8 | T-CAP-01 |
| A composition other than `min()`; a product of de-risk multipliers | 31 | T-CAP-02 |
| An acting or displayed field whose source is a regime model (`source_kind: regime_model`), or a smoothed or forward-looking label | 11c, 24, 27 | T-DNB-01 |
| An ML classifier as an estimator, gate or label source; a challenger entry of kind `ml` | 11a, 29 | T-DNB-01 |
| A conformal calibration layer on the display labels | 28 | T-DNB-01 |
| A sizing estimator that takes `max()` over an implied-vol series | 30 | T-DNB-01 |
| An estimator change outside a counted R-30 revision | 25 | T-DNB-01, I-10 |
| An edit to `instrument_book`, `notional_nav`, `rebalance`, `no_trade_band` or a cost after a card's `results_md5` exists (a new card id is required) | 23, 32 | T-DNB-01, T-BOOK-01 |
| `instrument_book: KRX_stock_book` on a market-gross scalar (`instruments.market_scalar_on_stock_book: refused`) | 33 | T-DNB-01, T-BOOK-01 |
| A pooled or A-provisional tier declared after any market's result exists | 34 | T-DNB-01 |
| A card whose evidence field cites a forward book as validation | 35 | T-DNB-01, I-14 |
| A Kish computation (`kish_design_effect` is in `gate.step3.forbidden`), or an N rule other than `gate.step3.n_gate: max(N_clusters, N_equiv)` | 36 | T-DNB-01, T-NEFF-01, T-STEP3-02 |
| An R-28 instance with `market: KR` | 37 | T-DNB-01 |
| A recommended book reading a FORWARD-SIM, refusal-book or specification-only multiplier (an R-31 step with disposition `INVARIANT_STEP`, binding share ≤ 0.10, is not specification-only; Resolution 6) | 22 | I-03 |
| A production rule reading a value-timed or unpublished series; a provisional or bar-derived acting close | 19, 26 | T-LAG-01, T-PROV-01, T-BAR-01 |

Items without a row (1, 3–7, 9, 10, 12–18, 20) are design prohibitions with no configuration shape of their own. Code review enforces them against this list, and reopening one needs a new card with new evidence (§8).

Keys and items below are VERBATIM from `do_not_build.refused_shapes` (L4662–L4679). The predicate column is this brief's reading "as a predicate over the rule-object fields of §7.1" (L4689, L6231). Each refusal carries the items and their labels from `do_not_build.items`.

| # | `refused_shapes` key | Items | Refuse when | Object |
|---|---|---|---|---|
| 1 | `order_path_or_broker_adapter` | 21 | any key (recursive) in `{order_path, cancel_path, withdrawal_path, deposit_address_path, transfer_path, broker_adapter, execution_adapter, order_client}`, or `read_only` present and not `true` (key list PROPOSED; the binding enforcement is T-RO-01 / T-RO-02, L6235) | rule object, header, book config, store root |
| 2 | `multiplier_weight_or_cap_above_1` | 2, 8 | B3.3: `output_range[1] > 1.0`; an overlay outside `[0.5, 1.0]`; vt or vs outside `[0, 1.0]`; `tier == "C"` | rule object; block table |
| 3 | `composition_not_min` | 31 | `output_range` not null and `composition != "min"` (missing counts; `"product"` is the named case) | rule object; block table |
| 4 | `regime_model_source_acting_or_displayed` | 11, 24, 27 | any `inputs[i].source_kind == "regime_model"`, whatever its role ("acting or displayed", L6238) | rule object; context/display config |
| 5 | `smoothed_or_forward_looking_label` | 24 | any key `smoothed: true` or `forward_looking: true` in the object; or an `acting_exposure` input whose `series_id` is a display label, the regime read or a sheet z-score (item 24, L6175). No §7.1 field encodes "smoothed" (A-9) | rule object |
| 6 | `ml_classifier_estimator_gate_or_label` | 11 (11a), 29 | `estimator.kind == "ml"`; any `inputs[i].source_kind == "ml_classifier"`; "a challenger entry of kind `ml`" (L6239) | rule object; `vol_target.estimator_gate.challenger` |
| 7 | `conformal_label_layer` | 28 | `label_layer == "conformal"` (allowed: `"none"` or absent) | rule object; display-label config |
| 8 | `sizing_estimator_max_over_implied` | 30 | `factor ∈ {vt, vs}` and the estimator takes `max()` over an implied-vol series: `estimator.combine == "max"` with any input `source_kind == "implied_vol"`, or `estimator.name` matching `max(…implied…)`. Conservative extension: any `acting_exposure` input with `source_kind == "implied_vol"` on a sizing rule whose `estimator.kind != "har"` (L6205: implied vol "may enter sizing only inside HAR-IV") | rule object |
| 9 | `estimator_change_outside_r30_revision` | 25 | pair: `old.estimator != new.estimator` and `revision` is not an R-30 counted revision (`revision.kind == "r30_counted_revision"`, PROPOSED marker; `vol_target.estimator_gate.switch: {counted_revision: true, full_v2_card_p: true}`, L4305) | `validate_rule_edit` |
| 10 | `header_edit_after_results_md5` | 23, 32 | pair, same `card_id`: `old.results_md5 is not None` and any of `instrument_book`, `notional_nav`, `rebalance`, `no_trade_band` or a cost differs ("a new card id is required", L6243; key comment L4672) | `validate_rule_edit`; header pair |
| 11 | `krx_stock_book_on_market_gross_scalar` | 33 | `instrument_book == "KRX_stock_book"` and (`applies_to == "market_gross"` or `exposure_basis == "total"`). Conservative extension to `US_shares_KIS` (L2822, `us_shares_50bp: single_names_only` L4404; A-10) | rule object; header + its rule |
| 12 | `pooled_or_a_provisional_tier_after_results` | 34 | pair: `old.results_md5 is not None` and `new` adds a pooled rule or an A-provisional tier; standalone: any `tier` naming A-provisional (`gate.tiers.A_provisional: closed`, L4610) | `validate_rule_edit`; rule object |
| 13 | `forward_record_cited_as_validation` | 35 | an `evidence` or `validation` field cites a forward book or forward record (field shape undefined in the spec; A-11) | rule object, card |
| 14 | `kish_or_other_n_eff_rule` | 36 | `n_rule` present and `!= "max(N_clusters, N_equiv)"`; any key or value starting `kish` | rule object; `gate.step3` |
| 15 | `r28_instance_market_kr` | 37 | the rule is an R-28 instance (`rule_id` or card family `R-28`) and `market == "KR"` | rule object |
| 16 | `recommended_book_reads_non_pass_multiplier` | 22 | `"recommended" ∈ books`, `kind ∈ {CARD-O, CARD-P}` and `verdicts.get(card_id, "NOT_RUN") != "PASS"`, unless the rule is R-31 with `disposition == "INVARIANT_STEP"` (L6249); or `"recommended"` listed together with `forward_sim` or `refusal` | rule object; book-builder config (runtime check I-03, M8) |
| 17 | `value_timed_or_provisional_acting_input` | 19, 26 | an input with `role == "acting_exposure"` and `timing == "value_proxy"`; the provisional and bar-derived cases are runtime (T-LAG-01, T-PROV-01, T-BAR-01, M1; L6250) | rule object |

§10.3's table has 16 rows and §7 has 17 keys: §7 splits the regime-model row into keys 4 and 5. Items without a row (1, 3–7, 9, 10, 12–18, 20) "are design prohibitions with no configuration shape of their own. Code review enforces them" (L6252).

T-DNB-01's seven named shapes map to rows: (a) regime-model state → 4; (b) Mondrian conformal label layer → 7; (c) maintained ML challenger pipeline → 6; (d) `max(SMA20, implied)` sizing → 8; (e) product-composed de-risk stacks → 3; (f) venue switch after results → 10; (g) stock book as a market-gross scalar → 11 (L3380–L3387, L5682).

Label lookup for the error text: `do_not_build.items[<n>]` is a string `<label>_<basis>` or a map of variants. Print `harm · G` style from `harm_G`. For a variant map print the matching variant (item 11 with an `ml` estimator → `11a_ml_vol_state_classifiers: harm_E`), or all variants when the object does not identify one; item 27 always adds `prohibition: binding_red_line_E1` (L4651).

#### B3.5 Block-level DO-NOT-BUILD checks in `validate_store`

| Path | Must equal | Item |
|---|---|---|
| `gate.step3.n_gate` | `"max(N_clusters, N_equiv)"` | 36 |
| `gate.step3.forbidden` | contains `kish_design_effect` and `revision_count_as_N` | 36 |
| `gate.tiers.A_provisional` | `"closed"` | 34 |
| `cards.R-28_trend_axis.markets_refused` | contains `KR` | 37 |
| `instruments.market_scalar_on_stock_book` | `"refused"` | 33 |
| `instruments.cost_floor.lower_than_table` | `"forbidden"` | 23 |
| `gate.costs` | `"read_from_gate"` | 23 |
| `monitoring.forward_record_can_raise_verdict` | `false` | 35 |
| `breaks.bocpd` | `log_only: true`, `displayed: false` | 27 |
| `vol_target.display_labels` | `filtered_only: true`, `acts: false` | 24 |
| `vol_target.logged_alt_estimators` | does not contain a `max(…implied)` estimator | 30 |
| `vol_target.estimator_gate.stage3.complexity_order` | subset of `[sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]` | 11, 29 |
| `do_not_build.items` | keys `"1"…"37"`; each value (or each variant value) starts with `harm_`, `null_` or `inconclusive_`, except `11.11b_range_log_har == "admitted"` and `27.prohibition == "binding_red_line_E1"` | T-DNB-01 "each §10 entry is labelled" |
| `do_not_build.items["11"]` | has keys `11a_ml_vol_state_classifiers` and `11b_range_log_har` | T-DNB-01 "item 11 is split" |
| `do_not_build.refused_shapes` | exactly the 17 keys of row table B3.4 | L4662–L4679 |

### B4. `core/rules/governance.py` (N) — `governance_events.jsonl` (§6.6, L4094–L4119; L1248–L1250)

```python
KINDS  = ("halt","rearm","book_state","demotion","package_freeze","package_redesign","header_commit","owner_ruling","calendar_change",
          "notional_change","admissibility_reweight","binding_share_recompute","binding_change","record_reset","verdict_integrity")   # L4104-L4105
ACTORS = ("owner","operator","runtime","harness","council")                                                                              # L4108
REQUIRED = ("schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5")         # L4100

def append_event(path: Path, *, kind: str, actor: str, reason: str, refs: list[str], book_id: str | None = None,
                 rule_id: str | None = None, key: str | None = None, old=..., new=..., utc: str | None = None) -> dict
def verify_chain(path: Path) -> None        # raises on the first broken link; M8 wires it into app start and raises GOVERNANCE_LOG_BROKEN (T-OBS-05, L5681)
```
- Line = `canonical_json(event)` + `"\n"`, UTF-8. `schema: "quantgen.governance_event"`, `schema_version: "2.0"` (L4102). `event_id`: uuid4 string. `utc`: ISO-8601 with `Z` (L3507).
- `prev_row_md5` = md5 of the previous line's bytes without the newline; `null` only on the first line (L4096, L4110). `old` and `new` are optional and may be any JSON type (L4107); omit the key when not given.
- `kind ∉ KINDS` or `actor ∉ ACTORS` → raise before writing. The object is closed (the §6 closed-object rule, L3509): no other key.
- Append-only: open in append mode, one `write`, `flush`, `os.fsync`. Never rewrite an earlier line.
- "`core/rules` (M0) owns the appender; T-OWNER-01 writes the first event" (L4096). A `governance_event` line "is a log record, not an artifact, and carries only its own fields" (L3508): no `read_only`, no `config_hash`.
- VERBATIM example line (L4116–L4118), which T-SCHEMA-01 validates after replacing `<uuid>` and `<md5>` by typed samples:

```
{"schema":"quantgen.governance_event","schema_version":"2.0","event_id":"<uuid>","utc":"2026-10-02T06:41:05Z","kind":"book_state",
 "book_id":"recommended:KR","rule_id":null,"key":"engine_state","old":"DISARMED","new":"ARMED","actor":"runtime",
 "reason":"every acting input bound to the book fresh and past warm-up; calendars cover 60 sessions or more","refs":["§3.8"],"prev_row_md5":"<md5>"}
```

### B5. Cost model (R-26 rules 1–2, L2792–L2806; P10, L579–L603; §8.5, L5016–L5028)

**Single source of rates (F2).** In `core/quant/validate.py` add, beside `GATE`:
```python
COST_BPS_PER_SIDE = {"krx_etf": 3.0, "krx_stock": 35.0, "us": 50.0, "crypto": 10.0, "futures": 5.0, "fx": 10.0}   # values moved verbatim from docs/asset_expansion_study.py:60
```
and replace line 60 of the docs script by `COST = V.COST_BPS_PER_SIDE` (it already imports the gate as `V`). The spec's table (L582–L589): KRX ETF 3 / 6, KRX stock 35 / 70, US shares via KIS 50 / 100, crypto 10 / 20, futures 5 / 10, FX 10 / 20 bp per side at 1× / 2×. Stress factor = existing `GATE["cost_stress"]` (2.0). The header's `costs.schedule[].cost_class` values in the spec's example are `futures` and `krx_etf` (L4932–L4933), i.e. the existing keys.

**Functions** in `core/quant/backtest.py` (spec path L2775–L2777):
```python
def table_rate(cost_class: str) -> float
#   COST_BPS_PER_SIDE[cost_class]; "KRX_LI_ETF" -> table.get("KRX_LI_ETF", table["krx_etf"])  (L2803); any other unknown class raises
def tick_size(instrument: Instrument, on: date, price: float) -> float
#   effective-dated lookup; no row covering `on` -> raise NotTradable ("An instrument whose tick table cannot be read for the date
#   is not tradable in the simulated book", L2863)
def cost_per_side(instrument: Instrument, on: date, price: float, side: Literal["buy","sell"]) -> dict
#   returns {"table_bp", "floor_bp", "applied_bp"}  (the §6.5 names, L2854, L4046-L4047)
def stress_cost_line(cost_bp: float, sigma20: float, sigma_median: float, *, etf_close_fill: bool, abs_ret: float) -> float
```
VERBATIM formula (L2793–L2796):

```
   cost_side(i, t) = max( table_rate(cost_class(i)),
                          commission + 0.5 * tick(i, P_t) / P_t + tax_side(i, t) )
```

In bp:
```
table_bp   = table_rate(instrument.cost_class)
tax_bp     = sell_tax_bp(on) if (instrument.tax_side == "sell" and side == "sell") else 0.0     # "the sell tax on stock sells, 0.20% in 2026. ETFs are exempt" (L2798)
floor_bp   = commission_bp + 0.5 * tick_size(instrument, on, price) / price * 1e4 + tax_bp     # commission_bp = store instruments.cost_floor.commission_bp = 1.4 (L2797, L4395)
applied_bp = max(table_bp, floor_bp)                                                            # "It can only raise the table rate, never lower it" (L2792)
stress     = cost_bp * min(max(sigma20 / sigma_median, 1.0), 5.0) + (10.0 if (etf_close_fill and abs_ret >= 0.03) else 0.0)   # L2831, L4406; printed, never gated
```
- `price <= 0`, non-finite inputs, or an unknown `cost_class` → raise.
- Index-level and class-only costs (a header `schedule` row such as `{to: …, cost_class: futures}` before the KODEX 200 listing, L4932) have no instrument and no tick: they use `table_rate(cost_class)`.
- Worked values (checked here): 252670 at ₩69, tick ₩1 → half tick 72.46 bp, floor 73.86 bp, applied 73.86 bp (spec: 72.5 / 73.9, L2799). KODEX 200 at ₩112,060, tick ₩5 → half tick 0.22 bp, floor 1.62 bp, applied 3.0 bp (spec: ≈ 1.6, table 3). 252670 at ₩62 → 82.0 bp and at ₩579 → 10.0 bp (spec: 10–82 bp, L2879).

**Tick table and tax (the only values the spec gives).**
- ETF tick: "₩1 below ₩2,000 and ₩5 at ₩2,000 or more from 2023-12-11; earlier ticks come from the KRX notices (owner action)" (L2803). M0 ships that single effective-dated row. An ETF date before 2023-12-11 → `NotTradable`.
- Sell tax: 0.20% in 2026 on stock sells; ETFs exempt (L2798). R-20 (M1) supplies `sell_tax_pct` and `tick_regime` as regime tags (L2786); M0 ships the 2026 row only and raises outside it.
- Stock, futures, US and crypto tick tables are **not in the spec** (A-12, blocker B-3).

**Instrument metadata** in `core/markets.py` (spec fields L2774): `Instrument(code, type, leverage, tick_table, tax_side, cost_class, contract_multiplier, eligibility)`. M0 needs two rows for T-COST-02: `252670` (ETF, `cost_class: KRX_LI_ETF`, tax exempt) and `069500` KODEX 200 (ETF, `cost_class: krx_etf`, tax exempt). Leverage L, eligibility metadata (L2805) and contract multipliers are consumed from M5 (T-BOOK-03) and are not given numerically by the spec.

**Leveraged and inverse ETFs (L2801–L2806; T-BOOK-03 runs from M5, L5555).** Eligible only if `tick / price ≤ 10 bp` (`li_etf.max_tick_bp_of_price: 10`); cost class `KRX_LI_ETF` "never lower than the floor"; look-through × L in R-07.

**No lowering (T-COST-03; L2800, L2862, L4090, DNB #23).** `def check_cost_policy(header_costs: dict, instrument_book: str) -> None` raises when:
- `per_side != "read_from_gate"`, `floor != "tick_floor"`, `stress != 2.0`, `stress_line != "printed"` (the §6.5 consts, L3958–L3959), or any numeric per-side rate appears in the header;
- a `schedule` row's `table_rate(cost_class)` is below `table_rate` of the book's own class ("an optional effective-dated `schedule` that may only raise a cost", L4090).
`stress_cost_line(...) >= cost_bp` always (the clip floor is 1).

Book → default cost class (PROPOSED; only the first four are implied by the spec text): `KRX_ETF_line → krx_etf` (L895), `KRX_stock_book → krx_stock`, `US_shares_KIS → us`, `KOSPI200_futures / mini_KOSPI200_futures / CME_micro_ES → futures` (L4436), `crypto_venue → crypto`, `KRX_listed_SP500_ETF → krx_etf`, `FX_broker_spot → fx`, `FX_KRX_USD_futures →` the higher of `fx` and `futures` (10 bp; A-14).

### B6. `validate_card_header` — R-26 clauses (L2807–L2826, L4088–L4090, L4882; T-BOOK-01)

```python
def validate_card_header(header: dict, store: MacroStore, *, contract_notional_krw: float | None = None) -> None    # raises MacroRefusal
```
Schema validation against `model_card_header.macro.v2.0` (closed by `unevaluatedProperties: false`, L3927) is the schema brief's step and runs first; the checks below are the R-26 logic on top of it. The header has no `market` and no `exposure_basis` field (L3929–L3933), so checks 5 and 9 read them from the §7.1 rule object `store.rule(header["rule_id"])`; no such rule object → refused (A-15).

| # | Check | Refuse when | Source |
|---|---|---|---|
| 1 | Required | any of `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `fill_model` missing (`instruments.header_required`, L4398); also `gate.card_header_required` (L4617–L4618): `cash_convention, episode_rule_version, family_id, ledger_hash_at_registration, history_first_close, data_span` | L2859 |
| 2 | Book enum | `instrument_book` outside the 11-value enum; `multi_line` without `instrument_lines[]` (one declared line per market) | L2808 |
| 3 | Rebalance | `rebalance ∉ {daily, weekly, monthly}` | L2809 |
| 4 | Band | `no_trade_band ∉ {0.0, 0.10}`; `0.10` on a book outside `[KRX_stock_book, US_shares_KIS]` (`instruments.no_trade_band`, L4400). "declared ex ante, never tuned, and counted as one trial" | L2810 |
| 5 | Notional | `header.notional_nav != store.get("sleeves.<market>.notional_nav")`, or the store value is `null` ("A card cannot declare its own notional") | L2811, L4088 |
| 6 | `nav_fx` | a non-KRW book without `nav_fx` (`nav_fx_if_non_krw`). Non-KRW books (PROPOSED): `CME_micro_ES`, `US_shares_KIS`, `FX_broker_spot`, `crypto_venue` unless its venue is declared KRW. `nav_fx.role ∈ {acting_exposure, forward_sim}` = the role of the book it values | L2812, L3954–L3955 |
| 7 | Futures | `roll_calendar` missing on `KOSPI200_futures`, `mini_KOSPI200_futures`, `CME_micro_ES`, `FX_KRX_USD_futures` | L2814 |
| 8 | Granularity floor | on a futures line: `contract_notional_krw > 0.05 * notional_nav` (`max_contract_share_of_sleeve: 0.05`). Exactly 5% is allowed (`<=`). Default contract notional = `instruments.futures_granularity.contract_notional_krw` (`KOSPI200 280e6`, `mini_KOSPI200 56e6`, `CME_micro_ES 52e6`, `as_of 2026-10-02`, `use: header_check_only`); a caller with data passes `price × effective-dated multiplier × nav_fx` | L2816–L2821, L4401–L4402 |
| 9 | Stock book as scalar | the header's rule has `exposure_basis == "total"` (or `applies_to == "market_gross"`) and `instrument_book == "KRX_stock_book"` (and `US_shares_KIS`, A-10). Not refused: "An ex-pair stock basket used to meet a concentration cap (R-07, D1) is not a market scalar" | L2822–L2826 |
| 10 | Costs | B5 `check_cost_policy` | L2800, L4090 |
| 11 | Result fields | the header carries `selection_factor`, `timing_profile`, `forward_record` or any other result field (schema-level) | L3913, L4088 |
| 12 | Owner decisions | for each key in `header.owner_decisions`: value `!=` the store's value at commit. Checked only at commit, never afterwards | L5672, L4963 |

- Float check done here: `56e6 <= 0.05 * 1.12e9` is `True` in IEEE doubles; `56e6 > 0.05 * 1e8` (the ₩0.1bn case) refuses. Sleeve minimums: mini K200 ₩1.12bn, Micro ES ₩1.04bn (L2821).
- "A different instrument book, rebalance rule or band is a **new card** in the family ledger. A venue is never switched after results (DNB #23)" (L2815) → B3.4 row 10.
- Fail-closed list (L2858–L2863): missing required field → refused; futures line above the floor → refused; stock book as market scalar → refused; cost below the floor → raises; unreadable tick table → not tradable.
- R-26 rule 6 printed lines (execution variants A/B/C, overnight/intraday, turnover by regime, stress line, roll and ban-basis lines; L2827–L2832) are M7 (T-BOOK-02, L5558).

### B7. Read-only scan (T-RO-01; P0 L491–L500; §10 item 21 L6162; §3.10 L1255–L1264)

One test in `tests/macro_acceptance.py`, built on `tests/acceptance.py::_code_only` and `runtime_py()` (extended with `docs/*.py`, `tests/*.py` excluded, and every `*.yaml` under the repo once one exists). "The forbidden symbols and AST patterns are listed in the test" (L5605): the spec gives no list; the lists below are PROPOSED and start from the needles already in the suite.

1. **Forbidden imports** (`ast.Import` / `ast.ImportFrom`, top-level module): `ccxt`, `web3`, `alpaca`, `alpaca_trade_api`, `ib_insync`, `ibapi`, `pykis`, `mojito`, `pyupbit`, `binance`, `kiteconnect`, `MetaTrader5`.
2. **Forbidden strings** in code with docstrings stripped (case-insensitive):
   - already asserted today: `order_cash`, `order-cash`, `place_order`, `submit_order`, `TTTC0802U`, `TTTC0801U`, `VTTC0802U` (`tests/acceptance.py:171-172`); `KIS_ACCOUNT`, `CANO`, `ACNT_PRDT_CD` (`:181`); `/v1/orders`, `/v1/withdraws`, `/api/v3/order`, `private_key`, `seed_phrase` (`tests/expansion_acceptance.py:155`);
   - added: `VTTC0801U`, `TTTC0803U`, `VTTC0803U`, `/trading/order`, `order-rvsecncl`, `send_order`, `create_order`, `/v1/deposits/generate_coin_address`, `/v1/deposits/coin_address`, `/sapi/v1/capital/withdraw`, `/sapi/v1/capital/deposit/address`, `/fapi/v1/order`, `deposit_address`, `withdraw(`.
   - Do **not** use bare `order`, `cancel`, `deposit` or `transfer`: they hit the simulated book (`core/engine/orders.py`, `ui/trading_page.py:105-116`), `core/skills/runner.py:162`, `core/ficc/structured.py:251` (`dual_currency_deposit`).
3. **KIS paths**: every string literal containing `/uapi/` also contains `/quotations/` (true for all 29 today, F11).
4. **HTTP writes**: an `ast.Call` on attribute `post`, `put` or `patch` is allowed only in the allowlist `{core/quant/insights.py, data/krx/kis_client.py, data/krx/krx_market_client.py}` (F11). A new file with such a call fails the test until it is reviewed and added.
5. **Simulated book only**: `core.engine.orders` is imported only by `core/engine/*` today (`evaluator.py:36`, `runtime.py:53`, `__init__.py:4`); the test pins that set plus the future macro `engine_feed` module, and asserts that `._orders` is touched only inside `core/engine/orders.py`. No module outside `core/engine` constructs an order object except through `OrderBook`.
6. **Artifacts**: every artifact the M0 writer produces has `read_only is True`; the writer refuses a payload without it (schema const, L3508). The store root has `read_only: true` (L4137).
7. "Never add a broker execution adapter, even behind a flag: §3.10 records constraints, not a design" (task M0-01; L1257).

Runtime guard T-RO-02 is M1 (L5551, L5606); its I-01 clause is M8 (L5587).

### B8. Hermetic harness, test registry, fixture manifest (§9 L5491–L5499; §9.0a/b; §9.5 L6018)

**Suite.** `tests/macro_acceptance.py` exposes `tests() -> list[tuple[str, callable]]` like the six existing suites; `tests/run_all.py` gains one import and one list entry `[(f"macro/{n}", f) for n, f in macro_tests()]`.

**T-HERM-01.** A context manager `_no_network()` used around the whole macro list: replace `socket.socket.connect`, `socket.create_connection` and `socket.getaddrinfo` by a function that raises (stdlib only; it covers FRED, Yahoo, KIS, FMP, ECOS, Treasury, the Claude API and any later provider without naming them). Keep the existing module patches (`core.ficc.data._fred_fetch`, `_yf_fetch`). The test asserts the suite passes inside the guard and that a deliberate connection attempt raises.

**T-HERM-02.** In `tests/run_all.py`, hash before the loop and after it: every file under `core/rules/` (the store file included), every family ledger file (none before M7), `config.macro_rules_path()` if it lies elsewhere, and the file listing + md5s of `config.macro_artifact_dir()`. Any difference fails a final row `macro/T-HERM-02`. Every macro test builds its store, ledgers, artifact directory and `governance_events.jsonl` under `tempfile.TemporaryDirectory()`.

**Registry.** `tests/macro_registry.py`: `REGISTRY: dict[str, dict]` with `{"tier": "fast"|"golden"|"freeze", "runs_from": "M0"…"M10"|"M7a"|"M7b", "clauses": [{"text": str, "runs_from": str}]}` and `BUILT = "M0"`. `tests()` returns only ids with `runs_from ≤ BUILT` and skips deferred clauses. Tiers (L5496): `fast` unit tests, ≤ 10 minutes in total; `golden` fixture reproductions, ≤ 2 hours; `freeze` = I-08, the formal runs of I-07 and I-16, the GJR-null paths, PBO — run only in the M7 freeze job and at formal card runs; `run_all.py` verifies their md5s and never recomputes them. The spec assigns no tier per id (A-16). "A verdict derived from a statistic within tolerance of its threshold is asserted as a class … never as a point" (L5499).

VERBATIM `runs_from` table (§9.0a, L5548–L5561) — the registry's source:

| runs_from | Tests and clauses |
|---|---|
| M0 | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01 (its S2 clause from M8), T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses; its printed-line clause from M7), T-DNB-01, T-OWNER-01 |
| M1 | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-XMKT-01, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-CAL-01/02, T-RO-02, G-POST-01 (its data rows; the other rows and the deferred clauses of these tests per §9.0b) |
| M2 | T-CAP-02 (its stack-card clause from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; G-KR-01..04, G-KR-02b/02c, G-US-01/01b/01c; G-KR-06 (reference mode, only once §9.4 item 2's rerun is md5-frozen); deferred clauses per §9.0b |
| M3 | T-B5-01 (its "cannot be PASS" clause from M7), I-10, T-EST-01/02/04 (their Stage-3, bootstrap-CI and counted-revision clauses, T-EST-03 and T-EST-05 from M7); G-B5-01..04, G-EST-01..04 |
| M4 | T-R03-01 (sleeve-scale and years clauses; ΔSR +0.273 on the French fixture as research-phase ledger rows), T-PRIOR-01; G-MOM-01..06, G-MOM-08, G-INTL-01, G-BOOK-01; G-MOM-07 (reference mode) |
| M5 | I-04, I-04b, I-06, I-06b, I-06c, T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-BAR-01 (R-27 clause), T-HALT-01, T-STEP-05, T-BOOK-03, T-MONO-01; G-LAD-01..03 (reference mode, §9.3.3) |
| M6 | T-CTX-01/02, T-BREAK-01 |
| M7, before the freeze | The harness tests of §8.1.3 step 1: T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04; I-05; then I-08 with T-GATE-01 and T-GATE-03 (the acceptance test) |
| M7, after the freeze | I-08's US VT15 clause and T-GATE-02; I-09, I-07, I-15, I-16, T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-R03-01 (step-3 and header clauses), T-R04-01, T-R14-01, T-R06-US-01, T-CARD-01/02, T-REPRO-01b, T-BOOK-02, T-STEP-01..04 and every clause deferred above; G-KR-L*, G-US-F*, G-PWR-*, G-DSR-01/02 |
| M8 | I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-DEMOTE-01..05, T-TREND-01..04, T-USFUT-01..05, T-BASIS-01 (S2 clause); G-KR-05/05s, G-TR-*, G-REF-* |
| M9 | I-11, T-REPRO-01c |
| M10 | T-CRYPTO-01, T-FX-01 |

VERBATIM clause deferrals (§9.0b, L5567–L5597):

| Test (its §9.0a row) | Clause | runs_from |
|---|---|---|
| T-BASIS-01 (M0) | "vt is not applied to L/S sleeves or to TS trend" | M0 as a rules-store predicate on §7.1 `applies_to`; the runtime check M4 (L/S sleeves) and M7 (R-14) |
| T-CAP-01 (M0) | "The overlay layer cannot emit 0." | M2 |
| T-OWNER-01 (M0) | "the ruling is written to `governance_events.jsonl`" | M0 (the §6.6 appender is an M0 deliverable) |
| T-FIX-01 / G-POST-01 (M1) | Rows: KOSPI close and return, drawdown from the 9,114.55 peak, close / 200-day average, Samsung / SK hynix closes, the KRW=X row | M1 |
| | Rows: rv20, vt, G-KR-01, G-KR-02, G-KR-02b. "Unchanged" items: the 22 Jun / 23 Jun / 30 Jul / 2 Oct weights, the relative label and rv21, turnover, G-KR-02c, and G-KR-02b gross and at 3 bp | M2 |
| | Row: G-B5-01 PIT p | M3 |
| | Row: Samsung + SK hynix implied share (B3a anchor) | M5 |
| | Rows: R-06 KR 3 bp p_ni and R-06 KR 35 bp ΔSR (v1.2-check mode, §9.3.3) | M7, after the freeze |
| | Row: G-KR-05 share. "Unchanged" items: G-KR-05s and G-KR-05 on VT20 | M8 |
| T-ROLE-01 (M1; both tables) | The risk-model clause; "sets every risk-model default" | M2 |
| T-ROLE-02 (M1) | "sets `hedge_credit_off` through its corr63 binding" | M2 |
| | "a missing cash day refuses the card (never cash = 0)" | M7 |
| | "fails the R-28 and R-29 FORWARD-SIM books closed … and HALTs no recommended book" | M8 |
| T-LAG-01 (M1) | "refuses to write the card"; the `timing_probe` exception | M7 |
| T-LAG-02 (M1) | "Re-running a rule … must change the result" (on R-06's vt) | M2 |
| | The `timing_probe` clause | M7 |
| T-MISS-02 (M1) | The risk_model clause; the exceptions in `hedge_state`, `market_vol_target` and `compose` | M2 |
| | The exceptions in `concentration_bound` and `drawdown_ladder` | M5 |
| T-RO-02 (M1) | "I-01 runs with the HTTP transport patched …" | M8 |
| T-CLOSE-01 (M1) | "the workflow never starts before 06:40:30Z (§3.9)" | M8 (the R-35 workflow) |
| T-SEL-01 (M7, before the freeze) | (e) "The card run recomputes f; where it differs from the acceptance report's f …" | M7, after the freeze |
| T-HEDGE-01, R-19 table (M2) | The assertion on a built `macro_state` | M6 |
| T-COST-01 (M2) | "both legs for L/S sleeves" | M4 |
| | "a 2× run exists for every card" | M7 |
| G-US-01c (M2) | The EWMA(0.94) challenger | M3 (R-30 builds `ewma094`) |
| I-06c (M5) | "`macro_state` validates" | M6 |
| | "an acting-field schema error HALTs (OPS) the books the artifact describes" | M8 (`bounds_ok`) |

The HALT clauses of T-ROLE-01, T-LAG-01 and T-MISS-02 stay at M1, because M1 builds the OPS-only per-book runtime (§12 M1; R2-C6).

**Fixture manifest.** `tests/fixtures/macro/MANIFEST.csv`, columns: `file, source, series, span, retrieved_at_utc, value_status, available_at_source, md5, licence, owner, tests, seed, B, block_rule` (L6018, L6035; the last three for stochastic goldens: "Every stochastic golden names its seed, B and block rule").
```python
def fixture(name: str) -> Path      # raises unless: listed in MANIFEST.csv, md5 matches, licence, owner and md5 non-empty
def check_fixture_dir() -> None     # raises on any file in tests/fixtures/macro/ that MANIFEST.csv does not list
```
- "a file without them [licence, owner, md5] is not a fixture" (L6035).
- M0 ships the header row only: no M0 test in this brief needs a fixture file. Golden-value fixtures are generated at M1's exit (L5492; TASK-M1-22).
- The post-close rule (a close-type row retrieved before its session's close-print bound + 10 minutes is refused, T-FIX-01) is M1 (L5613).
- Sources named by the spec live under `/home/claude/quantgen_macro_data/` (L22), which does not exist here (F12).

### B9. Reproducibility record (§7 `reproducibility`, L4680–L4684; T-REPRO-01a L5666)

- `reproducibility.record` (VERBATIM): `git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run`.
- `determinism`: `canonical_json: sorted_keys_repr_floats_no_whitespace`; `volatile_fields: [generated_at_utc, git_hash]`; `rng: numpy_pcg64_seedsequence_spawned_children`; `blas_threads: 1`; `relative_tol: 1.0e-12`. Seeds: `seed_study: 11`, `seed_research_bootstrap: 20261002`.
- `config_hash` = `MacroStore.config_hash()` ("hash of the rules-store state", L3508).
- RNG: `np.random.default_rng(seed)` is `Generator(PCG64(SeedSequence(seed)))`, the convention `core/quant/validate.py` already uses; children: `np.random.SeedSequence(seed).spawn(k)` → `default_rng(child)`. Single-threaded BLAS: set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` to `1` in the study entry point before importing numpy (no new dependency). T-REPRO-01b (statistics, M7) and T-REPRO-01c (Monte Carlo, M9) test the numbers; M0 tests the metadata only.
- `data_snapshot_id` is a labelled stub string until the M1 store provides `data_snapshot_id(knowledge_utc)` (L1014).
- `git_hash`: see blocker B-1.
- Which fields go where (A-17): every artifact carries the §6 common set `schema, schema_version, generated_at_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id, read_only` (L3508); a card additionally carries `seed`, `ledger_hash_at_registration` (header), `ledger_hash_at_run`, `results_md5`, `gate_package_version`, `gate_package_md5`. `header_md5` covers header fields only; `results_md5` covers result fields (L3913).

### B10. TASK-M0-15 (§9.4 item 7, L6004; §10.1 L6060–L6061)

- Procedure: bootstrap the book-level variant behind every E-labelled item "as `qf3_dnb_classes.py` does (63-day blocks, 1,000 resamples)"; each result replaces the E label with a B label through a logged store revision (history `kind: "label_update"`). B thresholds (L6054–L6056): `harm` = the 90% ΔSR interval lies below 0; `null` = the interval lies within ±0.10; `inconclusive` = it straddles 0 and is wider than ±0.10.
- "A label never lifts a prohibition" (L6066). The 27 E labels (script-extracted): items 4, 7, 10, 13, 15, 16, 17, 20, 28, 29, 37; 6 (`mom_under_rates_stress`, `level_thresholds`); 9 (all three variants); 11 (`11a_ml_vol_state_classifiers`, `unpenalised_hmm_ms_gates`, `complexity_rff_timing`); 12 (all three); 14 (both); 27 (three variants).
- Not runnable on this machine: the script, its inputs and each item's variant return series are absent (F12). Leave every E label as written; T-DNB-01 still holds.

## C. Schemas and config

### C1. YAML to JSON (how to write `core/rules/macro_rules.json` from the block below)

`yaml.safe_load` of the block gives the document. Apply exactly these conversions, then add `"rules": […]` and `"history": [{seed entry}]`:
1. `do_not_build.labels` parses as `["harm", None, "inconclusive"]` (L4621: bare `null`) → store `["harm", "null", "inconclusive"]`.
2. `instruments.futures_granularity.contract_notional_krw.{KOSPI200, mini_KOSPI200, CME_micro_ES}` parse as the strings `"280e6"`, `"56e6"`, `"52e6"` (PyYAML needs a dot for a float) → store numbers `280000000.0`, `56000000.0`, `52000000.0`.
3. Integer keys become strings in JSON: `do_not_build.items` `1…37` → `"1"…"37"`; `families.momentum.own_vol_scale.revisions` `2, 3` → `"2", "3"`.

Legitimate nulls after parsing (15): `owner_decisions.D1…D6.effective_from` and `.rationale`; `vol_target.other_markets.target_ann`; `sleeves.US.notional_nav`; `sleeves.KR.notional_nav`. Strings that must stay strings: `version "2.0.0"`, `gate.package.version "2.0.0"`, `gate.evaluation.episode_rule.version "1"`, `gate.card_p_v2.pc1_prime.gate_cost "1x"`, `cards.R-29_US_FUT.settling_run.pc1_prime_at ["1x","2x"]`, `sleeves.US.line "none"`, `cards.R-29_US_FUT.rule.floor "none"`.
YAML comments are not stored ("the JSON store has no comments, so no marker lives in a comment", L65).

### C2. §7 rules-store entries — VERBATIM (L4135–L4684)

```yaml
version: "2.0.0"                         # v2.0: Quant Council edition (v1.2.0 → 2.0.0)
as_of: "2026-10-02"
read_only: true                          # no order path; nothing here can enable one
owner_decisions:                         # canonical statement: the Quick start table (C-8); status: default | owner_set | pending
  # one canonical key per decision, a plain scalar; a rule block holds {ref: <key>}, never a literal copy (T-OWNER-01)
  D1: {key: risk_layer.korea_caps.template, value: msci_25_50, default: msci_25_50, options: [domestic_max10_or_weight, msci_25_50, pair_35],
       status: default, effective_from: null, rationale: null, refs: []}
  D2: {key: risk_layer.drawdown.hard_stop.level, value: -0.15, default: -0.15, options: [-0.15, "-1.5*sigma_book"], status: default,
       effective_from: null, rationale: null, refs: [cards.R-31_step_down.hard_stop_level]}   # a ruling gives R-31 a counted revision
  D3: {key: families.reversal.calm_state_downweight, value: not_adopted, default: not_adopted, options: [not_adopted, reopen_after_krx_net_test],
       status: default, effective_from: null, rationale: null, refs: []}
  D4: {key: monitoring.false_demotion_budget_per_year, value: 0.10, default: 0.10, options: [tighten_only_le_0p10], status: default,
       effective_from: null, rationale: null, refs: []}
  D5: {key: sleeves.US.line, value: none, default: none, options: [CME_micro_ES, KRX_listed_SP500_ETF, none], status: pending,
       effective_from: null, rationale: null, refs: [instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]}
  D6: {key: gate.acceptance_test.cdar_guard.calibration, value: lowest_placebo_false_pass_rule, default: lowest_placebo_false_pass_rule,
       options: [lowest_placebo_false_pass_rule, professors_bootstrap_one_sided_5pct, executives_placebo_p10_margin, qf_blind_margin], status: default,
       effective_from: null, rationale: null, refs: []}   # frozen with the package (R2-C2); applied only if a negative control passes (R-21 9(d)); a ruling only before the first attempt
time:
  storage_tz: UTC
  decision: close_t_earn_t_plus_1        # QUANTGEN rule 02
  calendars: effective_dated             # R-20: decision_time_utc() (the scheduled close), close_print_bound_utc() and usable_at() are calendar lookups
  decision_instant: close_print_bound_utc   # macro_state.decision_utc and the lag-audit instant: KRX scheduled close + 30 s (06:00:30Z
                                            #   2015-06-15..2016-07-29, 06:30:30Z after); NYSE 16:00 ET + 30 s, DST-aware (R-20)
  markets:
    KR:  {tz: Asia/Seoul, session: calendars.KR, scheduled_close_utc: calendar_lookup, close_print_bound_utc: calendar_lookup,   # today 06:30:00Z / 06:30:30Z; never read as constants
          session_rules: calendars.KR, regime_tags: calendars.regime_tags_file, open_no_entry_minutes: 30}
    US:  {tz: America/New_York, session: ["09:30","16:00"], decision_utc: close_print_bound_utc, session_rules: calendars.US}   # scheduled close + calendars.US.close_print_bound_s
    CRYPTO: {tz: UTC, decision_utc: "00:00:00Z of d+1", venue_declared: true, annualisation_days: 365}   # the bar dated d closes at 00:00:00Z on d+1 (R-17; deferred)
  cross_tz_rule: "us_dated_D_usable_for_KR_close_K_iff_D_le_K_minus_1_and_available_at_le_decision"
  cross_market_rule: data_contracts.cross_market   # R-19
  business_days: {publication: fed_sifma_calendar, decision: exchange_calendar}
  publication:
    H15: {posted: "16:15 ET on the next Fed business day"}
    H10: {posted: "Monday 16:15 ET; next business day if Monday is a Federal holiday"}
    TREASURY_PAR: {posted: "usually by 18:00 ET on D", log_posting_time: true, us_close_decision_bdays: 1}
    VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}
    BLS: {posted: "08:30 ET"}
    ECOS_USDKRW: {close_kst: "15:30", close_1500_until: "2016-08-01", snapshot_1530_from: "2026-07-06"}
calendars:                                           # R-20; data files in core/calendars/data/ (owner-signed)
  KR:
    close_kst: [{to: "2016-07-31", time: "15:00"}, {from: "2016-08-01", time: "15:30"}]
    closing_call_kst: [{to: "2016-07-31", window: ["14:50", "15:00"]}, {from: "2016-08-01", window: ["15:20", "15:30"]}]
    random_end: [{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, triggered_extensions: from_krx_notice},
                 {from: "2015-06-15", kind: unconditional, max_s: 30}]   # bound = scheduled close + max_s, or + print_tolerance_s before 2015-06-15
    csat_session_kst: [{to: "2016-07-31", window: ["10:00", "16:00"]}, {from: "2016-08-01", window: ["10:00", "16:30"]}]   # pre-2016 window UNVERIFIED: confirm from the KRX notice at the M1 sign-off
    csat_closing_call_kst: [{to: "2016-07-31", window: from_krx_notice}, {from: "2016-08-01", window: ["16:20", "16:30"]}]   # R-27 CSAT snapshot; confirm at the M1 sign-off
    first_trading_day_open_kst: "10:00"
    saturday_sessions_before: "1998-12-12"
    saturday_session_close_kst: from_krx_notice       # owner-signed at M1; decision_time_utc and the bound exist for Saturdays
    excluded_sessions: [{venue: NXT, window_kst: ["15:40", "20:00"]}, {venue: KRX_after_market, from: "2026-09-14", window_kst: ["16:00", "20:00"]}]
  US: {close_et: "16:00", early_close_et: "13:00", holiday_set: NYSE, tz: America/New_York, close_print_bound_s: 30}   # M1 confirms the bound from logged print times
  JP: {close_jst: [{to: "2024-11-04", time: "15:00"}, {from: "2024-11-05", time: "15:30"}], close_print_bound_s: 0}   # default, judgment: the 60 s buffer covers dissemination
  CN: {close_cst: from_sse_notices, close_print_bound_s: 0}          # SSE 15:00 CST today; effective-dated, owner-signed at M1 (§9.5)
  HK: {close_hkt: from_hkex_notices, close_print_bound_s: 0}         # HKEX 16:00 HKT today (closing auction from the notices)
  TW: {close_tst: from_twse_notices, close_print_bound_s: 0}         # TWSE 13:30 TST today (earlier hours from the notices)
  holiday_sets: [KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS]   # kept separate (QF2-A11); every registered input's obs_calendar
  regime_tags_file: core/calendars/data/kr_regime_tags.yaml
  change_control: {owner_sign_off: required, test_per_change: required}
  coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}   # T-CAL-02
data:
  store: {append_only: true, bitemporal: true, as_of_reads: true, snapshot_id: md5_of_visible_content_hashes}
  knowledge_utc: {pinned_once_per_run: true, defaults_to_now: false, written_to_every_artifact: true}   # R-01, §3.5
  run_mode: {values: [live, backtest, replay], selects: [production_channel, history_channel]}        # §3.9, §4.2
  value_status_rank: [official_close, revised, first_release, vendor_close, vendor_derived, vendor_derived_across_gap, live_snapshot, provisional_intraday]
  vendor_close_in_backtests: only_if_card_header_declares_the_vendor_as_data_source   # §4.1
  ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min,
           dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never,
           posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}   # deadline and poll window: default, judgment
  value_status_required_for_close_inputs: official_close
  require_session_match: true
  reject_rows_retrieved_before_close_plus_minutes: 10   # anchor: close_print_bound_utc of the row's session (R-01, T-FIX-01)
  reconciliation: {primary: [KIS, KRX], secondary: vendor, tol_index_bp: 1, tol_stock: exact,
                   on_mismatch: disputed_use_official_and_alert, auto_correct: false}
  stale_carry_flag: flat_ohlc_zero_volume_on_session_day
  daily_close_from_bars: forbidden
  bars: {stamp: bar_end, closing_auction_own_bar: true, available_at: bar_end_plus_latency}
  open_quality_flag: open_equals_prior_close
  fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}
  fail_closed_on_missing_acting_input: true
  synthetic_for_acting_inputs: forbidden # 'auto' provider degrade -> MissingInput
  interpolate: false
  monthly_lag_method: calendar           # never positional
  vintages: {source: alfred, store_first_release: true, store_latest: true}
  derived_series_in_house: [sahm, yoy, taylor_range]   # a gap gives NaN
  named_series_required: true
  brent_series: {spot: DCOILBRENTEU, futures: BZ=F}
  usdkrw: {input: [ECOS_1530_CLOSE, USDKRW_1530_SNAPSHOT], proxy: DEXKOUS, proxy_timing: H10_publication, production_reads_dexkous: false,
           record_fx_regime: true}
  us10y: {production: US10Y_KIS_QUOTE, history: [TREASURY_PAR, DGS10], dgs10_strict_lag_bdays: 2, treasury_lag_bdays: 1, live_proxy_history: "^TNX"}   # lag counts document the usual case only; code uses usable_at() (first close after the publication instant); counted on NYSE days the DGS10 count leaks on Columbus and Veterans Day
data_contracts:                                      # R-19
  staleness_rule: schedule_aware                     # stale iff decision_utc > expected_available_utc(series, last_obs) + grace, where
                                                     #   expected_available_utc = when the NEXT obs after last_obs is due (R-19 step 3)
  grace_publication_bdays: 1                         # Resolution 7
  source_exceptions: core/calendars/data/source_skipped.yaml   # owner-signed, versioned
  on_failure:
    acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books,
                      book_counter_halt_after: 2}   # "more than one decision"; per (book, series) and per book (R-19 rule 4)
    risk_model:      {action: conservative_default, set: {hedge_credit_off: true},
                      hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never,
                      also_on: hedge_state_exception}
    context:         {action: label_stale}
    forward_sim:     {action: fail_closed_that_book, alert: true, halt: never}
    history:         {action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}
    risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never,
                            sets_hedge_credit_off: false}   # default, judgment (R-19 rule 4)
    not_failures:    [warmup_before_first_armed_decision, disputed]
  cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}    # buffer: default, judgment
  ranges: {abs_daily_return_max: {KOSPI: 0.30}, VIXCLS: [5, 150], yields_pct: {US_TREASURY: [-1, 20], KR_CALL_CD: [-1, 40]}}   # Korean rates ran at 16-25% in 1997-98
  roles:                                             # bindings per (series, consumer, books); a scalar acting entry means its
                                                     #   market's [recommended, specification] books (R-19 rule 5)
    KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-06 KR (R-19 rule 5); vt enters it as 1.0 until then
    US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}      # no US sleeve while sleeves.US.line = none (D5)
    NAV_LINE_CLOSES: [{role: acting_exposure, consumer: nav, books: [recommended, specification], halt_after_consecutive_decisions: 3},
                      {role: forward_sim, consumer: nav, books: ["forward_sim:R-28", "forward_sim:R-29"]}]   # group (registry): each held line's official close, e.g. KODEX 200 (069500); a card's books bind their lines the same way (R-19 rule 5)
    SPX_OFFICIAL_CLOSE: [{role: forward_sim, consumer: R-28_R-29, books: ["forward_sim:R-28", "forward_sim:R-29"]},
                         {role: risk_model, consumer: corr63},
                         {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}]
    SOX_CLOSE: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}
    KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}
    KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}
    MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-03 (R-19 rule 5)
    DM_MKT_RET_24M: {role: acting_exposure, books: [specification]}        # R-04
    DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}        # R-04
    NON_KR_INDEX_MONTH_END_CLOSES: {role: forward_sim, books: ["forward_sim:R-28"]}
    USD_LIVE_PROXY: risk_model                       # one named series (§4.2), read as a quote snapshot stamped <= the decision instant
    PCEPILFE: risk_model
    US10Y_KIS_QUOTE: [{role: risk_model, consumer: corr63}, {role: context, consumer: R-12_refusal_book}]   # production
    DGS10: [{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]   # strict H.15
    ASIA_INDEX_CLOSES: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}   # Nikkei, Shanghai, HSI, TAIEX
    DTWEXBGS: context                                # never acting
    DEXKOUS: context                                 # R-11 retired; labelled proxy
    ECOS_1530_CLOSE: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx_backtests, books: ["forward_sim:R-29"]}]   # nav_fx history (R-26)
    USDKRW_1530_SNAPSHOT: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx, books: ["forward_sim:R-29"]}]   # nav_fx (R-26, R-29)
    BOK_CALL_RATE: history                           # R-22 cash leg (card harness only)
    US_RF: history                                   # R-22 cash leg (card harness only)
  unscheduled_delay: event_status_delayed
overlay:
  floor: 0.5
  cap: 1.0
  combine: min                           # R-02; a product-composed path raises
  floor_vs_vt_outside_halted: 0.5        # composed >= 0.5 x vt on every non-HALTED day (T-CAP-02)
  zero_only_in: [risk_layer, book_HALTED]           # per book (§3.8)
  books: [recommended, specification, forward_sim_per_card, refusal_display_only]
  recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]   # the first two need verdict PASS; INVARIANT_STEP: R-31 at binding share <= 0.10
  stack_card: {when_de_risk_factors_ge: 2, class: CARD-P, spec: "§8.7"}   # R-02
base_weights:                            # R-15
  cross_market: {method: inverse_vol, returns: weekly, cov_acting: ewma_0.97, cov_printed: ledoit_wolf_156w, spans: markets_with_sleeves}   # no HRP, no min-variance; ERC only for multi-asset sleeves
  family: {admissible_if: {prior_min: 1, card_verdict_not: REJECT}, weight: one_over_K, range_prior: lower_bound,
           no_registered_prior: not_admissible, not_run_admissible_except: [ts_trend], reject_reweight: logged_governance_event}   # R-15
  tilt_requires_family_card_pass: true
vol_target:                              # R-06 (cap 1.0 permanent, no floor)
  KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total,
       instrument_book: KRX_ETF_line, notional_nav: {ref: sleeves.KR.notional_nav}, rebalance: daily, no_trade_band: 0.0, fill_model: KRX_close_auction,
       card: {card_id: MACRO-R06-KR-ETF, build_status_on_pass: BUILD_AS_INSURANCE, conditions: see_R-06_card_korea, forward_record: falsification_only}}
  US: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, cap_permanent: true, exposure_basis: total,
       registered_card: {instrument_book: US_shares_KIS, verdict: REJECT, label: "REJECT (instrument: US shares via KIS, 50 bp, daily)", rerun: false},
       futures_card: cards.R-29_US_FUT}
  other_markets: {estimator: sma, window: 20, target_ann: null, cap: 1.0}   # pre-register per market on its card
  estimator_gate:                                    # R-30 (replaces v1.2 B5-only selection)
    acting_default: sma20                            # also the displayed baseline
    challenger: {name: comb, definition: "0.5*(gjr_t + log_har_range)", books_allowed: [KRX_ETF_line, KOSPI200_futures,
                 mini_KOSPI200_futures, CME_micro_ES], books_refused: [KRX_stock_book]}
    fit: {window: expanding, min_years: 10, refit_every_origins: 21}
    range_proxy: {KR: overnight_sq_plus_garman_klass, US: parkinson}
    stage1: {horizon_days: 21, tests: [fhs_var_exceedance_h21, fan_pit_h21, christoffersen_cc], printed: [kupiec_1d, cc_1d_95_99, es975_z2]}
    stage2: {loss: qlike, mcs_level: 0.90, stat: T_max, block: "max(10, 2h)", resamples: 2000, seed: 11, mse_mcs: printed}
    stage3: {objective: min_vol_of_vol_rolling63, eligibility: [dSR_noninferior_vs_sma20_delta_0p10, dMDD_vs_sma20_ge_0, pc2_le_0p90],
             ties: overlapping_bootstrap_ci, tie_break: simplest_surviving,
             complexity_order: [sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]}
    switch: {counted_revision: true, full_v2_card_p: true}
    fallback_to_sma20: {gjr_bounds: {persistence_max: 0.9999, nu: [2, 100]}, open_quality_max_share: 0.05,
                        flat_range_max_share: 0.05, window_sessions: 252}       # thresholds: default, judgment
    incumbent_calibration: {name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}
  annualisation_days: 252
  sigma: {returns: simple, ddof: 1, mean_adjusted: true, stale_carry_days: excluded_window_extends}   # R-06
  warmup: {min_valid_returns: 20, value: 1.0, status: warmup, counts_as_failure: false, only_before_first_armed_decision: true, after_armed: MissingInput, degenerate_sigma: MissingInput}   # T-VT-01
  display_labels: {rel: {method: trailing_756_quartiles}, abs: {method: expanding_full_history_quartiles, min_years: 10},
                   values: [calm, normal, elevated, stressed], filtered_only: true, acts: false,
                   per_label_coverage: reported, scoring: tick_loss}
  logged_alt_estimators: [asymmetric_slow_cut_fast_restore]   # BL-C04; max(sma20, implied) retired
families:
  momentum:
    own_vol_scale: {window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, exposure_basis: active,
                    series: paper_unit_gross_long_short, apply_to: sleeve_budget,
                    revisions: {2: {target: expanding_median_sigma126, min_obs: 252}, 3: {vs: "min(1, (0.12/sigma126)^2)"}}}
    dm_gate: {market_return_months: 24, market_vol_window: 126, vol_quantile: 0.6667, quantile_min_obs: 252,
              multiplier: 0.5, exposure_basis: active, books: [specification], label: "step 3 FAIL", a_provisional_route: closed, pooled_revision: none}
  reversal: {overlay: fixed_1.0, intraday_leg: false, calm_state_downweight: not_adopted}   # canonical key of D3 (Quick start)
  quality:  {overlay: fixed_1.0}
  flow:     {overlay: fixed_1.0}
  ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true,
             card: {class: CARD-O, claim: diversification, instrument_book: multi_line}}   # one declared line per market (R-14, R-26); target: default, judgment
weights_prior: see_R-15                  # 0-3 integers: admissibility filter and display only
prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}   # one-sided (prof); live_sharpe_multiplier 0.60 (take 40% off) printed too
risk_layer:                              # core/quant/risk + core/engine
  korea_caps:
    lookthrough: {source: daily_etf_pdf, leveraged_multiplier: L}
    template: msci_25_50                 # canonical key of D1 (Quick start)
    templates:
      msci_25_50: {single_name_max: 0.225, names_above: 0.045, aggregate_max: 0.45, review: [quarterly, on_breach],
                   breach_single_name: 0.25, breach_aggregate: 0.50}   # targets bound g daily; a breach is above the hard levels after the action
      domestic_max10_or_weight: {single_name_max: "max(0.10, market_cap_weight)"}
      pair_35: {pair_max_share_of_sleeve_nav: 0.35}    # look-through, cash in the denominator (R-07 (3))
    active_single_name_cap_nav: 0.05     # w_i - g * b_capped_i <= 0.05 NAV
    active_bound: "0.05 / (s_i - b_capped_i) for every name with s_i > b_capped_i"   # R-07 (4)
    semis_max_share_of_sleeve_nav: 0.50  # default, judgment; look-through, cash in the denominator (R-07 (5))
    report_by_book: true                 # concentration.by_book (§6.1)
    meet_cap_order: [lower_etf_line_weight, ex_pair_basket_only_if_owner_and_stock_card_pass_and_limit_lock_flags]
    report: [pair_lookthrough_share, pair_risk_contribution]
  drawdown:
    reference: whole_book_nav            # per-market attribution printed
    composition: min                     # with the overlays (R-02)
    steps: cards.R-31_step_down          # -8% / -12% totals, 21-session dwell; specification book while the binding share > 0.10
    hard_stop: {level: -0.15, alt: "-1.5*sigma_book", reference: hwm_since_last_rearm, action: book_HALTED, class: RISK,   # level: canonical key of D2
                scope: own_book_nav, rearm: automatic, rearm_refused_sessions: 10, rearm_calendar: book_primary_market,
                rearm_resets: [hwm_hard, ref_step], post_rearm_cap: 0.5, post_rearm_sessions: 10, post_rearm_cap_in_min: true,
                idempotent_while_halted: true, log: governance_review_event, protection_claim: false}
  halt_scope: per_book                  # C-1: only the books whose own NAV, artifact or bound acting input failed (§3.8)
  halted_triggers:
    RISK: [hard_stop, risk_limit_breach]   # breach: re-arm after 10 sessions only once the post-action target weights meet the limit; no reference reset; post_rearm_cap 0.5 from the actual re-arm
    OPS: [lag_audit_violation, acting_field_schema_or_bounds_failure, acting_input_fail_closed_beyond_declared_misses,
          feed_heartbeat_loss_60s, acting_risk_layer_exception, whole_book_nav_unavailable_gt_2_decisions, calendar_coverage, operator_kill,
          acting_step_error_beyond_limit]   # run_error (§3.9)
  heartbeat: {loss_s: 60, blocks_new_intraday_entries: immediately, auto_rearm_after_restored_min: 5}   # default, judgment
  ops_rearm: {when: cause_cleared, operator_required_after: [lag_audit_violation, acting_field_schema_or_bounds_failure],
              reference_reset: false, post_rearm_cap: false}
  never_halt_on: [risk_model_input_stale_or_failing, hedge_state_exception, context_input_stale, disputed_input, warmup_input_before_first_armed_decision,
                  input_bound_only_to_other_books, display_or_context_field_validation_failure, context_log_or_event_calendar_validation_failure]
  korea_covariance_extra: [SHANGHAI, HSI, TAIEX, NIKKEI]   # synchronous or lagged returns
  hedge_state: {core_pce_yoy_threshold: 0.030, corr_window: 63, corr_threshold: 0.0, corr_pairs: date_aligned, lag: statistic_not_leg,
                stale_input: hedge_credit_off, exception: hedge_credit_off, usd_input: USD_LIVE_PROXY, reasons_field: flags.hedge_reasons,
                hedge_failure_daily: {equity_ret_lt: -0.015, usd_ret_lt: 0.0},
                hedge_failure_weekly: {equity_ret_lt: -0.02, usd_ret_lt: 0.0},
                fx_hedge_credit: {display_only: true, window_weeks: 26, credit_if_corr_lt: 0.0},
                stressed_covariance_from_turbulence: only_after_preregistered_win}
annotations:                             # core/engine/evaluator; no exposure effect (R-08)
  vix_ts: {condition: "VIXCLS >= VXVCLS", threshold: 1.0, tuned: false, clearing: raw_parity_flag, action: annotate_only,
           request_kis_spread_snapshots: true, from: "first decision after the 16:15 ET VIX close", switch_budget_per_year: 14.0}   # logging only (R-08); card switch triggers follow R-25
events:                                  # core/calendars; evaluator blocks on simulated entries only (R-10)
  us_cpi_nfp: {block_new_intraday_entries_et: ["08:25","10:00"], resume_et: "10:00"}
  us_leaky_releases_pre_minutes: 30
  fomc: {block_new_intraday_entries_et: ["13:45","15:00"], resume_rule: "VIX<pre14 else 15:30", pre_fomc_long: false}
  bok_decision: {kospi200_futures_block_kst: ["09:45","10:15"], equity_daily_change: none}
  bok_press_conference: {kospi200_futures_block_kst: ["11:00","11:45"], equity_daily_change: none}
  kr_open: {block_first_session_minutes: 30, window_kst: ["09:00","09:30"], late_open_window_kst: ["10:00","10:30"],
            late_open_days: [first_trading_day_of_year, csat]}   # = time.markets.KR.open_no_entry_minutes (R-10)
  kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]
  multi_session_gap: {tag: gap_sessions, gap_sessions_min: 0, var_display_scale: "sqrt(max(n_us, 1))", report_separately: true, gross_rule: false}
  sidecar_cb: {block_new_entries_minutes_after_cb_reopen: 30, quotes_during_halt: indicative, gross_cut: false}
  daily_book_blackouts: false
  tags_change_weights: false
fill_model:                                          # R-27 (simulated book only)
  KRX: {snapshot: closing_call_start_minus_1min, snapshot_kst_since_2016-08-01: "15:19", fill: official_close, random_end_max_s: 30,
        fallback: post_close_session_UNVERIFIED, limit_price: tick_rounded_toward_prev_close,
        etf: {flag: LP_exempt_auction, inav_residual_flag_bp: 30}, limit_lock: non_fillable_at_close}
  NYSE: {snapshot_et: "15:50", fill: official_close_moc_equivalent}
  KOSPI200_futures: {trades_until_kst: "15:45", expiry_day_stop_kst: "15:20"}
  bars: {stamp: bar_end_utc, closing_auction_bar: separate, available_at: "bar_end + latency", daily_close_from_bars: forbidden}
instruments:                                         # R-26
  cost_floor: {formula: "max(table_rate, commission + 0.5*tick/price + tax_side)", commission_bp: 1.4,
               lower_than_table: forbidden}          # commission: EX2 quote; owner confirms vs broker schedule
  li_etf: {max_tick_bp_of_price: 10, cost_class: KRX_LI_ETF, lookthrough_multiplier: L, eligibility_rules: metadata}
  header_required: [instrument_book, rebalance, no_trade_band, notional_nav, fill_model, nav_fx_if_non_krw]
  notional_source: sleeves.<market>.notional_nav     # owner-signed, effective-dated; a card never declares its own
  no_trade_band: {allowed_values: [0.0, 0.10], allowed_books: [KRX_stock_book, US_shares_KIS], tuned: false}
  futures_granularity: {max_contract_share_of_sleeve: 0.05,
                        contract_notional_krw: {KOSPI200: 280e6, mini_KOSPI200: 56e6, CME_micro_ES: 52e6, as_of: "2026-10-02", use: header_check_only}}   # backtests compute notional PIT: price x effective-dated multiplier x nav_fx
  market_scalar_on_stock_book: refused
  us_shares_50bp: single_names_only
  printed_lines: [exec_variants_ABC, overnight_intraday, turnover_by_regime, stress_cost_line, roll_cost, ban_period_basis]
  stress_line: {multiplier: "clip(sigma20/sigma_median, 1, 5)", etf_close_extra_bp_if_abs_ret_ge_3pct: 10, gated: false}
  us_line_choice: {ref: sleeves.US.line}            # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
refusal_books:                           # R-11, R-12: REJECT recorded; display only; read by no book; off the re-gate queue
  S1_krw: {lookback_obs: 20, threshold_dlog: 0.03, multiplier: 0.75, target: KR_market_gross, one_sided: true, verdict: REJECT, regate_queue: false}
  S2_rates: {lookback_obs: 20, threshold_pp: 0.40, multiplier: 0.5, target: US_duration_sensitive_gross,
             excludes: [momentum, ls_factor_sleeves, KR], verdict: REJECT, regate_queue: false}
cards:                                   # R-28, R-29 (FORWARD-SIM) and R-31 (specification book until PASS)
  R-28_trend_axis:
    rule: {signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0,
           decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}
    claim: "slow-bear protection via the volatility state"
    judged: {incremental_on: vol_targeted_book, comparator: S_of_VT_book, claim_line_stacked_dMDD_min_pp: 3.0,
             claim_line_failure: cap_INSUFFICIENT}
    pooling: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true,
              declared_before_any_run: true}
    markets_allowed: [US, other_non_korean]
    markets_refused: [KR]
    logged_trials_same_ledger: [BAND200]
    status: FORWARD_SIM
    us_sleeve: {ref: sleeves.US.line}                # D5 (Quick start); FORWARD-SIM while none
    instrument_book: CME_micro_ES                    # US instance: incremental on R-29's futures vt book
    rebalance: monthly
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}
    fill_model: NYSE_moc
  R-29_US_FUT:
    card_id: MACRO-R06-US-FUT
    family: R-06                                     # one new trial in the R-06 ledger
    rule: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}
    instrument_book: CME_micro_ES
    cost_class: futures                              # 5 bp per side, read from the gate
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}   # live only if one contract <= 5% of it (R-26 granularity floor, checked at the header commit)   # ~KRW 1bn; never declared on the card
    nav_fx: {series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}
    episodes: {theta: 0.15}
    settling_run: {data: FF_daily_MktRF_1926-07_to_2026-08, cost_bp: 5, pc1_prime_at: [1x, 2x],
                   starts: decade_spaced, pass_share_min: from_band_shape, no_reject_at_any_start: true,
                   no_reject_in_midpoint_halves: true, full_span_must_pass: true}
    promotion: {requires: [us_sleeve_or_owner_line, settling_run_pass, v2_package_pass]}
    us_sleeve_and_line: {ref: sleeves.US.line}       # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
    logged_trials: [monthly_50bp, band_0p10_50bp]
    status: FORWARD_SIM
  R-31_step_down:
    steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]   # totals, non-cumulative
    dwell_sessions: 21
    step_reference: running_peak_since_last_reset    # resets at dwell end and at re-arm
    hard_stop_reference_resets_at_dwell_end: false   # R-07 reference; resets only at re-arm
    composition: min
    denominator: whole_book_nav
    binding_share_threshold: 0.10                    # > 0.10 -> specification book until PASS
    binding_share: {book: recommended_without_steps, span: declared_history, computed_at: [header_commit, composition_change],
                    window: full_never_trailing, compare: "n_bind / n_sessions > 0.10", disposition_if_le: INVARIANT_STEP}
    judged: {incremental_on: declared_book_without_steps, comparator: S}
    claim: "protection in persistent drawdowns; time-boxed; no Sharpe claim"
    hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}   # D2 (Quick start); never a literal copy (T-OWNER-01)
    status: SPECIFICATION_BOOK
sleeves:                                 # notional_nav: owner-signed, effective-dated, one value per sleeve (R-26); set before the M7 header commit
  US: {line: none, notional_nav: null}   # line: canonical key of D5 (pending)
  KR: {notional_nav: null}
context_log:
  probit: {alpha: -0.6045, beta: -0.7374, spread: "GS10 - TB3MS (bond-equivalent), monthly"}
  taylor_family: {r_star: [0.5, 1.0, 2.0], gap: [okun_2x, cbo], a: [0.5, 1.0], pi: core_pce_yoy, pi_star: 2.0}
  existing_sheet: {all_items_context_unless_acting: true, zscores: causal_display_only, regime_read: removed_if_regime_model_else_text_only}
  vintages_required: true
  additions: [leverage_and_flow, vrp, live_implied_vol_snapshots, turbulence_and_absorption_ratio]
breaks:                                  # R-18
  policy_trigger: official_framework_change      # shrink macro-conditioned multipliers to 1.0 + start a forward record
  statistical_trigger: log_only                  # active only after the 1990-2026 false-break test
  scale_reanchor: declared_events_only           # v1.2's 2x-3y-median/60-session rule is a logged flag only
  bocpd: {hazard: "1/250", prior: declared, log_only: true, displayed: false}
  market_structure_log: true
monitoring:                                          # R-25
  denominator: whole_book_nav
  operational_triggers: [lag_audit_violation, acting_param_edit_outside_revision, provisional_or_stale_input_reached_acting_decision,
                         switches_gt_p99_poisson_negbin, operator_kill_of_forward_books,
                         decision_gaps_gt_10pct_rolling_12m]          # immediate; outside the budget (§3.8, §8.8 (b))
  catastrophic:
    card_p: {all_of: ["fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5"], window_months: 12}
    card_o: {any_of: ["gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5"]}
  cusum: {frequency: monthly, k: 0.25, h: bootstrap_calibrated, in_control_arl_years_min: 20}
  false_demotion_budget_per_year: 0.10              # canonical key of D4 (owner_decisions.D4, Quick start)
  false_demotion_budget_split: {rule: equal_across_active_cards, fixed_at_record_start: true, recalibrated_on_new_card: false}
  budget_check: {panel: circular_shift, shifts: 20, min_offset_sessions: 252, short_sample: floor_T_over_252_offsets, seed: 11}
  cusum_calibration: {bootstrap: stationary, resamples: 2000, seed: 11, mean_block_months: 12}   # default, judgment
  switch_model: {default: poisson, negbin_if_lr_test_p_lt: 0.05}                                   # default, judgment
  demotion_verdict: {operational_or_integrity: REVISE, catastrophic_or_cusum: REJECT}              # default, judgment
  lockout_scope: family_x_market
  nav_unavailable_ops_halt_after_decisions: 2
  forward_record_can_raise_verdict: false
  regate_up_only_on_new_history: {continuous: new_objective_episode, discrete: tier_onset_count}
  lockout_months_after_demotion: 6
  bull_lag_alone_demotes: false
gate:                                    # the existing nine-step gate plus the frozen v2 package (§8; R-21-R-24, R-34)
  package: {version: "2.0.0", definitions_md5: written_at_freeze, acceptance_report_md5: written_at_freeze, frozen_utc: written_at_freeze,
            manifest: [gate_blocks_canonical_json, harness_source_files, acceptance_fixture_md5s, seeds],
            anchor: repository_commit_before_any_card_run, rehash_at_every_card_run: true}   # §8.1.3; T-CARD-02
  frozen_before_first_card_run: true
  card_classes: [CARD-O, CARD-P]
  card_p_v2:                                         # R-21
    comparator: S_same_average_exposure              # m_bar x overlay-off; constant; same days; uncosted
    pc1_prime: {horizons_sessions: [21, 126], es_level: 0.95, overlapping: true, gate_cost: 1x,
                point_must_exceed: 0.0, p_max: 0.10, p_form: uncentred_bootstrap_percentile, z_printed: true, bootstrap: stationary, mean_block_sessions: 250,
                resamples: 2000, seed: 11, two_x: revise_path, monthly_cards_horizons_months: [1, 6]}
    pc2: {tail_quantile: 0.05, ratio_max: 0.90, default_horizon: daily, ci: printed,
          horizon_matched: {adopt_if_placebo_false_pass_max: 0.10, placebos_per_card: 20, decided_in: acceptance_test}}
    pc3: {delta: 0.10, p_max: 0.10, p_ni: "max(p_block10, p_block_max21_PWpsi)", point_below_minus_delta: {at_1x: REJECT, at_2x: REVISE}}
    pc4: {episodes: objective_market_own, min_positive: 3, max_share: 0.50}
    pc5: {years_positive_min: 0.60}
    pc6: {neighbourhood: moore_8_or_2_axis_neighbours, keep_share_min: 0.50}
    pc6_axes:                                        # frozen per rule type; a card never declares axes or steps (default, judgment)
      vol_target: {window_mult: [0.5, 1, 2], target_mult: [0.75, 1, 1.25]}           # R-06 KR: {10, 20, 40} x {0.15, 0.20, 0.25}
      threshold_rule: {threshold_mult: [0.75, 1, 1.25], lookback_or_dwell_mult: [0.5, 1, 2]}
      monthly_trend_rule: {lookback_months: [8, 10, 12]}                              # one axis, 2 neighbours (QF5)
    pc7: {discrete_min_onsets: 30, decluster_gap: own_lookback, continuous_min_objective_episodes: 5, min_sessions: 882}
    caps: {do_no_harm: INSUFFICIENT_DATA, timing_fragile: INSUFFICIENT_DATA, estimator_calibration_fail: REVISE}   # SMA20: B5; challenger: R-30 Stage 1
    underpowered: {applies_if_mde80_gt: 0.10, converts: [pc3_p_value], never_waives: [pc1_prime, pc2, pc3_point]}
    gjr_null: {paths: 1000, seed: 11, mean: constant}                 # printed only
  acceptance_test:
    placebo: {construction: circular_shift_of_multiplier, per_family: 300, per_family_false_pass_max: 0.10,
              tau_min_sessions: 252, per_card: 20, per_card_passes_max: 2, seed: 11,
              per_card_tau: "round(252 + k*(T - 504)/19), k = 0..19", pass: pc1_prime_both_legs_1x_with_f,
              population: drafted_card_p_headers, family_pooling: own_series_300_per_card, on_excess: acceptance_fails}   # Q5 open (§8.10)
    negative_controls: [US_VT_5d_50bp, US_VT_10d_50bp, post_shock_day_0p5, post_shock_week_0p5, VT_sigma_lag_252]
    controls_allowed_verdicts: [REJECT, INSUFFICIENT_DATA]
    cdar_guard: {added_only_if_a_control_passes: true, calibration: lowest_placebo_false_pass_rule, fixed_margin_minus_5pp: withdrawn}   # calibration: canonical key of D6, frozen with the package (R2-C2)
    attempts_log: {path: gate/acceptance_runs.jsonl, append_only: true, hash_chain: prev_row_md5, listed_in_report: true,
                   counts_as: package_trial, printed_beside_every_verdict: true}   # R2-C3
    redesign: {max_per_package_version: 1, changes_limited_to: frozen_items_table, rationale_cites: [family_panels, negative_controls],
               fresh_seeds_fixed_before_run: true, per_card_excess: council_q5_only, failure_count: across_all_2x_versions_never_reset,
               after_second_failure: no_card_evaluated_under_v2_owner_notified}   # R2-C3; T-GATE-04
  evaluation:                                        # R-22
    episode_rule: {name: alternating_bear_bull, version: "1", prices: own_official_closes,
                   theta: {default: 0.20, KR: 0.20, US_SPX: 0.15}, low_vol_declared: [US_SPX],
                   others: {rule: "0.15 if long-run median SMA20 vol < 0.18 else 0.20", written_before_first_run: true},
                   window: first_return_after_peak_close_to_trough, sep_2026: asserted_not_an_episode}
    shock_type_table: "§8.6 named windows (printed only)"
    post_trough_window_sessions: 63                  # printed, not gated
    cost_episodes: {rebound_2009: ["2009-03-09", "2009-06-30"], rebound_2020: ["2020-03-23", "2020-06-08"],
                    h1_2026: ["2026-01-02", "2026-06-30"]}
    returns: excess
    cash: {KR: BOK_CALL_RATE, US: US_RF, other: registry_before_first_run}
    cash_day_count: act_365                          # default, judgment
    cash_rate_date: latest_rate_dated_on_or_before_previous_session   # R-22 rule 3; a closed day of the rate's own calendar carries the prior rate
    cash_units: {annual_rate: act_365, per_period_return: as_published}   # French RF is a per-period return (R2-C5)
    cash_read: frozen_card_snapshot_available_at_recorded_never_filtered   # role history; a missing cash day refuses the card
    start: first_close_plus_estimator_warmup
    history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}   # fixed before the freeze; a card never truncates it
    span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}
    data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}   # the last official closes in the frozen reference data (§9.3.1), fixed now; in the manifest
    start_band_shapes:                               # frozen; a card declares neither its band nor its pass share
      default: {months: 33, step: month, pass_share_min: "2/3"}
      R-06_KR: {from: "1997-05", to: "1999-12", step: month, starts: 32, pass_share_min: "2/3"}   # Resolution 1
      decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}   # R-29
    stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts,
                      no_reject_in_midpoint_halves: true, applies_to_every_shape: true}
    midpoint_halves: {split: calendar_midpoint_of_fixed_span, split_date_in_header: true}
    regime_lines: from_R20_tags
    primary_oos_line: declare_on_card
    risk_layer_in_card_books: {hard_stop: excluded_printed, caps: excluded_printed, except: card_claim_concerns_them}   # rule 6
  step3:                                             # R-23
    ledger: {required: true, hash: md5_canonical_json, research_phase_included: true, timing_class_required: true,
             family_id: by_rule_QC_modules, filing_cluster_rho: 0.5, appended_by: harness_only, hash_chain: prev_row_md5,
             hash_at: [registration, run]}
    basis: difference_series                         # rule minus comparator (overlay-off for CARD-O, S for CARD-P)
    n_gate: "max(N_clusters, N_equiv)"
    emax: {simulated_draws: 200000, seed: 11, below_2: exact_integral, from_2: bldp_closed_form}
    clusters: {linkage: average, rho_min: 0.5}
    variance: {default: V_null, se_null: median_lw_hac_of_family_trials, use_trials_if_independent_ge: 30, print_both: true}
    card_o_bar: 0.95
    card_p: {gated: false, selection_factor: bonferroni_N_eff, factor_one_if: config_fixed_before_any_run_on_span,
             overlap_rule: any_overlap, computed_by: step3, declared_on_header: refused, print_both: [f_1, f_N_eff],
             holm_across_variants: printed}
    row_set: {unit: distinct_configuration, key: [rule, params, estimator, window, cap, book, rebalance, timing_class, start_convention], readings: [market_scoped, family_wide], combine: max,
              snapshot: ledger_hash_at_registration, excludes: [own_run_rows, null_distribution_runs]}   # R2-C1
    spec_versions: publication_utc_listed_in_manifest   # the f = 1 route (a published SPEC version)
    printed: [N_raw, N_hat_linear_eq9, N_clusters, N_equiv, N_eff, break_even_N, z_check_one_sided_2p50_le_8_cells, by_q_global, dsr_vs0, psr_vs_S]
    forbidden: [kish_design_effect, revision_count_as_N]
  stats:                                             # R-24
    bootstrap: {method: ledoit_wolf_studentized_circular_block, null_centred: true, resamples: 2000, seed: 11,
                p_zero_print: "< 1/B", hac_p_printed: true}
    block: {rule: politis_white_on_influence_function, floor_sessions: 21, pc3_also_block_10: true}
    se_ladder_blocks: [10, 21, 63, 126, 250]         # SE_plateau = max (incl. LW-HAC)
    power: {alpha_one_sided: 0.10, power: 0.80, mde_factor: 2.1232, deltas: [0.05, 0.10], t_years: sessions_over_252, se: se_plateau}
    underpowered: {mde80_gt: 0.10, converts: [step5_p_value, pc3_p_value]}
    multiplicity: {p_source: analytic_hac_lw, bootstrap_resamples_if_used: "20*M/alpha", by_q_from_global_ledger: true,
                   one_sided_z: {le_8_cells: 2.50, bonferroni_120: 3.34}}
    pbo: {configs: ledger_union_frozen_pc6_grid, min_configs: 10, cscv_blocks: 16,
          objective: {CARD_O: paired_dSR_vs_off, CARD_P: blockwise_dES95_21}, winner_loses_share_gt: 0.10,
          reject_if: "PBO > 0.2 and winner_loses", null_calibration: printed}
    lo_adjusted_sr: {lags: [20, all], printed: true, gated: false}
    live_sharpe_multiplier: 0.60                     # take 40% off; HL haircut printed beside it
  timing:                                            # R-34
    lags_sessions: [-1, 0, 1, 2, 3]
    plus_publication_strict: true
    honest_lag: 1
    fragility_ratio_max: 0.5                         # declared once, before any card runs
    sign_flip_by_lag: 2
    consequence: {verdict_cap: INSUFFICIENT_DATA, tier_cap: B, require_live_timestamped_feed: true}
    positive_control: {fixture: KR_SOX_KRW_gate_B3, contents: R4_B3_inputs_and_rule, look_ahead_premium_min: 0.20}   # observed 0.28
    every_lag_in_family_ledger: true
    lookahead_rows: {mode: timing_probe, scope: [tests, r34_sandbox], tag: synthetic_lookahead, ledger_timing_class: NON-COMPLIANT,
                     production_writes: forbidden}
  tiers: {A: {min_onsets_declustered: 30, decluster_gap: own_lookback, min_stress_episodes_in_sample: 3, min_oos_episodes: 1,
              pooled_rule: declare_before_any_market_is_run},
          A_provisional: closed,          # BL-C12 resolved; no pooled or A-provisional route for a card already run
          B: {bounds: [0.5, 1.0], external_params: true, verdict_from_backtest: INSUFFICIENT_DATA, forward_record: falsification_only},
          C: {allowed: false}}
  parameter_budget_searched: 8
  stress_report_window: ["2022-01-01", "2026-10-02"]      # reported, not a holdout
  locked_holdout_start: "2027-01-01"
  costs: read_from_gate                  # KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; x2 stress
  card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version,
                         family_id, ledger_hash_at_registration, history_first_close, data_span]   # start_band, midpoint_halves: acting long-sample cards (R-22)
  card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]          # §6.5
do_not_build:                            # R-33; §10. Validation refuses a matching entry, card header or book configuration (T-DNB-01)
  labels: [harm, null, inconclusive]
  basis: {B: qf3_bootstrap_class_or_share_lt_0.05, E: item_evidence_provisional, G: breaks_P0_P19_or_red_line}
  items:                                 # one label per item, or per variant where they differ (§10.2)
    1: inconclusive_B
    2: harm_B
    3: inconclusive_B
    4: harm_E
    5: inconclusive_B
    6: {curve_resteepening: harm_B, real_rate: null_B, credit_weights: inconclusive_B, mom_under_rates_stress: inconclusive_E, level_thresholds: inconclusive_E}
    7: null_E
    8: inconclusive_B
    9: {forecasts_surveys_positioning: inconclusive_E, crowding_cuts: inconclusive_E, consensus_surprise_entries: null_E}
    10: inconclusive_E
    11: {11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, smoothed_regime_probabilities: harm_G,
         unpenalised_hmm_ms_gates: harm_E, complexity_rff_timing: null_E, llm_text_pre_cutoff_backtests: harm_G}
    12: {event_blackouts_24h_and_swing: inconclusive_E, quad_witching_blackout: null_E, expiry_close_fade: inconclusive_E}
    13: inconclusive_E
    14: {rate_differential_models: null_E, foreign_flow_rules: inconclusive_E}
    15: inconclusive_E
    16: inconclusive_E
    17: inconclusive_E
    18: harm_G
    19: harm_G
    20: inconclusive_E
    21: harm_G
    22: harm_G
    23: harm_G
    24: harm_G
    25: harm_G
    26: harm_G
    27: {jump_model: inconclusive_E, markov_switching: harm_E, gmm_and_change_point_states: inconclusive_E, prohibition: binding_red_line_E1}
    28: null_E
    29: harm_E
    30: harm_B
    31: harm_G
    32: harm_G
    33: harm_G
    34: harm_G
    35: harm_G
    36: harm_G
    37: inconclusive_E
  refused_shapes:                        # §10.3
    order_path_or_broker_adapter: 21
    multiplier_weight_or_cap_above_1: [2, 8]
    composition_not_min: 31
    regime_model_source_acting_or_displayed: [11, 24, 27]
    smoothed_or_forward_looking_label: 24
    ml_classifier_estimator_gate_or_label: [11, 29]
    conformal_label_layer: 28
    sizing_estimator_max_over_implied: 30
    estimator_change_outside_r30_revision: 25
    header_edit_after_results_md5: [23, 32]   # instrument_book, notional_nav, rebalance, no_trade_band, cost_bp
    krx_stock_book_on_market_gross_scalar: 33
    pooled_or_a_provisional_tier_after_results: 34
    forward_record_cited_as_validation: 35
    kish_or_other_n_eff_rule: 36
    r28_instance_market_kr: 37
    recommended_book_reads_non_pass_multiplier: 22
    value_timed_or_provisional_acting_input: [19, 26]
reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002,
                  record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5,
                           ledger_hash_at_registration, ledger_hash_at_run],
                  determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash],
                                rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}   # T-REPRO-01a/b/c
```

### C3. Owner decisions D1–D6 — canonical table, VERBATIM (L67–L74)

| ID | Decision | Default implemented in v2.0 | Rules-store key |
|---|---|---|---|
| D1 | Korea concentration template (risk appetite) | **MSCI 25/50**: single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; checked quarterly and on breach. Options: (a) domestic max(10%, market weight); (c) a 35% pair cap without the 0.45 trigger | `risk_layer.korea_caps.template` |
| D2 | Drawdown hard-stop level (risk appetite) | **−15% of book NAV** from the high-water mark since the last re-arm. Option (b): −1.5 σ_book | `risk_layer.drawdown.hard_stop.level` |
| D3 | Calm-state reversal down-weight, QF5-M10 (principle change) | **Not adopted: P3 stands** (council recommendation). Reopen only after the KRX net test in 2010–17 and 2018–26 | `families.reversal.calm_state_downweight` |
| D4 | Book-level false-demotion budget (risk appetite) | **≤ 10% a year** across all statistical demotion triggers, split equally across active cards, each split verified on a 20-shift placebo panel | `monitoring.false_demotion_budget_per_year` |
| D5 | Whether, and on which line, to run a US sleeve (product choice) | **No US sleeve until decided**: R-28 and R-29 stay FORWARD-SIM and never enter the recommended book. Options: index futures (Micro ES, notional ≈ ₩1bn or more); a KRX-listed S&P ETF line with FX and NAV lag modelled; no US sleeve. Scope: D5 governs the US market-gross line (R-06 US, R-28, R-29); QUANTGEN's existing factor sleeves on US shares (R-03's momentum sleeve) are not a US sleeve in D5's sense | `sleeves.US.line` |
| D6 | CDaR-guard calibration (applied only if a negative control passes the acceptance test; Resolution 4's one open sub-point) | **Frozen with the package now (R2-C2): the lowest-placebo-false-pass rule.** If a negative control passes, the guard is calibrated by the one of the three council candidates (the Professors' bootstrap test at one-sided 5%, the Executives' placebo-10th-percentile margin, QF's blind margin) with the lowest per-family placebo false-pass rate among those that bring every negative control to REJECT or INSUFFICIENT DATA; ties go to the Professors' test (default, judgment; placebo results only, never a card's numbers). If no candidate does, the attempt fails (R-21 9(a)). An owner ruling naming one candidate is accepted only before the first acceptance attempt; any later change is a new package version and a counted trial | `gate.acceptance_test.cdar_guard.calibration` |

Registry state at v2.0.0 (from C2): D1 `msci_25_50` (default); D2 `-0.15` (default; refs `cards.R-31_step_down.hard_stop_level`); D3 `not_adopted` (default); D4 `0.10` (default); D5 `none` (**pending**; refs `instruments.us_line_choice`, `cards.R-28_trend_axis.us_sleeve`, `cards.R-29_US_FUT.us_sleeve_and_line`); D6 `lowest_placebo_false_pass_rule` (default).

### C4. `do_not_build` labels (L4621–L4661, L6052–L6062)

- Labels: `harm`, `null`, `inconclusive`. Bases: `B: qf3_bootstrap_class_or_share_lt_0.05`, `E: item_evidence_provisional`, `G: breaks_P0_P19_or_red_line`.
- Counts in §7 (script): `harm_G` 16, `inconclusive_E` 16, `null_E` 6, `harm_E` 5, `inconclusive_B` 5, `harm_B` 3, `null_B` 1, plus `admitted` (11b) and `binding_red_line_E1` (27.prohibition). The §7 labels agree with the §10.2 text item by item (checked 1–37).
- Item 11 split (L6118–L6125): 11a ML vol-state classifiers prohibited; 11b range-based log-HAR admitted; 11c the other shortcuts labelled by variant.
- §10.4 "Not on this list" (L6256–L6260): log-HAR and COMB (R-30); the R-06 σ̂ display labels; the BOCPD probability (research log only); the KOSPI trend state as context; D3 is an owner decision, not a prohibition.

### C5. Status strings and enums this area reads or writes

| Set | Values | Source |
|---|---|---|
| Rule `kind` | `INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE` | L4693 |
| Books (rule object) | `recommended, specification, forward_sim, refusal` | L4698 |
| `overlay.books` | `recommended, specification, forward_sim_per_card, refusal_display_only` | L4278 |
| Book ids | `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on\|off\|S>` | L3609 |
| Owner-decision `status` | `default, owner_set, pending` | L4138 |
| Verdicts | `PASS, REVISE, REJECT, INSUFFICIENT_DATA` (+ `NOT_RUN` on a card reference) | L4007, L3759 |
| Dispositions | `RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP, SPECIFICATION_ONLY, FORWARD_SIM, REFUSAL_BOOK, DESCRIPTIVE` | L4012 |
| `build_status_on_pass` | `BUILD_NOW, BUILD_AS_INSURANCE` | L3939 |
| Card `status` in §7 | `FORWARD_SIM` (R-28, R-29), `SPECIFICATION_BOOK` (R-31) | L4424, L4447, L4461 |
| Verdict reason codes | `sufficiency, inconclusive, underpowered, do_no_harm, timing_fragile, stability, claim_not_shown, estimator_calibration`, or the failed check's id | L4779 |
| Governance `kind`, `actor` | B4 | L4104–L4108 |
| `costs_per_side` | `{table_bp, floor_bp, applied_bp, stress_line, roll_cost_line}` | L2854, L4046–L4048 |
| `overlay_decision.extras` (R-26) | `{instrument_book, contracts, w_target, w_held, band}` | L2856 |

### C6. Rule objects to seed in `rules` (PROPOSED derivation; the spec lists no rule objects)

Ids marked † are verbatim from the spec's examples; the rest are this brief's names. Every card rule starts without `recommended` in `books` (no card has run; row 16).

| `rule_id` | kind | factor | `output_range` | basis | `applies_to` | books | market | `instrument_book` | `card_id` | §7 block |
|---|---|---|---|---|---|---|---|---|---|---|
| `R-06-KR-VT20` † (L4903) | CARD-P | vt | [0.0, 1.0] | total | market_gross | [specification] | KR | KRX_ETF_line | `MACRO-R06-KR-ETF` † | `vol_target.KR` |
| `R-29-US-FUT` | CARD-P | vt | [0.0, 1.0] | total | market_gross | [forward_sim] | US | CME_micro_ES | `MACRO-R06-US-FUT` † | `cards.R-29_US_FUT` |
| `R-28-US-TREND` | CARD-P | overlay | [0.5, 1.0] | total | market_gross | [forward_sim] | US | CME_micro_ES | `MACRO-R28-US-TREND` † (L4824) | `cards.R-28_trend_axis` |
| `R-31-KR-STEPS` | CARD-P | ladder | [0.5, 1.0] | total | market_gross | [specification] | KR | KRX_ETF_line (from the card id) | `MACRO-R31-KR-ETF` † (L4824) | `cards.R-31_step_down` |
| `R-03-US-VS` | CARD-O | vs | [0.0, 1.0] | active | momentum | [specification] | US | US_shares_KIS (L4823) | `MACRO-R03-US-MOM` † | `families.momentum.own_vol_scale` |
| `R-04-DM` † (L3781) | CARD-O | overlay | [0.5, 1.0] | active | momentum | [specification] | US | — | `MACRO-R04-US-DM` † (L3782) | `families.momentum.dm_gate` |
| `R-11-S1` | CARD-P | overlay | [0.75, 1.0] | total | market_gross | [refusal] | KR | — | not named in the spec | `refusal_books.S1_krw` |
| `R-12-S2` † (L3798) | CARD-P | overlay | [0.5, 1.0] | total | market_gross | [refusal] | US | — | `MACRO-R12-US-RATES` † | `refusal_books.S2_rates` |

Not rule objects: `vol_target.US.registered_card` (a recorded REJECT, "They cannot act", L2824; as an object it would trip row 11 under A-10); `families.ts_trend` (R-14: a sleeve, exempt from overlays; card `MACRO-R14-MULTI-TREND`, `multi_line`); `families.{reversal,quality,flow}` (fixed 1.0, convention).

## D. Tests

All M0 tests of this area are **SYNTH** (inline values, temporary directories). Statements appear twice for T-COST-02, T-COST-03 and T-BOOK-01 (rule table and §9.1); "Both statements must pass; the rule's table carries the detail" (L5601).

| Test | `runs_from` | Exact assertion | Fixture | Class |
|---|---|---|---|---|
| T-RO-01 (L5605) | M0 | The static scan of B7 finds no order, cancel, withdrawal, deposit-address or transfer call and no import of an order-submission client; `core/engine/orders` is reached only through the simulated order book API; every artifact has `read_only: true`. Negative case: a temp `.py` with `import ccxt` or `"/uapi/domestic-stock/v1/trading/order-cash"` makes the scan function return a hit | repo source tree; temp file | SYNTH |
| T-HERM-01 (L5607) | M0 | The macro suite passes with all network touchpoints patched to raise; inside the guard a socket connect raises; the suite reads manifest-listed, md5-verified fixtures only (an unlisted file in `tests/fixtures/macro/` fails) | none | SYNTH |
| T-HERM-02 (L5608) | M0 | After `tests/run_all.py`, `core/rules` and every family ledger are byte-identical to their pre-run state; tests write only to temporary copies of the rules store, the ledgers and the artifact directory | pre/post md5 map | SYNTH |
| T-CAP-01 (L5626; L5513, L5646) | M0; "The overlay layer cannot emit 0." joins at M2 (L5570) | Rules-store side: an overlay rule object with `output_range` `[0.49, 1.0]`, `[0.5, 1.01]` → refused, items 2, 8; `[0.5, 1.0]` accepted. vt or vs with `hi = 1.01` or `lo < 0` → refused; `[0.0, 1.0]` accepted. A store copy with `vol_target.KR.cap = 1.5`, `overlay.cap = 1.2` or `overlay.floor = 0.4` fails `validate_store`. The shipped store passes ("Every stored block passes bounds validation", task M0-05). Schema side (schema brief): `overlay_decision.multipliers[].value` min 0.5 max 1.0, `vol_scale` min 0 max 1 (L3732–L3744) | synthetic rule objects; temp store | SYNTH |
| T-BASIS-01 (L5628) | M0 as the rules-store predicate on `applies_to`; runtime M4 (L/S sleeves) and M7 (R-14) (L5569); S2 clause M8 | "Every multiplier has `exposure_basis`": an object with `output_range` and no `exposure_basis` → refused. A `factor: vt` rule with `applies_to: momentum` (anything but `market_gross`) → refused. Any multiplier with `applies_to: ts_trend` → refused. Every C6 seed object passes | synthetic rule objects | SYNTH |
| T-OWNER-01 (L5672) | M0, including "the ruling is written to `governance_events.jsonl`" (L5571) | (i) each D1–D6 canonical key exists and holds a scalar equal to `owner_decisions.D<n>.value`; (ii) every `{ref: …}` resolves to it (7 refs; the D2 and D5 refs resolve to `-0.15` and `"none"`); (iii) `rule_on("D2", "-1.5*sigma_book", …)` flips `status` to `owner_set`, `cards.R-31_step_down.hard_stop_level` resolves to the new value, one valid hash-chained event of kind `owner_ruling` is appended (first line: `prev_row_md5` null) and `verify_chain` passes; (iv) a temp store whose `cards.R-31_step_down.hard_stop_level` is the literal `-0.20` → refused at load; (v) `{ref: k, other: 1}` → refused at load; (vi) a header whose `owner_decisions` equals the store at commit passes; after a later ruling the committed header is not re-checked; (vii) D4 `0.20` → refused; D5 `"IBKR"` → refused | temp store, temp jsonl | SYNTH |
| T-COST-02 (L2869, L5639) | M0 | `cost_per_side(252670, date in 2026, 69, "buy")["applied_bp"] ≥ 72` and equals 73.9 within 0.05 (73.86 with the 1.4 bp commission). `cost_per_side(KODEX 200, 112060)` → `applied_bp == 3.0`, `floor_bp` ≈ 1.6 (1.62). Property: `applied_bp ≥ table_bp` for seeded random prices and classes ("The floor never lowers a table rate") | inline | SYNTH |
| T-COST-03 (L2870, L5640) | M0 | "Lowering a cost in a card header raises": `costs.per_side: 2.0`, `stress: 1.0`, `floor: "none"`, or a `KRX_stock_book` header with `schedule: [{cost_class: krx_etf}]` → raises. "The stress line can only raise a cost": `stress_cost_line(c, σ20, σmed, …) ≥ c` for σ20/σmed in {0.2, 1, 3, 9} (clip to [1, 5]); + 10 bp on an ETF-line close fill with `abs_ret ≥ 0.03` | inline | SYNTH |
| T-BOOK-01 (L2871, L5641) | M0 header clauses; "Every card prints execution variants A/B/C and the overnight/intraday attribution" joins at M7 (L5550) | With a temp store where `sleeves.KR.notional_nav = 1.0e8`: (a) a header missing each of `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav` in turn → refused; (b) `mini_KOSPI200_futures` (₩56m) on the ₩0.1bn sleeve → refused; with the sleeve at `1.12e9` (exactly 5%) → allowed; at `1.119e9` → refused; (c) `notional_nav` ≠ `sleeves.KR.notional_nav` at commit → refused; a `null` sleeve notional → refused; (d) `KRX_stock_book` on a rule with `exposure_basis: total` → refused; (e) `no_trade_band: 0.10` on `KRX_ETF_line` → refused, on `KRX_stock_book` → allowed | synthetic headers; temp store | SYNTH |
| T-DNB-01 (L3391, L5682) | M0 | Item 11 is split (keys `11a…`, `11b_range_log_har: admitted`). Each of (a)–(g), "submitted as a §7.1 rule object, is refused by `core/rules` validation with the §10 item number in the error": (a) input `source_kind: regime_model` with role `acting_exposure`, and again with role `context` → 27; (b) `label_layer: conformal` → 28; (c) `estimator: {name: gbm, kind: ml}` → 29 / 11a; (d) vt rule, estimator max over an `implied_vol` input → 30; (e) `composition: product` → 31; (f) stored object with `results_md5` set, then `instrument_book` changed under the same `card_id` → 32 / 23; (g) `KRX_stock_book` + `applies_to: market_gross` → 33. Each error names the item and its label; each refusal adds one `refusal` history entry and leaves `config_hash` unchanged. Every item 1–37 carries a label (B3.5). The other ten shapes get one case each (rows 1, 5, 9, 12–17, and 2 via T-CAP-01) | synthetic rule objects; temp store | SYNTH |
| T-REPRO-01a (L5666) | M0 | "Every artifact and card records the seed, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, the ledger hashes and `results_md5`" — read per A-17. `config_hash` is stable across reloads and changes after an owner ruling; `canonical_json` is byte-stable (key order, float repr) | synthetic artifact and card | SYNTH (git_hash: B-1) |
| T-SCHEMA-01, the §6.6 clause (task M0-07) | M0 | The VERBATIM example line of B4 validates against `quantgen/governance_event.v2.0` after typed samples replace `<uuid>` and `<md5>`; a missing required key fails; an undeclared key fails | inline | SYNTH (needs the schema registry; F4) |

Related tests that land later but bind code written now:

| Test | `runs_from` | What M0 code it will exercise |
|---|---|---|
| T-RO-02 (L5606) | M1; I-01 clause M8 | KIS quotation allowlist frozen in `config.py`; B7 rule 3 is its static precursor |
| T-CAP-02 (L5627) | M2; stack-card clause M7 | "the rules store refuses `combine ≠ min`" (L881) → B3.3 / row 3 |
| T-COST-01 (L5638) | M2; "both legs" M4; "a 2× run exists for every card" M7 | "Changing the rate in a card header raises" → B5; reads `COST_BPS_PER_SIDE`. Goldens (KOSPI VT20 at 35 bp SR 0.609 ± 0.01; US VT15 at 50 bp SR 0.505 ± 0.01) are REFDATA |
| T-SER-02 (L5630) | M1 | every series id in the store and `data_contracts.roles` exists in the registry |
| T-PRIOR-01 (L5648) | M4 | "A tilt without a PASSed family card is refused by rules-store validation" → `base_weights.tilt_requires_family_card_pass: true`; a new predicate at M4 |
| T-BOOK-03 (L2873) | M5 | "A product whose tick exceeds 10 bp of its price is ineligible. Look-through counts × L in R-07." → `tick_size`, `Instrument.leverage` |
| T-B5-01, I-10 (L5642, L5700) | M3; counted-revision clause M7 | "An estimator switch without a counted revision is refused" → row 9 |
| T-BOOK-02 (L2872) | M7, after the freeze | printed lines; KOSPI VT20, 3 bp, 1997–2026: SR 0.448 / 0.450 / 0.465 (± 0.01) — REFDATA (KRX official closes from 1997; no local file) |
| T-CARD-01 (L5663) | M7 | "A card without a ledger hash or the R-26 header fields is refused" → B6 |
| T-R06-US-01 (L5646), T-R04-01 (L5645) | M7 | "Any vt > 1.0 fails validation"; "Card validation rejects any A-provisional or pooled route for a card already run" → rows 2, 12 |
| I-03 (L5690) | M8 | recommended book never reads a non-PASS factor → row 16 at run time |
| T-OBS-05 (L5681) | M8 | `verify_chain` at app start; a hand-edited row raises GOVERNANCE_LOG_BROKEN (page) |
| T-FX-01 (L5658) | M10 | an FX sleeve card without a declared instrument (`FX_KRX_USD_futures` or `FX_broker_spot`) is refused → B6 check 2 |

Feasibility of TASK-M0-15: **REFDATA**, no local substitute (B10). Owner inputs that M0 tests replace by synthetic values: `sleeves.<market>.notional_nav` (**OWNER**, needed before the M7 header commit, L76 (3)); the commission rate (**OWNER** confirms 1.4 bp, L2797); the ETF tick table before 2023-12-11 (**OWNER**, KRX notices, L76 (1)).

## E. Interfaces

**Needs (M0 is the first milestone).** From the schema brief, inside M0: the schema registry (`quantgen/governance_event.v2.0`, `model_card_header.macro.v2.0`) for T-SCHEMA-01 and B6; the artifact writer, which imports `canonical_json`, `md5_hex` and `MacroStore.config_hash` from `core/rules/macro_store.py` (dependency direction `core/ficc → core/rules`, never the reverse).

**Exposes to later milestones.**

| Name | Shape | First consumer |
|---|---|---|
| `load(path) -> MacroStore`; `.get(dotted)`, `.resolved()`, `.config_hash()`, `.history()` | B2 | every milestone reads its parameters here and "never invents them" (task M0-05) |
| `validate_rule_object`, `validate_rule_edit`, `validate_store` | B3 | M2 (compose), M3 (estimator switch), M4 (tilt predicate), M7 (cards), M8 (book builder) |
| `validate_card_header(header, store, …)` | B6 | M7 header commits (§8.1.3 step 4, L4821–L4826) |
| `append_event`, `verify_chain` | B4 | M1 (OPS HALT / re-arm / book_state events), M5 (RISK), M7 (`package_freeze`, `header_commit`), M8 (`demotion`, `verdict_integrity`; app-start verification) |
| `rule_on`, `set_sleeve_notional` | B2 | Macro page owner-decision panel (L761–L763); M7 notional sign-off |
| `COST_BPS_PER_SIDE`, `table_rate`, `tick_size`, `cost_per_side`, `stress_cost_line`, `check_cost_policy` | B5 | M2 (T-COST-01), M5 (fill model, T-BOOK-03), M7 (cards, printed lines) |
| `Instrument` table | B5 | M5 (R-07 look-through × L), M7 |
| `canonical_json`, `md5_hex` | B2 | artifact writer (M0), family ledger hash `md5_canonical_json` (L4566, M7), package manifest (L4820, M7), verdict chain (M8) |
| `config.macro_artifact_dir()`, `config.macro_rules_path()` | B1 | all |
| Test registry (`tier`, `runs_from`, clauses), `_no_network()`, `fixture()` | B8 | every later test |
| History entry kinds (`acting_param_edit` with `revision: null`) | B2 | R-25 demotion trigger, M8 (L4479) |

Store blocks by first reader: M1 `time`, `calendars`, `data`, `data_contracts`; M2 `overlay`, `vol_target` (KR, US, `sigma`, `warmup`, `display_labels`), `risk_layer.hedge_state`; M3 `vol_target.estimator_gate`; M4 `families`, `base_weights`, `prior_haircuts`; M5 `risk_layer` (caps, `drawdown.hard_stop`, `halted_triggers`, `heartbeat`, `ops_rearm`), `annotations`, `events`, `fill_model`; M6 `context_log`, `breaks`; M7 `gate.*`, `cards.R-31_step_down`, `instruments.printed_lines`, `reproducibility`; M8 `monitoring`, `cards.R-28_trend_axis`, `cards.R-29_US_FUT`, `refusal_books`; M10 `time.markets.CRYPTO`.

**Tech-fund programme touchpoints on this store** (`R3_TF_neural_link.md`, §13 L1283–L1310; owned by the tech-fund briefs, listed so the store can accept them as logged revisions rather than silent edits):
- XS-05 (L1293, Correction): replace `prior_haircuts` (L4329) by one haircut per stage (0.5 in sample, 0.3 post-publication, 0.75 drift-like).
- XS-11 (L1299, Tightening): `max(10, Politis-White on d and d^2)` for steps 2 and 5 — conflicts with `gate.stats.block: {rule: politis_white_on_influence_function, floor_sessions: 21}` (L4586) and with the spec's withdrawal of PW(d²) (L4991).
- XS-19 (L1307, Proposal): add DNB-TF-01..17 to the DO-NOT-BUILD list; `do_not_build.items` is keyed `"1"…"37"`, so tech-fund items need their own namespace (for example a sibling map), not renumbering.
- XS-21 (L1309): `base_weight = w / 3` vs `base_weights.family.weight: one_over_K` (L4283).
- G-21 / GOV-7 (L818, L174): itemised cost header (commission, date-varying sell tax, half-tick floor, sqrt impact) and a break-even pre-gate screen; the macro floor has no impact term.
Conservative reading for M0: write §7 verbatim as v2.0.0; apply none of these without an owner ruling; each later change is a logged revision.

## F. Ambiguities, contradictions and conservative readings

| # | Issue | Lines | Conservative reading used |
|---|---|---|---|
| A-1 | Where the macro store file lives. "one JSON file with edit history" in `core/rules` (L380); "the trading directory for the rules JSON" (L4126); T-HERM-02 says "`core/rules` … byte-identical" (L5608); the freeze writes `gate.package` to the store and commits it to the repository (L4820) | L380, L4126, L4820, L5608 | A separate file `core/rules/macro_rules.json`, tracked with the source (so the freeze can anchor it and T-HERM-02's wording holds literally), path overridable by env. The operator's `~/.nextgen/trading/rules.json` is untouched (F1). The alternative in `spec_constitution.md` (shipped default + runtime copy under `config.trading_dir()`) keeps owner rulings out of the source tree but needs a second file and a seeding step, and the freeze must then anchor the runtime copy; the coordinator picks one (F13) |
| A-2 | A literal copy equal to its canonical key: "never a literal copy; a literal copy that differs is refused" | L65, L4130 | Refuse any non-ref at a path listed in `D.refs`, equal or not |
| A-3 | §7.1 has no field telling an overlay from vt/vs, yet the bound depends on it | L4694 | Add `factor` (B3.1); refuse an object with `output_range` and no `factor` |
| A-4 | `exposure_basis` vs `applies_to` consistency is implied, not stated as a predicate | L865, L870, L568–L570 | Enforce `market_gross ⇔ total`, family ⇔ `active`; coordinator may drop it |
| A-5 | "It is logged in the store's edit history, and nothing is written" — a logged refusal is a write to the file | L6231 | The refused entry is not written; the refusal is logged; `config_hash` excludes `history` |
| A-6 | Directory of `governance_events.jsonl` is not given (`gate/…` and `cards/…` are relative paths too) | L4096, L1250, L4531, L4827 | `<macro_artifact_dir>/governance_events.jsonl`; M7 decides which logs must also be committed |
| A-7 | "Acting parameter" is never enumerated for the store, but R-25 demotes on its edit; L381 says such a parameter "may change only through a new card revision", L4894 says an edit outside a revision "demotes the card" | L381, L4128, L4894, L4479 | The store records the edit with `revision: null`; R-25 (M8) demotes. Every path is acting unless edited through `rule_on`, `set_sleeve_notional`, the package freeze or a label update |
| A-8 | May the owner confirm a commission **below** 1.4 bp? "the owner confirms it against the broker schedule"; "Lowering a pre-registered cost is never a permitted change" | L2797, L382 | Lowering `instruments.cost_floor.commission_bp` is refused; raising is a logged edit |
| A-9 | No §7.1 field encodes a "smoothed or forward-looking label" | L4699, L6238 | Row 5 of B3.4; plus the block check on `vol_target.display_labels` |
| A-10 | §10.3 names only `KRX_stock_book`; R-26 rule 5 and `us_shares_50bp: single_names_only` extend the ban to US shares used as a market scalar | L6244, L2822, L4404 | Refuse both books on a `total` / `market_gross` rule. The recorded US 50 bp REJECT stays a labelled record, not a rule object |
| A-11 | The "evidence field" of shape 35 is defined nowhere (not in §6.5, not in §7.1) | L6246, L4705 | Refuse any `evidence` / `validation` value that names a `forward_sim:` book or a forward record |
| A-12 | Tick tables for stocks, futures, US shares and crypto, the ETF tick before 2023-12-11, and sell-tax rates outside 2026 are not in the spec | L2803, L2798, L2786 | Ship only the given rows; `tick_size` raises `NotTradable` elsewhere; class-only costs use the table rate |
| A-13 | Scope of "the whole repository, including `core/skills` scripts and the commands of every workflow YAML": the skill scripts and workflow YAMLs live in an external repository today | L5605; `config.py:50-58` | Scan this repository only; when `macro_daily.yaml` is added (M8) it is scanned, and it may reference only `macro.*` skills |
| A-14 | Cost class of `FX_KRX_USD_futures`: futures (5 bp) or FX (10 bp) | L582–L589, L2808 | The higher rate (10 bp) until the R-17 card declares it (M10) |
| A-15 | The header schema has no `market` and no `exposure_basis`, but `sleeves.<market>.notional_nav` and the stock-book check need them; the notional of a `multi_line` card (R-14) is not defined | L3929–L3933, L2811, L2808 | Read both from the §7.1 rule object named by `header.rule_id`; refuse when it is missing. `multi_line` notional: undefined — refuse at M0 and settle at M7 (T-R14-01) |
| A-16 | No tier is assigned per test id | L5496 | `T-*` → `fast`; `G-*` and fixture-reading `I-*` → `golden`; I-08, the formal runs of I-07 and I-16, GJR-null paths and PBO → `freeze` |
| A-17 | T-REPRO-01a says every artifact records the seed, ledger hashes and `results_md5`, but the closed artifact schemas (`macro_state`, `overlay_decision`) declare none of them | L5666, L3508, L3720–L3723 | Artifacts: the §6 common set. Cards: the full `reproducibility.record` list |
| A-18 | Two conventions for owner-decision markers: an `owner_decision: D<n>` key inside rule blocks vs the registry with `{ref}`; §7 contains no such marker key | L1807, L6260 vs L65, L4130 | The registry governs (the Quick start table is canonical, C-8). No `owner_decision` key is written into blocks |
| A-19 | Granularity check "evaluated at the header commit (price × the effective-dated multiplier × `nav_fx`)" while the store constants are `as_of 2026-10-02`, `use: header_check_only`; multipliers are not given | L2816, L4402 | Parameter `contract_notional_krw`; default = the store constant; the caller passes a point-in-time value once M5/M7 can compute it |
| A-20 | `definitions_md5` covers "the canonical JSON of every `gate.*` block", and `gate.package` (which holds `definitions_md5`) is itself a `gate.*` block | L4820, L4499 | M7 issue; hash the `gate` block with `gate.package` excluded, and say so in the manifest |
| A-21 | D1/D2 ruling timing (notice period, effect while HALTED) is an open owner question | L5462 | `effective_from` is recorded; the ruling applies from the next decision; no special-casing at M0 |
| A-22 | §3.1 diagram says "owner decisions D1–D5" on the Macro page; the registry has D1–D6 | L762 vs L74 | Six decisions |
| A-23 | `T-BOOK-01` in §9.0 (council wording) says "5% of declared notional"; the rule table says "sleeve notional" | L5533 vs L2871 | The rule table governs (L5505: the refined row governs) |

## G. DO-NOT-BUILD items and invariants that bind this area

- **P0 / item 21 (L491–L500, L6162).** No order, cancel, withdrawal, deposit-address or transfer path, no broker adapter, "even behind a flag". Store root `read_only: true`; "nothing here can enable one" (L4137). T-RO-01 on every change.
- **P2 / items 2, 8 (L508–L517, L6077).** Overlays in `[0.5, 1.0]`; vt and vs in `[0, 1.0]`; nothing above 1.0 anywhere; cap 1.0 permanent; 0× only from the risk layer and HALTED; Tier C refused by the store.
- **Item 31 (L6206–L6210).** Composition is `min`, never a product; the store refuses `combine ≠ min`.
- **P8 (L568–L570).** Every multiplier declares `exposure_basis ∈ {active, total}`; vt only on `market_gross`; nothing on `ts_trend`.
- **P10 / items 23, 32 (L579–L602, L6170–L6174, L6211).** Rates are read from the gate's table, never redefined, never lowered; the floor only raises; every result also at 2×; book, notional, rebalance and band are header fields fixed before the run; a different book is a new card.
- **P15 / item 33 (L630–L633, L6212–L6215).** No stock book as a market-gross scalar.
- **P13 / item 36 (L620–L622, L6223).** `n_rule` is `max(N_clusters, N_equiv)`; Kish is never computed and never a field (L4092).
- **P7 / item 22 (L556–L565, L6163–L6167).** The recommended book reads PASS factors only (plus R-31 `INVARIANT_STEP`).
- **P19 / items 27, 11, 24, 28, 29, 30.** No regime-model state acting or displayed; no ML classifier; no conformal layer; no `max(SMA20, implied)`; display labels are causal volatility labels and never gates.
- **Items 25, 34, 35, 37.** Estimator change only as an R-30 counted revision; no pooled or A-provisional route after results; a forward record never validates; no R-28 instance in Korea.
- **No financial defaults (L375, L4127).** Every number explicit; a missing key raises; nothing is filled in.
- **Owner decisions (L65).** One canonical scalar key each; blocks hold `{ref}`; a ruling is a governance event, never a demotion, never a package change.
- **Hermetic tests (L5491–L5495).** No provider reached; no production state written.
- **Reference mode (L5992).** Refused configurations (a cap above 1, product stacks, the literal v1.2 ladder) may be computed only from `tests/reference/` or `docs/` with `reference_only=True`; "`core/` cannot import that code"; T-CAP-01 and T-DNB-01 "apply to the rules store and the books, not to this mode".
- **A label never lifts a prohibition (L6066).** An item reopens only through a new card with new evidence; a G item only by an owner change of principle (L6067).

## Blockers for the coordinator

| # | Blocker | Lines |
|---|---|---|
| B-1 | No git repository: `git_hash` has no source and the M7 freeze has no commit anchor. Conservative: the writer stamps `git rev-parse HEAD` when a repo exists, otherwise a labelled content hash of the source tree (`tree-md5:<md5>`); formal card runs (M7) refuse without a real commit or external timestamped anchor (L4820). Owner action: initialise a repository | L3508, L4501, L4820 |
| B-2 | `jsonschema` is not installed; draft 2020-12 with `unevaluatedProperties` is required | L3506, L3509, L3927 |
| B-3 | Owner inputs missing: `sleeves.KR.notional_nav`, `sleeves.US.notional_nav` (both `null`); commission confirmation; ETF tick table before 2023-12-11 and every non-ETF tick table; sell-tax history | L76, L4463–L4464, L2797, L2803 |
| B-4 | The gate's cost table must move from `docs/asset_expansion_study.py:60` into `core/quant/validate.py`; this edits an existing study script | L591, L4129 |
| B-5 | TASK-M0-15 cannot run: `qf3_dnb_classes.py` and the QF3 variant series are not on this machine | L6004, L6060 |
| B-6 | Tech-fund amendments XS-05, XS-11, XS-19, XS-21 and GOV-7 change §7 blocks or conflict with them; they need an owner ruling before the store departs from §7 | R3 L1293, L1299, L1307, L1309, L818 |
| B-7 | `prep/readlines.py` is broken (SyntaxError) | — |
