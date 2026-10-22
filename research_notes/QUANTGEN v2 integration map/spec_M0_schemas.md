# spec_M0_schemas — JSON artifact schemas 2.0, card header/card schemas, field classes, artifact writer, governance log (R-32)

Source: `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` ("SPEC"; line numbers `L…` refer to it). Read in full: L3361-3375 (R-32), L3501-4122 (§6), L4874-4966 (§8.4); plus the §9 rows and §9.0b clauses of every cited test, §3.8/§3.9 (L1173-1251), §3.5 (L961-1113), the R-19…R-34 "Outputs and schema fields" lists, §7 `reproducibility` (L4680-4684). Tasks: `prep/tasks/M0.json` TASK-M0-07/08/09/10/11.
Everything named "proposed" below is a path/name choice of this brief; field names, enums, bounds and status strings are SPEC-verbatim.
Verification done while writing this brief (scratch only, nothing in the repo was changed): the reference validator of §B1.4 (stdlib, 218 lines) loaded the seven schemas of §C verbatim and (a) validated all six SPEC examples after typed placeholder fill, (b) rejected every example with any one required top-level field removed or one undeclared field added, (c) validated a synthetic full `model_card.macro` (§C.9) and refused it with each T-SCHEMA-02 field removed, (d) resolved all 294 rule-output pointers of §D.3 as declared. So T-SCHEMA-01/02/03 are satisfiable by the SPEC text as written; no §6 fix is required for them.

---

## A. Scope

| Task | Deliverable (one line) | Target files (E = exists, N = new/proposed) |
|---|---|---|
| TASK-M0-08 | Seven §6 schemas (JSON Schema 2020-12 subset) in one registry keyed by `$id`; closed-object rule applied by the loader; stdlib validator | N `core/ficc/schemas/{macro_state,overlay_decision,event_calendar,context_log,model_card_header.macro,model_card.macro,governance_event}.v2.0.json` (verbatim §C.1-C.7); N `core/ficc/macro_schema.py` (registry + validator). E `core/ficc/macro.py` (18-indicator sheet; unchanged in M0; M6 adds the builders of SPEC §3.5 L1073-1076) |
| TASK-M0-09 | Header schema + card schema over one field set; `validate_card_header`; `header_md5` / `results_md5`; conditional card rules | pure functions `header_issues`, `card_issues`, `header_md5`, `results_md5` in N `core/ficc/macro_schema.py`; the public `validate_card_header` is the one of `spec_M0_rules_store.md` §B6 (`core/rules`, SPEC L2773), which must call `header_issues` first (A.1). E `core/quant/validate.py:735 ModelCard` = the app's existing card format (not changed; mapping in §E.3) |
| TASK-M0-10 | Exhaustive acting/display field classes; per-artifact check result; quarantine path | N in `core/ficc/macro_schema.py` (`DISPLAY_PATHS`, `check_artifact`); quarantine writer in N `core/ficc/macro_artifacts.py`; dir `<artifact_dir>/quarantine/` |
| TASK-M0-11 | One artifact writer: canonical JSON, md5, provenance stamp, reproducibility record, RNG convention | N `core/ficc/macro_artifacts.py`; E `config.py` [+] `macro_artifact_dir()` (defined in `spec_M0_rules_store.md` §B1; pattern of `trading_dir()` L236-238) |
| TASK-M0-07 | Append-only, hash-chained `governance_events.jsonl` appender + chain verifier; every line validates against `quantgen/governance_event.v2.0` | N `core/rules/governance.py` (SPEC L4096: "`core/rules` (M0) owns the appender"); signatures owned by `spec_M0_rules_store.md` §B4, schema-side contract in B5 here |
| tests | T-SCHEMA-01/02/03, T-REPRO-01a, the governance clause of T-OWNER-01, unit forms of the deferred clauses | N `tests/macro_acceptance.py` exposing `tests() -> list[(name, fn)]` (the pattern of E `tests/expansion_acceptance.py:306`), registered in E `tests/run_all.py` L30-44; N `tests/fixtures/macro/schema_examples.json`, N `tests/fixtures/macro/card_results_synthetic.json` (rows in `MANIFEST.csv`, TASK-M0-03) |

Out of this brief (interfaces only, §E): TASK-M0-01/02/03 (scan, harness, manifest), M0-04/05/06/14/15 (rule objects, store, owner registry, DNB), M0-12/13 (cost floor, R-26 header checks: they plug into `validate_card_header`).

### A.1 Reconciliation with the sibling briefs in this folder (read after they were written; one decision per row for the coordinator)

| # | Topic | Sibling says | This brief | Proposed single answer |
|---|---|---|---|---|
| R-1 | Where `canonical_json` / `md5_hex` are defined | `spec_M0_rules_store.md` §B2: in `core/rules/macro_store.py`, `canonical_json(obj) -> str`, and "dependency direction `core/ficc → core/rules`, never the reverse" | in the pure leaf `core/ficc/macro_schema.py`, returning `bytes` | **One definition in the leaf**, re-exported by the store module. Reason: `validate_card_header` and the appender (both in `core/rules`) need the schema registry, and `header_md5`/`results_md5`/`check_artifact` (K5) need `canonical_json` + the field sets; if the store module (which validates on load) held `canonical_json`, the chain store → validation → schema leaf → store would be an import cycle. The leaf imports only the stdlib, so both directions stay legal. Return type: either; the hashed bytes must be `canonical_json(obj)` in UTF-8 (identical under both). |
| R-2 | `validate_card_header` | `spec_M0_rules_store.md` §B6: `validate_card_header(header, store, *, contract_notional_krw=None) -> None`, raises `MacroRefusal`; covers the R-26 clauses | schema + H1-H10, H15 | **One public function = the sibling's.** It first calls `macro_schema.header_issues(header, …)` (B4) and refuses when the list is non-empty, then applies its store-dependent R-26 clauses (H11-H13 here are cross-references, not a second implementation). |
| R-3 | Governance appender | `spec_M0_rules_store.md` §B4: `append_event(path, *, kind, actor, reason, refs, book_id=None, rule_id=None, key=None, old=..., new=..., utc=None) -> dict`; `verify_chain(path) -> None` raising on the first broken link; hand-kept `KINDS`/`ACTORS`/`REQUIRED` tuples | B5 | **Sibling signatures**, plus the four schema-side requirements of B5 (validate each record against the registry schema; torn-line refusal; the verifier also schema-validates and reports the 1-based line; injectable `event_id`). |
| R-4 | Artifact modules | `spec_architecture.md`: `core/ficc/macro_artifacts.py` holds builders, validator / `bounds_ok`, writer, quarantine; schemas `core/ficc/schemas/*.v2.0.json`; `write_artifact(obj, kind) -> Path`; `validate(obj, schema_id) -> (acting_errors, display_errors)` | same directory and file; the registry/validator/field classes split out into the pure `core/ficc/macro_schema.py` (R-1); `write_artifact(artifact, *, root, relpath) -> WriteResult`; `check_artifact(artifact) -> ArtifactCheck` | Keep the leaf split; the `(acting_errors, display_errors)` pair is `ArtifactCheck.acting_errors/display_errors`; `kind` is read from `artifact["schema"]`. |
| R-5 | Artifact dir | both siblings: `config.macro_artifact_dir()`, env `NEXTGEN_MACRO_DIR`, default `~/.nextgen/macro` | same | no conflict (name adopted here). |

Facts about the repo that shape the build: `jsonschema` is not installed (`ModuleNotFoundError`) and may not be added; PyYAML is already a dependency (`requirements.txt`: `pyyaml>=6.0`; used at `core/skills/workflows.py:28`); `core/ficc/__init__.py` is docstring-only (importing `core.ficc.macro_schema` pulls nothing heavy); shipped JSON data already lives beside code (`data/calendars/*.json`); `core/rules/*` today is the operator trading-rule store (Side/OrderKind/…), unrelated to §7.1 rule objects; the working tree is **not a git repository** (see F-14); `tests/run_all.py` currently runs 266 checks, all PASS (`qa/acceptance_results.json`).

---

## B. Build spec

### B1. `core/ficc/macro_schema.py` — registry and validator (pure; imports: `copy, functools, hashlib, json, re, datetime, pathlib, typing`)

#### B1.1 Conventions the validator must implement (SPEC L3505-3512)

| # | Convention (verbatim sense) | Implementation |
|---|---|---|
| 1 | "JSON Schema draft 2020-12. All schemas are loaded into **one registry keyed by `$id`**; a cross-schema `$ref` is relative to the `$id` base `quantgen/` (e.g. `macro_state.v2.0#/$defs/input`)" (L3506) | `Registry.by_id: dict[str, dict]`. `$ref` = `"<doc>#<json-pointer>"`; empty `<doc>` = same schema; else key `"quantgen/" + <doc>`. Only two shapes occur: `#/$defs/<name>` and `macro_state.v2.0#/$defs/input` / `model_card_header.macro.v2.0#/$defs/fields`. |
| 2 | "All times are ISO-8601 UTC with a "Z" suffix. Dates are ISO dates (a monthly series uses the first day of its reference month)" (L3507) | `format: date-time` is **asserted**: regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$` and `datetime.fromisoformat(v[:19])` must parse. `format: date`: `len == 10` and `date.fromisoformat`. `format` applies to strings only (a `null` under `type: ["string","null"]` passes). See F-1. |
| 3 | Common provenance: every artifact carries `schema`, `schema_version` ("2.0"), `generated_at_utc`, `knowledge_utc`, `git_hash`, `config_hash`, `data_snapshot_id`, `read_only: true`; `event_calendar` carries them once in its envelope; a model card carries them in its result part; "a `governance_event` line (§6.6) is a log record, not an artifact, and carries only its own fields" (L3508) | Already in each schema's `properties`/`required` (§C). The header schema has none of them (no `schema` discriminator on a header). |
| 4 | **Closed objects**: "`additionalProperties: false` applies to every object schema that declares `properties`, except `extras` (always open), a map (an object that declares its own `additionalProperties`), a schema that declares `unevaluatedProperties`, and the card header's shared field set `model_card_header.macro.v2.0#/$defs/fields`, which the two card schemas of §6.5 close through `unevaluatedProperties: false`. The listings omit the keyword for brevity; the schema loader adds it under exactly this rule, and T-SCHEMA-01 runs with it." (L3509) | `close_objects()` in B1.4, applied once at load to a deep copy; the schema files stay verbatim (no keyword added on disk). Walk: `properties` values (with their key, so the property named `extras` is skipped), `$defs` values (the def named `fields` is skipped), `items`, `additionalProperties` (when a schema), `allOf`. Objects without `properties` (e.g. `parameters`, `outcomes`, `tests.step1`, `timing.inputs`) stay open. |
| 5 | **Placeholders**: "a string written `<…>` stands for a value of the declared type (a hash, an instant, a date, a number); T-SCHEMA-01 replaces it by a typed sample before validating. Every other value is literal." (L3510) | Test helper `fill()` (B1.4): a string that fully matches `<[^<>]*>` is replaced, by the schema at that position: `format date-time` → `"2026-10-02T06:40:45Z"`; `format date` → `"2026-10-02"`; `integer` → `1`; `number` → `1.0e8`; else 32 × `"0"`. (`"<= close_print_bound_utc(KR, t)"` in the §8.4 example is literal: it does not end with `>`.) |
| 6 | "No artifact contains an order instruction. Weights are targets for the simulated order book only." (L3511) | Not schema-expressible beyond closure; enforced by T-RO-01 (other brief) and by closed objects. |
| 7 | Version history: v1.1/v1.2 artifacts used `schema_version` "1.1" (L3512) | No such artifacts exist in this repo; `schema_version` const "2.0" refuses them. No migration code. |

#### B1.2 Keyword subset (complete: these 18 are the only keywords the seven schemas use)

`$id, $defs, $ref, allOf, type (string or list), required, properties, additionalProperties (schema; `false` only via the loader), unevaluatedProperties (false), items, enum, const, minimum, maximum, exclusiveMinimum, minItems, format (date | date-time), description (ignored)`.

Semantics that differ from naive Python and must hold (all exercised by §D):
- `type: number` rejects `bool`; `type: integer` accepts `int` (not bool) and integral floats; `null` = `None`.
- `const` / `enum` use JSON equality: `True != 1`, `1 == 1.0`, `None` only equals `null` (`enum: [0.5, 1.0, null]`, `enum: [null, "widen_grid", …]`, `enum: [0.0, 0.10]`, `const: 2.0`, `const: true`).
- Numbers must be finite (NaN/±inf → error "not finite"; canonical JSON also refuses them, B3).
- `$ref` beside other keywords is evaluated together with them (header root: `{"type":"object","$ref":"#/$defs/fields","unevaluatedProperties":false}`).
- `unevaluatedProperties: false`: allowed keys = the static union of `properties` reachable through the schema itself, its `$ref` and its `allOf` (no `if/anyOf/oneOf` exists, so the static union is exact).
- `additionalProperties: <schema>` (maps: `owner_decisions`, `concentration.by_book`, `runtime[].consecutive_failures`, `rule_versions`, `gating_lines`, `forecast_eval.qlike_mcs_p/mse_mcs_p`) validates every key not in `properties`.
- `{}` = any JSON value (`owner_decisions.*.value`, `governance_event.old/new`, every leaf of `tests.*` and `printed`).
- Fail closed at load (`SchemaLoadError`): a keyword outside the 18, a `format` other than the two, a duplicate `$id`, a `$ref` that does not resolve, a missing schema file.
- The validator never fills a default and never mutates the instance.

#### B1.3 Public surface (proposed names)

```python
SCHEMA_DIR = Path(__file__).parent / "schemas"
BASE = "quantgen/"
ID = {  # artifact["schema"] const -> registry $id
    "quantgen.macro_state":      "quantgen/macro_state.v2.0",
    "quantgen.overlay_decision": "quantgen/overlay_decision.v2.0",
    "quantgen.event_calendar":   "quantgen/event_calendar.v2.0",
    "quantgen.context_log":      "quantgen/context_log.v2.0",
    "quantgen.model_card.macro": "quantgen/model_card.macro.v2.0",
    "quantgen.governance_event": "quantgen/governance_event.v2.0",
}
HEADER_ID = "quantgen/model_card_header.macro.v2.0"   # a header carries no `schema` field: always addressed explicitly
CARD_ID   = "quantgen/model_card.macro.v2.0"

class SchemaError(NamedTuple): path: str; message: str      # path = JSON pointer, "" = root; message in
    # {"required", "undeclared", "type [...]", "const <v>", "enum [...]", "minimum <n>", "maximum <n>",
    #  "exclusiveMinimum <n>", "minItems <n>", "format date|date-time", "not finite", "unknown schema"}
class SchemaLoadError(Exception)

@functools.lru_cache(maxsize=1)
def registry() -> Registry                       # loads the 7 files of SCHEMA_DIR, applies close_objects, runs the load checks
def validate(schema_id: str, instance) -> list[SchemaError]     # [] = valid; reports every error, never stops at the first
def schema_id_of(artifact) -> str | None         # ID.get(artifact.get("schema")) if artifact is a dict
def enum_of(schema_id: str, pointer: str) -> tuple   # single source for enums used by later milestones (no re-declared lists)
HEADER_FIELDS: frozenset[str]   # = properties of model_card_header.macro.v2.0#/$defs/fields (52 names)
RESULT_FIELDS: frozenset[str]   # = top-level properties of model_card.macro.v2.0 (48 names); HEADER_FIELDS ∩ RESULT_FIELDS = ∅ (verified)
VOLATILE_FIELDS = ("generated_at_utc", "git_hash")   # = reproducibility.determinism.volatile_fields (B3)
def canonical_json(obj) -> bytes                 # spec in B3; pure, defined here so the writer, the cards and the governance log share one serializer
def md5_hex(data: bytes) -> str
def header_md5(header: dict) -> str              # spec in B4
def results_md5(card: dict) -> str               # spec in B4
def split_card(card: dict) -> tuple[dict, dict]  # (header part, result part) by HEADER_FIELDS / RESULT_FIELDS
def header_issues(header: dict, *, acting_long_sample: bool = True, committed_md5: str | None = None,
                  seed_study: int | None = None) -> list[SchemaError]          # schema + H1-H10, H15 (B4)
def card_issues(card: dict, *, committed_header: dict | None = None,
                acting_long_sample: bool = True) -> list[SchemaError]            # schema + K1-K8 (B4)
```

Import direction (no cycles; A.1 R-1): `core/ficc/macro_schema.py` is a leaf (stdlib only, no I/O beyond reading its schema files). It is imported by `core/ficc/macro_artifacts.py` (I/O), by the `core/rules` store/validation modules and by `core/rules/governance.py`. Nothing in this area imports `core/engine`.

Error path convention (needed by the field classes of B2): a missing required key `k` under object path `p` is reported at `p + "/" + k`; an undeclared key likewise; array items at `p/<index>`.

#### B1.4 Reference implementation (verified in scratch against every case of §D.1-D.3; adapt names, keep semantics)

```python
"""Reference stdlib validator for the QUANTGEN section-6 schemas (JSON Schema 2020-12 subset)."""
import copy
import re
from datetime import date, datetime

BASE = "quantgen/"
_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
_PLACEHOLDER = re.compile(r"<[^<>]*>")
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is_type(v, t):
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())
    return isinstance(v, _TYPES[t])


def _json_eq(a, b):          # JSON equality: True != 1, 1 == 1.0
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def close_objects(schema, *, key=None, is_fields=False):
    """Section-6 closed-object rule, applied once at load."""
    if isinstance(schema, list):
        for s in schema:
            close_objects(s)
        return
    if not isinstance(schema, dict):
        return
    if ("properties" in schema and key != "extras" and not is_fields
            and "additionalProperties" not in schema and "unevaluatedProperties" not in schema):
        schema["additionalProperties"] = False
    for k, sub in (schema.get("properties") or {}).items():
        close_objects(sub, key=k)
    for k, sub in (schema.get("$defs") or {}).items():
        close_objects(sub, is_fields=(k == "fields"))
    for k in ("items", "additionalProperties"):
        if isinstance(schema.get(k), dict):
            close_objects(schema[k])
    close_objects(schema.get("allOf") or [])


SUPPORTED = {"$id", "$ref", "$defs", "type", "required", "properties", "const", "enum", "format", "description",
             "items", "minimum", "maximum", "exclusiveMinimum", "minItems", "additionalProperties", "allOf",
             "unevaluatedProperties"}


class SchemaLoadError(Exception):
    pass


class Registry:
    def __init__(self, schemas):
        self.by_id = {}
        for s in schemas:
            s = copy.deepcopy(s)
            close_objects(s)
            if s["$id"] in self.by_id:
                raise SchemaLoadError("duplicate $id %s" % s["$id"])
            self.by_id[s["$id"]] = s
        for root in self.by_id.values():          # fail closed at load: unknown keyword, bad format, dangling $ref
            self._check(root, root)

    def _check(self, s, root):
        bad = set(s) - SUPPORTED
        if bad:
            raise SchemaLoadError("unsupported keyword(s) %s in %s" % (sorted(bad), root["$id"]))
        if s.get("format") not in (None, "date", "date-time"):
            raise SchemaLoadError("unsupported format %r in %s" % (s["format"], root["$id"]))
        if "$ref" in s:
            try:
                self.resolve(s["$ref"], root)
            except KeyError:
                raise SchemaLoadError("dangling $ref %s in %s" % (s["$ref"], root["$id"]))
        subs = list((s.get("properties") or {}).values()) + list((s.get("$defs") or {}).values()) + list(s.get("allOf") or [])
        subs += [s[k] for k in ("items", "additionalProperties") if isinstance(s.get(k), dict)]
        for sub in subs:
            self._check(sub, root)

    def resolve(self, ref, root):
        doc, _, ptr = ref.partition("#")
        node = root if not doc else self.by_id[doc if doc.startswith(BASE) else BASE + doc]
        newroot = node
        for part in [p for p in ptr.split("/") if p]:
            node = node[part]
        return node, newroot

    def declared(self, schema, root):
        """Property names statically reachable through properties / $ref / allOf."""
        names = set(schema.get("properties") or {})
        if "$ref" in schema:
            names |= self.declared(*self.resolve(schema["$ref"], root))
        for sub in schema.get("allOf") or []:
            names |= self.declared(sub, root)
        return names

    def validate(self, schema_id, inst):
        root = self.by_id[schema_id]
        errs = []
        self._v(root, root, inst, "", errs)
        return errs

    def _v(self, s, root, v, path, errs):
        if "$ref" in s:
            sub, subroot = self.resolve(s["$ref"], root)
            self._v(sub, subroot, v, path, errs)
        for sub in s.get("allOf") or []:
            self._v(sub, root, v, path, errs)
        if "const" in s and not _json_eq(v, s["const"]):
            errs.append((path, "const %r" % (s["const"],)))
        if "enum" in s and not any(_json_eq(v, e) for e in s["enum"]):
            errs.append((path, "enum %r" % (s["enum"],)))
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_is_type(v, t) for t in types):
                errs.append((path, "type %s" % types))
                return
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v != v or v in (float("inf"), float("-inf")):
                errs.append((path, "not finite"))
            if "minimum" in s and v < s["minimum"]:
                errs.append((path, "minimum %s" % s["minimum"]))
            if "maximum" in s and v > s["maximum"]:
                errs.append((path, "maximum %s" % s["maximum"]))
            if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
                errs.append((path, "exclusiveMinimum %s" % s["exclusiveMinimum"]))
        if isinstance(v, str) and "format" in s:
            ok = True
            if s["format"] == "date-time":
                ok = bool(_DT.match(v))
                if ok:
                    try:
                        datetime.fromisoformat(v[:19])
                    except ValueError:
                        ok = False
            elif s["format"] == "date":
                try:
                    ok = len(v) == 10 and bool(date.fromisoformat(v))
                except ValueError:
                    ok = False
            if not ok:
                errs.append((path, "format %s" % s["format"]))
        if isinstance(v, list):
            if "minItems" in s and len(v) < s["minItems"]:
                errs.append((path, "minItems %s" % s["minItems"]))
            if isinstance(s.get("items"), dict):
                for i, x in enumerate(v):
                    self._v(s["items"], root, x, "%s/%d" % (path, i), errs)
        if isinstance(v, dict):
            for r in s.get("required") or []:
                if r not in v:
                    errs.append(("%s/%s" % (path, r), "required"))
            props = s.get("properties") or {}
            for k, x in v.items():
                if k in props:
                    self._v(props[k], root, x, "%s/%s" % (path, k), errs)
            ap = s.get("additionalProperties")
            if ap is False:
                for k in v:
                    if k not in props:
                        errs.append(("%s/%s" % (path, k), "undeclared"))
            elif isinstance(ap, dict):
                for k, x in v.items():
                    if k not in props:
                        self._v(ap, root, x, "%s/%s" % (path, k), errs)
            if s.get("unevaluatedProperties") is False:
                known = self.declared(s, root)
                for k in v:
                    if k not in known:
                        errs.append(("%s/%s" % (path, k), "undeclared"))

    # typed placeholder fill (T-SCHEMA-01)
    def fill(self, schema_id, inst):
        root = self.by_id[schema_id]
        return self._fill(root, root, copy.deepcopy(inst))

    def _schemas_at(self, s, root):
        out = [(s, root)]
        if "$ref" in s:
            out += self._schemas_at(*self.resolve(s["$ref"], root))
        for sub in s.get("allOf") or []:
            out += self._schemas_at(sub, root)
        return out

    def _fill(self, s, root, v):
        alts = self._schemas_at(s, root)
        if isinstance(v, str) and _PLACEHOLDER.fullmatch(v):
            for a, _ in alts:
                types = a.get("type")
                types = types if isinstance(types, list) else [types]
                if a.get("format") == "date-time":
                    return "2026-10-02T06:40:45Z"
                if a.get("format") == "date":
                    return "2026-10-02"
                if "integer" in types:
                    return 1
                if "number" in types:
                    return 1.0e8
            return "0" * 32
        if isinstance(v, dict):
            for k in v:
                for a, r in alts:
                    sub = (a.get("properties") or {}).get(k)
                    if sub is None and isinstance(a.get("additionalProperties"), dict):
                        sub = a["additionalProperties"]
                    if sub is not None:
                        v[k] = self._fill(sub, r, v[k])
                        break
                else:
                    v[k] = self._fill({}, root, v[k])
        if isinstance(v, list):
            hit = next(((a["items"], r) for a, r in alts if isinstance(a.get("items"), dict)), ({}, root))
            v[:] = [self._fill(hit[0], hit[1], x) for x in v]
        return v
```

`fill()` is a test helper (T-SCHEMA-01 only); keep it in `tests/macro_acceptance.py`, not in the runtime module.

### B2. Field classes and the per-artifact check (TASK-M0-10; R-32 L3370, exhaustive list "R2-C4")

#### B2.1 Classes (verbatim list, as JSON-pointer prefixes)

```python
DISPLAY_PATHS = {
  "quantgen.macro_state": (
    "/owner_decisions", "/alerts", "/annotations", "/refusal_books", "/forward_sim",
    # "the flags that set no exposure":
    "/flags/gap_sessions", "/flags/kr_open_gap_event", "/flags/var_display_scale",
    # "the hedge-state flags ..., which never HALT, R-09":
    "/flags/hedge_credit_off", "/flags/hedge_failure", "/flags/classic_risk_off", "/flags/fx_hedge_credit",
    "/flags/hedge_reasons", "/flags/hedge_stale_inputs",
    # "in macro_state.vol":
    "/vol/display_label_rel", "/vol/display_label_abs", "/vol/label_method_rel", "/vol/label_method_abs", "/vol/alt_sigma_logged",
  ),
  "quantgen.overlay_decision": ("/reasons", "/refusal", "/forward_sim"),
}
NON_ACTING_ROLES = ("forward_sim", "risk_model", "context", "history")     # "in both, the inputs entries whose role is not acting_exposure"
WHOLE_REFUSAL = ("quantgen.context_log", "quantgen.event_calendar", "quantgen.model_card.macro")
```

Rule for one error path `p` of a `macro_state` / `overlay_decision`:
1. display if `p == q` or `p.startswith(q + "/")` for a `q` in `DISPLAY_PATHS[kind]`;
2. display if `p` is `/inputs/<i>` or below, `inputs[i]` is a dict and `inputs[i]["role"] in NON_ACTING_ROLES`;
3. **acting otherwise** — "Every other property is acting: among them the `acting_exposure` entries of `inputs`, the rest of `vol`, `concentration`, `runtime`, `lag_audit`, `fail_closed`, the ladder and hard-stop flags, and every weight, multiplier and composition field. A property added later is acting until it is classified here, so an unclassified field fails closed." (L3370). Consequences: an undeclared key anywhere outside a display prefix is acting; an input whose `role` is missing or invalid is acting; errors at `/inputs`, `/flags`, `/vol` themselves (wrong type) are acting; provenance fields are acting; `flags.dm_bear_state`, `ladder_*`, `block_new_entries`, `hard_stop*`, `engine_state` are acting.

`extras` is "never schema-validated" (L3370): no error can arise below it except `/extras` not being an object (acting). `extras.w_target` / `extras.w_held` (R-26 per-instrument weights) "are checked by `bounds_ok` in code, in [0, 1]":

```python
def check_extras_bounds(artifact: dict) -> list[SchemaError]
#   for key in ("w_target", "w_held") present in artifact["extras"]: value may be a number, a list of numbers or a dict of numbers;
#   every leaf must be a finite number in [0, 1], else SchemaError("/extras/<key>[/<sub>]", "bounds [0, 1]")  -> ACTING class
```

#### B2.2 `check_artifact`

```python
@dataclass(frozen=True)
class ArtifactCheck:
    kind: str | None            # artifact["schema"]
    schema_id: str | None
    status: Literal["ok", "display_errors", "acting_errors", "refused"]
    acting_errors: tuple[SchemaError, ...]
    display_errors: tuple[SchemaError, ...]
    books: tuple[str, ...]      # the books the artifact describes = the HALT scope; () unless status == "acting_errors"

def check_artifact(artifact) -> ArtifactCheck
```

Algorithm:
1. `sid = schema_id_of(artifact)`; `None` (not a dict, no/unknown `schema`) → `status="refused"`, one error `("/schema", "unknown schema")`, `books=()`. A `governance_event` or a bare header passed here → `refused` (they have their own entry points, B4/B5).
2. `errs = validate(sid, artifact)`; for `macro_state` / `overlay_decision` add `check_extras_bounds` and the semantic checks of B2.3; for `context_log` add S8; for `model_card.macro` add the pure card checks K1-K6 of B4.
3. `kind in WHOLE_REFUSAL`: any error → `refused` ("refused: it is not written to the artifact directory, it is written to `<artifact_dir>/quarantine/` with its errors (so the audit trail and replays keep it), an alert is raised, and it never HALTs (P9, P18)", L3370); `books=()` always.
4. `macro_state` / `overlay_decision`: split by B2.1. Any acting error → `acting_errors` ("trips the `bounds_ok` gate and HALTs (OPS) the books it describes; it is written to `<artifact_dir>/quarantine/` with its errors", L3370; §3.9 L1222-1227). Only display errors → `display_errors` ("writes the artifact with `extras.validation_errors`, raises an alert and never HALTs"). None → `ok`.
5. `books` for `acting_errors`: `macro_state` → every parseable `runtime[].book_id`; if none is readable → `("recommended:<market>", "specification:<market>")`; `overlay_decision` → `("recommended:<market>", "specification:<market>")` ∪ `books` of its `acting_exposure` inputs; if `market` itself is unreadable → `("*",)` = every book the caller holds for this run (fail closed). See F-9.

M0 delivers the classification only. The HALT itself (`runtime_halt(book_id, "OPS", …)`, operator re-arm "once the fix's test passes", L1179) is wired by `bounds_ok` at M8 (SPEC §9.0b L5595); M0 must not call the engine.

#### B2.3 Semantic (cross-field) checks stated in §6 but not expressible in the keyword subset

Each returns `SchemaError`s that are classified by their path exactly like schema errors.

| Id | Artifact | Check (source) | Error path | M |
|---|---|---|---|---|
| S1 | overlay_decision | In `vol_scale_card`, every `multipliers[].card`, `forward_sim[].card`, `refusal[].card`: `displayed_as ∈ {"recommendation","insurance"}` **iff** `verdict = "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}` (L3767) | `<card path>/displayed_as` | M0 |
| S2 | overlay_decision | `displayed_as = "invariant"` **iff** `disposition = INVARIANT_STEP` (L3768) | same | M0 |
| S3 | overlay_decision | `vol_scale_recommended_book` = `vol_scale` if its card is PASS (S1 sense), else `1.0` (L3733, L3769); absent `vol_scale_card` counts as not PASS | `/vol_scale_recommended_book` | M0 |
| S4 | overlay_decision | `ladder` and `post_rearm_cap` are non-null only when `family = "market_gross"` ("market_gross only", L3738-3739) | `/ladder`, `/post_rearm_cap` | M0 |
| S5 | overlay_decision | `overlay_min == min(1.0, multipliers[].value…, ladder, post_rearm_cap)` (nulls skipped); `overlay_applied_recommended_book` = the same `min()` over only the factors whose card satisfies S1 or S2, "every other factor enters as 1.0" (L3769); `overlay_applied_spec_book == overlay_min` (an inference: the specification book holds every factor, L4794). Recomputed by `bounds_ok` (L1222-1223, T-CAP-02) | `/overlay_min`, `/overlay_applied_*` | function in M0; gate at M2/M8 (F-10 for the ladder term) |
| S6 | macro_state | `flags.engine_state` equals the `engine_state` of the `runtime[]` entry whose `book_id == "recommended:" + market`, when that entry exists ("reports the market's recommended book", L3584, L1178) | `/flags/engine_state` | M0 |
| S7 | macro_state | In a non-null `runtime[].halt`: top-level `class`, `reason_code`, `since_utc` restate `causes[0]`; `rearm_mode` is `"operator"` while any cause with `cleared_utc` null/absent has `rearm_mode = "operator"`, else `"auto"` (L1179) | `/runtime/<i>/halt/...` | M0 function; meaningful from M5 |
| S8 | context_log | `as_of_utc == decision_utc` (L3874 "= decision_utc (one log per decision)") | `/as_of_utc` | M0 |
| S9 | governance log | `prev_row_md5` is null only on the first line (L4110) | (appender/verifier, B5) | M0 |

Not checked here because the needed fact is outside the record: `vt_weight_recommended_book` vs R-06's card verdict (L3559), `available_at_utc ≤ decision_utc` and `retrieved_at_utc ≤ knowledge_utc` (lag audit, M1; L3697), `var_display_scale = sqrt(max(n_US, 1))` (I-06b, M5), label byte-identity with the rule's label (L3938, M7).

### B3. `core/ficc/macro_artifacts.py` — canonical JSON, provenance, writer, quarantine (TASK-M0-11)

Config read (verbatim, SPEC §7 L4680-4684; the rules-store brief stores it, this module reads it):

```yaml
reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002,
                  record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5,
                           ledger_hash_at_registration, ledger_hash_at_run],
                  determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash],
                                rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}   # T-REPRO-01a/b/c
```

```python
# canonical_json / md5_hex / VOLATILE_FIELDS are defined in macro_schema.py (pure) and re-exported here.
# VOLATILE_FIELDS must equal reproducibility.determinism.volatile_fields: assert when the store block is loaded.

def canonical_json(obj) -> bytes
#   json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
#   = "UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace" (T-REPLAY-01 L5616; TASK-M0-11).
#   CPython's json prints floats with float.__repr__. NaN/inf raise ValueError (fail closed). numpy scalars must be converted by the
#   builder (.item()); no `default=` hook (the existing validate._json_default str()-fallback at core/quant/validate.py:769-776 must NOT be reused: it hides types).
#   Pin: canonical_json({"b": 1.0, "a": [0.1, True, None, "é", 1e-07, 100000000.0, 3]})
#        == b'{"a":[0.1,true,null,"\xc3\xa9",1e-07,100000000.0,3],"b":1.0}'   (md5 4e41d73e54f7559cf7d69a19f57c2d33)
def md5_hex(data: bytes) -> str                              # hashlib.md5(data).hexdigest()
def strip_volatile(artifact: dict) -> dict                   # shallow copy without the top-level VOLATILE_FIELDS (replay comparison, T-REPLAY-01)
def git_hash() -> str                                        # `git rev-parse HEAD` of the repo root; no git repo -> the literal "UNVERSIONED" (never invent a sha; F-14)
def data_snapshot_id(content_hashes=()) -> str               # M0 stub of SPEC L1014: md5 of the sorted content hashes (order-invariant); M1 replaces the body.
#   Stub rule: md5_hex("\n".join(sorted(content_hashes)).encode()); with no store -> md5 of b"" = d41d8cd98f00b204e9800998ecf8427e (F-6)
def provenance(*, knowledge_utc: str, config_hash: str, data_snapshot_id: str, generated_at_utc: str | None = None) -> dict
#   -> {"schema_version": "2.0", "read_only": True, "generated_at_utc": <now, "…Z", second resolution>, "knowledge_utc": knowledge_utc,
#       "git_hash": git_hash(), "config_hash": config_hash, "data_snapshot_id": data_snapshot_id}
#   knowledge_utc is a parameter, never "now" (SPEC L1001-1003, L1105). The builder adds "schema".
def rng(seed: int) -> numpy.random.Generator                 # Generator(PCG64(SeedSequence(seed)))
def child_rngs(seed: int, n: int) -> list                    # [Generator(PCG64(s)) for s in SeedSequence(seed).spawn(n)]
#   blas_threads: 1 -> study/test entry points set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS = "1" before importing numpy
#   (T-REPRO-01b/c run from M7/M9; M0 only fixes the convention).

@dataclass(frozen=True)
class WriteResult:
    status: Literal["written", "written_with_display_errors", "quarantined"]
    path: Path
    check: ArtifactCheck
    alerts: tuple[dict, ...]    # structured like macro_state.alerts[] items (§C.1); sinks are M8

def write_artifact(artifact: dict, *, root: Path | None = None, relpath: str | None = None) -> WriteResult
def quarantine(artifact, errors, *, root: Path | None = None) -> Path
```

`write_artifact` algorithm (the only path by which a §6 artifact or card reaches disk):
1. `root = root or config.macro_artifact_dir()`; tests always pass a temp `root` (T-HERM-02).
2. `chk = check_artifact(artifact)`.
3. `ok` → atomic write of `canonical_json(artifact)` to `root/relpath` (temp file in the same dir + `os.replace`, as `core/rules/store.py:216-231` does, but **without** its `except: pass` — a failed write raises). → `written`.
4. `display_errors` → `artifact.setdefault("extras", {})["validation_errors"] = [{"path": p, "message": m} for …]` (shape proposed; the field name `extras.validation_errors` is SPEC, L3370/L3630/L3755), write as in 3, one alert `{code: "SCHEMA_DISPLAY_FIELD", severity: "warn", …}` (code proposed). → `written_with_display_errors`. Never a HALT.
5. `acting_errors` → nothing in the artifact directory; `quarantine(...)`; alert severity `page` (proposed); the caller (M8 `bounds_ok`) HALTs (OPS) `chk.books`. → `quarantined`.
6. `refused` (`context_log`, `event_calendar`, `model_card`, unknown) → nothing in the artifact directory; `quarantine(...)`; alert; **never** a HALT (`chk.books == ()`). "A card that fails validation is not written." (L3368). → `quarantined`.
7. A `model_card.macro` has already had K1-K6 applied inside `check_artifact` (step 2), so a direct call cannot write a card that breaks them. The comparison with the committed header (K8, T-CARD-01) is `card_issues(card, committed_header=…)`, which the M7 study calls before `write_artifact`.

`quarantine`: writes `canonical_json({"quarantined_utc": …, "schema": kind, "errors": [{"path","message","class": "acting"|"display"|"refused"}], "artifact": artifact})` to `root/"quarantine"/f"{kind or 'unknown'}__{md5_hex(canonical_json(artifact))[:12]}.json"` (file naming proposed; content-addressed so a replayed failure does not multiply files). If the artifact itself is not JSON-serialisable (NaN), store `repr(artifact)` under `"artifact_repr"` instead.

Default `relpath` (proposed; SPEC fixes only `<artifact_dir>/quarantine/`): `macro_state/<market>/<decided_session>.json`; `overlay_decision/<market>/<effective_session>/<family>.json`; `context_log/<decision_utc with ":" removed>.json`; `event_calendar/<calendar_version>.json`. Cards: the caller passes `root`/`relpath` (their home is M7's decision, §E.3).

`config.macro_artifact_dir()` (SPEC §7 L4126 "It gains the macro artifact directory (proposed)") is specified in `spec_M0_rules_store.md` §B1: env `NEXTGEN_MACRO_DIR`, else `Path.home() / ".nextgen" / "macro"` (the pattern of `trading_dir()`, `config.py` L236-238). This module only calls it.

### B4. Header and card validation — pure functions in `core/ficc/macro_schema.py` (TASK-M0-09; §6.5 L3909-4092, §8.4 L4874-4896)

Binding statements:
- "**Two schemas, one field set.** The **header** (the §8.4 pre-registration) is validated against `model_card_header.macro` by `validate_card_header` at commit, before any run; `header_md5` covers the header fields only. The **card** is header ∪ results and is validated against `model_card.macro` when it is written; `results_md5` covers the result fields. Both close through `unevaluatedProperties: false`, so a header that carries a result field (`selection_factor`, `timing_profile`, `forward_record`, …) is refused, and a card cannot carry an undeclared field." (L3913)
- "The header is written before the study run, its md5 (`header_md5`) is committed, and it is immutable once committed." (L4876)
- "**The Kish N̂ is never a field.** `N_hat_linear` is the linear eq. 9 value, printed as a bound." (L4092)
- "`selection_factor` is computed by `step3()` at the run, never declared: a header that declares it is refused" (L4884); "`verdict_at_f1` and `verdict_at_f_neff` are both printed, and `verdict` is the one at the binding f" (L4091).

```python
def header_md5(header: dict) -> str
#   md5_hex(canonical_json({k: v for k, v in header.items() if k in HEADER_FIELDS and k != "header_md5"}))      (F-2)
def results_md5(card: dict) -> str
#   md5_hex(canonical_json({k: v for k, v in card.items() if k in RESULT_FIELDS and k not in ("results_md5",) + VOLATILE_FIELDS}))   (F-3)
def split_card(card: dict) -> tuple[dict, dict]                # (header part, result part) by HEADER_FIELDS / RESULT_FIELDS

def header_issues(header: dict, *, acting_long_sample: bool = True, committed_md5: str | None = None,
                  seed_study: int | None = None) -> list[SchemaError]
def card_issues(card: dict, *, committed_header: dict | None = None, acting_long_sample: bool = True) -> list[SchemaError]
```

`header_issues` = `validate(HEADER_ID, header)` + the rules marked "here" below. The public commit-time entry point is `validate_card_header` of `spec_M0_rules_store.md` §B6 (A.1 R-2): it calls `header_issues` first and refuses on any issue, then applies the store-dependent rules. A refused header: nothing is committed, no md5 is recorded, no ledger row or governance event is written. (Committing — the `header_commit` governance event, the ledger hash — is M7; M0 ships the checks and the hash.)

| Id | Refused when (source) | Needs | Owner |
|---|---|---|---|
| H1 | a field in the schema's `required` list is missing — incl. `ledger_hash_at_registration`, `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav` (L4088; T-BOOK-01, T-CARD-01) | schema | here |
| H2 | the header declares `selection_factor` "or any other result field" (L4088) | schema (`unevaluatedProperties`) | here |
| H3 | "an acting long-sample card whose `start_band` or `midpoint_halves` is null (R-22; both are null on other cards)" (L4088, L2392) | `acting_long_sample` argument; default **True** = fail closed (F-4) | here |
| H4 | `header["header_md5"] != header_md5(header)`; or `committed_md5` given and different (T-CARD-01 L5663) | — | here |
| H5 | `checks != "gate_package_" + gate_package_version` (L3984, L4886, L4954) | — | here |
| H6 | `comparator` not matching the class: CARD-P → `S_same_average_exposure`; CARD-O → `overlay_off` ("`comparator` (S, or overlay-off for CARD-O)", L4886) | — | here (F-13: tech-fund S_beta) |
| H7 | `build_status_on_pass = BUILD_AS_INSURANCE` with `class != CARD-P` or `label` null (L4089) | — | here |
| H8 | `class = CARD-P` with `claim_type != "protection"` ("A Sharpe or predictability claim on a protective rule is refused", L4851; a reading, F-5) | — | here |
| H9 | `no_trade_band = 0.10` on a book other than `KRX_stock_book` / `US_shares_KIS` (L3952) | — | here (pure; the same R-26 clause is listed in the rules-store brief §B6 — implement once, in `header_issues`) |
| H10 | `instrument_book = multi_line` without non-empty `instrument_lines`; a futures book (`KOSPI200_futures`, `mini_KOSPI200_futures`, `CME_micro_ES`, `FX_KRX_USD_futures`) with null/absent `roll_calendar` (L4882) | — | here (pure; as H9) |
| H11 | "a non-KRW book without `nav_fx`" (L4088) | the KRW/non-KRW book map (F-7) | rules-store brief §B6 (TASK-M0-13) |
| H12 | `notional_nav` "differs from `sleeves.<market>.notional_nav` at commit" (L4088); a store without the sleeve key at a real commit → refused (no silent pass) | rules store | rules-store brief §B6 (TASK-M0-13) |
| H13 | "a stock book used as a market-gross scalar"; "a futures line whose one contract exceeds 5% of `notional_nav`" (L4088) | rule object, instrument table | rules-store brief §B6 (TASK-M0-13) |
| H14 | `gate_package_version` / `gate_package_md5` other than the frozen package's (L2244) | `gate.package` | M7 |
| H15 | `seed != reproducibility.seed_study` (11) (L4888 "`seed: 11`", L4680) | `seed_study` | here, when `seed_study` is supplied |
| H16 | `start_band` not one of the frozen `gate.evaluation.start_band_shapes`; `history_first_close != gate.evaluation.history_start[market]`; searched-parameter budget > 8 over all macro cards (L2372-2375, L3966, L4896) | gate config | M7 |

Card rules. K1-K6 are pure single-record checks and run inside `check_artifact` (B2.2 step 2), error path = the field named; `card_issues` = the `check_artifact(card)` errors + K7-K8.

| Id | Refused when (source) | Where |
|---|---|---|
| K1 | not (`disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}` **iff** `verdict = PASS`) (L4089) | `check_artifact` |
| K2 | on PASS: `build_status_on_pass = BUILD_NOW` must give `RECOMMENDATION`; `BUILD_AS_INSURANCE` must give `BUILD_AS_INSURANCE` ("a build status, not a verdict", L4089) | `check_artifact` |
| K3 | `disposition = BUILD_AS_INSURANCE` with `class != CARD-P` or `label` null (L4089) | `check_artifact` |
| K4 | `disposition = INVARIANT_STEP` on a card whose `family_id != "R-31"` ("reserved for R-31 (binding share ≤ 0.10)", L4089) | `check_artifact` |
| K5 | `card["header_md5"] != header_md5(header part)` or `card["results_md5"] != results_md5(card)` | `check_artifact` |
| K6 | `start_band` non-null with `start_band_results` null, or `midpoint_halves` non-null with `midpoint_halves_results` null (reading of L3364 "the stability lines"; F-4) | `check_artifact` |
| K7 | every H-rule that needs no outside fact (H3, H5-H10) re-applied to the header part | `card_issues` |
| K8 | `committed_header` given and any header field differs from it (T-CARD-01: "A card whose header md5 differs from the committed header is refused") | `card_issues` |

Already enforced by the card schema itself: `lag_audit_violations` const `0`; `cost_stress` const `2.0`; `selection_factor.rule` const `computed_by_step3`; `verdict` ∈ 4 values (no `NOT_RUN`: a written card has a verdict; `NOT_RUN` exists only in `overlay_decision.$defs.card`); `tests` and `printed` key sets closed; no Kish property anywhere.

Header-field semantics table (§8.4 L4878-4888, verbatim groups; "Every field below is required unless marked optional", L4876):

| Group | Fields |
|---|---|
| Identity | `card_id`, `family_id` (assigned by rule, R-23), `rule_id`, `revision`, `class`, `claim` (verbatim text) and `claim_type`, `build_status_on_pass` (BUILD_NOW or BUILD_AS_INSURANCE), `tier`, `created_utc`, `header_md5`, `gate_package_version` and `gate_package_md5` |
| Rule | `hypothesis`, `mechanism` (a second-moment mechanism; red line P5), `rule`, `parameters`, `searched_parameters`, `estimator` |
| Book (R-26) | `instrument_book` (with `instrument_lines[]` for `multi_line`), `rebalance`, `no_trade_band`, `notional_nav` (= `sleeves.<market>.notional_nav` at commit), `nav_fx` (non-KRW books), `fill_model`, `roll_calendar` (futures), `costs: {per_side: read_from_gate, floor: tick_floor, stress: 2.0, stress_line: printed, schedule (optional; it may only raise a cost)}` |
| Data and conventions (R-22, R-20) | `data` (source and `value_status = official_close`), `history_first_close` (the registry's history start), `data_span` (start = first close + estimator warm-up; end = `gate.evaluation.data_cutoff` for a CARD-P drafted for the freeze, else the last official close before the commit, as a date), `cash_convention`, `episode_rule_version`, `start_band` (a frozen shape) and `midpoint_halves` (with the split date), both null unless the card is an acting long-sample card, `gating_lines` (optional), `regime_lines`, `primary_oos_line`, `printed_lines` |
| Multiplicity (R-23) | `ledger_hash_at_registration`, `N_raw_at_registration`. `selection_factor` is computed by `step3()` at the run, never declared |
| Timing (R-34, R-19) | `timing`: the decision convention and every acting input with its series, channel, `available_at` rule and timing class; `live_feeds` (required if the card is timing-fragile). `timing_profile` is a result (covered by `results_md5`), never in the header |
| Checks | `comparator` (S, or overlay-off for CARD-O), `benchmarks`, `checks: gate_package_<version>`, card-specific `claim_lines` (e.g. R-28's stacked ΔMDD ≥ 3 pp) and `pooling_rule` |
| Outcomes | What PASS, INSUFFICIENT DATA and REJECT lead to |
| Label and seed | `label` (the text displayed with the verdict), `seed: 11` |

Revision vs new card (L4890-4896; consumed by the ledger/M7, recorded here because it defines header immutability): new **revision** (counted in N) = "any threshold, window, multiplier, timing, universe, estimator, class, cash convention, start band or episode rule, and the adoption of a new gate-package version"; new **card** (also counted) = "a different claim, a different instrument book, rebalance rule, band or venue (DNB #23)"; "An edit to an acting parameter in the rules store outside a revision demotes the card (R-25)"; parameter budget: "at most **8 searched parameters**" over all macro cards.

Config cross-check (verbatim, SPEC §7 L4617-4619; assert at load that both lists are subsets of the schema `required` lists — verified true):

```yaml
  card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version,
                         family_id, ledger_hash_at_registration, history_first_close, data_span]   # start_band, midpoint_halves: acting long-sample cards (R-22)
  card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]          # §6.5
```

### B5. `core/rules/governance.py` — `governance_events.jsonl` (TASK-M0-07; §6.6 L4094-4119, §3.9 L1248-1250)

"Every HALT and re-arm, book-state change, demotion, package freeze or redesign, header commit, owner ruling, calendar or notional change, R-15 admissibility re-weighting, R-31 binding-share recompute, change of a derived binding (R-19 rule 5), forward-record reset and verdict-integrity failure writes one line. Each line carries the md5 of the previous line (`prev_row_md5`, null only on the first), as `gate/acceptance_runs.jsonl` does; the chain is verified at app start (T-OBS-05). `core/rules` (M0) owns the appender; T-OWNER-01 writes the first event." (L4096)

Signatures are those of `spec_M0_rules_store.md` §B4 (A.1 R-3):

```python
KINDS  = ("halt","rearm","book_state","demotion","package_freeze","package_redesign","header_commit","owner_ruling","calendar_change",
          "notional_change","admissibility_reweight","binding_share_recompute","binding_change","record_reset","verdict_integrity")   # 15
ACTORS = ("owner","operator","runtime","harness","council")
def append_event(path: Path, *, kind: str, actor: str, reason: str, refs: list[str], book_id: str | None = None,
                 rule_id: str | None = None, key: str | None = None, old=..., new=..., utc: str | None = None,
                 event_id: str | None = None) -> dict                     # event_id: added here, for deterministic tests
def verify_chain(path: Path) -> None                                       # raises GovernanceLogBroken(line: int, reason: str) on the first bad line
```

Default path: `config.macro_artifact_dir() / "governance_events.jsonl"` (location proposed in both briefs; F-8). Schema-side requirements this brief adds to that section:

1. **One source for the shape.** The record is validated with `validate("quantgen/governance_event.v2.0", record)` before the write; any error raises and nothing is appended. `KINDS` / `ACTORS` must equal `enum_of(GOV_ID, "/properties/kind")` / `…/actor` (assert at import, or derive them); no separate hand-kept `REQUIRED` tuple.
2. **Record** = `{"schema": "quantgen.governance_event", "schema_version": "2.0", "event_id": event_id or uuid4 string, "utc": utc or now "…Z", "kind", "book_id", "rule_id", "key", ["old"], ["new"], "actor", "reason", "refs": list(refs), "prev_row_md5"}`; `book_id`, `rule_id`, `key` are always present (null allowed; they are `required`); `old`/`new` are written only when supplied (any JSON type).
3. **Chain.** `prev_row_md5` = md5 of the stored UTF-8 bytes of the previous line without its `\n`; `None` only when the file has no line. Read and append in binary (`"ab"`, one `write`, `flush`, `os.fsync`) so Windows never writes `\r\n`. A non-empty file that does not end in `b"\n"` (torn write) → raise, append nothing. The file is never rewritten, truncated or repaired by code.
4. **Verifier.** Missing or empty file → passes. For line *i* (1-based, raw bytes): JSON-parse, schema-validate, and `prev_row_md5` must be `None` if *i* = 1 else the md5 of line *i−1*'s stored bytes; a final line without `b"\n"` is bad. The first bad line raises with its number. At M8 app start this becomes `GOVERNANCE_LOG_BROKEN` (page) (T-OBS-05, L5681); "Ship the chain verifier now; M8 wires it into app start" (TASK-M0-07).

Who writes which kind (for later milestones; the appender accepts all 15 from day one): `owner_ruling` (M0, owner registry, T-OWNER-01), `notional_change` (M0-13), `calendar_change` (M1), `book_state`/`halt`/`rearm` (M1 OPS runtime, M5 RISK), `binding_change` (R-19 rule 5), `admissibility_reweight` (R-15, M4), `binding_share_recompute` (R-31), `package_freeze`/`package_redesign`/`header_commit` (M7), `demotion`/`record_reset`/`verdict_integrity` (M8).

---

## C. Schemas (verbatim from SPEC §6; store each as its own file under `core/ficc/schemas/`, unmodified — the loader adds `additionalProperties: false`)

Counts for a load-time self-check: `macro_state` 26 top-level properties / 23 required; `overlay_decision` 32 / 28; `event_calendar` 10 / 10; `context_log` 13 / 12; `model_card_header.macro` `$defs.fields` 52 / 44; `model_card.macro` 48 / 39 (plus the header's via `allOf`); `governance_event` 14 / 12. `extras` exists only on `macro_state`, `overlay_decision`, `context_log`.

### C.1 `quantgen/macro_state.v2.0` (one per market per decision time; SPEC L3524-3652)

New in 2.0 (L3516-3521): every input carries `value_status`, `session_date`, `available_at_source`, `retrieved_at_utc` (required) and its staleness `role`; `vol` carries the instrument book and both volatility labels; `flags` carry the hard stop, the step state, gap sessions and `fx_hedge_credit`; new blocks `annotations` (R-08), `refusal_books` and `forward_sim` (display only), `concentration` (R-07), `owner_decisions`; (round 1) `knowledge_utc`, `decided_session`, `run_mode`; inputs carry `obs_kind`, `dispute`, `books`, `expected_available_utc` (the next-due instant), `stale_deadline_utc`, `content_hash`; the `lag_audit` record; `vol.estimator_gate` as an object, R-30's estimator names, `vt_status`, `vt_weight_recommended_book`; `flags.hedge_reasons`, `gap_sessions ≥ 0`, `var_display_scale`; R-31's ladder names; `concentration.by_book`; structured `alerts`; `runtime[]`, one entry per book.

```json
{
  "$id": "quantgen/macro_state.v2.0",
  "type": "object",
  "required": ["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
               "decision_utc","decided_session","effective_session","market","run_mode","inputs","lag_audit","vol","flags","annotations",
               "concentration","owner_decisions","runtime","fail_closed","alerts"],
  "properties": {
    "schema": {"const": "quantgen.macro_state"}, "schema_version": {"const": "2.0"}, "read_only": {"const": true},
    "generated_at_utc": {"type": "string", "format": "date-time"},
    "knowledge_utc": {"type": "string", "format": "date-time", "description": "the run's pinned knowledge instant (R-01)"},
    "git_hash": {"type": "string"}, "config_hash": {"type": "string"}, "data_snapshot_id": {"type": "string"},
    "decision_utc": {"type": "string", "format": "date-time", "description": "close_print_bound_utc(market, decided_session) from the calendar (R-20)"},
    "decided_session": {"type": "string", "format": "date", "description": "the session whose official close is decided on (t)"},
    "effective_session": {"type": "string", "format": "date", "description": "the session whose return the decision earns (t+1)"},
    "market": {"enum": ["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]},
    "run_mode": {"enum": ["live","backtest","replay"]},
    "inputs": {"type": "array", "items": {"$ref": "#/$defs/input"}},
    "lag_audit": {"type": "object", "required": ["checked","violations"], "properties": {
        "checked": {"type": "integer", "minimum": 0},
        "violations": {"type": "array", "items": {"type": "object",
          "required": ["series_id","obs_date","check","expected_usable_at_utc","stamped_available_at_utc"],
          "properties": {"series_id": {"type": "string"}, "obs_date": {"type": "string", "format": "date"}, "check": {"type": "string"},
            "expected_usable_at_utc": {"type": "string", "format": "date-time"},
            "stamped_available_at_utc": {"type": "string", "format": "date-time"}}}}}},
    "vol": {"type": "object", "properties": {
        "estimator": {"enum": ["sma20","ewma094","ewma097","garch_t","gjr_t","log_har_range","comb"], "description": "R-30; the sma60 reference line goes in extras (§9.4)"},
        "estimator_b5": {"enum": ["PASS","FAIL","NOT_RUN"]},
        "estimator_gate": {"type": "object", "required": ["status","fallback_used"], "properties": {
            "status": {"enum": ["registered_default","challenger_selected","fallback_to_sma20","NOT_RUN"]},
            "stage1": {"type": ["object","null"]}, "stage2_mcs_p": {"type": ["number","null"]}, "stage3_rank": {"type": ["integer","null"]},
            "fallback_used": {"type": "boolean"}, "reason": {"type": ["string","null"]}}},
        "vt_status": {"enum": ["ok","warmup","fail_closed"], "description": "R-06: a warm-up returns 1.0 and is not a failure"},
        "sigma_ann": {"type": ["number","null"], "minimum": 0},
        "target_ann": {"type": "number", "exclusiveMinimum": 0},
        "vt_weight_next": {"type": "number", "minimum": 0, "maximum": 1, "description": "specification book"},
        "vt_weight_recommended_book": {"type": "number", "minimum": 0, "maximum": 1, "description": "= vt_weight_next once R-06's card is PASS; 1.0 while NOT_RUN or INSUFFICIENT"},
        "instrument_book": {"type": "string"}, "rebalance": {"enum": ["daily","weekly","monthly"]},
        "no_trade_band": {"type": ["number","null"], "minimum": 0},
        "display_label_rel": {"enum": ["calm","normal","elevated","stressed"]},
        "label_method_rel": {"const": "trailing756_quartiles_causal_filtered"},
        "display_label_abs": {"enum": ["calm","normal","elevated","stressed"]},
        "label_method_abs": {"const": "expanding_full_history_quartiles_causal_filtered"},
        "alt_sigma_logged": {"type": ["number","null"], "description": "asymmetric estimator only (BL-C04); max(SMA20, implied) is retired"}},
      "required": ["estimator","estimator_b5","estimator_gate","vt_status","sigma_ann","target_ann","vt_weight_next","vt_weight_recommended_book",
                   "instrument_book","display_label_rel","label_method_rel","display_label_abs","label_method_abs"]},
    "flags": {"type": "object", "properties": {
        "dm_bear_state": {"type": "boolean", "description": "specification book only (R-04)"},
        "hedge_credit_off": {"type": "boolean"}, "hedge_failure": {"type": "boolean"}, "classic_risk_off": {"type": "boolean"},
        "hedge_reasons": {"type": "array", "items": {"enum": ["ok","risk_model_input_stale","risk_model_exception","corr_positive","core_pce_ge_3"]}, "description": "causes can co-occur (R-09, R-19)"},
        "hedge_stale_inputs": {"type": "array", "items": {"type": "string"}},
        "fx_hedge_credit": {"type": ["boolean","null"], "description": "display only (R-09)"},
        "kr_open_gap_event": {"type": "boolean"},
        "gap_sessions": {"type": "integer", "minimum": 0, "description": "n_US: US sessions since the previous KRX close; 0 after a US-only holiday (R-10)"},
        "var_display_scale": {"type": "number", "minimum": 1, "description": "sqrt(max(n_US, 1)); display only (R-10)"},
        "ladder_step": {"enum": ["none","step_-8","step_-12","hard_stop_-15"]},
        "ladder_dwell_left": {"type": "integer", "minimum": 0},
        "block_new_entries": {"type": "boolean", "description": "the -12% step's evaluator block (R-31)"},
        "ladder_steps_act_in": {"enum": ["recommended","specification"], "description": "recommended only as INVARIANT_STEP (binding share <= 0.10)"},
        "hard_stop": {"enum": ["armed","halted","rearm_refused","post_rearm_cap"]},
        "hard_stop_level": {"type": "number", "description": "owner decision D2 (risk_layer.drawdown.hard_stop.level)"},
        "engine_state": {"enum": ["DISARMED","ARMED","HALTED"], "description": "the market's recommended book; every book is in runtime[]"}},
      "required": ["hedge_credit_off","hedge_failure","classic_risk_off","hedge_reasons","kr_open_gap_event","gap_sessions","var_display_scale",
                   "ladder_step","ladder_dwell_left","block_new_entries","hard_stop","engine_state"]},
    "annotations": {"type": "object", "properties": {"vix_ge_vix3m": {"type": "boolean", "description": "R-08; changes no weight"}, "notes": {"type": "array", "items": {"type": "string"}}},
      "required": ["vix_ge_vix3m"]},
    "refusal_books": {"type": "object", "description": "display only; read by no book (R-11, R-12)",
      "properties": {"S1_krw_flag": {"type": ["boolean","null"]}, "S2_rates_flag": {"type": ["boolean","null"]}}},
    "forward_sim": {"type": "object", "description": "FORWARD-SIM cards (R-28, R-29); never the recommended book",
      "properties": {"R28_below_sma10m": {"type": ["boolean","null"]}, "R29_vt_weight_next": {"type": ["number","null"], "minimum": 0, "maximum": 1}}},
    "concentration": {"type": "object", "properties": {
        "template": {"enum": ["domestic_max10_or_weight","msci_25_50","pair_35"], "description": "owner decision D1"},
        "pair_share_kospi": {"type": ["number","null"]}, "pair_lookthrough_share": {"type": ["number","null"]},
        "pair_risk_contribution": {"type": ["number","null"]},
        "absolute_bound": {"type": ["number","null"], "description": "template single-name level / look-through share (R-07 (4))"},
        "active_bound": {"type": ["number","null"], "description": "min over names of 0.05 / (s_i - b_tilde_i) (R-07 (2), (4))"},
        "aggregate_bound": {"type": ["number","null"], "description": "aggregate template limit / look-through share of names above 4.5% (R-07 (3), (4))"},
        "semis_bound": {"type": ["number","null"], "description": "0.50 / look-through semiconductor share of sleeve NAV (R-07 (5))"},
        "by_book": {"type": "object", "additionalProperties": {"type": "object", "required": ["composed","gross","binding_factor"],
          "properties": {"composed": {"type": "number", "minimum": 0, "maximum": 1}, "gross": {"type": "number", "minimum": 0, "maximum": 1},
            "binding_factor": {"enum": ["none","absolute_single_name","active_single_name","aggregate","semis"]}}}}},
      "required": ["template","by_book"]},
    "owner_decisions": {"type": "object", "description": "every decision whose canonical key a rule of this market reads, plus every decision with status pending", "additionalProperties": {"type": "object",
        "required": ["decision","value","status"],
        "properties": {"decision": {"enum": ["D1","D2","D3","D4","D5","D6"]}, "value": {}, "status": {"enum": ["default","owner_set","pending"]}}}},
    "runtime": {"type": "array", "items": {"type": "object", "required": ["book_id","engine_state","halt","consecutive_failures","book_counter"],
      "properties": {"book_id": {"type": "string", "description": "recommended:<market>, specification:<market>, forward_sim:<rule>, refusal:<rule>, card:<card_id>:<on|off|S>"},
        "engine_state": {"enum": ["DISARMED","ARMED","HALTED"]},
        "halt": {"type": ["object","null"], "required": ["class","reason_code","since_utc","rearm_mode","causes"],
          "properties": {"class": {"enum": ["RISK","OPS"]}, "reason_code": {"type": "string"},
            "component": {"type": ["string","null"]}, "series_id": {"type": ["string","null"]}, "since_utc": {"type": "string", "format": "date-time"},
            "rearm_not_before": {"type": ["string","null"], "format": "date", "description": "RISK: the decided_session (t+10) of the earliest automatic re-arm decision (a breach re-arms only once its limit is met); null for OPS"}, "rearm_mode": {"enum": ["auto","operator"]},
            "causes": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["class","reason_code","since_utc","rearm_mode"],
              "properties": {"class": {"enum": ["RISK","OPS"]}, "reason_code": {"type": "string"}, "since_utc": {"type": "string", "format": "date-time"},
                "rearm_mode": {"enum": ["auto","operator"]}, "rearm_not_before": {"type": ["string","null"], "format": "date"},
                "cleared_utc": {"type": ["string","null"], "format": "date-time"}}}},
            "ack_by": {"type": ["string","null"]}, "ack_utc": {"type": ["string","null"], "format": "date-time"}}},
        "post_rearm_cap_until": {"type": ["string","null"], "format": "date", "description": "the last decided_session whose weights carry post_rearm_cap 0.5: the actual re-arm decision + 9 sessions (t+19 after an automatic re-arm at t+10)"}, "nav": {"type": ["number","null"]},
        "hwm_hard": {"type": ["number","null"]}, "ref_step": {"type": ["number","null"]},
        "consecutive_failures": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}, "description": "per acting series bound to the book (R-19 rule 4)"},
        "book_counter": {"type": "integer", "minimum": 0, "description": "R-19 rule 4"}}}},
    "fail_closed": {"type": "boolean"},
    "alerts": {"type": "array", "items": {"type": "object", "required": ["alert_id","code","severity","component","first_seen_utc","count"],
      "properties": {"alert_id": {"type": "string"}, "code": {"type": "string"}, "severity": {"enum": ["info","warn","page"]},
        "component": {"type": "string"}, "series_id": {"type": ["string","null"]}, "books": {"type": "array", "items": {"type": "string"}},
        "first_seen_utc": {"type": "string", "format": "date-time"}, "count": {"type": "integer", "minimum": 1},
        "escalated": {"type": "boolean"}, "ack_utc": {"type": ["string","null"], "format": "date-time"}}}},
    "extras": {"type": "object", "description": "open: e.g. regime_tags (R-20), validation_errors (R-32), the sma60 reference line"}
  },
  "$defs": {"input": {"type": "object",
    "required": ["name","series_id","source","obs_date","session_date","obs_kind","value","value_status","dispute","available_at_utc","available_at_source",
                 "retrieved_at_utc","expected_available_utc","stale_deadline_utc","vintage","timing","role","books","status","content_hash"],
    "properties": {"name": {"type": "string"}, "series_id": {"type": "string"}, "source": {"type": "string"}, "channel": {"type": ["string","null"]},
      "obs_date": {"type": "string", "format": "date"}, "session_date": {"type": ["string","null"], "format": "date"},
      "obs_kind": {"enum": ["close","quote_snapshot","release","bar","derived"]},
      "value": {"type": ["number","null"]},
      "value_status": {"enum": ["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]},
      "dispute": {"type": "boolean", "description": "official value used, two-source mismatch alerted (R-01 (3)); never a failure"},
      "available_at_utc": {"type": "string", "format": "date-time"},
      "available_at_source": {"enum": ["published","calendar_bound","inferred_from_retrieval"]},
      "retrieved_at_utc": {"type": "string", "format": "date-time"},
      "expected_available_utc": {"type": ["string","null"], "format": "date-time", "description": "R-19: the instant the next observation after obs_date is due"},
      "stale_deadline_utc": {"type": ["string","null"], "format": "date-time", "description": "expected_available_utc + grace (one publication business day)"},
      "vintage": {"type": ["string","null"], "format": "date", "description": "ALFRED realtime_start of this value; null for unrevised market prices"},
      "timing": {"enum": ["live","publication","value_proxy"]},
      "role": {"enum": ["acting_exposure","forward_sim","risk_model","context","history"]},
      "books": {"type": "array", "items": {"type": "string"}, "description": "the books this binding feeds: the HALT scope (§3.8)"},
      "status": {"enum": ["ok","stale","stale_missed_release","missing","provisional_rejected","session_mismatch","synthetic_rejected","disputed","warmup"]},
      "content_hash": {"type": "string"}}}}
}
```

Example (KR, decided at the official close of 2 Oct 2026, earning in the next KRX session 6 Oct; SPEC L3658-3693) — fixture `macro_state`:

```json
{"schema":"quantgen.macro_state","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>",
 "decision_utc":"2026-10-02T06:30:30Z","decided_session":"2026-10-02","effective_session":"2026-10-06","market":"KR","run_mode":"live",
 "inputs":[{"name":"KOSPI official close","series_id":"KOSPI_OFFICIAL_CLOSE","source":"KIS","channel":"KRX official close","obs_date":"2026-10-02","session_date":"2026-10-02",
            "obs_kind":"close","value":7003.74,"value_status":"official_close","dispute":false,"available_at_utc":"2026-10-02T06:30:30Z","available_at_source":"calendar_bound",
            "retrieved_at_utc":"2026-10-02T06:40:45Z","expected_available_utc":"2026-10-06T06:30:30Z","stale_deadline_utc":"2026-10-07T06:30:30Z","vintage":null,
            "timing":"live","role":"acting_exposure","books":["specification:KR"],"status":"ok","content_hash":"<md5>"},
           {"name":"USD/KRW DEXKOUS (labelled proxy; R-11 refusal book and context)","series_id":"DEXKOUS","source":"FRED","channel":"H.10","obs_date":"2026-09-25","session_date":null,
            "obs_kind":"release","value":1356.51,"value_status":"first_release","dispute":false,"available_at_utc":"2026-09-28T20:15:00Z","available_at_source":"published",
            "retrieved_at_utc":"2026-10-02T06:40:45Z","expected_available_utc":"2026-10-05T20:15:00Z","stale_deadline_utc":"2026-10-06T20:15:00Z","vintage":null,
            "timing":"publication","role":"context","books":[],"status":"ok","content_hash":"<md5>"}],
 "lag_audit":{"checked":1,"violations":[]},
 "vol":{"estimator":"sma20","estimator_b5":"PASS",
        "estimator_gate":{"status":"registered_default","stage1":null,"stage2_mcs_p":null,"stage3_rank":null,"fallback_used":false,"reason":null},
        "vt_status":"ok","sigma_ann":0.2882,"target_ann":0.20,"vt_weight_next":0.694,"vt_weight_recommended_book":1.0,
        "instrument_book":"KRX_ETF_line","rebalance":"daily","no_trade_band":0.0,
        "display_label_rel":"elevated","label_method_rel":"trailing756_quartiles_causal_filtered",
        "display_label_abs":"stressed","label_method_abs":"expanding_full_history_quartiles_causal_filtered","alt_sigma_logged":null},
 "flags":{"dm_bear_state":false,"hedge_credit_off":true,"hedge_failure":false,"classic_risk_off":false,"hedge_reasons":["corr_positive","core_pce_ge_3"],
          "hedge_stale_inputs":[],"fx_hedge_credit":false,"kr_open_gap_event":true,"gap_sessions":2,"var_display_scale":1.4142,
          "ladder_step":"none","ladder_dwell_left":0,"block_new_entries":false,"ladder_steps_act_in":"specification",
          "hard_stop":"armed","hard_stop_level":-0.15,"engine_state":"ARMED"},
 "annotations":{"vix_ge_vix3m":false,"notes":[]},
 "refusal_books":{"S1_krw_flag":false,"S2_rates_flag":null},
 "forward_sim":{"R28_below_sma10m":null,"R29_vt_weight_next":null},
 "concentration":{"template":"msci_25_50","pair_share_kospi":0.51,"pair_lookthrough_share":0.538,"pair_risk_contribution":0.75,
                  "absolute_bound":0.755,"active_bound":0.685,"semis_bound":null,
                  "by_book":{"recommended:KR":{"composed":1.0,"gross":0.685,"binding_factor":"active_single_name"},
                             "specification:KR":{"composed":0.694,"gross":0.685,"binding_factor":"active_single_name"}}},
 "owner_decisions":{"risk_layer.korea_caps.template":{"decision":"D1","value":"msci_25_50","status":"default"},
                    "risk_layer.drawdown.hard_stop.level":{"decision":"D2","value":-0.15,"status":"default"}},
 "runtime":[{"book_id":"recommended:KR","engine_state":"ARMED","halt":null,"post_rearm_cap_until":null,"nav":null,"hwm_hard":null,"ref_step":null,
             "consecutive_failures":{},"book_counter":0},
            {"book_id":"specification:KR","engine_state":"ARMED","halt":null,"post_rearm_cap_until":null,"nav":null,"hwm_hard":null,"ref_step":null,
             "consecutive_failures":{},"book_counter":0}],
 "fail_closed":false,"alerts":[]}
```

Binding notes on the example (L3697-3706): `decision_utc` = `close_print_bound_utc('KR', 2026-10-02)` = 06:30:30Z; "Every input has `available_at_utc ≤ decision_utc` and `retrieved_at_utc ≤ knowledge_utc`"; `expected_available_utc` "is when the **next** observation is due, never the availability of the row itself"; `stale_deadline_utc` adds one publication business day; `gap_sessions` 2 → VaR scale √2 = 1.4142, and "After a US-only holiday `gap_sessions` is 0 and the scale is 1 (I-06c)"; `inputs[]` is abbreviated (2 rows shown) and `lag_audit.checked` counts the one audited row shown (context rows are skipped by the audit); `ladder_steps_act_in = "specification"` while the Korea steps bind on more than 10% of days; "NAV fields are null until the simulated books start".

### C.2 `quantgen/overlay_decision.v2.0` (one per market × family per decision; SPEC L3718-3763)

New in 2.0 (L3710-3715): `composition` is `min`, `overlay_min` replaces `overlay_product`; the market-gross record carries the `ladder` multiplier; each card carries a `disposition` and a `label`; new lists `refusal` (display only) and `binding`; (round 1) the common provenance fields; `inputs` typed as the `macro_state` input; the `post_rearm_cap` factor; the `INVARIANT_STEP` disposition; `extras` (R-26, R-27, R-32).

```json
{
  "$id": "quantgen/overlay_decision.v2.0", "type": "object",
  "required": ["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
               "decision_utc","effective_session","market","family","exposure_basis","vol_scale","vol_scale_recommended_book","multipliers","composition",
               "overlay_min","overlay_floor","overlay_cap","overlay_applied_spec_book","overlay_applied_recommended_book","forward_sim","refusal","binding",
               "reasons","inputs","rule_versions"],
  "properties": {
    "schema": {"const": "quantgen.overlay_decision"}, "schema_version": {"const": "2.0"}, "read_only": {"const": true},
    "generated_at_utc": {"type": "string", "format": "date-time"}, "knowledge_utc": {"type": "string", "format": "date-time"},
    "git_hash": {"type": "string"}, "config_hash": {"type": "string"}, "data_snapshot_id": {"type": "string"},
    "decision_utc": {"type": "string", "format": "date-time"}, "effective_session": {"type": "string", "format": "date"},
    "market": {"enum": ["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]},
    "family": {"enum": ["momentum","reversal","flow","quality","ts_trend","market_gross"]},
    "exposure_basis": {"enum": ["active","total"]},
    "vol_scale": {"type": "number", "minimum": 0, "maximum": 1, "description": "specification book (vs; vt for market_gross)"},
    "vol_scale_recommended_book": {"type": "number", "minimum": 0, "maximum": 1, "description": "= vol_scale if its card is PASS, else 1.0"},
    "vol_scale_card": {"$ref": "#/$defs/card"},
    "multipliers": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","exposure_basis","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "exposure_basis": {"enum": ["active","total"]}, "card": {"$ref": "#/$defs/card"}}}},
    "ladder": {"enum": [0.5, 1.0, null], "description": "market_gross only (R-07, R-31)"},
    "post_rearm_cap": {"enum": [0.5, 1.0, null], "description": "market_gross only; an argument of min() for 10 sessions after a RISK re-arm (R-07)"},
    "composition": {"const": "min"},
    "overlay_min": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "overlay_floor": {"const": 0.5}, "overlay_cap": {"const": 1.0},
    "overlay_applied_spec_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "overlay_applied_recommended_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "forward_sim": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0, "maximum": 1.0},
                      "would_apply_to": {"type": "string"}, "card": {"$ref": "#/$defs/card"}}}},
    "refusal": {"type": "array", "description": "display only; read by no book (R-11, R-12)", "items": {"type": "object", "required": ["rule_id","value","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "would_apply_to": {"type": "string"}, "card": {"$ref": "#/$defs/card"}}}},
    "binding": {"type": "array", "items": {"type": "string"}, "description": "factors at which min() or a limit bound"},
    "reasons": {"type": "array", "items": {"type": "string"}},
    "inputs": {"type": "array", "items": {"$ref": "macro_state.v2.0#/$defs/input"}},
    "rule_versions": {"type": "object", "additionalProperties": {"type": "string"}},
    "extras": {"type": "object", "description": "open: R-26 {instrument_book, contracts, w_target, w_held, band, usdkrw}, R-27 {fill_model, decision_price_source, fill_status, flags}, R-32 validation_errors"}
  },
  "$defs": {"card": {"type": "object", "required": ["card_id","class","verdict","disposition","displayed_as","results_md5"],
     "properties": {"card_id": {"type": "string"}, "class": {"enum": ["CARD-O","CARD-P"]},
       "verdict": {"enum": ["PASS","REVISE","REJECT","INSUFFICIENT_DATA","NOT_RUN"]},
       "disposition": {"enum": ["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]},
       "displayed_as": {"enum": ["recommendation","insurance","invariant","descriptive","refusal"]},
       "label": {"type": ["string","null"]}, "results_md5": {"type": ["string","null"]}}}}
}
```

Rules (verbatim, L3767-3771):
- `displayed_as ∈ {"recommendation", "insurance"}` iff `verdict = "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`.
- `displayed_as = "invariant"` iff `disposition = INVARIANT_STEP`: an R-31 step whose binding share is ≤ 0.10, frozen with the R-31 header. It needs no PASS and acts as part of the R-07 invariant (Resolution 6; R-31, R-35).
- `vol_scale_recommended_book` and `overlay_applied_recommended_book` use only those factors; every other factor enters as 1.0.
- The recommended-book builder refuses any factor with disposition `SPECIFICATION_ONLY`, `FORWARD_SIM` or `REFUSAL_BOOK`, and any card whose `build_status_on_pass` is BUILD_AS_INSURANCE while its verdict is NOT_RUN or INSUFFICIENT_DATA (I-03, R-35).
- A validation failure confined to display or context fields writes the record with `extras.validation_errors` and an alert, and never HALTs; an acting-field failure HALTs (OPS) the books the record describes (R-32).

Example (before the first card run; every verdict `NOT_RUN`; SPEC L3776-3792) — fixture `overlay_decision`:

```json
{"schema":"quantgen.overlay_decision","schema_version":"2.0","read_only":true,"generated_at_utc":"<run time>","knowledge_utc":"<pinned knowledge instant>",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","decision_utc":"2026-10-01T20:00:30Z","effective_session":"2026-10-02",
 "market":"US","family":"momentum","exposure_basis":"active","vol_scale":0.50,"vol_scale_recommended_book":1.0,
 "vol_scale_card":{"card_id":"MACRO-R03-US-MOM","class":"CARD-O","verdict":"NOT_RUN","disposition":"DESCRIPTIVE","displayed_as":"descriptive",
                   "label":"indicative PASS; step 3 borderline","results_md5":null},
 "multipliers":[{"rule_id":"R-04-DM","value":1.0,"exposure_basis":"active",
                 "card":{"card_id":"MACRO-R04-US-DM","class":"CARD-O","verdict":"NOT_RUN","disposition":"SPECIFICATION_ONLY","displayed_as":"descriptive",
                         "label":"step 3 FAIL (indicative)","results_md5":null}}],
 "ladder":null,"post_rearm_cap":null,"composition":"min","overlay_min":1.0,"overlay_floor":0.5,"overlay_cap":1.0,
 "overlay_applied_spec_book":1.0,"overlay_applied_recommended_book":1.0,
 "forward_sim":[],"refusal":[],"binding":[],
 "reasons":["DM: 24m market return +39.7% >= 0 -> 1.0 (specification book only)","VS: sigma126 23.9% -> min(1, 0.12/0.239)=0.50"],
 "inputs":[{"name":"Mom sigma126","series_id":"MOM_PAPER_LS_SERIES","source":"French Data Library","channel":"Mom daily (research snapshot)","obs_date":"2026-08-31","session_date":null,
            "obs_kind":"derived","value":0.239,"value_status":"vendor_derived","dispute":false,"available_at_utc":"2026-09-30T00:00:00Z","available_at_source":"published",
            "retrieved_at_utc":"<retrieved_at_utc>","expected_available_utc":null,"stale_deadline_utc":null,"vintage":null,
            "timing":"publication","role":"acting_exposure","books":["specification:US"],"status":"ok","content_hash":"<md5>"}],
 "rule_versions":{"R-03":"2.0","R-04":"2.0"}}
```

Notes (L3796-3798): US `decision_utc` = `close_print_bound_utc('US', 2026-10-01)` = 20:00:30Z; staleness fields are null only because the research file carries no publication schedule (in production R-19 fills both); the S2 refusal entry belongs in the US record with `family: "market_gross"` and `exposure_basis: "total"`: `{"rule_id":"R-12-S2","value":0.5,"would_apply_to":"US duration-sensitive gross (refusal book)","card":{"card_id":"MACRO-R12-US-RATES","class":"CARD-P","verdict":"REJECT","disposition":"REFUSAL_BOOK","displayed_as":"refusal",...}}` (elided in the SPEC, so not a T-SCHEMA-01 example; a completed copy is used in §D.3).

### C.3 `quantgen/event_calendar.v2.0` (one file per calendar version; `core/calendars`; SPEC L3809-3830)

New in 2.0 (L3802-3806): the BoK decision and the press conference are separate event types; a `KRX_HOLIDAY_GAP` type with `gap_sessions` and `var_display_scale`; the `annotate_only` window action; (round 1) a file envelope carrying the common provenance fields once; `gap_sessions ≥ 0`.

```json
{"$id":"quantgen/event_calendar.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","calendar_version","events"],
 "properties":{"schema":{"const":"quantgen.event_calendar"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "calendar_version":{"type":"string","description":"the owner-signed core/calendars data version (T-CAL-01)"},
  "events":{"type":"array","items":{"$ref":"#/$defs/event"}}},
 "$defs":{"event":{"type":"object",
  "required":["event_id","type","region","scheduled_utc","status","source","windows"],
  "properties":{"event_id":{"type":"string"},
   "type":{"enum":["FOMC","US_CPI","US_NFP","US_OTHER_RELEASE","BOK_DECISION","BOK_PRESS_CONFERENCE","BOJ","ECB","KOSPI200_EXPIRY","INDEX_CHANGE","HYPERSCALER_EARNINGS","OIL_GEO","FX_INTERVENTION","KRX_HOLIDAY_GAP","POLICY_FRAMEWORK_CHANGE","MARKET_STRUCTURE_CHANGE","OTHER"]},
   "region":{"type":"string"},"scheduled_utc":{"type":"string","format":"date-time"},
   "status":{"enum":["scheduled","released","cancelled","delayed"]},"released_utc":{"type":["string","null"],"format":"date-time"},
   "source":{"type":"string"},
   "windows":{"type":"array","items":{"type":"object","required":["market","action","start_utc","end_utc"],
      "properties":{"market":{"type":"string"},"action":{"enum":["evaluator_block_new_intraday_entries","evaluator_block_new_futures_entries","annotate_only"]},
                    "start_utc":{"type":"string","format":"date-time"},"end_utc":{"type":"string","format":"date-time"},
                    "resume_condition":{"type":["string","null"]}}}},
   "kr_open_gap_session":{"type":["string","null"],"format":"date"},
   "gap_sessions":{"type":["integer","null"],"minimum":0},
   "var_display_scale":{"type":["number","null"],"description":"sqrt(max(n_US, 1)) for multi-session gaps; display only"},
   "scenario_tag":{"type":["string","null"]},"notes":{"type":"string"}}}}}
```

Envelope and the two example entries (SPEC L3836-3837, L3843-3847, L3853-3856) — fixture `event_calendar` = the envelope with `events` = [FOMC, NFP]:

```json
{"schema":"quantgen.event_calendar","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","calendar_version":"<signed version>","events":[]}
```
```json
{"event_id":"FOMC-2026-10-28","type":"FOMC","region":"US","scheduled_utc":"2026-10-28T18:00:00Z","status":"scheduled","released_utc":null,
 "source":"federalreserve.gov FOMC calendar",
 "windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":"VIX < pre-14:00 ET level else 19:30Z"},
            {"market":"KR_FUT_NIGHT","action":"evaluator_block_new_futures_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":null}],
 "kr_open_gap_session":"2026-10-29","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event night"}
```
```json
{"event_id":"US-NFP-2026-10-02","type":"US_NFP","region":"US","scheduled_utc":"2026-10-02T12:30:00Z","status":"scheduled","released_utc":null,
 "source":"bls.gov Employment Situation schedule",
 "windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-02T12:25:00Z","end_utc":"2026-10-02T14:00:00Z","resume_condition":"10:00 ET"}],
 "kr_open_gap_session":"2026-10-06","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event; the 6 Oct session is also tagged KRX_HOLIDAY_GAP"}
```

### C.4 `quantgen/context_log.v2.0` (one per decision; `core/ficc/macro`; SPEC L3868-3889)

New in 2.0 (L3861-3865): items require `vintage` (null for unrevised series) and `retrieved_at_utc`; revised series carry `first_release`, `latest`, `vintage_date`; each item carries its timing and a stale label; (round 1) the common provenance fields and `decision_utc`; items require `series_id`, `value_status`, `stale`. "`vintage` is the vintage of `value`; `latest` and `vintage_date` are the latest vintage visible at `knowledge_utc`; `as_of_utc` is the run's `decision_utc` (one log per decision). A `context_log` that fails validation is refused, labelled and alerted, and never HALTs (R-32)."

```json
{"$id":"quantgen/context_log.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","decision_utc","as_of_utc","items","acts"],
 "properties":{"schema":{"const":"quantgen.context_log"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "decision_utc":{"type":"string","format":"date-time"},
  "as_of_utc":{"type":"string","format":"date-time","description":"= decision_utc (one log per decision)"},
  "acts":{"const":false},
  "items":{"type":"array","items":{"type":"object",
     "required":["name","series_id","value","obs_date","available_at_utc","retrieved_at_utc","vintage","source","timing","value_status","stale"],
     "properties":{"name":{"type":"string"},"series_id":{"type":"string"},"value":{"type":["number","string","null"]},
        "obs_date":{"type":"string","format":"date"},
        "available_at_utc":{"type":"string","format":"date-time"},"retrieved_at_utc":{"type":"string","format":"date-time"},
        "vintage":{"type":["string","null"],"format":"date","description":"the vintage of value (ALFRED realtime_start); null for unrevised series"},
        "first_release":{"type":["number","null"]},"latest":{"type":["number","null"]},
        "vintage_date":{"type":["string","null"],"format":"date","description":"the latest vintage visible at knowledge_utc"},
        "value_status":{"enum":["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]},
        "source":{"type":"string"},"timing":{"enum":["live","publication","value_proxy"]},"stale":{"type":"boolean"},
        "zscore_causal":{"type":["number","null"]},"zscore_window":{"type":["string","null"]},
        "from_sheet":{"type":"boolean","description":"true for the existing 18-indicator sheet items"},
        "range":{"type":["array","null"],"items":{"type":"number"}},"note":{"type":"string"}}}},
  "extras":{"type":"object"}}}
```

Example (SPEC L3895-3906) — fixture `context_log`:

```json
{"schema":"quantgen.context_log","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","decision_utc":"2026-10-02T06:30:30Z","as_of_utc":"2026-10-02T06:30:30Z","acts":false,
 "items":[
  {"name":"Taylor residual range (pp)","series_id":"TAYLOR_RESIDUAL_RANGE","value":null,"range":[-2.3,-0.4],"obs_date":"2026-08-01",
   "available_at_utc":"<latest input release>","retrieved_at_utc":"<retrieved>","vintage":"<vintage date>",
   "source":"FRED PCEPILFE/UNRATE/NROU/GDPPOT; EFFR 3.875 mid","timing":"publication","value_status":"vendor_derived","stale":false,"note":"never thresholded"},
  {"name":"Recession probit (E-T coefficients)","series_id":"RECESSION_PROBIT_ET","value":0.095,"obs_date":"<last input date>",
   "available_at_utc":"<latest input release>","retrieved_at_utc":"<retrieved>","vintage":null,
   "source":"FRED T10Y3M; published coefficients","timing":"publication","value_status":"vendor_derived","stale":false,"note":"last read in Q1a"},
  {"name":"Payrolls, 2025 monthly average (k)","series_id":"PAYEMS","value":9.7,"first_release":119.4,"latest":9.7,"obs_date":"2025-12-01",
   "available_at_utc":"<release instant>","retrieved_at_utc":"<retrieved>","vintage":"<vintage date>","vintage_date":"<vintage date>",
   "source":"FRED/ALFRED PAYEMS","timing":"publication","value_status":"revised","stale":false,"note":"known then vs known now"}]}
```

### C.5 `quantgen/model_card_header.macro.v2.0` (SPEC L3927-3992)

"QUANTGEN's cards already hold a hypothesis, a rule, a data span, pre-registered costs, a seed, every test line, the decision and an md5 of the results (public page). These schemas are a **proposed** superset for macro cards. Map them onto the app's actual card format; do not run a parallel registry." (L3911)

```json
{"$id":"quantgen/model_card_header.macro.v2.0","type":"object","$ref":"#/$defs/fields","unevaluatedProperties":false,
 "$defs":{"fields":{"type":"object",
  "required":["card_id","family_id","rule_id","revision","class","claim","claim_type","label","build_status_on_pass","tier","created_utc","header_md5",
              "gate_package_version","gate_package_md5","hypothesis","mechanism","rule","parameters","searched_parameters","estimator",
              "instrument_book","rebalance","no_trade_band","notional_nav","fill_model","costs","data","history_first_close","data_span",
              "cash_convention","episode_rule_version","start_band","midpoint_halves","regime_lines","primary_oos_line","printed_lines",
              "comparator","benchmarks","checks","ledger_hash_at_registration","N_raw_at_registration","timing","outcomes","seed"],
  "properties":{
   "card_id":{"type":"string"},"family_id":{"type":"string","description":"assigned by rule (R-23)"},"rule_id":{"type":"string"},
   "revision":{"type":"integer","minimum":1},"class":{"enum":["CARD-O","CARD-P"]},
   "claim":{"type":"string","description":"verbatim claim text (§8.4)"},"claim_type":{"enum":["outperformance","protection","diversification"]},
   "label":{"type":["string","null"],"description":"the text displayed with the verdict, byte-identical to the rule's label"},
   "build_status_on_pass":{"enum":["BUILD_NOW","BUILD_AS_INSURANCE"]},"tier":{"enum":["A","B","C"]},
   "created_utc":{"type":"string","format":"date-time"},
   "header_md5":{"type":"string","description":"md5 of the header fields, committed before the run"},
   "gate_package_version":{"type":"string","description":"the frozen v2 package (§7 gate.package.version)"},
   "gate_package_md5":{"type":"string","description":"gate.package.definitions_md5 at the freeze (§8.1.3)"},
   "hypothesis":{"type":"string"},"mechanism":{"type":"string","description":"the second-moment mechanism (red line P5)"},
   "rule":{"type":"string"},"parameters":{"type":"object"},"searched_parameters":{"type":"array","items":{"type":"string"}},
   "estimator":{"type":"string","description":"e.g. sma20; a change is a counted revision (R-30)"},
   "instrument_book":{"enum":["KRX_ETF_line","KRX_stock_book","KOSPI200_futures","mini_KOSPI200_futures","CME_micro_ES","US_shares_KIS","KRX_listed_SP500_ETF","crypto_venue","FX_KRX_USD_futures","FX_broker_spot","multi_line"],
                      "description":"R-26; KRX_stock_book is never a market-gross scalar; KRX_listed_SP500_ETF only under D5"},
   "instrument_lines":{"type":["array","null"],"items":{"type":"object","required":["market","instrument_book"],
      "properties":{"market":{"type":"string"},"instrument_book":{"type":"string"}}}},
   "rebalance":{"enum":["daily","weekly","monthly"]},
   "no_trade_band":{"enum":[0.0,0.10],"description":"0.10 only on KRX_stock_book and US_shares_KIS (R-26)"},
   "notional_nav":{"type":"number","exclusiveMinimum":0,"description":"KRW; = sleeves.<market>.notional_nav at commit (R-26)"},
   "nav_fx":{"type":["object","null"],"properties":{"series":{"type":"string"},"history":{"type":"string"},"conversion_instant":{"type":"string"},
      "role":{"enum":["acting_exposure","forward_sim"],"description":"the role of the book it values (R-19 rule 5)"}}},
   "fill_model":{"type":"string","description":"R-27, e.g. KRX_close_auction"},
   "roll_calendar":{"type":["object","null"],"description":"futures books only"},
   "costs":{"type":"object","required":["per_side","floor","stress","stress_line"],
      "properties":{"per_side":{"const":"read_from_gate"},"floor":{"const":"tick_floor"},"stress":{"const":2.0},"stress_line":{"const":"printed"},
        "schedule":{"type":["array","null"],"items":{"type":"object","required":["cost_class"],
           "properties":{"from":{"type":"string","format":"date"},"to":{"type":"string","format":"date"},"cost_class":{"type":"string"}}}},
        "printed_lines":{"type":"array","items":{"type":"string"}}}},
   "data":{"type":"object","required":["source","value_status"],
      "properties":{"source":{"type":"string"},"value_status":{"enum":["official_close","vendor_close"]},"history_file":{"type":"string"},
        "reconciliation":{"type":"string"},"golden_tolerance":{"type":"string"},"saturday_sessions_before":{"type":["string","null"],"format":"date"}}},
   "history_first_close":{"type":"string","format":"date","description":"gate.evaluation.history_start of the card's market (R-22)"},
   "data_span":{"type":"object","required":["start","end"],"properties":{"start":{"type":"string"},
      "end":{"type":"string","format":"date","description":"the last official close before the header commit; never 'latest'"}}},
   "cash_convention":{"type":"object","required":["returns","cash_series"],
      "properties":{"returns":{"const":"excess"},"cash_series":{"type":"string"},"day_count":{"const":"act_365"}}},
   "episode_rule_version":{"type":"string"},
   "start_band":{"type":["object","null"],"required":["shape","starts","require"],
      "properties":{"shape":{"enum":["default","R-06_KR","decade_spaced"]},"from":{"type":"string"},"to":{"type":"string"},
        "step":{"enum":["month","decade"]},"starts":{"type":"integer","minimum":1},
        "require":{"type":"object","properties":{"no_reject":{"const":true},"pass_share_min":{"enum":["2/3","4/5"]}}}}},
   "midpoint_halves":{"type":["object","null"],"required":["split","split_date","require"],
      "properties":{"split":{"const":"calendar_midpoint"},"split_date":{"type":"string","format":"date"},"require":{"const":"no_reject"}}},
   "gating_lines":{"type":["object","null"],"additionalProperties":{"type":["string","object"]}},
   "regime_lines":{"const":"from_R20_tags"},
   "primary_oos_line":{"type":"string"},
   "printed_lines":{"type":"array","items":{"type":"string"}},
   "comparator":{"enum":["S_same_average_exposure","overlay_off"]},
   "benchmarks":{"type":"array","items":{"enum":["buy_and_hold","overlay_off","static_same_avg_exposure","ewma_derisk","current_recommended_book"]}},
   "checks":{"type":"string","description":"gate_package_<version>"},
   "claim_lines":{"type":["array","null"],"items":{"type":"object"}},
   "pooling_rule":{"type":["object","null"]},
   "ledger_hash_at_registration":{"type":"string"},"N_raw_at_registration":{"type":"integer","minimum":1},
   "timing":{"type":"object","required":["decision","inputs"],"properties":{"decision":{"const":"close_t_earn_t_plus_1"},"inputs":{"type":"object"}}},
   "live_feeds":{"type":["array","null"],"items":{"type":"string"}},
   "outcomes":{"type":"object","description":"what PASS, INSUFFICIENT_DATA and REJECT lead to"},
   "owner_decisions":{"type":"object","description":"owner-decision keys the card depends on, with their values"},
   "seed":{"type":"integer"}}}}}
```

Optional header properties (8): `instrument_lines`, `nav_fx`, `roll_calendar`, `gating_lines`, `claim_lines`, `pooling_rule`, `live_feeds`, `owner_decisions` (conditionally required by B4 H10/H11 and at M7).

### C.6 `quantgen/model_card.macro.v2.0` (header ∪ results; SPEC L3996-4084)

"New in 2.0 (a card validates only with all of them)" (L3915-3924): `family_id`, `ledger_hash_at_registration` (header) and `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `V_null` and `selection_factor` = {value, rule: computed_by_step3, alt_value} (result; R-23); `power {se_hac, se_blk250, se_plateau, mde80, power_at_0p05, power_at_0p10, …}` (R-24); `timing_profile` (a result; R-34); `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `nav_fx` (R-26); `cash_convention`, `history_first_close`, `data_span` with a fixed end, `start_band`, `midpoint_halves`, `episode_rule_version` (R-22); the stability results `start_band_results`, `midpoint_halves_results`, `regime_line_results`, and `gjr_null_pct`; `gate_package_version` and `gate_package_md5`, `build_status_on_pass`, `disposition`, `label`, `owner_decisions`; the remaining header fields of §8.4: `claim` with `claim_type`, `estimator`, `fill_model` (and `roll_calendar` for futures), `costs`, `data`, `regime_lines`, `primary_oos_line`, `printed_lines`, `comparator`, `benchmarks`, `checks` and `outcomes`; the reproducibility fields `git_hash`, `config_hash`, `data_snapshot_id` and `knowledge_utc` (T-REPRO-01a).

```json
{"$id":"quantgen/model_card.macro.v2.0","type":"object",
 "allOf":[{"$ref":"model_card_header.macro.v2.0#/$defs/fields"}],
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
             "verdict","verdict_reason","caps_applied","verdict_at_f1","verdict_at_f_neff","disposition","first_failed_check","permitted_fix",
             "ledger_hash_at_run","N_raw","N_clusters","N_equiv","N_hat_linear","N_eff","E_max_sim","V_null","V_trials","selection_factor",
             "power","timing_profile","episodes","start_band_results","midpoint_halves_results","regime_line_results","gjr_null_pct",
             "costs_per_side","cost_stress","tests","printed","lag_audit_violations","results_md5"],
 "properties":{
  "schema":{"const":"quantgen.model_card.macro"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "verdict_reason":{"type":["string","null"],"description":"a §8.1.1 reason code or the failed check's id"},
  "caps_applied":{"type":"array","items":{"type":"string"}},
  "verdict_at_f1":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "verdict_at_f_neff":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "disposition":{"enum":["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]},
  "first_failed_check":{"type":["string","null"]},
  "permitted_fix":{"enum":[null,"widen_grid","lengthen_holding","extend_history","repair_rerun"]},
  "ledger_hash_at_run":{"type":"string"},
  "N_raw":{"type":"integer","minimum":1},"N_clusters":{"type":"integer","minimum":1},"N_equiv":{"type":"number","minimum":1},
  "N_hat_linear":{"type":"number","minimum":1},"N_eff":{"type":"number","minimum":1},"E_max_sim":{"type":"number"},
  "V_null":{"type":"number","exclusiveMinimum":0},"V_trials":{"type":["number","null"]},
  "selection_factor":{"type":"object","required":["value","rule","alt_value"],
     "properties":{"value":{"type":"number","minimum":1},"rule":{"const":"computed_by_step3"},"alt_value":{"type":"number","minimum":1}}},
  "power":{"type":"object","required":["se_hac","se_blk250","se_plateau","mde80","power_at_0p05","power_at_0p10"],
     "properties":{"se_hac":{"type":"number"},"se_blk250":{"type":"number"},"se_plateau":{"type":"number"},"se_curve":{"type":["object","array"]},
       "mde80":{"type":"number"},"power_at_0p05":{"type":"number"},"power_at_0p10":{"type":"number"},"pc3_power_at_0":{"type":["number","null"]},
       "years_to_detect_0p05":{"type":["number","null"]},"underpowered":{"type":"boolean"}}},
  "timing_profile":{"type":"object","required":["lags","strict","LP","LF","FR","label","live_feeds"],
     "properties":{"lags":{"type":"array","items":{"type":"object","required":["L","dSR","dMDD","dES21","timing_class"],
         "properties":{"L":{"type":"integer","minimum":-1,"maximum":3},"dSR":{"type":"number"},"dMDD":{"type":"number"},"dES21":{"type":"number"},
           "lag_audit":{"type":["object","null"]},"timing_class":{"enum":["VALUE","NON-COMPLIANT","COMPLIANT"]}}}},
       "strict":{"type":["object","null"]},"LP":{"type":"number"},"LF":{"type":["number","null"]},"FR":{"type":["number","null"]},
       "label":{"enum":["robust","timing_fragile"]},"live_feeds":{"type":"array","items":{"type":"string"}}}},
  "episodes":{"type":"array","items":{"type":"object","required":["peak","trough","depth","open"],
     "properties":{"peak":{"type":"string","format":"date"},"trough":{"type":"string","format":"date"},"depth":{"type":"number"},
       "window":{"type":"array","items":{"type":"string","format":"date"}},"benefit_vs_S":{"type":["number","null"]},"share":{"type":["number","null"]},
       "regime_tags":{"type":"object"},"post_trough_63":{"type":["number","null"]},"open":{"type":"boolean"}}}},
  "cost_episodes":{"type":"array","items":{"type":"object"}},
  "pc4_section_8_6":{"type":["object","null"]},
  "start_band_results":{"type":["object","null"],"required":["starts","verdicts","n_pass","n_starts","n_reject","floor_pass"],
     "properties":{"starts":{"type":"array","items":{"type":"string"}},"verdicts":{"type":"array","items":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]}},
       "n_pass":{"type":"integer","minimum":0},"n_starts":{"type":"integer","minimum":1},"n_reject":{"type":"integer","minimum":0},"floor_pass":{"type":"boolean"}}},
  "midpoint_halves_results":{"type":["object","null"],"required":["h1","h2"],
     "properties":{"h1":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},"h2":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]}}},
  "regime_line_results":{"type":"array","items":{"type":"object","required":["line","span","verdict","gated"],
     "properties":{"line":{"type":"string"},"span":{"type":"string"},"verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
       "numbers":{"type":"object"},"gated":{"type":"boolean"}}}},
  "gjr_null_pct":{"type":["number","null"],"minimum":0,"maximum":100},
  "costs_per_side":{"type":"object","required":["table_bp","floor_bp","applied_bp"],
     "properties":{"table_bp":{"type":"number"},"floor_bp":{"type":"number"},"applied_bp":{"type":"number"},
       "stress_line":{"type":["object","null"]},"roll_cost_line":{"type":["object","null"]}}},
  "cost_stress":{"const":2.0},
  "claim_line_results":{"type":["object","null"],"properties":{"stacked_dMDD":{"type":"number"},"band":{"type":"array","items":{"type":"number"}},"pass":{"type":"boolean"}}},
  "pooling":{"type":["object","null"],"properties":{"rule":{"type":"string"},"n_onsets_own":{"type":"integer"},"n_onsets_pooled":{"type":"integer"}}},
  "snooping":{"type":["object","null"],"properties":{"n_variants":{"type":"integer"},"share_dMDD_ge_3pp":{"type":"number"},"deflated_prob_sr":{}}},
  "settling_run":{"type":["object","null"],"properties":{"span":{"type":"string"},"verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
     "pc1_prime_1x":{"type":"boolean"},"pc1_prime_2x":{"type":"boolean"},"starts":{"type":"array","items":{"type":"string"}},
     "n_pass":{"type":"integer"},"n_starts":{"type":"integer"},"n_reject":{"type":"integer"},"midpoint_halves":{"type":["object","null"]}}},
  "contracts_path":{"type":["array","null"]},
  "forecast_eval":{"type":["object","null"],"properties":{"qlike_mcs_p":{"type":"object","additionalProperties":{"type":"number"}},
     "mse_mcs_p":{"type":"object","additionalProperties":{"type":"number"}},"christoffersen_p":{"type":["number","null"]},"es_z2":{"type":["number","null"]},
     "fan_pit_p":{"type":["number","null"]},"vol_of_vol":{"type":["number","null"]},"dMDD_vs_sma20":{"type":["number","null"]},"dSR_vs_sma20":{"type":["number","null"]}}},
  "forward_record":{"type":["object","null"],"description":"falsification alarms only (R-25); can never raise the verdict","properties":{
     "start_utc":{"type":"string","format":"date-time"},"first_registered_utc":{"type":"string","format":"date-time"},"months":{"type":"number"},
     "dSR_vs_S":{"type":["number","null"]},"dES21":{"type":["number","null"]},"dMDD":{"type":["number","null"]},"cusum_S":{"type":["number","null"]},
     "alarms":{"type":"array","items":{"type":"object"}},"switches":{"type":["integer","null"]},"switch_p99":{"type":["number","null"]},
     "lag_audit_violations":{"type":"integer","minimum":0},"demoted":{"type":"boolean"},"demotion_reason":{"type":["string","null"]},
     "honesty_line":{"type":"string"},"missed_decisions":{"type":"integer","minimum":0},"gaps":{"type":"array","items":{"type":"object"}}}},
  "tests":{"type":"object","description":"one entry per gate step (1-9) and per protective check (§8.7); the key set is closed, and so is every entry whose fields a rule enumerates (R-21, R-22, R-23, R-24)","properties":{
     "step1":{"type":"object"},"step2":{"type":"object"},
     "step3":{"type":"object","properties":{"deflated_dSR":{},"at_N_raw":{},"at_N_hat_linear":{},"borderline":{},"break_even_N":{},"z_check":{},"by_q":{},"dsr_vs0":{},"psr_vs_S":{},"selection_factor":{},"pass":{}}},
     "step4":{"type":"object","properties":{"pbo":{},"winner_loses_share":{},"pbo_null":{},"slope":{},"n_configs":{}}},
     "step5":{"type":"object"},"step6":{"type":"object"},"step7":{"type":"object"},"step8":{"type":"object"},"step9":{"type":"object"},
     "PC1p":{"type":"object","properties":{"legs":{"type":"array","items":{"type":"object","properties":{"h":{},"dES":{},"z":{},"p":{},"p_adj":{},"pass":{}}}},
       "two_x":{"type":"array","items":{"type":"object","properties":{"h":{},"dES":{},"z":{},"p":{},"p_adj":{},"pass":{}}}}}},
     "PC2":{"type":"object","properties":{"ratio_daily":{},"ratio_horizon":{},"ci90":{},"horizon_used":{},"pass":{}}},
     "PC3":{"type":"object","properties":{"dSR":{},"p10":{},"pPW":{},"block_PW":{},"p_ni":{},"p_adj":{},"point_2x":{},"pass":{},"p_lw":{},"p_hac":{},"block":{},"n_blocks":{}}},
     "PC4":{"type":"object","properties":{"positive":{},"n":{},"max_share":{}}},
     "PC5":{"type":"object"},"PC6":{"type":"object"},"PC7":{"type":"object"}}},
  "printed":{"type":"object","description":"never gated","properties":{
     "dMDD":{},"dCDaR95":{},"dES99":{},"bands":{},"placebo_panel":{},"tuw":{},"reentry_lag":{},"post_trough":{},"rolling_5y":{},
     "with_risk_layer":{},"lo_sr_20":{},"lo_sr_all":{},"by_q":{},"hl_haircut":{},"exec_variants":{},"overnight_intraday":{},
     "turnover_by_regime":{},"stress_cost":{},"roll_cost":{},"ban_basis":{},"fill_tracking_error":{},"binding_share":{},
     "binding_shares":{},"n_halts":{},"persistence_check":{}}},
  "lag_audit_violations":{"const":0,"description":"L >= 1 and strict rows only (R-34)"},
  "results_md5":{"type":"string"}},
 "unevaluatedProperties":false}
```

Optional result properties (9): `cost_episodes`, `pc4_section_8_6`, `claim_line_results`, `pooling`, `snooping`, `settling_run`, `contracts_path`, `forecast_eval`, `forward_record`.
Validation rules (L4087-4092) are encoded in B4 (H1-H13, K1-K8).

### C.7 `quantgen/governance_event.v2.0` (one JSON line per event; SPEC L4099-4110)

```json
{"$id":"quantgen/governance_event.v2.0","type":"object",
 "required":["schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5"],
 "properties":{
  "schema":{"const":"quantgen.governance_event"},"schema_version":{"const":"2.0"},
  "event_id":{"type":"string"},"utc":{"type":"string","format":"date-time"},
  "kind":{"enum":["halt","rearm","book_state","demotion","package_freeze","package_redesign","header_commit","owner_ruling","calendar_change",
                  "notional_change","admissibility_reweight","binding_share_recompute","binding_change","record_reset","verdict_integrity"]},
  "book_id":{"type":["string","null"]},"rule_id":{"type":["string","null"]},"key":{"type":["string","null"]},
  "old":{"description":"the value before the event (any JSON type)"},"new":{"description":"the value after the event (any JSON type)"},
  "actor":{"enum":["owner","operator","runtime","harness","council"]},
  "reason":{"type":"string"},"refs":{"type":"array","items":{"type":"string"}},
  "prev_row_md5":{"type":["string","null"],"description":"md5 of the previous line; null only on the first line"}}}
```

Example line (a book's first arming; SPEC L4116-4118) — fixture `governance_event`:

```json
{"schema":"quantgen.governance_event","schema_version":"2.0","event_id":"<uuid>","utc":"2026-10-02T06:41:05Z","kind":"book_state",
 "book_id":"recommended:KR","rule_id":null,"key":"engine_state","old":"DISARMED","new":"ARMED","actor":"runtime",
 "reason":"every acting input bound to the book fresh and past warm-up; calendars cover 60 sessions or more","refs":["§3.8"],"prev_row_md5":"<md5>"}
```

### C.8 The §8.4 example header (R-06 KR, the formal long-history card; SPEC L4901-4964) — fixture `model_card_header`

"It validates against `model_card_header.macro` (T-SCHEMA-01); `<…>` values are typed placeholders filled at commit" (L4898). Store the parsed form in the JSON fixture (`yaml.safe_load` of this block gives 46 keys = the 44 required + `gating_lines` + `owner_decisions`; `label` equals `claim` byte for byte through the `&label`/`*label` anchor; quoted dates stay strings; `episode_rule_version` is the string `"1"`; `no_trade_band` is `0.0`; verified VALID after placeholder fill).

```yaml
card_id: MACRO-R06-KR-ETF
family_id: R-06                               # assigned by rule (QC_modules.csv; R-23)
rule_id: R-06-KR-VT20
revision: 2                                   # v1.2's 2016-26 card was revision 1; new span and conventions
class: CARD-P
claim: &label "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent."
label: *label                                 # byte-identical to the R-06 label (UTF-8)
claim_type: protection
build_status_on_pass: BUILD_AS_INSURANCE
tier: A                                       # continuous; objective episodes (18 on 1997-2026)
created_utc: "<commit time>"
header_md5: "<md5 of the header fields, committed before the run>"
gate_package_version: "2.0.0"
gate_package_md5: "<gate.package.definitions_md5 at the freeze>"
hypothesis: "VT20 lowers tail losses vs a same-average-exposure static book without a Sharpe loss beyond 0.10"
mechanism: "variance reduction (variance ratio 0.59); implicitly short the rebound premium (timing return -1.8%/yr)"
rule: "vt = min(1.0, 0.20 / sigma_SMA20(t)); decided at the KRX close of t (available_at <= close_print_bound_utc(KR, t)); earns from t+1"
parameters: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, floor: none}
searched_parameters: []                       # PC-6 neighbours come from the frozen pc6_axes, never from the header (R-21)
estimator: sma20                              # a COMB revision would be a new counted revision (R-30)
instrument_book: KRX_ETF_line                 # KODEX 200; tick floor applies
notional_nav: "<sleeves.KR.notional_nav at commit, KRW>"   # owner-signed (R-26); a futures line only if one mini contract <= 5% (about KRW 1bn+)
rebalance: daily
no_trade_band: 0.0                            # bands only on stock and US-share books
fill_model: KRX_close_auction                 # R-27
costs:
  per_side: read_from_gate
  floor: tick_floor
  stress: 2.0
  stress_line: printed
  schedule:                                   # no ETF existed before Oct-2002; a declared cost may only rise (P10)
    - {to: "<the day before the KODEX 200 listing, from the KRX listing record>", cost_class: futures}
    - {from: "<the KODEX 200 listing date>", cost_class: krx_etf}
  printed_lines: [krx_etf_3bp_throughout]     # the DLA-K8 / G-KR-L01 convention, printed for comparison
data: {source: KRX_official_closes, value_status: official_close, history_file: "<the frozen KRX official-close fixture>",
       reconciliation: "R-01: index 1 bp, stocks exact", golden_tolerance: "Level-2, only for I-16's raw-flag data check vs G-KR-L01; the formal run's differences are printed, never gated",
       saturday_sessions_before: "1998-12-12"}
history_first_close: "1997-04-01"             # gate.evaluation.history_start KR (R-22)
data_span: {start: first_close_plus_20_session_warmup, end: "2026-10-02"}   # gate.evaluation.data_cutoff.KR (R-22): fixed now, never "latest"
cash_convention: {returns: excess, cash_series: BOK_CALL_RATE, day_count: act_365}
episode_rule_version: "1"                     # alternating >= 20% on KOSPI's own closes; Sep-2026 is not an episode
gating_lines:
  full_span: v2_PASS
  etf_era: {from: "<the first day of the first full month after the KODEX 200 listing>", to: "2025-12-31", require: v2_PASS}
start_band: {shape: R-06_KR, from: "1997-05", to: "1999-12", step: month, starts: 32, require: {no_reject: true, pass_share_min: "2/3"}}
midpoint_halves: {split: calendar_midpoint, split_date: "<the calendar midpoint of the fixed span>", require: no_reject}
regime_lines: from_R20_tags
printed_lines: [etf_era_to_present, pre_design_2002-10_to_2015-12, "1997_to_2002_alone", "2016_to_2025_alone",
                rolling_decades, pc4_under_section_8_6, ewma094_line, timing_return, years_lagging_S,
                h1_2026_bull_tax, median_reentry_lag, per_regime_table, with_risk_layer]
primary_oos_line: etf_era
comparator: S_same_average_exposure
benchmarks: [buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk]
checks: gate_package_2.0.0
ledger_hash_at_registration: "<md5 of the R-06 family ledger at commit>"
N_raw_at_registration: "<R-06 ledger row count at commit>"
# selection_factor: never declared here; step3() computes it at the run and the card prints f = 1 and f = N_eff (R-23)
timing:
  decision: close_t_earn_t_plus_1
  inputs: {KOSPI: {series: KOSPI_OFFICIAL_CLOSE, value_status: official_close, available_at: "<= close_print_bound_utc(KR, t)"}}
outcomes: {PASS: BUILD-AS-INSURANCE, INSUFFICIENT_DATA: specification_book_control_regated_on_new_objective_episode,
           REJECT: archive}               # the forward record is a falsification alarm only (R-25)
owner_decisions: {risk_layer.korea_caps.template: msci_25_50}   # D1; caps are excluded from the card books and printed (R-22 rule 6)
seed: 11
```

### C.9 Synthetic result block for T-SCHEMA-02 / T-SCHEMA-03 (not SPEC text; built for this brief; `header example (filled) ∪ this` validates against `model_card.macro` — verified). Values are schema-shaped fillers, not results; fixture `card_results_synthetic.json`

```json
{
 "schema": "quantgen.model_card.macro",
 "schema_version": "2.0",
 "read_only": true,
 "generated_at_utc": "2026-10-02T06:40:45Z",
 "knowledge_utc": "2026-10-02T06:40:45Z",
 "git_hash": "00000000000000000000000000000000",
 "config_hash": "00000000000000000000000000000000",
 "data_snapshot_id": "00000000000000000000000000000000",
 "verdict": "INSUFFICIENT_DATA",
 "verdict_reason": "underpowered",
 "caps_applied": [],
 "verdict_at_f1": "INSUFFICIENT_DATA",
 "verdict_at_f_neff": "INSUFFICIENT_DATA",
 "disposition": "SPECIFICATION_ONLY",
 "first_failed_check": "PC3",
 "permitted_fix": null,
 "ledger_hash_at_run": "00000000000000000000000000000000",
 "N_raw": 3,
 "N_clusters": 2,
 "N_equiv": 1.3,
 "N_hat_linear": 2.1,
 "N_eff": 2,
 "E_max_sim": 0.5,
 "V_null": 1.0,
 "V_trials": null,
 "selection_factor": {"value": 1.26, "rule": "computed_by_step3", "alt_value": 1.49},
 "power": {"se_hac": 0.1, "se_blk250": 0.1, "se_plateau": 0.1, "se_curve": {"250": 0.1}, "mde80": 0.3, "power_at_0p05": 0.1, "power_at_0p10": 0.2, "pc3_power_at_0": 0.5, "years_to_detect_0p05": 99.0},
 "timing_profile": {"lags": [{"L": 1, "dSR": 0.0, "dMDD": 0.0, "dES21": 0.0, "lag_audit": null, "timing_class": "COMPLIANT"}], "strict": null, "LP": 0.0, "LF": null, "FR": null, "label": "robust", "live_feeds": []},
 "episodes": [{"peak": "2026-06-22", "trough": "2026-07-30", "depth": -0.386, "window": ["2026-06-22", "2026-07-30"], "benefit_vs_S": 0.01, "share": 0.1, "regime_tags": {}, "post_trough_63": null, "open": false}],
 "cost_episodes": [{}],
 "pc4_section_8_6": {"positive": 3, "n": 4, "max_share": 0.493},
 "start_band_results": {"starts": ["1997-05"], "verdicts": ["INSUFFICIENT_DATA"], "n_pass": 0, "n_starts": 1, "n_reject": 0, "floor_pass": false},
 "midpoint_halves_results": {"h1": "INSUFFICIENT_DATA", "h2": "INSUFFICIENT_DATA"},
 "regime_line_results": [{"line": "etf_era", "span": "2002-11..2025-12", "verdict": "INSUFFICIENT_DATA", "numbers": {}, "gated": true}],
 "gjr_null_pct": 87.0,
 "costs_per_side": {"table_bp": 3.0, "floor_bp": 0.3, "applied_bp": 3.0, "stress_line": null, "roll_cost_line": null},
 "cost_stress": 2.0,
 "claim_line_results": {"stacked_dMDD": 0.149, "band": [0.0, 0.2], "pass": true},
 "pooling": {"rule": "pooled_onsets", "n_onsets_own": 5, "n_onsets_pooled": 45},
 "snooping": {"n_variants": 10, "share_dMDD_ge_3pp": 0.5, "deflated_prob_sr": 0.5},
 "settling_run": {"span": "1926-07..2026-08", "verdict": "INSUFFICIENT_DATA", "pc1_prime_1x": true, "pc1_prime_2x": false, "starts": ["1926-07"], "n_pass": 0, "n_starts": 10, "n_reject": 0, "midpoint_halves": null},
 "contracts_path": [1, 1, 2],
 "forecast_eval": {"qlike_mcs_p": {"1": 0.0005, "5": 0.0005, "21": 0.0005}, "mse_mcs_p": {"1": 0.2}, "christoffersen_p": 0.2, "es_z2": 0.1, "fan_pit_p": 0.11, "vol_of_vol": 0.3, "dMDD_vs_sma20": 0.0, "dSR_vs_sma20": 0.0},
 "forward_record": {"start_utc": "2026-10-02T06:40:45Z", "first_registered_utc": "2026-10-02T06:40:45Z", "months": 0.0, "dSR_vs_S": null, "dES21": null, "dMDD": null, "cusum_S": null, "alarms": [], "switches": null, "switch_p99": null, "lag_audit_violations": 0, "demoted": false, "demotion_reason": null, "honesty_line": "falsification alarm only", "missed_decisions": 0, "gaps": []},
 "tests": {"step1": {}, "step2": {"p_lw": 0.1, "p_hac": 0.1, "block": 250, "n_blocks": 10}, "step3": {"deflated_dSR": 0.98, "at_N_raw": 0.9, "at_N_hat_linear": 0.947, "borderline": true, "break_even_N": 7, "z_check": 1.33, "by_q": {}, "dsr_vs0": 0.9, "psr_vs_S": 0.9, "selection_factor": 1.26, "pass": true}, "step4": {"pbo": 0.1, "winner_loses_share": 0.03, "pbo_null": 0.5, "slope": -1.0, "n_configs": 8}, "step5": {"p_lw": 0.1, "p_hac": 0.1, "block": 250, "n_blocks": 10}, "step6": {}, "step7": {}, "step8": {}, "step9": {}, "PC1p": {"legs": [{"h": 21, "dES": 0.0165, "z": 1.0, "p": 0.1, "p_adj": 0.13, "pass": false}], "two_x": [{"h": 21, "dES": 0.0165, "z": 1.0, "p": 0.1, "p_adj": 0.13, "pass": false}]}, "PC2": {"ratio_daily": 0.95, "ratio_horizon": 0.9, "ci90": [0.8, 1.0], "horizon_used": 21, "pass": true}, "PC3": {"dSR": 0.006, "p10": 0.07, "pPW": 0.078, "block_PW": 30, "p_ni": 0.078, "p_adj": 0.098, "point_2x": 0.0, "pass": false, "p_lw": 0.07, "p_hac": 0.07, "block": 30, "n_blocks": 240}, "PC4": {"positive": 14, "n": 18, "max_share": 0.174}, "PC5": {}, "PC6": {}, "PC7": {}},
 "printed": {"dMDD": 0.0, "dCDaR95": 0.0, "dES99": 0.0, "bands": {}, "placebo_panel": {"n": 20, "passes": 1}, "tuw": 0.0, "reentry_lag": 0, "post_trough": {}, "rolling_5y": [], "with_risk_layer": {}, "lo_sr_20": 0.0, "lo_sr_all": 0.0, "by_q": {}, "hl_haircut": 0.0, "exec_variants": {"A": 0, "B": 0, "C": 0}, "overnight_intraday": {}, "turnover_by_regime": {}, "stress_cost": 0.0, "roll_cost": 0.0, "ban_basis": null, "fill_tracking_error": 0.0019, "binding_share": 0.19, "binding_shares": {}, "n_halts": 24, "persistence_check": {}},
 "lag_audit_violations": 0,
 "results_md5": "00000000000000000000000000000000"
}
```

---

## D. Tests (all hermetic; runner pattern: `tests/macro_acceptance.py::tests()`; every write goes to a `tempfile.mkdtemp()` root; registry rows: tier `fast`, `runs_from` as below)

Feasibility classes: **SYNTH** = inline/synthetic fixtures only; **REFDATA** = needs frozen reference data not on this machine; **OWNER** = needs owner input/credentials/live sessions.

### D.1 T-SCHEMA-01 — runs_from M0 (L5550) — SYNTH

Row (L5669): "Every example in this spec validates against its §6 schema: the §6 examples and the §8.4 header (against `model_card_header.macro`), a `<…>` placeholder being replaced by a typed sample first. The schemas load into one registry keyed by `$id`, with the closed-object rule of §6. A missing required field fails; an undeclared field fails." (R-32 acceptance L3372 same.)

Fixture `tests/fixtures/macro/schema_examples.json` = `{"macro_state": C.1 example, "overlay_decision": C.2 example, "event_calendar": C.3 envelope with events [FOMC, NFP], "context_log": C.4 example, "governance_event": C.7 example, "model_card_header": C.8 parsed}` — placeholders kept as written. There is no `model_card.macro` example in the SPEC (F-11).

Assertions:
1. `registry().by_id` has exactly the 7 `$id`s of §C; `overlay_decision.inputs.items.$ref` (`macro_state.v2.0#/$defs/input`) and `model_card.macro.allOf[0].$ref` (`model_card_header.macro.v2.0#/$defs/fields`) resolve.
2. For each of the 6 fixtures: `validate(id, fill(id, fixture)) == []`. Each of the 2 event entries also validates against `event_calendar.v2.0#/$defs/event`.
3. Missing required: for each fixture and each name in its schema's top-level `required` (header: `$defs.fields.required`), deleting the key yields ≥ 1 error at `"/" + name`. Same for nested required lists at least once each: `inputs[0]` (20 names), `vol` (13), `flags` (12), `runtime[0]` (5), `lag_audit` (2), `multipliers[0]` (4), `$defs.card` (6), `events[0]` (7), `events[0].windows[0]` (4), `items[0]` (11), header `costs` (4), `data` (2), `data_span` (2), `cash_convention` (2), `start_band` (3), `midpoint_halves` (3), `timing` (2).
4. Undeclared: adding key `zzz` at the top level of each fixture → error `("/zzz","undeclared")`; also inside `inputs[0]`, `vol`, `flags`, `annotations`, `concentration`, `runtime[0]`, `alerts[]` item, `multipliers[0]`, `vol_scale_card`, `events[0]`, `windows[0]`, context `items[0]`, header `costs`, `data`, `start_band.require`.
5. Open positions accept anything: `extras.zzz` (macro_state, overlay_decision, context_log); header `parameters.zzz`, `outcomes.zzz`, `owner_decisions.zzz`, `timing.inputs.zzz`. Maps validate their values: `owner_decisions["x"] = {"decision":"D9",…}` → enum error; `by_book["x"] = {}` → 3 required errors; `rule_versions["R-99"] = 1` → type error.
6. Header carrying a result field (`selection_factor`, `timing_profile`, `forward_record`, `start_band_results` each in turn) → `("/<name>","undeclared")`.
7. Bounds samples: `vol.vt_weight_next = 1.01` → maximum 1; `multipliers[0].value = 0.49` → minimum 0.5; `composition = "product"` → const; `ladder = 0.25` → enum; `overlay_cap = 1.5` → const; `read_only = 1` → const (bool ≠ int); `flags.gap_sessions = -1` → minimum 0; `gap_sessions = 0` with `var_display_scale = 1` valid; `halt.causes = []` → minItems 1; `generated_at_utc = "2026-10-02T06:41:07+00:00"` → format date-time; `decided_session = "2026-10-2"` → format date.
8. Loader guards: a schema copy with keyword `pattern` → `SchemaLoadError`; a dangling `$ref` → `SchemaLoadError`.

### D.2 T-SCHEMA-02 — runs_from M0 — SYNTH

Row (L5670): "`model_card.macro` validates only with `family_id`, `ledger_hash_at_registration` and `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `V_null`, `selection_factor`, `power {se_hac, se_blk250, se_plateau, mde80, power_at_0p05, power_at_0p10}`, `timing_profile`, `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `cash_convention`, `start_band` (acting long-sample cards), `episode_rule_version`, `start_band_results`, `midpoint_halves_results`, `gjr_null_pct` and the reproducibility fields; each removed in turn → refused. `macro_state` inputs carry `value_status`, `session_date` and the provenance fields. `context_log` items carry `series_id`, `vintage`, `retrieved_at_utc`, `value_status` and `stale`." The council wording at L5539 (`ledger_hash`, `linear N̂`, `power {se, mde80}`, "stability lines") is superseded by this row: "the refined row … governs" (L5505: T-SCHEMA-02 "(the §6.5 names)").

Fixture: `card = fill(header example) ∪ C.9`; before any `check_artifact` / `card_issues` / `write_artifact` call the test sets `card["header_md5"] = header_md5(card)` and `card["results_md5"] = results_md5(card)` (the fixture values are fillers, so K5 would otherwise fire). Likewise T-SCHEMA-01 validates the §8.4 header example at schema level (`validate(HEADER_ID, …)`), as its row says; `header_issues` cases first set `header_md5` (H4).
Assertions:
1. `validate(CARD_ID, card) == []`.
2. For each of the 26 names `family_id, ledger_hash_at_registration, ledger_hash_at_run, N_raw, N_clusters, N_equiv, N_hat_linear, N_eff, V_null, selection_factor, power, timing_profile, instrument_book, rebalance, no_trade_band, notional_nav, cash_convention, start_band, episode_rule_version, start_band_results, midpoint_halves_results, gjr_null_pct, git_hash, config_hash, data_snapshot_id, knowledge_utc`: card without it → non-empty errors. For each of the 6 `power` sub-keys: same. (Verified: all 32 removals are refused.)
3. `start_band` (acting long-sample): `header_issues(header with start_band=None, acting_long_sample=True)` and the same with `midpoint_halves=None` → non-empty; with `acting_long_sample=False` and both null → the two fields raise no issue (schema allows null).
4. Kish: no property name in any of the 7 schemas contains `kish` (case-insensitive walk of the registry); `card + {"kish_n": 3.0}` → `("/kish_n","undeclared")`.
5. `macro_state`: removing each of the 20 required keys of `inputs[0]` (incl. `value_status`, `session_date`, `available_at_utc`, `available_at_source`, `retrieved_at_utc`, `content_hash`, `vintage`) → refused; removing each top-level common provenance field (`schema, schema_version, read_only, generated_at_utc, knowledge_utc, git_hash, config_hash, data_snapshot_id`) → refused (F-12).
6. `context_log`: removing each of `series_id, vintage, retrieved_at_utc, value_status, stale` from `items[0]` → refused (`vintage` may be `null` but the key must exist).
7. Conditional card rules K1-K4 with one injected violation each (e.g. `verdict=PASS, disposition=SPECIFICATION_ONLY`; `verdict=REVISE, disposition=RECOMMENDATION`; `disposition=INVARIANT_STEP, family_id="R-06"`; `BUILD_AS_INSURANCE` on `CARD-O`) → `check_artifact(card).status == "refused"` with an error at the field named.

### D.3 T-SCHEMA-03 — runs_from M0 — SYNTH

Row (L5671): "One synthetic artifact or card per rule, built from that rule's "Outputs and schema fields" list, validates against its §6 schema; a field a rule writes that its schema lacks fails the test." (§6 preamble L3503; C-7.)

Fixture (inline in the test): `RULE_OUTPUTS` below — every field named in a rule's Outputs list, transcribed as `<schema>:<pointer>` (`*` = any array index or map key). Formal "Outputs and schema fields" lists exist for R-19…R-31 and R-34 (SPEC L1946-1951, L2080-2084, L2234-2240, L2384-2388, L2507-2510, L2611-2616, L2731-2733, L2852-2856, L2939-2941, L3032-3034, L3121-3123, L3229-3232, L3331-3334, L3450); R-01, R-03, R-04 have an "Output" row (L1494, L1521, L1538); R-08 and R-13 name their fields in the rule text (L1601, L1674). R-32, R-33, R-35 are "short entries" with no Outputs list (L1811); the remaining v1.2 rules name no schema field in their tables (F-15).

Assertions:
1. Static: every pointer of `RULE_OUTPUTS` resolves to a declared position in its schema (walk `properties` / `items` / `additionalProperties` / `$ref` / `allOf`; anything below `extras`, below an object without `properties`, or below `{}` is declared). Verified: 294 of 294 resolve. Negative controls: `macro_state:/flags/nope`, `model_card.macro:/tests/step3/nope`, `model_card.macro:/kish` do not.
2. Dynamic: one synthetic instance per rule validates — start from the T-SCHEMA-01/02 fixtures and set that rule's fields: e.g. R-19 `inputs[0].status = "stale_missed_release"`, `fail_closed = true`, one `alerts[]` item, `runtime[0].halt = {"class":"OPS","reason_code":"acting_input_stale:KOSPI_OFFICIAL_CLOSE","since_utc":…,"rearm_mode":"auto","causes":[{same four}]}`; R-20 `extras.regime_tags`, an event of type `KRX_HOLIDAY_GAP` with `gap_sessions: 2`; R-26 `overlay_decision.extras = {instrument_book, contracts, w_target, w_held, band}`; R-27 `extras = {fill_model, decision_price_source: "official_close"|"snapshot_1519", fill_status: "filled"|"non_fillable_limit_lock"|"carried", flags: ["LP_exempt_auction","inav_residual_gt_30bp"]}`; R-28/R-29 `overlay_decision.forward_sim[] = {rule_id: "R-28"|"R-29", value, card{6 required keys}}`, `macro_state.forward_sim.R28_below_sma10m`; R-30 `vol.estimator = "comb"`, `estimator_gate.status = "challenger_selected"`; R-31 `flags.ladder_step = "step_-8"`, `multipliers[] rule_id "R-31"`, `runtime[].hwm_hard/ref_step`; the L3798 S2 refusal entry completed with `label: null`, `results_md5: null` inside a `market_gross` / `exposure_basis: total` record; card rules (R-21…R-25, R-34 and the card parts of R-20/R-26…R-31) → the C.9 card. (Verified VALID for all of these.)
3. Test-of-the-test: adding one undeclared field to a rule's synthetic instance outside `extras` makes that rule's case fail.

`RULE_OUTPUTS` (generated from the SPEC lists; `{a,b}` = several names under the same parent):

| Rule | Fields (schema: pointers) |
|---|---|
| R-01 | `macro_state:/inputs/*/{value_status, session_date, available_at_utc, retrieved_at_utc, role}`; `macro_state:/lag_audit`; `model_card.macro:/lag_audit_violations` |
| R-03 | `overlay_decision:/{vol_scale, exposure_basis}` |
| R-04 | `overlay_decision:/multipliers/*/{value, rule_id}`; `overlay_decision:/multipliers/*/card/disposition` |
| R-08 | `macro_state:/annotations/vix_ge_vix3m` |
| R-13 | `context_log:/items/*/{vintage, retrieved_at_utc, first_release, latest, vintage_date, timing, stale}` |
| R-19 | `macro_state:/inputs/*/{role, expected_available_utc, stale_deadline_utc, status}`; `macro_state:/{fail_closed, alerts}`; `macro_state:/flags/hedge_reasons`; `context_log:/items/*/stale`; `macro_state:/runtime/*/halt/{class, reason_code}` |
| R-20 | `macro_state:/{decision_utc, effective_session}`; `macro_state:/extras/regime_tags`; `model_card.macro:/regime_line_results`; `event_calendar:/events/*/{kr_open_gap_session, gap_sessions}`; `macro_state:/flags/{kr_open_gap_event, gap_sessions}` |
| R-21 | `model_card.macro:/tests/PC1p/legs/*/{h, dES, z, p, p_adj, pass}`; `model_card.macro:/tests/PC1p/two_x/*/{h, dES, z, p, p_adj, pass}`; `model_card.macro:/tests/PC2/{ratio_daily, ratio_horizon, ci90, horizon_used, pass}`; `model_card.macro:/tests/PC3/{dSR, p10, pPW, block_PW, p_ni, p_adj, point_2x, pass}`; `model_card.macro:/tests/{PC4, PC5, PC6, PC7}`; `model_card.macro:/{caps_applied, verdict, verdict_reason, gjr_null_pct, verdict_at_f1, verdict_at_f_neff}`; `model_card.macro:/printed/{dMDD, dCDaR95, dES99, bands, tuw, reentry_lag, post_trough, rolling_5y, with_risk_layer}`; `model_card.macro:/printed/placebo_panel/{n, passes}` |
| R-22 | `model_card.macro:/{episode_rule_version, regime_line_results, cost_episodes}`; `model_card.macro:/episodes/*/{peak, trough, depth, window, benefit_vs_S, share, regime_tags, post_trough_63, open}`; `model_card.macro:/tests/PC4/{positive, n, max_share}`; `model_card.macro:/pc4_section_8_6/{positive, n, max_share}`; `model_card_header.macro:/{cash_convention, history_first_close, start_band, regime_lines, primary_oos_line}`; `model_card_header.macro:/data_span/{end, start}`; `model_card_header.macro:/midpoint_halves/split_date`; `model_card.macro:/start_band_results/{starts, verdicts, n_pass, n_starts, n_reject, floor_pass}`; `model_card.macro:/midpoint_halves_results/{h1, h2}`; `model_card.macro:/printed/with_risk_layer` |
| R-23 | `model_card_header.macro:/{family_id, ledger_hash_at_registration, N_raw_at_registration}`; `model_card.macro:/{ledger_hash_at_run, N_raw, N_clusters, N_equiv, N_hat_linear, N_eff, E_max_sim, V_null, V_trials}`; `model_card.macro:/selection_factor/{value, rule, alt_value}`; `model_card.macro:/tests/step3/{deflated_dSR, at_N_raw, at_N_hat_linear, borderline, break_even_N, z_check, by_q, dsr_vs0, psr_vs_S, selection_factor, pass}` |
| R-24 | `model_card.macro:/power/{se_hac, se_blk250, se_plateau, se_curve, mde80, power_at_0p05, power_at_0p10, pc3_power_at_0, years_to_detect_0p05}`; `model_card.macro:/tests/step2/{p_lw, p_hac, block, n_blocks}`; `model_card.macro:/tests/step5/{p_lw, p_hac, block, n_blocks}`; `model_card.macro:/tests/PC3/{p_lw, p_hac, block, n_blocks}`; `model_card.macro:/tests/step4/{pbo, winner_loses_share, pbo_null, slope, n_configs}`; `model_card.macro:/printed/{lo_sr_20, lo_sr_all, by_q, hl_haircut}`; `model_card.macro:/verdict_reason` |
| R-25 | `model_card.macro:/forward_record/{start_utc, first_registered_utc, months, dSR_vs_S, dES21, dMDD, cusum_S, alarms, switches, switch_p99, lag_audit_violations, demoted, demotion_reason, honesty_line, missed_decisions, gaps}` |
| R-26 | `model_card_header.macro:/{instrument_book, instrument_lines, rebalance, no_trade_band, notional_nav, nav_fx, fill_model, roll_calendar}`; `model_card.macro:/costs_per_side/{table_bp, floor_bp, applied_bp, stress_line, roll_cost_line}`; `model_card.macro:/printed/exec_variants/{A, B, C}`; `model_card.macro:/printed/{overnight_intraday, turnover_by_regime, stress_cost, roll_cost, ban_basis}`; `overlay_decision:/extras/{instrument_book, contracts, w_target, w_held, band}` |
| R-27 | `overlay_decision:/extras/{fill_model, decision_price_source, fill_status, flags}`; `model_card.macro:/printed/fill_tracking_error` |
| R-28 | `macro_state:/forward_sim/R28_below_sma10m`; `overlay_decision:/forward_sim/*/rule_id`; `overlay_decision:/forward_sim/*/card/{class, verdict, disposition, displayed_as}`; `overlay_decision:/multipliers/*/{rule_id, exposure_basis}`; `model_card_header.macro:/claim_lines`; `model_card.macro:/claim_line_results/{stacked_dMDD, band, pass}`; `model_card.macro:/pooling/{rule, n_onsets_own, n_onsets_pooled}`; `model_card.macro:/gjr_null_pct`; `model_card.macro:/snooping/{n_variants, share_dMDD_ge_3pp, deflated_prob_sr}` |
| R-29 | `model_card_header.macro:/{card_id, instrument_book, notional_nav}`; `model_card.macro:/{contracts_path, start_band_results}`; `model_card.macro:/settling_run/{span, verdict, pc1_prime_1x, pc1_prime_2x, starts, n_pass, n_starts, n_reject, midpoint_halves}`; `overlay_decision:/forward_sim/*/rule_id` |
| R-30 | `macro_state:/vol/estimator`; `macro_state:/vol/estimator_gate/{status, stage1, stage2_mcs_p, stage3_rank, fallback_used, reason}`; `model_card.macro:/forecast_eval/qlike_mcs_p/*`; `model_card.macro:/forecast_eval/mse_mcs_p/*`; `model_card.macro:/forecast_eval/{christoffersen_p, es_z2, fan_pit_p, vol_of_vol, dMDD_vs_sma20, dSR_vs_sma20}` |
| R-31 | `macro_state:/flags/{ladder_step, ladder_dwell_left, block_new_entries}`; `macro_state:/runtime/*/{hwm_hard, ref_step}`; `overlay_decision:/multipliers/*/rule_id`; `overlay_decision:/multipliers/*/card/verdict`; `model_card.macro:/printed/{binding_share, n_halts, persistence_check}` |
| R-34 | `model_card.macro:/timing_profile/lags/*/{L, dSR, dMDD, dES21, lag_audit, timing_class}`; `model_card.macro:/timing_profile/{strict, LP, LF, FR, label, live_feeds}` |

Rule outputs that have **no §6 schema** (cannot be covered by T-SCHEMA-03; do not invent schemas for them in M0): R-21 `acceptance_report.json` and its md5 (L2240); R-25 `monitoring_report` (L2733); R-23 family-ledger rows (L2440); R-35 `cards/verdicts.jsonl` rows and `run_log.jsonl` records (L3487, L1237-1238); `gate/acceptance_runs.jsonl` (L4819). The test lists them explicitly as "no schema; owned by M7/M8" so a later schema is a visible change.

Name differences between a rule list and §6 (rule governs, L3368; resolution in F-16): R-23 "`N_raw` at registration" ↔ `N_raw_at_registration`; R-22 "lacks … `start`" ↔ `data_span.start`; R-28 card `{class, verdict, disposition, displayed_as}` ↔ `$defs.card` also requires `card_id`, `results_md5`.

### D.4 T-REPRO-01a — runs_from M0 — SYNTH

Row (L5666): "Every artifact and card records the seed, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, the ledger hashes and `results_md5` (§6, §7 `reproducibility.record`)."

Assertions (reading F-12):
1. Card: every name of `reproducibility.record` (`git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5, ledger_hash_at_registration, ledger_hash_at_run`) is in `required` of `model_card.macro` (directly or through the header field set) — 10 of 10 (verified) — and present, non-empty, in the synthetic card written through `write_artifact`.
2. Non-card artifacts (`macro_state`, `overlay_decision`, `event_calendar`, `context_log`): `git_hash, config_hash, data_snapshot_id, knowledge_utc` are `required` in each schema and present in every file `write_artifact` produces; `read_only is True` (T-RO-01 clause "Every artifact has `read_only: true`", L5605).
3. `provenance()` refuses a missing `knowledge_utc` (TypeError: keyword-only, no default) — it is never "now".
4. `canonical_json` pin of B3; `canonical_json` raises on NaN; two writes of the same artifact produce byte-identical files; `strip_volatile` removes exactly `generated_at_utc` and `git_hash`.
5. `header_md5` is unchanged by adding/altering any result field and changes when any header field other than `header_md5` changes; `results_md5` is unchanged by a header-field change, by `generated_at_utc` and by `git_hash`, and changes when any other result field changes.
6. RNG convention: `rng(11).random()` equals `numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(11))).random()`; `child_rngs(11, 2)` streams differ from each other and are reproducible.

### D.5 Clauses of other tests that this area must satisfy

| Test (runs_from) | Clause | Assertion at M0 (unit form) | Fixture | Class |
|---|---|---|---|---|
| T-OWNER-01 (M0; §9.0b L5571) | "the ruling is written to `governance_events.jsonl`" | `append_event(tmp_log, kind="owner_ruling", actor="owner", key="risk_layer.drawdown.hard_stop.level", old=-0.15, new=-0.12, reason=…, refs=[])`: one line, validates, `prev_row_md5 is None`; a second event has `prev_row_md5 == md5(first line bytes)`; `verify_chain(tmp_log)` returns without raising | inline | SYNTH |
| T-SCHEMA-01 (M0; TASK-M0-07) | "The §6.6 example line validates against `quantgen/governance_event.v2.0`" | D.1 item 2 | C.7 | SYNTH |
| T-OBS-05 (M8, L5681) | "At app start the `governance_events.jsonl` hash chain is verified; a hand-edited row raises GOVERNANCE_LOG_BROKEN (page)" | M0: in a 3-line temp log, edit the `reason` text of line 1 (still valid JSON) → `verify_chain` raises with `line == 2`; delete line 2 → raises at the new line 2; make line 1 invalid JSON → `line == 1`; torn last line → raises; `append_event` with an unknown `kind` raises and leaves the file byte-identical. App-start wiring and the page alert: M8 | inline | SYNTH |
| I-06c (M5; §9.0b L5594) | "`macro_state` validates" — joins at M6 | the built KR 2026-11-26 `macro_state` (`gap_sessions` 0, VaR scale 1, `kr_open_gap_event` false) validates. M0 form: D.1 item 7 (`gap_sessions = 0`) | M0: inline; M6: post-close fixture | M0 SYNTH; M6 REFDATA (frozen KRX/NYSE calendars + post-close store; no local substitute carries `official_close` status) |
| I-06c (M5; §9.0b L5595) | "An out-of-schema context field never HALTs; an acting-field schema error HALTs (OPS) the books the artifact describes" — joins at M8 (`bounds_ok`) | M0: `check_artifact` on the macro_state fixture with (a) `annotations.bogus = 1`, `inputs[1].value = "x"` (role `context`), `flags.gap_sessions = -1` → `display_errors`, `books == ()`; (b) plus `inputs[0].value = "x"` (role `acting_exposure`), `vol.vt_weight_next = 2`, `flags.new_flag = true` → `acting_errors`, `books == ("recommended:KR","specification:KR")` (verified classification) | inline | SYNTH (HALT wiring M8) |
| T-SCOPE-01 (f) (M8, L5675) | "A context_log schema failure HALTs nothing" | M0: `check_artifact(context_log with items[0].stale removed)` → `refused`, `books == ()`; `write_artifact` → `quarantined`, no file under `context_log/`, one file under `quarantine/` | inline | SYNTH |
| T-CARD-01 (M7, L5663) | "A card whose header md5 differs from the committed header is refused. … A card without a ledger hash or the R-26 header fields is refused. `displayed_as ∈ {recommendation, insurance}` iff verdict = PASS." | M0: H1, H4, K5, S1 unit cases. The revision/ledger clause ("A class or claim change creates a new revision and increments the family ledger") is M7 | inline | SYNTH |
| T-BOOK-01 (M0 header clauses, L5641) | header refusals of R-26 | `validate_card_header` of the rules-store brief (§B6), which calls `header_issues` (H1, H9, H10) and applies H11-H13 | inline | SYNTH |
| T-REPLAY-01 (M8, L5616) | canonicalisation: "UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace), excluding only `generated_at_utc` and `git_hash`" | M0: D.4 item 4 | inline | SYNTH at M0; full replay REFDATA (needs the M1 store) |
| T-HERM-02 (M0, L5608) | "tests write only to temporary copies of … the artifact directory" | every call in this suite passes a temp `root` / temp log path; after the suite `config.macro_artifact_dir()` is byte-identical / still absent | — | SYNTH |
| T-RO-01 (M0, L5605) | "Every artifact has `read_only: true`" | `read_only` is `const true` and `required` in the 5 artifact schemas (not in the header or the governance line, L3508) | — | SYNTH |
| T-CTX-02 (M6, L5655) | "Every `context_log` item carries `vintage` and `retrieved_at_utc`" | schema `required` (D.2 item 6) | — | SYNTH |
| I-01 (M8, L5688) | "All five artifacts are produced and valid against schema 2.0" | not M0. Needs the post-close fixtures for KR 2026-07-30 / 2026-10-02 and US 2026-07-30 / 2026-10-01 | — | REFDATA: `/home/claude/quantgen_macro_data/` extracts (not on this machine). Local `docs/asset_expansion/cache/yf_069500.KS.csv`, `yf_SPY.csv`, `fred_DEXKOUS.csv`, `yf__VIX.csv`, `yf__VIX3M.csv` are vendor/FRED daily files: usable only as `vendor_close` reference-mode inputs, never as `official_close` acting inputs (F-17) |

No test of this area is OWNER-class. The only owner input that touches these schemas is `sleeves.<market>.notional_nav` (header `notional_nav`), needed before the M7 header commit (Quick start L76 (3)), replaced by a typed sample in every M0 test.

---

## E. Interfaces

### E.1 Needs from other M0 work

| From | What | Shape |
|---|---|---|
| TASK-M0-02/03 (harness, manifest) | temp roots; `MANIFEST.csv` rows for the two fixtures of this brief; test registry rows (`tier: fast`, `runs_from: M0`, the §9.0b deferrals of §D.5) | `tests/fixtures/macro/…` |
| TASK-M0-05 (rules store) | `config_hash` = "hash of the rules-store state" (L3508); the `reproducibility` block; `gate.evaluation.card_header_required` / `card_result_required` | `config_hash() -> str` (proposed: md5 of the canonical JSON of the store state, with `canonical_json`/`md5_hex` of B3; the SPEC names no algorithm) |
| TASK-M0-06 (owner registry) | values for `macro_state.owner_decisions` — a map `<canonical key> -> {decision: "D1".."D6", value, status: "default"|"owner_set"|"pending"}` holding "every decision whose canonical key a rule of this market reads, plus every decision with status pending" (L3605) — and for header `owner_decisions` (key → value at commit); calls `append_event(path, kind="owner_ruling", …)` | dict |
| TASK-M0-12/13 | cost policy consts already in the header schema (`per_side: read_from_gate`, `floor: tick_floor`, `stress: 2.0`, `stress_line: printed`); `sleeves.<market>.notional_nav`; the KRW/non-KRW and futures book maps for H10-H13 | held by the rules-store brief's `validate_card_header(header, store, …)` |

### E.2 Exposes to later milestones

| Consumer | Uses |
|---|---|
| M1 (PIT store, R-19) | `$defs.input` field set = `PITValue` projected to JSON (SPEC L967-988): `name, series_id, source, channel, obs_date, session_date, obs_kind, value, value_status, dispute, available_at_utc, available_at_source, retrieved_at_utc, expected_available_utc, stale_deadline_utc, vintage, timing, role, books, status, content_hash`. Status map (L1108): `MissingInput.reason` missing / stale / provisional_intraday / session_mismatch / synthetic_rejected → `inputs[].status` missing / stale_missed_release / provisional_rejected / session_mismatch / synthetic_rejected; a stale context input → `stale`; `Stale("missing")` → missing, `Stale("missed_release")` → stale_missed_release; `ok`, `disputed`, `warmup` are not failures. `data_snapshot_id()` body replaces the M0 stub. `append_event(path, kind="calendar_change" | "book_state" | "halt" | "rearm" | "binding_change", …)`. `lag_audit = {checked, violations[{series_id, obs_date, check, expected_usable_at_utc, stamped_available_at_utc}]}` |
| M2-M5 (risk layer, engine) | enums and bounds via `enum_of`: `vol.estimator`, `vt_status {ok, warmup, fail_closed}`, `hedge_reasons`, `ladder_step {none, step_-8, step_-12, hard_stop_-15}`, `hard_stop {armed, halted, rearm_refused, post_rearm_cap}`, `engine_state {DISARMED, ARMED, HALTED}`, `halt.class {RISK, OPS}`, `rearm_mode {auto, operator}`, `binding_factor {none, absolute_single_name, active_single_name, aggregate, semis}`, concentration `template {domestic_max10_or_weight, msci_25_50, pair_35}`; `runtime[]` entry shape; book-id grammar `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on|off|S>` (L3609, L1180); S5 recomputation helper |
| M6 (builders `build_macro_state`, `build_overlay_decisions`, `build_context_log`, L1073-1075) | `provenance()`, `write_artifact()`, `check_artifact()`; `context_log` items; `acts: false` |
| M7 (cards, gate) | `header_issues`, `card_issues`, `header_md5`, `results_md5`, `HEADER_FIELDS`, `RESULT_FIELDS`, `rng`/`child_rngs`; `append_event(path, kind="header_commit" | "package_freeze" | "package_redesign", …)`; enums `verdict`, `disposition`, `permitted_fix {null, widen_grid, lengthen_holding, extend_history, repair_rerun}`, `timing_class {VALUE, NON-COMPLIANT, COMPLIANT}`, `timing_profile.label {robust, timing_fragile}`; verdict reason codes for `verdict_reason` (L4779): `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id |
| M8 (`bounds_ok`, `verdict_filter`, app start) | `check_artifact().status/books` → `runtime_halt(book, "OPS", …)`; quarantine dir; `verify_chain(path)` → `GOVERNANCE_LOG_BROKEN`; `strip_volatile` + `canonical_json` for T-REPLAY-01; `results_md5` re-hash for T-CARD-03 |
| UI Macro page (later) | reads artifacts from `config.macro_artifact_dir()`; displays only schema fields; `extras.validation_errors` badge |

### E.3 Existing card format vs `model_card.macro` (SPEC L3911 "Map them onto the app's actual card format; do not run a parallel registry")

Existing: `core/quant/validate.py:735 ModelCard` → `docs/asset_expansion/cards/*.json` (34 files; e.g. `S_E2_voltarget_kodex200.json`), read by `validate.load_cards` and `ui/strategy_lab_page.py`. Top-level keys: `card_id, kind, hypothesis, rules, universe, data, costs, protocol, trials, seed, stats, tests, decision, decision_reason, revise_target, lines, decay_haircut, created, author, results_file, results_md5, citations`.

| Existing key | `model_card.macro` | Note |
|---|---|---|
| `card_id`, `hypothesis`, `seed`, `results_md5`, `tests` | same names | `tests` key set differs (existing: `dsr, pbo, ci90, sr_stress`; v2: `step1…step9, PC1p, PC2…PC7`) |
| `decision` / `decision_reason` | `verdict` / `verdict_reason` | same four verdict words; v2 writes `INSUFFICIENT_DATA` with an underscore |
| `revise_target` | `first_failed_check` + `permitted_fix` | |
| `rules`, `universe` | `rule`, `parameters`, `searched_parameters`, `instrument_book` | |
| `data {sessions,start,end,source}` | `data`, `data_span`, `history_first_close` | |
| `costs {cost_bps, stress_multiplier}` | `costs` (policy consts) + `costs_per_side {table_bp, floor_bp, applied_bp}` + `cost_stress 2.0` | a header may not carry a rate |
| `trials {N_planned, N_total, ledger}` | `N_raw_at_registration`, `N_raw`, `N_eff`, ledger hashes | |
| `created` | `created_utc` | |
| `kind`, `lines`, `decay_haircut`, `author`, `results_file`, `citations`, `protocol`, `stats` | **no counterpart; the closed schema refuses them** | `printed.hl_haircut` is the nearest to `decay_haircut` |

Conservative reading: the 34 existing cards are not macro cards and are never validated against `model_card.macro` (they carry no `schema` field); macro cards are written only through `card_issues` + `write_artifact`; "no parallel registry" is met at the reader, by one loader that lists both kinds and a view adapter for the UI (M7/M8; F-18). M0 changes neither `ModelCard` nor the existing files.

---

## F. Ambiguities, contradictions and conservative readings

| # | Where | Issue | Reading taken (conservative) |
|---|---|---|---|
| F-1 | L3507 vs JSON Schema 2020-12 | `format` is annotation-only in the standard; the SPEC says all times are UTC with "Z" | Assert `format` (reject offsets, missing "Z", bad dates). All SPEC examples pass. |
| F-2 | L3913, L3941, L4876 | `header_md5` "covers the header fields only" but is itself a header field | Hash every `HEADER_FIELDS` key except `header_md5`, canonical JSON. `created_utc` is included (it is a header field). |
| F-3 | L3913 "`results_md5` covers the result fields" vs L4683 `volatile_fields: [generated_at_utc, git_hash]` vs L3487 "its card file re-hashes to the committed `results_md5`" | Whether `results_md5` includes itself and the two volatile fields | Exclude `results_md5`, `generated_at_utc`, `git_hash`; include everything else in `RESULT_FIELDS` (incl. `knowledge_utc`, `config_hash`, `data_snapshot_id`, `ledger_hash_at_run`). `git_hash` stays protected by `cards/verdicts.jsonl` (L3487). **Decision needed before the M7 freeze**; changing it later is a package change. |
| F-4 | L4088, L2340, L4618, L4883 | "acting long-sample card" has no machine-readable definition (no header flag; R-06 KR, R-29 have bands; "both are null on other cards") | `header_issues(…, acting_long_sample=True)` by default: a null `start_band`/`midpoint_halves` is refused unless the caller states the card is not long-sample. K6 (band ⇒ band results) is an inference, fail closed. Owner/M7 must name the predicate. |
| F-5 | L4851 | "A Sharpe or predictability claim on a protective rule is refused" is about claim text; `claim_type` enum is `{outperformance, protection, diversification}` | CARD-P requires `claim_type = protection` (H8). Text screening of `claim` is not attempted. |
| F-6 | L3508, L1014, L5616 | `data_snapshot_id` = "md5 of the sorted content hashes visible at `knowledge_utc`": the concatenation format is not given | M0 stub: md5 of `"\n".join(sorted(hashes))`; M1 owns the final rule. Until M1 the id is the md5 of the empty string and must be labelled a stub in any display. |
| F-7 | L4088 "a non-KRW book without `nav_fx`" | The set of non-KRW books is not enumerated | KRW books = `KRX_ETF_line, KRX_stock_book, KOSPI200_futures, mini_KOSPI200_futures, KRX_listed_SP500_ETF, FX_KRX_USD_futures`; every other book (incl. `crypto_venue`, `FX_broker_spot`, `multi_line`) requires `nav_fx` (fail closed). Owned by TASK-M0-13. |
| F-8 | L4096, L4110, L1250, L4126 | Location of `governance_events.jsonl` and of the artifact dir is "proposed"; "md5 of the previous line" does not say bytes vs re-serialised | `config.macro_artifact_dir()` = `~/.nextgen/macro` (env `NEXTGEN_MACRO_DIR`); log at its root; hash = md5 of the stored UTF-8 bytes of the previous line without its `\n`. |
| F-9 | L3370 "HALTs (OPS) the books it describes"; L1178 | An `overlay_decision` has no `runtime[]`; "the books it describes" is not defined for it; no `reason_code` literal is given for this HALT | Books = `recommended:<market>` + `specification:<market>` (+ books of acting inputs); unreadable market → all of the run's books. `reason_code` proposed `acting_artifact_invalid`; final literal belongs to M5/M8. |
| F-10 | L3738, L3769, L3581 | `overlay_applied_recommended_book` depends on whether the ladder acts in the recommended book (`macro_state.flags.ladder_steps_act_in`), a field of another artifact | S5 takes `ladder_in_recommended: bool` as an argument; default False (ladder enters the recommended book as 1.0 = no claim of an acting step). Cross-artifact check at M8. |
| F-11 | L3909-4092 | The SPEC has no `model_card.macro` example; T-SCHEMA-01 "every example" therefore has no card instance | T-SCHEMA-01 covers the six examples; the card is covered by T-SCHEMA-02/03 with the synthetic C.9 block. |
| F-12 | L5666 "Every artifact and card records the seed, …, the ledger hashes and `results_md5`"; L3365 "`macro_state` inputs carry … every common provenance field" | Non-card artifact schemas are closed and declare no `seed`, ledger hash or `results_md5`; inputs declare no `git_hash` etc. | Cards: all 10 names of `reproducibility.record`. Other artifacts: the four provenance names their schema declares. Inputs: the 20 required input fields; the common provenance fields are asserted on the artifact. No undeclared field is added to a closed schema (it would be an acting failure). |
| F-13 | Tech-fund R3 `research_notes/R3_TF_neural_link.md` L814 (G-17 attribution block "on every card"), L822 and L1300 (G-25 / XS-12 `S_beta` comparator), L1299 (XS-11 block rule) | The council card schema is closed (`unevaluatedProperties: false`, no `extras`) and `comparator` is `enum ["S_same_average_exposure","overlay_off"]`: an attribution block or an `S_beta` comparator is refused as written | Do not extend the v2.0 schemas silently. The tech-fund brief must supply exact field names; they enter as declared, optional properties in a named amendment of `model_card.macro` (+ `HEADER_FIELDS`/`RESULT_FIELDS`), before the M7 freeze. Until then tech-fund cards cannot be written as `model_card.macro`. XS-11 needs no schema change (`tests.step2/step5` are open; `PC3.block_PW` exists). |
| F-14 | L3508 `git_hash`; L4820 "committed to the repository, an external, timestamped anchor"; L3487 (iii) | The QUANTGEN tree is not a git repository | `git_hash()` returns `"UNVERSIONED"` (schema type is `string`); never a fabricated sha. The M7 freeze anchor and `verdict_filter` (iii) cannot be met until the owner puts the tree under git. Blocker for M7/M8, not for M0. |
| F-15 | L5671 "per rule"; L1806, L1811 | Only R-19…R-31, R-34 have "Outputs and schema fields" lists; R-01/R-03/R-04 have an "Output" row; R-32/R-33/R-35 are short entries; other v1.2 rules name no schema field | T-SCHEMA-03 iterates the 19 rules of `RULE_OUTPUTS`; rules without a list are covered through the full fixtures (every §6 field appears in at least one validated instance). |
| F-16 | L2508 vs L3933/L4884; L2391 vs L3967; L3033 vs L3757 | Three name/shape differences between rule lists and §6 | `N_raw_at_registration` (two of three sources; `N_raw` is the result field); `start` = `data_span.start`; `$defs.card` keeps its six required keys. No §6 edit. |
| F-17 | L5688 "All five artifacts" | The five are not listed (§3.9 `build_artifacts` names `macro_state`, `overlay_decision`, `context_log`, event windows and gap tags, R-08 annotation) | Out of M0. Reading for M8: `macro_state`, `overlay_decision`, `context_log`, `event_calendar`, plus the `run_log.jsonl` record; to be confirmed. |
| F-18 | L3911 | "do not run a parallel registry" vs a closed card schema that cannot hold the existing card keys | §E.3: separate validation, one reader. |
| F-19 | L3630, L3370 | Shape of `extras.validation_errors`; quarantine file naming; alert codes | Proposed in B3; any shape is schema-legal because `extras` is open. |
| F-20 | L4031-4034 vs L2323 | `episodes[].trough` is a required non-null date while an episode may be `open: true` ("a bear not yet confirmed over") | Keep the schema: an open episode carries its running-low date as `trough` with `open: true`. M7 (R-22) confirms. |
| F-21 | L3972-3977 | `start_band.require` and `midpoint_halves` are closed objects with consts; a card "declares neither its band nor its pass share" (L2372) | The header restates the frozen shape; H16 (M7) checks it equals `gate.evaluation.start_band_shapes`. M0 validates shape only. |

---

## G. DO-NOT-BUILD items and invariants binding this area

- **No order path, no order field.** "No artifact contains an order instruction. Weights are targets for the simulated order book only." (L3511). `read_only` is `const true` on the five artifact schemas; the writer has no other mode (T-RO-01; §10 item 21).
- **Cap 1.0 is permanent; overlays in [0.5, 1.0]; composition is `min`.** Schema bounds: `vol.vt_weight_next`, `vt_weight_recommended_book`, `vol_scale`, `vol_scale_recommended_book`, `forward_sim[].value`, `R29_vt_weight_next`, `by_book.composed/gross` ∈ [0, 1]; `multipliers[].value`, `refusal[].value`, `overlay_min`, `overlay_applied_*` ∈ [0.5, 1.0]; `ladder`, `post_rearm_cap` ∈ {0.5, 1.0, null}; `composition` const `min`; `overlay_floor` const 0.5; `overlay_cap` const 1.0 (§10 items 2, 8, 31; T-CAP-01). Never widen a bound to make an artifact validate.
- **The Kish N̂ is never a field** (L4092; §10 item 36). No schema property, no extras key, no code path.
- **No regime-model state, acting or displayed** (§10 items 11, 24, 27; R-33 L3381, L3389): the only state labels in `macro_state` are the σ̂ display labels (`display_label_rel/abs` ∈ {calm, normal, elevated, stressed}, methods const `trailing756_quartiles_causal_filtered` / `expanding_full_history_quartiles_causal_filtered`); "A BOCPD probability may be written only to the R-18 research log, never displayed." Do not add a field for one, in `extras` either.
- **`max(SMA20, implied)` is retired** (L3566; §10 item 30): `alt_sigma_logged` is "asymmetric estimator only".
- **A header never carries a result, and is immutable once committed** (L3913, L4876; §10 items 23, 32): no code path rewrites a committed header; a change is a new revision or a new card (L4891-4892).
- **A forward record can never raise a verdict** (L4060 "falsification alarms only (R-25); can never raise the verdict"; §10 item 35).
- **Refusal and FORWARD-SIM blocks are display only, read by no book** (L3589-3592, L3748; §10 item 22); `context_log.acts` is const `false` and no acting module may read it (T-CTX-01).
- **Unclassified = acting = fail closed** (L3370). Adding a property to `macro_state`/`overlay_decision` without adding it to `DISPLAY_PATHS` makes its errors HALT-class by design; do not default new fields to display.
- **`extras` is not a back door**: it is never schema-validated, so nothing an acting module reads may live only there except the R-26/R-27 keys the SPEC names (`instrument_book, contracts, w_target, w_held, band, usdkrw, fill_model, decision_price_source, fill_status, flags`), with `w_target`/`w_held` bounded in code.
- **Schemas are the contract (C-7)**: "Where a rule's "Outputs and schema fields" list and this section differ, the rule governs and this section is fixed in the same change" (L3503). A schema edit is made in the JSON file and in the SPEC-derived tests together; never by loosening the validator.
- **No financial defaults**: the validator and the writer never fill a missing value; a missing field is an error (repo rule, `core/rules/model.py` docstring; SPEC L4127).
- **No verdict before the M7 freeze** (P11, L5546): this area validates shapes only; C.9 values are fillers and must never be displayed or written outside a temp root.
- **Governance log is append-only and hash-chained**; never rewritten, truncated or repaired by code; a broken chain is reported, not fixed (L1250, T-OBS-05).
- **Hermetic**: no network; tests write only under temp roots (T-HERM-01/02). **No new dependency** (`jsonschema` stays absent).
